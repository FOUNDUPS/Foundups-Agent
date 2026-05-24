"""Synthetic Regime Pack — Trade Due-Diligence Decision-Shape Evidence

Slice: TRADE_DUE_DILIGENCE_SYNTHETIC_REGIME_PACK_PHASE1
Worker: W6
Spec: TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1 (PR #683)
Engine: TRADE_DUE_DILIGENCE_SCORING_ENGINE_PHASE1 (PR #687)
Schema: TRADE_DUE_DILIGENCE_SCHEMA_PHASE1 (PR #685)

Purpose
-------
Exercise the deterministic due-diligence scoring engine against named
synthetic regimes that span the decision-shape space. This is *evidence*,
not acceptance testing: each regime declares an `expected_band` HYPOTHESIS,
but expected-vs-actual divergence is recorded as a finding, not a failure
(per operator's patched test policy).

Boundary contract (LOCKED — no exceptions in this slice)
-------------------------------------------------------
- SIMULATION_MODE_ONLY
- SYNTHETIC_EVIDENCE_ONLY (every datum here is a hand-built deterministic
  Python literal; no live feeds, no recorded production data)
- NO_LIVE_FEEDS / NO_NETWORK_CALLS / NO_WALLET / NO_ORDER_PLACEMENT
- NO_REAL_TRADING / NO_EXCHANGE_SDK_IMPORT
- NO change to Trade status (not_portfolio / poc_status=idea /
  entity_type=skeleton_candidate)

The 7 mandatory regimes (post-soft-disqualifier tuning, PR #693 reconciled)
---------------------------------------------------------------------------
R1: organic_launch_clean_socials       — expected: CANDIDATE_FOR_FUTURE_REVIEW (MATCH)
R2: influencer_pump_high_concentration — expected: SIMULATE_ONLY (soft disqualifier: influencer_risk < 20)
R3: dead_x_no_telegram                 — expected: SIMULATE_ONLY (EXPECTATION_TOO_STRICT per PR #693 F2)
R4: issuer_prior_rug_history           — expected: REJECT (issuer disqualifier) (MATCH)
R5: whale_accumulation_then_dump       — expected: SIMULATE_ONLY (soft disqualifier: whale_risk < 20)
R6: telegram_active_low_authenticity   — expected: SIMULATE_ONLY (soft disqualifier: social<40+tg<50)
R7: bonding_curve_migration_risk       — expected: CANDIDATE_FOR_FUTURE_REVIEW (ACCEPTABLE_BEHAVIOR per PR #693 F5)

All expected bands are now reconciled with engine output. No divergences remain.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Set, Tuple

# Trade src/ is on sys.path via test files; mirror that here so the fixture
# module can be imported standalone (e.g. via the audit-doc generator).
_TRADE_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_TRADE_SRC) not in sys.path:
    sys.path.insert(0, str(_TRADE_SRC))

from contracts import (  # noqa: E402  (sys.path setup above)
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


# ---------------------------------------------------------------------------
# Regime input type (a complete engine-input bundle)
# ---------------------------------------------------------------------------

class RegimeInputs(NamedTuple):
    """One regime's deterministic input bundle for the scoring engine."""

    regime_id: str
    description: str
    expected_band: DecisionBand
    expected_band_rationale: str
    candidate: LaunchpadTokenCandidate
    issuer_report: Optional[EntityHistoryReport]
    wallet_reports: List[WalletAuditReport]
    social_report: Optional[SocialPresenceReport]
    influencer_report: Optional[InfluencerRiskReport]


# ---------------------------------------------------------------------------
# Determinism helpers
# ---------------------------------------------------------------------------
#
# Post-#691 (clock fix): the scoring engine no longer reads an implicit
# clock. Both `candidate.timestamp` and `evaluation_time` must be explicit
# and fixed for byte-identical determinism. This module exposes
# FIXTURE_REFERENCE_TIME — the canonical "now" used by all regime
# constructors. Tests pass the same value as `evaluation_time` to the
# scoring engine so launch_timing buckets resolve deterministically.

# Canonical reference time for all regime fixtures. Tests should pass this
# same value as `evaluation_time` to `DueDiligenceScoringEngine.score()`.
FIXTURE_REFERENCE_TIME: datetime = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)


