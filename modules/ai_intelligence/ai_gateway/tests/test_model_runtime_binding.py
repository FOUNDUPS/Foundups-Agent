"""Tests for RedDog dynamic runtime model binding receipts."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_intelligence_catalog import (
    ModelCapabilityCard,
    PromotionState,
    build_model_catalog_snapshot,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    ModelBenchmarkEvidenceReceipt,
    ModelOutcomeMetrics,
    ModelPromotionEvidenceReceipt,
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
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import VerifiedModelProductionEvidence
from model_signed_evidence_test_helpers import make_verified_production_evidence


TASK = "architecture"
TASK_SET = "sha256:task-set"
HELD_OUT = "sha256:held-out"
TOPOLOGY = "sha256:topology"
VERIFIER = "sha256:verifier"


def _card(model_id: str, *, provider: str = "provider") -> ModelCapabilityCard:
    return ModelCapabilityCard(
        provider=provider,
        model_id=model_id,
        canonical_model_id=model_id,
        source="test",
        promotion_state=PromotionState.CHAMPION,
        task_families=(TASK,),
        benchmark_scores={TASK: 0.9},
        verifier_pass_rate=0.95,
    ).normalized()


def _benchmark(model_id: str, *, topology: str = TOPOLOGY, accepted: int = 19) -> ModelBenchmarkEvidenceReceipt:
    return build_model_benchmark_evidence_receipt(
        model_id=model_id,
        task_family=TASK,
        task_set_digest=TASK_SET,
        held_out_split_digest=HELD_OUT,
        prompt_topology_digest=topology,
        verifier_digest=VERIFIER,
        verifier_receipt_id=f"verifier:{model_id}",
        sample_count=20,
        accepted_count=accepted,
        metrics=ModelOutcomeMetrics(latency_ms=1000, input_tokens=500, output_tokens=200),
    )


def _promotion(benchmark: ModelBenchmarkEvidenceReceipt) -> ModelPromotionEvidenceReceipt:
    return build_model_promotion_evidence_receipt(
        benchmark_receipt=benchmark,
        promotion_state=PromotionState.CHAMPION,
        promotion_authority_receipt_id=f"authority:{benchmark.model_id}",
        signed_promotion_receipt_id=f"signed:{benchmark.model_id}",
        min_verifier_pass_rate=0.9,
    )


def _verified_evidence(
    *,
    snapshot_id: str,
    selection_receipt_id: str = "model_selection_receipt:pending",
    pairs: tuple[tuple[ModelBenchmarkEvidenceReceipt, ModelPromotionEvidenceReceipt], ...],
) -> VerifiedModelProductionEvidence:
    entries = []
    for benchmark, promotion in pairs:
        entries.extend(
            make_verified_production_evidence(
                benchmark,
                promotion,
                catalog_snapshot_id=snapshot_id,
                selection_receipt_id=selection_receipt_id,
            ).entries
        )
    return VerifiedModelProductionEvidence(entries=tuple(entries))


def _production_selection(snapshot, requirements, *pairs):
    provisional = _verified_evidence(snapshot_id=snapshot.snapshot_id, pairs=tuple(pairs))
    first = select_models_for_task(snapshot, requirements, production_evidence=provisional)
    verified = _verified_evidence(
        snapshot_id=snapshot.snapshot_id,
        selection_receipt_id=first.receipt_id,
        pairs=tuple(pairs),
    )
    second = select_models_for_task(snapshot, requirements, production_evidence=verified)
    assert second.receipt_id == first.receipt_id
    return second, verified


def _policy(**overrides) -> ModelRuntimeBindingPolicy:
    values = {
        "task_family": TASK,
        "runtime_surface": "reddog_fusion",
        "min_verifier_pass_rate": 0.9,
        "required_task_set_digest": TASK_SET,
        "required_held_out_split_digest": HELD_OUT,
        "required_verifier_digest": VERIFIER,
        "required_panel_topology_digest": None,
        "authority_receipt_id": "runtime-authority:1",
    }
    values.update(overrides)
    return ModelRuntimeBindingPolicy(**values)


def test_single_model_runtime_binding_requires_receipt_bound_evidence():
    card = _card("provider/champion")
    snapshot = build_model_catalog_snapshot((card,), generated_at="2026-07-16T00:00:00+00:00")
    benchmark = _benchmark("provider/champion")
    promotion = _promotion(benchmark)
    selection, verified_evidence = _production_selection(
        snapshot,
        ModelTaskRequirements(
            task_family=TASK,
            purpose=SelectionPurpose.PRODUCTION,
            min_verifier_pass_rate=0.9,
        ),
        (benchmark, promotion),
    )

    receipt = bind_reddog_runtime_models(
        catalog_snapshot=snapshot,
        selection_receipt=selection,
        benchmark_evidence_receipts=(benchmark,),
        promotion_evidence_receipts=(promotion,),
        policy=_policy(),
        verified_production_evidence=verified_evidence,
    )

    assert selection.decision == SelectionDecision.SELECTED
    assert receipt.decision == ModelRuntimeBindingDecision.BOUND
    assert receipt.principal_model == "provider/champion"
    assert receipt.panel_models == ()
    assert receipt.benchmark_evidence_receipt_ids == (benchmark.receipt_id,)
    assert receipt.promotion_evidence_receipt_ids == (promotion.receipt_id,)
    assert receipt.signed_promotion_receipt_ids == (promotion.signed_promotion_receipt_id,)
    payload = receipt.to_reddog_bridge_payload()
    assert payload["lead_model"] == "provider/champion"
    assert payload["panel_models"] == []
    assert payload["model_runtime_binding_receipt_id"] == receipt.receipt_id


def test_catalog_only_champion_cannot_bind_runtime():
    card = _card("provider/champion")
    snapshot = build_model_catalog_snapshot((card,), generated_at="2026-07-16T00:00:00+00:00")
    selection = select_models_for_task(
        snapshot,
        ModelTaskRequirements(
            task_family=TASK,
            purpose=SelectionPurpose.PRODUCTION,
            min_verifier_pass_rate=0.9,
        ),
    )

    receipt = bind_reddog_runtime_models(
        catalog_snapshot=snapshot,
        selection_receipt=selection,
        benchmark_evidence_receipts=(),
        promotion_evidence_receipts=(),
        policy=_policy(),
    )

    assert selection.decision == SelectionDecision.REJECTED
    assert receipt.decision == ModelRuntimeBindingDecision.REJECTED
    assert "selection_not_selected" in receipt.rejection_reasons
    assert "missing_selected_models" in receipt.rejection_reasons
    try:
        receipt.to_reddog_bridge_payload()
    except ValueError as exc:
        assert str(exc) == "runtime_binding_not_bound"
    else:
        raise AssertionError("rejected binding must not produce bridge payload")


def test_evaluation_selection_remains_supported_but_cannot_bind_production_runtime():
    card = _card("provider/champion")
    snapshot = build_model_catalog_snapshot((card,), generated_at="2026-07-16T00:00:00+00:00")
    benchmark = _benchmark("provider/champion")
    promotion = _promotion(benchmark)
    selection = select_models_for_task(snapshot, ModelTaskRequirements(task_family=TASK))

    receipt = bind_reddog_runtime_models(
        catalog_snapshot=snapshot,
        selection_receipt=selection,
        benchmark_evidence_receipts=(benchmark,),
        promotion_evidence_receipts=(promotion,),
        policy=_policy(),
    )

    assert selection.decision == SelectionDecision.SELECTED
    assert receipt.decision == ModelRuntimeBindingDecision.REJECTED
    assert "selection_not_production" in receipt.rejection_reasons


def test_runtime_binding_rejects_mismatched_receipts_and_policy():
    card = _card("provider/champion")
    snapshot = build_model_catalog_snapshot((card,), generated_at="2026-07-16T00:00:00+00:00")
    benchmark = _benchmark("provider/champion")
    promotion = _promotion(benchmark)
    selection, verified_evidence = _production_selection(
        snapshot,
        ModelTaskRequirements(
            task_family=TASK,
            purpose=SelectionPurpose.PRODUCTION,
            min_verifier_pass_rate=0.9,
        ),
        (benchmark, promotion),
    )

    receipt = bind_reddog_runtime_models(
        catalog_snapshot=snapshot,
        selection_receipt=selection,
        benchmark_evidence_receipts=(benchmark,),
        promotion_evidence_receipts=(promotion,),
        policy=_policy(required_task_set_digest="sha256:other", required_verifier_digest="sha256:other"),
        verified_production_evidence=verified_evidence,
    )

    assert receipt.decision == ModelRuntimeBindingDecision.REJECTED
    assert "task_set_digest_mismatch" in receipt.rejection_reasons
    assert "verifier_digest_mismatch" in receipt.rejection_reasons


def test_panel_runtime_binding_rejects_single_model_evidence_without_signed_aggregate():
    cards = (
        _card("provider/principal", provider="a"),
        _card("provider/researcher", provider="b"),
        _card("provider/critic", provider="c"),
    )
    snapshot = build_model_catalog_snapshot(cards, generated_at="2026-07-16T00:00:00+00:00")
    benchmarks = tuple(_benchmark(card.canonical_model_id, topology=TOPOLOGY) for card in cards)
    promotions = tuple(_promotion(benchmark) for benchmark in benchmarks)
    selection, verified_evidence = _production_selection(
        snapshot,
        ModelTaskRequirements(
            task_family=TASK,
            purpose=SelectionPurpose.PRODUCTION,
            selection_mode=SelectionMode.PANEL,
            max_candidates=3,
            min_verifier_pass_rate=0.9,
            panel_roles=("principal", "researcher", "critic"),
            panel_topology_digest=TOPOLOGY,
        ),
        *zip(benchmarks, promotions),
    )

    receipt = bind_reddog_runtime_models(
        catalog_snapshot=snapshot,
        selection_receipt=selection,
        benchmark_evidence_receipts=benchmarks,
        promotion_evidence_receipts=promotions,
        policy=_policy(required_panel_topology_digest=TOPOLOGY),
        verified_production_evidence=verified_evidence,
    )

    assert selection.decision == SelectionDecision.SELECTED
    assert receipt.decision == ModelRuntimeBindingDecision.REJECTED
    assert "missing_verified_panel_evidence" in receipt.rejection_reasons
    assert receipt.principal_model is None
    try:
        receipt.to_reddog_bridge_payload()
    except ValueError as exc:
        assert str(exc) == "runtime_binding_not_bound"
    else:
        raise AssertionError("unauthenticated panel binding must not produce a bridge payload")


def test_panel_runtime_binding_rejects_topology_mismatch():
    cards = (_card("provider/principal", provider="a"), _card("provider/researcher", provider="b"))
    snapshot = build_model_catalog_snapshot(cards, generated_at="2026-07-16T00:00:00+00:00")
    benchmarks = tuple(_benchmark(card.canonical_model_id, topology=TOPOLOGY) for card in cards)
    promotions = tuple(_promotion(benchmark) for benchmark in benchmarks)
    selection, verified_evidence = _production_selection(
        snapshot,
        ModelTaskRequirements(
            task_family=TASK,
            purpose=SelectionPurpose.PRODUCTION,
            selection_mode=SelectionMode.PANEL,
            max_candidates=2,
            min_verifier_pass_rate=0.9,
            panel_roles=("principal", "researcher"),
            panel_topology_digest=TOPOLOGY,
        ),
        *zip(benchmarks, promotions),
    )

    receipt = bind_reddog_runtime_models(
        catalog_snapshot=snapshot,
        selection_receipt=selection,
        benchmark_evidence_receipts=benchmarks,
        promotion_evidence_receipts=promotions,
        policy=_policy(required_panel_topology_digest="sha256:wrong"),
        verified_production_evidence=verified_evidence,
    )

    assert receipt.decision == ModelRuntimeBindingDecision.REJECTED
    assert "panel_topology_digest_mismatch" in receipt.rejection_reasons


def test_runtime_binding_rejects_duplicate_evidence_receipts():
    benchmark = _benchmark("provider/champion")
    promotion = _promotion(benchmark)
    card = _card("provider/champion")
    snapshot = build_model_catalog_snapshot((card,), generated_at="2026-07-16T00:00:00+00:00")
    selection, verified_evidence = _production_selection(
        snapshot,
        ModelTaskRequirements(
            task_family=TASK,
            purpose=SelectionPurpose.PRODUCTION,
            min_verifier_pass_rate=0.9,
        ),
        (benchmark, promotion),
    )

    try:
        bind_reddog_runtime_models(
            catalog_snapshot=snapshot,
            selection_receipt=selection,
            benchmark_evidence_receipts=(benchmark, benchmark),
            promotion_evidence_receipts=(promotion,),
            policy=_policy(),
            verified_production_evidence=verified_evidence,
        )
    except ValueError as exc:
        assert str(exc) == "duplicate_benchmark_receipt_for_model"
    else:
        raise AssertionError("duplicate evidence must fail closed")


def test_runtime_binding_module_has_no_network_command_or_runtime_mutation_imports():
    source = Path("modules/ai_intelligence/ai_gateway/src/model_runtime_binding.py").read_text()
    tree = ast.parse(source)
    imported: set[str] = set()
    banned_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id in {
                "os",
                "subprocess",
                "requests",
                "urllib",
                "socket",
            }:
                banned_calls.append(f"{node.func.value.id}.{node.func.attr}")

    assert "subprocess" not in imported
    assert "requests" not in imported
    assert "urllib" not in imported
    assert "socket" not in imported
    assert banned_calls == []
