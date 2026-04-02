"""Channel Partner Pool - Genesis Founding Channel Partner Mechanics.

Implements the ChannelPartnerPool branch of PassiveParticipationPool per
canonical Du 4% partition model (2026-03-31).

CANONICAL DU POOL PARTITION:
  DuPool (4% of epoch distribution)
  ├── ActiveFounderPool (80% of Du = 3.2% of total)
  └── PassiveParticipationPool (20% of Du = 0.8% of total)
      ├── BTCStakerPool (weighted by deterministic formula)
      └── ChannelPartnerPool (equal split, max 21, genesis only) ← THIS FILE

GENESIS CHANNEL PARTNER RULES:
1. Pre-launch registration only
2. Hard cap: 21 founding channel partners
3. Equal split allocation (no tiered weighting in tranche 1)
4. Ecosystem-wide participation surface
5. Closes permanently at first mainnet FoundUp genesis/token issuance event

PARADIGM: CABR/PoB (not CAGR/ROI)
- Channel partners provide DISTRIBUTION (network reach)
- Partners receive F_i ALLOCATIONS (protocol mechanics)
- This is PROTOCOL PARTICIPATION, not investment

BOUNDARY NOTE:
- ChannelPartnerPool = genesis protocol participants (this file)
- BTCStakerPool = BTC liquidity providers (separate, weighted)
- I_i holders in investor_staking.py = SEPARATE bonding-curve lane
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# Genesis channel partner hard cap
CHANNEL_PARTNER_CAP = 21

# Channel partner pool share of PassiveParticipationPool
# PassiveParticipationPool = 20% of Du = 0.8% of total
# ChannelPartnerPool splits this with BTCStakerPool
# For genesis tranche: 50/50 split assumed until BTCStakerPool is implemented
CHANNEL_PARTNER_PASSIVE_SHARE = 0.50  # 50% of PassiveParticipationPool


class RegistryState(Enum):
    """Channel partner registry state."""

    OPEN = "open"  # Pre-launch: accepting registrations
    CLOSED = "closed"  # Post-launch: permanently closed


@dataclass
class ChannelPartner:
    """A registered genesis channel partner."""

    partner_id: str
    registered_at: str  # ISO timestamp
    display_name: Optional[str] = None
    channel_url: Optional[str] = None

    # Cumulative allocations received
    total_fi_allocated: float = 0.0
    epochs_participated: int = 0


@dataclass
class GenesisClosureEvent:
    """Records the mainnet genesis event that closed registration."""

    event_id: str
    timestamp: str  # ISO timestamp
    foundup_id: str  # First mainnet FoundUp
    closed_by: str = "mainnet_genesis"


@dataclass
class ChannelPartnerDistribution:
    """Result of distributing epoch allocation to channel partners."""

    epoch: int
    pool_amount: float  # Total F_i allocated to channel partner pool
    partner_count: int
    per_partner_amount: float
    distributions: Dict[str, float] = field(default_factory=dict)  # partner_id -> amount


class ChannelPartnerPool:
    """Genesis Founding Channel Partner Pool.

    Manages:
    1. Pre-launch partner registration (max 21)
    2. Launch closure event (permanent)
    3. Equal-split epoch distributions
    4. Ecosystem-wide participation tracking
    """

    def __init__(self) -> None:
        self._partners: Dict[str, ChannelPartner] = {}
        self._state: RegistryState = RegistryState.OPEN
        self._closure_event: Optional[GenesisClosureEvent] = None

        # Distribution tracking
        self._total_distributed: float = 0.0
        self._distribution_history: List[ChannelPartnerDistribution] = []

    # =========================================================================
    # REGISTRY OPERATIONS
    # =========================================================================

    @property
    def is_closed(self) -> bool:
        """True if registration is permanently closed."""
        return self._state == RegistryState.CLOSED

    @property
    def partner_count(self) -> int:
        """Number of registered partners."""
        return len(self._partners)

    @property
    def remaining_slots(self) -> int:
        """Slots remaining before cap."""
        return max(0, CHANNEL_PARTNER_CAP - self.partner_count)

    @property
    def is_at_cap(self) -> bool:
        """True if cap reached."""
        return self.partner_count >= CHANNEL_PARTNER_CAP

    def register_partner(
        self,
        partner_id: str,
        display_name: Optional[str] = None,
        channel_url: Optional[str] = None,
    ) -> tuple[bool, str]:
        """Register a new genesis channel partner.

        Args:
            partner_id: Unique partner identifier
            display_name: Optional display name
            channel_url: Optional channel/platform URL

        Returns:
            (success, message) tuple
        """
        # Check closure
        if self.is_closed:
            logger.warning(
                "[ChannelPartnerPool] Registration rejected: registry closed at mainnet genesis"
            )
            return (False, "Registry closed: mainnet genesis has occurred")

        # Check cap
        if self.is_at_cap:
            logger.warning(
                f"[ChannelPartnerPool] Registration rejected: cap of {CHANNEL_PARTNER_CAP} reached"
            )
            return (False, f"Registration cap of {CHANNEL_PARTNER_CAP} partners reached")

        # Check duplicate
        if partner_id in self._partners:
            logger.warning(
                f"[ChannelPartnerPool] Registration rejected: {partner_id} already registered"
            )
            return (False, f"Partner {partner_id} is already registered")

        # Register
        partner = ChannelPartner(
            partner_id=partner_id,
            registered_at=datetime.now().isoformat(),
            display_name=display_name,
            channel_url=channel_url,
        )
        self._partners[partner_id] = partner

        logger.info(
            f"[ChannelPartnerPool] Registered partner {partner_id} "
            f"({self.partner_count}/{CHANNEL_PARTNER_CAP} slots used)"
        )
        return (True, f"Partner {partner_id} registered successfully")

    def close_on_mainnet_genesis(
        self,
        event_id: str,
        timestamp: str,
        foundup_id: str,
    ) -> bool:
        """Close registration permanently on mainnet genesis event.

        Args:
            event_id: Unique identifier for the genesis event
            timestamp: ISO timestamp of the event
            foundup_id: ID of the first mainnet FoundUp

        Returns:
            True if closure succeeded, False if already closed
        """
        if self.is_closed:
            logger.warning(
                "[ChannelPartnerPool] Already closed, cannot close again"
            )
            return False

        self._state = RegistryState.CLOSED
        self._closure_event = GenesisClosureEvent(
            event_id=event_id,
            timestamp=timestamp,
            foundup_id=foundup_id,
        )

        logger.info(
            f"[ChannelPartnerPool] Registry CLOSED at mainnet genesis. "
            f"Event: {event_id}, FoundUp: {foundup_id}, "
            f"Partners locked: {self.partner_count}"
        )
        return True

    def list_partners(self) -> List[ChannelPartner]:
        """List all registered partners."""
        return list(self._partners.values())

    def get_partner(self, partner_id: str) -> Optional[ChannelPartner]:
        """Get a specific partner by ID."""
        return self._partners.get(partner_id)

    # =========================================================================
    # DISTRIBUTION OPERATIONS
    # =========================================================================

    def calculate_partner_share(self, pool_amount: float) -> float:
        """Calculate per-partner share using equal split.

        Args:
            pool_amount: Total F_i allocated to channel partner pool

        Returns:
            Per-partner allocation (0 if no partners)
        """
        if self.partner_count == 0:
            return 0.0
        return pool_amount / self.partner_count

    def distribute_epoch(
        self,
        epoch: int,
        pool_amount: float,
    ) -> ChannelPartnerDistribution:
        """Distribute epoch allocation to all registered partners.

        Uses equal split: each partner gets pool_amount / partner_count.

        Args:
            epoch: Epoch number
            pool_amount: Total F_i allocated to channel partner pool

        Returns:
            Distribution result with per-partner amounts
        """
        per_partner = self.calculate_partner_share(pool_amount)

        distributions: Dict[str, float] = {}
        for partner_id, partner in self._partners.items():
            partner.total_fi_allocated += per_partner
            partner.epochs_participated += 1
            distributions[partner_id] = per_partner

        self._total_distributed += pool_amount

        result = ChannelPartnerDistribution(
            epoch=epoch,
            pool_amount=pool_amount,
            partner_count=self.partner_count,
            per_partner_amount=per_partner,
            distributions=distributions,
        )
        self._distribution_history.append(result)

        logger.info(
            f"[ChannelPartnerPool] Epoch {epoch}: distributed {pool_amount:.4f} F_i "
            f"to {self.partner_count} partners ({per_partner:.4f} each)"
        )
        return result

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_stats(self) -> Dict:
        """Get pool statistics."""
        return {
            "partner_count": self.partner_count,
            "cap": CHANNEL_PARTNER_CAP,
            "remaining_slots": self.remaining_slots,
            "is_closed": self.is_closed,
            "closure_event": (
                {
                    "event_id": self._closure_event.event_id,
                    "timestamp": self._closure_event.timestamp,
                    "foundup_id": self._closure_event.foundup_id,
                }
                if self._closure_event
                else None
            ),
            "total_distributed": self._total_distributed,
            "epochs_distributed": len(self._distribution_history),
            "passive_share": CHANNEL_PARTNER_PASSIVE_SHARE,
        }


# =============================================================================
# SINGLETON PATTERN
# =============================================================================

_channel_partner_pool: Optional[ChannelPartnerPool] = None


def get_channel_partner_pool() -> ChannelPartnerPool:
    """Get the global channel partner pool singleton."""
    global _channel_partner_pool
    if _channel_partner_pool is None:
        _channel_partner_pool = ChannelPartnerPool()
    return _channel_partner_pool


def reset_channel_partner_pool() -> None:
    """Reset the channel partner pool (for testing)."""
    global _channel_partner_pool
    _channel_partner_pool = None
