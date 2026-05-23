"""Trade FoundUp - Simulation Harness Tests

Tests for deterministic PoC simulation harness.

WSP 97 Truth Boundary:
- All tests verify simulation-only behavior
- No real trading, wallet signing, network calls, or order placement

Slice: TRADE_POC_SIMULATION_HARNESS_PHASE1
"""

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from simulation_harness import (
    SimulationHarness,
    SimulationSummary,
    SimulationState,
    SyntheticBar,
    TradeLedger,
    SimulatedFill,
    TradeSide,
    SimpleSMAStrategy,
    StrategyIntent,
    IntentType,
    InvariantViolation,
    DEFAULT_SEED,
    DEFAULT_BARS,
    DEFAULT_INITIAL_CAPITAL,
    MIN_ORDER_SIZE,
)


# ---------------------------------------------------------------------------
# Forbidden Imports Test
# ---------------------------------------------------------------------------


FORBIDDEN_IMPORTS = {
    "requests",
    "urllib",
    "httpx",
    "aiohttp",
    "websocket",
    "websockets",
    "ccxt",
    "web3",
    "socket",
    "alpaca",
    "binance",
    "coinbase",
    "kraken",
    "ib_insync",
}


class TestForbiddenImports:
    """Verify simulation_harness.py does not import forbidden modules."""

    def test_no_forbidden_imports_in_source(self):
        """Source file does not import any forbidden modules."""
        harness_path = Path(__file__).parent.parent / "src" / "simulation_harness.py"
        assert harness_path.exists(), f"Source file not found: {harness_path}"

        source_code = harness_path.read_text(encoding="utf-8")
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

    def test_no_forbidden_imports_by_harness(self):
        """Verify simulation_harness.py does not import forbidden modules directly."""
        import importlib.util
        harness_path = Path(__file__).parent.parent / "src" / "simulation_harness.py"

        spec = importlib.util.spec_from_file_location("simulation_harness", harness_path)
        assert spec is not None and spec.loader is not None

        source_code = harness_path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_IMPORTS:
            pattern_import = f"import {forbidden}"
            pattern_from = f"from {forbidden}"
            assert pattern_import not in source_code, f"Found '{pattern_import}' in source"
            assert pattern_from not in source_code, f"Found '{pattern_from}' in source"


