"""Readiness distinguishes missing evidence, measured failure and admission."""
from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from modules.infrastructure.wre_core.src import dashboard_alerts, dae_preflight
from modules.infrastructure.wre_core.src.pattern_memory import (
    PatternMemory,
    _parse_iso_utc,
    _parse_iso_utc_with_meta,
)


@pytest.fixture
def memory(tmp_path):
    store = PatternMemory(tmp_path / "patterns.db")
    yield store
    store.conn.close()


def test_unrelated_executions_do_not_create_metric_evidence(memory):
    memory.increment_counter("total_executions", 45)
    dashboard = memory.get_telemetry_dashboard()
    for metric in ("tot_confidence_rate", "codeact_success_rate",
                   "variation_win_rate", "retrieval_coverage"):
        assert dashboard[metric] is None
    monitor = dashboard_alerts.DashboardAlertMonitor(memory)
    assert not monitor.has_sufficient_data(dashboard)
    assert monitor.check_all() == []


def test_historical_measured_zero_survives_partial_unknown(memory):
    memory.conn.executemany(
        "INSERT INTO retrieval_quality "
        "(retrieval_id,execution_id,skill_name,query,timestamp,results_count,relevance_score) "
        "VALUES (?,?,?,'fixture','2026-06-26T00:00:00+00:00',0,0.0)",
        [(str(i), str(i), "shorts_fixture") for i in range(45)],
    )
    memory.conn.commit()
    dashboard = memory.get_telemetry_dashboard()
    assert dashboard["retrieval_coverage"] == 0.0
    evidence = dashboard["metric_evidence"]["retrieval_coverage"]
    assert evidence["samples"] == 45
    assert evidence["recorded_from"] == "2026-06-26T00:00:00+00:00"
    assert evidence["recorded_to"] == evidence["recorded_from"]
    assert evidence["skill_count"] == 1
    assert dashboard["telemetry_scope"] == "database_lifetime"
    alerts = dashboard_alerts.DashboardAlertMonitor(memory).check_all()
    assert [(a.metric, a.severity) for a in alerts] == [("retrieval_coverage", "critical")]


def test_unscored_retrieval_is_not_a_measured_zero(memory):
    memory.conn.execute(
        "INSERT INTO retrieval_quality (retrieval_id,execution_id,skill_name,query,timestamp) "
        "VALUES ('r','e','fixture','fixture','2026-06-26')"
    )
    memory.conn.commit()
    dashboard = memory.get_telemetry_dashboard()
    assert dashboard["total_retrievals"] == 1
    assert dashboard["retrieval_coverage"] is None
    assert dashboard["metric_evidence"]["retrieval_coverage"]["samples"] == 0


def test_one_metric_below_minimum_does_not_hide_another_failure(memory):
    memory.increment_counter("total_executions", 1000)
    memory.increment_counter("tot_selections", 1)
    memory.increment_counter("codeact_exec_fail", 25)
    alerts = dashboard_alerts.DashboardAlertMonitor(memory).check_all()
    assert [(a.metric, a.severity) for a in alerts] == [("codeact_success_rate", "critical")]


def test_dashboard_reads_existing_memory_without_schema_or_seed_writes(memory, monkeypatch):
    path = memory.db_path
    before = path.read_bytes()
    def forbidden(*args, **kwargs):
        pytest.fail("Readiness must not initialize or seed memory")
    monkeypatch.setattr(PatternMemory, "_initialize_schema", forbidden)
    monkeypatch.setattr(PatternMemory, "_seed_false_positive_memory", forbidden)
    reader = PatternMemory(path, read_only=True)
    try:
        assert reader.get_telemetry_dashboard()["total_executions"] == 0
        with pytest.raises(sqlite3.OperationalError):
            reader.conn.execute("DELETE FROM telemetry_counters")
    finally:
        reader.conn.close()
    assert path.read_bytes() == before


def test_read_only_missing_database_is_not_created(tmp_path):
    path = tmp_path / "missing" / "memory.db"
    with pytest.raises(sqlite3.OperationalError):
        PatternMemory(path, read_only=True)
    assert not path.parent.exists()


@pytest.mark.parametrize("interactive,expected", [(True, False), (False, True)])
def test_display_and_action_defaults_are_explicit(monkeypatch, interactive, expected):
    monkeypatch.delenv("WRE_DASHBOARD_AUTO_ENFORCE", raising=False)
    assert dae_preflight.dashboard_auto_enforce_enabled(interactive_menu=interactive) is expected


@pytest.mark.parametrize("override,expected", [("0", False), ("1", True)])
def test_explicit_enforcement_override_is_preserved(monkeypatch, override, expected):
    monkeypatch.setenv("WRE_DASHBOARD_AUTO_ENFORCE", override)
    for interactive in (False, True):
        assert dae_preflight.dashboard_auto_enforce_enabled(interactive_menu=interactive) is expected


