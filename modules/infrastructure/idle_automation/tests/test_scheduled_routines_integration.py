#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for scheduled routines in idle automation.

Tests cover:
- Scheduled routine execution through idle automation DAE
- Dispatch to correct native paths
- Result recording and status reporting
"""

import json
import pytest
from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from modules.infrastructure.idle_automation.src.schedule_evaluator import (
    ScheduleEvaluator,
)


class TestScheduledRoutinesDispatch:
    """Test scheduled routine dispatch logic."""

    @pytest.fixture
    def temp_memory_path(self, tmp_path):
        """Create temporary memory directory."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        return memory_dir

    @pytest.fixture
    def mock_dae(self, temp_memory_path):
        """Create a mock IdleAutomationDAE with temp paths."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        # Patch memory path before instantiation
        with patch.object(IdleAutomationDAE, "__init__", lambda self: None):
            dae = IdleAutomationDAE()
            dae.module_path = temp_memory_path.parent
            dae.memory_path = temp_memory_path
            dae.idle_state = {}
            dae.execution_history = []
            dae.config = {
                "auto_git_push": False,
                "auto_linkedin_post": False,
                "auto_self_research": True,
                "idle_task_timeout": 300,
                "max_daily_executions": 3,
                "self_research_timeout": 900,
                "health_critical_threshold": 20,
                "health_warning_threshold": 50,
            }
            dae.wre_integration = None

            # Add required methods
            dae._parse_bool_env = lambda key, default: default
            dae._save_idle_state = MagicMock()

            return dae

    @pytest.mark.asyncio
    async def test_execute_scheduled_routines_no_due_schedules(
        self, mock_dae, temp_memory_path
    ):
        """When no schedules are due, returns success with 0 executed."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        schedules_path = temp_memory_path / "schedules.json"
        mock_evaluator = ScheduleEvaluator(schedules_path=schedules_path)

        with patch(
            "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
            return_value=mock_evaluator,
        ):
            result = await IdleAutomationDAE._execute_scheduled_routines(mock_dae)

        assert result["success"] is True
        assert result["due_count"] == 0
        assert result["executed_count"] == 0

    @pytest.mark.asyncio
    async def test_execute_scheduled_routines_dispatches_self_research(
        self, mock_dae, temp_memory_path
    ):
        """Due self_research schedule dispatches to self research refresh."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        # Create a due schedule
        schedules_path = temp_memory_path / "schedules.json"
        evaluator = ScheduleEvaluator(schedules_path=schedules_path)
        evaluator.add_schedule("run self research daily")

        # Mock the self-research execution
        mock_dae._execute_self_research_refresh = AsyncMock(
            return_value={
                "success": True,
                "update_candidates": 5,
                "autonomous_tasks": 2,
            }
        )

        with patch(
            "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
            return_value=evaluator,
        ):
            result = await IdleAutomationDAE._execute_scheduled_routines(mock_dae)

        assert result["success"] is True
        assert result["due_count"] == 1
        assert result["executed_count"] == 1
        mock_dae._execute_self_research_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_scheduled_routines_dispatches_queue_audit(
        self, mock_dae, temp_memory_path
    ):
        """Due queue_audit schedule dispatches to queue builder."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        # Create a due schedule
        schedules_path = temp_memory_path / "schedules.json"
        evaluator = ScheduleEvaluator(schedules_path=schedules_path)
        evaluator.add_schedule("run queue audit daily")

        # Mock the queue audit execution
        mock_dae._run_queue_audit = AsyncMock(
            return_value={"success": True, "summary": "Queue refreshed"}
        )

        with patch(
            "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
            return_value=evaluator,
        ):
            result = await IdleAutomationDAE._execute_scheduled_routines(mock_dae)

        assert result["success"] is True
        assert result["executed_count"] == 1
        mock_dae._run_queue_audit.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_scheduled_routines_records_execution(
        self, mock_dae, temp_memory_path
    ):
        """Execution is recorded in schedule spec."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        # Create a due schedule
        schedules_path = temp_memory_path / "schedules.json"
        evaluator = ScheduleEvaluator(schedules_path=schedules_path)
        spec = evaluator.add_schedule("run self research daily")
        assert spec.last_run is None

        # Mock the self-research execution
        mock_dae._execute_self_research_refresh = AsyncMock(
            return_value={
                "success": True,
                "update_candidates": 5,
                "autonomous_tasks": 2,
            }
        )

        with patch(
            "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
            return_value=evaluator,
        ):
            await IdleAutomationDAE._execute_scheduled_routines(mock_dae)

        # Check last_run is set on the evaluator instance we passed in
        updated = evaluator.get_schedule(spec.id)
        assert updated.last_run is not None

    @pytest.mark.asyncio
    async def test_execute_scheduled_routines_disabled_returns_early(
        self, mock_dae, temp_memory_path
    ):
        """When disabled via env, returns early without evaluating."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        mock_dae._parse_bool_env = lambda key, default: (
            False if key == "AUTO_SCHEDULED_ROUTINES" else default
        )

        result = await IdleAutomationDAE._execute_scheduled_routines(mock_dae)

        assert result["success"] is False
        assert "disabled" in result["error"].lower()


