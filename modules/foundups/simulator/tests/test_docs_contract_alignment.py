"""Docs/contract alignment guardrails for simulator economics."""

from __future__ import annotations

import json
import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_source_of_truth_matrix(root: Path) -> dict:
    matrix_path = root / "modules/foundups/simulator/contracts/source_of_truth_matrix.json"
    assert matrix_path.exists(), "Missing source_of_truth_matrix.json"
    return json.loads(matrix_path.read_text(encoding="utf-8"))


def _extract_streamable_events_from_sse(sse_text: str) -> set[str]:
    match = re.search(r"STREAMABLE_EVENT_TYPES\s*=\s*\{(.*?)\n\}", sse_text, re.S)
    assert match is not None, "Could not locate STREAMABLE_EVENT_TYPES in sse_server.py"
    return set(re.findall(r'"([a-z_]+)"', match.group(1)))


def _extract_streamable_events_from_interface(interface_text: str) -> set[str]:
    match = re.search(
        r"### STREAMABLE_EVENT_TYPES\s*```python\s*STREAMABLE_EVENT_TYPES = \{(.*?)\n\}\s*```",
        interface_text,
        re.S,
    )
    assert match is not None, "Could not locate STREAMABLE_EVENT_TYPES block in INTERFACE.md"
    return set(re.findall(r'"([a-z_]+)"', match.group(1)))


def test_sse_streamable_events_match_interface_contract() -> None:
    """SSE runtime stream set must exactly match INTERFACE.md contract list."""
    root = _repo_root()
    sse_text = (root / "modules/foundups/simulator/sse_server.py").read_text(encoding="utf-8")
    interface_text = (root / "modules/foundups/simulator/INTERFACE.md").read_text(encoding="utf-8")

    sse_events = _extract_streamable_events_from_sse(sse_text)
    interface_events = _extract_streamable_events_from_interface(interface_text)

    assert sse_events == interface_events


def test_tokenomics_genesis_example_matches_btc_reserve_constant() -> None:
    """Tokenomics and architecture denominations must match the genesis constant."""
    root = _repo_root()
    reserve_text = (
        root / "modules/foundups/simulator/economics/btc_reserve.py"
    ).read_text(encoding="utf-8", errors="ignore")
    tokenomics_text = (
        root / "modules/infrastructure/foundups_tokenization/docs/TOKENOMICS.md"
    ).read_text(encoding="utf-8", errors="ignore")

    genesis_match = re.search(r"genesis_ups_per_btc:\s*float\s*=\s*([0-9_]+(?:\.[0-9]+)?)", reserve_text)
    assert genesis_match is not None, "Could not locate genesis_ups_per_btc in btc_reserve.py"
    genesis_value = int(float(genesis_match.group(1).replace("_", "")))

    doc_match = re.search(r"ups_per_btc = ([0-9,]+) \(genesis default\)", tokenomics_text)
    assert doc_match is not None, "Could not locate tokenomics genesis default example"
    doc_value = int(doc_match.group(1).replace(",", ""))

    assert doc_value == genesis_value

    architecture_text = (
        root / "docs/architecture/FOUNDUPS_BTC_RESERVE_TOKEN_ARCHITECTURE.md"
    ).read_text(encoding="utf-8")
    architecture_match = re.search(
        r"Canonical constraint: 1 UPS = ([0-9,]+) satoshis? \(at genesis",
        architecture_text,
    )
    assert architecture_match is not None, "Could not locate architecture genesis denomination"
    architecture_sats = int(architecture_match.group(1).replace(",", ""))
    assert architecture_sats * genesis_value == 100_000_000

    # A source map must not promote an incompatible forecast unit to chain policy.
    matrix = _load_source_of_truth_matrix(root)
    units = next(item for item in matrix["economic_invariants"]
                 if item["id"] == "ups_sat_accounting_unit")
    assert units["status"] == "CONFLICTING"
    assert units["decision_class"] == "D"
    assert units["chain_activation"] == "BLOCKED"
    observations = units["observations"]
    assert observations["btc_reserve_genesis"]["ups_per_btc"] == genesis_value
    assert observations["btc_reserve_genesis"]["satoshis_per_ups"] == architecture_sats
    assert observations["projection_accounting"]["satoshis_per_ups"] != architecture_sats


def test_governing_economic_protocol_mirrors_match() -> None:
    """Economic contract changes must not leave the knowledge mirror stale."""
    root = _repo_root()
    for name in (
        "WSP_26_FoundUPS_DAE_Tokenization.md",
        "WSP_27_pArtifact_DAE_Architecture.md",
        "WSP_29_CABR_Engine.md",
        "WSP_100_DAE_SmartDAO_Escalation_Protocol.md",
    ):
        framework = (root / "WSP_framework/src" / name).read_text(encoding="utf-8")
        knowledge = (root / "WSP_knowledge/src" / name).read_text(encoding="utf-8")
        assert framework == knowledge, f"Stale governing mirror: {name}"


def test_source_of_truth_matrix_paths_exist() -> None:
    """All declared references in the source-of-truth matrix must exist."""
    root = _repo_root()
    matrix = _load_source_of_truth_matrix(root)

    paths: set[str] = set()
    for invariant in matrix.get("economic_invariants", []):
        paths.update(invariant.get("code_refs", []))
        paths.update(invariant.get("doc_refs", []))

    for event_meta in matrix.get("event_contracts", {}).values():
        paths.update(event_meta.get("emitter_refs", []))
        interface_ref = event_meta.get("interface_ref")
        if interface_ref:
            paths.add(interface_ref)

    for docs_key in ("tokenization_docs", "skill_docs"):
        paths.update(matrix.get("doc_alignment", {}).get(docs_key, []))

    missing = [path for path in sorted(paths) if not (root / path).exists()]
    assert not missing, f"Missing contract references: {missing}"


def test_matrix_declared_events_have_emit_sites() -> None:
    """Every matrix-declared event contract must map to at least one emit site."""
    root = _repo_root()
    matrix = _load_source_of_truth_matrix(root)

    for event_type, meta in matrix.get("event_contracts", {}).items():
        emitters = meta.get("emitter_refs", [])
        assert emitters, f"{event_type} has no emitter_refs in matrix"
        pattern = re.compile(rf"event_type\s*=\s*[\"']{re.escape(event_type)}[\"']")

        matched = False
        for emitter_path in emitters:
            text = (root / emitter_path).read_text(encoding="utf-8", errors="ignore")
            if pattern.search(text):
                matched = True
                break

        assert matched, f"{event_type} has no explicit emit site in declared emitters"


def test_skill_and_tokenomics_docs_share_cabr_semantics() -> None:
    """Skill guidance and tokenomics docs should both state CABR routing semantics."""
    root = _repo_root()
    skill_text = (
        root / "modules/communication/moltbot_bridge/workspace/skills/foundups-wsp/SKILL.md"
    ).read_text(encoding="utf-8", errors="ignore")
    tokenomics_text = (
        root / "modules/infrastructure/foundups_tokenization/docs/TOKENOMICS.md"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "CABR controls" in skill_text and "flow rate" in skill_text
    assert "CABR does not create UPS" in tokenomics_text or "CABR does not create" in tokenomics_text
    assert "total_ups_circulating" in skill_text
    assert "total_ups_circulating" in tokenomics_text
