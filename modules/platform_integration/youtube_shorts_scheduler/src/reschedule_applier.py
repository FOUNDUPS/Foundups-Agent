"""
Reschedule Applier - MUTATING apply for the #851 reschedule PLAN.

Slice: SHORTS_RESCHEDULE_APPLY_PHASE2  (Mode B, Phase 2 - the apply layer)

What this does
--------------
Consumes the dry-run rebalance PLAN produced by reschedule_planner.py / the
reschedule_plan SKILLz (#851) and, for each move with a real video_id, moves a
scheduled short from its over-crowded ``from_date`` onto the target ``to_date`` at
the peak ``slot_local`` via the Studio visibility-edit popup date/time picker.

DEFAULT = DRY-RUN (zero DOM mutation)
-------------------------------------
This module mutates NOTHING by default. Each move is, by default, only LOGGED as a
"would move" plus a breadcrumb + PatternMemory outcome with status ``dry_run``.
Real DOM apply happens ONLY when the environment variable
``YT_RESCHEDULE_APPLY == "1"`` (default ``"0"``). Merging this code therefore
changes no schedule; 012 enables the flag after observing dry-runs and
live-validates.

For the agent, never for a human
--------------------------------
The WRE/daemon triggers this and the ``--agent-command`` surface invokes it
(``youtube action reschedule_apply``). There is NO manual-012 apply path; 012 only
observes outcomes and flips the env flag.

Safety
------
- ``YT_RESCHEDULE_APPLY != "1"`` -> dry-run hard (picker/save helpers NEVER called).
- A move whose ``video_id`` is the sentinel ``(needs-live-list)`` is SKIPPED
  (specific-video selection for those needs the live Studio list, out of scope).
- CAP SAFETY: before applying a move we re-count, within THIS batch, how many items
  already target ``to_date`` for the channel. If applying would exceed the cap on
  the target day, the move is SKIPPED (status ``skipped``, reason ``cap``). This is
  a second guard on top of the planner's own cap math.
- Per-move try/except: one failed move never aborts the batch.

Reuse (WSP 84)
--------------
- Plan rows: reschedule_planner.MovePlan / NEEDS_LIVE_LIST + plan_all_channels.
- DOM picker: dom_automation.YouTubeStudioDOM.reschedule_open_set_save (which
  reuses set_schedule_date / set_schedule_time / click_done / click_save and the
  shadow_dom_finder-backed open_scheduled_edit_popup).
- Cap: HARD_CAP_PER_DAY (schedule_tracker, #844).

WSP References:
- WSP 3:  platform_integration owns publish-time/rebalance policy.
- WSP 50: flag-gated mutation; default read-only; pure-where-possible + injectable DOM.
- WSP 84: reuse the planner, the date/time picker, the shadow finder, the cap.
- WSP 91: breadcrumb per move. WSP 60/48: PatternMemory outcome per move.
- WSP 22: ModLog documents the apply gate + the needs-live-list skip seam.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Authoritative per-day cap (#844) + the needs-live-list sentinel (#851).
try:
    from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import (
        HARD_CAP_PER_DAY,
    )
except Exception:  # pragma: no cover - defensive import for isolated tests
    HARD_CAP_PER_DAY = 3

try:
    from modules.platform_integration.youtube_shorts_scheduler.src.reschedule_planner import (
        NEEDS_LIVE_LIST,
    )
except Exception:  # pragma: no cover - defensive import for isolated tests
    NEEDS_LIVE_LIST = "(needs-live-list)"

# Env gate name (single load-bearing knob). Default "0" => DRY-RUN.
APPLY_ENV = "YT_RESCHEDULE_APPLY"

SOURCE_DAE = "youtube_shorts_scheduler"
SKILL_NAME = "reschedule_apply"

# Per-move outcome statuses.
STATUS_APPLIED = "applied"
STATUS_DRY_RUN = "dry_run"
STATUS_SKIPPED = "skipped"
STATUS_ERROR = "error"


def apply_enabled() -> bool:
    """True ONLY when YT_RESCHEDULE_APPLY == "1" (default off -> dry-run)."""
    return os.getenv(APPLY_ENV, "0").strip() == "1"


# === Signal emission (WSP 91 breadcrumb + WSP 60/48 PatternMemory) ===========

def _emit_move_breadcrumb(move_result: Dict[str, Any], dry_run: bool) -> None:
    """Emit a per-move breadcrumb so the WRE/overseer can learn (WSP 91)."""
    try:
        from modules.communication.livechat.src.breadcrumb_telemetry import (
            get_breadcrumb_telemetry,
        )

        status = move_result.get("status")
        get_breadcrumb_telemetry().store_breadcrumb(
            source_dae=SOURCE_DAE,
            event_type="reschedule_apply",
            message=(
                f"reschedule-apply ({'dry-run' if dry_run else 'apply'}): "
                f"{status} {move_result.get('video_id')} "
                f"{move_result.get('from_date')} -> {move_result.get('to_date')} "
                f"@ {move_result.get('slot_local')}"
            ),
            phase="RESCHEDULE_APPLY",
            metadata={
                "skill": SKILL_NAME,
                "dry_run": dry_run,
                "move": move_result,
            },
        )
    except Exception as exc:  # pragma: no cover - telemetry best-effort
        logger.debug(f"[{SKILL_NAME}] breadcrumb emit failed: {exc}")


def _store_move_outcome(move_result: Dict[str, Any], dry_run: bool) -> None:
    """Store a per-move SkillOutcome so the WRE remembers each move (WSP 60/48)."""
    try:
        from modules.infrastructure.wre_core.src.pattern_memory import (
            PatternMemory,
            SkillOutcome,
        )

        status = move_result.get("status")
        success = status in (STATUS_APPLIED, STATUS_DRY_RUN)
        outcome = SkillOutcome(
            execution_id=f"{SKILL_NAME}-{uuid.uuid4().hex[:12]}",
            skill_name=SKILL_NAME,
            agent="qwen",
            timestamp=datetime.now().isoformat(),
            input_context=str(
                {
                    "dry_run": dry_run,
                    "channel_id": move_result.get("channel_id"),
                    "video_id": move_result.get("video_id"),
                    "to_date": move_result.get("to_date"),
                }
            ),
            output_result=str({"status": status, "reason": move_result.get("reason")})[:10000],
            success=success,
            pattern_fidelity=1.0,
            outcome_quality=1.0 if success else 0.0,
            execution_time_ms=0,
            step_count=1,
            failed_at_step=None if success else status,
            notes=f"source={SKILL_NAME} dry_run={str(dry_run).lower()} status={status}",
        )
        PatternMemory().store_outcome(outcome)
    except Exception as exc:  # pragma: no cover - memory best-effort
        logger.debug(f"[{SKILL_NAME}] pattern memory store failed: {exc}")


# === Core per-move apply =====================================================

def _move_record(move: Dict[str, Any], status: str, reason: str = "") -> Dict[str, Any]:
    """Build a normalized per-move result record."""
    return {
        "channel_id": move.get("channel_id"),
        "channel_name": move.get("channel_name"),
        "from_date": move.get("from_date"),
        "to_date": move.get("to_date"),
        "slot_et": move.get("slot_et"),
        "slot_local": move.get("slot_local"),
        "video_id": move.get("video_id"),
        "status": status,
        "reason": reason,
    }


def apply_moves(
    moves: List[Dict[str, Any]],
    *,
    dom: Any = None,
    cap: int = HARD_CAP_PER_DAY,
    dry_run: Optional[bool] = None,
    emit_signals: bool = True,
) -> Dict[str, Any]:
    """Apply (or dry-run) a list of plan move rows.

    Args:
        moves: list of plan move dicts (channel_id, channel_name, from_date,
            to_date, slot_et, slot_local, video_id) -- the #851 plan rows.
        dom: the DOM driver exposing ``reschedule_open_set_save(date, time, video_id)``
            (a ``YouTubeStudioDOM``). REQUIRED only when actually applying; in
            dry-run it is never touched. Injectable for tests.
        cap: per-day hard cap (default HARD_CAP_PER_DAY=3) for the target-day guard.
        dry_run: force dry-run (True) / force apply (False). When None (default),
            resolved from the ``YT_RESCHEDULE_APPLY`` env gate (default => dry-run).
        emit_signals: emit breadcrumb + PatternMemory per move.

    Returns:
        {
          dry_run, cap, total, applied, dry_run_count, skipped, errors,
          results: [per-move record...]
        }

    Behavior:
        - dry-run (default): the DOM picker/save helpers are NEVER called. Each
          eligible move is recorded as ``dry_run`` ("would move ...").
        - apply (YT_RESCHEDULE_APPLY=1): each eligible move drives
          ``dom.reschedule_open_set_save``.
        - NEEDS_LIVE_LIST moves -> ``skipped`` (reason ``needs_live_list``).
        - target-day cap would be exceeded -> ``skipped`` (reason ``cap``).
        - per-move exception -> ``error``; the batch continues.
    """
    is_dry_run = (not apply_enabled()) if dry_run is None else bool(dry_run)

    results: List[Dict[str, Any]] = []
    # Batch-local target-day fill counter: (channel_id, to_date) -> planned count.
    target_fill: Dict[tuple, int] = {}

    for move in moves or []:
        video_id = move.get("video_id")
        channel_id = move.get("channel_id")
        to_date = move.get("to_date")
        slot_local = move.get("slot_local")

        # 1) Skip surplus moves the planner couldn't name (needs the live list).
        if video_id == NEEDS_LIVE_LIST or not video_id:
            rec = _move_record(move, STATUS_SKIPPED, reason="needs_live_list")
            results.append(rec)
            if emit_signals:
                _emit_move_breadcrumb(rec, is_dry_run)
                _store_move_outcome(rec, is_dry_run)
            continue

        # 2) CAP SAFETY: never plan/apply more than `cap` onto a target day.
        key = (channel_id, to_date)
        if target_fill.get(key, 0) >= cap:
            rec = _move_record(move, STATUS_SKIPPED, reason="cap")
            results.append(rec)
            logger.warning(
                "[RESCHED-APPLY] Skip %s -> %s @ %s: target day at cap (%d)",
                video_id, to_date, slot_local, cap,
            )
            if emit_signals:
                _emit_move_breadcrumb(rec, is_dry_run)
                _store_move_outcome(rec, is_dry_run)
            continue

        # 3) Dry-run: log a "would move" and NEVER touch the DOM.
        if is_dry_run:
            logger.info(
                "[RESCHED-APPLY] would move %s %s -> %s @ %s",
                video_id, move.get("from_date"), to_date, slot_local,
            )
            rec = _move_record(move, STATUS_DRY_RUN)
            results.append(rec)
            target_fill[key] = target_fill.get(key, 0) + 1
            if emit_signals:
                _emit_move_breadcrumb(rec, is_dry_run)
                _store_move_outcome(rec, is_dry_run)
            continue

        # 4) REAL APPLY (YT_RESCHEDULE_APPLY=1): drive the reused picker per move.
        try:
            if dom is None:
                raise RuntimeError("apply requested but no DOM driver provided")
            ok = dom.reschedule_open_set_save(to_date, slot_local, video_id=video_id)
            if ok:
                rec = _move_record(move, STATUS_APPLIED)
                target_fill[key] = target_fill.get(key, 0) + 1
            else:
                rec = _move_record(move, STATUS_ERROR, reason="dom_returned_false")
        except Exception as exc:  # per-move: never abort the batch
            logger.error(
                "[RESCHED-APPLY] apply error for %s -> %s: %s: %s",
                video_id, to_date, type(exc).__name__, exc,
            )
            rec = _move_record(move, STATUS_ERROR, reason=f"{type(exc).__name__}: {exc}")
        results.append(rec)
        if emit_signals:
            _emit_move_breadcrumb(rec, is_dry_run)
            _store_move_outcome(rec, is_dry_run)

    summary = {
        "dry_run": is_dry_run,
        "cap": cap,
        "total": len(results),
        "applied": sum(1 for r in results if r["status"] == STATUS_APPLIED),
        "dry_run_count": sum(1 for r in results if r["status"] == STATUS_DRY_RUN),
        "skipped": sum(1 for r in results if r["status"] == STATUS_SKIPPED),
        "errors": sum(1 for r in results if r["status"] == STATUS_ERROR),
        "results": results,
    }
    return summary


def flatten_plan_moves(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten a plan_all_channels() result into a single list of move rows."""
    moves: List[Dict[str, Any]] = []
    for ch in plan.get("channels", []) or []:
        for mv in ch.get("moves", []) or []:
            moves.append(mv)
    return moves


