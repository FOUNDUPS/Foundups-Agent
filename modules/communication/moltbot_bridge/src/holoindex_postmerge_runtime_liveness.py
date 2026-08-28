"""Fail-closed liveness and binding checks for one exact HoloIndex task."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from modules.infrastructure.idle_automation.src.holoindex_postmerge_contract import (
    ASSIGNMENT_LEASE_SECONDS,
    CLAIM_AGENT_ID,
    TASK_PREFIX,
    holoindex_postmerge_task_binding_valid,
)
from modules.infrastructure.database.src.holoindex_postmerge_claim_contract import (
    holoindex_postmerge_claim_binding_valid,
)


_LIVE_RUNTIME_STATES = frozenset({"starting", "running", "degraded"})
_ACTIVE_TASK_STATES = frozenset({"pending", "assigned", "executing"})
_SUPERVISOR_BINDING_TIMEOUT_SECONDS = 60.0
_TASK_PHASE_TIMEOUT_SECONDS = {
    "pending": 60.0,
    "assigned": 60.0,
    "executing": float(ASSIGNMENT_LEASE_SECONDS),
}


def _runtime_rejection(broker: Any, runtime_id: str) -> str:
    try:
        status = broker.get_runtime_status(runtime_id)
    except Exception:
        return f"{runtime_id}_status_unavailable"
    if not isinstance(status, Mapping) or status.get("registered") is not True:
        return f"{runtime_id}_not_registered"
    if status.get("last_error"):
        return f"{runtime_id}_runtime_error"
    if not (
        status.get("running") is True
        and status.get("thread_alive") is True
        and status.get("state") in _LIVE_RUNTIME_STATES
    ):
        return f"{runtime_id}_not_live"
    return ""


def _claim_rejection(task: Mapping[str, Any], status: str) -> str:
    if status not in {"assigned", "executing"}:
        return ""
    context = task["context"]
    if holoindex_postmerge_claim_binding_valid(
        task_id=str(task.get("task_id") or ""),
        agent_id=CLAIM_AGENT_ID,
        assigned_at=task.get("assigned_at"),
        context=context,
        require_active=True,
    ):
        return ""
    if holoindex_postmerge_claim_binding_valid(
        task_id=str(task.get("task_id") or ""),
        agent_id=CLAIM_AGENT_ID,
        assigned_at=task.get("assigned_at"),
        context=context,
        require_expired=True,
    ):
        return "postmerge_task_claim_expired"
    return "postmerge_task_claim_invalid"


def _task_binding_rejection(
    task: Mapping[str, Any], task_id: str, head: str, authority_root_digest: str,
) -> str:
    context = task.get("context")
    status = str(task.get("status") or "")
    if status in {"failed", "superseded", "cancelled"}:
        return f"postmerge_task_{status}"
    if status == "completed":
        return "postmerge_completion_invalid"
    assigned_to = str(task.get("assigned_to") or "")
    expected = CLAIM_AGENT_ID if status in {"assigned", "executing"} else ""
    if assigned_to != expected:
        return "postmerge_task_assignment_invalid"
    if not isinstance(context, Mapping) or not (
        task.get("task_id") == task_id
        and task_id == TASK_PREFIX + head
        and holoindex_postmerge_task_binding_valid(
            task,
            target_repo_head_sha=head,
            authority_root_digest=authority_root_digest,
        )
    ):
        return "postmerge_task_binding_invalid"
    if status == "retry_wait":
        return "postmerge_task_retry_wait"
    if status not in _ACTIVE_TASK_STATES:
        return "postmerge_task_status_invalid"
    return _claim_rejection(task, status)


def _progress_marker(task: Mapping[str, Any]) -> str:
    context = task.get("context") if isinstance(task.get("context"), Mapping) else {}
    payload = {
        "status": str(task.get("status") or ""),
        "assigned_at": str(task.get("assigned_at") or ""),
        "claim_id": str(context.get("claim_id") or ""),
        "claim_binding_digest": str(context.get("claim_binding_digest") or ""),
        "claim_expires_at": str(context.get("claim_expires_at") or ""),
        "retry_count": context.get("retry_count"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def holoindex_postmerge_runtime_inspection(
    broker: Any, database: Any, *, task_id: str, expected_head: str,
    expected_authority_root_digest: str,
) -> tuple[str, str, float]:
    """Return rejection, secret-free progress marker, and phase deadline."""

    for runtime_id in ("openclaw", "openclaw_supervisor"):
        rejection = _runtime_rejection(broker, runtime_id)
        if rejection:
            return rejection, "", 0.0
    try:
        task = database.get_autonomous_task_by_id(task_id)
    except Exception:
        return "postmerge_task_status_unavailable", "", 0.0
    if not isinstance(task, Mapping):
        return "postmerge_task_missing", "", 0.0
    status = str(task.get("status") or "")
    return (
        _task_binding_rejection(
            task, task_id, expected_head, expected_authority_root_digest,
        ),
        _progress_marker(task),
        _TASK_PHASE_TIMEOUT_SECONDS.get(status, 0.0),
    )


def holoindex_postmerge_runtime_rejection(
    broker: Any, database: Any, *, task_id: str, expected_head: str,
    expected_authority_root_digest: str,
) -> str:
    """Return one stable rejection code, or empty text while work is live."""

    return holoindex_postmerge_runtime_inspection(
        broker, database, task_id=task_id, expected_head=expected_head,
        expected_authority_root_digest=expected_authority_root_digest,
    )[0]


def wait_for_supervisor_binding(
    binder: Callable[[str, Path], str], task_id: str, expected_root: Path, *,
    broker: Any, database: Any, expected_head: str,
    expected_authority_root_digest: str, deadline: float,
    clock: Callable[[], float], sleeper: Callable[[float], None], interval: float,
) -> str:
    """Wait briefly for an attested live supervisor to bind the exact task."""

    bind_deadline = min(deadline, clock() + _SUPERVISOR_BINDING_TIMEOUT_SECONDS)
    while clock() < bind_deadline:
        try:
            status = binder(task_id, expected_root)
        except BaseException:
            return "postmerge_task_binding_exception"
        if status == "bound":
            return ""
        if status != "not_ready":
            return "postmerge_task_binding_rejected"
        rejection, _, _ = holoindex_postmerge_runtime_inspection(
            broker, database, task_id=task_id, expected_head=expected_head,
            expected_authority_root_digest=expected_authority_root_digest,
        )
        if rejection:
            return rejection
        sleeper(interval)
    return "postmerge_task_binding_timeout"


def release_supervisor_binding(
    releaser: Callable[[str, Path], str], task_id: str, expected_root: Path,
) -> str:
    """Release exactly the controller-owned task binding or fail closed."""

    try:
        status = releaser(task_id, expected_root)
    except BaseException:
        return "postmerge_task_release_exception"
    return "" if status == "released" else "postmerge_task_release_rejected"


def run_with_supervisor_binding_release(
    operation: Callable[[], tuple[Mapping[str, Any] | None, str]],
    releaser: Callable[[str, Path], str], task_id: str, expected_root: Path,
) -> tuple[Mapping[str, Any] | None, str]:
    """Run one bound operation and prove release on every exit path."""

    try:
        result = operation()
    except BaseException:
        release_reason = release_supervisor_binding(
            releaser, task_id, expected_root,
        )
        if release_reason:
            return None, release_reason
        raise
    release_reason = release_supervisor_binding(releaser, task_id, expected_root)
    return (None, release_reason) if release_reason else result


def preexisting_runtime_topology(broker: Any) -> str:
    active = [
        bool(status.get("thread_alive") or status.get("running"))
        for status in (
            broker.get_runtime_status("openclaw"),
            broker.get_runtime_status("openclaw_supervisor"),
        )
    ]
    return "all" if all(active) else "partial" if any(active) else "none"


__all__ = [
    "holoindex_postmerge_runtime_inspection",
    "holoindex_postmerge_runtime_rejection",
    "preexisting_runtime_topology",
    "release_supervisor_binding",
    "run_with_supervisor_binding_release",
    "wait_for_supervisor_binding",
]