class TestDispatchScheduledRoutine:
    """Test individual routine dispatch."""

    @pytest.fixture
    def mock_dae(self, tmp_path):
        """Create a mock DAE for dispatch testing."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        with patch.object(IdleAutomationDAE, "__init__", lambda self: None):
            dae = IdleAutomationDAE()
            dae.module_path = tmp_path
            dae.config = {"self_research_timeout": 300}
            return dae

    @pytest.mark.asyncio
    async def test_dispatch_self_research(self, mock_dae):
        """self_research routine calls _execute_self_research_refresh."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        mock_dae._execute_self_research_refresh = AsyncMock(
            return_value={
                "success": True,
                "update_candidates": 3,
                "autonomous_tasks": 1,
            }
        )

        result = await IdleAutomationDAE._dispatch_scheduled_routine(
            mock_dae, "self_research"
        )

        assert result["success"] is True
        assert "3 candidates" in result["summary"]
        mock_dae._execute_self_research_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_grant_watchlist(self, mock_dae):
        """grant_watchlist routine calls refresh_grant_watchlist."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        # Mock the refresher with proper method using correct status keys
        mock_refresher = MagicMock()
        mock_refresher.refresh_grant_watchlist.return_value = {
            "refresh_success": True,
            "status": {
                "watch_count": 15,
                "changed_count": 3,
                "error_count": 1,
            },
        }

        with patch(
            "modules.infrastructure.idle_automation.src.self_research_refresh.SelfResearchRefresher",
            return_value=mock_refresher,
        ):
            result = await IdleAutomationDAE._dispatch_scheduled_routine(
                mock_dae, "grant_watchlist"
            )

        assert result["success"] is True
        assert "15 watched" in result["summary"]
        assert "3 changed" in result["summary"]

    @pytest.mark.asyncio
    async def test_dispatch_unknown_routine(self, mock_dae):
        """Unknown routine returns error."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        result = await IdleAutomationDAE._dispatch_scheduled_routine(
            mock_dae, "unknown_routine"
        )

        assert result["success"] is False
        assert "unknown" in result["error"].lower()


