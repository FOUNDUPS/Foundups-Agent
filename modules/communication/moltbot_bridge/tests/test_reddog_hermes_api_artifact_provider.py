"""Adversarial contract tests for the real upstream Hermes API provider."""

from __future__ import annotations

import ast
import os
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from modules.communication.moltbot_bridge.src.fusion_redaction_gate import REDACTION_GATE_PASSED
from modules.communication.moltbot_bridge.src.reddog_hermes_api_artifact_provider import (
    HermesApiArtifactGenerationRunner,
)
from modules.communication.moltbot_bridge.src.reddog_hermes_api_confinement import (
    HERMES_ARTIFACT_PROFILE,
    HERMES_EXPECTED_API_VERSION,
)
from modules.communication.moltbot_bridge.src.reddog_hermes_api_transport import HermesApiResponse
from modules.communication.moltbot_bridge.src.reddog_hermes_api_transport import (
    RuntimeHermesApiKeyProvider,
    SystemHermesApiTransport,
)


class FakeKeyProvider:
    def __init__(self, value="k" * 48):
        self.value = value

    def read_key(self):
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


class FakeTransport:
    def __init__(self, *, status=None, toolsets=None, skills=None, capabilities=None, events=None):
        self.calls = []
        self.statuses = list(status or [_completed()])
        self.toolsets = toolsets or _toolsets()
        self.skills = skills or {"object": "list", "data": []}
        self.capabilities = capabilities or _capabilities()
        self.events = list(events) if events is not None else [_event_for_status(self.statuses[-1])]

    def request(self, method, path, *, headers, payload, timeout_seconds):
        self.calls.append((method, path, dict(headers), payload, timeout_seconds))
        if path == "/v1/capabilities" and not headers:
            return HermesApiResponse(401, '{}')
        if path == "/v1/capabilities":
            return _response(self.capabilities)
        if path == "/health/detailed":
            return _response(_health())
        if path == "/v1/toolsets":
            return _response(self.toolsets)
        if path == "/v1/skills":
            return _response(self.skills)
        if path == "/v1/runs":
            return HermesApiResponse(202, '{"run_id":"run-1","status":"started"}')
        if path.endswith("/stop"):
            self.statuses = [{"object": "hermes.run", "run_id": "run-1", "status": "cancelled"}]
            return HermesApiResponse(202, '{"status":"stopping"}')
        if path.endswith("/events"):
            return HermesApiResponse(200, _event_stream(self.events))
        return _response(self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0])


class PostflightDriftTransport(FakeTransport):
    def __init__(self):
        super().__init__()
        self.toolset_reads = 0

    def request(self, method, path, *, headers, payload, timeout_seconds):
        if path == "/v1/toolsets":
            self.toolset_reads += 1
            if self.toolset_reads > 1:
                return _response(_toolsets(enabled=True))
        return super().request(
            method, path, headers=headers, payload=payload, timeout_seconds=timeout_seconds
        )


def _response(value):
    return HermesApiResponse(200, json.dumps(value))


def _capabilities():
    features = {
        "run_submission": True, "run_status": True, "run_events_sse": True,
        "run_stop": True,
        "run_approval_response": True, "tool_progress_events": True,
        "approval_events": True,
    }
    endpoints = {
        "runs": {"method": "POST", "path": "/v1/runs"},
        "run_status": {"method": "GET", "path": "/v1/runs/{run_id}"},
        "run_events": {"method": "GET", "path": "/v1/runs/{run_id}/events"},
        "run_stop": {"method": "POST", "path": "/v1/runs/{run_id}/stop"},
        "skills": {"method": "GET", "path": "/v1/skills"},
        "toolsets": {"method": "GET", "path": "/v1/toolsets"},
    }
    return {
        "object": "hermes.api_server.capabilities", "platform": "hermes-agent",
        "model": HERMES_ARTIFACT_PROFILE, "auth": {"type": "bearer", "required": True},
        "runtime": {"mode": "server_agent", "tool_execution": "server", "split_runtime": False},
        "features": features, "endpoints": endpoints,
    }


def _health():
    return {
        "status": "ok",
        "platform": "hermes-agent",
        "version": HERMES_EXPECTED_API_VERSION,
    }


def _toolsets(*, enabled=False):
    return {"object": "list", "platform": "api_server", "data": [
        {"name": "terminal", "enabled": enabled, "configured": True, "tools": ["terminal"]}
    ]}


def _completed(output='{"artifact_contents":{"src/example.py":"ok"}}', **changes):
    value = {"object": "hermes.run", "run_id": "run-1", "status": "completed", "output": output}
    value.update(changes)
    return value


def _completed_event(output='{"artifact_contents":{"src/example.py":"ok"}}'):
    return {"event": "run.completed", "run_id": "run-1", "output": output}


