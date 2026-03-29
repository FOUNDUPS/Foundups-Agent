#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for PQN Swarm Hub SQLite persistence layer.

Phase 1 persistence tests:
1. SQLiteStore initialization
2. Work unit CRUD
3. Submission CRUD
4. Verification decision CRUD
5. Contribution CRUD
6. Participant and gate decision CRUD
7. Service integration with store injection
"""

import gc
import pytest
import tempfile
from pathlib import Path

from modules.foundups.pqn_swarm_hub import (
    PQNWorkUnit,
    rESPSubmission,
    VerificationDecision,
    ContributionRecord,
    WorkUnitStatus,
    SubmissionStatus,
    SQLiteStore,
    get_sqlite_store,
    reset_sqlite_store,
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ContributionReporter,
    ParticipantGate,
    ParticipantIdentity,
    ParticipantTier,
)


@pytest.fixture
def temp_db_dir(tmp_path):
    """Provide a temporary directory for test databases."""
    return tmp_path / "test_swarm_db"


@pytest.fixture
def store(temp_db_dir):
    """Provide a fresh SQLiteStore for each test."""
    reset_sqlite_store()
    s = SQLiteStore(db_dir=temp_db_dir, db_filename="test.db")
    yield s
    # Cleanup - close connections before removing temp dir
    del s
    gc.collect()


class TestSQLiteStoreInit:
    """Tests for SQLiteStore initialization."""

    def test_creates_db_file(self, temp_db_dir):
        """Store creates database file on init."""
        store = SQLiteStore(db_dir=temp_db_dir, db_filename="init_test.db")
        assert store.db_path.exists()
        assert store.db_path.name == "init_test.db"

    def test_creates_directory(self, tmp_path):
        """Store creates directory if it doesn't exist."""
        nested = tmp_path / "nested" / "path"
        store = SQLiteStore(db_dir=nested, db_filename="test.db")
        assert nested.exists()
        assert store.db_path.exists()

    def test_get_stats_empty(self, store):
        """Fresh store returns zero counts."""
        stats = store.get_stats()
        assert stats["work_units"] == 0
        assert stats["submissions"] == 0
        assert stats["verification_decisions"] == 0
        assert stats["contributions"] == 0
        assert stats["participants"] == 0
        assert stats["gate_decisions"] == 0


class TestWorkUnitPersistence:
    """Tests for work unit CRUD operations."""

    def test_save_and_get(self, store):
        """Work unit can be saved and retrieved."""
        wu = PQNWorkUnit(
            description="Persistence test",
            config={"steps": 100},
            creator_id="test_agent",
        )
        store.save_work_unit(wu)

        retrieved = store.get_work_unit(wu.work_unit_id)
        assert retrieved is not None
        assert retrieved.work_unit_id == wu.work_unit_id
        assert retrieved.description == "Persistence test"
        assert retrieved.config == {"steps": 100}
        assert retrieved.creator_id == "test_agent"
        assert retrieved.status == WorkUnitStatus.PENDING

    def test_get_nonexistent(self, store):
        """Getting nonexistent work unit returns None."""
        assert store.get_work_unit("nonexistent_id") is None

    def test_list_empty(self, store):
        """List on empty store returns empty list."""
        assert store.list_work_units() == []

    def test_list_with_status_filter(self, store):
        """List can filter by status."""
        wu1 = PQNWorkUnit(description="A", config={}, creator_id="x")
        wu2 = PQNWorkUnit(description="B", config={}, creator_id="x")
        wu2.status = WorkUnitStatus.IN_PROGRESS

        store.save_work_unit(wu1)
        store.save_work_unit(wu2)

        pending = store.list_work_units(status_filter=WorkUnitStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].description == "A"

        in_progress = store.list_work_units(status_filter=WorkUnitStatus.IN_PROGRESS)
        assert len(in_progress) == 1
        assert in_progress[0].description == "B"

    def test_update_existing(self, store):
        """Saving existing work unit updates it."""
        wu = PQNWorkUnit(description="Original", config={}, creator_id="x")
        store.save_work_unit(wu)

        wu.description = "Updated"
        wu.status = WorkUnitStatus.COMPLETED
        store.save_work_unit(wu)

        retrieved = store.get_work_unit(wu.work_unit_id)
        assert retrieved.description == "Updated"
        assert retrieved.status == WorkUnitStatus.COMPLETED


