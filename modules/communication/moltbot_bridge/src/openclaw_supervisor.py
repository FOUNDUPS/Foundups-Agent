#!/usr/bin/env python3
"""Explicit OpenClaw 24/7 supervisor state machine."""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Deque, Dict, Optional

logger = logging.getLogger(__name__)


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


class OpenClawSupervisor:
    """Canonical 0102 supervisor for the resident OpenClaw runtime."""

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

    def stop(self) -> None:
        self._stop_event.set()
        self._stop_self_audit()

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

    def _stop_self_audit(self) -> None:
        if self._self_audit_loop is None:
            return
        try:
            self._self_audit_loop.stop()
        finally:
            self._self_audit_loop = None

    def _observe(self) -> Dict[str, Any]:
        broker = self._get_broker()
        observer = self._get_observer()
        return {
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
        }

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

        return {"kind": "idle", "reason": "resident_openclaw_healthy"}

    def _plan(self, triage: Dict[str, Any], observation: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": triage["action"],
            "target": "openclaw",
            "reason": triage["reason"],
            "git_dirty_files": observation["git"]["dirty_files"],
            "restart_budget": observation.get("restart_budget", {}),
            "next_restart_attempt": self._attempts_in_window() + 1,
        }

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
        return {"ok": False, "error": "unsupported_action"}

    def _verify(self, plan: Dict[str, Any], action_result: Dict[str, Any]) -> Dict[str, Any]:
        broker = self._get_broker()
        if broker is None:
            return {"ok": False, "error": "broker_unavailable"}
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

    def _remember(
        self,
        observation: Dict[str, Any],
        plan_or_triage: Dict[str, Any],
        action_result: Dict[str, Any],
        verify: Dict[str, Any],
    ) -> None:
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
        follow = observation.get("openclaw_follow", {})
        self._event_cursor = int(follow.get("next_cursor", self._event_cursor) or self._event_cursor)

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
