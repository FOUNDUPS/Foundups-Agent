"""RedDog queue-authorized PatternMemory admission explicit invoke guard.

Slice: REDDOG_WRE_QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_PHASE1

This module consumes an accepted queue-authorized held-out regression gate
result, then writes a verified outcome record through an injected sink. It does
not instantiate PatternMemory, run commands, publish PRs, merge, settle rewards,
or mutate HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence

from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_held_out_regression_gate_invoke import (
    QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT,
)
from modules.infrastructure.wre_core.src.reddog_held_out_recursive_improvement_regression_gate import (
    HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT,
)


QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT = (
    "QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT"
)
QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT = (
    "QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT"
)

SECRET_MARKERS = (
    "authorization:",
    "bearer ",
    "api_key",
    "apikey",
    "private_key",
    "begin private key",
    "secret=",
    "token=",
    "password=",
)


class PatternMemoryAdmissionSink(Protocol):
    def store_verified_outcome(self, record: Mapping[str, Any]) -> str:
        ...


class QueueAuthorizedPatternMemoryAdmissionInvokeReason:
    EXPLICIT_INVOKE_MISSING = "REJECT_EXPLICIT_QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_MISSING"
    SINK_REQUIRED = "REJECT_INJECTED_PATTERN_MEMORY_ADMISSION_SINK_REQUIRED"
    HELD_OUT_INVOKE_NOT_ACCEPTED = "REJECT_QUEUE_HELD_OUT_REGRESSION_GATE_INVOKE_NOT_ACCEPTED"
    GATE_PAYLOAD_MISSING = "REJECT_HELD_OUT_GATE_PAYLOAD_MISSING"
    GATE_PAYLOAD_NOT_ACCEPTED = "REJECT_HELD_OUT_GATE_PAYLOAD_NOT_ACCEPTED"
    GATE_RECEIPT_MISSING = "REJECT_HELD_OUT_GATE_RECEIPT_MISSING"
    PATTERN_MEMORY_NOT_ALLOWED = "REJECT_PATTERN_MEMORY_ADMISSION_NOT_ALLOWED"
    ADMISSION_REQUEST_INVALID = "REJECT_PATTERN_MEMORY_ADMISSION_REQUEST_INVALID"
    WORK_ORDER_ID_MISMATCH = "REJECT_WORK_ORDER_ID_MISMATCH"
    MODEL_RUNTIME_BINDING_MISMATCH = "REJECT_MODEL_RUNTIME_BINDING_MISMATCH"
    SECRET_IN_RECORD = "REJECT_SECRET_IN_PATTERN_MEMORY_RECORD"
    SINK_WRITE_FAILED = "REJECT_PATTERN_MEMORY_ADMISSION_SINK_WRITE_FAILED"


@dataclass(frozen=True)
class QueueAuthorizedPatternMemoryAdmissionReceipt:
    admission_id: str
    work_order_id: str
    slice_name: str
    gate_id: str
    ratchet_id: str
    verifier_receipt_id: str
    improvement_job_id: str
    held_out_suite_id: str
    model_runtime_binding_receipt_id: Optional[str]
    model_runtime_binding_digest: str
    pattern_memory_record_id: Optional[str]
    record_digest: str
    rejection_reasons: List[str]
    no_command_execution_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QueueAuthorizedPatternMemoryAdmissionInvokeResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    receipt: Optional[QueueAuthorizedPatternMemoryAdmissionReceipt] = None
    explicit_queue_authorized_pattern_memory_admission_requested: bool = False
    pattern_memory_write_performed: bool = False
    no_command_execution_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict() if self.receipt else None
        return payload


def _digest(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _dedupe(values: Sequence[str]) -> List[str]:
    return list(dict.fromkeys(str(v) for v in values if str(v or "").strip()))


def _contains_secret(value: Any) -> bool:
    text = json.dumps(value, sort_keys=True, default=str).lower()
    return any(marker in text for marker in SECRET_MARKERS)


def _same_nonempty(left: Any, right: Any) -> bool:
    left_text = str(left or "")
    return bool(left_text) and left_text == str(right or "")


def _is_digest(value: Any) -> bool:
    text = str(value or "")
    return (
        text.startswith("sha256:")
        and len(text) == 71
        and all(ch in "0123456789abcdef" for ch in text.removeprefix("sha256:"))
    )


def _runtime_binding_pair(value: Mapping[str, Any]) -> tuple[str, str]:
    receipt_id = str(
        value.get("model_runtime_binding_receipt_id")
        or value.get("runtime_binding_receipt_id")
        or ""
    )
    digest = str(value.get("model_runtime_binding_digest") or "")
    return receipt_id, digest


def _runtime_binding_ok(
    gate_receipt: Mapping[str, Any],
    admission_request: Mapping[str, Any],
) -> bool:
    pairs = [
        pair
        for pair in (
            _runtime_binding_pair(gate_receipt),
            _runtime_binding_pair(admission_request),
        )
        if pair[0] or pair[1]
    ]
    if not pairs:
        return True
    for receipt_id, digest in pairs:
        if not receipt_id or not digest:
            return False
        if not receipt_id.startswith("reddog_model_runtime_binding:") or not _is_digest(digest):
            return False
    return all(pair == pairs[0] for pair in pairs[1:])


def _record_from_gate(
    *,
    gate_result: Mapping[str, Any],
    gate_receipt: Mapping[str, Any],
    admission_request: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "record_type": "reddog_verified_recursive_improvement_outcome",
        "work_order_id": str(gate_receipt.get("work_order_id") or ""),
        "slice_name": str(gate_receipt.get("slice_name") or ""),
        "gate_id": str(gate_receipt.get("gate_id") or ""),
        "ratchet_id": str(gate_receipt.get("ratchet_id") or ""),
        "verifier_receipt_id": str(gate_receipt.get("verifier_receipt_id") or ""),
        "improvement_job_id": str(gate_receipt.get("improvement_job_id") or ""),
        "held_out_suite_id": str(gate_receipt.get("held_out_suite_id") or ""),
        "held_out_suite_digest": str(gate_receipt.get("held_out_suite_digest") or ""),
        "model_runtime_binding_receipt_id": str(
            gate_receipt.get("model_runtime_binding_receipt_id") or ""
        ),
        "model_runtime_binding_digest": str(gate_receipt.get("model_runtime_binding_digest") or ""),
        "candidate_head_sha": str(gate_receipt.get("candidate_head_sha") or ""),
        "regression_test_count": int(gate_receipt.get("regression_test_count") or 0),
        "pattern_memory_admission_allowed": True,
        "gate_result_digest": _digest(gate_result),
        "admission_metadata": dict(_mapping(admission_request.get("admission_metadata"))),
    }


def _build_receipt(
    *,
    record: Mapping[str, Any],
    record_id: Optional[str],
    reasons: Sequence[str],
) -> QueueAuthorizedPatternMemoryAdmissionReceipt:
    deduped = _dedupe(reasons)
    seed = {
        "record": record,
        "record_id": record_id,
        "rejection_reasons": deduped,
    }
    return QueueAuthorizedPatternMemoryAdmissionReceipt(
        admission_id="pattern_memory_admission_" + _digest(seed).removeprefix("sha256:")[:16],
        work_order_id=str(record.get("work_order_id") or ""),
        slice_name=str(record.get("slice_name") or ""),
        gate_id=str(record.get("gate_id") or ""),
        ratchet_id=str(record.get("ratchet_id") or ""),
        verifier_receipt_id=str(record.get("verifier_receipt_id") or ""),
        improvement_job_id=str(record.get("improvement_job_id") or ""),
        held_out_suite_id=str(record.get("held_out_suite_id") or ""),
        model_runtime_binding_receipt_id=str(
            record.get("model_runtime_binding_receipt_id") or ""
        )
        or None,
        model_runtime_binding_digest=str(record.get("model_runtime_binding_digest") or ""),
        pattern_memory_record_id=record_id,
        record_digest=_digest(record),
        rejection_reasons=deduped,
    )


def canonical_pattern_memory_admission_identity(
    record: Mapping[str, Any],
    record_id: str,
) -> tuple[str, str]:
    """Return the admission ID and record digest for a persisted outcome."""

    receipt = _build_receipt(record=record, record_id=record_id, reasons=[])
    return receipt.admission_id, receipt.record_digest


def _reject(
    reasons: Sequence[str],
    *,
    explicit_requested: bool,
    receipt: Optional[QueueAuthorizedPatternMemoryAdmissionReceipt] = None,
) -> QueueAuthorizedPatternMemoryAdmissionInvokeResult:
    return QueueAuthorizedPatternMemoryAdmissionInvokeResult(
        decision=QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT,
        rejection_reasons=_dedupe(reasons),
        receipt=receipt,
        explicit_queue_authorized_pattern_memory_admission_requested=explicit_requested,
        pattern_memory_write_performed=False,
    )


def invoke_reddog_wre_queue_authorized_pattern_memory_admission(
    *,
    explicit_queue_authorized_pattern_memory_admission_requested: bool,
    queue_held_out_gate_result: Mapping[str, Any],
    admission_request: Mapping[str, Any],
    sink: Optional[PatternMemoryAdmissionSink],
) -> QueueAuthorizedPatternMemoryAdmissionInvokeResult:
    """Admit a verified recursive outcome into an injected PatternMemory sink."""

    if explicit_queue_authorized_pattern_memory_admission_requested is not True:
        return _reject(
            [QueueAuthorizedPatternMemoryAdmissionInvokeReason.EXPLICIT_INVOKE_MISSING],
            explicit_requested=False,
        )
    if sink is None:
        return _reject(
            [QueueAuthorizedPatternMemoryAdmissionInvokeReason.SINK_REQUIRED],
            explicit_requested=True,
        )

    reasons: List[str] = []
    queue_gate = _mapping(queue_held_out_gate_result)
    if queue_gate.get("decision") != QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT:
        reasons.append(QueueAuthorizedPatternMemoryAdmissionInvokeReason.HELD_OUT_INVOKE_NOT_ACCEPTED)

    gate_payload = _mapping(queue_gate.get("gate_result"))
    if not gate_payload:
        reasons.append(QueueAuthorizedPatternMemoryAdmissionInvokeReason.GATE_PAYLOAD_MISSING)
    elif (
        gate_payload.get("decision") != HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT
        or gate_payload.get("accepted") is not True
    ):
        reasons.append(QueueAuthorizedPatternMemoryAdmissionInvokeReason.GATE_PAYLOAD_NOT_ACCEPTED)

    gate_receipt = _mapping(gate_payload.get("receipt"))
    if not gate_receipt:
        reasons.append(QueueAuthorizedPatternMemoryAdmissionInvokeReason.GATE_RECEIPT_MISSING)
    elif gate_receipt.get("pattern_memory_admission_allowed") is not True:
        reasons.append(QueueAuthorizedPatternMemoryAdmissionInvokeReason.PATTERN_MEMORY_NOT_ALLOWED)

    request = _mapping(admission_request)
    if not request:
        reasons.append(QueueAuthorizedPatternMemoryAdmissionInvokeReason.ADMISSION_REQUEST_INVALID)
    elif gate_receipt and not _same_nonempty(
        request.get("work_order_id") or gate_receipt.get("work_order_id"),
        gate_receipt.get("work_order_id"),
    ):
        reasons.append(QueueAuthorizedPatternMemoryAdmissionInvokeReason.WORK_ORDER_ID_MISMATCH)
    elif gate_receipt and request and not _runtime_binding_ok(gate_receipt, request):
        reasons.append(
            QueueAuthorizedPatternMemoryAdmissionInvokeReason.MODEL_RUNTIME_BINDING_MISMATCH
        )

    record = (
        _record_from_gate(
            gate_result=gate_payload,
            gate_receipt=gate_receipt,
            admission_request=request,
        )
        if gate_payload and gate_receipt and request
        else {}
    )
    if record and _contains_secret(record):
        reasons.append(QueueAuthorizedPatternMemoryAdmissionInvokeReason.SECRET_IN_RECORD)

    if reasons:
        receipt = _build_receipt(record=record, record_id=None, reasons=reasons) if record else None
        return _reject(reasons, explicit_requested=True, receipt=receipt)

    try:
        record_id = sink.store_verified_outcome(record)
    except Exception:
        receipt = _build_receipt(
            record=record,
            record_id=None,
            reasons=[QueueAuthorizedPatternMemoryAdmissionInvokeReason.SINK_WRITE_FAILED],
        )
        return _reject(
            [QueueAuthorizedPatternMemoryAdmissionInvokeReason.SINK_WRITE_FAILED],
            explicit_requested=True,
            receipt=receipt,
        )

    receipt = _build_receipt(record=record, record_id=str(record_id or ""), reasons=[])
    return QueueAuthorizedPatternMemoryAdmissionInvokeResult(
        decision=QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT,
        rejection_reasons=[],
        receipt=receipt,
        explicit_queue_authorized_pattern_memory_admission_requested=True,
        pattern_memory_write_performed=True,
    )


__all__ = [
    "PatternMemoryAdmissionSink",
    "canonical_pattern_memory_admission_identity",
    "QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT",
    "QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT",
    "QueueAuthorizedPatternMemoryAdmissionInvokeReason",
    "QueueAuthorizedPatternMemoryAdmissionInvokeResult",
    "QueueAuthorizedPatternMemoryAdmissionReceipt",
    "invoke_reddog_wre_queue_authorized_pattern_memory_admission",
]
