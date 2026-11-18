"""
Unit tests for the reschedule_applier + reschedule_apply SKILLz (Mode B Phase 2).

Slice: SHORTS_RESCHEDULE_APPLY_PHASE2

Model under test
----------------
apply_moves consumes #851 plan rows and, per move:
  - DEFAULT DRY-RUN (YT_RESCHEDULE_APPLY != "1"): logs "would move", NEVER touches
    the DOM picker/save helpers, records status `dry_run`.
  - APPLY (YT_RESCHEDULE_APPLY == "1") with a driver: calls
    dom.reschedule_open_set_save(to_date, slot_local, video_id=...) per move.
  - `(needs-live-list)` -> skipped (reason needs_live_list).
  - target-day cap would be exceeded -> skipped (reason cap).
  - per-move exception -> error, batch continues.

These tests are MOCK-ONLY (no live browser, no daemon, no live models) and
NON-VACUOUS:
  - apply path asserts the picker is called with the EXACT date+time per move.
  - test_dryrun_must_not_call_dom_helpers PROVES the dry-run guard: it would FAIL
    if dry-run ever called the mutating helpers (the whole point of "merge mutates
    nothing").
"""

from unittest.mock import MagicMock, patch

import pytest

from modules.platform_integration.youtube_shorts_scheduler.src.reschedule_applier import (
    NEEDS_LIVE_LIST,
    STATUS_APPLIED,
    STATUS_DRY_RUN,
    STATUS_ERROR,
    STATUS_SKIPPED,
    apply_enabled,
    apply_moves,
    apply_plan,
    flatten_plan_moves,
)


# --- helpers -----------------------------------------------------------------

def _move(video_id, to_date="Jan 2, 2026", slot_local="8:00 AM", channel_id="UC_x",
          from_date="Jan 5, 2026", slot_et="08:00"):
    return {
        "channel_id": channel_id,
        "channel_name": "FoundUps",
        "from_date": from_date,
        "to_date": to_date,
        "slot_et": slot_et,
        "slot_local": slot_local,
        "video_id": video_id,
    }


def _mock_dom(ok=True):
    """A DOM whose reschedule_open_set_save records calls and returns `ok`."""
    dom = MagicMock()
    dom.reschedule_open_set_save.return_value = ok
    return dom


# --- dry-run (default) -------------------------------------------------------

def test_dryrun_default_logs_moves_without_dom(monkeypatch):
    """Default (no env, no driver) is dry-run: moves recorded as dry_run, no DOM."""
    monkeypatch.delenv("YT_RESCHEDULE_APPLY", raising=False)
    dom = _mock_dom()
    moves = [_move("vid1"), _move("vid2", to_date="Jan 3, 2026")]

    result = apply_moves(moves, dom=dom, emit_signals=False)

    assert result["dry_run"] is True
    assert result["dry_run_count"] == 2
    assert result["applied"] == 0
    assert all(r["status"] == STATUS_DRY_RUN for r in result["results"])
    dom.reschedule_open_set_save.assert_not_called()


def test_dryrun_must_not_call_dom_helpers(monkeypatch):
    """NON-VACUITY / merge-safety proof: dry-run NEVER calls the mutating helper.

    If apply_moves wrongly drove the picker in dry-run, this assertion FAILS --
    which is exactly the regression we must catch (merging mutates nothing).
    """
    monkeypatch.setenv("YT_RESCHEDULE_APPLY", "0")
    dom = _mock_dom()
    # Spy that EXPLODES if anyone tries to drive a mutation in dry-run.
    dom.reschedule_open_set_save.side_effect = AssertionError(
        "dry-run must not call reschedule_open_set_save"
    )

    result = apply_moves([_move("vid1")], dom=dom, emit_signals=False)

    assert result["dry_run"] is True
    assert result["results"][0]["status"] == STATUS_DRY_RUN
    # Also assert directly that no mutation was attempted.
    dom.reschedule_open_set_save.assert_not_called()


def test_apply_enabled_env_gate(monkeypatch):
    monkeypatch.setenv("YT_RESCHEDULE_APPLY", "1")
    assert apply_enabled() is True
    monkeypatch.setenv("YT_RESCHEDULE_APPLY", "0")
    assert apply_enabled() is False
    monkeypatch.delenv("YT_RESCHEDULE_APPLY", raising=False)
    assert apply_enabled() is False


