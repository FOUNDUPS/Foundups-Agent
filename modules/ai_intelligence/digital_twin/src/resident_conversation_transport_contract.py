"""Strict zero-authority envelope for resident RedDog conversation traffic."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


SCHEMA_VERSION = "reddog_resident_conversation_request.v1"
BINDING_SCHEMA_VERSION = "reddog_resident_conversation_binding.v1"
MAX_OPERATOR_TEXT_SCALARS = 12_000
MAX_REQUEST_TTL_SECONDS = 300
MAX_CLOCK_SKEW_SECONDS = 30

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "operation",
        "request_id",
        "conversation_id",
        "expected_revision",
        "turn_id",
        "client_nonce",
        "idempotency_key",
        "issued_at",
        "expires_at",
        "operator_text",
    }
)


class ResidentConversationOperation(str, Enum):
    """Transport operations; none grants model or effect authority."""

    TURN = "TURN"
    STATUS = "STATUS"
    CANCEL = "CANCEL"


@dataclass(frozen=True, slots=True)
class ResidentConversationRequest:
    """One untrusted client envelope after strict structural validation."""

    operation: ResidentConversationOperation
    request_id: str
    conversation_id: str
    expected_revision: int
    turn_id: str
    client_nonce: str
    idempotency_key: str
    issued_at: int
    expires_at: int
    operator_text: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        reasons = resident_conversation_request_reasons(self)
        if reasons:
            raise ValueError(reasons[0])

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "operation": self.operation.value,
            "request_id": self.request_id,
            "conversation_id": self.conversation_id,
            "expected_revision": self.expected_revision,
            "turn_id": self.turn_id,
            "client_nonce": self.client_nonce,
            "idempotency_key": self.idempotency_key,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "operator_text": self.operator_text,
        }

    def request_digest(self) -> str:
        """Return a canonical integrity digest, not an authentication proof."""

        return _canonical_digest(self.to_dict())

    def content_free_binding(self) -> dict[str, Any]:
        """Project receipt-safe metadata without operator text or identity claims."""

        return {
            "schema_version": BINDING_SCHEMA_VERSION,
            "operation": self.operation.value,
            "request_id": self.request_id,
            "request_digest": self.request_digest(),
            "conversation_id": self.conversation_id,
            "expected_revision": self.expected_revision,
            "turn_id": self.turn_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "grants_identity_authority": False,
            "grants_effect_authority": False,
        }


def request_from_mapping(
    payload: Mapping[str, Any], *, now_epoch: int
) -> ResidentConversationRequest:
    """Strictly rehydrate and freshness-check an untrusted client request."""

    if type(payload) is not dict or set(payload) != _REQUEST_FIELDS:
        raise ValueError("resident_conversation_request_shape_invalid")
    request = ResidentConversationRequest(
        schema_version=_strict_string(payload["schema_version"]),
        operation=_strict_operation(payload["operation"]),
        request_id=_strict_string(payload["request_id"]),
        conversation_id=_strict_string(payload["conversation_id"]),
        expected_revision=_strict_integer(payload["expected_revision"]),
        turn_id=_strict_string(payload["turn_id"]),
        client_nonce=_strict_string(payload["client_nonce"]),
        idempotency_key=_strict_string(payload["idempotency_key"]),
        issued_at=_strict_integer(payload["issued_at"]),
        expires_at=_strict_integer(payload["expires_at"]),
        operator_text=_normalized_operator_text(payload["operator_text"]),
    )
    enforce_request_freshness(request, now_epoch=now_epoch)
    return request


def enforce_request_freshness(
    request: ResidentConversationRequest, *, now_epoch: int
) -> None:
    """Reject expired or implausibly future-dated envelopes."""

    if type(request) is not ResidentConversationRequest:
        raise ValueError("resident_conversation_request_type_invalid")
    if type(now_epoch) is not int or now_epoch < 0:
        raise ValueError("resident_conversation_now_invalid")
    if request.issued_at > now_epoch + MAX_CLOCK_SKEW_SECONDS:
        raise ValueError("resident_conversation_request_not_yet_valid")
    if request.expires_at <= now_epoch:
        raise ValueError("resident_conversation_request_expired")


def resident_conversation_request_reasons(
    request: ResidentConversationRequest,
) -> tuple[str, ...]:
    """Return stable violations without consulting authentication or runtime state."""

    if type(request) is not ResidentConversationRequest:
        return ("resident_conversation_request_type_invalid",)
    reasons: list[str] = []
    if request.schema_version != SCHEMA_VERSION:
        reasons.append("resident_conversation_schema_invalid")
    if type(request.operation) is not ResidentConversationOperation:
        reasons.append("resident_conversation_operation_invalid")
    if not _native_request_scalars(request):
        reasons.append("resident_conversation_request_type_invalid")
    if not _canonical_operator_text(request.operator_text):
        reasons.append("resident_conversation_operator_text_invalid")
    if not all(
        _SHA256_RE.fullmatch(value)
        for value in (
            request.request_id,
            request.turn_id,
            request.client_nonce,
            request.idempotency_key,
        )
    ):
        reasons.append("resident_conversation_request_binding_invalid")
    if request.conversation_id and not _SHA256_RE.fullmatch(request.conversation_id):
        reasons.append("resident_conversation_conversation_id_invalid")
    if not _valid_time_window(request):
        reasons.append("resident_conversation_request_ttl_invalid")
    reasons.extend(_operation_reasons(request))
    return tuple(dict.fromkeys(reasons))


def _operation_reasons(request: ResidentConversationRequest) -> tuple[str, ...]:
    if type(request.operation) is not ResidentConversationOperation:
        return ()
    if request.operation is ResidentConversationOperation.TURN:
        if not request.operator_text:
            return ("resident_conversation_operator_text_required",)
        if request.conversation_id:
            return (
                ()
                if request.expected_revision >= 0
                else ("resident_conversation_revision_invalid",)
            )
        return (
            ()
            if request.expected_revision == -1
            else ("resident_conversation_revision_invalid",)
        )
    if request.operator_text:
        return ("resident_conversation_operator_text_forbidden",)
    if not request.conversation_id:
        return ("resident_conversation_conversation_id_required",)
    if request.expected_revision < 0:
        return ("resident_conversation_revision_invalid",)
    return ()


def _native_request_scalars(request: ResidentConversationRequest) -> bool:
    string_values = (
        request.schema_version,
        request.request_id,
        request.conversation_id,
        request.turn_id,
        request.client_nonce,
        request.idempotency_key,
        request.operator_text,
    )
    integer_values = (
        request.expected_revision,
        request.issued_at,
        request.expires_at,
    )
    return all(type(value) is str for value in string_values) and all(
        type(value) is int for value in integer_values
    )


def _valid_time_window(request: ResidentConversationRequest) -> bool:
    return (
        request.issued_at >= 0
        and request.expires_at > request.issued_at
        and request.expires_at - request.issued_at <= MAX_REQUEST_TTL_SECONDS
    )


def _canonical_operator_text(value: object) -> bool:
    if type(value) is not str or "\x00" in value:
        return False
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        return False
    return (
        value == unicodedata.normalize("NFKC", value).strip()
        and len(value) <= MAX_OPERATOR_TEXT_SCALARS
    )


def _normalized_operator_text(value: object) -> str:
    text = _strict_string(value)
    if "\x00" in text or any(ord(char) < 32 and char not in "\n\r\t" for char in text):
        raise ValueError("resident_conversation_operator_text_invalid")
    normalized = unicodedata.normalize("NFKC", text).strip()
    if len(normalized) > MAX_OPERATOR_TEXT_SCALARS:
        raise ValueError("resident_conversation_operator_text_invalid")
    return normalized


def _strict_operation(value: object) -> ResidentConversationOperation:
    text = _strict_string(value)
    try:
        return ResidentConversationOperation(text)
    except ValueError as exc:
        raise ValueError("resident_conversation_operation_invalid") from exc


def _strict_integer(value: object) -> int:
    if type(value) is not int:
        raise ValueError("resident_conversation_request_type_invalid")
    return value


def _strict_string(value: object) -> str:
    if type(value) is not str:
        raise ValueError("resident_conversation_request_type_invalid")
    return value


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


__all__ = [
    "BINDING_SCHEMA_VERSION",
    "MAX_CLOCK_SKEW_SECONDS",
    "MAX_OPERATOR_TEXT_SCALARS",
    "MAX_REQUEST_TTL_SECONDS",
    "ResidentConversationOperation",
    "ResidentConversationRequest",
    "SCHEMA_VERSION",
    "enforce_request_freshness",
    "request_from_mapping",
    "resident_conversation_request_reasons",
]
