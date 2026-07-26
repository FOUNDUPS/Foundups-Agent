"""RedDog resident queue orchestration planner.

Slice: REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN_PHASE1

This module gives the resident RedDog loop a deterministic view of the next
queue-authorized bridge to run.  It consumes the authoritative work-state
snapshot plus already-emitted chain results, validates ordering, and stops at
the first missing or rejected stage.

It does not invoke authority issuance, verify signatures, open valves, create
worktrees, edit files, run shell commands, publish PRs, admit PatternMemory,
enqueue OpenClaw, dispatch Hermes, settle rewards, or re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_request_dryrun import (
    QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_runtime_invoke import (
    QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_verification_invoke import (
    QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_bounded_worker_pilot_invoke import (
    QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_execution_valve_invoke import (
    QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_executor_plan_dryrun import (
    QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_held_out_regression_gate_invoke import (
    QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_model_feedback_ledger_admission_invoke import (
    QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_pattern_memory_admission_invoke import (
    QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_slice_verifier_invoke import (
    QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_draft_pr_publish_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_outcome_ratchet_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_worktree_create_invoke import (
    QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_consumer_dryrun import (
    WRE_QUEUE_CONSUMER_DRYRUN_READY,
    plan_reddog_wre_queue_consumer_dry_run,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_verified_authority_work_order_invoke import (
    QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
)


RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY = "RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY"
RESIDENT_QUEUE_ORCHESTRATION_PLAN_REJECT = "RESIDENT_QUEUE_ORCHESTRATION_PLAN_REJECT"
RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE = "RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE"

NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN = "RUN_QUEUE_AUTHORITY_REQUEST_DRYRUN"
NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE = "RUN_QUEUE_AUTHORITY_RUNTIME_INVOKE"
NEXT_QUEUE_AUTHORITY_VERIFICATION_INVOKE = "RUN_QUEUE_AUTHORITY_VERIFICATION_INVOKE"
NEXT_QUEUE_WORKER_DISPATCH_DRYRUN = "RUN_QUEUE_SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN"
NEXT_QUEUE_WORKER_DISPATCH_RUNTIME = "RUN_QUEUE_SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME"
NEXT_QUEUE_WORK_ORDER_INVOCATION = "RUN_QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE"
NEXT_QUEUE_EXECUTOR_PLAN_DRYRUN = "RUN_QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN"
NEXT_QUEUE_EXECUTION_VALVE_INVOKE = "RUN_QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE"
NEXT_QUEUE_WORKTREE_CREATE_INVOKE = "RUN_QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE"
NEXT_QUEUE_ASSURANCE_CAPACITY_ADMISSION = (
    "RUN_QUEUE_ASSURANCE_CAPACITY_ADMISSION"
)
NEXT_QUEUE_BOUNDED_WORKER_PILOT_INVOKE = "RUN_QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE"
NEXT_QUEUE_SLICE_VERIFIER_INVOKE = "RUN_QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE"
NEXT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_INVOKE = "RUN_QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE"
NEXT_QUEUE_VERIFIED_OUTCOME_RATCHET_INVOKE = "RUN_QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE"
NEXT_QUEUE_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE = "RUN_QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE"
NEXT_QUEUE_HELD_OUT_REGRESSION_GATE_INVOKE = "RUN_QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE"
NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE = "RUN_QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE"
NEXT_QUEUE_CHAIN_COMPLETE = "STOP_QUEUE_CHAIN_COMPLETE"

FAIL_QUEUE_CONSUMER_NOT_READY = "FAIL_QUEUE_CONSUMER_NOT_READY"
FAIL_STAGE_REJECTED = "FAIL_STAGE_REJECTED"
FAIL_OUT_OF_ORDER_STAGE_RESULT = "FAIL_OUT_OF_ORDER_STAGE_RESULT"
FAIL_CHAIN_RESULTS_NOT_MAPPING = "FAIL_CHAIN_RESULTS_NOT_MAPPING"


@dataclass(frozen=True)
class ResidentQueueStage:
    """One ordered RedDog queue bridge stage."""

    key: str
    status_field: str
    accepted_value: str
    next_action_when_missing: str


@dataclass(frozen=True)
class ResidentQueueOrchestrationPlan:
    """Deterministic next-step plan for one authoritative queue item."""

    accepted: bool
    status: str
    plan_id: str
    selected_queue_item_id: Optional[str]
    selected_slice: Optional[str]
    current_stage: Optional[str]
    next_action: str
    accepted_stages: Tuple[str, ...] = ()
    missing_stage: Optional[str] = None
    rejection_reasons: List[str] = field(default_factory=list)
    queue_consumer_result: Optional[Dict[str, Any]] = None
    no_authority_issued: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_CHAIN: Tuple[ResidentQueueStage, ...] = (
    ResidentQueueStage(
        "authority_request",
        "status",
        QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT,
        NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN,
    ),
    ResidentQueueStage(
        "authority_runtime",
        "decision",
        QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
        NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE,
    ),
    ResidentQueueStage(
        "authority_verification",
        "decision",
        QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
        NEXT_QUEUE_AUTHORITY_VERIFICATION_INVOKE,
    ),
    ResidentQueueStage(
        "worker_dispatch_dryrun",
        "decision",
        SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT,
        NEXT_QUEUE_WORKER_DISPATCH_DRYRUN,
    ),
    ResidentQueueStage(
        "worker_dispatch_runtime",
        "decision",
        SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT,
        NEXT_QUEUE_WORKER_DISPATCH_RUNTIME,
    ),
    ResidentQueueStage(
        "work_order_invocation",
        "decision",
        QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
        NEXT_QUEUE_WORK_ORDER_INVOCATION,
    ),
    ResidentQueueStage(
        "executor_plan",
        "decision",
        QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
        NEXT_QUEUE_EXECUTOR_PLAN_DRYRUN,
    ),
    ResidentQueueStage(
        "execution_valve",
        "decision",
        QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT,
        NEXT_QUEUE_EXECUTION_VALVE_INVOKE,
    ),
    ResidentQueueStage(
        "worktree_create",
        "decision",
        QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
        NEXT_QUEUE_WORKTREE_CREATE_INVOKE,
    ),
    ResidentQueueStage(
        "assurance_capacity_admission",
        "decision",
        "ASSURANCE_CAPACITY_ADMISSION_ACCEPT",
        NEXT_QUEUE_ASSURANCE_CAPACITY_ADMISSION,
    ),
    ResidentQueueStage(
        "bounded_worker_pilot",
        "decision",
        QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT,
        NEXT_QUEUE_BOUNDED_WORKER_PILOT_INVOKE,
    ),
    ResidentQueueStage(
        "slice_verifier",
        "decision",
        QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT,
        NEXT_QUEUE_SLICE_VERIFIER_INVOKE,
    ),
    ResidentQueueStage(
        "verified_draft_pr_publish",
        "decision",
        QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT,
        NEXT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_INVOKE,
    ),
    ResidentQueueStage(
        "verified_outcome_ratchet",
        "decision",
        QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT,
        NEXT_QUEUE_VERIFIED_OUTCOME_RATCHET_INVOKE,
    ),
    ResidentQueueStage(
        "model_feedback_admission",
        "decision",
        QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_ACCEPT,
        NEXT_QUEUE_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE,
    ),
    ResidentQueueStage(
        "held_out_regression_gate",
        "decision",
        QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT,
        NEXT_QUEUE_HELD_OUT_REGRESSION_GATE_INVOKE,
    ),
    ResidentQueueStage(
        "pattern_memory_admission",
        "decision",
        QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT,
        NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE,
    ),
)

_STAGE_KEYS = tuple(stage.key for stage in _CHAIN)


def _canonical_digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _dedupe(values: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value or "").strip()))


def _queue_consumer_result(
    work_state_snapshot: Mapping[str, Any],
    *,
    queue_consumer_result: Optional[Mapping[str, Any]],
    requested_queue_item_id: Optional[str],
    now_iso: Optional[str],
) -> Mapping[str, Any]:
    supplied = _mapping(queue_consumer_result)
    if supplied:
        return supplied
    return plan_reddog_wre_queue_consumer_dry_run(
        work_state_snapshot,
        now_iso=now_iso,
        requested_queue_item_id=requested_queue_item_id,
    ).to_dict()


def _reject(
    *,
    reasons: Sequence[str],
    selected_queue_item_id: Optional[str],
    selected_slice: Optional[str],
    current_stage: Optional[str],
    next_action: str,
    accepted_stages: Sequence[str],
    queue_consumer: Optional[Mapping[str, Any]] = None,
) -> ResidentQueueOrchestrationPlan:
    payload = {
        "status": RESIDENT_QUEUE_ORCHESTRATION_PLAN_REJECT,
        "selected_queue_item_id": selected_queue_item_id,
        "selected_slice": selected_slice,
        "current_stage": current_stage,
        "next_action": next_action,
        "accepted_stages": tuple(accepted_stages),
        "rejection_reasons": tuple(_dedupe(reasons)),
    }
    return ResidentQueueOrchestrationPlan(
        accepted=False,
        status=RESIDENT_QUEUE_ORCHESTRATION_PLAN_REJECT,
        plan_id=_canonical_digest(payload),
        selected_queue_item_id=selected_queue_item_id,
        selected_slice=selected_slice,
        current_stage=current_stage,
        next_action=next_action,
        accepted_stages=tuple(accepted_stages),
        rejection_reasons=_dedupe(reasons),
        queue_consumer_result=dict(queue_consumer) if queue_consumer else None,
    )


def _ready(
    *,
    selected_queue_item_id: Optional[str],
    selected_slice: Optional[str],
    current_stage: Optional[str],
    next_action: str,
    accepted_stages: Sequence[str],
    missing_stage: Optional[str],
    queue_consumer: Mapping[str, Any],
) -> ResidentQueueOrchestrationPlan:
    status = (
        RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE
        if next_action == NEXT_QUEUE_CHAIN_COMPLETE
        else RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY
    )
    payload = {
        "status": status,
        "selected_queue_item_id": selected_queue_item_id,
        "selected_slice": selected_slice,
        "current_stage": current_stage,
        "next_action": next_action,
        "accepted_stages": tuple(accepted_stages),
        "missing_stage": missing_stage,
    }
    return ResidentQueueOrchestrationPlan(
        accepted=True,
        status=status,
        plan_id=_canonical_digest(payload),
        selected_queue_item_id=selected_queue_item_id,
        selected_slice=selected_slice,
        current_stage=current_stage,
        next_action=next_action,
        accepted_stages=tuple(accepted_stages),
        missing_stage=missing_stage,
        queue_consumer_result=dict(queue_consumer),
    )


def plan_reddog_resident_queue_orchestration(
    work_state_snapshot: Mapping[str, Any],
    *,
    queue_consumer_result: Optional[Mapping[str, Any]] = None,
    chain_results: Optional[Mapping[str, Mapping[str, Any]]] = None,
    requested_queue_item_id: Optional[str] = None,
    now_iso: Optional[str] = None,
) -> ResidentQueueOrchestrationPlan:
    """Plan the next queue-authorized bridge without invoking it."""

    if chain_results is not None and not isinstance(chain_results, Mapping):
        return _reject(
            reasons=(FAIL_CHAIN_RESULTS_NOT_MAPPING,),
            selected_queue_item_id=None,
            selected_slice=None,
            current_stage=None,
            next_action="REJECT",
            accepted_stages=(),
        )

    results = chain_results or {}
    queue_consumer = _queue_consumer_result(
        work_state_snapshot,
        queue_consumer_result=queue_consumer_result,
        requested_queue_item_id=requested_queue_item_id,
        now_iso=now_iso,
    )
    selected_queue_item_id = (
        str(queue_consumer.get("selected_queue_item_id") or "")
        or None
    )
    selected_slice = str(queue_consumer.get("selected_slice") or "") or None
    queue_reasons = [str(reason) for reason in queue_consumer.get("rejection_reasons") or ()]
    if (
        queue_consumer.get("accepted") is not True
        or queue_consumer.get("status") != WRE_QUEUE_CONSUMER_DRYRUN_READY
    ):
        return _reject(
            reasons=(FAIL_QUEUE_CONSUMER_NOT_READY, *queue_reasons),
            selected_queue_item_id=selected_queue_item_id,
            selected_slice=selected_slice,
            current_stage="queue_consumer",
            next_action="REJECT",
            accepted_stages=(),
            queue_consumer=queue_consumer,
        )

    accepted_stages: List[str] = ["queue_consumer"]
    for index, stage in enumerate(_CHAIN):
        supplied = _mapping(results.get(stage.key))
        if not supplied:
            future_supplied = [key for key in _STAGE_KEYS[index + 1 :] if _mapping(results.get(key))]
            if future_supplied:
                return _reject(
                    reasons=(
                        f"{FAIL_OUT_OF_ORDER_STAGE_RESULT}:{stage.key}",
                        *(f"future_stage_present:{key}" for key in future_supplied),
                    ),
                    selected_queue_item_id=selected_queue_item_id,
                    selected_slice=selected_slice,
                    current_stage=stage.key,
                    next_action=stage.next_action_when_missing,
                    accepted_stages=accepted_stages,
                    queue_consumer=queue_consumer,
                )
            return _ready(
                selected_queue_item_id=selected_queue_item_id,
                selected_slice=selected_slice,
                current_stage=stage.key,
                next_action=stage.next_action_when_missing,
                accepted_stages=accepted_stages,
                missing_stage=stage.key,
                queue_consumer=queue_consumer,
            )

        if supplied.get(stage.status_field) != stage.accepted_value:
            reasons = [
                f"{FAIL_STAGE_REJECTED}:{stage.key}",
                *[str(reason) for reason in supplied.get("rejection_reasons") or ()],
            ]
            return _reject(
                reasons=reasons,
                selected_queue_item_id=selected_queue_item_id,
                selected_slice=selected_slice,
                current_stage=stage.key,
                next_action="REJECT",
                accepted_stages=accepted_stages,
                queue_consumer=queue_consumer,
            )
        accepted_stages.append(stage.key)

    return _ready(
        selected_queue_item_id=selected_queue_item_id,
        selected_slice=selected_slice,
        current_stage=None,
        next_action=NEXT_QUEUE_CHAIN_COMPLETE,
        accepted_stages=accepted_stages,
        missing_stage=None,
        queue_consumer=queue_consumer,
    )


__all__ = [
    "FAIL_CHAIN_RESULTS_NOT_MAPPING",
    "FAIL_OUT_OF_ORDER_STAGE_RESULT",
    "FAIL_QUEUE_CONSUMER_NOT_READY",
    "FAIL_STAGE_REJECTED",
    "NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN",
    "NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE",
    "NEXT_QUEUE_AUTHORITY_VERIFICATION_INVOKE",
    "NEXT_QUEUE_ASSURANCE_CAPACITY_ADMISSION",
    "NEXT_QUEUE_BOUNDED_WORKER_PILOT_INVOKE",
    "NEXT_QUEUE_CHAIN_COMPLETE",
    "NEXT_QUEUE_EXECUTION_VALVE_INVOKE",
    "NEXT_QUEUE_EXECUTOR_PLAN_DRYRUN",
    "NEXT_QUEUE_HELD_OUT_REGRESSION_GATE_INVOKE",
    "NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE",
    "NEXT_QUEUE_SLICE_VERIFIER_INVOKE",
    "NEXT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_INVOKE",
    "NEXT_QUEUE_VERIFIED_OUTCOME_RATCHET_INVOKE",
    "NEXT_QUEUE_WORKER_DISPATCH_DRYRUN",
    "NEXT_QUEUE_WORKER_DISPATCH_RUNTIME",
    "NEXT_QUEUE_WORK_ORDER_INVOCATION",
    "NEXT_QUEUE_WORKTREE_CREATE_INVOKE",
    "RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE",
    "RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY",
    "RESIDENT_QUEUE_ORCHESTRATION_PLAN_REJECT",
    "ResidentQueueOrchestrationPlan",
    "ResidentQueueStage",
    "plan_reddog_resident_queue_orchestration",
]
