"""Reserved AgentDB namespace for exact-SHA HoloIndex maintenance tasks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping

from .signed_worker_execution_store import is_signed_worker_task_id


HOLOINDEX_POSTMERGE_TASK_PREFIX = "holoindex_postmerge_refresh:"


def is_holoindex_postmerge_task_id(task_id: str) -> bool:
    """Return whether a task occupies the protected post-merge namespace."""

    return str(task_id or "").startswith(HOLOINDEX_POSTMERGE_TASK_PREFIX)


def is_canonical_holoindex_postmerge_task_id(task_id: str) -> bool:
    """Return whether a task is the exact prefix plus lowercase Git SHA."""

    value = str(task_id or "")
    suffix = value.removeprefix(HOLOINDEX_POSTMERGE_TASK_PREFIX)
    return bool(
        value.startswith(HOLOINDEX_POSTMERGE_TASK_PREFIX)
        and len(suffix) == 40
        and all(char in "0123456789abcdef" for char in suffix)
    )


def is_protected_autonomous_task_id(task_id: str) -> bool:
    """Return whether generic AgentDB mutation APIs must reject the task."""

    return is_signed_worker_task_id(task_id) or is_holoindex_postmerge_task_id(
        task_id
    )


def _valid_task_binding(
    task_id: str,
    context: Mapping[str, Any],
) -> bool:
    target_sha = str(context.get("target_repo_head_sha") or "")
    authority_digest = str(context.get("authority_root_digest") or "")
    return bool(
        task_id == HOLOINDEX_POSTMERGE_TASK_PREFIX + target_sha
        and len(target_sha) == 40
        and all(char in "0123456789abcdef" for char in target_sha)
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
    owner: Any,
    task_id: str,
    expected_status: str,
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
    """Insert one protected post-merge task without replacing state."""
    if not _valid_task_binding(task_id, context):
        return False
    return owner.db.execute_write(
        """
        INSERT OR IGNORE INTO agents_autonomous_tasks
        (task_id, description, required_skills, estimated_complexity,
         priority_score, context)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            task_id, description, json.dumps(required_skills),
            estimated_complexity, priority_score, json.dumps(context),
        ),
    ) > 0


def schedule_holoindex_postmerge_task_retry(
    owner: Any,
    task_id: str,
    *,
    context: dict[str, Any],
    retry_not_before: str,
) -> bool:
    """Schedule retry through the protected post-merge lane only."""
    stored = _stored_binding(owner, task_id, "failed")
    if stored is None or not _valid_task_binding(task_id, context):
        return False
    raw_context, _ = stored
    return owner.db.execute_write(
        """
        UPDATE agents_autonomous_tasks
        SET status = 'retry_wait', context = ?, retry_not_before = ?,
            assigned_to = NULL, assigned_at = NULL
        WHERE task_id = ? AND status = 'failed' AND context = ?
        """,
        (json.dumps(context), retry_not_before, task_id, raw_context),
    ) > 0


def requeue_holoindex_postmerge_task(
    owner: Any,
    task_id: str,
    *,
    expected_status: str = "retry_wait",
) -> bool:
    """Requeue only a protected exact-SHA post-merge task."""
    stored = _stored_binding(owner, task_id, expected_status)
    if stored is None:
        return False
    raw_context, _ = stored
    return owner.db.execute_write(
        """
        UPDATE agents_autonomous_tasks
        SET status = 'pending', retry_not_before = NULL,
            assigned_to = NULL, assigned_at = NULL, completed_at = NULL
        WHERE task_id = ? AND status = ? AND context = ?
        """,
        (task_id, expected_status, raw_context),
    ) > 0


def reclaim_expired_holoindex_postmerge_task(
    owner: Any,
    task_id: str,
    agent_id: str,
    *,
    expected_assigned_at: str,
) -> bool:
    """CAS one expired protected assignment into retryable failure."""
    stored = _stored_binding(owner, task_id, "assigned")
    if stored is None:
        stored = _stored_binding(owner, task_id, "executing")
    if stored is None:
        return False
    raw_context, _ = stored
    return owner.db.execute_write(
        """
        UPDATE agents_autonomous_tasks
        SET status = 'failed', completed_at = ?
        WHERE task_id = ? AND status IN ('assigned', 'executing')
          AND assigned_to = ? AND assigned_at = ? AND context = ?
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            task_id,
            agent_id,
            expected_assigned_at,
            raw_context,
        ),
    ) == 1


class HoloIndexPostmergeTaskNamespaceMixin:
    """Compatibility surface for AgentDB's protected post-merge operations."""

    create_holoindex_postmerge_task_if_absent = create_holoindex_postmerge_task_if_absent
    reclaim_expired_holoindex_postmerge_task = reclaim_expired_holoindex_postmerge_task
    schedule_holoindex_postmerge_task_retry = schedule_holoindex_postmerge_task_retry
    requeue_holoindex_postmerge_task = requeue_holoindex_postmerge_task


__all__ = [
    "HOLOINDEX_POSTMERGE_TASK_PREFIX",
    "HoloIndexPostmergeTaskNamespaceMixin",
    "create_holoindex_postmerge_task_if_absent",
    "is_canonical_holoindex_postmerge_task_id",
    "is_holoindex_postmerge_task_id",
    "is_protected_autonomous_task_id",
    "reclaim_expired_holoindex_postmerge_task",
    "requeue_holoindex_postmerge_task",
    "schedule_holoindex_postmerge_task_retry",
]
