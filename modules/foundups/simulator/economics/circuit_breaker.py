"""Circuit Breaker - Prevents Death Spiral.

Based on ERC-7265 and DeFi best practices.

Triggers:
1. Backing ratio < 80% → pause exits
2. Outflow > 10% of supply per day → queue exits
3. BTC price crash > 30% in 24h → emergency mode

Actions when triggered:
- Pause F_i → UPS conversions
- Reduce demurrage to 0
- Queue exits (gradual release)
- Notify users

This prevents Terra-style death spirals where panic → exits → more panic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from ._token_numeric import _require_numbers

logger = logging.getLogger(__name__)


class BreakerState(Enum):
    """Circuit breaker states."""
    NORMAL = "normal"  # All operations allowed
    CAUTION = "caution"  # Warnings, no restrictions
    RESTRICTED = "restricted"  # Exits queued, demurrage paused
    EMERGENCY = "emergency"  # All exits paused, governance required


class BreakerTrigger(Enum):
    """What triggered the circuit breaker."""
    BACKING_LOW = "backing_low"  # Reserve backing < threshold
    OUTFLOW_HIGH = "outflow_high"  # Too many exits per day
    BTC_CRASH = "btc_crash"  # BTC price dropped significantly
    MANUAL = "manual"  # Governance triggered


@dataclass
class BreakerConfig:
    """Configuration for circuit breaker thresholds."""

    # Backing ratio thresholds
    backing_caution: float = 0.90  # 90% → caution
    backing_restricted: float = 0.80  # 80% → restricted
    backing_emergency: float = 0.50  # 50% → emergency

    # Outflow thresholds (% of total supply per day)
    outflow_caution: float = 0.05  # 5%/day → caution
    outflow_restricted: float = 0.10  # 10%/day → restricted

    # BTC price crash threshold
    btc_crash_threshold: float = 0.30  # 30% drop in 24h → emergency

    # Cooldown before deactivation
    cooldown_hours: int = 24

    # Queue processing rate
    queue_release_per_hour: float = 0.10  # 10% of queue per hour


@dataclass
class QueuedExit:
    """An exit request waiting in queue."""
    human_id: str
    foundup_id: str
    fi_amount: float
    requested_at: datetime
    priority: int = 0  # Higher = processed first


@dataclass
class CircuitBreaker:
    """Circuit breaker for FoundUps economic system.

    Prevents death spirals by:
    1. Detecting stress conditions early
    2. Pausing/queuing exits during stress
    3. Reducing demurrage to not punish users for system issues
    4. Gradual recovery to normal operations
    """

    config: BreakerConfig = field(default_factory=BreakerConfig)

    # Current state
    state: BreakerState = BreakerState.NORMAL
    trigger: Optional[BreakerTrigger] = None
    triggered_at: Optional[datetime] = None

    # Exit queue (when in RESTRICTED mode)
    exit_queue: List[QueuedExit] = field(default_factory=list)

    # Metrics tracking
    daily_outflow: float = 0.0
    last_outflow_reset: datetime = field(default_factory=datetime.now)
    btc_price_24h_ago: float = 100000.0

    # Statistics
    times_triggered: int = 0
    total_queued_exits: int = 0

    def check_conditions(
        self,
        backing_ratio: float,
        current_btc_price: float,
    ) -> BreakerState:
        """Check all conditions and update state.

        Args:
            backing_ratio: Current UPS backing ratio
            current_btc_price: Current BTC price in USD

        Returns:
            New breaker state
        """
        _require_numbers(backing_ratio, current_btc_price,
                         self.btc_price_24h_ago, self.daily_outflow)
        # Check BTC crash
        if self.btc_price_24h_ago > 0:
            btc_change = (current_btc_price - self.btc_price_24h_ago) / self.btc_price_24h_ago
            if btc_change < -self.config.btc_crash_threshold:
                return self._transition_to(BreakerState.EMERGENCY, BreakerTrigger.BTC_CRASH)

        # Check backing ratio (most important)
        if backing_ratio < self.config.backing_emergency:
            return self._transition_to(BreakerState.EMERGENCY, BreakerTrigger.BACKING_LOW)
        if backing_ratio < self.config.backing_restricted:
            return self._transition_to(BreakerState.RESTRICTED, BreakerTrigger.BACKING_LOW)

        # Evaluate every restricted signal before any lower-severity caution.
        outflow_ratio = self.daily_outflow  # Already as ratio
        if outflow_ratio > self.config.outflow_restricted:
            return self._transition_to(BreakerState.RESTRICTED, BreakerTrigger.OUTFLOW_HIGH)
        if backing_ratio < self.config.backing_caution:
            return self._transition_to(BreakerState.CAUTION, BreakerTrigger.BACKING_LOW)
        if outflow_ratio > self.config.outflow_caution:
            return self._transition_to(BreakerState.CAUTION, BreakerTrigger.OUTFLOW_HIGH)

        # Check if can recover to normal
        if self.state != BreakerState.NORMAL:
            if self._can_recover():
                return self._transition_to(BreakerState.NORMAL, None)

        return self.state

    def _transition_to(self, new_state: BreakerState, trigger: Optional[BreakerTrigger]) -> BreakerState:
        """Transition to a new state."""
        if new_state == self.state:
            return self.state

        # A milder current signal is not recovery authorization. Apply the
        # existing cooldown/empty-queue rule to every severity downgrade.
        severity = {BreakerState.NORMAL: 0, BreakerState.CAUTION: 1,
                    BreakerState.RESTRICTED: 2, BreakerState.EMERGENCY: 3}
        if severity[new_state] < severity[self.state] and not self._can_recover():
            return self.state

        old_state = self.state
        self.state = new_state
        self.trigger = trigger
        self.triggered_at = datetime.now() if trigger else None

        if new_state != BreakerState.NORMAL:
            self.times_triggered += 1

        logger.warning(
            f"[CircuitBreaker] {old_state.value} → {new_state.value} "
            f"(trigger: {trigger.value if trigger else 'recovery'})"
        )

        return new_state

    def _can_recover(self) -> bool:
        """Check if conditions allow recovery to normal."""
        if not self.triggered_at:
            return True

        # Must wait cooldown period
        cooldown = timedelta(hours=self.config.cooldown_hours)
        if datetime.now() - self.triggered_at < cooldown:
            return False

        # Queue must be empty
        if self.exit_queue:
            return False

        return True

    def record_outflow(self, ups_amount: float, total_supply: float) -> None:
        """Record an outflow (exit) event."""
        # Reset daily counter if needed
        if datetime.now() - self.last_outflow_reset > timedelta(days=1):
            self.daily_outflow = 0.0
            self.last_outflow_reset = datetime.now()

        self.daily_outflow += ups_amount / total_supply if total_supply > 0 else 0

    def update_btc_price(self, new_price: float) -> None:
        """Update BTC price for crash detection."""
        # Simple 24h rolling (in production: proper time-weighted)
        self.btc_price_24h_ago = new_price

    def can_exit(self) -> bool:
        """Check if exits are currently allowed."""
        return self.state in (BreakerState.NORMAL, BreakerState.CAUTION)

    def must_queue_exit(self) -> bool:
        """Check if exits must be queued."""
        return self.state == BreakerState.RESTRICTED

    def exits_blocked(self) -> bool:
        """Check if exits are completely blocked."""
        return self.state == BreakerState.EMERGENCY

    def queue_exit(
        self,
        human_id: str,
        foundup_id: str,
        fi_amount: float,
    ) -> QueuedExit:
        """Add an exit request to the queue."""
        queued = QueuedExit(
            human_id=human_id,
            foundup_id=foundup_id,
            fi_amount=fi_amount,
            requested_at=datetime.now(),
        )
        self.exit_queue.append(queued)
        self.total_queued_exits += 1

        logger.info(
            f"[CircuitBreaker] Queued exit: {human_id} -> {fi_amount:.2f} F_i "
            f"(queue size: {len(self.exit_queue)})"
        )
        return queued

    def process_queue(self) -> List[QueuedExit]:
        """Process queued exits (call hourly).

        Returns:
            List of exits ready to process
        """
        if not self.exit_queue or self.exits_blocked():
            return []

        # Process 10% of queue per hour
        num_to_process = max(1, int(len(self.exit_queue) * self.config.queue_release_per_hour))
        ready = self.exit_queue[:num_to_process]
        self.exit_queue = self.exit_queue[num_to_process:]

        logger.info(
            f"[CircuitBreaker] Processing {len(ready)} queued exits "
            f"(remaining: {len(self.exit_queue)})"
        )
        return ready

    def get_demurrage_multiplier(self) -> float:
        """Get demurrage rate multiplier based on state.

        Returns:
            Multiplier (0.0 = no demurrage, 1.0 = full demurrage)
        """
        if self.state == BreakerState.EMERGENCY:
            return 0.0  # No demurrage during emergency
        elif self.state == BreakerState.RESTRICTED:
            return 0.25  # 25% of normal demurrage
        elif self.state == BreakerState.CAUTION:
            return 0.50  # 50% of normal demurrage
        return 1.0  # Full demurrage

    def get_status(self) -> Dict:
        """Get current circuit breaker status."""
        return {
            "state": self.state.value,
            "trigger": self.trigger.value if self.trigger else None,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "exits_allowed": self.can_exit(),
            "exits_queued": self.must_queue_exit(),
            "exits_blocked": self.exits_blocked(),
            "queue_size": len(self.exit_queue),
            "demurrage_multiplier": self.get_demurrage_multiplier(),
            "daily_outflow": f"{self.daily_outflow*100:.2f}%",
            "times_triggered": self.times_triggered,
        }


# Singleton instance
_circuit_breaker: Optional[CircuitBreaker] = None


def get_circuit_breaker() -> CircuitBreaker:
    """Get singleton circuit breaker instance."""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()
    return _circuit_breaker


def reset_circuit_breaker() -> None:
    """Reset circuit breaker (for testing)."""
    global _circuit_breaker
    _circuit_breaker = None
