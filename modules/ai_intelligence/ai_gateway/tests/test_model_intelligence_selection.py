"""Tests for task-scoped model selection receipts."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_intelligence_catalog import (
    Availability,
    ModelCapabilityCard,
    PromotionState,
    build_model_catalog_snapshot,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import (
    ModelTaskRequirements,
    SelectionDecision,
    SelectionMode,
    SelectionPurpose,
    select_models_for_task,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    ModelOutcomeMetrics,
    build_model_benchmark_evidence_receipt,
    build_model_promotion_evidence_receipt,
    production_evidence_for_selection,
)


def _snapshot(*cards: ModelCapabilityCard):
    return build_model_catalog_snapshot(cards, generated_at="2026-07-16T00:00:00+00:00")


def _card(
    model_id: str,
    *,
    provider: str = "test",
    promotion_state: PromotionState = PromotionState.CANDIDATE,
    availability: Availability = Availability.AVAILABLE,
    task_families: tuple[str, ...] = ("architecture",),
    verifier_pass_rate: float | None = None,
    benchmark_scores: dict[str, float] | None = None,
    context_window: int | None = 128000,
    supports_tools: bool = False,
    supports_structured_output: bool = False,
    supports_reasoning: bool = False,
    input_cost_per_million: float | None = None,
    output_cost_per_million: float | None = None,
) -> ModelCapabilityCard:
    return ModelCapabilityCard(
        provider=provider,
        model_id=model_id,
        canonical_model_id=model_id,
        source="test",
        availability=availability,
        freshness="test",
        promotion_state=promotion_state,
        task_families=task_families,
        context_window=context_window,
        supports_tools=supports_tools,
        supports_structured_output=supports_structured_output,
        supports_reasoning=supports_reasoning,
        input_cost_per_million=input_cost_per_million,
        output_cost_per_million=output_cost_per_million,
        verifier_pass_rate=verifier_pass_rate,
        benchmark_scores=benchmark_scores or {},
    ).normalized()


def test_evaluation_selects_candidate_for_benchmarking():
    snapshot = _snapshot(_card("provider/candidate", benchmark_scores={}))
    receipt = select_models_for_task(snapshot, ModelTaskRequirements(task_family="architecture"))

    assert receipt.decision == SelectionDecision.SELECTED
    assert receipt.selected_model_ids == ("provider/candidate",)
    assert receipt.catalog_snapshot_id == snapshot.snapshot_id
    assert receipt.receipt_id.startswith("model_selection_receipt:")


def test_production_rejects_unbenchmarked_non_champion_candidate():
    snapshot = _snapshot(_card("provider/candidate", benchmark_scores={}))
    receipt = select_models_for_task(
        snapshot,
        ModelTaskRequirements(
            task_family="architecture",
            purpose=SelectionPurpose.PRODUCTION,
            min_verifier_pass_rate=0.9,
        ),
    )

    assert receipt.decision == SelectionDecision.REJECTED
    assert receipt.selected_model_ids == ()
    assert "not_production_champion:1" in receipt.rejection_reasons
    assert "missing_production_evidence:1" in receipt.rejection_reasons


def test_production_rejects_catalog_only_champion_without_receipt_bound_evidence():
    champion = _card(
        "provider/champion",
        provider="a",
        promotion_state=PromotionState.CHAMPION,
        verifier_pass_rate=0.96,
        benchmark_scores={"architecture": 0.88},
    )
    receipt = select_models_for_task(
        _snapshot(champion),
        ModelTaskRequirements(
            task_family="architecture",
            purpose=SelectionPurpose.PRODUCTION,
            min_verifier_pass_rate=0.9,
        ),
    )

    assert receipt.decision == SelectionDecision.REJECTED
    assert receipt.selected_model_ids == ()
    assert "missing_production_evidence:1" in receipt.rejection_reasons


def test_production_requires_explicit_nonzero_verifier_threshold():
    champion = _card(
        "provider/champion",
        promotion_state=PromotionState.CHAMPION,
        verifier_pass_rate=0.99,
        benchmark_scores={"architecture": 0.99},
    )
    receipt = select_models_for_task(
        _snapshot(champion),
        ModelTaskRequirements(
            task_family="architecture",
            purpose=SelectionPurpose.PRODUCTION,
        ),
        production_evidence={
            "provider/champion": {
                "model_id": "provider/champion",
                "task_family": "architecture",
                "benchmark_evidence_receipt_id": "benchmark:1",
                "promotion_receipt_id": "promotion:1",
                "signed_promotion_receipt_id": "signed:1",
                "task_set_digest": "sha256:taskset",
                "held_out_split_digest": "sha256:heldout",
                "prompt_topology_digest": "sha256:topology",
                "verifier_digest": "sha256:verifier",
                "sample_count": 10,
                "verifier_pass_rate": 0.99,
                "promotion_state": "champion",
            }
        },
    )

    assert receipt.decision == SelectionDecision.REJECTED
    assert "production_verifier_threshold_missing:1" in receipt.rejection_reasons


def test_production_selects_champion_only_with_benchmark_and_signed_promotion_receipts():
    champion = _card(
        "provider/champion",
        provider="a",
        promotion_state=PromotionState.CHAMPION,
        verifier_pass_rate=0.01,
        benchmark_scores={},
    )
    candidate = _card(
        "provider/candidate",
        provider="b",
        promotion_state=PromotionState.CANDIDATE,
        verifier_pass_rate=0.99,
        benchmark_scores={"architecture": 0.99},
    )
    benchmark = build_model_benchmark_evidence_receipt(
        model_id="provider/champion",
        task_family="architecture",
        task_set_digest="sha256:task-set",
        held_out_split_digest="sha256:held-out",
        prompt_topology_digest="sha256:topology",
        verifier_digest="sha256:verifier",
        verifier_receipt_id="verifier_receipt:1",
        sample_count=50,
        accepted_count=47,
        metrics=ModelOutcomeMetrics(latency_ms=1200, input_tokens=1000, output_tokens=500),
    )
    promotion = build_model_promotion_evidence_receipt(
        benchmark_receipt=benchmark,
        promotion_state=PromotionState.CHAMPION,
        promotion_authority_receipt_id="promotion_authority:1",
        signed_promotion_receipt_id="signed_promotion:1",
        min_verifier_pass_rate=0.9,
    )
    receipt = select_models_for_task(
        _snapshot(candidate, champion),
        ModelTaskRequirements(
            task_family="architecture",
            purpose=SelectionPurpose.PRODUCTION,
            min_verifier_pass_rate=0.9,
        ),
        production_evidence=production_evidence_for_selection(benchmark, promotion),
    )

    assert receipt.decision == SelectionDecision.SELECTED
    assert receipt.selected_model_ids == ("provider/champion",)
    assert all(item.canonical_model_id != "provider/candidate" for item in receipt.rankings)


def test_requirements_filter_context_tools_structured_reasoning_and_cost():
    good = _card(
        "provider/good",
        supports_tools=True,
        supports_structured_output=True,
        supports_reasoning=True,
        context_window=200000,
        input_cost_per_million=1.0,
        output_cost_per_million=2.0,
    )
    no_tools = _card("provider/no-tools", supports_tools=False)
    costly = _card(
        "provider/costly",
        supports_tools=True,
        supports_structured_output=True,
        supports_reasoning=True,
        context_window=200000,
        input_cost_per_million=100.0,
    )
    receipt = select_models_for_task(
        _snapshot(no_tools, costly, good),
        ModelTaskRequirements(
            task_family="architecture",
            min_context_window=100000,
            require_tools=True,
            require_structured_output=True,
            require_reasoning=True,
            max_input_cost_per_million=10.0,
        ),
    )

    assert receipt.selected_model_ids == ("provider/good",)
    assert all(item.canonical_model_id == "provider/good" for item in receipt.rankings)


def test_panel_selection_prefers_provider_diversity():
    snapshot = _snapshot(
        _card("a/strong", provider="a", benchmark_scores={"architecture": 0.9}),
        _card("a/second", provider="a", benchmark_scores={"architecture": 0.8}),
        _card("b/diverse", provider="b", benchmark_scores={"architecture": 0.7}),
    )
    receipt = select_models_for_task(
        snapshot,
        ModelTaskRequirements(
            task_family="architecture",
            selection_mode=SelectionMode.PANEL,
            max_candidates=2,
        ),
    )

    assert receipt.decision == SelectionDecision.SELECTED
    assert len(receipt.selected_model_ids) == 2
    assert receipt.panel_topology_digest
    assert [assignment.role for assignment in receipt.role_assignments] == ["principal", "researcher"]
    selected_providers = {
        item.provider for item in receipt.rankings if item.canonical_model_id in receipt.selected_model_ids
    }
    assert selected_providers == {"a", "b"}


def test_panel_selection_reserves_verifier_role_for_independent_verifier():
    snapshot = _snapshot(_card("a/strong", provider="a"), _card("b/diverse", provider="b"))

    try:
        select_models_for_task(
            snapshot,
            ModelTaskRequirements(
                task_family="architecture",
                selection_mode=SelectionMode.PANEL,
                max_candidates=2,
                panel_roles=("principal", "verifier"),
            ),
        )
    except ValueError as exc:
        assert str(exc) == "verifier_role_reserved_for_independent_verifier"
    else:
        raise AssertionError("expected verifier role to be rejected")


def test_blocked_and_unavailable_models_are_never_selected():
    snapshot = _snapshot(
        _card("provider/blocked", promotion_state=PromotionState.BLOCKED),
        _card("provider/unavailable", availability=Availability.UNAVAILABLE),
    )
    receipt = select_models_for_task(snapshot, ModelTaskRequirements(task_family="architecture"))

    assert receipt.decision == SelectionDecision.REJECTED
    assert "promotion_state_not_eligible:1" in receipt.rejection_reasons
    assert "unavailable:1" in receipt.rejection_reasons


def test_receipt_digest_is_stable_and_binds_snapshot_id():
    snapshot = _snapshot(_card("provider/a"), _card("provider/b"))
    requirements = ModelTaskRequirements(task_family="architecture")

    first = select_models_for_task(snapshot, requirements)
    second = select_models_for_task(snapshot, requirements)

    assert first.receipt_id == second.receipt_id
    assert first.catalog_snapshot_id == snapshot.snapshot_id

    changed_snapshot = _snapshot(_card("provider/a", benchmark_scores={"architecture": 0.9}))
    changed = select_models_for_task(changed_snapshot, requirements)
    assert changed.receipt_id != first.receipt_id


def test_selector_has_no_network_or_command_execution_imports():
    source = Path("modules/ai_intelligence/ai_gateway/src/model_intelligence_selection.py").read_text()
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
