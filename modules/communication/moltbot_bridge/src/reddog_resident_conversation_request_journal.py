"""Authenticated durable replay reservation for RedDog conversation requests."""

from __future__ import annotations

from typing import Any, Mapping

from modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract import (
    ResidentConversationRequest,
    enforce_request_freshness,
    resident_conversation_request_reasons,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    discard_conversation_scope_capability,
    resident_conversation_request_journal_authority_matches,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_request_journal_store import (
    AgentDbResidentConversationRequestJournal,
    MAX_REQUESTS_PER_CONVERSATION,
    MAX_REQUESTS_TOTAL,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_request_reservation_contract import (
    ResidentConversationRequestReservationResult,
    SCHEMA_VERSION,
    STATUS_REJECTED,
    STATUS_RESERVED,
    accepted_result,
    digest_shaped,
    rejected_result,
    reservation_identity,
    reservation_record,
    reservation_record_reasons,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_scope_binding import (
    ResidentConversationScopeBindingResult,
    SCHEMA_VERSION as SCOPE_BINDING_SCHEMA_VERSION,
)


_STORE_RESULT_FIELDS = frozenset(
    {"ok", "reason", "record", "stored", "idempotent_replay"}
)
_STORE_FAILURE_REASONS = frozenset(
    {
        "resident_conversation_request_reservation_invalid",
        "resident_conversation_request_journal_admission_invalid",
        "resident_conversation_request_journal_unavailable",
        "resident_conversation_request_scope_changed",
        "resident_conversation_request_journal_integrity",
        "resident_conversation_request_journal_capacity",
        "resident_conversation_request_conversation_capacity",
        "resident_conversation_request_idempotency_conflict",
    }
)


def reserve_bound_resident_conversation_request(
    *,
    journal: AgentDbResidentConversationRequestJournal,
    request: ResidentConversationRequest,
    binding: ResidentConversationScopeBindingResult,
    now_epoch: int,
) -> ResidentConversationRequestReservationResult:
    """Consume binder proof and persist one zero-authority replay fence."""

    reason, admission_authority = _admission_reason(request, binding, now_epoch)
    if reason:
        return rejected_result(reason)
    candidate = reservation_record(request, binding, now_epoch)
    try:
        stored = journal.reserve(
            candidate, admission_authority=admission_authority
        )
    except Exception:
        return rejected_result("resident_conversation_request_journal_unavailable")
    finally:
        discard_conversation_scope_capability(admission_authority)
    reason, value = _stored_result_reason(stored, candidate)
    if reason or value is None:
        return rejected_result(reason or "resident_conversation_request_journal_unavailable")
    return accepted_result(
        value, stored=stored["stored"], idempotent=stored["idempotent_replay"]
    )


def _admission_reason(
    request: ResidentConversationRequest,
    binding: ResidentConversationScopeBindingResult,
    now_epoch: int,
) -> tuple[str, Any | None]:
    if type(now_epoch) is not int or now_epoch < 0:
        return "resident_conversation_now_invalid", None
    if type(request) is not ResidentConversationRequest:
        return "resident_conversation_request_type_invalid", None
    reasons = resident_conversation_request_reasons(request)
    if reasons:
        return reasons[0], None
    try:
        enforce_request_freshness(request, now_epoch=now_epoch)
    except ValueError as exc:
        return (str(exc) or "resident_conversation_request_invalid"), None
    if type(binding) is not ResidentConversationScopeBindingResult:
        return "resident_conversation_scope_binding_invalid", None
    return _binding_reason(request, binding, now_epoch)


def _binding_reason(
    request: ResidentConversationRequest,
    binding: ResidentConversationScopeBindingResult,
    now_epoch: int,
) -> tuple[str, Any | None]:
    expected = (
        request.operation.value, request.request_id, request.request_digest(),
        request.conversation_id, request.expected_revision, request.turn_id,
    )
    actual = (
        binding.operation, binding.request_id, binding.request_digest,
        binding.conversation_id, binding.expected_revision, binding.turn_id,
    )
    identity = _binding_identity(binding)
    invalid = (
        not binding.accepted
        or binding.status != "RESIDENT_CONVERSATION_SCOPE_BOUND"
        or binding.rejection_reasons
        or actual != expected
        or binding.current_revision != request.expected_revision
        or not digest_shaped(binding.binding_id)
        or binding.cas_reserved
        or binding.grants_identity_authority
        or binding.grants_effect_authority
        or not binding.no_agentdb_mutation_performed
        or not digest_shaped(binding.record_digest)
        or not digest_shaped(binding.revision_receipt_id)
        or binding.binding_id != canonical_digest(identity)
    )
    if invalid:
        return "resident_conversation_scope_binding_invalid", None
    candidate = reservation_record(request, binding, now_epoch)
    authority = getattr(binding, "_reservation_capability", None)
    authorized = resident_conversation_request_journal_authority_matches(
        authority,
        reservation_id=candidate["reservation_id"], reserved_at=now_epoch,
    )
    return (
        ("", authority) if authorized
        else ("resident_conversation_scope_binding_invalid", None)
    )


def _binding_identity(binding: ResidentConversationScopeBindingResult) -> dict[str, Any]:
    return {
        "schema_version": SCOPE_BINDING_SCHEMA_VERSION,
        "operation": binding.operation, "request_id": binding.request_id,
        "request_digest": binding.request_digest,
        "conversation_id": binding.conversation_id,
        "expected_revision": binding.expected_revision,
        "current_revision": binding.current_revision, "turn_id": binding.turn_id,
        "current_turn_id": binding.current_turn_id, "scope_kind": binding.scope_kind,
        "record_digest": binding.record_digest,
        "revision_receipt_id": binding.revision_receipt_id,
        "principal_record_digest": binding.principal_record_digest,
        "session_binding_digest": binding.session_binding_digest,
    }


def _stored_result_reason(
    stored: Any, candidate: Mapping[str, Any]
) -> tuple[str, Mapping[str, Any] | None]:
    unavailable = "resident_conversation_request_journal_unavailable"
    if not isinstance(stored, Mapping) or set(stored) != _STORE_RESULT_FIELDS:
        return unavailable, None
    if type(stored.get("ok")) is not bool:
        return unavailable, None
    if stored["ok"] is False:
        reason = stored.get("reason")
        return (str(reason), None) if reason in _STORE_FAILURE_REASONS else (unavailable, None)
    value = stored.get("record")
    flags = (stored.get("stored"), stored.get("idempotent_replay"))
    valid = (
        stored.get("reason") == ""
        and isinstance(value, dict)
        and not reservation_record_reasons(value)
        and reservation_identity(value) == reservation_identity(candidate)
        and all(type(flag) is bool for flag in flags)
        and flags in {(True, False), (False, True)}
    )
    return ("", value) if valid else (unavailable, None)


__all__ = [
    "AgentDbResidentConversationRequestJournal",
    "MAX_REQUESTS_PER_CONVERSATION",
    "MAX_REQUESTS_TOTAL",
    "ResidentConversationRequestReservationResult",
    "SCHEMA_VERSION",
    "STATUS_REJECTED",
    "STATUS_RESERVED",
    "reserve_bound_resident_conversation_request",
]
