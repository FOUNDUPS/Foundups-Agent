"""Exact wire contract for the root verified-outcome authority service."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping


SCHEMA_VERSION = "foundup_verified_outcome_root_authority_service.v1"
SIGNER_PROOF_PREFIX = "foundup-verified-outcome-root-request.v1."
OP_RESERVE = "RESERVE"
OP_COMMIT = "COMMIT"
STATUS_ACCEPT = "ACCEPT"
STATUS_REJECT = "REJECT"
MAX_MESSAGE_BYTES = 64 * 1024


@dataclass(frozen=True)
class RootAuthorityRequest:
    operation: str
    request_id: str
    descriptor_id: str
    owner_config_id: str
    authorization_id: str
    receipt_id: str
    work_order_id: str
    evidence_digest: str
    issued_at: int
    signer_instance_signature: str
    reservation_id: str | None = None
    signature_digest: str | None = None

    def to_bytes(self) -> bytes:
        validate_request(self)
        return _encode({"schema_version": SCHEMA_VERSION, **asdict(self)})


@dataclass(frozen=True)
class RootAuthorityResponse:
    status: str
    request_id: str
    descriptor_id: str
    owner_config_id: str
    authorization_id: str
    reservation_id: str | None
    state: str
    reason: str = ""

    @property
    def accepted(self) -> bool:
        return self.status == STATUS_ACCEPT

    def to_bytes(self) -> bytes:
        validate_response(self)
        return _encode({"schema_version": SCHEMA_VERSION, **asdict(self)})


def request_from_bytes(value: bytes) -> RootAuthorityRequest:
    data = _decode(value)
    expected = {"schema_version", *RootAuthorityRequest.__dataclass_fields__}
    if set(data) != expected or data.pop("schema_version") != SCHEMA_VERSION:
        raise ValueError("root_authority_request_shape_invalid")
    request = RootAuthorityRequest(**data)
    validate_request(request)
    return request


def response_from_bytes(value: bytes) -> RootAuthorityResponse:
    data = _decode(value)
    expected = {"schema_version", *RootAuthorityResponse.__dataclass_fields__}
    if set(data) != expected or data.pop("schema_version") != SCHEMA_VERSION:
        raise ValueError("root_authority_response_shape_invalid")
    response = RootAuthorityResponse(**data)
    validate_response(response)
    return response


def validate_request(value: RootAuthorityRequest) -> None:
    if not isinstance(value, RootAuthorityRequest) or value.operation not in {
        OP_RESERVE,
        OP_COMMIT,
    }:
        raise ValueError("root_authority_request_invalid")
    required_digests = (
        value.request_id,
        value.descriptor_id,
        value.owner_config_id,
        value.evidence_digest,
    )
    required_text = (
        value.authorization_id,
        value.receipt_id,
        value.work_order_id,
    )
    if (
        any(not _sha256(item) for item in required_digests)
        or any(not _text(item) for item in required_text)
        or type(value.issued_at) is not int
        or not _signature(value.signer_instance_signature)
        or request_id_for(asdict(value)) != value.request_id
    ):
        raise ValueError("root_authority_request_invalid")
    commit = value.operation == OP_COMMIT
    if commit != bool(value.reservation_id and value.signature_digest):
        raise ValueError("root_authority_request_phase_invalid")
    if commit and not _sha256(value.reservation_id):
        raise ValueError("root_authority_reservation_invalid")
    if commit and not _sha256(value.signature_digest):
        raise ValueError("root_authority_signature_digest_invalid")


def validate_response(value: RootAuthorityResponse) -> None:
    if (
        not isinstance(value, RootAuthorityResponse)
        or value.status not in {STATUS_ACCEPT, STATUS_REJECT}
        or any(
            not _sha256(item)
            for item in (
                value.request_id,
                value.descriptor_id,
                value.owner_config_id,
            )
        )
        or not _text(value.authorization_id)
        or not _text(value.state)
        or not isinstance(value.reason, str)
        or not value.reason.isascii()
    ):
        raise ValueError("root_authority_response_invalid")
    if value.accepted != bool(value.reservation_id):
        raise ValueError("root_authority_response_reservation_invalid")
    if value.reservation_id and not _sha256(value.reservation_id):
        raise ValueError("root_authority_response_reservation_invalid")


def request_id_for(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("request_id", None)
    return _digest(payload)


def canonical_signer_instance_input(value: RootAuthorityRequest) -> str:
    """Bind the E0 signer key to every authority request field."""

    payload = asdict(value)
    payload.pop("request_id", None)
    payload.pop("signer_instance_signature", None)
    return SIGNER_PROOF_PREFIX + json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )


def _encode(value: Mapping[str, Any]) -> bytes:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii") + b"\n"
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ValueError("root_authority_message_too_large")
    return raw


def _decode(value: bytes) -> dict[str, Any]:
    if not isinstance(value, bytes) or not value or len(value) > MAX_MESSAGE_BYTES:
        raise ValueError("root_authority_message_invalid")
    try:
        data = json.loads(value.decode("ascii").strip())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("root_authority_message_invalid") from exc
    if not isinstance(data, dict):
        raise ValueError("root_authority_message_invalid")
    return data


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.isascii()


def _sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


def _signature(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("ed25519-sig-v1:") and value.isascii()


def _digest(value: Mapping[str, Any]) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


__all__ = [
    "MAX_MESSAGE_BYTES",
    "OP_COMMIT",
    "OP_RESERVE",
    "RootAuthorityRequest",
    "RootAuthorityResponse",
    "SCHEMA_VERSION",
    "SIGNER_PROOF_PREFIX",
    "STATUS_ACCEPT",
    "STATUS_REJECT",
    "canonical_signer_instance_input",
    "request_from_bytes",
    "request_id_for",
    "response_from_bytes",
]
