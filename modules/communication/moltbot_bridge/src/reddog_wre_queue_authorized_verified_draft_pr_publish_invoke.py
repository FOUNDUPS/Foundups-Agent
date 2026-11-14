"""RedDog queue-authorized verified draft PR publish explicit invoke guard.

Slice: REDDOG_WRE_QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_PHASE1

This module consumes an accepted queue-authorized autonomous slice verifier
result, then invokes the existing WRE verified draft PR publish gate through an
injected runner. It publishes draft PRs only; it never marks ready, merges,
executes commands, writes PatternMemory, settles rewards, or mutates HoloIndex.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_slice_verifier_invoke import (
    QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT,
)
from modules.infrastructure.wre_core.src.reddog_verified_draft_pr_publish import (
    VERIFIED_DRAFT_PR_PUBLISH_ACCEPT,
    VerifiedDraftPrPublishResult,
    publish_verified_draft_pr,
)
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
)


QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT = (
    "QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT"
)
QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT = (
    "QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT"
)


class QueueAuthorizedVerifiedDraftPrPublishInvokeReason:
    EXPLICIT_INVOKE_MISSING = "REJECT_EXPLICIT_QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_MISSING"
    RUNNER_REQUIRED = "REJECT_INJECTED_DRAFT_PR_RUNNER_REQUIRED"
    SLICE_VERIFIER_NOT_ACCEPTED = "REJECT_QUEUE_SLICE_VERIFIER_NOT_ACCEPTED"
    VERIFIER_PAYLOAD_MISSING = "REJECT_VERIFIER_PAYLOAD_MISSING"
    VERIFIER_PAYLOAD_NOT_ACCEPTED = "REJECT_VERIFIER_PAYLOAD_NOT_ACCEPTED"
    VERIFIER_RECEIPT_MISSING = "REJECT_VERIFIER_RECEIPT_MISSING"
    PUBLISH_REQUEST_INVALID = "REJECT_DRAFT_PR_PUBLISH_REQUEST_INVALID"
    WORK_ORDER_ID_MISMATCH = "REJECT_WORK_ORDER_ID_MISMATCH"
    PUBLISH_NOT_ACCEPTED = "REJECT_VERIFIED_DRAFT_PR_PUBLISH_NOT_ACCEPTED"


@dataclass(frozen=True)
class QueueAuthorizedVerifiedDraftPrPublishInvokeResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    publish_result: Optional[VerifiedDraftPrPublishResult] = None
    explicit_queue_authorized_verified_draft_pr_publish_requested: bool = False
    no_ready_performed: bool = True
    no_merge_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["publish_result"] = self.publish_result.to_dict() if self.publish_result else None
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
    publish_result: Optional[VerifiedDraftPrPublishResult] = None,
) -> QueueAuthorizedVerifiedDraftPrPublishInvokeResult:
    return QueueAuthorizedVerifiedDraftPrPublishInvokeResult(
        decision=QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT,
        rejection_reasons=_dedupe(reasons),
        publish_result=publish_result,
        explicit_queue_authorized_verified_draft_pr_publish_requested=explicit_requested,
    )


def _enrich_publish_request(
    publish_request: Mapping[str, Any],
    verifier_result: Mapping[str, Any],
) -> Dict[str, Any]:
    enriched = dict(publish_request)
    enriched["verifier_result"] = dict(verifier_result)
    return enriched


def invoke_reddog_wre_queue_authorized_verified_draft_pr_publish(
    *,
    explicit_queue_authorized_verified_draft_pr_publish_requested: bool,
    queue_slice_verifier_result: Mapping[str, Any],
    publish_request: Mapping[str, Any],
    runner: Optional[Any],
) -> QueueAuthorizedVerifiedDraftPrPublishInvokeResult:
    """Publish a draft PR only after accepted queue-authorized verification."""

    if explicit_queue_authorized_verified_draft_pr_publish_requested is not True:
        return _reject(
            [QueueAuthorizedVerifiedDraftPrPublishInvokeReason.EXPLICIT_INVOKE_MISSING],
            explicit_requested=False,
        )
    if runner is None:
        return _reject(
            [QueueAuthorizedVerifiedDraftPrPublishInvokeReason.RUNNER_REQUIRED],
            explicit_requested=True,
        )

    reasons: List[str] = []
    queue_verifier = _mapping(queue_slice_verifier_result)
    if queue_verifier.get("decision") != QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT:
        reasons.append(QueueAuthorizedVerifiedDraftPrPublishInvokeReason.SLICE_VERIFIER_NOT_ACCEPTED)

    verifier_payload = _mapping(queue_verifier.get("verifier_result"))
    if not verifier_payload:
        reasons.append(QueueAuthorizedVerifiedDraftPrPublishInvokeReason.VERIFIER_PAYLOAD_MISSING)
    elif (
        verifier_payload.get("decision") != AUTONOMOUS_SLICE_VERIFIER_ACCEPT
        or verifier_payload.get("accepted") is not True
    ):
        reasons.append(QueueAuthorizedVerifiedDraftPrPublishInvokeReason.VERIFIER_PAYLOAD_NOT_ACCEPTED)

    verifier_receipt = _mapping(verifier_payload.get("receipt"))
    if not verifier_receipt:
        reasons.append(QueueAuthorizedVerifiedDraftPrPublishInvokeReason.VERIFIER_RECEIPT_MISSING)

    request = _mapping(publish_request)
    if not request:
        reasons.append(QueueAuthorizedVerifiedDraftPrPublishInvokeReason.PUBLISH_REQUEST_INVALID)

    if verifier_receipt and request:
        request_work_order = str(request.get("work_order_id") or verifier_receipt.get("work_order_id") or "")
        if request_work_order != str(verifier_receipt.get("work_order_id") or ""):
            reasons.append(QueueAuthorizedVerifiedDraftPrPublishInvokeReason.WORK_ORDER_ID_MISMATCH)

    if reasons:
        return _reject(reasons, explicit_requested=True)

    published = publish_verified_draft_pr(
        _enrich_publish_request(request, verifier_payload),
        runner=runner,
    )
    if published.decision != VERIFIED_DRAFT_PR_PUBLISH_ACCEPT:
        return _reject(
            [
                QueueAuthorizedVerifiedDraftPrPublishInvokeReason.PUBLISH_NOT_ACCEPTED,
                *published.rejection_reasons,
            ],
            explicit_requested=True,
            publish_result=published,
        )

    return QueueAuthorizedVerifiedDraftPrPublishInvokeResult(
        decision=QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT,
        rejection_reasons=[],
        publish_result=published,
        explicit_queue_authorized_verified_draft_pr_publish_requested=True,
    )


__all__ = [
    "QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT",
    "QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT",
    "QueueAuthorizedVerifiedDraftPrPublishInvokeReason",
    "QueueAuthorizedVerifiedDraftPrPublishInvokeResult",
    "invoke_reddog_wre_queue_authorized_verified_draft_pr_publish",
]
