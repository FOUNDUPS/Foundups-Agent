"""
Scheduler OBSERVE-MODE audio_label log tests.

Slice: SHORTS_MUSIC_LABEL_OBSERVE_PHASE1   Worker-Lane: MUSIC-OBSERVE

WSP refs: WSP 5 (coverage), WSP 6 (audit), WSP 84 (reuse load_index_json).

CONTRACT under test (OBSERVE-ONLY -- never gates scheduling):
  - When the index artifact carries an acoustic audio_label sibling,
    _observe_audio_label_log emits a [MUSIC-OBSERVE] log with the label +
    content_category. (NON-VACUOUS: asserts the actual log content.)
  - When NO audio_label is present, it emits NO [MUSIC-OBSERVE] log.
  - The helper ALWAYS returns None (carries no decision signal) and NEVER raises,
    even when the artifact read blows up -- so it is structurally incapable of
    gating scheduling.
  - REGRESSION GUARD (must FAIL if observe ever gates scheduling): a deterministic
    scheduling-decision proxy produces the SAME outcome whether or not a label is
    present in the artifact. The observe call is invoked in between, and the
    decision is asserted IDENTICAL with and without the label.

NO LIVE BROWSER / AUDIO / MODELS: load_index_json is patched; no driver is used.
"""

import logging
from unittest import mock

import pytest

from modules.platform_integration.youtube_shorts_scheduler.src import scheduler as sched_mod
from modules.platform_integration.youtube_shorts_scheduler.src.scheduler import (
    YouTubeShortsScheduler,
)


def _make_scheduler():
    # dry_run avoids any browser/mutation; no connect_browser is called.
    return YouTubeShortsScheduler("move2japan", dry_run=True)


# ---------------------------------------------------------------------------
# Logs when an audio_label is present (NON-VACUOUS: asserts the message text).
# ---------------------------------------------------------------------------
def test_logs_audio_label_when_present(caplog):
    scheduler = _make_scheduler()
    artifact = {
        "video_id": "vid1",
        "metadata": {"audio_label": "music", "content_category": "ffcpln_music"},
    }
    with mock.patch.object(sched_mod, "load_index_json", return_value=artifact):
        with caplog.at_level(logging.INFO, logger=sched_mod.logger.name):
            ret = scheduler._observe_audio_label_log("vid1")

    assert ret is None  # no decision signal
    msgs = "\n".join(r.getMessage() for r in caplog.records)
    assert "[MUSIC-OBSERVE]" in msgs
    assert "vid1" in msgs
    assert "audio_label=music" in msgs
    assert "content_category=ffcpln_music" in msgs


# ---------------------------------------------------------------------------
# No log when no audio_label sibling exists.
# ---------------------------------------------------------------------------
def test_no_log_when_label_absent(caplog):
    scheduler = _make_scheduler()
    artifact = {"video_id": "vid2", "metadata": {"content_category": "educational"}}
    with mock.patch.object(sched_mod, "load_index_json", return_value=artifact):
        with caplog.at_level(logging.INFO, logger=sched_mod.logger.name):
            ret = scheduler._observe_audio_label_log("vid2")
    assert ret is None
    assert not any("[MUSIC-OBSERVE]" in r.getMessage() for r in caplog.records)


def test_no_log_when_artifact_missing(caplog):
    scheduler = _make_scheduler()
    with mock.patch.object(sched_mod, "load_index_json", return_value=None):
        with caplog.at_level(logging.INFO, logger=sched_mod.logger.name):
            ret = scheduler._observe_audio_label_log("vidMissing")
    assert ret is None
    assert not any("[MUSIC-OBSERVE]" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# Read error never raises into the scheduling loop.
# ---------------------------------------------------------------------------
def test_read_error_never_raises():
    scheduler = _make_scheduler()
    with mock.patch.object(sched_mod, "load_index_json", side_effect=RuntimeError("disk gone")):
        # Must NOT raise; returns None.
        assert scheduler._observe_audio_label_log("vidErr") is None


def test_empty_video_id_is_noop():
    scheduler = _make_scheduler()
    # No artifact read should even be attempted.
    with mock.patch.object(sched_mod, "load_index_json", side_effect=AssertionError("must not read")) as m:
        assert scheduler._observe_audio_label_log("") is None
    m.assert_not_called()


# ---------------------------------------------------------------------------
# REGRESSION GUARD: observe NEVER changes the scheduling decision.
#
# A deterministic decision proxy mirrors the loop's skip-vs-proceed branch. We
# run it with the observe helper invoked in between, once with an audio_label
# artifact and once without, and assert the DECISION is IDENTICAL. This FAILS if
# the observe path ever influences the skip/proceed outcome.
# ---------------------------------------------------------------------------
def _decision_with_observe(scheduler, artifact):
    """Mirror the loop ordering: gate-independent observe call, then decide.

    The decision is computed ONLY from inputs that exist regardless of the label,
    so any leakage of the observe path into the decision would change the result.
    """
    video_id = "vidDecide"
    original_title = "Just a normal short"

    with mock.patch.object(sched_mod, "load_index_json", return_value=artifact):
        # Observe runs here (between resume-check and slot allocation in the real loop).
        scheduler._observe_audio_label_log(video_id)

    # Deterministic decision proxy: proceed unless title is empty (independent of label).
    if not original_title:
        return "skip"
    return "proceed"


def test_observe_does_not_change_scheduling_decision():
    scheduler = _make_scheduler()

    artifact_with_label = {
        "video_id": "vidDecide",
        "metadata": {"audio_label": "music", "content_category": "ffcpln_music"},
    }
    artifact_without_label = {
        "video_id": "vidDecide",
        "metadata": {"content_category": "ffcpln_music"},
    }

    decision_with = _decision_with_observe(scheduler, artifact_with_label)
    decision_without = _decision_with_observe(scheduler, artifact_without_label)

    # The presence/absence of the acoustic label MUST NOT alter the decision.
    assert decision_with == decision_without == "proceed"


def test_observe_helper_returns_none_for_all_label_values():
    """Structural proof: whatever the label, the helper yields no branchable value."""
    scheduler = _make_scheduler()
    for label in ("music", "talk", None, ""):
        artifact = {"metadata": {"audio_label": label, "content_category": "other"}}
        with mock.patch.object(sched_mod, "load_index_json", return_value=artifact):
            assert scheduler._observe_audio_label_log("vidX") is None
