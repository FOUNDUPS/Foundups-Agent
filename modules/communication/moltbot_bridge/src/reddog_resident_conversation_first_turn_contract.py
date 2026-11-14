"""Explicit v2 journal contract for an empty-ID TURN resolution link."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract import (
    ResidentConversationOperation,
    ResidentConversationRequest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_request_reservation_contract import (
    digest_shaped,
)


SCHEMA_VERSION = "reddog_resident_conversation_request_reservation.v2"
BINDING_SCHEMA_VERSION = "reddog_resident_conversation_first_turn_binding.v1"
RESERVATION_KIND = "RESOLVED_INITIAL_TURN"
STATUS_RESERVED = "RESIDENT_CONVERSATION_FIRST_TURN_RESERVED"
STATUS_REJECTED = "RESIDENT_CONVERSATION_FIRST_TURN_REJECT"
_RECORD_FIELDS = frozenset(
    {
        "schema_version", "reservation_kind", "reservation_id", "operation",
        "request_id", "request_digest", "source_request_digest",
        "source_conversation_id", "source_expected_revision", "conversation_id",
        "expected_revision", "turn_id", "client_nonce", "idempotency_key",
        "issued_at", "expires_at", "binding_id", "scope_record_digest",
        "initial_turn_request_binding_digest",
        "revision_receipt_id", "initial_scope_state_digest", "reserved_at",
    }
)


@dataclass(frozen=True, slots=True)
class ResidentConversationFirstTurnBindingResult:
    """Content-free proof that an initial TURN matches one signed E0 scope."""

    accepted: bool
    status: str
    binding_id: str = ""
    operation: str = ""
    request_id: str = ""
    request_digest: str = ""
    source_request_digest: str = ""
    conversation_id: str = ""
    expected_revision: int = -1
    turn_id: str = ""
    initial_turn_request_binding_digest: str = ""
    scope_record_digest: str = ""
    revision_receipt_id: str = ""
    initial_scope_state_digest: str = ""
    principal_record_digest: str = ""
    session_binding_digest: str = ""
    rejection_reasons: tuple[str, ...] = ()
    schema_version: str = BINDING_SCHEMA_VERSION
    grants_identity_authority: bool = False
    grants_effect_authority: bool = False
    no_agentdb_mutation_performed: bool = True
    no_model_invocation_performed: bool = True
    no_worker_dispatch_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    _reservation_capability: Any = field(
        default=None, init=False, repr=False, compare=False
    )


@dataclass(frozen=True, slots=True)
class ResidentConversationFirstTurnResolutionResult:
    """Content-free result for one durable initial-TURN resolution link."""

    accepted: bool
    status: str
    reservation_id: str = ""
    request_id: str = ""
    request_digest: str = ""
    source_request_digest: str = ""
    conversation_id: str = ""
    expected_revision: int = -1
    turn_id: str = ""
    binding_id: str = ""
    initial_turn_request_binding_digest: str = ""
    revision_receipt_id: str = ""
    stored: bool = False
    idempotent_replay: bool = False
    rejection_reasons: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION
    reservation_kind: str = RESERVATION_KIND
    conversation_cas_reserved: bool = False
    conversation_scope_created_or_exactly_recovered: bool = False
    grants_identity_authority: bool = False
    grants_effect_authority: bool = False
    no_model_invocation_performed: bool = True
    no_worker_dispatch_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def first_turn_reservation_record(
    source_request: ResidentConversationRequest,
    resolved_request: ResidentConversationRequest,
    binding: ResidentConversationFirstTurnBindingResult,
    now_epoch: int,
) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "reservation_kind": RESERVATION_KIND,
        "operation": resolved_request.operation.value,
        "request_id": resolved_request.request_id,
        "request_digest": resolved_request.request_digest(),
        "source_request_digest": source_request.request_digest(),
        "source_conversation_id": source_request.conversation_id,
        "source_expected_revision": source_request.expected_revision,
        "conversation_id": resolved_request.conversation_id,
        "expected_revision": resolved_request.expected_revision,
        "turn_id": resolved_request.turn_id,
        "client_nonce": resolved_request.client_nonce,
        "idempotency_key": resolved_request.idempotency_key,
        "issued_at": resolved_request.issued_at,
        "expires_at": resolved_request.expires_at,
        "binding_id": binding.binding_id,
        "initial_turn_request_binding_digest": (
            binding.initial_turn_request_binding_digest
        ),
        "scope_record_digest": binding.scope_record_digest,
        "revision_receipt_id": binding.revision_receipt_id,
        "initial_scope_state_digest": binding.initial_scope_state_digest,
    }
    return {
        **payload, "reservation_id": canonical_digest(payload),
        "reserved_at": now_epoch,
    }


def first_turn_reservation_record_reasons(
    record: Mapping[str, Any],
) -> tuple[str, ...]:
    if type(record) is not dict or set(record) != _RECORD_FIELDS:
        return ("resident_conversation_first_turn_reservation_shape_invalid",)
    numeric = (
        "source_expected_revision", "expected_revision", "issued_at",
        "expires_at", "reserved_at",
    )
    strings = tuple(record.get(name) for name in _RECORD_FIELDS - set(numeric))
    if not all(type(value) is str for value in strings) or not all(
        type(record.get(name)) is int for name in numeric
    ):
        return ("resident_conversation_first_turn_reservation_type_invalid",)
    if (
        record["schema_version"] != SCHEMA_VERSION
        or record["reservation_kind"] != RESERVATION_KIND
        or record["operation"] != ResidentConversationOperation.TURN.value
    ):
        return ("resident_conversation_first_turn_reservation_schema_invalid",)
    if (
        record["source_conversation_id"] != ""
        or record["source_expected_revision"] != -1
        or record["expected_revision"] != 0
        or record["issued_at"] < 0
        or record["expires_at"] <= record["issued_at"]
        or not record["issued_at"] <= record["reserved_at"] < record["expires_at"]
    ):
        return ("resident_conversation_first_turn_reservation_state_invalid",)
    digests = tuple(
        record[name] for name in (
            "reservation_id", "request_id", "request_digest",
            "source_request_digest", "conversation_id", "turn_id", "client_nonce",
            "idempotency_key", "binding_id", "scope_record_digest",
            "initial_turn_request_binding_digest",
            "revision_receipt_id", "initial_scope_state_digest",
        )
    )
    if not all(digest_shaped(value) for value in digests):
        return ("resident_conversation_first_turn_reservation_binding_invalid",)
    if record["reservation_id"] != canonical_digest(
        first_turn_reservation_identity(record)
    ):
        return ("resident_conversation_first_turn_reservation_digest_invalid",)
    return ()


def first_turn_reservation_identity(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: record[key]
        for key in _RECORD_FIELDS - {"reservation_id", "reserved_at"}
    }


def accepted_first_turn_result(
    record: Mapping[str, Any], *, stored: bool, idempotent: bool,
) -> ResidentConversationFirstTurnResolutionResult:
    return ResidentConversationFirstTurnResolutionResult(
        accepted=True, status=STATUS_RESERVED,
        reservation_id=str(record["reservation_id"]),
        request_id=str(record["request_id"]),
        request_digest=str(record["request_digest"]),
        source_request_digest=str(record["source_request_digest"]),
        conversation_id=str(record["conversation_id"]),
        expected_revision=int(record["expected_revision"]),
        turn_id=str(record["turn_id"]), binding_id=str(record["binding_id"]),
        initial_turn_request_binding_digest=str(
            record["initial_turn_request_binding_digest"]
        ),
        revision_receipt_id=str(record["revision_receipt_id"]),
        stored=stored, idempotent_replay=idempotent,
        conversation_scope_created_or_exactly_recovered=True,
    )


def rejected_first_turn_result(
    reason: str,
) -> ResidentConversationFirstTurnResolutionResult:
    return ResidentConversationFirstTurnResolutionResult(
        accepted=False, status=STATUS_REJECTED, rejection_reasons=(reason,)
    )


def first_turn_request_binding_digest(
    source: ResidentConversationRequest, resolved: ResidentConversationRequest,
) -> str:
    """Commit the exact empty-ID request and its deterministic resolved form."""

    return canonical_digest(
        {
            "schema_version": BINDING_SCHEMA_VERSION,
            "source_request": source.to_dict(),
            "resolved_request": resolved.to_dict(),
        }
    )


def first_turn_scope_binding_id(
    *, request_binding_digest: str, revision_receipt_id: str,
    initial_scope_state_digest: str, principal_record_digest: str,
    session_binding_digest: str,
) -> str:
    """Bind request identity to authenticated E0 and session identity."""

    return canonical_digest(
        {
            "schema_version": BINDING_SCHEMA_VERSION,
            "initial_turn_request_binding_digest": request_binding_digest,
            "revision_receipt_id": revision_receipt_id,
            "initial_scope_state_digest": initial_scope_state_digest,
            "principal_record_digest": principal_record_digest,
            "session_binding_digest": session_binding_digest,
        }
    )


__all__ = [
    "BINDING_SCHEMA_VERSION", "RESERVATION_KIND", "SCHEMA_VERSION",
    "ResidentConversationFirstTurnBindingResult",
    "ResidentConversationFirstTurnResolutionResult",
    "accepted_first_turn_result", "first_turn_reservation_identity",
    "first_turn_reservation_record", "first_turn_reservation_record_reasons",
    "first_turn_request_binding_digest", "first_turn_scope_binding_id",
    "rejected_first_turn_result",
]
