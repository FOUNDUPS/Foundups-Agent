"""Wire contract for root-owned signer-revocation anchor operations."""

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

SCHEMA_VERSION = "foundup-root-revocation-anchor-service.v1"
SIGNING_PREFIX = "foundup-root-revocation-anchor-request.v1."
OP_LOAD = "REVOCATION_ANCHOR_LOAD"
OP_ADVANCE = "REVOCATION_ANCHOR_ADVANCE"
STATUS_ACCEPT = "ACCEPT"
STATUS_REJECT = "REJECT"


@dataclass(frozen=True)
class RootRevocationRequest:
    operation: str
    request_id: str
    request_nonce: str
    descriptor_id: str
    owner_config_id: str
    policy_id: str
    binding_digest: str
    policy: Mapping[str, Any]
    snapshot_id: str | None
    issued_at: int
    signer_instance_signature: str

    def to_bytes(self) -> bytes:
        validate_request(self)
        return encode_message({"schema_version": SCHEMA_VERSION, **asdict(self)})


@dataclass(frozen=True)
class RootRevocationResponse:
    status: str
    request_id: str
    descriptor_id: str
    owner_config_id: str
    policy_id: str
    binding_digest: str
    snapshot_id: str | None
    state: str
    sequence: int | None = None
    revision: str | None = None
    reason: str = ""

    @property
    def accepted(self) -> bool:
        return self.status == STATUS_ACCEPT

    def to_bytes(self) -> bytes:
        validate_response(self)
        return encode_message({"schema_version": SCHEMA_VERSION, **asdict(self)})


def request_from_bytes(value: bytes) -> RootRevocationRequest:
    data = decode_message(value)
    expected = {"schema_version", *RootRevocationRequest.__dataclass_fields__}
    if set(data) != expected or data.pop("schema_version") != SCHEMA_VERSION:
        raise ValueError("root_revocation_request_shape_invalid")
    request = RootRevocationRequest(**data)
    validate_request(request)
    return request


def response_from_bytes(value: bytes) -> RootRevocationResponse:
    data = decode_message(value)
    expected = {"schema_version", *RootRevocationResponse.__dataclass_fields__}
    if set(data) != expected or data.pop("schema_version") != SCHEMA_VERSION:
        raise ValueError("root_revocation_response_shape_invalid")
    response = RootRevocationResponse(**data)
    validate_response(response)
    return response


def request_id_for(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("request_id", None)
    return digest_mapping(payload)


def canonical_signer_input(value: RootRevocationRequest) -> str:
    payload = asdict(value)
    payload.pop("request_id", None)
    payload.pop("signer_instance_signature", None)
    return SIGNING_PREFIX + canonical_bytes(payload).decode("ascii")


def validate_request(value: RootRevocationRequest) -> None:
    if (
        type(value) is not RootRevocationRequest
        or value.operation not in {OP_LOAD, OP_ADVANCE}
        or not _nonce(value.request_nonce)
        or any(not _sha(item) for item in (
            value.request_id, value.descriptor_id, value.owner_config_id,
            value.policy_id, value.binding_digest,
        ))
        or not isinstance(value.policy, Mapping)
        or type(value.issued_at) is not int or value.issued_at < 1
        or not _signature(value.signer_instance_signature)
        or request_id_for(asdict(value)) != value.request_id
    ):
        raise ValueError("root_revocation_request_invalid")
    if (value.operation == OP_LOAD) != (value.snapshot_id is None):
        raise ValueError("root_revocation_request_phase_invalid")
    if value.snapshot_id is not None and not _sha(value.snapshot_id):
        raise ValueError("root_revocation_snapshot_id_invalid")
    encode_message({"schema_version": SCHEMA_VERSION, **asdict(value)})


def validate_response(value: RootRevocationResponse) -> None:
    high = _high_water(value.sequence, value.revision)
    if (
        type(value) is not RootRevocationResponse
        or value.status not in {STATUS_ACCEPT, STATUS_REJECT}
        or any(not _sha(item) for item in (
            value.request_id, value.descriptor_id, value.owner_config_id,
            value.policy_id, value.binding_digest,
        ))
        or (value.snapshot_id is not None and not _sha(value.snapshot_id))
        or value.state not in {"LOADED", "ADVANCED", "REJECTED"}
        or not isinstance(value.reason, str) or not value.reason.isascii()
        or (value.accepted != (value.state in {"LOADED", "ADVANCED"}))
        or (not value.accepted and high is not None)
        or (high is None) != (value.snapshot_id is None)
        or (
            high is not None
            and value.snapshot_id != "sha256:" + high[1]
        )
    ):
        raise ValueError("root_revocation_response_invalid")


def is_revocation_wire_message(value: bytes) -> bool:
    try:
        return decode_message(value).get("schema_version") == SCHEMA_VERSION
    except ValueError:
        return False


def _high_water(sequence: Any, revision: Any) -> tuple[int, str] | None:
    if sequence is None and revision is None:
        return None
    if (type(sequence) is not int or sequence < 1 or not isinstance(revision, str)
            or len(revision) != 64 or any(c not in "0123456789abcdef" for c in revision)):
        raise ValueError("root_revocation_high_water_invalid")
    return sequence, revision


def _sha(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:])


def _signature(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("ed25519-sig-v1:") and value.isascii()


def _nonce(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


__all__ = [
    "MAX_MESSAGE_BYTES", "OP_ADVANCE", "OP_LOAD", "RootRevocationRequest",
    "RootRevocationResponse", "SCHEMA_VERSION", "SIGNING_PREFIX",
    "STATUS_ACCEPT", "STATUS_REJECT",
    "canonical_signer_input", "is_revocation_wire_message",
    "request_from_bytes", "request_id_for", "response_from_bytes",
]
