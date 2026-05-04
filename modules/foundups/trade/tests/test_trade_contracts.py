"""Trade FoundUp Contract Tests

Tests for typed contracts in src/contracts.py.

WSP References:
- WSP 97: Truth Boundaries (all execution fields False)
- WSP 11: Interface Protocol (contracts serialize correctly)
"""
import json
from datetime import datetime, timezone

import pytest

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from contracts import (
    TruthFields,
    MarketAdapterSpec,
    LaunchpadAdapterSpec,
    AdapterStatus,
    MarketEvent,
    TokenEvent,
    WalletEvent,
    SocialEvent,
    RiskEvent,
    TradeSignal,
    ExitSignal,
    ProofMetric,
    SimulationResult,
    ExecutionGuardPolicy,
    UnsupportedOperationError,
    DEFAULT_TRUTH_FIELDS,
    DEFAULT_EXECUTION_GUARD,
)


class TestTruthFields:
    """WSP 97 truth fields must default to no-execution state."""

    def test_default_dry_run_mode_true(self):
        """dry_run_mode defaults to True."""
        tf = TruthFields()
        assert tf.dry_run_mode is True

    def test_default_no_money_mode_true(self):
        """no_money_mode defaults to True."""
        tf = TruthFields()
        assert tf.no_money_mode is True

    def test_default_real_execution_performed_false(self):
        """real_execution_performed defaults to False."""
        tf = TruthFields()
        assert tf.real_execution_performed is False

    def test_default_verification_complete_false(self):
        """verification_complete defaults to False."""
        tf = TruthFields()
        assert tf.verification_complete is False

    def test_default_cabr_ready_false(self):
        """cabr_ready defaults to False."""
        tf = TruthFields()
        assert tf.cabr_ready is False

    def test_default_payout_ready_false(self):
        """payout_ready defaults to False."""
        tf = TruthFields()
        assert tf.payout_ready is False

    def test_assert_no_execution_passes_on_defaults(self):
        """assert_no_execution passes with default values."""
        tf = TruthFields()
        # Should not raise
        tf.assert_no_execution()

    def test_assert_no_execution_fails_on_real_execution(self):
        """assert_no_execution fails if real_execution_performed is True."""
        tf = TruthFields(real_execution_performed=True)
        with pytest.raises(AssertionError):
            tf.assert_no_execution()

    def test_to_dict_serializes_all_fields(self):
        """to_dict includes all truth fields."""
        tf = TruthFields()
        d = tf.to_dict()
        assert "dry_run_mode" in d
        assert "no_money_mode" in d
        assert "real_execution_performed" in d
        assert "verification_complete" in d
        assert "cabr_ready" in d
        assert "payout_ready" in d


class TestExecutionGuardPolicy:
    """Execution guard must block all execution operations."""

    def test_default_no_money_mode_true(self):
        """no_money_mode defaults to True."""
        guard = ExecutionGuardPolicy()
        assert guard.no_money_mode is True

    def test_default_dry_run_mode_true(self):
        """dry_run_mode defaults to True."""
        guard = ExecutionGuardPolicy()
        assert guard.dry_run_mode is True

    def test_block_real_trades(self):
        """Real trades are blocked."""
        guard = ExecutionGuardPolicy()
        with pytest.raises(UnsupportedOperationError):
            guard.assert_operation_allowed("real_trade")

    def test_block_wallet_signing(self):
        """Wallet signing is blocked."""
        guard = ExecutionGuardPolicy()
        with pytest.raises(UnsupportedOperationError):
            guard.assert_operation_allowed("wallet_sign")

    def test_block_private_key_access(self):
        """Private key access is blocked."""
        guard = ExecutionGuardPolicy()
        with pytest.raises(UnsupportedOperationError):
            guard.assert_operation_allowed("private_key_access")

    def test_block_order_placement(self):
        """Order placement is blocked."""
        guard = ExecutionGuardPolicy()
        with pytest.raises(UnsupportedOperationError):
            guard.assert_operation_allowed("order_place")

    def test_block_capital_deployment(self):
        """Capital deployment is blocked."""
        guard = ExecutionGuardPolicy()
        with pytest.raises(UnsupportedOperationError):
            guard.assert_operation_allowed("capital_deploy")

    def test_block_wash_trading(self):
        """Wash trading is blocked."""
        guard = ExecutionGuardPolicy()
        with pytest.raises(UnsupportedOperationError):
            guard.assert_operation_allowed("wash_trade")

    def test_block_market_manipulation(self):
        """Market manipulation is blocked."""
        guard = ExecutionGuardPolicy()
        with pytest.raises(UnsupportedOperationError):
            guard.assert_operation_allowed("market_manipulate")

    def test_block_bot_concealment(self):
        """Bot concealment is blocked."""
        guard = ExecutionGuardPolicy()
        with pytest.raises(UnsupportedOperationError):
            guard.assert_operation_allowed("conceal_bot")

    def test_block_fake_volume(self):
        """Fake volume is blocked."""
        guard = ExecutionGuardPolicy()
        with pytest.raises(UnsupportedOperationError):
            guard.assert_operation_allowed("fake_volume")

    def test_unknown_operation_passes(self):
        """Unknown operations pass (not in block list)."""
        guard = ExecutionGuardPolicy()
        # Should not raise
        guard.assert_operation_allowed("unknown_operation")

    def test_to_dict_serializes(self):
        """to_dict serializes all fields."""
        guard = ExecutionGuardPolicy()
        d = guard.to_dict()
        assert d["no_money_mode"] is True
        assert d["dry_run_mode"] is True
        assert d["block_real_trades"] is True


