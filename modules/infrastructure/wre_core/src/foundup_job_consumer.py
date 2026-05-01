# -*- coding: utf-8 -*-
"""
WRE FoundUpJob Consumer — Phase 1B Consumer Seam with Receipt Binding

Drains FoundUpJobs through the WRE routing pipeline without making
OpenClaw call Hermes directly. All dispatch goes through RouteEnvelope.

Architecture:
  OpenClaw -> FoundUpJob (QUEUED) -> WRE Router -> RouteEnvelope
           -> This Consumer -> Hermes Executor (if routed)
           -> Terminal Job -> Receipt Emitter -> pAVS Verification
           -> ConsumerResult (contains entire closed-loop evidence)

Phase 1B Enhancement:
  - ConsumerResult now carries receipt emission and pAVS verification
  - One ConsumerResult contains the complete closed-loop evidence chain
  - No need for callers to manually call receipt/pAVS APIs

WSP Compliance:
  WSP 11  : Interface contract (typed dispatch)
  WSP 50  : Pre-Action Verification (route_foundup_job validates first)
  WSP 77  : Agent Coordination (WRE controls dispatch, not OpenClaw)
  WSP 97  : System Execution Prompting (dry_run=True default, no overclaims)

NAVIGATION:
  -> Uses: foundup_job_router.py (route_foundup_job, RouteEnvelope)
  -> Uses: hermes_foundup_job_executor.py (execute_foundup_job)
  -> Uses: receipt_emitter.py (emit_receipt_for_terminal_job)
  -> Uses: openclaw_foundup_orchestrator.py (get_job_queue, clear_job_queue)
  -> Called by: WRE gateway, manual drain commands
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional

from .foundup_job_router import (
    RouteEnvelope,
    RouteStatus,
    TargetBackend,
    route_foundup_job,
)

if TYPE_CHECKING:
    from modules.communication.moltbot_bridge.src.receipt_emitter import (
        ReceiptEmissionResult,
    )

logger = logging.getLogger("wre_foundup_job_consumer")


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Consumer Result
# ---------------------------------------------------------------------------


@dataclass
class ConsumerResult:
    """
    Result container for a single job consumption.

    Phase 1B: Contains the complete closed-loop evidence chain:
      - Routing decision (envelope)
      - Hermes execution result (if dispatched)
      - Receipt emission result (if terminal)
      - pAVS verification result (via emission result)

    One ConsumerResult contains everything needed to audit the
    entire dry-run closed loop without manual API calls.

    WSP 97 Truth Boundaries:
      - receipt_emission.verification.verification_complete = False
      - receipt_emission.verification.cabr_ready = False
      - receipt_emission.verification.payout_ready = False
    """

    job_id: str
    """Job identifier."""

    dispatched: bool
    """True if job was dispatched to Hermes."""

    route_status: RouteStatus
    """Routing decision status."""

    target_backend: TargetBackend
    """Target backend from routing."""

    reason: str
    """Human-readable reason for result."""

    hermes_result: Optional[Any] = None
    """HermesJobExecutionResult if dispatched, else None."""

    envelope: Optional[RouteEnvelope] = None
    """RouteEnvelope from routing decision."""

    receipt_emission: Optional["ReceiptEmissionResult"] = None
    """
    Receipt emission result (if job reached terminal state).

    Contains:
      - receipt: ProofOfComputeReceipt with evidence_refs
      - verification: PAVSVerificationResult with truth fields

    None if job did not reach terminal state or was not dispatched.
    """

    consumed_at: datetime = field(default_factory=_utc_now)
    """Timestamp when consumption completed."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for logging/JSON."""
        result = {
            "job_id": self.job_id,
            "dispatched": self.dispatched,
            "route_status": self.route_status.value,
            "target_backend": self.target_backend.value,
            "reason": self.reason,
            "consumed_at": self.consumed_at.isoformat(),
            "receipt_emitted": self.receipt_emission is not None and self.receipt_emission.success,
        }
        # Include pAVS truth fields if available
        if self.receipt_emission and self.receipt_emission.verification:
            v = self.receipt_emission.verification
            result["verification_complete"] = v.verification_complete
            result["cabr_ready"] = v.cabr_ready
            result["payout_ready"] = v.payout_ready
        return result

    @property
    def is_terminal(self) -> bool:
        """True if job reached terminal state."""
        if self.hermes_result is None:
            return False
        job = getattr(self.hermes_result, "job", None)
        if job is None:
            return False
        status = getattr(job, "status", None)
        if status is None:
            return False
        return status.value in ("succeeded", "failed", "blocked")

    @property
    def has_receipt(self) -> bool:
        """True if receipt was emitted."""
        return self.receipt_emission is not None and self.receipt_emission.success

    @property
    def verification_complete(self) -> bool:
        """WSP 97: Always False - never claim final verification."""
        if self.receipt_emission and self.receipt_emission.verification:
            return self.receipt_emission.verification.verification_complete
        return False

    @property
    def cabr_ready(self) -> bool:
        """WSP 97: Always False - no CABR consensus exists."""
        if self.receipt_emission and self.receipt_emission.verification:
            return self.receipt_emission.verification.cabr_ready
        return False

    @property
    def payout_ready(self) -> bool:
        """WSP 97: Always False - no payout engine exists."""
        if self.receipt_emission and self.receipt_emission.verification:
            return self.receipt_emission.verification.payout_ready
        return False


