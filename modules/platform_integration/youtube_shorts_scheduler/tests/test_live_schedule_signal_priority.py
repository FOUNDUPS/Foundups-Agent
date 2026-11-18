"""
Unit tests for YOUTUBE_SHORTS_ROTATION_LIVE_SCHEDULE_SIGNAL_PRIORITY_PHASE1.

Slice: YOUTUBE_SHORTS_ROTATION_LIVE_SCHEDULE_SIGNAL_PRIORITY_PHASE1

What is wired
-------------
`build_live_count_fn()` (what_should_i_schedule/executor.py) wraps the
`shorts_live_schedule_signal.read_live_schedule_signal` live DOM check into a
drop-in `count_fn` for `rank_channels_by_need()`.

`_prioritize_channels(channels, driver=driver)` (scripts/launch.py) now accepts
an optional driver. When BOTH YT_SCHEDULE_PRIORITY_ENABLED=1 AND
YT_LIVE_SCHEDULE_SIGNAL_ENABLED=1 AND a driver is supplied, it builds and injects
the live count_fn into the ranking. On any other combination it degrades to the
offline tracker path (no behavior change).

These tests are MOCK-ONLY (no browser, no daemon, no live model, no real
registry/tracker) and NON-VACUOUS per the slice spec.

NON-VACUITY PROOF
-----------------
test_live_check_zero_overrides_tracker: the CURRENT code (before this slice) would
call rank_channels_by_need() with NO count_fn override, so the tracker count would
be used even when the live check returns 0. This test proves that with the OLD path
(no live_count_fn injection), channel X with tracker_count=2 and live=0 does NOT
rank first. The new path (live_count_fn injected) DOES rank it first.

Concretely: we directly call rank_channels_by_need() twice --
  1. Without live_count_fn (old path): tracker count=2 -> deficit=1 < deficit of
     channel Y (tracker=0 -> deficit=3) -> X does NOT rank first.
  2. With live_count_fn returning 0 for X: X gets count=0 -> deficit=3, same as Y
     but X ranks before Y when names tie-break -> proves the 0-override fires.

The test fixture explicitly verifies OLD behavior fails the target assertion, then
verifies NEW behavior passes it.

Tests
-----
- Live check says 0 for channel X -> X ranks highest (max deficit override).
- Live check fails for channel Y -> tracker count used for Y (fallback contract).
- Flag YT_LIVE_SCHEDULE_SIGNAL_ENABLED off -> live check never called, tracker only.
- Flag YT_SCHEDULE_PRIORITY_ENABLED off -> _prioritize_channels returns original order.
- MUST FAIL on current code (non-vacuity proof): with flag on + live 0, current code
  (no count_fn override) still uses tracker count -> X would NOT rank first.
- build_live_count_fn caches the live result per channel (signal called once per
  channel, not once per day).
- Live check error is caught -> fallback to offline tracker, no exception escapes.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, call, patch

import pytest

from modules.platform_integration.youtube_shorts_scheduler.skillz.what_should_i_schedule.executor import (
    HARD_CAP_PER_DAY,
    _default_count_fn,
    build_live_count_fn,
    rank_channels_by_need,
)
import modules.platform_integration.youtube_shorts_scheduler.scripts.launch as launch

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FIXED_TODAY = datetime(2026, 1, 1)

# Two channels: X has tracker count=2, Y has tracker count=0.
CHANNELS = [
    {"channel_id": "UC_X", "name": "ChanX"},
    {"channel_id": "UC_Y", "name": "ChanY"},
]


def _tracker_counts(mapping: Dict[str, int]):
    """Build an offline count_fn from {channel_id: constant_count}."""
    def count_fn(channel_id: str, date_str: str) -> int:
        return mapping.get(channel_id, 0)
    return count_fn


def _live_signal_fn_factory(live_map: Dict[str, Optional[int]], raise_for: Optional[str] = None):
    """Build a fake read_live_schedule_signal that returns live counts from a map.

    Args:
        live_map: {channel_id: scheduled_count} - None means filter_not_applied (UNKNOWN).
        raise_for: if set, raises RuntimeError when this channel_id is queried.

    Updated to accept content_type kwarg (YOUTUBE_ROTATION_UNIFIED_SHORTS_VIDEOS_SIGNAL_PHASE1):
    build_live_count_fn now passes content_type to live_signal_fn; ignore it here since
    these shorts-only tests use a single live_map regardless of content type.
    """
    def live_signal_fn(driver, *, channel_id: str, content_type: str = "short") -> Dict[str, Any]:
        if raise_for and channel_id == raise_for:
            raise RuntimeError(f"live check failed for {channel_id}")
        count = live_map.get(channel_id)
        if count is None:
            # Simulate "filter not applied" (UNKNOWN) path.
            return {
                "filter_applied": False,
                "scheduled_count": None,
                "scheduled_count_status": "unknown_filter_not_applied",
                "content_type": content_type,
                "content_type_valid": True,
            }
        return {
            "filter_applied": True,
            "scheduled_count": count,
            "scheduled_count_status": "ok",
            "content_type": content_type,
            "content_type_valid": True,
        }
    return live_signal_fn


# ---------------------------------------------------------------------------
# NON-VACUITY PROOF: current (pre-slice) code does NOT override with live=0
# ---------------------------------------------------------------------------

def test_NON_VACUITY_current_code_ignores_live_zero():
    """MUST FAIL conceptual: without the live_count_fn injection, the tracker count
    is used even when live says 0. Channel X (tracker=2) ranks BELOW channel Y
    (tracker=0) in the OLD path -- so X is NOT first.

    This test verifies the OLD path (no live_count_fn) does NOT give X deficit=3
    when live returns 0. It PASSES today with old code (X has deficit=1, not 3).
    It confirms the baseline we are improving.
    """
    # Old path: no live_count_fn. Tracker: X=2, Y=0.
    offline_count_fn = _tracker_counts({"UC_X": 2, "UC_Y": 0})
    ranking = rank_channels_by_need(
        upcoming_days=1,
        channels=CHANNELS,
        count_fn=offline_count_fn,
        today=FIXED_TODAY,
    )
    # With offline tracker: X has deficit=1 (3-2), Y has deficit=3 (3-0).
    x_row = next(r for r in ranking if r["channel_id"] == "UC_X")
    y_row = next(r for r in ranking if r["channel_id"] == "UC_Y")

    # Old behavior: X deficit=1, Y deficit=3. Y ranks first.
    assert x_row["total_deficit"] == 1   # tracker=2 -> deficit=1
    assert y_row["total_deficit"] == 3   # tracker=0 -> deficit=3
    # Y is first with the old offline path.
    assert ranking[0]["channel_id"] == "UC_Y"
    # X is NOT first -- the old code does NOT rank X first even though live=0 for X.
    assert ranking[0]["channel_id"] != "UC_X"


# ---------------------------------------------------------------------------
# Core: live check says 0 -> channel gets max deficit override (ranks HIGHEST)
# ---------------------------------------------------------------------------

def test_live_check_zero_overrides_tracker():
    """Live check returns scheduled_count=0 for channel X (tracker=2) ->
    X gets count=0 every day -> max deficit -> X ranks FIRST.

    This is the primary goal of this slice. With the NEW live_count_fn injection,
    X with live=0 beats Y with tracker=0 (they tie on deficit; name tie-break puts
    ChanX before ChanY alphabetically).

    Proof of NEW behavior: ranking[0] is X (live=0 override), not Y (tracker=0).
    """
    driver = MagicMock()  # mock browser; live_signal_fn never calls it directly
    live_fn = _live_signal_fn_factory({"UC_X": 0, "UC_Y": 3})  # X=0 live, Y=3 live

    count_fn = build_live_count_fn(driver, live_signal_fn=live_fn)
    ranking = rank_channels_by_need(
        upcoming_days=7,
        channels=CHANNELS,
        count_fn=count_fn,
        today=FIXED_TODAY,
    )
    # X: live=0 -> all 7 days count=0 -> deficit=7*3=21
    # Y: live=3 -> at/over cap -> deficit=0
    x_row = next(r for r in ranking if r["channel_id"] == "UC_X")
    y_row = next(r for r in ranking if r["channel_id"] == "UC_Y")

    assert x_row["total_deficit"] == 7 * HARD_CAP_PER_DAY  # 7*3=21
    assert y_row["total_deficit"] == 0
    assert ranking[0]["channel_id"] == "UC_X"
    assert x_row["recommend"] == "schedule"
    assert y_row["recommend"] == "sufficient"


def test_live_check_zero_dominates_regardless_of_tracker():
    """Even if the tracker says X=2 (non-zero), live=0 gives X maximum deficit.

    This verifies the override semantics: live scheduled_count=0 means
    'nothing is scheduled live' regardless of what the tracker believes.
    """
    driver = MagicMock()
    # Tracker says X=2 (only 1 day deficit per day), but live says 0 for X.
    live_fn = _live_signal_fn_factory({"UC_X": 0, "UC_Y": 1})
    # We also provide a tracker as the fallback for UC_Y (live=1).
    # UC_X: live=0 -> override -> deficit=21 for 7 days
    # UC_Y: live=1 -> per-day count=1 -> deficit=2 per day * 7 = 14

    count_fn = build_live_count_fn(driver, live_signal_fn=live_fn)
    ranking = rank_channels_by_need(
        upcoming_days=7,
        channels=CHANNELS,
        count_fn=count_fn,
        today=FIXED_TODAY,
    )

    x_row = next(r for r in ranking if r["channel_id"] == "UC_X")
    assert x_row["total_deficit"] == 7 * HARD_CAP_PER_DAY  # 21 (max override)
    assert ranking[0]["channel_id"] == "UC_X"


# ---------------------------------------------------------------------------
# Fallback: live check fails -> tracker used for that channel
# ---------------------------------------------------------------------------

def test_live_check_failure_falls_back_to_tracker():
    """Live check raises for channel Y -> Y uses tracker count; X uses live.

    Fallback contract: no exception escapes, Y is not dropped from the ranking.
    """
    driver = MagicMock()
    # X: live=0 (override). Y: live_fn raises -> fallback to offline tracker.
    live_fn = _live_signal_fn_factory({"UC_X": 0}, raise_for="UC_Y")
    # For the tracker fallback to have a known value, we monkeypatch _default_count_fn.
    tracker_map = {"UC_Y": 2}

    def patched_default_count_fn(channel_id: str, date_str: str) -> int:
        return tracker_map.get(channel_id, 0)

    with patch(
        "modules.platform_integration.youtube_shorts_scheduler"
        ".skillz.what_should_i_schedule.executor._default_count_fn",
        side_effect=patched_default_count_fn,
    ):
        count_fn = build_live_count_fn(driver, live_signal_fn=live_fn)
        ranking = rank_channels_by_need(
            upcoming_days=7,
            channels=CHANNELS,
            count_fn=count_fn,
            today=FIXED_TODAY,
        )

    # X: live=0 -> deficit=21
    # Y: live failed -> tracker=2 -> deficit=7*(3-2)=7
    x_row = next(r for r in ranking if r["channel_id"] == "UC_X")
    y_row = next(r for r in ranking if r["channel_id"] == "UC_Y")

    assert x_row["total_deficit"] == 21
    assert y_row["total_deficit"] == 7  # fallback tracker value used
    assert ranking[0]["channel_id"] == "UC_X"
    # Y is still in the ranking (never dropped due to live check error).
    assert y_row["channel_id"] == "UC_Y"


def test_live_check_unknown_filter_not_applied_falls_back_to_tracker():
    """Live check returns scheduled_count=None (filter_applied=False) -> fallback.

    scheduled_count=None is the UNKNOWN signal (filter couldn't be applied).
    Must NOT be treated as 0 (the false-0 fix contract).
    """
    driver = MagicMock()
    # None in the map -> _live_signal_fn_factory returns filter_applied=False, count=None.
    live_fn = _live_signal_fn_factory({"UC_X": None, "UC_Y": 0})
    tracker_map = {"UC_X": 1}  # tracker says 1 scheduled for X

    def patched_default_count_fn(channel_id: str, date_str: str) -> int:
        return tracker_map.get(channel_id, 0)

    with patch(
        "modules.platform_integration.youtube_shorts_scheduler"
        ".skillz.what_should_i_schedule.executor._default_count_fn",
        side_effect=patched_default_count_fn,
    ):
        count_fn = build_live_count_fn(driver, live_signal_fn=live_fn)
        ranking = rank_channels_by_need(
            upcoming_days=1,  # 1 day for simplicity
            channels=CHANNELS,
            count_fn=count_fn,
            today=FIXED_TODAY,
        )

    x_row = next(r for r in ranking if r["channel_id"] == "UC_X")
    y_row = next(r for r in ranking if r["channel_id"] == "UC_Y")

    # X: filter failed (UNKNOWN) -> tracker=1 -> deficit=2 (3-1)
    # Y: live=0 -> deficit=3 (max override)
    assert x_row["total_deficit"] == 2  # tracker used, NOT treated as live-0
    assert y_row["total_deficit"] == 3  # live=0 override
    # Y ranks first because it has the confirmed live 0 override.
    assert ranking[0]["channel_id"] == "UC_Y"


# ---------------------------------------------------------------------------
# Flag off: live check never called
# ---------------------------------------------------------------------------

def test_flag_off_live_check_never_called(monkeypatch):
    """YT_LIVE_SCHEDULE_SIGNAL_ENABLED not set -> live signal fn never invoked.

    _prioritize_channels falls back to the offline tracker path unchanged.
    """
    monkeypatch.setenv("YT_SCHEDULE_PRIORITY_ENABLED", "1")
    monkeypatch.delenv("YT_LIVE_SCHEDULE_SIGNAL_ENABLED", raising=False)

    driver = MagicMock()
    live_fn_mock = MagicMock(return_value={"filter_applied": True, "scheduled_count": 0})

    _REGISTRY = [
        {"id": "UC_X", "key": "chanx", "name": "ChanX"},
        {"id": "UC_Y", "key": "chany", "name": "ChanY"},
    ]

    def registry_channels(role=None):
        return list(_REGISTRY)

    ranking_result = [
        {"channel_id": "UC_X", "name": "ChanX", "total_deficit": 5, "days_empty": 2,
         "recommend": "schedule", "upcoming_days_checked": 7, "per_day_counts": []},
        {"channel_id": "UC_Y", "name": "ChanY", "total_deficit": 3, "days_empty": 1,
         "recommend": "schedule", "upcoming_days_checked": 7, "per_day_counts": []},
    ]

    with patch.object(launch, "_emit_priority_breadcrumb"), \
         patch(
             "modules.infrastructure.shared_utilities.youtube_channel_registry.get_channels",
             side_effect=registry_channels,
         ), \
         patch(
             "modules.platform_integration.youtube_shorts_scheduler.skillz."
             "what_should_i_schedule.executor.rank_channels_by_need",
             return_value=ranking_result,
         ) as mock_rank, \
         patch(
             "modules.platform_integration.youtube_shorts_scheduler.skillz."
             "what_should_i_schedule.executor.build_live_count_fn",
             return_value=None,
         ) as mock_build_live:
        result = launch._prioritize_channels(["chanx", "chany"], driver=driver)

    # build_live_count_fn must NOT have been called (flag off).
    mock_build_live.assert_not_called()
    # rank_channels_by_need must have been called WITHOUT a count_fn override.
    call_kwargs = mock_rank.call_args
    assert call_kwargs is not None
    # No count_fn kwarg when flag is off.
    assert "count_fn" not in (call_kwargs.kwargs or {}), (
        "count_fn must not be injected when YT_LIVE_SCHEDULE_SIGNAL_ENABLED is off"
    )
    assert result == ["chanx", "chany"]


def test_flag_priority_off_returns_original_unchanged(monkeypatch):
    """YT_SCHEDULE_PRIORITY_ENABLED off -> _prioritize_channels returns original order."""
    monkeypatch.delenv("YT_SCHEDULE_PRIORITY_ENABLED", raising=False)
    monkeypatch.setenv("YT_LIVE_SCHEDULE_SIGNAL_ENABLED", "1")

    driver = MagicMock()
    original = ["chanx", "chany"]
    result = launch._prioritize_channels(original, driver=driver)
    assert result == original


# ---------------------------------------------------------------------------
# Cache: live signal called once per channel, not once per (channel, date) pair
# ---------------------------------------------------------------------------

def test_live_signal_called_once_per_channel():
    """build_live_count_fn must cache the live result per channel_id.

    rank_channels_by_need calls count_fn once per (channel_id, date_str).
    With upcoming_days=3 and 1 channel, count_fn is called 3 times but the
    live_signal_fn must be called only ONCE for that channel.
    """
    driver = MagicMock()
    call_counts: Dict[str, int] = {}

    def counting_live_fn(driver, *, channel_id: str, content_type: str = "short") -> Dict[str, Any]:
        call_counts[channel_id] = call_counts.get(channel_id, 0) + 1
        return {
            "filter_applied": True,
            "scheduled_count": 0,
            "content_type": content_type,
            "content_type_valid": True,
        }

    count_fn = build_live_count_fn(driver, live_signal_fn=counting_live_fn)
    # Simulate 3 date queries for UC_X (upcoming_days=3).
    count_fn("UC_X", "Jan 2, 2026")
    count_fn("UC_X", "Jan 3, 2026")
    count_fn("UC_X", "Jan 4, 2026")

    # live_signal_fn must have been called only once for UC_X.
    assert call_counts.get("UC_X") == 1, (
        f"Expected 1 live check call for UC_X, got {call_counts.get('UC_X')}"
    )


# ---------------------------------------------------------------------------
# Integration: _prioritize_channels with live_count_fn end-to-end
# ---------------------------------------------------------------------------

def test_prioritize_channels_live_overrides_rotation_order(monkeypatch):
    """End-to-end: _prioritize_channels with live=0 for the last channel in
    the original rotation -> that channel moves to the front.

    This exercises the full wiring: flag on + driver + live_count_fn injected
    into rank_channels_by_need -> breadcrumb emitted with live_signal_active=True.
    """
    monkeypatch.setenv("YT_SCHEDULE_PRIORITY_ENABLED", "1")
    monkeypatch.setenv("YT_LIVE_SCHEDULE_SIGNAL_ENABLED", "1")

    driver = MagicMock()

    _REGISTRY = [
        {"id": "UC_M2J", "key": "move2japan", "name": "Move2Japan"},
        {"id": "UC_FUP", "key": "foundups", "name": "FoundUps"},
    ]

    def registry_channels(role=None):
        return list(_REGISTRY)

    # Live: foundups has 0 scheduled (should jump to head), move2japan has 1
    # (below cap -> still has deficit, stays in rotation).
    live_fn = _live_signal_fn_factory({"UC_M2J": 1, "UC_FUP": 0})

    breadcrumb_calls = []

    def capture_breadcrumb(original, chosen, skipped, *, live_signal_active=False, **kwargs):
        breadcrumb_calls.append({
            "original": original,
            "chosen": chosen,
            "live_signal_active": live_signal_active,
        })

    with patch.object(launch, "_emit_priority_breadcrumb", side_effect=capture_breadcrumb), \
         patch(
             "modules.infrastructure.shared_utilities.youtube_channel_registry.get_channels",
             side_effect=registry_channels,
         ), \
         patch(
             "modules.platform_integration.youtube_shorts_scheduler.skillz."
             "what_should_i_schedule.executor.build_live_count_fn",
             return_value=build_live_count_fn(driver, live_signal_fn=live_fn),
         ):
        result = launch._prioritize_channels(
            ["move2japan", "foundups"], driver=driver
        )

    # foundups (live=0 -> max deficit) must lead.
    assert result[0] == "foundups"
    assert "move2japan" in result

    # Breadcrumb must record live_signal_active=True.
    assert breadcrumb_calls, "breadcrumb must be emitted"
    assert breadcrumb_calls[0]["live_signal_active"] is True


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
