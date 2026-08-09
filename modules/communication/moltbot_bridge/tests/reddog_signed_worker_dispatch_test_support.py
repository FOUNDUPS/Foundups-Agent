"""Focused fixtures for signed worker progressive-stage tests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)
from modules.communication.moltbot_bridge.src import (
    reddog_progressive_execution_stage_policy as stage_policy,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    governed_worker_dispatch_snapshot,
)


_DEFAULT_PROMPT = "Fix one bounded RedDog FoundUp module defect"
_DEFAULT_TARGET = "modules/foundups/paccess_001/src/worker.py"
_ALLOCATION_PROMPTS: dict[str, str] = {}


def signed_bounded_stage_receipt(
    *,
    requested_operation: str = "bounded_module_fix",
    changed_paths: Sequence[str] = (_DEFAULT_TARGET,),
) -> dict[str, object]:
    """Build a self-consistent admitted stage for authority-chain tests."""

    unsigned: dict[str, object] = {
        "schema_version": stage_policy.SCHEMA_VERSION,
        "receipt_id": "",
        "stage": stage_policy.STAGE_BOUNDED_EXECUTION,
        "decision": stage_policy.DECISION_BOUNDED_EXECUTION_ADMITTED,
        "determination_action": "FIX",
        "selected_slice": "REDDOG_TEST_SLICE_PHASE1",
        "requested_operation": requested_operation,
        "changed_paths": tuple(changed_paths),
        "wsp15_allocation_receipt_id": "sha256:wsp15-allocation",
        "wsp15_allocation_digest": "sha256:wsp15-allocation-digest",
        "complexity": 2,
        "risk_classes": (),
        "would_block_reasons": (),
        "rejection_reasons": (),
        "no_effect_authority": False,
        "independent_verifier_required": True,
        "production_authority_granted": False,
    }
    unsigned["receipt_id"] = stage_policy._digest(stage_policy._unsigned(unsigned))
    return unsigned


def signed_stage_binding(
    *,
    requested_operation: str = "bounded_module_fix",
    changed_paths: Sequence[str] = (_DEFAULT_TARGET,),
) -> dict[str, object]:
    receipt = signed_bounded_stage_receipt(
        requested_operation=requested_operation,
        changed_paths=changed_paths,
    )
    return {
        "progressive_policy_stage_receipt_id": receipt["receipt_id"],
        "progressive_policy_stage_digest": stage_policy._digest(receipt),
        "progressive_policy_stage_receipt": receipt,
    }


def signed_audit_stage_binding() -> dict[str, object]:
    operation = "signed_0102_readonly_review:foundup_module"
    unsigned: dict[str, object] = {
        "schema_version": stage_policy.SCHEMA_VERSION,
        "receipt_id": "",
        "stage": stage_policy.STAGE_AUDIT,
        "decision": stage_policy.DECISION_AUDIT_CONTINUES,
        "determination_action": "AUDIT",
        "selected_slice": "REDDOG_READONLY_AUDIT_PHASE1",
        "requested_operation": operation,
        "changed_paths": (),
        "wsp15_allocation_receipt_id": "sha256:wsp15-readonly",
        "wsp15_allocation_digest": "sha256:wsp15-readonly-digest",
        "complexity": 1,
        "risk_classes": (),
        "would_block_reasons": (),
        "rejection_reasons": (),
        "no_effect_authority": True,
        "independent_verifier_required": False,
        "production_authority_granted": False,
    }
    unsigned["receipt_id"] = stage_policy._digest(stage_policy._unsigned(unsigned))
    return {
        "progressive_policy_stage_receipt_id": unsigned["receipt_id"],
        "progressive_policy_stage_digest": stage_policy._digest(unsigned),
        "progressive_policy_stage_receipt": unsigned,
    }


def bounded_allocation(*, prompt_suffix: str = "", **overrides: object) -> dict[str, object]:
    """Build a canonical bounded allocation and retain its exact prompt."""
    prompt = f"{_DEFAULT_PROMPT} {prompt_suffix}".strip()
    payload = allocate_reddog_wsp15_receipt(
        requested_operation="edit_foundup_module",
        prompt_text=prompt,
        changed_paths=(_DEFAULT_TARGET,),
        allowed_read_targets=(_DEFAULT_TARGET,),
    ).to_dict()
    payload.update(overrides)
    _ALLOCATION_PROMPTS[str(payload.get("receipt_id") or "")] = prompt
    return payload


def readonly_allocation(
    *,
    targets: Sequence[str] = (_DEFAULT_TARGET,),
    runtime_binding: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build a canonical no-effects allocation for a signed 0102 audit."""
    prompt = "RedDog OpenClaw signed 0102 read-only review runtime security audit."
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation="signed_0102_readonly_review:redDog_runtime_security",
        prompt_text=prompt,
        allowed_read_targets=targets,
        model_runtime_binding_receipt=runtime_binding,
    ).to_dict()
    _ALLOCATION_PROMPTS[str(allocation["receipt_id"])] = prompt
    return allocation


def governed_snapshot(
    allocation: dict[str, object] | None = None,
    **queue_overrides: object,
) -> dict[str, object]:
    """Bind the exact allocation prompt into a governed queue snapshot."""
    resolved = allocation or bounded_allocation()
    task_prompt = _ALLOCATION_PROMPTS.get(
        str(resolved.get("receipt_id") or ""),
        _DEFAULT_PROMPT,
    )
    queue_item = {
        "queue_item_id": "queue-1",
        "slice_id": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
        "status": "QUEUED",
        "wsp15_allocation_receipt": resolved,
        **queue_overrides,
    }
    return governed_worker_dispatch_snapshot(
        {
            "schema_version": "reddog_authoritative_work_state.v1",
            "wre_queue_items": [queue_item],
        },
        task_prompt_text=task_prompt,
    )
