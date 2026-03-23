#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
24/7 Supervisor State Machine - DONOR/PROTOTYPE

⚠️  DEPRECATION NOTICE (2026-03-22):
    This module is a DONOR/PROTOTYPE, not the canonical supervisor.
    The canonical supervisor is: modules/communication/moltbot_bridge/src/openclaw_supervisor.py

    Key behaviors from this file have been unified into OpenClawSupervisor:
    - AI Overseer integration (PLAN)
    - PatternMemory (REMEMBER)
    - LibidoMonitor/Gemma fidelity (VERIFY)
    - SupervisorMetrics telemetry

    DO NOT use this module for production. Use OpenClawSupervisor instead.
    This file is preserved for reference and potential future backports.

WSP Compliance:
- WSP 49: Module structure
- WSP 77: Agent coordination (Qwen/Gemma via AI Overseer)
- WSP 91: Observability (telemetry, logging)
- WSP 96: Libido monitor integration
- WSP 97: CoT/CoR gates (embedded in WRE/AI Overseer)

Architecture:
    BOOT → PREFLIGHT → OBSERVE → TRIAGE → PLAN → EXECUTE → VERIFY → REMEMBER → ESCALATE → IDLE_WATCH
      ↑_______________________________________________________________________________|

Layer 2 Enhancement (2026-03-11):
- OBSERVE: Real event polling from DaemonSelfAuditLoop
- EXECUTE: Real skill calls via WREMasterOrchestrator
- VERIFY: Real Gemma fidelity validation
- REMEMBER: Real SQLite outcome storage

Key Insight: "The 24/7 system should be state-driven, not chat-driven."
Source: OPENCLAW_0102_HANDOFF_2026-03-07.md
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SupervisorState(Enum):
    """10-state machine states."""

    BOOT = "boot"
    PREFLIGHT = "preflight"
    OBSERVE = "observe"
    TRIAGE = "triage"
    PLAN = "plan"
    EXECUTE = "execute"
    VERIFY = "verify"
    REMEMBER = "remember"
    ESCALATE = "escalate"
    IDLE_WATCH = "idle_watch"


@dataclass
class SupervisorMetrics:
    """Telemetry for observability (WSP 91)."""

    cycles_completed: int = 0
    events_observed: int = 0
    fixes_attempted: int = 0
    fixes_succeeded: int = 0
    escalations_triggered: int = 0
    last_state_change: float = field(default_factory=time.time)
    state_durations: Dict[str, float] = field(default_factory=dict)


@dataclass
class TriageTask:
    """Task queued for execution."""

    event_signature: str
    source_file: str
    recommended_fix: str
    auto_fixable: bool
    priority: int = 1
    timestamp: float = field(default_factory=time.time)


class Supervisor24x7:
    """
    24/7 Autonomous Supervisor - Orchestrates existing components.

    NOT reinventing - ORCHESTRATING:
    - DaemonSelfAuditLoop for OBSERVE/TRIAGE/ESCALATE
    - AIIntelligenceOverseer for PLAN
    - WREMasterOrchestrator for EXECUTE
    - PatternMemory for REMEMBER
    - LibidoMonitor for VERIFY
    """

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()
        self.state = SupervisorState.BOOT
        self.metrics = SupervisorMetrics()
        self._stop_event = asyncio.Event()

        # Configuration from environment
        self.interval_sec = float(os.getenv("SUPERVISOR_24X7_INTERVAL_SEC", "5"))
        self.enabled = os.getenv("SUPERVISOR_24X7_ENABLED", "1") == "1"

        # Components (lazy loaded in BOOT)
        self._audit_loop: Any = None
        self._ai_overseer: Any = None
        self._wre_orchestrator: Any = None
        self._pattern_memory: Any = None
        self._libido_monitor: Any = None

        # Current cycle state
        self._current_events: List[Any] = []
        self._triage_queue: List[TriageTask] = []
        self._execution_results: List[Dict[str, Any]] = []

        logger.info(f"[SUPERVISOR] Initialized at {self.repo_root}")

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    async def run(self) -> None:
        """Main state machine loop."""
        if not self.enabled:
            logger.warning("[SUPERVISOR] Disabled via SUPERVISOR_24X7_ENABLED=0")
            return

        logger.info("[SUPERVISOR] Starting 24/7 state machine loop")
        while not self._stop_event.is_set():
            try:
                await self._execute_current_state()
            except Exception as e:
                logger.error(f"[SUPERVISOR] State {self.state.value} failed: {e}")
                self._transition_to(SupervisorState.IDLE_WATCH)

            await asyncio.sleep(0.1)

        logger.info("[SUPERVISOR] Stopped")

    async def stop(self) -> None:
        """Signal graceful shutdown."""
        logger.info("[SUPERVISOR] Stop requested")
        self._stop_event.set()

    def get_state(self) -> SupervisorState:
        """Return current state."""
        return self.state

    def get_metrics(self) -> Dict[str, Any]:
        """Return telemetry metrics."""
        return {
            "state": self.state.value,
            "cycles_completed": self.metrics.cycles_completed,
            "events_observed": self.metrics.events_observed,
            "fixes_attempted": self.metrics.fixes_attempted,
            "fixes_succeeded": self.metrics.fixes_succeeded,
            "escalations_triggered": self.metrics.escalations_triggered,
            "uptime_seconds": time.time() - self.metrics.last_state_change,
        }

    # =========================================================================
    # STATE MACHINE
    # =========================================================================

    async def _execute_current_state(self) -> None:
        """Execute handler for current state."""
        handler = getattr(self, f"_handle_{self.state.value}", None)
        if handler:
            start_time = time.time()
            await handler()
            duration = time.time() - start_time
            self.metrics.state_durations[self.state.value] = duration

    def _transition_to(self, new_state: SupervisorState) -> None:
        """Transition to new state with logging."""
        old_state = self.state
        self.state = new_state
        self.metrics.last_state_change = time.time()
        logger.debug(f"[SUPERVISOR] {old_state.value} -> {new_state.value}")

    # =========================================================================
    # STATE HANDLERS - LAYER 2 (Real Wiring)
    # =========================================================================

    async def _handle_boot(self) -> None:
        """BOOT: Initialize all subsystems."""
        logger.info("[SUPERVISOR] BOOT: Initializing subsystems")

        # Load DaemonSelfAuditLoop
        try:
            from modules.infrastructure.wre_core.src.daemon_self_audit_loop import (
                DaemonSelfAuditLoop,
            )

            self._audit_loop = DaemonSelfAuditLoop(self.repo_root)
            self._audit_loop.start()
            logger.info("[SUPERVISOR] BOOT: DaemonSelfAuditLoop started")
        except ImportError as e:
            logger.warning(f"[SUPERVISOR] BOOT: DaemonSelfAuditLoop unavailable: {e}")

        # Load AI Overseer
        try:
            from modules.ai_intelligence.ai_overseer.src.ai_overseer import (
                AIIntelligenceOverseer,
            )

            self._ai_overseer = AIIntelligenceOverseer(repo_root=self.repo_root)
            logger.info("[SUPERVISOR] BOOT: AIIntelligenceOverseer loaded")
        except ImportError as e:
            logger.warning(f"[SUPERVISOR] BOOT: AIIntelligenceOverseer unavailable: {e}")

        # Load WRE Master Orchestrator
        try:
            from modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_master_orchestrator import (
                WREMasterOrchestrator,
            )

            self._wre_orchestrator = WREMasterOrchestrator()
            logger.info("[SUPERVISOR] BOOT: WREMasterOrchestrator loaded")
        except ImportError as e:
            logger.warning(f"[SUPERVISOR] BOOT: WREMasterOrchestrator unavailable: {e}")

        # Load Pattern Memory
        try:
            from modules.infrastructure.wre_core.src.pattern_memory import (
                PatternMemory,
            )

            db_path = self.repo_root / "modules/infrastructure/wre_core/memory/pattern_memory.db"
            self._pattern_memory = PatternMemory(db_path=db_path)
            logger.info("[SUPERVISOR] BOOT: PatternMemory loaded")
        except (ImportError, Exception) as e:
            logger.warning(f"[SUPERVISOR] BOOT: PatternMemory unavailable: {e}")

        # Load Libido Monitor (Layer 2)
        try:
            from modules.infrastructure.wre_core.src.libido_monitor import (
                GemmaLibidoMonitor,
            )

            self._libido_monitor = GemmaLibidoMonitor()
            logger.info("[SUPERVISOR] BOOT: LibidoMonitor loaded")
        except (ImportError, Exception) as e:
            logger.warning(f"[SUPERVISOR] BOOT: LibidoMonitor unavailable: {e}")

        # Wire GitHub Orchestrator to FAM (WSP 103)
        try:
            from modules.infrastructure.github_orchestrator import wire_github_to_fam

            if wire_github_to_fam():
                logger.info("[SUPERVISOR] BOOT: GitHub Orchestrator wired to FAM")
            else:
                logger.warning("[SUPERVISOR] BOOT: GitHub Orchestrator wiring failed")
        except ImportError as e:
            logger.warning(f"[SUPERVISOR] BOOT: GitHub Orchestrator unavailable: {e}")

        self._transition_to(SupervisorState.PREFLIGHT)

    async def _handle_preflight(self) -> None:
        """PREFLIGHT: Run validation gates."""
        logger.info("[SUPERVISOR] PREFLIGHT: Running validation gates")

        preflight_results: Dict[str, bool] = {}

        # Check critical environment
        preflight_results["env_loaded"] = os.getenv("FOUNDUPS_AGENT_ROOT") is not None

        # Check daemon self-audit is running
        preflight_results["audit_loop_active"] = (
            self._audit_loop is not None
            and hasattr(self._audit_loop, "_thread")
            and self._audit_loop._thread is not None
            and self._audit_loop._thread.is_alive()
        )

        # Check WRE orchestrator
        preflight_results["wre_orchestrator_loaded"] = self._wre_orchestrator is not None

        # Check pattern memory
        preflight_results["pattern_memory_loaded"] = self._pattern_memory is not None

        # Log preflight results
        passed = sum(preflight_results.values())
        total = len(preflight_results)
        logger.info(f"[SUPERVISOR] PREFLIGHT: {passed}/{total} checks passed - {preflight_results}")

        self._transition_to(SupervisorState.OBSERVE)

    async def _handle_observe(self) -> None:
        """OBSERVE: Poll real events from DaemonSelfAuditLoop (Layer 2)."""
        logger.debug("[SUPERVISOR] OBSERVE: Scanning for events")

        self._current_events = []

        if self._audit_loop:
            # Layer 2: Call scan_once() for real event detection
            try:
                events = self._audit_loop.scan_once()
                if events:
                    self._current_events = list(events)
                    self.metrics.events_observed += len(self._current_events)
            except Exception as e:
                logger.warning(f"[SUPERVISOR] OBSERVE: scan_once() failed: {e}")
                # Fallback to cached events
                events = getattr(self._audit_loop, "_recent_events", [])
                self._current_events = list(events)
                self.metrics.events_observed += len(self._current_events)

        # Layer 2.1: antifaFM DJ audio health check (if OBS mode active)
        await self._observe_antifafm_audio()

        if self._current_events:
            logger.info(f"[SUPERVISOR] OBSERVE: {len(self._current_events)} events detected")
            self._transition_to(SupervisorState.TRIAGE)
        else:
            self._transition_to(SupervisorState.IDLE_WATCH)

    async def _observe_antifafm_audio(self) -> None:
        """Check antifaFM audio health via antifafm_dj skill."""
        # Only check if antifaFM OBS mode is active
        if os.getenv("ANTIFAFM_USE_OBS", "0") != "1":
            return

        try:
            from modules.ai_intelligence.ai_overseer.skillz.antifafm_dj import (
                check_audio_health,
            )

            health = check_audio_health()
            if not health.get("healthy"):
                # Create synthetic event for audio issue
                issues = health.get("issues", ["audio_not_healthy"])
                event = type("AudioEvent", (), {
                    "signature": f"antifafm_audio_unhealthy:{','.join(issues)}",
                    "source_file": "antifafm_dj",
                    "auto_fixable": True,
                    "recommended_fix": "restart_antifafm_audio",
                })()
                self._current_events.append(event)
                self.metrics.events_observed += 1
                logger.warning(f"[SUPERVISOR] OBSERVE: antifaFM audio unhealthy: {issues}")
        except ImportError:
            pass  # antifafm_dj skill not available
        except Exception as e:
            logger.debug(f"[SUPERVISOR] OBSERVE: antifaFM audio check skipped: {e}")

    async def _handle_triage(self) -> None:
        """TRIAGE: Classify issues using DaemonSelfAuditLoop's _recommend_fix (Layer 2)."""
        logger.info(f"[SUPERVISOR] TRIAGE: Processing {len(self._current_events)} events")

        self._triage_queue = []

        for event in self._current_events:
            signature = getattr(event, "signature", str(event))
            source_file = getattr(event, "source_file", "unknown")

            # Layer 2: Use audit loop's recommendation if available
            recommended_fix = "inspect_log_and_create_patch_task"
            if self._audit_loop and hasattr(self._audit_loop, "_recommend_fix"):
                try:
                    recommended_fix = self._audit_loop._recommend_fix(signature)
                except Exception:
                    pass

            # Determine if auto-fixable based on audit loop's allowed_fixes
            auto_fixable = False
            if self._audit_loop:
                allowed = getattr(self._audit_loop, "allowed_fixes", set())
                auto_fixable = recommended_fix in allowed

            task = TriageTask(
                event_signature=signature,
                source_file=source_file,
                recommended_fix=recommended_fix,
                auto_fixable=auto_fixable,
            )
            self._triage_queue.append(task)

        if self._triage_queue:
            logger.info(f"[SUPERVISOR] TRIAGE: {len(self._triage_queue)} tasks queued")
            self._transition_to(SupervisorState.PLAN)
        else:
            self._transition_to(SupervisorState.IDLE_WATCH)

    async def _handle_plan(self) -> None:
        """PLAN: Route to AI Overseer for strategic planning (Layer 2)."""
        logger.info("[SUPERVISOR] PLAN: Creating coordination plan")

        auto_tasks = [t for t in self._triage_queue if t.auto_fixable]
        non_auto_tasks = [t for t in self._triage_queue if not t.auto_fixable]

        # Layer 2: Real AI Overseer routing for non-auto tasks
        if non_auto_tasks and self._ai_overseer:
            try:
                mission_context = {
                    "mission_type": "daemon_monitoring",
                    "tasks": [
                        {"signature": t.event_signature, "fix": t.recommended_fix}
                        for t in non_auto_tasks
                    ],
                }
                # Call AI Overseer's quick_response for strategic guidance
                if hasattr(self._ai_overseer, "quick_response"):
                    guidance = self._ai_overseer.quick_response(
                        f"Supervisor triage: {len(non_auto_tasks)} tasks need strategic planning. "
                        f"Tasks: {mission_context['tasks'][:3]}. Recommend action priority."
                    )
                    logger.info(f"[SUPERVISOR] PLAN: AI Overseer guidance: {guidance[:200] if guidance else 'none'}")
            except Exception as e:
                logger.warning(f"[SUPERVISOR] PLAN: AI Overseer routing failed: {e}")

        self._transition_to(SupervisorState.EXECUTE)

    async def _handle_execute(self) -> None:
        """EXECUTE: Run fixes via WRE or DaemonSelfAuditLoop (Layer 2)."""
        logger.info(f"[SUPERVISOR] EXECUTE: Processing {len(self._triage_queue)} tasks")

        self._execution_results = []

        for task in self._triage_queue:
            result = {"task": task.event_signature, "fix": task.recommended_fix, "success": False, "detail": ""}

            if task.auto_fixable:
                # Layer 2.1: Handle antifaFM audio restart
                if task.recommended_fix == "restart_antifafm_audio":
                    try:
                        from modules.ai_intelligence.ai_overseer.skillz.antifafm_dj import (
                            restart_audio_source,
                        )
                        restart_result = restart_audio_source()
                        result["success"] = restart_result.get("success", False)
                        result["detail"] = str(restart_result)
                        self.metrics.fixes_attempted += 1
                        if result["success"]:
                            self.metrics.fixes_succeeded += 1
                        logger.info(f"[SUPERVISOR] EXECUTE: antifaFM audio restart -> {'OK' if result['success'] else 'FAIL'}")
                    except Exception as e:
                        result["detail"] = str(e)
                        logger.warning(f"[SUPERVISOR] EXECUTE: antifaFM audio restart failed: {e}")
                    self._execution_results.append(result)
                    continue

                # Layer 2: Use audit loop's _apply_policy_fix for real execution
                elif self._audit_loop and hasattr(self._audit_loop, "_apply_policy_fix"):
                    try:
                        success, detail = self._audit_loop._apply_policy_fix(task.recommended_fix)
                        result["success"] = success
                        result["detail"] = detail
                        self.metrics.fixes_attempted += 1
                        if success:
                            self.metrics.fixes_succeeded += 1
                        logger.info(f"[SUPERVISOR] EXECUTE: {task.recommended_fix} -> {'OK' if success else 'FAIL'}: {detail}")
                    except Exception as e:
                        result["detail"] = str(e)
                        logger.warning(f"[SUPERVISOR] EXECUTE: {task.recommended_fix} exception: {e}")
                elif self._wre_orchestrator and hasattr(self._wre_orchestrator, "execute_skill"):
                    # Fallback to WRE orchestrator
                    try:
                        wre_result = self._wre_orchestrator.execute_skill(
                            skill_name=task.recommended_fix,
                            agent="qwen",
                            input_context={"event_signature": task.event_signature},
                        )
                        result["success"] = wre_result.get("success", False)
                        result["detail"] = str(wre_result)
                        self.metrics.fixes_attempted += 1
                        if result["success"]:
                            self.metrics.fixes_succeeded += 1
                    except Exception as e:
                        result["detail"] = str(e)
            else:
                result["detail"] = "non_auto_fixable_skipped"

            self._execution_results.append(result)

        self._transition_to(SupervisorState.VERIFY)

    async def _handle_verify(self) -> None:
        """VERIFY: Validate execution fidelity with Gemma (Layer 2)."""
        logger.debug("[SUPERVISOR] VERIFY: Checking execution results")

        for result in self._execution_results:
            if not result.get("success"):
                continue

            fidelity = 0.85  # Default fidelity

            # Layer 2: Real Gemma validation if libido monitor available
            if self._libido_monitor and hasattr(self._libido_monitor, "validate_step_fidelity"):
                try:
                    validation = self._libido_monitor.validate_step_fidelity(
                        step_description=f"Fix: {result['fix']} for {result['task']}",
                        step_output=result["detail"],
                    )
                    if isinstance(validation, dict):
                        fidelity = validation.get("fidelity", 0.85)
                    elif isinstance(validation, (int, float)):
                        fidelity = float(validation)
                except Exception as e:
                    logger.warning(f"[SUPERVISOR] VERIFY: Gemma validation failed: {e}")

            result["fidelity"] = fidelity

            if fidelity >= 0.618:
                logger.info(f"[SUPERVISOR] VERIFY: {result['fix']} fidelity {fidelity:.3f} >= 0.618 OK")
            else:
                logger.warning(f"[SUPERVISOR] VERIFY: {result['fix']} fidelity {fidelity:.3f} < 0.618 - flagging")

        self._transition_to(SupervisorState.REMEMBER)

    async def _handle_remember(self) -> None:
        """REMEMBER: Store outcomes to SQLite pattern memory (Layer 2)."""
        logger.debug("[SUPERVISOR] REMEMBER: Storing outcomes")

        if self._pattern_memory and self._execution_results:
            for result in self._execution_results:
                try:
                    # Layer 2: Real SQLite storage
                    if hasattr(self._pattern_memory, "store_outcome"):
                        outcome = {
                            "skill_name": result.get("fix", "unknown"),
                            "success": result.get("success", False),
                            "fidelity": result.get("fidelity", 0.0),
                            "context": result.get("task", ""),
                            "timestamp": datetime.now().isoformat(),
                        }
                        self._pattern_memory.store_outcome(outcome)
                        logger.debug(f"[SUPERVISOR] REMEMBER: Stored outcome for {result['fix']}")
                except Exception as e:
                    logger.warning(f"[SUPERVISOR] REMEMBER: Storage failed: {e}")

        self._transition_to(SupervisorState.ESCALATE)

    async def _handle_escalate(self) -> None:
        """ESCALATE: Check escalation conditions via DaemonSelfAuditLoop (Layer 2)."""
        logger.debug("[SUPERVISOR] ESCALATE: Checking escalation conditions")

        needs_escalation = False
        escalation_reasons = []

        # Layer 2: Check audit loop's escalation state
        if self._audit_loop:
            # Check for repeated failures
            stats = getattr(self._audit_loop, "_signature_stats", {})
            escalate_after = getattr(self._audit_loop, "escalate_after", 3)

            for sig, sig_stats in stats.items():
                count = sig_stats.get("count", 0)
                if count >= escalate_after:
                    needs_escalation = True
                    escalation_reasons.append(f"{sig}: {count} occurrences")

        if needs_escalation:
            self.metrics.escalations_triggered += 1
            logger.warning(f"[SUPERVISOR] ESCALATE: Triggered - {escalation_reasons}")

            # Layer 2: Dispatch escalation if configured
            if self._audit_loop and hasattr(self._audit_loop, "_dispatch_escalation"):
                try:
                    self._audit_loop._dispatch_escalation(escalation_reasons)
                except Exception as e:
                    logger.error(f"[SUPERVISOR] ESCALATE: Dispatch failed: {e}")

        self._transition_to(SupervisorState.IDLE_WATCH)

    async def _handle_idle_watch(self) -> None:
        """IDLE_WATCH: Wait for next cycle."""
        self.metrics.cycles_completed += 1
        logger.debug(f"[SUPERVISOR] IDLE_WATCH: Cycle {self.metrics.cycles_completed} complete, waiting {self.interval_sec}s")

        try:
            await asyncio.wait_for(
                self._stop_event.wait(),
                timeout=self.interval_sec,
            )
        except asyncio.TimeoutError:
            pass

        self._transition_to(SupervisorState.OBSERVE)
