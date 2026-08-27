"""Unit contracts for worktree-safe Streamable HTTP launcher routing."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

from modules.infrastructure.foundups_mcp_bridge.scripts import launch
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_bundle_public import (
    project_holo_query_bundle,
)
from modules.infrastructure.foundups_mcp_bridge.src.mcp_server import (
    REMOTE_READ_ONLY_ALLOWLIST,
)


def _readiness():
    names = sorted(REMOTE_READ_ONLY_ALLOWLIST)
    return {
        "verified": True, "transport": "streamable_http", "route": "/mcp",
        "legacy_sse_authoritative": False, "tools_count": len(names),
        "tool_names": names, "latency_ms": 1.0,
    }


def _hostile_child_environment(monkeypatch):
    hostile = {
        "OPENAI_API_KEY", "GITHUB_TOKEN", "AWS_SECRET_ACCESS_KEY",
        "AZURE_CLIENT_SECRET", "GOOGLE_APPLICATION_CREDENTIALS",
        "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT", "LD_PRELOAD",
        "DYLD_INSERT_LIBRARIES",
    }
    for key in hostile:
        monkeypatch.setenv(key, "synthetic-sensitive-value")
    return hostile


def test_freshness_gate_import_does_not_require_optional_mcp_packages():
    repo_root = Path(__file__).resolve().parents[4]
    module_name = "modules.infrastructure.foundups_mcp_bridge.src.bridge_server"
    code = (
        "import sys;"
        f"sys.path.insert(0, {str(repo_root)!r});"
        "import modules.infrastructure.foundups_mcp_bridge.src.holo_query_freshness_gate;"
        f"assert {module_name!r} not in sys.modules;"
        "print('FRESHNESS_IMPORT_OK')"
    )
    env = launch._closed_child_base_env()
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-S", "-B", "-c", code], capture_output=True,
        text=True, timeout=10, check=False, env=env,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "FRESHNESS_IMPORT_OK"


def test_linked_worktree_resolver_prefers_common_main_env(monkeypatch):
    observed = []
    main_fragment = str(Path("O:/Foundups-Agent/foundups-mcp-p1"))

    def capable(candidate):
        observed.append(str(candidate))
        return main_fragment.casefold() in str(candidate).casefold()

    monkeypatch.setattr(launch, "_mcp_python_capable", capable)
    selected = launch._get_mcp_env_python(Path.cwd())
    assert main_fragment.casefold() in str(selected).casefold()
    assert len(observed) == 2


def test_windows_venv_runtime_uses_base_interpreter_and_preserves_pid(tmp_path):
    environment = tmp_path / "mcp-env"
    scripts = environment / "Scripts"
    packages = environment / "Lib" / "site-packages"
    base_executable = Path(
        getattr(sys, "_base_executable", sys.executable)
    ).resolve()
    assert base_executable.is_file()
    scripts.mkdir(parents=True)
    packages.mkdir(parents=True)
    launcher = scripts / "python.exe"
    launcher.write_bytes(b"venv launcher")
    (environment / "pyvenv.cfg").write_text(
        f"home = {base_executable.parent}\n"
        f"executable = {base_executable}\n",
        encoding="utf-8",
    )

    executable, selected_packages = launch._mcp_runtime_python(launcher)
    assert executable == base_executable
    assert selected_packages == packages.resolve()
    child_env = os.environ.copy()
    child_env.pop("PYTHONPATH", None)
    process = subprocess.Popen(
        [str(executable), "-I", "-c", "import os; print(os.getpid())"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=child_env,
    )
    stdout, _stderr = process.communicate(timeout=10)
    assert process.returncode == 0
    assert int(stdout.strip()) == process.pid


def test_readiness_schema_is_exact():
    assert launch._readiness_schema_valid(_readiness()) is True
    for key, value in {
        "route": "/sse", "transport": "sse", "verified": False,
        "tools_count": 99, "latency_ms": float("nan"),
    }.items():
        forged = {**_readiness(), key: value}
        assert launch._readiness_schema_valid(forged) is False


def test_direct_canary_rejects_injected_extra_tool():
    assert launch._remote_tool_names_exact({"holo_query_bundle"}) is True
    assert launch._remote_tool_names_exact({
        "holo_query_bundle", "injected_extra_tool",
    }) is False


def test_lexical_canary_requires_complete_inner_receipt(tmp_path):
    inner = project_holo_query_bundle({
        "ok": True, "owner_attempts": 0,
        "no_holoindex_reindex_performed": True,
    }, tmp_path)
    assert launch._mcp_bundle_response_ok({"status": "ok", "data": inner})
    for changed in (
        {"ok": False}, {"owner_attempts": 1},
        {"no_holoindex_reindex_performed": False},
    ):
        rejected = project_holo_query_bundle({**inner, **changed}, tmp_path)
        assert not launch._mcp_bundle_response_ok({"status": "ok", "data": rejected})
    for changed in (
        {"public_projection_bounded": False},
        {"public_projection_bytes": inner["public_projection_bytes"] + 1},
    ):
        assert not launch._mcp_bundle_response_ok({
            "status": "ok", "data": {**inner, **changed},
        })


def test_readiness_subprocess_rejects_forged_nonzero_exit(monkeypatch, tmp_path):
    interpreter = tmp_path / "python.exe"
    interpreter.write_bytes(b"test")
    monkeypatch.setattr(launch, "_get_mcp_env_python", lambda _root: interpreter)
    monkeypatch.setattr(launch, "_mcp_python_capable", lambda _path: True)
    result = subprocess.CompletedProcess(
        [], 3, stdout=json.dumps(_readiness()), stderr="",
    )
    monkeypatch.setattr(launch.subprocess, "run", lambda *_args, **_kwargs: result)
    observed = launch._verify_readiness_subprocess(
        tmp_path, "127.0.0.1", 8128, "", 2.0,
    )
    assert observed == {"verified": False, "error": "mcp_readiness_process_failed"}


def test_server_child_environment_is_closed(monkeypatch, tmp_path):
    hostile = _hostile_child_environment(monkeypatch)
    interpreter = tmp_path / "python.exe"
    interpreter.write_bytes(b"test")
    monkeypatch.setattr(launch, "_get_mcp_env_python", lambda _root: interpreter)
    monkeypatch.setattr(launch, "_mcp_python_capable", lambda _path: True)
    monkeypatch.setattr(launch, "_mcp_runtime_python", lambda path: (path, None))
    options = launch.MCPLaunchOptions(
        tmp_path, "127.0.0.1", 8128, "synthetic-local-token", True,
    )
    _command, env, error = launch._http_subprocess_spec(options)
    assert error is None and env is not None
    assert hostile.isdisjoint(env)
    assert env["PYTHONPATH"] == str(tmp_path)
    assert env["FOUNDUPS_MCP_AUTH_TOKEN"] == "synthetic-local-token"


def test_capability_probe_environment_is_closed(monkeypatch, tmp_path):
    hostile = _hostile_child_environment(monkeypatch)
    interpreter = tmp_path / "python.exe"
    interpreter.write_bytes(b"test")
    captured = {}

    def run(*_args, **kwargs):
        captured.update(kwargs["env"])
        return subprocess.CompletedProcess(
            [], 0,
            stdout=json.dumps(launch.MCP_RUNTIME_VERSIONS, sort_keys=True,
                              separators=(",", ":")) + "\n",
            stderr="",
        )

    monkeypatch.setattr(launch.subprocess, "run", run)
    assert launch._mcp_python_capable(interpreter) is True
    assert hostile.isdisjoint(captured)


def test_capability_probe_rejects_dependency_version_drift(monkeypatch, tmp_path):
    interpreter = tmp_path / "python.exe"
    interpreter.write_bytes(b"test")
    drift = dict(launch.MCP_RUNTIME_VERSIONS, fastmcp="3.2.0")
    monkeypatch.setattr(
        launch.subprocess, "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            [], 0, stdout=json.dumps(drift, sort_keys=True,
                                     separators=(",", ":")) + "\n", stderr="",
        ),
    )
    assert launch._mcp_python_capable(interpreter) is False


def test_runtime_version_contract_matches_requirements():
    requirements = Path(__file__).resolve().parents[1] / "requirements.txt"
    declarations = [
        line.strip() for line in requirements.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    expected = [f"{name}=={version}" for name, version in launch.MCP_RUNTIME_VERSIONS.items()]
    names = [line.split("==", 1)[0] for line in declarations]
    assert len(declarations) == 4
    assert len(set(names)) == 4
    assert sorted(declarations) == sorted(expected)


def test_readiness_child_environment_is_closed(monkeypatch, tmp_path):
    hostile = _hostile_child_environment(monkeypatch)
    interpreter = tmp_path / "python.exe"
    interpreter.write_bytes(b"test")
    captured = {}
    monkeypatch.setattr(launch, "_get_mcp_env_python", lambda _root: interpreter)
    monkeypatch.setattr(launch, "_mcp_python_capable", lambda _path: True)
    monkeypatch.setattr(launch, "_mcp_runtime_python", lambda path: (path, None))

    def run(*_args, **kwargs):
        captured.update(kwargs["env"])
        return subprocess.CompletedProcess([], 0, stdout=json.dumps(_readiness()), stderr="")

    monkeypatch.setattr(launch.subprocess, "run", run)
    observed = launch._verify_readiness_subprocess(
        tmp_path, "127.0.0.1", 8128, "synthetic-local-token", 2.0,
    )
    assert observed["verified"] is True
    assert hostile.isdisjoint(captured)
    assert captured["FOUNDUPS_MCP_AUTH_TOKEN"] == "synthetic-local-token"


def test_crashed_runtime_is_reaped_before_restart(monkeypatch, tmp_path):
    old_lock = MagicMock()
    dead_proc = MagicMock()
    dead_proc.poll.return_value = 7
    dead = launch.MCPRuntimeHandle(
        mode="subprocess", host="127.0.0.1", port=8128,
        started_at=0.0, lock=old_lock, proc=dead_proc,
    )
    new_lock = MagicMock()
    observed = {}
    monkeypatch.setattr(launch, "_active_runtime", dead)
    monkeypatch.setattr(launch, "_acquire_http_lock", lambda: (new_lock, None))

    def start(options, lock, blocking):
        observed.update(options=options, lock=lock, blocking=blocking)
        return {"status": "running"}

    monkeypatch.setattr(launch, "_launch_http_subprocess", start)
    result = launch.run_mcp_bridge_http(repo_root=tmp_path, blocking=False)
    assert result == {"status": "running"}
    old_lock.release.assert_called_once_with()
    assert dead.lock is None and observed["lock"] is new_lock
    assert observed["blocking"] is False


def test_launcher_rejects_non_loopback_and_missing_dev_token(tmp_path):
    assert launch.run_mcp_bridge_http(
        host="0.0.0.0", repo_root=tmp_path, blocking=False,
    )["error"] == "loopback_binding_required"
    assert launch.run_mcp_bridge_http(
        host="127.0.0.1", auth_token="", require_auth=True,
        repo_root=tmp_path, blocking=False,
    )["error"] == "auth_token_required_for_remote_exposure"
