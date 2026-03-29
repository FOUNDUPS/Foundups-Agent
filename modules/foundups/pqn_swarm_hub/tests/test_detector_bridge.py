#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for PQN Swarm Hub DetectorBridge.

Phase 1 integration tests:
1. DetectorBridge.run() calls pqn_alignment.run_detector()
2. Metrics are correctly parsed from CSV/JSONL artifacts
3. Full flow: register -> detector -> submit -> verify -> contribution

Per 012 correction:
- Do NOT assume detector output auto-accepts
- Use manual_verify() for guaranteed happy-path proof
"""

import os
import tempfile
import shutil
import pytest

from modules.foundups.pqn_swarm_hub import (
    PQNWorkUnit,
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ContributionReporter,
    DetectorBridge,
    WorkUnitStatus,
    SubmissionStatus,
)


@pytest.fixture
def temp_output_dir():
    """Create temp directory for detector output."""
    d = tempfile.mkdtemp(prefix="pqn_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def services():
    """Create fresh service instances."""
    registry = WorkUnitRegistry()
    sink = SubmissionSink(registry)
    engine = VerificationEngine(sink)
    reporter = ContributionReporter(engine)
    bridge = DetectorBridge()
    return {
        "registry": registry,
        "sink": sink,
        "engine": engine,
        "reporter": reporter,
        "bridge": bridge,
    }


class TestDetectorBridge:
    """Unit tests for DetectorBridge."""

    def test_bridge_runs_detector(self, temp_output_dir, services):
        """DetectorBridge.run() executes pqn_alignment.run_detector()."""
        bridge = services["bridge"]
        registry = services["registry"]

        # Register work unit with minimal config for fast execution
        work_unit = registry.register(
            description="Test detector bridge",
            config={
                "script": "^^^",
                "steps": 50,
                "dt": 0.071,
                "out_dir": temp_output_dir,
            },
            creator_id="test_agent",
        )

        # Run detector via bridge
        result = bridge.run(work_unit)

        # Verify result structure
        assert "events_path" in result
        assert "metrics_csv" in result
        assert "metrics" in result
        assert "steps" in result

        # Verify files were created
        assert os.path.exists(result["events_path"])
        assert os.path.exists(result["metrics_csv"])

    def test_bridge_parses_metrics(self, temp_output_dir, services):
        """DetectorBridge extracts metrics from detector artifacts."""
        bridge = services["bridge"]
        registry = services["registry"]

        work_unit = registry.register(
            description="Test metrics parsing",
            config={
                "script": "^^^&&&",
                "steps": 100,
                "dt": 0.071,
                "out_dir": temp_output_dir,
            },
            creator_id="test_agent",
        )

        result = bridge.run(work_unit)
        metrics = result["metrics"]

        # Verify metric fields exist
        assert "coherence" in metrics
        assert "pqn_rate" in metrics
        assert "paradox_rate" in metrics
        assert "resonance_hz" in metrics  # may be None if no hits
        assert "sample_count" in metrics

        # Coherence should be a float in [0, 1]
        assert isinstance(metrics["coherence"], float)
        assert 0.0 <= metrics["coherence"] <= 1.0

        # Rates should be non-negative
        assert metrics["pqn_rate"] >= 0.0
        assert metrics["paradox_rate"] >= 0.0


class TestSubmitFromDetector:
    """Tests for SubmissionSink.submit_from_detector()."""

    def test_submit_from_detector_creates_submission(self, temp_output_dir, services):
        """submit_from_detector() creates rESPSubmission from bridge output."""
        bridge = services["bridge"]
        registry = services["registry"]
        sink = services["sink"]

        work_unit = registry.register(
            description="Test submit from detector",
            config={
                "script": "^^^",
                "steps": 50,
                "dt": 0.071,
                "out_dir": temp_output_dir,
            },
            creator_id="test_agent",
        )

        # Run detector
        bridge_result = bridge.run(work_unit)

        # Submit from detector output
        submission = sink.submit_from_detector(
            work_unit_id=work_unit.work_unit_id,
            bridge_result=bridge_result,
            submitter_id="test_agent",
        )

        # Verify submission
        assert submission.work_unit_id == work_unit.work_unit_id
        assert submission.submitter_id == "test_agent"
        assert submission.status == SubmissionStatus.PENDING_VERIFICATION
        assert "coherence" in submission.metrics
        assert len(submission.artifacts) == 2  # events + csv


class TestDetectorIntegrationFlow:
    """Integration tests for full detector-backed flow."""

    def test_real_detector_verdict(self, temp_output_dir, services):
        """
        Real detector run -> real submission -> real verification verdict.

        Does NOT assume auto-accept. Accepts whatever verdict the detector
        output produces under current verification rules.
        """
        bridge = services["bridge"]
        registry = services["registry"]
        sink = services["sink"]
        engine = services["engine"]

        # Register work unit
        work_unit = registry.register(
            description="Integration test - real verdict",
            config={
                "script": "^^^&&&###",
                "steps": 100,
                "dt": 0.071,
                "out_dir": temp_output_dir,
            },
            creator_id="test_agent",
        )

        # Run detector
        bridge_result = bridge.run(work_unit)

        # Submit
        submission = sink.submit_from_detector(
            work_unit_id=work_unit.work_unit_id,
            bridge_result=bridge_result,
            submitter_id="test_agent",
        )

        # Auto-verify - accept whatever verdict
        decision = engine.auto_verify(submission.submission_id)

        # Verify decision was made (accept or reject)
        assert decision.decision in ("accept", "reject")
        assert decision.verifier_id == "auto"
        assert "coherence=" in decision.rationale

        # Submission status should reflect verdict
        updated_sub = sink.get(submission.submission_id)
        if decision.decision == "accept":
            assert updated_sub.status == SubmissionStatus.ACCEPTED
        else:
            assert updated_sub.status == SubmissionStatus.REJECTED

    def test_full_happy_path_with_manual_verify(self, temp_output_dir, services):
        """
        Full flow using manual_verify() for guaranteed contribution recording.

        Proves: register -> detector -> submit -> manual_verify(accept) -> contribution
        """
        bridge = services["bridge"]
        registry = services["registry"]
        sink = services["sink"]
        engine = services["engine"]
        reporter = services["reporter"]

        # Register work unit
        work_unit = registry.register(
            description="Happy path test",
            config={
                "script": "^^^",
                "steps": 50,
                "dt": 0.071,
                "out_dir": temp_output_dir,
            },
            creator_id="test_agent",
        )

        # Run detector
        bridge_result = bridge.run(work_unit)

        # Submit
        submission = sink.submit_from_detector(
            work_unit_id=work_unit.work_unit_id,
            bridge_result=bridge_result,
            submitter_id="test_agent",
        )

        # Manual accept to guarantee happy path
        decision = engine.manual_verify(
            submission_id=submission.submission_id,
            decision="accept",
            verifier_id="test_verifier",
            rationale="Manual accept for integration test",
        )

        assert decision.decision == "accept"

        # Record contribution
        contribution = reporter.record(
            work_unit_id=work_unit.work_unit_id,
            submission_id=submission.submission_id,
            decision_id=decision.decision_id,
            contributor_id="test_agent",
            score=0.85,
        )

        # Verify full chain
        assert contribution.work_unit_id == work_unit.work_unit_id
        assert contribution.submission_id == submission.submission_id
        assert contribution.decision_id == decision.decision_id
        assert contribution.contributor_id == "test_agent"
        assert contribution.score == 0.85

        # Verify stats
        stats = reporter.get_stats("test_agent")
        assert stats["total"] == 1
        assert stats["avg_score"] == 0.85
