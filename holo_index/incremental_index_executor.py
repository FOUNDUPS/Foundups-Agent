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
from typing import Any, Callable

from holo_index.freshness_receipt import (
    HoloIndexFreshnessReceipt,
    build_freshness_receipt,
    load_freshness_receipt,
    publish_maintenance_invalidation,
    write_freshness_receipt,
)
from holo_index.embedding_space import CANONICAL_INDEX_BACKEND
from holo_index.incremental_foundup_index import (
    DECISION_NO_INDEXABLE_CHANGES,
    DECISION_PLANNED,
    DECISION_REJECTED,
    OP_DELETE_PATH_ID,
    OP_UPSERT_PATH,
    IncrementalFoundUpIndexOperation,
    IncrementalFoundUpIndexPlan,
    path_is_under_foundup,
)
from holo_index.incremental_index_records import (
    IncrementalCollectionGateway,
    collection_add_records,
    existing_path_ids,
    prepare_records,
    read_indexable_file,
    resolve_repo_path,
)
from holo_index.maintenance_lock import (
    MaintenanceLeaseBusy,
    acquire_maintenance_lease,
    maintenance_lock_path,
)
from holo_index.isolated_collection_snapshot_probe import (
    IsolatedSnapshotProbeError,
    finalize_chroma_client,
    verify_collection_snapshots_isolated,
)
from holo_index.repository_state import (
    REPOSITORY_DIRTY_CODE,
    REPOSITORY_STATE_UNAVAILABLE_CODE,
    RepositoryState,
    read_repository_state,
)


SCHEMA_VERSION = "holoindex_event_driven_incremental_index_executor.v2"

DECISION_APPLIED = "APPLIED"
DECISION_NOOP = "NOOP"
DECISION_FAILED = "FAILED"

BOUNDARY_REQUIRED = "HOLOINDEX_MAINTENANCE_BOUNDARY_REQUIRED"
LEASE_BUSY = "HOLOINDEX_MAINTENANCE_LEASE_BUSY"
LEASE_UNAVAILABLE = "HOLOINDEX_MAINTENANCE_LEASE_UNAVAILABLE"
INVALIDATION_FAILED = "HOLOINDEX_MAINTENANCE_INVALIDATION_FAILED"
REPOSITORY_STATE_CHANGED = "HOLOINDEX_REPOSITORY_STATE_CHANGED"
FINAL_RECEIPT_FAILED = "HOLOINDEX_FINAL_RECEIPT_FAILED"
FINAL_PROOF_FAILED = "HOLOINDEX_MAINTENANCE_PROOF_FAILED"
OPERATION_FAILED = "HOLOINDEX_INCREMENTAL_OPERATION_FAILED"

RepositoryStateReader = Callable[[Path | str], RepositoryState]


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
    affected_paths: list[str] = field(default_factory=list)
    freshness_generation_id: str = ""
    repository_head_sha: str = ""
    rejection_reasons: list[str] = field(default_factory=list)
    no_full_reindex_performed: bool = True
    no_runtime_reindex_performed: bool = True
    collection_mutation_performed: bool = False
    receipt_written: bool = False
    freshness_invalidation_published: bool = False

    @property
    def mutation_performed(self) -> bool:
        """Compatibility-neutral name for the execution truth bit."""

        return self.collection_mutation_performed

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["mutation_performed"] = self.mutation_performed
        return payload


