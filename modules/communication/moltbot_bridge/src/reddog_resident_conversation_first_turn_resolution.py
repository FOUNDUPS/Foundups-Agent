"""Current-generation aggregate for one durable resolved initial TURN."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract import (
    ResidentConversationRequest,
)
from modules.communication.moltbot_bridge.src.reddog_authenticated_conversation_scope_state import (
    create_authenticated_conversation_scope_from_verified_authority,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    discard_conversation_scope_capability,
    resident_conversation_request_journal_authority_matches,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_identity import (
    conversation_scope_id,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_session_authority_source import (
    ConversationSessionAuthoritySourceError,
    lease_current_generation_conversation_session,
    public_conversation_session_authority_reason,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_first_turn_binding import (
    bind_resolved_initial_turn_to_verified_scope_authority,
    validate_resolved_initial_turn_replay,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_first_turn_contract import (
    ResidentConversationFirstTurnResolutionResult,
    accepted_first_turn_result,
    first_turn_request_binding_digest,
    first_turn_reservation_identity,
    first_turn_reservation_record,
    first_turn_reservation_record_reasons,
    rejected_first_turn_result,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_new_scope_resolution import (
    resolve_resident_conversation_new_scope_request,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_request_journal_store import (
    AgentDbResidentConversationRequestJournal,
)


UNAVAILABLE_REASON = "resident_conversation_first_turn_resolution_unavailable"
_STORE_FIELDS = frozenset({"ok", "reason", "record", "stored", "idempotent_replay"})
_LOAD_FAILURES = frozenset(
    {
        "resident_conversation_request_reservation_missing",
        "resident_conversation_request_idempotency_conflict",
        "resident_conversation_request_journal_unavailable",
    }
)
_RESERVE_FAILURES = frozenset(
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


def resolve_current_generation_resident_conversation_first_turn(
    *, repo_root: Path, intent: Mapping[str, Any], grounding_receipt_id: str,
    serialized_credential: str, owner_config_path: str, now_epoch: int,
    scope_store: AgentDbConversationScopeStore,
    request_journal: AgentDbResidentConversationRequestJournal,
    request: ResidentConversationRequest,
) -> ResidentConversationFirstTurnResolutionResult:
    """Create/recover E0 and durably link the exact empty-ID request to it."""
    creation, reason = resolve_resident_conversation_new_scope_request(
        repo_root=repo_root, intent=intent, request=request, now_epoch=now_epoch,
        grounding_receipt_id=grounding_receipt_id,
    )
    if reason or creation is None:
        rejected = reason or "resident_conversation_new_scope_intent_invalid"
        return rejected_first_turn_result(rejected)
    try:
        with lease_current_generation_conversation_session(
            repo_root=repo_root, intent=intent,
            grounding_receipt_id=grounding_receipt_id,
            serialized_credential=serialized_credential,
            owner_config_path=owner_config_path, now_epoch=now_epoch,
            include_principal_scope_capability=False,
            include_secondary_foundup_authority=True,
            require_record_signing_context=True,
        ) as session:
            secondary = session.secondary_authority
            if secondary is None:
                return rejected_first_turn_result(UNAVAILABLE_REASON)
            resolved = _resolved_request(session, creation, intent, request)
            creation = _request_bound_creation(creation, request, resolved)
            loaded = request_journal.load_related(
                conversation_id=resolved.conversation_id,
                idempotency_key=resolved.idempotency_key,
                request_id=resolved.request_id,
                client_nonce=resolved.client_nonce,
            )
            return _resolve_after_authenticated_lookup(
                repo_root=repo_root, creation=creation, request=request,
                resolved=resolved, loaded=loaded, session=session,
                scope_store=scope_store, request_journal=request_journal,
                now_epoch=now_epoch,
            )
    except ConversationSessionAuthoritySourceError as exc:
        return rejected_first_turn_result(
            public_conversation_session_authority_reason(
                exc, unavailable_reason=UNAVAILABLE_REASON
            )
        )
    except Exception:
        return rejected_first_turn_result(UNAVAILABLE_REASON)


def _request_bound_creation(
    creation: Any, source: ResidentConversationRequest,
    resolved: ResidentConversationRequest,
) -> Any:
    return replace(
        creation,
        initial_turn_request_binding_digest=first_turn_request_binding_digest(
            source, resolved
        ),
    )


def _resolved_request(
    session: Any, creation: Any, intent: Mapping[str, Any],
    request: ResidentConversationRequest,
) -> ResidentConversationRequest:
    identity = (
        str(session.authority_receipt["session_id"])
        or str(session.session_binding_digest)
    )
    return replace(
        request,
        conversation_id=conversation_scope_id(
            principal_id=session.principal_id, scope_kind=creation.scope_kind,
            foundup_id=str(intent["foundup_id"]),
            discussion_foundup_ids=creation.discussion_foundup_ids,
            session_identity=identity, conversation_nonce=creation.conversation_nonce,
        ),
        expected_revision=0,
    )


def _resolve_after_authenticated_lookup(
    *, repo_root: Path, creation: Any, request: ResidentConversationRequest,
    resolved: ResidentConversationRequest, loaded: Any, session: Any,
    scope_store: AgentDbConversationScopeStore,
    request_journal: AgentDbResidentConversationRequestJournal,
    now_epoch: int,
) -> ResidentConversationFirstTurnResolutionResult:
    state, record = _loaded_state(loaded)
    if state == "found" and record is not None:
        reason = validate_resolved_initial_turn_replay(
            store=scope_store, authority=session.authority,
            source_request=request, resolved_request=resolved,
            reservation=record, now_epoch=now_epoch,
        )
        return (
            rejected_first_turn_result(reason)
            if reason else accepted_first_turn_result(
                record, stored=False, idempotent=True
            )
        )
    if state != "missing":
        return rejected_first_turn_result(state)
    created = create_authenticated_conversation_scope_from_verified_authority(
        store=scope_store, authority=session.authority, repo_root=repo_root,
        request=creation, now_epoch=now_epoch, record_epoch=request.issued_at,
        minimum_expires_at=request.expires_at,
    )
    if (
        not created.accepted
        or created.conversation_id != resolved.conversation_id
        or created.conversation_revision != 0
    ):
        reason = (
            created.rejection_reasons[0]
            if created.rejection_reasons else UNAVAILABLE_REASON
        )
        return rejected_first_turn_result(reason)
    binding = bind_resolved_initial_turn_to_verified_scope_authority(
        store=scope_store, authority=session.secondary_authority,
        source_request=request, resolved_request=resolved, now_epoch=now_epoch,
    )
    if not binding.accepted:
        return rejected_first_turn_result(
            binding.rejection_reasons[0]
            if binding.rejection_reasons else UNAVAILABLE_REASON
        )
    return _reserve(request_journal, request, resolved, binding, now_epoch)


def _reserve(
    journal: AgentDbResidentConversationRequestJournal,
    source: ResidentConversationRequest, resolved: ResidentConversationRequest,
    binding: Any, now_epoch: int,
) -> ResidentConversationFirstTurnResolutionResult:
    candidate = first_turn_reservation_record(source, resolved, binding, now_epoch)
    authority = getattr(binding, "_reservation_capability", None)
    if not resident_conversation_request_journal_authority_matches(
        authority, reservation_id=candidate["reservation_id"], reserved_at=now_epoch,
    ):
        discard_conversation_scope_capability(authority)
        return rejected_first_turn_result("resident_conversation_first_turn_binding_invalid")
    try:
        stored = journal.reserve(candidate, admission_authority=authority)
    except Exception:
        return rejected_first_turn_result(UNAVAILABLE_REASON)
    finally:
        discard_conversation_scope_capability(authority)
    reason, value = _stored_state(stored, candidate)
    return (
        rejected_first_turn_result(reason)
        if reason or value is None else accepted_first_turn_result(
            value, stored=bool(stored["stored"]),
            idempotent=bool(stored["idempotent_replay"]),
        )
    )


def _loaded_state(result: Any) -> tuple[str, Mapping[str, Any] | None]:
    if not isinstance(result, Mapping) or set(result) != _STORE_FIELDS:
        return UNAVAILABLE_REASON, None
    if result.get("ok") is True and isinstance(result.get("record"), dict):
        return "found", result["record"]
    reason = result.get("reason")
    if reason == "resident_conversation_request_reservation_missing":
        return "missing", None
    return (str(reason), None) if reason in _LOAD_FAILURES else (UNAVAILABLE_REASON, None)


def _stored_state(
    result: Any, candidate: Mapping[str, Any],
) -> tuple[str, Mapping[str, Any] | None]:
    if not isinstance(result, Mapping) or set(result) != _STORE_FIELDS:
        return UNAVAILABLE_REASON, None
    if result.get("ok") is False:
        reason = result.get("reason")
        return (str(reason), None) if reason in _RESERVE_FAILURES else (UNAVAILABLE_REASON, None)
    value = result.get("record")
    flags = (result.get("stored"), result.get("idempotent_replay"))
    valid = bool(
        result.get("reason") == "" and isinstance(value, dict)
        and not first_turn_reservation_record_reasons(value)
        and first_turn_reservation_identity(value)
        == first_turn_reservation_identity(candidate)
        and flags in {(True, False), (False, True)}
    )
    return ("", value) if valid else (UNAVAILABLE_REASON, None)


__all__ = [
    "UNAVAILABLE_REASON",
    "resolve_current_generation_resident_conversation_first_turn",
]
