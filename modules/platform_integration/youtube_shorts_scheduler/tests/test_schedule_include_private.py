"""
Mock-only tests for SHORTS_SCHEDULE_INCLUDE_PRIVATE_PHASE1.

Proves the flag-gated PRIVATE pass on YouTubeShortsScheduler.run_scheduling_cycle:

  * flag OFF (default) -> ONLY the UNLISTED pass runs (navigate is called with
    "UNLISTED" and NEVER with "PRIVATE").  <-- the MUST-FAIL guard
  * flag ON  -> BOTH the UNLISTED and PRIVATE passes run (navigate called with
    each), and a [PRIVATE->PUBLIC] log fires per private video scheduled.
  * the edit-page visibility guard ACCEPTS "private" only when the private pass
    is active, and still REJECTS it on the unlisted pass.

NO live browser: self.driver / self.dom / self.tracker are mocks. The scheduler
is built with __new__ so __init__ (which connects config) is bypassed and only the
attributes the cycle touches are wired by hand.

NON-VACUITY: test_flag_off_never_navigates_private FAILS if the PRIVATE pass runs
while the flag is off (it asserts navigate is NEVER called with PRIVATE). Reverting
_resolve_visibility_targets to always include PRIVATE makes that test fail.
"""

import asyncio
import logging
import os

import pytest

from modules.platform_integration.youtube_shorts_scheduler.src.scheduler import (
    YouTubeShortsScheduler,
)


class _FakeTracker:
    """Minimal stand-in for ScheduleTracker.

    Hands out a unique slot per call (so the loop never thinks slots are
    exhausted) and records increments. Shared across passes, exactly like the
    real single self.tracker.
    """

    def __init__(self):
        self.increments = []
        self._scheduled_ids = set()
        self._n = 0

    def log_schedule_report(self):
        pass

    def is_video_scheduled(self, video_id):
        return video_id in self._scheduled_ids

    def get_next_available_slot(self, time_slots, max_per_day, channel_tz=None):
        self._n += 1
        # Distinct date per allocation so the per-day cap never short-circuits
        # the test (the cap itself is exercised by the dedicated tracker tests).
        return (f"Jan {self._n:02d}, 2026", "5:30 AM")

    def increment(self, date_str, video_id):
        self.increments.append((date_str, video_id))
        self._scheduled_ids.add(video_id)

    def remove_video(self, video_id):
        self._scheduled_ids.discard(video_id)


class _RecordingDOM:
    """Mock DOM that records navigate_to_shorts_with_fallback visibility args.

    get_unlisted_videos returns the UNLISTED roster ONCE then empties (so the
    continuous batch loop terminates). The scheduler's own private scrape reads
    self.driver.execute_script, which we stub to return the PRIVATE roster once.
    """

    def __init__(self, unlisted_rows, private_rows, edit_vis="unlisted"):
        self.navigate_calls = []  # list of visibility strings
        self._unlisted = list(unlisted_rows)
        self._unlisted_served = False
        self._edit_vis = edit_vis

    # --- navigation / filter ---
    def navigate_to_shorts_with_fallback(self, channel_id, visibility, use_ui_tars=True):
        self.navigate_calls.append(visibility)
        return True

    def read_visibility_filter_state(self):
        return {"detected": None, "chip_texts": []}

    def set_page_size(self, n):
        pass

    def click_back_to_shorts_list(self):
        pass

    # --- UNLISTED scrape (delegated to by the scheduler for the unlisted pass) ---
    def get_unlisted_videos(self):
        if self._unlisted_served:
            return []
        self._unlisted_served = True
        return list(self._unlisted)

    # --- edit page / scheduling ---
    def navigate_to_video(self, video_id):
        pass

    def read_edit_page_visibility(self):
        return self._edit_vis

    def schedule_video(self, date_str, time_str):
        return True

    def human_delay(self, base, variance):
        return 0.0


class _FakeDriver:
    """Stubs execute_script for the scheduler-side PRIVATE row scrape.

    Returns the private roster once (per PRIVATE navigation), then []. The
    scheduler calls execute_script(<private scrape JS>); we ignore the JS text
    and serve the roster based on the active filter recorded by the DOM mock.
    """

    def __init__(self, dom, private_rows):
        self._dom = dom
        self._private = list(private_rows)
        self._private_served = False

    def execute_script(self, script, *args):
        # Only the private scrape uses execute_script in the cycle path.
        if self._private_served:
            return []
        self._private_served = True
        return list(self._private)


