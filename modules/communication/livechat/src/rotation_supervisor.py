"""
Agentic Rotation Supervisor - Task-Based Channel Rotation
==========================================================

WSP 77 Compliant: Agent coordination via discrete task supervision.

ARCHITECTURE (Unix Philosophy):
  - Each operation (comments, shorts, indexing) is a discrete CLI task
  - Supervisor spawns task → pings heartbeat → rotates on completion/timeout
  - No complex async nesting - just spawn/monitor/rotate

FLOW:
  ┌─────────────────────────────────────────────────────────────────┐
  │  RotationSupervisor                                             │
  │    └─ for channel in channels:                                  │
  │         task = spawn_task(channel, operation_type)              │
  │         while not task.done:                                    │
  │             if heartbeat_stale(30s): kill → rotate              │
  │             await ping(5s)                                      │
  │         signal_channel_complete(channel)                        │
  │    signal_rotation_complete()                                   │
  └─────────────────────────────────────────────────────────────────┘

KEY DIFFERENCE FROM PREVIOUS:
  - Old: Sequential async calls that can hang indefinitely
  - New: Subprocess tasks with heartbeat monitoring and kill capability

Usage:
    supervisor = RotationSupervisor(browser="edge")
    await supervisor.run_rotation(
        channels=["FoundUps", "antifaFM"],
        operation="comments",
        timeout_per_channel=300  # 5 min per channel (not 1 hour!)
    )

Author: 0102
Created: 2026-02-27
Updated: 2026-03-30 (Phase 2: G5 cycle watchdog + G3 channel operation tracking)
WSP: 77 (Agent Coordination), 91 (Observability)
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from modules.infrastructure.shared_utilities.youtube_channel_registry import (
    get_channels,
    group_channels_by_browser,
)
from modules.communication.livechat.src.rotation_checkpoint import (
    save_checkpoint,
    load_checkpoint,
    clear_checkpoint,
    get_remaining_channels,
)

logger = logging.getLogger(__name__)

# =============================================================================
# G5: Cycle Watchdog Constants (Phase 2)
# =============================================================================
# Maximum duration for entire rotation cycle before emitting stall breadcrumb.
# This is a sentinel-queryable raw fact - AI Overseer interprets severity.
MAX_CYCLE_DURATION_HOURS = float(os.getenv("YT_MAX_CYCLE_DURATION_HOURS", "2.0"))

# =============================================================================
# G6: Escalation Threshold Constants (Phase 3)
# =============================================================================
# Consecutive failure count that triggers human_intervention_required breadcrumb.
# Uses Phase 2 consecutive_failures from youtube_channel_operations table.
ESCALATION_FAILURE_THRESHOLD = int(os.getenv("YT_ESCALATION_FAILURE_THRESHOLD", "3"))


class OperationType(Enum):
    """Discrete operations that can be rotated."""
    COMMENTS = "comments"
    SHORTS = "shorts"
    INDEXING = "indexing"
    LIVE_CHAT = "live_chat"


class TaskState(Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    FAILED = "failed"
    KILLED = "killed"


@dataclass
class TaskHeartbeat:
    """Heartbeat tracking for a running task."""
    task_id: str
    channel: str
    operation: OperationType
    started_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    comments_processed: int = 0
    state: TaskState = TaskState.PENDING
    pid: Optional[int] = None
    error: Optional[str] = None

    def update_heartbeat(self, comments: int = 0):
        """Update heartbeat timestamp and progress."""
        self.last_heartbeat = time.time()
        self.comments_processed = comments

    def is_stale(self, threshold_seconds: float = 30.0) -> bool:
        """Check if heartbeat is stale (no update in threshold)."""
        return (time.time() - self.last_heartbeat) > threshold_seconds

    def elapsed(self) -> float:
        """Seconds since task started."""
        return time.time() - self.started_at

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging/telemetry."""
        return {
            "task_id": self.task_id,
            "channel": self.channel,
            "operation": self.operation.value,
            "state": self.state.value,
            "elapsed_seconds": round(self.elapsed(), 1),
            "heartbeat_age": round(time.time() - self.last_heartbeat, 1),
            "comments_processed": self.comments_processed,
            "pid": self.pid,
            "error": self.error,
        }


