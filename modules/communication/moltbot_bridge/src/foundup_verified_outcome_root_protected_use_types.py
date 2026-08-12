"""Typed messages for root-linearized signer protected use."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_wire_codec import (
    encode_message,
)

SCHEMA_VERSION = "foundup-root-signer-protected-use-service.v1"
SIGNING_PREFIX = "foundup-root-signer-protected-use-request.v1."
OP_ACQUIRE = "PROTECTED_USE_ACQUIRE"
OP_FINISH = "PROTECTED_USE_FINISH"
STATUS_ACCEPT = "ACCEPT"
STATUS_REJECT = "REJECT"


@dataclass(frozen=True)
class RootProtectedUseRequest:
    operation: str
    request_id: str
    request_nonce: str
    descriptor_id: str
    owner_config_id: str
    policy_id: str
    binding_digest: str
    policy: Mapping[str, Any]
    grant_id: str
    key_epoch: str
    signing_request_digest: str
    use_nonce: str
    protected_use_id: str
    grant_expires_at: int
    acquired_sequence: int | None
    acquired_revision: str | None
    issued_at: int
    signer_instance_signature: str

    def to_bytes(self) -> bytes:
        from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_validation import (
            validate_request,
        )

        validate_request(self)
        return encode_message({"schema_version": SCHEMA_VERSION, **asdict(self)})


@dataclass(frozen=True)
class RootProtectedUseResponse:
    status: str
    request_id: str
    descriptor_id: str
    owner_config_id: str
    policy_id: str
    binding_digest: str
    protected_use_id: str
    state: str
    sequence: int | None = None
    revision: str | None = None
    reason: str = ""

    @property
    def accepted(self) -> bool:
        return self.status == STATUS_ACCEPT

    def to_bytes(self) -> bytes:
        from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_validation import (
            validate_response,
        )

        validate_response(self)
        return encode_message({"schema_version": SCHEMA_VERSION, **asdict(self)})


__all__ = [
    "OP_ACQUIRE", "OP_FINISH", "RootProtectedUseRequest",
    "RootProtectedUseResponse", "SCHEMA_VERSION", "SIGNING_PREFIX",
    "STATUS_ACCEPT", "STATUS_REJECT",
]
