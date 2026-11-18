"""Deterministic intent/depth/effect classification for RedDog conversation."""

from __future__ import annotations

import re
import unicodedata

from .conversation_plane_contract import (
    ConversationPlaneDecision,
    EffectCeiling,
    InteractionIntent,
    ReasoningDepth,
)


MAX_TURN_CHARS = 12000

_AMBIGUOUS_AUTHORIZATION = re.compile(
    r"^\s*(?:do it|go ahead|proceed|ship it|make it so)[.!]?\s*$", re.I
)
_CANCEL = re.compile(
    r"^\s*(?:cancel|stop|abort)(?:\s+(?:that|this|the\s+current|current)"
    r"\s*(?:job|task|work|run|request)?)?[.!]?\s*$",
    re.I,
)
_STATUS = re.compile(
    r"(?:\b(?:status|progress)\b.*\b(?:job|task|work|run|request)\b|"
    r"\b(?:job|task|work|run|request)\b.*\b(?:status|progress)\b|"
    r"^\s*(?:status|progress)[?!.]?\s*$)",
    re.I,
)
_AUTHORIZE = re.compile(
    r"\b(?:authorize|approve|proceed\s+with|execute)\b.{0,80}"
    r"\b(?:proposal|work\s*order|change\s*set|plan)\b",
    re.I,
)
_CONVERSATIONAL_CONTENT = re.compile(
    r"\b(?:draft|write|rewrite|improve|polish|fix)\b.{0,40}"
    r"\b(?:reply|response|message|email|comment|post)\b",
    re.I,
)
_PROPOSE = re.compile(
    r"\b(?:fix|implement|build|change|edit|update|refactor|harden|repair|"
    r"add|remove|deploy|merge|commit|publish|install|write|create|finish|"
    r"complete|work(?:ing)?\s+on|continue\b.{0,40}\b(?:work|task|"
    r"implementation|repair|build))\b",
    re.I,
)
_RESEARCH = re.compile(
    r"\b(?:audit|review|research|investigate|analy[sz]e|explain|compare|"
    r"verify|look\s+up|find\s+out|what\s+is|how\s+does|why\s+does)\b",
    re.I,
)
_EXPLICIT_PANEL = re.compile(
    r"\b(?:full\s+panel|use\s+(?:a\s+)?panel|multiple\s+critics|adversarial\s+panel)\b",
    re.I,
)
_EXPLICIT_CRITIC = re.compile(
    r"\b(?:critic|critique|challenge|adversarial\s+review|second\s+opinion)\b",
    re.I,
)

_RISK_PATTERNS = (
    ("authentication", re.compile(r"\b(?:auth(?:entication|orization)?|oauth|credential|secret|token)\b", re.I)),
    ("security", re.compile(r"\b(?:security|vulnerability|exploit|unsafe|attack)\b", re.I)),
    ("privacy", re.compile(r"\b(?:privacy|personal\s+data|pii|private\s+data)\b", re.I)),
    ("money", re.compile(r"\b(?:money|funds?|payment|wallet|trade|financial|cabr|payout)\b", re.I)),
    ("irreversible", re.compile(r"\b(?:delete|destroy|irreversible|production|deploy|merge|publish)\b", re.I)),
    ("contradiction", re.compile(r"\b(?:contradict|conflict|disagree|inconsistent)\w*\b", re.I)),
)


def classify_conversation_turn(operator_text: str) -> ConversationPlaneDecision:
    """Classify operator text without reading memory, models, HoloIndex, or effects."""

    text = _normalized_operator_text(operator_text)
    intent, intent_reason = _interaction_intent(text)
    risks = _risk_signals(text)
    depth, depth_reason = _reasoning_depth(text, intent, risks)
    effect = _effect_ceiling(intent)
    reasons = [intent_reason, depth_reason]
    reasons.extend(f"risk_signal:{risk}" for risk in risks)
    return ConversationPlaneDecision(
        interaction_intent=intent,
        reasoning_depth=depth,
        effect_ceiling=effect,
        reason_codes=tuple(dict.fromkeys(reasons)),
        risk_signals=risks,
        foreground_reply_allowed=True,
        asynchronous_readonly_allowed=(
            intent is InteractionIntent.RESEARCH or depth is not ReasoningDepth.FAST
        ),
        requires_authenticated_authority=intent in {
            InteractionIntent.AUTHORIZE,
            InteractionIntent.CANCEL,
        },
    )


def _interaction_intent(text: str) -> tuple[InteractionIntent, str]:
    if _CANCEL.search(text):
        return InteractionIntent.CANCEL, "intent_cancel_request"
    if _STATUS.search(text):
        return InteractionIntent.STATUS, "intent_status_readonly"
    if _AMBIGUOUS_AUTHORIZATION.search(text):
        return InteractionIntent.CHAT, "ambiguous_authorization_without_bound_proposal"
    if _AUTHORIZE.search(text):
        return InteractionIntent.AUTHORIZE, "intent_authorize_requires_existing_authority"
    if _CONVERSATIONAL_CONTENT.search(text):
        return InteractionIntent.CHAT, "intent_conversational_content"
    if _PROPOSE.search(text):
        return InteractionIntent.PROPOSE, "intent_work_proposal"
    if _RESEARCH.search(text):
        return InteractionIntent.RESEARCH, "intent_readonly_research"
    return InteractionIntent.CHAT, "intent_chat_default"


def _reasoning_depth(
    text: str,
    intent: InteractionIntent,
    risks: tuple[str, ...],
) -> tuple[ReasoningDepth, str]:
    if _EXPLICIT_PANEL.search(text) or len(risks) >= 2:
        return ReasoningDepth.PANEL, "reasoning_panel_required"
    if (
        _EXPLICIT_CRITIC.search(text)
        or risks
        or intent in {InteractionIntent.PROPOSE, InteractionIntent.AUTHORIZE}
    ):
        return ReasoningDepth.CRITIC, "reasoning_critic_required"
    return ReasoningDepth.FAST, "reasoning_fast_default"


def _effect_ceiling(intent: InteractionIntent) -> EffectCeiling:
    if intent in {InteractionIntent.RESEARCH, InteractionIntent.STATUS}:
        return EffectCeiling.READ_ONLY
    if intent in {InteractionIntent.PROPOSE, InteractionIntent.AUTHORIZE}:
        return EffectCeiling.PROPOSAL
    return EffectCeiling.NONE


def _risk_signals(text: str) -> tuple[str, ...]:
    return tuple(name for name, pattern in _RISK_PATTERNS if pattern.search(text))


def _normalized_operator_text(value: str) -> str:
    if type(value) is not str:
        raise ValueError("conversation_plane_operator_text_invalid")
    if not value.strip() or len(value) > MAX_TURN_CHARS or "\x00" in value:
        raise ValueError("conversation_plane_operator_text_invalid")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        raise ValueError("conversation_plane_operator_text_invalid")
    normalized = unicodedata.normalize("NFKC", value).strip()
    if not normalized or len(normalized) > MAX_TURN_CHARS:
        raise ValueError("conversation_plane_operator_text_invalid")
    return normalized


__all__ = ["MAX_TURN_CHARS", "classify_conversation_turn"]
