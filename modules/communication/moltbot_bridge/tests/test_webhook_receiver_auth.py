"""Webhook authentication must fail closed without a configured secret."""

from unittest.mock import patch

from modules.communication.moltbot_bridge.src.webhook_receiver import (
    get_webhook_token,
    verify_token,
)


_AUTH_ENV = {"OpenClaw_Pass": "", "FOUNDUPS_WEBHOOK_TOKEN": ""}


def test_missing_webhook_secret_rejects_all_headers() -> None:
    with patch.dict("os.environ", _AUTH_ENV, clear=False):
        assert get_webhook_token() is None
        assert verify_token("Bearer dev-token-change-me", None, None) is False
        assert verify_token(None, None, "dev-token-change-me") is False


def test_insecure_default_is_rejected_when_explicitly_configured() -> None:
    env = {"OpenClaw_Pass": "dev-token-change-me", "FOUNDUPS_WEBHOOK_TOKEN": ""}
    with patch.dict("os.environ", env, clear=False):
        assert get_webhook_token() is None
        assert verify_token(None, "dev-token-change-me", None) is False


def test_configured_secret_accepts_supported_headers() -> None:
    env = {"OpenClaw_Pass": "configured-test-secret", "FOUNDUPS_WEBHOOK_TOKEN": ""}
    with patch.dict("os.environ", env, clear=False):
        assert verify_token("Bearer configured-test-secret", None, None) is True
        assert verify_token(None, None, "configured-test-secret") is True
        assert verify_token(None, "configured-test-secret", None) is True
        assert verify_token("Bearer wrong", None, None) is False
