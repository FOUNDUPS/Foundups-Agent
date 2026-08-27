#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ImprovementJob Contract — Codebase Self-Improvement Orchestration

Typed contract for OpenClaw/WRE codebase repair, cleanup, and enhancement jobs.
Distinct from FoundUpJob (which builds FoundUps). ImprovementJob repairs the
codebase itself based on FMAS findings, WSP violations, orphan capabilities, etc.

Architecture:
  OpenClaw IMPROVEMENT Intent -> ImprovementJob (PENDING)
  -> Architect Review (if MEDIUM/HIGH risk)
  -> Worker Assignment
  -> Execution (dry_run=True default)
  -> Validation (FMAS/tests)
  -> Completion (ModLog update)

WSP Compliance:
  WSP 11  : Interface contract (typed API)
  WSP 15  : Low-lying fruit priority scoring
  WSP 50  : Pre-Action Verification (validate_scope)
  WSP 77  : Agent Coordination (worker assignment)
  WSP 91  : Observability (timestamps, evidence)
  WSP 97  : System Execution Prompting (dry_run=True default, no overclaims)

WSP 97 TRUTH BOUNDARIES:
  - dry_run=True by default (no production execution without explicit approval)
  - No CABR/payout/reward/token fields (not a FoundUp, no economic layer)
  - No execution methods (contract only, execution is separate)
  - MEDIUM/HIGH risk requires architect review before execution

NAVIGATION:
  -> Pattern: foundup_job_contract.py (FoundUpJob)
  -> Used by: execute_improvement (future), improvement_router (future)
  -> Validates: WSP_MODULE_VIOLATIONS.md entries, FMAS findings, orphan reports
