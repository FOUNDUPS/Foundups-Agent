#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for 0102 daemon self-audit loop."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

from modules.infrastructure.wre_core.src.daemon_self_audit_loop import (
    DaemonSelfAuditLoop,
)

POPEN_TARGET = "modules.infrastructure.wre_core.src.daemon_self_audit_loop.subprocess.Popen"


def _read_jsonl(path: Path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def test_self_audit_opens_task_on_error_line(tmp_path: Path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    log_file = logs / "daemon.log"
    log_file.write_text("[ERROR] health endpoint unavailable\n", encoding="utf-8")

    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "logs/**/*.log")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "0")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    events = loop.scan_once()

    assert events == 1
    rows = _read_jsonl(loop.task_log_path)
    assert len(rows) == 1
    assert rows[0]["recommended_fix"] == "start_ironclaw_gateway"
    assert rows[0]["auto_fix_attempted"] is False
    assert rows[0]["auto_fix_result"].startswith("improvement_job_proposed:")
    assert rows[0]["improvement_job_id"].startswith("imp_")

    proposals = _read_jsonl(loop.improvement_job_log_path)
    assert len(proposals) == 1
    assert proposals[0]["job"]["status"] == "pending"
    assert proposals[0]["job"]["dry_run"] is True
    assert proposals[0]["no_execution_performed"] is True


