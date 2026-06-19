"""
Unit tests for the shorts_live_schedule_signal SKILLz (read-only live signals).

Slice: SHORTS_LIVE_SCHEDULE_AND_VIEW_SIGNAL_PHASE1

Model under test
----------------
Read two read-only signals from the YouTube Studio shorts list:
  1. ACCURATE scheduled count via the "Has schedule" filter (chip-bar input +
     filter dialog), reached through the shadow-piercing finder. When the filter
     CANNOT be applied -> scheduled_count = None (UNKNOWN), NEVER a false 0.
  2. Per-video VIEW count -> a low-viewed signal (views strictly below threshold;
     UNKNOWN views never counted as low-viewed).

These tests are MOCK-ONLY (no live browser, no daemon, no live models) and
NON-VACUOUS:
  - accurate scheduled count when rows exist (NOT 0),
  - the false-0 is fixed: a present-schedule channel returns > 0,
  - views parsed from the list,
  - filter-fail returns UNKNOWN/None, NOT 0,
  - a reproduction of the OLD timing-out behavior (returns a false 0) is asserted,
    then the NEW path on the SAME timeout returns UNKNOWN (None) instead -- so a
    regression back to the false-0 behavior FAILS this test,
  - breadcrumb + PatternMemory emission are invoked (mocked + asserted),
  - parsing responds to the injected DOM (a static impl fails).
"""

from unittest.mock import MagicMock, patch

import pytest

from modules.platform_integration.youtube_shorts_scheduler.skillz.shorts_live_schedule_signal.executor import (
    DEFAULT_LOW_VIEW_THRESHOLD,
    LIVE_SIGNAL_ENABLED_ENV,
    parse_row_signal,
    parse_view_count,
    read_live_schedule_signal,
    run_skill,
    summarize_rows,
)


# --- A mock Studio DOM: rows with scheduled/views + a "Has schedule" filter ---

def _mock_rows_present_schedule():
    """Raw scraped rows as the shadow-pierced JS scrape would return them.

    3 scheduled rows + 2 unlisted rows, mixed view counts including a low-viewed
    one and an UNKNOWN-views one.
    """
    return [
        {"video_id": "sch1", "visibility_text": "Scheduled", "scheduled_date": "Feb 5, 2026", "views_text": "0 views"},
        {"video_id": "sch2", "visibility_text": "Scheduled", "scheduled_date": "Feb 6, 2026", "views_text": "1.2K views"},
        {"video_id": "sch3", "visibility_text": "Scheduled", "scheduled_date": "Feb 7, 2026", "views_text": "12 views"},
        {"video_id": "unl1", "visibility_text": "Unlisted", "scheduled_date": "", "views_text": "5 views"},
        {"video_id": "unl2", "visibility_text": "Unlisted", "scheduled_date": "", "views_text": "-"},
    ]


def _filter_ok(_driver):
    """A 'Has schedule' applier that succeeds (mock live filter applied)."""
    return True


def _filter_timeout(_driver):
    """A 'Has schedule' applier that FAILS (simulates the live filter TIMEOUT).

    This is the failure the real [CPS-AUDIT] path hits on the Edge channels.
    """
    return False


# ---------------------------------------------------------------------------
# parse_view_count: pure parser
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text,expected",
    [
        ("1,234 views", 1234),
        ("1.2K views", 1200),
        ("3.4M", 3_400_000),
        ("2B views", 2_000_000_000),
        ("0", 0),
        ("0 views", 0),
        ("12 views", 12),
        ("1,000,000 views", 1_000_000),
        ("1.234", 1234),       # plain thousands separator, no suffix
        ("-", None),           # UNKNOWN, distinct from 0
        ("", None),
        (None, None),
        ("No views", None),
    ],
)
def test_parse_view_count(text, expected):
    assert parse_view_count(text) == expected


def test_parse_view_count_unknown_is_not_zero():
    """UNKNOWN views must be None, NOT 0 (so it is never a low-viewed false hit)."""
    assert parse_view_count("-") is None
    assert parse_view_count("0") == 0
    assert parse_view_count("-") != parse_view_count("0")


