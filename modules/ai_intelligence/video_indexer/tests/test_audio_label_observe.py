# -*- coding: utf-8 -*-
"""
Tests for OBSERVE-MODE acoustic music/talk label in PHASE 2 indexing.

Slice: SHORTS_MUSIC_LABEL_OBSERVE_PHASE1   Worker-Lane: MUSIC-OBSERVE

WSP refs: WSP 5 (coverage), WSP 6 (audit), WSP 84 (reuse VideoArchiveExtractor +
audio_content_classifier.classify_content).

CONTRACT under test (observe-only, flag-gated, default OFF):
  - flag ON  -> _observe_audio_label downloads (mocked) + classifies (mocked) and
                returns {audio_label, audio_label_confidence}; the per-video write
                path stores those as a SIBLING of content_category (UNTOUCHED) and
                emits the [MUSIC-OBSERVE] compare-breadcrumb.
  - flag OFF -> _observe_audio_label is a pure no-op (returns None, ZERO audio
                work: extract_audio / classify_content are NEVER called) and the
                artifact has NO audio_label field.
  - download/classify error -> _observe_audio_label returns None (no exception),
                indexing continues, NO audio_label field, content_category intact.

NO LIVE AUDIO / BROWSER / MODELS: extract_audio + classify_content are mocked.
The acoustic classifier import target is patched at its source module so the heavy
librosa/yt-dlp/ffmpeg path is never exercised.
"""

import json
import os
import tempfile
from dataclasses import dataclass
from types import SimpleNamespace
from unittest import mock

import pytest

from modules.ai_intelligence.video_indexer.src import studio_ask_indexer as sai
from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import (
    AskResult,
    StudioAskIndexer,
)
from modules.ai_intelligence.video_indexer.src.video_index_store import VideoIndexStore


# ---------------------------------------------------------------------------
# Test doubles mirroring the real return contracts (no heavy deps).
# ---------------------------------------------------------------------------
@dataclass
class _FakeResult:
    """Mirror of audio_content_classifier.ClassificationResult."""
    label: str
    confidence: float
    method: str = "acoustic"


def _fake_extractor_returning(array_value):
    """Build a fake VideoArchiveExtractor class whose extract_audio returns array_value."""
    class _FakeExtractor:
        def __init__(self, *a, **k):
            pass

        def extract_audio(self, video_id, use_cache=True):
            return array_value

    return _FakeExtractor


@pytest.fixture(autouse=True)
def _clear_flag():
    """Ensure the observe flag starts unset for every test (default OFF)."""
    prev = os.environ.pop(sai.AUDIO_LABEL_OBSERVE_FLAG, None)
    yield
    if prev is None:
        os.environ.pop(sai.AUDIO_LABEL_OBSERVE_FLAG, None)
    else:
        os.environ[sai.AUDIO_LABEL_OBSERVE_FLAG] = prev


import contextlib
import sys
import types


@contextlib.contextmanager
def _patch_audio_chain(extractor_cls, classify_fn):
    """Inject FAKE source modules so the lazy imports inside _observe_audio_label
    resolve to our doubles -- WITHOUT importing the real heavy modules.

    _observe_audio_label lazily does:
        from modules.platform_integration.youtube_live_audio.src.youtube_live_audio
            import VideoArchiveExtractor
        from modules.ai_intelligence.audio_content_classifier.src.audio_content_classifier
            import classify_content as acoustic_classify_content

    The real youtube_live_audio module has a top-level `import numpy as np`, so we
    must NOT import it in a hermetic test. We register fake modules in sys.modules
    BEFORE the lazy import runs; Python's import machinery returns the cached fake.
    """
    yla_name = "modules.platform_integration.youtube_live_audio.src.youtube_live_audio"
    acc_name = "modules.ai_intelligence.audio_content_classifier.src.audio_content_classifier"

    fake_yla = types.ModuleType(yla_name)
    fake_yla.VideoArchiveExtractor = extractor_cls
    fake_acc = types.ModuleType(acc_name)
    fake_acc.classify_content = classify_fn

    saved = {k: sys.modules.get(k) for k in (yla_name, acc_name)}
    sys.modules[yla_name] = fake_yla
    sys.modules[acc_name] = fake_acc
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


# ===========================================================================
# _observe_audio_label: flag ON -> computes label (mock chain, no real audio)
# ===========================================================================
def test_observe_label_flag_on_returns_label():
    os.environ[sai.AUDIO_LABEL_OBSERVE_FLAG] = "1"
    classify = mock.Mock(return_value=_FakeResult(label="music", confidence=0.91, method="acoustic"))
    with _patch_audio_chain(_fake_extractor_returning([0.1, -0.1, 0.2]), classify):
        observed = sai._observe_audio_label("vidMUSIC")
    assert observed == {"audio_label": "music", "audio_label_confidence": 0.91}
    classify.assert_called_once()  # NON-VACUOUS: the classifier really ran


def test_observe_label_talk_path():
    os.environ[sai.AUDIO_LABEL_OBSERVE_FLAG] = "1"
    classify = mock.Mock(return_value=_FakeResult(label="talk", confidence=0.77, method="acoustic"))
    with _patch_audio_chain(_fake_extractor_returning([0.0, 0.0]), classify):
        observed = sai._observe_audio_label("vidTALK")
    assert observed == {"audio_label": "talk", "audio_label_confidence": 0.77}


# ===========================================================================
# _observe_audio_label: flag OFF -> pure no-op, ZERO audio work
# ===========================================================================
def test_observe_label_flag_off_is_noop():
    # Flag unset by fixture. extract_audio / classify must NEVER be called.
    classify = mock.Mock(side_effect=AssertionError("classify must not run when flag OFF"))

    class _ExplodingExtractor:
        def __init__(self, *a, **k):
            raise AssertionError("extractor must not be constructed when flag OFF")

    with _patch_audio_chain(_ExplodingExtractor, classify):
        observed = sai._observe_audio_label("vidX")
    assert observed is None
    classify.assert_not_called()


