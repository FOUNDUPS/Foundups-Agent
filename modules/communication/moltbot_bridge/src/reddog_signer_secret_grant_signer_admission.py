"""Signer-side admission for one independently issued secret grant."""

from __future__ import annotations

from typing import Any

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_authority_policy import (
    SECRET_GRANT_SIGNING_OPERATION,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_rate_authority import (
    DurableSignerSecretGrantRateAuthority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_nonce_store import (
    DurableSignerSecretGrantNonceStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_issuance import (
    validate_secret_grant_signing_request,
)

REJECT_POLICY_MISSING = "REJECT_ED25519_SIGNER_POLICY_MISSING"
REJECT_REQUEST_INVALID = "REJECT_ED25519_SIGNER_REQUEST_INVALID"


def secret_grant_signer_rejection(
    backend: Any, request: SigningRequest, *, now_epoch: int
) -> str:
    """Validate grant domain and atomically enforce signed rate policy."""

    if request.requested_operation != SECRET_GRANT_SIGNING_OPERATION:
        return ""
    policy = backend.secret_grant_authority_policy
    if policy is None:
        return REJECT_POLICY_MISSING
    if validate_secret_grant_signing_request(
        request, policy, now_epoch=now_epoch
    ) is None:
        return REJECT_REQUEST_INVALID
    rate = backend.secret_grant_rate_authority
    if (
        type(rate) is not DurableSignerSecretGrantRateAuthority
        or type(rate.replay_store) is not DurableSignerSecretGrantNonceStore
    ):
        return REJECT_POLICY_MISSING
    if (
        rate.replay_store_id != policy.replay_store_id
        or rate.durability_receipt_id
        != policy.replay_store_durability_receipt_id
        or rate.replay_store_binding_digest
        != policy.replay_store_binding_digest
        or rate.replay_store_instance_digest
        != policy.replay_store_instance_digest
    ):
        return REJECT_REQUEST_INVALID
    admitted = rate.consume_issuance_attempt(
        authority_subject=policy.issuer_public_key,
        now_epoch=now_epoch,
        window_seconds=policy.rate_limit_window_seconds,
        max_requests=policy.rate_limit_max_requests,
    )
    return "" if admitted else REJECT_REQUEST_INVALID


__all__ = ["secret_grant_signer_rejection"]
