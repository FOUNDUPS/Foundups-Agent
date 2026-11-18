#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for dependency/CVE startup preflight."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

from modules.infrastructure.wre_core.src.dependency_security_preflight import (
    _run,
    run_dependency_security_preflight,
)


def test_dependency_preflight_passes_with_clean_results(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_MAX_CRITICAL", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_MAX_HIGH", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_REQUIRE_TOOLS", "1")

    def _fake_run(cmd, timeout_sec=180, cwd=None):
        if "pip_audit" in " ".join(cmd):
            return {"ok": True, "code": 0, "stdout": "[]", "stderr": "", "cmd": cmd}
        return {"ok": True, "code": 0, "stdout": "{}", "stderr": "", "cmd": cmd}

    with patch("modules.infrastructure.wre_core.src.dependency_security_preflight._run", side_effect=_fake_run):
        status = run_dependency_security_preflight(tmp_path, force=True)

    assert status["passed"] is True
    assert status["totals"]["critical"] == 0
    assert status["totals"]["high"] == 0


def test_dependency_command_rejects_invalid_utf8_scanner_output() -> None:
    result = _run(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(bytes([0x81]))",
        ]
    )

    assert result["ok"] is False
    assert result["code"] == 0
    assert result["stdout"] == ""
    assert result["failure_kind"] == "invalid_stdout_encoding"


def test_dependency_command_preserves_valid_utf8_output() -> None:
    result = _run(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write('advisory \\u2014 current'.encode('utf-8'))",
        ]
    )

    assert result["ok"] is True
    assert result["stdout"] == "advisory \u2014 current"


def test_dependency_command_captures_bytes_before_strict_decode() -> None:
    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight.subprocess.run"
    ) as mocked:
        mocked.return_value.returncode = 0
        mocked.return_value.stdout = b"{}"
        mocked.return_value.stderr = b""

        result = _run(["scanner", "--json"])

    assert result["ok"] is True
    assert mocked.call_args.kwargs["text"] is False
    assert "encoding" not in mocked.call_args.kwargs
    assert "errors" not in mocked.call_args.kwargs


def test_dependency_preflight_rejects_empty_npm_evidence(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_REQUIRE_TOOLS", "0")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

    def _fake_run(cmd, timeout_sec=180, cwd=None):
        if "pip_audit" in " ".join(cmd):
            return {"ok": True, "code": 0, "stdout": "[]", "stderr": "", "cmd": cmd}
        return {"ok": True, "code": 0, "stdout": "", "stderr": "", "cmd": cmd}

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_fake_run,
    ):
        status = run_dependency_security_preflight(tmp_path, force=True)

    assert status["passed"] is False
    assert status["tool_failures"] == 1
    assert status["evidence_failures"] == 1


def test_dependency_preflight_rejects_missing_npm_schema(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_REQUIRE_TOOLS", "0")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

    def _fake_run(cmd, timeout_sec=180, cwd=None):
        stdout = "[]" if "pip_audit" in " ".join(cmd) else "{}"
        return {"ok": True, "code": 0, "stdout": stdout, "stderr": "", "cmd": cmd}

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_fake_run,
    ):
        status = run_dependency_security_preflight(tmp_path, force=True)

    assert status["passed"] is False
    assert status["evidence_failures"] == 1


def test_dependency_preflight_rejects_nonnative_npm_counts(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_REQUIRE_TOOLS", "0")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

    def _fake_run(cmd, timeout_sec=180, cwd=None):
        if "pip_audit" in " ".join(cmd):
            stdout = "[]"
        else:
            stdout = (
                '{"metadata":{"vulnerabilities":{"info":0,"critical":"0",'
                '"high":0,"moderate":0,"low":0,"total":0}}}'
            )
        return {"ok": True, "code": 0, "stdout": stdout, "stderr": "", "cmd": cmd}

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_fake_run,
    ):
        status = run_dependency_security_preflight(tmp_path, force=True)

    assert status["passed"] is False
    assert status["evidence_failures"] == 1


