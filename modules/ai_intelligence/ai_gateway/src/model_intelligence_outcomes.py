"""Benchmark evidence and outcome receipts for model intelligence.

This module hardens model selection beyond scalar catalog fields. It defines the
receipt-bound benchmark, promotion, and outcome evidence that production model
selection must consume before RedDog can bind a model or Fusion panel.

No function in this module calls a model, writes PatternMemory, promotes a model
by itself, mutates HoloIndex, or executes commands.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping

from .model_intelligence_catalog import PromotionState
from .model_intelligence_selection import ModelSelectionReceipt, SelectionDecision


BENCHMARK_SCHEMA_VERSION = "model_benchmark_evidence_receipt.v1"
PROMOTION_SCHEMA_VERSION = "model_promotion_evidence_receipt.v1"
OUTCOME_SCHEMA_VERSION = "model_selection_outcome_receipt.v1"


class VerifierDecision(str, Enum):
    """Independent verifier verdict for the model-produced work."""

    ACCEPT = "accept"
    REJECT = "reject"
    ERROR = "error"
    SKIPPED = "skipped"


class OutcomeDecision(str, Enum):
    """Whether this outcome may feed benchmark/recursive learning."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ModelOutcomeMetrics:
    """Bounded numeric measurements for one model or panel outcome."""

    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_estimate_usd: float | None = None

    def normalized(self) -> "ModelOutcomeMetrics":
        return ModelOutcomeMetrics(
            latency_ms=_non_negative_int_or_none(self.latency_ms),
            input_tokens=_non_negative_int_or_none(self.input_tokens),
            output_tokens=_non_negative_int_or_none(self.output_tokens),
            cost_estimate_usd=_non_negative_float_or_none(self.cost_estimate_usd),
        )


@dataclass(frozen=True)
class ModelBenchmarkEvidenceReceipt:
    """Receipt for measured model performance on a held-out task set."""

    receipt_id: str
    model_id: str
    task_family: str
    task_set_digest: str
    held_out_split_digest: str
    prompt_topology_digest: str
    verifier_digest: str
    verifier_receipt_id: str
    sample_count: int
    accepted_count: int
    verifier_pass_rate: float
    metrics: ModelOutcomeMetrics
    schema_version: str = BENCHMARK_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "model_id": self.model_id,
            "task_family": self.task_family,
            "task_set_digest": self.task_set_digest,
            "held_out_split_digest": self.held_out_split_digest,
            "prompt_topology_digest": self.prompt_topology_digest,
            "verifier_digest": self.verifier_digest,
            "verifier_receipt_id": self.verifier_receipt_id,
            "sample_count": self.sample_count,
            "accepted_count": self.accepted_count,
            "verifier_pass_rate": self.verifier_pass_rate,
            "metrics": asdict(self.metrics.normalized()),
        }


@dataclass(frozen=True)
class ModelPromotionEvidenceReceipt:
    """Receipt proving a model was authorized for a promotion state."""

    receipt_id: str
    model_id: str
    task_family: str
    benchmark_evidence_receipt_id: str
    promotion_state: PromotionState
    promotion_authority_receipt_id: str
    signed_promotion_receipt_id: str
    min_verifier_pass_rate: float
    schema_version: str = PROMOTION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "model_id": self.model_id,
            "task_family": self.task_family,
            "benchmark_evidence_receipt_id": self.benchmark_evidence_receipt_id,
            "promotion_state": self.promotion_state.value,
            "promotion_authority_receipt_id": self.promotion_authority_receipt_id,
            "signed_promotion_receipt_id": self.signed_promotion_receipt_id,
            "min_verifier_pass_rate": self.min_verifier_pass_rate,
        }


