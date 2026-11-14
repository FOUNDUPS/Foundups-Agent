"""Task-store and execution helpers for start-operations Holo repair."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_start_operations_holo_repair_contract import (
    ASSIGNMENT_LEASE_SECONDS,
    CLAIM_AGENT_ID,
    REQUIRED_SKILLS,
    holo_repair_task_context,
    holo_repair_task_id,
    validate_holo_repair_task_binding,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_holo_repair_capability import (
    REGISTRY,
)


def runtime_dependencies(
    db: Any | None,
    ensure_operational: Callable[..., Any] | None,
) -> tuple[Any, Callable[..., Any]]:
    if db is None:
        from modules.infrastructure.database.src.agent_db import AgentDB

        db = AgentDB()
    if ensure_operational is None:
        from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_maintenance_handshake import (
            ensure_reddog_holoindex_operational,
        )

        ensure_operational = ensure_reddog_holoindex_operational
    return db, ensure_operational


def _assigned_expired(task: Mapping[str, Any]) -> bool:
    raw = str(task.get("assigned_at") or "")
    try:
        assigned = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return True
    if assigned.tzinfo is None:
        assigned = assigned.replace(tzinfo=UTC)
    return datetime.now(UTC) >= assigned + timedelta(
        seconds=ASSIGNMENT_LEASE_SECONDS
    )


def _recover_stale_assignment(db: Any, task_id: str, task: Mapping[str, Any]) -> bool:
    if (
        str(task.get("status") or "") != "assigned"
        or str(task.get("assigned_to") or "") != CLAIM_AGENT_ID
        or not _assigned_expired(task)
    ):
        return False
    assigned_at = str(task.get("assigned_at") or "")
    reclaimed = db.reclaim_expired_holoindex_postmerge_task(
        task_id,
        CLAIM_AGENT_ID,
        expected_assigned_at=assigned_at,
    )
    return bool(
        reclaimed
        and db.requeue_autonomous_task(task_id, expected_status="failed")
    )


def _load_task(db: Any, *, task_id: str, context: Mapping[str, Any]) -> bool:
    created = db.create_autonomous_task_if_absent(
        task_id=task_id,
        description=(
            "Restore exact-HEAD HoloIndex owner for "
            + str(context["target_repo_head_sha"])
        ),
        required_skills=REQUIRED_SKILLS,
        estimated_complexity=3.0,
        priority_score=20.0,
        context=dict(context),
    )
    persisted = db.get_autonomous_task_by_id(task_id)
    if not isinstance(persisted, Mapping) or persisted.get("context") != context:
        return False
    status = str(persisted.get("status") or "")
    return created or status == "pending" or _recover_stale_assignment(
        db, task_id, persisted
    )


def prepare_task(
    *,
    root: Path,
    repo_head_sha: str,
    control_request_id: str,
    db: Any,
) -> tuple[str, Mapping[str, Any], str]:
    context = holo_repair_task_context(
        repo_root=root,
        repo_head_sha=repo_head_sha,
        control_request_id=control_request_id,
    )
    task_id = holo_repair_task_id(context)
    reasons = validate_holo_repair_task_binding(
        repo_root=root, task_id=task_id, context=context
    )
    if reasons:
        return task_id, context, "holo_repair_request_invalid"
    if not _load_task(db, task_id=task_id, context=context):
        return task_id, context, "holo_repair_task_conflict"
    return task_id, context, ""


def execute_repair(
    *,
    root: Path,
    task_id: str,
    db: Any,
    task_executor: Callable[..., Mapping[str, Any]] | None,
) -> Mapping[str, Any] | None:
    try:
        if not db.assign_autonomous_task(task_id, CLAIM_AGENT_ID):
            return None
        persisted = db.get_autonomous_task_by_id(task_id)
        context = (
            persisted.get("context")
            if isinstance(persisted, Mapping)
            else None
        )
        capability = (
            REGISTRY.issue(task_id=task_id, context=context)
            if isinstance(context, Mapping)
            else None
        )
        if capability is None:
            return {"ok": False, "error_class": "repair_capability_issue_failed"}
        if task_executor is None:
            from modules.communication.moltbot_bridge.scripts.run_task import (
                execute_task,
            )

            task_executor = execute_task
        return task_executor(
            task_id, repo_root=root, execution_claim=capability)
    except Exception as exc:
        return {"ok": False, "error_class": type(exc).__name__}


__all__ = ["execute_repair", "prepare_task", "runtime_dependencies"]
