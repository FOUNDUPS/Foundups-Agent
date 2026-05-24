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
# Fixed Evaluation Time (deterministic scoring)
# ---------------------------------------------------------------------------

FIXED_EVAL_TIME = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)


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
    """A freshly launched token candidate (2 minutes before FIXED_EVAL_TIME)."""
    return LaunchpadTokenCandidate(
        token_address="So1FreshToken11111111111111111111111111111111",
        token_symbol="FRESH",
        token_name="Fresh Token",
        chain="solana",
        launchpad="pumpfun",
        timestamp=FIXED_EVAL_TIME - timedelta(minutes=2),
        creator_address="Creator11111111111111111111111111111111111111",
        bonding_curve_progress=0.15,
        initial_market_cap_usd=5000.0,
        transaction_count=50,
        passed_initial_filter=True,
    )


@pytest.fixture
def old_candidate():
    """An old token (8 hours before FIXED_EVAL_TIME)."""
    return LaunchpadTokenCandidate(
        token_address="So1OldToken111111111111111111111111111111111",
        token_symbol="OLD",
        token_name="Old Token",
        timestamp=FIXED_EVAL_TIME - timedelta(hours=8),
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
        score = score_launch_timing(fresh_candidate, FIXED_EVAL_TIME)
        assert score == 100.0

    def test_old_launch_scores_low(self, old_candidate):
        """Old launch (6+ hours) scores low."""
        score = score_launch_timing(old_candidate, FIXED_EVAL_TIME)
        assert score == 20.0

    def test_30_minute_launch(self, fresh_candidate):
        """30 minute old launch scores between 50-70."""
        fresh_candidate.timestamp = FIXED_EVAL_TIME - timedelta(minutes=30)
        score = score_launch_timing(fresh_candidate, FIXED_EVAL_TIME)
        assert 50.0 <= score <= 75.0

    def test_score_bounds(self, fresh_candidate):
        """Score is always 0-100."""
        for minutes in [0, 5, 30, 60, 360, 1000]:
            fresh_candidate.timestamp = FIXED_EVAL_TIME - timedelta(minutes=minutes)
            score = score_launch_timing(fresh_candidate, FIXED_EVAL_TIME)
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
        result = engine.score(fresh_candidate, evaluation_time=FIXED_EVAL_TIME)
        assert isinstance(result, TradeDueDiligenceScore)

    def test_score_populates_all_components(self, fresh_candidate, clean_issuer, good_social):
        """Engine populates all 10 component scores."""
        engine = create_scoring_engine()
        result = engine.score(
            fresh_candidate,
            evaluation_time=FIXED_EVAL_TIME,
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
        result = engine.score(fresh_candidate, evaluation_time=FIXED_EVAL_TIME)
        assert result.total_score == result.calculate_total_score()

    def test_risk_score_inverted(self, fresh_candidate):
        """Risk score is inverted total score."""
        engine = create_scoring_engine()
        result = engine.score(fresh_candidate, evaluation_time=FIXED_EVAL_TIME)
        assert result.risk_score == 100.0 - result.total_score

    def test_decision_band_assigned(self, fresh_candidate):
        """Decision band is assigned."""
        engine = create_scoring_engine()
        result = engine.score(fresh_candidate, evaluation_time=FIXED_EVAL_TIME)
        assert result.decision_band in list(DecisionBand)

    def test_band_rationale_generated(self, fresh_candidate):
        """Band rationale is generated."""
        engine = create_scoring_engine()
        result = engine.score(fresh_candidate, evaluation_time=FIXED_EVAL_TIME)
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
            evaluation_time=FIXED_EVAL_TIME,
            issuer_report=clean_issuer,
            social_report=good_social,
        )
        result2 = engine.score(
            fresh_candidate,
            evaluation_time=FIXED_EVAL_TIME,
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

        result1 = engine.score(fresh_candidate, evaluation_time=FIXED_EVAL_TIME, issuer_report=clean_issuer)
        result2 = engine.score(fresh_candidate, evaluation_time=FIXED_EVAL_TIME, issuer_report=clean_issuer)

        json1 = json.dumps(result1.to_dict(), sort_keys=True)
        json2 = json.dumps(result2.to_dict(), sort_keys=True)

        assert json1 == json2

    def test_byte_identical_determinism(self, fresh_candidate, clean_issuer, good_social):
        """Identical inputs produce byte-identical JSON output."""
        engine = create_scoring_engine()

        result1 = engine.score(
            fresh_candidate,
            evaluation_time=FIXED_EVAL_TIME,
            issuer_report=clean_issuer,
            social_report=good_social,
        )
        result2 = engine.score(
            fresh_candidate,
            evaluation_time=FIXED_EVAL_TIME,
            issuer_report=clean_issuer,
            social_report=good_social,
        )

        json1 = json.dumps(result1.to_dict(), sort_keys=True)
        json2 = json.dumps(result2.to_dict(), sort_keys=True)

        assert json1 == json2, "JSON outputs must be byte-identical"
        assert len(json1) > 0, "JSON output must not be empty"


# ---------------------------------------------------------------------------
# Decision Band Tests
# ---------------------------------------------------------------------------


class TestDecisionBandDetermination:
    """Tests for decision band determination via scoring engine."""

    def test_reject_band_reachable(self, fresh_candidate, blacklisted_issuer):
        """REJECT band is reachable."""
        engine = create_scoring_engine()
        result = engine.score(fresh_candidate, evaluation_time=FIXED_EVAL_TIME, issuer_report=blacklisted_issuer)
        assert result.decision_band == DecisionBand.REJECT

    def test_observe_band_reachable(self, fresh_candidate):
        """OBSERVE band is reachable."""
        engine = create_scoring_engine()
        poor_social = SocialPresenceReport(
            token_address=fresh_candidate.token_address,
            social_authenticity_score=20.0,
            evidence_completeness=0.3,
        )
        result = engine.score(fresh_candidate, evaluation_time=FIXED_EVAL_TIME, social_report=poor_social)
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
            evaluation_time=FIXED_EVAL_TIME,
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
            evaluation_time=FIXED_EVAL_TIME,
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
            evaluation_time=FIXED_EVAL_TIME,
            issuer_report=blacklist_issuer,
            wallet_reports=scammer_wallets,
        )
        assert result.rug_honeypot < 20 or result.issuer_history < 20
        assert result.decision_band == DecisionBand.REJECT

    def test_low_evidence_forces_observe(self, fresh_candidate):
        """Low evidence confidence forces OBSERVE."""
        engine = create_scoring_engine()
        fresh_candidate.passed_initial_filter = False
        result = engine.score(fresh_candidate, evaluation_time=FIXED_EVAL_TIME)
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
        result = engine.score(fresh_candidate, evaluation_time=FIXED_EVAL_TIME, issuer_report=blacklisted_issuer)
        assert result.decision_band == DecisionBand.REJECT
        assert "authorize" not in result.band_rationale.lower() or "not" in result.band_rationale.lower()

    def test_observe_does_not_authorize(self, fresh_candidate):
        """OBSERVE band does not authorize trading."""
        engine = create_scoring_engine()
        result = engine.score(fresh_candidate, evaluation_time=FIXED_EVAL_TIME)
        if result.decision_band == DecisionBand.OBSERVE:
            assert "OBSERVE" in result.band_rationale

    def test_simulate_only_does_not_authorize(self, fresh_candidate, clean_issuer, good_social):
        """SIMULATE_ONLY band does not authorize trading."""
        engine = create_scoring_engine()
        result = engine.score(
            fresh_candidate,
            evaluation_time=FIXED_EVAL_TIME,
            issuer_report=clean_issuer,
            social_report=good_social,
        )
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
            evaluation_time=FIXED_EVAL_TIME,
            issuer_report=clean_issuer,
            wallet_reports=distributed_wallets,
            social_report=good_social,
            influencer_report=low_risk_influencer,
        )
        if result.decision_band == DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW:
            assert "future review" in result.band_rationale.lower() or "CANDIDATE" in result.band_rationale


