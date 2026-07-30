"""Main-process bridge from a durable FIX claim to existing handoff artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from modules.communication.moltbot_bridge.src.reddog_agentdb_fix_promotion_claim import (
    AgentDbFixPromotionClaimStore,
    RedDogFixPromotionClaim,
    claim_next_reddog_fix_promotion,
)
from modules.communication.moltbot_bridge.src.reddog_resident_fix_promotion_artifact_handoff import (
    run_reddog_resident_fix_promotion_artifact_handoff,
)


MAIN_FIX_CLAIM_HANDOFF_APPLIED = "MAIN_FIX_CLAIM_HANDOFF_APPLIED"
MAIN_FIX_CLAIM_HANDOFF_IDLE = "MAIN_FIX_CLAIM_HANDOFF_IDLE"
MAIN_FIX_CLAIM_HANDOFF_REJECT = "MAIN_FIX_CLAIM_HANDOFF_REJECT"


@dataclass(frozen=True)
class MainFixPromotionClaimHandoffResult:
    accepted: bool
    status: str
    claim: Optional[RedDogFixPromotionClaim]
    architect_determination_path: Optional[str]
    memex_supply_receipt_path: Optional[str]
    rejection_reasons: tuple[str, ...] = ()
    no_signing_performed: bool = True
    no_queue_mutation_performed: bool = True
    no_worker_dispatch_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["claim"] = self.claim.to_dict() if self.claim else None
        return value


def run_reddog_main_fix_promotion_claim_handoff(
    *,
    repo_root: Path | str,
    architect_determination_output_path: Path | str | None,
    memex_supply_receipt_output_path: Path | str | None,
    worker_id: str,
    now: datetime | None = None,
    lease_seconds: int = 900,
    agent_db_factory: Optional[Callable[[], Any]] = None,
) -> MainFixPromotionClaimHandoffResult:
    """Claim and materialize one FIX using existing AgentDB truth."""

    claim = claim_next_reddog_fix_promotion(
        worker_id=worker_id,
        now=now,
        lease_seconds=lease_seconds,
        agent_db_factory=agent_db_factory,
    )
    if not claim.accepted:
        return MainFixPromotionClaimHandoffResult(
            False,
            MAIN_FIX_CLAIM_HANDOFF_IDLE,
            None,
            None,
            None,
            claim.rejection_reasons,
        )
    return _materialize_claim(
        claim=claim,
        store=AgentDbFixPromotionClaimStore(agent_db_factory),
        repo_root=repo_root,
        architect_determination_output_path=architect_determination_output_path,
        memex_supply_receipt_output_path=memex_supply_receipt_output_path,
        now=now,
    )


def _materialize_claim(
    *,
    claim: RedDogFixPromotionClaim,
    store: AgentDbFixPromotionClaimStore,
    repo_root: Path | str,
    architect_determination_output_path: Path | str | None,
    memex_supply_receipt_output_path: Path | str | None,
    now: datetime | None,
) -> MainFixPromotionClaimHandoffResult:
    handoff = run_reddog_resident_fix_promotion_artifact_handoff(
        repo_root=repo_root,
        intent_id=str(claim.intent_id or ""),
        architect_determination_output_path=architect_determination_output_path,
        memex_supply_receipt_output_path=memex_supply_receipt_output_path,
        expected_claim_binding={
            "cycle_id": str(claim.cycle_id or ""),
            "snapshot_id": str(claim.snapshot_id or ""),
            "determination_id": str(claim.determination_id or ""),
            "queue_candidate_id": str(claim.queue_candidate_id or ""),
            "wsp15_allocation_receipt_id": str(
                claim.wsp15_allocation_receipt_id or ""
            ),
        },
    )
    if not handoff.accepted:
        store.release(claim, now=now)
        return MainFixPromotionClaimHandoffResult(
            False,
            MAIN_FIX_CLAIM_HANDOFF_REJECT,
            claim,
            None,
            None,
            handoff.rejection_reasons,
        )
    return MainFixPromotionClaimHandoffResult(
        True,
        MAIN_FIX_CLAIM_HANDOFF_APPLIED,
        claim,
        handoff.architect_determination_path,
        handoff.memex_supply_receipt_path,
    )

__all__ = [
    "MAIN_FIX_CLAIM_HANDOFF_APPLIED",
    "MAIN_FIX_CLAIM_HANDOFF_IDLE",
    "MAIN_FIX_CLAIM_HANDOFF_REJECT",
    "MainFixPromotionClaimHandoffResult",
    "run_reddog_main_fix_promotion_claim_handoff",
]
