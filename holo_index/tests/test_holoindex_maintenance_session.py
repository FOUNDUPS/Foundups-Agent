"""Adversarial tests for the CLI/WRE maintenance transaction boundary."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import holo_index.maintenance_session as maintenance_module
from holo_index.freshness_receipt import (
    freshness_receipt_path,
    load_freshness_receipt,
)
from holo_index.maintenance_lock import maintenance_lock_path, probe_maintenance_lock
from holo_index.maintenance_session import MaintenanceSession, MaintenanceSessionError
from holo_index.source_scope import canonical_source_scope_id

SPACE_FINGERPRINT = "sha256:" + ("1" * 64)

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
            "metadatas": [
                {"path": f"{self.name}/item_{index}.py"}
                for index in range(self._count)
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


def test_session_invalidates_before_work_and_publishes_only_full_plan(
    tmp_path: Path,
) -> None:
    reader = lambda _root: _clean_state()
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
