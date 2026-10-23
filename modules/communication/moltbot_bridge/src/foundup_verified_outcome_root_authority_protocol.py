"""Exact wire contract for the root verified-outcome authority service."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_wire_codec import (
    MAX_MESSAGE_BYTES,
    canonical_bytes,
    decode_message,
    digest_mapping,
    encode_message,
)


SCHEMA_VERSION = "foundup_verified_outcome_root_authority_service.v1"
SIGNER_PROOF_PREFIX = "foundup-verified-outcome-root-request.v1."
RECORD_COMMIT_SCHEMA = "foundup_verified_outcome_root_authority_service.v2"
RECORD_COMMIT_PROOF_PREFIX = "foundup-verified-outcome-root-request.v2."
OP_RESERVE = "RESERVE"
OP_COMMIT = "COMMIT"
OP_COMMIT_RECORD = "COMMIT_RECORD"
STATUS_ACCEPT = "ACCEPT"
STATUS_REJECT = "REJECT"


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
        return encode_message({"schema_version": SCHEMA_VERSION, **asdict(self)})


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
        return encode_message({"schema_version": SCHEMA_VERSION, **asdict(self)})


@dataclass(frozen=True)
class RootAuthorityRecordCommitRequest(RootAuthorityRequest):
    response_record: str = ""
    record_digest: str = ""

    def to_bytes(self) -> bytes:
        validate_record_commit_request(self)
        return encode_message({"schema_version": RECORD_COMMIT_SCHEMA, **asdict(self)})


@dataclass(frozen=True)
class RootAuthorityRecordCommitResponse(RootAuthorityResponse):
    record_digest: str = ""

    def to_bytes(self) -> bytes:
        validate_record_commit_response(self)
        return encode_message({"schema_version": RECORD_COMMIT_SCHEMA, **asdict(self)})


def record_commit_request_from_bytes(value: bytes) -> RootAuthorityRecordCommitRequest:
    data = decode_message(value)
    expected = {"schema_version", *RootAuthorityRecordCommitRequest.__dataclass_fields__}
    if set(data) != expected or data.pop("schema_version") != RECORD_COMMIT_SCHEMA:
        raise ValueError("root_record_commit_request_shape_invalid")
    request = RootAuthorityRecordCommitRequest(**data)
    if request.to_bytes() != value:
        raise ValueError("root_record_commit_request_noncanonical")
    return request


def record_commit_response_from_bytes(value: bytes) -> RootAuthorityRecordCommitResponse:
    data = decode_message(value)
    expected = {"schema_version", *RootAuthorityRecordCommitResponse.__dataclass_fields__}
    if set(data) != expected or data.pop("schema_version") != RECORD_COMMIT_SCHEMA:
        raise ValueError("root_record_commit_response_shape_invalid")
    response = RootAuthorityRecordCommitResponse(**data)
    if response.to_bytes() != value:
        raise ValueError("root_record_commit_response_noncanonical")
    return response


def request_from_bytes(value: bytes) -> RootAuthorityRequest:
    data = decode_message(value)
    expected = {"schema_version", *RootAuthorityRequest.__dataclass_fields__}
    if set(data) != expected or data.pop("schema_version") != SCHEMA_VERSION:
        raise ValueError("root_authority_request_shape_invalid")
    request = RootAuthorityRequest(**data)
    validate_request(request)
    return request


def response_from_bytes(value: bytes) -> RootAuthorityResponse:
    data = decode_message(value)
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
    _validate_request_identity(value)
    commit = value.operation == OP_COMMIT
    if commit != bool(value.reservation_id and value.signature_digest):
        raise ValueError("root_authority_request_phase_invalid")
    if commit and not _sha256(value.reservation_id):
        raise ValueError("root_authority_reservation_invalid")
    if commit and not _sha256(value.signature_digest):
        raise ValueError("root_authority_signature_digest_invalid")


def _validate_request_identity(value: RootAuthorityRequest) -> None:
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


def validate_record_commit_request(value: RootAuthorityRecordCommitRequest) -> None:
    if (type(value) is not RootAuthorityRecordCommitRequest
        or value.operation != OP_COMMIT_RECORD
        or value.signature_digest is not None
        or not _sha256(value.reservation_id)
        or not _sha256(value.record_digest)
        or type(value.response_record) is not str
        or not value.response_record.isascii()
        or not 0 < len(value.response_record) <= MAX_MESSAGE_BYTES):
        raise ValueError("root_record_commit_request_invalid")
    _validate_request_identity(value)


def validate_record_commit_response(value: RootAuthorityRecordCommitResponse) -> None:
    validate_response(value)
    if (type(value) is not RootAuthorityRecordCommitResponse
        or value.state != ("COMMITTED" if value.accepted else "REJECTED")
        or (not _sha256(value.record_digest) if value.accepted else value.record_digest != "")):
        raise ValueError("root_record_commit_response_invalid")


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
    return digest_mapping(payload)


def canonical_signer_instance_input(value: RootAuthorityRequest) -> str:
    """Bind the E0 signer key to every authority request field."""

    payload = asdict(value)
    payload.pop("request_id", None)
    payload.pop("signer_instance_signature", None)
    prefix = (RECORD_COMMIT_PROOF_PREFIX if type(value) is RootAuthorityRecordCommitRequest
              else SIGNER_PROOF_PREFIX)
    return prefix + canonical_bytes(payload).decode("ascii")


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.isascii()


def _sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


def _signature(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("ed25519-sig-v1:") and value.isascii()


__all__ = [
    "MAX_MESSAGE_BYTES",
    "OP_COMMIT",
    "OP_COMMIT_RECORD",
    "OP_RESERVE",
    "RootAuthorityRequest",
    "RootAuthorityResponse",
    "RootAuthorityRecordCommitRequest",
    "RootAuthorityRecordCommitResponse",
    "RECORD_COMMIT_SCHEMA",
    "RECORD_COMMIT_PROOF_PREFIX",
    "SCHEMA_VERSION",
    "SIGNER_PROOF_PREFIX",
    "STATUS_ACCEPT",
    "STATUS_REJECT",
    "canonical_signer_instance_input",
    "request_from_bytes",
    "record_commit_request_from_bytes",
    "record_commit_response_from_bytes",
    "request_id_for",
    "response_from_bytes",
]
