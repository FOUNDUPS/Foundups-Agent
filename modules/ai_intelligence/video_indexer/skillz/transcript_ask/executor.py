# -*- coding: utf-8 -*-
"""Adapter from the legacy ``transcript_ask`` skill name to the action surface.

The Studio Ask response is a semantic video index, not a verbatim transcript.
This executor delegates every live path to the canonical action surface so
OpenClaw, the CLI, and direct skill calls share the same guards.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


async def execute_skill(
    video_id: Optional[str] = None,
    channel: str = "undaodu",
    driver=None,
    mode: str = "single",
    browser: Optional[str] = None,
    max_videos: int = 10,
    max_cycles: int = 1,
    force_reindex: bool = False,
) -> Dict[str, Any]:
    """Run a Studio Ask index action.

    ``driver`` remains for call compatibility but is intentionally unused;
    governed actions attach through the configured browser-debug port.
    """
    del driver

    from modules.ai_intelligence.video_indexer.src.action_surface import (
        StudioAskChannelCycleInput,
        StudioAskPortfolioCycleInput,
        StudioAskSingleVideoInput,
        VideoIndexAction,
        run_action,
    )
    from modules.infrastructure.shared_utilities.youtube_channel_registry import (
        get_channel_by_key,
    )

    normalized_mode = (mode or "single").strip().lower()
    if normalized_mode == "portfolio":
        return await run_action(
            VideoIndexAction.STUDIO_ASK_PORTFOLIO_CYCLE,
            inp=StudioAskPortfolioCycleInput(
                max_videos_per_channel=max_videos,
                force_reindex=force_reindex,
            ),
        )

    entry = get_channel_by_key(channel)
    if not entry or not entry.get("id"):
        return {"success": False, "error": f"unknown channel: {channel}"}
    channel_id = str(entry["id"])
    selected_browser = browser or str(
        (entry.get("browser") or {}).get("comment_browser") or "chrome"
    )

    if normalized_mode == "single":
        if not video_id:
            return {"success": False, "error": "video_id is required for single mode"}
        result = await run_action(
            VideoIndexAction.STUDIO_ASK_SINGLE_VIDEO,
            inp=StudioAskSingleVideoInput(
                video_id=video_id,
                browser=selected_browser,
                channel_id=channel_id,
                persist=True,
            ),
        )
        return result.__dict__

    if normalized_mode == "channel":
        return await run_action(
            VideoIndexAction.STUDIO_ASK_CHANNEL_CYCLE,
            inp=StudioAskChannelCycleInput(
                channel_id=channel_id,
                browser=selected_browser,
                max_videos=max_videos,
                force_reindex=force_reindex,
            ),
        )

    if normalized_mode == "daemon":
        return await run_action(
            VideoIndexAction.STUDIO_ASK_DAEMON_CYCLE,
            channels=[channel_id],
            browser=selected_browser,
            max_videos_per_channel=max_videos,
            max_cycles=max_cycles,
        )

    return {
        "success": False,
        "error": "mode must be one of: single, channel, portfolio, daemon",
    }
