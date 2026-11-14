"""Verify principal-signed credentials for a RedDog conversation session.

The credential is a reusable, short-lived conversational identity bearer. It
does not grant work, repository, shell, signer, or merge authority. Verification
uses only the current-generation principal public key; no signing material is
available to the consumer process.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityRecord,
    PrincipalAuthorityResolver,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    constant_time_compare,
)


SCHEMA_VERSION = "reddog_conversation_session_credential.v1"
SIGNING_PREFIX = "reddog-conversation-session.v1"
AUDIENCE = "foundups.reddog"
MODE = "reusable_within_ttl"
MAX_CREDENTIAL_BYTES = 8192
MAX_TTL_SECONDS = 3600
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
FIELDS = frozenset(
    {
        "schema_version", "credential_id", "principal_id", "principal_provider",
        "audience", "repo_full_name", "foundup_scope", "transport", "session_id",
        "credential_mode", "issued_at", "expires_at", "signature",
    }
)
ID_FIELDS = FIELDS - {"credential_id", "signature"}


@dataclass(frozen=True)
class VerifiedConversationSessionCredential:
    credential_id: str
    principal_id: str
    principal_provider: str
    repo_full_name: str
    foundup_scope: tuple[str, ...]
    transport: str
    session_id: str
    issued_at: int
    expires_at: int
    signature: str
    principal_record: PrincipalAuthorityRecord


def verify_conversation_session_credential(
    serialized: str,
    *,
    principal_resolver: PrincipalAuthorityResolver,
    expected_repo_full_name: str,
    expected_transport: str,
    now_epoch: int,
) -> VerifiedConversationSessionCredential | None:
    """Strictly verify one reusable session credential or return ``None``."""

    raw = _parse(serialized)
    if raw is None or not _shape_valid(raw, now_epoch):
        return None
    if not (
        constant_time_compare(str(raw["audience"]), AUDIENCE)
        and constant_time_compare(str(raw["repo_full_name"]), expected_repo_full_name)
        and constant_time_compare(str(raw["transport"]), expected_transport)
    ):
        return None
    record = _resolve_record(raw, principal_resolver)
    if record is None or not _scope_valid(raw, record, expected_repo_full_name):
        return None
    if not constant_time_compare(str(raw["credential_id"]), credential_id(raw)):
        return None
    try:
        verified = Ed25519SignatureVerifier().verify(
            record.principal_public_key,
            canonical_conversation_session_signing_input(raw),
            str(raw["signature"]),
        ) is True
    except Exception:
        verified = False
    if not verified:
        return None
    return VerifiedConversationSessionCredential(
        credential_id=str(raw["credential_id"]),
        principal_id=str(raw["principal_id"]),
        principal_provider=str(raw["principal_provider"]),
        repo_full_name=str(raw["repo_full_name"]),
        foundup_scope=tuple(str(item) for item in raw["foundup_scope"]),
        transport=str(raw["transport"]),
        session_id=str(raw["session_id"]),
        issued_at=int(raw["issued_at"]),
        expires_at=int(raw["expires_at"]),
        signature=str(raw["signature"]),
        principal_record=record,
    )


def credential_id(value: Mapping[str, Any]) -> str:
    return canonical_digest({field: value.get(field) for field in sorted(ID_FIELDS)})


def canonical_conversation_session_signing_input(value: Mapping[str, Any]) -> str:
    payload = {field: value.get(field) for field in sorted(FIELDS - {"signature"})}
    return SIGNING_PREFIX + "." + json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _parse(serialized: str) -> Mapping[str, Any] | None:
    if not isinstance(serialized, str) or not serialized or not serialized.isascii():
        return None
    if len(serialized.encode("ascii")) > MAX_CREDENTIAL_BYTES:
        return None
    try:
        value = json.loads(serialized, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, UnicodeError, ValueError):
        return None
    return value if isinstance(value, Mapping) and set(value) == FIELDS else None


def _shape_valid(value: Mapping[str, Any], now_epoch: int) -> bool:
    strings = (
        value.get("principal_id"), value.get("principal_provider"), value.get("repo_full_name"),
        value.get("transport"), value.get("signature"),
    )
    scope = value.get("foundup_scope")
    issued, expires = value.get("issued_at"), value.get("expires_at")
    return bool(
        value.get("schema_version") == SCHEMA_VERSION
        and value.get("audience") == AUDIENCE
        and value.get("credential_mode") == MODE
        and SHA256_RE.fullmatch(str(value.get("credential_id") or ""))
        and SHA256_RE.fullmatch(str(value.get("session_id") or ""))
        and all(_text(item) for item in strings)
        and isinstance(scope, list) and scope and len(scope) <= 16
        and all(_text(item) for item in scope) and len(set(scope)) == len(scope)
        and type(issued) is int and type(expires) is int
        and issued <= int(now_epoch) < expires
        and 0 < expires - issued <= MAX_TTL_SECONDS
    )


def _resolve_record(
    value: Mapping[str, Any], resolver: PrincipalAuthorityResolver
) -> PrincipalAuthorityRecord | None:
    try:
        record = resolver.resolve(
            str(value["principal_id"]), str(value["principal_provider"])
        )
    except Exception:
        return None
    return record if type(record) is PrincipalAuthorityRecord else None


def _scope_valid(
    value: Mapping[str, Any], record: PrincipalAuthorityRecord, repo_full_name: str
) -> bool:
    credential_scope = set(map(str, value["foundup_scope"]))
    return bool(
        record.principal_id == value["principal_id"]
        and record.principal_provider == value["principal_provider"]
        and repo_full_name in set(record.repo_scope)
        and credential_scope.issubset(set(record.foundup_scope))
    )


def _text(value: Any) -> bool:
    return bool(isinstance(value, str) and value.strip() and value.isascii() and len(value) <= 1024)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("conversation_session_credential_duplicate_field")
        value[key] = item
    return value


__all__ = [
    "AUDIENCE", "FIELDS", "MAX_TTL_SECONDS", "MODE", "SCHEMA_VERSION",
    "SIGNING_PREFIX", "VerifiedConversationSessionCredential",
    "canonical_conversation_session_signing_input", "credential_id",
    "verify_conversation_session_credential",
]
