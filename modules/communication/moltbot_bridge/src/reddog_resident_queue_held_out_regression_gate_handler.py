"""Resident RedDog held-out regression gate stage handler.

Slice: REDDOG_RESIDENT_QUEUE_HELD_OUT_REGRESSION_GATE_HANDLER_PHASE1

This module adapts the existing queue-authorized held-out regression gate
explicit invoke guard to the resident queue next-stage dispatcher. It reads the
recorded `verified_outcome_ratchet` stage result from the chain-results store
and invokes the existing held-out gate with injected gate evidence.

It emits only a deterministic held-out gate result. It does not run tests, run
commands, publish PRs, merge, write PatternMemory, enqueue OpenClaw, dispatch
Hermes, settle rewards, or re-index HoloIndex.
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
    NEXT_QUEUE_HELD_OUT_REGRESSION_GATE_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_held_out_regression_gate_invoke import (
    QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_REJECT,
    invoke_reddog_wre_queue_authorized_held_out_regression_gate,
)


HELD_OUT_REGRESSION_GATE_STAGE_KEY = "held_out_regression_gate"
VERIFIED_OUTCOME_RATCHET_STAGE_KEY = "verified_outcome_ratchet"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_VERIFIED_OUTCOME_RATCHET_STAGE_MISSING = "FAIL_VERIFIED_OUTCOME_RATCHET_STAGE_MISSING"
FAIL_HELD_OUT_GATE_REQUEST_MISSING = "FAIL_HELD_OUT_GATE_REQUEST_MISSING"


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
        "decision": QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_REJECT,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "gate_result": None,
        "explicit_queue_authorized_held_out_regression_gate_requested": False,
        "no_command_execution_performed": True,
        "no_test_execution_performed": True,
        "no_pattern_memory_write_performed": True,
        "no_pr_publish_performed": True,
        "no_merge_performed": True,
        "no_reward_settlement_performed": True,
        "no_holoindex_reindex_performed": True,
    }


@dataclass(frozen=True)
class ResidentQueueHeldOutRegressionGateStageHandler:
    """Callable handler for the resident queue `held_out_regression_gate` stage."""

    chain_results_store: ResidentQueueChainResultsStore
    held_out_gate_request: Mapping[str, Any]

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != HELD_OUT_REGRESSION_GATE_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{HELD_OUT_REGRESSION_GATE_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_HELD_OUT_REGRESSION_GATE_INVOKE:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_HELD_OUT_REGRESSION_GATE_INVOKE}",
                f"actual:{request.next_action}",
            )

        stage_results = _stage_results(_mapping(self.chain_results_store.load()))
        outcome_ratchet = _mapping(stage_results.get(VERIFIED_OUTCOME_RATCHET_STAGE_KEY))
        if not outcome_ratchet:
            return _reject(FAIL_VERIFIED_OUTCOME_RATCHET_STAGE_MISSING)

        gate_request = _mapping(self.held_out_gate_request)
        if not gate_request:
            return _reject(FAIL_HELD_OUT_GATE_REQUEST_MISSING)

        return invoke_reddog_wre_queue_authorized_held_out_regression_gate(
            explicit_queue_authorized_held_out_regression_gate_requested=True,
            queue_verified_outcome_ratchet_result=outcome_ratchet,
            held_out_gate_request=gate_request,
        ).to_dict()


def build_reddog_resident_queue_held_out_regression_gate_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    held_out_gate_request: Mapping[str, Any],
) -> ResidentQueueHeldOutRegressionGateStageHandler:
    """Build the injected held-out-regression-gate handler for the dispatcher."""

    return ResidentQueueHeldOutRegressionGateStageHandler(
        chain_results_store=chain_results_store,
        held_out_gate_request=held_out_gate_request,
    )


__all__ = [
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "FAIL_HELD_OUT_GATE_REQUEST_MISSING",
    "FAIL_VERIFIED_OUTCOME_RATCHET_STAGE_MISSING",
    "HELD_OUT_REGRESSION_GATE_STAGE_KEY",
    "ResidentQueueHeldOutRegressionGateStageHandler",
    "VERIFIED_OUTCOME_RATCHET_STAGE_KEY",
    "build_reddog_resident_queue_held_out_regression_gate_stage_handler",
]