def _make_scheduler(unlisted_rows, private_rows, dry_run=True, edit_vis="unlisted"):
    s = YouTubeShortsScheduler.__new__(YouTubeShortsScheduler)
    s.channel_key = "move2japan"
    s.channel_id = "UC_TEST"
    s.channel_name = "TestChannel"
    s.channel_tz = None
    s.time_slots = ["5:30 AM"]
    s.max_per_day = 3
    s.dry_run = dry_run
    s.tracker = _FakeTracker()
    dom = _RecordingDOM(unlisted_rows, private_rows, edit_vis=edit_vis)
    s.dom = dom
    s.driver = _FakeDriver(dom, private_rows)
    # ensure_healthy_connection() is called at cycle start; force it healthy.
    s.ensure_healthy_connection = lambda: True
    return s


def _run(s, **kwargs):
    return asyncio.run(s.run_scheduling_cycle(update_metadata=False, **kwargs))


@pytest.fixture(autouse=True)
def _clear_flag(monkeypatch):
    monkeypatch.delenv("YT_SCHEDULE_INCLUDE_PRIVATE", raising=False)
    # Keep optional side-channels off for deterministic mock runs.
    monkeypatch.delenv("YT_SCHEDULER_DO_SYNC", raising=False)
    monkeypatch.delenv("YT_SCHEDULER_POST_AUDIT", raising=False)
    yield


# ---------------------------------------------------------------------------
# Flag resolution (unit)
# ---------------------------------------------------------------------------

def test_resolve_targets_default_unlisted_only():
    s = YouTubeShortsScheduler.__new__(YouTubeShortsScheduler)
    assert s._resolve_visibility_targets() == ["UNLISTED"]


def test_resolve_targets_flag_on(monkeypatch):
    monkeypatch.setenv("YT_SCHEDULE_INCLUDE_PRIVATE", "1")
    s = YouTubeShortsScheduler.__new__(YouTubeShortsScheduler)
    assert s._resolve_visibility_targets() == ["UNLISTED", "PRIVATE"]


def test_resolve_targets_flag_non_one_is_off(monkeypatch):
    # Spec is strict equality to "1"; anything else stays UNLISTED-only.
    monkeypatch.setenv("YT_SCHEDULE_INCLUDE_PRIVATE", "true")
    s = YouTubeShortsScheduler.__new__(YouTubeShortsScheduler)
    assert s._resolve_visibility_targets() == ["UNLISTED"]


# ---------------------------------------------------------------------------
# Flag OFF -> UNLISTED-only (MUST-FAIL guard)
# ---------------------------------------------------------------------------

def test_flag_off_runs_only_unlisted_pass():
    s = _make_scheduler(
        unlisted_rows=[{"video_id": "u1", "title": "U one"}],
        private_rows=[{"video_id": "p1", "title": "P one"}],
    )
    results = _run(s)
    assert results["visibility_targets"] == ["UNLISTED"]
    # navigate called with UNLISTED, NEVER with PRIVATE
    assert "UNLISTED" in s.dom.navigate_calls
    assert "PRIVATE" not in s.dom.navigate_calls


def test_flag_off_never_navigates_private():
    """MUST-FAIL guard: if the private pass ever runs while the flag is off,
    navigate would be called with 'PRIVATE' and this assertion fails."""
    s = _make_scheduler(
        unlisted_rows=[{"video_id": "u1", "title": "U one"}],
        private_rows=[{"video_id": "p1", "title": "P one"}],
    )
    _run(s)
    assert s.dom.navigate_calls.count("PRIVATE") == 0


def test_flag_off_no_private_scheduled():
    s = _make_scheduler(
        unlisted_rows=[{"video_id": "u1", "title": "U one"}],
        private_rows=[{"video_id": "p1", "title": "P one"}],
    )
    results = _run(s)
    scheduled_ids = {v["video_id"] for v in results["scheduled"]}
    assert scheduled_ids == {"u1"}
    assert "p1" not in scheduled_ids


