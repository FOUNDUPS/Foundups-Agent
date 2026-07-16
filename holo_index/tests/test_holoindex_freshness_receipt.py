"""Tests for HOLOINDEX_FRESHNESS_RECEIPT_PHASE1."""

from __future__ import annotations

import json
import re
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


class SnapshotCollection:
    def __init__(self, name: str, count: int):
        self.name = name
        self._count = count
        self.metadata = {"embedding_backend": "test-embedding"}

    def count(self) -> int:
        return self._count

    def get(self, include=None):
        return {
            "ids": [f"{self.name}:{index}" for index in range(self._count)],
            "metadatas": [
                {"path": f"{self.name}/item_{index}.txt"}
                for index in range(self._count)
            ],
        }


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
        values[attr_name] = SnapshotCollection(collection_name, counts.get(collection_name, 3))
    return SimpleNamespace(**values)


def _count_only_holo(**counts: int):
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


def _assert_sha256_digest(value: str) -> None:
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", value)


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
    _assert_sha256_digest(receipt.generation_id)
    assert [entry.name for entry in receipt.collections] == list(ALL_COLLECTIONS)
    assert all(entry.status == "indexed" for entry in receipt.collections)
    assert all(entry.verification == "PASS" for entry in receipt.collections)
    assert all(entry.embedding_backend == "test-embedding" for entry in receipt.collections)
    for entry in receipt.collections:
        _assert_sha256_digest(entry.source_manifest_digest)
        _assert_sha256_digest(entry.indexed_paths_digest)
        _assert_sha256_digest(entry.removed_paths_digest)


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
        "extensions/reddog/extension.js",
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
    assert "collection_verification_not_pass:navigation_work_ledger" in check.reasons


def test_count_only_collection_receipt_fails_closed_for_required_path(tmp_path: Path) -> None:
    receipt = build_freshness_receipt(
        _count_only_holo(),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="manual_index",
        generated_at="2026-07-12T00:00:00+00:00",
        repo_head_sha="abc123",
    )

    check = evaluate_freshness_for_paths(
        receipt,
        ["modules/foundups/agent/src/create_foundup_dryrun.py"],
        expected_repo_head_sha="abc123",
    )

    assert check.ok is False
    assert check.stale_collections == ["navigation_symbols"]
    assert "collection_verification_not_pass:navigation_symbols" in check.reasons
    assert "collection_manifest_missing:navigation_symbols" in check.reasons
    assert "collection_indexed_paths_missing:navigation_symbols" in check.reasons


def test_legacy_count_only_mapping_fails_required_generation_and_manifest() -> None:
    legacy = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": "2026-07-12T00:00:00+00:00",
        "repo_root": str(REPO_ROOT),
        "repo_head_sha": "abc123",
        "ssd_path": "ssd",
        "source": "legacy",
        "collections": [
            {
                "name": "navigation_symbols",
                "count": 1,
                "status": "indexed",
                "source": "legacy",
                "repo_head_sha": "abc123",
                "last_indexed_at": "2026-07-12T00:00:00+00:00",
            }
        ],
    }

    check = evaluate_freshness_for_paths(
        legacy,
        ["modules/foundups/agent/src/create_foundup_dryrun.py"],
        expected_repo_head_sha="abc123",
    )

    assert check.ok is False
    assert "missing_holoindex_generation_id" in check.reasons
    assert "collection_verification_not_pass:navigation_symbols" in check.reasons
    assert "collection_manifest_missing:navigation_symbols" in check.reasons


def test_generation_id_changes_when_collection_manifest_changes(tmp_path: Path) -> None:
    first = build_freshness_receipt(
        _holo(),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="manual_index",
        generated_at="2026-07-12T00:00:00+00:00",
        repo_head_sha="abc123",
    )
    second = build_freshness_receipt(
        _holo(**{"navigation_symbols": 4}),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="manual_index",
        generated_at="2026-07-12T00:00:00+00:00",
        repo_head_sha="abc123",
    )

    assert first.generation_id != second.generation_id


def test_code_refresh_does_not_mark_skill_collection_fresh_without_skill_manifest(
    tmp_path: Path,
) -> None:
    receipt = build_freshness_receipt(
        _holo(**{"navigation_skills": 3}),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="code_only_refresh",
        generated_at="2026-07-12T00:00:00+00:00",
        repo_head_sha="abc123",
    )
    data = receipt.to_dict()
    for entry in data["collections"]:
        if entry["name"] == "navigation_skills":
            entry["source_manifest_digest"] = ""
            entry["indexed_paths_digest"] = ""
            entry["verification"] = "UNVERIFIED"

    check = evaluate_freshness_for_paths(
        data,
        ["modules/foundups/agent/SKILLz.md"],
        expected_repo_head_sha="abc123",
    )

    assert check.ok is False
    assert check.stale_collections == ["navigation_skills"]
    assert "collection_verification_not_pass:navigation_skills" in check.reasons
    assert "collection_manifest_missing:navigation_skills" in check.reasons


def test_cli_index_state_writer_emits_freshness_receipt_contract() -> None:
    source = (REPO_ROOT / "holo_index" / "_cli_main.py").read_text(encoding="utf-8")

    assert "build_freshness_receipt(" in source
    assert "write_freshness_receipt(receipt, receipt_path)" in source
    assert '"freshness_receipt_path": str(receipt_path)' in source
    assert "HOLOINDEX_QUERY_READONLY" in source
