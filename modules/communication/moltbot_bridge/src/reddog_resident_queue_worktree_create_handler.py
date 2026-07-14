"""Resident RedDog worktree-create stage handler.

Slice: REDDOG_RESIDENT_QUEUE_WORKTREE_CREATE_HANDLER_PHASE1

This module adapts the existing queue-authorized worktree-create explicit
invoke guard to the resident queue next-stage dispatcher. It reads recorded
`executor_plan` and `execution_valve` stage results from the chain-results
store, resolves the bound work order through an injected resolver, and calls the
existing worktree-create guard with an injected runner.

The handler does not edit files, execute task commands, enqueue OpenClaw,
dispatch Hermes, publish PRs, settle rewards, or re-index HoloIndex.
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
    NEXT_QUEUE_WORKTREE_CREATE_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_worktree_create_invoke import (
    QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT,
    invoke_reddog_wre_queue_authorized_worktree_create,
)


EXECUTION_VALVE_STAGE_KEY = "execution_valve"
EXECUTOR_PLAN_STAGE_KEY = "executor_plan"
WORKTREE_CREATE_STAGE_KEY = "worktree_create"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_EXECUTOR_PLAN_STAGE_MISSING = "FAIL_EXECUTOR_PLAN_STAGE_MISSING"
FAIL_EXECUTION_VALVE_STAGE_MISSING = "FAIL_EXECUTION_VALVE_STAGE_MISSING"
FAIL_WORK_ORDER_ID_MISSING = "FAIL_WORK_ORDER_ID_MISSING"
FAIL_WORK_ORDER_MISSING = "FAIL_WORK_ORDER_MISSING"


class ResidentQueueWorktreeCreateWorkOrderResolver(Protocol):
    """Injected resolver for the work order bound to executor plan."""

    def resolve(
        self,
        *,
        work_order_id: str,
        queue_item_id: Optional[str],
        selected_slice: Optional[str],
    ) -> Mapping[str, Any]:
        """Return the work order mapping for an accepted executor plan."""


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


def _work_order_id_from_executor_plan(executor_plan: Mapping[str, Any]) -> str:
    executor = _mapping(executor_plan.get("executor_plan_result"))
    if executor.get("work_order_id"):
        return str(executor.get("work_order_id") or "").strip()
    plan = _mapping(executor.get("plan"))
    return str(plan.get("work_order_id") or "").strip()


def _reject(*reasons: str) -> dict[str, Any]:
    return {
        "decision": QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "worktree_create_result": None,
        "explicit_queue_authorized_worktree_create_requested": False,
        "no_task_execution_performed": True,
        "no_file_edit_performed": True,
        "no_shell_command_executed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_pr_created": True,
        "no_reward_settlement_performed": True,
        "no_holoindex_reindex_performed": True,
    }


@dataclass(frozen=True)
class ResidentQueueWorktreeCreateStageHandler:
    """Callable handler for the resident queue `worktree_create` stage."""

    chain_results_store: ResidentQueueChainResultsStore
    work_order_resolver: ResidentQueueWorktreeCreateWorkOrderResolver
    runner: Any
    repo_root: Path
    now: Optional[datetime] = None
    locks: Optional[MutableSet[str]] = None

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != WORKTREE_CREATE_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{WORKTREE_CREATE_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_WORKTREE_CREATE_INVOKE:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_WORKTREE_CREATE_INVOKE}",
                f"actual:{request.next_action}",
            )

        stage_results = _stage_results(_mapping(self.chain_results_store.load()))
        executor_plan = _mapping(stage_results.get(EXECUTOR_PLAN_STAGE_KEY))
        if not executor_plan:
            return _reject(FAIL_EXECUTOR_PLAN_STAGE_MISSING)
        execution_valve = _mapping(stage_results.get(EXECUTION_VALVE_STAGE_KEY))
        if not execution_valve:
            return _reject(FAIL_EXECUTION_VALVE_STAGE_MISSING)

        work_order_id = _work_order_id_from_executor_plan(executor_plan)
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

        return invoke_reddog_wre_queue_authorized_worktree_create(
            explicit_queue_authorized_worktree_create_requested=True,
            queue_executor_plan_result=executor_plan,
            queue_execution_valve_result=execution_valve,
            work_order=work_order,
            runner=self.runner,
            repo_root=self.repo_root,
            now=self.now,
            locks=self.locks,
        ).to_dict()


def build_reddog_resident_queue_worktree_create_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    work_order_resolver: ResidentQueueWorktreeCreateWorkOrderResolver,
    runner: Any,
    repo_root: Path,
    now: Optional[datetime] = None,
    locks: Optional[MutableSet[str]] = None,
) -> ResidentQueueWorktreeCreateStageHandler:
    """Build the injected worktree-create handler for the dispatcher."""

    return ResidentQueueWorktreeCreateStageHandler(
        chain_results_store=chain_results_store,
        work_order_resolver=work_order_resolver,
        runner=runner,
        repo_root=repo_root,
        now=now,
        locks=locks,
    )


__all__ = [
    "EXECUTION_VALVE_STAGE_KEY",
    "EXECUTOR_PLAN_STAGE_KEY",
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "FAIL_EXECUTION_VALVE_STAGE_MISSING",
    "FAIL_EXECUTOR_PLAN_STAGE_MISSING",
    "FAIL_WORK_ORDER_ID_MISSING",
    "FAIL_WORK_ORDER_MISSING",
    "ResidentQueueWorktreeCreateStageHandler",
    "ResidentQueueWorktreeCreateWorkOrderResolver",
    "WORKTREE_CREATE_STAGE_KEY",
    "build_reddog_resident_queue_worktree_create_stage_handler",
]