def _event_for_status(status):
    state = str(status.get("status") or "")
    event = {"event": "run." + state, "run_id": str(status.get("run_id") or "run-1")}
    if state == "completed":
        event["output"] = status.get("output")
    return event


def _event_stream(events):
    return "".join("data: " + json.dumps(event) + "\n\n" for event in events) + ": stream closed\n\n"


def _binding(model="qwen/qwen3-coder", provider="openrouter"):
    return {"model_selection": {"lead_model": model, "role_assignments": [
        {"role": "principal", "canonical_model_id": model, "provider": provider}
    ]}}


def _generate(transport, *, binding=None, key_provider=None, **kwargs):
    runner = HermesApiArtifactGenerationRunner(
        transport, key_provider or FakeKeyProvider(), sleeper=lambda _value: None
    )
    verified = _binding() if binding is None else binding
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_hermes_api_artifact_provider.consume_artifact_generation_model",
        return_value=verified,
    ):
        return runner.generate_artifacts(
            prompt=kwargs.get("prompt", "implement bounded artifact"),
            context=kwargs.get("context", "governed context"),
            binding=object(), timeout_seconds=kwargs.get("timeout", 5),
        )


def test_real_hermes_api_route_is_signed_text_only_and_truthful():
    transport = FakeTransport()
    result = _generate(transport)
    assert result.ok and result.artifact_contents == {"src/example.py": "ok"}
    assert result.provider_runtime == "hermes_api" and result.hermes_dispatch_performed
    assert result.worker_process_started is False and result.file_write_performed is False
    submit = next(call for call in transport.calls if call[1] == "/v1/runs")
    assert submit[3]["model"] == "qwen/qwen3-coder"
    assert submit[3]["provider"] == "openrouter"
    assert "Authorization" in submit[2] and "X-Hermes-Session-Key" in submit[2]


@pytest.mark.parametrize("binding", [
    {},
    {"model_selection": {"lead_model": "x", "role_assignments": []}},
    {"model_selection": {"lead_model": "x", "role_assignments": [
        {"role": "principal", "canonical_model_id": "y", "provider": "openrouter"}
    ]}},
    {"model_selection": {"lead_model": "--unsafe", "role_assignments": [
        {"role": "principal", "canonical_model_id": "--unsafe", "provider": "openrouter"}
    ]}},
])
def test_invalid_signed_route_precedes_secret_and_network(binding):
    transport = FakeTransport()
    key = FakeKeyProvider(RuntimeError("must-not-read"))
    result = _generate(transport, binding=binding, key_provider=key)
    assert result.rejection_reasons == ("FAIL_HERMES_MODEL_BINDING",)
    assert transport.calls == []


def test_redaction_precedes_model_capability_secret_and_network():
    transport = FakeTransport()
    blocked = SimpleNamespace(status="BLOCKED_LOCALLY", redacted_prompt=None, redacted_context=None)
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_hermes_api_artifact_provider.evaluate_redaction_gate",
        return_value=blocked,
    ), patch(
        "modules.communication.moltbot_bridge.src.reddog_hermes_api_artifact_provider.consume_artifact_generation_model"
    ) as consume:
        runner = HermesApiArtifactGenerationRunner(transport, FakeKeyProvider())
        result = runner.generate_artifacts(prompt="p", context="c", binding=object(), timeout_seconds=5)
    assert result.rejection_reasons == ("FAIL_HERMES_REDACTION_BLOCKED",)
    assert consume.call_count == 0 and transport.calls == []


@pytest.mark.parametrize("changes,reason", [
    ({"capabilities": {"object": "bad"}}, "FAIL_HERMES_CAPABILITY_CONFINEMENT"),
    ({"toolsets": _toolsets(enabled=True)}, "FAIL_HERMES_TOOLSET_CONFINEMENT"),
    ({"skills": {"object": "list", "data": [{"name": "shell"}]}}, "FAIL_HERMES_SKILL_CONFINEMENT"),
])
def test_preflight_rejects_unconfined_upstream_surface(changes, reason):
    result = _generate(FakeTransport(**changes))
    assert result.rejection_reasons == (reason,)
    assert result.provider_invocation_performed is False
    assert result.made_network_call is True


def test_tool_or_approval_activity_is_stopped_and_rejected():
    transport = FakeTransport(status=[{"status": "waiting_for_approval", "last_event": "approval.request"}])
    result = _generate(transport)
    assert result.rejection_reasons == ("FAIL_HERMES_TOOL_ACTIVITY",)
    assert result.run_abort_confirmed is True
    assert any(path.endswith("/stop") for _, path, *_ in transport.calls)


def test_toolset_drift_after_run_rejects_completed_output():
    result = _generate(PostflightDriftTransport())
    assert result.rejection_reasons == ("FAIL_HERMES_POSTFLIGHT_CONFINEMENT",)
    assert result.ok is False


