"""Durable bounded lease renewal for one admitted signed-worker execution."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from .signed_worker_execution_binding import finalization_binding
from .signed_worker_execution_lease_schema import (
    MAX_EXECUTION_LEASE_SECONDS,
    ensure_execution_lease_schema,
    initialize_execution_lease,
)
from .signed_worker_execution_lease_time import aware, parse_utc
from .signed_worker_execution_lease_fence import matching_execution_lease


MAX_EXECUTION_LEASE_RENEWALS = 60


def renew_signed_worker_execution_lease(
    db: Any,
    *,
    task_id: str,
    context: Mapping[str, Any],
    now: datetime | None = None,
    extension_seconds: int,
) -> bool:
    """Extend a live lease without changing the signed claim/use receipts."""

    current = aware(now or datetime.now(timezone.utc))
    if extension_seconds <= 0:
        return False
    binding = finalization_binding(
        task_id,
        context.get("signed_worker_execution_claim"),
        context.get("signed_worker_execution_use"),
    )
    if binding is None:
        return False
    assigned_to, claim, use = binding
    try:
        with db.db.get_connection() as connection:
            return _renew(
                connection,
                task_id=task_id,
                assigned_to=assigned_to,
                claim=claim,
                use=use,
                now=current,
                extension_seconds=extension_seconds,
            )
    except Exception:
        return False


def execution_lease_state(
    db: Any,
    *,
    task_id: str,
    context: Mapping[str, Any],
    now: datetime,
) -> str:
    """Return ACTIVE, EXPIRED, or INVALID for the exact admitted execution."""

    binding = finalization_binding(
        task_id,
        context.get("signed_worker_execution_claim"),
        context.get("signed_worker_execution_use"),
    )
    if binding is None:
        return "INVALID"
    assigned_to, claim, use = binding
    try:
        with db.db.get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM agents_signed_worker_execution_leases "
                "WHERE task_id = ?",
                (task_id,),
            ).fetchone()
    except Exception:
        return "INVALID"
    if not matching_execution_lease(
        row, assigned_to=assigned_to, claim=claim, use=use
    ):
        return "INVALID"
    expires_at = parse_utc(dict(row).get("lease_expires_at"))
    if expires_at is None:
        return "INVALID"
    return "ACTIVE" if aware(now) < expires_at else "EXPIRED"


def _renew(
    connection: Any,
    *,
    task_id: str,
    assigned_to: str,
    claim: Mapping[str, Any],
    use: Mapping[str, Any],
    now: datetime,
    extension_seconds: int,
) -> bool:
    task, lease = _renewal_rows(connection, task_id)
    if not _live_task_matches(task, assigned_to, claim, use):
        return False
    if not matching_execution_lease(lease, assigned_to=assigned_to, claim=claim, use=use):
        return False
    payload = dict(lease)
    expires_at = parse_utc(payload.get("lease_expires_at"))
    max_expires_at = parse_utc(payload.get("max_expires_at"))
    renewals = int(payload.get("renewal_count") or 0)
    if (
        expires_at is None
        or max_expires_at is None
        or now >= expires_at
        or renewals >= MAX_EXECUTION_LEASE_RENEWALS
    ):
        return False
    renewed_until = min(
        now + timedelta(seconds=extension_seconds),
        max_expires_at,
    )
    if renewed_until <= expires_at:
        return True
    changed = connection.execute(
        "UPDATE agents_signed_worker_execution_leases "
        "SET lease_expires_at = ?, renewal_count = ?, updated_at = ? "
        "WHERE task_id = ? AND claim_receipt_id = ? AND use_receipt_id = ? "
        "AND lease_expires_at = ? AND renewal_count = ?",
        (
            renewed_until.isoformat(),
            renewals + 1,
            now.isoformat(),
            task_id,
            claim["receipt_id"],
            use["receipt_id"],
            payload["lease_expires_at"],
            renewals,
        ),
    ).rowcount
    return changed == 1


def _renewal_rows(connection: Any, task_id: str) -> tuple[Any, Any]:
    task = connection.execute(
        "SELECT status, assigned_to, context FROM agents_autonomous_tasks "
        "WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    lease = connection.execute(
        "SELECT * FROM agents_signed_worker_execution_leases WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    return task, lease


def _live_task_matches(
    row: Any,
    assigned_to: str,
    claim: Mapping[str, Any],
    use: Mapping[str, Any],
) -> bool:
    if row is None:
        return False
    payload = dict(row)
    try:
        context = json.loads(str(payload.get("context") or ""))
    except (TypeError, ValueError):
        return False
    return (
        payload.get("status") == "executing"
        and payload.get("assigned_to") == assigned_to
        and isinstance(context, Mapping)
        and context.get("signed_worker_execution_claim") == claim
        and context.get("signed_worker_execution_use") == use
    )


__all__ = [
    "MAX_EXECUTION_LEASE_RENEWALS",
    "MAX_EXECUTION_LEASE_SECONDS",
    "ensure_execution_lease_schema", "execution_lease_state",
    "initialize_execution_lease",
    "renew_signed_worker_execution_lease"]
