"""Exact current-generation policy for signer secret-grant issuance."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_optional_authority_bindings import (
    is_sha256_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import (
    CANONICAL_AUTHORITY_TIERS,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    constant_time_compare,
)

SECRET_GRANT_SIGNING_OPERATION = "issue_signer_secret_access_grant"


@dataclass(frozen=True, slots=True)
class SignerSecretGrantAuthorityPolicy:
    """Exact current-generation scope assigned to one grant authority key."""

    issuer_principal_id: str
    issuer_principal_provider: str
    issuer_public_key: str
    issuer_key_epoch: str
    requester_principal_id: str
    signer_agent_id: str
    signer_profile_id: str
    signing_key_ref_hash: str
    audit_mac_key_ref_hash: str
    key_epoch: str
    permission_snapshot_digest: str
    owner_config_id: str
    signer_generation_id: str
    signer_public_key: str
    signer_key_fingerprint: str
    replay_store_binding_digest: str
    replay_store_id: str
    replay_store_durability_receipt_id: str
    replay_store_instance_digest: str
    allowed_operations: tuple[str, ...]
    allowed_authority_tiers: tuple[str, ...]
    consensus_required_tiers: tuple[str, ...]
    rate_limit_window_seconds: int
    rate_limit_max_requests: int


def secret_grant_policy_rejected(policy: object) -> bool:
    """Reject malformed or ambiguous grant-authority policy."""

    if type(policy) is not SignerSecretGrantAuthorityPolicy:
        return True
    excluded = {
        "allowed_operations",
        "allowed_authority_tiers",
        "consensus_required_tiers",
        "rate_limit_window_seconds",
        "rate_limit_max_requests",
    }
    values = tuple(
        getattr(policy, item.name) for item in fields(policy) if item.name not in excluded
    )
    lists = (
        policy.allowed_operations,
        policy.allowed_authority_tiers,
        policy.consensus_required_tiers,
    )
    return bool(
        any(type(value) is not str or not value or not value.isascii() for value in values)
        or any(type(items) is not tuple or not items for items in lists[:2])
        or any(not _ascii_item(item) for items in lists for item in items)
        or any(tuple(sorted(set(items))) != items for items in lists)
        or not set(policy.consensus_required_tiers).issubset(
            policy.allowed_authority_tiers
        )
        or not set(policy.allowed_authority_tiers).issubset(
            CANONICAL_AUTHORITY_TIERS
        )
        or type(policy.rate_limit_window_seconds) is not int
        or not 1 <= policy.rate_limit_window_seconds <= 3600
        or type(policy.rate_limit_max_requests) is not int
        or not 1 <= policy.rate_limit_max_requests <= 1000
    )


def secret_grant_binding_rejected(
    grant: Mapping[str, Any], policy: SignerSecretGrantAuthorityPolicy
) -> bool:
    """Require every signed grant binding to match current policy."""

    excluded = {
        "issuer_key_epoch",
        "requester_principal_id",
        "allowed_operations",
        "allowed_authority_tiers",
        "consensus_required_tiers",
        "rate_limit_window_seconds",
        "rate_limit_max_requests",
    }
    binding_names = tuple(
        item.name for item in fields(policy) if item.name not in excluded
    )
    return bool(
        any(
            not constant_time_compare(str(grant[name]), str(getattr(policy, name)))
            for name in binding_names
        )
        or grant["requested_operation"] not in policy.allowed_operations
        or grant["authority_tier"] not in policy.allowed_authority_tiers
        or grant["requested_operation"] == SECRET_GRANT_SIGNING_OPERATION
        or constant_time_compare(policy.issuer_public_key, policy.signer_public_key)
    )


def secret_grant_consensus_rejected(tier: str, consensus: str | None) -> bool:
    """Keep elevated issuance closed until verified consensus is available."""

    if consensus is not None and not is_sha256_digest(consensus):
        return True
    # A digest-shaped value is not authenticated consensus. A later slice must
    # supply an opaque capability from the canonical consensus verifier.
    return consensus is not None if tier == "LOW" else True


def _ascii_item(value: object) -> bool:
    return type(value) is str and bool(value) and value.isascii()


__all__ = [
    "SECRET_GRANT_SIGNING_OPERATION",
    "SignerSecretGrantAuthorityPolicy",
    "secret_grant_binding_rejected",
    "secret_grant_consensus_rejected",
    "secret_grant_policy_rejected",
]
