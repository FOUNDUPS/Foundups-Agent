"""Durable pre-finalization staging for independent-assurance output."""

from __future__ import annotations

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


__all__ = ["stage_assurance_completion"]