def test_dependency_preflight_counts_utf8_npm_advisory(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_MAX_CRITICAL", "2")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_MAX_HIGH", "7")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_REQUIRE_TOOLS", "1")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

    def _fake_run(cmd, timeout_sec=180, cwd=None):
        if "pip_audit" in " ".join(cmd):
            stdout = "[]"
        else:
            stdout = (
                '{"advisories":{"title":"clerk-nextjs \u2014 current"},'
                '"metadata":{"vulnerabilities":{"info":0,"critical":2,"high":7,'
                '"moderate":0,"low":0,"total":9}}}'
            )
        return {"ok": True, "code": 1, "stdout": stdout, "stderr": "", "cmd": cmd}

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_fake_run,
    ):
        status = run_dependency_security_preflight(tmp_path, force=True)

    assert status["passed"] is True
    assert status["totals"]["critical"] == 2
    assert status["totals"]["high"] == 7


def test_dependency_preflight_rejects_cargo_exit_101(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_REQUIRE_TOOLS", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_CHECK_NODE", "0")
    (tmp_path / "Cargo.lock").write_text("", encoding="utf-8")

    def _fake_run(cmd, timeout_sec=180, cwd=None):
        if "pip_audit" in " ".join(cmd):
            return {"ok": True, "code": 0, "stdout": "[]", "stderr": "", "cmd": cmd}
        return {"ok": True, "code": 101, "stdout": "{}", "stderr": "", "cmd": cmd}

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_fake_run,
    ):
        status = run_dependency_security_preflight(tmp_path, force=True)

    assert status["passed"] is False
    assert status["tool_failures"] == 1
    assert status["evidence_failures"] == 1


def test_dependency_preflight_invalidates_legacy_cache(tmp_path: Path, monkeypatch):
    cache = (
        tmp_path
        / "modules"
        / "infrastructure"
        / "wre_core"
        / "reports"
        / "dependency_security_cache.json"
    )
    cache.parent.mkdir(parents=True)
    cache.write_text(
        '{"checked_at":99999999999,"passed":true,"totals":{}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_CHECK_NODE", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_CHECK_RUST", "0")

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        return_value={
            "ok": True,
            "code": 0,
            "stdout": "[]",
            "stderr": "",
            "cmd": [],
        },
    ) as mocked:
        status = run_dependency_security_preflight(tmp_path, force=False)

    assert mocked.called
    assert status["cached"] is False
    assert status["schema_version"] == "dependency_security_preflight.v3"


def test_dependency_preflight_fails_on_high_threshold_breach(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_MAX_CRITICAL", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_MAX_HIGH", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_REQUIRE_TOOLS", "1")
    # Trigger node check path.
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

    def _fake_run(cmd, timeout_sec=180, cwd=None):
        cmd_str = " ".join(cmd)
        if "pip_audit" in cmd_str:
            return {"ok": True, "code": 0, "stdout": "[]", "stderr": "", "cmd": cmd}
        if cmd and Path(cmd[0]).name.startswith("npm"):
            stdout = '{"metadata":{"vulnerabilities":{"info":0,"critical":0,"high":2,"moderate":0,"low":0,"total":2}}}'
            return {"ok": True, "code": 1, "stdout": stdout, "stderr": "", "cmd": cmd}
        return {"ok": True, "code": 0, "stdout": "{}", "stderr": "", "cmd": cmd}

    with patch("modules.infrastructure.wre_core.src.dependency_security_preflight._run", side_effect=_fake_run):
        status = run_dependency_security_preflight(tmp_path, force=True)

    assert status["passed"] is False
    assert status["totals"]["high"] == 2


def test_dependency_preflight_fails_when_tools_required_and_unavailable(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_REQUIRE_TOOLS", "1")

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        return_value={"ok": False, "code": 127, "stdout": "", "stderr": "missing", "cmd": []},
    ):
        status = run_dependency_security_preflight(tmp_path, force=True)

    assert status["passed"] is False
    assert status["tool_failures"] >= 1


def test_dependency_preflight_scans_all_node_lockfiles(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_MAX_CRITICAL", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_MAX_HIGH", "5")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_REQUIRE_TOOLS", "1")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_NODE_LOCK_SCOPE", "all")

    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    app = tmp_path / "apps" / "web"
    app.mkdir(parents=True, exist_ok=True)
    (app / "package-lock.json").write_text("{}", encoding="utf-8")

    def _fake_run(cmd, timeout_sec=180, cwd=None):
        cmd_str = " ".join(cmd)
        if "pip_audit" in cmd_str:
            return {"ok": True, "code": 0, "stdout": "[]", "stderr": "", "cmd": cmd}
        if cmd and Path(cmd[0]).name.startswith("npm"):
            if cwd and str(cwd).endswith("apps\\web"):
                stdout = '{"metadata":{"vulnerabilities":{"info":0,"critical":0,"high":3,"moderate":0,"low":0,"total":3}}}'
            else:
                stdout = '{"metadata":{"vulnerabilities":{"info":0,"critical":0,"high":2,"moderate":0,"low":0,"total":2}}}'
            return {"ok": True, "code": 1, "stdout": stdout, "stderr": "", "cmd": cmd}
        return {"ok": True, "code": 0, "stdout": "{}", "stderr": "", "cmd": cmd}

    with patch("modules.infrastructure.wre_core.src.dependency_security_preflight._run", side_effect=_fake_run):
        status = run_dependency_security_preflight(tmp_path, force=True)

    assert status["node_lock_scope"] == "all"
    assert status["node_lock_count"] == 2
    assert status["totals"]["high"] == 5
    assert status["passed"] is True


