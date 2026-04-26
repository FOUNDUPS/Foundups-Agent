#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verification Gap Guard — Policy Enforcement for Protected Decisions

Enforces the VerificationGapGuard contract: AI systems may surface anomaly
signals but cannot be the sole judge for protected decision classes.

Canonical Rule: AI surfaces. Humans decide. The gap is guarded.

WSP 97 TRUTH BOUNDARIES:
  DOES:
    - Define protected decision classes
    - Block AI agents from executing protected actions
    - Require human review for protected decisions
    - Preserve evidence references
    - Track source (server-side vs browser/local AI)
    - Return truthful BlockedActionResult with reason

  DOES NOT:
    - Implement fraud detection algorithms
    - Implement legal/reputation judgment logic
    - Implement reward denial mechanics
    - Implement payout/wallet actions
    - Run pAVS/CABR consensus
    - Mark cabr_ready, payout_ready, or verification_complete as final
    - Implement browser Gemma (advisory signals only from that source)

Contract Reference:
  modules/foundups/docs/VERIFICATION_GAP_GUARD_CONTRACT.md

WSP Compliance:
  WSP 11  : Interface contract (typed API)
  WSP 97  : System Execution Prompting (truth boundaries)
  WSP 91  : Observability (timestamps, audit fields)
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Union

logger = logging.getLogger("verification_gap_guard")


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Protected Decision Classes
# ---------------------------------------------------------------------------


class ProtectedClass(str, Enum):
    """
    Protected decision classes that require human review.

    No AI agent (server-side or client-side) may unilaterally execute
    decisions in these classes.
    """

    FRAUD_ACCUSATION = "fraud_accusation"
    """Labeling a participant or FoundUp as fraudulent."""

    SCAM_ACCUSATION = "scam_accusation"
    """Labeling content or behavior as a scam."""

    DEEPFAKE_ACCUSATION = "deepfake_accusation"
    """Labeling media as synthetically manipulated."""

    REWARD_DENIAL = "reward_denial"
    """Blocking or denying earned rewards/payouts."""

    REPUTATION_IMPACT = "reputation_impact"
    """Publishing negative reputation to trust ledger."""

    LEGAL_EXPOSURE = "legal_exposure"
    """Decisions that create legal liability."""

    IDENTITY_RISK = "identity_risk"
    """Decisions affecting identity/account status."""

    TRUST_LEDGER_PUBLICATION = "trust_ledger_publication"
    """Writing to Public Trust Ledger."""

    WALLET_ACTION = "wallet_action"
    """Token transfers, staking, payout execution."""

    PAYOUT_FINALITY = "payout_finality"
    """Marking payout as final/irreversible."""


# ---------------------------------------------------------------------------
# Anomaly Types
# ---------------------------------------------------------------------------


class AnomalyType(str, Enum):
    """Types of anomalies that can be surfaced by AI agents."""

    PATTERN_MISMATCH = "pattern_mismatch"
    """Detected pattern does not match expected behavior."""

    CONFIDENCE_BELOW_THRESHOLD = "confidence_below_threshold"
    """AI confidence score below required threshold."""

    DUPLICATE_SUBMISSION = "duplicate_submission"
    """Submission appears to be a duplicate."""

    VELOCITY_ANOMALY = "velocity_anomaly"
    """Unusual rate of activity detected."""

    CONTENT_FLAG = "content_flag"
    """Content flagged by automated filter."""

    IDENTITY_MISMATCH = "identity_mismatch"
    """Identity claims do not match evidence."""

    EVIDENCE_INCOMPLETE = "evidence_incomplete"
    """Required evidence is missing or incomplete."""

    EXTERNAL_REPORT = "external_report"
    """External party reported an issue."""


# ---------------------------------------------------------------------------
# Agent Actions
# ---------------------------------------------------------------------------


class AgentAction(str, Enum):
    """Actions that AI agents may attempt to perform."""

    # Allowed actions (advisory, non-final)
    SURFACE_ANOMALY = "surface_anomaly"
    SUMMARIZE_EVIDENCE = "summarize_evidence"
    OPEN_PANEL = "open_panel"
    REQUEST_REVIEW = "request_review"
    COMPUTE_CONFIDENCE = "compute_confidence"
    LOG_AUDIT = "log_audit"
    NOTIFY_REDDOG = "notify_reddog"

    # Blocked actions (protected decision classes)
    DENY_REWARD = "deny_reward"
    PUBLISH_ACCUSATION = "publish_accusation"
    WRITE_TRUST_LEDGER = "write_trust_ledger"
    EXECUTE_PAYOUT = "execute_payout"
    FINALIZE_REPUTATION = "finalize_reputation"
    TRIGGER_LEGAL = "trigger_legal"
    SUSPEND_IDENTITY = "suspend_identity"


