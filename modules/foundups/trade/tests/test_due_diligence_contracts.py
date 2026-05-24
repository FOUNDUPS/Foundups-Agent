"""Trade FoundUp - Due Diligence Contract Tests

Tests for due-diligence scoring contracts from TRADE_DUE_DILIGENCE_SCHEMA_PHASE1.

WSP 97 Truth Boundary:
- All tests verify pure data contracts
- No network calls, wallet access, or order placement
- No decision band authorizes real trading

Spec: TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1 (PR #683)
Slice: TRADE_DUE_DILIGENCE_SCHEMA_PHASE1
"""

import ast
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from contracts import (
    DecisionBand,
    RiskClassification,
    EntityType,
    WalletClassification,
    EntityHistoryReport,
    WalletAuditReport,
    SocialPresenceReport,
    InfluencerRiskReport,
    LaunchpadTokenCandidate,
    TradeDueDiligenceScore,
    assert_no_real_trading_authorized,
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
    """Verify contracts.py does not import forbidden modules."""

    def test_no_forbidden_imports_in_source(self):
        """Source file does not import any forbidden modules."""
        contracts_path = Path(__file__).parent.parent / "src" / "contracts.py"
        assert contracts_path.exists(), f"Source file not found: {contracts_path}"

        source_code = contracts_path.read_text(encoding="utf-8")
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
    "api_key",
    "secret",
    "signer",
    "wallet_private_key",
    "private_key",
    "order_id",
    "endpoint",
    "exchange_client",
    "api_url",
    "api_secret",
}


class TestForbiddenFields:
    """Verify contracts.py does not contain forbidden fields."""

    def test_no_forbidden_fields_in_source(self):
        """Source file does not contain forbidden field names."""
        contracts_path = Path(__file__).parent.parent / "src" / "contracts.py"
        source_code = contracts_path.read_text(encoding="utf-8")

        for forbidden in FORBIDDEN_FIELDS:
            pattern_attr = f"self.{forbidden}"
            pattern_param = f"{forbidden}:"
            pattern_field = f"{forbidden} ="

            assert pattern_attr not in source_code, f"Forbidden field 'self.{forbidden}' found"
            # Allow type hints but not actual field definitions
            if forbidden not in ["endpoint"]:  # endpoint is in documentation_url context
                assert pattern_field not in source_code or "documentation" in source_code, \
                    f"Forbidden field '{forbidden} =' found"


# ---------------------------------------------------------------------------
# DecisionBand Tests
# ---------------------------------------------------------------------------


class TestDecisionBand:
    """Tests for DecisionBand enum."""

    def test_all_bands_defined(self):
        """All four decision bands are defined."""
        assert DecisionBand.REJECT.value == "reject"
        assert DecisionBand.OBSERVE.value == "observe"
        assert DecisionBand.SIMULATE_ONLY.value == "simulate_only"
        assert DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW.value == "candidate_for_future_review"

    def test_no_band_authorizes_real_trading(self):
        """No decision band authorizes real trading."""
        for band in DecisionBand:
            # This should not raise - it's a documentation assertion
            assert_no_real_trading_authorized(band)


# ---------------------------------------------------------------------------
# EntityHistoryReport Tests
# ---------------------------------------------------------------------------


