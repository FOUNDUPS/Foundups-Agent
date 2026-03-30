#!/usr/bin/env python3
"""
Test G5: Cycle Watchdog (Phase 2)

Tests the MAX_CYCLE_DURATION_HOURS watchdog in rotation_supervisor.py.
This emits a breadcrumb when the rotation cycle exceeds the threshold,
allowing AI Overseer to detect hung rotations.

WSP 91: Observability
WSP 77: Agent Coordination

Author: 0102
Created: 2026-03-30
"""

import os
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import modules.communication.livechat.src.rotation_supervisor as rs_module
from modules.communication.livechat.src.rotation_supervisor import (
    RotationSupervisor,
    OperationType,
    TaskState,
    MAX_CYCLE_DURATION_HOURS,
)


class TestMaxCycleDurationConstant:
    """Test MAX_CYCLE_DURATION_HOURS constant."""

    def test_default_value(self):
        """Test default value is 2.0 hours."""
        # Reset to default by clearing env var
        with patch.dict(os.environ, {}, clear=True):
            # Re-import to get default
            from importlib import reload
            import modules.communication.livechat.src.rotation_supervisor as rs
            reload(rs)
            assert rs.MAX_CYCLE_DURATION_HOURS == 2.0

    def test_env_override(self):
        """Test env var override."""
        with patch.dict(os.environ, {"YT_MAX_CYCLE_DURATION_HOURS": "4.5"}):
            from importlib import reload
            import modules.communication.livechat.src.rotation_supervisor as rs
            reload(rs)
            assert rs.MAX_CYCLE_DURATION_HOURS == 4.5


