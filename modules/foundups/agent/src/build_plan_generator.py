#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BuildPlan Generator — Generate BuildPlan from FoundUpJob

Creates a BuildPlan from a FoundUpJob, bridging job-based orchestration
to plan-based build control without enabling real execution.

WSP 97 TRUTH BOUNDARIES:
  - Generator produces dry_run=True plans only
  - Generator does not execute BuildPlan steps
  - Generator does not wire real Hermes execution
  - No CABR/payout/reward/token fields

Architecture:
  FoundUpJob (OpenClaw) -> Generator -> BuildPlan -> (Future: Executor)

WSP Compliance:
  WSP 11  : Interface contract (typed API)
  WSP 50  : Pre-action validation (validate_job_for_build_plan)
  WSP 77  : Agent coordination (job->plan translation)
  WSP 97  : Truth boundaries (dry_run=True, no real execution)

NAVIGATION:
  -> Uses: build_plan.py (BuildPlan, BuildTarget, BuildScope)
  -> Uses: foundup_job_contract.py (FoundUpJob, CANONICAL_ACTIONS)
  -> Spec: modules/foundups/docs/FOUNDUP_BUILD_PLAN_CONTRACT.md
  -> Called by: Internal VoteBallot PoC (future integration)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    CANONICAL_ACTIONS,
    FoundUpJob,
    is_supported_action,
)

from .build_plan import (
    BuildMode,
    BuildPlan,
    BuildPlanStatus,
    BuildScope,
    BuildTarget,
    create_standard_build_steps,
    generate_build_plan_id,
)

logger = logging.getLogger("build_plan_generator")


# ---------------------------------------------------------------------------
# Supported Actions for BuildPlan Generation
# ---------------------------------------------------------------------------

# Actions that can generate BuildPlans (not queue_foundup_job)
BUILDPLAN_SUPPORTED_ACTIONS: frozenset[str] = frozenset({
    "build_foundup",
    "extract_foundup",
    "validate_foundup",
})

# Actions that should NOT generate BuildPlans
BUILDPLAN_UNSUPPORTED_ACTIONS: frozenset[str] = frozenset({
    "queue_foundup_job",  # Meta-action, not executable
})


# ---------------------------------------------------------------------------
# Known FoundUp Module Paths (repo evidence)
# ---------------------------------------------------------------------------

# Known FoundUp IDs with proven module paths in the repo
# Used for module_path inference when payload doesn't specify
KNOWN_FOUNDUP_PATHS: Dict[str, str] = {
    "voteballots": "modules/foundups/voteballots",
    "gotjunk": "modules/foundups/gotjunk",
    "kosei": "modules/foundups/kosei",
    "pqn_portal": "modules/foundups/pqn_portal",
    "social_twin": "modules/foundups/social_twin",
    "move2japan": "modules/foundups/move2japan",
}


def get_known_foundup_path(foundup_id: str) -> Optional[str]:
    """
    Get known module path for a FoundUp ID.

    Returns None if not a known FoundUp with repo evidence.
    """
    return KNOWN_FOUNDUP_PATHS.get(foundup_id.lower())


# ---------------------------------------------------------------------------
# Validation Result
# ---------------------------------------------------------------------------


@dataclass
class GenerationValidationResult:
    """Result of job validation for BuildPlan generation."""

    valid: bool
    """True if job can generate a BuildPlan."""

    error_code: Optional[str] = None
    """Machine-readable error code if invalid."""

    error_message: Optional[str] = None
    """Human-readable error message if invalid."""

    inferred_module_path: Optional[str] = None
    """Module path inferred from foundup_id if not in payload."""


# ---------------------------------------------------------------------------
# Validation Functions
# ---------------------------------------------------------------------------


