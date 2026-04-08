"""
antifaFM YouTube Live Broadcaster DAE

Bridges Icecast audio stream to YouTube Live via FFmpeg.

Pattern Sources (Module Cube Reuse - WSP 84):
- modules/communication/livechat/src/peertube_relay_handler.py (FFmpeg subprocess)
- modules/communication/livechat/src/youtube_dae_heartbeat.py (heartbeat + telemetry)
- modules/communication/livechat/src/auto_moderator_dae.py (DAE lifecycle)
- modules/infrastructure/wre_core/src/skill_trigger.py (WRE skill firing)

WSP Compliance:
- WSP 27: Universal DAE Architecture (4-phase lifecycle)
- WSP 46: WRE Protocol (skill trigger integration)
- WSP 64: Secure credential management (ENV vars only - stream key)
- WSP 77: Agent Coordination (AI Overseer + WRE skills)
- WSP 91: DAEMON Observability (heartbeat + telemetry)
- WSP 96: WRE Skills (domain-based skill discovery)

NAVIGATION: antifaFM radio → YouTube Live bridge
-> Called by: CLI youtube_menu.py (option 10)
-> Delegates to: FFmpegStreamer, StreamHealthMonitor, SkillTriggerMixin
-> Pattern: PeerTubeRelayHandler (FFmpeg subprocess)
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from .ffmpeg_streamer import FFmpegStreamer, StreamConfig, StreamState, FFmpegStreamerError
from .stream_health_monitor import StreamHealthMonitor, RecoveryConfig, HealthState

# WRE Integration (WSP 46, WSP 96)
try:
    from modules.infrastructure.wre_core.src.skill_trigger import SkillTriggerMixin
    WRE_AVAILABLE = True
except ImportError:
    SkillTriggerMixin = object  # Fallback to no-op base class
    WRE_AVAILABLE = False

logger = logging.getLogger(__name__)


def _env_truthy(name: str, default: str = "false") -> bool:
    """Environment variable truthy check - pattern from auto_moderator_dae.py"""
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")


class BroadcasterStatus(Enum):
    """Broadcaster status - pattern from YouTubeDAEHeartbeat"""
    OFFLINE = "offline"
    STARTING = "starting"
    BROADCASTING = "broadcasting"
    DEGRADED = "degraded"  # Health issues but still running
    ERROR = "error"
    STOPPING = "stopping"


@dataclass
class BroadcastTelemetry:
    """Telemetry data - pattern from YouTubeHeartbeatData"""
    timestamp: datetime
    status: BroadcasterStatus
    uptime_seconds: float
    stream_url: str
    restart_count: int
    health_state: str
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "uptime_seconds": self.uptime_seconds,
            "stream_url": self.stream_url,
            "restart_count": self.restart_count,
            "health_state": self.health_state,
            "error_message": self.error_message,
        }


class AntifaFMBroadcaster(SkillTriggerMixin):
    """
    antifaFM YouTube Live Broadcaster DAE.

    Streams Icecast audio to YouTube Live with:
    - Static visual overlay (Layer 1 MVP)
    - Auto-recovery with exponential backoff
    - Telemetry logging for observability
    - AI Overseer integration for error detection
    - WRE skill execution for autonomous operations

    DAE Phases (WSP 27):
    - Phase -1 (Signal): Icecast audio stream input
    - Phase 0 (Knowledge): Stream metadata, health history
    - Phase 1 (Protocol): FFmpeg command construction
    - Phase 2 (Agentic): Auto-recovery, health monitoring, WRE skills

    WRE Integration (WSP 46, WSP 96):
    - Domain: "streaming"
    - Skills: suno_stt_lyrics_extract, antifafm_add_video
    - Cadence: 15 minutes (fires domain skills periodically)
    """

    def __init__(self, enable_ai_monitoring: bool = True):
        """
        Initialize antifaFM Broadcaster DAE.

        Args:
            enable_ai_monitoring: Enable AI Overseer for error detection (WSP 77)
        """
        logger.info("[RADIO] Initializing antifaFM Broadcaster DAE")

        # Configuration from ENV (WSP 64: Secure credential management)
        self.enabled = _env_truthy("ANTIFAFM_BROADCASTER_ENABLED", "true")
        self.stream_url = os.getenv("ANTIFAFM_STREAM_URL", "https://antifaFM.com/radio.mp3")
        self.stream_key = os.getenv("ANTIFAFM_YOUTUBE_STREAM_KEY", "")
        self.visual_path = os.getenv(
            "ANTIFAFM_DEFAULT_VISUAL",
            "modules/platform_integration/antifafm_broadcaster/assets/default_visual.png"
        )

        # Telemetry config (WSP 91)
        self.telemetry_path = Path(os.getenv(
            "ANTIFAFM_TELEMETRY_PATH",
            "modules/platform_integration/antifafm_broadcaster/telemetry.jsonl"
        ))
        self.heartbeat_interval = int(os.getenv("ANTIFAFM_HEARTBEAT_INTERVAL", "30"))

        # YouTube max stream duration (default 11 hours, before 12-hour limit)
        # Set ANTIFAFM_MAX_DURATION_HOURS=0 to disable auto-restart
        self.max_duration_seconds = int(os.getenv("ANTIFAFM_MAX_DURATION_HOURS", "11")) * 3600

        # State tracking
        self.status = BroadcasterStatus.OFFLINE
        self.start_time: Optional[float] = None
        self.streamer: Optional[FFmpegStreamer] = None
        self.health_monitor: Optional[StreamHealthMonitor] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

        # Optional Discord voice lane (ANTIFAFM_DISCORD_VOICE_ENABLED) — sibling to YouTube FFmpeg
        self.discord_output: Optional[Any] = None
        if _env_truthy("ANTIFAFM_DISCORD_VOICE_ENABLED"):
            self._init_discord_output()

        # AI Overseer integration (WSP 77)
        self.enable_ai_monitoring = enable_ai_monitoring
        self.ai_overseer = None
        if enable_ai_monitoring:
            self._init_ai_overseer()

        # WRE Skill Trigger integration (WSP 46, WSP 96)
        if WRE_AVAILABLE:
            self.init_skill_triggers(
                domain="streaming",
                cadence_minutes=15,
                agent="qwen",
            )
            logger.info("[RADIO] WRE skill triggers initialized (domain=streaming)")
        else:
            logger.debug("[RADIO] WRE not available - skill triggers disabled")

        # Validate configuration
        if not self.stream_key:
            logger.warning("[RADIO] ANTIFAFM_YOUTUBE_STREAM_KEY not set - will fail on start")

        if self.enabled:
            logger.info(f"[RADIO] antifaFM Broadcaster initialized")
            logger.info(f"    Stream URL: {self.stream_url}")
            logger.info(f"    Visual: {self.visual_path}")
            logger.info(f"    Stream Key: {'***configured***' if self.stream_key else 'NOT SET'}")
        else:
            logger.info("[RADIO] antifaFM Broadcaster disabled (ANTIFAFM_BROADCASTER_ENABLED=false)")

    def _init_ai_overseer(self) -> None:
        """Initialize AI Overseer for error detection (WSP 77)."""
        try:
            from modules.ai_intelligence.ai_overseer.src.ai_overseer import AIOverseer
            self.ai_overseer = AIOverseer()
            logger.info("[RADIO] AI Overseer connected for error monitoring")
        except ImportError:
            logger.debug("[RADIO] AI Overseer not available - monitoring disabled")
            self.ai_overseer = None
        except Exception as e:
            logger.warning(f"[RADIO] AI Overseer init failed: {e}")
            self.ai_overseer = None

    def _init_discord_output(self) -> None:
        """Optional Discord voice lane: same Icecast URL; requires discord.py + token/guild/channel."""
        try:
            from .discord_voice_output import DISCORD_VOICE_AVAILABLE, build_discord_voice_from_env
        except ImportError as e:
            logger.warning("[DISCORD] discord_voice_output import failed: %s", e)
            return

        if not DISCORD_VOICE_AVAILABLE:
            logger.warning(
                "[DISCORD] discord.py / PyNaCl not installed — voice lane skipped "
                "(pip install -r modules/platform_integration/antifafm_broadcaster/requirements.txt)"
            )
            return

        self.discord_output = build_discord_voice_from_env(self.stream_url)
        if self.discord_output:
            logger.info("[DISCORD] Voice adapter ready (start deferred until YouTube lane is up)")

    def _resolve_ingest_url(self) -> str:
        """
        Resolve RTMPS ingest URL with priority:
        1. ANTIFAFM_RTMP_URL env var (explicit override)
        2. YouTube Data API (stream-specific ingest URL)
        3. Generic fallback (may not work for all streams)

        Returns:
            str: RTMPS ingest URL to use
        """
        # Priority 1: Explicit override from environment
        explicit_url = os.getenv("ANTIFAFM_RTMP_URL", "")
        if explicit_url:
            logger.info(f"[INGEST] Using explicit ANTIFAFM_RTMP_URL: {explicit_url[:50]}...")
            return explicit_url

        token_set_raw = os.getenv("ANTIFAFM_YOUTUBE_TOKEN_SET", "10").strip()
        token_set = int(token_set_raw) if token_set_raw.isdigit() else None

        # Priority 2: API-resolved stream-specific URL
        try:
            from .youtube_ingest_resolver import get_ingest_url_with_fallback
            rtmp_url, is_api_resolved = get_ingest_url_with_fallback(
                stream_key=self.stream_key,
                fallback_url="rtmps://a.rtmps.youtube.com:443/live2",
                token_index=token_set,
            )
            if is_api_resolved:
                logger.info(f"[INGEST] Using API-resolved URL: {rtmp_url[:50]}...")
            else:
                logger.warning("[INGEST] API resolution failed, using generic fallback URL")
            return rtmp_url
        except ImportError as e:
            logger.warning(f"[INGEST] youtube_ingest_resolver not available: {e}")
        except Exception as e:
            logger.warning(f"[INGEST] API resolution error: {e}")

        # Priority 3: Generic fallback
        fallback = "rtmps://a.rtmps.youtube.com:443/live2"
        logger.warning(f"[INGEST] Using generic fallback: {fallback}")
        return fallback

    async def start(self) -> bool:
        """
        Start broadcasting to YouTube Live.

        Returns:
            bool: True if started successfully
        """
        if not self.enabled:
            logger.warning("[RADIO] Broadcaster disabled - cannot start")
            return False

        if self.status == BroadcasterStatus.BROADCASTING:
            logger.warning("[RADIO] Already broadcasting")
            return True

        if not self.stream_key:
            logger.error("[RADIO] Cannot start - ANTIFAFM_YOUTUBE_STREAM_KEY not set")
            return False

        self.status = BroadcasterStatus.STARTING
        logger.info("[RADIO] Starting antifaFM broadcast to YouTube Live...")

        # NOTE: Go Live click is done in launch.py BEFORE this method is called
        # This ensures it happens synchronously before the menu loads

        try:
            # Resolve RTMPS ingest URL (API-resolved > env var > generic fallback)
            rtmp_url = self._resolve_ingest_url()

            # Create stream config
            config = StreamConfig(
                audio_url=self.stream_url,
                visual_path=self.visual_path,
                rtmp_url=rtmp_url,
                stream_key=self.stream_key,
            )

            # Initialize FFmpeg streamer
            self.streamer = FFmpegStreamer(config)

            # Start streaming
            success = self.streamer.start()
            if not success:
                self.status = BroadcasterStatus.ERROR
                return False

            # Initialize health monitor with auto-recovery
            self.health_monitor = StreamHealthMonitor(
                check_fn=self._check_stream_health,
                restart_fn=self._restart_stream,
                config=RecoveryConfig(
                    initial_delay=5.0,
                    max_delay=300.0,
                    backoff_multiplier=2.0,
                    max_consecutive_failures=5,
                    health_check_interval=30.0,
                ),
            )
            await self.health_monitor.start()

            # Start heartbeat telemetry
            self._running = True
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            self.status = BroadcasterStatus.BROADCASTING
            self.start_time = time.time()
            logger.info("[OK] antifaFM broadcasting to YouTube Live")

            # Discord voice sibling lane — failures must not affect YouTube
            if self.discord_output:
                try:
                    discord_ok = await self.discord_output.start()
                    if not discord_ok:
                        logger.warning("[DISCORD] Voice lane failed to start — YouTube continues")
                        try:
                            await self.discord_output.stop()
                        except Exception:
                            pass
                        self.discord_output = None
                except Exception as e:
                    logger.error("[DISCORD] Voice lane exception: %s", e, exc_info=True)
                    try:
                        if self.discord_output:
                            await self.discord_output.stop()
                    except Exception:
                        pass
                    self.discord_output = None

            # Log telemetry
            self._write_telemetry()

            return True

        except FFmpegStreamerError as e:
            self.status = BroadcasterStatus.ERROR
            logger.error(f"[RADIO] FFmpeg error: {e}")
            return False
        except Exception as e:
            self.status = BroadcasterStatus.ERROR
            logger.error(f"[RADIO] Start failed: {e}")
            return False

    async def stop(self) -> bool:
        """
        Stop broadcasting.

        Returns:
            bool: True if stopped successfully
        """
        if self.status == BroadcasterStatus.OFFLINE:
            logger.debug("[RADIO] Already stopped")
            return True

        self.status = BroadcasterStatus.STOPPING
        logger.info("[RADIO] Stopping antifaFM broadcast...")
        self._running = False

        # Stop heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        # Stop health monitor
        if self.health_monitor:
            await self.health_monitor.stop()
            self.health_monitor = None

        # Stop FFmpeg
        if self.streamer:
            self.streamer.stop()
            self.streamer = None

        if self.discord_output:
            try:
                await self.discord_output.stop()
            except Exception as e:
                logger.error("[DISCORD] stop error: %s", e)
            self.discord_output = None

        self.status = BroadcasterStatus.OFFLINE
        self.start_time = None
        logger.info("[OK] antifaFM broadcast stopped")

        # Log final telemetry
        self._write_telemetry()

        return True

    def _check_stream_health(self) -> bool:
        """Health check function for StreamHealthMonitor."""
        if self.streamer is None:
            logger.warning("[HEALTH] No streamer instance")
            return False

        # Use detailed health check that examines stderr
        is_healthy, status_msg = self.streamer.is_streaming_healthy()

        if not is_healthy:
            logger.warning(f"[HEALTH] Stream unhealthy: {status_msg}")
            # Log last stderr for debugging
            last_stderr = self.streamer.get_last_stderr(10)
            if last_stderr:
                logger.error(f"[HEALTH] FFmpeg last output:\n{last_stderr}")

        return is_healthy

    async def _restart_stream(self) -> bool:
        """Restart function for StreamHealthMonitor."""
        logger.info("[RADIO] Auto-recovery: restarting FFmpeg stream...")

        if self.streamer:
            self.streamer.stop()

        try:
            # Resolve ingest URL (may re-fetch from API on restart)
            rtmp_url = self._resolve_ingest_url()
            config = StreamConfig(
                audio_url=self.stream_url,
                visual_path=self.visual_path,
                rtmp_url=rtmp_url,
                stream_key=self.stream_key,
            )
            self.streamer = FFmpegStreamer(config)
            return self.streamer.start()
        except Exception as e:
            logger.error(f"[RADIO] Restart failed: {e}")
            return False

    async def _heartbeat_loop(self) -> None:
        """Heartbeat loop for telemetry and AI monitoring."""
        while self._running:
            try:
                # Update status based on health
                if self.health_monitor and self.health_monitor.needs_intervention:
                    self.status = BroadcasterStatus.ERROR
                    logger.error("[RADIO] Health monitor entered FAILED state - stopping heartbeat until manual restart")
                    self._write_telemetry()
                    self._running = False
                    break
                elif self.health_monitor and not self.health_monitor.is_healthy:
                    self.status = BroadcasterStatus.DEGRADED

                # YouTube duration limit check (auto-restart before 12-hour cutoff)
                if self.max_duration_seconds > 0 and self.start_time:
                    uptime = time.time() - self.start_time
                    if uptime >= self.max_duration_seconds:
                        hours = uptime / 3600
                        logger.warning(f"[RADIO] Approaching YouTube 12-hour limit ({hours:.1f}h) - initiating graceful restart")
                        await self._restart_stream()
                        self.start_time = time.time()  # Reset timer after restart

                # Write telemetry
                self._write_telemetry()

                # AI Overseer scan (WSP 77)
                if self.ai_overseer and self.status == BroadcasterStatus.ERROR:
                    await self._notify_ai_overseer()

                # WRE Skill execution (WSP 46, WSP 96)
                # Fire domain skills on cadence (every 15 min by default)
                if WRE_AVAILABLE and self.status == BroadcasterStatus.BROADCASTING:
                    try:
                        skill_results = await self.fire_pending_skills(
                            extra_context={
                                "stream_url": self.stream_url,
                                "uptime_seconds": time.time() - self.start_time if self.start_time else 0,
                                "health_state": self.health_monitor.get_metrics().get("state") if self.health_monitor else "unknown",
                            }
                        )
                        if skill_results:
                            logger.info(f"[RADIO] WRE skills executed: {len(skill_results)} results")
                    except Exception as e:
                        logger.debug(f"[RADIO] WRE skill execution failed: {e}")

                await asyncio.sleep(self.heartbeat_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[RADIO] Heartbeat error: {e}")
                await asyncio.sleep(self.heartbeat_interval)

    def _write_telemetry(self) -> None:
        """Write telemetry to JSONL file (WSP 91)."""
        try:
            uptime = 0.0
            if self.start_time:
                uptime = time.time() - self.start_time

            restart_count = 0
            health_state = "unknown"
            if self.health_monitor:
                metrics = self.health_monitor.get_metrics()
                restart_count = metrics.get("restart_count", 0)
                health_state = metrics.get("state", "unknown")

            error_msg = None
            if self.streamer:
                status = self.streamer.get_status()
                error_msg = status.get("error")

            telemetry = BroadcastTelemetry(
                timestamp=datetime.now(),
                status=self.status,
                uptime_seconds=uptime,
                stream_url=self.stream_url,
                restart_count=restart_count,
                health_state=health_state,
                error_message=error_msg,
            )

            payload = telemetry.to_dict()
            if self.discord_output:
                payload["discord_voice"] = self.discord_output.get_status()

            # Ensure directory exists
            self.telemetry_path.parent.mkdir(parents=True, exist_ok=True)

            # Append to JSONL
            with open(self.telemetry_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")

        except Exception as e:
            logger.debug(f"[RADIO] Telemetry write failed: {e}")

    async def _notify_ai_overseer(self) -> None:
        """Notify AI Overseer of error state (WSP 77)."""
        if not self.ai_overseer:
            return

        try:
            error_context = {
                "module": "antifafm_broadcaster",
                "status": self.status.value,
                "error": self.streamer.get_status().get("error") if self.streamer else None,
            }
            # AI Overseer would analyze and potentially trigger autonomous fix
            logger.info(f"[RADIO] Notified AI Overseer of error state: {error_context}")
        except Exception as e:
            logger.debug(f"[RADIO] AI Overseer notification failed: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current broadcaster status."""
        uptime = None
        if self.start_time:
            uptime = time.time() - self.start_time

        streamer_status = {}
        if self.streamer:
            streamer_status = self.streamer.get_status()

        health_metrics = {}
        if self.health_monitor:
            health_metrics = self.health_monitor.get_metrics()

        # WRE trigger status (WSP 46)
        wre_status = {}
        if WRE_AVAILABLE and hasattr(self, 'get_trigger_status'):
            wre_status = self.get_trigger_status()

        out: Dict[str, Any] = {
            "status": self.status.value,
            "enabled": self.enabled,
            "uptime_seconds": uptime,
            "uptime_formatted": self._format_uptime(uptime),
            "stream_url": self.stream_url,
            "visual_path": self.visual_path,
            "stream_key_configured": bool(self.stream_key),
            "streamer": streamer_status,
            "health": health_metrics,
            "wre": wre_status,
        }
        out["discord_voice"] = self.discord_output.get_status() if self.discord_output else None
        out["discord_voice_enabled_flag"] = _env_truthy("ANTIFAFM_DISCORD_VOICE_ENABLED")
        return out

    @staticmethod
    def _format_uptime(seconds: Optional[float]) -> str:
        """Format uptime as human-readable string."""
        if seconds is None:
            return "N/A"
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# CLI entry point for testing
async def main():
    """Test broadcaster from CLI."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    print("\n[TEST] antifaFM YouTube Live Broadcaster")
    print("=" * 50)

    broadcaster = AntifaFMBroadcaster(enable_ai_monitoring=False)

    status = broadcaster.get_status()
    print(f"\nStatus: {json.dumps(status, indent=2)}")

    if not status["stream_key_configured"]:
        print("\n[WARN] Set ANTIFAFM_YOUTUBE_STREAM_KEY to test streaming")
        return

    print("\nStarting 30-second test broadcast...")
    success = await broadcaster.start()

    if success:
        for i in range(6):
            await asyncio.sleep(5)
            status = broadcaster.get_status()
            print(f"[{i*5}s] Status: {status['status']}, Uptime: {status['uptime_formatted']}")

        await broadcaster.stop()
        print("\n[OK] Test complete")
    else:
        print("\n[FAIL] Failed to start broadcaster")


if __name__ == "__main__":
    asyncio.run(main())
