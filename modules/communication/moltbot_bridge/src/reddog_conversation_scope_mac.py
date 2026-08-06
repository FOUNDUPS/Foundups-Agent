"""Derived MAC helpers for authenticated RedDog conversation records."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Mapping


def derive_conversation_scope_mac_key(
    secret: bytes, principal_provider: str, principal_id: str
) -> bytes:
    context = (
        f"reddog-conversation-scope-state.v1|{principal_provider}|{principal_id}"
    ).encode("utf-8")
    return hmac.new(secret, context, hashlib.sha256).digest()


def sign_conversation_scope_record(record: Mapping[str, Any], key: bytes) -> str:
    payload = dict(record)
    payload.pop("record_digest", None)
    for field in (
        "record_auth_signature", "record_auth_signer_public_key",
        "record_auth_key_fingerprint", "record_auth_key_epoch",
        "record_auth_audit_mac", "record_auth_audit_attestation_signature",
    ):
        payload.pop(field, None)
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return "hmac-sha256:" + hmac.new(key, raw, hashlib.sha256).hexdigest()


def verify_conversation_scope_record(
    record: Mapping[str, Any], keys: tuple[bytes, ...]
) -> bool:
    supplied = str(record.get("record_auth_signature") or "")
    return bool(keys) and any(
        hmac.compare_digest(supplied, sign_conversation_scope_record(record, key))
        for key in keys
    )


__all__ = [
    "derive_conversation_scope_mac_key",
    "sign_conversation_scope_record",
    "verify_conversation_scope_record",
]
