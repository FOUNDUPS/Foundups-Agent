"""Resident RedDog signed-authority worker-dispatch dry-run stage handler.

Slice: REDDOG_RESIDENT_QUEUE_WORKER_DISPATCH_DRYRUN_STAGE_PHASE1

This module adapts the signed-authority worker-dispatch dry-run planner to the
resident queue next-stage dispatcher. It reads the accepted authority runtime
and verification stage results from the chain-results store, binds them to the
authoritative WSP15 allocation receipt on the selected queue item, and emits
planned worker intents only.

It does not register workers, spawn workers, mutate queues, create worktrees,
execute shell commands, enqueue OpenClaw, dispatch Hermes, publish PRs, settle
rewards, mutate repository files, or re-index HoloIndex.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_WORKER_DISPATCH_DRYRUN,
)
from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_REJECT,
    plan_reddog_signed_authority_worker_dispatch_dry_run,
)


AUTHORITY_RUNTIME_STAGE_KEY = "authority_runtime"
AUTHORITY_VERIFICATION_STAGE_KEY = "authority_verification"
WORKER_DISPATCH_DRYRUN_STAGE_KEY = "worker_dispatch_dryrun"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_AUTHORITY_RUNTIME_STAGE_MISSING = "FAIL_AUTHORITY_RUNTIME_STAGE_MISSING"
FAIL_AUTHORITY_VERIFICATION_STAGE_MISSING = "FAIL_AUTHORITY_VERIFICATION_STAGE_MISSING"
FAIL_QUEUE_ITEM_MISSING = "FAIL_QUEUE_ITEM_MISSING"
FAIL_WSP15_ALLOCATION_MISSING = "FAIL_WSP15_ALLOCATION_MISSING"


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


def _queue_item(snapshot: Mapping[str, Any], queue_item_id: str | None) -> Mapping[str, Any]:
    items = snapshot.get("wre_queue_items")
    if not isinstance(items, list):
        return {}
    for item in items:
        candidate = _mapping(item)
        if str(candidate.get("queue_item_id") or "") == str(queue_item_id or ""):
            return candidate
    return {}


def _reject(*reasons: str) -> dict[str, Any]:
    return {
        "accepted": False,
        "decision": SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_REJECT,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "receipt": None,
        "explicit_signed_authority_worker_dispatch_dryrun_requested": False,
        "no_worker_spawn_performed": True,
        "no_queue_mutation_performed": True,
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
class ResidentQueueWorkerDispatchDryRunStageHandler:
    """Callable handler for the resident queue `worker_dispatch_dryrun` stage."""

    work_state_snapshot: Mapping[str, Any]
    chain_results_store: ResidentQueueChainResultsStore

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != WORKER_DISPATCH_DRYRUN_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{WORKER_DISPATCH_DRYRUN_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_WORKER_DISPATCH_DRYRUN:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_WORKER_DISPATCH_DRYRUN}",
                f"actual:{request.next_action}",
            )

        stage_results = _stage_results(_mapping(self.chain_results_store.load()))
        authority_runtime = _mapping(stage_results.get(AUTHORITY_RUNTIME_STAGE_KEY))
        if not authority_runtime:
            return _reject(FAIL_AUTHORITY_RUNTIME_STAGE_MISSING)
        authority_verification = _mapping(stage_results.get(AUTHORITY_VERIFICATION_STAGE_KEY))
        if not authority_verification:
            return _reject(FAIL_AUTHORITY_VERIFICATION_STAGE_MISSING)

        queue_item = _queue_item(_mapping(self.work_state_snapshot), request.queue_item_id)
        if not queue_item:
            return _reject(FAIL_QUEUE_ITEM_MISSING, f"queue_item_id:{request.queue_item_id}")
        allocation = _mapping(queue_item.get("wsp15_allocation_receipt"))
        if not allocation:
            return _reject(FAIL_WSP15_ALLOCATION_MISSING, f"queue_item_id:{request.queue_item_id}")

        return plan_reddog_signed_authority_worker_dispatch_dry_run(
            explicit_signed_authority_worker_dispatch_dryrun_requested=True,
            queue_authority_verification_result=authority_verification,
            queue_authority_runtime_result=authority_runtime,
            wsp15_allocation_receipt=allocation,
        ).to_dict()


def build_reddog_resident_queue_worker_dispatch_dryrun_stage_handler(
    *,
    work_state_snapshot: Mapping[str, Any],
    chain_results_store: ResidentQueueChainResultsStore,
) -> ResidentQueueWorkerDispatchDryRunStageHandler:
    """Build the injected worker-dispatch dry-run handler."""

    return ResidentQueueWorkerDispatchDryRunStageHandler(
        work_state_snapshot=work_state_snapshot,
        chain_results_store=chain_results_store,
    )


__all__ = [
    "AUTHORITY_RUNTIME_STAGE_KEY",
    "AUTHORITY_VERIFICATION_STAGE_KEY",
    "FAIL_AUTHORITY_RUNTIME_STAGE_MISSING",
    "FAIL_AUTHORITY_VERIFICATION_STAGE_MISSING",
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "FAIL_QUEUE_ITEM_MISSING",
    "FAIL_WSP15_ALLOCATION_MISSING",
    "ResidentQueueWorkerDispatchDryRunStageHandler",
    "WORKER_DISPATCH_DRYRUN_STAGE_KEY",
    "build_reddog_resident_queue_worker_dispatch_dryrun_stage_handler",
]
