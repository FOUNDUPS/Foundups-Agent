"""Rehydrate deterministic inputs for model-runtime binding verification."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .model_intelligence_outcomes import (
    ModelBenchmarkEvidenceReceipt,
    ModelPromotionEvidenceReceipt,
)
from .model_runtime_binding import ModelRuntimeBindingPolicy
from .model_signed_evidence import (
    rehydrate_model_benchmark_evidence_receipt,
    rehydrate_model_promotion_evidence_receipt,
)


def rehydrate_benchmark_evidence(
    values: Sequence[Mapping[str, Any]],
) -> tuple[ModelBenchmarkEvidenceReceipt, ...]:
    if not values:
        raise ValueError("model_benchmark_evidence_missing")
    return tuple(rehydrate_model_benchmark_evidence_receipt(value) for value in values)


def rehydrate_promotion_evidence(
    values: Sequence[Mapping[str, Any]],
    benchmarks: Sequence[ModelBenchmarkEvidenceReceipt],
) -> tuple[ModelPromotionEvidenceReceipt, ...]:
    by_id = {item.receipt_id: item for item in benchmarks}
    result: list[ModelPromotionEvidenceReceipt] = []
    for value in values:
        benchmark = by_id.get(str(value.get("benchmark_evidence_receipt_id") or ""))
        if benchmark is None:
            raise ValueError("model_promotion_benchmark_missing")
        result.append(
            rehydrate_model_promotion_evidence_receipt(
                value, benchmark_receipt=benchmark
            )
        )
    if not result:
        raise ValueError("model_promotion_evidence_missing")
    return tuple(result)


def rehydrate_runtime_policy(
    value: Mapping[str, Any],
) -> ModelRuntimeBindingPolicy:
    return ModelRuntimeBindingPolicy(
        task_family=_required(value, "task_family"),
        runtime_surface=_required(value, "runtime_surface"),
        min_verifier_pass_rate=float(value["min_verifier_pass_rate"]),
        required_task_set_digest=_required(value, "required_task_set_digest"),
        required_held_out_split_digest=_required(
            value, "required_held_out_split_digest"
        ),
        required_verifier_digest=_required(value, "required_verifier_digest"),
        required_panel_topology_digest=_optional(
            value.get("required_panel_topology_digest")
        ),
        authority_receipt_id=_required(value, "authority_receipt_id"),
    ).normalized()


def _required(value: Mapping[str, Any], name: str) -> str:
    result = str(value.get(name) or "").strip()
    if not result:
        raise ValueError(f"{name}_missing")
    return result


def _optional(value: Any) -> str | None:
    result = str(value or "").strip()
    return result or None


__all__ = [
    "rehydrate_benchmark_evidence",
    "rehydrate_promotion_evidence",
    "rehydrate_runtime_policy",
]
