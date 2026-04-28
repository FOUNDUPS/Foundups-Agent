# -*- coding: utf-8 -*-
"""
WRE FoundUpJob Consumer — Phase 1A Consumer Seam

Drains FoundUpJobs through the WRE routing pipeline without making
OpenClaw call Hermes directly. All dispatch goes through RouteEnvelope.

Architecture:
  OpenClaw -> FoundUpJob (QUEUED) -> WRE Router -> RouteEnvelope
           -> This Consumer -> Hermes Executor (if routed)
           -> Terminal Job -> Receipt Emitter

This is Phase 1A: synchronous drain only, no daemon loop.

WSP Compliance:
  WSP 11  : Interface contract (typed dispatch)
  WSP 50  : Pre-Action Verification (route_foundup_job validates first)
  WSP 77  : Agent Coordination (WRE controls dispatch, not OpenClaw)
  WSP 97  : System Execution Prompting (dry_run=True default, no overclaims)

NAVIGATION:
  -> Uses: foundup_job_router.py (route_foundup_job, RouteEnvelope)
  -> Uses: hermes_foundup_job_executor.py (execute_foundup_job)
  -> Uses: openclaw_foundup_orchestrator.py (get_job_queue, clear_job_queue)
  -> Called by: WRE gateway, manual drain commands
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from .foundup_job_router import (
    RouteEnvelope,
    RouteStatus,
    TargetBackend,
    route_foundup_job,
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

    Wraps the HermesJobExecutionResult (if dispatched) or records
    why the job was not dispatched.
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

    consumed_at: datetime = field(default_factory=_utc_now)
    """Timestamp when consumption completed."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for logging/JSON."""
        return {
            "job_id": self.job_id,
            "dispatched": self.dispatched,
            "route_status": self.route_status.value,
            "target_backend": self.target_backend.value,
            "reason": self.reason,
            "consumed_at": self.consumed_at.isoformat(),
        }


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
            reason = (
                f"Dispatched to {envelope.target_backend.value}; "
                f"job_status={hermes_result.job.status.value}"
            )

            logger.info(
                "[CONSUMER] Job %s completed: status=%s",
                job_id,
                hermes_result.job.status.value,
            )

            return ConsumerResult(
                job_id=job_id,
                dispatched=dispatched,
                route_status=envelope.route_status,
                target_backend=envelope.target_backend,
                reason=reason,
                hermes_result=hermes_result,
                envelope=envelope,
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