def test_dependency_preflight_ignores_hidden_nested_worktree_lockfiles(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_MAX_CRITICAL", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_MAX_HIGH", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_REQUIRE_TOOLS", "1")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_NODE_LOCK_SCOPE", "all")

    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    hidden = tmp_path / ".feature_clean"
    hidden.mkdir(parents=True, exist_ok=True)
    (hidden / ".git").write_text("gitdir: /tmp/fake\n", encoding="utf-8")
    (hidden / "package-lock.json").write_text("{}", encoding="utf-8")

    def _fake_run(cmd, timeout_sec=180, cwd=None):
        cmd_str = " ".join(cmd)
        if "pip_audit" in cmd_str:
            return {"ok": True, "code": 0, "stdout": "[]", "stderr": "", "cmd": cmd}
        if cmd and Path(cmd[0]).name.startswith("npm"):
            stdout = '{"metadata":{"vulnerabilities":{"info":0,"critical":0,"high":0,"moderate":0,"low":0,"total":0}}}'
            return {"ok": True, "code": 0, "stdout": stdout, "stderr": "", "cmd": cmd}
        return {"ok": True, "code": 0, "stdout": "{}", "stderr": "", "cmd": cmd}

    with patch("modules.infrastructure.wre_core.src.dependency_security_preflight._run", side_effect=_fake_run):
        status = run_dependency_security_preflight(tmp_path, force=True)

    assert status["node_lock_scope"] == "all"
    assert status["node_lock_count"] == 1


def test_dependency_preflight_counts_pip_audit_dict_payload_and_unknown_threshold(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_MAX_CRITICAL", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_MAX_HIGH", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_MAX_UNKNOWN", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_REQUIRE_TOOLS", "1")

    def _fake_run(cmd, timeout_sec=180, cwd=None):
        cmd_str = " ".join(cmd)
        if "pip_audit" in cmd_str:
            stdout = (
                '{"dependencies":[{"name":"pkg","version":"1","vulns":[{"id":"CVE-0000-0000"}]}],'
                '"fixes":[]}'
            )
            return {"ok": True, "code": 1, "stdout": stdout, "stderr": "", "cmd": cmd}
        return {"ok": True, "code": 0, "stdout": "{}", "stderr": "", "cmd": cmd}

    with patch("modules.infrastructure.wre_core.src.dependency_security_preflight._run", side_effect=_fake_run):
        status = run_dependency_security_preflight(tmp_path, force=True)

    assert status["totals"]["unknown"] == 1
    assert status["max_unknown"] == 0
    assert status["passed"] is False


def _clean_scanner_run(cmd, timeout_sec=180, cwd=None):
    if "pip_audit" in " ".join(cmd):
        stdout = "[]"
    else:
        stdout = (
            '{"metadata":{"vulnerabilities":{"info":0,"low":0,'
            '"moderate":0,"high":0,"critical":0,"total":0}}}'
        )
    return {"ok": True, "code": 0, "stdout": stdout, "stderr": "", "cmd": cmd}


