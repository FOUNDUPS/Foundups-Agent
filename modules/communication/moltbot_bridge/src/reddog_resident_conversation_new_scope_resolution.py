"""Resolve one empty-ID resident TURN into an exact grounded FoundUp scope."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract import (
    ResidentConversationOperation,
    ResidentConversationRequest,
    enforce_request_freshness,
    resident_conversation_request_reasons,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_request import (
    ConversationScopeCreateRequest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_digest import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_record import (
    verified_grounding,
)


INTENT_SCHEMA = "reddog_intent.v2"
SCOPE_TTL_SECONDS = 3600
_INTENT_FIELDS = frozenset(
    {
        "schema_version", "intent_id", "source_surface", "origin",
        "principal_ref", "foundup_id", "work_focus", "grounding_receipt",
        "submits_executable_authority", "client_request_id",
    }
)


def resolve_resident_conversation_new_scope_request(
    *, repo_root: Path, intent: Mapping[str, Any], grounding_receipt_id: str,
    request: ResidentConversationRequest, now_epoch: int,
) -> tuple[ConversationScopeCreateRequest | None, str]:
    """Return one trusted creation request without identity or effect authority."""

    reason = _new_turn_reason(request, now_epoch)
    if reason:
        return None, reason
    values, reason = _intent_values(intent, grounding_receipt_id, request)
    if reason:
        return None, reason
    try:
        grounded, reason = verified_grounding(
            repo_root, values["work_focus"], values["grounding_receipt"]
        )
        if reason or grounded.get("foundup_id") != values["foundup_id"]:
            return None, reason or "resident_conversation_new_scope_foundup_mismatch"
        return _create_request(values, request), ""
    except Exception:
        return None, "resident_conversation_new_scope_grounding_invalid"


def _new_turn_reason(request: ResidentConversationRequest, now_epoch: int) -> str:
    try:
        if type(now_epoch) is not int or now_epoch < 0:
            return "resident_conversation_now_invalid"
        reasons = resident_conversation_request_reasons(request)
        if reasons:
            return reasons[0]
        enforce_request_freshness(request, now_epoch=now_epoch)
        if request.issued_at > now_epoch:
            return "resident_conversation_new_scope_request_not_yet_valid"
        if (
            request.operation is not ResidentConversationOperation.TURN
            or request.conversation_id
            or request.expected_revision != -1
        ):
            return "resident_conversation_new_scope_turn_required"
    except ValueError as exc:
        return str(exc) or "resident_conversation_request_invalid"
    except Exception:
        return "resident_conversation_request_invalid"
    return ""


def _intent_values(
    intent: Mapping[str, Any], grounding_receipt_id: str,
    request: ResidentConversationRequest,
) -> tuple[dict[str, Any], str]:
    if type(intent) is not dict or set(intent) != _INTENT_FIELDS:
        return {}, "resident_conversation_new_scope_intent_invalid"
    try:
        payload = {key: intent[key] for key in _INTENT_FIELDS - {"intent_id"}}
        native_strings = (
            intent["schema_version"], intent["intent_id"], intent["source_surface"],
            intent["origin"], intent["principal_ref"], intent["foundup_id"],
            intent["work_focus"], intent["client_request_id"], grounding_receipt_id,
        )
        valid = bool(
            all(type(item) is str and item for item in native_strings)
            and type(intent["grounding_receipt"]) is dict
            and intent["schema_version"] == INTENT_SCHEMA
            and intent["source_surface"] == "editor_thin_client"
            and intent["origin"] == "extension"
            and intent["submits_executable_authority"] is False
            and intent["intent_id"] == canonical_digest(payload)
            and intent["client_request_id"] == request.request_id
            and intent["work_focus"] == request.operator_text
            and intent["grounding_receipt"].get("receipt_id")
            == grounding_receipt_id
        )
    except Exception:
        valid = False
    return (dict(intent), "") if valid else (
        {}, "resident_conversation_new_scope_intent_binding_invalid"
    )


def _create_request(
    values: Mapping[str, Any], request: ResidentConversationRequest,
) -> ConversationScopeCreateRequest:
    foundup_id = str(values["foundup_id"])
    return ConversationScopeCreateRequest(
        work_focus=str(values["work_focus"]),
        grounding_receipt=values["grounding_receipt"],
        discussion_foundup_ids=(foundup_id,),
        conversation_nonce=request.client_nonce,
        turn_id=request.turn_id,
        active_topic=foundup_id,
        current_objective="Begin a grounded RedDog conversation for this FoundUp.",
        ttl_seconds=SCOPE_TTL_SECONDS,
        scope_kind="foundup",
    )


__all__ = [
    "INTENT_SCHEMA", "SCOPE_TTL_SECONDS",
    "resolve_resident_conversation_new_scope_request",
]
