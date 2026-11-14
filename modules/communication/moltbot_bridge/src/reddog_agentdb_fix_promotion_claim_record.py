"""Typed coordination receipt for one durable RedDog FIX claim."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class RedDogFixPromotionClaim:
    accepted: bool
    status: str
    claim_id: Optional[str] = None
    lease_id: Optional[str] = None
    lease_owner: Optional[str] = None
    lease_expires_at: Optional[str] = None
    intent_id: Optional[str] = None
    cycle_id: Optional[str] = None
    snapshot_id: Optional[str] = None
    determination_id: Optional[str] = None
    queue_candidate_id: Optional[str] = None
    wsp15_allocation_receipt_id: Optional[str] = None
    claim_revision: Optional[int] = None
    rejection_reasons: tuple[str, ...] = ()
    no_execution_authority_granted: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def accepted_fix_promotion_claim(
    binding,
    *,
    claim_id: str,
    lease_id: str,
    worker_id: str,
    expires: str,
    revision: int,
) -> RedDogFixPromotionClaim:
    return RedDogFixPromotionClaim(
        accepted=True,
        status="REDDOG_FIX_PROMOTION_CLAIM_READY",
        claim_id=claim_id,
        lease_id=lease_id,
        lease_owner=worker_id,
        lease_expires_at=expires,
        intent_id=binding["intent_id"],
        cycle_id=binding["cycle_id"],
        snapshot_id=binding["snapshot_id"],
        determination_id=binding["determination_id"],
        queue_candidate_id=binding["queue_candidate_id"],
        wsp15_allocation_receipt_id=binding["wsp15_allocation_receipt_id"],
        claim_revision=revision,
    )


__all__ = ["RedDogFixPromotionClaim", "accepted_fix_promotion_claim"]