def _disable_non_python_scanners(monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_CHECK_NODE", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_CHECK_RUST", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_PREFLIGHT_ENFORCED", "0")


def _cache_file(repo_root: Path) -> Path:
    return (
        repo_root
        / "modules"
        / "infrastructure"
        / "wre_core"
        / "reports"
        / "dependency_security_cache.json"
    )


def test_dependency_preflight_cache_is_advisory_only(tmp_path: Path, monkeypatch):
    _disable_non_python_scanners(monkeypatch)
    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_clean_scanner_run,
    ):
        run_dependency_security_preflight(tmp_path, force=True)

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=AssertionError("cache should avoid a live advisory scan"),
    ):
        status = run_dependency_security_preflight(tmp_path, force=False)

    assert status["cached"] is True
    assert status["cache_authority"] == "ADVISORY_ONLY"
    assert status["passed"] is False
    assert status["degraded"] is True
    assert status["counts_withheld"] is True
    assert status["evidence_failures"] == 1


def test_dependency_preflight_enforced_mode_ignores_cache(tmp_path: Path, monkeypatch):
    _disable_non_python_scanners(monkeypatch)
    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_clean_scanner_run,
    ):
        run_dependency_security_preflight(tmp_path, force=True)
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_PREFLIGHT_ENFORCED", "1")

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_clean_scanner_run,
    ) as mocked:
        status = run_dependency_security_preflight(tmp_path, force=False)

    assert mocked.called
    assert status["cached"] is False
    assert status["cache_authority"] == "LIVE_SCAN"


def test_dependency_preflight_cache_rejects_threshold_change(tmp_path: Path, monkeypatch):
    _disable_non_python_scanners(monkeypatch)
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_MAX_HIGH", "5")
    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_clean_scanner_run,
    ):
        run_dependency_security_preflight(tmp_path, force=True)
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_MAX_HIGH", "0")

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_clean_scanner_run,
    ) as mocked:
        status = run_dependency_security_preflight(tmp_path, force=False)

    assert mocked.called
    assert status["cached"] is False


def test_dependency_preflight_cache_rejects_dependency_change(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_CHECK_RUST", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_PREFLIGHT_ENFORCED", "0")
    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_clean_scanner_run,
    ):
        run_dependency_security_preflight(tmp_path, force=True)
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_clean_scanner_run,
    ) as mocked:
        status = run_dependency_security_preflight(tmp_path, force=False)

    assert mocked.called
    assert status["node_lock_count"] == 1
    assert status["cached"] is False


def test_dependency_preflight_cache_rejects_future_timestamp(tmp_path: Path, monkeypatch):
    _disable_non_python_scanners(monkeypatch)
    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_clean_scanner_run,
    ):
        run_dependency_security_preflight(tmp_path, force=True)
    cache = json.loads(_cache_file(tmp_path).read_text(encoding="utf-8"))
    cache["checked_at"] = 99_999_999_999
    _cache_file(tmp_path).write_text(json.dumps(cache), encoding="utf-8")

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_clean_scanner_run,
    ) as mocked:
        status = run_dependency_security_preflight(tmp_path, force=False)

    assert mocked.called
    assert status["cached"] is False


def test_dependency_preflight_cache_rejects_internal_contradiction(tmp_path: Path, monkeypatch):
    _disable_non_python_scanners(monkeypatch)
    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_clean_scanner_run,
    ):
        run_dependency_security_preflight(tmp_path, force=True)
    cache = json.loads(_cache_file(tmp_path).read_text(encoding="utf-8"))
    cache.update(evidence_failures=1, passed=True)
    _cache_file(tmp_path).write_text(json.dumps(cache), encoding="utf-8")

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_clean_scanner_run,
    ) as mocked:
        status = run_dependency_security_preflight(tmp_path, force=False)

    assert mocked.called
    assert status["cached"] is False


def test_dependency_preflight_cache_rejects_tampered_policy(tmp_path: Path, monkeypatch):
    _disable_non_python_scanners(monkeypatch)
    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_clean_scanner_run,
    ):
        run_dependency_security_preflight(tmp_path, force=True)
    cache = json.loads(_cache_file(tmp_path).read_text(encoding="utf-8"))
    cache.update(max_high=999, passed=True)
    _cache_file(tmp_path).write_text(json.dumps(cache), encoding="utf-8")

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_clean_scanner_run,
    ) as mocked:
        status = run_dependency_security_preflight(tmp_path, force=False)

    assert mocked.called
    assert status["cached"] is False


