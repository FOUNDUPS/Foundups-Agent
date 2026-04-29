#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BuildPlan Executor — Interface Stub for Controlled Step Execution

Implements the BuildPlanExecutor interface from BUILD_PLAN_EXECUTION_ADAPTER_CONTRACT.md.
This is an interface stub only. Real execution is NOT implemented.

WSP 97 TRUTH BOUNDARIES:
  - dry_run=True by default
  - Real execution (dry_run=False) returns BLOCKED
  - verification_complete=False always
  - cabr_ready=False always
  - payout_ready=False always
  - No actual file operations performed

Architecture:
  BuildPlan -> BuildPlanExecutor -> StepExecutionResult
           -> ExecutionReceipt (with WSP 97 truth fields)

WSP Compliance:
  WSP 11  : Interface contract (typed API)
  WSP 50  : Pre-action validation (validate_plan)
  WSP 77  : Agent coordination (gate evaluation)
  WSP 97  : Truth boundaries (no real execution)

NAVIGATION:
  -> Spec: modules/foundups/docs/BUILD_PLAN_EXECUTION_ADAPTER_CONTRACT.md
  -> Uses: build_plan.py (BuildPlan, BuildStep, GateType)
  -> Called by: Future orchestration (not implemented)
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .build_plan import (
    BuildMode,
    BuildPlan,
    BuildPlanStatus,
    BuildStep,
    BuildStepAction,
    GateType,
    GateStatus,
    StepStatus,
)

logger = logging.getLogger("build_plan_executor")


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class StepExecutionStatus(str, Enum):
    """Step execution outcome status."""

    SUCCEEDED = "succeeded"
    """Step completed successfully (simulation or execution)."""

    FAILED = "failed"
    """Step failed during execution."""

    BLOCKED = "blocked"
    """Step blocked by gate, scope, or policy."""

    SKIPPED = "skipped"
    """Step skipped (optional or condition not met)."""

    SIMULATED = "simulated"
    """Step was simulated (dry-run), not executed."""


class ExecutionMode(str, Enum):
    """Execution mode for the executor."""

    DRY_RUN = "dry_run"
    """Simulate steps, no real changes."""

    REAL = "real"
    """Real execution (NOT IMPLEMENTED)."""


class ExecutionBlockReason(str, Enum):
    """Reasons why execution may be blocked."""

    REAL_EXECUTION_NOT_IMPLEMENTED = "real_execution_not_implemented"
    """Real execution is not implemented in this stub."""

    MUTATING_ACTION_IN_STUB = "mutating_action_in_stub"
    """Mutating actions are blocked in stub implementation."""

    GATE_FAILED = "gate_failed"
    """A required gate did not pass."""

    HUMAN_APPROVAL_REQUIRED = "human_approval_required"
    """Human approval gate required but not passed."""

    SCOPE_VIOLATION = "scope_violation"
    """Operation outside allowed scope."""

    PLAN_NOT_VALID = "plan_not_valid"
    """Plan failed validation."""

    MODE_REAL_NOT_ALLOWED = "mode_real_not_allowed"
    """Plan has mode=REAL but approval not granted."""


# ---------------------------------------------------------------------------
# Actions that can be safely simulated
# ---------------------------------------------------------------------------

# Actions that only validate/read, do not mutate
SAFE_SIMULATION_ACTIONS: frozenset[BuildStepAction] = frozenset({
    BuildStepAction.VALIDATE_GENESIS,
    BuildStepAction.VALIDATE_MANIFEST,
    BuildStepAction.VALIDATE_STRUCTURE,
    BuildStepAction.RUN_TESTS,  # Tests can run in dry-run
})

