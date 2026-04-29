#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BuildPlan Swarm Coordination — Multi-Agent Step Assignment Scaffold

Implements the SwarmCoordinator interface from BUILD_PLAN_SWARM_COORDINATION_CONTRACT.md.
This is a scaffold only. No real parallel execution is implemented.

WSP 97 TRUTH BOUNDARIES:
  - All assignments are simulated only
  - No workers actually edit files
  - No real agent processes start
  - real_execution_performed=False always
  - verification_complete=False always
  - cabr_ready=False always
  - No CABR/reward/payout/token fields

Architecture:
  BuildPlan -> SwarmCoordinator -> StepAssignment
           -> WorkerIdentity (registered, leased)
           -> FileOwnershipClaim (claimed, released)
           -> EvidenceBundle (aggregated refs)
           -> SwarmExecutionSummary (simulated-only)

WSP Compliance:
  WSP 11  : Interface contract (typed API)
  WSP 50  : Pre-action validation (scope checks)
  WSP 77  : Agent coordination (swarm model)
  WSP 97  : Truth boundaries (simulation only)

NAVIGATION:
  -> Spec: modules/foundups/docs/BUILD_PLAN_SWARM_COORDINATION_CONTRACT.md
  -> Uses: build_plan.py (BuildPlan, BuildStep, BuildTarget)
  -> Uses: build_plan_executor.py (patterns)
  -> Called by: Future swarm orchestration (not implemented)
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .build_plan import (
    BuildPlan,
    BuildStep,
    BuildTarget,
)

logger = logging.getLogger("build_plan_swarm")


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AssignmentStatus(str, Enum):
    """Step assignment lifecycle status."""

    ASSIGNED = "assigned"
    """Step assigned to worker, not yet started."""

    IN_PROGRESS = "in_progress"
    """Worker is processing the step."""

    COMPLETED = "completed"
    """Step completed (simulated)."""

    FAILED = "failed"
    """Step failed during simulation."""

    CANCELLED = "cancelled"
    """Assignment cancelled."""


class LeaseStatus(str, Enum):
    """Worker lease status."""

    ACTIVE = "active"
    """Lease is active, worker can hold claims."""

    EXPIRED = "expired"
    """Lease expired, claims released."""

    RELEASED = "released"
    """Worker explicitly released lease."""


class ConflictSeverity(str, Enum):
    """Conflict severity level."""

    WARNING = "warning"
    """Same file claimed by 2 workers, different steps."""

    ERROR = "error"
    """Same file claimed by 2 workers, same step."""

    FATAL = "fatal"
    """File outside target scope."""


class WorkerCapability(str, Enum):
    """Worker capability types."""

    VALIDATE = "validate"
    """Can perform validation steps."""

    BUILD = "build"
    """Can perform build/create steps."""

    TEST = "test"
    """Can perform test steps."""

    ALL = "all"
    """Can perform all step types."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_LEASE_DURATION_SECONDS = 300  # 5 minutes


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Lease:
    """Worker lease for holding file claims."""

    lease_id: str
    """Unique lease identifier."""

    worker_id: str
    """Worker holding this lease."""

    issued_at: datetime = field(default_factory=utc_now)
    """When lease was issued."""

    expires_at: datetime = field(default_factory=lambda: utc_now() + timedelta(seconds=DEFAULT_LEASE_DURATION_SECONDS))
    """When lease expires."""

    status: LeaseStatus = LeaseStatus.ACTIVE
    """Current lease status."""

    renewal_count: int = 0
    """Number of times lease was renewed."""

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        """Check if lease is expired."""
        now = now or utc_now()
        return now >= self.expires_at or self.status == LeaseStatus.EXPIRED

    def renew(self, duration_seconds: int = DEFAULT_LEASE_DURATION_SECONDS) -> None:
        """Renew the lease."""
        self.expires_at = utc_now() + timedelta(seconds=duration_seconds)
        self.renewal_count += 1
        self.status = LeaseStatus.ACTIVE

    def expire(self) -> None:
        """Expire the lease."""
        self.status = LeaseStatus.EXPIRED

    def release(self) -> None:
        """Release the lease."""
        self.status = LeaseStatus.RELEASED

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "lease_id": self.lease_id,
            "worker_id": self.worker_id,
            "issued_at": utc_iso(self.issued_at),
            "expires_at": utc_iso(self.expires_at),
            "status": self.status.value,
            "renewal_count": self.renewal_count,
        }


@dataclass
class WorkerIdentity:
    """Worker identity and capabilities."""

    worker_id: str
    """Unique worker identifier."""

    worker_type: str
    """Worker type: openclaw, hermes, 0102."""

    capabilities: List[str] = field(default_factory=list)
    """Worker capabilities: validate, build, test."""

    registered_at: datetime = field(default_factory=utc_now)
    """When worker registered."""

    lease: Optional[Lease] = None
    """Worker's current lease."""

    def has_capability(self, capability: str) -> bool:
        """Check if worker has a capability."""
        return capability in self.capabilities or "all" in self.capabilities

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "worker_id": self.worker_id,
            "worker_type": self.worker_type,
            "capabilities": self.capabilities,
            "registered_at": utc_iso(self.registered_at),
            "lease": self.lease.to_dict() if self.lease else None,
        }


