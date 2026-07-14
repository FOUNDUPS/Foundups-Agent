"""RedDog read-only audit swarm AgentDB enqueue seam.

Slice: REDDOG_OPENCLAW_READONLY_AUDIT_SWARM_AGENTDB_ENQUEUE_PHASE1

This module turns an accepted read-only audit swarm plan into durable
OpenClaw/AgentDB autonomous-task assignments. It does not execute the audit
tasks, call models, dispatch Hermes/WRE, create worktrees, edit files, run
shell commands, mutate HoloIndex, or enqueue live FoundUp work.

The concrete AgentDB writer is intentionally narrow: it writes only pending
autonomous-task records for already-planned read-only audit assignments. Actual
worker execution/report collection remains a later slice.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Protocol, Sequence

from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_runtime import (
    FORBIDDEN_ACTIONS,
    READONLY_AUDIT_SWARM_PLANNED,
    ReadOnlyAuditAssignment,
    ReadOnlyAuditSwarmPlan,
)


READONLY_AUDIT_SWARM_ENQUEUE_ACCEPT = "READONLY_AUDIT_SWARM_ENQUEUE_ACCEPT"
READONLY_AUDIT_SWARM_ENQUEUE_REJECT = "READONLY_AUDIT_SWARM_ENQUEUE_REJECT"

READONLY_AUDIT_TASK_SKILL = "reddog_readonly_audit"
READONLY_AUDIT_TASK_SOURCE = "reddog_openclaw_readonly_audit_swarm"


class ReadOnlyAuditEnqueueReason:
    PLAN_NOT_ACCEPTED = "REJECT_SWARM_PLAN_NOT_ACCEPTED"
    MISSING_ASSIGNMENTS = "REJECT_MISSING_ASSIGNMENTS"
    ASSIGNMENT_UNSAFE = "REJECT_ASSIGNMENT_UNSAFE"
    WRITER_MISSING = "REJECT_READONLY_AUDIT_WRITER_MISSING"
    WRITER_REJECTED = "REJECT_READONLY_AUDIT_WRITER_REJECTED"
    IDEMPOTENCY_REPLAY = "REJECT_READONLY_AUDIT_ASSIGNMENT_REPLAY"


@dataclass(frozen=True)
class ReadOnlyAuditTaskSpec:
    """Pending AgentDB task derived from one read-only audit assignment."""

    task_id: str
    description: str
    required_skills: tuple[str, ...]
    estimated_complexity: float
    priority_score: float
    context: Mapping[str, Any]
    origin_continuity_id: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["required_skills"] = list(self.required_skills)
        payload["context"] = dict(self.context)
        return payload


@dataclass(frozen=True)
class ReadOnlyAuditSwarmEnqueueReceipt:
    """Receipt for durable publication of read-only audit assignments."""

    enqueue_receipt_id: str
    status: str
    swarm_id: Optional[str]
    snapshot_receipt_id: Optional[str]
    determination_id: Optional[str]
    task_ids: tuple[str, ...]
    assignment_ids: tuple[str, ...]
    rejection_reasons: tuple[str, ...]
    created_at: str
    receipt_digest: str
    no_model_call_performed: bool = True
    no_task_execution_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_worktree_operation_performed: bool = True
    no_live_foundup_enqueue_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReadOnlyAuditSwarmEnqueueResult:
    """Result from publishing read-only audit assignments."""

    accepted: bool
    decision: str
    receipt: ReadOnlyAuditSwarmEnqueueReceipt
    tasks: tuple[ReadOnlyAuditTaskSpec, ...]
    rejection_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "decision": self.decision,
            "receipt": self.receipt.to_dict(),
            "tasks": [task.to_dict() for task in self.tasks],
            "rejection_reasons": list(self.rejection_reasons),
        }


class ReadOnlyAuditTaskWriter(Protocol):
    """Injected writer for durable task publication."""

    def enqueue_readonly_audit_tasks(
        self,
        tasks: Sequence[ReadOnlyAuditTaskSpec],
        receipt: ReadOnlyAuditSwarmEnqueueReceipt,
    ) -> Mapping[str, Any]: ...


class AgentDbReadOnlyAuditTaskWriter:
    """Concrete AgentDB writer for pending read-only audit tasks.

    Construction is side-effect free; AgentDB is imported and opened only when
    enqueueing. The batch is preflighted and inserted inside one DB transaction
    to avoid partial publication when a task id already exists.
    """

    def __init__(self, agent_db_factory: Optional[Any] = None) -> None:
        self._agent_db_factory = agent_db_factory

    def enqueue_readonly_audit_tasks(
        self,
        tasks: Sequence[ReadOnlyAuditTaskSpec],
        receipt: ReadOnlyAuditSwarmEnqueueReceipt,
    ) -> Mapping[str, Any]:
        factory = self._agent_db_factory
        if factory is None:
            from modules.infrastructure.database.src.agent_db import AgentDB

            factory = AgentDB

        db = factory()
        task_ids = tuple(task.task_id for task in tasks)
        try:
            with db.db.get_connection() as conn:
                for task_id in task_ids:
                    existing = conn.execute(
                        "SELECT task_id FROM agents_autonomous_tasks WHERE task_id = ?",
                        (task_id,),
                    ).fetchone()
                    if existing:
                        return {
                            "ok": False,
                            "reason": "task_already_exists",
                            "task_id": task_id,
                            "created_task_ids": [],
                        }

                for task in tasks:
                    conn.execute(
                        """
                        INSERT INTO agents_autonomous_tasks
                        (task_id, description, required_skills, estimated_complexity,
                         priority_score, discovered_by, context, origin_continuity_id, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                        """,
                        (
                            task.task_id,
                            task.description,
                            json.dumps(list(task.required_skills), sort_keys=True),
                            float(task.estimated_complexity),
                            float(task.priority_score),
                            READONLY_AUDIT_TASK_SOURCE,
                            json.dumps(dict(task.context), sort_keys=True),
                            task.origin_continuity_id,
                        ),
                    )
        except Exception as exc:
            return {
                "ok": False,
                "reason": "agentdb_write_failed",
                "error": str(exc)[:200],
                "created_task_ids": [],
            }

        return {"ok": True, "created_task_ids": list(task_ids)}


def enqueue_reddog_readonly_audit_swarm(
    *,
    plan: ReadOnlyAuditSwarmPlan,
    writer: Optional[ReadOnlyAuditTaskWriter],
    seen_assignment_ids: Optional[set[str]] = None,
    now: Optional[datetime] = None,
) -> ReadOnlyAuditSwarmEnqueueResult:
    """Publish an accepted read-only audit swarm plan as pending tasks."""

    checked_at = _iso8601(now)
    reasons = _validate_plan(plan)
    if writer is None:
        reasons.append(ReadOnlyAuditEnqueueReason.WRITER_MISSING)

    assignment_ids = tuple(assignment.assignment_id for assignment in getattr(plan, "assignments", ()))
    if seen_assignment_ids is not None:
        for assignment_id in assignment_ids:
            if assignment_id in seen_assignment_ids:
                reasons.append(ReadOnlyAuditEnqueueReason.IDEMPOTENCY_REPLAY)
                break

    tasks = tuple(_build_task_spec(plan, assignment) for assignment in getattr(plan, "assignments", ()))
    deduped_reasons = _dedupe(reasons)
    if deduped_reasons:
        return _result(
            accepted=False,
            plan=plan,
            tasks=(),
            reasons=deduped_reasons,
            created_at=checked_at,
        )

    assert writer is not None
    provisional = _receipt(
        status=READONLY_AUDIT_SWARM_ENQUEUE_ACCEPT,
        plan=plan,
        tasks=tasks,
        reasons=(),
        created_at=checked_at,
    )
    try:
        writer_result = writer.enqueue_readonly_audit_tasks(tasks, provisional)
    except Exception:
        writer_result = {"ok": False, "reason": "writer_exception"}
    if not isinstance(writer_result, Mapping) or writer_result.get("ok") is not True:
        return _result(
            accepted=False,
            plan=plan,
            tasks=(),
            reasons=[ReadOnlyAuditEnqueueReason.WRITER_REJECTED],
            created_at=checked_at,
        )

    created = tuple(str(value) for value in writer_result.get("created_task_ids", ()))
    expected = tuple(task.task_id for task in tasks)
    if created != expected:
        return _result(
            accepted=False,
            plan=plan,
            tasks=(),
            reasons=[ReadOnlyAuditEnqueueReason.WRITER_REJECTED],
            created_at=checked_at,
        )

    if seen_assignment_ids is not None:
        seen_assignment_ids.update(assignment_ids)

    return _result(
        accepted=True,
        plan=plan,
        tasks=tasks,
        reasons=(),
        created_at=checked_at,
    )


def _validate_plan(plan: ReadOnlyAuditSwarmPlan) -> list[str]:
    reasons: list[str] = []
    if not isinstance(plan, ReadOnlyAuditSwarmPlan) or not plan.accepted:
        return [ReadOnlyAuditEnqueueReason.PLAN_NOT_ACCEPTED]
    if plan.status != READONLY_AUDIT_SWARM_PLANNED or plan.receipt.status != READONLY_AUDIT_SWARM_PLANNED:
        reasons.append(ReadOnlyAuditEnqueueReason.PLAN_NOT_ACCEPTED)
    if not plan.assignments:
        reasons.append(ReadOnlyAuditEnqueueReason.MISSING_ASSIGNMENTS)
    for assignment in plan.assignments:
        if not _assignment_safe(assignment, plan):
            reasons.append(ReadOnlyAuditEnqueueReason.ASSIGNMENT_UNSAFE)
            break
    return reasons


def _assignment_safe(assignment: ReadOnlyAuditAssignment, plan: ReadOnlyAuditSwarmPlan) -> bool:
    if assignment.assignment_id not in set(plan.receipt.assignment_ids):
        return False
    if assignment.snapshot_receipt_id != plan.receipt.snapshot_receipt_id:
        return False
    if assignment.context_view_id != plan.receipt.context_view_id:
        return False
    if assignment.evidence_bundle_id != plan.receipt.evidence_bundle_id:
        return False
    if assignment.determination_id != plan.receipt.determination_id:
        return False
    if assignment.no_worker_spawn_performed is not True:
        return False
    if assignment.no_execution_performed is not True:
        return False
    if assignment.no_repo_mutation_performed is not True:
        return False
    if tuple(assignment.forbidden_actions) != tuple(FORBIDDEN_ACTIONS):
        return False
    return bool(assignment.lane_id and assignment.allowed_read_targets)


def _build_task_spec(plan: ReadOnlyAuditSwarmPlan, assignment: ReadOnlyAuditAssignment) -> ReadOnlyAuditTaskSpec:
    task_id = "reddog-readonly-audit-" + _digest(
        {
            "swarm_id": plan.receipt.swarm_id,
            "assignment_id": assignment.assignment_id,
            "lane_id": assignment.lane_id,
        }
    )[:16]
    context = {
        "source": READONLY_AUDIT_TASK_SOURCE,
        "slice_name": "REDDOG_OPENCLAW_READONLY_AUDIT_SWARM_AGENTDB_ENQUEUE_PHASE1",
        "swarm_receipt": plan.receipt.to_dict(),
        "assignment": assignment.to_dict(),
        "forbidden_actions": list(FORBIDDEN_ACTIONS),
        "report_contract": {
            "repo_mutation_performed": False,
            "execution_performed": False,
            "openclaw_enqueue_performed": False,
            "requires_evidence_refs": True,
        },
    }
    priority = {
        "security_governance_audit": 0.95,
        "runtime_freshness_audit": 0.90,
        "repo_code_audit": 0.85,
        "external_research_audit": 0.80,
        "skill_gap_audit": 0.75,
    }.get(assignment.lane_id, 0.70)
    return ReadOnlyAuditTaskSpec(
        task_id=task_id,
        description=f"RedDog read-only audit lane: {assignment.lane_id}",
        required_skills=(READONLY_AUDIT_TASK_SKILL,),
        estimated_complexity=0.35,
        priority_score=priority,
        context=context,
        origin_continuity_id=assignment.determination_id,
    )


def _result(
    *,
    accepted: bool,
    plan: ReadOnlyAuditSwarmPlan,
    tasks: Sequence[ReadOnlyAuditTaskSpec],
    reasons: Sequence[str],
    created_at: str,
) -> ReadOnlyAuditSwarmEnqueueResult:
    decision = READONLY_AUDIT_SWARM_ENQUEUE_ACCEPT if accepted else READONLY_AUDIT_SWARM_ENQUEUE_REJECT
    receipt = _receipt(
        status=decision,
        plan=plan,
        tasks=tasks,
        reasons=tuple(reasons),
        created_at=created_at,
    )
    return ReadOnlyAuditSwarmEnqueueResult(
        accepted=accepted,
        decision=decision,
        receipt=receipt,
        tasks=tuple(tasks),
        rejection_reasons=tuple(reasons),
    )


def _receipt(
    *,
    status: str,
    plan: ReadOnlyAuditSwarmPlan,
    tasks: Sequence[ReadOnlyAuditTaskSpec],
    reasons: Sequence[str],
    created_at: str,
) -> ReadOnlyAuditSwarmEnqueueReceipt:
    payload = {
        "status": status,
        "swarm_id": getattr(plan.receipt, "swarm_id", None),
        "task_ids": [task.task_id for task in tasks],
        "assignment_ids": [assignment.assignment_id for assignment in getattr(plan, "assignments", ())],
        "rejection_reasons": list(reasons),
        "created_at": created_at,
    }
    receipt_id = "readonly-audit-enqueue-" + _digest(payload)[:16]
    receipt_payload = {
        **payload,
        "enqueue_receipt_id": receipt_id,
        "snapshot_receipt_id": getattr(plan.receipt, "snapshot_receipt_id", None),
        "determination_id": getattr(plan.receipt, "determination_id", None),
    }
    receipt_digest = "sha256:" + _digest(receipt_payload)
    return ReadOnlyAuditSwarmEnqueueReceipt(
        enqueue_receipt_id=receipt_id,
        status=status,
        swarm_id=getattr(plan.receipt, "swarm_id", None),
        snapshot_receipt_id=getattr(plan.receipt, "snapshot_receipt_id", None),
        determination_id=getattr(plan.receipt, "determination_id", None),
        task_ids=tuple(task.task_id for task in tasks),
        assignment_ids=tuple(assignment.assignment_id for assignment in getattr(plan, "assignments", ())),
        rejection_reasons=tuple(reasons),
        created_at=created_at,
        receipt_digest=receipt_digest,
    )


def _dedupe(items: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(str(item) for item in items if str(item).strip()))


def _iso8601(value: Optional[datetime]) -> str:
    current = value or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "AgentDbReadOnlyAuditTaskWriter",
    "READONLY_AUDIT_SWARM_ENQUEUE_ACCEPT",
    "READONLY_AUDIT_SWARM_ENQUEUE_REJECT",
    "READONLY_AUDIT_TASK_SKILL",
    "READONLY_AUDIT_TASK_SOURCE",
    "ReadOnlyAuditEnqueueReason",
    "ReadOnlyAuditSwarmEnqueueReceipt",
    "ReadOnlyAuditSwarmEnqueueResult",
    "ReadOnlyAuditTaskSpec",
    "ReadOnlyAuditTaskWriter",
    "enqueue_reddog_readonly_audit_swarm",
]
