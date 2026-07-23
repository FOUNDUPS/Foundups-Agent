# -*- coding: utf-8 -*-
"""
WRE FoundUpJob Consumer — Phase 1B Consumer Seam with Receipt Binding

Drains FoundUpJobs through the WRE routing pipeline without making
OpenClaw call Hermes directly. All dispatch goes through RouteEnvelope.

Architecture:
  OpenClaw -> FoundUpJob (QUEUED) -> WRE Router -> RouteEnvelope
           -> This Consumer -> scaffold dry-run adapter OR Hermes Executor
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

import copy
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
from .foundup_scaffold_adapter import (
    CreateFoundUpDryRunScaffoldAdapter,
    ScaffoldAdapter,
)
from .foundup_scaffold_dispatch import dispatch_create_scaffold
from .foundup_scaffold_route_contract import canonical_json_copy

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

    retained_count: int = 0  # Number of jobs retained.
    def __post_init__(self) -> None:
        self.results = copy.deepcopy(list(self.results))
        self.cleared_job_ids = list(canonical_json_copy(self.cleared_job_ids))
        self.retained_job_ids = list(canonical_json_copy(self.retained_job_ids))
        self.retention_reasons = canonical_json_copy(self.retention_reasons)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for logging/JSON."""
        return {
            "results": canonical_json_copy([r.to_dict() for r in self.results]),
            "cleared_job_ids": canonical_json_copy(self.cleared_job_ids),
            "retained_job_ids": canonical_json_copy(self.retained_job_ids),
            "retention_reasons": canonical_json_copy(self.retention_reasons),
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

    Phase 1C: Checkpoint/evidence fields from WRE HermesJobExecutor:
      - checkpoint_state: Hermes swarm checkpoint state
      - checkpoint_result: Summary of work completed
      - evidence_path: Path to evidence directory

    One ConsumerResult contains everything needed to audit the
    entire dry-run closed loop without manual API calls.

    WSP 97 Truth Boundaries:
      - receipt_emission.verification.verification_complete = False
      - receipt_emission.verification.cabr_ready = False
      - receipt_emission.verification.payout_ready = False
      - real_execution_performed = False (Phase 1 dry-run seam)
    """

    job_id: str
    """Job identifier."""

    dispatched: bool
    """True if job was dispatched to its routed backend adapter."""

    route_status: RouteStatus
    """Routing decision status."""

    target_backend: TargetBackend
    """Target backend from routing."""

    reason: str
    """Human-readable reason for result."""

    hermes_result: Optional[Any] = None
    """HermesDelegationResult if dispatched via WRE executor, else None."""

    scaffold_result: Optional[Dict[str, Any]] = None
    """Verified create_foundup dry-run plan result, otherwise None."""

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

    # --- Phase 1C Checkpoint Protocol Fields ---
    checkpoint_state: Optional[str] = None
    """Hermes swarm checkpoint state (DONE|BLOCKED|NEEDS_INPUT|HANDOFF|SIMULATED)."""

    checkpoint_result: Optional[str] = None
    """Summary of work completed (if any)."""

    checkpoint_blocker: Optional[str] = None
    """Description of blocker (if BLOCKED)."""

    checkpoint_next_action: Optional[str] = None
    """Suggested next step."""

    evidence_path: Optional[str] = None
    """Path to evidence directory (.hermes_evidence/{job_id}/)."""

    real_execution_performed: bool = False
    """WSP 97: True ONLY if real delegate_task was called (never in Phase 1)."""

    context_bundle_dry_run: Optional[Dict[str, Any]] = None
    """
    WRE_CONTEXT_BUNDLE_DRYRUN_RUNTIME_WIRING_PHASE2: serialized DryRunResult.

    Carries the #786 ContextBundle dry-run preview
    (``DryRunResult.to_dict()``) when, and ONLY when, the seam took its
    PRE-EXISTING dry-run branch (Hermes execution status == SIMULATED and
    ``real_execution_performed`` is False, i.e. HERMES_DELEGATE_ENABLED
    unset/0). This is an OPTIONAL evidence field on the EXISTING
    ConsumerResult receipt -- NOT a new receipt type and NOT a new
    orchestrator. It is ``None`` on the real-exec / BLOCKED branch and
    whenever the bundle build / consume could not run (an observable error
    projection is recorded instead of raising). It contains refs + sha256
    only (no file bodies), source_authority="monorepo_poc", gate NAMES to
    re-check (never pass-state), and readiness flags all False.
    """

    consumed_at: datetime = field(default_factory=_utc_now)
    """Timestamp when consumption completed."""

    def __post_init__(self) -> None:
        """Detach nested JSON evidence from adapter and caller-owned objects."""
        if self.scaffold_result is not None:
            self.scaffold_result = canonical_json_copy(self.scaffold_result)
        if self.context_bundle_dry_run is not None:
            self.context_bundle_dry_run = canonical_json_copy(
                self.context_bundle_dry_run
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for logging/JSON."""
        return {
            "job_id": self.job_id,
            "dispatched": self.dispatched,
            "route_status": self.route_status.value,
            "target_backend": self.target_backend.value,
            "reason": self.reason,
            "scaffold_result": (
                canonical_json_copy(self.scaffold_result)
                if self.scaffold_result is not None
                else None
            ),
            "consumed_at": self.consumed_at.isoformat(),
            "receipt_emitted": self.receipt_emission is not None and self.receipt_emission.success,
            # Phase 1C Checkpoint Protocol Fields
            "checkpoint_state": self.checkpoint_state,
            "checkpoint_result": self.checkpoint_result,
            "checkpoint_blocker": self.checkpoint_blocker,
            "checkpoint_next_action": self.checkpoint_next_action,
            "evidence_path": self.evidence_path,
            "real_execution_performed": self.real_execution_performed,
            # WRE_CONTEXT_BUNDLE_DRYRUN_RUNTIME_WIRING_PHASE2 evidence (dry-run only)
            "context_bundle_dry_run": (
                canonical_json_copy(self.context_bundle_dry_run)
                if self.context_bundle_dry_run is not None
                else None
            ),
            # WSP 97 truth fields (always present via properties)
            "verification_complete": self.verification_complete,
            "cabr_ready": self.cabr_ready,
            "payout_ready": self.payout_ready,
        }

    @property
    def is_terminal(self) -> bool:
        """
        True if job reached terminal state.

        Terminal states for WRE HermesJobExecutor (HermesDelegationResult):
          - SIMULATED: Dry-run completed successfully
          - EXECUTED: Real execution completed (Phase 2+)
          - BLOCKED_*: Blocked by validation/gate/feature
          - ERROR_*: Execution error

        Legacy support for old HermesJobExecutionResult:
          - job.status.value in (succeeded, failed, blocked)
        """
        if self.scaffold_result is not None:
            return self.scaffold_result.get("ok") is True

        if self.hermes_result is None:
            return False

        # WRE executor returns HermesDelegationResult with .status enum
        status = getattr(self.hermes_result, "status", None)
        if status is not None:
            # Check if it's a HermesExecutionStatus enum value
            status_value = status.value if hasattr(status, "value") else str(status)
            terminal_prefixes = ("SIMULATED", "EXECUTED", "BLOCKED", "ERROR")
            return any(status_value.startswith(prefix) for prefix in terminal_prefixes)

        # Legacy: old executor returns result with .job.status
        job = getattr(self.hermes_result, "job", None)
        if job is None:
            return False
        job_status = getattr(job, "status", None)
        if job_status is None:
            return False
        return job_status.value in ("succeeded", "failed", "blocked")

    @property
    def has_receipt(self) -> bool:
        """True if receipt was emitted."""
        return self.receipt_emission is not None and self.receipt_emission.success

    @property
    def should_clear(self) -> bool:
        """
        True if job completed successfully and should be cleared from queue.

        Criteria for clearing (all must be true):
          - Dispatched to its routed backend adapter
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
            # WSP 97 truth: distinguish intentional skip from actual failure
            # Dry-run (SIMULATED) intentionally skips receipt emission
            if self.checkpoint_state == "SIMULATED" and not self.real_execution_performed:
                return "dry_run_evidence_only"
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
      - Only ROUTED jobs dispatch to a backend adapter
      - QUEUED/BLOCKED/UNSUPPORTED do not execute

    Attributes:
        dry_run: If True, force dry-run mode for all Hermes dispatches.
    """

    def __init__(
        self,
        dry_run: bool = True,
        scaffold_adapter: Optional[ScaffoldAdapter] = None,
    ):
        """
        Initialize consumer.

        Args:
            dry_run: Force dry-run mode for Hermes dispatches. Default True.
            scaffold_adapter: Injected create_foundup dry-run planning boundary.
        """
        self.dry_run = dry_run
        self.scaffold_adapter = (
            scaffold_adapter or CreateFoundUpDryRunScaffoldAdapter()
        )

    def consume_one(self, job: Any) -> ConsumerResult:
        """
        Consume a single FoundUpJob through the pipeline.

        Steps:
          1. Route via route_foundup_job(job)
          2. Dispatch HERMES_SCAFFOLD to the dry-run adapter; other HERMES_*
             backends use execute_foundup_job
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
            if envelope.target_backend == TargetBackend.HERMES_SCAFFOLD:
                return self._dispatch_to_scaffold(envelope)
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

    def _dispatch_to_scaffold(
        self,
        envelope: RouteEnvelope,
    ) -> ConsumerResult:
        """Dispatch only the immutable request snapshot carried by the route."""
        request = envelope.scaffold_request
        if request is None:
            return ConsumerResult(
                job_id=envelope.job_id,
                dispatched=False,
                route_status=RouteStatus.BLOCKED,
                target_backend=envelope.target_backend,
                reason="create_foundup route omitted its frozen request",
                envelope=envelope,
                checkpoint_state="BLOCKED",
                checkpoint_blocker="FAIL_SCAFFOLD_ROUTE_REQUEST",
            )

        outcome = dispatch_create_scaffold(
            self.scaffold_adapter,
            request,
            dry_run=self.dry_run,
        )
        return ConsumerResult(
            job_id=envelope.job_id,
            dispatched=outcome.dispatched,
            route_status=(
                envelope.route_status
                if outcome.dispatched
                else RouteStatus.BLOCKED
            ),
            target_backend=envelope.target_backend,
            reason=outcome.reason_human,
            envelope=envelope,
            scaffold_result=outcome.scaffold_result,
            checkpoint_state=outcome.checkpoint_state,
            checkpoint_result=outcome.checkpoint_result,
            checkpoint_blocker=outcome.checkpoint_blocker,
            real_execution_performed=False,
        )

    def _dispatch_to_hermes(
        self, job: Any, envelope: RouteEnvelope
    ) -> ConsumerResult:
        """
        Dispatch job to WRE Hermes executor dry-run seam.

        Phase 1C: Uses WRE HermesJobExecutor for checkpoint/evidence artifacts.
        Real execution is blocked in Phase 1 - all jobs return SIMULATED status.

        Args:
            job: FoundUpJob to execute.
            envelope: RouteEnvelope from routing.

        Returns:
            ConsumerResult with Hermes execution outcome and checkpoint fields.
        """
        job_id = envelope.job_id

        try:
            # Phase 1C: Import WRE executor instead of legacy path
            from modules.infrastructure.wre_core.src.hermes_job_executor import (
                execute_foundup_job,
                HermesDelegationResult,
            )

            logger.info(
                "[CONSUMER] Dispatching job %s to WRE executor (dry_run=%s)",
                job_id,
                self.dry_run,
            )

            # WRE executor respects dry_run via constructor, not per-call param
            # For Phase 1C, we always use dry_run=True (set in consumer init)
            hermes_result: HermesDelegationResult = execute_foundup_job(job)

            dispatched = True
            exec_status = hermes_result.status.value
            reason = (
                f"Dispatched to {envelope.target_backend.value}; "
                f"status={exec_status}"
            )

            logger.info(
                "[CONSUMER] Job %s completed: status=%s checkpoint=%s",
                job_id,
                exec_status,
                hermes_result.checkpoint_state,
            )

            # Phase 1B: Emit receipt if job is terminal
            # For WRE executor, check status instead of job.status
            receipt_emission = self._emit_receipt_for_hermes_result(
                job, hermes_result, job_id
            )
            if receipt_emission:
                if receipt_emission.success:
                    reason += f"; receipt={receipt_emission.receipt.receipt_id}"
                else:
                    reason += f"; receipt_error={receipt_emission.error}"

            # WRE_CONTEXT_BUNDLE_DRYRUN_RUNTIME_WIRING_PHASE2:
            # Attach the #786 ContextBundle dry-run preview ONLY on the
            # seam's PRE-EXISTING dry-run branch (SIMULATED + no real exec).
            # The real-exec / BLOCKED branch is untouched and contributes no
            # bundle evidence. This is the only runtime wiring of the dry-run
            # consumer into the existing dispatch seam; no new orchestrator,
            # no new receipt type, no second resolver, no real execution.
            context_bundle_dry_run = self._attach_context_bundle_dry_run(
                job, hermes_result, job_id
            )

            return ConsumerResult(
                job_id=job_id,
                dispatched=dispatched,
                route_status=envelope.route_status,
                target_backend=envelope.target_backend,
                reason=reason,
                hermes_result=hermes_result,
                envelope=envelope,
                receipt_emission=receipt_emission,
                # Phase 1C Checkpoint Protocol Fields
                checkpoint_state=hermes_result.checkpoint_state,
                checkpoint_result=hermes_result.checkpoint_result,
                checkpoint_blocker=hermes_result.checkpoint_blocker,
                checkpoint_next_action=hermes_result.checkpoint_next_action,
                evidence_path=hermes_result.evidence_path,
                real_execution_performed=hermes_result.real_execution_performed,
                context_bundle_dry_run=context_bundle_dry_run,
            )

        except ImportError as e:
            logger.error("[CONSUMER] WRE Hermes executor not available: %s", e)
            return ConsumerResult(
                job_id=job_id,
                dispatched=False,
                route_status=envelope.route_status,
                target_backend=envelope.target_backend,
                reason=f"WRE Hermes executor import failed: {e}",
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

    def _attach_context_bundle_dry_run(
        self, job: Any, hermes_result: Any, job_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Build the #786 ContextBundle dry-run preview on the dry-run branch ONLY.

        WRE_CONTEXT_BUNDLE_DRYRUN_RUNTIME_WIRING_PHASE2 (W6).

        This runs the read-only #775 ContextBundle producer and the #786
        ``consume_context_bundle_dry_run`` consumer and returns the
        serialized ``DryRunResult`` (``to_dict()``) for attachment to the
        EXISTING ``ConsumerResult`` receipt.

        Strict boundary (no overclaim, no real execution):
          - Runs ONLY when the seam took its PRE-EXISTING dry-run branch:
            the Hermes execution status is SIMULATED AND
            ``real_execution_performed`` is False (HERMES_DELEGATE_ENABLED
            unset/0). On the real-exec / BLOCKED branch this returns None
            and contributes no bundle evidence.
          - As a positive control, it also requires
            ``is_hermes_delegation_enabled()`` to be False so the wiring can
            never be reached with the live-delegation flag set.
          - The module_path is resolved ONLY through the single shared
            validated resolver (#778/#779). The bundle is built from the
            resolved manifest path. NO second resolver is defined here.
          - The #786 consumer receives the job so its shared-resolver
            cross-check / observable-ignore runs; a forged
            payload.module_path / source_module is rejected there and the
            rejected value is surfaced (never used) in the result.
          - NO subprocess, NO Hermes real delegation, NO file write, NO FAM
            event. The consumer is return-value-only.
          - Any failure (resolver reject, builder reject, consumer reject,
            import error) is captured as an OBSERVABLE error projection and
            returned; it NEVER raises into the dispatch path and NEVER
            promotes readiness.

        Returns:
            Serialized ``DryRunResult`` dict on the dry-run branch, an
            observable ``{"dry_run": True, "context_bundle_error": ...}``
            dict if the bundle could not be produced, or None when the
            branch is not the dry-run branch.
        """
        # --- Gate 1: only the PRE-EXISTING dry-run branch (SIMULATED, no real exec) ---
        status = getattr(hermes_result, "status", None)
        status_value = status.value if hasattr(status, "value") else str(status)
        real_exec = getattr(hermes_result, "real_execution_performed", False)
        if status_value != "SIMULATED" or real_exec:
            # Real-exec / BLOCKED / error branch: no bundle evidence attached.
            return None

        # --- Gate 2: positive control -- live delegation flag must be unset/0 ---
        try:
            from modules.infrastructure.wre_core.src.hermes_job_executor import (
                is_hermes_delegation_enabled,
            )
        except ImportError as exc:  # pragma: no cover - defensive
            return {
                "dry_run": True,
                "real_execution_performed": False,
                "context_bundle_error": f"flag_check_import_failed: {type(exc).__name__}",
            }
        if is_hermes_delegation_enabled():
            # Not the dry-run branch by flag; do not attach (defensive).
            return None

        # --- Build + consume the bundle (return-value-only; no side effects) ---
        try:
            from pathlib import Path as _Path

            from modules.foundups.agent.src.module_path_resolution import (
                DEFAULT_REPO_ROOT,
                _resolve_validated_module_path,
            )
            from modules.foundups.agent.src.context_bundle_builder import (
                build_context_bundle,
            )
            from modules.foundups.agent.src.context_bundle_dry_run_consumer import (
                DryRunConsumerRejected,
                consume_context_bundle_dry_run,
            )
        except ImportError as exc:
            logger.info(
                "[CONSUMER] ContextBundle dry-run wiring unavailable for job %s: %s",
                job_id,
                exc,
            )
            return {
                "dry_run": True,
                "real_execution_performed": False,
                "context_bundle_error": f"import_unavailable: {type(exc).__name__}",
            }

        repo_root = DEFAULT_REPO_ROOT

        # Resolve module_path via the SINGLE shared validated resolver. The
        # manifest path is derived from the validated canonical path; the
        # bundle is built from that manifest. No payload value is trusted.
        try:
            resolved = _resolve_validated_module_path(job, repo_root)
        except Exception as exc:  # pragma: no cover - resolver is fail-closed
            return {
                "dry_run": True,
                "real_execution_performed": False,
                "context_bundle_error": f"resolver_exception: {type(exc).__name__}",
            }
        if resolved.failed or not resolved.effective:
            return {
                "dry_run": True,
                "real_execution_performed": False,
                "context_bundle_error": "module_path_resolution_failed",
                "fail_token": resolved.fail_token,
                "payload_module_path_ignored": resolved.ignored,
            }

        manifest_path = _Path(repo_root) / resolved.effective / "foundup_manifest.json"

        # created_at: the builder requires a string; it is NOT used for
        # bundle_id (sha256-derived). Use a wall-clock ISO value for
        # provenance only.
        created_at = _utc_now().isoformat()

        try:
            bundle = build_context_bundle(
                manifest_path, repo_root, created_at=created_at
            )
        except Exception as exc:
            return {
                "dry_run": True,
                "real_execution_performed": False,
                "context_bundle_error": f"bundle_build_rejected: {type(exc).__name__}",
            }

        try:
            dry_run_result = consume_context_bundle_dry_run(
                bundle, job=job, repo_root=repo_root
            )
        except DryRunConsumerRejected as exc:
            # Non-monorepo_poc, forged payload, or readiness promotion: the
            # consumer refused. Surface the refusal as observable evidence;
            # never promote, never raise into dispatch.
            return {
                "dry_run": True,
                "real_execution_performed": False,
                "context_bundle_error": f"consumer_rejected: {type(exc).__name__}",
            }
        except Exception as exc:  # pragma: no cover - defensive
            return {
                "dry_run": True,
                "real_execution_performed": False,
                "context_bundle_error": f"consumer_exception: {type(exc).__name__}",
            }

        logger.info(
            "[CONSUMER] ContextBundle dry-run preview attached for job %s "
            "(module_path=%s, source_authority=%s)",
            job_id,
            dry_run_result.resolved_module_path,
            dry_run_result.source_authority,
        )
        return dry_run_result.to_dict()

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

    def _emit_receipt_for_hermes_result(
        self, job: Any, hermes_result: Any, job_id: str
    ) -> Optional["ReceiptEmissionResult"]:
        """
        Emit receipt based on WRE HermesDelegationResult status.

        Phase 1C: WRE executor returns HermesDelegationResult with checkpoint/evidence.
        Receipt emission is only attempted if the execution status is terminal
        AND the underlying job reached terminal state.

        Args:
            job: The original FoundUpJob (may not have terminal status in dry-run).
            hermes_result: HermesDelegationResult from WRE executor.
            job_id: Job identifier for logging.

        Returns:
            ReceiptEmissionResult if terminal and receipt emittable, None otherwise.

        WSP 97 truth:
            - Dry-run jobs (SIMULATED status) with non-terminal job state -> no receipt
            - Only real terminal jobs emit receipts
            - Evidence is captured in checkpoint fields, not receipts for dry-run
        """
        # Check HermesDelegationResult status
        status = getattr(hermes_result, "status", None)
        if status is None:
            logger.debug("[CONSUMER] Job %s has no status in hermes_result", job_id)
            return None

        status_value = status.value if hasattr(status, "value") else str(status)

        # Check if execution reached a terminal-like state
        terminal_prefixes = ("SIMULATED", "EXECUTED", "BLOCKED", "ERROR")
        is_exec_terminal = any(status_value.startswith(prefix) for prefix in terminal_prefixes)

        if not is_exec_terminal:
            logger.debug(
                "[CONSUMER] Job %s execution not terminal (%s), skipping receipt",
                job_id,
                status_value,
            )
            return None

        # WSP 97: For dry-run (SIMULATED), evidence is in checkpoint/evidence files
        # Receipt emission requires underlying job to have terminal status
        # In Phase 1, job status is NOT mutated by WRE executor
        if status_value == "SIMULATED":
            real_exec = getattr(hermes_result, "real_execution_performed", False)
            if not real_exec:
                logger.info(
                    "[CONSUMER] Job %s simulated (dry-run), evidence in checkpoint files. "
                    "Receipt emission skipped (WSP 97: no overclaim).",
                    job_id,
                )
                # Return None - evidence is in hermes_result.evidence_path
                return None

        # For EXECUTED or error states, delegate to standard receipt emission
        return self._emit_receipt_if_terminal(job, job_id)

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
