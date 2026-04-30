#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Worker Queue Observability — Event Scaffolding for Queue Telemetry

Implements observability/status event scaffolding for SwarmWorkerQueue
and worker assignment flow per WSP 91 (DAEMON Observability Protocol).

This is observability scaffold only.
- Events are in-memory only (Phase 1)
- Events are append-only
- No external telemetry sink yet
- No RedDog/pfMALL event emission yet
- No real worker process starts

WSP 91 Three Pillars:
  - Logs: Event emission with timestamps
  - Traces: Not implemented (Phase 2)
  - Metrics: Snapshot methods for aggregated state

WSP 97 TRUTH BOUNDARIES:
  - All events are observability only
  - No real processes are represented
  - No files are edited
  - No CABR/reward/payout/token fields
  - real_execution_performed does not exist

WSP Compliance:
  WSP 11  : Interface contract (typed API)
  WSP 50  : Pre-action validation (event validation)
  WSP 91  : DAEMON Observability Protocol
  WSP 97  : Truth boundaries (no execution claims)

NAVIGATION:
  -> Uses: build_plan_swarm_queue.py (SwarmWorkerQueue, QueueEntryStatus)
  -> Spec: WSP_framework/src/WSP_91_DAEMON_Observability_Protocol.md
  -> Called by: Future WRE observability integration
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("worker_queue_observability")


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WorkerQueueEventType(str, Enum):
    """Types of worker queue events."""

    HEARTBEAT = "heartbeat"
    """Worker sent heartbeat."""

    LEASE_EXPIRED = "lease_expired"
    """Assignment lease expired."""

    WORKER_AVAILABLE = "worker_available"
    """Worker became available for assignments."""

    WORKER_UNAVAILABLE = "worker_unavailable"
    """Worker became unavailable."""

    ASSIGNMENT_ENQUEUED = "assignment_enqueued"
    """Assignment was enqueued."""

    ASSIGNMENT_DEQUEUED = "assignment_dequeued"
    """Assignment was dequeued by worker."""

    ASSIGNMENT_COMPLETED = "assignment_completed"
    """Assignment was completed."""

    QUEUE_STATUS_CHANGE = "queue_status_change"
    """Queue status changed."""


class WorkerAvailabilityStatus(str, Enum):
    """Worker availability status for telemetry."""

    AVAILABLE = "available"
    """Worker is available for new assignments."""

    BUSY = "busy"
    """Worker is processing an assignment."""

    OFFLINE = "offline"
    """Worker is not responding."""

    TERMINATED = "terminated"
    """Worker was deregistered."""


class QueueHealthStatus(str, Enum):
    """Queue health status for telemetry."""

    HEALTHY = "healthy"
    """Queue operating normally."""

    DEGRADED = "degraded"
    """Queue has pending issues (expired entries, etc.)."""

    UNHEALTHY = "unhealthy"
    """Queue has critical issues."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class WorkerQueueEvent:
    """
    Base event for worker queue observability.

    WSP 91: Implements Pillar 1 (Logs) - discrete events with timestamps.
    WSP 97: No execution claims, no CABR/payout fields.
    """

    event_id: str
    """Unique event identifier."""

    event_type: WorkerQueueEventType
    """Type of event."""

    created_at: datetime = field(default_factory=utc_now)
    """When event was created."""

    worker_id: Optional[str] = None
    """Worker involved in event (if applicable)."""

    entry_id: Optional[str] = None
    """Queue entry involved (if applicable)."""

    evidence_refs: List[str] = field(default_factory=list)
    """Evidence references (if applicable)."""

    payload: Dict[str, Any] = field(default_factory=dict)
    """Additional event payload."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "created_at": utc_iso(self.created_at),
            "worker_id": self.worker_id,
            "entry_id": self.entry_id,
            "evidence_refs": self.evidence_refs,
            "payload": self.payload,
        }


@dataclass
class WorkerHeartbeatSnapshot:
    """
    Snapshot of worker heartbeat state.

    WSP 91: Metrics pillar - aggregated measurements.
    """

    worker_id: str
    """Worker that sent heartbeat."""

    heartbeat_at: datetime = field(default_factory=utc_now)
    """When heartbeat was sent."""

    entry_id: Optional[str] = None
    """Entry being processed (if any)."""

    lease_remaining_seconds: Optional[int] = None
    """Seconds remaining on lease."""

    consecutive_heartbeats: int = 0
    """Consecutive heartbeats without failure."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "worker_id": self.worker_id,
            "heartbeat_at": utc_iso(self.heartbeat_at),
            "entry_id": self.entry_id,
            "lease_remaining_seconds": self.lease_remaining_seconds,
            "consecutive_heartbeats": self.consecutive_heartbeats,
        }


@dataclass
class LeaseExpirySignal:
    """
    Signal that a lease has expired.

    WSP 91: Logs pillar - lease lifecycle event.
    """

    entry_id: str
    """Queue entry whose lease expired."""

    worker_id: str
    """Worker that held the lease."""

    expired_at: datetime = field(default_factory=utc_now)
    """When expiration was detected."""

    reason: str = ""
    """Reason for expiration."""

    was_requeued: bool = False
    """True if entry was requeued for retry."""

    retry_count: int = 0
    """Current retry count."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "entry_id": self.entry_id,
            "worker_id": self.worker_id,
            "expired_at": utc_iso(self.expired_at),
            "reason": self.reason,
            "was_requeued": self.was_requeued,
            "retry_count": self.retry_count,
        }