"""

from __future__ import annotations

import fnmatch
import json
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .improvement_job_identity import (
    canonical_improvement_repo_path,
    generate_idempotent_improvement_job_id,
)

logger = logging.getLogger("improvement_job_contract")


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Improvement Type
# ---------------------------------------------------------------------------


class ImprovementType(str, Enum):
    """
    Classification of improvement task.

    Maps to execute_improvement sub-types in openclaw_execution_routes.py.
    """

    WSP_VIOLATION = "wsp_violation"
    """Fix WSP protocol violations (structure, naming, etc.)."""

    MODULE_REPAIR = "module_repair"
    """Repair module structure, missing files, broken imports."""

    TEST_HYGIENE = "test_hygiene"
    """Fix stale tests, missing coverage, broken fixtures."""

    ORPHAN_CONNECTION = "orphan_connection"
    """Connect orphaned CLI capabilities to WRE via SKILLz.md."""

    DRIFT_CORRECTION = "drift_correction"
    """Correct code drift, duplicate modules, stale references."""

    FMAS_SCAN = "fmas_scan"
    """Execute FMAS scan and remediate findings."""

    DOC_LEDGER_HYGIENE = "doc_ledger_hygiene"
    """Update ModLog, TestModLog, ROADMAP, README documentation."""


# ---------------------------------------------------------------------------
# Improvement Status
# ---------------------------------------------------------------------------


class ImprovementStatus(str, Enum):
    """
    ImprovementJob lifecycle states.

    State machine:
      PENDING -> APPROVED -> EXECUTING -> VALIDATING -> COMPLETED
                    |            |            |
                    |            +-> FAILED   +-> FAILED
                    |
                    +-> BLOCKED (requires architect review)
    """

    PENDING = "pending"
    """Job created, awaiting approval or auto-approval."""

    APPROVED = "approved"
    """Approved for execution (LOW risk auto-approved, MEDIUM/HIGH by architect)."""

    EXECUTING = "executing"
    """Worker executing repair."""

    VALIDATING = "validating"
    """Post-execution validation (FMAS/tests)."""

    COMPLETED = "completed"
    """Terminal: repair completed and validated."""

    FAILED = "failed"
    """Terminal: repair or validation failed."""

    BLOCKED = "blocked"
    """Blocked awaiting architect review or external dependency."""


# Valid state transitions
_VALID_TRANSITIONS: Dict[ImprovementStatus, frozenset[ImprovementStatus]] = {
    ImprovementStatus.PENDING: frozenset({
        ImprovementStatus.APPROVED,
        ImprovementStatus.BLOCKED,
        ImprovementStatus.FAILED,
    }),
    ImprovementStatus.APPROVED: frozenset({
        ImprovementStatus.EXECUTING,
        ImprovementStatus.BLOCKED,
        ImprovementStatus.FAILED,
    }),
    ImprovementStatus.EXECUTING: frozenset({
        ImprovementStatus.VALIDATING,
        ImprovementStatus.FAILED,
    }),
    ImprovementStatus.VALIDATING: frozenset({
        ImprovementStatus.COMPLETED,
        ImprovementStatus.FAILED,
    }),
    ImprovementStatus.BLOCKED: frozenset({
        ImprovementStatus.APPROVED,
        ImprovementStatus.FAILED,
    }),
    ImprovementStatus.COMPLETED: frozenset(),  # Terminal
    ImprovementStatus.FAILED: frozenset(),     # Terminal
}


def is_valid_improvement_transition(
    from_status: ImprovementStatus,
    to_status: ImprovementStatus,
) -> bool:
    """Check if state transition is allowed."""
    return to_status in _VALID_TRANSITIONS.get(from_status, frozenset())


def is_terminal_improvement_status(status: ImprovementStatus) -> bool:
    """Check if status is terminal (no further transitions)."""
    return status in (ImprovementStatus.COMPLETED, ImprovementStatus.FAILED)


# ---------------------------------------------------------------------------
# Risk Level
# ---------------------------------------------------------------------------


class ImprovementRiskLevel(str, Enum):
    """
    Risk classification for improvement job.

    Determines approval requirements:
      LOW    : Auto-approve if low_lying_fruit=True
      MEDIUM : Requires architect review
      HIGH   : Requires architect review + explicit approval
    """

    LOW = "low"
    """Safe change: documentation, comments, trivial fixes."""

    MEDIUM = "medium"
    """Moderate change: module restructuring, interface changes."""

    HIGH = "high"
    """Risky change: cross-module refactoring, security-related."""


# ---------------------------------------------------------------------------
# Status Reason Codes
# ---------------------------------------------------------------------------


class ImprovementReasonCode(str, Enum):
    """Machine-readable status reason codes for ImprovementJob."""

    # Success
    OK_COMPLETED = "OK_COMPLETED"
    OK_DRY_RUN_PASSED = "OK_DRY_RUN_PASSED"
    OK_VALIDATION_PASSED = "OK_VALIDATION_PASSED"
    OK_AUTO_APPROVED = "OK_AUTO_APPROVED"
    OK_ARCHITECT_APPROVED = "OK_ARCHITECT_APPROVED"

    # Blocked
    BLOCKED_REQUIRES_ARCHITECT_REVIEW = "BLOCKED_REQUIRES_ARCHITECT_REVIEW"
    BLOCKED_SCOPE_VIOLATION = "BLOCKED_SCOPE_VIOLATION"
    BLOCKED_DEPENDENCY_MISSING = "BLOCKED_DEPENDENCY_MISSING"

    # Failed - Validation
    FAIL_VALIDATION_ERROR = "FAIL_VALIDATION_ERROR"
    FAIL_FMAS_CHECK = "FAIL_FMAS_CHECK"
    FAIL_TEST_FAILURE = "FAIL_TEST_FAILURE"
    FAIL_SCOPE_VIOLATION = "FAIL_SCOPE_VIOLATION"

    # Failed - Execution
    FAIL_EXECUTION_ERROR = "FAIL_EXECUTION_ERROR"
    FAIL_WORKER_UNAVAILABLE = "FAIL_WORKER_UNAVAILABLE"

    # Failed - State
    FAIL_INVALID_TRANSITION = "FAIL_INVALID_TRANSITION"

    # Unknown
    UNKNOWN = "UNKNOWN"


def _parse_improvement_reason_code(value: str) -> ImprovementReasonCode:
    """Parse reason code string, falling back to UNKNOWN if invalid."""
    try:
        return ImprovementReasonCode(value)
    except ValueError:
        return ImprovementReasonCode.UNKNOWN


# ---------------------------------------------------------------------------
# WSP 15 Priority
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class WSP15Priority:
    """
    Legacy WSP-15-inspired execution-risk hints.

    This is not canonical numeric WSP 15 C/I/D/Impact MPS evidence and must
    not be serialized as an allocation receipt. It only preserves compatibility
    hints for local ordering until an architect supplies real MPS scores.
    """

    low_lying_fruit: bool = False
    """True if this is a low-effort, high-impact fix."""

    estimated_complexity: str = "unknown"
    """Complexity estimate: trivial, simple, moderate, complex."""

    blast_radius: str = "single_file"
    """Impact scope: single_file, single_module, cross_module, system_wide."""

    requires_architect_review: bool = True
    """True if architect must review before execution."""

    reason: str = ""
    """Human-readable explanation of priority scoring."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "low_lying_fruit": self.low_lying_fruit,
            "estimated_complexity": self.estimated_complexity,
            "blast_radius": self.blast_radius,
            "requires_architect_review": self.requires_architect_review,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WSP15Priority:
        """Deserialize from dict."""
        return cls(
            low_lying_fruit=bool(data.get("low_lying_fruit", False)),
            estimated_complexity=data.get("estimated_complexity", "unknown"),
            blast_radius=data.get("blast_radius", "single_file"),
            requires_architect_review=bool(data.get("requires_architect_review", True)),
            reason=data.get("reason", ""),
        )

    @classmethod
    def for_low_risk(cls, reason: str = "Auto-classified as low-risk") -> WSP15Priority:
        """Factory for low-risk proposal hints; no execution authority."""
        return cls(
            low_lying_fruit=True,
            estimated_complexity="trivial",
            blast_radius="single_file",
            requires_architect_review=False,
            reason=reason,
        )

    @classmethod
    def for_medium_risk(cls, reason: str = "Requires architect review") -> WSP15Priority:
        """Factory for medium-risk improvements requiring review."""
        return cls(
            low_lying_fruit=False,
            estimated_complexity="moderate",
            blast_radius="single_module",
            requires_architect_review=True,
            reason=reason,
        )

    @classmethod
    def for_high_risk(cls, reason: str = "Cross-module impact") -> WSP15Priority:
        """Factory for high-risk improvements requiring explicit approval."""
        return cls(
            low_lying_fruit=False,
            estimated_complexity="complex",
            blast_radius="cross_module",
            requires_architect_review=True,
            reason=reason,
        )


