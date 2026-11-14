"""Finite self-audit scan status contracts with inert effects and explicit clocks."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from modules.infrastructure.wre_core.src.daemon_self_audit_loop import DaemonSelfAuditLoop


# Retained scan inputs; consumer assertions now require truthful status.
def test_run_characterizes_raised_scan_then_zero_continuation():
    from unittest.mock import Mock, call

    stop = SimpleNamespace(
        is_set=Mock(side_effect=[False, False, True]), wait=Mock(return_value=False),
    )
    loop = SimpleNamespace(
        _stop=stop, interval_sec=0.25,
        scan_once=Mock(side_effect=[RuntimeError("scan failed"), 0]),
    )

    assert DaemonSelfAuditLoop._run(loop) is None

    assert loop.scan_once.call_args_list == [call(), call()]
    assert stop.is_set.call_count == 3
    assert stop.wait.call_args_list == [call(1.0), call(1.0)]


@pytest.mark.parametrize("existing_offset", (None, 7))
def test_tail_characterizes_stat_error_as_empty_without_offset_change(
    tmp_path: Path, existing_offset,
):
    path = tmp_path / "scan.log"
    offsets = {} if existing_offset is None else {str(path): existing_offset}
    loop = SimpleNamespace(_offsets=dict(offsets), repo_root=tmp_path, max_read_bytes=8)
    target = "modules.infrastructure.wre_core.src.daemon_self_audit_loop"

    with patch.object(Path, "stat", side_effect=OSError("stat unavailable")):
        with patch(target + ".secure_read_confined_bytes") as reader:
            assert DaemonSelfAuditLoop._tail_new_lines(loop, path) == []

    reader.assert_not_called()
    assert loop._offsets == offsets


@pytest.mark.parametrize("error_type", (OSError, ValueError))
@pytest.mark.parametrize("offset,read_from", ((7, 7), (30, 4)))
def test_tail_characterizes_read_error_and_same_offset_retry(
    tmp_path: Path, error_type, offset, read_from,
):
    from unittest.mock import call

    path = tmp_path / "scan.log"
    path.write_bytes(b"first\nlater\n")
    offsets = {str(path): offset, "unrelated.log": 41}
    loop = SimpleNamespace(_offsets=dict(offsets), repo_root=tmp_path, max_read_bytes=8)
    target = "modules.infrastructure.wre_core.src.daemon_self_audit_loop"
    responses = [error_type("read unavailable"), (b"tail\n", 12)]

    with patch(target + ".secure_read_confined_bytes", side_effect=responses) as reader:
        assert DaemonSelfAuditLoop._tail_new_lines(loop, path) == []
        assert loop._offsets == offsets
        assert DaemonSelfAuditLoop._tail_new_lines(loop, path) == ["tail"]

    expected_call = call(path, allowed_root=tmp_path, offset=read_from, max_bytes=8)
    assert reader.call_args_list == [expected_call, expected_call]
    assert loop._offsets == {str(path): 12, "unrelated.log": 41}


def test_tail_characterizes_successful_empty_read_records_offset(tmp_path: Path):
    path = tmp_path / "empty.log"
    path.write_bytes(b"")
    loop = SimpleNamespace(_offsets={}, repo_root=tmp_path, max_read_bytes=8)
    target = "modules.infrastructure.wre_core.src.daemon_self_audit_loop"

    with patch(target + ".secure_read_confined_bytes", return_value=(b"", 0)) as reader:
        assert DaemonSelfAuditLoop._tail_new_lines(loop, path) == []

    reader.assert_called_once_with(path, allowed_root=tmp_path, offset=0, max_bytes=8)
    assert loop._offsets == {str(path): 0}


def _inert_scan_health_supervisor(audit_loop, *, enabled):
    from unittest.mock import Mock

    broker = SimpleNamespace(get_runtime_status=Mock(return_value={"registered": False}))
    observer = SimpleNamespace(
        get_live_status=Mock(return_value={"registered": False}),
        follow_events=Mock(return_value={
            "events": [], "next_cursor": 7, "latest_sequence_id": 7,
        }),
    )
    state = SimpleNamespace(
        _get_broker=Mock(return_value=broker),
        _get_observer=Mock(return_value=observer),
        _git_summary=Mock(return_value={"dirty": False}),
        _attempts_in_window=Mock(return_value=0),
        _observe_holoindex_postmerge=Mock(return_value=None),
        _event_cursor=7, self_audit_enabled=enabled,
        max_restart_attempts=2, restart_window_sec=60,
        _self_audit_loop=audit_loop, metrics=SimpleNamespace(events_observed=11),
    )
    return state, broker, observer


@pytest.mark.parametrize("mode", ("zero", "positive", "error", "absent", "disabled"))
def test_supervisor_characterizes_scan_count_projection_without_health_status(mode):
    from unittest.mock import Mock, call
    from modules.communication.moltbot_bridge.src import openclaw_supervisor

    scan = Mock(return_value=3 if mode == "positive" else 0)
    if mode == "error":
        scan.side_effect = RuntimeError("scan failed")
    audit_loop = None if mode in {"absent", "disabled"} else SimpleNamespace(scan_once=scan)
    state, broker, observer = _inert_scan_health_supervisor(
        audit_loop, enabled=mode != "disabled",
    )

    with patch.object(openclaw_supervisor, "logger") as log:
        observation = openclaw_supervisor.OpenClawSupervisor._observe(state)

    event_count = 3 if mode == "positive" else 0
    status = observation.pop("self_audit_status")
    expected = {"error": "failed", "absent": "absent", "disabled": "disabled"}
    assert status["outcome"] == expected.get(mode, "unavailable")
    assert status["attempt_id"] is None
    assert status["last_success"] is None
    assert status["last_success_age_sec"] is None
    assert observation == {
        "openclaw_runtime": {"registered": False},
        "supervisor_runtime": {"registered": False},
        "openclaw_live": {"registered": False},
        "openclaw_follow": {"events": [], "next_cursor": 7, "latest_sequence_id": 7},
        "git": {"dirty": False}, "self_audit_enabled": mode != "disabled",
        "restart_budget": {"max_attempts": 2, "window_sec": 60, "attempts_in_window": 0},
        "self_audit_event_count": event_count,
    }
    assert state.metrics.events_observed == 11 + event_count
    assert scan.call_args_list == ([] if audit_loop is None else [call()])
    assert log.warning.call_count == (1 if mode == "error" else 0)
    if mode == "error":
        assert log.warning.call_args.args[1] == "scan_failed"
    assert log.info.call_count == (1 if mode == "positive" else 0)
    state._get_broker.assert_called_once_with()
    state._get_observer.assert_called_once_with()
    state._git_summary.assert_called_once_with()
    state._attempts_in_window.assert_called_once_with()
    state._observe_holoindex_postmerge.assert_called_once_with(observation)
    assert broker.get_runtime_status.call_args_list == [call("openclaw"), call("openclaw_supervisor")]
    observer.get_live_status.assert_called_once_with("openclaw", limit=4)
    observer.follow_events.assert_called_once_with(dae_id="openclaw", since_sequence=7, limit=8)


@pytest.fixture
def scan_owner(tmp_path, monkeypatch):
    import inspect

    assert callable(getattr(DaemonSelfAuditLoop, "scan_once_with_status", None))
    assert "monotonic_clock" in inspect.signature(DaemonSelfAuditLoop).parameters
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_TELEMETRY", "0")
    clock = Mock(return_value=100.0)
    with patch.object(DaemonSelfAuditLoop, "_load_state"):
        with patch.object(DaemonSelfAuditLoop, "_resolve_runtime_root", return_value=tmp_path / "runtime"):
            loop = DaemonSelfAuditLoop(tmp_path, monotonic_clock=clock)
    path = tmp_path / "scan.log"
    path.write_bytes(b"quiet\n")
    loop._scan_once_locked = loop._scan_once_with_lease
    loop._resolve_log_files = Mock(return_value=[path])
    loop._tail_new_lines = Mock(return_value=[])
    loop._is_error_line = Mock(return_value=True)
    loop._is_duplicate = Mock(return_value=False)
    loop._is_noise_signature = Mock(return_value=False)
    for name in ("_open_fix_task", "_persist_event", "_increment_counter",
                 "_record_signature_event", "_maybe_escalate", "_save_state"):
        setattr(loop, name, Mock())
    return SimpleNamespace(loop=loop, clock=clock, path=path)


def test_scan_status_starts_unattempted_without_inventing_freshness(scan_owner):
    status = scan_owner.loop.get_scan_status()
    assert status["attempt_id"] == 0
    assert status["outcome"] == "never_scanned"
    assert status["coverage"] == "unknown"
    assert status["event_count"] is None
    assert status["started_at_monotonic"] is None
    assert status["completed_at_monotonic"] is None
    assert status["last_success"] is None
    assert status["last_success_age_sec"] is None
    scan_owner.loop._resolve_log_files.assert_not_called()


@pytest.mark.parametrize("count", (0, 3))
def test_scan_status_completion_binds_count_and_preserves_integer_api(scan_owner, count):
    loop = scan_owner.loop
    loop._tail_new_lines.return_value = [f"finding {index}" for index in range(count)]
    first = loop.scan_once_with_status()
    assert first["attempt_id"] == 1
    assert first["outcome"] == "completed"
    assert first["coverage"] == "bounded"
    assert first["event_count"] == count
    assert first["error_codes"] == []
    assert first["started_at_monotonic"] == first["completed_at_monotonic"] == 100.0
    assert first["last_success"] == {
        "attempt_id": 1, "completed_at_monotonic": 100.0, "event_count": count,
    }
    scan_owner.clock.return_value = 135.0
    assert loop.get_scan_status()["last_success_age_sec"] == 35.0
    assert type(loop.scan_once()) is int
    assert loop.get_scan_status()["attempt_id"] == 2
    assert first["attempt_id"] == 1
    assert loop._persist_event.call_count == 2 * count


@pytest.mark.parametrize("after_effect", (False, True))
def test_scan_status_failure_keeps_unknown_count_and_original_exception(scan_owner, after_effect):
    loop = scan_owner.loop
    failure = RuntimeError("private/path and sensitive log payload")
    if after_effect:
        loop._tail_new_lines.return_value = ["finding"]
        loop._maybe_escalate.side_effect = failure
    else:
        loop._resolve_log_files.side_effect = failure
    status = loop.scan_once_with_status()
    assert status["outcome"] == "failed"
    assert status["event_count"] is None
    assert status["last_success"] is None
    assert "scan_failed" in status["error_codes"]
    assert "private/path" not in repr(status)
    assert "sensitive" not in repr(status)
    assert loop._persist_event.call_count == int(after_effect)
    with pytest.raises(RuntimeError) as caught:
        loop.scan_once()
    assert caught.value is failure
    assert loop.get_scan_status()["attempt_id"] == 2


def test_scan_status_interrupt_records_attempt_then_propagates(scan_owner):
    failure = KeyboardInterrupt("private interruption detail")
    scan_owner.loop._resolve_log_files.side_effect = failure
    with pytest.raises(KeyboardInterrupt) as caught:
        scan_owner.loop.scan_once_with_status()
    assert caught.value is failure
    status = scan_owner.loop.get_scan_status()
    assert status["outcome"] == "failed"
    assert status["event_count"] is None
    assert status["error_codes"] == ["scan_interrupted"]
    assert "private" not in repr(status)


@pytest.mark.parametrize("failure", ("stat", "read_oserror", "read_valueerror"))
def test_scan_status_partial_inputs_preserve_offsets_and_last_success(scan_owner, failure):
    loop = scan_owner.loop
    previous = loop.scan_once_with_status()["last_success"]
    scan_owner.clock.return_value = 150.0
    loop._tail_new_lines = DaemonSelfAuditLoop._tail_new_lines.__get__(loop)
    loop._offsets[str(scan_owner.path)] = 3
    target = "modules.infrastructure.wre_core.src.daemon_self_audit_loop"
    if failure == "stat":
        context = patch.object(Path, "stat", side_effect=OSError("private input"))
    else:
        error = OSError if failure == "read_oserror" else ValueError
        context = patch(target + ".secure_read_confined_bytes", side_effect=error("private input"))
    with context:
        status = loop.scan_once_with_status()
    assert status["outcome"] == "partial"
    assert status["coverage"] == "known_partial"
    assert status["event_count"] == 0
    assert status["error_codes"] == ["stat_failed" if failure == "stat" else "read_failed"]
    assert status["last_success"] == previous
    assert status["last_success_age_sec"] == 50.0
    assert loop._offsets == {str(scan_owner.path): 3}
    assert "private" not in repr(status)


def test_scan_status_no_inputs_is_completed_but_not_full_coverage(scan_owner):
    scan_owner.loop._resolve_log_files.return_value = []
    status = scan_owner.loop.scan_once_with_status()
    assert status["outcome"] == "completed"
    assert status["coverage"] == "no_inputs"
    assert status["event_count"] == 0
    assert not any(key in status for key in ("healthy", "fresh", "stale", "full_coverage"))


def test_scan_status_discovery_failure_records_unknown_coverage_and_rethrows(scan_owner):
    loop = scan_owner.loop
    loop._resolve_log_files = DaemonSelfAuditLoop._resolve_log_files.__get__(loop)
    with patch.object(Path, "glob", side_effect=OSError("private discovery location")):
        status = loop.scan_once_with_status()
    assert status["outcome"] == "failed"
    assert status["event_count"] is None
    assert "discovery_failed" in status["error_codes"]
    assert "private" not in repr(status)


def test_scan_status_running_snapshot_and_returned_data_are_isolated(scan_owner):
    loop = scan_owner.loop
    observed = []
    original = loop._scan_once_locked

    def during_scan():
        observed.append(loop.get_scan_status())
        return original()

    loop._scan_once_locked = during_scan
    result = loop.scan_once_with_status()
    assert observed[0]["outcome"] == "running"
    assert observed[0]["event_count"] is None
    assert observed[0]["attempt_id"] == result["attempt_id"]
    result["error_codes"].append("forged")
    result["last_success"]["attempt_id"] = 999
    fresh = loop.get_scan_status()
    assert fresh["error_codes"] == []
    assert fresh["last_success"]["attempt_id"] == 1
    assert observed[0]["outcome"] == "running"


@pytest.mark.parametrize("invalid", ("bool", "nan", "infinite", "negative", "text", "raises"))
def test_scan_status_invalid_clock_does_not_mask_scanning(scan_owner, invalid):
    previous = scan_owner.loop.scan_once_with_status()["last_success"]
    values = {"bool": True, "nan": float("nan"), "infinite": float("inf"),
              "negative": -1.0, "text": "clock"}
    if invalid == "raises":
        scan_owner.clock.side_effect = RuntimeError("clock unavailable")
    else:
        scan_owner.clock.return_value = values[invalid]
    assert scan_owner.loop.scan_once() == 0
    status = scan_owner.loop.get_scan_status()
    assert status["outcome"] == "completed"
    assert status["clock_valid"] is False
    assert status["completed_at_monotonic"] is None
    assert status["last_success"] == previous
    assert status["last_success_age_sec"] is None
    failure = ValueError("scan failure takes precedence")
    scan_owner.loop._resolve_log_files.side_effect = failure
    with pytest.raises(ValueError) as caught:
        scan_owner.loop.scan_once()
    assert caught.value is failure


def test_scan_status_backward_clock_uses_high_water_after_failed_attempt(scan_owner):
    loop = scan_owner.loop
    previous = loop.scan_once_with_status()["last_success"]
    scan_owner.clock.return_value = 200.0
    loop._resolve_log_files.side_effect = RuntimeError("failed at later time")
    assert loop.scan_once_with_status()["last_success"] == previous
    scan_owner.clock.return_value = 150.0
    status = loop.get_scan_status()
    assert status["clock_valid"] is False
    assert status["last_success_age_sec"] is None
    scan_owner.clock.return_value = 250.0
    assert loop.get_scan_status()["last_success_age_sec"] == 150.0


@pytest.mark.parametrize("count", (True, -1, 1.5, "1"))
def test_scan_status_invalid_count_is_failed_without_coercion(scan_owner, count):
    scan_owner.loop._scan_once_locked = Mock(return_value=count)
    status = scan_owner.loop.scan_once_with_status()
    assert status["outcome"] == "failed"
    assert status["event_count"] is None
    assert status["last_success"] is None


def test_supervisor_uses_returned_attempt_despite_later_scan(scan_owner):
    from modules.communication.moltbot_bridge.src import openclaw_supervisor

    loop = scan_owner.loop
    scan = loop.scan_once_with_status

    def interleave():
        loop._tail_new_lines.return_value = ["first"]
        first = scan()
        loop._tail_new_lines.return_value = ["later", "later again"]
        scan()
        return first

    loop.scan_once_with_status = Mock(side_effect=interleave)
    state, _, _ = _inert_scan_health_supervisor(loop, enabled=True)
    observation = openclaw_supervisor.OpenClawSupervisor._observe(state)
    assert observation["self_audit_event_count"] == 1
    assert observation["self_audit_status"]["attempt_id"] == 1
    assert observation["self_audit_status"]["event_count"] == 1
    assert state.metrics.events_observed == 12
    assert loop.get_scan_status()["attempt_id"] == 2
    assert loop.get_scan_status()["event_count"] == 2
    loop.scan_once_with_status.assert_called_once_with()


def test_supervisor_disabled_owner_does_not_scan(scan_owner):
    from modules.communication.moltbot_bridge.src import openclaw_supervisor

    state, _, _ = _inert_scan_health_supervisor(scan_owner.loop, enabled=False)
    result = openclaw_supervisor.OpenClawSupervisor._observe(state)
    assert result["self_audit_status"]["outcome"] == "disabled"
    assert result["self_audit_event_count"] == 0
    scan_owner.loop._resolve_log_files.assert_not_called()


@pytest.mark.parametrize("value", (None, True, {}, {"event_count": True}))
def test_supervisor_malformed_status_never_retries_legacy_scan(value):
    from modules.communication.moltbot_bridge.src import openclaw_supervisor

    owner = SimpleNamespace(scan_once_with_status=Mock(return_value=value), scan_once=Mock())
    state, _, _ = _inert_scan_health_supervisor(owner, enabled=True)
    result = openclaw_supervisor.OpenClawSupervisor._observe(state)
    assert result["self_audit_status"]["outcome"] == "unavailable"
    assert result["self_audit_event_count"] == 0
    assert state.metrics.events_observed == 11
    owner.scan_once_with_status.assert_called_once_with()
    owner.scan_once.assert_not_called()


def test_supervisor_magicmock_does_not_fabricate_status_capability():
    from modules.communication.moltbot_bridge.src import openclaw_supervisor

    owner = Mock()
    owner.scan_once.return_value = 2
    state, _, _ = _inert_scan_health_supervisor(owner, enabled=True)
    result = openclaw_supervisor.OpenClawSupervisor._observe(state)
    assert result["self_audit_status"]["outcome"] == "unavailable"
    assert result["self_audit_event_count"] == 2
    owner.scan_once.assert_called_once_with()
    assert "scan_once_with_status" not in owner._mock_children


def test_scan_status_mixed_input_preserves_positive_count_and_supervisor_metric(scan_owner):
    from modules.communication.moltbot_bridge.src import openclaw_supervisor

    loop = scan_owner.loop
    previous = loop.scan_once_with_status()["last_success"]
    bad = scan_owner.path.with_name("bad.log")
    bad.write_bytes(b"unreadable")
    loop._resolve_log_files.return_value = [scan_owner.path, bad]
    loop._tail_new_lines = DaemonSelfAuditLoop._tail_new_lines.__get__(loop)
    scan_owner.clock.return_value = 150.0

    def read(path, **kwargs):
        if path == bad:
            raise OSError("private failing path")
        return b"finding a\nfinding b\nfinding c\n", 30

    state, _, _ = _inert_scan_health_supervisor(loop, enabled=True)
    target = "modules.infrastructure.wre_core.src.daemon_self_audit_loop.secure_read_confined_bytes"
    with patch(target, side_effect=read):
        result = openclaw_supervisor.OpenClawSupervisor._observe(state)
    status = result["self_audit_status"]
    assert status["outcome"] == "partial"
    assert status["coverage"] == "known_partial"
    assert status["event_count"] == result["self_audit_event_count"] == 3
    assert state.metrics.events_observed == 14
    assert loop._persist_event.call_count == 3
    assert status["last_success"] == previous
    assert status["last_success_age_sec"] == 50.0


@pytest.mark.parametrize("kind", ("invalid_glob", "escaped_candidate", "nonfile"))
def test_scan_status_discovery_exclusions_cannot_refresh_success(scan_owner, monkeypatch, kind):
    loop = scan_owner.loop
    previous = loop.scan_once_with_status()["last_success"]
    scan_owner.clock.return_value = 150.0
    loop._resolve_log_files = DaemonSelfAuditLoop._resolve_log_files.__get__(loop)
    pattern = "../outside/*.log;*.log" if kind == "invalid_glob" else "*.log"
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", pattern)
    candidate = scan_owner.path
    if kind == "escaped_candidate":
        candidate = loop.repo_root.parent / "outside.log"
    elif kind == "nonfile":
        candidate = loop.repo_root
    with patch.object(Path, "glob", return_value=[candidate]):
        status = loop.scan_once_with_status()
    assert status["outcome"] == "partial"
    assert status["coverage"] == "known_partial"
    assert "discovery_excluded" in status["error_codes"]
    assert status["last_success"] == previous
    assert status["last_success_age_sec"] == 50.0
    assert "outside.log" not in repr(status)


def test_scan_status_no_inputs_never_refreshes_bounded_input_success(scan_owner):
    loop = scan_owner.loop
    loop._resolve_log_files.return_value = []
    assert loop.scan_once_with_status()["last_success"] is None
    loop._resolve_log_files.return_value = [scan_owner.path]
    previous = loop.scan_once_with_status()["last_success"]
    assert previous is not None
    scan_owner.clock.return_value = 180.0
    loop._resolve_log_files.return_value = []
    status = loop.scan_once_with_status()
    assert status["outcome"] == "completed"
    assert status["coverage"] == "no_inputs"
    assert status["event_count"] == 0
    assert status["last_success"] == previous
    assert status["last_success_age_sec"] == 80.0


def test_scan_status_backward_attempt_cannot_replace_success_then_recovers(scan_owner):
    loop = scan_owner.loop
    previous = loop.scan_once_with_status()["last_success"]
    scan_owner.clock.return_value = 200.0
    loop._resolve_log_files.side_effect = RuntimeError("failed later attempt")
    assert loop.scan_once_with_status()["outcome"] == "failed"
    loop._resolve_log_files.side_effect = None
    scan_owner.clock.return_value = 150.0
    status = loop.scan_once_with_status()
    assert status["outcome"] == "completed"
    assert status["clock_valid"] is False
    assert status["completed_at_monotonic"] is None
    assert status["last_success"] == previous
    assert status["last_success_age_sec"] is None
    scan_owner.clock.return_value = 250.0
    recovered = loop.scan_once_with_status()
    assert recovered["clock_valid"] is True
    assert recovered["last_success"]["attempt_id"] == recovered["attempt_id"] == 4
    assert recovered["last_success"]["completed_at_monotonic"] == 250.0


def test_scan_status_snapshot_precedes_scan_lock_release(scan_owner):
    loop = scan_owner.loop
    real_lock = loop._scan_lock
    subsequent = []

    class ReleaseHook:
        fired = False

        def __enter__(self):
            real_lock.acquire()

        def __exit__(self, *args):
            real_lock.release()
            if not self.fired:
                self.fired = True
                loop._tail_new_lines.return_value = ["later"]
                subsequent.append(loop.scan_once_with_status())

    loop._scan_lock = ReleaseHook()
    first = loop.scan_once_with_status()
    assert first["attempt_id"] == 1
    assert first["event_count"] == 0
    assert subsequent[0]["attempt_id"] == 2
    assert subsequent[0]["event_count"] == 1
    assert loop.get_scan_status()["attempt_id"] == 2


@pytest.mark.parametrize("changes", (
    {"coverage": "known_partial", "error_codes": ["read_failed"]},
    {"outcome": "partial", "coverage": "known_partial", "error_codes": []},
    {"outcome": "partial", "coverage": "bounded", "error_codes": ["read_failed"]},
    {"outcome": "failed", "event_count": None, "coverage": "bounded", "error_codes": ["scan_failed"]},
    {"last_success": {"attempt_id": 2, "completed_at_monotonic": 100.0, "event_count": 0}},
    {"last_success": {"attempt_id": 1, "completed_at_monotonic": 101.0, "event_count": 0}},
    {"last_success_age_sec": 42.0},
    {"clock_valid": True, "sampled_at_monotonic": None},
    {"clock_valid": False, "sampled_at_monotonic": 100.0},
    {"outcome": "partial", "coverage": "known_partial", "error_codes": ["read_failed", "read_failed"]},
    {"coverage": "no_inputs"},
    {"started_at_monotonic": 101.0},
    {"completed_at_monotonic": 101.0},
    {"last_success": {"attempt_id": 1, "completed_at_monotonic": 100.0, "event_count": 3}},
    {"outcome": "failed", "event_count": None, "coverage": "unknown", "error_codes": []},
    {"last_success": None, "last_success_age_sec": 0.0},
    {"attempt_id": 2, "started_at_monotonic": 90.0},
    {"last_success": None, "last_success_age_sec": None},
))
def test_supervisor_rejects_contradictory_status_without_rescan(scan_owner, changes):
    from modules.communication.moltbot_bridge.src import openclaw_supervisor

    status = scan_owner.loop.scan_once_with_status()
    status.update(changes)
    owner = SimpleNamespace(scan_once_with_status=Mock(return_value=status), scan_once=Mock())
    state, _, _ = _inert_scan_health_supervisor(owner, enabled=True)
    result = openclaw_supervisor.OpenClawSupervisor._observe(state)
    assert result["self_audit_status"]["outcome"] == "unavailable"
    assert result["self_audit_event_count"] == 0
    assert state.metrics.events_observed == 11
    owner.scan_once_with_status.assert_called_once_with()
    owner.scan_once.assert_not_called()


@pytest.mark.parametrize("samples,success_id", (([None, 110.0, 120.0], 1),
                                              ([110.0, None, 120.0], 1),
                                              ([110.0, 115.0, None], 2)))
def test_supervisor_accepts_qualified_partial_clock_samples(scan_owner, samples, success_id):
    from modules.communication.moltbot_bridge.src import openclaw_supervisor

    scan_owner.loop.scan_once_with_status()
    scan_owner.clock.side_effect = samples
    scan_owner.loop._tail_new_lines.return_value = ["one finding"]
    state, _, _ = _inert_scan_health_supervisor(scan_owner.loop, enabled=True)
    result = openclaw_supervisor.OpenClawSupervisor._observe(state)
    status = result["self_audit_status"]
    assert status["outcome"] == "completed"
    assert status["event_count"] == result["self_audit_event_count"] == 1
    assert state.metrics.events_observed == 12
    assert status["last_success"]["attempt_id"] == success_id
    assert status["clock_valid"] is (samples[2] is not None)
    assert status["last_success_age_sec"] == (20.0 if success_id == 1 else None)