@dataclass
class WorkerAvailabilitySnapshot:
    """
    Snapshot of worker availability state.

    WSP 91: Metrics pillar - worker health telemetry.
    """

    worker_id: str
    """Worker identifier."""

    status: WorkerAvailabilityStatus
    """Availability status."""

    capabilities: List[str] = field(default_factory=list)
    """Worker capabilities."""

    last_heartbeat_at: Optional[datetime] = None
    """Last heartbeat timestamp."""

    current_assignment_id: Optional[str] = None
    """Current assignment (if busy)."""

    snapshot_at: datetime = field(default_factory=utc_now)
    """When snapshot was taken."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "worker_id": self.worker_id,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "last_heartbeat_at": utc_iso(self.last_heartbeat_at),
            "current_assignment_id": self.current_assignment_id,
            "snapshot_at": utc_iso(self.snapshot_at),
        }


@dataclass
class QueueHealthSnapshot:
    """
    Snapshot of queue health state.

    WSP 91: Metrics pillar - queue health telemetry.
    """

    status: QueueHealthStatus
    """Overall queue health status."""

    total_queued: int = 0
    """Entries waiting for pickup."""

    total_processing: int = 0
    """Entries being processed."""

    total_completed: int = 0
    """Entries completed."""

    total_failed: int = 0
    """Entries failed."""

    total_expired: int = 0
    """Entries expired."""

    oldest_queued_seconds: Optional[int] = None
    """Age of oldest queued entry in seconds."""

    snapshot_at: datetime = field(default_factory=utc_now)
    """When snapshot was taken."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "status": self.status.value,
            "total_queued": self.total_queued,
            "total_processing": self.total_processing,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "total_expired": self.total_expired,
            "oldest_queued_seconds": self.oldest_queued_seconds,
            "snapshot_at": utc_iso(self.snapshot_at),
        }


# ---------------------------------------------------------------------------
# WorkerQueueObservability
# ---------------------------------------------------------------------------


