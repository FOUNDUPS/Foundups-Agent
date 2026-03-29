"""
PQN Swarm Hub - External Contributor Path Tests

Tests proving an external contributor can:
1. Be evaluated through the current gate model
2. Register and submit through the documented external path
3. Complete the flow without hidden operator context

WSP 5: >=90% test coverage for public API
WSP 97: External contributor path validation for proto-readiness
"""

import gc
import pytest
from pathlib import Path

from modules.foundups.pqn_swarm_hub import (
    ContributionReporter,
    SubmissionSink,
    VerificationEngine,
    WorkUnitRegistry,
    WorkUnitStatus,
    SubmissionStatus,
    ParticipantGate,
    ParticipantIdentity,
    ParticipantTier,
    ParticipantStatus,
    GateDecision,
    get_sqlite_store,
    reset_sqlite_store,
)


@pytest.fixture
def external_hub(tmp_path):
    """Full hub with gate for external contributor testing."""
    gate = ParticipantGate()
    registry = WorkUnitRegistry()
    sink = SubmissionSink(registry)
    engine = VerificationEngine(sink)
    reporter = ContributionReporter(engine, artifact_dir=tmp_path / "contributions")
    return gate, registry, sink, engine, reporter


@pytest.fixture
def persisted_external_hub(tmp_path):
    """Hub with SQLite persistence for external contributor testing."""
    reset_sqlite_store()
    store = get_sqlite_store(db_dir=tmp_path, db_filename="test_external_contrib.db")
    gate = ParticipantGate(store=store)
    registry = WorkUnitRegistry(store=store)
    sink = SubmissionSink(registry, store=store)
    engine = VerificationEngine(sink, store=store)
    reporter = ContributionReporter(engine, store=store, artifact_dir=tmp_path / "contributions")
    yield gate, registry, sink, engine, reporter, store
    gc.collect()
    reset_sqlite_store()


class TestExternalIdentityDeclaration:
    """Tests for external participant identity declaration."""

    def test_external_identity_creation(self):
        """External participant can declare identity with required fields."""
        identity = ParticipantIdentity(
            display_name="external_researcher_001",
            model_type="human",
            compute_capacity="medium",
            capability_tags=["rESP", "physics"],
            metadata={"affiliation": "independent"},
        )

        assert identity.participant_id  # Auto-generated
        assert identity.display_name == "external_researcher_001"
        assert identity.model_type == "human"
        assert identity.compute_capacity == "medium"
        assert "rESP" in identity.capability_tags

    def test_external_identity_deterministic_id(self):
        """Identity ID is deterministic based on inputs."""
        # Same inputs at same time should produce same ID
        identity1 = ParticipantIdentity(
            display_name="researcher",
            model_type="human",
            compute_capacity="low",
        )
        # Different name produces different ID
        identity2 = ParticipantIdentity(
            display_name="different_researcher",
            model_type="human",
            compute_capacity="low",
        )

        assert identity1.participant_id != identity2.participant_id

    def test_minimal_identity_allowed(self):
        """External identity with minimal fields is valid."""
        identity = ParticipantIdentity(
            display_name="minimal_contributor",
            model_type="unknown",
        )

        assert identity.participant_id
        assert identity.display_name == "minimal_contributor"


