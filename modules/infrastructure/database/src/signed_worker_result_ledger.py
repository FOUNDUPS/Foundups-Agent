"""Durable AgentDB continuity ledger for signed-worker results."""

from __future__ import annotations

from typing import Any, Mapping

from .signed_worker_result_history import (
    RESULT_HISTORY_LIMIT,
    history_entries,
    valid_history_entry,
    validated_result_history,
)


def ensure_result_history_schema(connection: Any) -> None:
    """Create the independently durable result-continuity ledger."""

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS agents_signed_worker_result_history (
            task_id TEXT NOT NULL,
            attempt_sequence INTEGER NOT NULL,
            claim_receipt_id TEXT NOT NULL,
            use_receipt_id TEXT NOT NULL,
            claim_status TEXT NOT NULL,
            result_receipt_id TEXT NOT NULL,
            result_receipt_digest TEXT NOT NULL,
            previous_history_digest TEXT NOT NULL,
            history_entry_digest TEXT NOT NULL,
            recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (task_id, attempt_sequence),
            UNIQUE (task_id, claim_receipt_id),
            UNIQUE (task_id, use_receipt_id)
        )
        """
    )


def validate_result_history_ledger(
    connection: Any, task_id: str, context: Mapping[str, Any]
) -> bool:
    """Require context to equal the canonical durable ledger tail."""

    try:
        history = history_entries(validated_result_history(context))
    except ValueError:
        return False
    stored = _read_entries(connection, task_id)
    return stored is not None and history == stored[-RESULT_HISTORY_LIMIT:]


def persist_result_history_ledger(
    connection: Any,
    task_id: str,
    context: Mapping[str, Any],
    *,
    claim_receipt_id: str,
    use_receipt_id: str,
) -> bool:
    """Validate an unchanged tail or append exactly one durable result."""

    try:
        history = history_entries(validated_result_history(context))
    except ValueError:
        return False
    stored = _read_entries(connection, task_id)
    if stored is None:
        return False
    if history == stored[-RESULT_HISTORY_LIMIT:]:
        return True
    if not _is_exact_next_tail(history, stored):
        return False
    return _insert_entry(
        connection,
        task_id,
        history[-1],
        claim_receipt_id=claim_receipt_id,
        use_receipt_id=use_receipt_id,
    )


def _is_exact_next_tail(
    history: list[dict[str, Any]], stored: list[dict[str, Any]]
) -> bool:
    if not history or history[-1]["attempt_sequence"] != len(stored) + 1:
        return False
    return history == [*stored, history[-1]][-RESULT_HISTORY_LIMIT:]


def _insert_entry(
    connection: Any,
    task_id: str,
    entry: Mapping[str, Any],
    *,
    claim_receipt_id: str,
    use_receipt_id: str,
) -> bool:
    changed = connection.execute(
        "INSERT INTO agents_signed_worker_result_history ("
        "task_id, attempt_sequence, claim_receipt_id, use_receipt_id, "
        "claim_status, result_receipt_id, result_receipt_digest, "
        "previous_history_digest, history_entry_digest"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            task_id,
            entry["attempt_sequence"],
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


def _read_entries(
    connection: Any, task_id: str
) -> list[dict[str, Any]] | None:
    rows = connection.execute(
        "SELECT attempt_sequence, claim_status, result_receipt_id, "
        "result_receipt_digest, previous_history_digest, history_entry_digest "
        "FROM agents_signed_worker_result_history "
        "WHERE task_id = ? ORDER BY attempt_sequence",
        (task_id,),
    ).fetchall()
    entries = [_row_entry(row) for row in rows]
    for expected, entry in enumerate(entries, 1):
        prior = entries[expected - 2] if expected > 1 else None
        supplied = str(entry.pop("history_entry_digest") or "")
        if (
            entry["attempt_sequence"] != expected
            or not valid_history_entry(
                entry,
                supplied,
                prior,
                require_genesis=expected == 1,
            )
        ):
            return None
        entry["history_entry_digest"] = supplied
    return entries


def _row_entry(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    return {
        "attempt_sequence": int(payload.get("attempt_sequence") or 0),
        "claim_status": str(payload.get("claim_status") or ""),
        "receipt_id": str(payload.get("result_receipt_id") or ""),
        "receipt_digest": str(payload.get("result_receipt_digest") or ""),
        "previous_history_digest": str(payload.get("previous_history_digest") or ""),
        "history_entry_digest": str(payload.get("history_entry_digest") or ""),
    }


__all__ = [
    "RESULT_HISTORY_LIMIT",
    "ensure_result_history_schema",
    "persist_result_history_ledger",
    "validate_result_history_ledger",
    "validated_result_history",
]