@dataclass
class FileOwnershipClaim:
    """File ownership claim by a worker."""

    claim_id: str
    """Unique claim identifier."""

    file_path: str
    """Path to the claimed file."""

    worker_id: str
    """Worker holding this claim."""

    step_id: str
    """Step this claim is for."""

    claimed_at: datetime = field(default_factory=utc_now)
    """When claim was made."""

    expires_at: datetime = field(default_factory=lambda: utc_now() + timedelta(seconds=DEFAULT_LEASE_DURATION_SECONDS))
    """When claim expires (tied to lease)."""

    released: bool = False
    """True if claim was released."""

    def is_active(self, now: Optional[datetime] = None) -> bool:
        """Check if claim is still active."""
        now = now or utc_now()
        return not self.released and now < self.expires_at

    def release(self) -> None:
        """Release this claim."""
        self.released = True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "claim_id": self.claim_id,
            "file_path": self.file_path,
            "worker_id": self.worker_id,
            "step_id": self.step_id,
            "claimed_at": utc_iso(self.claimed_at),
            "expires_at": utc_iso(self.expires_at),
            "released": self.released,
        }


@dataclass
class StepAssignment:
    """Step assigned to a worker."""

    assignment_id: str
    """Unique assignment identifier."""

    step_id: str
    """BuildStep being assigned."""

    worker_id: str
    """Worker assigned to this step."""

    owned_files: List[str] = field(default_factory=list)
    """Files owned by this assignment."""

    status: AssignmentStatus = AssignmentStatus.ASSIGNED
    """Assignment status."""

    assigned_at: datetime = field(default_factory=utc_now)
    """When assignment was made."""

    completed_at: Optional[datetime] = None
    """When assignment completed."""

    evidence_refs: List[str] = field(default_factory=list)
    """Evidence references from execution."""

    simulated: bool = True
    """WSP 97: Always True in scaffold."""

    def __post_init__(self) -> None:
        """Enforce WSP 97: simulated is always True."""
        self.simulated = True

    def complete(self, evidence_refs: Optional[List[str]] = None) -> None:
        """Mark assignment as completed."""
        self.status = AssignmentStatus.COMPLETED
        self.completed_at = utc_now()
        if evidence_refs:
            self.evidence_refs.extend(evidence_refs)

    def fail(self, error_message: Optional[str] = None) -> None:
        """Mark assignment as failed."""
        self.status = AssignmentStatus.FAILED
        self.completed_at = utc_now()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "assignment_id": self.assignment_id,
            "step_id": self.step_id,
            "worker_id": self.worker_id,
            "owned_files": self.owned_files,
            "status": self.status.value,
            "assigned_at": utc_iso(self.assigned_at),
            "completed_at": utc_iso(self.completed_at),
            "evidence_refs": self.evidence_refs,
            "simulated": self.simulated,
        }