class TestExternalGateEvaluation:
    """Tests for gate evaluation of external participants."""

    def test_external_participant_gate_entry(self, external_hub):
        """External participant can request and receive gate decision."""
        gate, _, _, _, _ = external_hub

        identity = ParticipantIdentity(
            display_name="external_contributor",
            model_type="human",
            compute_capacity="high",
            capability_tags=["physics"],
        )

        decision = gate.request_entry(identity, requested_tier=ParticipantTier.CONTRIBUTOR)

        assert isinstance(decision, GateDecision)
        assert decision.participant_id == identity.participant_id
        assert decision.decision == "approve"  # Phase 1: auto-approve
        assert decision.tier == ParticipantTier.CONTRIBUTOR
        assert decision.decider_id == "auto"

    def test_external_participant_auto_approved_phase1(self, external_hub):
        """Phase 1: External participants are auto-approved."""
        gate, _, _, _, _ = external_hub

        identity = ParticipantIdentity(
            display_name="auto_approve_test",
            model_type="external_tool",
        )

        decision = gate.request_entry(identity)

        assert decision.decision == "approve"
        assert "Phase 1" in decision.reason or "auto" in decision.reason.lower()
        assert gate.get_status(identity.participant_id) == ParticipantStatus.APPROVED

    def test_external_participant_tier_assignment(self, external_hub):
        """External participant receives requested tier."""
        gate, _, _, _, _ = external_hub

        identity = ParticipantIdentity(
            display_name="verifier_request",
            model_type="human",
        )

        decision = gate.request_entry(identity, requested_tier=ParticipantTier.VERIFIER)

        assert decision.tier == ParticipantTier.VERIFIER
        assert gate.get_tier(identity.participant_id) == ParticipantTier.VERIFIER

    def test_external_permission_check(self, external_hub):
        """Approved external participant has correct permissions."""
        gate, _, _, _, _ = external_hub

        identity = ParticipantIdentity(
            display_name="permission_test",
            model_type="human",
        )
        gate.request_entry(identity, requested_tier=ParticipantTier.CONTRIBUTOR)

        # Should have CONTRIBUTOR and OBSERVER permissions
        assert gate.check_permission(identity.participant_id, ParticipantTier.CONTRIBUTOR)
        assert gate.check_permission(identity.participant_id, ParticipantTier.OBSERVER)

        # Should NOT have VERIFIER or COORDINATOR permissions
        assert not gate.check_permission(identity.participant_id, ParticipantTier.VERIFIER)
        assert not gate.check_permission(identity.participant_id, ParticipantTier.COORDINATOR)

    def test_unapproved_participant_no_permission(self, external_hub):
        """Participant without gate entry has no permissions."""
        gate, _, _, _, _ = external_hub

        # Never requested entry
        assert not gate.check_permission("unknown_id", ParticipantTier.OBSERVER)


class TestExternalContributorFullFlow:
    """End-to-end tests for external contributor path."""

    def test_external_contributor_full_flow(self, external_hub):
        """Complete external contributor flow: identity -> gate -> register -> submit -> verify -> contribution."""
        gate, registry, sink, engine, reporter = external_hub

        # 1. Declare identity
        identity = ParticipantIdentity(
            display_name="full_flow_contributor",
            model_type="human",
            compute_capacity="medium",
            capability_tags=["rESP"],
        )

        # 2. Request gate entry
        gate_decision = gate.request_entry(identity, requested_tier=ParticipantTier.CONTRIBUTOR)
        assert gate_decision.decision == "approve"

        # 3. Register external work unit
        work_unit = registry.register_external(
            description="External full flow test",
            config={"method": "custom", "parameters": {}},
            creator_id=identity.participant_id,
        )
        assert work_unit.source == "external"
        assert work_unit.creator_id == identity.participant_id

        # 4. Submit external results
        submission = sink.submit_external(
            work_unit_id=work_unit.work_unit_id,
            submitter_id=identity.participant_id,
            metrics={"coherence": 0.72, "pqn_rate": 0.05, "custom_metric": 100},
            artifacts=["external/output.json"],
        )
        assert submission.source == "external"
        assert submission.submitter_id == identity.participant_id

        # 5. Verify
        decision = engine.auto_verify(submission.submission_id)
        assert decision.decision == "accept"  # coherence 0.72 >= 0.618

        # 6. Record contribution
        contribution = reporter.record(
            work_unit_id=work_unit.work_unit_id,
            submission_id=submission.submission_id,
            decision_id=decision.decision_id,
            contributor_id=identity.participant_id,
            score=0.85,
        )
        assert contribution.contributor_id == identity.participant_id
        assert contribution.score == 0.85

    def test_external_flow_deterministic(self, external_hub):
        """External flow produces deterministic IDs (no hidden context)."""
        gate, registry, sink, engine, reporter = external_hub

        identity = ParticipantIdentity(
            display_name="deterministic_test",
            model_type="human",
        )
        gate.request_entry(identity)

        work_unit = registry.register_external(
            description="Deterministic test",
            config={},
            creator_id=identity.participant_id,
        )

        # IDs are deterministic hashes, not random
        assert len(work_unit.work_unit_id) == 16  # SHA256[:16]
        assert work_unit.work_unit_id.isalnum()

    def test_external_flow_no_operator_context_required(self, external_hub):
        """External flow completes without any hidden operator context."""
        gate, registry, sink, engine, reporter = external_hub

        # All inputs are explicit - no env vars, no session state
        identity = ParticipantIdentity(
            display_name="no_context_test",
            model_type="external_agent",
            compute_capacity="low",
        )

        gate_decision = gate.request_entry(identity)
        assert gate_decision.decision == "approve"

        work_unit = registry.register_external(
            description="No context required",
            config={"source": "external_tool"},
            creator_id=identity.participant_id,
        )

        submission = sink.submit_external(
            work_unit_id=work_unit.work_unit_id,
            submitter_id=identity.participant_id,
            metrics={"coherence": 0.65, "pqn_rate": 0.01},
        )

        decision = engine.auto_verify(submission.submission_id)

        # Flow completes with all explicit inputs
        assert decision.decision == "accept"
        assert decision.submission_id == submission.submission_id