class TestAdapterSpecs:
    """Adapter specs must serialize correctly."""

    def test_market_adapter_spec_to_dict(self):
        """MarketAdapterSpec serializes to dict."""
        spec = MarketAdapterSpec(
            adapter_id="solana",
            chain_or_exchange="solana",
            display_name="Solana",
            status=AdapterStatus.PLANNED,
        )
        d = spec.to_dict()
        assert d["adapter_id"] == "solana"
        assert d["status"] == "planned"
        assert d["live_execution_enabled"] is False

    def test_launchpad_adapter_spec_to_dict(self):
        """LaunchpadAdapterSpec serializes to dict."""
        spec = LaunchpadAdapterSpec(
            adapter_id="pumpfun",
            platform_name="pump.fun",
            chain="solana",
            display_name="Pump.fun",
            status=AdapterStatus.PLANNED,
        )
        d = spec.to_dict()
        assert d["adapter_id"] == "pumpfun"
        assert d["platform_name"] == "pump.fun"
        assert d["live_execution_enabled"] is False

    def test_adapter_live_execution_default_false(self):
        """live_execution_enabled defaults to False."""
        market = MarketAdapterSpec(
            adapter_id="test",
            chain_or_exchange="test",
            display_name="Test",
        )
        launchpad = LaunchpadAdapterSpec(
            adapter_id="test",
            platform_name="test",
            chain="test",
            display_name="Test",
        )
        assert market.live_execution_enabled is False
        assert launchpad.live_execution_enabled is False


class TestEventSchemas:
    """Event schemas must serialize to dict/JSON."""

    def test_market_event_to_dict(self):
        """MarketEvent serializes to dict."""
        event = MarketEvent(
            event_id="evt_123",
            event_type="price_update",
            adapter_id="solana",
            chain="solana",
            price_usd=0.001,
        )
        d = event.to_dict()
        assert d["event_id"] == "evt_123"
        assert d["price_usd"] == 0.001
        assert "timestamp" in d

    def test_token_event_to_dict(self):
        """TokenEvent serializes to dict."""
        event = TokenEvent(
            event_id="evt_456",
            event_type="token_created",
            adapter_id="pumpfun",
            chain="solana",
            token_symbol="MEME",
        )
        d = event.to_dict()
        assert d["token_symbol"] == "MEME"

    def test_wallet_event_to_dict(self):
        """WalletEvent serializes to dict."""
        event = WalletEvent(
            event_id="evt_789",
            event_type="buy",
            adapter_id="solana",
            chain="solana",
            wallet_cluster_id="cluster_abc",
        )
        d = event.to_dict()
        assert d["wallet_cluster_id"] == "cluster_abc"

    def test_social_event_to_dict(self):
        """SocialEvent serializes to dict."""
        event = SocialEvent(
            event_id="evt_social",
            event_type="mention",
            source="twitter",
            sentiment_score=0.8,
        )
        d = event.to_dict()
        assert d["sentiment_score"] == 0.8

    def test_risk_event_to_dict(self):
        """RiskEvent serializes to dict."""
        event = RiskEvent(
            event_id="evt_risk",
            event_type="honeypot_detected",
            overall_risk_score=0.95,
            is_honeypot=True,
        )
        d = event.to_dict()
        assert d["overall_risk_score"] == 0.95
        assert d["is_honeypot"] is True


