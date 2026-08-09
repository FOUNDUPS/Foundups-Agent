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
from modules.communication.moltbot_bridge.src.reddog_signer_optional_authority_bindings import (
    is_sha256_digest,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
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
        and stage.get("selected_slice") == authority.get("selected_slice")
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


def _request_receipt_bindings_valid(request: Any) -> bool:
    queue_receipt = request.queue_consumer_receipt
    stage = request.progressive_policy_stage_receipt
    return bool(
        isinstance(queue_receipt, Mapping)
        and canonical_full_work_order_digest(queue_receipt)
        == request.queue_consumer_receipt_digest
        and str(queue_receipt.get("slice_id") or "")
        == str(stage.get("selected_slice") or "")
        and queue_receipt.get("wsp15_allocation_receipt_id")
        == request.wsp15_allocation_receipt_id
        and queue_receipt.get("wsp15_allocation_digest")
        == request.wsp15_allocation_digest
        and queue_receipt.get("progressive_policy_stage_receipt_id")
        == request.progressive_policy_stage_receipt_id
        and queue_receipt.get("progressive_policy_stage_digest")
        == request.progressive_policy_stage_digest
        and is_sha256_digest(request.queue_consumer_receipt_digest)
        and request.wsp15_allocation_receipt_id.startswith("sha256:")
        and request.wsp15_allocation_digest.startswith("sha256:")
        and request.wsp15_priority in {"P0", "P1", "P2", "P3", "P4"}
        and type(request.wsp15_mps_total) is int
        and request.wsp15_reasoning_tier in {"REGULAR", "HIGH", "ULTRA"}
        and is_sha256_digest(request.progressive_policy_stage_receipt_id)
        and is_sha256_digest(request.progressive_policy_stage_digest)
    )


def validate_progressive_runtime_request(request: Any) -> bool:
    """Validate queue receipt, allocation, stage, and selected-slice lineage."""

    try:
        authority = request.to_dict()
        authority["selected_slice"] = str(
            request.queue_consumer_receipt.get("slice_id") or ""
        )
        return bool(
            _request_receipt_bindings_valid(request)
            and validate_progressive_authority_binding(
                authority,
                expected_stage_receipt_id=(
                    request.progressive_policy_stage_receipt_id
                ),
                expected_stage_digest=request.progressive_policy_stage_digest,
            )
        )
    except (AttributeError, TypeError, ValueError):
        return False


__all__ = [
    "validate_progressive_authority_binding",
    "validate_progressive_runtime_request",
]
