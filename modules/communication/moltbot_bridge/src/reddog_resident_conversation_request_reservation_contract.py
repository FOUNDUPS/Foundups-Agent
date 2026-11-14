"""Pure contract for content-free resident conversation request reservations."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Mapping

from modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract import (
    ResidentConversationOperation,
    ResidentConversationRequest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    canonical_digest,
)

if TYPE_CHECKING:
    from modules.communication.moltbot_bridge.src.reddog_resident_conversation_scope_binding import (
        ResidentConversationScopeBindingResult,
    )


SCHEMA_VERSION = "reddog_resident_conversation_request_reservation.v1"
STATUS_RESERVED = "RESIDENT_CONVERSATION_REQUEST_RESERVED"
STATUS_REJECTED = "RESIDENT_CONVERSATION_REQUEST_REJECT"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RECORD_FIELDS = frozenset(
    {
        "schema_version", "reservation_id", "operation", "request_id",
        "request_digest", "conversation_id", "expected_revision", "turn_id",
        "client_nonce", "idempotency_key", "issued_at", "expires_at",
        "binding_id", "scope_record_digest", "revision_receipt_id", "reserved_at",
    }
)


@dataclass(frozen=True, slots=True)
class ResidentConversationRequestReservationResult:
    """Content-free result for one durable request reservation."""

    accepted: bool
    status: str
    reservation_id: str = ""
    operation: str = ""
    request_id: str = ""
    request_digest: str = ""
    conversation_id: str = ""
    expected_revision: int = -1
    turn_id: str = ""
    binding_id: str = ""
    stored: bool = False
    idempotent_replay: bool = False
    rejection_reasons: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION
    conversation_cas_reserved: bool = False
    conversation_scope_mutation_performed: bool = False
    grants_identity_authority: bool = False
    grants_effect_authority: bool = False
    no_model_invocation_performed: bool = True
    no_worker_dispatch_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def reservation_record(
    request: ResidentConversationRequest,
    binding: "ResidentConversationScopeBindingResult",
    now_epoch: int,
) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "operation": request.operation.value,
        "request_id": request.request_id,
        "request_digest": request.request_digest(),
        "conversation_id": request.conversation_id,
        "expected_revision": request.expected_revision,
        "turn_id": request.turn_id,
        "client_nonce": request.client_nonce,
        "idempotency_key": request.idempotency_key,
        "issued_at": request.issued_at,
        "expires_at": request.expires_at,
        "binding_id": binding.binding_id,
        "scope_record_digest": binding.record_digest,
        "revision_receipt_id": binding.revision_receipt_id,
    }
    return {
        **payload, "reservation_id": canonical_digest(payload),
        "reserved_at": now_epoch,
    }


def reservation_record_reasons(record: Mapping[str, Any]) -> tuple[str, ...]:
    if type(record) is not dict or set(record) != _RECORD_FIELDS:
        return ("resident_conversation_request_reservation_shape_invalid",)
    if record.get("schema_version") != SCHEMA_VERSION:
        return ("resident_conversation_request_reservation_schema_invalid",)
    numeric = ("expected_revision", "issued_at", "expires_at", "reserved_at")
    strings = tuple(record.get(name) for name in _RECORD_FIELDS - set(numeric))
    integers = tuple(record.get(name) for name in numeric)
    if not all(type(value) is str for value in strings) or not all(
        type(value) is int for value in integers
    ):
        return ("resident_conversation_request_reservation_type_invalid",)
    if record["operation"] not in {item.value for item in ResidentConversationOperation}:
        return ("resident_conversation_request_reservation_operation_invalid",)
    if (
        record["expected_revision"] < 0
        or record["issued_at"] < 0
        or record["expires_at"] <= record["issued_at"]
        or not record["issued_at"] <= record["reserved_at"] < record["expires_at"]
    ):
        return ("resident_conversation_request_reservation_time_invalid",)
    digests = tuple(record[name] for name in (
        "reservation_id", "request_id", "request_digest", "conversation_id",
        "turn_id", "client_nonce", "idempotency_key", "binding_id",
        "scope_record_digest", "revision_receipt_id",
    ))
    if not all(digest_shaped(value) for value in digests):
        return ("resident_conversation_request_reservation_binding_invalid",)
    if record["reservation_id"] != canonical_digest(reservation_identity(record)):
        return ("resident_conversation_request_reservation_digest_invalid",)
    return ()


def reservation_identity(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: record[key]
        for key in _RECORD_FIELDS - {"reservation_id", "reserved_at"}
    }


def accepted_result(
    record: Mapping[str, Any], *, stored: bool, idempotent: bool
) -> ResidentConversationRequestReservationResult:
    return ResidentConversationRequestReservationResult(
        accepted=True, status=STATUS_RESERVED,
        reservation_id=str(record["reservation_id"]), operation=str(record["operation"]),
        request_id=str(record["request_id"]), request_digest=str(record["request_digest"]),
        conversation_id=str(record["conversation_id"]),
        expected_revision=int(record["expected_revision"]), turn_id=str(record["turn_id"]),
        binding_id=str(record["binding_id"]), stored=stored, idempotent_replay=idempotent,
    )


def rejected_result(reason: str) -> ResidentConversationRequestReservationResult:
    return ResidentConversationRequestReservationResult(
        accepted=False, status=STATUS_REJECTED, rejection_reasons=(reason,)
    )


def digest_shaped(value: object) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


__all__ = [
    "ResidentConversationRequestReservationResult", "SCHEMA_VERSION",
    "STATUS_REJECTED", "STATUS_RESERVED",
]
