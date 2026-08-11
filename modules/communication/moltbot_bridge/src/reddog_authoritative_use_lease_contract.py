"""Canonical external-signer request for one exact RedDog runtime effect."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)


AUTHORITATIVE_USE_LEASE_SCHEMA_VERSION = "reddog_authoritative_use_lease.v1"
AUTHORITATIVE_USE_LEASE_SIGNING_OPERATION = "issue_authoritative_use_lease"
AUTHORITATIVE_USE_LEASE_SIGNING_PREFIX = "reddog-authoritative-use-lease.v1."
AUTHORITATIVE_USE_LEASE_SIGNER_ROLE = "signer:authoritative-use-lease"
MAX_AUTHORITATIVE_USE_LEASE_TTL_SECONDS = 30
MAX_AUTHORITATIVE_USE_LEASE_CLOCK_SKEW_SECONDS = 5
SUPPORTED_EFFECT_KINDS = frozenset({"live_enqueue", "worktree_create"})
SUPPORTED_AUTHORITY_TIERS = frozenset({"HIGH", "ULTRA"})

_NONCE_RE = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_FIELDS = frozenset(
    {
        "schema_version",
        "lease_nonce",
        "effect_kind",
        "effect_request_digest",
        "requester_principal_id",
        "signer_profile_id",
        "signer_public_key",
        "key_epoch",
        "manifest_id",
        "artifact_generation_digest",
        "generation",
        "generation_revision",
        "owner_config_id",
        "run_packet_id",
        "config_digest",
        "session_id",
        "socket_path_digest",
        "current_generation_receipt_id",
        "lifecycle_admission_receipt_id",
        "work_authority_digest",
        "identity_digest",
        "work_order_id",
        "work_order_digest",
        "queue_item_id",
        "selected_slice",
        "expected_bindings_digest",
        "issued_at",
        "expires_at",
    }
)
_DIGEST_FIELDS = frozenset(
    {
        "effect_request_digest",
        "manifest_id",
        "artifact_generation_digest",
        "owner_config_id",
        "run_packet_id",
        "config_digest",
        "socket_path_digest",
        "current_generation_receipt_id",
        "lifecycle_admission_receipt_id",
        "work_authority_digest",
        "identity_digest",
        "work_order_digest",
        "expected_bindings_digest",
    }
)


def build_authoritative_use_lease_request(
    payload: Mapping[str, Any], *, authority_tier: str
) -> SigningRequest:
    """Build one strict, domain-separated request for the external signer."""

    checked = validate_authoritative_use_lease_payload(payload)
    if checked is None or authority_tier not in SUPPORTED_AUTHORITY_TIERS:
        raise ValueError("authoritative_use_lease_request_invalid")
    signing_input = AUTHORITATIVE_USE_LEASE_SIGNING_PREFIX + canonical_payload(checked)
    return SigningRequest(
        signing_input=signing_input,
        payload_digest=digest_mapping(checked),
        signer_role=AUTHORITATIVE_USE_LEASE_SIGNER_ROLE,
        signer_public_key=str(checked["signer_public_key"]),
        requester_principal_id=str(checked["requester_principal_id"]),
        nonce="authoritative-use-lease:" + str(checked["lease_nonce"]),
        key_epoch=str(checked["key_epoch"]),
        requested_operation=AUTHORITATIVE_USE_LEASE_SIGNING_OPERATION,
        authority_tier=authority_tier,
        consensus_receipt_digest=None,
    )


def validate_authoritative_use_lease_request(
    request: object, *, now_epoch: int
) -> dict[str, Any] | None:
    """Return the exact payload only for a fresh canonical request."""

    if type(request) is not SigningRequest or type(now_epoch) is not int:
        return None
    prefix = AUTHORITATIVE_USE_LEASE_SIGNING_PREFIX
    if not request.signing_input.startswith(prefix):
        return None
    try:
        payload = json.loads(request.signing_input[len(prefix) :])
    except (TypeError, json.JSONDecodeError):
        return None
    checked = validate_authoritative_use_lease_payload(payload)
    if checked is None or not _request_matches(request, checked):
        return None
    return checked if _fresh(checked, now_epoch) else None


def validate_authoritative_use_lease_payload(
    payload: object,
) -> dict[str, Any] | None:
    """Validate exact shape, types, bindings, and canonical digest fields."""

    if not isinstance(payload, Mapping) or set(payload) != _FIELDS:
        return None
    if payload.get("schema_version") != AUTHORITATIVE_USE_LEASE_SCHEMA_VERSION:
        return None
    if type(payload.get("generation")) is not int or payload["generation"] < 1:
        return None
    if (
        type(payload.get("issued_at")) is not int
        or type(payload.get("expires_at")) is not int
    ):
        return None
    if payload.get("effect_kind") not in SUPPORTED_EFFECT_KINDS:
        return None
    if not _NONCE_RE.fullmatch(str(payload.get("lease_nonce") or "")):
        return None
    if any(not is_sha256(payload.get(field)) for field in _DIGEST_FIELDS):
        return None
    text_fields = _FIELDS - _DIGEST_FIELDS - {"generation", "issued_at", "expires_at"}
    if any(not _ascii(payload.get(field)) for field in text_fields):
        return None
    checked = dict(payload)
    return checked if _canonical_round_trip(checked) else None


def canonical_payload(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def digest_mapping(payload: Mapping[str, Any]) -> str:
    return digest_text(canonical_payload(payload))


def authoritative_use_effect_digest(
    effect_kind: str, effect_payload: Mapping[str, Any]
) -> str:
    """Bind one supported effect kind to its complete canonical input."""

    if effect_kind not in SUPPORTED_EFFECT_KINDS or not isinstance(
        effect_payload, Mapping
    ):
        raise ValueError("authoritative_use_effect_invalid")
    if not _ascii_deep(effect_payload):
        raise ValueError("authoritative_use_effect_non_ascii")
    return digest_mapping(
        {"effect_kind": effect_kind, "effect_payload": dict(effect_payload)}
    )


def digest_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def is_sha256(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 71
        and value.startswith("sha256:")
        and value[7:] != "0" * 64
        and all(char in "0123456789abcdef" for char in value[7:])
    )


def _request_matches(request: SigningRequest, payload: Mapping[str, Any]) -> bool:
    return all(
        (
            request.requested_operation == AUTHORITATIVE_USE_LEASE_SIGNING_OPERATION,
            request.signer_role == AUTHORITATIVE_USE_LEASE_SIGNER_ROLE,
            request.signer_public_key == payload["signer_public_key"],
            request.key_epoch == payload["key_epoch"],
            request.requester_principal_id == payload["requester_principal_id"],
            request.nonce == "authoritative-use-lease:" + str(payload["lease_nonce"]),
            request.payload_digest == digest_mapping(payload),
            request.consensus_receipt_digest is None,
            request.authority_tier in SUPPORTED_AUTHORITY_TIERS,
        )
    )


def _fresh(payload: Mapping[str, Any], now_epoch: int) -> bool:
    issued = int(payload["issued_at"])
    expires = int(payload["expires_at"])
    ttl = expires - issued
    return bool(
        0 < ttl <= MAX_AUTHORITATIVE_USE_LEASE_TTL_SECONDS
        and issued <= now_epoch + MAX_AUTHORITATIVE_USE_LEASE_CLOCK_SKEW_SECONDS
        and now_epoch < expires
    )


def _canonical_round_trip(payload: Mapping[str, Any]) -> bool:
    try:
        return json.loads(canonical_payload(payload)) == dict(payload)
    except (TypeError, ValueError):
        return False


def _ascii(value: object) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= 512
        and all(ord(char) < 128 for char in value)
    )


def _ascii_deep(value: object) -> bool:
    if isinstance(value, str):
        return len(value) <= 4096 and all(ord(char) < 128 for char in value)
    if isinstance(value, Mapping):
        return all(_ascii(key) and _ascii_deep(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_ascii_deep(item) for item in value)
    return value is None or type(value) in {bool, int}


__all__ = [
    "AUTHORITATIVE_USE_LEASE_SCHEMA_VERSION",
    "AUTHORITATIVE_USE_LEASE_SIGNER_ROLE",
    "AUTHORITATIVE_USE_LEASE_SIGNING_OPERATION",
    "AUTHORITATIVE_USE_LEASE_SIGNING_PREFIX",
    "MAX_AUTHORITATIVE_USE_LEASE_TTL_SECONDS",
    "SUPPORTED_AUTHORITY_TIERS",
    "SUPPORTED_EFFECT_KINDS",
    "authoritative_use_effect_digest",
    "build_authoritative_use_lease_request",
    "canonical_payload",
    "digest_mapping",
    "digest_text",
    "is_sha256",
    "validate_authoritative_use_lease_payload",
    "validate_authoritative_use_lease_request",
]
