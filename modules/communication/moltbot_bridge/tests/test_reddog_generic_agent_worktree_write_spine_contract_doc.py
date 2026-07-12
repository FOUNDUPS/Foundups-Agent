"""Static tests for REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_CONTRACT_PHASE1."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
CONTRACT_DOC = (
    REPO_ROOT
    / "docs"
    / "audits"
    / "architecture"
    / "REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_CONTRACT_PHASE1.md"
)

REQUIRED_SECTIONS = (
    "## Purpose",
    "## Direct-read evidence (WSP_50)",
    "## 1. Generic domain profile contract",
    "## 2. Required authority inputs",
    "## 3. Re-derived root invariant",
    "## 4. Pin-independent denylist",
    "## 5. Worktree and command boundary",
    "## 6. Receipt chain",
    "## 7. Fail-closed rejection rules",
    "## 8. WSP_15 sequence",
    "## 9. HoloIndex boundary",
    "## 10. WSP_97 truth table",
    "## Explicit non-goals",
    "## Truth Boundary Checklist",
)

REQUIRED_MARKERS = (
    "GENERIC DOES NOT MEAN UNBOUNDED",
    "GenericAgentWorktreeDomainProfile",
    "canonical_root_fn",
    "materialize_fn",
    "RedDogOperatorLoopWardrobeSelectionReceipt",
    "RedDogDelegatedWorkAuthority",
    "SignedReceiptChainVerificationResult",
    "ExecutionValveDecision",
    "VALVE_OPEN_WORKTREE_CREATE",
    "consensus_receipt_digest",
    "WreCwdGuardResult",
    "pin-independent governance/CI denylist",
    "draft PR only",
    "GenericAgentWorktreeWriteReceipt",
    "no_merge_performed",
    "no_reward_settlement_performed",
    "HOLOINDEX_REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_CONTRACT_INDEX_GAP_PHASE1",
    "SPECIFIED_NOT_IMPLEMENTED",
    "OBSERVED",
)

FORBIDDEN_SCOPE = (
    "No generic writer implementation.",
    "No live write.",
    "No shell runner.",
    "No merge authority.",
    "No HoloIndex re-index.",
)


@pytest.fixture(scope="module")
def contract_text() -> str:
    assert CONTRACT_DOC.is_file(), "generic agent worktree write spine contract missing"
    return CONTRACT_DOC.read_text(encoding="utf-8")


def test_generic_worktree_spine_contract_doc_exists(contract_text: str) -> None:
    assert len(contract_text) > 7000


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_generic_worktree_spine_contract_sections(section: str, contract_text: str) -> None:
    assert section in contract_text, f"missing section: {section}"


@pytest.mark.parametrize("marker", REQUIRED_MARKERS)
def test_generic_worktree_spine_contract_markers(marker: str, contract_text: str) -> None:
    assert marker in contract_text, f"missing marker: {marker}"


@pytest.mark.parametrize("line", FORBIDDEN_SCOPE)
def test_generic_worktree_spine_contract_non_goals(line: str, contract_text: str) -> None:
    assert line in contract_text


def test_generic_worktree_spine_contract_requires_rederived_root(contract_text: str) -> None:
    lower = contract_text.lower()
    assert "re-derived root" in lower
    assert "trusting caller-supplied `allowed_paths`" in lower
    assert "must not widen" in lower


def test_generic_worktree_spine_contract_requires_full_valve_not_env_shortcut(contract_text: str) -> None:
    assert "_resolve_valve_state(env, [])" in contract_text
    assert "full `evaluate_reddog_execution_valve(...)`" in contract_text
    assert "decision digest plus empty `rejection_reasons`" in contract_text


def test_generic_worktree_spine_contract_denies_authority_substrate_edits(contract_text: str) -> None:
    for marker in (
        ".github/workflows/**",
        "WSP framework protocol files",
        "HoloIndex indexer/ranking/config files",
        "RedDog valve, policy gate, signature verifier",
        "permission stores",
    ):
        assert marker in contract_text


def test_generic_worktree_spine_contract_ascii_only(contract_text: str) -> None:
    non_ascii = [hex(ord(char)) for char in contract_text if ord(char) > 127]
    assert non_ascii == [], f"non-ASCII chars found: {non_ascii[:5]}"
