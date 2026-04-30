#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BuildPlan Swarm WRE Queue — Worker Assignment Queue Scaffold

Implements the SwarmWorkerQueue interface from BUILD_PLAN_SWARM_WRE_QUEUE_CONTRACT.md.
This is a scaffold only. No real WRE queue integration is implemented.

WSP 97 TRUTH BOUNDARIES:
  - Queue entries are simulated only
  - No real worker process dequeue
  - No files are edited
  - No CABR/reward/payout/token fields
  - real_execution_performed does not exist (cannot become True)

Architecture:
  StepAssignment (from SwarmCoordinator)
      │
      ▼
  SwarmWorkerQueue.enqueue_assignment()
      │
      ▼
  SwarmWorkerQueueEntry (QUEUED)
      │
      ├─> dequeue_for_worker() ─> WorkerDequeueResult
      ├─> heartbeat() ─> renew lease
      ├─> complete_assignment() ─> Entry COMPLETED
      └─> expire_entries() ─> requeue or EXPIRED

WSP Compliance:
  WSP 11  : Interface contract (typed API)
  WSP 50  : Pre-action validation (capability matching)
  WSP 77  : Agent coordination (queue model)
  WSP 97  : Truth boundaries (simulation only)

NAVIGATION:
  -> Spec: modules/foundups/docs/BUILD_PLAN_SWARM_WRE_QUEUE_CONTRACT.md
  -> Uses: build_plan_swarm.py (StepAssignment)
  -> Uses: build_plan.py (BuildStepAction)
  -> Called by: Future WRE queue integration (not implemented)
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .build_plan import BuildStepAction
from .build_plan_swarm import StepAssignment

logger = logging.getLogger("build_plan_swarm_queue")


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_LEASE_DURATION_SECONDS = 300  # 5 minutes
DEFAULT_MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class QueuePriority(str, Enum):
    """Queue entry priority levels."""

    CRITICAL = "critical"
    """Must process immediately."""

    HIGH = "high"
    """Process before normal."""

    NORMAL = "normal"
    """Default priority."""

    LOW = "low"
    """Process when idle."""


class QueueEntryStatus(str, Enum):
    """Queue entry lifecycle status."""

    QUEUED = "queued"
    """Waiting for worker pickup."""

    PROCESSING = "processing"
    """Worker has dequeued and is processing."""

    COMPLETED = "completed"
    """Successfully completed."""

    FAILED = "failed"
    """Failed after max retries."""

    EXPIRED = "expired"
    """Lease expired, not retried."""


class DequeueDecision(str, Enum):
    """Dequeue operation result decision."""

    ASSIGNED = "assigned"
    """Entry assigned to worker."""

    NO_MATCH = "no_match"
    """No entry matches worker capabilities."""

    QUEUE_EMPTY = "queue_empty"
    """No entries in queue."""

    BLOCKED = "blocked"
    """Worker blocked from dequeue."""


class CompletionStatus(str, Enum):
    """Assignment completion status."""

    SUCCEEDED = "succeeded"
    """Assignment completed successfully."""

    FAILED = "failed"
    """Assignment failed."""

    SKIPPED = "skipped"
    """Assignment skipped (optional step)."""


# ---------------------------------------------------------------------------
# Capability Mapping
# ---------------------------------------------------------------------------

# Map step actions to required capabilities
ACTION_CAPABILITY_MAP: Dict[BuildStepAction, str] = {
    BuildStepAction.VALIDATE_GENESIS: "validate",
    BuildStepAction.VALIDATE_MANIFEST: "validate",
    BuildStepAction.VALIDATE_STRUCTURE: "validate",
    BuildStepAction.CREATE_SPEC: "build",
    BuildStepAction.CREATE_TEST: "build",
    BuildStepAction.CREATE_MODULE: "build",
    BuildStepAction.CREATE_ADAPTERS: "build",
    BuildStepAction.UPDATE_MANIFEST: "build",
    BuildStepAction.UPDATE_MODLOG: "build",
    BuildStepAction.UPDATE_TESTMODLOG: "build",
    BuildStepAction.RUN_TESTS: "test",
    BuildStepAction.DRY_RUN_BUILD: "build",
    BuildStepAction.SUBMIT_RECEIPT: "validate",
    BuildStepAction.REQUEST_APPROVAL: "validate",
    BuildStepAction.ARCHIVE_BUILD: "build",
}


