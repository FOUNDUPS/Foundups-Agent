"""Transactional elevated-consensus flow at the Ed25519 signer boundary."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_elevated_consensus_signer_reservation import (
    commit_elevated_consensus_nonce,
    rollback_elevated_consensus_nonce,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_authority_policy import (
    SECRET_GRANT_SIGNING_OPERATION,
)


def consensus_signing_rejection(
    reservation: Any, reason: str
) -> SigningResponse:
    rollback_elevated_consensus_nonce(reservation)
    return SigningResponse(
        accepted=False,
        rejection_code=str(reason),
        no_secret_material_returned=True,
    )


def complete_elevated_consensus_signing(
    reservation: Any,
    response: SigningResponse,
    *,
    commit_failure_code: str,
) -> SigningResponse:
    if reservation is None:
        return response
    if response.accepted is not True:
        rollback_elevated_consensus_nonce(reservation)
        return response
    if not commit_elevated_consensus_nonce(reservation):
        return SigningResponse(
            accepted=False,
            rejection_code=commit_failure_code,
            no_secret_material_returned=True,
        )
    return response


def requires_signer_audit_attestation(
    request: SigningRequest, *payloads: Mapping[str, Any] | None
) -> bool:
    return bool(
        request.requested_operation == SECRET_GRANT_SIGNING_OPERATION
        or any(payload is not None for payload in payloads)
    )


__all__ = [
    "complete_elevated_consensus_signing",
    "consensus_signing_rejection",
    "requires_signer_audit_attestation",
    "rollback_elevated_consensus_nonce",
]