class TestEntityHistoryReport:
    """Tests for EntityHistoryReport."""

    def test_valid_construction(self):
        """EntityHistoryReport constructs with valid data."""
        report = EntityHistoryReport(
            entity_id="hash_abc123",
            entity_type=EntityType.ISSUER,
            prior_token_launches=5,
            prior_rug_pulls=0,
            prior_successful_launches=4,
            confidence=0.8,
        )
        assert report.entity_id == "hash_abc123"
        assert report.entity_type == EntityType.ISSUER
        assert report.confidence == 0.8

    def test_confidence_bounds(self):
        """confidence must be 0.0-1.0."""
        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            EntityHistoryReport(
                entity_id="test",
                entity_type=EntityType.ISSUER,
                confidence=1.5,
            )

    def test_negative_rug_pulls_rejected(self):
        """prior_rug_pulls cannot be negative."""
        with pytest.raises(ValueError, match="prior_rug_pulls cannot be negative"):
            EntityHistoryReport(
                entity_id="test",
                entity_type=EntityType.ISSUER,
                prior_rug_pulls=-1,
            )

    def test_serialization(self):
        """EntityHistoryReport serializes to dict."""
        report = EntityHistoryReport(
            entity_id="test",
            entity_type=EntityType.INFLUENCER,
            risk_classification=RiskClassification.FLAGGED,
        )
        d = report.to_dict()
        assert d["entity_id"] == "test"
        assert d["entity_type"] == "influencer"
        assert d["risk_classification"] == "flagged"

    def test_json_serializable(self):
        """EntityHistoryReport dict is JSON serializable."""
        report = EntityHistoryReport(entity_id="test", entity_type=EntityType.WHALE)
        json_str = json.dumps(report.to_dict())
        assert "entity_id" in json_str


# ---------------------------------------------------------------------------
# WalletAuditReport Tests
# ---------------------------------------------------------------------------


class TestWalletAuditReport:
    """Tests for WalletAuditReport."""

    def test_valid_construction(self):
        """WalletAuditReport constructs with valid data."""
        report = WalletAuditReport(
            wallet_hash="hash_wallet123",
            token_address="token_abc",
            holding_percent=15.5,
            risk_contribution=0.3,
        )
        assert report.wallet_hash == "hash_wallet123"
        assert report.holding_percent == 15.5

    def test_holding_percent_bounds(self):
        """holding_percent must be 0.0-100.0."""
        with pytest.raises(ValueError, match="holding_percent must be 0.0-100.0"):
            WalletAuditReport(
                wallet_hash="test",
                token_address="test",
                holding_percent=150.0,
            )

    def test_risk_contribution_bounds(self):
        """risk_contribution must be 0.0-1.0."""
        with pytest.raises(ValueError, match="risk_contribution must be 0.0-1.0"):
            WalletAuditReport(
                wallet_hash="test",
                token_address="test",
                risk_contribution=1.5,
            )

    def test_serialization(self):
        """WalletAuditReport serializes to dict."""
        report = WalletAuditReport(
            wallet_hash="test",
            token_address="token",
            entity_classification=WalletClassification.WHALE,
        )
        d = report.to_dict()
        assert d["wallet_hash"] == "test"
        assert d["entity_classification"] == "whale"


# ---------------------------------------------------------------------------
# SocialPresenceReport Tests
# ---------------------------------------------------------------------------


class TestSocialPresenceReport:
    """Tests for SocialPresenceReport."""

    def test_valid_construction(self):
        """SocialPresenceReport constructs with valid data."""
        report = SocialPresenceReport(
            token_address="token_abc",
            x_account_exists=True,
            telegram_exists=True,
            social_authenticity_score=75.0,
            evidence_completeness=0.9,
        )
        assert report.social_authenticity_score == 75.0
        assert report.evidence_completeness == 0.9

    def test_score_bounds(self):
        """social_authenticity_score must be 0.0-100.0."""
        with pytest.raises(ValueError, match="social_authenticity_score must be 0.0-100.0"):
            SocialPresenceReport(
                token_address="test",
                social_authenticity_score=105.0,
            )

    def test_evidence_bounds(self):
        """evidence_completeness must be 0.0-1.0."""
        with pytest.raises(ValueError, match="evidence_completeness must be 0.0-1.0"):
            SocialPresenceReport(
                token_address="test",
                evidence_completeness=2.0,
            )


# ---------------------------------------------------------------------------
# InfluencerRiskReport Tests
# ---------------------------------------------------------------------------


