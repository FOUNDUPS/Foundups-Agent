"""Allocation Engine - 0102 Digital Twin UPS→F_i Routing.

Orchestrates the flow from 012 subscription UPS to F_i acquisition:

1. 012 receives UPS from subscription
2. 0102 digital twin decides allocation (fixed or autonomous)
3. For each FoundUp target:
   - Check F_i availability
   - AVAILABLE → direct stake (UPS→F_i)
   - SCARCE → place buy order on DEX

This is an ORCHESTRATOR - it calls existing engines, doesn't duplicate logic:
- TokenEconomicsEngine: staking operations
- OrderBookManager: DEX buy orders
- FiRatingEngine: autonomous allocation decisions
- PoolDistributor: availability checks

All allocation decisions are 0102-managed. 012 interacts through digital twin.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .token_economics import TokenEconomicsEngine, HumanUPSAccount
    from .fi_orderbook import OrderBookManager, Order, Trade
    from .fi_rating import FiRatingEngine

from .fi_orderbook import OrderStatus

logger = logging.getLogger(__name__)


class AllocationStrategy(Enum):
    """How 0102 digital twin allocates UPS to FoundUps."""

    FIXED = "fixed"           # 012 specifies exact percentages
    AUTONOMOUS = "autonomous"  # 0102 decides based on CABR/ratings
    BALANCED = "balanced"      # Equal split across portfolio
    MOMENTUM = "momentum"      # Weight toward high-performing F_i


class AllocationPath(Enum):
    """How F_i was acquired."""

    DIRECT_STAKE = "direct_stake"  # F_i available, staked directly
    DEX_BUY = "dex_buy"            # F_i scarce, bought on exchange
    DEX_PENDING = "dex_pending"    # Buy order placed, awaiting fill
    FAILED = "failed"              # Allocation failed


@dataclass
class AllocationTarget:
    """A single FoundUp allocation target."""

    foundup_id: str
    percentage: float  # 0.0 to 1.0
    ups_amount: float = 0.0  # Calculated from total * percentage


@dataclass
class AllocationResult:
    """Result of allocating UPS to a single FoundUp."""

    foundup_id: str
    ups_allocated: float
    fi_received: float
    path: AllocationPath
    order_id: Optional[str] = None  # If DEX_PENDING
    fee_paid: float = 0.0
    message: str = ""


@dataclass
class AllocationBatch:
    """Result of allocating UPS across multiple FoundUps."""

    human_id: str
    total_ups: float
    strategy: AllocationStrategy
    results: List[AllocationResult] = field(default_factory=list)

    @property
    def total_fi_received(self) -> float:
        """Total F_i received across all allocations."""
        return sum(r.fi_received for r in self.results)

    @property
    def total_fees(self) -> float:
        """Total fees paid across all allocations."""
        return sum(r.fee_paid for r in self.results)

    @property
    def pending_orders(self) -> List[AllocationResult]:
        """Allocations waiting for DEX fill."""
        return [r for r in self.results if r.path == AllocationPath.DEX_PENDING]

    @property
    def success_count(self) -> int:
        """Number of successful allocations."""
        return sum(1 for r in self.results if r.path in (
            AllocationPath.DIRECT_STAKE, AllocationPath.DEX_BUY
        ))


class AllocationEngine:
    """0102 Digital Twin Allocation Engine.

    Orchestrates UPS→F_i allocation decisions:
    - Fixed: 012 specifies exact allocation percentages
    - Autonomous: 0102 decides based on F_i ratings and CABR scores

    Routes to direct staking when F_i available, DEX buy orders when scarce.
    """

    def __init__(
        self,
        token_engine: Optional["TokenEconomicsEngine"] = None,
        orderbook_manager: Optional["OrderBookManager"] = None,
        rating_engine: Optional["FiRatingEngine"] = None,
    ):
        """Initialize allocation engine with component engines.

        Args:
            token_engine: For staking operations
            orderbook_manager: For DEX buy orders
            rating_engine: For autonomous allocation decisions
        """
        self.token_engine = token_engine
        self.orderbook_manager = orderbook_manager
        self.rating_engine = rating_engine

        # Allocation history
        self.total_allocated_ups: float = 0.0
        self.total_fi_acquired: float = 0.0
        self.allocation_count: int = 0

        # Thresholds
        self.min_allocation_ups: float = 1.0  # Minimum UPS per FoundUp
        self.scarcity_threshold: float = 0.10  # <10% remaining = scarce

        logger.info("[AllocationEngine] Initialized")

    def check_fi_availability(
        self,
        foundup_id: str,
    ) -> Tuple[bool, float, float]:
        """Check if F_i is available for direct staking.

        Args:
            foundup_id: FoundUp to check

        Returns:
            (is_available, remaining_supply, total_supply)
        """
        if self.token_engine is None:
            logger.warning("[AllocationEngine] No token engine - assuming available")
            return (True, float('inf'), float('inf'))

        pool = self.token_engine.foundup_pools.get(foundup_id)
        if pool is None:
            # No pool = new FoundUp, always available
            return (True, float('inf'), float('inf'))

        remaining = pool.remaining_mintable
        total = pool.available_supply

        # Scarce if <10% remaining at current tier
        is_available = (total == 0) or (remaining / total > self.scarcity_threshold)

        return (is_available, remaining, total)

    def allocate_fixed(
        self,
        human_id: str,
        total_ups: float,
        targets: Dict[str, float],  # foundup_id -> percentage (0-1)
    ) -> AllocationBatch:
        """Allocate UPS with fixed percentages specified by 012.

        Args:
            human_id: 012 identifier
            total_ups: Total UPS to allocate
            targets: {foundup_id: percentage} - must sum to <= 1.0

        Returns:
            AllocationBatch with results for each target
        """
        batch = AllocationBatch(
            human_id=human_id,
            total_ups=total_ups,
            strategy=AllocationStrategy.FIXED,
        )

        # Validate percentages
        total_pct = sum(targets.values())
        if total_pct > 1.0:
            logger.warning(f"[AllocationEngine] Percentages sum to {total_pct:.2%} > 100%")
            # Normalize
            targets = {k: v / total_pct for k, v in targets.items()}

        # Allocate to each target
        for foundup_id, percentage in targets.items():
            ups_amount = total_ups * percentage

            if ups_amount < self.min_allocation_ups:
                batch.results.append(AllocationResult(
                    foundup_id=foundup_id,
                    ups_allocated=0.0,
                    fi_received=0.0,
                    path=AllocationPath.FAILED,
                    message=f"Below minimum: {ups_amount:.2f} < {self.min_allocation_ups}",
                ))
                continue

            result = self._allocate_single(human_id, foundup_id, ups_amount)
            batch.results.append(result)

        # Update stats
        self.total_allocated_ups += sum(r.ups_allocated for r in batch.results)
        self.total_fi_acquired += batch.total_fi_received
        self.allocation_count += 1

        logger.info(
            f"[AllocationEngine] FIXED allocation for {human_id}: "
            f"{total_ups:.2f} UPS -> {batch.total_fi_received:.2f} F_i "
            f"({batch.success_count}/{len(targets)} targets, "
            f"{len(batch.pending_orders)} pending)"
        )

        return batch

    def allocate_autonomous(
        self,
        human_id: str,
        total_ups: float,
        candidate_foundups: Optional[List[str]] = None,
        max_targets: int = 5,
    ) -> AllocationBatch:
        """Let 0102 digital twin decide allocation autonomously.

        Uses F_i ratings and CABR scores to determine optimal allocation.

        Args:
            human_id: 012 identifier
            total_ups: Total UPS to allocate
            candidate_foundups: Optional list to consider (else all known)
            max_targets: Maximum FoundUps to allocate to

        Returns:
            AllocationBatch with results
        """
        batch = AllocationBatch(
            human_id=human_id,
            total_ups=total_ups,
            strategy=AllocationStrategy.AUTONOMOUS,
        )

        # Get candidates
        if candidate_foundups is None:
            if self.token_engine is not None:
                candidate_foundups = list(self.token_engine.foundup_pools.keys())
            else:
                logger.warning("[AllocationEngine] No candidates for autonomous allocation")
                return batch

        if not candidate_foundups:
            return batch

        # Score and rank candidates
        scored = self._score_candidates(candidate_foundups)

        # Take top N
        top_candidates = sorted(scored.items(), key=lambda x: x[1], reverse=True)[:max_targets]

        if not top_candidates:
            return batch

        # Allocate proportionally to scores
        total_score = sum(score for _, score in top_candidates)
        if total_score == 0:
            # Equal split if no scoring available
            pct = 1.0 / len(top_candidates)
            targets = {fid: pct for fid, _ in top_candidates}
        else:
            targets = {fid: score / total_score for fid, score in top_candidates}

        # Execute allocation
        for foundup_id, percentage in targets.items():
            ups_amount = total_ups * percentage

            if ups_amount < self.min_allocation_ups:
                continue

            result = self._allocate_single(human_id, foundup_id, ups_amount)
            batch.results.append(result)

        # Update stats
        self.total_allocated_ups += sum(r.ups_allocated for r in batch.results)
        self.total_fi_acquired += batch.total_fi_received
        self.allocation_count += 1

        logger.info(
            f"[AllocationEngine] AUTONOMOUS allocation for {human_id}: "
            f"{total_ups:.2f} UPS -> {batch.total_fi_received:.2f} F_i "
            f"({batch.success_count} targets, {len(batch.pending_orders)} pending)"
        )

        return batch

    def _score_candidates(self, foundup_ids: List[str]) -> Dict[str, float]:
        """Score FoundUp candidates for autonomous allocation.

        Uses F_i ratings if available, else equal scoring.
        """
        scores = {}

        for fid in foundup_ids:
            score = 1.0  # Default equal weight

            # Use F_i rating if available
            if self.rating_engine is not None:
                rating = None
                if hasattr(self.rating_engine, "get_rating"):
                    rating = self.rating_engine.get_rating(fid)
                elif hasattr(self.rating_engine, "foundups"):
                    rating = self.rating_engine.foundups.get(fid)
                if rating is not None:
                    # Composite score is already normalized to 0..1.
                    score = max(0.0, min(1.0, float(rating.composite)))

            # Check availability - penalize scarce FoundUps
            is_available, remaining, total = self.check_fi_availability(fid)
            if not is_available:
                score *= 0.5  # Reduce score for scarce F_i

            scores[fid] = score

        return scores

    def _allocate_single(
        self,
        human_id: str,
        foundup_id: str,
        ups_amount: float,
    ) -> AllocationResult:
        """Allocate UPS to a single FoundUp.

        Routes to direct stake or DEX based on availability.
        """
        # Check availability
        is_available, remaining, total = self.check_fi_availability(foundup_id)

        if is_available:
            # Path A: Direct stake
            return self._stake_direct(human_id, foundup_id, ups_amount)
        else:
            # Path B: DEX buy order
            return self._place_buy_order(human_id, foundup_id, ups_amount)

    def _stake_direct(
        self,
        human_id: str,
        foundup_id: str,
        ups_amount: float,
    ) -> AllocationResult:
        """Direct stake UPS for F_i."""
        if self.token_engine is None:
            return AllocationResult(
                foundup_id=foundup_id,
                ups_allocated=ups_amount,
                fi_received=0.0,
                path=AllocationPath.FAILED,
                message="No token engine configured",
            )

        fi_received, fee_paid = self.token_engine.human_stakes_ups(
            human_id=human_id,
            foundup_id=foundup_id,
            ups_amount=ups_amount,
        )

        if fi_received > 0:
            return AllocationResult(
                foundup_id=foundup_id,
                ups_allocated=ups_amount,
                fi_received=fi_received,
                path=AllocationPath.DIRECT_STAKE,
                fee_paid=fee_paid,
                message=f"Staked {ups_amount:.2f} UPS -> {fi_received:.2f} F_i",
            )
        else:
            return AllocationResult(
                foundup_id=foundup_id,
                ups_allocated=0.0,
                fi_received=0.0,
                path=AllocationPath.FAILED,
                message="Staking failed - insufficient UPS or pool issue",
            )

    def _place_buy_order(
        self,
        human_id: str,
        foundup_id: str,
        ups_amount: float,
    ) -> AllocationResult:
        """Place DEX buy order for scarce F_i."""
        if self.orderbook_manager is None:
            return AllocationResult(
                foundup_id=foundup_id,
                ups_allocated=ups_amount,
                fi_received=0.0,
                path=AllocationPath.FAILED,
                message="No orderbook manager configured",
            )

        # Calculate bid price (use mid price or slight premium)
        book = self.orderbook_manager.get_or_create_book(foundup_id)

        if book.best_ask is not None:
            # Bid at ask price for immediate fill
            price = book.best_ask
        elif book.mid_price is not None:
            price = book.mid_price
        else:
            # No market - use default price
            price = 1.0  # 1 UPS = 1 F_i default

        # Calculate quantity we can buy
        quantity = ups_amount / price

        # Place order
        order, trades = book.place_buy_order(
            human_id=human_id,
            price=price,
            quantity=quantity,
        )

        if order.status == OrderStatus.CANCELLED:
            return AllocationResult(
                foundup_id=foundup_id,
                ups_allocated=sum(t.ups_total for t in trades),
                fi_received=sum(t.quantity for t in trades),
                path=AllocationPath.DEX_BUY if trades else AllocationPath.FAILED,
                order_id=order.order_id,
                fee_paid=sum(t.fee_ups for t in trades),
                message=f"Order cancelled: {order.rejection_reason}; {order.remaining:.2f} F_i unfilled",
            )

        if trades:
            # Immediate fill (partial or full)
            fi_received = sum(t.quantity for t in trades)
            fee_paid = sum(t.fee_ups for t in trades)

            if order.remaining > 0:
                # Partial fill - rest is pending
                return AllocationResult(
                    foundup_id=foundup_id,
                    ups_allocated=ups_amount,
                    fi_received=fi_received,
                    path=AllocationPath.DEX_BUY,
                    order_id=order.order_id,
                    fee_paid=fee_paid,
                    message=f"Partial fill: {fi_received:.2f} F_i, {order.remaining:.2f} pending",
                )
            else:
                # Full fill
                return AllocationResult(
                    foundup_id=foundup_id,
                    ups_allocated=ups_amount,
                    fi_received=fi_received,
                    path=AllocationPath.DEX_BUY,
                    fee_paid=fee_paid,
                    message=f"DEX buy: {fi_received:.2f} F_i @ {price:.4f}",
                )
        else:
            # No immediate fill - order pending
            return AllocationResult(
                foundup_id=foundup_id,
                ups_allocated=ups_amount,
                fi_received=0.0,
                path=AllocationPath.DEX_PENDING,
                order_id=order.order_id,
                message=f"Buy order placed: {quantity:.2f} F_i @ {price:.4f}",
            )

    def get_stats(self) -> Dict:
        """Get allocation engine statistics."""
        return {
            "total_allocated_ups": self.total_allocated_ups,
            "total_fi_acquired": self.total_fi_acquired,
            "allocation_count": self.allocation_count,
            "avg_ups_per_allocation": (
                self.total_allocated_ups / self.allocation_count
                if self.allocation_count > 0 else 0.0
            ),
            "conversion_rate": (
                self.total_fi_acquired / self.total_allocated_ups
                if self.total_allocated_ups > 0 else 0.0
            ),
        }


# Singleton instance
_allocation_engine: Optional[AllocationEngine] = None


def get_allocation_engine() -> AllocationEngine:
    """Get or create the singleton allocation engine."""
    global _allocation_engine
    if _allocation_engine is None:
        _allocation_engine = AllocationEngine()
    return _allocation_engine


def reset_allocation_engine() -> None:
    """Reset the singleton (for testing)."""
    global _allocation_engine
    _allocation_engine = None