# --- apply (flag on) ---------------------------------------------------------

def test_apply_calls_picker_with_correct_date_time(monkeypatch):
    """YT_RESCHEDULE_APPLY=1: picker called with the exact date+time per move."""
    monkeypatch.setenv("YT_RESCHEDULE_APPLY", "1")
    dom = _mock_dom(ok=True)
    moves = [
        _move("vidA", to_date="Jan 2, 2026", slot_local="8:00 AM"),
        _move("vidB", to_date="Jan 3, 2026", slot_local="12:00 PM"),
    ]

    result = apply_moves(moves, dom=dom, emit_signals=False)

    assert result["dry_run"] is False
    assert result["applied"] == 2
    assert all(r["status"] == STATUS_APPLIED for r in result["results"])
    # Exact picker args per move (date=to_date, time=slot_local, scoped by video_id).
    calls = dom.reschedule_open_set_save.call_args_list
    assert calls[0].args == ("Jan 2, 2026", "8:00 AM")
    assert calls[0].kwargs == {"video_id": "vidA"}
    assert calls[1].args == ("Jan 3, 2026", "12:00 PM")
    assert calls[1].kwargs == {"video_id": "vidB"}


def test_apply_force_dry_run_overrides_env(monkeypatch):
    """dry_run=True forces dry-run even when the env flag says apply."""
    monkeypatch.setenv("YT_RESCHEDULE_APPLY", "1")
    dom = _mock_dom()
    result = apply_moves([_move("vid1")], dom=dom, dry_run=True, emit_signals=False)
    assert result["dry_run"] is True
    dom.reschedule_open_set_save.assert_not_called()


# --- skip: needs-live-list ---------------------------------------------------

def test_needs_live_list_is_skipped(monkeypatch):
    monkeypatch.setenv("YT_RESCHEDULE_APPLY", "1")
    dom = _mock_dom()
    moves = [_move(NEEDS_LIVE_LIST), _move("realvid")]

    result = apply_moves(moves, dom=dom, emit_signals=False)

    statuses = [r["status"] for r in result["results"]]
    assert statuses == [STATUS_SKIPPED, STATUS_APPLIED]
    assert result["results"][0]["reason"] == "needs_live_list"
    # Only the real video is applied -- the sentinel never reaches the picker.
    dom.reschedule_open_set_save.assert_called_once()
    assert dom.reschedule_open_set_save.call_args.kwargs == {"video_id": "realvid"}


# --- skip: cap safety --------------------------------------------------------

def test_cap_exceeded_on_target_is_skipped(monkeypatch):
    """cap=3 on the SAME target day: 4th move onto that day is skipped (reason cap)."""
    monkeypatch.setenv("YT_RESCHEDULE_APPLY", "1")
    dom = _mock_dom()
    same_day = "Jan 2, 2026"
    moves = [
        _move("v1", to_date=same_day),
        _move("v2", to_date=same_day),
        _move("v3", to_date=same_day),
        _move("v4", to_date=same_day),  # exceeds cap=3
    ]

    result = apply_moves(moves, dom=dom, cap=3, emit_signals=False)

    statuses = [r["status"] for r in result["results"]]
    assert statuses == [STATUS_APPLIED, STATUS_APPLIED, STATUS_APPLIED, STATUS_SKIPPED]
    assert result["results"][3]["reason"] == "cap"
    assert result["applied"] == 3
    assert result["skipped"] == 1
    assert dom.reschedule_open_set_save.call_count == 3


def test_cap_guard_also_applies_in_dry_run(monkeypatch):
    """The cap guard holds in dry-run too (would-be 4th onto a day is skipped)."""
    monkeypatch.delenv("YT_RESCHEDULE_APPLY", raising=False)
    dom = _mock_dom()
    day = "Jan 2, 2026"
    moves = [_move(f"v{i}", to_date=day) for i in range(4)]

    result = apply_moves(moves, dom=dom, cap=3, emit_signals=False)

    assert result["dry_run_count"] == 3
    assert result["skipped"] == 1
    assert result["results"][3]["reason"] == "cap"
    dom.reschedule_open_set_save.assert_not_called()


# --- per-move error: batch continues ----------------------------------------

