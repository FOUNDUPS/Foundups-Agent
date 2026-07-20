"""Durable AgentDB resident RedDog architect cycle.

Slice: REDDOG_RESIDENT_ARCHITECT_DURABLE_AGENTDB_CYCLE_PHASE1

This module turns the RedDog thin-client intent into a durable AgentDB cycle:
intent submission, read-only audit task enqueue, OpenClaw-owned task claiming,
read-only report persistence, backend architect determination, and status
recovery by intent ID. It does not execute shell commands, mutate source files,
create worktrees, dispatch Hermes, create PRs, promote PatternMemory, enqueue
live FoundUp work, or re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence

from holo_index.freshness_receipt import HoloIndexFreshnessReceipt
from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
    READONLY_AUDIT_OPENCLAW_CLAIM_ACCEPT,
    READONLY_AUDIT_OPENCLAW_CLAIM_IDLE,
    claim_reddog_readonly_audit_task_once,
)
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ArchitectDeterminationStore,
    ArchitectModelRunner,
)
from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    validate_grounded_target_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_main_readonly_operational_bootstrap import (
    DEFAULT_BOOTSTRAP_CHANGED_PATHS,
    DEFAULT_BOOTSTRAP_READ_TARGETS,
    REDDOG_MAIN_BOOTSTRAP_READY,
    RedDogMainReadonlyBootstrapResult,
    run_reddog_main_readonly_operational_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    AgentDbReadOnlyAuditTaskWriter,
    READONLY_AUDIT_TASK_SOURCE,
)
from modules.communication.moltbot_bridge.src.reddog_operational_memex_snapshot_supplier import (
    OperationalMemexSnapshotSupplyConfig,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_runtime import (
    DEFAULT_AUDIT_LANES,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime import (
    ExternalResearchRetriever,
    ReadOnlyEvidenceQueryAdapter,
    RepoAuditModelRunner,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_decision_persistence import (
    ReadOnlyAuditDecisionStore,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_report_collection import (
    AgentDbReadOnlyAuditReportStore,
    ReadOnlyAuditReportStore,
)


REDDOG_RESIDENT_CYCLE_ACCEPT = "REDDOG_RESIDENT_CYCLE_ACCEPT"
REDDOG_RESIDENT_CYCLE_REJECT = "REDDOG_RESIDENT_CYCLE_REJECT"

STATUS_SUBMITTED = "SUBMITTED"
STATUS_ENQUEUED = "ENQUEUED"
STATUS_RUNNING = "RUNNING"
STATUS_DETERMINED = "DETERMINED"
STATUS_FAILED = "FAILED"
STATUS_TIMED_OUT = "TIMED_OUT"
STATUS_CANCELLED = "CANCELLED"

TERMINAL_STATUSES = frozenset({STATUS_DETERMINED, STATUS_FAILED, STATUS_TIMED_OUT, STATUS_CANCELLED})
RUNTIME_BOUNDARY_FIELDS = (
    "read_only_authority_only",
    "no_shell_command_executed",
    "no_repo_mutation_performed",
    "no_holoindex_reindex_performed",
    "no_hermes_dispatch_performed",
    "no_worktree_operation_performed",
    "no_pr_created",
    "no_pattern_memory_promotion_performed",
    "no_live_foundup_enqueue_performed",
)
ALLOWED_STATUS_TRANSITIONS = {
    STATUS_SUBMITTED: frozenset({STATUS_ENQUEUED, STATUS_FAILED, STATUS_CANCELLED}),
    STATUS_ENQUEUED: frozenset({STATUS_RUNNING, STATUS_CANCELLED}),
    STATUS_RUNNING: frozenset(
        {STATUS_RUNNING, STATUS_DETERMINED, STATUS_FAILED, STATUS_TIMED_OUT, STATUS_CANCELLED}
    ),
}
IMMUTABLE_CYCLE_FIELDS = frozenset(
    {
        "schema_version",
        "intent_id",
        "intent_digest",
        "intent",
        "created_at",
        "genesis_state_digest",
        *RUNTIME_BOUNDARY_FIELDS,
    }
)
GENESIS_RECORD_FIELDS = frozenset(
    {
        "schema_version",
        "intent_id",
        "intent_digest",
        "cycle_id",
        "status",
        "intent",
        "snapshot_id",
        "determination_id",
        "swarm_id",
        "task_ids",
        "task_status_counts",
        "openclaw_claims",
        "retry_count",
        "record_revision",
        "attempt_history",
        "transition_history",
        "created_at",
        "updated_at",
        "rejection_reasons",
        "genesis_state_digest",
        *RUNTIME_BOUNDARY_FIELDS,
    }
)


class ResidentCycleReason:
    INTENT_INVALID = "REJECT_RESIDENT_CYCLE_INTENT_INVALID"
    EXECUTABLE_AUTHORITY_REQUESTED = "REJECT_RESIDENT_CYCLE_EXECUTABLE_AUTHORITY_REQUESTED"
    EXTERNAL_RESEARCH_RETRIEVER_MISSING = "REJECT_RESIDENT_CYCLE_EXTERNAL_RESEARCH_RETRIEVER_MISSING"
    BOOTSTRAP_REJECTED = "REJECT_RESIDENT_CYCLE_BOOTSTRAP_REJECTED"
    TASK_ENQUEUE_REJECTED = "REJECT_RESIDENT_CYCLE_TASK_ENQUEUE_REJECTED"
    NO_TASK_IDS = "REJECT_RESIDENT_CYCLE_NO_TASK_IDS"
    OPENCLAW_CLAIM_REJECTED = "REJECT_RESIDENT_CYCLE_OPENCLAW_CLAIM_REJECTED"
    TIMEOUT = "REJECT_RESIDENT_CYCLE_TIMEOUT"
    FINAL_BOOTSTRAP_REJECTED = "REJECT_RESIDENT_CYCLE_FINAL_BOOTSTRAP_REJECTED"
    ARCHITECT_DETERMINATION_MISSING = "REJECT_RESIDENT_CYCLE_ARCHITECT_DETERMINATION_MISSING"
    DUPLICATE_ACTIVE_INTENT = "REJECT_RESIDENT_CYCLE_DUPLICATE_ACTIVE_INTENT"
    RETRY_NOT_ALLOWED = "REJECT_RESIDENT_CYCLE_RETRY_NOT_ALLOWED"
    CANCELLED = "REJECT_RESIDENT_CYCLE_CANCELLED"
    STORE_REJECTED = "REJECT_RESIDENT_CYCLE_STORE_REJECTED"
    INTENT_CONFLICT = "REJECT_RESIDENT_CYCLE_INTENT_CONFLICT"
    ACTIVE_INTENT = "REJECT_RESIDENT_CYCLE_ACTIVE_INTENT"
    TRANSITION_CONFLICT = "REJECT_RESIDENT_CYCLE_TRANSITION_CONFLICT"
    CANCELLATION_CONFLICT = "REJECT_RESIDENT_CYCLE_CANCELLATION_CONFLICT"


class ResidentArchitectCycleStore(Protocol):
    def load_cycle_by_intent(self, intent_id: str) -> Optional[Mapping[str, Any]]: ...

    def create_cycle(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def transition_cycle(
        self,
        intent_id: str,
        *,
        expected_revision: int,
        expected_statuses: Sequence[str],
        updates: Mapping[str, Any],
        allow_terminal_retry: bool = False,
    ) -> Mapping[str, Any]: ...

    def load_task_ids(self, determination_id: str) -> tuple[str, ...]: ...

    def load_task_status_counts(self, task_ids: Sequence[str]) -> Mapping[str, int]: ...

    def delete_cycle_tasks(self, task_ids: Sequence[str]) -> None: ...


class NoopExternalResearchRetriever:
    """Fail-closed external retriever used when no approved source is configured.

    The resident cycle still needs an object implementing the retriever
    protocol so the external-research worker can emit an explicit missing
    evidence receipt. This retriever performs no network I/O and returns no
    content-bearing evidence.
    """

    def fetch(self, target: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "source_url": str(target.get("url") or target.get("target") or ""),
            "source_type": "unconfigured",
            "finding_status": "missing",
            "rejection_reasons": ["approved_external_research_retriever_not_configured"],
        }


@dataclass(frozen=True)
class RedDogResidentArchitectCycleResult:
    accepted: bool
    decision: str
    status: str
    intent_id: str
    cycle_id: str
    snapshot_id: Optional[str]
    determination_id: Optional[str]
    swarm_id: Optional[str]
    task_ids: tuple[str, ...]
    task_status_counts: Mapping[str, int]
    openclaw_claims: tuple[Mapping[str, Any], ...]
    final_bootstrap: Optional[RedDogMainReadonlyBootstrapResult]
    architect_action: Optional[str]
    architect_next_slice: Optional[str]
    architect_determination_id: Optional[str]
    queue_candidate_count: int
    duplicate_intent_reused: bool
    recovered_existing_cycle: bool
    retry_count: int
    record_revision: int
    intent_digest: str
    rejection_reasons: tuple[str, ...]
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_worktree_operation_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_promotion_performed: bool = True
    no_live_foundup_enqueue_performed: bool = True
    read_only_authority_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["final_bootstrap"] = self.final_bootstrap.to_dict() if self.final_bootstrap else None
        payload["task_status_counts"] = dict(self.task_status_counts)
        payload["openclaw_claims"] = [dict(item) for item in self.openclaw_claims]
        payload["rejection_reasons"] = list(self.rejection_reasons)
        return payload


class AgentDbResidentArchitectCycleStore:
    """AgentDB-backed resident-cycle store."""

    def __init__(self, agent_db_factory: Optional[Callable[[], Any]] = None) -> None:
        self._agent_db_factory = agent_db_factory

    def load_cycle_by_intent(self, intent_id: str) -> Optional[Mapping[str, Any]]:
        db = self._agent_db()
        self._ensure_table(db)
        rows = db.db.execute_query(
            "SELECT revision, cycle_json FROM reddog_resident_architect_cycles WHERE intent_id = ?",
            (intent_id,),
        )
        if not rows:
            return None
        row = rows[0]
        try:
            revision = int(row["revision"] if isinstance(row, Mapping) else row[0])
            value = row["cycle_json"] if isinstance(row, Mapping) else row[1]
            record = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError, KeyError, IndexError):
            return {
                "intent_id": intent_id,
                "status": STATUS_FAILED,
                "_store_revision": -1,
                "_store_integrity_valid": False,
            }
        if not isinstance(record, dict):
            return {
                "intent_id": intent_id,
                "status": STATUS_FAILED,
                "_store_revision": revision,
                "_store_integrity_valid": False,
            }
        record["_store_revision"] = revision
        record["_store_integrity_valid"] = (
            int(record.get("record_revision", -1)) == revision
            and _transition_history_is_valid(record, revision=revision)
        )
        return record

    def create_cycle(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        db = self._agent_db()
        self._ensure_table(db)
        value = dict(record)
        supplied_revision = _parse_nonnegative_int(value.get("record_revision"))
        value["record_revision"] = 0
        intent = value.get("intent")
        intent_id = str(value.get("intent_id") or "")
        retry_count = _parse_nonnegative_int(value.get("retry_count"))
        expected_cycle_id = _digest(
            {"intent_id": intent_id, "retry_count": 0, "slice": "resident_agentdb_cycle"}
        )
        if (
            value.get("schema_version") != "reddog_resident_architect_cycle.v2"
            or not isinstance(intent, Mapping)
            or not intent_id
            or str(intent.get("intent_id") or "") != intent_id
            or bool(_validate_intent(intent))
            or str(value.get("intent_digest") or "") != resident_intent_digest(intent)
            or any(value.get(field) is not True for field in RUNTIME_BOUNDARY_FIELDS)
            or frozenset(value) != GENESIS_RECORD_FIELDS
            or str(value.get("genesis_state_digest") or "") != _genesis_state_digest(value)
            or value.get("status") != STATUS_SUBMITTED
            or str(value.get("cycle_id") or "") != expected_cycle_id
            or retry_count != 0
            or supplied_revision != 0
            or value.get("transition_history") != []
            or value.get("attempt_history") != []
            or value.get("task_ids") != []
            or value.get("task_status_counts") != {}
            or value.get("openclaw_claims") != []
            or value.get("rejection_reasons") != []
            or value.get("snapshot_id") is not None
            or value.get("determination_id") is not None
            or value.get("swarm_id") is not None
        ):
            return {"ok": False, "stored": False, "reason": "invalid_cycle_record", "record": None}
        payload = _canonical_json(value)
        with db.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reddog_resident_architect_cycles
                (intent_id, cycle_id, status, snapshot_id, determination_id, revision, cycle_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(intent_id) DO NOTHING
                """,
                (
                    value.get("intent_id"),
                    value.get("cycle_id"),
                    value.get("status"),
                    value.get("snapshot_id"),
                    value.get("determination_id"),
                    0,
                    payload,
                    _now_iso(),
                ),
            )
        return {
            "ok": cursor.rowcount == 1,
            "stored": cursor.rowcount == 1,
            "reason": "" if cursor.rowcount == 1 else "cycle_exists",
            "record": value if cursor.rowcount == 1 else None,
        }

    def transition_cycle(
        self,
        intent_id: str,
        *,
        expected_revision: int,
        expected_statuses: Sequence[str],
        updates: Mapping[str, Any],
        allow_terminal_retry: bool = False,
    ) -> Mapping[str, Any]:
        db = self._agent_db()
        self._ensure_table(db)
        allowed = frozenset(str(status) for status in expected_statuses)
        with db.db.get_connection() as conn:
            row = conn.execute(
                """
                SELECT revision, cycle_json
                FROM reddog_resident_architect_cycles
                WHERE intent_id = ?
                """,
                (intent_id,),
            ).fetchone()
            if row is None:
                return {"ok": False, "reason": "missing_cycle"}
            revision = int(row["revision"] if isinstance(row, Mapping) else row[0])
            current = json.loads(
                row["cycle_json"] if isinstance(row, Mapping) else row[1]
            )
            status = str(current.get("status") or "")
            next_status = str(updates.get("status") or status)
            legacy_cancel = bool(
                next_status == STATUS_CANCELLED
                and "record_revision" not in current
                and "intent_digest" not in current
            )
            if revision != int(expected_revision) or (
                int(current.get("record_revision", -1)) != revision and not legacy_cancel
            ):
                return {"ok": False, "reason": "revision_conflict"}
            if not legacy_cancel and not _transition_history_is_valid(current, revision=revision):
                return {"ok": False, "reason": "transition_history_invalid"}
            if status not in allowed:
                return {"ok": False, "reason": "status_conflict"}
            if status in TERMINAL_STATUSES and not (
                allow_terminal_retry
                and status in {STATUS_FAILED, STATUS_TIMED_OUT}
                and next_status == STATUS_SUBMITTED
            ):
                return {"ok": False, "reason": "terminal_status"}
            if status not in TERMINAL_STATUSES and next_status not in ALLOWED_STATUS_TRANSITIONS.get(status, ()):
                return {"ok": False, "reason": "invalid_status_transition"}
            for field in IMMUTABLE_CYCLE_FIELDS:
                if field in updates and updates.get(field) != current.get(field):
                    return {"ok": False, "reason": f"immutable_field:{field}"}
            try:
                retry_error = _validate_retry_transition(
                    current=current,
                    updates=updates,
                    allow_terminal_retry=allow_terminal_retry,
                    next_status=next_status,
                )
            except (TypeError, ValueError):
                retry_error = "retry_metadata_invalid"
            if retry_error:
                return {"ok": False, "reason": retry_error}
            merged = dict(current)
            merged.update(dict(updates))
            merged.pop("_store_integrity_valid", None)
            merged.pop("_store_revision", None)
            merged["record_revision"] = revision + 1
            history = list(current.get("transition_history") or ())
            previous_receipt_id = str(history[-1].get("receipt_id") or "") if history else ""
            transition_receipt = {
                "schema_version": "reddog_resident_cycle_transition.v1",
                "intent_id": intent_id,
                "cycle_id": str(merged.get("cycle_id") or ""),
                "from_status": status,
                "to_status": next_status,
                "from_revision": revision,
                "to_revision": revision + 1,
                "updates_digest": _digest(dict(updates)),
                "previous_receipt_id": previous_receipt_id,
                "transitioned_at": _now_iso(),
                "authority": "observational_internal_integrity_only",
            }
            state_for_digest = dict(merged)
            state_for_digest.pop("transition_history", None)
            transition_receipt["result_state_digest"] = _digest(state_for_digest)
            transition_receipt["receipt_id"] = _digest(transition_receipt)
            merged["transition_history"] = [*history, transition_receipt]
            payload = _canonical_json(merged)
            cursor = conn.execute(
                """
                UPDATE reddog_resident_architect_cycles
                SET cycle_id = ?, status = ?, snapshot_id = ?, determination_id = ?,
                    revision = ?, cycle_json = ?, updated_at = ?
                WHERE intent_id = ? AND revision = ?
                """,
                (
                    merged.get("cycle_id"),
                    merged.get("status"),
                    merged.get("snapshot_id"),
                    merged.get("determination_id"),
                    revision + 1,
                    payload,
                    _now_iso(),
                    intent_id,
                    revision,
                ),
            )
        if cursor.rowcount != 1:
            return {"ok": False, "reason": "revision_conflict"}
        return {"ok": True, "stored": True, "record": merged}

    def upsert_cycle(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        """Compatibility seam: create only; existing rows require explicit CAS."""
        return self.create_cycle(record)

    def update_cycle(self, intent_id: str, updates: Mapping[str, Any]) -> Mapping[str, Any]:
        del intent_id, updates
        return {"ok": False, "reason": "cas_required"}

    def load_task_ids(self, determination_id: str) -> tuple[str, ...]:
        if not determination_id:
            return ()
        db = self._agent_db()
        rows = db.db.execute_query(
            """
            SELECT task_id FROM agents_autonomous_tasks
            WHERE discovered_by = ? AND origin_continuity_id = ?
            ORDER BY priority_score DESC, discovered_at ASC
            """,
            (READONLY_AUDIT_TASK_SOURCE, determination_id),
        )
        return tuple(str(row["task_id"] if isinstance(row, Mapping) else row[0]) for row in rows)

    def load_task_status_counts(self, task_ids: Sequence[str]) -> Mapping[str, int]:
        if not task_ids:
            return {}
        db = self._agent_db()
        counts: dict[str, int] = {}
        for task_id in task_ids:
            rows = db.db.execute_query(
                "SELECT status FROM agents_autonomous_tasks WHERE task_id = ?",
                (task_id,),
            )
            if rows and isinstance(rows[0], Mapping):
                status = str(rows[0]["status"])
            elif rows:
                status = str(rows[0][0])
            else:
                status = "missing"
            counts[status] = counts.get(status, 0) + 1
        return counts

    def delete_cycle_tasks(self, task_ids: Sequence[str]) -> None:
        if not task_ids:
            return
        db = self._agent_db()
        with db.db.get_connection() as conn:
            for task_id in task_ids:
                conn.execute(
                    """
                    DELETE FROM agents_autonomous_tasks
                    WHERE task_id = ? AND discovered_by = ? AND status IN ('failed', 'pending', 'assigned')
                    """,
                    (task_id, READONLY_AUDIT_TASK_SOURCE),
                )

    def _agent_db(self) -> Any:
        factory = self._agent_db_factory
        if factory is None:
            from modules.infrastructure.database.src.agent_db import AgentDB

            factory = AgentDB
        return factory()

    @staticmethod
    def _ensure_table(db: Any) -> None:
        with db.db.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reddog_resident_architect_cycles (
                    intent_id TEXT PRIMARY KEY,
                    cycle_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    snapshot_id TEXT,
                    determination_id TEXT,
                    revision INTEGER NOT NULL DEFAULT 0,
                    cycle_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            columns = {
                str(row["name"] if isinstance(row, Mapping) else row[1])
                for row in conn.execute(
                    "PRAGMA table_info(reddog_resident_architect_cycles)"
                ).fetchall()
            }
            if "revision" not in columns:
                conn.execute(
                    "ALTER TABLE reddog_resident_architect_cycles "
                    "ADD COLUMN revision INTEGER NOT NULL DEFAULT 0"
                )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_reddog_resident_architect_cycles_status
                ON reddog_resident_architect_cycles(status)
                """
            )


def run_reddog_resident_architect_durable_agentdb_cycle(
    *,
    repo_root: Path | str,
    red_dog_intent: Mapping[str, Any],
    work_state_path: Path | str | None = None,
    holoindex_receipt_path: Path | str | None = None,
    holoindex_ssd_path: Path | str | None = None,
    changed_paths: Sequence[str] = DEFAULT_BOOTSTRAP_CHANGED_PATHS,
    allowed_read_targets: Sequence[str] = DEFAULT_BOOTSTRAP_READ_TARGETS,
    requested_operation: str = "extension_resident_architect_session",
    prompt_text: str = "extension resident RedDog architect session",
    now_iso: str | None = None,
    repo_state_override: Mapping[str, Any] | None = None,
    work_state_snapshot_override: Mapping[str, Any] | None = None,
    holoindex_receipt_override: HoloIndexFreshnessReceipt | Mapping[str, Any] | None = None,
    breadcrumbs: Sequence[Mapping[str, Any]] = (),
    brain_state: Mapping[str, Any] | None = None,
    workspace_memory_notes: Sequence[Mapping[str, Any]] = (),
    memex_snapshot_supply_config: OperationalMemexSnapshotSupplyConfig | Mapping[str, Any] | None = None,
    audit_lanes: Sequence[str] = DEFAULT_AUDIT_LANES,
    cycle_store: ResidentArchitectCycleStore | None = None,
    agent_db_factory: Optional[Callable[[], Any]] = None,
    report_store: ReadOnlyAuditReportStore | None = None,
    decision_store: ReadOnlyAuditDecisionStore | None = None,
    architect_model_runner: ArchitectModelRunner | None = None,
    architect_model_runtime_binding_receipt: Mapping[str, Any] | None = None,
    architect_determination_store: ArchitectDeterminationStore | None = None,
    audit_model_runner: RepoAuditModelRunner | None = None,
    audit_model_runtime_binding_receipt: Mapping[str, Any] | None = None,
    holoindex_adapter: ReadOnlyEvidenceQueryAdapter | None = None,
    codeindex_adapter: ReadOnlyEvidenceQueryAdapter | None = None,
    external_research_retriever: ExternalResearchRetriever | None = None,
    openclaw_claim_runner: Optional[Callable[..., Mapping[str, Any]]] = None,
    max_claims: int = 8,
    timeout_seconds: int = 60,
    cancel_requested: bool = False,
    retry_requested: bool = False,
) -> RedDogResidentArchitectCycleResult:
    """Submit or resume one durable resident RedDog architect cycle."""

    root = Path(repo_root).resolve()
    store = cycle_store or AgentDbResidentArchitectCycleStore(agent_db_factory=agent_db_factory)
    reasons = _validate_intent(red_dog_intent)
    intent_id = str(red_dog_intent.get("intent_id") or "").strip()
    existing = store.load_cycle_by_intent(intent_id) if intent_id else None
    submitted_intent_digest = resident_intent_digest(red_dog_intent)

    if cancel_requested:
        if existing is None:
            if reasons:
                return _reject(red_dog_intent, reasons)
            synthetic = _new_record(red_dog_intent, retry_count=0)
            synthetic.update(
                {
                    "status": STATUS_CANCELLED,
                    "cancelled_at": _now_iso(),
                    "rejection_reasons": [ResidentCycleReason.CANCELLED],
                }
            )
            return _result_from_record(
                record=synthetic,
                accepted=False,
                rejection_reasons=(ResidentCycleReason.CANCELLED,),
            )
        if not _record_matches_cancel_request(existing, submitted_intent_digest):
            return _result_from_record(
                record=existing,
                accepted=False,
                rejection_reasons=(ResidentCycleReason.INTENT_CONFLICT,),
            )
        existing, cancelled = _cancel_cycle_with_retry(store, existing)
        return _result_from_record(
            record=existing,
            accepted=False,
            rejection_reasons=(
                ResidentCycleReason.CANCELLED if cancelled else ResidentCycleReason.CANCELLATION_CONFLICT,
            ),
        )

    if existing is not None and (
        existing.get("_store_integrity_valid") is not True
        or str(existing.get("intent_digest") or "") != submitted_intent_digest
        or any(existing.get(field) is not True for field in RUNTIME_BOUNDARY_FIELDS)
    ):
        return _result_from_record(
            record=existing,
            accepted=False,
            rejection_reasons=(ResidentCycleReason.INTENT_CONFLICT,),
        )

    retry_source: Mapping[str, Any] | None = None
    if existing is not None and retry_requested:
        status = str(existing.get("status") or "")
        if status not in {STATUS_FAILED, STATUS_TIMED_OUT}:
            return _result_from_record(
                record=existing,
                accepted=False,
                rejection_reasons=(ResidentCycleReason.RETRY_NOT_ALLOWED,),
            )
        old_tasks = tuple(str(task_id) for task_id in existing.get("task_ids", ()) if str(task_id))
        retry_source = existing
        retry_count = int(existing.get("retry_count", 0)) + 1
        retried = _new_record(red_dog_intent, retry_count=retry_count)
        retried["created_at"] = existing.get("created_at")
        retried["genesis_state_digest"] = existing.get("genesis_state_digest")
        retried["attempt_history"] = [
            *list(existing.get("attempt_history") or ()),
            _attempt_history_entry(existing),
        ]
        transitioned = _transition_record(
            store,
            existing,
            expected_statuses=(STATUS_FAILED, STATUS_TIMED_OUT, STATUS_CANCELLED),
            updates=retried,
            allow_terminal_retry=True,
        )
        if transitioned is None:
            return _transition_conflict_result(store, intent_id)
        store.delete_cycle_tasks(old_tasks)
        existing = None

    if existing is not None and str(existing.get("status")) == STATUS_DETERMINED:
        return _result_from_record(record=existing, accepted=True, duplicate_intent_reused=True)

    if existing is not None:
        return _result_from_record(
            record=existing,
            accepted=False,
            rejection_reasons=(ResidentCycleReason.ACTIVE_INTENT,),
            recovered_existing_cycle=True,
        )

    if reasons:
        return _reject(red_dog_intent, reasons)
    if external_research_retriever is None:
        external_research_retriever = NoopExternalResearchRetriever()

    retry_count = int(retry_source.get("retry_count", 0)) + 1 if retry_source else 0
    record = (
        dict(store.load_cycle_by_intent(intent_id) or {})
        if retry_source is not None
        else _new_record(red_dog_intent, retry_count=retry_count)
    )
    recovered = retry_source is not None

    if retry_source is None:
        created = store.create_cycle(record)
        if not created.get("ok"):
            latest = store.load_cycle_by_intent(intent_id)
            if isinstance(latest, Mapping) and str(latest.get("intent_digest") or "") != submitted_intent_digest:
                return _result_from_record(
                    record=latest,
                    accepted=False,
                    rejection_reasons=(ResidentCycleReason.INTENT_CONFLICT,),
                )
            return _transition_conflict_result(store, intent_id)
        record = dict(created.get("record") or record)

    if str(record.get("status") or "") == STATUS_SUBMITTED:
        initial = run_reddog_main_readonly_operational_bootstrap(
            repo_root=root,
            work_state_path=work_state_path,
            holoindex_receipt_path=holoindex_receipt_path,
            holoindex_ssd_path=holoindex_ssd_path,
            changed_paths=changed_paths,
            allowed_read_targets=allowed_read_targets,
            requested_operation=requested_operation,
            prompt_text=prompt_text,
            now_iso=now_iso,
            repo_state_override=repo_state_override,
            work_state_snapshot_override=work_state_snapshot_override,
            holoindex_receipt_override=holoindex_receipt_override,
            breadcrumbs=breadcrumbs,
            brain_state=brain_state,
            workspace_memory_notes=workspace_memory_notes,
            audit_lanes=audit_lanes,
            enqueue_readonly_audit_tasks=True,
            enqueue_writer=AgentDbReadOnlyAuditTaskWriter(agent_db_factory=agent_db_factory),
            memex_snapshot_supply_config=_intent_bound_memex_config(
                red_dog_intent=red_dog_intent,
                config=memex_snapshot_supply_config,
            ),
            grounding_receipt=red_dog_intent.get("grounding_receipt"),
            grounding_work_focus=str(red_dog_intent.get("work_focus") or prompt_text),
            audit_model_runtime_binding_receipt=audit_model_runtime_binding_receipt,
            require_audit_model_runtime_binding=audit_model_runner is None,
        )
        if not initial.ready or initial.status != REDDOG_MAIN_BOOTSTRAP_READY:
            transitioned = _transition_record(
                store,
                record,
                expected_statuses=(STATUS_SUBMITTED,),
                updates=_failure_updates(
                    STATUS_FAILED,
                    (ResidentCycleReason.BOOTSTRAP_REJECTED, *initial.rejection_reasons),
                ),
            )
            if transitioned is None:
                return _transition_conflict_result(store, intent_id)
            record = transitioned
            return _result_from_record(record=record, accepted=False)
        if not initial.enqueue_attempted or initial.enqueue_task_count <= 0 or initial.enqueue_rejection_reasons:
            transitioned = _transition_record(
                store,
                record,
                expected_statuses=(STATUS_SUBMITTED,),
                updates=_failure_updates(
                    STATUS_FAILED,
                    (ResidentCycleReason.TASK_ENQUEUE_REJECTED, *initial.enqueue_rejection_reasons),
                ),
            )
            if transitioned is None:
                return _transition_conflict_result(store, intent_id)
            record = transitioned
            return _result_from_record(record=record, accepted=False)
        task_ids = store.load_task_ids(str(initial.determination_id or ""))
        if not task_ids:
            transitioned = _transition_record(
                store,
                record,
                expected_statuses=(STATUS_SUBMITTED,),
                updates=_failure_updates(STATUS_FAILED, (ResidentCycleReason.NO_TASK_IDS,)),
            )
            if transitioned is None:
                return _transition_conflict_result(store, intent_id)
            record = transitioned
            return _result_from_record(record=record, accepted=False)
        transitioned = _transition_record(
            store,
            record,
            expected_statuses=(STATUS_SUBMITTED,),
            updates={
                "status": STATUS_ENQUEUED,
                "snapshot_id": initial.snapshot_receipt_id,
                "determination_id": initial.determination_id,
                "swarm_id": initial.swarm_id,
                "task_ids": list(task_ids),
                "task_status_counts": dict(store.load_task_status_counts(task_ids)),
                "initial_bootstrap": initial.to_dict(),
                "updated_at": _now_iso(),
            },
        )
        if transitioned is None:
            return _transition_conflict_result(store, intent_id)
        record = transitioned

    if str(record.get("status") or "") == STATUS_ENQUEUED:
        transitioned = _transition_record(
            store,
            record,
            expected_statuses=(STATUS_ENQUEUED,),
            updates={"status": STATUS_RUNNING, "updated_at": _now_iso()},
        )
        if transitioned is None:
            return _transition_conflict_result(store, intent_id)
        record = transitioned

    task_ids = tuple(str(task_id) for task_id in record.get("task_ids", ()) if str(task_id))
    claims: list[Mapping[str, Any]] = []
    claim_runner = openclaw_claim_runner or claim_reddog_readonly_audit_task_once
    for _ in range(max(0, int(max_claims))):
        checkpoint = _checkpoint_record(store, record)
        if checkpoint is None or str(checkpoint.get("status") or "") == STATUS_CANCELLED:
            return _transition_conflict_result(store, intent_id)
        record = checkpoint
        counts = dict(store.load_task_status_counts(task_ids))
        if task_ids and counts.get("completed", 0) == len(task_ids):
            break
        claim = dict(
            claim_runner(
                repo_root=root,
                agent_db_factory=agent_db_factory,
                report_store=report_store or AgentDbReadOnlyAuditReportStore(agent_db_factory=agent_db_factory),
                audit_model_runner=audit_model_runner,
                holoindex_adapter=holoindex_adapter,
                codeindex_adapter=codeindex_adapter,
                external_research_retriever=external_research_retriever,
                timeout_seconds=timeout_seconds,
            )
        )
        claims.append(claim)
        transitioned = _transition_record(
            store,
            record,
            expected_statuses=(STATUS_RUNNING,),
            updates={
                "openclaw_claims": [dict(item) for item in claims],
                "task_status_counts": dict(store.load_task_status_counts(task_ids)),
                "updated_at": _now_iso(),
            },
        )
        if transitioned is None:
            return _transition_conflict_result(store, intent_id)
        record = transitioned
        if claim.get("status") == READONLY_AUDIT_OPENCLAW_CLAIM_IDLE:
            break
        if claim.get("status") != READONLY_AUDIT_OPENCLAW_CLAIM_ACCEPT:
            updates = _failure_updates(
                    STATUS_FAILED,
                    (ResidentCycleReason.OPENCLAW_CLAIM_REJECTED, *claim.get("rejection_reasons", ())),
                )
            updates["openclaw_claims"] = [dict(item) for item in claims]
            updates["task_status_counts"] = dict(store.load_task_status_counts(task_ids))
            transitioned = _transition_record(
                store,
                record,
                expected_statuses=(STATUS_RUNNING,),
                updates=updates,
            )
            if transitioned is None:
                return _transition_conflict_result(store, intent_id)
            record = transitioned
            return _result_from_record(record=record, accepted=False, recovered_existing_cycle=recovered)

    counts = dict(store.load_task_status_counts(task_ids))
    record["task_status_counts"] = counts
    record["openclaw_claims"] = [dict(item) for item in claims]
    if not task_ids or counts.get("completed", 0) != len(task_ids):
        updates = _failure_updates(STATUS_TIMED_OUT, (ResidentCycleReason.TIMEOUT,))
        updates["task_status_counts"] = counts
        updates["openclaw_claims"] = [dict(item) for item in claims]
        transitioned = _transition_record(
            store,
            record,
            expected_statuses=(STATUS_RUNNING,),
            updates=updates,
        )
        if transitioned is None:
            return _transition_conflict_result(store, intent_id)
        record = transitioned
        return _result_from_record(record=record, accepted=False, recovered_existing_cycle=recovered)

    checkpoint = _checkpoint_record(store, record)
    if checkpoint is None or str(checkpoint.get("status") or "") == STATUS_CANCELLED:
        return _transition_conflict_result(store, intent_id)
    record = checkpoint

    final = run_reddog_main_readonly_operational_bootstrap(
        repo_root=root,
        work_state_path=work_state_path,
        holoindex_receipt_path=holoindex_receipt_path,
        holoindex_ssd_path=holoindex_ssd_path,
        changed_paths=changed_paths,
        allowed_read_targets=allowed_read_targets,
        requested_operation=requested_operation,
        prompt_text=prompt_text,
        now_iso=now_iso,
        repo_state_override=repo_state_override,
        work_state_snapshot_override=work_state_snapshot_override,
        holoindex_receipt_override=holoindex_receipt_override,
        breadcrumbs=breadcrumbs,
        brain_state=brain_state,
        workspace_memory_notes=workspace_memory_notes,
        grounding_receipt=red_dog_intent.get("grounding_receipt"),
        grounding_work_focus=str(red_dog_intent.get("work_focus") or prompt_text),
        audit_model_runtime_binding_receipt=audit_model_runtime_binding_receipt,
        require_audit_model_runtime_binding=audit_model_runner is None,
        audit_lanes=audit_lanes,
        collect_readonly_audit_reports=True,
        report_store=report_store or AgentDbReadOnlyAuditReportStore(agent_db_factory=agent_db_factory),
        persist_readonly_audit_decision=True,
        decision_store=decision_store,
        run_backend_architect_determination=True,
        architect_model_runner=architect_model_runner,
        architect_model_runtime_binding_receipt_override=architect_model_runtime_binding_receipt,
        architect_determination_store=architect_determination_store,
    )
    if not final.ready:
        updates = _failure_updates(
                STATUS_FAILED,
                (ResidentCycleReason.FINAL_BOOTSTRAP_REJECTED, *final.rejection_reasons),
            )
        updates["final_bootstrap"] = final.to_dict()
        transitioned = _transition_record(
            store,
            record,
            expected_statuses=(STATUS_RUNNING,),
            updates=updates,
        )
        if transitioned is None:
            return _transition_conflict_result(store, intent_id)
        record = transitioned
        return _result_from_record(
            record=record,
            accepted=False,
            final_bootstrap=final,
            recovered_existing_cycle=recovered,
        )
    if not final.backend_architect_determination_id:
        updates = _failure_updates(
            STATUS_FAILED,
            (ResidentCycleReason.ARCHITECT_DETERMINATION_MISSING,),
        )
        updates["final_bootstrap"] = final.to_dict()
        transitioned = _transition_record(
            store,
            record,
            expected_statuses=(STATUS_RUNNING,),
            updates=updates,
        )
        if transitioned is None:
            return _transition_conflict_result(store, intent_id)
        record = transitioned
        return _result_from_record(
            record=record,
            accepted=False,
            final_bootstrap=final,
            recovered_existing_cycle=recovered,
        )

    transitioned = _transition_record(
        store,
        record,
        expected_statuses=(STATUS_RUNNING,),
        updates={
            "status": STATUS_DETERMINED,
            "rejection_reasons": [],
            "final_bootstrap": final.to_dict(),
            "architect_action": final.backend_architect_determination_action,
            "architect_next_slice": final.backend_architect_determination_next_slice,
            "architect_determination_id": final.backend_architect_determination_id,
            "queue_candidate_count": final.backend_architect_determination_queue_candidate_count,
            "updated_at": _now_iso(),
        },
    )
    if transitioned is None:
        return _transition_conflict_result(store, intent_id)
    record = transitioned
    return _result_from_record(record=record, accepted=True, final_bootstrap=final, recovered_existing_cycle=recovered)


def _new_record(intent: Mapping[str, Any], *, retry_count: int) -> dict[str, Any]:
    intent_id = str(intent.get("intent_id") or "").strip()
    record = {
        "schema_version": "reddog_resident_architect_cycle.v2",
        "intent_id": intent_id,
        "intent_digest": resident_intent_digest(intent),
        "cycle_id": _digest({"intent_id": intent_id, "retry_count": retry_count, "slice": "resident_agentdb_cycle"}),
        "status": STATUS_SUBMITTED,
        "intent": dict(intent),
        "snapshot_id": None,
        "determination_id": None,
        "swarm_id": None,
        "task_ids": [],
        "task_status_counts": {},
        "openclaw_claims": [],
        "retry_count": retry_count,
        "record_revision": 0,
        "attempt_history": [],
        "transition_history": [],
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "rejection_reasons": [],
    }
    record.update({field: True for field in RUNTIME_BOUNDARY_FIELDS})
    record["genesis_state_digest"] = _genesis_state_digest(record)
    return record


def _validate_intent(intent: Mapping[str, Any]) -> tuple[str, ...]:
    reasons: list[str] = []
    schema = intent.get("schema_version") if isinstance(intent, Mapping) else None
    main_v1 = bool(
        schema == "reddog_intent.v1"
        and intent.get("origin") == "main.py"
        and intent.get("requested_authority") == "read_only_audit"
    )
    if not isinstance(intent, Mapping) or (schema != "reddog_intent.v2" and not main_v1):
        reasons.append(ResidentCycleReason.INTENT_INVALID)
    if not str(intent.get("intent_id") or "").strip():
        reasons.append(ResidentCycleReason.INTENT_INVALID)
    if intent.get("submits_executable_authority") is not False:
        reasons.append(ResidentCycleReason.EXECUTABLE_AUTHORITY_REQUESTED)
    if isinstance(intent, Mapping) and schema == "reddog_intent.v2":
        grounding = validate_grounded_target_receipt(
            intent.get("grounding_receipt") if isinstance(intent.get("grounding_receipt"), Mapping) else None,
            work_focus=str(intent.get("work_focus") or ""),
        )
        reasons.extend(grounding.rejection_reasons)
    return tuple(dict.fromkeys(reasons))


def _intent_bound_memex_config(
    *,
    red_dog_intent: Mapping[str, Any],
    config: OperationalMemexSnapshotSupplyConfig | Mapping[str, Any] | None,
) -> OperationalMemexSnapshotSupplyConfig | Mapping[str, Any] | None:
    if config is None:
        return None
    if isinstance(config, OperationalMemexSnapshotSupplyConfig):
        if config.principal_id:
            return config
        return OperationalMemexSnapshotSupplyConfig(
            foundup_id=config.foundup_id,
            principal_id=_principal_id(red_dog_intent),
            identity=config.identity,
            roadmap_state=config.roadmap_state,
            verified_outcomes=config.verified_outcomes,
            policy_issued_at=config.policy_issued_at,
            policy_expires_at=config.policy_expires_at,
            holoindex_generation_id=config.holoindex_generation_id,
            source_revision=config.source_revision,
            max_records=config.max_records,
        )
    data = dict(config)
    data.setdefault("principal_id", _principal_id(red_dog_intent))
    data.setdefault("foundup_id", str(red_dog_intent.get("foundup_id") or "").strip())
    return data


def _principal_id(intent: Mapping[str, Any]) -> str:
    return str(
        intent.get("principal_id")
        or intent.get("principal_ref")
        or intent.get("origin_principal")
        or ""
    ).strip()


def _failure_updates(status: str, reasons: Sequence[str]) -> dict[str, Any]:
    return {
        "status": status,
        "rejection_reasons": list(dict.fromkeys(str(reason) for reason in reasons if str(reason).strip())),
        "updated_at": _now_iso(),
    }


def resident_intent_digest(intent: Mapping[str, Any]) -> str:
    return _digest({"schema_version": "reddog_resident_intent_binding.v1", "intent": dict(intent)})


def _attempt_history_entry(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "cycle_id": str(record.get("cycle_id") or ""),
        "status": str(record.get("status") or ""),
        "record_revision": int(record.get("record_revision") or 0),
        "retry_count": int(record.get("retry_count") or 0),
        "task_ids": [str(task_id) for task_id in record.get("task_ids", ()) if str(task_id)],
        "closed_at": _now_iso(),
    }


def _validate_retry_transition(
    *,
    current: Mapping[str, Any],
    updates: Mapping[str, Any],
    allow_terminal_retry: bool,
    next_status: str,
) -> str:
    current_retry = int(current.get("retry_count") or 0)
    current_history = list(current.get("attempt_history") or ())
    is_retry = bool(allow_terminal_retry and next_status == STATUS_SUBMITTED)
    if not is_retry:
        if "retry_count" in updates and int(updates.get("retry_count") or 0) != current_retry:
            return "retry_count_not_monotonic"
        if "attempt_history" in updates and list(updates.get("attempt_history") or ()) != current_history:
            return "attempt_history_not_monotonic"
        return ""

    expected_retry = current_retry + 1
    if int(updates.get("retry_count") or -1) != expected_retry:
        return "retry_count_not_monotonic"
    history = list(updates.get("attempt_history") or ())
    if len(history) != len(current_history) + 1 or history[:-1] != current_history:
        return "attempt_history_not_monotonic"
    entry = history[-1] if isinstance(history[-1], Mapping) else {}
    expected_entry = {
        "cycle_id": str(current.get("cycle_id") or ""),
        "status": str(current.get("status") or ""),
        "record_revision": int(current.get("record_revision") or 0),
        "retry_count": current_retry,
        "task_ids": [str(task_id) for task_id in current.get("task_ids", ()) if str(task_id)],
    }
    if any(entry.get(key) != value for key, value in expected_entry.items()) or not str(
        entry.get("closed_at") or ""
    ):
        return "attempt_history_not_monotonic"
    expected_cycle_id = _digest(
        {
            "intent_id": str(current.get("intent_id") or ""),
            "retry_count": expected_retry,
            "slice": "resident_agentdb_cycle",
        }
    )
    if str(updates.get("cycle_id") or "") != expected_cycle_id:
        return "retry_cycle_id_invalid"
    return ""


def _transition_history_is_valid(record: Mapping[str, Any], *, revision: int) -> bool:
    history = record.get("transition_history")
    if not isinstance(history, list) or len(history) != revision:
        return False
    intent_id = str(record.get("intent_id") or "")
    retry_count = _parse_nonnegative_int(record.get("retry_count"))
    if retry_count is None:
        return False
    if not history:
        return bool(
            revision == 0
            and frozenset(key for key in record if not str(key).startswith("_store_"))
            == GENESIS_RECORD_FIELDS
            and str(record.get("status") or "") == STATUS_SUBMITTED
            and retry_count == 0
            and record.get("attempt_history") == []
            and str(record.get("cycle_id") or "")
            == _digest({"intent_id": intent_id, "retry_count": 0, "slice": "resident_agentdb_cycle"})
            and str(record.get("genesis_state_digest") or "") == _genesis_state_digest(record)
        )
    previous_receipt_id = ""
    previous_status = ""
    retry_edges = 0
    for index, raw_entry in enumerate(history):
        if not isinstance(raw_entry, Mapping):
            return False
        entry = dict(raw_entry)
        receipt_id = str(entry.pop("receipt_id", ""))
        from_revision = _parse_nonnegative_int(entry.get("from_revision"))
        to_revision = _parse_nonnegative_int(entry.get("to_revision"))
        if (
            entry.get("schema_version") != "reddog_resident_cycle_transition.v1"
            or str(entry.get("intent_id") or "") != str(record.get("intent_id") or "")
            or from_revision != index
            or to_revision != index + 1
            or str(entry.get("previous_receipt_id") or "") != previous_receipt_id
            or entry.get("authority") != "observational_internal_integrity_only"
            or receipt_id != _digest(entry)
        ):
            return False
        from_status = str(entry.get("from_status") or "")
        to_status = str(entry.get("to_status") or "")
        if index == 0 and from_status != STATUS_SUBMITTED:
            return False
        if index and from_status != previous_status:
            return False
        if from_status in {STATUS_FAILED, STATUS_TIMED_OUT} and to_status == STATUS_SUBMITTED:
            retry_edges += 1
        elif from_status in TERMINAL_STATUSES:
            return False
        elif to_status not in ALLOWED_STATUS_TRANSITIONS.get(from_status, ()):
            return False
        previous_status = to_status
        previous_receipt_id = receipt_id
    state_for_digest = dict(record)
    state_for_digest.pop("transition_history", None)
    state_for_digest.pop("_store_integrity_valid", None)
    state_for_digest.pop("_store_revision", None)
    final_state_digest = str(history[-1].get("result_state_digest") or "")
    return (
        previous_status == str(record.get("status") or "")
        and retry_edges == retry_count
        and len(record.get("attempt_history") or ()) == retry_edges
        and final_state_digest == _digest(state_for_digest)
    )


def _record_matches_cancel_request(record: Mapping[str, Any], submitted_intent_digest: str) -> bool:
    if (
        record.get("_store_integrity_valid") is True
        and str(record.get("intent_digest") or "") == submitted_intent_digest
        and all(record.get(field) is True for field in RUNTIME_BOUNDARY_FIELDS)
    ):
        return True
    intent = record.get("intent")
    return bool(
        (
            str(record.get("status") or "") not in TERMINAL_STATUSES
            or str(record.get("status") or "") == STATUS_CANCELLED
        )
        and not str(record.get("intent_digest") or "")
        and isinstance(intent, Mapping)
        and resident_intent_digest(intent) == submitted_intent_digest
    )


def _parse_nonnegative_int(value: Any) -> Optional[int]:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _genesis_state_digest(record: Mapping[str, Any]) -> str:
    value = {
        str(key): item
        for key, item in record.items()
        if key != "genesis_state_digest" and not str(key).startswith("_store_")
    }
    return _digest({"schema_version": "reddog_resident_cycle_genesis.v1", "record": value})


def _cancel_cycle_with_retry(
    store: ResidentArchitectCycleStore,
    existing: Mapping[str, Any],
    *,
    max_attempts: int = 3,
) -> tuple[dict[str, Any], bool]:
    intent_id = str(existing.get("intent_id") or "")
    current = dict(existing)
    for _ in range(max(1, int(max_attempts))):
        status = str(current.get("status") or "")
        if status == STATUS_CANCELLED:
            return current, True
        if status in TERMINAL_STATUSES:
            return current, False
        transitioned = _transition_record(
            store,
            current,
            expected_statuses=(STATUS_SUBMITTED, STATUS_ENQUEUED, STATUS_RUNNING),
            updates={
                "status": STATUS_CANCELLED,
                "cancelled_at": _now_iso(),
                "rejection_reasons": [ResidentCycleReason.CANCELLED],
                "updated_at": _now_iso(),
            },
        )
        if transitioned is not None:
            return transitioned, True
        latest = store.load_cycle_by_intent(intent_id)
        if not isinstance(latest, Mapping):
            break
        current = dict(latest)
    return current, str(current.get("status") or "") == STATUS_CANCELLED


def _transition_record(
    store: ResidentArchitectCycleStore,
    record: Mapping[str, Any],
    *,
    expected_statuses: Sequence[str],
    updates: Mapping[str, Any],
    allow_terminal_retry: bool = False,
) -> Optional[dict[str, Any]]:
    transition = getattr(store, "transition_cycle", None)
    if not callable(transition):
        return None
    result = transition(
        str(record.get("intent_id") or ""),
        expected_revision=int(record.get("record_revision", record.get("_store_revision", -1))),
        expected_statuses=tuple(expected_statuses),
        updates=dict(updates),
        allow_terminal_retry=allow_terminal_retry,
    )
    if not isinstance(result, Mapping):
        return None
    value = result.get("record")
    return dict(value) if result.get("ok") and isinstance(value, Mapping) else None


def _checkpoint_record(
    store: ResidentArchitectCycleStore,
    record: Mapping[str, Any],
) -> Optional[dict[str, Any]]:
    latest = store.load_cycle_by_intent(str(record.get("intent_id") or ""))
    if not isinstance(latest, Mapping):
        return None
    if latest.get("_store_integrity_valid") is not True:
        return None
    if int(latest.get("record_revision", -1)) != int(record.get("record_revision", -2)):
        return dict(latest) if str(latest.get("status") or "") == STATUS_CANCELLED else None
    return dict(latest)


def _transition_conflict_result(
    store: ResidentArchitectCycleStore,
    intent_id: str,
) -> RedDogResidentArchitectCycleResult:
    latest = store.load_cycle_by_intent(intent_id)
    record = dict(latest) if isinstance(latest, Mapping) else _new_record({"intent_id": intent_id}, retry_count=0)
    if str(record.get("status") or "") == STATUS_CANCELLED:
        reasons = (ResidentCycleReason.CANCELLED,)
    else:
        reasons = (ResidentCycleReason.TRANSITION_CONFLICT,)
    return _result_from_record(record=record, accepted=False, rejection_reasons=reasons)


def _reject(intent: Mapping[str, Any], reasons: Sequence[str]) -> RedDogResidentArchitectCycleResult:
    record = _new_record(intent if isinstance(intent, Mapping) else {}, retry_count=0)
    record.update(_failure_updates(STATUS_FAILED, reasons))
    return _result_from_record(record=record, accepted=False)


def _result_from_record(
    *,
    record: Mapping[str, Any],
    accepted: bool,
    rejection_reasons: Sequence[str] | None = None,
    final_bootstrap: RedDogMainReadonlyBootstrapResult | None = None,
    duplicate_intent_reused: bool = False,
    recovered_existing_cycle: bool = False,
) -> RedDogResidentArchitectCycleResult:
    reasons = tuple(rejection_reasons) if rejection_reasons is not None else tuple(record.get("rejection_reasons", ()))
    final = final_bootstrap
    return RedDogResidentArchitectCycleResult(
        accepted=accepted,
        decision=REDDOG_RESIDENT_CYCLE_ACCEPT if accepted else REDDOG_RESIDENT_CYCLE_REJECT,
        status=str(record.get("status") or STATUS_FAILED),
        intent_id=str(record.get("intent_id") or ""),
        cycle_id=str(record.get("cycle_id") or ""),
        snapshot_id=_optional_string(record.get("snapshot_id")),
        determination_id=_optional_string(record.get("determination_id")),
        swarm_id=_optional_string(record.get("swarm_id")),
        task_ids=tuple(str(task_id) for task_id in record.get("task_ids", ()) if str(task_id)),
        task_status_counts=dict(record.get("task_status_counts") or {}),
        openclaw_claims=tuple(dict(item) for item in record.get("openclaw_claims", ()) if isinstance(item, Mapping)),
        final_bootstrap=final,
        architect_action=_optional_string(record.get("architect_action")),
        architect_next_slice=_optional_string(record.get("architect_next_slice")),
        architect_determination_id=_optional_string(record.get("architect_determination_id")),
        queue_candidate_count=int(record.get("queue_candidate_count") or 0),
        duplicate_intent_reused=duplicate_intent_reused,
        recovered_existing_cycle=recovered_existing_cycle,
        retry_count=int(record.get("retry_count") or 0),
        record_revision=int(record.get("record_revision") or 0),
        intent_digest=str(record.get("intent_digest") or ""),
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason).strip())),
        **{
            field: record.get(field) is True
            for field in RUNTIME_BOUNDARY_FIELDS
        },
    )


def _optional_string(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _digest(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "AgentDbResidentArchitectCycleStore",
    "NoopExternalResearchRetriever",
    "REDDOG_RESIDENT_CYCLE_ACCEPT",
    "REDDOG_RESIDENT_CYCLE_REJECT",
    "RedDogResidentArchitectCycleResult",
    "ResidentCycleReason",
    "RUNTIME_BOUNDARY_FIELDS",
    "STATUS_CANCELLED",
    "STATUS_DETERMINED",
    "STATUS_ENQUEUED",
    "STATUS_FAILED",
    "STATUS_RUNNING",
    "STATUS_SUBMITTED",
    "STATUS_TIMED_OUT",
    "resident_intent_digest",
    "run_reddog_resident_architect_durable_agentdb_cycle",
]