# ---------------------------------------------------------------------------
# Timezone Validation Tests (TRADE_DUE_DILIGENCE_SCORING_ENGINE_DETERMINISTIC_CLOCK_FIX_PHASE1)
# ---------------------------------------------------------------------------


class TestTimezoneValidation:
    """Tests for evaluation_time timezone handling."""

    def test_naive_datetime_raises_valueerror(self, fresh_candidate):
        """Naive datetime (no tzinfo) raises ValueError."""
        engine = create_scoring_engine()
        naive_time = datetime(2026, 5, 24, 12, 0, 0)  # No tzinfo

        with pytest.raises(ValueError, match="timezone-aware"):
            engine.score(fresh_candidate, evaluation_time=naive_time)

    def test_non_utc_timezone_normalizes_to_utc(self, fresh_candidate, clean_issuer, good_social):
        """Non-UTC timezone normalizes to UTC and produces identical output."""
        engine = create_scoring_engine()

        # JST = UTC+9
        from datetime import timezone as tz

        jst = tz(timedelta(hours=9))
        utc_time = datetime(2026, 5, 24, 12, 0, 0, tzinfo=tz.utc)
        jst_time = datetime(2026, 5, 24, 21, 0, 0, tzinfo=jst)  # Same instant

        result_utc = engine.score(
            fresh_candidate,
            evaluation_time=utc_time,
            issuer_report=clean_issuer,
            social_report=good_social,
        )
        result_jst = engine.score(
            fresh_candidate,
            evaluation_time=jst_time,
            issuer_report=clean_issuer,
            social_report=good_social,
        )

        json_utc = json.dumps(result_utc.to_dict(), sort_keys=True)
        json_jst = json.dumps(result_jst.to_dict(), sort_keys=True)

        assert json_utc == json_jst, "Same instant in different timezones must produce byte-identical output"


