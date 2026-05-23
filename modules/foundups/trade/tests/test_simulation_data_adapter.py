"""Trade FoundUp - Simulated Data Adapter Tests

Tests for simulation-only data adapter.

WSP 97 Truth Boundary:
- All tests verify simulation-only behavior
- Adapter must have network_capable=False, live_capable=False, wallet_capable=False

Slice: TRADE_ADAPTER_INTEGRATION_PHASE1
"""

import ast
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from simulation_data_adapter import (
    SimulatedDataAdapter,
    DataAdapterProtocol,
    SimulatedDataAdapterConfig,
    create_simulated_adapter,
    create_default_adapter,
)
from simulation_harness import (
    SimulationHarness,
    SyntheticBar,
)


# ---------------------------------------------------------------------------
# Forbidden Imports Test
# ---------------------------------------------------------------------------


FORBIDDEN_IMPORTS = {
    "requests",
    "urllib",
    "urllib3",
    "httpx",
    "aiohttp",
    "websocket",
    "websockets",
    "socket",
    "asyncio",
    "ccxt",
    "web3",
    "alpaca",
    "binance",
    "coinbase",
    "kraken",
    "ib_insync",
    "ftx",
    "bitfinex",
    "oandapyV20",
    "polygon",
    "yfinance",
    "pandas_datareader",
    "ib_async",
    "eth_account",
    "cryptography",
    "PyJWT",
    "paramiko",
    "smtplib",
    "ftplib",
    "telnetlib",
}


class TestForbiddenImports:
    """Verify simulation_data_adapter.py does not import forbidden modules."""

    def test_no_forbidden_imports_in_source(self):
        """Source file does not import any forbidden modules."""
        adapter_path = Path(__file__).parent.parent / "src" / "simulation_data_adapter.py"
        assert adapter_path.exists(), f"Source file not found: {adapter_path}"

        source_code = adapter_path.read_text(encoding="utf-8")
        tree = ast.parse(source_code)

        imported_modules = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.add(node.module.split(".")[0])

        violations = imported_modules & FORBIDDEN_IMPORTS
        assert len(violations) == 0, f"Forbidden imports found: {violations}"


# ---------------------------------------------------------------------------
# Forbidden Fields Test
# ---------------------------------------------------------------------------


FORBIDDEN_FIELDS = {
    "url",
    "endpoint",
    "host",
    "port",
    "api_key",
    "secret",
    "signer",
    "client_id",
    "exchange",
    "order",
    "wallet",
    "network",
    "mode",
}

ALLOWED_EXCEPTIONS = {
    "network_capable",
    "live_capable",
    "wallet_capable",
}


class TestForbiddenFields:
    """Verify simulation_data_adapter.py does not contain forbidden fields."""

    def test_no_forbidden_fields_in_source(self):
        """Source file does not contain forbidden field names as parameters or attributes."""
        adapter_path = Path(__file__).parent.parent / "src" / "simulation_data_adapter.py"
        source_code = adapter_path.read_text(encoding="utf-8")

        for forbidden in FORBIDDEN_FIELDS:
            if forbidden == "network":
                continue
            if forbidden == "wallet":
                continue

            pattern_param = f"{forbidden}="
            pattern_attr = f"self.{forbidden}"

            if pattern_param in source_code or pattern_attr in source_code:
                if forbidden in {"network", "wallet"}:
                    for allowed in ALLOWED_EXCEPTIONS:
                        if allowed in source_code:
                            continue
                assert False, f"Forbidden field '{forbidden}' found in source"

    def test_capability_flags_hardcoded_false(self):
        """Capability flags must be hardcoded to False."""
        adapter = SimulatedDataAdapter()
        desc = adapter.describe()

        assert desc["network_capable"] is False, "network_capable must be False"
        assert desc["live_capable"] is False, "live_capable must be False"
        assert desc["wallet_capable"] is False, "wallet_capable must be False"


# ---------------------------------------------------------------------------
# Adapter Basic Tests
# ---------------------------------------------------------------------------


class TestSimulatedDataAdapter:
    """Tests for SimulatedDataAdapter."""

    def test_default_initialization(self):
        """Adapter initializes with default parameters."""
        adapter = SimulatedDataAdapter()
        assert adapter.seed == 42
        assert adapter.bar_count == 100
        assert adapter.initial_price == 100.0
        assert adapter.volatility == 0.02

    def test_custom_initialization(self):
        """Adapter initializes with custom parameters."""
        adapter = SimulatedDataAdapter(
            seed=123,
            bar_count=50,
            initial_price=200.0,
            volatility=0.05,
        )
        assert adapter.seed == 123
        assert adapter.bar_count == 50
        assert adapter.initial_price == 200.0
        assert adapter.volatility == 0.05

    def test_iter_bars_returns_correct_count(self):
        """iter_bars returns correct number of bars."""
        adapter = SimulatedDataAdapter(seed=42, bar_count=50)
        bars = list(adapter.iter_bars())
        assert len(bars) == 50

    def test_get_bars_returns_correct_count(self):
        """get_bars returns correct number of bars."""
        adapter = SimulatedDataAdapter(seed=42, bar_count=100)
        bars = adapter.get_bars()
        assert len(bars) == 100

    def test_bars_are_synthetic_bar_type(self):
        """All bars are SyntheticBar type."""
        adapter = SimulatedDataAdapter(seed=42, bar_count=10)
        for bar in adapter.iter_bars():
            assert isinstance(bar, SyntheticBar)

    def test_bar_indices_sequential(self):
        """Bar indices are sequential from 0."""
        adapter = SimulatedDataAdapter(seed=42, bar_count=20)
        bars = list(adapter.iter_bars())
        for i, bar in enumerate(bars):
            assert bar.bar_index == i


