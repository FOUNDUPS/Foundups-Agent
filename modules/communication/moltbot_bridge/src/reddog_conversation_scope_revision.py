"""Revision-chain validation for authenticated RedDog conversation scope."""

from __future__ import annotations

import re
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_digest import (
    canonical_digest,
)


REVISION_RECEIPT_SCHEMA = "reddog_conversation_scope_revision.v1"
REVISION_RECEIPT_FIELDS = frozenset(
    {
        "schema_version", "conversation_id", "revision", "previous_receipt_id",
        "state_digest", "authority", "receipt_id",
    }
)
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def valid_revision_receipts(record: Mapping[str, Any]) -> bool:
    receipts = record.get("revision_receipts")
    revision_value = _integer(record.get("conversation_revision"), default=-1)
    if not isinstance(receipts, list) or len(receipts) != revision_value + 1:
        return False
    previous = ""
    for revision, raw in enumerate(receipts):
        if (
            not isinstance(raw, Mapping)
            or set(raw) != REVISION_RECEIPT_FIELDS
            or raw.get("schema_version") != REVISION_RECEIPT_SCHEMA
        ):
            return False
        receipt = dict(raw)
        receipt_id = str(receipt.pop("receipt_id", ""))
        if (
            receipt.get("conversation_id") != record.get("conversation_id")
            or receipt.get("revision") != revision
            or receipt.get("previous_receipt_id") != previous
            or receipt.get("authority") != "authenticated_scope_integrity_not_work_authority"
            or not SHA256_RE.fullmatch(str(receipt.get("state_digest") or ""))
            or receipt_id != canonical_digest(receipt)
        ):
            return False
        previous = receipt_id
    state = {
        key: value
        for key, value in record.items()
        if key not in {"revision_receipts", "record_auth_mac", "record_digest"}
    }
    return bool(receipts) and receipts[-1].get("state_digest") == canonical_digest(state)


def _integer(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


__all__ = [
    "REVISION_RECEIPT_FIELDS", "REVISION_RECEIPT_SCHEMA", "valid_revision_receipts",
]
