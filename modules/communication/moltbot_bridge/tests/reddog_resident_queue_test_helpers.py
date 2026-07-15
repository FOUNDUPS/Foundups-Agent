"""Shared resident queue test fixtures."""

from __future__ import annotations

from typing import Any

from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)


WORKER_DISPATCH_DRYRUN_STAGE_RESULT = {
    "decision": "SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT",
}


def queue_wsp15_allocation_receipt(*, prompt_text: str = "RedDog resident queue worktree authority") -> dict[str, Any]:
    return allocate_reddog_wsp15_receipt(
        requested_operation="create_foundup",
        prompt_text=prompt_text,
        changed_paths=("modules/communication/moltbot_bridge/src/reddog_resident_queue_orchestration_plan.py",),
        allowed_read_targets=("modules/communication/moltbot_bridge/src/reddog_resident_queue_orchestration_plan.py",),
    ).to_dict()


def with_queue_wsp15_allocation(queue_item: dict[str, Any], *, prompt_text: str = "RedDog resident queue worktree authority") -> dict[str, Any]:
    allocation = queue_wsp15_allocation_receipt(prompt_text=prompt_text)
    item = dict(queue_item)
    refs = [str(ref) for ref in item.get("evidence_refs") or ()]
    refs.extend(
        [
            f"wsp15_allocation:{allocation['receipt_id']}",
        ]
    )
    item["evidence_refs"] = list(dict.fromkeys(refs))
    item["wsp15_allocation_receipt"] = allocation
    return item
