#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WRE Destructive Action Guard - Fail-Closed Runtime Seam (Phase 1)

Provides fail-closed validation for destructive actions in the WRE/Hermes flow.
This module implements the gate contracts defined in WRE_DESTRUCTIVE_ACTION_GUARD.md
using HXA18-HXA21 precedents for safe operation.

Architecture:
    Action Request -> DestructiveActionGuard -> GuardDecision
                   -> If ALLOW_DRY_RUN: proceed with dry-run evidence only
                   -> If BLOCKED: halt with reason
                   -> If REQUIRES_APPROVAL: queue for human approval (future)

Key Principle: FAIL-CLOSED
    - Unknown action class -> BLOCKED
    - Missing security gate -> BLOCKED for D3+
    - Missing capability token -> BLOCKED for D3+
    - Missing human approval -> BLOCKED for D4+
    - D4/D5/D6 -> BLOCKED in Phase 1 (no live execution)
    - live_execution_allowed = False (ALWAYS in Phase 1)

WSP Compliance:
    WSP 97 : Truth Boundaries (all safety fields remain False)
    WSP 50 : Pre-Action Verification (fail-closed validation)
    WSP 11 : Interface contract (typed request/result)

Slice: HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME_PHASE1
Worker: 0102

NAVIGATION:
    -> Uses: WRE_DESTRUCTIVE_ACTION_GUARD.md (design document)
    -> Related: HXA19 (repo creation gate), HXA20 (production source gate)
    -> Related: HXA21 (capability token infrastructure)
    -> Integrates with: hermes_job_executor.py (future, validation only)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging
import os
import re
import sys

logger = logging.getLogger("wre_destructive_action_guard")


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


# ===========================================================================
# SECTION 1: Destructive Action Classification (from WRE_DESTRUCTIVE_ACTION_GUARD.md)
# ===========================================================================


class DestructiveActionClass(str, Enum):
    """
    Classification of destructive actions by severity.

    From WRE_DESTRUCTIVE_ACTION_GUARD.md Section 2.1:
    - D0: Read-only observations
    - D1: Read operations
    - D2: Simulation/dry-run
    - D3: Sandbox writes (within workspace)
    - D4: Repo writes (requires approval)
    - D5: External side effects (blocked Phase 1)
    - D6: Irreversible actions (blocked Phase 1)
    """

    D0_OBSERVE = "D0_OBSERVE"
    """Read-only observations. No state modification."""

    D1_READ = "D1_READ"
    """Read operations. File read, API GET, log inspection."""

    D2_SIMULATE = "D2_SIMULATE"
    """Simulation/dry-run. Local temp changes only."""

    D3_WRITE_SANDBOX = "D3_WRITE_SANDBOX"
    """Sandbox writes. Within workspace binding, path-validated."""

    D4_WRITE_REPO = "D4_WRITE_REPO"
    """Repo writes. Requires human approval. BLOCKED Phase 1."""

    D5_EXTERNAL_SIDE_EFFECT = "D5_EXTERNAL_SIDE_EFFECT"
    """External side effects. API calls, emails. BLOCKED Phase 1."""

    D6_IRREVERSIBLE = "D6_IRREVERSIBLE"
    """Irreversible actions. Delete, revoke. BLOCKED Phase 1."""


# Severity order for comparison
_CLASS_SEVERITY: Dict[DestructiveActionClass, int] = {
    DestructiveActionClass.D0_OBSERVE: 0,
    DestructiveActionClass.D1_READ: 1,
    DestructiveActionClass.D2_SIMULATE: 2,
    DestructiveActionClass.D3_WRITE_SANDBOX: 3,
    DestructiveActionClass.D4_WRITE_REPO: 4,
    DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT: 5,
    DestructiveActionClass.D6_IRREVERSIBLE: 6,
}


def class_severity(action_class: DestructiveActionClass) -> int:
    """Return numeric severity for comparison."""
    return _CLASS_SEVERITY.get(action_class, 99)


def class_at_least(
    action_class: DestructiveActionClass,
    threshold: DestructiveActionClass,
) -> bool:
    """Check if action_class is at or above threshold severity."""
    return class_severity(action_class) >= class_severity(threshold)


# ===========================================================================
# SECTION 2: Guard Decision
# ===========================================================================