def test_dependency_preflight_cache_rejects_nan_timestamp(tmp_path: Path, monkeypatch):
    _disable_non_python_scanners(monkeypatch)
    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_clean_scanner_run,
    ):
        run_dependency_security_preflight(tmp_path, force=True)
    cache = json.loads(_cache_file(tmp_path).read_text(encoding="utf-8"))
    cache["checked_at"] = float("nan")
    _cache_file(tmp_path).write_text(json.dumps(cache), encoding="utf-8")

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=_clean_scanner_run,
    ) as mocked:
        status = run_dependency_security_preflight(tmp_path, force=False)

    assert mocked.called
    assert status["cached"] is False


def test_dependency_preflight_rejects_inconsistent_npm_total(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_CHECK_RUST", "0")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

    def fake_run(cmd, timeout_sec=180, cwd=None):
        result = _clean_scanner_run(cmd, timeout_sec, cwd)
        if "pip_audit" not in " ".join(cmd):
            result["stdout"] = (
                '{"metadata":{"vulnerabilities":{"info":0,"low":0,'
                '"moderate":0,"high":0,"critical":0,"total":9}}}'
            )
        return result

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=fake_run,
    ):
        status = run_dependency_security_preflight(tmp_path, force=True)

    assert status["passed"] is False
    assert status["evidence_failures"] == 1


def test_dependency_preflight_rejects_inconsistent_cargo_summary(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_CHECK_NODE", "0")
    (tmp_path / "Cargo.lock").write_text("", encoding="utf-8")

    def fake_run(cmd, timeout_sec=180, cwd=None):
        if "pip_audit" in " ".join(cmd):
            return _clean_scanner_run(cmd, timeout_sec, cwd)
        return {
            "ok": True,
            "code": 1,
            "stdout": '{"vulnerabilities":{"found":true,"count":3,"list":[]}}',
            "stderr": "",
            "cmd": cmd,
        }

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=fake_run,
    ):
        status = run_dependency_security_preflight(tmp_path, force=True)

    assert status["passed"] is False
    assert status["evidence_failures"] == 1


def test_dependency_preflight_audits_each_cargo_lock(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_CHECK_NODE", "0")
    (tmp_path / "Cargo.lock").write_text("", encoding="utf-8")
    nested = tmp_path / "crates" / "worker"
    nested.mkdir(parents=True)
    (nested / "Cargo.lock").write_text("", encoding="utf-8")

    def fake_run(cmd, timeout_sec=180, cwd=None):
        if "pip_audit" in " ".join(cmd):
            return _clean_scanner_run(cmd, timeout_sec, cwd)
        vulnerable = Path(cwd or tmp_path) == nested
        item = '{"severity":"high"}' if vulnerable else ""
        return {
            "ok": True,
            "code": 1 if vulnerable else 0,
            "stdout": (
                '{"vulnerabilities":{"found":'
                f'{str(vulnerable).lower()},"count":{int(vulnerable)},'
                f'"list":[{item}]}}}}'
            ),
            "stderr": "",
            "cmd": cmd,
        }

    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        side_effect=fake_run,
    ) as mocked:
        status = run_dependency_security_preflight(tmp_path, force=True)

    cargo_calls = [call for call in mocked.call_args_list if "pip_audit" not in " ".join(call.args[0])]
    assert len(cargo_calls) == 2
    assert {Path(call.kwargs["cwd"]) for call in cargo_calls} == {tmp_path, nested}
    assert status["cargo_lock_count"] == 2
    assert status["totals"]["high"] == 1
    assert status["passed"] is False


def test_dependency_preflight_missing_optional_scanner_is_degraded(tmp_path: Path, monkeypatch):
    _disable_non_python_scanners(monkeypatch)
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_REQUIRE_TOOLS", "0")
    with patch(
        "modules.infrastructure.wre_core.src.dependency_security_preflight._run",
        return_value={
            "ok": False,
            "failure_kind": "process_error",
            "code": 127,
            "stdout": "",
            "stderr": "missing",
            "cmd": [],
        },
    ):
        status = run_dependency_security_preflight(tmp_path, force=True)

    assert status["passed"] is False
    assert status["degraded"] is True
    assert status["available"] is False
    assert status["checks"][0]["passed"] is False
