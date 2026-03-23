#!/usr/bin/env python3
"""
Executes an autonomous task from AgentDB via WRE or self-audit infrastructure.

This is the P0 task consumer triggered by OpenClawSupervisor._execute().
It can be called:
  - In-process via execute_task(task_id) from the supervisor
  - As a script via python run_task.py --task_id <id>

Dispatch priority:
  1. WRE execute_skill() if required_skills match a registered skill
  2. DaemonSelfAuditLoop._apply_policy_fix() for self_audit-sourced tasks
  3. Fail with "no_executor_matched" — never silently complete
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)


def execute_task(task_id: str, repo_root: Path | None = None) -> Dict[str, Any]:
    """
    Execute a single autonomous task from AgentDB.

    Returns:
        Dict with keys: ok (bool), detail (str), executor (str),
        execution_time_ms (int)
    """
    if repo_root is None:
        repo_root = REPO_ROOT

    start = time.monotonic()

    try:
        from modules.infrastructure.database.src.agent_db import AgentDB
    except ImportError as e:
        return {"ok": False, "detail": f"AgentDB import failed: {e}", "executor": "none", "execution_time_ms": 0}

    db = AgentDB()

    # Fetch the task (supervisor sets it to "assigned" before calling us)
    tasks = db.get_autonomous_tasks(status="assigned", limit=100)
    task = next((t for t in tasks if t.get("task_id") == task_id), None)

    if not task:
        return {"ok": False, "detail": f"Task {task_id} not found in 'assigned' state", "executor": "none", "execution_time_ms": 0}

    required_skills = task.get("required_skills", [])
    context = task.get("context", {})
    source = context.get("source", "") if isinstance(context, dict) else ""
    description = task.get("description", "")

    logger.info("[RUN_TASK] Executing task %s: %s (skills=%s, source=%s)", task_id, description[:80], required_skills, source)

    result: Dict[str, Any] = {"ok": False, "detail": "no_executor_matched", "executor": "none"}

    # ── Dispatch path 1: WRE skill execution ──
    if required_skills:
        wre_result = _try_wre_dispatch(repo_root, task_id, required_skills, context, description)
        if wre_result is not None:
            result = wre_result

    # ── Dispatch path 2: Self-audit policy fix ──
    if not result["ok"] and result["detail"] == "no_executor_matched" and source == "self_audit":
        audit_result = _try_self_audit_dispatch(repo_root, context)
        if audit_result is not None:
            result = audit_result

    # ── Finalize in AgentDB ──
    elapsed_ms = int((time.monotonic() - start) * 1000)
    result["execution_time_ms"] = elapsed_ms

    if result["ok"]:
        db.complete_autonomous_task(task_id)
        logger.info("[RUN_TASK] Task %s completed (executor=%s, %dms)", task_id, result["executor"], elapsed_ms)
    else:
        # Mark as failed by updating status directly (no fail_autonomous_task method yet)
        try:
            db.db.execute_write(
                "UPDATE agents_autonomous_tasks SET status = 'failed' WHERE task_id = ?",
                (task_id,),
            )
        except Exception as fail_exc:
            logger.warning("[RUN_TASK] Could not mark task %s as failed: %s", task_id, fail_exc)
        logger.warning("[RUN_TASK] Task %s failed: %s (executor=%s)", task_id, result["detail"][:200], result["executor"])

    return result


def _try_wre_dispatch(
    repo_root: Path,
    task_id: str,
    required_skills: list,
    context: dict,
    description: str,
) -> Dict[str, Any] | None:
    """Attempt to dispatch via WRE execute_skill. Returns result or None."""
    try:
        from modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_master_orchestrator import (
            WREMasterOrchestrator,
        )

        wre = WREMasterOrchestrator()
        loader = getattr(wre, "skills_loader", None)

        # WRE_MOCK_SKILLS env allows test injection of fake skills
        mock_skills = set(filter(None, os.getenv("WRE_MOCK_SKILLS", "").split(",")))

        for skill_name in required_skills:
            # Check if this skill is actually registered (or mocked for tests)
            has_skill = skill_name in mock_skills
            if not has_skill and loader is not None:
                has_skill_fn = getattr(loader, "has_skill", None)
                if callable(has_skill_fn):
                    try:
                        has_skill = has_skill_fn(skill_name)
                    except Exception:
                        pass
                if not has_skill:
                    registry = getattr(loader, "registry", {}) or {}
                    skills = registry.get("skills", {}) if isinstance(registry, dict) else {}
                    has_skill = isinstance(skills, dict) and skill_name in skills

            if not has_skill:
                continue

            input_context = {
                "type": "autonomous_task",
                "task_id": task_id,
                "task": description,
                "source": "openclaw_supervisor",
                "context": context,
            }

            wre_result = wre.execute_skill(
                skill_name=skill_name,
                agent="qwen",
                input_context=input_context,
            )

            success = wre_result.get("success", False)
            return {
                "ok": success,
                "detail": json.dumps(wre_result, default=str)[:1000],
                "executor": f"wre:{skill_name}",
                "wre_result": wre_result,
            }

    except ImportError as e:
        logger.debug("[RUN_TASK] WRE unavailable: %s", e)
    except Exception as e:
        logger.warning("[RUN_TASK] WRE dispatch error: %s", e)
        return {"ok": False, "detail": f"wre_error: {e}", "executor": "wre"}

    return None


def _try_self_audit_dispatch(repo_root: Path, context: dict) -> Dict[str, Any] | None:
    """Attempt to dispatch via DaemonSelfAuditLoop policy fix. Returns result or None."""
    recommended_fix = None
    if isinstance(context, dict):
        ctx_inner = context.get("context", {})
        if isinstance(ctx_inner, dict):
            recommended_fix = ctx_inner.get("recommended_fix")

    if not recommended_fix:
        return None

    try:
        from modules.infrastructure.wre_core.src.daemon_self_audit_loop import DaemonSelfAuditLoop

        audit_loop = DaemonSelfAuditLoop(repo_root)
        if hasattr(audit_loop, "_apply_policy_fix"):
            success, detail = audit_loop._apply_policy_fix(recommended_fix)
            return {
                "ok": success,
                "detail": str(detail)[:500],
                "executor": f"self_audit:{recommended_fix}",
            }
    except ImportError as e:
        logger.debug("[RUN_TASK] DaemonSelfAuditLoop unavailable: %s", e)
    except Exception as e:
        logger.warning("[RUN_TASK] Self-audit dispatch error: %s", e)
        return {"ok": False, "detail": f"self_audit_error: {e}", "executor": "self_audit"}

    return None


def main():
    parser = argparse.ArgumentParser(description="Run an autonomous task.")
    parser.add_argument("--task_id", type=str, required=True, help="Task ID from AgentDB")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    result = execute_task(args.task_id)

    if result["ok"]:
        print(f"[RUN_TASK] SUCCESS: {result['executor']} ({result['execution_time_ms']}ms)")
    else:
        print(f"[RUN_TASK] FAILED: {result['detail'][:200]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
