"""Injected tests for WSL metadata and explicit command-probe modes."""

from __future__ import annotations

import ast
import json
from dataclasses import asdict
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
    "FOUNDUPS_AGENT_WSL_COMMAND_PROBE_ENABLED": "1",
    "FOUNDUPS_AGENT_WSL_DISTRO": "Ubuntu-24.04",
    "FOUNDUPS_AGENT_WSL_EXPECTED_BASE": r"E:\Agents\WSL\Ubuntu-24.04",
}

# Captured legacy disabled wire; it contains no checkout or platform paths.
DISABLED_WIRE = (
    '{"authority_class":"advisory_unverified_runtime_report","base_path":"",'
    '"components":[],"distro":"","expected_base_path":"",'
    '"reasons":["runtime_probe_disabled"],'
    '"receipt_id":"sha256:ca46e9f3279389db36e506279323e6de1e6a633f8113faf107c56c92c57b966e",'
    '"schema_version":"foundups_agent_wsl_runtime_receipt.v1","state":"DISABLED"}'
)


def _base(_distro: str) -> str:
    return r"E:\Agents\WSL\Ubuntu-24.04"


@pytest.mark.parametrize("openclaw_version", [
    "OpenClaw 2026.7.1",
    "OpenClaw 2026.7.1 (abcdef0)",
    "OpenClaw 2026.7.1-2",
    "OpenClaw 2026.7.1-2 (abcdef0)",
])
def test_probe_accepts_exact_named_distro_and_components(capsys, openclaw_version) -> None:
    calls: list[tuple[str, ...]] = []

    def runner(command, _timeout):
        assert _timeout == 10.0
        calls.append(tuple(command))
        version = (
            openclaw_version
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
    assert receipt.components[0].version == openclaw_version
    assert all("--exec" in command and "--version" in command for command in calls)
    assert calls == [build_wsl_version_command(name, "Ubuntu-24.04") for name in COMPONENT_EXECUTABLES]
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


@pytest.mark.parametrize("command_enabled", ["0", "1"])
def test_base_path_mismatch_rejects_before_component_probe(command_enabled) -> None:
    calls = 0

    def runner(_command, _timeout):
        nonlocal calls
        calls += 1
        return 0, "unexpected"

    receipt = probe_wsl_agent_runtime(
        environment={**ENV, "FOUNDUPS_AGENT_WSL_COMMAND_PROBE_ENABLED": command_enabled},
        runner=runner,
        base_path_resolver=lambda _distro: r"C:\Users\user\AppData\Local\wsl",
    )

    assert receipt.state == "NOT_READY"
    assert receipt.reasons == ("distro_base_path_mismatch",)
    assert calls == 0


def test_missing_component_returns_not_ready_in_command_mode() -> None:
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


@pytest.mark.parametrize("runtime_enabled", [None, "0"])
@pytest.mark.parametrize("command_enabled", ["0", "1"])
def test_disabled_probe_performs_no_host_access(monkeypatch, runtime_enabled, command_enabled) -> None:
    environment = {"FOUNDUPS_AGENT_WSL_COMMAND_PROBE_ENABLED": command_enabled}
    if runtime_enabled is not None:
        environment["FOUNDUPS_AGENT_WSL_RUNTIME_ENABLED"] = runtime_enabled
    monkeypatch.setattr(runtime_module, "_trusted_wsl_path", lambda: pytest.fail("WSL resolved"))
    receipt = probe_wsl_agent_runtime(
        environment=environment,
        runner=lambda *_args: pytest.fail("runner called"),
        base_path_resolver=lambda *_args: pytest.fail("resolver called"),
    )
    assert receipt.state == "DISABLED"
    assert json.dumps(asdict(receipt), sort_keys=True, separators=(",", ":")) == DISABLED_WIRE


def test_probe_is_disabled_by_default() -> None:
    receipt = probe_wsl_agent_runtime(
        environment={},
        runner=lambda *_args: pytest.fail("runner called"),
        base_path_resolver=lambda *_args: pytest.fail("resolver called"),
    )
    assert receipt.state == "DISABLED"
    assert json.dumps(asdict(receipt), sort_keys=True, separators=(",", ":")) == DISABLED_WIRE


@pytest.mark.parametrize("command_enabled", [None, "0", "false", "off", "unknown"])
@pytest.mark.parametrize("injected_runner", [False, True])
def test_metadata_mode_checks_binding_without_command_access(monkeypatch, command_enabled, injected_runner):
    environment = dict(ENV)
    environment.pop("FOUNDUPS_AGENT_WSL_COMMAND_PROBE_ENABLED")
    if command_enabled is not None:
        environment["FOUNDUPS_AGENT_WSL_COMMAND_PROBE_ENABLED"] = command_enabled
    resolutions = []

    def resolver(distro):
        resolutions.append(distro)
        return _base(distro)

    monkeypatch.setattr(runtime_module, "_trusted_wsl_path", lambda: pytest.fail("WSL resolved"))
    receipt = probe_wsl_agent_runtime(
        environment=environment, base_path_resolver=resolver,
        runner=(lambda *_args: pytest.fail("runner called")) if injected_runner else None,
    )
    assert resolutions == ["Ubuntu-24.04"]
    assert receipt.state == "NOT_READY"
    assert receipt.components == ()
    assert receipt.reasons == ("command_probe_disabled",)
    assert receipt.base_path == receipt.expected_base_path == _base("Ubuntu-24.04")
    assert receipt.distro == "Ubuntu-24.04"
    assert receipt.authority_class == "advisory_unverified_runtime_report"


@pytest.mark.parametrize("command_enabled", ["0", "1"])
def test_unregistered_distro_rejects_before_command_access(monkeypatch, command_enabled):
    def resolver(_distro):
        raise ValueError("private registration detail")

    monkeypatch.setattr(runtime_module, "_trusted_wsl_path", lambda: pytest.fail("WSL resolved"))
    receipt = probe_wsl_agent_runtime(
        environment={**ENV, "FOUNDUPS_AGENT_WSL_COMMAND_PROBE_ENABLED": command_enabled},
        base_path_resolver=resolver, runner=lambda *_args: pytest.fail("runner called"),
    )
    assert receipt.state == "NOT_READY"
    assert receipt.components == ()
    assert receipt.reasons == ("distro_not_registered",)
    assert "private registration detail" not in repr(receipt)


@pytest.mark.parametrize("initial,changed", [("0", "1"), ("1", "0")])
def test_command_mode_is_captured_before_resolver_callback(initial, changed):
    environment = {**ENV, "FOUNDUPS_AGENT_WSL_COMMAND_PROBE_ENABLED": initial}
    calls = []

    def resolver(distro):
        environment["FOUNDUPS_AGENT_WSL_COMMAND_PROBE_ENABLED"] = changed
        return _base(distro)

    def runner(command, timeout):
        calls.append((tuple(command), timeout))
        version = "OpenClaw 2026.7.1" if command[-2].endswith("/openclaw") else "Hermes Agent v0.19.1 (2026.7.30)"
        return 0, version

    receipt = probe_wsl_agent_runtime(environment=environment, base_path_resolver=resolver, runner=runner)
    if initial == "0":
        assert calls == []
        assert receipt.state == "NOT_READY"
        assert receipt.components == ()
        assert receipt.reasons == ("command_probe_disabled",)
    else:
        assert receipt.state == "PASS"
        assert calls == [(build_wsl_version_command(name, "Ubuntu-24.04"), 10.0) for name in COMPONENT_EXECUTABLES]


@pytest.mark.parametrize("version", [
    "OpenClaw 2026.7.1 SECRET_SHAPED_VALUE",
    "OpenClaw 2026.7.1-2 SECRET_SHAPED_VALUE",
    "OpenClaw 2026.7.1-SECRET_SHAPED_VALUE",
    "OpenClaw 2026.7.1-2 (SECRET_SHAPED_VALUE)",
])
def test_secret_shaped_suffix_cannot_enter_version_evidence(capsys, version) -> None:
    receipt = run_wsl_agent_runtime_advisory(
        environment=ENV,
        runner=lambda *_args: (0, version),
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
