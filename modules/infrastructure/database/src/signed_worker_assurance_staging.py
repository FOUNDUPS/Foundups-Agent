"""Durable pre-finalization staging for independent-assurance output."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .signed_worker_assurance_request import (
    canonical_request_digest,
    canonical_request_json,
    parse_utc,
    validated_assurance_completion_request,
)


def stage_assurance_completion(
    connection: Any,
    *,
    request: Mapping[str, Any],
) -> bool:
    """Bind verifier output to its executing task without terminalizing it."""

    normalized = validated_assurance_completion_request(request)
    if normalized is None:
        return False
    reservation = _reservation(connection, normalized["reservation_id"])
    if not _reservation_accepts(reservation, normalized):
        return False
    task = connection.execute(
        "SELECT status, assigned_to FROM agents_autonomous_tasks "
        "WHERE task_id = ?",
        (normalized["verifier_task_id"],),
    ).fetchone()
    if (
        task is None
        or dict(task).get("status") != "executing"
        or dict(task).get("assigned_to")
        != normalized["verifier_principal_id"]
    ):
        return False
    raw = canonical_request_json(normalized)
    digest = canonical_request_digest(normalized)
    existing = str(reservation.get("staged_completion_json") or "")
    existing_digest = str(reservation.get("staged_completion_digest") or "")
    if existing or existing_digest:
        return existing == raw and existing_digest == digest
    changed = connection.execute(
        "UPDATE agents_independent_assurance_reservations "
        "SET staged_completion_json = ?, staged_completion_digest = ?, "
        "staged_at = ? WHERE reservation_id = ? AND status = 'RESERVED' "
        "AND staged_completion_json IS NULL "
        "AND staged_completion_digest IS NULL",
        (
            raw,
            digest,
            normalized["completed_at"],
            normalized["reservation_id"],
        ),
    ).rowcount
    return changed == 1


def rehydrate_staged_assurance_completion(
    database: Any,
    *,
    task_id: str,
    assigned_to: str,
) -> dict[str, str] | None:
    """Return the single durable staged request bound to an executing verifier."""

    if not task_id or not assigned_to:
        return None
    selected = _staged_request_rows(
        database,
        task_id=task_id,
        assigned_to=assigned_to,
    )
    if selected is None:
        return None
    reservation, task_row = selected
    if (
        task_row.get("status") != "executing"
        or task_row.get("assigned_to") != assigned_to
    ):
        return None
    return _validated_staged_request(
        reservation,
        task_id=task_id,
        assigned_to=assigned_to,
    )


def _staged_request_rows(
    database: Any,
    *,
    task_id: str,
    assigned_to: str,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    try:
        with database.get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM agents_independent_assurance_reservations "
                "WHERE verifier_task_id = ? AND verifier_principal_id = ? "
                "AND status = 'RESERVED' AND staged_completion_json IS NOT NULL "
                "AND staged_completion_digest IS NOT NULL",
                (task_id, assigned_to),
            ).fetchall()
            task = connection.execute(
                "SELECT status, assigned_to FROM agents_autonomous_tasks "
                "WHERE task_id = ?",
                (task_id,),
            ).fetchone()
    except Exception:
        return None
    if len(rows) != 1 or task is None:
        return None
    return dict(rows[0]), dict(task)


def _validated_staged_request(
    reservation: Mapping[str, Any],
    *,
    task_id: str,
    assigned_to: str,
) -> dict[str, str] | None:
    try:
        request = json.loads(str(reservation.get("staged_completion_json") or ""))
    except (TypeError, ValueError):
        return None
    normalized = validated_assurance_completion_request(
        request,
        task_id=task_id,
        assigned_to=assigned_to,
    )
    if (
        normalized is None
        or canonical_request_json(normalized)
        != reservation.get("staged_completion_json")
        or canonical_request_digest(normalized)
        != reservation.get("staged_completion_digest")
        or not _reservation_accepts(reservation, normalized)
    ):
        return None
    return normalized


def _reservation(connection: Any, reservation_id: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT * FROM agents_independent_assurance_reservations "
        "WHERE reservation_id = ?",
        (reservation_id,),
    ).fetchone()
    return dict(row) if row is not None else {}


def _reservation_accepts(
    reservation: Mapping[str, Any],
    request: Mapping[str, str],
) -> bool:
    completed = parse_utc(request["completed_at"])
    reserved = parse_utc(
        str(
            reservation.get("admission_reserved_at")
            or reservation.get("reserved_at")
            or ""
        )
    )
    expires = parse_utc(str(reservation.get("expires_at") or ""))
    return (
        reservation.get("status") == "RESERVED"
        and reservation.get("verifier_task_id") == request["verifier_task_id"]
        and reservation.get("verifier_principal_id")
        == request["verifier_principal_id"]
        and reservation.get("admission_reservation_digest")
        == request["admission_reservation_digest"]
        and completed is not None
        and reserved is not None
        and expires is not None
        and reserved <= completed < expires
    )


__all__ = [
    "rehydrate_staged_assurance_completion",
    "stage_assurance_completion",
]