def _age_offset(minutes: float) -> datetime:
    """Return a UTC datetime that is `minutes` before FIXTURE_REFERENCE_TIME.

    Pure function — no implicit clock. Same input → same output across runs.
    """
    return FIXTURE_REFERENCE_TIME - timedelta(minutes=minutes)


# Hard-coded mock token addresses & creator hashes used across regimes.
# These are intentionally non-real-looking, all-uppercase synthetic strings.
_SYNTHETIC_TOKEN = "SYNTHETIC_TOKEN_REGIME_{idx:02d}"
_SYNTHETIC_CREATOR = "SYNTHETIC_CREATOR_HASH_{idx:02d}"
_SYNTHETIC_WALLET = "SYNTHETIC_WALLET_HASH_R{regime}_W{idx:03d}"


# ---------------------------------------------------------------------------
# Regime constructors
# ---------------------------------------------------------------------------

def _make_token(
    idx: int,
    *,
    age_minutes: float,
    bonding_curve_progress: float,
    passed_initial_filter: bool = True,
    initial_market_cap_usd: float = 12_500.0,
    transaction_count: int = 42,
) -> LaunchpadTokenCandidate:
    return LaunchpadTokenCandidate(
        token_address=_SYNTHETIC_TOKEN.format(idx=idx),
        token_symbol=f"SYN{idx:02d}",
        token_name=f"Synthetic Regime {idx:02d}",
        chain="solana",
        launchpad="pumpfun",
        timestamp=_age_offset(age_minutes),
        creator_address=_SYNTHETIC_CREATOR.format(idx=idx),
        bonding_curve_progress=bonding_curve_progress,
        initial_market_cap_usd=initial_market_cap_usd,
        transaction_count=transaction_count,
        passed_initial_filter=passed_initial_filter,
        discovery_source="simulation",
    )


def _retail_wallets(
    regime: int,
    n: int,
    *,
    avg_holding_percent: float,
    spread: float = 0.5,
) -> List[WalletAuditReport]:
    """Build `n` retail wallets summing to roughly `n * avg_holding_percent`.

    Uses deterministic per-wallet variations so total ordering and sum are
    reproducible across runs.
    """
    wallets: List[WalletAuditReport] = []
    token = _SYNTHETIC_TOKEN.format(idx=regime)
    for i in range(n):
        # deterministic small variation: alternates +/-
        delta = spread * (-1.0 if i % 2 else 1.0) * (i % 3) / max(n, 1)
        holding = max(0.0, min(100.0, avg_holding_percent + delta))
        wallets.append(
            WalletAuditReport(
                wallet_hash=_SYNTHETIC_WALLET.format(regime=regime, idx=i),
                token_address=token,
                holding_percent=holding,
                entity_classification=WalletClassification.RETAIL,
                risk_contribution=0.05,
                prior_tokens_held=2,
            )
        )
    return wallets