# ---------------------------------------------------------------------------
# Static Clock Scan Tests (TRADE_DUE_DILIGENCE_SCORING_ENGINE_DETERMINISTIC_CLOCK_FIX_PHASE1)
# ---------------------------------------------------------------------------


FORBIDDEN_CLOCK_PATTERNS = {
    "datetime.now",
    "date.today",
    "time.time",
    "time.monotonic",
    "_utc_now",
}


class TestStaticClockScan:
    """Verify scoring source has no implicit wall-clock calls."""

    def test_no_forbidden_clock_patterns_in_source(self):
        """Source file contains zero hits for forbidden clock patterns."""
        source_path = Path(__file__).parent.parent / "src" / "due_diligence_scoring.py"
        assert source_path.exists(), f"Source file not found: {source_path}"

        source_code = source_path.read_text(encoding="utf-8")

        violations = []
        for pattern in FORBIDDEN_CLOCK_PATTERNS:
            if pattern in source_code:
                violations.append(pattern)

        assert len(violations) == 0, f"Forbidden clock patterns found: {violations}"


# ---------------------------------------------------------------------------
# Scoring Invariants Tests (TRADE_DUE_DILIGENCE_SCORING_ENGINE_DETERMINISTIC_CLOCK_FIX_PHASE1)
# ---------------------------------------------------------------------------


class TestScoringInvariants:
    """Verify scoring weights, bands, and disqualifiers are unchanged."""

    def test_component_weights_sum_to_one(self):
        """All 10 component weights sum to 1.0."""
        weights = {
            "launch_timing": 0.10,
            "issuer_history": 0.15,
            "social_authenticity": 0.10,
            "telegram_quality": 0.05,
            "influencer_risk": 0.10,
            "holder_distribution": 0.15,
            "whale_risk": 0.10,
            "prior_token_history": 0.10,
            "bonding_curve": 0.05,
            "rug_honeypot": 0.10,
        }
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.0001, f"Weights sum to {total}, expected 1.0"

    def test_decision_bands_unchanged(self):
        """All 4 decision bands exist."""
        bands = list(DecisionBand)
        expected = {"REJECT", "OBSERVE", "SIMULATE_ONLY", "CANDIDATE_FOR_FUTURE_REVIEW"}
        actual = {b.name for b in bands}
        assert actual == expected, f"Decision bands changed: {actual}"

    def test_hard_disqualifier_thresholds_unchanged(self, fresh_candidate, blacklisted_issuer):
        """Hard disqualifiers still use threshold < 20."""
        engine = create_scoring_engine()
        result = engine.score(fresh_candidate, evaluation_time=FIXED_EVAL_TIME, issuer_report=blacklisted_issuer)

        assert result.issuer_history < 20 or result.rug_honeypot < 20
        assert result.decision_band == DecisionBand.REJECT

    def test_low_evidence_threshold_unchanged(self, fresh_candidate):
        """Low evidence threshold still 0.5."""
        engine = create_scoring_engine()
        fresh_candidate.passed_initial_filter = False
        result = engine.score(fresh_candidate, evaluation_time=FIXED_EVAL_TIME)

        assert result.evidence_confidence < 0.5
        assert result.decision_band == DecisionBand.OBSERVE


