#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hermes FoundUpJob Executor Adapter — WSP 97-Safe Seam.

Adapter layer mapping FoundUpJob contract to Hermes delegate_task interface.
Does NOT consume jobs or execute real subagents by default.

Architecture:
  FoundUpJob (queued) → HermesJobExecutor → HermesDelegationRequest → [dry_run result]
                                                                    ↘ [real execution blocked]

Feature Flag:
  HERMES_DELEGATE_ENABLED=0 (default): Simulation only, no real delegate_task calls
  HERMES_DELEGATE_ENABLED=1: Blocked with explicit message (Phase 2 implementation)

WSP Compliance:
  WSP 11  : Interface contract (typed request/result)
  WSP 50  : Pre-Action Verification (lazy import, validation)
  WSP 97  : Truth boundaries (no false CABR/verification/payout claims)

NAVIGATION:
  -> Uses: modules/communication/moltbot_bridge/src/foundup_job_contract.py (FoundUpJob)
  -> Imports: vendor/hermes-agent/tools/delegate_tool.py (lazy, when enabled)
  -> Called by: Future FoundUpJobConsumer integration

Slice: HERMES_JOB_EXECUTOR_ADAPTER_PHASE1
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.communication.moltbot_bridge.src.foundup_job_contract import (
        FoundUpJob,
        PolicyFlags,
    )

logger = logging.getLogger("hermes_job_executor")


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Feature Flag
# ---------------------------------------------------------------------------

_HERMES_DELEGATE_ENABLED_KEY = "HERMES_DELEGATE_ENABLED"


def is_hermes_delegation_enabled() -> bool:
    """Check if Hermes delegation is enabled via environment flag."""
    value = os.environ.get(_HERMES_DELEGATE_ENABLED_KEY, "0")
    return value.strip().lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Execution Status Codes
# ---------------------------------------------------------------------------


class HermesExecutionStatus(str, Enum):
    """Status codes for Hermes delegation execution."""

    # Success (Phase 2+)
    EXECUTED = "EXECUTED"

    # Simulation (dry_run=True or feature flag disabled)
    SIMULATED = "SIMULATED"

    # Blocked states
    BLOCKED_FEATURE_DISABLED = "BLOCKED_FEATURE_DISABLED"
    BLOCKED_IMPORT_UNAVAILABLE = "BLOCKED_IMPORT_UNAVAILABLE"
    BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED = "BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED"
    BLOCKED_INVALID_JOB = "BLOCKED_INVALID_JOB"
    BLOCKED_UNSUPPORTED_ACTION = "BLOCKED_UNSUPPORTED_ACTION"

    # Error states
    ERROR_DELEGATION_FAILED = "ERROR_DELEGATION_FAILED"
    ERROR_UNEXPECTED = "ERROR_UNEXPECTED"


# ---------------------------------------------------------------------------
# Hermes Delegation Request (outbound contract)
# ---------------------------------------------------------------------------


