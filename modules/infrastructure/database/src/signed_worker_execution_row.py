"""Exact-row authentication and CAS update for signed-worker finalization."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Mapping

from .signed_worker_execution_binding import canonical_digest


def matching_execution_context(
    row: Any,
    assigned_to: str,
    claim: Mapping[str, Any],
    use: Mapping[str, Any],
) -> tuple[str, dict[str, Any]] | None:
    """Authenticate the exact executing row and its claim-bound context."""

    if row is None:
        return None
    payload, raw_context = dict(row), str(dict(row).get("context") or "")
    try:
        stored = json.loads(raw_context)
    except (TypeError, ValueError):
        return None
    if (
        payload.get("status") != "executing"
        or str(payload.get("assigned_to") or "") != assigned_to
        or not isinstance(stored, dict)
        or not supplied_execution_receipts_match(stored, claim, use)
    ):
        return None
    digest_context = dict(stored)
    digest_context.pop("signed_worker_execution_claim", None)
    digest_context.pop("signed_worker_execution_use", None)
    return (
        (raw_context, dict(stored))
        if claim.get("context_digest") == canonical_digest(digest_context)
        else None
    )


def supplied_execution_receipts_match(
    context: Mapping[str, Any],
    claim: Mapping[str, Any],
    use: Mapping[str, Any],
) -> bool:
    """Require the exact admitted claim and one-use receipt pair."""

    return bool(
        context.get("signed_worker_execution_claim") == claim
        and context.get("signed_worker_execution_use") == use
    )


def update_signed_worker_final_row(
    connection: Any,
    *,
    row: Mapping[str, Any],
    task_id: str,
    assigned_to: str,
    raw_context: str,
    final_context: Mapping[str, Any],
    persisted_status: str,
    retry_not_before: str | None,
) -> bool:
    """CAS one executing row to its validated terminal or requeue state."""

    requeue = persisted_status == "pending"
    changed = connection.execute(
        "UPDATE agents_autonomous_tasks SET context = ?, status = ?, "
        "completed_at = ?, retry_not_before = ?, assigned_to = ?, assigned_at = ? "
        "WHERE task_id = ? AND status = 'executing' "
        "AND assigned_to = ? AND context = ?",
        (
            json.dumps(dict(final_context), sort_keys=True),
            persisted_status,
            None if requeue else row.get("completed_at") or datetime.now().isoformat(),
            retry_not_before if requeue else None,
            None if requeue else assigned_to,
            None if requeue else row.get("assigned_at"),
            task_id,
            assigned_to,
            raw_context,
        ),
    ).rowcount
    return changed == 1


__all__ = [
    "matching_execution_context",
    "supplied_execution_receipts_match",
    "update_signed_worker_final_row",
]
