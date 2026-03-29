"""Tests for FAMAdapter live validation against FAMDaemon.

Phase 2 Gate: Proves FAMAdapter can emit real contribution and verification
events into a live FAMDaemon event store without direct core mutation.

Coverage:
1. emit_contribution_event() with live FAMDaemon
2. emit_verification_event() with live FAMDaemon
3. Events appear in FAM event store
4. No direct core mutation
5. Adapter boundary respected

WSP References:
- WSP 72: Module independence
- WSP 91: Observability (contribution events audit-safe)
- WSP 97: Lifecycle evaluation (externalization gate)
"""

import gc
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pytest

# FAMDaemon imports
from modules.foundups.agent_market.src.fam_daemon import (
    FAMDaemon,
    get_fam_daemon,
)
import modules.foundups.agent_market.src.fam_daemon as fam_module

# PQN Swarm Hub imports
from modules.foundups.pqn_swarm_hub import (
    ContributionRecord,
    VerificationDecision,
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ContributionReporter,
)
from modules.foundups.pqn_swarm_hub.src.fam_adapter import (
    FAMAdapter,
    get_fam_adapter,
)
import modules.foundups.pqn_swarm_hub.src.fam_adapter as adapter_module


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_fam_daemon(tmp_path) -> Generator[FAMDaemon, None, None]:
    """Create a temporary FAMDaemon for testing.

    Uses isolated temp storage to avoid polluting real FAM store.
    """
    # Reset module singleton
    fam_module._daemon = None

    daemon = FAMDaemon(
        data_dir=tmp_path / "fam_data",
        heartbeat_interval_sec=60.0,  # Long interval - we control heartbeats
        auto_start=False,  # Don't start heartbeat loop
    )

    yield daemon

    # Cleanup
    if daemon._running:
        daemon.stop()
    fam_module._daemon = None
    gc.collect()


@pytest.fixture
def live_fam_adapter(temp_fam_daemon) -> Generator[FAMAdapter, None, None]:
    """Create FAMAdapter connected to live temp FAMDaemon.

    This is the key fixture for live validation testing.
    """
    # Reset adapter singleton
    adapter_module._adapter_instance = None

    # Create adapter and manually wire to our temp daemon
    adapter = FAMAdapter(auto_connect=False)

    # Manually connect to temp daemon (bypassing module-level singleton)
    adapter._fam_daemon = temp_fam_daemon
    adapter._emit_fn = temp_fam_daemon.emit
    adapter._connected = True

    yield adapter

    # Cleanup
    adapter_module._adapter_instance = None


@pytest.fixture
def pqn_services() -> dict:
    """Create PQN Swarm Hub services (in-memory)."""
    registry = WorkUnitRegistry()
    sink = SubmissionSink(registry)
    engine = VerificationEngine(sink)
    reporter = ContributionReporter(engine)

    return {
        "registry": registry,
        "sink": sink,
        "engine": engine,
        "reporter": reporter,
    }


@pytest.fixture
def sample_contribution(pqn_services) -> ContributionRecord:
    """Create a real ContributionRecord through the PQN flow."""
    registry = pqn_services["registry"]
    sink = pqn_services["sink"]
    engine = pqn_services["engine"]
    reporter = pqn_services["reporter"]

    # Execute real flow
    work_unit = registry.register(
        description="FAM validation test work unit",
        config={"steps": 100, "dt": 0.1},
        creator_id="test_agent",
    )

    submission = sink.submit(
        work_unit_id=work_unit.work_unit_id,
        submitter_id="test_agent",
        metrics={"coherence": 0.85, "pqn_rate": 0.15},
        artifacts=["test_artifact.csv"],
    )

    decision = engine.manual_verify(
        submission_id=submission.submission_id,
        decision="accept",
        verifier_id="test_verifier",
        rationale="Test validation passes",
    )

    contribution = reporter.record(
        work_unit_id=work_unit.work_unit_id,
        submission_id=submission.submission_id,
        decision_id=decision.decision_id,
        contributor_id="test_agent",
        score=0.9,
    )

    return contribution


