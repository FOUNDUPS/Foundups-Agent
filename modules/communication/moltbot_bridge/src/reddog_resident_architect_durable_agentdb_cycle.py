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


class ResidentArchitectCycleStore(Protocol):
    def load_cycle_by_intent(self, intent_id: str) -> Optional[Mapping[str, Any]]: ...

    def upsert_cycle(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def update_cycle(self, intent_id: str, updates: Mapping[str, Any]) -> Mapping[str, Any]: ...

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
            "SELECT cycle_json FROM reddog_resident_architect_cycles WHERE intent_id = ?",
            (intent_id,),
        )
        if not rows:
            return None
        value = rows[0]["cycle_json"] if isinstance(rows[0], Mapping) else rows[0][0]
        return json.loads(value)

    def upsert_cycle(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        db = self._agent_db()
        self._ensure_table(db)
        payload = _canonical_json(record)
        with db.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO reddog_resident_architect_cycles
                (intent_id, cycle_id, status, snapshot_id, determination_id, cycle_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(intent_id) DO UPDATE SET
                    cycle_id = excluded.cycle_id,
                    status = excluded.status,
                    snapshot_id = excluded.snapshot_id,
                    determination_id = excluded.determination_id,
                    cycle_json = excluded.cycle_json,
                    updated_at = excluded.updated_at
                """,
                (
                    record.get("intent_id"),
                    record.get("cycle_id"),
                    record.get("status"),
                    record.get("snapshot_id"),
                    record.get("determination_id"),
                    payload,
                    _now_iso(),
                ),
            )
        return {"ok": True, "stored": True}

    def update_cycle(self, intent_id: str, updates: Mapping[str, Any]) -> Mapping[str, Any]:
        current = self.load_cycle_by_intent(intent_id)
        if current is None:
            return {"ok": False, "reason": "missing_cycle"}
        merged = dict(current)
        merged.update(dict(updates))
        return self.upsert_cycle(merged)

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
                    cycle_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
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
    architect_determination_store: ArchitectDeterminationStore | None = None,
    audit_model_runner: RepoAuditModelRunner | None = None,
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
    existing = store.load_cycle_by_intent(intent_id) if intent_id and not reasons else None

    if cancel_requested:
        if existing is not None and str(existing.get("status")) not in TERMINAL_STATUSES:
            store.update_cycle(intent_id, {"status": STATUS_CANCELLED, "cancelled_at": _now_iso()})
        return _result_from_record(
            record=store.load_cycle_by_intent(intent_id) or existing or _new_record(red_dog_intent, retry_count=0),
            accepted=False,
            rejection_reasons=(ResidentCycleReason.CANCELLED,),
        )

    if existing is not None and retry_requested:
        status = str(existing.get("status") or "")
        if status not in {STATUS_FAILED, STATUS_TIMED_OUT, STATUS_CANCELLED}:
            return _result_from_record(
                record=existing,
                accepted=False,
                rejection_reasons=(ResidentCycleReason.RETRY_NOT_ALLOWED,),
            )
        old_tasks = tuple(str(task_id) for task_id in existing.get("task_ids", ()) if str(task_id))
        store.delete_cycle_tasks(old_tasks)
        existing = None

    if existing is not None and str(existing.get("status")) == STATUS_DETERMINED:
        return _result_from_record(record=existing, accepted=True, duplicate_intent_reused=True)

    if reasons:
        return _reject(red_dog_intent, reasons)
    if external_research_retriever is None:
        external_research_retriever = NoopExternalResearchRetriever()

    if retry_requested:
        retry_count = int(existing.get("retry_count", 0)) + 1 if existing else 1
    elif existing:
        retry_count = int(existing.get("retry_count", 0))
    else:
        retry_count = 0
    record = dict(existing) if existing is not None else _new_record(red_dog_intent, retry_count=retry_count)
    recovered = existing is not None

    if existing is None:
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
        )
        if not initial.ready or initial.status != REDDOG_MAIN_BOOTSTRAP_READY:
            record.update(
                _failure_updates(
                    STATUS_FAILED,
                    (ResidentCycleReason.BOOTSTRAP_REJECTED, *initial.rejection_reasons),
                )
            )
            store.upsert_cycle(record)
            return _result_from_record(record=record, accepted=False)
        if not initial.enqueue_attempted or initial.enqueue_task_count <= 0 or initial.enqueue_rejection_reasons:
            record.update(
                _failure_updates(
                    STATUS_FAILED,
                    (ResidentCycleReason.TASK_ENQUEUE_REJECTED, *initial.enqueue_rejection_reasons),
                )
            )
            store.upsert_cycle(record)
            return _result_from_record(record=record, accepted=False)
        task_ids = store.load_task_ids(str(initial.determination_id or ""))
        if not task_ids:
            record.update(_failure_updates(STATUS_FAILED, (ResidentCycleReason.NO_TASK_IDS,)))
            store.upsert_cycle(record)
            return _result_from_record(record=record, accepted=False)
        record.update(
            {
                "status": STATUS_ENQUEUED,
                "snapshot_id": initial.snapshot_receipt_id,
                "determination_id": initial.determination_id,
                "swarm_id": initial.swarm_id,
                "task_ids": list(task_ids),
                "task_status_counts": dict(store.load_task_status_counts(task_ids)),
                "initial_bootstrap": initial.to_dict(),
                "updated_at": _now_iso(),
            }
        )
        store.upsert_cycle(record)

    task_ids = tuple(str(task_id) for task_id in record.get("task_ids", ()) if str(task_id))
    claims: list[Mapping[str, Any]] = []
    claim_runner = openclaw_claim_runner or claim_reddog_readonly_audit_task_once
    for _ in range(max(0, int(max_claims))):
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
        if claim.get("status") == READONLY_AUDIT_OPENCLAW_CLAIM_IDLE:
            break
        if claim.get("status") != READONLY_AUDIT_OPENCLAW_CLAIM_ACCEPT:
            record.update(
                _failure_updates(
                    STATUS_FAILED,
                    (ResidentCycleReason.OPENCLAW_CLAIM_REJECTED, *claim.get("rejection_reasons", ())),
                )
            )
            record["openclaw_claims"] = [dict(item) for item in claims]
            record["task_status_counts"] = dict(store.load_task_status_counts(task_ids))
            store.upsert_cycle(record)
            return _result_from_record(record=record, accepted=False, recovered_existing_cycle=recovered)

    counts = dict(store.load_task_status_counts(task_ids))
    record["task_status_counts"] = counts
    record["openclaw_claims"] = [dict(item) for item in claims]
    if not task_ids or counts.get("completed", 0) != len(task_ids):
        record.update(_failure_updates(STATUS_TIMED_OUT, (ResidentCycleReason.TIMEOUT,)))
        store.upsert_cycle(record)
        return _result_from_record(record=record, accepted=False, recovered_existing_cycle=recovered)

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
        audit_lanes=audit_lanes,
        collect_readonly_audit_reports=True,
        report_store=report_store or AgentDbReadOnlyAuditReportStore(agent_db_factory=agent_db_factory),
        persist_readonly_audit_decision=True,
        decision_store=decision_store,
        run_backend_architect_determination=True,
        architect_model_runner=architect_model_runner,
        architect_determination_store=architect_determination_store,
    )
    if not final.ready:
        record.update(
            _failure_updates(
                STATUS_FAILED,
                (ResidentCycleReason.FINAL_BOOTSTRAP_REJECTED, *final.rejection_reasons),
            )
        )
        record["final_bootstrap"] = final.to_dict()
        store.upsert_cycle(record)
        return _result_from_record(
            record=record,
            accepted=False,
            final_bootstrap=final,
            recovered_existing_cycle=recovered,
        )
    if not final.backend_architect_determination_id:
        record.update(_failure_updates(STATUS_FAILED, (ResidentCycleReason.ARCHITECT_DETERMINATION_MISSING,)))
        record["final_bootstrap"] = final.to_dict()
        store.upsert_cycle(record)
        return _result_from_record(
            record=record,
            accepted=False,
            final_bootstrap=final,
            recovered_existing_cycle=recovered,
        )

    record.update(
        {
            "status": STATUS_DETERMINED,
            "rejection_reasons": [],
            "final_bootstrap": final.to_dict(),
            "architect_action": final.backend_architect_determination_action,
            "architect_next_slice": final.backend_architect_determination_next_slice,
            "architect_determination_id": final.backend_architect_determination_id,
            "queue_candidate_count": final.backend_architect_determination_queue_candidate_count,
            "updated_at": _now_iso(),
        }
    )
    store.upsert_cycle(record)
    return _result_from_record(record=record, accepted=True, final_bootstrap=final, recovered_existing_cycle=recovered)


def _new_record(intent: Mapping[str, Any], *, retry_count: int) -> dict[str, Any]:
    intent_id = str(intent.get("intent_id") or "").strip()
    return {
        "schema_version": "reddog_resident_architect_cycle.v1",
        "intent_id": intent_id,
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
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "rejection_reasons": [],
        "read_only_authority_only": True,
    }


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
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason).strip())),
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
    "STATUS_CANCELLED",
    "STATUS_DETERMINED",
    "STATUS_ENQUEUED",
    "STATUS_FAILED",
    "STATUS_RUNNING",
    "STATUS_SUBMITTED",
    "STATUS_TIMED_OUT",
    "run_reddog_resident_architect_durable_agentdb_cycle",
]
