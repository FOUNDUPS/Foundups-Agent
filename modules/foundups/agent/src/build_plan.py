#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BuildPlan Dataclass Contract — Typed FoundUp Build Orchestration

Implements the BuildPlan interface from FOUNDUP_BUILD_PLAN_CONTRACT.md.
Defines multi-step build plans with gates, steps, evidence, and scope constraints.

WSP 97 TRUTH BOUNDARIES:
  - dry_run=True by default
  - mode defaults to DRY_RUN
  - status defaults to DRAFT
  - Real builds require explicit human approval gate
  - No CABR/payout/reward fields exist in this contract

Architecture:
  BuildPlan defines the plan, not the executor.
  Execution is delegated to Hermes/WRE via FoundUpJob.

WSP Compliance:
  WSP 11  : Interface contract (typed API)
  WSP 50  : Pre-action validation (validate_scope)
  WSP 77  : Agent coordination (steps, gates)
  WSP 97  : Truth boundaries (is_real_build_allowed)

NAVIGATION:
  -> Spec: modules/foundups/docs/FOUNDUP_BUILD_PLAN_CONTRACT.md
  -> Uses: foundup_job_contract.py patterns (to_dict, from_dict)
  -> Called by: Future build orchestration (not implemented)
"""

from __future__ import annotations

import fnmatch
import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("build_plan")


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BuildPlanStatus(str, Enum):
    """
    BuildPlan lifecycle states.

    State machine:
      DRAFT -> APPROVED -> EXECUTING -> COMPLETED
                              |
                              +-> FAILED
                              +-> CANCELLED
    """

    DRAFT = "draft"
    """Plan created but not approved."""

    APPROVED = "approved"
    """Plan approved by human/architect."""

    EXECUTING = "executing"
    """Plan execution in progress."""

    COMPLETED = "completed"
    """Plan completed successfully."""

    FAILED = "failed"
    """Plan failed during execution."""

    CANCELLED = "cancelled"
    """Plan cancelled before completion."""


class BuildMode(str, Enum):
    """
    Build execution mode.

    WSP 97: DRY_RUN is default. REAL requires human_approval_gate.
    """

    DRY_RUN = "dry_run"
    """Simulated execution, no real changes."""

    REAL = "real"
    """Real execution, creates actual artifacts."""


class BuildScope(str, Enum):
    """Build target scope."""

    GENESIS_ONLY = "genesis_only"
    """Validate/create genesis artifacts only."""

    FULL_BUILD = "full_build"
    """Complete FoundUp build with all steps."""

    INCREMENTAL = "incremental"
    """Update existing FoundUp."""


class BuildStepAction(str, Enum):
    """Canonical build step actions."""

    VALIDATE_GENESIS = "validate_genesis"
    VALIDATE_MANIFEST = "validate_manifest"
    VALIDATE_STRUCTURE = "validate_structure"
    CREATE_SPEC = "create_spec"
    CREATE_TEST = "create_test"
    CREATE_MODULE = "create_module"
    CREATE_ADAPTERS = "create_adapters"
    UPDATE_MANIFEST = "update_manifest"
    UPDATE_MODLOG = "update_modlog"
    UPDATE_TESTMODLOG = "update_testmodlog"
    RUN_TESTS = "run_tests"
    DRY_RUN_BUILD = "dry_run_build"
    SUBMIT_RECEIPT = "submit_receipt"
    REQUEST_APPROVAL = "request_approval"
    ARCHIVE_BUILD = "archive_build"


class GateType(str, Enum):
    """Build gate types."""

    GENESIS_GATE = "genesis_gate"
    WSP_STRUCTURE_GATE = "wsp_structure_gate"
    MANIFEST_GATE = "manifest_gate"
    DRY_RUN_GATE = "dry_run_gate"
    TEST_GATE = "test_gate"
    MODLOG_GATE = "modlog_gate"
    PAVS_SUBMISSION_GATE = "pavs_submission_gate"
    HUMAN_APPROVAL_GATE = "human_approval_gate"


class GateStatus(str, Enum):
    """Gate evaluation status."""

    PENDING = "pending"
    """Gate not yet evaluated."""

    PASSED = "passed"
    """Gate passed."""

    FAILED = "failed"
    """Gate failed."""

    SKIPPED = "skipped"
    """Gate skipped (optional gate)."""


class StepStatus(str, Enum):
    """Step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Blocked Path Patterns (WSP 97)
