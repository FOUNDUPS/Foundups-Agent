"""Shared result and telemetry helpers for the AgentDB task runner."""

from __future__ import annotations

import logging
from typing import Any, Dict, Mapping

logger = logging.getLogger(__name__)


def start_runtime_emitter(
    task_id: str, source: str, description: str
) -> tuple[Any, Any, Any]:
    try:
        from modules.infrastructure.dae_daemon.src.runtime_emitter import (
            emit_failure,
            emit_start,
            emit_success,
        )

        started = emit_start(
            "run_task",
            "task_dispatch",
            task_id=task_id,
            details={"source": source, "description": description[:80]},
        )
        return started, emit_success, emit_failure
    except Exception:
        return None, None, None


def complete_task(
    db: Any,
    task_id: str,
    result: Mapping[str, Any],
    elapsed_ms: int,
    emitters: tuple[Any, Any, Any],
) -> None:
    db.complete_autonomous_task(task_id)
    logger.info(
        "[RUN_TASK] Task %s completed (executor=%s, %dms)",
        task_id,
        result["executor"],
        elapsed_ms,
    )
    started, emit_success, _ = emitters
    if started is not None and emit_success:
        try:
            emit_success(
                "run_task",
                "task_dispatch",
                started,
                task_id=task_id,
                details={"executor": result["executor"]},
            )
        except Exception:
            pass


def fail_task(
    db: Any,
    task_id: str,
    result: Mapping[str, Any],
    emitters: tuple[Any, Any, Any],
) -> None:
    try:
        db.db.execute_write(
            "UPDATE agents_autonomous_tasks SET status = 'failed' WHERE task_id = ?",
            (task_id,),
        )
    except Exception as exc:
        logger.warning("[RUN_TASK] Could not mark task %s as failed: %s", task_id, exc)
    logger.warning(
        "[RUN_TASK] Task %s failed: %s (executor=%s)",
        task_id,
        str(result["detail"])[:200],
        result["executor"],
    )
    started, _, emit_failure = emitters
    if started is not None and emit_failure:
        try:
            emit_failure(
                "run_task",
                "task_dispatch",
                started,
                str(result["detail"])[:200],
                task_id=task_id,
                details={"executor": result["executor"]},
            )
        except Exception:
            pass


def no_executor_result() -> Dict[str, Any]:
    return {"ok": False, "detail": "no_executor_matched", "executor": "none"}


def no_executor_matched(result: Mapping[str, Any]) -> bool:
    return (
        result.get("ok") is not True
        and result.get("detail") == "no_executor_matched"
    )


__all__ = [
    "complete_task",
    "fail_task",
    "no_executor_matched",
    "no_executor_result",
    "start_runtime_emitter",
]
