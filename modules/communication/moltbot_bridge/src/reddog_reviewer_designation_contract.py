"""Strict reviewer-designation wire data; validation does not grant authority."""

from __future__ import annotations

from typing import Any

from .reddog_ed25519_signature_verifier_backend import (
    MAX_SIGNING_INPUT_BYTES, decode_ed25519_public_key, decode_ed25519_signature,
)
from .reddog_runtime_artifact_manifest_contract import canonical_json, digest, is_sha256

AUTHORITY_SCHEMA = "reddog_reviewer_designation_authority.v1"
DESIGNATION_SCHEMA = "reddog_reviewer_designation.v1"
DECISION_SCHEMA = "reddog_effect_reviewer_decision.v1"
PRIVILEGE = "designate_effect_reviewers"
SIGNING_PREFIX = "reddog-reviewer-designation.v1."
PARENT_AUTHORITY_SCHEMA = "reddog_parent_reviewer_designation_authority.v1"
PARENT_DESIGNATION_SCHEMA = "reddog_parent_reviewer_designation.v1"
PARENT_DECISION_SCHEMA = "reddog_elevated_authority_reviewer_decision.v1"
PARENT_PRIVILEGE = "designate_parent_reviewers"
PARENT_SIGNING_PREFIX = "reddog-parent-reviewer-designation.v1."
_COMMON_FIELDS = frozenset({
    "schema_version", "privilege", "issuer_principal_id", "issuer_principal_provider",
    "issuer_key_epoch", "repo_full_name", "foundup_id", "policy_digest",
    "decision_schema_version", "issued_at", "expires_at",
})
_AUTHORITY_FIELDS = _COMMON_FIELDS | {"issuer_public_key"}
_DESIGNATION_FIELDS = _COMMON_FIELDS | {"owner_authority_digest", "reviewers", "signature"}
_ENTRY_FIELDS = frozenset({
    "principal_id", "principal_provider", "public_key", "key_epoch",
    "authorized_roles", "issued_at", "expires_at",
})


def _invalid() -> None:
    raise ValueError("reviewer_designation_invalid")


def _text(value: Any, maximum: int = 1024) -> bool:
    return type(value) is str and 1 <= len(value) <= maximum and value.isascii() and bool(value.strip())


def _interval(value: dict[str, Any]) -> None:
    start, end = value["issued_at"], value["expires_at"]
    if type(start) is not int or type(end) is not int or not 0 <= start < end:
        _invalid()


def _shape(value: Any, fields: frozenset[str]) -> dict[str, Any]:
    if type(value) is not dict or any(type(key) is not str for key in value) or set(value) != fields:
        _invalid()
    copied = dict(value)
    _interval(copied)
    return copied


def _common(value: Any, fields: frozenset[str], schema: str, privilege=PRIVILEGE, decision_schema=DECISION_SCHEMA) -> dict[str, Any]:
    copied = _shape(value, fields)
    text_fields = _COMMON_FIELDS - {"issued_at", "expires_at"}
    if (any(not _text(copied[key]) for key in text_fields)
            or copied["schema_version"] != schema or copied["privilege"] != privilege
            or copied["decision_schema_version"] != decision_schema
            or not is_sha256(copied["policy_digest"])):
        _invalid()
    return copied


def validate_reviewer_designation_authority(value: Any) -> dict[str, Any]:
    """Return defensive exact wire data; its trusted origin must be established separately."""
    copied = _common(value, _AUTHORITY_FIELDS, AUTHORITY_SCHEMA)
    key = copied["issuer_public_key"]
    if not _text(key) or decode_ed25519_public_key(key) is None:
        _invalid()
    return copied