class GuardDecision(str, Enum):
    """Decision from destructive action guard evaluation."""

    ALLOW_DRY_RUN = "ALLOW_DRY_RUN"
    """Action allowed as dry-run only. No live execution."""

    BLOCKED = "BLOCKED"
    """Action blocked by guard. Do not proceed."""

    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    """Action requires human approval. Queue for approval (future)."""


class GuardBlockReasonCode(str, Enum):
    """Machine-readable reason codes for guard blocks."""

    # Allowed
    OK_DRY_RUN = "OK_DRY_RUN"
    OK_SANDBOX = "OK_SANDBOX"

    # Blocked - Missing gates
    MISSING_SECURITY_GATE = "MISSING_SECURITY_GATE"
    MISSING_CAPABILITY_TOKEN = "MISSING_CAPABILITY_TOKEN"
    MISSING_HUMAN_APPROVAL = "MISSING_HUMAN_APPROVAL"
    MISSING_WORKSPACE_BINDING = "MISSING_WORKSPACE_BINDING"
    MISSING_PATH_VALIDATION = "MISSING_PATH_VALIDATION"

    # Blocked - Class restrictions
    BLOCKED_D4_REPO_WRITE_PHASE1 = "BLOCKED_D4_REPO_WRITE_PHASE1"
    BLOCKED_D5_EXTERNAL_PHASE1 = "BLOCKED_D5_EXTERNAL_PHASE1"
    BLOCKED_D6_IRREVERSIBLE_PHASE1 = "BLOCKED_D6_IRREVERSIBLE_PHASE1"
    BLOCKED_UNKNOWN_CLASS = "BLOCKED_UNKNOWN_CLASS"

    # Requires approval (future)
    REQUIRES_HUMAN_APPROVAL = "REQUIRES_HUMAN_APPROVAL"


# ===========================================================================
# SECTION 3: Destructive Action Request
# ===========================================================================


@dataclass
class DestructiveActionRequest:
    """
    Request to perform a destructive action.

    This dataclass captures all information needed to evaluate whether
    a destructive action should be allowed, blocked, or require approval.

    WSP 97: This is a request contract. No action is taken by creating this.
    """

    # === Action Identity ===
    action_id: str
    """Unique identifier for this action request."""

    action_type: str
    """Type of action being requested (e.g., 'file_write', 'repo_create')."""

    target_path: str
    """Target path or resource identifier."""

    # === Classification ===
    requested_class: DestructiveActionClass
    """Requested destructive action class (D0-D6)."""

    # === Execution Mode ===
    dry_run_mode: bool = True
    """If True, action should only be simulated. Default: True (safe)."""

    # === Gates ===
    human_approval: bool = False
    """Whether human approval has been granted."""

    capability_token_present: bool = False
    """Whether a valid capability token is present."""

    security_gate_passed: bool = False
    """Whether security gate check has passed."""

    # === Workspace Binding ===
    workspace_binding_enforced: bool = False
    """Whether workspace binding has been verified."""

    path_constraints_validated: bool = False
    """Whether path is within allowed roots and not blocked."""

    # === Metadata ===
    requester_id: str = ""
    """Identity of the requester (agent/worker)."""

    job_id: str = ""
    """Associated FoundUpJob ID if applicable."""

    created_at: datetime = field(default_factory=_utc_now)
    """Request creation timestamp."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for logging/audit."""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "target_path": self.target_path,
            "requested_class": self.requested_class.value,
            "dry_run_mode": self.dry_run_mode,
            "human_approval": self.human_approval,
            "capability_token_present": self.capability_token_present,
            "security_gate_passed": self.security_gate_passed,
            "workspace_binding_enforced": self.workspace_binding_enforced,
            "path_constraints_validated": self.path_constraints_validated,
            "requester_id": self.requester_id,
            "job_id": self.job_id,
            "created_at": self.created_at.isoformat(),
        }


# ===========================================================================
# SECTION 4: Destructive Action Guard Result
# ===========================================================================


