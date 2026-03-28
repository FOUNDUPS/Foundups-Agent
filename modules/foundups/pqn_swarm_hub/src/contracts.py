#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PQN Swarm Hub FoundUp - PoC Contracts

Dataclass contracts for the PQN Swarm Hub work registry, submission sink,
verification, and contribution measurement.

WSP Compliance:
  WSP 11  : Interface contract definitions
  WSP 72  : Module independence (no circular deps)
  WSP 84  : Code Reuse (deterministic ID pattern from moltbook_distribution_adapter)

NAVIGATION:
  -> Interface: modules/foundups/pqn_swarm_hub/INTERFACE.md
  -> Reuses: modules/ai_intelligence/pqn_alignment (detector)
  -> Reuses: modules/communication/moltbot_bridge/src/moltbook_distribution_adapter.py
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def generate_id(entity_type: str, *args: str) -> str:
    """
    Generate deterministic ID for idempotency.

    Pattern reused from moltbook_distribution_adapter (WSP 84).
    """
    seed = f"{entity_type}:{':'.join(str(a) for a in args)}"
    return hashlib.sha256(seed.encode()).hexdigest()[:16]


# --- Enums ---


class WorkUnitStatus(str, Enum):
    """Status of a PQN work unit."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SubmissionStatus(str, Enum):
    """Status of an rESP submission."""

    PENDING_VERIFICATION = "pending_verification"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


# --- PoC Contracts ---


@dataclass
class PQNWorkUnit:
    """
    Bounded research task registration.

    Represents a single PQN detection work unit that can be assigned,
    executed, and verified.
    """

    description: str
    config: Dict[str, Any]
    creator_id: str
    work_unit_id: str = field(default="")
    status: WorkUnitStatus = WorkUnitStatus.PENDING
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        if not self.work_unit_id:
            self.work_unit_id = generate_id(
                "work_unit",
                self.description[:50],
                self.creator_id,
                self.created_at.isoformat(),
            )


@dataclass
class rESPSubmission:
    """
    Structured rESP result intake.

    Represents a submission of detection results for a work unit.
    """

    work_unit_id: str
    submitter_id: str
    metrics: Dict[str, Any]
    artifacts: List[str] = field(default_factory=list)
    submission_id: str = field(default="")
    status: SubmissionStatus = SubmissionStatus.PENDING_VERIFICATION
    submitted_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        if not self.submission_id:
            self.submission_id = generate_id(
                "submission",
                self.work_unit_id,
                self.submitter_id,
                self.submitted_at.isoformat(),
            )


@dataclass
class VerificationDecision:
    """
    Accept/reject outcome.

    Records the verification decision for a submission.
    """

    submission_id: str
    decision: Literal["accept", "reject"]
    verifier_id: str
    rationale: str = ""
    decision_id: str = field(default="")
    decided_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        if not self.decision_id:
            self.decision_id = generate_id(
                "decision",
                self.submission_id,
                self.verifier_id,
                self.decided_at.isoformat(),
            )


@dataclass
class ContributionRecord:
    """
    ROC-style contribution output.

    Records the contribution score for verified work.
    """

    work_unit_id: str
    submission_id: str
    decision_id: str
    contributor_id: str
    score: float
    contribution_id: str = field(default="")
    recorded_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        if not self.contribution_id:
            self.contribution_id = generate_id(
                "contribution",
                self.work_unit_id,
                self.submission_id,
                self.decision_id,
                self.contributor_id,
            )
        # Clamp score to valid range
        self.score = max(0.0, min(1.0, self.score))