@dataclass(frozen=True)
class ModelSelectionOutcomeReceipt:
    """Digest-bound outcome for a model selection receipt."""

    receipt_id: str
    selection_receipt_id: str
    catalog_snapshot_id: str
    task_family: str
    selected_model_ids: tuple[str, ...]
    verifier_decision: VerifierDecision
    verification_receipt_ids: tuple[str, ...]
    outcome_decision: OutcomeDecision
    feedback_eligible: bool
    metrics: ModelOutcomeMetrics
    rejection_reasons: tuple[str, ...] = ()
    evidence_receipt_ids: tuple[str, ...] = ()
    schema_version: str = OUTCOME_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "selection_receipt_id": self.selection_receipt_id,
            "catalog_snapshot_id": self.catalog_snapshot_id,
            "task_family": self.task_family,
            "selected_model_ids": list(self.selected_model_ids),
            "verifier_decision": self.verifier_decision.value,
            "verification_receipt_ids": list(self.verification_receipt_ids),
            "outcome_decision": self.outcome_decision.value,
            "feedback_eligible": self.feedback_eligible,
            "metrics": asdict(self.metrics.normalized()),
            "rejection_reasons": list(self.rejection_reasons),
            "evidence_receipt_ids": list(self.evidence_receipt_ids),
        }


def build_model_benchmark_evidence_receipt(
    *,
    model_id: str,
    task_family: str,
    task_set_digest: str,
    held_out_split_digest: str,
    prompt_topology_digest: str,
    verifier_digest: str,
    verifier_receipt_id: str,
    sample_count: int,
    accepted_count: int,
    metrics: ModelOutcomeMetrics | None = None,
) -> ModelBenchmarkEvidenceReceipt:
    """Build a receipt for measured held-out benchmark evidence."""

    normalized = {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "model_id": _required("model_id", model_id),
        "task_family": _clean_token(_required("task_family", task_family)),
        "task_set_digest": _required("task_set_digest", task_set_digest),
        "held_out_split_digest": _required("held_out_split_digest", held_out_split_digest),
        "prompt_topology_digest": _required("prompt_topology_digest", prompt_topology_digest),
        "verifier_digest": _required("verifier_digest", verifier_digest),
        "verifier_receipt_id": _required("verifier_receipt_id", verifier_receipt_id),
        "sample_count": _positive_int(sample_count, "sample_count"),
        "accepted_count": _bounded_accepted_count(accepted_count, sample_count),
        "metrics": asdict((metrics or ModelOutcomeMetrics()).normalized()),
    }
    pass_rate = round(normalized["accepted_count"] / normalized["sample_count"], 6)
    body = {**normalized, "verifier_pass_rate": pass_rate}
    return ModelBenchmarkEvidenceReceipt(
        receipt_id=_digest_prefixed("model_benchmark_evidence", body),
        model_id=normalized["model_id"],
        task_family=normalized["task_family"],
        task_set_digest=normalized["task_set_digest"],
        held_out_split_digest=normalized["held_out_split_digest"],
        prompt_topology_digest=normalized["prompt_topology_digest"],
        verifier_digest=normalized["verifier_digest"],
        verifier_receipt_id=normalized["verifier_receipt_id"],
        sample_count=normalized["sample_count"],
        accepted_count=normalized["accepted_count"],
        verifier_pass_rate=pass_rate,
        metrics=(metrics or ModelOutcomeMetrics()).normalized(),
    )


def build_model_promotion_evidence_receipt(
    *,
    benchmark_receipt: ModelBenchmarkEvidenceReceipt,
    promotion_state: PromotionState,
    promotion_authority_receipt_id: str,
    signed_promotion_receipt_id: str,
    min_verifier_pass_rate: float,
) -> ModelPromotionEvidenceReceipt:
    """Build a signed-authority promotion receipt over benchmark evidence."""

    threshold = _threshold(min_verifier_pass_rate)
    if promotion_state != PromotionState.CHAMPION:
        raise ValueError("only_champion_promotion_supported")
    if benchmark_receipt.verifier_pass_rate < threshold:
        raise ValueError("benchmark_below_promotion_threshold")
    body = {
        "schema_version": PROMOTION_SCHEMA_VERSION,
        "model_id": benchmark_receipt.model_id,
        "task_family": benchmark_receipt.task_family,
        "benchmark_evidence_receipt_id": benchmark_receipt.receipt_id,
        "promotion_state": promotion_state.value,
        "promotion_authority_receipt_id": _required("promotion_authority_receipt_id", promotion_authority_receipt_id),
        "signed_promotion_receipt_id": _required("signed_promotion_receipt_id", signed_promotion_receipt_id),
        "min_verifier_pass_rate": threshold,
    }
    return ModelPromotionEvidenceReceipt(
        receipt_id=_digest_prefixed("model_promotion_evidence", body),
        model_id=benchmark_receipt.model_id,
        task_family=benchmark_receipt.task_family,
        benchmark_evidence_receipt_id=benchmark_receipt.receipt_id,
        promotion_state=promotion_state,
        promotion_authority_receipt_id=body["promotion_authority_receipt_id"],
        signed_promotion_receipt_id=body["signed_promotion_receipt_id"],
        min_verifier_pass_rate=threshold,
    )