@dataclass
class DestructiveActionGuardResult:
    """
    Result of destructive action guard evaluation.

    WSP 97 Truth Boundaries:
    - live_execution_allowed = False (ALWAYS in Phase 1)
    - repo_created = False (ALWAYS)
    - production_source_modified = False (ALWAYS)
    - external_federation_initiated = False (ALWAYS)
    - verification_complete = False (no CABR pipeline)
    - cabr_ready = False (no CABR pipeline)
    - payout_ready = False (no payout pipeline)
    """

    # === Decision ===
    allowed: bool
    """Whether the action is allowed to proceed."""

    decision: GuardDecision
    """The guard decision (ALLOW_DRY_RUN, BLOCKED, REQUIRES_APPROVAL)."""

    reason_code: GuardBlockReasonCode
    """Machine-readable reason code."""

    # === Classification ===
    destructive_class: DestructiveActionClass
    """The evaluated destructive action class."""

    # === Execution Constraints ===
    dry_run_only: bool = True
    """If True, only dry-run execution is allowed. Default: True."""

    # === WSP 97 Truth Fields - ALWAYS False in Phase 1 ===
    live_execution_allowed: bool = False
    """WSP 97: Always False in Phase 1. No live execution permitted."""

    repo_created: bool = False
    """WSP 97: Always False. No repo creation performed."""

    production_source_modified: bool = False
    """WSP 97: Always False. No production source modified."""

    external_federation_initiated: bool = False
    """WSP 97: Always False. No external federation initiated."""

    verification_complete: bool = False
    """WSP 97: Always False. No CABR verification performed."""

    cabr_ready: bool = False
    """WSP 97: Always False. No CABR pipeline integration."""

    payout_ready: bool = False
    """WSP 97: Always False. No payout pipeline integration."""

    # === Additional Context ===
    reason_human: str = ""
    """Human-readable explanation of the decision."""

    gates_checked: List[str] = field(default_factory=list)
    """List of gates that were evaluated."""

    gates_passed: List[str] = field(default_factory=list)
    """List of gates that passed."""

    gates_failed: List[str] = field(default_factory=list)
    """List of gates that failed."""

    evaluated_at: datetime = field(default_factory=_utc_now)
    """Evaluation timestamp."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for logging/audit."""
        return {
            "allowed": self.allowed,
            "decision": self.decision.value,
            "reason_code": self.reason_code.value,
            "destructive_class": self.destructive_class.value,
            "dry_run_only": self.dry_run_only,
            # WSP 97 Truth Fields
            "live_execution_allowed": self.live_execution_allowed,
            "repo_created": self.repo_created,
            "production_source_modified": self.production_source_modified,
            "external_federation_initiated": self.external_federation_initiated,
            "verification_complete": self.verification_complete,
            "cabr_ready": self.cabr_ready,
            "payout_ready": self.payout_ready,
            # Context
            "reason_human": self.reason_human,
            "gates_checked": self.gates_checked,
            "gates_passed": self.gates_passed,
            "gates_failed": self.gates_failed,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


# ===========================================================================
# SECTION 5: Destructive Action Guard (Fail-Closed Evaluator)
# ===========================================================================


class DestructiveActionGuard:
    """
    Fail-closed evaluator for destructive actions.

    Phase 1 Behavior:
    - D0 (observe): Allowed only if dry_run_mode=True
    - D1 (read): Allowed only if dry_run_mode=True
    - D2 (simulate): Allowed if dry_run_mode=True
    - D3 (sandbox): Requires workspace_binding, path_validation, capability_token, security_gate
    - D4 (repo): BLOCKED in Phase 1
    - D5 (external): BLOCKED in Phase 1
    - D6 (irreversible): BLOCKED in Phase 1

    Key Principle: FAIL-CLOSED
    - Any missing gate for D3+ blocks the action
    - Unknown class blocks the action
    - live_execution_allowed is always False
    """

    def __init__(self):
        """Initialize the guard with Phase 1 constraints."""
        # Phase 1: No live execution allowed
        self.phase = 1
        self.live_execution_enabled = False

    def evaluate(self, request: DestructiveActionRequest) -> DestructiveActionGuardResult:
        """
        Evaluate a destructive action request.

        Args:
            request: DestructiveActionRequest to evaluate

        Returns:
            DestructiveActionGuardResult with decision and truth fields

        WSP 97: This does NOT perform the action. It only evaluates permission.
        """
        gates_checked: List[str] = []
        gates_passed: List[str] = []
        gates_failed: List[str] = []

        action_class = request.requested_class

        # Gate 0: Validate action class is known
        gates_checked.append("known_class")
        if action_class not in DestructiveActionClass.__members__.values():
            gates_failed.append("known_class")
            return self._blocked_result(
                action_class=action_class,
                reason_code=GuardBlockReasonCode.BLOCKED_UNKNOWN_CLASS,
                reason_human=f"Unknown action class: {action_class}",
                gates_checked=gates_checked,
                gates_passed=gates_passed,
                gates_failed=gates_failed,
            )
        gates_passed.append("known_class")

        # Gate 1: D0/D1 - Observe/Read only allowed in dry-run
        if action_class in (
            DestructiveActionClass.D0_OBSERVE,
            DestructiveActionClass.D1_READ,
        ):
            gates_checked.append("dry_run_mode")
            if request.dry_run_mode:
                gates_passed.append("dry_run_mode")
                return self._allow_dry_run_result(
                    action_class=action_class,
                    reason_code=GuardBlockReasonCode.OK_DRY_RUN,
                    reason_human=f"{action_class.value} allowed in dry-run mode",
                    gates_checked=gates_checked,
                    gates_passed=gates_passed,
                    gates_failed=gates_failed,
                )
            else:
                # Even D0/D1 require dry_run in Phase 1
                gates_failed.append("dry_run_mode")
                return self._blocked_result(
                    action_class=action_class,
                    reason_code=GuardBlockReasonCode.BLOCKED_D4_REPO_WRITE_PHASE1,
                    reason_human="Live execution not enabled in Phase 1",
                    gates_checked=gates_checked,
                    gates_passed=gates_passed,
                    gates_failed=gates_failed,
                )

        # Gate 2: D2 - Simulate allowed only if dry_run_mode=True
        if action_class == DestructiveActionClass.D2_SIMULATE:
            gates_checked.append("dry_run_mode")
            if request.dry_run_mode:
                gates_passed.append("dry_run_mode")
                return self._allow_dry_run_result(
                    action_class=action_class,
                    reason_code=GuardBlockReasonCode.OK_DRY_RUN,
                    reason_human="D2_SIMULATE allowed in dry-run mode",
                    gates_checked=gates_checked,
                    gates_passed=gates_passed,
                    gates_failed=gates_failed,
                )
            else:
                gates_failed.append("dry_run_mode")
                return self._blocked_result(
                    action_class=action_class,
                    reason_code=GuardBlockReasonCode.BLOCKED_D4_REPO_WRITE_PHASE1,
                    reason_human="Live simulation not enabled in Phase 1",
                    gates_checked=gates_checked,
                    gates_passed=gates_passed,
                    gates_failed=gates_failed,
                )

        # Gate 3: D3 - Sandbox write requires all gates
        if action_class == DestructiveActionClass.D3_WRITE_SANDBOX:
            # Check workspace binding
            gates_checked.append("workspace_binding")
            if not request.workspace_binding_enforced:
                gates_failed.append("workspace_binding")
                return self._blocked_result(
                    action_class=action_class,
                    reason_code=GuardBlockReasonCode.MISSING_WORKSPACE_BINDING,
                    reason_human="D3_WRITE_SANDBOX requires workspace binding",
                    gates_checked=gates_checked,
                    gates_passed=gates_passed,
                    gates_failed=gates_failed,
                )
            gates_passed.append("workspace_binding")

            # Check path validation
            gates_checked.append("path_constraints")
            if not request.path_constraints_validated:
                gates_failed.append("path_constraints")
                return self._blocked_result(
                    action_class=action_class,
                    reason_code=GuardBlockReasonCode.MISSING_PATH_VALIDATION,
                    reason_human="D3_WRITE_SANDBOX requires path constraint validation",
                    gates_checked=gates_checked,
                    gates_passed=gates_passed,
                    gates_failed=gates_failed,
                )
            gates_passed.append("path_constraints")

            # Check capability token
            gates_checked.append("capability_token")
            if not request.capability_token_present:
                gates_failed.append("capability_token")
                return self._blocked_result(
                    action_class=action_class,
                    reason_code=GuardBlockReasonCode.MISSING_CAPABILITY_TOKEN,
                    reason_human="D3_WRITE_SANDBOX requires capability token",
                    gates_checked=gates_checked,
                    gates_passed=gates_passed,
                    gates_failed=gates_failed,
                )
            gates_passed.append("capability_token")

            # Check security gate
            gates_checked.append("security_gate")
            if not request.security_gate_passed:
                gates_failed.append("security_gate")
                return self._blocked_result(
                    action_class=action_class,
                    reason_code=GuardBlockReasonCode.MISSING_SECURITY_GATE,
                    reason_human="D3_WRITE_SANDBOX requires security gate",
                    gates_checked=gates_checked,
                    gates_passed=gates_passed,
                    gates_failed=gates_failed,
                )
            gates_passed.append("security_gate")

            # All D3 gates passed - allow as dry-run/sandbox only
            return self._allow_dry_run_result(
                action_class=action_class,
                reason_code=GuardBlockReasonCode.OK_SANDBOX,
                reason_human="D3_WRITE_SANDBOX allowed (dry-run/sandbox only)",
                gates_checked=gates_checked,
                gates_passed=gates_passed,
                gates_failed=gates_failed,
            )

        # Gate 4: D4 - Repo write BLOCKED in Phase 1
        if action_class == DestructiveActionClass.D4_WRITE_REPO:
            gates_checked.append("phase1_d4_block")
            gates_failed.append("phase1_d4_block")
            return self._blocked_result(
                action_class=action_class,
                reason_code=GuardBlockReasonCode.BLOCKED_D4_REPO_WRITE_PHASE1,
                reason_human="D4_WRITE_REPO blocked in Phase 1",
                gates_checked=gates_checked,
                gates_passed=gates_passed,
                gates_failed=gates_failed,
            )

        # Gate 5: D5 - External side effect BLOCKED in Phase 1
        if action_class == DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT:
            gates_checked.append("phase1_d5_block")
            gates_failed.append("phase1_d5_block")
            return self._blocked_result(
                action_class=action_class,
                reason_code=GuardBlockReasonCode.BLOCKED_D5_EXTERNAL_PHASE1,
                reason_human="D5_EXTERNAL_SIDE_EFFECT blocked in Phase 1",
                gates_checked=gates_checked,
                gates_passed=gates_passed,
                gates_failed=gates_failed,
            )

        # Gate 6: D6 - Irreversible BLOCKED in Phase 1
        if action_class == DestructiveActionClass.D6_IRREVERSIBLE:
            gates_checked.append("phase1_d6_block")
            gates_failed.append("phase1_d6_block")
            return self._blocked_result(
                action_class=action_class,
                reason_code=GuardBlockReasonCode.BLOCKED_D6_IRREVERSIBLE_PHASE1,
                reason_human="D6_IRREVERSIBLE blocked in Phase 1",
                gates_checked=gates_checked,
                gates_passed=gates_passed,
                gates_failed=gates_failed,
            )

        # Fallback: Unknown class
        return self._blocked_result(
            action_class=action_class,
            reason_code=GuardBlockReasonCode.BLOCKED_UNKNOWN_CLASS,
            reason_human=f"Unknown or unhandled action class: {action_class}",
            gates_checked=gates_checked,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
        )

    def _allow_dry_run_result(
        self,
        action_class: DestructiveActionClass,
        reason_code: GuardBlockReasonCode,
        reason_human: str,
        gates_checked: List[str],
        gates_passed: List[str],
        gates_failed: List[str],
    ) -> DestructiveActionGuardResult:
        """Create an ALLOW_DRY_RUN result."""
        return DestructiveActionGuardResult(
            allowed=True,
            decision=GuardDecision.ALLOW_DRY_RUN,
            reason_code=reason_code,
            destructive_class=action_class,
            dry_run_only=True,
            # WSP 97 Truth Fields - ALWAYS False
            live_execution_allowed=False,
            repo_created=False,
            production_source_modified=False,
            external_federation_initiated=False,
            verification_complete=False,
            cabr_ready=False,
            payout_ready=False,
            # Context
            reason_human=reason_human,
            gates_checked=gates_checked,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
        )

    def _blocked_result(
        self,
        action_class: DestructiveActionClass,
        reason_code: GuardBlockReasonCode,
        reason_human: str,
        gates_checked: List[str],
        gates_passed: List[str],
        gates_failed: List[str],
    ) -> DestructiveActionGuardResult:
        """Create a BLOCKED result."""
        return DestructiveActionGuardResult(
            allowed=False,
            decision=GuardDecision.BLOCKED,
            reason_code=reason_code,
            destructive_class=action_class,
            dry_run_only=True,
            # WSP 97 Truth Fields - ALWAYS False
            live_execution_allowed=False,
            repo_created=False,
            production_source_modified=False,
            external_federation_initiated=False,
            verification_complete=False,
            cabr_ready=False,
            payout_ready=False,
            # Context
            reason_human=reason_human,
            gates_checked=gates_checked,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
        )


# ===========================================================================
# SECTION 6: Module-Level Convenience Functions
# ===========================================================================

_guard_singleton: Optional[DestructiveActionGuard] = None


def get_destructive_action_guard() -> DestructiveActionGuard:
    """Get or create singleton DestructiveActionGuard."""
    global _guard_singleton
    if _guard_singleton is None:
        _guard_singleton = DestructiveActionGuard()
    return _guard_singleton


def evaluate_destructive_action(
    request: DestructiveActionRequest,
) -> DestructiveActionGuardResult:
    """
    Convenience function to evaluate a destructive action request.

    Uses default singleton guard with Phase 1 constraints.

    Args:
        request: DestructiveActionRequest to evaluate

    Returns:
        DestructiveActionGuardResult with decision and truth fields

    WSP 97: This does NOT perform the action. It only evaluates permission.
    """
    return get_destructive_action_guard().evaluate(request)


# ===========================================================================
# SECTION 7: Path Canonicalization Utilities (P0 Symlink Fix)
# ===========================================================================


# Control character pattern: ASCII 0x00-0x1F except tab (0x09), newline (0x0A), CR (0x0D)
# We block ALL control chars including tab/newline/CR for path safety
_CONTROL_CHAR_PATTERN = re.compile(r'[\x00-\x1f]')


@dataclass
class PathCanonicalizeResult:
    """Result of path canonicalization."""

    is_safe: bool
    """Whether the path is safe (no control chars, resolvable)."""

    canonical_path: str
    """The canonicalized path (empty if not safe)."""

    original_path: str
    """The original input path."""

    reason: str
    """Human-readable reason if not safe, empty otherwise."""

    resolved_symlinks: bool
    """Whether symlinks were resolved."""


def canonicalize_path(path: str) -> PathCanonicalizeResult:
    """
    Canonicalize a path with full symlink resolution.

    This function:
    1. Checks for control characters (BLOCKED)
    2. Checks for UNC paths on Windows (BLOCKED)
    3. Resolves symlinks via os.path.realpath()
    4. Normalizes separators
    5. Applies case normalization on Windows

    Args:
        path: The path to canonicalize

    Returns:
        PathCanonicalizeResult with safety status and canonical path

    WSP 97: This is a validation utility. No filesystem modification.
    """
    if not path or not path.strip():
        return PathCanonicalizeResult(
            is_safe=False,
            canonical_path="",
            original_path=path,
            reason="Empty or whitespace-only path",
            resolved_symlinks=False,
        )

    # Check for control characters (P1 fix)
    if _CONTROL_CHAR_PATTERN.search(path):
        return PathCanonicalizeResult(
            is_safe=False,
            canonical_path="",
            original_path=path,
            reason="Path contains control characters",
            resolved_symlinks=False,
        )

    # Check for UNC paths (P1 fix)
    if path.startswith("\\\\") or path.startswith("//"):
        return PathCanonicalizeResult(
            is_safe=False,
            canonical_path="",
            original_path=path,
            reason="UNC paths are blocked",
            resolved_symlinks=False,
        )

    # Check for Windows device paths
    if path.startswith("\\\\.\\"):
        return PathCanonicalizeResult(
            is_safe=False,
            canonical_path="",
            original_path=path,
            reason="Windows device paths are blocked",
            resolved_symlinks=False,
        )

    # Check for Windows long path prefix
    if path.startswith("\\\\?\\"):
        return PathCanonicalizeResult(
            is_safe=False,
            canonical_path="",
            original_path=path,
            reason="Windows long path prefix blocked",
            resolved_symlinks=False,
        )

    try:
        # First normalize to handle .. components
        normalized = os.path.normpath(path)

        # Apply case normalization on Windows (P1 fix)
        if sys.platform == "win32":
            normalized = os.path.normcase(normalized)

        # Resolve symlinks (P0 fix) - this is the critical security fix
        # os.path.realpath resolves all symlinks to get the actual path
        resolved = os.path.realpath(normalized)

        # Apply case normalization again after resolution on Windows
        if sys.platform == "win32":
            resolved = os.path.normcase(resolved)

        # Normalize separators to forward slash for consistent comparison
        canonical = resolved.replace("\\", "/")

        return PathCanonicalizeResult(
            is_safe=True,
            canonical_path=canonical,
            original_path=path,
            reason="",
            resolved_symlinks=(normalized != resolved),
        )

    except OSError as e:
        # Fail-closed on any resolution error
        return PathCanonicalizeResult(
            is_safe=False,
            canonical_path="",
            original_path=path,
            reason=f"Path resolution failed: {e}",
            resolved_symlinks=False,
        )


class PathConstraintValidator:
    """
    Path constraint validator with full symlink resolution.

    This class provides path validation that:
    1. Canonicalizes paths (resolves symlinks, normalizes)
    2. Checks against allowed roots (after canonicalization)
    3. Checks against blocked paths (after canonicalization)

    Key Principle: FAIL-CLOSED
    - Unknown/unresolvable paths are blocked
    - Symlinks are resolved before boundary checking
    - Control characters are blocked

    WSP 97: This is a validation utility. No filesystem modification.

    Slice: DESTRUCTIVE_ACTION_GUARD_PATH_CANONICALIZATION_IMPL_PHASE1
    """

    def __init__(
        self,
        allowed_paths: List[str],
        blocked_paths: Optional[List[str]] = None,
    ):
        """
        Initialize validator with allowed and blocked paths.

        Args:
            allowed_paths: List of allowed root paths
            blocked_paths: Optional list of blocked paths (override allowed)
        """
        self.allowed_paths = allowed_paths or []
        self.blocked_paths = blocked_paths or []

        # Pre-canonicalize allowed/blocked for comparison
        self._canonical_allowed: List[str] = []
        self._canonical_blocked: List[str] = []

        for ap in self.allowed_paths:
            result = canonicalize_path(ap)
            if result.is_safe:
                self._canonical_allowed.append(result.canonical_path)

        for bp in self.blocked_paths:
            result = canonicalize_path(bp)
            if result.is_safe:
                self._canonical_blocked.append(result.canonical_path)

    def is_path_allowed(self, target_path: str) -> bool:
        """
        Check if a path is allowed after full canonicalization.

        This method:
        1. Canonicalizes the target path (resolves symlinks)
        2. Checks against blocked paths first (override)
        3. Checks against allowed paths

        Args:
            target_path: The path to check

        Returns:
            True if path is allowed, False otherwise (fail-closed)
        """
        # Canonicalize target path
        result = canonicalize_path(target_path)

        if not result.is_safe:
            # Fail-closed: unsafe paths are blocked
            return False

        canonical = result.canonical_path

        # Check blocked paths first (override)
        for blocked in self._canonical_blocked:
            if canonical == blocked or canonical.startswith(blocked + "/"):
                return False

        # Check allowed paths
        for allowed in self._canonical_allowed:
            if canonical == allowed or canonical.startswith(allowed + "/"):
                return True

        # Fail-closed: not in any allowed path
        return False

    def validate_path(self, target_path: str) -> Tuple[bool, str]:
        """
        Validate a path with detailed reason.

        Args:
            target_path: The path to validate

        Returns:
            Tuple of (is_allowed, reason)
        """
        result = canonicalize_path(target_path)

        if not result.is_safe:
            return False, f"Path canonicalization failed: {result.reason}"

        canonical = result.canonical_path

        # Check blocked paths first
        for blocked in self._canonical_blocked:
            if canonical == blocked or canonical.startswith(blocked + "/"):
                return False, f"Path is in blocked list: {blocked}"

        # Check allowed paths
        for allowed in self._canonical_allowed:
            if canonical == allowed or canonical.startswith(allowed + "/"):
                return True, f"Path allowed under: {allowed}"

        return False, "Path not in any allowed root (fail-closed)"