@pytest.fixture
def sample_verification(pqn_services) -> tuple:
    """Create a real VerificationDecision with associated work_unit_id."""
    registry = pqn_services["registry"]
    sink = pqn_services["sink"]
    engine = pqn_services["engine"]

    work_unit = registry.register(
        description="FAM verification test",
        config={"steps": 50},
        creator_id="test_verifier_agent",
    )

    submission = sink.submit(
        work_unit_id=work_unit.work_unit_id,
        submitter_id="test_verifier_agent",
        metrics={"coherence": 0.7},
    )

    decision = engine.manual_verify(
        submission_id=submission.submission_id,
        decision="accept",
        verifier_id="verifier_001",
        rationale="Verification test",
    )

    return decision, work_unit.work_unit_id


# ============================================================================
# Live Validation Tests
# ============================================================================


class TestFAMLiveConnection:
    """Tests for FAMAdapter connection to live FAMDaemon."""

    def test_adapter_connects_to_live_daemon(self, live_fam_adapter, temp_fam_daemon):
        """FAMAdapter connects to live FAMDaemon."""
        assert live_fam_adapter.is_connected is True
        assert live_fam_adapter._fam_daemon is temp_fam_daemon
        assert live_fam_adapter._emit_fn is not None

    def test_adapter_status_reflects_connection(self, live_fam_adapter):
        """get_status() reflects live connection state."""
        status = live_fam_adapter.get_status()

        assert status["connected"] is True
        assert "fam_module_path" in status


class TestEmitContributionEvent:
    """Tests for emit_contribution_event() with live FAMDaemon."""

    def test_emit_contribution_succeeds(
        self,
        live_fam_adapter,
        sample_contribution,
    ):
        """emit_contribution_event() succeeds with live daemon."""
        success, message = live_fam_adapter.emit_contribution_event(
            contribution=sample_contribution,
            actor_id="pqn_swarm_hub",
        )

        assert success is True
        assert message == "ok"

    def test_contribution_event_appears_in_fam_store(
        self,
        live_fam_adapter,
        temp_fam_daemon,
        sample_contribution,
    ):
        """Emitted contribution event appears in FAM event store."""
        # Emit
        live_fam_adapter.emit_contribution_event(
            contribution=sample_contribution,
            actor_id="pqn_swarm_hub",
        )

        # Query FAM store
        events = temp_fam_daemon.query_events(
            event_type="pqn_contribution_recorded",
        )

        assert len(events) == 1
        event = events[0]

        # Verify event structure
        assert event.event_type == "pqn_contribution_recorded"
        assert event.actor_id == "pqn_swarm_hub"
        assert event.task_id == sample_contribution.work_unit_id

    def test_contribution_payload_contains_required_fields(
        self,
        live_fam_adapter,
        temp_fam_daemon,
        sample_contribution,
    ):
        """Contribution event payload contains all required fields."""
        live_fam_adapter.emit_contribution_event(
            contribution=sample_contribution,
            actor_id="pqn_swarm_hub",
        )

        events = temp_fam_daemon.query_events(
            event_type="pqn_contribution_recorded",
        )
        payload = events[0].payload

        # Verify all required fields
        assert payload["contribution_id"] == sample_contribution.contribution_id
        assert payload["work_unit_id"] == sample_contribution.work_unit_id
        assert payload["submission_id"] == sample_contribution.submission_id
        assert payload["decision_id"] == sample_contribution.decision_id
        assert payload["contributor_id"] == sample_contribution.contributor_id
        assert payload["score"] == sample_contribution.score
        assert payload["source"] == "pqn_swarm_hub"
        assert "recorded_at" in payload  # ISO format timestamp

    def test_contribution_event_persists_to_store(
        self,
        live_fam_adapter,
        temp_fam_daemon,
        sample_contribution,
    ):
        """Contribution event is persisted to FAM event store."""
        # Emit
        live_fam_adapter.emit_contribution_event(
            contribution=sample_contribution,
        )

        # Get store stats
        stats = temp_fam_daemon.get_status()["event_store_stats"]

        assert stats["total_events"] >= 1
        assert "pqn_contribution_recorded" in stats["events_by_type"]
        assert stats["events_by_type"]["pqn_contribution_recorded"] >= 1


