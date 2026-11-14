"""Cross-process fence for one authoritative RedDog FIX promotion."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Mapping, TypeVar

from modules.communication.moltbot_bridge.src.reddog_agentdb_fix_promotion_claim_record import (
    RedDogFixPromotionClaim,
)
from modules.communication.moltbot_bridge.src.reddog_agentdb_fix_promotion_claim_storage import (
    ensure_claim_table,
    iso_utc,
    utc,
)


T = TypeVar("T")


class FixPromotionClaimFenceLost(RuntimeError):
    """Raised when a claimant no longer owns the durable promotion fence."""


def execute_with_fix_promotion_claim_fence(
    store: Any,
    claim: RedDogFixPromotionClaim,
    operation: Callable[[Mapping[str, Any]], T],
    *,
    now: datetime | None = None,
) -> T:
    """Hold the AgentDB writer fence across the authoritative promotion CAS."""

    observed = utc(now)
    if not _claim_complete(claim):
        raise FixPromotionClaimFenceLost("promotion_claim_incomplete")
    db = store._db()
    ensure_claim_table(db)
    with db.db.get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = _current_claim_row(conn, claim, observed)
        if row is None:
            raise FixPromotionClaimFenceLost("promotion_claim_fence_lost")
        fence = _fence_mapping(claim, row)
        result = operation(fence)
        if getattr(result, "accepted", False):
            _mark_applied(conn, claim, result, observed)
        return result


def _current_claim_row(conn, claim, observed):
    return conn.execute(
        """
        SELECT revision, determination_id, queue_candidate_id, wsp15_receipt_id
        FROM reddog_fix_promotion_claims
        WHERE claim_id = ? AND status = 'CLAIMED' AND lease_id = ?
          AND lease_owner = ? AND revision = ? AND lease_expires_at > ?
        """,
        (
            claim.claim_id,
            claim.lease_id,
            claim.lease_owner,
            claim.claim_revision,
            iso_utc(observed),
        ),
    ).fetchone()


def _fence_mapping(claim, row) -> dict[str, Any]:
    return {
        "schema_version": "reddog_fix_promotion_claim_fence.v1",
        "agentdb_claim_id": claim.claim_id,
        "lease_id": claim.lease_id,
        "lease_owner": claim.lease_owner,
        "claim_revision": int(row["revision"]),
        "determination_id": str(row["determination_id"]),
        "queue_candidate_id": str(row["queue_candidate_id"]),
        "wsp15_allocation_receipt_id": str(row["wsp15_receipt_id"]),
    }


def _mark_applied(conn, claim, result, observed) -> None:
    receipt = getattr(result, "receipt", None)
    receipt_id = str(getattr(receipt, "promotion_receipt_id", "") or "")
    committed_revision = str(getattr(receipt, "committed_revision", "") or "")
    if not receipt_id or not committed_revision:
        raise FixPromotionClaimFenceLost("promotion_receipt_binding_missing")
    cursor = conn.execute(
        """
        UPDATE reddog_fix_promotion_claims
        SET status = 'APPLIED', promotion_receipt_id = ?, committed_revision = ?,
            lease_id = NULL, lease_owner = NULL, lease_expires_at = NULL,
            revision = revision + 1, updated_at = ?
        WHERE claim_id = ? AND status = 'CLAIMED' AND lease_id = ?
          AND lease_owner = ? AND revision = ? AND lease_expires_at > ?
        """,
        (
            receipt_id,
            committed_revision,
            iso_utc(observed),
            claim.claim_id,
            claim.lease_id,
            claim.lease_owner,
            claim.claim_revision,
            iso_utc(observed),
        ),
    )
    if cursor.rowcount != 1:
        raise FixPromotionClaimFenceLost("promotion_claim_completion_failed")


def _claim_complete(claim: RedDogFixPromotionClaim) -> bool:
    return bool(
        claim.accepted
        and claim.claim_id
        and claim.lease_id
        and claim.lease_owner
        and claim.claim_revision is not None
    )


__all__ = [
    "FixPromotionClaimFenceLost",
    "execute_with_fix_promotion_claim_fence",
]
