from unittest.mock import patch

import main


def test_ironclaw_preflight_skips_when_backend_is_openclaw(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("OPENCLAW_IRONCLAW_PREFLIGHT", "1")
    monkeypatch.setenv("OPENCLAW_CONVERSATION_BACKEND", "openclaw")
    monkeypatch.delenv("OPENCLAW_IRONCLAW_PREFLIGHT_ALWAYS", raising=False)

    ok = main.run_ironclaw_runtime_preflight(tmp_path)

    assert ok is True
    captured = capsys.readouterr().out
    assert "[IRONCLAW] preflight=SKIP backend=openclaw" in captured


def test_ironclaw_preflight_passes_when_runtime_or_fallback_is_ready(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("OPENCLAW_CONVERSATION_BACKEND", "ironclaw")
    monkeypatch.setenv("OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK", "0")

    with patch(
        "modules.communication.moltbot_bridge.src.ironclaw_gateway_client.IronClawGatewayClient.startup_probe",
        return_value={
            "ok": True,
            "detail": "ironclaw_healthy: healthy via /v1/models",
            "backend": "ironclaw",
        },
    ):
        ok = main.run_ironclaw_runtime_preflight(tmp_path)

    assert ok is True
    captured = capsys.readouterr().out
    assert "[IRONCLAW] preflight=PASS backend=ironclaw resolved=ironclaw" in captured


def test_ironclaw_preflight_blocks_when_backend_requires_ironclaw_and_probe_fails(
    monkeypatch, capsys, tmp_path
):
    monkeypatch.setenv("OPENCLAW_CONVERSATION_BACKEND", "ironclaw")
    monkeypatch.setenv("OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK", "0")
    monkeypatch.delenv("OPENCLAW_IRONCLAW_PREFLIGHT_ENFORCED", raising=False)

    with patch(
        "modules.communication.moltbot_bridge.src.ironclaw_gateway_client.IronClawGatewayClient.startup_probe",
        return_value={
            "ok": False,
            "detail": "ironclaw_down, lm_studio_unavailable",
            "backend": None,
            "remediation": ["Run: ironclaw gateway"],
        },
    ):
        ok = main.run_ironclaw_runtime_preflight(tmp_path)

    assert ok is False
    captured = capsys.readouterr().out
    assert "[IRONCLAW] preflight=FAIL backend=ironclaw resolved=none" in captured
    assert "Startup blocked" in captured


def test_ironclaw_preflight_warns_but_allows_when_fallback_policy_is_enabled(
    monkeypatch, capsys, tmp_path
):
    monkeypatch.setenv("OPENCLAW_CONVERSATION_BACKEND", "ironclaw")
    monkeypatch.setenv("OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK", "1")
    monkeypatch.delenv("OPENCLAW_IRONCLAW_PREFLIGHT_ENFORCED", raising=False)

    with patch(
        "modules.communication.moltbot_bridge.src.ironclaw_gateway_client.IronClawGatewayClient.startup_probe",
        return_value={
            "ok": False,
            "detail": "ironclaw_down but local fallback policy active",
            "backend": "lm_studio",
            "remediation": ["Start LM Studio"],
        },
    ):
        ok = main.run_ironclaw_runtime_preflight(tmp_path)

    assert ok is True
    captured = capsys.readouterr().out
    assert "[IRONCLAW] preflight=FAIL backend=ironclaw resolved=lm_studio" in captured
    assert "Startup blocked" not in captured
