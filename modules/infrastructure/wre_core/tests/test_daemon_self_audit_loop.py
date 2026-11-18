#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for 0102 daemon self-audit loop."""

from __future__ import annotations

import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from modules.infrastructure.wre_core.src.daemon_self_audit_loop import (
    DaemonSelfAuditLoop,
)

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
    events = loop.scan_once()

    assert events == 1
    rows = _read_jsonl(loop.task_log_path)
    assert rows[0]["auto_fix_attempted"] is False
    assert rows[0]["auto_fix_result"].startswith("improvement_job_proposed:")


def test_direct_start_primitive_requires_master_process_gate(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "1")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOW_LEGACY_AUTO_FIX", "1")
    monkeypatch.delenv("OPENCLAW_SELF_AUDIT_ALLOW_LEGACY_PROCESS_DISPATCH", raising=False)
    loop = DaemonSelfAuditLoop(repo_root=tmp_path)

    attempted, result = loop._dispatch_start_command("echo start")

    assert attempted is False
    assert result == "legacy_process_dispatch_disabled"


def test_direct_escalation_primitive_requires_master_process_gate(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOW_LEGACY_ESCALATION_DISPATCH", "1")
    monkeypatch.delenv("OPENCLAW_SELF_AUDIT_ALLOW_LEGACY_PROCESS_DISPATCH", raising=False)
    loop = DaemonSelfAuditLoop(repo_root=tmp_path)

    attempted, result = loop._dispatch_escalation_command("echo escalate")

    assert attempted is False
    assert result == "legacy_process_dispatch_disabled"


def test_self_audit_legacy_policy_fix_remains_disabled_with_dual_opt_in(
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
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOW_LEGACY_PROCESS_DISPATCH", "1")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOWED_FIXES", "start_ironclaw_gateway")
    monkeypatch.setenv("IRONCLAW_START_CMD", "echo start")
    monkeypatch.setenv("IRONCLAW_START_RETRY_COUNT", "0")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    events = loop.scan_once()

    assert events == 1
    rows = _read_jsonl(loop.task_log_path)
    assert rows[0]["auto_fix_attempted"] is False
    assert rows[0]["auto_fix_result"].startswith("improvement_job_proposed:")


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
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOW_LEGACY_PROCESS_DISPATCH", "1")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOWED_FIXES", "start_ironclaw_gateway")
    monkeypatch.setenv("IRONCLAW_START_CMD", "echo start")
    monkeypatch.setenv("IRONCLAW_START_RETRY_COUNT", "2")
    monkeypatch.setenv("IRONCLAW_START_RETRY_DELAY_SEC", "0")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    with patch.object(
        DaemonSelfAuditLoop,
        "_verify_ironclaw_health",
        return_value=(False, "health_error:URLError"),
    ):
        events = loop.scan_once()

    assert events == 1
    rows = _read_jsonl(loop.task_log_path)
    assert rows[0]["auto_fix_attempted"] is False
    assert rows[0]["auto_fix_result"].startswith("improvement_job_proposed:")


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
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOW_LEGACY_PROCESS_DISPATCH", "1")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOWED_FIXES", "start_ironclaw_gateway")
    monkeypatch.setenv("IRONCLAW_START_CMD", "echo start")
    monkeypatch.setenv("IRONCLAW_START_RETRY_COUNT", "3")
    monkeypatch.setenv("IRONCLAW_START_RETRY_DELAY_SEC", "0")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    with patch.object(
        DaemonSelfAuditLoop,
        "_verify_ironclaw_health",
        return_value=(True, "health_ok:200"),
    ):
        events = loop.scan_once()

    assert events == 1
    rows = _read_jsonl(loop.task_log_path)
    assert rows[0]["auto_fix_attempted"] is False
    assert rows[0]["auto_fix_result"].startswith("improvement_job_proposed:")


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

    report = loop.runtime_root / "dae_event_store_health.json"
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
    assert escalations[0]["dispatch_attempted"] is False
    assert escalations[0]["dispatch_result"] == "legacy_escalation_dispatch_disabled"


