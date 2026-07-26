"""Tests for HOLOINDEX_FRESHNESS_RECEIPT_PHASE1."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from holo_index.freshness_receipt import (
    ALL_COLLECTIONS,
    SCHEMA_VERSION,
    build_freshness_receipt,
    build_maintenance_invalidation,
    collections_for_changed_paths,
    collections_for_path,
    collection_snapshot_matches_entry,
    evaluate_freshness_for_paths,
    freshness_receipt_path,
    load_freshness_receipt,
    publish_maintenance_invalidation,
    write_freshness_receipt,
)
from holo_index.maintenance_lock import (
    AUTHORITY_BLOCK_MARKER_CONTENT,
    MaintenanceLeaseBusy,
    acquire_authority_update_lease,
    acquire_maintenance_lease,
    authority_block_marker_path,
    authority_block_marker_valid,
    authority_update_lock_path,
    maintenance_lock_path,
    probe_maintenance_lock,
)
from holo_index.source_scope import canonical_source_scope_id

REPO_ROOT = Path(__file__).resolve().parents[2]
SPACE_FINGERPRINT = "sha256:" + ("1" * 64)


class CountCollection:
    def __init__(self, count: int):
        self._count = count

    def count(self) -> int:
        return self._count


class SnapshotCollection:
    def __init__(self, name: str, count: int):
        self.name = name
        self._count = count
        self.metadata = {
            "embedding_backend": "test-embedding",
            "embedding_model": "test-model",
            "embedding_space_fingerprint": SPACE_FINGERPRINT,
        }

    def count(self) -> int:
        return self._count

    def get(self, include=None):
        return {
            "ids": [f"{self.name}:{index}" for index in range(self._count)],
            "documents": [
                f"document:{self.name}:{index}" for index in range(self._count)
            ],
            "metadatas": [
                {"path": f"{self.name}/item_{index}.txt"}
                for index in range(self._count)
            ],
            "embeddings": [[float(index)] for index in range(self._count)],
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
    return SimpleNamespace(
        **values,
        index_embedding_backend="test-embedding",
        index_embedding_model_id="test-model",
        index_embedding_space_fingerprint=SPACE_FINGERPRINT,
    )


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
    assert all(entry.embedding_model == "test-model" for entry in receipt.collections)
    assert all(
        entry.embedding_space_fingerprint == SPACE_FINGERPRINT
        for entry in receipt.collections
    )
    for entry in receipt.collections:
        _assert_sha256_digest(entry.source_manifest_digest)
        _assert_sha256_digest(entry.indexed_paths_digest)
        _assert_sha256_digest(entry.removed_paths_digest)


def test_snapshot_verification_uses_fresh_client_collection_handle(
    tmp_path: Path,
) -> None:
    baseline_holo = _holo()
    receipt = build_freshness_receipt(
        baseline_holo,
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="manual_index",
        generated_at="2026-07-19T00:00:00+00:00",
        repo_head_sha="abc123",
    )
    entry = next(
        value for value in receipt.collections if value.name == "navigation_code"
    )
    stale = SnapshotCollection("navigation_code", 3)
    stale.get = lambda include=None: {
        **SnapshotCollection("navigation_code", 3).get(include=include),
        "documents": ["stale", "stale", "stale"],
    }
    persisted = SnapshotCollection("navigation_code", 3)
    candidate = _holo()
    candidate.code_collection = stale
    lookups: list[tuple[str, object]] = []

    def get_collection(name: str, *, embedding_function):
        lookups.append((name, embedding_function))
        return persisted if name == "navigation_code" else None

    candidate.client = SimpleNamespace(
        get_collection=get_collection
    )

    assert collection_snapshot_matches_entry(candidate, "navigation_code", entry)
    assert lookups == [("navigation_code", None)]

    candidate.client = SimpleNamespace(
        get_collection=lambda _name: (_ for _ in ()).throw(RuntimeError("unavailable"))
    )
    assert not collection_snapshot_matches_entry(candidate, "navigation_code", entry)

    persisted.get = lambda include=None: {
        **SnapshotCollection("navigation_code", 3).get(include=include),
        "documents": ["mutated", "mutated", "mutated"],
    }
    candidate.client = SimpleNamespace(get_collection=lambda _name: persisted)
    assert not collection_snapshot_matches_entry(candidate, "navigation_code", entry)


def test_receipt_construction_uses_indexer_write_handle(
    tmp_path: Path,
) -> None:
    candidate = _holo()
    client_calls = 0

    def stale_persisted_handle(_name: str):
        nonlocal client_calls
        client_calls += 1
        return SnapshotCollection("navigation_code", 2)

    candidate.client = SimpleNamespace(get_collection=stale_persisted_handle)
    receipt = build_freshness_receipt(
        candidate,
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="manual_index",
        generated_at="2026-07-19T00:00:00+00:00",
        repo_head_sha="abc123",
    )
    code = next(
        value for value in receipt.collections if value.name == "navigation_code"
    )

    assert code.count == 3
    assert client_calls == 0


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
    assert check.stale_collections == [
        "navigation_docs",
        "navigation_work_ledger",
        "navigation_wsp",
    ]
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
    assert check.stale_collections == [
        "navigation_docs",
        "navigation_work_ledger",
    ]
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


@pytest.mark.parametrize(
    ("scope", "field", "value"),
    (
        ("receipt", "generated_at", "2026-07-13T00:00:00+00:00"),
        ("receipt", "repo_root", "O:/forged"),
        ("receipt", "ssd_path", "O:/forged-index"),
        ("receipt", "source", "forged-source"),
        ("collection", "last_indexed_at", "2026-07-13T00:00:00+00:00"),
        ("collection", "source", "forged-source"),
        ("collection", "schema_version", "holoindex_collection_freshness.v1"),
    ),
)
def test_query_rejects_tampering_of_any_generation_bound_field(
    tmp_path: Path,
    scope: str,
    field: str,
    value: str,
) -> None:
    receipt = build_freshness_receipt(
        _holo(),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="manual_index",
        generated_at="2026-07-12T00:00:00+00:00",
        repo_head_sha="abc123",
        refresh_source_manifests={
            "navigation_symbols": "sha256:" + ("a" * 64),
        },
        refresh_source_scopes={
            "navigation_symbols": canonical_source_scope_id("navigation_symbols"),
        },
    ).to_dict()
    target = receipt if scope == "receipt" else receipt["collections"][4]
    target[field] = value

    result = evaluate_freshness_for_paths(
        receipt,
        ["modules/example/src/example.py"],
        expected_repo_head_sha="abc123",
    )

    assert result.ok is False
    assert "invalid_freshness_receipt_integrity" in result.reasons


def _assert_scoped_refresh_truth(refreshed) -> None:
    wsp_check = evaluate_freshness_for_paths(
        refreshed,
        ["WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md"],
        expected_repo_head_sha="sha-b",
    )
    knowledge_check = evaluate_freshness_for_paths(
        refreshed,
        ["WSP_knowledge/docs/Papers/PQN_Deep_Dive.md"],
        expected_repo_head_sha="sha-b",
    )
    test_check = evaluate_freshness_for_paths(
        refreshed,
        ["modules/example/tests/test_example.py"],
        expected_repo_head_sha="sha-b",
    )
    assert "stale_collection_sha:navigation_wsp" in wsp_check.reasons
    assert "stale_collection_sha:navigation_knowledge" in knowledge_check.reasons
    assert test_check.ok is False
    assert "stale_collection_sha:navigation_symbols" in test_check.reasons


def test_changed_path_mapping_covers_overlapping_source_sets() -> None:
    assert collections_for_path("modules/example/tests/test_runtime.py") == {
        "navigation_symbols",
        "navigation_tests",
    }
    assert collections_for_path("modules/example/SKILLz.md") == {
        "navigation_docs",
        "navigation_skills",
    }
    assert collections_for_path("WSP_knowledge/WSP_Test_Registry.json") == {
        "navigation_tests",
    }
    assert collections_for_path(
        "docs/0102_session_briefings/work_ledger.schema.json"
    ) == {"navigation_work_ledger"}
    assert collections_for_path(
        "docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md"
    ) == {"navigation_docs", "navigation_work_ledger"}
    assert collections_for_path("public/runtime.mjs") == {"navigation_code"}
    assert collections_for_path("public/worker.cjs") == {"navigation_code"}
    assert collections_for_path("WSP_framework/src/README.md") == set()


def test_test_only_refresh_preserves_prior_wsp_and_knowledge_entries(
    tmp_path: Path,
) -> None:
    base = build_freshness_receipt(
        _holo(),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="full_refresh",
        generated_at="2026-07-12T00:00:00+00:00",
        repo_head_sha="sha-a",
    )

    refreshed = build_freshness_receipt(
        _holo(**{"navigation_tests": 4}),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="test_only_refresh",
        generated_at="2026-07-13T00:00:00+00:00",
        repo_head_sha="sha-b",
        refreshed_collections={"navigation_tests"},
        base_receipt=base,
        refresh_source_manifests={
            "navigation_tests": "sha256:" + ("a" * 64),
        },
        refresh_source_scopes={
            "navigation_tests": canonical_source_scope_id("navigation_tests"),
        },
    )

    before = {entry.name: entry for entry in base.collections}
    after = {entry.name: entry for entry in refreshed.collections}
    assert after["navigation_tests"].repo_head_sha == "sha-b"
    assert after["navigation_wsp"] == before["navigation_wsp"]
    assert after["navigation_knowledge"] == before["navigation_knowledge"]
    assert refreshed.base_generation_id == base.generation_id

    _assert_scoped_refresh_truth(refreshed)


def test_complete_manifest_without_canonical_scope_fails_closed(
    tmp_path: Path,
) -> None:
    receipt = build_freshness_receipt(
        _holo(),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="test_refresh",
        repo_head_sha="sha-b",
        refreshed_collections={"navigation_tests"},
        refresh_source_manifests={
            "navigation_tests": "sha256:" + ("a" * 64),
        },
        refresh_source_scopes={
            "navigation_tests": "holoindex.navigation_tests.narrowed.v1",
        },
    )

    check = evaluate_freshness_for_paths(
        receipt,
        ["modules/example/tests/test_example.py"],
        expected_repo_head_sha="sha-b",
    )

    assert check.ok is False
    assert "collection_source_scope_mismatch:navigation_tests" in check.reasons


def test_complete_manifest_without_policy_digest_fails_closed(
    tmp_path: Path,
) -> None:
    receipt = build_freshness_receipt(
        _holo(),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="test_refresh",
        repo_head_sha="sha-b",
        refreshed_collections={"navigation_tests"},
        refresh_source_manifests={
            "navigation_tests": "sha256:" + ("a" * 64),
        },
        refresh_source_scopes={
            "navigation_tests": canonical_source_scope_id("navigation_tests"),
        },
    )

    check = evaluate_freshness_for_paths(
        receipt,
        ["modules/example/tests/test_example.py"],
        expected_repo_head_sha="sha-b",
    )

    assert check.ok is False
    assert "collection_source_policy_digest_invalid:navigation_tests" in check.reasons


def test_partial_refresh_without_base_marks_untouched_collections_unverified(
    tmp_path: Path,
) -> None:
    receipt = build_freshness_receipt(
        _holo(),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="test_only_refresh",
        repo_head_sha="sha-b",
        refreshed_collections={"navigation_tests"},
    )

    entries = {entry.name: entry for entry in receipt.collections}
    assert entries["navigation_tests"].verification == "PASS"
    assert entries["navigation_wsp"].status == "unverified"
    assert entries["navigation_wsp"].repo_head_sha == ""
    assert entries["navigation_wsp"].verification == "UNVERIFIED"


def test_partial_refresh_rejects_unknown_collection_name(tmp_path: Path) -> None:
    try:
        build_freshness_receipt(
            _holo(),
            ssd_path=tmp_path,
            repo_root=REPO_ROOT,
            source="bad_refresh",
            refreshed_collections={"navigation_typo"},
        )
    except ValueError as exc:
        assert "navigation_typo" in str(exc)
    else:
        raise AssertionError("unknown collection must fail closed")


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
    assert check.stale_collections == ["navigation_docs", "navigation_skills"]
    assert "collection_verification_not_pass:navigation_skills" in check.reasons
    assert "collection_manifest_missing:navigation_skills" in check.reasons


def test_cli_index_state_writer_emits_freshness_receipt_contract() -> None:
    cli_source = (REPO_ROOT / "holo_index" / "_cli_main.py").read_text(
        encoding="utf-8"
    )
    session_source = (
        REPO_ROOT / "holo_index" / "maintenance_session.py"
    ).read_text(encoding="utf-8")

    assert cli_source.index("MaintenanceSession.begin(") < cli_source.index(
        "holo = HoloIndex("
    )
    assert "maintenance_session.complete(" in cli_source
    assert (
        '"freshness_receipt_path": str(maintenance_session.receipt_path)'
        in cli_source
    )
    assert "publish_maintenance_invalidation(" in session_source
    assert "build_freshness_receipt(" in session_source
    assert "write_freshness_receipt(receipt, session.receipt_path)" in session_source
    assert "HOLOINDEX_QUERY_READONLY" in cli_source


def test_read_only_lock_probe_does_not_create_absent_path(tmp_path: Path) -> None:
    lock_path = maintenance_lock_path(tmp_path / "never-created")

    probe = probe_maintenance_lock(lock_path)

    assert probe.status == "absent"
    assert probe.clear is True
    assert lock_path.exists() is False
    assert lock_path.parent.exists() is False


def test_lock_probe_fails_closed_for_invalid_sentinel(tmp_path: Path) -> None:
    lock_path = maintenance_lock_path(tmp_path)
    lock_path.parent.mkdir(parents=True)
    lock_path.touch()

    probe = probe_maintenance_lock(lock_path)

    assert probe.status == "error"
    assert probe.clear is False
    assert probe.reason == "lock_file_invalid"


def test_maintenance_lease_is_exclusive_across_processes(tmp_path: Path) -> None:
    lock_path = maintenance_lock_path(tmp_path)
    child_source = (
        "import sys\n"
        "from holo_index.maintenance_lock import acquire_maintenance_lease\n"
        "with acquire_maintenance_lease(sys.argv[1]):\n"
        "    print('locked', flush=True)\n"
        "    sys.stdin.readline()\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-B", "-c", child_source, str(lock_path)],
        cwd=REPO_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout is not None
        assert process.stdout.readline().strip() == "locked"
        probe = probe_maintenance_lock(lock_path)
        assert probe.status == "held"
        assert probe.clear is False
        assert probe.reason == "maintenance_in_progress"
        with pytest.raises(MaintenanceLeaseBusy):
            acquire_maintenance_lease(lock_path)
    finally:
        if process.stdin is not None:
            process.stdin.write("release\n")
            process.stdin.flush()
            process.stdin.close()
        return_code = process.wait(timeout=10)
        stderr = process.stderr.read() if process.stderr is not None else ""
        assert return_code == 0, stderr

    assert probe_maintenance_lock(lock_path).status == "idle"


def test_acquiring_lease_does_not_rewrite_freshness_receipt(tmp_path: Path) -> None:
    receipt = build_freshness_receipt(
        _holo(),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="full_refresh",
        repo_head_sha="sha-a",
    )
    receipt_path = freshness_receipt_path(tmp_path)
    write_freshness_receipt(receipt, receipt_path)
    before = receipt_path.read_bytes()

    with acquire_maintenance_lease(maintenance_lock_path(tmp_path)):
        assert receipt_path.read_bytes() == before

    assert receipt_path.read_bytes() == before


def test_authority_and_maintenance_leases_are_distinct_and_can_nest(
    tmp_path: Path,
) -> None:
    assert authority_update_lock_path(tmp_path) != maintenance_lock_path(tmp_path)

    with acquire_authority_update_lease(tmp_path):
        with acquire_maintenance_lease(maintenance_lock_path(tmp_path)):
            assert authority_update_lock_path(tmp_path).exists()
            assert maintenance_lock_path(tmp_path).exists()
        assert probe_maintenance_lock(maintenance_lock_path(tmp_path)).clear


def test_authority_block_marker_requires_exact_regular_content(
    tmp_path: Path,
) -> None:
    marker = authority_block_marker_path(tmp_path)
    assert not authority_block_marker_valid(tmp_path)
    marker.write_bytes(b"wrong")
    assert not authority_block_marker_valid(tmp_path)
    marker.write_bytes(AUTHORITY_BLOCK_MARKER_CONTENT)
    assert authority_block_marker_valid(tmp_path)


def test_maintenance_invalidation_preserves_only_unplanned_proof(
    tmp_path: Path,
) -> None:
    base = build_freshness_receipt(
        _holo(),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="full_refresh",
        generated_at="2026-07-12T00:00:00+00:00",
        repo_head_sha="sha-a",
    )
    receipt_path = freshness_receipt_path(tmp_path)

    published = publish_maintenance_invalidation(
        receipt_path,
        {"navigation_symbols", "navigation_tests"},
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        base_receipt=base,
        generated_at="2026-07-13T00:00:00+00:00",
        repo_head_sha="sha-a",
    )
    loaded = load_freshness_receipt(receipt_path)

    assert loaded == published
    assert loaded.base_generation_id == base.generation_id
    assert loaded.generation_id != base.generation_id
    before = {entry.name: entry for entry in base.collections}
    after = {entry.name: entry for entry in loaded.collections}
    for name in ("navigation_symbols", "navigation_tests"):
        entry = after[name]
        assert entry.status == "maintenance_in_progress"
        assert entry.verification == "IN_PROGRESS"
        assert entry.count == 0
        assert entry.repo_head_sha == ""
        assert entry.source_manifest_digest == ""
        assert entry.indexed_paths_digest == ""
    assert after["navigation_wsp"] == before["navigation_wsp"]
    assert after["navigation_knowledge"] == before["navigation_knowledge"]

    check = evaluate_freshness_for_paths(
        loaded,
        ["modules/example/tests/test_example.py"],
        expected_repo_head_sha="sha-a",
    )
    assert check.ok is False
    assert check.stale_collections == [
        "navigation_symbols",
        "navigation_tests",
    ]
    assert "collection_not_indexed:navigation_tests" in check.reasons


def test_maintenance_invalidation_without_base_is_fully_fail_closed(
    tmp_path: Path,
) -> None:
    receipt = build_maintenance_invalidation(
        {"navigation_tests"},
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        base_receipt=None,
        repo_head_sha="sha-a",
    )
    entries = {entry.name: entry for entry in receipt.collections}

    assert entries["navigation_tests"].verification == "IN_PROGRESS"
    assert entries["navigation_wsp"].verification == "UNVERIFIED"
    assert entries["navigation_wsp"].status == "unverified"


def test_atomic_receipt_failure_keeps_previous_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = build_freshness_receipt(
        _holo(),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="first",
        repo_head_sha="sha-a",
    )
    second = build_freshness_receipt(
        _holo(**{"navigation_tests": 4}),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="second",
        repo_head_sha="sha-b",
    )
    receipt_path = freshness_receipt_path(tmp_path)
    write_freshness_receipt(first, receipt_path)

    def fail_replace(source: object, destination: object) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr("holo_index.freshness_receipt.os.replace", fail_replace)
    with pytest.raises(OSError, match="injected replace failure"):
        write_freshness_receipt(second, receipt_path)

    assert load_freshness_receipt(receipt_path) == first
    assert list(receipt_path.parent.glob(f".{receipt_path.name}.*.tmp")) == []