@dataclass
class HermesDelegationRequest:
    """
    Outbound request to Hermes delegate_task.

    Maps FoundUpJob fields to Hermes delegate_task parameters.
    This is the contract between WRE and Hermes delegation layer.

    Attributes:
        goal: Task goal derived from requested_action
        context: Serialized job context including payload
        toolsets: Hermes toolsets to enable (default: none for dry_run)
        max_iterations: Max delegation iterations
        job_id: Source FoundUpJob.job_id for correlation
        foundup_id: Target FoundUp (optional)
        tenant_id: Actor scope
        requested_action: Original action requested
        policy_snapshot: Frozen policy_flags at request time
        dry_run: If True, Hermes should not execute terminal/file tools
    """

    # Core delegation params
    goal: str
    context: str
    toolsets: List[str] = field(default_factory=list)
    max_iterations: int = 50

    # Correlation fields
    job_id: str = ""
    foundup_id: Optional[str] = None
    tenant_id: str = ""
    requested_action: str = ""

    # Policy snapshot
    policy_snapshot: Dict[str, bool] = field(default_factory=dict)

    # Execution control
    dry_run: bool = True

    # Metadata
    created_at: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for logging/audit."""
        return {
            "goal": self.goal,
            "context": self.context,
            "toolsets": self.toolsets,
            "max_iterations": self.max_iterations,
            "job_id": self.job_id,
            "foundup_id": self.foundup_id,
            "tenant_id": self.tenant_id,
            "requested_action": self.requested_action,
            "policy_snapshot": self.policy_snapshot,
            "dry_run": self.dry_run,
            "created_at": self.created_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# Hermes Delegation Result (inbound contract)
# ---------------------------------------------------------------------------


@dataclass
class HermesDelegationResult:
    """
    Result from Hermes delegation attempt.

    Contains execution status, timing, and WSP 97-compliant truth fields.

    Attributes:
        status: HermesExecutionStatus code
        status_reason: Human-readable explanation
        request: Original HermesDelegationRequest
        delegate_response: Raw Hermes delegate_task response (if executed)
        duration_seconds: Wall clock time
        api_calls: Number of Hermes API calls (0 if simulated)

        WSP 97 Truth Fields:
        real_execution_performed: True ONLY if delegate_task was called
        verification_complete: Always False (no CABR verification yet)
        cabr_ready: Always False (no CABR pipeline integration)
        payout_ready: Always False (no payout pipeline integration)
    """

    # Core result
    status: HermesExecutionStatus
    status_reason: str

    # Request correlation
    request: Optional[HermesDelegationRequest] = None

    # Hermes response (if executed)
    delegate_response: Optional[Dict[str, Any]] = None

    # Metrics
    duration_seconds: float = 0.0
    api_calls: int = 0

    # WSP 97 Truth Fields - NEVER set to True in this adapter
    real_execution_performed: bool = False
    verification_complete: bool = False
    cabr_ready: bool = False
    payout_ready: bool = False

    # Metadata
    completed_at: datetime = field(default_factory=_utc_now)
    executor_version: str = "0.1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for logging/audit."""
        return {
            "status": self.status.value,
            "status_reason": self.status_reason,
            "request": self.request.to_dict() if self.request else None,
            "delegate_response": self.delegate_response,
            "duration_seconds": self.duration_seconds,
            "api_calls": self.api_calls,
            "real_execution_performed": self.real_execution_performed,
            "verification_complete": self.verification_complete,
            "cabr_ready": self.cabr_ready,
            "payout_ready": self.payout_ready,
            "completed_at": self.completed_at.isoformat(),
            "executor_version": self.executor_version,
        }


# ---------------------------------------------------------------------------
# Hermes Job Executor
# ---------------------------------------------------------------------------


