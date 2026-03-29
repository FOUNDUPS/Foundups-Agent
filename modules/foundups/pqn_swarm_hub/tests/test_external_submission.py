"""
PQN Swarm Hub - External Submission Path Tests

Tests for generic external submission support (Phase 2).
Validates that externally-sourced work units and submissions
can flow through the same verification/contribution pipeline.

WSP 5: >=90% test coverage for public API
WSP 72: Module independence
"""

import gc
import json
import pytest
from pathlib import Path

from modules.foundups.pqn_swarm_hub import (
    ContributionReporter,
    SubmissionSink,
    VerificationEngine,
    WorkUnitRegistry,
    WorkUnitStatus,
    SubmissionStatus,
    get_sqlite_store,
    reset_sqlite_store,
)
from modules.foundups.pqn_swarm_hub.src.contracts import PQNWorkUnit, rESPSubmission


@pytest.fixture
def hub(tmp_path):
    """Wire up the full PoC stack with isolated artifact dir."""
    registry = WorkUnitRegistry()
    sink = SubmissionSink(registry)
    engine = VerificationEngine(sink)
    reporter = ContributionReporter(engine, artifact_dir=tmp_path / "contributions")
    return registry, sink, engine, reporter


@pytest.fixture
def persisted_hub(tmp_path):
    """Hub with SQLite persistence."""
    reset_sqlite_store()
    store = get_sqlite_store(db_dir=tmp_path, db_filename="test_external.db")
    registry = WorkUnitRegistry(store=store)
    sink = SubmissionSink(registry, store=store)
    engine = VerificationEngine(sink, store=store)
    reporter = ContributionReporter(engine, store=store, artifact_dir=tmp_path / "contributions")
    yield registry, sink, engine, reporter, store
    # Cleanup
    gc.collect()
    reset_sqlite_store()


class TestExternalWorkUnitRegistration:
    """Tests for register_external() method."""

    def test_register_external_sets_source(self, hub):
        """register_external() creates work unit with source='external'."""
        registry, _, _, _ = hub

        unit = registry.register_external(
            description="External rESP result from GPD",
            config={"external_tool": "gpd", "version": "1.0"},
            creator_id="external_contributor_001",
        )

        assert unit.work_unit_id
        assert unit.source == "external"
        assert unit.status == WorkUnitStatus.PENDING
        assert unit.creator_id == "external_contributor_001"

    def test_register_internal_default_source(self, hub):
        """Default register() creates work unit with source='internal'."""
        registry, _, _, _ = hub

        unit = registry.register(
            description="Internal detector work",
            config={"steps": 1200},
            creator_id="internal_agent",
        )

        assert unit.source == "internal"

    def test_register_explicit_source(self, hub):
        """register() accepts explicit source parameter."""
        registry, _, _, _ = hub

        unit = registry.register(
            description="Custom source work",
            config={},
            creator_id="agent",
            source="custom_pipeline",
        )

        assert unit.source == "custom_pipeline"


class TestExternalSubmission:
    """Tests for submit_external() method."""

    def test_submit_external_sets_source(self, hub):
        """submit_external() creates submission with source='external'."""
        registry, sink, _, _ = hub

        # Register external work unit
        unit = registry.register_external(
            description="External submission test",
            config={"external": True},
            creator_id="ext_contributor",
        )

        # Submit externally
        submission = sink.submit_external(
            work_unit_id=unit.work_unit_id,
            submitter_id="ext_contributor",
            metrics={"coherence": 0.72, "custom_metric": 42},
            artifacts=["external/results.json"],
        )

        assert submission.submission_id
        assert submission.source == "external"
        assert submission.metrics["custom_metric"] == 42

    def test_submit_internal_default_source(self, hub):
        """Default submit() creates submission with source='internal'."""
        registry, sink, _, _ = hub

        unit = registry.register(
            description="Internal submission test",
            config={},
            creator_id="agent",
        )

        submission = sink.submit(
            work_unit_id=unit.work_unit_id,
            submitter_id="agent",
            metrics={"coherence": 0.8},
        )

        assert submission.source == "internal"

    def test_submit_explicit_source(self, hub):
        """submit() accepts explicit source parameter."""
        registry, sink, _, _ = hub

        unit = registry.register(
            description="Custom source test",
            config={},
            creator_id="agent",
        )

        submission = sink.submit(
            work_unit_id=unit.work_unit_id,
            submitter_id="agent",
            metrics={"coherence": 0.75},
            source="custom_pipeline",
        )

        assert submission.source == "custom_pipeline"