def test_self_audit_auto_fix_requires_legacy_opt_in(tmp_path: Path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    log_file = logs / "daemon.log"
    log_file.write_text(
        "IronClaw runtime is unavailable, health endpoint unavailable\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "logs/**/*.log")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "1")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOWED_FIXES", "start_ironclaw_gateway")
    monkeypatch.setenv("IRONCLAW_START_CMD", "echo start")
    # This test only exercises dispatch; bypass the health-poll retry loop
    # added by IRONCLAW_START_RETRY_COUNT (covered by a dedicated test).
    monkeypatch.setenv("IRONCLAW_START_RETRY_COUNT", "0")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    with patch(POPEN_TARGET) as mock_popen:
        events = loop.scan_once()

    assert events == 1
    assert mock_popen.call_count == 0
    rows = _read_jsonl(loop.task_log_path)
    assert rows[0]["auto_fix_attempted"] is False
    assert rows[0]["auto_fix_result"].startswith("improvement_job_proposed:")


def test_self_audit_legacy_policy_fix_dispatches_with_dual_opt_in(
    tmp_path: Path, monkeypatch
):
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    log_file = logs / "daemon.log"
    log_file.write_text(
        "IronClaw runtime is unavailable, health endpoint unavailable\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "logs/**/*.log")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "1")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOW_LEGACY_AUTO_FIX", "1")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOWED_FIXES", "start_ironclaw_gateway")
    monkeypatch.setenv("IRONCLAW_START_CMD", "echo start")
    monkeypatch.setenv("IRONCLAW_START_RETRY_COUNT", "0")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    with patch(POPEN_TARGET) as mock_popen:
        events = loop.scan_once()

    assert events == 1
    assert mock_popen.call_count == 1
    rows = _read_jsonl(loop.task_log_path)
    assert rows[0]["auto_fix_attempted"] is True
    assert rows[0]["auto_fix_result"] == "start_command_dispatched"


def test_ironclaw_retry_reports_attempted_but_unhealthy(tmp_path: Path, monkeypatch):
    """Dispatch succeeds, health polling never does -> attempted=True, result flags unhealthy."""
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    log_file = logs / "daemon.log"
    log_file.write_text(
        "IronClaw runtime is unavailable, health endpoint unavailable\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "logs/**/*.log")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "1")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOW_LEGACY_AUTO_FIX", "1")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOWED_FIXES", "start_ironclaw_gateway")
    monkeypatch.setenv("IRONCLAW_START_CMD", "echo start")
    monkeypatch.setenv("IRONCLAW_START_RETRY_COUNT", "2")
    monkeypatch.setenv("IRONCLAW_START_RETRY_DELAY_SEC", "0")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    with patch(POPEN_TARGET) as mock_popen, patch.object(
        DaemonSelfAuditLoop,
        "_verify_ironclaw_health",
        return_value=(False, "health_error:URLError"),
    ):
        events = loop.scan_once()

    assert events == 1
    assert mock_popen.call_count == 1
    rows = _read_jsonl(loop.task_log_path)
    # Dispatch ran -> attempted=True, even though health never came up.
    assert rows[0]["auto_fix_attempted"] is True
    result = rows[0]["auto_fix_result"]
    assert result.startswith("attempted_but_unhealthy_after_2_attempt(s):")
    assert "start_command_dispatched" not in result  # classified as failure


def test_ironclaw_retry_reports_healthy_when_health_endpoint_responds(tmp_path: Path, monkeypatch):
    """Dispatch succeeds; health passes on first poll and keeps the marker."""
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    log_file = logs / "daemon.log"
    log_file.write_text(
        "IronClaw runtime is unavailable, health endpoint unavailable\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "logs/**/*.log")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "1")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOW_LEGACY_AUTO_FIX", "1")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOWED_FIXES", "start_ironclaw_gateway")
    monkeypatch.setenv("IRONCLAW_START_CMD", "echo start")
    monkeypatch.setenv("IRONCLAW_START_RETRY_COUNT", "3")
    monkeypatch.setenv("IRONCLAW_START_RETRY_DELAY_SEC", "0")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    with patch(POPEN_TARGET) as mock_popen, patch.object(
        DaemonSelfAuditLoop,
        "_verify_ironclaw_health",
        return_value=(True, "health_ok:200"),
    ):
        events = loop.scan_once()

    assert events == 1
    assert mock_popen.call_count == 1
    rows = _read_jsonl(loop.task_log_path)
    assert rows[0]["auto_fix_attempted"] is True
    result = rows[0]["auto_fix_result"]
    assert result.startswith("healthy_after_1_attempt(s):")
    assert "start_command_dispatched" in result  # classified as success


def test_self_audit_verifies_event_store_when_sequence_error_seen(tmp_path: Path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    log_file = logs / "daemon.log"
    log_file.write_text(
        "Write failed: UNIQUE constraint failed: dae_events.sequence_id\n",
        encoding="utf-8",
    )

    daemon_memory = tmp_path / "modules/infrastructure/dae_daemon/memory"
    daemon_memory.mkdir(parents=True)
    db_path = daemon_memory / "dae_audit.db"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE dae_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sequence_id INTEGER UNIQUE NOT NULL
            )
            """
        )
        conn.execute("INSERT INTO dae_events (sequence_id) VALUES (1)")
        conn.commit()

    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "logs/**/*.log")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "1")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOW_LEGACY_AUTO_FIX", "1")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOWED_FIXES", "verify_dae_event_store")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    events = loop.scan_once()

    assert events == 1
    rows = _read_jsonl(loop.task_log_path)
    assert rows[0]["recommended_fix"] == "verify_dae_event_store"
    assert rows[0]["auto_fix_attempted"] is True
    assert rows[0]["auto_fix_result"] == "event_store_verified"

    report = tmp_path / "modules/infrastructure/wre_core/reports/dae_event_store_health.json"
    assert report.exists()


def test_self_audit_persists_fix_stats(tmp_path: Path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    log_file = logs / "daemon.log"
    log_file.write_text(
        "IronClaw runtime is unavailable, health endpoint unavailable\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "logs/**/*.log")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "0")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    loop.scan_once()
    loop.stop()

    state = json.loads(loop.state_path.read_text(encoding="utf-8"))
    assert "fix_stats" in state
    assert "start_ironclaw_gateway" in state["fix_stats"]


def test_self_audit_escalates_repeated_signature(tmp_path: Path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    log_file = logs / "daemon.log"
    line = "IronClaw runtime is unavailable, health endpoint unavailable\n"
    log_file.write_text(line, encoding="utf-8")

    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "logs/**/*.log")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "0")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ESCALATE_AFTER", "3")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ESCALATION_WINDOW_SEC", "900")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ESCALATION_COOLDOWN_SEC", "600")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    loop.scan_once()

    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(line)
    loop._seen.clear()
    loop.scan_once()

    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(line)
    loop._seen.clear()
    loop.scan_once()

    escalations = _read_jsonl(loop.escalation_log_path)
    assert len(escalations) == 1
    assert escalations[0]["event_count"] >= 3
    assert escalations[0]["dispatch_attempted"] is False


def test_self_audit_escalation_command_requires_legacy_dispatch_flag(
    tmp_path: Path, monkeypatch
):
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    log_file = logs / "daemon.log"
    line = "IronClaw runtime is unavailable, health endpoint unavailable\n"
    log_file.write_text(line, encoding="utf-8")

    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "logs/**/*.log")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "0")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ESCALATE_AFTER", "3")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ESCALATION_WINDOW_SEC", "900")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ESCALATION_COOLDOWN_SEC", "600")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ESCALATE_CMD", "echo escalate")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    with patch(POPEN_TARGET) as mock_popen:
        loop.scan_once()
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(line)
        loop._seen.clear()
        loop.scan_once()
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(line)
        loop._seen.clear()
        loop.scan_once()

    assert mock_popen.call_count == 0
    escalations = _read_jsonl(loop.escalation_log_path)
    assert len(escalations) == 1
    assert escalations[0]["dispatch_attempted"] is False
    assert escalations[0]["dispatch_result"] == "legacy_escalation_dispatch_disabled"


def test_self_audit_legacy_escalation_dispatches_configured_command(
    tmp_path: Path, monkeypatch
):
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    log_file = logs / "daemon.log"
    line = "IronClaw runtime is unavailable, health endpoint unavailable\n"
    log_file.write_text(line, encoding="utf-8")

    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "logs/**/*.log")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "0")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ESCALATE_AFTER", "3")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ESCALATION_WINDOW_SEC", "900")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ESCALATION_COOLDOWN_SEC", "600")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ESCALATE_CMD", "echo escalate")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOW_LEGACY_ESCALATION_DISPATCH", "1")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    with patch(POPEN_TARGET) as mock_popen:
        loop.scan_once()
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(line)
        loop._seen.clear()
        loop.scan_once()
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(line)
        loop._seen.clear()
        loop.scan_once()

    assert mock_popen.call_count == 1
    escalations = _read_jsonl(loop.escalation_log_path)
    assert len(escalations) == 1
    assert escalations[0]["dispatch_attempted"] is True
    assert "dispatch" in escalations[0]["dispatch_result"]


def test_self_audit_filters_noise_signatures(tmp_path: Path, monkeypatch):
    """Noise signatures (traceback headers, generic raises) should be ignored."""
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    log_file = logs / "daemon.log"
    # Write noise patterns that match ERROR_PATTERNS but are in NOISE_SIGNATURES
    log_file.write_text(
        "Traceback (most recent call last):\n"
        "  File foo.py, line 42\n"
        "raise exception_class(message, screen, stacktrace)\n"
        "ntdll!RtlInitializeExceptionChain [0x7707d81b+6b]\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "logs/**/*.log")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "0")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    events = loop.scan_once()

    # All lines should be filtered as noise -- no events opened
    assert events == 0
    rows = _read_jsonl(loop.task_log_path)
    assert len(rows) == 0
