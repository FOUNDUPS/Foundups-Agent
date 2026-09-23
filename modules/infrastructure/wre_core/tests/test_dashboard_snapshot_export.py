#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for dashboard snapshot export utility.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os

import pytest

from modules.infrastructure.wre_core.src import dashboard_alerts

from modules.infrastructure.wre_core.src.dashboard_snapshot_export import (
    export_dashboard_snapshot,
    prune_old_snapshots,
)


def test_export_dashboard_snapshot_writes_files(tmp_path):
    payload = {
        "healthy": True,
        "alerts": [],
        "dashboard": {"tot_confidence_rate": 0.72},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    result = export_dashboard_snapshot(
        output_dir=tmp_path,
        retention_days=30,
        pretty=True,
        health_data=payload,
    )

    snapshot = Path(result["snapshot_path"])
    latest = Path(result["latest_path"])

    assert snapshot.exists()
    assert latest.exists()
    assert result["healthy"] is True
    text = latest.read_text(encoding="utf-8")
    assert "\"source_of_truth\": \"sqlite\"" in text


def _research_report(tmp_path, attempts=0):
    path = tmp_path / "invocation-fixture" / "report.json"
    path.parent.mkdir()
    report = {
        "schema": "wre_auto_research_report.v1", "invocation_id": path.parent.name,
        "report_path": str(path), "status": "completed", "dry_run": True,
        "stop_reason": "attempt_limit", "cleanup": "restored",
        "failure": None, "cleanup_failure": None, "baseline_input_sha256": "a" * 64,
        "attempts_requested": attempts, "attempts_started": attempts,
        "attempts_finished": attempts, "iterations_run": attempts,
        "baseline_evaluations": 1, "candidate_evaluations": attempts,
        "baseline": {"fitness": 3.0}, "optimized": {"fitness": 3.0},
        "improvement": 0.0, "history": [],
        "outcome_counts": dict.fromkeys(
            ("accepted", "rejected", "crashed", "failed_validation", "no_proposal"), 0),
    }
    return path, report


def _write_research(path, report):
    path.write_text(json.dumps(report), encoding="utf-8")


@pytest.mark.parametrize("outcome", [None, "accepted", "crashed", "no_proposal"])
def test_research_display_remains_unverified(tmp_path, outcome):
    path, report = _research_report(tmp_path, int(outcome is not None))
    if outcome:
        report["history"] = [{"iteration": 1, "status": outcome}]
        report["outcome_counts"][outcome] = 1
    if outcome == "accepted":
        report["optimized"]["fitness"], report["improvement"] = 5.0, 2.0
    if outcome == "no_proposal":
        report["candidate_evaluations"] = 0
    # A report cannot supply its own independent verification/retention authority.
    report.update(independently_verified=True, retained_improvements=100,
                  resource_usage={"tokens": 0})
    _write_research(path, report)
    result = dashboard_alerts.read_research_report_summary(path, "a" * 64)
    assert result["state"] == "unverified_diagnostic"
    assert result["attempts"] == int(outcome is not None)
    assert result["outcome_counts"] == report["outcome_counts"]
    assert result["improvement"] == report["improvement"]
    assert all(result[k] is None for k in (
        "independently_verified", "retained_improvements", "resource_usage"))
    assert result["file_age_seconds"] >= 0


@pytest.mark.parametrize("field,value", [
    ("schema", "other"), ("status", "aborted"), ("status", "incomplete"),
    ("dry_run", 1), ("cleanup", "failed"), ("failure", {"type": "Error"}),
    ("cleanup_failure", {}), ("stop_reason", "interrupted"),
    ("baseline_input_sha256", "b" * 64), ("report_path", r"\\server\share\report.json"),
    ("invocation_id", "invocation-other"), ("attempts_started", True),
    ("attempts_requested", -1), ("attempts_finished", 1), ("iterations_run", 1),
    ("baseline_evaluations", 0), ("candidate_evaluations", 1),
    ("improvement", float("nan")), ("improvement", float("inf")),
    ("improvement", True), ("improvement", 2), ("baseline", {"fitness": True}),
    ("optimized", {"fitness": float("inf")}), ("history", [{}]),
    ("outcome_counts", {"accepted": 0}),
])
def test_research_display_invalid_reports_are_unknown(tmp_path, field, value):
    path, report = _research_report(tmp_path)
    report[field] = value
    _write_research(path, report)
    result = dashboard_alerts.read_research_report_summary(path, "a" * 64)
    assert result["state"] == "unknown"
    assert "improvement" not in result


@pytest.mark.parametrize("payload", ["{", "[]", "{\"status\":1,\"status\":2}",
                                     "[" * 2000, " " * (1024 * 1024 + 1)],
                         ids=["truncated", "array", "duplicate", "deep", "oversized"])
def test_research_display_bad_files_are_unknown(tmp_path, payload):
    path, _ = _research_report(tmp_path)
    path.write_text(payload, encoding="utf-8")
    assert dashboard_alerts.read_research_report_summary(path, "a" * 64)["state"] == "unknown"


@pytest.mark.parametrize("age", [-120, 90000])
def test_research_display_file_age_is_not_execution_freshness(tmp_path, age):
    path, report = _research_report(tmp_path)
    _write_research(path, report)
    timestamp = datetime.now(timezone.utc).timestamp() - age
    os.utime(path, (timestamp, timestamp))
    result = dashboard_alerts.read_research_report_summary(path, "a" * 64)
    assert result["state"] == "unknown"
    assert result["reason"] == "stale_file"


@pytest.mark.parametrize("selection,digest", [
    (None, "a" * 64), ("relative/report.json", "a" * 64),
    (r"\\server\share\report.json", "a" * 64),
    (r"\\?\C:\report.json", "a" * 64), ("/report.json", "invalid"),
    (r"\/server/share/invocation-fixture/report.json", "a" * 64),
    (r"/\server/share/invocation-fixture/report.json", "a" * 64),
])
def test_research_display_invalid_selection_does_not_open(monkeypatch, selection, digest):
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid selection must not touch the filesystem")
    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", forbidden)
        guard.setattr(Path, "stat", forbidden)
        result = dashboard_alerts.read_research_report_summary(selection, digest)
    assert result["state"] == "unknown"


def test_research_display_missing_or_directory_is_unknown(tmp_path):
    path, _ = _research_report(tmp_path)
    assert dashboard_alerts.read_research_report_summary(path, "a" * 64)["state"] == "unknown"
    path.mkdir()
    assert dashboard_alerts.read_research_report_summary(path, "a" * 64)["state"] == "unknown"


def test_research_display_is_read_only_and_sanitized(tmp_path, monkeypatch, capsys):
    path, report = _research_report(tmp_path)
    report["ignored"] = "PRIVATE-CONTENT\n\x1b[31m"
    _write_research(path, report)
    before = path.read_bytes()
    monkeypatch.setenv("WRE_RESEARCH_REPORT_PATH", str(path))
    monkeypatch.setenv("WRE_RESEARCH_BASELINE_SHA256", "a" * 64)
    def forbidden(*args, **kwargs):
        pytest.fail("Research display must not initialize health/memory or write")
    monkeypatch.setattr(dashboard_alerts, "check_dashboard_health", forbidden)
    monkeypatch.setattr(dashboard_alerts, "DashboardAlertMonitor", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    dashboard_alerts.print_research_report_summary()
    output = capsys.readouterr().out
    assert "unverified_diagnostic" in output
    assert "retained=unknown" in output and "resource_usage=unknown" in output
    assert "PRIVATE-CONTENT" not in output and str(path) not in output
    assert path.read_bytes() == before


@pytest.mark.parametrize("change", ["bool_count", "negative_count", "wrong_history", "duplicate_key"])
def test_research_display_rejects_ambiguous_accounting(tmp_path, change):
    path, report = _research_report(tmp_path)
    if change == "bool_count":
        report["outcome_counts"]["accepted"] = False
    elif change == "negative_count":
        report["outcome_counts"]["crashed"] = -1
    elif change == "wrong_history":
        report["history"] = [{"iteration": 1, "status": "accepted"}]
    _write_research(path, report)
    if change == "duplicate_key":
        path.write_text(path.read_text().replace('"dry_run": true',
                        '"dry_run": false, "dry_run": true'), encoding="utf-8")
    assert dashboard_alerts.read_research_report_summary(path, "a" * 64)["state"] == "unknown"


@pytest.mark.parametrize("age_limit", [0, -1, True, float("nan"), float("inf"), "86400"])
def test_research_display_invalid_age_budget_is_unknown(tmp_path, age_limit):
    path, report = _research_report(tmp_path)
    _write_research(path, report)
    result = dashboard_alerts.read_research_report_summary(
        path, "a" * 64, max_age_seconds=age_limit)
    assert result["state"] == "unknown"


def test_main_dashboard_reads_actual_selected_report(tmp_path, monkeypatch, capsys):
    import main
    path, report = _research_report(tmp_path)
    _write_research(path, report)
    monkeypatch.setenv("WRE_RESEARCH_REPORT_PATH", str(path))
    monkeypatch.setenv("WRE_RESEARCH_BASELINE_SHA256", "a" * 64)
    monkeypatch.setenv("WRE_DASHBOARD_PREFLIGHT", "1")
    monkeypatch.setenv("WRE_DASHBOARD_PREFLIGHT_ENFORCED", "1")
    monkeypatch.setattr(dashboard_alerts, "check_dashboard_health", lambda: {"healthy": True})
    assert main.run_wre_dashboard_preflight(tmp_path) is True
    output = capsys.readouterr().out
    assert "[WRE-RESEARCH] unverified_diagnostic" in output
    assert "attempts=0" in output and "retained=unknown" in output
    assert "[WRE-DASHBOARD] preflight=PASS" in output


@pytest.mark.parametrize("accepted", [False, True])
def test_research_display_gain_requires_accepted_attempt(tmp_path, accepted):
    path, report = _research_report(tmp_path, int(accepted))
    if accepted:
        report["history"] = [{"iteration": 1, "status": "accepted"}]
        report["outcome_counts"]["accepted"] = 1
    else:
        report["optimized"]["fitness"], report["improvement"] = 5.0, 2.0
    _write_research(path, report)
    assert dashboard_alerts.read_research_report_summary(path, "a" * 64)["state"] == "unknown"


def test_prune_old_snapshots_removes_aged_files(tmp_path):
    old_file = tmp_path / "dashboard_snapshot_old.json"
    new_file = tmp_path / "dashboard_snapshot_new.json"
    latest = tmp_path / "latest.json"

    old_file.write_text("{}", encoding="utf-8")
    new_file.write_text("{}", encoding="utf-8")
    latest.write_text("{}", encoding="utf-8")

    old_time = datetime.now(timezone.utc) - timedelta(days=45)
    new_time = datetime.now(timezone.utc)
    old_ts = old_time.timestamp()
    new_ts = new_time.timestamp()

    import os

    os.utime(old_file, (old_ts, old_ts))
    os.utime(new_file, (new_ts, new_ts))
    os.utime(latest, (old_ts, old_ts))

    removed = prune_old_snapshots(tmp_path, retention_days=30)
    assert removed == 1
    assert not old_file.exists()
    assert new_file.exists()
    # latest.json should never be touched by pruning
    assert latest.exists()
