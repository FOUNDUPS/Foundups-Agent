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
from typing import Any, Dict, List, Optional

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
