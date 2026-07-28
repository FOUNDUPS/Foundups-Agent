"""Bounded public types for signed worker-dispatch publication."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Protocol, Sequence


SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT = (
    "SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT"
)
SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_REJECT = (
    "SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_REJECT"
)


class WorkerDispatchRuntimeReason:
    DRYRUN_NOT_ACCEPTED = "REJECT_WORKER_DISPATCH_DRYRUN_NOT_ACCEPTED"
    RECEIPT_MISSING = "REJECT_WORKER_DISPATCH_DRYRUN_RECEIPT_MISSING"
    INTENTS_MISSING = "REJECT_WORKER_DISPATCH_INTENTS_MISSING"
    INTENT_UNSAFE = "REJECT_WORKER_DISPATCH_INTENT_UNSAFE"
    DISPATCH_SCHEMA_MISMATCH = "REJECT_WORKER_DISPATCH_SCHEMA_MISMATCH"
    QUEUE_ITEM_MISSING = "REJECT_WORKER_DISPATCH_QUEUE_ITEM_MISSING"
    WSP15_BINDING_MISMATCH = "REJECT_WORKER_DISPATCH_WSP15_BINDING_MISMATCH"
    MODEL_RUNTIME_BINDING_MISMATCH = (
        "REJECT_WORKER_DISPATCH_MODEL_RUNTIME_BINDING_MISMATCH"
    )
    WORKER_PLAN_BINDING_MISMATCH = (
        "REJECT_WORKER_DISPATCH_WORKER_PLAN_BINDING_MISMATCH"
    )
    ARCHITECT_FIX_PUBLICATION_BINDING_MISMATCH = (
        "REJECT_WORKER_DISPATCH_ARCHITECT_FIX_PUBLICATION_BINDING_MISMATCH"
    )
    AUTHORITY_VERIFICATION_BINDING_MISMATCH = (
        "REJECT_WORKER_DISPATCH_AUTHORITY_VERIFICATION_BINDING_MISMATCH"
    )
    WORK_ORDER_BINDING_MISMATCH = "REJECT_WORKER_DISPATCH_WORK_ORDER_BINDING_MISMATCH"
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
    model_runtime_binding_receipt_id: str
    model_runtime_binding_digest: str
    architect_fix_publication_receipt_id: str
    architect_fix_publication_binding_digest: str
    verified_work_authority_digest: str
    authority_verification_receipt_id: str
    authority_verification_receipt_digest: str
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
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict() if self.receipt else None
        payload["tasks"] = [task.to_dict() for task in self.tasks]
        payload["rejection_reasons"] = list(self.rejection_reasons)
        return payload


class SignedWorkerDispatchTaskWriter(Protocol):
    """Injected writer for durable signed worker-dispatch task publication."""

    def enqueue_signed_worker_dispatch_tasks(
        self,
        tasks: Sequence[SignedWorkerDispatchTaskSpec],
        receipt: SignedWorkerDispatchRuntimeReceipt,
    ) -> Mapping[str, Any]: ...


def reject_runtime(reasons: Sequence[str]) -> SignedWorkerDispatchRuntimeResult:
    return SignedWorkerDispatchRuntimeResult(
        accepted=False,
        decision=SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_REJECT,
        receipt=None,
        tasks=(),
        rejection_reasons=dedupe(reasons),
    )


def mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def sequence(value: Any) -> tuple[Any, ...]:
    return tuple(value) if isinstance(value, (list, tuple)) else ()


def dedupe(items: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(item) for item in items if str(item).strip()))


def canonical_digest(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def iso8601(value: Optional[datetime]) -> str:
    current = value or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).replace(microsecond=0).isoformat()
