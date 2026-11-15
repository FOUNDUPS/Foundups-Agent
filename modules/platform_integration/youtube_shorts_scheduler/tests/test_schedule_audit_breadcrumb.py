#!/usr/bin/env python3
"""
Test G4: Schedule Audit Breadcrumb Emission (Phase 3)

Tests that schedule_audit_unhealthy breadcrumb is emitted when post-audit
reports an unhealthy state (false positives, time collisions, etc.).

WSP 91: Observability
WSP 77: Agent Coordination

Author: 0102
Created: 2026-03-30
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))


@pytest.fixture
def mock_scheduler(tmp_path, monkeypatch):
    from modules.platform_integration.youtube_shorts_scheduler.src import scheduler as owner
    from modules.platform_integration.youtube_shorts_scheduler.src import schedule_tracker
    from modules.platform_integration.youtube_shorts_scheduler.src.content_page_scheduler import ContentPageScheduler
    from modules.platform_integration.youtube_shorts_scheduler.src.schedule_inventory import collect_scheduled_inventory

    channel_id = 'UC' + 'a' * 22
    monkeypatch.setattr(schedule_tracker, 'TRACKER_DIR', tmp_path / 'calendar')
    monkeypatch.setattr(owner, 'get_channel_config', lambda _: {
        'id': channel_id, 'name': 'Fixture channel', 'chrome_port': 9222,
        'timezone': 'America/New_York', 'max_per_day': 3,
    })
    monkeypatch.setattr(ContentPageScheduler, 'navigate_to_scheduled', lambda *_: True)
    for variable, filename in (
        ('YT_012_MANIFEST_FILE', 'inbox.json'),
        ('YT_012_MANIFEST_ACK_FILE', 'ack.json'),
        ('YT_012_MANIFEST_STATE_FILE', 'state.json'),
    ):
        monkeypatch.setenv(variable, str(tmp_path / filename))
    scheduler = owner.YouTubeShortsScheduler('foundups')
    scheduler.driver = MagicMock()
    scheduler.dom = MagicMock(driver=scheduler.driver)
    scheduler.driver.execute_script.return_value = {
        'channel_id': channel_id, 'url': f'https://studio.youtube.com/channel/{channel_id}/videos/short',
        'chip_texts': ['Visibility: Has schedule'], 'search_text': '', 'loading': False,
        'empty': True, 'previous_page': False, 'next_page': False, 'rows': [],
    }
    scheduler.dom.read_scheduled_inventory.side_effect = lambda channel: collect_scheduled_inventory(scheduler.dom, channel)
    scheduler.ensure_healthy_connection = MagicMock(return_value=True)
    scheduler._run_visibility_pass = AsyncMock(return_value=False)
    scheduler.tracker.log_schedule_report = MagicMock()
    return scheduler


class TestScheduleAuditBreadcrumbEmission:
    """Test G4: schedule_audit_unhealthy breadcrumb emission."""

    @pytest.mark.asyncio
    async def test_breadcrumb_emitted_when_audit_unhealthy(self, mock_scheduler):
        """Test breadcrumb emitted when audit reports unhealthy."""
        captured_breadcrumbs = []

        def capture_breadcrumb(**kwargs):
            captured_breadcrumbs.append(kwargs)

        telemetry_mock = MagicMock()
        telemetry_mock.store_breadcrumb = capture_breadcrumb

        # Mock unhealthy audit report
        unhealthy_report = {
            "status": "complete",
            "healthy": False,
            "false_positives": [{"video_id": "vid1"}, {"video_id": "vid2"}],
            "time_collisions": [{"slot": "Feb 1, 2026 @ 5:00 PM", "video_ids": ["a", "b"]}],
            "missing_from_tracker": [{"video_id": "vid3"}],
            "healed": ["vid1"],
        }

        with patch.dict(os.environ, {"YT_SCHEDULER_POST_AUDIT": "true"}), \
             patch("modules.platform_integration.youtube_shorts_scheduler.src.schedule_auditor.ScheduleAuditor") as mock_auditor_cls, \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=telemetry_mock):

            mock_auditor = MagicMock()
            mock_auditor.run_audit.return_value = unhealthy_report
            mock_auditor_cls.return_value = mock_auditor

            # Mock the scheduling cycle to complete quickly
            mock_scheduler.dom.navigate_to_shorts_with_fallback.return_value = True
            mock_scheduler.dom.get_unlisted_videos.return_value = []
            mock_scheduler.tracker.log_schedule_report.return_value = None

            result = await mock_scheduler.run_scheduling_cycle(max_videos=0)

            # Verify breadcrumb was emitted
            audit_breadcrumbs = [
                b for b in captured_breadcrumbs
                if b.get("event_type") == "schedule_audit_unhealthy"
            ]
            assert len(audit_breadcrumbs) == 1

    @pytest.mark.asyncio
    async def test_breadcrumb_metadata_contains_raw_facts(self, mock_scheduler):
        """Test breadcrumb metadata contains required raw facts."""
        captured_metadata = {}

        def capture_breadcrumb(**kwargs):
            if kwargs.get("event_type") == "schedule_audit_unhealthy":
                captured_metadata.update(kwargs.get("metadata", {}))

        telemetry_mock = MagicMock()
        telemetry_mock.store_breadcrumb = capture_breadcrumb

        unhealthy_report = {
            "status": "complete",
            "healthy": False,
            "false_positives": [{"video_id": "vid1"}],
            "time_collisions": [{"slot": "Feb 1, 2026 @ 5:00 PM", "video_ids": ["a", "b"]}],
            "missing_from_tracker": [{"video_id": "vid2"}, {"video_id": "vid3"}],
            "healed": [],
        }

        with patch.dict(os.environ, {"YT_SCHEDULER_POST_AUDIT": "true"}), \
             patch("modules.platform_integration.youtube_shorts_scheduler.src.schedule_auditor.ScheduleAuditor") as mock_auditor_cls, \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=telemetry_mock):

            mock_auditor = MagicMock()
            mock_auditor.run_audit.return_value = unhealthy_report
            mock_auditor_cls.return_value = mock_auditor

            mock_scheduler.dom.navigate_to_shorts_with_fallback.return_value = True
            mock_scheduler.dom.get_unlisted_videos.return_value = []
            mock_scheduler.tracker.log_schedule_report.return_value = None

            await mock_scheduler.run_scheduling_cycle(max_videos=0)

            # Verify metadata fields (contract from Phase 3)
            assert "channel_key" in captured_metadata
            assert "channel_id" in captured_metadata
            assert "false_positives" in captured_metadata
            assert "time_collisions" in captured_metadata
            assert "missing_from_tracker" in captured_metadata
            assert "auto_heal" in captured_metadata
            assert "healed" in captured_metadata

            # Verify values match
            assert captured_metadata["false_positives"] == 1
            assert captured_metadata["time_collisions"] == 1
            assert captured_metadata["missing_from_tracker"] == 2

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", ["failed", "partial"])
    async def test_incomplete_audit_is_unknown_not_clean_or_absence_conflict(self, mock_scheduler, status):
        telemetry = MagicMock()
        report = {"status": status, "healthy": None, "total_scheduled": None,
                  "observed_scheduled_count": 1, "false_positives": [], "time_collisions": [], "healed": []}
        with patch.dict(os.environ, {"YT_SCHEDULER_POST_AUDIT": "true"}), \
             patch("modules.platform_integration.youtube_shorts_scheduler.src.schedule_auditor.ScheduleAuditor") as factory, \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=telemetry):
            factory.return_value.run_audit.return_value = report
            result = await mock_scheduler.run_scheduling_cycle()
        assert result["audit"]["status"] == status
        assert result["audit"]["healthy"] is None and result["audit"]["total_scheduled"] is None
        assert result["audit"]["observed_scheduled_count"] == 1
        assert telemetry.store_breadcrumb.call_count == 0

    @pytest.mark.asyncio
    async def test_no_breadcrumb_when_audit_healthy(self, mock_scheduler):
        """Test no breadcrumb emitted when audit is healthy."""
        captured_breadcrumbs = []

        def capture_breadcrumb(**kwargs):
            captured_breadcrumbs.append(kwargs)

        telemetry_mock = MagicMock()
        telemetry_mock.store_breadcrumb = capture_breadcrumb

        healthy_report = {
            "status": "complete",
            "healthy": True,
            "false_positives": [],
            "time_collisions": [],
            "missing_from_tracker": [],
            "healed": [],
        }

        with patch.dict(os.environ, {"YT_SCHEDULER_POST_AUDIT": "true"}), \
             patch("modules.platform_integration.youtube_shorts_scheduler.src.schedule_auditor.ScheduleAuditor") as mock_auditor_cls, \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=telemetry_mock):

            mock_auditor = MagicMock()
            mock_auditor.run_audit.return_value = healthy_report
            mock_auditor_cls.return_value = mock_auditor

            mock_scheduler.dom.navigate_to_shorts_with_fallback.return_value = True
            mock_scheduler.dom.get_unlisted_videos.return_value = []
            mock_scheduler.tracker.log_schedule_report.return_value = None

            await mock_scheduler.run_scheduling_cycle(max_videos=0)

            # Verify NO audit_unhealthy breadcrumb was emitted
            audit_breadcrumbs = [
                b for b in captured_breadcrumbs
                if b.get("event_type") == "schedule_audit_unhealthy"
            ]
            assert len(audit_breadcrumbs) == 0

    @pytest.mark.asyncio
    async def test_no_breadcrumb_when_audit_disabled(self, mock_scheduler):
        """Test no breadcrumb when post-audit is disabled (default)."""
        captured_breadcrumbs = []

        def capture_breadcrumb(**kwargs):
            captured_breadcrumbs.append(kwargs)

        telemetry_mock = MagicMock()
        telemetry_mock.store_breadcrumb = capture_breadcrumb

        with patch.dict(os.environ, {"YT_SCHEDULER_POST_AUDIT": "false"}, clear=False), \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=telemetry_mock):

            mock_scheduler.dom.navigate_to_shorts_with_fallback.return_value = True
            mock_scheduler.dom.get_unlisted_videos.return_value = []
            mock_scheduler.tracker.log_schedule_report.return_value = None

            await mock_scheduler.run_scheduling_cycle(max_videos=0)

            # Verify NO audit_unhealthy breadcrumb (audit was skipped)
            audit_breadcrumbs = [
                b for b in captured_breadcrumbs
                if b.get("event_type") == "schedule_audit_unhealthy"
            ]
            assert len(audit_breadcrumbs) == 0


class TestScheduleAuditAutoHeal:
    """Test auto-heal flag is passed correctly."""

    @pytest.mark.asyncio
    async def test_auto_heal_passed_to_auditor(self, mock_scheduler):
        """Test auto_heal flag from env is passed to auditor."""
        unhealthy_report = {
            "status": "complete",
            "healthy": False,
            "false_positives": [{"video_id": "vid1"}],
            "time_collisions": [],
            "missing_from_tracker": [],
            "healed": ["vid1"],
        }

        with patch.dict(os.environ, {
            "YT_SCHEDULER_POST_AUDIT": "true",
            "YT_SCHEDULER_AUDIT_AUTO_HEAL": "true",
        }), \
             patch("modules.platform_integration.youtube_shorts_scheduler.src.schedule_auditor.ScheduleAuditor") as mock_auditor_cls, \
             patch("modules.communication.livechat.src.breadcrumb_telemetry.get_breadcrumb_telemetry", return_value=MagicMock()):

            mock_auditor = MagicMock()
            mock_auditor.run_audit.return_value = unhealthy_report
            mock_auditor_cls.return_value = mock_auditor

            mock_scheduler.dom.navigate_to_shorts_with_fallback.return_value = True
            mock_scheduler.dom.get_unlisted_videos.return_value = []
            mock_scheduler.tracker.log_schedule_report.return_value = None

            await mock_scheduler.run_scheduling_cycle(max_videos=0)

            # Verify auto_heal was passed as True
            mock_auditor.run_audit.assert_called_once_with(auto_heal=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
