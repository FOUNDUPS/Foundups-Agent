"""
Tests for IronClaw gateway client health probing behavior.
"""

from unittest.mock import MagicMock, patch

from modules.communication.moltbot_bridge.src.ironclaw_gateway_client import (
    IronClawGatewayClient,
)


def _mock_response(ok: bool, status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.ok = ok
    resp.status_code = status_code
    return resp


def test_health_prefers_explicit_health_endpoint():
    client = IronClawGatewayClient()
    with patch(
        "requests.get",
        side_effect=[
            _mock_response(True, 200),  # /api/health
        ],
    ):
        healthy, detail = client.health()

    assert healthy is True
    assert detail == "healthy via /api/health"


def test_health_falls_back_to_models_endpoint():
    client = IronClawGatewayClient()
    with patch(
        "requests.get",
        side_effect=[
            _mock_response(False, 404),  # /api/health
            _mock_response(False, 404),  # /health
            _mock_response(True, 200),   # /v1/models
        ],
    ):
        healthy, detail = client.health()

    assert healthy is True
    assert detail == "healthy via /v1/models"


def test_health_returns_diagnostics_when_all_probes_fail():
    client = IronClawGatewayClient()
    with patch(
        "requests.get",
        side_effect=[
            _mock_response(False, 404),  # /api/health
            Exception("boom"),           # /health
            _mock_response(False, 503),  # /v1/models
        ],
    ):
        healthy, detail = client.health()

    assert healthy is False
    assert detail.startswith("health probes failed (")
    assert "/api/health=404" in detail
    assert "/health=error:Exception" in detail
    assert "/v1/models=503" in detail


def test_startup_probe_accepts_lm_studio_fallback(monkeypatch):
    client = IronClawGatewayClient()
    monkeypatch.setenv("SIM_QWEN_BACKEND", "local")
    monkeypatch.setenv("SIM_QWEN_BACKEND_URL", "http://127.0.0.1:1234")

    with patch.object(client, "health", return_value=(False, "health probes failed")):
        with patch("requests.get", return_value=_mock_response(True, 200)):
            status = client.startup_probe()

    assert status["ok"] is True
    assert status["backend"] == "lm_studio"
    assert "lm_studio_fallback_ok" in status["detail"]


def test_startup_probe_returns_remediation_when_all_backends_are_down(monkeypatch):
    client = IronClawGatewayClient()
    monkeypatch.setenv("SIM_QWEN_BACKEND", "local")
    monkeypatch.delenv("IRONCLAW_START_CMD", raising=False)

    with patch.object(client, "health", return_value=(False, "health probes failed")):
        with patch("requests.get", side_effect=Exception("offline")):
            status = client.startup_probe()

    assert status["ok"] is False
    assert status["backend"] is None
    assert any("Set IRONCLAW_START_CMD" in item for item in status["remediation"])
