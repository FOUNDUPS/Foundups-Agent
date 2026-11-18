"""Treasury Governance Service for FoundUps Agent Market.

Manages treasury proposals, approvals, and transfers with
multi-signature support and audit trail.

WSP References:
- WSP 11: Implements TreasuryGovernanceService interface contract
- WSP 30: Governance state machine design
- WSP 50: Error handling with domain exceptions
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .interfaces import TreasuryGovernanceService
from .exceptions import NotFoundError, PermissionDeniedError, ValidationError

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class ProposalStatus(str, Enum):
    """Status of a treasury proposal."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


@dataclass
class TreasuryProposal:
    """A proposal for treasury transfer."""

    proposal_id: str
    foundup_id: str
    proposer_id: str
    amount: int
    reason: str
    status: ProposalStatus = ProposalStatus.PENDING
    approvals: List[str] = field(default_factory=list)
    rejections: List[str] = field(default_factory=list)
    required_approvals: int = 1
    created_at: datetime = field(default_factory=_utc_now)
    executed_at: Optional[datetime] = None
    execution_ref: Optional[str] = None


@dataclass
class TreasuryState:
    """Current state of a FoundUp treasury."""

    foundup_id: str
    balance: int = 0
    pending_outflows: int = 0
    total_inflows: int = 0
    total_outflows: int = 0
    last_updated: datetime = field(default_factory=_utc_now)


