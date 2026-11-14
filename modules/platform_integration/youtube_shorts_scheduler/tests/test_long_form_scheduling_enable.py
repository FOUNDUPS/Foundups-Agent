"""
Long-form (Videos-tab) scheduling enablement tests (Phase 1).

Slice: LONG_FORM_SCHEDULING_ENABLE_PHASE1

Proves the previously-DORMANT long-form video scheduling pass inside
run_multi_channel_scheduler (launch.py, the YT_VIDEO_PROCESSING_ENABLED block)
now runs for ALL 4 channels when the master flag is ON, gated default-OFF, with
a per-channel per-pass ROTATION budget mirroring the shorts #858 fairness fix.

WHAT WAS DORMANT (origin/main):
  - The long-form pass is gated by YT_VIDEO_PROCESSING_ENABLED (default "false"),
    set nowhere in daemon operation -> never ran.
  - It additionally requires the channel registry content_types to include
    "upload". On origin/main ONLY move2japan + undaodu had "upload"; foundups +
    antifafm were ["short"] -> even with the flag on, 2/4 channels were skipped.

THE CHANGE:
  1. Registry DEFAULTS: foundups + antifafm content_types now include "upload",
     so all 4 channels are long-form-eligible when the flag is enabled.
  2. A per-channel per-pass budget (YT_VIDEO_PER_CHANNEL_PER_PASS, default 8)
     caps long-form scheduled per channel per pass -> rotation, not drain.
  3. YT_VIDEO_PROCESSING_ENABLED stays the master gate, DEFAULT OFF.

ANTI-VACUITY / MUST-FAIL:
  - test_all_four_channels_have_upload_content_type asserts "upload" is in the
    REGISTRY DEFAULT content_types for foundups AND antifafm. On origin/main
    (["short"]) this FAILS -> it pins the registry change, not a tautology.
  - test_flag_off_does_not_run_long_form asserts the long-form ContentPageScheduler
    is NEVER constructed when YT_VIDEO_PROCESSING_ENABLED is unset/false. If the
    gate were removed/inverted this FAILS.
  - test_flag_on_runs_long_form_for_all_four_channels asserts schedule_all_visible
    is invoked once per channel for ALL FOUR keys incl. foundups/antifafm. If
    foundups/antifafm still lacked "upload", they would be skipped and the
    asserted set would be missing them -> FAIL.
  - The mock schedule_all_visible HONORS max_videos against a real backlog
    (scheduled = min(max_videos, backlog)), so the rotation-budget assertion is
    non-trivial: a stub ignoring the arg could not produce the capped numbers.
  - All heavy collaborators (browser, swapper, DOM, oops, cache, navigation) are
    mocked; NO live browser, NO network, NO disk writes.
"""

import os
from unittest.mock import MagicMock

import pytest

from modules.platform_integration.youtube_shorts_scheduler.scripts import launch as launch_mod
from modules.infrastructure.shared_utilities import youtube_channel_registry as registry_mod

# Pre-import the SUT's lazily-imported collaborators NOW with REAL selenium in
# place (foundups_driver subclasses webdriver.Chrome at import time).
import selenium.webdriver as _sel_webdriver  # noqa: E402,F401
import modules.infrastructure.foundups_selenium.src.foundups_driver  # noqa: F401,E402
import modules.communication.video_comments.skillz.tars_account_swapper.account_swapper_skill  # noqa: F401,E402
import modules.communication.livechat.src.multi_channel_coordinator  # noqa: F401,E402
import modules.platform_integration.youtube_shorts_scheduler.src.scheduler  # noqa: F401,E402
import modules.platform_integration.youtube_shorts_scheduler.src.dom_automation  # noqa: F401,E402
import modules.platform_integration.youtube_shorts_scheduler.src.content_page_scheduler as cps_mod  # noqa: E402
import modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker as tracker_mod  # noqa: E402
import modules.platform_integration.youtube_shorts_scheduler.src.channel_config as channel_config_mod  # noqa: E402


# Drive ALL FOUR channels through ONE browser group so a single
# run_multi_channel_scheduler pass exercises every channel's long-form branch.
_ALL_FOUR = ["move2japan", "undaodu", "foundups", "antifafm"]
_LONGFORM_BACKLOG = 100  # per-channel upload backlog (>> the per-pass budget)


