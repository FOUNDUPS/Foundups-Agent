# -*- coding: utf-8 -*-
"""
WRE FoundUpJob Router — Phase 1 Routing Envelope

Routes FoundUpJob instances to appropriate execution backends based on
requested_action and job state. Returns typed routing decisions without
executing the job.

Architecture:
  OpenClaw -> FoundUpJob -> WRE Router -> RouteEnvelope -> Hermes/FAM (later)

This is Phase 1: routing seam only. Actual execution is deferred to W4
(Hermes adapter) and future slices.

WSP Compliance:
  WSP 11  : Interface contract (typed envelope)
  WSP 50  : Pre-Action Verification (identity validation)
  WSP 77  : Agent Coordination (target_backend routing)
  WSP 97  : System Execution Prompting (truthful route_status)

NAVIGATION:
  -> Called by: OpenClaw orchestrator, future WRE gateway
  -> Related: modules/communication/moltbot_bridge/src/foundup_job_contract.py
  -> Depends on: FoundUpJob, JobStatus, PolicyFlags
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("wre_foundup_job_router")


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Route Status and Target Backend
# ---------------------------------------------------------------------------


class RouteStatus(str, Enum):
    """
    Routing decision status.

    ROUTED       : Job successfully routed to a target backend
    QUEUED       : Job acknowledged, queued for later processing
    BLOCKED      : Job blocked by policy or missing dependencies
    UNSUPPORTED  : Requested action not supported by any backend
    FAILED       : Routing failed due to validation error
    """

    ROUTED = "routed"
    QUEUED = "queued"
    BLOCKED = "blocked"
    UNSUPPORTED = "unsupported"
    FAILED = "failed"


class TargetBackend(str, Enum):
    """
    Execution backend targets.

    HERMES_BUILDER   : Hermes FoundUp builder (build/extract)
    HERMES_VALIDATOR : Hermes validation (validate)
    OPENCLAW_QUEUE   : OpenClaw job queue (queue_foundup_job)
    FAM_TRACKER      : FAM task tracker (future)
    NONE             : No routing target (blocked/failed/unsupported)
    """

    HERMES_BUILDER = "hermes_builder"
    HERMES_VALIDATOR = "hermes_validator"
    OPENCLAW_QUEUE = "openclaw_queue"
    FAM_TRACKER = "fam_tracker"
    NONE = "none"


# Action -> Backend mapping
_ACTION_BACKEND_MAP: Dict[str, TargetBackend] = {
    "build_foundup": TargetBackend.HERMES_BUILDER,
    "extract_foundup": TargetBackend.HERMES_BUILDER,
    "validate_foundup": TargetBackend.HERMES_VALIDATOR,
    "queue_foundup_job": TargetBackend.OPENCLAW_QUEUE,
}


# ---------------------------------------------------------------------------
# Routing Reason Codes
# ---------------------------------------------------------------------------


class RouteReasonCode(str, Enum):
    """
    Machine-readable routing reason codes.
    """

    # Success
    OK_ROUTED = "OK_ROUTED"
    OK_QUEUED = "OK_QUEUED"

    # Blocked
    BLOCKED_MISSING_JOB_ID = "BLOCKED_MISSING_JOB_ID"
    BLOCKED_MISSING_TENANT_ID = "BLOCKED_MISSING_TENANT_ID"
    BLOCKED_MISSING_ACTION = "BLOCKED_MISSING_ACTION"
    BLOCKED_TERMINAL_STATUS = "BLOCKED_TERMINAL_STATUS"
    BLOCKED_POLICY_GATE = "BLOCKED_POLICY_GATE"

    # Unsupported
    UNSUPPORTED_ACTION = "UNSUPPORTED_ACTION"

    # Failed
    FAIL_VALIDATION = "FAIL_VALIDATION"
    FAIL_INTERNAL = "FAIL_INTERNAL"


# ---------------------------------------------------------------------------
# Envelope Validation (WSP 97: Distinguish FoundUpJob from generic DAE)
# ---------------------------------------------------------------------------


class EnvelopeType(str, Enum):
    """
    Envelope type classification.

    GENERIC_DAE    : Standard DAE envelope (objective-only minimum)
    FOUNDUP_JOB    : FoundUpJob execution envelope (strict validation)
    """

    GENERIC_DAE = "generic_dae"
    FOUNDUP_JOB = "foundup_job"


class EnvelopeValidationCode(str, Enum):
    """
    Envelope validation reason codes.
    """

    # Valid
    VALID = "VALID"
    VALID_DRY_RUN_DEFAULTED = "VALID_DRY_RUN_DEFAULTED"
    VALID_EVIDENCE_PENDING = "VALID_EVIDENCE_PENDING"

    # Invalid - Missing Fields
    MISSING_JOB_ID = "MISSING_JOB_ID"
    MISSING_FOUNDUP_ID = "MISSING_FOUNDUP_ID"
    MISSING_TENANT_ID = "MISSING_TENANT_ID"
    MISSING_ACTION = "MISSING_ACTION"
    MISSING_POLICY_FLAGS = "MISSING_POLICY_FLAGS"

    # Invalid - Policy
    DRY_RUN_NOT_SET = "DRY_RUN_NOT_SET"

    # Invalid - Evidence
    INVALID_EVIDENCE_REFS_TYPE = "INVALID_EVIDENCE_REFS_TYPE"
    INVALID_EVIDENCE_REF_ENTRY = "INVALID_EVIDENCE_REF_ENTRY"

    # Invalid - Live Mode Policy Gates
    LIVE_MODE_NOT_ENABLED = "LIVE_MODE_NOT_ENABLED"
    LIVE_MODE_REQUIRES_HUMAN_APPROVAL = "LIVE_MODE_REQUIRES_HUMAN_APPROVAL"
    LIVE_MODE_REQUIRES_EVIDENCE = "LIVE_MODE_REQUIRES_EVIDENCE"
    LIVE_MODE_REQUIRES_SECURITY_GATE = "LIVE_MODE_REQUIRES_SECURITY_GATE"

    # Invalid - Compute Budget
    INVALID_COMPUTE_BUDGET_TYPE = "INVALID_COMPUTE_BUDGET_TYPE"
    INVALID_COMPUTE_BUDGET_NEGATIVE = "INVALID_COMPUTE_BUDGET_NEGATIVE"
    INVALID_COMPUTE_USED_TYPE = "INVALID_COMPUTE_USED_TYPE"
    INVALID_COMPUTE_USED_NEGATIVE = "INVALID_COMPUTE_USED_NEGATIVE"
    COMPUTE_USED_EXCEEDS_BUDGET = "COMPUTE_USED_EXCEEDS_BUDGET"
    LIVE_MODE_REQUIRES_COMPUTE_BUDGET = "LIVE_MODE_REQUIRES_COMPUTE_BUDGET"
    INVALID_COMPUTE_TIER = "INVALID_COMPUTE_TIER"
    INVALID_MODEL_PREFERENCE = "INVALID_MODEL_PREFERENCE"

    # Invalid - Model Routing Policy
    MODEL_PREFERENCE_NOT_ALLOWED_FOR_TIER = "MODEL_PREFERENCE_NOT_ALLOWED_FOR_TIER"


@dataclass
class EnvelopeValidationResult:
    """
    Result of FoundUpJob envelope validation.

    WSP 97 Truth: Returns explicit validation status with missing field list.
    Evidence validation does NOT imply verification_complete, cabr_ready, or payout_ready.
    """

    valid: bool
    """Whether envelope passes validation."""

    envelope_type: EnvelopeType
    """Detected envelope type."""

    validation_code: EnvelopeValidationCode
    """Machine-readable validation result."""

    missing_fields: List[str] = field(default_factory=list)
    """List of missing required fields."""

    validation_message: str = ""
    """Human-readable validation explanation."""

    dry_run_defaulted: bool = False
    """True if dry_run was defaulted to True (WSP 97 safety default)."""

    policy_flags_snapshot: Dict[str, bool] = field(default_factory=dict)
    """Policy flags at validation time (if present)."""

    # === Evidence Validation (WSP 97 Truth) ===
    evidence_refs_validated: bool = False
    """True if evidence_refs passed validation."""

    evidence_refs_count: int = 0
    """Number of evidence refs in envelope."""

    evidence_pending: bool = False
    """True if evidence is pending (empty in dry-run mode)."""

    # === Live Mode Policy Gates ===
    is_live_mode: bool = False
    """True if dry_run_mode=False (explicit live execution requested)."""

    live_mode_gates_passed: bool = False
    """True if all required live mode gates passed."""

    missing_live_gates: List[str] = field(default_factory=list)
    """List of missing live mode policy gates."""

    # === Compute Budget Validation ===
    compute_budget_validated: bool = False
    """True if compute budget fields passed validation."""

    compute_budget_value: Optional[int] = None
    """Compute budget from envelope (None = unlimited/not set)."""

    compute_used_value: int = 0
    """Compute used from envelope."""

    compute_tier_value: str = ""
    """Compute tier from envelope."""

    model_preference_value: str = ""
    """Model preference from envelope."""

    # === Model Routing Policy Validation ===
    model_routing_policy_validated: bool = False
    """True if tier/preference compatibility passed validation."""

    model_routing_policy_reason: str = ""
    """Explanation of routing policy validation result."""

    # === WSP 97 Truth Fields (ALWAYS False at validation time) ===
    verification_complete: bool = False
    """WSP 97: Always False. Evidence presence does NOT imply verification."""

    cabr_ready: bool = False
    """WSP 97: Always False. Evidence does NOT enable CABR claims."""

    payout_ready: bool = False
    """WSP 97: Always False. Evidence does NOT enable payout claims."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging/API response."""
        return {
            "valid": self.valid,
            "envelope_type": self.envelope_type.value,
            "validation_code": self.validation_code.value,
            "missing_fields": self.missing_fields,
            "validation_message": self.validation_message,
            "dry_run_defaulted": self.dry_run_defaulted,
            "policy_flags_snapshot": self.policy_flags_snapshot,
            "evidence_refs_validated": self.evidence_refs_validated,
            "evidence_refs_count": self.evidence_refs_count,
            "evidence_pending": self.evidence_pending,
            # Live mode gates
            "is_live_mode": self.is_live_mode,
            "live_mode_gates_passed": self.live_mode_gates_passed,
            "missing_live_gates": self.missing_live_gates,
            # Compute budget
            "compute_budget_validated": self.compute_budget_validated,
            "compute_budget_value": self.compute_budget_value,
            "compute_used_value": self.compute_used_value,
            "compute_tier_value": self.compute_tier_value,
            "model_preference_value": self.model_preference_value,
            # Model routing policy
            "model_routing_policy_validated": self.model_routing_policy_validated,
            "model_routing_policy_reason": self.model_routing_policy_reason,
            # WSP 97 Truth: Always False at validation time
            "verification_complete": self.verification_complete,
            "cabr_ready": self.cabr_ready,
            "payout_ready": self.payout_ready,
        }


