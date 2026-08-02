#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FoundUp Job Contract — Canonical Orchestration Contract

Shared job contract between OpenClaw (orchestration) and Hermes (execution).
Defines job identity, lifecycle states, execution metadata, and audit fields.

Architecture:
  OpenClaw -> Job (QUEUED) -> Hermes -> Job (RUNNING) -> FAM/Build -> Job (SUCCEEDED|FAILED)

WSP Compliance:
  WSP 11  : Interface contract (explicit, typed)
  WSP 50  : Pre-Action Verification (preflight fields)
  WSP 77  : Agent Coordination (worker identity)
  WSP 91  : Observability (timestamps, audit trail)
  WSP 97  : System Execution Prompting (truth fields, evidence_refs)

NAVIGATION:
  -> Used by: openclaw_dae.py, hermes_adapter.py, fam_adapter.py
  -> Related: modules/foundups/agent_market/src/models.py (Task/Proof/Verification)
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("foundup_job_contract")


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Canonical Requested Actions (Single Source of Truth)
# ---------------------------------------------------------------------------

# Canonical action values for FoundUpJob.requested_action
# All workers (W1/W4/W5/W6) MUST use these exact strings.
# Short forms (build, extract, validate, queue) are NOT supported.
CANONICAL_ACTIONS: frozenset[str] = frozenset({
    "create_foundup",     # NEW: author a NEW monorepo FoundUp scaffold from a
                          # validated genesis envelope. Distinct from
                          # build_foundup/extract_foundup (which operate on an
                          # EXISTING module). See
                          # docs/audits/architecture/FOUNDUP_SCAFFOLD_CONTRACT_PHASE1.md.
    "build_foundup",      # W4: Hermes builds FoundUp from spec
    "extract_foundup",    # W4: Hermes extracts FoundUp to external repo
    "validate_foundup",   # W4: Hermes validates FoundUp manifest/gates
    "queue_foundup_job",  # W5: WRE queues job for later execution
})

# Actions that operate on an EXISTING module (extraction/build). create_foundup
# MUST NOT be routed to any of these (FOUNDUP_SCAFFOLD_CONTRACT_PHASE1 Section 3,
# no-alias rule). A future executor branches on the action string BEFORE dispatch.
EXISTING_MODULE_ACTIONS: frozenset[str] = frozenset({
    "build_foundup",
    "extract_foundup",
})


def is_supported_action(action: str) -> bool:
    """
    Check if action is a canonical supported action.

    Args:
        action: The requested_action string to validate

    Returns:
        True if action is in CANONICAL_ACTIONS, False otherwise

    Usage by workers:
        from foundup_job_contract import is_supported_action, CANONICAL_ACTIONS
        if not is_supported_action(job.requested_action):
            job.fail(FAIL_UNSUPPORTED_ACTION, f"Unknown action: {job.requested_action}")
    """
    return action in CANONICAL_ACTIONS


# ---------------------------------------------------------------------------
# Lifecycle States
# ---------------------------------------------------------------------------


class JobStatus(str, Enum):
    """
    Job lifecycle states.

    State machine:
      QUEUED → RUNNING → SUCCEEDED
                 │
                 ├─→ BLOCKED → RUNNING (resume)
                 │      └───→ FAILED (timeout)
                 │
                 └─→ FAILED (error)

    Terminal states: SUCCEEDED, FAILED
    """

    QUEUED = "queued"        # Job created, waiting for worker
    RUNNING = "running"      # Worker executing
    BLOCKED = "blocked"      # External dependency, awaiting resolution
    FAILED = "failed"        # Terminal: error or timeout
    SUCCEEDED = "succeeded"  # Terminal: completed successfully


# Valid state transitions (from_state -> set of to_states)
_VALID_TRANSITIONS: Dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.QUEUED: frozenset({JobStatus.RUNNING, JobStatus.FAILED}),
    JobStatus.RUNNING: frozenset({JobStatus.BLOCKED, JobStatus.FAILED, JobStatus.SUCCEEDED}),
    JobStatus.BLOCKED: frozenset({JobStatus.RUNNING, JobStatus.FAILED}),
    JobStatus.FAILED: frozenset(),     # Terminal
    JobStatus.SUCCEEDED: frozenset(),  # Terminal
}


def is_valid_transition(from_status: JobStatus, to_status: JobStatus) -> bool:
    """Check if state transition is allowed."""
    return to_status in _VALID_TRANSITIONS.get(from_status, frozenset())


