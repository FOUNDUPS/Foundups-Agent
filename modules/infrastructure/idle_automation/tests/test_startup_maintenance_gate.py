#!/usr/bin/env python3
"""
Tests for startup maintenance gate.

Verifies:
1. Stale detection works without heavy execution
2. Task queuing behavior
3. Never blocks startup
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))


class TestStartupMaintenanceDetection:
    """Tests for maintenance detection logic."""

    def test_detects_stale_self_research(self, tmp_path):
        """Detects stale self-research status."""
        from modules.infrastructure.idle_automation.src.startup_maintenance_gate import (
            StartupMaintenanceGate,
        )

        gate = StartupMaintenanceGate(repo_root=REPO_ROOT)
        check = gate.check_self_research_status()

        # Should have expected structure
        assert "artifact" in check
        assert "stale" in check
        assert check["artifact"] == "self_research_status"
        assert isinstance(check["stale"], bool)

    def test_detects_stale_holo_index(self):
        """Detects stale HoloIndex."""
        from modules.infrastructure.idle_automation.src.startup_maintenance_gate import (
            StartupMaintenanceGate,
        )

        gate = StartupMaintenanceGate(repo_root=REPO_ROOT)
        check = gate.check_holo_index_freshness()

        assert "artifact" in check
        assert check["artifact"] == "holo_index"
        assert "stale" in check

    def test_detects_training_readiness(self):
        """Detects training readiness without running training."""
        from modules.infrastructure.idle_automation.src.startup_maintenance_gate import (
            StartupMaintenanceGate,
        )

        gate = StartupMaintenanceGate(repo_root=REPO_ROOT)
        check = gate.check_training_readiness()

        assert "artifact" in check
        assert check["artifact"] == "training_readiness"
        assert "training_due" in check
        assert "stale" in check

    def test_detects_model_routing_status(self):
        """Detects model routing status staleness."""
        from modules.infrastructure.idle_automation.src.startup_maintenance_gate import (
            StartupMaintenanceGate,
        )

        gate = StartupMaintenanceGate(repo_root=REPO_ROOT)
        check = gate.check_model_routing_status()

        assert "artifact" in check
        assert check["artifact"] == "model_routing_status"
        assert "stale" in check

    def test_detect_maintenance_needs_returns_summary(self):
        """detect_maintenance_needs returns complete summary."""
        from modules.infrastructure.idle_automation.src.startup_maintenance_gate import (
            StartupMaintenanceGate,
        )

        gate = StartupMaintenanceGate(repo_root=REPO_ROOT)
        result = gate.detect_maintenance_needs()

        assert "checked_at" in result
        assert "checks" in result
        assert "stale_count" in result
        assert "training_due" in result
        assert "maintenance_needed" in result

        # Checks should have all 4 artifacts
        assert "self_research" in result["checks"]
        assert "holo_index" in result["checks"]
        assert "training" in result["checks"]
        assert "model_routing" in result["checks"]


class TestStartupMaintenanceQueueing:
    """Tests for task queueing behavior."""

    def test_queues_tasks_when_stale(self):
        """Queues maintenance tasks when artifacts are stale."""
        from modules.infrastructure.idle_automation.src.startup_maintenance_gate import (
            StartupMaintenanceGate,
        )

        # Mock detection with stale artifacts
        detection = {
            "checked_at": "2026-03-24T00:00:00+00:00",
            "checks": {
                "self_research": {"stale": True, "age_hours": 24.0},
                "holo_index": {"stale": True, "code_stale": True, "wsp_stale": False},
                "training": {"stale": True, "training_due": False},
                "model_routing": {"stale": False},
            },
            "stale_count": 3,
            "training_due": False,
            "maintenance_needed": True,
        }

        gate = StartupMaintenanceGate(repo_root=REPO_ROOT)

        # Mock AgentDB
        mock_db = MagicMock()
        mock_db.create_autonomous_task.return_value = True
        mock_db.db.execute_write.return_value = 1

        with patch("modules.infrastructure.database.src.agent_db.AgentDB", return_value=mock_db):
            queued = gate.queue_maintenance_tasks(detection)

        # Should queue self_research and holo_index (both stale)
        # Training is stale but training_due=False, so not queued
        queued_types = [q["type"] for q in queued]
        assert "self_research_refresh" in queued_types
        assert "holo_index_refresh" in queued_types
        assert "training_batch" not in queued_types  # training_due=False

    def test_does_not_queue_training_unless_due(self):
        """Training batch only queued when explicitly due."""
        from modules.infrastructure.idle_automation.src.startup_maintenance_gate import (
            StartupMaintenanceGate,
        )

        # Mock detection: training stale but NOT due
        detection = {
            "checked_at": "2026-03-24T00:00:00+00:00",
            "checks": {
                "self_research": {"stale": False},
                "holo_index": {"stale": False},
                "training": {"stale": True, "training_due": False},  # Stale but not due
                "model_routing": {"stale": False},
            },
            "stale_count": 1,
            "training_due": False,
            "maintenance_needed": True,
        }

        gate = StartupMaintenanceGate(repo_root=REPO_ROOT)

        mock_db = MagicMock()
        mock_db.create_autonomous_task.return_value = True

        with patch("modules.infrastructure.database.src.agent_db.AgentDB", return_value=mock_db):
            queued = gate.queue_maintenance_tasks(detection)

        # Training should NOT be queued (not due)
        queued_types = [q["type"] for q in queued]
        assert "training_batch" not in queued_types

    def test_queues_training_when_due_and_stale(self):
        """Training batch queued when both due AND stale."""
        from modules.infrastructure.idle_automation.src.startup_maintenance_gate import (
            StartupMaintenanceGate,
        )

        # Mock detection: training is BOTH stale AND due
        detection = {
            "checked_at": "2026-03-24T00:00:00+00:00",
            "checks": {
                "self_research": {"stale": False},
                "holo_index": {"stale": False},
                "training": {"stale": True, "training_due": True, "checkpoint_line": 5000},
                "model_routing": {"stale": False},
            },
            "stale_count": 1,
            "training_due": True,
            "maintenance_needed": True,
        }

        gate = StartupMaintenanceGate(repo_root=REPO_ROOT)

        mock_db = MagicMock()
        mock_db.create_autonomous_task.return_value = True
        mock_db.db.execute_write.return_value = 1

        with patch("modules.infrastructure.database.src.agent_db.AgentDB", return_value=mock_db):
            queued = gate.queue_maintenance_tasks(detection)

        # Training SHOULD be queued (both stale AND due)
        queued_types = [q["type"] for q in queued]
        assert "training_batch" in queued_types


class TestStartupMaintenanceNonBlocking:
    """Tests that startup is never blocked."""

    def test_run_always_returns_true(self):
        """run_startup_maintenance_gate always returns True (non-blocking)."""
        from modules.infrastructure.idle_automation.src.startup_maintenance_gate import (
            run_startup_maintenance_gate,
        )

        # Should return True even if everything is stale
        result = run_startup_maintenance_gate(repo_root=REPO_ROOT, queue_tasks=False)
        assert result is True

    def test_returns_true_on_import_error(self):
        """Returns True even if dependencies fail to import."""
        from modules.infrastructure.idle_automation.src.startup_maintenance_gate import (
            run_startup_maintenance_gate,
        )

        # Patch to simulate import error
        with patch(
            "modules.infrastructure.idle_automation.src.startup_maintenance_gate.StartupMaintenanceGate",
            side_effect=ImportError("test"),
        ):
            # Should still return True (non-blocking)
            result = run_startup_maintenance_gate(repo_root=REPO_ROOT)
            # Note: The function catches ImportError internally
            assert result is True

    def test_returns_true_on_exception(self):
        """Returns True even on unexpected exceptions."""
        from modules.infrastructure.idle_automation.src.startup_maintenance_gate import (
            run_startup_maintenance_gate,
        )

        # Patch to simulate exception
        with patch(
            "modules.infrastructure.idle_automation.src.startup_maintenance_gate.StartupMaintenanceGate.detect_maintenance_needs",
            side_effect=RuntimeError("test exception"),
        ):
            result = run_startup_maintenance_gate(repo_root=REPO_ROOT)
            assert result is True


class TestStartupMaintenanceNoHeavyWork:
    """Tests that no heavy work is done inline."""

    def test_does_not_run_holo_index_refresh_inline(self):
        """HoloIndex refresh is queued, not run inline."""
        from modules.infrastructure.idle_automation.src.startup_maintenance_gate import (
            StartupMaintenanceGate,
        )

        gate = StartupMaintenanceGate(repo_root=REPO_ROOT)

        # Run detection - should be fast
        import time

        start = time.monotonic()
        result = gate.detect_maintenance_needs()
        elapsed = time.monotonic() - start

        # Detection should be fast (< 5 seconds)
        # HoloIndex refresh takes 15-30 seconds - if it ran, this would fail
        assert elapsed < 5.0, f"Detection took {elapsed:.1f}s - too slow, may be doing heavy work"

    def test_does_not_run_training_inline(self):
        """Training is queued, not run inline."""
        from modules.infrastructure.idle_automation.src.startup_maintenance_gate import (
            StartupMaintenanceGate,
        )

        gate = StartupMaintenanceGate(repo_root=REPO_ROOT)

        # Run full gate including queueing
        import time

        start = time.monotonic()

        mock_db = MagicMock()
        mock_db.create_autonomous_task.return_value = True
        mock_db.db.execute_write.return_value = 1

        with patch("modules.infrastructure.database.src.agent_db.AgentDB", return_value=mock_db):
            result = gate.run(queue_tasks=True)

        elapsed = time.monotonic() - start

        # Full run should still be fast (< 5 seconds)
        # Training takes 30+ seconds - if it ran, this would fail
        assert elapsed < 5.0, f"Full run took {elapsed:.1f}s - too slow, may be doing heavy work"


class TestStartupTaskExecution:
    """Integration tests proving queued tasks are executable through run_task.py."""

    def test_model_status_task_executes(self, tmp_path):
        """startup_refresh_model_status task executes through dispatch path."""
        from modules.communication.moltbot_bridge.scripts.run_task import (
            _try_startup_maintenance_dispatch,
        )

        result = _try_startup_maintenance_dispatch(
            repo_root=REPO_ROOT,
            task_id="startup_refresh_model_status",
            context={"source": "startup_maintenance_gate"},
        )

        assert result is not None, "Model status task should have an executor"
        assert result["executor"] == "startup:model_status"
        # ok can be True or False depending on LM Studio state, but should not error
        assert "detail" in result

    def test_holo_index_task_executes(self, tmp_path):
        """startup_refresh_holo_index task executes through dispatch path."""
        from modules.communication.moltbot_bridge.scripts.run_task import (
            _try_startup_maintenance_dispatch,
        )
        from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_maintenance_handshake import (
            RedDogHoloIndexOperationalResult,
        )

        with patch(
            "modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_maintenance_handshake.ensure_reddog_holoindex_operational",
            return_value=RedDogHoloIndexOperationalResult(
                ready=True,
                status="READY",
                refreshed=False,
                error="",
                repo_head_sha="a" * 40,
                generation_id=f"sha256:{'b' * 64}",
                freshness_receipt_digest=f"sha256:{'c' * 64}",
                freshness_reasons=(),
            ),
        ) as mock_ensure:
            result = _try_startup_maintenance_dispatch(
                repo_root=tmp_path,
                task_id="startup_refresh_holo_index",
                context={"source": "startup_maintenance_gate"},
            )

        mock_ensure.assert_called_once_with(
            repo_root=tmp_path,
            requested=True,
            auto_maintenance=True,
        )
        assert result is not None, "HoloIndex task should have an executor"
        assert result["executor"] == "startup:holo_index"
        assert result["ok"] is True
        expected_receipt = {
            "ready": True,
            "status": "READY",
            "refreshed": False,
            "error": "",
            "repo_head_sha": "a" * 40,
            "generation_id": f"sha256:{'b' * 64}",
            "freshness_receipt_digest": f"sha256:{'c' * 64}",
            "freshness_reasons": [],
        }
        assert result["structured_result"] == expected_receipt
        assert json.loads(result["detail"]) == expected_receipt

    def test_self_research_task_executes_live(self):
        """startup_refresh_self_research executes through live dispatch (no mocking)."""
        from modules.communication.moltbot_bridge.scripts.run_task import (
            _try_startup_maintenance_dispatch,
        )

        # Live dispatch - verifies correct SelfResearchRefresher.run() kwargs
        result = _try_startup_maintenance_dispatch(
            repo_root=REPO_ROOT,
            task_id="startup_refresh_self_research",
            context={"source": "startup_maintenance_gate"},
        )

        assert result is not None, "Self research task should have an executor"
        assert result["executor"] == "startup:self_research"
        # Critical: no "unexpected keyword argument" in detail
        assert "unexpected keyword" not in result.get("detail", "").lower()
        # Regression: success detection uses generated_on, not status field
        assert result["ok"] is True, "Self research should return ok=True when report has generated_on"

    def test_training_batch_task_executes_live(self):
        """startup_training_batch executes through live dispatch (IdleAutomationDAE)."""
        from modules.communication.moltbot_bridge.scripts.run_task import (
            _try_startup_maintenance_dispatch,
        )

        # Live dispatch - verifies correct IdleAutomationDAE._execute_pattern_training() call
        result = _try_startup_maintenance_dispatch(
            repo_root=REPO_ROOT,
            task_id="startup_training_batch",
            context={"source": "startup_maintenance_gate"},
        )

        assert result is not None, "Training batch task should have an executor"
        assert result["executor"] == "startup:training_batch"
        # ok may be True or False depending on training state, but should not error
        assert "detail" in result
        # Critical: no "unexpected keyword argument" in detail
        assert "unexpected keyword" not in result.get("detail", "").lower()
        # Should have structured training result
        structured = result.get("structured_result", {})
        assert "task" in structured or "error" in result.get("detail", "")

    def test_unknown_task_returns_none(self):
        """Unknown startup task returns None (falls through to no_executor_matched)."""
        from modules.communication.moltbot_bridge.scripts.run_task import (
            _try_startup_maintenance_dispatch,
        )

        result = _try_startup_maintenance_dispatch(
            repo_root=REPO_ROOT,
            task_id="startup_unknown_task",
            context={"source": "startup_maintenance_gate"},
        )

        assert result is None, "Unknown task should return None"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
