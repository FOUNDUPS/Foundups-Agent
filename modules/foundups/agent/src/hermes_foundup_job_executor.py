#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hermes FoundUp Job Executor

Accepts a FoundUpJob, validates lifecycle/action, invokes Hermes FoundUp builder,
and returns updated job with truthful status, reason, evidence, and dry-run metadata.

Architecture:
    OpenClaw -> FoundUpJob (QUEUED) -> This Executor -> HermesFoundUpBuilder
             -> FoundUpJob (RUNNING) -> FoundUpJob (SUCCEEDED|BLOCKED|FAILED)

WSP Compliance:
    WSP 97  : Truthful status mapping, evidence_refs, no overclaims
    WSP 50  : Pre-action validation before Hermes invocation
    WSP 77  : Agent coordination (worker identity)
    WSP 11  : Interface contract (typed inputs/outputs)

Scope:
    This slice implements the Hermes job execution seam ONLY.
    It does NOT implement:
    - FAM pAVS event emission
    - CABR/PoB/reward logic
    - WRE skill queueing
    - Full autonomous build claims

NAVIGATION:
    -> Uses: foundup_job_contract.py (FoundUpJob, JobStatus, StatusReasonCode)
    -> Uses: hermes_adapter.py (HermesFoundUpBuilder)
    -> Called by: openclaw_foundup_orchestrator.py (future wiring)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
    JobStatus,
    PolicyFlags,
    StatusReasonCode,
    is_terminal_status,
)

# Module-path resolution moved to a shared module in
# BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1 (Addendum-C
# behavior-preserving extraction). This back-compat shim re-exports every
# name the prior in-file resolver exposed so existing imports keep working
# with ZERO test edits per Addendum C #3. The same objects are bound (no
# wrapping, no shadowing); identity is preserved across the import boundary.
#
# The #773 validator is still the source of truth -- it is consumed inside
# the shared module, exactly as before. This executor no longer imports the
# validator directly because every consumer of the module-path trust rule
# now routes through the single shared resolver (WSP 84).
from modules.foundups.agent.src.module_path_resolution import (  # noqa: F401
    ALL_FAIL_TOKENS,
    DEFAULT_REPO_ROOT,
    FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH,
    FAIL_TOKEN_MANIFEST_MISMATCH,
    FAIL_TOKEN_MANIFEST_MISSING,
    FAIL_TOKEN_SYNTACTIC_REJECT,
    ResolvedModulePath,
    _find_manifest_for_foundup_id,
    _MANIFEST_SEARCH_GLOBS,
    _resolve_validated_module_path,
    _stringify_ignored,
)

logger = logging.getLogger("hermes_foundup_job_executor")

# Worker identity for this executor
WORKER_ID = "hermes_foundup_executor"

# Supported actions that Hermes can handle
SUPPORTED_ACTIONS = frozenset({
    "build_foundup",
    "extract_foundup",
    "validate_foundup",
})


# ---------------------------------------------------------------------------
# Module-path resolution surface (re-exported from the shared module)
# ---------------------------------------------------------------------------
#
# DEFAULT_REPO_ROOT, _MANIFEST_SEARCH_GLOBS, the four FAIL_TOKEN_* constants,
# ALL_FAIL_TOKENS, and the ResolvedModulePath dataclass are now defined in
# modules/foundups/agent/src/module_path_resolution.py and re-exported by the
# import block above (BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1,
# Addendum-C behavior-preserving extraction). External imports of these names
# from this executor module continue to resolve to the SAME objects.


