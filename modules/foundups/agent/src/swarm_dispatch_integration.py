#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Swarm Dispatch Integration — Queue-Dispatcher Coordination

Integrates SwarmWorkerQueue with AssignmentDispatcher for end-to-end
simulated worker assignment flow.

This is simulated integration only. No real worker processes are started.

WSP 97 TRUTH BOUNDARIES:
  - All dispatch is simulated only
  - No real processes are started
  - No Claude/OpenClaw/Hermes invocation
  - No files are edited
  - No CABR/reward/payout/token fields
  - real_execution_performed does not exist

Architecture:
  SwarmWorkerQueue
      │
      ├─> dequeue_for_worker()
      │       │
      │       ▼
      │   SwarmDispatchCoordinator.dispatch_next()
      │       │
      │       ▼
      │   AssignmentDispatcher.dispatch_assignment()
      │       │
      │       ▼
      │   (Simulated work)
      │       │
      │       ▼
      │   SwarmDispatchCoordinator.complete_dispatched_assignment()
      │       │
      │       ├─> AssignmentDispatcher.receive_completion()
      │       └─> SwarmWorkerQueue.complete_assignment()
      │
      └─> Evidence aggregation

WSP Compliance:
  WSP 11  : Interface contract (typed API)
  WSP 50  : Pre-action validation (capability matching)
  WSP 77  : Agent coordination (dispatch coordination)
  WSP 97  : Truth boundaries (simulation only)

NAVIGATION:
  -> Uses: build_plan_swarm_queue.py (SwarmWorkerQueue)
  -> Uses: worker_assignment_protocol.py (AssignmentDispatcher)
  -> Uses: build_plan.py (BuildStepAction)
  -> Called by: VoteBallot PoC tests, future WRE integration
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .build_plan import BuildStepAction
from .build_plan_swarm_queue import (
    AssignmentCompletionReport,
    CompletionStatus,
    DequeueDecision,
    QueueEntryStatus,
    SwarmWorkerQueue,
    SwarmWorkerQueueEntry,
    WorkerDequeueRequest,
    WorkerDequeueResult,
)
from .worker_assignment_protocol import (
    AssignmentDispatcher,
    AssignmentDispatchRequest,
    AssignmentDispatchResult,
    AssignmentDispatchStatus,
    WorkerCompletionEvent,
    WorkerProcess,
    WorkerProcessStatus,
)

