#!/usr/bin/env python3
"""
Executes an autonomous task from AgentDB via WRE or self-audit infrastructure.

This is the P0 task consumer triggered by OpenClawSupervisor._execute().
It can be called:
  - In-process via execute_task(task_id) from the supervisor
  - As a script via python run_task.py --task_id <id>

Dispatch priority:
  1. Exact typed routes (read-only audit, signed worker, startup maintenance)
  2. WRE execute_skill() if required_skills match a registered skill
  3. DaemonSelfAuditLoop._apply_policy_fix() for self_audit-sourced tasks
  4. Grant task dispatch for openclaw-grants tasks (review/stabilize)
  5. Fail with "no_executor_matched" — never silently complete
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Mapping

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)

def execute_task(
    task_id: str,
    repo_root: Path | None = None,
    *,
    signed_worker_runner: Any | None = None,
    execution_claim: Mapping[str, str] | None = None,
) -> Dict[str, Any]:
    """Execute a single assigned AgentDB task through its exact route."""
    repo_root = repo_root or REPO_ROOT
    start = time.monotonic()
    db, task, load_error = _load_assigned_task(task_id)
    if load_error is not None:
        return load_error
    assert db is not None and task is not None
    required_skills = task.get("required_skills", [])
    context = task.get("context", {})
    source = context.get("source", "") if isinstance(context, dict) else ""
    discovered_by = str(task.get("discovered_by") or "")
    description = task.get("description", "")

    logger.info("[RUN_TASK] Executing task %s: %s (skills=%s, source=%s)", task_id, description[:80], required_skills, source)

    emitters = _start_runtime_emitter(task_id, source, description)

    result = _dispatch_exact_routes(
        repo_root=repo_root,
        db=db,
        task_id=task_id,
        context=context,
        required_skills=required_skills,
        source=source,
        discovered_by=discovered_by,
        signed_worker_runner=signed_worker_runner,
        execution_claim=execution_claim,
    )

    # Dispatch path 4: WRE skill execution.
    result = _dispatch_fallback_routes(
        result=result,
        repo_root=repo_root,
        task_id=task_id,
        context=context,
        required_skills=required_skills,
        source=source,
        description=description,
    )

    # ── Dispatch path 2: Self-audit policy fix ──
    # ── Dispatch path 3: Grant task dispatch (openclaw-grants) ──
    # ── Finalize in AgentDB ──
    return _finalize_task_result(
        db=db,
        task_id=task_id,
        context=context,
        result=result,
        start=start,
        emitters=emitters,
    )


def _load_assigned_task(
    task_id: str,
) -> tuple[Any | None, Mapping[str, Any] | None, Dict[str, Any] | None]:
    try:
        from modules.infrastructure.database.src.agent_db import AgentDB
    except ImportError as exc:
        return None, None, {
            "ok": False,
            "detail": f"AgentDB import failed: {exc}",
            "executor": "none",
            "execution_time_ms": 0,
        }
    db = AgentDB()
    tasks = db.get_autonomous_tasks(status="assigned", limit=100)
    task = next((item for item in tasks if item.get("task_id") == task_id), None)
    if task is None:
        return db, None, {
            "ok": False,
            "detail": f"Task {task_id} not found in 'assigned' state",
            "executor": "none",
            "execution_time_ms": 0,
        }
    return db, task, None


def _dispatch_exact_routes(
    *,
    repo_root: Path,
    db: Any,
    task_id: str,
    context: Mapping[str, Any],
    required_skills: Any,
    source: str,
    discovered_by: str,
    signed_worker_runner: Any | None,
    execution_claim: Mapping[str, str] | None,
) -> Dict[str, Any]:
    result = _no_executor_result()
    if "reddog_readonly_audit" in required_skills and source == "reddog_openclaw_readonly_audit_swarm":
        readonly = _try_reddog_readonly_audit_dispatch(repo_root, task_id, context)
        if readonly is not None:
            result = readonly
    if _no_executor_matched(result):
        signed = _try_signed_worker_dispatch(
            repo_root=repo_root, db=db, task_id=task_id, context=context,
            required_skills=required_skills, source=source,
            discovered_by=discovered_by, signed_worker_runner=signed_worker_runner,
        )
        if signed is not None:
            result = signed
    if _no_executor_matched(result) and source in {
        "startup_maintenance_gate", "holoindex_postmerge_coordinator",
    }:
        startup = _try_startup_maintenance_dispatch(
            repo_root, task_id, context, execution_claim=execution_claim,
        )
        if startup is not None:
            result = startup
    return result


def _try_signed_worker_dispatch(
    *,
    repo_root: Path,
    db: Any,
    task_id: str,
    context: Mapping[str, Any],
    required_skills: Any,
    source: str,
    discovered_by: str,
    signed_worker_runner: Any | None,
) -> Dict[str, Any] | None:
    from modules.communication.moltbot_bridge.src.reddog_signed_worker_run_task_runtime import (
        execute_signed_worker_from_agentdb,
    )
    result = execute_signed_worker_from_agentdb(
        repo_root=repo_root, db=db, task_id=task_id, context=context,
        required_skills=required_skills, source=source,
        discovered_by=discovered_by, signed_worker_runner=signed_worker_runner,
        env=os.environ,
    )
    return dict(result) if result is not None else None


def _dispatch_fallback_routes(
    *,
    result: Dict[str, Any],
    repo_root: Path,
    task_id: str,
    context: Mapping[str, Any],
    required_skills: Any,
    source: str,
    description: str,
) -> Dict[str, Any]:
    if required_skills and _no_executor_matched(result):
        wre_result = _try_wre_dispatch(
            repo_root, task_id, required_skills, context, description
        )
        if wre_result is not None:
            result = wre_result
    if _no_executor_matched(result) and source == "self_audit":
        audit_result = _try_self_audit_dispatch(repo_root, context)
        if audit_result is not None:
            result = audit_result
    if _no_executor_matched(result) and "openclaw-grants" in required_skills:
        grant_result = _try_grant_dispatch(
            repo_root, task_id, context, description
        )
        if grant_result is not None:
            result = grant_result
    return result


def _finalize_task_result(
    *,
    db: Any,
    task_id: str,
    context: Mapping[str, Any],
    result: Dict[str, Any],
    start: float,
    emitters: tuple[Any, Any, Any],
) -> Dict[str, Any]:
    elapsed_ms = int((time.monotonic() - start) * 1000)
    result["execution_time_ms"] = elapsed_ms
    if result["ok"] and result.get("executor") == "reddog:readonly_audit":
        persist = _try_reddog_readonly_audit_report_persist(
            task_id, context, result
        )
        result["readonly_audit_report_persist"] = persist
        if not persist.get("accepted", False):
            result["ok"] = False
            result["detail"] = json.dumps(persist, default=str)[:1000]
    if result.get("finalization_owned"):
        logger.info(
            "[RUN_TASK] Task %s finalization owned by executor=%s (%dms)",
            task_id, result["executor"], elapsed_ms,
        )
    elif result["ok"]:
        _complete_task(db, task_id, result, elapsed_ms, emitters)
    else:
        _fail_task(db, task_id, result, emitters)
    return result


def _start_runtime_emitter(
    task_id: str, source: str, description: str
) -> tuple[Any, Any, Any]:
    try:
        from modules.infrastructure.dae_daemon.src.runtime_emitter import (
            emit_failure, emit_start, emit_success,
        )
        started = emit_start(
            "run_task", "task_dispatch", task_id=task_id,
            details={"source": source, "description": description[:80]},
        )
        return started, emit_success, emit_failure
    except Exception:
        return None, None, None


def _complete_task(
    db: Any,
    task_id: str,
    result: Mapping[str, Any],
    elapsed_ms: int,
    emitters: tuple[Any, Any, Any],
) -> None:
    db.complete_autonomous_task(task_id)
    logger.info(
        "[RUN_TASK] Task %s completed (executor=%s, %dms)",
        task_id, result["executor"], elapsed_ms,
    )
    started, emit_success, _ = emitters
    if started is not None and emit_success:
        try:
            emit_success(
                "run_task", "task_dispatch", started, task_id=task_id,
                details={"executor": result["executor"]},
            )
        except Exception:
            pass


def _fail_task(
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
    except Exception as fail_exc:
        logger.warning("[RUN_TASK] Could not mark task %s as failed: %s", task_id, fail_exc)
    logger.warning(
        "[RUN_TASK] Task %s failed: %s (executor=%s)",
        task_id, str(result["detail"])[:200], result["executor"],
    )
    started, _, emit_failure = emitters
    if started is not None and emit_failure:
        try:
            emit_failure(
                "run_task", "task_dispatch", started, str(result["detail"])[:200],
                task_id=task_id, details={"executor": result["executor"]},
            )
        except Exception:
            pass


def _no_executor_result() -> Dict[str, Any]:
    return {"ok": False, "detail": "no_executor_matched", "executor": "none"}


def _no_executor_matched(result: Mapping[str, Any]) -> bool:
    return result.get("ok") is not True and result.get("detail") == "no_executor_matched"


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


def _dispatch_holoindex_maintenance(repo_root: Path) -> Dict[str, Any]:
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


def _run_self_research_refresh(refresher: Any) -> Dict[str, Any]:
    """Run the bounded startup self-research refresh."""
    try:
        result = refresher.run(
            run_holo_refresh=False,
            run_compliance=True,
            run_self_audit=True,
            run_watchlists=True,
            write_tasks=True,
            emit_nudges=True,
        )
        success = isinstance(result, dict) and "generated_on" in result
        return {
            "ok": success,
            "detail": json.dumps(result, default=str)[:1000],
            "executor": "startup:self_research",
            "structured_result": result,
        }
    except Exception as exc:
        return {
            "ok": False,
            "detail": f"self_research_error: {exc}",
            "executor": "startup:self_research",
        }


def _run_model_status_refresh(repo_root: Path) -> Dict[str, Any]:
    """Refresh model availability and persist the bounded status report."""
    try:
        from modules.communication.moltbot_bridge.src.openclaw_runtime_support import (
            get_model_availability_snapshot,
        )

        result = get_model_availability_snapshot(dae=None, live_probe=False)
        try:
            from modules.infrastructure.dependency_launcher.src.dae_dependencies import (
                get_dependency_status,
            )

            result["lm_studio_running"] = get_dependency_status().get(
                "lm_studio",
                False,
            )
        except Exception:
            result["lm_studio_running"] = None
        reports_dir = (
            repo_root
            / "modules"
            / "communication"
            / "moltbot_bridge"
            / "workspace"
            / "reports"
        )
        reports_dir.mkdir(parents=True, exist_ok=True)
        status_path = reports_dir / "local_model_status.json"
        status_path.write_text(
            json.dumps(result, indent=2, default=str),
            encoding="utf-8",
        )
        return {
            "ok": True,
            "detail": json.dumps(result, default=str)[:1000],
            "executor": "startup:model_status",
            "structured_result": result,
        }
    except Exception as exc:
        return {
            "ok": False,
            "detail": f"model_status_error: {exc}",
            "executor": "startup:model_status",
        }


def _run_training_batch() -> Dict[str, Any]:
    """Run one startup pattern-training batch when the DAE is available."""
    try:
        import asyncio
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        result = asyncio.run(IdleAutomationDAE()._execute_pattern_training())
        return {
            "ok": result.get("success", False),
            "detail": json.dumps(result, default=str)[:1000],
            "executor": "startup:training_batch",
            "structured_result": result,
        }
    except Exception as exc:
        return {
            "ok": False,
            "detail": f"training_error: {exc}",
            "executor": "startup:training_batch",
        }


def _try_startup_maintenance_dispatch(
    repo_root: Path,
    task_id: str,
    context: dict,
    *,
    execution_claim: Mapping[str, str] | None = None,
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
    if (
        context.get("source") == "holoindex_postmerge_coordinator"
        and task_id.startswith("holoindex_postmerge_refresh:")
    ):
        from modules.infrastructure.idle_automation.src.holoindex_postmerge_executor import (
            execute_holoindex_postmerge_task,
        )

        logger.info(
            "[RUN_TASK] Post-merge dispatch: exact-SHA HoloIndex maintenance"
        )
        return execute_holoindex_postmerge_task(
            repo_root=repo_root,
            task_id=task_id,
            context=context,
            execution_claim=execution_claim,
        )

    if task_id == "startup_refresh_holo_index":
        logger.info("[RUN_TASK] Startup dispatch: HoloIndex maintenance handshake")
        return _dispatch_holoindex_maintenance(repo_root)

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
        return _run_self_research_refresh(refresher)
    if task_id == "startup_refresh_model_status":
        logger.info("[RUN_TASK] Startup dispatch: model status refresh")
        return _run_model_status_refresh(repo_root)
    if task_id == "startup_training_batch":
        logger.info("[RUN_TASK] Startup dispatch: training batch")
        return _run_training_batch()
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
