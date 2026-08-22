"""Bind a zero-authority resident request to authenticated AgentDB state."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract import (
    ResidentConversationOperation,
    ResidentConversationRequest,
    enforce_request_freshness,
    resident_conversation_request_reasons,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    AuthenticatedConversationScopeCapability,
    consume_conversation_scope_capability,
    conversation_scope_authority_view,
    discard_conversation_scope_capability,
    verify_record_with_scope_authority,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    canonical_digest,
    validate_record,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_record import (
    authority_matches,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)


SCHEMA_VERSION = "reddog_resident_conversation_scope_binding.v1"


@dataclass(frozen=True, slots=True)
class ResidentConversationScopeBindingResult:
    """Content-free, non-authoritative result of one scope admission."""

    accepted: bool
    status: str
    binding_id: str = ""
    operation: str = ""
    request_id: str = ""
    request_digest: str = ""
    conversation_id: str = ""
    expected_revision: int = -1
    current_revision: int = -1
    turn_id: str = ""
    current_turn_id: str = ""
    scope_kind: str = ""
    record_digest: str = ""
    revision_receipt_id: str = ""
    principal_record_digest: str = ""
    session_binding_digest: str = ""
    rejection_reasons: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION
    cas_reserved: bool = False
    grants_identity_authority: bool = False
    grants_effect_authority: bool = False
    no_agentdb_mutation_performed: bool = True
    no_model_invocation_performed: bool = True
    no_worker_dispatch_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def bind_resident_conversation_request_to_authenticated_scope(
    *,
    store: AgentDbConversationScopeStore,
    capability: AuthenticatedConversationScopeCapability,
    request: ResidentConversationRequest,
    now_epoch: int,
) -> ResidentConversationScopeBindingResult:
    """Consume identity proof and bind one request to current AgentDB state."""

    reason = _resident_request_rejection_reason(request, now_epoch)
    if reason:
        return _retire_and_reject_binding(capability, reason)
    if not request.conversation_id:
        return _retire_and_reject_binding(
            capability, "resident_conversation_new_scope_resolution_required"
        )
    record = _load_binding_record(store, request.conversation_id)
    if record is None:
        return _retire_and_reject_binding(
            capability, "resident_conversation_access_denied"
        )
    authority, view = _consume_current_record_authority(
        capability, record, now_epoch
    )
    if authority is None or view is None:
        return _binding_rejected("resident_conversation_access_denied")
    try:
        reason = _current_record_request_rejection_reason(
            record, request, now_epoch
        )
        return (
            _binding_rejected(reason)
            if reason
            else _accepted_scope_binding(record, view, request)
        )
    finally:
        discard_conversation_scope_capability(authority)


def _resident_request_rejection_reason(
    request: ResidentConversationRequest, now_epoch: int
) -> str:
    if type(now_epoch) is not int or now_epoch < 0:
        return "resident_conversation_now_invalid"
    reasons = resident_conversation_request_reasons(request)
    if reasons:
        return reasons[0]
    try:
        enforce_request_freshness(request, now_epoch=now_epoch)
    except ValueError as exc:
        return str(exc) or "resident_conversation_request_invalid"
    return ""


def _load_binding_record(
    store: AgentDbConversationScopeStore, conversation_id: str
) -> Mapping[str, Any] | None:
    try:
        loaded = store.load(conversation_id)
        if not isinstance(loaded, Mapping):
            return None
        record = loaded.get("record")
        if (
            not isinstance(record, Mapping)
            or record.get("conversation_id") != conversation_id
            or validate_record(record)
        ):
            return None
        return record
    except Exception:
        return None


def _consume_current_record_authority(
    capability: AuthenticatedConversationScopeCapability,
    record: Mapping[str, Any],
    now_epoch: int,
) -> tuple[Any, Mapping[str, Any] | None]:
    authority = None
    try:
        authority = consume_conversation_scope_capability(
            capability,
            active_foundup_id=str(record["authorized_foundup_id"]),
            discussion_foundup_ids=tuple(record["discussion_foundup_ids"]),
            now_epoch=now_epoch,
            scope_kind=str(record["scope_kind"]),
        )
        view = conversation_scope_authority_view(authority)
        verified = bool(
            authority is not None
            and view is not None
            and authority_matches(record, view)
            and verify_record_with_scope_authority(authority, record)
        )
    except Exception:
        view, verified = None, False
    if not verified:
        discard_conversation_scope_capability(authority)
        return None, None
    return authority, view


def _current_record_request_rejection_reason(
    record: Mapping[str, Any],
    request: ResidentConversationRequest,
    now_epoch: int,
) -> str:
    if int(now_epoch) >= int(record["expires_at"]):
        return "resident_conversation_scope_expired"
    if request.expected_revision != int(record["conversation_revision"]):
        return "resident_conversation_revision_conflict"
    current_turn = str(record["turn_id"])
    if request.operation is ResidentConversationOperation.TURN:
        return (
            "resident_conversation_turn_conflict"
            if request.turn_id == current_turn
            else ""
        )
    return (
        "resident_conversation_turn_conflict"
        if request.turn_id != current_turn
        else ""
    )


def _accepted_scope_binding(
    record: Mapping[str, Any],
    authority: Mapping[str, Any],
    request: ResidentConversationRequest,
) -> ResidentConversationScopeBindingResult:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "operation": request.operation.value,
        "request_id": request.request_id,
        "request_digest": request.request_digest(),
        "conversation_id": request.conversation_id,
        "expected_revision": request.expected_revision,
        "current_revision": int(record["conversation_revision"]),
        "turn_id": request.turn_id,
        "current_turn_id": str(record["turn_id"]),
        "scope_kind": str(record["scope_kind"]),
        "record_digest": str(record["record_digest"]),
        "revision_receipt_id": str(record["revision_receipts"][-1]["receipt_id"]),
        "principal_record_digest": str(authority["principal_record_digest"]),
        "session_binding_digest": str(authority["session_binding_digest"]),
    }
    return ResidentConversationScopeBindingResult(
        accepted=True,
        status="RESIDENT_CONVERSATION_SCOPE_BOUND",
        binding_id=canonical_digest(payload),
        **{key: value for key, value in payload.items() if key != "schema_version"},
    )


def _retire_and_reject_binding(
    capability: Any, reason: str
) -> ResidentConversationScopeBindingResult:
    discard_conversation_scope_capability(capability)
    return _binding_rejected(reason)


def _binding_rejected(reason: str) -> ResidentConversationScopeBindingResult:
    return ResidentConversationScopeBindingResult(
        accepted=False,
        status="RESIDENT_CONVERSATION_SCOPE_REJECT",
        rejection_reasons=(reason,),
    )


__all__ = [
    "ResidentConversationScopeBindingResult",
    "SCHEMA_VERSION",
    "bind_resident_conversation_request_to_authenticated_scope",
]