def get_required_capability(action: BuildStepAction) -> str:
    """Get required capability for a step action."""
    return ACTION_CAPABILITY_MAP.get(action, "all")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SwarmWorkerQueueEntry:
    """Queue entry for a step assignment."""

    entry_id: str
    """Unique queue entry identifier."""

    assignment_id: str
    """Source StepAssignment ID."""

    step_id: str
    """BuildStep being assigned."""

    step_action: BuildStepAction
    """Step action enum for capability matching."""

    required_capability: str
    """Capability needed to process this entry."""

    priority: QueuePriority = QueuePriority.NORMAL
    """Entry priority."""

    status: QueueEntryStatus = QueueEntryStatus.QUEUED
    """Entry lifecycle status."""

    worker_id: Optional[str] = None
    """Worker processing this entry (if any)."""

    owned_files: List[str] = field(default_factory=list)
    """Files claimed by this assignment."""

    queued_at: datetime = field(default_factory=utc_now)
    """When entry was queued."""

    processing_started_at: Optional[datetime] = None
    """When worker started processing."""

    completed_at: Optional[datetime] = None
    """When entry was completed."""

    lease_expires_at: Optional[datetime] = None
    """When processing lease expires."""

    retry_count: int = 0
    """Number of times entry was requeued."""

    max_retries: int = DEFAULT_MAX_RETRIES
    """Maximum retry attempts."""

    evidence_refs: List[str] = field(default_factory=list)
    """Evidence from completion."""

    error_message: Optional[str] = None
    """Error message if failed."""

    simulated: bool = True
    """WSP 97: Always True in scaffold."""

    def __post_init__(self) -> None:
        """Enforce WSP 97: simulated is always True."""
        self.simulated = True

    def is_retriable(self) -> bool:
        """Check if entry can be retried."""
        return self.retry_count < self.max_retries

    def is_lease_expired(self, now: Optional[datetime] = None) -> bool:
        """Check if processing lease is expired."""
        if self.lease_expires_at is None:
            return False
        now = now or utc_now()
        return now >= self.lease_expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "entry_id": self.entry_id,
            "assignment_id": self.assignment_id,
            "step_id": self.step_id,
            "step_action": self.step_action.value,
            "required_capability": self.required_capability,
            "priority": self.priority.value,
            "status": self.status.value,
            "worker_id": self.worker_id,
            "owned_files": self.owned_files,
            "queued_at": utc_iso(self.queued_at),
            "processing_started_at": utc_iso(self.processing_started_at),
            "completed_at": utc_iso(self.completed_at),
            "lease_expires_at": utc_iso(self.lease_expires_at),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "evidence_refs": self.evidence_refs,
            "error_message": self.error_message,
            "simulated": self.simulated,
        }


@dataclass
class WorkerDequeueRequest:
    """Request to dequeue an assignment for a worker."""

    worker_id: str
    """Worker requesting assignment."""

    capabilities: List[str] = field(default_factory=list)
    """Worker capabilities."""

    max_entries: int = 1
    """Maximum entries to dequeue."""

    preferred_step_ids: List[str] = field(default_factory=list)
    """Preferred steps (optional)."""

    def has_capability(self, capability: str) -> bool:
        """Check if worker has a capability."""
        return capability in self.capabilities or "all" in self.capabilities


