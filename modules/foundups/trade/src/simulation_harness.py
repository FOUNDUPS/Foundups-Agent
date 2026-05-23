"""Trade FoundUp - Simulation Harness

Deterministic PoC simulation harness for Trade module.
Generates synthetic market data and runs bounded strategy simulation.

WSP References:
- WSP 97: Truth Boundaries (simulation-only, no real trading)
- WSP 104: FoundUp Route Namespace

Phase 0 Constraints:
- Synthetic data only
- No network calls
- No wallet/key/order operations
- Deterministic output for same seed + bars

Slice: TRADE_POC_SIMULATION_HARNESS_PHASE1
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

try:
    from .contracts import (
        TruthFields,
        ExecutionGuardPolicy,
        DEFAULT_TRUTH_FIELDS,
        DEFAULT_EXECUTION_GUARD,
    )
    from .guards import (
        SimulationGuard,
        create_phase0_guard,
        validate_execution_guard_policy,
        validate_truth_fields,
    )
except ImportError:
    from contracts import (
        TruthFields,
        ExecutionGuardPolicy,
        DEFAULT_TRUTH_FIELDS,
        DEFAULT_EXECUTION_GUARD,
    )
    from guards import (
        SimulationGuard,
        create_phase0_guard,
        validate_execution_guard_policy,
        validate_truth_fields,
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_SEED = 42
DEFAULT_BARS = 100
DEFAULT_INITIAL_CAPITAL = 10000.0
MIN_ORDER_SIZE = 1
MAX_POSITION = 100


# ---------------------------------------------------------------------------
# Synthetic Bar
# ---------------------------------------------------------------------------


@dataclass
class SyntheticBar:
    """Synthetic OHLCV bar for simulation."""

    bar_index: int
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bar_index": self.bar_index,
            "open": round(self.open_price, 6),
            "high": round(self.high_price, 6),
            "low": round(self.low_price, 6),
            "close": round(self.close_price, 6),
            "volume": self.volume,
        }


# ---------------------------------------------------------------------------
# Simulation State
# ---------------------------------------------------------------------------


@dataclass
class SimulationState:
    """Current state of simulation at any bar."""

    bar_index: int
    cash: float
    position: int
    mark_price: float
    entry_price: Optional[float] = None

    @property
    def equity(self) -> float:
        """Total equity = cash + position * mark_price."""
        return self.cash + self.position * self.mark_price

    @property
    def unrealized_pnl(self) -> float:
        """Unrealized P&L on open position."""
        if self.position == 0 or self.entry_price is None:
            return 0.0
        return self.position * (self.mark_price - self.entry_price)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bar_index": self.bar_index,
            "cash": round(self.cash, 6),
            "position": self.position,
            "mark_price": round(self.mark_price, 6),
            "equity": round(self.equity, 6),
            "unrealized_pnl": round(self.unrealized_pnl, 6),
            "entry_price": round(self.entry_price, 6) if self.entry_price else None,
        }


# ---------------------------------------------------------------------------
# Trade Ledger
# ---------------------------------------------------------------------------


class TradeSide(str, Enum):
    """Side of a simulated trade."""

    BUY = "buy"
    SELL = "sell"


@dataclass
class SimulatedFill:
    """Record of a simulated trade fill."""

    fill_id: str
    bar_index: int
    side: TradeSide
    quantity: int
    price: float
    realized_pnl: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fill_id": self.fill_id,
            "bar_index": self.bar_index,
            "side": self.side.value,
            "quantity": self.quantity,
            "price": round(self.price, 6),
            "realized_pnl": round(self.realized_pnl, 6),
        }


@dataclass
class TradeLedger:
    """Ledger of all simulated fills."""

    fills: List[SimulatedFill] = field(default_factory=list)

    def add_fill(self, fill: SimulatedFill) -> None:
        self.fills.append(fill)

    @property
    def total_trades(self) -> int:
        return len(self.fills)

    @property
    def total_buys(self) -> int:
        return sum(1 for f in self.fills if f.side == TradeSide.BUY)

    @property
    def total_sells(self) -> int:
        return sum(1 for f in self.fills if f.side == TradeSide.SELL)

    @property
    def total_realized_pnl(self) -> float:
        return sum(f.realized_pnl for f in self.fills)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_trades": self.total_trades,
            "total_buys": self.total_buys,
            "total_sells": self.total_sells,
            "total_realized_pnl": round(self.total_realized_pnl, 6),
            "fills": [f.to_dict() for f in self.fills],
        }


# ---------------------------------------------------------------------------
# Strategy Intent
# ---------------------------------------------------------------------------


class IntentType(str, Enum):
    """Type of strategy intent."""

    HOLD = "hold"
    BUY = "buy"
    SELL = "sell"


@dataclass
class StrategyIntent:
    """Intent from strategy for the harness to execute."""

    intent_type: IntentType
    quantity: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_type": self.intent_type.value,
            "quantity": self.quantity,
        }


# ---------------------------------------------------------------------------
# Strategy Protocol
# ---------------------------------------------------------------------------


class ReferenceStrategy(Protocol):
    """Protocol for simulation strategies."""

    def receive_bar(
        self,
        bar: SyntheticBar,
        state: SimulationState,
    ) -> StrategyIntent:
        """Process a bar and return intent."""
        ...


# ---------------------------------------------------------------------------
# Simple Moving Average Strategy (Reference)
# ---------------------------------------------------------------------------


class SimpleSMAStrategy:
    """Simple moving average crossover strategy for reference.

    Long-only: buys when short SMA crosses above long SMA,
    sells when short SMA crosses below long SMA.
    """

    def __init__(self, short_period: int = 5, long_period: int = 10) -> None:
        self.short_period = short_period
        self.long_period = long_period
        self.prices: List[float] = []

    def _sma(self, period: int) -> Optional[float]:
        if len(self.prices) < period:
            return None
        return sum(self.prices[-period:]) / period

    def receive_bar(
        self,
        bar: SyntheticBar,
        state: SimulationState,
    ) -> StrategyIntent:
        self.prices.append(bar.close_price)

        short_sma = self._sma(self.short_period)
        long_sma = self._sma(self.long_period)

        if short_sma is None or long_sma is None:
            return StrategyIntent(IntentType.HOLD)

        if short_sma > long_sma and state.position == 0:
            affordable = int(state.cash // bar.close_price)
            qty = min(affordable, MAX_POSITION)
            if qty >= MIN_ORDER_SIZE:
                return StrategyIntent(IntentType.BUY, quantity=qty)

        elif short_sma < long_sma and state.position > 0:
            return StrategyIntent(IntentType.SELL, quantity=state.position)

        return StrategyIntent(IntentType.HOLD)


# ---------------------------------------------------------------------------
# Invariant Violations
# ---------------------------------------------------------------------------


@dataclass
class InvariantViolation:
    """Record of an invariant violation."""

    bar_index: int
    invariant: str
    message: str
    value: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bar_index": self.bar_index,
            "invariant": self.invariant,
            "message": self.message,
            "value": str(self.value),
        }


# ---------------------------------------------------------------------------
# Simulation Summary
# ---------------------------------------------------------------------------


@dataclass
class SimulationSummary:
    """Summary of simulation run."""

    run_id: str
    seed: int
    bars: int
    initial_capital: float
    final_equity: float
    total_trades: int
    gross_pnl: float
    max_drawdown: float
    sharpe_like_ratio: Optional[float]
    invariant_violations: int
    violations: List[InvariantViolation]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "seed": self.seed,
            "bars": self.bars,
            "initial_capital": round(self.initial_capital, 6),
            "final_equity": round(self.final_equity, 6),
            "total_trades": self.total_trades,
            "gross_pnl": round(self.gross_pnl, 6),
            "max_drawdown": round(self.max_drawdown, 6),
            "sharpe_like_ratio": round(self.sharpe_like_ratio, 6) if self.sharpe_like_ratio else None,
            "invariant_violations": self.invariant_violations,
            "violations": [v.to_dict() for v in self.violations],
        }


# ---------------------------------------------------------------------------
# Simulation Harness
# ---------------------------------------------------------------------------


class SimulationHarness:
    """Deterministic simulation harness for Trade PoC.

    Generates synthetic bars and runs a bounded strategy simulation.
    All operations are simulation-only per WSP 97.
    """

    def __init__(
        self,
        seed: int = DEFAULT_SEED,
        bars: int = DEFAULT_BARS,
        initial_capital: float = DEFAULT_INITIAL_CAPITAL,
        strategy: Optional[ReferenceStrategy] = None,
    ) -> None:
        self.seed = seed
        self.bars = bars
        self.initial_capital = initial_capital
        self.strategy = strategy or SimpleSMAStrategy()

        self.run_id = f"run-{seed}-{bars}"

        self._rng = random.Random(seed)
        self._synthetic_bars: List[SyntheticBar] = []
        self._ledger = TradeLedger()
        self._equity_history: List[float] = []
        self._violations: List[InvariantViolation] = []

        self._guard = create_phase0_guard()

    def _generate_synthetic_bars(self) -> List[SyntheticBar]:
        """Generate deterministic synthetic OHLCV bars."""
        bars_list: List[SyntheticBar] = []
        price = 100.0

        for i in range(self.bars):
            change_pct = self._rng.gauss(0.0, 0.02)
            close_price = price * (1 + change_pct)
            close_price = max(close_price, 1.0)

            high_offset = abs(self._rng.gauss(0, 0.01))
            low_offset = abs(self._rng.gauss(0, 0.01))

            open_price = price
            high_price = max(open_price, close_price) * (1 + high_offset)
            low_price = min(open_price, close_price) * (1 - low_offset)

            volume = int(self._rng.gauss(10000, 2000))
            volume = max(volume, 100)

            bar = SyntheticBar(
                bar_index=i,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
            )
            bars_list.append(bar)
            price = close_price

        return bars_list

    def _check_invariants(self, state: SimulationState, bar: SyntheticBar) -> None:
        """Check simulation invariants after each bar."""
        if state.cash < 0:
            self._violations.append(InvariantViolation(
                bar_index=bar.bar_index,
                invariant="cash_non_negative",
                message="Cash went negative (long-only violation)",
                value=state.cash,
            ))

        if state.position < 0:
            self._violations.append(InvariantViolation(
                bar_index=bar.bar_index,
                invariant="position_non_negative",
                message="Position went negative (long-only violation)",
                value=state.position,
            ))

        import math
        if math.isnan(state.equity) or math.isinf(state.equity):
            self._violations.append(InvariantViolation(
                bar_index=bar.bar_index,
                invariant="no_nan_infinity",
                message="Equity is NaN or Infinity",
                value=state.equity,
            ))

        if math.isnan(state.cash) or math.isinf(state.cash):
            self._violations.append(InvariantViolation(
                bar_index=bar.bar_index,
                invariant="no_nan_infinity",
                message="Cash is NaN or Infinity",
                value=state.cash,
            ))

    def _check_final_invariants(self, state: SimulationState) -> None:
        """Check final state invariants."""
        expected_equity = state.cash + state.position * state.mark_price
        if abs(state.equity - expected_equity) > 0.0001:
            self._violations.append(InvariantViolation(
                bar_index=state.bar_index,
                invariant="equity_reconciliation",
                message="Final equity does not match cash + position * mark_price",
                value={"equity": state.equity, "expected": expected_equity},
            ))

        ledger_position = sum(
            f.quantity if f.side == TradeSide.BUY else -f.quantity
            for f in self._ledger.fills
        )
        if ledger_position != state.position:
            self._violations.append(InvariantViolation(
                bar_index=state.bar_index,
                invariant="ledger_reconciliation",
                message="Position does not reconcile to ledger",
                value={"position": state.position, "ledger": ledger_position},
            ))

    def _calculate_max_drawdown(self) -> float:
        """Calculate max drawdown from equity history."""
        if not self._equity_history:
            return 0.0

        peak = self._equity_history[0]
        max_dd = 0.0

        for equity in self._equity_history:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def _calculate_sharpe_like_ratio(self) -> Optional[float]:
        """Calculate simplified Sharpe-like ratio from returns."""
        if len(self._equity_history) < 2:
            return None

        returns = []
        for i in range(1, len(self._equity_history)):
            prev = self._equity_history[i - 1]
            curr = self._equity_history[i]
            if prev > 0:
                returns.append((curr - prev) / prev)

        if not returns:
            return None

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)

        if variance <= 0:
            return None

        import math
        std_return = math.sqrt(variance)
        if std_return == 0:
            return None

        return mean_return / std_return

    def run(self) -> SimulationSummary:
        """Run the simulation.

        Returns:
            SimulationSummary with results and invariant check.
        """
        with self._guard:
            self._guard.assert_simulation_only("simulation_run")

            self._synthetic_bars = self._generate_synthetic_bars()
            if not self._synthetic_bars:
                return SimulationSummary(
                    run_id=self.run_id,
                    seed=self.seed,
                    bars=self.bars,
                    initial_capital=self.initial_capital,
                    final_equity=self.initial_capital,
                    total_trades=0,
                    gross_pnl=0.0,
                    max_drawdown=0.0,
                    sharpe_like_ratio=None,
                    invariant_violations=0,
                    violations=[],
                )

            state = SimulationState(
                bar_index=0,
                cash=self.initial_capital,
                position=0,
                mark_price=self._synthetic_bars[0].close_price,
            )

            for bar in self._synthetic_bars:
                state.bar_index = bar.bar_index
                state.mark_price = bar.close_price

                intent = self.strategy.receive_bar(bar, state)

                if intent.intent_type == IntentType.BUY and intent.quantity > 0:
                    qty = intent.quantity
                    if qty < MIN_ORDER_SIZE:
                        self._violations.append(InvariantViolation(
                            bar_index=bar.bar_index,
                            invariant="min_order_size",
                            message=f"Order below min size {MIN_ORDER_SIZE}",
                            value=qty,
                        ))
                    else:
                        cost = qty * bar.close_price
                        if cost <= state.cash:
                            state.cash -= cost
                            state.position += qty
                            state.entry_price = bar.close_price

                            fill_id = f"fill-{self.seed}-{bar.bar_index}-buy"
                            self._ledger.add_fill(SimulatedFill(
                                fill_id=fill_id,
                                bar_index=bar.bar_index,
                                side=TradeSide.BUY,
                                quantity=qty,
                                price=bar.close_price,
                            ))

                elif intent.intent_type == IntentType.SELL and intent.quantity > 0:
                    qty = min(intent.quantity, state.position)
                    if qty > 0:
                        proceeds = qty * bar.close_price
                        realized_pnl = 0.0
                        if state.entry_price is not None:
                            realized_pnl = qty * (bar.close_price - state.entry_price)

                        state.cash += proceeds
                        state.position -= qty

                        fill_id = f"fill-{self.seed}-{bar.bar_index}-sell"
                        self._ledger.add_fill(SimulatedFill(
                            fill_id=fill_id,
                            bar_index=bar.bar_index,
                            side=TradeSide.SELL,
                            quantity=qty,
                            price=bar.close_price,
                            realized_pnl=realized_pnl,
                        ))

                        if state.position == 0:
                            state.entry_price = None

                self._check_invariants(state, bar)
                self._equity_history.append(state.equity)

            self._check_final_invariants(state)

            return SimulationSummary(
                run_id=self.run_id,
                seed=self.seed,
                bars=self.bars,
                initial_capital=self.initial_capital,
                final_equity=state.equity,
                total_trades=self._ledger.total_trades,
                gross_pnl=state.equity - self.initial_capital,
                max_drawdown=self._calculate_max_drawdown(),
                sharpe_like_ratio=self._calculate_sharpe_like_ratio(),
                invariant_violations=len(self._violations),
                violations=self._violations,
            )

    def to_json(self) -> str:
        """Serialize simulation result to deterministic JSON.

        Returns:
            Canonical JSON string (sorted keys, no random elements).
        """
        summary = self.run()
        output = {
            "summary": summary.to_dict(),
            "ledger": self._ledger.to_dict(),
            "truth_boundary": {
                "is_simulation": True,
                "no_money_mode": True,
                "dry_run_mode": True,
                "real_execution_performed": False,
                "network_calls": False,
                "wallet_signing": False,
                "order_placement": False,
            },
        }
        return json.dumps(output, sort_keys=True, indent=2)

    def get_bars(self) -> List[SyntheticBar]:
        """Get generated synthetic bars (after run)."""
        return self._synthetic_bars

    def get_ledger(self) -> TradeLedger:
        """Get trade ledger (after run)."""
        return self._ledger


# ---------------------------------------------------------------------------
# CLI Entry Point Helper
# ---------------------------------------------------------------------------


def run_simulation(
    seed: int = DEFAULT_SEED,
    bars: int = DEFAULT_BARS,
    initial_capital: float = DEFAULT_INITIAL_CAPITAL,
    output_json: bool = False,
    output_path: Optional[str] = None,
) -> SimulationSummary:
    """Run simulation with given parameters.

    Args:
        seed: Random seed for deterministic generation
        bars: Number of synthetic bars
        initial_capital: Starting capital
        output_json: If True, print JSON to stdout
        output_path: If provided, write JSON to this path

    Returns:
        SimulationSummary with results
    """
    harness = SimulationHarness(
        seed=seed,
        bars=bars,
        initial_capital=initial_capital,
    )

    summary = harness.run()

    if output_json:
        json_output = harness.to_json()
        print(json_output)

    if output_path:
        json_output = harness.to_json()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_output)

    return summary
