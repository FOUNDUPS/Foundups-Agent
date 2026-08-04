"""Verified-outcome reservation boundary for the Ed25519 signer backend."""

from __future__ import annotations

from typing import Any

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VERIFIED_OUTCOME_SIGNING_OPERATION,
    validate_verified_outcome_signing_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)


REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_MISSING = (
    "REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_MISSING"
)
REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_REJECTED = (
    "REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_REJECTED"
)


def prepare_verified_outcome_signing(
    backend: Any,
    request: SigningRequest,
    *,
    domain_mismatch_code: str,
    request_invalid_code: str,
) -> tuple[dict[str, Any] | None, Any, str]:
    if request.requested_operation != VERIFIED_OUTCOME_SIGNING_OPERATION:
        return None, None, ""
    policy = backend.verified_outcome_signer_policy
    if policy is None:
        return None, None, domain_mismatch_code
    authority = backend.verified_outcome_signing_authority
    if authority is None:
        return None, None, REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_MISSING
    payload = validate_verified_outcome_signing_request(
        request,
        policy,
        now_epoch=int(backend.proposal_clock()),
    )
    if payload is None:
        return None, None, request_invalid_code
    try:
        reservation = authority.reserve(
            receipt_id=str(payload["receipt_id"]),
            work_order_id=str(payload["work_order_id"]),
            evidence_digest=str(payload["covered_action_digest"]),
            issued_at=int(payload["issued_at"]),
        )
    except Exception:
        reservation = None
    if reservation is None:
        return None, None, REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_REJECTED
    return dict(payload), reservation, ""


def commit_outcome_reservation(backend: Any, reservation: Any) -> bool:
    if reservation is None:
        return True
    try:
        assert backend.verified_outcome_signing_authority is not None
        backend.verified_outcome_signing_authority.commit(reservation)
        return True
    except Exception:
        rollback_outcome_reservation(backend, reservation)
        return False


def rollback_outcome_reservation(backend: Any, reservation: Any) -> None:
    if reservation is None or backend.verified_outcome_signing_authority is None:
        return
    try:
        backend.verified_outcome_signing_authority.rollback(reservation)
    except Exception:
        return


__all__ = [
    "REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_MISSING",
    "REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_REJECTED",
    "commit_outcome_reservation",
    "prepare_verified_outcome_signing",
    "rollback_outcome_reservation",
]
