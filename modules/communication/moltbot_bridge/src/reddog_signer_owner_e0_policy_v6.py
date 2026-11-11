"""Additive v6 grant-service fields for the signer owner policy."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping


CANONICAL_AUTHORITY_TIERS = frozenset({"LOW", "HIGH", "ULTRA"})
MAX_POLICY_TTL_SECONDS = 900
_LIST_FIELDS = ("allowed_operations", "allowed_authority_tiers", "consensus_required_tiers")


def require_policy_scope_lists(raw: Mapping[str, Any]) -> None:
    low_handshake = (
        raw["allowed_operations"] == ["signer_socket_peer_handshake"]
        and raw["allowed_authority_tiers"] == ["LOW"]
    )
    for name in _LIST_FIELDS:
        values = raw[name]
        if (
            (not values and not (name == "consensus_required_tiers" and low_handshake))
            or len(values) > 64
            or values != sorted(set(values))
            or any(type(item) is not str or not item or not item.isascii() for item in values)
        ):
            raise ValueError("signer_owner_e0_policy_scope_invalid")
    if not set(raw["consensus_required_tiers"]).issubset(raw["allowed_authority_tiers"]):
        raise ValueError("signer_owner_e0_policy_scope_invalid")
    if not set(raw["allowed_authority_tiers"]).issubset(CANONICAL_AUTHORITY_TIERS):
        raise ValueError("signer_owner_e0_policy_scope_invalid")


POLICY_SCHEMA_V6 = POLICY_PREFIX_V6 = "reddog-signer-owner-e0-policy.v6"
POLICY_FIELDS_V5 = frozenset(
    {
        "schema_version", "policy_id", "owner_config_id", "manifest_id",
        "artifact_generation_digest", "config_digest", "generation",
        "generation_revision", "grant_authority_principal_id",
        "grant_authority_principal_provider", "grant_authority_public_key",
        "grant_authority_key_epoch", "grant_requester_principal_id",
        "revocation_authority_principal_id",
        "revocation_authority_principal_provider",
        "revocation_authority_public_key", "target_signer_agent_id",
        "target_signer_profile_id", "target_signer_public_key",
        "target_signer_key_fingerprint", "target_signer_key_epoch",
        "target_signer_generation_id", "signing_key_ref_hash",
        "audit_mac_key_ref_hash", "permission_snapshot_digest",
        "permission_snapshot_receipt_id", "replay_root", "replay_path",
        "replay_store_id", "replay_store_durability_receipt_id",
        "revocation_root", "revocation_path", "revocation_store_id",
        "revocation_store_durability_receipt_id",
        "revocation_snapshot_schema", "revocation_store_schema",
        "revocation_witness_root", "revocation_witness_path",
        "revocation_witness_store_id", "revocation_lock_path",
        "revocation_witness_store_durability_receipt_id",
        "revocation_anchor_store_id",
        "revocation_anchor_store_durability_receipt_id",
        "revocation_anchor_state_binding_digest", "allowed_operations",
        "allowed_authority_tiers", "consensus_required_tiers",
        "rate_limit_window_seconds", "rate_limit_max_requests", "issued_at",
        "expires_at", "signature",
    }
)
POLICY_DIGEST_FIELDS_V5 = (
    "policy_id", "owner_config_id", "manifest_id",
    "artifact_generation_digest", "config_digest",
    "target_signer_key_fingerprint", "target_signer_generation_id",
    "signing_key_ref_hash", "audit_mac_key_ref_hash",
    "permission_snapshot_digest", "permission_snapshot_receipt_id",
    "replay_store_durability_receipt_id",
    "revocation_store_durability_receipt_id",
    "revocation_witness_store_durability_receipt_id",
    "revocation_anchor_store_durability_receipt_id",
    "revocation_anchor_state_binding_digest",
)
GRANT_SERVICE_FIELDS = frozenset(
    {
        "grant_authority_signer_agent_id",
        "grant_authority_signer_profile_id",
        "grant_authority_key_fingerprint",
        "grant_authority_manifest_id",
        "grant_authority_artifact_generation_digest",
        "grant_authority_config_digest",
        "grant_authority_run_packet_digest",
        "grant_authority_signing_key_ref_hash",
        "grant_authority_audit_mac_key_ref_hash",
        "grant_authority_permission_snapshot_digest",
        "grant_authority_permission_snapshot_receipt_id",
    }
)
GRANT_SERVICE_MANIFEST_FIELDS = frozenset(
    {
        "grant_authority_manifest_id",
        "grant_authority_artifact_generation_digest",
        "grant_authority_config_digest",
        "grant_authority_run_packet_digest",
    }
)
GRANT_SERVICE_DIGEST_FIELDS = (
    "grant_authority_key_fingerprint",
    "grant_authority_manifest_id",
    "grant_authority_artifact_generation_digest",
    "grant_authority_config_digest",
    "grant_authority_run_packet_digest",
    "grant_authority_signing_key_ref_hash",
    "grant_authority_audit_mac_key_ref_hash",
    "grant_authority_permission_snapshot_digest",
    "grant_authority_permission_snapshot_receipt_id",
)
_SERVICE_AGENT_ID = re.compile(
    r"[a-z][a-z0-9_-]{1,31}:[a-z0-9][a-z0-9._-]{0,95}\Z"
)
_SERVICE_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def valid_service_agent_id(value: object) -> bool:
    """Return whether a public signer agent ID has one bounded namespace."""

    return type(value) is str and _SERVICE_AGENT_ID.fullmatch(value) is not None


def valid_service_token(value: object) -> bool:
    """Return whether a public profile or epoch is a bounded inert token."""

    return type(value) is str and _SERVICE_TOKEN.fullmatch(value) is not None


def require_grant_service_bindings(raw: Mapping[str, Any]) -> None:
    fingerprint = "sha256:" + hashlib.sha256(
        str(raw["grant_authority_public_key"]).encode("ascii")
    ).hexdigest()
    key_references = {
        raw["signing_key_ref_hash"],
        raw["audit_mac_key_ref_hash"],
        raw["grant_authority_signing_key_ref_hash"],
        raw["grant_authority_audit_mac_key_ref_hash"],
    }
    if (
        raw["grant_authority_key_fingerprint"] != fingerprint
        or not valid_service_agent_id(raw["grant_authority_signer_agent_id"])
        or not valid_service_agent_id(raw["target_signer_agent_id"])
        or not valid_service_token(raw["grant_authority_signer_profile_id"])
        or not valid_service_token(raw["target_signer_profile_id"])
        or not valid_service_token(raw["grant_authority_key_epoch"])
        or not valid_service_token(raw["target_signer_key_epoch"])
        or raw["grant_authority_public_key"]
        == raw["target_signer_public_key"]
        or raw["grant_authority_key_fingerprint"]
        == raw["target_signer_key_fingerprint"]
        or raw["grant_authority_signer_agent_id"]
        == raw["target_signer_agent_id"]
        or raw["grant_authority_signer_profile_id"]
        == raw["target_signer_profile_id"]
        or len(key_references) != 4
    ):
        raise ValueError("signer_owner_e0_grant_service_binding_invalid")


def require_policy_time(raw: Mapping[str, Any], now_epoch: int) -> None:
    issued = raw["issued_at"]
    expires = raw["expires_at"]
    if (
        raw["generation"] < 1
        or not 0 <= issued <= now_epoch < expires
        or not 0 < expires - issued <= MAX_POLICY_TTL_SECONDS
        or not 1 <= raw["rate_limit_window_seconds"] <= 3600
        or not 1 <= raw["rate_limit_max_requests"] <= 1000
    ):
        raise ValueError("signer_owner_e0_policy_time_invalid")


__all__ = [
    "GRANT_SERVICE_DIGEST_FIELDS",
    "GRANT_SERVICE_FIELDS",
    "GRANT_SERVICE_MANIFEST_FIELDS",
    "POLICY_PREFIX_V6",
    "POLICY_DIGEST_FIELDS_V5",
    "POLICY_FIELDS_V5",
    "POLICY_SCHEMA_V6",
    "require_grant_service_bindings",
    "valid_service_agent_id",
    "valid_service_token",
]
