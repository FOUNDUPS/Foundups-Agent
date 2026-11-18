"""Tests for OpenClaw bounded maintenance task selector.

Validates safe task selection, HoloIndex bundle usage, escalation paths,
and report artifact generation.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestMaintenanceTaskDataclass:
    """Test MaintenanceTask dataclass behavior."""

    def test_task_with_allowed_family_is_safe(self):
        """Task with allowed family and low risk is safe."""
        from modules.communication.moltbot_bridge.src.openclaw_maintenance_selector import (
            MaintenanceTask,
        )

        task = MaintenanceTask(
            task_id="test-123",
            family="self_audit_fix",
            description="Apply self-audit policy fix",
            source="self_audit",
            risk_level="low",
        )
        assert task.is_safe() is True

    def test_task_with_blocked_family_is_not_safe(self):
        """Task with blocked family is not safe."""
        from modules.communication.moltbot_bridge.src.openclaw_maintenance_selector import (
            MaintenanceTask,
        )

        task = MaintenanceTask(
            task_id="test-123",
            family="source_edit",
            description="Edit source code",
            source="unknown",
            risk_level="high",
        )
        assert task.is_safe() is False

    def test_task_with_escalation_reason_is_not_safe(self):
        """Task with escalation reason is not safe."""
        from modules.communication.moltbot_bridge.src.openclaw_maintenance_selector import (
            MaintenanceTask,
        )

        task = MaintenanceTask(
            task_id="test-123",
            family="self_audit_fix",
            description="Fix with code edit",
            source="self_audit",
            risk_level="low",
            escalation_reason="Contains source modification keywords",
        )
        assert task.is_safe() is False

    def test_to_dict_serialization(self):
        """Task serializes correctly."""
        from modules.communication.moltbot_bridge.src.openclaw_maintenance_selector import (
            MaintenanceTask,
        )

        task = MaintenanceTask(
            task_id="test-123",
            family="grant_review",
            description="Review grant watchlist items",
            source="grant_review",
            risk_level="low",
            bundle_confidence=0.75,
            execution_hints=["Check report exists"],
        )
        result = task.to_dict()

        assert result["task_id"] == "test-123"
        assert result["family"] == "grant_review"
        assert result["is_safe"] is True
        assert result["bundle_confidence"] == 0.75


class TestSelectMaintenanceTask:
    """Test select_maintenance_task function."""

    def test_no_pending_tasks_returns_none(self):
        """Empty pending tasks returns no selection."""
        from modules.communication.moltbot_bridge.src.openclaw_maintenance_selector import (
            select_maintenance_task,
        )

        result = select_maintenance_task(
            pending_tasks=[],
            observation={},
            repo_root=Path("."),
        )

        assert result.selected_task is None
        assert result.selection_reason == "no_pending_tasks"
        assert result.candidates_evaluated == 0

    def test_selects_safe_self_audit_task(self):
        """Selects safe self-audit task from pending."""
        from modules.communication.moltbot_bridge.src.openclaw_maintenance_selector import (
            select_maintenance_task,
        )

        pending_tasks = [
            {
                "task_id": "task-001",
                "description": "Apply policy fix for IronClaw",
                "context": {"source": "self_audit"},
                "required_skills": [],
            }
        ]

        with patch(
            "modules.communication.moltbot_bridge.src.openclaw_execution_bundle.build_execution_bundle"
        ) as mock_bundle:
            mock_bundle.return_value = MagicMock(
                confidence=0.8,
                candidate_paths=[],
                verification_hints=["Check fix applied"],
            )
            result = select_maintenance_task(
                pending_tasks=pending_tasks,
                observation={},
                repo_root=Path("."),
            )

        assert result.selected_task is not None
        assert result.selected_task.family == "self_audit_fix"
        assert result.selected_task.is_safe() is True
        assert result.bundle_used is True
        assert result.selection_reason == "safe_task_selected"

    def test_escalates_source_edit_task(self):
        """Escalates task with source edit keywords (valid family but blocked pattern)."""
        from modules.communication.moltbot_bridge.src.openclaw_maintenance_selector import (
            select_maintenance_task,
        )

        pending_tasks = [
            {
                "task_id": "task-002",
                "description": "Refactor the self-audit module code",
                "context": {"source": "self_audit"},  # Valid source maps to self_audit_fix
                "required_skills": [],
            }
        ]

        result = select_maintenance_task(
            pending_tasks=pending_tasks,
            observation={},
            repo_root=Path("."),
        )

        assert result.selected_task is not None
        assert result.selected_task.is_safe() is False
        assert result.selected_task.escalation_reason is not None
        assert "source" in result.selected_task.escalation_reason.lower()
        assert result.selection_reason == "escalation_required"

    def test_skips_unknown_family_tasks(self):
        """Skips tasks with unknown family."""
        from modules.communication.moltbot_bridge.src.openclaw_maintenance_selector import (
            select_maintenance_task,
        )

        pending_tasks = [
            {
                "task_id": "task-003",
                "description": "Some random task without matching family",
                "context": {"source": "unknown_source"},
                "required_skills": ["unknown-skill"],
            }
        ]

        result = select_maintenance_task(
            pending_tasks=pending_tasks,
            observation={},
            repo_root=Path("."),
        )

        assert result.selected_task is None
        assert result.selection_reason == "no_safe_tasks_found"
        assert result.candidates_evaluated == 1

    def test_selects_grant_review_task(self):
        """Selects grant review task via required_skills."""
        from modules.communication.moltbot_bridge.src.openclaw_maintenance_selector import (
            select_maintenance_task,
        )

        pending_tasks = [
            {
                "task_id": "task-004",
                "description": "Review grant watchlist",
                "context": {"source": "grant"},
                "required_skills": ["openclaw-grants"],
            }
        ]

        with patch(
            "modules.communication.moltbot_bridge.src.openclaw_execution_bundle.build_execution_bundle"
        ) as mock_bundle:
            mock_bundle.return_value = MagicMock(
                confidence=0.6,
                candidate_paths=[],
                verification_hints=[],
            )
            result = select_maintenance_task(
                pending_tasks=pending_tasks,
                observation={},
                repo_root=Path("."),
            )

        assert result.selected_task is not None
        assert result.selected_task.family == "grant_review"
        assert result.selected_task.is_safe() is True

    def test_postmerge_selection_does_not_recursively_query_holoindex(self):
        from modules.communication.moltbot_bridge.src.openclaw_maintenance_selector import (
            select_maintenance_task,
        )

        task = {
            "task_id": "holoindex_postmerge_refresh:" + ("a" * 40),
            "description": "Refresh exact SHA HoloIndex authority",
            "context": {"source": "holoindex_postmerge_coordinator"},
            "required_skills": ["holo-search"],
        }
        with patch(
            "modules.communication.moltbot_bridge.src.openclaw_execution_bundle.build_execution_bundle"
        ) as build_bundle:
            result = select_maintenance_task(
                pending_tasks=[task], observation={}, repo_root=Path("."),
            )

        assert result.selected_task is not None
        assert result.selected_task.family == "holoindex_postmerge"
        assert result.selected_task.bundle_confidence == 0.0
        assert result.bundle_used is False
        build_bundle.assert_not_called()


class TestWriteMaintenanceReport:
    """Test maintenance report artifact generation."""

    def test_writes_report_to_workspace(self):
        """Report written to workspace/reports directory."""
        from modules.communication.moltbot_bridge.src.openclaw_maintenance_selector import (
            MaintenanceSelectionResult,
            MaintenanceTask,
            write_maintenance_report,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            reports_dir = repo_root / "modules" / "communication" / "moltbot_bridge" / "workspace" / "reports"

            task = MaintenanceTask(
                task_id="test-123",
                family="self_audit_fix",
                description="Test task",
                source="self_audit",
                risk_level="low",
            )
            selection = MaintenanceSelectionResult(
                selected_task=task,
                candidates_evaluated=1,
                selection_reason="safe_task_selected",
                bundle_used=True,
            )
            action_result = {"ok": True, "executor": "test", "execution_time_ms": 100}
            verify_result = {"ok": True, "fidelity": 0.9}

            report_path = write_maintenance_report(
                selection, action_result, verify_result, repo_root
            )

            assert report_path.exists()
            assert report_path.parent == reports_dir
            assert "maintenance_cycle_" in report_path.name

            content = json.loads(report_path.read_text())
            assert content["outcome"] == "success"
            assert content["selection"]["selected_task"]["task_id"] == "test-123"
            assert content["execution"]["ok"] is True
            assert content["verification"]["fidelity"] == 0.9

    def test_writes_failure_report(self):
        """Report captures failure state."""
        from modules.communication.moltbot_bridge.src.openclaw_maintenance_selector import (
            MaintenanceSelectionResult,
            MaintenanceTask,
            write_maintenance_report,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)

            task = MaintenanceTask(
                task_id="fail-456",
                family="grant_review",
                description="Failed task",
                source="grant_review",
                risk_level="low",
            )
            selection = MaintenanceSelectionResult(
                selected_task=task,
                candidates_evaluated=1,
                selection_reason="safe_task_selected",
                bundle_used=False,
            )
            action_result = {"ok": False, "error": "executor_failed", "execution_time_ms": 50}
            verify_result = {"ok": False, "fidelity": 0.0, "error": "task_not_completed"}

            report_path = write_maintenance_report(
                selection, action_result, verify_result, repo_root
            )

            content = json.loads(report_path.read_text())
            assert content["outcome"] == "failure"
            assert content["execution"]["ok"] is False
            assert content["verification"]["error"] == "task_not_completed"


class TestAllowedTaskFamilies:
    """Test allowed task family configuration."""

    def test_all_families_have_required_fields(self):
        """All allowed families have required configuration fields."""
        from modules.communication.moltbot_bridge.src.openclaw_maintenance_selector import (
            ALLOWED_TASK_FAMILIES,
        )

        for family, config in ALLOWED_TASK_FAMILIES.items():
            assert "description" in config, f"{family} missing description"
            assert "risk" in config, f"{family} missing risk"
            assert config["risk"] == "low", f"{family} should be low risk"
            assert "sources" in config, f"{family} missing sources"
            assert "required_skills" in config, f"{family} missing required_skills"

    def test_blocked_families_have_reasons(self):
        """All blocked families have escalation reasons."""
        from modules.communication.moltbot_bridge.src.openclaw_maintenance_selector import (
            BLOCKED_TASK_FAMILIES,
        )

        for family, reason in BLOCKED_TASK_FAMILIES.items():
            assert isinstance(reason, str)
            assert len(reason) > 10  # Meaningful reason
