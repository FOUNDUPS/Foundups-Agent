"""Tests for the read-only OpenClaw/Hermes WSL runtime binding."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from modules.infrastructure.dependency_launcher.src import wsl_agent_runtime as runtime_module
from modules.infrastructure.dependency_launcher.src.wsl_agent_runtime import (
    COMPONENT_EXECUTABLES,
    build_wsl_version_command,
    probe_wsl_agent_runtime,
    run_wsl_agent_runtime_advisory,
)


ENV = {
    "FOUNDUPS_AGENT_WSL_RUNTIME_ENABLED": "1",
    "FOUNDUPS_AGENT_WSL_DISTRO": "Ubuntu-24.04",
    "FOUNDUPS_AGENT_WSL_EXPECTED_BASE": r"E:\Agents\WSL\Ubuntu-24.04",
}


def _base(_distro: str) -> str:
    return r"E:\Agents\WSL\Ubuntu-24.04"


def test_probe_accepts_exact_named_distro_and_components(capsys) -> None:
    calls: list[tuple[str, ...]] = []

    def runner(command, _timeout):
        assert _timeout == 10.0
        calls.append(tuple(command))
        version = (
            "OpenClaw 2026.7.1"
            if any(str(part).endswith("/openclaw") for part in command)
            else "Hermes Agent v0.19.1 (2026.7.30)"
        )
        return 0, version

    receipt = run_wsl_agent_runtime_advisory(
        environment=ENV, runner=runner, base_path_resolver=_base
    )

    assert receipt.state == "PASS"
    assert receipt.authority_class == "advisory_unverified_runtime_report"
    assert receipt.base_path == ENV["FOUNDUPS_AGENT_WSL_EXPECTED_BASE"]
    assert {item.component_id for item in receipt.components} == {"openclaw", "hermes"}
    assert all("--exec" in command and "--version" in command for command in calls)
    assert "preflight=PASS" in capsys.readouterr().out


def test_commands_are_fixed_shell_free_argument_vectors() -> None:
    assert build_wsl_version_command("openclaw", "Ubuntu-24.04") == (
        "wsl.exe",
        "--distribution",
        "Ubuntu-24.04",
        "--exec",
        "/usr/local/bin/openclaw",
        "--version",
    )
    assert COMPONENT_EXECUTABLES["hermes"] == "/usr/local/bin/hermes"


@pytest.mark.parametrize("distro", ["", "Ubuntu 24.04", "Ubuntu;whoami", "../Ubuntu"])
def test_invalid_distro_rejects(distro: str) -> None:
    with pytest.raises(ValueError, match="wsl_distro_invalid"):
        build_wsl_version_command("openclaw", distro)


def test_invalid_configured_distro_returns_fail_closed_receipt() -> None:
    receipt = probe_wsl_agent_runtime(
        environment={
            "FOUNDUPS_AGENT_WSL_RUNTIME_ENABLED": "1",
            "FOUNDUPS_AGENT_WSL_DISTRO": "Ubuntu;whoami",
        },
        runner=lambda *_args: pytest.fail("runner called"),
        base_path_resolver=lambda *_args: pytest.fail("resolver called"),
    )
    assert receipt.state == "NOT_READY"
    assert receipt.reasons == ("distro_invalid",)


def test_unknown_component_rejects() -> None:
    with pytest.raises(ValueError, match="wsl_component_not_allowlisted"):
        build_wsl_version_command("other", "Ubuntu-24.04")


def test_base_path_mismatch_rejects_before_component_probe() -> None:
    calls = 0

    def runner(_command, _timeout):
        nonlocal calls
        calls += 1
        return 0, "unexpected"

    receipt = probe_wsl_agent_runtime(
        environment=ENV,
        runner=runner,
        base_path_resolver=lambda _distro: r"C:\Users\user\AppData\Local\wsl",
    )

    assert receipt.state == "NOT_READY"
    assert receipt.reasons == ("distro_base_path_mismatch",)
    assert calls == 0


def test_missing_component_fails_closed_without_start_or_update() -> None:
    def runner(command, _timeout):
        if any(str(part).endswith("/openclaw") for part in command):
            return 0, "OpenClaw 2026.7.1"
        return 127, ""

    receipt = probe_wsl_agent_runtime(
        environment=ENV, runner=runner, base_path_resolver=_base
    )

    assert receipt.state == "NOT_READY"
    assert receipt.reasons == ("runtime_unavailable",)


def test_unexpected_version_output_does_not_authenticate_runtime() -> None:
    receipt = probe_wsl_agent_runtime(
        environment=ENV,
        runner=lambda *_args: (0, "healthy but substituted executable"),
        base_path_resolver=_base,
    )
    assert receipt.state == "NOT_READY"
    assert receipt.reasons == ("runtime_unavailable", "runtime_unavailable")


def test_version_evidence_excludes_trailing_diagnostic_metadata() -> None:
    def runner(command, _timeout):
        if any(str(part).endswith("/openclaw") for part in command):
            return 0, "OpenClaw 2026.7.1\nprivate diagnostic detail"
        return 0, "Hermes Agent v0.19.1 (2026.7.30)\nprivate diagnostic detail"

    receipt = probe_wsl_agent_runtime(
        environment=ENV, runner=runner, base_path_resolver=_base
    )
    assert receipt.state == "PASS"
    assert all("diagnostic" not in item.version for item in receipt.components)


def test_disabled_probe_performs_no_host_access() -> None:
    receipt = probe_wsl_agent_runtime(
        environment={"FOUNDUPS_AGENT_WSL_RUNTIME_ENABLED": "0"},
        runner=lambda *_args: pytest.fail("runner called"),
        base_path_resolver=lambda *_args: pytest.fail("resolver called"),
    )
    assert receipt.state == "DISABLED"


def test_probe_is_disabled_by_default() -> None:
    receipt = probe_wsl_agent_runtime(
        environment={},
        runner=lambda *_args: pytest.fail("runner called"),
        base_path_resolver=lambda *_args: pytest.fail("resolver called"),
    )
    assert receipt.state == "DISABLED"


def test_secret_shaped_suffix_cannot_enter_version_evidence(capsys) -> None:
    receipt = run_wsl_agent_runtime_advisory(
        environment=ENV,
        runner=lambda *_args: (0, "OpenClaw 2026.7.1 SECRET_SHAPED_VALUE"),
        base_path_resolver=_base,
    )
    assert receipt.state == "NOT_READY"
    assert "SECRET_SHAPED_VALUE" not in capsys.readouterr().out


def test_production_runner_uses_system32_wsl(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "System32" / "wsl.exe"
    executable.parent.mkdir()
    executable.write_bytes(b"MZ")
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return type("Completed", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()

    monkeypatch.setattr(runtime_module, "_trusted_wsl_path", lambda: executable)
    monkeypatch.setattr(runtime_module.subprocess, "run", fake_run)
    assert runtime_module._run_command(("wsl.exe", "--status"), 1.0) == (0, "ok")
    assert calls[0][0][0] == str(executable)
    assert calls[0][1]["shell"] is False


def test_probe_errors_are_content_free() -> None:
    receipt = probe_wsl_agent_runtime(
        environment=ENV,
        runner=lambda *_args: (_ for _ in ()).throw(RuntimeError("secret detail")),
        base_path_resolver=_base,
    )
    assert receipt.state == "NOT_READY"
    assert "secret detail" not in repr(receipt)


def test_source_has_no_network_shell_or_update_surface() -> None:
    path = Path(__file__).resolve().parents[1] / "src" / "wsl_agent_runtime.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_imports = {"requests", "urllib", "httpx", "aiohttp", "socket"}
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")])
    }
    assert not (imports & banned_imports)
    assert "shell=True" not in source
    assert "shutil.which" not in source
    assert "npm install" not in source
    assert "hermes update" not in source
    assert "openclaw update" not in source


def test_source_follows_wsp62_boundaries() -> None:
    path = Path(__file__).resolve().parents[1] / "src" / "wsl_agent_runtime.py"
    lines = path.read_text(encoding="utf-8").splitlines()
    tree = ast.parse("\n".join(lines))
    assert len(lines) <= 240
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 50
        if isinstance(node, ast.ClassDef):
            assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 200