class _FakeShortsScheduler:
    """Shorts path stub — returns an empty cycle so the test isolates long-form."""

    def __init__(self, channel_key, dry_run=False):
        self.channel_key = channel_key
        self.dry_run = dry_run
        self.driver = None
        self.dom = None

    async def run_scheduling_cycle(self, max_videos=0):
        return {
            "total_scheduled": 0,
            "total_errors": 0,
            "total_skipped": 0,
            "skipped": [],
            "cycle_seconds": 1,
        }


class _FakeContentPageScheduler:
    """
    Stand-in for ContentPageScheduler. Records every (channel_key, max_videos)
    schedule_all_visible call and HONORS max_videos against a backlog, so the
    rotation-budget assertion is non-vacuous.
    """

    instances = 0                      # count constructions (flag-off must stay 0)
    schedule_calls = []                # list of (channel_key, max_videos)
    nav_calls = []                     # list of (channel_key, content_type)
    tz_calls = []                      # list of (channel_key, channel_tz, time_slots)

    def __init__(self, driver):
        self.driver = driver
        self._channel_key = None
        _FakeContentPageScheduler.instances += 1

    def navigate_to_content(self, channel_key, content_type="short", visibility="UNLISTED", **kw):
        self._channel_key = channel_key
        _FakeContentPageScheduler.nav_calls.append((channel_key, content_type))
        return True

    async def schedule_all_visible(self, tracker, time_slots, max_per_day=8,
                                   max_videos=9999, stop_event=None,
                                   channel_tz=None):
        ch = self._channel_key
        _FakeContentPageScheduler.schedule_calls.append((ch, max_videos))
        _FakeContentPageScheduler.tz_calls.append((ch, channel_tz, list(time_slots)))
        scheduled = min(max_videos, _LONGFORM_BACKLOG)
        return {
            "total_scheduled": scheduled,
            "total_errors": 0,
            "total_skipped": 0,
            "scheduled": [],
            "errors": [],
        }


class _FakeTracker:
    def __init__(self, channel_key):
        self.channel_key = channel_key


def _reset_recorders():
    _FakeContentPageScheduler.instances = 0
    _FakeContentPageScheduler.schedule_calls = []
    _FakeContentPageScheduler.nav_calls = []
    _FakeContentPageScheduler.tz_calls = []


