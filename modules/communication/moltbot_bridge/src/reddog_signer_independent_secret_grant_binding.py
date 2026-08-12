"""Current-generation binding derivation for independent grant issuance."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_resolve_per_sign_backend import (
    ResolvePerSignBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_authority_policy import (
    SignerSecretGrantAuthorityPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_nonce_store import (
    DurableSignerSecretGrantNonceStore,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    constant_time_compare,
)


def resolve_secret_grant_target_binding(
    policy: Mapping[str, Any],
    replay_store: DurableSignerSecretGrantNonceStore,
) -> ResolvePerSignBinding:
    """Derive target signer scope only from signed owner policy and store."""

    if type(replay_store) is not DurableSignerSecretGrantNonceStore:
        raise ValueError("secret_grant_replay_store_invalid")
    return ResolvePerSignBinding(
        issuer_principal_id=str(policy["grant_authority_principal_id"]),
        issuer_principal_provider=str(policy["grant_authority_principal_provider"]),
        issuer_public_key=str(policy["grant_authority_public_key"]),
        signer_agent_id=str(policy["target_signer_agent_id"]),
        signer_profile_id=str(policy["target_signer_profile_id"]),
        signing_key_ref_hash=str(policy["signing_key_ref_hash"]),
        audit_mac_key_ref_hash=str(policy["audit_mac_key_ref_hash"]),
        key_epoch=str(policy["target_signer_key_epoch"]),
        permission_snapshot_digest=str(policy["permission_snapshot_digest"]),
        owner_config_id=str(policy["owner_config_id"]),
        signer_generation_id=str(policy["target_signer_generation_id"]),
        signer_public_key=str(policy["target_signer_public_key"]),
        signer_key_fingerprint=str(policy["target_signer_key_fingerprint"]),
        replay_store_binding_digest=replay_store.replay_store_binding_digest,
        replay_store_id=replay_store.replay_store_id,
        replay_store_durability_receipt_id=replay_store.durability_receipt_id,
        replay_store_instance_digest=replay_store.replay_store_instance_digest,
    )


def build_secret_grant_authority_policy(
    owner_policy: Mapping[str, Any],
    binding: ResolvePerSignBinding,
    replay_store: DurableSignerSecretGrantNonceStore,
    *,
    authority_principal_id: str,
    authority_principal_provider: str,
    authority_public_key: str,
    authority_key_epoch: str,
    requester_principal_id: str,
) -> SignerSecretGrantAuthorityPolicy:
    """Bind an injected grant client to signed E0 authority and rate policy."""

    expected = (
        (authority_principal_id, owner_policy["grant_authority_principal_id"]),
        (authority_principal_provider, owner_policy["grant_authority_principal_provider"]),
        (authority_public_key, owner_policy["grant_authority_public_key"]),
        (authority_key_epoch, owner_policy["grant_authority_key_epoch"]),
        (
            requester_principal_id,
            owner_policy["grant_requester_principal_id"],
        ),
        (replay_store.replay_store_id, owner_policy["replay_store_id"]),
        (
            replay_store.durability_receipt_id,
            owner_policy["replay_store_durability_receipt_id"],
        ),
    )
    if any(not constant_time_compare(str(left), str(right)) for left, right in expected):
        raise ValueError("secret_grant_authority_binding_invalid")
    return SignerSecretGrantAuthorityPolicy(
        **asdict(binding),
        issuer_key_epoch=str(owner_policy["grant_authority_key_epoch"]),
        requester_principal_id=requester_principal_id,
        allowed_operations=tuple(owner_policy["allowed_operations"]),
        allowed_authority_tiers=tuple(owner_policy["allowed_authority_tiers"]),
        consensus_required_tiers=tuple(owner_policy["consensus_required_tiers"]),
        rate_limit_window_seconds=int(owner_policy["rate_limit_window_seconds"]),
        rate_limit_max_requests=int(owner_policy["rate_limit_max_requests"]),
    )


__all__ = [
    "build_secret_grant_authority_policy",
    "resolve_secret_grant_target_binding",
]
