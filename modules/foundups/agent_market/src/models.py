"""Core schemas for FoundUps Agent Market."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .exceptions import ValidationError


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")


class TaskStatus(str, Enum):
    OPEN = "open"
    CLAIMED = "claimed"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    PAID = "paid"


class PayoutStatus(str, Enum):
    INITIATED = "initiated"
    COMPLETED = "completed"


@dataclass(slots=True)
class Foundup:
    foundup_id: str
    name: str
    owner_id: str
    token_symbol: str
    immutable_metadata: Dict[str, str] = field(default_factory=dict)
    mutable_metadata: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty(self.foundup_id, "foundup_id")
        _require_non_empty(self.name, "name")
        _require_non_empty(self.owner_id, "owner_id")
        _require_non_empty(self.token_symbol, "token_symbol")


@dataclass(slots=True)
class TokenTerms:
    token_name: str
    token_symbol: str
    max_supply: int
    treasury_account: str
    vesting_policy: Dict[str, str] = field(default_factory=dict)
    chain_hint: Optional[str] = None

    def __post_init__(self) -> None:
        _require_non_empty(self.token_name, "token_name")
        _require_non_empty(self.token_symbol, "token_symbol")
        _require_non_empty(self.treasury_account, "treasury_account")
        if not isinstance(self.max_supply, int) or self.max_supply <= 0:
            raise ValidationError("max_supply must be a positive integer")


@dataclass(slots=True)
class AgentProfile:
    agent_id: str
    display_name: str
    capability_tags: List[str]
    role: str
    joined_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty(self.agent_id, "agent_id")
        _require_non_empty(self.display_name, "display_name")
        _require_non_empty(self.role, "role")
        if not isinstance(self.capability_tags, list):
            raise ValidationError("capability_tags must be a list")


@dataclass(slots=True)
class Task:
    task_id: str
    foundup_id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    reward_amount: int
    creator_id: str
    status: TaskStatus = TaskStatus.OPEN
    assignee_id: Optional[str] = None
    proof_id: Optional[str] = None
    verification_id: Optional[str] = None
    payout_id: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty(self.task_id, "task_id")
        _require_non_empty(self.foundup_id, "foundup_id")
        _require_non_empty(self.title, "title")
        _require_non_empty(self.description, "description")
        _require_non_empty(self.creator_id, "creator_id")
        if not isinstance(self.acceptance_criteria, list) or not self.acceptance_criteria:
            raise ValidationError("acceptance_criteria must be a non-empty list")
        if not isinstance(self.reward_amount, int) or self.reward_amount <= 0:
            raise ValidationError("reward_amount must be a positive integer")


@dataclass(slots=True)
class Proof:
    proof_id: str
    task_id: str
    submitter_id: str
    artifact_uri: str
    artifact_hash: str
    notes: str = ""
    submitted_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty(self.proof_id, "proof_id")
        _require_non_empty(self.task_id, "task_id")
        _require_non_empty(self.submitter_id, "submitter_id")
        _require_non_empty(self.artifact_uri, "artifact_uri")
        _require_non_empty(self.artifact_hash, "artifact_hash")


@dataclass(slots=True)
class Verification:
    verification_id: str
    task_id: str
    verifier_id: str
    approved: bool
    reason: str
    verified_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty(self.verification_id, "verification_id")
        _require_non_empty(self.task_id, "task_id")
        _require_non_empty(self.verifier_id, "verifier_id")
        _require_non_empty(self.reason, "reason")
        if not isinstance(self.approved, bool):
            raise ValidationError("approved must be bool")


@dataclass(slots=True)
class Payout:
    payout_id: str
    task_id: str
    recipient_id: str
    amount: int
    status: PayoutStatus = PayoutStatus.INITIATED
    reference: Optional[str] = None
    paid_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        _require_non_empty(self.payout_id, "payout_id")
        _require_non_empty(self.task_id, "task_id")
        _require_non_empty(self.recipient_id, "recipient_id")
        if not isinstance(self.amount, int) or self.amount <= 0:
            raise ValidationError("amount must be a positive integer")


@dataclass(slots=True)
class DistributionPost:
    distribution_id: str
    foundup_id: str
    task_id: str
    channel: str
    content: str
    actor_id: str
    dedupe_key: str
    external_ref: Optional[str] = None
    published_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty(self.distribution_id, "distribution_id")
        _require_non_empty(self.foundup_id, "foundup_id")
        _require_non_empty(self.task_id, "task_id")
        _require_non_empty(self.channel, "channel")
        _require_non_empty(self.content, "content")
        _require_non_empty(self.actor_id, "actor_id")
        _require_non_empty(self.dedupe_key, "dedupe_key")


@dataclass(slots=True)
class EventRecord:
    event_id: str
    event_type: str
    actor_id: str
    payload: Dict[str, Any]
    foundup_id: Optional[str] = None
    task_id: Optional[str] = None
    proof_id: Optional[str] = None
    payout_id: Optional[str] = None
    timestamp: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty(self.event_id, "event_id")
        _require_non_empty(self.event_type, "event_type")
        _require_non_empty(self.actor_id, "actor_id")
        if not isinstance(self.payload, dict):
            raise ValidationError("payload must be a dict")


@dataclass(slots=True)
class ComputePlan:
    plan_id: str
    actor_id: str
    tier: str
    status: str
    monthly_credit_allocation: int = 0
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty(self.plan_id, "plan_id")
        _require_non_empty(self.actor_id, "actor_id")
        _require_non_empty(self.tier, "tier")
        _require_non_empty(self.status, "status")
        if not isinstance(self.monthly_credit_allocation, int) or self.monthly_credit_allocation < 0:
            raise ValidationError("monthly_credit_allocation must be non-negative integer")


@dataclass(slots=True)
class ComputeWallet:
    wallet_id: str
    actor_id: str
    credit_balance: int = 0
    reserved_credits: int = 0
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty(self.wallet_id, "wallet_id")
        _require_non_empty(self.actor_id, "actor_id")
        if not isinstance(self.credit_balance, int) or self.credit_balance < 0:
            raise ValidationError("credit_balance must be non-negative integer")
        if not isinstance(self.reserved_credits, int) or self.reserved_credits < 0:
            raise ValidationError("reserved_credits must be non-negative integer")


@dataclass(slots=True)
class ComputeLedgerEntry:
    entry_id: str
    actor_id: str
    entry_type: str
    amount: int
    reason: str
    rail: Optional[str] = None
    payment_ref: Optional[str] = None
    foundup_id: Optional[str] = None
    event_id: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty(self.entry_id, "entry_id")
        _require_non_empty(self.actor_id, "actor_id")
        _require_non_empty(self.entry_type, "entry_type")
        _require_non_empty(self.reason, "reason")
        if not isinstance(self.amount, int) or self.amount <= 0:
            raise ValidationError("amount must be a positive integer")


@dataclass(slots=True)
class ComputeSession:
    session_id: str
    actor_id: str
    foundup_id: str
    workload: Dict[str, Any]
    credits_debited: int
    proof_id: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty(self.session_id, "session_id")
        _require_non_empty(self.actor_id, "actor_id")
        _require_non_empty(self.foundup_id, "foundup_id")
        if not isinstance(self.workload, dict):
            raise ValidationError("workload must be a dict")
        if not isinstance(self.credits_debited, int) or self.credits_debited < 0:
            raise ValidationError("credits_debited must be non-negative integer")