def detect_envelope_type(envelope: Dict[str, Any]) -> EnvelopeType:
    """
    Detect whether envelope is a FoundUpJob or generic DAE envelope.

    FoundUpJob indicators:
      - has job_id field
      - has requested_action in CANONICAL_ACTIONS
      - has foundup_id field
      - has tenant_id field

    Args:
        envelope: Dict envelope to classify

    Returns:
        EnvelopeType.FOUNDUP_JOB if FoundUpJob indicators present,
        EnvelopeType.GENERIC_DAE otherwise
    """
    # FoundUpJob indicators
    foundup_job_fields = {"job_id", "foundup_id", "tenant_id", "requested_action"}

    # Check for FoundUpJob signature
    present_fields = set(envelope.keys()) & foundup_job_fields
    if len(present_fields) >= 2:  # At least 2 FoundUpJob fields = FoundUpJob envelope
        return EnvelopeType.FOUNDUP_JOB

    # Check for canonical actions
    action = envelope.get("requested_action", "")
    if action and action in {
        "build_foundup",
        "extract_foundup",
        "validate_foundup",
        "queue_foundup_job",
    }:
        return EnvelopeType.FOUNDUP_JOB

    return EnvelopeType.GENERIC_DAE


def _sanitize_untrusted_policy_flags_dict(
    policy_flags: Dict[str, Any],
) -> Tuple[Dict[str, bool], bool]:
    """Sanitize a raw, untrusted envelope ``policy_flags`` dict at the router boundary.

    SECURITY (FOUNDUP_JOB_ROUTER_POLICYFLAGS_BOUNDARY_SANITIZATION, #752):
    A raw ``policy_flags`` dict arriving on an inbound envelope is UNTRUSTED.
    A malicious or stale caller can self-assert any gate/token flag (e.g.
    ``security_gate_passed=True``) by carrying ``True`` in the dict. This is the
    untrusted-envelope trust boundary: every server-authored gate/token flag
    (all of ``_SERVER_AUTHORED_FLAGS`` — security_gate_*, permission_gate_*,
    exfoliation_gate_*, wsp_preflight_*, capability_token_*) is FORCED to False
    here regardless of inbound data. Server authority for those flags comes
    EXCLUSIVELY from a server-authored ``PolicyFlags`` object snapshot (the
    ``hasattr(policy_flags, "to_dict")`` branch), never from a raw dict.

    Only ``dry_run_mode`` survives from inbound data: it is operator-authored and
    ``True`` is the safe/sandbox direction. ``PolicyFlags.from_dict`` yields
    ``dry_run_mode=False`` when the key is absent, which would mis-classify a
    missing flag as LIVE; this function restores the router's safe default so an
    absent ``dry_run_mode`` is treated as dry-run (True), NOT live.

    Args:
        policy_flags: Raw untrusted dict from the inbound envelope.

    Returns:
        Tuple of (sanitized_policy_snapshot, dry_run_defaulted) where the snapshot
        has all server-authored gate/token flags forced False and a safe
        ``dry_run_mode`` default applied when the inbound dict omitted it.
    """
    # Deferred import to avoid a circular dependency (router <-> contract); matches
    # the existing deferred-import pattern used elsewhere in this module.
    from modules.communication.moltbot_bridge.src.foundup_job_contract import PolicyFlags

    # from_dict zeroes ALL _SERVER_AUTHORED_FLAGS and preserves only dry_run_mode.
    sanitized = PolicyFlags.from_dict(policy_flags).to_dict()

    dry_run_defaulted = "dry_run_mode" not in policy_flags
    if dry_run_defaulted:
        # from_dict({}) yields dry_run_mode=False; restore the router's safe
        # default so missing flags are NOT treated as live.
        sanitized["dry_run_mode"] = True

    return sanitized, dry_run_defaulted


