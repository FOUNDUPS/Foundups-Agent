"""Tests for HOLOINDEX_EVENT_DRIVEN_INCREMENTAL_INDEX_EXECUTOR_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

from holo_index.freshness_receipt import freshness_receipt_path, load_freshness_receipt
from holo_index.incremental_foundup_index import (
    DECISION_NO_INDEXABLE_CHANGES,
    DECISION_REJECTED,
    IncrementalFoundUpIndexPlan,
    plan_incremental_foundup_index,
)
from holo_index.incremental_index_executor import (
    DECISION_APPLIED,
    DECISION_FAILED,
    DECISION_NOOP,
    canonical_plan_digest,
    execute_incremental_foundup_index_plan,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE = REPO_ROOT / "holo_index" / "incremental_index_executor.py"


class FakeCollection:
    def __init__(self, name: str):
        self.name = name
        self.metadata = {"embedding_backend": "fake"}
        self.deleted: list[list[str]] = []
        self.added: list[dict] = []

    def delete(self, ids):
        self.deleted.append(list(ids))

    def add(self, **kwargs):
        self.added.append(kwargs)

    def count(self) -> int:
        return len(self.added)

    def get(self, include=None):
        ids = []
        metadatas = []
        for payload in self.added:
            ids.extend(payload.get("ids", []))
            metadatas.extend(payload.get("metadatas", []))
        return {"ids": ids, "metadatas": metadatas}


class FakeGateway:
    def __init__(self):
        self.collections: dict[str, FakeCollection] = {}
        self.embedded: list[str] = []

    def get_collection(self, name: str):
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
    return SimpleNamespace(**values)


def _write_foundup_files(repo_root: Path) -> None:
    foundup_root = repo_root / "modules" / "foundups" / "paccess_001"
    (foundup_root / "src").mkdir(parents=True)
    (foundup_root / "tests").mkdir(parents=True)
    (foundup_root / "src" / "main.py").write_text("def create_foundup():\n    return True\n", encoding="utf-8")
    (foundup_root / "README.md").write_text("# pAccess\n", encoding="utf-8")
    (foundup_root / "tests" / "test_main.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")


def test_executor_applies_scoped_upsert_operations(tmp_path: Path) -> None:
    _write_foundup_files(tmp_path)
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=[
            "modules/foundups/paccess_001/src/main.py",
            "modules/foundups/paccess_001/README.md",
        ],
    )

    receipt = execute_incremental_foundup_index_plan(
        plan,
        repo_root=tmp_path,
        gateway=gateway,
    )

    assert receipt.decision == DECISION_APPLIED
    assert receipt.plan_digest == canonical_plan_digest(plan)
    assert receipt.operations_attempted == 2
    assert receipt.operations_applied == 2
    assert receipt.collection_mutation_performed is True
    assert receipt.no_full_reindex_performed is True
    assert receipt.no_runtime_reindex_performed is True
    assert set(receipt.upserted_paths) == {
        "modules/foundups/paccess_001/src/main.py",
        "modules/foundups/paccess_001/README.md",
    }
    symbol_collection = gateway.get_collection("navigation_symbols")
    docs_collection = gateway.get_collection("navigation_docs")
    assert len(symbol_collection.deleted) == 1
    assert len(symbol_collection.added) == 1
    assert symbol_collection.added[0]["metadatas"][0]["foundup_id"] == "paccess_001"
    assert docs_collection.added[0]["metadatas"][0]["path"] == "modules/foundups/paccess_001/README.md"


def test_executor_applies_delete_operations_without_reading_source(tmp_path: Path) -> None:
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        removed_paths=["modules/foundups/paccess_001/src/main.py"],
    )

    receipt = execute_incremental_foundup_index_plan(
        plan,
        repo_root=tmp_path,
        gateway=gateway,
    )

    assert receipt.decision == DECISION_APPLIED
    assert receipt.deleted_paths == ["modules/foundups/paccess_001/src/main.py"]
    assert gateway.get_collection("navigation_symbols").deleted
    assert gateway.embedded == []


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

    receipt = execute_incremental_foundup_index_plan(plan, repo_root=tmp_path, gateway=gateway)

    assert receipt.decision == DECISION_FAILED
    assert receipt.collection_mutation_performed is False
    assert any(reason.startswith("source_file_missing:") for reason in receipt.rejection_reasons)


def test_executor_writes_freshness_receipt_when_holo_snapshot_supplied(tmp_path: Path) -> None:
    _write_foundup_files(tmp_path)
    gateway = FakeGateway()
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )
    ssd_path = tmp_path / "ssd"
    receipt_path = freshness_receipt_path(ssd_path)

    receipt = execute_incremental_foundup_index_plan(
        plan,
        repo_root=tmp_path,
        gateway=gateway,
        holo_for_receipt=_holo_from_gateway(gateway),
        freshness_receipt_path=receipt_path,
    )
    loaded = load_freshness_receipt(receipt_path)

    assert receipt.decision == DECISION_APPLIED
    assert receipt.receipt_written is True
    assert receipt.freshness_generation_id == loaded.generation_id
    assert loaded.source == "wre_incremental_index"


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
