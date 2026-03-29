"""Tests for OpenClaw skill evolution report surface.

WSP Compliance: WSP 5 (Test Coverage), WSP 48 (Recursive Self-Improvement)

Verifies:
1. Report builder discovers only openclaw_ skills and classifies correctly
2. Supervisor integration: env gate, idle path, higher-priority blocking
3. Regression: no WRE mutation APIs called
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modules.infrastructure.database.src.db_manager import DatabaseManager


@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    DatabaseManager.reset_for_tests()
    yield
    DatabaseManager.reset_for_tests()


# ---------------------------------------------------------------------------
# 1. Report Builder Tests
# ---------------------------------------------------------------------------


class TestDiscoverOpenclawSkills:
    """discover_openclaw_skills() returns only openclaw_ prefixed skills."""

    @pytest.fixture
    def pattern_memory(self, tmp_path):
        """Create PatternMemory with test outcomes."""
        from modules.infrastructure.wre_core.src.pattern_memory import (
            PatternMemory,
            SkillOutcome,
        )

        db_path = tmp_path / "test_evolution.db"
        memory = PatternMemory(db_path=db_path)

        # Insert openclaw_ skills
        for i, skill in enumerate(["openclaw_code", "openclaw_chat", "openclaw_memory"]):
            memory.store_outcome(
                SkillOutcome(
                    execution_id=f"exec_{skill}_{i}",
                    skill_name=skill,
                    agent="openclaw_dae",
                    timestamp="2026-03-29T10:00:00",
                    input_context="{}",
                    output_result="{}",
                    success=True,
                    pattern_fidelity=0.85,
                    outcome_quality=0.9,
                    execution_time_ms=100,
                    step_count=1,
                )
            )

        # Insert non-openclaw skills (should be excluded)
        for skill in ["qwen_gitpush", "gemma_validate", "supervisor_start_openclaw"]:
            memory.store_outcome(
                SkillOutcome(
                    execution_id=f"exec_{skill}",
                    skill_name=skill,
                    agent="wre",
                    timestamp="2026-03-29T10:00:00",
                    input_context="{}",
                    output_result="{}",
                    success=True,
                    pattern_fidelity=0.95,
                    outcome_quality=0.9,
                    execution_time_ms=50,
                    step_count=1,
                )
            )

        return memory

    def test_discovers_only_openclaw_skills(self, pattern_memory):
        """Only skills with openclaw_ prefix are returned."""
        from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
            discover_openclaw_skills,
        )

        skills = discover_openclaw_skills(pattern_memory, days=7)

        assert len(skills) == 3
        assert all(s.startswith("openclaw_") for s in skills)
        assert "openclaw_code" in skills
        assert "openclaw_chat" in skills
        assert "openclaw_memory" in skills
        # Non-openclaw skills excluded
        assert "qwen_gitpush" not in skills
        assert "gemma_validate" not in skills

    def test_empty_when_no_openclaw_skills(self, tmp_path):
        """Returns empty list when no openclaw_ skills exist."""
        from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory
        from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
            discover_openclaw_skills,
        )

        db_path = tmp_path / "empty_evolution.db"
        memory = PatternMemory(db_path=db_path)

        skills = discover_openclaw_skills(memory, days=7)
        assert skills == []


class TestClassifySkillMetrics:
    """classify_skill_metrics() returns correct status and recommendation."""

    def test_insufficient_data_when_below_min_executions(self):
        """Returns insufficient_data when execution_count < min_executions."""
        from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
            classify_skill_metrics,
        )

        metrics = {"execution_count": 2, "avg_fidelity": 0.75}
        status, recommendation = classify_skill_metrics(metrics, min_executions=3)

        assert status == "insufficient_data"
        assert recommendation == "gather_more_data"

    def test_candidate_for_review_when_low_fidelity(self):
        """Returns candidate_for_review when fidelity below threshold."""
        from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
            classify_skill_metrics,
        )

        metrics = {"execution_count": 5, "avg_fidelity": 0.80}
        status, recommendation = classify_skill_metrics(
            metrics, min_executions=3, fidelity_threshold=0.90
        )

        assert status == "candidate_for_review"
        assert recommendation == "review_for_evolution"

    def test_healthy_when_above_threshold(self):
        """Returns healthy when fidelity >= threshold."""
        from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
            classify_skill_metrics,
        )

        metrics = {"execution_count": 10, "avg_fidelity": 0.95}
        status, recommendation = classify_skill_metrics(
            metrics, min_executions=3, fidelity_threshold=0.90
        )

        assert status == "healthy"
        assert recommendation == "no_action"


class TestBuildSkillEvolutionReport:
    """build_skill_evolution_report() produces correct contract."""

    @pytest.fixture
    def pattern_memory_with_candidates(self, tmp_path):
        """Create PatternMemory with a mix of healthy and candidate skills."""
        from modules.infrastructure.wre_core.src.pattern_memory import (
            PatternMemory,
            SkillOutcome,
        )

        db_path = tmp_path / "test_report.db"
        memory = PatternMemory(db_path=db_path)

        # Healthy skill (high fidelity)
        for i in range(5):
            memory.store_outcome(
                SkillOutcome(
                    execution_id=f"exec_healthy_{i}",
                    skill_name="openclaw_healthy",
                    agent="openclaw_dae",
                    timestamp="2026-03-29T10:00:00",
                    input_context="{}",
                    output_result="{}",
                    success=True,
                    pattern_fidelity=0.95,
                    outcome_quality=0.95,
                    execution_time_ms=100,
                    step_count=1,
                )
            )

        # Candidate skill (low fidelity)
        for i in range(5):
            memory.store_outcome(
                SkillOutcome(
                    execution_id=f"exec_candidate_{i}",
                    skill_name="openclaw_candidate",
                    agent="openclaw_dae",
                    timestamp="2026-03-29T10:00:00",
                    input_context="{}",
                    output_result="{}",
                    success=True,
                    pattern_fidelity=0.75,
                    outcome_quality=0.70,
                    execution_time_ms=200,
                    step_count=2,
                )
            )

        # Insufficient data skill (only 1 execution)
        memory.store_outcome(
            SkillOutcome(
                execution_id="exec_insufficient_0",
                skill_name="openclaw_insufficient",
                agent="openclaw_dae",
                timestamp="2026-03-29T10:00:00",
                input_context="{}",
                output_result="{}",
                success=True,
                pattern_fidelity=0.60,
                outcome_quality=0.60,
                execution_time_ms=300,
                step_count=1,
            )
        )

        return memory

    def test_report_has_canonical_top_level_fields(self, pattern_memory_with_candidates):
        """Report contains all required top-level fields."""
        from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
            build_skill_evolution_report,
        )

        report = build_skill_evolution_report(pattern_memory_with_candidates)

        assert "generated_on" in report
        assert "period_days" in report
        assert "min_executions" in report
        assert "fidelity_threshold" in report
        assert "skills_evaluated" in report
        assert "candidate_count" in report
        assert "candidates" in report

    def test_report_skills_evaluated_count(self, pattern_memory_with_candidates):
        """skills_evaluated counts all openclaw_ skills."""
        from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
            build_skill_evolution_report,
        )

        report = build_skill_evolution_report(pattern_memory_with_candidates)

        # 3 openclaw_ skills: healthy, candidate, insufficient
        assert report["skills_evaluated"] == 3

    def test_report_only_includes_candidates(self, pattern_memory_with_candidates):
        """candidates array only includes candidate_for_review skills."""
        from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
            build_skill_evolution_report,
        )

        report = build_skill_evolution_report(pattern_memory_with_candidates)

        # Only openclaw_candidate should be in candidates (meets min_executions, below threshold)
        assert report["candidate_count"] == 1
        assert len(report["candidates"]) == 1
        assert report["candidates"][0]["skill_name"] == "openclaw_candidate"

    def test_candidate_has_required_fields(self, pattern_memory_with_candidates):
        """Each candidate entry has all required fields."""
        from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
            build_skill_evolution_report,
        )

        report = build_skill_evolution_report(pattern_memory_with_candidates)
        candidate = report["candidates"][0]

        assert "skill_name" in candidate
        assert "execution_count" in candidate
        assert "avg_fidelity" in candidate
        assert "success_rate" in candidate
        assert "avg_time_ms" in candidate
        assert "latest_evolution_event" in candidate
        assert "status" in candidate
        assert "recommendation" in candidate

    def test_latest_evolution_event_included_when_present(self, tmp_path):
        """latest_evolution_event is populated from evolution history."""
        from modules.infrastructure.wre_core.src.pattern_memory import (
            PatternMemory,
            SkillOutcome,
        )
        from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
            build_skill_evolution_report,
        )

        db_path = tmp_path / "test_evolution_event.db"
        memory = PatternMemory(db_path=db_path)

        # Add candidate skill
        for i in range(5):
            memory.store_outcome(
                SkillOutcome(
                    execution_id=f"exec_evolved_{i}",
                    skill_name="openclaw_evolved",
                    agent="openclaw_dae",
                    timestamp="2026-03-29T10:00:00",
                    input_context="{}",
                    output_result="{}",
                    success=True,
                    pattern_fidelity=0.80,
                    outcome_quality=0.80,
                    execution_time_ms=100,
                    step_count=1,
                )
            )

        # Add evolution event
        memory.record_learning_event(
            event_id="ev_001",
            skill_name="openclaw_evolved",
            event_type="variation_created",
            description="Test evolution",
            continuity_id="cont_123",
            execution_id="exec_456",
        )

        report = build_skill_evolution_report(memory)
        candidate = report["candidates"][0]

        assert candidate["latest_evolution_event"] is not None
        assert candidate["latest_evolution_event"]["event_type"] == "variation_created"
        assert candidate["latest_evolution_event"]["continuity_id"] == "cont_123"


# ---------------------------------------------------------------------------
# 2. Supervisor Integration Tests
# ---------------------------------------------------------------------------


class TestSupervisorSkillEvolutionGate:
    """Supervisor env gate controls skill evolution report generation."""

    @pytest.fixture
    def mock_broker_observer(self):
        """Create healthy broker/observer mocks."""
        broker = MagicMock()
        broker.get_runtime_status.return_value = {
            "registered": True,
            "running": True,
            "state": "running",
            "last_error": "",
            "enabled": True,
        }
        observer = MagicMock()
        observer.get_live_status.return_value = {"registered": True, "recent_events": []}
        observer.follow_events.return_value = {
            "events": [],
            "next_cursor": 0,
            "latest_sequence_id": 0,
        }
        return broker, observer

    def test_env_gate_off_no_report(self, tmp_path, monkeypatch, mock_broker_observer):
        """When OPENCLAW_SKILL_EVOLUTION_ENABLED=0, no report generated."""
        from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
            OpenClawSupervisor,
        )

        monkeypatch.setenv("OPENCLAW_SKILL_EVOLUTION_ENABLED", "0")
        broker, observer = mock_broker_observer

        events = []
        supervisor = OpenClawSupervisor(
            repo_root=tmp_path,
            broker=broker,
            observer=observer,
            action_reporter=lambda action, result, details: events.append((action, result, details)),
            self_audit_factory=lambda repo_root: MagicMock(),
        )

        with patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
            mock_db.return_value.get_autonomous_tasks.return_value = []
            result = supervisor.run_cycle()

        assert result["triage"]["kind"] == "idle"
        assert "skill_evolution_report" not in result["triage"]

    def test_env_gate_on_report_due_generates_report(self, tmp_path, monkeypatch, mock_broker_observer):
        """When gate on and report due, generates report in idle result."""
        from datetime import datetime
        from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
            OpenClawSupervisor,
        )
        from modules.infrastructure.wre_core.src.pattern_memory import (
            PatternMemory,
            SkillOutcome,
        )

        monkeypatch.setenv("OPENCLAW_SKILL_EVOLUTION_ENABLED", "1")
        broker, observer = mock_broker_observer

        # Create PatternMemory with a candidate skill
        db_path = tmp_path / "wre_core" / "memory" / "pattern_memory.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        memory = PatternMemory(db_path=db_path)

        # Use current timestamp to ensure it's within the query window
        current_ts = datetime.now().isoformat()
        for i in range(5):
            memory.store_outcome(
                SkillOutcome(
                    execution_id=f"exec_test_{i}",
                    skill_name="openclaw_test",
                    agent="openclaw_dae",
                    timestamp=current_ts,
                    input_context="{}",
                    output_result="{}",
                    success=True,
                    pattern_fidelity=0.75,
                    outcome_quality=0.75,
                    execution_time_ms=100,
                    step_count=1,
                )
            )

        events = []
        supervisor = OpenClawSupervisor(
            repo_root=tmp_path,
            broker=broker,
            observer=observer,
            action_reporter=lambda action, result, details: events.append((action, result, details)),
            self_audit_factory=lambda repo_root: MagicMock(),
        )

        # Run first cycle to bootstrap, then inject our pattern memory
        # (bootstrap initializes its own pattern memory)
        with patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
            mock_db.return_value.get_autonomous_tasks.return_value = []
            supervisor.run_cycle()  # Bootstrap cycle

        # Now inject our test pattern memory after bootstrap
        supervisor._pattern_memory = memory

        # Delete any report created during bootstrap so the next cycle sees it as due
        from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
            get_skill_evolution_report_path,
        )
        report_path = get_skill_evolution_report_path(tmp_path)
        if report_path.exists():
            report_path.unlink()

        with patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
            mock_db.return_value.get_autonomous_tasks.return_value = []
            result = supervisor.run_cycle()  # Test cycle

        assert result["triage"]["kind"] == "idle"
        assert "skill_evolution_report" in result["triage"]
        assert result["triage"]["skill_evolution_report"]["skills_evaluated"] >= 1

        # Verify report file was written
        report_path = (
            tmp_path / "modules" / "communication" / "moltbot_bridge"
            / "workspace" / "reports" / "openclaw_skill_evolution_report.json"
        )
        assert report_path.exists()

    def test_higher_priority_work_blocks_report(self, tmp_path, monkeypatch, mock_broker_observer):
        """When higher-priority work exists, skill evolution does not run."""
        from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
            OpenClawSupervisor,
            SupervisorState,
        )

        monkeypatch.setenv("OPENCLAW_SKILL_EVOLUTION_ENABLED", "1")
        monkeypatch.setenv("OPENCLAW_AUTO_TASKS_ENABLED", "1")
        broker, observer = mock_broker_observer

        events = []
        supervisor = OpenClawSupervisor(
            repo_root=tmp_path,
            broker=broker,
            observer=observer,
            action_reporter=lambda action, result, details: events.append((action, result, details)),
            self_audit_factory=lambda repo_root: MagicMock(),
        )

        with patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
            # Return a pending autonomous task (higher priority)
            mock_db.return_value.get_autonomous_tasks.return_value = [
                {"task_id": "task_001", "description": "test task", "required_skills": []}
            ]
            mock_db.return_value.assign_autonomous_task.return_value = None

            # Mock task execution
            with patch(
                "modules.communication.moltbot_bridge.scripts.run_task.execute_task"
            ) as mock_exec:
                mock_exec.return_value = {"ok": True, "executor": "test"}
                result = supervisor.run_cycle()

        # When action is taken, result has 'plan' not 'triage'
        # Verify it selected the autonomous task action (not idle)
        assert "plan" in result
        assert result["plan"]["action"] == "execute_autonomous_task"
        # Skill evolution report should NOT be in the cycle (not idle path)
        assert "skill_evolution_report" not in result.get("plan", {})


class TestReportDueFreshness:
    """skill_evolution_report_due() checks report freshness."""

    def test_report_due_when_missing(self, tmp_path):
        """Returns True when report file does not exist."""
        from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
            skill_evolution_report_due,
        )

        assert skill_evolution_report_due(tmp_path) is True

    def test_report_not_due_when_fresh(self, tmp_path):
        """Returns False when report is recent."""
        from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
            get_skill_evolution_report_path,
            skill_evolution_report_due,
        )

        report_path = get_skill_evolution_report_path(tmp_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text('{"generated_on": "2026-03-29T10:00:00Z"}')

        # With default max_age_sec=3600, fresh report should not be due
        assert skill_evolution_report_due(tmp_path, max_age_sec=3600) is False

    def test_report_due_when_stale(self, tmp_path):
        """Returns True when report is older than max_age_sec."""
        from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
            get_skill_evolution_report_path,
            skill_evolution_report_due,
        )

        report_path = get_skill_evolution_report_path(tmp_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text('{"generated_on": "2026-03-29T10:00:00Z"}')

        # Set mtime to past
        old_mtime = time.time() - 7200  # 2 hours ago
        os.utime(report_path, (old_mtime, old_mtime))

        assert skill_evolution_report_due(tmp_path, max_age_sec=3600) is True


# ---------------------------------------------------------------------------
# 3. Regression Tests — No WRE Mutation
# ---------------------------------------------------------------------------


class TestNoWREMutation:
    """Verify Phase 1 does not call WRE mutation APIs."""

    def test_build_report_does_not_call_evolve_skill(self, tmp_path):
        """build_skill_evolution_report does not call evolve_skill."""
        from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory
        from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
            build_skill_evolution_report,
        )

        db_path = tmp_path / "test_no_mutation.db"
        memory = PatternMemory(db_path=db_path)

        # Patch any potential mutation methods
        memory.evolve_skill = MagicMock()
        memory.schedule_ab_test = MagicMock()
        memory.promote_variation = MagicMock()

        build_skill_evolution_report(memory)

        # Verify no mutation methods called
        memory.evolve_skill.assert_not_called()
        memory.schedule_ab_test.assert_not_called()
        memory.promote_variation.assert_not_called()

    def test_supervisor_idle_path_does_not_call_mutation_apis(
        self, tmp_path, monkeypatch
    ):
        """Supervisor skill evolution path does not call WRE mutation APIs."""
        from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
            OpenClawSupervisor,
        )
        from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory

        monkeypatch.setenv("OPENCLAW_SKILL_EVOLUTION_ENABLED", "1")

        broker = MagicMock()
        broker.get_runtime_status.return_value = {
            "registered": True,
            "running": True,
            "state": "running",
            "last_error": "",
            "enabled": True,
        }
        observer = MagicMock()
        observer.get_live_status.return_value = {"registered": True}
        observer.follow_events.return_value = {"events": [], "next_cursor": 0, "latest_sequence_id": 0}

        db_path = tmp_path / "test_no_supervisor_mutation.db"
        memory = PatternMemory(db_path=db_path)

        # Patch mutation methods
        memory.evolve_skill = MagicMock()
        memory.schedule_ab_test = MagicMock()
        memory.promote_variation = MagicMock()

        supervisor = OpenClawSupervisor(
            repo_root=tmp_path,
            broker=broker,
            observer=observer,
            action_reporter=lambda *args: None,
            self_audit_factory=lambda repo_root: MagicMock(),
        )
        supervisor._pattern_memory = memory

        with patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
            mock_db.return_value.get_autonomous_tasks.return_value = []
            supervisor.run_cycle()

        # Verify no mutation methods called
        memory.evolve_skill.assert_not_called()
        memory.schedule_ab_test.assert_not_called()
        memory.promote_variation.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