def validate_foundup_job_envelope(envelope: Dict[str, Any]) -> EnvelopeValidationResult:
    """
    Validate envelope for FoundUpJob execution.

    WSP 97 Truth Boundaries:
      - Requires: job_id, foundup_id, tenant_id, requested_action
      - Requires: policy_flags with dry_run_mode (defaults to True if missing)
      - Returns explicit validation failure with missing field list

    Args:
        envelope: Dict containing FoundUpJob envelope fields

    Returns:
        EnvelopeValidationResult with validation status and details
    """
    envelope_type = detect_envelope_type(envelope)

    # If this is a generic DAE envelope, use permissive validation
    if envelope_type == EnvelopeType.GENERIC_DAE:
        if "objective" in envelope:
            return EnvelopeValidationResult(
                valid=True,
                envelope_type=EnvelopeType.GENERIC_DAE,
                validation_code=EnvelopeValidationCode.VALID,
                validation_message="Generic DAE envelope validated (objective present)",
            )
        else:
            return EnvelopeValidationResult(
                valid=False,
                envelope_type=EnvelopeType.GENERIC_DAE,
                validation_code=EnvelopeValidationCode.MISSING_ACTION,
                missing_fields=["objective"],
                validation_message="Generic DAE envelope requires 'objective' field",
            )

    # FoundUpJob envelope: strict validation
    missing_fields = []

    # Required identity fields
    if not envelope.get("job_id"):
        missing_fields.append("job_id")

    if not envelope.get("foundup_id"):
        missing_fields.append("foundup_id")

    if not envelope.get("tenant_id"):
        missing_fields.append("tenant_id")

    if not envelope.get("requested_action"):
        missing_fields.append("requested_action")

    # Early return if identity fields missing
    if missing_fields:
        # Determine primary missing field for code
        if "job_id" in missing_fields:
            code = EnvelopeValidationCode.MISSING_JOB_ID
        elif "foundup_id" in missing_fields:
            code = EnvelopeValidationCode.MISSING_FOUNDUP_ID
        elif "tenant_id" in missing_fields:
            code = EnvelopeValidationCode.MISSING_TENANT_ID
        else:
            code = EnvelopeValidationCode.MISSING_ACTION

        return EnvelopeValidationResult(
            valid=False,
            envelope_type=EnvelopeType.FOUNDUP_JOB,
            validation_code=code,
            missing_fields=missing_fields,
            validation_message=f"FoundUpJob envelope missing required fields: {missing_fields}",
        )

    # Policy flags / dry_run validation
    policy_flags = envelope.get("policy_flags")
    policy_snapshot: Dict[str, bool] = {}
    dry_run_defaulted = False

    if policy_flags is None:
        # WSP 97: Default dry_run to True for safety
        dry_run_defaulted = True
        policy_snapshot = {"dry_run_mode": True}
        logger.info(
            "[WSP97] FoundUpJob envelope missing policy_flags - dry_run_mode defaulted to True"
        )
    elif isinstance(policy_flags, dict):
        # SECURITY (#752): raw envelope dict is UNTRUSTED. Sanitize so self-asserted
        # gate/token flags cannot survive; preserve safe dry_run default.
        policy_snapshot, dry_run_defaulted = _sanitize_untrusted_policy_flags_dict(
            policy_flags
        )
        if dry_run_defaulted:
            logger.info(
                "[WSP97] FoundUpJob envelope missing dry_run_mode - defaulted to True"
            )
    elif hasattr(policy_flags, "to_dict"):
        policy_snapshot = policy_flags.to_dict()
        if not policy_snapshot.get("dry_run_mode"):
            dry_run_defaulted = True
            policy_snapshot["dry_run_mode"] = True

    # Determine if this is live mode (explicit dry_run_mode=False)
    is_live_mode = policy_snapshot.get("dry_run_mode") is False and not dry_run_defaulted

    # Evidence refs validation (WSP 97: validate shape, not verification)
    evidence_result = _validate_evidence_refs(
        envelope.get("evidence_refs"),
        is_dry_run=not is_live_mode,  # Dry-run if not explicitly live mode
    )

    if not evidence_result["valid"]:
        return EnvelopeValidationResult(
            valid=False,
            envelope_type=EnvelopeType.FOUNDUP_JOB,
            validation_code=evidence_result["code"],
            missing_fields=[],
            validation_message=evidence_result["message"],
            dry_run_defaulted=dry_run_defaulted,
            policy_flags_snapshot=policy_snapshot,
            evidence_refs_validated=False,
            evidence_refs_count=evidence_result.get("count", 0),
            evidence_pending=False,
            is_live_mode=is_live_mode,
        )

    evidence_pending = evidence_result.get("pending", False)
    evidence_count = evidence_result.get("count", 0)

    # Live mode policy gate validation
    if is_live_mode:
        live_gate_result = _validate_live_mode_gates(
            policy_snapshot=policy_snapshot,
            evidence_count=evidence_count,
            evidence_pending=evidence_pending,
        )

        if not live_gate_result["valid"]:
            return EnvelopeValidationResult(
                valid=False,
                envelope_type=EnvelopeType.FOUNDUP_JOB,
                validation_code=live_gate_result["code"],
                missing_fields=[],
                validation_message=live_gate_result["message"],
                dry_run_defaulted=dry_run_defaulted,
                policy_flags_snapshot=policy_snapshot,
                evidence_refs_validated=True,
                evidence_refs_count=evidence_count,
                evidence_pending=evidence_pending,
                is_live_mode=True,
                live_mode_gates_passed=False,
                missing_live_gates=live_gate_result.get("missing_gates", []),
            )

    # Compute budget validation (WSP 97: structural only, no metering claims)
    compute_result = _validate_compute_budget(envelope, is_live_mode=is_live_mode)

    if not compute_result["valid"]:
        return EnvelopeValidationResult(
            valid=False,
            envelope_type=EnvelopeType.FOUNDUP_JOB,
            validation_code=compute_result["code"],
            missing_fields=[],
            validation_message=compute_result["message"],
            dry_run_defaulted=dry_run_defaulted,
            policy_flags_snapshot=policy_snapshot,
            evidence_refs_validated=True,
            evidence_refs_count=evidence_count,
            evidence_pending=evidence_pending,
            is_live_mode=is_live_mode,
            live_mode_gates_passed=is_live_mode,
            compute_budget_validated=False,
            compute_budget_value=compute_result.get("budget"),
            compute_used_value=compute_result.get("used", 0),
            compute_tier_value=compute_result.get("tier", ""),
            model_preference_value=compute_result.get("model_preference", ""),
            model_routing_policy_validated=compute_result.get("routing_policy_validated", False),
            model_routing_policy_reason=compute_result.get("routing_policy_reason", ""),
        )

    # Valid FoundUpJob envelope
    # Determine validation code
    if evidence_pending:
        validation_code = EnvelopeValidationCode.VALID_EVIDENCE_PENDING
    elif dry_run_defaulted:
        validation_code = EnvelopeValidationCode.VALID_DRY_RUN_DEFAULTED
    else:
        validation_code = EnvelopeValidationCode.VALID

    return EnvelopeValidationResult(
        valid=True,
        envelope_type=EnvelopeType.FOUNDUP_JOB,
        validation_code=validation_code,
        validation_message="FoundUpJob envelope validated successfully",
        dry_run_defaulted=dry_run_defaulted,
        policy_flags_snapshot=policy_snapshot,
        evidence_refs_validated=True,
        evidence_refs_count=evidence_count,
        evidence_pending=evidence_pending,
        is_live_mode=is_live_mode,
        live_mode_gates_passed=is_live_mode,  # True only if live mode and passed gates
        # Compute budget (WSP 97: structural validation, no metering claims)
        compute_budget_validated=True,
        compute_budget_value=compute_result.get("budget"),
        compute_used_value=compute_result.get("used", 0),
        compute_tier_value=compute_result.get("tier", "freemium"),
        model_preference_value=compute_result.get("model_preference", "auto"),
        # Model routing policy (WSP 97: policy validation, no model selected)
        model_routing_policy_validated=compute_result.get("routing_policy_validated", True),
        model_routing_policy_reason=compute_result.get("routing_policy_reason", ""),
        # WSP 97 Truth: Always False at validation time
        verification_complete=False,
        cabr_ready=False,
        payout_ready=False,
    )


