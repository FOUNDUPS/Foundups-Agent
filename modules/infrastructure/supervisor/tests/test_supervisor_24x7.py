#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for 24/7 Supervisor state machine (Layer 2)."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from modules.infrastructure.supervisor.src.supervisor_24x7 import (
    Supervisor24x7,
    SupervisorState,
    SupervisorMetrics,
    TriageTask,
)


class TestSupervisorState:
    """Test SupervisorState enum."""

    def test_all_states_defined(self):
        """Verify all 10 states are defined."""
        expected_states = {
            "boot", "preflight", "observe", "triage", "plan",
            "execute", "verify", "remember", "escalate", "idle_watch"
        }
        actual_states = {s.value for s in SupervisorState}
        assert actual_states == expected_states

    def test_state_values_are_strings(self):
        """State values should be lowercase strings."""
        for state in SupervisorState:
            assert isinstance(state.value, str)
            assert state.value == state.value.lower()


class TestSupervisorMetrics:
    """Test SupervisorMetrics dataclass."""

    def test_default_values(self):
        """Metrics should initialize with zeros."""
        metrics = SupervisorMetrics()
        assert metrics.cycles_completed == 0
        assert metrics.events_observed == 0
        assert metrics.fixes_attempted == 0
        assert metrics.fixes_succeeded == 0
        assert metrics.escalations_triggered == 0


class TestTriageTask:
    """Test TriageTask dataclass."""

    def test_create_task(self):
        """Create a triage task."""
        task = TriageTask(
            event_signature="ironclaw runtime is unavailable",
            source_file="test.log",
            recommended_fix="start_ironclaw_gateway",
            auto_fixable=True,
        )
        assert task.event_signature == "ironclaw runtime is unavailable"
        assert task.auto_fixable is True
        assert task.timestamp > 0

    def test_task_priority_default(self):
        """Task priority defaults to 1."""
        task = TriageTask(
            event_signature="test",
            source_file="test.log",
            recommended_fix="test_fix",
            auto_fixable=False,
        )
        assert task.priority == 1


class TestSupervisor24x7:
    """Test Supervisor24x7 class."""

    @pytest.fixture
    def repo_root(self, tmp_path: Path) -> Path:
        """Create temporary repo root."""
        return tmp_path

    @pytest.fixture
    def supervisor(self, repo_root: Path) -> Supervisor24x7:
        """Create supervisor instance."""
        return Supervisor24x7(repo_root=repo_root)

    def test_init(self, supervisor: Supervisor24x7):
        """Supervisor initializes in BOOT state."""
        assert supervisor.state == SupervisorState.BOOT
        assert supervisor.enabled is True
        assert supervisor.metrics.cycles_completed == 0

    def test_get_state(self, supervisor: Supervisor24x7):
        """get_state returns current state."""
        assert supervisor.get_state() == SupervisorState.BOOT

    def test_get_metrics(self, supervisor: Supervisor24x7):
        """get_metrics returns telemetry dict."""
        metrics = supervisor.get_metrics()
        assert "state" in metrics
        assert "cycles_completed" in metrics
        assert metrics["state"] == "boot"

    def test_transition_to(self, supervisor: Supervisor24x7):
        """_transition_to changes state."""
        supervisor._transition_to(SupervisorState.PREFLIGHT)
        assert supervisor.state == SupervisorState.PREFLIGHT

    @pytest.mark.asyncio
    async def test_handle_boot(self, supervisor: Supervisor24x7):
        """BOOT state transitions to PREFLIGHT."""
        await supervisor._handle_boot()
        assert supervisor.state == SupervisorState.PREFLIGHT

    @pytest.mark.asyncio
    async def test_handle_preflight(self, supervisor: Supervisor24x7):
        """PREFLIGHT state transitions to OBSERVE."""
        supervisor.state = SupervisorState.PREFLIGHT
        await supervisor._handle_preflight()
        assert supervisor.state == SupervisorState.OBSERVE

    @pytest.mark.asyncio
    async def test_handle_observe_no_events(self, supervisor: Supervisor24x7):
        """OBSERVE with no events transitions to IDLE_WATCH."""
        supervisor.state = SupervisorState.OBSERVE
        await supervisor._handle_observe()
        assert supervisor.state == SupervisorState.IDLE_WATCH

    @pytest.mark.asyncio
    async def test_handle_observe_with_mock_events(self, supervisor: Supervisor24x7):
        """OBSERVE with events transitions to TRIAGE."""
        supervisor.state = SupervisorState.OBSERVE

        # Mock audit loop with events
        mock_audit = MagicMock()
        mock_audit.scan_once.return_value = [MagicMock(signature="test_error")]
        supervisor._audit_loop = mock_audit

        await supervisor._handle_observe()
        assert supervisor.state == SupervisorState.TRIAGE
        assert len(supervisor._current_events) == 1

    @pytest.mark.asyncio
    async def test_handle_triage_creates_tasks(self, supervisor: Supervisor24x7):
        """TRIAGE creates tasks from events."""
        supervisor.state = SupervisorState.TRIAGE
        supervisor._current_events = [MagicMock(signature="test_error", source_file="test.log")]

        await supervisor._handle_triage()
        assert supervisor.state == SupervisorState.PLAN
        assert len(supervisor._triage_queue) == 1

    @pytest.mark.asyncio
    async def test_handle_execute_with_mock_audit(self, supervisor: Supervisor24x7):
        """EXECUTE calls audit loop's _apply_policy_fix."""
        supervisor.state = SupervisorState.EXECUTE
        supervisor._triage_queue = [
            TriageTask(
                event_signature="test",
                source_file="test.log",
                recommended_fix="start_ironclaw_gateway",
                auto_fixable=True,
            )
        ]

        # Mock audit loop
        mock_audit = MagicMock()
        mock_audit._apply_policy_fix.return_value = (True, "success")
        supervisor._audit_loop = mock_audit

        await supervisor._handle_execute()
        assert supervisor.state == SupervisorState.VERIFY
        assert supervisor.metrics.fixes_attempted == 1
        assert supervisor.metrics.fixes_succeeded == 1

    @pytest.mark.asyncio
    async def test_handle_verify_checks_fidelity(self, supervisor: Supervisor24x7):
        """VERIFY checks execution fidelity."""
        supervisor.state = SupervisorState.VERIFY
        supervisor._execution_results = [
            {"task": "test", "fix": "test_fix", "success": True, "detail": "ok"}
        ]

        await supervisor._handle_verify()
        assert supervisor.state == SupervisorState.REMEMBER
        assert "fidelity" in supervisor._execution_results[0]

    @pytest.mark.asyncio
    async def test_handle_idle_watch(self, supervisor: Supervisor24x7):
        """IDLE_WATCH increments cycle count."""
        supervisor.state = SupervisorState.IDLE_WATCH
        supervisor.interval_sec = 0.1
        await supervisor._handle_idle_watch()
        assert supervisor.metrics.cycles_completed == 1
        assert supervisor.state == SupervisorState.OBSERVE

    @pytest.mark.asyncio
    async def test_stop(self, supervisor: Supervisor24x7):
        """stop() signals shutdown."""
        await supervisor.stop()
        assert supervisor._stop_event.is_set()

    @pytest.mark.asyncio
    async def test_run_disabled(self, supervisor: Supervisor24x7):
        """run() returns immediately when disabled."""
        supervisor.enabled = False
        await supervisor.run()


