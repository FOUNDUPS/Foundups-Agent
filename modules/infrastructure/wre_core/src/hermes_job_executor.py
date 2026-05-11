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

import fnmatch
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, TYPE_CHECKING

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
# Workspace Binding Contract
# ---------------------------------------------------------------------------

# Security-hardcoded blocked paths (never accessible)
BLOCKED_PATHS: FrozenSet[str] = frozenset([
    ".env",
    ".env.*",
    "**/.env",
    "**/.env.*",
    "*.pem",
    "*.key",
    "**/secrets/",
    "**/credentials/",
    ".git/config",
    ".git/credentials",
    "**/__pycache__/",
    "vendor/",
    ".hermes/",
    "node_modules/",
    ".venv/",
    "venv/",
])

# Action-to-allowed-paths mapping
# {action: [path_templates]} where {foundup_id} and {job_id} are placeholders
ACTION_ALLOWED_PATHS: Dict[str, List[str]] = {
    "build_foundup": [
        "modules/foundups/{foundup_id}/",
        ".hermes_evidence/{job_id}/",
    ],
    "extract_foundup": [
        "modules/foundups/{foundup_id}/",
        ".hermes_evidence/{job_id}/",
    ],
    "validate_foundup": [
        "modules/foundups/{foundup_id}/",
        ".hermes_evidence/{job_id}/",
    ],
    "queue_foundup_job": [
        ".hermes_evidence/{job_id}/",
    ],
}

# Default allowed paths when action not in map or foundup_id is None
DEFAULT_ALLOWED_PATHS: List[str] = [
    ".hermes_evidence/{job_id}/",
]