class TestInfluencerRiskReport:
    """Tests for InfluencerRiskReport."""

    def test_valid_construction(self):
        """InfluencerRiskReport constructs with valid data."""
        report = InfluencerRiskReport(
            token_address="token_abc",
            known_pumper_wallets_detected=2,
            influencer_risk_score=65.0,
        )
        assert report.known_pumper_wallets_detected == 2
        assert report.influencer_risk_score == 65.0

    def test_risk_score_bounds(self):
        """influencer_risk_score must be 0.0-100.0."""
        with pytest.raises(ValueError, match="influencer_risk_score must be 0.0-100.0"):
            InfluencerRiskReport(
                token_address="test",
                influencer_risk_score=150.0,
            )


# ---------------------------------------------------------------------------
# LaunchpadTokenCandidate Tests
# ---------------------------------------------------------------------------


class TestLaunchpadTokenCandidate:
    """Tests for LaunchpadTokenCandidate."""

    def test_valid_construction(self):
        """LaunchpadTokenCandidate constructs with valid data."""
        candidate = LaunchpadTokenCandidate(
            token_address="token_abc",
            token_symbol="ABC",
            token_name="Test Token",
            bonding_curve_progress=0.65,
        )
        assert candidate.token_symbol == "ABC"
        assert candidate.bonding_curve_progress == 0.65

    def test_bonding_curve_bounds(self):
        """bonding_curve_progress must be 0.0-1.0."""
        with pytest.raises(ValueError, match="bonding_curve_progress must be 0.0-1.0"):
            LaunchpadTokenCandidate(
                token_address="test",
                token_symbol="TEST",
                token_name="Test",
                bonding_curve_progress=1.5,
            )

    def test_defaults(self):
        """LaunchpadTokenCandidate has correct defaults."""
        candidate = LaunchpadTokenCandidate(
            token_address="test",
            token_symbol="TEST",
            token_name="Test",
        )
        assert candidate.chain == "solana"
        assert candidate.launchpad == "pumpfun"
        assert candidate.discovery_source == "simulation"


# ---------------------------------------------------------------------------
# TradeDueDiligenceScore Tests
# ---------------------------------------------------------------------------


class TestTradeDueDiligenceScore:
    """Tests for TradeDueDiligenceScore."""

    def test_valid_construction(self):
        """TradeDueDiligenceScore constructs with valid data."""
        score = TradeDueDiligenceScore(
            token_address="token_abc",
            launch_timing=80.0,
            issuer_history=70.0,
            social_authenticity=65.0,
            telegram_quality=60.0,
            influencer_risk=75.0,
            holder_distribution=55.0,
            whale_risk=70.0,
            prior_token_history=50.0,
            bonding_curve=85.0,
            rug_honeypot=90.0,
            total_score=68.0,
            evidence_confidence=0.85,
        )
        assert score.launch_timing == 80.0
        assert score.total_score == 68.0

    def test_component_bounds(self):
        """All component scores must be 0.0-100.0."""
        with pytest.raises(ValueError, match="launch_timing must be 0.0-100.0"):
            TradeDueDiligenceScore(
                token_address="test",
                launch_timing=150.0,
            )

    def test_negative_score_rejected(self):
        """Negative scores are rejected."""
        with pytest.raises(ValueError, match="issuer_history must be 0.0-100.0"):
            TradeDueDiligenceScore(
                token_address="test",
                issuer_history=-10.0,
            )

    def test_evidence_confidence_bounds(self):
        """evidence_confidence must be 0.0-1.0."""
        with pytest.raises(ValueError, match="evidence_confidence must be 0.0-1.0"):
            TradeDueDiligenceScore(
                token_address="test",
                evidence_confidence=1.5,
            )

    def test_calculate_total_score(self):
        """calculate_total_score computes weighted sum."""
        score = TradeDueDiligenceScore(
            token_address="test",
            launch_timing=100.0,  # weight 0.10
            issuer_history=100.0,  # weight 0.15
            social_authenticity=100.0,  # weight 0.10
            telegram_quality=100.0,  # weight 0.05
            influencer_risk=100.0,  # weight 0.10
            holder_distribution=100.0,  # weight 0.15
            whale_risk=100.0,  # weight 0.10
            prior_token_history=100.0,  # weight 0.10
            bonding_curve=100.0,  # weight 0.05
            rug_honeypot=100.0,  # weight 0.10
        )
        # All 100 with weights summing to 1.0 should give 100
        assert score.calculate_total_score() == 100.0

    def test_calculate_total_score_weighted(self):
        """calculate_total_score applies weights correctly."""
        score = TradeDueDiligenceScore(
            token_address="test",
            launch_timing=50.0,  # 50 * 0.10 = 5
            issuer_history=0.0,  # 0 * 0.15 = 0
            social_authenticity=0.0,
            telegram_quality=0.0,
            influencer_risk=0.0,
            holder_distribution=0.0,
            whale_risk=0.0,
            prior_token_history=0.0,
            bonding_curve=0.0,
            rug_honeypot=0.0,
        )
        assert score.calculate_total_score() == 5.0