@pytest.mark.parametrize("critical", [False, True])
def test_cold_start_does_not_hide_a_sampled_critical(monkeypatch, critical, capsys):
    monkeypatch.setattr(dae_preflight, "_run_openclaw_security_preflight", lambda *a, **k: True)
    monkeypatch.setenv("WRE_DASHBOARD_PREFLIGHT", "1")
    monkeypatch.setenv("WRE_DASHBOARD_AUTO_ENFORCE", "1")
    monkeypatch.setattr(dashboard_alerts.DashboardAlertMonitor, "is_in_watch_period", lambda self: False)
    health = {"healthy": False, "insufficient_data": True, "total_executions": 45,
              "min_samples": 25, "unknown_metrics": ["tot_confidence_rate"], "alerts": []}
    if critical:
        health["alerts"] = [{"metric": "retrieval_coverage", "value": 0.0,
                            "threshold": .6, "severity": "critical"}]
    monkeypatch.setattr(dashboard_alerts, "check_dashboard_health", lambda: health)
    assert dae_preflight.run_dae_preflight("test_action", quiet=True) is (not critical)
    output = capsys.readouterr().out
    assert ("blocked" in output.lower()) is critical
    assert ("FAIL" if critical else "UNKNOWN") in output


def test_missing_default_store_is_unknown_without_creating_it(tmp_path, monkeypatch):
    path = tmp_path / "uncreated" / "patterns.db"
    monkeypatch.setattr(PatternMemory, "default_db_path", staticmethod(lambda: path))
    health = dashboard_alerts.check_dashboard_health()
    assert health["status"] == "UNKNOWN"
    assert health["healthy"] is False
    assert health["dashboard"]["storage_state"] == "not_created"
    assert not path.parent.exists()


def test_health_uses_one_snapshot_and_never_calls_unknown_healthy(memory, monkeypatch):
    monitor = dashboard_alerts.DashboardAlertMonitor(memory)
    monkeypatch.setattr(dashboard_alerts, "DashboardAlertMonitor", lambda: monitor)
    original = monitor.get_dashboard
    calls = []
    def snapshot():
        calls.append(True)
        return original()
    monkeypatch.setattr(monitor, "get_dashboard", snapshot)
    health = dashboard_alerts.check_dashboard_health()
    assert len(calls) == 1
    assert health["healthy"] is False
    assert health["status"] == "UNKNOWN"
    assert "retrieval_coverage" in health["unknown_metrics"]


def test_counter_update_dates_are_not_presented_as_sample_windows(memory, capsys):
    memory.increment_counter("tot_selections", 1)
    dashboard = dashboard_alerts.DashboardAlertMonitor(memory).get_dashboard()
    dashboard_alerts.print_dashboard_evidence({"dashboard": dashboard,
        "unknown_metrics": ["tot_confidence_rate"]})
    output = capsys.readouterr().out
    assert "UNKNOWN (measured=0.000) samples=1" in output
    assert "last_counter_updates=" in output
    assert "not a sample window" in output


