"""Exact-SHA AgentDB lifecycle for protected HoloIndex maintenance tasks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping

from .protected_autonomous_task_namespace import (
    HOLOINDEX_POSTMERGE_TASK_PREFIX,
    ProtectedAutonomousTaskNamespaceMixin,
    has_holoindex_postmerge_task_binding,
    has_protected_task_binding,
    is_canonical_holoindex_postmerge_task_id,
    is_holoindex_postmerge_task_id,
    is_protected_autonomous_task_id,
)


def _valid_task_binding(task_id: str, context: Mapping[str, Any]) -> bool:
    target_sha = str(context.get("target_repo_head_sha") or "")
    authority_digest = str(context.get("authority_root_digest") or "")
    return bool(
        task_id == HOLOINDEX_POSTMERGE_TASK_PREFIX + target_sha
        and is_canonical_holoindex_postmerge_task_id(task_id)
        and context.get("schema_version")
        == "holoindex_postmerge_coordination_v1"
        and context.get("source") == "holoindex_postmerge_coordinator"
        and context.get("request_event_id")
        == "holoindex_postmerge_requested:" + target_sha
        and authority_digest.startswith("sha256:")
        and len(authority_digest) == 71
        and all(char in "0123456789abcdef" for char in authority_digest[7:])
    )


def _stored_binding(
    owner: Any, task_id: str, expected_status: str
) -> tuple[str, dict[str, Any]] | None:
    rows = owner.db.execute_query(
        "SELECT status, context FROM agents_autonomous_tasks WHERE task_id = ?",
        (task_id,),
    )
    if not rows or str(rows[0].get("status") or "") != expected_status:
        return None
    raw_context = str(rows[0].get("context") or "")
    try:
        context = json.loads(raw_context)
    except (TypeError, ValueError):
        return None
    if not isinstance(context, dict) or not _valid_task_binding(task_id, context):
        return None
    return raw_context, context


def create_holoindex_postmerge_task_if_absent(
    owner: Any,
    *,
    task_id: str,
    description: str,
    required_skills: list[str],
    estimated_complexity: float,
    priority_score: float,
    context: dict[str, Any],
) -> bool:
    if not _valid_task_binding(task_id, context):
        return False
    return owner.db.execute_write(
        "INSERT OR IGNORE INTO agents_autonomous_tasks "
        "(task_id, description, required_skills, estimated_complexity, "
        "priority_score, context) VALUES (?, ?, ?, ?, ?, ?)",
        (
            task_id, description, json.dumps(required_skills),
            estimated_complexity, priority_score, json.dumps(context),
        ),
    ) > 0


def _retry_context_valid(
    stored: Mapping[str, Any], supplied: Mapping[str, Any], retry_at: str
) -> bool:
    mutable = {"retry_count", "retry_not_before"}
    old = {key: value for key, value in stored.items() if key not in mutable}
    new = {key: value for key, value in supplied.items() if key not in mutable}
    try:
        sequence_valid = int(supplied.get("retry_count")) == int(
            stored.get("retry_count") or 0
        ) + 1
    except (TypeError, ValueError):
        sequence_valid = False
    return old == new and sequence_valid and supplied.get("retry_not_before") == retry_at


def schedule_holoindex_postmerge_task_retry(
    owner: Any, task_id: str, *, context: dict[str, Any], retry_not_before: str
) -> bool:
    stored = _stored_binding(owner, task_id, "failed")
    if stored is None or not _valid_task_binding(task_id, context):
        return False
    raw_context, stored_context = stored
    if not _retry_context_valid(stored_context, context, retry_not_before):
        return False
    return owner.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'retry_wait', context = ?, "
        "retry_not_before = ?, assigned_to = NULL, assigned_at = NULL "
        "WHERE task_id = ? AND status = 'failed' AND context = ?",
        (json.dumps(context), retry_not_before, task_id, raw_context),
    ) > 0


def requeue_holoindex_postmerge_task(
    owner: Any, task_id: str, *, expected_status: str = "retry_wait"
) -> bool:
    stored = _stored_binding(owner, task_id, expected_status)
    if stored is None:
        return False
    raw_context, _ = stored
    return owner.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'pending', "
        "retry_not_before = NULL, assigned_to = NULL, assigned_at = NULL, "
        "completed_at = NULL WHERE task_id = ? AND status = ? AND context = ?",
        (task_id, expected_status, raw_context),
    ) > 0


def reclaim_expired_holoindex_postmerge_task(
    owner: Any, task_id: str, agent_id: str, *, expected_assigned_at: str
) -> bool:
    stored = _stored_binding(owner, task_id, "assigned")
    if stored is None:
        stored = _stored_binding(owner, task_id, "executing")
    if stored is None:
        return False
    raw_context, _ = stored
    return owner.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'failed', completed_at = ? "
        "WHERE task_id = ? AND status IN ('assigned', 'executing') "
        "AND assigned_to = ? AND assigned_at = ? AND context = ?",
        (
            datetime.now(timezone.utc).isoformat(), task_id, agent_id,
            expected_assigned_at, raw_context,
        ),
    ) == 1


class HoloIndexPostmergeTaskNamespaceMixin(ProtectedAutonomousTaskNamespaceMixin):
    create_holoindex_postmerge_task_if_absent = create_holoindex_postmerge_task_if_absent
    reclaim_expired_holoindex_postmerge_task = reclaim_expired_holoindex_postmerge_task
    requeue_holoindex_postmerge_task = requeue_holoindex_postmerge_task
    schedule_holoindex_postmerge_task_retry = schedule_holoindex_postmerge_task_retry


__all__ = [
    "HOLOINDEX_POSTMERGE_TASK_PREFIX",
    "HoloIndexPostmergeTaskNamespaceMixin",
    "has_holoindex_postmerge_task_binding",
    "has_protected_task_binding",
    "is_canonical_holoindex_postmerge_task_id",
    "is_holoindex_postmerge_task_id",
    "is_protected_autonomous_task_id",
]