class TestGetScheduledRoutinesStatus:
    """Test status reporting for scheduled routines."""

    @pytest.fixture
    def temp_memory_path(self, tmp_path):
        """Create temporary memory directory."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        return memory_dir

    def test_status_with_no_schedules(self, temp_memory_path):
        """Status reports empty when no schedules exist."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        schedules_path = temp_memory_path / "schedules.json"
        mock_evaluator = ScheduleEvaluator(schedules_path=schedules_path)

        with patch.object(IdleAutomationDAE, "__init__", lambda self: None):
            dae = IdleAutomationDAE()
            dae.module_path = temp_memory_path.parent
            dae.memory_path = temp_memory_path

            with patch(
                "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
                return_value=mock_evaluator,
            ):
                status = IdleAutomationDAE._get_scheduled_routines_status(dae)

            assert status["total_count"] == 0
            assert status["due_count"] == 0

    def test_status_with_schedules(self, temp_memory_path):
        """Status reports schedules correctly."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        # Create schedules
        schedules_path = temp_memory_path / "schedules.json"
        evaluator = ScheduleEvaluator(schedules_path=schedules_path)
        evaluator.add_schedule("run self research daily")
        evaluator.add_schedule("run queue audit nightly")

        with patch.object(IdleAutomationDAE, "__init__", lambda self: None):
            dae = IdleAutomationDAE()
            dae.module_path = temp_memory_path.parent
            dae.memory_path = temp_memory_path

            with patch(
                "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
                return_value=evaluator,
            ):
                status = IdleAutomationDAE._get_scheduled_routines_status(dae)

            assert status["total_count"] == 2
            assert status["enabled_count"] == 2
            assert len(status["schedules"]) == 2


class TestPartialFailureReporting:
    """Test that partial failures are correctly reported."""

    @pytest.fixture
    def temp_memory_path(self, tmp_path):
        """Create temporary memory directory."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        return memory_dir

    @pytest.mark.asyncio
    async def test_one_failure_makes_overall_success_false(self, temp_memory_path):
        """If any due routine fails, overall success should be False."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        # Create two schedules
        schedules_path = temp_memory_path / "schedules.json"
        evaluator = ScheduleEvaluator(schedules_path=schedules_path)
        evaluator.add_schedule("run self research daily")
        evaluator.add_schedule("run grant watchlist daily")

        with patch.object(IdleAutomationDAE, "__init__", lambda self: None):
            dae = IdleAutomationDAE()
            dae.module_path = temp_memory_path.parent
            dae.memory_path = temp_memory_path
            dae.idle_state = {}
            dae._parse_bool_env = lambda key, default: default
            dae._save_idle_state = MagicMock()

            # self_research succeeds, grant_watchlist fails
            dae._execute_self_research_refresh = AsyncMock(
                return_value={"success": True, "update_candidates": 1, "autonomous_tasks": 0}
            )
            dae._run_grant_watchlist_refresh = AsyncMock(
                return_value={"success": False, "error": "test failure"}
            )

            with patch(
                "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
                return_value=evaluator,
            ):
                result = await IdleAutomationDAE._execute_scheduled_routines(dae)

            # Overall success should be False because one routine failed
            assert result["success"] is False
            assert result["failed_count"] == 1
            assert result["executed_count"] == 1


class TestDuplicateRerunPrevention:
    """Test that duplicate immediate reruns are prevented."""

    @pytest.fixture
    def temp_memory_path(self, tmp_path):
        """Create temporary memory directory."""
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        return memory_dir

    @pytest.mark.asyncio
    async def test_second_run_same_window_skipped(self, temp_memory_path):
        """A schedule that just ran is not due again in same window."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        # Create a schedule
        schedules_path = temp_memory_path / "schedules.json"
        evaluator = ScheduleEvaluator(schedules_path=schedules_path)
        spec = evaluator.add_schedule("run self research daily")

        # First run - should execute
        with patch.object(IdleAutomationDAE, "__init__", lambda self: None):
            dae = IdleAutomationDAE()
            dae.module_path = temp_memory_path.parent
            dae.memory_path = temp_memory_path
            dae.idle_state = {}
            dae._parse_bool_env = lambda key, default: default
            dae._save_idle_state = MagicMock()
            dae._execute_self_research_refresh = AsyncMock(
                return_value={"success": True, "update_candidates": 1, "autonomous_tasks": 0}
            )

            with patch(
                "modules.infrastructure.idle_automation.src.schedule_evaluator.ScheduleEvaluator",
                return_value=evaluator,
            ):
                result1 = await IdleAutomationDAE._execute_scheduled_routines(dae)
                assert result1["executed_count"] == 1

                # Second run immediately after - should skip (evaluator state persisted)
                result2 = await IdleAutomationDAE._execute_scheduled_routines(dae)
                assert result2["due_count"] == 0
                assert result2["executed_count"] == 0