def canonical_plan_digest(plan: IncrementalFoundUpIndexPlan) -> str:
    payload = json.dumps(plan.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _reject(
    plan: IncrementalFoundUpIndexPlan,
    reasons: list[str],
    *,
    operations_attempted: int = 0,
    operations_applied: int = 0,
    upserted_paths: list[str] | None = None,
    deleted_paths: list[str] | None = None,
    affected_paths: list[str] | None = None,
    collection_mutation_performed: bool = False,
    freshness_generation_id: str = "",
    repository_head_sha: str = "",
    receipt_written: bool = False,
    freshness_invalidation_published: bool = False,
) -> IncrementalIndexExecutionReceipt:
    return IncrementalIndexExecutionReceipt(
        schema_version=SCHEMA_VERSION,
        decision=DECISION_FAILED,
        plan_digest=canonical_plan_digest(plan),
        foundup_id=plan.foundup_id,
        foundup_root=plan.foundup_root,
        target_collections=list(plan.target_collections),
        operations_attempted=operations_attempted,
        operations_applied=operations_applied,
        upserted_paths=list(upserted_paths or []),
        deleted_paths=list(deleted_paths or []),
        affected_paths=list(affected_paths or []),
        freshness_generation_id=freshness_generation_id,
        repository_head_sha=repository_head_sha,
        rejection_reasons=reasons,
        collection_mutation_performed=collection_mutation_performed,
        receipt_written=receipt_written,
        freshness_invalidation_published=freshness_invalidation_published,
    )


def _proven_repository_state(
    repo_root: Path,
    reader: RepositoryStateReader,
) -> tuple[RepositoryState | None, str]:
    try:
        state = reader(repo_root)
        proven_clean = bool(getattr(state, "proven_clean", False))
        reason = str(getattr(state, "error", ""))
        head_sha = str(getattr(state, "head_sha", ""))
    except Exception:
        return None, REPOSITORY_STATE_UNAVAILABLE_CODE
    if not proven_clean:
        if reason == REPOSITORY_DIRTY_CODE:
            return None, REPOSITORY_DIRTY_CODE
        return None, REPOSITORY_STATE_UNAVAILABLE_CODE
    if len(head_sha) not in {40, 64} or any(
        character not in "0123456789abcdefABCDEF" for character in head_sha
    ):
        return None, REPOSITORY_STATE_UNAVAILABLE_CODE
    return state, ""


def _receipt_proves_targets(
    receipt: HoloIndexFreshnessReceipt,
    target_collections: set[str],
    head_sha: str,
) -> bool:
    by_name = {entry.name: entry for entry in receipt.collections}
    return all(
        name in by_name
        and by_name[name].status == "indexed"
        and by_name[name].verification == "PASS"
        and by_name[name].proof_kind == "complete_source_manifest"
        and by_name[name].repo_head_sha == head_sha
        and bool(by_name[name].source_manifest_digest)
        and bool(by_name[name].indexed_paths_digest)
        and by_name[name].embedding_backend == CANONICAL_INDEX_BACKEND
        and bool(by_name[name].embedding_model)
        and by_name[name].embedding_space_fingerprint.startswith("sha256:")
        for name in target_collections
    )


@dataclass
class _ExecutionState:
    plan: IncrementalFoundUpIndexPlan
    root: Path
    gateway: IncrementalCollectionGateway
    holo_for_receipt: Any
    receipt_path: Path
    receipt_source: str
    max_file_bytes: int
    repository_state_reader: RepositoryStateReader
    initial_state: RepositoryState
    target_collections: set[str]
    ssd_path: Path
    upserted: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    affected: list[str] = field(default_factory=list)
    applied: int = 0
    attempted: int = 0
    mutation_performed: bool = False
    invalidation: HoloIndexFreshnessReceipt | None = None

    def mark_affected(self, path: str) -> None:
        if path not in self.affected:
            self.affected.append(path)

    def failure(self, reason: str) -> IncrementalIndexExecutionReceipt:
        invalidated = self.invalidation is not None
        generation_id = (
            self.invalidation.generation_id if self.invalidation is not None else ""
        )
        return _reject(
            self.plan,
            [reason],
            operations_attempted=self.attempted,
            operations_applied=self.applied,
            upserted_paths=self.upserted,
            deleted_paths=self.deleted,
            affected_paths=self.affected,
            collection_mutation_performed=self.mutation_performed,
            freshness_generation_id=generation_id,
            repository_head_sha=self.initial_state.head_sha,
            receipt_written=invalidated,
            freshness_invalidation_published=invalidated,
        )


def _early_execution_receipt(
    plan: IncrementalFoundUpIndexPlan,
    *,
    holo_for_receipt: Any | None,
    freshness_receipt_path: Path | str | None,
) -> IncrementalIndexExecutionReceipt | None:
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
    if holo_for_receipt is None or freshness_receipt_path is None:
        return _reject(plan, [BOUNDARY_REQUIRED])
    return None


def _plan_scope_failure(plan: IncrementalFoundUpIndexPlan) -> str:
    target_collections = set(plan.target_collections)
    operation_collections = {operation.collection for operation in plan.operations}
    if operation_collections != target_collections:
        return "plan_collection_scope_mismatch"
    for operation in plan.operations:
        if operation.foundup_id != plan.foundup_id:
            return "operation_foundup_mismatch"
        try:
            in_scope = path_is_under_foundup(
                operation.repo_relative_path,
                plan.foundup_id,
            )
        except ValueError:
            in_scope = False
        if not in_scope:
            return "path_outside_foundup_scope"
        if operation.operation not in {OP_UPSERT_PATH, OP_DELETE_PATH_ID}:
            return "unsupported_operation"
    return ""


def _load_base_receipt(state: _ExecutionState) -> HoloIndexFreshnessReceipt | None:
    try:
        if not state.receipt_path.exists():
            return None
        return load_freshness_receipt(state.receipt_path)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _publish_invalidation(state: _ExecutionState) -> str:
    base_receipt = _load_base_receipt(state)
    try:
        state.invalidation = publish_maintenance_invalidation(
            state.receipt_path,
            state.plan.target_collections,
            ssd_path=state.ssd_path,
            repo_root=state.root,
            base_receipt=base_receipt,
            repo_head_sha=state.initial_state.head_sha,
        )
    except Exception:
        return INVALIDATION_FAILED
    return ""


def _apply_upsert(
    state: _ExecutionState,
    operation: IncrementalFoundUpIndexOperation,
    collection: Any,
) -> None:
    source_path = resolve_repo_path(state.root, operation.repo_relative_path)
    document = read_indexable_file(source_path, max_file_bytes=state.max_file_bytes)
    records = prepare_records(
        operation=operation,
        document=document,
        plan=state.plan,
        gateway=state.gateway,
        receipt_source=state.receipt_source,
    )
    existing_ids = existing_path_ids(
        collection,
        repo_relative_path=operation.repo_relative_path,
        stable_id=operation.stable_id,
    )
    if existing_ids:
        collection.delete(ids=existing_ids)
        state.mutation_performed = True
        state.mark_affected(operation.repo_relative_path)
    if records:
        collection_add_records(collection, records)
        state.mutation_performed = True
        state.mark_affected(operation.repo_relative_path)
    state.upserted.append(operation.repo_relative_path)


def _apply_delete(
    state: _ExecutionState,
    operation: IncrementalFoundUpIndexOperation,
    collection: Any,
) -> None:
    existing_ids = existing_path_ids(
        collection,
        repo_relative_path=operation.repo_relative_path,
        stable_id=operation.stable_id,
    )
    if existing_ids:
        collection.delete(ids=existing_ids)
        state.mutation_performed = True
        state.mark_affected(operation.repo_relative_path)
    state.deleted.append(operation.repo_relative_path)


def _apply_operation(
    state: _ExecutionState,
    operation: IncrementalFoundUpIndexOperation,
) -> None:
    state.attempted += 1
    collection = state.gateway.get_collection(operation.collection)
    if operation.operation == OP_UPSERT_PATH:
        _apply_upsert(state, operation, collection)
    elif operation.operation == OP_DELETE_PATH_ID:
        _apply_delete(state, operation, collection)
    else:
        raise ValueError(f"unsupported_operation:{operation.operation}")
    state.mark_affected(operation.repo_relative_path)
    state.applied += 1


def _apply_operations(state: _ExecutionState) -> str:
    try:
        for operation in state.plan.operations:
            _apply_operation(state, operation)
    except Exception:
        return OPERATION_FAILED
    return ""


def _verify_repository_unchanged(state: _ExecutionState) -> str:
    final_state, state_failure = _proven_repository_state(
        state.root,
        state.repository_state_reader,
    )
    if final_state is None:
        return state_failure
    if final_state.head_sha != state.initial_state.head_sha:
        return REPOSITORY_STATE_CHANGED
    return ""


def _publish_final_receipt(
    state: _ExecutionState,
) -> tuple[HoloIndexFreshnessReceipt | None, str]:
    try:
        receipt = build_freshness_receipt(
            state.holo_for_receipt,
            ssd_path=state.ssd_path,
            repo_root=state.root,
            source=state.receipt_source,
            repo_head_sha=state.initial_state.head_sha,
            refreshed_collections=state.plan.target_collections,
            base_receipt=state.invalidation,
        )
        if not _receipt_proves_targets(
            receipt,
            state.target_collections,
            state.initial_state.head_sha,
        ):
            return None, FINAL_PROOF_FAILED
    except Exception:
        return None, FINAL_RECEIPT_FAILED
    try:
        finalize_chroma_client(getattr(state.holo_for_receipt, "client", None))
        proof_failures = verify_collection_snapshots_isolated(
            receipt,
            ssd_path=state.ssd_path,
            repo_root=state.root,
        )
        if proof_failures:
            return None, FINAL_PROOF_FAILED
    except Exception:
        return None, FINAL_PROOF_FAILED
    try:
        write_freshness_receipt(receipt, state.receipt_path)
    except Exception:
        return None, FINAL_RECEIPT_FAILED
    return receipt, ""


def _applied_receipt(
    state: _ExecutionState,
    receipt: HoloIndexFreshnessReceipt,
) -> IncrementalIndexExecutionReceipt:
    return IncrementalIndexExecutionReceipt(
        schema_version=SCHEMA_VERSION,
        decision=DECISION_APPLIED,
        plan_digest=canonical_plan_digest(state.plan),
        foundup_id=state.plan.foundup_id,
        foundup_root=state.plan.foundup_root,
        target_collections=list(state.plan.target_collections),
        operations_attempted=state.attempted,
        operations_applied=state.applied,
        upserted_paths=state.upserted,
        deleted_paths=state.deleted,
        affected_paths=state.affected,
        freshness_generation_id=receipt.generation_id,
        repository_head_sha=state.initial_state.head_sha,
        collection_mutation_performed=state.mutation_performed,
        receipt_written=True,
        freshness_invalidation_published=True,
    )


def _execute_while_leased(
    state: _ExecutionState,
) -> IncrementalIndexExecutionReceipt:
    failure = _publish_invalidation(state)
    if failure:
        return state.failure(failure)
    failure = _apply_operations(state)
    if failure:
        return state.failure(failure)
    failure = _verify_repository_unchanged(state)
    if failure:
        return state.failure(failure)
    receipt, failure = _publish_final_receipt(state)
    if failure or receipt is None:
        return state.failure(failure or FINAL_RECEIPT_FAILED)
    return _applied_receipt(state, receipt)


def _release_lease(lease: Any) -> None:
    try:
        lease.release()
    except Exception:
        pass


def execute_incremental_foundup_index_plan(
    plan: IncrementalFoundUpIndexPlan,
    *,
    repo_root: Path | str,
    gateway: IncrementalCollectionGateway,
    holo_for_receipt: Any | None = None,
    freshness_receipt_path: Path | str | None = None,
    receipt_source: str = "wre_incremental_index",
    max_file_bytes: int = 12000,
    repository_state_reader: RepositoryStateReader = read_repository_state,
) -> IncrementalIndexExecutionReceipt:
    """Apply an already validated FoundUp-scoped incremental plan."""

    early_receipt = _early_execution_receipt(
        plan,
        holo_for_receipt=holo_for_receipt,
        freshness_receipt_path=freshness_receipt_path,
    )
    if early_receipt is not None:
        return early_receipt

    scope_failure = _plan_scope_failure(plan)
    if scope_failure:
        return _reject(plan, [scope_failure])

    root = Path(repo_root).resolve(strict=False)
    initial_state, state_failure = _proven_repository_state(
        root,
        repository_state_reader,
    )
    if initial_state is None:
        return _reject(plan, [state_failure])

    receipt_path = Path(freshness_receipt_path)
    ssd_path = receipt_path.parent.parent
    try:
        lease = acquire_maintenance_lease(maintenance_lock_path(ssd_path))
    except MaintenanceLeaseBusy:
        return _reject(
            plan,
            [LEASE_BUSY],
            repository_head_sha=initial_state.head_sha,
        )
    except Exception:
        return _reject(
            plan,
            [LEASE_UNAVAILABLE],
            repository_head_sha=initial_state.head_sha,
        )

    state = _ExecutionState(
        plan=plan,
        root=root,
        gateway=gateway,
        holo_for_receipt=holo_for_receipt,
        receipt_path=receipt_path,
        receipt_source=receipt_source,
        max_file_bytes=max_file_bytes,
        repository_state_reader=repository_state_reader,
        initial_state=initial_state,
        target_collections=set(plan.target_collections),
        ssd_path=ssd_path,
    )
    try:
        return _execute_while_leased(state)
    finally:
        _release_lease(lease)


__all__ = [
    "BOUNDARY_REQUIRED",
    "DECISION_APPLIED",
    "DECISION_FAILED",
    "DECISION_NOOP",
    "FINAL_PROOF_FAILED",
    "FINAL_RECEIPT_FAILED",
    "INVALIDATION_FAILED",
    "IncrementalCollectionGateway",
    "IncrementalIndexExecutionReceipt",
    "LEASE_BUSY",
    "LEASE_UNAVAILABLE",
    "OPERATION_FAILED",
    "REPOSITORY_STATE_CHANGED",
    "RepositoryStateReader",
    "SCHEMA_VERSION",
    "canonical_plan_digest",
    "execute_incremental_foundup_index_plan",
]