def production_evidence_for_selection(
    benchmark_receipt: ModelBenchmarkEvidenceReceipt,
    promotion_receipt: ModelPromotionEvidenceReceipt,
) -> dict[str, dict[str, Any]]:
    """Convert receipts into the evidence mapping consumed by selection."""

    if promotion_receipt.benchmark_evidence_receipt_id != benchmark_receipt.receipt_id:
        raise ValueError("promotion_benchmark_mismatch")
    if promotion_receipt.model_id != benchmark_receipt.model_id:
        raise ValueError("promotion_model_mismatch")
    if promotion_receipt.task_family != benchmark_receipt.task_family:
        raise ValueError("promotion_task_mismatch")
    return {
        benchmark_receipt.model_id: {
            "model_id": benchmark_receipt.model_id,
            "task_family": benchmark_receipt.task_family,
            "benchmark_evidence_receipt_id": benchmark_receipt.receipt_id,
            "promotion_receipt_id": promotion_receipt.receipt_id,
            "signed_promotion_receipt_id": promotion_receipt.signed_promotion_receipt_id,
            "task_set_digest": benchmark_receipt.task_set_digest,
            "held_out_split_digest": benchmark_receipt.held_out_split_digest,
            "prompt_topology_digest": benchmark_receipt.prompt_topology_digest,
            "verifier_digest": benchmark_receipt.verifier_digest,
            "sample_count": benchmark_receipt.sample_count,
            "verifier_pass_rate": benchmark_receipt.verifier_pass_rate,
            "promotion_state": promotion_receipt.promotion_state.value,
        }
    }


def build_model_selection_outcome_receipt(
    selection_receipt: ModelSelectionReceipt,
    *,
    verifier_decision: VerifierDecision | str,
    verification_receipt_ids: tuple[str, ...] = (),
    task_completed: bool = False,
    evidence_correct: bool = False,
    unauthorized_changes_detected: bool = False,
    regression_detected: bool = False,
    metrics: ModelOutcomeMetrics | None = None,
    rejection_reasons: tuple[str, ...] = (),
    evidence_receipt_ids: tuple[str, ...] = (),
) -> ModelSelectionOutcomeReceipt:
    """Build a fail-closed outcome receipt for a model selection result."""

    verifier = _coerce_verifier_decision(verifier_decision)
    normalized_verification_receipts = _normalize_receipts(verification_receipt_ids)
    normalized_evidence_receipts = _normalize_receipts(evidence_receipt_ids)
    normalized_rejections = tuple(sorted(_clean_reason(reason) for reason in rejection_reasons if str(reason).strip()))
    metrics_value = (metrics or ModelOutcomeMetrics()).normalized()
    automatic_rejections = _automatic_rejection_reasons(
        selection_receipt=selection_receipt,
        verifier_decision=verifier,
        verification_receipt_ids=normalized_verification_receipts,
        task_completed=task_completed,
        evidence_correct=evidence_correct,
        unauthorized_changes_detected=unauthorized_changes_detected,
        regression_detected=regression_detected,
    )
    all_rejections = tuple(sorted(set(normalized_rejections + automatic_rejections)))
    feedback_eligible = not all_rejections
    outcome_decision = OutcomeDecision.ACCEPTED if feedback_eligible else OutcomeDecision.REJECTED
    body = {
        "schema_version": OUTCOME_SCHEMA_VERSION,
        "selection_receipt_id": selection_receipt.receipt_id,
        "catalog_snapshot_id": selection_receipt.catalog_snapshot_id,
        "task_family": selection_receipt.requirements.task_family,
        "selected_model_ids": list(selection_receipt.selected_model_ids),
        "verifier_decision": verifier.value,
        "verification_receipt_ids": list(normalized_verification_receipts),
        "outcome_decision": outcome_decision.value,
        "feedback_eligible": feedback_eligible,
        "metrics": asdict(metrics_value),
        "rejection_reasons": list(all_rejections),
        "evidence_receipt_ids": list(normalized_evidence_receipts),
    }
    return ModelSelectionOutcomeReceipt(
        receipt_id=_digest_prefixed("model_selection_outcome_receipt", body),
        selection_receipt_id=selection_receipt.receipt_id,
        catalog_snapshot_id=selection_receipt.catalog_snapshot_id,
        task_family=selection_receipt.requirements.task_family,
        selected_model_ids=selection_receipt.selected_model_ids,
        verifier_decision=verifier,
        verification_receipt_ids=normalized_verification_receipts,
        outcome_decision=outcome_decision,
        feedback_eligible=feedback_eligible,
        metrics=metrics_value,
        rejection_reasons=all_rejections,
        evidence_receipt_ids=normalized_evidence_receipts,
    )