class TestCycleWatchdogLogic:
    """Test cycle watchdog detection logic."""

    @pytest.fixture
    def supervisor(self):
        """Create supervisor with mocked dependencies."""
        with patch("modules.communication.livechat.src.rotation_supervisor.group_channels_by_browser"):
            sup = RotationSupervisor(browser="chrome")
        return sup

    @pytest.mark.asyncio
    async def test_normal_cycle_no_watchdog(self, supervisor):
        """Test normal cycle does not trigger watchdog."""
        # Mock dependencies - use the module's TaskState reference
        with patch.object(supervisor, "_get_channels_for_browser", return_value=["Channel1"]), \
             patch.object(supervisor, "_spawn_task") as mock_spawn, \
             patch.object(supervisor, "_monitor_task") as mock_monitor, \
             patch.object(supervisor, "_record_channel_op"):

            # Setup mock task that completes quickly
            mock_heartbeat = MagicMock()
            mock_heartbeat.state = rs_module.TaskState.RUNNING
            mock_heartbeat.task_id = "test_task"
            mock_heartbeat.comments_processed = 5
            mock_spawn.return_value = mock_heartbeat
            mock_monitor.return_value = rs_module.TaskState.COMPLETED

            result = await supervisor.run_rotation(
                operation=OperationType.COMMENTS,
                channels=["TestChannel"],
            )

            assert "TestChannel" in result.channels_processed
            assert result.elapsed_seconds < 60  # Should be fast

    @pytest.mark.asyncio
    async def test_watchdog_triggers_on_threshold(self, supervisor):
        """Test watchdog triggers when cycle exceeds threshold (simple test)."""
        # Patch MAX_CYCLE_DURATION_HOURS to 0 so it triggers immediately
        captured_breadcrumbs = []

        def capture_breadcrumb(**kwargs):
            captured_breadcrumbs.append(kwargs)

        telemetry_mock = MagicMock()
        telemetry_mock.store_breadcrumb = capture_breadcrumb

        with patch.object(supervisor, "_get_channels_for_browser", return_value=["Ch1", "Ch2", "Ch3"]), \
             patch.object(supervisor, "_spawn_task") as mock_spawn, \
             patch.object(supervisor, "_monitor_task") as mock_monitor, \
             patch.object(supervisor, "_record_channel_op"), \
             patch.object(rs_module, "MAX_CYCLE_DURATION_HOURS", 0), \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=telemetry_mock):

            mock_heartbeat = MagicMock()
            mock_heartbeat.state = rs_module.TaskState.RUNNING
            mock_heartbeat.task_id = "test_task"
            mock_heartbeat.comments_processed = 5
            mock_spawn.return_value = mock_heartbeat
            mock_monitor.return_value = rs_module.TaskState.COMPLETED

            result = await supervisor.run_rotation(
                operation=OperationType.COMMENTS,
                channels=["Ch1", "Ch2", "Ch3"],
            )

            # Should have emitted a stall breadcrumb
            stall_breadcrumbs = [b for b in captured_breadcrumbs
                                 if b.get("event_type") == "rotation_cycle_stalled"]
            assert len(stall_breadcrumbs) >= 1

    @pytest.mark.asyncio
    async def test_watchdog_breadcrumb_contains_metadata(self, supervisor):
        """Test watchdog breadcrumb contains required metadata."""
        captured_breadcrumbs = []

        def capture_breadcrumb(**kwargs):
            captured_breadcrumbs.append(kwargs)

        telemetry_mock = MagicMock()
        telemetry_mock.store_breadcrumb = capture_breadcrumb

        with patch.object(supervisor, "_get_channels_for_browser", return_value=["Ch1", "Ch2", "Ch3"]), \
             patch.object(supervisor, "_spawn_task") as mock_spawn, \
             patch.object(supervisor, "_monitor_task") as mock_monitor, \
             patch.object(supervisor, "_record_channel_op"), \
             patch.object(supervisor, "_check_escalation"), \
             patch.object(rs_module, "MAX_CYCLE_DURATION_HOURS", 0), \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=telemetry_mock):

            mock_heartbeat = MagicMock()
            mock_heartbeat.state = rs_module.TaskState.RUNNING
            mock_heartbeat.task_id = "test_task"
            mock_heartbeat.comments_processed = 0
            mock_spawn.return_value = mock_heartbeat
            mock_monitor.return_value = rs_module.TaskState.COMPLETED

            await supervisor.run_rotation(
                operation=OperationType.COMMENTS,
                channels=["Ch1", "Ch2", "Ch3"],
            )

            # Find the stall breadcrumb and check metadata
            stall_breadcrumbs = [b for b in captured_breadcrumbs
                                 if b.get("event_type") == "rotation_cycle_stalled"]
            assert len(stall_breadcrumbs) >= 1, f"Expected stall breadcrumb, got: {captured_breadcrumbs}"

            captured_metadata = stall_breadcrumbs[0].get("metadata", {})

            # Verify metadata fields (contract from Phase 2)
            assert "elapsed_hours" in captured_metadata
            assert "max_hours" in captured_metadata
            assert "channels_processed" in captured_metadata
            assert "channels_remaining" in captured_metadata
            # Additional fields added per 012 review
            assert "cycle_started_at" in captured_metadata
            assert "operation" in captured_metadata
            assert "browser" in captured_metadata


class TestRecordChannelOpIntegration:
    """Test _record_channel_op() integration."""

    @pytest.fixture
    def supervisor(self):
        """Create supervisor with mocked dependencies."""
        with patch("modules.communication.livechat.src.rotation_supervisor.group_channels_by_browser"):
            sup = RotationSupervisor(browser="edge")
        return sup

    def test_record_channel_op_on_success(self, supervisor):
        """Test channel operation recorded on successful completion."""
        with patch("modules.communication.livechat.src.youtube_telemetry_store.YouTubeTelemetryStore") as mock_store:
            mock_instance = MagicMock()
            mock_store.return_value = mock_instance

            supervisor._record_channel_op("TestChannel", "comments", success=True)

            mock_instance.record_channel_operation.assert_called_once_with(
                channel_id="TestChannel",  # Falls back to name if not in registry
                channel_name="TestChannel",
                operation="comments",
                success=True,
            )

    def test_record_channel_op_on_failure(self, supervisor):
        """Test channel operation recorded on failure."""
        with patch("modules.communication.livechat.src.youtube_telemetry_store.YouTubeTelemetryStore") as mock_store:
            mock_instance = MagicMock()
            mock_store.return_value = mock_instance

            supervisor._record_channel_op("FailedChannel", "shorts", success=False)

            mock_instance.record_channel_operation.assert_called_once_with(
                channel_id="FailedChannel",
                channel_name="FailedChannel",
                operation="shorts",
                success=False,
            )

    def test_record_channel_op_handles_errors(self, supervisor, caplog):
        """Test _record_channel_op handles errors gracefully."""
        import logging

        with patch("modules.communication.livechat.src.youtube_telemetry_store.YouTubeTelemetryStore") as mock_store:
            mock_store.side_effect = Exception("Database error")

            with caplog.at_level(logging.DEBUG):
                # Should not raise
                supervisor._record_channel_op("Channel", "comments", success=True)

            # Should log debug message
            assert "Failed to record channel operation" in caplog.text


