"""Model selection outcome feedback ledger admission.

This module admits independently verified model-selection outcomes into an
injected feedback ledger. It does not call providers, run benchmarks, promote
models, execute commands, write PatternMemory, mutate HoloIndex, or change
RedDog runtime model defaults.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence

from .model_intelligence_outcomes import (
    ModelSelectionOutcomeReceipt,
    outcome_feedback_record,
    rehydrate_model_selection_outcome_receipt,
)


MODEL_FEEDBACK_LEDGER_ADMISSION_ACCEPT = "MODEL_FEEDBACK_LEDGER_ADMISSION_ACCEPT"
MODEL_FEEDBACK_LEDGER_ADMISSION_REJECT = "MODEL_FEEDBACK_LEDGER_ADMISSION_REJECT"
MODEL_FEEDBACK_LEDGER_RECORD_TYPE = "model_selection_outcome_feedback"

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


class ModelFeedbackLedgerAdmissionReason:
    EXPLICIT_INVOKE_MISSING = "REJECT_EXPLICIT_MODEL_FEEDBACK_LEDGER_ADMISSION_MISSING"
    STORE_REQUIRED = "REJECT_INJECTED_MODEL_FEEDBACK_LEDGER_STORE_REQUIRED"
    OUTCOME_RECEIPT_INVALID = "REJECT_MODEL_SELECTION_OUTCOME_RECEIPT_INVALID"
    OUTCOME_NOT_FEEDBACK_ELIGIBLE = "REJECT_MODEL_SELECTION_OUTCOME_NOT_FEEDBACK_ELIGIBLE"
    SOURCE_RATCHET_REJECTED = "REJECT_SOURCE_RATCHET_NOT_ACCEPTED"
    VERIFIER_RECEIPT_MISMATCH = "REJECT_SOURCE_RATCHET_VERIFIER_RECEIPT_MISMATCH"
    MODEL_RUNTIME_BINDING_MISMATCH = "REJECT_SOURCE_RATCHET_MODEL_RUNTIME_BINDING_MISMATCH"
    SECRET_IN_RECORD = "REJECT_SECRET_IN_MODEL_FEEDBACK_RECORD"
    STORE_WRITE_FAILED = "REJECT_MODEL_FEEDBACK_LEDGER_STORE_WRITE_FAILED"


class ModelFeedbackLedgerStore(Protocol):
    def append(self, record: Mapping[str, Any]) -> str:
        ...


class InMemoryModelFeedbackLedgerStore:
    """Test/local store for model feedback ledger records."""

    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []

    def append(self, record: Mapping[str, Any]) -> str:
        payload = dict(record)
        self.records.append(payload)
        return f"model-feedback-record-{len(self.records)}"


class JsonlModelFeedbackLedgerStore:
    """Append-only JSONL store for model feedback records."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def append(self, record: Mapping[str, Any]) -> str:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
        return str(record["feedback_record_id"])


@dataclass(frozen=True)
class ModelFeedbackLedgerAdmissionReceipt:
    admission_id: str
    outcome_receipt_id: str
    selection_receipt_id: str
    catalog_snapshot_id: str
    task_family: str
    selected_model_ids: List[str]
    verification_receipt_ids: List[str]
    model_runtime_binding_receipt_id: Optional[str]
    model_runtime_binding_digest: str
    source_ratchet_id: Optional[str]
    source_ratchet_digest: str
    feedback_record_id: Optional[str]
    feedback_record_digest: str
    rejection_reasons: List[str]
    no_provider_call_performed: bool = True
    no_benchmark_execution_performed: bool = True
    no_model_promotion_performed: bool = True
    no_command_execution_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelFeedbackLedgerAdmissionResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    receipt: Optional[ModelFeedbackLedgerAdmissionReceipt] = None
    explicit_model_feedback_ledger_admission_requested: bool = False
    feedback_write_performed: bool = False
    no_provider_call_performed: bool = True
    no_benchmark_execution_performed: bool = True
    no_model_promotion_performed: bool = True
    no_command_execution_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict() if self.receipt else None
        return payload


def admit_model_selection_outcome_feedback(
    *,
    explicit_model_feedback_ledger_admission_requested: bool,
    model_selection_outcome_receipt: ModelSelectionOutcomeReceipt | Mapping[str, Any],
    store: Optional[ModelFeedbackLedgerStore],
    source_ratchet_receipt: Mapping[str, Any] | None = None,
) -> ModelFeedbackLedgerAdmissionResult:
    """Admit one verified model-selection outcome into an injected ledger."""

    if explicit_model_feedback_ledger_admission_requested is not True:
        return _reject(
            [ModelFeedbackLedgerAdmissionReason.EXPLICIT_INVOKE_MISSING],
            explicit_requested=False,
        )
    if store is None:
        return _reject(
            [ModelFeedbackLedgerAdmissionReason.STORE_REQUIRED],
            explicit_requested=True,
        )

    reasons: List[str] = []
    try:
        outcome = _outcome_receipt(model_selection_outcome_receipt)
    except Exception as exc:
        return _reject(
            [
                ModelFeedbackLedgerAdmissionReason.OUTCOME_RECEIPT_INVALID,
                f"outcome_error:{type(exc).__name__}",
            ],
            explicit_requested=True,
        )

    try:
        record = outcome_feedback_record(outcome)
    except Exception:
        reasons.append(ModelFeedbackLedgerAdmissionReason.OUTCOME_NOT_FEEDBACK_ELIGIBLE)
        record = {}

    ratchet = _mapping(source_ratchet_receipt)
    if ratchet:
        reasons.extend(_ratchet_binding_rejections(outcome, ratchet))

    if record:
        record = _feedback_record(outcome=outcome, base_record=record, source_ratchet_receipt=ratchet)
        if _contains_secret(record):
            reasons.append(ModelFeedbackLedgerAdmissionReason.SECRET_IN_RECORD)

    if reasons:
        receipt = _admission_receipt(
            outcome=outcome,
            record=record,
            record_id=None,
            reasons=reasons,
            source_ratchet_receipt=ratchet,
        )
        return _reject(reasons, explicit_requested=True, receipt=receipt)

    try:
        record_id = store.append(record)
    except Exception:
        receipt = _admission_receipt(
            outcome=outcome,
            record=record,
            record_id=None,
            reasons=[ModelFeedbackLedgerAdmissionReason.STORE_WRITE_FAILED],
            source_ratchet_receipt=ratchet,
        )
        return _reject(
            [ModelFeedbackLedgerAdmissionReason.STORE_WRITE_FAILED],
            explicit_requested=True,
            receipt=receipt,
        )

    receipt = _admission_receipt(
        outcome=outcome,
        record=record,
        record_id=str(record_id or ""),
        reasons=[],
        source_ratchet_receipt=ratchet,
    )
    return ModelFeedbackLedgerAdmissionResult(
        decision=MODEL_FEEDBACK_LEDGER_ADMISSION_ACCEPT,
        rejection_reasons=[],
        receipt=receipt,
        explicit_model_feedback_ledger_admission_requested=True,
        feedback_write_performed=True,
    )


def _outcome_receipt(value: ModelSelectionOutcomeReceipt | Mapping[str, Any]) -> ModelSelectionOutcomeReceipt:
    if isinstance(value, ModelSelectionOutcomeReceipt):
        return value
    if isinstance(value, Mapping):
        return rehydrate_model_selection_outcome_receipt(value)
    raise ValueError("invalid_outcome_receipt")


def _feedback_record(
    *,
    outcome: ModelSelectionOutcomeReceipt,
    base_record: Mapping[str, Any],
    source_ratchet_receipt: Mapping[str, Any],
) -> Dict[str, Any]:
    source_ratchet_id, source_ratchet_digest = _source_ratchet_pair(source_ratchet_receipt)
    record = {
        "record_type": MODEL_FEEDBACK_LEDGER_RECORD_TYPE,
        "schema_version": "model_feedback_ledger_record.v1",
        **dict(base_record),
        "source_ratchet_id": source_ratchet_id,
        "source_ratchet_digest": source_ratchet_digest,
    }
    record["feedback_record_id"] = "model_feedback_" + _digest(
        {
            "outcome_receipt_id": outcome.receipt_id,
            "source_ratchet_id": source_ratchet_id,
            "source_ratchet_digest": source_ratchet_digest,
        }
    ).removeprefix("sha256:")[:16]
    return record