def test_self_audit_legacy_escalation_remains_disabled_with_flags(
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
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ALLOW_LEGACY_PROCESS_DISPATCH", "1")

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
    assert escalations[0]["dispatch_attempted"] is False
    assert escalations[0]["dispatch_result"] == "legacy_escalation_dispatch_disabled"


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


def test_self_audit_runtime_artifacts_default_outside_repository(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("OPENCLAW_SELF_AUDIT_RUNTIME_ROOT", raising=False)
    monkeypatch.delenv("REDDOG_RESIDENT_RUNTIME_ROOT", raising=False)

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)

    with pytest.raises(ValueError):
        loop.runtime_root.relative_to(tmp_path.resolve())
    assert loop.task_log_path.parent == loop.runtime_root
    assert loop.state_path.parent == loop.runtime_root


def test_self_audit_rejects_runtime_root_inside_repository(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "OPENCLAW_SELF_AUDIT_RUNTIME_ROOT",
        str(tmp_path / "modules" / "runtime"),
    )

    with pytest.raises(ValueError, match="inside_repo"):
        DaemonSelfAuditLoop(repo_root=tmp_path)


def test_self_audit_redacts_secrets_before_all_runtime_persistence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    log_file = logs / "daemon.log"
    api_secret = "sk-1234567890abcdefghijkl"
    bearer_secret = "bearer-secret-value-123456"
    query_secret = "query-secret-value"
    log_file.write_text(
        "[ERROR] api\u200b_key="
        + api_secret
        + " Authorization: Bearer "
        + bearer_secret
        + " https://example.test/x?access_token="
        + query_secret
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "logs/**/*.log")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "0")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    assert loop.scan_once() == 1

    persisted = "\n".join(
        path.read_text(encoding="utf-8")
        for path in loop.runtime_root.glob("*")
        if path.is_file()
    )
    for secret in (api_secret, bearer_secret, query_secret):
        assert secret not in persisted
    assert "[REDACTED]" in persisted

    event = _read_jsonl(loop.task_log_path)[0]
    assert event["redaction_applied"] is True
    assert event["redaction_replacements"] >= 3
    assert not (tmp_path / "modules/infrastructure/wre_core/reports").exists()


def test_self_audit_rejects_log_glob_escape_and_external_symlink(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    (outside / "outside.log").write_text("[ERROR] external secret\n", encoding="utf-8")

    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "../outside/*.log")
    loop = DaemonSelfAuditLoop(repo_root=repo)
    assert loop.scan_once() == 0

    link = repo / "linked-logs"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        return
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "linked-logs/*.log")
    loop = DaemonSelfAuditLoop(repo_root=repo)
    assert loop.scan_once() == 0


def test_self_audit_redacts_generalized_secret_shapes_in_real_sinks(
    tmp_path: Path,
    monkeypatch,
) -> None:
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    secrets = (
        "openrouter-secret",
        "aws-secret",
        "my-password",
        "query-token",
        "cookie-one",
        "cookie-two",
        "private-key-fragment",
        "daemon-opaque-token",
        "daemon-auth-token",
    )
    (logs / "daemon.log").write_text(
        "[ERROR] OPENROUTER_API_KEY=openrouter-secret\n"
        "[ERROR] AWS_SECRET_ACCESS_KEY=aws-secret MY_PASSWORD=my-password\n"
        "[ERROR] https://example.test/?token=query-token\n"
        "[ERROR] Cookie: first=cookie-one; second=cookie-two\n"
        "[ERROR] token=daemon-opaque-token auth_token=daemon-auth-token\n"
        "[ERROR] -----BEGIN PRIVATE KEY----- private-key-fragment\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "logs/**/*.log")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "0")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    assert loop.scan_once() == 6

    persisted = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in loop.runtime_root.glob("*")
        if path.is_file()
    )
    for secret in secrets:
        assert secret not in persisted
    assert "[REDACTED" in persisted

def test_self_audit_serializes_concurrent_scans(tmp_path: Path, monkeypatch) -> None:
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    (logs / "daemon.log").write_text("[ERROR] health endpoint unavailable\n", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "logs/**/*.log")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "0")

    loop = DaemonSelfAuditLoop(repo_root=tmp_path)
    with ThreadPoolExecutor(max_workers=8) as executor:
        counts = list(executor.map(lambda _: loop.scan_once(), range(16)))

    assert sum(counts) == 1
    assert len(_read_jsonl(loop.task_log_path)) == 1


def test_self_audit_serializes_scans_across_loop_instances(
    tmp_path: Path,
    monkeypatch,
) -> None:
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    (logs / "daemon.log").write_text("[ERROR] health endpoint unavailable\n", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "logs/**/*.log")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "0")

    loops = [DaemonSelfAuditLoop(repo_root=tmp_path) for _ in range(4)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        counts = list(executor.map(lambda loop: loop.scan_once(), loops))

    assert sum(counts) == 1
    assert len(_read_jsonl(loops[0].task_log_path)) == 1


class _OwnedCounterMemory:
    def __init__(self, original, controls):
        self.owner = threading.get_ident()
        self.memory = original(db_path=controls.db_path)
        self.controls = controls
        self.close_threads = []
        self.closed = False
        controls.handles.append(self)

    def increment_counter(self, name, delta):
        if self.controls.before_increment:
            self.controls.before_increment()
        if self.controls.increment_error:
            raise self.controls.increment_error
        return self.memory.increment_counter(name, delta)

    def close(self):
        self.close_threads.append(threading.get_ident())
        self.memory.close()
        self.closed = True
        if self.controls.close_error:
            raise self.controls.close_error


def _cleanup_owned_counter_handles(controls):
    for handle in controls.handles:
        if handle.owner == threading.get_ident() and not handle.closed:
            handle.memory.close()
            handle.closed = True


@pytest.fixture
def counter_memory(tmp_path: Path, monkeypatch):
    from modules.infrastructure.wre_core.src import pattern_memory

    repo = tmp_path / "repo"
    (repo / "logs").mkdir(parents=True)
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_LOG_GLOBS", "logs/**/*.log")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "0")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_TELEMETRY", "1")
    original = pattern_memory.PatternMemory
    controls = SimpleNamespace(
        db_path=tmp_path / "counter.db", handles=[], factory_calls=0,
        factory_error=None, increment_error=None, close_error=None,
        before_increment=None, loop=DaemonSelfAuditLoop(repo),
        log_file=repo / "logs" / "daemon.log",
    )

    def factory():
        controls.factory_calls += 1
        if controls.factory_error:
            raise controls.factory_error
        return _OwnedCounterMemory(original, controls)

    monkeypatch.setattr(pattern_memory, "PatternMemory", factory)
    try:
        yield controls
    finally:
        _cleanup_owned_counter_handles(controls)