# Actions that require file mutation (blocked in stub)
MUTATING_ACTIONS: frozenset[BuildStepAction] = frozenset({
    BuildStepAction.CREATE_SPEC,
    BuildStepAction.CREATE_TEST,
    BuildStepAction.CREATE_MODULE,
    BuildStepAction.CREATE_ADAPTERS,
    BuildStepAction.UPDATE_MANIFEST,
    BuildStepAction.UPDATE_MODLOG,
    BuildStepAction.UPDATE_TESTMODLOG,
})


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class DiffSummary:
    """Summary of file changes (planned or actual)."""

    files_created: int = 0
    files_modified: int = 0
    files_deleted: int = 0
    lines_added: int = 0
    lines_removed: int = 0

    def to_dict(self) -> Dict[str, int]:
        """Serialize to dictionary."""
        return {
            "files_created": self.files_created,
            "files_modified": self.files_modified,
            "files_deleted": self.files_deleted,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
        }


@dataclass
class StepExecutionContext:
    """Context for step execution."""

    plan: BuildPlan
    step: BuildStep
    step_index: int
    dry_run: bool = True
    target_files: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=utc_now)
    timeout_ms: int = 60000
    worker_id: str = "build_plan_executor"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "plan_id": self.plan.build_plan_id,
            "step_id": self.step.step_id,
            "step_index": self.step_index,
            "dry_run": self.dry_run,
            "target_files": self.target_files,
            "started_at": utc_iso(self.started_at),
            "timeout_ms": self.timeout_ms,
            "worker_id": self.worker_id,
        }


@dataclass
class StepExecutionResult:
    """Result of step execution."""

    # Identity
    step_id: str
    step_name: str
    action: BuildStepAction

    # Outcome
    status: StepExecutionStatus

    # Mode
    dry_run: bool = True
    simulated: bool = True

    # Evidence
    planned_diff: Optional[DiffSummary] = None
    actual_diff: Optional[DiffSummary] = None  # Always None in stub
    evidence_refs: List[str] = field(default_factory=list)

    # Timing
    started_at: datetime = field(default_factory=utc_now)
    completed_at: Optional[datetime] = None
    duration_ms: int = 0

    # Error
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "step_id": self.step_id,
            "step_name": self.step_name,
            "action": self.action.value,
            "status": self.status.value,
            "dry_run": self.dry_run,
            "simulated": self.simulated,
            "planned_diff": self.planned_diff.to_dict() if self.planned_diff else None,
            "actual_diff": self.actual_diff.to_dict() if self.actual_diff else None,
            "evidence_refs": self.evidence_refs,
            "started_at": utc_iso(self.started_at),
            "completed_at": utc_iso(self.completed_at),
            "duration_ms": self.duration_ms,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


@dataclass
class GateEvaluationResult:
    """Result of gate evaluation."""

    gate_id: str
    gate_type: GateType
    passed: bool
    reason: str
    checked_at: datetime = field(default_factory=utc_now)
    checked_by: str = "system"
    blocks_execution: bool = False
    requires_human: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "gate_id": self.gate_id,
            "gate_type": self.gate_type.value,
            "passed": self.passed,
            "reason": self.reason,
            "checked_at": utc_iso(self.checked_at),
            "checked_by": self.checked_by,
            "blocks_execution": self.blocks_execution,
            "requires_human": self.requires_human,
        }


@dataclass
class ValidationResult:
    """Result of plan validation."""

    valid: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "valid": self.valid,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "warnings": self.warnings,
        }


