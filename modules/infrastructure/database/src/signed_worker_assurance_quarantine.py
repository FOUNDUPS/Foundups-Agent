"""Atomic assurance transitions for signed-worker execution quarantine."""

from __future__ import annotations

from typing import Any, Mapping

from .protected_autonomous_task_namespace import (
    has_holoindex_postmerge_task_binding,
)


def quarantine_linked_assurance(
    connection: Any,
    *,
    task_id: str,
    reason: str,
    now_iso: str,
) -> bool:
    """Quarantine one unambiguous reservation and release its verifier."""

    rows = _linked_rows(connection, task_id)
    if not rows:
        return True
    if len(rows) != 1:
        return False
    reservation = rows[0]
    if has_holoindex_postmerge_task_binding(reservation):
        return False
    if reservation.get("status") == "QUARANTINED":
        return linked_assurance_is_quarantined(connection, task_id)
    if reservation.get("status") != "RESERVED":
        return False
    changed = connection.execute(
        "UPDATE agents_independent_assurance_reservations "
        "SET status = 'QUARANTINED', terminal_status = 'INDETERMINATE', "
        "completed_at = ?, revocation_reason = ? "
        "WHERE reservation_id = ? AND status = 'RESERVED'",
        (
            now_iso,
            f"signed_worker_execution_quarantined:{reason}",
            reservation["reservation_id"],
        ),
    ).rowcount
    return changed == 1 and _cancel_paired_verifier(
        connection, task_id, reservation, now_iso
    )


def linked_assurance_is_quarantined(connection: Any, task_id: str) -> bool:
    """Verify reservation and paired verifier reached coherent terminal state."""

    rows = _linked_rows(connection, task_id)
    if not rows:
        return True
    reservation = rows[0] if len(rows) == 1 else {}
    return (
        not has_holoindex_postmerge_task_binding(reservation)
        and reservation.get("status") == "QUARANTINED"
        and _paired_verifier_is_terminal(connection, task_id, reservation)
    )


def _linked_rows(connection: Any, task_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT reservation_id, status, author_task_id, verifier_task_id, "
        "verifier_principal_id FROM agents_independent_assurance_reservations "
        "WHERE author_task_id = ? OR verifier_task_id = ?",
        (task_id, task_id),
    ).fetchall()
    return [dict(row) for row in rows]


def _cancel_paired_verifier(
    connection: Any,
    task_id: str,
    reservation: Mapping[str, Any],
    now_iso: str,
) -> bool:
    if reservation.get("author_task_id") != task_id:
        return True
    return connection.execute(
        "UPDATE agents_autonomous_tasks SET status = 'cancelled', completed_at = ? "
        "WHERE task_id = ? AND status IN ('assigned', 'executing') "
        "AND assigned_to = ?",
        (
            now_iso,
            reservation.get("verifier_task_id"),
            reservation.get("verifier_principal_id"),
        ),
    ).rowcount == 1


def _paired_verifier_is_terminal(
    connection: Any,
    task_id: str,
    reservation: Mapping[str, Any],
) -> bool:
    if reservation.get("author_task_id") != task_id:
        return True
    row = connection.execute(
        "SELECT status FROM agents_autonomous_tasks WHERE task_id = ?",
        (reservation.get("verifier_task_id"),),
    ).fetchone()
    return (
        row is not None
        and dict(row).get("status") in {"cancelled", "quarantined"}
    )


__all__ = ["linked_assurance_is_quarantined", "quarantine_linked_assurance"]
