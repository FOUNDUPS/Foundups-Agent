"""Canonical shape and time validation for signer revocation snapshots."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    ascii_deep,
    is_sha256,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    canonical_signing_input,
)

SNAPSHOT_SCHEMA = "reddog-signer-secret-grant-revocations.v1"
SNAPSHOT_PREFIX = SNAPSHOT_SCHEMA
MAX_SNAPSHOT_TTL_SECONDS = 300
SNAPSHOT_FIELDS = frozenset(
    {
        "schema_version", "snapshot_id", "policy_id", "owner_config_id",
        "manifest_id", "artifact_generation_digest", "authority_principal_id",
        "authority_principal_provider", "authority_public_key",
        "target_signer_agent_id", "target_signer_profile_id",
        "target_signer_public_key", "target_signer_key_epoch",
        "target_signer_generation_id", "store_id", "durability_receipt_id",
        "sequence", "issued_at", "expires_at", "revoked_grant_ids",
        "revoked_key_epochs", "signature",
    }
)
_DIGEST_FIELDS = (
    "snapshot_id", "policy_id", "owner_config_id", "manifest_id",
    "artifact_generation_digest", "target_signer_generation_id",
    "durability_receipt_id",
)
_LIST_FIELDS = ("revoked_grant_ids", "revoked_key_epochs")


def signer_grant_revocation_snapshot_id(value: Mapping[str, Any]) -> str:
    core = {
        key: value[key]
        for key in sorted(SNAPSHOT_FIELDS - {"snapshot_id", "signature"})
    }
    raw = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("ascii")).hexdigest()


def canonical_signer_grant_revocation_snapshot_input(
    value: Mapping[str, Any],
) -> str:
    return canonical_signing_input(value, SNAPSHOT_PREFIX)


def validated_signer_grant_revocation_snapshot(
    value: Mapping[str, Any], *, now_epoch: int,
) -> dict[str, Any]:
    if type(now_epoch) is not int:
        raise ValueError("signer_grant_revocation_snapshot_malformed")
    raw = validated_snapshot_integrity(value)
    if not raw["issued_at"] <= now_epoch < raw["expires_at"]:
        raise ValueError("signer_grant_revocation_snapshot_time_invalid")
    return raw


def validated_snapshot_integrity(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("signer_grant_revocation_snapshot_malformed")
    try:
        raw = dict(value)
    except Exception:
        raise ValueError("signer_grant_revocation_snapshot_malformed") from None
    if set(raw) != SNAPSHOT_FIELDS or raw.get("schema_version") != SNAPSHOT_SCHEMA:
        raise ValueError("signer_grant_revocation_snapshot_malformed")
    if not ascii_deep(raw) or not _types_valid(raw):
        raise ValueError("signer_grant_revocation_snapshot_malformed")
    if any(not is_sha256(raw[name]) for name in _DIGEST_FIELDS):
        raise ValueError("signer_grant_revocation_snapshot_digest_invalid")
    if raw["snapshot_id"] != signer_grant_revocation_snapshot_id(raw):
        raise ValueError("signer_grant_revocation_snapshot_id_invalid")
    _require_time_window(raw)
    _require_lists(raw)
    return raw


def _types_valid(raw: Mapping[str, Any]) -> bool:
    integers = {"sequence", "issued_at", "expires_at"}
    strings = SNAPSHOT_FIELDS - integers - set(_LIST_FIELDS)
    return bool(
        all(type(raw.get(name)) is int for name in integers)
        and all(
            type(raw.get(name)) is str and 0 < len(raw[name]) <= 4096
            for name in strings
        )
        and all(type(raw.get(name)) is list for name in _LIST_FIELDS)
    )


def _require_time_window(raw: Mapping[str, Any]) -> None:
    issued, expires = raw["issued_at"], raw["expires_at"]
    if (
        not 1 <= raw["sequence"] <= 9_223_372_036_854_775_807
        or not 0 <= issued < expires
        or not 0 < expires - issued <= MAX_SNAPSHOT_TTL_SECONDS
    ):
        raise ValueError("signer_grant_revocation_snapshot_time_invalid")


def _require_lists(raw: Mapping[str, Any]) -> None:
    for name in _LIST_FIELDS:
        values = raw[name]
        invalid_item = any(
            type(item) is not str
            or not 0 < len(item) <= 256
            or not item.isascii()
            for item in values
        )
        if len(values) > 4096 or invalid_item or values != sorted(set(values)):
            raise ValueError("signer_grant_revocation_snapshot_scope_invalid")
    if any(not is_sha256(item) for item in raw["revoked_grant_ids"]):
        raise ValueError("signer_grant_revocation_snapshot_scope_invalid")


__all__ = [
    "MAX_SNAPSHOT_TTL_SECONDS", "SNAPSHOT_FIELDS", "SNAPSHOT_SCHEMA",
    "canonical_signer_grant_revocation_snapshot_input",
    "signer_grant_revocation_snapshot_id",
    "validated_signer_grant_revocation_snapshot", "validated_snapshot_integrity",
]
