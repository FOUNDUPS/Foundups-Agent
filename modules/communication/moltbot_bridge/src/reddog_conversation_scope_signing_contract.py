"""Canonical contract for E0 conversation-scope state signatures."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    IsolatedSignerClient,
    SigningRequest,
)


SCHEMA_VERSION = "reddog_conversation_scope_state_attestation.v1"
SIGNING_OPERATION = "attest_conversation_scope_state"
RECOVERY_SIGNING_OPERATION = "recover_conversation_scope_state"
SIGNING_OPERATIONS = frozenset({SIGNING_OPERATION, RECOVERY_SIGNING_OPERATION})
SIGNING_PREFIX = "reddog-conversation-scope-state.v2."
AUTH_SCHEME = "ed25519-e0-v1"
MAX_SIGNING_INPUT_BYTES = 65536
MIN_SOCKET_REQUEST_BYTES = (2 * MAX_SIGNING_INPUT_BYTES) + 32768
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
AUTH_RESPONSE_FIELDS = frozenset(
    {
        "record_auth_signature",
        "record_auth_signer_public_key",
        "record_auth_key_fingerprint",
        "record_auth_key_epoch",
        "record_auth_audit_mac",
        "record_auth_audit_attestation_signature",
    }
)


@dataclass(frozen=True)
class ConversationScopeSignerPolicy:
    issuer_principal_id: str
    issuer_principal_provider: str
    repo_full_name: str
    signer_public_key: str
    key_epoch: str
    max_scope_ttl_seconds: int = 86400


@dataclass(frozen=True)
class ConversationScopeSigningContext:
    signer: IsolatedSignerClient
    signer_public_key: str
    key_epoch: str
    serialized_session_credential: str = field(repr=False)


def unsigned_conversation_scope_record(record: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(record)
    value.pop("record_digest", None)
    for name in AUTH_RESPONSE_FIELDS:
        value.pop(name, None)
    return value


def canonical_conversation_scope_signing_input(
    record: Mapping[str, Any], serialized_credential: str
) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "record": unsigned_conversation_scope_record(record),
        "serialized_session_credential": serialized_credential,
    }
    return SIGNING_PREFIX + json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )


def build_conversation_scope_signing_request(
    context: ConversationScopeSigningContext,
    record: Mapping[str, Any],
    *,
    require_replay: bool = False,
) -> SigningRequest | None:
    try:
        signing_input = canonical_conversation_scope_signing_input(
            record, context.serialized_session_credential
        )
        if len(signing_input.encode("ascii")) > MAX_SIGNING_INPUT_BYTES:
            return None
        return SigningRequest(
            signing_input=signing_input,
            payload_digest=signing_input_digest(signing_input),
            signer_role="reddog",
            signer_public_key=context.signer_public_key,
            requester_principal_id=str(record["principal_id"]),
            nonce=str(record["record_auth_nonce"]),
            key_epoch=context.key_epoch,
            requested_operation=(
                RECOVERY_SIGNING_OPERATION if require_replay else SIGNING_OPERATION
            ),
            authority_tier="NONE",
            consensus_receipt_digest=None,
        )
    except (KeyError, TypeError, UnicodeError, ValueError):
        return None


def decode_conversation_scope_signing_input(
    value: str,
) -> tuple[Mapping[str, Any], str] | None:
    if not isinstance(value, str) or not value.startswith(SIGNING_PREFIX):
        return None
    if not value.isascii() or len(value.encode("ascii")) > MAX_SIGNING_INPUT_BYTES:
        return None
    try:
        payload = json.loads(
            value[len(SIGNING_PREFIX) :], object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, TypeError, UnicodeError, ValueError):
        return None
    if not isinstance(payload, Mapping) or set(payload) != {
        "schema_version", "record", "serialized_session_credential"
    }:
        return None
    record = payload.get("record")
    serialized = payload.get("serialized_session_credential")
    if payload.get("schema_version") != SCHEMA_VERSION or not isinstance(
        record, Mapping
    ) or not isinstance(serialized, str):
        return None
    return dict(record), serialized


def signing_input_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("ascii")).hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("conversation_scope_signing_duplicate_field")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"conversation_scope_signing_non_finite:{value}")


__all__ = [
    "AUTH_RESPONSE_FIELDS", "AUTH_SCHEME", "MAX_SIGNING_INPUT_BYTES",
    "MIN_SOCKET_REQUEST_BYTES",
    "RECOVERY_SIGNING_OPERATION", "SCHEMA_VERSION", "SHA256_RE",
    "SIGNING_OPERATION", "SIGNING_OPERATIONS", "SIGNING_PREFIX",
    "ConversationScopeSignerPolicy", "ConversationScopeSigningContext",
    "build_conversation_scope_signing_request",
    "canonical_conversation_scope_signing_input",
    "decode_conversation_scope_signing_input", "signing_input_digest",
    "unsigned_conversation_scope_record",
]
