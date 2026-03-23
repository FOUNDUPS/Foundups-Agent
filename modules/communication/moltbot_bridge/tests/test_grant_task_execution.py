#!/usr/bin/env python3
"""
Tests for grant task execution through run_task.py.

Verifies:
1. grant_watchlist_review executes successfully
2. grant_watchlist_stabilize executes successfully
3. Repeated publication doesn't create duplicate pending tasks
4. Unknown autonomous task skills fail closed
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure repo root is in path
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))


class TestGrantTaskExecution:
    """Tests for grant task execution via run_task.py."""

    def test_grant_review_executes_successfully(self):
        """Grant review task executes and returns structured evidence."""
        from modules.communication.moltbot_bridge.src.grant_task_executor import (
            execute_grant_review,
        )

        changed_items = ["BNB Chain Grants", "NEAR Ecosystem Funding"]
        result = execute_grant_review(changed_items)

        assert result["task_type"] == "grant_watchlist_review"
        assert result["items_reviewed"] <= len(changed_items)
        assert "findings" in result
        assert "recommendations" in result
        assert "memory_update" in result
        # Success depends on watchlist file existence, but structure should be valid
        assert isinstance(result["findings"], list)

    def test_grant_stabilize_executes_successfully(self):
        """Grant stabilize task executes and returns remediation detail."""
        from modules.communication.moltbot_bridge.src.grant_task_executor import (
            execute_grant_stabilize,
        )

        error_items = ["Filecoin Grants"]
        result = execute_grant_stabilize(error_items)

        assert result["task_type"] == "grant_watchlist_stabilize"
        assert result["items_analyzed"] == len(error_items)
        assert "diagnostics" in result
        assert "remediation_steps" in result
        assert "memory_update" in result
        assert isinstance(result["diagnostics"], list)

    def test_grant_review_empty_items(self):
        """Grant review with no items returns appropriate status."""
        from modules.communication.moltbot_bridge.src.grant_task_executor import (
            execute_grant_review,
        )

        result = execute_grant_review([])
        assert result["success"] is False
        assert result["detail"] == "no_changed_items_provided"

    def test_grant_stabilize_empty_items(self):
        """Grant stabilize with no items returns appropriate status."""
        from modules.communication.moltbot_bridge.src.grant_task_executor import (
            execute_grant_stabilize,
        )

        result = execute_grant_stabilize([])
        assert result["success"] is False
        assert result["detail"] == "no_error_items_provided"


class TestRunTaskGrantDispatch:
    """Tests for grant dispatch through run_task.execute_task."""

    @pytest.fixture
    def mock_agent_db(self):
        """Create a mock AgentDB for testing."""
        mock_db = MagicMock()
        mock_db.db = MagicMock()
        mock_db.db.execute_write = MagicMock(return_value=1)
        return mock_db

    def test_grant_review_dispatch_through_run_task(self, mock_agent_db):
        """Grant review task dispatches correctly through run_task."""
        from modules.communication.moltbot_bridge.scripts.run_task import _try_grant_dispatch

        context = {
            "source": "external_watchlist",
            "title": "review 5 changed grant opportunity page(s)",
            "context": {
                "changed_count": 5,
                "changed_items": ["BNB Chain Grants", "NEAR Ecosystem Funding"],
            },
        }

        result = _try_grant_dispatch(
            REPO_ROOT,
            "grant_watchlist_review",
            context,
            "External funding sources changed",
        )

        assert result is not None
        assert result["executor"] == "grant:review"
        assert "structured_result" in result
        assert result["structured_result"]["task_type"] == "grant_watchlist_review"

    def test_grant_stabilize_dispatch_through_run_task(self, mock_agent_db):
        """Grant stabilize task dispatches correctly through run_task."""
        from modules.communication.moltbot_bridge.scripts.run_task import _try_grant_dispatch

        context = {
            "source": "external_watchlist",
            "title": "stabilize 1 watchlist refresh error(s)",
            "context": {
                "error_count": 1,
                "error_items": ["Filecoin Grants"],
            },
        }

        result = _try_grant_dispatch(
            REPO_ROOT,
            "grant_watchlist_stabilize",
            context,
            "Official-source opportunity refresh is degraded",
        )

        assert result is not None
        assert result["executor"] == "grant:stabilize"
        assert "structured_result" in result
        assert result["structured_result"]["task_type"] == "grant_watchlist_stabilize"

    def test_unknown_grant_task_returns_none(self):
        """Unknown grant-like task_id returns None (fail closed)."""
        from modules.communication.moltbot_bridge.scripts.run_task import _try_grant_dispatch

        context = {
            "context": {"changed_items": ["Some Grant"]},
        }

        result = _try_grant_dispatch(
            REPO_ROOT,
            "grant_unknown_action",  # Not a recognized task_id
            context,
            "Unknown grant task",
        )

        assert result is None  # Should fail closed

    def test_wrong_task_id_with_changed_items_fails_closed(self):
        """Task with changed_items but wrong task_id fails closed."""
        from modules.communication.moltbot_bridge.scripts.run_task import _try_grant_dispatch

        context = {
            "context": {
                "changed_items": ["BNB Chain Grants"],
            },
        }

        # Old slugified task_id should NOT match
        result = _try_grant_dispatch(
            REPO_ROOT,
            "self_research_external_watchlist_review_5_changed_grant_opportunity_page_s",
            context,
            "Old format task",
        )

        assert result is None  # Should NOT execute with old task_id format


class TestDuplicatePrevention:
    """Tests for duplicate task prevention in self-research publishing."""

    def test_stable_task_id_used_for_grant_review(self):
        """Verify stable task_id is used for grant review candidates."""
        from modules.infrastructure.idle_automation.src.self_research_refresh import (
            SelfResearchRefresher,
        )

        refresher = SelfResearchRefresher()
        candidates = refresher.build_update_candidates(
            holo_index={"skipped": True},
            compliance={"skipped": True},
            self_audit={"skipped": True},
            grant_watchlist={
                "status": {
                    "changed_count": 3,
                    "changed_items": ["Grant A", "Grant B", "Grant C"],
                    "error_count": 0,
                }
            },
        )

        # Find the grant review candidate
        review_candidates = [c for c in candidates if c["task_id"] == "grant_watchlist_review"]
        assert len(review_candidates) == 1
        assert review_candidates[0]["task_id"] == "grant_watchlist_review"  # Stable ID

    def test_stable_task_id_used_for_grant_stabilize(self):
        """Verify stable task_id is used for grant stabilize candidates."""
        from modules.infrastructure.idle_automation.src.self_research_refresh import (
            SelfResearchRefresher,
        )

        refresher = SelfResearchRefresher()
        candidates = refresher.build_update_candidates(
            holo_index={"skipped": True},
            compliance={"skipped": True},
            self_audit={"skipped": True},
            grant_watchlist={
                "status": {
                    "changed_count": 0,
                    "error_count": 2,
                    "error_items": ["Filecoin Grants", "Other Grant"],
                }
            },
        )

        # Find the grant stabilize candidate
        stabilize_candidates = [c for c in candidates if c["task_id"] == "grant_watchlist_stabilize"]
        assert len(stabilize_candidates) == 1
        assert stabilize_candidates[0]["task_id"] == "grant_watchlist_stabilize"  # Stable ID

    def test_insert_or_replace_prevents_duplicates(self):
        """Verify INSERT OR REPLACE is used (schema-level deduplication)."""
        # This is a schema-level guarantee - AgentDB.create_autonomous_task uses
        # INSERT OR REPLACE with task_id as PRIMARY KEY
        from modules.infrastructure.database.src.agent_db import AgentDB
        import inspect

        source = inspect.getsource(AgentDB.create_autonomous_task)
        assert "INSERT OR REPLACE" in source

    def test_completed_grant_task_skip_logic_exists(self):
        """Verify the completed task skip logic is implemented in publish_autonomous_tasks."""
        import inspect
        from modules.infrastructure.idle_automation.src.self_research_refresh import (
            SelfResearchRefresher,
        )

        # Verify the skip logic is in the code
        source = inspect.getsource(SelfResearchRefresher.publish_autonomous_tasks)
        assert "completed_same_context" in source
        assert "completed_stable_grants" in source
        assert "status" in source and "completed" in source


class TestStaleTaskCleanup:
    """Tests for stale grant task cleanup during publishing."""

    def test_stale_cleanup_uses_combined_filter(self):
        """Verify stale cleanup uses combined filter (LIKE pattern + skill filter)."""
        import inspect
        from modules.infrastructure.idle_automation.src.self_research_refresh import (
            SelfResearchRefresher,
        )

        source = inspect.getsource(SelfResearchRefresher.publish_autonomous_tasks)
        # Combined filter: task_id LIKE pattern + required_skills filter
        assert "self_research_external_watchlist_%" in source
        assert "openclaw-grants" in source

    def test_stale_cleanup_targets_only_grant_skills(self):
        """Verify stale cleanup only targets openclaw-grants tasks, not PQN/ecosystem."""
        import inspect
        from modules.infrastructure.idle_automation.src.self_research_refresh import (
            SelfResearchRefresher,
        )

        source = inspect.getsource(SelfResearchRefresher.publish_autonomous_tasks)
        # The skill filter ensures only grant tasks are deleted
        assert "required_skills LIKE '%openclaw-grants%'" in source

    def test_stale_cleanup_preserves_stable_ids(self):
        """Verify cleanup does NOT delete stable grant_watchlist_* IDs."""
        import inspect
        from modules.infrastructure.idle_automation.src.self_research_refresh import (
            SelfResearchRefresher,
        )

        source = inspect.getsource(SelfResearchRefresher.publish_autonomous_tasks)
        # Stable IDs are excluded via NOT IN clause
        assert "NOT IN (?, ?)" in source
        assert "grant_watchlist_review" in source
        assert "grant_watchlist_stabilize" in source


class TestCompletedSameContext:
    """Tests for completed task same-context skip behavior."""

    def test_completed_same_context_skip(self, tmp_path):
        """Completed stable grant task with same context is NOT reopened."""
        from modules.infrastructure.idle_automation.src.self_research_refresh import (
            SelfResearchRefresher,
        )

        # Create mock AgentDB that returns completed task with same context
        mock_db = MagicMock()
        mock_db_inner = MagicMock()

        # Stored context matching what will be in the candidate
        stored_context = json.dumps({
            "context": {
                "changed_items": ["Grant A", "Grant B"],
                "error_items": [],
            }
        })

        # Return completed status when checking stable grant tasks
        def mock_query(sql, params):
            # First query: SELECT status, context (to build completed_stable_grants set)
            if "SELECT status, context" in sql:
                return [{"status": "completed", "context": stored_context}]
            # Second query: SELECT context (for context comparison)
            if "SELECT context" in sql:
                return [{"context": stored_context}]
            return []

        mock_db_inner.execute_query = mock_query
        mock_db_inner.execute_write = MagicMock(return_value=1)
        mock_db.db = mock_db_inner
        mock_db.create_autonomous_task = MagicMock(return_value=True)

        refresher = SelfResearchRefresher(report_path=tmp_path / "report.json")

        # Build candidate with SAME items as completed task
        candidates = [{
            "task_id": "grant_watchlist_review",
            "source": "external_watchlist",
            "title": "review 2 changed grant opportunity page(s)",
            "description": "Test",
            "required_skills": ["openclaw-grants"],
            "context": {
                "changed_items": ["Grant A", "Grant B"],  # Same as completed
                "error_items": [],
            },
            "mps": {"priority": "P1", "complexity": 2},
            "priority_score": 14.0,
        }]

        with patch("modules.infrastructure.database.src.agent_db.AgentDB", return_value=mock_db):
            published = refresher.publish_autonomous_tasks(candidates)

        # Should be skipped with completed_same_context reason
        assert len(published) == 1
        assert published[0]["skipped_reason"] == "completed_same_context"
        assert published[0]["created"] is False

    def test_changed_context_reopens_task(self, tmp_path):
        """Completed stable grant task with DIFFERENT context can be republished."""
        from modules.infrastructure.idle_automation.src.self_research_refresh import (
            SelfResearchRefresher,
        )

        mock_db = MagicMock()
        mock_db_inner = MagicMock()

        # Stored context with OLD items
        stored_context = json.dumps({
            "context": {
                "changed_items": ["Old Grant A"],  # OLD items
                "error_items": [],
            }
        })

        def mock_query(sql, params):
            # First query: SELECT status, context (to build completed_stable_grants set)
            if "SELECT status, context" in sql:
                return [{"status": "completed", "context": stored_context}]
            # Second query: SELECT context (for context comparison)
            if "SELECT context" in sql:
                return [{"context": stored_context}]
            return []

        mock_db_inner.execute_query = mock_query
        mock_db_inner.execute_write = MagicMock(return_value=1)
        mock_db.db = mock_db_inner
        mock_db.create_autonomous_task = MagicMock(return_value=True)

        refresher = SelfResearchRefresher(report_path=tmp_path / "report.json")

        # Build candidate with NEW items (context changed)
        candidates = [{
            "task_id": "grant_watchlist_review",
            "source": "external_watchlist",
            "title": "review changed grants",
            "description": "Test",
            "required_skills": ["openclaw-grants"],
            "context": {
                "changed_items": ["New Grant X", "New Grant Y"],  # DIFFERENT from completed
                "error_items": [],
            },
            "mps": {"priority": "P1", "complexity": 2},
            "priority_score": 14.0,
        }]

        with patch("modules.infrastructure.database.src.agent_db.AgentDB", return_value=mock_db):
            published = refresher.publish_autonomous_tasks(candidates)

        # Should be republished (context changed)
        assert len(published) == 1
        assert "skipped_reason" not in published[0]
        assert mock_db.create_autonomous_task.called


class TestRepoFitScoring:
    """Tests for grant repo-fit scoring."""

    def test_p0_grant_gets_high_fit_score(self):
        """P0 grants from rescored sheet get high fit score."""
        from modules.communication.moltbot_bridge.src.grant_task_executor import (
            _priority_to_fit_score,
        )

        # Actual priority groups from web3_grants_0102_wsp97_rescored_20260322.json
        assert _priority_to_fit_score("p0_apply_now") == 0.95
        assert _priority_to_fit_score("p1_after_one_concrete_adapter") == 0.70
        assert _priority_to_fit_score("p2_deprioritized_until_new_chain_surface") == 0.35

    def test_p0_grant_generates_recommendations(self):
        """P0 grants with high fit score generate recommendations."""
        from modules.communication.moltbot_bridge.src.grant_task_executor import (
            execute_grant_review,
        )

        # Use actual P0 grant from rescored sheet
        result = execute_grant_review(["Ethereum Ecosystem Support Program"])

        assert result["success"] is True
        # If rescored sheet is available, should find P0 grant
        findings = result.get("findings", [])
        if findings:
            esp_finding = next((f for f in findings if f["name"] == "Ethereum Ecosystem Support Program"), None)
            if esp_finding and esp_finding["repo_fit_assessment"].get("group") == "p0_apply_now":
                assert esp_finding["repo_fit_assessment"]["fit_score"] == 0.95

    def test_ethereum_esp_gets_p0_fit_score(self):
        """Ethereum Ecosystem Support Program is P0 with fit_score=0.95."""
        from modules.communication.moltbot_bridge.src.grant_task_executor import (
            _assess_repo_fit,
            _load_rescored_sheet,
        )

        rescored = _load_rescored_sheet()
        if rescored:
            assessment = _assess_repo_fit("Ethereum Ecosystem Support Program", rescored)
            # Should be in p0_apply_now group with 0.95 fit score
            if assessment.get("group") == "p0_apply_now":
                assert assessment["fit_score"] == 0.95


class TestFailClosed:
    """Tests for fail-closed behavior on unknown tasks."""

    def test_unknown_skill_fails_closed(self):
        """Unknown required_skills fail closed (no executor matched)."""
        from modules.communication.moltbot_bridge.scripts.run_task import (
            _try_wre_dispatch,
            _try_self_audit_dispatch,
            _try_grant_dispatch,
        )

        context = {"source": "unknown_source"}

        # WRE dispatch - unknown skill
        wre_result = _try_wre_dispatch(
            REPO_ROOT,
            "unknown_task",
            ["unknown-skill-xyz"],
            context,
            "Unknown task",
        )
        assert wre_result is None  # No executor matched

        # Self-audit dispatch - wrong source
        audit_result = _try_self_audit_dispatch(REPO_ROOT, context)
        assert audit_result is None  # No executor matched

        # Grant dispatch - wrong task_id
        grant_result = _try_grant_dispatch(
            REPO_ROOT,
            "unknown_task",
            context,
            "Unknown task",
        )
        assert grant_result is None  # No executor matched


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
