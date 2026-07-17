"""RedDog signed-authority worker dispatch dry-run planner.

Slice: REDDOG_SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_PHASE1

This module consumes an accepted queue authority verification result, the
signed authority runtime payload, and the authoritative WSP15 allocation
receipt. It emits deterministic worker-dispatch intents only. It does not
register workers, spawn workers, enqueue OpenClaw, dispatch Hermes, run shell
commands, mutate the repository, publish PRs, settle rewards, or re-index
HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    AUTHORITY_ISSUED,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_runtime_invoke import (
    QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_verification_invoke import (
    QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
)


SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT = (
    "SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT"
)
SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_REJECT = (
    "SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_REJECT"
)


class SignedAuthorityWorkerDispatchDryRunReason:
    EXPLICIT_REQUEST_MISSING = "REJECT_EXPLICIT_SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_MISSING"
    AUTHORITY_VERIFICATION_NOT_ACCEPTED = "REJECT_AUTHORITY_VERIFICATION_NOT_ACCEPTED"
    AUTHORITY_RUNTIME_NOT_ACCEPTED = "REJECT_AUTHORITY_RUNTIME_NOT_ACCEPTED"
    AUTHORITY_PAYLOAD_MISSING = "REJECT_AUTHORITY_PAYLOAD_MISSING"
    WSP15_ALLOCATION_MISSING = "REJECT_WSP15_ALLOCATION_MISSING"
    WSP15_ALLOCATION_MALFORMED = "REJECT_WSP15_ALLOCATION_MALFORMED"
    WSP15_RECEIPT_ID_MISMATCH = "REJECT_WSP15_RECEIPT_ID_MISMATCH"
    WSP15_DIGEST_MISMATCH = "REJECT_WSP15_DIGEST_MISMATCH"
    WSP15_PRIORITY_MISMATCH = "REJECT_WSP15_PRIORITY_MISMATCH"
    WSP15_MPS_TOTAL_MISMATCH = "REJECT_WSP15_MPS_TOTAL_MISMATCH"
    WSP15_REASONING_TIER_MISMATCH = "REJECT_WSP15_REASONING_TIER_MISMATCH"
    MODEL_RUNTIME_BINDING_MISMATCH = "REJECT_MODEL_RUNTIME_BINDING_MISMATCH"
    QUEUE_MUTATION_NOT_ALLOWED = "REJECT_QUEUE_MUTATION_NOT_ALLOWED"
    HERMES_EXECUTION_NOT_ALLOWED = "REJECT_HERMES_EXECUTION_NOT_ALLOWED"
    WORKER_PLAN_EMPTY = "REJECT_WORKER_PLAN_EMPTY"


@dataclass(frozen=True)
class WorkerDispatchIntent:
    """One planned worker assignment intent. This is not a worker invocation."""

    intent_id: str
    role: str
    worker_runtime: str
    capability: str
    work_order_id: str
    foundup_id: str
    requested_operation: str
    wsp15_allocation_receipt_id: str
    wsp15_allocation_digest: str
    model_runtime_binding_receipt_id: str = ""
    model_runtime_binding_digest: str = ""
    dry_run_only: bool = True
    no_worker_spawn_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SignedAuthorityWorkerDispatchDryRunReceipt:
    receipt_id: str
    work_order_id: str
    foundup_id: str
    requested_operation: str
    wsp15_allocation_receipt_id: str
    wsp15_allocation_digest: str
    wsp15_priority: str
    wsp15_mps_total: int
    wsp15_reasoning_tier: str
    model_runtime_binding_receipt_id: str
    model_runtime_binding_digest: str
    dispatch_intent_count: int
    dispatch_intents: Tuple[WorkerDispatchIntent, ...]
    no_worker_spawn_performed: bool = True
    no_queue_mutation_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["dispatch_intents"] = [intent.to_dict() for intent in self.dispatch_intents]
        return payload


@dataclass(frozen=True)
class SignedAuthorityWorkerDispatchDryRunResult:
    accepted: bool
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    receipt: SignedAuthorityWorkerDispatchDryRunReceipt | None = None
    explicit_signed_authority_worker_dispatch_dryrun_requested: bool = False
    no_worker_spawn_performed: bool = True
    no_queue_mutation_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict() if self.receipt else None
        return payload


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return value
    return {}


def _digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _reject(
    reasons: Sequence[str],
    *,
    explicit_requested: bool,
) -> SignedAuthorityWorkerDispatchDryRunResult:
    return SignedAuthorityWorkerDispatchDryRunResult(
        accepted=False,
        decision=SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_REJECT,
        rejection_reasons=list(dict.fromkeys(reasons)),
        receipt=None,
        explicit_signed_authority_worker_dispatch_dryrun_requested=explicit_requested,
    )


def _valid_priority_for_mps(priority: str, mps_total: int) -> bool:
    if mps_total >= 18:
        return priority == "P0"
    if mps_total >= 14:
        return priority == "P1"
    if mps_total >= 10:
        return priority == "P2"
    if mps_total >= 7:
        return priority == "P3"
    return priority == "P4"


def _validate_allocation(allocation: Mapping[str, Any]) -> List[str]:
    reasons: List[str] = []
    if not allocation:
        return [SignedAuthorityWorkerDispatchDryRunReason.WSP15_ALLOCATION_MISSING]
    receipt_id = str(allocation.get("receipt_id") or "")
    priority = str(allocation.get("priority") or "")
    tier = str(allocation.get("reasoning_tier") or "")
    total = allocation.get("mps_total")
    worker_plan = _mapping(allocation.get("worker_plan"))
    if (
        not receipt_id.startswith("sha256:")
        or priority not in {"P0", "P1", "P2", "P3", "P4"}
        or tier not in {"REGULAR", "HIGH", "ULTRA"}
        or type(total) is not int
        or not _valid_priority_for_mps(priority, total)
        or not worker_plan
    ):
        reasons.append(SignedAuthorityWorkerDispatchDryRunReason.WSP15_ALLOCATION_MALFORMED)
    if worker_plan and worker_plan.get("queue_mutation_allowed") is not False:
        reasons.append(SignedAuthorityWorkerDispatchDryRunReason.QUEUE_MUTATION_NOT_ALLOWED)
    if worker_plan and worker_plan.get("hermes_execution_allowed") is not False:
        reasons.append(SignedAuthorityWorkerDispatchDryRunReason.HERMES_EXECUTION_NOT_ALLOWED)
    return reasons


def _build_intents(
    *,
    work_authority: Mapping[str, Any],
    allocation: Mapping[str, Any],
) -> Tuple[WorkerDispatchIntent, ...]:
    worker_plan = _mapping(allocation.get("worker_plan"))
    intents: List[WorkerDispatchIntent] = []
    base = {
        "work_order_id": str(work_authority["work_order_id"]),
        "foundup_id": str(work_authority["foundup_id"]),
        "requested_operation": str(work_authority["requested_operation"]),
        "wsp15_allocation_receipt_id": str(allocation["receipt_id"]),
        "wsp15_allocation_digest": _digest(allocation),
        "model_runtime_binding_receipt_id": str(work_authority.get("model_runtime_binding_receipt_id") or ""),
        "model_runtime_binding_digest": str(work_authority.get("model_runtime_binding_digest") or ""),
    }

    roles: List[tuple[str, str, str]] = []
    coding_count = int(worker_plan.get("coding_worker_count") or 0)
    active_bounded_code_workers = 1 if coding_count > 0 else 0
    for index in range(active_bounded_code_workers):
        roles.append((f"coding_worker_{index + 1}", "0102", "bounded_code_change"))
    if worker_plan.get("openclaw_candidate") is True and coding_count <= 0:
        roles.append(("openclaw_candidate", "openclaw", "candidate_queue_review"))
    if coding_count > 0:
        roles.append(("queue_stage_worker", "openclaw", "queue_stage_progress"))

    for role, runtime, capability in roles:
        seed = {
            **base,
            "role": role,
            "worker_runtime": runtime,
            "capability": capability,
        }
        intents.append(
            WorkerDispatchIntent(
                intent_id="worker_dispatch_intent_" + _digest(seed).removeprefix("sha256:")[:16],
                role=role,
                worker_runtime=runtime,
                capability=capability,
                **base,
            )
        )
    return tuple(intents)


def plan_reddog_signed_authority_worker_dispatch_dry_run(
    *,
    explicit_signed_authority_worker_dispatch_dryrun_requested: bool,
    queue_authority_verification_result: Mapping[str, Any],
    queue_authority_runtime_result: Mapping[str, Any],
    wsp15_allocation_receipt: Mapping[str, Any],
) -> SignedAuthorityWorkerDispatchDryRunResult:
    """Plan worker dispatch from accepted signed authority without dispatching workers."""

    if explicit_signed_authority_worker_dispatch_dryrun_requested is not True:
        return _reject(
            [SignedAuthorityWorkerDispatchDryRunReason.EXPLICIT_REQUEST_MISSING],
            explicit_requested=False,
        )

    verification = _mapping(queue_authority_verification_result)
    verification_result = _mapping(verification.get("verification_result"))
    if (
        verification.get("decision") != QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT
        or verification_result.get("accepted") is not True
    ):
        return _reject(
            [SignedAuthorityWorkerDispatchDryRunReason.AUTHORITY_VERIFICATION_NOT_ACCEPTED],
            explicit_requested=True,
        )

    runtime = _mapping(queue_authority_runtime_result)
    authority = _mapping(runtime.get("authority_result"))
    receipt = _mapping(authority.get("receipt"))
    if (
        runtime.get("decision") != QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT
        or authority.get("accepted") is not True
        or receipt.get("status") != AUTHORITY_ISSUED
    ):
        return _reject(
            [SignedAuthorityWorkerDispatchDryRunReason.AUTHORITY_RUNTIME_NOT_ACCEPTED],
            explicit_requested=True,
        )

    work_authority = _mapping(authority.get("work_authority"))
    if not work_authority:
        return _reject(
            [SignedAuthorityWorkerDispatchDryRunReason.AUTHORITY_PAYLOAD_MISSING],
            explicit_requested=True,
        )

    allocation = _mapping(wsp15_allocation_receipt)
    reasons = _validate_allocation(allocation)
    if reasons:
        return _reject(reasons, explicit_requested=True)

    allocation_receipt_id = str(allocation["receipt_id"])
    allocation_digest = _digest(allocation)
    if str(work_authority.get("wsp15_allocation_receipt_id") or "") != allocation_receipt_id:
        reasons.append(SignedAuthorityWorkerDispatchDryRunReason.WSP15_RECEIPT_ID_MISMATCH)
    if str(work_authority.get("wsp15_allocation_digest") or "") != allocation_digest:
        reasons.append(SignedAuthorityWorkerDispatchDryRunReason.WSP15_DIGEST_MISMATCH)
    if str(work_authority.get("wsp15_priority") or "") != str(allocation["priority"]):
        reasons.append(SignedAuthorityWorkerDispatchDryRunReason.WSP15_PRIORITY_MISMATCH)
    if work_authority.get("wsp15_mps_total") != allocation["mps_total"]:
        reasons.append(SignedAuthorityWorkerDispatchDryRunReason.WSP15_MPS_TOTAL_MISMATCH)
    if str(work_authority.get("wsp15_reasoning_tier") or "") != str(allocation["reasoning_tier"]):
        reasons.append(SignedAuthorityWorkerDispatchDryRunReason.WSP15_REASONING_TIER_MISMATCH)
    runtime_binding_id = str(work_authority.get("model_runtime_binding_receipt_id") or "")
    runtime_binding_digest = str(work_authority.get("model_runtime_binding_digest") or "")
    if bool(runtime_binding_id) != bool(runtime_binding_digest):
        reasons.append(SignedAuthorityWorkerDispatchDryRunReason.MODEL_RUNTIME_BINDING_MISMATCH)
    if runtime_binding_id and (
        not runtime_binding_id.startswith("reddog_model_runtime_binding:")
        or not runtime_binding_digest.startswith("sha256:")
    ):
        reasons.append(SignedAuthorityWorkerDispatchDryRunReason.MODEL_RUNTIME_BINDING_MISMATCH)
    if reasons:
        return _reject(reasons, explicit_requested=True)

    intents = _build_intents(work_authority=work_authority, allocation=allocation)
    if not intents:
        return _reject(
            [SignedAuthorityWorkerDispatchDryRunReason.WORKER_PLAN_EMPTY],
            explicit_requested=True,
        )

    receipt_seed = {
        "work_order_id": work_authority["work_order_id"],
        "wsp15_allocation_receipt_id": allocation_receipt_id,
        "wsp15_allocation_digest": allocation_digest,
        "model_runtime_binding_receipt_id": runtime_binding_id,
        "model_runtime_binding_digest": runtime_binding_digest,
        "dispatch_intent_ids": [intent.intent_id for intent in intents],
    }
    receipt = SignedAuthorityWorkerDispatchDryRunReceipt(
        receipt_id="signed_authority_worker_dispatch_" + _digest(receipt_seed).removeprefix("sha256:")[:16],
        work_order_id=str(work_authority["work_order_id"]),
        foundup_id=str(work_authority["foundup_id"]),
        requested_operation=str(work_authority["requested_operation"]),
        wsp15_allocation_receipt_id=allocation_receipt_id,
        wsp15_allocation_digest=allocation_digest,
        wsp15_priority=str(allocation["priority"]),
        wsp15_mps_total=int(allocation["mps_total"]),
        wsp15_reasoning_tier=str(allocation["reasoning_tier"]),
        model_runtime_binding_receipt_id=runtime_binding_id,
        model_runtime_binding_digest=runtime_binding_digest,
        dispatch_intent_count=len(intents),
        dispatch_intents=intents,
    )
    return SignedAuthorityWorkerDispatchDryRunResult(
        accepted=True,
        decision=SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT,
        rejection_reasons=[],
        receipt=receipt,
        explicit_signed_authority_worker_dispatch_dryrun_requested=True,
    )


__all__ = [
    "SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT",
    "SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_REJECT",
    "SignedAuthorityWorkerDispatchDryRunReason",
    "SignedAuthorityWorkerDispatchDryRunReceipt",
    "SignedAuthorityWorkerDispatchDryRunResult",
    "WorkerDispatchIntent",
    "plan_reddog_signed_authority_worker_dispatch_dry_run",
]
