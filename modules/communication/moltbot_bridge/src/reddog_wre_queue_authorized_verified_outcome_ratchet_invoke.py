"""RedDog queue-authorized verified outcome ratchet explicit invoke guard.

Slice: REDDOG_WRE_QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_PHASE1

This module consumes an accepted queue-authorized verified draft PR publish
result, then invokes the existing WRE verified outcome ratchet through an
injected store. It records outcome receipts only; it never executes commands,
publishes PRs, marks ready, merges, settles rewards, or mutates HoloIndex.
PatternMemory writes require a separate explicit flag and injected sink.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_draft_pr_publish_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT,
)
from modules.infrastructure.wre_core.src.reddog_verified_draft_pr_publish import (
    VERIFIED_DRAFT_PR_PUBLISH_ACCEPT,
)
from modules.infrastructure.wre_core.src.reddog_verified_outcome_ratchet import (
    OUTCOME_RATCHET_RECORDED,
    OutcomeRatchetStore,
    PatternMemorySink,
    VerifiedOutcomeRatchetResult,
    ratchet_verified_outcome,
)


QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT = (
    "QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT"
)
QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT = (
    "QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT"
)


class QueueAuthorizedVerifiedOutcomeRatchetInvokeReason:
    EXPLICIT_INVOKE_MISSING = "REJECT_EXPLICIT_QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_MISSING"
    STORE_REQUIRED = "REJECT_INJECTED_OUTCOME_RATCHET_STORE_REQUIRED"
    PUBLISH_INVOKE_NOT_ACCEPTED = "REJECT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_NOT_ACCEPTED"
    PUBLISH_PAYLOAD_MISSING = "REJECT_PUBLISH_PAYLOAD_MISSING"
    PUBLISH_PAYLOAD_NOT_ACCEPTED = "REJECT_PUBLISH_PAYLOAD_NOT_ACCEPTED"
    PUBLISH_RECEIPT_MISSING = "REJECT_PUBLISH_RECEIPT_MISSING"
    RATCHET_REQUEST_INVALID = "REJECT_OUTCOME_RATCHET_REQUEST_INVALID"
    VERIFIER_RECEIPT_MISMATCH = "REJECT_VERIFIER_RECEIPT_MISMATCH"
    WORK_ORDER_ID_MISMATCH = "REJECT_WORK_ORDER_ID_MISMATCH"
    PATTERN_MEMORY_EXPLICIT_MISSING = "REJECT_PATTERN_MEMORY_EXPLICIT_MISSING"
    PATTERN_MEMORY_SINK_REQUIRED = "REJECT_PATTERN_MEMORY_SINK_REQUIRED"
    RATCHET_NOT_ACCEPTED = "REJECT_VERIFIED_OUTCOME_RATCHET_NOT_ACCEPTED"


@dataclass(frozen=True)
class QueueAuthorizedVerifiedOutcomeRatchetInvokeResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    ratchet_result: Optional[VerifiedOutcomeRatchetResult] = None
    explicit_queue_authorized_verified_outcome_ratchet_requested: bool = False
    explicit_pattern_memory_write_requested: bool = False
    no_command_execution_performed: bool = True
    no_pr_publish_performed: bool = True
    no_ready_performed: bool = True
    no_merge_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["ratchet_result"] = self.ratchet_result.to_dict() if self.ratchet_result else None
        return payload


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _dedupe(values: Sequence[str]) -> List[str]:
    return list(dict.fromkeys(str(v) for v in values if str(v or "").strip()))


def _reject(
    reasons: Sequence[str],
    *,
    explicit_requested: bool,
    explicit_pattern_requested: bool,
    ratchet_result: Optional[VerifiedOutcomeRatchetResult] = None,
) -> QueueAuthorizedVerifiedOutcomeRatchetInvokeResult:
    return QueueAuthorizedVerifiedOutcomeRatchetInvokeResult(
        decision=QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT,
        rejection_reasons=_dedupe(reasons),
        ratchet_result=ratchet_result,
        explicit_queue_authorized_verified_outcome_ratchet_requested=explicit_requested,
        explicit_pattern_memory_write_requested=explicit_pattern_requested,
    )


def _same_nonempty(left: Any, right: Any) -> bool:
    left_text = str(left or "")
    return bool(left_text) and left_text == str(right or "")


def _enrich_ratchet_request(
    ratchet_request: Mapping[str, Any],
    publish_result: Mapping[str, Any],
    *,
    enable_pattern_memory_write: bool,
) -> Dict[str, Any]:
    enriched = dict(ratchet_request)
    enriched["publish_result"] = dict(publish_result)
    enriched["enable_pattern_memory_write"] = enable_pattern_memory_write
    return enriched


def invoke_reddog_wre_queue_authorized_verified_outcome_ratchet(
    *,
    explicit_queue_authorized_verified_outcome_ratchet_requested: bool,
    queue_verified_draft_pr_publish_result: Mapping[str, Any],
    ratchet_request: Mapping[str, Any],
    store: Optional[OutcomeRatchetStore],
    explicit_pattern_memory_write_requested: bool = False,
    pattern_memory_sink: Optional[PatternMemorySink] = None,
) -> QueueAuthorizedVerifiedOutcomeRatchetInvokeResult:
    """Record a verified outcome only after queue-authorized draft PR publish."""

    if explicit_queue_authorized_verified_outcome_ratchet_requested is not True:
        return _reject(
            [QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.EXPLICIT_INVOKE_MISSING],
            explicit_requested=False,
            explicit_pattern_requested=explicit_pattern_memory_write_requested,
        )
    if store is None:
        return _reject(
            [QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.STORE_REQUIRED],
            explicit_requested=True,
            explicit_pattern_requested=explicit_pattern_memory_write_requested,
        )

    reasons: List[str] = []
    publish_invoke = _mapping(queue_verified_draft_pr_publish_result)
    if (
        publish_invoke.get("decision")
        != QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT
    ):
        reasons.append(
            QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.PUBLISH_INVOKE_NOT_ACCEPTED
        )

    publish_payload = _mapping(publish_invoke.get("publish_result"))
    if not publish_payload:
        reasons.append(QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.PUBLISH_PAYLOAD_MISSING)
    elif (
        publish_payload.get("decision") != VERIFIED_DRAFT_PR_PUBLISH_ACCEPT
        or publish_payload.get("accepted") is not True
    ):
        reasons.append(QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.PUBLISH_PAYLOAD_NOT_ACCEPTED)

    publish_receipt = _mapping(publish_payload.get("receipt"))
    if not publish_receipt:
        reasons.append(QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.PUBLISH_RECEIPT_MISSING)

    request = _mapping(ratchet_request)
    if not request:
        reasons.append(QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.RATCHET_REQUEST_INVALID)

    verifier_result = _mapping(request.get("verification_result"))
    verifier_receipt = _mapping(verifier_result.get("receipt"))
    if publish_receipt and verifier_receipt:
        if not _same_nonempty(
            verifier_receipt.get("receipt_id"),
            publish_receipt.get("verifier_receipt_id"),
        ):
            reasons.append(QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.VERIFIER_RECEIPT_MISMATCH)
        if not _same_nonempty(
            request.get("work_order_id") or verifier_receipt.get("work_order_id"),
            publish_receipt.get("work_order_id"),
        ):
            reasons.append(QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.WORK_ORDER_ID_MISMATCH)
    elif publish_receipt and request:
        reasons.append(QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.VERIFIER_RECEIPT_MISMATCH)

    pattern_requested_by_request = request.get("enable_pattern_memory_write") is True
    if pattern_requested_by_request and explicit_pattern_memory_write_requested is not True:
        reasons.append(QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.PATTERN_MEMORY_EXPLICIT_MISSING)
    if (
        pattern_requested_by_request
        and explicit_pattern_memory_write_requested is True
        and pattern_memory_sink is None
    ):
        reasons.append(QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.PATTERN_MEMORY_SINK_REQUIRED)

    if reasons:
        return _reject(
            reasons,
            explicit_requested=True,
            explicit_pattern_requested=explicit_pattern_memory_write_requested,
        )

    ratcheted = ratchet_verified_outcome(
        _enrich_ratchet_request(
            request,
            publish_payload,
            enable_pattern_memory_write=pattern_requested_by_request,
        ),
        store=store,
        pattern_memory_sink=pattern_memory_sink,
    )
    if ratcheted.decision != OUTCOME_RATCHET_RECORDED or ratcheted.accepted is not True:
        return _reject(
            [
                QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.RATCHET_NOT_ACCEPTED,
                *ratcheted.rejection_reasons,
            ],
            explicit_requested=True,
            explicit_pattern_requested=explicit_pattern_memory_write_requested,
            ratchet_result=ratcheted,
        )

    return QueueAuthorizedVerifiedOutcomeRatchetInvokeResult(
        decision=QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT,
        rejection_reasons=[],
        ratchet_result=ratcheted,
        explicit_queue_authorized_verified_outcome_ratchet_requested=True,
        explicit_pattern_memory_write_requested=explicit_pattern_memory_write_requested,
    )


__all__ = [
    "QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT",
    "QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT",
    "QueueAuthorizedVerifiedOutcomeRatchetInvokeReason",
    "QueueAuthorizedVerifiedOutcomeRatchetInvokeResult",
    "invoke_reddog_wre_queue_authorized_verified_outcome_ratchet",
]
