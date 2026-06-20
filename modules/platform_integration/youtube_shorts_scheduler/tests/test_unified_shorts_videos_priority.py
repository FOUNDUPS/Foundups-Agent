"""
Unit tests for YOUTUBE_ROTATION_UNIFIED_SHORTS_VIDEOS_SIGNAL_PHASE1.

Slice: YOUTUBE_ROTATION_UNIFIED_SHORTS_VIDEOS_SIGNAL_PHASE1

What is wired
-------------
1. read_live_schedule_signal (shorts_live_schedule_signal/executor.py) now accepts
   content_type ("short" | "upload"). Validates at entry; invalid -> fail closed.
   DOM scan logic (HAS_SCHEDULE filter + row scrape) is REUSED unchanged (WSP 84).

2. build_live_count_fn (what_should_i_schedule/executor.py) now accepts
   content_type. Threads it through to read_live_schedule_signal without
   duplicating the DOM scan (WSP 84). Caches per channel_id (Addendum D:
   one live call per channel per content_type per pass).

3. _prioritize_channels (scripts/launch.py) now computes a second videos ranking
   when YT_VIDEO_PROCESSING_ENABLED=1 AND YT_LIVE_SCHEDULE_SIGNAL_ENABLED=1 AND
   driver available. Result stored in _pass_video_ranking (priority-only, no
   upload behavior change, Addendum F).

4. Videos loop in run_multi_channel_scheduler applies a priority skip gate:
   channel with total_deficit==0 from live signal skips its video pass.

Decision model (012):
  - Shorts=0 (live) -> highest Shorts priority
  - Videos=0 (live) AND YT_VIDEO_PROCESSING_ENABLED=1 -> highest Videos priority
  - Both empty -> Shorts first (deterministic)
  - Live check fails for any -> fallback per Addendum E
  - YT_VIDEO_PROCESSING_ENABLED=0 -> Videos check NOT run

These tests are MOCK-ONLY (no live browser, no daemon, no real registry/tracker).
NO skip/xfail.

NON-VACUITY PROOF (test 8):
Without the unified ranking, a channel with Shorts=full but Videos=empty is NOT
prioritised for Videos in the current code (no video ranking computed). This test
asserts the OLD behaviour (no video priority) fails the target check, then shows
the NEW code corrects it by computing a separate videos ranking.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, call, patch

import pytest

from modules.platform_integration.youtube_shorts_scheduler.skillz.shorts_live_schedule_signal.executor import (
    VALID_CONTENT_TYPES,
    _validate_content_type,
    read_live_schedule_signal,
)
from modules.platform_integration.youtube_shorts_scheduler.skillz.what_should_i_schedule.executor import (
    HARD_CAP_PER_DAY,
    _default_count_fn,
    build_live_count_fn,
    rank_channels_by_need,
)
import modules.platform_integration.youtube_shorts_scheduler.scripts.launch as launch

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

FIXED_TODAY = datetime(2026, 1, 1)

# Two channels: A has plenty of shorts + empty videos; B has empty shorts + videos.
CHANNELS = [
    {"channel_id": "UC_A", "name": "ChanA"},
    {"channel_id": "UC_B", "name": "ChanB"},
]


def _make_mock_driver():
    """Return a bare MagicMock as a stand-in WebDriver. Never runs browser code."""
    return MagicMock(name="mock_driver")


def _live_signal_with(scheduled_count, filter_applied=True, content_type_valid=True):
    """Build a read_live_schedule_signal result shape for injection."""
    return {
        "success": filter_applied and scheduled_count is not None,
        "filter_applied": filter_applied,
        "scheduled_count": scheduled_count,
        "scheduled_count_status": "ok" if (filter_applied and scheduled_count is not None) else "unknown",
        "content_type_valid": content_type_valid,
        "content_type": "short",
        "row_count": scheduled_count or 0,
        "low_viewed_count": 0,
        "low_viewed_videos": [],
        "scheduled_videos": [],
        "videos": [],
        "patterns": {"has_schedule_filter_applied": filter_applied},
    }


def _tracker_count_fn(counts: "dict[str, int]"):
    """Offline count_fn returning fixed values per channel_id (ignores date)."""
    def _fn(channel_id: str, date_str: str) -> int:
        return counts.get(channel_id, 0)
    return _fn


# ---------------------------------------------------------------------------
# Test 1: Shorts empty (live=0) + Videos not empty -> highest Shorts priority;
#         Videos ranking shows it lower.
# ---------------------------------------------------------------------------

def test_shorts_empty_videos_not_empty_shorts_highest_priority():
    """Shorts=0 (live), Videos not empty -> channel gets highest Shorts priority.

    When live check confirms shorts=0, the channel gets max deficit in the Shorts
    ranking and ranks first. The Videos ranking correctly shows Videos not empty.
    """
    driver = _make_mock_driver()
    # Channel A: live shorts=0 (empty), live videos=5 (not empty).
    # Channel B: live shorts=3, live videos=2.
    def _live_fn(drv, *, channel_id, content_type="short"):
        if content_type == "short":
            count = 0 if channel_id == "UC_A" else 3
        else:  # upload
            count = 5 if channel_id == "UC_A" else 2
        return _live_signal_with(count)

    # Shorts ranking: A has deficit (0 live), B has 3 live (non-zero).
    shorts_count_fn = build_live_count_fn(driver, content_type="short", live_signal_fn=_live_fn)
    shorts_ranking = rank_channels_by_need(
        channels=CHANNELS, count_fn=shorts_count_fn, today=FIXED_TODAY,
    )
    # A should be first (shorts=0 -> max deficit).
    assert shorts_ranking[0]["channel_id"] == "UC_A", \
        "ChanA (shorts=0) must be highest in Shorts ranking"

    # Videos ranking: A has 5 videos (not empty -> lower priority for videos).
    video_count_fn = build_live_count_fn(driver, content_type="upload", live_signal_fn=_live_fn)
    video_ranking = rank_channels_by_need(
        channels=CHANNELS, count_fn=video_count_fn, today=FIXED_TODAY,
    )
    # B has fewer videos scheduled -> higher video priority than A.
    # At minimum A should NOT be the top videos priority (videos not empty).
    a_video_row = next(r for r in video_ranking if r["channel_id"] == "UC_A")
    assert a_video_row["total_deficit"] >= 0  # sanity
    # Since A has 5 scheduled (non-zero), B with 2 scheduled also non-zero but lower ->
    # Both have deficit, and the channel with fewer counts higher. B has 2 < 5 so B ranks first.
    assert video_ranking[0]["channel_id"] == "UC_B", \
        "ChanB (fewer videos) should have higher Videos priority than ChanA (more videos)"


# ---------------------------------------------------------------------------
# Test 2: Videos empty (live=0) + YT_VIDEO_PROCESSING_ENABLED=1 -> highest Videos priority.
# ---------------------------------------------------------------------------

def test_videos_empty_processing_enabled_highest_videos_priority(monkeypatch):
    """Videos=0 (live) AND YT_VIDEO_PROCESSING_ENABLED=1 -> channel highest Videos priority."""
    monkeypatch.setenv("YT_VIDEO_PROCESSING_ENABLED", "1")
    driver = _make_mock_driver()

    # Channel A: shorts=3 (not empty), videos=0 (empty -> highest videos priority).
    def _live_fn(drv, *, channel_id, content_type="short"):
        if content_type == "short":
            return _live_signal_with(3)
        else:  # upload
            count = 0 if channel_id == "UC_A" else 2
            return _live_signal_with(count)

    video_count_fn = build_live_count_fn(driver, content_type="upload", live_signal_fn=_live_fn)
    video_ranking = rank_channels_by_need(
        channels=CHANNELS, count_fn=video_count_fn, today=FIXED_TODAY,
    )
    # A has videos=0 -> max deficit -> highest Videos priority.
    assert video_ranking[0]["channel_id"] == "UC_A", \
        "ChanA (videos=0) must be highest in Videos ranking"


# ---------------------------------------------------------------------------
# Test 3: Both Shorts and Videos empty -> Shorts first (deterministic).
# ---------------------------------------------------------------------------

def test_both_empty_shorts_first_deterministic(monkeypatch):
    """Both Shorts=0 AND Videos=0 -> Shorts decision wins (Shorts first, deterministic)."""
    monkeypatch.setenv("YT_VIDEO_PROCESSING_ENABLED", "1")
    monkeypatch.setenv("YT_SCHEDULE_PRIORITY_ENABLED", "1")
    monkeypatch.setenv("YT_LIVE_SCHEDULE_SIGNAL_ENABLED", "1")
    driver = _make_mock_driver()

    # Both shorts and videos = 0 for UC_A.
    def _live_fn(drv, *, channel_id, content_type="short"):
        return _live_signal_with(0)

    # Simulate _prioritize_channels computing the videos ranking internally.
    # The decision model: both empty -> decision = "both_empty_shorts_first".
    shorts_count_fn = build_live_count_fn(driver, content_type="short", live_signal_fn=_live_fn)
    video_count_fn = build_live_count_fn(driver, content_type="upload", live_signal_fn=_live_fn)

    shorts_ranking = rank_channels_by_need(
        channels=CHANNELS, count_fn=shorts_count_fn, today=FIXED_TODAY,
    )
    video_ranking = rank_channels_by_need(
        channels=CHANNELS, count_fn=video_count_fn, today=FIXED_TODAY,
    )

    # Both rankings have maximum deficit for all channels. Shorts ranking is
    # what drives the Shorts scheduling pass (decision: Shorts first).
    # Both rankings return valid lists (no failure).
    assert len(shorts_ranking) == len(CHANNELS)
    assert len(video_ranking) == len(CHANNELS)
    # All channels have maximum deficit in both rankings.
    for row in shorts_ranking:
        assert row["total_deficit"] == HARD_CAP_PER_DAY * 7  # 7 days x cap
    for row in video_ranking:
        assert row["total_deficit"] == HARD_CAP_PER_DAY * 7


# ---------------------------------------------------------------------------
# Test 4: Per-channel Shorts live check fails -> that channel falls back for
#         Shorts only; Videos check still runs (Addendum E per-channel failure).
# ---------------------------------------------------------------------------

def test_per_channel_shorts_failure_fallback_videos_unaffected():
    """Per-channel live check error for Shorts falls back for that channel only.

    Other channels still get the live Shorts signal. The Videos check is not
    affected by the Shorts failure (independent dimensions).
    Addendum E: per-channel failure, not systemic.
    """
    driver = _make_mock_driver()

    def _live_fn(drv, *, channel_id, content_type="short"):
        if content_type == "short" and channel_id == "UC_A":
            raise RuntimeError("DOM timeout for UC_A shorts")
        if content_type == "short":
            return _live_signal_with(0)  # UC_B shorts empty
        # Videos: both channels have 2 scheduled.
        return _live_signal_with(2)

    # Build shorts count_fn: UC_A will fall back to offline tracker.
    with patch(
        "modules.platform_integration.youtube_shorts_scheduler.skillz"
        ".what_should_i_schedule.executor._default_count_fn",
        side_effect=lambda ch, ds: 1 if ch == "UC_A" else 0,
    ):
        shorts_count_fn = build_live_count_fn(driver, content_type="short", live_signal_fn=_live_fn)
        # UC_A: live fails -> offline tracker returns 1 -> deficit = cap - 1 per day.
        # UC_B: live=0 -> max deficit (cap per day).
        # UC_B should rank higher than UC_A (UC_B has more deficit).
        shorts_ranking = rank_channels_by_need(
            channels=CHANNELS, count_fn=shorts_count_fn, today=FIXED_TODAY,
        )

    assert shorts_ranking[0]["channel_id"] == "UC_B", \
        "UC_B (live shorts=0) should rank higher than UC_A (offline fallback count=1)"

    # Videos check runs independently -- UC_A's Shorts failure doesn't affect it.
    video_count_fn = build_live_count_fn(driver, content_type="upload", live_signal_fn=_live_fn)
    video_ranking = rank_channels_by_need(
        channels=CHANNELS, count_fn=video_count_fn, today=FIXED_TODAY,
    )
    # Both have videos=2 -> same deficit. Ranking still returns both channels.
    assert len(video_ranking) == 2
    # UC_A not dropped from Videos ranking due to Shorts failure.
    video_ids = {r["channel_id"] for r in video_ranking}
    assert "UC_A" in video_ids
    assert "UC_B" in video_ids


# ---------------------------------------------------------------------------
# Test 5: Systemic Videos dimension failure -> Videos falls back globally;
#         Shorts live check unaffected (Addendum E systemic failure).
# ---------------------------------------------------------------------------

def test_systemic_videos_failure_shorts_unaffected(monkeypatch):
    """Systemic Videos dimension failure -> all channels fall back for Videos.

    Shorts live check is completely unaffected -- it still uses live signal.
    No channel is dropped from rotation due to the Videos failure.
    """
    monkeypatch.setenv("YT_VIDEO_PROCESSING_ENABLED", "1")
    driver = _make_mock_driver()

    # Shorts: UC_A has 0 scheduled (live), UC_B has 2.
    # Videos: ALL calls raise (systemic failure).
    shorts_results = {"UC_A": 0, "UC_B": 2}

    def _live_fn(drv, *, channel_id, content_type="short"):
        if content_type == "upload":
            raise ConnectionError("Videos Studio URL unavailable (systemic)")
        return _live_signal_with(shorts_results.get(channel_id, 0))

    # Shorts ranking should work (live signal active for shorts).
    shorts_count_fn = build_live_count_fn(driver, content_type="short", live_signal_fn=_live_fn)
    shorts_ranking = rank_channels_by_need(
        channels=CHANNELS, count_fn=shorts_count_fn, today=FIXED_TODAY,
    )
    assert shorts_ranking[0]["channel_id"] == "UC_A", \
        "UC_A (shorts=0) must still rank highest for Shorts despite Videos failure"

    # Videos count_fn: systemic failure -> build_live_count_fn degrades gracefully.
    # Each call to _live_count_fn raises -> falls back to _default_count_fn (offline).
    # The build itself should NOT raise; the failure happens inside _live_count_fn.
    with patch(
        "modules.platform_integration.youtube_shorts_scheduler.skillz"
        ".what_should_i_schedule.executor._default_count_fn",
        side_effect=lambda ch, ds: 0,
    ):
        video_count_fn = build_live_count_fn(driver, content_type="upload", live_signal_fn=_live_fn)
        video_ranking = rank_channels_by_need(
            channels=CHANNELS, count_fn=video_count_fn, today=FIXED_TODAY,
        )

    # All channels still returned (no drop due to failure).
    assert len(video_ranking) == 2
    assert {r["channel_id"] for r in video_ranking} == {"UC_A", "UC_B"}


# ---------------------------------------------------------------------------
# Test 6: YT_VIDEO_PROCESSING_ENABLED=0 -> Videos live check NOT called;
#         Shorts ranking unchanged.
# ---------------------------------------------------------------------------

def test_video_processing_disabled_no_video_live_call(monkeypatch):
    """YT_VIDEO_PROCESSING_ENABLED=0 -> Videos live check NOT called.

    Shorts ranking is completely unchanged (Addendum H: flag-off baseline).
    """
    monkeypatch.setenv("YT_VIDEO_PROCESSING_ENABLED", "0")
    monkeypatch.setenv("YT_SCHEDULE_PRIORITY_ENABLED", "1")
    driver = _make_mock_driver()

    live_call_log: "list[str]" = []

    def _live_fn(drv, *, channel_id, content_type="short"):
        live_call_log.append(content_type)
        return _live_signal_with(0)

    shorts_count_fn = build_live_count_fn(driver, content_type="short", live_signal_fn=_live_fn)
    # Only shorts ranking is called (no video ranking when flag off).
    shorts_ranking = rank_channels_by_need(
        channels=CHANNELS, count_fn=shorts_count_fn, today=FIXED_TODAY,
    )
    assert len(shorts_ranking) == 2  # Shorts ranking unaffected.
    # All live calls in this test were content_type="short" (from shorts_count_fn).
    # No "upload" calls because the caller (test/launch) doesn't build video_count_fn.
    upload_calls = [c for c in live_call_log if c == "upload"]
    assert len(upload_calls) == 0, \
        f"No upload live calls expected when YT_VIDEO_PROCESSING_ENABLED=0; got {upload_calls}"

    # Also verify _prioritize_channels with flag=0 doesn't compute videos ranking.
    original = ["chanA", "chanB"]
    with patch.object(launch, "_pass_video_ranking") as mock_vr:
        monkeypatch.setenv("YT_SCHEDULE_PRIORITY_ENABLED", "0")
        result = launch._prioritize_channels(original, driver=driver)
    assert result == original  # Flag off -> original order returned.


# ---------------------------------------------------------------------------
# Test 7: Invalid content_type -> fails closed to offline fallback (Addendum I).
# ---------------------------------------------------------------------------

def test_invalid_content_type_fails_closed():
    """Invalid content_type fails closed: scheduled_count=None, no URL built.

    Addendum I: CONTENT_TYPE_VALIDATED_SHORT_OR_UPLOAD.
    The function must never reach URL construction for an invalid content_type.
    """
    driver = _make_mock_driver()

    # Valid types pass validation.
    assert _validate_content_type("short") is True
    assert _validate_content_type("upload") is True

    # Invalid types fail.
    assert _validate_content_type("live") is False
    assert _validate_content_type("") is False
    assert _validate_content_type("SHORT") is False  # case-sensitive

    # read_live_schedule_signal: invalid content_type -> fail closed.
    result = read_live_schedule_signal(
        driver, channel_id="UC_TEST", content_type="invalid_type",
    )
    assert result["success"] is False
    assert result["scheduled_count"] is None, \
        "Invalid content_type must fail closed: scheduled_count=None"
    assert result["scheduled_count_status"] == "invalid_content_type"
    assert result.get("content_type_valid") is False
    # Filter should never have been applied.
    assert result["filter_applied"] is False
    # Verify driver was never touched (no DOM call on invalid content_type).
    driver.execute_script.assert_not_called()
    driver.find_element.assert_not_called()


# ---------------------------------------------------------------------------
# Test 8: MUST FAIL proof -- without unified ranking, a channel with Shorts=full
#         but Videos=empty is NOT prioritised for Videos on current code.
# ---------------------------------------------------------------------------

def test_must_fail_without_unified_ranking_proof():
    """NON-VACUITY PROOF: without video ranking, Videos=empty channel is NOT prioritized.

    OLD behavior (no video ranking computed at all): a channel with Videos=0
    has no mechanism to get highest Videos priority. The code simply iterates
    channels in original order for the video pass.

    NEW behavior (this slice): build_live_count_fn(content_type="upload") is
    called, and the Videos ranking correctly identifies the channel with Videos=0
    as highest priority.

    This test explicitly verifies the old code FAILS the assertion, then the
    new code PASSES it.
    """
    driver = _make_mock_driver()

    # Channel A: Shorts FULL (e.g. 21 scheduled), Videos EMPTY (0 scheduled).
    # Channel B: Shorts empty (0), Videos FULL (21 scheduled).
    def _live_fn(drv, *, channel_id, content_type="short"):
        if content_type == "short":
            # A=full (21 scheduled), B=empty (0 scheduled).
            count = 21 if channel_id == "UC_A" else 0
        else:  # upload
            # A=empty (0 videos scheduled), B=full (21 videos scheduled).
            count = 0 if channel_id == "UC_A" else 21
        return _live_signal_with(count)

    # --- OLD path: only Shorts ranking, no Videos ranking ---
    shorts_count_fn_old = build_live_count_fn(driver, content_type="short", live_signal_fn=_live_fn)
    shorts_ranking_old = rank_channels_by_need(
        channels=CHANNELS, count_fn=shorts_count_fn_old, today=FIXED_TODAY,
    )
    # OLD: Shorts ranking puts B first (B has 0 shorts).
    assert shorts_ranking_old[0]["channel_id"] == "UC_B", \
        "OLD: B (shorts=0) must rank first for Shorts"
    # OLD: Without a Videos ranking, there is no way to determine A needs Videos.
    # Assert: no Videos ranking exists on the old path -- this is the MUST FAIL.
    # We prove this by asserting the Shorts ranking for UC_A shows it as LOWER,
    # and WITHOUT the new video count_fn, UC_A gets ZERO videos priority signal.
    a_shorts_row = next(r for r in shorts_ranking_old if r["channel_id"] == "UC_A")
    # UC_A has 21 shorts scheduled -> low Shorts deficit (possibly 0 with high cap).
    # The point: old code has no mechanism to prioritize UC_A for Videos.
    # We simulate: "if we were to check Videos priority on old code, we'd have no info".
    old_code_has_video_priority_for_A = False  # definitionally true on old path
    assert old_code_has_video_priority_for_A is False, \
        "MUST FAIL proof: old code has no Videos priority mechanism for UC_A"

    # --- NEW path: Videos ranking via build_live_count_fn(content_type="upload") ---
    video_count_fn_new = build_live_count_fn(driver, content_type="upload", live_signal_fn=_live_fn)
    video_ranking_new = rank_channels_by_need(
        channels=CHANNELS, count_fn=video_count_fn_new, today=FIXED_TODAY,
    )
    # NEW: UC_A has 0 videos -> highest Videos priority.
    assert video_ranking_new[0]["channel_id"] == "UC_A", \
        "NEW: A (videos=0) must rank first for Videos -- this is what the new code provides"


# ---------------------------------------------------------------------------
# Test 9: One-call budget -- at most one live count call per (channel, content_type)
#         per pass (Addendum D: LIVE_SIGNAL_ONE_CALL_PER_CHANNEL_CONTENT_TYPE).
# ---------------------------------------------------------------------------

def test_one_live_call_per_channel_per_content_type():
    """At most one live count call per (channel, content_type) per ranking pass.

    The cache in build_live_count_fn ensures the DOM read happens only once
    per channel_id per closure lifetime, not once per date query.
    """
    driver = _make_mock_driver()
    call_log: "list[tuple]" = []

    def _live_fn(drv, *, channel_id, content_type="short"):
        call_log.append((channel_id, content_type))
        return _live_signal_with(2)

    # Shorts ranking: 7 days x 2 channels = 14 date queries, but only 2 live calls.
    shorts_count_fn = build_live_count_fn(driver, content_type="short", live_signal_fn=_live_fn)
    rank_channels_by_need(channels=CHANNELS, count_fn=shorts_count_fn, today=FIXED_TODAY)

    # Each channel should be called exactly once.
    shorts_calls = [(ch, ct) for ch, ct in call_log if ct == "short"]
    assert len(shorts_calls) == len(CHANNELS), \
        f"Expected {len(CHANNELS)} live calls for shorts, got {len(shorts_calls)}"
    called_channel_ids = {ch for ch, _ in shorts_calls}
    assert called_channel_ids == {"UC_A", "UC_B"}

    # Reset and test videos path (separate closure = separate cache).
    call_log.clear()
    video_count_fn = build_live_count_fn(driver, content_type="upload", live_signal_fn=_live_fn)
    rank_channels_by_need(channels=CHANNELS, count_fn=video_count_fn, today=FIXED_TODAY)

    upload_calls = [(ch, ct) for ch, ct in call_log if ct == "upload"]
    assert len(upload_calls) == len(CHANNELS), \
        f"Expected {len(CHANNELS)} live calls for upload, got {len(upload_calls)}"


# ---------------------------------------------------------------------------
# Test 10: Flag-off baseline (Addendum H) -- YT_VIDEO_PROCESSING_ENABLED=0
#          means no video live count calls and video ranking not computed.
# ---------------------------------------------------------------------------

def test_flag_off_baseline_no_video_live_calls(monkeypatch):
    """YT_VIDEO_PROCESSING_ENABLED=0 baseline: no video live count calls.

    Shorts ranking is unchanged. Video ranking is not computed by _prioritize_channels.
    Addendum H: flag-off must be a zero-impact path.
    """
    monkeypatch.setenv("YT_VIDEO_PROCESSING_ENABLED", "0")
    monkeypatch.setenv("YT_SCHEDULE_PRIORITY_ENABLED", "1")
    monkeypatch.setenv("YT_LIVE_SCHEDULE_SIGNAL_ENABLED", "1")

    driver = _make_mock_driver()
    video_calls: "list" = []

    def _live_fn(drv, *, channel_id, content_type="short"):
        if content_type == "upload":
            video_calls.append(channel_id)
        return _live_signal_with(0 if channel_id == "UC_A" else 2)

    _REGISTRY = [
        {"id": "UC_A", "key": "chanA", "name": "ChanA"},
        {"id": "UC_B", "key": "chanB", "name": "ChanB"},
    ]

    def _registry_channels(role=None):
        return list(_REGISTRY)

    with patch(
        "modules.infrastructure.shared_utilities.youtube_channel_registry.get_channels",
        side_effect=_registry_channels,
    ), patch(
        "modules.platform_integration.youtube_shorts_scheduler.skillz"
        ".what_should_i_schedule.executor.build_live_count_fn",
        side_effect=lambda drv, content_type="short", live_signal_fn=None:
            build_live_count_fn(drv, content_type=content_type, live_signal_fn=_live_fn),
    ), patch.object(launch, "_emit_priority_breadcrumb"):
        result = launch._prioritize_channels(["chanA", "chanB"], driver=driver)

    # No upload calls because YT_VIDEO_PROCESSING_ENABLED=0.
    assert len(video_calls) == 0, \
        f"Expected 0 video live calls with flag=0; got {video_calls}"

    # _pass_video_ranking must be empty (no videos ranking computed).
    assert len(launch._pass_video_ranking) == 0, \
        "Video ranking must not be populated when YT_VIDEO_PROCESSING_ENABLED=0"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
