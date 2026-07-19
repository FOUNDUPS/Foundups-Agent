"""Adversarial tests for the CLI/WRE maintenance transaction boundary."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import holo_index.maintenance_session as maintenance_module
from holo_index.freshness_receipt import (
    BASELINE_QUERY_COLLECTIONS,
    evaluate_freshness_for_paths,
    freshness_receipt_path,
    load_freshness_receipt,
    write_freshness_receipt,
)
from holo_index.maintenance_lock import maintenance_lock_path, probe_maintenance_lock
from holo_index.maintenance_session import MaintenanceSession, MaintenanceSessionError
from holo_index.source_scope import canonical_source_scope_id

SPACE_FINGERPRINT = "sha256:" + ("1" * 64)
BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40

class _Collection:
    def __init__(self, name: str, count: int = 2) -> None:
        self.name = name
        self._count = count
        self.metadata = {
            "embedding_backend": "sentence_transformers",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
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
                {"path": f"{self.name}/item_{index}.py"}
                for index in range(self._count)
            ],
            "embeddings": [
                [float(index), float(index + 1)] for index in range(self._count)
            ],
        }


def _holo() -> SimpleNamespace:
    names = {
        "code_collection": "navigation_code",
        "wsp_collection": "navigation_wsp",
        "test_collection": "navigation_tests",
        "skill_collection": "navigation_skills",
        "symbol_collection": "navigation_symbols",
        "docs_collection": "navigation_docs",
        "knowledge_collection": "navigation_knowledge",
        "work_ledger_collection": "navigation_work_ledger",
        "vocabulary_collection": "navigation_vocabulary",
    }
    return SimpleNamespace(
        **{attribute: _Collection(name) for attribute, name in names.items()},
        index_embedding_backend="sentence_transformers",
        index_embedding_model_id="sentence-transformers/all-MiniLM-L6-v2",
        index_embedding_space_fingerprint=SPACE_FINGERPRINT,
    )


def _attach_chroma_client(
    holo: SimpleNamespace,
    lifecycle: list[str],
    label: str,
) -> None:
    class ChromaClient:
        __module__ = "chromadb.api.client"

        def __init__(self) -> None:
            self._system = SimpleNamespace(
                stop=lambda: lifecycle.append(f"{label}_stopped")
            )

        @staticmethod
        def clear_system_cache() -> None:
            lifecycle.append(f"{label}_cache_cleared")

    holo.client = ChromaClient()


def _clean_state(head: str = "abc123") -> SimpleNamespace:
    return SimpleNamespace(proven_clean=True, head_sha=head, error="")


def _proofs(*names: str) -> dict[str, SimpleNamespace]:
    return {
        name: SimpleNamespace(
            complete=True,
            collection_name=name,
            indexed_count=2,
            source_manifest_digest="sha256:" + ("a" * 64),
            source_scope_id=canonical_source_scope_id(name),
        )
        for name in names
    }


def _manifest_probe(_holo, names) -> dict[str, SimpleNamespace]:
    return {
        name: SimpleNamespace(
            digest="sha256:" + ("a" * 64),
            source_scope_id=canonical_source_scope_id(name),
        )
        for name in names
    }


@pytest.fixture(autouse=True)
def _canonical_manifest_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        maintenance_module,
        "probe_canonical_source_manifests",
        _manifest_probe,
    )


def _seed_baseline(tmp_path: Path) -> None:
    session = MaintenanceSession.begin(
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
        planned_collections=BASELINE_QUERY_COLLECTIONS,
        repository_state_reader=lambda _root: _clean_state(BASE_SHA),
    )
    session.complete(
        _holo(),
        refreshed_collections=BASELINE_QUERY_COLLECTIONS,
        source="baseline",
        refresh_proofs=_proofs(*BASELINE_QUERY_COLLECTIONS),
    )
    session.close()


def _targeted_session(tmp_path: Path) -> MaintenanceSession:
    return MaintenanceSession.begin(
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
        planned_collections={"navigation_code"},
        repository_state_reader=lambda _root: _clean_state(HEAD_SHA),
    )


def test_session_invalidates_before_work_and_publishes_only_full_plan(
    tmp_path: Path,
) -> None:
    def reader(_root: Path):
        return _clean_state()

    session = MaintenanceSession.begin(
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
        planned_collections={"navigation_code", "navigation_wsp"},
        repository_state_reader=reader,
    )

    assert probe_maintenance_lock(maintenance_lock_path(tmp_path / "ssd")).held
    invalid = load_freshness_receipt(freshness_receipt_path(tmp_path / "ssd"))
    invalid_by_name = {entry.name: entry for entry in invalid.collections}
    assert invalid_by_name["navigation_code"].verification == "IN_PROGRESS"
    assert invalid_by_name["navigation_wsp"].verification == "IN_PROGRESS"

    receipt = session.complete(
        _holo(),
        refreshed_collections={"navigation_code", "navigation_wsp"},
        source="test",
        refresh_proofs=_proofs("navigation_code", "navigation_wsp"),
    )
    session.close()

    by_name = {entry.name: entry for entry in receipt.collections}
    assert by_name["navigation_code"].verification == "PASS"
    assert by_name["navigation_wsp"].verification == "PASS"
    assert probe_maintenance_lock(maintenance_lock_path(tmp_path / "ssd")).clear


def test_dirty_repository_refuses_before_creating_storage(tmp_path: Path) -> None:
    dirty = SimpleNamespace(
        proven_clean=False,
        head_sha="abc123",
        error="HOLOINDEX_REPOSITORY_DIRTY",
    )
    with pytest.raises(MaintenanceSessionError, match="HOLOINDEX_REPOSITORY_DIRTY"):
        MaintenanceSession.begin(
            ssd_path=tmp_path / "ssd",
            repo_root=tmp_path / "repo",
            planned_collections={"navigation_code"},
            repository_state_reader=lambda _root: dirty,
        )

    assert not (tmp_path / "ssd").exists()


def test_incomplete_plan_leaves_published_invalidation(tmp_path: Path) -> None:
    session = MaintenanceSession.begin(
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
        planned_collections={"navigation_code", "navigation_wsp"},
        repository_state_reader=lambda _root: _clean_state(),
    )

    with pytest.raises(MaintenanceSessionError, match="HOLOINDEX_MAINTENANCE_INCOMPLETE"):
        session.complete(
            _holo(),
            refreshed_collections={"navigation_code"},
            source="test",
            refresh_proofs=_proofs("navigation_code"),
        )
    session.close()

    receipt = load_freshness_receipt(freshness_receipt_path(tmp_path / "ssd"))
    by_name = {entry.name: entry for entry in receipt.collections}
    assert by_name["navigation_code"].verification == "IN_PROGRESS"
    assert by_name["navigation_wsp"].verification == "IN_PROGRESS"


def test_narrowed_source_scope_cannot_publish_pass(tmp_path: Path) -> None:
    session = MaintenanceSession.begin(
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
        planned_collections={"navigation_symbols"},
        repository_state_reader=lambda _root: _clean_state(),
    )
    proofs = _proofs("navigation_symbols")
    proofs["navigation_symbols"].source_scope_id = (
        "holoindex.navigation_symbols.modules-only.v1"
    )

    with pytest.raises(
        MaintenanceSessionError,
        match="HOLOINDEX_MAINTENANCE_SOURCE_PROOF_INCOMPLETE",
    ):
        session.complete(
            _holo(),
            refreshed_collections={"navigation_symbols"},
            source="test",
            refresh_proofs=proofs,
        )
    session.close()

    receipt = load_freshness_receipt(freshness_receipt_path(tmp_path / "ssd"))
    symbols = next(
        entry
        for entry in receipt.collections
        if entry.name == "navigation_symbols"
    )
    assert symbols.proof_kind == "invalidated"


def test_final_receipt_failure_never_restores_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MaintenanceSession.begin(
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
        planned_collections={"navigation_code"},
        repository_state_reader=lambda _root: _clean_state(),
    )
    monkeypatch.setattr(
        maintenance_module,
        "write_freshness_receipt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    with pytest.raises(
        MaintenanceSessionError,
        match="HOLOINDEX_MAINTENANCE_RECEIPT_WRITE_FAILED",
    ):
        session.complete(
            _holo(),
            refreshed_collections={"navigation_code"},
            source="test",
            refresh_proofs=_proofs("navigation_code"),
        )
    session.close()

    receipt = load_freshness_receipt(freshness_receipt_path(tmp_path / "ssd"))
    code = next(entry for entry in receipt.collections if entry.name == "navigation_code")
    assert code.verification == "IN_PROGRESS"


def test_repository_head_change_blocks_final_pass(tmp_path: Path) -> None:
    states = iter((_clean_state("abc123"), _clean_state("def456")))
    session = MaintenanceSession.begin(
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
        planned_collections={"navigation_code"},
        repository_state_reader=lambda _root: next(states),
    )

    with pytest.raises(
        MaintenanceSessionError,
        match="HOLOINDEX_REPOSITORY_HEAD_CHANGED",
    ):
        session.complete(
            _holo(),
            refreshed_collections={"navigation_code"},
            source="test",
            refresh_proofs=_proofs("navigation_code"),
        )
    session.close()


def test_targeted_refresh_carries_only_verified_unchanged_collections(
    tmp_path: Path,
) -> None:
    _seed_baseline(tmp_path)
    baseline = load_freshness_receipt(freshness_receipt_path(tmp_path / "ssd"))
    session = _targeted_session(tmp_path)
    receipt = session.complete(
        _holo(),
        refreshed_collections={"navigation_code"},
        source="targeted",
        refresh_proofs=_proofs("navigation_code"),
    )
    session.close()

    by_name = {entry.name: entry for entry in receipt.collections}
    carried = BASELINE_QUERY_COLLECTIONS.difference({"navigation_code"})
    assert all(by_name[name].repo_head_sha == HEAD_SHA for name in carried)
    assert all(
        by_name[name].proof_kind == "verified_unchanged_source_manifest"
        for name in carried
    )
    assert all(by_name[name].carried_from_repo_head_sha == BASE_SHA for name in carried)
    assert all(
        by_name[name].carried_from_generation_id == baseline.generation_id
        for name in carried
    )
    check = evaluate_freshness_for_paths(
        receipt,
        (
            "NAVIGATION.py",
            "modules/example/src/example.py",
            "WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md",
            "WSP_knowledge/WSP_Test_Registry.json",
            "modules/example/SKILLz.md",
            "modules/example/README.md",
            "WSP_knowledge/docs/Papers/example.md",
        ),
        expected_repo_head_sha=HEAD_SHA,
    )
    assert check.ok is True


def test_targeted_refresh_rejects_changed_source_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_baseline(tmp_path)

    def changed_probe(holo, names):
        manifests = _manifest_probe(holo, names)
        manifests["navigation_wsp"] = SimpleNamespace(
            digest="sha256:" + ("f" * 64),
            source_scope_id=canonical_source_scope_id("navigation_wsp"),
        )
        return manifests

    monkeypatch.setattr(
        maintenance_module,
        "probe_canonical_source_manifests",
        changed_probe,
    )
    session = _targeted_session(tmp_path)
    with pytest.raises(
        MaintenanceSessionError,
        match="HOLOINDEX_CARRY_FORWARD_PROOF_FAILED",
    ):
        session.complete(
            _holo(),
            refreshed_collections={"navigation_code"},
            source="targeted",
            refresh_proofs=_proofs("navigation_code"),
        )
    session.close()


def test_refreshed_collection_rejects_claimed_manifest_mismatch(
    tmp_path: Path,
) -> None:
    session = MaintenanceSession.begin(
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
        planned_collections={"navigation_code"},
        repository_state_reader=lambda _root: _clean_state(HEAD_SHA),
    )
    proofs = _proofs("navigation_code")
    proofs["navigation_code"].source_manifest_digest = "sha256:" + ("f" * 64)

    with pytest.raises(
        MaintenanceSessionError,
        match="HOLOINDEX_REFRESH_SOURCE_MANIFEST_MISMATCH",
    ):
        session.complete(
            _holo(),
            refreshed_collections={"navigation_code"},
            source="targeted",
            refresh_proofs=proofs,
        )
    session.close()


def test_targeted_refresh_rejects_collection_snapshot_mutation(tmp_path: Path) -> None:
    _seed_baseline(tmp_path)
    session = _targeted_session(tmp_path)
    holo = _holo()
    holo.wsp_collection._count = 3
    with pytest.raises(
        MaintenanceSessionError,
        match="HOLOINDEX_FINAL_COLLECTION_SNAPSHOT_MISMATCH",
    ):
        session.complete(
            holo,
            refreshed_collections={"navigation_code"},
            source="targeted",
            refresh_proofs=_proofs("navigation_code"),
        )
    session.close()


@pytest.mark.parametrize("mutated_field", ("documents", "metadatas", "embeddings"))
def test_targeted_refresh_rejects_collection_content_mutation(
    tmp_path: Path,
    mutated_field: str,
) -> None:
    _seed_baseline(tmp_path)
    session = _targeted_session(tmp_path)
    holo = _holo()
    original_get = holo.wsp_collection.get

    def mutated_snapshot(include=None):
        snapshot = original_get(include=include)
        snapshot[mutated_field][0] = (
            {"path": "navigation_wsp/tampered.py"}
            if mutated_field == "metadatas"
            else [99.0, 100.0]
            if mutated_field == "embeddings"
            else "tampered document"
        )
        return snapshot

    holo.wsp_collection.get = mutated_snapshot
    with pytest.raises(
        MaintenanceSessionError,
        match="HOLOINDEX_FINAL_COLLECTION_SNAPSHOT_MISMATCH",
    ):
        session.complete(
            holo,
            refreshed_collections={"navigation_code"},
            source="targeted",
            refresh_proofs=_proofs("navigation_code"),
        )
    session.close()


def test_final_snapshot_recheck_blocks_post_proof_mutation(tmp_path: Path) -> None:
    session = MaintenanceSession.begin(
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
        planned_collections={"navigation_code"},
        repository_state_reader=lambda _root: _clean_state(HEAD_SHA),
    )
    holo = _holo()
    original_get = holo.code_collection.get
    calls = 0

    def changing_snapshot(include=None):
        nonlocal calls
        calls += 1
        snapshot = original_get(include=include)
        if calls > 1:
            snapshot["documents"][0] = "changed after receipt assembly"
        return snapshot

    holo.code_collection.get = changing_snapshot
    with pytest.raises(
        MaintenanceSessionError,
        match="HOLOINDEX_FINAL_COLLECTION_SNAPSHOT_MISMATCH",
    ):
        session.complete(
            holo,
            refreshed_collections={"navigation_code"},
            source="targeted",
            refresh_proofs=_proofs("navigation_code"),
        )
    session.close()

    invalidation = load_freshness_receipt(freshness_receipt_path(tmp_path / "ssd"))
    code = next(
        entry for entry in invalidation.collections if entry.name == "navigation_code"
    )
    assert code.verification == "IN_PROGRESS"


def test_real_client_routes_final_snapshot_check_to_isolated_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MaintenanceSession.begin(
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
        planned_collections={"navigation_code"},
        repository_state_reader=lambda _root: _clean_state(HEAD_SHA),
    )
    holo = _holo()
    calls = []
    lifecycle = []

    class ChromaClient:
        __module__ = "chromadb.api.client"

        def __init__(self) -> None:
            self._system = SimpleNamespace(
                stop=lambda: lifecycle.append("writer_stopped")
            )

        @staticmethod
        def clear_system_cache() -> None:
            lifecycle.append("cache_cleared")

    holo.client = ChromaClient()
    monkeypatch.setattr(
        maintenance_module,
        "open_persisted_collection_view",
        lambda _ssd: lifecycle.append("persisted_view_opened") or holo,
    )
    monkeypatch.setattr(
        maintenance_module,
        "verify_collection_snapshots_isolated",
        lambda receipt, **kwargs: (
            lifecycle.append("isolated_probe"),
            calls.append((receipt, kwargs)),
            [],
        )[-1],
    )

    receipt = session.complete(
        holo,
        refreshed_collections={"navigation_code"},
        source="targeted",
        refresh_proofs=_proofs("navigation_code"),
    )
    session.close()

    assert receipt.source == "targeted"
    assert len(calls) == 1
    assert lifecycle == [
        "writer_stopped",
        "cache_cleared",
        "persisted_view_opened",
        "writer_stopped",
        "cache_cleared",
        "isolated_probe",
    ]
    assert calls[0][1]["ssd_path"] == tmp_path / "ssd"
    assert calls[0][1]["repo_root"] == tmp_path / "repo"


def test_persisted_proof_view_finalizes_when_receipt_build_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MaintenanceSession.begin(
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
        planned_collections={"navigation_code"},
        repository_state_reader=lambda _root: _clean_state(HEAD_SHA),
    )
    lifecycle: list[str] = []
    writer = _holo()
    proof = _holo()
    _attach_chroma_client(writer, lifecycle, "writer")
    _attach_chroma_client(proof, lifecycle, "proof")
    monkeypatch.setattr(
        maintenance_module,
        "open_persisted_collection_view",
        lambda _ssd: lifecycle.append("persisted_view_opened") or proof,
    )
    monkeypatch.setattr(
        maintenance_module,
        "_build_completed_receipt",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("build failed")),
    )

    with pytest.raises(RuntimeError, match="build failed"):
        session.complete(
            writer,
            refreshed_collections={"navigation_code"},
            source="targeted",
            refresh_proofs=_proofs("navigation_code"),
        )
    session.close()

    assert lifecycle == [
        "writer_stopped",
        "writer_cache_cleared",
        "persisted_view_opened",
        "proof_stopped",
        "proof_cache_cleared",
    ]


def test_persisted_proof_view_finalizes_when_repository_head_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MaintenanceSession.begin(
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
        planned_collections={"navigation_code"},
        repository_state_reader=lambda _root: _clean_state(HEAD_SHA),
    )
    states = iter((HEAD_SHA, "c" * 40))
    session._repository_state_reader = lambda _root: _clean_state(next(states))
    lifecycle: list[str] = []
    writer = _holo()
    proof = _holo()
    _attach_chroma_client(writer, lifecycle, "writer")
    _attach_chroma_client(proof, lifecycle, "proof")
    monkeypatch.setattr(
        maintenance_module,
        "open_persisted_collection_view",
        lambda _ssd: lifecycle.append("persisted_view_opened") or proof,
    )

    with pytest.raises(
        MaintenanceSessionError,
        match="HOLOINDEX_REPOSITORY_HEAD_CHANGED",
    ):
        session.complete(
            writer,
            refreshed_collections={"navigation_code"},
            source="targeted",
            refresh_proofs=_proofs("navigation_code"),
        )
    session.close()

    assert lifecycle == [
        "writer_stopped",
        "writer_cache_cleared",
        "persisted_view_opened",
        "proof_stopped",
        "proof_cache_cleared",
    ]


def test_serialized_carry_forward_tampering_fails_query_admission(
    tmp_path: Path,
) -> None:
    _seed_baseline(tmp_path)
    session = _targeted_session(tmp_path)
    receipt = session.complete(
        _holo(),
        refreshed_collections={"navigation_code"},
        source="targeted",
        refresh_proofs=_proofs("navigation_code"),
    )
    session.close()
    serialized = receipt.to_dict()
    carried = next(
        entry
        for entry in serialized["collections"]
        if entry["name"] == "navigation_wsp"
    )
    carried["carry_forward_evidence_digest"] = "sha256:" + ("f" * 64)

    result = evaluate_freshness_for_paths(
        serialized,
        ["WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md"],
        expected_repo_head_sha=HEAD_SHA,
    )

    assert result.ok is False
    assert "invalid_freshness_receipt_integrity" in result.reasons


def test_full_refresh_migrates_obsolete_receipt_schema(tmp_path: Path) -> None:
    _seed_baseline(tmp_path)
    path = freshness_receipt_path(tmp_path / "ssd")
    obsolete = replace(load_freshness_receipt(path), schema_version="v1-obsolete")
    write_freshness_receipt(obsolete, path)

    session = MaintenanceSession.begin(
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
        planned_collections=BASELINE_QUERY_COLLECTIONS,
        repository_state_reader=lambda _root: _clean_state(HEAD_SHA),
    )
    receipt = session.complete(
        _holo(),
        refreshed_collections=BASELINE_QUERY_COLLECTIONS,
        source="full_migration",
        refresh_proofs=_proofs(*BASELINE_QUERY_COLLECTIONS),
    )
    session.close()

    assert receipt.base_generation_id == ""
    assert all(
        entry.verification == "PASS"
        for entry in receipt.collections
        if entry.name in BASELINE_QUERY_COLLECTIONS
    )


def test_targeted_refresh_rejects_policy_environment_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_baseline(tmp_path)
    monkeypatch.setenv("HOLO_SYMBOL_ROOTS", "modules")
    session = _targeted_session(tmp_path)
    with pytest.raises(
        MaintenanceSessionError,
        match="carry_forward_policy_changed:navigation_symbols",
    ):
        session.complete(
            _holo(),
            refreshed_collections={"navigation_code"},
            source="targeted",
            refresh_proofs=_proofs("navigation_code"),
        )
    session.close()


def test_targeted_refresh_rejects_source_probe_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_baseline(tmp_path)

    def fail_probe(_holo, _names):
        raise RuntimeError("source probe failed")

    monkeypatch.setattr(
        maintenance_module,
        "probe_canonical_source_manifests",
        fail_probe,
    )
    session = _targeted_session(tmp_path)
    with pytest.raises(
        MaintenanceSessionError,
        match="HOLOINDEX_REFRESH_SOURCE_PROBE_FAILED",
    ):
        session.complete(
            _holo(),
            refreshed_collections={"navigation_code"},
            source="targeted",
            refresh_proofs=_proofs("navigation_code"),
        )
    session.close()


def test_targeted_refresh_rejects_tampered_base_generation(tmp_path: Path) -> None:
    _seed_baseline(tmp_path)
    path = freshness_receipt_path(tmp_path / "ssd")
    receipt = load_freshness_receipt(path)
    receipt.collections[0] = receipt.collections[0].__class__(
        **{
            **receipt.collections[0].__dict__,
            "source_manifest_digest": "sha256:" + ("f" * 64),
        }
    )
    write_freshness_receipt(receipt, path)

    with pytest.raises(
        MaintenanceSessionError,
        match="HOLOINDEX_BASE_FRESHNESS_RECEIPT_INVALID",
    ):
        _targeted_session(tmp_path)


@pytest.mark.parametrize("field", ("repo_root", "ssd_path"))
def test_targeted_refresh_rejects_cross_store_base_receipt(
    tmp_path: Path,
    field: str,
) -> None:
    _seed_baseline(tmp_path)
    path = freshness_receipt_path(tmp_path / "ssd")
    receipt = load_freshness_receipt(path)
    receipt = replace(receipt, **{field: str(tmp_path / "different" / field)})
    write_freshness_receipt(receipt, path)

    with pytest.raises(
        MaintenanceSessionError,
        match="HOLOINDEX_BASE_FRESHNESS_RECEIPT_INVALID",
    ):
        _targeted_session(tmp_path)


@pytest.mark.parametrize(
    ("backend", "fingerprint"),
    [
        ("turboquant_onnx_int8", SPACE_FINGERPRINT),
        ("sentence_transformers", ""),
    ],
)
def test_noncanonical_embedding_space_cannot_publish_pass(
    tmp_path: Path,
    backend: str,
    fingerprint: str,
) -> None:
    session = MaintenanceSession.begin(
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
        planned_collections={"navigation_code"},
        repository_state_reader=lambda _root: _clean_state(),
    )
    holo = _holo()
    holo.index_embedding_backend = backend
    holo.index_embedding_space_fingerprint = fingerprint
    holo.code_collection.metadata["embedding_backend"] = backend
    holo.code_collection.metadata["embedding_space_fingerprint"] = fingerprint
    with pytest.raises(
        MaintenanceSessionError, match="HOLOINDEX_MAINTENANCE_PROOF_FAILED"
    ):
        session.complete(
            holo,
            refreshed_collections={"navigation_code"},
            source="test",
            refresh_proofs=_proofs("navigation_code"),
        )
    session.close()
