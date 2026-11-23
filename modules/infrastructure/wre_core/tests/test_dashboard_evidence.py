"""Readiness distinguishes missing evidence, measured failure and admission."""
import sqlite3

import pytest

from modules.infrastructure.wre_core.src import dashboard_alerts, dae_preflight
from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory


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

    health = dashboard_alerts.check_dashboard_health(
        pattern_memory=memory,
        current_since=since,
        collection_id="fresh_healthy",
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
    since = "2026-11-24T00:00:00Z"
    fresh_ts = "2026-11-24T01:00:00+00:00"
    empty_health = dashboard_alerts.check_dashboard_health(
        pattern_memory=memory,
        current_since=since,
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
    dash = memory.get_telemetry_dashboard(since=since)
    cur_ret = dash["current_metric_evidence"]["retrieval_coverage"]
    assert cur_ret["total_retrievals"] == 30
    assert cur_ret["samples"] == 10

    insuff_health = dashboard_alerts.check_dashboard_health(
        pattern_memory=memory,
        current_since=since,
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
    assert open_policy["unattended_work_allowed"] is True
    assert open_policy["worker_admission_granted"] is False
    assert open_policy["model_admission_granted"] is False

    gated_policy = dae_preflight.dashboard_readiness(
        ready_health,
        in_watch=False,
        unresolved_admission_gates=("19/P0_worker_custody",),
    )
    assert gated_policy["unattended_work_allowed"] is False
    assert gated_policy["unresolved_admission_gates"] == ("19/P0_worker_custody",)
    assert gated_policy["worker_admission_granted"] is False
    assert gated_policy["model_admission_granted"] is False


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
