"""Contracts for the zero-authority RedDog conversational plane."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from modules.ai_intelligence.digital_twin.src.conversation_plane import (
    MAX_TURN_CHARS,
    classify_conversation_turn,
)
from modules.ai_intelligence.digital_twin.src.conversation_plane_contract import (
    ConversationPlaneDecision,
    EffectCeiling,
    InteractionIntent,
    ReasoningDepth,
    decision_from_mapping,
    enforce_effect_ceiling,
)


CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "conversation_plane_cases.json").read_text(
        encoding="utf-8"
    )
)


def _case_text(case: dict[str, object]) -> str:
    if "text" in case:
        return str(case["text"])
    repeat = case["text_repeat"]
    assert type(repeat) is dict
    return str(repeat["value"]) * int(repeat["count"])


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_conversation_plane_cross_surface_vectors(case: dict[str, object]) -> None:
    text = _case_text(case)
    if "error" in case:
        with pytest.raises(ValueError, match=str(case["error"])):
            classify_conversation_turn(text)
        return
    decision = classify_conversation_turn(text)
    assert decision.interaction_intent.value == case["interaction_intent"]
    assert decision.reasoning_depth.value == case["reasoning_depth"]
    assert decision.effect_ceiling.value == case["effect_ceiling"]
    assert (
        decision.requires_authenticated_authority
        is case["requires_authenticated_authority"]
    )
    assert decision.chat_can_create_effects is False
    assert decision.foreground_reply_allowed is True


def test_round_trip_is_strict_and_preserves_zero_authority() -> None:
    original = classify_conversation_turn("Implement the bounded adapter.")
    restored = decision_from_mapping(original.to_dict())
    assert restored == original
    assert restored.effect_ceiling is EffectCeiling.PROPOSAL
    assert restored.chat_can_create_effects is False


@pytest.mark.parametrize("requested", ["READ_ONLY", "PROPOSAL", "BOUNDED_EXECUTION"])
def test_chat_text_cannot_elevate_effects(requested: str) -> None:
    decision = classify_conversation_turn("Hello RedDog.")
    with pytest.raises(ValueError, match="conversation_plane_effect_ceiling_exceeded"):
        enforce_effect_ceiling(decision, requested)


def test_research_allows_only_read_only_downstream_work() -> None:
    decision = classify_conversation_turn("Research the routing architecture.")
    assert enforce_effect_ceiling(decision, EffectCeiling.NONE) is EffectCeiling.NONE
    assert (
        enforce_effect_ceiling(decision, EffectCeiling.READ_ONLY)
        is EffectCeiling.READ_ONLY
    )
    with pytest.raises(ValueError, match="conversation_plane_effect_ceiling_exceeded"):
        enforce_effect_ceiling(decision, EffectCeiling.PROPOSAL)


def test_risk_changes_reasoning_not_effect() -> None:
    ordinary = classify_conversation_turn("We should talk.")
    risky = classify_conversation_turn("We should talk about wallet privacy.")
    assert ordinary.interaction_intent is risky.interaction_intent is InteractionIntent.CHAT
    assert ordinary.effect_ceiling is risky.effect_ceiling is EffectCeiling.NONE
    assert ordinary.reasoning_depth is ReasoningDepth.FAST
    assert risky.reasoning_depth is ReasoningDepth.PANEL


@pytest.mark.parametrize(
    "value",
    ["", " ", "x" * (MAX_TURN_CHARS + 1), "hello\x00world", "hello\x01world"],
)
def test_invalid_operator_text_fails_closed(value: str) -> None:
    with pytest.raises(ValueError, match="conversation_plane_operator_text_invalid"):
        classify_conversation_turn(value)


def test_non_native_types_and_extra_fields_fail_closed() -> None:
    decision = classify_conversation_turn("Hello").to_dict()
    decision["foreground_reply_allowed"] = 1
    with pytest.raises(ValueError, match="conversation_plane_decision_type_invalid"):
        decision_from_mapping(decision)
    decision = classify_conversation_turn("Hello").to_dict()
    decision["unexpected"] = True
    with pytest.raises(ValueError, match="conversation_plane_decision_shape_invalid"):
        decision_from_mapping(decision)
    decision = classify_conversation_turn("Hello").to_dict()
    decision["interaction_intent"] = "EXECUTE"
    with pytest.raises(ValueError, match="conversation_plane_decision_enum_invalid"):
        decision_from_mapping(decision)


def test_async_admission_is_derived_not_caller_controlled() -> None:
    decision = classify_conversation_turn("Hello").to_dict()
    decision["asynchronous_readonly_allowed"] = True
    with pytest.raises(ValueError, match="conversation_plane_async_admission_invalid"):
        decision_from_mapping(decision)


def test_contract_rejects_conversation_plane_execution_authority() -> None:
    with pytest.raises(ValueError, match="conversation_plane_intent_effect_mismatch"):
        ConversationPlaneDecision(
            interaction_intent=InteractionIntent.CHAT,
            reasoning_depth=ReasoningDepth.FAST,
            effect_ceiling=EffectCeiling.BOUNDED_EXECUTION,
            reason_codes=("forged",),
            risk_signals=(),
            foreground_reply_allowed=True,
            asynchronous_readonly_allowed=False,
            requires_authenticated_authority=False,
        )


def test_effect_gate_rejects_forged_or_mutated_decisions() -> None:
    forged = type("ForgedDecision", (), {"effect_ceiling": EffectCeiling.BOUNDED_EXECUTION})()
    with pytest.raises(ValueError, match="conversation_plane_decision_type_invalid"):
        enforce_effect_ceiling(forged, EffectCeiling.BOUNDED_EXECUTION)  # type: ignore[arg-type]
    decision = classify_conversation_turn("Hello RedDog.")
    object.__setattr__(decision, "effect_ceiling", EffectCeiling.BOUNDED_EXECUTION)
    with pytest.raises(ValueError, match="conversation_plane_intent_effect_mismatch"):
        enforce_effect_ceiling(decision, EffectCeiling.BOUNDED_EXECUTION)


@pytest.mark.parametrize(
    "name", ["conversation_plane.py", "conversation_plane_contract.py"]
)
def test_conversation_plane_python_wsp62_limits(name: str) -> None:
    source = (Path(__file__).parents[1] / "src" / name).read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert len(source.splitlines()) <= 500
    assert all(node.end_lineno - node.lineno + 1 <= 50 for node in functions)
