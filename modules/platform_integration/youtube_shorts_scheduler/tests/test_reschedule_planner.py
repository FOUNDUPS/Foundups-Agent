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
from copy import deepcopy
from unittest.mock import patch

import pytest

from modules.platform_integration.youtube_shorts_scheduler.src.reschedule_planner import (
    NEEDS_LIVE_LIST,
    find_over_cap_days,
    plan_all_channels,
    plan_channel_reschedule,
    plan_bounded_unlisted_batch,
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


# Bounded unlisted preview: synthetic observations only, never a writer input.
_CHANNEL = "UC" + "a" * 22


def _at(value):
    return datetime.fromisoformat(value)


def _clip(number, topic="topic-a", **changes):
    return dict(channel_id=_CHANNEL, video_id=f"v{number:010d}",
                visibility="unlisted", source_at=_at("2026-11-16T11:00:00+09:00"),
                topic=topic, evidence_ref=f"fixture:transcript:{number}",
                content_verified=True, held=False, **changes)


def _preview_inputs():
    clips = [_clip(1), _clip(2), _clip(3, "topic-b"), _clip(4, "topic-b")]
    return dict(channel_id=_CHANNEL, candidates=clips,
                allowed_video_ids=[r["video_id"] for r in clips],
                source_start=_at("2026-11-15T00:00:00+09:00"),
                source_end=_at("2026-11-17T00:00:00+09:00"),
                windows=[(_at("2026-11-18T20:00:00+09:00"), _at("2026-11-19T04:00:00+09:00")),
                         (_at("2026-11-19T20:00:00+09:00"), _at("2026-11-20T04:00:00+09:00"))],
                timezone=TOKYO_TZ, occupied=[], inventory_complete=True,
                observed_at=_at("2026-11-16T12:00:00+09:00"),
                now=_at("2026-11-16T12:00:10+09:00"), live_state="not_live",
                operator_editing=False)


def test_bounded_preview_top_bottom_topics_offsets_and_no_mutation():
    args = _preview_inputs()
    original = deepcopy(args)
    result = plan_bounded_unlisted_batch(**args)
    assert args == original
    assert result == plan_bounded_unlisted_batch(**args)
    assert result["status"] == "preview_only"
    assert result["effects_disabled"] is True
    assert result["execution_authorized"] is False
    assert result["scheduling_verified"] is False
    assert [r["video_id"] for r in result["planned"]] == [f"v{n:010d}" for n in (1, 4, 2, 3)]
    assert [r["publish_at_studio"] for r in result["planned"]] == [
        "2026-11-18T20:07:00+09:00", "2026-11-19T00:19:00+09:00",
        "2026-11-19T20:31:00+09:00", "2026-11-20T00:31:00+09:00"]
    assert result["planned"][0]["publish_at_audience"] == "2026-11-18T06:07:00-05:00"
    assert not result["unplaced"]


def test_bounded_preview_only_explicit_window_no_closing_release():
    args = _preview_inputs()
    args["windows"] = args["windows"][:1]
    result = plan_bounded_unlisted_batch(**args)
    assert len(result["planned"]) == 2
    assert len(result["unplaced"]) == 2
    assert all(_at(r["publish_at_studio"]) < args["windows"][0][1] for r in result["planned"])


def test_bounded_preview_exclusions_and_identical_duplicate():
    args = _preview_inputs()
    args["candidates"][0]["held"] = True
    args["candidates"][1]["visibility"] = "scheduled"
    args["candidates"][2]["content_verified"] = False
    args["candidates"].append(dict(args["candidates"][3]))
    args["allowed_video_ids"].append("missing0001")
    result = plan_bounded_unlisted_batch(**args)
    assert [r["video_id"] for r in result["planned"]] == ["v0000000004"]
    assert {r["reason"] for r in result["excluded"]} == {
        "held", "already_scheduled_or_reserved", "content_evidence_missing", "candidate_missing"}


@pytest.mark.parametrize("change,reason", [
    ({"live_state": "live"}, "live_state_not_clear"),
    ({"live_state": "unknown"}, "live_state_not_clear"),
    ({"operator_editing": True}, "operator_editing"),
    ({"inventory_complete": False}, "inventory_incomplete"),
    ({"observed_at": _at("2026-11-16T11:58:00+09:00")}, "observations_stale_or_future"),
    ({"observed_at": _at("2026-11-16T12:01:00+09:00")}, "observations_stale_or_future"),
])
def test_bounded_preview_observation_blocks(change, reason):
    args = _preview_inputs()
    args.update(change)
    result = plan_bounded_unlisted_batch(**args)
    assert result["status"] == "blocked" and result["reason"] == reason
    assert not result["planned"] and result["effects_disabled"]


@pytest.mark.parametrize("change", [
    {"minimum_spacing_minutes": True}, {"minimum_spacing_minutes": 239},
    {"minute_offsets": [True, 19]}, {"minute_offsets": [[], 19]},
    {"minute_offsets": [7, 7]}, {"minute_offsets": [-1, 19]},
    {"max_per_day": True}, {"channel_id": "move2japan"},
    {"timezone": "not/a/timezone"}, {"now": datetime(2026, 11, 16)},
    {"inventory_complete": 1}, {"windows": []}, {"live_state": "maybe"},
])
def test_bounded_preview_rejects_malformed_inputs(change):
    args = _preview_inputs()
    args.update(change)
    with pytest.raises(ValueError, match="bounded_preview:"):
        plan_bounded_unlisted_batch(**args)


def test_bounded_preview_conflicting_duplicate_fails_closed():
    args = _preview_inputs()
    other = dict(args["candidates"][0], held=True)
    args["candidates"].append(other)
    with pytest.raises(ValueError, match="candidate_conflict"):
        plan_bounded_unlisted_batch(**args)


@pytest.mark.parametrize("field,value,reason", [
    ("visibility", "private", "not_unlisted"),
    ("source_at", _at("2026-11-14T00:00:00+09:00"), "outside_source_window"),
    ("source_at", _at("2026-11-17T00:00:00+09:00"), "source_in_future"),
    ("evidence_ref", "", "content_evidence_missing"),
    ("topic", "", "content_evidence_missing"),
])
def test_bounded_preview_content_and_source_exclusions(field, value, reason):
    args = _preview_inputs()
    args["candidates"][0][field] = value
    result = plan_bounded_unlisted_batch(**args)
    assert {"video_id": "v0000000001", "reason": reason} in result["excluded"]


def test_bounded_preview_reserved_id_and_instant_collisions():
    args = _preview_inputs()
    args["occupied"] = [dict(channel_id=_CHANNEL, video_id="v0000000001",
                             publish_at=_at("2026-11-18T20:00:00+09:00"), status="unknown")]
    result = plan_bounded_unlisted_batch(**args)
    assert {"video_id": "v0000000001", "reason": "already_scheduled_or_reserved"} in result["excluded"]
    assert result["planned"][0]["publish_at_studio"] == "2026-11-19T00:19:00+09:00"


def test_bounded_preview_retains_daily_cap_across_midnight():
    args = _preview_inputs()
    args["max_per_day"] = 1
    args["occupied"] = [dict(channel_id=_CHANNEL, video_id="existing001",
                             publish_at=_at("2026-11-18T01:00:00+09:00"), status="scheduled")]
    result = plan_bounded_unlisted_batch(**args)
    dates = [r["publish_at_studio"][:10] for r in result["planned"]]
    assert "2026-11-18" not in dates
    assert len(dates) == len(set(dates)) == 2


def test_bounded_preview_dst_audience_conversion_is_date_specific():
    args = _preview_inputs()
    args["windows"] = [(_at("2026-10-31T20:00:00+09:00"), _at("2026-11-01T04:00:00+09:00")),
                       (_at("2026-11-02T20:00:00+09:00"), _at("2026-11-03T04:00:00+09:00"))]
    args["now"] = args["observed_at"] = _at("2026-10-30T12:00:00+09:00")
    args["source_start"] = _at("2026-10-29T00:00:00+09:00")
    args["source_end"] = _at("2026-10-31T00:00:00+09:00")
    for row in args["candidates"]:
        row["source_at"] = _at("2026-10-30T11:00:00+09:00")
    result = plan_bounded_unlisted_batch(**args)
    assert result["planned"][0]["publish_at_audience"].endswith("-04:00")
    assert result["planned"][-1]["publish_at_audience"].endswith("-05:00")


def test_bounded_preview_unordered_windows_rejected():
    args = _preview_inputs()
    args["windows"].reverse()
    with pytest.raises(ValueError, match="window_bounds_invalid"):
        plan_bounded_unlisted_batch(**args)


@pytest.mark.parametrize("mutation", ["foreign", "bad_boolean", "missing_field", "unknown_field"])
def test_bounded_preview_candidate_schema_and_scope_fail_closed(mutation):
    args = _preview_inputs()
    row = args["candidates"][0]
    if mutation == "foreign":
        row["channel_id"] = "UC" + "b" * 22
    elif mutation == "bad_boolean":
        row["content_verified"] = 1
    elif mutation == "missing_field":
        del row["held"]
    else:
        row["title"] = "A title is not evidence"
    with pytest.raises(ValueError, match="bounded_preview:candidate_"):
        plan_bounded_unlisted_batch(**args)


def test_bounded_preview_occupied_conflict_and_missing_instant_refused():
    args = _preview_inputs()
    row = dict(channel_id=_CHANNEL, video_id="existing001",
               publish_at=_at("2026-11-18T01:00:00+09:00"), status="reserved")
    args["occupied"] = [row, dict(row, publish_at=_at("2026-11-18T02:00:00+09:00"))]
    with pytest.raises(ValueError, match="occupied_conflict"):
        plan_bounded_unlisted_batch(**args)
    args["occupied"] = [dict(row, publish_at=None)]
    with pytest.raises(ValueError, match="aware_datetime_required"):
        plan_bounded_unlisted_batch(**args)


def test_bounded_preview_empty_authorization_and_zero_cap_do_not_plan():
    args = _preview_inputs()
    args["allowed_video_ids"] = []
    result = plan_bounded_unlisted_batch(**args)
    assert not result["planned"]
    assert {r["reason"] for r in result["excluded"]} == {"outside_allowed_ids"}
    args = _preview_inputs()
    result = plan_bounded_unlisted_batch(**args, max_per_day=0)
    assert not result["planned"] and len(result["unplaced"]) == 4
    assert plan_bounded_unlisted_batch(**args, max_per_day=100)["daily_cap"] == HARD_CAP_PER_DAY


def test_bounded_preview_rejects_dst_fold_wall_window():
    args = _preview_inputs()
    args["timezone"] = "America/New_York"
    args["now"] = args["observed_at"] = _at("2026-10-30T12:00:00+00:00")
    args["windows"] = [(_at("2026-11-01T01:00:00-04:00"), _at("2026-11-01T04:00:00-05:00"))]
    with pytest.raises(ValueError, match="window_wall_time_ambiguous"):
        plan_bounded_unlisted_batch(**args)


def test_bounded_preview_skips_fold_candidates_and_keeps_elapsed_spacing():
    args = _preview_inputs()
    args["timezone"] = "America/New_York"
    args["now"] = args["observed_at"] = _at("2026-10-30T12:00:00+00:00")
    args["source_start"] = _at("2026-10-29T00:00:00+00:00")
    args["source_end"] = _at("2026-10-31T00:00:00+00:00")
    for row in args["candidates"]:
        row["source_at"] = _at("2026-10-30T11:00:00+00:00")
    args["windows"] = [(_at("2026-10-31T21:00:00-04:00"), _at("2026-11-01T07:00:00-05:00"))]
    result = plan_bounded_unlisted_batch(**args)
    assert len(result["planned"]) == 2  # 01:19 fold is deliberately not offered
    slots = [_at(r["publish_at_utc"]) for r in result["planned"]]
    assert (slots[1] - slots[0]).total_seconds() >= 240 * 60


def test_bounded_preview_has_no_file_network_or_reservation_effects(monkeypatch):
    import builtins
    import socket
    import pytz
    from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import ScheduleTracker
    # Load bundled timezone data before sealing effects, even in isolated runs.
    pytz.timezone(TOKYO_TZ)
    pytz.timezone(NY_TZ)
    def forbidden(*args, **kwargs):
        raise AssertionError("preview attempted external effect")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(ScheduleTracker, "reserve_slot", forbidden)
    monkeypatch.setattr(ScheduleTracker, "save", forbidden)
    assert plan_bounded_unlisted_batch(**_preview_inputs())["effects_disabled"]


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
