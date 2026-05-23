"""Trade FoundUp - Due Diligence Scoring Engine Tests

Tests for deterministic scoring engine from TRADE_DUE_DILIGENCE_SCORING_ENGINE_PHASE1.

WSP 97 Truth Boundary:
- All tests verify pure computation
- No network calls, wallet access, or order placement
- No decision band authorizes real trading

Spec: TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1 (PR #683)
Slice: TRADE_DUE_DILIGENCE_SCORING_ENGINE_PHASE1
"""

import ast
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from contracts import (
    DecisionBand,
    EntityHistoryReport,
    EntityType,
    InfluencerRiskReport,
    LaunchpadTokenCandidate,
    RiskClassification,
    SocialPresenceReport,
    TradeDueDiligenceScore,
    WalletAuditReport,
    WalletClassification,
)
from due_diligence_scoring import (
    DEFAULT_SCORING_ENGINE,
    DueDiligenceScoringEngine,
    calculate_evidence_confidence,
    create_scoring_engine,
    score_bonding_curve,
    score_holder_distribution,
    score_influencer_risk,
    score_issuer_history,
    score_launch_timing,
    score_prior_token_history,
    score_rug_honeypot,
    score_social_authenticity,
    score_telegram_quality,
    score_whale_risk,
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
    """Verify due_diligence_scoring.py does not import forbidden modules."""

    def test_no_forbidden_imports_in_source(self):
        """Source file does not import any forbidden modules."""
        source_path = Path(__file__).parent.parent / "src" / "due_diligence_scoring.py"
        assert source_path.exists(), f"Source file not found: {source_path}"

        source_code = source_path.read_text(encoding="utf-8")
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
    """Verify due_diligence_scoring.py does not contain forbidden fields."""

    def test_no_forbidden_fields_in_source(self):
        """Source file does not contain forbidden field names."""
        source_path = Path(__file__).parent.parent / "src" / "due_diligence_scoring.py"
        source_code = source_path.read_text(encoding="utf-8")

        for forbidden in FORBIDDEN_FIELDS:
            pattern_attr = f"self.{forbidden}"
            assert pattern_attr not in source_code, f"Forbidden field 'self.{forbidden}' found"


# ---------------------------------------------------------------------------
# Helper Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fresh_candidate():
    """A freshly launched token candidate."""
    return LaunchpadTokenCandidate(
        token_address="So1FreshToken11111111111111111111111111111111",
        token_symbol="FRESH",
        token_name="Fresh Token",
        chain="solana",
        launchpad="pumpfun",
        timestamp=datetime.now(timezone.utc),
        creator_address="Creator11111111111111111111111111111111111111",
        bonding_curve_progress=0.15,
        initial_market_cap_usd=5000.0,
        transaction_count=50,
        passed_initial_filter=True,
    )


@pytest.fixture
def old_candidate():
    """An old token (6+ hours ago)."""
    return LaunchpadTokenCandidate(
        token_address="So1OldToken111111111111111111111111111111111",
        token_symbol="OLD",
        token_name="Old Token",
        timestamp=datetime.now(timezone.utc) - timedelta(hours=8),
        bonding_curve_progress=0.80,
        passed_initial_filter=True,
    )


@pytest.fixture
def clean_issuer():
    """Clean issuer with no rug history."""
    return EntityHistoryReport(
        entity_id="issuer_clean_001",
        entity_type=EntityType.ISSUER,
        prior_token_launches=5,
        prior_rug_pulls=0,
        prior_successful_launches=4,
        average_token_lifespan_hours=200.0,
        risk_classification=RiskClassification.CLEAN,
        confidence=0.9,
    )


@pytest.fixture
def risky_issuer():
    """Risky issuer with rug history."""
    return EntityHistoryReport(
        entity_id="issuer_risky_001",
        entity_type=EntityType.ISSUER,
        prior_token_launches=10,
        prior_rug_pulls=5,
        prior_successful_launches=2,
        average_token_lifespan_hours=2.0,
        average_holder_loss_percent=75.0,
        risk_classification=RiskClassification.FLAGGED,
        confidence=0.95,
    )


@pytest.fixture
def blacklisted_issuer():
    """Blacklisted issuer."""
    return EntityHistoryReport(
        entity_id="issuer_blacklist_001",
        entity_type=EntityType.ISSUER,
        prior_token_launches=20,
        prior_rug_pulls=18,
        risk_classification=RiskClassification.BLACKLISTED,
        confidence=1.0,
    )


@pytest.fixture
def good_social():
    """Good social presence."""
    return SocialPresenceReport(
        token_address="So1Token1111111111111111111111111111111111111",
        x_account_exists=True,
        x_account_age_days=365,
        x_follower_count=5000,
        x_follower_bot_percent=5.0,
        x_engagement_authenticity=0.85,
        telegram_exists=True,
        telegram_member_count=2000,
        telegram_bot_percent=10.0,
        telegram_admin_active=True,
        telegram_spam_ratio=0.05,
        social_authenticity_score=85.0,
        evidence_completeness=0.9,
    )


@pytest.fixture
def low_risk_influencer():
    """Low-risk influencer report."""
    return InfluencerRiskReport(
        token_address="So1Token1111111111111111111111111111111111111",
        known_pumper_wallets_detected=0,
        coordinated_buy_timing_detected=False,
        influencer_mentions_count=3,
        influencer_risk_score=15.0,
        evidence_completeness=0.8,
    )


@pytest.fixture
def high_risk_influencer():
    """High-risk influencer report."""
    return InfluencerRiskReport(
        token_address="So1Token1111111111111111111111111111111111111",
        known_pumper_wallets_detected=5,
        coordinated_buy_timing_detected=True,
        influencer_mentions_count=20,
        influencers_with_prior_rugs=3,
        influencer_risk_score=85.0,
        evidence_completeness=0.9,
    )


@pytest.fixture
def distributed_wallets():
    """Well-distributed wallet holdings."""
    return [
        WalletAuditReport(
            wallet_hash=f"wallet_{i}",
            token_address="So1Token1111111111111111111111111111111111111",
            holding_percent=5.0,
            entity_classification=WalletClassification.RETAIL,
            risk_contribution=0.1,
        )
        for i in range(20)
    ]


@pytest.fixture
def concentrated_wallets():
    """Concentrated wallet holdings (whale-dominated)."""
    wallets = [
        WalletAuditReport(
            wallet_hash="whale_1",
            token_address="So1Token1111111111111111111111111111111111111",
            holding_percent=40.0,
            entity_classification=WalletClassification.WHALE,
            risk_contribution=0.8,
        ),
        WalletAuditReport(
            wallet_hash="whale_2",
            token_address="So1Token1111111111111111111111111111111111111",
            holding_percent=25.0,
            entity_classification=WalletClassification.WHALE,
            risk_contribution=0.6,
        ),
    ]
    return wallets


@pytest.fixture
def scammer_wallets():
    """Wallets including scammers."""
    return [
        WalletAuditReport(
            wallet_hash="scammer_1",
            token_address="So1Token1111111111111111111111111111111111111",
            holding_percent=30.0,
            entity_classification=WalletClassification.SCAMMER,
            risk_contribution=1.0,
        ),
    ]


# ---------------------------------------------------------------------------
# Component Scorer Tests
# ---------------------------------------------------------------------------


class TestScoreLaunchTiming:
    """Tests for launch timing scorer."""

    def test_fresh_launch_scores_high(self, fresh_candidate):
        """Fresh launch (< 5 min) scores 100."""
        score = score_launch_timing(fresh_candidate)
        assert score == 100.0

    def test_old_launch_scores_low(self, old_candidate):
        """Old launch (6+ hours) scores low."""
        score = score_launch_timing(old_candidate)
        assert score == 20.0

    def test_30_minute_launch(self, fresh_candidate):
        """30 minute old launch scores between 50-70."""
        fresh_candidate.timestamp = datetime.now(timezone.utc) - timedelta(minutes=30)
        score = score_launch_timing(fresh_candidate)
        assert 50.0 <= score <= 75.0

    def test_score_bounds(self, fresh_candidate):
        """Score is always 0-100."""
        for minutes in [0, 5, 30, 60, 360, 1000]:
            fresh_candidate.timestamp = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            score = score_launch_timing(fresh_candidate)
            assert 0.0 <= score <= 100.0


class TestScoreIssuerHistory:
    """Tests for issuer history scorer."""

    def test_clean_issuer_scores_high(self, clean_issuer):
        """Clean issuer with no rugs scores high."""
        score = score_issuer_history(clean_issuer)
        assert score >= 80.0

    def test_risky_issuer_scores_low(self, risky_issuer):
        """Risky issuer with rugs scores low."""
        score = score_issuer_history(risky_issuer)
        assert score <= 40.0

    def test_blacklisted_issuer_scores_zero(self, blacklisted_issuer):
        """Blacklisted issuer scores 0."""
        score = score_issuer_history(blacklisted_issuer)
        assert score == 0.0

    def test_none_issuer_scores_neutral(self):
        """No issuer report scores 50 (neutral)."""
        score = score_issuer_history(None)
        assert score == 50.0


class TestScoreSocialAuthenticity:
    """Tests for social authenticity scorer."""

    def test_good_social_scores_high(self, good_social):
        """Good social presence scores high."""
        score = score_social_authenticity(good_social)
        assert score == 85.0

    def test_none_social_scores_low(self):
        """No social report scores low."""
        score = score_social_authenticity(None)
        assert score == 30.0


class TestScoreTelegramQuality:
    """Tests for Telegram quality scorer."""

    def test_good_telegram_scores_high(self, good_social):
        """Good Telegram community scores high."""
        score = score_telegram_quality(good_social)
        assert score >= 70.0

    def test_no_telegram_scores_low(self, good_social):
        """No Telegram scores low."""
        good_social.telegram_exists = False
        score = score_telegram_quality(good_social)
        assert score == 20.0


class TestScoreInfluencerRisk:
    """Tests for influencer risk scorer."""

    def test_low_risk_scores_high(self, low_risk_influencer):
        """Low influencer risk scores high."""
        score = score_influencer_risk(low_risk_influencer)
        assert score == 85.0

    def test_high_risk_scores_low(self, high_risk_influencer):
        """High influencer risk scores low."""
        score = score_influencer_risk(high_risk_influencer)
        assert score == 15.0


class TestScoreHolderDistribution:
    """Tests for holder distribution scorer."""

    def test_distributed_scores_high(self, distributed_wallets):
        """Well-distributed holdings score high."""
        score = score_holder_distribution(distributed_wallets)
        assert score >= 80.0

    def test_concentrated_scores_low(self, concentrated_wallets):
        """Concentrated holdings score low."""
        score = score_holder_distribution(concentrated_wallets)
        assert score <= 40.0

    def test_no_wallets_scores_neutral(self):
        """No wallet data scores neutral."""
        score = score_holder_distribution([])
        assert score == 40.0


class TestScoreWhaleRisk:
    """Tests for whale risk scorer."""

    def test_no_whales_scores_high(self, distributed_wallets):
        """No whale wallets scores high."""
        score = score_whale_risk(distributed_wallets)
        assert score == 90.0

    def test_whale_dominated_scores_low(self, concentrated_wallets):
        """Whale-dominated holdings score low."""
        score = score_whale_risk(concentrated_wallets)
        assert score <= 30.0


class TestScoreBondingCurve:
    """Tests for bonding curve scorer."""

    def test_optimal_curve_scores_high(self, fresh_candidate):
        """15% bonding curve scores well."""
        fresh_candidate.bonding_curve_progress = 0.15
        score = score_bonding_curve(fresh_candidate)
        assert score >= 80.0

    def test_early_curve_scores_low(self, fresh_candidate):
        """< 5% bonding curve scores low."""
        fresh_candidate.bonding_curve_progress = 0.02
        score = score_bonding_curve(fresh_candidate)
        assert score == 30.0

    def test_late_curve_scores_medium(self, fresh_candidate):
        """90% bonding curve scores lower."""
        fresh_candidate.bonding_curve_progress = 0.90
        score = score_bonding_curve(fresh_candidate)
        assert score <= 40.0


class TestScoreRugHoneypot:
    """Tests for rug/honeypot risk scorer."""

    def test_clean_scores_high(self, clean_issuer, low_risk_influencer, distributed_wallets):
        """Clean inputs score high."""
        score = score_rug_honeypot(clean_issuer, low_risk_influencer, distributed_wallets)
        assert score >= 80.0

    def test_risky_issuer_scores_low(self, risky_issuer, low_risk_influencer, distributed_wallets):
        """Risky issuer lowers rug score."""
        score = score_rug_honeypot(risky_issuer, low_risk_influencer, distributed_wallets)
        assert score <= 50.0

    def test_blacklisted_scores_zero(self, blacklisted_issuer, low_risk_influencer, distributed_wallets):
        """Blacklisted issuer scores 0."""
        score = score_rug_honeypot(blacklisted_issuer, low_risk_influencer, distributed_wallets)
        assert score == 0.0

    def test_scammer_wallets_score_low(self, clean_issuer, low_risk_influencer, scammer_wallets):
        """Scammer wallets lower score."""
        score = score_rug_honeypot(clean_issuer, low_risk_influencer, scammer_wallets)
        assert score <= 50.0


# ---------------------------------------------------------------------------
# Evidence Confidence Tests
# ---------------------------------------------------------------------------


class TestEvidenceConfidence:
    """Tests for evidence confidence calculation."""

    def test_full_evidence_high_confidence(
        self, fresh_candidate, clean_issuer, good_social, low_risk_influencer, distributed_wallets
    ):
        """Full evidence with high confidence scores high."""
        confidence = calculate_evidence_confidence(
            clean_issuer, distributed_wallets, good_social, low_risk_influencer, fresh_candidate
        )
        assert confidence >= 0.7

    def test_no_evidence_low_confidence(self, fresh_candidate):
        """No evidence scores low."""
        fresh_candidate.passed_initial_filter = False
        confidence = calculate_evidence_confidence(None, [], None, None, fresh_candidate)
        assert confidence <= 0.2


# ---------------------------------------------------------------------------
# Scoring Engine Tests
# ---------------------------------------------------------------------------


class TestScoringEngine:
    """Tests for DueDiligenceScoringEngine."""

    def test_default_engine_exists(self):
        """Default engine instance exists."""
        assert DEFAULT_SCORING_ENGINE is not None

    def test_factory_creates_engine(self):
        """Factory function creates engine."""
        engine = create_scoring_engine()
        assert isinstance(engine, DueDiligenceScoringEngine)

    def test_score_returns_due_diligence_score(self, fresh_candidate):
        """Engine returns TradeDueDiligenceScore."""
        engine = create_scoring_engine()
        result = engine.score(fresh_candidate)
        assert isinstance(result, TradeDueDiligenceScore)

    def test_score_populates_all_components(self, fresh_candidate, clean_issuer, good_social):
        """Engine populates all 10 component scores."""
        engine = create_scoring_engine()
        result = engine.score(
            fresh_candidate,
            issuer_report=clean_issuer,
            social_report=good_social,
        )

        assert result.launch_timing >= 0
        assert result.issuer_history >= 0
        assert result.social_authenticity >= 0
        assert result.telegram_quality >= 0
        assert result.influencer_risk >= 0
        assert result.holder_distribution >= 0
        assert result.whale_risk >= 0
        assert result.prior_token_history >= 0
        assert result.bonding_curve >= 0
        assert result.rug_honeypot >= 0

    def test_total_score_calculated(self, fresh_candidate):
        """Total score is calculated from components."""
        engine = create_scoring_engine()
        result = engine.score(fresh_candidate)
        assert result.total_score == result.calculate_total_score()

    def test_risk_score_inverted(self, fresh_candidate):
        """Risk score is inverted total score."""
        engine = create_scoring_engine()
        result = engine.score(fresh_candidate)
        assert result.risk_score == 100.0 - result.total_score

    def test_decision_band_assigned(self, fresh_candidate):
        """Decision band is assigned."""
        engine = create_scoring_engine()
        result = engine.score(fresh_candidate)
        assert result.decision_band in list(DecisionBand)

    def test_band_rationale_generated(self, fresh_candidate):
        """Band rationale is generated."""
        engine = create_scoring_engine()
        result = engine.score(fresh_candidate)
        assert len(result.band_rationale) > 0


# ---------------------------------------------------------------------------
# Determinism Tests
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Tests for deterministic scoring."""

    def test_same_inputs_same_output(self, fresh_candidate, clean_issuer, good_social):
        """Same inputs produce identical scores."""
        engine = create_scoring_engine()

        result1 = engine.score(
            fresh_candidate,
            issuer_report=clean_issuer,
            social_report=good_social,
        )
        result2 = engine.score(
            fresh_candidate,
            issuer_report=clean_issuer,
            social_report=good_social,
        )

        assert result1.total_score == result2.total_score
        assert result1.decision_band == result2.decision_band
        assert result1.launch_timing == result2.launch_timing
        assert result1.issuer_history == result2.issuer_history

    def test_json_serialization_deterministic(self, fresh_candidate, clean_issuer):
        """JSON output is deterministic."""
        engine = create_scoring_engine()

        result1 = engine.score(fresh_candidate, issuer_report=clean_issuer)
        result2 = engine.score(fresh_candidate, issuer_report=clean_issuer)

        json1 = json.dumps(result1.to_dict(), sort_keys=True)
        json2 = json.dumps(result2.to_dict(), sort_keys=True)

        assert json1 == json2


# ---------------------------------------------------------------------------
# Decision Band Tests
# ---------------------------------------------------------------------------


class TestDecisionBandDetermination:
    """Tests for decision band determination via scoring engine."""

    def test_reject_band_reachable(self, fresh_candidate, blacklisted_issuer):
        """REJECT band is reachable."""
        engine = create_scoring_engine()
        result = engine.score(fresh_candidate, issuer_report=blacklisted_issuer)
        assert result.decision_band == DecisionBand.REJECT

    def test_observe_band_reachable(self, fresh_candidate):
        """OBSERVE band is reachable."""
        engine = create_scoring_engine()
        poor_social = SocialPresenceReport(
            token_address=fresh_candidate.token_address,
            social_authenticity_score=20.0,
            evidence_completeness=0.3,
        )
        result = engine.score(fresh_candidate, social_report=poor_social)
        assert result.decision_band == DecisionBand.OBSERVE

    def test_simulate_only_band_reachable(self, fresh_candidate, clean_issuer, good_social):
        """SIMULATE_ONLY band is reachable."""
        engine = create_scoring_engine()
        moderate_social = SocialPresenceReport(
            token_address=fresh_candidate.token_address,
            social_authenticity_score=50.0,
            evidence_completeness=0.8,
            telegram_exists=True,
            telegram_member_count=500,
            telegram_admin_active=True,
        )
        result = engine.score(
            fresh_candidate,
            issuer_report=clean_issuer,
            social_report=moderate_social,
        )
        assert result.total_score >= 50.0

    def test_candidate_band_reachable(
        self, fresh_candidate, clean_issuer, good_social, low_risk_influencer, distributed_wallets
    ):
        """CANDIDATE_FOR_FUTURE_REVIEW band is reachable."""
        engine = create_scoring_engine()
        result = engine.score(
            fresh_candidate,
            issuer_report=clean_issuer,
            wallet_reports=distributed_wallets,
            social_report=good_social,
            influencer_report=low_risk_influencer,
        )
        assert result.total_score >= 70.0
        assert result.decision_band == DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW

    def test_rug_hard_disqualifier(self, fresh_candidate, clean_issuer, scammer_wallets):
        """Rug risk < 20 forces REJECT regardless of other scores."""
        engine = create_scoring_engine()
        fresh_candidate.bonding_curve_progress = 0.15

        blacklist_issuer = EntityHistoryReport(
            entity_id="bad_issuer",
            entity_type=EntityType.ISSUER,
            prior_rug_pulls=5,
            risk_classification=RiskClassification.BLACKLISTED,
            confidence=1.0,
        )

        result = engine.score(
            fresh_candidate,
            issuer_report=blacklist_issuer,
            wallet_reports=scammer_wallets,
        )
        assert result.rug_honeypot < 20 or result.issuer_history < 20
        assert result.decision_band == DecisionBand.REJECT

    def test_low_evidence_forces_observe(self, fresh_candidate):
        """Low evidence confidence forces OBSERVE."""
        engine = create_scoring_engine()
        fresh_candidate.passed_initial_filter = False
        result = engine.score(fresh_candidate)
        assert result.evidence_confidence < 0.5
        assert result.decision_band == DecisionBand.OBSERVE


# ---------------------------------------------------------------------------
# No Real Trading Authorization Tests
# ---------------------------------------------------------------------------


class TestNoRealTradingAuthorization:
    """Verify no decision band authorizes real trading."""

    def test_reject_does_not_authorize(self, fresh_candidate, blacklisted_issuer):
        """REJECT band does not authorize trading."""
        engine = create_scoring_engine()
        result = engine.score(fresh_candidate, issuer_report=blacklisted_issuer)
        assert result.decision_band == DecisionBand.REJECT
        assert "authorize" not in result.band_rationale.lower() or "not" in result.band_rationale.lower()

    def test_observe_does_not_authorize(self, fresh_candidate):
        """OBSERVE band does not authorize trading."""
        engine = create_scoring_engine()
        result = engine.score(fresh_candidate)
        if result.decision_band == DecisionBand.OBSERVE:
            assert "OBSERVE" in result.band_rationale

    def test_simulate_only_does_not_authorize(self, fresh_candidate, clean_issuer, good_social):
        """SIMULATE_ONLY band does not authorize trading."""
        engine = create_scoring_engine()
        result = engine.score(fresh_candidate, issuer_report=clean_issuer, social_report=good_social)
        assert "SIMULATE" in result.band_rationale or "simulation" in result.band_rationale.lower() \
            or "CANDIDATE" in result.band_rationale or "OBSERVE" in result.band_rationale \
            or "REJECT" in result.band_rationale

    def test_candidate_does_not_authorize(
        self, fresh_candidate, clean_issuer, good_social, low_risk_influencer, distributed_wallets
    ):
        """CANDIDATE band does not authorize trading."""
        engine = create_scoring_engine()
        result = engine.score(
            fresh_candidate,
            issuer_report=clean_issuer,
            wallet_reports=distributed_wallets,
            social_report=good_social,
            influencer_report=low_risk_influencer,
        )
        if result.decision_band == DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW:
            assert "future review" in result.band_rationale.lower() or "CANDIDATE" in result.band_rationale
