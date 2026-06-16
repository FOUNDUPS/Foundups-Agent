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

    NON-VACUITY (hardened): the per-video loop in run_indexing_cycle wraps each
    video body in an inner `except Exception as e:` that appends {"video_id",
    "error": str(e)} into results["errors"]; only the OUTER except sets
    results["fatal_error"]. So a swallowed AttributeError from a missing
    save_video access lands in results["errors"] mentioning 'save_video', and
    NEVER reaches results["fatal_error"]. Asserting only `"fatal_error" not in
    results` would therefore be VACUOUS (it cannot observe a save_video access).
    This control instead inspects results["errors"] directly:

      (a) REACHABILITY: navigate_to_video was called with the video id, proving
          the per-video loop body actually executed (dry_run=False; a no-op loop
          would make every "not accessed" claim vacuous). results["indexed"] is
          NOT asserted non-empty because the empty tmp artifact dir makes the
          builder return None -> the video lands in results["skipped"], which is
          the correct read-only behavior.
      (b) NON-VACUOUS DETECTION: no entry in results["errors"] references
          'save_video', AND results["errors"] == [] for the clean read-only path.
          If the indexing path accessed save_video, the spec_set AttributeError
          ("Mock object has no attribute 'save_video'") would be swallowed into
          results["errors"] and this assertion would FAIL.
      (c) DOCUMENTATION: the strict spec_set double genuinely lacks save_video
          (no create=True, no loose Mock - inventing it would re-vacuate Control 4).

    The discrimination test test_control4_detection_channel_surfaces_save_video
    PROVES (b) has teeth: injecting an actual save_video access makes this exact
    channel surface 'save_video' in results["errors"].

    Records: SAVE_VIDEO_LATENT_BUG_REMOVED_FROM_INDEXING_PATH.
    """
    monkeypatch.setenv("VIDEO_INDEXER_ARTIFACT_PATH", str(tmp_path))
    scheduler = _make_scheduler()

    # (c) DOCUMENTATION: the strict spec_set double does not expose save_video.
    assert not hasattr(scheduler.dom, "save_video")

    results = await scheduler.run_indexing_cycle(max_videos=1, video_type="shorts")

    # (a) REACHABILITY: the per-video loop body executed for vid1.
    scheduler.dom.navigate_to_video.assert_called_with("vid1")

    # (b) NON-VACUOUS DETECTION: a swallowed save_video AttributeError would land
    # in results["errors"]; on the clean read-only path there are no errors and
    # none reference save_video.
    assert not any(
        "save_video" in (e.get("error", "")) for e in results["errors"]
    ), f"indexing path accessed save_video; swallowed into errors: {results['errors']}"
    assert results["errors"] == [], (
        f"clean read-only indexing path produced errors: {results['errors']}"
    )

    # The OUTER except (fatal_error) is NOT the detection channel here; documented
    # for completeness only.
    assert "fatal_error" not in results
    # Still no save_video attribute was materialised on the double.
    assert not hasattr(scheduler.dom, "save_video")


# ---------------------------------------------------------------------------
# CONTROL 4 (discrimination) - the save_video detection channel has teeth
# ---------------------------------------------------------------------------

async def test_control4_detection_channel_surfaces_save_video(tmp_path, monkeypatch):
    """
    DISCRIMINATION test for Control 4 (no product-code edit).

    Proves the detection channel Control 4 relies on actually works: if the
    indexing path accesses self.dom.save_video(), the spec_set AttributeError is
    swallowed by the per-video inner `except` into results["errors"] mentioning
    'save_video' (it is NOT promoted to results["fatal_error"]).

    We monkeypatch the BOUND name the indexing loop calls -
    scheduler.py line ~1107: `ctx = build_index_metadata_context(...)`, imported
    at scheduler.py:29 into the scheduler module namespace - with a stand-in that
    first calls scheduler.dom.save_video() (forcing the spec_set AttributeError
    INSIDE the per-video try body) and then delegates to the real builder. This
    simulates "the indexing path touches save_video" WITHOUT editing product code.

    Expected: the AttributeError surfaces in results["errors"] (any entry's error
    string contains 'save_video'), and Control 4's
    `assert results["errors"] == []` / `not any("save_video" in ...)` would FAIL
    under this injection. This is what makes Control 4 non-vacuous.
    """
    from modules.platform_integration.youtube_shorts_scheduler.src import (
        scheduler as scheduler_module,
    )

    monkeypatch.setenv("VIDEO_INDEXER_ARTIFACT_PATH", str(tmp_path))
    scheduler = _make_scheduler()

    real_builder = scheduler_module.build_index_metadata_context

    def _builder_touching_save_video(**kwargs):
        # Force the exact spec_set AttributeError Control 4 must detect, from
        # INSIDE the per-video loop body so the inner except swallows it.
        scheduler.dom.save_video()  # AttributeError: spec_set has no save_video
        return real_builder(**kwargs)  # pragma: no cover - never reached

    monkeypatch.setattr(
        scheduler_module,
        "build_index_metadata_context",
        _builder_touching_save_video,
    )

    results = await scheduler.run_indexing_cycle(max_videos=1, video_type="shorts")

    # Reachability: the loop body executed for vid1.
    scheduler.dom.navigate_to_video.assert_called_with("vid1")

    # The swallowed save_video AttributeError SURFACES via results["errors"].
    assert any(
        "save_video" in e.get("error", "") for e in results["errors"]
    ), f"expected save_video AttributeError in errors, got: {results['errors']}"

    # It is swallowed by the inner except, NOT promoted to fatal_error - which is
    # precisely why Control 4 must inspect results["errors"], not fatal_error.
    assert "fatal_error" not in results


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


# ---------------------------------------------------------------------------
# SCHEDULING PATH x INDEX-CONTEXT CONSUMPTION (Phase 1 consumption coverage)
#
# Slice: SHORTS_SCHEDULER_VIDEO_INDEX_CONTEXT_CONSUMPTION_COVERAGE_PHASE1
#
# These two tests PIN the artifact-consumption behavior that #820 ALREADY built
# in _update_video_metadata (scheduler.py:891-916), driven end-to-end through
# run_scheduling_cycle. They do NOT rebuild consumption; they only observe it via
# the strict spec_set DOM double. WSP_97: CONSUMPTION_ALREADY_IMPLEMENTED_NOT_REBUILT.
#
# Both run dry_run=False so the per-video write/schedule body executes; both first
# assert REACHABILITY (navigate_to_video) before any content/sink claim, because a
# write path that never ran makes every "not called" / content assertion vacuous
# (the #820 Control-4 lesson). read_edit_page_visibility -> "unlisted" (set by the
# shared _make_strict_dom) -- otherwise the video is skipped before the write and
# the test would be a FALSE NEGATIVE.
#
# Bound-name discipline: ensure_index_json and create_stub_index_json are NOT
# imported into the scheduler module namespace (scheduler.py:24-30 imports only
# load_index_json/save_index_json/build_digital_twin_index_block/
# update_index_after_schedule/build_index_metadata_context). The read path
# therefore CANNOT call them; we assert that structurally via hasattr (a stronger,
# non-vacuous proof than spying a name that is not bound). save_index_json IS bound
# and is spied directly.
# ---------------------------------------------------------------------------

# Index-derived hashtags that the PRESENT-artifact path would weave in (topics
# ["Mindfulness", "Zen"] from _write_artifact). TEST A asserts NONE of these leak
# into the description when the artifact is ABSENT.
_INDEX_DERIVED_HASHTAGS = ("#Mindfulness", "#Zen")
_TWIN_MARKER = "0102 DIGITAL TWIN INDEX"


async def test_scheduling_path_missing_artifact_writes_base_content(tmp_path, monkeypatch):
    """
    TEST A - scheduling path + MISSING artifact.

    run_scheduling_cycle(max_videos=1, update_metadata=True) with NO artifact on
    disk (VIDEO_INDEXER_ARTIFACT_PATH points at an empty tmp dir). The explicit
    scheduling write STILL fires (edit_title/edit_description/schedule_video), but
    the description is BASE content -- build_index_metadata_context returns None so
    NO enhancement is injected, and the read path never indexes.

    NON-VACUITY: this test FAILS if the missing-artifact path were (re-)coupled to
    indexing (a bound ensure_index_json / save_index_json on the read path would
    fire, or an artifact file would appear), OR if base content were enhanced
    without an artifact (the twin marker / index hashtags would appear in the
    edit_description argument).
    """
    from modules.platform_integration.youtube_shorts_scheduler.src import (
        scheduler as scheduler_module,
    )

    # Empty artifact dir -> artifact ABSENT for vid1.
    monkeypatch.setenv("VIDEO_INDEXER_ARTIFACT_PATH", str(tmp_path))
    monkeypatch.setenv("YT_SCHEDULER_INDEX_WEAVE_ENABLED", "true")
    monkeypatch.setenv("YT_SCHEDULER_INDEX_ENHANCE_DESCRIPTION", "true")

    # Pin the channel base description deterministically. get_standard_description
    # is randomized (content_generator.py: 70% main / 30% alt + random ICE victim
    # interpolation), so we stub the BOUND scheduler name to a fixed sentinel that
    # contains NEITHER the twin marker NOR the index-derived hashtags. The written
    # description must then equal this sentinel EXACTLY -> proves no enhancement was
    # injected on the missing-artifact path (non-vacuous, deterministic).
    _BASE_SENTINEL = "FIXED BASE DESCRIPTION - no enhancement expected."
    monkeypatch.setattr(
        scheduler_module, "get_standard_description", lambda *a, **k: _BASE_SENTINEL
    )

    # Bound-name structural proof: the read path cannot call indexing entrypoints
    # that were removed from the scheduler namespace.
    assert not hasattr(scheduler_module, "ensure_index_json")
    assert not hasattr(scheduler_module, "create_stub_index_json")

    # save_index_json IS bound -> spy it (must NOT fire when artifact is absent:
    # the post-schedule sync at scheduler.py:481-497 short-circuits on a None
    # load_index_json, so save_index_json is never reached).
    save_spy = MagicMock(
        side_effect=AssertionError("save_index_json must NOT be called on the missing-artifact path")
    )
    monkeypatch.setattr(scheduler_module, "save_index_json", save_spy)

    # GeminiVideoAnalyzer must never be imported/instantiated on the read path.
    import sys
    import types

    constructed = {"count": 0}

    class _BoomGemini:
        def __init__(self, *a, **k):
            constructed["count"] += 1
            raise AssertionError("GeminiVideoAnalyzer must NOT be instantiated on the scheduling read path")

    fake_mod = types.ModuleType("modules.ai_intelligence.video_indexer.src.gemini_video_analyzer")
    fake_mod.GeminiVideoAnalyzer = _BoomGemini
    fake_mod.save_analysis_result = lambda *a, **k: None
    monkeypatch.setitem(
        sys.modules,
        "modules.ai_intelligence.video_indexer.src.gemini_video_analyzer",
        fake_mod,
    )

    scheduler = _make_scheduler()

    await scheduler.run_scheduling_cycle(max_videos=1, update_metadata=True)

    # REACHABILITY (before any content/sink claim): the per-video write body ran.
    scheduler.dom.navigate_to_video.assert_called_with("vid1")

    # The explicit scheduling write STILL fires.
    assert scheduler.dom.edit_title.call_count >= 1
    assert scheduler.dom.edit_description.call_count >= 1
    assert scheduler.dom.schedule_video.call_count == 1

    # The description argument is BASE content (no enhancement injected).
    desc_args, _ = scheduler.dom.edit_description.call_args
    written_description = desc_args[0]
    assert _TWIN_MARKER not in written_description, (
        "base description must NOT contain the digital-twin block when no artifact exists"
    )
    for tag in _INDEX_DERIVED_HASHTAGS:
        assert tag not in written_description, (
            f"base description must NOT contain index-derived hashtag {tag} with no artifact"
        )
    # Equals the (pinned) channel base description exactly: no woven context,
    # hashtags, or twin block were appended.
    assert written_description == _BASE_SENTINEL

    # NO scheduler-owned indexing: bound save_index_json never fired (side_effect
    # would have raised), GeminiVideoAnalyzer never constructed, and NO artifact
    # file was created on disk during the run.
    assert save_spy.call_count == 0
    assert constructed["count"] == 0
    artifact_path = Path(tmp_path) / "move2japan" / "vid1.json"
    assert not artifact_path.exists(), "missing-artifact scheduling path must NOT create an artifact"


async def test_scheduling_path_present_artifact_weaves_index_context(tmp_path, monkeypatch):
    """
    TEST B - scheduling path + PRESENT artifact.

    A realistic artifact (topics ["Mindfulness", "Zen"], key_points populated) is
    written via tmp_path + VIDEO_INDEXER_ARTIFACT_PATH, then
    run_scheduling_cycle(update_metadata=True) is driven. The edit_description
    argument INCLUDES the index context, the woven index hashtags, AND the
    digital-twin block -> proving the consumption is APPLIED (not a no-op). The
    explicit scheduling path schedules the video exactly once.

    NON-VACUITY: the enhanced markers are asserted PRESENT (a no-op / None builder
    would fail this). A companion read-path cross-check proves schedule_video is
    invoked ONLY from the explicit scheduling path: run_indexing_cycle over the same
    harness yields schedule_video.call_count == 0.
    """
    channel_key = "move2japan"
    video_id = "vid1"
    artifact_path = _write_artifact(tmp_path, monkeypatch, channel_key, video_id)
    assert artifact_path.exists()  # precondition: artifact present

    monkeypatch.setenv("YT_SCHEDULER_INDEX_WEAVE_ENABLED", "true")
    monkeypatch.setenv("YT_SCHEDULER_INDEX_ENHANCE_DESCRIPTION", "true")

    scheduler = _make_scheduler()

    await scheduler.run_scheduling_cycle(max_videos=1, update_metadata=True)

    # REACHABILITY (before any content/sink claim): the per-video write body ran.
    scheduler.dom.navigate_to_video.assert_called_with("vid1")

    # schedule_video fired exactly once on the explicit scheduling path.
    assert scheduler.dom.schedule_video.call_count == 1

    # The woven description proves consumption is APPLIED (not a no-op):
    assert scheduler.dom.edit_description.call_count >= 1
    desc_args, _ = scheduler.dom.edit_description.call_args
    written_description = desc_args[0]
    # (i) index context injected (key_point from the artifact surfaces in context),
    assert "Breathe and be present." in written_description, (
        "human-facing index context must be injected into the description"
    )
    # (ii) at least one woven index hashtag present,
    assert any(tag in written_description for tag in _INDEX_DERIVED_HASHTAGS), (
        "woven index hashtags must appear in the enhanced description"
    )
    # (iii) the digital-twin block present.
    assert _TWIN_MARKER in written_description, (
        "digital-twin index block must appear in the enhanced description"
    )

    # CROSS-CHECK: schedule_video is invoked ONLY from the explicit scheduling
    # path. A fresh scheduler running the READ path (run_indexing_cycle) never
    # schedules (pairs with Control 3/7).
    read_scheduler = _make_scheduler()
    await read_scheduler.run_indexing_cycle(max_videos=1, video_type="shorts")
    read_scheduler.dom.navigate_to_video.assert_called_with("vid1")
    assert read_scheduler.dom.schedule_video.call_count == 0


async def test_scheduling_path_present_artifact_disabled_skips_enhancement(tmp_path, monkeypatch):
    """
    TEST B (env-gate complement) - PRESENT artifact but enhancement DISABLED.

    With YT_SCHEDULER_INDEX_WEAVE_ENABLED=false the read path skips
    build_index_metadata_context entirely, so the digital-twin block and woven
    index hashtags are ABSENT even though the artifact exists. This proves the
    twin block in TEST B is gated by the env switch (not unconditional), making the
    PRESENT/ENABLED assertion in TEST B non-vacuous.
    """
    channel_key = "move2japan"
    video_id = "vid1"
    artifact_path = _write_artifact(tmp_path, monkeypatch, channel_key, video_id)
    assert artifact_path.exists()

    monkeypatch.setenv("YT_SCHEDULER_INDEX_WEAVE_ENABLED", "false")

    scheduler = _make_scheduler()

    await scheduler.run_scheduling_cycle(max_videos=1, update_metadata=True)

    scheduler.dom.navigate_to_video.assert_called_with("vid1")
    assert scheduler.dom.schedule_video.call_count == 1
    assert scheduler.dom.edit_description.call_count >= 1
    desc_args, _ = scheduler.dom.edit_description.call_args
    written_description = desc_args[0]
    assert _TWIN_MARKER not in written_description, (
        "twin block must be ABSENT when YT_SCHEDULER_INDEX_WEAVE_ENABLED=false"
    )


async def test_update_metadata_logs_index_context_marker(tmp_path, monkeypatch, caplog):
    """
    Observability: _update_video_metadata emits a single behaviour-neutral marker
    'index_context=present|missing|disabled'. This asserts ONLY the token is
    present (not any content/transcript). present -> ctx applied; missing ->
    artifact absent; disabled -> weave env switch off.
    """
    import logging

    # present (artifact written, weave enabled by default)
    _write_artifact(tmp_path, monkeypatch, "move2japan", "vid1")
    monkeypatch.setenv("YT_SCHEDULER_INDEX_WEAVE_ENABLED", "true")
    scheduler = _make_scheduler()
    with caplog.at_level(logging.INFO):
        await scheduler._update_video_metadata(
            video_id="vid1",
            original_title="Original Title",
            date_str="Jun 20, 2026",
            time_str="5:00 PM",
        )
    assert "index_context=present" in caplog.text

    # missing (empty artifact dir)
    caplog.clear()
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.setenv("VIDEO_INDEXER_ARTIFACT_PATH", str(empty_dir))
    scheduler_missing = _make_scheduler()
    with caplog.at_level(logging.INFO):
        await scheduler_missing._update_video_metadata(
            video_id="vid_absent",
            original_title="Original Title",
            date_str="Jun 20, 2026",
            time_str="5:00 PM",
        )
    assert "index_context=missing" in caplog.text

    # disabled (weave env switch off)
    caplog.clear()
    monkeypatch.setenv("YT_SCHEDULER_INDEX_WEAVE_ENABLED", "false")
    scheduler_disabled = _make_scheduler()
    with caplog.at_level(logging.INFO):
        await scheduler_disabled._update_video_metadata(
            video_id="vid1",
            original_title="Original Title",
            date_str="Jun 20, 2026",
            time_str="5:00 PM",
        )
    assert "index_context=disabled" in caplog.text