@dataclass
class ConflictReport:
    """File ownership conflict report."""

    conflict_id: str
    """Unique conflict identifier."""

    file_path: str
    """File with conflicting claims."""

    claimants: List[str] = field(default_factory=list)
    """Worker IDs claiming the same file."""

    severity: ConflictSeverity = ConflictSeverity.WARNING
    """Conflict severity."""

    detected_at: datetime = field(default_factory=utc_now)
    """When conflict was detected."""

    resolution: Optional[str] = None
    """How conflict was resolved, if at all."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "conflict_id": self.conflict_id,
            "file_path": self.file_path,
            "claimants": self.claimants,
            "severity": self.severity.value,
            "detected_at": utc_iso(self.detected_at),
            "resolution": self.resolution,
        }


@dataclass
class EvidenceBundle:
    """Aggregated evidence from all assignments."""

    bundle_id: str
    """Unique bundle identifier."""

    plan_id: str
    """BuildPlan this evidence is for."""

    total_assignments: int = 0
    """Total number of assignments."""

    completed_assignments: int = 0
    """Number of completed assignments."""

    evidence_refs: List[str] = field(default_factory=list)
    """Aggregated evidence references."""

    aggregated_at: datetime = field(default_factory=utc_now)
    """When evidence was aggregated."""

    # WSP 97: These are ALWAYS False
    verification_complete: bool = False
    cabr_ready: bool = False

    def __post_init__(self) -> None:
        """Enforce WSP 97 truth fields."""
        self.verification_complete = False
        self.cabr_ready = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "bundle_id": self.bundle_id,
            "plan_id": self.plan_id,
            "total_assignments": self.total_assignments,
            "completed_assignments": self.completed_assignments,
            "evidence_refs": self.evidence_refs,
            "aggregated_at": utc_iso(self.aggregated_at),
            "verification_complete": self.verification_complete,
            "cabr_ready": self.cabr_ready,
        }


@dataclass
class SwarmExecutionSummary:
    """Summary of swarm execution state."""

    plan_id: str
    """BuildPlan being executed."""

    total_workers: int = 0
    """Number of registered workers."""

    total_assignments: int = 0
    """Total assignments made."""

    completed_assignments: int = 0
    """Completed assignments."""

    failed_assignments: int = 0
    """Failed assignments."""

    active_conflicts: int = 0
    """Number of active conflicts."""

    all_simulated: bool = True
    """WSP 97: Always True."""

    build_complete: bool = False
    """True only if all assignments are simulated-complete."""

    real_execution_performed: bool = False
    """WSP 97: Always False."""

    def __post_init__(self) -> None:
        """Enforce WSP 97 truth fields."""
        self.all_simulated = True
        self.real_execution_performed = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "plan_id": self.plan_id,
            "total_workers": self.total_workers,
            "total_assignments": self.total_assignments,
            "completed_assignments": self.completed_assignments,
            "failed_assignments": self.failed_assignments,
            "active_conflicts": self.active_conflicts,
            "all_simulated": self.all_simulated,
            "build_complete": self.build_complete,
            "real_execution_performed": self.real_execution_performed,
        }


# ---------------------------------------------------------------------------
# SwarmCoordinator
# ---------------------------------------------------------------------------


class SwarmCoordinator:
    """
    Multi-agent step assignment and file ownership coordination.

    WSP 97 Truth Boundaries:
      - All assignments are simulated only
      - No workers actually edit files
      - No real agent processes start
      - No CABR/reward/payout fields
    """

    def __init__(self, plan: BuildPlan, lease_duration_seconds: int = DEFAULT_LEASE_DURATION_SECONDS):
        """
        Initialize swarm coordinator.

        Args:
            plan: BuildPlan to coordinate.
            lease_duration_seconds: Default lease duration.
        """
        self.plan = plan
        self.lease_duration_seconds = lease_duration_seconds

        # Worker registry
        self._workers: Dict[str, WorkerIdentity] = {}

        # Assignment tracking
        self._assignments: Dict[str, StepAssignment] = {}
        self._step_to_assignment: Dict[str, str] = {}  # step_id -> assignment_id

        # File ownership
        self._file_claims: Dict[str, FileOwnershipClaim] = {}  # file_path -> claim
        self._worker_claims: Dict[str, Set[str]] = {}  # worker_id -> set of file_paths

        # Conflicts
        self._conflicts: List[ConflictReport] = []

    # ------------------------------------------------------------------
    # Worker Management
    # ------------------------------------------------------------------

    def register_worker(self, worker: WorkerIdentity) -> None:
        """
        Register a worker in the swarm.

        Args:
            worker: WorkerIdentity to register.

        Raises:
            ValueError: If worker_id already registered.
        """
        if worker.worker_id in self._workers:
            raise ValueError(f"Worker {worker.worker_id} already registered")

        # Issue lease
        lease = Lease(
            lease_id=f"lease_{secrets.token_hex(4)}",
            worker_id=worker.worker_id,
            expires_at=utc_now() + timedelta(seconds=self.lease_duration_seconds),
        )
        worker.lease = lease
        worker.registered_at = utc_now()

        self._workers[worker.worker_id] = worker
        self._worker_claims[worker.worker_id] = set()

        logger.info(
            "[SWARM] Registered worker %s (type=%s, capabilities=%s)",
            worker.worker_id,
            worker.worker_type,
            worker.capabilities,
        )

    def get_worker(self, worker_id: str) -> Optional[WorkerIdentity]:
        """Get a worker by ID."""
        return self._workers.get(worker_id)

    def list_workers(self) -> List[WorkerIdentity]:
        """List all registered workers."""
        return list(self._workers.values())

    # ------------------------------------------------------------------
    # Step Assignment
    # ------------------------------------------------------------------

    def assign_step(
        self,
        step: BuildStep,
        worker_id: str,
        owned_files: List[str],
    ) -> StepAssignment:
        """
        Assign a step to a worker with file ownership.

        Args:
            step: BuildStep to assign.
            worker_id: Worker to assign to.
            owned_files: Files this assignment will own.

        Returns:
            StepAssignment created.

        Raises:
            ValueError: If worker not registered or step already assigned.
        """
        if worker_id not in self._workers:
            raise ValueError(f"Worker {worker_id} not registered")

        if step.step_id in self._step_to_assignment:
            raise ValueError(f"Step {step.step_id} already assigned")

        # Check worker lease is active
        worker = self._workers[worker_id]
        if worker.lease and worker.lease.is_expired():
            raise ValueError(f"Worker {worker_id} lease expired")

        # Validate files are in scope
        for file_path in owned_files:
            if not self._is_in_scope(file_path):
                raise ValueError(f"File {file_path} outside target scope")

        # Claim files
        claims = self.claim_files(worker_id, owned_files, step.step_id)

        # Create assignment
        assignment = StepAssignment(
            assignment_id=f"assign_{secrets.token_hex(4)}",
            step_id=step.step_id,
            worker_id=worker_id,
            owned_files=owned_files,
            status=AssignmentStatus.ASSIGNED,
        )

        self._assignments[assignment.assignment_id] = assignment
        self._step_to_assignment[step.step_id] = assignment.assignment_id

        logger.info(
            "[SWARM] Assigned step %s to worker %s (files=%d)",
            step.step_id,
            worker_id,
            len(owned_files),
        )

        return assignment

    def complete_assignment(
        self,
        assignment_id: str,
        evidence_refs: Optional[List[str]] = None,
    ) -> None:
        """
        Mark an assignment as completed.

        Args:
            assignment_id: Assignment to complete.
            evidence_refs: Evidence from execution.
        """
        if assignment_id not in self._assignments:
            raise ValueError(f"Assignment {assignment_id} not found")

        assignment = self._assignments[assignment_id]
        assignment.complete(evidence_refs)

        # Release files
        self.release_files(assignment.worker_id, assignment.owned_files)

        logger.info(
            "[SWARM] Completed assignment %s (step=%s, evidence=%d)",
            assignment_id,
            assignment.step_id,
            len(evidence_refs or []),
        )

    def get_assignment(self, assignment_id: str) -> Optional[StepAssignment]:
        """Get an assignment by ID."""
        return self._assignments.get(assignment_id)

    # ------------------------------------------------------------------
    # File Ownership
    # ------------------------------------------------------------------

    def claim_files(
        self,
        worker_id: str,
        files: List[str],
        step_id: str,
    ) -> List[FileOwnershipClaim]:
        """
        Claim file ownership for a step.

        Args:
            worker_id: Worker claiming files.
            files: Files to claim.
            step_id: Step this claim is for.

        Returns:
            List of FileOwnershipClaim created.

        Raises:
            ValueError: If file already claimed by another worker.
        """
        if worker_id not in self._workers:
            raise ValueError(f"Worker {worker_id} not registered")

        worker = self._workers[worker_id]
        claims = []

        for file_path in files:
            # Check if file is in scope
            if not self._is_in_scope(file_path):
                conflict = ConflictReport(
                    conflict_id=f"conflict_{secrets.token_hex(4)}",
                    file_path=file_path,
                    claimants=[worker_id],
                    severity=ConflictSeverity.FATAL,
                    resolution="blocked_out_of_scope",
                )
                self._conflicts.append(conflict)
                raise ValueError(f"File {file_path} outside target scope")

            # Check if file already claimed
            if file_path in self._file_claims:
                existing = self._file_claims[file_path]
                if existing.is_active() and existing.worker_id != worker_id:
                    # Conflict: different worker
                    severity = (
                        ConflictSeverity.ERROR
                        if existing.step_id == step_id
                        else ConflictSeverity.WARNING
                    )
                    conflict = ConflictReport(
                        conflict_id=f"conflict_{secrets.token_hex(4)}",
                        file_path=file_path,
                        claimants=[existing.worker_id, worker_id],
                        severity=severity,
                    )
                    self._conflicts.append(conflict)
                    raise ValueError(
                        f"File {file_path} already claimed by {existing.worker_id}"
                    )

            # Create claim
            lease_expires = (
                worker.lease.expires_at if worker.lease else utc_now() + timedelta(seconds=self.lease_duration_seconds)
            )
            claim = FileOwnershipClaim(
                claim_id=f"claim_{secrets.token_hex(4)}",
                file_path=file_path,
                worker_id=worker_id,
                step_id=step_id,
                expires_at=lease_expires,
            )

            self._file_claims[file_path] = claim
            self._worker_claims[worker_id].add(file_path)
            claims.append(claim)

        return claims

    def release_files(self, worker_id: str, files: List[str]) -> None:
        """
        Release file ownership.

        Args:
            worker_id: Worker releasing files.
            files: Files to release.
        """
        for file_path in files:
            if file_path in self._file_claims:
                claim = self._file_claims[file_path]
                if claim.worker_id == worker_id:
                    claim.release()
                    del self._file_claims[file_path]

            if worker_id in self._worker_claims:
                self._worker_claims[worker_id].discard(file_path)

    def _is_in_scope(self, file_path: str) -> bool:
        """Check if file is within BuildPlan target scope."""
        if not self.plan.target:
            return False

        target = self.plan.target
        normalized = file_path.replace("\\", "/")

        # Check module_path
        if target.module_path:
            module_normalized = target.module_path.replace("\\", "/")
            if normalized.startswith(module_normalized):
                return True

        # Check pwa_surface_path
        if target.pwa_surface_path:
            pwa_normalized = target.pwa_surface_path.replace("\\", "/")
            if normalized.startswith(pwa_normalized):
                return True

        # Check allowed_paths
        for allowed in target.allowed_paths:
            allowed_normalized = allowed.replace("\\", "/")
            if normalized.startswith(allowed_normalized):
                return True

        # Check blocked_paths
        for blocked in target.blocked_paths:
            blocked_normalized = blocked.replace("\\", "/")
            if normalized.startswith(blocked_normalized):
                return False

        return False

    # ------------------------------------------------------------------
    # Lease Management
    # ------------------------------------------------------------------

    def renew_lease(self, lease_id: str) -> Lease:
        """
        Renew a worker's lease.

        Args:
            lease_id: Lease to renew.

        Returns:
            Renewed Lease.

        Raises:
            ValueError: If lease not found.
        """
        for worker in self._workers.values():
            if worker.lease and worker.lease.lease_id == lease_id:
                worker.lease.renew(self.lease_duration_seconds)
                # Extend file claims too
                for file_path in self._worker_claims.get(worker.worker_id, set()):
                    if file_path in self._file_claims:
                        self._file_claims[file_path].expires_at = worker.lease.expires_at
                return worker.lease

        raise ValueError(f"Lease {lease_id} not found")

    def expire_leases(self, now: Optional[datetime] = None) -> List[str]:
        """
        Expire stale leases and release their claims.

        Args:
            now: Current time (for testing).

        Returns:
            List of expired worker IDs.
        """
        now = now or utc_now()
        expired_workers = []

        for worker in self._workers.values():
            if worker.lease and worker.lease.is_expired(now):
                worker.lease.expire()
                expired_workers.append(worker.worker_id)

                # Release all claims
                for file_path in list(self._worker_claims.get(worker.worker_id, set())):
                    if file_path in self._file_claims:
                        self._file_claims[file_path].release()
                        del self._file_claims[file_path]
                self._worker_claims[worker.worker_id] = set()

                logger.info(
                    "[SWARM] Expired lease for worker %s",
                    worker.worker_id,
                )

        return expired_workers

    # ------------------------------------------------------------------
    # Conflict Detection
    # ------------------------------------------------------------------

    def detect_conflicts(self) -> List[ConflictReport]:
        """
        Detect file ownership conflicts.

        Returns:
            List of ConflictReport for current conflicts.
        """
        # Check for active conflicts in current claims
        file_to_claimants: Dict[str, List[str]] = {}

        for file_path, claim in self._file_claims.items():
            if claim.is_active():
                if file_path not in file_to_claimants:
                    file_to_claimants[file_path] = []
                file_to_claimants[file_path].append(claim.worker_id)

        # Generate conflict reports for duplicates
        for file_path, claimants in file_to_claimants.items():
            if len(claimants) > 1:
                conflict = ConflictReport(
                    conflict_id=f"conflict_{secrets.token_hex(4)}",
                    file_path=file_path,
                    claimants=claimants,
                    severity=ConflictSeverity.ERROR,
                )
                if conflict not in self._conflicts:
                    self._conflicts.append(conflict)

        return self._conflicts

    # ------------------------------------------------------------------
    # Evidence Aggregation
    # ------------------------------------------------------------------

    def aggregate_evidence(self) -> EvidenceBundle:
        """
        Aggregate evidence from all assignments.

        Returns:
            EvidenceBundle with aggregated refs.
        """
        evidence_refs = []
        completed = 0

        for assignment in self._assignments.values():
            if assignment.status == AssignmentStatus.COMPLETED:
                completed += 1
                evidence_refs.extend(assignment.evidence_refs)

        bundle = EvidenceBundle(
            bundle_id=f"bundle_{secrets.token_hex(4)}",
            plan_id=self.plan.build_plan_id,
            total_assignments=len(self._assignments),
            completed_assignments=completed,
            evidence_refs=evidence_refs,
        )

        return bundle

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summarize(self) -> SwarmExecutionSummary:
        """
        Summarize swarm execution state.

        Returns:
            SwarmExecutionSummary with current state.
        """
        completed = sum(
            1 for a in self._assignments.values()
            if a.status == AssignmentStatus.COMPLETED
        )
        failed = sum(
            1 for a in self._assignments.values()
            if a.status == AssignmentStatus.FAILED
        )
        active_conflicts = sum(
            1 for c in self._conflicts
            if c.resolution is None
        )

        # build_complete is True only if ALL assignments are completed
        build_complete = (
            len(self._assignments) > 0
            and completed == len(self._assignments)
            and failed == 0
        )

        summary = SwarmExecutionSummary(
            plan_id=self.plan.build_plan_id,
            total_workers=len(self._workers),
            total_assignments=len(self._assignments),
            completed_assignments=completed,
            failed_assignments=failed,
            active_conflicts=active_conflicts,
            build_complete=build_complete,
        )

        return summary


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def create_swarm_coordinator(plan: BuildPlan) -> SwarmCoordinator:
    """
    Create a SwarmCoordinator for a BuildPlan.

    Args:
        plan: BuildPlan to coordinate.

    Returns:
        SwarmCoordinator instance.
    """
    return SwarmCoordinator(plan=plan)
