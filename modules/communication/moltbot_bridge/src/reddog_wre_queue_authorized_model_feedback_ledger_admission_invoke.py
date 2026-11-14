"""RedDog queue-authorized model-feedback ledger admission invoke guard.

Slice: REDDOG_WRE_QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_PHASE1

This module consumes an accepted queue-authorized verified-outcome ratchet
result that emitted a model-selection outcome receipt, then admits that receipt
through an injected model-feedback ledger store. It does not call providers, run
benchmarks, promote models, execute commands, write PatternMemory, mutate
HoloIndex, publish PRs, merge, or settle rewards.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from modules.ai_intelligence.ai_gateway.src.model_feedback_ledger import (
    MODEL_FEEDBACK_LEDGER_ADMISSION_ACCEPT,
    MODEL_FEEDBACK_LEDGER_ADMISSION_REJECT,
    ModelFeedbackLedgerStore,
    admit_model_selection_outcome_feedback,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_outcome_ratchet_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT,
)
from modules.infrastructure.wre_core.src.reddog_verified_outcome_ratchet import (
    OUTCOME_RATCHET_RECORDED,
)


QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_ACCEPT = (
    "QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_ACCEPT"
)
QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT = (
    "QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT"
)


class QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason:
    EXPLICIT_INVOKE_MISSING = "REJECT_EXPLICIT_QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_MISSING"
    STORE_REQUIRED = "REJECT_INJECTED_MODEL_FEEDBACK_LEDGER_STORE_REQUIRED"
    OUTCOME_RATCHET_INVOKE_NOT_ACCEPTED = "REJECT_QUEUE_VERIFIED_OUTCOME_RATCHET_INVOKE_NOT_ACCEPTED"
    RATCHET_PAYLOAD_MISSING = "REJECT_VERIFIED_OUTCOME_RATCHET_PAYLOAD_MISSING"
    RATCHET_PAYLOAD_NOT_ACCEPTED = "REJECT_VERIFIED_OUTCOME_RATCHET_PAYLOAD_NOT_ACCEPTED"
    RATCHET_RECEIPT_MISSING = "REJECT_VERIFIED_OUTCOME_RATCHET_RECEIPT_MISSING"
    MODEL_OUTCOME_RECEIPT_MISSING = "REJECT_MODEL_SELECTION_OUTCOME_RECEIPT_MISSING"
    ADMISSION_NOT_ACCEPTED = "REJECT_MODEL_FEEDBACK_LEDGER_ADMISSION_NOT_ACCEPTED"


@dataclass(frozen=True)
class QueueAuthorizedModelFeedbackLedgerAdmissionInvokeResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    model_feedback_admission_result: Optional[Dict[str, Any]] = None
    explicit_queue_authorized_model_feedback_ledger_admission_requested: bool = False
    model_feedback_write_performed: bool = False
    no_provider_call_performed: bool = True
    no_benchmark_execution_performed: bool = True
    no_model_promotion_performed: bool = True
    no_command_execution_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _dedupe(values: Sequence[str]) -> List[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value or "").strip()))


def _reject(
    reasons: Sequence[str],
    *,
    explicit_requested: bool,
    admission_result: Optional[Mapping[str, Any]] = None,
) -> QueueAuthorizedModelFeedbackLedgerAdmissionInvokeResult:
    return QueueAuthorizedModelFeedbackLedgerAdmissionInvokeResult(
        decision=QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT,
        rejection_reasons=_dedupe(reasons),
        model_feedback_admission_result=dict(admission_result) if admission_result else None,
        explicit_queue_authorized_model_feedback_ledger_admission_requested=explicit_requested,
        model_feedback_write_performed=False,
    )


def invoke_reddog_wre_queue_authorized_model_feedback_ledger_admission(
    *,
    explicit_queue_authorized_model_feedback_ledger_admission_requested: bool,
    queue_verified_outcome_ratchet_result: Mapping[str, Any],
    store: Optional[ModelFeedbackLedgerStore],
) -> QueueAuthorizedModelFeedbackLedgerAdmissionInvokeResult:
    """Admit a model-selection outcome receipt after accepted queue ratchet."""

    if explicit_queue_authorized_model_feedback_ledger_admission_requested is not True:
        return _reject(
            [QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason.EXPLICIT_INVOKE_MISSING],
            explicit_requested=False,
        )
    if store is None:
        return _reject(
            [QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason.STORE_REQUIRED],
            explicit_requested=True,
        )

    reasons: List[str] = []
    queue_ratchet = _mapping(queue_verified_outcome_ratchet_result)
    if queue_ratchet.get("decision") != QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT:
        reasons.append(
            QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason.OUTCOME_RATCHET_INVOKE_NOT_ACCEPTED
        )

    ratchet_payload = _mapping(queue_ratchet.get("ratchet_result"))
    if not ratchet_payload:
        reasons.append(QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason.RATCHET_PAYLOAD_MISSING)
    elif (
        ratchet_payload.get("decision") != OUTCOME_RATCHET_RECORDED
        or ratchet_payload.get("accepted") is not True
    ):
        reasons.append(QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason.RATCHET_PAYLOAD_NOT_ACCEPTED)

    ratchet_receipt = _mapping(ratchet_payload.get("receipt"))
    if not ratchet_receipt:
        reasons.append(QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason.RATCHET_RECEIPT_MISSING)

    model_outcome_receipt = _mapping(queue_ratchet.get("model_selection_outcome_receipt"))
    if not model_outcome_receipt:
        reasons.append(QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason.MODEL_OUTCOME_RECEIPT_MISSING)

    if reasons:
        return _reject(reasons, explicit_requested=True)

    admission = admit_model_selection_outcome_feedback(
        explicit_model_feedback_ledger_admission_requested=True,
        model_selection_outcome_receipt=model_outcome_receipt,
        source_ratchet_receipt=ratchet_receipt,
        store=store,
    )
    admission_payload = admission.to_dict()
    if admission.decision != MODEL_FEEDBACK_LEDGER_ADMISSION_ACCEPT:
        return _reject(
            [
                QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason.ADMISSION_NOT_ACCEPTED,
                *admission.rejection_reasons,
            ],
            explicit_requested=True,
            admission_result=admission_payload,
        )

    return QueueAuthorizedModelFeedbackLedgerAdmissionInvokeResult(
        decision=QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_ACCEPT,
        rejection_reasons=[],
        model_feedback_admission_result=admission_payload,
        explicit_queue_authorized_model_feedback_ledger_admission_requested=True,
        model_feedback_write_performed=admission.feedback_write_performed,
    )


__all__ = [
    "QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_ACCEPT",
    "QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT",
    "QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason",
    "QueueAuthorizedModelFeedbackLedgerAdmissionInvokeResult",
    "invoke_reddog_wre_queue_authorized_model_feedback_ledger_admission",
]