# Immutable sets for fast lookup
ALLOWED_ACTIONS: frozenset[AgentAction] = frozenset({
    AgentAction.SURFACE_ANOMALY,
    AgentAction.SUMMARIZE_EVIDENCE,
    AgentAction.OPEN_PANEL,
    AgentAction.REQUEST_REVIEW,
    AgentAction.COMPUTE_CONFIDENCE,
    AgentAction.LOG_AUDIT,
    AgentAction.NOTIFY_REDDOG,
})

BLOCKED_ACTIONS: frozenset[AgentAction] = frozenset({
    AgentAction.DENY_REWARD,
    AgentAction.PUBLISH_ACCUSATION,
    AgentAction.WRITE_TRUST_LEDGER,
    AgentAction.EXECUTE_PAYOUT,
    AgentAction.FINALIZE_REPUTATION,
    AgentAction.TRIGGER_LEGAL,
    AgentAction.SUSPEND_IDENTITY,
})

# Browser/local AI sources (advisory only)
LOCAL_AI_SOURCES: frozenset[str] = frozenset({
    "local_gemma",
    "browser_gemma",
    "webgpu_gemma",
    "on_device",
    "local_model",
})


# ---------------------------------------------------------------------------
# Verification Gap Event
# ---------------------------------------------------------------------------


