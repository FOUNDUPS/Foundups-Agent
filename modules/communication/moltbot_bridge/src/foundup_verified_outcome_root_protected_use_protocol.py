"""Wire contract for root-linearized signer protected-use operations."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_wire_codec import (
    canonical_bytes,
    decode_message,
    digest_mapping,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_types import (
    OP_ACQUIRE,
    OP_FINISH,
    RootProtectedUseRequest,
    RootProtectedUseResponse,
    SCHEMA_VERSION,
    SIGNING_PREFIX,
    STATUS_ACCEPT,
    STATUS_REJECT,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_validation import (
    validate_request,
    validate_response,
)


def request_from_bytes(value: bytes) -> RootProtectedUseRequest:
    data = decode_message(value)
    expected = {"schema_version", *RootProtectedUseRequest.__dataclass_fields__}
    if set(data) != expected or data.pop("schema_version") != SCHEMA_VERSION:
        raise ValueError("root_protected_use_request_shape_invalid")
    request = RootProtectedUseRequest(**data)
    validate_request(request)
    return request


def response_from_bytes(value: bytes) -> RootProtectedUseResponse:
    data = decode_message(value)
    expected = {"schema_version", *RootProtectedUseResponse.__dataclass_fields__}
    if set(data) != expected or data.pop("schema_version") != SCHEMA_VERSION:
        raise ValueError("root_protected_use_response_shape_invalid")
    response = RootProtectedUseResponse(**data)
    validate_response(response)
    return response


def protected_use_id_for(value: Mapping[str, Any]) -> str:
    fields = (
        "descriptor_id", "owner_config_id", "policy_id", "binding_digest",
        "grant_id", "key_epoch", "signing_request_digest", "use_nonce",
        "grant_expires_at",
    )
    try:
        payload = {field: value[field] for field in fields}
    except (KeyError, TypeError) as exc:
        raise ValueError("root_protected_use_identity_invalid") from exc
    return digest_mapping(payload)


def request_id_for(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("request_id", None)
    return digest_mapping(payload)


def canonical_signer_input(value: RootProtectedUseRequest) -> str:
    payload = asdict(value)
    payload.pop("request_id", None)
    payload.pop("signer_instance_signature", None)
    return SIGNING_PREFIX + canonical_bytes(payload).decode("ascii")


def is_protected_use_wire_message(value: bytes) -> bool:
    try:
        return decode_message(value).get("schema_version") == SCHEMA_VERSION
    except ValueError:
        return False


def finish_revision_for(
    protected_use_id: str, acquired_sequence: int, acquired_revision: str,
) -> str:
    return digest_mapping(
        {
            "purpose": "root-protected-use-finished",
            "protected_use_id": protected_use_id,
            "acquired_sequence": acquired_sequence,
            "acquired_revision": acquired_revision,
        }
    )[7:]


__all__ = [
    "OP_ACQUIRE", "OP_FINISH", "RootProtectedUseRequest",
    "RootProtectedUseResponse", "SCHEMA_VERSION", "SIGNING_PREFIX",
    "STATUS_ACCEPT", "STATUS_REJECT", "canonical_signer_input",
    "finish_revision_for", "is_protected_use_wire_message",
    "protected_use_id_for", "request_from_bytes", "request_id_for",
    "response_from_bytes",
]
