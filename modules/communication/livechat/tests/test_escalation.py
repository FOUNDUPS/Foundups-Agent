#!/usr/bin/env python3
"""
Test G6: Escalation Path (Phase 3)

Tests the human_intervention_required breadcrumb emission when channels
exceed the consecutive failure threshold.

WSP 91: Observability
WSP 77: Agent Coordination

Author: 0102
Created: 2026-03-30
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import modules.communication.livechat.src.rotation_supervisor as rs_module
from modules.communication.livechat.src.rotation_supervisor import (
    RotationSupervisor,
    OperationType,
    ESCALATION_FAILURE_THRESHOLD,
)


class TestEscalationThresholdConstant:
    """Test ESCALATION_FAILURE_THRESHOLD constant."""

    def test_default_value(self):
        """Test default value is 3."""
        with patch.dict(os.environ, {}, clear=True):
            from importlib import reload
            import modules.communication.livechat.src.rotation_supervisor as rs
            reload(rs)
            assert rs.ESCALATION_FAILURE_THRESHOLD == 3

    def test_env_override(self):
        """Test env var override."""
        with patch.dict(os.environ, {"YT_ESCALATION_FAILURE_THRESHOLD": "5"}):
            from importlib import reload
            import modules.communication.livechat.src.rotation_supervisor as rs
            reload(rs)
            assert rs.ESCALATION_FAILURE_THRESHOLD == 5


class TestEscalationCheck:
    """Test _check_escalation() method."""

    @pytest.fixture
    def supervisor(self):
        """Create supervisor with mocked dependencies."""
        with patch("modules.communication.livechat.src.rotation_supervisor.group_channels_by_browser"):
            sup = RotationSupervisor(browser="chrome")
        return sup

    def test_no_escalation_below_threshold(self, supervisor):
        """Test no breadcrumb when failures below threshold."""
        captured_breadcrumbs = []

        def capture_breadcrumb(**kwargs):
            captured_breadcrumbs.append(kwargs)

        telemetry_mock = MagicMock()
        telemetry_mock.store_breadcrumb = capture_breadcrumb

        # Mock store returning channels with low failure counts
        mock_store = MagicMock()
        mock_store.get_stale_channels.return_value = [
            {"channel_id": "ch1", "channel_name": "Channel1", "consecutive_failures": 1, "hours_stale": 10},
            {"channel_id": "ch2", "channel_name": "Channel2", "consecutive_failures": 2, "hours_stale": 5},
        ]

        with patch("modules.communication.livechat.src.youtube_telemetry_store.YouTubeTelemetryStore", return_value=mock_store), \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=telemetry_mock), \
             patch.object(rs_module, "ESCALATION_FAILURE_THRESHOLD", 3):

            supervisor._check_escalation("comments")

            # No escalation breadcrumbs should be emitted
            escalation_breadcrumbs = [
                b for b in captured_breadcrumbs
                if b.get("event_type") == "human_intervention_required"
            ]
            assert len(escalation_breadcrumbs) == 0

    def test_escalation_at_threshold(self, supervisor):
        """Test breadcrumb emitted when failures at threshold."""
        captured_breadcrumbs = []

        def capture_breadcrumb(**kwargs):
            captured_breadcrumbs.append(kwargs)

        telemetry_mock = MagicMock()
        telemetry_mock.store_breadcrumb = capture_breadcrumb

        # Mock store returning channel at threshold
        mock_store = MagicMock()
        mock_store.get_stale_channels.return_value = [
            {"channel_id": "ch1", "channel_name": "FailingChannel", "consecutive_failures": 3, "hours_stale": 24},
        ]

        with patch("modules.communication.livechat.src.youtube_telemetry_store.YouTubeTelemetryStore", return_value=mock_store), \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=telemetry_mock), \
             patch.object(rs_module, "ESCALATION_FAILURE_THRESHOLD", 3):

            supervisor._check_escalation("comments")

            # Should have escalation breadcrumb
            escalation_breadcrumbs = [
                b for b in captured_breadcrumbs
                if b.get("event_type") == "human_intervention_required"
            ]
            assert len(escalation_breadcrumbs) == 1

    def test_escalation_above_threshold(self, supervisor):
        """Test breadcrumb emitted when failures above threshold."""
        captured_breadcrumbs = []

        def capture_breadcrumb(**kwargs):
            captured_breadcrumbs.append(kwargs)

        telemetry_mock = MagicMock()
        telemetry_mock.store_breadcrumb = capture_breadcrumb

        mock_store = MagicMock()
        mock_store.get_stale_channels.return_value = [
            {"channel_id": "ch1", "channel_name": "BadChannel", "consecutive_failures": 10, "hours_stale": 48},
        ]

        with patch("modules.communication.livechat.src.youtube_telemetry_store.YouTubeTelemetryStore", return_value=mock_store), \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=telemetry_mock), \
             patch.object(rs_module, "ESCALATION_FAILURE_THRESHOLD", 3):

            supervisor._check_escalation("comments")

            escalation_breadcrumbs = [
                b for b in captured_breadcrumbs
                if b.get("event_type") == "human_intervention_required"
            ]
            assert len(escalation_breadcrumbs) == 1

    def test_escalation_multiple_channels(self, supervisor):
        """Test breadcrumb emitted for each failing channel."""
        captured_breadcrumbs = []

        def capture_breadcrumb(**kwargs):
            captured_breadcrumbs.append(kwargs)

        telemetry_mock = MagicMock()
        telemetry_mock.store_breadcrumb = capture_breadcrumb

        mock_store = MagicMock()
        mock_store.get_stale_channels.return_value = [
            {"channel_id": "ch1", "channel_name": "BadChannel1", "consecutive_failures": 5, "hours_stale": 24},
            {"channel_id": "ch2", "channel_name": "OkChannel", "consecutive_failures": 1, "hours_stale": 2},
            {"channel_id": "ch3", "channel_name": "BadChannel2", "consecutive_failures": 8, "hours_stale": 72},
        ]

        with patch("modules.communication.livechat.src.youtube_telemetry_store.YouTubeTelemetryStore", return_value=mock_store), \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=telemetry_mock), \
             patch.object(rs_module, "ESCALATION_FAILURE_THRESHOLD", 3):

            supervisor._check_escalation("comments")

            escalation_breadcrumbs = [
                b for b in captured_breadcrumbs
                if b.get("event_type") == "human_intervention_required"
            ]
            # Should have 2 escalations (ch1 and ch3)
            assert len(escalation_breadcrumbs) == 2

    def test_escalation_metadata_contains_raw_facts(self, supervisor):
        """Test escalation breadcrumb contains required metadata."""
        captured_metadata = {}

        def capture_breadcrumb(**kwargs):
            if kwargs.get("event_type") == "human_intervention_required":
                captured_metadata.update(kwargs.get("metadata", {}))

        telemetry_mock = MagicMock()
        telemetry_mock.store_breadcrumb = capture_breadcrumb

        mock_store = MagicMock()
        mock_store.get_stale_channels.return_value = [
            {"channel_id": "ch123", "channel_name": "FailingChannel", "consecutive_failures": 5, "hours_stale": 48.5},
        ]

        with patch("modules.communication.livechat.src.youtube_telemetry_store.YouTubeTelemetryStore", return_value=mock_store), \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=telemetry_mock), \
             patch.object(rs_module, "ESCALATION_FAILURE_THRESHOLD", 3):

            supervisor._check_escalation("shorts")

            # Verify metadata fields (contract from Phase 3)
            assert captured_metadata.get("channel_id") == "ch123"
            assert captured_metadata.get("channel_name") == "FailingChannel"
            assert captured_metadata.get("consecutive_failures") == 5
            assert captured_metadata.get("operation") == "shorts"
            assert captured_metadata.get("threshold") == 3
            assert captured_metadata.get("action") == "human_intervention_required"
            assert captured_metadata.get("hours_stale") == 48.5

    def test_escalation_handles_store_errors_gracefully(self, supervisor, caplog):
        """Test _check_escalation handles errors without failing."""
        import logging

        with patch("modules.communication.livechat.src.youtube_telemetry_store.YouTubeTelemetryStore") as mock_cls:
            mock_cls.side_effect = Exception("Database connection failed")

            with caplog.at_level(logging.DEBUG):
                # Should not raise
                supervisor._check_escalation("comments")

            # Should log debug message about failure
            assert "Escalation check failed" in caplog.text


class TestEscalationIntegrationWithRotation:
    """Test escalation check is called after rotation."""

    @pytest.fixture
    def supervisor(self):
        """Create supervisor with mocked dependencies."""
        with patch("modules.communication.livechat.src.rotation_supervisor.group_channels_by_browser"):
            sup = RotationSupervisor(browser="chrome")
        return sup

    @pytest.mark.asyncio
    async def test_escalation_called_after_rotation_complete(self, supervisor):
        """Test _check_escalation is called at end of run_rotation."""
        escalation_calls = []

        def track_escalation(operation):
            escalation_calls.append(operation)

        with patch.object(supervisor, "_get_channels_for_browser", return_value=["Ch1"]), \
             patch.object(supervisor, "_spawn_task") as mock_spawn, \
             patch.object(supervisor, "_monitor_task") as mock_monitor, \
             patch.object(supervisor, "_record_channel_op"), \
             patch.object(supervisor, "_check_escalation", side_effect=track_escalation), \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=MagicMock()):

            mock_heartbeat = MagicMock()
            mock_heartbeat.state = rs_module.TaskState.RUNNING
            mock_heartbeat.task_id = "task"
            mock_heartbeat.comments_processed = 5
            mock_spawn.return_value = mock_heartbeat
            mock_monitor.return_value = rs_module.TaskState.COMPLETED

            await supervisor.run_rotation(
                operation=OperationType.COMMENTS,
                channels=["Ch1"],
            )

            # _check_escalation should have been called with operation value
            assert len(escalation_calls) == 1
            assert escalation_calls[0] == "comments"


class TestNoDoubleAuthority:
    """Test that Phase 2 telemetry remains the single authority for failure tracking."""

    @pytest.fixture
    def supervisor(self):
        """Create supervisor with mocked dependencies."""
        with patch("modules.communication.livechat.src.rotation_supervisor.group_channels_by_browser"):
            sup = RotationSupervisor(browser="chrome")
        return sup

    def test_escalation_queries_phase2_store(self, supervisor):
        """Test escalation uses Phase 2 YouTubeTelemetryStore, not new storage."""
        mock_store = MagicMock()
        mock_store.get_stale_channels.return_value = []

        with patch("modules.communication.livechat.src.youtube_telemetry_store.YouTubeTelemetryStore", return_value=mock_store) as mock_cls:
            supervisor._check_escalation("comments")

            # Should have instantiated YouTubeTelemetryStore
            mock_cls.assert_called_once()
            # Should have called get_stale_channels
            mock_store.get_stale_channels.assert_called_once()

    def test_escalation_does_not_write_to_store(self, supervisor):
        """Test escalation is read-only - does not modify Phase 2 telemetry."""
        mock_store = MagicMock()
        mock_store.get_stale_channels.return_value = [
            {"channel_id": "ch1", "channel_name": "BadChannel", "consecutive_failures": 10, "hours_stale": 48},
        ]

        with patch("modules.communication.livechat.src.youtube_telemetry_store.YouTubeTelemetryStore", return_value=mock_store), \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=MagicMock()):

            supervisor._check_escalation("comments")

            # Should NOT have called any write methods
            mock_store.record_channel_operation.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