# ---------------------------------------------------------------------------
# Improvement Scope
# ---------------------------------------------------------------------------


@dataclass
class ImprovementScope:
    """
    Bounded scope for improvement job.

    Defines what paths can be modified and which are blocked.
    Used by validate_scope() to enforce boundaries.
    """

    module_path: str = ""
    """Primary module being improved (e.g., 'modules/infrastructure/wre_core')."""

    file_paths: List[str] = field(default_factory=list)
    """Specific files to modify (if empty, module_path determines scope)."""

    wsp_refs: List[str] = field(default_factory=list)
    """WSP protocols relevant to this improvement (e.g., ['WSP 49', 'WSP 22'])."""

    allowed_paths: List[str] = field(default_factory=list)
    """Glob patterns for allowed paths. If empty, module_path is used."""

    blocked_paths: List[str] = field(default_factory=list)
    """Glob patterns for blocked paths (always denied)."""

    def __post_init__(self) -> None:
        """Set default allowed_paths if not provided."""
        if not self.allowed_paths and self.module_path:
            # Default: allow anything under module_path
            self.allowed_paths = [f"{self.module_path}/**"]

    def validate_path(self, path: str) -> bool:
        """
        Check if a path is within allowed scope.

        Args:
            path: Path to validate (relative or absolute).

        Returns:
            True if path is allowed, False if blocked or out of scope.
        """
        path_str = canonical_improvement_repo_path(str(path))
        if path_str is None:
            return False
        module_path = canonical_improvement_repo_path(self.module_path)
        if self.module_path and module_path is None:
            return False
        if module_path and not (
            path_str == module_path or path_str.startswith(f"{module_path}/")
        ):
            return False

        # Check blocked paths first (deny takes precedence)
        for blocked in self.blocked_paths:
            blocked_pattern = canonical_improvement_repo_path(blocked, allow_glob=True)
            if blocked_pattern is None:
                return False
            if fnmatch.fnmatch(path_str, blocked_pattern):
                return False

        # If file_paths specified, check exact match
        if self.file_paths:
            for allowed_file in self.file_paths:
                expected = canonical_improvement_repo_path(allowed_file)
                if expected is None:
                    return False
                if module_path and not expected.startswith("modules/"):
                    expected = f"{module_path}/{expected}"
                if path_str == expected:
                    return True
            return False

        # Check allowed patterns
        for allowed in self.allowed_paths:
            allowed_pattern = canonical_improvement_repo_path(allowed, allow_glob=True)
            if allowed_pattern is None:
                return False
            if fnmatch.fnmatch(path_str, allowed_pattern):
                return True

        return False

    def is_well_formed(self) -> bool:
        """Return whether every declared scope path is canonical and confined."""
        module_path = canonical_improvement_repo_path(self.module_path)
        if self.module_path and module_path is None:
            return False
        if not module_path and not self.file_paths:
            return False
        for path in self.file_paths:
            canonical = canonical_improvement_repo_path(path)
            if canonical is None:
                return False
            if module_path and not (
                canonical == module_path or canonical.startswith(f"{module_path}/")
            ):
                return False
            if not self.validate_path(canonical):
                return False
        for pattern in (*self.allowed_paths, *self.blocked_paths):
            if canonical_improvement_repo_path(pattern, allow_glob=True) is None:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "module_path": self.module_path,
            "file_paths": self.file_paths,
            "wsp_refs": self.wsp_refs,
            "allowed_paths": self.allowed_paths,
            "blocked_paths": self.blocked_paths,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ImprovementScope:
        """Deserialize from dict."""
        return cls(
            module_path=data.get("module_path", ""),
            file_paths=data.get("file_paths", []),
            wsp_refs=data.get("wsp_refs", []),
            allowed_paths=data.get("allowed_paths", []),
            blocked_paths=data.get("blocked_paths", []),
        )


