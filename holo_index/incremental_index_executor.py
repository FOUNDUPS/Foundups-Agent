"""Event-driven incremental HoloIndex executor.

This module executes a precomputed FoundUp-scoped incremental plan against
injected collection handles. It is a WRE/CI maintenance primitive, not a RedDog
runtime query primitive.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from holo_index.freshness_receipt import (
    HoloIndexFreshnessReceipt,
    build_freshness_receipt,
    write_freshness_receipt,
)
from holo_index.incremental_foundup_index import (
    DECISION_NO_INDEXABLE_CHANGES,
    DECISION_PLANNED,
    DECISION_REJECTED,
    OP_DELETE_PATH_ID,
    OP_UPSERT_PATH,
    IncrementalFoundUpIndexPlan,
    path_is_under_foundup,
)


SCHEMA_VERSION = "holoindex_event_driven_incremental_index_executor.v1"

DECISION_APPLIED = "APPLIED"
DECISION_NOOP = "NOOP"
DECISION_FAILED = "FAILED"


class IncrementalCollectionGateway(Protocol):
    """Injected collection and embedding adapter."""

    def get_collection(self, name: str) -> Any:
        """Return the mutable collection handle for a collection name."""

    def embed(self, text: str) -> list[float]:
        """Return an embedding for the provided text."""


@dataclass(frozen=True)
class IncrementalIndexExecutionReceipt:
    """Receipt for one incremental execution attempt."""

    schema_version: str
    decision: str
    plan_digest: str
    foundup_id: str
    foundup_root: str
    target_collections: list[str] = field(default_factory=list)
    operations_attempted: int = 0
    operations_applied: int = 0
    upserted_paths: list[str] = field(default_factory=list)
    deleted_paths: list[str] = field(default_factory=list)
    freshness_generation_id: str = ""
    rejection_reasons: list[str] = field(default_factory=list)
    no_full_reindex_performed: bool = True
    no_runtime_reindex_performed: bool = True
    collection_mutation_performed: bool = False
    receipt_written: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_plan_digest(plan: IncrementalFoundUpIndexPlan) -> str:
    payload = json.dumps(plan.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _reject(
    plan: IncrementalFoundUpIndexPlan,
    reasons: list[str],
) -> IncrementalIndexExecutionReceipt:
    return IncrementalIndexExecutionReceipt(
        schema_version=SCHEMA_VERSION,
        decision=DECISION_FAILED,
        plan_digest=canonical_plan_digest(plan),
        foundup_id=plan.foundup_id,
        foundup_root=plan.foundup_root,
        target_collections=list(plan.target_collections),
        operations_attempted=len(plan.operations),
        rejection_reasons=reasons,
    )


def _resolve_repo_path(repo_root: Path, repo_relative_path: str) -> Path:
    root = repo_root.resolve()
    target = (root / repo_relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path_outside_repo:{repo_relative_path}") from exc
    return target


def _read_indexable_file(path: Path, *, max_file_bytes: int) -> str:
    if not path.exists() or not path.is_file():
        raise ValueError(f"source_file_missing:{path}")
    data = path.read_bytes()
    if len(data) > max_file_bytes:
        data = data[:max_file_bytes]
    return data.decode("utf-8", errors="replace")


def _collection_delete(collection: Any, stable_id: str) -> None:
    collection.delete(ids=[stable_id])


def _collection_add(
    collection: Any,
    *,
    stable_id: str,
    document: str,
    metadata: dict[str, Any],
    embedding: list[float],
) -> None:
    payload: dict[str, Any] = {
        "ids": [stable_id],
        "documents": [document],
        "metadatas": [metadata],
    }
    if embedding:
        payload["embeddings"] = [embedding]
    collection.add(**payload)


def execute_incremental_foundup_index_plan(
    plan: IncrementalFoundUpIndexPlan,
    *,
    repo_root: Path | str,
    gateway: IncrementalCollectionGateway,
    holo_for_receipt: Any | None = None,
    freshness_receipt_path: Path | str | None = None,
    receipt_source: str = "wre_incremental_index",
    max_file_bytes: int = 12000,
) -> IncrementalIndexExecutionReceipt:
    """Apply an already validated FoundUp-scoped incremental plan."""

    if plan.schema_version != "holoindex_incremental_foundup_index.v1":
        return _reject(plan, ["unsupported_plan_schema"])
    if plan.decision == DECISION_REJECTED:
        return _reject(plan, ["plan_rejected", *plan.rejection_reasons])
    if plan.decision == DECISION_NO_INDEXABLE_CHANGES:
        return IncrementalIndexExecutionReceipt(
            schema_version=SCHEMA_VERSION,
            decision=DECISION_NOOP,
            plan_digest=canonical_plan_digest(plan),
            foundup_id=plan.foundup_id,
            foundup_root=plan.foundup_root,
            target_collections=list(plan.target_collections),
            rejection_reasons=["no_indexable_changes"],
        )
    if plan.decision != DECISION_PLANNED:
        return _reject(plan, [f"unsupported_plan_decision:{plan.decision}"])
    if not plan.operations:
        return _reject(plan, ["planned_without_operations"])

    root = Path(repo_root)
    upserted: list[str] = []
    deleted: list[str] = []
    applied = 0
    try:
        for operation in plan.operations:
            if not path_is_under_foundup(operation.repo_relative_path, plan.foundup_id):
                raise ValueError(f"path_outside_foundup_scope:{operation.repo_relative_path}")
            collection = gateway.get_collection(operation.collection)
            if operation.operation == OP_UPSERT_PATH:
                source_path = _resolve_repo_path(root, operation.repo_relative_path)
                document = _read_indexable_file(source_path, max_file_bytes=max_file_bytes)
                embedding = gateway.embed(document)
                metadata = {
                    "path": operation.repo_relative_path,
                    "foundup_id": plan.foundup_id,
                    "foundup_root": plan.foundup_root,
                    "collection": operation.collection,
                    "source": receipt_source,
                }
                _collection_delete(collection, operation.stable_id)
                _collection_add(
                    collection,
                    stable_id=operation.stable_id,
                    document=document,
                    metadata=metadata,
                    embedding=embedding,
                )
                upserted.append(operation.repo_relative_path)
                applied += 1
            elif operation.operation == OP_DELETE_PATH_ID:
                _collection_delete(collection, operation.stable_id)
                deleted.append(operation.repo_relative_path)
                applied += 1
            else:
                raise ValueError(f"unsupported_operation:{operation.operation}")
    except Exception as exc:
        return _reject(plan, [str(exc)])

    generation_id = ""
    receipt_written = False
    if holo_for_receipt is not None and freshness_receipt_path is not None:
        receipt: HoloIndexFreshnessReceipt = build_freshness_receipt(
            holo_for_receipt,
            ssd_path=Path(freshness_receipt_path).parents[1],
            repo_root=root,
            source=receipt_source,
        )
        generation_id = receipt.generation_id
        write_freshness_receipt(receipt, freshness_receipt_path)
        receipt_written = True

    return IncrementalIndexExecutionReceipt(
        schema_version=SCHEMA_VERSION,
        decision=DECISION_APPLIED,
        plan_digest=canonical_plan_digest(plan),
        foundup_id=plan.foundup_id,
        foundup_root=plan.foundup_root,
        target_collections=list(plan.target_collections),
        operations_attempted=len(plan.operations),
        operations_applied=applied,
        upserted_paths=upserted,
        deleted_paths=deleted,
        freshness_generation_id=generation_id,
        collection_mutation_performed=applied > 0,
        receipt_written=receipt_written,
    )


__all__ = [
    "DECISION_APPLIED",
    "DECISION_FAILED",
    "DECISION_NOOP",
    "IncrementalCollectionGateway",
    "IncrementalIndexExecutionReceipt",
    "SCHEMA_VERSION",
    "canonical_plan_digest",
    "execute_incremental_foundup_index_plan",
]
