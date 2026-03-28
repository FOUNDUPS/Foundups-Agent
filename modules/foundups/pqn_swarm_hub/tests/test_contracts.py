#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for PQN Swarm Hub FoundUp contracts.

Phase 0 PoC acceptance tests:
1. Contract creation
2. Deterministic IDs
3. Status values
4. Score clamping
"""

import pytest
from datetime import datetime, timezone

from modules.foundups.pqn_swarm_hub import (
    PQNWorkUnit,
    rESPSubmission,
    VerificationDecision,
    ContributionRecord,
    WorkUnitStatus,
    SubmissionStatus,
    generate_id,
)


class TestPQNWorkUnit:
    """Tests for PQNWorkUnit contract."""

    def test_creation(self):
        """Work unit can be created with required fields."""
        wu = PQNWorkUnit(
            description="Test sweep",
            config={"steps": 1200},
            creator_id="agent_x",
        )
        assert wu.work_unit_id
        assert wu.status == WorkUnitStatus.PENDING
        assert wu.description == "Test sweep"
        assert wu.config == {"steps": 1200}
        assert wu.creator_id == "agent_x"

    def test_deterministic_id_same_inputs(self):
        """Same inputs produce same work_unit_id when created_at is fixed."""
        ts = datetime(2026, 3, 29, 12, 0, 0, tzinfo=timezone.utc)
        wu1 = PQNWorkUnit(
            description="Test sweep",
            config={"steps": 1200},
            creator_id="agent_x",
            created_at=ts,
        )
        wu2 = PQNWorkUnit(
            description="Test sweep",
            config={"steps": 1200},
            creator_id="agent_x",
            created_at=ts,
        )
        assert wu1.work_unit_id == wu2.work_unit_id

    def test_status_values(self):
        """All status values are valid."""
        wu = PQNWorkUnit(
            description="Test",
            config={},
            creator_id="x",
            status=WorkUnitStatus.IN_PROGRESS,
        )
        assert wu.status == WorkUnitStatus.IN_PROGRESS


class TestRESPSubmission:
    """Tests for rESPSubmission contract."""

    def test_creation(self):
        """Submission can be created with required fields."""
        sub = rESPSubmission(
            work_unit_id="wu_123",
            submitter_id="agent_x",
            metrics={"coherence": 0.74, "pqn_rate": 0.12},
        )
        assert sub.submission_id
        assert sub.status == SubmissionStatus.PENDING_VERIFICATION
        assert sub.metrics["coherence"] == 0.74

    def test_artifacts_default_empty(self):
        """Artifacts list defaults to empty."""
        sub = rESPSubmission(
            work_unit_id="wu_123",
            submitter_id="agent_x",
            metrics={},
        )
        assert sub.artifacts == []


class TestVerificationDecision:
    """Tests for VerificationDecision contract."""

    def test_accept_decision(self):
        """Accept decision can be created."""
        dec = VerificationDecision(
            submission_id="sub_123",
            decision="accept",
            verifier_id="verifier_y",
            rationale="Resonance within range",
        )
        assert dec.decision_id
        assert dec.decision == "accept"
        assert dec.rationale == "Resonance within range"

    def test_reject_decision(self):
        """Reject decision can be created."""
        dec = VerificationDecision(
            submission_id="sub_123",
            decision="reject",
            verifier_id="verifier_y",
            rationale="Coherence too low",
        )
        assert dec.decision == "reject"


class TestContributionRecord:
    """Tests for ContributionRecord contract."""

    def test_creation(self):
        """Contribution record can be created."""
        cr = ContributionRecord(
            work_unit_id="wu_123",
            submission_id="sub_123",
            decision_id="dec_123",
            contributor_id="agent_x",
            score=0.85,
        )
        assert cr.contribution_id
        assert cr.score == 0.85

    def test_score_clamped_high(self):
        """Score above 1.0 is clamped to 1.0."""
        cr = ContributionRecord(
            work_unit_id="wu_123",
            submission_id="sub_123",
            decision_id="dec_123",
            contributor_id="agent_x",
            score=1.5,
        )
        assert cr.score == 1.0

    def test_score_clamped_low(self):
        """Score below 0.0 is clamped to 0.0."""
        cr = ContributionRecord(
            work_unit_id="wu_123",
            submission_id="sub_123",
            decision_id="dec_123",
            contributor_id="agent_x",
            score=-0.5,
        )
        assert cr.score == 0.0


class TestGenerateId:
    """Tests for deterministic ID generation."""

    def test_same_inputs_same_id(self):
        """Same inputs produce same ID."""
        id1 = generate_id("test", "a", "b", "c")
        id2 = generate_id("test", "a", "b", "c")
        assert id1 == id2

    def test_different_inputs_different_id(self):
        """Different inputs produce different IDs."""
        id1 = generate_id("test", "a", "b", "c")
        id2 = generate_id("test", "a", "b", "d")
        assert id1 != id2

    def test_id_length(self):
        """ID is 16 characters (hex)."""
        id1 = generate_id("test", "a")
        assert len(id1) == 16
