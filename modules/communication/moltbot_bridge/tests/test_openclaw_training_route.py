"""Focused tests for OpenClaw training route surface.

Tests:
- Training intent classification
- Training status route
- Training due query
- Start training dispatcher contract
- Commander authorization
"""

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures and Helpers
# ---------------------------------------------------------------------------

@dataclass
class MockIntent:
    """Mock OpenClawIntent for testing."""
    raw_message: str
    is_authorized_commander: bool
    extracted_task: str = ""


class MockDAE:
    """Mock OpenClawDAE for testing."""
    pass


# ---------------------------------------------------------------------------
# Intent Classification Tests
# ---------------------------------------------------------------------------

class TestTrainingIntentClassification:
    """Test TRAINING intent category classification."""

    def test_training_category_exists(self):
        """TRAINING IntentCategory is defined."""
        from modules.communication.moltbot_bridge.src.openclaw_dae import IntentCategory

        assert hasattr(IntentCategory, "TRAINING")
        assert IntentCategory.TRAINING.value == "training"

    def test_training_keywords_defined(self):
        """Training keywords are defined in INTENT_KEYWORDS."""
        from modules.communication.moltbot_bridge.src.openclaw_dae import (
            IntentCategory,
            OpenClawDAE,
        )

        keywords = OpenClawDAE.INTENT_KEYWORDS.get(IntentCategory.TRAINING, [])
        assert len(keywords) > 0
        assert "training" in keywords
        assert "training status" in keywords

    def test_training_route_defined(self):
        """Training route is defined in DOMAIN_ROUTES."""
        from modules.communication.moltbot_bridge.src.openclaw_dae import (
            IntentCategory,
            OpenClawDAE,
        )

        route = OpenClawDAE.DOMAIN_ROUTES.get(IntentCategory.TRAINING)
        assert route == "training_controller"


# ---------------------------------------------------------------------------
# Commander Authorization Tests
# ---------------------------------------------------------------------------

class TestTrainingCommanderAuthorization:
    """Test that training commands require commander authority."""

    def test_non_commander_blocked(self):
        """Non-commander gets authorization error."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_training,
        )

        intent = MockIntent(
            raw_message="training status",
            is_authorized_commander=False,
        )
        result = execute_training(MockDAE(), intent)

        assert "require @012 authorization" in result
        assert "logged" in result

    def test_commander_allowed(self):
        """Commander gets training status."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_training,
        )

        intent = MockIntent(
            raw_message="training status",
            is_authorized_commander=True,
        )

        # Mock the status data fetch to avoid filesystem dependency
        with patch(
            "modules.communication.moltbot_bridge.src.openclaw_execution_routes._get_training_status_data"
        ) as mock_status:
            mock_status.return_value = {
                "checkpoint_line": 100000,
                "corpus_lines": 180000,
                "progress_pct": 55.5,
                "training_due": True,
                "exists": True,
                "age_hours": 2.0,
            }
            result = execute_training(MockDAE(), intent)

        assert "Training Status" in result
        assert "55.5%" in result


# ---------------------------------------------------------------------------
# Training Status Route Tests
# ---------------------------------------------------------------------------