# ---------------------------------------------------------------------------

# These paths are NEVER allowed in any build plan
BLOCKED_PATH_PATTERNS: frozenset[str] = frozenset({
    "**/wallet/**",
    "**/token/**",
    "**/reward/**",
    "**/payout/**",
    "**/cabr/**",
    "**/blockchain/**",
    "**/agent_market/**",
    "**/.env*",
    "**/credentials*",
    "**/secrets*",
})


def is_blocked_path(path: str) -> bool:
    """Check if a path matches any blocked pattern."""
    for pattern in BLOCKED_PATH_PATTERNS:
        if fnmatch.fnmatch(path, pattern):
            return True
        # Also check path components
        if fnmatch.fnmatch(str(Path(path)), pattern):
            return True
    return False


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class BuildTarget:
    """Build target location and scope constraints."""

    # Module location
    module_path: str
    """Module path, e.g. 'modules/foundups/voteballots'."""

    foundup_manifest_path: Optional[str] = None
    """Manifest path, auto-generated from module_path if not provided."""

    # Surface paths
    pwa_surface_path: Optional[str] = None
    """PWA surface path, e.g. 'public/member/foundups/voteballots/'."""

    tests_path: Optional[str] = None
    """Tests path, auto-generated from module_path if not provided."""

    docs_path: Optional[str] = None
    """Docs path, auto-generated from module_path if not provided."""

    # Required artifact paths
    modlog_path: Optional[str] = None
    testmodlog_path: Optional[str] = None
    readme_path: Optional[str] = None
    interface_path: Optional[str] = None

    # Scope boundaries
    allowed_paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Auto-populate paths from module_path."""
        if not self.foundup_manifest_path:
            self.foundup_manifest_path = f"{self.module_path}/foundup_manifest.json"
        if not self.tests_path:
            self.tests_path = f"{self.module_path}/tests/"
        if not self.docs_path:
            self.docs_path = f"{self.module_path}/docs/"
        if not self.modlog_path:
            self.modlog_path = f"{self.module_path}/ModLog.md"
        if not self.testmodlog_path:
            self.testmodlog_path = f"{self.module_path}/tests/TestModLog.md"
        if not self.readme_path:
            self.readme_path = f"{self.module_path}/README.md"

        # Default allowed paths
        if not self.allowed_paths:
            self.allowed_paths = [
                f"{self.module_path}/**",
            ]
            if self.pwa_surface_path:
                self.allowed_paths.append(f"{self.pwa_surface_path}/**")

        # Add global blocked paths
        self.blocked_paths.extend(BLOCKED_PATH_PATTERNS)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "module_path": self.module_path,
            "foundup_manifest_path": self.foundup_manifest_path,
            "pwa_surface_path": self.pwa_surface_path,
            "tests_path": self.tests_path,
            "docs_path": self.docs_path,
            "modlog_path": self.modlog_path,
            "testmodlog_path": self.testmodlog_path,
            "readme_path": self.readme_path,
            "interface_path": self.interface_path,
            "allowed_paths": self.allowed_paths,
            "blocked_paths": list(self.blocked_paths),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BuildTarget:
        """Deserialize from dictionary."""
        return cls(
            module_path=data["module_path"],
            foundup_manifest_path=data.get("foundup_manifest_path"),
            pwa_surface_path=data.get("pwa_surface_path"),
            tests_path=data.get("tests_path"),
            docs_path=data.get("docs_path"),
            modlog_path=data.get("modlog_path"),
            testmodlog_path=data.get("testmodlog_path"),
            readme_path=data.get("readme_path"),
            interface_path=data.get("interface_path"),
            allowed_paths=data.get("allowed_paths", []),
            blocked_paths=data.get("blocked_paths", []),
        )


@dataclass
class BuildGate:
    """Build gate definition and evaluation state."""

    gate_id: str
    """Unique gate identifier, e.g. 'genesis_gate'."""

    gate_type: GateType
    """Gate type enum."""

    gate_name: str = ""
    """Human-readable gate name."""

    required: bool = True
    """If True, build cannot proceed without passing."""

    status: GateStatus = GateStatus.PENDING
    """Gate evaluation status."""

    reason: Optional[str] = None
    """Explanation if failed."""

    checked_at: Optional[datetime] = None
    """Evaluation timestamp."""

    checked_by: Optional[str] = None
    """Evaluator: 'system' | worker_id | human_reviewer_id."""

    # Human approval gate specific fields
    approver_id: Optional[str] = None
    approval_method: str = "not_approved"
    approval_scope: Optional[str] = None

    def __post_init__(self) -> None:
        """Set gate name from type if not provided."""
        if not self.gate_name:
            self.gate_name = self.gate_type.value.replace("_", " ").title()

    @property
    def passed(self) -> bool:
        """Check if gate passed."""
        return self.status == GateStatus.PASSED

    @property
    def checked(self) -> bool:
        """Check if gate has been evaluated."""
        return self.status != GateStatus.PENDING

    def evaluate(
        self,
        passed: bool,
        reason: str,
        checked_by: str = "system",
    ) -> None:
        """Evaluate the gate."""
        self.status = GateStatus.PASSED if passed else GateStatus.FAILED
        self.reason = reason
        self.checked_at = utc_now()
        self.checked_by = checked_by

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "gate_id": self.gate_id,
            "gate_type": self.gate_type.value,
            "gate_name": self.gate_name,
            "required": self.required,
            "status": self.status.value,
            "passed": self.passed,
            "checked": self.checked,
            "reason": self.reason,
            "checked_at": utc_iso(self.checked_at),
            "checked_by": self.checked_by,
            "approver_id": self.approver_id,
            "approval_method": self.approval_method,
            "approval_scope": self.approval_scope,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BuildGate:
        """Deserialize from dictionary."""
        gate = cls(
            gate_id=data["gate_id"],
            gate_type=GateType(data["gate_type"]),
            gate_name=data.get("gate_name", ""),
            required=data.get("required", True),
            status=GateStatus(data.get("status", "pending")),
            reason=data.get("reason"),
            checked_by=data.get("checked_by"),
            approver_id=data.get("approver_id"),
            approval_method=data.get("approval_method", "not_approved"),
            approval_scope=data.get("approval_scope"),
        )
        if data.get("checked_at"):
            gate.checked_at = datetime.fromisoformat(data["checked_at"])
        return gate


@dataclass
class BuildStep:
    """Build step definition and execution state."""

    step_id: str
    """Step identifier, e.g. 'step_01'."""

    step_name: str
    """Human-readable step name."""

    action: BuildStepAction
    """Step action enum."""

    target_files: List[str] = field(default_factory=list)
    """Files to create/modify."""

    expected_outputs: List[str] = field(default_factory=list)
    """Expected result files/artifacts."""

    rollback_point: bool = False
    """If True, state can be restored to before this step."""

    rollback_command: Optional[str] = None
    """Command to execute rollback."""

    evidence_required: bool = True
    """If True, step must produce evidence_refs."""

    status: StepStatus = StepStatus.PENDING
    """Step execution status."""

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "step_id": self.step_id,
            "step_name": self.step_name,
            "action": self.action.value,
            "target_files": self.target_files,
            "expected_outputs": self.expected_outputs,
            "rollback_point": self.rollback_point,
            "rollback_command": self.rollback_command,
            "evidence_required": self.evidence_required,
            "status": self.status.value,
            "started_at": utc_iso(self.started_at),
            "completed_at": utc_iso(self.completed_at),
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BuildStep:
        """Deserialize from dictionary."""
        step = cls(
            step_id=data["step_id"],
            step_name=data["step_name"],
            action=BuildStepAction(data["action"]),
            target_files=data.get("target_files", []),
            expected_outputs=data.get("expected_outputs", []),
            rollback_point=data.get("rollback_point", False),
            rollback_command=data.get("rollback_command"),
            evidence_required=data.get("evidence_required", True),
            status=StepStatus(data.get("status", "pending")),
            error_message=data.get("error_message"),
        )
        if data.get("started_at"):
            step.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            step.completed_at = datetime.fromisoformat(data["completed_at"])
        return step


@dataclass
class BuildEvidence:
    """Build evidence reference."""

    file_path: str
    """Path to evidence file."""

    content_hash: Optional[str] = None
    """SHA256 hash of file content."""

    timestamp: datetime = field(default_factory=utc_now)
    """Evidence creation timestamp."""

    evidence_type: str = "file"
    """Evidence type: file, log, receipt, etc."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "file_path": self.file_path,
            "content_hash": self.content_hash,
            "timestamp": utc_iso(self.timestamp),
            "evidence_type": self.evidence_type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BuildEvidence:
        """Deserialize from dictionary."""
        evidence = cls(
            file_path=data["file_path"],
            content_hash=data.get("content_hash"),
            evidence_type=data.get("evidence_type", "file"),
        )
        if data.get("timestamp"):
            evidence.timestamp = datetime.fromisoformat(data["timestamp"])
        return evidence


