"""Tests for OBAI Discord bot — config, lifecycle, identity safety.

Does NOT require a live Discord connection.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

# Ensure the module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from modules.communication.obai_discord_bot.src.obai_discord_bot import (
    FOUNDUPS_GUILD_ID,
    HELP_TEXT,
    OBAIConfig,
    OBAIDiscordBot,
    load_config,
)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


class TestLoadConfig:
    """Test config loading from environment variables."""

    def test_loads_token_from_env(self, monkeypatch):
        monkeypatch.setenv("OBAI_BOT", "test-token-abc")
        config = load_config()
        assert config.token == "test-token-abc"

    def test_default_guild_id(self, monkeypatch):
        monkeypatch.setenv("OBAI_BOT", "tok")
        config = load_config()
        assert config.guild_id == FOUNDUPS_GUILD_ID

    def test_custom_guild_id(self, monkeypatch):
        monkeypatch.setenv("OBAI_BOT", "tok")
        monkeypatch.setenv("OBAI_GUILD_ID", "123456789")
        config = load_config()
        assert config.guild_id == 123456789

    def test_default_log_level(self, monkeypatch):
        monkeypatch.setenv("OBAI_BOT", "tok")
        config = load_config()
        assert config.log_level == "INFO"

    def test_custom_log_level(self, monkeypatch):
        monkeypatch.setenv("OBAI_BOT", "tok")
        monkeypatch.setenv("OBAI_LOG_LEVEL", "debug")
        config = load_config()
        assert config.log_level == "DEBUG"

    def test_enabled_default_true(self, monkeypatch):
        monkeypatch.setenv("OBAI_BOT", "tok")
        config = load_config()
        assert config.enabled is True

    def test_enabled_false(self, monkeypatch):
        monkeypatch.setenv("OBAI_BOT", "tok")
        monkeypatch.setenv("OBAI_ENABLED", "false")
        config = load_config()
        assert config.enabled is False

    def test_enabled_zero(self, monkeypatch):
        monkeypatch.setenv("OBAI_BOT", "tok")
        monkeypatch.setenv("OBAI_ENABLED", "0")
        config = load_config()
        assert config.enabled is False

    def test_missing_token_exits_when_enabled(self, monkeypatch):
        monkeypatch.delenv("OBAI_BOT", raising=False)
        monkeypatch.delenv("OBAI_ENABLED", raising=False)
        with pytest.raises(SystemExit):
            load_config()

    def test_missing_token_ok_when_disabled(self, monkeypatch):
        monkeypatch.delenv("OBAI_BOT", raising=False)
        monkeypatch.setenv("OBAI_ENABLED", "false")
        config = load_config()
        assert config.enabled is False
        assert config.token == ""

    def test_invalid_guild_id_exits(self, monkeypatch):
        monkeypatch.setenv("OBAI_BOT", "tok")
        monkeypatch.setenv("OBAI_GUILD_ID", "not-a-number")
        with pytest.raises(SystemExit):
            load_config()

    def test_whitespace_token_treated_as_missing(self, monkeypatch):
        monkeypatch.setenv("OBAI_BOT", "   ")
        monkeypatch.delenv("OBAI_ENABLED", raising=False)
        with pytest.raises(SystemExit):
            load_config()


# ---------------------------------------------------------------------------
# Bot initialization
# ---------------------------------------------------------------------------


class TestBotInit:
    """Test OBAIDiscordBot initialization (no live Discord)."""

    def _make_config(self, **overrides):
        defaults = {"token": "test-token", "guild_id": FOUNDUPS_GUILD_ID, "log_level": "INFO", "enabled": True}
        defaults.update(overrides)
        return OBAIConfig(**defaults)

    def test_creates_client_with_intents(self):
        config = self._make_config()
        bot = OBAIDiscordBot(config)
        assert bot._client is not None
        assert bot._client.intents.message_content is True
        assert bot._client.intents.guilds is True
        assert bot._client.intents.guild_messages is True

    def test_not_connected_before_start(self):
        config = self._make_config()
        bot = OBAIDiscordBot(config)
        assert bot.is_connected() is False

    def test_status_before_start(self):
        config = self._make_config()
        bot = OBAIDiscordBot(config)
        status = bot.get_status()
        assert status["connected"] is False
        assert status["enabled"] is True
        assert status["guild_id"] == FOUNDUPS_GUILD_ID
        assert status["bot_user"] is None
        assert status["started_at"] is None

    def test_disabled_bot_status(self):
        config = self._make_config(enabled=False)
        bot = OBAIDiscordBot(config)
        status = bot.get_status()
        assert status["enabled"] is False


# ---------------------------------------------------------------------------
# Message handling
# ---------------------------------------------------------------------------


class TestMessageHandling:
    """Test on_message logic without live Discord.

    discord.py 2.x makes Client.user a read-only property, so we mock
    the entire _client object rather than trying to set .user on a real Client.
    """

    def _make_bot_with_mock_client(self):
        config = OBAIConfig(token="test-token", guild_id=FOUNDUPS_GUILD_ID, log_level="INFO", enabled=True)
        bot = OBAIDiscordBot(config)
        mock_client = MagicMock()
        mock_client.user = MagicMock()
        mock_client.user.id = 1127122752776699915
        bot._client = mock_client
        return bot

    @pytest.mark.asyncio
    async def test_ignores_own_messages(self):
        bot = self._make_bot_with_mock_client()
        msg = MagicMock()
        msg.author = bot._client.user  # Same object = own message
        msg.reply = AsyncMock()

        await bot.on_message(msg)
        msg.reply.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignores_bot_messages(self):
        bot = self._make_bot_with_mock_client()
        msg = MagicMock()
        msg.author = MagicMock()
        msg.author.bot = True
        msg.reply = AsyncMock()

        await bot.on_message(msg)
        msg.reply.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignores_non_mention(self):
        bot = self._make_bot_with_mock_client()
        bot._client.user.mentioned_in = MagicMock(return_value=False)

        msg = MagicMock()
        msg.author = MagicMock()
        msg.author.bot = False
        msg.reply = AsyncMock()

        await bot.on_message(msg)
        msg.reply.assert_not_called()

    @pytest.mark.asyncio
    async def test_replies_to_mention(self):
        bot = self._make_bot_with_mock_client()
        bot._client.user.mentioned_in = MagicMock(return_value=True)

        msg = MagicMock()
        msg.author = MagicMock()
        msg.author.bot = False
        msg.mention_everyone = False
        msg.channel = MagicMock()  # Not a DMChannel instance
        msg.channel.name = "swarm-general"
        msg.content = "@OBAI help me"
        msg.reply = AsyncMock()

        await bot.on_message(msg)
        msg.reply.assert_called_once_with(HELP_TEXT)

    @pytest.mark.asyncio
    async def test_ignores_everyone_mention(self):
        bot = self._make_bot_with_mock_client()
        bot._client.user.mentioned_in = MagicMock(return_value=True)

        msg = MagicMock()
        msg.author = MagicMock()
        msg.author.bot = False
        msg.mention_everyone = True
        msg.reply = AsyncMock()

        await bot.on_message(msg)
        msg.reply.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignores_dm_channel(self):
        bot = self._make_bot_with_mock_client()
        bot._client.user.mentioned_in = MagicMock(return_value=True)

        msg = MagicMock()
        msg.author = MagicMock()
        msg.author.bot = False
        msg.mention_everyone = False
        msg.channel = MagicMock(spec=discord.DMChannel)
        msg.content = "hello"
        msg.reply = AsyncMock()

        await bot.on_message(msg)
        msg.reply.assert_not_called()


# ---------------------------------------------------------------------------
# Help text identity check
# ---------------------------------------------------------------------------


class TestHelpText:
    """Verify help text preserves OBAI identity boundary."""

    def test_starts_with_obai_prefix(self):
        assert HELP_TEXT.startswith("[OBAI]")

    def test_does_not_claim_admin(self):
        lower = HELP_TEXT.lower()
        assert "admin" not in lower or "operator" in lower

    def test_mentions_operator_escalation(self):
        assert "operator" in HELP_TEXT.lower()

    def test_does_not_mention_cabr_scoring(self):
        assert "score" not in HELP_TEXT.lower()
        assert "cabr" not in HELP_TEXT.lower()
