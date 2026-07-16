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
  3. Grant task dispatch for openclaw-grants tasks (review/stabilize)
  4. Fail with "no_executor_matched" — never silently complete
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


def execute_task(
    task_id: str,
    repo_root: Path | None = None,
    *,
    signed_worker_runner: Any | None = None,
) -> Dict[str, Any]:
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

    # Runtime emitter: structured event for troubleshooting/tuning
    try:
        from modules.infrastructure.dae_daemon.src.runtime_emitter import emit_start, emit_success, emit_failure
        _emit_start = emit_start("run_task", "task_dispatch", task_id=task_id,
                                 details={"source": source, "description": description[:80]})
    except Exception:
        _emit_start = None
        emit_success = emit_failure = None  # type: ignore[assignment]

    result: Dict[str, Any] = {"ok": False, "detail": "no_executor_matched", "executor": "none"}

    # Dispatch path 1: exact RedDog read-only audit report execution.
    if "reddog_readonly_audit" in required_skills and source == "reddog_openclaw_readonly_audit_swarm":
        readonly_result = _try_reddog_readonly_audit_dispatch(repo_root, task_id, context)
        if readonly_result is not None:
            result = readonly_result

    # Dispatch path 2: exact RedDog signed worker-dispatch task execution.
    if not result["ok"] and result["detail"] == "no_executor_matched":
        signed_worker_result = _try_reddog_signed_worker_dispatch(
            repo_root,
            task_id,
            context,
            required_skills,
            source,
            signed_worker_runner,
        )
        if signed_worker_result is not None:
            result = signed_worker_result

    # Dispatch path 3: WRE skill execution.
    if required_skills:
        if not result["ok"] and result["detail"] == "no_executor_matched":
            wre_result = _try_wre_dispatch(repo_root, task_id, required_skills, context, description)
            if wre_result is not None:
                result = wre_result

    # ── Dispatch path 2: Self-audit policy fix ──
    if not result["ok"] and result["detail"] == "no_executor_matched" and source == "self_audit":
        audit_result = _try_self_audit_dispatch(repo_root, context)
        if audit_result is not None:
            result = audit_result

    # ── Dispatch path 3: Grant task dispatch (openclaw-grants) ──
    if not result["ok"] and result["detail"] == "no_executor_matched":
        if "openclaw-grants" in required_skills:
            grant_result = _try_grant_dispatch(repo_root, task_id, context, description)
            if grant_result is not None:
                result = grant_result

    # ── Dispatch path 4: Startup maintenance tasks ──
    if not result["ok"] and result["detail"] == "no_executor_matched" and source == "startup_maintenance_gate":
        startup_result = _try_startup_maintenance_dispatch(repo_root, task_id, context)
        if startup_result is not None:
            result = startup_result

    # ── Finalize in AgentDB ──
    elapsed_ms = int((time.monotonic() - start) * 1000)
    result["execution_time_ms"] = elapsed_ms
    if result["ok"] and result.get("executor") == "reddog:readonly_audit":
        persist_result = _try_reddog_readonly_audit_report_persist(task_id, context, result)
        result["readonly_audit_report_persist"] = persist_result
        if not persist_result.get("accepted", False):
            result["ok"] = False
            result["detail"] = json.dumps(persist_result, default=str)[:1000]

    if result["ok"]:
        db.complete_autonomous_task(task_id)
        logger.info("[RUN_TASK] Task %s completed (executor=%s, %dms)", task_id, result["executor"], elapsed_ms)
        if _emit_start is not None and emit_success:
            try:
                emit_success("run_task", "task_dispatch", _emit_start,
                             task_id=task_id, details={"executor": result["executor"]})
            except Exception:
                pass
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
        if _emit_start is not None and emit_failure:
            try:
                emit_failure("run_task", "task_dispatch", _emit_start,
                             result["detail"][:200], task_id=task_id,
                             details={"executor": result["executor"]})
            except Exception:
                pass

    return result


def _try_reddog_readonly_audit_dispatch(
    repo_root: Path,
    task_id: str,
    context: dict,
) -> Dict[str, Any] | None:
    """Execute an exact RedDog read-only audit task. Returns result or None."""
    try:
        from modules.communication.moltbot_bridge.src.reddog_readonly_audit_task_executor import (
            execute_reddog_readonly_audit_task,
        )
    except ImportError as e:
        logger.debug("[RUN_TASK] RedDog read-only audit executor unavailable: %s", e)
        return None

    try:
        audit_result = execute_reddog_readonly_audit_task(
            task_context=context,
            repo_root=repo_root,
            task_id=task_id,
        )
        payload = audit_result.to_dict()
        return {
            "ok": bool(audit_result.accepted),
            "detail": json.dumps(payload, default=str)[:1000],
            "executor": "reddog:readonly_audit",
            "structured_result": payload,
        }
    except Exception as e:
        logger.warning("[RUN_TASK] RedDog read-only audit dispatch error: %s", e)
        return {
            "ok": False,
            "detail": f"reddog_readonly_audit_error: {e}",
            "executor": "reddog:readonly_audit",
        }