def _whale_wallets(
    regime: int,
    n: int,
    *,
    holding_percent: float,
    risk_contribution: float = 0.7,
    prior_dumps_executed: int = 2,
) -> List[WalletAuditReport]:
    """Build `n` whale wallets, each holding `holding_percent`."""
    token = _SYNTHETIC_TOKEN.format(idx=regime)
    return [
        WalletAuditReport(
            wallet_hash=_SYNTHETIC_WALLET.format(regime=regime, idx=1000 + i),
            token_address=token,
            holding_percent=holding_percent,
            entity_classification=WalletClassification.WHALE,
            risk_contribution=risk_contribution,
            prior_tokens_held=10,
            prior_dumps_executed=prior_dumps_executed,
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# R1: organic_launch_clean_socials  →  expected CANDIDATE_FOR_FUTURE_REVIEW
# ---------------------------------------------------------------------------

def regime_R1_organic_launch_clean_socials() -> RegimeInputs:
    regime_id = "R1_organic_launch_clean_socials"
    idx = 1
    token = _SYNTHETIC_TOKEN.format(idx=idx)
    return RegimeInputs(
        regime_id=regime_id,
        description=(
            "Fresh launch (~2 min old), clean issuer track record, healthy "
            "distributed retail holders, active authentic socials, no "
            "influencer coordination."
        ),
        expected_band=DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW,
        expected_band_rationale="all components high; total_score > 70",
        candidate=_make_token(
            idx=idx,
            age_minutes=2.0,
            bonding_curve_progress=0.25,  # in the 80+ score sweet spot
            passed_initial_filter=True,
        ),
        issuer_report=EntityHistoryReport(
            entity_id=_SYNTHETIC_CREATOR.format(idx=idx),
            entity_type=EntityType.ISSUER,
            prior_token_launches=4,
            prior_rug_pulls=0,
            prior_successful_launches=4,
            average_token_lifespan_hours=720.0,  # >168 hours bonus
            average_holder_loss_percent=5.0,
            risk_classification=RiskClassification.CLEAN,
            confidence=0.95,
        ),
        wallet_reports=_retail_wallets(idx, n=20, avg_holding_percent=3.5),
        social_report=SocialPresenceReport(
            token_address=token,
            x_account_exists=True,
            x_account_age_days=365,
            x_follower_count=12_000,
            x_follower_bot_percent=8.0,
            x_engagement_authenticity=0.85,
            x_prior_token_mentions=2,
            telegram_exists=True,
            telegram_member_count=2_500,
            telegram_bot_percent=5.0,
            telegram_admin_active=True,
            telegram_spam_ratio=0.05,
            social_authenticity_score=88.0,
            evidence_completeness=0.9,
        ),
        influencer_report=InfluencerRiskReport(
            token_address=token,
            known_pumper_wallets_detected=0,
            coordinated_buy_timing_detected=False,
            influencers_with_prior_rugs=0,
            total_influencers_detected=1,
            influencer_risk_score=10.0,
            coordination_risk_score=5.0,
            evidence_completeness=0.85,
        ),
    )


# ---------------------------------------------------------------------------
# R2: influencer_pump_high_concentration  →  expected SIMULATE_ONLY
# ---------------------------------------------------------------------------

def regime_R2_influencer_pump_high_concentration() -> RegimeInputs:
    regime_id = "R2_influencer_pump_high_concentration"
    idx = 2
    token = _SYNTHETIC_TOKEN.format(idx=idx)
    return RegimeInputs(
        regime_id=regime_id,
        description=(
            "Coordinated influencer pump with heavy top-holder + whale "
            "concentration. Multiple pumper wallets detected; coordinated "
            "buy timing. Issuer clean (so it's not an issuer disqualifier "
            "— this regime stresses the whale + influencer path)."
        ),
        expected_band=DecisionBand.SIMULATE_ONLY,
        expected_band_rationale=(
            "PR #693 soft-disqualifier: influencer_risk=10 < 20 caps at SIMULATE_ONLY"
        ),
        candidate=_make_token(
            idx=idx,
            age_minutes=15.0,  # mild decay
            bonding_curve_progress=0.45,
            passed_initial_filter=True,
        ),
        issuer_report=EntityHistoryReport(
            entity_id=_SYNTHETIC_CREATOR.format(idx=idx),
            entity_type=EntityType.ISSUER,
            prior_token_launches=1,
            prior_rug_pulls=0,
            prior_successful_launches=1,
            average_token_lifespan_hours=200.0,
            average_holder_loss_percent=10.0,
            risk_classification=RiskClassification.CLEAN,
            confidence=0.7,
        ),
        wallet_reports=(
            _whale_wallets(idx, n=3, holding_percent=22.0, risk_contribution=0.9)
            + _retail_wallets(idx, n=10, avg_holding_percent=2.5)
        ),
        social_report=SocialPresenceReport(
            token_address=token,
            x_account_exists=True,
            x_account_age_days=10,
            x_follower_count=8_000,
            x_follower_bot_percent=70.0,
            x_engagement_authenticity=0.2,
            x_prior_token_mentions=0,
            telegram_exists=True,
            telegram_member_count=4_000,
            telegram_bot_percent=60.0,
            telegram_admin_active=False,
            telegram_spam_ratio=0.7,
            social_authenticity_score=18.0,
            evidence_completeness=0.85,
        ),
        influencer_report=InfluencerRiskReport(
            token_address=token,
            known_pumper_wallets_detected=4,
            coordinated_buy_timing_detected=True,
            multiple_influencers_same_token=True,
            influencer_mentions_count=7,
            influencers_with_prior_rugs=2,
            total_influencers_detected=3,
            influencer_risk_score=90.0,
            coordination_risk_score=85.0,
            evidence_completeness=0.9,
        ),
    )


# ---------------------------------------------------------------------------
# R3: dead_x_no_telegram  →  expected SIMULATE_ONLY (per PR #693 F2 finding)
# ---------------------------------------------------------------------------

def regime_R3_dead_x_no_telegram() -> RegimeInputs:
    regime_id = "R3_dead_x_no_telegram"
    idx = 3
    token = _SYNTHETIC_TOKEN.format(idx=idx)
    return RegimeInputs(
        regime_id=regime_id,
        description=(
            "Token with X account that has no real engagement and no "
            "Telegram channel. No issuer rug history, no whale concentration "
            "— this stresses the social-presence component path."
        ),
        expected_band=DecisionBand.SIMULATE_ONLY,
        expected_band_rationale=(
            "PR #693 F2: Total score 66.90 lands in [50,70) range → SIMULATE_ONLY. "
            "Social weights (0.10+0.05=0.15) too small to drag total below 50. "
            "DO NOT TUNE - this is EXPECTATION_TOO_STRICT, not a scoring defect."
        ),
        candidate=_make_token(
            idx=idx,
            age_minutes=20.0,
            bonding_curve_progress=0.12,
            passed_initial_filter=True,
        ),
        issuer_report=EntityHistoryReport(
            entity_id=_SYNTHETIC_CREATOR.format(idx=idx),
            entity_type=EntityType.ISSUER,
            prior_token_launches=0,
            prior_rug_pulls=0,
            prior_successful_launches=0,
            risk_classification=RiskClassification.CLEAN,
            confidence=0.5,
        ),
        wallet_reports=_retail_wallets(idx, n=8, avg_holding_percent=6.0),
        social_report=SocialPresenceReport(
            token_address=token,
            x_account_exists=True,
            x_account_age_days=3,
            x_follower_count=15,
            x_follower_bot_percent=10.0,
            x_engagement_authenticity=0.05,
            x_prior_token_mentions=0,
            telegram_exists=False,
            telegram_member_count=0,
            telegram_bot_percent=0.0,
            telegram_admin_active=False,
            telegram_spam_ratio=0.0,
            social_authenticity_score=5.0,
            evidence_completeness=0.7,
        ),
        influencer_report=InfluencerRiskReport(
            token_address=token,
            known_pumper_wallets_detected=0,
            coordinated_buy_timing_detected=False,
            influencers_with_prior_rugs=0,
            total_influencers_detected=0,
            influencer_risk_score=15.0,
            coordination_risk_score=5.0,
            evidence_completeness=0.6,
        ),
    )


# ---------------------------------------------------------------------------
# R4: issuer_prior_rug_history  →  expected REJECT (issuer disqualifier)
# ---------------------------------------------------------------------------

def regime_R4_issuer_prior_rug_history() -> RegimeInputs:
    regime_id = "R4_issuer_prior_rug_history"
    idx = 4
    token = _SYNTHETIC_TOKEN.format(idx=idx)
    return RegimeInputs(
        regime_id=regime_id,
        description=(
            "Issuer has 3 prior rug pulls and is FLAGGED. Should trip the "
            "issuer_history < 20 hard disqualifier and also drag "
            "rug_honeypot down. Other signals neutral-to-good — this isolates "
            "the issuer-history disqualifier."
        ),
        expected_band=DecisionBand.REJECT,
        expected_band_rationale="hard disqualifier: issuer_history < 20",
        candidate=_make_token(
            idx=idx,
            age_minutes=4.0,
            bonding_curve_progress=0.20,
            passed_initial_filter=True,
        ),
        issuer_report=EntityHistoryReport(
            entity_id=_SYNTHETIC_CREATOR.format(idx=idx),
            entity_type=EntityType.ISSUER,
            prior_token_launches=5,
            prior_rug_pulls=3,
            prior_successful_launches=1,
            average_token_lifespan_hours=2.0,
            average_holder_loss_percent=85.0,
            risk_classification=RiskClassification.FLAGGED,
            confidence=0.9,
        ),
        wallet_reports=_retail_wallets(idx, n=12, avg_holding_percent=4.0),
        social_report=SocialPresenceReport(
            token_address=token,
            x_account_exists=True,
            x_account_age_days=180,
            x_follower_count=2_000,
            x_follower_bot_percent=20.0,
            x_engagement_authenticity=0.6,
            telegram_exists=True,
            telegram_member_count=800,
            telegram_bot_percent=15.0,
            telegram_admin_active=True,
            telegram_spam_ratio=0.1,
            social_authenticity_score=65.0,
            evidence_completeness=0.75,
        ),
        influencer_report=InfluencerRiskReport(
            token_address=token,
            known_pumper_wallets_detected=0,
            influencers_with_prior_rugs=0,
            total_influencers_detected=1,
            influencer_risk_score=25.0,
            evidence_completeness=0.7,
        ),
    )


# ---------------------------------------------------------------------------
# R5: whale_accumulation_then_dump  →  expected SIMULATE_ONLY (soft disqualifier)
# ---------------------------------------------------------------------------

def regime_R5_whale_accumulation_then_dump() -> RegimeInputs:
    regime_id = "R5_whale_accumulation_then_dump"
    idx = 5
    token = _SYNTHETIC_TOKEN.format(idx=idx)
    return RegimeInputs(
        regime_id=regime_id,
        description=(
            "Several whales control most supply, multiple prior dumps "
            "executed on prior tokens by these wallets. Influencer signals "
            "absent (so this regime isolates the whale + holder_distribution "
            "path)."
        ),
        expected_band=DecisionBand.SIMULATE_ONLY,
        expected_band_rationale=(
            "PR #693 soft-disqualifier: whale_risk=14.5 < 20 caps at SIMULATE_ONLY. "
            "Total score 72.12 would reach CANDIDATE_FOR_FUTURE_REVIEW without the cap."
        ),
        candidate=_make_token(
            idx=idx,
            age_minutes=8.0,
            bonding_curve_progress=0.30,
            passed_initial_filter=True,
        ),
        issuer_report=EntityHistoryReport(
            entity_id=_SYNTHETIC_CREATOR.format(idx=idx),
            entity_type=EntityType.ISSUER,
            prior_token_launches=2,
            prior_rug_pulls=0,
            prior_successful_launches=1,
            average_token_lifespan_hours=120.0,
            average_holder_loss_percent=15.0,
            risk_classification=RiskClassification.CLEAN,
            confidence=0.7,
        ),
        wallet_reports=(
            _whale_wallets(idx, n=4, holding_percent=18.0, risk_contribution=0.85, prior_dumps_executed=3)
            + _retail_wallets(idx, n=6, avg_holding_percent=3.0)
        ),
        social_report=SocialPresenceReport(
            token_address=token,
            x_account_exists=True,
            x_account_age_days=90,
            x_follower_count=1_500,
            x_follower_bot_percent=12.0,
            x_engagement_authenticity=0.65,
            telegram_exists=True,
            telegram_member_count=600,
            telegram_bot_percent=12.0,
            telegram_admin_active=True,
            telegram_spam_ratio=0.08,
            social_authenticity_score=62.0,
            evidence_completeness=0.7,
        ),
        influencer_report=InfluencerRiskReport(
            token_address=token,
            known_pumper_wallets_detected=0,
            coordinated_buy_timing_detected=False,
            influencers_with_prior_rugs=0,
            total_influencers_detected=0,
            influencer_risk_score=15.0,
            coordination_risk_score=5.0,
            evidence_completeness=0.65,
        ),
    )


# ---------------------------------------------------------------------------
# R6: telegram_active_low_authenticity  →  expected SIMULATE_ONLY or OBSERVE
# ---------------------------------------------------------------------------

def regime_R6_telegram_active_low_authenticity() -> RegimeInputs:
    regime_id = "R6_telegram_active_low_authenticity"
    idx = 6
    token = _SYNTHETIC_TOKEN.format(idx=idx)
    return RegimeInputs(
        regime_id=regime_id,
        description=(
            "Telegram looks busy on the surface (high member count, admin "
            "active) but bot ratio and spam ratio are high; X account "
            "engagement authenticity low. Issuer clean. Tests the social_"
            "authenticity vs telegram_quality split."
        ),
        expected_band=DecisionBand.SIMULATE_ONLY,
        expected_band_rationale=(
            "median scores everywhere except social; total expected 50-70"
        ),
        candidate=_make_token(
            idx=idx,
            age_minutes=3.0,
            bonding_curve_progress=0.30,
            passed_initial_filter=True,
        ),
        issuer_report=EntityHistoryReport(
            entity_id=_SYNTHETIC_CREATOR.format(idx=idx),
            entity_type=EntityType.ISSUER,
            prior_token_launches=2,
            prior_rug_pulls=0,
            prior_successful_launches=2,
            average_token_lifespan_hours=400.0,
            average_holder_loss_percent=10.0,
            risk_classification=RiskClassification.CLEAN,
            confidence=0.8,
        ),
        wallet_reports=_retail_wallets(idx, n=18, avg_holding_percent=4.0),
        social_report=SocialPresenceReport(
            token_address=token,
            x_account_exists=True,
            x_account_age_days=60,
            x_follower_count=5_000,
            x_follower_bot_percent=55.0,
            x_engagement_authenticity=0.25,
            telegram_exists=True,
            telegram_member_count=2_000,  # > 1000 → +20
            telegram_bot_percent=45.0,    # large penalty
            telegram_admin_active=True,
            telegram_spam_ratio=0.4,
            social_authenticity_score=35.0,
            evidence_completeness=0.8,
        ),
        influencer_report=InfluencerRiskReport(
            token_address=token,
            known_pumper_wallets_detected=1,
            coordinated_buy_timing_detected=False,
            influencers_with_prior_rugs=0,
            total_influencers_detected=2,
            influencer_risk_score=30.0,
            coordination_risk_score=20.0,
            evidence_completeness=0.75,
        ),
    )


# ---------------------------------------------------------------------------
# R7: bonding_curve_migration_risk  →  expected CANDIDATE_FOR_FUTURE_REVIEW (per PR #693 F5)
# ---------------------------------------------------------------------------

def regime_R7_bonding_curve_migration_risk() -> RegimeInputs:
    regime_id = "R7_bonding_curve_migration_risk"
    idx = 7
    token = _SYNTHETIC_TOKEN.format(idx=idx)
    return RegimeInputs(
        regime_id=regime_id,
        description=(
            "Bonding curve well past the sweet spot (progress=0.85). Other "
            "signals are reasonable. Tests the bonding-curve-late penalty in "
            "isolation."
        ),
        expected_band=DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW,
        expected_band_rationale=(
            "PR #693 F5: bonding_curve weight (0.05) too small to drop total below 70. "
            "Total score 89.70 reaches CANDIDATE_FOR_FUTURE_REVIEW. "
            "DO NOT TUNE - this is ACCEPTABLE_BEHAVIOR per decision-shape review."
        ),
        candidate=_make_token(
            idx=idx,
            age_minutes=2.0,
            bonding_curve_progress=0.85,
            passed_initial_filter=True,
        ),
        issuer_report=EntityHistoryReport(
            entity_id=_SYNTHETIC_CREATOR.format(idx=idx),
            entity_type=EntityType.ISSUER,
            prior_token_launches=3,
            prior_rug_pulls=0,
            prior_successful_launches=3,
            average_token_lifespan_hours=500.0,
            average_holder_loss_percent=8.0,
            risk_classification=RiskClassification.CLEAN,
            confidence=0.85,
        ),
        wallet_reports=_retail_wallets(idx, n=16, avg_holding_percent=4.0),
        social_report=SocialPresenceReport(
            token_address=token,
            x_account_exists=True,
            x_account_age_days=200,
            x_follower_count=6_000,
            x_follower_bot_percent=10.0,
            x_engagement_authenticity=0.8,
            telegram_exists=True,
            telegram_member_count=1_500,
            telegram_bot_percent=8.0,
            telegram_admin_active=True,
            telegram_spam_ratio=0.07,
            social_authenticity_score=78.0,
            evidence_completeness=0.85,
        ),
        influencer_report=InfluencerRiskReport(
            token_address=token,
            known_pumper_wallets_detected=0,
            coordinated_buy_timing_detected=False,
            influencers_with_prior_rugs=0,
            total_influencers_detected=1,
            influencer_risk_score=18.0,
            coordination_risk_score=10.0,
            evidence_completeness=0.8,
        ),
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_REGIME_CONSTRUCTORS: List[Callable[[], RegimeInputs]] = [
    regime_R1_organic_launch_clean_socials,
    regime_R2_influencer_pump_high_concentration,
    regime_R3_dead_x_no_telegram,
    regime_R4_issuer_prior_rug_history,
    regime_R5_whale_accumulation_then_dump,
    regime_R6_telegram_active_low_authenticity,
    regime_R7_bonding_curve_migration_risk,
]


# ---------------------------------------------------------------------------
# Result schema + helpers (used by the regime tests + audit-doc generation)
# ---------------------------------------------------------------------------

# Hard-disqualifier names that determine_decision_band() checks.
HARD_DISQUALIFIER_NAMES = (
    "rug_honeypot_below_20",
    "issuer_history_below_20",
    "evidence_confidence_below_0_5",
)


def detect_hard_disqualifiers(score: TradeDueDiligenceScore) -> List[str]:
    """Which hard disqualifiers (from contracts.determine_decision_band) tripped."""
    out: List[str] = []
    if score.rug_honeypot < 20:
        out.append("rug_honeypot_below_20")
    if score.issuer_history < 20:
        out.append("issuer_history_below_20")
    if score.evidence_confidence < 0.5:
        out.append("evidence_confidence_below_0_5")
    return out


def component_scores(score: TradeDueDiligenceScore) -> Dict[str, float]:
    """Component-only score map (no aggregates, no timestamp)."""
    return {
        "launch_timing": score.launch_timing,
        "issuer_history": score.issuer_history,
        "social_authenticity": score.social_authenticity,
        "telegram_quality": score.telegram_quality,
        "influencer_risk": score.influencer_risk,
        "holder_distribution": score.holder_distribution,
        "whale_risk": score.whale_risk,
        "prior_token_history": score.prior_token_history,
        "bonding_curve": score.bonding_curve,
        "rug_honeypot": score.rug_honeypot,
    }


# Post-#691 (clock fix): the scoring engine no longer reads an implicit
# clock. Same (regime inputs, evaluation_time) → byte-identical component
# scores. No rounding is applied to the deterministic_hash payload — the
# hash captures the full float precision of every component.


def deterministic_hash(score: TradeDueDiligenceScore) -> str:
    """SHA-256 hex hash of the component-score fingerprint.

    Uses RAW (non-rounded) component scores + total_score + risk_score +
    evidence_confidence + decision_band + the set of hard disqualifiers
    triggered. Timestamp is excluded (it's an input to scoring, not an
    output). Post-#691, scoring is fully deterministic without rounding.
    """
    payload = {
        "components": component_scores(score),
        "total_score": score.total_score,
        "risk_score": score.risk_score,
        "evidence_confidence": score.evidence_confidence,
        "decision_band": score.decision_band.value,
        "hard_disqualifiers": sorted(detect_hard_disqualifiers(score)),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_regime_result(
    regime: RegimeInputs,
    score: TradeDueDiligenceScore,
) -> Dict[str, Any]:
    """Construct the per-regime result record (audit + test consume this).

    Raw float scores (no rounding). Post-#691, byte-identical determinism
    holds without a rounding mask.
    """
    actual_band = score.decision_band
    return {
        "regime_id": regime.regime_id,
        "description": regime.description,
        "expected_band": regime.expected_band.value,
        "actual_band": actual_band.value,
        "band_match": (actual_band == regime.expected_band),
        "total_score": score.total_score,
        "risk_score": score.risk_score,
        "evidence_confidence": score.evidence_confidence,
        "component_scores": component_scores(score),
        "hard_disqualifiers_triggered": sorted(detect_hard_disqualifiers(score)),
        "deterministic_hash": deterministic_hash(score),
        "band_rationale": score.band_rationale,
    }


# Sanity check at import time — every regime must be uniquely IDed.
def _validate_registry_unique_ids() -> None:
    seen: Set[str] = set()
    for ctor in ALL_REGIME_CONSTRUCTORS:
        rid = ctor().regime_id
        if rid in seen:
            raise AssertionError(f"Duplicate regime_id {rid!r} in registry")
        seen.add(rid)


_validate_registry_unique_ids()
