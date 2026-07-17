"""Resident RedDog model-feedback ledger admission stage handler.

Slice: REDDOG_RESIDENT_QUEUE_MODEL_FEEDBACK_LEDGER_ADMISSION_STAGE_PHASE1

This module adapts the queue-authorized model-feedback ledger admission invoke
guard to the resident queue next-stage dispatcher. It reads the recorded
`verified_outcome_ratchet` stage result from the chain-results store. If that
stage emitted a model-selection outcome receipt, an injected feedback ledger
store is required and the receipt is admitted through the queue-authorized
guard. If no model outcome receipt exists, this stage records an accepted no-op
so existing non-model-feedback queue chains can continue.

It does not call providers, run benchmarks, promote models, run commands,
publish PRs, merge, write PatternMemory, enqueue OpenClaw, dispatch Hermes,
settle rewards, or re-index HoloIndex.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from modules.ai_intelligence.ai_gateway.src.model_feedback_ledger import (
    ModelFeedbackLedgerStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_model_feedback_ledger_admission_invoke import (
    QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT,
    invoke_reddog_wre_queue_authorized_model_feedback_ledger_admission,
)


MODEL_FEEDBACK_ADMISSION_STAGE_KEY = "model_feedback_admission"
VERIFIED_OUTCOME_RATCHET_STAGE_KEY = "verified_outcome_ratchet"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_VERIFIED_OUTCOME_RATCHET_STAGE_MISSING = "FAIL_VERIFIED_OUTCOME_RATCHET_STAGE_MISSING"
FAIL_MODEL_FEEDBACK_LEDGER_STORE_MISSING = "FAIL_MODEL_FEEDBACK_LEDGER_STORE_MISSING"


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
        "decision": QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "model_feedback_admission_result": None,
        "explicit_queue_authorized_model_feedback_ledger_admission_requested": False,
        "model_feedback_write_performed": False,
        "no_provider_call_performed": True,
        "no_benchmark_execution_performed": True,
        "no_model_promotion_performed": True,
        "no_command_execution_performed": True,
        "no_pr_publish_performed": True,
        "no_merge_performed": True,
        "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
        "no_holoindex_reindex_performed": True,
    }


def _accept_noop() -> dict[str, Any]:
    return {
        "decision": QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_ACCEPT,
        "rejection_reasons": [],
        "model_feedback_admission_result": None,
        "explicit_queue_authorized_model_feedback_ledger_admission_requested": True,
        "model_feedback_write_performed": False,
        "model_feedback_noop_reason": "no_model_selection_outcome_receipt",
        "no_provider_call_performed": True,
        "no_benchmark_execution_performed": True,
        "no_model_promotion_performed": True,
        "no_command_execution_performed": True,
        "no_pr_publish_performed": True,
        "no_merge_performed": True,
        "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
        "no_holoindex_reindex_performed": True,
    }


@dataclass(frozen=True)
class ResidentQueueModelFeedbackLedgerAdmissionStageHandler:
    """Callable handler for the resident queue `model_feedback_admission` stage."""

    chain_results_store: ResidentQueueChainResultsStore
    store: Optional[ModelFeedbackLedgerStore]

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != MODEL_FEEDBACK_ADMISSION_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{MODEL_FEEDBACK_ADMISSION_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE}",
                f"actual:{request.next_action}",
            )

        stage_results = _stage_results(_mapping(self.chain_results_store.load()))
        queue_ratchet = _mapping(stage_results.get(VERIFIED_OUTCOME_RATCHET_STAGE_KEY))
        if not queue_ratchet:
            return _reject(FAIL_VERIFIED_OUTCOME_RATCHET_STAGE_MISSING)

        if not _mapping(queue_ratchet.get("model_selection_outcome_receipt")):
            return _accept_noop()
        if self.store is None:
            return _reject(FAIL_MODEL_FEEDBACK_LEDGER_STORE_MISSING)

        return invoke_reddog_wre_queue_authorized_model_feedback_ledger_admission(
            explicit_queue_authorized_model_feedback_ledger_admission_requested=True,
            queue_verified_outcome_ratchet_result=queue_ratchet,
            store=self.store,
        ).to_dict()


def build_reddog_resident_queue_model_feedback_ledger_admission_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    store: Optional[ModelFeedbackLedgerStore],
) -> ResidentQueueModelFeedbackLedgerAdmissionStageHandler:
    """Build the injected model-feedback admission handler for the dispatcher."""

    return ResidentQueueModelFeedbackLedgerAdmissionStageHandler(
        chain_results_store=chain_results_store,
        store=store,
    )


__all__ = [
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "FAIL_MODEL_FEEDBACK_LEDGER_STORE_MISSING",
    "FAIL_VERIFIED_OUTCOME_RATCHET_STAGE_MISSING",
    "MODEL_FEEDBACK_ADMISSION_STAGE_KEY",
    "ResidentQueueModelFeedbackLedgerAdmissionStageHandler",
    "VERIFIED_OUTCOME_RATCHET_STAGE_KEY",
    "build_reddog_resident_queue_model_feedback_ledger_admission_stage_handler",
]
