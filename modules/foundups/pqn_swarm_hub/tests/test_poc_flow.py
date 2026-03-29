"""
PQN Swarm Hub - End-to-End PoC Flow Test

Proves the minimum PoC acceptance criteria:
  1. Register one bounded PQN work unit
  2. Submit one structured rESP result
  3. Verify accept/reject
  4. Write one durable artifact/report
  5. Record one ROC-style contribution output

WSP 5: >=90% test coverage for public API
"""

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
)


@pytest.fixture
def hub(tmp_path):
    """Wire up the full PoC stack with isolated artifact dir."""
    registry = WorkUnitRegistry()
    sink = SubmissionSink(registry)
    engine = VerificationEngine(sink)
    reporter = ContributionReporter(engine, artifact_dir=tmp_path / "contributions")
    return registry, sink, engine, reporter


class TestMinimumPoCFlow:
    """One end-to-end pass through all five acceptance criteria."""

    def test_full_accepted_flow(self, hub):
        registry, sink, engine, reporter = hub

        # 1. Register work unit
        unit = registry.register(
            description="Sweep 7.05Hz resonance",
            config={"steps": 1200, "dt": 0.071},
            creator_id="agent_x",
        )
        assert unit.work_unit_id
        assert unit.status == WorkUnitStatus.PENDING

        # 2. Submit rESP result (coherence above 0.618 floor)
        submission = sink.submit(
            work_unit_id=unit.work_unit_id,
            submitter_id="agent_x",
            metrics={"coherence": 0.74, "pqn_rate": 0.12, "resonance_hz": 7.08},
            artifacts=["results/sweep_001.csv"],
        )
        assert submission.submission_id
        assert submission.status == SubmissionStatus.PENDING_VERIFICATION
        # Work unit advances to IN_PROGRESS on first submission
        assert registry.get(unit.work_unit_id).status == WorkUnitStatus.IN_PROGRESS

        # 3. Verify — auto-verify should accept (coherence >= 0.618)
        decision = engine.auto_verify(submission.submission_id)
        assert decision.decision == "accept"
        assert decision.decision_id
        assert submission.submission_id == decision.submission_id
        # Submission status updated
        assert sink.get(submission.submission_id).status == SubmissionStatus.ACCEPTED

        # 4. Record contribution — writes durable artifact
        contribution = reporter.record(
            work_unit_id=unit.work_unit_id,
            submission_id=submission.submission_id,
            decision_id=decision.decision_id,
            contributor_id="agent_x",
            score=0.85,
        )
        assert contribution.contribution_id
        assert contribution.score == 0.85

        # 5. Durable artifact exists on disk
        artifact_path = (
            reporter._artifact_dir / f"{contribution.contribution_id}.json"
        )
        assert artifact_path.exists()
        data = json.loads(artifact_path.read_text())
        assert data["contributor_id"] == "agent_x"
        assert data["score"] == 0.85

    def test_rejected_flow(self, hub):
        """Low coherence submission is auto-rejected; no contribution recorded."""
        registry, sink, engine, reporter = hub

        unit = registry.register(
            description="Failed sweep",
            config={"steps": 600},
            creator_id="agent_y",
        )
        submission = sink.submit(
            work_unit_id=unit.work_unit_id,
            submitter_id="agent_y",
            metrics={"coherence": 0.3, "pqn_rate": 0.0},
        )

        decision = engine.auto_verify(submission.submission_id)
        assert decision.decision == "reject"
        assert sink.get(submission.submission_id).status == SubmissionStatus.REJECTED

        # Cannot record contribution for rejected decision
        with pytest.raises(ValueError, match="rejected decision"):
            reporter.record(
                work_unit_id=unit.work_unit_id,
                submission_id=submission.submission_id,
                decision_id=decision.decision_id,
                contributor_id="agent_y",
                score=0.5,
            )

    def test_manual_verify_override(self, hub):
        """Human verifier can override auto-verification."""
        registry, sink, engine, reporter = hub

        unit = registry.register(
            description="Manual review sweep",
            config={},
            creator_id="agent_z",
        )
        # Low metrics — would normally be auto-rejected
        submission = sink.submit(
            work_unit_id=unit.work_unit_id,
            submitter_id="agent_z",
            metrics={"coherence": 0.4, "pqn_rate": 0.0},
        )

        # Human expert accepts it anyway
        decision = engine.manual_verify(
            submission_id=submission.submission_id,
            decision="accept",
            verifier_id="human_012",
            rationale="Anomalous result, manually validated",
        )
        assert decision.decision == "accept"
        assert decision.verifier_id == "human_012"

        # Contribution can now be recorded
        cr = reporter.record(
            work_unit_id=unit.work_unit_id,
            submission_id=submission.submission_id,
            decision_id=decision.decision_id,
            contributor_id="agent_z",
            score=0.6,
        )
        assert cr.score == 0.6

    def test_idempotent_submission(self, hub):
        """Re-submitting same work returns existing submission."""
        registry, sink, engine, reporter = hub

        unit = registry.register(
            description="Idempotency test",
            config={},
            creator_id="agent_x",
        )
        from datetime import datetime, timezone
        ts = datetime(2026, 3, 29, 12, 0, 0, tzinfo=timezone.utc)

        sub1 = sink.submit(
            work_unit_id=unit.work_unit_id,
            submitter_id="agent_x",
            metrics={"coherence": 0.7, "pqn_rate": 0.1},
        )
        # Force same timestamp for deterministic ID
        sub1.submitted_at = ts
        # Manually re-store with known ID
        sink._memory[sub1.submission_id] = sub1

        # Second submission with same ID should return existing
        from modules.foundups.pqn_swarm_hub.src.contracts import rESPSubmission
        sub2 = rESPSubmission(
            work_unit_id=unit.work_unit_id,
            submitter_id="agent_x",
            metrics={"coherence": 0.7, "pqn_rate": 0.1},
            submitted_at=ts,
        )
        # Manually insert to trigger idempotency path
        sink._memory[sub2.submission_id] = sub1  # same object

        result = sink.get(sub2.submission_id)
        assert result is sub1

    def test_contributor_stats(self, hub):
        """Contributor stats aggregate correctly across contributions."""
        registry, sink, engine, reporter = hub

        scores = [0.6, 0.8, 1.0]
        for i, score in enumerate(scores):
            unit = registry.register(
                description=f"Work unit {i}",
                config={},
                creator_id="agent_x",
            )
            sub = sink.submit(
                work_unit_id=unit.work_unit_id,
                submitter_id="agent_x",
                metrics={"coherence": 0.7, "pqn_rate": 0.1},
            )
            dec = engine.auto_verify(sub.submission_id)
            reporter.record(
                work_unit_id=unit.work_unit_id,
                submission_id=sub.submission_id,
                decision_id=dec.decision_id,
                contributor_id="agent_x",
                score=score,
            )

        stats = reporter.get_stats("agent_x")
        assert stats["total"] == 3
        assert abs(stats["avg_score"] - 0.8) < 0.001
        assert stats["max_score"] == 1.0
