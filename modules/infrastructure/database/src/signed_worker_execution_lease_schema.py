"""Schema and initial persistence for signed-worker execution leases."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Mapping

from .signed_worker_execution_lease_time import parse_utc


MAX_EXECUTION_LEASE_SECONDS = 14_400


def ensure_execution_lease_schema(connection: Any) -> None:
    """Create the exact-claim execution lease table."""

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS agents_signed_worker_execution_leases (
            task_id TEXT PRIMARY KEY,
            claim_receipt_id TEXT NOT NULL,
            use_receipt_id TEXT NOT NULL,
            assigned_to TEXT NOT NULL,
            initial_claimed_at TEXT NOT NULL,
            lease_expires_at TEXT NOT NULL,
            max_expires_at TEXT NOT NULL,
            renewal_count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
        """
    )


def initialize_execution_lease(
    connection: Any,
    *,
    task_id: str,
    assigned_to: str,
    claim: Mapping[str, Any],
    use: Mapping[str, Any],
) -> bool:
    """Persist the initial lease in the execution-admission transaction."""

    claimed_at = parse_utc(claim.get("claimed_at"))
    expires_at = parse_utc(claim.get("lease_expires_at"))
    if not _valid_initial_receipts(
        claim,
        use,
        claimed_at=claimed_at,
        expires_at=expires_at,
    ):
        return False
    max_expires_at = claimed_at + timedelta(
        seconds=MAX_EXECUTION_LEASE_SECONDS
    )
    connection.execute(
        "DELETE FROM agents_signed_worker_execution_leases WHERE task_id = ?",
        (task_id,),
    )
    changed = connection.execute(
        "INSERT INTO agents_signed_worker_execution_leases ("
        "task_id, claim_receipt_id, use_receipt_id, assigned_to, "
        "initial_claimed_at, lease_expires_at, max_expires_at, updated_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            task_id,
            str(claim["receipt_id"]),
            str(use["receipt_id"]),
            assigned_to,
            claimed_at.isoformat(),
            expires_at.isoformat(),
            max_expires_at.isoformat(),
            claimed_at.isoformat(),
        ),
    ).rowcount
    return changed == 1


def _valid_initial_receipts(
    claim: Mapping[str, Any],
    use: Mapping[str, Any],
    *,
    claimed_at: Any,
    expires_at: Any,
) -> bool:
    return bool(
        claimed_at is not None
        and expires_at is not None
        and expires_at > claimed_at
        and claim.get("receipt_id")
        and use.get("receipt_id")
    )


__all__ = [
    "MAX_EXECUTION_LEASE_SECONDS",
    "ensure_execution_lease_schema",
    "initialize_execution_lease",
]
