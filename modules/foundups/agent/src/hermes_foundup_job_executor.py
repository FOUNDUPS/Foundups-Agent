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

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
    JobStatus,
    PolicyFlags,
    StatusReasonCode,
    is_terminal_status,
)

# Module-path resolution (HERMES_MODULE_PATH_TRUST_REMOVAL_PHASE1):
# the #773 validator is imported and consumed as the source of truth for
# any module_path that enters the executor. The leading-underscore helper
# is intentionally a module-private import per the validator's "no IO /
# no execution" contract; we do NOT mutate the validator's public surface
# in this slice.
from modules.foundups.agent.src.foundup_manifest_validator import (
    validate_manifest_file,
)
from modules.foundups.agent.src.foundup_manifest_validator import (
    _canonicalize_module_path as _validator_canonicalize_module_path,
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
# Module-path resolution constants (HERMES_MODULE_PATH_TRUST_REMOVAL_PHASE1)
# ---------------------------------------------------------------------------

# Default repository root for manifest lookup. Derived from this source file's
# location so the executor does not depend on a CWD or env var.
# modules/foundups/agent/src/hermes_foundup_job_executor.py -> parents[4] = repo root
DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[4]

# Bounded glob set for foundup_id -> manifest lookup when the job payload
# omits module_path / source_module entirely. Mirrors the canonical
# manifest directory set surveyed in Phase 0 (8 manifests on disk today;
# this slice's lookup walks at most these globs and never recurses).
_MANIFEST_SEARCH_GLOBS: Tuple[str, ...] = (
    "modules/foundups/*/foundup_manifest.json",
    "modules/gamification/*/foundup_manifest.json",
    "modules/platform_integration/*/foundup_manifest.json",
    "modules/communication/*/foundup_manifest.json",
    "modules/ai_intelligence/*/foundup_manifest.json",
    "modules/infrastructure/*/foundup_manifest.json",
)

# Greppable failure-mode tokens emitted on resolution failure. The
# StatusReasonCode stays frozen at FAIL_VALIDATION_ERROR per the dispatch
# (no job-contract schema change); granularity comes from this prefix on
# reason_human + a parallel evidence_refs entry. This lets W10 and future
# audits distinguish failure classes by greppable string match instead of
# prose parsing.
FAIL_TOKEN_SYNTACTIC_REJECT: str = "syntactic_reject"
FAIL_TOKEN_MANIFEST_MISMATCH: str = "manifest_mismatch"
FAIL_TOKEN_MANIFEST_MISSING: str = "manifest_missing"
FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH: str = "cross_foundup_mismatch"

ALL_FAIL_TOKENS: frozenset = frozenset({
    FAIL_TOKEN_SYNTACTIC_REJECT,
    FAIL_TOKEN_MANIFEST_MISMATCH,
    FAIL_TOKEN_MANIFEST_MISSING,
    FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH,
})


@dataclass(frozen=True)
class ResolvedModulePath:
    """Outcome of validated module-path resolution.

    Observable-ignore shape mirroring
    ``modules/foundups/agent/src/source_authority.py:resolve_source_authority``:
    the consumer can inspect ``ignored`` to see exactly what the caller
    tried to declare, even on success. Silent swallow is refused per the
    #777 convention.

    Attributes:
        effective: canonical module_path from the validated manifest (the
            source of truth). ``None`` iff ``failed`` is True.
        ignored: the payload-declared candidate, stringified, or ``None``
            if and only if the caller supplied no candidate (neither
            ``payload.module_path`` nor ``payload.source_module``).
            Visible even on success; this is the observable-ignore
            channel.
        failed: True iff resolution failed.
        fail_token: one of ``ALL_FAIL_TOKENS`` on failure, else ``None``.
        fail_human: human-readable explanation prefixed with the
            ``fail_token`` for grep-ability; empty on success.
    """

    effective: Optional[str]
    ignored: Optional[str]
    failed: bool
    fail_token: Optional[str]
    fail_human: str


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


def _stringify_ignored(declared: Any) -> Optional[str]:
    """Mirror of ``source_authority.py``'s ignored-value stringification.

    Returns ``None`` if and only if ``declared`` is ``None``; otherwise
    ``str(declared)``. The observable-ignore channel uses this so callers
    can detect a (potentially malicious) declaration attempt regardless
    of input type.
    """
    if declared is None:
        return None
    return str(declared)


def _find_manifest_for_foundup_id(
    repo_root: Path, foundup_id: str
) -> Optional[Path]:
    """Locate a manifest file whose top-level ``foundup_id`` matches.

    Bounded scan over the 6 canonical manifest directories (Phase 0 found
    8 manifests today). Returns the first matching path, or ``None``.
    Used ONLY when the job payload omits both ``module_path`` and
    ``source_module``; this is the explicit alternative to the removed
    ``foundup_id``-as-path heuristic.

    The scan reads each candidate JSON only to check its top-level
    ``foundup_id`` field. No execution. No write.
    """
    if not foundup_id:
        return None
    for glob in _MANIFEST_SEARCH_GLOBS:
        for candidate in sorted(repo_root.glob(glob)):
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("foundup_id") == foundup_id:
                return candidate
    return None


def _resolve_validated_module_path(
    job: FoundUpJob,
    repo_root: Path,
) -> ResolvedModulePath:
    """Resolve a job's ``module_path`` through the #773 validator. Fail-closed.

    Pinned design (HERMES_MODULE_PATH_TRUST_REMOVAL_PHASE1):

    - **candidate** = ``payload.module_path`` or, if absent, the alias
      ``payload.source_module``. Empty string is treated as ABSENT
      (Addendum D #4).
    - **foundup_id heuristic REMOVED**: a ``/`` in ``foundup_id`` is
      no longer a path source. If the candidate is absent, fall through
      to a bounded foundup_id scan, NEVER to the raw ``foundup_id``
      string.
    - **syntactic hardening BEFORE any manifest contact**: the candidate
      is canonicalized via the validator's ``_canonicalize_module_path``
      helper. Empty / absolute / UNC / ``..`` traversal / backslash
      forms (and anything not under ``modules/``) are REJECTED with
      ``FAIL_TOKEN_SYNTACTIC_REJECT``.
    - **manifest location**: when the candidate resolves syntactically,
      the manifest is ``<repo_root>/<canonical>/foundup_manifest.json``.
      When the candidate is absent, the manifest is the first hit of the
      bounded foundup_id scan.
    - **validator gate**: ``validate_manifest_file`` (#773) is consumed
      as-is. It never raises; ``ok=False`` on missing / unreadable /
      shape-invalid manifest. Tokenized as ``manifest_missing`` for
      I/O-class errors, ``manifest_mismatch`` otherwise.
    - **cross-FoundUp substitution defense** (Addendum D #1, load-bearing):
      after validator passes, the manifest's ``foundup_id`` MUST equal
      ``job.foundup_id``. A job carrying ``foundup_id=A`` with a payload
      pointing at FoundUp B's real manifest is REJECTED with
      ``FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH``. The "some valid manifest
      exists for this path" check is NOT sufficient.
    - **case-variant defense** (Addendum D #3, Windows host reality):
      when the candidate was provided, the candidate's canonical form
      is exact-string-compared (case-sensitive) against the manifest's
      ``build_contract.module_path`` canonical form. Mismatch =>
      ``FAIL_TOKEN_MANIFEST_MISMATCH``.
    - **derivation when candidate absent**: ``effective`` becomes the
      manifest's canonical ``module_path`` (manifest is the source of
      truth). The ``foundup_id`` heuristic is never the source.
    - **observable ignored**: the payload-declared candidate is visible
      in ``ResolvedModulePath.ignored`` even on success (mirrors #777).
    """
    payload = job.payload or {}

    # Step 1: extract candidate; treat empty string as ABSENT.
    raw_candidate: Any = payload.get("module_path")
    if isinstance(raw_candidate, str) and not raw_candidate:
        raw_candidate = None
    if raw_candidate is None:
        raw_candidate = payload.get("source_module")
        if isinstance(raw_candidate, str) and not raw_candidate:
            raw_candidate = None
    ignored = _stringify_ignored(raw_candidate)

    canonical: Optional[str] = None
    manifest_path: Path

    if raw_candidate is not None:
        # Step 2: syntactic harden BEFORE any manifest contact.
        #
        # The validator's ``_canonicalize_module_path`` would itself convert
        # backslashes to forward slashes ("harmless equivalents"). For the
        # CONSUMER boundary (Addendum C #5) backslashes must be REJECTED
        # before any manifest contact -- on a Windows host, accepting them
        # invites path-name confusion. We do the backslash check here
        # explicitly so the rejection token is ``syntactic_reject`` and not
        # the more ambiguous ``manifest_mismatch``.
        if isinstance(raw_candidate, str) and "\\" in raw_candidate:
            return ResolvedModulePath(
                effective=None,
                ignored=ignored,
                failed=True,
                fail_token=FAIL_TOKEN_SYNTACTIC_REJECT,
                fail_human=(
                    f"{FAIL_TOKEN_SYNTACTIC_REJECT}: payload module_path "
                    f"{raw_candidate!r} contains backslashes; only "
                    f"POSIX-style forward slashes are accepted"
                ),
            )
        canonical = _validator_canonicalize_module_path(raw_candidate)
        if canonical is None or not canonical.startswith("modules/"):
            return ResolvedModulePath(
                effective=None,
                ignored=ignored,
                failed=True,
                fail_token=FAIL_TOKEN_SYNTACTIC_REJECT,
                fail_human=(
                    f"{FAIL_TOKEN_SYNTACTIC_REJECT}: payload module_path "
                    f"{raw_candidate!r} is empty, absolute, UNC, contains "
                    f"'..' traversal, or is not under modules/"
                ),
            )
        manifest_path = repo_root / canonical / "foundup_manifest.json"
    else:
        # Step 3: derive from validated manifest via bounded foundup_id scan.
        manifest_path_opt = _find_manifest_for_foundup_id(
            repo_root, job.foundup_id or ""
        )
        if manifest_path_opt is None:
            return ResolvedModulePath(
                effective=None,
                ignored=ignored,
                failed=True,
                fail_token=FAIL_TOKEN_MANIFEST_MISSING,
                fail_human=(
                    f"{FAIL_TOKEN_MANIFEST_MISSING}: no payload module_path; "
                    f"bounded scan for foundup_id={job.foundup_id!r} returned "
                    f"no manifest"
                ),
            )
        manifest_path = manifest_path_opt

    # Step 4: validate via #773 (never raises). Pass the manifest path as a
    # string -- the validator's public signature accepts ``str | PurePosixPath``
    # and normalizes internally; passing the OS ``Path`` directly satisfies
    # the runtime contract but tickles the static-type checker, which is why
    # we stringify here.
    result = validate_manifest_file(str(manifest_path))
    if not result.ok:
        err = result.errors[0] if result.errors else "validation failed"
        # I/O-class errors -> manifest_missing; shape errors -> manifest_mismatch.
        if (
            "not found" in err
            or "unreadable" in err
            or "not valid JSON" in err
        ):
            token = FAIL_TOKEN_MANIFEST_MISSING
        else:
            token = FAIL_TOKEN_MANIFEST_MISMATCH
        return ResolvedModulePath(
            effective=None,
            ignored=ignored,
            failed=True,
            fail_token=token,
            fail_human=f"{token}: {err}",
        )

    # Step 5: re-read the validated manifest to extract foundup_id and
    # module_path for the two final cross-checks. The validator confirmed
    # the manifest is well-formed and that its declared module_path matches
    # the manifest file's parent directory; we now confirm the foundup_id
    # binding and (when applicable) the candidate's case-sensitive match.
    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return ResolvedModulePath(
            effective=None,
            ignored=ignored,
            failed=True,
            fail_token=FAIL_TOKEN_MANIFEST_MISSING,
            fail_human=(
                f"{FAIL_TOKEN_MANIFEST_MISSING}: re-read failed: "
                f"{type(exc).__name__}"
            ),
        )
    manifest_foundup_id = manifest_data.get("foundup_id")
    manifest_module_path = manifest_data.get("build_contract", {}).get(
        "module_path", ""
    )
    canonical_manifest_module = _validator_canonicalize_module_path(
        manifest_module_path
    )

    if canonical_manifest_module is None:
        return ResolvedModulePath(
            effective=None,
            ignored=ignored,
            failed=True,
            fail_token=FAIL_TOKEN_MANIFEST_MISMATCH,
            fail_human=(
                f"{FAIL_TOKEN_MANIFEST_MISMATCH}: manifest at {manifest_path} "
                f"has un-canonicalizable build_contract.module_path="
                f"{manifest_module_path!r}"
            ),
        )

    # Step 6: cross-FoundUp substitution defense (Addendum D #1).
    if manifest_foundup_id != job.foundup_id:
        return ResolvedModulePath(
            effective=None,
            ignored=ignored,
            failed=True,
            fail_token=FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH,
            fail_human=(
                f"{FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH}: job.foundup_id="
                f"{job.foundup_id!r} but the manifest at {manifest_path} "
                f"declares foundup_id={manifest_foundup_id!r}"
            ),
        )

    # Step 7: when candidate provided, exact-string compare candidate canonical
    # vs manifest canonical (#773 exact-match at consumer boundary; Addendum
    # D #3 case-variant defense). When candidate was absent, derivation is
    # already from the validated manifest and this check is a no-op.
    if raw_candidate is not None and canonical != canonical_manifest_module:
        return ResolvedModulePath(
            effective=None,
            ignored=ignored,
            failed=True,
            fail_token=FAIL_TOKEN_MANIFEST_MISMATCH,
            fail_human=(
                f"{FAIL_TOKEN_MANIFEST_MISMATCH}: payload candidate canonical "
                f"{canonical!r} != manifest module_path "
                f"{canonical_manifest_module!r}"
            ),
        )

    # Success: effective is the manifest's canonical module_path (the source
    # of truth). The payload-declared value is preserved in ``ignored`` for
    # observability even when it matches.
    return ResolvedModulePath(
        effective=canonical_manifest_module,
        ignored=ignored,
        failed=False,
        fail_token=None,
        fail_human="",
    )


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