@pytest.mark.parametrize("event", [
    {"event": "tool.completed", "run_id": "run-1"},
    {"event": "subagent.complete", "run_id": "run-1"},
    {"event": "approval.request", "run_id": "run-1"},
])
def test_completed_status_cannot_hide_earlier_effect_event(event):
    transport = FakeTransport(events=[event, _completed_event()])
    result = _generate(transport)
    assert result.rejection_reasons == ("FAIL_HERMES_EVENT_CONFINEMENT",)
    assert result.effect_observation_complete is False
    assert result.run_abort_confirmed is False


def test_event_log_must_match_terminal_status_output_and_run_id():
    wrong_output = FakeTransport(events=[_completed_event("different")])
    assert _generate(wrong_output).rejection_reasons == ("FAIL_HERMES_EVENT_CONFINEMENT",)
    wrong_run = FakeTransport(events=[{
        "event": "run.completed", "run_id": "run-other",
        "output": '{"artifact_contents":{"src/example.py":"ok"}}',
    }])
    assert _generate(wrong_run).rejection_reasons == ("FAIL_HERMES_EVENT_CONFINEMENT",)


def test_attacker_run_id_cannot_become_a_request_path():
    class BadRunId(FakeTransport):
        def request(self, method, path, *, headers, payload, timeout_seconds):
            if path == "/v1/runs":
                return HermesApiResponse(202, '{"run_id":"../admin","status":"started"}')
            return super().request(
                method, path, headers=headers, payload=payload, timeout_seconds=timeout_seconds
            )

    transport = BadRunId()
    result = _generate(transport)
    assert result.rejection_reasons == ("FAIL_HERMES_RUN_SUBMISSION",)
    assert not any("../admin" in path for _, path, *_ in transport.calls)
    assert result.effect_observation_complete is False


@pytest.mark.parametrize("output", [
    "not-json", "{}", '{"artifact_contents":{}}',
    '{"artifact_contents":{"../escape.py":"bad"}}',
    '{"artifact_contents":{"x.py":"one"},"artifact_contents":{"x.py":"two"}}',
])
def test_malformed_duplicate_or_unsafe_artifacts_reject(output):
    result = _generate(FakeTransport(status=[_completed(output)]))
    assert result.rejection_reasons == ("FAIL_HERMES_ARTIFACT_OUTPUT",)


def test_secret_never_appears_in_result_or_receipt_fields():
    secret = "super-private-hermes-api-key-value-1234567890"
    result = _generate(FakeTransport(), key_provider=FakeKeyProvider(secret))
    assert secret not in repr(result) and secret not in json.dumps(result.to_dict())


def test_runtime_key_provider_reads_only_confined_bounded_secret(tmp_path):
    repo, runtime = tmp_path / "repo", tmp_path / "runtime"
    repo.mkdir(); (runtime / "hermes-api").mkdir(parents=True)
    key_path = runtime / "hermes-api" / "api-key"
    key_path.write_text("k" * 48, encoding="utf-8")
    if os.name != "nt":
        key_path.chmod(0o600)
    provider = RuntimeHermesApiKeyProvider(runtime, repo)
    assert provider.read_key() == "k" * 48
    key_path.write_text("short", encoding="utf-8")
    with pytest.raises(ValueError, match="hermes_api_key_invalid"):
        provider.read_key()


def test_system_transport_is_fixed_loopback_and_rejects_unsafe_paths(monkeypatch):
    captured = {}

    class Response:
        status = 200
        def getheader(self, _name): return "2"
        def read(self, _size): return b"{}"

    class Connection:
        def __init__(self, host, port, timeout):
            captured.update(host=host, port=port, timeout=timeout)
        def request(self, method, path, body=None, headers=None):
            captured.update(method=method, path=path, body=body, headers=headers)
        def getresponse(self): return Response()
        def close(self): captured["closed"] = True

    monkeypatch.setattr(
        "modules.communication.moltbot_bridge.src.reddog_hermes_api_transport.http.client.HTTPConnection",
        Connection,
    )
    transport = SystemHermesApiTransport()
    response = transport.request("GET", "/health", headers={}, payload=None, timeout_seconds=3)
    assert response.status == 200
    assert captured["host"] == "127.0.0.1" and captured["port"] == 8642
    assert captured["closed"] is True
    assert transport.request("GET", "//attacker", headers={}, payload=None, timeout_seconds=3).status == 0


def test_provider_has_no_shell_subprocess_or_repository_write():
    paths = [
        Path("modules/communication/moltbot_bridge/src/reddog_hermes_api_artifact_provider.py"),
        Path("modules/communication/moltbot_bridge/src/reddog_hermes_api_run_lifecycle.py"),
    ]
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
        assert not imports.intersection({"subprocess", "os", "shutil"})
        assert not any(
            isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"write_text", "write_bytes", "mkdir", "Popen", "system"}
            for node in ast.walk(tree)
        )
