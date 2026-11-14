"""Typed zero-authority contract for the RedDog conversation plane."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


SCHEMA_VERSION = "reddog_conversation_plane_decision.v1"


class InteractionIntent(str, Enum):
    CHAT = "CHAT"
    RESEARCH = "RESEARCH"
    PROPOSE = "PROPOSE"
    AUTHORIZE = "AUTHORIZE"
    STATUS = "STATUS"
    CANCEL = "CANCEL"


class ReasoningDepth(str, Enum):
    FAST = "FAST"
    CRITIC = "CRITIC"
    PANEL = "PANEL"


class EffectCeiling(str, Enum):
    NONE = "NONE"
    READ_ONLY = "READ_ONLY"
    PROPOSAL = "PROPOSAL"
    BOUNDED_EXECUTION = "BOUNDED_EXECUTION"


_EFFECT_RANK = {
    EffectCeiling.NONE: 0,
    EffectCeiling.READ_ONLY: 1,
    EffectCeiling.PROPOSAL: 2,
    EffectCeiling.BOUNDED_EXECUTION: 3,
}

_INTENT_EFFECTS = {
    InteractionIntent.CHAT: EffectCeiling.NONE,
    InteractionIntent.RESEARCH: EffectCeiling.READ_ONLY,
    InteractionIntent.PROPOSE: EffectCeiling.PROPOSAL,
    InteractionIntent.AUTHORIZE: EffectCeiling.PROPOSAL,
    InteractionIntent.STATUS: EffectCeiling.READ_ONLY,
    InteractionIntent.CANCEL: EffectCeiling.NONE,
}


@dataclass(frozen=True, slots=True)
class ConversationPlaneDecision:
    """One deterministic routing decision; it is evidence, never authority."""

    interaction_intent: InteractionIntent
    reasoning_depth: ReasoningDepth
    effect_ceiling: EffectCeiling
    reason_codes: tuple[str, ...]
    risk_signals: tuple[str, ...]
    foreground_reply_allowed: bool
    asynchronous_readonly_allowed: bool
    requires_authenticated_authority: bool
    chat_can_create_effects: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        reasons = conversation_decision_reasons(self)
        if reasons:
            raise ValueError(reasons[0])

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "interaction_intent": self.interaction_intent.value,
            "reasoning_depth": self.reasoning_depth.value,
            "effect_ceiling": self.effect_ceiling.value,
            "reason_codes": list(self.reason_codes),
            "risk_signals": list(self.risk_signals),
            "foreground_reply_allowed": self.foreground_reply_allowed,
            "asynchronous_readonly_allowed": self.asynchronous_readonly_allowed,
            "requires_authenticated_authority": self.requires_authenticated_authority,
            "chat_can_create_effects": self.chat_can_create_effects,
        }


def conversation_decision_reasons(
    decision: ConversationPlaneDecision,
) -> tuple[str, ...]:
    """Return stable contract violations without interpreting model output."""

    if type(decision) is not ConversationPlaneDecision:
        return ("conversation_plane_decision_type_invalid",)
    reasons: list[str] = []
    enum_shape_valid = _native_decision_enums(decision)
    if not enum_shape_valid:
        reasons.append("conversation_plane_decision_type_invalid")
    if type(decision.schema_version) is not str or decision.schema_version != SCHEMA_VERSION:
        reasons.append("conversation_plane_schema_invalid")
    if enum_shape_valid and decision.effect_ceiling is not _INTENT_EFFECTS[decision.interaction_intent]:
        reasons.append("conversation_plane_intent_effect_mismatch")
    if enum_shape_valid and decision.effect_ceiling is EffectCeiling.BOUNDED_EXECUTION:
        reasons.append("conversation_plane_execution_authority_forbidden")
    if not _native_decision_booleans(decision):
        reasons.append("conversation_plane_decision_type_invalid")
    if decision.chat_can_create_effects is not False:
        reasons.append("conversation_plane_chat_effect_forbidden")
    if decision.foreground_reply_allowed is not True:
        reasons.append("conversation_plane_foreground_reply_required")
    if (
        type(decision.reason_codes) is not tuple
        or type(decision.risk_signals) is not tuple
        or not _valid_codes(decision.reason_codes)
        or not _valid_codes(decision.risk_signals, allow_empty=True)
    ):
        reasons.append("conversation_plane_reason_shape_invalid")
    if enum_shape_valid:
        required = decision.interaction_intent in {
            InteractionIntent.AUTHORIZE,
            InteractionIntent.CANCEL,
        }
        if decision.requires_authenticated_authority is not required:
            reasons.append("conversation_plane_authority_requirement_invalid")
        asynchronous = (
            decision.interaction_intent is InteractionIntent.RESEARCH
            or decision.reasoning_depth is not ReasoningDepth.FAST
        )
        if decision.asynchronous_readonly_allowed is not asynchronous:
            reasons.append("conversation_plane_async_admission_invalid")
    return tuple(dict.fromkeys(reasons))


def enforce_effect_ceiling(
    decision: ConversationPlaneDecision,
    requested_effect: EffectCeiling | str,
) -> EffectCeiling:
    """Reject any downstream/model request that exceeds the deterministic ceiling."""

    violations = conversation_decision_reasons(decision)
    if violations:
        raise ValueError(violations[0])
    requested = _strict_effect(requested_effect)
    if _EFFECT_RANK[requested] > _EFFECT_RANK[decision.effect_ceiling]:
        raise ValueError("conversation_plane_effect_ceiling_exceeded")
    return requested


def decision_from_mapping(payload: Mapping[str, Any]) -> ConversationPlaneDecision:
    """Strictly rehydrate a decision from an adapter boundary."""

    expected = {
        "schema_version", "interaction_intent", "reasoning_depth",
        "effect_ceiling", "reason_codes", "risk_signals",
        "foreground_reply_allowed", "asynchronous_readonly_allowed",
        "requires_authenticated_authority", "chat_can_create_effects",
    }
    if type(payload) is not dict or set(payload) != expected:
        raise ValueError("conversation_plane_decision_shape_invalid")
    if any(
        type(payload[name]) is not bool
        for name in (
            "foreground_reply_allowed", "asynchronous_readonly_allowed",
            "requires_authenticated_authority", "chat_can_create_effects",
        )
    ):
        raise ValueError("conversation_plane_decision_type_invalid")
    return ConversationPlaneDecision(
        schema_version=_strict_string(payload["schema_version"]),
        interaction_intent=_strict_enum(InteractionIntent, payload["interaction_intent"]),
        reasoning_depth=_strict_enum(ReasoningDepth, payload["reasoning_depth"]),
        effect_ceiling=_strict_enum(EffectCeiling, payload["effect_ceiling"]),
        reason_codes=_strict_codes(payload["reason_codes"]),
        risk_signals=_strict_codes(payload["risk_signals"], allow_empty=True),
        foreground_reply_allowed=payload["foreground_reply_allowed"],
        asynchronous_readonly_allowed=payload["asynchronous_readonly_allowed"],
        requires_authenticated_authority=payload["requires_authenticated_authority"],
        chat_can_create_effects=payload["chat_can_create_effects"],
    )


def _strict_effect(value: EffectCeiling | str) -> EffectCeiling:
    if isinstance(value, EffectCeiling):
        return value
    if type(value) is not str:
        raise ValueError("conversation_plane_effect_invalid")
    try:
        return EffectCeiling(value)
    except ValueError as exc:
        raise ValueError("conversation_plane_effect_invalid") from exc


def _strict_enum(enum_type: type[Enum], value: object) -> Any:
    text = _strict_string(value)
    try:
        return enum_type(text)
    except ValueError as exc:
        raise ValueError("conversation_plane_decision_enum_invalid") from exc


def _native_decision_enums(decision: ConversationPlaneDecision) -> bool:
    return (
        type(decision.interaction_intent) is InteractionIntent
        and type(decision.reasoning_depth) is ReasoningDepth
        and type(decision.effect_ceiling) is EffectCeiling
    )


def _native_decision_booleans(decision: ConversationPlaneDecision) -> bool:
    return all(
        type(value) is bool
        for value in (
            decision.foreground_reply_allowed,
            decision.asynchronous_readonly_allowed,
            decision.requires_authenticated_authority,
            decision.chat_can_create_effects,
        )
    )


def _strict_codes(value: object, *, allow_empty: bool = False) -> tuple[str, ...]:
    if type(value) is not list or not _valid_codes(tuple(value), allow_empty=allow_empty):
        raise ValueError("conversation_plane_reason_shape_invalid")
    return tuple(value)


def _valid_codes(value: tuple[object, ...], *, allow_empty: bool = False) -> bool:
    return (allow_empty or bool(value)) and len(value) <= 16 and all(
        type(item) is str and item and len(item) <= 96 for item in value
    ) and len(set(value)) == len(value)


def _strict_string(value: object) -> str:
    if type(value) is not str:
        raise ValueError("conversation_plane_decision_type_invalid")
    return value


__all__ = [
    "ConversationPlaneDecision",
    "EffectCeiling",
    "InteractionIntent",
    "ReasoningDepth",
    "SCHEMA_VERSION",
    "conversation_decision_reasons",
    "decision_from_mapping",
    "enforce_effect_ceiling",
]