def _main_functions():
    import ast
    import logging
    import os
    from pathlib import Path
    path = Path(__file__).resolve().parents[4] / "main.py"
    names = {"run_connect_wre", "_wre_dashboard_auto_enforce_enabled",
             "run_wre_dashboard_preflight", "run_headless"}
    nodes = [node for node in ast.parse(path.read_text(encoding="utf-8")).body
             if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {"os": os, "Path": Path, "logger": logging.getLogger(__name__), "__file__": str(path)}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


@pytest.mark.parametrize("critical", [False, True])
def test_root_connect_and_headless_preserve_warmup_but_enforce_measured_failure(monkeypatch, critical):
    monkeypatch.setenv("WRE_DASHBOARD_PREFLIGHT", "1")
    monkeypatch.setenv("WRE_DASHBOARD_AUTO_ENFORCE", "1")
    monkeypatch.setattr(dashboard_alerts.DashboardAlertMonitor, "is_in_watch_period", lambda self: False)
    health = {"healthy": False, "insufficient_data": True, "alerts": [], "unknown_metrics": ["tot_confidence_rate"]}
    if critical:
        health["alerts"] = [{"severity": "critical", "metric": "retrieval_coverage"}]
    monkeypatch.setattr(dashboard_alerts, "check_dashboard_health", lambda: health)
    namespace = _main_functions()
    result = namespace["run_connect_wre"](None)
    assert result["readiness"] == ("BLOCKED" if critical else "UNKNOWN")
    assert result["admission_allowed"] is (not critical)
    assert result["connection"] == "CHECKED"
    reached = []
    namespace["run_reddog_holoindex_headless_preflight"] = lambda root: reached.append(True) or False
    assert namespace["run_headless"]() == 1
    assert bool(reached) is (not critical)


def test_root_checker_error_is_unknown_and_not_admitted(monkeypatch):
    def fail():
        raise RuntimeError("fixture database failure")
    monkeypatch.setattr(dashboard_alerts, "check_dashboard_health", fail)
    result = _main_functions()["run_connect_wre"](None)
    assert result["readiness"] == "UNKNOWN"
    assert result["admission_allowed"] is False


@pytest.mark.parametrize("payload", [None, {}, {"healthy": False}, {"healthy": True, "alerts": [None]}])
def test_malformed_checker_result_is_not_warmup_admission(monkeypatch, payload):
    monkeypatch.setattr(dashboard_alerts, "check_dashboard_health", lambda: payload)
    result = _main_functions()["run_connect_wre"](None)
    assert result["readiness"] == "UNKNOWN"
    assert result["admission_allowed"] is False


@pytest.mark.parametrize("enabled,warning,unknown,readiness", [
    ("0", False, False, "DISABLED"),
    ("1", True, False, "DEGRADED"),
    ("1", True, True, "DEGRADED"),
])
def test_headless_requires_enabled_ready_or_clean_warmup(monkeypatch, enabled, warning, unknown, readiness):
    monkeypatch.setenv("WRE_DASHBOARD_PREFLIGHT", enabled)
    monkeypatch.setattr(dashboard_alerts, "check_dashboard_health", lambda: {
        "healthy": not warning, "insufficient_data": unknown,
        "alerts": [{"severity": "warning"}] if warning else []})
    result = _main_functions()["run_connect_wre"](None)
    assert result["readiness"] == readiness
    assert result["admission_allowed"] is False


@pytest.mark.parametrize("interactive,expected", [(True, True), (False, False)])
def test_startup_context_preserves_critical_policy(monkeypatch, interactive, expected):
    import sys
    import types
    monkeypatch.delenv("WRE_DASHBOARD_AUTO_ENFORCE", raising=False)
    monkeypatch.setenv("WRE_DASHBOARD_PREFLIGHT", "1")
    monkeypatch.setenv("WRE_DASHBOARD_PREFLIGHT_ENFORCED", "0")
    monkeypatch.setenv("OPENCLAW_24X7", "0")
    monkeypatch.setattr(dashboard_alerts.DashboardAlertMonitor, "is_in_watch_period", lambda self: False)
    monkeypatch.setattr(dashboard_alerts, "print_research_report_summary", lambda: None)
    monkeypatch.setattr(dashboard_alerts, "check_dashboard_health", lambda: {
        "healthy": False, "insufficient_data": True,
        "alerts": [{"severity": "critical", "metric": "retrieval_coverage"}]})
    monkeypatch.setitem(sys.modules, "modules.ai_intelligence.ai_overseer.src.preflight_resolution",
                        types.SimpleNamespace(on_preflight_fail=lambda **kwargs: None))
    assert _main_functions()["run_wre_dashboard_preflight"](None, interactive_menu=interactive) is expected


def test_historical_only_rows_become_stale_unknown_in_current_window_read_only(memory):
    memory.conn.executemany(
        "INSERT INTO retrieval_quality "
        "(retrieval_id,execution_id,skill_name,query,timestamp,results_count,relevance_score) "
        "VALUES (?,?,?,'fixture','2026-06-26T00:00:00+00:00',0,0.0)",
        [(f"hist_{i}", f"hist_{i}", "shorts_fixture") for i in range(45)],
    )
    memory.conn.commit()
    path = memory.db_path
    before = path.read_bytes()

    reader = PatternMemory(path, read_only=True)
    try:
        health = dashboard_alerts.check_dashboard_health(
            pattern_memory=reader,
            current_since="2026-11-01T00:00:00Z",
            collection_id="audit_run_1",
        )
    finally:
        reader.conn.close()

    assert path.read_bytes() == before
    assert health["telemetry_scope"] == "current_window"
    assert health["collection_identity"]["collection_id"] == "audit_run_1"
    assert health["historical_critical_count"] == 1
    assert [(a["metric"], a["severity"]) for a in health["historical_alerts"]] == [
        ("retrieval_coverage", "critical")
    ]
    assert health["alerts"] == []
    assert health["healthy"] is False
    assert health["current_readiness"] == "STALE_UNKNOWN"
    ret_status = health["metric_statuses"]["retrieval_coverage"]
    assert ret_status["status"] == "STALE_UNKNOWN"
    assert ret_status["collection_state"] == "stale_historical_only"
    assert ret_status["samples"] == 0
    assert ret_status["lifetime_samples"] == 45
    assert ret_status["lifetime_status"] == "CRITICAL"

    policy = dae_preflight.dashboard_readiness(health, in_watch=False)
    assert policy["unattended_work_allowed"] is False
    assert policy["historical_critical"] == 1
    assert policy["worker_admission_granted"] is False
    assert policy["model_admission_granted"] is False


def test_fresh_healthy_windowed_metrics_stay_fail_closed_when_counters_unwindowed(memory):
    now_dt = datetime(2026, 11, 24, 2, 0, tzinfo=timezone.utc)
    since = "2026-11-24T00:00:00+00:00"
    fresh_ts = "2026-11-24T01:00:00+00:00"
    memory.conn.executemany(
        "INSERT INTO retrieval_quality "
        "(retrieval_id,execution_id,skill_name,query,timestamp,results_count,relevance_score) "
        "VALUES (?,?,?,?,?,3,0.9)",
        [(f"r_{i}", f"e_{i}", "skill_a", "q", fresh_ts) for i in range(25)],
    )
    memory.conn.executemany(
        "INSERT INTO skill_variations "
        "(variation_id,skill_name,parent_version,variation_content,created_at,created_by,test_status,promoted) "
        "VALUES (?,?,?,?,?,?, 'promoted', 1)",
        [(f"v_{i}", "skill_a", "v0", "body", fresh_ts, "worker") for i in range(25)],
    )
    memory.conn.commit()
    memory.increment_counter("tot_selections", 30)
    memory.increment_counter("tot_high_confidence", 28)
    memory.conn.execute("UPDATE telemetry_counters SET last_updated = ?", (fresh_ts,))
    memory.conn.commit()

    health = dashboard_alerts.check_dashboard_health(
        pattern_memory=memory,
        current_since=since,
        collection_id="fresh_healthy",
        now=now_dt,
    )
    statuses = health["metric_statuses"]
    assert statuses["retrieval_coverage"]["status"] == "PASS"
    assert statuses["retrieval_coverage"]["collection_state"] == "fresh_sampled"
    assert statuses["retrieval_coverage"]["samples"] == 25
    assert statuses["retrieval_coverage"]["window_bounded"] is True
    assert statuses["variation_win_rate"]["status"] == "PASS"
    assert statuses["variation_win_rate"]["collection_state"] == "fresh_sampled"
    assert statuses["variation_win_rate"]["samples"] == 25
    assert statuses["variation_win_rate"]["window_bounded"] is True
    assert statuses["tot_confidence_rate"]["status"] == "UNKNOWN"
    assert statuses["tot_confidence_rate"]["collection_state"] == "unwindowed_cumulative_counter"
    assert statuses["tot_confidence_rate"]["window_bounded"] is False
    assert health["healthy"] is False
    assert health["current_readiness"] == "UNKNOWN"
    policy = dae_preflight.dashboard_readiness(health, in_watch=False)
    assert policy["unattended_work_allowed"] is False


def test_fresh_failing_retrieval_blocks_current_window(memory):
    now_dt = datetime(2026, 11, 24, 2, 0, tzinfo=timezone.utc)
    since = "2026-11-24T00:00:00Z"
    fresh_ts = "2026-11-24T01:00:00+00:00"
    memory.conn.executemany(
        "INSERT INTO retrieval_quality "
        "(retrieval_id,execution_id,skill_name,query,timestamp,results_count,relevance_score) "
        "VALUES (?,?,?,?,?,0,0.0)",
        [(f"rf_{i}", f"ef_{i}", "skill_b", "q", fresh_ts) for i in range(25)],
    )
    memory.conn.commit()

    health = dashboard_alerts.check_dashboard_health(
        pattern_memory=memory,
        current_since=since,
        now=now_dt,
    )
    assert health["current_readiness"] == "BLOCKED"
    assert [(a["metric"], a["severity"]) for a in health["alerts"]] == [
        ("retrieval_coverage", "critical")
    ]
    policy = dae_preflight.dashboard_readiness(health, in_watch=False)
    assert policy["allowed"] is False
    assert policy["readiness"] == "BLOCKED"
    assert policy["unattended_work_allowed"] is False


def test_absent_and_insufficient_current_samples_exclude_null_scores(memory):
    now_dt = datetime(2026, 11, 24, 2, 0, tzinfo=timezone.utc)
    since = "2026-11-24T00:00:00Z"
    fresh_ts = "2026-11-24T01:00:00+00:00"
    empty_health = dashboard_alerts.check_dashboard_health(
        pattern_memory=memory,
        current_since=since,
        now=now_dt,
    )
    assert empty_health["metric_statuses"]["retrieval_coverage"]["collection_state"] == "no_samples"
    assert empty_health["metric_statuses"]["retrieval_coverage"]["samples"] == 0
    assert empty_health["healthy"] is False
    assert dae_preflight.dashboard_readiness(empty_health, in_watch=False)["unattended_work_allowed"] is False

    memory.conn.executemany(
        "INSERT INTO retrieval_quality "
        "(retrieval_id,execution_id,skill_name,query,timestamp,results_count,relevance_score) "
        "VALUES (?,?,?,?,?,1,?)",
        [(f"s_{i}", f"es_{i}", "skill_c", "q", fresh_ts, 0.9 if i < 10 else None) for i in range(30)],
    )
    memory.conn.commit()
    dash = memory.get_telemetry_dashboard(since=since, now=now_dt)
    cur_ret = dash["current_metric_evidence"]["retrieval_coverage"]
    assert cur_ret["total_retrievals"] == 30
    assert cur_ret["samples"] == 10

    insuff_health = dashboard_alerts.check_dashboard_health(
        pattern_memory=memory,
        current_since=since,
        now=now_dt,
    )
    assert insuff_health["metric_statuses"]["retrieval_coverage"]["status"] == "UNKNOWN"
    assert insuff_health["metric_statuses"]["retrieval_coverage"]["collection_state"] == "insufficient_current_samples"
    assert insuff_health["healthy"] is False
    assert dae_preflight.dashboard_readiness(insuff_health, in_watch=False)["unattended_work_allowed"] is False


def test_invalid_since_rejected_and_unresolved_gate_blocks_unattended_work(memory):
    with pytest.raises(ValueError):
        memory.get_telemetry_dashboard(since="not-a-valid-iso-timestamp")

    ready_health = {
        "healthy": True,
        "status": "PASS",
        "current_readiness": "READY",
        "insufficient_data": False,
        "unknown_metrics": [],
        "alerts": [],
        "historical_critical_count": 0,
    }
    open_policy = dae_preflight.dashboard_readiness(ready_health, in_watch=False)
    assert open_policy["readiness"] == "READY"
    assert open_policy["unattended_work_allowed"] is False
    assert open_policy["admission_authority_verified"] is False
    assert open_policy["unresolved_admission_gates"] == ("protected_admission_unverified",)
    assert open_policy["worker_admission_granted"] is False
    assert open_policy["model_admission_granted"] is False

    gated_policy = dae_preflight.dashboard_readiness(
        ready_health,
        in_watch=False,
        unresolved_admission_gates=("19/P0_worker_custody",),
    )
    assert gated_policy["unattended_work_allowed"] is False
    assert gated_policy["admission_authority_verified"] is False
    assert gated_policy["unresolved_admission_gates"] == ("19/P0_worker_custody",)
    assert gated_policy["worker_admission_granted"] is False
    assert gated_policy["model_admission_granted"] is False


def test_future_timestamps_excluded_and_future_since_rejected(memory):
    now_dt = datetime(2026, 11, 24, 0, 0, tzinfo=timezone.utc)
    since = "2026-11-01T00:00:00+00:00"
    future_ts = "2027-01-01T00:00:00+00:00"
    naive_ts = "2026-11-10T12:00:00"

    memory.conn.executemany(
        "INSERT INTO retrieval_quality "
        "(retrieval_id,execution_id,skill_name,query,timestamp,results_count,relevance_score) "
        "VALUES (?,?,?,?,?,3,0.95)",
        [(f"fut_r_{i}", f"fut_e_{i}", "skill_fut", "q", future_ts) for i in range(25)],
    )
    memory.conn.execute(
        "INSERT INTO retrieval_quality "
        "(retrieval_id,execution_id,skill_name,query,timestamp,results_count,relevance_score) "
        "VALUES ('naive_r','naive_e','skill_fut','q',?,1,0.95)",
        (naive_ts,),
    )
    memory.conn.execute(
        "INSERT INTO retrieval_quality "
        "(retrieval_id,execution_id,skill_name,query,timestamp,results_count,relevance_score) "
        "VALUES ('bad_r','bad_e','skill_fut','q','not-a-timestamp',1,0.95)"
    )
    memory.conn.executemany(
        "INSERT INTO skill_variations "
        "(variation_id,skill_name,parent_version,variation_content,created_at,created_by,test_status,promoted) "
        "VALUES (?,?,?,?,?,?, 'promoted', 1)",
        [(f"fut_v_{i}", "skill_fut", "v0", "body", future_ts, "worker") for i in range(25)],
    )
    memory.conn.execute(
        "INSERT OR REPLACE INTO telemetry_counters (counter_name, counter_value, last_updated) "
        "VALUES ('tot_selections', 25, ?), ('tot_high_confidence', 25, ?)",
        (future_ts, future_ts),
    )
    memory.conn.commit()

    assert _parse_iso_utc("2026-11-24T05:30:00") is None
    assert _parse_iso_utc("2026-11-24T05:30:00+09:00") == datetime(2026, 11, 23, 20, 30, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="explicit timezone offset"):
        memory.get_telemetry_dashboard(since="2026-11-24T05:30:00", now=now_dt)
    with pytest.raises(ValueError, match="timezone-aware"):
        memory.get_telemetry_dashboard(since=since, now=datetime(2026, 11, 24, 0, 0))
    with pytest.raises(ValueError, match="cannot exceed evaluated_at"):
        memory.get_telemetry_dashboard(since="2027-01-01T00:00:00+00:00", now=now_dt)

    dash = memory.get_telemetry_dashboard(since=since, now=now_dt)
    assert dash["collection_scope"]["upper_bound"] == now_dt.isoformat()
    assert dash["collection_scope"]["naive_timestamp_policy"] == "excluded_ambiguous_timezone"
    cur_ret = dash["current_metric_evidence"]["retrieval_coverage"]
    assert cur_ret["samples"] == 0
    assert cur_ret["future_rows"] == 25
    assert cur_ret["naive_timestamp_rows"] == 1
    assert cur_ret["invalid_timestamp_rows"] == 1
    assert cur_ret["timestamp_assumption"] == "naive_excluded_unknown_timezone"

    memory.conn.execute("DELETE FROM retrieval_quality WHERE retrieval_id IN ('naive_r', 'bad_r')")
    memory.conn.commit()
    health = dashboard_alerts.check_dashboard_health(
        pattern_memory=memory,
        current_since=since,
        collection_id="future_only_test",
        now=now_dt,
    )
    statuses = health["metric_statuses"]
    assert statuses["retrieval_coverage"]["status"] == "UNKNOWN"
    assert statuses["retrieval_coverage"]["collection_state"] == "future_timestamp_excluded"
    assert statuses["retrieval_coverage"]["samples"] == 0
    assert statuses["retrieval_coverage"]["future_rows"] == 25
    assert statuses["variation_win_rate"]["status"] == "UNKNOWN"
    assert statuses["variation_win_rate"]["collection_state"] == "future_timestamp_excluded"
    assert statuses["tot_confidence_rate"]["status"] == "UNKNOWN"
    assert statuses["tot_confidence_rate"]["collection_state"] == "future_timestamp_excluded"
    assert health["healthy"] is False
    assert dae_preflight.dashboard_readiness(health, in_watch=False)["unattended_work_allowed"] is False


def test_all_pass_lifetime_sqlite_fixture_never_unlocks_unattended_work(memory):
    fresh_ts = "2026-11-23T12:00:00+00:00"
    memory.conn.executemany(
        "INSERT INTO retrieval_quality "
        "(retrieval_id,execution_id,skill_name,query,timestamp,results_count,relevance_score) "
        "VALUES (?,?,?,?,?,3,0.95)",
        [(f"pass_r_{i}", f"pass_e_{i}", "skill_ok", "q", fresh_ts) for i in range(25)],
    )
    memory.conn.executemany(
        "INSERT INTO skill_variations "
        "(variation_id,skill_name,parent_version,variation_content,created_at,created_by,test_status,promoted) "
        "VALUES (?,?,?,?,?,?, 'promoted', 1)",
        [(f"pass_v_{i}", "skill_ok", "v0", "body", fresh_ts, "worker") for i in range(25)],
    )
    memory.conn.execute(
        "INSERT OR REPLACE INTO telemetry_counters (counter_name, counter_value, last_updated) VALUES "
        "('total_executions', 1000, ?), ('tot_selections', 25, ?), ('tot_high_confidence', 25, ?), "
        "('codeact_exec_success', 25, ?), ('codeact_exec_fail', 0, ?), ('codeact_gate_triggers', 0, ?)",
        (fresh_ts, fresh_ts, fresh_ts, fresh_ts, fresh_ts, fresh_ts),
    )
    memory.conn.commit()
    path = memory.db_path
    before = path.read_bytes()

    reader = PatternMemory(path, read_only=True)
    try:
        health = dashboard_alerts.check_dashboard_health(pattern_memory=reader)
    finally:
        reader.conn.close()

    assert path.read_bytes() == before
    assert health["healthy"] is True
    assert health["status"] == "PASS"
    policy = dae_preflight.dashboard_readiness(health, in_watch=False)
    assert policy["readiness"] == "READY"
    assert policy["unattended_work_allowed"] is False
    assert policy["admission_authority_verified"] is False
    assert policy["worker_admission_granted"] is False
    assert policy["model_admission_granted"] is False
    assert policy["unresolved_admission_gates"] == ("protected_admission_unverified",)


def test_monitor_run_check_and_check_all_honor_current_scope_and_preserve_lifetime_history(memory):
    now_dt = datetime(2026, 11, 24, 2, 0, tzinfo=timezone.utc)
    hist_ts = "2026-11-10T12:00:00+00:00"
    cur_ts = "2026-11-23T12:00:00+00:00"
    since = "2026-11-23T00:00:00+00:00"

    memory.conn.executemany(
        "INSERT INTO retrieval_quality "
        "(retrieval_id,execution_id,skill_name,query,timestamp,results_count,relevance_score) "
        "VALUES (?,?,?,?,?,3,0.95)",
        [(f"hg_{i}", f"ehg_{i}", "skill_h", "q", hist_ts) for i in range(250)],
    )
    memory.conn.executemany(
        "INSERT INTO retrieval_quality "
        "(retrieval_id,execution_id,skill_name,query,timestamp,results_count,relevance_score) "
        "VALUES (?,?,?,?,?,0,0.0)",
        [(f"cb_{i}", f"ecb_{i}", "skill_c", "q", cur_ts) for i in range(25)],
    )
    memory.conn.executemany(
        "INSERT INTO skill_variations "
        "(variation_id,skill_name,parent_version,variation_content,created_at,created_by,test_status,promoted) "
        "VALUES (?,?,?,?,?,?, 'promoted', 1)",
        [(f"cv_{i}", "skill_c", "v0", "body", cur_ts, "worker") for i in range(25)],
    )
    memory.conn.execute(
        "INSERT OR REPLACE INTO telemetry_counters (counter_name, counter_value, last_updated) VALUES "
        "('tot_selections', 25, ?), ('tot_high_confidence', 25, ?), "
        "('codeact_exec_success', 25, ?), ('codeact_exec_fail', 0, ?), ('codeact_gate_triggers', 0, ?)",
        (cur_ts, cur_ts, cur_ts, cur_ts, cur_ts),
    )
    memory.conn.commit()
    path = memory.db_path
    before = path.read_bytes()

    reader = PatternMemory(path, read_only=True)
    try:
        monitor = dashboard_alerts.DashboardAlertMonitor(reader, current_since=since, collection_id="qa_b_mixed")
        assert monitor.run_check(verbose=False, now=now_dt) is False
        dash = monitor.get_dashboard(now=now_dt)
        cur_alerts = monitor.check_all(dashboard=dash)
        assert [(a.metric, a.severity) for a in cur_alerts] == [("retrieval_coverage", "critical")]
        assert monitor.check_lifetime_all(dashboard=dash) == []
        health = dashboard_alerts.check_dashboard_health(
            pattern_memory=reader,
            current_since=since,
            collection_id="qa_b_mixed",
            now=now_dt,
        )
    finally:
        reader.conn.close()

    assert path.read_bytes() == before
    assert health["current_readiness"] == "BLOCKED"
    assert health["historical_alerts"] == []
    assert health["historical_critical_count"] == 0
    ret = health["metric_statuses"]["retrieval_coverage"]
    assert ret["status"] == "CRITICAL"
    assert ret["samples"] == 25
    assert ret["lifetime_status"] == "PASS"
    assert ret["lifetime_samples"] == 275


def test_naive_rows_fail_closed_and_writers_emit_explicit_offsets_with_boundaries(memory):
    now_dt = datetime(2026, 11, 24, 2, 0, tzinfo=timezone.utc)
    since = "2026-11-23T15:00:00+00:00"
    naive_ts = "2026-11-24T05:30:00"

    memory.conn.executemany(
        "INSERT INTO retrieval_quality "
        "(retrieval_id,execution_id,skill_name,query,timestamp,results_count,relevance_score) "
        "VALUES (?,?,?,?,?,3,0.95)",
        [(f"nv_{i}", f"env_{i}", "skill_nv", "q", naive_ts) for i in range(25)],
    )
    memory.conn.commit()

    health = dashboard_alerts.check_dashboard_health(
        pattern_memory=memory,
        current_since=since,
        collection_id="naive_rows_test",
        now=now_dt,
    )
    ret = health["metric_statuses"]["retrieval_coverage"]
    assert ret["status"] == "UNKNOWN"
    assert ret["collection_state"] == "naive_timestamp_excluded"
    assert ret["samples"] == 0
    assert ret["naive_timestamp_rows"] == 25
    assert ret["lifetime_status"] == "PASS"
    assert ret["lifetime_samples"] == 25
    assert dae_preflight.dashboard_readiness(health, in_watch=False)["unattended_work_allowed"] is False

    # Boundary and explicit-offset normalization checks (+09:00, -05:00, Z)
    memory.conn.execute("DELETE FROM retrieval_quality")
    boundary_rows = [
        ("b_before", "eb_1", "skill_b", "q", "2026-11-23T23:59:59+09:00", 1, 0.9),  # 14:59:59Z -> historical
        ("b_start", "eb_2", "skill_b", "q", "2026-11-24T00:00:00+09:00", 1, 0.9),   # 15:00:00Z -> included
        ("b_neg5", "eb_3", "skill_b", "q", "2026-11-23T19:00:00-05:00", 1, 0.9),    # 00:00:00Z -> included
        ("b_end", "eb_4", "skill_b", "q", "2026-11-24T02:00:00Z", 1, 0.9),          # 02:00:00Z -> included
        ("b_future", "eb_5", "skill_b", "q", "2026-11-24T02:00:01+00:00", 1, 0.9),  # 02:00:01Z -> future
    ]
    memory.conn.executemany(
        "INSERT INTO retrieval_quality "
        "(retrieval_id,execution_id,skill_name,query,timestamp,results_count,relevance_score) "
        "VALUES (?,?,?,?,?,?,?)",
        boundary_rows,
    )
    memory.conn.commit()
    dash_utc = memory.get_telemetry_dashboard(since="2026-11-23T15:00:00+00:00", now=now_dt)
    dash_jst = memory.get_telemetry_dashboard(since="2026-11-24T00:00:00+09:00", now=now_dt)
    for dash in (dash_utc, dash_jst):
        ev = dash["current_metric_evidence"]["retrieval_coverage"]
        assert ev["samples"] == 3
        assert ev["future_rows"] == 1
        assert ev["naive_timestamp_rows"] == 0

    # Writer compatibility: writers must emit explicit timezone offsets and enter active UTC windows
    before_write = datetime.now(timezone.utc) - timedelta(seconds=1)
    memory.record_retrieval("w_r1", "w_e1", "skill_w", "q", 2, 0.95, 10)
    memory.store_variation("w_v1", "skill_w", "body", created_by="worker")
    memory.conn.execute("UPDATE skill_variations SET test_status='promoted', promoted=1 WHERE variation_id='w_v1'")
    memory.increment_counter("tot_selections", 1)
    memory.conn.commit()
    after_write = datetime.now(timezone.utc) + timedelta(seconds=1)

    r_ts = memory.conn.execute("SELECT timestamp FROM retrieval_quality WHERE retrieval_id='w_r1'").fetchone()[0]
    v_ts = memory.conn.execute("SELECT created_at FROM skill_variations WHERE variation_id='w_v1'").fetchone()[0]
    c_ts = memory.conn.execute("SELECT last_updated FROM telemetry_counters WHERE counter_name='tot_selections'").fetchone()[0]
    for ts in (r_ts, v_ts, c_ts):
        dt, was_naive = _parse_iso_utc_with_meta(ts)
        assert dt is not None and was_naive is False

    w_dash = memory.get_telemetry_dashboard(since=before_write.isoformat(), now=after_write)
    assert w_dash["current_metric_evidence"]["retrieval_coverage"]["samples"] >= 1
    assert w_dash["current_metric_evidence"]["variation_win_rate"]["samples"] == 1
    assert w_dash["current_metric_evidence"]["tot_confidence_rate"]["counter_updated_in_window"] is True


def test_standalone_env_current_since_drives_run_check(monkeypatch, memory, capsys):
    now_dt = datetime(2026, 11, 24, 2, 0, tzinfo=timezone.utc)
    hist_ts = "2026-11-10T12:00:00+00:00"
    cur_ts = "2026-11-23T12:00:00+00:00"
    memory.conn.executemany(
        "INSERT INTO retrieval_quality "
        "(retrieval_id,execution_id,skill_name,query,timestamp,results_count,relevance_score) "
        "VALUES (?,?,?,?,?,3,0.95)",
        [(f"shg_{i}", f"eshg_{i}", "skill_s", "q", hist_ts) for i in range(250)],
    )
    memory.conn.executemany(
        "INSERT INTO retrieval_quality "
        "(retrieval_id,execution_id,skill_name,query,timestamp,results_count,relevance_score) "
        "VALUES (?,?,?,?,?,0,0.0)",
        [(f"scb_{i}", f"escb_{i}", "skill_s", "q", cur_ts) for i in range(25)],
    )
    memory.conn.commit()
    reader = PatternMemory(memory.db_path, read_only=True)
    try:
        monkeypatch.setenv("WRE_DASHBOARD_CURRENT_SINCE", "2026-11-23T00:00:00+00:00")
        monkeypatch.setenv("WRE_DASHBOARD_COLLECTION_ID", "standalone_env")
        monitor = dashboard_alerts.DashboardAlertMonitor(reader)
        assert monitor.current_since == "2026-11-23T00:00:00+00:00"
        assert monitor.run_check(verbose=True, now=now_dt) is False
    finally:
        reader.conn.close()
    out = capsys.readouterr().out
    assert "Scope: current_window since=2026-11-23T00:00:00+00:00 collection_id=standalone_env" in out
    assert "Historical critical count: 0" in out


def test_root_connect_wre_separates_total_executions_from_metric_samples(monkeypatch):
    monkeypatch.setenv("WRE_DASHBOARD_PREFLIGHT", "1")
    monkeypatch.setenv("WRE_DASHBOARD_AUTO_ENFORCE", "1")
    monkeypatch.setattr(dashboard_alerts.DashboardAlertMonitor, "is_in_watch_period", lambda self: False)
    health = {
        "healthy": False,
        "insufficient_data": True,
        "total_executions": 45,
        "metric_samples": {"retrieval_coverage": 0, "variation_win_rate": 0},
        "telemetry_scope": "current_window",
        "current_readiness": "STALE_UNKNOWN",
        "historical_critical_count": 1,
        "unknown_metrics": ["retrieval_coverage", "variation_win_rate"],
        "alerts": [],
    }
    monkeypatch.setattr(dashboard_alerts, "check_dashboard_health", lambda: health)
    result = _main_functions()["run_connect_wre"](None)
    assert result["sample_coverage"] == 45
    assert result["total_executions"] == 45
    assert result["metric_samples"] == {"retrieval_coverage": 0, "variation_win_rate": 0}
    assert result["telemetry_scope"] == "current_window"
    assert result["current_readiness"] == "STALE_UNKNOWN"
    assert result["historical_critical_count"] == 1
    assert result["unattended_work_allowed"] is False
