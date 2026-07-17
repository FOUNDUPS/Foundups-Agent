"""Champion/challenger promotion gate for model intelligence.

The gate validates benchmark-run evidence and, only when signed promotion
authority is supplied, emits a promotion evidence receipt. It does not mutate
the model catalog, write a champion ledger, call providers, or bind RedDog
runtime defaults.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping

from .model_combination_benchmark_harness import ModelCombinationBenchmarkRunReceipt
from .model_intelligence_catalog import PromotionState
from .model_intelligence_outcomes import (
    ModelBenchmarkEvidenceReceipt,
    ModelPromotionEvidenceReceipt,
    build_model_promotion_evidence_receipt,
)


PROMOTION_GATE_SCHEMA_VERSION = "model_promotion_gate_receipt.v1"
PROMOTION_POLICY_SCHEMA_VERSION = "model_promotion_policy.v1"


class ModelPromotionGateDecision(str, Enum):
    """Decision emitted by the benchmark promotion gate."""

    PROMOTE_CHAMPION = "promote_champion"
    KEEP_CHALLENGER = "keep_challenger"
    REJECT = "reject"


@dataclass(frozen=True)
class ModelPromotionPolicy:
    """Explicit policy for champion/challenger evaluation."""

    task_family: str
    candidate_id: str
    min_verifier_pass_rate: float
    min_sample_count: int
    required_task_set_digest: str
    required_held_out_split_digest: str
    required_verifier_digest: str
    max_latency_ms: int | None = None
    max_cost_estimate_usd: float | None = None
    schema_version: str = PROMOTION_POLICY_SCHEMA_VERSION

    def normalized(self) -> "ModelPromotionPolicy":
        return ModelPromotionPolicy(
            task_family=_clean_token(_required("task_family", self.task_family)),
            candidate_id=_required("candidate_id", self.candidate_id),
            min_verifier_pass_rate=_threshold(self.min_verifier_pass_rate),
            min_sample_count=_positive_int(self.min_sample_count, "min_sample_count"),
            required_task_set_digest=_required("required_task_set_digest", self.required_task_set_digest),
            required_held_out_split_digest=_required(
                "required_held_out_split_digest",
                self.required_held_out_split_digest,
            ),
            required_verifier_digest=_required("required_verifier_digest", self.required_verifier_digest),
            max_latency_ms=_positive_int_or_none(self.max_latency_ms, "max_latency_ms"),
            max_cost_estimate_usd=_positive_float_or_none(
                self.max_cost_estimate_usd,
                "max_cost_estimate_usd",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        policy = self.normalized()
        return {
            "schema_version": policy.schema_version,
            "task_family": policy.task_family,
            "candidate_id": policy.candidate_id,
            "min_verifier_pass_rate": policy.min_verifier_pass_rate,
            "min_sample_count": policy.min_sample_count,
            "required_task_set_digest": policy.required_task_set_digest,
            "required_held_out_split_digest": policy.required_held_out_split_digest,
            "required_verifier_digest": policy.required_verifier_digest,
            "max_latency_ms": policy.max_latency_ms,
            "max_cost_estimate_usd": policy.max_cost_estimate_usd,
        }


@dataclass(frozen=True)
class ModelPromotionGateReceipt:
    """Digest-bound promotion gate result."""

    receipt_id: str
    decision: ModelPromotionGateDecision
    candidate_id: str
    task_family: str
    benchmark_run_receipt_id: str
    benchmark_evidence_receipt_id: str | None
    policy: ModelPromotionPolicy
    promotion_evidence_receipt: ModelPromotionEvidenceReceipt | None = None
    rejection_reasons: tuple[str, ...] = ()
    schema_version: str = PROMOTION_GATE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "decision": self.decision.value,
            "candidate_id": self.candidate_id,
            "task_family": self.task_family,
            "benchmark_run_receipt_id": self.benchmark_run_receipt_id,
            "benchmark_evidence_receipt_id": self.benchmark_evidence_receipt_id,
            "policy": self.policy.to_dict(),
            "promotion_evidence_receipt": (
                self.promotion_evidence_receipt.to_dict() if self.promotion_evidence_receipt else None
            ),
            "rejection_reasons": list(self.rejection_reasons),
        }


def evaluate_model_promotion_gate(
    *,
    benchmark_run_receipt: ModelCombinationBenchmarkRunReceipt,
    policy: ModelPromotionPolicy,
    promotion_authority_receipt_id: str | None = None,
    signed_promotion_receipt_id: str | None = None,
) -> ModelPromotionGateReceipt:
    """Evaluate one benchmark candidate for champion/challenger promotion."""

    normalized_policy = policy.normalized()
    benchmark_run_receipt_id = _digest_prefixed(
        "model_combination_benchmark_run_projection",
        _benchmark_run_projection(benchmark_run_receipt),
    )
    evidence = _find_candidate_evidence(benchmark_run_receipt, normalized_policy.candidate_id)
    rejections = _evidence_rejections(benchmark_run_receipt, normalized_policy, evidence)
    promotion_evidence: ModelPromotionEvidenceReceipt | None = None
    decision = ModelPromotionGateDecision.REJECT
    if evidence and not rejections:
        if evidence.verifier_pass_rate < normalized_policy.min_verifier_pass_rate:
            decision = ModelPromotionGateDecision.KEEP_CHALLENGER
            rejections.append("verifier_pass_rate_below_champion_threshold")
        elif not promotion_authority_receipt_id or not str(promotion_authority_receipt_id).strip():
            rejections.append("missing_promotion_authority_receipt")
        elif not signed_promotion_receipt_id or not str(signed_promotion_receipt_id).strip():
            rejections.append("missing_signed_promotion_receipt")
        else:
            promotion_evidence = build_model_promotion_evidence_receipt(
                benchmark_receipt=evidence,
                promotion_state=PromotionState.CHAMPION,
                promotion_authority_receipt_id=promotion_authority_receipt_id,
                signed_promotion_receipt_id=signed_promotion_receipt_id,
                min_verifier_pass_rate=normalized_policy.min_verifier_pass_rate,
            )
            decision = ModelPromotionGateDecision.PROMOTE_CHAMPION
    body = {
        "schema_version": PROMOTION_GATE_SCHEMA_VERSION,
        "decision": decision.value,
        "candidate_id": normalized_policy.candidate_id,
        "task_family": normalized_policy.task_family,
        "benchmark_run_receipt_id": benchmark_run_receipt_id,
        "benchmark_evidence_receipt_id": evidence.receipt_id if evidence else None,
        "policy": normalized_policy.to_dict(),
        "promotion_evidence_receipt_id": promotion_evidence.receipt_id if promotion_evidence else None,
        "rejection_reasons": sorted(set(rejections)),
    }
    return ModelPromotionGateReceipt(
        receipt_id=_digest_prefixed("model_promotion_gate", body),
        decision=decision,
        candidate_id=normalized_policy.candidate_id,
        task_family=normalized_policy.task_family,
        benchmark_run_receipt_id=benchmark_run_receipt_id,
        benchmark_evidence_receipt_id=evidence.receipt_id if evidence else None,
        policy=normalized_policy,
        promotion_evidence_receipt=promotion_evidence,
        rejection_reasons=tuple(sorted(set(rejections))),
    )


def rehydrate_model_promotion_policy(data: Mapping[str, Any]) -> ModelPromotionPolicy:
    """Rehydrate a serialized promotion policy and normalize its fields."""

    if not isinstance(data, Mapping):
        raise ValueError("invalid_promotion_policy")
    if data.get("schema_version") != PROMOTION_POLICY_SCHEMA_VERSION:
        raise ValueError("invalid_promotion_policy_schema")
    return ModelPromotionPolicy(
        task_family=_required("task_family", data.get("task_family")),
        candidate_id=_required("candidate_id", data.get("candidate_id")),
        min_verifier_pass_rate=float(data.get("min_verifier_pass_rate")),
        min_sample_count=int(data.get("min_sample_count")),
        required_task_set_digest=_required("required_task_set_digest", data.get("required_task_set_digest")),
        required_held_out_split_digest=_required(
            "required_held_out_split_digest",
            data.get("required_held_out_split_digest"),
        ),
        required_verifier_digest=_required("required_verifier_digest", data.get("required_verifier_digest")),
        max_latency_ms=_optional_int(data.get("max_latency_ms")),
        max_cost_estimate_usd=_optional_float(data.get("max_cost_estimate_usd")),
    ).normalized()


def rehydrate_model_promotion_evidence_receipt(
    data: Mapping[str, Any],
) -> ModelPromotionEvidenceReceipt:
    """Rehydrate promotion evidence and recompute its deterministic ID."""

    if not isinstance(data, Mapping):
        raise ValueError("invalid_promotion_evidence")
    if data.get("schema_version") != "model_promotion_evidence_receipt.v1":
        raise ValueError("invalid_promotion_evidence_schema")
    promotion_state = PromotionState(_required("promotion_state", data.get("promotion_state")))
    threshold = _threshold(float(data.get("min_verifier_pass_rate")))
    body = {
        "schema_version": "model_promotion_evidence_receipt.v1",
        "model_id": _required("model_id", data.get("model_id")),
        "task_family": _clean_token(_required("task_family", data.get("task_family"))),
        "benchmark_evidence_receipt_id": _required(
            "benchmark_evidence_receipt_id",
            data.get("benchmark_evidence_receipt_id"),
        ),
        "promotion_state": promotion_state.value,
        "promotion_authority_receipt_id": _required(
            "promotion_authority_receipt_id",
            data.get("promotion_authority_receipt_id"),
        ),
        "signed_promotion_receipt_id": _required(
            "signed_promotion_receipt_id",
            data.get("signed_promotion_receipt_id"),
        ),
        "min_verifier_pass_rate": threshold,
    }
    receipt_id = _digest_prefixed("model_promotion_evidence", body)
    if not hmac.compare_digest(receipt_id, _required("receipt_id", data.get("receipt_id"))):
        raise ValueError("promotion_evidence_receipt_id_mismatch")
    return ModelPromotionEvidenceReceipt(
        receipt_id=receipt_id,
        model_id=body["model_id"],
        task_family=body["task_family"],
        benchmark_evidence_receipt_id=body["benchmark_evidence_receipt_id"],
        promotion_state=promotion_state,
        promotion_authority_receipt_id=body["promotion_authority_receipt_id"],
        signed_promotion_receipt_id=body["signed_promotion_receipt_id"],
        min_verifier_pass_rate=threshold,
    )


def rehydrate_model_promotion_gate_receipt(data: Mapping[str, Any]) -> ModelPromotionGateReceipt:
    """Rehydrate a serialized promotion gate receipt and recompute its ID."""

    if not isinstance(data, Mapping):
        raise ValueError("invalid_promotion_gate_receipt")
    if data.get("schema_version") != PROMOTION_GATE_SCHEMA_VERSION:
        raise ValueError("invalid_promotion_gate_schema")
    policy = rehydrate_model_promotion_policy(_mapping(data.get("policy"), "policy"))
    decision = ModelPromotionGateDecision(_required("decision", data.get("decision")))
    candidate_id = _required("candidate_id", data.get("candidate_id"))
    task_family = _clean_token(_required("task_family", data.get("task_family")))
    benchmark_run_receipt_id = _required(
        "benchmark_run_receipt_id",
        data.get("benchmark_run_receipt_id"),
    )
    benchmark_evidence_receipt_id = _optional(data.get("benchmark_evidence_receipt_id"))
    promotion_evidence = None
    promotion_raw = data.get("promotion_evidence_receipt")
    if promotion_raw is not None:
        promotion_evidence = rehydrate_model_promotion_evidence_receipt(
            _mapping(promotion_raw, "promotion_evidence_receipt")
        )
    if decision == ModelPromotionGateDecision.PROMOTE_CHAMPION and promotion_evidence is None:
        raise ValueError("promotion_evidence_missing")
    if promotion_evidence is not None:
        if promotion_evidence.model_id != candidate_id:
            raise ValueError("promotion_evidence_candidate_mismatch")
        if promotion_evidence.task_family != task_family:
            raise ValueError("promotion_evidence_task_family_mismatch")
        if promotion_evidence.benchmark_evidence_receipt_id != benchmark_evidence_receipt_id:
            raise ValueError("promotion_evidence_benchmark_mismatch")
    rejection_reasons = tuple(
        sorted(
            _clean_token(reason)
            for reason in _list(data.get("rejection_reasons", []))
            if str(reason).strip()
        )
    )
    body = {
        "schema_version": PROMOTION_GATE_SCHEMA_VERSION,
        "decision": decision.value,
        "candidate_id": candidate_id,
        "task_family": task_family,
        "benchmark_run_receipt_id": benchmark_run_receipt_id,
        "benchmark_evidence_receipt_id": benchmark_evidence_receipt_id,
        "policy": policy.to_dict(),
        "promotion_evidence_receipt_id": promotion_evidence.receipt_id if promotion_evidence else None,
        "rejection_reasons": sorted(set(rejection_reasons)),
    }
    receipt_id = _digest_prefixed("model_promotion_gate", body)
    if not hmac.compare_digest(receipt_id, _required("receipt_id", data.get("receipt_id"))):
        raise ValueError("promotion_gate_receipt_id_mismatch")
    return ModelPromotionGateReceipt(
        receipt_id=receipt_id,
        decision=decision,
        candidate_id=candidate_id,
        task_family=task_family,
        benchmark_run_receipt_id=benchmark_run_receipt_id,
        benchmark_evidence_receipt_id=benchmark_evidence_receipt_id,
        policy=policy,
        promotion_evidence_receipt=promotion_evidence,
        rejection_reasons=rejection_reasons,
    )


def _find_candidate_evidence(
    benchmark_run_receipt: ModelCombinationBenchmarkRunReceipt,
    candidate_id: str,
) -> ModelBenchmarkEvidenceReceipt | None:
    matches = [
        evidence for evidence in benchmark_run_receipt.benchmark_evidence_receipts if evidence.model_id == candidate_id
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def _evidence_rejections(
    benchmark_run_receipt: ModelCombinationBenchmarkRunReceipt,
    policy: ModelPromotionPolicy,
    evidence: ModelBenchmarkEvidenceReceipt | None,
) -> list[str]:
    reasons: list[str] = []
    if evidence is None:
        return ["benchmark_evidence_missing_or_ambiguous"]
    if benchmark_run_receipt.task_family != policy.task_family:
        reasons.append("task_family_mismatch")
    if benchmark_run_receipt.task_set_digest != policy.required_task_set_digest:
        reasons.append("task_set_digest_mismatch")
    if benchmark_run_receipt.held_out_split_digest != policy.required_held_out_split_digest:
        reasons.append("held_out_split_digest_mismatch")
    if benchmark_run_receipt.verifier_digest != policy.required_verifier_digest:
        reasons.append("verifier_digest_mismatch")
    if evidence.task_family != policy.task_family:
        reasons.append("evidence_task_family_mismatch")
    if evidence.task_set_digest != benchmark_run_receipt.task_set_digest:
        reasons.append("evidence_task_set_digest_mismatch")
    if evidence.held_out_split_digest != benchmark_run_receipt.held_out_split_digest:
        reasons.append("evidence_held_out_split_digest_mismatch")
    if evidence.verifier_digest != benchmark_run_receipt.verifier_digest:
        reasons.append("evidence_verifier_digest_mismatch")
    if evidence.sample_count < policy.min_sample_count:
        reasons.append("sample_count_below_policy")
    if policy.max_latency_ms is not None and evidence.metrics.latency_ms is not None:
        if evidence.metrics.latency_ms > policy.max_latency_ms:
            reasons.append("latency_above_policy")
    if policy.max_cost_estimate_usd is not None and evidence.metrics.cost_estimate_usd is not None:
        if evidence.metrics.cost_estimate_usd > policy.max_cost_estimate_usd:
            reasons.append("cost_above_policy")
    return reasons


def _benchmark_run_projection(receipt: ModelCombinationBenchmarkRunReceipt) -> dict[str, Any]:
    return {
        "schema_version": receipt.schema_version,
        "task_family": receipt.task_family,
        "task_set_digest": receipt.task_set_digest,
        "held_out_split_digest": receipt.held_out_split_digest,
        "verifier_digest": receipt.verifier_digest,
        "candidates": [candidate.to_dict() for candidate in receipt.candidates],
        "benchmark_evidence_receipts": [
            evidence.to_dict() for evidence in receipt.benchmark_evidence_receipts
        ],
    }


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name}_missing")
    return value


def _list(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return (value,)


def _required(name: str, value: Any) -> str:
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"missing_{name}")
    return cleaned


def _optional(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _threshold(value: float) -> float:
    parsed = float(value)
    if parsed <= 0 or parsed > 1:
        raise ValueError("invalid_verifier_threshold")
    return parsed


def _positive_int(value: int, name: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"invalid_{name}")
    return parsed


def _positive_int_or_none(value: int | None, name: str) -> int | None:
    if value is None:
        return None
    return _positive_int(value, name)


def _positive_float_or_none(value: float | None, name: str) -> float | None:
    if value is None:
        return None
    parsed = float(value)
    if parsed <= 0:
        raise ValueError(f"invalid_{name}")
    return parsed


def _clean_token(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _digest_prefixed(prefix: str, value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"
