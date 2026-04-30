#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Worker Assignment Protocol — Real Worker Dispatch Scaffold

Defines typed interfaces for dispatching SwarmWorkerQueue assignments to
actual worker processes (OpenClaw, Hermes, Claude 0102, Qwen, Gemma).

This is a scaffold only. No real worker processes are started.

WSP 97 TRUTH BOUNDARIES:
  - All dispatch is simulated only
  - No real processes are started
  - No Claude/OpenClaw/Hermes invocation
  - No files are edited
  - No CABR/reward/payout/token fields
  - real_execution_performed does not exist (cannot become True)

Architecture:
  SwarmWorkerQueue.dequeue_for_worker()
      │
      ▼
  AssignmentDispatcher.dispatch_assignment()
      │
      ├─> WorkerProcess registration
      ├─> Assignment dispatch (SIMULATED)
      ├─> Heartbeat monitoring
      └─> Completion reporting

WSP Compliance:
  WSP 11  : Interface contract (typed API)
  WSP 50  : Pre-action validation (identity verification)
  WSP 77  : Agent coordination (worker dispatch)
  WSP 97  : Truth boundaries (simulation only)

NAVIGATION:
  -> Spec: modules/foundups/docs/REAL_WORKER_ASSIGNMENT_PROTOCOL.md
  -> Uses: build_plan_swarm_queue.py (SwarmWorkerQueueEntry)
  -> Uses: build_plan_swarm.py (StepAssignment)
  -> Uses: build_plan.py (BuildStepAction)
  -> Called by: Future WRE worker integration (not implemented)
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .build_plan import BuildStepAction

logger = logging.getLogger("worker_assignment_protocol")


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WorkerProcessStatus(str, Enum):
    """Worker process lifecycle status."""

    IDLE = "idle"
    """Registered, awaiting assignment."""

    ASSIGNED = "assigned"
    """Assignment dispatched."""

    PROCESSING = "processing"
    """Actively processing assignment."""

    FAILED = "failed"
    """Failed/error state."""

    TERMINATED = "terminated"
    """Deregistered."""


class WorkerRuntimeType(str, Enum):
    """Worker runtime type."""

    OPENCLAW = "openclaw"
    """OpenClaw agent."""

    HERMES = "hermes"
    """Hermes FoundUp builder."""

    CLAUDE_0102 = "claude_0102"
    """Claude 0102 agent."""

    QWEN = "qwen"
    """Qwen local model."""

    GEMMA = "gemma"
    """Gemma local model."""

    GENERIC = "generic"
    """Generic/unknown worker."""


class AssignmentDispatchStatus(str, Enum):
    """Assignment dispatch result status."""

    SIMULATED_DISPATCH = "simulated_dispatch"
    """Dispatch simulated (no real process)."""

    SPECIFIED_NOT_IMPLEMENTED = "specified_not_implemented"
    """Interface specified but not implemented."""

    WORKER_NOT_FOUND = "worker_not_found"
    """Worker not registered."""

    WORKER_BUSY = "worker_busy"
    """Worker already has assignment."""

    CAPABILITY_MISMATCH = "capability_mismatch"
    """Worker lacks required capability."""

    DISPATCH_FAILED = "dispatch_failed"
    """Dispatch failed for other reason."""