def validate_job_for_build_plan(job: FoundUpJob) -> GenerationValidationResult:
    """
    Validate that a FoundUpJob can generate a BuildPlan.

    Checks:
      1. foundup_id is present
      2. requested_action is supported
      3. module_path can be determined (from payload or inference)
      4. Path is within allowed scope

    Returns:
        GenerationValidationResult with validation outcome.
    """
    # Check foundup_id
    if not job.foundup_id:
        return GenerationValidationResult(
            valid=False,
            error_code="MISSING_FOUNDUP_ID",
            error_message="FoundUpJob.foundup_id is required for BuildPlan generation",
        )

    # Check requested_action is supported
    action = job.requested_action
    if action in BUILDPLAN_UNSUPPORTED_ACTIONS:
        return GenerationValidationResult(
            valid=False,
            error_code="UNSUPPORTED_ACTION",
            error_message=f"Action '{action}' cannot generate a BuildPlan. "
            f"Use one of: {', '.join(sorted(BUILDPLAN_SUPPORTED_ACTIONS))}",
        )

    if action not in BUILDPLAN_SUPPORTED_ACTIONS:
        return GenerationValidationResult(
            valid=False,
            error_code="UNKNOWN_ACTION",
            error_message=f"Unknown action '{action}'. "
            f"Supported actions: {', '.join(sorted(BUILDPLAN_SUPPORTED_ACTIONS))}",
        )

    # Determine module_path
    payload = job.payload or {}
    module_path = payload.get("module_path") or payload.get("source_module")

    # Try to infer from foundup_id if not provided
    inferred_path = None
    if not module_path:
        inferred_path = get_known_foundup_path(job.foundup_id)
        if inferred_path:
            module_path = inferred_path
        else:
            return GenerationValidationResult(
                valid=False,
                error_code="MISSING_MODULE_PATH",
                error_message=(
                    f"Cannot determine module_path for FoundUp '{job.foundup_id}'. "
                    f"Provide payload.module_path or use a known FoundUp ID: "
                    f"{', '.join(sorted(KNOWN_FOUNDUP_PATHS.keys()))}"
                ),
            )

    # Validate path is within allowed scope
    if not _is_valid_foundup_path(module_path):
        return GenerationValidationResult(
            valid=False,
            error_code="INVALID_MODULE_PATH",
            error_message=(
                f"Module path '{module_path}' is outside allowed scope. "
                f"Must be under modules/foundups/ or a recognized target path."
            ),
        )

    return GenerationValidationResult(
        valid=True,
        inferred_module_path=inferred_path,
    )


def _is_valid_foundup_path(path: str) -> bool:
    """
    Check if path is a valid FoundUp module path.

    Valid paths:
      - modules/foundups/<foundup_id>/...
      - public/member/foundups/<foundup_id>/... (PWA surface)
    """
    normalized = path.replace("\\", "/").lower()

    # Must be under foundups module or surface
    valid_prefixes = [
        "modules/foundups/",
        "public/member/foundups/",
    ]

    for prefix in valid_prefixes:
        if normalized.startswith(prefix):
            return True

    return False


# ---------------------------------------------------------------------------
# Scope Inference
# ---------------------------------------------------------------------------


def infer_build_scope(job: FoundUpJob) -> BuildScope:
    """
    Infer BuildScope from job action and payload.

    Mapping:
      validate_foundup -> GENESIS_ONLY
      build_foundup -> FULL_BUILD
      extract_foundup -> FULL_BUILD
    """
    action = job.requested_action
    payload = job.payload or {}

    # Check payload for explicit scope
    explicit_scope = payload.get("build_scope")
    if explicit_scope:
        try:
            return BuildScope(explicit_scope)
        except ValueError:
            pass  # Fall through to inference

    # Infer from action
    if action == "validate_foundup":
        return BuildScope.GENESIS_ONLY

    if action in ("build_foundup", "extract_foundup"):
        return BuildScope.FULL_BUILD

    # Default to genesis only for unknown
    return BuildScope.GENESIS_ONLY


# ---------------------------------------------------------------------------
# BuildTarget Generation
# ---------------------------------------------------------------------------


def build_target_from_job(job: FoundUpJob) -> BuildTarget:
    """
    Generate BuildTarget from FoundUpJob payload.

    Maps job.payload fields to BuildTarget fields.
    """
    payload = job.payload or {}

    # Determine module_path (validated before this is called)
    module_path = payload.get("module_path") or payload.get("source_module")
    if not module_path and job.foundup_id:
        module_path = get_known_foundup_path(job.foundup_id)

    if not module_path:
        # Should not reach here if validation passed
        module_path = f"modules/foundups/{job.foundup_id}"

    # Extract optional paths from payload
    pwa_surface_path = payload.get("pwa_surface_path")
    if not pwa_surface_path and job.foundup_id:
        # Default PWA surface path
        pwa_surface_path = f"public/member/foundups/{job.foundup_id}/"

    return BuildTarget(
        module_path=module_path,
        foundup_manifest_path=payload.get("foundup_manifest_path"),
        pwa_surface_path=pwa_surface_path,
        tests_path=payload.get("tests_path"),
        docs_path=payload.get("docs_path"),
        modlog_path=payload.get("modlog_path"),
        testmodlog_path=payload.get("testmodlog_path"),
        readme_path=payload.get("readme_path"),
        interface_path=payload.get("interface_path"),
        allowed_paths=payload.get("allowed_paths", []),
        blocked_paths=payload.get("blocked_paths", []),
    )