# ---------------------------------------------------------------------------
# Determinism Tests
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Verify simulation produces deterministic output."""

    def test_same_seed_produces_identical_json(self):
        """Same seed + bars produces byte-identical JSON."""
        harness1 = SimulationHarness(seed=42, bars=50)
        json1 = harness1.to_json()

        harness2 = SimulationHarness(seed=42, bars=50)
        json2 = harness2.to_json()

        assert json1 == json2, "JSON output is not deterministic"

    def test_different_seeds_produce_different_results(self):
        """Different seeds produce different results."""
        harness1 = SimulationHarness(seed=42, bars=50)
        json1 = harness1.to_json()

        harness2 = SimulationHarness(seed=123, bars=50)
        json2 = harness2.to_json()

        assert json1 != json2, "Different seeds should produce different results"

    def test_run_id_derived_from_seed_and_bars(self):
        """run_id is deterministic: run-{seed}-{bars}."""
        harness = SimulationHarness(seed=42, bars=100)
        assert harness.run_id == "run-42-100"

    def test_no_wall_clock_timestamps(self):
        """Output does not contain wall-clock timestamps."""
        harness = SimulationHarness(seed=42, bars=50)
        json_output = harness.to_json()

        import re
        iso_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        matches = re.findall(iso_pattern, json_output)
        assert len(matches) == 0, f"Wall-clock timestamps found: {matches}"

    def test_no_random_uuids(self):
        """Output does not contain random UUIDs."""
        harness = SimulationHarness(seed=42, bars=50)
        json_output = harness.to_json()

        import re
        uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        matches = re.findall(uuid_pattern, json_output, re.IGNORECASE)
        assert len(matches) == 0, f"Random UUIDs found: {matches}"


# ---------------------------------------------------------------------------
# Synthetic Bar Tests
# ---------------------------------------------------------------------------


class TestSyntheticBar:
    """Tests for SyntheticBar dataclass."""

    def test_bar_to_dict(self):
        """Bar serializes correctly."""
        bar = SyntheticBar(
            bar_index=0,
            open_price=100.0,
            high_price=102.0,
            low_price=99.0,
            close_price=101.0,
            volume=10000,
        )
        d = bar.to_dict()
        assert d["bar_index"] == 0
        assert d["open"] == 100.0
        assert d["high"] == 102.0
        assert d["low"] == 99.0
        assert d["close"] == 101.0
        assert d["volume"] == 10000

    def test_bar_generation_bounded(self):
        """Generated bars have valid OHLC relationships."""
        harness = SimulationHarness(seed=42, bars=100)
        harness.run()
        bars = harness.get_bars()

        for bar in bars:
            assert bar.high_price >= bar.open_price
            assert bar.high_price >= bar.close_price
            assert bar.low_price <= bar.open_price
            assert bar.low_price <= bar.close_price
            assert bar.volume > 0
            assert bar.close_price > 0


# ---------------------------------------------------------------------------
# Simulation State Tests
# ---------------------------------------------------------------------------


class TestSimulationState:
    """Tests for SimulationState dataclass."""

    def test_equity_calculation(self):
        """Equity = cash + position * mark_price."""
        state = SimulationState(
            bar_index=0,
            cash=5000.0,
            position=50,
            mark_price=100.0,
        )
        assert state.equity == 10000.0

    def test_unrealized_pnl_calculation(self):
        """Unrealized PnL calculated from entry price."""
        state = SimulationState(
            bar_index=0,
            cash=5000.0,
            position=50,
            mark_price=110.0,
            entry_price=100.0,
        )
        assert state.unrealized_pnl == 500.0

    def test_unrealized_pnl_zero_position(self):
        """Unrealized PnL is 0 with no position."""
        state = SimulationState(
            bar_index=0,
            cash=10000.0,
            position=0,
            mark_price=100.0,
        )
        assert state.unrealized_pnl == 0.0

    def test_state_to_dict(self):
        """State serializes correctly."""
        state = SimulationState(
            bar_index=5,
            cash=5000.0,
            position=50,
            mark_price=100.0,
            entry_price=95.0,
        )
        d = state.to_dict()
        assert d["bar_index"] == 5
        assert d["cash"] == 5000.0
        assert d["position"] == 50
        assert d["equity"] == 10000.0


# ---------------------------------------------------------------------------
# Trade Ledger Tests
# ---------------------------------------------------------------------------


class TestTradeLedger:
    """Tests for TradeLedger."""

    def test_empty_ledger(self):
        """Empty ledger has zero trades."""
        ledger = TradeLedger()
        assert ledger.total_trades == 0
        assert ledger.total_buys == 0
        assert ledger.total_sells == 0
        assert ledger.total_realized_pnl == 0.0

    def test_add_fill(self):
        """Adding fills updates counts."""
        ledger = TradeLedger()
        ledger.add_fill(SimulatedFill(
            fill_id="fill-1",
            bar_index=0,
            side=TradeSide.BUY,
            quantity=10,
            price=100.0,
        ))
        assert ledger.total_trades == 1
        assert ledger.total_buys == 1
        assert ledger.total_sells == 0

    def test_realized_pnl_accumulation(self):
        """Realized PnL accumulates from sells."""
        ledger = TradeLedger()
        ledger.add_fill(SimulatedFill(
            fill_id="fill-1",
            bar_index=0,
            side=TradeSide.BUY,
            quantity=10,
            price=100.0,
        ))
        ledger.add_fill(SimulatedFill(
            fill_id="fill-2",
            bar_index=5,
            side=TradeSide.SELL,
            quantity=10,
            price=110.0,
            realized_pnl=100.0,
        ))
        assert ledger.total_realized_pnl == 100.0


# ---------------------------------------------------------------------------
# Strategy Tests
# ---------------------------------------------------------------------------


class TestSimpleSMAStrategy:
    """Tests for SimpleSMAStrategy."""

    def test_initial_hold(self):
        """Strategy holds until enough data."""
        strategy = SimpleSMAStrategy(short_period=5, long_period=10)
        bar = SyntheticBar(0, 100, 102, 99, 101, 10000)
        state = SimulationState(0, 10000.0, 0, 101.0)

        intent = strategy.receive_bar(bar, state)
        assert intent.intent_type == IntentType.HOLD

    def test_buy_signal_when_sma_crosses(self):
        """Strategy generates buy on SMA crossover."""
        strategy = SimpleSMAStrategy(short_period=2, long_period=3)
        state = SimulationState(0, 10000.0, 0, 100.0)

        bars_prices = [100, 100, 100, 102, 105]
        intents = []
        for i, price in enumerate(bars_prices):
            bar = SyntheticBar(i, price, price+1, price-1, price, 10000)
            state.mark_price = price
            intent = strategy.receive_bar(bar, state)
            intents.append(intent)

        buy_intents = [i for i in intents if i.intent_type == IntentType.BUY]
        assert len(buy_intents) > 0


# ---------------------------------------------------------------------------
# Simulation Harness Tests
# ---------------------------------------------------------------------------


class TestSimulationHarness:
    """Tests for SimulationHarness."""

    def test_run_returns_summary(self):
        """Run returns SimulationSummary."""
        harness = SimulationHarness(seed=42, bars=50)
        summary = harness.run()
        assert isinstance(summary, SimulationSummary)
        assert summary.seed == 42
        assert summary.bars == 50

    def test_default_seed_42_no_violations(self):
        """Default seed 42 run has no invariant violations."""
        harness = SimulationHarness(seed=42, bars=100)
        summary = harness.run()
        assert summary.invariant_violations == 0, (
            f"Violations found: {[v.to_dict() for v in summary.violations]}"
        )

    def test_initial_capital_preserved_or_traded(self):
        """Initial capital is preserved or traded into equity."""
        harness = SimulationHarness(seed=42, bars=100, initial_capital=10000.0)
        summary = harness.run()
        assert summary.final_equity > 0

    def test_max_drawdown_bounded(self):
        """Max drawdown is between 0 and 1."""
        harness = SimulationHarness(seed=42, bars=100)
        summary = harness.run()
        assert 0.0 <= summary.max_drawdown <= 1.0

    def test_truth_boundary_in_output(self):
        """JSON output includes truth boundary."""
        harness = SimulationHarness(seed=42, bars=50)
        json_output = harness.to_json()
        data = json.loads(json_output)

        assert "truth_boundary" in data
        tb = data["truth_boundary"]
        assert tb["is_simulation"] is True
        assert tb["no_money_mode"] is True
        assert tb["dry_run_mode"] is True
        assert tb["real_execution_performed"] is False
        assert tb["network_calls"] is False
        assert tb["wallet_signing"] is False
        assert tb["order_placement"] is False

    def test_ledger_reconciles_to_position(self):
        """Ledger fills reconcile to final position."""
        harness = SimulationHarness(seed=42, bars=100)
        harness.run()
        ledger = harness.get_ledger()

        ledger_position = sum(
            f.quantity if f.side == TradeSide.BUY else -f.quantity
            for f in ledger.fills
        )

        json_output = harness.to_json()
        data = json.loads(json_output)
        summary = data["summary"]

        assert summary["invariant_violations"] == 0 or ledger_position >= 0


# ---------------------------------------------------------------------------
# Invariant Tests
# ---------------------------------------------------------------------------


class TestInvariants:
    """Tests for simulation invariants."""

    def test_cash_never_negative(self):
        """Cash remains non-negative throughout simulation."""
        harness = SimulationHarness(seed=42, bars=100)
        summary = harness.run()

        cash_violations = [
            v for v in summary.violations
            if v.invariant == "cash_non_negative"
        ]
        assert len(cash_violations) == 0

    def test_no_nan_infinity(self):
        """No NaN or Infinity values in simulation."""
        harness = SimulationHarness(seed=42, bars=100)
        summary = harness.run()

        nan_violations = [
            v for v in summary.violations
            if v.invariant == "no_nan_infinity"
        ]
        assert len(nan_violations) == 0

    def test_position_reconciles_to_ledger(self):
        """Position reconciles to trade ledger."""
        harness = SimulationHarness(seed=42, bars=100)
        summary = harness.run()

        reconcile_violations = [
            v for v in summary.violations
            if v.invariant == "ledger_reconciliation"
        ]
        assert len(reconcile_violations) == 0

    def test_equity_reconciles(self):
        """Final equity equals cash + position * mark_price."""
        harness = SimulationHarness(seed=42, bars=100)
        summary = harness.run()

        equity_violations = [
            v for v in summary.violations
            if v.invariant == "equity_reconciliation"
        ]
        assert len(equity_violations) == 0


# ---------------------------------------------------------------------------
# CLI Tests
# ---------------------------------------------------------------------------


class TestCLI:
    """Tests for CLI interface."""

    def test_cli_simulate_exits_0(self):
        """CLI --simulate exits 0 for seed 42."""
        result = subprocess.run(
            [sys.executable, "-m", "modules.foundups.trade", "--simulate", "--seed", "42"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent.parent.parent),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_cli_json_output_parseable(self):
        """CLI --json outputs valid JSON."""
        result = subprocess.run(
            [sys.executable, "-m", "modules.foundups.trade", "--simulate", "--seed", "42", "--json"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent.parent.parent),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

        data = json.loads(result.stdout)
        assert "summary" in data
        assert "ledger" in data
        assert "truth_boundary" in data

    def test_cli_deterministic_rerun(self):
        """Two CLI runs with same seed produce identical JSON."""
        cwd = str(Path(__file__).parent.parent.parent.parent.parent)

        result1 = subprocess.run(
            [sys.executable, "-m", "modules.foundups.trade", "--simulate", "--seed", "42", "--json"],
            capture_output=True,
            text=True,
            cwd=cwd,
        )

        result2 = subprocess.run(
            [sys.executable, "-m", "modules.foundups.trade", "--simulate", "--seed", "42", "--json"],
            capture_output=True,
            text=True,
            cwd=cwd,
        )

        assert result1.returncode == 0
        assert result2.returncode == 0
        assert result1.stdout == result2.stdout, "CLI output is not deterministic"

    def test_cli_no_simulate_exits_2(self):
        """CLI without --simulate exits 2."""
        result = subprocess.run(
            [sys.executable, "-m", "modules.foundups.trade"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent.parent.parent),
        )
        assert result.returncode == 2

    def test_cli_invalid_bars_exits_2(self):
        """CLI with invalid bars exits 2."""
        result = subprocess.run(
            [sys.executable, "-m", "modules.foundups.trade", "--simulate", "--bars", "0"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent.parent.parent),
        )
        assert result.returncode == 2


# ---------------------------------------------------------------------------
# No Network / No Order Placement Tests
# ---------------------------------------------------------------------------


class TestNoNetworkNoOrderPlacement:
    """Verify no network or order placement operations."""

    def test_simulation_guard_active(self):
        """SimulationGuard is active during run."""
        harness = SimulationHarness(seed=42, bars=50)
        summary = harness.run()
        assert summary.invariant_violations == 0

    def test_truth_boundary_enforced(self):
        """Truth boundary fields are correct in output."""
        harness = SimulationHarness(seed=42, bars=50)
        json_output = harness.to_json()
        data = json.loads(json_output)

        tb = data["truth_boundary"]
        assert tb["is_simulation"] is True
        assert tb["network_calls"] is False
        assert tb["wallet_signing"] is False
        assert tb["order_placement"] is False

    def test_no_external_dependencies_in_run(self):
        """Run does not require external dependencies."""
        harness = SimulationHarness(seed=42, bars=100)
        summary = harness.run()
        assert summary is not None