class WorkerTrustLevel(str, Enum):
    """Worker trust level."""

    UNTRUSTED = "untrusted"
    """New/unknown worker."""

    VERIFIED = "verified"
    """Identity confirmed."""

    TRUSTED = "trusted"
    """Track record established."""

    SYSTEM = "system"
    """System-level worker."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class WorkerProcess:
    """
    Registered worker process.

    WSP 97: simulated is always True. No real process is represented.
    """

    worker_id: str
    """Unique worker identifier."""

    runtime_type: WorkerRuntimeType
    """Worker runtime type."""

    capabilities: List[str] = field(default_factory=list)
    """Worker capabilities (validate, build, test, etc.)."""

    trust_level: WorkerTrustLevel = WorkerTrustLevel.UNTRUSTED
    """Worker trust level."""

    status: WorkerProcessStatus = WorkerProcessStatus.IDLE
    """Worker lifecycle status."""

    registered_at: datetime = field(default_factory=utc_now)
    """When worker was registered."""

    last_seen_at: Optional[datetime] = None
    """Last heartbeat time."""

    current_assignment_id: Optional[str] = None
    """Current assignment ID if any."""

    # Identity verification (simulated)
    identity_verified: bool = False
    """True if identity was verified (simulated)."""

    identity_method: Optional[str] = None
    """Verification method: api_key, jwt, mtls, internal, none."""

    # WSP 97 Truth Fields
    simulated: bool = True
    """Always True in scaffold."""

    def __post_init__(self) -> None:
        """Enforce WSP 97: simulated is always True."""
        self.simulated = True

    def has_capability(self, capability: str) -> bool:
        """Check if worker has a capability."""
        return capability in self.capabilities or "all" in self.capabilities

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "worker_id": self.worker_id,
            "runtime_type": self.runtime_type.value,
            "capabilities": self.capabilities,
            "trust_level": self.trust_level.value,
            "status": self.status.value,
            "registered_at": utc_iso(self.registered_at),
            "last_seen_at": utc_iso(self.last_seen_at),
            "current_assignment_id": self.current_assignment_id,
            "identity_verified": self.identity_verified,
            "identity_method": self.identity_method,
            "simulated": self.simulated,
        }


@dataclass
class WorkerRegistration:
    """Request to register a worker process."""

    worker_id: str
    """Proposed worker ID."""

    runtime_type: WorkerRuntimeType
    """Worker runtime type."""

    capabilities: List[str] = field(default_factory=list)
    """Worker capabilities."""

    identity_claim: Optional[str] = None
    """Identity claim (API key, JWT, etc.) — simulated."""

    requested_trust_level: WorkerTrustLevel = WorkerTrustLevel.UNTRUSTED
    """Requested trust level."""


@dataclass
class WorkerDeregistration:
    """Result of worker deregistration."""

    worker_id: str
    """Worker that was deregistered."""

    deregistered_at: datetime = field(default_factory=utc_now)
    """When deregistration occurred."""

    reason: str = ""
    """Reason for deregistration."""

    assignments_released: List[str] = field(default_factory=list)
    """Assignment IDs that were released."""

    success: bool = True
    """True if deregistration succeeded."""


@dataclass
class AssignmentDispatchRequest:
    """Request to dispatch an assignment to a worker."""

    assignment_id: str
    """From StepAssignment."""

    entry_id: str
    """From SwarmWorkerQueueEntry."""

    worker_id: str
    """Target worker."""

    step_id: str
    """BuildStep ID."""

    step_action: BuildStepAction
    """Action to perform."""

    owned_files: List[str] = field(default_factory=list)
    """Files to work on."""

    timeout_seconds: int = 300
    """Assignment timeout."""


@dataclass
class AssignmentDispatchResult:
    """
    Result of assignment dispatch.

    WSP 97: simulated is always True, real_process_started is always False.
    """

    success: bool
    """True if dispatch succeeded."""

    dispatch_status: AssignmentDispatchStatus
    """Dispatch status."""

    assignment_id: str = ""
    """Assignment ID."""

    worker_id: str = ""
    """Worker ID."""

    reason: str = ""
    """Human-readable reason."""

    dispatched_at: Optional[datetime] = None
    """When dispatch occurred."""

    # WSP 97 Truth Fields
    simulated: bool = True
    """Always True in scaffold."""

    real_process_started: bool = False
    """Always False in scaffold."""

    def __post_init__(self) -> None:
        """Enforce WSP 97: simulated=True, real_process_started=False."""
        self.simulated = True
        self.real_process_started = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "dispatch_status": self.dispatch_status.value,
            "assignment_id": self.assignment_id,
            "worker_id": self.worker_id,
            "reason": self.reason,
            "dispatched_at": utc_iso(self.dispatched_at),
            "simulated": self.simulated,
            "real_process_started": self.real_process_started,
        }


@dataclass
class WorkerHeartbeatEvent:
    """Heartbeat event from worker."""

    worker_id: str
    """Worker sending heartbeat."""

    assignment_id: Optional[str] = None
    """Current assignment if any."""

    heartbeat_at: datetime = field(default_factory=utc_now)
    """When heartbeat was sent."""

    status: WorkerProcessStatus = WorkerProcessStatus.PROCESSING
    """Worker status."""

    progress_percent: Optional[int] = None
    """Progress 0-100 if applicable."""


@dataclass
class WorkerCompletionEvent:
    """
    Completion event from worker.

    WSP 97: simulated is always True. Cannot set real_execution_performed.
    """

    worker_id: str
    """Worker reporting completion."""

    assignment_id: str
    """Assignment that was completed."""

    completed_at: datetime = field(default_factory=utc_now)
    """When completion occurred."""

    success: bool = True
    """True if assignment succeeded."""

    evidence_refs: List[str] = field(default_factory=list)
    """Evidence from execution."""

    error_message: Optional[str] = None
    """Error message if failed."""

    # WSP 97 Truth Fields
    simulated: bool = True
    """Always True in scaffold."""

    def __post_init__(self) -> None:
        """Enforce WSP 97: simulated is always True."""
        self.simulated = True


# ---------------------------------------------------------------------------
# AssignmentDispatcher
# ---------------------------------------------------------------------------


class AssignmentDispatcher:
    """
    Dispatches SwarmWorkerQueue assignments to worker processes.

    WSP 97 Truth Boundaries:
      - All dispatch is simulated only
      - No real processes are started
      - No Claude/OpenClaw/Hermes invocation
      - No files are edited
      - No CABR/reward/payout fields
    """

    def __init__(self) -> None:
        """Initialize the dispatcher."""
        # In-memory worker registry (Phase 1)
        self._workers: Dict[str, WorkerProcess] = {}

        # Assignment tracking
        self._assignments: Dict[str, str] = {}  # assignment_id -> worker_id

        # Event log (for audit trail)
        self._events: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Worker Registration
    # ------------------------------------------------------------------

    def register_worker(
        self,
        registration: WorkerRegistration,
    ) -> WorkerProcess:
        """
        Register a worker process with capabilities.

        Args:
            registration: WorkerRegistration with worker details.

        Returns:
            WorkerProcess representing the registered worker.

        Raises:
            ValueError: If worker ID already registered.
        """
        if registration.worker_id in self._workers:
            raise ValueError(
                f"Worker {registration.worker_id} already registered"
            )

        # Verify identity (simulated)
        identity_verified = self._verify_identity(registration)

        # Determine trust level
        trust_level = (
            registration.requested_trust_level
            if identity_verified
            else WorkerTrustLevel.UNTRUSTED
        )

        # Create worker process
        worker = WorkerProcess(
            worker_id=registration.worker_id,
            runtime_type=registration.runtime_type,
            capabilities=list(registration.capabilities),
            trust_level=trust_level,
            status=WorkerProcessStatus.IDLE,
            identity_verified=identity_verified,
            identity_method="simulated" if identity_verified else None,
        )

        self._workers[worker.worker_id] = worker

        # Log event
        self._log_event("worker_registered", {
            "worker_id": worker.worker_id,
            "runtime_type": worker.runtime_type.value,
            "capabilities": worker.capabilities,
        })

        logger.info(
            "[DISPATCHER] Registered worker %s (%s) with capabilities %s",
            worker.worker_id,
            worker.runtime_type.value,
            worker.capabilities,
        )

        return worker

    def _verify_identity(self, registration: WorkerRegistration) -> bool:
        """
        Verify worker identity claim.

        WSP 97: Always returns True in scaffold. Real verification NOT IMPLEMENTED.

        Args:
            registration: Worker registration with identity claim.

        Returns:
            True (simulated verification).
        """
        # Simulated verification — always passes
        return True

    # ------------------------------------------------------------------
    # Worker Deregistration
    # ------------------------------------------------------------------

    def deregister_worker(
        self,
        worker_id: str,
    ) -> WorkerDeregistration:
        """
        Deregister a worker, releasing any assignments.

        Args:
            worker_id: Worker to deregister.

        Returns:
            WorkerDeregistration with result.
        """
        worker = self._workers.get(worker_id)

        if not worker:
            return WorkerDeregistration(
                worker_id=worker_id,
                reason=f"Worker {worker_id} not found",
                success=False,
            )

        # Release any assignments
        released_assignments = []
        for assignment_id, assigned_worker in list(self._assignments.items()):
            if assigned_worker == worker_id:
                del self._assignments[assignment_id]
                released_assignments.append(assignment_id)

        # Update worker status
        worker.status = WorkerProcessStatus.TERMINATED
        worker.current_assignment_id = None

        # Log event
        self._log_event("worker_deregistered", {
            "worker_id": worker_id,
            "assignments_released": released_assignments,
        })

        logger.info(
            "[DISPATCHER] Deregistered worker %s, released %d assignments",
            worker_id,
            len(released_assignments),
        )

        return WorkerDeregistration(
            worker_id=worker_id,
            reason="Worker deregistered",
            assignments_released=released_assignments,
            success=True,
        )

    # ------------------------------------------------------------------
    # Assignment Dispatch
    # ------------------------------------------------------------------

    def dispatch_assignment(
        self,
        request: AssignmentDispatchRequest,
    ) -> AssignmentDispatchResult:
        """
        Dispatch an assignment to a registered worker.

        WSP 97: Returns SIMULATED_DISPATCH or SPECIFIED_NOT_IMPLEMENTED.
        Does NOT start a real process.

        Args:
            request: AssignmentDispatchRequest with assignment details.

        Returns:
            AssignmentDispatchResult with dispatch status.
        """
        worker = self._workers.get(request.worker_id)

        # Check worker exists
        if not worker:
            return AssignmentDispatchResult(
                success=False,
                dispatch_status=AssignmentDispatchStatus.WORKER_NOT_FOUND,
                assignment_id=request.assignment_id,
                worker_id=request.worker_id,
                reason=f"Worker {request.worker_id} not found",
            )

        # Check worker is available
        if worker.status not in [WorkerProcessStatus.IDLE]:
            return AssignmentDispatchResult(
                success=False,
                dispatch_status=AssignmentDispatchStatus.WORKER_BUSY,
                assignment_id=request.assignment_id,
                worker_id=request.worker_id,
                reason=f"Worker {request.worker_id} is {worker.status.value}",
            )

        # Check capability (simplified — real implementation would use action mapping)
        # For now, any registered worker can receive any assignment (simulated)

        # Simulate dispatch (no real process started)
        worker.status = WorkerProcessStatus.ASSIGNED
        worker.current_assignment_id = request.assignment_id
        self._assignments[request.assignment_id] = request.worker_id

        # Log event
        self._log_event("assignment_dispatched", {
            "assignment_id": request.assignment_id,
            "worker_id": request.worker_id,
            "step_id": request.step_id,
            "step_action": request.step_action.value,
        })

        logger.info(
            "[DISPATCHER] Dispatched assignment %s to worker %s (SIMULATED)",
            request.assignment_id,
            request.worker_id,
        )

        return AssignmentDispatchResult(
            success=True,
            dispatch_status=AssignmentDispatchStatus.SIMULATED_DISPATCH,
            assignment_id=request.assignment_id,
            worker_id=request.worker_id,
            reason="Assignment dispatched (simulated)",
            dispatched_at=utc_now(),
        )

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    def receive_heartbeat(
        self,
        event: WorkerHeartbeatEvent,
    ) -> WorkerProcess:
        """
        Receive heartbeat from worker, update last_seen.

        Args:
            event: WorkerHeartbeatEvent from worker.

        Returns:
            Updated WorkerProcess.

        Raises:
            ValueError: If worker not found.
        """
        worker = self._workers.get(event.worker_id)

        if not worker:
            raise ValueError(f"Worker {event.worker_id} not found")

        # Update last seen
        worker.last_seen_at = event.heartbeat_at

        # Update status if processing
        if event.status == WorkerProcessStatus.PROCESSING:
            worker.status = WorkerProcessStatus.PROCESSING

        # Log event (debug level to avoid spam)
        logger.debug(
            "[DISPATCHER] Heartbeat from worker %s (progress=%s)",
            event.worker_id,
            event.progress_percent,
        )

        return worker

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------

    def receive_completion(
        self,
        event: WorkerCompletionEvent,
    ) -> AssignmentDispatchResult:
        """
        Receive completion report from worker.

        WSP 97: Cannot set real_execution_performed=True.

        Args:
            event: WorkerCompletionEvent from worker.

        Returns:
            AssignmentDispatchResult with completion status.
        """
        worker = self._workers.get(event.worker_id)

        if not worker:
            return AssignmentDispatchResult(
                success=False,
                dispatch_status=AssignmentDispatchStatus.WORKER_NOT_FOUND,
                assignment_id=event.assignment_id,
                worker_id=event.worker_id,
                reason=f"Worker {event.worker_id} not found",
            )

        # Clear assignment
        if event.assignment_id in self._assignments:
            del self._assignments[event.assignment_id]

        # Update worker status
        worker.status = WorkerProcessStatus.IDLE
        worker.current_assignment_id = None
        worker.last_seen_at = event.completed_at

        # Log event
        self._log_event("completion_received", {
            "assignment_id": event.assignment_id,
            "worker_id": event.worker_id,
            "success": event.success,
            "evidence_refs": event.evidence_refs,
            "error_message": event.error_message,
        })

        logger.info(
            "[DISPATCHER] Completion from worker %s for assignment %s (success=%s, evidence=%d)",
            event.worker_id,
            event.assignment_id,
            event.success,
            len(event.evidence_refs),
        )

        return AssignmentDispatchResult(
            success=event.success,
            dispatch_status=AssignmentDispatchStatus.SIMULATED_DISPATCH,
            assignment_id=event.assignment_id,
            worker_id=event.worker_id,
            reason="Completion received" if event.success else event.error_message or "Failed",
            dispatched_at=event.completed_at,
        )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list_workers(
        self,
        status: Optional[WorkerProcessStatus] = None,
    ) -> List[WorkerProcess]:
        """
        List registered workers, optionally filtered by status.

        Args:
            status: Filter by status (optional).

        Returns:
            List of matching workers.
        """
        if status is None:
            return list(self._workers.values())

        return [w for w in self._workers.values() if w.status == status]

    def get_worker(self, worker_id: str) -> Optional[WorkerProcess]:
        """Get a worker by ID."""
        return self._workers.get(worker_id)

    def get_events(self) -> List[Dict[str, Any]]:
        """Get audit event log."""
        return list(self._events)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log an audit event."""
        self._events.append({
            "event_type": event_type,
            "timestamp": utc_now().isoformat(),
            **data,
        })


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def create_assignment_dispatcher() -> AssignmentDispatcher:
    """
    Create an AssignmentDispatcher instance.

    Returns:
        AssignmentDispatcher instance.
    """
    return AssignmentDispatcher()