def _parse_reason_code(value: str) -> StatusReasonCode:
    """Parse reason code string, falling back to UNKNOWN if invalid."""
    try:
        return StatusReasonCode(value)
    except ValueError:
        return StatusReasonCode.UNKNOWN


def is_terminal_status(status: JobStatus) -> bool:
    """Check if status is terminal (no further transitions)."""
    return status in (JobStatus.FAILED, JobStatus.SUCCEEDED)


# ---------------------------------------------------------------------------
# Status Reason Codes (Machine-Readable)
# ---------------------------------------------------------------------------


class StatusReasonCode(str, Enum):
    """
    Machine-readable status reason codes.

    Organized by category:
      OK_*      : Success reasons
      BLOCKED_* : Blocking reasons
      FAIL_*    : Failure reasons
    """

    # Success
    OK_COMPLETED = "OK_COMPLETED"
    OK_DRY_RUN_PASSED = "OK_DRY_RUN_PASSED"
    OK_VALIDATION_PASSED = "OK_VALIDATION_PASSED"

    # Blocked
    BLOCKED_DEPENDENCY_MISSING = "BLOCKED_DEPENDENCY_MISSING"
    BLOCKED_AWAITING_APPROVAL = "BLOCKED_AWAITING_APPROVAL"
    BLOCKED_RATE_LIMITED = "BLOCKED_RATE_LIMITED"
    BLOCKED_EXTERNAL_SERVICE = "BLOCKED_EXTERNAL_SERVICE"
    BLOCKED_COMPUTE_EXHAUSTED = "BLOCKED_COMPUTE_EXHAUSTED"

    # Failed - Security
    FAIL_SECURITY_GATE = "FAIL_SECURITY_GATE"
    FAIL_PERMISSION_DENIED = "FAIL_PERMISSION_DENIED"

    # Failed - Validation
    FAIL_VALIDATION_ERROR = "FAIL_VALIDATION_ERROR"
    FAIL_EXFOLIATION_GATE = "FAIL_EXFOLIATION_GATE"
    FAIL_MANIFEST_INVALID = "FAIL_MANIFEST_INVALID"

    # Failed - Execution
    FAIL_EXECUTION_ERROR = "FAIL_EXECUTION_ERROR"
    FAIL_TIMEOUT = "FAIL_TIMEOUT"
    FAIL_WORKER_UNAVAILABLE = "FAIL_WORKER_UNAVAILABLE"

    # Failed - State
    FAIL_INVALID_TRANSITION = "FAIL_INVALID_TRANSITION"
    FAIL_ALREADY_TERMINAL = "FAIL_ALREADY_TERMINAL"

    # Failed - Action
    FAIL_UNSUPPORTED_ACTION = "FAIL_UNSUPPORTED_ACTION"

    # Failed - create_foundup (FOUNDUP_CREATE_ACTION_DRYRUN_PHASE1)
    FAIL_FOUNDUP_ID_EXISTS = "FAIL_FOUNDUP_ID_EXISTS"
    FAIL_CREATE_ALIASED_TO_EXTRACT = "FAIL_CREATE_ALIASED_TO_EXTRACT"
    FAIL_ENVELOPE_NOT_GATE_PASSED = "FAIL_ENVELOPE_NOT_GATE_PASSED"

    # Unknown
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Policy Flags
# ---------------------------------------------------------------------------


# HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1 (#746):
# Security/token gate flags are SERVER-AUTHORED ONLY. They MUST NOT be trusted
# from deserialized (untrusted) job data. PolicyFlags.from_dict forces every
# field in this frozenset to False regardless of inbound data; server authority
# comes exclusively from runtime validation write-back in the executor.
#
# NOT in this set (preserved across deserialization):
#   - dry_run_mode: operator-authored; True is the safe/sandbox direction.
_SERVER_AUTHORED_FLAGS: frozenset = frozenset(
    {
        "security_gate_checked",
        "security_gate_passed",
        "permission_gate_checked",
        "permission_gate_passed",
        "exfoliation_gate_checked",
        "exfoliation_gate_passed",
        "wsp_preflight_checked",
        "wsp_preflight_passed",
        "capability_token_checked",
        "capability_token_present",
        "capability_token_validated",
        "capability_token_scope_authorized",
    }
)