# ---------------------------------------------------------------------------
# parse_row_signal + summarize_rows: pure aggregation
# ---------------------------------------------------------------------------

def test_parse_row_signal_scheduled_flag_from_label():
    row = parse_row_signal(
        {"video_id": "x", "visibility_text": "Scheduled", "scheduled_date": "Feb 5, 2026", "views_text": "9 views"}
    )
    assert row.scheduled is True
    assert row.scheduled_date == "Feb 5, 2026"
    assert row.views == 9


def test_parse_row_signal_unlisted_has_no_scheduled_date():
    row = parse_row_signal(
        {"video_id": "x", "visibility_text": "Unlisted", "scheduled_date": "Feb 5, 2026", "views_text": "9 views"}
    )
    assert row.scheduled is False
    assert row.scheduled_date is None  # date only carried for scheduled rows


def test_summarize_counts_scheduled_and_low_viewed():
    rows = [parse_row_signal(r) for r in _mock_rows_present_schedule()]
    summary = summarize_rows(rows, low_view_threshold=100)

    # 3 scheduled rows -> count is 3, NOT 0.
    assert summary["scheduled_count"] == 3
    # low-viewed (<100, views known): sch1(0), sch3(12), unl1(5) = 3.
    # sch2 (1200) is high; unl2 (UNKNOWN) is NOT low-viewed.
    assert summary["low_viewed_count"] == 3
    low_ids = {v["video_id"] for v in summary["low_viewed_videos"]}
    assert low_ids == {"sch1", "sch3", "unl1"}
    assert "unl2" not in low_ids  # UNKNOWN views never counted low-viewed


# ---------------------------------------------------------------------------
# read_live_schedule_signal: orchestration (accurate count + fail-safe)
# ---------------------------------------------------------------------------

def test_accurate_scheduled_count_when_rows_exist():
    """Filter applied + rows present -> accurate scheduled_count > 0 (NOT a false 0)."""
    signal = read_live_schedule_signal(
        MagicMock(),
        channel_id="UC_FOUNDUPS",
        apply_filter_fn=_filter_ok,
        scrape_fn=lambda d: _mock_rows_present_schedule(),
    )
    assert signal["filter_applied"] is True
    assert signal["scheduled_count"] == 3        # the load-bearing assertion
    assert signal["scheduled_count"] != 0        # false-0 is fixed
    assert signal["scheduled_count_status"] == "ok"
    assert signal["success"] is True


def test_false_zero_is_fixed_present_schedule_channel_returns_positive():
    """A present-schedule channel must NOT report 0 when the filter is applied."""
    signal = read_live_schedule_signal(
        MagicMock(),
        channel_id="UC_ANTIFAFM",
        apply_filter_fn=_filter_ok,
        scrape_fn=lambda d: _mock_rows_present_schedule(),
    )
    assert signal["scheduled_count"] > 0


def test_views_parsed_from_list():
    """Per-video views are parsed into the signal output."""
    signal = read_live_schedule_signal(
        MagicMock(),
        channel_id="UC_FOUNDUPS",
        apply_filter_fn=_filter_ok,
        scrape_fn=lambda d: _mock_rows_present_schedule(),
    )
    views_by_id = {v["video_id"]: v["views"] for v in signal["videos"]}
    assert views_by_id["sch2"] == 1200
    assert views_by_id["sch1"] == 0
    assert views_by_id["unl2"] is None  # UNKNOWN preserved as None
    assert signal["patterns"]["views_parsed"] is True


def test_filter_fail_returns_unknown_not_zero():
    """Filter cannot be applied (TIMEOUT) -> scheduled_count is None (UNKNOWN), NOT 0."""
    signal = read_live_schedule_signal(
        MagicMock(),
        channel_id="UC_FOUNDUPS",
        apply_filter_fn=_filter_timeout,
        # Even if rows could be scraped, a non-applied filter must not be trusted.
        scrape_fn=lambda d: _mock_rows_present_schedule(),
    )
    assert signal["filter_applied"] is False
    assert signal["scheduled_count"] is None      # UNKNOWN, not 0
    assert signal["scheduled_count"] != 0
    assert signal["scheduled_count_status"] == "unknown_filter_not_applied"
    assert signal["success"] is False


