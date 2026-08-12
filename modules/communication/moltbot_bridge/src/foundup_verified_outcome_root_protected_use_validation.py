"""Strict shape validation for root protected-use wire messages."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_wire_codec import (
    encode_message,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_types import (
    OP_ACQUIRE,
    OP_FINISH,
    RootProtectedUseRequest,
    RootProtectedUseResponse,
    SCHEMA_VERSION,
    STATUS_ACCEPT,
    STATUS_REJECT,
)


def validate_request(value: RootProtectedUseRequest) -> None:
    if (
        type(value) is not RootProtectedUseRequest
        or value.operation not in {OP_ACQUIRE, OP_FINISH}
        or not _revision(value.request_nonce)
        or not _revision(value.use_nonce)
        or any(not _sha(item) for item in (
            value.request_id, value.descriptor_id, value.owner_config_id,
            value.policy_id, value.binding_digest, value.grant_id,
            value.signing_request_digest, value.protected_use_id,
        ))
        or not _ascii(value.key_epoch)
        or not isinstance(value.policy, Mapping)
        or type(value.grant_expires_at) is not int
        or type(value.issued_at) is not int
        or value.grant_expires_at < 1
        or not _signature(value.signer_instance_signature)
    ):
        raise ValueError("root_protected_use_request_invalid")
    _require_request_bindings(value)
    encode_message({"schema_version": SCHEMA_VERSION, **asdict(value)})


def _require_request_bindings(value: RootProtectedUseRequest) -> None:
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_protocol import (
        protected_use_id_for,
        request_id_for,
    )

    if (
        protected_use_id_for(asdict(value)) != value.protected_use_id
        or request_id_for(asdict(value)) != value.request_id
    ):
        raise ValueError("root_protected_use_request_binding_invalid")
    high = high_water(value.acquired_sequence, value.acquired_revision)
    if (value.operation == OP_ACQUIRE) != (high is None):
        raise ValueError("root_protected_use_request_phase_invalid")
    if value.operation == OP_ACQUIRE and value.grant_expires_at <= value.issued_at:
        raise ValueError("root_protected_use_request_expired")


def validate_response(value: RootProtectedUseResponse) -> None:
    high = high_water(value.sequence, value.revision)
    if (
        type(value) is not RootProtectedUseResponse
        or value.status not in {STATUS_ACCEPT, STATUS_REJECT}
        or any(not _sha(item) for item in (
            value.request_id, value.descriptor_id, value.owner_config_id,
            value.policy_id, value.binding_digest, value.protected_use_id,
        ))
        or value.state not in {"ACQUIRED", "FINISHED", "REJECTED"}
        or not _ascii_or_empty(value.reason)
        or value.accepted != (value.state in {"ACQUIRED", "FINISHED"})
        or (value.accepted and high is None)
        or (not value.accepted and high is not None)
    ):
        raise ValueError("root_protected_use_response_invalid")
    if high is not None:
        parity = 1 if value.state == "ACQUIRED" else 0
        if high[0] % 2 != parity:
            raise ValueError("root_protected_use_response_sequence_invalid")


def high_water(sequence: Any, revision: Any) -> tuple[int, str] | None:
    if sequence is None and revision is None:
        return None
    if type(sequence) is not int or sequence < 1 or not _revision(revision):
        raise ValueError("root_protected_use_high_water_invalid")
    return sequence, str(revision)


def _sha(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and _revision(text[7:])


def _revision(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _signature(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("ed25519-sig-v1:") and value.isascii()


def _ascii(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value.isascii() and len(value) <= 4096


def _ascii_or_empty(value: Any) -> bool:
    return isinstance(value, str) and value.isascii() and len(value) <= 4096


__all__ = ["high_water", "validate_request", "validate_response"]
