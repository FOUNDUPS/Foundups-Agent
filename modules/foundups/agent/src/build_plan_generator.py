#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BuildPlan Generator -- Generate BuildPlan from FoundUpJob

Creates a BuildPlan from a FoundUpJob, bridging job-based orchestration
to plan-based build control without enabling real execution.

WSP 97 TRUTH BOUNDARIES:
  - Generator produces dry_run=True plans only
  - Generator does not execute BuildPlan steps
  - Generator does not wire real Hermes execution
  - No CABR/payout/reward/token fields

Architecture:
  FoundUpJob (OpenClaw) -> Generator -> BuildPlan -> (Future: Executor)

Module-path trust (BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1):
  Closes the #778 carry-forward. This generator no longer trusts raw
  payload.module_path / source_module, no longer infers from a hard-coded
  KNOWN_FOUNDUP_PATHS dict, and no longer synthesizes
  modules/foundups/{foundup_id}. All module-identity resolution flows
  through the SHARED module_path_resolution._resolve_validated_module_path
  -- the SAME single source of truth the Hermes executor (#778) consumes
  via shim (WSP 84).

  Cross-FoundUp substitution, case-variant payload, absolute / UNC /
  traversal / backslash forms, bare basenames, and public/member/foundups/
  PWA surfaces all produce a fail-closed GenerationValidationResult whose
  error_code is one of the closed-set #778 tokens
  {syntactic_reject, manifest_mismatch, manifest_missing,
  cross_foundup_mismatch}. The rejected payload value is observable in
  rejected_payload_value and the error_message, and NEVER propagates into
  the BuildTarget output.

  PWA-surface ruling: DERIVED_ONLY. BuildTarget.pwa_surface_path is derived
  deterministically from the validated canonical module_path basename,
  never from a payload-supplied surface path.

WSP Compliance:
  WSP 11  : Interface contract (typed API)
  WSP 50  : Pre-action validation (validate_job_for_build_plan)
  WSP 77  : Agent coordination (job->plan translation)
  WSP 84  : Single source of truth (no second resolver implementation)
  WSP 97  : Truth boundaries (dry_run=True, no real execution; fail-closed)

NAVIGATION:
  -> Uses: build_plan.py (BuildPlan, BuildTarget, BuildScope)
  -> Uses: foundup_job_contract.py (FoundUpJob, CANONICAL_ACTIONS)
  -> Uses: module_path_resolution.py (#778 shared validator-gated resolver)
  -> Spec: modules/foundups/docs/FOUNDUP_BUILD_PLAN_CONTRACT.md
  -> Called by: Internal VoteBallot PoC (future integration)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
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

# Shared module-path resolver -- single source of truth across the agent
# module (BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1). The Hermes
# executor (#778) consumes the SAME resolver via a re-export shim. There is
# exactly ONE implementation of the module-path trust rule (WSP 84).
from .module_path_resolution import (
    DEFAULT_REPO_ROOT,
    ResolvedModulePath,
    _resolve_validated_module_path,
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
# Module-Path Trust (BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1)
# ---------------------------------------------------------------------------
#
# The prior KNOWN_FOUNDUP_PATHS dict + get_known_foundup_path() inference
# helper (case-insensitive .lower() lookup), the
# f"modules/foundups/{job.foundup_id}" synthesis fallback, and the
# case-insensitive prefix-only _is_valid_foundup_path validator (which also
# admitted public/member/foundups/) were all non-manifest path sources that
# bypassed the #771/#773 manifest validator -- the same trust class deleted
# at the executor seam in #778. They have been DELETED in this slice;
# module-identity resolution now flows exclusively through the SHARED
# module_path_resolution._resolve_validated_module_path resolver.
#
# Phase-0 KNOWN_FOUNDUP_PATHS consumer census:
#   - 2 PATH_IDENTITY_USE sites (the two payload-path fallbacks here),
#   - 1 co-located error-string interpolation of KNOWN_FOUNDUP_PATHS.keys()
#     inside the now-deleted branch (not a surviving display consumer),
#   - 0 non-test cross-module callers.
# Ruling: DELETE_AS_DEAD_CODE (no display-only non-test consumer survives).


# ---------------------------------------------------------------------------
# Validation Result
# ---------------------------------------------------------------------------


@dataclass
class GenerationValidationResult:
    """Result of job validation for BuildPlan generation.

    Module-path trust contract (BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1):
      - error_code on failure is one of the pre-resolver gates
        {MISSING_FOUNDUP_ID, UNSUPPORTED_ACTION, UNKNOWN_ACTION} OR one of
        the closed-set #778 resolver tokens
        {syntactic_reject, manifest_mismatch, manifest_missing,
        cross_foundup_mismatch}.
      - inferred_module_path is the manifest-derived canonical module_path
        on success. None on any failure -- the rejected payload value is
        captured only in rejected_payload_value and error_message
        (observable, never used downstream).
      - rejected_payload_value mirrors the resolver's
        ResolvedModulePath.ignored observable-ignore channel. None iff no
        payload candidate was supplied; otherwise reported even on success
        (no silent swallow). It MUST NOT propagate into any BuildTarget /
        BuildPlan / source-ref output (WSP_97 row
        REJECTED_VALUE_NOT_IN_BUILDPLAN_OUTPUT).
    """

    valid: bool
    """True if job can generate a BuildPlan."""

    error_code: Optional[str] = None
    """Machine-readable error code if invalid."""

    error_message: Optional[str] = None
    """Human-readable error message if invalid."""

    inferred_module_path: Optional[str] = None
    """Manifest-derived canonical module_path on success. None on failure."""

    rejected_payload_value: Optional[str] = None
    """Stringified payload-declared candidate (observable-ignore). None iff
    the caller supplied no candidate. Visible even on success; NEVER
    propagated into BuildTarget output."""


# ---------------------------------------------------------------------------
# Validation Functions
# ---------------------------------------------------------------------------


def validate_job_for_build_plan(
    job: FoundUpJob, repo_root: Optional[Path] = None
) -> GenerationValidationResult:
    """Validate that a FoundUpJob can generate a BuildPlan.

    Module-path trust contract (BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1):

      1. job.foundup_id must be present.
      2. job.requested_action must be in BUILDPLAN_SUPPORTED_ACTIONS.
      3. module_path is resolved through the SHARED resolver
         module_path_resolution._resolve_validated_module_path (the same
         single source of truth #778 consumes via shim). No raw payload
         trust, no KNOWN_FOUNDUP_PATHS inference, no foundup_id-as-path
         synthesis, no case-insensitive prefix match, no
         public/member/foundups/ admit.

    On resolver rejection the closed-set #778 fail_token becomes the
    error_code and the rejected payload value is reported in
    rejected_payload_value (never used downstream).

    Args:
        job: FoundUpJob to validate.
        repo_root: Optional override for manifest lookup root (defaults to
            module_path_resolution.DEFAULT_REPO_ROOT).
    """
    # Pre-resolver gate: foundup_id must be present.
    if not job.foundup_id:
        return GenerationValidationResult(
            valid=False,
            error_code="MISSING_FOUNDUP_ID",
            error_message="FoundUpJob.foundup_id is required for BuildPlan generation",
        )

    # Pre-resolver gate: requested_action must be supported.
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

    # Module-path resolution via the SHARED #778 resolver. Fail-closed.
    # The resolver enforces: syntactic hardening pre-manifest (backslash /
    # absolute / UNC / traversal / not-under-modules/), bounded foundup_id
    # scan when payload candidate absent, #773 manifest validator gate,
    # cross-FoundUp substitution defense, case-variant defense.
    effective_repo_root = repo_root or DEFAULT_REPO_ROOT
    resolved: ResolvedModulePath = _resolve_validated_module_path(
        job, effective_repo_root
    )
    if resolved.failed:
        # The closed-set fail_token doubles as the error_code so downstream
        # auditors grep on the same taxonomy the executor (#778) uses. The
        # rejected payload value is observable but NEVER used downstream.
        return GenerationValidationResult(
            valid=False,
            error_code=resolved.fail_token or "manifest_missing",
            error_message=resolved.fail_human,
            inferred_module_path=None,
            rejected_payload_value=resolved.ignored,
        )

    # Success: the manifest's canonical module_path is the source of truth.
    # ignored carries any payload candidate for observability but is NOT
    # used downstream (build_target_from_job uses resolved.effective).
    return GenerationValidationResult(
        valid=True,
        inferred_module_path=resolved.effective,
        rejected_payload_value=resolved.ignored,
    )


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


def build_target_from_job(
    job: FoundUpJob, repo_root: Optional[Path] = None
) -> BuildTarget:
    """Generate BuildTarget from a validated FoundUpJob.

    Module-path trust contract (BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1):

      The module_path field of the produced BuildTarget is ALWAYS the
      validated manifest's canonical module_path (the resolver's effective
      value). Raw payload.module_path / payload.source_module /
      foundup_id-synthesis values are NEVER used as identity.

      PWA-surface ruling: DERIVED_ONLY. pwa_surface_path is derived
      deterministically from the canonical module_path basename plus a
      fixed public/member/foundups/<basename>/ template;
      payload.pwa_surface_path is NOT trusted as module-identity surface.

      Other BuildTarget fields (tests_path, docs_path, ...) remain
      payload-overridable; they are auto-derived from module_path by
      BuildTarget itself when omitted (see build_plan.py auto-derivation).
      Those alternates are not module identity and do not affect the trust
      seam this slice closes.

    Args:
        job: FoundUpJob whose payload provides BuildTarget field overrides.
            The job MUST have passed validate_job_for_build_plan first.
        repo_root: Optional override for manifest lookup root.

    Raises:
        ValueError: when the job fails validated module-path resolution
            (defense-in-depth; create_build_plan_from_job validates first).
            The rejected value appears only in the error message, never in a
            returned BuildTarget.
    """
    payload = job.payload or {}

    # The module_path that lands in BuildTarget is ALWAYS the resolver's
    # canonical effective value. The rejected-payload channel
    # (resolved.ignored) is read ONLY for the error-raise path; it never
    # enters the BuildTarget output.
    effective_repo_root = repo_root or DEFAULT_REPO_ROOT
    resolved: ResolvedModulePath = _resolve_validated_module_path(
        job, effective_repo_root
    )
    if resolved.failed:
        # Mirror the ValueError shape create_build_plan_from_job uses so
        # callers see one consistent failure path. The greppable token is
        # preserved in the message head.
        raise ValueError(f"[{resolved.fail_token}] {resolved.fail_human}")
    module_path: str = resolved.effective or ""

    # PWA-surface derivation (DERIVED_ONLY): ALWAYS from the canonical
    # module_path's last segment, never from payload-supplied surface paths
    # or from job.foundup_id. The basename of a validated canonical
    # module_path is the on-disk module directory name and is a safe key.
    module_basename = module_path.rsplit("/", 1)[-1] if module_path else ""
    pwa_surface_path = (
        f"public/member/foundups/{module_basename}/" if module_basename else None
    )

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