@dataclass
class WorkspaceBinding:
    """
    Workspace context for Hermes delegation sandbox.

    Defines the filesystem boundaries within which Hermes subagents
    may operate. All paths are relative to workspace_root unless
    otherwise specified.

    Attributes:
        workspace_root: Absolute path to FoundUps-Agent repository root
        workspace_hint: Relative path hint for Hermes (e.g., "modules/foundups/gotjunk")
        allowed_paths: Paths Hermes may read/write (relative to workspace_root)
        blocked_paths: Paths Hermes must NOT access (glob patterns)
        evidence_output_path: Absolute path for job evidence output
        retention_on_failure: Retention mode ("preserve", "cleanup", "archive")
    """

    workspace_root: str
    workspace_hint: Optional[str] = None
    allowed_paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)
    evidence_output_path: str = ""
    retention_on_failure: str = "preserve"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for logging/audit."""
        return {
            "workspace_root": self.workspace_root,
            "workspace_hint": self.workspace_hint,
            "allowed_paths": self.allowed_paths,
            "blocked_paths": self.blocked_paths,
            "evidence_output_path": self.evidence_output_path,
            "retention_on_failure": self.retention_on_failure,
        }

    def is_path_allowed(self, path: str) -> bool:
        """
        Check if a path is allowed by this binding.

        Args:
            path: Path to check (relative to workspace_root)

        Returns:
            True if path is within allowed_paths and not in blocked_paths
        """
        from pathlib import PurePosixPath

        # Normalize path to forward slashes for consistent matching
        normalized = os.path.normpath(path).replace("\\", "/")
        path_obj = PurePosixPath(normalized)

        # Check blocked patterns first (deny takes precedence)
        for pattern in self.blocked_paths:
            # Use PurePath.match() which supports ** for recursive matching
            if path_obj.match(pattern):
                return False
            # Also check fnmatch for simple patterns without **
            if "**" not in pattern and fnmatch.fnmatch(normalized, pattern):
                return False
            # Check if path starts with blocked directory
            pattern_clean = pattern.rstrip("/*").replace("**/", "")
            if pattern_clean and (
                normalized.startswith(pattern_clean + "/")
                or normalized == pattern_clean
                or ("/" + pattern_clean + "/") in ("/" + normalized + "/")
            ):
                return False

        # Check allowed paths
        for allowed in self.allowed_paths:
            allowed_clean = allowed.rstrip("/")
            if normalized.startswith(allowed_clean + "/") or normalized == allowed_clean:
                return True

        return False


def get_evidence_output_path(workspace_root: str, job_id: str) -> str:
    """
    Generate evidence output path for a job.

    Args:
        workspace_root: Root directory of workspace
        job_id: Job identifier

    Returns:
        Absolute path to evidence output directory
    """
    return os.path.join(workspace_root, ".hermes_evidence", job_id)


def build_allowed_paths(
    action: str,
    foundup_id: Optional[str],
    job_id: str,
) -> List[str]:
    """
    Build allowed paths list based on action and job context.

    Args:
        action: Requested action (e.g., "build_foundup")
        foundup_id: Target FoundUp ID (may be None)
        job_id: Job identifier

    Returns:
        List of allowed path patterns with placeholders resolved
    """
    # Get template paths for action
    templates = ACTION_ALLOWED_PATHS.get(action, DEFAULT_ALLOWED_PATHS)

    # If no foundup_id, use restricted default
    if not foundup_id:
        templates = DEFAULT_ALLOWED_PATHS

    # Resolve placeholders
    resolved = []
    for template in templates:
        path = template.replace("{job_id}", job_id)
        if foundup_id:
            path = path.replace("{foundup_id}", foundup_id)
        elif "{foundup_id}" in path:
            # Skip paths requiring foundup_id when not available
            continue
        resolved.append(path)

    return resolved


# ---------------------------------------------------------------------------
# Execution Status Codes
# ---------------------------------------------------------------------------


class HermesExecutionStatus(str, Enum):
    """Status codes for Hermes delegation execution."""

    # Success (Phase 2+)
    EXECUTED = "EXECUTED"

    # Simulation (dry_run=True or feature flag disabled)
    SIMULATED = "SIMULATED"

    # Controlled Harness (HXA14+) - explicit test-only delegation
    CONTROLLED_HARNESS_EXECUTED = "CONTROLLED_HARNESS_EXECUTED"

    # HXA16 Adapter Boundary - real delegate interface proven but not called
    DELEGATE_ADAPTER_BOUNDARY_PROVEN = "DELEGATE_ADAPTER_BOUNDARY_PROVEN"

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
        workspace_binding: Workspace context and path constraints
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

    # Workspace binding (Phase 1 contract addition)
    workspace_binding: Optional[WorkspaceBinding] = None

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
            "workspace_binding": self.workspace_binding.to_dict() if self.workspace_binding else None,
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

        Checkpoint Protocol Fields (Hermes swarm format):
        checkpoint_state: DONE|BLOCKED|NEEDS_INPUT|HANDOFF|SIMULATED
        checkpoint_result: Summary of work completed (if any)
        checkpoint_blocker: Description of blocker (if BLOCKED)
        checkpoint_next_action: Suggested next step
        files_changed: List of files modified during execution
        commands_run: List of commands executed

        Evidence Collection Fields:
        evidence_path: Path to evidence directory (.hermes_evidence/{job_id}/)

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

    # Checkpoint Protocol Fields (Hermes swarm format)
    checkpoint_state: str = "SIMULATED"
    checkpoint_result: Optional[str] = None
    checkpoint_blocker: Optional[str] = None
    checkpoint_next_action: Optional[str] = None
    files_changed: List[str] = field(default_factory=list)
    commands_run: List[str] = field(default_factory=list)

    # Evidence Collection Fields
    evidence_path: Optional[str] = None

    # WSP 97 Truth Fields - NEVER set to True in this adapter
    real_execution_performed: bool = False
    verification_complete: bool = False
    cabr_ready: bool = False
    payout_ready: bool = False

    # HXA14 Controlled Harness Truth Fields
    controlled_delegate_invoked: bool = False
    live_external_delegate_called: bool = False
    repo_created: bool = False
    production_source_modified: bool = False
    external_federation_ready: bool = False
    external_federation_initiated: bool = False
    production_ready: bool = False
    production_readiness_claimed: bool = False

    # HXA16 Real Delegate Adapter Truth Fields
    real_delegate_adapter_invoked: bool = False

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
            # Checkpoint Protocol Fields
            "checkpoint_state": self.checkpoint_state,
            "checkpoint_result": self.checkpoint_result,
            "checkpoint_blocker": self.checkpoint_blocker,
            "checkpoint_next_action": self.checkpoint_next_action,
            "files_changed": self.files_changed,
            "commands_run": self.commands_run,
            # Evidence Collection Fields
            "evidence_path": self.evidence_path,
            # WSP 97 Truth Fields
            "real_execution_performed": self.real_execution_performed,
            "verification_complete": self.verification_complete,
            "cabr_ready": self.cabr_ready,
            "payout_ready": self.payout_ready,
            # HXA14 Controlled Harness Truth Fields
            "controlled_delegate_invoked": self.controlled_delegate_invoked,
            "live_external_delegate_called": self.live_external_delegate_called,
            "repo_created": self.repo_created,
            "production_source_modified": self.production_source_modified,
            "external_federation_ready": self.external_federation_ready,
            "external_federation_initiated": self.external_federation_initiated,
            "production_ready": self.production_ready,
            "production_readiness_claimed": self.production_readiness_claimed,
            # HXA16 Real Delegate Adapter Truth Fields
            "real_delegate_adapter_invoked": self.real_delegate_adapter_invoked,
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
        workspace_root: Optional[str] = None,
        controlled_harness: bool = False,
        real_delegate_adapter: bool = False,
    ):
        """
        Initialize executor.

        Args:
            dry_run: If True (default), never call real delegate_task
            max_iterations: Default iteration limit for Hermes
            default_toolsets: Default toolsets (empty by default for safety)
            workspace_root: Root directory for workspace binding (auto-detected if None)
            controlled_harness: If True, use controlled delegate instead of real/blocked.
                               This is an explicit test-only mode (HXA14).
                               MUST be explicitly set; default is False.
            real_delegate_adapter: If True (with controlled_harness), prove adapter boundary
                                   to real Hermes delegate interface without calling it.
                                   This is an explicit test-only mode (HXA16).
                                   MUST be explicitly set; default is False.
        """
        self.dry_run = dry_run
        self.max_iterations = max_iterations
        self.default_toolsets = default_toolsets or []
        self.workspace_root = workspace_root or self._detect_workspace_root()
        self.controlled_harness = controlled_harness
        self.real_delegate_adapter = real_delegate_adapter
        self._delegate_task_fn = None
        self._controlled_delegate_fn = None
        self._import_attempted = False
        self._import_error: Optional[str] = None

    def _detect_workspace_root(self) -> str:
        """
        Detect workspace root from environment or current directory.

        Priority:
          1. FOUNDUPS_WORKSPACE_ROOT env var
          2. Current working directory

        Returns:
            Absolute path to workspace root
        """
        env_root = os.environ.get("FOUNDUPS_WORKSPACE_ROOT")
        if env_root:
            return os.path.abspath(env_root)
        return os.getcwd()

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

    def _execute_controlled_delegate(
        self,
        job: "FoundUpJob",
        request: HermesDelegationRequest,
    ) -> Dict[str, Any]:
        """
        Execute controlled delegate for test harness.

        This is NOT a real Hermes delegate_task call. It simulates delegation
        behavior for testing purposes while maintaining all safety boundaries.

        HXA14 Controlled Harness Semantics:
          - Explicitly invoked only when controlled_harness=True
          - Does NOT call live external delegate_task
          - Does NOT create GitHub repositories
          - Does NOT modify production FoundUp source
          - DOES write evidence artifacts to temp workspace
          - Returns truthful controlled_delegate_invoked=True

        Args:
            job: FoundUpJob being processed
            request: HermesDelegationRequest built from job

        Returns:
            Simulated delegate response with controlled execution markers
        """
        logger.info(
            "[HERMES-EXEC] Executing controlled delegate for job %s (harness mode)",
            job.job_id,
        )

        foundup_id = job.foundup_id or "unknown"

        # Simulate delegate execution - deterministic, no external calls
        simulated_files_changed = [
            f".hermes_evidence/{job.job_id}/controlled_delegate_output.json",
            f".hermes_evidence/{job.job_id}/{foundup_id}_poc/README.md",
            f".hermes_evidence/{job.job_id}/{foundup_id}_poc/manifest.preview.json",
        ]

        return {
            "status": "CONTROLLED_HARNESS_COMPLETE",
            "message": (
                f"Controlled delegate executed for {foundup_id}. "
                "This is a test harness execution, not live delegation."
            ),
            "files_changed": simulated_files_changed,
            "commands_run": [],
            "iterations": 1,
            "controlled_harness": True,
            "live_delegate_called": False,
            "repo_created": False,
            "production_source_modified": False,
            "job_id": job.job_id,
            "foundup_id": foundup_id,
            "executed_at": _utc_now().isoformat(),
        }

    def _execute_real_delegate_adapter(
        self,
        job: "FoundUpJob",
        request: HermesDelegationRequest,
    ) -> Dict[str, Any]:
        """
        Execute real delegate adapter boundary proof.

        HXA16 Real Delegate Adapter Semantics:
          - Proves the adapter boundary to real Hermes delegate_task exists
          - Documents interface requirements (parent_agent, toolsets, etc)
          - Does NOT call live external delegate_task
          - Does NOT instantiate full Hermes runtime
          - Does NOT create GitHub repositories
          - Does NOT modify production FoundUp source
          - DOES write evidence artifacts documenting the interface
          - Returns truthful real_delegate_adapter_invoked=True

        The real delegate_task in vendor/hermes-agent/tools/delegate_tool.py
        requires full Hermes runtime infrastructure which cannot be safely
        instantiated without production risk. This method proves the boundary
        exists and documents requirements without making the call.

        Args:
            job: FoundUpJob being processed
            request: HermesDelegationRequest built from job

        Returns:
            Adapter boundary proof response with interface documentation
        """
        from pathlib import Path

        logger.info(
            "[HERMES-EXEC] Executing real delegate adapter boundary proof for job %s",
            job.job_id,
        )

        foundup_id = job.foundup_id or "unknown"
        delegate_tool_path = Path("vendor/hermes-agent/tools/delegate_tool.py")

        # Document interface requirements
        interface_requirements = {
            "parent_agent": "AIAgent instance with full agent context",
            "toolsets": "Hermes toolset configurations (file ops, web, etc)",
            "model_config": "LLM model configurations (Claude, etc)",
            "credentials": "API keys and authentication tokens",
            "terminal_sessions": "Isolated terminal session contexts",
            "child_agent_spawning": "Ability to spawn child AIAgent instances",
        }

        # Document why external call is blocked
        blocked_reason = (
            "Real delegate_task requires full Hermes runtime infrastructure. "
            "Instantiating AIAgent would require real API credentials (production exposure), "
            "network access to LLM providers (external calls), and file system access "
            "beyond evidence workspace (production risk). Cannot be safely invoked "
            "without violating WSP 97 truth boundaries."
        )

        # Evidence files to generate
        evidence_files = [
            f".hermes_evidence/{job.job_id}/adapter_boundary_proof.json",
            f".hermes_evidence/{job.job_id}/delegate_interface_requirements.json",
            f".hermes_evidence/{job.job_id}/metadata.json",
            f".hermes_evidence/{job.job_id}/checkpoint.json",
        ]

        return {
            "status": "ADAPTER_BOUNDARY_PROVEN",
            "verdict": "DELEGATE_ADAPTER_BOUNDARY_PROVEN_EXTERNAL_CALL_NOT_ENABLED",
            "message": (
                f"Real delegate adapter boundary proven for {foundup_id}. "
                "Interface documented but external delegate NOT called."
            ),
            "delegate_tool_path": str(delegate_tool_path),
            "delegate_tool_exists": delegate_tool_path.exists(),
            "interface_requirements": interface_requirements,
            "blocked_reason": blocked_reason,
            "external_call_enabled": False,
            "files_changed": evidence_files,
            "commands_run": [],
            "iterations": 0,
            "real_delegate_adapter": True,
            "controlled_harness": True,
            "live_delegate_called": False,
            "repo_created": False,
            "production_source_modified": False,
            "external_federation_initiated": False,
            "production_readiness_claimed": False,
            "job_id": job.job_id,
            "foundup_id": foundup_id,
            "executed_at": _utc_now().isoformat(),
        }

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

        # Build workspace binding
        workspace_binding = self._build_workspace_binding(job)

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
            workspace_binding=workspace_binding,
        )

    def _build_workspace_binding(self, job: "FoundUpJob") -> WorkspaceBinding:
        """
        Build WorkspaceBinding from job context.

        Derives workspace hint, allowed/blocked paths, and evidence output
        path from job identity fields.

        Args:
            job: Source FoundUpJob

        Returns:
            WorkspaceBinding with path constraints
        """
        # Derive workspace hint from foundup_id
        workspace_hint = None
        if job.foundup_id:
            workspace_hint = f"modules/foundups/{job.foundup_id}"

        # Build allowed paths based on action and foundup_id
        allowed_paths = build_allowed_paths(
            action=job.requested_action,
            foundup_id=job.foundup_id,
            job_id=job.job_id,
        )

        # Evidence output path
        evidence_output_path = get_evidence_output_path(
            workspace_root=self.workspace_root,
            job_id=job.job_id,
        )

        return WorkspaceBinding(
            workspace_root=self.workspace_root,
            workspace_hint=workspace_hint,
            allowed_paths=allowed_paths,
            blocked_paths=list(BLOCKED_PATHS),
            evidence_output_path=evidence_output_path,
            retention_on_failure="preserve",
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
          3. If controlled_harness: execute controlled delegate (HXA14)
          4. Check feature flag
          5. If disabled or dry_run: return SIMULATED
          6. If enabled and not dry_run: return BLOCKED (Phase 2)

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

        # Step 3: HXA14/HXA16 Controlled Harness paths
        if self.controlled_harness:
            # Step 3a: HXA16 Real Delegate Adapter - prove boundary without calling
            if self.real_delegate_adapter:
                logger.info(
                    "[HERMES-EXEC] Real delegate adapter mode, proving boundary for job %s",
                    job.job_id,
                )
                delegate_response = self._execute_real_delegate_adapter(job, request)

                result = HermesDelegationResult(
                    status=HermesExecutionStatus.DELEGATE_ADAPTER_BOUNDARY_PROVEN,
                    status_reason=(
                        f"Real delegate adapter boundary proven for job {job.job_id}. "
                        "Interface documented but external delegate NOT called."
                    ),
                    request=request,
                    delegate_response=delegate_response,
                    duration_seconds=time.monotonic() - start_time,
                    checkpoint_state="ADAPTER_BOUNDARY_PROVEN",
                    checkpoint_result=f"Adapter boundary proven for {job.foundup_id or 'unknown'}",
                    files_changed=delegate_response.get("files_changed", []),
                    # WSP 97 Truth Fields
                    real_execution_performed=False,
                    verification_complete=False,
                    cabr_ready=False,
                    payout_ready=False,
                    # HXA14/HXA16 Controlled Harness Truth Fields
                    controlled_delegate_invoked=True,
                    live_external_delegate_called=False,
                    repo_created=False,
                    production_source_modified=False,
                    external_federation_ready=False,
                    external_federation_initiated=False,
                    production_ready=False,
                    production_readiness_claimed=False,
                    # HXA16 Adapter Truth Fields
                    real_delegate_adapter_invoked=True,
                )
                result.evidence_path = self._write_evidence(job, request, result)
                return result

            # Step 3b: HXA14 Controlled Harness - explicit test-only path
            logger.info(
                "[HERMES-EXEC] Controlled harness enabled, executing controlled delegate for job %s",
                job.job_id,
            )
            # Execute controlled delegate (no live external calls)
            delegate_response = self._execute_controlled_delegate(job, request)

            result = HermesDelegationResult(
                status=HermesExecutionStatus.CONTROLLED_HARNESS_EXECUTED,
                status_reason=(
                    f"Controlled harness executed for job {job.job_id}. "
                    "This is a test harness execution - no live external delegate called."
                ),
                request=request,
                delegate_response=delegate_response,
                duration_seconds=time.monotonic() - start_time,
                checkpoint_state="CONTROLLED_HARNESS_COMPLETE",
                checkpoint_result=f"Controlled delegate completed for {job.foundup_id or 'unknown'}",
                files_changed=delegate_response.get("files_changed", []),
                # WSP 97 Truth Fields
                real_execution_performed=False,  # No REAL execution
                verification_complete=False,
                cabr_ready=False,
                payout_ready=False,
                # HXA14 Controlled Harness Truth Fields
                controlled_delegate_invoked=True,
                live_external_delegate_called=False,
                repo_created=False,
                production_source_modified=False,
                external_federation_ready=False,
                external_federation_initiated=False,
                production_ready=False,
                production_readiness_claimed=False,
                # HXA16 - not using adapter
                real_delegate_adapter_invoked=False,
            )
            result.evidence_path = self._write_evidence(job, request, result)
            return result

        # Step 4: Check feature flag
        if not is_hermes_delegation_enabled():
            logger.info(
                "[HERMES-EXEC] Feature disabled, simulating job %s",
                job.job_id,
            )
            result = HermesDelegationResult(
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
            result.evidence_path = self._write_evidence(job, request, result)
            return result

        # Step 4: Feature enabled - check dry_run
        if self.dry_run:
            logger.info(
                "[HERMES-EXEC] dry_run=True, simulating job %s",
                job.job_id,
            )
            result = HermesDelegationResult(
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
            result.evidence_path = self._write_evidence(job, request, result)
            return result

        # Step 5: Check import availability
        if not self._lazy_import_delegate_task():
            result = HermesDelegationResult(
                status=HermesExecutionStatus.BLOCKED_IMPORT_UNAVAILABLE,
                status_reason=(
                    f"Cannot import Hermes delegate_task: {self._import_error}. "
                    "Ensure vendor/hermes-agent is available."
                ),
                request=request,
                duration_seconds=time.monotonic() - start_time,
                real_execution_performed=False,
            )
            result.evidence_path = self._write_evidence(job, request, result)
            return result

        # Step 6: Real execution blocked in Phase 1
        logger.warning(
            "[HERMES-EXEC] Real delegation NOT IMPLEMENTED, blocking job %s",
            job.job_id,
        )
        result = HermesDelegationResult(
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
        result.evidence_path = self._write_evidence(job, request, result)
        return result

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

    def _generate_poc_artifact_plan(
        self,
        job: "FoundUpJob",
        request: HermesDelegationRequest,
    ) -> Dict[str, Any]:
        """
        Generate deterministic PoC artifact plan for build_foundup action.

        This is a dry-run plan showing what artifacts WOULD be generated
        if live delegation was enabled. No actual files are created
        in production source - only the plan is written to evidence.

        WSP 97: This is observability, not execution proof.
          - poc_generation=True indicates plan was generated
          - real_execution_performed=False (no actual file creation)
          - repo_created=False (no GitHub operations)
          - live_delegate_called=False (no delegate_task invocation)

        Args:
            job: Source FoundUpJob
            request: HermesDelegationRequest

        Returns:
            Dict containing the PoC artifact plan
        """
        foundup_id = job.foundup_id or "unknown"

        # Deterministic plan based on action
        if job.requested_action == "build_foundup":
            planned_artifacts = [
                f"modules/foundups/{foundup_id}/src/__init__.py",
                f"modules/foundups/{foundup_id}/src/{foundup_id}_core.py",
                f"modules/foundups/{foundup_id}/src/{foundup_id}_api.py",
                f"modules/foundups/{foundup_id}/tests/test_{foundup_id}_core.py",
            ]
            plan_description = f"Build PoC scaffold for FoundUp '{foundup_id}'"
        elif job.requested_action == "extract_foundup":
            planned_artifacts = [
                f"external-repos/{foundup_id}/README.md",
                f"external-repos/{foundup_id}/requirements.txt",
                f"external-repos/{foundup_id}/src/",
            ]
            plan_description = f"Extract FoundUp '{foundup_id}' to external repo"
        else:
            planned_artifacts = []
            plan_description = f"Execute action '{job.requested_action}'"

        return {
            "poc_generation": True,
            "foundup_id": foundup_id,
            "requested_action": job.requested_action,
            "plan_description": plan_description,
            "planned_artifacts": planned_artifacts,
            "planned_artifact_count": len(planned_artifacts),
            # WSP 97 truth fields
            "real_execution_performed": False,
            "repo_created": False,
            "live_delegate_called": False,
            "artifacts_written_to_source": False,
            # Execution mode
            "dry_run": request.dry_run,
            "hermes_delegate_enabled": is_hermes_delegation_enabled(),
            # Generation metadata
            "generated_at": _utc_now().isoformat(),
            "generator_version": "0.1.0",
        }

    def _generate_controlled_scaffold(
        self,
        job: "FoundUpJob",
        request: HermesDelegationRequest,
        evidence_dir: str,
    ) -> Dict[str, Any]:
        """
        Generate controlled scaffold artifacts in temp/evidence workspace.

        HXA10: Moves from plan-only (HXA9) to actual scaffold file generation,
        but ONLY in the evidence workspace - never production source.

        Generated artifacts are clearly marked as dry-run/preview:
          - {foundup_id}_poc/README.md
          - {foundup_id}_poc/manifest.preview.json
          - {foundup_id}_poc/interface.preview.md
          - {foundup_id}_poc/implementation_plan.md

        WSP 97 Truth Boundaries:
          - controlled_scaffold_generated=True (files written to temp)
          - real_execution_performed=False (not production)
          - repo_created=False (no GitHub)
          - live_delegate_called=False (no delegate_task)
          - production_source_modified=False

        Args:
            job: Source FoundUpJob
            request: HermesDelegationRequest
            evidence_dir: Path to evidence directory

        Returns:
            Dict containing scaffold generation metadata
        """
        foundup_id = job.foundup_id or "unknown"
        scaffold_dir = os.path.join(evidence_dir, f"{foundup_id}_poc")
        os.makedirs(scaffold_dir, exist_ok=True)

        generated_files = []
        generation_timestamp = _utc_now().isoformat()

        # Generate README.md (dry-run scaffold)
        readme_path = os.path.join(scaffold_dir, "README.md")
        readme_content = f"""# {foundup_id.upper()} PoC Scaffold

