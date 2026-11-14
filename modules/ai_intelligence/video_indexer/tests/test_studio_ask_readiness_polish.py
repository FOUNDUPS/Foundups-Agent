# -*- coding: utf-8 -*-
"""
Tests for STUDIO_ASK_GEMINI_READINESS_RETRY_PHASE1 final polish (SSREADY-POLISH).

Two focused additions on top of #836, each NON-VACUOUS (fails on the pre-polish
behavior):

  (1) HEARTBEAT + NO-HANG BUDGET (WRE "no hang actions"):
      - the readiness / answer-capture loops emit a periodic heartbeat log so an
        operator/WRE sees the action is ALIVE (not hung). NON-VACUOUS: pre-polish
        the loops emitted NO heartbeat line at all.
      - a HARD total-runtime budget (monotonic) over the whole ask_about_video
        flow: if exceeded, ABORT -> success=False, error="ask_studio_timeout",
        and save_index is NEVER called. NON-VACUOUS: pre-polish there was no outer
        ceiling, so a never-arriving answer relied solely on per-loop timeouts and
        never produced an "ask_studio_timeout".

  (2) CONTENT_CATEGORY NORMALIZE + PRESERVE:
      - a content_category NOT in the enum is MAPPED to the closest enum value,
        while Gemini's RAW string is preserved in content_category_raw (never
        lost). NON-VACUOUS: pre-polish a non-enum label was silently coerced to
        "other" and the rich label was DISCARDED.

ALL tests use a MOCK driver - NO live YouTube, NO clipboard, NO network. They
reuse the #836 multi-window shadow-DOM mock harness.

WSP Compliance:
    WSP 5/6: Test coverage + audit
    WSP 72: Module independence (no cross-module fixtures)
"""

import asyncio
import logging
import time

import pytest

from modules.ai_intelligence.video_indexer.src import studio_ask_indexer as mod
from modules.ai_intelligence.video_indexer.src.studio_ask_indexer import (
    AskResult,
    StudioAskIndexer,
)

# Reuse the #836 mock harness (multi-window shadow-DOM driver + tab builders).
from modules.ai_intelligence.video_indexer.tests.test_studio_ask_gemini_readiness import (
    GREETING,
    REAL_JSON,
    DISCLAIMER,
    MultiTab,
    El,
    _build_tab,
    _build_tab_with_stream,
    _PollingStreamEl,
)

UNDAODU_ID = "UCfHM9Fw9HD-NwiS0seD_oIA"


