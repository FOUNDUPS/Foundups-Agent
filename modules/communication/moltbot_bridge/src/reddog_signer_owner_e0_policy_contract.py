"""Signed owner policy contract for production E0 signer composition."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    ascii_deep,
    is_sha256,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_v6 import (
    GRANT_SERVICE_DIGEST_FIELDS,
    GRANT_SERVICE_FIELDS,
    GRANT_SERVICE_MANIFEST_FIELDS,
    POLICY_DIGEST_FIELDS_V5,
    POLICY_FIELDS_V5,
    POLICY_PREFIX_V6,
    POLICY_SCHEMA_V6,
    require_grant_service_bindings,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import canonical_signing_input
POLICY_SCHEMA_V5 = POLICY_PREFIX_V5 = "reddog-signer-owner-e0-policy.v5"
POLICY_SCHEMA = POLICY_PREFIX = POLICY_SCHEMA_V6
MAX_POLICY_TTL_SECONDS = 900
CANONICAL_AUTHORITY_TIERS = frozenset({"LOW", "HIGH", "ULTRA"})
POLICY_FIELDS_V6 = POLICY_FIELDS_V5 | GRANT_SERVICE_FIELDS
POLICY_FIELDS = POLICY_FIELDS_V6
_DIGEST_FIELDS_V6 = POLICY_DIGEST_FIELDS_V5 + GRANT_SERVICE_DIGEST_FIELDS
_LIST_FIELDS = ("allowed_operations", "allowed_authority_tiers", "consensus_required_tiers")
_AUTHORITY_BINDING_EXCLUDED_FIELDS = {
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
} | GRANT_SERVICE_MANIFEST_FIELDS


def signer_owner_e0_policy_id(value: Mapping[str, Any]) -> str:
    fields = _policy_fields(value.get("schema_version"))
    core = {
        key: value[key]
        for key in sorted(fields - {"policy_id", "signature"})
    }
    raw = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("ascii")).hexdigest()


def signer_key_reference_digest(reference: str) -> str:
    if type(reference) is not str or not reference or not reference.isascii():
        raise ValueError("signer_owner_e0_key_reference_invalid")
    return "sha256:" + hashlib.sha256(reference.encode("ascii")).hexdigest()


def signer_owner_e0_authority_binding_digest(value: Mapping[str, Any]) -> str:
    try:
        fields = _policy_fields(value.get("schema_version"))
        included = fields - _AUTHORITY_BINDING_EXCLUDED_FIELDS
        core = {key: value[key] for key in sorted(included)}
        raw = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        encoded = raw.encode("ascii")
    except (KeyError, TypeError, UnicodeEncodeError) as exc:
        raise ValueError("signer_owner_e0_authority_binding_invalid") from exc
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def canonical_signer_owner_e0_policy_input(value: Mapping[str, Any]) -> str:
    schema = value.get("schema_version")
    _policy_fields(schema)
    prefix = POLICY_PREFIX_V6 if schema == POLICY_SCHEMA_V6 else POLICY_PREFIX_V5
    return canonical_signing_input(value, prefix)


def validated_signer_owner_e0_policy(value: Mapping[str, Any], *, now_epoch: int) -> dict[str, Any]:
    if not isinstance(value, Mapping) or type(now_epoch) is not int:
        raise ValueError("signer_owner_e0_policy_malformed")
    raw = {key: list(item) if isinstance(item, list) else item for key, item in value.items()}
    try:
        fields = _policy_fields(raw.get("schema_version"))
    except ValueError as exc:
        raise ValueError("signer_owner_e0_policy_malformed") from exc
    if set(raw) != fields:
        raise ValueError("signer_owner_e0_policy_malformed")
    if not ascii_deep(raw) or not _types_valid(raw, fields):
        raise ValueError("signer_owner_e0_policy_malformed")
    digest_fields = (
        _DIGEST_FIELDS_V6
        if raw["schema_version"] == POLICY_SCHEMA_V6
        else POLICY_DIGEST_FIELDS_V5
    )
    if any(not is_sha256(str(raw[name])) for name in digest_fields):
        raise ValueError("signer_owner_e0_policy_digest_invalid")
    if raw["policy_id"] != signer_owner_e0_policy_id(raw):
        raise ValueError("signer_owner_e0_policy_id_invalid")
    _require_time(raw, now_epoch)
    _require_lists(raw)
    if raw["schema_version"] == POLICY_SCHEMA_V6:
        require_grant_service_bindings(raw)
    return raw


def _types_valid(raw: Mapping[str, Any], fields: frozenset[str]) -> bool:
    integers = {
        "generation",
        "rate_limit_window_seconds",
        "rate_limit_max_requests",
        "issued_at",
        "expires_at",
    }
    strings = fields - integers - set(_LIST_FIELDS)
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


def _policy_fields(schema: object) -> frozenset[str]:
    if schema == POLICY_SCHEMA_V5:
        return POLICY_FIELDS_V5
    if schema == POLICY_SCHEMA_V6:
        return POLICY_FIELDS_V6
    raise ValueError("signer_owner_e0_policy_schema_invalid")
__all__ = [
    "CANONICAL_AUTHORITY_TIERS",
    "POLICY_FIELDS",
    "POLICY_FIELDS_V5",
    "POLICY_FIELDS_V6",
    "POLICY_SCHEMA",
    "POLICY_SCHEMA_V5",
    "POLICY_SCHEMA_V6",
    "canonical_signer_owner_e0_policy_input",
    "signer_key_reference_digest",
    "signer_owner_e0_authority_binding_digest",
    "signer_owner_e0_policy_id",
    "validated_signer_owner_e0_policy",
]