def apply_plan(
    *,
    dom: Any = None,
    plan: Optional[Dict[str, Any]] = None,
    plan_factory: Optional[Callable[[], Dict[str, Any]]] = None,
    cap: int = HARD_CAP_PER_DAY,
    dry_run: Optional[bool] = None,
    emit_signals: bool = True,
) -> Dict[str, Any]:
    """Compute (or accept) the #851 plan, then apply/dry-run its moves.

    Args:
        dom: injected DOM driver (only used on real apply).
        plan: a pre-computed plan_all_channels() result; if omitted, ``plan_factory``
            is called (default: reschedule_planner.plan_all_channels).
        plan_factory: zero-arg callable returning a plan dict (injectable for tests).
        cap / dry_run / emit_signals: see apply_moves.

    Returns:
        apply_moves(...) summary augmented with ``skill`` + ``plan_summary``.
    """
    if plan is None:
        if plan_factory is None:
            from modules.platform_integration.youtube_shorts_scheduler.src.reschedule_planner import (
                plan_all_channels,
            )
            plan_factory = plan_all_channels
        plan = plan_factory()

    moves = flatten_plan_moves(plan)
    result = apply_moves(
        moves, dom=dom, cap=cap, dry_run=dry_run, emit_signals=emit_signals
    )
    result["skill"] = SKILL_NAME
    result["plan_summary"] = plan.get("summary", {})
    result["success"] = True
    return result