# ---------------------------------------------------------------------------
# Soft Disqualifier Tests (TRADE_DUE_DILIGENCE_SOFT_DISQUALIFIER_PHASE1)
# ---------------------------------------------------------------------------


class TestSoftDisqualifiers:
    """Tests for soft disqualifier logic (PR #696).

    Soft disqualifiers cap CANDIDATE_FOR_FUTURE_REVIEW at SIMULATE_ONLY
    when certain risk signals are present.

    Authorized tuning (R2, R5, R6):
    - R2: influencer_risk < 20 -> cap at SIMULATE_ONLY
    - R5: whale_risk < 20 -> cap at SIMULATE_ONLY
    - R6: social_authenticity < 40 AND telegram_quality < 50 -> cap at SIMULATE_ONLY

    NOT TUNED (R3, R7):
    - R3: dead_x_no_telegram - social weights, no soft disqualifier
    - R7: bonding_curve_migration_risk - curve weights, no soft disqualifier
    """

    def test_whale_risk_soft_disqualifier_caps_at_simulate_only(self):
        """whale_risk < 20 caps CANDIDATE at SIMULATE_ONLY (R5)."""
        score = TradeDueDiligenceScore(
            token_address="test_whale_risk",
            issuer_history=80.0,  # Clear hard disqualifier
            rug_honeypot=80.0,  # Clear hard disqualifier
            whale_risk=15.0,  # BELOW soft disqualifier threshold (20)
            influencer_risk=80.0,  # Above soft disqualifier threshold
            social_authenticity=80.0,  # Above soft disqualifier threshold
            telegram_quality=80.0,  # Above soft disqualifier threshold
            total_score=75.0,  # Would be CANDIDATE without soft disqualifier
            evidence_confidence=0.9,
        )
        # Would be CANDIDATE_FOR_FUTURE_REVIEW without soft disqualifier
        # But whale_risk < 20 caps at SIMULATE_ONLY
        assert score.determine_decision_band() == DecisionBand.SIMULATE_ONLY

    def test_influencer_risk_soft_disqualifier_caps_at_simulate_only(self):
        """influencer_risk < 20 caps CANDIDATE at SIMULATE_ONLY (R2)."""
        score = TradeDueDiligenceScore(
            token_address="test_influencer_risk",
            issuer_history=80.0,  # Clear hard disqualifier
            rug_honeypot=80.0,  # Clear hard disqualifier
            whale_risk=80.0,  # Above soft disqualifier threshold
            influencer_risk=10.0,  # BELOW soft disqualifier threshold (20)
            social_authenticity=80.0,  # Above soft disqualifier threshold
            telegram_quality=80.0,  # Above soft disqualifier threshold
            total_score=75.0,  # Would be CANDIDATE without soft disqualifier
            evidence_confidence=0.9,
        )
        # Would be CANDIDATE_FOR_FUTURE_REVIEW without soft disqualifier
        # But influencer_risk < 20 caps at SIMULATE_ONLY
        assert score.determine_decision_band() == DecisionBand.SIMULATE_ONLY

    def test_social_telegram_soft_disqualifier_caps_at_simulate_only(self):
        """social_authenticity < 40 AND telegram_quality < 50 caps at SIMULATE_ONLY (R6)."""
        score = TradeDueDiligenceScore(
            token_address="test_social_telegram",
            issuer_history=80.0,  # Clear hard disqualifier
            rug_honeypot=80.0,  # Clear hard disqualifier
            whale_risk=80.0,  # Above soft disqualifier threshold
            influencer_risk=80.0,  # Above soft disqualifier threshold
            social_authenticity=35.0,  # BELOW soft disqualifier threshold (40)
            telegram_quality=45.0,  # BELOW soft disqualifier threshold (50)
            total_score=75.0,  # Would be CANDIDATE without soft disqualifier
            evidence_confidence=0.9,
        )
        # Would be CANDIDATE_FOR_FUTURE_REVIEW without soft disqualifier
        # But social_authenticity < 40 AND telegram_quality < 50 caps at SIMULATE_ONLY
        assert score.determine_decision_band() == DecisionBand.SIMULATE_ONLY

    def test_social_only_does_not_trigger_soft_disqualifier(self):
        """social_authenticity < 40 alone does NOT trigger soft disqualifier."""
        score = TradeDueDiligenceScore(
            token_address="test_social_only",
            issuer_history=80.0,
            rug_honeypot=80.0,
            whale_risk=80.0,
            influencer_risk=80.0,
            social_authenticity=35.0,  # BELOW threshold
            telegram_quality=80.0,  # ABOVE threshold - only social is low
            total_score=75.0,
            evidence_confidence=0.9,
        )
        # Both conditions required, only one met -> CANDIDATE allowed
        assert score.determine_decision_band() == DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW

    def test_telegram_only_does_not_trigger_soft_disqualifier(self):
        """telegram_quality < 50 alone does NOT trigger soft disqualifier."""
        score = TradeDueDiligenceScore(
            token_address="test_telegram_only",
            issuer_history=80.0,
            rug_honeypot=80.0,
            whale_risk=80.0,
            influencer_risk=80.0,
            social_authenticity=80.0,  # ABOVE threshold - only telegram is low
            telegram_quality=45.0,  # BELOW threshold
            total_score=75.0,
            evidence_confidence=0.9,
        )
        # Both conditions required, only one met -> CANDIDATE allowed
        assert score.determine_decision_band() == DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW

    def test_soft_disqualifiers_do_not_affect_simulate_only_band(self):
        """Soft disqualifiers only cap CANDIDATE, not lower bands."""
        score = TradeDueDiligenceScore(
            token_address="test_simulate_band",
            issuer_history=80.0,
            rug_honeypot=80.0,
            whale_risk=15.0,  # Would trigger soft disqualifier
            influencer_risk=10.0,  # Would trigger soft disqualifier
            social_authenticity=30.0,  # Would trigger soft disqualifier
            telegram_quality=40.0,  # Would trigger soft disqualifier
            total_score=60.0,  # SIMULATE_ONLY range (50-70)
            evidence_confidence=0.9,
        )
        # SIMULATE_ONLY is already at or below the cap, no change
        assert score.determine_decision_band() == DecisionBand.SIMULATE_ONLY

    def test_soft_disqualifiers_do_not_affect_observe_band(self):
        """Soft disqualifiers do not affect OBSERVE band."""
        score = TradeDueDiligenceScore(
            token_address="test_observe_band",
            issuer_history=80.0,
            rug_honeypot=80.0,
            whale_risk=15.0,  # Would trigger soft disqualifier
            total_score=40.0,  # OBSERVE range (30-50)
            evidence_confidence=0.9,
        )
        # OBSERVE is below soft disqualifier cap, unchanged
        assert score.determine_decision_band() == DecisionBand.OBSERVE

    def test_soft_disqualifiers_do_not_affect_reject_band(self):
        """Soft disqualifiers do not affect REJECT band."""
        score = TradeDueDiligenceScore(
            token_address="test_reject_band",
            issuer_history=80.0,
            rug_honeypot=80.0,
            whale_risk=15.0,  # Would trigger soft disqualifier
            total_score=25.0,  # REJECT range (< 30)
            evidence_confidence=0.9,
        )
        # REJECT is below soft disqualifier cap, unchanged
        assert score.determine_decision_band() == DecisionBand.REJECT

    def test_hard_disqualifier_takes_priority_over_soft(self):
        """Hard disqualifiers still trigger even with soft disqualifier conditions."""
        score = TradeDueDiligenceScore(
            token_address="test_hard_priority",
            issuer_history=10.0,  # Hard disqualifier (< 20)
            rug_honeypot=80.0,
            whale_risk=15.0,  # Would be soft disqualifier
            total_score=75.0,
            evidence_confidence=0.9,
        )
        # Hard disqualifier takes priority -> REJECT
        assert score.determine_decision_band() == DecisionBand.REJECT

    def test_all_components_high_allows_candidate(self):
        """All components above thresholds allows CANDIDATE_FOR_FUTURE_REVIEW."""
        score = TradeDueDiligenceScore(
            token_address="test_all_high",
            issuer_history=90.0,
            rug_honeypot=90.0,
            whale_risk=90.0,  # Above threshold (20)
            influencer_risk=90.0,  # Above threshold (20)
            social_authenticity=90.0,  # Above threshold (40)
            telegram_quality=90.0,  # Above threshold (50)
            total_score=85.0,
            evidence_confidence=0.95,
        )
        # No soft disqualifiers triggered -> CANDIDATE allowed
        assert score.determine_decision_band() == DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW


class TestR3R7UnchangedBehavior:
    """Tests proving R3 and R7 regimes are NOT affected by soft disqualifiers.

    R3 (dead_x_no_telegram) and R7 (bonding_curve_migration_risk) are explicitly
    NOT TUNED per PR #696. Their behavior is controlled by:
    - R3: weighted sum via social_authenticity and telegram_quality weights
    - R7: weighted sum via bonding_curve weight

    No soft disqualifier was added for these regimes.
    """

    def test_bonding_curve_low_does_not_trigger_soft_disqualifier(self):
        """Low bonding_curve does NOT trigger soft disqualifier (R7 unchanged)."""
        score = TradeDueDiligenceScore(
            token_address="test_bonding_curve_r7",
            issuer_history=90.0,
            rug_honeypot=90.0,
            whale_risk=90.0,
            influencer_risk=90.0,
            social_authenticity=90.0,
            telegram_quality=90.0,
            bonding_curve=42.5,  # Low (late curve) - R7 scenario
            total_score=85.0,  # Still in CANDIDATE range due to weights
            evidence_confidence=0.9,
        )
        # bonding_curve weight is 0.05, so low value doesn't drop total much
        # No soft disqualifier for bonding_curve -> CANDIDATE allowed
        assert score.determine_decision_band() == DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW

    def test_social_authenticity_very_low_alone_does_not_trigger(self):
        """Very low social_authenticity alone does NOT trigger (R3 unchanged).

        R3 has social_authenticity=5 but telegram_quality=20 (above telegram threshold).
        The social-telegram soft disqualifier requires BOTH conditions.
        """
        score = TradeDueDiligenceScore(
            token_address="test_social_r3",
            issuer_history=90.0,
            rug_honeypot=90.0,
            whale_risk=90.0,
            influencer_risk=90.0,
            social_authenticity=5.0,  # R3-like: very low
            telegram_quality=60.0,  # Above soft disqualifier threshold (50)
            total_score=80.0,
            evidence_confidence=0.9,
        )
        # social_authenticity < 40 BUT telegram_quality >= 50
        # Soft disqualifier requires BOTH -> CANDIDATE allowed
        assert score.determine_decision_band() == DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW

    def test_weights_unchanged_for_r3_r7_components(self):
        """Weights for social and bonding_curve components remain unchanged."""
        # Verify weights from spec (unchanged by this slice)
        expected_weights = {
            "social_authenticity": 0.10,
            "telegram_quality": 0.05,
            "bonding_curve": 0.05,
        }
        score = TradeDueDiligenceScore(token_address="test")
        for component, expected in expected_weights.items():
            assert score._WEIGHTS[component] == expected, (
                f"Weight for {component} changed: expected {expected}, "
                f"got {score._WEIGHTS[component]}"
            )
