"""Resident RedDog execution-valve stage handler.

Slice: REDDOG_RESIDENT_QUEUE_EXECUTION_VALVE_HANDLER_PHASE1

This module adapts the existing queue-authorized execution-valve explicit
invoke guard to the resident queue next-stage dispatcher. It reads the recorded
`work_order_invocation` and `executor_plan` stage results from the chain-results
store, resolves the bound work order through an injected resolver, and evaluates
the existing execution valve with an injected environment.

It emits only a valve decision. It does not create worktrees, spawn workers,
execute shell commands, enqueue OpenClaw, dispatch Hermes, publish PRs, settle
rewards, mutate repository files, or re-index HoloIndex.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Optional, Protocol

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_EXECUTION_VALVE_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    INTAKE_FOUNDUP_JOB,
    VALVE_OPEN_WORKTREE_CREATE,
    ExecutionValveEnvironment,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_execution_valve_invoke import (
    QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT,
    invoke_reddog_wre_queue_authorized_execution_valve,
)


EXECUTION_VALVE_STAGE_KEY = "execution_valve"
EXECUTOR_PLAN_STAGE_KEY = "executor_plan"
WORK_ORDER_INVOCATION_STAGE_KEY = "work_order_invocation"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_WORK_ORDER_INVOCATION_STAGE_MISSING = "FAIL_WORK_ORDER_INVOCATION_STAGE_MISSING"
FAIL_EXECUTOR_PLAN_STAGE_MISSING = "FAIL_EXECUTOR_PLAN_STAGE_MISSING"
FAIL_WORK_ORDER_ID_MISSING = "FAIL_WORK_ORDER_ID_MISSING"
FAIL_WORK_ORDER_MISSING = "FAIL_WORK_ORDER_MISSING"


class ResidentQueueExecutionValveWorkOrderResolver(Protocol):
    """Injected resolver for the work order bound to queue invocation."""

    def resolve(
        self,
        *,
        work_order_id: str,
        queue_item_id: Optional[str],
        selected_slice: Optional[str],
    ) -> Mapping[str, Any]:
        """Return the work order mapping for an accepted invocation result."""


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _stage_results(state: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    raw = state.get("stage_results") if state.get("schema_version") == "reddog_resident_queue_chain_results.v1" else state
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): value for key, value in raw.items() if isinstance(value, Mapping)}


def _work_order_id_from_invocation(work_order_invocation: Mapping[str, Any]) -> str:
    invocation = _mapping(work_order_invocation.get("invocation_result"))
    return str(invocation.get("work_order_id") or "").strip()


def _reject(*reasons: str) -> dict[str, Any]:
    return {
        "decision": QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "valve_decision": None,
        "explicit_queue_authorized_execution_valve_requested": False,
        "no_worker_spawn_performed": True,
        "no_worktree_created": True,
        "no_shell_command_executed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_pr_created": True,
        "no_reward_settlement_performed": True,
    }


@dataclass(frozen=True)
class ResidentQueueExecutionValveStageHandler:
    """Callable handler for the resident queue `execution_valve` stage."""

    chain_results_store: ResidentQueueChainResultsStore
    work_order_resolver: ResidentQueueExecutionValveWorkOrderResolver
    valve_environment: ExecutionValveEnvironment | Mapping[str, Any]
    now: Optional[datetime] = None
    intake_target: str = INTAKE_FOUNDUP_JOB
    expected_valve_state: str = VALVE_OPEN_WORKTREE_CREATE

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != EXECUTION_VALVE_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{EXECUTION_VALVE_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_EXECUTION_VALVE_INVOKE:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_EXECUTION_VALVE_INVOKE}",
                f"actual:{request.next_action}",
            )

        stage_results = _stage_results(_mapping(self.chain_results_store.load()))
        work_order_invocation = _mapping(stage_results.get(WORK_ORDER_INVOCATION_STAGE_KEY))
        if not work_order_invocation:
            return _reject(FAIL_WORK_ORDER_INVOCATION_STAGE_MISSING)
        executor_plan = _mapping(stage_results.get(EXECUTOR_PLAN_STAGE_KEY))
        if not executor_plan:
            return _reject(FAIL_EXECUTOR_PLAN_STAGE_MISSING)

        work_order_id = _work_order_id_from_invocation(work_order_invocation)
        if not work_order_id:
            return _reject(FAIL_WORK_ORDER_ID_MISSING)
        work_order = _mapping(
            self.work_order_resolver.resolve(
                work_order_id=work_order_id,
                queue_item_id=request.queue_item_id,
                selected_slice=request.selected_slice,
            )
        )
        if not work_order:
            return _reject(FAIL_WORK_ORDER_MISSING, f"work_order_id:{work_order_id}")

        return invoke_reddog_wre_queue_authorized_execution_valve(
            explicit_queue_authorized_execution_valve_requested=True,
            queue_work_order_invocation_result=work_order_invocation,
            queue_executor_plan_result=executor_plan,
            work_order=work_order,
            valve_environment=self.valve_environment,
            now=self.now,
            intake_target=self.intake_target,
            expected_valve_state=self.expected_valve_state,
        ).to_dict()


def build_reddog_resident_queue_execution_valve_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    work_order_resolver: ResidentQueueExecutionValveWorkOrderResolver,
    valve_environment: ExecutionValveEnvironment | Mapping[str, Any],
    now: Optional[datetime] = None,
    intake_target: str = INTAKE_FOUNDUP_JOB,
    expected_valve_state: str = VALVE_OPEN_WORKTREE_CREATE,
) -> ResidentQueueExecutionValveStageHandler:
    """Build the injected execution-valve handler for the dispatcher."""

    return ResidentQueueExecutionValveStageHandler(
        chain_results_store=chain_results_store,
        work_order_resolver=work_order_resolver,
        valve_environment=valve_environment,
        now=now,
        intake_target=intake_target,
        expected_valve_state=expected_valve_state,
    )


__all__ = [
    "EXECUTION_VALVE_STAGE_KEY",
    "EXECUTOR_PLAN_STAGE_KEY",
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "FAIL_EXECUTOR_PLAN_STAGE_MISSING",
    "FAIL_WORK_ORDER_ID_MISSING",
    "FAIL_WORK_ORDER_INVOCATION_STAGE_MISSING",
    "FAIL_WORK_ORDER_MISSING",
    "ResidentQueueExecutionValveStageHandler",
    "ResidentQueueExecutionValveWorkOrderResolver",
    "WORK_ORDER_INVOCATION_STAGE_KEY",
    "build_reddog_resident_queue_execution_valve_stage_handler",
]
