#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for PQN Swarm Hub Publication Adapter.

Tests:
1. PublicationAdapter initialization
2. Successful publish via mocked MoltBook
3. Rejected decision does not publish
4. Stub fallback when MoltBook unavailable
5. Payload formatting
"""

import gc
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from modules.foundups.pqn_swarm_hub import (
    ContributionRecord,
    PQNWorkUnit,
    VerificationDecision,
    rESPSubmission,
)
from modules.foundups.pqn_swarm_hub.src.publication_adapter import (
    PublicationAdapter,
    PublicationResult,
    get_publication_adapter,
    reset_publication_adapter,
)


@pytest.fixture
def work_unit() -> PQNWorkUnit:
    """Sample work unit."""
    return PQNWorkUnit(
        description="Test 7.05Hz resonance sweep",
        config={"steps": 1200, "dt": 0.071},
        creator_id="test_creator",
    )


@pytest.fixture
def submission(work_unit: PQNWorkUnit) -> rESPSubmission:
    """Sample submission."""
    return rESPSubmission(
        work_unit_id=work_unit.work_unit_id,
        submitter_id="test_submitter",
        metrics={
            "coherence": 0.85,
            "pqn_rate": 0.12,
            "resonance_hz": 7.05,
            "paradox_rate": 0.02,
        },
        artifacts=["data/events.jsonl", "data/metrics.csv"],
    )


@pytest.fixture
def accept_decision(submission: rESPSubmission) -> VerificationDecision:
    """Sample accepted decision."""
    return VerificationDecision(
        submission_id=submission.submission_id,
        decision="accept",
        verifier_id="auto",
        rationale="Coherence meets φ-floor threshold",
    )


@pytest.fixture
def reject_decision(submission: rESPSubmission) -> VerificationDecision:
    """Sample rejected decision."""
    return VerificationDecision(
        submission_id=submission.submission_id,
        decision="reject",
        verifier_id="auto",
        rationale="Coherence below threshold",
    )


@pytest.fixture
def contribution(
    work_unit: PQNWorkUnit,
    submission: rESPSubmission,
    accept_decision: VerificationDecision,
) -> ContributionRecord:
    """Sample contribution."""
    return ContributionRecord(
        work_unit_id=work_unit.work_unit_id,
        submission_id=submission.submission_id,
        decision_id=accept_decision.decision_id,
        contributor_id="test_contributor",
        score=0.95,
    )


@pytest.fixture(autouse=True)
def reset_adapter():
    """Reset singleton before each test."""
    reset_publication_adapter()
    yield
    reset_publication_adapter()
    gc.collect()


class TestPublicationAdapterInit:
    """Tests for PublicationAdapter initialization."""

    def test_init_defaults(self):
        """Adapter initializes with defaults."""
        adapter = PublicationAdapter()
        assert not adapter.is_connected
        assert adapter.get_stub_publications() == []

    def test_init_no_auto_connect(self):
        """Adapter does not connect without auto_connect."""
        adapter = PublicationAdapter(auto_connect=False)
        assert not adapter.is_connected

    def test_get_status(self):
        """get_status returns adapter state."""
        adapter = PublicationAdapter()
        status = adapter.get_status()
        assert "connected" in status
        assert "stub_publications_pending" in status
        assert status["connected"] is False
        assert status["stub_publications_pending"] == 0


class TestPublishSuccess:
    """Tests for successful publication via mocked MoltBook."""

    def test_publish_success_via_moltbook(
        self,
        work_unit: PQNWorkUnit,
        submission: rESPSubmission,
        accept_decision: VerificationDecision,
        contribution: ContributionRecord,
    ):
        """Successful publish via mocked MoltBook adapter."""
        adapter = PublicationAdapter()

        # Mock MoltBook adapter
        mock_moltbook = MagicMock()
        mock_moltbook.publish_research.return_value = {
            "post_id": "moltbook_abc123",
            "channel": "pqn_research",
            "status": "published",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duplicate": False,
        }

        # Inject mock
        adapter._moltbook_adapter = mock_moltbook
        adapter._connected = True

        result = adapter.publish(
            work_unit=work_unit,
            submission=submission,
            decision=accept_decision,
            contribution=contribution,
            actor_id="test_actor",
        )

        assert result.success is True
        assert result.post_id == "moltbook_abc123"
        assert result.channel == "pqn_research"
        assert result.status == "published"
        assert result.duplicate is False

        # Verify MoltBook was called correctly
        mock_moltbook.publish_research.assert_called_once()
        call_kwargs = mock_moltbook.publish_research.call_args.kwargs
        assert call_kwargs["research_id"] == contribution.contribution_id
        assert "PQN:" in call_kwargs["topic"]
        assert call_kwargs["actor_id"] == "test_actor"

    def test_publish_returns_duplicate_flag(
        self,
        work_unit: PQNWorkUnit,
        submission: rESPSubmission,
        accept_decision: VerificationDecision,
        contribution: ContributionRecord,
    ):
        """Duplicate flag is passed through from MoltBook."""
        adapter = PublicationAdapter()

        mock_moltbook = MagicMock()
        mock_moltbook.publish_research.return_value = {
            "post_id": "moltbook_abc123",
            "channel": "pqn_research",
            "status": "published",
            "duplicate": True,
        }

        adapter._moltbook_adapter = mock_moltbook
        adapter._connected = True

        result = adapter.publish(
            work_unit=work_unit,
            submission=submission,
            decision=accept_decision,
            contribution=contribution,
        )

        assert result.success is True
        assert result.duplicate is True


class TestRejectedDecision:
    """Tests proving rejected decisions do not publish."""

    def test_rejected_decision_does_not_publish(
        self,
        work_unit: PQNWorkUnit,
        submission: rESPSubmission,
        reject_decision: VerificationDecision,
        contribution: ContributionRecord,
    ):
        """Rejected decision returns immediately without publishing."""
        adapter = PublicationAdapter()

        mock_moltbook = MagicMock()
        adapter._moltbook_adapter = mock_moltbook
        adapter._connected = True

        result = adapter.publish(
            work_unit=work_unit,
            submission=submission,
            decision=reject_decision,
            contribution=contribution,
        )

        assert result.success is False
        assert result.status == "rejected_decision"
        assert "reject" in result.message.lower()
        assert result.post_id is None

        # MoltBook should NOT be called
        mock_moltbook.publish_research.assert_not_called()

    def test_reject_reason_in_message(
        self,
        work_unit: PQNWorkUnit,
        submission: rESPSubmission,
        reject_decision: VerificationDecision,
        contribution: ContributionRecord,
    ):
        """Rejection reason is included in result message."""
        adapter = PublicationAdapter()

        result = adapter.publish(
            work_unit=work_unit,
            submission=submission,
            decision=reject_decision,
            contribution=contribution,
        )

        assert "reject" in result.message.lower()
        assert result.status == "rejected_decision"


class TestStubFallback:
    """Tests for graceful fallback when MoltBook unavailable."""

    def test_stub_fallback_when_not_connected(
        self,
        work_unit: PQNWorkUnit,
        submission: rESPSubmission,
        accept_decision: VerificationDecision,
        contribution: ContributionRecord,
    ):
        """Stub publish when MoltBook unavailable."""
        adapter = PublicationAdapter()
        # Force not connected state by setting _connected = False and _moltbook_adapter = None
        adapter._connected = False
        adapter._moltbook_adapter = None

        # Mock connect() to return False (simulate MoltBook unavailable)
        adapter.connect = lambda: False

        result = adapter.publish(
            work_unit=work_unit,
            submission=submission,
            decision=accept_decision,
            contribution=contribution,
        )

        # Stub should succeed
        assert result.success is True
        assert result.status == "stub"
        assert result.channel == "stub"
        assert "stub_" in result.post_id
        assert "unavailable" in result.message.lower()

    def test_stub_records_publication(
        self,
        work_unit: PQNWorkUnit,
        submission: rESPSubmission,
        accept_decision: VerificationDecision,
        contribution: ContributionRecord,
    ):
        """Stub mode records publication for later sync."""
        adapter = PublicationAdapter()
        # Force stub mode
        adapter._connected = False
        adapter._moltbook_adapter = None
        adapter.connect = lambda: False

        result = adapter.publish(
            work_unit=work_unit,
            submission=submission,
            decision=accept_decision,
            contribution=contribution,
        )

        stubs = adapter.get_stub_publications()
        assert len(stubs) == 1
        assert stubs[0]["payload"]["research_id"] == contribution.contribution_id

    def test_clear_stub_publications(
        self,
        work_unit: PQNWorkUnit,
        submission: rESPSubmission,
        accept_decision: VerificationDecision,
        contribution: ContributionRecord,
    ):
        """clear_stub_publications clears and returns count."""
        adapter = PublicationAdapter()
        # Force stub mode
        adapter._connected = False
        adapter._moltbook_adapter = None
        adapter.connect = lambda: False

        # Create second work unit for different contribution ID
        work_unit2 = PQNWorkUnit(
            description="Second work unit",
            config={"steps": 500},
            creator_id="test_creator",
        )
        submission2 = rESPSubmission(
            work_unit_id=work_unit2.work_unit_id,
            submitter_id="test_submitter",
            metrics={"coherence": 0.9},
        )
        contribution2 = ContributionRecord(
            work_unit_id=work_unit2.work_unit_id,
            submission_id=submission2.submission_id,
            decision_id=accept_decision.decision_id,
            contributor_id="test_contributor",
            score=0.9,
        )

        # Publish twice with different contributions
        adapter.publish(work_unit, submission, accept_decision, contribution)
        adapter.publish(work_unit2, submission2, accept_decision, contribution2)

        assert len(adapter.get_stub_publications()) == 2

        count = adapter.clear_stub_publications()
        assert count == 2
        assert len(adapter.get_stub_publications()) == 0


class TestPayloadFormatting:
    """Tests for payload formatting."""

    def test_payload_contains_required_fields(
        self,
        work_unit: PQNWorkUnit,
        submission: rESPSubmission,
        accept_decision: VerificationDecision,
        contribution: ContributionRecord,
    ):
        """Payload contains all required fields."""
        adapter = PublicationAdapter()

        payload = adapter._format_payload(
            work_unit, submission, accept_decision, contribution
        )

        assert payload["research_id"] == contribution.contribution_id
        assert "PQN:" in payload["topic"]
        assert "content" in payload
        assert "metadata" in payload

        # Metadata fields
        meta = payload["metadata"]
        assert meta["work_unit_id"] == work_unit.work_unit_id
        assert meta["submission_id"] == submission.submission_id
        assert meta["contribution_id"] == contribution.contribution_id
        assert meta["contributor_id"] == contribution.contributor_id
        assert meta["score"] == contribution.score
        assert meta["coherence"] == 0.85
        assert meta["pqn_rate"] == 0.12

    def test_payload_content_includes_metrics(
        self,
        work_unit: PQNWorkUnit,
        submission: rESPSubmission,
        accept_decision: VerificationDecision,
        contribution: ContributionRecord,
    ):
        """Content includes formatted metrics."""
        adapter = PublicationAdapter()

        payload = adapter._format_payload(
            work_unit, submission, accept_decision, contribution
        )

        content = payload["content"]
        assert "Coherence:" in content
        assert "PQN Rate:" in content
        assert "0.85" in content  # coherence value

    def test_payload_includes_artifacts(
        self,
        work_unit: PQNWorkUnit,
        submission: rESPSubmission,
        accept_decision: VerificationDecision,
        contribution: ContributionRecord,
    ):
        """Artifacts are included in content."""
        adapter = PublicationAdapter()

        payload = adapter._format_payload(
            work_unit, submission, accept_decision, contribution
        )

        content = payload["content"]
        assert "Artifacts" in content
        assert "events.jsonl" in content


class TestMoltBookError:
    """Tests for MoltBook error handling."""

    def test_moltbook_error_returns_failure(
        self,
        work_unit: PQNWorkUnit,
        submission: rESPSubmission,
        accept_decision: VerificationDecision,
        contribution: ContributionRecord,
    ):
        """MoltBook errors result in graceful failure."""
        adapter = PublicationAdapter()

        mock_moltbook = MagicMock()
        mock_moltbook.publish_research.side_effect = Exception("MoltBook down")

        adapter._moltbook_adapter = mock_moltbook
        adapter._connected = True

        result = adapter.publish(
            work_unit=work_unit,
            submission=submission,
            decision=accept_decision,
            contribution=contribution,
        )

        assert result.success is False
        assert result.status == "failed"
        assert "error" in result.message.lower() or "moltbook" in result.message.lower()


class TestSingleton:
    """Tests for singleton behavior."""

    def test_get_publication_adapter_returns_same_instance(self):
        """get_publication_adapter returns singleton."""
        adapter1 = get_publication_adapter()
        adapter2 = get_publication_adapter()
        assert adapter1 is adapter2

    def test_reset_clears_singleton(self):
        """reset_publication_adapter clears singleton."""
        adapter1 = get_publication_adapter()
        reset_publication_adapter()
        adapter2 = get_publication_adapter()
        assert adapter1 is not adapter2