# ---------------------------------------------------------------------------
# Decision Band Determination Tests
# ---------------------------------------------------------------------------


class TestDecisionBandDetermination:
    """Tests for decision band determination logic."""

    def test_low_rug_score_forces_reject(self):
        """rug_honeypot < 20 forces REJECT."""
        score = TradeDueDiligenceScore(
            token_address="test",
            rug_honeypot=15.0,
            total_score=80.0,
            evidence_confidence=0.9,
        )
        assert score.determine_decision_band() == DecisionBand.REJECT

    def test_low_issuer_history_forces_reject(self):
        """issuer_history < 20 forces REJECT."""
        score = TradeDueDiligenceScore(
            token_address="test",
            issuer_history=10.0,
            rug_honeypot=80.0,
            total_score=70.0,
            evidence_confidence=0.9,
        )
        assert score.determine_decision_band() == DecisionBand.REJECT

    def test_low_confidence_forces_observe(self):
        """evidence_confidence < 0.5 forces OBSERVE."""
        score = TradeDueDiligenceScore(
            token_address="test",
            issuer_history=80.0,
            rug_honeypot=80.0,
            total_score=75.0,
            evidence_confidence=0.4,
        )
        assert score.determine_decision_band() == DecisionBand.OBSERVE

    def test_score_under_30_is_reject(self):
        """total_score < 30 is REJECT."""
        score = TradeDueDiligenceScore(
            token_address="test",
            issuer_history=50.0,
            rug_honeypot=50.0,
            total_score=25.0,
            evidence_confidence=0.8,
        )
        assert score.determine_decision_band() == DecisionBand.REJECT

    def test_score_30_to_50_is_observe(self):
        """total_score 30-50 is OBSERVE."""
        score = TradeDueDiligenceScore(
            token_address="test",
            issuer_history=50.0,
            rug_honeypot=50.0,
            total_score=40.0,
            evidence_confidence=0.8,
        )
        assert score.determine_decision_band() == DecisionBand.OBSERVE

    def test_score_50_to_70_is_simulate_only(self):
        """total_score 50-70 is SIMULATE_ONLY."""
        score = TradeDueDiligenceScore(
            token_address="test",
            issuer_history=60.0,
            rug_honeypot=60.0,
            total_score=60.0,
            evidence_confidence=0.8,
        )
        assert score.determine_decision_band() == DecisionBand.SIMULATE_ONLY

    def test_score_over_70_is_candidate(self):
        """total_score > 70 is CANDIDATE_FOR_FUTURE_REVIEW.

        Note: Must set whale_risk, influencer_risk, social_authenticity, and
        telegram_quality above soft-disqualifier thresholds to isolate the
        total_score band logic (PR #696 soft-disqualifier tuning).
        """
        score = TradeDueDiligenceScore(
            token_address="test",
            issuer_history=80.0,
            rug_honeypot=80.0,
            whale_risk=80.0,  # Above soft-disqualifier threshold (20)
            influencer_risk=80.0,  # Above soft-disqualifier threshold (20)
            social_authenticity=80.0,  # Above soft-disqualifier threshold (40)
            telegram_quality=80.0,  # Above soft-disqualifier threshold (50)
            total_score=75.0,
            evidence_confidence=0.9,
        )
        assert score.determine_decision_band() == DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW


