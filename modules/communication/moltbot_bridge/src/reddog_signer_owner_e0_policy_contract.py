"""Signed owner policy contract for production E0 signer composition."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    ascii_deep,
    is_sha256,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import canonical_signing_input
POLICY_SCHEMA = POLICY_PREFIX = "reddog-signer-owner-e0-policy.v5"
MAX_POLICY_TTL_SECONDS = 900
CANONICAL_AUTHORITY_TIERS = frozenset({"LOW", "HIGH", "ULTRA"})
POLICY_FIELDS = frozenset(
    {
        "schema_version",
        "policy_id",
        "owner_config_id",
        "manifest_id",
        "artifact_generation_digest",
        "config_digest",
        "generation",
        "generation_revision",
        "grant_authority_principal_id",
        "grant_authority_principal_provider",
        "grant_authority_public_key",
        "grant_authority_key_epoch",
        "grant_requester_principal_id",
        "revocation_authority_principal_id",
        "revocation_authority_principal_provider",
        "revocation_authority_public_key",
        "target_signer_agent_id",
        "target_signer_profile_id",
        "target_signer_public_key",
        "target_signer_key_fingerprint",
        "target_signer_key_epoch",
        "target_signer_generation_id",
        "signing_key_ref_hash",
        "audit_mac_key_ref_hash",
        "permission_snapshot_digest",
        "permission_snapshot_receipt_id",
        "replay_root",
        "replay_path",
        "replay_store_id",
        "replay_store_durability_receipt_id",
        "revocation_root",
        "revocation_path",
        "revocation_store_id",
        "revocation_store_durability_receipt_id",
        "revocation_snapshot_schema", "revocation_store_schema", "revocation_witness_root",
        "revocation_witness_path", "revocation_witness_store_id", "revocation_lock_path",
        "revocation_witness_store_durability_receipt_id",
        "revocation_anchor_store_id", "revocation_anchor_store_durability_receipt_id",
        "revocation_anchor_state_binding_digest",
        "allowed_operations",
        "allowed_authority_tiers",
        "consensus_required_tiers",
        "rate_limit_window_seconds",
        "rate_limit_max_requests",
        "issued_at",
        "expires_at",
        "signature",
    }
)
_DIGEST_FIELDS = (
    "policy_id",
    "owner_config_id",
    "manifest_id",
    "artifact_generation_digest",
    "config_digest",
    "target_signer_key_fingerprint",
    "target_signer_generation_id",
    "signing_key_ref_hash",
    "audit_mac_key_ref_hash",
    "permission_snapshot_digest",
    "permission_snapshot_receipt_id",
    "replay_store_durability_receipt_id",
    "revocation_store_durability_receipt_id", "revocation_witness_store_durability_receipt_id",
    "revocation_anchor_store_durability_receipt_id",
    "revocation_anchor_state_binding_digest",
)
_LIST_FIELDS = ("allowed_operations", "allowed_authority_tiers", "consensus_required_tiers")
_AUTHORITY_BINDING_FIELDS = POLICY_FIELDS - {
    "schema_version",
    "policy_id",
    "owner_config_id",
    "manifest_id",
    "artifact_generation_digest",
    "config_digest",
    "generation",
    "generation_revision",
    "issued_at",
    "expires_at",
    "signature",
}


def signer_owner_e0_policy_id(value: Mapping[str, Any]) -> str:
    core = {
        key: value[key]
        for key in sorted(POLICY_FIELDS - {"policy_id", "signature"})
    }
    raw = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("ascii")).hexdigest()


def signer_key_reference_digest(reference: str) -> str:
    if type(reference) is not str or not reference or not reference.isascii():
        raise ValueError("signer_owner_e0_key_reference_invalid")
    return "sha256:" + hashlib.sha256(reference.encode("ascii")).hexdigest()


def signer_owner_e0_authority_binding_digest(value: Mapping[str, Any]) -> str:
    try:
        core = {key: value[key] for key in sorted(_AUTHORITY_BINDING_FIELDS)}
        raw = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        encoded = raw.encode("ascii")
    except (KeyError, TypeError, UnicodeEncodeError) as exc:
        raise ValueError("signer_owner_e0_authority_binding_invalid") from exc
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def canonical_signer_owner_e0_policy_input(value: Mapping[str, Any]) -> str:
    return canonical_signing_input(value, POLICY_PREFIX)


def validated_signer_owner_e0_policy(value: Mapping[str, Any], *, now_epoch: int) -> dict[str, Any]:
    if not isinstance(value, Mapping) or type(now_epoch) is not int:
        raise ValueError("signer_owner_e0_policy_malformed")
    raw = {key: list(item) if isinstance(item, list) else item for key, item in value.items()}
    if set(raw) != POLICY_FIELDS or raw.get("schema_version") != POLICY_SCHEMA:
        raise ValueError("signer_owner_e0_policy_malformed")
    if not ascii_deep(raw) or not _types_valid(raw):
        raise ValueError("signer_owner_e0_policy_malformed")
    if any(not is_sha256(str(raw[name])) for name in _DIGEST_FIELDS):
        raise ValueError("signer_owner_e0_policy_digest_invalid")
    if raw["policy_id"] != signer_owner_e0_policy_id(raw):
        raise ValueError("signer_owner_e0_policy_id_invalid")
    _require_time(raw, now_epoch)
    _require_lists(raw)
    return raw


def _types_valid(raw: Mapping[str, Any]) -> bool:
    integers = {
        "generation",
        "rate_limit_window_seconds",
        "rate_limit_max_requests",
        "issued_at",
        "expires_at",
    }
    strings = POLICY_FIELDS - integers - set(_LIST_FIELDS)
    return bool(
        all(type(raw.get(name)) is int for name in integers)
        and all(type(raw.get(name)) is str and raw[name] for name in strings)
        and all(type(raw.get(name)) is list for name in _LIST_FIELDS)
    )


def _require_time(raw: Mapping[str, Any], now_epoch: int) -> None:
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


def _require_lists(raw: Mapping[str, Any]) -> None:
    for name in _LIST_FIELDS:
        values = raw[name]
        if (
            not values
            or len(values) > 64
            or values != sorted(set(values))
            or any(type(item) is not str or not item or not item.isascii() for item in values)
        ):
            raise ValueError("signer_owner_e0_policy_scope_invalid")
    if not set(raw["consensus_required_tiers"]).issubset(raw["allowed_authority_tiers"]):
        raise ValueError("signer_owner_e0_policy_scope_invalid")
    if not set(raw["allowed_authority_tiers"]).issubset(CANONICAL_AUTHORITY_TIERS):
        raise ValueError("signer_owner_e0_policy_scope_invalid")
__all__ = [
    "CANONICAL_AUTHORITY_TIERS",
    "POLICY_FIELDS",
    "POLICY_SCHEMA",
    "canonical_signer_owner_e0_policy_input",
    "signer_key_reference_digest",
    "signer_owner_e0_authority_binding_digest",
    "signer_owner_e0_policy_id",
    "validated_signer_owner_e0_policy",
]
