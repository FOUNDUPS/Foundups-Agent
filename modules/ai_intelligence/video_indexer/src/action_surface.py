# -*- coding: utf-8 -*-
"""
Video Indexing Action Surface (SKILLz/ACTION SURFACE) - Phase 1.

A typed, reusable capability surface for video indexing so the CLI menu,
OpenClaw/WRE, Hermes/Kanban, or any 0102 agent can invoke the SAME governed
capability instead of a one-off menu helper.

Model (WSP 27 / WSP 80 / WSP 95):
    SKILLz   = capability contract (the typed action IDs + dataclasses here)
    DAE      = executor (StudioAskIndexer.ask_about_video does the work)
    menu     = operator trigger (indexing_menu.py routes through run_action)
    heartbeat= observability (existing telemetry, not owned here)
    scheduler= artifact CONSUMER (NOT the owner of indexing)

BOUNDARY (HARD - Phase 1):
    - This surface may DESCRIBE and ROUTE an action.
    - It MUST NOT carry credentials, gate-pass state, or self-authorize live
      mutation. 0102 ATTACHES to an already-authenticated browser session via
      the existing dae_dependencies connect helpers (debuggerAddress); it never
      handles credentials.
    - It MUST NOT call GeminiVideoAnalyzer, the Shorts Scheduler, or any
      metadata-mutation / publish / schedule / save_video path.
    - The single_video action routes ONLY to StudioAskIndexer.ask_about_video,
      which navigates + scrapes the Studio "Ask Studio" DOM and returns a
      result. It does NOT edit_title / edit_description / save_video / schedule.

WSP Compliance:
    WSP 11: Interface Protocol (typed inputs/outputs)
    WSP 27: DAE Architecture (Signal -> Knowledge -> Protocol -> Agentic)
    WSP 72: Module Independence
    WSP 84: Code Reuse (reuses StudioAskIndexer + VideoIndexStore; no new store)
    WSP 91: DAE Observability

Phase 1 IMPLEMENTS: video_index.studio_ask.single_video
Phase 1 REGISTERS (NOT wired -> Phase 2): channel_cycle, daemon_cycle,
    gemini_api.single_video, whisper.local_transcript,
    shorts_scheduler.consume_video_index
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Reuse the canonical index root (same as studio_ask_indexer.INDEX_ROOT).
INDEX_ROOT = Path("memory") / "video_index"

# Governed browser -> Chrome DevTools remote-debug port mapping.
# 0102 ATTACHES to an already-authenticated session; it never handles creds.
#   chrome -> 9222 (Move2Japan / UnDaoDu)
#   edge   -> 9223 (FoundUps / antifaFM)
BROWSER_PORTS: Dict[str, int] = {
    "chrome": 9222,
    "edge": 9223,
}


# =============================================================================
# Typed Action IDs
# =============================================================================

class VideoIndexAction:
    """
    Typed action IDs for the video indexing action surface.

    IMPLEMENTED this phase:
        STUDIO_ASK_SINGLE_VIDEO

    REGISTERED as IDs but NOT wired this phase (-> raise NotImplementedError or
    return a 'not_implemented' result). Phase 1 does NOT import Gemini/scheduler.
    """

    # IMPLEMENTED (Phase 1): bounded single-video Studio Ask index test.
    STUDIO_ASK_SINGLE_VIDEO = "video_index.studio_ask.single_video"

    # REGISTERED ONLY (Phase 2+): not wired this phase.
    STUDIO_ASK_CHANNEL_CYCLE = "video_index.studio_ask.channel_cycle"
    STUDIO_ASK_DAEMON_CYCLE = "video_index.studio_ask.daemon_cycle"
    GEMINI_API_SINGLE_VIDEO = "video_index.gemini_api.single_video"
    WHISPER_LOCAL_TRANSCRIPT = "video_index.whisper.local_transcript"
    SHORTS_SCHEDULER_CONSUME = "shorts_scheduler.consume_video_index"


# All action IDs the surface knows about (impl + registered).
ALL_ACTION_IDS = (
    VideoIndexAction.STUDIO_ASK_SINGLE_VIDEO,
    VideoIndexAction.STUDIO_ASK_CHANNEL_CYCLE,
    VideoIndexAction.STUDIO_ASK_DAEMON_CYCLE,
    VideoIndexAction.GEMINI_API_SINGLE_VIDEO,
    VideoIndexAction.WHISPER_LOCAL_TRANSCRIPT,
    VideoIndexAction.SHORTS_SCHEDULER_CONSUME,
)

# Subset implemented (routes to real work) this phase.
IMPLEMENTED_ACTION_IDS = (
    VideoIndexAction.STUDIO_ASK_SINGLE_VIDEO,
)

# Subset registered-but-not-wired this phase.
REGISTERED_ONLY_ACTION_IDS = tuple(
    a for a in ALL_ACTION_IDS if a not in IMPLEMENTED_ACTION_IDS
)


# =============================================================================
# Typed I/O dataclasses
# =============================================================================

@dataclass
class StudioAskSingleVideoInput:
    """
    Typed input for video_index.studio_ask.single_video.

    Args:
        video_id: Raw YouTube video ID OR a watch/Studio URL. A URL is parsed
            down to the bare 11-char video ID (see parse_video_id).
        browser: 'chrome' (port 9222) or 'edge' (port 9223). 0102 attaches to
            an already-authenticated session on that port.
        channel_id: Optional YouTube channel ID. Used only to resolve the
            channel-specific Ask prompt + the persist folder key. NOT required.
        persist: When True (default), a successful result is written to
            memory/video_index/{channel}/{video_id}.json via VideoIndexStore.
    """

    video_id: str
    browser: str = "chrome"
    channel_id: Optional[str] = None
    persist: bool = True


@dataclass
class StudioAskSingleVideoOutput:
    """Typed output for video_index.studio_ask.single_video (no secrets)."""

    success: bool
    video_id: str
    browser: str
    provider: str = "studio_ask"
    response_text_length: int = 0
    topics_count: int = 0
    saved_path: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# Helpers
# =============================================================================

def parse_video_id(value: str) -> str:
    """
    Accept a raw video ID OR a YouTube/Studio URL and return the bare video ID.

    Recognized URL shapes:
        https://www.youtube.com/watch?v=VIDEOID
        https://youtu.be/VIDEOID
        https://studio.youtube.com/video/VIDEOID/edit
        https://www.youtube.com/shorts/VIDEOID
    A bare ID is returned unchanged (whitespace stripped).
    """
    if not value:
        return value
    raw = value.strip()

    # studio.youtube.com/video/<id>/edit  OR  /video/<id>
    m = re.search(r"/video/([^/?&#]+)", raw)
    if m:
        return m.group(1)
    # watch?v=<id>  (or &v=<id>)
    m = re.search(r"[?&]v=([^&#]+)", raw)
    if m:
        return m.group(1)
    # youtu.be/<id>  OR  /shorts/<id>  OR  /embed/<id>
    m = re.search(r"(?:youtu\.be/|/shorts/|/embed/)([^/?&#]+)", raw)
    if m:
        return m.group(1)
    # No URL markers -> treat as a bare ID.
    return raw


def port_for_browser(browser: str) -> int:
    """Resolve the Chrome DevTools remote-debug port for a browser label."""
    key = (browser or "").strip().lower()
    if key not in BROWSER_PORTS:
        raise ValueError(
            f"Unknown browser '{browser}'. Expected one of {sorted(BROWSER_PORTS)}."
        )
    return BROWSER_PORTS[key]


def _connect_attached_driver(browser: str):
    """
    Attach to the already-authenticated browser session on the governed port.

    Reuses the existing dae_dependencies connect helpers (which own the
    9222/9223 mapping + debuggerAddress attach). NO credentials handled here.
    Returns a Selenium driver or None on failure.
    """
    # Validate/normalize the port mapping up-front (fail-closed on bad browser).
    _ = port_for_browser(browser)
    key = browser.strip().lower()

    from modules.infrastructure.dependency_launcher.src.dae_dependencies import (
        connect_chrome_with_retry,
        connect_edge_with_retry,
    )
    if key == "edge":
        return connect_edge_with_retry(max_retries=3, retry_delay=2.0)
    return connect_chrome_with_retry(max_retries=3, retry_delay=2.0)


# =============================================================================
# Single-video action (IMPLEMENTED this phase)
# =============================================================================

async def run_studio_ask_single_video(
    inp: StudioAskSingleVideoInput,
) -> StudioAskSingleVideoOutput:
    """
    Run a bounded, single-video Studio "Ask Studio" index (Phase 1).

    Routes ONLY to StudioAskIndexer.ask_about_video. It NEVER calls Gemini,
    the Shorts Scheduler, or any metadata-mutation / publish / schedule path.

    Flow:
        1. Parse the bare video ID (accepts raw ID or URL).
        2. Attach to the governed browser session (chrome->9222 / edge->9223).
        3. Construct StudioAskIndexer(driver=...) and await ask_about_video().
        4. IF persist AND success: write the result to
           memory/video_index/{channel}/{video_id}.json via VideoIndexStore
           (reusing StudioAskIndexer._ask_result_to_index_data; no new store).
        5. Map -> typed output. On any failure return success=False + error
           (fail-closed).
    """
    # Lazy, module-specific imports (NOT the package __init__) so this code
    # path never imports/uses GeminiVideoAnalyzer.
    from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import (
        StudioAskIndexer,
    )
    from modules.ai_intelligence.video_indexer.src.video_index_store import (
        VideoIndexStore,
    )

    video_id = parse_video_id(inp.video_id)
    browser = (inp.browser or "chrome").strip().lower()

    # Resolve the channel folder key + registry entry (best-effort; optional).
    channel_key = "test"
    channel_entry: Optional[Dict[str, Any]] = None
    if inp.channel_id:
        try:
            from modules.infrastructure.shared_utilities.youtube_channel_registry import (
                get_channel_by_id,
            )
            channel_entry = get_channel_by_id(inp.channel_id)
            if channel_entry:
                channel_key = channel_entry.get("key") or inp.channel_id
            else:
                channel_key = inp.channel_id
        except Exception as e:  # registry optional; never fail the action on it
            logger.debug(f"[ACTION-SURFACE] channel registry lookup skipped: {e}")
            channel_key = inp.channel_id

    # Validate browser/port up-front (fail-closed).
    try:
        port_for_browser(browser)
    except ValueError as e:
        return StudioAskSingleVideoOutput(
            success=False, video_id=video_id, browser=browser, error=str(e),
        )

    # Attach to the governed, already-authenticated browser session.
    try:
        driver = _connect_attached_driver(browser)
    except Exception as e:
        logger.error(f"[ACTION-SURFACE] browser attach failed: {e}")
        return StudioAskSingleVideoOutput(
            success=False, video_id=video_id, browser=browser,
            error=f"browser attach failed: {e}",
        )
    if driver is None:
        return StudioAskSingleVideoOutput(
            success=False, video_id=video_id, browser=browser,
            error=f"could not attach to {browser} session (port "
                  f"{BROWSER_PORTS.get(browser)})",
        )

    # Run the bounded Studio Ask (navigate + scrape only; no mutation).
    try:
        indexer = StudioAskIndexer(driver=driver)
        ask_result = await indexer.ask_about_video(
            video_id, channel_entry=channel_entry,
        )
    except Exception as e:
        logger.error(f"[ACTION-SURFACE] ask_about_video error: {e}")
        return StudioAskSingleVideoOutput(
            success=False, video_id=video_id, browser=browser,
            error=str(e),
        )

    if not ask_result.success:
        return StudioAskSingleVideoOutput(
            success=False, video_id=video_id, browser=browser,
            response_text_length=len(ask_result.response_text or ""),
            topics_count=len(ask_result.topics or []),
            error=ask_result.error or "ask_about_video returned success=False",
        )

    # Persist ONLY when requested AND the ask succeeded (fail-closed otherwise).
    saved_path: Optional[str] = None
    if inp.persist:
        try:
            index_data = StudioAskIndexer._ask_result_to_index_data(
                ask_result, channel_key=channel_key,
            )
            store = VideoIndexStore(base_path=str(INDEX_ROOT / channel_key))
            saved_path = store.save_index(video_id, index_data)
        except Exception as e:
            logger.error(f"[ACTION-SURFACE] persist failed: {e}")
            # Persist failure is reported but the ask itself succeeded.
            return StudioAskSingleVideoOutput(
                success=False, video_id=video_id, browser=browser,
                response_text_length=len(ask_result.response_text or ""),
                topics_count=len(ask_result.topics or []),
                error=f"persist failed: {e}",
            )

    return StudioAskSingleVideoOutput(
        success=True, video_id=video_id, browser=browser,
        response_text_length=len(ask_result.response_text or ""),
        topics_count=len(ask_result.topics or []),
        saved_path=saved_path,
    )


# =============================================================================
# Registered-only actions (NOT wired this phase)
# =============================================================================

def _not_implemented(action_id: str) -> Dict[str, Any]:
    """Uniform 'not_implemented' result for registered-but-unwired actions."""
    return {
        "action_id": action_id,
        "status": "not_implemented",
        "phase": "Phase 2",
        "detail": (
            f"Action '{action_id}' is registered as an ID but not wired in "
            f"Phase 1. Do not route live work through it yet."
        ),
    }


# =============================================================================
# Dispatcher
# =============================================================================

async def run_action(action_id: str, **kwargs) -> Any:
    """
    Route a call to the action surface by typed action ID.

    IMPLEMENTED:
        video_index.studio_ask.single_video
            kwargs -> StudioAskSingleVideoInput fields
            (video_id, browser, channel_id, persist) OR pass inp=<dataclass>.
            Returns StudioAskSingleVideoOutput.

    REGISTERED ONLY (Phase 2 - NOT wired): returns a 'not_implemented' result
    dict. NEVER imports Gemini/scheduler from here.

    Unknown action IDs raise ValueError (fail-closed).
    """
    if action_id == VideoIndexAction.STUDIO_ASK_SINGLE_VIDEO:
        inp = kwargs.get("inp")
        if inp is None:
            inp = StudioAskSingleVideoInput(
                video_id=kwargs["video_id"],
                browser=kwargs.get("browser", "chrome"),
                channel_id=kwargs.get("channel_id"),
                persist=kwargs.get("persist", True),
            )
        return await run_studio_ask_single_video(inp)

    if action_id in REGISTERED_ONLY_ACTION_IDS:
        return _not_implemented(action_id)

    raise ValueError(
        f"Unknown action_id '{action_id}'. Known IDs: {list(ALL_ACTION_IDS)}"
    )
