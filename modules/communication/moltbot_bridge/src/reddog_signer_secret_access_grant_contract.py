"""Canonical contract for signed E0 signer secret-access grants."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    ascii_deep,
)
from modules.communication.moltbot_bridge.src.reddog_signer_optional_authority_bindings import (
    is_sha256_digest,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PrincipalKeyResolver,
    canonical_signing_input,
    constant_time_compare,
)

GRANT_SCHEMA = "reddog-signer-secret-access-grant.v1"
GRANT_PREFIX = "reddog-signer-secret-access-grant.v1"
MAX_GRANT_TTL_SECONDS = 300

REJECT_MALFORMED = "REJECT_SECRET_GRANT_MALFORMED"
REJECT_NON_ASCII = "REJECT_SECRET_GRANT_NON_ASCII"
REJECT_DIGEST = "REJECT_SECRET_GRANT_DIGEST_INVALID"
REJECT_TIME = "REJECT_SECRET_GRANT_TIME_INVALID"
REJECT_ISSUER = "REJECT_SECRET_GRANT_ISSUER_UNTRUSTED"
REJECT_BINDING = "REJECT_SECRET_GRANT_BINDING_MISMATCH"
REJECT_GRANT_ID = "REJECT_SECRET_GRANT_ID_MISMATCH"
REJECT_SIGNATURE = "REJECT_SECRET_GRANT_SIGNATURE_INVALID"
REJECT_REVOKED = "REJECT_SECRET_GRANT_REVOKED"
REJECT_NONCE = "REJECT_SECRET_GRANT_NONCE_REPLAY"
REJECT_CAPABILITY = "REJECT_SECRET_GRANT_CAPABILITY_INVALID"

_STRING_FIELDS = (
    "schema_version", "issuer_principal_id", "issuer_principal_provider",
    "issuer_public_key", "signer_agent_id", "signer_profile_id",
    "signing_key_ref_hash", "audit_mac_key_ref_hash", "key_epoch",
    "permission_snapshot_digest", "owner_config_id", "signer_generation_id",
    "nonce", "grant_id", "signature",
)
_TIME_FIELDS = ("issued_at", "expires_at")
GRANT_FIELDS = frozenset(_STRING_FIELDS + _TIME_FIELDS)
_DIGEST_FIELDS = (
    "signing_key_ref_hash", "audit_mac_key_ref_hash",
    "permission_snapshot_digest", "owner_config_id", "signer_generation_id",
)


class SignerSecretAccessGrantRejected(Exception):
    """Fail-closed rejection carrying one static reason code."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True)
class ExpectedSignerSecretGrantBinding:
    issuer_principal_id: str
    issuer_principal_provider: str
    issuer_public_key: str
    signer_agent_id: str
    signer_profile_id: str
    signing_key_ref_hash: str
    audit_mac_key_ref_hash: str
    key_epoch: str
    permission_snapshot_digest: str
    owner_config_id: str
    signer_generation_id: str


def signer_secret_access_grant_id(grant: Mapping[str, Any]) -> str:
    core = {
        key: grant[key]
        for key in sorted(GRANT_FIELDS - {"grant_id", "signature"})
    }
    raw = json.dumps(
        core, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def canonical_signer_secret_access_grant_input(
    grant: Mapping[str, Any],
) -> str:
    return canonical_signing_input(grant, GRANT_PREFIX)


def validated_signer_secret_grant(
    grant: Mapping[str, Any], now: int
) -> dict[str, Any]:
    if not isinstance(grant, Mapping) or type(now) is not int:
        raise SignerSecretAccessGrantRejected(REJECT_MALFORMED)
    try:
        raw = dict(grant)
    except Exception:
        raise SignerSecretAccessGrantRejected(REJECT_MALFORMED) from None
    if frozenset(raw) != GRANT_FIELDS or raw.get("schema_version") != GRANT_SCHEMA:
        raise SignerSecretAccessGrantRejected(REJECT_MALFORMED)
    if any(not isinstance(raw.get(key), str) or not raw[key] for key in _STRING_FIELDS):
        raise SignerSecretAccessGrantRejected(REJECT_MALFORMED)
    if any(type(raw.get(key)) is not int for key in _TIME_FIELDS):
        raise SignerSecretAccessGrantRejected(REJECT_MALFORMED)
    if not ascii_deep(raw):
        raise SignerSecretAccessGrantRejected(REJECT_NON_ASCII)
    if any(len(raw[key]) > 4096 for key in _STRING_FIELDS) or len(raw["nonce"]) > 256:
        raise SignerSecretAccessGrantRejected(REJECT_MALFORMED)
    if any(not is_sha256_digest(raw[key]) for key in _DIGEST_FIELDS + ("grant_id",)):
        raise SignerSecretAccessGrantRejected(REJECT_DIGEST)
    issued, expires = int(raw["issued_at"]), int(raw["expires_at"])
    if (
        any(value < 0 for value in (now, issued, expires))
        or issued > now
        or expires <= now
        or not 0 < expires - issued <= MAX_GRANT_TTL_SECONDS
    ):
        raise SignerSecretAccessGrantRejected(REJECT_TIME)
    return raw


def verify_expected_signer_secret_grant(
    grant: Mapping[str, Any], expected: ExpectedSignerSecretGrantBinding
) -> None:
    if not isinstance(expected, ExpectedSignerSecretGrantBinding):
        raise SignerSecretAccessGrantRejected(REJECT_BINDING)
    values = {item.name: getattr(expected, item.name) for item in fields(expected)}
    if any(
        not isinstance(value, str) or not value or not ascii_deep(value)
        for value in values.values()
    ):
        raise SignerSecretAccessGrantRejected(REJECT_BINDING)
    for item in fields(expected):
        if not constant_time_compare(str(grant[item.name]), values[item.name]):
            raise SignerSecretAccessGrantRejected(REJECT_BINDING)


def verify_signer_secret_grant_issuer(
    grant: Mapping[str, Any], resolver: PrincipalKeyResolver
) -> None:
    try:
        trusted = resolver.resolve(
            str(grant["issuer_principal_id"]),
            str(grant["issuer_principal_provider"]),
        )
    except Exception:
        trusted = None
    if not isinstance(trusted, str) or not constant_time_compare(
        trusted, str(grant["issuer_public_key"])
    ):
        raise SignerSecretAccessGrantRejected(REJECT_ISSUER)
