"""Resident RedDog PatternMemory admission stage handler.

Slice: REDDOG_RESIDENT_QUEUE_PATTERN_MEMORY_ADMISSION_HANDLER_PHASE1

This module adapts the existing queue-authorized PatternMemory admission
explicit invoke guard to the resident queue next-stage dispatcher. It reads the
recorded `held_out_regression_gate` stage result from the chain-results store
and invokes the existing admission guard with an injected admission request and
sink.

It writes only through the injected sink after held-out regression acceptance.
It does not instantiate PatternMemory, run commands, publish PRs, merge, settle
rewards, enqueue OpenClaw, dispatch Hermes, or re-index HoloIndex.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_pattern_memory_admission_invoke import (
    PatternMemoryAdmissionSink,
    QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT,
    invoke_reddog_wre_queue_authorized_pattern_memory_admission,
)


PATTERN_MEMORY_ADMISSION_STAGE_KEY = "pattern_memory_admission"
HELD_OUT_REGRESSION_GATE_STAGE_KEY = "held_out_regression_gate"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_HELD_OUT_REGRESSION_GATE_STAGE_MISSING = "FAIL_HELD_OUT_REGRESSION_GATE_STAGE_MISSING"
FAIL_ADMISSION_REQUEST_MISSING = "FAIL_ADMISSION_REQUEST_MISSING"
FAIL_PATTERN_MEMORY_SINK_MISSING = "FAIL_PATTERN_MEMORY_SINK_MISSING"


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
        "decision": QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "receipt": None,
        "explicit_queue_authorized_pattern_memory_admission_requested": False,
        "pattern_memory_write_performed": False,
        "no_command_execution_performed": True,
        "no_pr_publish_performed": True,
        "no_merge_performed": True,
        "no_reward_settlement_performed": True,
        "no_holoindex_reindex_performed": True,
    }


@dataclass(frozen=True)
class ResidentQueuePatternMemoryAdmissionStageHandler:
    """Callable handler for the resident queue `pattern_memory_admission` stage."""

    chain_results_store: ResidentQueueChainResultsStore
    admission_request: Mapping[str, Any]
    sink: Optional[PatternMemoryAdmissionSink]

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != PATTERN_MEMORY_ADMISSION_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{PATTERN_MEMORY_ADMISSION_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE}",
                f"actual:{request.next_action}",
            )

        stage_results = _stage_results(_mapping(self.chain_results_store.load()))
        held_out_gate = _mapping(stage_results.get(HELD_OUT_REGRESSION_GATE_STAGE_KEY))
        if not held_out_gate:
            return _reject(FAIL_HELD_OUT_REGRESSION_GATE_STAGE_MISSING)

        admission_request = _mapping(self.admission_request)
        if not admission_request:
            return _reject(FAIL_ADMISSION_REQUEST_MISSING)
        if self.sink is None:
            return _reject(FAIL_PATTERN_MEMORY_SINK_MISSING)

        return invoke_reddog_wre_queue_authorized_pattern_memory_admission(
            explicit_queue_authorized_pattern_memory_admission_requested=True,
            queue_held_out_gate_result=held_out_gate,
            admission_request=admission_request,
            sink=self.sink,
        ).to_dict()


def build_reddog_resident_queue_pattern_memory_admission_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    admission_request: Mapping[str, Any],
    sink: Optional[PatternMemoryAdmissionSink],
) -> ResidentQueuePatternMemoryAdmissionStageHandler:
    """Build the injected PatternMemory admission handler for the dispatcher."""

    return ResidentQueuePatternMemoryAdmissionStageHandler(
        chain_results_store=chain_results_store,
        admission_request=admission_request,
        sink=sink,
    )


__all__ = [
    "FAIL_ADMISSION_REQUEST_MISSING",
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "FAIL_HELD_OUT_REGRESSION_GATE_STAGE_MISSING",
    "FAIL_PATTERN_MEMORY_SINK_MISSING",
    "HELD_OUT_REGRESSION_GATE_STAGE_KEY",
    "PATTERN_MEMORY_ADMISSION_STAGE_KEY",
    "ResidentQueuePatternMemoryAdmissionStageHandler",
    "build_reddog_resident_queue_pattern_memory_admission_stage_handler",
]