# ---------------------------------------------------------------------------
# BuildPlan
# ---------------------------------------------------------------------------


@dataclass
class BuildPlan:
    """
    FoundUp Build Plan — Multi-step orchestration contract.

    WSP 97 Truth Boundaries:
      - dry_run=True by default
      - mode defaults to DRY_RUN
      - status defaults to DRAFT
      - Real builds require human_approval_gate
      - No CABR/payout/reward/token fields
    """

    # === Plan Identity ===
    build_plan_id: str
    """Unique: bp_{foundup_id}_{timestamp_hex}_{random}"""

    # === Source Context ===
    foundup_id: str
    """Target FoundUp (e.g., 'voteballots')."""

    tenant_id: str
    """Actor scope (e.g., '012')."""

    intent_id: Optional[str] = None
    """OpenClaw session correlation."""

    source_job_id: Optional[str] = None
    """FoundUpJob that triggered this plan."""

    # === Execution Mode ===
    requested_action: str = "build_foundup"
    """Canonical action."""

    mode: BuildMode = BuildMode.DRY_RUN
    """Build mode. Default: DRY_RUN."""

    dry_run: bool = True
    """Explicit dry_run flag. Default: True."""

    status: BuildPlanStatus = BuildPlanStatus.DRAFT
    """Plan status. Default: DRAFT."""

    # === Target ===
    target: Optional[BuildTarget] = None
    """Build target definition."""

    # === Steps ===
    steps: List[BuildStep] = field(default_factory=list)
    """Ordered build steps."""

    # === Gates ===
    gates: List[BuildGate] = field(default_factory=list)
    """Build gates."""

    # === Evidence ===
    evidence_refs: List[BuildEvidence] = field(default_factory=list)
    """Evidence references."""

    # === Timestamps ===
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    # === Versioning ===
    plan_version: str = "1.0.0"

    def __post_init__(self) -> None:
        """Validate and initialize defaults."""
        if not self.build_plan_id:
            raise ValueError("build_plan_id is required")
        if not self.foundup_id:
            raise ValueError("foundup_id is required")
        if not self.tenant_id:
            raise ValueError("tenant_id is required")

        # Ensure mode/status are enums
        if isinstance(self.mode, str):
            self.mode = BuildMode(self.mode)
        if isinstance(self.status, str):
            self.status = BuildPlanStatus(self.status)

        # Initialize default gates if not provided
        if not self.gates:
            self.gates = self._create_default_gates()

    def _create_default_gates(self) -> List[BuildGate]:
        """Create default gate set."""
        return [
            BuildGate(
                gate_id="genesis_gate",
                gate_type=GateType.GENESIS_GATE,
                required=True,
            ),
            BuildGate(
                gate_id="wsp_structure_gate",
                gate_type=GateType.WSP_STRUCTURE_GATE,
                required=True,
            ),
            BuildGate(
                gate_id="manifest_gate",
                gate_type=GateType.MANIFEST_GATE,
                required=True,
            ),
            BuildGate(
                gate_id="dry_run_gate",
                gate_type=GateType.DRY_RUN_GATE,
                required=True,
            ),
            BuildGate(
                gate_id="test_gate",
                gate_type=GateType.TEST_GATE,
                required=True,
            ),
            BuildGate(
                gate_id="modlog_gate",
                gate_type=GateType.MODLOG_GATE,
                required=True,
            ),
            BuildGate(
                gate_id="pavs_submission_gate",
                gate_type=GateType.PAVS_SUBMISSION_GATE,
                required=False,  # Only required for real builds
            ),
            BuildGate(
                gate_id="human_approval_gate",
                gate_type=GateType.HUMAN_APPROVAL_GATE,
                required=False,  # Only required for real builds
            ),
        ]

    # ------------------------------------------------------------------
    # Gate Queries
    # ------------------------------------------------------------------

    def get_gate(self, gate_type: GateType) -> Optional[BuildGate]:
        """Get gate by type."""
        for gate in self.gates:
            if gate.gate_type == gate_type:
                return gate
        return None

    def required_gates_passed(self) -> bool:
        """Check if all required gates have passed."""
        for gate in self.gates:
            if gate.required and not gate.passed:
                return False
        return True

    def get_failed_required_gates(self) -> List[BuildGate]:
        """Get list of required gates that failed or are pending."""
        return [
            gate for gate in self.gates
            if gate.required and not gate.passed
        ]

    # ------------------------------------------------------------------
    # Real Build Checks (WSP 97)
    # ------------------------------------------------------------------

    def is_real_build_allowed(self) -> bool:
        """
        Check if real (non-dry-run) build is allowed.

        WSP 97: Real builds require:
          - mode == REAL
          - dry_run == False
          - human_approval_gate passed
          - dry_run_gate passed (prior dry-run succeeded)
          - test_gate passed
          - Rollback points exist
        """
        # Mode and dry_run must be set for real
        if self.mode != BuildMode.REAL:
            return False
        if self.dry_run:
            return False

        # Human approval gate must pass
        human_gate = self.get_gate(GateType.HUMAN_APPROVAL_GATE)
        if not human_gate or not human_gate.passed:
            return False

        # Dry-run gate must pass (proves dry-run was done)
        dry_run_gate = self.get_gate(GateType.DRY_RUN_GATE)
        if not dry_run_gate or not dry_run_gate.passed:
            return False

        # Test gate must pass
        test_gate = self.get_gate(GateType.TEST_GATE)
        if not test_gate or not test_gate.passed:
            return False

        # Must have rollback points
        if not self.has_rollback_points():
            return False

        return True

    def has_rollback_points(self) -> bool:
        """Check if any step has rollback_point=True."""
        return any(step.rollback_point for step in self.steps)

    # ------------------------------------------------------------------
    # Scope Validation
    # ------------------------------------------------------------------

    def validate_scope(self, path: str) -> bool:
        """
        Validate that a path is within allowed scope.

        Args:
            path: Path to validate.

        Returns:
            True if path is allowed, False otherwise.
        """
        if not self.target:
            # No target defined, reject all paths
            return False

        # Check blocked paths first (takes precedence)
        for blocked in self.target.blocked_paths:
            if fnmatch.fnmatch(path, blocked):
                return False

        # Check if path is blocked by global patterns
        if is_blocked_path(path):
            return False

        # Check allowed paths
        for allowed in self.target.allowed_paths:
            if fnmatch.fnmatch(path, allowed):
                return True

        return False

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "build_plan_id": self.build_plan_id,
            "foundup_id": self.foundup_id,
            "tenant_id": self.tenant_id,
            "intent_id": self.intent_id,
            "source_job_id": self.source_job_id,
            "requested_action": self.requested_action,
            "mode": self.mode.value,
            "dry_run": self.dry_run,
            "status": self.status.value,
            "target": self.target.to_dict() if self.target else None,
            "steps": [step.to_dict() for step in self.steps],
            "gates": [gate.to_dict() for gate in self.gates],
            "evidence_refs": [ev.to_dict() for ev in self.evidence_refs],
            "created_at": utc_iso(self.created_at),
            "updated_at": utc_iso(self.updated_at),
            "plan_version": self.plan_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BuildPlan:
        """Deserialize from dictionary."""
        plan = cls(
            build_plan_id=data["build_plan_id"],
            foundup_id=data["foundup_id"],
            tenant_id=data["tenant_id"],
            intent_id=data.get("intent_id"),
            source_job_id=data.get("source_job_id"),
            requested_action=data.get("requested_action", "build_foundup"),
            mode=BuildMode(data.get("mode", "dry_run")),
            dry_run=data.get("dry_run", True),
            status=BuildPlanStatus(data.get("status", "draft")),
            plan_version=data.get("plan_version", "1.0.0"),
        )

        # Deserialize target
        if data.get("target"):
            plan.target = BuildTarget.from_dict(data["target"])

        # Deserialize steps
        plan.steps = [BuildStep.from_dict(s) for s in data.get("steps", [])]

        # Deserialize gates (replace defaults)
        if data.get("gates"):
            plan.gates = [BuildGate.from_dict(g) for g in data["gates"]]

        # Deserialize evidence
        plan.evidence_refs = [
            BuildEvidence.from_dict(e) for e in data.get("evidence_refs", [])
        ]

        # Restore timestamps
        if data.get("created_at"):
            plan.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            plan.updated_at = datetime.fromisoformat(data["updated_at"])

        return plan