class InMemoryTreasuryGovernance(TreasuryGovernanceService):
    """In-memory implementation of treasury governance.

    Provides proposal-based treasury management with:
    - Multi-signature approval support
    - Audit trail for all operations
    - Safe defaults (require approval for transfers)

    Example:
        treasury = InMemoryTreasuryGovernance()
        proposal_id = treasury.propose_transfer(
            foundup_id="fup_123",
            amount=1000,
            reason="Development bounty",
            proposer_id="user_1",
        )
        treasury.approve_transfer(proposal_id, "user_2")
        tx_ref = treasury.execute_transfer(proposal_id, "user_1")
    """

    def __init__(
        self,
        required_approvals: int = 1,
        max_single_transfer: int = 100_000,
    ) -> None:
        """Initialize treasury governance.

        Args:
            required_approvals: Number of approvals needed for execution.
            max_single_transfer: Maximum allowed single transfer amount.
        """
        self._proposals: Dict[str, TreasuryProposal] = {}
        self._states: Dict[str, TreasuryState] = {}
        self._required_approvals = required_approvals
        self._max_single_transfer = max_single_transfer
        self._events: List[Dict[str, Any]] = []

        logger.info(
            "[TREASURY] Initialized | required_approvals=%d max_transfer=%d",
            required_approvals,
            max_single_transfer,
        )

    def _get_or_create_state(self, foundup_id: str) -> TreasuryState:
        """Get or create treasury state for a FoundUp."""
        if foundup_id not in self._states:
            self._states[foundup_id] = TreasuryState(foundup_id=foundup_id)
        return self._states[foundup_id]

    def _emit_event(
        self,
        event_type: str,
        actor_id: str,
        foundup_id: str,
        payload: Dict[str, Any],
    ) -> None:
        """Emit a treasury event for audit trail."""
        self._events.append({
            "event_id": _generate_id("evt"),
            "event_type": event_type,
            "actor_id": actor_id,
            "foundup_id": foundup_id,
            "payload": payload,
            "timestamp": _utc_now().isoformat(),
        })

    def propose_transfer(
        self,
        foundup_id: str,
        amount: int,
        reason: str,
        proposer_id: str,
    ) -> str:
        """Propose a treasury transfer.

        Args:
            foundup_id: FoundUp treasury to transfer from.
            amount: Amount to transfer.
            reason: Reason for transfer.
            proposer_id: ID of actor proposing transfer.

        Returns:
            Proposal ID.

        Raises:
            ValidationError: If amount exceeds limits or reason empty.
        """
        if amount <= 0:
            raise ValidationError("Transfer amount must be positive")
        if amount > self._max_single_transfer:
            raise ValidationError(
                f"Amount {amount} exceeds max single transfer {self._max_single_transfer}"
            )
        if not reason or not reason.strip():
            raise ValidationError("Transfer reason is required")

        proposal_id = _generate_id("prop")
        proposal = TreasuryProposal(
            proposal_id=proposal_id,
            foundup_id=foundup_id,
            proposer_id=proposer_id,
            amount=amount,
            reason=reason.strip(),
            required_approvals=self._required_approvals,
        )

        self._proposals[proposal_id] = proposal

        # Update pending outflows
        state = self._get_or_create_state(foundup_id)
        state.pending_outflows += amount
        state.last_updated = _utc_now()

        self._emit_event(
            "treasury.proposal.created",
            proposer_id,
            foundup_id,
            {"proposal_id": proposal_id, "amount": amount, "reason": reason},
        )

        logger.info(
            "[TREASURY] Proposal created | id=%s foundup=%s amount=%d",
            proposal_id,
            foundup_id,
            amount,
        )

        return proposal_id

    def approve_transfer(self, proposal_id: str, approver_id: str) -> None:
        """Approve a treasury transfer proposal.

        Args:
            proposal_id: ID of proposal to approve.
            approver_id: ID of actor approving.

        Raises:
            NotFoundError: If proposal not found.
            ValidationError: If proposal not pending or already approved by this actor.
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            raise NotFoundError(f"Proposal not found: {proposal_id}")

        if proposal.status != ProposalStatus.PENDING:
            raise ValidationError(f"Proposal not pending: {proposal.status.value}")

        if approver_id in proposal.approvals:
            raise ValidationError(f"Already approved by: {approver_id}")

        if approver_id == proposal.proposer_id and self._required_approvals > 1:
            raise ValidationError("Proposer cannot approve their own proposal")

        proposal.approvals.append(approver_id)

        # Check if enough approvals
        if len(proposal.approvals) >= proposal.required_approvals:
            proposal.status = ProposalStatus.APPROVED

        self._emit_event(
            "treasury.proposal.approved",
            approver_id,
            proposal.foundup_id,
            {
                "proposal_id": proposal_id,
                "approval_count": len(proposal.approvals),
                "required": proposal.required_approvals,
            },
        )

        logger.info(
            "[TREASURY] Proposal approved | id=%s by=%s approvals=%d/%d",
            proposal_id,
            approver_id,
            len(proposal.approvals),
            proposal.required_approvals,
        )

    def execute_transfer(self, proposal_id: str, executor_id: str) -> str:
        """Execute an approved treasury transfer.

        Args:
            proposal_id: ID of approved proposal to execute.
            executor_id: ID of actor executing transfer.

        Returns:
            Transaction reference string.

        Raises:
            NotFoundError: If proposal not found.
            ValidationError: If proposal not approved.
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            raise NotFoundError(f"Proposal not found: {proposal_id}")

        if proposal.status != ProposalStatus.APPROVED:
            raise ValidationError(
                f"Cannot execute proposal with status: {proposal.status.value}"
            )

        state = self._get_or_create_state(proposal.foundup_id)

        # Check sufficient balance
        if state.balance < proposal.amount:
            raise ValidationError(
                f"Insufficient balance: {state.balance} < {proposal.amount}"
            )

        # Execute transfer
        tx_ref = _generate_id("tx")
        state.balance -= proposal.amount
        state.pending_outflows -= proposal.amount
        state.total_outflows += proposal.amount
        state.last_updated = _utc_now()

        proposal.status = ProposalStatus.EXECUTED
        proposal.executed_at = _utc_now()
        proposal.execution_ref = tx_ref

        self._emit_event(
            "treasury.transfer.executed",
            executor_id,
            proposal.foundup_id,
            {
                "proposal_id": proposal_id,
                "amount": proposal.amount,
                "tx_ref": tx_ref,
            },
        )

        logger.info(
            "[TREASURY] Transfer executed | id=%s amount=%d tx=%s",
            proposal_id,
            proposal.amount,
            tx_ref,
        )

        return tx_ref

    def get_treasury_state(self, foundup_id: str) -> Dict[str, object]:
        """Get current treasury state.

        Args:
            foundup_id: FoundUp to get state for.

        Returns:
            Dict with balance, pending outflows, totals.
        """
        state = self._get_or_create_state(foundup_id)
        return {
            "foundup_id": state.foundup_id,
            "balance": state.balance,
            "pending_outflows": state.pending_outflows,
            "total_inflows": state.total_inflows,
            "total_outflows": state.total_outflows,
            "last_updated": state.last_updated.isoformat(),
        }

    def deposit(self, foundup_id: str, amount: int, source: str) -> None:
        """Deposit funds into treasury.

        Args:
            foundup_id: FoundUp treasury to deposit to.
            amount: Amount to deposit.
            source: Source description.
        """
        if amount <= 0:
            raise ValidationError("Deposit amount must be positive")

        state = self._get_or_create_state(foundup_id)
        state.balance += amount
        state.total_inflows += amount
        state.last_updated = _utc_now()

        self._emit_event(
            "treasury.deposit",
            "system",
            foundup_id,
            {"amount": amount, "source": source},
        )

        logger.info(
            "[TREASURY] Deposit | foundup=%s amount=%d source=%s",
            foundup_id,
            amount,
            source,
        )

    def get_pending_proposals(self, foundup_id: str) -> List[Dict[str, Any]]:
        """Get pending proposals for a FoundUp.

        Args:
            foundup_id: FoundUp to get proposals for.

        Returns:
            List of pending proposal dicts.
        """
        return [
            {
                "proposal_id": p.proposal_id,
                "amount": p.amount,
                "reason": p.reason,
                "proposer_id": p.proposer_id,
                "approvals": p.approvals,
                "required_approvals": p.required_approvals,
                "created_at": p.created_at.isoformat(),
            }
            for p in self._proposals.values()
            if p.foundup_id == foundup_id and p.status == ProposalStatus.PENDING
        ]


# Keep stub for backwards compatibility
class TreasuryGovernanceStub(TreasuryGovernanceService):
    """Stub implementation for testing (deprecated, use InMemoryTreasuryGovernance)."""

    pass


# Default instance
_default_treasury: Optional[InMemoryTreasuryGovernance] = None


def get_treasury_governance() -> InMemoryTreasuryGovernance:
    """Get or create the default treasury governance instance."""
    global _default_treasury
    if _default_treasury is None:
        _default_treasury = InMemoryTreasuryGovernance()
    return _default_treasury
