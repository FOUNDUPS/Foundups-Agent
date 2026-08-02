"""Tests for HOLOINDEX_EVENT_DRIVEN_INCREMENTAL_INDEX_EXECUTOR_PHASE1."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import holo_index.incremental_index_executor as executor_module
from holo_index.freshness_receipt import (
    build_freshness_receipt,
    freshness_receipt_path,
    load_freshness_receipt,
    write_freshness_receipt,
)
from holo_index.incremental_foundup_index import (
    DECISION_NO_INDEXABLE_CHANGES,
    DECISION_REJECTED,
    IncrementalFoundUpIndexPlan,
    plan_incremental_foundup_index,
)
from holo_index.incremental_index_executor import (
    BOUNDARY_REQUIRED,
    DECISION_APPLIED,
    DECISION_FAILED,
    DECISION_NOOP,
    FINAL_PROOF_FAILED,
    FINAL_RECEIPT_FAILED,
    INVALIDATION_FAILED,
    LEASE_BUSY,
    OPERATION_FAILED,
    REPOSITORY_STATE_CHANGED,
    canonical_plan_digest,
    execute_incremental_foundup_index_plan,
)
from holo_index.maintenance_lock import (
    MaintenanceLeaseBusy,
    maintenance_lock_path,
    probe_maintenance_lock,
)
from holo_index.repository_state import (
    REPOSITORY_DIRTY_CODE,
    RepositoryState,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE = REPO_ROOT / "holo_index" / "incremental_index_executor.py"
SHA_A = "a" * 40
SHA_B = "b" * 40
SPACE_FINGERPRINT = "sha256:" + ("1" * 64)


@pytest.fixture(autouse=True)
def _accept_isolated_persisted_proof(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        executor_module,
        "finalize_chroma_client",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        executor_module,
        "verify_collection_snapshots_isolated",
        lambda *_args, **_kwargs: [],
    )


class FakeCollection:
    def __init__(self, name: str):
        self.name = name
        self.metadata = {
            "embedding_backend": "sentence_transformers",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "embedding_space_fingerprint": SPACE_FINGERPRINT,
        }
        self.deleted: list[list[str]] = []
        self.added: list[dict] = []
        self.records: dict[str, dict] = {}
        self.add_calls = 0
        self.fail_add_call: int | None = None

    def delete(self, ids):
        deleted_ids = list(ids)
        self.deleted.append(deleted_ids)
        for item_id in deleted_ids:
            self.records.pop(item_id, None)

    def add(self, **kwargs):
        self.add_calls += 1
        if self.fail_add_call == self.add_calls:
            raise RuntimeError("injected_add_failure")
        self.added.append(kwargs)
        ids = kwargs.get("ids", [])
        documents = kwargs.get("documents", [])
        metadatas = kwargs.get("metadatas", [])
        embeddings = kwargs.get("embeddings", [])
        for item_id, document, metadata, embedding in zip(
            ids,
            documents,
            metadatas,
            embeddings,
        ):
            self.records[item_id] = {
                "document": document,
                "metadata": metadata,
                "embedding": embedding,
            }

    def seed(self, item_id: str, *, path: str, foundup_id: str = "paccess_001") -> None:
        self.records[item_id] = {
            "document": "legacy",
            "metadata": {"path": path, "foundup_id": foundup_id},
            "embedding": [0.0],
        }

    def count(self) -> int:
        return len(self.records)

    def get(self, include=None):
        return {
            "ids": list(self.records),
            "documents": [record["document"] for record in self.records.values()],
            "metadatas": [
                record["metadata"]
                for record in self.records.values()
            ],
            "embeddings": [record["embedding"] for record in self.records.values()],
        }


class FakeGateway:
    def __init__(self):
        self.collections: dict[str, FakeCollection] = {}
        self.embedded: list[str] = []
        self.collection_requests: list[str] = []

    def get_collection(self, name: str):
        self.collection_requests.append(name)
        return self.collections.setdefault(name, FakeCollection(name))

    def embed(self, text: str):
        self.embedded.append(text)
        return [float(len(text))]


def _holo_from_gateway(gateway: FakeGateway):
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
        values[attr_name] = gateway.get_collection(collection_name)
    return SimpleNamespace(
        **values,
        index_embedding_backend="sentence_transformers",
        index_embedding_model_id="sentence-transformers/all-MiniLM-L6-v2",
        index_embedding_space_fingerprint=SPACE_FINGERPRINT,
    )


def _repository_state(sha: str = SHA_A, *, clean: bool = True) -> RepositoryState:
    return RepositoryState(
        head_sha=sha,
        clean=clean,
        state_digest="sha256:test-state",
        error="" if clean else REPOSITORY_DIRTY_CODE,
    )


def _clean_repository_state(_repo_root: Path | str) -> RepositoryState:
    return _repository_state()


def _execute_plan(
    plan: IncrementalFoundUpIndexPlan,
    *,
    repo_root: Path,
    gateway: FakeGateway,
    holo: object | None = None,
    receipt_path: Path | None = None,
    repository_state_reader=_clean_repository_state,
):
    snapshot = holo or _holo_from_gateway(gateway)
    target_receipt = receipt_path or freshness_receipt_path(repo_root / "ssd")
    gateway.collection_requests.clear()
    return execute_incremental_foundup_index_plan(
        plan,
        repo_root=repo_root,
        gateway=gateway,
        holo_for_receipt=snapshot,
        freshness_receipt_path=target_receipt,
        repository_state_reader=repository_state_reader,
    )


def _install_complete_proof_builder(
    monkeypatch: pytest.MonkeyPatch,
    target_collections: set[str],
) -> None:
    real_builder = executor_module.build_freshness_receipt

    def build_with_complete_proof(*args, **kwargs):
        receipt = real_builder(*args, **kwargs)
        return replace(
            receipt,
            collections=[
                replace(entry, proof_kind="complete_source_manifest")
                if entry.name in target_collections
                else entry
                for entry in receipt.collections
            ],
        )

    monkeypatch.setattr(
        executor_module,
        "build_freshness_receipt",
        build_with_complete_proof,
    )


def _write_foundup_files(repo_root: Path) -> None:
    foundup_root = repo_root / "modules" / "foundups" / "paccess_001"
    (foundup_root / "src").mkdir(parents=True)
    (foundup_root / "tests").mkdir(parents=True)
    (foundup_root / "src" / "main.py").write_text("def create_foundup():\n    return True\n", encoding="utf-8")
    (foundup_root / "README.md").write_text("# pAccess\n", encoding="utf-8")
    (foundup_root / "tests" / "test_main.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")


def test_executor_mutates_scoped_upserts_then_requires_full_proof(
    tmp_path: Path,
) -> None:
    _write_foundup_files(tmp_path)
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=[
            "modules/foundups/paccess_001/src/main.py",
            "modules/foundups/paccess_001/README.md",
        ],
    )

    receipt = _execute_plan(
        plan,
        repo_root=tmp_path,
        gateway=gateway,
    )

    assert receipt.decision == DECISION_FAILED
    assert receipt.rejection_reasons == [FINAL_PROOF_FAILED]
    assert receipt.plan_digest == canonical_plan_digest(plan)
    assert receipt.operations_attempted == 2
    assert receipt.operations_applied == 2
    assert receipt.collection_mutation_performed is True
    assert set(receipt.affected_paths) == set(receipt.upserted_paths)
    assert receipt.no_full_reindex_performed is True
    assert receipt.no_runtime_reindex_performed is True
    assert set(receipt.upserted_paths) == {
        "modules/foundups/paccess_001/src/main.py",
        "modules/foundups/paccess_001/README.md",
    }
    symbol_collection = gateway.get_collection("navigation_symbols")
    docs_collection = gateway.get_collection("navigation_docs")
    assert len(symbol_collection.added) == 1
    assert symbol_collection.added[0]["metadatas"][0]["foundup_id"] == "paccess_001"
    assert docs_collection.added[0]["metadatas"][0]["path"] == "modules/foundups/paccess_001/README.md"
    assert docs_collection.added[0]["metadatas"][0][
        "source_content_digest"
    ].startswith("sha256:")


def test_incremental_publication_requires_isolated_vector_proof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_foundup_files(tmp_path)
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )
    _install_complete_proof_builder(monkeypatch, set(plan.target_collections))
    calls: list[str] = []

    def reject_probe(receipt, **_kwargs):
        calls.append(receipt.generation_id)
        raise executor_module.IsolatedSnapshotProbeError(
            "VECTOR_SEGMENT_UNAVAILABLE"
        )

    monkeypatch.setattr(
        executor_module,
        "verify_collection_snapshots_isolated",
        reject_probe,
    )

    receipt = _execute_plan(plan, repo_root=tmp_path, gateway=gateway)

    assert calls
    assert receipt.decision == DECISION_FAILED
    assert receipt.rejection_reasons == [FINAL_PROOF_FAILED]
    invalidation = load_freshness_receipt(freshness_receipt_path(tmp_path / "ssd"))
    by_name = {entry.name: entry for entry in invalidation.collections}
    assert all(
        by_name[name].verification == "IN_PROGRESS"
        for name in plan.target_collections
    )


def test_incremental_publication_rejects_reported_snapshot_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_foundup_files(tmp_path)
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )
    _install_complete_proof_builder(monkeypatch, set(plan.target_collections))
    monkeypatch.setattr(
        executor_module,
        "verify_collection_snapshots_isolated",
        lambda _receipt, **_kwargs: ["navigation_code"],
    )

    receipt = _execute_plan(plan, repo_root=tmp_path, gateway=gateway)

    assert receipt.decision == DECISION_FAILED
    assert receipt.rejection_reasons == [FINAL_PROOF_FAILED]
    invalidation = load_freshness_receipt(freshness_receipt_path(tmp_path / "ssd"))
    by_name = {entry.name: entry for entry in invalidation.collections}
    assert all(
        by_name[name].verification == "IN_PROGRESS"
        for name in plan.target_collections
    )


def test_incremental_publication_requires_writer_finalization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_foundup_files(tmp_path)
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )
    _install_complete_proof_builder(monkeypatch, set(plan.target_collections))
    probe_calls: list[str] = []
    monkeypatch.setattr(
        executor_module,
        "finalize_chroma_client",
        lambda _client: (_ for _ in ()).throw(RuntimeError("not flushed")),
    )
    monkeypatch.setattr(
        executor_module,
        "verify_collection_snapshots_isolated",
        lambda receipt, **_kwargs: probe_calls.append(receipt.generation_id),
    )

    receipt = _execute_plan(plan, repo_root=tmp_path, gateway=gateway)

    assert receipt.decision == DECISION_FAILED
    assert receipt.rejection_reasons == [FINAL_PROOF_FAILED]
    assert probe_calls == []


def test_oversize_source_is_rejected_without_partial_indexing(tmp_path: Path) -> None:
    _write_foundup_files(tmp_path)
    source = (
        tmp_path
        / "modules"
        / "foundups"
        / "paccess_001"
        / "README.md"
    )
    source.write_text("# pAccess" + chr(10) + ("x" * 64), encoding="utf-8")
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/README.md"],
    )

    receipt = execute_incremental_foundup_index_plan(
        plan,
        repo_root=tmp_path,
        gateway=gateway,
        holo_for_receipt=_holo_from_gateway(gateway),
        freshness_receipt_path=freshness_receipt_path(tmp_path / "ssd"),
        max_file_bytes=16,
        repository_state_reader=_clean_repository_state,
    )

    assert receipt.decision == DECISION_FAILED
    assert receipt.rejection_reasons == [OPERATION_FAILED]
    assert receipt.collection_mutation_performed is False
    assert gateway.get_collection("navigation_docs").added == []


def test_changed_symbol_path_replaces_all_legacy_ids_with_ast_records(tmp_path: Path) -> None:
    source_path = tmp_path / "modules" / "foundups" / "paccess_001" / "src" / "main.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        "class Builder:\n"
        "    def build(self, value):\n"
        "        return value\n\n"
        "def helper(item):\n"
        "    return item\n",
        encoding="utf-8",
    )
    repo_path = "modules/foundups/paccess_001/src/main.py"
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=[repo_path],
    )
    gateway = FakeGateway()
    collection = gateway.get_collection("navigation_symbols")
    collection.seed("sym_2048", path=f"D:/previous/worktree/{repo_path}")
    collection.seed(plan.operations[0].stable_id, path=repo_path)
    collection.seed(
        "sym_survivor",
        path="modules/foundups/paccess_001/src/other.py",
    )

    receipt = _execute_plan(
        plan,
        repo_root=tmp_path,
        gateway=gateway,
    )

    assert receipt.decision == DECISION_FAILED
    assert receipt.rejection_reasons == [FINAL_PROOF_FAILED]
    assert set(collection.deleted[0]) == {
        "sym_2048",
        plan.operations[0].stable_id,
    }
    assert "sym_survivor" in collection.records
    payload = collection.added[0]
    assert len(payload["ids"]) == 3
    assert all(item_id.startswith("hidx_nav_symbols_") for item_id in payload["ids"])
    assert {
        metadata["qualified_name"]
        for metadata in payload["metadatas"]
    } == {"Builder", "Builder.build", "helper"}
    assert all(
        metadata["path"] == repo_path
        for metadata in payload["metadatas"]
    )
    assert all("return item" not in document for document in payload["documents"])


def test_executor_mutates_delete_then_requires_full_proof(tmp_path: Path) -> None:
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        removed_paths=["modules/foundups/paccess_001/src/main.py"],
    )

    symbol_collection = gateway.get_collection("navigation_symbols")
    target_path = "modules/foundups/paccess_001/src/main.py"
    symbol_collection.seed(
        "sym_17",
        path=f"C:/old/repo/{target_path}",
        foundup_id="legacy_manifest_id",
    )
    symbol_collection.seed("sym_18", path=target_path)
    symbol_collection.seed(
        "sym_survivor",
        path="modules/foundups/paccess_001/src/other.py",
    )

    receipt = _execute_plan(
        plan,
        repo_root=tmp_path,
        gateway=gateway,
    )

    assert receipt.decision == DECISION_FAILED
    assert receipt.rejection_reasons == [FINAL_PROOF_FAILED]
    assert receipt.deleted_paths == ["modules/foundups/paccess_001/src/main.py"]
    assert set(symbol_collection.deleted[0]) == {"sym_17", "sym_18"}
    assert "sym_survivor" in symbol_collection.records
    assert gateway.embedded == []


def test_failure_after_mutation_reports_partial_execution_truth(tmp_path: Path) -> None:
    foundup_src = tmp_path / "modules" / "foundups" / "paccess_001" / "src"
    foundup_src.mkdir(parents=True)
    first_path = "modules/foundups/paccess_001/src/first.py"
    second_path = "modules/foundups/paccess_001/src/second.py"
    (foundup_src / "first.py").write_text(
        "def first():\n    return 1\n",
        encoding="utf-8",
    )
    (foundup_src / "second.py").write_text(
        "def second():\n    return 2\n",
        encoding="utf-8",
    )
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=[first_path, second_path],
    )
    gateway = FakeGateway()
    collection = gateway.get_collection("navigation_symbols")
    collection.seed("sym_second_legacy", path=f"C:/old/repo/{second_path}")
    collection.fail_add_call = 2

    receipt = _execute_plan(
        plan,
        repo_root=tmp_path,
        gateway=gateway,
    )

    assert receipt.decision == DECISION_FAILED
    assert receipt.operations_attempted == 2
    assert receipt.operations_applied == 1
    assert receipt.collection_mutation_performed is True
    assert receipt.mutation_performed is True
    assert receipt.to_dict()["mutation_performed"] is True
    assert receipt.upserted_paths == [first_path]
    assert receipt.affected_paths == [first_path, second_path]
    assert receipt.receipt_written is True
    assert receipt.freshness_invalidation_published is True
    assert receipt.rejection_reasons == [OPERATION_FAILED]
    assert "sym_second_legacy" not in collection.records
    invalid = load_freshness_receipt(
        freshness_receipt_path(tmp_path / "ssd")
    )
    by_name = {entry.name: entry for entry in invalid.collections}
    assert by_name["navigation_symbols"].verification == "IN_PROGRESS"
    assert probe_maintenance_lock(
        maintenance_lock_path(tmp_path / "ssd")
    ).status == "idle"


def test_executor_rejects_rejected_and_noop_plans(tmp_path: Path) -> None:
    gateway = FakeGateway()
    rejected = IncrementalFoundUpIndexPlan(
        schema_version="holoindex_incremental_foundup_index.v1",
        decision=DECISION_REJECTED,
        foundup_id="bad",
        foundup_root="",
        rejection_reasons=["invalid_foundup_id"],
    )
    noop = IncrementalFoundUpIndexPlan(
        schema_version="holoindex_incremental_foundup_index.v1",
        decision=DECISION_NO_INDEXABLE_CHANGES,
        foundup_id="paccess_001",
        foundup_root="modules/foundups/paccess_001",
    )

    rejected_receipt = execute_incremental_foundup_index_plan(rejected, repo_root=tmp_path, gateway=gateway)
    noop_receipt = execute_incremental_foundup_index_plan(noop, repo_root=tmp_path, gateway=gateway)

    assert rejected_receipt.decision == DECISION_FAILED
    assert "plan_rejected" in rejected_receipt.rejection_reasons
    assert noop_receipt.decision == DECISION_NOOP
    assert noop_receipt.collection_mutation_performed is False


def test_executor_fails_closed_when_changed_source_is_missing(tmp_path: Path) -> None:
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )

    receipt = _execute_plan(plan, repo_root=tmp_path, gateway=gateway)

    assert receipt.decision == DECISION_FAILED
    assert receipt.collection_mutation_performed is False
    assert receipt.operations_applied == 0
    assert receipt.affected_paths == []
    assert receipt.rejection_reasons == [OPERATION_FAILED]


def test_snapshot_only_final_receipt_is_rejected_and_invalidation_remains(
    tmp_path: Path,
) -> None:
    _write_foundup_files(tmp_path)
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )
    ssd_path = tmp_path / "ssd"
    receipt_path = freshness_receipt_path(ssd_path)

    receipt = _execute_plan(
        plan,
        repo_root=tmp_path,
        gateway=gateway,
        receipt_path=receipt_path,
    )
    loaded = load_freshness_receipt(receipt_path)

    assert receipt.decision == DECISION_FAILED
    assert receipt.rejection_reasons == [FINAL_PROOF_FAILED]
    assert receipt.receipt_written is True
    assert receipt.freshness_generation_id == loaded.generation_id
    assert loaded.source == "maintenance_in_progress"
    entries = {entry.name: entry for entry in loaded.collections}
    assert entries["navigation_symbols"].verification == "IN_PROGRESS"
    assert entries["navigation_symbols"].proof_kind == "invalidated"
    assert entries["navigation_wsp"].verification == "UNVERIFIED"


def _seed_all_collections(gateway: FakeGateway) -> None:
    for name in (
        "navigation_code",
        "navigation_wsp",
        "navigation_tests",
        "navigation_skills",
        "navigation_symbols",
        "navigation_docs",
        "navigation_knowledge",
        "navigation_work_ledger",
        "navigation_vocabulary",
    ):
        gateway.get_collection(name).add(
            ids=[f"{name}:base"],
            embeddings=[[1.0]],
            documents=["base"],
            metadatas=[{"path": f"{name}/base.txt"}],
        )


def test_executor_preserves_untouched_collection_proof_from_base_receipt(
    tmp_path: Path,
) -> None:
    _write_foundup_files(tmp_path)
    gateway = FakeGateway()
    holo = _holo_from_gateway(gateway)
    _seed_all_collections(gateway)
    ssd_path = tmp_path / "ssd"
    receipt_path = freshness_receipt_path(ssd_path)
    base = build_freshness_receipt(
        holo,
        ssd_path=ssd_path,
        repo_root=tmp_path,
        source="full_refresh",
        repo_head_sha="sha-a",
    )
    write_freshness_receipt(base, receipt_path)

    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )
    execution = _execute_plan(
        plan,
        repo_root=tmp_path,
        gateway=gateway,
        holo=holo,
        receipt_path=receipt_path,
    )
    loaded = load_freshness_receipt(receipt_path)
    before = {entry.name: entry for entry in base.collections}
    after = {entry.name: entry for entry in loaded.collections}

    assert execution.decision == DECISION_FAILED
    assert execution.rejection_reasons == [FINAL_PROOF_FAILED]
    assert after["navigation_wsp"] == before["navigation_wsp"]
    assert after["navigation_symbols"].verification == "IN_PROGRESS"
    assert after["navigation_symbols"].proof_kind == "invalidated"
    assert loaded.base_generation_id == base.generation_id


def test_planned_execution_requires_complete_maintenance_boundary(
    tmp_path: Path,
) -> None:
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )

    receipt = execute_incremental_foundup_index_plan(
        plan,
        repo_root=tmp_path,
        gateway=gateway,
    )

    assert receipt.rejection_reasons == [BOUNDARY_REQUIRED]
    assert receipt.collection_mutation_performed is False
    assert gateway.collection_requests == []


def test_declared_collection_scope_must_equal_operation_scope(
    tmp_path: Path,
) -> None:
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )
    tampered = replace(
        plan,
        target_collections=[*plan.target_collections, "navigation_docs"],
    )

    receipt = _execute_plan(tampered, repo_root=tmp_path, gateway=gateway)

    assert receipt.rejection_reasons == ["plan_collection_scope_mismatch"]
    assert gateway.collection_requests == []


def test_dirty_repository_fails_before_lease_or_collection_access(
    tmp_path: Path,
) -> None:
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )

    receipt = _execute_plan(
        plan,
        repo_root=tmp_path,
        gateway=gateway,
        repository_state_reader=lambda _root: _repository_state(clean=False),
    )

    assert receipt.rejection_reasons == [REPOSITORY_DIRTY_CODE]
    assert receipt.collection_mutation_performed is False
    assert gateway.collection_requests == []
    assert not maintenance_lock_path(tmp_path / "ssd").exists()


def test_busy_lease_fails_without_invalidation_or_collection_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )

    def busy(_path: Path) -> None:
        raise MaintenanceLeaseBusy("held")

    monkeypatch.setattr(executor_module, "acquire_maintenance_lease", busy)
    receipt = _execute_plan(plan, repo_root=tmp_path, gateway=gateway)

    assert receipt.rejection_reasons == [LEASE_BUSY]
    assert receipt.collection_mutation_performed is False
    assert receipt.freshness_invalidation_published is False
    assert gateway.collection_requests == []
    assert not freshness_receipt_path(tmp_path / "ssd").exists()


def test_invalidation_failure_prevents_collection_access_and_releases_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )

    def fail_invalidation(*_args, **_kwargs):
        raise OSError("injected")

    monkeypatch.setattr(
        executor_module,
        "publish_maintenance_invalidation",
        fail_invalidation,
    )
    receipt = _execute_plan(plan, repo_root=tmp_path, gateway=gateway)

    assert receipt.rejection_reasons == [INVALIDATION_FAILED]
    assert receipt.collection_mutation_performed is False
    assert gateway.collection_requests == []
    assert probe_maintenance_lock(
        maintenance_lock_path(tmp_path / "ssd")
    ).status == "idle"


def test_invalidation_is_visible_before_first_collection_access(
    tmp_path: Path,
) -> None:
    _write_foundup_files(tmp_path)
    gateway = FakeGateway()
    holo = _holo_from_gateway(gateway)
    gateway.collection_requests.clear()
    receipt_path = freshness_receipt_path(tmp_path / "ssd")
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )
    original_get_collection = gateway.get_collection
    observed: list[str] = []

    def guarded_get_collection(name: str):
        invalid = load_freshness_receipt(receipt_path)
        by_name = {entry.name: entry for entry in invalid.collections}
        assert by_name[name].verification == "IN_PROGRESS"
        observed.append(name)
        return original_get_collection(name)

    gateway.get_collection = guarded_get_collection  # type: ignore[method-assign]
    receipt = execute_incremental_foundup_index_plan(
        plan,
        repo_root=tmp_path,
        gateway=gateway,
        holo_for_receipt=holo,
        freshness_receipt_path=receipt_path,
        repository_state_reader=_clean_repository_state,
    )

    assert receipt.decision == DECISION_FAILED
    assert receipt.rejection_reasons == [FINAL_PROOF_FAILED]
    assert observed == ["navigation_symbols"]


def test_changed_head_after_mutation_leaves_invalidation_and_releases_lease(
    tmp_path: Path,
) -> None:
    _write_foundup_files(tmp_path)
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )
    states = iter((_repository_state(SHA_A), _repository_state(SHA_B)))

    receipt = _execute_plan(
        plan,
        repo_root=tmp_path,
        gateway=gateway,
        repository_state_reader=lambda _root: next(states),
    )

    assert receipt.rejection_reasons == [REPOSITORY_STATE_CHANGED]
    assert receipt.collection_mutation_performed is True
    assert receipt.freshness_invalidation_published is True
    invalid = load_freshness_receipt(
        freshness_receipt_path(tmp_path / "ssd")
    )
    by_name = {entry.name: entry for entry in invalid.collections}
    assert by_name["navigation_symbols"].verification == "IN_PROGRESS"
    assert probe_maintenance_lock(
        maintenance_lock_path(tmp_path / "ssd")
    ).status == "idle"


def test_failed_final_proof_does_not_replace_invalidation(tmp_path: Path) -> None:
    _write_foundup_files(tmp_path)
    gateway = FakeGateway()
    empty_holo = _holo_from_gateway(FakeGateway())
    receipt_path = freshness_receipt_path(tmp_path / "ssd")
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )

    receipt = _execute_plan(
        plan,
        repo_root=tmp_path,
        gateway=gateway,
        holo=empty_holo,
        receipt_path=receipt_path,
    )

    assert receipt.rejection_reasons == [FINAL_PROOF_FAILED]
    invalid = load_freshness_receipt(receipt_path)
    by_name = {entry.name: entry for entry in invalid.collections}
    assert by_name["navigation_symbols"].verification == "IN_PROGRESS"


def test_final_receipt_write_failure_keeps_invalidation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_foundup_files(tmp_path)
    gateway = FakeGateway()
    receipt_path = freshness_receipt_path(tmp_path / "ssd")
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )
    _install_complete_proof_builder(
        monkeypatch,
        set(plan.target_collections),
    )

    def fail_final_write(_receipt, _path) -> None:
        raise OSError("injected")

    monkeypatch.setattr(
        executor_module,
        "write_freshness_receipt",
        fail_final_write,
    )
    receipt = _execute_plan(
        plan,
        repo_root=tmp_path,
        gateway=gateway,
        receipt_path=receipt_path,
    )

    assert receipt.rejection_reasons == [FINAL_RECEIPT_FAILED]
    invalid = load_freshness_receipt(receipt_path)
    by_name = {entry.name: entry for entry in invalid.collections}
    assert by_name["navigation_symbols"].verification == "IN_PROGRESS"


def test_lease_is_held_until_final_receipt_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_foundup_files(tmp_path)
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )

    class FakeLease:
        released = False

        def release(self) -> None:
            self.released = True

    lease = FakeLease()
    real_write = executor_module.write_freshness_receipt

    def guarded_write(receipt, path) -> None:
        assert lease.released is False
        real_write(receipt, path)

    monkeypatch.setattr(
        executor_module,
        "acquire_maintenance_lease",
        lambda _path: lease,
    )
    monkeypatch.setattr(executor_module, "write_freshness_receipt", guarded_write)
    _install_complete_proof_builder(
        monkeypatch,
        set(plan.target_collections),
    )

    receipt = _execute_plan(plan, repo_root=tmp_path, gateway=gateway)

    assert receipt.decision == DECISION_APPLIED
    assert lease.released is True


def test_executor_module_has_no_full_reindex_or_subprocess_calls() -> None:
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_imports = {"subprocess", "requests", "holo_index.core.holo_index"}
    banned_calls = {
        "_reset_collection",
        "delete_collection",
        "index_code_entries",
        "index_wsp_entries",
        "index_docs_entries",
        "index_symbol_entries",
        "index_all",
        "run",
        "system",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in banned_imports
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "") not in banned_imports
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in banned_calls
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls
