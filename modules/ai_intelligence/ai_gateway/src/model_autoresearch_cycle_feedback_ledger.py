"""AutoResearch cycle feedback ledger admission.

This module admits verified model AutoResearch cycle receipts into an injected
feedback ledger. It does not call providers, run benchmarks, promote models,
execute commands, write PatternMemory, mutate HoloIndex, or change RedDog
runtime model defaults.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence

from .model_autoresearch_cycle_receipt import (
    ModelAutoResearchCycleReceipt,
    rehydrate_model_autoresearch_cycle_receipt,
)
from .model_champion_challenger_autoresearch import (
    ModelAutoResearchPlanReceipt,
    rehydrate_model_autoresearch_plan_receipt,
)


MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_ACCEPT = (
    "MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_ACCEPT"
)
MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_REJECT = (
    "MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_REJECT"
)
MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_RECORD_TYPE = "model_autoresearch_cycle_feedback"
MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_RECORD_SCHEMA = (
    "model_autoresearch_cycle_feedback_record.v1"
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


class ModelAutoResearchCycleFeedbackLedgerAdmissionReason:
    EXPLICIT_INVOKE_MISSING = "REJECT_EXPLICIT_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_MISSING"
    STORE_REQUIRED = "REJECT_INJECTED_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_STORE_REQUIRED"
    CYCLE_RECEIPT_INVALID = "REJECT_AUTORESEARCH_CYCLE_RECEIPT_INVALID"
    SOURCE_PLAN_RECEIPT_INVALID = "REJECT_AUTORESEARCH_CYCLE_SOURCE_PLAN_RECEIPT_INVALID"
    SOURCE_PLAN_RECEIPT_MISMATCH = "REJECT_AUTORESEARCH_CYCLE_SOURCE_PLAN_RECEIPT_MISMATCH"
    CYCLE_NOT_FEEDBACK_ELIGIBLE = "REJECT_AUTORESEARCH_CYCLE_NOT_FEEDBACK_ELIGIBLE"
    SECRET_IN_RECORD = "REJECT_SECRET_IN_AUTORESEARCH_CYCLE_FEEDBACK_RECORD"
    STORE_WRITE_FAILED = "REJECT_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_STORE_WRITE_FAILED"


class ModelAutoResearchCycleFeedbackLedgerStore(Protocol):
    def append(self, record: Mapping[str, Any]) -> str:
        ...


class InMemoryModelAutoResearchCycleFeedbackLedgerStore:
    """Test/local store for model AutoResearch cycle feedback records."""

    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []

    def append(self, record: Mapping[str, Any]) -> str:
        payload = dict(record)
        self.records.append(payload)
        return f"model-autoresearch-cycle-feedback-record-{len(self.records)}"


class JsonlModelAutoResearchCycleFeedbackLedgerStore:
    """Append-only JSONL store for model AutoResearch cycle feedback records."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def append(self, record: Mapping[str, Any]) -> str:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
        return str(record["feedback_record_id"])


@dataclass(frozen=True)
class ModelAutoResearchCycleFeedbackLedgerAdmissionReceipt:
    admission_id: str
    cycle_receipt_id: str
    source_plan_receipt_id: str
    campaign_execution_receipt_id: str
    promotion_gate_supply_receipt_id: str
    task_family: Optional[str]
    catalog_snapshot_id: Optional[str]
    source_plan_receipt_digest: str
    executed_candidate_ids: List[str]
    promotion_gate_receipt_ids: List[str]
    feedback_record_id: Optional[str]
    feedback_record_digest: str
    rejection_reasons: List[str]
    no_provider_call_performed: bool = True
    no_benchmark_execution_performed: bool = True
    no_model_promotion_performed: bool = True
    no_command_execution_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_runtime_binding_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelAutoResearchCycleFeedbackLedgerAdmissionResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    receipt: Optional[ModelAutoResearchCycleFeedbackLedgerAdmissionReceipt] = None
    explicit_autoresearch_cycle_feedback_ledger_admission_requested: bool = False
    feedback_write_performed: bool = False
    no_provider_call_performed: bool = True
    no_benchmark_execution_performed: bool = True
    no_model_promotion_performed: bool = True
    no_command_execution_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_runtime_binding_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict() if self.receipt else None
        return payload


def admit_model_autoresearch_cycle_feedback(
    *,
    explicit_autoresearch_cycle_feedback_ledger_admission_requested: bool,
    cycle_receipt: ModelAutoResearchCycleReceipt | Mapping[str, Any],
    store: Optional[ModelAutoResearchCycleFeedbackLedgerStore],
    source_plan_receipt: ModelAutoResearchPlanReceipt | Mapping[str, Any] | None = None,
) -> ModelAutoResearchCycleFeedbackLedgerAdmissionResult:
    """Admit one verified AutoResearch cycle receipt into an injected ledger."""

    if explicit_autoresearch_cycle_feedback_ledger_admission_requested is not True:
        return _reject(
            [ModelAutoResearchCycleFeedbackLedgerAdmissionReason.EXPLICIT_INVOKE_MISSING],
            explicit_requested=False,
        )
    if store is None:
        return _reject(
            [ModelAutoResearchCycleFeedbackLedgerAdmissionReason.STORE_REQUIRED],
            explicit_requested=True,
        )

    try:
        cycle = _cycle_receipt(cycle_receipt)
    except Exception as exc:
        return _reject(
            [
                ModelAutoResearchCycleFeedbackLedgerAdmissionReason.CYCLE_RECEIPT_INVALID,
                f"cycle_error:{type(exc).__name__}",
            ],
            explicit_requested=True,
        )
    plan: Optional[ModelAutoResearchPlanReceipt] = None
    if source_plan_receipt is not None:
        try:
            plan = _plan_receipt(source_plan_receipt)
        except Exception as exc:
            return _reject(
                [
                    ModelAutoResearchCycleFeedbackLedgerAdmissionReason.SOURCE_PLAN_RECEIPT_INVALID,
                    f"plan_error:{type(exc).__name__}",
                ],
                explicit_requested=True,
            )
        if plan.receipt_id != cycle.source_plan_receipt_id:
            receipt = _admission_receipt(
                cycle=cycle,
                plan=plan,
                record={},
                record_id=None,
                reasons=[ModelAutoResearchCycleFeedbackLedgerAdmissionReason.SOURCE_PLAN_RECEIPT_MISMATCH],
            )
            return _reject(
                [ModelAutoResearchCycleFeedbackLedgerAdmissionReason.SOURCE_PLAN_RECEIPT_MISMATCH],
                explicit_requested=True,
                receipt=receipt,
            )

    record: Dict[str, Any] = {}
    reasons: List[str] = []
    if not cycle.executed_candidate_ids or not cycle.promotion_gate_receipt_ids:
        reasons.append(ModelAutoResearchCycleFeedbackLedgerAdmissionReason.CYCLE_NOT_FEEDBACK_ELIGIBLE)
    if not reasons:
        record = _feedback_record(cycle, plan)
        if _contains_secret(record):
            reasons.append(ModelAutoResearchCycleFeedbackLedgerAdmissionReason.SECRET_IN_RECORD)
    if reasons:
        receipt = _admission_receipt(cycle=cycle, record=record, record_id=None, reasons=reasons)
        return _reject(reasons, explicit_requested=True, receipt=receipt)

    try:
        record_id = store.append(record)
    except Exception:
        receipt = _admission_receipt(
            cycle=cycle,
            record=record,
            record_id=None,
            reasons=[ModelAutoResearchCycleFeedbackLedgerAdmissionReason.STORE_WRITE_FAILED],
        )
        return _reject(
            [ModelAutoResearchCycleFeedbackLedgerAdmissionReason.STORE_WRITE_FAILED],
            explicit_requested=True,
            receipt=receipt,
        )

    receipt = _admission_receipt(cycle=cycle, record=record, record_id=str(record_id or ""), reasons=[])
    return ModelAutoResearchCycleFeedbackLedgerAdmissionResult(
        decision=MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_ACCEPT,
        rejection_reasons=[],
        receipt=receipt,
        explicit_autoresearch_cycle_feedback_ledger_admission_requested=True,
        feedback_write_performed=True,
    )


def _cycle_receipt(
    value: ModelAutoResearchCycleReceipt | Mapping[str, Any],
) -> ModelAutoResearchCycleReceipt:
    if isinstance(value, ModelAutoResearchCycleReceipt):
        return value
    if isinstance(value, Mapping):
        return rehydrate_model_autoresearch_cycle_receipt(value)
    raise ValueError("invalid_autoresearch_cycle_receipt")


def _plan_receipt(
    value: ModelAutoResearchPlanReceipt | Mapping[str, Any],
) -> ModelAutoResearchPlanReceipt:
    if isinstance(value, ModelAutoResearchPlanReceipt):
        return value
    if isinstance(value, Mapping):
        return rehydrate_model_autoresearch_plan_receipt(value)
    raise ValueError("invalid_autoresearch_plan_receipt")


def _feedback_record(
    cycle: ModelAutoResearchCycleReceipt,
    plan: Optional[ModelAutoResearchPlanReceipt],
) -> Dict[str, Any]:
    record = {
        "record_type": MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_RECORD_TYPE,
        "schema_version": MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_RECORD_SCHEMA,
        "cycle_receipt_id": cycle.receipt_id,
        "source_plan_receipt_id": cycle.source_plan_receipt_id,
        "source_plan_context_bound": plan is not None,
        "campaign_execution_receipt_id": cycle.campaign_execution_receipt_id,
        "promotion_gate_supply_receipt_id": cycle.promotion_gate_supply_receipt_id,
        "executed_candidate_ids": list(cycle.executed_candidate_ids),
        "promotion_gate_receipt_ids": list(cycle.promotion_gate_receipt_ids),
    }
    if plan is not None:
        record["task_family"] = plan.policy.task_family
        record["catalog_snapshot_id"] = plan.policy.catalog_snapshot_id
        record["source_plan_receipt_digest"] = _digest(plan.to_dict())
    record["feedback_record_id"] = "model_autoresearch_cycle_feedback_" + _digest(record).removeprefix("sha256:")[:16]
    return record


def _admission_receipt(
    *,
    cycle: ModelAutoResearchCycleReceipt,
    plan: Optional[ModelAutoResearchPlanReceipt] = None,
    record: Mapping[str, Any],
    record_id: Optional[str],
    reasons: Sequence[str],
) -> ModelAutoResearchCycleFeedbackLedgerAdmissionReceipt:
    deduped = _dedupe(reasons)
    seed = {
        "cycle_receipt_id": cycle.receipt_id,
        "record": record,
        "record_id": record_id,
        "rejection_reasons": deduped,
    }
    return ModelAutoResearchCycleFeedbackLedgerAdmissionReceipt(
        admission_id="model_autoresearch_cycle_feedback_admission_" + _digest(seed).removeprefix("sha256:")[:16],
        cycle_receipt_id=cycle.receipt_id,
        source_plan_receipt_id=cycle.source_plan_receipt_id,
        campaign_execution_receipt_id=cycle.campaign_execution_receipt_id,
        promotion_gate_supply_receipt_id=cycle.promotion_gate_supply_receipt_id,
        task_family=plan.policy.task_family if plan is not None else None,
        catalog_snapshot_id=plan.policy.catalog_snapshot_id if plan is not None else None,
        source_plan_receipt_digest=_digest(plan.to_dict()) if plan is not None else "",
        executed_candidate_ids=list(cycle.executed_candidate_ids),
        promotion_gate_receipt_ids=list(cycle.promotion_gate_receipt_ids),
        feedback_record_id=record_id,
        feedback_record_digest=_digest(record),
        rejection_reasons=deduped,
    )


def _reject(
    reasons: Sequence[str],
    *,
    explicit_requested: bool,
    receipt: Optional[ModelAutoResearchCycleFeedbackLedgerAdmissionReceipt] = None,
) -> ModelAutoResearchCycleFeedbackLedgerAdmissionResult:
    return ModelAutoResearchCycleFeedbackLedgerAdmissionResult(
        decision=MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_REJECT,
        rejection_reasons=_dedupe(reasons),
        receipt=receipt,
        explicit_autoresearch_cycle_feedback_ledger_admission_requested=explicit_requested,
        feedback_write_performed=False,
    )


def _dedupe(values: Sequence[str]) -> List[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value or "").strip()))


def _contains_secret(value: Any) -> bool:
    text = json.dumps(value, sort_keys=True, default=str).lower()
    return any(marker in text for marker in SECRET_MARKERS)


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "InMemoryModelAutoResearchCycleFeedbackLedgerStore",
    "JsonlModelAutoResearchCycleFeedbackLedgerStore",
    "MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_ACCEPT",
    "MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_REJECT",
    "MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_RECORD_TYPE",
    "ModelAutoResearchCycleFeedbackLedgerAdmissionReason",
    "ModelAutoResearchCycleFeedbackLedgerAdmissionReceipt",
    "ModelAutoResearchCycleFeedbackLedgerAdmissionResult",
    "ModelAutoResearchCycleFeedbackLedgerStore",
    "admit_model_autoresearch_cycle_feedback",
]
