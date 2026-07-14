"""Resident RedDog slice-verifier stage handler.

Slice: REDDOG_RESIDENT_QUEUE_SLICE_VERIFIER_HANDLER_PHASE1

This module adapts the existing queue-authorized autonomous slice verifier
explicit invoke guard to the resident queue next-stage dispatcher. It reads the
recorded `bounded_worker_pilot` stage result from the chain-results store and
invokes the existing verifier guard with injected machine-derived verifier
evidence.

It verifies evidence only. It does not run commands, create or update PRs,
merge, enqueue OpenClaw, dispatch Hermes, write PatternMemory, settle rewards,
or re-index HoloIndex.
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
    NEXT_QUEUE_SLICE_VERIFIER_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_slice_verifier_invoke import (
    QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT,
    invoke_reddog_wre_queue_authorized_slice_verifier,
)


SLICE_VERIFIER_STAGE_KEY = "slice_verifier"
BOUNDED_WORKER_PILOT_STAGE_KEY = "bounded_worker_pilot"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_BOUNDED_WORKER_PILOT_STAGE_MISSING = "FAIL_BOUNDED_WORKER_PILOT_STAGE_MISSING"
FAIL_VERIFIER_REQUEST_MISSING = "FAIL_VERIFIER_REQUEST_MISSING"


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


def _reject(*reasons: str) -> dict[str, Any]:
    return {
        "decision": QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "verifier_result": None,
        "explicit_queue_authorized_slice_verifier_requested": False,
        "no_command_execution_performed": True,
        "no_github_call_performed": True,
        "no_pr_publish_performed": True,
        "no_merge_performed": True,
        "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
        "no_holoindex_reindex_performed": True,
    }


@dataclass(frozen=True)
class ResidentQueueSliceVerifierStageHandler:
    """Callable handler for the resident queue `slice_verifier` stage."""

    chain_results_store: ResidentQueueChainResultsStore
    verifier_request: Mapping[str, Any]

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != SLICE_VERIFIER_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{SLICE_VERIFIER_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_SLICE_VERIFIER_INVOKE:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_SLICE_VERIFIER_INVOKE}",
                f"actual:{request.next_action}",
            )

        stage_results = _stage_results(_mapping(self.chain_results_store.load()))
        bounded_worker_pilot = _mapping(stage_results.get(BOUNDED_WORKER_PILOT_STAGE_KEY))
        if not bounded_worker_pilot:
            return _reject(FAIL_BOUNDED_WORKER_PILOT_STAGE_MISSING)

        verifier_request = _mapping(self.verifier_request)
        if not verifier_request:
            return _reject(FAIL_VERIFIER_REQUEST_MISSING)

        return invoke_reddog_wre_queue_authorized_slice_verifier(
            explicit_queue_authorized_slice_verifier_requested=True,
            queue_bounded_worker_pilot_result=bounded_worker_pilot,
            verifier_request=verifier_request,
        ).to_dict()


def build_reddog_resident_queue_slice_verifier_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    verifier_request: Mapping[str, Any],
) -> ResidentQueueSliceVerifierStageHandler:
    """Build the injected slice-verifier handler for the dispatcher."""

    return ResidentQueueSliceVerifierStageHandler(
        chain_results_store=chain_results_store,
        verifier_request=verifier_request,
    )


__all__ = [
    "BOUNDED_WORKER_PILOT_STAGE_KEY",
    "FAIL_BOUNDED_WORKER_PILOT_STAGE_MISSING",
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "FAIL_VERIFIER_REQUEST_MISSING",
    "ResidentQueueSliceVerifierStageHandler",
    "SLICE_VERIFIER_STAGE_KEY",
    "build_reddog_resident_queue_slice_verifier_stage_handler",
]
