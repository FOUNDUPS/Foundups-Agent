"""Pure validation helpers for signed-worker result continuity."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


RESULT_HISTORY_LIMIT = 10
ENTRY_KEYS = {
    "attempt_sequence",
    "claim_status",
    "receipt_id",
    "receipt_digest",
    "previous_history_digest",
    "history_entry_digest",
}


def canonical_digest(payload: Any) -> str:
    """Return the canonical digest used by result receipts and ledger entries."""

    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, default=str,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


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


def history_entries(history: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return copied canonical entries from validated context."""

    entries = history.get("signed_worker_task_result_receipts", [])
    return [dict(item) for item in entries] if isinstance(entries, list) else []


def valid_history_entry(
    entry: Mapping[str, Any],
    supplied: str,
    prior: Mapping[str, Any] | None,
    *,
    require_genesis: bool = False,
) -> bool:
    """Validate one entry and its link to the preceding durable entry."""

    expected_sequence = int(prior["attempt_sequence"]) + 1 if prior else None
    expected_previous = (
        str(prior["history_entry_digest"])
        if prior
        else canonical_digest([]) if require_genesis else None
    )
    return (
        bool(entry["claim_status"])
        and _is_digest(entry["receipt_digest"])
        and _is_digest(entry["previous_history_digest"])
        and _is_digest(supplied)
        and (expected_sequence is None or entry["attempt_sequence"] == expected_sequence)
        and (expected_previous is None or entry["previous_history_digest"] == expected_previous)
        and supplied == canonical_digest(entry)
    )


def _validate_last_result(last: Mapping[str, Any]) -> None:
    body = dict(last)
    supplied = str(body.pop("receipt_digest", "") or "")
    if not _is_digest(supplied) or supplied != canonical_digest(body):
        raise ValueError("signed_worker_last_result_digest_mismatch")


def _normalize_entries(history: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in history:
        if not isinstance(item, Mapping) or set(item) != ENTRY_KEYS:
            raise ValueError("signed_worker_result_history_item_invalid")
        sequence = item.get("attempt_sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
            raise ValueError("signed_worker_result_history_item_invalid")
        entry = {
            "attempt_sequence": sequence,
            **{
                key: str(item.get(key) or "")
                for key in ENTRY_KEYS
                if key not in {"attempt_sequence", "history_entry_digest"}
            },
        }
        supplied = str(item.get("history_entry_digest") or "")
        prior = normalized[-1] if normalized else None
        if not valid_history_entry(entry, supplied, prior):
            raise ValueError("signed_worker_result_history_item_invalid")
        entry["history_entry_digest"] = supplied
        normalized.append(entry)
    return normalized


def _is_digest(value: Any) -> bool:
    text = str(value or "").removeprefix("sha256:")
    return len(text) == 64 and all(char in "0123456789abcdef" for char in text)


__all__ = [
    "RESULT_HISTORY_LIMIT",
    "canonical_digest",
    "history_entries",
    "valid_history_entry",
    "validated_result_history",
]