# ---------------------------------------------------------------------------
# Regression anchor: the OLD timing-out behavior returned a FALSE 0.
# The NEW path on the SAME timeout returns UNKNOWN (None). A regression back to
# the old false-0 behavior FAILS this test.
# ---------------------------------------------------------------------------

def _old_audit_path_on_timeout(rows):
    """Reproduction of the OLD [CPS-AUDIT] behavior.

    Mirrors content_page_scheduler.audit_calendar(): when the visibility filter
    fails it "continues unfiltered" and then scrapes XPATH_SCHEDULED_ROWS on a
    page where the Scheduled view never loaded -> 0 rows -> "Total scheduled: 0".
    We model the timeout as: filter not applied -> the scheduled-row scrape yields
    nothing -> count 0. THIS IS THE BUG.
    """
    filter_applied = False  # the timeout
    if not filter_applied:
        scheduled_rows = []  # unfiltered page: scheduled scrape finds nothing
    else:  # pragma: no cover - not the timeout case here
        scheduled_rows = [r for r in rows if "scheduled" in r["visibility_text"].lower()]
    return len(scheduled_rows)  # -> 0 (false)


def test_old_path_produces_false_zero_then_new_path_returns_unknown():
    """Pin the bug, then prove the new path does NOT reproduce it.

    Step 1: the OLD path on a timeout returns a false 0 (the documented bug).
    Step 2: the NEW path on the SAME timeout returns None (UNKNOWN), never 0.
    """
    rows = _mock_rows_present_schedule()

    # Step 1: the OLD behavior is the false 0 (the bug we are fixing).
    old_count = _old_audit_path_on_timeout(rows)
    assert old_count == 0  # demonstrates the false-0 bug exists in the old path

    # Step 2: the NEW path on the same timeout must NOT return 0.
    new_signal = read_live_schedule_signal(
        MagicMock(),
        channel_id="UC_FOUNDUPS",
        apply_filter_fn=_filter_timeout,  # same timeout
        scrape_fn=lambda d: rows,
    )
    assert new_signal["scheduled_count"] is None        # UNKNOWN
    assert new_signal["scheduled_count"] != old_count   # i.e. != 0 (false)


# ---------------------------------------------------------------------------
# Non-vacuity: the signal MUST depend on the injected DOM.
# ---------------------------------------------------------------------------

def test_signal_responds_to_dom_not_static():
    """Changing the mock DOM changes the count -> proves the scrape drives it.

    A static impl that ignored the DOM (e.g. always 3, or always 0) would keep
    the SAME count; this asserts the count FLIPS with the injected rows.
    """
    sig_three = read_live_schedule_signal(
        MagicMock(),
        channel_id="UC_X",
        apply_filter_fn=_filter_ok,
        scrape_fn=lambda d: _mock_rows_present_schedule(),  # 3 scheduled
    )
    one_scheduled = [
        {"video_id": "only", "visibility_text": "Scheduled", "scheduled_date": "Feb 9, 2026", "views_text": "7 views"},
        {"video_id": "u", "visibility_text": "Unlisted", "scheduled_date": "", "views_text": "7 views"},
    ]
    sig_one = read_live_schedule_signal(
        MagicMock(),
        channel_id="UC_X",
        apply_filter_fn=_filter_ok,
        scrape_fn=lambda d: one_scheduled,
    )
    assert sig_three["scheduled_count"] == 3
    assert sig_one["scheduled_count"] == 1
    assert sig_three["scheduled_count"] != sig_one["scheduled_count"]


# ---------------------------------------------------------------------------
# Signal emission: breadcrumb + PatternMemory must be invoked.
# ---------------------------------------------------------------------------