class TestEmitVerificationEvent:
    """Tests for emit_verification_event() with live FAMDaemon."""

    def test_emit_verification_succeeds(
        self,
        live_fam_adapter,
        sample_verification,
    ):
        """emit_verification_event() succeeds with live daemon."""
        decision, work_unit_id = sample_verification

        success, message = live_fam_adapter.emit_verification_event(
            decision=decision,
            work_unit_id=work_unit_id,
            actor_id="pqn_swarm_hub",
        )

        assert success is True
        assert message == "ok"

    def test_verification_event_appears_in_fam_store(
        self,
        live_fam_adapter,
        temp_fam_daemon,
        sample_verification,
    ):
        """Emitted verification event appears in FAM event store."""
        decision, work_unit_id = sample_verification

        # Emit
        live_fam_adapter.emit_verification_event(
            decision=decision,
            work_unit_id=work_unit_id,
            actor_id="pqn_swarm_hub",
        )

        # Query FAM store
        events = temp_fam_daemon.query_events(
            event_type="pqn_verification_recorded",
        )

        assert len(events) == 1
        event = events[0]

        # Verify event structure
        assert event.event_type == "pqn_verification_recorded"
        assert event.actor_id == "pqn_swarm_hub"
        assert event.task_id == work_unit_id

    def test_verification_payload_contains_required_fields(
        self,
        live_fam_adapter,
        temp_fam_daemon,
        sample_verification,
    ):
        """Verification event payload contains all required fields."""
        decision, work_unit_id = sample_verification

        live_fam_adapter.emit_verification_event(
            decision=decision,
            work_unit_id=work_unit_id,
            actor_id="pqn_swarm_hub",
        )

        events = temp_fam_daemon.query_events(
            event_type="pqn_verification_recorded",
        )
        payload = events[0].payload

        # Verify all required fields
        assert payload["decision_id"] == decision.decision_id
        assert payload["submission_id"] == decision.submission_id
        assert payload["work_unit_id"] == work_unit_id
        assert payload["decision"] == decision.decision
        assert payload["verifier_id"] == decision.verifier_id
        assert payload["rationale"] == decision.rationale
        assert payload["source"] == "pqn_swarm_hub"
        assert "decided_at" in payload  # ISO format timestamp


class TestAdapterBoundaryRespected:
    """Tests verifying adapter boundary is respected (no direct mutation)."""

    def test_adapter_uses_only_emit_interface(
        self,
        live_fam_adapter,
        temp_fam_daemon,
        sample_contribution,
    ):
        """Adapter uses only FAMDaemon.emit() interface, not direct store access."""
        # The adapter should only have _emit_fn reference
        assert live_fam_adapter._emit_fn == temp_fam_daemon.emit

        # Emit through adapter
        live_fam_adapter.emit_contribution_event(sample_contribution)

        # Verify event went through daemon's emit (has proper event_id format)
        events = temp_fam_daemon.query_events(
            event_type="pqn_contribution_recorded",
        )

        assert len(events) == 1
        assert events[0].event_id.startswith("fam_ev_")
        assert events[0].sequence_id > 0

    def test_no_direct_event_store_access(self, live_fam_adapter):
        """Adapter does not expose direct event store access."""
        # Adapter should not have _event_store attribute
        assert not hasattr(live_fam_adapter, "_event_store")

        # Adapter should not have write() method
        assert not hasattr(live_fam_adapter, "write")

        # Adapter should only expose emit methods
        public_methods = [m for m in dir(live_fam_adapter) if not m.startswith("_")]
        assert "emit_contribution_event" in public_methods
        assert "emit_verification_event" in public_methods
        assert "connect" in public_methods
        assert "get_status" in public_methods


