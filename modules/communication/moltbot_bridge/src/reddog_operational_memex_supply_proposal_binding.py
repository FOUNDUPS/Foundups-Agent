"""Revalidate typed Memex supply before architect-proposal signing."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_operational_memex_supply_receipt import (
    OperationalMemexSupplyReceipt,
    rehydrate_operational_memex_supply_receipt,
)


def verify_memex_supply_for_architect_proposal(
    receipt: OperationalMemexSupplyReceipt,
    *,
    proposal_admission: Mapping[str, Any],
    requester_principal_id: str,
    proposal_issued_at: int,
) -> OperationalMemexSupplyReceipt:
    """Reject manually constructed or proposal-mismatched typed receipts."""

    if not isinstance(receipt, OperationalMemexSupplyReceipt):
        raise ValueError("architect_proposal_memex_supply_not_verified")
    proposal = dict(proposal_admission)
    return rehydrate_operational_memex_supply_receipt(
        receipt.to_dict(),
        expected_foundup_id=receipt.foundup_id,
        expected_principal_id=requester_principal_id,
        expected_snapshot_receipt_id=str(
            proposal.get("snapshot_receipt_id") or ""
        ),
        expected_snapshot_content_digest=str(
            proposal.get("snapshot_content_digest") or ""
        ),
        expected_holoindex_generation_id=str(
            proposal.get("holoindex_generation_id") or ""
        ),
        expected_source_revision=str(
            proposal.get("work_state_revision") or ""
        ),
        now_iso=datetime.fromtimestamp(
            int(proposal_issued_at),
            timezone.utc,
        ).isoformat(),
    )


__all__ = ["verify_memex_supply_for_architect_proposal"]