class WorkerQueueObservability:
    """
    Observability system for SwarmWorkerQueue telemetry.

    Implements WSP 91 (DAEMON Observability Protocol) Pillar 1 (Logs)
    and basic Pillar 3 (Metrics) via snapshot methods.

    WSP 97 Truth Boundaries:
      - All events are observability only
      - No real processes are represented
      - No execution claims
      - No CABR/reward/payout fields
    """

    def __init__(self) -> None:
        """Initialize the observability system."""
        # In-memory event storage (Phase 1)
        self._events: List[WorkerQueueEvent] = []

        # Worker heartbeat tracking
        self._worker_heartbeats: Dict[str, WorkerHeartbeatSnapshot] = {}

    # ------------------------------------------------------------------
    # Event Emission
    # ------------------------------------------------------------------

    def emit_event(self, event: WorkerQueueEvent) -> WorkerQueueEvent:
        """
        Emit an observability event.

        Events are stored in-memory and append-only.

        Args:
            event: WorkerQueueEvent to emit.

        Returns:
            The emitted event.
        """
        self._events.append(event)

        logger.info(
            "[OBSERVABILITY] Event %s: %s (worker=%s, entry=%s)",
            event.event_id,
            event.event_type.value,
            event.worker_id,
            event.entry_id,
        )

        return event

    def emit_heartbeat(
        self,
        worker_id: str,
        entry_id: Optional[str] = None,
    ) -> WorkerQueueEvent:
        """
        Emit a heartbeat event for a worker.

        Args:
            worker_id: Worker sending heartbeat.
            entry_id: Entry being processed (optional).

        Returns:
            The emitted heartbeat event.
        """
        event_id = f"evt_{secrets.token_hex(6)}"

        event = WorkerQueueEvent(
            event_id=event_id,
            event_type=WorkerQueueEventType.HEARTBEAT,
            worker_id=worker_id,
            entry_id=entry_id,
            payload={"source": "worker_queue_observability"},
        )

        # Update heartbeat tracking
        existing = self._worker_heartbeats.get(worker_id)
        consecutive = (existing.consecutive_heartbeats + 1) if existing else 1

        self._worker_heartbeats[worker_id] = WorkerHeartbeatSnapshot(
            worker_id=worker_id,
            heartbeat_at=event.created_at,
            entry_id=entry_id,
            consecutive_heartbeats=consecutive,
        )

        return self.emit_event(event)

    def emit_lease_expired(
        self,
        entry_id: str,
        worker_id: str,
        reason: str,
    ) -> WorkerQueueEvent:
        """
        Emit a lease expiry event.

        Args:
            entry_id: Queue entry whose lease expired.
            worker_id: Worker that held the lease.
            reason: Reason for expiration.

        Returns:
            The emitted lease expiry event.
        """
        event_id = f"evt_{secrets.token_hex(6)}"

        signal = LeaseExpirySignal(
            entry_id=entry_id,
            worker_id=worker_id,
            reason=reason,
        )

        event = WorkerQueueEvent(
            event_id=event_id,
            event_type=WorkerQueueEventType.LEASE_EXPIRED,
            worker_id=worker_id,
            entry_id=entry_id,
            payload=signal.to_dict(),
        )

        return self.emit_event(event)

    def emit_worker_available(
        self,
        worker_id: str,
        capabilities: List[str],
    ) -> WorkerQueueEvent:
        """
        Emit a worker available event.

        Args:
            worker_id: Worker that became available.
            capabilities: Worker capabilities.

        Returns:
            The emitted availability event.
        """
        event_id = f"evt_{secrets.token_hex(6)}"

        snapshot = WorkerAvailabilitySnapshot(
            worker_id=worker_id,
            status=WorkerAvailabilityStatus.AVAILABLE,
            capabilities=capabilities,
        )

        event = WorkerQueueEvent(
            event_id=event_id,
            event_type=WorkerQueueEventType.WORKER_AVAILABLE,
            worker_id=worker_id,
            payload=snapshot.to_dict(),
        )

        return self.emit_event(event)

    def emit_worker_unavailable(
        self,
        worker_id: str,
        reason: str,
    ) -> WorkerQueueEvent:
        """
        Emit a worker unavailable event.

        Args:
            worker_id: Worker that became unavailable.
            reason: Reason for unavailability.

        Returns:
            The emitted unavailability event.
        """
        event_id = f"evt_{secrets.token_hex(6)}"

        event = WorkerQueueEvent(
            event_id=event_id,
            event_type=WorkerQueueEventType.WORKER_UNAVAILABLE,
            worker_id=worker_id,
            payload={
                "status": WorkerAvailabilityStatus.OFFLINE.value,
                "reason": reason,
            },
        )

        return self.emit_event(event)

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def snapshot_queue_health(
        self,
        queue: "SwarmWorkerQueue",  # noqa: F821
    ) -> QueueHealthSnapshot:
        """
        Take a health snapshot of the queue.

        Args:
            queue: SwarmWorkerQueue to snapshot.

        Returns:
            QueueHealthSnapshot with current state.
        """
        # Import here to avoid circular import
        from .build_plan_swarm_queue import QueueEntryStatus

        counts = queue.count_by_status()

        total_queued = counts.get(QueueEntryStatus.QUEUED, 0)
        total_processing = counts.get(QueueEntryStatus.PROCESSING, 0)
        total_completed = counts.get(QueueEntryStatus.COMPLETED, 0)
        total_failed = counts.get(QueueEntryStatus.FAILED, 0)
        total_expired = counts.get(QueueEntryStatus.EXPIRED, 0)

        # Calculate oldest queued entry age
        queued_entries = queue.list_entries(status=QueueEntryStatus.QUEUED)
        oldest_queued_seconds = None
        if queued_entries:
            now = utc_now()
            oldest = min(e.queued_at for e in queued_entries)
            oldest_queued_seconds = int((now - oldest).total_seconds())

        # Determine health status
        if total_failed > 0 or total_expired > 0:
            status = QueueHealthStatus.DEGRADED
        elif total_processing > 10 or (oldest_queued_seconds and oldest_queued_seconds > 300):
            status = QueueHealthStatus.DEGRADED
        else:
            status = QueueHealthStatus.HEALTHY

        return QueueHealthSnapshot(
            status=status,
            total_queued=total_queued,
            total_processing=total_processing,
            total_completed=total_completed,
            total_failed=total_failed,
            total_expired=total_expired,
            oldest_queued_seconds=oldest_queued_seconds,
        )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_events(
        self,
        worker_id: Optional[str] = None,
    ) -> List[WorkerQueueEvent]:
        """
        Get events, optionally filtered by worker_id.

        Args:
            worker_id: Filter by worker ID (optional).

        Returns:
            List of matching events.
        """
        if worker_id is None:
            return list(self._events)

        return [e for e in self._events if e.worker_id == worker_id]

    def get_heartbeat_snapshot(
        self,
        worker_id: str,
    ) -> Optional[WorkerHeartbeatSnapshot]:
        """Get latest heartbeat snapshot for a worker."""
        return self._worker_heartbeats.get(worker_id)

    def clear_events(self) -> int:
        """
        Clear all events (for testing/cleanup).

        Returns:
            Number of events cleared.
        """
        count = len(self._events)
        self._events.clear()
        self._worker_heartbeats.clear()
        return count


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def create_worker_queue_observability() -> WorkerQueueObservability:
    """
    Create a WorkerQueueObservability instance.

    Returns:
        WorkerQueueObservability instance.
    """
    return WorkerQueueObservability()