def outcome_feedback_record(receipt: ModelSelectionOutcomeReceipt) -> dict[str, Any]:
    """Return the minimal record a downstream benchmark ledger may admit."""

    if not receipt.feedback_eligible:
        raise ValueError("outcome_not_feedback_eligible")
    return {
        "outcome_receipt_id": receipt.receipt_id,
        "selection_receipt_id": receipt.selection_receipt_id,
        "catalog_snapshot_id": receipt.catalog_snapshot_id,
        "task_family": receipt.task_family,
        "selected_model_ids": list(receipt.selected_model_ids),
        "verification_receipt_ids": list(receipt.verification_receipt_ids),
        "metrics": asdict(receipt.metrics.normalized()),
    }


def _automatic_rejection_reasons(
    *,
    selection_receipt: ModelSelectionReceipt,
    verifier_decision: VerifierDecision,
    verification_receipt_ids: tuple[str, ...],
    task_completed: bool,
    evidence_correct: bool,
    unauthorized_changes_detected: bool,
    regression_detected: bool,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if selection_receipt.decision != SelectionDecision.SELECTED:
        reasons.append("selection_not_selected")
    if not selection_receipt.selected_model_ids:
        reasons.append("missing_selected_models")
    if verifier_decision != VerifierDecision.ACCEPT:
        reasons.append("verifier_not_accept")
    if not verification_receipt_ids:
        reasons.append("missing_verification_receipts")
    if not task_completed:
        reasons.append("task_not_completed")
    if not evidence_correct:
        reasons.append("evidence_not_verified")
    if unauthorized_changes_detected:
        reasons.append("unauthorized_changes_detected")
    if regression_detected:
        reasons.append("regression_detected")
    return tuple(sorted(set(reasons)))


def _coerce_verifier_decision(value: VerifierDecision | str) -> VerifierDecision:
    if isinstance(value, VerifierDecision):
        return value
    try:
        return VerifierDecision(str(value).strip().lower())
    except ValueError as exc:
        raise ValueError("invalid_verifier_decision") from exc


def _normalize_receipts(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(sorted(str(value).strip() for value in values if str(value).strip()))
    if len(set(normalized)) != len(normalized):
        raise ValueError("duplicate_receipt_ids")
    return normalized


def _required(name: str, value: Any) -> str:
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"missing_{name}")
    return cleaned


def _positive_int(value: int, name: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"invalid_{name}")
    return parsed


def _bounded_accepted_count(value: int, sample_count: int) -> int:
    parsed = int(value)
    if parsed < 0 or parsed > int(sample_count):
        raise ValueError("invalid_accepted_count")
    return parsed


def _threshold(value: float) -> float:
    parsed = float(value)
    if parsed <= 0 or parsed > 1:
        raise ValueError("invalid_verifier_threshold")
    return parsed


def _clean_reason(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _clean_token(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _non_negative_int_or_none(value: int | None) -> int | None:
    if value is None:
        return None
    parsed = int(value)
    if parsed < 0:
        raise ValueError("negative_metric")
    return parsed


def _non_negative_float_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    parsed = float(value)
    if parsed < 0:
        raise ValueError("negative_metric")
    return parsed


def _digest_prefixed(prefix: str, value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"
