"""Atomic assurance-reservation completion for signed-worker finalization."""

from __future__ import annotations

from typing import Any, Mapping

from .signed_worker_assurance_request import (
    ASSURANCE_COMPLETION_SCHEMA_VERSION,
    build_assurance_completion_request,
    canonical_request_digest,
    canonical_request_json,
    parse_utc,
    validated_assurance_completion_request,
)


def complete_assurance_reservation(
    connection: Any,
    *,
    task_id: str,
    assigned_to: str,
    request: Mapping[str, Any],
) -> bool:
    """Complete one reservation inside the caller-owned DB transaction."""

    normalized = validated_assurance_completion_request(
        request,
        task_id=str(task_id or ""),
        assigned_to=str(assigned_to or ""),
    )
    if normalized is None:
        return False
    if not _matches_durable_reservation(connection, normalized):
        return False
    changed = connection.execute(
        "UPDATE agents_independent_assurance_reservations "
        "SET status = ?, terminal_receipt_id = ?, "
        "terminal_receipt_digest = ?, terminal_status = ?, completed_at = ? "
        "WHERE reservation_id = ? AND status = 'RESERVED' "
        "AND verifier_task_id = ? AND verifier_principal_id = ? "
        "AND admission_reservation_digest = ?",
        (
            normalized["terminal_status"],
            normalized["terminal_receipt_id"],
            normalized["terminal_receipt_digest"],
            normalized["terminal_status"],
            normalized["completed_at"],
            normalized["reservation_id"],
            normalized["verifier_task_id"],
            normalized["verifier_principal_id"],
            normalized["admission_reservation_digest"],
        ),
    ).rowcount
    return changed == 1


def _matches_durable_reservation(
    connection: Any,
    request: Mapping[str, str],
) -> bool:
    row = connection.execute(
        "SELECT status, verifier_task_id, verifier_principal_id, "
        "admission_reservation_digest, admission_reserved_at, reserved_at, "
        "expires_at, staged_completion_json, staged_completion_digest "
        "FROM agents_independent_assurance_reservations "
        "WHERE reservation_id = ?",
        (request["reservation_id"],),
    ).fetchone()
    if row is None:
        return False
    durable = dict(row)
    return (
        durable.get("status") == "RESERVED"
        and durable.get("verifier_task_id") == request["verifier_task_id"]
        and durable.get("verifier_principal_id")
        == request["verifier_principal_id"]
        and durable.get("admission_reservation_digest")
        == request["admission_reservation_digest"]
        and durable.get("staged_completion_json")
        == canonical_request_json(request)
        and durable.get("staged_completion_digest")
        == canonical_request_digest(request)
        and _within_lease(durable, request["completed_at"])
    )


def _within_lease(
    reservation: Mapping[str, Any],
    completed_at: str,
) -> bool:
    completed = parse_utc(completed_at)
    reserved = parse_utc(
        str(
            reservation.get("admission_reserved_at")
            or reservation.get("reserved_at")
            or ""
        )
    )
    expires = parse_utc(str(reservation.get("expires_at") or ""))
    return (
        completed is not None
        and reserved is not None
        and expires is not None
        and reserved <= completed < expires
    )


__all__ = [
    "ASSURANCE_COMPLETION_SCHEMA_VERSION",
    "build_assurance_completion_request",
    "complete_assurance_reservation",
]
