#!/usr/bin/env python3
"""
Canonical OpenClaw 24/7 Supervisor State Machine.

This is the CANONICAL supervisor for the FoundUps Agent runtime.
`Supervisor24x7` in modules/infrastructure/supervisor/ is a donor/prototype.

Architecture (WSP prompt pack 2026-03-22):
- AI Overseer: observe, gate, correlate, rank
- OpenClawSupervisor: schedule, budget, launch, verify (THIS FILE)
- OpenClaw: executive/control plane
- WRE + DAEs: execution
- PatternMemory: recall and learning

State machine:
    BOOT → PREFLIGHT → OBSERVE → TRIAGE → PLAN → EXECUTE → VERIFY → REMEMBER → ESCALATE → IDLE_WATCH
      ↑___________________________________________________________________________________|
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SupervisorMetrics:
    """Telemetry for observability (WSP 91)."""

    cycles_completed: int = 0
    events_observed: int = 0
    tasks_executed: int = 0
    tasks_succeeded: int = 0
    escalations_triggered: int = 0
    last_state_change: float = field(default_factory=time.time)
    state_durations: Dict[str, float] = field(default_factory=dict)


class SupervisorState(str, Enum):
    BOOT = "BOOT"
    PREFLIGHT = "PREFLIGHT"
    OBSERVE = "OBSERVE"
    TRIAGE = "TRIAGE"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    REMEMBER = "REMEMBER"
    ESCALATE = "ESCALATE"
    IDLE_WATCH = "IDLE_WATCH"


def _normalize_ai_analysis(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize AI Overseer analysis to consistent shape.

    Handles two return shapes from analyze_mission_requirements():
    - Normal: classification.complexity, patterns_detected, recommended_team
    - Fallback: top-level complexity, requires_coordination (no classification object)
    """
    # Extract complexity: prefer classification.complexity, fall back to top-level
    classification = analysis.get("classification", {})
    if isinstance(classification, dict) and "complexity" in classification:
        complexity = classification.get("complexity", 0)
    else:
        complexity = analysis.get("complexity", 0)

    return {
        "complexity": complexity,
        "patterns": analysis.get("patterns_detected", []),
        "recommended_team": analysis.get("recommended_team", {}),
        "method": analysis.get("method", "unknown"),
        "requires_coordination": analysis.get("requires_coordination"),
    }


class OpenClawSupervisor:
    """
    Canonical 0102 supervisor for the resident OpenClaw runtime.

    This is the production supervisor launched by main.py.
    Unified from OpenClawSupervisor + Supervisor24x7 behaviors (P1 2026-03-22).
    """

    def __init__(
        self,
        repo_root: Path,
        *,
        broker: Any | None = None,
        observer: Any | None = None,
        action_reporter: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
        self_audit_factory: Optional[Callable[[Path], Any]] = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.poll_sec = float(os.getenv("OPENCLAW_SUPERVISOR_POLL_SEC", "10"))
        self.restart_enabled = os.getenv("OPENCLAW_SUPERVISOR_ALLOW_RESTART", "1") != "0"
        self.max_restart_attempts = max(int(os.getenv("OPENCLAW_SUPERVISOR_MAX_RESTARTS", "3")), 1)
        self.restart_window_sec = max(float(os.getenv("OPENCLAW_SUPERVISOR_RESTART_WINDOW_SEC", "900")), 60.0)
        self.self_audit_enabled = os.getenv("OPENCLAW_SELF_AUDIT_ENABLED", "1") != "0"
        self.current_state = SupervisorState.BOOT
        self.last_reason = "init"
        self.last_cycle: Dict[str, Any] = {}
        self._bootstrapped = False
        self._stop_event = threading.Event()
        self._broker = broker
        self._observer = observer
        self._action_reporter = action_reporter or self._build_daemon_reporter()
        self._self_audit_factory = self_audit_factory
        self._self_audit_loop: Any | None = None
        self._event_cursor = 0
        self._restart_attempts: Deque[float] = deque()

        # Unified from Supervisor24x7 (P1 2026-03-22)
        self.metrics = SupervisorMetrics()
        self._ai_overseer: Any | None = None
        self._pattern_memory: Any | None = None
        self._libido_monitor: Any | None = None
        self._triage_queue: List[Dict[str, Any]] = []
        self._execution_results: List[Dict[str, Any]] = []

    def stop(self) -> None:
        self._stop_event.set()
        self._stop_self_audit()

    def get_metrics(self) -> Dict[str, Any]:
        """Return telemetry metrics (WSP 91 observability)."""
        return {
            "state": self.current_state.value,
            "cycles_completed": self.metrics.cycles_completed,
            "events_observed": self.metrics.events_observed,
            "tasks_executed": self.metrics.tasks_executed,
            "tasks_succeeded": self.metrics.tasks_succeeded,
            "escalations_triggered": self.metrics.escalations_triggered,
            "uptime_seconds": time.time() - self.metrics.last_state_change,
            "restart_budget": {
                "max_attempts": self.max_restart_attempts,
                "window_sec": self.restart_window_sec,
                "attempts_in_window": self._attempts_in_window(),
            },
        }

    def run_forever(self) -> Dict[str, Any]:
        while not self._stop_event.is_set():
            self.run_cycle()
            self._stop_event.wait(max(self.poll_sec, 1.0))
        return {"status": "stopped", "state": self.current_state.value}

    def run_cycle(self) -> Dict[str, Any]:
        if not self._bootstrapped:
            self._transition(SupervisorState.BOOT, "startup")
            self._start_self_audit()
            self._transition(SupervisorState.PREFLIGHT, "dependencies_checked")
            self._bootstrapped = True

        observation: Dict[str, Any] = {}
        plan: Dict[str, Any] | None = None
        action_result: Dict[str, Any] = {}
        verify: Dict[str, Any] = {}

        self._transition(SupervisorState.OBSERVE, "cycle_start")
        observation = self._observe()

        self._transition(SupervisorState.TRIAGE, "observation_ready")
        triage = self._triage(observation)
        if triage["kind"] == "idle":
            self._transition(SupervisorState.IDLE_WATCH, triage["reason"])
            self._remember(observation, triage, {}, {"ok": True, "state": "idle"})
            self.last_cycle = {
                "state": self.current_state.value,
                "triage": triage,
                "observation": observation,
            }
            return self.last_cycle

        if triage["kind"] == "escalate":
            self._transition(SupervisorState.ESCALATE, triage["reason"])
            verify = {"ok": False, "error": triage["reason"]}
            self._remember(observation, triage, {}, verify)
            self.last_cycle = {
                "state": self.current_state.value,
                "triage": triage,
                "observation": observation,
                "verify": verify,
            }
            return self.last_cycle

        self._transition(SupervisorState.PLAN, triage["reason"])
        plan = self._plan(triage, observation)

        self._transition(SupervisorState.EXECUTE, plan["action"])
        action_result = self._execute(plan)

        self._transition(SupervisorState.VERIFY, plan["action"])
        verify = self._verify(plan, action_result)

        if not verify["ok"]:
            self._transition(SupervisorState.ESCALATE, verify.get("error", "verify_failed"))
            self._remember(observation, plan, action_result, verify)
        else:
            self._transition(SupervisorState.REMEMBER, plan["action"])
            self._remember(observation, plan, action_result, verify)
            self._transition(SupervisorState.IDLE_WATCH, "cycle_complete")

        self.last_cycle = {
            "state": self.current_state.value,
            "plan": plan,
            "action_result": action_result,
            "verify": verify,
            "observation": observation,
        }
        return self.last_cycle

    # ------------------------------------------------------------------ #
    #  Infrastructure helpers                                             #
    # ------------------------------------------------------------------ #

    def _build_daemon_reporter(self) -> Callable[[str, str, Dict[str, Any]], None]:
        from modules.infrastructure.dae_daemon.src.dae_daemon import get_central_daemon
        from modules.infrastructure.dae_daemon.src.schemas import DAEEventType

        daemon = get_central_daemon()

        def reporter(action_type: str, result: str, details: Dict[str, Any]) -> None:
            daemon.registry.report_event(
                "openclaw_supervisor",
                DAEEventType.ACTION_PERFORMED,
                {
                    "action_type": action_type,
                    "result": result[:200],
                    "details": details,
                },
            )

        return reporter

    def _get_broker(self) -> Any | None:
        if self._broker is None:
            from modules.infrastructure.dae_daemon.src.dae_launch_broker import (
                get_dae_launch_broker,
            )

            self._broker = get_dae_launch_broker()
        return self._broker

    def _get_observer(self) -> Any | None:
        if self._observer is None:
            from modules.infrastructure.dae_daemon.src.dae_observer import get_dae_observer

            self._observer = get_dae_observer()
        return self._observer

    def _transition(self, state: SupervisorState, reason: str) -> None:
        self.current_state = state
        self.last_reason = reason
        self._action_reporter(
            "supervisor_state",
            state.value,
            {"state": state.value, "reason": reason},
        )

    # ------------------------------------------------------------------ #
    #  Self-Audit Lifecycle                                               #
    # ------------------------------------------------------------------ #

    def _start_self_audit(self) -> None:
        if not self.self_audit_enabled or self._self_audit_loop is not None:
            return
        try:
            factory = self._self_audit_factory
            if factory is None:
                from modules.infrastructure.wre_core.src.daemon_self_audit_loop import (
                    DaemonSelfAuditLoop,
                )

                factory = DaemonSelfAuditLoop
            self._self_audit_loop = factory(self.repo_root)
            self._self_audit_loop.start()
            self._action_reporter(
                "supervisor_subsystem",
                "self_audit_started",
                {"subsystem": "daemon_self_audit"},
            )
        except Exception as exc:
            self._action_reporter(
                "supervisor_subsystem",
                "self_audit_failed",
                {"subsystem": "daemon_self_audit", "error": str(exc)[:200]},
            )

        # Initialize unified components (ported from Supervisor24x7)
        self._init_unified_components()

    def _init_unified_components(self) -> None:
        """Initialize AI Overseer, PatternMemory, LibidoMonitor (unified from Supervisor24x7)."""
        # AI Overseer for PLAN state
        try:
            from modules.ai_intelligence.ai_overseer.src.ai_overseer import (
                AIIntelligenceOverseer,
            )
            self._ai_overseer = AIIntelligenceOverseer(repo_root=self.repo_root)
            logger.info("[SUPERVISOR] AI Overseer loaded")
        except ImportError as e:
            logger.debug("[SUPERVISOR] AI Overseer unavailable: %s", e)

        # Pattern Memory for REMEMBER state
        try:
            from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory
            db_path = self.repo_root / "modules/infrastructure/wre_core/memory/pattern_memory.db"
            self._pattern_memory = PatternMemory(db_path=db_path)
            logger.info("[SUPERVISOR] PatternMemory loaded")
        except (ImportError, Exception) as e:
            logger.debug("[SUPERVISOR] PatternMemory unavailable: %s", e)

        # Libido Monitor for VERIFY state (Gemma fidelity)
        try:
            from modules.infrastructure.wre_core.src.libido_monitor import GemmaLibidoMonitor
            self._libido_monitor = GemmaLibidoMonitor()
            logger.info("[SUPERVISOR] LibidoMonitor loaded")
        except (ImportError, Exception) as e:
            logger.debug("[SUPERVISOR] LibidoMonitor unavailable: %s", e)

    def _stop_self_audit(self) -> None:
        if self._self_audit_loop is None:
            return
        try:
            self._self_audit_loop.stop()
        finally:
            self._self_audit_loop = None

    # ------------------------------------------------------------------ #
    #  OBSERVE — poll broker, observer, git, self-audit                   #
    # ------------------------------------------------------------------ #

    def _observe(self) -> Dict[str, Any]:
        broker = self._get_broker()
        observer = self._get_observer()
        obs: Dict[str, Any] = {
            "openclaw_runtime": broker.get_runtime_status("openclaw") if broker else {"registered": False},
            "supervisor_runtime": broker.get_runtime_status("openclaw_supervisor") if broker else {"registered": False},
            "openclaw_live": observer.get_live_status("openclaw", limit=4) if observer else {"registered": False},
            "openclaw_follow": (
                observer.follow_events(
                    dae_id="openclaw",
                    since_sequence=self._event_cursor,
                    limit=8,
                )
                if observer
                else {"events": [], "next_cursor": self._event_cursor, "latest_sequence_id": self._event_cursor}
            ),
            "git": self._git_summary(),
            "self_audit_enabled": self.self_audit_enabled,
            "restart_budget": {
                "max_attempts": self.max_restart_attempts,
                "window_sec": self.restart_window_sec,
                "attempts_in_window": self._attempts_in_window(),
            },
            "self_audit_events": [],
        }

        # Poll DaemonSelfAuditLoop for real events (ported from Supervisor24x7)
        if self._self_audit_loop and hasattr(self._self_audit_loop, "scan_once"):
            try:
                events = self._self_audit_loop.scan_once()
                if events:
                    obs["self_audit_events"] = list(events)
                    self.metrics.events_observed += len(obs["self_audit_events"])
                    logger.info(
                        "[SUPERVISOR] OBSERVE: %d self-audit events detected",
                        len(obs["self_audit_events"]),
                    )
            except Exception as exc:
                logger.warning("[SUPERVISOR] OBSERVE: scan_once() failed: %s", exc)

        return obs

    # ------------------------------------------------------------------ #
    #  TRIAGE — decide what action to take                                #
    # ------------------------------------------------------------------ #

    def _triage(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        broker = self._get_broker()
        observer = self._get_observer()
        if broker is None or observer is None:
            return {"kind": "escalate", "reason": "broker_or_observer_unavailable"}

        runtime = observation["openclaw_runtime"]
        if not runtime.get("registered"):
            return {"kind": "escalate", "reason": "openclaw_runtime_not_registered"}

        if not runtime.get("running"):
            if not self.restart_enabled:
                return {"kind": "escalate", "reason": "resident_openclaw_down_restart_disabled"}
            if not self._can_attempt_restart():
                return {
                    "kind": "escalate",
                    "reason": "resident_openclaw_restart_budget_exhausted",
                    "restart_budget": observation.get("restart_budget", {}),
                }
            return {
                "kind": "action",
                "reason": "resident_openclaw_not_running",
                "action": "start_openclaw",
                "restart_budget": observation.get("restart_budget", {}),
            }

        # Check AgentDB for pending autonomous tasks
        try:
            from modules.infrastructure.database.src.agent_db import AgentDB
            db = AgentDB()
            tasks = db.get_autonomous_tasks(status="pending", limit=1)
            if tasks:
                return {
                    "kind": "action",
                    "reason": "autonomous_task_pending",
                    "action": "execute_autonomous_task",
                    "task": tasks[0],
                }
        except Exception as exc:
            logger.warning("Failed to check autonomous tasks: %s", exc)

        # Check self-audit events (lower priority than restart and AgentDB tasks)
        audit_events = observation.get("self_audit_events", [])
        if audit_events:
            event = audit_events[0]
            signature = getattr(event, "signature", str(event))
            recommended_fix = "inspect_log_and_create_patch_task"
            auto_fixable = False
            if self._self_audit_loop and hasattr(self._self_audit_loop, "_recommend_fix"):
                try:
                    recommended_fix = self._self_audit_loop._recommend_fix(signature)
                except Exception:
                    pass
            if self._self_audit_loop:
                allowed = getattr(self._self_audit_loop, "allowed_fixes", set())
                auto_fixable = recommended_fix in allowed
            if auto_fixable:
                return {
                    "kind": "action",
                    "reason": "self_audit_event_detected",
                    "action": "execute_self_audit_fix",
                    "event_signature": signature,
                    "recommended_fix": recommended_fix,
                }

        return {"kind": "idle", "reason": "resident_openclaw_healthy"}

    # ------------------------------------------------------------------ #
    #  PLAN — build execution plan from triage                            #
    # ------------------------------------------------------------------ #

    def _plan(self, triage: Dict[str, Any], observation: Dict[str, Any]) -> Dict[str, Any]:
        plan: Dict[str, Any] = {
            "action": triage["action"],
            "target": "openclaw",
            "reason": triage["reason"],
            "git_dirty_files": observation["git"]["dirty_files"],
            "restart_budget": observation.get("restart_budget", {}),
            "next_restart_attempt": self._attempts_in_window() + 1,
            "task": triage.get("task"),
        }
        # Carry self-audit fix metadata into plan
        if triage["action"] == "execute_self_audit_fix":
            plan["event_signature"] = triage.get("event_signature")
            plan["recommended_fix"] = triage.get("recommended_fix")

        # WSP 77: AI Overseer fast classification (Gemma 50-100ms)
        if self._ai_overseer is not None:
            try:
                mission_desc = f"{triage['action']}: {triage.get('reason', 'supervisor cycle')}"
                analysis = self._ai_overseer.analyze_mission_requirements(mission_desc)
                plan["ai_analysis"] = _normalize_ai_analysis(analysis)
            except Exception as exc:
                logger.debug(f"[SUPERVISOR] AI Overseer analysis skipped: {exc}")
                plan["ai_analysis"] = {"error": str(exc)[:200]}

        return plan

    # ------------------------------------------------------------------ #
    #  EXECUTE — dispatch action                                          #
    # ------------------------------------------------------------------ #

    def _execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        broker = self._get_broker()
        if broker is None:
            return {"ok": False, "error": "broker_unavailable"}

        if plan["action"] == "start_openclaw":
            self._record_restart_attempt()
            result = broker.start_dae("openclaw", actor_id="0102")
            self._action_reporter(
                "supervisor_execute",
                result.get("status", result.get("error", "unknown")),
                {"plan": plan, "result": result},
            )
            return result

        elif plan["action"] == "execute_autonomous_task":
            task = plan.get("task", {})
            task_id = task.get("task_id")
            result: Dict[str, Any] = {"ok": False, "error": "unknown"}
            try:
                from modules.infrastructure.database.src.agent_db import AgentDB

                db = AgentDB()
                if task_id:
                    db.assign_autonomous_task(task_id, "openclaw_supervisor")

                    # In-process dispatch via run_task.execute_task()
                    from modules.communication.moltbot_bridge.scripts.run_task import (
                        execute_task,
                    )

                    task_result = execute_task(task_id, repo_root=self.repo_root)
                    result = {
                        "ok": task_result.get("ok", False),
                        "status": "completed" if task_result.get("ok") else "task_failed",
                        "executor": task_result.get("executor", "unknown"),
                        "detail": task_result.get("detail", "")[:1000],
                        "execution_time_ms": task_result.get("execution_time_ms", 0),
                    }
                else:
                    result = {"ok": False, "error": "no_task_id"}
            except Exception as exc:
                result = {"ok": False, "status": "execute_error", "error": str(exc)[:500]}

            self._action_reporter(
                "supervisor_execute",
                result.get("status", result.get("error", "unknown")),
                {"plan": plan, "result": result},
            )
            return result

        elif plan["action"] == "execute_self_audit_fix":
            recommended_fix = plan.get("recommended_fix", "")
            result: Dict[str, Any] = {"ok": False, "error": "no_audit_loop"}
            if self._self_audit_loop and hasattr(self._self_audit_loop, "_apply_policy_fix"):
                try:
                    success, detail = self._self_audit_loop._apply_policy_fix(recommended_fix)
                    result = {
                        "ok": success,
                        "status": "applied" if success else "fix_failed",
                        "detail": str(detail)[:500],
                    }
                except Exception as exc:
                    result = {"ok": False, "status": "fix_error", "error": str(exc)[:500]}

            self._action_reporter(
                "supervisor_execute",
                result.get("status", result.get("error", "unknown")),
                {"plan": plan, "result": result},
            )
            return result

        return {"ok": False, "error": "unsupported_action"}

    # ------------------------------------------------------------------ #
    #  VERIFY — check execution results                                   #
    # ------------------------------------------------------------------ #

    def _verify(self, plan: Dict[str, Any], action_result: Dict[str, Any]) -> Dict[str, Any]:
        broker = self._get_broker()
        if broker is None:
            return {"ok": False, "error": "broker_unavailable"}

        if plan["action"] == "execute_autonomous_task":
            task = plan.get("task", {})
            task_id = task.get("task_id")
            task_status = None

            try:
                from modules.infrastructure.database.src.agent_db import AgentDB

                db = AgentDB()
                completed_tasks = db.get_autonomous_tasks(status="completed", limit=100)
                if task_id and any(item.get("task_id") == task_id for item in completed_tasks):
                    task_status = "completed"
            except Exception as exc:
                logger.debug("[SUPERVISOR] VERIFY: task status check skipped: %s", exc)

            ok = bool(action_result.get("ok", False) and task_status == "completed")
            fidelity = 0.85  # Default

            # Gemma fidelity validation (unified from Supervisor24x7)
            if ok and self._libido_monitor and hasattr(self._libido_monitor, "validate_step_fidelity"):
                try:
                    validation = self._libido_monitor.validate_step_fidelity(
                        step_description=f"Task: {plan.get('task', {}).get('task_id', 'unknown')}",
                        step_output=str(action_result)[:500],
                    )
                    if isinstance(validation, dict):
                        fidelity = validation.get("fidelity", 0.85)
                    elif isinstance(validation, (int, float)):
                        fidelity = float(validation)
                    logger.debug("[SUPERVISOR] VERIFY: Gemma fidelity = %.3f", fidelity)
                except Exception as e:
                    logger.debug("[SUPERVISOR] VERIFY: Gemma validation skipped: %s", e)

            error = action_result.get("error", "")
            if not ok and not error and task_status != "completed":
                error = "task_not_completed"

            return {
                "ok": ok,
                "status": action_result,
                "task_status": task_status,
                "error": error,
                "fidelity": fidelity,
            }

        status = broker.get_runtime_status(plan["target"])
        running_states = {"starting", "running", "degraded"}
        ok = (
            action_result.get("status") in {"starting", "already_running"}
            and status.get("registered")
            and (
                status.get("running")
                or str(status.get("state", "")).lower() in running_states
            )
        )
        return {"ok": ok, "status": status, "error": status.get("last_error", "")}

    # ------------------------------------------------------------------ #
    #  REMEMBER — store outcomes and update metrics                       #
    # ------------------------------------------------------------------ #

    def _remember(
        self,
        observation: Dict[str, Any],
        plan_or_triage: Dict[str, Any],
        action_result: Dict[str, Any],
        verify: Dict[str, Any],
    ) -> None:
        # Update metrics
        self.metrics.cycles_completed += 1
        if action_result.get("ok"):
            self.metrics.tasks_executed += 1
            if verify.get("ok"):
                self.metrics.tasks_succeeded += 1

        # Report to daemon
        self._action_reporter(
            "supervisor_cycle",
            "recorded",
            {
                "state": self.current_state.value,
                "reason": self.last_reason,
                "plan": plan_or_triage,
                "action_result": action_result,
                "verify": verify,
                "git": observation.get("git", {}),
                "restart_budget": observation.get("restart_budget", {}),
                "openclaw_follow": observation.get("openclaw_follow", {}),
            },
        )

        # Store to PatternMemory using proper SkillOutcome dataclass
        if self._pattern_memory and action_result.get("ok"):
            try:
                from modules.infrastructure.wre_core.src.pattern_memory import SkillOutcome

                skill_name = plan_or_triage.get("action", "unknown")
                fidelity = float(verify.get("fidelity", 0.85))
                outcome = SkillOutcome(
                    execution_id=f"supervisor_{uuid.uuid4().hex[:12]}",
                    skill_name=skill_name,
                    agent="openclaw_supervisor",
                    timestamp=datetime.now().isoformat(),
                    input_context=json.dumps(plan_or_triage, default=str)[:2000],
                    output_result=json.dumps(action_result, default=str)[:2000],
                    success=bool(verify.get("ok", False)),
                    pattern_fidelity=fidelity,
                    outcome_quality=1.0 if verify.get("ok") else 0.0,
                    execution_time_ms=int(action_result.get("execution_time_ms", 0)),
                    step_count=1,
                    notes=f"Supervisor cycle: {plan_or_triage.get('reason', '')}",
                )
                self._pattern_memory.store_outcome(outcome)
                logger.debug(
                    "[SUPERVISOR] REMEMBER: Stored SkillOutcome for %s (fidelity=%.3f)",
                    skill_name,
                    fidelity,
                )
            except Exception as e:
                logger.debug("[SUPERVISOR] REMEMBER: PatternMemory storage skipped: %s", e)

        follow = observation.get("openclaw_follow", {})
        self._event_cursor = int(follow.get("next_cursor", self._event_cursor) or self._event_cursor)

    # ------------------------------------------------------------------ #
    #  Utility helpers                                                    #
    # ------------------------------------------------------------------ #

    def _git_summary(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain", "--branch"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            lines = result.stdout.splitlines()
            branch = lines[0].strip() if lines else "unknown"
            dirty_files = max(len(lines) - 1, 0)
            return {"branch": branch, "dirty_files": dirty_files}
        except Exception as exc:
            return {"branch": "unknown", "dirty_files": -1, "error": str(exc)[:200]}

    def _attempts_in_window(self) -> int:
        now = time.time()
        self._prune_restart_attempts(now)
        return len(self._restart_attempts)

    def _can_attempt_restart(self) -> bool:
        return self._attempts_in_window() < self.max_restart_attempts

    def _record_restart_attempt(self) -> None:
        now = time.time()
        self._prune_restart_attempts(now)
        self._restart_attempts.append(now)

    def _prune_restart_attempts(self, now: float) -> None:
        cutoff = now - self.restart_window_sec
        while self._restart_attempts and self._restart_attempts[0] < cutoff:
            self._restart_attempts.popleft()
