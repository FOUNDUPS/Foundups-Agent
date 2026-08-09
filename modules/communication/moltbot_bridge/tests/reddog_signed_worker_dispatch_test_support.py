"""Focused fixtures for signed worker progressive-stage tests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    governed_worker_dispatch_snapshot,
)


_DEFAULT_PROMPT = "Fix one bounded RedDog FoundUp module defect"
_DEFAULT_TARGET = "modules/foundups/paccess_001/src/worker.py"
_ALLOCATION_PROMPTS: dict[str, str] = {}


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
