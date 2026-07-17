"""Test helpers for RedDog model runtime binding receipts."""

from __future__ import annotations

import json
from typing import Any

from modules.ai_intelligence.ai_gateway.src.model_intelligence_catalog import (
    ModelCapabilityCard,
    PromotionState,
    build_model_catalog_snapshot,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    ModelOutcomeMetrics,
    build_model_benchmark_evidence_receipt,
    build_model_promotion_evidence_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import (
    ModelTaskRequirements,
    SelectionDecision,
    SelectionPurpose,
    select_models_for_task,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding import (
    ModelRuntimeBindingDecision,
    ModelRuntimeBindingPolicy,
    bind_reddog_runtime_models,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    VerifiedModelProductionEvidence,
)
from modules.ai_intelligence.ai_gateway.tests.model_signed_evidence_test_helpers import (
    make_verified_production_evidence,
)


def model_selection_and_runtime_binding_receipts(
    *,
    runtime_surface: str,
    model_id: str = "openai/gpt-5.6-code",
    task_family: str = "reddog_runtime_model_call",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build matching model-selection and runtime-binding receipts for tests."""

    task_set_digest = "sha256:task-set"
    held_out_digest = "sha256:held-out"
    verifier_digest = "sha256:verifier"
    card = ModelCapabilityCard(
        provider=model_id.split("/", 1)[0],
        model_id=model_id,
        canonical_model_id=model_id,
        source="test",
        promotion_state=PromotionState.CHAMPION,
        task_families=(task_family,),
        supports_structured_output=True,
        supports_reasoning=True,
        benchmark_scores={task_family: 0.95},
        verifier_pass_rate=0.95,
    ).normalized()
    snapshot = build_model_catalog_snapshot((card,), generated_at="2026-07-16T00:00:00+00:00")
    benchmark = build_model_benchmark_evidence_receipt(
        model_id=model_id,
        task_family=task_family,
        task_set_digest=task_set_digest,
        held_out_split_digest=held_out_digest,
        prompt_topology_digest="sha256:topology",
        verifier_digest=verifier_digest,
        verifier_receipt_id="sha256:verifier-receipt",
        sample_count=20,
        accepted_count=20,
        metrics=ModelOutcomeMetrics(latency_ms=100, input_tokens=10, output_tokens=20),
    )
    promotion = build_model_promotion_evidence_receipt(
        benchmark_receipt=benchmark,
        promotion_state=PromotionState.CHAMPION,
        promotion_authority_receipt_id="sha256:promotion-authority",
        signed_promotion_receipt_id="signature:promotion",
        min_verifier_pass_rate=0.9,
    )
    provisional = make_verified_production_evidence(
        benchmark,
        promotion,
        catalog_snapshot_id=snapshot.snapshot_id,
    )
    first_selection = select_models_for_task(
        snapshot,
        ModelTaskRequirements(
            task_family=task_family,
            purpose=SelectionPurpose.PRODUCTION,
            min_verifier_pass_rate=0.9,
            require_structured_output=True,
            require_reasoning=True,
        ),
        production_evidence=provisional,
    )
    verified = make_verified_production_evidence(
        benchmark,
        promotion,
        catalog_snapshot_id=snapshot.snapshot_id,
        selection_receipt_id=first_selection.receipt_id,
    )
    evidence = VerifiedModelProductionEvidence(entries=tuple(verified.entries))
    selection = select_models_for_task(
        snapshot,
        first_selection.requirements,
        production_evidence=evidence,
    )
    receipt = bind_reddog_runtime_models(
        catalog_snapshot=snapshot,
        selection_receipt=selection,
        benchmark_evidence_receipts=(benchmark,),
        promotion_evidence_receipts=(promotion,),
        policy=ModelRuntimeBindingPolicy(
            task_family=task_family,
            runtime_surface=runtime_surface,
            min_verifier_pass_rate=0.9,
            required_task_set_digest=task_set_digest,
            required_held_out_split_digest=held_out_digest,
            required_verifier_digest=verifier_digest,
            authority_receipt_id="runtime-authority:test",
        ),
        verified_production_evidence=evidence,
    )
    assert selection.decision == SelectionDecision.SELECTED
    assert receipt.decision == ModelRuntimeBindingDecision.BOUND
    return _json_normalized(selection.to_dict()), _json_normalized(receipt.to_dict())


def model_runtime_binding_receipt(
    *,
    runtime_surface: str,
    model_id: str = "openai/gpt-5.6-code",
    task_family: str = "reddog_runtime_model_call",
) -> dict[str, Any]:
    """Build a valid single-model runtime binding receipt for runtime tests."""

    _, receipt = model_selection_and_runtime_binding_receipts(
        runtime_surface=runtime_surface,
        model_id=model_id,
        task_family=task_family,
    )
    return receipt


def _json_normalized(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, sort_keys=True, default=str))