def test_run_skill_emits_breadcrumb_and_pattern_memory(monkeypatch):
    """run_skill must emit a live_schedule_signal breadcrumb AND a SkillOutcome."""
    monkeypatch.setenv(LIVE_SIGNAL_ENABLED_ENV, "1")  # enable live read for this test
    with patch(
        "modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry"
    ) as bc, patch(
        "modules.infrastructure.wre_core.src.pattern_memory.PatternMemory"
    ) as pm, patch(
        "modules.infrastructure.wre_core.src.pattern_memory.SkillOutcome"
    ) as outcome:
        result = run_skill(
            channel="UC_FOUNDUPS",            # UC... id -> no registry lookup
            driver=MagicMock(),
            apply_filter_fn=_filter_ok,
            scrape_fn=lambda d: _mock_rows_present_schedule(),
            emit_signals=True,
        )

        bc.return_value.store_breadcrumb.assert_called_once()
        kwargs = bc.return_value.store_breadcrumb.call_args.kwargs
        assert kwargs["event_type"] == "live_schedule_signal"
        assert kwargs["source_dae"] == "youtube_shorts_scheduler"
        assert kwargs["metadata"]["scheduled_count"] == 3

        pm.return_value.store_outcome.assert_called_once()
        outcome.assert_called_once()

    assert result["success"] is True
    assert result["scheduled_count"] == 3
    assert result["breadcrumb_emitted"] is True
    assert result["outcome_stored"] is True


def test_run_skill_no_driver_returns_unknown_not_zero(monkeypatch):
    """No live browser (flag ON) -> scheduled_count None (UNKNOWN), never a false 0."""
    monkeypatch.setenv(LIVE_SIGNAL_ENABLED_ENV, "1")  # enabled; gate passes, driver None
    with patch(
        "modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry"
    ), patch(
        "modules.infrastructure.wre_core.src.pattern_memory.PatternMemory"
    ), patch(
        "modules.infrastructure.wre_core.src.pattern_memory.SkillOutcome"
    ):
        result = run_skill(channel="UC_FOUNDUPS", driver=None, emit_signals=True)
    assert result["scheduled_count"] is None
    assert result["scheduled_count_status"] == "unknown_no_driver"
    assert result["success"] is False


def test_run_skill_no_signals_skips_emission(monkeypatch):
    """emit_signals=False must NOT emit breadcrumb/outcome (diagnostic path)."""
    monkeypatch.setenv(LIVE_SIGNAL_ENABLED_ENV, "1")  # enable live read for this test
    with patch(
        "modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry"
    ) as bc, patch(
        "modules.infrastructure.wre_core.src.pattern_memory.PatternMemory"
    ) as pm:
        result = run_skill(
            channel="UC_FOUNDUPS",
            driver=MagicMock(),
            apply_filter_fn=_filter_ok,
            scrape_fn=lambda d: _mock_rows_present_schedule(),
            emit_signals=False,
        )
        bc.return_value.store_breadcrumb.assert_not_called()
        pm.return_value.store_outcome.assert_not_called()
    assert result["breadcrumb_emitted"] is False
    assert result["outcome_stored"] is False


def test_default_low_view_threshold_is_sane():
    assert DEFAULT_LOW_VIEW_THRESHOLD == 100


# ---------------------------------------------------------------------------
# Auto-fire COST self-gate (SHORTS_SKILLZ_AUTONOMOUS_REGISTRATION_PHASE1).
# The skill now carries `domain: youtube` and auto-fires every cadence cycle.
# A live DOM round-trip is costly + contends with the daemon browser, so the
# executor SELF-GATES on YT_LIVE_SCHEDULE_SIGNAL_ENABLED (default "0"):
#   - flag OFF  -> NO-OP: filter applier + scrape are NEVER called, no DOM touch.
#   - flag ON   -> runs as before (mock scrape drives an accurate count).
# These are the load-bearing non-vacuity assertions: a regression that scrapes
# the DOM while the flag is off FAILS (assert the scrape/filter not called).
# ---------------------------------------------------------------------------

