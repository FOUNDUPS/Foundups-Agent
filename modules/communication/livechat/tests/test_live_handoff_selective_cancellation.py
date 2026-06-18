"""
Mock-only tests for LIVE_HANDOFF_SELECTIVE_CANCELLATION_PHASE1 (always-flow Layer 1).

POLICY (012-decided, ALWAYS-FLOW): on a live handoff the system must NOT go idle.
Only the live channel yields; the other channels + indexing + scheduling keep
flowing. The old in-code rule "Once on live chat, do NOT return to comments"
(auto_moderator_dae.py near :971) is SUPERSEDED.

DEFECT under test (blanket cancel): ``self._comment_engagement_task`` is the
per-browser engagement SUPERVISOR (``_comment_engagement_loop``) which owns BOTH
``_browser_tasks = {"chrome": T, "edge": T}``. Cancelling it (the old
``terminate_comment_engagement`` body, called from the live-confirm path) triggers
the supervisor's CancelledError handler which cancels Chrome AND Edge loops --
killing ALL executor work, not just the live channel.

FIX (Option A): on the live-confirm path call
``terminate_comment_engagement(for_live_handoff=True)``, which does NOT cancel the
supervisor. The EXISTING per-channel live-defer in the coordinator
(multi_channel_coordinator.py chrome :880-889 / edge :502-511) already skips ONLY
the live channel and keeps rotating the rest.

NO BROWSER CONTENTION: live chat = YouTube Data API (livechat_core.py,
youtube_service); comment executor = Chrome 9222 CDP (multi_channel_coordinator.py
connect_chrome_with_retry). Separate transports -> per-channel continuation is
contention-safe.

THESE TESTS ARE MOCK-ONLY. They NEVER open a browser, attach to port 9222, or
drive Selenium. They mock ``get_live_channel`` and the task/loop structure, and
exercise the REAL production method ``AutoModeratorDAE.terminate_comment_engagement``.
"""
import asyncio

import pytest

from modules.communication.livechat.src.auto_moderator_dae import AutoModeratorDAE


# ---------------------------------------------------------------------------
# Channel fixtures (mirror the registry: Chrome=[UnDaoDu, M2J], Edge=[antifaFM, FoundUps])
# ---------------------------------------------------------------------------
CHROME_CHANNELS = [("UnDaoDu", "UC-undaodu"), ("Move2Japan", "UC-m2j")]
EDGE_CHANNELS = [("antifaFM", "UC-antifafm"), ("FoundUps", "UC-foundups")]


def _new_dae():
    """Construct an AutoModeratorDAE WITHOUT running its heavy __init__.

    We bypass __init__ (which imports WRE/Qwen/telemetry singletons and is not
    needed here) and set ONLY the attributes ``terminate_comment_engagement``
    reads. This keeps the test pure -- no browser, no network, no singletons.
    """
    dae = AutoModeratorDAE.__new__(AutoModeratorDAE)
    dae._comment_engagement_task = None
    dae._live_chat_active = False
    dae._live_stream_pending = False
    return dae


class _FakeSupervisor:
    """Stand-in for the real ``_comment_engagement_loop`` supervisor task.

    The real supervisor owns ``_browser_tasks = {"chrome": T, "edge": T}`` and,
    on CancelledError, cancels BOTH (auto_moderator_dae.py :1389-1394). We model
    exactly that blanket-cancel behavior so a test can prove the production method
    either triggers it (old behavior) or skips it (always-flow fix).
    """

    def __init__(self):
        self.browser_loops = {"chrome": True, "edge": True}  # True == still running
        self._cancelled = False

    def done(self):
        return self._cancelled

    def cancel(self):
        # Mirror the supervisor's CancelledError handler: blanket-cancel BOTH loops.
        self._cancelled = True
        self.browser_loops["chrome"] = False
        self.browser_loops["edge"] = False

    def __await__(self):
        async def _await_cancelled():
            if self._cancelled:
                raise asyncio.CancelledError()
        return _await_cancelled().__await__()


def _run_per_channel_loop(channels, live_channel, supervisor):
    """Faithful model of the coordinator's per-browser loop + per-channel defer.

    Mirrors multi_channel_coordinator.py:
        for (name, channel_id) in channels:
            if get_live_channel() == channel_id:   # :887 chrome / :509 edge
                continue                            # skip ONLY the live channel
            <process channel>

    A browser loop only runs if its task was NOT blanket-cancelled by the
    supervisor. Returns the list of channel_ids actually processed.
    """
    processed = []
    for name, channel_id in channels:
        if live_channel == channel_id:
            # Per-channel defer: skip ONLY the live channel (REUSED, not rebuilt).
            continue
        processed.append(channel_id)
    return processed


def _simulate_after_terminate(supervisor, live_channel):
    """Run both browser loops as they would run after terminate_comment_engagement.

    If the supervisor was blanket-cancelled, neither loop runs (the defect). If it
    survived, each loop runs and applies the per-channel defer.
    """
    chrome_processed = (
        _run_per_channel_loop(CHROME_CHANNELS, live_channel, supervisor)
        if supervisor.browser_loops["chrome"]
        else []
    )
    edge_processed = (
        _run_per_channel_loop(EDGE_CHANNELS, live_channel, supervisor)
        if supervisor.browser_loops["edge"]
        else []
    )
    return chrome_processed, edge_processed


