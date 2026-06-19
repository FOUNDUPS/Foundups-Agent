#!/usr/bin/env python3
"""
reschedule_plan - SKILLz Executor

Computes a dry-run REBALANCE PLAN for over-crowded schedule days. The historical
backlog was scheduled at up to 8/day before the per-day cap landed (#844,
HARD_CAP_PER_DAY=3). This SKILLz proposes moving the excess (count > cap) off each
over-crowded day onto the nearest under-target upcoming days, placing each moved
item into a US-ET peak slot converted to the channel Studio-account timezone
(peak_window.py, #847).

DRY-RUN / READ-ONLY (Mode B Phase 1)
------------------------------------
This is the PREVIEW/decision layer. DRY_RUN is ALWAYS True in this slice: the skill
RETURNS the plan and emits learning signals, but NEVER mutates a schedule, never
opens a browser, never calls a live model. The mutating DOM apply (click
"Scheduled" -> ytcp-video-visibility-edit-popup date/time picker) is an explicit
Phase-2 follow-up wired through this same plan -- NOT built here.

For the agent, never for a human
--------------------------------
The WRE/daemon triggers this SKILLz and the `--agent-command` surface invokes it
(`youtube action reschedule_plan`). 012 only OBSERVES the emitted breadcrumb +
PatternMemory outcome and the JSON plan. There is NO manual-012 apply path.

WSP Compliance:
    WSP 95: SKILLz Wardrobe (micro chain-of-thought + pattern fidelity)
    WSP 77: Agent Coordination (Qwen/daemon consumes the plan)
    WSP 91: DAEmon Observability (breadcrumb on every run)
    WSP 60/48: Pattern Memory outcome on every run (WRE self-improvement)
    WSP 27: Phase 0 KNOWLEDGE (plan-before-act)

Malleable seams (intentional):
    - DATA SOURCE is injected via `load_schedule` (default: ScheduleTracker JSON).
      A future LIVE Studio scrape plugs in here WITHOUT touching the plan math.
    - PLAN MATH lives in src/reschedule_planner.py behind pure functions
      (find_over_cap_days / find_target_days / assign_peak_slot). Slot policy and
      target selection are independently swappable.
    - Phase-2 apply seam: each plan row is a complete move instruction; the Phase-2
      DOM applier consumes rows. View-based ("low-viewed first") prioritization
      needs per-video view data (NOT in the tracker) -- separate Phase-2 signal.

Usage (agent / daemon):
    from .executor import run_skill
    plan = run_skill()  # dry-run; emits breadcrumb + PatternMemory

Usage (--agent-command surface, via youtube_automation_adapter):
    youtube action reschedule_plan
    (the adapter spawns: python -m ...skillz.reschedule_plan.run_skill --json)
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Authoritative per-day cap, imported from the tracker (#844).
try:
    from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import (
        HARD_CAP_PER_DAY,
    )
except Exception:  # pragma: no cover - defensive import for isolated tests
    HARD_CAP_PER_DAY = 3

from modules.platform_integration.youtube_shorts_scheduler.src.reschedule_planner import (
    plan_all_channels,
)

# This slice is ALWAYS a dry-run preview. The mutating apply is a Phase-2 slice
# that flips its own gate; this constant documents the seam and pins the behavior.
DRY_RUN = True

# Source DAE label for breadcrumb attribution (WSP 91).
SOURCE_DAE = "youtube_shorts_scheduler"
SKILL_NAME = "reschedule_plan"


# === Signal emission (WSP 91 breadcrumb + WSP 60/48 PatternMemory) ==========

def _emit_breadcrumb(result: Dict[str, Any]) -> bool:
    """Emit a reschedule_plan breadcrumb so the WRE/overseer can learn (WSP 91)."""
    try:
        from modules.communication.livechat.src.breadcrumb_telemetry import (
            get_breadcrumb_telemetry,
        )

        summary = result.get("summary", {})
        get_breadcrumb_telemetry().store_breadcrumb(
            source_dae=SOURCE_DAE,
            event_type="reschedule_plan",
            message=(
                f"reschedule-plan (dry-run): {summary.get('days_over_cap', 0)} days "
                f"over cap, {summary.get('total_moves', 0)} moves across "
                f"{summary.get('channels_needing_rebalance', 0)} channel(s)"
            ),
            phase="RESCHEDULE_PLAN",
            metadata={
                "skill": SKILL_NAME,
                "dry_run": result.get("dry_run", True),
                "cap": result.get("cap", HARD_CAP_PER_DAY),
                "summary": summary,
                "plan": result.get("channels", []),
            },
        )
        return True
    except Exception as exc:  # pragma: no cover - telemetry is best-effort
        logger.warning(f"[{SKILL_NAME}] breadcrumb emit failed: {exc}")
        return False


def _store_outcome(result: Dict[str, Any]) -> bool:
    """Store a SkillOutcome so the WRE remembers each run (WSP 60/48)."""
    try:
        from modules.infrastructure.wre_core.src.pattern_memory import (
            PatternMemory,
            SkillOutcome,
        )

        summary = result.get("summary", {})
        total_moves = summary.get("total_moves", 0)
        outcome = SkillOutcome(
            execution_id=f"{SKILL_NAME}-{uuid.uuid4().hex[:12]}",
            skill_name=SKILL_NAME,
            agent="qwen",
            timestamp=datetime.now().isoformat(),
            input_context=json.dumps(
                {
                    "dry_run": result.get("dry_run", True),
                    "cap": result.get("cap", HARD_CAP_PER_DAY),
                    "channels": result.get("channel_count", 0),
                },
                separators=(",", ":"),
            ),
            output_result=json.dumps({"summary": summary}, separators=(",", ":"))[:10000],
            success=True,
            pattern_fidelity=1.0,
            outcome_quality=1.0 if total_moves > 0 else 0.8,
            execution_time_ms=0,
            step_count=total_moves,
            failed_at_step=None,
            notes=f"source={SKILL_NAME} dry_run=true read_only=true cap={result.get('cap')}",
        )
        PatternMemory().store_outcome(outcome)
        return True
    except Exception as exc:  # pragma: no cover - memory is best-effort
        logger.warning(f"[{SKILL_NAME}] pattern memory store failed: {exc}")
        return False


def run_skill(
    *,
    cap: int = HARD_CAP_PER_DAY,
    channels: Optional[List[Dict[str, str]]] = None,
    load_schedule: Optional[Callable[[str], tuple]] = None,
    today: Optional[datetime] = None,
    horizon_days: Optional[int] = None,
    emit_signals: bool = True,
) -> Dict[str, Any]:
    """SKILLz entry point: compute the dry-run rebalance plan + emit WRE signals.

    Returns a structured result (for the daemon/Qwen to consume) including the
    per-channel plans, the summary, and which signals were emitted. NEVER mutates.
    """
    plan_kwargs: Dict[str, Any] = {"cap": cap, "channels": channels, "today": today}
    if load_schedule is not None:
        plan_kwargs["load_schedule"] = load_schedule
    if horizon_days is not None:
        plan_kwargs["horizon_days"] = horizon_days

    result = plan_all_channels(**plan_kwargs)
    # Pin the dry-run contract for this slice regardless of any downstream override.
    result["dry_run"] = DRY_RUN
    result["skill"] = SKILL_NAME

    breadcrumb_emitted = False
    outcome_stored = False
    if emit_signals:
        breadcrumb_emitted = _emit_breadcrumb(result)
        outcome_stored = _store_outcome(result)

    result["success"] = True
    result["breadcrumb_emitted"] = breadcrumb_emitted
    result["outcome_stored"] = outcome_stored
    return result
