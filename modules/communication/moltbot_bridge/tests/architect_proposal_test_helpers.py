"""Shared fixtures for architect proposal-admission runtime tests."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_architect_proposal_executability_admission import (
    ArchitectProposalAdmissionPolicy,
    EFFECT_NONE,
    EFFECT_READ_ONLY_AUDIT,
    EFFECT_REPOSITORY_CODE_CHANGE,
    LIVE_EXECUTION_CAPABILITIES,
)
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ACTION_FIX,
)


def architect_model_output(
    allocation: Mapping[str, Any],
    evidence_ref: str,
    *,
    action: str = ACTION_FIX,
    slice_name: str = "REDDOG_NEXT_RUNTIME_SLICE_PHASE1",
) -> dict[str, Any]:
    effect = (
        EFFECT_REPOSITORY_CODE_CHANGE
        if action == ACTION_FIX
        else EFFECT_NONE if action == "STOP" else EFFECT_READ_ONLY_AUDIT
    )
    return {
        "action": action,
        "next_slice_name": (
            slice_name if action != "STOP" else None
        ),
        "summary": "Verified reports support one next backend runtime slice.",
        "decision_reasons": ["selected verified P0 runtime gap"],
        "evidence_refs": [evidence_ref],
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "reuse_decision": "EXTEND_EXISTING",
        "requested_operation": (
            "bounded_code_change" if action == ACTION_FIX else "readonly_research"
        ),
        "target_runtime": "reddog_resident_queue",
        "target_effect_plane": effect,
        "allowed_paths": list(allocation.get("changed_paths") or ()),
        "denied_paths": [".github/workflows/**", ".env"],
        "required_tests": [
            "pytest modules/communication/moltbot_bridge/tests/test_reddog_next_runtime_slice.py"
        ],
        "required_policy_gates": ["WSP_50", "WSP_97"],
        "required_capabilities": (
            list(LIVE_EXECUTION_CAPABILITIES) if action == ACTION_FIX else []
        ),
        "produced_capabilities": [],
        "expected_evidence": ["exact_sha_test_receipt", "independent_review_receipt"],
        "stop_conditions": ["stop_before_merge"],
    }


def ready_proposal_policy() -> ArchitectProposalAdmissionPolicy:
    return ArchitectProposalAdmissionPolicy(
        platform="linux",
        available_capabilities=LIVE_EXECUTION_CAPABILITIES,
        missing_capability_reasons={},
    )


def runtime_kwargs(inputs: Mapping[str, Any]) -> dict[str, Any]:
    kwargs = {
        "snapshot": inputs["snapshot"],
        "context_view": inputs["context_view"],
        "evidence_bundle": inputs["evidence_bundle"],
        "fusion_gate": inputs["fusion_gate"],
        "report_collection": inputs["report_collection"],
        "reports": inputs["reports"],
        "proposal_admission_policy": ready_proposal_policy(),
    }
    if inputs["architect_runtime_binding"] is not None:
        kwargs["model_runtime_binding_receipt"] = inputs[
            "architect_runtime_binding"
        ]
    return kwargs


__all__ = [
    "architect_model_output",
    "ready_proposal_policy",
    "runtime_kwargs",
]