def _validate_live_mode_gates(
    policy_snapshot: Dict[str, bool],
    evidence_count: int,
    evidence_pending: bool,
) -> Dict[str, Any]:
    """
    Validate live mode policy gates for FoundUpJob execution.

    Live mode (dry_run_mode=False) requires explicit approval and evidence
    before any non-dry-run execution can proceed.

    WSP 97 Truth Boundaries:
      - Live mode gates do NOT imply verification_complete=True
      - Live mode gates do NOT enable CABR or payout claims
      - This is validation only - no actual execution occurs

    Required gates for Phase 1:
      - human_approval=True OR permission_gate_passed=True
      - security_gate_passed=True (required in live mode)
      - Non-empty evidence_refs (evidence_pending=False)

    SECURITY (#752): Gate 2 is FAIL-CLOSED. In live mode, security MUST have
    passed; ``security_gate_passed`` is read from a server-authored snapshot only
    (raw envelope dicts are sanitized to False upstream), so a self-asserted raw
    dict can never satisfy this gate. The legacy ``security_gate_checked`` opt-in
    is no longer a precondition.

    Args:
        policy_snapshot: Policy flags at validation time
        evidence_count: Number of evidence refs in envelope
        evidence_pending: Whether evidence is pending

    Returns:
        Dict with: valid, code, message, missing_gates
    """
    missing_gates: List[str] = []

    # Gate 1: Human approval OR permission gate passed
    human_approval = policy_snapshot.get("human_approval", False)
    permission_gate_passed = policy_snapshot.get("permission_gate_passed", False)

    if not human_approval and not permission_gate_passed:
        missing_gates.append("human_approval")

    # Gate 2: Security gate (FAIL-CLOSED) — must pass in live mode.
    # security_gate_checked is retained for logging only; it is NOT a precondition.
    security_gate_checked = policy_snapshot.get("security_gate_checked", False)
    security_gate_passed = policy_snapshot.get("security_gate_passed", False)

    if not security_gate_passed:
        missing_gates.append("security_gate_passed")
        logger.info(
            "[WSP97] Live mode security_gate_passed=False "
            "(security_gate_checked=%s) - fail-closed",
            security_gate_checked,
        )

    # Gate 3: Evidence must be present (not pending)
    if evidence_pending or evidence_count == 0:
        missing_gates.append("evidence_refs")

    # Determine result
    if missing_gates:
        # Determine primary failure code
        if "human_approval" in missing_gates:
            code = EnvelopeValidationCode.LIVE_MODE_REQUIRES_HUMAN_APPROVAL
        elif "security_gate_passed" in missing_gates:
            code = EnvelopeValidationCode.LIVE_MODE_REQUIRES_SECURITY_GATE
        elif "evidence_refs" in missing_gates:
            code = EnvelopeValidationCode.LIVE_MODE_REQUIRES_EVIDENCE
        else:
            code = EnvelopeValidationCode.LIVE_MODE_NOT_ENABLED

        return {
            "valid": False,
            "code": code,
            "message": f"Live mode requires gates: {missing_gates}",
            "missing_gates": missing_gates,
        }

    # All gates passed
    logger.info("[WSP97] Live mode gates passed - validation only, no execution")
    return {
        "valid": True,
        "code": EnvelopeValidationCode.VALID,
        "message": "Live mode gates passed (validation only)",
        "missing_gates": [],
    }


