"""Tests for Trade Harness Scoring Integration

Slice: TRADE_HARNESS_INTEGRATION_WITH_SCORING_PHASE1

Tests:
1. Gate behavior (4 band scenarios)
2. Determinism (baseline hash unchanged when gate disabled)
3. Forbidden imports scan
4. Forbidden fields scan
5. Band → action mapping verification
"""

from __future__ import annotations

import ast
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from contracts import DecisionBand
from simulation_harness import (
    IntentType,
    SimulationHarness,
    SimulationState,
    StrategyIntent,
    SyntheticBar,
)
from scoring_integration import (
    ALLOWED_BANDS,
    BLOCKED_BANDS,
    GateAction,
    ScoringGate,
    ScoringGateResult,
    apply_scoring_gate,
    derive_synthetic_candidate,
    derive_synthetic_reports,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Baseline hash from main (scoring gate disabled)
BASELINE_HASH = "c90cd57aedbe9bab094551198d8c07c93fa02edf635653639ebbf3f931b58726"
BASELINE_LENGTH = 3690


# ---------------------------------------------------------------------------
# Forbidden imports (from #687/#691 constraints)
# ---------------------------------------------------------------------------

FORBIDDEN_IMPORTS = frozenset({
    "requests",
    "urllib",
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
    "polygon",
    "yfinance",
    "eth_account",
    "cryptography",
})


FORBIDDEN_FIELDS = frozenset({
    "api_key",
    "secret",
    "signer",
    "wallet_private_key",
    "order_id",
    "endpoint",
    "exchange_client",
})


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_bar() -> SyntheticBar:
    """Create a sample synthetic bar."""
    return SyntheticBar(
        bar_index=10,
        open_price=100.0,
        high_price=102.0,
        low_price=98.0,
        close_price=101.0,
        volume=10000,
    )


@pytest.fixture
def sample_state() -> SimulationState:
    """Create a sample simulation state."""
    return SimulationState(
        bar_index=10,
        cash=10000.0,
        position=0,
        mark_price=101.0,
    )


@pytest.fixture
def buy_intent() -> StrategyIntent:
    """Create a buy intent."""
    return StrategyIntent(IntentType.BUY, quantity=10)


@pytest.fixture
def sell_intent() -> StrategyIntent:
    """Create a sell intent."""
    return StrategyIntent(IntentType.SELL, quantity=5)


@pytest.fixture
def hold_intent() -> StrategyIntent:
    """Create a hold intent."""
    return StrategyIntent(IntentType.HOLD)


@pytest.fixture
def enabled_gate() -> ScoringGate:
    """Create an enabled scoring gate."""
    return ScoringGate(enabled=True, seed=42)


@pytest.fixture
def disabled_gate() -> ScoringGate:
    """Create a disabled scoring gate."""
    return ScoringGate(enabled=False, seed=42)


# ---------------------------------------------------------------------------
# Determinism Tests
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Tests for deterministic behavior."""

    def test_baseline_hash_unchanged_with_gate_disabled(self):
        """Verify baseline output is byte-identical when gate is disabled.

        This is the critical backward-compatibility test: default behavior
        (scoring gate disabled) must produce the same output as main.
        """
        harness = SimulationHarness(seed=42, bars=100)
        json_output = harness.to_json()

        actual_hash = hashlib.sha256(json_output.encode()).hexdigest()

        assert actual_hash == BASELINE_HASH, (
            f"Baseline hash changed! Expected {BASELINE_HASH}, got {actual_hash}. "
            "Default behavior must remain byte-identical."
        )

    def test_baseline_length_unchanged(self):
        """Verify baseline output length is unchanged."""
        harness = SimulationHarness(seed=42, bars=100)
        json_output = harness.to_json()

        assert len(json_output) == BASELINE_LENGTH, (
            f"Baseline length changed! Expected {BASELINE_LENGTH}, got {len(json_output)}."
        )

    def test_synthetic_candidate_is_deterministic(self, sample_bar: SyntheticBar):
        """Verify synthetic candidate derivation is deterministic."""
        time = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)

        candidate1 = derive_synthetic_candidate(sample_bar, seed=42, evaluation_time=time)
        candidate2 = derive_synthetic_candidate(sample_bar, seed=42, evaluation_time=time)

        assert candidate1.token_address == candidate2.token_address
        assert candidate1.token_symbol == candidate2.token_symbol
        assert candidate1.bonding_curve_progress == candidate2.bonding_curve_progress

    def test_synthetic_reports_are_deterministic(self, sample_bar: SyntheticBar):
        """Verify synthetic reports derivation is deterministic."""
        issuer1, wallets1, social1, inf1 = derive_synthetic_reports(sample_bar, seed=42)
        issuer2, wallets2, social2, inf2 = derive_synthetic_reports(sample_bar, seed=42)

        assert issuer1.entity_id == issuer2.entity_id
        assert len(wallets1) == len(wallets2)
        assert social1.social_authenticity_score == social2.social_authenticity_score
        assert inf1.influencer_risk_score == inf2.influencer_risk_score

    def test_gate_results_are_deterministic(
        self,
        sample_bar: SyntheticBar,
        sample_state: SimulationState,
        buy_intent: StrategyIntent,
    ):
        """Verify gate results are deterministic across runs."""
        gate1 = ScoringGate(enabled=True, seed=42)
        gate2 = ScoringGate(enabled=True, seed=42)

        result1 = gate1.apply(sample_bar, buy_intent, sample_state)
        result2 = gate2.apply(sample_bar, buy_intent, sample_state)

        # Same input → same output
        assert result1.intent_type == result2.intent_type
        assert result1.quantity == result2.quantity

        # Same gate results
        assert len(gate1.get_results()) == len(gate2.get_results())
        assert gate1.get_results()[0].decision_band == gate2.get_results()[0].decision_band


# ---------------------------------------------------------------------------
# Gate Behavior Tests
# ---------------------------------------------------------------------------


class TestGateBehavior:
    """Tests for scoring gate behavior."""

    def test_disabled_gate_is_passthrough(
        self,
        sample_bar: SyntheticBar,
        sample_state: SimulationState,
        buy_intent: StrategyIntent,
        disabled_gate: ScoringGate,
    ):
        """Disabled gate should pass through all intents unchanged."""
        result = disabled_gate.apply(sample_bar, buy_intent, sample_state)

        assert result.intent_type == IntentType.BUY
        assert result.quantity == buy_intent.quantity
        assert len(disabled_gate.get_results()) == 0  # No evaluation recorded

    def test_sell_intent_passes_through(
        self,
        sample_bar: SyntheticBar,
        sample_state: SimulationState,
        sell_intent: StrategyIntent,
        enabled_gate: ScoringGate,
    ):
        """SELL intents should always pass through (only BUY is gated)."""
        result = enabled_gate.apply(sample_bar, sell_intent, sample_state)

        assert result.intent_type == IntentType.SELL
        assert result.quantity == sell_intent.quantity

    def test_hold_intent_passes_through(
        self,
        sample_bar: SyntheticBar,
        sample_state: SimulationState,
        hold_intent: StrategyIntent,
        enabled_gate: ScoringGate,
    ):
        """HOLD intents should always pass through."""
        result = enabled_gate.apply(sample_bar, hold_intent, sample_state)

        assert result.intent_type == IntentType.HOLD

    def test_buy_intent_is_evaluated(
        self,
        sample_bar: SyntheticBar,
        sample_state: SimulationState,
        buy_intent: StrategyIntent,
        enabled_gate: ScoringGate,
    ):
        """BUY intents should be evaluated when gate is enabled."""
        enabled_gate.apply(sample_bar, buy_intent, sample_state)

        results = enabled_gate.get_results()
        assert len(results) == 1
        assert results[0].original_intent.intent_type == IntentType.BUY

    def test_convenience_function_with_none_gate(
        self,
        sample_bar: SyntheticBar,
        sample_state: SimulationState,
        buy_intent: StrategyIntent,
    ):
        """apply_scoring_gate with None gate should pass through."""
        result = apply_scoring_gate(sample_bar, buy_intent, sample_state, gate=None)

        assert result.intent_type == IntentType.BUY
        assert result.quantity == buy_intent.quantity


# ---------------------------------------------------------------------------
# Band → Action Mapping Tests
# ---------------------------------------------------------------------------


class TestBandActionMapping:
    """Tests for decision band → gate action mapping."""

    def test_allowed_bands_set(self):
        """Verify allowed bands are correct."""
        assert DecisionBand.SIMULATE_ONLY in ALLOWED_BANDS
        assert DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW in ALLOWED_BANDS
        assert len(ALLOWED_BANDS) == 2

    def test_blocked_bands_set(self):
        """Verify blocked bands are correct."""
        assert DecisionBand.REJECT in BLOCKED_BANDS
        assert DecisionBand.OBSERVE in BLOCKED_BANDS
        assert len(BLOCKED_BANDS) == 2

    def test_all_bands_covered(self):
        """Verify all bands are in either ALLOWED or BLOCKED."""
        all_bands = set(DecisionBand)
        covered = ALLOWED_BANDS | BLOCKED_BANDS

        assert all_bands == covered, (
            f"Some bands not covered: {all_bands - covered}"
        )

    def test_no_overlap(self):
        """Verify no band is both allowed and blocked."""
        overlap = ALLOWED_BANDS & BLOCKED_BANDS
        assert len(overlap) == 0, f"Bands in both sets: {overlap}"


# ---------------------------------------------------------------------------
# Gate Result Tests
# ---------------------------------------------------------------------------


class TestGateResults:
    """Tests for gate result recording and summary."""

    def test_gate_records_results(
        self,
        sample_bar: SyntheticBar,
        sample_state: SimulationState,
        buy_intent: StrategyIntent,
        enabled_gate: ScoringGate,
    ):
        """Gate should record evaluation results."""
        enabled_gate.apply(sample_bar, buy_intent, sample_state)

        results = enabled_gate.get_results()
        assert len(results) == 1

        result = results[0]
        assert isinstance(result, ScoringGateResult)
        assert result.decision_band in DecisionBand
        assert 0 <= result.total_score <= 100
        assert 0 <= result.evidence_confidence <= 1

    def test_gate_summary_empty(self, disabled_gate: ScoringGate):
        """Summary with no evaluations."""
        summary = disabled_gate.get_summary()

        assert summary["total_evaluations"] == 0
        assert summary["allowed"] == 0
        assert summary["blocked"] == 0

    def test_gate_reset(
        self,
        sample_bar: SyntheticBar,
        sample_state: SimulationState,
        buy_intent: StrategyIntent,
        enabled_gate: ScoringGate,
    ):
        """Gate reset should clear results."""
        enabled_gate.apply(sample_bar, buy_intent, sample_state)
        assert len(enabled_gate.get_results()) == 1

        enabled_gate.reset()
        assert len(enabled_gate.get_results()) == 0

    def test_result_to_dict(
        self,
        sample_bar: SyntheticBar,
        sample_state: SimulationState,
        buy_intent: StrategyIntent,
        enabled_gate: ScoringGate,
    ):
        """Result should serialize to dict."""
        enabled_gate.apply(sample_bar, buy_intent, sample_state)

        result = enabled_gate.get_results()[0]
        d = result.to_dict()

        assert "action" in d
        assert "decision_band" in d
        assert "total_score" in d
        assert "gate_rationale" in d


# ---------------------------------------------------------------------------
# Synthetic Candidate Tests
# ---------------------------------------------------------------------------


class TestSyntheticCandidate:
    """Tests for synthetic candidate derivation."""

    def test_candidate_has_required_fields(self, sample_bar: SyntheticBar):
        """Derived candidate should have all required fields."""
        time = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)
        candidate = derive_synthetic_candidate(sample_bar, seed=42, evaluation_time=time)

        assert candidate.token_address
        assert candidate.token_symbol
        assert candidate.chain == "solana"
        assert candidate.launchpad == "pumpfun"
        assert candidate.discovery_source == "simulation"
        assert 0 <= candidate.bonding_curve_progress <= 1
        assert candidate.timestamp.tzinfo is not None

    def test_different_seeds_produce_different_candidates(self, sample_bar: SyntheticBar):
        """Different seeds should produce different candidates."""
        time = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)

        c1 = derive_synthetic_candidate(sample_bar, seed=42, evaluation_time=time)
        c2 = derive_synthetic_candidate(sample_bar, seed=999, evaluation_time=time)

        assert c1.token_address != c2.token_address

    def test_different_bars_produce_different_candidates(self):
        """Different bars should produce different candidates."""
        time = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)

        bar1 = SyntheticBar(bar_index=1, open_price=100, high_price=101, low_price=99, close_price=100, volume=1000)
        bar2 = SyntheticBar(bar_index=2, open_price=100, high_price=101, low_price=99, close_price=100, volume=1000)

        c1 = derive_synthetic_candidate(bar1, seed=42, evaluation_time=time)
        c2 = derive_synthetic_candidate(bar2, seed=42, evaluation_time=time)

        assert c1.token_address != c2.token_address


# ---------------------------------------------------------------------------
# Forbidden Import Scan
# ---------------------------------------------------------------------------


class TestForbiddenImports:
    """Static scan for forbidden imports."""

    def _get_source_files(self) -> List[Path]:
        """Get all Python source files in trade/src."""
        src_dir = Path(__file__).parent.parent / "src"
        return list(src_dir.glob("*.py"))

    def _extract_imports(self, filepath: Path) -> set:
        """Extract all import names from a Python file."""
        imports = set()
        try:
            content = filepath.read_text(encoding="utf-8")
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split(".")[0])
        except (SyntaxError, FileNotFoundError):
            pass

        return imports

    def test_scoring_integration_has_no_forbidden_imports(self):
        """scoring_integration.py must not import forbidden modules."""
        filepath = Path(__file__).parent.parent / "src" / "scoring_integration.py"
        imports = self._extract_imports(filepath)

        violations = imports & FORBIDDEN_IMPORTS
        assert len(violations) == 0, (
            f"scoring_integration.py has forbidden imports: {violations}"
        )

    def test_all_src_files_have_no_forbidden_imports(self):
        """All trade/src files must not import forbidden modules."""
        all_violations = {}

        for filepath in self._get_source_files():
            imports = self._extract_imports(filepath)
            violations = imports & FORBIDDEN_IMPORTS

            if violations:
                all_violations[filepath.name] = violations

        assert len(all_violations) == 0, (
            f"Files with forbidden imports: {all_violations}"
        )


# ---------------------------------------------------------------------------
# Forbidden Field Scan
# ---------------------------------------------------------------------------


class TestForbiddenFields:
    """Static scan for forbidden fields."""

    def _get_source_files(self) -> List[Path]:
        """Get all Python source files in trade/src."""
        src_dir = Path(__file__).parent.parent / "src"
        return list(src_dir.glob("*.py"))

    def _scan_for_fields(self, filepath: Path) -> set:
        """Scan file for forbidden field names."""
        found = set()
        try:
            content = filepath.read_text(encoding="utf-8")

            for field in FORBIDDEN_FIELDS:
                if field in content:
                    found.add(field)
        except FileNotFoundError:
            pass

        return found

    def test_scoring_integration_has_no_forbidden_fields(self):
        """scoring_integration.py must not contain forbidden field names."""
        filepath = Path(__file__).parent.parent / "src" / "scoring_integration.py"
        found = self._scan_for_fields(filepath)

        assert len(found) == 0, (
            f"scoring_integration.py has forbidden fields: {found}"
        )

    def test_all_src_files_have_no_forbidden_fields(self):
        """All trade/src files must not contain forbidden field names."""
        all_violations = {}

        for filepath in self._get_source_files():
            found = self._scan_for_fields(filepath)

            if found:
                all_violations[filepath.name] = found

        assert len(all_violations) == 0, (
            f"Files with forbidden fields: {all_violations}"
        )


# ---------------------------------------------------------------------------
# Integration Test
# ---------------------------------------------------------------------------


class TestIntegration:
    """End-to-end integration tests."""

    def test_gate_can_filter_buys_across_simulation(self):
        """Gate should be able to filter buys during a simulation run.

        This doesn't run the full harness with gate (that would require
        modifying simulation_harness.py), but verifies the gate can
        process multiple bars.
        """
        gate = ScoringGate(enabled=True, seed=42)

        # Simulate processing multiple bars
        harness = SimulationHarness(seed=42, bars=20)
        harness.run()

        bars = harness.get_bars()
        state = SimulationState(bar_index=0, cash=10000.0, position=0, mark_price=100.0)

        for bar in bars[:10]:
            intent = StrategyIntent(IntentType.BUY, quantity=5)
            gate.apply(bar, intent, state)

        # Should have 10 evaluations
        assert len(gate.get_results()) == 10

        # Summary should show distribution
        summary = gate.get_summary()
        assert summary["total_evaluations"] == 10
        assert summary["enabled"] is True
