"""Principal-signed, one-use disclosure for resident Principal Memex context."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AuthorityRuntimeStore,
    PrincipalAuthorityRecord,
    PrincipalAuthorityResolver,
    principal_memex_disclosure_revoked,
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


SCHEMA_VERSION = "reddog_principal_memex_disclosure.v2"
SIGNING_PREFIX = "reddog-principal-memex-disclosure.v2"
AUDIENCE = "foundups.reddog"
PURPOSE = "resident_architect_context"
RUNTIME_SURFACE = "reddog_backend_architect"
MAX_TTL_SECONDS = 300
MAX_ITEMS = 32
MAX_BYTES = 12_288
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RUNTIME_RECEIPT_RE = re.compile(
    r"^reddog_model_runtime_binding:[0-9a-f]{64}$"
)
_FIELDS = frozenset(
    {
        "schema_version", "disclosure_id", "principal_id", "principal_provider",
        "audience", "repo_full_name", "transport", "credential_id", "session_id",
        "conversation_id", "conversation_revision", "conversation_record_digest",
        "decision_item_ids", "sensitivity", "purpose", "runtime_surface",
        "model_runtime_binding_receipt_id", "model_runtime_binding_digest",
        "intent_id", "grounding_receipt_id", "session_binding_digest",
        "nonce", "issued_at", "expires_at", "signature",
    }
)
_ID_FIELDS = _FIELDS - {"disclosure_id", "signature"}


class PrincipalMemexDisclosureGuard(Protocol):
    def is_revoked(self, disclosure: "VerifiedPrincipalMemexDisclosure") -> bool: ...
    def admit_once(self, disclosure: "VerifiedPrincipalMemexDisclosure") -> bool: ...


@dataclass(frozen=True)
class VerifiedPrincipalMemexDisclosure:
    disclosure_id: str
    principal_id: str
    principal_provider: str
    repo_full_name: str
    transport: str
    credential_id: str
    session_id: str
    conversation_id: str
    conversation_revision: int
    conversation_record_digest: str
    decision_item_ids: tuple[str, ...]
    model_runtime_binding_receipt_id: str
    model_runtime_binding_digest: str
    intent_id: str
    grounding_receipt_id: str
    session_binding_digest: str
    nonce: str
    issued_at: int
    expires_at: int


class AuthorityRuntimePrincipalMemexDisclosureGuard:
    """Use the existing root-owned authority state for revocation and replay."""

    def __init__(self, store: AuthorityRuntimeStore) -> None:
        self._store = store

    def is_revoked(self, disclosure: VerifiedPrincipalMemexDisclosure) -> bool:
        try:
            state = self._store.load()
        except Exception:
            return True
        return principal_memex_disclosure_revoked(
            state,
            disclosure.principal_id,
            disclosure.credential_id,
            disclosure.session_id,
            disclosure.disclosure_id,
        )

    def admit_once(self, disclosure: VerifiedPrincipalMemexDisclosure) -> bool:
        try:
            return self._store.admit_principal_memex_disclosure(
                disclosure.nonce,
                disclosure.principal_id,
                disclosure.credential_id,
                disclosure.session_id,
                disclosure.disclosure_id,
            ) is True
        except Exception:
            return False


def verify_principal_memex_disclosure(
    serialized: str,
    *,
    principal_resolver: PrincipalAuthorityResolver,
    expected_repo_full_name: str,
    expected_transport: str,
    expected_model_runtime_binding_receipt_id: str,
    expected_model_runtime_binding_digest: str,
    expected_intent_id: str,
    expected_grounding_receipt_id: str,
    expected_session_binding_digest: str,
    now_epoch: int,
) -> VerifiedPrincipalMemexDisclosure | None:
    raw = _parse(serialized)
    if raw is None or not _shape_valid(raw, int(now_epoch)):
        return None
    expected = (
        ("audience", AUDIENCE),
        ("repo_full_name", expected_repo_full_name),
        ("transport", expected_transport),
        ("runtime_surface", RUNTIME_SURFACE),
        ("purpose", PURPOSE),
        ("model_runtime_binding_receipt_id", expected_model_runtime_binding_receipt_id),
        ("model_runtime_binding_digest", expected_model_runtime_binding_digest),
        ("intent_id", expected_intent_id),
        ("grounding_receipt_id", expected_grounding_receipt_id),
        ("session_binding_digest", expected_session_binding_digest),
    )
    if any(not constant_time_compare(str(raw[field]), str(value)) for field, value in expected):
        return None
    record = _principal_record(raw, principal_resolver)
    if record is None or not constant_time_compare(str(raw["disclosure_id"]), disclosure_id(raw)):
        return None
    try:
        signature_ok = Ed25519SignatureVerifier().verify(
            record.principal_public_key,
            canonical_principal_memex_disclosure_signing_input(raw),
            str(raw["signature"]),
        ) is True
    except Exception:
        signature_ok = False
    return _verified(raw) if signature_ok else None


def disclosure_id(value: Mapping[str, Any]) -> str:
    return canonical_digest({field: value.get(field) for field in sorted(_ID_FIELDS)})


def canonical_principal_memex_disclosure_signing_input(value: Mapping[str, Any]) -> str:
    payload = {field: value.get(field) for field in sorted(_FIELDS - {"signature"})}
    return SIGNING_PREFIX + "." + json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _parse(serialized: str) -> Mapping[str, Any] | None:
    if type(serialized) is not str or not serialized or not serialized.isascii():
        return None
    if len(serialized.encode("ascii")) > MAX_BYTES:
        return None
    try:
        value = json.loads(serialized, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, UnicodeError, ValueError):
        return None
    return value if type(value) is dict and set(value) == _FIELDS else None


def _shape_valid(value: Mapping[str, Any], now_epoch: int) -> bool:
    sha256_ids = (
        "disclosure_id", "credential_id", "session_id", "conversation_id",
        "conversation_record_digest", "model_runtime_binding_digest", "nonce",
        "intent_id", "grounding_receipt_id", "session_binding_digest",
    )
    text = ("principal_id", "principal_provider", "repo_full_name", "transport", "signature")
    items = value.get("decision_item_ids")
    issued, expires, revision = value.get("issued_at"), value.get("expires_at"), value.get("conversation_revision")
    return bool(
        value.get("schema_version") == SCHEMA_VERSION
        and value.get("audience") == AUDIENCE
        and value.get("purpose") == PURPOSE
        and value.get("runtime_surface") == RUNTIME_SURFACE
        and value.get("sensitivity") == "public"
        and all(
            _SHA256_RE.fullmatch(str(value.get(field) or ""))
            for field in sha256_ids
        )
        and _RUNTIME_RECEIPT_RE.fullmatch(
            str(value.get("model_runtime_binding_receipt_id") or "")
        )
        and all(_text(value.get(field)) for field in text)
        and type(items) is list and 0 < len(items) <= MAX_ITEMS
        and all(type(item) is str and _SHA256_RE.fullmatch(item) for item in items)
        and len(items) == len(set(items))
        and type(revision) is int and revision >= 0
        and type(issued) is int and type(expires) is int
        and issued <= now_epoch < expires and 0 < expires - issued <= MAX_TTL_SECONDS
    )


def _principal_record(
    value: Mapping[str, Any], resolver: PrincipalAuthorityResolver,
) -> PrincipalAuthorityRecord | None:
    try:
        record = resolver.resolve(str(value["principal_id"]), str(value["principal_provider"]))
    except Exception:
        return None
    if type(record) is not PrincipalAuthorityRecord or not all(
        (
            constant_time_compare(record.principal_id, str(value["principal_id"])),
            constant_time_compare(
                record.principal_provider, str(value["principal_provider"])
            ),
            bool(record.principal_public_key),
            bool(record.verified_subject_digest),
        )
    ):
        return None
    return record if str(value["repo_full_name"]) in set(record.repo_scope) else None


def _verified(value: Mapping[str, Any]) -> VerifiedPrincipalMemexDisclosure:
    return VerifiedPrincipalMemexDisclosure(
        disclosure_id=str(value["disclosure_id"]), principal_id=str(value["principal_id"]),
        principal_provider=str(value["principal_provider"]), repo_full_name=str(value["repo_full_name"]),
        transport=str(value["transport"]), credential_id=str(value["credential_id"]),
        session_id=str(value["session_id"]), conversation_id=str(value["conversation_id"]),
        conversation_revision=int(value["conversation_revision"]),
        conversation_record_digest=str(value["conversation_record_digest"]),
        decision_item_ids=tuple(value["decision_item_ids"]),
        model_runtime_binding_receipt_id=str(value["model_runtime_binding_receipt_id"]),
        model_runtime_binding_digest=str(value["model_runtime_binding_digest"]),
        intent_id=str(value["intent_id"]),
        grounding_receipt_id=str(value["grounding_receipt_id"]),
        session_binding_digest=str(value["session_binding_digest"]),
        nonce=str(value["nonce"]),
        issued_at=int(value["issued_at"]), expires_at=int(value["expires_at"]),
    )


def _text(value: Any) -> bool:
    return bool(type(value) is str and value.strip() and value.isascii() and len(value) <= 1024)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("principal_memex_disclosure_duplicate_field")
        value[key] = item
    return value


__all__ = [
    "AUDIENCE", "PURPOSE", "RUNTIME_SURFACE", "SCHEMA_VERSION",
    "AuthorityRuntimePrincipalMemexDisclosureGuard", "PrincipalMemexDisclosureGuard",
    "VerifiedPrincipalMemexDisclosure", "canonical_principal_memex_disclosure_signing_input",
    "disclosure_id", "verify_principal_memex_disclosure",
]