def _validate_evidence_refs(
    evidence_refs: Any,
    is_dry_run: bool = True,
) -> Dict[str, Any]:
    """
    Validate evidence_refs shape for FoundUpJob envelope.

    WSP 97 Truth Boundaries:
      - Evidence validation proves traceability shape only
      - Evidence does NOT imply verification_complete=True
      - Evidence does NOT enable CABR or payout claims
      - Empty evidence_refs accepted in dry-run mode (pending)

    Args:
        evidence_refs: Evidence refs from envelope (may be None, list, or invalid)
        is_dry_run: Whether dry_run_mode is True (allows empty evidence)

    Returns:
        Dict with: valid, code, message, count, pending
    """
    # No evidence_refs field: allowed (pending if dry-run)
    if evidence_refs is None:
        if is_dry_run:
            return {
                "valid": True,
                "code": EnvelopeValidationCode.VALID_EVIDENCE_PENDING,
                "message": "Evidence refs pending (dry-run mode)",
                "count": 0,
                "pending": True,
            }
        else:
            # Live mode without evidence: still valid but flagged
            logger.warning(
                "[WSP97] FoundUpJob envelope has no evidence_refs in live mode"
            )
            return {
                "valid": True,
                "code": EnvelopeValidationCode.VALID,
                "message": "Evidence refs not provided (live mode)",
                "count": 0,
                "pending": False,
            }

    # Must be a list
    if not isinstance(evidence_refs, list):
        return {
            "valid": False,
            "code": EnvelopeValidationCode.INVALID_EVIDENCE_REFS_TYPE,
            "message": f"evidence_refs must be a list, got {type(evidence_refs).__name__}",
            "count": 0,
            "pending": False,
        }

    # Empty list: allowed in dry-run mode
    if len(evidence_refs) == 0:
        if is_dry_run:
            return {
                "valid": True,
                "code": EnvelopeValidationCode.VALID_EVIDENCE_PENDING,
                "message": "Evidence refs empty (dry-run mode, pending)",
                "count": 0,
                "pending": True,
            }
        else:
            # Live mode with empty list: still valid
            return {
                "valid": True,
                "code": EnvelopeValidationCode.VALID,
                "message": "Evidence refs empty (live mode)",
                "count": 0,
                "pending": False,
            }

    # Validate each entry
    for idx, ref in enumerate(evidence_refs):
        if isinstance(ref, str):
            # String refs must be non-empty
            if not ref.strip():
                return {
                    "valid": False,
                    "code": EnvelopeValidationCode.INVALID_EVIDENCE_REF_ENTRY,
                    "message": f"evidence_refs[{idx}] is empty string",
                    "count": len(evidence_refs),
                    "pending": False,
                }
        elif isinstance(ref, dict):
            # Dict refs must have at least 'path' or 'id' field
            if not ref.get("path") and not ref.get("id") and not ref.get("ref"):
                return {
                    "valid": False,
                    "code": EnvelopeValidationCode.INVALID_EVIDENCE_REF_ENTRY,
                    "message": f"evidence_refs[{idx}] dict missing 'path', 'id', or 'ref' field",
                    "count": len(evidence_refs),
                    "pending": False,
                }
        else:
            # Invalid type
            return {
                "valid": False,
                "code": EnvelopeValidationCode.INVALID_EVIDENCE_REF_ENTRY,
                "message": f"evidence_refs[{idx}] must be string or dict, got {type(ref).__name__}",
                "count": len(evidence_refs),
                "pending": False,
            }

    # All entries valid
    return {
        "valid": True,
        "code": EnvelopeValidationCode.VALID,
        "message": f"Evidence refs validated ({len(evidence_refs)} entries)",
        "count": len(evidence_refs),
        "pending": False,
    }


