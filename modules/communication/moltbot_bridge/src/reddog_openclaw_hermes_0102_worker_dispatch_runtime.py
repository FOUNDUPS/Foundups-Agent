"""Publish signed RedDog worker-dispatch intents to AgentDB.

Slice: REDDOG_OPENCLAW_HERMES_0102_WORKER_DISPATCH_RUNTIME_PHASE1

This module is the first runtime publication layer after signed worker-dispatch
planning. It turns accepted signed-authority worker intents into pending
AgentDB tasks for OpenClaw/Hermes/0102 claim surfaces.

It does not start a worker process, execute Hermes, create a worktree, run shell
commands, mutate repository files, publish PRs, admit PatternMemory, settle
rewards, or re-index HoloIndex. The only side effect performed by the concrete
writer is insertion of pending autonomous-task rows.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Protocol, Sequence

from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT,
)


SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT = (
    "SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT"
)
SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_REJECT = (
    "SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_REJECT"
)

SIGNED_WORKER_DISPATCH_TASK_SOURCE = "reddog_signed_worker_dispatch_runtime"
SIGNED_WORKER_DISPATCH_TASK_SKILL = "reddog_signed_worker_dispatch"
WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION = "reddog_worker_dispatch_runtime.v1"

_ALLOWED_WORKER_RUNTIMES = frozenset({"0102", "openclaw", "hermes"})
_PRIORITY_SCORE = {
    "P0": 0.97,
    "P1": 0.90,
    "P2": 0.82,
    "P3": 0.70,
    "P4": 0.55,
}
_COMPLEXITY_SCORE = {
    "P0": 0.85,
    "P1": 0.75,
    "P2": 0.62,
    "P3": 0.48,
    "P4": 0.35,
}


class WorkerDispatchRuntimeReason:
    DRYRUN_NOT_ACCEPTED = "REJECT_WORKER_DISPATCH_DRYRUN_NOT_ACCEPTED"
    RECEIPT_MISSING = "REJECT_WORKER_DISPATCH_DRYRUN_RECEIPT_MISSING"
    INTENTS_MISSING = "REJECT_WORKER_DISPATCH_INTENTS_MISSING"
    INTENT_UNSAFE = "REJECT_WORKER_DISPATCH_INTENT_UNSAFE"
    QUEUE_ITEM_MISSING = "REJECT_WORKER_DISPATCH_QUEUE_ITEM_MISSING"
    WSP15_BINDING_MISMATCH = "REJECT_WORKER_DISPATCH_WSP15_BINDING_MISMATCH"
    WRITER_MISSING = "REJECT_WORKER_DISPATCH_WRITER_MISSING"
    WRITER_REJECTED = "REJECT_WORKER_DISPATCH_WRITER_REJECTED"
    IDEMPOTENCY_REPLAY = "REJECT_WORKER_DISPATCH_IDEMPOTENCY_REPLAY"


@dataclass(frozen=True)
class SignedWorkerDispatchTaskSpec:
    """Pending AgentDB task derived from one signed worker-dispatch intent."""

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
class SignedWorkerDispatchRuntimeReceipt:
    """Receipt for publishing signed worker intents as pending tasks."""

    schema_version: str
    receipt_id: str
    status: str
    source_dispatch_receipt_id: str
    queue_item_id: str
    work_order_id: str
    foundup_id: str
    requested_operation: str
    wsp15_allocation_receipt_id: str
    wsp15_allocation_digest: str
    task_ids: tuple[str, ...]
    intent_ids: tuple[str, ...]
    worker_runtimes: tuple[str, ...]
    created_at: str
    receipt_digest: str
    agentdb_tasks_enqueued: bool
    no_worker_process_started: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_hermes_execution_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SignedWorkerDispatchRuntimeResult:
    """Result from the signed worker-dispatch runtime publisher."""

    accepted: bool
    decision: str
    receipt: Optional[SignedWorkerDispatchRuntimeReceipt]
    tasks: tuple[SignedWorkerDispatchTaskSpec, ...]
    rejection_reasons: tuple[str, ...]
    no_worker_process_started: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_hermes_execution_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "decision": self.decision,
            "receipt": self.receipt.to_dict() if self.receipt else None,
            "tasks": [task.to_dict() for task in self.tasks],
            "rejection_reasons": list(self.rejection_reasons),
            "no_worker_process_started": self.no_worker_process_started,
            "no_worktree_created": self.no_worktree_created,
            "no_shell_command_executed": self.no_shell_command_executed,
            "no_hermes_execution_performed": self.no_hermes_execution_performed,
            "no_repo_mutation_performed": self.no_repo_mutation_performed,
            "no_holoindex_reindex_performed": self.no_holoindex_reindex_performed,
            "no_pr_created": self.no_pr_created,
            "no_pattern_memory_write_performed": self.no_pattern_memory_write_performed,
            "no_reward_settlement_performed": self.no_reward_settlement_performed,
        }


class SignedWorkerDispatchTaskWriter(Protocol):
    """Injected writer for durable signed worker-dispatch task publication."""

    def enqueue_signed_worker_dispatch_tasks(
        self,
        tasks: Sequence[SignedWorkerDispatchTaskSpec],
        receipt: SignedWorkerDispatchRuntimeReceipt,
    ) -> Mapping[str, Any]: ...


class AgentDbSignedWorkerDispatchTaskWriter:
    """Concrete AgentDB writer for pending signed worker-dispatch tasks."""

    def __init__(self, agent_db_factory: Optional[Any] = None) -> None:
        self._agent_db_factory = agent_db_factory

    def enqueue_signed_worker_dispatch_tasks(
        self,
        tasks: Sequence[SignedWorkerDispatchTaskSpec],
        receipt: SignedWorkerDispatchRuntimeReceipt,
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
                            SIGNED_WORKER_DISPATCH_TASK_SOURCE,
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

        return {
            "ok": True,
            "created_task_ids": list(task_ids),
            "source_dispatch_receipt_id": receipt.source_dispatch_receipt_id,
        }


def publish_reddog_signed_worker_dispatch_runtime(
    *,
    worker_dispatch_dryrun_result: Mapping[str, Any],
    work_state_snapshot: Mapping[str, Any],
    queue_item_id: str,
    writer: Optional[SignedWorkerDispatchTaskWriter],
    seen_intent_ids: Optional[set[str]] = None,
    now: Optional[datetime] = None,
) -> SignedWorkerDispatchRuntimeResult:
    """Publish accepted signed worker intents as pending AgentDB tasks."""

    created_at = _iso8601(now)
    reasons: list[str] = []
    dryrun = _mapping(worker_dispatch_dryrun_result)
    receipt = _mapping(dryrun.get("receipt"))
    if dryrun.get("accepted") is not True or dryrun.get("decision") != SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT:
        reasons.append(WorkerDispatchRuntimeReason.DRYRUN_NOT_ACCEPTED)
    if not receipt:
        reasons.append(WorkerDispatchRuntimeReason.RECEIPT_MISSING)
    intents = tuple(_mapping(intent) for intent in _list(receipt.get("dispatch_intents")))
    if not intents:
        reasons.append(WorkerDispatchRuntimeReason.INTENTS_MISSING)

    queue_item = _queue_item(work_state_snapshot, queue_item_id)
    if not queue_item:
        reasons.append(WorkerDispatchRuntimeReason.QUEUE_ITEM_MISSING)
    if writer is None:
        reasons.append(WorkerDispatchRuntimeReason.WRITER_MISSING)
    if not _wsp15_matches_queue_item(receipt, queue_item):
        reasons.append(WorkerDispatchRuntimeReason.WSP15_BINDING_MISMATCH)

    if seen_intent_ids is not None:
        for intent in intents:
            intent_id = str(intent.get("intent_id") or "")
            if intent_id in seen_intent_ids:
                reasons.append(WorkerDispatchRuntimeReason.IDEMPOTENCY_REPLAY)
                break

    for intent in intents:
        if not _intent_safe(intent, receipt):
            reasons.append(WorkerDispatchRuntimeReason.INTENT_UNSAFE)
            break

    deduped_reasons = _dedupe(reasons)
    if deduped_reasons:
        return _reject(deduped_reasons)

    tasks = tuple(_build_task(queue_item=queue_item, dryrun_receipt=receipt, intent=intent) for intent in intents)
    runtime_receipt = _receipt(
        accepted=True,
        receipt=receipt,
        queue_item=queue_item,
        tasks=tasks,
        reasons=(),
        created_at=created_at,
    )
    assert writer is not None
    try:
        writer_result = writer.enqueue_signed_worker_dispatch_tasks(tasks, runtime_receipt)
    except Exception:
        writer_result = {"ok": False, "reason": "writer_exception", "created_task_ids": []}
    if not isinstance(writer_result, Mapping) or writer_result.get("ok") is not True:
        return _reject([WorkerDispatchRuntimeReason.WRITER_REJECTED])
    if tuple(str(value) for value in writer_result.get("created_task_ids", ())) != tuple(task.task_id for task in tasks):
        return _reject([WorkerDispatchRuntimeReason.WRITER_REJECTED])

    if seen_intent_ids is not None:
        seen_intent_ids.update(str(intent.get("intent_id") or "") for intent in intents)

    return SignedWorkerDispatchRuntimeResult(
        accepted=True,
        decision=SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT,
        receipt=runtime_receipt,
        tasks=tasks,
        rejection_reasons=(),
    )


def _reject(reasons: Sequence[str]) -> SignedWorkerDispatchRuntimeResult:
    return SignedWorkerDispatchRuntimeResult(
        accepted=False,
        decision=SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_REJECT,
        receipt=None,
        tasks=(),
        rejection_reasons=tuple(_dedupe(reasons)),
    )


def _receipt(
    *,
    accepted: bool,
    receipt: Mapping[str, Any],
    queue_item: Mapping[str, Any],
    tasks: Sequence[SignedWorkerDispatchTaskSpec],
    reasons: Sequence[str],
    created_at: str,
) -> SignedWorkerDispatchRuntimeReceipt:
    status = (
        SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT
        if accepted
        else SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_REJECT
    )
    intent_ids = tuple(str(intent.get("intent_id") or "") for intent in _list(receipt.get("dispatch_intents")))
    payload = {
        "schema_version": WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION,
        "status": status,
        "source_dispatch_receipt_id": str(receipt.get("receipt_id") or ""),
        "queue_item_id": str(queue_item.get("queue_item_id") or ""),
        "task_ids": [task.task_id for task in tasks],
        "intent_ids": list(intent_ids),
        "rejection_reasons": list(reasons),
        "created_at": created_at,
    }
    receipt_id = "signed_worker_dispatch_runtime_" + _digest(payload).removeprefix("sha256:")[:16]
    digest_payload = {**payload, "receipt_id": receipt_id}
    return SignedWorkerDispatchRuntimeReceipt(
        schema_version=WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION,
        receipt_id=receipt_id,
        status=status,
        source_dispatch_receipt_id=str(receipt.get("receipt_id") or ""),
        queue_item_id=str(queue_item.get("queue_item_id") or ""),
        work_order_id=str(receipt.get("work_order_id") or ""),
        foundup_id=str(receipt.get("foundup_id") or ""),
        requested_operation=str(receipt.get("requested_operation") or ""),
        wsp15_allocation_receipt_id=str(receipt.get("wsp15_allocation_receipt_id") or ""),
        wsp15_allocation_digest=str(receipt.get("wsp15_allocation_digest") or ""),
        task_ids=tuple(task.task_id for task in tasks),
        intent_ids=intent_ids,
        worker_runtimes=tuple(sorted({str(_mapping(intent).get("worker_runtime") or "") for intent in _list(receipt.get("dispatch_intents"))})),
        created_at=created_at,
        receipt_digest=_digest(digest_payload),
        agentdb_tasks_enqueued=accepted,
    )


def _build_task(
    *,
    queue_item: Mapping[str, Any],
    dryrun_receipt: Mapping[str, Any],
    intent: Mapping[str, Any],
) -> SignedWorkerDispatchTaskSpec:
    runtime = str(intent["worker_runtime"])
    capability = str(intent["capability"])
    role = str(intent["role"])
    task_seed = {
        "source_dispatch_receipt_id": dryrun_receipt["receipt_id"],
        "queue_item_id": queue_item["queue_item_id"],
        "intent_id": intent["intent_id"],
    }
    priority = str(dryrun_receipt.get("wsp15_priority") or "P2")
    context = {
        "source": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        "schema_version": WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION,
        "slice_name": "REDDOG_OPENCLAW_HERMES_0102_WORKER_DISPATCH_RUNTIME_PHASE1",
        "queue_item_id": str(queue_item["queue_item_id"]),
        "selected_slice": str(queue_item.get("slice_id") or ""),
        "worker_runtime": runtime,
        "worker_role": role,
        "capability": capability,
        "signed_authority_worker_dispatch_receipt": dict(dryrun_receipt),
        "worker_dispatch_intent": dict(intent),
        "wsp15_allocation_receipt": dict(_mapping(queue_item.get("wsp15_allocation_receipt"))),
        "execution_allowed_by_dispatch_runtime": False,
        "requires_downstream_stages": [
            "work_order_invocation",
            "executor_plan",
            "execution_valve",
            "worktree_create",
            "bounded_worker_pilot",
            "slice_verifier",
        ],
        "report_contract": {
            "worker_process_started": False,
            "repo_mutation_performed": False,
            "hermes_execution_performed": False,
            "requires_signed_authority": True,
        },
    }
    return SignedWorkerDispatchTaskSpec(
        task_id="reddog-worker-dispatch-" + _digest(task_seed).removeprefix("sha256:")[:16],
        description=f"RedDog signed worker dispatch: {role} ({runtime}/{capability})",
        required_skills=(
            SIGNED_WORKER_DISPATCH_TASK_SKILL,
            f"runtime:{runtime}",
            f"capability:{capability}",
        ),
        estimated_complexity=_COMPLEXITY_SCORE.get(priority, 0.62),
        priority_score=_PRIORITY_SCORE.get(priority, 0.82),
        context=context,
        origin_continuity_id=str(dryrun_receipt["work_order_id"]),
    )


def _intent_safe(intent: Mapping[str, Any], receipt: Mapping[str, Any]) -> bool:
    if not intent:
        return False
    valid_intent_ids = {str(_mapping(value).get("intent_id") or "") for value in _list(receipt.get("dispatch_intents"))}
    if str(intent.get("intent_id") or "") not in valid_intent_ids:
        return False
    runtime = str(intent.get("worker_runtime") or "")
    if runtime not in _ALLOWED_WORKER_RUNTIMES:
        return False
    if not str(intent.get("role") or "") or not str(intent.get("capability") or ""):
        return False
    if intent.get("dry_run_only") is not True:
        return False
    if intent.get("no_worker_spawn_performed") is not True:
        return False
    if intent.get("no_openclaw_enqueue_performed") is not True:
        return False
    if intent.get("no_hermes_dispatch_performed") is not True:
        return False
    for key in (
        "work_order_id",
        "foundup_id",
        "requested_operation",
        "wsp15_allocation_receipt_id",
        "wsp15_allocation_digest",
    ):
        if str(intent.get(key) or "") != str(receipt.get(key) or ""):
            return False
    return True


def _wsp15_matches_queue_item(receipt: Mapping[str, Any], queue_item: Mapping[str, Any]) -> bool:
    if not receipt or not queue_item:
        return False
    allocation = _mapping(queue_item.get("wsp15_allocation_receipt"))
    if not allocation:
        return False
    return (
        str(receipt.get("wsp15_allocation_receipt_id") or "") == str(allocation.get("receipt_id") or "")
        and str(receipt.get("wsp15_allocation_digest") or "") == _digest(allocation)
    )


def _queue_item(snapshot: Mapping[str, Any], queue_item_id: str) -> Mapping[str, Any]:
    for item in _list(snapshot.get("wre_queue_items")):
        candidate = _mapping(item)
        if str(candidate.get("queue_item_id") or "") == str(queue_item_id or ""):
            return candidate
    return {}


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _list(value: Any) -> tuple[Any, ...]:
    return tuple(value) if isinstance(value, (list, tuple)) else ()


def _dedupe(items: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(item) for item in items if str(item).strip()))


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _iso8601(value: Optional[datetime]) -> str:
    current = value or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).replace(microsecond=0).isoformat()


__all__ = [
    "AgentDbSignedWorkerDispatchTaskWriter",
    "SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT",
    "SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_REJECT",
    "SIGNED_WORKER_DISPATCH_TASK_SKILL",
    "SIGNED_WORKER_DISPATCH_TASK_SOURCE",
    "SignedWorkerDispatchRuntimeReceipt",
    "SignedWorkerDispatchRuntimeResult",
    "SignedWorkerDispatchTaskSpec",
    "SignedWorkerDispatchTaskWriter",
    "WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION",
    "WorkerDispatchRuntimeReason",
    "publish_reddog_signed_worker_dispatch_runtime",
]
