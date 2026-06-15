"""
Index<->Metadata Decoupling tests (Phase 1).

Slice: SHORTS_SCHEDULER_INDEX_METADATA_DECOUPLING_PHASE1

Proves the Phase 1 read/write split for the YouTube Shorts Scheduler:
  - The INDEXING path (run_indexing_cycle) performs NO live YouTube mutation:
    it never calls edit_title / edit_description / schedule_video / save_video.
  - The scheduler READ path is a pure CONSUMER of an EXISTING index artifact:
    it never calls ensure_index_json and never imports/instantiates
    GeminiVideoAnalyzer.
  - A MISSING artifact -> "skip enhancement", NOT "index now".
  - The EXPLICIT scheduling path STILL writes live metadata (regression anchor).
  - The pure builder build_index_metadata_context() is read-only.

ANTI-VACUITY (ADDENDUM C/D):
  - The DOM double is a strict spec_set MagicMock against the REAL
    YouTubeStudioDOM class, so save_video does NOT exist on it (it is not a real
    method - dom_automation.py has no `def save_video`). Accessing a missing
    attribute on a spec_set mock raises AttributeError, so the refactored
    indexing path must not touch save_video at all.
  - NO bare Mock()/MagicMock() without spec; NO mock.patch.object(..., 'save_video',
    create=True). Inventing save_video would make Control 4 vacuous.
  - Each control first asserts the loop body executed (navigate_to_video called)
    BEFORE asserting the (non-)call of a sink, because dry_run=True would skip the
    body and make "not called" vacuous.
  - Negative controls 1/2/5/6 FAIL on the old coupled code (they exercise the same
    sinks the old code drove). Control 3 is paired with Control 7 (see its docstring).
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from modules.platform_integration.youtube_shorts_scheduler.src.dom_automation import (
    YouTubeStudioDOM,
)
from modules.platform_integration.youtube_shorts_scheduler.src.scheduler import (
    YouTubeShortsScheduler,
)
from modules.platform_integration.youtube_shorts_scheduler.src import index_weave
from modules.platform_integration.youtube_shorts_scheduler.src.index_weave import (
    build_index_metadata_context,
    MetadataContext,
)


# ---------------------------------------------------------------------------
# Shared harness (strict, anti-vacuity)
# ---------------------------------------------------------------------------

def _make_strict_dom():
    """
    Strict spec_set DOM double based on the REAL YouTubeStudioDOM interface.

    spec_set means: attributes NOT defined on the real class (e.g. save_video,
    which dom_automation.py does NOT define) raise AttributeError on access. This
    is what proves the refactored indexing path never touches save_video.
    """
    dom = MagicMock(spec_set=YouTubeStudioDOM)
    dom.check_driver_health.return_value = True
    dom.navigate_to_video.return_value = None
    dom.get_unlisted_videos.return_value = [{"video_id": "vid1", "title": "Original Title"}]
    dom.read_edit_page_visibility.return_value = "unlisted"
    dom.get_current_description.return_value = ""
    dom.edit_title.return_value = None
    dom.edit_description.return_value = None
    dom.schedule_video.return_value = True
    dom.human_delay.return_value = 0.0
    return dom


def _make_driver():
    """Truthy driver double (so `if not self.driver` is False)."""
    driver = MagicMock()
    driver.get.return_value = None
    driver.execute_script.return_value = "not_found"
    driver.find_elements.return_value = []
    return driver


def _make_scheduler():
    """Connected scheduler with a strict DOM double; dry_run=False (live path)."""
    scheduler = YouTubeShortsScheduler("move2japan", dry_run=False)
    scheduler.driver = _make_driver()
    scheduler.dom = _make_strict_dom()
    return scheduler


def _write_artifact(tmp_path, monkeypatch, channel_key, video_id):
    """Write a real index artifact under a tmp VIDEO_INDEXER_ARTIFACT_PATH."""
    monkeypatch.setenv("VIDEO_INDEXER_ARTIFACT_PATH", str(tmp_path))
    artifact = {
        "video_id": video_id,
        "title": "Original Title",
        "indexed_at": "2026-06-16T00:00:00Z",
        "indexer": "studio_ask",
        "audio": {"segments": [{"start": 0, "end": 5, "text": "hi"}], "transcript_summary": "calm talk"},
        "visual": {"description": "", "keyframes": []},
        "metadata": {
            "duration": "0:30",
            "topics": ["Mindfulness", "Zen"],
            "speakers": [],
            "key_points": ["Breathe and be present."],
            "summary": "A short on mindful breathing.",
        },
        "classification": {"discovered_categories": ["Mindfulness"]},
    }
    path = Path(tmp_path) / channel_key.lower() / f"{video_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# CONTROL 1 - INDEXING does NOT call edit_title (FAILS on old code)
# ---------------------------------------------------------------------------

async def test_control1_indexing_does_not_call_edit_title(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_INDEXER_ARTIFACT_PATH", str(tmp_path))
    scheduler = _make_scheduler()

    await scheduler.run_indexing_cycle(max_videos=1, video_type="shorts")

    # Reachability: the per-video loop body executed.
    scheduler.dom.navigate_to_video.assert_called_with("vid1")
    # Sink assertion on the DOUBLE's call_count (not log text / results dict).
    assert scheduler.dom.edit_title.call_count == 0


# ---------------------------------------------------------------------------
# CONTROL 2 - INDEXING does NOT call edit_description (FAILS on old code)
# ---------------------------------------------------------------------------

async def test_control2_indexing_does_not_call_edit_description(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_INDEXER_ARTIFACT_PATH", str(tmp_path))
    scheduler = _make_scheduler()

    await scheduler.run_indexing_cycle(max_videos=1, video_type="shorts")

    scheduler.dom.navigate_to_video.assert_called_with("vid1")
    assert scheduler.dom.edit_description.call_count == 0


# ---------------------------------------------------------------------------
# CONTROL 3 - INDEXING does NOT call schedule_video (paired w/ Control 7)
# ---------------------------------------------------------------------------

async def test_control3_indexing_does_not_call_schedule_video(tmp_path, monkeypatch):
    """
    HONESTY FLAG: the OLD run_indexing_cycle already SKIPPED scheduling, so this
    passes on BOTH old and new code and is NOT a true negative control in
    isolation. It is meaningful only when PAIRED with Control 7 (positive
    schedule_video call) on the SAME strict-double type, which proves
    schedule_video exists and is wired. Documented honestly in the PR.
    """
    monkeypatch.setenv("VIDEO_INDEXER_ARTIFACT_PATH", str(tmp_path))
    scheduler = _make_scheduler()

    await scheduler.run_indexing_cycle(max_videos=1, video_type="shorts")

    scheduler.dom.navigate_to_video.assert_called_with("vid1")
    assert scheduler.dom.schedule_video.call_count == 0


# ---------------------------------------------------------------------------
# CONTROL 4 - INDEXING does NOT access/resolve save_video (highest vacuity risk)
# ---------------------------------------------------------------------------

async def test_control4_indexing_does_not_access_save_video(tmp_path, monkeypatch):
    """
    save_video is NOT a real method on YouTubeStudioDOM (dom_automation.py has no
    `def save_video`). With a spec_set double, ANY access to save_video raises
    AttributeError. The refactored indexing path must therefore never touch it.

    On the OLD code, run_indexing_cycle called self.dom.save_video(): against this
    strict double that path would raise AttributeError (latent bug surfaced).
    We do NOT invent save_video (no create=True, no loose Mock).

    Records: SAVE_VIDEO_LATENT_BUG_REMOVED_FROM_INDEXING_PATH.
    """
    monkeypatch.setenv("VIDEO_INDEXER_ARTIFACT_PATH", str(tmp_path))
    scheduler = _make_scheduler()

    # The strict spec_set double does not expose save_video at all.
    assert not hasattr(scheduler.dom, "save_video")

    # Cycle completes WITHOUT raising AttributeError for a missing save_video.
    results = await scheduler.run_indexing_cycle(max_videos=1, video_type="shorts")

    scheduler.dom.navigate_to_video.assert_called_with("vid1")
    assert "fatal_error" not in results
    # Still no save_video attribute was materialised on the double.
    assert not hasattr(scheduler.dom, "save_video")


# ---------------------------------------------------------------------------
# CONTROL 5 - scheduler READ path does NOT call ensure_index_json (FAILS on old)
# ---------------------------------------------------------------------------

async def test_control5_read_path_does_not_call_ensure_index_json(tmp_path, monkeypatch):
    """
    Spy on the BOUND name in the scheduler module namespace would be vacuous for
    ensure_index_json because the refactor REMOVED that import. The non-vacuous
    proof: with a PRESENT artifact the read path fully executes and produces a
    woven description, while patching index_weave.ensure_index_json shows it is
    never invoked. On the OLD code ensure_index_json fired at scheduler.py:901.
    """
    channel_key = "move2japan"
    video_id = "vid1"
    _write_artifact(tmp_path, monkeypatch, channel_key, video_id)

    ensure_spy = MagicMock(side_effect=AssertionError("ensure_index_json must NOT be called on read path"))
    monkeypatch.setattr(index_weave, "ensure_index_json", ensure_spy)
    load_spy = MagicMock(wraps=index_weave.load_index_json)
    monkeypatch.setattr(
        "modules.platform_integration.youtube_shorts_scheduler.src.index_weave.load_index_json",
        load_spy,
    )

    scheduler = _make_scheduler()
    monkeypatch.setenv("YT_SCHEDULER_INDEX_WEAVE_ENABLED", "true")

    # Drive the scheduling read path directly (update_metadata=True case).
    await scheduler._update_video_metadata(
        video_id=video_id,
        original_title="Original Title",
        date_str="Jun 20, 2026",
        time_str="5:00 PM",
    )

    assert ensure_spy.call_count == 0
    # The read path used the artifact (load_index_json invoked) ...
    assert load_spy.call_count >= 1
    # ... and a live write still fired on the scheduling path (artifact present).
    assert scheduler.dom.edit_title.call_count >= 1
    assert scheduler.dom.edit_description.call_count >= 1


# ---------------------------------------------------------------------------
# CONTROL 6 - scheduler READ path does NOT import/instantiate GeminiVideoAnalyzer
# ---------------------------------------------------------------------------

async def test_control6_read_path_no_gemini(tmp_path, monkeypatch):
    """
    Install an import guard so that ANY attempt to construct GeminiVideoAnalyzer
    raises. GeminiVideoAnalyzer is reached only via ensure_index_json(mode='gemini')
    (index_weave.py:365). After the refactor the read path never touches it.

    On OLD code the gemini reindex branch (scheduler.py:377) could construct it.
    """
    import sys
    import types

    constructed = {"count": 0}

    class _BoomGemini:
        def __init__(self, *a, **k):
            constructed["count"] += 1
            raise AssertionError("GeminiVideoAnalyzer must NOT be instantiated on the read path")

    fake_mod = types.ModuleType("modules.ai_intelligence.video_indexer.src.gemini_video_analyzer")
    fake_mod.GeminiVideoAnalyzer = _BoomGemini
    fake_mod.save_analysis_result = lambda *a, **k: None
    monkeypatch.setitem(
        sys.modules,
        "modules.ai_intelligence.video_indexer.src.gemini_video_analyzer",
        fake_mod,
    )

    channel_key = "move2japan"
    video_id = "vid1"
    _write_artifact(tmp_path, monkeypatch, channel_key, video_id)

    scheduler = _make_scheduler()
    monkeypatch.setenv("YT_SCHEDULER_INDEX_WEAVE_ENABLED", "true")

    await scheduler._update_video_metadata(
        video_id=video_id,
        original_title="Original Title",
        date_str="Jun 20, 2026",
        time_str="5:00 PM",
    )

    assert constructed["count"] == 0


# ---------------------------------------------------------------------------
# CONTROL 7 - EXPLICIT scheduling path STILL writes (positive regression anchor)
# ---------------------------------------------------------------------------

async def test_control7_scheduling_path_still_writes(tmp_path, monkeypatch):
    """
    MUST PASS on BOTH old and refactored code. If the refactor breaks this, the
    decoupling changed observable scheduling behavior -> STOP/NEEDS_012.

    read_edit_page_visibility -> 'unlisted' (else the video is skipped before
    schedule_video is reached). Asserts the live-write sinks fire on the explicit
    scheduling path, and pairs with Control 3 to prove schedule_video is wired.
    """
    monkeypatch.setenv("VIDEO_INDEXER_ARTIFACT_PATH", str(tmp_path))
    scheduler = _make_scheduler()

    await scheduler.run_scheduling_cycle(max_videos=1, update_metadata=True)

    # Reachability: per-video body executed.
    scheduler.dom.navigate_to_video.assert_called_with("vid1")
    # Live writes fired on the explicit scheduling path.
    assert scheduler.dom.edit_title.call_count >= 1
    assert scheduler.dom.edit_description.call_count >= 1
    assert scheduler.dom.schedule_video.call_count == 1
    args, _ = scheduler.dom.schedule_video.call_args
    assert len(args) == 2  # (date_str, time_str)


# ---------------------------------------------------------------------------
# PURE BUILDER - read-only (present + missing artifact)
# ---------------------------------------------------------------------------

def test_pure_builder_present_artifact_is_read_only(tmp_path, monkeypatch):
    """
    Present artifact -> NON-None MetadataContext with populated description/hashtags/
    digital-twin content; ensure_index_json/save_index_json/create_stub_index_json
    all uncalled; GeminiVideoAnalyzer never imported; signature takes no dom/driver.
    """
    import inspect
    import sys
    import types

    channel_key = "move2japan"
    video_id = "vid1"
    _write_artifact(tmp_path, monkeypatch, channel_key, video_id)

    ensure_spy = MagicMock(side_effect=AssertionError("ensure_index_json must NOT be called"))
    save_spy = MagicMock(side_effect=AssertionError("save_index_json must NOT be called"))
    stub_spy = MagicMock(side_effect=AssertionError("create_stub_index_json must NOT be called"))
    monkeypatch.setattr(index_weave, "ensure_index_json", ensure_spy)
    monkeypatch.setattr(index_weave, "save_index_json", save_spy)
    monkeypatch.setattr(index_weave, "create_stub_index_json", stub_spy)

    class _BoomGemini:
        def __init__(self, *a, **k):
            raise AssertionError("GeminiVideoAnalyzer must NOT be imported/instantiated")

    fake_mod = types.ModuleType("modules.ai_intelligence.video_indexer.src.gemini_video_analyzer")
    fake_mod.GeminiVideoAnalyzer = _BoomGemini
    fake_mod.save_analysis_result = lambda *a, **k: None
    monkeypatch.setitem(
        sys.modules,
        "modules.ai_intelligence.video_indexer.src.gemini_video_analyzer",
        fake_mod,
    )

    # Signature must NOT take a dom/driver argument.
    params = set(inspect.signature(build_index_metadata_context).parameters)
    assert "dom" not in params
    assert "driver" not in params

    ctx = build_index_metadata_context(
        channel_key=channel_key,
        video_id=video_id,
        original_title="Original Title",
        base_description="Base description body.",
        inform_title=False,
        enhance_description=True,
    )

    assert isinstance(ctx, MetadataContext)
    assert ctx.used_index is True
    # Description context proves the builder actually ran (not a no-op).
    assert "Base description body." in ctx.new_description
    assert "0102 DIGITAL TWIN INDEX v1" in ctx.new_description
    assert "#" in ctx.new_description  # topic hashtags woven in
    assert ensure_spy.call_count == 0
    assert save_spy.call_count == 0
    assert stub_spy.call_count == 0


def test_pure_builder_missing_artifact_returns_none(tmp_path, monkeypatch):
    """
    Missing artifact -> builder returns None (skip enhancement) AND
    ensure_index_json/save_index_json never called (does NOT index now).
    Paired with the present-artifact case so a builder that ALWAYS returns None
    cannot pass vacuously.
    """
    # Point at an empty tmp dir -> artifact absent.
    monkeypatch.setenv("VIDEO_INDEXER_ARTIFACT_PATH", str(tmp_path))

    ensure_spy = MagicMock(side_effect=AssertionError("ensure_index_json must NOT be called"))
    save_spy = MagicMock(side_effect=AssertionError("save_index_json must NOT be called"))
    monkeypatch.setattr(index_weave, "ensure_index_json", ensure_spy)
    monkeypatch.setattr(index_weave, "save_index_json", save_spy)

    ctx = build_index_metadata_context(
        channel_key="move2japan",
        video_id="missing_vid",
        original_title="Original Title",
        base_description="Base description body.",
        inform_title=False,
        enhance_description=True,
    )

    assert ctx is None
    assert ensure_spy.call_count == 0
    assert save_spy.call_count == 0