# ---------------------------------------------------------------------------
# Factory Functions
# ---------------------------------------------------------------------------


def generate_build_plan_id(foundup_id: str) -> str:
    """
    Generate unique build plan ID.

    Format: bp_{foundup_id}_{timestamp_hex}_{random_hex}
    Example: bp_voteballots_66d1a2b3_abc123
    """
    timestamp_hex = hex(int(utc_now().timestamp()))[2:][:8]
    random_hex = secrets.token_hex(3)
    foundup_slug = foundup_id.lower().replace("-", "_")[:20]
    return f"bp_{foundup_slug}_{timestamp_hex}_{random_hex}"


def create_build_plan(
    foundup_id: str,
    tenant_id: str,
    module_path: str,
    intent_id: Optional[str] = None,
    source_job_id: Optional[str] = None,
) -> BuildPlan:
    """
    Factory function to create a new BuildPlan.

    Args:
        foundup_id: Target FoundUp ID
        tenant_id: Actor scope
        module_path: Target module path
        intent_id: OpenClaw session correlation (optional)
        source_job_id: Source FoundUpJob ID (optional)

    Returns:
        BuildPlan with defaults (dry_run=True, mode=DRY_RUN, status=DRAFT)
    """
    plan_id = generate_build_plan_id(foundup_id)

    target = BuildTarget(module_path=module_path)

    return BuildPlan(
        build_plan_id=plan_id,
        foundup_id=foundup_id,
        tenant_id=tenant_id,
        intent_id=intent_id,
        source_job_id=source_job_id,
        target=target,
    )