# ---------------------------------------------------------------------------
# Compute Budget Validation (WSP 97: Structural validation only)
# ---------------------------------------------------------------------------

# Allowed compute tiers (from FoundUpJob contract)
ALLOWED_COMPUTE_TIERS: frozenset[str] = frozenset({
    "freemium",
    "basic",
    "enterprise",
})

# Allowed model preferences (from FoundUpJob contract)
ALLOWED_MODEL_PREFERENCES: frozenset[str] = frozenset({
    "auto",
    "free",
    "standard",
    "premium",
})

# Tier -> allowed model preferences (conservative routing policy)
# - auto is always allowed (runtime selects based on tier)
# - freemium: free models only (no paid inference)
# - basic: free + standard models
# - enterprise: all models including premium
TIER_ALLOWED_PREFERENCES: Dict[str, frozenset[str]] = {
    "freemium": frozenset({"auto", "free"}),
    "basic": frozenset({"auto", "free", "standard"}),
    "enterprise": frozenset({"auto", "free", "standard", "premium"}),
}


def _validate_compute_budget(
    envelope: Dict[str, Any],
    is_live_mode: bool = False,
) -> Dict[str, Any]:
    """
    Validate compute budget fields for FoundUpJob envelope.

    WSP 97 Truth Boundaries:
      - Compute validation proves structural correctness only
      - Does NOT verify actual metering accuracy
      - Does NOT prove resource consumption tracking
      - Does NOT enable billing claims

    Validates:
      - compute_budget: Optional[int] (None or non-negative integer)
      - compute_used: int (non-negative integer)
      - compute_tier: str (must be in ALLOWED_COMPUTE_TIERS)
      - model_preference: str (must be in ALLOWED_MODEL_PREFERENCES)
      - compute_used <= compute_budget (when budget is set)
      - live mode requires explicit compute_budget

    Args:
        envelope: FoundUpJob envelope dict
        is_live_mode: Whether dry_run_mode=False (live execution)

    Returns:
        Dict with: valid, code, message, budget, used, tier, model_preference
    """
    # Extract fields with defaults matching FoundUpJob contract
    compute_budget = envelope.get("compute_budget")  # None = unlimited
    compute_used = envelope.get("compute_used", 0)
    compute_tier = envelope.get("compute_tier", "freemium")
    model_preference = envelope.get("model_preference", "auto")

    # === compute_budget type validation ===
    # Contract: Optional[int] - None or int only (no floats)
    if compute_budget is not None:
        if not isinstance(compute_budget, int) or isinstance(compute_budget, bool):
            return {
                "valid": False,
                "code": EnvelopeValidationCode.INVALID_COMPUTE_BUDGET_TYPE,
                "message": f"compute_budget must be int or None, got {type(compute_budget).__name__}",
                "budget": None,
                "used": compute_used if isinstance(compute_used, int) else 0,
                "tier": compute_tier,
                "model_preference": model_preference,
            }

        # Non-negative check
        if compute_budget < 0:
            return {
                "valid": False,
                "code": EnvelopeValidationCode.INVALID_COMPUTE_BUDGET_NEGATIVE,
                "message": f"compute_budget must be non-negative, got {compute_budget}",
                "budget": compute_budget,
                "used": compute_used if isinstance(compute_used, int) else 0,
                "tier": compute_tier,
                "model_preference": model_preference,
            }

    # === compute_used type validation ===
    # Contract: int only (no floats)
    if not isinstance(compute_used, int) or isinstance(compute_used, bool):
        return {
            "valid": False,
            "code": EnvelopeValidationCode.INVALID_COMPUTE_USED_TYPE,
            "message": f"compute_used must be int, got {type(compute_used).__name__}",
            "budget": compute_budget,
            "used": 0,
            "tier": compute_tier,
            "model_preference": model_preference,
        }

    # Non-negative check
    if compute_used < 0:
        return {
            "valid": False,
            "code": EnvelopeValidationCode.INVALID_COMPUTE_USED_NEGATIVE,
            "message": f"compute_used must be non-negative, got {compute_used}",
            "budget": compute_budget,
            "used": compute_used,
            "tier": compute_tier,
            "model_preference": model_preference,
        }

    # === Budget exhaustion check ===
    if compute_budget is not None and compute_used > compute_budget:
        return {
            "valid": False,
            "code": EnvelopeValidationCode.COMPUTE_USED_EXCEEDS_BUDGET,
            "message": f"compute_used ({compute_used}) exceeds compute_budget ({compute_budget})",
            "budget": compute_budget,
            "used": compute_used,
            "tier": compute_tier,
            "model_preference": model_preference,
        }

    # === Live mode requires explicit budget ===
    if is_live_mode and compute_budget is None:
        return {
            "valid": False,
            "code": EnvelopeValidationCode.LIVE_MODE_REQUIRES_COMPUTE_BUDGET,
            "message": "Live mode requires explicit compute_budget",
            "budget": None,
            "used": compute_used,
            "tier": compute_tier,
            "model_preference": model_preference,
        }

    # === compute_tier validation ===
    if compute_tier not in ALLOWED_COMPUTE_TIERS:
        return {
            "valid": False,
            "code": EnvelopeValidationCode.INVALID_COMPUTE_TIER,
            "message": f"compute_tier must be one of {sorted(ALLOWED_COMPUTE_TIERS)}, got '{compute_tier}'",
            "budget": compute_budget,
            "used": compute_used,
            "tier": compute_tier,
            "model_preference": model_preference,
        }

    # === model_preference validation ===
    if model_preference not in ALLOWED_MODEL_PREFERENCES:
        return {
            "valid": False,
            "code": EnvelopeValidationCode.INVALID_MODEL_PREFERENCE,
            "message": f"model_preference must be one of {sorted(ALLOWED_MODEL_PREFERENCES)}, got '{model_preference}'",
            "budget": compute_budget,
            "used": compute_used,
            "tier": compute_tier,
            "model_preference": model_preference,
            "routing_policy_validated": False,
            "routing_policy_reason": "model_preference validation failed",
        }

    # === Tier/preference compatibility check ===
    allowed_for_tier = TIER_ALLOWED_PREFERENCES.get(compute_tier, frozenset())
    if model_preference not in allowed_for_tier:
        return {
            "valid": False,
            "code": EnvelopeValidationCode.MODEL_PREFERENCE_NOT_ALLOWED_FOR_TIER,
            "message": f"model_preference '{model_preference}' not allowed for compute_tier '{compute_tier}' (allowed: {sorted(allowed_for_tier)})",
            "budget": compute_budget,
            "used": compute_used,
            "tier": compute_tier,
            "model_preference": model_preference,
            "routing_policy_validated": False,
            "routing_policy_reason": f"tier '{compute_tier}' does not allow preference '{model_preference}'",
        }

    # All checks passed
    routing_reason = f"tier '{compute_tier}' allows preference '{model_preference}'"
    return {
        "valid": True,
        "code": EnvelopeValidationCode.VALID,
        "message": "Compute budget validated",
        "budget": compute_budget,
        "used": compute_used,
        "tier": compute_tier,
        "model_preference": model_preference,
        "routing_policy_validated": True,
        "routing_policy_reason": routing_reason,
    }


