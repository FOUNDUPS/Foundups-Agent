"""Trade FoundUp - Simulated Data Adapter

Simulation-only data adapter for Trade module.
Generates deterministic synthetic bars for simulation harness.

WSP References:
- WSP 97: Truth Boundaries (simulation-only, no real trading)
- WSP 104: FoundUp Route Namespace

Phase 0 Constraints:
- Synthetic data only
- No network calls
- No wallet/key/order operations
- Deterministic output for same seed + bar_count

Slice: TRADE_ADAPTER_INTEGRATION_PHASE1
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Protocol

try:
    from .simulation_harness import SyntheticBar
except ImportError:
    from simulation_harness import SyntheticBar


# ---------------------------------------------------------------------------
# Data Adapter Protocol
# ---------------------------------------------------------------------------


class DataAdapterProtocol(Protocol):
    """Protocol for simulation data adapters."""

    def iter_bars(self) -> Iterator[SyntheticBar]:
        """Iterate over synthetic bars."""
        ...

    def describe(self) -> Dict[str, Any]:
        """Return adapter description."""
        ...


# ---------------------------------------------------------------------------
# Simulated Data Adapter
# ---------------------------------------------------------------------------


@dataclass
class SimulatedDataAdapterConfig:
    """Configuration for SimulatedDataAdapter."""

    seed: int = 42
    bar_count: int = 100
    initial_price: float = 100.0
    volatility: float = 0.02
    volume_mean: int = 10000
    volume_std: int = 2000
    volume_min: int = 100


class SimulatedDataAdapter:
    """Simulated data adapter for Trade PoC.

    Generates deterministic synthetic OHLCV bars for simulation.
    Produces identical output to SimulationHarness._generate_synthetic_bars()
    for backward compatibility and deterministic equivalence.

    WSP 97 Truth Boundary:
    - network_capable: False (always)
    - live_capable: False (always)
    - wallet_capable: False (always)
    """

    def __init__(
        self,
        seed: int = 42,
        bar_count: int = 100,
        initial_price: float = 100.0,
        volatility: float = 0.02,
        volume_mean: int = 10000,
        volume_std: int = 2000,
        volume_min: int = 100,
        fixture_path: Optional[str] = None,
    ) -> None:
        """Initialize SimulatedDataAdapter.

        Args:
            seed: Random seed for deterministic generation
            bar_count: Number of bars to generate
            initial_price: Starting price for synthetic data
            volatility: Price change standard deviation (default 0.02 = 2%)
            volume_mean: Mean volume per bar
            volume_std: Volume standard deviation
            volume_min: Minimum volume floor
            fixture_path: Optional path to fixture file (not implemented)
        """
        self.seed = seed
        self.bar_count = bar_count
        self.initial_price = initial_price
        self.volatility = volatility
        self.volume_mean = volume_mean
        self.volume_std = volume_std
        self.volume_min = volume_min
        self.fixture_path = fixture_path

        self._rng = random.Random(seed)
        self._bars_generated = False
        self._cached_bars: List[SyntheticBar] = []

    def _generate_bars(self) -> List[SyntheticBar]:
        """Generate deterministic synthetic OHLCV bars.

        This method produces identical output to
        SimulationHarness._generate_synthetic_bars() for the same seed
        to preserve deterministic equivalence.
        """
        if self._bars_generated:
            return self._cached_bars

        bars_list: List[SyntheticBar] = []
        price = self.initial_price

        for i in range(self.bar_count):
            change_pct = self._rng.gauss(0.0, self.volatility)
            close_price = price * (1 + change_pct)
            close_price = max(close_price, 1.0)

            high_offset = abs(self._rng.gauss(0, 0.01))
            low_offset = abs(self._rng.gauss(0, 0.01))

            open_price = price
            high_price = max(open_price, close_price) * (1 + high_offset)
            low_price = min(open_price, close_price) * (1 - low_offset)

            volume = int(self._rng.gauss(self.volume_mean, self.volume_std))
            volume = max(volume, self.volume_min)

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

        self._cached_bars = bars_list
        self._bars_generated = True
        return bars_list

    def iter_bars(self) -> Iterator[SyntheticBar]:
        """Iterate over synthetic bars.

        Returns:
            Iterator of SyntheticBar objects
        """
        bars = self._generate_bars()
        for bar in bars:
            yield bar

    def get_bars(self) -> List[SyntheticBar]:
        """Get all synthetic bars as a list.

        Returns:
            List of SyntheticBar objects
        """
        return self._generate_bars()

    def describe(self) -> Dict[str, Any]:
        """Return adapter description.

        Returns:
            Dict with adapter metadata and capability flags
        """
        return {
            "type": "simulated",
            "seed": self.seed,
            "bar_count": self.bar_count,
            "source": "fixture" if self.fixture_path else "deterministic_generator",
            "initial_price": self.initial_price,
            "volatility": self.volatility,
            "network_capable": False,
            "live_capable": False,
            "wallet_capable": False,
        }

    def reset(self) -> None:
        """Reset adapter state for fresh generation."""
        self._rng = random.Random(self.seed)
        self._bars_generated = False
        self._cached_bars = []


# ---------------------------------------------------------------------------
# Factory Functions
# ---------------------------------------------------------------------------


def create_simulated_adapter(
    seed: int = 42,
    bar_count: int = 100,
    **kwargs: Any,
) -> SimulatedDataAdapter:
    """Create a SimulatedDataAdapter with given parameters.

    Args:
        seed: Random seed
        bar_count: Number of bars
        **kwargs: Additional config passed to SimulatedDataAdapter

    Returns:
        Configured SimulatedDataAdapter
    """
    return SimulatedDataAdapter(seed=seed, bar_count=bar_count, **kwargs)


def create_default_adapter() -> SimulatedDataAdapter:
    """Create a SimulatedDataAdapter with default parameters.

    Returns:
        SimulatedDataAdapter with seed=42, bar_count=100
    """
    return SimulatedDataAdapter(seed=42, bar_count=100)