@dataclass(slots=True)
class PolicyFlags:
    """
    Gates and policies applied during job execution.

    All flags default to False (not checked/not passed).
    Set to True after gate passes.

    HXA24: Capability token policy flags added.
    These fields track whether a capability token was checked, present,
    validated, and scope-authorized. All default to False (safe).

    For D3+ operations, all four capability token flags must be True:
      - capability_token_checked: Token check was performed
      - capability_token_present: A token was provided
      - capability_token_validated: Token signature/expiry validated
      - capability_token_scope_authorized: Token scope covers the action
    """

    security_gate_checked: bool = False
    security_gate_passed: bool = False

    permission_gate_checked: bool = False
    permission_gate_passed: bool = False

    exfoliation_gate_checked: bool = False
    exfoliation_gate_passed: bool = False

    wsp_preflight_checked: bool = False
    wsp_preflight_passed: bool = False

    dry_run_mode: bool = True

    # HXA24: Capability token policy flags
    capability_token_checked: bool = False
    """Whether a capability token check was performed."""

    capability_token_present: bool = False
    """Whether a capability token was provided in the request."""

    capability_token_validated: bool = False
    """Whether the token signature and expiry were validated."""

    capability_token_scope_authorized: bool = False
    """Whether the token scope covers the requested action."""

    def to_dict(self) -> Dict[str, bool]:
        """Serialize to dict."""
        return {
            "security_gate_checked": self.security_gate_checked,
            "security_gate_passed": self.security_gate_passed,
            "permission_gate_checked": self.permission_gate_checked,
            "permission_gate_passed": self.permission_gate_passed,
            "exfoliation_gate_checked": self.exfoliation_gate_checked,
            "exfoliation_gate_passed": self.exfoliation_gate_passed,
            "wsp_preflight_checked": self.wsp_preflight_checked,
            "wsp_preflight_passed": self.wsp_preflight_passed,
            "dry_run_mode": self.dry_run_mode,
            # HXA24: Capability token policy flags
            "capability_token_checked": self.capability_token_checked,
            "capability_token_present": self.capability_token_present,
            "capability_token_validated": self.capability_token_validated,
            "capability_token_scope_authorized": self.capability_token_scope_authorized,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PolicyFlags:
        """Deserialize from dict.

        SECURITY (HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1, #746):
        Deserialized gate/token state is UNTRUSTED and is FORCED to False.
        Every field in ``_SERVER_AUTHORED_FLAGS`` (all security/permission/
        exfoliation/wsp-preflight gate flags and all four capability_token_*
        flags) is zeroed REGARDLESS of inbound data — a malicious or stale
        payload can never grant itself a passing gate or a valid token by
        carrying ``True`` here.

        Server authority for these flags comes EXCLUSIVELY from runtime
        validation write-back (see HermesJobExecutor.execute, which writes the
        validator verdict into job.policy_flags before the destructive-action
        guard reads it). Code that legitimately needs a flag True must set it
        via the direct ``PolicyFlags(...)`` constructor or by object attribute
        assignment (server-authored), NOT through this untrusted path.

        ONLY ``dry_run_mode`` is preserved from inbound data: it is
        operator-authored and ``True`` is the safe/sandbox direction.
        """
        # Single deserialization chokepoint. Both FoundUpJob.from_dict and
        # FoundUpJob.__post_init__ route here, so this covers every path.
        return cls(
            # Server-authored gate/token flags: forced False (untrusted input
            # is NOT read). See _SERVER_AUTHORED_FLAGS.
            security_gate_checked=False,
            security_gate_passed=False,
            permission_gate_checked=False,
            permission_gate_passed=False,
            exfoliation_gate_checked=False,
            exfoliation_gate_passed=False,
            wsp_preflight_checked=False,
            wsp_preflight_passed=False,
            capability_token_checked=False,
            capability_token_present=False,
            capability_token_validated=False,
            capability_token_scope_authorized=False,
            # Operator-authored: preserved (True is the safe/sandbox direction).
            dry_run_mode=bool(data.get("dry_run_mode", True)),
        )


# ---------------------------------------------------------------------------
# FoundUp Job Contract
# ---------------------------------------------------------------------------


@dataclass
class FoundUpJob:
    """
    Canonical FoundUp orchestration job contract.

    Shared between OpenClaw (creates job), Hermes (executes job),
    and FAM (tracks task completion).

    Identity fields link the job to its origin (intent) and target (foundup).
    Lifecycle fields track execution state.
    Audit fields enable WSP 97 truthful reporting.
    """

    # === Core Identity ===
    job_id: str
    """Unique job identifier. Format: j_{action}_{timestamp_hex}_{random_hex}"""

    tenant_id: str
    """Actor scope / owner. Maps to sender or commander identity."""

    foundup_id: Optional[str] = None
    """Target FoundUp (if job is foundup-scoped). May be None for system jobs."""

    intent_id: Optional[str] = None
    """Source request correlation. Links to OpenClawIntent session_key or similar."""

    # === Lifecycle ===
    status: JobStatus = JobStatus.QUEUED
    """Current lifecycle state."""

    previous_status: Optional[JobStatus] = None
    """Previous state (for audit trail)."""

    # === Execution Metadata ===
    requested_action: str = ""
    """Action being requested (e.g., 'extract', 'launch', 'validate')."""

    worker_id: Optional[str] = None
    """Worker/executor identity. Set when job moves to RUNNING."""

    idempotency_key: Optional[str] = None
    """
    Replay guard. If set, duplicate jobs with same key are rejected.
    Format: sha256(tenant_id:foundup_id:action:payload_hash)[:16]
    """

    # === Timestamps ===
    created_at: datetime = field(default_factory=utc_now)
    """Job creation timestamp."""

    started_at: Optional[datetime] = None
    """Execution start timestamp. Set when status → RUNNING."""

    completed_at: Optional[datetime] = None
    """Execution completion timestamp. Set when status → SUCCEEDED|FAILED."""

    blocked_at: Optional[datetime] = None
    """Blocking timestamp. Set when status → BLOCKED."""

    # === Truth/Audit Fields (WSP 97) ===
    status_reason_code: StatusReasonCode = StatusReasonCode.UNKNOWN
    """Machine-readable status reason."""

    status_reason_human: str = ""
    """Operator-readable status explanation."""

    evidence_refs: List[str] = field(default_factory=list)
    """
    Paths/IDs proving outcome.
    Examples: ["modules/foundups/gotjunk/foundup_manifest.json", "proof_123"]
    """

    policy_flags: PolicyFlags = field(default_factory=PolicyFlags)
    """Gates and policies applied during execution."""

    # === Payload (Opaque) ===
    payload: Dict[str, Any] = field(default_factory=dict)
    """
    Action-specific payload. Structure depends on requested_action.
    OpenClaw and Hermes agree on payload schema per action.
    """

    creation_mode: Optional[str] = None
    """Creation contract mode. ``create_foundup`` requires ``new_scaffold``."""
    genesis_envelope_digest: Optional[str] = None
    """SHA-256 binding to the validated FoundUp genesis envelope."""
    scaffold_contract_digest: Optional[str] = None
    """SHA-256 binding to the dry-run FoundUp scaffold contract."""
    # === Compute Metering ===
    compute_tier: str = "freemium"
    """Compute tier: freemium | basic | enterprise. Determines model routing."""

    compute_budget: Optional[int] = None
    """Allocated compute units for this job. None = unlimited (enterprise)."""

    compute_used: int = 0
    """Compute units consumed so far."""

    model_preference: str = "auto"
    """
    Model routing preference:
      auto     = RedDog picks based on tier/complexity
      free     = OpenRouter free models only (gemma, llama, etc.)
      standard = Paid models (sonnet, gpt-4o-mini)
      premium  = High-end (opus, gpt-4o)
    """

    # === Internal ===
    _transition_history: List[Dict[str, Any]] = field(default_factory=list)
    """Internal: records all state transitions for debugging."""

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.job_id or not self.job_id.strip():
            raise ValueError("job_id is required")
        if not self.tenant_id or not self.tenant_id.strip():
            raise ValueError("tenant_id is required")

        # Ensure status is JobStatus enum
        if isinstance(self.status, str):
            self.status = JobStatus(self.status)
        if isinstance(self.previous_status, str):
            self.previous_status = JobStatus(self.previous_status)
        if isinstance(self.status_reason_code, str):
            try:
                self.status_reason_code = StatusReasonCode(self.status_reason_code)
            except ValueError:
                self.status_reason_code = StatusReasonCode.UNKNOWN

        # Ensure policy_flags is PolicyFlags
        if isinstance(self.policy_flags, dict):
            self.policy_flags = PolicyFlags.from_dict(self.policy_flags)

    # ------------------------------------------------------------------
    # State Transitions
    # ------------------------------------------------------------------

    def transition_to(
        self,
        new_status: JobStatus,
        reason_code: StatusReasonCode,
        reason_human: str,
        worker_id: Optional[str] = None,
        evidence_refs: Optional[List[str]] = None,
    ) -> bool:
        """
        Attempt state transition with validation.

        Args:
            new_status: Target state
            reason_code: Machine-readable reason
            reason_human: Operator-readable explanation
            worker_id: Executor identity (for RUNNING transition)
            evidence_refs: Evidence to append

        Returns:
            True if transition succeeded, False if invalid
        """
        if not is_valid_transition(self.status, new_status):
            logger.warning(
                "[JOB] Invalid transition %s → %s for job %s",
                self.status.value,
                new_status.value,
                self.job_id,
            )
            self.status_reason_code = StatusReasonCode.FAIL_INVALID_TRANSITION
            self.status_reason_human = (
                f"Cannot transition from {self.status.value} to {new_status.value}"
            )
            return False

        now = utc_now()

        # Record transition
        self._transition_history.append({
            "from": self.status.value,
            "to": new_status.value,
            "reason_code": reason_code.value,
            "reason_human": reason_human,
            "timestamp": now.isoformat(),
        })

        # Update state
        self.previous_status = self.status
        self.status = new_status
        self.status_reason_code = reason_code
        self.status_reason_human = reason_human

        # Update timestamps
        if new_status == JobStatus.RUNNING:
            self.started_at = now
            if worker_id:
                self.worker_id = worker_id
        elif new_status == JobStatus.BLOCKED:
            self.blocked_at = now
        elif is_terminal_status(new_status):
            self.completed_at = now

        # Append evidence
        if evidence_refs:
            self.evidence_refs.extend(evidence_refs)

        logger.info(
            "[JOB] Transition %s: %s → %s (%s)",
            self.job_id,
            self.previous_status.value if self.previous_status else "None",
            new_status.value,
            reason_code.value,
        )
        return True

    def start(
        self,
        worker_id: str,
        reason_human: str = "Job started by worker",
    ) -> bool:
        """Convenience: transition QUEUED → RUNNING."""
        return self.transition_to(
            new_status=JobStatus.RUNNING,
            reason_code=StatusReasonCode.OK_VALIDATION_PASSED,
            reason_human=reason_human,
            worker_id=worker_id,
        )

    def block(
        self,
        reason_code: StatusReasonCode,
        reason_human: str,
    ) -> bool:
        """Convenience: transition RUNNING → BLOCKED."""
        return self.transition_to(
            new_status=JobStatus.BLOCKED,
            reason_code=reason_code,
            reason_human=reason_human,
        )

    def resume(
        self,
        reason_human: str = "Blocker resolved",
    ) -> bool:
        """Convenience: transition BLOCKED → RUNNING."""
        return self.transition_to(
            new_status=JobStatus.RUNNING,
            reason_code=StatusReasonCode.OK_VALIDATION_PASSED,
            reason_human=reason_human,
        )

    def succeed(
        self,
        reason_human: str = "Job completed successfully",
        evidence_refs: Optional[List[str]] = None,
    ) -> bool:
        """Convenience: transition RUNNING → SUCCEEDED."""
        return self.transition_to(
            new_status=JobStatus.SUCCEEDED,
            reason_code=StatusReasonCode.OK_COMPLETED,
            reason_human=reason_human,
            evidence_refs=evidence_refs,
        )

    def fail(
        self,
        reason_code: StatusReasonCode,
        reason_human: str,
        evidence_refs: Optional[List[str]] = None,
    ) -> bool:
        """Convenience: transition to FAILED from any non-terminal state."""
        return self.transition_to(
            new_status=JobStatus.FAILED,
            reason_code=reason_code,
            reason_human=reason_human,
            evidence_refs=evidence_refs,
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize job to dict for logging/persistence."""
        return {
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "foundup_id": self.foundup_id,
            "intent_id": self.intent_id,
            "status": self.status.value,
            "previous_status": self.previous_status.value if self.previous_status else None,
            "requested_action": self.requested_action,
            "worker_id": self.worker_id,
            "idempotency_key": self.idempotency_key,
            "created_at": utc_iso(self.created_at),
            "started_at": utc_iso(self.started_at),
            "completed_at": utc_iso(self.completed_at),
            "blocked_at": utc_iso(self.blocked_at),
            "status_reason_code": self.status_reason_code.value,
            "status_reason_human": self.status_reason_human,
            "evidence_refs": self.evidence_refs,
            "policy_flags": self.policy_flags.to_dict(),
            "payload": self.payload,
            "creation_mode": self.creation_mode,
            "genesis_envelope_digest": self.genesis_envelope_digest,
            "scaffold_contract_digest": self.scaffold_contract_digest,
            "compute_tier": self.compute_tier,
            "compute_budget": self.compute_budget,
            "compute_used": self.compute_used,
            "model_preference": self.model_preference,
            "_transition_history": self._transition_history,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize job to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FoundUpJob:
        """Deserialize job from dict."""
        job = cls(
            job_id=data["job_id"],
            tenant_id=data["tenant_id"],
            foundup_id=data.get("foundup_id"),
            intent_id=data.get("intent_id"),
            status=JobStatus(data.get("status", "queued")),
            previous_status=(
                JobStatus(data["previous_status"])
                if data.get("previous_status")
                else None
            ),
            requested_action=data.get("requested_action", ""),
            worker_id=data.get("worker_id"),
            idempotency_key=data.get("idempotency_key"),
            status_reason_code=_parse_reason_code(
                data.get("status_reason_code", "UNKNOWN")
            ),
            status_reason_human=data.get("status_reason_human", ""),
            evidence_refs=data.get("evidence_refs", []),
            policy_flags=PolicyFlags.from_dict(data.get("policy_flags", {})),
            payload=data.get("payload", {}),
            creation_mode=data.get("creation_mode"),
            genesis_envelope_digest=data.get("genesis_envelope_digest"),
            scaffold_contract_digest=data.get("scaffold_contract_digest"),
            compute_tier=data.get("compute_tier", "freemium"),
            compute_budget=data.get("compute_budget"),
            compute_used=data.get("compute_used", 0),
            model_preference=data.get("model_preference", "auto"),
        )

        # Restore timestamps
        for ts_field in ("created_at", "started_at", "completed_at", "blocked_at"):
            ts_value = data.get(ts_field)
            if ts_value:
                setattr(job, ts_field, datetime.fromisoformat(ts_value))

        # Restore transition history
        job._transition_history = data.get("_transition_history", [])

        return job


# ---------------------------------------------------------------------------
# Factory Functions
# ---------------------------------------------------------------------------


def generate_job_id(action: str) -> str:
    """
    Generate unique job ID.

    Format: j_{action}_{timestamp_hex}_{random_hex}
    Example: j_extract_18a3b2c1_f4e5d6
    """
    import secrets

    timestamp_hex = hex(int(utc_now().timestamp()))[2:][:8]
    random_hex = secrets.token_hex(3)
    action_slug = action.lower().replace(" ", "_")[:20]
    return f"j_{action_slug}_{timestamp_hex}_{random_hex}"


def generate_idempotency_key(
    tenant_id: str,
    foundup_id: Optional[str],
    action: str,
    payload: Dict[str, Any],
) -> str:
    """
    Generate deterministic idempotency key.

    Format: sha256(tenant_id:foundup_id:action:payload_json)[:16]
    """
    payload_json = json.dumps(payload, sort_keys=True, default=str)
    key_input = f"{tenant_id}:{foundup_id or ''}:{action}:{payload_json}"
    return hashlib.sha256(key_input.encode()).hexdigest()[:16]


def create_job(
    tenant_id: str,
    requested_action: str,
    foundup_id: Optional[str] = None,
    intent_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    generate_idempotency: bool = True,
    creation_mode: Optional[str] = None,
    genesis_envelope_digest: Optional[str] = None,
    scaffold_contract_digest: Optional[str] = None,
) -> FoundUpJob:
    """
    Factory function to create a new FoundUpJob.

    Args:
        tenant_id: Actor scope / owner
        requested_action: Action to perform
        foundup_id: Target FoundUp (optional)
        intent_id: Source request correlation (optional)
        payload: Action-specific payload (optional)
        generate_idempotency: Auto-generate idempotency key
        creation_mode: Typed create_foundup mode binding (optional)
        genesis_envelope_digest: Typed genesis-envelope lineage binding (optional)
        scaffold_contract_digest: Typed scaffold-contract lineage binding (optional)

    Returns:
        FoundUpJob in QUEUED state
    """
    job_id = generate_job_id(requested_action)
    payload = payload or {}

    idempotency_key = None
    if generate_idempotency:
        idempotency_key = generate_idempotency_key(
            tenant_id, foundup_id, requested_action, payload
        )

    return FoundUpJob(
        job_id=job_id,
        tenant_id=tenant_id,
        foundup_id=foundup_id,
        intent_id=intent_id,
        requested_action=requested_action,
        idempotency_key=idempotency_key,
        payload=payload,
        creation_mode=creation_mode,
        genesis_envelope_digest=genesis_envelope_digest,
        scaffold_contract_digest=scaffold_contract_digest,
    )
