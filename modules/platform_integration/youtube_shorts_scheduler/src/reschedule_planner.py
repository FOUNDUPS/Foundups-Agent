"""
Reschedule Planner - dry-run REBALANCE PLAN for over-crowded schedule days.

Slice: SHORTS_RESCHEDULE_PLAN_PHASE1  (Mode B, Phase 1 - PREVIEW/decision layer)

Problem
-------
Before the per-day cap landed (#844, HARD_CAP_PER_DAY=3 in schedule_tracker.py),
the historical backlog was scheduled at up to 8/day. Those over-crowded days are
now "illegal" against the cap. This module computes a PLAN to MOVE the excess
(count > HARD_CAP_PER_DAY) off each over-crowded day onto the nearest under-target
upcoming days, placing each moved item into a US-ET peak slot converted to the
channel's Studio-account timezone (peak_window.py, #847).

Strictly read-only / dry-run
----------------------------
This is the PREVIEW/decision layer. It NEVER mutates a schedule, never opens a
browser, never calls a live model. It reads the persisted per-channel tracker
(memory/schedule_<id>.json via ScheduleTracker) and RETURNS a structured plan.

The MUTATING DOM apply (click "Scheduled" -> ytcp-video-visibility-edit-popup
date/time picker) is an explicit Phase-2 follow-up, NOT built here. See the
"Phase-2 apply seam" note below.

Data model granularity (Phase 0 finding)
-----------------------------------------
ScheduleTracker stores BOTH:
  - schedule:  Dict[date_str, int]        (date -> count)            line ~100
  - video_ids: Dict[date_str, List[str]]  (date -> [video_ids])      line ~101
So a video<->date mapping EXISTS and the plan names which videos move WHEN the
ids are present for the over-crowded date. BUT the count is authoritative and can
exceed the recorded id list (set_count()/sync_from_youtube() can leave video_ids
incomplete, and the historical 8/day backlog predates id tracking). When the
recorded ids for a date are fewer than the excess to move, the surplus moves are
labelled video_id="(needs-live-list)" -- specific-video selection for those needs
the LIVE Studio list (Phase 2).

Malleable seams (intentional)
-----------------------------
- SLOT ASSIGNMENT is a pure function (assign_peak_slots) behind get_peak_slots_*.
  Swap the peak policy WITHOUT touching the move math.
- TARGET SELECTION (find_target_days) is pure; a future view-based ("low-viewed
  first") prioritization plugs in here -- BUT that needs per-video view data which
  is NOT in the tracker (Phase-2 / separate signal). See "view-data seam" below.
- Phase-2 apply seam: a plan row is a complete instruction (channel, from_date,
  to_date, slot_et, slot_local, video_id). The Phase-2 DOM applier consumes these
  rows; it lives outside this module and is gated behind its own explicit slice.

WSP References:
- WSP 3:  platform_integration owns publish-time/rebalance policy.
- WSP 84: reuse ScheduleTracker, HARD_CAP_PER_DAY (#844), peak_window.py (#847),
          youtube_channel_registry.
- WSP 50: pure, unit-testable; no mutation, no browser, no live model.
- WSP 22: ModLog documents the Phase-2 apply seam + view-data prioritization seam.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Authoritative per-day cap. Imported from the tracker so this planner tracks the
# single load-bearing knob (HARD_CAP_PER_DAY, schedule_tracker.py, landed #844).
try:
    from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import (
        HARD_CAP_PER_DAY,
        ScheduleTracker,
    )
except Exception:  # pragma: no cover - defensive import for isolated tests
    HARD_CAP_PER_DAY = 3
    ScheduleTracker = None  # type: ignore

# Peak-slot policy + per-channel tz conversion (#847). Pure helpers.
try:
    from modules.platform_integration.youtube_shorts_scheduler.src.peak_window import (
        convert_et_to_channel_tz,
        get_peak_slots_et,
    )
except Exception:  # pragma: no cover - defensive import for isolated tests
    def get_peak_slots_et() -> List[str]:  # type: ignore
        return ["08:00", "12:00", "20:00"]

    def convert_et_to_channel_tz(et_time, channel_tz, on_date):  # type: ignore
        return et_time

# How far ahead to search for under-target target days when none are free sooner.
DEFAULT_HORIZON_DAYS = 90

# Sentinel for moves whose specific video id is unknown from the tracker (needs
# the LIVE Studio list -- Phase 2).
NEEDS_LIVE_LIST = "(needs-live-list)"

# Date format the tracker uses everywhere: "Jan 5, 2026" (Windows-safe, no %-d).
_DATE_FMT = "%b %d, %Y"


def _format_date(d: datetime) -> str:
    """Format a datetime in the tracker's exact date-key format."""
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse a 'Jan 5, 2026' tracker date key to a datetime (None if unparseable)."""
    try:
        return datetime.strptime(date_str.strip(), _DATE_FMT)
    except ValueError:
        try:
            return datetime.strptime(" ".join(date_str.split()), _DATE_FMT)
        except ValueError:
            return None


@dataclass
class MovePlan:
    """One proposed move: take an over-cap item off from_date onto to_date@slot."""

    channel_id: str
    channel_name: str
    from_date: str
    to_date: str
    slot_et: str
    slot_local: str
    video_id: str  # real id, or NEEDS_LIVE_LIST when the tracker can't name it

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "from_date": self.from_date,
            "to_date": self.to_date,
            "slot_et": self.slot_et,
            "slot_local": self.slot_local,
            "video_id": self.video_id,
        }


@dataclass
class ChannelReschedulePlan:
    """The rebalance plan for one channel + its summary."""

    channel_id: str
    channel_name: str
    timezone: str
    cap: int
    days_over_cap: int
    total_moves: int
    unplaceable_moves: int  # excess that found no under-cap target within horizon
    moves: List[MovePlan] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "timezone": self.timezone,
            "cap": self.cap,
            "days_over_cap": self.days_over_cap,
            "total_moves": self.total_moves,
            "unplaceable_moves": self.unplaceable_moves,
            "moves": [m.to_dict() for m in self.moves],
        }


# === Pure helper: which dates are over the cap, and by how much ===============

def find_over_cap_days(
    schedule: Dict[str, int], cap: int = HARD_CAP_PER_DAY
) -> List[tuple]:
    """Return [(date_str, parsed_dt, excess)] for days with count > cap.

    excess = count - cap (the number of items that MUST move off that day).
    Sorted chronologically (nearest over-crowded day first). Days that don't parse
    are skipped (cannot place them deterministically).
    """
    over: List[tuple] = []
    for date_str, count in schedule.items():
        if count <= cap:
            continue
        parsed = _parse_date(date_str)
        if parsed is None:
            logger.warning("[RESCHED] Unparseable over-cap date skipped: %r", date_str)
            continue
        over.append((date_str, parsed, count - cap))
    over.sort(key=lambda t: t[1])
    return over


# === Malleable seam: target-day selection ====================================

def find_target_days(
    schedule: Dict[str, int],
    *,
    cap: int = HARD_CAP_PER_DAY,
    after: datetime,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    source_dates: Optional[set] = None,
) -> List[tuple]:
    """Return [(date_str, parsed_dt, free_slots)] for under-cap upcoming days.

    A target day is any calendar day in (after, after+horizon] whose current count
    is < cap, EXCLUDING the over-crowded source days themselves (never plan a move
    onto a day we're trying to drain). free_slots = cap - count (>= 1). Ordered
    nearest-first so excess lands as soon as possible.

    NOTE (view-data seam): this orders targets by date only. A future "low-viewed
    first" prioritization would re-order/select the items being MOVED by per-video
    view counts -- but view data is NOT in the tracker, so that prioritization is a
    separate signal (Phase 2). Target-DAY selection stays date-driven here.
    """
    source = source_dates or set()
    targets: List[tuple] = []
    for offset in range(1, horizon_days + 1):
        d = after + timedelta(days=offset)
        date_str = _format_date(d)
        if date_str in source:
            continue
        count = schedule.get(date_str, 0)
        free = cap - count
        if free >= 1:
            targets.append((date_str, d, free))
    return targets


# === Malleable seam: peak-slot assignment (per channel tz) ====================

def assign_peak_slot(slot_index: int, channel_tz: str, on_date: datetime) -> tuple:
    """Return (slot_et, slot_local) for the slot_index-th fill of a day.

    slot_index 0 -> morning (08:00 ET), 1 -> lunch (12:00 ET), 2 -> evening (20:00
    ET); beyond the list it clamps to the last slot. slot_local is the bare 12h
    wall-clock to type into Studio in the channel account tz (DST-aware, #847).
    """
    et_slots = get_peak_slots_et()
    idx = min(slot_index, len(et_slots) - 1)
    slot_et = et_slots[idx]
    slot_local = convert_et_to_channel_tz(slot_et, channel_tz, on_date)
    return slot_et, slot_local


def _video_ids_for_excess(
    video_ids: Dict[str, List[str]], from_date: str, excess: int, cap: int
) -> List[str]:
    """Pick which video ids move off an over-crowded day (the surplus over the cap).

    We keep the FIRST `cap` recorded ids on the source day and move the surplus
    (the trailing ids). When the recorded id list is shorter than count (historical
    8/day backlog predates id tracking, or set_count/sync left it incomplete), the
    missing surplus ids are NEEDS_LIVE_LIST -- naming those needs the live Studio
    list (Phase 2).
    """
    ids = list(video_ids.get(from_date, []))
    # Surplus recorded ids are everything beyond the first `cap` kept on the day.
    surplus_recorded = ids[cap:] if len(ids) > cap else []
    moving: List[str] = list(surplus_recorded[:excess])
    while len(moving) < excess:
        moving.append(NEEDS_LIVE_LIST)
    return moving


def plan_channel_reschedule(
    channel_id: str,
    channel_name: str,
    channel_tz: str,
    schedule: Dict[str, int],
    *,
    video_ids: Optional[Dict[str, List[str]]] = None,
    cap: int = HARD_CAP_PER_DAY,
    today: Optional[datetime] = None,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
) -> ChannelReschedulePlan:
    """Compute the dry-run rebalance plan for ONE channel (pure + deterministic).

    For each over-crowded day (count > cap), move the excess (count - cap) onto the
    nearest under-target upcoming days, filling each target up to (but never over)
    the cap and assigning peak slots in the channel tz. A target day's remaining
    free capacity is tracked so it is NEVER planned over the cap.

    Args:
        channel_id: tracker key / YouTube channel id.
        channel_name: human-readable name (for plan rows).
        channel_tz: IANA tz of the channel Studio account (for slot conversion).
        schedule: date_str -> count (from ScheduleTracker.schedule).
        video_ids: date_str -> [ids] (from ScheduleTracker.video_ids); optional.
        cap: per-day hard cap (default HARD_CAP_PER_DAY=3).
        today: injectable clock (default datetime.now()); targets are strictly after.
        horizon_days: how far ahead to search for target days.

    Returns:
        ChannelReschedulePlan with moves + summary (days_over_cap, total_moves,
        unplaceable_moves).
    """
    vids = video_ids or {}
    base = today or datetime.now()

    over_days = find_over_cap_days(schedule, cap=cap)
    source_dates = {d for (d, _dt, _x) in over_days}

    # Build a fill-tracker for target days: date_str -> already-used count in the
    # plan (start from current schedule count, never exceed cap).
    targets = find_target_days(
        schedule,
        cap=cap,
        after=base,
        horizon_days=horizon_days,
        source_dates=source_dates,
    )
    target_used: Dict[str, int] = {d: schedule.get(d, 0) for (d, _dt, _f) in targets}
    target_order: List[tuple] = list(targets)  # (date_str, dt, free) nearest-first

    moves: List[MovePlan] = []
    unplaceable = 0

    for from_date, _from_dt, excess in over_days:
        moving_ids = _video_ids_for_excess(vids, from_date, excess, cap)
        for vid in moving_ids:
            placed = False
            for to_date, to_dt, _free in target_order:
                used = target_used.get(to_date, 0)
                if used >= cap:
                    continue
                slot_index = used  # 0->morning, 1->lunch, 2->evening
                slot_et, slot_local = assign_peak_slot(slot_index, channel_tz, to_dt)
                moves.append(
                    MovePlan(
                        channel_id=channel_id,
                        channel_name=channel_name,
                        from_date=from_date,
                        to_date=to_date,
                        slot_et=slot_et,
                        slot_local=slot_local,
                        video_id=vid,
                    )
                )
                target_used[to_date] = used + 1
                placed = True
                break
            if not placed:
                unplaceable += 1
                logger.warning(
                    "[RESCHED] No under-cap target within %d days for a move off %s "
                    "(channel %s)",
                    horizon_days,
                    from_date,
                    channel_id,
                )

    return ChannelReschedulePlan(
        channel_id=channel_id,
        channel_name=channel_name,
        timezone=channel_tz,
        cap=cap,
        days_over_cap=len(over_days),
        total_moves=len(moves),
        unplaceable_moves=unplaceable,
        moves=moves,
    )


# === Data source seam: load a channel's persisted schedule (read-only) ========

def _default_load_schedule(channel_id: str) -> tuple:
    """Default data source: persisted per-channel tracker JSON (read-only).

    Returns (schedule, video_ids) from ScheduleTracker(channel_id). No browser,
    no mutation.
    """
    if ScheduleTracker is None:  # pragma: no cover - only when import failed
        return {}, {}
    tracker = ScheduleTracker(channel_id)
    return dict(tracker.schedule), dict(tracker.video_ids)


def plan_all_channels(
    *,
    cap: int = HARD_CAP_PER_DAY,
    channels: Optional[List[Dict[str, str]]] = None,
    load_schedule: Callable[[str], tuple] = _default_load_schedule,
    today: Optional[datetime] = None,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
) -> Dict[str, Any]:
    """Compute the dry-run rebalance plan across all shorts-enabled channels.

    Args:
        cap: per-day hard cap (default HARD_CAP_PER_DAY=3).
        channels: optional [{channel_id, name, timezone}, ...] override (default:
                  registry shorts channels).
        load_schedule: (channel_id) -> (schedule, video_ids). Swappable data source.
        today: injectable clock for deterministic tests.
        horizon_days: target-search horizon.

    Returns:
        {dry_run: True, cap, channel_count, channels: [plan_dict...], summary:
         {days_over_cap, total_moves, unplaceable_moves, channels_needing_rebalance}}.
    """
    chan_list = channels if channels is not None else _default_channels()

    channel_plans: List[Dict[str, Any]] = []
    total_days_over = 0
    total_moves = 0
    total_unplaceable = 0
    channels_needing = 0

    for ch in chan_list:
        schedule, video_ids = load_schedule(ch["channel_id"])
        plan = plan_channel_reschedule(
            ch["channel_id"],
            ch.get("name", ch["channel_id"]),
            ch.get("timezone", "UTC"),
            schedule,
            video_ids=video_ids,
            cap=cap,
            today=today,
            horizon_days=horizon_days,
        )
        channel_plans.append(plan.to_dict())
        total_days_over += plan.days_over_cap
        total_moves += plan.total_moves
        total_unplaceable += plan.unplaceable_moves
        if plan.total_moves > 0 or plan.days_over_cap > 0:
            channels_needing += 1

    return {
        "dry_run": True,  # ALWAYS preview in this slice; apply is Phase 2.
        "cap": cap,
        "channel_count": len(chan_list),
        "channels": channel_plans,
        "summary": {
            "days_over_cap": total_days_over,
            "total_moves": total_moves,
            "unplaceable_moves": total_unplaceable,
            "channels_needing_rebalance": channels_needing,
        },
    }


def _default_channels() -> List[Dict[str, str]]:
    """Load shorts-enabled channels (id + name + timezone) from the registry."""
    from modules.infrastructure.shared_utilities.youtube_channel_registry import (
        get_channels,
    )

    channels: List[Dict[str, str]] = []
    for ch in get_channels(role="shorts"):
        cid = ch.get("id")
        if not cid:
            continue
        channels.append(
            {
                "channel_id": cid,
                "name": ch.get("name", ch.get("key", cid)),
                "timezone": ch.get("timezone", "UTC"),
            }
        )
    return channels
