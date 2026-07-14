"""RedDog queue-authorized held-out regression gate explicit invoke guard.

Slice: REDDOG_WRE_QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_PHASE1

This module consumes an accepted queue-authorized verified outcome ratchet
result, then invokes the existing WRE held-out recursive-improvement regression
gate. It emits only a deterministic gate receipt; it never runs tests, writes
PatternMemory, publishes PRs, merges, executes commands, or mutates HoloIndex.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_outcome_ratchet_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT,
)
from modules.infrastructure.wre_core.src.reddog_held_out_recursive_improvement_regression_gate import (
    HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT,
    HeldOutRecursiveImprovementRegressionResult,
    evaluate_held_out_recursive_improvement_regression_gate,
)
from modules.infrastructure.wre_core.src.reddog_verified_outcome_ratchet import (
    OUTCOME_RATCHET_RECORDED,
)


QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT = (
    "QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT"
)
QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_REJECT = (
    "QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_REJECT"
)


class QueueAuthorizedHeldOutRegressionGateInvokeReason:
    EXPLICIT_INVOKE_MISSING = "REJECT_EXPLICIT_QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_MISSING"
    RATCHET_INVOKE_NOT_ACCEPTED = "REJECT_QUEUE_VERIFIED_OUTCOME_RATCHET_INVOKE_NOT_ACCEPTED"
    RATCHET_PAYLOAD_MISSING = "REJECT_RATCHET_PAYLOAD_MISSING"
    RATCHET_PAYLOAD_NOT_RECORDED = "REJECT_RATCHET_PAYLOAD_NOT_RECORDED"
    RATCHET_RECEIPT_MISSING = "REJECT_RATCHET_RECEIPT_MISSING"
    GATE_REQUEST_INVALID = "REJECT_HELD_OUT_GATE_REQUEST_INVALID"
    VERIFICATION_PAYLOAD_MISSING = "REJECT_VERIFICATION_PAYLOAD_MISSING"
    VERIFIER_RECEIPT_MISMATCH = "REJECT_VERIFIER_RECEIPT_MISMATCH"
    WORK_ORDER_ID_MISMATCH = "REJECT_WORK_ORDER_ID_MISMATCH"
    GATE_NOT_ACCEPTED = "REJECT_HELD_OUT_REGRESSION_GATE_NOT_ACCEPTED"


@dataclass(frozen=True)
class QueueAuthorizedHeldOutRegressionGateInvokeResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    gate_result: Optional[HeldOutRecursiveImprovementRegressionResult] = None
    explicit_queue_authorized_held_out_regression_gate_requested: bool = False
    no_command_execution_performed: bool = True
    no_test_execution_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["gate_result"] = self.gate_result.to_dict() if self.gate_result else None
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
    gate_result: Optional[HeldOutRecursiveImprovementRegressionResult] = None,
) -> QueueAuthorizedHeldOutRegressionGateInvokeResult:
    return QueueAuthorizedHeldOutRegressionGateInvokeResult(
        decision=QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_REJECT,
        rejection_reasons=_dedupe(reasons),
        gate_result=gate_result,
        explicit_queue_authorized_held_out_regression_gate_requested=explicit_requested,
    )


def _same_nonempty(left: Any, right: Any) -> bool:
    left_text = str(left or "")
    return bool(left_text) and left_text == str(right or "")


def _enrich_gate_request(
    gate_request: Mapping[str, Any],
    ratchet_result: Mapping[str, Any],
) -> Dict[str, Any]:
    enriched = dict(gate_request)
    enriched["ratchet_result"] = dict(ratchet_result)
    return enriched


def invoke_reddog_wre_queue_authorized_held_out_regression_gate(
    *,
    explicit_queue_authorized_held_out_regression_gate_requested: bool,
    queue_verified_outcome_ratchet_result: Mapping[str, Any],
    held_out_gate_request: Mapping[str, Any],
) -> QueueAuthorizedHeldOutRegressionGateInvokeResult:
    """Evaluate held-out regression only after accepted queue outcome ratchet."""

    if explicit_queue_authorized_held_out_regression_gate_requested is not True:
        return _reject(
            [QueueAuthorizedHeldOutRegressionGateInvokeReason.EXPLICIT_INVOKE_MISSING],
            explicit_requested=False,
        )

    reasons: List[str] = []
    queue_ratchet = _mapping(queue_verified_outcome_ratchet_result)
    if queue_ratchet.get("decision") != QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT:
        reasons.append(QueueAuthorizedHeldOutRegressionGateInvokeReason.RATCHET_INVOKE_NOT_ACCEPTED)

    ratchet_payload = _mapping(queue_ratchet.get("ratchet_result"))
    if not ratchet_payload:
        reasons.append(QueueAuthorizedHeldOutRegressionGateInvokeReason.RATCHET_PAYLOAD_MISSING)
    elif (
        ratchet_payload.get("decision") != OUTCOME_RATCHET_RECORDED
        or ratchet_payload.get("accepted") is not True
    ):
        reasons.append(QueueAuthorizedHeldOutRegressionGateInvokeReason.RATCHET_PAYLOAD_NOT_RECORDED)

    ratchet_receipt = _mapping(ratchet_payload.get("receipt"))
    if not ratchet_receipt:
        reasons.append(QueueAuthorizedHeldOutRegressionGateInvokeReason.RATCHET_RECEIPT_MISSING)

    request = _mapping(held_out_gate_request)
    if not request:
        reasons.append(QueueAuthorizedHeldOutRegressionGateInvokeReason.GATE_REQUEST_INVALID)

    verification_result = _mapping(request.get("verification_result"))
    verification_receipt = _mapping(verification_result.get("receipt"))
    if not verification_result or not verification_receipt:
        reasons.append(QueueAuthorizedHeldOutRegressionGateInvokeReason.VERIFICATION_PAYLOAD_MISSING)
    elif ratchet_receipt:
        if not _same_nonempty(
            verification_receipt.get("receipt_id"),
            ratchet_receipt.get("verifier_receipt_id"),
        ):
            reasons.append(QueueAuthorizedHeldOutRegressionGateInvokeReason.VERIFIER_RECEIPT_MISMATCH)
        if not _same_nonempty(
            request.get("work_order_id") or verification_receipt.get("work_order_id"),
            ratchet_receipt.get("work_order_id"),
        ):
            reasons.append(QueueAuthorizedHeldOutRegressionGateInvokeReason.WORK_ORDER_ID_MISMATCH)

    if reasons:
        return _reject(reasons, explicit_requested=True)

    gated = evaluate_held_out_recursive_improvement_regression_gate(
        _enrich_gate_request(request, ratchet_payload)
    )
    if (
        gated.decision != HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT
        or gated.accepted is not True
    ):
        return _reject(
            [
                QueueAuthorizedHeldOutRegressionGateInvokeReason.GATE_NOT_ACCEPTED,
                *gated.rejection_reasons,
            ],
            explicit_requested=True,
            gate_result=gated,
        )

    return QueueAuthorizedHeldOutRegressionGateInvokeResult(
        decision=QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT,
        rejection_reasons=[],
        gate_result=gated,
        explicit_queue_authorized_held_out_regression_gate_requested=True,
    )


__all__ = [
    "QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT",
    "QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_REJECT",
    "QueueAuthorizedHeldOutRegressionGateInvokeReason",
    "QueueAuthorizedHeldOutRegressionGateInvokeResult",
    "invoke_reddog_wre_queue_authorized_held_out_regression_gate",
]