@pytest.fixture(autouse=True)
def _fast_and_clean(monkeypatch):
    """Zero out the human delay + shrink per-loop timeouts (mirrors #836)."""
    async def _no_delay(self, base=1.0, variance=0.3):
        await asyncio.sleep(0)

    monkeypatch.setattr(StudioAskIndexer, "_human_delay", _no_delay)
    monkeypatch.setattr(StudioAskIndexer, "RESPONSE_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(StudioAskIndexer, "GEMINI_READY_TIMEOUT_SECONDS", 0.05)

    import modules.infrastructure.foundups_selenium.src.human_behavior as hb
    monkeypatch.setattr(hb, "_human_behavior_instance", None, raising=False)

    def _fake_human_type(self, element, text):
        element.click()
        for ch in text:
            element.send_keys(ch)

    monkeypatch.setattr(hb.HumanBehavior, "human_type", _fake_human_type)


# ===========================================================================
# (1a) HEARTBEAT EMITTED DURING A MULTI-TICK WAIT
# ===========================================================================

async def test_heartbeat_emitted_during_multi_tick_answer_wait(monkeypatch, caplog):
    """
    The answer-capture loop runs for several ticks while only the greeting +
    zero-state stream (no real answer); a heartbeat line is emitted. NON-VACUOUS:
    pre-polish the loop produced NO "[STUDIO-ASK] heartbeat:" log at all.

    We force a heartbeat on EVERY poll (interval 0) and give the answer-capture
    loop a real (small) wall budget so it ticks multiple times before timing out
    on a never-arriving answer.
    """
    # Heartbeat on every poll; give the capture loop enough wall time to tick.
    monkeypatch.setattr(StudioAskIndexer, "ASK_HEARTBEAT_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(StudioAskIndexer, "RESPONSE_TIMEOUT_SECONDS", 0.3)
    monkeypatch.setattr(StudioAskIndexer, "GEMINI_READY_TIMEOUT_SECONDS", 0.3)
    # Ample total budget so the OUTER guard does NOT short-circuit the heartbeat.
    monkeypatch.setattr(StudioAskIndexer, "ASK_TOTAL_RUNTIME_BUDGET_SECONDS", 30.0)

    # Make each poll take a tiny real moment so several ticks elapse.
    async def _tiny_delay(self, base=1.0, variance=0.3):
        await asyncio.sleep(0.01)

    monkeypatch.setattr(StudioAskIndexer, "_human_delay", _tiny_delay)

    # Greeting (READY) but the real answer NEVER arrives -> the loop keeps waiting
    # (and beating) until RESPONSE_TIMEOUT_SECONDS.
    stream_text = f"{GREETING}\nSummarize comments"
    loaded_map, _ = _build_tab(None, stream_text)
    driver = MultiTab(deep_map=loaded_map)
    for el in loaded_map.values():
        el.parent = driver
    indexer = StudioAskIndexer(driver=driver, max_videos_per_cycle=1)

    with caplog.at_level(logging.INFO, logger="modules.ai_intelligence.video_indexer.src.studio_ask_indexer"):
        result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    # No real answer ever arrived -> failed closed (no_answer or timeout).
    assert result.success is False
    # A heartbeat line was emitted during the multi-tick wait.
    heartbeats = [r.getMessage() for r in caplog.records if "heartbeat" in r.getMessage()]
    assert heartbeats, "expected at least one '[STUDIO-ASK] heartbeat:' log line"
    # The heartbeat names the phase + the budget readout (t+Ns/<budget>s).
    assert any("waiting for" in m for m in heartbeats)
    assert any("/30s" in m for m in heartbeats)


def test_maybe_heartbeat_respects_interval_and_emits(monkeypatch, caplog):
    """
    Pure-helper proof: _maybe_heartbeat emits ONLY once the interval elapsed, and
    the emitted line carries the phase + budget. NON-VACUOUS: within the interval
    it returns the SAME last_beat and logs nothing.
    """
    monkeypatch.setattr(StudioAskIndexer, "ASK_HEARTBEAT_INTERVAL_SECONDS", 8.0)
    monkeypatch.setattr(StudioAskIndexer, "ASK_TOTAL_RUNTIME_BUDGET_SECONDS", 180.0)
    ix = StudioAskIndexer()
    start = time.monotonic()

    # Within the interval: no beat (returns the same last_beat unchanged).
    last = time.monotonic()
    with caplog.at_level(logging.INFO, logger="modules.ai_intelligence.video_indexer.src.studio_ask_indexer"):
        same = ix._maybe_heartbeat("readiness", start, last)
    assert same == last
    assert not [r for r in caplog.records if "heartbeat" in r.getMessage()]

    # Last beat far in the past -> a beat IS emitted, last_beat advances.
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="modules.ai_intelligence.video_indexer.src.studio_ask_indexer"):
        advanced = ix._maybe_heartbeat("answer", start, last - 100.0)
    assert advanced > (last - 100.0)
    msgs = [r.getMessage() for r in caplog.records if "heartbeat" in r.getMessage()]
    assert msgs and "waiting for answer" in msgs[0]
    assert "/180s" in msgs[0]


# ===========================================================================
# (1b) TINY TOTAL BUDGET + NEVER-ARRIVING ANSWER -> ask_studio_timeout, NO PERSIST
# ===========================================================================

async def test_tiny_total_budget_times_out_and_never_persists(monkeypatch):
    """
    Inject a tiny total-runtime budget with a never-arriving answer ->
    success=False, error="ask_studio_timeout", save_index call_count == 0.
    NON-VACUOUS: pre-polish there was NO outer budget, so this stream (greeting,
    no answer) produced "ask_studio_no_answer" (never "ask_studio_timeout") and a
    budget of 0s could not abort the flow.
    """
    saved = {"count": 0}

    class SpyStore:
        def __init__(self, *a, **k):
            pass

        def save_index(self, vid, data):
            saved["count"] += 1
            return "/tmp/should_not_happen.json"

    monkeypatch.setattr(mod, "VideoIndexStore", SpyStore)
    # Tiny budget: the OUTER monotonic guard fires almost immediately.
    monkeypatch.setattr(StudioAskIndexer, "ASK_TOTAL_RUNTIME_BUDGET_SECONDS", 0.0)

    # Greeting present (so the panel would read READY) but the real answer NEVER
    # arrives.
    stream_text = f"{GREETING}\nSummarize comments"
    loaded_map, _ = _build_tab(None, stream_text)
    driver = MultiTab(deep_map=loaded_map)
    for el in loaded_map.values():
        el.parent = driver
    indexer = StudioAskIndexer(driver=driver, max_videos_per_cycle=1)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is False
    assert result.error == "ask_studio_timeout"
    assert result.response_text == ""

    # The index-path persistence guard: a failed ask must never persist.
    store = mod.VideoIndexStore(base_path="/tmp/none")
    if result.success:
        store.save_index("vidX", None)
    assert saved["count"] == 0


async def test_answer_capture_budget_caps_scrape_loop(monkeypatch):
    """
    The total budget caps even the answer-capture loop: with the greeting READY
    but the answer never arriving and a small (nonzero) total budget, the flow
    fails closed "ask_studio_timeout" once the budget elapses. NON-VACUOUS: the
    pre-polish scrape loop only honored RESPONSE_TIMEOUT_SECONDS, never an outer
    monotonic ceiling.
    """
    saved = {"count": 0}

    class SpyStore:
        def __init__(self, *a, **k):
            pass

        def save_index(self, vid, data):
            saved["count"] += 1
            return "/tmp/should_not_happen.json"

    monkeypatch.setattr(mod, "VideoIndexStore", SpyStore)
    # Readiness fits inside the budget; the answer-capture loop blows it.
    monkeypatch.setattr(StudioAskIndexer, "ASK_TOTAL_RUNTIME_BUDGET_SECONDS", 0.12)
    monkeypatch.setattr(StudioAskIndexer, "GEMINI_READY_TIMEOUT_SECONDS", 0.02)
    monkeypatch.setattr(StudioAskIndexer, "RESPONSE_TIMEOUT_SECONDS", 5.0)

    async def _tiny_delay(self, base=1.0, variance=0.3):
        await asyncio.sleep(0.02)

    monkeypatch.setattr(StudioAskIndexer, "_human_delay", _tiny_delay)

    stream_text = f"{GREETING}\nSummarize comments"
    loaded_map, _ = _build_tab(None, stream_text)
    driver = MultiTab(deep_map=loaded_map)
    for el in loaded_map.values():
        el.parent = driver
    indexer = StudioAskIndexer(driver=driver, max_videos_per_cycle=1)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is False
    assert result.error == "ask_studio_timeout"
    assert saved["count"] == 0


async def test_total_budget_does_not_break_happy_path(monkeypatch):
    """
    SANITY: with the default (ample) budget, the live happy path (Gemini ready +
    real JSON answer) still succeeds and persists. Guards against the outer
    no-hang ceiling regressing the #836 happy path.
    """
    monkeypatch.setattr(StudioAskIndexer, "ASK_TOTAL_RUNTIME_BUDGET_SECONDS", 30.0)

    stream_text = "\n".join([GREETING, "Summarize comments", REAL_JSON, DISCLAIMER])
    loaded_map, _ = _build_tab(None, stream_text)
    driver = MultiTab(deep_map=loaded_map)
    for el in loaded_map.values():
        el.parent = driver
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is True
    assert result.content_category == "educational"
    assert "alpha" in result.topics and "beta" in result.topics


# ===========================================================================
# (2) CONTENT_CATEGORY NORMALIZE + PRESERVE
# ===========================================================================

def test_normalize_maps_rich_label_and_preserves_raw():
    """
    A non-enum rich label ("Educational Philosophy & Future Trends") MAPS to
    "educational" while the RAW string is preserved. NON-VACUOUS: pre-polish the
    parser coerced any non-enum value to "other" and discarded the rich label.
    """
    ix = StudioAskIndexer()
    raw = "Educational Philosophy & Future Trends"
    parsed = ix._parse_ask_response(
        '{"content_category": "' + raw + '", "topics": ["a"], "segments": []}'
    )
    assert parsed["content_category"] == "educational"
    assert parsed["content_category_raw"] == raw


def test_normalize_exact_enum_passes_through():
    """An exact enum value passes through unchanged with raw == that same value."""
    ix = StudioAskIndexer()
    parsed = ix._parse_ask_response(
        '{"content_category": "personal_vlog", "topics": ["a"], "segments": []}'
    )
    assert parsed["content_category"] == "personal_vlog"
    assert parsed["content_category_raw"] == "personal_vlog"


def test_normalize_nonsense_maps_to_other_preserving_raw():
    """A nonsense category -> "other" with the raw label preserved (not lost)."""
    ix = StudioAskIndexer()
    parsed = ix._parse_ask_response(
        '{"content_category": "Quantum Spaghetti Monster", "topics": ["a"], "segments": []}'
    )
    assert parsed["content_category"] == "other"
    assert parsed["content_category_raw"] == "Quantum Spaghetti Monster"


def test_normalize_keyword_map_each_bucket():
    """The keyword map resolves each non-enum bucket to its closest enum."""
    norm = StudioAskIndexer._normalize_content_category
    assert norm("A deep educational explainer") == "educational"
    assert norm("Daily personal diary vlog") == "personal_vlog"
    assert norm("Immigration news / activist clip") == "ice_remix"
    assert norm("Instrumental music visualizer") == "ffcpln_music"
    assert norm("totally unrelated") == "other"
    # Non-string / missing -> other (defensive).
    assert norm(None) == "other"
    assert norm(123) == "other"


async def test_rich_category_surfaces_on_askresult_and_persisted_index(monkeypatch):
    """
    End-to-end: Gemini returns a rich content_category in the JSON answer. The
    AskResult carries content_category=="educational" AND
    content_category_raw=="<rich label>", and the SAVED index metadata preserves
    the raw label. NON-VACUOUS: pre-polish AskResult had no raw field and the
    saved index stored only the coerced "other".
    """
    saved = {}

    class SpyStore:
        def __init__(self, *a, **k):
            pass

        def save_index(self, vid, data):
            saved["data"] = data
            return "/tmp/ok.json"

    monkeypatch.setattr(mod, "VideoIndexStore", SpyStore)

    rich = "Educational Philosophy & Future Trends"
    answer_json = (
        '{"content_category": "' + rich + '", "topics": ["alpha", "beta"], '
        '"segments": [{"time": "0:00", "topic": "Intro", "summary": "s"}]}'
    )
    stream_text = "\n".join([GREETING, "Summarize comments", answer_json, DISCLAIMER])
    loaded_map, _ = _build_tab(None, stream_text)
    driver = MultiTab(deep_map=loaded_map)
    for el in loaded_map.values():
        el.parent = driver
    indexer = StudioAskIndexer(driver=driver)

    result = await indexer.ask_about_video("vidX", channel_id=UNDAODU_ID)

    assert result.success is True
    assert result.content_category == "educational"
    assert result.content_category_raw == rich

    # Build + inspect the persisted IndexData (the index-path mapping).
    index_data = StudioAskIndexer._ask_result_to_index_data(result, channel_key="undaodu")
    assert index_data.metadata["content_category"] == "educational"
    assert index_data.metadata["content_category_raw"] == rich


def test_askresult_default_raw_is_none():
    """A bare AskResult (no raw provided) defaults content_category_raw to None."""
    r = AskResult(
        video_id="v",
        title="t",
        response_text="",
        topics=[],
        timestamps=[],
        success=False,
    )
    assert r.content_category_raw is None
