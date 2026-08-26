"""Bind and replay-check one resolved initial TURN against signed AgentDB state."""

from __future__ import annotations

from typing import Any, Mapping

from modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract import (
    ResidentConversationOperation,
    ResidentConversationRequest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    VerifiedConversationScopeAuthority,
    consume_and_verify_record_with_scope_authority,
    consume_verified_scope_authority_for_request_journal,
    conversation_scope_authority_view,
    discard_conversation_scope_capability,
    verify_record_with_scope_authority,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    validate_record,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_record import (
    authority_matches,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_first_turn_contract import (
    BINDING_SCHEMA_VERSION,
    ResidentConversationFirstTurnBindingResult,
    first_turn_request_binding_digest,
    first_turn_reservation_record,
    first_turn_reservation_record_reasons,
    first_turn_scope_binding_id,
)


def bind_resolved_initial_turn_to_verified_scope_authority(
    *, store: AgentDbConversationScopeStore,
    authority: VerifiedConversationScopeAuthority,
    source_request: ResidentConversationRequest,
    resolved_request: ResidentConversationRequest,
    now_epoch: int,
) -> ResidentConversationFirstTurnBindingResult:
    """Consume one sibling authority and mint a v2 journal proof for E0."""

    reason = _request_pair_reason(source_request, resolved_request, now_epoch)
    if reason:
        return _retire_and_reject(authority, reason)
    record = _load_record(store, resolved_request.conversation_id)
    view = conversation_scope_authority_view(authority)
    if not _authenticated_record(authority, view, record):
        return _retire_and_reject(authority, "resident_conversation_access_denied")
    try:
        reason = _initial_scope_reason(
            record, source_request, resolved_request, now_epoch
        )
        if reason:
            return _rejected(reason)
        receipt = record["revision_receipts"][0]
        payload = _binding_payload(
            source_request, resolved_request, record, receipt, view
        )
        result = ResidentConversationFirstTurnBindingResult(
            accepted=True, status="RESIDENT_CONVERSATION_FIRST_TURN_BOUND",
            binding_id=_scope_binding_id(record, receipt, view),
            **{key: value for key, value in payload.items() if key != "schema_version"},
        )
        candidate = first_turn_reservation_record(
            source_request, resolved_request, result, now_epoch
        )
        proof = consume_verified_scope_authority_for_request_journal(
            authority, record=record, reservation_id=candidate["reservation_id"],
            not_before_epoch=now_epoch,
            scope_expires_at=min(int(record["expires_at"]), int(view["expires_at"])),
        )
        if proof is None:
            return _rejected("resident_conversation_access_denied")
        object.__setattr__(result, "_reservation_capability", proof)
        return result
    except Exception:
        return _rejected("resident_conversation_access_denied")
    finally:
        discard_conversation_scope_capability(authority)


def validate_resolved_initial_turn_replay(
    *, store: AgentDbConversationScopeStore,
    authority: VerifiedConversationScopeAuthority,
    source_request: ResidentConversationRequest,
    resolved_request: ResidentConversationRequest,
    reservation: Mapping[str, Any],
    now_epoch: int,
) -> str:
    """Consume authority and validate one immutable E0 link at current state."""

    try:
        if _request_pair_reason(source_request, resolved_request, now_epoch):
            return "resident_conversation_first_turn_replay_invalid"
        if first_turn_reservation_record_reasons(reservation):
            return "resident_conversation_first_turn_replay_invalid"
        if _reservation_pair_reason(reservation, source_request, resolved_request):
            return "resident_conversation_request_idempotency_conflict"
        record = _load_record(store, resolved_request.conversation_id)
        view = consume_and_verify_record_with_scope_authority(authority, record)
        if not isinstance(view, Mapping):
            return "resident_conversation_access_denied"
        return _replay_binding_reason(
            record, reservation, source_request, resolved_request, view, now_epoch
        )
    except Exception:
        return "resident_conversation_first_turn_replay_invalid"
    finally:
        discard_conversation_scope_capability(authority)


def _replay_binding_reason(
    record: Mapping[str, Any], reservation: Mapping[str, Any],
    source: ResidentConversationRequest, resolved: ResidentConversationRequest,
    view: Mapping[str, Any], now_epoch: int,
) -> str:
    if int(now_epoch) >= int(record["expires_at"]):
        return "resident_conversation_scope_expired"
    first = record["revision_receipts"][0]
    request_binding = first_turn_request_binding_digest(source, resolved)
    valid = bool(
        first.get("revision") == 0
        and first.get("previous_receipt_id") == ""
        and first.get("receipt_id") == reservation["revision_receipt_id"]
        and first.get("state_digest") == reservation["initial_scope_state_digest"]
        and record.get("initial_turn_request_binding_digest") == request_binding
        and reservation.get("initial_turn_request_binding_digest") == request_binding
        and reservation.get("binding_id") == _scope_binding_id(record, first, view)
        and (
            int(record["conversation_revision"]) != 0
            or record.get("record_digest") == reservation["scope_record_digest"]
        )
    )
    return "" if valid else "resident_conversation_first_turn_replay_invalid"


def _request_pair_reason(
    source: ResidentConversationRequest,
    resolved: ResidentConversationRequest,
    now_epoch: int,
) -> str:
    if type(source) is not ResidentConversationRequest or type(resolved) is not ResidentConversationRequest:
        return "resident_conversation_request_type_invalid"
    source_values = source.to_dict()
    expected = {
        **source_values,
        "conversation_id": resolved.conversation_id,
        "expected_revision": 0,
    }
    if (
        source.operation is not ResidentConversationOperation.TURN
        or source.conversation_id != ""
        or source.expected_revision != -1
        or resolved.to_dict() != expected
        or type(now_epoch) is not int
        or not source.issued_at <= now_epoch < source.expires_at
    ):
        return "resident_conversation_first_turn_request_invalid"
    return ""


def _initial_scope_reason(
    record: Mapping[str, Any], source: ResidentConversationRequest,
    resolved: ResidentConversationRequest, now_epoch: int,
) -> str:
    if int(now_epoch) >= int(record["expires_at"]):
        return "resident_conversation_scope_expired"
    if (
        record.get("conversation_revision") != 0
        or record.get("turn_id") != source.turn_id
        or record.get("created_at") != source.issued_at
        or int(record["expires_at"]) < source.expires_at
        or record.get("initial_turn_request_binding_digest")
        != first_turn_request_binding_digest(source, resolved)
        or len(record.get("revision_receipts", ())) != 1
    ):
        return "resident_conversation_first_turn_scope_conflict"
    return ""


def _binding_payload(
    source: ResidentConversationRequest, resolved: ResidentConversationRequest,
    record: Mapping[str, Any], receipt: Mapping[str, Any],
    view: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": BINDING_SCHEMA_VERSION,
        "operation": resolved.operation.value,
        "request_id": resolved.request_id,
        "request_digest": resolved.request_digest(),
        "source_request_digest": source.request_digest(),
        "conversation_id": resolved.conversation_id,
        "expected_revision": resolved.expected_revision,
        "turn_id": resolved.turn_id,
        "initial_turn_request_binding_digest": str(
            record["initial_turn_request_binding_digest"]
        ),
        "scope_record_digest": str(record["record_digest"]),
        "revision_receipt_id": str(receipt["receipt_id"]),
        "initial_scope_state_digest": str(receipt["state_digest"]),
        "principal_record_digest": str(view["principal_record_digest"]),
        "session_binding_digest": str(view["session_binding_digest"]),
    }


def _scope_binding_id(
    record: Mapping[str, Any], receipt: Mapping[str, Any], view: Mapping[str, Any],
) -> str:
    return first_turn_scope_binding_id(
        request_binding_digest=str(record["initial_turn_request_binding_digest"]),
        revision_receipt_id=str(receipt["receipt_id"]),
        initial_scope_state_digest=str(receipt["state_digest"]),
        principal_record_digest=str(view["principal_record_digest"]),
        session_binding_digest=str(view["session_binding_digest"]),
    )


def _reservation_pair_reason(
    record: Mapping[str, Any], source: ResidentConversationRequest,
    resolved: ResidentConversationRequest,
) -> str:
    expected = (
        resolved.operation.value, resolved.request_id, resolved.request_digest(),
        source.request_digest(), source.conversation_id, source.expected_revision,
        resolved.conversation_id, resolved.expected_revision, resolved.turn_id,
        resolved.client_nonce, resolved.idempotency_key, resolved.issued_at,
        resolved.expires_at,
    )
    actual = tuple(
        record[name] for name in (
            "operation", "request_id", "request_digest", "source_request_digest",
            "source_conversation_id", "source_expected_revision", "conversation_id",
            "expected_revision", "turn_id", "client_nonce", "idempotency_key",
            "issued_at", "expires_at",
        )
    )
    return "" if actual == expected else "resident_conversation_request_idempotency_conflict"


def _load_record(
    store: AgentDbConversationScopeStore, conversation_id: str,
) -> Mapping[str, Any]:
    loaded = store.load(conversation_id)
    record = loaded.get("record") if isinstance(loaded, Mapping) else None
    return record if isinstance(record, Mapping) else {}


def _authenticated_record(authority: Any, view: Any, record: Any) -> bool:
    return bool(
        isinstance(view, Mapping) and isinstance(record, Mapping) and record
        and not validate_record(record) and authority_matches(record, view)
        and verify_record_with_scope_authority(authority, record)
    )


def _retire_and_reject(
    authority: Any, reason: str,
) -> ResidentConversationFirstTurnBindingResult:
    discard_conversation_scope_capability(authority)
    return _rejected(reason)


def _rejected(reason: str) -> ResidentConversationFirstTurnBindingResult:
    return ResidentConversationFirstTurnBindingResult(
        accepted=False, status="RESIDENT_CONVERSATION_FIRST_TURN_REJECT",
        rejection_reasons=(reason,),
    )


__all__ = [
    "bind_resolved_initial_turn_to_verified_scope_authority",
    "validate_resolved_initial_turn_replay",
]