class HermesJobExecutor:
    """
    Adapter mapping FoundUpJob -> Hermes delegate_task contract.

    This executor is a seam only - it does NOT:
      - Consume jobs from any queue
      - Start real Hermes subagents (blocked by design)
      - Modify FoundUpJob state
      - Interact with FAM pipeline

    It DOES:
      - Build HermesDelegationRequest from FoundUpJob
      - Validate job structure
      - Respect HERMES_DELEGATE_ENABLED feature flag
      - Return WSP 97-compliant HermesDelegationResult
      - Lazy-import Hermes delegate_task (only if enabled)

    Usage:
        executor = HermesJobExecutor(dry_run=True)
        result = executor.execute(job)
        if result.status == HermesExecutionStatus.SIMULATED:
            # Dry-run completed, no real delegation
            pass
    """

    def __init__(
        self,
        dry_run: bool = True,
        max_iterations: int = 50,
        default_toolsets: Optional[List[str]] = None,
    ):
        """
        Initialize executor.

        Args:
            dry_run: If True (default), never call real delegate_task
            max_iterations: Default iteration limit for Hermes
            default_toolsets: Default toolsets (empty by default for safety)
        """
        self.dry_run = dry_run
        self.max_iterations = max_iterations
        self.default_toolsets = default_toolsets or []
        self._delegate_task_fn = None
        self._import_attempted = False
        self._import_error: Optional[str] = None

    def _lazy_import_delegate_task(self) -> bool:
        """
        Lazy-load Hermes delegate_task function.

        Returns:
            True if import succeeded, False otherwise
        """
        if self._import_attempted:
            return self._delegate_task_fn is not None

        self._import_attempted = True

        try:
            from vendor.hermes_agent.tools.delegate_tool import delegate_task

            self._delegate_task_fn = delegate_task
            logger.info("[HERMES-EXEC] delegate_task imported successfully")
            return True
        except ImportError as exc:
            self._import_error = str(exc)
            logger.warning(
                "[HERMES-EXEC] Failed to import delegate_task: %s",
                exc,
            )
            return False
        except Exception as exc:
            self._import_error = f"Unexpected error: {exc}"
            logger.error(
                "[HERMES-EXEC] Unexpected import error: %s",
                exc,
            )
            return False

    def build_delegation_request(
        self,
        job: "FoundUpJob",
    ) -> HermesDelegationRequest:
        """
        Build HermesDelegationRequest from FoundUpJob.

        Maps job fields to Hermes delegate_task contract.

        Args:
            job: Source FoundUpJob

        Returns:
            HermesDelegationRequest ready for delegation
        """
        import json

        # Build goal from requested_action
        goal = self._build_goal(job)

        # Build context from job fields
        context = self._build_context(job)

        # Snapshot policy flags
        policy_snapshot = job.policy_flags.to_dict() if job.policy_flags else {}

        return HermesDelegationRequest(
            goal=goal,
            context=context,
            toolsets=list(self.default_toolsets),
            max_iterations=self.max_iterations,
            job_id=job.job_id,
            foundup_id=job.foundup_id,
            tenant_id=job.tenant_id,
            requested_action=job.requested_action,
            policy_snapshot=policy_snapshot,
            dry_run=self.dry_run,
        )

    def _build_goal(self, job: "FoundUpJob") -> str:
        """Build goal string from job."""
        action = job.requested_action or "execute_job"
        foundup_id = job.foundup_id or "(unspecified)"

        # Map actions to goal templates
        goal_templates = {
            "build_foundup": f"Build FoundUp '{foundup_id}' according to specification",
            "extract_foundup": f"Extract FoundUp '{foundup_id}' to external repository",
            "validate_foundup": f"Validate FoundUp '{foundup_id}' manifest and gates",
            "queue_foundup_job": f"Queue job for FoundUp '{foundup_id}'",
        }

        return goal_templates.get(
            action,
            f"Execute action '{action}' for FoundUp '{foundup_id}'",
        )

    def _build_context(self, job: "FoundUpJob") -> str:
        """Build context string from job payload and metadata."""
        import json

        context_parts = [
            f"Job ID: {job.job_id}",
            f"Tenant: {job.tenant_id}",
            f"Action: {job.requested_action}",
        ]

        if job.foundup_id:
            context_parts.append(f"FoundUp ID: {job.foundup_id}")

        if job.intent_id:
            context_parts.append(f"Intent ID: {job.intent_id}")

        if job.payload:
            # Include payload summary (truncated for context efficiency)
            payload_json = json.dumps(job.payload, default=str)
            if len(payload_json) > 1000:
                payload_json = payload_json[:1000] + "... (truncated)"
            context_parts.append(f"Payload: {payload_json}")

        return "\n".join(context_parts)

    def execute(self, job: "FoundUpJob") -> HermesDelegationResult:
        """
        Execute (or simulate) FoundUpJob via Hermes delegation.

        Decision tree:
          1. Validate job structure
          2. Build delegation request
          3. Check feature flag
          4. If disabled or dry_run: return SIMULATED
          5. If enabled and not dry_run: return BLOCKED (Phase 2)

        Args:
            job: FoundUpJob to execute

        Returns:
            HermesDelegationResult with execution outcome
        """
        import time

        start_time = time.monotonic()

        # Step 1: Validate job
        validation_error = self._validate_job(job)
        if validation_error:
            return HermesDelegationResult(
                status=HermesExecutionStatus.BLOCKED_INVALID_JOB,
                status_reason=validation_error,
                duration_seconds=time.monotonic() - start_time,
            )

        # Step 2: Build request
        request = self.build_delegation_request(job)

        # Step 3: Check feature flag
        if not is_hermes_delegation_enabled():
            logger.info(
                "[HERMES-EXEC] Feature disabled, simulating job %s",
                job.job_id,
            )
            return HermesDelegationResult(
                status=HermesExecutionStatus.SIMULATED,
                status_reason=(
                    f"Hermes delegation disabled ({_HERMES_DELEGATE_ENABLED_KEY}=0). "
                    f"Job {job.job_id} simulated, no real execution."
                ),
                request=request,
                duration_seconds=time.monotonic() - start_time,
                real_execution_performed=False,
                verification_complete=False,
                cabr_ready=False,
                payout_ready=False,
            )

        # Step 4: Feature enabled - check dry_run
        if self.dry_run:
            logger.info(
                "[HERMES-EXEC] dry_run=True, simulating job %s",
                job.job_id,
            )
            return HermesDelegationResult(
                status=HermesExecutionStatus.SIMULATED,
                status_reason=(
                    f"dry_run=True, job {job.job_id} simulated. "
                    "Set dry_run=False for real execution (blocked in Phase 1)."
                ),
                request=request,
                duration_seconds=time.monotonic() - start_time,
                real_execution_performed=False,
                verification_complete=False,
                cabr_ready=False,
                payout_ready=False,
            )

        # Step 5: Check import availability
        if not self._lazy_import_delegate_task():
            return HermesDelegationResult(
                status=HermesExecutionStatus.BLOCKED_IMPORT_UNAVAILABLE,
                status_reason=(
                    f"Cannot import Hermes delegate_task: {self._import_error}. "
                    "Ensure vendor/hermes-agent is available."
                ),
                request=request,
                duration_seconds=time.monotonic() - start_time,
                real_execution_performed=False,
            )

        # Step 6: Real execution blocked in Phase 1
        logger.warning(
            "[HERMES-EXEC] Real delegation NOT IMPLEMENTED, blocking job %s",
            job.job_id,
        )
        return HermesDelegationResult(
            status=HermesExecutionStatus.BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED,
            status_reason=(
                f"Real Hermes delegation not implemented in Phase 1. "
                f"Job {job.job_id} blocked. Enable terminal/file toolsets in Phase 2."
            ),
            request=request,
            duration_seconds=time.monotonic() - start_time,
            real_execution_performed=False,
            verification_complete=False,
            cabr_ready=False,
            payout_ready=False,
        )

    def _validate_job(self, job: "FoundUpJob") -> Optional[str]:
        """
        Validate job structure before delegation.

        Returns:
            Error message if invalid, None if valid
        """
        if not job:
            return "Job is None"

        if not job.job_id or not job.job_id.strip():
            return "Job missing job_id"

        if not job.tenant_id or not job.tenant_id.strip():
            return "Job missing tenant_id"

        if not job.requested_action or not job.requested_action.strip():
            return "Job missing requested_action"

        return None


# ---------------------------------------------------------------------------
# Module-Level Convenience Functions
# ---------------------------------------------------------------------------

_executor_singleton: Optional[HermesJobExecutor] = None


def get_executor(
    dry_run: bool = True,
    max_iterations: int = 50,
) -> HermesJobExecutor:
    """Get or create singleton HermesJobExecutor."""
    global _executor_singleton
    if _executor_singleton is None:
        _executor_singleton = HermesJobExecutor(
            dry_run=dry_run,
            max_iterations=max_iterations,
        )
    return _executor_singleton


def execute_foundup_job(job: "FoundUpJob") -> HermesDelegationResult:
    """
    Convenience function to execute FoundUpJob via Hermes.

    Uses default singleton executor with dry_run=True.
    """
    return get_executor().execute(job)
