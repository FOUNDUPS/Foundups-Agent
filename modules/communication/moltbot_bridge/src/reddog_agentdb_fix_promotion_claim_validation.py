"""Validate AgentDB cycle lineage before creating a promotion claim."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_architect_fix_candidate_gate import (
    validate_architect_fix_candidate,
)
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ACTION_FIX,
    ARCHITECT_DETERMINATION_ACCEPT,
    ARCHITECT_QUEUE_CANDIDATE_SCHEMA_VERSION,
)
from modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle import (
    STATUS_DETERMINED,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    validate_reddog_wsp15_allocation_receipt,
)


def validated_fix_promotion_binding(
    cycle: Mapping[str, Any] | None,
    determination: Mapping[str, Any] | None,
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Return immutable coordination fields only after canonical validation."""

    if not isinstance(cycle, Mapping) or cycle.get("_store_integrity_valid") is not True:
        return {}, ("cycle_integrity_invalid",)
    if not isinstance(determination, Mapping):
        return {}, ("determination_missing",)
    candidate = determination.get("queue_candidate")
    allocation = candidate.get("wsp15_allocation_receipt") if isinstance(candidate, Mapping) else None
    reasons = list(
        validate_architect_fix_candidate(
            candidate if isinstance(candidate, Mapping) else {},
            determination,
            schema_version=ARCHITECT_QUEUE_CANDIDATE_SCHEMA_VERSION,
        )
    )
    allocation_result = validate_reddog_wsp15_allocation_receipt(allocation)
    if not allocation_result.accepted:
        reasons.extend(allocation_result.rejection_reasons)
    if not _lineage_matches(cycle, determination, candidate, allocation):
        reasons.append("fix_promotion_binding_invalid")
    if reasons:
        return {}, tuple(dict.fromkeys(reasons))
    return {
        "intent_id": str(cycle["intent_id"]),
        "cycle_id": str(cycle["cycle_id"]),
        "snapshot_id": str(cycle["snapshot_id"]),
        "determination_id": str(determination["determination_receipt_id"]),
        "queue_candidate_id": str(candidate["queue_candidate_id"]),
        "wsp15_allocation_receipt_id": str(allocation["receipt_id"]),
    }, ()


def _lineage_matches(
    cycle: Mapping[str, Any],
    determination: Mapping[str, Any],
    candidate: Any,
    allocation: Any,
) -> bool:
    return bool(
        cycle.get("status") == STATUS_DETERMINED
        and cycle.get("architect_action") == ACTION_FIX
        and cycle.get("queue_candidate_count") == 1
        and determination.get("accepted") is True
        and determination.get("status") == ARCHITECT_DETERMINATION_ACCEPT
        and determination.get("action") == ACTION_FIX
        and determination.get("snapshot_receipt_id") == cycle.get("snapshot_id")
        and determination.get("determination_receipt_id")
        == cycle.get("architect_determination_id")
        and isinstance(candidate, Mapping)
        and candidate.get("status") == "CANDIDATE"
        and isinstance(allocation, Mapping)
        and allocation.get("receipt_id") == determination.get("wsp15_allocation_receipt_id")
    )


__all__ = ["validated_fix_promotion_binding"]