def _try_reddog_readonly_audit_report_persist(
    task_id: str,
    context: dict,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """Persist exact RedDog read-only audit task reports before completion."""
    try:
        from modules.communication.moltbot_bridge.src.reddog_readonly_audit_report_collection import (
            persist_reddog_readonly_audit_task_report,
        )
    except ImportError as e:
        logger.warning("[RUN_TASK] RedDog read-only audit report store unavailable: %s", e)
        return {
            "accepted": False,
            "status": "READONLY_AUDIT_REPORT_PERSIST_REJECT",
            "rejection_reasons": ["report_store_unavailable"],
        }

    try:
        return persist_reddog_readonly_audit_task_report(
            task_id=task_id,
            task_context=context,
            task_result=result,
        ).to_dict()
    except Exception as e:
        logger.warning("[RUN_TASK] RedDog read-only audit report persist error: %s", e)
        return {
            "accepted": False,
            "status": "READONLY_AUDIT_REPORT_PERSIST_REJECT",
            "rejection_reasons": ["report_store_error"],
        }


def _try_reddog_signed_worker_dispatch(
    repo_root: Path,
    task_id: str,
    context: dict,
    required_skills: list,
    source: str,
    signed_worker_runner: Any | None,
) -> Dict[str, Any] | None:
    """Execute exact RedDog signed worker-dispatch tasks before WRE fallback."""

    try:
        from modules.communication.moltbot_bridge.src.reddog_signed_worker_dispatch_task_executor import (
            SIGNED_WORKER_DISPATCH_TASK_SKILL,
            SIGNED_WORKER_DISPATCH_TASK_SOURCE,
            execute_reddog_signed_worker_dispatch_task,
        )
    except ImportError as e:
        logger.debug("[RUN_TASK] RedDog signed-worker executor unavailable: %s", e)
        return None

    if SIGNED_WORKER_DISPATCH_TASK_SKILL not in required_skills:
        return None
    if source != SIGNED_WORKER_DISPATCH_TASK_SOURCE:
        return None

    try:
        execution = execute_reddog_signed_worker_dispatch_task(
            task_context=context,
            task_id=task_id,
            repo_root=repo_root,
            runner=signed_worker_runner,
        )
        payload = execution.to_dict()
        return {
            "ok": bool(execution.accepted),
            "detail": json.dumps(payload, default=str)[:1000],
            "executor": "reddog:signed_worker_dispatch",
            "structured_result": payload,
        }
    except Exception as e:
        logger.warning("[RUN_TASK] RedDog signed-worker dispatch error: %s", e)
        return {
            "ok": False,
            "detail": f"reddog_signed_worker_dispatch_error: {e}",
            "executor": "reddog:signed_worker_dispatch",
        }


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


def _try_grant_dispatch(
    repo_root: Path, task_id: str, context: dict, description: str
) -> Dict[str, Any] | None:
    """
    Execute grant watchlist review or stabilization tasks.

    Handles:
      - grant_watchlist_review: Review changed grant pages
      - grant_watchlist_stabilize: Fix watchlist fetch errors

    Returns structured, machine-verifiable results suitable for supervisor verification.
    Human-only gates (KYC, identity, final submit) remain intact per SKILL.md.
    """
    try:
        from modules.communication.moltbot_bridge.src.grant_task_executor import (
            execute_grant_review,
            execute_grant_stabilize,
        )
    except ImportError as e:
        logger.debug("[RUN_TASK] grant_task_executor unavailable: %s", e)
        return None

    # Extract context details
    ctx_inner = context.get("context", {}) if isinstance(context, dict) else {}
    changed_items = ctx_inner.get("changed_items", [])
    error_items = ctx_inner.get("error_items", [])

    # Determine task type and execute
    if task_id == "grant_watchlist_review" and changed_items:
        logger.info("[RUN_TASK] Grant review dispatch: %d changed items", len(changed_items))
        result = execute_grant_review(changed_items)
        return {
            "ok": result.get("success", False),
            "detail": json.dumps(result, default=str)[:1000],
            "executor": "grant:review",
            "structured_result": result,
        }

    elif task_id == "grant_watchlist_stabilize" and error_items:
        logger.info("[RUN_TASK] Grant stabilize dispatch: %d error items", len(error_items))
        result = execute_grant_stabilize(error_items)
        return {
            "ok": result.get("success", False),
            "detail": json.dumps(result, default=str)[:1000],
            "executor": "grant:stabilize",
            "structured_result": result,
        }

    else:
        # Not a recognized grant task pattern
        return None


def _try_startup_maintenance_dispatch(
    repo_root: Path, task_id: str, context: dict
) -> Dict[str, Any] | None:
    """
    Execute startup maintenance tasks queued by startup_maintenance_gate.

    Handles:
      - startup_refresh_self_research: Run self-research refresh
      - startup_refresh_holo_index: Run HoloIndex refresh
      - startup_refresh_model_status: Run model status refresh
      - startup_training_batch: Run training batch (if training system available)

    Returns structured result or None if not a recognized startup task.
    """
    try:
        from modules.infrastructure.idle_automation.src.self_research_refresh import (
            SelfResearchRefresher,
        )
    except ImportError as e:
        logger.debug("[RUN_TASK] SelfResearchRefresher unavailable: %s", e)
        return None

    refresher = SelfResearchRefresher(repo_root=repo_root)

    if task_id == "startup_refresh_self_research":
        logger.info("[RUN_TASK] Startup dispatch: self-research refresh")
        try:
            # Use actual SelfResearchRefresher.run() signature
            result = refresher.run(
                run_holo_refresh=False,
                run_compliance=True,
                run_self_audit=True,
                run_watchlists=True,
                write_tasks=True,
                emit_nudges=True,
            )
            # Success = report dict with generated_on (means refresh completed)
            success = isinstance(result, dict) and "generated_on" in result
            return {
                "ok": success,
                "detail": json.dumps(result, default=str)[:1000],
                "executor": "startup:self_research",
                "structured_result": result,
            }
        except Exception as e:
            return {"ok": False, "detail": f"self_research_error: {e}", "executor": "startup:self_research"}

    elif task_id == "startup_refresh_holo_index":
        logger.info("[RUN_TASK] Startup dispatch: HoloIndex refresh")
        try:
            result = refresher.refresh_holo_index()
            success = result.get("refresh_success", False) or not result.get("code_stale", True)
            return {
                "ok": success,
                "detail": json.dumps(result, default=str)[:1000],
                "executor": "startup:holo_index",
                "structured_result": result,
            }
        except Exception as e:
            return {"ok": False, "detail": f"holo_index_error: {e}", "executor": "startup:holo_index"}

    elif task_id == "startup_refresh_model_status":
        logger.info("[RUN_TASK] Startup dispatch: model status refresh")
        try:
            from modules.communication.moltbot_bridge.src.openclaw_runtime_support import (
                get_model_availability_snapshot,
            )

            result = get_model_availability_snapshot(dae=None, live_probe=False)

            # Supplement with LM Studio running status (extra field, does not change shape)
            try:
                from modules.infrastructure.dependency_launcher.src.dae_dependencies import (
                    get_dependency_status,
                )
                dep_status = get_dependency_status()
                result["lm_studio_running"] = dep_status.get("lm_studio", False)
            except Exception:
                result["lm_studio_running"] = None

            reports_dir = repo_root / "modules" / "communication" / "moltbot_bridge" / "workspace" / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            status_path = reports_dir / "local_model_status.json"
            status_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

            return {
                "ok": True,
                "detail": json.dumps(result, default=str)[:1000],
                "executor": "startup:model_status",
                "structured_result": result,
            }
        except Exception as e:
            return {"ok": False, "detail": f"model_status_error: {e}", "executor": "startup:model_status"}

    elif task_id == "startup_training_batch":
        logger.info("[RUN_TASK] Startup dispatch: training batch")
        try:
            import asyncio
            from modules.infrastructure.idle_automation.src.idle_automation_dae import (
                IdleAutomationDAE,
            )

            dae = IdleAutomationDAE()
            result = asyncio.run(dae._execute_pattern_training())
            success = result.get("success", False)
            return {
                "ok": success,
                "detail": json.dumps(result, default=str)[:1000],
                "executor": "startup:training_batch",
                "structured_result": result,
            }
        except Exception as e:
            return {"ok": False, "detail": f"training_error: {e}", "executor": "startup:training_batch"}

    else:
        # Not a recognized startup task pattern
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