class TestSupervisorIntegration:
    """Integration tests for full state machine cycle."""

    @pytest.fixture
    def repo_root(self, tmp_path: Path) -> Path:
        """Create temporary repo root with required directories."""
        (tmp_path / "modules/infrastructure/wre_core/memory").mkdir(parents=True)
        return tmp_path

    @pytest.mark.asyncio
    async def test_full_cycle_no_events(self, repo_root: Path):
        """Run full cycle with no events."""
        supervisor = Supervisor24x7(repo_root=repo_root)
        supervisor.interval_sec = 0.1

        await supervisor._handle_boot()
        assert supervisor.state == SupervisorState.PREFLIGHT

        await supervisor._handle_preflight()
        assert supervisor.state == SupervisorState.OBSERVE

        await supervisor._handle_observe()
        assert supervisor.state == SupervisorState.IDLE_WATCH

        await supervisor._handle_idle_watch()
        assert supervisor.state == SupervisorState.OBSERVE
        assert supervisor.metrics.cycles_completed == 1

    @pytest.mark.asyncio
    async def test_full_cycle_with_events(self, repo_root: Path):
        """Run full cycle with mocked events."""
        supervisor = Supervisor24x7(repo_root=repo_root)
        supervisor.interval_sec = 0.1

        # Run boot first to initialize what it can
        await supervisor._handle_boot()

        # Now override with mock components (after boot)
        mock_audit = MagicMock()
        mock_audit.scan_once.return_value = [MagicMock(signature="test_error")]
        mock_audit._recommend_fix.return_value = "test_fix"
        mock_audit.allowed_fixes = {"test_fix"}
        mock_audit._apply_policy_fix.return_value = (True, "fixed")
        mock_audit._signature_stats = {}
        mock_audit._thread = MagicMock()
        mock_audit._thread.is_alive.return_value = True
        supervisor._audit_loop = mock_audit

        # Run through remaining states
        await supervisor._handle_preflight()
        await supervisor._handle_observe()
        assert supervisor.state == SupervisorState.TRIAGE

        await supervisor._handle_triage()
        assert supervisor.state == SupervisorState.PLAN

        await supervisor._handle_plan()
        assert supervisor.state == SupervisorState.EXECUTE

        await supervisor._handle_execute()
        assert supervisor.state == SupervisorState.VERIFY
        assert supervisor.metrics.fixes_attempted == 1

        await supervisor._handle_verify()
        assert supervisor.state == SupervisorState.REMEMBER

        await supervisor._handle_remember()
        assert supervisor.state == SupervisorState.ESCALATE

        await supervisor._handle_escalate()
        assert supervisor.state == SupervisorState.IDLE_WATCH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