@dataclass
class RotationResult:
    """Result of a full rotation cycle."""
    browser: str
    channels_processed: List[str]
    total_comments: int
    total_scheduled: int
    failed_channels: List[str]
    elapsed_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "browser": self.browser,
            "channels_processed": self.channels_processed,
            "total_comments": self.total_comments,
            "total_scheduled": self.total_scheduled,
            "failed_channels": self.failed_channels,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
        }


class RotationSupervisor:
    """
    Agentic supervisor for channel rotation.

    Spawns discrete CLI tasks, monitors heartbeats, and rotates on completion/timeout.
    This replaces the complex nested async loops in multi_channel_coordinator.
    """

    # CLI entry points for each operation type
    CLI_COMMANDS = {
        OperationType.COMMENTS: [
            sys.executable, "-m",
            "modules.communication.video_comments.skillz.tars_like_heart_reply.run_skill"
        ],
        OperationType.SHORTS: [
            sys.executable, "-m",
            "modules.platform_integration.youtube_shorts_scheduler.src.scheduler"
        ],
        OperationType.INDEXING: [
            sys.executable, "-m",
            "modules.ai_intelligence.video_indexer.src.studio_ask_indexer"
        ],
    }

    # Browser port mapping
    BROWSER_PORTS = {
        "chrome": 9222,
        "edge": 9223,
    }

    def __init__(
        self,
        browser: str = "chrome",
        heartbeat_interval: float = 5.0,
        heartbeat_timeout: float = 60.0,
        task_timeout: float = 300.0,  # 5 min per channel (NOT 1 hour!)
    ):
        """
        Initialize rotation supervisor.

        Args:
            browser: "chrome" or "edge"
            heartbeat_interval: Seconds between heartbeat checks
            heartbeat_timeout: Seconds without heartbeat before killing task
            task_timeout: Max seconds per channel task (hard timeout)
        """
        self.browser = browser
        self.browser_port = self.BROWSER_PORTS.get(browser, 9222)
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.task_timeout = task_timeout

        self._active_tasks: Dict[str, TaskHeartbeat] = {}
        self._rotation_id = f"rot_{int(time.time())}"

        # Heartbeat file for subprocess communication
        self._heartbeat_dir = Path(os.getenv("TEMP", "/tmp")) / "yt_rotation_heartbeats"
        self._heartbeat_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"[SUPERVISOR] Initialized for {browser} (port {self.browser_port})")
        logger.info(f"[SUPERVISOR] Timeouts: heartbeat={heartbeat_timeout}s, task={task_timeout}s")

    def _get_channels_for_browser(self) -> List[str]:
        """Get channels assigned to this browser."""
        return [
            str(channel.get("name", "")).strip()
            for channel in group_channels_by_browser(role="comments").get(self.browser, [])
            if channel.get("name")
        ]

    def _record_channel_op(self, channel: str, operation: str, success: bool = True) -> None:
        """
        G3: Record channel operation timestamp for sentinel tracking.

        Lazy import to avoid circular dependencies. This persists raw facts
        (timestamps, success/failure) for AI Overseer to query - no derived
        classifications are stored here.

        Args:
            channel: Channel name (resolved to ID via registry)
            operation: Operation type (comments, shorts, indexing)
            success: Whether operation completed successfully
        """
        try:
            from modules.communication.livechat.src.youtube_telemetry_store import YouTubeTelemetryStore
            channel_id = self._resolve_channel_id(channel)
            store = YouTubeTelemetryStore()
            store.record_channel_operation(
                channel_id=channel_id,
                channel_name=channel,
                operation=operation,
                success=success,
            )
        except Exception as e:
            # Non-critical - don't fail rotation for telemetry errors
            logger.debug(f"[SUPERVISOR] Failed to record channel operation: {e}")

    def _resolve_channel_id(self, channel: str) -> str:
        """Resolve a channel name/key/id to the canonical registry channel ID."""
        for registry_channel in get_channels(role="comments"):
            name = str(registry_channel.get("name", "")).strip().lower()
            key = str(registry_channel.get("key", "")).strip().lower()
            channel_id = str(registry_channel.get("id", "")).strip()
            token = str(channel).strip().lower()
            if token in {name, key, channel_id.lower()} and channel_id:
                return channel_id
        return channel

    def _check_escalation(self, operation: str) -> None:
        """
        G6: Check for channels requiring human intervention.

        Queries Phase 2 consecutive_failures and emits human_intervention_required
        breadcrumb when threshold exceeded. This is the escalation path for
        repeatedly failing channels.

        Args:
            operation: Operation type that just completed (for context)
        """
        try:
            from modules.communication.livechat.src.youtube_telemetry_store import YouTubeTelemetryStore
            store = YouTubeTelemetryStore()

            # Query channels with high consecutive failures
            # Use get_stale_channels with large window to get all tracked channels
            stale = store.get_stale_channels(operation=operation, max_age_hours=24 * 30)

            escalation_channels = [
                ch for ch in stale
                if ch.get("consecutive_failures", 0) >= ESCALATION_FAILURE_THRESHOLD
            ]

            if not escalation_channels:
                return

            # Emit escalation breadcrumb for AI Overseer
            from modules.communication.livechat.src.breadcrumb_telemetry import get_breadcrumb_telemetry
            telemetry = get_breadcrumb_telemetry()

            for ch in escalation_channels:
                telemetry.store_breadcrumb(
                    source_dae="rotation_supervisor",
                    event_type="human_intervention_required",
                    message=f"Channel {ch.get('channel_name', ch.get('channel_id'))} requires human intervention",
                    phase="ESCALATION",
                    metadata={
                        "channel_id": ch.get("channel_id"),
                        "channel_name": ch.get("channel_name"),
                        "consecutive_failures": ch.get("consecutive_failures", 0),
                        "operation": operation,
                        "threshold": ESCALATION_FAILURE_THRESHOLD,
                        "action": "human_intervention_required",
                        "hours_stale": ch.get("hours_stale"),
                    },
                )
                logger.warning(
                    f"[SUPERVISOR] ESCALATION: {ch.get('channel_name')} has "
                    f"{ch.get('consecutive_failures')} consecutive failures (threshold: {ESCALATION_FAILURE_THRESHOLD})"
                )

        except Exception as e:
            # Non-critical - don't fail rotation for escalation check errors
            logger.debug(f"[SUPERVISOR] Escalation check failed: {e}")

    def _build_task_command(
        self,
        channel: str,
        operation: OperationType,
        max_items: int = 10,
    ) -> List[str]:
        """Build CLI command for a specific task."""
        base_cmd = self.CLI_COMMANDS.get(operation, [])
        if not base_cmd:
            raise ValueError(f"Unknown operation: {operation}")

        channel_id = self._resolve_channel_id(channel)
        task_id = f"{self._rotation_id}_{channel}_{operation.value}"
        heartbeat_file = self._heartbeat_dir / f"{task_id}.json"

        cmd = list(base_cmd)

        if operation == OperationType.COMMENTS:
            cmd.extend([
                "--channel", channel_id,
                "--max-comments", str(max_items),
                "--browser-port", str(self.browser_port),
                "--heartbeat-file", str(heartbeat_file),  # For progress reporting
                "--profile", "full",  # Like + Heart + Reply
            ])
        elif operation == OperationType.SHORTS:
            cmd.extend([
                "--channel", channel.lower(),
                "--max", str(max_items),
                "--heartbeat-file", str(heartbeat_file),
            ])
        elif operation == OperationType.INDEXING:
            cmd.extend([
                "--channel", channel_id,
                "--heartbeat-file", str(heartbeat_file),
            ])

        return cmd, task_id, heartbeat_file

    async def _spawn_task(
        self,
        channel: str,
        operation: OperationType,
        max_items: int = 10,
    ) -> TaskHeartbeat:
        """Spawn a CLI task and return heartbeat tracker."""
        cmd, task_id, heartbeat_file = self._build_task_command(channel, operation, max_items)

        heartbeat = TaskHeartbeat(
            task_id=task_id,
            channel=channel,
            operation=operation,
            state=TaskState.RUNNING,
        )

        # Clean up old heartbeat file
        if heartbeat_file.exists():
            heartbeat_file.unlink()

        logger.info(f"[SUPERVISOR] Spawning task: {task_id}")
        logger.debug(f"[SUPERVISOR] Command: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(Path(__file__).parent.parent.parent.parent.parent),
            )
            heartbeat.pid = process.pid
            logger.info(f"[SUPERVISOR] Task spawned (PID: {process.pid})")

            # Store process reference for killing
            heartbeat._process = process
            heartbeat._heartbeat_file = heartbeat_file

        except Exception as e:
            heartbeat.state = TaskState.FAILED
            heartbeat.error = str(e)
            logger.error(f"[SUPERVISOR] Failed to spawn task: {e}")

        self._active_tasks[task_id] = heartbeat
        return heartbeat

    async def _read_heartbeat_file(self, heartbeat: TaskHeartbeat) -> bool:
        """Read heartbeat progress from file (subprocess writes this)."""
        heartbeat_file = getattr(heartbeat, '_heartbeat_file', None)
        if not heartbeat_file or not heartbeat_file.exists():
            return False

        try:
            data = json.loads(heartbeat_file.read_text())
            heartbeat.update_heartbeat(comments=data.get("comments_processed", 0))
            return True
        except Exception:
            return False

    async def _monitor_task(self, heartbeat: TaskHeartbeat) -> TaskState:
        """
        Monitor a running task until completion, timeout, or stale heartbeat.

        Returns final TaskState.
        """
        process = getattr(heartbeat, '_process', None)
        if not process:
            return TaskState.FAILED

        start_time = time.time()

        while True:
            # Check if process completed
            if process.returncode is not None:
                elapsed = time.time() - start_time
                if process.returncode == 0:
                    heartbeat.state = TaskState.COMPLETED
                    logger.info(f"[SUPERVISOR] Task completed: {heartbeat.channel} ({elapsed:.1f}s)")
                else:
                    heartbeat.state = TaskState.FAILED
                    heartbeat.error = f"Exit code {process.returncode}"
                    logger.warning(f"[SUPERVISOR] Task failed: {heartbeat.channel} (exit={process.returncode})")
                return heartbeat.state

            # Check hard timeout
            elapsed = time.time() - start_time
            if elapsed > self.task_timeout:
                logger.warning(f"[SUPERVISOR] Task TIMEOUT: {heartbeat.channel} ({elapsed:.1f}s > {self.task_timeout}s)")
                await self._kill_task(heartbeat)
                heartbeat.state = TaskState.TIMEOUT
                return TaskState.TIMEOUT

            # Read heartbeat file for progress
            await self._read_heartbeat_file(heartbeat)

            # Check heartbeat staleness (soft timeout)
            if heartbeat.is_stale(self.heartbeat_timeout):
                age = time.time() - heartbeat.last_heartbeat
                logger.warning(f"[SUPERVISOR] Heartbeat STALE: {heartbeat.channel} ({age:.1f}s > {self.heartbeat_timeout}s)")
                logger.warning(f"[SUPERVISOR] Task appears hung - killing and rotating")
                await self._kill_task(heartbeat)
                heartbeat.state = TaskState.KILLED
                return TaskState.KILLED

            # Log progress
            if int(elapsed) % 30 == 0 and elapsed > 0:  # Every 30s
                logger.info(f"[SUPERVISOR] {heartbeat.channel}: {heartbeat.comments_processed} processed, {elapsed:.0f}s elapsed")

            # Wait before next ping
            try:
                await asyncio.wait_for(
                    process.wait(),
                    timeout=self.heartbeat_interval,
                )
                # Process completed during wait
                continue
            except asyncio.TimeoutError:
                # Expected - process still running, continue loop
                pass

    async def _kill_task(self, heartbeat: TaskHeartbeat):
        """Forcefully terminate a hung task."""
        process = getattr(heartbeat, '_process', None)
        if not process:
            return

        pid = heartbeat.pid
        logger.info(f"[SUPERVISOR] Killing task (PID: {pid})")

        try:
            process.terminate()
            await asyncio.sleep(2)
            if process.returncode is None:
                process.kill()
                logger.info(f"[SUPERVISOR] Task killed (SIGKILL)")
        except ProcessLookupError:
            logger.debug(f"[SUPERVISOR] Process already exited")
        except Exception as e:
            logger.error(f"[SUPERVISOR] Kill failed: {e}")

    async def run_rotation(
        self,
        operation: OperationType = OperationType.COMMENTS,
        channels: List[str] = None,
        max_items_per_channel: int = 10,
    ) -> RotationResult:
        """
        Run a full rotation cycle for all channels.

        This is the main entry point. Replaces the complex nested loops
        in multi_channel_coordinator with clean spawn/monitor/rotate.

        Args:
            operation: Which operation to run (comments, shorts, indexing)
            channels: List of channel names (None = auto-detect from browser)
            max_items_per_channel: Max items to process per channel

        Returns:
            RotationResult with stats
        """
        if channels is None:
            channels = self._get_channels_for_browser()

        rotation_start = time.time()
        cycle_started_at = datetime.utcnow().isoformat()

        # G2: Load checkpoint for crash recovery
        checkpoint = load_checkpoint()
        if checkpoint and checkpoint.get("browser") == self.browser and checkpoint.get("operation") == operation.value:
            # Resume from checkpoint
            channels = get_remaining_channels(channels, checkpoint)
            cycle_started_at = checkpoint.get("cycle_started_at", cycle_started_at)

        channels_processed = []
        failed_channels = []
        total_comments = 0
        total_scheduled = 0

        tag = self.browser.upper()
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"[{tag}-ROTATION] STARTING: {operation.value}")
        logger.info(f"[{tag}-ROTATION] Channels: {channels}")
        logger.info(f"[{tag}-ROTATION] Timeout: {self.task_timeout}s per channel")
        logger.info("=" * 60)

        for idx, channel in enumerate(channels, 1):
            # G5: Cycle watchdog - check if cycle has exceeded max duration
            elapsed_hours = (time.time() - rotation_start) / 3600
            if elapsed_hours > MAX_CYCLE_DURATION_HOURS:
                logger.error(f"[{tag}-ROTATION] Cycle exceeded {MAX_CYCLE_DURATION_HOURS}h ({elapsed_hours:.2f}h) - emitting stall")
                try:
                    from modules.communication.livechat.src.breadcrumb_telemetry import get_breadcrumb_telemetry
                    telemetry = get_breadcrumb_telemetry()
                    telemetry.store_breadcrumb(
                        source_dae="rotation_supervisor",
                        event_type="rotation_cycle_stalled",
                        message=f"{tag} rotation cycle exceeded max duration",
                        phase=operation.value.upper(),
                        metadata={
                            "browser": self.browser,
                            "operation": operation.value,
                            "cycle_started_at": cycle_started_at,
                            "elapsed_hours": round(elapsed_hours, 2),
                            "max_hours": MAX_CYCLE_DURATION_HOURS,
                            "channels_processed": len(channels_processed),
                            "channels_remaining": len(channels) - idx + 1,
                            "failed_channels": failed_channels,
                        },
                    )
                except Exception as e:
                    logger.warning(f"[{tag}-ROTATION] Failed to emit stall breadcrumb: {e}")
                break  # Exit rotation loop

            logger.info("")
            logger.info(f"[{tag}-ROTATION] [{idx}/{len(channels)}] {channel}")
            logger.info("-" * 40)

            # Spawn task
            heartbeat = await self._spawn_task(channel, operation, max_items_per_channel)

            if heartbeat.state == TaskState.FAILED:
                failed_channels.append(channel)
                logger.error(f"[{tag}-ROTATION] {channel} FAILED to spawn: {heartbeat.error}")
                continue

            # Monitor until done/timeout/killed
            final_state = await self._monitor_task(heartbeat)

            if final_state in (TaskState.COMPLETED,):
                channels_processed.append(channel)
                total_comments += heartbeat.comments_processed
                logger.info(f"[{tag}-ROTATION] {channel} COMPLETE: {heartbeat.comments_processed} processed")
                # G3: Record successful channel operation for sentinel tracking
                self._record_channel_op(channel, operation.value, success=True)
            elif final_state in (TaskState.TIMEOUT, TaskState.KILLED):
                failed_channels.append(channel)
                logger.warning(f"[{tag}-ROTATION] {channel} {final_state.value}: rotating to next")
                # G3: Record failed channel operation for sentinel tracking
                self._record_channel_op(channel, operation.value, success=False)
            else:
                failed_channels.append(channel)
                logger.error(f"[{tag}-ROTATION] {channel} {final_state.value}: {heartbeat.error}")
                # G3: Record failed channel operation for sentinel tracking
                self._record_channel_op(channel, operation.value, success=False)

            # Clean up
            if heartbeat.task_id in self._active_tasks:
                del self._active_tasks[heartbeat.task_id]

            # G2: Save checkpoint after each channel for crash recovery
            save_checkpoint(
                browser=self.browser,
                processed_channels=set(channels_processed),
                current_channel=None,
                operation=operation.value,
                cycle_started_at=cycle_started_at,
            )

        elapsed = time.time() - rotation_start

        # Build result
        result = RotationResult(
            browser=self.browser,
            channels_processed=channels_processed,
            total_comments=total_comments,
            total_scheduled=total_scheduled,
            failed_channels=failed_channels,
            elapsed_seconds=elapsed,
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"[{tag}-ROTATION] COMPLETE")
        logger.info(f"[{tag}-ROTATION] Channels: {len(channels_processed)}/{len(channels)} successful")
        logger.info(f"[{tag}-ROTATION] Comments: {total_comments}")
        logger.info(f"[{tag}-ROTATION] Time: {elapsed:.1f}s")
        if failed_channels:
            logger.warning(f"[{tag}-ROTATION] Failed: {failed_channels}")
        logger.info("=" * 60)

        # G2: Clear checkpoint after successful rotation
        clear_checkpoint()

        # G3: Record rotation success for all processed channels
        # This tracks "when was this channel last part of a successful rotation cycle"
        for channel in channels_processed:
            self._record_channel_op(channel, "rotation", success=True)

        # Emit breadcrumb for activity routing
        try:
            from modules.communication.livechat.src.breadcrumb_telemetry import get_breadcrumb_telemetry
            telemetry = get_breadcrumb_telemetry()
            telemetry.store_breadcrumb(
                source_dae="rotation_supervisor",
                event_type="rotation_complete",
                message=f"{tag} rotation complete: {len(channels_processed)}/{len(channels)} channels",
                phase=operation.value.upper(),
                metadata=result.to_dict(),
            )
        except Exception:
            pass

        # G6: Check for channels requiring escalation (Phase 3)
        self._check_escalation(operation.value)

        return result

    async def run_full_cycle(
        self,
        operations: List[OperationType] = None,
        max_comments: int = 10,
        max_shorts: int = 5,
    ) -> Dict[str, RotationResult]:
        """
        Run a full cycle: Comments → Shorts → (Indexing).

        This replaces _browser_engagement_loop in auto_moderator_dae.
        """
        if operations is None:
            operations = [OperationType.COMMENTS]
            if os.getenv("YT_SHORTS_SCHEDULING_ENABLED", "true").lower() in ("1", "true", "yes"):
                operations.append(OperationType.SHORTS)

        results = {}

        for op in operations:
            max_items = max_comments if op == OperationType.COMMENTS else max_shorts
            result = await self.run_rotation(operation=op, max_items_per_channel=max_items)
            results[op.value] = result

        return results


