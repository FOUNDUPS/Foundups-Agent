"""Resident RedDog executor-plan stage handler.

Slice: REDDOG_RESIDENT_QUEUE_EXECUTOR_PLAN_HANDLER_PHASE1

This module adapts the existing queue-authorized executor-plan dry-run bridge
to the resident queue next-stage dispatcher. It reads the recorded
`work_order_invocation` stage result from the chain-results store, resolves the
matching work order through an injected resolver, and emits only the existing
executor dry-run plan.

It does not open the execution valve, spawn workers, create worktrees, execute
shell commands, enqueue OpenClaw, dispatch Hermes, publish PRs, settle rewards,
mutate repository files, or re-index HoloIndex.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, MutableSet, Optional, Protocol

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_EXECUTOR_PLAN_DRYRUN,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_executor_plan_dryrun import (
    QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT,
    plan_reddog_wre_queue_authorized_executor_dryrun,
)


EXECUTOR_PLAN_STAGE_KEY = "executor_plan"
WORK_ORDER_INVOCATION_STAGE_KEY = "work_order_invocation"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_WORK_ORDER_INVOCATION_STAGE_MISSING = "FAIL_WORK_ORDER_INVOCATION_STAGE_MISSING"
FAIL_WORK_ORDER_ID_MISSING = "FAIL_WORK_ORDER_ID_MISSING"
FAIL_WORK_ORDER_MISSING = "FAIL_WORK_ORDER_MISSING"


class ResidentQueueExecutorPlanWorkOrderResolver(Protocol):
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
        "decision": QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "executor_plan_result": None,
        "explicit_queue_authorized_executor_plan_requested": False,
        "no_execution_valve_opened": True,
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
class ResidentQueueExecutorPlanStageHandler:
    """Callable handler for the resident queue `executor_plan` stage."""

    chain_results_store: ResidentQueueChainResultsStore
    work_order_resolver: ResidentQueueExecutorPlanWorkOrderResolver
    now: Optional[datetime] = None
    locks: Optional[MutableSet[str]] = None
    repo_root: str | Path = "."

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != EXECUTOR_PLAN_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{EXECUTOR_PLAN_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_EXECUTOR_PLAN_DRYRUN:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_EXECUTOR_PLAN_DRYRUN}",
                f"actual:{request.next_action}",
            )

        stage_results = _stage_results(_mapping(self.chain_results_store.load()))
        work_order_invocation = _mapping(stage_results.get(WORK_ORDER_INVOCATION_STAGE_KEY))
        if not work_order_invocation:
            return _reject(FAIL_WORK_ORDER_INVOCATION_STAGE_MISSING)

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

        return plan_reddog_wre_queue_authorized_executor_dryrun(
            explicit_queue_authorized_executor_plan_requested=True,
            queue_work_order_invocation_result=work_order_invocation,
            work_order=work_order,
            now=self.now,
            locks=self.locks,
            repo_root=self.repo_root,
        ).to_dict()


def build_reddog_resident_queue_executor_plan_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    work_order_resolver: ResidentQueueExecutorPlanWorkOrderResolver,
    now: Optional[datetime] = None,
    locks: Optional[MutableSet[str]] = None,
    repo_root: str | Path = ".",
) -> ResidentQueueExecutorPlanStageHandler:
    """Build the injected executor-plan handler for the dispatcher."""

    return ResidentQueueExecutorPlanStageHandler(
        chain_results_store=chain_results_store,
        work_order_resolver=work_order_resolver,
        now=now,
        locks=locks,
        repo_root=repo_root,
    )


__all__ = [
    "EXECUTOR_PLAN_STAGE_KEY",
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "FAIL_WORK_ORDER_ID_MISSING",
    "FAIL_WORK_ORDER_INVOCATION_STAGE_MISSING",
    "FAIL_WORK_ORDER_MISSING",
    "ResidentQueueExecutorPlanStageHandler",
    "ResidentQueueExecutorPlanWorkOrderResolver",
    "WORK_ORDER_INVOCATION_STAGE_KEY",
    "build_reddog_resident_queue_executor_plan_stage_handler",
]