def test_disabled_by_default_no_ops_without_touching_dom(monkeypatch):
    """Flag OFF (default): no browser/filter/scrape, scheduled_count UNKNOWN not 0.

    The apply_filter_fn and scrape_fn are MagicMocks that MUST NOT be invoked.
    If the executor scrapes the DOM while disabled, these assertions FAIL.
    """
    monkeypatch.delenv(LIVE_SIGNAL_ENABLED_ENV, raising=False)  # ensure default-off

    apply_filter_spy = MagicMock(return_value=True)
    scrape_spy = MagicMock(return_value=_mock_rows_present_schedule())

    with patch(
        "modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry"
    ), patch(
        "modules.infrastructure.wre_core.src.pattern_memory.PatternMemory"
    ), patch(
        "modules.infrastructure.wre_core.src.pattern_memory.SkillOutcome"
    ):
        result = run_skill(
            channel="UC_FOUNDUPS",
            driver=MagicMock(),               # a driver IS available...
            apply_filter_fn=apply_filter_spy,  # ...but these must NOT be called
            scrape_fn=scrape_spy,
            emit_signals=True,
        )

    # The DOM was NOT touched (the whole point of the cost gate).
    apply_filter_spy.assert_not_called()
    scrape_spy.assert_not_called()

    assert result["skipped"] is True
    assert result["skip_reason"] == "disabled_by_flag"
    assert result["scheduled_count"] is None         # UNKNOWN, never a false 0
    assert result["scheduled_count"] != 0
    assert result["scheduled_count_status"] == "skipped_disabled_by_flag"
    assert result["enabled_env"] == LIVE_SIGNAL_ENABLED_ENV


def test_disabled_explicit_zero_no_ops(monkeypatch):
    """Flag explicitly '0' also no-ops (not just unset)."""
    monkeypatch.setenv(LIVE_SIGNAL_ENABLED_ENV, "0")
    scrape_spy = MagicMock(return_value=_mock_rows_present_schedule())
    with patch(
        "modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry"
    ), patch(
        "modules.infrastructure.wre_core.src.pattern_memory.PatternMemory"
    ), patch(
        "modules.infrastructure.wre_core.src.pattern_memory.SkillOutcome"
    ):
        result = run_skill(
            channel="UC_FOUNDUPS",
            driver=MagicMock(),
            apply_filter_fn=_filter_ok,
            scrape_fn=scrape_spy,
            emit_signals=False,
        )
    scrape_spy.assert_not_called()
    assert result["skipped"] is True
    assert result["scheduled_count"] is None


def test_disabled_no_op_still_emits_signals(monkeypatch):
    """Even when skipped, the fired-but-skipped run is recorded (breadcrumb + outcome)."""
    monkeypatch.delenv(LIVE_SIGNAL_ENABLED_ENV, raising=False)
    with patch(
        "modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry"
    ) as bc, patch(
        "modules.infrastructure.wre_core.src.pattern_memory.PatternMemory"
    ) as pm, patch(
        "modules.infrastructure.wre_core.src.pattern_memory.SkillOutcome"
    ):
        result = run_skill(
            channel="UC_FOUNDUPS",
            driver=MagicMock(),
            apply_filter_fn=_filter_ok,
            scrape_fn=lambda d: _mock_rows_present_schedule(),
            emit_signals=True,
        )
        bc.return_value.store_breadcrumb.assert_called_once()
        pm.return_value.store_outcome.assert_called_once()
    assert result["skipped"] is True
    assert result["breadcrumb_emitted"] is True
    assert result["outcome_stored"] is True


def test_enabled_runs_live_path_and_scrapes(monkeypatch):
    """Flag ON: the gate passes, the (mock) scrape IS called, accurate count returned."""
    monkeypatch.setenv(LIVE_SIGNAL_ENABLED_ENV, "1")
    scrape_spy = MagicMock(return_value=_mock_rows_present_schedule())
    with patch(
        "modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry"
    ), patch(
        "modules.infrastructure.wre_core.src.pattern_memory.PatternMemory"
    ), patch(
        "modules.infrastructure.wre_core.src.pattern_memory.SkillOutcome"
    ):
        result = run_skill(
            channel="UC_FOUNDUPS",
            driver=MagicMock(),
            apply_filter_fn=_filter_ok,
            scrape_fn=scrape_spy,
            emit_signals=True,
        )
    scrape_spy.assert_called_once()                  # the DOM read DID happen when enabled
    assert result.get("skipped") is not True
    assert result["scheduled_count"] == 3            # accurate, mock-driven
    assert result["success"] is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