logger = logging.getLogger("swarm_dispatch_integration")


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DispatchCycleStatus(str, Enum):
    """Status of a dispatch cycle."""

    SUCCESS = "success"
    """Dispatch cycle completed successfully."""

    NO_QUEUED_ENTRIES = "no_queued_entries"
    """No entries in queue."""

    NO_CAPABILITY_MATCH = "no_capability_match"
    """No entries match worker capabilities."""

    WORKER_NOT_FOUND = "worker_not_found"
    """Worker not registered in dispatcher."""

    DISPATCH_FAILED = "dispatch_failed"
    """Dispatch to worker failed."""

    COMPLETION_FAILED = "completion_failed"
    """Completion reporting failed."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class DispatchCycleResult:
    """
    Result of a single dispatch cycle.

    WSP 97: simulated is always True, real_process_started is always False.
    """

    success: bool
    """True if cycle completed successfully."""

    status: DispatchCycleStatus
    """Cycle status."""

    worker_id: str = ""
    """Worker involved in cycle."""

    entry_id: Optional[str] = None
    """Queue entry ID if applicable."""

    assignment_id: Optional[str] = None
    """Assignment ID if dispatched."""

    evidence_refs: List[str] = field(default_factory=list)
    """Evidence from completion (if completed)."""

    reason: str = ""
    """Human-readable reason."""

    # WSP 97 Truth Fields
    simulated: bool = True
    """Always True."""

    real_process_started: bool = False
    """Always False."""

    def __post_init__(self) -> None:
        """Enforce WSP 97 truth fields."""
        self.simulated = True
        self.real_process_started = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "status": self.status.value,
            "worker_id": self.worker_id,
            "entry_id": self.entry_id,
            "assignment_id": self.assignment_id,
            "evidence_refs": self.evidence_refs,
            "reason": self.reason,
            "simulated": self.simulated,
            "real_process_started": self.real_process_started,
        }


@dataclass
class QueueDispatchSummary:
    """
    Summary of queue dispatch state.

    WSP 97: all_simulated is always True, real_execution_performed is always False.
    """

    total_queued: int = 0
    """Total entries still queued."""

    total_processing: int = 0
    """Total entries being processed."""

    total_completed: int = 0
    """Total entries completed."""

    total_failed: int = 0
    """Total entries failed."""

    total_workers: int = 0
    """Total registered workers."""

    idle_workers: int = 0
    """Workers available for dispatch."""

    busy_workers: int = 0
    """Workers with assignments."""

    total_evidence_refs: int = 0
    """Total evidence refs collected."""

    # WSP 97 Truth Fields
    all_simulated: bool = True
    """Always True."""

    real_execution_performed: bool = False
    """Always False."""

    def __post_init__(self) -> None:
        """Enforce WSP 97 truth fields."""
        self.all_simulated = True
        self.real_execution_performed = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "total_queued": self.total_queued,
            "total_processing": self.total_processing,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "total_workers": self.total_workers,
            "idle_workers": self.idle_workers,
            "busy_workers": self.busy_workers,
            "total_evidence_refs": self.total_evidence_refs,
            "all_simulated": self.all_simulated,
            "real_execution_performed": self.real_execution_performed,
        }


# ---------------------------------------------------------------------------
# SwarmDispatchCoordinator
# ---------------------------------------------------------------------------


class SwarmDispatchCoordinator:
    """
    Coordinates between SwarmWorkerQueue and AssignmentDispatcher.

    Provides end-to-end simulated dispatch flow:
      1. Dequeue entry from queue matching worker capability
      2. Dispatch to worker via AssignmentDispatcher
      3. Complete assignment with evidence
      4. Track state across queue and dispatcher

    WSP 97 Truth Boundaries:
      - All dispatch is simulated only
      - No real processes are started
      - No files are edited
      - No CABR/reward/payout fields
    """

    def __init__(
        self,
        queue: SwarmWorkerQueue,
        dispatcher: AssignmentDispatcher,
    ) -> None:
        """
        Initialize the coordinator.

        Args:
            queue: SwarmWorkerQueue instance.
            dispatcher: AssignmentDispatcher instance.
        """
        self.queue = queue
        self.dispatcher = dispatcher

        # Track entry -> assignment mapping
        self._entry_to_assignment: Dict[str, str] = {}

        # Collect all evidence
        self._all_evidence: List[str] = []

    # ------------------------------------------------------------------
    # Dispatch Next
    # ------------------------------------------------------------------

    def dispatch_next(
        self,
        worker_id: str,
    ) -> DispatchCycleResult:
        """
        Dequeue next matching entry and dispatch to worker.

        Args:
            worker_id: Worker to dispatch to.

        Returns:
            DispatchCycleResult with dispatch status.
        """
        # Check worker exists in dispatcher
        worker = self.dispatcher.get_worker(worker_id)
        if not worker:
            return DispatchCycleResult(
                success=False,
                status=DispatchCycleStatus.WORKER_NOT_FOUND,
                worker_id=worker_id,
                reason=f"Worker {worker_id} not registered in dispatcher",
            )

        # Dequeue from queue using worker capabilities
        dequeue_request = WorkerDequeueRequest(
            worker_id=worker_id,
            capabilities=worker.capabilities,
            max_entries=1,
        )
        dequeue_result = self.queue.dequeue_for_worker(dequeue_request)

        if not dequeue_result.success:
            if dequeue_result.decision == DequeueDecision.QUEUE_EMPTY:
                return DispatchCycleResult(
                    success=False,
                    status=DispatchCycleStatus.NO_QUEUED_ENTRIES,
                    worker_id=worker_id,
                    reason="No entries in queue",
                )
            elif dequeue_result.decision == DequeueDecision.NO_MATCH:
                return DispatchCycleResult(
                    success=False,
                    status=DispatchCycleStatus.NO_CAPABILITY_MATCH,
                    worker_id=worker_id,
                    reason=f"No entries match capabilities: {worker.capabilities}",
                )
            else:
                return DispatchCycleResult(
                    success=False,
                    status=DispatchCycleStatus.DISPATCH_FAILED,
                    worker_id=worker_id,
                    reason=dequeue_result.reason,
                )

        # Get the dequeued entry
        entry = dequeue_result.entries[0]

        # Create dispatch request
        dispatch_request = AssignmentDispatchRequest(
            assignment_id=entry.assignment_id,
            entry_id=entry.entry_id,
            worker_id=worker_id,
            step_id=entry.step_id,
            step_action=entry.step_action,
            owned_files=entry.owned_files,
        )

        # Dispatch via dispatcher
        dispatch_result = self.dispatcher.dispatch_assignment(dispatch_request)

        if not dispatch_result.success:
            # Dispatch failed - entry is still in PROCESSING state in queue
            # In real system, we'd need to requeue - for now, just report failure
            return DispatchCycleResult(
                success=False,
                status=DispatchCycleStatus.DISPATCH_FAILED,
                worker_id=worker_id,
                entry_id=entry.entry_id,
                assignment_id=entry.assignment_id,
                reason=dispatch_result.reason,
            )

        # Track mapping
        self._entry_to_assignment[entry.entry_id] = entry.assignment_id

        logger.info(
            "[COORDINATOR] Dispatched entry %s to worker %s (simulated)",
            entry.entry_id,
            worker_id,
        )

        return DispatchCycleResult(
            success=True,
            status=DispatchCycleStatus.SUCCESS,
            worker_id=worker_id,
            entry_id=entry.entry_id,
            assignment_id=entry.assignment_id,
            reason="Dispatched successfully (simulated)",
        )

    # ------------------------------------------------------------------
    # Complete Dispatched Assignment
    # ------------------------------------------------------------------

    def complete_dispatched_assignment(
        self,
        worker_id: str,
        entry_id: str,
        evidence_refs: List[str],
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> DispatchCycleResult:
        """
        Complete a dispatched assignment with evidence.

        Reports completion to both AssignmentDispatcher and SwarmWorkerQueue.

        Args:
            worker_id: Worker completing the assignment.
            entry_id: Queue entry being completed.
            evidence_refs: Evidence from execution.
            success: True if assignment succeeded.
            error_message: Error message if failed.

        Returns:
            DispatchCycleResult with completion status.
        """
        # Get assignment ID from mapping
        assignment_id = self._entry_to_assignment.get(entry_id)
        if not assignment_id:
            # Try to get from queue entry
            entry = self.queue.get_entry(entry_id)
            if entry:
                assignment_id = entry.assignment_id
            else:
                return DispatchCycleResult(
                    success=False,
                    status=DispatchCycleStatus.COMPLETION_FAILED,
                    worker_id=worker_id,
                    entry_id=entry_id,
                    reason=f"Entry {entry_id} not found",
                )

        # Report completion to dispatcher
        completion_event = WorkerCompletionEvent(
            worker_id=worker_id,
            assignment_id=assignment_id,
            success=success,
            evidence_refs=evidence_refs,
            error_message=error_message,
        )
        dispatcher_result = self.dispatcher.receive_completion(completion_event)

        # Report completion to queue
        completion_status = (
            CompletionStatus.SUCCEEDED if success else CompletionStatus.FAILED
        )
        queue_report = AssignmentCompletionReport(
            entry_id=entry_id,
            worker_id=worker_id,
            status=completion_status,
            evidence_refs=evidence_refs,
            error_message=error_message,
        )
        queue_result = self.queue.complete_assignment(queue_report)

        if not queue_result.success:
            return DispatchCycleResult(
                success=False,
                status=DispatchCycleStatus.COMPLETION_FAILED,
                worker_id=worker_id,
                entry_id=entry_id,
                assignment_id=assignment_id,
                reason=queue_result.error_message or "Queue completion failed",
            )

        # Track evidence
        self._all_evidence.extend(evidence_refs)

        # Clean up mapping
        if entry_id in self._entry_to_assignment:
            del self._entry_to_assignment[entry_id]

        logger.info(
            "[COORDINATOR] Completed entry %s for worker %s (evidence=%d)",
            entry_id,
            worker_id,
            len(evidence_refs),
        )

        return DispatchCycleResult(
            success=True,
            status=DispatchCycleStatus.SUCCESS,
            worker_id=worker_id,
            entry_id=entry_id,
            assignment_id=assignment_id,
            evidence_refs=evidence_refs,
            reason="Completion recorded",
        )

    # ------------------------------------------------------------------
    # Run Simulated Cycle
    # ------------------------------------------------------------------

    def run_simulated_cycle(
        self,
        worker_id: str,
        evidence_refs: Optional[List[str]] = None,
    ) -> DispatchCycleResult:
        """
        Run a complete simulated dispatch cycle: dequeue -> dispatch -> complete.

        Args:
            worker_id: Worker to run cycle for.
            evidence_refs: Evidence to include in completion (optional).

        Returns:
            DispatchCycleResult with cycle status.
        """
        # Step 1: Dispatch next
        dispatch_result = self.dispatch_next(worker_id)

        if not dispatch_result.success:
            return dispatch_result

        # Step 2: Generate evidence if not provided
        entry_id = dispatch_result.entry_id
        assignment_id = dispatch_result.assignment_id

        if evidence_refs is None:
            evidence_refs = [
                f"evidence/{assignment_id}/simulated_execution",
                f"evidence/{entry_id}/step_completed",
            ]

        # Step 3: Complete
        completion_result = self.complete_dispatched_assignment(
            worker_id=worker_id,
            entry_id=entry_id,
            evidence_refs=evidence_refs,
        )

        return completion_result

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summarize(self) -> QueueDispatchSummary:
        """
        Get summary of queue dispatch state.

        Returns:
            QueueDispatchSummary with current state.
        """
        # Count queue entries by status
        queue_counts = self.queue.count_by_status()

        # Count workers by status
        all_workers = self.dispatcher.list_workers()
        idle_workers = self.dispatcher.list_workers(status=WorkerProcessStatus.IDLE)
        busy_workers = [
            w for w in all_workers
            if w.status in [WorkerProcessStatus.ASSIGNED, WorkerProcessStatus.PROCESSING]
        ]

        return QueueDispatchSummary(
            total_queued=queue_counts.get(QueueEntryStatus.QUEUED, 0),
            total_processing=queue_counts.get(QueueEntryStatus.PROCESSING, 0),
            total_completed=queue_counts.get(QueueEntryStatus.COMPLETED, 0),
            total_failed=queue_counts.get(QueueEntryStatus.FAILED, 0),
            total_workers=len(all_workers),
            idle_workers=len(idle_workers),
            busy_workers=len(busy_workers),
            total_evidence_refs=len(self._all_evidence),
        )

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_all_evidence(self) -> List[str]:
        """Get all collected evidence refs."""
        return list(self._all_evidence)


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def create_swarm_dispatch_coordinator(
    queue: SwarmWorkerQueue,
    dispatcher: AssignmentDispatcher,
) -> SwarmDispatchCoordinator:
    """
    Create a SwarmDispatchCoordinator instance.

    Args:
        queue: SwarmWorkerQueue instance.
        dispatcher: AssignmentDispatcher instance.

    Returns:
        SwarmDispatchCoordinator instance.
    """
    return SwarmDispatchCoordinator(queue=queue, dispatcher=dispatcher)