def _reviewer(value: Any) -> dict[str, Any]:
    copied = _shape(value, _ENTRY_FIELDS)
    for key in ("principal_id", "principal_provider", "public_key", "key_epoch"):
        if not _text(copied[key]):
            _invalid()
    roles = copied["authorized_roles"]
    if (decode_ed25519_public_key(copied["public_key"]) is None
            or type(roles) is not list or not 1 <= len(roles) <= 8
            or any(not _text(role, 64) for role in roles)
            or len(set(roles)) != len(roles)):
        _invalid()
    copied["authorized_roles"] = list(roles)
    return copied


def _signing_input(designation: dict[str, Any]) -> str:
    payload = {key: value for key, value in designation.items() if key != "signature"}
    result = (PARENT_SIGNING_PREFIX if designation["privilege"] == PARENT_PRIVILEGE else SIGNING_PREFIX) + canonical_json(payload)
    if len(result.encode("ascii")) > MAX_SIGNING_INPUT_BYTES:
        _invalid()
    return result


def validate_reviewer_designation(value: Any, *, _parent=False) -> dict[str, Any]:
    """Validate and copy one signed-shaped bundle without authenticating its signature."""
    copied = _common(value, _DESIGNATION_FIELDS, PARENT_DESIGNATION_SCHEMA if _parent else DESIGNATION_SCHEMA,
                     PARENT_PRIVILEGE if _parent else PRIVILEGE, PARENT_DECISION_SCHEMA if _parent else DECISION_SCHEMA)
    owner_digest, signature = copied["owner_authority_digest"], copied["signature"]
    values = copied["reviewers"]
    if (not _text(owner_digest) or not is_sha256(owner_digest)
            or not _text(signature) or decode_ed25519_signature(signature) is None
            or type(values) is not list or not 1 <= len(values) <= 8):
        _invalid()
    reviewers = [_reviewer(entry) for entry in values]
    pairs = [(entry["principal_id"], entry["principal_provider"]) for entry in reviewers]
    if len(set(pairs)) != len(pairs):
        _invalid()
    copied["reviewers"] = reviewers
    _signing_input(copied)
    return copied


def reviewer_designation_authority_digest(authority: Any) -> str:
    """Hash the whole validated block, never a caller-supplied verified flag."""
    if type(authority) is not dict:
        _invalid()
    return digest(validate_parent_reviewer_designation_authority(authority) if authority.get("schema_version") == PARENT_AUTHORITY_SCHEMA else validate_reviewer_designation_authority(authority))


def reviewer_designation_signing_input(designation: Any) -> str:
    """Revalidate mutable wire data and exclude only its signature from the preimage."""
    if type(designation) is not dict:
        _invalid()
    return _signing_input(validate_reviewer_designation(designation, _parent=designation.get("schema_version") == PARENT_DESIGNATION_SCHEMA))


__all__ = [
    "validate_reviewer_designation_authority", "validate_reviewer_designation",
    "reviewer_designation_authority_digest", "reviewer_designation_signing_input",
]


def validate_parent_reviewer_designation_authority(value):
    copied = _common(value, _AUTHORITY_FIELDS, PARENT_AUTHORITY_SCHEMA, PARENT_PRIVILEGE, PARENT_DECISION_SCHEMA)
    if not _text(copied["issuer_public_key"]) or decode_ed25519_public_key(copied["issuer_public_key"]) is None:
        _invalid()
    return copied


def validate_reviewer_designations(values, *, dual=False):
    if type(values) is not list or not 1 <= len(values) <= (2 if dual else 1):
        _invalid()
    checked = tuple(validate_reviewer_designation(value, _parent=dual and type(value) is dict
        and value.get("schema_version") == PARENT_DESIGNATION_SCHEMA) for value in values)
    if len({value["privilege"] for value in checked}) != len(checked):
        _invalid()
    return checked


def select_reviewer_designation(values, privilege):
    if privilege not in {PRIVILEGE, PARENT_PRIVILEGE}:
        _invalid()
    checked = validate_reviewer_designations(list(values), dual=True)
    matches = [value for value in checked if value["privilege"] == privilege]
    if len(matches) != 1:
        _invalid()
    return matches[0]