class TestExternalFullFlow:
    """End-to-end tests for external submission flow."""

    def test_external_accepted_flow(self, hub, tmp_path):
        """Full external flow: register_external -> submit_external -> verify -> contribution."""
        registry, sink, engine, reporter = hub

        # 1. Register external work unit
        unit = registry.register_external(
            description="External rESP detection result",
            config={
                "tool": "gpd",
                "version": "2.0",
                "parameters": {"sweep_range": [6.5, 7.5]},
            },
            creator_id="gpd_user_001",
        )
        assert unit.source == "external"

        # 2. Submit external results
        submission = sink.submit_external(
            work_unit_id=unit.work_unit_id,
            submitter_id="gpd_user_001",
            metrics={
                "coherence": 0.75,
                "pqn_rate": 0.08,
                "resonance_hz": 7.02,
                "gpd_confidence": 0.92,
            },
            artifacts=["gpd_output/run_001.json"],
        )
        assert submission.source == "external"
        assert registry.get(unit.work_unit_id).status == WorkUnitStatus.IN_PROGRESS

        # 3. Verify (auto-verify accepts coherence >= 0.618)
        decision = engine.auto_verify(submission.submission_id)
        assert decision.decision == "accept"
        assert sink.get(submission.submission_id).status == SubmissionStatus.ACCEPTED

        # 4. Record contribution
        contribution = reporter.record(
            work_unit_id=unit.work_unit_id,
            submission_id=submission.submission_id,
            decision_id=decision.decision_id,
            contributor_id="gpd_user_001",
            score=0.82,
        )
        assert contribution.contribution_id
        assert contribution.score == 0.82

    def test_external_rejected_flow(self, hub):
        """External submission below threshold is rejected."""
        registry, sink, engine, reporter = hub

        unit = registry.register_external(
            description="Low quality external result",
            config={},
            creator_id="contributor",
        )

        submission = sink.submit_external(
            work_unit_id=unit.work_unit_id,
            submitter_id="contributor",
            metrics={"coherence": 0.4},  # Below 0.618 threshold
        )

        decision = engine.auto_verify(submission.submission_id)
        assert decision.decision == "reject"
        assert sink.get(submission.submission_id).status == SubmissionStatus.REJECTED

        # Cannot record contribution for rejected
        with pytest.raises(ValueError, match="rejected"):
            reporter.record(
                work_unit_id=unit.work_unit_id,
                submission_id=submission.submission_id,
                decision_id=decision.decision_id,
                contributor_id="contributor",
                score=0.5,
            )


class TestExternalPersistence:
    """Tests for source field persistence."""

    def test_source_field_persisted(self, persisted_hub):
        """Source field survives SQLite round-trip."""
        registry, sink, engine, reporter, store = persisted_hub

        # Register and submit external
        unit = registry.register_external(
            description="Persistence test",
            config={"test": True},
            creator_id="ext_user",
        )
        submission = sink.submit_external(
            work_unit_id=unit.work_unit_id,
            submitter_id="ext_user",
            metrics={"coherence": 0.7},
        )

        # Retrieve from store directly
        stored_unit = store.get_work_unit(unit.work_unit_id)
        stored_sub = store.get_submission(submission.submission_id)

        assert stored_unit.source == "external"
        assert stored_sub.source == "external"

    def test_mixed_internal_external_persistence(self, persisted_hub):
        """Both internal and external sources are stored correctly."""
        registry, sink, _, _, store = persisted_hub

        # Internal work unit
        internal_unit = registry.register(
            description="Internal work",
            config={},
            creator_id="agent",
        )
        internal_sub = sink.submit(
            work_unit_id=internal_unit.work_unit_id,
            submitter_id="agent",
            metrics={"coherence": 0.8},
        )

        # External work unit
        external_unit = registry.register_external(
            description="External work",
            config={},
            creator_id="contributor",
        )
        external_sub = sink.submit_external(
            work_unit_id=external_unit.work_unit_id,
            submitter_id="contributor",
            metrics={"coherence": 0.75},
        )

        # Verify both stored with correct source
        assert store.get_work_unit(internal_unit.work_unit_id).source == "internal"
        assert store.get_work_unit(external_unit.work_unit_id).source == "external"
        assert store.get_submission(internal_sub.submission_id).source == "internal"
        assert store.get_submission(external_sub.submission_id).source == "external"


class TestSourceFieldInContracts:
    """Direct tests for source field in dataclasses."""

    def test_work_unit_default_source(self):
        """PQNWorkUnit defaults to source='internal'."""
        unit = PQNWorkUnit(
            description="Test",
            config={},
            creator_id="test",
        )
        assert unit.source == "internal"

    def test_work_unit_explicit_source(self):
        """PQNWorkUnit accepts explicit source."""
        unit = PQNWorkUnit(
            description="Test",
            config={},
            creator_id="test",
            source="external",
        )
        assert unit.source == "external"

    def test_submission_default_source(self):
        """rESPSubmission defaults to source='internal'."""
        sub = rESPSubmission(
            work_unit_id="test_wu",
            submitter_id="test",
            metrics={},
        )
        assert sub.source == "internal"

    def test_submission_explicit_source(self):
        """rESPSubmission accepts explicit source."""
        sub = rESPSubmission(
            work_unit_id="test_wu",
            submitter_id="test",
            metrics={},
            source="external",
        )
        assert sub.source == "external"