class TestSubmissionPersistence:
    """Tests for submission CRUD operations."""

    def test_save_and_get(self, store):
        """Submission can be saved and retrieved."""
        # Create parent work unit first (FK constraint)
        wu = PQNWorkUnit(description="Parent", config={}, creator_id="x")
        store.save_work_unit(wu)

        sub = rESPSubmission(
            work_unit_id=wu.work_unit_id,
            submitter_id="agent_y",
            metrics={"coherence": 0.75},
            artifacts=["path/to/file.jsonl"],
        )
        store.save_submission(sub)

        retrieved = store.get_submission(sub.submission_id)
        assert retrieved is not None
        assert retrieved.work_unit_id == wu.work_unit_id
        assert retrieved.metrics["coherence"] == 0.75
        assert "path/to/file.jsonl" in retrieved.artifacts

    def test_list_by_work_unit(self, store):
        """List can filter by work unit ID."""
        # Create parent work units first
        wu_a = PQNWorkUnit(description="A", config={}, creator_id="x")
        wu_b = PQNWorkUnit(description="B", config={}, creator_id="x")
        store.save_work_unit(wu_a)
        store.save_work_unit(wu_b)

        sub1 = rESPSubmission(work_unit_id=wu_a.work_unit_id, submitter_id="x", metrics={})
        sub2 = rESPSubmission(work_unit_id=wu_b.work_unit_id, submitter_id="x", metrics={})
        store.save_submission(sub1)
        store.save_submission(sub2)

        results = store.list_submissions(work_unit_id=wu_a.work_unit_id)
        assert len(results) == 1
        assert results[0].work_unit_id == wu_a.work_unit_id


class TestDecisionPersistence:
    """Tests for verification decision CRUD operations."""

    def test_save_and_get(self, store):
        """Decision can be saved and retrieved."""
        # Create parent chain: work_unit -> submission -> decision
        wu = PQNWorkUnit(description="Parent", config={}, creator_id="x")
        store.save_work_unit(wu)
        sub = rESPSubmission(work_unit_id=wu.work_unit_id, submitter_id="x", metrics={})
        store.save_submission(sub)

        dec = VerificationDecision(
            submission_id=sub.submission_id,
            decision="accept",
            verifier_id="auto",
            rationale="Meets threshold",
        )
        dec.confidence = 0.85
        store.save_decision(dec)

        retrieved = store.get_decision(dec.decision_id)
        assert retrieved is not None
        assert retrieved.decision == "accept"
        assert retrieved.confidence == 0.85

    def test_list_by_submission(self, store):
        """List can filter by submission ID."""
        # Create parent chains
        wu = PQNWorkUnit(description="Parent", config={}, creator_id="x")
        store.save_work_unit(wu)
        sub_a = rESPSubmission(work_unit_id=wu.work_unit_id, submitter_id="x", metrics={})
        sub_b = rESPSubmission(work_unit_id=wu.work_unit_id, submitter_id="y", metrics={})
        store.save_submission(sub_a)
        store.save_submission(sub_b)

        dec1 = VerificationDecision(
            submission_id=sub_a.submission_id, decision="accept", verifier_id="x", rationale=""
        )
        dec2 = VerificationDecision(
            submission_id=sub_b.submission_id, decision="reject", verifier_id="x", rationale=""
        )
        store.save_decision(dec1)
        store.save_decision(dec2)

        results = store.list_decisions(submission_id=sub_a.submission_id)
        assert len(results) == 1
        assert results[0].decision == "accept"


class TestContributionPersistence:
    """Tests for contribution CRUD operations."""

    def test_save_and_get(self, store):
        """Contribution can be saved and retrieved."""
        # Create full parent chain: work_unit -> submission -> decision -> contribution
        wu = PQNWorkUnit(description="Parent", config={}, creator_id="x")
        store.save_work_unit(wu)
        sub = rESPSubmission(work_unit_id=wu.work_unit_id, submitter_id="x", metrics={})
        store.save_submission(sub)
        dec = VerificationDecision(submission_id=sub.submission_id, decision="accept", verifier_id="x", rationale="")
        store.save_decision(dec)

        cr = ContributionRecord(
            work_unit_id=wu.work_unit_id,
            submission_id=sub.submission_id,
            decision_id=dec.decision_id,
            contributor_id="agent_z",
            score=0.95,
        )
        store.save_contribution(cr)

        retrieved = store.get_contribution(cr.contribution_id)
        assert retrieved is not None
        assert retrieved.score == 0.95
        assert retrieved.contributor_id == "agent_z"

    def test_list_by_contributor(self, store):
        """List can filter by contributor ID."""
        # Create full parent chains for two contributors
        wu1 = PQNWorkUnit(description="Work1", config={}, creator_id="x")
        wu2 = PQNWorkUnit(description="Work2", config={}, creator_id="x")
        store.save_work_unit(wu1)
        store.save_work_unit(wu2)

        sub1 = rESPSubmission(work_unit_id=wu1.work_unit_id, submitter_id="alice", metrics={})
        sub2 = rESPSubmission(work_unit_id=wu2.work_unit_id, submitter_id="bob", metrics={})
        store.save_submission(sub1)
        store.save_submission(sub2)

        dec1 = VerificationDecision(submission_id=sub1.submission_id, decision="accept", verifier_id="x", rationale="")
        dec2 = VerificationDecision(submission_id=sub2.submission_id, decision="accept", verifier_id="x", rationale="")
        store.save_decision(dec1)
        store.save_decision(dec2)

        cr1 = ContributionRecord(
            work_unit_id=wu1.work_unit_id, submission_id=sub1.submission_id, decision_id=dec1.decision_id,
            contributor_id="alice", score=0.8
        )
        cr2 = ContributionRecord(
            work_unit_id=wu2.work_unit_id, submission_id=sub2.submission_id, decision_id=dec2.decision_id,
            contributor_id="bob", score=0.9
        )
        store.save_contribution(cr1)
        store.save_contribution(cr2)

        results = store.list_contributions(contributor_id="alice")
        assert len(results) == 1
        assert results[0].contributor_id == "alice"


