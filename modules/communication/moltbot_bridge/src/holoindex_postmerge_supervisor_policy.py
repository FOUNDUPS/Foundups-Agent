"""OpenClaw policy for the exact-SHA HoloIndex post-merge task family."""

from __future__ import annotations

import os
import re
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


HOLOINDEX_POSTMERGE_SOURCE = "holoindex_postmerge_coordinator"
HOLOINDEX_POSTMERGE_TASK_PREFIX = "holoindex_postmerge_refresh:"
HOLOINDEX_POSTMERGE_ONLY_MODE = "holoindex_postmerge_only"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def is_holoindex_postmerge_only_mode(runtime_mode: str | None) -> bool:
    if runtime_mode not in {None, HOLOINDEX_POSTMERGE_ONLY_MODE}:
        raise ValueError("openclaw_supervisor_runtime_mode_invalid")
    return runtime_mode == HOLOINDEX_POSTMERGE_ONLY_MODE


def holoindex_postmerge_only_execution_rejection(
    *, enabled: bool, plan: Any,
) -> Dict[str, Any] | None:
    if not enabled:
        return None
    if not isinstance(plan, Mapping):
        return {
            "ok": False,
            "status": "rejected",
            "error": "holoindex_postmerge_only_plan_rejected",
        }
    task = plan.get("task")
    context = task.get("context") if isinstance(task, Mapping) else None
    allowed = bool(
        plan.get("action") == "execute_maintenance_task"
        and isinstance(task, Mapping)
        and task.get("family") == "holoindex_postmerge"
        and task.get("source") == HOLOINDEX_POSTMERGE_SOURCE
        and isinstance(context, Mapping)
        and context.get("source") == HOLOINDEX_POSTMERGE_SOURCE
        and is_canonical_holoindex_postmerge_task_id(task.get("task_id"))
    )
    return None if allowed else {
        "ok": False, "status": "rejected",
        "error": "holoindex_postmerge_only_plan_rejected",
    }


class HoloIndexPostmergePoller:
    """Own one bounded coordinator worker and its shutdown boundary."""

    def __init__(self, repo_root: Path, *, enabled: bool | None = None) -> None:
        self._repo_root = repo_root.resolve()
        self._enabled = enabled
        self._lock = threading.Lock()
        self._executor: ThreadPoolExecutor | None = None
        self._future: Future[Any] | None = None
        self._last_poll = 0.0
        self._stopped = False
        self._task_id = ""

    @property
    def future(self) -> Future[Any] | None:
        with self._lock:
            return self._future

    @property
    def task_id(self) -> str:
        with self._lock:
            return self._task_id

    def poll(self) -> Dict[str, Any] | None:
        with self._lock:
            if self._stopped:
                return _poll_status(False, "OWNER_STOPPED", "supervisor_stopped")
            completed = self._completed_result()
            if completed is not None:
                return completed
            enabled = (
                holoindex_postmerge_enabled()
                if self._enabled is None
                else self._enabled
            )
            if not enabled:
                return _poll_status(False, "OWNER_DISABLED", "postmerge_coordinator_disabled")
            if self._future is not None or not self._poll_due():
                return None
            self._schedule()
            return _poll_status(True, "MAINTENANCE_CHECK_SCHEDULED")

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            executor = self._executor
            self._executor = None
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)
        with self._lock:
            self._future = None

    def _completed_result(self) -> Dict[str, Any] | None:
        if self._future is None or not self._future.done():
            return None
        try:
            result = dict(self._future.result().to_dict())
            self._task_id = _canonical_task_id(result)
            return result
        except Exception as exc:
            return _poll_status(False, "REJECTED", type(exc).__name__)
        finally:
            self._future = None

    def _poll_due(self) -> bool:
        try:
            interval = max(
                float(os.getenv("HOLOINDEX_POSTMERGE_COORDINATOR_INTERVAL_SEC", "300")),
                30.0,
            )
        except ValueError:
            interval = 300.0
        return not self._last_poll or time.monotonic() - self._last_poll >= interval

    def _schedule(self) -> None:
        from modules.infrastructure.idle_automation.src.holoindex_postmerge_coordinator import (
            coordinate_holoindex_postmerge,
        )

        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="holoindex-postmerge",
            )
        self._last_poll = time.monotonic()
        self._future = self._executor.submit(
            coordinate_holoindex_postmerge,
            repo_root=self._repo_root,
        )


