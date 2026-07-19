from __future__ import annotations

import io
import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_BRIDGE_SPEC = importlib.util.spec_from_file_location(
    "reddog_advisory_model_once_progress_test",
    REPO_ROOT / "scripts" / "advisory_model_once.py",
)
if _BRIDGE_SPEC is None or _BRIDGE_SPEC.loader is None:
    raise RuntimeError("advisory_model_once_spec_unavailable")
bridge = importlib.util.module_from_spec(_BRIDGE_SPEC)
sys.modules[_BRIDGE_SPEC.name] = bridge
_BRIDGE_SPEC.loader.exec_module(bridge)
from modules.communication.moltbot_bridge.src.reddog_fusion_progress_receipt import (
    FusionProgressRecorder,
    validate_fusion_progress_receipt,
)


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.headers = {"X-Generation-Id": "gen-123"}

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def _run_main(payload: dict[str, object], *, api_key: str = "") -> dict[str, object]:
    stdin = mock.Mock()
    stdin.buffer = io.BytesIO(json.dumps(payload).encode("utf-8"))
    stdout = io.StringIO()
    stderr = io.StringIO()
    env = {bridge.ENV_API_KEY: api_key} if api_key else {}
    with mock.patch.object(sys, "stdin", stdin), mock.patch.object(sys, "stdout", stdout), mock.patch.object(
        sys, "stderr", stderr
    ), mock.patch.dict(os.environ, env, clear=True):
        bridge.main()
    return json.loads(stdout.getvalue())


def test_openrouter_response_metadata_and_usage_are_retained_without_content() -> None:
    response = {
        "id": "gen-body",
        "model": "served/model",
        "provider": "Provider A",
        "choices": [{"message": {"content": "model output"}}],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "cost": 0.0002,
            "completion_tokens_details": {"reasoning_tokens": 2, "reasoning": "hidden"},
        },
        "openrouter_metadata": {
            "requested": "requested/model",
            "strategy": "direct",
            "summary": "free-form provider data",
            "pipeline": [{"type": "guardrail", "name": "content-filter", "data": {"raw": "hidden"}}],
        },
    }
    seen_request = None

    def fake_urlopen(request, timeout=0):  # noqa: ARG001
        nonlocal seen_request
        seen_request = request
        return _Response(response)

    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        data, meta = bridge._post_openrouter("key", {"model": "requested/model", "messages": []}, 30)

    assert data["choices"][0]["message"]["content"] == "model output"
    assert seen_request.get_header("X-openrouter-metadata") == "enabled"
    assert meta["openrouter_generation_id"] == "gen-123"
    assert meta["openrouter_usage"]["total_tokens"] == 15
    assert meta["openrouter_metadata"]["response_provider"] == "Provider A"
    assert meta["openrouter_metadata"]["response_model"] == "served/model"


def test_chat_completion_creates_valid_content_free_receipt() -> None:
    recorder = FusionProgressRecorder("run-test")
    recorder.emit("lead_start", role="lead", model="requested/model")
    prior = bridge._PROGRESS_RECORDER
    bridge._PROGRESS_RECORDER = recorder
    try:
        with mock.patch.object(
            bridge,
            "_post_openrouter",
            return_value=(
                {"choices": [{"message": {"content": "private response"}}]},
                {
                    "retry_count": 1,
                    "openrouter_generation_id": "gen-1",
                    "openrouter_usage": {
                        "prompt_tokens": 4,
                        "completion_tokens": 3,
                        "total_tokens": 7,
                        "cost": 0.0001,
                    },
                    "openrouter_metadata": {"response_provider": "Provider A", "response_model": "served/model"},
                },
            ),
        ):
            content, _meta = bridge._chat_completion(
                "key",
                "requested/model",
                [{"role": "system", "content": "system"}, {"role": "user", "content": "prompt"}],
                max_tokens=20,
                temperature=0.2,
                timeout=30,
                role="lead",
            )
    finally:
        bridge._PROGRESS_RECORDER = prior

    assert content == "private response"
    receipt = recorder.receipt()
    assert validate_fusion_progress_receipt(receipt) == (True, ())
    serialized = json.dumps(receipt).lower()
    assert "private response" not in serialized
    assert '"messages"' not in serialized
    assert receipt["openrouter_calls"][0]["usage_verified"] is True
    assert receipt["openrouter_calls"][0]["cost_accounting_complete"] is False


def test_missing_key_returns_bound_progress_receipt_without_network() -> None:
    payload = {"bridge_run_id": "run-missing-key", "prompt": "hello", "mode": "openrouter_single"}
    with mock.patch.object(bridge, "_post_openrouter") as post:
        result = _run_main(payload)
    assert result["reason"] == "missing_key"
    assert post.call_count == 0
    receipt = result["fusion_progress_receipt"]
    assert result["fusion_progress_receipt_validation"] == {
        "applied": True,
        "valid": True,
        "rejection_reasons": [],
    }
    assert receipt["run_id"] == "run-missing-key"
    assert [event["stage"] for event in receipt["events"]] == ["bridge_start", "env_check"]
    assert validate_fusion_progress_receipt(receipt) == (True, ())


def test_redaction_block_emits_no_openrouter_call_receipt() -> None:
    payload = {
        "bridge_run_id": "run-blocked",
        "prompt": "private_reasoning hidden plan",
        "mode": "openrouter_single",
        "model": "requested/model",
    }
    with mock.patch.object(bridge, "_post_openrouter") as post:
        result = _run_main(payload, api_key="present-only-in-env")
    assert result["reason"] == "redaction_blocked"
    assert post.call_count == 0
    receipt = result["fusion_progress_receipt"]
    assert receipt["openrouter_call_count"] == 0
    assert receipt["events"][-1]["stage"] == "redaction_blocked"


def test_successful_single_runtime_binds_progress_events_to_call() -> None:
    payload = {
        "bridge_run_id": "run-single-success",
        "prompt": "Summarize the supplied evidence.",
        "mode": "openrouter_single",
        "model": "requested/model",
    }
    response = (
        {"choices": [{"message": {"content": "Model answer"}}]},
        {
            "retry_count": 0,
            "openrouter_generation_id": "gen-1",
            "openrouter_usage": {
                "prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6, "cost": 0.0001,
            },
            "openrouter_metadata": {
                "attempt": 1, "response_provider": "Provider A", "response_model": "served/model",
            },
        },
    )
    with mock.patch.object(bridge, "_post_openrouter", return_value=response):
        result = _run_main(payload, api_key="present-only-in-env")
    assert result["ok"] is True
    assert result["fusion_progress_receipt_validation"]["valid"] is True
    receipt = result["fusion_progress_receipt"]
    assert [event["stage"] for event in receipt["events"]][-2:] == ["single_start", "single_done"]
    assert receipt["openrouter_call_count"] == 1
    assert receipt["openrouter_calls"][0]["cost_accounting_complete"] is True
