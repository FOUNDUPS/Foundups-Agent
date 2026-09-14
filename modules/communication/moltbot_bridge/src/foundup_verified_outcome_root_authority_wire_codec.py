"""Strict bounded canonical JSON codec for root authority protocols."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

MAX_MESSAGE_BYTES = 64 * 1024
PENDING_RESPONSE_SCHEMA = "foundup_verified_outcome_pending_responses.v1"
MAX_PENDING_RESPONSE_RECORDS = 8
MAX_PENDING_RESPONSE_STORE_BYTES = 512 * 1024


def canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def encode_message(value: Mapping[str, Any]) -> bytes:
    raw = canonical_bytes(value) + b"\n"
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ValueError("root_authority_message_too_large")
    return raw


def decode_message(value: bytes) -> dict[str, Any]:
    if not isinstance(value, bytes) or not value or len(value) > MAX_MESSAGE_BYTES:
        raise ValueError("root_authority_message_invalid")
    try:
        data = json.loads(
            value.decode("ascii").strip(), object_pairs_hook=_strict_object
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("root_authority_message_invalid") from exc
    if not isinstance(data, dict):
        raise ValueError("root_authority_message_invalid")
    return data


def digest_mapping(value: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def pending_response_records(snapshot: Mapping[str, Any]) -> dict[str, str]:
    if not snapshot:
        return {}
    if (set(snapshot) != {"schema_version", "records", "revision"}
        or snapshot["schema_version"] != PENDING_RESPONSE_SCHEMA
        or type(snapshot["records"]) is not dict):
        raise ValueError("root_pending_response_snapshot_invalid")
    checked = pending_response_snapshot(snapshot["records"])
    if snapshot["revision"] != checked["revision"]:
        raise ValueError("root_pending_response_snapshot_revision_invalid")
    return dict(snapshot["records"])


def pending_response_snapshot(records: Mapping[str, str]) -> dict[str, Any]:
    if len(records) > MAX_PENDING_RESPONSE_RECORDS:
        raise ValueError("root_pending_response_capacity_exceeded")
    if any(type(key) is not str or not key.startswith("verified-outcome-authorization-")
           or type(raw) is not str or not raw.isascii() or not raw or len(raw) > MAX_MESSAGE_BYTES
           for key, raw in records.items()):
        raise ValueError("root_pending_response_record_invalid")
    snapshot = {"schema_version": PENDING_RESPONSE_SCHEMA, "records": dict(records)}
    snapshot["revision"] = digest_mapping(snapshot)[7:]
    if len((json.dumps(snapshot, sort_keys=True, indent=2) + "\n").encode("utf-8")) > MAX_PENDING_RESPONSE_STORE_BYTES:
        raise ValueError("root_pending_response_store_too_large")
    return snapshot


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("root_authority_message_duplicate_key")
        result[key] = value
    return result


__all__ = [
    "MAX_MESSAGE_BYTES", "canonical_bytes", "decode_message",
    "digest_mapping", "encode_message",
    "PENDING_RESPONSE_SCHEMA", "MAX_PENDING_RESPONSE_RECORDS",
    "MAX_PENDING_RESPONSE_STORE_BYTES", "pending_response_records", "pending_response_snapshot",
]
