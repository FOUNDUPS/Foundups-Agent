#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Skill Evolution Continuity Tracking

WSP Compliance: WSP 5 (Test Coverage), WSP 48 (Recursive Self-Improvement), WSP 91 (Observability)

Verifies that skill evolution events include continuity metadata for lineage tracking.
"""

import pytest
from pathlib import Path
from datetime import datetime
import uuid
import hashlib
import json
from types import SimpleNamespace

from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory


def test_runner_feedback_and_candidates_retain_exact_parent_after_reopen(monkeypatch, tmp_path):
    """Real storage binds two revisions without trusting executor-supplied lineage."""
    from modules.infrastructure.wre_core.tests.test_wre_execution_truth import _minimal_orchestrator

    orchestrator = _minimal_orchestrator(monkeypatch, tmp_path)
    db_path = tmp_path / "lineage.db"
    memory = PatternMemory(db_path=db_path)
    orchestrator.sqlite_memory = memory
    source = ["# Skill\nfirst revision"]
    orchestrator.skills_loader = SimpleNamespace(load_skill=lambda *_: source[0])
    monkeypatch.setattr(orchestrator.libido_monitor, "validate_step_fidelity", lambda **_: 0.2)
    supplied = {"success": False, "output": "failed", "steps_completed": 0,
                "_skill_binding": {"execution_id": "forged", "loaded_skill_sha256": "forged"}}
    monkeypatch.setattr(orchestrator, "_try_executor_dispatch", lambda *_: supplied)
    monkeypatch.setattr(orchestrator, "_generate_variation_with_qwen", lambda *_: "# candidate")
    expected = {}
    try:
        for text in ("# Skill\nfirst revision", "# Skill\nsecond revision 日本語"):
            source[0] = text
            result = orchestrator._execute_skill_once("lineage_skill", "qwen", {"_skill_binding": "forged"})
            assert result["success"] is False and result["variation_created"] is True
            expected[result["execution_id"]] = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    finally:
        memory.close()
    reopened = PatternMemory(db_path=db_path)
    try:
        rows = reopened.conn.execute("SELECT * FROM skill_outcomes").fetchall()
        assert len(rows) == 2
        for row in rows:
            binding = json.loads(row["output_result"])["_skill_binding"]
            assert binding == {"schema_version": "wre_skill_execution_binding.v1",
                               "execution_id": row["execution_id"],
                               "loaded_skill_sha256": expected[row["execution_id"]],
                               "scanner_admission_fingerprint": "f" * 64}
            assert row["success"] == 0 and row["outcome_quality"] == 0.0
        variants = reopened.conn.execute("SELECT * FROM skill_variations").fetchall()
        assert {row["parent_version"] for row in variants} == set(expected.values())
        assert all(row["promoted"] == 0 and row["test_status"] == "testing" for row in variants)
        assert {event["execution_id"] for event in reopened.get_evolution_history("lineage_skill")} == set(expected)
    finally:
        reopened.close()
    assert supplied["_skill_binding"]["execution_id"] == "forged"  # no mutation of producer object


class TestLearningEventsContinuitySchema:
    """Test learning_events table has continuity columns."""

    @pytest.fixture
    def memory(self, tmp_path):
        """Create isolated PatternMemory instance."""
        db_path = tmp_path / "test_evolution_continuity.db"
        return PatternMemory(db_path=db_path)

    def test_schema_has_continuity_columns(self, memory):
        """Verify learning_events table has continuity columns."""
        cursor = memory.conn.cursor()
        cursor.execute("PRAGMA table_info(learning_events)")
        columns = {row["name"] for row in cursor.fetchall()}

        assert "continuity_id" in columns
        assert "parent_continuity_id" in columns
        assert "execution_id" in columns

    def test_record_learning_event_with_continuity(self, memory):
        """Record learning event with continuity metadata."""
        event_id = str(uuid.uuid4())
        continuity_id = "abc123def456"
        parent_continuity_id = "parent789xyz"
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"

        memory.record_learning_event(
            event_id=event_id,
            skill_name="test_skill",
            event_type="variation_created",
            description="Test evolution with continuity",
            before_fidelity=0.75,
            after_fidelity=None,
            variation_id="test_skill_v1",
            continuity_id=continuity_id,
            parent_continuity_id=parent_continuity_id,
            execution_id=execution_id,
        )

        # Query back
        history = memory.get_evolution_history("test_skill")
        assert len(history) == 1

        event = history[0]
        assert event["continuity_id"] == continuity_id
        assert event["parent_continuity_id"] == parent_continuity_id
        assert event["execution_id"] == execution_id

    def test_record_learning_event_without_continuity(self, memory):
        """Record learning event without continuity (orphan/local WRE work)."""
        event_id = str(uuid.uuid4())

        memory.record_learning_event(
            event_id=event_id,
            skill_name="orphan_skill",
            event_type="variation_created",
            description="Orphan evolution (no continuity context)",
            before_fidelity=0.80,
        )

        history = memory.get_evolution_history("orphan_skill")
        assert len(history) == 1

        event = history[0]
        assert event["continuity_id"] is None
        assert event["parent_continuity_id"] is None
        assert event["execution_id"] is None


class TestEvolutionByLineage:
    """Test querying evolution events by continuity lineage."""

    @pytest.fixture
    def memory_with_events(self, tmp_path):
        """Create PatternMemory with test evolution events."""
        db_path = tmp_path / "test_lineage.db"
        memory = PatternMemory(db_path=db_path)

        # Create events in a lineage chain
        # Parent continuity: root123
        # Child continuity: child456 (parent=root123)
        # Orphan: orphan789 (no parent)

        memory.record_learning_event(
            event_id="event1",
            skill_name="skill_a",
            event_type="variation_created",
            description="Root evolution",
            continuity_id="root123",
            execution_id="exec_001",
        )

        memory.record_learning_event(
            event_id="event2",
            skill_name="skill_b",
            event_type="variation_created",
            description="Child evolution",
            continuity_id="child456",
            parent_continuity_id="root123",
            execution_id="exec_002",
        )

        memory.record_learning_event(
            event_id="event3",
            skill_name="skill_c",
            event_type="variation_promoted",
            description="Orphan evolution",
            continuity_id="orphan789",
            execution_id="exec_003",
        )

        return memory

    def test_get_evolution_by_continuity(self, memory_with_events):
        """Query evolution events by continuity_id."""
        events = memory_with_events.get_evolution_by_continuity("root123")

        assert len(events) == 1
        assert events[0]["event_id"] == "event1"
        assert events[0]["skill_name"] == "skill_a"

    def test_get_evolution_by_continuity_include_children(self, memory_with_events):
        """Query evolution events including children in lineage."""
        events = memory_with_events.get_evolution_by_continuity(
            "root123", include_children=True
        )

        assert len(events) == 2
        event_ids = {e["event_id"] for e in events}
        assert "event1" in event_ids  # Direct match
        assert "event2" in event_ids  # Child with parent=root123

    def test_get_evolution_by_execution(self, memory_with_events):
        """Query evolution events by execution_id."""
        events = memory_with_events.get_evolution_by_execution("exec_002")

        assert len(events) == 1
        assert events[0]["event_id"] == "event2"
        assert events[0]["skill_name"] == "skill_b"

    def test_get_evolution_nonexistent_continuity(self, memory_with_events):
        """Query with nonexistent continuity returns empty list."""
        events = memory_with_events.get_evolution_by_continuity("nonexistent")
        assert events == []

    def test_get_evolution_nonexistent_execution(self, memory_with_events):
        """Query with nonexistent execution returns empty list."""
        events = memory_with_events.get_evolution_by_execution("nonexistent")
        assert events == []


class TestEvolutionContinuityIntegration:
    """Integration tests for evolution continuity in WRE pipeline."""

    @pytest.fixture
    def memory(self, tmp_path):
        """Create isolated PatternMemory instance."""
        db_path = tmp_path / "test_integration.db"
        return PatternMemory(db_path=db_path)

    def test_full_lineage_chain_queryable(self, memory):
        """Verify full lineage chain is queryable after multiple evolutions."""
        # Simulate: Execution -> Evolution -> Variation -> Promotion

        # Step 1: First evolution (triggered by low fidelity)
        memory.record_learning_event(
            event_id="ev_001",
            skill_name="gitpush_skill",
            event_type="variation_created",
            description="Low fidelity triggered variation",
            before_fidelity=0.75,
            continuity_id="session_abc",
            parent_continuity_id="parent_xyz",
            execution_id="exec_100",
        )

        # Step 2: A/B test promotion (same continuity chain)
        memory.record_learning_event(
            event_id="ev_002",
            skill_name="gitpush_skill",
            event_type="variation_promoted",
            description="A/B test winner promoted",
            after_fidelity=0.95,
            continuity_id="session_abc",
            execution_id="exec_105",
        )

        # Query the full chain
        history = memory.get_evolution_history("gitpush_skill")
        assert len(history) == 2

        # Both events should be in the same continuity
        chain_events = memory.get_evolution_by_continuity("session_abc")
        assert len(chain_events) == 2

        # Can trace back to parent continuity
        assert history[0]["parent_continuity_id"] == "parent_xyz"

        # Can trace which execution triggered which evolution
        exec_100_events = memory.get_evolution_by_execution("exec_100")
        assert len(exec_100_events) == 1
        assert exec_100_events[0]["event_type"] == "variation_created"

        exec_105_events = memory.get_evolution_by_execution("exec_105")
        assert len(exec_105_events) == 1
        assert exec_105_events[0]["event_type"] == "variation_promoted"


class TestCandidateReadyContinuity:
    """A/B nomination remains non-production while retaining lineage."""

    @pytest.fixture
    def memory_with_ab_test(self, tmp_path):
        """Create PatternMemory with an active A/B test ready for nomination."""
        db_path = tmp_path / "test_promotion.db"
        memory = PatternMemory(db_path=db_path)
        memory.store_variation(
            variation_id="test_skill_v1",
            skill_name="test_promotion_skill",
            variation_content="# Candidate",
            parent_version="current",
        )

        # Schedule an A/B test
        test_id = memory.schedule_ab_test(
            skill_name="test_promotion_skill",
            control_version="current",
            treatment_version="test_skill_v1",
            sample_size_target=2  # Low threshold for quick promotion
        )

        # Record enough successes for treatment to win
        memory.record_ab_outcome(test_id, "control", success=False)
        memory.record_ab_outcome(test_id, "control", success=False)
        memory.record_ab_outcome(test_id, "treatment", success=True)
        memory.record_ab_outcome(test_id, "treatment", success=True)

        return memory, test_id

    def test_candidate_nomination_includes_continuity(self, memory_with_ab_test):
        """
        Statistical treatment win creates candidate lineage, not promotion.
        """
        memory, test_id = memory_with_ab_test

        # The statistical result is nomination evidence only.
        winner = memory.check_ab_promotion(test_id)
        assert winner == "treatment"

        execution_id = "exec_promo_001"
        continuity_id = "continuity_promo_abc"
        parent_continuity_id = "parent_promo_xyz"

        memory.stage_variation_candidate("test_skill_v1")
        memory.close_ab_test(test_id, "treatment_candidate")
        memory.record_learning_event(
            event_id="ev_promo_001",
            skill_name="test_promotion_skill",
            event_type="variation_candidate_ready",
            description="Nominated test_skill_v1 for independent verification",
            variation_id="test_skill_v1",
            continuity_id=continuity_id,
            parent_continuity_id=parent_continuity_id,
            execution_id=execution_id,
        )

        # Verify candidate event has continuity metadata.
        history = memory.get_evolution_history("test_promotion_skill")
        assert len(history) == 1

        candidate_event = history[0]
        assert candidate_event["event_type"] == "variation_candidate_ready"
        assert candidate_event["continuity_id"] == continuity_id
        assert candidate_event["parent_continuity_id"] == parent_continuity_id
        assert candidate_event["execution_id"] == execution_id

        # Queryable via lineage APIs
        by_continuity = memory.get_evolution_by_continuity(continuity_id)
        assert len(by_continuity) == 1
        assert by_continuity[0]["event_type"] == "variation_candidate_ready"

        by_execution = memory.get_evolution_by_execution(execution_id)
        assert len(by_execution) == 1
        assert by_execution[0]["variation_id"] == "test_skill_v1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