class HermesJobExecutionResult:
    """Result container for Hermes job execution."""

    __slots__ = ("job", "hermes_result", "error")

    def __init__(
        self,
        job: FoundUpJob,
        hermes_result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        self.job = job
        self.hermes_result = hermes_result
        self.error = error


def execute_foundup_job(
    job: FoundUpJob,
    repo_root: Optional[Path] = None,
    force_dry_run: bool = False,
) -> HermesJobExecutionResult:
    """
    Execute a FoundUpJob via HermesFoundUpBuilder.

    This is the main entry point for Hermes job execution.

    Args:
        job: FoundUpJob to execute. Must be in QUEUED state.
        repo_root: Repository root path. Defaults to O:/Foundups-Agent.
        force_dry_run: Force dry-run mode regardless of env vars.

    Returns:
        HermesJobExecutionResult with updated job and Hermes result.

    State Transitions:
        QUEUED -> RUNNING -> SUCCEEDED (on success)
        QUEUED -> RUNNING -> BLOCKED  (on security/exfoliation gate)
        QUEUED -> RUNNING -> FAILED   (on error/unsupported action)
        QUEUED -> FAILED              (if validation fails before RUNNING)

    Status Mapping:
        Hermes Result                -> JobStatus        -> StatusReasonCode
        ------------------------------------------------------------------
        success: True                -> SUCCEEDED        -> OK_COMPLETED / OK_DRY_RUN_PASSED
        error: security_gate_failed  -> BLOCKED          -> BLOCKED_AWAITING_APPROVAL
        error: exfoliation_gate_failed-> BLOCKED         -> FAIL_EXFOLIATION_GATE
        error: module_not_found      -> FAILED           -> FAIL_VALIDATION_ERROR
        unsupported action           -> FAILED           -> FAIL_VALIDATION_ERROR
        exception                    -> FAILED           -> FAIL_EXECUTION_ERROR
    """
    # Pre-validation: Job must not be terminal
    if is_terminal_status(job.status):
        logger.warning(
            "[HERMES-EXEC] Job %s already terminal: %s",
            job.job_id,
            job.status.value,
        )
        # Don't modify terminal jobs - return as-is with error
        return HermesJobExecutionResult(
            job=job,
            error=f"Job already in terminal state: {job.status.value}",
        )

    # Pre-validation: Job must be QUEUED
    if job.status != JobStatus.QUEUED:
        logger.warning(
            "[HERMES-EXEC] Job %s not QUEUED: %s",
            job.job_id,
            job.status.value,
        )
        job.fail(
            reason_code=StatusReasonCode.FAIL_INVALID_TRANSITION,
            reason_human=f"Expected QUEUED, got {job.status.value}",
        )
        return HermesJobExecutionResult(job=job, error="Job not in QUEUED state")

    # Pre-validation: Action must be supported
    action = job.requested_action
    if action not in SUPPORTED_ACTIONS:
        logger.warning(
            "[HERMES-EXEC] Unsupported action: %s for job %s",
            action,
            job.job_id,
        )
        job.fail(
            reason_code=StatusReasonCode.FAIL_VALIDATION_ERROR,
            reason_human=f"Unsupported action: {action}. Supported: {', '.join(sorted(SUPPORTED_ACTIONS))}",
        )
        return HermesJobExecutionResult(
            job=job,
            error=f"Unsupported action: {action}",
        )

    # Pre-validation: Module path must resolve via validated manifest (#773).
    # Replaces the prior _extract_module_path raw-trust behavior; closes the
    # #774 carry-forward "validator bypass risk" before this executor's
    # subprocess sink (HermesFoundUpBuilder.run_hermes_extraction).
    effective_repo_root = repo_root or DEFAULT_REPO_ROOT
    resolved = _resolve_validated_module_path(job, effective_repo_root)
    if resolved.failed:
        logger.warning(
            "[HERMES-EXEC] Module-path resolution failed for job %s: %s",
            job.job_id,
            resolved.fail_human,
        )
        # Observable-ignore: a rejected payload value is recorded in
        # evidence even when the failure_token is not strictly about it
        # (mirrors #777's source_authority.resolve convention).
        evidence: List[str] = []
        if resolved.ignored is not None:
            evidence.append(f"rejected_payload_value:{resolved.ignored}")
        if resolved.fail_token:
            evidence.append(f"fail_token:{resolved.fail_token}")
        job.fail(
            reason_code=StatusReasonCode.FAIL_VALIDATION_ERROR,
            reason_human=resolved.fail_human,
            evidence_refs=evidence if evidence else None,
        )
        return HermesJobExecutionResult(
            job=job,
            error=resolved.fail_human,
        )
    # ``resolved.effective`` is guaranteed non-None when ``failed`` is False
    # (see ResolvedModulePath success path). Bind a narrowed local for the
    # downstream type signature on _dispatch_action.
    assert resolved.effective is not None
    module_path: str = resolved.effective

    # Transition to RUNNING
    if not job.start(
        worker_id=WORKER_ID,
        reason_human=f"Hermes executing {action} for {module_path}",
    ):
        return HermesJobExecutionResult(
            job=job,
            error="Failed to transition to RUNNING",
        )

    # Initialize Hermes builder
    try:
        from .hermes_adapter import HermesFoundUpBuilder

        builder = HermesFoundUpBuilder(repo_root=repo_root)

        # Apply force_dry_run if requested
        if force_dry_run:
            builder.dry_run = True

        # Update policy flags
        job.policy_flags.dry_run_mode = builder.dry_run

    except ImportError as exc:
        logger.error("[HERMES-EXEC] HermesFoundUpBuilder import failed: %s", exc)
        job.fail(
            reason_code=StatusReasonCode.FAIL_WORKER_UNAVAILABLE,
            reason_human=f"Hermes builder not available: {exc}",
        )
        return HermesJobExecutionResult(job=job, error=str(exc))

    # Execute based on action
    try:
        hermes_result = _dispatch_action(builder, action, module_path, job)
    except Exception as exc:
        logger.exception("[HERMES-EXEC] Exception during %s: %s", action, exc)
        job.fail(
            reason_code=StatusReasonCode.FAIL_EXECUTION_ERROR,
            reason_human=f"Hermes execution exception: {exc}",
        )
        return HermesJobExecutionResult(job=job, error=str(exc))

    # Map Hermes result to job state
    _apply_hermes_result_to_job(job, hermes_result, action)

    return HermesJobExecutionResult(job=job, hermes_result=hermes_result)


# NOTE: _stringify_ignored, _find_manifest_for_foundup_id, and
# _resolve_validated_module_path are now defined in
# modules/foundups/agent/src/module_path_resolution.py and re-exported by the
# import block above (BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1,
# Addendum-C behavior-preserving extraction). External attribute access via
# `hermes_foundup_job_executor.<name>` continues to resolve to the SAME
# objects (identity preserved). There is exactly ONE implementation of the
# module-path trust rule (WSP 84 single source of truth).
#
# (Function bodies removed in this slice; the shared module owns them.)


def _dispatch_action(
    builder: Any,  # HermesFoundUpBuilder
    action: str,
    module_path: str,
    job: FoundUpJob,
) -> Dict[str, Any]:
    """
    Dispatch to appropriate HermesFoundUpBuilder method.

    Args:
        builder: HermesFoundUpBuilder instance
        action: Requested action
        module_path: Target module path
        job: Current job (for payload access)

    Returns:
        Hermes result dict
    """
    payload = job.payload or {}
    target_org = payload.get("target_org", "FOUNDUPS")

    if action == "extract_foundup":
        return builder.extract_foundup(
            source_module=module_path,
            target_org=target_org,
        )

    if action == "validate_foundup":
        # Validate = check exfoliation gate + analyze boundary
        gate = builder.check_exfoliation_gate(module_path)
        analysis = builder.analyze_boundary(module_path)

        return {
            "success": gate.passed,
            "error": None if gate.passed else "exfoliation_gate_failed",
            "source_module": module_path,
            "exfoliation_gate": {
                "passed": gate.passed,
                "checks": {
                    "module_boundary_clear": gate.module_boundary_clear,
                    "contracts_explicit": gate.contracts_explicit,
                    "runtime_testable": gate.runtime_testable,
                    "deploy_surface_understood": gate.deploy_surface_understood,
                    "shared_deps_adapter_level": gate.shared_deps_adapter_level,
                    "claw_can_participate": gate.claw_can_participate,
                },
            },
            "boundary_analysis": {
                "product_files": len(analysis.product_files),
                "core_dependencies": len(analysis.core_imports),
                "adapters_needed": analysis.adapters_needed,
                "blockers": analysis.blockers,
            },
            "dry_run": builder.dry_run,
        }

    if action == "build_foundup":
        # Build = full extraction (same as extract for now)
        return builder.extract_foundup(
            source_module=module_path,
            target_org=target_org,
        )

    # Should not reach here due to validation
    return {"success": False, "error": f"unhandled_action:{action}"}


def _apply_hermes_result_to_job(
    job: FoundUpJob,
    hermes_result: Dict[str, Any],
    action: str,
) -> None:
    """
    Map Hermes result to job state transition.

    Updates job status, reason, evidence, and payload.
    """
    success = hermes_result.get("success", False)
    error = hermes_result.get("error")
    dry_run = hermes_result.get("dry_run", False)

    # Update policy flags from result
    job.policy_flags.dry_run_mode = dry_run

    # Extract exfoliation gate info if present
    exfoliation_gate = hermes_result.get("exfoliation_gate", {})
    if exfoliation_gate:
        job.policy_flags.exfoliation_gate_checked = True
        job.policy_flags.exfoliation_gate_passed = exfoliation_gate.get("passed", False)

    # Build evidence refs
    evidence_refs = _build_evidence_refs(hermes_result, action)

    # Augment payload with Hermes result summary
    job.payload["hermes_result_summary"] = {
        "success": success,
        "error": error,
        "dry_run": dry_run,
        "action": action,
    }

    if success:
        # Determine success reason based on dry_run
        reason_code = (
            StatusReasonCode.OK_DRY_RUN_PASSED
            if dry_run
            else StatusReasonCode.OK_COMPLETED
        )
        reason_human = (
            f"Hermes {action} completed (dry-run)" if dry_run
            else f"Hermes {action} completed successfully"
        )

        job.succeed(
            reason_human=reason_human,
            evidence_refs=evidence_refs,
        )
        # Override reason code (succeed() uses OK_COMPLETED by default)
        job.status_reason_code = reason_code

    elif error == "security_gate_failed":
        # Security gate failure -> BLOCKED (awaiting approval)
        job.policy_flags.security_gate_checked = True
        job.policy_flags.security_gate_passed = False

        job.block(
            reason_code=StatusReasonCode.BLOCKED_AWAITING_APPROVAL,
            reason_human="Hermes security gate failed - awaiting AI Overseer approval",
        )
        job.evidence_refs.extend(evidence_refs)

    elif error == "exfoliation_gate_failed":
        # Exfoliation gate failure -> BLOCKED with gate details
        checks = exfoliation_gate.get("checks", {})
        failed_checks = [k for k, v in checks.items() if not v]

        job.block(
            reason_code=StatusReasonCode.FAIL_EXFOLIATION_GATE,
            reason_human=f"Exfoliation gate failed: {', '.join(failed_checks) or 'unknown checks'}",
        )

        # Add gate details to payload
        job.payload["exfoliation_gate_details"] = {
            "passed": False,
            "checks": checks,
            "failed_checks": failed_checks,
        }
        job.evidence_refs.extend(evidence_refs)

    else:
        # Other errors -> FAILED
        # Check for module not found
        boundary = hermes_result.get("boundary_analysis", {})
        blockers = boundary.get("blockers", [])

        is_not_found = any("not found" in b.lower() for b in blockers)

        if is_not_found:
            reason_code = StatusReasonCode.FAIL_VALIDATION_ERROR
            reason_human = f"Module not found or inaccessible: {blockers}"
        else:
            reason_code = StatusReasonCode.FAIL_EXECUTION_ERROR
            reason_human = f"Hermes {action} failed: {error or 'unknown error'}"

        job.fail(
            reason_code=reason_code,
            reason_human=reason_human,
            evidence_refs=evidence_refs,
        )


def _build_evidence_refs(
    hermes_result: Dict[str, Any],
    action: str,
) -> List[str]:
    """
    Build evidence refs from Hermes result.

    Evidence includes:
        - Target repo (if present)
        - Manifest path (if present)
        - Adapter paths (if generated)
    """
    evidence = []

    # Target repo as evidence
    target_repo = hermes_result.get("target_repo")
    if target_repo:
        evidence.append(f"github.com/{target_repo}")

    # Source module as evidence
    source_module = hermes_result.get("source_module")
    if source_module:
        evidence.append(f"{source_module}/foundup_manifest.json")

    # Adapters as evidence
    adapters = hermes_result.get("adapters", {})
    adapters_created = adapters.get("adapters_created", [])
    for adapter_path in adapters_created[:3]:  # Limit to 3
        evidence.append(adapter_path)

    return evidence


# ---------------------------------------------------------------------------
# Utility Functions for External Callers
# ---------------------------------------------------------------------------


def can_execute_action(action: str) -> bool:
    """Check if an action is supported by this executor."""
    return action in SUPPORTED_ACTIONS


def get_supported_actions() -> List[str]:
    """Get list of supported actions."""
    return sorted(SUPPORTED_ACTIONS)
