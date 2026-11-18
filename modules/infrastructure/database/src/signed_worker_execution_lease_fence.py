"""Durable lease binding and finalization fence for signed workers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from .signed_worker_execution_lease_time import aware, parse_utc


def execution_lease_allows_finalization(
    connection: Any,
    *,
    task_id: str,
    assigned_to: str,
    claim: Mapping[str, Any],
    use: Mapping[str, Any],
    now: datetime,
    allow_expired_recovery: bool,
) -> bool:
    """Fence finalization against the durable lease in the same transaction."""

    row = connection.execute(
        "SELECT * FROM agents_signed_worker_execution_leases WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    if not matching_execution_lease(
        row, assigned_to=assigned_to, claim=claim, use=use
    ):
        return False
    expires_at = parse_utc(dict(row).get("lease_expires_at"))
    if expires_at is None:
        return False
    expired = aware(now) >= expires_at
    return expired if allow_expired_recovery else not expired


def matching_execution_lease(
    row: Any,
    *,
    assigned_to: str,
    claim: Mapping[str, Any],
    use: Mapping[str, Any],
) -> bool:
    """Require the exact task owner and admitted receipt pair."""

    if row is None:
        return False
    payload = dict(row)
    return (
        payload.get("assigned_to") == assigned_to
        and payload.get("claim_receipt_id") == claim.get("receipt_id")
        and payload.get("use_receipt_id") == use.get("receipt_id")
        and payload.get("initial_claimed_at") == claim.get("claimed_at")
    )


__all__ = [
    "execution_lease_allows_finalization",
    "matching_execution_lease",
]