def _poll_status(
    accepted: bool,
    status: str,
    rejection_reason: str = "",
) -> Dict[str, Any]:
    return {
        "accepted": accepted,
        "status": status,
        "rejection_reasons": [rejection_reason] if rejection_reason else [],
    }


def _canonical_task_id(result: Mapping[str, Any]) -> str:
    target_sha = str(result.get("target_repo_head_sha") or "")
    task_id = str(result.get("task_id") or "")
    if (
        result.get("accepted") is True
        and _SHA_RE.fullmatch(target_sha)
        and task_id == HOLOINDEX_POSTMERGE_TASK_PREFIX + target_sha
    ):
        return task_id
    return ""


def is_canonical_holoindex_postmerge_task_id(task_id: Any) -> bool:
    if not isinstance(task_id, str) or not task_id.startswith(
        HOLOINDEX_POSTMERGE_TASK_PREFIX
    ):
        return False
    target_sha = task_id.removeprefix(HOLOINDEX_POSTMERGE_TASK_PREFIX)
    return _SHA_RE.fullmatch(target_sha) is not None


def holoindex_postmerge_enabled(
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Keep exact-SHA index maintenance active unless explicitly disabled."""

    env = os.environ if environ is None else environ
    return str(env.get("HOLOINDEX_POSTMERGE_COORDINATOR_ENABLED", "1")) == "1"


def is_holoindex_postmerge_task(task: Mapping[str, Any]) -> bool:
    context = task.get("context")
    return bool(
        isinstance(context, Mapping)
        and str(context.get("source") or "") == HOLOINDEX_POSTMERGE_SOURCE
    )


def validate_supervisor_holoindex_postmerge_completion(
    database: Any,
    task_id: str,
) -> Mapping[str, Any] | None:
    """Require the exact task-bound atomic completion receipt."""

    if not is_canonical_holoindex_postmerge_task_id(task_id):
        return None
    target_sha = task_id.removeprefix(HOLOINDEX_POSTMERGE_TASK_PREFIX)
    task = database.get_autonomous_task_by_id(task_id)
    context = task.get("context") if isinstance(task, Mapping) else None
    if not isinstance(context, Mapping):
        return None
    authority_root_digest = context.get("authority_root_digest")
    if not (
        context.get("source") == HOLOINDEX_POSTMERGE_SOURCE
        and context.get("target_repo_head_sha") == target_sha
        and isinstance(authority_root_digest, str)
        and _DIGEST_RE.fullmatch(authority_root_digest)
    ):
        return None
    from modules.infrastructure.idle_automation.src.holoindex_postmerge_contract import (
        validate_holoindex_postmerge_completion,
    )

    return validate_holoindex_postmerge_completion(
        database,
        task_id=task_id,
        target_repo_head_sha=target_sha,
        authority_root_digest=authority_root_digest,
    )


def verified_maintenance_task_status(
    database: Any,
    task_id: Any,
    family: Any,
) -> str | None:
    """Return completed only from the family-appropriate evidence source."""

    if family == "holoindex_postmerge":
        completion = validate_supervisor_holoindex_postmerge_completion(
            database, task_id
        )
        return "completed" if completion is not None else None
    completed_tasks = database.get_autonomous_tasks(status="completed", limit=100)
    if isinstance(task_id, str) and any(
        item.get("task_id") == task_id for item in completed_tasks
    ):
        return "completed"
    return None


def maintenance_candidates(
    tasks: Sequence[Mapping[str, Any]],
    *,
    general_maintenance_enabled: bool,
    postmerge_enabled: bool,
) -> List[Dict[str, Any]]:
    """Limit default maintenance authority to the post-merge family."""

    if general_maintenance_enabled:
        return [
            dict(task)
            for task in tasks
            if postmerge_enabled or not is_holoindex_postmerge_task(task)
        ]
    if not postmerge_enabled:
        return []
    return [dict(task) for task in tasks if is_holoindex_postmerge_task(task)]


def exclude_holoindex_postmerge_tasks(
    tasks: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Keep exact-SHA maintenance out of the generic task executor."""

    return [dict(task) for task in tasks if not is_holoindex_postmerge_task(task)]


__all__ = [
    "HoloIndexPostmergePoller",
    "exclude_holoindex_postmerge_tasks",
    "holoindex_postmerge_enabled",
    "is_holoindex_postmerge_task",
    "maintenance_candidates",
    "validate_supervisor_holoindex_postmerge_completion",
    "verified_maintenance_task_status",
]
