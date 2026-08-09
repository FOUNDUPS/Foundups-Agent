"""Shared validation for progressive-stage delegated authority bindings."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_progressive_execution_stage_policy import (
    validate_queue_progressive_stage_binding,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    canonical_reddog_wsp15_allocation_digest,
    validate_reddog_wsp15_allocation_receipt,
)


def validate_progressive_authority_binding(
    authority: Mapping[str, Any],
    *,
    expected_stage_receipt_id: Any,
    expected_stage_digest: Any,
) -> bool:
    """Recompute allocation policy and bind it to the exact signed authority."""

    allocation = authority.get("wsp15_allocation_receipt")
    stage = authority.get("progressive_policy_stage_receipt")
    if not isinstance(allocation, Mapping) or not isinstance(stage, Mapping):
        return False
    allocation_digest = canonical_reddog_wsp15_allocation_digest(allocation)
    return bool(
        validate_reddog_wsp15_allocation_receipt(allocation).accepted
        and allocation_digest == authority.get("wsp15_allocation_digest")
        and allocation.get("receipt_id")
        == authority.get("wsp15_allocation_receipt_id")
        and allocation.get("priority") == authority.get("wsp15_priority")
        and allocation.get("mps_total") == authority.get("wsp15_mps_total")
        and allocation.get("reasoning_tier")
        == authority.get("wsp15_reasoning_tier")
        and allocation.get("requested_operation")
        == authority.get("requested_operation")
        and tuple(allocation.get("changed_paths") or ())
        == tuple(authority.get("allowed_paths") or ())
        and stage.get("requested_operation") == authority.get("requested_operation")
        and tuple(stage.get("changed_paths") or ())
        == tuple(authority.get("allowed_paths") or ())
        and validate_queue_progressive_stage_binding(
            {
                "progressive_policy_stage_receipt_id": expected_stage_receipt_id,
                "progressive_policy_stage_digest": expected_stage_digest,
                "progressive_policy_stage_receipt": stage,
                "independent_verifier_required": stage.get(
                    "independent_verifier_required"
                ),
            },
            allocation,
        )
    )


__all__ = ["validate_progressive_authority_binding"]