@dataclass
class WorkerDequeueResult:
    """Result of a dequeue operation."""

    success: bool
    """True if at least one entry was assigned."""

    decision: DequeueDecision
    """Dequeue decision."""

    entries: List[SwarmWorkerQueueEntry] = field(default_factory=list)
    """Entries assigned to worker."""

    lease_expires_at: Optional[datetime] = None
    """Lease expiration for assigned entries."""

    reason: str = ""
    """Human-readable reason."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "decision": self.decision.value,
            "entries": [e.to_dict() for e in self.entries],
            "lease_expires_at": utc_iso(self.lease_expires_at),
            "reason": self.reason,
        }


@dataclass
class WorkerHeartbeat:
    """Result of a heartbeat operation."""

    entry_id: str
    """Entry that received heartbeat."""

    worker_id: str
    """Worker sending heartbeat."""

    lease_renewed: bool
    """True if lease was renewed."""

    new_expires_at: Optional[datetime] = None
    """New lease expiration time."""

    heartbeat_at: datetime = field(default_factory=utc_now)
    """When heartbeat was received."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "entry_id": self.entry_id,
            "worker_id": self.worker_id,
            "lease_renewed": self.lease_renewed,
            "new_expires_at": utc_iso(self.new_expires_at),
            "heartbeat_at": utc_iso(self.heartbeat_at),
        }


@dataclass
class AssignmentCompletionReport:
    """Report of assignment completion."""

    entry_id: str
    """Queue entry being completed."""

    worker_id: str
    """Worker reporting completion."""

    status: CompletionStatus
    """Completion status."""

    evidence_refs: List[str] = field(default_factory=list)
    """Evidence from execution."""

    error_message: Optional[str] = None
    """Error message if failed."""

    completed_at: datetime = field(default_factory=utc_now)
    """When completion was reported."""

    simulated: bool = True
    """WSP 97: Always True in scaffold."""

    def __post_init__(self) -> None:
        """Enforce WSP 97: simulated is always True."""
        self.simulated = True


