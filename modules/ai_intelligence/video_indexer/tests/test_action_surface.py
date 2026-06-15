# -*- coding: utf-8 -*-
"""
Tests for the video indexing typed SKILLz/ACTION SURFACE (Phase 1).

NO live browser: StudioAskIndexer / its driver / ask_about_video and the
dae_dependencies connect helpers are mocked. Asserts the single_video action
routes ONLY to ask_about_video and provably never calls GeminiVideoAnalyzer,
the Shorts Scheduler, or any metadata-mutation / publish / schedule path.

WSP Compliance:
    WSP 5/6: Test coverage + audit
    WSP 72: Module Independence (no cross-module live calls)
    WSP 84: Code Reuse (asserts reuse of VideoIndexStore path shape)
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.ai_intelligence.video_indexer.src import action_surface as A
from modules.ai_intelligence.video_indexer.src.action_surface import (
    ALL_ACTION_IDS,
    BROWSER_PORTS,
    IMPLEMENTED_ACTION_IDS,
    REGISTERED_ONLY_ACTION_IDS,
    StudioAskSingleVideoInput,
    StudioAskSingleVideoOutput,
    VideoIndexAction,
    parse_video_id,
    port_for_browser,
    run_action,
    run_studio_ask_single_video,
)
from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import AskResult


def _ok_ask_result(video_id="vid123"):
    return AskResult(
        video_id=video_id,
        title="Test Video",
        response_text="Topics covered: memory, WSP",
        topics=["memory", "WSP"],
        timestamps=[
            {"time": "0:10", "topic": "Memory", "summary": "Memory basics"},
        ],
        success=True,
    )


def _patched_indexer(ask_result):
    """Build a MagicMock StudioAskIndexer instance whose ask_about_video is async."""
    inst = MagicMock(name="StudioAskIndexerInstance")
    inst.ask_about_video = AsyncMock(return_value=ask_result)
    return inst


# =============================================================================
# Action ID registry
# =============================================================================

def test_single_video_is_implemented_id():
    assert VideoIndexAction.STUDIO_ASK_SINGLE_VIDEO == "video_index.studio_ask.single_video"
    assert VideoIndexAction.STUDIO_ASK_SINGLE_VIDEO in IMPLEMENTED_ACTION_IDS


def test_registered_only_ids_present_not_implemented():
    expected_registered = {
        VideoIndexAction.STUDIO_ASK_CHANNEL_CYCLE,
        VideoIndexAction.STUDIO_ASK_DAEMON_CYCLE,
        VideoIndexAction.GEMINI_API_SINGLE_VIDEO,
        VideoIndexAction.WHISPER_LOCAL_TRANSCRIPT,
        VideoIndexAction.SHORTS_SCHEDULER_CONSUME,
    }
    assert expected_registered.issubset(set(REGISTERED_ONLY_ACTION_IDS))
    # single_video must NOT be in the registered-only set.
    assert VideoIndexAction.STUDIO_ASK_SINGLE_VIDEO not in REGISTERED_ONLY_ACTION_IDS
    # All declared IDs are covered by impl + registered-only, no overlap.
    assert set(ALL_ACTION_IDS) == set(IMPLEMENTED_ACTION_IDS) | set(REGISTERED_ONLY_ACTION_IDS)


def test_shorts_scheduler_consume_is_separate_registered_id():
    """consume_video_index is a SEPARATE registered ID, not an indexing action."""
    assert VideoIndexAction.SHORTS_SCHEDULER_CONSUME == "shorts_scheduler.consume_video_index"
    assert VideoIndexAction.SHORTS_SCHEDULER_CONSUME in REGISTERED_ONLY_ACTION_IDS

    # Dispatching it returns 'not_implemented' and never runs an indexing action.
    out = asyncio.run(run_action(VideoIndexAction.SHORTS_SCHEDULER_CONSUME))
    assert isinstance(out, dict)
    assert out["status"] == "not_implemented"
    assert out["action_id"] == VideoIndexAction.SHORTS_SCHEDULER_CONSUME


def test_unknown_action_id_raises():
    with pytest.raises(ValueError):
        asyncio.run(run_action("video_index.does.not.exist"))


# =============================================================================
# URL / browser parsing
# =============================================================================

@pytest.mark.parametrize("url,expected", [
    ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s", "dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://studio.youtube.com/video/dQw4w9WgXcQ/edit", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
])
def test_parse_video_id(url, expected):
    assert parse_video_id(url) == expected


def test_browser_port_mapping():
    assert BROWSER_PORTS["chrome"] == 9222
    assert BROWSER_PORTS["edge"] == 9223
    assert port_for_browser("chrome") == 9222
    assert port_for_browser("CHROME") == 9222
    assert port_for_browser("edge") == 9223
    with pytest.raises(ValueError):
        port_for_browser("firefox")


def test_single_video_url_parsed_to_bare_id():
    """A raw URL input is parsed down to the bare video id in the output."""
    ask_result = _ok_ask_result(video_id="dQw4w9WgXcQ")
    inst = _patched_indexer(ask_result)
    with patch.object(A, "_connect_attached_driver", return_value=MagicMock()), \
         patch("modules.ai_intelligence.video_indexer.src.studio_ask_indexer.StudioAskIndexer",
               return_value=inst):
        out = asyncio.run(run_studio_ask_single_video(
            StudioAskSingleVideoInput(
                video_id="https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=9s",
                browser="chrome",
                persist=False,
            )
        ))
    assert out.video_id == "dQw4w9WgXcQ"
    # ask_about_video received the bare id, not the URL.
    inst.ask_about_video.assert_awaited_once()
    assert inst.ask_about_video.await_args.args[0] == "dQw4w9WgXcQ"


# =============================================================================
# single_video routes to ask_about_video + typed output
# =============================================================================

def test_single_video_calls_ask_about_video_returns_typed_output():
    ask_result = _ok_ask_result()
    inst = _patched_indexer(ask_result)
    with patch.object(A, "_connect_attached_driver", return_value=MagicMock()), \
         patch("modules.ai_intelligence.video_indexer.src.studio_ask_indexer.StudioAskIndexer",
               return_value=inst):
        out = asyncio.run(run_studio_ask_single_video(
            StudioAskSingleVideoInput(video_id="vid123", browser="chrome", persist=False)
        ))
    inst.ask_about_video.assert_awaited_once()
    assert isinstance(out, StudioAskSingleVideoOutput)
    assert out.success is True
    assert out.video_id == "vid123"
    assert out.provider == "studio_ask"
    assert out.browser == "chrome"
    assert out.response_text_length == len("Topics covered: memory, WSP")
    assert out.topics_count == 2
    assert out.saved_path is None  # persist=False


def test_single_video_fail_closed_when_ask_fails():
    ask_result = AskResult(
        video_id="vid123", title="", response_text="", topics=[],
        timestamps=[], success=False, error="Ask Studio response timeout (no DOM text)",
    )
    inst = _patched_indexer(ask_result)
    with patch.object(A, "_connect_attached_driver", return_value=MagicMock()), \
         patch("modules.ai_intelligence.video_indexer.src.studio_ask_indexer.StudioAskIndexer",
               return_value=inst):
        out = asyncio.run(run_studio_ask_single_video(
            StudioAskSingleVideoInput(video_id="vid123", browser="chrome", persist=True)
        ))
    assert out.success is False
    assert out.saved_path is None
    assert "timeout" in (out.error or "")


def test_single_video_fail_closed_when_no_driver():
    with patch.object(A, "_connect_attached_driver", return_value=None):
        out = asyncio.run(run_studio_ask_single_video(
            StudioAskSingleVideoInput(video_id="vid123", browser="edge", persist=True)
        ))
    assert out.success is False
    assert "9223" in (out.error or "")


# =============================================================================
# Persistence path shape (memory/video_index/{channel}/{video_id}.json)
# =============================================================================

def test_single_video_persists_only_when_persist_and_success():
    ask_result = _ok_ask_result()
    inst = _patched_indexer(ask_result)

    fake_store = MagicMock(name="VideoIndexStore")
    fake_store.save_index.return_value = "memory/video_index/test/vid123.json"
    store_ctor = MagicMock(return_value=fake_store)

    with patch.object(A, "_connect_attached_driver", return_value=MagicMock()), \
         patch("modules.ai_intelligence.video_indexer.src.studio_ask_indexer.StudioAskIndexer",
               return_value=inst), \
         patch("modules.ai_intelligence.video_indexer.src.video_index_store.VideoIndexStore",
               store_ctor):
        out = asyncio.run(run_studio_ask_single_video(
            StudioAskSingleVideoInput(video_id="vid123", browser="chrome", persist=True)
        ))

    # Store constructed with base_path memory/video_index/{channel}.
    store_ctor.assert_called_once()
    base_path = store_ctor.call_args.kwargs.get("base_path") or store_ctor.call_args.args[0]
    assert base_path.replace("\\", "/").endswith("memory/video_index/test")
    # save_index called with the bare video id.
    fake_store.save_index.assert_called_once()
    assert fake_store.save_index.call_args.args[0] == "vid123"
    assert out.saved_path.replace("\\", "/") == "memory/video_index/test/vid123.json"


def test_single_video_does_not_persist_when_persist_false():
    ask_result = _ok_ask_result()
    inst = _patched_indexer(ask_result)
    store_ctor = MagicMock(name="VideoIndexStoreCtor")

    with patch.object(A, "_connect_attached_driver", return_value=MagicMock()), \
         patch("modules.ai_intelligence.video_indexer.src.studio_ask_indexer.StudioAskIndexer",
               return_value=inst), \
         patch("modules.ai_intelligence.video_indexer.src.video_index_store.VideoIndexStore",
               store_ctor):
        out = asyncio.run(run_studio_ask_single_video(
            StudioAskSingleVideoInput(video_id="vid123", browser="chrome", persist=False)
        ))
    store_ctor.assert_not_called()
    assert out.saved_path is None


def test_single_video_uses_channel_key_in_path():
    """When channel_id resolves to a registry key, the path uses that key."""
    ask_result = _ok_ask_result()
    inst = _patched_indexer(ask_result)
    fake_store = MagicMock()
    fake_store.save_index.return_value = "memory/video_index/undaodu/vid123.json"
    store_ctor = MagicMock(return_value=fake_store)

    with patch.object(A, "_connect_attached_driver", return_value=MagicMock()), \
         patch("modules.ai_intelligence.video_indexer.src.studio_ask_indexer.StudioAskIndexer",
               return_value=inst), \
         patch("modules.ai_intelligence.video_indexer.src.video_index_store.VideoIndexStore",
               store_ctor), \
         patch("modules.infrastructure.shared_utilities.youtube_channel_registry.get_channel_by_id",
               return_value={"key": "undaodu", "name": "UnDaoDu"}):
        asyncio.run(run_studio_ask_single_video(
            StudioAskSingleVideoInput(
                video_id="vid123", browser="chrome",
                channel_id="UCfHM9Fw9HD-NwiS0seD_oIA", persist=True,
            )
        ))
    base_path = store_ctor.call_args.kwargs.get("base_path") or store_ctor.call_args.args[0]
    assert base_path.replace("\\", "/").endswith("memory/video_index/undaodu")


# =============================================================================
# BOUNDARY: Gemini + scheduler + metadata mutation provably NOT called
# =============================================================================

def test_single_video_does_not_call_gemini_video_analyzer():
    ask_result = _ok_ask_result()
    inst = _patched_indexer(ask_result)

    gemini_mock = MagicMock(side_effect=AssertionError("GeminiVideoAnalyzer MUST NOT be called"))

    with patch.object(A, "_connect_attached_driver", return_value=MagicMock()), \
         patch("modules.ai_intelligence.video_indexer.src.studio_ask_indexer.StudioAskIndexer",
               return_value=inst), \
         patch("modules.ai_intelligence.video_indexer.src.gemini_video_analyzer.GeminiVideoAnalyzer",
               gemini_mock):
        out = asyncio.run(run_studio_ask_single_video(
            StudioAskSingleVideoInput(video_id="vid123", browser="chrome", persist=False)
        ))
    assert out.success is True
    gemini_mock.assert_not_called()


def test_single_video_does_not_call_scheduler_or_mutate_metadata():
    """Patch every scheduler mutation method to raise-if-called; assert untouched."""
    ask_result = _ok_ask_result()
    inst = _patched_indexer(ask_result)

    from modules.platform_integration.youtube_shorts_scheduler.src import (
        dom_automation as dom_mod,
    )

    raise_if_called = MagicMock(side_effect=AssertionError("scheduler mutation MUST NOT be called"))

    # The Studio DOM scheduler class that owns metadata-mutation methods.
    scheduler_dom_cls = dom_mod.YouTubeStudioDOM

    patches = []
    for method in ("edit_title", "edit_description", "save_video", "schedule_video"):
        if hasattr(scheduler_dom_cls, method):
            patches.append(patch.object(scheduler_dom_cls, method, raise_if_called))
    # Sanity: at least one real mutation method must be patched for the
    # assertion to be meaningful.
    assert patches, "expected scheduler DOM mutation methods to patch"

    with patch.object(A, "_connect_attached_driver", return_value=MagicMock()), \
         patch("modules.ai_intelligence.video_indexer.src.studio_ask_indexer.StudioAskIndexer",
               return_value=inst):
        for p in patches:
            p.start()
        try:
            out = asyncio.run(run_studio_ask_single_video(
                StudioAskSingleVideoInput(video_id="vid123", browser="chrome", persist=False)
            ))
        finally:
            for p in patches:
                p.stop()

    assert out.success is True
    raise_if_called.assert_not_called()


def test_dispatcher_routes_single_video_via_kwargs():
    ask_result = _ok_ask_result()
    inst = _patched_indexer(ask_result)
    with patch.object(A, "_connect_attached_driver", return_value=MagicMock()), \
         patch("modules.ai_intelligence.video_indexer.src.studio_ask_indexer.StudioAskIndexer",
               return_value=inst):
        out = asyncio.run(run_action(
            VideoIndexAction.STUDIO_ASK_SINGLE_VIDEO,
            video_id="vid123", browser="chrome", persist=False,
        ))
    assert isinstance(out, StudioAskSingleVideoOutput)
    assert out.success is True
    inst.ask_about_video.assert_awaited_once()
