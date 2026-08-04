"""Signer-owned policy for verified FoundUp outcome receipts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PREFIX_RECEIPT,
    canonical_signing_input,
)


VERIFIED_OUTCOME_SIGNING_OPERATION = "attest_verified_foundup_outcome"
VERIFIED_OUTCOME_SIGNER_ROLE = "verified_foundup_outcome_authority"
VERIFIED_OUTCOME_SIGNING_PREFIX = PREFIX_RECEIPT + "."
_RECEIPT_FIELDS = {
    "receipt_id",
    "work_order_id",
    "reddog_id",
    "prev_receipt_hash",
    "covered_action_digest",
    "reward_account",
    "issued_at",
}


@dataclass(frozen=True)
class VerifiedOutcomeSignerPolicy:
    issuer_principal_id: str
    reddog_id: str
    signer_public_key: str
    key_epoch: str
    authority_tier: str
    consensus_receipt_digest: str
    max_future_skew_seconds: int = 60


def validate_verified_outcome_signing_request(
    request: SigningRequest,
    policy: VerifiedOutcomeSignerPolicy,
    *,
    now_epoch: int,
) -> Mapping[str, Any] | None:
    if (
        request.requested_operation != VERIFIED_OUTCOME_SIGNING_OPERATION
        or request.signer_role != VERIFIED_OUTCOME_SIGNER_ROLE
        or request.requester_principal_id != policy.issuer_principal_id
        or request.signer_public_key != policy.signer_public_key
        or request.key_epoch != policy.key_epoch
        or request.authority_tier != policy.authority_tier
        or request.consensus_receipt_digest != policy.consensus_receipt_digest
        or request.nonce == ""
        or request.payload_digest != _digest({"signing_input": request.signing_input})
        or policy.max_future_skew_seconds < 0
    ):
        return None
    payload = _parse_payload(request.signing_input)
    if payload is None or set(payload) != _RECEIPT_FIELDS:
        return None
    if (
        not str(payload.get("receipt_id") or "").startswith("verified-outcome-")
        or payload.get("receipt_id") != request.nonce
        or payload.get("reddog_id") != policy.reddog_id
        or payload.get("prev_receipt_hash") is not None
        or payload.get("reward_account") is not None
        or not str(payload.get("work_order_id") or "").strip()
        or not _sha256(payload.get("covered_action_digest"))
        or type(payload.get("issued_at")) is not int
        or payload["issued_at"] > now_epoch + policy.max_future_skew_seconds
        or payload["issued_at"] < now_epoch - policy.max_future_skew_seconds
        or canonical_signing_input(payload, PREFIX_RECEIPT) != request.signing_input
    ):
        return None
    return payload


def _parse_payload(signing_input: str) -> Mapping[str, Any] | None:
    if not isinstance(signing_input, str) or not signing_input.startswith(
        VERIFIED_OUTCOME_SIGNING_PREFIX
    ):
        return None
    try:
        payload = json.loads(signing_input[len(VERIFIED_OUTCOME_SIGNING_PREFIX) :])
    except (json.JSONDecodeError, TypeError):
        return None
    return payload if isinstance(payload, Mapping) else None


def _sha256(value: Any) -> bool:
    text = str(value or "")
    return (
        len(text) == 71
        and text.startswith("sha256:")
        and all(char in "0123456789abcdef" for char in text[7:])
    )


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX",
    "VERIFIED_OUTCOME_SIGNER_ROLE",
    "VERIFIED_OUTCOME_SIGNING_OPERATION",
    "VERIFIED_OUTCOME_SIGNING_PREFIX",
    "VerifiedOutcomeSignerPolicy",
    "validate_verified_outcome_signing_request",
]