def create_standard_build_steps(module_path: str) -> List[BuildStep]:
    """
    Create the standard 12-step build sequence.

    From FOUNDUP_BUILD_PLAN_CONTRACT.md Section 4.2.
    """
    return [
        BuildStep(
            step_id="step_01",
            step_name="Genesis validation",
            action=BuildStepAction.VALIDATE_GENESIS,
            rollback_point=False,
        ),
        BuildStep(
            step_id="step_02",
            step_name="Manifest validation",
            action=BuildStepAction.VALIDATE_MANIFEST,
            rollback_point=False,
        ),
        BuildStep(
            step_id="step_03",
            step_name="Create spec docs",
            action=BuildStepAction.CREATE_SPEC,
            target_files=[f"{module_path}/docs/SPEC.md"],
            rollback_point=True,
        ),
        BuildStep(
            step_id="step_04",
            step_name="Create tests",
            action=BuildStepAction.CREATE_TEST,
            target_files=[f"{module_path}/tests/"],
            rollback_point=True,
        ),
        BuildStep(
            step_id="step_05",
            step_name="Create module files",
            action=BuildStepAction.CREATE_MODULE,
            target_files=[f"{module_path}/src/"],
            rollback_point=True,
        ),
        BuildStep(
            step_id="step_06",
            step_name="Update manifest",
            action=BuildStepAction.UPDATE_MANIFEST,
            target_files=[f"{module_path}/foundup_manifest.json"],
            rollback_point=True,
        ),
        BuildStep(
            step_id="step_07",
            step_name="Run tests",
            action=BuildStepAction.RUN_TESTS,
            rollback_point=False,
        ),
        BuildStep(
            step_id="step_08",
            step_name="Update ModLog",
            action=BuildStepAction.UPDATE_MODLOG,
            target_files=[f"{module_path}/ModLog.md"],
            rollback_point=True,
        ),
        BuildStep(
            step_id="step_09",
            step_name="Update TestModLog",
            action=BuildStepAction.UPDATE_TESTMODLOG,
            target_files=[f"{module_path}/tests/TestModLog.md"],
            rollback_point=True,
        ),
        BuildStep(
            step_id="step_10",
            step_name="Dry-run build",
            action=BuildStepAction.DRY_RUN_BUILD,
            rollback_point=False,
        ),
        BuildStep(
            step_id="step_11",
            step_name="Submit receipt",
            action=BuildStepAction.SUBMIT_RECEIPT,
            rollback_point=False,
        ),
        BuildStep(
            step_id="step_12",
            step_name="Request approval",
            action=BuildStepAction.REQUEST_APPROVAL,
            rollback_point=False,
        ),
    ]
