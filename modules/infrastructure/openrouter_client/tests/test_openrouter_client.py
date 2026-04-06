# -*- coding: utf-8 -*-
"""Tests for OpenRouter client module."""

import os
import pytest
from unittest.mock import patch, MagicMock

# Set test API key before import
os.environ["OPENROUTER_API_KEY"] = "test-key-for-unit-tests"

from modules.infrastructure.openrouter_client.src.openrouter_client import (
    OpenRouterClient,
    OpenRouterConfig,
    OpenRouterResponse,
    MODEL_ALIASES,
    get_openrouter_client,
    openrouter_chat,
    openrouter_health,
)


class TestOpenRouterConfig:
    """Tests for OpenRouterConfig."""

    def test_from_env_defaults(self):
        """Test config loads with defaults."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False):
            config = OpenRouterConfig.from_env()
            assert config.api_key == "test-key"
            assert config.base_url == "https://openrouter.ai/api/v1"
            assert config.default_model == "anthropic/claude-sonnet-4"
            assert config.preset == "foundups-agent"
            assert config.timeout_sec == 60.0
            assert config.fallback_enabled is True
            assert config.web_search is False

    def test_from_env_custom(self):
        """Test config loads custom values."""
        env = {
            "OPENROUTER_API_KEY": "custom-key",
            "OPENROUTER_BASE_URL": "https://custom.api/v1",
            "OPENROUTER_DEFAULT_MODEL": "openai/gpt-4o",
            "OPENROUTER_PRESET": "custom-preset",
            "OPENROUTER_TIMEOUT_SEC": "30",
            "OPENROUTER_FALLBACK_ENABLED": "false",
            "OPENROUTER_WEB_SEARCH": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            config = OpenRouterConfig.from_env()
            assert config.api_key == "custom-key"
            assert config.base_url == "https://custom.api/v1"
            assert config.default_model == "openai/gpt-4o"
            assert config.preset == "custom-preset"
            assert config.timeout_sec == 30.0
            assert config.fallback_enabled is False
            assert config.web_search is True


class TestOpenRouterClient:
    """Tests for OpenRouterClient."""

    def test_model_alias_resolution(self):
        """Test model aliases resolve correctly."""
        client = OpenRouterClient()

        assert client._resolve_model("sonnet") == "anthropic/claude-sonnet-4"
        assert client._resolve_model("gpt4") == "openai/gpt-4o"
        assert client._resolve_model("llama") == "meta-llama/llama-3.1-70b-instruct"
        assert client._resolve_model("anthropic/custom-model") == "anthropic/custom-model"
        assert client._resolve_model(None) == client.config.default_model

    def test_is_configured(self):
        """Test is_configured check."""
        client = OpenRouterClient()
        assert client.is_configured() is True

        # Test with empty key
        empty_config = OpenRouterConfig(
            api_key="",
            base_url="https://openrouter.ai/api/v1",
            default_model="anthropic/claude-sonnet-4",
            preset="",
            timeout_sec=60.0,
            fallback_enabled=True,
            web_search=False,
        )
        client_empty = OpenRouterClient(config=empty_config)
        assert client_empty.is_configured() is False

    @patch("requests.Session.get")
    def test_health_success(self, mock_get):
        """Test health check success."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_get.return_value = mock_response

        client = OpenRouterClient()
        ok, detail = client.health()

        assert ok is True
        assert "healthy" in detail.lower()

    @patch("requests.Session.get")
    def test_health_failure(self, mock_get):
        """Test health check failure."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        client = OpenRouterClient()
        ok, detail = client.health()

        assert ok is False
        assert "500" in detail

    @patch("requests.Session.post")
    def test_chat_completion_success(self, mock_post):
        """Test chat completion success."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello! How can I help?"}}],
            "model": "anthropic/claude-sonnet-4",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_cost": 0.001,
            },
        }
        mock_post.return_value = mock_response

        client = OpenRouterClient()
        response = client.chat_completion(
            user_message="Hello",
            model="sonnet",
        )

        assert response.ok is True
        assert response.content == "Hello! How can I help?"
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 20
        assert response.cost == 0.001

    @patch("requests.Session.post")
    def test_chat_completion_error(self, mock_post):
        """Test chat completion error handling."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": {"message": "Invalid API key"}
        }
        mock_post.return_value = mock_response

        client = OpenRouterClient()
        response = client.chat_completion(user_message="Hello")

        assert response.ok is False
        assert "Invalid API key" in response.error

    def test_chat_completion_not_configured(self):
        """Test chat completion when not configured."""
        empty_config = OpenRouterConfig(
            api_key="",
            base_url="https://openrouter.ai/api/v1",
            default_model="anthropic/claude-sonnet-4",
            preset="",
            timeout_sec=60.0,
            fallback_enabled=True,
            web_search=False,
        )
        client = OpenRouterClient(config=empty_config)
        response = client.chat_completion(user_message="Hello")

        assert response.ok is False
        assert "not configured" in response.error.lower()


class TestModelAliases:
    """Tests for model alias mappings."""

    def test_all_aliases_have_values(self):
        """Verify all aliases map to valid model IDs."""
        for alias, model_id in MODEL_ALIASES.items():
            assert "/" in model_id, f"Alias '{alias}' should map to provider/model format"
            assert len(model_id) > 5, f"Alias '{alias}' has invalid model ID"


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_openrouter_client_returns_same_instance(self):
        """Test singleton returns same instance."""
        client1 = get_openrouter_client()
        client2 = get_openrouter_client()
        assert client1 is client2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