class TestFullFlowWithLiveFAM:
    """End-to-end flow tests with live FAM integration."""

    def test_complete_pqn_flow_emits_to_fam(
        self,
        live_fam_adapter,
        temp_fam_daemon,
        pqn_services,
    ):
        """Complete PQN flow emits both contribution and verification to FAM."""
        registry = pqn_services["registry"]
        sink = pqn_services["sink"]
        engine = pqn_services["engine"]
        reporter = pqn_services["reporter"]

        # Execute flow
        work_unit = registry.register(
            description="Full flow test",
            config={"steps": 200},
            creator_id="flow_agent",
        )

        submission = sink.submit(
            work_unit_id=work_unit.work_unit_id,
            submitter_id="flow_agent",
            metrics={"coherence": 0.88},
        )

        decision = engine.manual_verify(
            submission_id=submission.submission_id,
            decision="accept",
            verifier_id="flow_verifier",
            rationale="Full flow test passes",
        )

        # Emit verification event
        live_fam_adapter.emit_verification_event(
            decision=decision,
            work_unit_id=work_unit.work_unit_id,
            actor_id="pqn_swarm_hub",
        )

        contribution = reporter.record(
            work_unit_id=work_unit.work_unit_id,
            submission_id=submission.submission_id,
            decision_id=decision.decision_id,
            contributor_id="flow_agent",
            score=0.95,
        )

        # Emit contribution event
        live_fam_adapter.emit_contribution_event(
            contribution=contribution,
            actor_id="pqn_swarm_hub",
        )

        # Verify both events in FAM store
        verification_events = temp_fam_daemon.query_events(
            event_type="pqn_verification_recorded",
        )
        contribution_events = temp_fam_daemon.query_events(
            event_type="pqn_contribution_recorded",
        )

        assert len(verification_events) == 1
        assert len(contribution_events) == 1

        # Verify they reference the same work unit
        assert verification_events[0].task_id == work_unit.work_unit_id
        assert contribution_events[0].task_id == work_unit.work_unit_id

    def test_multiple_contributions_create_distinct_events(
        self,
        live_fam_adapter,
        temp_fam_daemon,
        pqn_services,
    ):
        """Multiple contributions create distinct events with unique dedupe keys."""
        registry = pqn_services["registry"]
        sink = pqn_services["sink"]
        engine = pqn_services["engine"]
        reporter = pqn_services["reporter"]

        contributions = []

        for i in range(3):
            work_unit = registry.register(
                description=f"Multi-contribution test {i}",
                config={"n": i},
                creator_id=f"agent_{i}",
            )

            submission = sink.submit(
                work_unit_id=work_unit.work_unit_id,
                submitter_id=f"agent_{i}",
                metrics={"coherence": 0.7 + i * 0.1},
            )

            decision = engine.manual_verify(
                submission_id=submission.submission_id,
                decision="accept",
                verifier_id="verifier",
                rationale="OK",
            )

            contribution = reporter.record(
                work_unit_id=work_unit.work_unit_id,
                submission_id=submission.submission_id,
                decision_id=decision.decision_id,
                contributor_id=f"agent_{i}",
                score=0.8 + i * 0.05,
            )

            success, _ = live_fam_adapter.emit_contribution_event(contribution)
            assert success is True
            contributions.append(contribution)

        # Verify all 3 events in FAM store
        events = temp_fam_daemon.query_events(
            event_type="pqn_contribution_recorded",
        )

        assert len(events) == 3

        # Verify distinct contribution IDs
        event_contribution_ids = {e.payload["contribution_id"] for e in events}
        expected_ids = {c.contribution_id for c in contributions}
        assert event_contribution_ids == expected_ids


class TestFAMStoreStats:
    """Tests for verifying FAM store statistics after live emission."""

    def test_stats_reflect_emitted_events(
        self,
        live_fam_adapter,
        temp_fam_daemon,
        sample_contribution,
        sample_verification,
    ):
        """FAM store stats correctly reflect emitted PQN events."""
        decision, work_unit_id = sample_verification

        # Emit both event types
        live_fam_adapter.emit_contribution_event(sample_contribution)
        live_fam_adapter.emit_verification_event(decision, work_unit_id)

        # Get stats
        stats = temp_fam_daemon.get_status()["event_store_stats"]

        assert stats["total_events"] >= 2
        assert "pqn_contribution_recorded" in stats["events_by_type"]
        assert "pqn_verification_recorded" in stats["events_by_type"]
        assert stats["events_by_type"]["pqn_contribution_recorded"] >= 1
        assert stats["events_by_type"]["pqn_verification_recorded"] >= 1

    def test_parity_check_passes_after_emission(
        self,
        live_fam_adapter,
        temp_fam_daemon,
        sample_contribution,
    ):
        """FAM store parity check passes after live emission."""
        live_fam_adapter.emit_contribution_event(sample_contribution)

        health = temp_fam_daemon.get_health()

        assert health.parity_ok is True
        assert "events" in health.parity_message
