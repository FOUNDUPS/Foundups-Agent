"""Strict signing domain for independently issued signer secret grants."""

from __future__ import annotations

import json
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    SECRET_GRANT_AUDIT_ATTESTATION_PREFIX,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_authority_policy import (
    SECRET_GRANT_SIGNING_OPERATION,
    SignerSecretGrantAuthorityPolicy,
    secret_grant_binding_rejected,
    secret_grant_consensus_rejected,
    secret_grant_policy_rejected,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant_contract import (
    GRANT_PREFIX,
    SignerSecretAccessGrantRejected,
    signer_secret_access_grant_id,
    validated_signer_secret_grant,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    canonical_signing_input,
    constant_time_compare,
)

SECRET_GRANT_SIGNER_ROLE = "signer_secret_grant_authority"
SECRET_GRANT_SIGNING_PREFIX = GRANT_PREFIX + "."


def build_secret_grant_signing_request(
    grant: Mapping[str, Any],
    *,
    policy: SignerSecretGrantAuthorityPolicy,
    consensus_receipt_digest: str | None,
) -> SigningRequest:
    """Build one canonical request for the independently hosted grant signer."""

    checked = _validated_unsigned_grant(grant, now_epoch=int(grant["issued_at"]))
    if secret_grant_policy_rejected(policy) or secret_grant_binding_rejected(
        checked, policy
    ):
        raise ValueError("secret_grant_signing_request_invalid")
    if secret_grant_consensus_rejected(
        str(checked["authority_tier"]), consensus_receipt_digest
    ):
        raise ValueError("secret_grant_signing_consensus_invalid")
    return SigningRequest(
        signing_input=canonical_signing_input(checked, GRANT_PREFIX),
        payload_digest=str(checked["grant_id"]),
        signer_role=SECRET_GRANT_SIGNER_ROLE,
        signer_public_key=policy.issuer_public_key,
        requester_principal_id=policy.requester_principal_id,
        nonce="signer-secret-grant:" + str(checked["nonce"]),
        key_epoch=policy.issuer_key_epoch,
        requested_operation=SECRET_GRANT_SIGNING_OPERATION,
        authority_tier=str(checked["authority_tier"]),
        consensus_receipt_digest=consensus_receipt_digest,
    )


def validate_secret_grant_signing_request(
    request: object,
    policy: SignerSecretGrantAuthorityPolicy,
    *,
    now_epoch: int,
) -> dict[str, Any] | None:
    """Return the unsigned grant only when request and policy match exactly."""

    if type(request) is not SigningRequest or secret_grant_policy_rejected(policy):
        return None
    grant = _grant_from_signing_input(request.signing_input, now_epoch)
    if grant is None or secret_grant_binding_rejected(grant, policy):
        return None
    expected = _request_for_comparison(grant, policy, request.consensus_receipt_digest)
    if expected is None or request.to_dict() != expected.to_dict():
        return None
    return grant


def _request_for_comparison(
    grant: Mapping[str, Any],
    policy: SignerSecretGrantAuthorityPolicy,
    consensus: str | None,
) -> SigningRequest | None:
    try:
        return build_secret_grant_signing_request(
            grant, policy=policy, consensus_receipt_digest=consensus
        )
    except (KeyError, TypeError, ValueError):
        return None


def _grant_from_signing_input(
    signing_input: str, now_epoch: int
) -> dict[str, Any] | None:
    if not isinstance(signing_input, str) or not signing_input.startswith(
        SECRET_GRANT_SIGNING_PREFIX
    ):
        return None
    body = signing_input[len(SECRET_GRANT_SIGNING_PREFIX) :]
    try:
        parsed = json.loads(body, object_pairs_hook=_reject_duplicate_keys)
        if not isinstance(parsed, dict):
            return None
        parsed["signature"] = "pending-signature"
        checked = _validated_unsigned_grant(parsed, now_epoch=now_epoch)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    return checked if body == canonical_signing_input(checked, GRANT_PREFIX)[len(SECRET_GRANT_SIGNING_PREFIX) :] else None


def _validated_unsigned_grant(
    grant: Mapping[str, Any], *, now_epoch: int
) -> dict[str, Any]:
    raw = dict(grant)
    raw["signature"] = "pending-signature"
    try:
        checked = validated_signer_secret_grant(raw, now_epoch)
    except SignerSecretAccessGrantRejected as exc:
        raise ValueError("secret_grant_signing_payload_invalid") from exc
    if not constant_time_compare(
        str(checked["grant_id"]), signer_secret_access_grant_id(checked)
    ):
        raise ValueError("secret_grant_signing_grant_id_invalid")
    return checked


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate secret-grant signing key")
        result[key] = value
    return result


__all__ = [
    "SECRET_GRANT_AUDIT_ATTESTATION_PREFIX",
    "SECRET_GRANT_SIGNER_ROLE",
    "SECRET_GRANT_SIGNING_OPERATION",
    "SECRET_GRANT_SIGNING_PREFIX",
    "SignerSecretGrantAuthorityPolicy",
    "build_secret_grant_signing_request",
    "validate_secret_grant_signing_request",
]