class TestTrainingStatusRoute:
    """Test training status command."""

    def test_status_shows_checkpoint(self):
        """Status report shows checkpoint line."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            _get_training_status,
        )

        with patch(
            "modules.communication.moltbot_bridge.src.openclaw_execution_routes._get_training_status_data"
        ) as mock_status:
            mock_status.return_value = {
                "checkpoint_line": 150000,
                "corpus_lines": 180000,
                "progress_pct": 83.3,
                "training_due": True,
                "exists": False,
                "age_hours": None,
            }
            result = _get_training_status()

        assert "150000" in result
        assert "180000" in result

    def test_status_shows_progress_percentage(self):
        """Status report shows progress percentage."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            _get_training_status,
        )

        with patch(
            "modules.communication.moltbot_bridge.src.openclaw_execution_routes._get_training_status_data"
        ) as mock_status:
            mock_status.return_value = {
                "checkpoint_line": 171000,
                "corpus_lines": 180000,
                "progress_pct": 95.0,
                "training_due": False,
                "exists": True,
                "age_hours": 1.5,
            }
            result = _get_training_status()

        assert "95.0%" in result

    def test_status_shows_due_with_threshold(self):
        """Status report shows due status with threshold info."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            _get_training_status,
        )

        with patch(
            "modules.communication.moltbot_bridge.src.openclaw_execution_routes._get_training_status_data"
        ) as mock_status:
            mock_status.return_value = {
                "checkpoint_line": 50000,
                "corpus_lines": 180000,
                "progress_pct": 27.8,
                "training_due": True,
                "exists": False,
                "age_hours": None,
            }
            result = _get_training_status()

        assert "Due**: YES" in result
        assert "95%" in result  # threshold shown


# ---------------------------------------------------------------------------
# Training Due Query Tests
# ---------------------------------------------------------------------------

class TestTrainingDueQuery:
    """Test 'is training due' query."""

    def test_due_query_returns_yes_when_below_threshold(self):
        """Due query returns YES when progress < 95%."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_training,
        )

        intent = MockIntent(
            raw_message="is training due",
            is_authorized_commander=True,
        )

        with patch(
            "modules.communication.moltbot_bridge.src.openclaw_execution_routes._get_training_status_data"
        ) as mock_status:
            mock_status.return_value = {
                "checkpoint_line": 90000,
                "corpus_lines": 180000,
                "progress_pct": 50.0,
                "training_due": True,
            }
            result = execute_training(MockDAE(), intent)

        assert "YES" in result
        assert "50.0%" in result

    def test_due_query_returns_no_when_above_threshold(self):
        """Due query returns NO when progress >= 95%."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            execute_training,
        )

        intent = MockIntent(
            raw_message="is training due",
            is_authorized_commander=True,
        )

        with patch(
            "modules.communication.moltbot_bridge.src.openclaw_execution_routes._get_training_status_data"
        ) as mock_status:
            mock_status.return_value = {
                "checkpoint_line": 175000,
                "corpus_lines": 180000,
                "progress_pct": 97.2,
                "training_due": False,
            }
            result = execute_training(MockDAE(), intent)

        assert "NO" in result
        assert "97.2%" in result


# ---------------------------------------------------------------------------
# Start Training Dispatcher Contract Tests
# ---------------------------------------------------------------------------

class TestStartTrainingDispatcherContract:
    """Test that start training correctly interprets dispatcher results."""

    def test_start_training_reports_success_on_ok_true(self):
        """Start training reports STARTED when dispatcher returns ok=True."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            _start_training_batch,
        )

        with patch(
            "modules.communication.moltbot_bridge.scripts.run_task._try_startup_maintenance_dispatch"
        ) as mock_dispatch:
            mock_dispatch.return_value = {
                "ok": True,
                "detail": '{"patterns_processed": 100}',
                "executor": "startup:training_batch",
                "structured_result": {"patterns_processed": 100},
            }
            result = _start_training_batch()

        assert "STARTED" in result
        assert "startup:training_batch" in result

    def test_start_training_reports_failure_on_ok_false(self):
        """Start training reports FAILED when dispatcher returns ok=False."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            _start_training_batch,
        )

        with patch(
            "modules.communication.moltbot_bridge.scripts.run_task._try_startup_maintenance_dispatch"
        ) as mock_dispatch:
            mock_dispatch.return_value = {
                "ok": False,
                "detail": "training_error: PatternMemory unavailable",
                "executor": "startup:training_batch",
            }
            result = _start_training_batch()

        assert "FAILED" in result
        assert "training_error" in result

    def test_start_training_handles_none_dispatch(self):
        """Start training reports NOT STARTED when dispatcher returns None."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            _start_training_batch,
        )

        with patch(
            "modules.communication.moltbot_bridge.scripts.run_task._try_startup_maintenance_dispatch"
        ) as mock_dispatch:
            mock_dispatch.return_value = None
            result = _start_training_batch()

        assert "NOT STARTED" in result
        assert "None" in result

    def test_start_training_handles_exception(self):
        """Start training reports ERROR on exception."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            _start_training_batch,
        )

        with patch(
            "modules.communication.moltbot_bridge.scripts.run_task._try_startup_maintenance_dispatch",
            side_effect=RuntimeError("dispatcher crashed"),
        ):
            result = _start_training_batch()

        assert "ERROR" in result
        assert "Could not start" in result

    def test_start_training_reports_complete_when_already_processed(self):
        """Start training reports COMPLETE when corpus is fully processed."""
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            _start_training_batch,
        )

        with patch(
            "modules.communication.moltbot_bridge.scripts.run_task._try_startup_maintenance_dispatch"
        ) as mock_dispatch:
            # Simulate the "Already processed" case from idle_automation_dae
            mock_dispatch.return_value = {
                "ok": False,
                "detail": '{"error": "Already processed (checkpoint: 181786, total: 181786)"}',
                "executor": "startup:training_batch",
                "structured_result": {
                    "success": False,
                    "error": "Already processed (checkpoint: 181786, total: 181786)",
                },
            }
            result = _start_training_batch()

        assert "COMPLETE" in result
        assert "No new data to process" in result
        assert "FAILED" not in result


# ---------------------------------------------------------------------------
# Due/Progress Semantic Consistency Tests
# ---------------------------------------------------------------------------

class TestDueProgressConsistency:
    """Test that due and progress use consistent semantics."""

    def test_due_false_when_progress_above_95(self):
        """Training is NOT due when progress >= 95%."""
        from modules.infrastructure.idle_automation.src.startup_maintenance_gate import (
            StartupMaintenanceGate,
        )

        gate = StartupMaintenanceGate(Path("O:/Foundups-Agent"))

        with patch.object(gate, "repo_root", Path("O:/Foundups-Agent")):
            with patch(
                "holo_index.qwen_advisor.pattern_memory.PatternMemory"
            ) as MockMem:
                mock_mem = MagicMock()
                mock_mem.get_stats.return_value = {"checkpoint_line": 171000}
                MockMem.return_value = mock_mem

                with patch("builtins.open", create=True) as mock_open:
                    # Simulate 180000 line corpus
                    mock_open.return_value.__enter__.return_value = iter(range(180000))

                    result = gate.check_training_readiness()

        # 171000 / 180000 = 95.0% - NOT due
        assert result["training_due"] is False
        assert result["progress_pct"] >= 95.0

    def test_due_true_when_progress_below_95(self):
        """Training IS due when progress < 95%."""
        from modules.infrastructure.idle_automation.src.startup_maintenance_gate import (
            StartupMaintenanceGate,
        )

        gate = StartupMaintenanceGate(Path("O:/Foundups-Agent"))

        with patch.object(gate, "repo_root", Path("O:/Foundups-Agent")):
            with patch(
                "holo_index.qwen_advisor.pattern_memory.PatternMemory"
            ) as MockMem:
                mock_mem = MagicMock()
                mock_mem.get_stats.return_value = {"checkpoint_line": 90000}
                MockMem.return_value = mock_mem

                with patch("builtins.open", create=True) as mock_open:
                    # Simulate 180000 line corpus
                    mock_open.return_value.__enter__.return_value = iter(range(180000))

                    result = gate.check_training_readiness()

        # 90000 / 180000 = 50.0% - IS due
        assert result["training_due"] is True
        assert result["progress_pct"] < 95.0
