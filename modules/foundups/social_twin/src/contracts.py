"""Core contracts for the Social Twin FoundUp."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class SocialTwinRole(str, Enum):
    ORCHESTRATOR = "orchestrator_0102"
    ENGAGER = "engager_0102"
    AMPLIFIER = "amplifier_0102"


class QueueStatus(str, Enum):
    SCANNED = "scanned"
    RANKED = "ranked"
    QUEUED = "queued"
    DISCUSSED = "discussed"
    DRAFTED = "drafted"
    APPROVED = "approved"
    EXECUTING = "executing"
    EXECUTED = "executed"
    AMPLIFIED = "amplified"
    FOLLOWUP_SCHEDULED = "followup_scheduled"
    CLOSED = "closed"
    REJECTED = "rejected"
    FAILED = "failed"


class ReviewAction(str, Enum):
    NEXT = "next"
    SKIP = "skip"
    REWRITE = "rewrite"
    APPROVE = "approve"
    REPLY_AS = "reply_as"
    FOLLOWUP_5D = "followup_5d"
    FOLLOWUP_7D = "followup_7d"
    ESCALATE_TO_ARTICLE = "escalate_to_article"


@dataclass(frozen=True)
class RoleAssignment:
    role: SocialTwinRole
    runtime: str
    model_policy: str
    mutation_allowed: bool


@dataclass
class OpportunityCandidate:
    platform: str
    source_post_id: str
    author: str
    source_url: str
    source_text: str
    alignment_keys: List[str] = field(default_factory=list)
    score: float = 0.0
    ranking_reasons: List[str] = field(default_factory=list)
    recommended_voice: str = "0102"
    recommended_entity: Optional[str] = None
    status: QueueStatus = QueueStatus.SCANNED


@dataclass
class MorningReviewPacket:
    queue_id: str
    reviewer_channel: str
    items: List[OpportunityCandidate] = field(default_factory=list)


@dataclass(frozen=True)
class SocialTwinTopology:
    foundup_id: str
    orchestrator: RoleAssignment
    engager: RoleAssignment
    amplifier: Optional[RoleAssignment] = None
    approval_required: bool = True


def default_social_twin_topology(foundup_id: str = "social_twin") -> SocialTwinTopology:
    """Return the default control-plane/action-plane split."""
    return SocialTwinTopology(
        foundup_id=foundup_id,
        orchestrator=RoleAssignment(
            role=SocialTwinRole.ORCHESTRATOR,
            runtime="openclaw_qwen_control_plane",
            model_policy="local_first_reasoning",
            mutation_allowed=False,
        ),
        engager=RoleAssignment(
            role=SocialTwinRole.ENGAGER,
            runtime="local_browser_execution_plane",
            model_policy="deterministic_first",
            mutation_allowed=True,
        ),
        amplifier=None,
        approval_required=True,
    )
