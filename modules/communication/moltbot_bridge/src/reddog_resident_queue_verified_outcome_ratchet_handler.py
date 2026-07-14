"""Resident RedDog verified outcome-ratchet stage handler.

Slice: REDDOG_RESIDENT_QUEUE_VERIFIED_OUTCOME_RATCHET_HANDLER_PHASE1

This module adapts the existing queue-authorized verified outcome ratchet
explicit invoke guard to the resident queue next-stage dispatcher. It reads the
recorded `verified_draft_pr_publish` stage result from the chain-results store
and invokes the existing ratchet guard with an injected ratchet request and
store.

It records verified outcome receipts only. It does not run commands, publish
PRs, mark ready, merge, settle rewards, enqueue OpenClaw, dispatch Hermes, or
re-index HoloIndex. PatternMemory admission remains disabled unless a caller
provides a separate explicit flag and injected sink.
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
    NEXT_QUEUE_VERIFIED_OUTCOME_RATCHET_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_outcome_ratchet_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT,
    invoke_reddog_wre_queue_authorized_verified_outcome_ratchet,
)
from modules.infrastructure.wre_core.src.reddog_verified_outcome_ratchet import (
    OutcomeRatchetStore,
    PatternMemorySink,
)


VERIFIED_OUTCOME_RATCHET_STAGE_KEY = "verified_outcome_ratchet"
VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY = "verified_draft_pr_publish"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_VERIFIED_DRAFT_PR_PUBLISH_STAGE_MISSING = "FAIL_VERIFIED_DRAFT_PR_PUBLISH_STAGE_MISSING"
FAIL_RATCHET_REQUEST_MISSING = "FAIL_RATCHET_REQUEST_MISSING"
FAIL_RATCHET_STORE_MISSING = "FAIL_RATCHET_STORE_MISSING"


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
        "decision": QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "ratchet_result": None,
        "explicit_queue_authorized_verified_outcome_ratchet_requested": False,
        "explicit_pattern_memory_write_requested": False,
        "no_command_execution_performed": True,
        "no_pr_publish_performed": True,
        "no_ready_performed": True,
        "no_merge_performed": True,
        "no_reward_settlement_performed": True,
        "no_holoindex_reindex_performed": True,
    }


@dataclass(frozen=True)
class ResidentQueueVerifiedOutcomeRatchetStageHandler:
    """Callable handler for the resident queue `verified_outcome_ratchet` stage."""

    chain_results_store: ResidentQueueChainResultsStore
    ratchet_request: Mapping[str, Any]
    store: Optional[OutcomeRatchetStore]
    explicit_pattern_memory_write_requested: bool = False
    pattern_memory_sink: Optional[PatternMemorySink] = None

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != VERIFIED_OUTCOME_RATCHET_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{VERIFIED_OUTCOME_RATCHET_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_VERIFIED_OUTCOME_RATCHET_INVOKE:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_VERIFIED_OUTCOME_RATCHET_INVOKE}",
                f"actual:{request.next_action}",
            )

        stage_results = _stage_results(_mapping(self.chain_results_store.load()))
        verified_publish = _mapping(stage_results.get(VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY))
        if not verified_publish:
            return _reject(FAIL_VERIFIED_DRAFT_PR_PUBLISH_STAGE_MISSING)

        ratchet_request = _mapping(self.ratchet_request)
        if not ratchet_request:
            return _reject(FAIL_RATCHET_REQUEST_MISSING)
        if self.store is None:
            return _reject(FAIL_RATCHET_STORE_MISSING)

        return invoke_reddog_wre_queue_authorized_verified_outcome_ratchet(
            explicit_queue_authorized_verified_outcome_ratchet_requested=True,
            queue_verified_draft_pr_publish_result=verified_publish,
            ratchet_request=ratchet_request,
            store=self.store,
            explicit_pattern_memory_write_requested=self.explicit_pattern_memory_write_requested,
            pattern_memory_sink=self.pattern_memory_sink,
        ).to_dict()


def build_reddog_resident_queue_verified_outcome_ratchet_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    ratchet_request: Mapping[str, Any],
    store: Optional[OutcomeRatchetStore],
    explicit_pattern_memory_write_requested: bool = False,
    pattern_memory_sink: Optional[PatternMemorySink] = None,
) -> ResidentQueueVerifiedOutcomeRatchetStageHandler:
    """Build the injected verified-outcome-ratchet handler for the dispatcher."""

    return ResidentQueueVerifiedOutcomeRatchetStageHandler(
        chain_results_store=chain_results_store,
        ratchet_request=ratchet_request,
        store=store,
        explicit_pattern_memory_write_requested=explicit_pattern_memory_write_requested,
        pattern_memory_sink=pattern_memory_sink,
    )


__all__ = [
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "FAIL_RATCHET_REQUEST_MISSING",
    "FAIL_RATCHET_STORE_MISSING",
    "FAIL_VERIFIED_DRAFT_PR_PUBLISH_STAGE_MISSING",
    "ResidentQueueVerifiedOutcomeRatchetStageHandler",
    "VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY",
    "VERIFIED_OUTCOME_RATCHET_STAGE_KEY",
    "build_reddog_resident_queue_verified_outcome_ratchet_stage_handler",
]
