"""RedDog queue-authorized execution valve explicit invoke guard.

Slice: REDDOG_WRE_QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_PHASE1

This module evaluates the existing RedDog execution valve from a queue-derived,
signed-authority work-order invocation and a queue-authorized executor-plan
dry-run. It emits only an execution-valve decision. It does not create
worktrees, spawn workers, run shell commands, enqueue OpenClaw, dispatch Hermes,
mutate repository files, publish PRs, settle rewards, or re-index HoloIndex.
"""

from __future__ import annotations

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
    evaluate_reddog_execution_valve,
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


def invoke_reddog_wre_queue_authorized_execution_valve(
    *,
    explicit_queue_authorized_execution_valve_requested: bool,
    queue_work_order_invocation_result: Mapping[str, Any],
    queue_executor_plan_result: Mapping[str, Any],
    work_order: Mapping[str, Any],
    valve_environment: ExecutionValveEnvironment | Mapping[str, Any],
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

    queue_invocation = _mapping(queue_work_order_invocation_result)
    if queue_invocation.get("decision") != QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT:
        return _reject(
            [QueueAuthorizedExecutionValveInvokeReason.WORK_ORDER_INVOCATION_NOT_ACCEPTED],
            explicit_requested=True,
        )
    invocation_payload = _mapping(queue_invocation.get("invocation_result"))
    if not invocation_payload:
        return _reject(
            [QueueAuthorizedExecutionValveInvokeReason.INVOCATION_PAYLOAD_MISSING],
            explicit_requested=True,
        )

    queue_executor = _mapping(queue_executor_plan_result)
    if queue_executor.get("decision") != QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT:
        return _reject(
            [QueueAuthorizedExecutionValveInvokeReason.EXECUTOR_PLAN_NOT_ACCEPTED],
            explicit_requested=True,
        )
    executor_payload = _mapping(queue_executor.get("executor_plan_result"))
    if not executor_payload:
        return _reject(
            [QueueAuthorizedExecutionValveInvokeReason.EXECUTOR_PLAN_PAYLOAD_MISSING],
            explicit_requested=True,
        )

    valve = evaluate_reddog_execution_valve(
        ExecutionValveRequest(
            work_order=work_order,
            policy_gate_receipt=_minimal_policy_gate_receipt(invocation_payload),
            reddog_work_order_receipt=_minimal_reddog_work_order_receipt(invocation_payload),
            invocation_result=invocation_payload,
            executor_plan_result=executor_payload,
            intake_target=intake_target,
            permission_snapshot=_mapping(work_order.get("repo_permission_snapshot")),
        ),
        valve_environment,
        now=now,
    )
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


__all__ = [
    "QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT",
    "QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT",
    "QueueAuthorizedExecutionValveInvokeReason",
    "QueueAuthorizedExecutionValveInvokeResult",
    "invoke_reddog_wre_queue_authorized_execution_valve",
]
