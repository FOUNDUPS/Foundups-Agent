"""Persistent Task Pipeline Service for FoundUps Agent Market.

Implements TaskPipelineService interface with SQLite persistence.
Manages complete task lifecycle: create → claim → submit → verify → payout.

WSP References:
- WSP 11: Implements TaskPipelineService interface contract
- WSP 30: Persistence layer integration
- WSP 50: Error handling with domain exceptions
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .exceptions import InvalidStateTransitionError, NotFoundError, PermissionDeniedError, ValidationError
from .interfaces import TaskPipelineService
from .models import EventRecord, Payout, Proof, Task, TaskStatus, Verification
from .persistence.sqlite_adapter import SQLiteAdapter

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class PersistentTaskPipeline(TaskPipelineService):
    """Persistent implementation of TaskPipelineService.

    Delegates storage to SQLiteAdapter and emits events for observability.

    Initiation lifecycle:
        OPEN → CLAIMED → SUBMITTED → VERIFIED (payout remains pending)

    Example:
        adapter = SQLiteAdapter()
        pipeline = PersistentTaskPipeline(adapter)
        task = pipeline.create_task(task)
        pipeline.claim_task(task.task_id, agent_id)
    """

    VALID_TRANSITIONS = {
        TaskStatus.OPEN: [TaskStatus.CLAIMED],
        TaskStatus.CLAIMED: [TaskStatus.SUBMITTED],
        TaskStatus.SUBMITTED: [TaskStatus.VERIFIED],
        TaskStatus.VERIFIED: [TaskStatus.PAID],
        TaskStatus.PAID: [],  # Terminal state
    }

    def __init__(self, adapter: SQLiteAdapter) -> None:
        """Initialize with SQLite adapter.

        Args:
            adapter: SQLiteAdapter instance for persistence.
        """
        self._adapter = adapter

    def _enforce_compute_access(
        self,
        actor_id: str,
        capability: str,
        foundup_id: str,
        reason: str,
    ) -> None:
        ensure = getattr(self._adapter, "ensure_access", None)
        debit = getattr(self._adapter, "debit_credits", None)
        if not callable(ensure) or not callable(debit):
            return

        decision = ensure(actor_id=actor_id, capability=capability, foundup_id=foundup_id)
        if not bool(decision.get("allowed")):
            raise PermissionDeniedError(str(decision.get("reason", "compute access denied")))
        required = int(decision.get("required_credits", 0))
        if required > 0:
            debit(actor_id=actor_id, amount=required, reason=reason, foundup_id=foundup_id)

    def _emit_event(
        self,
        event_type: str,
        actor_id: str,
        payload: Dict[str, Any],
        foundup_id: Optional[str] = None,
        task_id: Optional[str] = None,
        proof_id: Optional[str] = None,
        payout_id: Optional[str] = None,
    ) -> None:
        """Emit an event to the event log."""
        event = EventRecord(
            event_id=_generate_id("evt"),
            event_type=event_type,
            actor_id=actor_id,
            payload=payload,
            foundup_id=foundup_id,
            task_id=task_id,
            proof_id=proof_id,
            payout_id=payout_id,
            timestamp=_utc_now(),
        )
        self._adapter.create_event(event)
        logger.debug("Emitted event: %s for task %s", event_type, task_id)

    def _validate_transition(self, current: TaskStatus, target: TaskStatus) -> None:
        """Validate state transition is allowed."""
        allowed = self.VALID_TRANSITIONS.get(current, [])
        if target not in allowed:
            raise InvalidStateTransitionError(
                f"Invalid transition from {current.value} to {target.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

    def create_task(self, task: Task) -> Task:
        """Create a new task.

        Args:
            task: Task to create. Must have status OPEN.

        Returns:
            Created task.

        Raises:
            ValidationError: If task status is not OPEN.
        """
        if task.status != TaskStatus.OPEN:
            raise ValidationError("New task must have status OPEN")

        self._enforce_compute_access(
            actor_id=task.creator_id,
            capability="task.create",
            foundup_id=task.foundup_id,
            reason="create_task",
        )
        created = self._adapter.create_task(task)
        self._emit_event(
            event_type="task.created",
            actor_id=task.creator_id,
            payload={"title": task.title, "reward_amount": task.reward_amount},
            foundup_id=task.foundup_id,
            task_id=task.task_id,
        )
        logger.info("Task created: %s", task.task_id)
        return created

    def claim_task(self, task_id: str, agent_id: str) -> Task:
        """Claim a task for work.

        Args:
            task_id: ID of task to claim.
            agent_id: ID of agent claiming the task.

        Returns:
            Updated task with CLAIMED status.

        Raises:
            NotFoundError: If task not found.
            StateTransitionError: If task not in OPEN state.
        """
        task = self._adapter.get_task(task_id)
        self._validate_transition(task.status, TaskStatus.CLAIMED)
        self._enforce_compute_access(
            actor_id=agent_id,
            capability="task.claim",
            foundup_id=task.foundup_id,
            reason="claim_task",
        )

        task.status = TaskStatus.CLAIMED
        task.assignee_id = agent_id

        updated = self._adapter.update_task(task)
        self._emit_event(
            event_type="task.claimed",
            actor_id=agent_id,
            payload={"assignee_id": agent_id},
            foundup_id=task.foundup_id,
            task_id=task_id,
        )
        logger.info("Task %s claimed by %s", task_id, agent_id)
        return updated

    def submit_proof(self, proof: Proof) -> Task:
        """Submit proof of work for a task.

        Args:
            proof: Proof to submit.

        Returns:
            Updated task with SUBMITTED status.

        Raises:
            NotFoundError: If task not found.
            StateTransitionError: If task not in CLAIMED state.
            ValidationError: If submitter is not the assignee.
        """
        task = self._adapter.get_task(proof.task_id)
        self._validate_transition(task.status, TaskStatus.SUBMITTED)

        if task.assignee_id != proof.submitter_id:
            raise ValidationError(
                f"Proof submitter {proof.submitter_id} is not task assignee {task.assignee_id}"
            )
        self._enforce_compute_access(
            actor_id=proof.submitter_id,
            capability="proof.submit",
            foundup_id=task.foundup_id,
            reason="submit_proof",
        )

        # Save proof
        self._adapter.create_proof(proof)

        # Update task
        task.status = TaskStatus.SUBMITTED
        task.proof_id = proof.proof_id

        updated = self._adapter.update_task(task)
        self._emit_event(
            event_type="proof.submitted",
            actor_id=proof.submitter_id,
            payload={
                "proof_id": proof.proof_id,
                "artifact_uri": proof.artifact_uri,
                "artifact_hash": proof.artifact_hash,
            },
            foundup_id=task.foundup_id,
            task_id=task.task_id,
            proof_id=proof.proof_id,
        )
        logger.info("Proof %s submitted for task %s", proof.proof_id, task.task_id)
        return updated

    def verify_proof(self, task_id: str, verification: Verification) -> Task:
        """Verify submitted proof.

        Args:
            task_id: ID of task to verify.
            verification: Verification result.

        Returns:
            Updated task with VERIFIED status (if approved).

        Raises:
            NotFoundError: If task not found.
            StateTransitionError: If task not in SUBMITTED state.
            ValidationError: If verification rejected (approved=False).
        """
        task = self._adapter.get_task(task_id)
        self._validate_transition(task.status, TaskStatus.VERIFIED)

        if verification.task_id != task_id:
            raise ValidationError(f"Verification task_id mismatch: {verification.task_id} != {task_id}")
        self._enforce_compute_access(
            actor_id=verification.verifier_id,
            capability="proof.verify",
            foundup_id=task.foundup_id,
            reason="verify_proof",
        )

        # Save verification
        self._adapter.create_verification(verification)

        if not verification.approved:
            # Rejected - emit event but don't transition
            self._emit_event(
                event_type="proof.rejected",
                actor_id=verification.verifier_id,
                payload={"reason": verification.reason, "approved": False},
                foundup_id=task.foundup_id,
                task_id=task_id,
            )
            raise ValidationError(f"Proof rejected: {verification.reason}")

        # Approved - transition to VERIFIED
        task.status = TaskStatus.VERIFIED
        task.verification_id = verification.verification_id

        updated = self._adapter.update_task(task)
        self._emit_event(
            event_type="proof.verified",
            actor_id=verification.verifier_id,
            payload={"reason": verification.reason, "approved": True},
            foundup_id=task.foundup_id,
            task_id=task_id,
        )
        logger.info("Task %s verified by %s", task_id, verification.verifier_id)
        return updated

    def trigger_payout(self, task_id: str, actor_id: str) -> Payout:
        """Record pending initiation atomically; an exact retry has no new effects.

        The task remains VERIFIED until a separate confirmed settlement owner
        exists. SQLite is required; this method grants no payment authority.
        """
        return self._adapter.initiate_payout(task_id, actor_id)

    def get_task(self, task_id: str) -> Task:
        """Get a task by ID.

        Args:
            task_id: ID of task to retrieve.

        Returns:
            Task record.

        Raises:
            NotFoundError: If task not found.
        """
        return self._adapter.get_task(task_id)

    def get_trace(self, task_id: str) -> Dict[str, object]:
        """Get complete trace of a task's lifecycle.

        Args:
            task_id: ID of task to trace.

        Returns:
            Dict with task, proof, verification, payout, and events.
        """
        task = self._adapter.get_task(task_id)

        trace: Dict[str, object] = {
            "task": {
                "task_id": task.task_id,
                "title": task.title,
                "status": task.status.value,
                "creator_id": task.creator_id,
                "assignee_id": task.assignee_id,
                "reward_amount": task.reward_amount,
                "created_at": task.created_at.isoformat(),
            }
        }

        # Add proof if exists
        if task.proof_id:
            try:
                proof = self._adapter.get_proof(task.proof_id)
                trace["proof"] = {
                    "proof_id": proof.proof_id,
                    "artifact_uri": proof.artifact_uri,
                    "artifact_hash": proof.artifact_hash,
                    "submitted_at": proof.submitted_at.isoformat(),
                }
            except NotFoundError:
                trace["proof"] = None

        # Add verification if exists
        if task.verification_id:
            try:
                verification = self._adapter.get_verification(task.verification_id)
                trace["verification"] = {
                    "verification_id": verification.verification_id,
                    "verifier_id": verification.verifier_id,
                    "approved": verification.approved,
                    "reason": verification.reason,
                    "verified_at": verification.verified_at.isoformat(),
                }
            except NotFoundError:
                trace["verification"] = None

        # Add payout if exists
        if task.payout_id:
            try:
                payout = self._adapter.get_payout(task.payout_id)
                trace["payout"] = {
                    "payout_id": payout.payout_id,
                    "amount": payout.amount,
                    "status": payout.status.value,
                    "reference": payout.reference,
                    "paid_at": payout.paid_at.isoformat() if payout.paid_at else None,
                }
            except NotFoundError:
                trace["payout"] = None

        # Add events
        events = self._adapter.query_events(task_id=task_id, limit=50)
        trace["events"] = [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "actor_id": e.actor_id,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ]

        return trace


# Keep stub for backwards compatibility
class TaskPipelineStub(TaskPipelineService):
    """Stub implementation for testing (deprecated, use PersistentTaskPipeline)."""

    pass
