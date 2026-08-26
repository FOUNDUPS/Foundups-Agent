#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Pattern Memory (SQLite outcome storage for recursive learning)

WSP Compliance: WSP 5 (Test Coverage), WSP 96 (WRE Skills), WSP 48 (Recursive Self-Improvement), WSP 60 (Module Memory)
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from modules.infrastructure.wre_core.src.pattern_memory import (
    PatternMemory,
    SkillOutcome
)


class TestPatternMemory:
    """Test suite for Pattern Memory (recursive learning storage)"""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database for testing"""
        db_path = tmp_path / "test_pattern_memory.db"
        return db_path

    @pytest.fixture
    def memory(self, temp_db):
        """Create PatternMemory instance with temp database"""
        return PatternMemory(db_path=temp_db)

    def test_initialization(self, memory, temp_db):
        """Test database initialization and schema creation"""
        assert temp_db.exists()
        assert memory.db_path == temp_db
        assert memory.conn is not None

        # Verify tables created
        cursor = memory.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "skill_outcomes" in tables
        assert "skill_variations" in tables
        assert "learning_events" in tables

    def test_store_outcome(self, memory):
        """Test storing skill execution outcome"""
        outcome = SkillOutcome(
            execution_id="exec_001",
            skill_name="qwen_gitpush",
            agent="qwen",
            timestamp=datetime.now().isoformat(),
            input_context=json.dumps({"files_changed": 14}),
            output_result=json.dumps({"action": "push_now"}),
            success=True,
            pattern_fidelity=0.92,
            outcome_quality=0.95,
            execution_time_ms=1200,
            step_count=4,
            notes="Test execution"
        )

        memory.store_outcome(outcome)

        # Verify stored
        cursor = memory.conn.cursor()
        cursor.execute("SELECT * FROM skill_outcomes WHERE execution_id = ?", ("exec_001",))
        row = cursor.fetchone()

        assert row is not None
        assert row["skill_name"] == "qwen_gitpush"
        assert row["pattern_fidelity"] == 0.92

    def test_recall_successful_patterns(self, memory):
        """Test recalling successful execution patterns"""
        # Store 3 successful and 2 failed outcomes
        for i in range(5):
            fidelity = 0.95 if i < 3 else 0.70  # First 3 are successful
            outcome = SkillOutcome(
                execution_id=f"exec_{i:03d}",
                skill_name="qwen_gitpush",
                agent="qwen",
                timestamp=datetime.now().isoformat(),
                input_context=json.dumps({}),
                output_result=json.dumps({}),
                success=(i < 3),
                pattern_fidelity=fidelity,
                outcome_quality=0.90,
                execution_time_ms=1000,
                step_count=4
            )
            memory.store_outcome(outcome)

        # Recall successful patterns (≥0.90 fidelity)
        patterns = memory.recall_successful_patterns("qwen_gitpush", min_fidelity=0.90)

        assert len(patterns) == 3
        assert all(p["pattern_fidelity"] >= 0.90 for p in patterns)
        assert all(p["success"] == 1 for p in patterns)

    def test_recall_failure_patterns(self, memory):
        """Test recalling failed execution patterns"""
        # Store 2 successful and 3 failed outcomes
        for i in range(5):
            fidelity = 0.65 if i >= 2 else 0.92  # Last 3 are failures
            outcome = SkillOutcome(
                execution_id=f"exec_{i:03d}",
                skill_name="qwen_gitpush",
                agent="qwen",
                timestamp=datetime.now().isoformat(),
                input_context=json.dumps({}),
                output_result=json.dumps({}),
                success=(i < 2),
                pattern_fidelity=fidelity,
                outcome_quality=0.70,
                execution_time_ms=1000,
                step_count=4
            )
            memory.store_outcome(outcome)

        # Recall failure patterns (≤0.70 fidelity)
        patterns = memory.recall_failure_patterns("qwen_gitpush", max_fidelity=0.70)

        assert len(patterns) == 3
        assert all(p["pattern_fidelity"] <= 0.70 for p in patterns)

    def test_get_skill_metrics_no_data(self, memory):
        """Test metrics for skill with no executions"""
        metrics = memory.get_skill_metrics("nonexistent_skill", days=7)

        assert metrics["skill_name"] == "nonexistent_skill"
        assert metrics["execution_count"] == 0
        assert metrics["avg_fidelity"] == 0.0

    def test_get_skill_metrics_with_data(self, memory):
        """Test metrics calculation with execution data"""
        # Store 3 executions
        for i in range(3):
            outcome = SkillOutcome(
                execution_id=f"exec_{i:03d}",
                skill_name="qwen_gitpush",
                agent="qwen",
                timestamp=datetime.now().isoformat(),
                input_context=json.dumps({}),
                output_result=json.dumps({}),
                success=True,
                pattern_fidelity=0.90 + (i * 0.02),  # 0.90, 0.92, 0.94
                outcome_quality=0.95,
                execution_time_ms=1000 + (i * 100),
                step_count=4
            )
            memory.store_outcome(outcome)

        metrics = memory.get_skill_metrics("qwen_gitpush", days=7)

        assert metrics["execution_count"] == 3
        assert metrics["avg_fidelity"] == pytest.approx(0.92, abs=0.01)
        assert metrics["avg_quality"] == 0.95
        assert metrics["success_rate"] == 1.0
        assert metrics["avg_time_ms"] == pytest.approx(1100, abs=10)

    def test_store_variation(self, memory):
        """Test storing skill variation for A/B testing"""
        memory.store_variation(
            variation_id="qwen_gitpush_v1.1",
            skill_name="qwen_gitpush",
            variation_content="# Improved version...",
            parent_version="v1.0",
            created_by="qwen"
        )

        cursor = memory.conn.cursor()
        cursor.execute("SELECT * FROM skill_variations WHERE variation_id = ?", ("qwen_gitpush_v1.1",))
        row = cursor.fetchone()

        assert row is not None
        assert row["skill_name"] == "qwen_gitpush"
        assert row["parent_version"] == "v1.0"
        assert row["created_by"] == "qwen"
        assert row["test_status"] == "testing"

    def test_stage_variation_candidate_does_not_promote(self, memory):
        """An A/B winner remains non-production pending independent admission."""
        variation_id = "qwen_gitpush_candidate"
        memory.store_variation(
            variation_id=variation_id,
            skill_name="qwen_gitpush",
            variation_content="# Candidate version",
        )

        memory.stage_variation_candidate(variation_id)

        row = memory.conn.execute(
            "SELECT promoted, test_status FROM skill_variations "
            "WHERE variation_id = ?",
            (variation_id,),
        ).fetchone()
        assert row["promoted"] == 0
        assert row["test_status"] == "candidate_ready"

    def test_legacy_promote_variation_fails_closed(self, memory):
        """PatternMemory cannot self-authorize production state."""
        with pytest.raises(PermissionError, match="signed promoter"):
            memory.promote_variation("candidate_v1")

    @pytest.mark.parametrize("variant", ["", "candidate", "CONTROL"])
    def test_record_ab_outcome_rejects_unknown_variant(self, memory, variant):
        """Unknown variant labels cannot be counted as treatment."""
        test_id = memory.schedule_ab_test("skill", "v1", "v2", sample_size_target=1)

        with pytest.raises(ValueError, match="variant"):
            memory.record_ab_outcome(test_id, variant, success=True)

    def test_record_ab_outcome_requires_exact_boolean(self, memory):
        """Truthy strings cannot create A/B success evidence."""
        test_id = memory.schedule_ab_test("skill", "v1", "v2", sample_size_target=1)

        with pytest.raises(TypeError, match="boolean"):
            memory.record_ab_outcome(test_id, "treatment", success="false")

    def test_ab_nomination_requires_target_for_both_variants(self, memory):
        """One populated arm cannot nominate its own treatment."""
        test_id = memory.schedule_ab_test("skill", "v1", "v2", sample_size_target=2)
        memory.record_ab_outcome(test_id, "treatment", success=True)
        memory.record_ab_outcome(test_id, "treatment", success=True)
        assert memory.check_ab_promotion(test_id) is None

        memory.record_ab_outcome(test_id, "control", success=False)
        memory.record_ab_outcome(test_id, "control", success=False)
        assert memory.check_ab_promotion(test_id) == "treatment"

    def test_record_ab_outcome_rejects_inactive_test(self, memory):
        """Closed or missing tests cannot accept late samples."""
        test_id = memory.schedule_ab_test("skill", "v1", "v2", sample_size_target=1)
        memory.close_ab_test(test_id, "inconclusive")

        row = memory.conn.execute(
            "SELECT status, winner FROM ab_test_assignments WHERE test_id = ?",
            (test_id,),
        ).fetchone()
        assert row["status"] == "completed"
        assert row["winner"] == "inconclusive"

        with pytest.raises(ValueError, match="inactive"):
            memory.record_ab_outcome(test_id, "control", success=True)

    def test_record_learning_event(self, memory):
        """Test recording learning event for skill evolution"""
        memory.record_learning_event(
            event_id="learn_001",
            skill_name="qwen_gitpush",
            event_type="variation_promoted",
            description="Promoted v1.1 after fidelity improvement",
            before_fidelity=0.65,
            after_fidelity=0.92,
            variation_id="qwen_gitpush_v1.1"
        )

        cursor = memory.conn.cursor()
        cursor.execute("SELECT * FROM learning_events WHERE event_id = ?", ("learn_001",))
        row = cursor.fetchone()

        assert row is not None
        assert row["event_type"] == "variation_promoted"
        assert row["before_fidelity"] == 0.65
        assert row["after_fidelity"] == 0.92

    def test_get_evolution_history(self, memory):
        """Test retrieving evolution history"""
        # Record 3 learning events
        for i in range(3):
            memory.record_learning_event(
                event_id=f"learn_{i:03d}",
                skill_name="qwen_gitpush",
                event_type="variation_created",
                description=f"Created variation {i}",
                before_fidelity=0.60 + (i * 0.05),
                after_fidelity=0.70 + (i * 0.05)
            )

        history = memory.get_evolution_history("qwen_gitpush")

        assert len(history) == 3
        assert history[0]["event_id"] == "learn_000"  # Chronological order
        assert history[2]["event_id"] == "learn_002"

    def test_recall_patterns_respects_limit(self, memory):
        """Test limit parameter on pattern recall"""
        # Store 10 successful outcomes
        for i in range(10):
            outcome = SkillOutcome(
                execution_id=f"exec_{i:03d}",
                skill_name="qwen_gitpush",
                agent="qwen",
                timestamp=datetime.now().isoformat(),
                input_context=json.dumps({}),
                output_result=json.dumps({}),
                success=True,
                pattern_fidelity=0.95,
                outcome_quality=0.90,
                execution_time_ms=1000,
                step_count=4
            )
            memory.store_outcome(outcome)

        # Request only 5
        patterns = memory.recall_successful_patterns("qwen_gitpush", min_fidelity=0.90, limit=5)

        assert len(patterns) == 5

    def test_patterns_sorted_by_fidelity_desc(self, memory):
        """Test successful patterns returned in fidelity order (highest first)"""
        # Store outcomes with varying fidelity
        fidelities = [0.88, 0.95, 0.91, 0.97, 0.89]
        for i, fidelity in enumerate(fidelities):
            outcome = SkillOutcome(
                execution_id=f"exec_{i:03d}",
                skill_name="qwen_gitpush",
                agent="qwen",
                timestamp=datetime.now().isoformat(),
                input_context=json.dumps({}),
                output_result=json.dumps({}),
                success=True,
                pattern_fidelity=fidelity,
                outcome_quality=0.90,
                execution_time_ms=1000,
                step_count=4
            )
            memory.store_outcome(outcome)

        patterns = memory.recall_successful_patterns("qwen_gitpush", min_fidelity=0.85)

        # Should be sorted by fidelity descending
        assert patterns[0]["pattern_fidelity"] == 0.97
        assert patterns[1]["pattern_fidelity"] == 0.95
        assert patterns[-1]["pattern_fidelity"] == 0.88

    def test_failed_step_tracking(self, memory):
        """Test tracking which step failed"""
        outcome = SkillOutcome(
            execution_id="exec_001",
            skill_name="qwen_gitpush",
            agent="qwen",
            timestamp=datetime.now().isoformat(),
            input_context=json.dumps({}),
            output_result=json.dumps({}),
            success=False,
            pattern_fidelity=0.60,
            outcome_quality=0.50,
            execution_time_ms=500,
            step_count=4,
            failed_at_step=2  # Failed at step 2
        )

        memory.store_outcome(outcome)

        cursor = memory.conn.cursor()
        cursor.execute("SELECT * FROM skill_outcomes WHERE execution_id = ?", ("exec_001",))
        row = cursor.fetchone()

        assert row["failed_at_step"] == 2
        assert row["success"] == 0

    def test_metrics_time_window(self, memory):
        """Test metrics respect time window parameter"""
        now = datetime.now()

        # Store 1 recent outcome (within 7 days)
        recent = SkillOutcome(
            execution_id="exec_recent",
            skill_name="qwen_gitpush",
            agent="qwen",
            timestamp=now.isoformat(),
            input_context=json.dumps({}),
            output_result=json.dumps({}),
            success=True,
            pattern_fidelity=0.95,
            outcome_quality=0.90,
            execution_time_ms=1000,
            step_count=4
        )
        memory.store_outcome(recent)

        # Store 1 old outcome (10 days ago)
        old = SkillOutcome(
            execution_id="exec_old",
            skill_name="qwen_gitpush",
            agent="qwen",
            timestamp=(now - timedelta(days=10)).isoformat(),
            input_context=json.dumps({}),
            output_result=json.dumps({}),
            success=True,
            pattern_fidelity=0.85,
            outcome_quality=0.80,
            execution_time_ms=1500,
            step_count=4
        )
        memory.store_outcome(old)

        # Query last 7 days - should only get recent
        metrics = memory.get_skill_metrics("qwen_gitpush", days=7)

        assert metrics["execution_count"] == 1  # Only recent one
        assert metrics["avg_fidelity"] == 0.95  # Recent fidelity, not old

    def test_close_connection(self, memory):
        """Test database connection closes cleanly"""
        memory.close()

        # Connection should be closed
        with pytest.raises(Exception):
            memory.conn.cursor()


class TestSkillOutcome:
    """Test SkillOutcome dataclass"""

    def test_skill_outcome_creation(self):
        """Test creating SkillOutcome record"""
        outcome = SkillOutcome(
            execution_id="exec_001",
            skill_name="qwen_gitpush",
            agent="qwen",
            timestamp="2025-10-23T12:00:00",
            input_context=json.dumps({"files": 14}),
            output_result=json.dumps({"action": "push"}),
            success=True,
            pattern_fidelity=0.92,
            outcome_quality=0.95,
            execution_time_ms=1200,
            step_count=4
        )

        assert outcome.execution_id == "exec_001"
        assert outcome.skill_name == "qwen_gitpush"
        assert outcome.success is True
        assert outcome.failed_at_step is None

    def test_skill_outcome_with_failure(self):
        """Test SkillOutcome with failure details"""
        outcome = SkillOutcome(
            execution_id="exec_002",
            skill_name="qwen_gitpush",
            agent="qwen",
            timestamp="2025-10-23T12:00:00",
            input_context=json.dumps({}),
            output_result=json.dumps({}),
            success=False,
            pattern_fidelity=0.60,
            outcome_quality=0.50,
            execution_time_ms=800,
            step_count=4,
            failed_at_step=2,
            notes="Step 2 validation failed"
        )

        assert outcome.success is False
        assert outcome.failed_at_step == 2
        assert outcome.notes == "Step 2 validation failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
