"""Exact Holo maintenance task dispatch for OpenClaw."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_start_operations_holo_repair_capability import (
    REGISTRY,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_holo_repair_contract import (
    CLAIM_AGENT_ID,
    validate_holo_repair_task_binding,
)


def dispatch_holoindex_maintenance(repo_root: Path) -> dict[str, Any]:
    """Run the trusted exact-HEAD HoloIndex maintenance handshake."""

    try:
        from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_maintenance_handshake import (
            ensure_reddog_holoindex_operational,
        )

        result = ensure_reddog_holoindex_operational(
            repo_root=repo_root,
            requested=True,
            auto_maintenance=True,
        )
        structured = {
            "ready": result.ready,
            "status": result.status,
            "refreshed": result.refreshed,
            "error": result.error,
            "repo_head_sha": result.repo_head_sha,
            "generation_id": result.generation_id,
            "freshness_receipt_digest": result.freshness_receipt_digest,
            "freshness_reasons": list(result.freshness_reasons),
        }
        return {
            "ok": result.ready,
            "detail": json.dumps(structured, default=str)[:1000],
            "executor": "startup:holo_index",
            "structured_result": structured,
        }
    except Exception as exc:
        return {
            "ok": False,
            "detail": f"holo_index_error: {type(exc).__name__}",
            "executor": "startup:holo_index",
        }


def dispatch_start_operations_holo_repair(
    *,
    repo_root: Path,
    db: Any,
    task_id: str,
    context: Mapping[str, Any],
    execution_claim: Any,
    maintenance_runner: Callable[[Path], Mapping[str, Any]],
) -> dict[str, Any]:
    """Consume exact OpenClaw assignment authority before Holo maintenance."""

    try:
        persisted = db.get_autonomous_task_by_id(task_id)
    except Exception:
        return _rejected(["holo_repair_assignment_unavailable"])
    bound = persisted if isinstance(persisted, Mapping) else {}
    reasons = list(validate_holo_repair_task_binding(
        repo_root=repo_root, task_id=task_id, context=context
    ))
    if (
        bound.get("status") != "assigned"
        or bound.get("assigned_to") != CLAIM_AGENT_ID
        or bound.get("context") != context
    ):
        reasons.append("holo_repair_assignment_invalid")
    if reasons:
        return _rejected(reasons)
    if not REGISTRY.consume(task_id=task_id, context=context, capability=execution_claim):
        reasons.append("holo_repair_capability_invalid")
    if reasons:
        return _rejected(reasons)
    result = dict(maintenance_runner(repo_root))
    structured = dict(result.get("structured_result") or {})
    structured.update({
        "repair_task_id": task_id,
        "repair_request_id": str(context.get("repair_request_id") or ""),
    })
    return {**result, "structured_result": structured}


def _rejected(reasons: list[str]) -> dict[str, Any]:
    return {
        "ok": False,
        "detail": ",".join(reasons),
        "executor": "startup:holo_index",
        "structured_result": {
            "ready": False,
            "status": "REJECTED",
            "rejection_reasons": reasons,
        },
    }


__all__ = [
    "dispatch_holoindex_maintenance",
    "dispatch_start_operations_holo_repair",
]
