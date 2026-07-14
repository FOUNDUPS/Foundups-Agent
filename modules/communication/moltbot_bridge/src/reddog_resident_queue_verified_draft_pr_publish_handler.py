"""Resident RedDog verified draft-PR publish stage handler.

Slice: REDDOG_RESIDENT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_HANDLER_PHASE1

This module adapts the existing queue-authorized verified draft-PR publish
explicit invoke guard to the resident queue next-stage dispatcher. It reads the
recorded `slice_verifier` stage result from the chain-results store and invokes
the existing publish guard with an injected publish request and injected runner.

It can only use the injected runner through the lower verified draft-PR publish
gate. It does not mark PRs ready, merge, run commands, enqueue OpenClaw,
dispatch Hermes, write PatternMemory, settle rewards, or re-index HoloIndex.
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
    NEXT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_draft_pr_publish_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT,
    invoke_reddog_wre_queue_authorized_verified_draft_pr_publish,
)


VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY = "verified_draft_pr_publish"
SLICE_VERIFIER_STAGE_KEY = "slice_verifier"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_SLICE_VERIFIER_STAGE_MISSING = "FAIL_SLICE_VERIFIER_STAGE_MISSING"
FAIL_PUBLISH_REQUEST_MISSING = "FAIL_PUBLISH_REQUEST_MISSING"
FAIL_DRAFT_PR_RUNNER_MISSING = "FAIL_DRAFT_PR_RUNNER_MISSING"


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
        "decision": QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "publish_result": None,
        "explicit_queue_authorized_verified_draft_pr_publish_requested": False,
        "no_ready_performed": True,
        "no_merge_performed": True,
        "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
        "no_holoindex_reindex_performed": True,
    }


@dataclass(frozen=True)
class ResidentQueueVerifiedDraftPrPublishStageHandler:
    """Callable handler for the resident queue `verified_draft_pr_publish` stage."""

    chain_results_store: ResidentQueueChainResultsStore
    publish_request: Mapping[str, Any]
    runner: Optional[Any]

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_INVOKE:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_INVOKE}",
                f"actual:{request.next_action}",
            )

        stage_results = _stage_results(_mapping(self.chain_results_store.load()))
        slice_verifier = _mapping(stage_results.get(SLICE_VERIFIER_STAGE_KEY))
        if not slice_verifier:
            return _reject(FAIL_SLICE_VERIFIER_STAGE_MISSING)

        publish_request = _mapping(self.publish_request)
        if not publish_request:
            return _reject(FAIL_PUBLISH_REQUEST_MISSING)
        if self.runner is None:
            return _reject(FAIL_DRAFT_PR_RUNNER_MISSING)

        return invoke_reddog_wre_queue_authorized_verified_draft_pr_publish(
            explicit_queue_authorized_verified_draft_pr_publish_requested=True,
            queue_slice_verifier_result=slice_verifier,
            publish_request=publish_request,
            runner=self.runner,
        ).to_dict()


def build_reddog_resident_queue_verified_draft_pr_publish_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    publish_request: Mapping[str, Any],
    runner: Optional[Any],
) -> ResidentQueueVerifiedDraftPrPublishStageHandler:
    """Build the injected verified-draft-PR-publish handler for the dispatcher."""

    return ResidentQueueVerifiedDraftPrPublishStageHandler(
        chain_results_store=chain_results_store,
        publish_request=publish_request,
        runner=runner,
    )


__all__ = [
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "FAIL_DRAFT_PR_RUNNER_MISSING",
    "FAIL_PUBLISH_REQUEST_MISSING",
    "FAIL_SLICE_VERIFIER_STAGE_MISSING",
    "ResidentQueueVerifiedDraftPrPublishStageHandler",
    "SLICE_VERIFIER_STAGE_KEY",
    "VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY",
    "build_reddog_resident_queue_verified_draft_pr_publish_stage_handler",
]
