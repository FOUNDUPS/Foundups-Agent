"""Resident RedDog queue next-stage dispatcher.

Slice: REDDOG_RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_PHASE1

This module invokes exactly one injected handler for the current resident
queue-chain stage, then records the returned result through the governed
chain-results store. It has no default handlers and imports no concrete bridge
implementation. A caller must explicitly provide the handler map.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping, Optional, Protocol

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultRecordResult,
    ResidentQueueChainResultsStore,
    record_resident_queue_stage_result,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY,
    ResidentQueueOrchestrationPlan,
    plan_reddog_resident_queue_orchestration,
)


RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT = "RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT"
RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_REJECT = "RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_REJECT"

FAIL_EXPLICIT_DISPATCH_MISSING = "FAIL_EXPLICIT_DISPATCH_MISSING"
FAIL_PLAN_NOT_READY = "FAIL_PLAN_NOT_READY"
FAIL_CURRENT_STAGE_MISSING = "FAIL_CURRENT_STAGE_MISSING"
FAIL_HANDLER_MISSING = "FAIL_HANDLER_MISSING"
FAIL_HANDLER_EXCEPTION = "FAIL_HANDLER_EXCEPTION"
FAIL_HANDLER_RESULT_INVALID = "FAIL_HANDLER_RESULT_INVALID"
FAIL_RECORD_REJECTED = "FAIL_RECORD_REJECTED"


@dataclass(frozen=True)
class ResidentQueueStageDispatchRequest:
    """Payload passed to an injected stage handler."""

    stage_key: str
    next_action: str
    queue_item_id: Optional[str]
    selected_slice: Optional[str]
    plan_id: str
    accepted_stages: tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ResidentQueueStageHandler(Protocol):
    """Injected handler for one resident queue-chain stage."""

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        """Return the stage result to be recorded."""


@dataclass(frozen=True)
class ResidentQueueNextStageDispatchResult:
    """Result returned by the injected-handler dispatcher."""

    accepted: bool
    decision: str
    rejection_reasons: list[str] = field(default_factory=list)
    dispatched_stage: Optional[str] = None
    next_action: Optional[str] = None
    plan: Optional[ResidentQueueOrchestrationPlan] = None
    record_result: Optional[ResidentQueueChainResultRecordResult] = None
    stage_handler_invoked: bool = False
    deferred: bool = False
    defer_reason: Optional[str] = None
    retry_at: Optional[str] = None
    no_default_handler_used: bool = True
    no_authority_issued_by_dispatcher: bool = True
    no_worker_spawned_by_dispatcher: bool = True
    no_worktree_created_by_dispatcher: bool = True
    no_shell_command_executed_by_dispatcher: bool = True
    no_openclaw_enqueue_performed_by_dispatcher: bool = True
    no_hermes_dispatch_performed_by_dispatcher: bool = True
    no_repo_mutation_performed_by_dispatcher: bool = True
    no_holoindex_reindex_performed_by_dispatcher: bool = True
    no_pr_created_by_dispatcher: bool = True
    no_pattern_memory_write_performed_by_dispatcher: bool = True
    no_reward_settlement_performed_by_dispatcher: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accepted": self.accepted,
            "decision": self.decision,
            "rejection_reasons": self.rejection_reasons,
            "dispatched_stage": self.dispatched_stage,
            "next_action": self.next_action,
            "plan": self.plan.to_dict() if self.plan else None,
            "record_result": self.record_result.to_dict() if self.record_result else None,
            "stage_handler_invoked": self.stage_handler_invoked,
            "deferred": self.deferred,
            "defer_reason": self.defer_reason,
            "retry_at": self.retry_at,
            "no_default_handler_used": self.no_default_handler_used,
            "no_authority_issued_by_dispatcher": self.no_authority_issued_by_dispatcher,
            "no_worker_spawned_by_dispatcher": self.no_worker_spawned_by_dispatcher,
            "no_worktree_created_by_dispatcher": self.no_worktree_created_by_dispatcher,
            "no_shell_command_executed_by_dispatcher": self.no_shell_command_executed_by_dispatcher,
            "no_openclaw_enqueue_performed_by_dispatcher": self.no_openclaw_enqueue_performed_by_dispatcher,
            "no_hermes_dispatch_performed_by_dispatcher": self.no_hermes_dispatch_performed_by_dispatcher,
            "no_repo_mutation_performed_by_dispatcher": self.no_repo_mutation_performed_by_dispatcher,
            "no_holoindex_reindex_performed_by_dispatcher": self.no_holoindex_reindex_performed_by_dispatcher,
            "no_pr_created_by_dispatcher": self.no_pr_created_by_dispatcher,
            "no_pattern_memory_write_performed_by_dispatcher": self.no_pattern_memory_write_performed_by_dispatcher,
            "no_reward_settlement_performed_by_dispatcher": self.no_reward_settlement_performed_by_dispatcher,
        }


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _stage_results(state: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    raw = state.get("stage_results") if state.get("schema_version") == "reddog_resident_queue_chain_results.v1" else state
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): value for key, value in raw.items() if isinstance(value, Mapping)}


def _reject(
    reasons: list[str],
    *,
    plan: Optional[ResidentQueueOrchestrationPlan] = None,
    dispatched_stage: Optional[str] = None,
    next_action: Optional[str] = None,
    stage_handler_invoked: bool = False,
    record_result: Optional[ResidentQueueChainResultRecordResult] = None,
) -> ResidentQueueNextStageDispatchResult:
    return ResidentQueueNextStageDispatchResult(
        accepted=False,
        decision=RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_REJECT,
        rejection_reasons=list(dict.fromkeys(reasons)),
        dispatched_stage=dispatched_stage,
        next_action=next_action,
        plan=plan,
        record_result=record_result,
        stage_handler_invoked=stage_handler_invoked,
    )


def invoke_reddog_resident_queue_next_stage_dispatch(
    *,
    explicit_resident_queue_stage_dispatch_requested: bool,
    work_state_snapshot: Mapping[str, Any],
    store: ResidentQueueChainResultsStore,
    handlers: Mapping[str, ResidentQueueStageHandler],
    now_iso: str,
    requested_queue_item_id: Optional[str] = None,
) -> ResidentQueueNextStageDispatchResult:
    """Invoke one injected current-stage handler and record its result."""

    if explicit_resident_queue_stage_dispatch_requested is not True:
        return _reject([FAIL_EXPLICIT_DISPATCH_MISSING])

    current_state = _mapping(store.load())
    plan = plan_reddog_resident_queue_orchestration(
        work_state_snapshot,
        chain_results=_stage_results(current_state),
        requested_queue_item_id=requested_queue_item_id,
        now_iso=now_iso,
    )
    if plan.accepted is not True or plan.status != RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY:
        return _reject(
            [FAIL_PLAN_NOT_READY, *plan.rejection_reasons],
            plan=plan,
            next_action=plan.next_action,
        )
    if not plan.current_stage:
        return _reject(
            [FAIL_CURRENT_STAGE_MISSING],
            plan=plan,
            next_action=plan.next_action,
        )

    handler = handlers.get(plan.current_stage)
    if handler is None:
        return _reject(
            [FAIL_HANDLER_MISSING, f"stage:{plan.current_stage}"],
            plan=plan,
            dispatched_stage=plan.current_stage,
            next_action=plan.next_action,
        )

    request = ResidentQueueStageDispatchRequest(
        stage_key=plan.current_stage,
        next_action=plan.next_action,
        queue_item_id=plan.selected_queue_item_id,
        selected_slice=plan.selected_slice,
        plan_id=plan.plan_id,
        accepted_stages=plan.accepted_stages,
    )
    try:
        raw_stage_result = handler(request)
    except Exception as exc:  # noqa: BLE001 - injected handler failures fail closed.
        return _reject(
            [FAIL_HANDLER_EXCEPTION, exc.__class__.__name__],
            plan=plan,
            dispatched_stage=plan.current_stage,
            next_action=plan.next_action,
            stage_handler_invoked=True,
        )
    stage_result = _mapping(raw_stage_result)
    if not stage_result:
        return _reject(
            [FAIL_HANDLER_RESULT_INVALID],
            plan=plan,
            dispatched_stage=plan.current_stage,
            next_action=plan.next_action,
            stage_handler_invoked=True,
        )
    if stage_result.get("queue_chain_requeue_required") is True:
        return ResidentQueueNextStageDispatchResult(
            accepted=True,
            decision=RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT,
            rejection_reasons=[],
            dispatched_stage=plan.current_stage,
            next_action=plan.next_action,
            plan=plan,
            record_result=None,
            stage_handler_invoked=True,
            deferred=True,
            defer_reason=str(
                stage_result.get("status")
                or stage_result.get("decision")
                or "QUEUE_STAGE_DEFERRED"
            ),
            retry_at=str(stage_result.get("retry_at") or "") or None,
        )

    record = record_resident_queue_stage_result(
        work_state_snapshot=work_state_snapshot,
        store=store,
        stage_key=plan.current_stage,
        stage_result=stage_result,
        now_iso=now_iso,
        requested_queue_item_id=requested_queue_item_id,
    )
    if record.accepted is not True:
        return _reject(
            [FAIL_RECORD_REJECTED, *record.rejection_reasons],
            plan=plan,
            dispatched_stage=plan.current_stage,
            next_action=plan.next_action,
            stage_handler_invoked=True,
            record_result=record,
        )
    if stage_result.get("queue_chain_yield_required") is True:
        return ResidentQueueNextStageDispatchResult(
            accepted=True,
            decision=RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT,
            rejection_reasons=[],
            dispatched_stage=plan.current_stage,
            next_action=plan.next_action,
            plan=plan,
            record_result=record,
            stage_handler_invoked=True,
            deferred=True,
            defer_reason=str(
                stage_result.get("status")
                or stage_result.get("decision")
                or "QUEUE_STAGE_YIELDED"
            ),
            retry_at=str(stage_result.get("retry_at") or "") or None,
        )

    return ResidentQueueNextStageDispatchResult(
        accepted=True,
        decision=RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT,
        rejection_reasons=[],
        dispatched_stage=plan.current_stage,
        next_action=record.next_plan.next_action if record.next_plan else None,
        plan=plan,
        record_result=record,
        stage_handler_invoked=True,
    )


__all__ = [
    "FAIL_CURRENT_STAGE_MISSING",
    "FAIL_EXPLICIT_DISPATCH_MISSING",
    "FAIL_HANDLER_EXCEPTION",
    "FAIL_HANDLER_MISSING",
    "FAIL_HANDLER_RESULT_INVALID",
    "FAIL_PLAN_NOT_READY",
    "FAIL_RECORD_REJECTED",
    "RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT",
    "RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_REJECT",
    "ResidentQueueNextStageDispatchResult",
    "ResidentQueueStageDispatchRequest",
    "ResidentQueueStageHandler",
    "invoke_reddog_resident_queue_next_stage_dispatch",
]
