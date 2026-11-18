"""
Unit tests for the what_should_i_schedule SKILLz (channel scheduling-priority).

Slice: WHAT_SHOULD_I_SCHEDULE_SKILLZ_PHASE1

Model under test
----------------
Given the persisted per-channel schedule tracker (date -> count), rank the
shorts-enabled channels by scheduling NEED:
  per-day deficit = max(0, HARD_CAP_PER_DAY - count)
  total_deficit   = sum over the next N upcoming days
An empty-schedule channel ranks HIGHEST; a channel full at the cap every day ranks
LOWEST with recommend="sufficient".

These tests are mock-only (no browser, no daemon, no live models) and NON-VACUOUS:
  - empty channel ranks first, cap-full channel ranks last (sufficient)
  - deficit math is exact
  - breadcrumb + PatternMemory emission are invoked (mocked + asserted)
  - the ranking MUST respond to the injected counts (a counts-ignoring impl fails):
    equal counts => equal deficits, and swapping which channel is empty swaps the top.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from modules.platform_integration.youtube_shorts_scheduler.skillz.what_should_i_schedule.executor import (
    HARD_CAP_PER_DAY,
    compute_channel_need,
    rank_channels_by_need,
    run_skill,
)

# Deterministic clock so upcoming-date strings are stable across runs.
FIXED_TODAY = datetime(2026, 1, 1)

CHANNELS = [
    {"channel_id": "UC_EMPTY", "name": "EmptyChan"},
    {"channel_id": "UC_FULL", "name": "FullChan"},
    {"channel_id": "UC_PARTIAL", "name": "PartialChan"},
]


def _counts_source(mapping):
    """Build a count_fn from {channel_id: per_date_count} (constant per channel)."""

    def count_fn(channel_id, date_str):
        return mapping.get(channel_id, 0)

    return count_fn


def test_hard_cap_is_three():
    """Pin the load-bearing cap (HARD_CAP_PER_DAY=3, landed #844)."""
    assert HARD_CAP_PER_DAY == 3


def test_empty_channel_ranks_highest():
    """A channel with an empty upcoming schedule must rank first."""
    count_fn = _counts_source({"UC_EMPTY": 0, "UC_FULL": 3, "UC_PARTIAL": 2})
    ranking = rank_channels_by_need(
        upcoming_days=7,
        channels=CHANNELS,
        count_fn=count_fn,
        today=FIXED_TODAY,
    )
    assert ranking[0]["channel_id"] == "UC_EMPTY"
    assert ranking[0]["recommend"] == "schedule"
    assert ranking[0]["days_empty"] == 7
    # Empty channel: 7 days * (3 - 0) = 21 deficit.
    assert ranking[0]["total_deficit"] == 21


def test_full_channel_ranks_lowest_and_sufficient():
    """A channel full at the cap every day ranks last with recommend=sufficient."""
    count_fn = _counts_source({"UC_EMPTY": 0, "UC_FULL": 3, "UC_PARTIAL": 2})
    ranking = rank_channels_by_need(
        upcoming_days=7,
        channels=CHANNELS,
        count_fn=count_fn,
        today=FIXED_TODAY,
    )
    last = ranking[-1]
    assert last["channel_id"] == "UC_FULL"
    assert last["total_deficit"] == 0
    assert last["recommend"] == "sufficient"
    assert last["days_empty"] == 0


def test_deficit_math_is_exact():
    """Partial channel deficit = N * (cap - count); verify exact arithmetic."""
    need = compute_channel_need(
        "UC_PARTIAL",
        "PartialChan",
        upcoming_days=5,
        count_fn=_counts_source({"UC_PARTIAL": 2}),
        today=FIXED_TODAY,
    )
    # 5 days * (3 - 2) = 5
    assert need.total_deficit == 5
    assert need.upcoming_days_checked == 5
    assert need.days_empty == 0
    assert need.recommend == "schedule"
    assert need.per_day_counts == [2, 2, 2, 2, 2]


def test_over_cap_count_never_negative_deficit():
    """A day already at/over the cap contributes zero (never negative) deficit."""
    need = compute_channel_need(
        "UC_OVER",
        "OverChan",
        upcoming_days=4,
        count_fn=_counts_source({"UC_OVER": 5}),  # > cap
        today=FIXED_TODAY,
    )
    assert need.total_deficit == 0
    assert need.recommend == "sufficient"


def test_full_ordering_is_by_deficit():
    """Mixed counts: order must be empty > partial > full (deficit-driven)."""
    count_fn = _counts_source({"UC_EMPTY": 0, "UC_FULL": 3, "UC_PARTIAL": 2})
    ranking = rank_channels_by_need(
        upcoming_days=7,
        channels=CHANNELS,
        count_fn=count_fn,
        today=FIXED_TODAY,
    )
    order = [r["channel_id"] for r in ranking]
    assert order == ["UC_EMPTY", "UC_PARTIAL", "UC_FULL"]


# --- Non-vacuity guards: the ranking MUST depend on the counts ---------------

def test_ranking_responds_to_counts_not_static():
    """Swapping which channel is empty swaps the top — proves counts drive the rank.

    A buggy impl that ignored counts (e.g. returned registry order or all-equal)
    would keep the SAME top regardless of the data; this asserts the top FLIPS.
    """
    rank_a = rank_channels_by_need(
        upcoming_days=7,
        channels=CHANNELS,
        count_fn=_counts_source({"UC_EMPTY": 0, "UC_FULL": 3, "UC_PARTIAL": 3}),
        today=FIXED_TODAY,
    )
    rank_b = rank_channels_by_need(
        upcoming_days=7,
        channels=CHANNELS,
        # Now UC_FULL is the empty one instead.
        count_fn=_counts_source({"UC_EMPTY": 3, "UC_FULL": 0, "UC_PARTIAL": 3}),
        today=FIXED_TODAY,
    )
    assert rank_a[0]["channel_id"] == "UC_EMPTY"
    assert rank_b[0]["channel_id"] == "UC_FULL"
    assert rank_a[0]["channel_id"] != rank_b[0]["channel_id"]


def test_equal_counts_yield_equal_deficits():
    """Injecting EQUAL counts for all channels => EQUAL deficits (counts honored).

    If the impl fabricated deficits independent of counts, these would differ.
    """
    equal = _counts_source({"UC_EMPTY": 1, "UC_FULL": 1, "UC_PARTIAL": 1})
    ranking = rank_channels_by_need(
        upcoming_days=6,
        channels=CHANNELS,
        count_fn=equal,
        today=FIXED_TODAY,
    )
    deficits = {r["total_deficit"] for r in ranking}
    assert deficits == {6 * (HARD_CAP_PER_DAY - 1)}  # all equal: 6 * 2 = 12


def test_custom_deficit_formula_seam():
    """The need formula is a swappable seam (deficit_fn)."""
    # A flat 'each under-cap day counts 1' formula instead of (cap - count).
    flat = lambda count, cap: 1 if count < cap else 0
    need = compute_channel_need(
        "UC_EMPTY",
        "EmptyChan",
        upcoming_days=7,
        count_fn=_counts_source({"UC_EMPTY": 0}),
        deficit_fn=flat,
        today=FIXED_TODAY,
    )
    assert need.total_deficit == 7  # flat: 7 under-cap days * 1


# --- Signal emission: breadcrumb + PatternMemory must be invoked -------------

def test_run_skill_emits_breadcrumb_and_pattern_memory():
    """run_skill must emit a schedule_priority breadcrumb AND a SkillOutcome."""
    count_fn = _counts_source({"UC_EMPTY": 0, "UC_FULL": 3, "UC_PARTIAL": 2})

    # The telemetry + pattern-memory symbols are imported lazily inside the
    # executor's emit helpers, so patch them at their source modules.
    with patch(
        "modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry"
    ) as bc, patch(
        "modules.infrastructure.wre_core.src.pattern_memory.PatternMemory"
    ) as pm, patch(
        "modules.infrastructure.wre_core.src.pattern_memory.SkillOutcome"
    ) as outcome:
        result = run_skill(
            upcoming_days=7,
            channels=CHANNELS,
            count_fn=count_fn,
            today=FIXED_TODAY,
            emit_signals=True,
        )

        # Breadcrumb stored with the schedule_priority event type.
        bc.return_value.store_breadcrumb.assert_called_once()
        kwargs = bc.return_value.store_breadcrumb.call_args.kwargs
        assert kwargs["event_type"] == "schedule_priority"
        assert kwargs["source_dae"] == "youtube_shorts_scheduler"
        assert "ranking" in kwargs["metadata"]

        # PatternMemory outcome stored.
        pm.return_value.store_outcome.assert_called_once()
        outcome.assert_called_once()

    assert result["success"] is True
    assert result["breadcrumb_emitted"] is True
    assert result["outcome_stored"] is True
    assert result["recommended_channel"]["channel_id"] == "UC_EMPTY"


def test_run_skill_no_signals_skips_emission():
    """emit_signals=False must NOT emit breadcrumb/outcome (diagnostic path)."""
    count_fn = _counts_source({"UC_EMPTY": 0})
    with patch(
        "modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry"
    ) as bc, patch(
        "modules.infrastructure.wre_core.src.pattern_memory.PatternMemory"
    ) as pm:
        result = run_skill(
            upcoming_days=3,
            channels=[{"channel_id": "UC_EMPTY", "name": "EmptyChan"}],
            count_fn=count_fn,
            today=FIXED_TODAY,
            emit_signals=False,
        )
        bc.return_value.store_breadcrumb.assert_not_called()
        pm.return_value.store_outcome.assert_not_called()
    assert result["breadcrumb_emitted"] is False
    assert result["outcome_stored"] is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
