"""
Discord voice channel output for antifaFM Icecast stream.

Sibling to FFmpegStreamer: same audio URL, Discord voice instead of RTMPS.
Bounded adapter — no slash commands, single channel (see ANTIFAFM_DISCORD_VOICE_OUTPUT_SPEC).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

from .stream_health_monitor import StreamHealthMonitor, RecoveryConfig

logger = logging.getLogger(__name__)

try:
    import discord  # type: ignore
    from discord import FFmpegOpusAudio  # type: ignore

    DISCORD_VOICE_AVAILABLE = True

    class _AntifaVoiceClient(discord.Client):  # type: ignore[misc,valid-type]
        """Thin Client hook — discord.Client has no add_listener in all versions."""

        def __init__(self, voice_output: "DiscordVoiceOutput", **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self._voice_output = voice_output

        async def on_ready(self) -> None:  # noqa: D401
            vo = self._voice_output
            if vo._closed:
                return
            if vo._setup_done.is_set() and vo._setup_error is None:
                return
            try:
                await vo._initial_connect()
            except BaseException as e:
                vo._setup_error = e
                logger.exception("[DISCORD] Failed during on_ready voice setup")
            finally:
                vo._setup_done.set()

except ImportError:  # pragma: no cover - exercised when discord not installed
    discord = None  # type: ignore
    FFmpegOpusAudio = None  # type: ignore
    DISCORD_VOICE_AVAILABLE = False
    _AntifaVoiceClient = None  # type: ignore


def _env_volume(name: str, default: str = "1.0") -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return 1.0


class DiscordVoiceOutput:
    """
    Connect a bot user to a voice channel and play the Icecast URL via FFmpeg→Opus.

    Lifecycle matches broadcaster: start() after YouTube lane is up, stop() on shutdown.
    """

    def __init__(
        self,
        bot_token: str,
        guild_id: int,
        channel_id: int,
        stream_url: str,
        volume: Optional[float] = None,
    ) -> None:
        self.bot_token = bot_token
        self.guild_id = int(guild_id)
        self.channel_id = int(channel_id)
        self.stream_url = stream_url
        if volume is None:
            volume = _env_volume("ANTIFAFM_DISCORD_VOICE_VOLUME", "1.0")
        self.volume = max(0.0, min(2.0, float(volume)))

        self._client: Any = None
        self._voice: Any = None
        self._runner_task: Optional[asyncio.Task] = None
        self._setup_done = asyncio.Event()
        self._setup_error: Optional[BaseException] = None
        self._playback_lock = asyncio.Lock()
        self._health_monitor: Optional[StreamHealthMonitor] = None
        self._closed = False

    def _check_health(self) -> bool:
        if self._closed or not self._client:
            return False
        try:
            if not self._client.is_ready():
                return False
            vc = self._voice
            if not vc or not vc.is_connected():
                return False
            if not vc.is_playing():
                return False
            return True
        except Exception:
            return False

    async def _begin_playback_unlocked(self) -> None:
        if not DISCORD_VOICE_AVAILABLE or not self._voice:
            raise RuntimeError("Discord voice not ready for playback")
        if self._voice.is_playing():
            self._voice.stop()
        before = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        # PCMVolumeTransformer rejects Opus-backed sources; apply gain in FFmpeg (-af).
        if abs(self.volume - 1.0) <= 1e-6:
            source = FFmpegOpusAudio(self.stream_url, before_options=before)
        else:
            vol = max(0.0, min(2.0, self.volume))
            source = FFmpegOpusAudio(
                self.stream_url,
                before_options=before,
                options=f"-af volume={vol}",
            )
        self._voice.play(source, after=self._after_play)

    def _after_play(self, error: Optional[BaseException]) -> None:
        if error:
            logger.warning("[DISCORD] Playback stopped with error: %s", error)

    async def _restart_voice(self) -> bool:
        async with self._playback_lock:
            try:
                logger.info("[DISCORD] Health monitor: reconnecting voice playback")
                if self._voice:
                    self._voice.stop()
                    if self._voice.is_connected():
                        await self._voice.disconnect(force=True)
                    self._voice = None
                guild = self._client.get_guild(self.guild_id)
                if not guild:
                    logger.error("[DISCORD] Guild %s not found during restart", self.guild_id)
                    return False
                ch = guild.get_channel(self.channel_id)
                if ch is None or not isinstance(ch, discord.VoiceChannel):
                    logger.error("[DISCORD] Voice channel %s missing or wrong type", self.channel_id)
                    return False
                self._voice = await ch.connect(reconnect=True, timeout=60.0)
                await self._begin_playback_unlocked()
                return True
            except Exception as e:
                logger.error("[DISCORD] Restart failed: %s", e)
                return False

    async def _initial_connect(self) -> None:
        guild = self._client.get_guild(self.guild_id)
        if not guild:
            raise RuntimeError(f"Guild {self.guild_id} not visible to bot (wrong id or missing intent?)")
        ch = guild.get_channel(self.channel_id)
        if ch is None or not isinstance(ch, discord.VoiceChannel):
            raise RuntimeError(
                f"Voice channel {self.channel_id} not found or not a voice channel"
            )
        self._voice = await ch.connect(reconnect=True, timeout=60.0)
        async with self._playback_lock:
            await self._begin_playback_unlocked()

    async def start(self) -> bool:
        if not DISCORD_VOICE_AVAILABLE:
            logger.error("[DISCORD] discord.py / voice deps missing — pip install discord.py PyNaCl")
            return False
        if self._runner_task and not self._runner_task.done():
            logger.warning("[DISCORD] Already starting or running")
            return self._setup_done.is_set() and self._setup_error is None

        self._setup_done.clear()
        self._setup_error = None
        self._closed = False

        intents = discord.Intents.default()
        intents.voice_states = True

        assert _AntifaVoiceClient is not None
        self._client = _AntifaVoiceClient(self, intents=intents)

        self._runner_task = asyncio.create_task(
            self._client.start(self.bot_token, reconnect=True),
            name="antifafm-discord-client",
        )

        try:
            await asyncio.wait_for(self._setup_done.wait(), timeout=120.0)
        except asyncio.TimeoutError:
            logger.error("[DISCORD] Timed out waiting for voice ready")
            await self.stop()
            return False

        if self._setup_error is not None:
            await self.stop()
            return False

        self._health_monitor = StreamHealthMonitor(
            check_fn=self._check_health,
            restart_fn=self._restart_voice,
            config=RecoveryConfig(
                initial_delay=5.0,
                max_delay=120.0,
                backoff_multiplier=2.0,
                max_consecutive_failures=8,
                health_check_interval=15.0,
            ),
        )
        await self._health_monitor.start()
        logger.info("[DISCORD] Voice output started in #%s", self.channel_id)
        return True

    async def stop(self) -> bool:
        self._closed = True
        if self._health_monitor:
            await self._health_monitor.stop()
            self._health_monitor = None

        if self._voice:
            try:
                self._voice.stop()
                if self._voice.is_connected():
                    await self._voice.disconnect(force=True)
            except Exception as e:
                logger.debug("[DISCORD] Voice disconnect: %s", e)
            self._voice = None

        if self._client:
            try:
                await self._client.close()
            except Exception as e:
                logger.debug("[DISCORD] Client close: %s", e)
            self._client = None

        if self._runner_task:
            try:
                await asyncio.wait_for(self._runner_task, timeout=15.0)
            except asyncio.TimeoutError:
                self._runner_task.cancel()
                try:
                    await self._runner_task
                except asyncio.CancelledError:
                    pass
            except asyncio.CancelledError:
                pass
            self._runner_task = None

        logger.info("[DISCORD] Voice output stopped")
        return True

    def get_status(self) -> Dict[str, Any]:
        health: Dict[str, Any] = {}
        if self._health_monitor:
            m = self._health_monitor.get_metrics()
            health = {
                "state": m.get("state"),
                "restart_count": m.get("restart_count", 0),
                "consecutive_failures": m.get("consecutive_failures", 0),
            }
        vc_connected = False
        playing = False
        if self._voice:
            try:
                vc_connected = self._voice.is_connected()
                playing = self._voice.is_playing()
            except Exception:
                pass
        ready = False
        if self._client:
            try:
                ready = self._client.is_ready()
            except Exception:
                pass
        return {
            "output": "discord_voice",
            "available": DISCORD_VOICE_AVAILABLE,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "stream_url": self.stream_url,
            "client_ready": ready,
            "voice_connected": vc_connected,
            "playing": playing,
            "healthy": self._check_health(),
            "health_monitor": health,
        }


def _parse_snowflake_env(var_name: str) -> Optional[int]:
    """Parse Discord snowflake from env; invalid or non-positive → None (fail closed)."""
    raw = (os.getenv(var_name) or "").strip()
    if not raw:
        return None
    try:
        v = int(raw)
    except ValueError:
        logger.warning("[DISCORD] Invalid %s=%r (not an integer) — voice lane skipped", var_name, raw)
        return None
    if v <= 0:
        return None
    return v


def build_discord_voice_from_env(stream_url: str) -> Optional[DiscordVoiceOutput]:
    """Construct adapter from env if token present; caller checks ANTIFAFM_DISCORD_VOICE_ENABLED."""
    token = os.getenv("ANTIFAFM_BOT", "").strip() or os.getenv("ANTIFAFM_DISCORD_BOT_TOKEN", "").strip()
    if not token:
        logger.warning("[DISCORD] No ANTIFAFM_BOT / ANTIFAFM_DISCORD_BOT_TOKEN — voice lane skipped")
        return None
    gid = _parse_snowflake_env("ANTIFAFM_DISCORD_GUILD_ID")
    cid = _parse_snowflake_env("ANTIFAFM_DISCORD_VOICE_CHANNEL_ID")
    if gid is None or cid is None:
        logger.warning(
            "[DISCORD] ANTIFAFM_DISCORD_GUILD_ID / ANTIFAFM_DISCORD_VOICE_CHANNEL_ID "
            "missing, zero, or invalid — voice lane skipped"
        )
        return None
    return DiscordVoiceOutput(bot_token=token, guild_id=gid, channel_id=cid, stream_url=stream_url)