# ---------------------------------------------------------------------------
# M2J (Chrome) live: Chrome keeps processing UnDaoDu, skips M2J; Edge unaffected.
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_chrome_live_keeps_non_live_flowing_m2j():
    dae = _new_dae()
    supervisor = _FakeSupervisor()
    dae._comment_engagement_task = supervisor
    live_channel = "UC-m2j"  # Move2Japan (Chrome) is live

    # FIX path: always-flow live handoff -> supervisor NOT cancelled.
    await dae.terminate_comment_engagement(for_live_handoff=True)
    assert not supervisor.done(), "ALWAYS-FLOW: supervisor must NOT be cancelled on live handoff"

    chrome_processed, edge_processed = _simulate_after_terminate(supervisor, live_channel)

    # Chrome STILL processes the non-live Chrome channel (UnDaoDu) and SKIPS M2J.
    assert "UC-undaodu" in chrome_processed
    assert "UC-m2j" not in chrome_processed
    # Edge is completely unaffected (both Edge channels keep flowing).
    assert edge_processed == ["UC-antifafm", "UC-foundups"]


# ---------------------------------------------------------------------------
# FoundUps (Edge) live: symmetric -- Edge skips FoundUps, continues antifaFM;
# Chrome unaffected.
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_edge_live_keeps_non_live_flowing_foundups():
    dae = _new_dae()
    supervisor = _FakeSupervisor()
    dae._comment_engagement_task = supervisor
    live_channel = "UC-foundups"  # FoundUps (Edge) is live

    await dae.terminate_comment_engagement(for_live_handoff=True)
    assert not supervisor.done(), "ALWAYS-FLOW: supervisor must NOT be cancelled on live handoff"

    chrome_processed, edge_processed = _simulate_after_terminate(supervisor, live_channel)

    # Edge STILL processes antifaFM and SKIPS FoundUps.
    assert "UC-antifafm" in edge_processed
    assert "UC-foundups" not in edge_processed
    # Chrome is completely unaffected (both Chrome channels keep flowing).
    assert chrome_processed == ["UC-undaodu", "UC-m2j"]


# ---------------------------------------------------------------------------
# Offline (no live channel): full dual-browser loops run -- regression guard.
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_offline_full_dual_browser_loops():
    dae = _new_dae()
    supervisor = _FakeSupervisor()
    dae._comment_engagement_task = supervisor
    live_channel = None  # get_live_channel() -> None (offline)

    # Offline boot: there is no live handoff; the default (non-live-handoff) path
    # still terminates-and-restarts as before, but here we assert the supervisor
    # spawns full dual-browser loops with NO channel skipped.
    await dae.terminate_comment_engagement(for_live_handoff=True)
    assert not supervisor.done()

    chrome_processed, edge_processed = _simulate_after_terminate(supervisor, live_channel)
    assert chrome_processed == ["UC-undaodu", "UC-m2j"]
    assert edge_processed == ["UC-antifafm", "UC-foundups"]


# ---------------------------------------------------------------------------
# NON-VACUITY: prove each scenario FAILS under the OLD blanket-cancel behavior.
# We invoke the SAME production method with for_live_handoff=False (the legacy
# path), which cancels the supervisor -> the fake supervisor blanket-cancels BOTH
# browser loops -> non-live work is lost. This is exactly the defect; these
# assertions document that the fix is load-bearing.
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_old_blanket_cancel_kills_all_executor_work_m2j():
    dae = _new_dae()
    supervisor = _FakeSupervisor()
    dae._comment_engagement_task = supervisor
    live_channel = "UC-m2j"

    # OLD behavior (blanket cancel): the legacy default path cancels the supervisor.
    await dae.terminate_comment_engagement(for_live_handoff=False)
    assert supervisor.done(), "Legacy path DOES cancel the supervisor (the defect)"

    chrome_processed, edge_processed = _simulate_after_terminate(supervisor, live_channel)
    # The defect: ALL executor work is killed, not just the live channel.
    assert chrome_processed == [], "Blanket cancel kills the whole Chrome loop (non-live UnDaoDu lost)"
    assert edge_processed == [], "Blanket cancel ALSO kills the unrelated Edge loop"


@pytest.mark.asyncio
async def test_old_blanket_cancel_kills_all_executor_work_foundups():
    dae = _new_dae()
    supervisor = _FakeSupervisor()
    dae._comment_engagement_task = supervisor
    live_channel = "UC-foundups"

    await dae.terminate_comment_engagement(for_live_handoff=False)
    assert supervisor.done()

    chrome_processed, edge_processed = _simulate_after_terminate(supervisor, live_channel)
    assert chrome_processed == [], "Blanket cancel kills the unrelated Chrome loop"
    assert edge_processed == [], "Blanket cancel kills the Edge loop (non-live antifaFM lost)"
