"""Generic mutation boundary for reserved AgentDB task namespaces."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Mapping

from .signed_worker_execution_store import is_signed_worker_task_id


HOLOINDEX_POSTMERGE_TASK_PREFIX = "holoindex_postmerge_refresh:"


def is_holoindex_postmerge_task_id(task_id: str) -> bool:
    return str(task_id or "").startswith(HOLOINDEX_POSTMERGE_TASK_PREFIX)


def is_canonical_holoindex_postmerge_task_id(task_id: str) -> bool:
    value = str(task_id or "")
    suffix = value.removeprefix(HOLOINDEX_POSTMERGE_TASK_PREFIX)
    return bool(
        value.startswith(HOLOINDEX_POSTMERGE_TASK_PREFIX)
        and len(suffix) == 40
        and all(char in "0123456789abcdef" for char in suffix)
    )


def is_protected_autonomous_task_id(task_id: str) -> bool:
    return is_signed_worker_task_id(task_id) or is_holoindex_postmerge_task_id(
        task_id
    )


def has_protected_task_binding(value: Mapping[str, Any]) -> bool:
    return any(
        is_protected_autonomous_task_id(str(value.get(field) or ""))
        for field in ("author_task_id", "verifier_task_id")
    )


def has_holoindex_postmerge_task_binding(value: Mapping[str, Any]) -> bool:
    return any(
        is_holoindex_postmerge_task_id(str(value.get(field) or ""))
        for field in ("author_task_id", "verifier_task_id")
    )


def complete_autonomous_task(owner: Any, task_id: str) -> bool:
    """Complete an ordinary task without crossing a protected namespace."""
    if is_protected_autonomous_task_id(task_id):
        return False
    return owner.db.execute_write(
        "UPDATE agents_autonomous_tasks SET completed_at = ?, status = 'completed' "
        "WHERE task_id = ?",
        (datetime.now().isoformat(), task_id),
    ) > 0


def schedule_autonomous_task_retry(
    owner: Any,
    task_id: str,
    *,
    context: dict[str, Any],
    retry_not_before: str,
) -> bool:
    """Schedule an ordinary failed task without crossing protected lanes."""
    if is_protected_autonomous_task_id(task_id):
        return False
    return owner.db.execute_write(
        """
        UPDATE agents_autonomous_tasks
        SET status = 'retry_wait', context = ?, retry_not_before = ?,
            assigned_to = NULL, assigned_at = NULL
        WHERE task_id = ? AND status = 'failed'
        """,
        (json.dumps(context), retry_not_before, task_id),
    ) > 0


def requeue_autonomous_task(
    owner: Any,
    task_id: str,
    *,
    expected_status: str = "retry_wait",
) -> bool:
    """Requeue an ordinary task without crossing protected lanes."""
    if is_protected_autonomous_task_id(task_id):
        return False
    return owner.db.execute_write(
        """
        UPDATE agents_autonomous_tasks
        SET status = 'pending', retry_not_before = NULL,
            assigned_to = NULL, assigned_at = NULL, completed_at = NULL
        WHERE task_id = ? AND status = ?
        """,
        (task_id, expected_status),
    ) > 0


class ProtectedAutonomousTaskNamespaceMixin:
    """Compatibility surface for ordinary AgentDB task mutations."""

    complete_autonomous_task = complete_autonomous_task
    requeue_autonomous_task = requeue_autonomous_task
    schedule_autonomous_task_retry = schedule_autonomous_task_retry


__all__ = [
    "HOLOINDEX_POSTMERGE_TASK_PREFIX",
    "ProtectedAutonomousTaskNamespaceMixin",
    "has_holoindex_postmerge_task_binding",
    "has_protected_task_binding",
    "is_canonical_holoindex_postmerge_task_id",
    "is_holoindex_postmerge_task_id",
    "is_protected_autonomous_task_id",
]
