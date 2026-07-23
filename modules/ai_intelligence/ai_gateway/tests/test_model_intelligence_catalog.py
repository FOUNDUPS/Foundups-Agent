"""Tests for canonical model intelligence catalog snapshots."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_intelligence_catalog import (
    Availability,
    PromotionState,
    build_canonical_model_catalog,
    build_model_catalog_snapshot,
    normalize_local_role_cards,
    normalize_openrouter_catalog,
    normalize_static_registry_cards,
)
from modules.ai_intelligence.ai_gateway.src.model_registry import ModelInfo, ModelStatus


def test_static_registry_current_models_are_candidates_not_champions():
    cards = normalize_static_registry_cards(
        {
            "frontier-x": ModelInfo(
                model_id="frontier-x",
                provider="test",
                status=ModelStatus.CURRENT,
            ),
            "old-x": ModelInfo(
                model_id="old-x",
                provider="test",
                status=ModelStatus.SUNSET,
            ),
        },
        {"architecture": ["frontier-x"]},
    )

    by_id = {card.canonical_model_id: card for card in cards}
    assert by_id["frontier-x"].promotion_state == PromotionState.CANDIDATE
    assert by_id["frontier-x"].task_families == ("architecture",)
    assert by_id["old-x"].promotion_state == PromotionState.BLOCKED
    assert all(card.promotion_state != PromotionState.CHAMPION for card in cards)


def test_openrouter_catalog_normalizes_capability_and_pricing_evidence():
    cards, rejected = normalize_openrouter_catalog(
        {
            "data": [
                {
                    "id": "moonshotai/kimi-k3",
                    "context_length": 1048576,
                    "pricing": {"prompt": "0.000003", "completion": "0.000015"},
                    "architecture": {
                        "input_modalities": ["text", "image"],
                        "output_modalities": ["text"],
                    },
                    "supported_parameters": ["tools", "response_format", "reasoning"],
                }
            ]
        }
    )

    assert rejected == ()
    assert len(cards) == 1
    card = cards[0]
    assert card.provider == "openrouter"
    assert card.canonical_model_id == "moonshotai/kimi-k3"
    assert card.availability == Availability.UNKNOWN
    assert card.freshness == "provider_catalog_listing"
    assert card.privacy_policy == "provider_policy_unknown"
    assert card.task_families == ()
    assert card.promotion_state == PromotionState.CANDIDATE
    assert card.context_window == 1048576
    assert card.input_cost_per_million == 3.0
    assert card.output_cost_per_million == 15.0
    assert card.modalities == ("image", "text")
    assert card.supports_tools is True
    assert card.supports_structured_output is True
    assert card.supports_reasoning is True


def test_static_registry_exposes_kimi_k3_as_unpromoted_autoresearch_candidate():
    cards = normalize_static_registry_cards()
    by_id = {card.canonical_model_id: card for card in cards}

    kimi = by_id["moonshotai/kimi-k3"]
    assert kimi.provider == "openrouter"
    assert kimi.availability == Availability.UNKNOWN
    assert kimi.promotion_state == PromotionState.CANDIDATE
    assert {"coding", "code_review", "reasoning", "research", "analysis"}.issubset(
        set(kimi.task_families)
    )


def test_openrouter_catalog_rejects_malformed_records_fail_closed():
    cards, rejected = normalize_openrouter_catalog({"data": [{}, "bad"]})

    assert cards == ()
    assert [item.reason for item in rejected] == ["missing_model_id", "record_not_mapping"]
    assert all(item.record_digest.startswith("rejected_record:") for item in rejected)


@dataclass(frozen=True)
class _LocalSelection:
    exists: bool
    source: str
    path: Path


def test_local_role_cards_do_not_leak_local_filesystem_paths():
    cards = normalize_local_role_cards(
        {
            "code": _LocalSelection(
                exists=True,
                source="LOCAL_MODEL_CODE_PATH",
                path=Path("C:/Users/user/private/model.gguf"),
            )
        }
    )

    snapshot = build_model_catalog_snapshot(cards, generated_at="2026-07-16T00:00:00+00:00")
    as_text = str(snapshot.to_dict())
    assert cards[0].canonical_model_id == "local/code"
    assert cards[0].availability == Availability.AVAILABLE
    assert "C:/Users/user/private" not in as_text
    assert "model.gguf" not in as_text


def test_snapshot_digest_is_deterministic_and_changes_when_card_changes():
    cards, _rejected = normalize_openrouter_catalog(
        {
            "data": [
                {"id": "provider/b", "context_length": 20},
                {"id": "provider/a", "context_length": 10},
            ]
        }
    )
    first = build_model_catalog_snapshot(cards, generated_at="2026-07-16T00:00:00+00:00")
    second = build_model_catalog_snapshot(reversed(cards), generated_at="2026-07-16T00:00:00+00:00")

    assert first.snapshot_id == second.snapshot_id
    assert [card.canonical_model_id for card in first.cards] == ["provider/a", "provider/b"]

    changed_cards, _ = normalize_openrouter_catalog(
        {"data": [{"id": "provider/a", "context_length": 999}, {"id": "provider/b", "context_length": 20}]}
    )
    changed = build_model_catalog_snapshot(changed_cards, generated_at="2026-07-16T00:00:00+00:00")
    assert changed.snapshot_id != first.snapshot_id


def test_build_canonical_catalog_combines_sources_and_keeps_rejections():
    snapshot = build_canonical_model_catalog(
        static_registry=False,
        openrouter_payload={"data": [{"id": "openai/example"}, {}]},
        local_role_selections={"triage": {"exists": False, "source": "test"}},
        source_receipts=("provider_receipt:abc",),
        generated_at="2026-07-16T00:00:00+00:00",
    )

    assert snapshot.snapshot_id.startswith("model_catalog_snapshot:")
    assert snapshot.source_receipts == ("provider_receipt:abc",)
    assert [card.canonical_model_id for card in snapshot.cards] == ["local/triage", "openai/example"]
    assert snapshot.rejected_records[0].reason == "missing_model_id"
    assert snapshot.cards[0].promotion_state == PromotionState.CHALLENGER


def test_catalog_runtime_has_no_network_or_command_execution_imports():
    source = Path("modules/ai_intelligence/ai_gateway/src/model_intelligence_catalog.py").read_text()
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
