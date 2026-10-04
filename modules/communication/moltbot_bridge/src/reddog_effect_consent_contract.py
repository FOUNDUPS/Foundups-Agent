"""Bounded detached effect-consent data; validation alone grants no authority."""

from .reddog_ed25519_signature_verifier_backend import (
    decode_ed25519_public_key, decode_ed25519_signature,
)
from .reddog_elevated_authority_consensus_rehydration import MAX_CONSENSUS_RECEIPT_BYTES
from .reddog_runtime_artifact_manifest_contract import canonical_json, is_sha256, raw_digest

AUTHORITY_SCHEMA = "reddog_effect_consent_authority.v1"
ASSERTION_SCHEMA = "reddog_effect_consent.v1"
PRIVILEGE = "authorize_exact_high_worktree_effect"
SIGNING_PREFIX = "reddog-effect-consent.v1."
_COMMON = frozenset({
    "schema_version", "privilege", "issuer_principal_id", "issuer_principal_provider",
    "issuer_key_epoch", "repo_full_name", "foundup_id", "policy_digest",
    "authority_tier", "effect_kind", "requester_principal_id", "requester_principal_provider",
    "beneficiary_principal_id", "beneficiary_principal_provider", "reddog_id",
    "target_signer_profile_id", "target_signer_public_key", "target_signer_key_epoch",
    "issued_at", "expires_at",
})
_BINDINGS = frozenset({"owner_authority_digest", "parent_authority_request_digest",
                       "target_signing_request_digest", "effect_request_digest"})
_BODY = _COMMON | _BINDINGS | {"parent_authorization"}
_PARENT = frozenset({
    "authorization_digest", "authority_request_digest", "principal_id", "principal_provider",
    "principal_public_key", "reddog_id", "reddog_public_key", "repo_full_name", "foundup_id",
    "work_order_id", "key_epoch", "expires_at",
})


def _invalid():
    raise ValueError("effect_consent_invalid")


def _shape(value, fields):
    if type(value) is not dict or len(value) != len(fields):
        _invalid()
    if any(type(key) is not str for key in value) or set(value) != fields:
        _invalid()
    return dict(value)


def _text(value):
    return type(value) is str and 1 <= len(value) <= 256 and value.isascii() and bool(value.strip())


def _time(value):
    return type(value) is int and 0 <= value <= 2**63 - 1


def _fields(value, *, times, digests, keys):
    for name, item in value.items():
        if name in times:
            if not _time(item):
                _invalid()
        elif not _text(item):
            _invalid()
        elif name in digests and not is_sha256(item):
            _invalid()
        elif name in keys and decode_ed25519_public_key(item) is None:
            _invalid()


def _common(value, fields, schema):
    copied = _shape(value, fields)
    _fields({key: copied[key] for key in _COMMON}, times={"issued_at", "expires_at"},
            digests={"policy_digest"}, keys={"target_signer_public_key"})
    if (copied["schema_version"] != schema or copied["privilege"] != PRIVILEGE
            or copied["authority_tier"] != "HIGH" or copied["effect_kind"] != "worktree_create"
            or copied["issued_at"] >= copied["expires_at"]):
        _invalid()
    return copied


def validate_effect_consent_authority(value):
    """Copy exact static registration; its authenticated owner is a separate gate."""
    copied = _common(value, _COMMON | {"issuer_public_key"}, AUTHORITY_SCHEMA)
    if not _text(copied["issuer_public_key"]) or decode_ed25519_public_key(copied["issuer_public_key"]) is None:
        _invalid()
    return copied


def _body(value):
    copied = _common(value, _BODY, ASSERTION_SCHEMA)
    _fields({key: copied[key] for key in _BINDINGS}, times=set(), digests=_BINDINGS, keys=set())
    parent = _shape(copied["parent_authorization"], _PARENT)
    _fields(parent, times={"expires_at"}, digests={"authorization_digest", "authority_request_digest"},
            keys={"principal_public_key", "reddog_public_key"})
    copied["parent_authorization"] = parent
    return copied


def _bounded(encoded):
    if len(encoded.encode("ascii")) > MAX_CONSENSUS_RECEIPT_BYTES:
        _invalid()
    return encoded


def canonical_effect_consent_signing_input(body):
    """Encode the exact unsigned body, excluding neither context nor scope fields."""
    return _bounded(SIGNING_PREFIX + canonical_json(_body(body)))


def validate_effect_consent_assertion(value):
    """Copy signed-shaped data without treating a signature as verified."""
    copied = _shape(value, _BODY | {"signature"})
    signature = copied.pop("signature")
    if not _text(signature) or decode_ed25519_signature(signature) is None:
        _invalid()
    copied = _body(copied)
    _bounded(SIGNING_PREFIX + canonical_json(copied))
    copied["signature"] = signature
    _bounded(canonical_json(copied))
    return copied


def effect_consent_authority_digest(authority):
    """Commit the full validated registration, including its distinct privilege."""
    return raw_digest(canonical_json(validate_effect_consent_authority(authority)).encode("ascii"))
