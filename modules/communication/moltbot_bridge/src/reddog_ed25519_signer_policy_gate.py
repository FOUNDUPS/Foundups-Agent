"""Fail-closed signer policy and exact-request admission helpers."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, TypeVar

from modules.communication.moltbot_bridge.src import (
    reddog_signer_mutual_peer_handshake as peer_handshake,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VERIFIED_OUTCOME_SIGNING_OPERATION,
)
from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    PROPOSAL_AUTHENTICITY_SIGNING_OPERATION,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_conversation_scope_backend import (
    CONVERSATION_SCOPE_RECOVERY_SIGNING_OPERATION,
    CONVERSATION_SCOPE_SIGNING_OPERATION,
    conversation_signing_configured,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_validation import (
    CONTROL_LOOP_SIGNING_OPERATION,
    is_sha256_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant_contract import (
    signer_secret_access_request_digest,
)


REJECT_ED25519_SIGNER_POLICY_MISSING = "REJECT_ED25519_SIGNER_POLICY_MISSING"
REJECT_ED25519_SIGNER_EXACT_REQUEST_MISMATCH = (
    "REJECT_ED25519_SIGNER_EXACT_REQUEST_MISMATCH"
)
REJECT_ED25519_SIGNER_REQUEST_INVALID = "REJECT_ED25519_SIGNER_REQUEST_INVALID"
REJECT_ED25519_SIGNER_PROPOSAL_DOMAIN_ONLY = (
    "REJECT_ED25519_SIGNER_PROPOSAL_DOMAIN_ONLY"
)

_SPECIALIZED_OPERATIONS = frozenset(
    {
        CONTROL_LOOP_SIGNING_OPERATION,
        PROPOSAL_AUTHENTICITY_SIGNING_OPERATION,
        RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION,
        peer_handshake.SIGNER_PEER_HANDSHAKE_SIGNING_OPERATION,
        VERIFIED_OUTCOME_SIGNING_OPERATION,
        CONVERSATION_SCOPE_SIGNING_OPERATION,
        CONVERSATION_SCOPE_RECOVERY_SIGNING_OPERATION,
    }
)
_T = TypeVar("_T")


def signer_policy_rejection(backend: Any, request: SigningRequest) -> str:
    """Validate static policy or one exact E0-authorized request."""

    exact_authorized, reason = _exact_request_authorization(backend, request)
    if reason:
        return reason
    configured = _policy_configured(backend)
    if not configured and not exact_authorized:
        return (
            ""
            if request.requested_operation in _SPECIALIZED_OPERATIONS
            else REJECT_ED25519_SIGNER_POLICY_MISSING
        )
    if exact_authorized:
        return ""
    return (
        ""
        if request.requested_operation in _allowed_operations(backend)
        else REJECT_ED25519_SIGNER_PROPOSAL_DOMAIN_ONLY
    )


def bind_exact_signing_request(backend: _T, request: SigningRequest) -> _T:
    """Immutably bind one ephemeral Ed25519 backend to one exact request."""

    from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
        Ed25519SignerBackend,
    )

    if type(backend) is not Ed25519SignerBackend or type(request) is not SigningRequest:
        raise TypeError("exact signer binding requires canonical types")
    if backend.exact_signing_request_digest is not None:
        raise ValueError("exact signer binding is immutable")
    return replace(
        backend,
        exact_signing_request_digest=signer_secret_access_request_digest(
            request.to_dict()
        ),
    )


def _exact_request_authorization(
    backend: Any, request: SigningRequest
) -> tuple[bool, str]:
    expected = backend.exact_signing_request_digest
    if expected is None:
        return False, ""
    if not is_sha256_digest(expected):
        return False, REJECT_ED25519_SIGNER_REQUEST_INVALID
    if expected != signer_secret_access_request_digest(request.to_dict()):
        return False, REJECT_ED25519_SIGNER_EXACT_REQUEST_MISMATCH
    return True, ""


def _policy_configured(backend: Any) -> bool:
    return bool(
        backend.control_loop_authority_policy is not None
        or backend.proposal_authority_policy is not None
        or backend.runtime_artifact_manifest_authority is not None
        or backend.runtime_artifact_manifest_authority_boundary is not None
        or backend.signer_peer_instance_binding is not None
        or backend.verified_outcome_signer_policy is not None
        or conversation_signing_configured(backend)
    )


def _allowed_operations(backend: Any) -> set[str]:
    allowed: set[str] = set()
    if backend.signer_peer_instance_binding is not None:
        allowed.add(peer_handshake.SIGNER_PEER_HANDSHAKE_SIGNING_OPERATION)
    if backend.proposal_authority_policy is not None:
        allowed.add(PROPOSAL_AUTHENTICITY_SIGNING_OPERATION)
    if backend.control_loop_authority_policy is not None:
        allowed.add(CONTROL_LOOP_SIGNING_OPERATION)
    if (
        backend.runtime_artifact_manifest_authority is not None
        and backend.runtime_artifact_manifest_authority_boundary is not None
    ):
        allowed.add(RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION)
    if backend.verified_outcome_signer_policy is not None:
        allowed.add(VERIFIED_OUTCOME_SIGNING_OPERATION)
    if backend.conversation_scope_signer_policy is not None:
        allowed.update(
            {
                CONVERSATION_SCOPE_SIGNING_OPERATION,
                CONVERSATION_SCOPE_RECOVERY_SIGNING_OPERATION,
            }
        )
    return allowed


__all__ = [
    "REJECT_ED25519_SIGNER_EXACT_REQUEST_MISMATCH",
    "REJECT_ED25519_SIGNER_POLICY_MISSING",
    "bind_exact_signing_request",
    "signer_policy_rejection",
]