**STATUS**: DRY-RUN PREVIEW - NOT PRODUCTION CODE

This scaffold was generated by HXA10 controlled scaffold generation.
It exists ONLY in the evidence workspace for validation purposes.

## Generation Metadata

- **FoundUp ID**: {foundup_id}
- **Job ID**: {job.job_id}
- **Tenant ID**: {job.tenant_id}
- **Generated At**: {generation_timestamp}
- **Dry Run**: True
- **Production Ready**: False

## WSP 97 Truth Statement

This is a controlled dry-run scaffold. No production code was generated.
No external repository was created. No live Hermes delegate was called.

## Next Steps (Phase 2+)

1. Human review of scaffold structure
2. Approval gate for controlled production generation
3. CABR validation (not yet implemented)
"""
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        generated_files.append(f"{foundup_id}_poc/README.md")

        # Generate manifest.preview.json
        manifest_path = os.path.join(scaffold_dir, "manifest.preview.json")
        manifest_content = {
            "_preview_warning": "DRY-RUN SCAFFOLD - NOT PRODUCTION MANIFEST",
            "foundup_id": foundup_id,
            "name": foundup_id.replace("_", " ").title(),
            "version": "0.0.0-preview",
            "lifecycle_stage": "scaffold",
            "launch_readiness": "dry_run_only",
            "_wsp97_implementation_state": "SCAFFOLD_NOT_IMPLEMENTED",
            "generated_by": "HXA10_CONTROLLED_SCAFFOLD_GENERATION",
            "generated_at": generation_timestamp,
            "job_id": job.job_id,
            "dry_run": True,
            "production_ready": False,
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_content, f, indent=2)
        generated_files.append(f"{foundup_id}_poc/manifest.preview.json")

        # Generate interface.preview.md
        interface_path = os.path.join(scaffold_dir, "interface.preview.md")
        interface_content = f"""# {foundup_id.upper()} Interface Preview

