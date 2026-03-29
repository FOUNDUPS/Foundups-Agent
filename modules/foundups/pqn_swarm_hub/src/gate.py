"""
PQN Swarm Hub - Participant Gate

Internal-first participant entry policy for PQN Swarm Hub.
Phase 1: In-memory gate exercised internally. External-ready structure.
Phase 1+: Optional SQLite persistence via store injection.

WSP 72: Module independence
WSP 97: Gate preparation for future external researchers

Entry Requirements (per MOLTbook spec):
1. Identity declaration (model type, compute capacity)
2. Capability verification (challenge-response hook)
3. Output validation (WSP 00 pass hook)

Trust Model: No trust by declaration. Only behavior, output, verification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from .contracts import generate_id, utc_now

if TYPE_CHECKING:
    from .persistence import SQLiteStore


class ParticipantStatus(str, Enum):
    """Status of a gate participant."""

    PENDING = "pending"  # Awaiting verification
    APPROVED = "approved"  # Passed gate, can submit work
    REJECTED = "rejected"  # Failed gate
    SUSPENDED = "suspended"  # Temporarily blocked


class ParticipantTier(str, Enum):
    """Tier assignment per WSP 15 scoring."""

    OBSERVER = "observer"  # Can view, no submit
    CONTRIBUTOR = "contributor"  # Can submit rESP
    VERIFIER = "verifier"  # Can verify submissions
    COORDINATOR = "coordinator"  # Can create work units


@dataclass
class ParticipantIdentity:
    """
    Identity metadata for gate entry.

    External-ready structure exercised internally first.
    """

    participant_id: str = field(default="")
    display_name: str = ""
    model_type: str = ""  # e.g., "claude-opus-4-5", "qwen-1.5b", "human"
    compute_capacity: str = ""  # e.g., "high", "medium", "low"
    capability_tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        if not self.participant_id:
            self.participant_id = generate_id(
                "participant",
                self.display_name or "anon",
                self.model_type or "unknown",
                self.registered_at.isoformat(),
            )


@dataclass
class GateDecision:
    """
    Gate entry decision record.

    Audit-safe output for tracking entry/rejection.
    """

    participant_id: str
    decision: str  # "approve" | "reject" | "suspend"
    tier: ParticipantTier
    reason: str
    decider_id: str  # "auto" | verifier ID
    decision_id: str = field(default="")
    decided_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        if not self.decision_id:
            self.decision_id = generate_id(
                "gate_decision",
                self.participant_id,
                self.decision,
                self.decided_at.isoformat(),
            )


# Type alias for policy hooks
PolicyHook = Callable[[ParticipantIdentity], tuple]  # Returns (bool, str reason)


class ParticipantGate:
    """
    Internal-first participant gate for PQN Swarm Hub.

    Validates participant entry before allowing work unit interaction.
    Supports policy hooks for capability verification and WSP 00 checks.
    Supports both in-memory (Phase 1) and SQLite (Phase 1+) storage.

    Phase 1: In-memory, internal participants only.
    Proto+: External-ready with challenge-response.
    """

    def __init__(
        self,
        default_tier: ParticipantTier = ParticipantTier.CONTRIBUTOR,
        require_capability_check: bool = False,
        require_wsp00_check: bool = False,
        store: Optional[SQLiteStore] = None,
    ) -> None:
        """
        Initialize participant gate.

        Args:
            default_tier: Default tier for new participants
            require_capability_check: Require capability verification
            require_wsp00_check: Require WSP 00 validation
            store: Optional SQLiteStore for persistence. If None, in-memory only.
        """
        self._participants: Dict[str, ParticipantIdentity] = {}
        self._decisions: Dict[str, GateDecision] = {}
        self._status: Dict[str, ParticipantStatus] = {}
        self._tiers: Dict[str, ParticipantTier] = {}
        self._store = store

        self._default_tier = default_tier
        self._require_capability_check = require_capability_check
        self._require_wsp00_check = require_wsp00_check

        # Policy hooks (pluggable)
        self._capability_hook: Optional[PolicyHook] = None
        self._wsp00_hook: Optional[PolicyHook] = None

    def register_capability_hook(self, hook: PolicyHook) -> None:
        """Register capability verification hook (challenge-response)."""
        self._capability_hook = hook

    def register_wsp00_hook(self, hook: PolicyHook) -> None:
        """Register WSP 00 validation hook."""
        self._wsp00_hook = hook

    def request_entry(
        self,
        identity: ParticipantIdentity,
        requested_tier: Optional[ParticipantTier] = None,
    ) -> GateDecision:
        """
        Request entry to PQN Swarm Hub.

        Evaluates identity against policy hooks and assigns tier.
        Phase 1: Auto-approve internal participants.

        Args:
            identity: Participant identity metadata
            requested_tier: Optional tier request (may be downgraded)

        Returns:
            GateDecision with approval/rejection
        """
        # Store identity (memory + SQLite)
        self._participants[identity.participant_id] = identity
        if self._store:
            self._store.save_participant(identity)

        # Default tier
        tier = requested_tier or self._default_tier

        # Capability check (if required and hook registered)
        if self._require_capability_check and self._capability_hook:
            passed, reason = self._capability_hook(identity)
            if not passed:
                return self._record_decision(
                    identity.participant_id,
                    "reject",
                    ParticipantTier.OBSERVER,
                    f"Capability check failed: {reason}",
                    "auto",
                )

        # WSP 00 check (if required and hook registered)
        if self._require_wsp00_check and self._wsp00_hook:
            passed, reason = self._wsp00_hook(identity)
            if not passed:
                return self._record_decision(
                    identity.participant_id,
                    "reject",
                    ParticipantTier.OBSERVER,
                    f"WSP 00 check failed: {reason}",
                    "auto",
                )

        # Phase 1: Auto-approve internal participants
        return self._record_decision(
            identity.participant_id,
            "approve",
            tier,
            "Internal participant auto-approved (Phase 1)",
            "auto",
        )

    def _record_decision(
        self,
        participant_id: str,
        decision: str,
        tier: ParticipantTier,
        reason: str,
        decider_id: str,
    ) -> GateDecision:
        """Record gate decision and update participant status."""
        dec = GateDecision(
            participant_id=participant_id,
            decision=decision,
            tier=tier,
            reason=reason,
            decider_id=decider_id,
        )
        self._decisions[dec.decision_id] = dec
        if self._store:
            self._store.save_gate_decision(dec)

        # Update status
        if decision == "approve":
            self._status[participant_id] = ParticipantStatus.APPROVED
            self._tiers[participant_id] = tier
        elif decision == "reject":
            self._status[participant_id] = ParticipantStatus.REJECTED
            self._tiers[participant_id] = ParticipantTier.OBSERVER
        elif decision == "suspend":
            self._status[participant_id] = ParticipantStatus.SUSPENDED

        return dec

    def check_permission(
        self,
        participant_id: str,
        required_tier: ParticipantTier,
    ) -> bool:
        """
        Check if participant has required tier permission.

        Tier hierarchy: COORDINATOR > VERIFIER > CONTRIBUTOR > OBSERVER
        """
        if participant_id not in self._status:
            return False
        if self._status[participant_id] != ParticipantStatus.APPROVED:
            return False

        current_tier = self._tiers.get(participant_id, ParticipantTier.OBSERVER)
        tier_order = [
            ParticipantTier.OBSERVER,
            ParticipantTier.CONTRIBUTOR,
            ParticipantTier.VERIFIER,
            ParticipantTier.COORDINATOR,
        ]

        current_level = tier_order.index(current_tier)
        required_level = tier_order.index(required_tier)
        return current_level >= required_level

    def get_participant(self, participant_id: str) -> Optional[ParticipantIdentity]:
        """Get participant by ID. Checks memory first, then store."""
        p = self._participants.get(participant_id)
        if p is None and self._store:
            p = self._store.get_participant(participant_id)
            if p:
                self._participants[participant_id] = p  # Cache in memory
        return p

    def get_status(self, participant_id: str) -> Optional[ParticipantStatus]:
        return self._status.get(participant_id)

    def get_tier(self, participant_id: str) -> Optional[ParticipantTier]:
        return self._tiers.get(participant_id)

    def list_approved(self, tier_filter: Optional[ParticipantTier] = None) -> List[ParticipantIdentity]:
        """List all approved participants, optionally filtered by tier."""
        approved_ids = [
            pid for pid, status in self._status.items()
            if status == ParticipantStatus.APPROVED
        ]
        if tier_filter:
            approved_ids = [
                pid for pid in approved_ids
                if self._tiers.get(pid) == tier_filter
            ]
        return [self._participants[pid] for pid in approved_ids if pid in self._participants]

    def suspend(self, participant_id: str, reason: str, actor_id: str) -> GateDecision:
        """Suspend an approved participant."""
        if participant_id not in self._participants:
            raise KeyError(f"Participant not found: {participant_id}")
        current_tier = self._tiers.get(participant_id, ParticipantTier.OBSERVER)
        return self._record_decision(
            participant_id,
            "suspend",
            current_tier,
            reason,
            actor_id,
        )

    def reinstate(self, participant_id: str, reason: str, actor_id: str) -> GateDecision:
        """Reinstate a suspended participant."""
        if participant_id not in self._participants:
            raise KeyError(f"Participant not found: {participant_id}")
        if self._status.get(participant_id) != ParticipantStatus.SUSPENDED:
            raise ValueError(f"Participant {participant_id} is not suspended")
        current_tier = self._tiers.get(participant_id, ParticipantTier.CONTRIBUTOR)
        return self._record_decision(
            participant_id,
            "approve",
            current_tier,
            f"Reinstated: {reason}",
            actor_id,
        )
