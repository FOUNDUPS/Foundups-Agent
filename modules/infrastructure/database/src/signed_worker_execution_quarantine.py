"""Atomic terminal quarantine for unverifiable signed-worker executions."""

from __future__ import annotations

import json
from typing import Any

from .signed_worker_assurance_quarantine import (
    linked_assurance_is_quarantined,
    quarantine_linked_assurance,
)
from .signed_worker_execution_quarantine_receipt import (
    QUARANTINE_SCHEMA,
    build_quarantine_receipt,
    decoded_context,
    quarantine_receipt_matches,
)
from .signed_worker_execution_store import is_signed_worker_task_id


def quarantine_signed_worker_execution(
    db: Any, *, task_id: str, raw_context: Any,
    expected_status: str, reason: str, now_iso: str,
) -> str:
    """Quarantine task and verifier reservation in one transaction."""

    try:
        with db.db.get_connection() as connection:
            return _quarantine(
                connection,
                task_id=task_id,
                raw_context=str(raw_context or ""),
                expected_status=expected_status,
                reason=reason,
                now_iso=now_iso,
            )
    except Exception:
        return "REJECTED"


def quarantine_signed_worker_execution_in_transaction(
    connection: Any,
    *,
    task_id: str,
    raw_context: Any,
    expected_status: str,
    reason: str,
    now_iso: str,
) -> str:
    """Quarantine through an existing transaction without weakening checks."""

    return _quarantine(
        connection,
        task_id=task_id,
        raw_context=str(raw_context or ""),
        expected_status=expected_status,
        reason=reason,
        now_iso=now_iso,
    )


def _quarantine(
    connection: Any, *, task_id: str, raw_context: str,
    expected_status: str, reason: str, now_iso: str,
) -> str:
    if not is_signed_worker_task_id(task_id):
        return "REJECTED"
    task = connection.execute(
        "SELECT status, context FROM agents_autonomous_tasks WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    if quarantine_receipt_matches(task, task_id=task_id):
        if (
            not _no_result_history(connection, task_id)
            or not linked_assurance_is_quarantined(connection, task_id)
        ):
            return "REJECTED"
        return "QUARANTINED"
    if (
        task is None
        or dict(task).get("status") != expected_status
        or str(dict(task).get("context") or "") != raw_context
        or not _no_result_history(connection, task_id)
    ):
        return "REJECTED"
    return _persist_quarantine(
        connection, task_id, raw_context, expected_status, reason, now_iso
    )


def _persist_quarantine(
    connection: Any, task_id: str, raw_context: str,
    expected_status: str, reason: str, now_iso: str,
) -> str:
    context = decoded_context(raw_context)
    context["signed_worker_execution_quarantine"] = build_quarantine_receipt(
        task_id=task_id,
        reason=reason,
        now_iso=now_iso,
    )
    if not quarantine_linked_assurance(
        connection,
        task_id=task_id,
        reason=reason,
        now_iso=now_iso,
    ):
        raise RuntimeError("assurance_quarantine_rejected")
    changed = connection.execute(
        "UPDATE agents_autonomous_tasks SET status = 'quarantined', "
        "completed_at = ?, context = ? "
        "WHERE task_id = ? AND status = ? AND context = ?",
        (
            now_iso,
            json.dumps(context, sort_keys=True),
            task_id,
            expected_status,
            raw_context,
        ),
    ).rowcount
    if changed != 1:
        raise RuntimeError("task_quarantine_rejected")
    return "QUARANTINED"
def _no_result_history(connection: Any, task_id: str) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) AS count FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    return row is not None and int(dict(row).get("count") or 0) == 0


__all__ = [
    "QUARANTINE_SCHEMA",
    "quarantine_signed_worker_execution",
    "quarantine_signed_worker_execution_in_transaction",
]