@dataclass
class QueueAssignmentResult:
    """Result of a queue assignment operation."""

    success: bool
    """True if operation succeeded."""

    entry_id: Optional[str] = None
    """Entry ID if applicable."""

    error_code: Optional[str] = None
    """Machine-readable error code."""

    error_message: Optional[str] = None
    """Human-readable error message."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "entry_id": self.entry_id,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


# ---------------------------------------------------------------------------
# SwarmWorkerQueue
# ---------------------------------------------------------------------------


class SwarmWorkerQueue:
    """
    Queue for swarm worker assignment dispatch.

    WSP 97 Truth Boundaries:
      - Queue entries are simulated only
      - No real worker process dequeue
      - No files are edited
      - No CABR/reward/payout fields
    """

    def __init__(self, lease_duration_seconds: int = DEFAULT_LEASE_DURATION_SECONDS):
        """
        Initialize the queue.

        Args:
            lease_duration_seconds: Default lease duration for processing.
        """
        self.lease_duration_seconds = lease_duration_seconds

        # In-memory queue storage (Phase 1)
        self._entries: Dict[str, SwarmWorkerQueueEntry] = {}

        # Priority ordering (lower index = higher priority)
        self._priority_order = [
            QueuePriority.CRITICAL,
            QueuePriority.HIGH,
            QueuePriority.NORMAL,
            QueuePriority.LOW,
        ]

    # ------------------------------------------------------------------
    # Enqueue
    # ------------------------------------------------------------------

    def enqueue_assignment(
        self,
        assignment: StepAssignment,
        priority: QueuePriority = QueuePriority.NORMAL,
        step_action: Optional[BuildStepAction] = None,
    ) -> QueueAssignmentResult:
        """
        Enqueue a step assignment for worker pickup.

        Args:
            assignment: StepAssignment from SwarmCoordinator.
            priority: Queue priority.
            step_action: Step action (for capability matching).

        Returns:
            QueueAssignmentResult with entry_id if successful.
        """
        # Generate entry ID
        entry_id = f"qe_{secrets.token_hex(6)}"

        # Determine required capability
        action = step_action or BuildStepAction.VALIDATE_GENESIS
        required_capability = get_required_capability(action)

        # Create queue entry
        entry = SwarmWorkerQueueEntry(
            entry_id=entry_id,
            assignment_id=assignment.assignment_id,
            step_id=assignment.step_id,
            step_action=action,
            required_capability=required_capability,
            priority=priority,
            status=QueueEntryStatus.QUEUED,
            owned_files=list(assignment.owned_files),
        )

        self._entries[entry_id] = entry

        logger.info(
            "[QUEUE] Enqueued entry %s for assignment %s (cap=%s, priority=%s)",
            entry_id,
            assignment.assignment_id,
            required_capability,
            priority.value,
        )

        return QueueAssignmentResult(
            success=True,
            entry_id=entry_id,
        )

    # ------------------------------------------------------------------
    # Dequeue
    # ------------------------------------------------------------------

    def dequeue_for_worker(
        self,
        request: WorkerDequeueRequest,
    ) -> WorkerDequeueResult:
        """
        Attempt to dequeue an assignment for a worker.

        Args:
            request: WorkerDequeueRequest with worker capabilities.

        Returns:
            WorkerDequeueResult with assigned entries or decision.
        """
        # Find matching queued entries
        queued_entries = [
            e for e in self._entries.values()
            if e.status == QueueEntryStatus.QUEUED
        ]

        if not queued_entries:
            return WorkerDequeueResult(
                success=False,
                decision=DequeueDecision.QUEUE_EMPTY,
                reason="No entries in queue",
            )

        # Filter by capability match
        matching = [
            e for e in queued_entries
            if request.has_capability(e.required_capability)
        ]

        if not matching:
            return WorkerDequeueResult(
                success=False,
                decision=DequeueDecision.NO_MATCH,
                reason=f"No entries match capabilities: {request.capabilities}",
            )

        # Sort by priority, then by queued_at
        def sort_key(entry: SwarmWorkerQueueEntry) -> tuple:
            priority_idx = (
                self._priority_order.index(entry.priority)
                if entry.priority in self._priority_order
                else len(self._priority_order)
            )
            return (priority_idx, entry.queued_at)

        matching.sort(key=sort_key)

        # Prefer specific steps if requested
        if request.preferred_step_ids:
            preferred = [e for e in matching if e.step_id in request.preferred_step_ids]
            if preferred:
                matching = preferred + [e for e in matching if e not in preferred]

        # Take up to max_entries
        to_assign = matching[:request.max_entries]

        # Assign to worker
        lease_expires = utc_now() + timedelta(seconds=self.lease_duration_seconds)

        for entry in to_assign:
            entry.status = QueueEntryStatus.PROCESSING
            entry.worker_id = request.worker_id
            entry.processing_started_at = utc_now()
            entry.lease_expires_at = lease_expires

        logger.info(
            "[QUEUE] Dequeued %d entries for worker %s",
            len(to_assign),
            request.worker_id,
        )

        return WorkerDequeueResult(
            success=True,
            decision=DequeueDecision.ASSIGNED,
            entries=to_assign,
            lease_expires_at=lease_expires,
            reason=f"Assigned {len(to_assign)} entries",
        )

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    def heartbeat(
        self,
        worker_id: str,
        entry_id: str,
    ) -> WorkerHeartbeat:
        """
        Send heartbeat to renew processing lease.

        Args:
            worker_id: Worker sending heartbeat.
            entry_id: Entry to renew.

        Returns:
            WorkerHeartbeat with renewal status.
        """
        entry = self._entries.get(entry_id)

        if not entry:
            return WorkerHeartbeat(
                entry_id=entry_id,
                worker_id=worker_id,
                lease_renewed=False,
            )

        if entry.worker_id != worker_id:
            return WorkerHeartbeat(
                entry_id=entry_id,
                worker_id=worker_id,
                lease_renewed=False,
            )

        if entry.status != QueueEntryStatus.PROCESSING:
            return WorkerHeartbeat(
                entry_id=entry_id,
                worker_id=worker_id,
                lease_renewed=False,
            )

        # Renew lease
        new_expires = utc_now() + timedelta(seconds=self.lease_duration_seconds)
        entry.lease_expires_at = new_expires

        logger.debug(
            "[QUEUE] Heartbeat for entry %s, lease renewed to %s",
            entry_id,
            new_expires.isoformat(),
        )

        return WorkerHeartbeat(
            entry_id=entry_id,
            worker_id=worker_id,
            lease_renewed=True,
            new_expires_at=new_expires,
        )

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------

    def complete_assignment(
        self,
        report: AssignmentCompletionReport,
    ) -> QueueAssignmentResult:
        """
        Report assignment completion with evidence.

        Args:
            report: AssignmentCompletionReport from worker.

        Returns:
            QueueAssignmentResult with success status.
        """
        entry = self._entries.get(report.entry_id)

        if not entry:
            return QueueAssignmentResult(
                success=False,
                error_code="ENTRY_NOT_FOUND",
                error_message=f"Entry {report.entry_id} not found",
            )

        if entry.worker_id != report.worker_id:
            return QueueAssignmentResult(
                success=False,
                entry_id=entry.entry_id,
                error_code="WORKER_MISMATCH",
                error_message=f"Worker {report.worker_id} does not own entry",
            )

        if entry.status != QueueEntryStatus.PROCESSING:
            return QueueAssignmentResult(
                success=False,
                entry_id=entry.entry_id,
                error_code="INVALID_STATUS",
                error_message=f"Entry status is {entry.status.value}, expected PROCESSING",
            )

        # Update entry
        if report.status == CompletionStatus.SUCCEEDED:
            entry.status = QueueEntryStatus.COMPLETED
        elif report.status == CompletionStatus.FAILED:
            entry.status = QueueEntryStatus.FAILED
            entry.error_message = report.error_message
        elif report.status == CompletionStatus.SKIPPED:
            entry.status = QueueEntryStatus.COMPLETED  # Skipped is still complete

        entry.completed_at = report.completed_at
        entry.evidence_refs.extend(report.evidence_refs)

        logger.info(
            "[QUEUE] Completed entry %s with status %s (evidence=%d)",
            entry.entry_id,
            report.status.value,
            len(report.evidence_refs),
        )

        return QueueAssignmentResult(
            success=True,
            entry_id=entry.entry_id,
        )

    # ------------------------------------------------------------------
    # Expiration
    # ------------------------------------------------------------------

    def expire_entries(self, now: Optional[datetime] = None) -> List[str]:
        """
        Expire stale entries and requeue if retriable.

        Args:
            now: Current time (for testing).

        Returns:
            List of expired entry IDs.
        """
        now = now or utc_now()
        expired_ids = []

        for entry in self._entries.values():
            if entry.status == QueueEntryStatus.PROCESSING and entry.is_lease_expired(now):
                if entry.is_retriable():
                    # Requeue
                    entry.retry_count += 1
                    entry.status = QueueEntryStatus.QUEUED
                    entry.worker_id = None
                    entry.processing_started_at = None
                    entry.lease_expires_at = None
                    logger.info(
                        "[QUEUE] Requeued entry %s (retry %d/%d)",
                        entry.entry_id,
                        entry.retry_count,
                        entry.max_retries,
                    )
                else:
                    # Expire
                    entry.status = QueueEntryStatus.EXPIRED
                    logger.info(
                        "[QUEUE] Expired entry %s (max retries exceeded)",
                        entry.entry_id,
                    )

                expired_ids.append(entry.entry_id)

        return expired_ids

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list_entries(
        self,
        status: Optional[QueueEntryStatus] = None,
    ) -> List[SwarmWorkerQueueEntry]:
        """
        List queue entries, optionally filtered by status.

        Args:
            status: Filter by status (optional).

        Returns:
            List of matching entries.
        """
        if status is None:
            return list(self._entries.values())

        return [e for e in self._entries.values() if e.status == status]

    def get_entry(self, entry_id: str) -> Optional[SwarmWorkerQueueEntry]:
        """Get a single entry by ID."""
        return self._entries.get(entry_id)

    def count_by_status(self) -> Dict[QueueEntryStatus, int]:
        """Count entries by status."""
        counts: Dict[QueueEntryStatus, int] = {}
        for entry in self._entries.values():
            counts[entry.status] = counts.get(entry.status, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def create_swarm_worker_queue() -> SwarmWorkerQueue:
    """
    Create a SwarmWorkerQueue instance.

    Returns:
        SwarmWorkerQueue instance.
    """
    return SwarmWorkerQueue()
