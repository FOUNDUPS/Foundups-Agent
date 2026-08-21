"""Fail-closed completion-budget tests for RedDog's advisory bridge."""

from __future__ import annotations

import io
import json
import os
from unittest import mock

import pytest

import scripts.advisory_model_once as bridge
from modules.communication.moltbot_bridge.src.fusion_redaction_gate import (
    REDACTION_GATE_PASSED,
    RedactionReport,
)


def _passed_gate():
    return mock.Mock(
        status=REDACTION_GATE_PASSED,
        redacted_prompt="redacted-prompt",
        redacted_context=None,
        reason="ok",
        report=RedactionReport(),
    )


def _invoke(payload: dict[str, object]) -> tuple[int, dict[str, object]]:
    fake_stdin = mock.Mock()
    fake_stdin.buffer = io.BytesIO(json.dumps(payload).encode("utf-8"))
    stdout = io.StringIO()
    lead = str(payload.get("lead_model") or payload.get("model") or "")
    mode = str(payload.get("mode") or "")
    panel = tuple(
        bridge._panel_models(payload.get("panel_models"))
        if mode in {"foundups_fusion", "openrouter_fusion_alias"}
        else ()
    )
    receipt = mock.Mock(
        status=bridge.MODEL_RUNTIME_BINDING_READY,
        accepted=True,
        principal_model=lead,
        panel_models=panel,
        role_bindings=tuple(
            [{"role": "principal", "provider": "openrouter", "model_id": lead}]
            + [{"role": f"critic_{index}", "provider": "openrouter", "model_id": model}
               for index, model in enumerate(panel, 1)]
        ),
        binding_receipt_id="binding:test",
        topology_resolution_receipt_id="verified_model_runtime_topology:test",
        topology_verification_receipt_id="verified_model_runtime_binding:test",
        topology_valid_until=1_900_000_000,
    )
    with mock.patch("sys.stdin", fake_stdin), mock.patch("sys.stdout", stdout), mock.patch.dict(
        os.environ, {bridge.ENV_API_KEY: "test-key"}, clear=False
    ), mock.patch.object(bridge, "query_model_runtime_binding", return_value=receipt):
        rc = bridge.main()
    return rc, json.loads(stdout.getvalue())


@pytest.mark.parametrize("requested", (1, 256, 4096, 8192, 131072))
def test_single_valid_integer_budget_is_preserved_with_truthful_k3_receipt(requested):
    chat = mock.Mock(return_value=("ok", {"retry_count": 0, "final_retry_reason": None}))
    with mock.patch.object(bridge, "evaluate_redaction_gate", return_value=_passed_gate()), mock.patch.object(
        bridge, "_chat_completion", chat
    ):
        rc, result = _invoke(
            {
                "mode": "openrouter_single",
                "prompt": "audit",
                "lead_model": "moonshotai/kimi-k3",
                "max_tokens": requested,
            }
        )
    assert rc == 0 and result["ok"] is True
    assert chat.call_args.kwargs["max_tokens"] == requested
    packet = result["review_packet"]
    assert packet["requested_max_tokens"] == requested
    assert packet["effective_max_tokens"] == max(requested, 4096)


def test_single_missing_budget_keeps_existing_default():
    chat = mock.Mock(return_value=("ok", {"retry_count": 0, "final_retry_reason": None}))
    with mock.patch.object(bridge, "evaluate_redaction_gate", return_value=_passed_gate()), mock.patch.object(
        bridge, "_chat_completion", chat
    ):
        _rc, result = _invoke(
            {
                "mode": "openrouter_single",
                "prompt": "audit",
                "lead_model": "moonshotai/kimi-k3",
            }
        )
    assert chat.call_args.kwargs["max_tokens"] == 2048
    assert result["review_packet"]["requested_max_tokens"] == 2048
    assert result["review_packet"]["effective_max_tokens"] == 4096


@pytest.mark.parametrize("requested", (True, False, "256", None, 0, -1, 131073, 1.5))
@pytest.mark.parametrize("mode", ("openrouter_single", "foundups_fusion"))
def test_invalid_budget_fails_closed_before_any_provider(mode, requested):
    chat = mock.Mock()
    fusion = mock.Mock()
    payload = {
        "mode": mode,
        "prompt": "audit",
        "lead_model": "moonshotai/kimi-k3",
        "panel_models": ["z-ai/glm-5.2"],
        "max_tokens": requested,
    }
    with mock.patch.object(bridge, "evaluate_redaction_gate", return_value=_passed_gate()), mock.patch.object(
        bridge, "_chat_completion", chat
    ), mock.patch.object(bridge, "_run_foundups_fusion", fusion):
        rc, result = _invoke(payload)
    assert rc == 0
    assert result["ok"] is False
    assert result["reason"] == "invalid_max_tokens"
    chat.assert_not_called()
    fusion.assert_not_called()


@pytest.mark.parametrize(("requested", "expected"), ((None, 1600), (256, 256), (8192, 8192)))
def test_fusion_missing_or_valid_budget_reaches_fusion_unchanged(requested, expected):
    fusion = mock.Mock(return_value={"ok": True, "reason": "ok", "review_packet": {}})
    payload = {
        "mode": "foundups_fusion",
        "prompt": "audit",
        "lead_model": "moonshotai/kimi-k3",
        "panel_models": ["z-ai/glm-5.2"],
    }
    if requested is not None:
        payload["max_tokens"] = requested
    with mock.patch.object(bridge, "evaluate_redaction_gate", return_value=_passed_gate()), mock.patch.object(
        bridge, "_run_foundups_fusion", fusion
    ):
        rc, result = _invoke(payload)
    assert rc == 0 and result["ok"] is True
    assert fusion.call_args.args[3]["max_tokens"] == expected


def test_direct_fusion_core_rejects_out_of_range_before_provider():
    chat = mock.Mock()
    with mock.patch.object(bridge, "_chat_completion", chat), pytest.raises(
        ValueError, match="invalid_max_tokens"
    ):
        bridge._run_foundups_fusion_core(
            "key",
            "audit",
            [],
            {"panel_models": ["z-ai/glm-5.2"], "max_tokens": 131073},
        )
    chat.assert_not_called()
