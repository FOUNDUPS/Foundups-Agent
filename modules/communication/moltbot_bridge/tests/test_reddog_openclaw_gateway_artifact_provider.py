"""Fail-closed tests for the real OpenClaw Gateway CLI adapter."""
from __future__ import annotations
import ast, json, sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from modules.communication.moltbot_bridge.src.fusion_redaction_gate import REDACTION_GATE_PASSED
from modules.communication.moltbot_bridge.src.reddog_openclaw_gateway_artifact_provider import (
    FAIL_GATEWAY, OpenClawGatewayArtifactGenerationRunner,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_gateway_command_runner import (
    OpenClawCommandResult, SystemOpenClawCommandRunner,
)
from modules.communication.moltbot_bridge.src import reddog_openclaw_gateway_command_runner as command_module


class FakeRunner:
    def __init__(self, invocation=None, *, status=None, sandbox=None):
        self.calls, self.message = [], ""
        self.invocation = invocation or _agent_result()
        self.status = status or _status()
        self.sandbox = sandbox

    def run(self, argv, *, timeout_seconds):
        args = tuple(argv)
        self.calls.append((args, timeout_seconds))
        if args[1:] == ("--version",):
            return _command_result("OpenClaw 2026.7.1 (abc)\n")
        if args[1:3] == ("gateway", "status"):
            return _command_result(json.dumps(self.status))
        if args[1:3] == ("agents", "list"):
            return _command_result('[{"id":"reddog-artifact"}]')
        if args[1:3] == ("sandbox", "explain"):
            value = dict(self.sandbox or _sandbox(args[-2]))
            value["sessionKey"] = args[-2]
            return _command_result(json.dumps(value))
        path = Path(args[args.index("--message-file") + 1])
        self.message = path.read_text(encoding="utf-8")
        return self.invocation


class RaisingInvocationRunner(FakeRunner):
    def run(self, argv, *, timeout_seconds):
        if tuple(argv)[1:2] == ("agent",):
            raise RuntimeError("provider_transport_failed")
        return super().run(argv, timeout_seconds=timeout_seconds)


def _command_result(stdout="", *, code=0, **changes):
    return OpenClawCommandResult(code, stdout, process_started=True, **changes)


def _status():
    return {"cli": {"version": "2026.7.1"}, "config": {"cli": {"exists": True, "valid": True}},
            "gateway": {"bindMode": "loopback"},
            "rpc": {"ok": True, "server": {"version": "2026.7.1"}}}


def _sandbox(session_key, **changes):
    value = {"agentId": "reddog-artifact", "sessionKey": session_key,
             "sandbox": {"mode": "all", "sessionIsSandboxed": True,
                         "workspaceAccess": "none", "workspaceSource": "sandbox",
                         "runtimeWorkdir": "/workspace",
                         "workspaceMounts": [{"hostRoot": "/home/user/.openclaw/sandboxes/agent-reddog-artifact-test",
                                              "containerRoot": "/workspace", "writable": False,
                                              "source": "workspace"}],
                         "tools": {"allow": [], "deny": ["*"]}},
             "elevated": {"enabled": False}}
    value.update(changes)
    return value


def _agent_result(text=None, *, status="ok", **changes):
    content = text or '{"artifact_contents":{"src/example.py":"ok"}}'
    value = {"status": status, "runId": "run-1", "result": {"payloads": [{"text": content}]}}
    value.update(changes)
    return _command_result(json.dumps(value))


def _provider(tmp_path, runner, *, agent_id="reddog-artifact"):
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    return OpenClawGatewayArtifactGenerationRunner(repo, tmp_path / "runtime", agent_id, runner)


def _generate(provider, *, prompt="secret prompt", context="private context", model="qwen/qwen3-coder"):
    verified = {"model_selection": {"receipt_id": "selection-1", "lead_model": model}}
    with patch("modules.communication.moltbot_bridge.src.reddog_openclaw_gateway_artifact_provider.consume_artifact_generation_model", return_value=verified):
        return provider.generate_artifacts(prompt=prompt, context=context, binding=object(), timeout_seconds=17)


def test_real_gateway_cli_path_is_exact_session_sandboxed_and_truthful(tmp_path):
    runner = FakeRunner()
    result = _generate(_provider(tmp_path, runner))
    assert result.ok and result.artifact_contents == {"src/example.py": "ok"}
    assert result.worker_process_spawn_count == 5
    assert result.file_write_performed is True
    assert result.external_side_effects_possible is True
    assert runner.calls[1][0] == (
        "openclaw", "gateway", "status", "--require-rpc", "--json"
    )
    preflight, invocation = runner.calls[-2][0], runner.calls[-1][0]
    session = invocation[invocation.index("--session-key") + 1]
    assert preflight[-3:] == ("--session", session, "--json")
    assert invocation[invocation.index("--agent") + 1] == "reddog-artifact"
    assert "--local" not in invocation and runner.calls[-1][1] == 47
    assert list((tmp_path / "runtime").glob("reddog-openclaw-*.md")) == []


def test_sessions_are_unique_and_prompt_is_never_argv(tmp_path):
    runner = FakeRunner()
    provider = _provider(tmp_path, runner)
    _generate(provider, prompt="PROMPT_SECRET", context="CONTEXT_SECRET")
    first = runner.calls[-1][0]
    first_message = runner.message
    _generate(provider)
    second = runner.calls[-1][0]
    assert first[first.index("--session-key") + 1] != second[second.index("--session-key") + 1]
    assert "PROMPT_SECRET" not in " ".join(first)
    assert "CONTEXT_SECRET" not in " ".join(first)
    assert "PROMPT_SECRET" in first_message and "CONTEXT_SECRET" in first_message


@pytest.mark.parametrize("sandbox", [
    _sandbox("x", elevated={"enabled": True}),
    _sandbox("x", sandbox={"mode": "all", "sessionIsSandboxed": True, "workspaceAccess": "none", "workspaceSource": "sandbox", "runtimeWorkdir": "/workspace", "workspaceMounts": [{"hostRoot": "/repo", "containerRoot": "/workspace", "writable": False, "source": "workspace"}], "tools": {"allow": [], "deny": ["*"]}}),
    _sandbox("x", sandbox={"mode": "all", "sessionIsSandboxed": True, "workspaceAccess": "none", "workspaceSource": "sandbox", "runtimeWorkdir": "/workspace", "workspaceMounts": [{"hostRoot": "/home/user/.openclaw/sandboxes/agent-reddog-artifact-test", "containerRoot": "/workspace", "writable": False, "source": "workspace"}], "tools": {"allow": ["read"], "deny": ["*"]}}),
    _sandbox("x", sandbox={"mode": "all", "sessionIsSandboxed": True, "workspaceAccess": "none", "workspaceSource": "sandbox", "runtimeWorkdir": "/workspace", "workspaceMounts": [{"hostRoot": "/home/user/.openclaw/sandboxes/agent-reddog-artifact-test", "containerRoot": "/workspace", "writable": False, "source": "workspace"}], "tools": {"allow": [], "deny": ["exec", "write"]}}),
])
def test_sandbox_requires_closed_tool_policy(tmp_path, sandbox):
    runner = FakeRunner(sandbox=sandbox)
    assert _generate(_provider(tmp_path, runner)).rejection_reasons == (FAIL_GATEWAY,)
    assert len(runner.calls) == 4


@pytest.mark.parametrize("result", [
    _command_result(code=124, timed_out=True, termination_confirmed=True),
    _command_result(code=125, output_limit_exceeded=True),
    _command_result(code=124, termination_confirmed=False),
])
def test_indeterminate_invocation_never_reports_a_clean_abort(tmp_path, result):
    outcome = _generate(_provider(tmp_path, FakeRunner(result)))
    assert outcome.ok is False
    assert outcome.rejection_reasons == ("FAIL_OPENCLAW_AGENT_INDETERMINATE",)
    assert outcome.run_abort_confirmed is False
    assert outcome.effect_observation_complete is False


def test_uncaught_invocation_failure_never_reports_a_clean_abort(tmp_path):
    outcome = _generate(_provider(tmp_path, RaisingInvocationRunner()))
    assert outcome.rejection_reasons == ("FAIL_OPENCLAW_AGENT_REJECTED",)
    assert outcome.effect_observation_complete is False
    assert outcome.run_abort_confirmed is False


@pytest.mark.parametrize("text", [
    "not-json", "{}", '{"artifact_contents":{}}',
    '{"artifact_contents":{"x":1}}',
    '{"artifact_contents":{"x":"one"},"artifact_contents":{"x":"two"}}',
    '{"artifact_contents":{"x":"one","x":"two"}}',
])
def test_malformed_or_duplicate_output_rejects(tmp_path, text):
    outcome = _generate(_provider(tmp_path, FakeRunner(_agent_result(text))))
    assert outcome.rejection_reasons == ("FAIL_OPENCLAW_ARTIFACT_OUTPUT",)


def test_invalid_binding_precedes_all_openclaw_processes(tmp_path):
    runner = FakeRunner()
    assert _generate(_provider(tmp_path, runner), model="--local").rejection_reasons == (
        "FAIL_OPENCLAW_MODEL_BINDING",
    )
    assert runner.calls == []


def test_redaction_block_precedes_binding_file_and_process(tmp_path):
    runner = FakeRunner()
    blocked = SimpleNamespace(status="BLOCKED_LOCALLY", redacted_prompt=None, redacted_context=None)
    with patch("modules.communication.moltbot_bridge.src.reddog_openclaw_gateway_artifact_provider.evaluate_redaction_gate", return_value=blocked), patch("modules.communication.moltbot_bridge.src.reddog_openclaw_gateway_artifact_provider.consume_artifact_generation_model") as consume:
        result = _provider(tmp_path, runner).generate_artifacts(prompt="p", context="c", binding=object(), timeout_seconds=5)
    assert result.rejection_reasons == ("FAIL_OPENCLAW_REDACTION_BLOCKED",)
    assert runner.calls == [] and consume.call_count == 0


def test_system_transport_uses_trusted_wsl_and_rejects_other_commands(tmp_path, monkeypatch):
    trusted = tmp_path / "wsl.exe"
    trusted.write_bytes(b"")
    monkeypatch.setattr(command_module, "resolve_trusted_wsl_executable", lambda: trusted)
    runner = SystemOpenClawCommandRunner(distro="Ubuntu-24.04")
    command = runner._command(("openclaw", "agent", "--message-file", "E:/Agents/task.md"))
    assert command[:5] == [str(trusted), "--distribution", "Ubuntu-24.04", "--exec", "/usr/local/bin/openclaw"]
    assert command[-1] == "/mnt/e/Agents/task.md"
    assert runner._command(("powershell", "-c", "unsafe")) == []


def test_system_transport_bounds_output_and_confirms_process_termination(monkeypatch):
    monkeypatch.setattr(
        SystemOpenClawCommandRunner, "_command",
        lambda _self, _argv: [sys.executable, "-c", "print('x' * 10000)"],
    )
    result = SystemOpenClawCommandRunner(max_output_bytes=128).run(
        ("openclaw", "--version"), timeout_seconds=5,
    )
    assert result.process_started is True
    assert result.output_limit_exceeded is True
    assert result.termination_confirmed is True


def test_system_transport_bounds_time_and_confirms_process_termination(monkeypatch):
    monkeypatch.setattr(
        SystemOpenClawCommandRunner, "_command",
        lambda _self, _argv: [sys.executable, "-c", "import time; time.sleep(10)"],
    )
    result = SystemOpenClawCommandRunner().run(
        ("openclaw", "--version"), timeout_seconds=1,
    )
    assert result.timed_out is True
    assert result.termination_confirmed is True


def test_provider_has_no_local_or_shell_invocation():
    source = Path("modules/communication/moltbot_bridge/src/reddog_openclaw_gateway_artifact_provider.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert '"--local"' not in source and "'--local'" not in source
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr in {"Popen", "system", "popen"} for node in ast.walk(tree))