# ---------------------------------------------------------------------------
# Route Envelope
# ---------------------------------------------------------------------------


@dataclass
class RouteEnvelope:
    """
    WRE routing decision envelope.

    Contains all information needed to dispatch a FoundUpJob to its
    target backend, or to explain why routing was blocked/failed.
    """

    # === Job Identity (copied from FoundUpJob) ===
    job_id: str
    """Job identifier from source FoundUpJob."""

    tenant_id: str
    """Tenant/actor scope from source FoundUpJob."""

    # === Routing Decision ===
    target_backend: TargetBackend
    """Backend to dispatch job to. NONE if blocked/failed/unsupported."""

    requested_action: str
    """Action being routed."""

    route_status: RouteStatus
    """Routing decision status."""

    # === Reason/Evidence ===
    reason_code: RouteReasonCode
    """Machine-readable reason for routing decision."""

    reason_human: str
    """Operator-readable explanation."""

    evidence_refs: List[str] = field(default_factory=list)
    """Evidence paths/IDs supporting the routing decision."""

    # === Policy Summary ===
    policy_summary: Dict[str, bool] = field(default_factory=dict)
    """Snapshot of policy flags at routing time."""

    # === Timestamps ===
    routed_at: datetime = field(default_factory=utc_now)
    """Timestamp when routing decision was made."""

    # === Source Job State ===
    source_job_status: str = ""
    """Status of the source FoundUpJob at routing time."""

    foundup_id: Optional[str] = None
    """Target FoundUp ID from source job (if present)."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON/logging."""
        return {
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "target_backend": self.target_backend.value,
            "requested_action": self.requested_action,
            "route_status": self.route_status.value,
            "reason_code": self.reason_code.value,
            "reason_human": self.reason_human,
            "evidence_refs": self.evidence_refs,
            "policy_summary": self.policy_summary,
            "routed_at": self.routed_at.isoformat(),
            "source_job_status": self.source_job_status,
            "foundup_id": self.foundup_id,
        }


# ---------------------------------------------------------------------------
# Router Implementation
# ---------------------------------------------------------------------------


