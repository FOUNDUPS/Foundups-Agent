#!/usr/bin/env python3
"""
reschedule_apply - SKILLz Executor

Flag-gated MUTATING apply of the #851 reschedule PLAN. Moves a scheduled short
from an over-crowded day to a target day + peak slot via the Studio
visibility-edit popup date/time picker (reused from dom_automation.py).

DEFAULT = DRY-RUN (Mode B Phase 2)
----------------------------------
This skill mutates NOTHING by default. Each move is only LOGGED as a "would move"
plus a per-move breadcrumb + PatternMemory outcome (status ``dry_run``). Real DOM
apply happens ONLY when the env ``YT_RESCHEDULE_APPLY == "1"`` (default ``"0"``)
AND a live DOM driver is connected. Merging this code changes no schedule; 012
enables the flag after observing dry-runs and live-validates.

For the agent, never for a human
--------------------------------
The WRE/daemon triggers this SKILLz and the ``--agent-command`` surface invokes it
(``youtube action reschedule_apply``). 012 only observes the emitted breadcrumb +
PatternMemory outcomes and the JSON result. There is NO manual-012 apply path.

Safety (delegated to reschedule_applier.apply_moves):
    - dry-run hard unless YT_RESCHEDULE_APPLY == "1".
    - ``(needs-live-list)`` moves are SKIPPED.
    - per-channel target-day cap is re-checked; over-cap moves SKIPPED.
    - per-move try/except: one failure never aborts the batch.

WSP Compliance:
    WSP 95: SKILLz Wardrobe   WSP 77: Agent Coordination
    WSP 91: Observability     WSP 60/48: Pattern Memory
    WSP 50: flag-gated mutation, default read-only

Usage (agent / daemon, default dry-run):
    from .executor import run_skill
    result = run_skill()   # dry-run; logs would-apply moves, emits signals

Usage (--agent-command surface):
    youtube action reschedule_apply
    (adapter spawns: python -m ...skillz.reschedule_apply.run_skill --json)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

from modules.platform_integration.youtube_shorts_scheduler.src.reschedule_applier import (
    APPLY_ENV,
    SKILL_NAME,
    apply_enabled,
    apply_plan,
)

try:
    from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import (
        HARD_CAP_PER_DAY,
    )
except Exception:  # pragma: no cover - defensive import
    HARD_CAP_PER_DAY = 3


def run_skill(
    *,
    dom: Any = None,
    plan: Optional[Dict[str, Any]] = None,
    plan_factory: Optional[Callable[[], Dict[str, Any]]] = None,
    cap: int = HARD_CAP_PER_DAY,
    dry_run: Optional[bool] = None,
    emit_signals: bool = True,
) -> Dict[str, Any]:
    """SKILLz entry: compute the #851 plan and apply/dry-run its moves.

    Args:
        dom: optional live DOM driver (YouTubeStudioDOM). Only used on real apply.
            When None and apply is requested, apply_moves records ``error`` for each
            move (no browser is auto-launched here; the daemon supplies a driver).
        plan / plan_factory: pre-computed plan or factory (default: plan_all_channels).
        cap: per-day hard cap for the target-day guard.
        dry_run: force dry-run/apply; None => resolve from YT_RESCHEDULE_APPLY.
        emit_signals: emit breadcrumb + PatternMemory per move.

    Returns:
        apply summary (dry_run, counts, results, plan_summary, skill, success).
    """
    result = apply_plan(
        dom=dom,
        plan=plan,
        plan_factory=plan_factory,
        cap=cap,
        dry_run=dry_run,
        emit_signals=emit_signals,
    )
    # Pin observability fields for the agent/daemon consumer.
    result["skill"] = SKILL_NAME
    result["apply_env"] = APPLY_ENV
    result["apply_enabled"] = apply_enabled()
    return result