# ---------------------------------------------------------------------------
# Deterministic Equivalence Tests
# ---------------------------------------------------------------------------


class TestDeterministicEquivalence:
    """Verify adapter produces identical bars to harness internal generator."""

    def test_adapter_matches_harness_bars(self):
        """SimulatedDataAdapter produces same bars as SimulationHarness."""
        adapter = SimulatedDataAdapter(seed=42, bar_count=100)
        adapter_bars = adapter.get_bars()

        harness = SimulationHarness(seed=42, bars=100)
        harness.run()
        harness_bars = harness.get_bars()

        assert len(adapter_bars) == len(harness_bars)

        for i, (a_bar, h_bar) in enumerate(zip(adapter_bars, harness_bars)):
            assert a_bar.bar_index == h_bar.bar_index, f"Bar {i} index mismatch"
            assert abs(a_bar.open_price - h_bar.open_price) < 1e-10, f"Bar {i} open mismatch"
            assert abs(a_bar.high_price - h_bar.high_price) < 1e-10, f"Bar {i} high mismatch"
            assert abs(a_bar.low_price - h_bar.low_price) < 1e-10, f"Bar {i} low mismatch"
            assert abs(a_bar.close_price - h_bar.close_price) < 1e-10, f"Bar {i} close mismatch"
            assert a_bar.volume == h_bar.volume, f"Bar {i} volume mismatch"

    def test_determinism_across_multiple_seeds(self):
        """Determinism holds for multiple seeds."""
        for seed in [42, 123, 456, 789, 1000]:
            adapter = SimulatedDataAdapter(seed=seed, bar_count=50)
            harness = SimulationHarness(seed=seed, bars=50)
            harness.run()

            adapter_bars = adapter.get_bars()
            harness_bars = harness.get_bars()

            for i in range(50):
                assert abs(adapter_bars[i].close_price - harness_bars[i].close_price) < 1e-10

    def test_same_seed_produces_identical_bars(self):
        """Same seed produces identical bars across adapter instances."""
        adapter1 = SimulatedDataAdapter(seed=42, bar_count=100)
        adapter2 = SimulatedDataAdapter(seed=42, bar_count=100)

        bars1 = adapter1.get_bars()
        bars2 = adapter2.get_bars()

        for i in range(100):
            assert bars1[i].close_price == bars2[i].close_price


# ---------------------------------------------------------------------------
# Describe Tests
# ---------------------------------------------------------------------------


class TestDescribe:
    """Tests for describe() method."""

    def test_describe_returns_dict(self):
        """describe() returns a dict."""
        adapter = SimulatedDataAdapter()
        desc = adapter.describe()
        assert isinstance(desc, dict)

    def test_describe_contains_required_fields(self):
        """describe() contains all required fields."""
        adapter = SimulatedDataAdapter(seed=123, bar_count=50)
        desc = adapter.describe()

        assert desc["type"] == "simulated"
        assert desc["seed"] == 123
        assert desc["bar_count"] == 50
        assert desc["source"] == "deterministic_generator"
        assert "network_capable" in desc
        assert "live_capable" in desc
        assert "wallet_capable" in desc

    def test_describe_capability_flags_false(self):
        """All capability flags are False."""
        adapter = SimulatedDataAdapter()
        desc = adapter.describe()

        assert desc["network_capable"] is False
        assert desc["live_capable"] is False
        assert desc["wallet_capable"] is False

    def test_describe_source_fixture(self):
        """source is 'fixture' when fixture_path is set."""
        adapter = SimulatedDataAdapter(fixture_path="/some/path.json")
        desc = adapter.describe()
        assert desc["source"] == "fixture"


# ---------------------------------------------------------------------------
# Reset Tests
# ---------------------------------------------------------------------------


class TestReset:
    """Tests for reset() method."""

    def test_reset_regenerates_same_bars(self):
        """reset() allows regenerating same bars."""
        adapter = SimulatedDataAdapter(seed=42, bar_count=50)

        bars1 = adapter.get_bars()
        adapter.reset()
        bars2 = adapter.get_bars()

        for i in range(50):
            assert bars1[i].close_price == bars2[i].close_price


# ---------------------------------------------------------------------------
# Factory Function Tests
# ---------------------------------------------------------------------------


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_simulated_adapter(self):
        """create_simulated_adapter creates adapter with given params."""
        adapter = create_simulated_adapter(seed=123, bar_count=75)
        assert adapter.seed == 123
        assert adapter.bar_count == 75

    def test_create_default_adapter(self):
        """create_default_adapter creates adapter with defaults."""
        adapter = create_default_adapter()
        assert adapter.seed == 42
        assert adapter.bar_count == 100


# ---------------------------------------------------------------------------
# Protocol Compliance Tests
# ---------------------------------------------------------------------------


class TestProtocolCompliance:
    """Tests for DataAdapterProtocol compliance."""

    def test_adapter_has_iter_bars(self):
        """Adapter has iter_bars method."""
        adapter = SimulatedDataAdapter()
        assert hasattr(adapter, "iter_bars")
        assert callable(adapter.iter_bars)

    def test_adapter_has_describe(self):
        """Adapter has describe method."""
        adapter = SimulatedDataAdapter()
        assert hasattr(adapter, "describe")
        assert callable(adapter.describe)
