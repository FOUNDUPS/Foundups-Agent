"""Bounded serial loop for resident RedDog queue dispatch.

Slice: REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_RUNNER_PHASE1

This module repeatedly invokes the already-built resident queue next-stage
dispatcher with an injected handler map until the selected queue chain is
complete, rejected, or a caller-supplied step bound is reached.

It creates no default handlers and no runtime dependencies. It does not sign,
verify signatures, spawn workers, create worktrees, run shell commands, enqueue
OpenClaw, dispatch Hermes, publish PRs, admit PatternMemory, settle rewards,
mutate repository files, or re-index HoloIndex. Any stage effect comes only
from explicit caller-provided handlers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT,
    ResidentQueueNextStageDispatchResult,
    ResidentQueueStageHandler,
    invoke_reddog_resident_queue_next_stage_dispatch,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE,
    RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY,
    ResidentQueueOrchestrationPlan,
    plan_reddog_resident_queue_orchestration,
)


RESIDENT_QUEUE_SERIAL_LOOP_COMPLETE = "RESIDENT_QUEUE_SERIAL_LOOP_COMPLETE"
RESIDENT_QUEUE_SERIAL_LOOP_LIMIT_REACHED = "RESIDENT_QUEUE_SERIAL_LOOP_LIMIT_REACHED"
RESIDENT_QUEUE_SERIAL_LOOP_REJECT = "RESIDENT_QUEUE_SERIAL_LOOP_REJECT"

MAX_RESIDENT_QUEUE_SERIAL_LOOP_STEPS = 16

FAIL_EXPLICIT_LOOP_MISSING = "FAIL_EXPLICIT_RESIDENT_QUEUE_SERIAL_LOOP_MISSING"
FAIL_MAX_STEPS_INVALID = "FAIL_MAX_STEPS_INVALID"
FAIL_PLAN_NOT_READY = "FAIL_PLAN_NOT_READY"
FAIL_DISPATCH_REJECTED = "FAIL_DISPATCH_REJECTED"


@dataclass(frozen=True)
class ResidentQueueSerialLoopResult:
    """Result returned by the bounded serial queue loop."""

    accepted: bool
    status: str
    rejection_reasons: list[str] = field(default_factory=list)
    steps_run: int = 0
    dispatched_stages: tuple[str, ...] = ()
    next_action: Optional[str] = None
    final_plan: Optional[ResidentQueueOrchestrationPlan] = None
    dispatch_results: tuple[ResidentQueueNextStageDispatchResult, ...] = ()
    no_default_handler_used: bool = True
    no_dependency_created_by_loop: bool = True
    no_signing_performed_by_loop: bool = True
    no_worker_spawned_by_loop: bool = True
    no_worktree_created_by_loop: bool = True
    no_shell_command_executed_by_loop: bool = True
    no_openclaw_enqueue_performed_by_loop: bool = True
    no_hermes_dispatch_performed_by_loop: bool = True
    no_repo_mutation_performed_by_loop: bool = True
    no_holoindex_reindex_performed_by_loop: bool = True
    no_pr_created_by_loop: bool = True
    no_pattern_memory_client_created_by_loop: bool = True
    no_reward_settlement_performed_by_loop: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["final_plan"] = self.final_plan.to_dict() if self.final_plan else None
        payload["dispatch_results"] = tuple(result.to_dict() for result in self.dispatch_results)
        return payload


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


def _plan(
    *,
    work_state_snapshot: Mapping[str, Any],
    store: ResidentQueueChainResultsStore,
    requested_queue_item_id: Optional[str],
    now_iso: str,
) -> ResidentQueueOrchestrationPlan:
    state = _mapping(store.load())
    return plan_reddog_resident_queue_orchestration(
        work_state_snapshot,
        chain_results=_stage_results(state),
        requested_queue_item_id=requested_queue_item_id,
        now_iso=now_iso,
    )


def _reject(
    reasons: list[str],
    *,
    steps_run: int = 0,
    dispatched_stages: tuple[str, ...] = (),
    final_plan: Optional[ResidentQueueOrchestrationPlan] = None,
    dispatch_results: tuple[ResidentQueueNextStageDispatchResult, ...] = (),
) -> ResidentQueueSerialLoopResult:
    return ResidentQueueSerialLoopResult(
        accepted=False,
        status=RESIDENT_QUEUE_SERIAL_LOOP_REJECT,
        rejection_reasons=list(dict.fromkeys(reasons)),
        steps_run=steps_run,
        dispatched_stages=dispatched_stages,
        next_action=final_plan.next_action if final_plan else None,
        final_plan=final_plan,
        dispatch_results=dispatch_results,
    )


def run_reddog_resident_queue_serial_loop(
    *,
    explicit_resident_queue_serial_loop_requested: bool,
    work_state_snapshot: Mapping[str, Any],
    store: ResidentQueueChainResultsStore,
    handlers: Mapping[str, ResidentQueueStageHandler],
    now_iso: str,
    requested_queue_item_id: Optional[str] = None,
    max_steps: int = MAX_RESIDENT_QUEUE_SERIAL_LOOP_STEPS,
) -> ResidentQueueSerialLoopResult:
    """Advance one resident queue item through injected handlers."""

    if explicit_resident_queue_serial_loop_requested is not True:
        return _reject([FAIL_EXPLICIT_LOOP_MISSING])
    if (
        not isinstance(max_steps, int)
        or max_steps < 1
        or max_steps > MAX_RESIDENT_QUEUE_SERIAL_LOOP_STEPS
    ):
        return _reject([FAIL_MAX_STEPS_INVALID])

    dispatched: list[str] = []
    dispatch_results: list[ResidentQueueNextStageDispatchResult] = []
    current_plan = _plan(
        work_state_snapshot=work_state_snapshot,
        store=store,
        requested_queue_item_id=requested_queue_item_id,
        now_iso=now_iso,
    )
    if current_plan.accepted is True and current_plan.status == RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE:
        return ResidentQueueSerialLoopResult(
            accepted=True,
            status=RESIDENT_QUEUE_SERIAL_LOOP_COMPLETE,
            steps_run=0,
            dispatched_stages=(),
            next_action=current_plan.next_action,
            final_plan=current_plan,
            dispatch_results=(),
        )
    if current_plan.accepted is not True or current_plan.status != RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY:
        return _reject(
            [FAIL_PLAN_NOT_READY, *current_plan.rejection_reasons],
            final_plan=current_plan,
        )

    for _ in range(max_steps):
        dispatch = invoke_reddog_resident_queue_next_stage_dispatch(
            explicit_resident_queue_stage_dispatch_requested=True,
            work_state_snapshot=work_state_snapshot,
            store=store,
            handlers=handlers,
            now_iso=now_iso,
            requested_queue_item_id=requested_queue_item_id,
        )
        if dispatch.accepted is not True or dispatch.decision != RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT:
            return _reject(
                [FAIL_DISPATCH_REJECTED, *dispatch.rejection_reasons],
                steps_run=len(dispatch_results),
                dispatched_stages=tuple(dispatched),
                final_plan=dispatch.plan or current_plan,
                dispatch_results=tuple(dispatch_results),
            )
        dispatch_results.append(dispatch)
        if dispatch.dispatched_stage:
            dispatched.append(dispatch.dispatched_stage)

        current_plan = _plan(
            work_state_snapshot=work_state_snapshot,
            store=store,
            requested_queue_item_id=requested_queue_item_id,
            now_iso=now_iso,
        )
        if current_plan.accepted is True and current_plan.status == RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE:
            return ResidentQueueSerialLoopResult(
                accepted=True,
                status=RESIDENT_QUEUE_SERIAL_LOOP_COMPLETE,
                steps_run=len(dispatch_results),
                dispatched_stages=tuple(dispatched),
                next_action=current_plan.next_action,
                final_plan=current_plan,
                dispatch_results=tuple(dispatch_results),
            )
        if current_plan.accepted is not True or current_plan.status != RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY:
            return _reject(
                [FAIL_PLAN_NOT_READY, *current_plan.rejection_reasons],
                steps_run=len(dispatch_results),
                dispatched_stages=tuple(dispatched),
                final_plan=current_plan,
                dispatch_results=tuple(dispatch_results),
            )

    return ResidentQueueSerialLoopResult(
        accepted=True,
        status=RESIDENT_QUEUE_SERIAL_LOOP_LIMIT_REACHED,
        steps_run=len(dispatch_results),
        dispatched_stages=tuple(dispatched),
        next_action=current_plan.next_action,
        final_plan=current_plan,
        dispatch_results=tuple(dispatch_results),
    )


__all__ = [
    "FAIL_DISPATCH_REJECTED",
    "FAIL_EXPLICIT_LOOP_MISSING",
    "FAIL_MAX_STEPS_INVALID",
    "FAIL_PLAN_NOT_READY",
    "MAX_RESIDENT_QUEUE_SERIAL_LOOP_STEPS",
    "RESIDENT_QUEUE_SERIAL_LOOP_COMPLETE",
    "RESIDENT_QUEUE_SERIAL_LOOP_LIMIT_REACHED",
    "RESIDENT_QUEUE_SERIAL_LOOP_REJECT",
    "ResidentQueueSerialLoopResult",
    "run_reddog_resident_queue_serial_loop",
]
