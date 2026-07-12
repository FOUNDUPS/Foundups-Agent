"""Tests for HOLOINDEX_FRESHNESS_RECEIPT_PHASE1."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from holo_index.freshness_receipt import (
    ALL_COLLECTIONS,
    SCHEMA_VERSION,
    build_freshness_receipt,
    collections_for_changed_paths,
    evaluate_freshness_for_paths,
    freshness_receipt_path,
    load_freshness_receipt,
    write_freshness_receipt,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


class CountCollection:
    def __init__(self, count: int):
        self._count = count

    def count(self) -> int:
        return self._count


def _holo(**counts: int):
    attr_map = {
        "navigation_code": "code_collection",
        "navigation_wsp": "wsp_collection",
        "navigation_tests": "test_collection",
        "navigation_skills": "skill_collection",
        "navigation_symbols": "symbol_collection",
        "navigation_docs": "docs_collection",
        "navigation_knowledge": "knowledge_collection",
        "navigation_work_ledger": "work_ledger_collection",
        "navigation_vocabulary": "vocabulary_collection",
    }
    values = {}
    for collection_name, attr_name in attr_map.items():
        values[attr_name] = CountCollection(counts.get(collection_name, 3))
    return SimpleNamespace(**values)


def test_receipt_contains_all_expected_collections(tmp_path: Path) -> None:
    receipt = build_freshness_receipt(
        _holo(),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="manual_index",
        generated_at="2026-07-12T00:00:00+00:00",
        repo_head_sha="abc123",
    )

    assert receipt.schema_version == SCHEMA_VERSION
    assert receipt.repo_head_sha == "abc123"
    assert receipt.source == "manual_index"
    assert [entry.name for entry in receipt.collections] == list(ALL_COLLECTIONS)
    assert all(entry.status == "indexed" for entry in receipt.collections)


def test_receipt_roundtrip_json(tmp_path: Path) -> None:
    receipt = build_freshness_receipt(
        _holo(**{"navigation_skills": 0}),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="manual_index",
        generated_at="2026-07-12T00:00:00+00:00",
        repo_head_sha="abc123",
    )
    path = freshness_receipt_path(tmp_path)

    write_freshness_receipt(receipt, path)
    loaded = load_freshness_receipt(path)

    assert loaded.to_dict() == receipt.to_dict()
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["collections"][3]["name"] == "navigation_skills"
    assert raw["collections"][3]["status"] == "empty"


def test_changed_paths_map_to_freshness_collections() -> None:
    paths = [
        "WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md",
        "modules/foundups/agent/src/create_foundup_dryrun.py",
        "modules/foundups/agent/tests/test_create_foundup_dryrun.py",
        "modules/foundups/agent/README.md",
        "modules/foundups/agent/SKILLz.md",
        "docs/0102_session_briefings/work_ledger.schema.json",
        "WSP_knowledge/docs/Papers/PQN_Deep_Dive.md",
        "extensions/foundups_advisory_workers/extension.js",
    ]

    assert collections_for_changed_paths(paths) == [
        "navigation_code",
        "navigation_docs",
        "navigation_knowledge",
        "navigation_skills",
        "navigation_symbols",
        "navigation_tests",
        "navigation_work_ledger",
        "navigation_wsp",
    ]


def test_missing_receipt_fails_closed_for_changed_paths() -> None:
    check = evaluate_freshness_for_paths(
        None,
        ["modules/foundups/agent/src/create_foundup_dryrun.py"],
        expected_repo_head_sha="abc123",
    )

    assert check.ok is False
    assert check.required_collections == ["navigation_symbols"]
    assert check.stale_collections == ["navigation_symbols"]
    assert "missing_freshness_receipt" in check.reasons


def test_missing_required_collection_receipt_fails_closed(tmp_path: Path) -> None:
    receipt = build_freshness_receipt(
        _holo(),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="manual_index",
        generated_at="2026-07-12T00:00:00+00:00",
        repo_head_sha="abc123",
    )
    partial = receipt.to_dict()
    partial["collections"] = [
        entry for entry in partial["collections"] if entry["name"] != "navigation_symbols"
    ]

    check = evaluate_freshness_for_paths(
        partial,
        ["modules/foundups/agent/src/create_foundup_dryrun.py"],
        expected_repo_head_sha="abc123",
    )

    assert check.ok is False
    assert check.stale_collections == ["navigation_symbols"]
    assert "missing_collection_receipt:navigation_symbols" in check.reasons


def test_stale_repo_sha_fails_closed_for_required_collections(tmp_path: Path) -> None:
    receipt = build_freshness_receipt(
        _holo(),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="manual_index",
        generated_at="2026-07-12T00:00:00+00:00",
        repo_head_sha="old",
    )

    check = evaluate_freshness_for_paths(
        receipt,
        [
            "WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md",
            "docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md",
        ],
        expected_repo_head_sha="new",
    )

    assert check.ok is False
    assert check.stale_collections == ["navigation_work_ledger", "navigation_wsp"]
    assert "stale_repo_head_sha" in check.reasons


def test_empty_collection_fails_closed_when_path_requires_it(tmp_path: Path) -> None:
    receipt = build_freshness_receipt(
        _holo(**{"navigation_work_ledger": 0}),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="manual_index",
        generated_at="2026-07-12T00:00:00+00:00",
        repo_head_sha="abc123",
    )

    check = evaluate_freshness_for_paths(
        receipt,
        ["docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md"],
        expected_repo_head_sha="abc123",
    )

    assert check.ok is False
    assert check.stale_collections == ["navigation_work_ledger"]
    assert "collection_not_indexed:navigation_work_ledger" in check.reasons


def test_cli_index_state_writer_emits_freshness_receipt_contract() -> None:
    source = (REPO_ROOT / "holo_index" / "_cli_main.py").read_text(encoding="utf-8")

    assert "build_freshness_receipt(" in source
    assert "write_freshness_receipt(receipt, receipt_path)" in source
    assert '"freshness_receipt_path": str(receipt_path)' in source
    assert "HOLOINDEX_QUERY_READONLY" in source
