"""Test helpers for RedDog model runtime binding receipts."""

from __future__ import annotations

import json
import hashlib
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
    SelectionMode,
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
    panel_model_ids: tuple[str, ...] = (),
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build matching model-selection and runtime-binding receipts for tests."""

    task_set_digest = "sha256:task-set"
    held_out_digest = "sha256:held-out"
    verifier_digest = "sha256:verifier"
    model_ids = (model_id, *panel_model_ids)
    cards = tuple(
        ModelCapabilityCard(
            provider=candidate.split("/", 1)[0],
            model_id=candidate,
            canonical_model_id=candidate,
            source="test",
            promotion_state=PromotionState.CHAMPION,
            task_families=(task_family,),
            supports_structured_output=True,
            supports_reasoning=True,
            benchmark_scores={task_family: 0.99 - index * 0.01},
            verifier_pass_rate=0.99 - index * 0.01,
        ).normalized()
        for index, candidate in enumerate(model_ids)
    )
    snapshot = build_model_catalog_snapshot(cards, generated_at="2026-07-16T00:00:00+00:00")
    benchmarks = tuple(
        build_model_benchmark_evidence_receipt(
            model_id=candidate,
            task_family=task_family,
            task_set_digest=task_set_digest,
            held_out_split_digest=held_out_digest,
            prompt_topology_digest="sha256:topology",
            verifier_digest=verifier_digest,
            verifier_receipt_id=f"sha256:verifier-receipt-{index}",
            sample_count=20,
            accepted_count=20,
            metrics=ModelOutcomeMetrics(latency_ms=100 + index, input_tokens=10, output_tokens=20),
        )
        for index, candidate in enumerate(model_ids)
    )
    promotions = tuple(
        build_model_promotion_evidence_receipt(
            benchmark_receipt=benchmark,
            promotion_state=PromotionState.CHAMPION,
            promotion_authority_receipt_id="sha256:promotion-authority",
            signed_promotion_receipt_id=f"signature:promotion-{index}",
            min_verifier_pass_rate=0.9,
        )
        for index, benchmark in enumerate(benchmarks)
    )
    provisional = VerifiedModelProductionEvidence(
        entries=tuple(
            entry
            for benchmark, promotion in zip(benchmarks, promotions)
            for entry in make_verified_production_evidence(
                benchmark,
                promotion,
                catalog_snapshot_id=snapshot.snapshot_id,
            ).entries
        )
    )
    first_selection = select_models_for_task(
        snapshot,
        ModelTaskRequirements(
            task_family=task_family,
            selection_mode=SelectionMode.PANEL if panel_model_ids else SelectionMode.SINGLE,
            purpose=SelectionPurpose.PRODUCTION,
            min_verifier_pass_rate=0.9,
            require_structured_output=True,
            require_reasoning=True,
            max_candidates=len(model_ids),
            panel_roles=("principal", *(f"critic_{index}" for index in range(1, len(model_ids)))),
        ),
        production_evidence=provisional,
    )
    verified = VerifiedModelProductionEvidence(
        entries=tuple(
            entry
            for benchmark, promotion in zip(benchmarks, promotions)
            for entry in make_verified_production_evidence(
                benchmark,
                promotion,
                catalog_snapshot_id=snapshot.snapshot_id,
                selection_receipt_id=first_selection.receipt_id,
            ).entries
        )
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
        benchmark_evidence_receipts=benchmarks,
        promotion_evidence_receipts=promotions,
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
    runtime_dict = _json_normalized(receipt.to_dict())
    if panel_model_ids:
        runtime_dict.update(
            {
                "decision": ModelRuntimeBindingDecision.BOUND.value,
                "principal_model": model_id,
                "panel_models": list(panel_model_ids),
                "role_bindings": [
                    {"role": "principal", "model_id": model_id, "provider": model_id.split("/", 1)[0]},
                    *[
                        {
                            "role": f"critic_{index}",
                            "model_id": candidate,
                            "provider": candidate.split("/", 1)[0],
                        }
                        for index, candidate in enumerate(panel_model_ids, start=1)
                    ],
                ],
                "rejection_reasons": [],
            }
        )
        body = {key: value for key, value in runtime_dict.items() if key != "receipt_id"}
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        runtime_dict["receipt_id"] = "reddog_model_runtime_binding:" + hashlib.sha256(encoded).hexdigest()
    else:
        assert receipt.decision == ModelRuntimeBindingDecision.BOUND
    return _json_normalized(selection.to_dict()), runtime_dict


def model_runtime_binding_receipt(
    *,
    runtime_surface: str,
    model_id: str = "openai/gpt-5.6-code",
    task_family: str = "reddog_runtime_model_call",
    panel_model_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Build a valid single-model runtime binding receipt for runtime tests."""

    _, receipt = model_selection_and_runtime_binding_receipts(
        runtime_surface=runtime_surface,
        model_id=model_id,
        task_family=task_family,
        panel_model_ids=panel_model_ids,
    )
    return receipt


def _json_normalized(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, sort_keys=True, default=str))