# ---------------------------------------------------------------------------
# ImprovementJob Contract
# ---------------------------------------------------------------------------


@dataclass
class ImprovementJob:
    """
    Codebase improvement job contract.

    Typed wrapper for repair/enhancement tasks originating from:
      - FMAS findings
      - WSP_MODULE_VIOLATIONS.md entries
      - OrphanCapabilityScanner reports
      - Manual improvement intents via OpenClaw

    WSP 97 Truth Boundaries:
      - dry_run=True by default (no production changes without explicit approval)
      - No CABR/payout/reward/token fields (improvement, not economic activity)
      - No execution methods (contract defines state, not behavior)
      - MEDIUM/HIGH risk always requires architect review
    """

    # === Core Identity ===
    job_id: str
    """Unique job identifier. Format: imp_{type}_{timestamp_hex}_{random_hex}"""

    finding_id: str
    """Source finding ID (FMAS finding, violation ID, orphan ID, etc.)."""

    improvement_type: ImprovementType
    """Classification of improvement task."""

    # === Lifecycle ===
    status: ImprovementStatus = ImprovementStatus.PENDING
    """Current lifecycle state."""

    previous_status: Optional[ImprovementStatus] = None
    """Previous state (for audit trail)."""

    # === Scope ===
    scope: ImprovementScope = field(default_factory=ImprovementScope)
    """Bounded scope for this improvement."""

    # === Control Flags ===
    dry_run: bool = True
    """
    WSP 97: True by default. When True, no actual changes are made.
    Must be explicitly set to False for production execution.
    """

    risk_level: ImprovementRiskLevel = ImprovementRiskLevel.MEDIUM
    """Risk classification. Determines approval requirements."""

    wsp15_priority: WSP15Priority = field(default_factory=WSP15Priority)
    """WSP 15 low-lying fruit scoring."""

    # === Assignment ===
    requested_by: str = ""
    """Requestor identity (OpenClaw sender, 012, or system)."""

    assigned_worker: Optional[str] = None
    """Assigned worker (W1/W4/W5/etc.) when status reaches EXECUTING."""

    # === Timestamps ===
    created_at: datetime = field(default_factory=utc_now)
    """Job creation timestamp."""

    approved_at: Optional[datetime] = None
    """Approval timestamp (when status -> APPROVED)."""

    completed_at: Optional[datetime] = None
    """Completion timestamp (when status -> COMPLETED|FAILED)."""

    # === Truth/Audit Fields (WSP 97) ===
    status_reason_code: ImprovementReasonCode = ImprovementReasonCode.UNKNOWN
    """Machine-readable status reason."""

    status_reason_human: str = ""
    """Operator-readable status explanation."""

    evidence_refs: List[str] = field(default_factory=list)
    """
    Paths/IDs proving outcome.
    Examples: ['WSP_MODULE_VIOLATIONS.md#V022', 'FMAS_finding_abc123']
    """

    validation_refs: List[str] = field(default_factory=list)
    """
    Validation evidence (FMAS pass, test results).
    Examples: ['fmas_report_xyz.json', 'pytest_results.xml']
    """

    # === Payload ===
    payload: Dict[str, Any] = field(default_factory=dict)
    """
    Improvement-specific payload. Structure depends on improvement_type.
    May include: file_changes, commands_to_run, etc.
    """

    # === Internal ===
    _transition_history: List[Dict[str, Any]] = field(default_factory=list)
    """Internal: records all state transitions for debugging."""

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """Validate required fields and normalize enums."""
        if not self.job_id or not self.job_id.strip():
            raise ValueError("job_id is required")
        if not self.finding_id or not self.finding_id.strip():
            raise ValueError("finding_id is required")

        # Normalize enums from strings
        if isinstance(self.improvement_type, str):
            self.improvement_type = ImprovementType(self.improvement_type)
        if isinstance(self.status, str):
            self.status = ImprovementStatus(self.status)
        if isinstance(self.previous_status, str):
            self.previous_status = ImprovementStatus(self.previous_status)
        if isinstance(self.risk_level, str):
            self.risk_level = ImprovementRiskLevel(self.risk_level)
        if isinstance(self.status_reason_code, str):
            self.status_reason_code = _parse_improvement_reason_code(
                self.status_reason_code
            )

        # Normalize nested dataclasses
        if isinstance(self.scope, dict):
            self.scope = ImprovementScope.from_dict(self.scope)
        if isinstance(self.wsp15_priority, dict):
            self.wsp15_priority = WSP15Priority.from_dict(self.wsp15_priority)

        # Enforce architect review for MEDIUM/HIGH risk
        if self.risk_level in (ImprovementRiskLevel.MEDIUM, ImprovementRiskLevel.HIGH):
            self.wsp15_priority.requires_architect_review = True

    # ------------------------------------------------------------------
    # Scope Validation
    # ------------------------------------------------------------------

    def validate_scope(self, path: str) -> bool:
        """
        Check if a path is within allowed scope for this job.

        Args:
            path: Path to validate.

        Returns:
            True if path is allowed, False if blocked or out of scope.
        """
        return self.scope.validate_path(path)

    # ------------------------------------------------------------------
    # Approval Logic
    # ------------------------------------------------------------------

    def can_auto_approve(self) -> bool:
        """
        Check local eligibility only; this is not provenance or effect authority.

        Returns:
            True if LOW risk, bounded scope, low_lying_fruit, and dry_run=True.
        """
        return (
            self.risk_level == ImprovementRiskLevel.LOW
            and self.wsp15_priority.low_lying_fruit
            and not self.wsp15_priority.requires_architect_review
            and self.dry_run
            and self.scope.is_well_formed()
        )

    def requires_architect_review(self) -> bool:
        """
        Check if architect review is required before execution.

        Returns:
            True if MEDIUM/HIGH risk OR requires_architect_review=True.
        """
        return (
            self.risk_level in (ImprovementRiskLevel.MEDIUM, ImprovementRiskLevel.HIGH)
            or self.wsp15_priority.requires_architect_review
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize job to dict for logging/persistence."""
        return {
            "job_id": self.job_id,
            "finding_id": self.finding_id,
            "improvement_type": self.improvement_type.value,
            "status": self.status.value,
            "previous_status": (
                self.previous_status.value if self.previous_status else None
            ),
            "scope": self.scope.to_dict(),
            "dry_run": self.dry_run,
            "risk_level": self.risk_level.value,
            "wsp15_priority": self.wsp15_priority.to_dict(),
            "requested_by": self.requested_by,
            "assigned_worker": self.assigned_worker,
            "created_at": utc_iso(self.created_at),
            "approved_at": utc_iso(self.approved_at),
            "completed_at": utc_iso(self.completed_at),
            "status_reason_code": self.status_reason_code.value,
            "status_reason_human": self.status_reason_human,
            "evidence_refs": self.evidence_refs,
            "validation_refs": self.validation_refs,
            "payload": self.payload,
            "_transition_history": self._transition_history,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize job to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ImprovementJob:
        """Deserialize job from dict."""
        job = cls(
            job_id=data["job_id"],
            finding_id=data["finding_id"],
            improvement_type=ImprovementType(data["improvement_type"]),
            status=ImprovementStatus(data.get("status", "pending")),
            previous_status=(
                ImprovementStatus(data["previous_status"])
                if data.get("previous_status")
                else None
            ),
            scope=ImprovementScope.from_dict(data.get("scope", {})),
            dry_run=data.get("dry_run", True),
            risk_level=ImprovementRiskLevel(data.get("risk_level", "medium")),
            wsp15_priority=WSP15Priority.from_dict(data.get("wsp15_priority", {})),
            requested_by=data.get("requested_by", ""),
            assigned_worker=data.get("assigned_worker"),
            status_reason_code=_parse_improvement_reason_code(
                data.get("status_reason_code", "UNKNOWN")
            ),
            status_reason_human=data.get("status_reason_human", ""),
            evidence_refs=data.get("evidence_refs", []),
            validation_refs=data.get("validation_refs", []),
            payload=data.get("payload", {}),
        )

        # Restore timestamps
        for ts_field in ("created_at", "approved_at", "completed_at"):
            ts_value = data.get(ts_field)
            if ts_value:
                setattr(job, ts_field, datetime.fromisoformat(ts_value))

        # Restore transition history
        job._transition_history = data.get("_transition_history", [])

        return job


# ---------------------------------------------------------------------------
# Factory Functions
# ---------------------------------------------------------------------------


def generate_improvement_job_id(improvement_type: ImprovementType) -> str:
    """
    Generate unique improvement job ID.

    Format: imp_{type}_{timestamp_hex}_{random_hex}
    Example: imp_wsp_violation_18a3b2c1_f4e5d6
    """
    timestamp_hex = hex(int(utc_now().timestamp()))[2:][:8]
    random_hex = secrets.token_hex(3)
    type_slug = improvement_type.value.replace("_", "")[:12]
    return f"imp_{type_slug}_{timestamp_hex}_{random_hex}"


def create_improvement_job(
    finding_id: str,
    improvement_type: ImprovementType,
    scope: Optional[ImprovementScope] = None,
    risk_level: ImprovementRiskLevel = ImprovementRiskLevel.MEDIUM,
    requested_by: str = "system",
    payload: Optional[Dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
) -> ImprovementJob:
    """
    Factory function to create a new ImprovementJob.

    Args:
        finding_id: Source finding ID (FMAS, violation, orphan, etc.)
        improvement_type: Classification of improvement
        scope: Bounded scope (optional, defaults to empty)
        risk_level: Risk classification
        requested_by: Requestor identity
        payload: Improvement-specific payload

    Returns:
        ImprovementJob in PENDING state with dry_run=True.
    """
    job_id = (
        generate_idempotent_improvement_job_id(improvement_type, idempotency_key)
        if idempotency_key is not None
        else generate_improvement_job_id(improvement_type)
    )

    # Default priority based on risk level
    if risk_level == ImprovementRiskLevel.LOW:
        wsp15_priority = WSP15Priority.for_low_risk()
    elif risk_level == ImprovementRiskLevel.HIGH:
        wsp15_priority = WSP15Priority.for_high_risk()
    else:
        wsp15_priority = WSP15Priority.for_medium_risk()

    return ImprovementJob(
        job_id=job_id,
        finding_id=finding_id,
        improvement_type=improvement_type,
        scope=scope or ImprovementScope(),
        risk_level=risk_level,
        wsp15_priority=wsp15_priority,
        requested_by=requested_by,
        payload=payload or {},
    )