**STATUS**: DRY-RUN SCAFFOLD - NOT PRODUCTION INTERFACE

## Planned Public API

```python
# This is a PREVIEW - not implemented
class {foundup_id.title().replace('_', '')}Core:
    def __init__(self, config: dict) -> None:
        \"\"\"Initialize {foundup_id} core component.\"\"\"
        pass

    def execute(self, input_data: dict) -> dict:
        \"\"\"Execute primary {foundup_id} operation.\"\"\"
        pass
```

## WSP 97 Note

This interface preview is for planning purposes only.
No implementation exists. No production code was generated.
"""
        with open(interface_path, "w", encoding="utf-8") as f:
            f.write(interface_content)
        generated_files.append(f"{foundup_id}_poc/interface.preview.md")

        # Generate implementation_plan.md
        plan_path = os.path.join(scaffold_dir, "implementation_plan.md")
        plan_content = f"""# {foundup_id.upper()} Implementation Plan

**STATUS**: DRY-RUN SCAFFOLD - PLANNING DOCUMENT ONLY

## Phase 1: Scaffold (CURRENT - HXA10)

- [x] Generate controlled scaffold in evidence workspace
- [x] Create preview manifest
- [x] Create interface preview
- [ ] Human review and approval

## Phase 2: Controlled Generation (Future)

