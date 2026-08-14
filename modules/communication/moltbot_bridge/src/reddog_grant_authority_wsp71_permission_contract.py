"""Exact public receipt contract for grant-authority WSP 71 access."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    digest,
    is_sha256,
)

SCHEMA_VERSION = "reddog_grant_authority_wsp71_permission_receipt.v1"
PERMISSION_FILENAME = "grant_authority_wsp71_permission_receipt.json"
SECRETS_READ = "SECRETS_READ"
GET_SECRET = "get_secret"
MAX_RECEIPT_BYTES = 16 * 1024
FIELDS = frozenset(
    {
        "schema_version", "receipt_id", "owner_config_id", "e0_manifest_id",
        "e0_artifact_generation_digest", "e0_generation",
        "e0_generation_revision", "issuer_principal_id",
        "issuer_principal_provider", "issuer_public_key", "issuer_key_epoch",
        "signer_agent_id", "signer_profile_id", "signing_key_ref_hash",
        "audit_mac_key_ref_hash", "permission", "allowed_operations",
        "issued_at", "expires_at", "revoked",
    }
)


def permission_receipt_id(value: Mapping[str, Any]) -> str:
    body = dict(value)
    body.pop("receipt_id", None)
    return digest(body)


def validate_permission_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate exact shape and meaning without granting authority."""

    if not isinstance(value, Mapping) or set(value) != FIELDS:
        raise RuntimeArtifactManifestError("grant_permission_receipt_malformed")
    raw = dict(value)
    integers = {"e0_generation", "issued_at", "expires_at"}
    structured = {"allowed_operations", "revoked"}
    strings = FIELDS - integers - structured
    digests = {
        "receipt_id", "e0_manifest_id", "e0_artifact_generation_digest",
        "signing_key_ref_hash", "audit_mac_key_ref_hash",
    }
    if (
        any(
            type(raw.get(name)) is not str
            or not raw[name]
            or not raw[name].isascii()
            or len(raw[name]) > 4096
            for name in strings
        )
        or any(type(raw.get(name)) is not int for name in integers)
        or type(raw.get("allowed_operations")) is not list
        or type(raw.get("revoked")) is not bool
        or any(not is_sha256(raw[name]) for name in digests)
        or raw["schema_version"] != SCHEMA_VERSION
        or raw["permission"] != SECRETS_READ
        or raw["allowed_operations"] != [GET_SECRET]
        or raw["revoked"] is not False
        or raw["receipt_id"] != permission_receipt_id(raw)
        or not 0 <= raw["issued_at"] < raw["expires_at"]
    ):
        raise RuntimeArtifactManifestError("grant_permission_receipt_rejected")
    return raw


__all__ = [
    "FIELDS", "GET_SECRET", "MAX_RECEIPT_BYTES", "PERMISSION_FILENAME",
    "SCHEMA_VERSION", "SECRETS_READ", "permission_receipt_id",
    "validate_permission_receipt",
]