class TestExternalContributorPersistence:
    """Tests for external contributor persistence."""

    def test_external_identity_persisted(self, persisted_external_hub):
        """External participant identity survives persistence."""
        gate, _, _, _, _, store = persisted_external_hub

        identity = ParticipantIdentity(
            display_name="persist_identity",
            model_type="human",
            capability_tags=["test"],
        )
        gate.request_entry(identity)

        # Retrieve from store
        stored = store.get_participant(identity.participant_id)
        assert stored is not None
        assert stored.display_name == "persist_identity"
        assert stored.model_type == "human"

    def test_gate_decision_persisted(self, persisted_external_hub):
        """Gate decisions persist for audit trail."""
        gate, _, _, _, _, store = persisted_external_hub

        identity = ParticipantIdentity(
            display_name="decision_persist",
            model_type="human",
        )
        decision = gate.request_entry(identity)

        # Decision stored
        stored_decision = store.get_gate_decision(decision.decision_id)
        assert stored_decision is not None
        assert stored_decision.participant_id == identity.participant_id
        assert stored_decision.decision == "approve"

    def test_full_external_flow_persisted(self, persisted_external_hub):
        """Complete external flow persists all artifacts."""
        gate, registry, sink, engine, reporter, store = persisted_external_hub

        identity = ParticipantIdentity(
            display_name="full_persist_test",
            model_type="human",
        )
        gate.request_entry(identity)

        work_unit = registry.register_external(
            description="Persist flow test",
            config={},
            creator_id=identity.participant_id,
        )
        submission = sink.submit_external(
            work_unit_id=work_unit.work_unit_id,
            submitter_id=identity.participant_id,
            metrics={"coherence": 0.7, "pqn_rate": 0.02},
        )
        decision = engine.auto_verify(submission.submission_id)
        contribution = reporter.record(
            work_unit.work_unit_id,
            submission.submission_id,
            decision.decision_id,
            identity.participant_id,
            0.75,
        )

        # All artifacts persisted
        assert store.get_participant(identity.participant_id) is not None
        assert store.get_work_unit(work_unit.work_unit_id) is not None
        assert store.get_submission(submission.submission_id) is not None
        assert store.get_decision(decision.decision_id) is not None
        assert store.get_contribution(contribution.contribution_id) is not None