def route_foundup_job(job: Any) -> RouteEnvelope:
    """
    Route a FoundUpJob to the appropriate execution backend.

    This is the Phase 1 routing seam. It validates the job, determines
    the target backend, and returns a RouteEnvelope. It does NOT execute
    the job — that's for Hermes/FAM adapters.

    Args:
        job: FoundUpJob instance (or duck-typed object with same fields)

    Returns:
        RouteEnvelope with routing decision

    Raises:
        Nothing — returns failed/blocked envelope on errors
    """
    try:
        # === Identity Validation ===
        job_id = getattr(job, "job_id", None)
        if not job_id or not str(job_id).strip():
            return _make_blocked_envelope(
                job_id="",
                tenant_id=getattr(job, "tenant_id", "") or "",
                action=getattr(job, "requested_action", "") or "",
                reason_code=RouteReasonCode.BLOCKED_MISSING_JOB_ID,
                reason_human="Job ID is required for routing",
            )

        tenant_id = getattr(job, "tenant_id", None)
        if not tenant_id or not str(tenant_id).strip():
            return _make_blocked_envelope(
                job_id=job_id,
                tenant_id="",
                action=getattr(job, "requested_action", "") or "",
                reason_code=RouteReasonCode.BLOCKED_MISSING_TENANT_ID,
                reason_human="Tenant ID is required for routing",
            )

        # === Action Validation ===
        requested_action = getattr(job, "requested_action", None)
        if not requested_action or not str(requested_action).strip():
            return _make_blocked_envelope(
                job_id=job_id,
                tenant_id=tenant_id,
                action="",
                reason_code=RouteReasonCode.BLOCKED_MISSING_ACTION,
                reason_human="Requested action is required for routing",
            )

        # === Terminal Status Check ===
        job_status = getattr(job, "status", None)
        status_str = job_status.value if hasattr(job_status, "value") else str(job_status or "")

        # Check for terminal status (import here to avoid circular deps)
        try:
            from modules.communication.moltbot_bridge.src.foundup_job_contract import (
                is_terminal_status,
                JobStatus,
            )
            if job_status and is_terminal_status(job_status):
                return _make_blocked_envelope(
                    job_id=job_id,
                    tenant_id=tenant_id,
                    action=requested_action,
                    reason_code=RouteReasonCode.BLOCKED_TERMINAL_STATUS,
                    reason_human=f"Job is in terminal status: {status_str}",
                    source_status=status_str,
                    foundup_id=getattr(job, "foundup_id", None),
                )
        except ImportError:
            # If contract not available, assume non-terminal
            pass

        # === Policy Check ===
        policy_flags = getattr(job, "policy_flags", None)
        policy_summary: Dict[str, bool] = {}
        if policy_flags:
            if hasattr(policy_flags, "to_dict"):
                policy_summary = policy_flags.to_dict()
            elif isinstance(policy_flags, dict):
                policy_summary = policy_flags

            # Check for blocking policy state
            if policy_summary.get("security_gate_checked") and not policy_summary.get("security_gate_passed"):
                return _make_blocked_envelope(
                    job_id=job_id,
                    tenant_id=tenant_id,
                    action=requested_action,
                    reason_code=RouteReasonCode.BLOCKED_POLICY_GATE,
                    reason_human="Security gate check failed",
                    source_status=status_str,
                    foundup_id=getattr(job, "foundup_id", None),
                    policy_summary=policy_summary,
                )

        # === Route to Backend ===
        target_backend = _ACTION_BACKEND_MAP.get(requested_action)

        if target_backend is None:
            return RouteEnvelope(
                job_id=job_id,
                tenant_id=tenant_id,
                target_backend=TargetBackend.NONE,
                requested_action=requested_action,
                route_status=RouteStatus.UNSUPPORTED,
                reason_code=RouteReasonCode.UNSUPPORTED_ACTION,
                reason_human=f"Action '{requested_action}' is not supported",
                policy_summary=policy_summary,
                source_job_status=status_str,
                foundup_id=getattr(job, "foundup_id", None),
            )

        # === Queue Action Special Case ===
        if requested_action == "queue_foundup_job":
            return RouteEnvelope(
                job_id=job_id,
                tenant_id=tenant_id,
                target_backend=TargetBackend.OPENCLAW_QUEUE,
                requested_action=requested_action,
                route_status=RouteStatus.QUEUED,
                reason_code=RouteReasonCode.OK_QUEUED,
                reason_human="Job queued for later processing",
                policy_summary=policy_summary,
                source_job_status=status_str,
                foundup_id=getattr(job, "foundup_id", None),
            )

        # === Success ===
        return RouteEnvelope(
            job_id=job_id,
            tenant_id=tenant_id,
            target_backend=target_backend,
            requested_action=requested_action,
            route_status=RouteStatus.ROUTED,
            reason_code=RouteReasonCode.OK_ROUTED,
            reason_human=f"Job routed to {target_backend.value}",
            policy_summary=policy_summary,
            source_job_status=status_str,
            foundup_id=getattr(job, "foundup_id", None),
        )

    except Exception as e:
        logger.exception(f"Routing failed: {e}")
        return RouteEnvelope(
            job_id=getattr(job, "job_id", "") or "",
            tenant_id=getattr(job, "tenant_id", "") or "",
            target_backend=TargetBackend.NONE,
            requested_action=getattr(job, "requested_action", "") or "",
            route_status=RouteStatus.FAILED,
            reason_code=RouteReasonCode.FAIL_INTERNAL,
            reason_human=f"Internal routing error: {str(e)}",
        )


def _make_blocked_envelope(
    job_id: str,
    tenant_id: str,
    action: str,
    reason_code: RouteReasonCode,
    reason_human: str,
    source_status: str = "",
    foundup_id: Optional[str] = None,
    policy_summary: Optional[Dict[str, bool]] = None,
) -> RouteEnvelope:
    """Helper to construct blocked/failed envelopes."""
    return RouteEnvelope(
        job_id=job_id,
        tenant_id=tenant_id,
        target_backend=TargetBackend.NONE,
        requested_action=action,
        route_status=RouteStatus.BLOCKED,
        reason_code=reason_code,
        reason_human=reason_human,
        policy_summary=policy_summary or {},
        source_job_status=source_status,
        foundup_id=foundup_id,
    )


# ---------------------------------------------------------------------------
# Route Mapping (for inspection/documentation)
# ---------------------------------------------------------------------------


def get_action_route_map() -> Dict[str, str]:
    """Return the action -> backend mapping for documentation/inspection."""
    return {k: v.value for k, v in _ACTION_BACKEND_MAP.items()}