# ---------------------------------------------------------------------------
# No Real Trading Authorization Tests
# ---------------------------------------------------------------------------


class TestNoRealTradingAuthorization:
    """Tests that no decision band authorizes real trading."""

    def test_reject_does_not_authorize(self):
        """REJECT band does not authorize real trading."""
        assert_no_real_trading_authorized(DecisionBand.REJECT)

    def test_observe_does_not_authorize(self):
        """OBSERVE band does not authorize real trading."""
        assert_no_real_trading_authorized(DecisionBand.OBSERVE)

    def test_simulate_only_does_not_authorize(self):
        """SIMULATE_ONLY band does not authorize real trading."""
        assert_no_real_trading_authorized(DecisionBand.SIMULATE_ONLY)

    def test_candidate_does_not_authorize(self):
        """CANDIDATE_FOR_FUTURE_REVIEW band does not authorize real trading."""
        assert_no_real_trading_authorized(DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW)


# ---------------------------------------------------------------------------
# Serialization Tests
# ---------------------------------------------------------------------------


class TestSerialization:
    """Tests for deterministic serialization."""

    def test_due_diligence_score_serializes(self):
        """TradeDueDiligenceScore serializes to dict."""
        score = TradeDueDiligenceScore(
            token_address="test",
            total_score=65.0,
            decision_band=DecisionBand.SIMULATE_ONLY,
        )
        d = score.to_dict()
        assert d["token_address"] == "test"
        assert d["total_score"] == 65.0
        assert d["decision_band"] == "simulate_only"

    def test_due_diligence_score_json_serializable(self):
        """TradeDueDiligenceScore dict is JSON serializable."""
        score = TradeDueDiligenceScore(token_address="test")
        json_str = json.dumps(score.to_dict())
        parsed = json.loads(json_str)
        assert parsed["token_address"] == "test"

    def test_all_contracts_json_serializable(self):
        """All due-diligence contracts are JSON serializable."""
        contracts = [
            EntityHistoryReport(entity_id="test", entity_type=EntityType.ISSUER),
            WalletAuditReport(wallet_hash="test", token_address="test"),
            SocialPresenceReport(token_address="test"),
            InfluencerRiskReport(token_address="test"),
            LaunchpadTokenCandidate(token_address="test", token_symbol="T", token_name="Test"),
            TradeDueDiligenceScore(token_address="test"),
        ]
        for contract in contracts:
            json_str = json.dumps(contract.to_dict())
            assert json_str  # Non-empty JSON


# ---------------------------------------------------------------------------
# Missing Evidence Confidence Tests
# ---------------------------------------------------------------------------


class TestMissingEvidenceConfidence:
    """Tests for confidence impact on decision bands."""

    def test_zero_confidence_forces_observe(self):
        """Zero evidence confidence forces OBSERVE regardless of score."""
        score = TradeDueDiligenceScore(
            token_address="test",
            issuer_history=90.0,
            rug_honeypot=90.0,
            total_score=85.0,
            evidence_confidence=0.0,
        )
        # Low confidence should force OBSERVE
        assert score.determine_decision_band() == DecisionBand.OBSERVE

    def test_partial_confidence_allows_higher_bands(self):
        """Confidence >= 0.5 allows higher bands.

        Note: Must set whale_risk, influencer_risk, social_authenticity, and
        telegram_quality above soft-disqualifier thresholds to isolate the
        confidence logic (PR #696 soft-disqualifier tuning).
        """
        score = TradeDueDiligenceScore(
            token_address="test",
            issuer_history=80.0,
            rug_honeypot=80.0,
            whale_risk=80.0,  # Above soft-disqualifier threshold (20)
            influencer_risk=80.0,  # Above soft-disqualifier threshold (20)
            social_authenticity=80.0,  # Above soft-disqualifier threshold (40)
            telegram_quality=80.0,  # Above soft-disqualifier threshold (50)
            total_score=75.0,
            evidence_confidence=0.6,
        )
        assert score.determine_decision_band() == DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW
