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

READONLY_AUDIT_OPENCLAW_CLAIM_ACCEPT = "READONLY_AUDIT_OPENCLAW_CLAIM_ACCEPT"
READONLY_AUDIT_OPENCLAW_CLAIM_IDLE = "READONLY_AUDIT_OPENCLAW_CLAIM_IDLE"
READONLY_AUDIT_OPENCLAW_CLAIM_REJECT = "READONLY_AUDIT_OPENCLAW_CLAIM_REJECT"
SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT = "SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT"
SIGNED_WORKER_OPENCLAW_CLAIM_IDLE = "SIGNED_WORKER_OPENCLAW_CLAIM_IDLE"
SIGNED_WORKER_OPENCLAW_CLAIM_REJECT = "SIGNED_WORKER_OPENCLAW_CLAIM_REJECT"


class ReadOnlyAuditOpenClawClaimReason:
    NO_PENDING_TASK = "NO_PENDING_REDDOG_READONLY_AUDIT_TASK"
    CLAIM_RACE_LOST = "REJECT_REDDOG_READONLY_AUDIT_CLAIM_RACE_LOST"
    MALFORMED_CONTEXT = "REJECT_REDDOG_READONLY_AUDIT_MALFORMED_CONTEXT"
    TASK_EXECUTION_REJECTED = "REJECT_REDDOG_READONLY_AUDIT_TASK_EXECUTION_REJECTED"
    REPORT_PERSIST_REJECTED = "REJECT_REDDOG_READONLY_AUDIT_REPORT_PERSIST_REJECTED"
    AGENTDB_FAILURE = "REJECT_REDDOG_READONLY_AUDIT_AGENTDB_FAILURE"


class SignedWorkerOpenClawClaimReason:
    NO_PENDING_TASK = "NO_PENDING_REDDOG_SIGNED_WORKER_TASK"
    CLAIM_RACE_LOST = "REJECT_REDDOG_SIGNED_WORKER_CLAIM_RACE_LOST"
    MALFORMED_CONTEXT = "REJECT_REDDOG_SIGNED_WORKER_MALFORMED_CONTEXT"
    TASK_EXECUTION_REJECTED = "REJECT_REDDOG_SIGNED_WORKER_TASK_EXECUTION_REJECTED"
    AGENTDB_FAILURE = "REJECT_REDDOG_SIGNED_WORKER_AGENTDB_FAILURE"


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


def claim_reddog_readonly_audit_task_once(
    *,
    repo_root: Path,
    agent_id: str = "openclaw_supervisor",
    agent_db_factory: Optional[Callable[[], Any]] = None,
    report_store: Any | None = None,
    audit_model_runner: Any | None = None,
    holoindex_adapter: Any | None = None,
    codeindex_adapter: Any | None = None,
    external_research_retriever: Any | None = None,
    timeout_seconds: int = 60,
) -> Dict[str, Any]:
    """Claim and execute one RedDog read-only audit AgentDB task.

    This is the OpenClaw-owned execution seam for resident RedDog cycles. It
    atomically claims a pending RedDog read-only audit task from AgentDB, runs
    the existing read-only task executor, persists the report, and marks the
    AgentDB task complete. It does not run shell commands, mutate repo files,
    create worktrees, dispatch Hermes, create PRs, or re-index HoloIndex.
    """

    try:
        from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
            READONLY_AUDIT_TASK_SOURCE,
        )
        from modules.communication.moltbot_bridge.src.reddog_readonly_audit_report_collection import (
            AgentDbReadOnlyAuditReportStore,
            persist_reddog_readonly_audit_task_report,
        )
        from modules.communication.moltbot_bridge.src.reddog_readonly_audit_task_executor import (
            execute_reddog_readonly_audit_task,
        )
        from modules.infrastructure.database.src.agent_db import AgentDB

        factory = agent_db_factory or AgentDB
        db = factory()
        task = _claim_pending_reddog_readonly_audit_task(
            db=db,
            agent_id=agent_id,
            source=READONLY_AUDIT_TASK_SOURCE,
        )
    except Exception as exc:
        return _readonly_claim_result(
            accepted=False,
            status=READONLY_AUDIT_OPENCLAW_CLAIM_REJECT,
            rejection_reasons=(ReadOnlyAuditOpenClawClaimReason.AGENTDB_FAILURE,),
            detail=str(exc)[:300],
        )

    if task is None:
        return _readonly_claim_result(
            accepted=False,
            status=READONLY_AUDIT_OPENCLAW_CLAIM_IDLE,
            rejection_reasons=(ReadOnlyAuditOpenClawClaimReason.NO_PENDING_TASK,),
        )
    if task.get("claim_race_lost"):
        return _readonly_claim_result(
            accepted=False,
            status=READONLY_AUDIT_OPENCLAW_CLAIM_REJECT,
            task_id=str(task.get("task_id") or ""),
            rejection_reasons=(ReadOnlyAuditOpenClawClaimReason.CLAIM_RACE_LOST,),
        )

    task_id = str(task.get("task_id") or "")
    context = task.get("context")
    if not isinstance(context, dict):
        _mark_reddog_readonly_audit_task_failed(db, task_id)
        return _readonly_claim_result(
            accepted=False,
            status=READONLY_AUDIT_OPENCLAW_CLAIM_REJECT,
            task_id=task_id,
            rejection_reasons=(ReadOnlyAuditOpenClawClaimReason.MALFORMED_CONTEXT,),
        )

    run_result = execute_reddog_readonly_audit_task(
        task_context=context,
        repo_root=repo_root,
        task_id=task_id,
        model_runner=audit_model_runner,
        holoindex_adapter=holoindex_adapter,
        codeindex_adapter=codeindex_adapter,
        external_research_retriever=external_research_retriever,
        timeout_seconds=timeout_seconds,
    )
    if not run_result.accepted:
        _mark_reddog_readonly_audit_task_failed(db, task_id)
        return _readonly_claim_result(
            accepted=False,
            status=READONLY_AUDIT_OPENCLAW_CLAIM_REJECT,
            task_id=task_id,
            assignment_id=_readonly_assignment_id(context),
            rejection_reasons=(
                ReadOnlyAuditOpenClawClaimReason.TASK_EXECUTION_REJECTED,
                *run_result.rejection_reasons,
            ),
        )

    store = report_store or AgentDbReadOnlyAuditReportStore(agent_db_factory=factory)
    persist_result = persist_reddog_readonly_audit_task_report(
        task_id=task_id,
        task_context=context,
        task_result={
            "ok": True,
            "executor": "openclaw_supervisor:reddog_readonly_audit",
            "structured_result": run_result.to_dict(),
        },
        store=store,
    )
    if not persist_result.accepted:
        _mark_reddog_readonly_audit_task_failed(db, task_id)
        return _readonly_claim_result(
            accepted=False,
            status=READONLY_AUDIT_OPENCLAW_CLAIM_REJECT,
            task_id=task_id,
            assignment_id=_readonly_assignment_id(context),
            rejection_reasons=(
                ReadOnlyAuditOpenClawClaimReason.REPORT_PERSIST_REJECTED,
                *persist_result.rejection_reasons,
            ),
        )

    db.complete_autonomous_task(task_id)
    report = run_result.report if isinstance(run_result.report, dict) else {}
    return _readonly_claim_result(
        accepted=True,
        status=READONLY_AUDIT_OPENCLAW_CLAIM_ACCEPT,
        task_id=task_id,
        assignment_id=_readonly_assignment_id(context),
        report_digest=str(report.get("report_digest") or ""),
    )


def claim_reddog_signed_worker_dispatch_task_once(
    *,
    repo_root: Path,
    agent_id: str = "openclaw_supervisor",
    agent_db_factory: Optional[Callable[[], Any]] = None,
    signed_worker_runner: Any | None = None,
) -> Dict[str, Any]:
    """Claim and execute one signed RedDog worker-dispatch AgentDB task.

    This is the OpenClaw-owned consumer for tasks published by the signed
    worker-dispatch runtime. The task is claimed atomically from AgentDB and
    then validated by the signed-worker task executor. A real worker runner
    must be injected; no default runner is created here.
    """

    try:
        from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
            SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        )
        from modules.communication.moltbot_bridge.src.reddog_signed_worker_dispatch_task_executor import (
            execute_reddog_signed_worker_dispatch_task,
        )
        from modules.communication.moltbot_bridge.src.reddog_signed_worker_openclaw_queue_loop_runtime_binding import (
            build_reddog_signed_worker_queue_loop_runner_from_env,
        )
        from modules.infrastructure.database.src.agent_db import AgentDB

        factory = agent_db_factory or AgentDB
        db = factory()
        task = _claim_pending_reddog_signed_worker_dispatch_task(
            db=db,
            agent_id=agent_id,
            source=SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        )
    except Exception as exc:
        return _signed_worker_claim_result(
            accepted=False,
            status=SIGNED_WORKER_OPENCLAW_CLAIM_REJECT,
            rejection_reasons=(SignedWorkerOpenClawClaimReason.AGENTDB_FAILURE,),
            detail=str(exc)[:300],
        )

    if task is None:
        return _signed_worker_claim_result(
            accepted=False,
            status=SIGNED_WORKER_OPENCLAW_CLAIM_IDLE,
            rejection_reasons=(SignedWorkerOpenClawClaimReason.NO_PENDING_TASK,),
        )
    if task.get("claim_race_lost"):
        return _signed_worker_claim_result(
            accepted=False,
            status=SIGNED_WORKER_OPENCLAW_CLAIM_REJECT,
            task_id=str(task.get("task_id") or ""),
            rejection_reasons=(SignedWorkerOpenClawClaimReason.CLAIM_RACE_LOST,),
        )

    task_id = str(task.get("task_id") or "")
    context = task.get("context")
    if not isinstance(context, dict):
        _mark_reddog_signed_worker_dispatch_task_failed(db, task_id)
        return _signed_worker_claim_result(
            accepted=False,
            status=SIGNED_WORKER_OPENCLAW_CLAIM_REJECT,
            task_id=task_id,
            rejection_reasons=(SignedWorkerOpenClawClaimReason.MALFORMED_CONTEXT,),
        )

    effective_runner = signed_worker_runner
    if effective_runner is None:
        binding_result = build_reddog_signed_worker_queue_loop_runner_from_env(
            repo_root=repo_root,
            env=os.environ,
        )
        if binding_result.accepted:
            effective_runner = binding_result.runner
        elif binding_result.requested:
            _mark_reddog_signed_worker_dispatch_task_failed(db, task_id)
            return _signed_worker_claim_result(
                accepted=False,
                status=SIGNED_WORKER_OPENCLAW_CLAIM_REJECT,
                task_id=task_id,
                rejection_reasons=(
                    SignedWorkerOpenClawClaimReason.TASK_EXECUTION_REJECTED,
                    *binding_result.rejection_reasons,
                ),
            )

    run_result = execute_reddog_signed_worker_dispatch_task(
        task_context=context,
        task_id=task_id,
        repo_root=repo_root,
        runner=effective_runner,
    )
    if not run_result.accepted:
        _mark_reddog_signed_worker_dispatch_task_failed(db, task_id)
        return _signed_worker_claim_result(
            accepted=False,
            status=SIGNED_WORKER_OPENCLAW_CLAIM_REJECT,
            task_id=task_id,
            worker_role=run_result.worker_role,
            worker_runtime=run_result.worker_runtime,
            capability=run_result.capability,
            rejection_reasons=(
                SignedWorkerOpenClawClaimReason.TASK_EXECUTION_REJECTED,
                *run_result.rejection_reasons,
            ),
        )

    db.complete_autonomous_task(task_id)
    return _signed_worker_claim_result(
        accepted=True,
        status=SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT,
        task_id=task_id,
        worker_role=run_result.worker_role,
        worker_runtime=run_result.worker_runtime,
        capability=run_result.capability,
        receipt_id=run_result.receipt_id,
    )


def _claim_pending_reddog_readonly_audit_task(*, db: Any, agent_id: str, source: str) -> Optional[Dict[str, Any]]:
    with db.db.get_connection() as conn:
        row = conn.execute(
            """
            SELECT task_id, context FROM agents_autonomous_tasks
            WHERE status = 'pending' AND discovered_by = ?
            ORDER BY priority_score DESC, discovered_at ASC
            LIMIT 1
            """,
            (source,),
        ).fetchone()
        if not row:
            return None
        task_id = row["task_id"] if hasattr(row, "keys") else row[0]
        updated = conn.execute(
            """
            UPDATE agents_autonomous_tasks
            SET assigned_to = ?, assigned_at = CURRENT_TIMESTAMP, status = 'assigned'
            WHERE task_id = ? AND status = 'pending' AND discovered_by = ?
            """,
            (agent_id, task_id, source),
        ).rowcount
        if updated != 1:
            return {"task_id": task_id, "claim_race_lost": True}
        raw_context = row["context"] if hasattr(row, "keys") else row[1]
    try:
        context = json.loads(raw_context) if isinstance(raw_context, str) else raw_context
    except Exception:
        context = None
    return {"task_id": task_id, "context": context}


def _claim_pending_reddog_signed_worker_dispatch_task(
    *,
    db: Any,
    agent_id: str,
    source: str,
) -> Optional[Dict[str, Any]]:
    from modules.communication.moltbot_bridge.src.reddog_signed_worker_openclaw_queue_loop_runtime_binding import (
        is_openclaw_candidate_signed_worker_context,
    )

    with db.db.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT task_id, context FROM agents_autonomous_tasks
            WHERE status = 'pending' AND discovered_by = ?
            ORDER BY priority_score DESC, discovered_at ASC
            LIMIT 50
            """,
            (source,),
        ).fetchall()
        if not rows:
            return None
        row = None
        context: Any = None
        raw_context: Any = None
        for candidate in rows:
            raw_candidate = candidate["context"] if hasattr(candidate, "keys") else candidate[1]
            try:
                candidate_context = json.loads(raw_candidate) if isinstance(raw_candidate, str) else raw_candidate
            except Exception:
                candidate_context = None
            if is_openclaw_candidate_signed_worker_context(candidate_context):
                row = candidate
                raw_context = raw_candidate
                context = candidate_context
                break
        if row is None:
            return None
        task_id = row["task_id"] if hasattr(row, "keys") else row[0]
        updated = conn.execute(
            """
            UPDATE agents_autonomous_tasks
            SET assigned_to = ?, assigned_at = CURRENT_TIMESTAMP, status = 'assigned'
            WHERE task_id = ? AND status = 'pending' AND discovered_by = ?
            """,
            (agent_id, task_id, source),
        ).rowcount
        if updated != 1:
            return {"task_id": task_id, "claim_race_lost": True}
    if context is None:
        try:
            context = json.loads(raw_context) if isinstance(raw_context, str) else raw_context
        except Exception:
            context = None
    return {"task_id": task_id, "context": context}


def _mark_reddog_readonly_audit_task_failed(db: Any, task_id: str) -> None:
    if not task_id:
        return
    try:
        db.db.execute_write(
            "UPDATE agents_autonomous_tasks SET status = 'failed', completed_at = CURRENT_TIMESTAMP WHERE task_id = ?",
            (task_id,),
        )
    except Exception:
        logger.debug("[SUPERVISOR] Failed to mark RedDog readonly audit task failed", exc_info=True)


def _mark_reddog_signed_worker_dispatch_task_failed(db: Any, task_id: str) -> None:
    if not task_id:
        return
    try:
        db.db.execute_write(
            "UPDATE agents_autonomous_tasks SET status = 'failed', completed_at = CURRENT_TIMESTAMP WHERE task_id = ?",
            (task_id,),
        )
    except Exception:
        logger.debug("[SUPERVISOR] Failed to mark RedDog signed-worker task failed", exc_info=True)


def _readonly_assignment_id(context: Dict[str, Any]) -> str:
    assignment = context.get("assignment") if isinstance(context, dict) else {}
    return str(assignment.get("assignment_id") or "") if isinstance(assignment, dict) else ""


def _readonly_claim_result(
    *,
    accepted: bool,
    status: str,
    task_id: str | None = None,
    assignment_id: str | None = None,
    report_digest: str | None = None,
    rejection_reasons=(),
    detail: str = "",
) -> Dict[str, Any]:
    return {
        "accepted": accepted,
        "status": status,
        "task_id": task_id,
        "assignment_id": assignment_id,
        "report_digest": report_digest,
        "rejection_reasons": tuple(dict.fromkeys(str(reason) for reason in rejection_reasons if str(reason))),
        "detail": detail,
        "no_shell_command_executed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_worktree_operation_performed": True,
        "no_pr_created": True,
        "no_live_foundup_enqueue_performed": True,
    }


def _signed_worker_claim_result(
    *,
    accepted: bool,
    status: str,
    task_id: str | None = None,
    worker_role: str | None = None,
    worker_runtime: str | None = None,
    capability: str | None = None,
    receipt_id: str | None = None,
    rejection_reasons=(),
    detail: str = "",
) -> Dict[str, Any]:
    return {
        "accepted": accepted,
        "status": status,
        "task_id": task_id,
        "worker_role": worker_role,
        "worker_runtime": worker_runtime,
        "capability": capability,
        "receipt_id": receipt_id,
        "rejection_reasons": tuple(dict.fromkeys(str(reason) for reason in rejection_reasons if str(reason))),
        "detail": detail,
        "no_shell_command_executed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_worktree_operation_performed": True,
        "no_pr_created": True,
        "no_live_foundup_enqueue_performed": True,
        "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
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

    def claim_reddog_readonly_audit_task_once(
        self,
        *,
        agent_db_factory: Optional[Callable[[], Any]] = None,
        report_store: Any | None = None,
        audit_model_runner: Any | None = None,
        holoindex_adapter: Any | None = None,
        codeindex_adapter: Any | None = None,
        external_research_retriever: Any | None = None,
        timeout_seconds: int = 60,
    ) -> Dict[str, Any]:
        """Claim one RedDog read-only audit task through OpenClaw."""

        return claim_reddog_readonly_audit_task_once(
            repo_root=self.repo_root,
            agent_id="openclaw_supervisor",
            agent_db_factory=agent_db_factory,
            report_store=report_store,
            audit_model_runner=audit_model_runner,
            holoindex_adapter=holoindex_adapter,
            codeindex_adapter=codeindex_adapter,
            external_research_retriever=external_research_retriever,
            timeout_seconds=timeout_seconds,
        )

    def claim_reddog_signed_worker_dispatch_task_once(
        self,
        *,
        agent_db_factory: Optional[Callable[[], Any]] = None,
        signed_worker_runner: Any | None = None,
    ) -> Dict[str, Any]:
        """Claim one signed RedDog worker-dispatch task through OpenClaw."""

        return claim_reddog_signed_worker_dispatch_task_once(
            repo_root=self.repo_root,
            agent_id="openclaw_supervisor",
            agent_db_factory=agent_db_factory,
            signed_worker_runner=signed_worker_runner,
        )

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

    def run_cycle(self, parent_context=None) -> Dict[str, Any]:
        """Run one supervisor cycle.

        Args:
            parent_context: Optional parent continuity context for cross-surface lineage.
                           Pass when supervisor is triggered by another surface's work.
        """
        if not self._bootstrapped:
            self._transition(SupervisorState.BOOT, "startup")
            self._start_self_audit()
            self._transition(SupervisorState.PREFLIGHT, "dependencies_checked")
            self._bootstrapped = True

        # Gateway Continuity Layer: Create continuity context for this cycle
        cycle_id = f"cycle_{self.metrics.cycles_completed}"
        self._continuity_context = self._create_continuity_context(cycle_id, parent_context)

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
            # Emit nudge for high-value escalation reasons
            escalation_reason = triage["reason"]
            high_value_reasons = {
                "resident_openclaw_restart_budget_exhausted",
                "broker_or_observer_unavailable",
                "openclaw_runtime_not_registered",
            }
            if escalation_reason in high_value_reasons:
                self._emit_supervisor_nudge(
                    trigger_type="supervisor_escalation",
                    title=f"Supervisor escalation: {escalation_reason}",
                    summary=(
                        f"Supervisor reached ESCALATE state due to: {escalation_reason}. "
                        f"Restart budget: {triage.get('restart_budget', {})}. "
                        f"Manual intervention may be required."
                    ),
                    priority="P0" if "budget_exhausted" in escalation_reason else "P1",
                    details={
                        "escalation_reason": escalation_reason,
                        "restart_budget": triage.get("restart_budget"),
                        "observation_keys": list(observation.keys()),
                    },
                )
            self.last_cycle = {
                "state": self.current_state.value,
                "triage": triage,
                "observation": observation,
                "verify": verify,
            }
            return self.last_cycle

        # Gateway Continuity Layer: Resolve origin continuity for autonomous tasks
        # If this task was discovered by prior work, link to that origin
        if triage.get("action") == "execute_autonomous_task" and triage.get("task"):
            self._resolve_and_link_origin_continuity(triage["task"])

        self._transition(SupervisorState.PLAN, triage["reason"])
        plan = self._plan(triage, observation)

        self._transition(SupervisorState.EXECUTE, plan["action"])
        action_result = self._execute(plan)

        self._transition(SupervisorState.VERIFY, plan["action"])
        verify = self._verify(plan, action_result)

        if not verify["ok"]:
            self._transition(SupervisorState.ESCALATE, verify.get("error", "verify_failed"))
            self._remember(observation, plan, action_result, verify)
            # Emit nudge for verify failure (high-value event)
            # Include task_id and error in title to distinguish different failures
            task_id = plan.get("task", {}).get("task_id") if plan.get("task") else None
            verify_error = verify.get("error", "unknown")
            title_suffix = f" [{task_id}]" if task_id else ""
            title_suffix += f" ({verify_error})" if verify_error != "unknown" else ""
            self._emit_supervisor_nudge(
                trigger_type="supervisor_verify_failure",
                title=f"Task verify failed: {plan.get('action', 'unknown')}{title_suffix}",
                summary=(
                    f"Execution of {plan.get('action')} completed but verification failed. "
                    f"Error: {verify_error}. Reason: {plan.get('reason', '')}"
                ),
                priority="P1",
                details={
                    "plan_action": plan.get("action"),
                    "plan_reason": plan.get("reason"),
                    "verify_error": verify_error,
                    "task_id": task_id,
                    "fidelity": verify.get("fidelity"),
                },
            )
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

    def _get_pending_self_audit_event(self) -> Optional[Dict[str, Any]]:
        """Read first pending self-audit event from JSONL.

        Returns event where auto_fix_attempted is False and recommended_fix
        is in the allowed fixes list (has a real executor).
        """
        if self._self_audit_loop is None:
            return None

        task_log_path = getattr(self._self_audit_loop, "task_log_path", None)
        if task_log_path is None or not Path(task_log_path).exists():
            return None

        # Get allowed fixes from the loop (these have real executors)
        allowed_fixes = getattr(self._self_audit_loop, "allowed_fixes", set())
        if not allowed_fixes:
            return None

        try:
            # Read last N lines (recent events) to avoid scanning entire file
            lines = Path(task_log_path).read_text(encoding="utf-8").strip().split("\n")
            # Process most recent first (last 50 lines)
            for line in reversed(lines[-50:]):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    # Skip already-attempted fixes
                    if event.get("auto_fix_attempted", False):
                        continue
                    # Only return events with executable fixes
                    fix = event.get("recommended_fix", "")
                    if fix.lower() in allowed_fixes:
                        return event
                except json.JSONDecodeError:
                    continue
        except Exception as exc:
            logger.debug("[SUPERVISOR] Failed to read self-audit JSONL: %s", exc)

        return None

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
            "self_audit_event_count": 0,
        }

        # Poll DaemonSelfAuditLoop for real events (ported from Supervisor24x7)
        # NOTE: scan_once() returns int (count of events), not an iterable
        if self._self_audit_loop and hasattr(self._self_audit_loop, "scan_once"):
            try:
                event_count = self._self_audit_loop.scan_once()
                if event_count and event_count > 0:
                    obs["self_audit_event_count"] = event_count
                    self.metrics.events_observed += event_count
                    logger.info(
                        "[SUPERVISOR] OBSERVE: %d self-audit events detected",
                        event_count,
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
        # CIRCUIT BREAKER: Only auto-execute if explicitly enabled by 012
        # Set OPENCLAW_AUTO_TASKS_ENABLED=1 after menu choice to activate
        auto_tasks_enabled = os.getenv("OPENCLAW_AUTO_TASKS_ENABLED", "0") == "1"
        if auto_tasks_enabled:
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

        # Bounded maintenance task selection (WSP 77/87/97)
        # Uses maintenance selector to find safe, low-risk tasks with HoloIndex direction
        maintenance_enabled = os.getenv("OPENCLAW_MAINTENANCE_ENABLED", "0") == "1"
        if maintenance_enabled:
            try:
                from modules.infrastructure.database.src.agent_db import AgentDB
                from .openclaw_maintenance_selector import select_maintenance_task

                db = AgentDB()
                pending_tasks = db.get_autonomous_tasks(status="pending", limit=10)
                selection = select_maintenance_task(
                    pending_tasks=pending_tasks,
                    observation=observation,
                    repo_root=self.repo_root,
                )

                if selection.selected_task:
                    task = selection.selected_task
                    if task.is_safe():
                        # Safe bounded task - execute it
                        return {
                            "kind": "action",
                            "reason": "bounded_maintenance_task",
                            "action": "execute_maintenance_task",
                            "task": {
                                "task_id": task.task_id,
                                "family": task.family,
                                "description": task.description,
                                "source": task.source,
                                "required_skills": [],
                                "context": {"source": task.source},
                            },
                            "maintenance_selection": selection.to_dict(),
                        }
                    else:
                        # Task requires escalation
                        return {
                            "kind": "escalate",
                            "reason": f"maintenance_escalation:{task.escalation_reason}",
                            "task": task.to_dict(),
                            "maintenance_selection": selection.to_dict(),
                        }
            except Exception as exc:
                logger.warning("Failed to select maintenance task: %s", exc)

        # Check self-audit events from JSONL (lower priority than restart and AgentDB tasks)
        # DaemonSelfAuditLoop persists events to JSONL with recommended_fix field
        self_audit_enabled = os.getenv("OPENCLAW_SELF_AUDIT_ENABLED", "1") != "0"
        if self_audit_enabled and self._self_audit_loop:
            pending_event = self._get_pending_self_audit_event()
            if pending_event:
                return {
                    "kind": "action",
                    "reason": "self_audit_event_pending",
                    "action": "execute_self_audit_fix",
                    "event_signature": pending_event.get("signature", ""),
                    "recommended_fix": pending_event.get("recommended_fix", ""),
                    "source_file": pending_event.get("source_file", ""),
                }

        # Skill Evolution Loop — Phase 1: report surface (idle path only, lowest priority)
        # Build/write report as idle-path observability; do not create a new action branch
        skill_evolution_report: Dict[str, Any] | None = None
        skill_evolution_enabled = os.getenv("OPENCLAW_SKILL_EVOLUTION_ENABLED", "0") == "1"
        if skill_evolution_enabled and self._pattern_memory:
            try:
                from .openclaw_skill_evolution import (
                    build_skill_evolution_report,
                    skill_evolution_report_due,
                    write_skill_evolution_report,
                )

                if skill_evolution_report_due(self.repo_root):
                    report = build_skill_evolution_report(self._pattern_memory)
                    report_path = write_skill_evolution_report(self.repo_root, report)
                    skill_evolution_report = {
                        "report_path": str(report_path),
                        "skills_evaluated": report.get("skills_evaluated", 0),
                        "candidate_count": report.get("candidate_count", 0),
                        "generated_on": report.get("generated_on"),
                    }
                    logger.info(
                        "[SUPERVISOR] Skill evolution report generated: %d skills, %d candidates",
                        skill_evolution_report["skills_evaluated"],
                        skill_evolution_report["candidate_count"],
                    )
            except Exception as exc:
                logger.debug("[SUPERVISOR] Skill evolution report skipped: %s", exc)

        # Skill Evolution Loop — Phase 2: mutation surface (idle path only, gated)
        # Surfaces mutation eligibility/readiness but does NOT mutate
        mutation_surface_report: Dict[str, Any] | None = None
        mutation_surface_enabled = os.getenv("OPENCLAW_MUTATION_SURFACE_ENABLED", "0") == "1"
        if mutation_surface_enabled and self._pattern_memory:
            try:
                from .openclaw_skill_evolution import (
                    build_mutation_surface_report,
                    mutation_surface_report_due,
                    write_mutation_surface_report,
                )

                if mutation_surface_report_due(self.repo_root):
                    report = build_mutation_surface_report(self._pattern_memory)
                    report_path = write_mutation_surface_report(self.repo_root, report)
                    mutation_surface_report = {
                        "report_path": str(report_path),
                        "enabled": report.get("enabled", False),
                        "skills_evaluated": report.get("skills_evaluated", 0),
                        "summary": report.get("summary", {}),
                        "gates": report.get("gates", {}),
                        "generated_on": report.get("generated_on"),
                    }
                    logger.info(
                        "[SUPERVISOR] Mutation surface report generated: %d skills, summary=%s",
                        mutation_surface_report["skills_evaluated"],
                        mutation_surface_report["summary"],
                    )
            except Exception as exc:
                logger.debug("[SUPERVISOR] Mutation surface report skipped: %s", exc)

        idle_result: Dict[str, Any] = {"kind": "idle", "reason": "resident_openclaw_healthy"}
        if skill_evolution_report:
            idle_result["skill_evolution_report"] = skill_evolution_report
        if mutation_surface_report:
            idle_result["mutation_surface_report"] = mutation_surface_report
        return idle_result

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

        # Carry maintenance selection metadata into plan (WSP 77/87/97)
        if triage["action"] == "execute_maintenance_task":
            plan["maintenance_selection"] = triage.get("maintenance_selection", {})

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

        # Runtime emitter: structured event for supervisor execution observability
        _rt_start = None
        try:
            from modules.infrastructure.dae_daemon.src.runtime_emitter import (
                emit_start as _re_start, emit_success as _re_ok, emit_failure as _re_fail,
            )
            _rt_start = _re_start(
                "openclaw_supervisor", "supervisor_execute",
                details={"action": plan.get("action", "unknown")},
            )
        except Exception:
            _re_ok = _re_fail = None

        if plan["action"] == "start_openclaw":
            self._record_restart_attempt()
            result = broker.start_dae("openclaw", actor_id="0102")
            self._action_reporter(
                "supervisor_execute",
                result.get("status", result.get("error", "unknown")),
                {"plan": plan, "result": result},
            )
            if _rt_start is not None:
                try:
                    if result.get("ok") or result.get("status") == "started":
                        _re_ok("openclaw_supervisor", "supervisor_execute", _rt_start,
                               details={"action": "start_openclaw"})
                    else:
                        _re_fail("openclaw_supervisor", "supervisor_execute", _rt_start,
                                 result.get("error", "unknown")[:200],
                                 details={"action": "start_openclaw"})
                except Exception:
                    pass
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
            if _rt_start is not None:
                try:
                    if result.get("ok"):
                        _re_ok("openclaw_supervisor", "supervisor_execute", _rt_start,
                               task_id=task_id,
                               details={"action": "execute_autonomous_task",
                                         "executor": result.get("executor", "unknown")})
                    else:
                        _re_fail("openclaw_supervisor", "supervisor_execute", _rt_start,
                                 result.get("error", result.get("status", "unknown"))[:200],
                                 task_id=task_id,
                                 details={"action": "execute_autonomous_task"})
                except Exception:
                    pass
            return result

        elif plan["action"] == "execute_maintenance_task":
            # Bounded maintenance task execution (WSP 77/87/97)
            task = plan.get("task", {})
            task_id = task.get("task_id")
            family = task.get("family", "unknown")
            result: Dict[str, Any] = {"ok": False, "error": "unknown"}
            try:
                from modules.infrastructure.database.src.agent_db import AgentDB
                from .openclaw_maintenance_selector import write_maintenance_report

                db = AgentDB()
                if task_id:
                    db.assign_autonomous_task(task_id, "openclaw_supervisor")

                    # Dispatch via run_task.execute_task() (same as autonomous tasks)
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
                        "family": family,
                    }
                else:
                    result = {"ok": False, "error": "no_task_id", "family": family}
            except Exception as exc:
                result = {"ok": False, "status": "execute_error", "error": str(exc)[:500], "family": family}

            self._action_reporter(
                "supervisor_execute",
                result.get("status", result.get("error", "unknown")),
                {"plan": plan, "result": result, "maintenance": True},
            )
            if _rt_start is not None:
                try:
                    if result.get("ok"):
                        _re_ok("openclaw_supervisor", "supervisor_execute", _rt_start,
                               task_id=task_id,
                               details={"action": "execute_maintenance_task",
                                        "family": family,
                                        "executor": result.get("executor", "unknown")})
                    else:
                        _re_fail("openclaw_supervisor", "supervisor_execute", _rt_start,
                                 result.get("error", result.get("status", "unknown"))[:200],
                                 task_id=task_id,
                                 details={"action": "execute_maintenance_task", "family": family})
                except Exception:
                    pass
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
            if _rt_start is not None:
                try:
                    if result.get("ok"):
                        _re_ok("openclaw_supervisor", "supervisor_execute", _rt_start,
                               details={"action": "execute_self_audit_fix"})
                    else:
                        _re_fail("openclaw_supervisor", "supervisor_execute", _rt_start,
                                 result.get("error", "unknown")[:200],
                                 details={"action": "execute_self_audit_fix"})
                except Exception:
                    pass
            return result

        # Fallback for unsupported actions
        if _rt_start is not None:
            try:
                _re_fail("openclaw_supervisor", "supervisor_execute", _rt_start,
                         "unsupported_action",
                         details={"action": plan.get("action", "unknown")})
            except Exception:
                pass
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

        if plan["action"] == "execute_maintenance_task":
            # Bounded maintenance task verification (WSP 77/87/97)
            task = plan.get("task", {})
            task_id = task.get("task_id")
            family = task.get("family", "unknown")
            task_status = None

            try:
                from modules.infrastructure.database.src.agent_db import AgentDB

                db = AgentDB()
                completed_tasks = db.get_autonomous_tasks(status="completed", limit=100)
                if task_id and any(item.get("task_id") == task_id for item in completed_tasks):
                    task_status = "completed"
            except Exception as exc:
                logger.debug("[SUPERVISOR] VERIFY: maintenance task status check skipped: %s", exc)

            ok = bool(action_result.get("ok", False) and task_status == "completed")
            fidelity = 0.85  # Default for maintenance tasks

            # Gemma fidelity validation for maintenance tasks
            if ok and self._libido_monitor and hasattr(self._libido_monitor, "validate_step_fidelity"):
                try:
                    validation = self._libido_monitor.validate_step_fidelity(
                        step_description=f"Maintenance [{family}]: {task_id}",
                        step_output=str(action_result)[:500],
                    )
                    if isinstance(validation, dict):
                        fidelity = validation.get("fidelity", 0.85)
                    elif isinstance(validation, (int, float)):
                        fidelity = float(validation)
                    logger.debug("[SUPERVISOR] VERIFY: Maintenance fidelity = %.3f", fidelity)
                except Exception as e:
                    logger.debug("[SUPERVISOR] VERIFY: Maintenance Gemma validation skipped: %s", e)

            error = action_result.get("error", "")
            if not ok and not error and task_status != "completed":
                error = "maintenance_task_not_completed"

            # Write maintenance report artifact
            try:
                from .openclaw_maintenance_selector import (
                    MaintenanceSelectionResult,
                    MaintenanceTask,
                    write_maintenance_report,
                )

                selection = plan.get("maintenance_selection", {})
                selection_result = MaintenanceSelectionResult(
                    selected_task=MaintenanceTask(
                        task_id=task_id or "",
                        family=family,
                        description=task.get("description", "")[:200],
                        source=task.get("source", ""),
                        risk_level="low",
                    ) if task_id else None,
                    candidates_evaluated=selection.get("candidates_evaluated", 0),
                    selection_reason=selection.get("selection_reason", "maintenance"),
                    bundle_used=selection.get("bundle_used", False),
                )
                verify_result = {"ok": ok, "fidelity": fidelity, "error": error}
                report_path = write_maintenance_report(
                    selection_result, action_result, verify_result, self.repo_root
                )
                logger.info("[SUPERVISOR] VERIFY: Maintenance report: %s", report_path.name)
            except Exception as exc:
                logger.debug("[SUPERVISOR] VERIFY: Maintenance report write failed: %s", exc)

            return {
                "ok": ok,
                "status": action_result,
                "task_status": task_status,
                "error": error,
                "fidelity": fidelity,
                "family": family,
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

        # Gateway Continuity Layer: Record breadcrumb with continuity metadata
        self._record_continuity_breadcrumb(plan_or_triage, action_result, verify)

    def _create_continuity_context(self, cycle_id: str, parent_context=None) -> Any:
        """Create continuity context for a supervisor cycle.

        Args:
            cycle_id: Identifier for this supervisor cycle.
            parent_context: Optional parent continuity context for cross-surface lineage.
                           If provided, the supervisor context will be forked as a child.
        """
        try:
            from modules.communication.moltbot_bridge.src.continuity_context import (
                ContinuityManager,
            )
            return ContinuityManager.from_supervisor(
                cycle_id=cycle_id,
                state=self.current_state.value,
                parent_context=parent_context,
            )
        except Exception as exc:
            logger.debug("[SUPERVISOR] Continuity context creation failed: %s", exc)
            return None

    def _resolve_and_link_origin_continuity(self, task: Dict[str, Any]) -> None:
        """Resolve origin continuity from task and link to current cycle context.

        When supervisor executes a task that was discovered by prior work,
        this establishes lineage back to the originating continuity.
        """
        try:
            from modules.communication.moltbot_bridge.src.continuity_context import (
                ContinuityManager,
            )
            origin_ctx = ContinuityManager.resolve_origin_continuity_from_task(task)
            if origin_ctx and self._continuity_context:
                # Link current cycle to the original work
                self._continuity_context.parent_continuity_id = origin_ctx.continuity_id
                self._continuity_context.surface_metadata["origin_task_id"] = task.get("task_id")
                self._continuity_context.surface_metadata["origin_resolution"] = "autonomous_task"
                logger.info(
                    "[SUPERVISOR] Linked to origin continuity: %s (task=%s)",
                    origin_ctx.continuity_id,
                    task.get("task_id"),
                )
        except Exception as exc:
            logger.debug("[SUPERVISOR] Origin continuity resolution failed: %s", exc)

    def _record_continuity_breadcrumb(
        self,
        plan_or_triage: Dict[str, Any],
        action_result: Dict[str, Any],
        verify: Dict[str, Any],
    ) -> None:
        """Record a breadcrumb with continuity metadata for cross-surface tracking."""
        continuity_ctx = getattr(self, "_continuity_context", None)
        if continuity_ctx is None:
            return

        try:
            from modules.infrastructure.database.src.agent_db import AgentDB

            action = plan_or_triage.get("action", plan_or_triage.get("kind", "unknown"))
            db = AgentDB()
            db.add_breadcrumb(
                session_id=continuity_ctx.session_id,
                action=f"supervisor_{action}",
                agent_id="openclaw_supervisor",
                data={
                    "state": self.current_state.value,
                    "reason": plan_or_triage.get("reason", ""),
                    "success": bool(verify.get("ok", False)),
                    "action_ok": bool(action_result.get("ok", False)),
                },
                continuity_id=continuity_ctx.continuity_id,
                runtime_surface=continuity_ctx.surface.value,
                sender_normalized="supervisor",
                parent_continuity_id=continuity_ctx.parent_continuity_id,
            )
            logger.debug(
                "[SUPERVISOR] Breadcrumb recorded | continuity_id=%s surface=%s",
                continuity_ctx.continuity_id,
                continuity_ctx.surface.value,
            )
        except Exception as exc:
            logger.debug("[SUPERVISOR] Failed to record continuity breadcrumb: %s", exc)

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

    # ------------------------------------------------------------------ #
    #  Memory Nudge Emission                                              #
    # ------------------------------------------------------------------ #

    def _emit_supervisor_nudge(
        self,
        trigger_type: str,
        title: str,
        summary: str,
        priority: str,
        details: Dict[str, Any],
    ) -> bool:
        """
        Emit a memory nudge for high-value supervisor events.

        Emits nudges for:
        - supervisor_verify_failure: Task execution verification failed
        - supervisor_escalation: Budget exhausted, broker unavailable, etc.

        Returns True if nudge was emitted (not deduplicated).
        """
        try:
            from modules.communication.moltbot_bridge.src.memory_nudge_engine import (
                MemoryNudgeEngine,
                NudgeEvent,
            )

            event = NudgeEvent(
                trigger_type=trigger_type,
                title=title,
                summary=summary,
                provenance="openclaw_supervisor",
                priority=priority,
                details=details,
            )

            engine = MemoryNudgeEngine(repo_root=self.repo_root)
            created = engine.emit_nudges([event], record_breadcrumbs=True)

            if created:
                logger.info(
                    "[SUPERVISOR] Emitted memory nudge: %s (%s)",
                    title[:50],
                    trigger_type,
                )
                return True
            else:
                logger.debug(
                    "[SUPERVISOR] Nudge deduplicated: %s",
                    event.signature,
                )
                return False

        except ImportError:
            logger.debug("[SUPERVISOR] MemoryNudgeEngine not available")
            return False
        except Exception as exc:
            logger.debug("[SUPERVISOR] Failed to emit nudge: %s", exc)
            return False