@dataclass
class VerificationGapEvent:
    """
    Event capturing an anomaly that requires human review.

    WSP 97: This event surfaces anomalies. It does NOT make decisions.
    The human_decision fields remain None until a human reviewer acts.
    """

    # Identity
    foundup_id: str
    tenant_id: str
    anomaly_type: AnomalyType
    risk_class: ProtectedClass

    # Source
    source_panel: str = "agent_surface"
    source_agent: Optional[str] = None

    # Confidence (advisory only)
    confidence: float = 0.0

    # Evidence
    evidence_refs: List[str] = field(default_factory=list)
    evidence_summary: Optional[str] = None

    # Review gate - always true for protected classes
    requires_human_review: bool = True

    # Human decision fields - None until human acts
    human_reviewer_id: Optional[str] = None
    human_decision: Optional[str] = None  # "approved" | "rejected" | "escalated"
    human_decision_at: Optional[datetime] = None
    human_decision_reason: Optional[str] = None

    # Agent boundary fields
    allowed_agent_actions: List[AgentAction] = field(default_factory=list)
    blocked_agent_actions: List[AgentAction] = field(default_factory=list)

    # Audit
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    # Generated ID
    event_id: str = field(default="")

    def __post_init__(self) -> None:
        """Generate deterministic event_id and set agent action boundaries."""
        if not self.event_id:
            self.event_id = self._generate_event_id()

        # Set allowed/blocked actions based on contract
        if not self.allowed_agent_actions:
            self.allowed_agent_actions = list(ALLOWED_ACTIONS)
        if not self.blocked_agent_actions:
            self.blocked_agent_actions = list(BLOCKED_ACTIONS)

        # Protected classes always require human review
        if self.risk_class in ProtectedClass:
            self.requires_human_review = True

    def _generate_event_id(self) -> str:
        """Generate deterministic event ID from identity fields."""
        seed = f"{self.foundup_id}:{self.tenant_id}:{self.anomaly_type.value}:{_utc_iso(self.created_at)}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    def is_from_local_ai(self) -> bool:
        """Check if this event originated from browser/local AI."""
        return self.source_panel in LOCAL_AI_SOURCES

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON/API transport."""
        return {
            "event_id": self.event_id,
            "foundup_id": self.foundup_id,
            "tenant_id": self.tenant_id,
            "source_panel": self.source_panel,
            "source_agent": self.source_agent,
            "anomaly_type": self.anomaly_type.value,
            "risk_class": self.risk_class.value,
            "confidence": self.confidence,
            "evidence_refs": self.evidence_refs,
            "evidence_summary": self.evidence_summary,
            "requires_human_review": self.requires_human_review,
            "human_reviewer_id": self.human_reviewer_id,
            "human_decision": self.human_decision,
            "human_decision_at": _utc_iso(self.human_decision_at),
            "human_decision_reason": self.human_decision_reason,
            "allowed_agent_actions": [a.value for a in self.allowed_agent_actions],
            "blocked_agent_actions": [a.value for a in self.blocked_agent_actions],
            "created_at": _utc_iso(self.created_at),
            "updated_at": _utc_iso(self.updated_at),
        }


# ---------------------------------------------------------------------------
# Blocked Action Result
# ---------------------------------------------------------------------------


@dataclass
class BlockedActionResult:
    """
    Result returned when an AI agent attempts a blocked action.

    WSP 97: reason_human explains truthfully why the action was blocked.
    """

    blocked: bool
    action: AgentAction
    reason_code: str
    reason_human: str
    event_id: Optional[str] = None
    requires_human_review: bool = True
    suggested_action: str = "request_review"

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "blocked": self.blocked,
            "action": self.action.value if isinstance(self.action, AgentAction) else self.action,
            "reason_code": self.reason_code,
            "reason_human": self.reason_human,
            "event_id": self.event_id,
            "requires_human_review": self.requires_human_review,
            "suggested_action": self.suggested_action,
        }


# ---------------------------------------------------------------------------
# Guard Functions
# ---------------------------------------------------------------------------


def is_protected_action(action: Union[AgentAction, str]) -> bool:
    """
    Check if an action is protected (requires human review).

    Args:
        action: AgentAction enum or string action name.

    Returns:
        True if the action is in the blocked/protected set.
    """
    if isinstance(action, str):
        try:
            action = AgentAction(action)
        except ValueError:
            # Unknown action - treat as potentially protected
            return True

    return action in BLOCKED_ACTIONS


def requires_human_review(event: VerificationGapEvent) -> bool:
    """
    Check if an event requires human review.

    Args:
        event: The VerificationGapEvent to check.

    Returns:
        True if the event requires human review before any protected
        decision can be made.

    WSP 97: Protected classes ALWAYS require human review.
    Local AI sources are advisory only and cannot bypass this.
    """
    # Protected classes always require review
    if event.risk_class in ProtectedClass:
        return True

    # Local AI sources are advisory only
    if event.is_from_local_ai():
        return True

    # Explicit flag
    return event.requires_human_review


def block_protected_action(
    event: VerificationGapEvent,
    action: Union[AgentAction, str],
) -> BlockedActionResult:
    """
    Attempt to perform an action and return blocked result if protected.

    Args:
        event: The VerificationGapEvent context.
        action: The action the AI agent is attempting.

    Returns:
        BlockedActionResult indicating whether the action was blocked
        and why.

    WSP 97: This function NEVER executes protected actions. It only
    reports whether they would be blocked.
    """
    # Normalize action to enum
    if isinstance(action, str):
        try:
            action_enum = AgentAction(action)
        except ValueError:
            # Unknown action - block it
            return BlockedActionResult(
                blocked=True,
                action=AgentAction.DENY_REWARD,  # Placeholder for unknown
                reason_code="UNKNOWN_ACTION",
                reason_human=f"Unknown action '{action}' is not permitted. Only known allowed actions may proceed.",
                event_id=event.event_id,
                requires_human_review=True,
            )
    else:
        action_enum = action

    # Check if action is allowed
    if action_enum in ALLOWED_ACTIONS:
        return BlockedActionResult(
            blocked=False,
            action=action_enum,
            reason_code="ACTION_ALLOWED",
            reason_human=f"Action '{action_enum.value}' is permitted for AI agents.",
            event_id=event.event_id,
            requires_human_review=event.requires_human_review,
            suggested_action=action_enum.value,
        )

    # Action is blocked - determine reason
    if event.is_from_local_ai():
        reason_code = "LOCAL_AI_ADVISORY_ONLY"
        reason_human = (
            f"Action '{action_enum.value}' blocked: Browser/local AI signals are advisory only. "
            f"Local models cannot perform protected decisions. Route to human review."
        )
    elif event.risk_class in ProtectedClass:
        reason_code = f"PROTECTED_CLASS_{event.risk_class.value.upper()}"
        reason_human = (
            f"Action '{action_enum.value}' blocked: This action falls under protected class "
            f"'{event.risk_class.value}'. AI agents cannot make this decision unilaterally. "
            f"Human review is required before finalization."
        )
    else:
        reason_code = "ACTION_BLOCKED"
        reason_human = (
            f"Action '{action_enum.value}' is blocked for AI agents. "
            f"Only allowed actions may proceed without human review."
        )

    logger.info(
        "Blocked protected action: action=%s, event_id=%s, reason=%s",
        action_enum.value,
        event.event_id,
        reason_code,
    )

    return BlockedActionResult(
        blocked=True,
        action=action_enum,
        reason_code=reason_code,
        reason_human=reason_human,
        event_id=event.event_id,
        requires_human_review=True,
        suggested_action="request_review",
    )


# ---------------------------------------------------------------------------
# Convenience API
# ---------------------------------------------------------------------------


def create_gap_event(
    foundup_id: str,
    tenant_id: str,
    anomaly_type: Union[AnomalyType, str],
    risk_class: Union[ProtectedClass, str],
    source_panel: str = "agent_surface",
    confidence: float = 0.0,
    evidence_refs: Optional[List[str]] = None,
    evidence_summary: Optional[str] = None,
) -> VerificationGapEvent:
    """
    Factory function to create a VerificationGapEvent.

    WSP 97: This function creates the event structure. It does NOT
    make any decisions or claims about the anomaly.
    """
    # Normalize enums
    if isinstance(anomaly_type, str):
        anomaly_type = AnomalyType(anomaly_type)
    if isinstance(risk_class, str):
        risk_class = ProtectedClass(risk_class)

    return VerificationGapEvent(
        foundup_id=foundup_id,
        tenant_id=tenant_id,
        anomaly_type=anomaly_type,
        risk_class=risk_class,
        source_panel=source_panel,
        confidence=confidence,
        evidence_refs=evidence_refs or [],
        evidence_summary=evidence_summary,
    )