# ---------------------------------------------------------------------------
# BuildPlan Generation
# ---------------------------------------------------------------------------


def create_build_plan_from_job(job: FoundUpJob) -> BuildPlan:
    """
    Generate a BuildPlan from a FoundUpJob.

    Maps job identity, payload, and action to a BuildPlan structure.
    Always produces dry_run=True plans (WSP 97).

    Args:
        job: FoundUpJob to generate plan from.

    Returns:
        BuildPlan with job identity, target, and standard steps.

    Raises:
        ValueError: If job fails validation.

    WSP 97: This function ONLY generates plans with dry_run=True.
    It does NOT execute steps or enable real builds.
    """
    # Validate job
    validation = validate_job_for_build_plan(job)
    if not validation.valid:
        raise ValueError(
            f"[{validation.error_code}] {validation.error_message}"
        )

    # Generate plan ID
    plan_id = generate_build_plan_id(job.foundup_id)

    # Build target from job
    target = build_target_from_job(job)

    # Determine dry_run mode
    payload = job.payload or {}
    dry_run = True  # WSP 97: Always default to True

    # Check if job explicitly sets dry_run (still default True)
    if payload.get("dry_run") is False:
        # Log warning but keep dry_run=True for generator
        logger.warning(
            "[GENERATOR] Job %s requested dry_run=False, "
            "but generator always produces dry_run=True plans",
            job.job_id,
        )

    # Also check policy_flags
    if job.policy_flags and job.policy_flags.dry_run_mode is False:
        logger.warning(
            "[GENERATOR] Job %s has policy_flags.dry_run_mode=False, "
            "but generator always produces dry_run=True plans",
            job.job_id,
        )

    # Infer build scope
    scope = infer_build_scope(job)

    # Create plan
    plan = BuildPlan(
        build_plan_id=plan_id,
        foundup_id=job.foundup_id,
        tenant_id=job.tenant_id,
        intent_id=job.intent_id,
        source_job_id=job.job_id,
        requested_action=job.requested_action,
        mode=BuildMode.DRY_RUN,  # WSP 97: Always DRY_RUN
        dry_run=dry_run,  # WSP 97: Always True
        status=BuildPlanStatus.DRAFT,
        target=target,
    )

    # Add standard steps based on scope
    if scope in (BuildScope.FULL_BUILD, BuildScope.INCREMENTAL):
        plan.steps = create_standard_build_steps(target.module_path)
    elif scope == BuildScope.GENESIS_ONLY:
        # Genesis-only: first 2 validation steps
        all_steps = create_standard_build_steps(target.module_path)
        plan.steps = all_steps[:2]

    logger.info(
        "[GENERATOR] Created BuildPlan %s for job %s (foundup=%s, scope=%s)",
        plan.build_plan_id,
        job.job_id,
        job.foundup_id,
        scope.value,
    )

    return plan


# ---------------------------------------------------------------------------
# Convenience: Check if Job Can Generate Plan
# ---------------------------------------------------------------------------


def can_generate_build_plan(job: FoundUpJob) -> bool:
    """
    Check if a FoundUpJob can generate a BuildPlan.

    Args:
        job: FoundUpJob to check.

    Returns:
        True if job can generate a BuildPlan, False otherwise.
    """
    validation = validate_job_for_build_plan(job)
    return validation.valid


def get_generation_error(job: FoundUpJob) -> Optional[str]:
    """
    Get the generation error for a job, if any.

    Args:
        job: FoundUpJob to check.

    Returns:
        Error message if job cannot generate a BuildPlan, None otherwise.
    """
    validation = validate_job_for_build_plan(job)
    if validation.valid:
        return None
    return f"[{validation.error_code}] {validation.error_message}"
