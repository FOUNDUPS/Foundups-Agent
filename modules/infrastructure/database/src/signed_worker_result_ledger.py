"""Durable continuity validation for signed-worker execution results."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


RESULT_HISTORY_LIMIT = 10
_ENTRY_KEYS = {
    "claim_status",
    "receipt_id",
    "receipt_digest",
    "previous_history_digest",
    "history_entry_digest",
}


def validated_result_history(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return canonical result continuity or raise on malformed content."""

    last = context.get("signed_worker_task_last_result")
    history = context.get("signed_worker_task_result_receipts")
    if last is None and history is None:
        return {}
    if not isinstance(last, Mapping) or not isinstance(history, list):
        raise ValueError("signed_worker_result_history_malformed")
    if not 1 <= len(history) <= RESULT_HISTORY_LIMIT:
        raise ValueError("signed_worker_result_history_count_invalid")
    _validate_last_result(last)
    normalized = _normalize_entries(history)
    if any(
        normalized[-1][key] != str(last.get(key) or "")
        for key in ("claim_status", "receipt_id", "receipt_digest")
    ):
        raise ValueError("signed_worker_result_history_tail_mismatch")
    return {
        "signed_worker_task_last_result": dict(last),
        "signed_worker_task_result_receipts": normalized,
    }


def validate_result_history_ledger(
    connection: Any, task_id: str, context: Mapping[str, Any]
) -> bool:
    """Require mutable task context to match the independent AgentDB ledger."""

    try:
        history = _history_entries(validated_result_history(context))
    except ValueError:
        return False
    return history == _read_entries(connection, task_id)


def persist_result_history_ledger(
    connection: Any,
    task_id: str,
    context: Mapping[str, Any],
    *,
    claim_receipt_id: str,
    use_receipt_id: str,
) -> bool:
    """Validate unchanged history or append exactly one result atomically."""

    try:
        history = _history_entries(validated_result_history(context))
    except ValueError:
        return False
    stored = _read_entries(connection, task_id)
    if history == stored:
        return True
    if len(history) != len(stored) + 1 or history[:-1] != stored:
        return False
    entry = history[-1]
    changed = connection.execute(
        "INSERT INTO agents_signed_worker_result_history ("
        "task_id, attempt_sequence, claim_receipt_id, use_receipt_id, "
        "claim_status, result_receipt_id, result_receipt_digest, "
        "previous_history_digest, history_entry_digest"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            task_id,
            len(history),
            claim_receipt_id,
            use_receipt_id,
            entry["claim_status"],
            entry["receipt_id"],
            entry["receipt_digest"],
            entry["previous_history_digest"],
            entry["history_entry_digest"],
        ),
    ).rowcount
    return changed == 1


def _validate_last_result(last: Mapping[str, Any]) -> None:
    body = dict(last)
    supplied = str(body.pop("receipt_digest", "") or "")
    if not _is_digest(supplied) or supplied != _digest(body):
        raise ValueError("signed_worker_last_result_digest_mismatch")


def _normalize_entries(history: list[Any]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in history:
        if not isinstance(item, Mapping) or set(item) != _ENTRY_KEYS:
            raise ValueError("signed_worker_result_history_item_invalid")
        entry = {key: str(item.get(key) or "") for key in item}
        supplied = entry.pop("history_entry_digest")
        if (
            not entry["claim_status"]
            or not _is_digest(entry["receipt_digest"])
            or not _is_digest(entry["previous_history_digest"])
            or not _is_digest(supplied)
            or entry["previous_history_digest"] != _digest(normalized)
            or supplied != _digest(entry)
        ):
            raise ValueError("signed_worker_result_history_item_invalid")
        entry["history_entry_digest"] = supplied
        normalized.append(entry)
    return normalized


def _read_entries(connection: Any, task_id: str) -> list[dict[str, str]]:
    rows = connection.execute(
        "SELECT attempt_sequence, claim_status, result_receipt_id, "
        "result_receipt_digest, previous_history_digest, history_entry_digest "
        "FROM agents_signed_worker_result_history "
        "WHERE task_id = ? ORDER BY attempt_sequence",
        (task_id,),
    ).fetchall()
    entries: list[dict[str, str]] = []
    for expected, row in enumerate(rows, 1):
        payload = dict(row)
        if int(payload.get("attempt_sequence") or 0) != expected:
            return []
        entries.append(
            {
                "claim_status": str(payload.get("claim_status") or ""),
                "receipt_id": str(payload.get("result_receipt_id") or ""),
                "receipt_digest": str(payload.get("result_receipt_digest") or ""),
                "previous_history_digest": str(
                    payload.get("previous_history_digest") or ""
                ),
                "history_entry_digest": str(
                    payload.get("history_entry_digest") or ""
                ),
            }
        )
    return entries


def _history_entries(history: Mapping[str, Any]) -> list[dict[str, str]]:
    entries = history.get("signed_worker_task_result_receipts", [])
    return [dict(item) for item in entries] if isinstance(entries, list) else []


def _digest(payload: Any) -> str:
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, default=str,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_digest(value: Any) -> bool:
    text = str(value or "").removeprefix("sha256:")
    return len(text) == 64 and all(char in "0123456789abcdef" for char in text)


__all__ = [
    "RESULT_HISTORY_LIMIT",
    "persist_result_history_ledger",
    "validate_result_history_ledger",
    "validated_result_history",
]
