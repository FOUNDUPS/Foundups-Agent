"""RedDog queue-authorized execution valve explicit invoke guard.

Slice: REDDOG_WRE_QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_PHASE1

This module evaluates the existing RedDog execution valve from a queue-derived,
signed-authority work-order invocation and a queue-authorized executor-plan
dry-run. It emits only an execution-valve decision. It does not create
worktrees, spawn workers, run shell commands, enqueue OpenClaw, dispatch Hermes,
mutate repository files, publish PRs, settle rewards, or re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    INTAKE_FOUNDUP_JOB,
    VALVE_CLOSED,
    VALVE_OPEN_WORKTREE_CREATE,
    ExecutionValveDecision,
    ExecutionValveEnvironment,
    ExecutionValveRequest,
    GovernedExecutionValveEnvironment,
    evaluate_reddog_execution_valve,
    evaluate_reddog_execution_valve_canonical,
)
from modules.communication.moltbot_bridge.src.reddog_execution_valve_use_time_authority import (
    GovernedValveUseTimeResolution,
)
from modules.communication.moltbot_bridge.src.reddog_progressive_execution_stage_policy import (
    validate_signed_progressive_stage_binding,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_executor_plan_dryrun import (
    QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_verified_authority_work_order_invoke import (
    QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
)


QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT = "QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT"
QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT = "QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT"


class QueueAuthorizedExecutionValveInvokeReason:
    EXPLICIT_INVOKE_MISSING = "REJECT_EXPLICIT_QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_MISSING"
    WORK_ORDER_INVOCATION_NOT_ACCEPTED = "REJECT_QUEUE_WORK_ORDER_INVOCATION_NOT_ACCEPTED"
    EXECUTOR_PLAN_NOT_ACCEPTED = "REJECT_QUEUE_EXECUTOR_PLAN_NOT_ACCEPTED"
    INVOCATION_PAYLOAD_MISSING = "REJECT_INVOCATION_PAYLOAD_MISSING"
    EXECUTOR_PLAN_PAYLOAD_MISSING = "REJECT_EXECUTOR_PLAN_PAYLOAD_MISSING"
    VALVE_STATE_NOT_EXPECTED = "REJECT_EXECUTION_VALVE_STATE_NOT_EXPECTED"
    GOVERNED_USE_TIME_AUTHORITY_MISSING = "REJECT_GOVERNED_USE_TIME_AUTHORITY_MISSING"
    BOUNDED_EXECUTION_STAGE_REQUIRED = "REJECT_SIGNED_BOUNDED_EXECUTION_STAGE_REQUIRED"


@dataclass(frozen=True)
class QueueAuthorizedExecutionValveInvokeResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    valve_decision: Optional[ExecutionValveDecision] = None
    explicit_queue_authorized_execution_valve_requested: bool = False
    no_worker_spawn_performed: bool = True
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
        payload["valve_decision"] = self.valve_decision.to_dict() if self.valve_decision else None
        return payload


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _minimal_policy_gate_receipt(invocation: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "decision": invocation.get("policy_gate_decision"),
        "receipt_digest": invocation.get("policy_gate_receipt_digest"),
        "no_execution_performed": True,
        "work_order_id": invocation.get("work_order_id"),
    }


def _minimal_reddog_work_order_receipt(invocation: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "receipt_id": invocation.get("receipt_id"),
        "receipt_digest": invocation.get("receipt_digest"),
        "policy_gate_receipt_digest": invocation.get("policy_gate_receipt_digest"),
        "no_execution_performed": True,
        "work_order_id": invocation.get("work_order_id"),
    }


def _reject(
    reasons: Sequence[str],
    *,
    explicit_requested: bool,
    valve_decision: Optional[ExecutionValveDecision] = None,
) -> QueueAuthorizedExecutionValveInvokeResult:
    return QueueAuthorizedExecutionValveInvokeResult(
        decision=QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT,
        rejection_reasons=list(dict.fromkeys(reasons)),
        valve_decision=valve_decision,
        explicit_queue_authorized_execution_valve_requested=explicit_requested,
    )


def _accepted_queue_payloads(
    invocation_result: Mapping[str, Any], executor_result: Mapping[str, Any]
) -> tuple[Mapping[str, Any], Mapping[str, Any], Optional[str]]:
    queue_invocation = _mapping(invocation_result)
    if queue_invocation.get("decision") != QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT:
        return {}, {}, QueueAuthorizedExecutionValveInvokeReason.WORK_ORDER_INVOCATION_NOT_ACCEPTED
    invocation = _mapping(queue_invocation.get("invocation_result"))
    if not invocation:
        return {}, {}, QueueAuthorizedExecutionValveInvokeReason.INVOCATION_PAYLOAD_MISSING
    queue_executor = _mapping(executor_result)
    if queue_executor.get("decision") != QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT:
        return {}, {}, QueueAuthorizedExecutionValveInvokeReason.EXECUTOR_PLAN_NOT_ACCEPTED
    executor = _mapping(queue_executor.get("executor_plan_result"))
    if not executor:
        return {}, {}, QueueAuthorizedExecutionValveInvokeReason.EXECUTOR_PLAN_PAYLOAD_MISSING
    return invocation, executor, None


def _evaluate_authorized_valve(
    request: ExecutionValveRequest,
    environment: ExecutionValveEnvironment | GovernedExecutionValveEnvironment | Mapping[str, Any],
    resolution: Optional[GovernedValveUseTimeResolution],
    now: Optional[datetime],
) -> tuple[Optional[ExecutionValveDecision], Optional[str]]:
    if not isinstance(environment, GovernedExecutionValveEnvironment):
        return evaluate_reddog_execution_valve(request, environment, now=now), None
    if resolution is None or resolution.environment is None:
        return None, QueueAuthorizedExecutionValveInvokeReason.GOVERNED_USE_TIME_AUTHORITY_MISSING
    valve = evaluate_reddog_execution_valve_canonical(
        request,
        resolution.environment,
        expected_bindings=resolution.expected_bindings,
        permission_ttl_seconds=resolution.permission_ttl_seconds,
        permission_expires_at=resolution.permission_expires_at,
        now=now,
    )
    if resolution.rejection_reasons:
        valve = _closed_with_use_time_rejections(valve, resolution.rejection_reasons)
    return valve, None


def invoke_reddog_wre_queue_authorized_execution_valve(
    *,
    explicit_queue_authorized_execution_valve_requested: bool,
    queue_work_order_invocation_result: Mapping[str, Any],
    queue_executor_plan_result: Mapping[str, Any],
    work_order: Mapping[str, Any],
    signed_work_authority: Mapping[str, Any],
    valve_environment: ExecutionValveEnvironment | GovernedExecutionValveEnvironment | Mapping[str, Any],
    governed_use_time_resolution: Optional[GovernedValveUseTimeResolution] = None,
    now: Optional[datetime] = None,
    intake_target: str = INTAKE_FOUNDUP_JOB,
    expected_valve_state: str = VALVE_OPEN_WORKTREE_CREATE,
) -> QueueAuthorizedExecutionValveInvokeResult:
    """Evaluate the execution valve from a queue-authorized receipt chain."""

    if explicit_queue_authorized_execution_valve_requested is not True:
        return _reject(
            [QueueAuthorizedExecutionValveInvokeReason.EXPLICIT_INVOKE_MISSING],
            explicit_requested=False,
        )

    authority = _mapping(signed_work_authority)
    if not validate_signed_progressive_stage_binding(
        _mapping(authority.get("progressive_policy_stage_receipt")),
        expected_receipt_id=authority.get("progressive_policy_stage_receipt_id"),
        expected_digest=authority.get("progressive_policy_stage_digest"),
        require_bounded_effects=True,
    ):
        return _reject(
            [QueueAuthorizedExecutionValveInvokeReason.BOUNDED_EXECUTION_STAGE_REQUIRED],
            explicit_requested=True,
        )

    invocation_payload, executor_payload, payload_reason = _accepted_queue_payloads(
        queue_work_order_invocation_result, queue_executor_plan_result
    )
    if payload_reason:
        return _reject([payload_reason], explicit_requested=True)

    valve_request = ExecutionValveRequest(
        work_order=work_order,
        policy_gate_receipt=_minimal_policy_gate_receipt(invocation_payload),
        reddog_work_order_receipt=_minimal_reddog_work_order_receipt(invocation_payload),
        invocation_result=invocation_payload,
        executor_plan_result=executor_payload,
        intake_target=intake_target,
        permission_snapshot=_mapping(work_order.get("repo_permission_snapshot")),
    )
    valve, valve_reason = _evaluate_authorized_valve(
        valve_request, valve_environment, governed_use_time_resolution, now
    )
    if valve_reason or valve is None:
        return _reject([valve_reason or "governed_valve_evaluation_missing"], explicit_requested=True)
    if valve.valve_state != expected_valve_state:
        return _reject(
            [
                QueueAuthorizedExecutionValveInvokeReason.VALVE_STATE_NOT_EXPECTED,
                *valve.rejection_reasons,
            ],
            explicit_requested=True,
            valve_decision=valve,
        )

    return QueueAuthorizedExecutionValveInvokeResult(
        decision=QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT,
        rejection_reasons=[],
        valve_decision=valve,
        explicit_queue_authorized_execution_valve_requested=True,
    )


def _closed_with_use_time_rejections(
    decision: ExecutionValveDecision, reasons: Sequence[str]
) -> ExecutionValveDecision:
    combined = list(dict.fromkeys([*reasons, *decision.rejection_reasons]))
    gates = list(dict.fromkeys([*decision.gates_checked, "canonical_use_time_authority"]))
    body = {
        **decision.to_dict(),
        "valve_state": VALVE_CLOSED,
        "rejection_reasons": combined,
        "gates_checked": gates,
    }
    body.pop("decision_digest", None)
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return ExecutionValveDecision(
        valve_state=VALVE_CLOSED,
        work_order_id=decision.work_order_id,
        rejection_reasons=combined,
        gates_checked=gates,
        no_execution_performed=True,
        decision_digest=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        intake_target=decision.intake_target,
        authorization_mode=decision.authorization_mode,
        authorization_binding_digest=decision.authorization_binding_digest,
    )


__all__ = [
    "QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT",
    "QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT",
    "QueueAuthorizedExecutionValveInvokeReason",
    "QueueAuthorizedExecutionValveInvokeResult",
    "invoke_reddog_wre_queue_authorized_execution_valve",
]
