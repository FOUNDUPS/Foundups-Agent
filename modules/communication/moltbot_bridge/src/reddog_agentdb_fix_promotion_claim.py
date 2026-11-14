"""Claim one validated durable RedDog FIX for main-process promotion."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_agentdb_fix_promotion_claim_store import (
    AgentDbFixPromotionClaimStore,
    RedDogFixPromotionClaim,
)
from modules.communication.moltbot_bridge.src.reddog_agentdb_fix_promotion_claim_validation import (
    validated_fix_promotion_binding,
)
from modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle import (
    AgentDbResidentArchitectCycleStore,
)


def claim_next_reddog_fix_promotion(
    *,
    worker_id: str,
    now: datetime | None = None,
    lease_seconds: int = 300,
    agent_db_factory: Optional[Callable[[], Any]] = None,
) -> RedDogFixPromotionClaim:
    """Lease the oldest valid unpromoted terminal FIX determination."""

    store = AgentDbFixPromotionClaimStore(agent_db_factory)
    cycle_store = AgentDbResidentArchitectCycleStore(agent_db_factory)
    rejected: list[str] = []
    for intent_id in store.determined_intent_ids():
        cycle = cycle_store.load_cycle_by_intent(intent_id)
        determination: Mapping[str, Any] | None = None
        if isinstance(cycle, Mapping):
            determination = store.load_determination(
                str(cycle.get("architect_determination_id") or "")
            )
        binding, reasons = validated_fix_promotion_binding(cycle, determination)
        if reasons:
            rejected.extend(reasons)
            continue
        claim = store.claim(
            binding,
            worker_id=worker_id,
            now=now,
            lease_seconds=lease_seconds,
        )
        if claim.accepted:
            return claim
    return store.idle(*tuple(dict.fromkeys(rejected)))


__all__ = [
    "AgentDbFixPromotionClaimStore",
    "RedDogFixPromotionClaim",
    "claim_next_reddog_fix_promotion",
]
