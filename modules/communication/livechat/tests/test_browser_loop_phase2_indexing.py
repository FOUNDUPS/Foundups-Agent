"""
Tests for PHASE 2 (VIDEO INDEXING) gating in AutoModeratorDAE._browser_engagement_loop.

Slice: EDGE_LOOP_INDEXING_PHASE1
WSP refs: WSP 5 (coverage), WSP 6 (audit), WSP 84 (reuse run_video_indexing_cycle).

Context
-------
The per-browser engagement loop runs:
    PHASE 1 (comments) -> PHASE 2 (video indexing) -> PHASE 3 (scheduling) -> PHASE 4 (LinkedIn)

Before this slice, PHASE 2 was gated Chrome-only:

    if browser_name == "chrome" and os.getenv("YT_VIDEO_INDEXING_ENABLED", ...):

So the Edge loop (FoundUps / antifaFM, port 9223) NEVER ran PHASE 2 and those
channels were never indexed by the loop. This slice relaxes the gate so PHASE 2
runs for WHICHEVER browser drives the loop, under the SAME YT_VIDEO_INDEXING_ENABLED
flag, reusing run_video_indexing_cycle (which already filters channels by browser).

These tests are MOCK ONLY. No real browser is ever opened:
  - run_video_indexing_cycle is mocked (the only PHASE 2 work) and asserted.
  - PHASE 1 / 3 / 4 are disabled via env flags so the loop isolates PHASE 2.
  - asyncio.sleep is patched to raise CancelledError after the first cycle,
    so the otherwise-infinite `while True` loop runs exactly one cycle.

Non-vacuity: test_edge_loop_runs_phase2_indexing_when_enabled MUST FAIL on the
pre-slice code (Edge skipped PHASE 2 -> mock never called -> assert_called fails).
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure repo root on path (tests may be invoked from various cwds)
_REPO_ROOT = Path(__file__).resolve().parents[5]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from modules.communication.livechat.src.auto_moderator_dae import AutoModeratorDAE


# Env that isolates PHASE 2: disable PHASE 1 (comments), PHASE 3 (shorts),
# PHASE 4 (LinkedIn), and the RotationSupervisor path. Only the indexing flag varies.
_ISOLATE_PHASE2_ENV = {
    "YT_COMMENTS_ENABLED": "false",
    "YT_SHORTS_SCHEDULING_ENABLED": "false",
    "LN_FEED_ENGAGEMENT_ENABLED": "false",
    "YT_USE_ROTATION_SUPERVISOR": "false",
}


def _make_dae():
    """Build a minimal AutoModeratorDAE without the heavyweight __init__.

    The loop only touches a handful of attributes; we set exactly those so no
    real auth / browser / scheduler is constructed.
    """
    dae = object.__new__(AutoModeratorDAE)
    dae.multi_channel_coordinator = MagicMock()
    dae._shorts_scheduler_available = False  # PHASE 3 short-circuits before any work
    dae._skill_trigger = None
    dae._shorts_total_cycles = 0
    dae._shorts_total_scheduled = 0
    dae._shorts_last_cycle_result = None
    return dae


async def _run_one_cycle(browser_name: str, indexing_enabled: bool, mock_indexing_cycle):
    """Drive _browser_engagement_loop for exactly one cycle and return.

    asyncio.sleep is patched to raise CancelledError so the infinite while-loop
    exits after a single pass (the loop re-raises CancelledError cleanly).
    """
    dae = _make_dae()

    env = dict(_ISOLATE_PHASE2_ENV)
    env["YT_VIDEO_INDEXING_ENABLED"] = "true" if indexing_enabled else "false"

    async def _sleep_then_stop(*_args, **_kwargs):
        # End-of-cycle sleep -> stop the loop after one full cycle.
        raise asyncio.CancelledError()

    with patch.dict("os.environ", env, clear=False), \
         patch(
             "modules.ai_intelligence.video_indexer.src.studio_ask_indexer.run_video_indexing_cycle",
             mock_indexing_cycle,
         ), \
         patch(
             "modules.communication.livechat.src.auto_moderator_dae.get_activity_router",
             MagicMock(),
         ), \
         patch("asyncio.sleep", side_effect=_sleep_then_stop):
        with pytest.raises(asyncio.CancelledError):
            await dae._browser_engagement_loop(
                browser_name=browser_name,
                runner=MagicMock(),
                max_comments=0,
                mode="test",
                interval_minutes=10,
                browser_lock=None,
                scheduler_stop_event=None,
            )


@pytest.mark.asyncio
async def test_edge_loop_runs_phase2_indexing_when_enabled():
    """EDGE loop MUST invoke run_video_indexing_cycle for the Edge browser.

    NON-VACUITY: This fails on pre-slice code, where PHASE 2 was gated
    `browser_name == "chrome"` and the Edge loop skipped it entirely.
    """
    mock_cycle = AsyncMock(return_value={"ok": True})
    await _run_one_cycle("edge", indexing_enabled=True, mock_indexing_cycle=mock_cycle)

    mock_cycle.assert_awaited_once()
    # PHASE 2 must run for the Edge channels (FoundUps / antifaFM live behind browser="edge").
    _, kwargs = mock_cycle.call_args
    assert kwargs.get("browser") == "edge", (
        f"Edge loop must index Edge channels, got browser={kwargs.get('browser')!r}"
    )


@pytest.mark.asyncio
async def test_chrome_loop_still_runs_phase2_indexing_when_enabled():
    """Regression: CHROME loop must STILL invoke indexing (M2J/UnDaoDu) for browser=chrome."""
    mock_cycle = AsyncMock(return_value={"ok": True})
    await _run_one_cycle("chrome", indexing_enabled=True, mock_indexing_cycle=mock_cycle)

    mock_cycle.assert_awaited_once()
    _, kwargs = mock_cycle.call_args
    assert kwargs.get("browser") == "chrome", (
        f"Chrome loop must index Chrome channels, got browser={kwargs.get('browser')!r}"
    )


@pytest.mark.asyncio
async def test_edge_loop_skips_phase2_when_indexing_disabled():
    """Regression guard: with YT_VIDEO_INDEXING_ENABLED=false the Edge loop runs NO indexing."""
    mock_cycle = AsyncMock(return_value={"ok": True})
    await _run_one_cycle("edge", indexing_enabled=False, mock_indexing_cycle=mock_cycle)

    mock_cycle.assert_not_awaited()


@pytest.mark.asyncio
async def test_chrome_loop_skips_phase2_when_indexing_disabled():
    """Regression guard: with indexing disabled the Chrome loop also runs NO indexing."""
    mock_cycle = AsyncMock(return_value={"ok": True})
    await _run_one_cycle("chrome", indexing_enabled=False, mock_indexing_cycle=mock_cycle)

    mock_cycle.assert_not_awaited()