def test_per_move_error_continues_batch(monkeypatch):
    """One failing move -> status error; the batch keeps going."""
    monkeypatch.setenv("YT_RESCHEDULE_APPLY", "1")
    dom = MagicMock()
    # First call raises, second succeeds.
    dom.reschedule_open_set_save.side_effect = [RuntimeError("boom"), True]
    moves = [_move("vbad", to_date="Jan 2, 2026"), _move("vok", to_date="Jan 3, 2026")]

    result = apply_moves(moves, dom=dom, emit_signals=False)

    statuses = [r["status"] for r in result["results"]]
    assert statuses == [STATUS_ERROR, STATUS_APPLIED]
    assert result["errors"] == 1
    assert result["applied"] == 1
    assert "boom" in result["results"][0]["reason"]
    assert dom.reschedule_open_set_save.call_count == 2


def test_dom_returns_false_is_error(monkeypatch):
    """A picker that returns False (without raising) is recorded as error."""
    monkeypatch.setenv("YT_RESCHEDULE_APPLY", "1")
    dom = _mock_dom(ok=False)
    result = apply_moves([_move("v1")], dom=dom, emit_signals=False)
    assert result["results"][0]["status"] == STATUS_ERROR
    assert result["results"][0]["reason"] == "dom_returned_false"


def test_apply_requested_without_driver_is_error(monkeypatch):
    """Apply requested but no driver -> error per move (no browser auto-launch)."""
    monkeypatch.setenv("YT_RESCHEDULE_APPLY", "1")
    result = apply_moves([_move("v1")], dom=None, emit_signals=False)
    assert result["results"][0]["status"] == STATUS_ERROR


# --- plan plumbing -----------------------------------------------------------

def test_flatten_plan_moves():
    plan = {
        "channels": [
            {"moves": [_move("a"), _move("b")]},
            {"moves": [_move("c")]},
            {"moves": []},
        ]
    }
    flat = flatten_plan_moves(plan)
    assert [m["video_id"] for m in flat] == ["a", "b", "c"]


def test_apply_plan_uses_factory_and_is_dry_run_by_default(monkeypatch):
    """apply_plan pulls moves from the injected plan factory; default dry-run."""
    monkeypatch.delenv("YT_RESCHEDULE_APPLY", raising=False)
    dom = _mock_dom()
    plan = {
        "summary": {"days_over_cap": 1, "total_moves": 1, "unplaceable_moves": 0},
        "channels": [{"moves": [_move("vid1")]}],
    }
    result = apply_plan(dom=dom, plan_factory=lambda: plan, emit_signals=False)

    assert result["skill"] == "reschedule_apply"
    assert result["dry_run"] is True
    assert result["dry_run_count"] == 1
    assert result["plan_summary"] == plan["summary"]
    assert result["success"] is True
    dom.reschedule_open_set_save.assert_not_called()


# --- SKILLz executor / run_skill --------------------------------------------

def test_executor_run_skill_default_dry_run(monkeypatch):
    monkeypatch.delenv("YT_RESCHEDULE_APPLY", raising=False)
    from modules.platform_integration.youtube_shorts_scheduler.skillz.reschedule_apply.executor import (
        run_skill,
    )
    plan = {
        "summary": {"days_over_cap": 1, "total_moves": 1, "unplaceable_moves": 0},
        "channels": [{"moves": [_move("vid1")]}],
    }
    result = run_skill(plan_factory=lambda: plan, emit_signals=False)
    assert result["skill"] == "reschedule_apply"
    assert result["apply_env"] == "YT_RESCHEDULE_APPLY"
    assert result["apply_enabled"] is False
    assert result["dry_run"] is True


# --- signal emission (mocked + asserted) ------------------------------------

def test_signals_emitted_per_move(monkeypatch):
    """Breadcrumb + PatternMemory invoked once per move when emit_signals=True."""
    monkeypatch.delenv("YT_RESCHEDULE_APPLY", raising=False)
    with patch(
        "modules.platform_integration.youtube_shorts_scheduler.src.reschedule_applier._emit_move_breadcrumb"
    ) as mock_bc, patch(
        "modules.platform_integration.youtube_shorts_scheduler.src.reschedule_applier._store_move_outcome"
    ) as mock_pm:
        apply_moves([_move("a"), _move("b", to_date="Jan 3, 2026")], dom=_mock_dom(), emit_signals=True)
    assert mock_bc.call_count == 2
    assert mock_pm.call_count == 2
