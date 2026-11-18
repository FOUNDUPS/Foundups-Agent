"""Canonical receipt helpers for signed-worker quarantine state."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


QUARANTINE_SCHEMA = "reddog_signed_worker_execution_quarantine.v1"


def build_quarantine_receipt(
    *,
    task_id: str,
    reason: str,
    now_iso: str,
) -> dict[str, Any]:
    """Build the task-local receipt for one atomic quarantine effect."""

    receipt = {
        "schema_version": QUARANTINE_SCHEMA,
        "task_id": task_id,
        "reason": reason,
        "quarantined_at": now_iso,
        "effect_commit_state": "INDETERMINATE",
        "no_worker_effect_replayed": True,
    }
    receipt["receipt_id"] = _digest(receipt)
    return receipt


def quarantine_receipt_matches(row: Any, *, task_id: str) -> bool:
    """Validate the local marker before independent-state reconciliation."""

    if row is None or dict(row).get("status") != "quarantined":
        return False
    receipt = decoded_context(dict(row).get("context")).get(
        "signed_worker_execution_quarantine"
    )
    return bool(
        isinstance(receipt, Mapping)
        and receipt.get("schema_version") == QUARANTINE_SCHEMA
        and receipt.get("task_id") == task_id
        and receipt.get("effect_commit_state") == "INDETERMINATE"
        and receipt.get("no_worker_effect_replayed") is True
        and _digest_without_receipt(receipt) == receipt.get("receipt_id")
    )


def decoded_context(raw_context: Any) -> dict[str, Any]:
    """Return a copied JSON object or an empty fail-closed context."""

    try:
        parsed = json.loads(str(raw_context or ""))
    except (TypeError, ValueError):
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


def _digest_without_receipt(receipt: Mapping[str, Any]) -> str:
    return _digest(
        {key: value for key, value in receipt.items() if key != "receipt_id"}
    )


def _digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


__all__ = [
    "QUARANTINE_SCHEMA",
    "build_quarantine_receipt",
    "decoded_context",
    "quarantine_receipt_matches",
]
