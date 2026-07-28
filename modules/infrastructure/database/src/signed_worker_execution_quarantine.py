"""Atomic terminal quarantine for unverifiable signed-worker executions."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


QUARANTINE_SCHEMA = "reddog_signed_worker_execution_quarantine.v1"


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


def _quarantine(
    connection: Any, *, task_id: str, raw_context: str,
    expected_status: str, reason: str, now_iso: str,
) -> str:
    task = connection.execute(
        "SELECT status, context FROM agents_autonomous_tasks WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    if _already_quarantined(task, task_id=task_id):
        if not _no_result_history(connection, task_id):
            return "REJECTED"
        if not _quarantine_reservation(
            connection,
            task_id=task_id,
            reason=reason,
            now_iso=now_iso,
        ):
            raise RuntimeError("assurance_quarantine_rejected")
        return "QUARANTINED"
    if (
        task is None
        or dict(task).get("status") != expected_status
        or str(dict(task).get("context") or "") != raw_context
    ):
        return "REJECTED"
    return _persist_quarantine(
        connection, task_id, raw_context, expected_status, reason, now_iso
    )


def _persist_quarantine(
    connection: Any, task_id: str, raw_context: str,
    expected_status: str, reason: str, now_iso: str,
) -> str:
    context = _context(raw_context)
    context["signed_worker_execution_quarantine"] = _receipt(
        task_id=task_id,
        reason=reason,
        now_iso=now_iso,
    )
    if not _quarantine_reservation(
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


def _quarantine_reservation(
    connection: Any, *, task_id: str, reason: str, now_iso: str,
) -> bool:
    row = connection.execute(
        "SELECT reservation_id, status FROM "
        "agents_independent_assurance_reservations "
        "WHERE verifier_task_id = ?",
        (task_id,),
    ).fetchone()
    if row is None:
        return True
    payload = dict(row)
    if payload.get("status") == "QUARANTINED":
        return True
    if payload.get("status") != "RESERVED":
        return False
    changed = connection.execute(
        "UPDATE agents_independent_assurance_reservations "
        "SET status = 'QUARANTINED', terminal_status = 'INDETERMINATE', "
        "completed_at = ?, revocation_reason = ? "
        "WHERE reservation_id = ? AND status = 'RESERVED'",
        (
            now_iso,
            f"signed_worker_execution_quarantined:{reason}",
            payload["reservation_id"],
        ),
    ).rowcount
    return changed == 1


def _already_quarantined(row: Any, *, task_id: str) -> bool:
    if row is None or dict(row).get("status") != "quarantined":
        return False
    context = _context(str(dict(row).get("context") or ""))
    receipt = context.get("signed_worker_execution_quarantine")
    return bool(
        isinstance(receipt, Mapping)
        and receipt.get("schema_version") == QUARANTINE_SCHEMA
        and receipt.get("task_id") == task_id
        and receipt.get("effect_commit_state") == "INDETERMINATE"
        and receipt.get("no_worker_effect_replayed") is True
        and _digest_without_receipt(receipt) == receipt.get("receipt_id")
    )


def _no_result_history(connection: Any, task_id: str) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) AS count FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    return row is not None and int(dict(row).get("count") or 0) == 0


def _receipt(*, task_id: str, reason: str, now_iso: str) -> dict[str, Any]:
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


def _context(raw_context: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_context)
    except (TypeError, ValueError):
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


def _digest_without_receipt(receipt: Mapping[str, Any]) -> str:
    return _digest(
        {
            key: value
            for key, value in receipt.items()
            if key != "receipt_id"
        }
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
    "quarantine_signed_worker_execution",
]
