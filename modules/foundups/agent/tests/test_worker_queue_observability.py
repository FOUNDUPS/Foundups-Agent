#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Worker Queue Observability Tests

Tests for worker queue observability event scaffolding per WSP 91.

WSP 97 TRUTH BOUNDARIES:
  - All events are observability only
  - No real processes are represented
  - No CABR/reward/payout/token fields

Test Coverage:
  1. emit_event stores append-only event
  2. emit_heartbeat creates heartbeat event
  3. emit_lease_expired creates lease expiry signal
  4. worker availability/unavailability events are recorded
  5. snapshot_queue_health reports queued/dequeued/completed/expired counts
  6. get_events filters by worker_id
  7. event fields preserve evidence_refs
  8. all observability is in-memory only
  9. no real worker/process fields imply execution
  10. no CABR/reward/payout/token fields exist

WSP References: WSP 11, WSP 50, WSP 91, WSP 97.
"""

from __future__ import annotations

import pytest

from modules.foundups.agent.src.worker_queue_observability import (
    LeaseExpirySignal,
    QueueHealthSnapshot,
    QueueHealthStatus,
    WorkerAvailabilitySnapshot,
    WorkerAvailabilityStatus,
    WorkerHeartbeatSnapshot,
    WorkerQueueEvent,
    WorkerQueueEventType,
    WorkerQueueObservability,
    create_worker_queue_observability,
)

from modules.foundups.agent.src.build_plan_swarm_queue import (
    QueueEntryStatus,
    QueuePriority,
    SwarmWorkerQueue,
    create_swarm_worker_queue,
)

from modules.foundups.agent.src.build_plan_swarm import (
    StepAssignment,
)

from modules.foundups.agent.src.build_plan import (
    BuildStepAction,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def observability() -> WorkerQueueObservability:
    """Create a WorkerQueueObservability instance."""
    return create_worker_queue_observability()


@pytest.fixture
def queue() -> SwarmWorkerQueue:
    """Create a SwarmWorkerQueue instance."""
    return create_swarm_worker_queue()


@pytest.fixture
def sample_assignment() -> StepAssignment:
    """Create a sample StepAssignment."""
    return StepAssignment(
        assignment_id="assign_obs_001",
        step_id="step_validate_001",
        worker_id="obs_worker_001",
        owned_files=["modules/test/README.md"],
    )


# ---------------------------------------------------------------------------
# Test: emit_event stores append-only event
# ---------------------------------------------------------------------------


class TestEmitEvent:
    """Test emit_event functionality."""

    def test_emit_event_stores_event(
        self, observability: WorkerQueueObservability
    ) -> None:
        """emit_event stores event in append-only list."""
        event = WorkerQueueEvent(
            event_id="evt_test_001",
            event_type=WorkerQueueEventType.HEARTBEAT,
            worker_id="worker_001",
        )

        result = observability.emit_event(event)

        assert result.event_id == "evt_test_001"
        assert len(observability.get_events()) == 1
        assert observability.get_events()[0].event_id == "evt_test_001"

    def test_emit_event_is_append_only(
        self, observability: WorkerQueueObservability
    ) -> None:
        """Events are append-only."""
        event1 = WorkerQueueEvent(
            event_id="evt_001",
            event_type=WorkerQueueEventType.HEARTBEAT,
        )
        event2 = WorkerQueueEvent(
            event_id="evt_002",
            event_type=WorkerQueueEventType.LEASE_EXPIRED,
        )

        observability.emit_event(event1)
        observability.emit_event(event2)

        events = observability.get_events()
        assert len(events) == 2
        assert events[0].event_id == "evt_001"
        assert events[1].event_id == "evt_002"

    def test_emit_event_preserves_all_fields(
        self, observability: WorkerQueueObservability
    ) -> None:
        """All event fields are preserved."""
        event = WorkerQueueEvent(
            event_id="evt_full_001",
            event_type=WorkerQueueEventType.ASSIGNMENT_COMPLETED,
            worker_id="worker_full",
            entry_id="entry_full",
            evidence_refs=["evidence/ref1", "evidence/ref2"],
            payload={"custom_key": "custom_value"},
        )

        observability.emit_event(event)
        stored = observability.get_events()[0]

        assert stored.worker_id == "worker_full"
        assert stored.entry_id == "entry_full"
        assert len(stored.evidence_refs) == 2
        assert "evidence/ref1" in stored.evidence_refs
        assert stored.payload["custom_key"] == "custom_value"


# ---------------------------------------------------------------------------
# Test: emit_heartbeat creates heartbeat event
# ---------------------------------------------------------------------------


class TestEmitHeartbeat:
    """Test emit_heartbeat functionality."""

    def test_emit_heartbeat_creates_event(
        self, observability: WorkerQueueObservability
    ) -> None:
        """emit_heartbeat creates heartbeat event."""
        event = observability.emit_heartbeat(
            worker_id="hb_worker_001",
            entry_id="hb_entry_001",
        )

        assert event.event_type == WorkerQueueEventType.HEARTBEAT
        assert event.worker_id == "hb_worker_001"
        assert event.entry_id == "hb_entry_001"
        assert event.event_id.startswith("evt_")

    def test_emit_heartbeat_tracks_consecutive(
        self, observability: WorkerQueueObservability
    ) -> None:
        """Consecutive heartbeats are tracked."""
        worker_id = "consecutive_worker"

        observability.emit_heartbeat(worker_id)
        observability.emit_heartbeat(worker_id)
        observability.emit_heartbeat(worker_id)

        snapshot = observability.get_heartbeat_snapshot(worker_id)
        assert snapshot is not None
        assert snapshot.consecutive_heartbeats == 3

    def test_emit_heartbeat_without_entry(
        self, observability: WorkerQueueObservability
    ) -> None:
        """Heartbeat without entry_id is valid."""
        event = observability.emit_heartbeat(worker_id="idle_worker")

        assert event.entry_id is None
        assert event.worker_id == "idle_worker"


# ---------------------------------------------------------------------------
# Test: emit_lease_expired creates lease expiry signal
# ---------------------------------------------------------------------------


class TestEmitLeaseExpired:
    """Test emit_lease_expired functionality."""

    def test_emit_lease_expired_creates_event(
        self, observability: WorkerQueueObservability
    ) -> None:
        """emit_lease_expired creates lease expiry event."""
        event = observability.emit_lease_expired(
            entry_id="expired_entry_001",
            worker_id="expired_worker_001",
            reason="Lease timeout",
        )

        assert event.event_type == WorkerQueueEventType.LEASE_EXPIRED
        assert event.entry_id == "expired_entry_001"
        assert event.worker_id == "expired_worker_001"

        # Payload contains LeaseExpirySignal data
        assert event.payload["reason"] == "Lease timeout"
        assert event.payload["entry_id"] == "expired_entry_001"

    def test_lease_expiry_signal_serialization(self) -> None:
        """LeaseExpirySignal serializes correctly."""
        signal = LeaseExpirySignal(
            entry_id="sig_entry_001",
            worker_id="sig_worker_001",
            reason="Test reason",
            was_requeued=True,
            retry_count=2,
        )

        data = signal.to_dict()

        assert data["entry_id"] == "sig_entry_001"
        assert data["worker_id"] == "sig_worker_001"
        assert data["reason"] == "Test reason"
        assert data["was_requeued"] is True
        assert data["retry_count"] == 2


# ---------------------------------------------------------------------------
# Test: Worker availability events
# ---------------------------------------------------------------------------


class TestWorkerAvailabilityEvents:
    """Test worker availability/unavailability events."""

    def test_emit_worker_available(
        self, observability: WorkerQueueObservability
    ) -> None:
        """emit_worker_available creates availability event."""
        event = observability.emit_worker_available(
            worker_id="avail_worker_001",
            capabilities=["validate", "build"],
        )

        assert event.event_type == WorkerQueueEventType.WORKER_AVAILABLE
        assert event.worker_id == "avail_worker_001"
        assert event.payload["status"] == WorkerAvailabilityStatus.AVAILABLE.value
        assert "validate" in event.payload["capabilities"]
        assert "build" in event.payload["capabilities"]

    def test_emit_worker_unavailable(
        self, observability: WorkerQueueObservability
    ) -> None:
        """emit_worker_unavailable creates unavailability event."""
        event = observability.emit_worker_unavailable(
            worker_id="unavail_worker_001",
            reason="Connection lost",
        )

        assert event.event_type == WorkerQueueEventType.WORKER_UNAVAILABLE
        assert event.worker_id == "unavail_worker_001"
        assert event.payload["reason"] == "Connection lost"
        assert event.payload["status"] == WorkerAvailabilityStatus.OFFLINE.value

    def test_availability_snapshot_serialization(self) -> None:
        """WorkerAvailabilitySnapshot serializes correctly."""
        snapshot = WorkerAvailabilitySnapshot(
            worker_id="snap_worker_001",
            status=WorkerAvailabilityStatus.BUSY,
            capabilities=["test"],
            current_assignment_id="assign_001",
        )

        data = snapshot.to_dict()

        assert data["worker_id"] == "snap_worker_001"
        assert data["status"] == "busy"
        assert data["current_assignment_id"] == "assign_001"


# ---------------------------------------------------------------------------
# Test: snapshot_queue_health reports counts
# ---------------------------------------------------------------------------


class TestSnapshotQueueHealth:
    """Test snapshot_queue_health functionality."""

    def test_snapshot_empty_queue(
        self,
        observability: WorkerQueueObservability,
        queue: SwarmWorkerQueue,
    ) -> None:
        """Snapshot of empty queue reports zeros."""
        snapshot = observability.snapshot_queue_health(queue)

        assert snapshot.total_queued == 0
        assert snapshot.total_processing == 0
        assert snapshot.total_completed == 0
        assert snapshot.total_failed == 0
        assert snapshot.total_expired == 0
        assert snapshot.status == QueueHealthStatus.HEALTHY

    def test_snapshot_with_queued_entries(
        self,
        observability: WorkerQueueObservability,
        queue: SwarmWorkerQueue,
        sample_assignment: StepAssignment,
    ) -> None:
        """Snapshot reports queued entry counts."""
        # Enqueue some entries
        queue.enqueue_assignment(
            assignment=sample_assignment,
            step_action=BuildStepAction.VALIDATE_GENESIS,
        )

        snapshot = observability.snapshot_queue_health(queue)

        assert snapshot.total_queued == 1
        assert snapshot.oldest_queued_seconds is not None
        assert snapshot.oldest_queued_seconds >= 0

    def test_snapshot_health_status_degraded(
        self,
        observability: WorkerQueueObservability,
        queue: SwarmWorkerQueue,
    ) -> None:
        """Queue with failed entries is DEGRADED."""
        # Create a mock entry directly (simulating failed state)
        from modules.foundups.agent.src.build_plan_swarm_queue import (
            SwarmWorkerQueueEntry,
        )

        failed_entry = SwarmWorkerQueueEntry(
            entry_id="failed_001",
            assignment_id="assign_failed",
            step_id="step_failed",
            step_action=BuildStepAction.RUN_TESTS,
            required_capability="test",
            status=QueueEntryStatus.FAILED,
        )
        queue._entries[failed_entry.entry_id] = failed_entry

        snapshot = observability.snapshot_queue_health(queue)

        assert snapshot.total_failed == 1
        assert snapshot.status == QueueHealthStatus.DEGRADED

    def test_snapshot_serialization(
        self,
        observability: WorkerQueueObservability,
        queue: SwarmWorkerQueue,
    ) -> None:
        """QueueHealthSnapshot serializes correctly."""
        snapshot = observability.snapshot_queue_health(queue)
        data = snapshot.to_dict()

        assert "status" in data
        assert "total_queued" in data
        assert "total_processing" in data
        assert "total_completed" in data
        assert "total_failed" in data
        assert "total_expired" in data
        assert "snapshot_at" in data


# ---------------------------------------------------------------------------
# Test: get_events filters by worker_id
# ---------------------------------------------------------------------------


class TestGetEventsFiltering:
    """Test get_events filtering functionality."""

    def test_get_events_all(
        self, observability: WorkerQueueObservability
    ) -> None:
        """get_events() without filter returns all events."""
        observability.emit_heartbeat("worker_a")
        observability.emit_heartbeat("worker_b")
        observability.emit_heartbeat("worker_c")

        events = observability.get_events()

        assert len(events) == 3

    def test_get_events_by_worker_id(
        self, observability: WorkerQueueObservability
    ) -> None:
        """get_events(worker_id) filters correctly."""
        observability.emit_heartbeat("filter_worker_001")
        observability.emit_heartbeat("filter_worker_002")
        observability.emit_heartbeat("filter_worker_001")
        observability.emit_heartbeat("filter_worker_003")

        events = observability.get_events(worker_id="filter_worker_001")

        assert len(events) == 2
        assert all(e.worker_id == "filter_worker_001" for e in events)

    def test_get_events_no_match(
        self, observability: WorkerQueueObservability
    ) -> None:
        """get_events with no matching worker returns empty list."""
        observability.emit_heartbeat("existing_worker")

        events = observability.get_events(worker_id="nonexistent_worker")

        assert len(events) == 0


# ---------------------------------------------------------------------------
# Test: Evidence refs preservation
# ---------------------------------------------------------------------------


class TestEvidenceRefsPreservation:
    """Test that evidence_refs are preserved in events."""

    def test_event_preserves_evidence_refs(
        self, observability: WorkerQueueObservability
    ) -> None:
        """Event evidence_refs are preserved."""
        evidence = [
            "evidence/queue/heartbeat_001",
            "evidence/queue/lease_renewal",
        ]

        event = WorkerQueueEvent(
            event_id="evt_evidence_001",
            event_type=WorkerQueueEventType.ASSIGNMENT_COMPLETED,
            evidence_refs=evidence,
        )

        observability.emit_event(event)
        stored = observability.get_events()[0]

        assert len(stored.evidence_refs) == 2
        assert "evidence/queue/heartbeat_001" in stored.evidence_refs
        assert "evidence/queue/lease_renewal" in stored.evidence_refs

    def test_to_dict_includes_evidence_refs(
        self, observability: WorkerQueueObservability
    ) -> None:
        """Event serialization includes evidence_refs."""
        event = WorkerQueueEvent(
            event_id="evt_serial_001",
            event_type=WorkerQueueEventType.HEARTBEAT,
            evidence_refs=["ref1", "ref2"],
        )

        data = event.to_dict()

        assert "evidence_refs" in data
        assert len(data["evidence_refs"]) == 2


# ---------------------------------------------------------------------------
# Test: In-memory only observability
# ---------------------------------------------------------------------------


class TestInMemoryObservability:
    """Test that observability is in-memory only."""

    def test_observability_is_in_memory(
        self, observability: WorkerQueueObservability
    ) -> None:
        """Events are stored in memory only."""
        observability.emit_heartbeat("memory_worker")

        # Check internal state
        assert len(observability._events) == 1
        assert len(observability._worker_heartbeats) == 1

    def test_clear_events_removes_all(
        self, observability: WorkerQueueObservability
    ) -> None:
        """clear_events removes all events."""
        observability.emit_heartbeat("clear_worker_1")
        observability.emit_heartbeat("clear_worker_2")
        observability.emit_heartbeat("clear_worker_3")

        cleared = observability.clear_events()

        assert cleared == 3
        assert len(observability.get_events()) == 0
        assert len(observability._worker_heartbeats) == 0


# ---------------------------------------------------------------------------
# Test: No real execution fields
# ---------------------------------------------------------------------------


class TestNoRealExecutionFields:
    """Test that no real execution fields exist."""

    def test_event_has_no_real_execution_fields(self) -> None:
        """WorkerQueueEvent has no real_execution_performed field."""
        event = WorkerQueueEvent(
            event_id="evt_noexec_001",
            event_type=WorkerQueueEventType.HEARTBEAT,
        )

        assert not hasattr(event, "real_execution_performed")
        assert not hasattr(event, "real_process_started")

        data = event.to_dict()
        assert "real_execution_performed" not in data
        assert "real_process_started" not in data

    def test_snapshot_has_no_real_execution_fields(self) -> None:
        """Snapshots have no real execution fields."""
        heartbeat = WorkerHeartbeatSnapshot(worker_id="snap_worker")
        availability = WorkerAvailabilitySnapshot(
            worker_id="avail_worker",
            status=WorkerAvailabilityStatus.AVAILABLE,
        )
        health = QueueHealthSnapshot(status=QueueHealthStatus.HEALTHY)

        for snapshot in [heartbeat, availability, health]:
            assert not hasattr(snapshot, "real_execution_performed")
            data = snapshot.to_dict()
            assert "real_execution_performed" not in data


# ---------------------------------------------------------------------------
# Test: No CABR/reward/payout/token fields
# ---------------------------------------------------------------------------


class TestNoCABRFields:
    """Test that no CABR/reward/payout/token fields exist."""

    def test_event_has_no_cabr_fields(self) -> None:
        """WorkerQueueEvent has no CABR/payout fields."""
        event = WorkerQueueEvent(
            event_id="evt_nocabr_001",
            event_type=WorkerQueueEventType.ASSIGNMENT_COMPLETED,
        )

        data = event.to_dict()

        assert "cabr_ready" not in data
        assert "payout_ready" not in data
        assert "reward" not in data
        assert "tokens" not in data
        assert "payout_amount" not in data

    def test_snapshot_has_no_cabr_fields(self) -> None:
        """Snapshots have no CABR/payout fields."""
        health = QueueHealthSnapshot(status=QueueHealthStatus.HEALTHY)

        data = health.to_dict()

        assert "cabr_ready" not in data
        assert "payout_ready" not in data
        assert "reward" not in data
        assert "tokens" not in data

    def test_heartbeat_snapshot_has_no_cabr_fields(self) -> None:
        """WorkerHeartbeatSnapshot has no CABR/payout fields."""
        snapshot = WorkerHeartbeatSnapshot(worker_id="hb_nocabr")

        data = snapshot.to_dict()

        assert "cabr_ready" not in data
        assert "payout_ready" not in data
        assert "reward" not in data
        assert "tokens" not in data


# ---------------------------------------------------------------------------
# Test: Factory function
# ---------------------------------------------------------------------------


class TestFactoryFunction:
    """Test factory function."""

    def test_create_worker_queue_observability(self) -> None:
        """Factory creates valid instance."""
        obs = create_worker_queue_observability()

        assert isinstance(obs, WorkerQueueObservability)
        assert len(obs.get_events()) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
