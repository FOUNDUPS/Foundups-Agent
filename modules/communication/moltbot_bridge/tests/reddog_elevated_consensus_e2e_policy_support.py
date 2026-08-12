"""Target-specific owner policy fixtures for elevated consensus E2E tests."""

from __future__ import annotations

import hashlib
from typing import Any

from modules.communication.moltbot_bridge.src.reddog_signer_resolve_per_sign_backend import (
    ResolvePerSignBinding,
)


def build_binding(
    store: Any, role: str, target: str, issuer: str
) -> ResolvePerSignBinding:
    def digest(char: str) -> str:
        return "sha256:" + char * 64

    return ResolvePerSignBinding(
        issuer_principal_id=f"grant:owner:{role}",
        issuer_principal_provider="local",
        issuer_public_key=issuer,
        signer_agent_id=f"signer:{role}",
        signer_profile_id=f"profile:{role}",
        signing_key_ref_hash=digest("1"),
        audit_mac_key_ref_hash=digest("2"),
        key_epoch="epoch-1",
        permission_snapshot_digest=digest("3"),
        owner_config_id=digest("4"),
        signer_generation_id=digest("5"),
        signer_public_key=target,
        signer_key_fingerprint="sha256:" + hashlib.sha256(target.encode()).hexdigest(),
        replay_store_binding_digest=store.replay_store_binding_digest,
        replay_store_id=store.replay_store_id,
        replay_store_durability_receipt_id=store.durability_receipt_id,
        replay_store_instance_digest=store.replay_store_instance_digest,
    )


def owner_policy(binding: ResolvePerSignBinding) -> dict[str, Any]:
    return {
        "grant_authority_principal_id": binding.issuer_principal_id,
        "grant_authority_principal_provider": binding.issuer_principal_provider,
        "grant_authority_public_key": binding.issuer_public_key,
        "grant_authority_key_epoch": "grant-epoch-1",
        "grant_requester_principal_id": "provider:grant-client",
        "revocation_authority_principal_id": "revocation:owner",
        "revocation_authority_principal_provider": "local",
        "revocation_authority_public_key": "revocation-key",
        "target_signer_agent_id": binding.signer_agent_id,
        "target_signer_profile_id": binding.signer_profile_id,
        "target_signer_public_key": binding.signer_public_key,
        "target_signer_key_fingerprint": binding.signer_key_fingerprint,
        "target_signer_key_epoch": binding.key_epoch,
        "target_signer_generation_id": binding.signer_generation_id,
        "signing_key_ref_hash": binding.signing_key_ref_hash,
        "audit_mac_key_ref_hash": binding.audit_mac_key_ref_hash,
        "permission_snapshot_digest": binding.permission_snapshot_digest,
        "owner_config_id": binding.owner_config_id,
        "allowed_operations": ["delegate_reddog_identity", "edit_foundup_module"],
        "allowed_authority_tiers": ["HIGH"],
        "consensus_required_tiers": ["HIGH"],
        "rate_limit_window_seconds": 60,
        "rate_limit_max_requests": 10,
        "replay_store_id": binding.replay_store_id,
        "replay_store_durability_receipt_id": binding.replay_store_durability_receipt_id,
        "expires_at": 2_000_000_120,
    }


__all__ = ["build_binding", "owner_policy"]
