"""Tests for model benchmark evidence and outcome receipts."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_intelligence_catalog import (
    ModelCapabilityCard,
    PromotionState,
    build_model_catalog_snapshot,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    ModelOutcomeMetrics,
    OutcomeDecision,
    VerifierDecision,
    build_model_benchmark_evidence_receipt,
    build_model_promotion_evidence_receipt,
    build_model_selection_outcome_receipt,
    outcome_feedback_record,
    production_evidence_for_selection,
    rehydrate_model_selection_outcome_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import (
    ModelTaskRequirements,
    SelectionDecision,
    SelectionPurpose,
    select_models_for_task,
)
from model_signed_evidence_test_helpers import make_verified_production_evidence


def _selected_receipt():
    snapshot = build_model_catalog_snapshot(
        (
            ModelCapabilityCard(
                provider="provider",
                model_id="provider/model",
                canonical_model_id="provider/model",
                source="test",
                promotion_state=PromotionState.CANDIDATE,
                task_families=("architecture",),
            ).normalized(),
        ),
        generated_at="2026-07-16T00:00:00+00:00",
    )
    receipt = select_models_for_task(snapshot, ModelTaskRequirements(task_family="architecture"))
    assert receipt.decision == SelectionDecision.SELECTED
    return receipt


def _digest(value) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _runtime_binding_receipt(selection):
    return {
        "schema_version": "reddog_model_runtime_binding_receipt.v1",
        "receipt_id": "reddog_model_runtime_binding:test",
        "decision": "bound",
        "runtime_surface": "backend_architect",
        "catalog_snapshot_id": selection.catalog_snapshot_id,
        "selection_receipt_id": selection.receipt_id,
        "task_family": selection.requirements.task_family,
        "principal_model": selection.selected_model_ids[0],
        "panel_models": [],
        "role_bindings": [
            {
                "role": "principal",
                "model_id": selection.selected_model_ids[0],
                "provider": "provider",
            }
        ],
        "benchmark_evidence_receipt_ids": ["model_benchmark_evidence:test"],
        "promotion_evidence_receipt_ids": ["model_promotion_evidence:test"],
        "signed_promotion_receipt_ids": ["signature:test"],
        "policy": {
            "schema_version": "reddog_model_runtime_binding_policy.v1",
            "task_family": selection.requirements.task_family,
            "runtime_surface": "backend_architect",
            "min_verifier_pass_rate": 0.9,
            "required_task_set_digest": "sha256:taskset",
            "required_held_out_split_digest": "sha256:heldout",
            "required_verifier_digest": "sha256:verifier",
            "max_panel_models": 4,
            "required_panel_topology_digest": None,
            "authority_receipt_id": "authority:test",
        },
        "rejection_reasons": [],
    }


def test_benchmark_evidence_binds_held_out_task_set_verifier_topology_and_metrics():
    receipt = build_model_benchmark_evidence_receipt(
        model_id="provider/model",
        task_family="architecture",
        task_set_digest="sha256:taskset",
        held_out_split_digest="sha256:heldout",
        prompt_topology_digest="sha256:topology",
        verifier_digest="sha256:verifier",
        verifier_receipt_id="verifier:1",
        sample_count=25,
        accepted_count=23,
        metrics=ModelOutcomeMetrics(latency_ms=1000, input_tokens=200, output_tokens=100, cost_estimate_usd=0.12),
    )

    assert receipt.receipt_id.startswith("model_benchmark_evidence:")
    assert receipt.verifier_pass_rate == 0.92
    assert receipt.task_set_digest == "sha256:taskset"
    assert receipt.held_out_split_digest == "sha256:heldout"
    assert receipt.prompt_topology_digest == "sha256:topology"
    assert receipt.verifier_digest == "sha256:verifier"


def test_benchmark_evidence_rejects_missing_digest_and_bad_sample_counts():
    for kwargs in (
        {"task_set_digest": ""},
        {"sample_count": 0},
        {"accepted_count": 6, "sample_count": 5},
    ):
        base = {
            "model_id": "provider/model",
            "task_family": "architecture",
            "task_set_digest": "sha256:taskset",
            "held_out_split_digest": "sha256:heldout",
            "prompt_topology_digest": "sha256:topology",
            "verifier_digest": "sha256:verifier",
            "verifier_receipt_id": "verifier:1",
            "sample_count": 5,
            "accepted_count": 4,
        }
        base.update(kwargs)
        try:
            build_model_benchmark_evidence_receipt(**base)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected rejection for {kwargs}")


def test_promotion_evidence_requires_signed_authority_and_threshold():
    benchmark = build_model_benchmark_evidence_receipt(
        model_id="provider/model",
        task_family="architecture",
        task_set_digest="sha256:taskset",
        held_out_split_digest="sha256:heldout",
        prompt_topology_digest="sha256:topology",
        verifier_digest="sha256:verifier",
        verifier_receipt_id="verifier:1",
        sample_count=10,
        accepted_count=10,
    )

    promotion = build_model_promotion_evidence_receipt(
        benchmark_receipt=benchmark,
        promotion_state=PromotionState.CHAMPION,
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signature:1",
        min_verifier_pass_rate=0.95,
    )

    assert promotion.receipt_id.startswith("model_promotion_evidence:")
    assert promotion.signed_promotion_receipt_id == "signature:1"

    try:
        build_model_promotion_evidence_receipt(
            benchmark_receipt=benchmark,
            promotion_state=PromotionState.CHAMPION,
            promotion_authority_receipt_id="authority:1",
            signed_promotion_receipt_id="",
            min_verifier_pass_rate=0.95,
        )
    except ValueError as exc:
        assert str(exc) == "missing_signed_promotion_receipt_id"
    else:
        raise AssertionError("expected missing signature rejection")


def test_verified_production_evidence_feeds_hardened_selection():
    benchmark = build_model_benchmark_evidence_receipt(
        model_id="provider/model",
        task_family="architecture",
        task_set_digest="sha256:taskset",
        held_out_split_digest="sha256:heldout",
        prompt_topology_digest="sha256:topology",
        verifier_digest="sha256:verifier",
        verifier_receipt_id="verifier:1",
        sample_count=10,
        accepted_count=9,
    )
    promotion = build_model_promotion_evidence_receipt(
        benchmark_receipt=benchmark,
        promotion_state=PromotionState.CHAMPION,
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signature:1",
        min_verifier_pass_rate=0.9,
    )
    snapshot = build_model_catalog_snapshot(
        (
            ModelCapabilityCard(
                provider="provider",
                model_id="provider/model",
                canonical_model_id="provider/model",
                source="test",
                promotion_state=PromotionState.CHAMPION,
                task_families=("architecture",),
            ).normalized(),
        ),
        generated_at="2026-07-16T00:00:00+00:00",
    )

    verified_evidence = make_verified_production_evidence(
        benchmark,
        promotion,
        catalog_snapshot_id=snapshot.snapshot_id,
    )
    receipt = select_models_for_task(
        snapshot,
        ModelTaskRequirements(
            task_family="architecture",
            purpose=SelectionPurpose.PRODUCTION,
            min_verifier_pass_rate=0.9,
        ),
        production_evidence=verified_evidence,
    )

    assert receipt.selected_model_ids == ("provider/model",)


def test_legacy_production_evidence_map_is_rejected_by_selection():
    benchmark = build_model_benchmark_evidence_receipt(
        model_id="provider/model",
        task_family="architecture",
        task_set_digest="sha256:taskset",
        held_out_split_digest="sha256:heldout",
        prompt_topology_digest="sha256:topology",
        verifier_digest="sha256:verifier",
        verifier_receipt_id="verifier:1",
        sample_count=10,
        accepted_count=9,
    )
    promotion = build_model_promotion_evidence_receipt(
        benchmark_receipt=benchmark,
        promotion_state=PromotionState.CHAMPION,
        promotion_authority_receipt_id="authority:1",
        signed_promotion_receipt_id="signature:1",
        min_verifier_pass_rate=0.9,
    )
    snapshot = build_model_catalog_snapshot(
        (
            ModelCapabilityCard(
                provider="provider",
                model_id="provider/model",
                canonical_model_id="provider/model",
                source="test",
                promotion_state=PromotionState.CHAMPION,
                task_families=("architecture",),
            ).normalized(),
        ),
        generated_at="2026-07-16T00:00:00+00:00",
    )

    receipt = select_models_for_task(
        snapshot,
        ModelTaskRequirements(
            task_family="architecture",
            purpose=SelectionPurpose.PRODUCTION,
            min_verifier_pass_rate=0.9,
        ),
        production_evidence=production_evidence_for_selection(benchmark, promotion),
    )

    assert receipt.selected_model_ids == ()
    assert "production_evidence_not_authenticated:1" in receipt.rejection_reasons


def test_outcome_receipt_accepts_only_verified_complete_results():
    selection = _selected_receipt()
    receipt = build_model_selection_outcome_receipt(
        selection,
        verifier_decision=VerifierDecision.ACCEPT,
        verification_receipt_ids=("verify:1",),
        task_completed=True,
        evidence_correct=True,
        metrics=ModelOutcomeMetrics(latency_ms=100),
    )

    assert receipt.outcome_decision == OutcomeDecision.ACCEPTED
    assert receipt.feedback_eligible is True
    feedback = outcome_feedback_record(receipt)
    assert feedback["outcome_receipt_id"] == receipt.receipt_id
    assert feedback["model_runtime_binding_receipt_id"] is None
    assert feedback["model_runtime_binding_digest"] == ""


def test_outcome_feedback_record_carries_runtime_binding_receipt_digest():
    selection = _selected_receipt()
    runtime_binding = _runtime_binding_receipt(selection)
    receipt = build_model_selection_outcome_receipt(
        selection,
        model_runtime_binding_receipt=runtime_binding,
        verifier_decision=VerifierDecision.ACCEPT,
        verification_receipt_ids=("verify:1",),
        task_completed=True,
        evidence_correct=True,
    )

    assert receipt.feedback_eligible is True
    assert receipt.model_runtime_binding_receipt_id == "reddog_model_runtime_binding:test"
    assert receipt.model_runtime_binding_digest == _digest(runtime_binding)
    feedback = outcome_feedback_record(receipt)
    assert feedback["model_runtime_binding_receipt_id"] == "reddog_model_runtime_binding:test"
    assert feedback["model_runtime_binding_digest"] == _digest(runtime_binding)


def test_rehydrate_outcome_receipt_recomputes_digest_and_preserves_runtime_binding():
    selection = _selected_receipt()
    runtime_binding = _runtime_binding_receipt(selection)
    receipt = build_model_selection_outcome_receipt(
        selection,
        model_runtime_binding_receipt=runtime_binding,
        verifier_decision=VerifierDecision.ACCEPT,
        verification_receipt_ids=("verify:1",),
        task_completed=True,
        evidence_correct=True,
    )

    rehydrated = rehydrate_model_selection_outcome_receipt(receipt.to_dict())

    assert rehydrated == receipt
    assert rehydrated.model_runtime_binding_receipt_id == "reddog_model_runtime_binding:test"
    assert rehydrated.model_runtime_binding_digest == _digest(runtime_binding)


def test_rehydrate_outcome_receipt_rejects_tampering_and_inconsistent_feedback_state():
    selection = _selected_receipt()
    receipt = build_model_selection_outcome_receipt(
        selection,
        verifier_decision=VerifierDecision.ACCEPT,
        verification_receipt_ids=("verify:1",),
        task_completed=True,
        evidence_correct=True,
    ).to_dict()

    tampered_model = dict(receipt)
    tampered_model["selected_model_ids"] = ["provider/other"]
    try:
        rehydrate_model_selection_outcome_receipt(tampered_model)
    except ValueError as exc:
        assert str(exc) == "outcome_receipt_id_mismatch"
    else:
        raise AssertionError("expected tampered outcome receipt rejection")

    inconsistent = dict(receipt)
    inconsistent["feedback_eligible"] = False
    try:
        rehydrate_model_selection_outcome_receipt(inconsistent)
    except ValueError as exc:
        assert str(exc) == "feedback_eligibility_mismatch"
    else:
        raise AssertionError("expected inconsistent feedback state rejection")


def test_outcome_receipt_rejects_forged_runtime_binding_receipts():
    selection = _selected_receipt()
    valid = _runtime_binding_receipt(selection)
    cases = [
        ("selection_receipt_id", "other", "model_runtime_binding_selection_mismatch"),
        ("catalog_snapshot_id", "other", "model_runtime_binding_catalog_mismatch"),
        ("task_family", "other", "model_runtime_binding_task_family_mismatch"),
        ("decision", "rejected", "model_runtime_binding_not_bound"),
        ("receipt_id", "model_runtime_binding:test", "invalid_model_runtime_binding_receipt_id"),
    ]

    for key, value, reason in cases:
        forged = dict(valid)
        forged[key] = value
        try:
            build_model_selection_outcome_receipt(
                selection,
                model_runtime_binding_receipt=forged,
                verifier_decision=VerifierDecision.ACCEPT,
                verification_receipt_ids=("verify:1",),
                task_completed=True,
                evidence_correct=True,
            )
        except ValueError as exc:
            assert str(exc) == reason
        else:
            raise AssertionError(f"expected {reason}")


def test_outcome_receipt_rejects_unverified_or_regressed_results():
    selection = _selected_receipt()
    receipt = build_model_selection_outcome_receipt(
        selection,
        verifier_decision=VerifierDecision.REJECT,
        verification_receipt_ids=("verify:1",),
        task_completed=True,
        evidence_correct=True,
        regression_detected=True,
    )

    assert receipt.outcome_decision == OutcomeDecision.REJECTED
    assert receipt.feedback_eligible is False
    assert "verifier_not_accept" in receipt.rejection_reasons
    assert "regression_detected" in receipt.rejection_reasons

    try:
        outcome_feedback_record(receipt)
    except ValueError as exc:
        assert str(exc) == "outcome_not_feedback_eligible"
    else:
        raise AssertionError("rejected outcome must not feed benchmark memory")


def test_outcome_module_has_no_network_or_command_execution_imports():
    source = Path("modules/ai_intelligence/ai_gateway/src/model_intelligence_outcomes.py").read_text()
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert not (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id in {"os", "subprocess", "requests", "urllib"}
            )

    assert "subprocess" not in imported
    assert "requests" not in imported
    assert "urllib" not in imported