def _ratchet_binding_rejections(
    outcome: ModelSelectionOutcomeReceipt,
    source_ratchet_receipt: Mapping[str, Any],
) -> List[str]:
    reasons: List[str] = []
    if source_ratchet_receipt.get("rejection_reasons"):
        reasons.append(ModelFeedbackLedgerAdmissionReason.SOURCE_RATCHET_REJECTED)
    verifier_receipt_id = str(source_ratchet_receipt.get("verifier_receipt_id") or "")
    if verifier_receipt_id and verifier_receipt_id not in outcome.verification_receipt_ids:
        reasons.append(ModelFeedbackLedgerAdmissionReason.VERIFIER_RECEIPT_MISMATCH)
    ratchet_runtime_id = str(source_ratchet_receipt.get("model_runtime_binding_receipt_id") or "")
    ratchet_runtime_digest = str(source_ratchet_receipt.get("model_runtime_binding_digest") or "")
    outcome_runtime_id = outcome.model_runtime_binding_receipt_id or ""
    outcome_runtime_digest = outcome.model_runtime_binding_digest or ""
    runtime_pairs = [
        pair
        for pair in (
            (ratchet_runtime_id, ratchet_runtime_digest),
            (outcome_runtime_id, outcome_runtime_digest),
        )
        if pair[0] or pair[1]
    ]
    if runtime_pairs:
        for receipt_id, digest in runtime_pairs:
            if not receipt_id or not _is_digest(digest):
                reasons.append(ModelFeedbackLedgerAdmissionReason.MODEL_RUNTIME_BINDING_MISMATCH)
                break
        else:
            if any(pair != runtime_pairs[0] for pair in runtime_pairs[1:]):
                reasons.append(ModelFeedbackLedgerAdmissionReason.MODEL_RUNTIME_BINDING_MISMATCH)
    return _dedupe(reasons)


def _admission_receipt(
    *,
    outcome: ModelSelectionOutcomeReceipt,
    record: Mapping[str, Any],
    record_id: Optional[str],
    reasons: Sequence[str],
    source_ratchet_receipt: Mapping[str, Any],
) -> ModelFeedbackLedgerAdmissionReceipt:
    source_ratchet_id, source_ratchet_digest = _source_ratchet_pair(source_ratchet_receipt)
    deduped = _dedupe(reasons)
    seed = {
        "record": record,
        "record_id": record_id,
        "rejection_reasons": deduped,
    }
    return ModelFeedbackLedgerAdmissionReceipt(
        admission_id="model_feedback_admission_" + _digest(seed).removeprefix("sha256:")[:16],
        outcome_receipt_id=outcome.receipt_id,
        selection_receipt_id=outcome.selection_receipt_id,
        catalog_snapshot_id=outcome.catalog_snapshot_id,
        task_family=outcome.task_family,
        selected_model_ids=list(outcome.selected_model_ids),
        verification_receipt_ids=list(outcome.verification_receipt_ids),
        model_runtime_binding_receipt_id=outcome.model_runtime_binding_receipt_id,
        model_runtime_binding_digest=outcome.model_runtime_binding_digest,
        source_ratchet_id=source_ratchet_id,
        source_ratchet_digest=source_ratchet_digest,
        feedback_record_id=record_id,
        feedback_record_digest=_digest(record),
        rejection_reasons=deduped,
    )


def _source_ratchet_pair(source_ratchet_receipt: Mapping[str, Any]) -> tuple[Optional[str], str]:
    if not source_ratchet_receipt:
        return None, ""
    ratchet_id = str(source_ratchet_receipt.get("ratchet_id") or "")
    return ratchet_id or None, _digest(source_ratchet_receipt)


def _reject(
    reasons: Sequence[str],
    *,
    explicit_requested: bool,
    receipt: Optional[ModelFeedbackLedgerAdmissionReceipt] = None,
) -> ModelFeedbackLedgerAdmissionResult:
    return ModelFeedbackLedgerAdmissionResult(
        decision=MODEL_FEEDBACK_LEDGER_ADMISSION_REJECT,
        rejection_reasons=_dedupe(reasons),
        receipt=receipt,
        explicit_model_feedback_ledger_admission_requested=explicit_requested,
        feedback_write_performed=False,
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _dedupe(values: Sequence[str]) -> List[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value or "").strip()))


def _contains_secret(value: Any) -> bool:
    text = json.dumps(value, sort_keys=True, default=str).lower()
    return any(marker in text for marker in SECRET_MARKERS)


def _is_digest(value: Any) -> bool:
    text = str(value or "")
    return (
        text.startswith("sha256:")
        and len(text) == 71
        and all(ch in "0123456789abcdef" for ch in text.removeprefix("sha256:"))
    )


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "InMemoryModelFeedbackLedgerStore",
    "JsonlModelFeedbackLedgerStore",
    "MODEL_FEEDBACK_LEDGER_ADMISSION_ACCEPT",
    "MODEL_FEEDBACK_LEDGER_ADMISSION_REJECT",
    "MODEL_FEEDBACK_LEDGER_RECORD_TYPE",
    "ModelFeedbackLedgerAdmissionReason",
    "ModelFeedbackLedgerAdmissionReceipt",
    "ModelFeedbackLedgerAdmissionResult",
    "ModelFeedbackLedgerStore",
    "admit_model_selection_outcome_feedback",
]