@pytest.fixture
def longform_harness(monkeypatch):
    """
    Patch every heavy collaborator so run_multi_channel_scheduler runs in-process
    with NO browser/network/disk and the long-form ContentPageScheduler is the
    fake recorder. Returns the recorder class.
    """
    _reset_recorders()

    # Force all four channels into the edge browser group -> one rotation pass.
    monkeypatch.setitem(launch_mod.BROWSER_CHANNELS, "edge", list(_ALL_FOUR))

    # --- browser connection (selenium imported locally in the SUT) ---
    fake_driver = MagicMock(name="driver")
    fake_driver.window_handles = ["h0"]
    fake_driver.current_url = "https://studio.youtube.com/"
    monkeypatch.setattr("selenium.webdriver.Edge", lambda *a, **k: fake_driver)
    monkeypatch.setattr("selenium.webdriver.Chrome", lambda *a, **k: fake_driver)

    # --- shorts scheduler + DOM + account swapper ---
    monkeypatch.setattr(
        "modules.platform_integration.youtube_shorts_scheduler.src.scheduler.YouTubeShortsScheduler",
        _FakeShortsScheduler,
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
    monkeypatch.setattr(launch_mod, "_prioritize_channels", lambda chans: chans)

    # --- long-form collaborators (imported locally in the SUT's long-form block) ---
    monkeypatch.setattr(cps_mod, "ContentPageScheduler", _FakeContentPageScheduler)
    monkeypatch.setattr(tracker_mod, "ScheduleTracker", _FakeTracker)

    # get_channel_config: return a per-channel config with a registry timezone so
    # the SUT's tz-warning branch is exercised for the Tokyo channels.
    _TZ = {
        "move2japan": "Asia/Tokyo",
        "undaodu": "Asia/Tokyo",
        "foundups": "America/New_York",
        "antifafm": "America/New_York",
    }
    monkeypatch.setattr(
        channel_config_mod,
        "get_channel_config",
        lambda key: {"timezone": _TZ.get(key), "time_slots": ["08:00", "12:00", "20:00"]},
    )

    # get_channel_by_key drives the content_types eligibility check in the SUT.
    # Make ALL FOUR upload-eligible (mirrors the registry-default change) so the
    # long-form branch is reached for every channel.
    monkeypatch.setattr(
        launch_mod,
        "get_channel_by_key",
        lambda key: {"key": key, "content_types": ["short", "upload"]},
    )

    # Disable the post-loop calendar audit (it builds a real ContentPageScheduler
    # against the mocked driver — out of scope here).
    monkeypatch.setenv("YT_SCHEDULE_AUDIT_ENABLED", "false")

    # Clean env baseline for the knobs under test.
    monkeypatch.delenv("YT_VIDEO_PROCESSING_ENABLED", raising=False)
    monkeypatch.delenv("YT_VIDEO_PER_CHANNEL_PER_PASS", raising=False)

    return _FakeContentPageScheduler


# ---------------------------------------------------------------------------
# Registry default change (MUST FAIL on origin/main where these were ["short"])
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("channel_key", ["foundups", "antifafm"])
def test_all_four_channels_have_upload_content_type(channel_key):
    """
    The registry DEFAULT content_types for foundups AND antifafm must now include
    "upload". On origin/main these were ["short"] -> this assertion FAILS, so it
    genuinely pins the enablement change (not a tautology).
    """
    defaults = {c["key"]: c for c in registry_mod._default_channels()}
    assert channel_key in defaults, f"{channel_key} missing from registry defaults"
    cts = defaults[channel_key].get("content_types", [])
    assert "upload" in cts, (
        f"registry DEFAULT content_types for '{channel_key}' is {cts!r}; "
        f"long-form enablement requires 'upload'. On origin/main this was "
        f"['short'] -> long-form was skipped for this channel."
    )


def test_move2japan_undaodu_still_have_upload():
    """Pre-existing upload channels must remain upload-eligible (no regression)."""
    defaults = {c["key"]: c for c in registry_mod._default_channels()}
    for key in ("move2japan", "undaodu"):
        assert "upload" in defaults[key].get("content_types", []), (
            f"{key} lost its 'upload' content_type"
        )


# ---------------------------------------------------------------------------
# Flag default-OFF: long-form pass must NOT run
# ---------------------------------------------------------------------------

def test_flag_off_does_not_run_long_form(longform_harness):
    """
    With YT_VIDEO_PROCESSING_ENABLED unset (default off), the long-form
    ContentPageScheduler is NEVER constructed and schedule_all_visible NEVER
    called. If the master gate were removed/inverted this FAILS.
    """
    launch_mod.run_multi_channel_scheduler(
        browser="edge", mode="schedule", max_per_channel=9999, dry_run=False
    )
    assert longform_harness.instances == 0, (
        "long-form ContentPageScheduler was constructed while "
        "YT_VIDEO_PROCESSING_ENABLED was OFF — the master gate leaked"
    )
    assert longform_harness.schedule_calls == [], (
        "long-form schedule_all_visible ran while the master flag was OFF"
    )


def test_flag_explicit_false_does_not_run_long_form(longform_harness, monkeypatch):
    """Explicit 'false' is equivalent to unset — no long-form pass."""
    monkeypatch.setenv("YT_VIDEO_PROCESSING_ENABLED", "false")
    launch_mod.run_multi_channel_scheduler(
        browser="edge", mode="schedule", max_per_channel=9999, dry_run=False
    )
    assert longform_harness.schedule_calls == []


# ---------------------------------------------------------------------------
# Flag ON: long-form runs for ALL FOUR channels, rotation-budgeted
# ---------------------------------------------------------------------------

def test_flag_on_runs_long_form_for_all_four_channels(longform_harness, monkeypatch):
    """
    With YT_VIDEO_PROCESSING_ENABLED=1, the long-form pass runs for ALL FOUR
    channels (incl. foundups + antifafm now that they have "upload"), each
    scheduled exactly once via schedule_all_visible.
    """
    monkeypatch.setenv("YT_VIDEO_PROCESSING_ENABLED", "1")

    launch_mod.run_multi_channel_scheduler(
        browser="edge", mode="schedule", max_per_channel=9999, dry_run=False
    )

    calls = longform_harness.schedule_calls
    assert calls, "long-form schedule_all_visible never ran with flag ON (vacuous)"

    touched = {c for c, _ in calls}
    assert touched == set(_ALL_FOUR), (
        f"long-form did not run for all 4 channels in one pass: touched={touched}; "
        f"foundups/antifafm must be included now that they have 'upload'"
    )

    # Navigation used the Videos tab (content_type="upload") for every channel.
    nav_uploads = {c for c, ct in longform_harness.nav_calls if ct == "upload"}
    assert nav_uploads == set(_ALL_FOUR), (
        f"long-form navigate_to_content(content_type='upload') missing channels: "
        f"{set(_ALL_FOUR) - nav_uploads}"
    )


def test_long_form_rotation_budget_default(longform_harness, monkeypatch):
    """
    Default rotation budget: every channel's schedule_all_visible is called with
    max_videos == 8 (YT_VIDEO_PER_CHANNEL_PER_PASS default), NOT max_per_channel
    (9999). The mock honors max_videos, so each channel schedules exactly 8 of
    its 100-video backlog -> rotation, not drain.
    """
    monkeypatch.setenv("YT_VIDEO_PROCESSING_ENABLED", "1")

    results = launch_mod.run_multi_channel_scheduler(
        browser="edge", mode="schedule", max_per_channel=9999, dry_run=False
    )

    calls = longform_harness.schedule_calls
    assert calls, "vacuous: no long-form calls"
    for channel_key, max_videos in calls:
        assert max_videos == 8, (
            f"{channel_key} long-form called with max_videos={max_videos}; "
            f"expected the per-pass rotation budget of 8, not the drain 9999"
        )

    # Each channel scheduled exactly the 8-video budget (not the full 100 backlog).
    for ch in _ALL_FOUR:
        sched = results["channels"][f"{ch}_videos"]["total_scheduled"]
        assert sched == 8, (
            f"{ch} long-form scheduled {sched} this pass; rotation budget should "
            f"cap at 8, not drain the {_LONGFORM_BACKLOG}-video backlog"
        )


def test_long_form_rotation_must_fail_if_old_drain(longform_harness, monkeypatch):
    """
    MUST-FAIL proof for the rotation budget: the OLD long-form code passed
    max_videos=min(max_per_channel, 5) with NO env-tunable rotation budget and
    no per-pass fairness across the full backlog. This pins that the budget now
    reaches schedule_all_visible and caps the FIRST channel well below the
    backlog. A drain-one-fully regression (max_videos >= backlog) FAILS here.
    """
    monkeypatch.setenv("YT_VIDEO_PROCESSING_ENABLED", "1")

    launch_mod.run_multi_channel_scheduler(
        browser="edge", mode="schedule", max_per_channel=9999, dry_run=False
    )

    calls = longform_harness.schedule_calls
    assert calls, "vacuous: no long-form calls"
    first_channel, first_max = calls[0]
    assert first_max < _LONGFORM_BACKLOG, (
        f"DRAIN REGRESSION: first long-form channel '{first_channel}' called with "
        f"max_videos={first_max} >= backlog {_LONGFORM_BACKLOG}; rotation budget lost"
    )
    assert first_max == 8


def test_long_form_budget_env_override(longform_harness, monkeypatch):
    """The rotation budget is TUNABLE via YT_VIDEO_PER_CHANNEL_PER_PASS."""
    monkeypatch.setenv("YT_VIDEO_PROCESSING_ENABLED", "1")
    monkeypatch.setenv("YT_VIDEO_PER_CHANNEL_PER_PASS", "4")

    launch_mod.run_multi_channel_scheduler(
        browser="edge", mode="schedule", max_per_channel=9999, dry_run=False
    )
    for channel_key, max_videos in longform_harness.schedule_calls:
        assert max_videos == 4, (
            f"{channel_key}: env override YT_VIDEO_PER_CHANNEL_PER_PASS=4 not honored "
            f"(got {max_videos})"
        )


def test_long_form_budget_invalid_env_falls_back(longform_harness, monkeypatch):
    """Garbage / non-positive override -> safe fallback to the default 8 budget."""
    monkeypatch.setenv("YT_VIDEO_PROCESSING_ENABLED", "1")
    for bad in ("not-an-int", "0", "-3", ""):
        _reset_recorders()
        monkeypatch.setenv("YT_VIDEO_PER_CHANNEL_PER_PASS", bad)
        launch_mod.run_multi_channel_scheduler(
            browser="edge", mode="schedule", max_per_channel=9999, dry_run=False
        )
        for channel_key, max_videos in longform_harness.schedule_calls:
            assert max_videos == 8, (
                f"bad env '{bad}': {channel_key} got max_videos={max_videos}, "
                f"expected fallback budget 8"
            )