class TestParticipantPersistence:
    """Tests for participant CRUD operations."""

    def test_save_and_get(self, store):
        """Participant can be saved and retrieved."""
        p = ParticipantIdentity(
            display_name="TestBot",
            model_type="qwen-1.5b",
            compute_capacity="low",
            capability_tags=["physics", "rESP"],
        )
        store.save_participant(p)

        retrieved = store.get_participant(p.participant_id)
        assert retrieved is not None
        assert retrieved.display_name == "TestBot"
        assert retrieved.model_type == "qwen-1.5b"
        assert "physics" in retrieved.capability_tags


class TestServiceIntegration:
    """Tests for services with store injection."""

    def test_registry_persists_work_units(self, store):
        """WorkUnitRegistry persists to store when injected."""
        registry = WorkUnitRegistry(store=store)

        wu = registry.register(
            description="Persistent work unit",
            config={"test": True},
            creator_id="integration_test",
        )

        # Clear memory and verify retrieval from store
        registry2 = WorkUnitRegistry(store=store)
        retrieved = registry2.get(wu.work_unit_id)
        assert retrieved.description == "Persistent work unit"

    def test_full_flow_with_persistence(self, store, temp_db_dir):
        """Full flow persists across service instances."""
        # Setup services with store
        registry = WorkUnitRegistry(store=store)
        sink = SubmissionSink(registry, store=store)
        engine = VerificationEngine(sink, store=store)
        reporter = ContributionReporter(
            engine,
            artifact_dir=temp_db_dir / "artifacts",
            store=store,
        )

        # Execute flow
        wu = registry.register("Flow test", {"x": 1}, "flow_agent")
        sub = sink.submit(wu.work_unit_id, "flow_agent", {"coherence": 0.8})
        dec = engine.manual_verify(sub.submission_id, "accept", "verifier", "Good")
        cr = reporter.record(wu.work_unit_id, sub.submission_id, dec.decision_id, "flow_agent", 0.9)

        # Verify stats
        stats = store.get_stats()
        assert stats["work_units"] == 1
        assert stats["submissions"] == 1
        assert stats["verification_decisions"] == 1
        assert stats["contributions"] == 1

        # Verify persistence - create new service instances
        registry2 = WorkUnitRegistry(store=store)
        sink2 = SubmissionSink(registry2, store=store)
        engine2 = VerificationEngine(sink2, store=store)
        reporter2 = ContributionReporter(engine2, store=store)

        assert registry2.get(wu.work_unit_id) is not None
        assert sink2.get(sub.submission_id) is not None
        assert engine2.get(dec.decision_id) is not None
        assert reporter2.get(cr.contribution_id) is not None

    def test_gate_persists_participants(self, store):
        """ParticipantGate persists participants and decisions."""
        gate = ParticipantGate(store=store)

        identity = ParticipantIdentity(
            display_name="PersistentAgent",
            model_type="claude-opus-4-5",
        )
        decision = gate.request_entry(identity)

        # Verify in store
        retrieved_p = store.get_participant(identity.participant_id)
        assert retrieved_p is not None
        assert retrieved_p.display_name == "PersistentAgent"

        retrieved_d = store.get_gate_decision(decision.decision_id)
        assert retrieved_d is not None
        assert retrieved_d.decision == "approve"
