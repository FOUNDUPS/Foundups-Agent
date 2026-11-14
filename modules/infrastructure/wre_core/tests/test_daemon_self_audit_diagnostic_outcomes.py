"""SQLite diagnostic accounting with inert sinks and explicit disposable stores."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import Mock

import pytest

from modules.infrastructure.wre_core.src.daemon_self_audit_loop import (
    DaemonSelfAuditLoop,
    SelfAuditEvent,
)


@pytest.fixture
def diagnostic_owner(tmp_path: Path):
    loop = object.__new__(DaemonSelfAuditLoop)
    loop.repo_root = tmp_path / "repository"
    loop.runtime_root = tmp_path / "runtime"
    loop.repo_root.mkdir()
    loop.runtime_root.mkdir()
    loop.state_path = loop.runtime_root / "state.json"
    loop.auto_fix_enabled = True
    loop.allowed_fixes = {
        "verify_dae_event_store", "diagnose_microphone_device",
        "start_ironclaw_gateway", "inspect_log_and_create_patch_task",
    }
    loop.improvement_proposals_enabled = False
    loop.legacy_process_dispatch_enabled = True
    loop.fix_cooldown_sec = 60
    loop.escalate_after = 3
    loop.escalation_window_sec = 900
    loop.escalation_cooldown_sec = 60
    loop.escalation_cmd = "inert fixture command"
    loop.escalation_dispatch_enabled = False
    loop._fix_stats, loop._signature_stats = {}, {}
    loop._last_fix_at, loop._last_escalation_at = {}, {}
    loop._offsets, loop._seen = {}, {}
    loop._state_loaded_mtime_ns = 0
    loop._recommend_fix = Mock(return_value="verify_dae_event_store")
    loop._apply_policy_fix = Mock(return_value=(True, "event_store_verified"))
    loop._increment_counter = Mock()
    loop._persist_escalation = Mock()
    loop._dispatch_escalation_command = Mock(side_effect=AssertionError("no dispatch"))
    return loop


def _open_diagnostic(loop):
    return loop._open_fix_task(
        loop.repo_root / "scan.log", "sqlite sequence collision", "synthetic failure"
    )


def _feedback_values(loop, action):
    stats = loop._fix_stats[action]
    return tuple(stats.get(key, 0) for key in (
        "attempts", "successes", "failures", "diagnostic_successes"
    ))


_OUTCOME_CASES = (
    ("verify_dae_event_store", True, "event_store_verified",
     ("self_audit_diagnostic_attempts", "self_audit_diagnostic_success"), (0, 0, 0, 1), True),
    ("verify_dae_event_store", False, "dae_event_store_not_found",
     ("self_audit_diagnostic_attempts",), (0, 0, 0, 0), True),
    ("verify_dae_event_store", False, "event_store_integrity_failed",
     ("self_audit_diagnostic_attempts",), (0, 0, 0, 0), True),
    ("verify_dae_event_store", False, "event_store_verify_exception",
     ("self_audit_diagnostic_attempts",), (0, 0, 0, 0), True),
    ("verify_dae_event_store", False, "cooldown_active",
     ("self_audit_diagnostic_attempts",), (0, 0, 0, 0), True),
    ("verify_dae_event_store", True, "prefix:event_store_verified",
     ("self_audit_diagnostic_attempts",), (0, 0, 0, 0), True),
    ("verify_dae_event_store", True, "microphone_diagnostics_written",
     ("self_audit_diagnostic_attempts",), (0, 0, 0, 0), True),
    ("verify_dae_event_store", True, "start_command_dispatched",
     ("self_audit_diagnostic_attempts",), (0, 0, 0, 0), True),
    ("verify_dae_event_store", True, "event_store_verified:microphone_diagnostics_written",
     ("self_audit_diagnostic_attempts",), (0, 0, 0, 0), True),
    ("verify_dae_event_store", 1, "event_store_verified",
     ("self_audit_diagnostic_attempts",), (0, 0, 0, 0), True),
    ("verify_dae_event_store", False, "event_store_verified",
     ("self_audit_diagnostic_attempts",), (0, 0, 0, 0), True),
    ("inspect_log_and_create_patch_task", True, "event_store_verified",
     ("self_audit_auto_fix_attempts", "self_audit_auto_fix_fail"), (1, 0, 1, 0), True),
    ("diagnose_microphone_device", True, "microphone_diagnostics_written",
     ("self_audit_auto_fix_attempts", "self_audit_auto_fix_success"), (1, 1, 0, 0), False),
    ("start_ironclaw_gateway", True, "start_command_dispatched",
     ("self_audit_auto_fix_attempts", "self_audit_auto_fix_success"), (1, 1, 0, 0), False),
    ("start_ironclaw_gateway", True, "attempted_but_unhealthy_after_1_attempt(s)",
     ("self_audit_auto_fix_attempts", "self_audit_auto_fix_fail"), (1, 0, 1, 0), True),
    ("start_ironclaw_gateway", False, "dispatch_failed:disabled",
     ("self_audit_auto_fix_attempts",), (0, 0, 0, 0), True),
)


@pytest.mark.parametrize(
    "action,attempted,result,counters,feedback,escalates", _OUTCOME_CASES,
    ids=("verified", "not-found", "integrity-failed", "exception-result", "cooldown",
         "decorated-marker", "cross-microphone", "cross-start", "mixed-markers",
         "integer-flag", "false-success-marker", "wrong-action", "legacy-microphone",
         "legacy-start", "legacy-failure", "legacy-not-attempted"),
)
def test_diagnostic_outcome_uses_all_three_existing_consumers(
    diagnostic_owner, action, attempted, result, counters, feedback, escalates
):
    loop = diagnostic_owner
    loop._recommend_fix.return_value = action
    loop._apply_policy_fix.return_value = (attempted, result)
    event = _open_diagnostic(loop)
    assert event.auto_fix_attempted is attempted
    assert event.auto_fix_result == result
    assert tuple(call.args[0] for call in loop._increment_counter.call_args_list) == counters
    assert _feedback_values(loop, action) == feedback
    assert loop._fix_stats[action]["last_result"] == result
    loop._apply_policy_fix.assert_called_once_with(action)
    event.timestamp = 1000.0
    for _ in range(3):
        loop._record_signature_event(event)
    loop._maybe_escalate(event)
    assert loop._persist_escalation.call_count == int(escalates)
    loop._dispatch_escalation_command.assert_not_called()


def test_diagnostic_feedback_preserves_historical_score_and_saved_fields(diagnostic_owner):
    loop = diagnostic_owner
    action = "verify_dae_event_store"
    history = {"attempts": 9, "successes": 5, "failures": 4, "last_result": "older",
               "last_attempt_at": 12.0, "unclassified_history": {"retained": True}}
    loop._fix_stats[action] = dict(history)
    score = loop._fix_score(action)
    loop._record_fix_feedback(action, True, "event_store_verified")
    latest_attempt = loop._fix_stats[action]["last_attempt_at"]
    loop._record_fix_feedback(action, False, "cooldown_active")
    assert _feedback_values(loop, action) == (9, 5, 4, 1)
    assert loop._fix_score(action) == score
    assert loop._fix_stats[action]["last_result"] == "cooldown_active"
    assert loop._fix_stats[action]["last_attempt_at"] == latest_attempt
    assert loop._fix_stats[action]["unclassified_history"] == history["unclassified_history"]
    loop._save_state()
    saved = json.loads(loop.state_path.read_text(encoding="utf-8"))["fix_stats"][action]
    loop._fix_stats = {}
    loop._load_state()
    assert loop._fix_stats[action] == saved
    assert _feedback_values(loop, action) == (9, 5, 4, 1)
    assert loop._fix_score(action) == score


def test_diagnostic_success_respects_escalation_threshold_and_cooldown(diagnostic_owner):
    loop = diagnostic_owner
    event = SelfAuditEvent(1000.0, "synthetic.log", "repeated collision", "synthetic",
                           "verify_dae_event_store", True, "event_store_verified")
    for _ in range(2):
        loop._record_signature_event(event)
        loop._maybe_escalate(event)
    loop._persist_escalation.assert_not_called()
    loop._record_signature_event(event)
    loop._maybe_escalate(event)
    assert loop._persist_escalation.call_count == 1
    first = loop._persist_escalation.call_args.args[0]
    assert first.event_count == 3
    assert first.last_fix_result == "event_store_verified"
    assert first.dispatch_attempted is False
    event.timestamp += 10
    loop._record_signature_event(event)
    loop._maybe_escalate(event)
    assert loop._persist_escalation.call_count == 1
    event.timestamp += 60
    loop._record_signature_event(event)
    loop._maybe_escalate(event)
    assert loop._persist_escalation.call_count == 2
    assert loop._persist_escalation.call_args.args[0].event_count == 5
    loop._dispatch_escalation_command.assert_not_called()


@pytest.mark.parametrize("gate", ("disabled", "not_allowlisted"))
def test_diagnostic_not_invoked_has_no_attempt_counter(diagnostic_owner, gate):
    loop = diagnostic_owner
    if gate == "disabled":
        loop.auto_fix_enabled = False
    else:
        loop.allowed_fixes.clear()
    event = _open_diagnostic(loop)
    assert event.auto_fix_attempted is False
    assert event.auto_fix_result == "not_attempted"
    loop._apply_policy_fix.assert_not_called()
    loop._increment_counter.assert_not_called()
    assert _feedback_values(loop, "verify_dae_event_store") == (0, 0, 0, 0)


@pytest.mark.parametrize("action,counter", (
    ("verify_dae_event_store", "self_audit_diagnostic_attempts"),
    ("start_ironclaw_gateway", "self_audit_auto_fix_attempts"),
))
def test_diagnostic_invocation_count_precedes_handler_exception(diagnostic_owner, action, counter):
    loop = diagnostic_owner
    loop._recommend_fix.return_value = action

    def fail_handler(_action):
        loop._increment_counter.assert_called_once_with(counter)
        raise RuntimeError("synthetic handler failure")

    loop._apply_policy_fix.side_effect = fail_handler
    with pytest.raises(RuntimeError, match="synthetic handler failure"):
        _open_diagnostic(loop)
    loop._apply_policy_fix.assert_called_once_with(action)
    assert loop._fix_stats == {}
    loop._persist_escalation.assert_not_called()


def test_diagnostic_sqlite_report_and_tuple_do_not_claim_a_repair(diagnostic_owner):
    loop = diagnostic_owner
    path = loop.repo_root / "modules/infrastructure/dae_daemon/memory/dae_audit.db"
    path.parent.mkdir(parents=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE dae_events (sequence_id INTEGER UNIQUE NOT NULL)")
        connection.execute("INSERT INTO dae_events VALUES (1)")
        connection.commit()
    connection.close()
    original_database = path.read_bytes()
    del loop._apply_policy_fix
    event = _open_diagnostic(loop)
    assert (event.auto_fix_attempted, event.auto_fix_result) == (True, "event_store_verified")
    report = json.loads((loop.runtime_root / "dae_event_store_health.json").read_text(encoding="utf-8"))
    assert report["integrity_check"] == "ok"
    assert report["total_events"] == report["max_sequence_id"] == 1
    assert report["duplicate_sequence_rows"] == 0
    assert Path(report["db_path"]) == path
    assert path.read_bytes() == original_database
    assert tuple(call.args[0] for call in loop._increment_counter.call_args_list) == (
        "self_audit_diagnostic_attempts", "self_audit_diagnostic_success"
    )
    assert _feedback_values(loop, "verify_dae_event_store") == (0, 0, 0, 1)
