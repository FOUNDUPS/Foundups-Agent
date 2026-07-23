"""Canonical provider-call evidence fixtures for RedDog integration tests."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_provider_call_evidence import (
    ProviderCallOutcome,
    ProviderCallReason,
    arm_provider_call,
    create_precall_evidence,
    terminalize_provider_call,
)


def audit_provider_call_evidence(
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    model_selection = binding.get("model_selection")
    return _completed_provider_call_evidence(
        model_selection if isinstance(model_selection, Mapping) else {},
        surface="reddog_readonly_audit_worker",
        task_id=str(binding.get("task_id") or "") or None,
        cycle_id=None,
    )


def architect_provider_call_evidence(
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    topology = binding.get("model_selection")
    return _completed_provider_call_evidence(
        topology if isinstance(topology, Mapping) else {},
        surface="reddog_backend_architect",
        task_id=None,
        cycle_id=str(binding.get("cycle_id") or ""),
    )


def _completed_provider_call_evidence(
    topology: Mapping[str, Any],
    *,
    surface: str,
    task_id: str | None,
    cycle_id: str | None,
) -> dict[str, Any]:
    precall = create_precall_evidence(
        surface=surface,
        task_id=task_id,
        work_order_id=None,
        queue_item_id=None,
        run_id=None,
        cycle_id=cycle_id,
        requested_provider="openrouter",
        requested_model=str(topology.get("lead_model") or ""),
        redacted_input_digest="sha256:" + "a" * 64,
        model_runtime_binding_receipt_id=str(
            topology.get("model_runtime_binding_receipt_id") or ""
        ),
        model_runtime_binding_digest=str(
            topology.get("model_runtime_binding_digest") or ""
        ),
        request_metadata={"fixture": True},
        started_at_ms=100,
    )
    return terminalize_provider_call(
        arm_provider_call(precall),
        outcome=ProviderCallOutcome.COMPLETED,
        reason=ProviderCallReason.PROVIDER_RETURNED,
        completed_at_ms=101,
    ).to_dict()