@dataclass
class ExecutionReceipt:
    """
    Receipt for BuildPlan execution.

    WSP 97 Truth Fields:
      - verification_complete = False (always)
      - cabr_ready = False (always)
      - payout_ready = False (always)
      - real_execution_performed = False (stub)
    """

    # Identity
    receipt_id: str
    plan_id: str
    source_job_id: Optional[str] = None

    # Correlation
    foundup_id: str = ""
    tenant_id: str = ""

    # Execution Summary
    mode: ExecutionMode = ExecutionMode.DRY_RUN
    total_steps: int = 0
    steps_succeeded: int = 0
    steps_failed: int = 0
    steps_blocked: int = 0
    steps_skipped: int = 0

    # Gates
    all_gates_passed: bool = False
    gates_evaluated: List[GateEvaluationResult] = field(default_factory=list)

    # Evidence
    step_results: List[StepExecutionResult] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)

    # Timestamps
    started_at: datetime = field(default_factory=utc_now)
    completed_at: Optional[datetime] = None

    # WSP 97 Truth Fields (ALWAYS these values)
    verification_complete: bool = False
    cabr_ready: bool = False
    payout_ready: bool = False
    real_execution_performed: bool = False

    def __post_init__(self) -> None:
        """Enforce WSP 97 truth fields."""
        # These MUST be False - cannot be overridden
        self.verification_complete = False
        self.cabr_ready = False
        self.payout_ready = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "receipt_id": self.receipt_id,
            "plan_id": self.plan_id,
            "source_job_id": self.source_job_id,
            "foundup_id": self.foundup_id,
            "tenant_id": self.tenant_id,
            "mode": self.mode.value,
            "total_steps": self.total_steps,
            "steps_succeeded": self.steps_succeeded,
            "steps_failed": self.steps_failed,
            "steps_blocked": self.steps_blocked,
            "steps_skipped": self.steps_skipped,
            "all_gates_passed": self.all_gates_passed,
            "gates_evaluated": [g.to_dict() for g in self.gates_evaluated],
            "step_results": [r.to_dict() for r in self.step_results],
            "evidence_refs": self.evidence_refs,
            "started_at": utc_iso(self.started_at),
            "completed_at": utc_iso(self.completed_at),
            # WSP 97 truth fields
            "verification_complete": self.verification_complete,
            "cabr_ready": self.cabr_ready,
            "payout_ready": self.payout_ready,
            "real_execution_performed": self.real_execution_performed,
        }


# ---------------------------------------------------------------------------
# BuildPlanExecutor
# ---------------------------------------------------------------------------


