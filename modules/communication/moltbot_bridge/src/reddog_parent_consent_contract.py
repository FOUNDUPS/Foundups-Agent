"""Exact detached parent consent data; parsing does not authenticate authority."""

from dataclasses import dataclass

from .reddog_ed25519_signature_verifier_backend import (
    decode_ed25519_public_key, decode_ed25519_signature,
)
from .reddog_elevated_authority_consensus_rehydration import MAX_CONSENSUS_RECEIPT_BYTES
from .reddog_runtime_artifact_manifest_contract import canonical_json, is_sha256, raw_digest

AUTHORITY_SCHEMA = "reddog_parent_consent_authority.v1"
ASSERTION_SCHEMA = "reddog_parent_consent.v1"
PRIVILEGE = "authorize_exact_high_delegated_request"
SIGNING_PREFIX = "reddog-parent-consent.v1."
CURRENT_FIELDS = frozenset({"manifest_id", "artifact_generation_digest", "generation",
                            "generation_revision", "owner_config_id", "config_digest"})
COMMON_FIELDS = frozenset({
    "schema_version", "privilege", "issuer_principal_id", "issuer_principal_provider",
    "issuer_public_key", "issuer_key_epoch", "beneficiary_principal_id",
    "beneficiary_principal_provider", "beneficiary_public_key", "reddog_id",
    "reddog_public_key", "reddog_key_epoch", "repo_full_name", "foundup_id",
    "policy_digest", "authority_tier", "requested_operation", "issued_at", "expires_at",
})
ASSERTION_FIELDS = COMMON_FIELDS | CURRENT_FIELDS | {
    "owner_authority_digest", "authority_request_digest",
}
_TIMES = frozenset({"issued_at", "expires_at", "generation"})
_DIGESTS = frozenset({"policy_digest", "owner_authority_digest", "authority_request_digest",
                      "manifest_id", "artifact_generation_digest",
                      "owner_config_id", "config_digest"})
_KEYS = frozenset({"issuer_public_key", "beneficiary_public_key", "reddog_public_key"})


@dataclass(frozen=True, slots=True)
class ParentConsentEvidence:
    """Policy-bound data, deliberately not legacy SovereignAuthorizationEvidence.

    Current trusted composition remains required before any downstream use.
    This neither authenticates policy provenance nor reviewer/model execution.
    """
    authorization_digest: str
    authority_request_digest: str
    principal_id: str
    principal_provider: str
    principal_public_key: str
    reddog_id: str
    reddog_public_key: str
    repo_full_name: str
    foundup_id: str
    work_order_id: str
    key_epoch: str
    expires_at: int
    consensus_policy_digest: str


def _invalid():
    raise ValueError("parent_consent_invalid")


def _shape(value, fields):
    if type(value) is not dict or len(value) != len(fields):
        _invalid()
    if any(type(key) is not str for key in value) or set(value) != fields:
        _invalid()
    return dict(value)


def _text(value):
    return type(value) is str and 1 <= len(value) <= 256 and value.isascii() and bool(value.strip())


def _validate(value, fields, schema):
    copied = _shape(value, fields)
    for name, item in copied.items():
        if name in _TIMES:
            if type(item) is not int or not 0 <= item <= 2**63 - 1:
                _invalid()
        elif (not _text(item) or (name in _DIGESTS and not is_sha256(item))
              or (name in _KEYS and decode_ed25519_public_key(item) is None)):
            _invalid()
    if (copied["schema_version"] != schema or copied["privilege"] != PRIVILEGE
            or copied["authority_tier"] != "HIGH" or copied["requested_operation"] != "worktree_create"
            or copied["issued_at"] >= copied["expires_at"]):
        _invalid()
    if "generation_revision" in copied:
        revision = copied["generation_revision"]
        if len(revision) != 64 or any(char not in "0123456789abcdef" for char in revision):
            _invalid()
    return copied


def _bounded(encoded):
    if len(encoded.encode("ascii")) > MAX_CONSENSUS_RECEIPT_BYTES:
        _invalid()
    return encoded


def validate_parent_consent_authority(value):
    """Validate an opt-in registration; its root-owned provenance is separate."""
    return _validate(value, COMMON_FIELDS, AUTHORITY_SCHEMA)


def canonical_parent_consent_signing_input(body):
    """Sign every assertion field in a domain distinct from effect consent."""
    return _bounded(SIGNING_PREFIX + canonical_json(_validate(body, ASSERTION_FIELDS, ASSERTION_SCHEMA)))


def validate_parent_consent_assertion(value):
    copied = _shape(value, ASSERTION_FIELDS | {"signature"})
    signature = copied.pop("signature")
    if not _text(signature) or decode_ed25519_signature(signature) is None:
        _invalid()
    copied = _validate(copied, ASSERTION_FIELDS, ASSERTION_SCHEMA)
    canonical_parent_consent_signing_input(copied)
    copied["signature"] = signature
    _bounded(canonical_json(copied))
    return copied


def parent_consent_authority_digest(authority):
    return raw_digest(canonical_json(validate_parent_consent_authority(authority)).encode("ascii"))