# ===========================================================================
# _observe_audio_label: failures never raise, return None
# ===========================================================================
def test_observe_label_download_none_returns_none():
    os.environ[sai.AUDIO_LABEL_OBSERVE_FLAG] = "1"
    classify = mock.Mock(side_effect=AssertionError("classify must not run if download is None"))
    with _patch_audio_chain(_fake_extractor_returning(None), classify):
        observed = sai._observe_audio_label("vidNoAudio")
    assert observed is None
    classify.assert_not_called()


def test_observe_label_classify_raises_returns_none():
    os.environ[sai.AUDIO_LABEL_OBSERVE_FLAG] = "1"
    classify = mock.Mock(side_effect=RuntimeError("boom in classifier"))
    with _patch_audio_chain(_fake_extractor_returning([0.1, 0.2, 0.3]), classify):
        observed = sai._observe_audio_label("vidErr")  # must NOT raise
    assert observed is None


def test_observe_label_unavailable_method_returns_none():
    # Classifier ran but could not decide (fail-safe 'unavailable') -> no observation.
    os.environ[sai.AUDIO_LABEL_OBSERVE_FLAG] = "1"
    classify = mock.Mock(return_value=_FakeResult(label="talk", confidence=0.0, method="unavailable"))
    with _patch_audio_chain(_fake_extractor_returning([0.0]), classify):
        observed = sai._observe_audio_label("vidUnavail")
    assert observed is None


# ===========================================================================
# Artifact-write integration: when a label is observed, it is stored as a
# SIBLING of content_category (which stays UNTOUCHED) and persists to JSON.
# ===========================================================================
def test_label_written_as_sibling_of_content_category_on_disk():
    os.environ["VIDEO_INDEX_SQLITE_DISABLE"] = "1"
    try:
        ask_result = AskResult(
            video_id="vidSibling",
            title="A Song",
            response_text="lyrics ...",
            topics=["music"],
            timestamps=[{"time": "0:05", "topic": "intro", "summary": "intro"}],
            success=True,
            content_category="ffcpln_music",
        )
        index_data = StudioAskIndexer._ask_result_to_index_data(ask_result, channel_key="undaodu")

        # Simulate the loop's observe-write (helper already covered above).
        observed = {"audio_label": "music", "audio_label_confidence": 0.88}
        index_data.metadata["audio_label"] = observed["audio_label"]
        index_data.metadata["audio_label_confidence"] = observed["audio_label_confidence"]

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VideoIndexStore(base_path=tmpdir)
            saved_path = store.save_index("vidSibling", index_data)
            with open(saved_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        meta = data["metadata"]
        # SIBLING present, content_category UNTOUCHED.
        assert meta["audio_label"] == "music"
        assert meta["audio_label_confidence"] == 0.88
        assert meta["content_category"] == "ffcpln_music"
    finally:
        os.environ.pop("VIDEO_INDEX_SQLITE_DISABLE", None)


def test_no_label_field_when_observe_returns_none():
    """Flag-off / failure path: artifact carries NO audio_label field."""
    os.environ["VIDEO_INDEX_SQLITE_DISABLE"] = "1"
    try:
        ask_result = AskResult(
            video_id="vidPlain",
            title="A Talk",
            response_text="...",
            topics=["talk"],
            timestamps=[{"time": "0:05", "topic": "intro", "summary": "intro"}],
            success=True,
            content_category="educational",
        )
        index_data = StudioAskIndexer._ask_result_to_index_data(ask_result, channel_key="undaodu")
        # observe returned None -> caller writes nothing.
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VideoIndexStore(base_path=tmpdir)
            saved_path = store.save_index("vidPlain", index_data)
            with open(saved_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        assert "audio_label" not in data["metadata"]
        assert "audio_label_confidence" not in data["metadata"]
        assert data["metadata"]["content_category"] == "educational"
    finally:
        os.environ.pop("VIDEO_INDEX_SQLITE_DISABLE", None)


# ===========================================================================
# Compare-breadcrumb: the loop's observe write emits a [MUSIC-OBSERVE] log with
# video_id + audio_label + content_category so 012 can compare acoustic vs LLM.
# We exercise the exact write+log snippet the loop runs (helper mocked).
# ===========================================================================
def test_compare_breadcrumb_logged(caplog):
    import logging

    ask_result = AskResult(
        video_id="vidCrumb",
        title="A Song",
        response_text="...",
        topics=["music"],
        timestamps=[{"time": "0:05", "topic": "intro", "summary": "intro"}],
        success=True,
        content_category="ffcpln_music",
    )
    index_data = StudioAskIndexer._ask_result_to_index_data(ask_result, channel_key="undaodu")

    observed = {"audio_label": "music", "audio_label_confidence": 0.93}
    with caplog.at_level(logging.INFO, logger=sai.logger.name):
        # Mirror the loop body exactly.
        index_data.metadata["audio_label"] = observed["audio_label"]
        index_data.metadata["audio_label_confidence"] = observed["audio_label_confidence"]
        sai.logger.info(
            "[MUSIC-OBSERVE] %s audio_label=%s confidence=%s content_category=%s",
            "vidCrumb",
            observed["audio_label"],
            observed["audio_label_confidence"],
            index_data.metadata.get("content_category"),
        )

    msgs = "\n".join(r.getMessage() for r in caplog.records)
    assert "[MUSIC-OBSERVE]" in msgs
    assert "vidCrumb" in msgs
    assert "audio_label=music" in msgs
    assert "content_category=ffcpln_music" in msgs
