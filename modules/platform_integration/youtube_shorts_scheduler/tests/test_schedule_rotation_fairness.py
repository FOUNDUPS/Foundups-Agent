"""
Schedule rotation fairness tests (Phase 1).

Slice: SHORTS_SCHEDULE_ROTATION_FAIRNESS_PHASE1

Proves run_multi_channel_scheduler ROTATES ~3 days of content per channel per
pass instead of DRAINING the first channel's entire backlog (up to the 60-day
window / ~180 videos) before ever touching the next channel.

THE BUG (origin/main, launch.py): the per-channel call was
    scheduler.run_scheduling_cycle(max_videos=max_per_channel)
with max_per_channel defaulting to 9999 (and the DAE passing
YT_SHORTS_PER_CYCLE default 9999). Since run_scheduling_cycle's max_videos only
limits the COUNT (scheduler.py: unlisted[:max_videos]; HARD_CAP_PER_DAY=3 only
spreads dates), the FIRST channel scheduled its whole backlog before the
for-loop reached the next channel.

THE FIX: a per-channel per-pass budget (YT_SHORTS_PER_CHANNEL_PER_PASS, default
"9" = 3 days x 3/day). Each channel is now called with
    max_videos = min(max_per_channel, per_channel_per_pass)
so it schedules ~9 then the loop rotates; the daemon's next PHASE 3 re-invocation
continues draining round-robin until every backlog is empty.

ANTI-VACUITY:
  - The mock run_scheduling_cycle is NON-TRIVIAL: it consumes max_videos against
    a real 100-video backlog (scheduled = min(max_videos, remaining)), so a stub
    that ignored the arg could not produce the asserted partial-drain numbers.
  - test_rotation_must_fail_if_old_drain asserts max_videos <= 9 for EVERY
    channel call. On the OLD code (max_videos=max_per_channel=9999) this FAILS,
    so the test genuinely pins the new behavior and would catch a regression.
  - We assert BOTH channels were touched in ONE pass AND neither was drained to
    100 (each got exactly the 9-video budget), which the drain-one-fully code
    could not satisfy (channel 1 would take 100, channel 2 would also take 100,
    and the recorded max_videos would be 9999, not 9).
  - All collaborators (browser, account swapper, DOM, oops detector, schedule
    cache) are mocked; NO live browser, NO real network, NO real filesystem
    writes. The only behavior exercised is the budget arithmetic + the for-loop.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from modules.platform_integration.youtube_shorts_scheduler.scripts import launch as launch_mod

# Pre-import the SUT's lazily-imported collaborators NOW, with the REAL selenium
# classes still in place. foundups_driver.py does `class FoundUpsDriver(webdriver.Chrome)`
# at import time, so the subclass must be built before we patch webdriver.Edge/Chrome.
import selenium.webdriver as _sel_webdriver  # noqa: E402
import modules.infrastructure.foundups_selenium.src.foundups_driver  # noqa: F401,E402
import modules.communication.video_comments.skillz.tars_account_swapper.account_swapper_skill  # noqa: F401,E402
import modules.communication.livechat.src.multi_channel_coordinator  # noqa: F401,E402
import modules.platform_integration.youtube_shorts_scheduler.src.scheduler  # noqa: F401,E402
import modules.platform_integration.youtube_shorts_scheduler.src.dom_automation  # noqa: F401,E402


# Edge browser has two channels in the registry -> good rotation surface.
_EDGE_CHANNELS = ["foundups", "antifafm"]
_BACKLOG = 100  # per-channel unlisted backlog (way more than the 9-video budget)


class _FakeScheduler:
    """
    Stand-in for YouTubeShortsScheduler whose run_scheduling_cycle HONORS
    max_videos exactly the way the real one does (count limiter against a
    backlog). Records every max_videos it was called with so tests can assert
    the per-channel per-pass budget actually reached run_scheduling_cycle.
    """

    # class-level recorders shared across the per-channel instances the SUT makes
    calls = []  # list of (channel_key, max_videos)

    def __init__(self, channel_key, dry_run=False):
        self.channel_key = channel_key
        self.dry_run = dry_run
        self.driver = None
        self.dom = None

    async def run_scheduling_cycle(self, max_videos=0):
        _FakeScheduler.calls.append((self.channel_key, max_videos))
        # Honor max_videos the way scheduler.py does: 0 == unlimited, else cap.
        remaining = _BACKLOG
        scheduled = remaining if max_videos == 0 else min(max_videos, remaining)
        return {
            "total_scheduled": scheduled,
            "total_errors": 0,
            "total_skipped": 0,
            "skipped": [],
            "cycle_seconds": 1,
        }


@pytest.fixture
def rotation_harness(monkeypatch):
    """
    Patch every heavy collaborator so run_multi_channel_scheduler runs in-process
    with NO browser/network/disk. Returns the shared call recorder.
    """
    _FakeScheduler.calls = []

    # Force a known 2-channel edge rotation regardless of registry state.
    monkeypatch.setitem(launch_mod.BROWSER_CHANNELS, "edge", list(_EDGE_CHANNELS))

    # --- browser connection (selenium webdriver imported locally in the SUT) ---
    fake_driver = MagicMock(name="driver")
    fake_driver.window_handles = ["h0"]  # single tab -> skip the close-tabs path
    fake_driver.current_url = "https://studio.youtube.com/"
    monkeypatch.setattr("selenium.webdriver.Edge", lambda *a, **k: fake_driver)
    monkeypatch.setattr("selenium.webdriver.Chrome", lambda *a, **k: fake_driver)

    # --- scheduler + DOM + account swapper (imported locally in the SUT) ---
    monkeypatch.setattr(
        "modules.platform_integration.youtube_shorts_scheduler.src.scheduler.YouTubeShortsScheduler",
        _FakeScheduler,
    )
    monkeypatch.setattr(
        "modules.platform_integration.youtube_shorts_scheduler.src.dom_automation.YouTubeStudioDOM",
        lambda *a, **k: MagicMock(name="dom"),
    )

    class _FakeSwapper:
        def __init__(self, driver):
            self.driver = driver

        async def swap_to(self, *a, **k):
            return True

    monkeypatch.setattr(
        "modules.communication.video_comments.skillz.tars_account_swapper.account_swapper_skill.TarsAccountSwapper",
        _FakeSwapper,
    )

    # --- oops detector + skip cache (no real disk / no skipping) ---
    monkeypatch.setattr(
        "modules.communication.livechat.src.multi_channel_coordinator._is_oops_page",
        lambda *a, **k: False,
    )
    monkeypatch.setattr(launch_mod, "_load_schedule_cache", lambda: {})
    monkeypatch.setattr(launch_mod, "_should_skip_channel", lambda *a, **k: False)
    monkeypatch.setattr(launch_mod, "_record_channel_result", lambda *a, **k: None)
    # Keep priority wiring a no-op (do not touch #854 ordering in these tests).
    monkeypatch.setattr(launch_mod, "_prioritize_channels", lambda chans: chans)

    # Ensure a clean env baseline for the budget knob.
    monkeypatch.delenv("YT_SHORTS_PER_CHANNEL_PER_PASS", raising=False)
    monkeypatch.delenv("YT_VIDEO_PROCESSING_ENABLED", raising=False)
    # Disable the post-loop calendar audit + long-form video pass: both spin up a
    # real ContentPageScheduler against the mocked driver (out of scope for the
    # rotation budget under test, and would block on real Selenium waits).
    monkeypatch.setenv("YT_SCHEDULE_AUDIT_ENABLED", "false")
    monkeypatch.setenv("YT_VIDEO_PROCESSING_ENABLED", "false")

    return _FakeScheduler.calls


def test_each_channel_called_with_budget_not_full_drain(rotation_harness):
    """
    With the DEFAULT (no env override), every channel's run_scheduling_cycle is
    called with max_videos == 9 (the 3-days budget), NOT max_per_channel (9999).
    """
    results = launch_mod.run_multi_channel_scheduler(
        browser="edge", mode="schedule", max_per_channel=9999, dry_run=False
    )

    calls = rotation_harness
    assert calls, "run_scheduling_cycle was never called (vacuous)"

    # Every per-channel call must be budgeted (<= 9), NOT the 9999 drain.
    for channel_key, max_videos in calls:
        assert max_videos == 9, (
            f"{channel_key} called with max_videos={max_videos}; expected the "
            f"per-pass budget of 9, not the drain-one-fully 9999"
        )

    # Both edge channels touched in ONE pass (rotation, not drain).
    touched = {c for c, _ in calls}
    assert touched == set(_EDGE_CHANNELS), (
        f"rotation did not touch all channels in one pass: touched={touched}"
    )

    # And neither channel was drained to its full 100 backlog this pass.
    for ch in _EDGE_CHANNELS:
        scheduled = results["channels"][ch]["total_scheduled"]
        assert scheduled == 9, (
            f"{ch} scheduled {scheduled} this pass; rotation budget should cap at 9, "
            f"not drain the full {_BACKLOG}-video backlog"
        )


def test_rotation_must_fail_if_old_drain(rotation_harness):
    """
    MUST-FAIL proof: this is the assertion the OLD drain-one-fully code violates.
    On origin/main the call was run_scheduling_cycle(max_videos=max_per_channel)
    with max_per_channel=9999, so max_videos would be 9999 (> 9) here and this
    test would FAIL. It passes only because the fix budgets each channel to 9.
    """
    launch_mod.run_multi_channel_scheduler(
        browser="edge", mode="schedule", max_per_channel=9999, dry_run=False
    )

    calls = rotation_harness
    assert calls, "run_scheduling_cycle was never called (vacuous)"

    # The first channel must NOT have drained the whole backlog: its budget is 9.
    first_channel, first_max = calls[0]
    assert first_max <= 9, (
        f"DRAIN-ONE-FULLY REGRESSION: first channel '{first_channel}' was called "
        f"with max_videos={first_max} (>9). The old code passed 9999 here, "
        f"draining the entire backlog before rotating. Expected a per-pass budget <=9."
    )
    # Total scheduled across the pass must be ~budget*channels, not backlog*1.
    total = first_max
    assert total < _BACKLOG, (
        f"first channel consumed >= the full backlog ({total} >= {_BACKLOG}); "
        f"that is the drain-one-fully bug, not rotation"
    )


def test_env_override_restores_large_budget(rotation_harness, monkeypatch):
    """
    The fix is TUNABLE: setting YT_SHORTS_PER_CHANNEL_PER_PASS very high restores
    the old drain-one-fully behavior (budget bounded only by max_per_channel).
    """
    monkeypatch.setenv("YT_SHORTS_PER_CHANNEL_PER_PASS", "100000")

    results = launch_mod.run_multi_channel_scheduler(
        browser="edge", mode="schedule", max_per_channel=9999, dry_run=False
    )

    calls = rotation_harness
    assert calls, "run_scheduling_cycle was never called (vacuous)"

    # min(9999, 100000) == 9999 -> the large budget is passed through.
    for channel_key, max_videos in calls:
        assert max_videos == 9999, (
            f"{channel_key} called with max_videos={max_videos}; the env override "
            f"should restore the max_per_channel-bounded budget (9999)"
        )

    # With a 9999 budget against a 100 backlog, each channel drains fully (100).
    for ch in _EDGE_CHANNELS:
        assert results["channels"][ch]["total_scheduled"] == _BACKLOG


def test_invalid_env_falls_back_to_default_budget(rotation_harness, monkeypatch):
    """Garbage / non-positive env -> safe fallback to the default 9 budget."""
    for bad in ("not-an-int", "0", "-5", ""):
        _FakeScheduler.calls = []
        monkeypatch.setenv("YT_SHORTS_PER_CHANNEL_PER_PASS", bad)
        launch_mod.run_multi_channel_scheduler(
            browser="edge", mode="schedule", max_per_channel=9999, dry_run=False
        )
        for channel_key, max_videos in _FakeScheduler.calls:
            assert max_videos == 9, (
                f"bad env '{bad}': {channel_key} got max_videos={max_videos}, "
                f"expected fallback budget 9"
            )
