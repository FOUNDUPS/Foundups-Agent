"""
Boot/runtime integration: Discord voice lane + AntifaFMBroadcaster.

Uses mocks — no real Discord or FFmpeg.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def youtube_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTIFAFM_YOUTUBE_STREAM_KEY", "test-stream-key")
    monkeypatch.setenv("ANTIFAFM_BROADCASTER_ENABLED", "true")
    monkeypatch.setenv("ANTIFAFM_DISCORD_VOICE_ENABLED", "0")


def test_discord_lane_absent_when_flag_off(youtube_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTIFAFM_DISCORD_VOICE_ENABLED", raising=False)
    from modules.platform_integration.antifafm_broadcaster.src.antifafm_broadcaster import AntifaFMBroadcaster

    b = AntifaFMBroadcaster(enable_ai_monitoring=False)
    assert b.discord_output is None
    st = b.get_status()
    assert st["discord_voice"] is None
    assert st["discord_voice_enabled_flag"] is False


def test_discord_flag_on_without_token_no_adapter(
    youtube_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTIFAFM_DISCORD_VOICE_ENABLED", "1")
    monkeypatch.setenv("ANTIFAFM_BOT", "")
    monkeypatch.setenv("ANTIFAFM_DISCORD_GUILD_ID", "1")
    monkeypatch.setenv("ANTIFAFM_DISCORD_VOICE_CHANNEL_ID", "2")

    from modules.platform_integration.antifafm_broadcaster.src.antifafm_broadcaster import AntifaFMBroadcaster

    b = AntifaFMBroadcaster(enable_ai_monitoring=False)
    assert b.discord_output is None


def test_broadcaster_start_await_discord_start_when_configured(
    youtube_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTIFAFM_DISCORD_VOICE_ENABLED", "1")
    monkeypatch.setenv("ANTIFAFM_BOT", "dummy-token")
    monkeypatch.setenv("ANTIFAFM_DISCORD_GUILD_ID", "99")
    monkeypatch.setenv("ANTIFAFM_DISCORD_VOICE_CHANNEL_ID", "100")

    mock_lane = MagicMock()
    mock_lane.start = AsyncMock(return_value=True)
    mock_lane.stop = AsyncMock(return_value=True)
    mock_lane.get_status = MagicMock(
        return_value={"output": "discord_voice", "playing": True, "healthy": True}
    )

    ffmpeg_path = "modules.platform_integration.antifafm_broadcaster.src.antifafm_broadcaster.FFmpegStreamer"
    health_path = "modules.platform_integration.antifafm_broadcaster.src.antifafm_broadcaster.StreamHealthMonitor"
    build_path = (
        "modules.platform_integration.antifafm_broadcaster.src.discord_voice_output."
        "build_discord_voice_from_env"
    )

    async def _run() -> None:
        with patch(build_path, return_value=mock_lane):
            from modules.platform_integration.antifafm_broadcaster.src.antifafm_broadcaster import (
                AntifaFMBroadcaster,
            )

            b = AntifaFMBroadcaster(enable_ai_monitoring=False)
            assert b.discord_output is mock_lane

            with patch(ffmpeg_path) as FS_cls, patch(health_path) as HM_cls:
                fs_inst = MagicMock()
                fs_inst.start = MagicMock(return_value=True)
                fs_inst.stop = MagicMock()
                fs_inst.get_status = MagicMock(return_value={"state": "running"})
                fs_inst.is_streaming_healthy = MagicMock(return_value=(True, "ok"))
                fs_inst.get_last_stderr = MagicMock(return_value="")
                FS_cls.return_value = fs_inst

                hm_inst = MagicMock()
                hm_inst.start = AsyncMock()
                hm_inst.stop = AsyncMock()
                hm_inst.needs_intervention = False
                hm_inst.is_healthy = True
                hm_inst.get_metrics = MagicMock(return_value={"state": "healthy", "restart_count": 0})
                HM_cls.return_value = hm_inst

                ok = await b.start()
                assert ok is True
                mock_lane.start.assert_awaited_once()

                st = b.get_status()
                assert st["discord_voice"] is not None
                assert st["discord_voice"]["output"] == "discord_voice"

                await b.stop()
                mock_lane.stop.assert_awaited()

    asyncio.run(_run())


def test_discord_start_failure_does_not_fail_youtube(
    youtube_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTIFAFM_DISCORD_VOICE_ENABLED", "1")
    monkeypatch.setenv("ANTIFAFM_BOT", "dummy-token")
    monkeypatch.setenv("ANTIFAFM_DISCORD_GUILD_ID", "99")
    monkeypatch.setenv("ANTIFAFM_DISCORD_VOICE_CHANNEL_ID", "100")

    mock_lane = MagicMock()
    mock_lane.start = AsyncMock(return_value=False)
    mock_lane.stop = AsyncMock(return_value=True)

    ffmpeg_path = "modules.platform_integration.antifafm_broadcaster.src.antifafm_broadcaster.FFmpegStreamer"
    health_path = "modules.platform_integration.antifafm_broadcaster.src.antifafm_broadcaster.StreamHealthMonitor"
    build_path = (
        "modules.platform_integration.antifafm_broadcaster.src.discord_voice_output."
        "build_discord_voice_from_env"
    )

    async def _run() -> None:
        with patch(build_path, return_value=mock_lane):
            from modules.platform_integration.antifafm_broadcaster.src.antifafm_broadcaster import (
                AntifaFMBroadcaster,
            )

            b = AntifaFMBroadcaster(enable_ai_monitoring=False)

            with patch(ffmpeg_path) as FS_cls, patch(health_path) as HM_cls:
                fs_inst = MagicMock()
                fs_inst.start = MagicMock(return_value=True)
                fs_inst.stop = MagicMock()
                fs_inst.get_status = MagicMock(return_value={})
                fs_inst.is_streaming_healthy = MagicMock(return_value=(True, "ok"))
                fs_inst.get_last_stderr = MagicMock(return_value="")
                FS_cls.return_value = fs_inst

                hm_inst = MagicMock()
                hm_inst.start = AsyncMock()
                hm_inst.stop = AsyncMock()
                hm_inst.needs_intervention = False
                hm_inst.is_healthy = True
                hm_inst.get_metrics = MagicMock(return_value={"state": "healthy", "restart_count": 0})
                HM_cls.return_value = hm_inst

                ok = await b.start()
                assert ok is True
                assert b.discord_output is None
                mock_lane.stop.assert_awaited()

    asyncio.run(_run())


def test_build_discord_voice_from_env_returns_none_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTIFAFM_BOT", raising=False)
    monkeypatch.delenv("ANTIFAFM_DISCORD_BOT_TOKEN", raising=False)
    monkeypatch.setenv("ANTIFAFM_DISCORD_GUILD_ID", "1")
    monkeypatch.setenv("ANTIFAFM_DISCORD_VOICE_CHANNEL_ID", "2")

    from modules.platform_integration.antifafm_broadcaster.src.discord_voice_output import (
        build_discord_voice_from_env,
    )

    assert build_discord_voice_from_env("https://example.com/stream.mp3") is None


def test_build_discord_voice_from_env_invalid_guild_skips_lane(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTIFAFM_BOT", "fake-token")
    monkeypatch.setenv("ANTIFAFM_DISCORD_GUILD_ID", "not-a-number")
    monkeypatch.setenv("ANTIFAFM_DISCORD_VOICE_CHANNEL_ID", "123456789012345678")

    from modules.platform_integration.antifafm_broadcaster.src.discord_voice_output import (
        build_discord_voice_from_env,
    )

    assert build_discord_voice_from_env("https://example.com/stream.mp3") is None