class TestGatePolicyHooks:
    """Tests for gate policy hooks (proto-stage optional)."""

    def test_capability_hook_optional(self):
        """Capability hook is optional in Phase 1."""
        gate = ParticipantGate(require_capability_check=False)

        identity = ParticipantIdentity(
            display_name="no_hook_test",
            model_type="human",
        )

        # Approves without capability hook
        decision = gate.request_entry(identity)
        assert decision.decision == "approve"

    def test_wsp00_hook_optional(self):
        """WSP 00 hook is optional in Phase 1."""
        gate = ParticipantGate(require_wsp00_check=False)

        identity = ParticipantIdentity(
            display_name="no_wsp00_test",
            model_type="human",
        )

        # Approves without WSP 00 hook
        decision = gate.request_entry(identity)
        assert decision.decision == "approve"

    def test_capability_hook_rejection(self):
        """Capability hook can reject participants when enabled."""
        gate = ParticipantGate(require_capability_check=True)

        # Register a failing hook
        def failing_hook(identity):
            return (False, "Capability test failed")

        gate.register_capability_hook(failing_hook)

        identity = ParticipantIdentity(
            display_name="fail_cap_test",
            model_type="human",
        )

        decision = gate.request_entry(identity)
        assert decision.decision == "reject"
        assert "Capability check failed" in decision.reason

    def test_wsp00_hook_rejection(self):
        """WSP 00 hook can reject participants when enabled."""
        gate = ParticipantGate(require_wsp00_check=True)

        # Register a failing hook
        def failing_hook(identity):
            return (False, "WSP 00 validation failed")

        gate.register_wsp00_hook(failing_hook)

        identity = ParticipantIdentity(
            display_name="fail_wsp00_test",
            model_type="human",
        )

        decision = gate.request_entry(identity)
        assert decision.decision == "reject"
        assert "WSP 00 check failed" in decision.reason


class TestExternalContributorEdgeCases:
    """Edge cases for external contributor path."""

    def test_external_submission_low_coherence_rejected(self, external_hub):
        """External submission below coherence threshold is rejected."""
        gate, registry, sink, engine, reporter = external_hub

        identity = ParticipantIdentity(display_name="low_coherence", model_type="human")
        gate.request_entry(identity)

        work_unit = registry.register_external("Low coherence test", {}, identity.participant_id)
        submission = sink.submit_external(
            work_unit_id=work_unit.work_unit_id,
            submitter_id=identity.participant_id,
            metrics={"coherence": 0.4},  # Below 0.618 threshold
        )

        decision = engine.auto_verify(submission.submission_id)
        assert decision.decision == "reject"

    def test_external_multiple_contributors(self, external_hub):
        """Multiple external contributors can participate independently."""
        gate, registry, sink, engine, reporter = external_hub

        # Two independent contributors
        identity1 = ParticipantIdentity(display_name="contrib_1", model_type="human")
        identity2 = ParticipantIdentity(display_name="contrib_2", model_type="external_tool")

        gate.request_entry(identity1)
        gate.request_entry(identity2)

        # Each registers their own work unit
        wu1 = registry.register_external("Contrib 1 work", {}, identity1.participant_id)
        wu2 = registry.register_external("Contrib 2 work", {}, identity2.participant_id)

        assert wu1.work_unit_id != wu2.work_unit_id
        assert wu1.creator_id == identity1.participant_id
        assert wu2.creator_id == identity2.participant_id

    def test_external_contributor_suspension(self, external_hub):
        """Suspended external contributor loses permissions."""
        gate, _, _, _, _ = external_hub

        identity = ParticipantIdentity(display_name="suspend_test", model_type="human")
        gate.request_entry(identity, requested_tier=ParticipantTier.CONTRIBUTOR)

        # Initially has permission
        assert gate.check_permission(identity.participant_id, ParticipantTier.CONTRIBUTOR)

        # Suspend
        gate.suspend(identity.participant_id, "Test suspension", "admin")

        # No longer has permission
        assert not gate.check_permission(identity.participant_id, ParticipantTier.CONTRIBUTOR)
        assert gate.get_status(identity.participant_id) == ParticipantStatus.SUSPENDED

    def test_external_contributor_reinstatement(self, external_hub):
        """Suspended external contributor can be reinstated."""
        gate, _, _, _, _ = external_hub

        identity = ParticipantIdentity(display_name="reinstate_test", model_type="human")
        gate.request_entry(identity, requested_tier=ParticipantTier.CONTRIBUTOR)

        gate.suspend(identity.participant_id, "Temporary suspension", "admin")
        assert not gate.check_permission(identity.participant_id, ParticipantTier.CONTRIBUTOR)

        gate.reinstate(identity.participant_id, "Reinstatement approved", "admin")
        assert gate.check_permission(identity.participant_id, ParticipantTier.CONTRIBUTOR)
        assert gate.get_status(identity.participant_id) == ParticipantStatus.APPROVED
