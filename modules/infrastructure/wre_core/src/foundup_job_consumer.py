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


# ---------------------------------------------------------------------------
# Drain Result with Retention Metadata
# ---------------------------------------------------------------------------


@dataclass
class DrainResult:
    """
    Result of draining the FoundUpJob queue with retention semantics.

    WSP 97 truth:
      - Only successful terminal jobs with receipts are cleared
      - Failed/incomplete jobs are retained with explicit reasons
      - No silent dropping of failures
    """

    results: List["ConsumerResult"]
    """All ConsumerResults from the drain operation."""

    cleared_job_ids: List[str]
    """Job IDs that were cleared (successful terminal with receipt)."""

    retained_job_ids: List[str]
    """Job IDs that were retained (failed/incomplete)."""

    retention_reasons: Dict[str, str]
    """Map of retained job_id -> retention reason."""

    cleared_count: int = 0
    """Number of jobs cleared."""

    retained_count: int = 0
    """Number of jobs retained."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for logging/JSON."""
        return {
            "results": [r.to_dict() for r in self.results],
            "cleared_job_ids": self.cleared_job_ids,
            "retained_job_ids": self.retained_job_ids,
            "retention_reasons": self.retention_reasons,
            "cleared_count": self.cleared_count,
            "retained_count": self.retained_count,
        }


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
    def should_clear(self) -> bool:
        """
        True if job completed successfully and should be cleared from queue.

        Criteria for clearing (all must be true):
          - Dispatched to Hermes
          - Reached terminal state (succeeded/failed/blocked)
          - Receipt emitted successfully

        Jobs that fail routing, Hermes dispatch, or receipt emission
        are retained for retry or manual inspection.
        """
        return self.dispatched and self.is_terminal and self.has_receipt

    @property
    def retention_reason(self) -> Optional[str]:
        """
        Why this job should be retained (not cleared).

        Returns None if job should be cleared.
        """
        if self.should_clear:
            return None
        if not self.dispatched:
            if self.route_status == RouteStatus.FAILED:
                return "routing_failed"
            if self.route_status == RouteStatus.BLOCKED:
                return "routing_blocked"
            if self.route_status == RouteStatus.UNSUPPORTED:
                return "action_unsupported"
            return "not_dispatched"
        if not self.is_terminal:
            return "not_terminal"
        if not self.has_receipt:
            return "receipt_emission_failed"
        return "unknown"

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

        Args:
            clear: If True, clear successful jobs after draining. Default True.
                   Uses retention-aware clearing: only clears jobs that
                   completed successfully with receipt emission.

        Returns:
            List of ConsumerResult for each job in the queue.

        Note:
            This is a synchronous operation. No daemon loop.
            Failed/incomplete jobs are retained in the queue.
        """
        drain_result = self.drain_openclaw_queue_with_retention(clear=clear)
        return drain_result.results

    def drain_openclaw_queue_with_retention(self, clear: bool = True) -> DrainResult:
        """
        Drain the OpenClaw FoundUpJob queue with retention semantics.

        Only clears jobs that:
          - Were dispatched to Hermes
          - Reached terminal state (succeeded/failed/blocked)
          - Had receipt emitted successfully

        Jobs that fail routing, Hermes dispatch, or receipt emission
        are retained in the queue for retry or manual inspection.

        Args:
            clear: If True, clear successful jobs. Default True.
                   Failed jobs are always retained.

        Returns:
            DrainResult with full retention metadata.

        WSP 97 truth:
          - No silent dropping of failures
          - Explicit retention reasons for each retained job
        """
        try:
            from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
                get_job_queue,
                remove_jobs_by_id,
            )
        except ImportError as e:
            logger.error("[CONSUMER] OpenClaw orchestrator not available: %s", e)
            return DrainResult(
                results=[],
                cleared_job_ids=[],
                retained_job_ids=[],
                retention_reasons={},
                cleared_count=0,
                retained_count=0,
            )

        queue = get_job_queue()
        job_count = len(queue)

        if job_count == 0:
            logger.info("[CONSUMER] Queue empty, nothing to drain")
            return DrainResult(
                results=[],
                cleared_job_ids=[],
                retained_job_ids=[],
                retention_reasons={},
                cleared_count=0,
                retained_count=0,
            )

        logger.info("[CONSUMER] Draining %d job(s) from OpenClaw queue", job_count)

        # Drain all jobs
        results = self.drain_jobs(queue)

        # Classify results for retention
        cleared_job_ids: List[str] = []
        retained_job_ids: List[str] = []
        retention_reasons: Dict[str, str] = {}

        for result in results:
            if result.should_clear:
                cleared_job_ids.append(result.job_id)
            else:
                retained_job_ids.append(result.job_id)
                retention_reasons[result.job_id] = result.retention_reason or "unknown"

        # Remove only successful jobs if clear=True
        if clear and cleared_job_ids:
            removed = remove_jobs_by_id(cleared_job_ids)
            logger.info(
                "[CONSUMER] Cleared %d successful job(s); %d retained",
                removed,
                len(retained_job_ids),
            )

        if retained_job_ids:
            logger.warning(
                "[CONSUMER] Retained %d job(s) in queue: %s",
                len(retained_job_ids),
                {jid: retention_reasons[jid] for jid in retained_job_ids},
            )

        return DrainResult(
            results=results,
            cleared_job_ids=cleared_job_ids,
            retained_job_ids=retained_job_ids,
            retention_reasons=retention_reasons,
            cleared_count=len(cleared_job_ids),
            retained_count=len(retained_job_ids),
        )


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


def drain_openclaw_queue_dry_run(clear: bool = True) -> Dict[str, Any]:
    """
    Drain the OpenClaw FoundUpJob queue once in dry-run mode.

    Convenience function that:
      1. Creates a FoundUpJobConsumer(dry_run=True)
      2. Drains the OpenClaw queue with retention semantics
      3. Returns structured evidence including retention metadata

    Args:
        clear: If True, clear successful jobs after draining. Default True.
               Failed jobs are always retained.

    Returns:
        Dict containing:
          - job_count: Number of jobs drained
          - results: List of ConsumerResult.to_dict() for each job
          - dry_run: True (always)
          - cleared_job_ids: Jobs that were cleared
          - retained_job_ids: Jobs that were retained
          - retention_reasons: Map of retained job_id -> reason
          - summary: Aggregated stats

    WSP 97 truth boundaries:
      - dry_run=True always
      - verification_complete=False always
      - cabr_ready=False always
      - payout_ready=False always
      - No silent dropping of failures
    """
    consumer = FoundUpJobConsumer(dry_run=True)
    drain_result = consumer.drain_openclaw_queue_with_retention(clear=clear)

    # Aggregate stats
    dispatched_count = sum(1 for r in drain_result.results if r.dispatched)
    receipt_count = sum(1 for r in drain_result.results if r.has_receipt)
    terminal_count = sum(1 for r in drain_result.results if r.is_terminal)

    return {
        "job_count": len(drain_result.results),
        "results": [r.to_dict() for r in drain_result.results],
        "dry_run": True,
        "cleared_job_ids": drain_result.cleared_job_ids,
        "retained_job_ids": drain_result.retained_job_ids,
        "retention_reasons": drain_result.retention_reasons,
        "cleared_count": drain_result.cleared_count,
        "retained_count": drain_result.retained_count,
        "summary": {
            "dispatched": dispatched_count,
            "receipts_emitted": receipt_count,
            "terminal_jobs": terminal_count,
            "verification_complete": False,
            "cabr_ready": False,
            "payout_ready": False,
        },
    }