class TestSignalSchemas:
    """Signal schemas must default to simulation mode."""

    def test_trade_signal_is_simulation_default_true(self):
        """TradeSignal.is_simulation defaults to True."""
        signal = TradeSignal(
            signal_id="sig_123",
            signal_type="entry",
        )
        assert signal.is_simulation is True

    def test_exit_signal_is_simulation_default_true(self):
        """ExitSignal.is_simulation defaults to True."""
        signal = ExitSignal(
            signal_id="sig_456",
            signal_type="exit",
        )
        assert signal.is_simulation is True

    def test_trade_signal_to_dict(self):
        """TradeSignal serializes to dict."""
        signal = TradeSignal(
            signal_id="sig_123",
            signal_type="entry",
            confidence=0.85,
        )
        d = signal.to_dict()
        assert d["confidence"] == 0.85
        assert d["is_simulation"] is True

    def test_exit_signal_to_dict(self):
        """ExitSignal serializes to dict."""
        signal = ExitSignal(
            signal_id="sig_456",
            signal_type="stop_loss",
            urgency="critical",
        )
        d = signal.to_dict()
        assert d["urgency"] == "critical"


class TestProofSchemas:
    """Proof schemas must serialize correctly."""

    def test_proof_metric_to_dict(self):
        """ProofMetric serializes to dict."""
        metric = ProofMetric(
            metric_id="metric_123",
            metric_type="detection_latency",
            value=150.0,
            unit="ms",
            category="latency",
        )
        d = metric.to_dict()
        assert d["value"] == 150.0
        assert d["unit"] == "ms"

    def test_simulation_result_default_no_real_capital(self):
        """SimulationResult.real_capital_used defaults to False."""
        result = SimulationResult(
            simulation_id="sim_123",
        )
        assert result.real_capital_used is False
        assert result.is_simulation is True

    def test_simulation_result_to_dict(self):
        """SimulationResult serializes to dict."""
        result = SimulationResult(
            simulation_id="sim_123",
            total_trades=100,
            win_rate=0.55,
            simulated_pnl_percent=25.0,
        )
        d = result.to_dict()
        assert d["win_rate"] == 0.55
        assert d["real_capital_used"] is False


class TestJsonSerialization:
    """All contracts must serialize to valid JSON."""

    def test_truth_fields_json(self):
        """TruthFields serializes to valid JSON."""
        tf = TruthFields()
        json_str = json.dumps(tf.to_dict())
        assert json.loads(json_str)

    def test_execution_guard_json(self):
        """ExecutionGuardPolicy serializes to valid JSON."""
        guard = ExecutionGuardPolicy()
        json_str = json.dumps(guard.to_dict())
        assert json.loads(json_str)

    def test_market_event_json(self):
        """MarketEvent serializes to valid JSON."""
        event = MarketEvent(
            event_id="test",
            event_type="test",
            adapter_id="test",
            chain="test",
        )
        json_str = json.dumps(event.to_dict())
        assert json.loads(json_str)

    def test_simulation_result_json(self):
        """SimulationResult serializes to valid JSON."""
        result = SimulationResult(simulation_id="test")
        json_str = json.dumps(result.to_dict())
        assert json.loads(json_str)


class TestDefaultInstances:
    """Default instances must have correct values."""

    def test_default_truth_fields(self):
        """DEFAULT_TRUTH_FIELDS has correct values."""
        assert DEFAULT_TRUTH_FIELDS.dry_run_mode is True
        assert DEFAULT_TRUTH_FIELDS.no_money_mode is True
        assert DEFAULT_TRUTH_FIELDS.real_execution_performed is False

    def test_default_execution_guard(self):
        """DEFAULT_EXECUTION_GUARD blocks execution."""
        with pytest.raises(UnsupportedOperationError):
            DEFAULT_EXECUTION_GUARD.assert_operation_allowed("real_trade")