# =============================================================================
# HEARTBEAT FILE HELPER (for subprocesses to report progress)
# =============================================================================

def write_heartbeat(heartbeat_file: str, comments_processed: int = 0, **kwargs):
    """
    Write heartbeat file from subprocess.

    Call this periodically from run_skill.py to report progress.
    The supervisor reads this file to detect hangs.

    Usage in subprocess:
        from modules.communication.livechat.src.rotation_supervisor import write_heartbeat
        write_heartbeat(args.heartbeat_file, comments_processed=count)
    """
    if not heartbeat_file:
        return

    try:
        data = {
            "timestamp": time.time(),
            "comments_processed": comments_processed,
            **kwargs,
        }
        Path(heartbeat_file).write_text(json.dumps(data))
    except Exception:
        pass  # Non-critical


# =============================================================================
# STANDALONE ENTRY POINT
# =============================================================================

async def main():
    """CLI entry point for testing rotation supervisor."""
    import argparse

    parser = argparse.ArgumentParser(description="Agentic Rotation Supervisor")
    parser.add_argument("--browser", default="edge", choices=["chrome", "edge"])
    parser.add_argument("--operation", default="comments", choices=["comments", "shorts", "indexing"])
    parser.add_argument("--max-items", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=300, help="Per-channel timeout (seconds)")
    parser.add_argument("--heartbeat-timeout", type=int, default=60, help="Heartbeat stale threshold")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    supervisor = RotationSupervisor(
        browser=args.browser,
        task_timeout=args.timeout,
        heartbeat_timeout=args.heartbeat_timeout,
    )

    result = await supervisor.run_rotation(
        operation=OperationType(args.operation),
        max_items_per_channel=args.max_items,
    )

    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