# ---------------------------------------------------------------------------
# Flag ON -> UNLISTED + PRIVATE passes
# ---------------------------------------------------------------------------

def test_flag_on_runs_both_passes(monkeypatch):
    monkeypatch.setenv("YT_SCHEDULE_INCLUDE_PRIVATE", "1")
    s = _make_scheduler(
        unlisted_rows=[{"video_id": "u1", "title": "U one"}],
        private_rows=[{"video_id": "p1", "title": "P one"}],
    )
    results = _run(s)
    assert results["visibility_targets"] == ["UNLISTED", "PRIVATE"]
    assert "UNLISTED" in s.dom.navigate_calls
    assert "PRIVATE" in s.dom.navigate_calls
    scheduled_ids = {v["video_id"] for v in results["scheduled"]}
    assert {"u1", "p1"} <= scheduled_ids


def test_flag_on_private_to_public_log_fires(monkeypatch, caplog):
    monkeypatch.setenv("YT_SCHEDULE_INCLUDE_PRIVATE", "1")
    s = _make_scheduler(
        unlisted_rows=[{"video_id": "u1", "title": "U one"}],
        private_rows=[{"video_id": "p1", "title": "P one"}],
    )
    with caplog.at_level(logging.WARNING):
        _run(s)
    breadcrumbs = [
        r.getMessage() for r in caplog.records
        if r.getMessage().startswith("[PRIVATE->PUBLIC]")
    ]
    assert len(breadcrumbs) == 1, breadcrumbs
    assert "p1" in breadcrumbs[0]
    # No breadcrumb for the unlisted video.
    assert all("u1" not in b for b in breadcrumbs)


def test_flag_on_log_fires_once_per_private_video(monkeypatch, caplog):
    monkeypatch.setenv("YT_SCHEDULE_INCLUDE_PRIVATE", "1")
    s = _make_scheduler(
        unlisted_rows=[{"video_id": "u1", "title": "U one"}],
        private_rows=[
            {"video_id": "p1", "title": "P one"},
            {"video_id": "p2", "title": "P two"},
        ],
    )
    with caplog.at_level(logging.WARNING):
        _run(s)
    breadcrumbs = [
        r.getMessage() for r in caplog.records
        if r.getMessage().startswith("[PRIVATE->PUBLIC]")
    ]
    assert len(breadcrumbs) == 2
    assert {"p1", "p2"} == {b.split()[1] for b in breadcrumbs}


# ---------------------------------------------------------------------------
# Edit-page visibility guard
# ---------------------------------------------------------------------------

def test_edit_guard_accepts_private_on_private_pass(monkeypatch):
    """Non-dry-run: a private edit-page video is scheduled (not skipped) when the
    private pass is active."""
    monkeypatch.setenv("YT_SCHEDULE_INCLUDE_PRIVATE", "1")
    s = _make_scheduler(
        unlisted_rows=[],  # skip straight to the private pass
        private_rows=[{"video_id": "p1", "title": "P one"}],
        dry_run=False,
        edit_vis="private",
    )
    results = _run(s)
    scheduled_ids = {v["video_id"] for v in results["scheduled"]}
    assert "p1" in scheduled_ids
    # Not rejected as wrong visibility.
    assert not any(
        sk.get("video_id") == "p1" and "Wrong visibility" in sk.get("reason", "")
        for sk in results["skipped"]
    )


def test_edit_guard_rejects_private_on_unlisted_pass():
    """Non-dry-run, flag OFF: a video that reads 'private' on the edit page during
    the UNLISTED pass is still rejected as wrong visibility (guard NOT relaxed)."""
    s = _make_scheduler(
        unlisted_rows=[{"video_id": "u1", "title": "U one"}],
        private_rows=[],
        dry_run=False,
        edit_vis="private",  # edit page disagrees with the unlisted list filter
    )
    results = _run(s)
    scheduled_ids = {v["video_id"] for v in results["scheduled"]}
    assert "u1" not in scheduled_ids
    assert any(
        sk.get("video_id") == "u1" and "Wrong visibility" in sk.get("reason", "")
        for sk in results["skipped"]
    )