class TestRotationFlowWithWatchdog:
    """Test full rotation flow with watchdog integration."""

    @pytest.fixture
    def supervisor(self):
        """Create supervisor with mocked dependencies."""
        with patch("modules.communication.livechat.src.rotation_supervisor.group_channels_by_browser"):
            sup = RotationSupervisor(browser="chrome")
        return sup

    @pytest.mark.asyncio
    async def test_rotation_breaks_on_watchdog_trigger(self, supervisor):
        """Test rotation loop breaks when watchdog triggers."""
        with patch.object(supervisor, "_get_channels_for_browser", return_value=["A", "B", "C", "D", "E"]), \
             patch.object(supervisor, "_spawn_task") as mock_spawn, \
             patch.object(supervisor, "_monitor_task") as mock_monitor, \
             patch.object(supervisor, "_record_channel_op"), \
             patch.object(rs_module, "MAX_CYCLE_DURATION_HOURS", 0), \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=MagicMock()):

            mock_heartbeat = MagicMock()
            mock_heartbeat.state = rs_module.TaskState.RUNNING
            mock_heartbeat.task_id = "task"
            mock_heartbeat.comments_processed = 0
            mock_spawn.return_value = mock_heartbeat
            mock_monitor.return_value = rs_module.TaskState.COMPLETED

            result = await supervisor.run_rotation(
                operation=OperationType.COMMENTS,
                channels=["A", "B", "C", "D", "E"],
            )

            # Should break early due to watchdog
            # Since MAX_CYCLE_DURATION_HOURS=0, it should break on first iteration
            assert len(result.channels_processed) < 5

    @pytest.mark.asyncio
    async def test_record_channel_op_called_for_each_channel(self, supervisor):
        """Test _record_channel_op is called after each channel."""
        record_calls = []

        def track_record(channel, operation, success):
            record_calls.append((channel, operation, success))

        with patch.object(supervisor, "_get_channels_for_browser", return_value=["Ch1", "Ch2"]), \
             patch.object(supervisor, "_spawn_task") as mock_spawn, \
             patch.object(supervisor, "_monitor_task") as mock_monitor, \
             patch.object(supervisor, "_record_channel_op", side_effect=track_record), \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=MagicMock()):

            mock_heartbeat = MagicMock()
            mock_heartbeat.state = rs_module.TaskState.RUNNING
            mock_heartbeat.task_id = "task"
            mock_heartbeat.comments_processed = 3
            mock_spawn.return_value = mock_heartbeat
            mock_monitor.return_value = rs_module.TaskState.COMPLETED

            await supervisor.run_rotation(
                operation=OperationType.COMMENTS,
                channels=["Ch1", "Ch2"],
            )

            # Should have recorded both channels:
            # - 2 per-channel operation records (comments)
            # - 2 rotation success records (at end of successful rotation)
            assert len(record_calls) == 4
            assert record_calls[0] == ("Ch1", "comments", True)
            assert record_calls[1] == ("Ch2", "comments", True)
            assert record_calls[2] == ("Ch1", "rotation", True)
            assert record_calls[3] == ("Ch2", "rotation", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
