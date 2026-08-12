"""Strict bounded canonical JSON codec for root authority protocols."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

MAX_MESSAGE_BYTES = 64 * 1024


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
]
