"""
Unit tests for the reschedule_plan SKILLz + reschedule_planner (Mode B Phase 1).

Slice: SHORTS_RESCHEDULE_PLAN_PHASE1

Model under test
----------------
Given the persisted per-channel schedule tracker (date -> count, date -> [ids]),
compute a dry-run REBALANCE PLAN: for any day with count > HARD_CAP_PER_DAY, move
the excess (count - cap) onto the nearest under-target upcoming days, into US-ET
peak slots converted to the channel tz, NEVER exceeding the cap on a target day.

These tests are mock-only (no browser, no daemon, no live models) and NON-VACUOUS:
  - a day at 5 (cap 3) -> plan moves exactly 2; no target exceeds the cap
  - a fully-<=cap schedule -> empty plan (nothing to do)
  - peak-slot + per-channel tz assignment correct (ET -> channel wall-clock)
  - breadcrumb + PatternMemory emission invoked (mocked + asserted)
  - NON-VACUITY: an injected over-cap day MUST produce moves -- a planner that
    ignored over-cap days would fail (see test_planner_must_not_ignore_over_cap).
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from modules.platform_integration.youtube_shorts_scheduler.src.reschedule_planner import (
    NEEDS_LIVE_LIST,
    find_over_cap_days,
    plan_all_channels,
    plan_channel_reschedule,
)
from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import (
    HARD_CAP_PER_DAY,
)
from modules.platform_integration.youtube_shorts_scheduler.skillz.reschedule_plan.executor import (
    DRY_RUN,
    run_skill,
)

# Deterministic clock so upcoming-date strings are stable across runs.
# Jan 1 2026; targets are strictly AFTER this date.
FIXED_TODAY = datetime(2026, 1, 1)

# A New York channel (identity ET conversion) and a Tokyo channel (offset).
NY_TZ = "America/New_York"
TOKYO_TZ = "Asia/Tokyo"


def _date(d: datetime) -> str:
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def test_hard_cap_is_three():
    """Pin the load-bearing cap (HARD_CAP_PER_DAY=3, landed #844)."""
    assert HARD_CAP_PER_DAY == 3


def test_dry_run_constant_is_true():
    """This slice is ALWAYS a dry-run preview; the apply is Phase 2."""
    assert DRY_RUN is True


# --- Core: a day at 5 -> exactly 2 moves, no target over cap -----------------

def test_day_at_five_moves_two_no_target_over_cap():
    """A day with 5 (cap 3) plans exactly 2 moves onto under-target days."""
    over_date = _date(datetime(2026, 1, 20))  # 19 days out, well past targets
    schedule = {over_date: 5}
    plan = plan_channel_reschedule(
        "UC_NY",
        "FoundUps",
        NY_TZ,
        schedule,
        video_ids={},
        today=FIXED_TODAY,
    )
    assert plan.days_over_cap == 1
    assert plan.total_moves == 2  # excess = 5 - 3
    assert plan.unplaceable_moves == 0
    # All moves originate from the over-crowded day.
    assert all(m.from_date == over_date for m in plan.moves)
    # No target day is planned over the cap: tally per to_date <= cap.
    per_target = {}
    for m in plan.moves:
        per_target[m.to_date] = per_target.get(m.to_date, 0) + 1
    assert all(c <= HARD_CAP_PER_DAY for c in per_target.values())
    # Targets must be strictly in the future (after FIXED_TODAY) and not the source.
    for m in plan.moves:
        to_dt = datetime.strptime(m.to_date, "%b %d, %Y")
        assert to_dt > FIXED_TODAY
        assert m.to_date != over_date


def test_target_with_existing_count_not_pushed_over_cap():
    """A near target already at cap-1 takes only ONE move, never exceeding the cap."""
    over_date = _date(datetime(2026, 1, 20))
    near1 = _date(datetime(2026, 1, 2))  # already at 2 -> 1 free slot
    near2 = _date(datetime(2026, 1, 3))  # empty -> 3 free
    schedule = {over_date: 5, near1: 2, near2: 0}
    plan = plan_channel_reschedule(
        "UC_NY", "FoundUps", NY_TZ, schedule, video_ids={}, today=FIXED_TODAY
    )
    assert plan.total_moves == 2
    per_target = {}
    for m in plan.moves:
        per_target[m.to_date] = per_target.get(m.to_date, 0) + 1
    # near1 had 2 -> at most 1 new move there (2 + 1 = 3 = cap).
    assert per_target.get(near1, 0) <= 1
    # And no target's (existing + planned) exceeds the cap.
    assert schedule.get(near1, 0) + per_target.get(near1, 0) <= HARD_CAP_PER_DAY
    assert schedule.get(near2, 0) + per_target.get(near2, 0) <= HARD_CAP_PER_DAY


# --- Empty plan when nothing is over the cap --------------------------------

def test_all_under_cap_yields_empty_plan():
    """A schedule with every day <= cap plans zero moves (nothing to do)."""
    schedule = {
        _date(datetime(2026, 1, 10)): 3,
        _date(datetime(2026, 1, 11)): 2,
        _date(datetime(2026, 1, 12)): 1,
    }
    plan = plan_channel_reschedule(
        "UC_NY", "FoundUps", NY_TZ, schedule, video_ids={}, today=FIXED_TODAY
    )
    assert plan.days_over_cap == 0
    assert plan.total_moves == 0
    assert plan.moves == []


# --- Peak-slot + per-channel tz assignment ----------------------------------

def test_peak_slot_and_tz_assignment_ny_identity():
    """NY channel: ET peak slots type through as the same wall clock (identity)."""
    over_date = _date(datetime(2026, 1, 20))
    # 4 over the cap so the first target fills all 3 slots (morning/lunch/evening).
    schedule = {over_date: 7}  # excess 4
    plan = plan_channel_reschedule(
        "UC_NY", "FoundUps", NY_TZ, schedule, video_ids={}, today=FIXED_TODAY
    )
    # The first 3 moves land on the SAME nearest target with the 3 peak slots.
    first_target = plan.moves[0].to_date
    same_day = [m for m in plan.moves if m.to_date == first_target]
    assert len(same_day) == 3
    # Slots assigned in order morning/lunch/evening by ET source.
    assert [m.slot_et for m in same_day] == ["08:00", "12:00", "20:00"]
    # NY in January (EST) is identity to ET -> bare 12h local equals the ET clock.
    assert [m.slot_local for m in same_day] == ["8:00 AM", "12:00 PM", "8:00 PM"]


def test_peak_slot_tz_conversion_tokyo_offset():
    """Tokyo channel: 08:00 ET (EST) converts to 10:00 PM JST same calendar day.

    EST is UTC-5, JST is UTC+9 -> +14h. 08:00 ET -> 22:00 JST = '10:00 PM'.
    """
    over_date = _date(datetime(2026, 1, 20))
    schedule = {over_date: 4}  # excess 1 -> single morning slot
    plan = plan_channel_reschedule(
        "UC_TOKYO", "Move2Japan", TOKYO_TZ, schedule, video_ids={}, today=FIXED_TODAY
    )
    assert plan.total_moves == 1
    move = plan.moves[0]
    assert move.slot_et == "08:00"
    assert move.slot_local == "10:00 PM"  # 08:00 EST + 14h = 22:00 JST


# --- video<->date naming + needs-live-list fallback -------------------------

def test_recorded_ids_named_surplus_labelled_needs_live_list():
    """Recorded surplus ids are NAMED; missing surplus -> '(needs-live-list)'.

    Day count 5 (excess 2). Only 4 ids recorded -> the first 3 stay, 1 recorded
    surplus id moves NAMED, the 2nd move is unnamed (needs the live Studio list).
    """
    over_date = _date(datetime(2026, 1, 20))
    schedule = {over_date: 5}
    video_ids = {over_date: ["v0", "v1", "v2", "v3"]}  # 4 recorded for count 5
    plan = plan_channel_reschedule(
        "UC_NY", "FoundUps", NY_TZ, schedule, video_ids=video_ids, today=FIXED_TODAY
    )
    moved_ids = [m.video_id for m in plan.moves]
    assert "v3" in moved_ids  # the recorded surplus id (index 3, beyond first cap=3)
    assert NEEDS_LIVE_LIST in moved_ids  # the unrecorded surplus -> needs live list
    assert len(moved_ids) == 2


# --- find_over_cap_days helper ----------------------------------------------

def test_find_over_cap_days_excess_math():
    """find_over_cap_days returns (date, dt, excess=count-cap) only for over days."""
    schedule = {
        _date(datetime(2026, 1, 10)): 3,  # at cap, not over
        _date(datetime(2026, 1, 11)): 8,  # excess 5
        _date(datetime(2026, 1, 12)): 4,  # excess 1
    }
    over = find_over_cap_days(schedule, cap=HARD_CAP_PER_DAY)
    excess_by_date = {d: x for (d, _dt, x) in over}
    assert _date(datetime(2026, 1, 10)) not in excess_by_date
    assert excess_by_date[_date(datetime(2026, 1, 11))] == 5
    assert excess_by_date[_date(datetime(2026, 1, 12))] == 1


# --- NON-VACUITY: the planner MUST act on over-cap days ----------------------

def test_planner_must_not_ignore_over_cap():
    """Inject an over-cap day; a planner that IGNORED it would produce 0 moves.

    This is the load-bearing non-vacuity guard: total_moves MUST equal the injected
    excess. A no-op / over-cap-ignoring implementation fails here.
    """
    over_date = _date(datetime(2026, 2, 1))
    schedule = {over_date: 6}  # excess 3
    plan = plan_channel_reschedule(
        "UC_NY", "FoundUps", NY_TZ, schedule, video_ids={}, today=FIXED_TODAY
    )
    # Exactly the excess (6 - 3) must be planned for movement.
    assert plan.total_moves == 3
    assert plan.days_over_cap == 1
    # And every move actually leaves the over-crowded day.
    assert all(m.from_date == over_date for m in plan.moves)


def test_no_target_within_horizon_marks_unplaceable():
    """When no under-cap target exists within the horizon, excess is unplaceable.

    Horizon of 0 days means no target days at all -> the excess cannot be placed.
    """
    over_date = _date(datetime(2026, 1, 20))
    schedule = {over_date: 5}  # excess 2
    plan = plan_channel_reschedule(
        "UC_NY",
        "FoundUps",
        NY_TZ,
        schedule,
        video_ids={},
        today=FIXED_TODAY,
        horizon_days=0,
    )
    assert plan.total_moves == 0
    assert plan.unplaceable_moves == 2


# --- plan_all_channels aggregation + dry-run flag ---------------------------

def test_plan_all_channels_aggregates_and_is_dry_run():
    """plan_all_channels sums per-channel plans and is flagged dry-run."""
    over_date = _date(datetime(2026, 1, 20))

    def load_schedule(channel_id):
        if channel_id == "UC_NY":
            return {over_date: 5}, {}  # excess 2
        return {over_date: 3}, {}  # at cap, no moves

    channels = [
        {"channel_id": "UC_NY", "name": "FoundUps", "timezone": NY_TZ},
        {"channel_id": "UC_TOKYO", "name": "Move2Japan", "timezone": TOKYO_TZ},
    ]
    result = plan_all_channels(
        channels=channels,
        load_schedule=load_schedule,
        today=FIXED_TODAY,
    )
    assert result["dry_run"] is True
    assert result["channel_count"] == 2
    assert result["summary"]["days_over_cap"] == 1
    assert result["summary"]["total_moves"] == 2
    assert result["summary"]["channels_needing_rebalance"] == 1


# --- Signal emission: breadcrumb + PatternMemory must be invoked -------------

def test_run_skill_emits_breadcrumb_and_pattern_memory():
    """run_skill must emit a reschedule_plan breadcrumb AND a SkillOutcome."""
    over_date = _date(datetime(2026, 1, 20))

    def load_schedule(channel_id):
        return {over_date: 5}, {}  # excess 2

    channels = [{"channel_id": "UC_NY", "name": "FoundUps", "timezone": NY_TZ}]

    with patch(
        "modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry"
    ) as bc, patch(
        "modules.infrastructure.wre_core.src.pattern_memory.PatternMemory"
    ) as pm, patch(
        "modules.infrastructure.wre_core.src.pattern_memory.SkillOutcome"
    ) as outcome:
        result = run_skill(
            channels=channels,
            load_schedule=load_schedule,
            today=FIXED_TODAY,
            emit_signals=True,
        )

        # Breadcrumb stored with the reschedule_plan event type + plan metadata.
        bc.return_value.store_breadcrumb.assert_called_once()
        kwargs = bc.return_value.store_breadcrumb.call_args.kwargs
        assert kwargs["event_type"] == "reschedule_plan"
        assert kwargs["source_dae"] == "youtube_shorts_scheduler"
        assert "plan" in kwargs["metadata"]
        assert "summary" in kwargs["metadata"]

        # PatternMemory().store_outcome called with a SkillOutcome.
        outcome.assert_called_once()
        out_kwargs = outcome.call_args.kwargs
        assert out_kwargs["skill_name"] == "reschedule_plan"
        pm.return_value.store_outcome.assert_called_once()

    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["skill"] == "reschedule_plan"
    assert result["breadcrumb_emitted"] is True
    assert result["outcome_stored"] is True


def test_run_skill_no_signals_skips_emission():
    """--no-signals path: emission helpers are NOT invoked."""
    over_date = _date(datetime(2026, 1, 20))

    def load_schedule(channel_id):
        return {over_date: 5}, {}

    channels = [{"channel_id": "UC_NY", "name": "FoundUps", "timezone": NY_TZ}]

    with patch(
        "modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry"
    ) as bc:
        result = run_skill(
            channels=channels,
            load_schedule=load_schedule,
            today=FIXED_TODAY,
            emit_signals=False,
        )
        bc.assert_not_called()

    assert result["breadcrumb_emitted"] is False
    assert result["outcome_stored"] is False