def _stored_counter(controls, name="owned_counter"):
    connection = sqlite3.connect(str(controls.db_path))
    try:
        row = connection.execute(
            "SELECT counter_value FROM telemetry_counters WHERE counter_name = ?", (name,)
        ).fetchone()
        return row[0] if row else 0
    finally:
        connection.close()


def test_counter_operations_use_separate_closed_handles(counter_memory):
    state = counter_memory
    state.loop._increment_counter("owned_counter")
    state.loop._increment_counter("owned_counter", 2)

    assert _stored_counter(state) == 3
    assert state.factory_calls == len(state.handles) == 2
    for handle in state.handles:
        assert handle.close_threads == [handle.owner] == [threading.get_ident()]
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            handle.memory.get_counter("owned_counter")


@pytest.mark.parametrize("failure", (
    "factory", "increment", "close", "both", "interrupt", "interrupt_close",
))
def test_counter_failure_cleanup_and_propagation(counter_memory, failure):
    state = counter_memory
    if failure == "factory":
        state.factory_error = RuntimeError("factory failure")
    if failure in {"increment", "both"}:
        state.increment_error = RuntimeError("increment failure")
    if failure.startswith("interrupt"):
        state.increment_error = KeyboardInterrupt("increment interrupted")
    if failure in {"close", "both", "interrupt_close"}:
        state.close_error = RuntimeError("close failure")

    if failure.startswith("interrupt"):
        with pytest.raises(KeyboardInterrupt) as caught:
            state.loop._increment_counter("owned_counter")
        assert caught.value is state.increment_error
    else:
        state.loop._increment_counter("owned_counter")
    assert state.factory_calls == 1
    assert len(state.handles) == (0 if failure == "factory" else 1)
    for handle in state.handles:
        assert handle.close_threads == [handle.owner] == [threading.get_ident()]
        assert handle.closed
    if state.handles:
        assert _stored_counter(state) == (1 if failure == "close" else 0)


def test_counter_disabled_telemetry_never_constructs_memory(counter_memory):
    state = counter_memory
    state.loop.enable_telemetry = False
    state.factory_error = AssertionError("disabled telemetry constructed memory")
    state.loop._increment_counter("owned_counter")
    assert state.factory_calls == 0
    assert not state.db_path.exists()


def test_distinct_live_scan_threads_persist_both_event_counters(counter_memory):
    state = counter_memory
    ready, release = threading.Event(), threading.Event()
    state.log_file.write_text("[ERROR] lifecycle alpha failure\n", encoding="utf-8")

    def background_scan():
        try:
            count = state.loop.scan_once()
            ready.set()
            assert release.wait(5)
            return count
        finally:
            _cleanup_owned_counter_handles(state)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(background_scan)
        try:
            assert ready.wait(5)
            assert future.running()
            assert state.handles[0].owner != threading.get_ident()
            with state.log_file.open("a", encoding="utf-8") as handle:
                handle.write("[ERROR] lifecycle beta failure\n")
            assert state.loop.scan_once() == 1
        finally:
            release.set()
        assert future.result(timeout=5) == 1
    assert _stored_counter(state, "self_audit_events_total") == 2
    rows = _read_jsonl(state.loop.task_log_path)
    assert len(rows) == len({row["signature"] for row in rows}) == 2
    assert len(state.handles) == len({handle.owner for handle in state.handles}) == 2
    assert all(handle.close_threads == [handle.owner] for handle in state.handles)


def test_stop_timeout_does_not_close_active_foreign_counter(counter_memory):
    state = counter_memory
    entered, release = threading.Event(), threading.Event()

    def pause_increment():
        state.loop._thread = threading.current_thread()
        entered.set()
        assert release.wait(5)

    def background_counter():
        try:
            state.loop._increment_counter("owned_counter")
        finally:
            _cleanup_owned_counter_handles(state)

    state.before_increment = pause_increment
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(background_counter)
        try:
            assert entered.wait(5)
            state.loop.stop(timeout_sec=0.01)
            assert future.running()
            assert state.loop._stop.is_set()
            assert state.handles[0].close_threads == []
            assert not state.handles[0].closed
        finally:
            release.set()
        future.result(timeout=5)
    handle = state.handles[0]
    assert handle.owner != threading.get_ident()
    assert handle.close_threads == [handle.owner]
    assert _stored_counter(state) == 1
