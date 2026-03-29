# -*- coding: utf-8 -*-
"""
YouTube DAE Heartbeat Service - Health Monitoring + AI Overseer Integration

Provides:
1. Heartbeat monitoring for YouTube DAE operational status
2. Health check with metrics (uptime, memory, CPU, stream status)
3. JSONL telemetry for external monitoring (MCP servers, dashboards)
4. AI Overseer integration for proactive error detection
5. Self-healing via autonomous code patching

WSP Compliance:
- WSP 77: Agent Coordination (AI Overseer monitors heartbeat)
- WSP 91: DAEMON Observability (JSONL telemetry streaming)

Architecture:
  Heartbeat Loop (30s) → Metrics Collection → Health Check → AI Overseer Scan
  → Autonomous Fix (if needed) → Telemetry Write → Repeat
"""

import asyncio
import logging
import json
import os
import sys
from datetime import datetime
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from modules.communication.livechat.src.automation_gates import gate_snapshot

logger = logging.getLogger(__name__)


def _env_truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")


class HeartbeatStatus(Enum):
    """Health status indicators"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"

@dataclass
class YouTubeHeartbeatData:
    """Heartbeat pulse data"""
    timestamp: datetime
    status: HeartbeatStatus
    uptime_seconds: float
    stream_active: bool
    stream_video_id: Optional[str]
    memory_usage_mb: Optional[float]
    cpu_usage_percent: Optional[float]
    errors_detected: int
    fixes_applied: int

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "uptime_seconds": self.uptime_seconds,
            "stream_active": self.stream_active,
            "stream_video_id": self.stream_video_id,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "errors_detected": self.errors_detected,
            "fixes_applied": self.fixes_applied
        }

class YouTubeDAEHeartbeat:
    """
    YouTube DAE Heartbeat Service

    Monitors YouTube daemon health and integrates with AI Overseer
    for proactive error detection and autonomous fixing.
    """

    def __init__(
        self,
        dae_instance,
        heartbeat_interval: int = 30,
        enable_ai_overseer: bool = True
    ):
        """
        Initialize heartbeat service.

        Args:
            dae_instance: AutoModeratorDAE instance to monitor
            heartbeat_interval: Seconds between pulses (default: 30)
            enable_ai_overseer: Enable AI Overseer monitoring (default: True)
        """
        self.dae = dae_instance
        self.heartbeat_interval = heartbeat_interval
        self.enable_ai_overseer = enable_ai_overseer
        self.start_time = datetime.now()
        self.last_heartbeat = None
        self.pulse_count = 0
        self.running = False

        # AI Overseer integration
        self.ai_overseer = None
        self.overseer_skill_path = None
        if enable_ai_overseer:
            self._init_ai_overseer()

        # Health tracking
        self.health_history = []
        self.max_history_size = 100
        self.total_errors_detected = 0
        self.total_fixes_applied = 0

        logger.info(f"[HEARTBEAT] YouTube DAE Heartbeat initialized (interval: {heartbeat_interval}s, AI Overseer: {enable_ai_overseer})")

    def _init_ai_overseer(self):
        """Initialize AI Overseer for proactive monitoring"""
        try:
            from modules.ai_intelligence.ai_overseer.src.ai_overseer import AIIntelligenceOverseer

            # Initialize overseer
            # Navigate from: modules/communication/livechat/src/youtube_dae_heartbeat.py
            # To repo root: ../../../../ = O:/Foundups-Agent/
            repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
            self.ai_overseer = AIIntelligenceOverseer(repo_root)

            # Skill path for YouTube daemon monitoring
            self.overseer_skill_path = repo_root / "modules" / "communication" / "livechat" / "skillz" / "youtube_daemon_monitor.json"

            logger.info("[HEARTBEAT] AI Overseer connected - proactive monitoring enabled")

        except Exception as e:
            logger.warning(f"[HEARTBEAT] AI Overseer unavailable: {e}")
            self.enable_ai_overseer = False

    async def start_heartbeat(self):
        """Start the heartbeat monitoring loop"""
        self.running = True
        self.start_time = datetime.now()

        logger.info("[HEARTBEAT] YouTube DAE Heartbeat started")

        try:
            while self.running:
                await self._pulse()
                await asyncio.sleep(self.heartbeat_interval)
        except asyncio.CancelledError:
            logger.info("[HEARTBEAT] Heartbeat cancelled")
        except Exception as e:
            logger.error(f"[HEARTBEAT] Heartbeat error: {e}")
        finally:
            self.running = False
            logger.info("[HEARTBEAT] Heartbeat stopped")

    async def _pulse(self):
        """Generate a heartbeat pulse with health checks"""
        try:
            # Calculate uptime
            uptime = (datetime.now() - self.start_time).total_seconds()

            # Get system metrics
            memory_usage = self._get_memory_usage()
            cpu_usage = self._get_cpu_usage()

            # Get stream status
            stream_active = False
            stream_video_id = None
            if hasattr(self.dae, 'current_video_id'):
                stream_active = self.dae.current_video_id is not None
                stream_video_id = self.dae.current_video_id

            # AI Overseer proactive monitoring (if enabled)
            errors_detected = 0
            fixes_applied = 0
            if self.enable_ai_overseer and self.ai_overseer:
                overseer_result = await self._run_ai_overseer_check()
                errors_detected = overseer_result.get("bugs_detected", 0)
                fixes_applied = overseer_result.get("bugs_fixed", 0)

                self.total_errors_detected += errors_detected
                self.total_fixes_applied += fixes_applied

                # Check for rotation stalls and auto-trigger recovery (G1)
                stall_result = self.ai_overseer.check_rotation_stalls(minutes=5, auto_trigger=True)
                if stall_result.get("rotations_triggered", 0) > 0:
                    logger.info(f"[HEARTBEAT] Auto-triggered rotation recovery (PID: {stall_result.get('rotation_pid')})")

            # Determine health status
            status = self._calculate_health_status(
                uptime, memory_usage, cpu_usage, errors_detected
            )

            # Create heartbeat data
            heartbeat = YouTubeHeartbeatData(
                timestamp=datetime.now(),
                status=status,
                uptime_seconds=uptime,
                stream_active=stream_active,
                stream_video_id=stream_video_id,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage,
                errors_detected=errors_detected,
                fixes_applied=fixes_applied
            )

            # Store heartbeat
            self.last_heartbeat = heartbeat
            self.pulse_count += 1

            # Add to history
            self.health_history.append(heartbeat)
            if len(self.health_history) > self.max_history_size:
                self.health_history.pop(0)

            # Write telemetry
            await self._write_telemetry(heartbeat)

            # Log pulse (reduced frequency)
            if self.pulse_count % 10 == 0:
                logger.info(f"[HEARTBEAT] Pulse #{self.pulse_count} - Status: {status.value}")
                logger.info(f"  Uptime: {uptime:.0f}s | Stream: {stream_video_id or 'None'}")
                logger.info(f"  Total: {self.total_errors_detected} errors, {self.total_fixes_applied} fixes")

        except Exception as e:
            logger.error(f"[HEARTBEAT] Pulse failed: {e}")
            # Create error heartbeat
            self.last_heartbeat = YouTubeHeartbeatData(
                timestamp=datetime.now(),
                status=HeartbeatStatus.CRITICAL,
                uptime_seconds=(datetime.now() - self.start_time).total_seconds(),
                stream_active=False,
                stream_video_id=None,
                memory_usage_mb=None,
                cpu_usage_percent=None,
                errors_detected=0,
                fixes_applied=0
            )

    async def _run_ai_overseer_check(self) -> Dict:
        """
        Run AI Overseer proactive health check.

        Reads recent daemon logs and passes to AI Overseer for autonomous
        error detection and fixing.
        """
        try:
            if not self.ai_overseer or not self.overseer_skill_path:
                return {"bugs_detected": 0, "bugs_fixed": 0, "fixes_applied": []}

            # Read recent daemon telemetry from YouTube DAE's internal logs
            # In production: This would read from actual daemon stdout/stderr
            # For now: Check recent JSONL telemetry for error patterns
            bash_output = await self._get_recent_daemon_logs()

            if not bash_output:
                # No recent logs - daemon healthy
                return {"bugs_detected": 0, "bugs_fixed": 0, "fixes_applied": []}

            # Call AI Overseer with daemon output (synchronous call)
            # Pass THROTTLED chat_sender from DAE instance for live announcements (012's vision!)
            chat_sender = None
            announce_to_chat = False
            if hasattr(self.dae, 'livechat') and self.dae.livechat is not None:
                # Use livechat_core's throttled send_chat_message instead of raw chat_sender
                if hasattr(self.dae.livechat, 'send_chat_message'):
                    # Create a wrapper that uses the throttled send_chat_message
                    class ThrottledChatSender:
                        def __init__(self, livechat_core):
                            self.livechat_core = livechat_core

                        async def send_message(self, message_text: str, response_type: str = 'general', skip_delay: bool = False):
                            """Send message through throttled livechat_core instead of raw chat_sender"""
                            return await self.livechat_core.send_chat_message(
                                message_text=message_text,
                                skip_delay=skip_delay,  # Still allow skip_delay for priority messages
                                response_type=response_type
                            )

                    chat_sender = ThrottledChatSender(self.dae.livechat)
                    announce_to_chat = True
                    logger.debug("[HEARTBEAT] Throttled chat sender available - live announcements ENABLED with intelligent throttling")

            result = self.ai_overseer.monitor_daemon(
                bash_output=bash_output,
                skill_path=self.overseer_skill_path,
                auto_fix=True,  # Enable autonomous fixing
                chat_sender=chat_sender,  # Wire up DAE chat_sender for live announcements
                announce_to_chat=announce_to_chat  # Enable when chat_sender available
            )

            # Log results
            if result.get("bugs_detected", 0) > 0:
                logger.info(f"[HEARTBEAT] AI Overseer detected {result['bugs_detected']} errors")

            if result.get("bugs_fixed", 0) > 0:
                logger.info(f"[HEARTBEAT] AI Overseer applied {result['bugs_fixed']} autonomous fixes")

                # Check if restart needed
                for fix in result.get("fixes_applied", []):
                    if fix.get("needs_restart"):
                        logger.warning("[HEARTBEAT] Fix requires daemon restart - will apply on next restart cycle")

            return result

        except Exception as e:
            logger.error(f"[HEARTBEAT] AI Overseer check failed: {e}")
            return {"bugs_detected": 0, "bugs_fixed": 0, "fixes_applied": []}

    async def _get_recent_daemon_logs(self) -> Optional[str]:
        """
        Get recent daemon logs for AI Overseer analysis.

        Reads from Python logging system to capture all module logs including chat_sender.
        """
        try:
            # Read from Python log file (foundups_agent.log captures all module logs)
            log_file = Path("logs/foundups_agent.log")

            if not log_file.exists():
                logger.debug("[HEARTBEAT] No log file found at logs/foundups_agent.log")
                return None

            # Read last 200 lines (should cover recent chat messages and errors)
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                # Seek to end and read backwards for efficiency
                f.seek(0, 2)  # Seek to end
                file_size = f.tell()

                # Read last ~50KB (approximately 200-500 log lines)
                read_size = min(50000, file_size)
                f.seek(max(0, file_size - read_size))

                # Skip partial first line
                if file_size > read_size:
                    f.readline()

                recent_logs = f.read()

            return recent_logs if recent_logs.strip() else None

        except Exception as e:
            logger.error(f"[HEARTBEAT] Failed to read daemon logs: {e}")
            return None

    async def _write_telemetry(self, heartbeat: YouTubeHeartbeatData):
        """
        Write heartbeat telemetry to JSONL for streaming observability.

        WSP 91: DAEMON Observability Protocol
        """
        try:
            # Telemetry file path
            telemetry_file = Path("logs/youtube_dae_heartbeat.jsonl")
            telemetry_file.parent.mkdir(parents=True, exist_ok=True)

            payload = heartbeat.to_dict()
            run_id = os.getenv("YT_AUTOMATION_RUN_ID", "").strip()
            payload["run_id"] = run_id or None
            payload["automation_gates"] = gate_snapshot()

            # Write as JSONL (one JSON object per line)
            with open(telemetry_file, 'a', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False)
                f.write('\n')

        except Exception as e:
            # Don't crash heartbeat on telemetry errors
            logger.error(f"[HEARTBEAT] Telemetry write failed: {e}")

    def _calculate_health_status(
        self,
        uptime: float,
        memory_mb: Optional[float],
        cpu_percent: Optional[float],
        errors_detected: int
    ) -> HeartbeatStatus:
        """Calculate health status from metrics"""

        status = HeartbeatStatus.HEALTHY

        # Check for warning conditions
        if memory_mb and memory_mb > 500:  # Over 500MB
            status = HeartbeatStatus.WARNING

        if cpu_percent and cpu_percent > 70:  # Over 70% CPU
            status = HeartbeatStatus.WARNING

        # Check for critical conditions
        if errors_detected > 0:  # Active errors detected
            status = HeartbeatStatus.CRITICAL

        if uptime < 60:  # Recently restarted
            status = HeartbeatStatus.WARNING

        return status

    def _get_memory_usage(self) -> Optional[float]:
        """Get memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except (ImportError, Exception):
            return None

    def _get_cpu_usage(self) -> Optional[float]:
        """Get CPU usage percentage"""
        try:
            import psutil
            return psutil.Process().cpu_percent()
        except (ImportError, Exception):
            return None

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status for external monitoring"""
        if not self.last_heartbeat:
            return {
                "status": "offline",
                "message": "No heartbeat data available"
            }

        return {
            "status": self.last_heartbeat.status.value,
            "last_pulse": self.last_heartbeat.timestamp.isoformat(),
            "uptime_seconds": self.last_heartbeat.uptime_seconds,
            "pulse_count": self.pulse_count,
            "stream_active": self.last_heartbeat.stream_active,
            "stream_video_id": self.last_heartbeat.stream_video_id,
            "memory_usage_mb": self.last_heartbeat.memory_usage_mb,
            "cpu_usage_percent": self.last_heartbeat.cpu_usage_percent,
            "total_errors_detected": self.total_errors_detected,
            "total_fixes_applied": self.total_fixes_applied,
            "health_history_size": len(self.health_history)
        }

    def stop_heartbeat(self):
        """Stop the heartbeat service"""
        logger.info("[HEARTBEAT] Stopping YouTube DAE Heartbeat...")
        self.running = False


# Convenience function
async def start_youtube_dae_with_heartbeat(
    dae_instance,
    heartbeat_interval: int = 30,
    enable_ai_overseer: bool = True
) -> YouTubeDAEHeartbeat:
    """
    Start YouTube DAE with heartbeat monitoring.

    Args:
        dae_instance: AutoModeratorDAE instance
        heartbeat_interval: Seconds between pulses
        enable_ai_overseer: Enable AI Overseer monitoring

    Returns:
        YouTubeDAEHeartbeat instance
    """
    logger.info("[HEARTBEAT] Starting YouTube DAE with Heartbeat + AI Overseer")

    # Create heartbeat service
    heartbeat = YouTubeDAEHeartbeat(
        dae_instance,
        heartbeat_interval=heartbeat_interval,
        enable_ai_overseer=enable_ai_overseer
    )

    # Start heartbeat in background
    asyncio.create_task(heartbeat.start_heartbeat())

    logger.info("[HEARTBEAT] YouTube DAE Heartbeat started successfully")

    return heartbeat
