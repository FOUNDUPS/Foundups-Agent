"""Offline fixed synthetic Broadcast probe contracts."""

import importlib.util
import io
import json
from pathlib import Path
import urllib.error

import pytest


PATH = Path(__file__).resolve().parents[1] / "reddog_openrouter_telemetry_probe.py"
spec = importlib.util.spec_from_file_location("synthetic_broadcast_probe_subject", PATH)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class Response:
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return None
    def read(self, size):
        return self.data[:size]


def setup_probe(monkeypatch, data=None, error=None):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-" + "or-" + "synthetic_test_credential_only")
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append((request, timeout))
            if error:
                raise error
            return Response(data)
    monkeypatch.setattr(subject.urllib.request, "build_opener", lambda handler: Opener())
    return calls


def test_fixed_synthetic_request_and_safe_output(monkeypatch):
    calls = setup_probe(monkeypatch, json.dumps({"model": "vendor/model", "choices": [{"message": {"content": "PRIVATE_RESPONSE"}}],
                                                "usage": {"prompt_tokens": 4, "completion_tokens": 1, "total_tokens": 5},
                                                "metadata": "PRIVATE_METADATA"}).encode())
    result = subject.probe()
    assert result["ok"] is True and result["verified_task_success"] is None
    assert "model" not in result
    assert len(calls) == 1
    request, timeout = calls[0]
    assert request.full_url == "https://openrouter.ai/api/v1/chat/completions"
    body = json.loads(request.data)
    assert body["messages"] == [{"role": "user", "content": "Reply with OK."}]
    assert body["model"] == "openrouter/free" and body["max_tokens"] == 16
    assert body["trace"]["trace_id"] == result["trace_id"]
    assert timeout == 30
    assert "PRIVATE" not in json.dumps(result)


def test_no_credential_blocks_network(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(subject.urllib.request, "build_opener", lambda *args: pytest.fail("no network"))
    assert subject.probe()["status"] == "credential_unavailable"


@pytest.mark.parametrize("data", [b"x" * 65537, b"SECRET_INVALID_JSON", b"[]", b"{}", b'{"error":"SECRET"}'],
                         ids=["oversized", "non-json", "array", "missing-choices", "provider-error"])
def test_invalid_or_oversized_response_never_echoes_content(monkeypatch, data):
    calls = setup_probe(monkeypatch, data)
    result = subject.probe()
    assert result["ok"] is False and "SECRET" not in json.dumps(result)
    assert len(calls) == 1


def test_http_failure_no_retry_body_read_or_raw_error(monkeypatch):
    error = urllib.error.HTTPError("https://secret.example/PRIVATE", 429, "PRIVATE_ERROR", {}, io.BytesIO(b"PRIVATE_BODY"))
    calls = setup_probe(monkeypatch, error=error)
    result = subject.probe()
    assert result["http_status"] == 429 and result["status"] == "http_error"
    assert "PRIVATE" not in json.dumps(result) and len(calls) == 1
    assert error.fp.tell() == 0


def test_redirect_handler_never_returns_redirect_request():
    assert subject._NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example") is None


def test_nonfinite_usage_and_hostile_model_omitted(monkeypatch):
    setup_probe(monkeypatch, json.dumps({"model": "https://PRIVATE.example", "choices": [{"message": {"content": "OK"}}],
                                       "usage": {"prompt_tokens": True, "completion_tokens": float("nan"), "total_tokens": -1}}).encode())
    result = subject.probe()
    assert "model" not in result and set(result["usage"].values()) == {None}


def test_secret_shaped_remote_model_never_emitted(monkeypatch):
    hostile_model = "vendor/" + "sk-" + "or-" + "x" * 24
    setup_probe(monkeypatch, json.dumps({"model": hostile_model,
                                       "choices": [{"message": {"content": "OK"}}]}).encode())
    result = subject.probe()
    assert result["ok"] is True
    assert "model" not in result and hostile_model not in json.dumps(result)