class BuildPlanExecutor:
    """
    BuildPlan Executor — Interface Stub.

    Translates BuildPlan steps into bounded operations.
    This is a stub: real execution is NOT implemented.

    WSP 97 Truth Boundaries:
      - dry_run=True by default
      - execute_step with dry_run=False returns BLOCKED
      - No actual file operations performed
      - No CABR/payout/reward fields
    """

    def __init__(self, dry_run: bool = True):
        """
        Initialize executor.

        Args:
            dry_run: Force dry-run mode. Default True.
        """
        self.dry_run = dry_run
        self._execution_id = f"exec_{secrets.token_hex(4)}"

    def is_dry_run(self) -> bool:
        """Check if executor is in dry-run mode."""
        return self.dry_run

    # ------------------------------------------------------------------
    # Plan Validation
    # ------------------------------------------------------------------

    def validate_plan(self, plan: BuildPlan) -> ValidationResult:
        """
        Validate a BuildPlan before execution.

        Checks:
          - Plan has required identity fields
          - Plan has target
          - mode=REAL requires human_approval_gate
          - Steps exist

        Args:
            plan: BuildPlan to validate.

        Returns:
            ValidationResult with validation outcome.
        """
        warnings = []

        # Check identity
        if not plan.build_plan_id:
            return ValidationResult(
                valid=False,
                error_code="MISSING_PLAN_ID",
                error_message="BuildPlan.build_plan_id is required",
            )

        if not plan.foundup_id:
            return ValidationResult(
                valid=False,
                error_code="MISSING_FOUNDUP_ID",
                error_message="BuildPlan.foundup_id is required",
            )

        # Check target
        if not plan.target:
            return ValidationResult(
                valid=False,
                error_code="MISSING_TARGET",
                error_message="BuildPlan.target is required",
            )

        # Check mode=REAL requires approval
        if plan.mode == BuildMode.REAL:
            human_gate = plan.get_gate(GateType.HUMAN_APPROVAL_GATE)
            if not human_gate or not human_gate.passed:
                return ValidationResult(
                    valid=False,
                    error_code="MODE_REAL_NO_APPROVAL",
                    error_message="mode=REAL requires human_approval_gate to be passed",
                )

        # Check steps exist
        if not plan.steps:
            warnings.append("Plan has no steps")

        # Warn about real execution
        if not plan.dry_run:
            warnings.append("Plan has dry_run=False but real execution is not implemented")

        return ValidationResult(
            valid=True,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Gate Evaluation
    # ------------------------------------------------------------------

    def evaluate_gate(
        self, plan: BuildPlan, gate_type: GateType
    ) -> GateEvaluationResult:
        """
        Evaluate a gate for the plan.

        Args:
            plan: BuildPlan being executed.
            gate_type: Type of gate to evaluate.

        Returns:
            GateEvaluationResult with evaluation outcome.
        """
        gate = plan.get_gate(gate_type)
        gate_id = gate.gate_id if gate else f"{gate_type.value}_auto"

        # Check if gate already passed in plan
        if gate and gate.passed:
            return GateEvaluationResult(
                gate_id=gate_id,
                gate_type=gate_type,
                passed=True,
                reason="Gate already passed in plan",
                checked_by="system",
            )

        # Evaluate based on gate type
        if gate_type == GateType.GENESIS_GATE:
            # Check target has module_path
            passed = plan.target is not None and bool(plan.target.module_path)
            reason = "Genesis validation: target exists" if passed else "No target defined"

        elif gate_type == GateType.DRY_RUN_GATE:
            # Dry-run gate passes if plan is dry-run
            passed = plan.dry_run
            reason = "Dry-run mode active" if passed else "Plan is not dry-run"

        elif gate_type == GateType.HUMAN_APPROVAL_GATE:
            # Human approval must be explicitly set
            passed = gate is not None and gate.passed
            reason = "Human approval granted" if passed else "Human approval required"
            return GateEvaluationResult(
                gate_id=gate_id,
                gate_type=gate_type,
                passed=passed,
                reason=reason,
                checked_by="system",
                blocks_execution=not passed,
                requires_human=True,
            )

        else:
            # Default: pass in stub (no real validation)
            passed = True
            reason = f"Gate {gate_type.value} auto-passed in stub"

        return GateEvaluationResult(
            gate_id=gate_id,
            gate_type=gate_type,
            passed=passed,
            reason=reason,
            checked_by="system",
            blocks_execution=gate.required if gate else False,
        )

    # ------------------------------------------------------------------
    # Step Simulation
    # ------------------------------------------------------------------

    def simulate_step(
        self, plan: BuildPlan, step: BuildStep
    ) -> StepExecutionResult:
        """
        Simulate a step without making changes.

        Args:
            plan: BuildPlan containing the step.
            step: BuildStep to simulate.

        Returns:
            StepExecutionResult with simulation outcome.
        """
        started_at = utc_now()

        # Check if action is safe to simulate
        if step.action in SAFE_SIMULATION_ACTIONS:
            # Safe actions: validation, tests
            status = StepExecutionStatus.SIMULATED
            planned_diff = DiffSummary()  # No changes
            error_code = None
            error_message = None

        elif step.action in MUTATING_ACTIONS:
            # Mutating actions: return simulated with planned_diff
            status = StepExecutionStatus.SIMULATED
            planned_diff = DiffSummary(
                files_created=len(step.target_files) if step.target_files else 1,
                lines_added=100,  # Placeholder estimate
            )
            error_code = None
            error_message = None

        else:
            # Other actions: simulate as pass
            status = StepExecutionStatus.SIMULATED
            planned_diff = DiffSummary()
            error_code = None
            error_message = None

        completed_at = utc_now()
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        return StepExecutionResult(
            step_id=step.step_id,
            step_name=step.step_name,
            action=step.action,
            status=status,
            dry_run=True,
            simulated=True,
            planned_diff=planned_diff,
            actual_diff=None,
            evidence_refs=[f"simulation/{plan.build_plan_id}/{step.step_id}"],
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            error_code=error_code,
            error_message=error_message,
        )

    # ------------------------------------------------------------------
    # Step Execution
    # ------------------------------------------------------------------

    def execute_step(
        self, plan: BuildPlan, step: BuildStep
    ) -> StepExecutionResult:
        """
        Execute a step.

        WSP 97: Real execution is NOT implemented.
          - If dry_run=True: delegates to simulate_step
          - If dry_run=False: returns BLOCKED

        Args:
            plan: BuildPlan containing the step.
            step: BuildStep to execute.

        Returns:
            StepExecutionResult with execution outcome.
        """
        started_at = utc_now()

        # Dry-run mode: delegate to simulation
        if self.dry_run:
            return self.simulate_step(plan, step)

        # Real execution: BLOCKED (not implemented)
        completed_at = utc_now()
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        logger.warning(
            "[EXECUTOR] Real execution blocked for step %s: not implemented",
            step.step_id,
        )

        return StepExecutionResult(
            step_id=step.step_id,
            step_name=step.step_name,
            action=step.action,
            status=StepExecutionStatus.BLOCKED,
            dry_run=False,
            simulated=False,
            planned_diff=None,
            actual_diff=None,
            evidence_refs=[],
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            error_code=ExecutionBlockReason.REAL_EXECUTION_NOT_IMPLEMENTED.value,
            error_message="Real execution is not implemented. Use dry_run=True.",
        )

    # ------------------------------------------------------------------
    # Execution Receipt
    # ------------------------------------------------------------------

    def create_execution_receipt(
        self,
        plan: BuildPlan,
        results: List[StepExecutionResult],
    ) -> ExecutionReceipt:
        """
        Create an ExecutionReceipt from plan and step results.

        WSP 97 Truth Fields:
          - verification_complete = False (always)
          - cabr_ready = False (always)
          - payout_ready = False (always)
          - real_execution_performed = False (stub)

        Args:
            plan: BuildPlan that was executed.
            results: List of StepExecutionResult from execution.

        Returns:
            ExecutionReceipt with all truth fields False.
        """
        receipt_id = f"rcpt_{plan.build_plan_id}_{secrets.token_hex(4)}"

        # Count step outcomes
        succeeded = sum(1 for r in results if r.status == StepExecutionStatus.SUCCEEDED)
        simulated = sum(1 for r in results if r.status == StepExecutionStatus.SIMULATED)
        failed = sum(1 for r in results if r.status == StepExecutionStatus.FAILED)
        blocked = sum(1 for r in results if r.status == StepExecutionStatus.BLOCKED)
        skipped = sum(1 for r in results if r.status == StepExecutionStatus.SKIPPED)

        # Simulated counts as succeeded for summary
        steps_succeeded = succeeded + simulated

        # Collect evidence refs
        evidence_refs = []
        for result in results:
            evidence_refs.extend(result.evidence_refs)

        # Evaluate gates for receipt
        gates_evaluated = []
        all_gates_passed = True
        for gate in plan.gates:
            gate_result = self.evaluate_gate(plan, gate.gate_type)
            gates_evaluated.append(gate_result)
            if gate.required and not gate_result.passed:
                all_gates_passed = False

        return ExecutionReceipt(
            receipt_id=receipt_id,
            plan_id=plan.build_plan_id,
            source_job_id=plan.source_job_id,
            foundup_id=plan.foundup_id,
            tenant_id=plan.tenant_id,
            mode=ExecutionMode.DRY_RUN if self.dry_run else ExecutionMode.REAL,
            total_steps=len(results),
            steps_succeeded=steps_succeeded,
            steps_failed=failed,
            steps_blocked=blocked,
            steps_skipped=skipped,
            all_gates_passed=all_gates_passed,
            gates_evaluated=gates_evaluated,
            step_results=results,
            evidence_refs=evidence_refs,
            completed_at=utc_now(),
            # WSP 97: These are ALWAYS False
            verification_complete=False,
            cabr_ready=False,
            payout_ready=False,
            real_execution_performed=False,
        )


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_executor(dry_run: bool = True) -> BuildPlanExecutor:
    """
    Get a BuildPlanExecutor instance.

    Args:
        dry_run: Force dry-run mode. Default True.

    Returns:
        BuildPlanExecutor configured for dry-run.
    """
    return BuildPlanExecutor(dry_run=dry_run)