# ---------------------------------------------------------------------------
# FoundUpJob Consumer
# ---------------------------------------------------------------------------


class FoundUpJobConsumer:
    """
    WRE-controlled consumer for FoundUpJobs.

    Drains jobs through the typed pipeline:
      1. route_foundup_job(job) -> RouteEnvelope
      2. Dispatch based on target_backend (only if ROUTED)
      3. Return result with execution outcome

    This is Phase 1A: synchronous operations only, no daemon loop.

    WSP 97 truth boundaries:
      - dry_run=True by default (no production execution)
      - Only ROUTED jobs dispatch to Hermes
      - QUEUED/BLOCKED/UNSUPPORTED do not execute

    Attributes:
        dry_run: If True, force dry-run mode for all Hermes dispatches.
    """

    def __init__(self, dry_run: bool = True):
        """
        Initialize consumer.

        Args:
            dry_run: Force dry-run mode for Hermes dispatches. Default True.
        """
        self.dry_run = dry_run

    def consume_one(self, job: Any) -> ConsumerResult:
        """
        Consume a single FoundUpJob through the pipeline.

        Steps:
          1. Route via route_foundup_job(job)
          2. If ROUTED to HERMES_*, dispatch to execute_foundup_job
          3. Return ConsumerResult with outcome

        Args:
            job: FoundUpJob instance to consume.

        Returns:
            ConsumerResult with dispatch outcome.
        """
        job_id = getattr(job, "job_id", "") or ""

        # Step 1: Route
        try:
            envelope = route_foundup_job(job)
        except Exception as e:
            logger.exception("[CONSUMER] Routing failed for job %s: %s", job_id, e)
            return ConsumerResult(
                job_id=job_id,
                dispatched=False,
                route_status=RouteStatus.FAILED,
                target_backend=TargetBackend.NONE,
                reason=f"Routing exception: {e}",
            )

        # Step 2: Dispatch based on target_backend
        if envelope.route_status == RouteStatus.ROUTED:
            if envelope.target_backend in (
                TargetBackend.HERMES_BUILDER,
                TargetBackend.HERMES_VALIDATOR,
            ):
                return self._dispatch_to_hermes(job, envelope)

        # Step 3: Not dispatched (QUEUED, BLOCKED, UNSUPPORTED, FAILED, etc.)
        logger.info(
            "[CONSUMER] Job %s not dispatched: status=%s backend=%s",
            job_id,
            envelope.route_status.value,
            envelope.target_backend.value,
        )
        return ConsumerResult(
            job_id=job_id,
            dispatched=False,
            route_status=envelope.route_status,
            target_backend=envelope.target_backend,
            reason=envelope.reason_human,
            envelope=envelope,
        )

    def _dispatch_to_hermes(
        self, job: Any, envelope: RouteEnvelope
    ) -> ConsumerResult:
        """
        Dispatch job to Hermes executor.

        Args:
            job: FoundUpJob to execute.
            envelope: RouteEnvelope from routing.

        Returns:
            ConsumerResult with Hermes execution outcome.
        """
        job_id = envelope.job_id

        try:
            # Import here to avoid circular deps at module load
            from modules.foundups.agent.src.hermes_foundup_job_executor import (
                execute_foundup_job,
                HermesJobExecutionResult,
            )

            logger.info(
                "[CONSUMER] Dispatching job %s to %s (dry_run=%s)",
                job_id,
                envelope.target_backend.value,
                self.dry_run,
            )

            hermes_result: HermesJobExecutionResult = execute_foundup_job(
                job, force_dry_run=self.dry_run
            )

            dispatched = True
            job_status = hermes_result.job.status.value
            reason = (
                f"Dispatched to {envelope.target_backend.value}; "
                f"job_status={job_status}"
            )

            logger.info(
                "[CONSUMER] Job %s completed: status=%s",
                job_id,
                job_status,
            )

            # Phase 1B: Emit receipt if job is terminal
            receipt_emission = self._emit_receipt_if_terminal(hermes_result.job, job_id)
            if receipt_emission:
                if receipt_emission.success:
                    reason += f"; receipt={receipt_emission.receipt.receipt_id}"
                else:
                    reason += f"; receipt_error={receipt_emission.error}"

            return ConsumerResult(
                job_id=job_id,
                dispatched=dispatched,
                route_status=envelope.route_status,
                target_backend=envelope.target_backend,
                reason=reason,
                hermes_result=hermes_result,
                envelope=envelope,
                receipt_emission=receipt_emission,
            )

        except ImportError as e:
            logger.error("[CONSUMER] Hermes executor not available: %s", e)
            return ConsumerResult(
                job_id=job_id,
                dispatched=False,
                route_status=envelope.route_status,
                target_backend=envelope.target_backend,
                reason=f"Hermes executor import failed: {e}",
                envelope=envelope,
            )

        except Exception as e:
            logger.exception("[CONSUMER] Hermes dispatch failed for job %s: %s", job_id, e)
            return ConsumerResult(
                job_id=job_id,
                dispatched=False,
                route_status=envelope.route_status,
                target_backend=envelope.target_backend,
                reason=f"Hermes dispatch exception: {e}",
                envelope=envelope,
            )

    def _emit_receipt_if_terminal(
        self, job: Any, job_id: str
    ) -> Optional["ReceiptEmissionResult"]:
        """
        Emit receipt and run pAVS verification if job is terminal.

        Args:
            job: The FoundUpJob after Hermes execution.
            job_id: Job identifier for logging.

        Returns:
            ReceiptEmissionResult if job is terminal, None otherwise.

        WSP 97 truth:
            - Only terminal jobs emit receipts
            - verification_complete=False always
            - cabr_ready=False always
            - payout_ready=False always
        """
        # Check if job is terminal
        status = getattr(job, "status", None)
        if status is None:
            return None

        status_value = status.value if hasattr(status, "value") else str(status)
        if status_value.lower() not in ("succeeded", "failed", "blocked"):
            logger.debug("[CONSUMER] Job %s not terminal (%s), skipping receipt", job_id, status_value)
            return None

        # Import receipt emitter
        try:
            from modules.communication.moltbot_bridge.src.receipt_emitter import (
                emit_receipt_for_terminal_job,
                ReceiptEmissionResult,
            )
        except ImportError as e:
            logger.error("[CONSUMER] Receipt emitter not available: %s", e)
            # Return a failure result without importing the class
            return None

        # Emit receipt (includes pAVS verification)
        try:
            emission_result = emit_receipt_for_terminal_job(job)

            if emission_result.success:
                logger.info(
                    "[CONSUMER] Receipt emitted for job %s: receipt=%s decision=%s",
                    job_id,
                    emission_result.receipt.receipt_id,
                    emission_result.verification.decision.value if emission_result.verification else "N/A",
                )
            else:
                logger.warning(
                    "[CONSUMER] Receipt emission failed for job %s: %s",
                    job_id,
                    emission_result.error,
                )

            return emission_result

        except Exception as e:
            logger.exception("[CONSUMER] Receipt emission exception for job %s: %s", job_id, e)
            # Return None rather than constructing a partial result
            return None

    def drain_jobs(self, jobs: Iterable[Any]) -> List[ConsumerResult]:
        """
        Drain multiple jobs through the pipeline.

        Args:
            jobs: Iterable of FoundUpJob instances.

        Returns:
            List of ConsumerResult for each job.
        """
        results = []
        for job in jobs:
            result = self.consume_one(job)
            results.append(result)
        return results

    def drain_openclaw_queue_once(self, clear: bool = True) -> List[ConsumerResult]:
        """
        Drain the OpenClaw FoundUpJob queue once.

        Imports the queue from openclaw_foundup_orchestrator, processes all
        jobs, and optionally clears the queue after successful processing.

        Args:
            clear: If True, clear the queue after draining. Default True.

        Returns:
            List of ConsumerResult for each job in the queue.

        Note:
            This is a synchronous operation. No daemon loop.
        """
        try:
            from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
                get_job_queue,
                clear_job_queue,
            )
        except ImportError as e:
            logger.error("[CONSUMER] OpenClaw orchestrator not available: %s", e)
            return []

        queue = get_job_queue()
        job_count = len(queue)

        if job_count == 0:
            logger.info("[CONSUMER] Queue empty, nothing to drain")
            return []

        logger.info("[CONSUMER] Draining %d job(s) from OpenClaw queue", job_count)

        # Drain all jobs
        results = self.drain_jobs(queue)

        # Clear queue only after successful drain (if requested)
        if clear:
            clear_job_queue()
            logger.info("[CONSUMER] Cleared OpenClaw queue after drain")

        return results


# ---------------------------------------------------------------------------
# Convenience: Get Consumer Instance
# ---------------------------------------------------------------------------


def get_consumer(dry_run: bool = True) -> FoundUpJobConsumer:
    """
    Get a FoundUpJobConsumer instance.

    Args:
        dry_run: Force dry-run mode for Hermes dispatches. Default True.

    Returns:
        Configured FoundUpJobConsumer.
    """
    return FoundUpJobConsumer(dry_run=dry_run)