- [ ] Enable HERMES_DELEGATE_ENABLED=1 in test harness
- [ ] Generate src/ stub files
- [ ] Validate generated code passes linter
- [ ] No GitHub repo creation yet

## Phase 3: Production (Future)

- [ ] Human approval gate
- [ ] CABR validation
- [ ] External repo creation (if applicable)
- [ ] Production deployment

## WSP 97 Truth

- This is a planning document only
- No implementation code exists
- No production readiness claimed
- Generated: {generation_timestamp}
"""
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(plan_content)
        generated_files.append(f"{foundup_id}_poc/implementation_plan.md")

        logger.info(
            "[HERMES-EXEC] Controlled scaffold generated at %s (%d files)",
            scaffold_dir,
            len(generated_files),
        )

        return {
            "controlled_scaffold_generated": True,
            "scaffold_dir": scaffold_dir,
            "generated_files": generated_files,
            "generated_file_count": len(generated_files),
            "foundup_id": foundup_id,
            # WSP 97 truth fields
            "real_execution_performed": False,
            "repo_created": False,
            "live_delegate_called": False,
            "production_source_modified": False,
            "dry_run": request.dry_run,
            # Generation metadata
            "generated_at": generation_timestamp,
            "generator_version": "0.2.0",
            "generator_slice": "HXA10_CONTROLLED_SCAFFOLD_GENERATION",
        }

    def _write_adapter_boundary_evidence(
        self,
        job: "FoundUpJob",
        request: HermesDelegationRequest,
        result: HermesDelegationResult,
        evidence_dir: str,
    ) -> None:
        """
        Write HXA16 adapter boundary proof evidence files.

        Creates:
          - adapter_boundary_proof.json: Full proof with verdict and rationale
          - delegate_interface_requirements.json: Interface requirements doc

        Args:
            job: Source FoundUpJob
            request: HermesDelegationRequest that was built
            result: HermesDelegationResult with execution outcome
            evidence_dir: Path to evidence directory
        """
        from pathlib import Path

        delegate_tool_path = Path("vendor/hermes-agent/tools/delegate_tool.py")
        foundup_id = job.foundup_id or "unknown"

        # Interface requirements documentation
        interface_requirements = {
            "parent_agent": "AIAgent instance with full agent context",
            "toolsets": "Hermes toolset configurations (file ops, web, etc)",
            "model_config": "LLM model configurations (Claude, etc)",
            "credentials": "API keys and authentication tokens",
            "terminal_sessions": "Isolated terminal session contexts",
            "child_agent_spawning": "Ability to spawn child AIAgent instances",
            "external_call_enabled": False,
            "external_call_blocked_reason": (
                "Cannot safely instantiate Hermes runtime without production risk"
            ),
        }

        # Write delegate_interface_requirements.json
        interface_path = os.path.join(evidence_dir, "delegate_interface_requirements.json")
        with open(interface_path, "w", encoding="utf-8") as f:
            json.dump(interface_requirements, f, indent=2, default=str)

        # Adapter boundary proof
        adapter_proof = {
            "foundup_id": foundup_id,
            "job_id": job.job_id,
            "verdict": "DELEGATE_ADAPTER_BOUNDARY_PROVEN_EXTERNAL_CALL_NOT_ENABLED",
            "real_delegate_adapter_invoked": True,
            "live_external_delegate_called": False,
            "delegate_tool_path": str(delegate_tool_path),
            "delegate_tool_exists": delegate_tool_path.exists(),
            "interface_requirements": interface_requirements,
            "blocked_reason": (
                "Real delegate_task requires full Hermes runtime infrastructure. "
                "Instantiating AIAgent would require real API credentials (production exposure), "
                "network access to LLM providers (external calls), and file system access "
                "beyond evidence workspace (production risk). Cannot be safely invoked "
                "without violating WSP 97 truth boundaries."
            ),
            "wsp97_truth_fields": {
                "real_execution_performed": result.real_execution_performed,
                "repo_created": result.repo_created,
                "production_source_modified": result.production_source_modified,
                "external_federation_initiated": result.external_federation_initiated,
                "production_readiness_claimed": result.production_readiness_claimed,
            },
            "proven_at": result.completed_at.isoformat(),
        }

        # Write adapter_boundary_proof.json
        proof_path = os.path.join(evidence_dir, "adapter_boundary_proof.json")
        with open(proof_path, "w", encoding="utf-8") as f:
            json.dump(adapter_proof, f, indent=2, default=str)

        logger.info(
            "[HERMES-EXEC] HXA16 adapter boundary proof written to %s",
            proof_path,
        )

    def _write_evidence(
        self,
        job: "FoundUpJob",
        request: HermesDelegationRequest,
        result: HermesDelegationResult,
    ) -> Optional[str]:
        """
        Write evidence files for job execution.

        Creates .hermes_evidence/{job_id}/ directory with:
          - metadata.json: Job identity, workspace binding, timing
          - checkpoint.json: Checkpoint state and execution details
          - poc_artifact_bundle.json: PoC artifact plan (for build_foundup)

        Evidence files are observability artifacts only (WSP 97).
        They prove the job was processed, not that real work occurred.

        Args:
            job: Source FoundUpJob
            request: HermesDelegationRequest that was built
            result: HermesDelegationResult with execution outcome

        Returns:
            Absolute path to evidence directory, or None on error
        """
        try:
            # Get evidence output path from workspace binding
            evidence_dir = request.workspace_binding.evidence_output_path

            # Create evidence directory
            os.makedirs(evidence_dir, exist_ok=True)

            # Build metadata.json contents
            metadata = {
                "job_id": job.job_id,
                "foundup_id": job.foundup_id,
                "tenant_id": job.tenant_id,
                "requested_action": job.requested_action,
                "intent_id": job.intent_id,
                "workspace_binding": request.workspace_binding.to_dict(),
                "started_at": request.created_at.isoformat(),
                "completed_at": result.completed_at.isoformat(),
                "dry_run": request.dry_run,
                "execution_status": result.status.value,
            }

            # Write metadata.json
            metadata_path = os.path.join(evidence_dir, "metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, default=str)

            # Build checkpoint.json contents
            checkpoint = {
                "state": result.checkpoint_state,
                "result": result.checkpoint_result,
                "blocker": result.checkpoint_blocker,
                "next_action": result.checkpoint_next_action,
                "files_changed": result.files_changed,
                "commands_run": result.commands_run,
                "exit_reason": result.status_reason,
            }

            # Write checkpoint.json
            checkpoint_path = os.path.join(evidence_dir, "checkpoint.json")
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(checkpoint, f, indent=2, default=str)

            # Generate and write poc_artifact_bundle.json for build_foundup actions
            if job.requested_action in ("build_foundup", "extract_foundup"):
                poc_plan = self._generate_poc_artifact_plan(job, request)
                poc_bundle_path = os.path.join(evidence_dir, "poc_artifact_bundle.json")
                with open(poc_bundle_path, "w", encoding="utf-8") as f:
                    json.dump(poc_plan, f, indent=2, default=str)
                logger.info(
                    "[HERMES-EXEC] PoC artifact bundle written to %s",
                    poc_bundle_path,
                )

                # HXA10: Generate controlled scaffold files in evidence workspace
                scaffold_result = self._generate_controlled_scaffold(
                    job, request, evidence_dir
                )
                scaffold_meta_path = os.path.join(
                    evidence_dir, "controlled_scaffold.json"
                )
                with open(scaffold_meta_path, "w", encoding="utf-8") as f:
                    json.dump(scaffold_result, f, indent=2, default=str)
                logger.info(
                    "[HERMES-EXEC] Controlled scaffold metadata written to %s",
                    scaffold_meta_path,
                )

            # HXA16: Generate adapter boundary proof files when real_delegate_adapter mode
            if result.real_delegate_adapter_invoked:
                self._write_adapter_boundary_evidence(
                    job, request, result, evidence_dir
                )

            logger.info(
                "[HERMES-EXEC] Evidence written to %s",
                evidence_dir,
            )
            return evidence_dir

        except Exception as exc:
            # Evidence failure must not fail job (WSP 97 observability)
            logger.warning(
                "[HERMES-EXEC] Failed to write evidence for job %s: %s",
                job.job_id,
                exc,
            )
            return None


# ---------------------------------------------------------------------------
# Module-Level Convenience Functions
# ---------------------------------------------------------------------------

_executor_singleton: Optional[HermesJobExecutor] = None


def get_executor(
    dry_run: bool = True,
    max_iterations: int = 50,
    workspace_root: Optional[str] = None,
) -> HermesJobExecutor:
    """Get or create singleton HermesJobExecutor."""
    global _executor_singleton
    if _executor_singleton is None:
        _executor_singleton = HermesJobExecutor(
            dry_run=dry_run,
            max_iterations=max_iterations,
            workspace_root=workspace_root,
        )
    return _executor_singleton


def execute_foundup_job(job: "FoundUpJob") -> HermesDelegationResult:
    """
    Convenience function to execute FoundUpJob via Hermes.

    Uses default singleton executor with dry_run=True.
    """
    return get_executor().execute(job)
