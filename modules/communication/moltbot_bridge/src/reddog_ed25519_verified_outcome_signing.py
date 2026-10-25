"""Verified-outcome reservation boundary for the Ed25519 signer backend."""

from __future__ import annotations

import hashlib
from typing import Any

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VERIFIED_OUTCOME_SIGNING_OPERATION,
    validate_verified_outcome_signing_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_signature,
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
        proof_input = authority.reserve_proof_input(
            receipt_id=str(payload["receipt_id"]),
            work_order_id=str(payload["work_order_id"]),
            evidence_digest=str(payload["covered_action_digest"]),
            issued_at=int(payload["issued_at"]),
        )
        proof = _sign_proof(backend, proof_input)
        reservation = authority.reserve(
            receipt_id=str(payload["receipt_id"]),
            work_order_id=str(payload["work_order_id"]),
            evidence_digest=str(payload["covered_action_digest"]),
            issued_at=int(payload["issued_at"]),
            signer_instance_signature=proof,
        )
    except Exception:
        reservation = None
    if reservation is None:
        return None, None, REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_REJECTED
    return dict(payload), reservation, ""


def commit_outcome_reservation(
    backend: Any, reservation: Any, signature: str
) -> bool:
    if reservation is None:
        return True
    try:
        assert backend.verified_outcome_signing_authority is not None
        signature_digest = "sha256:" + hashlib.sha256(
            signature.encode("ascii")
        ).hexdigest()
        proof_input = backend.verified_outcome_signing_authority.commit_proof_input(
            reservation, signature_digest
        )
        proof = _sign_proof(backend, proof_input)
        backend.verified_outcome_signing_authority.commit(
            reservation, signature_digest, proof
        )
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


def _sign_proof(backend: Any, value: str) -> str:
    if not isinstance(value, str) or not value.isascii():
        raise ValueError("verified_outcome_root_proof_input_invalid")
    return encode_ed25519_signature(
        backend.private_key.sign(value.encode("ascii"))
    )


__all__ = [
    "REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_MISSING",
    "REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_REJECTED",
    "commit_outcome_reservation",
    "prepare_verified_outcome_signing",
    "rollback_outcome_reservation",
]
