"""Trade Due Diligence Scoring Engine

Deterministic scoring engine for pump.fun token due diligence.
Pure computation - no network calls, wallet access, or order placement.

WSP References:
- WSP 97: Truth Boundaries (no false execution claims)
- WSP 104: FoundUp Route Namespace

Spec: TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1 (PR #683)
Slice: TRADE_DUE_DILIGENCE_SCORING_ENGINE_PHASE1

Inputs:
- EntityHistoryReport (issuer/influencer history)
- WalletAuditReport[] (holder distribution)
- SocialPresenceReport (X/Telegram signals)
- InfluencerRiskReport (pump coordination)
- LaunchpadTokenCandidate (token metadata)

Output:
- TradeDueDiligenceScore with all 10 components filled
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

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


def _clamp(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Clamp value to range [min_val, max_val]."""
    return max(min_val, min(max_val, value))


# ---------------------------------------------------------------------------
# Component Scorers (pure functions, deterministic)
# ---------------------------------------------------------------------------


def score_launch_timing(candidate: LaunchpadTokenCandidate, evaluation_time: datetime) -> float:
    """Score launch timing (0-100).

    Fresh launches (< 5 min) score higher.
    Older launches lose points progressively.

    Args:
        candidate: Token candidate with timestamp
        evaluation_time: Timezone-aware datetime for evaluation (must have tzinfo)

    Spec Section 8.1: launch_timing weight = 0.10
    """
    age_seconds = (evaluation_time - candidate.timestamp).total_seconds()

    if age_seconds < 0:
        age_seconds = 0

    age_minutes = age_seconds / 60.0

    if age_minutes < 5:
        return 100.0
    elif age_minutes < 30:
        decay = (age_minutes - 5) / 25 * 30
        return _clamp(100.0 - decay)
    elif age_minutes < 60:
        decay = 30 + (age_minutes - 30) / 30 * 20
        return _clamp(100.0 - decay)
    elif age_minutes < 360:
        decay = 50 + (age_minutes - 60) / 300 * 30
        return _clamp(100.0 - decay)
    else:
        return 20.0


def score_issuer_history(report: Optional[EntityHistoryReport]) -> float:
    """Score issuer history (0-100).

    Clean history scores high. Rug pulls severely penalize.

    Spec Section 8.1: issuer_history weight = 0.15
    """
    if report is None:
        return 50.0

    base_score = 100.0

    if report.prior_rug_pulls > 0:
        penalty = min(report.prior_rug_pulls * 40, 80)
        base_score -= penalty

    if report.prior_token_launches > 0:
        rug_ratio = report.prior_rug_pulls / report.prior_token_launches
        if rug_ratio > 0.5:
            base_score -= 20
        elif rug_ratio > 0.25:
            base_score -= 10

    if report.risk_classification == RiskClassification.BLACKLISTED:
        return 0.0
    elif report.risk_classification == RiskClassification.FLAGGED:
        base_score = min(base_score, 30.0)
    elif report.risk_classification == RiskClassification.SUSPICIOUS:
        base_score = min(base_score, 50.0)

    confidence_factor = 0.5 + (report.confidence * 0.5)
    base_score *= confidence_factor

    return _clamp(base_score)


def score_social_authenticity(report: Optional[SocialPresenceReport]) -> float:
    """Score social authenticity (0-100).

    Real communities with genuine engagement score high.

    Spec Section 8.1: social_authenticity weight = 0.10
    """
    if report is None:
        return 30.0

    return _clamp(report.social_authenticity_score)


def score_telegram_quality(report: Optional[SocialPresenceReport]) -> float:
    """Score Telegram quality (0-100).

    Active, non-bot Telegram communities score high.

    Spec Section 8.1: telegram_quality weight = 0.05
    """
    if report is None:
        return 30.0

    if not report.telegram_exists:
        return 20.0

    base_score = 50.0

    if report.telegram_member_count > 1000:
        base_score += 20.0
    elif report.telegram_member_count > 500:
        base_score += 15.0
    elif report.telegram_member_count > 100:
        base_score += 10.0

    if report.telegram_admin_active:
        base_score += 10.0

    bot_penalty = report.telegram_bot_percent * 0.5
    base_score -= bot_penalty

    spam_penalty = report.telegram_spam_ratio * 30
    base_score -= spam_penalty

    return _clamp(base_score)


def score_influencer_risk(report: Optional[InfluencerRiskReport]) -> float:
    """Score influencer risk (0-100, inverted: high = low risk).

    Low influencer manipulation risk scores high.

    Spec Section 8.1: influencer_risk weight = 0.10
    """
    if report is None:
        return 60.0

    risk = report.influencer_risk_score
    return _clamp(100.0 - risk)


def score_holder_distribution(wallet_reports: List[WalletAuditReport]) -> float:
    """Score holder distribution (0-100).

    Well-distributed holdings score high.
    Top holder concentration severely penalizes.

    Spec Section 8.1: holder_distribution weight = 0.15
    """
    if not wallet_reports:
        return 40.0

    total_holding = sum(w.holding_percent for w in wallet_reports)

    if total_holding < 50:
        return 50.0

    sorted_wallets = sorted(wallet_reports, key=lambda w: w.holding_percent, reverse=True)

    top_holder_pct = sorted_wallets[0].holding_percent if sorted_wallets else 0.0
    top_10_pct = sum(w.holding_percent for w in sorted_wallets[:10])

    score = 100.0

    if top_holder_pct > 50:
        return 10.0
    elif top_holder_pct > 30:
        score -= 50
    elif top_holder_pct > 20:
        score -= 30
    elif top_holder_pct > 10:
        score -= 15

    if top_10_pct > 80:
        score -= 30
    elif top_10_pct > 60:
        score -= 15

    return _clamp(score)


def score_whale_risk(wallet_reports: List[WalletAuditReport]) -> float:
    """Score whale risk (0-100, inverted: high = low risk).

    Low whale manipulation risk scores high.

    Spec Section 8.1: whale_risk weight = 0.10
    """
    if not wallet_reports:
        return 50.0

    whale_wallets = [w for w in wallet_reports if w.entity_classification == WalletClassification.WHALE]

    if not whale_wallets:
        return 90.0

    total_whale_holding = sum(w.holding_percent for w in whale_wallets)
    whale_risk_contributions = sum(w.risk_contribution for w in whale_wallets)

    score = 100.0

    if total_whale_holding > 50:
        score -= 60
    elif total_whale_holding > 30:
        score -= 40
    elif total_whale_holding > 15:
        score -= 20

    avg_risk = whale_risk_contributions / len(whale_wallets) if whale_wallets else 0
    score -= avg_risk * 30

    return _clamp(score)


def score_prior_token_history(
    report: Optional[EntityHistoryReport],
    candidate: LaunchpadTokenCandidate
) -> float:
    """Score prior token history (0-100).

    Positive track record scores high.

    Spec Section 8.1: prior_token_history weight = 0.10
    """
    if report is None:
        return 50.0

    if report.prior_token_launches == 0:
        return 60.0

    success_ratio = (
        report.prior_successful_launches / report.prior_token_launches
        if report.prior_token_launches > 0 else 0.0
    )

    base_score = 50.0 + (success_ratio * 40)

    if report.average_token_lifespan_hours > 168:
        base_score += 10.0
    elif report.average_token_lifespan_hours > 24:
        base_score += 5.0
    elif report.average_token_lifespan_hours < 1:
        base_score -= 20.0

    if report.average_holder_loss_percent > 50:
        base_score -= 30.0
    elif report.average_holder_loss_percent > 25:
        base_score -= 15.0

    return _clamp(base_score)


def score_bonding_curve(candidate: LaunchpadTokenCandidate) -> float:
    """Score bonding curve progression (0-100).

    Healthy curve progression (10-50%) scores highest.
    Too early or too late penalized.

    Spec Section 8.1: bonding_curve weight = 0.05
    """
    progress = candidate.bonding_curve_progress

    if progress < 0.05:
        return 30.0
    elif progress < 0.10:
        return 50.0 + (progress - 0.05) / 0.05 * 30
    elif progress <= 0.50:
        return 80.0 + (0.50 - progress) / 0.40 * 20
    elif progress <= 0.80:
        return 80.0 - (progress - 0.50) / 0.30 * 30
    else:
        return 50.0 - (progress - 0.80) / 0.20 * 30

    return _clamp(50.0)


def score_rug_honeypot(
    issuer_report: Optional[EntityHistoryReport],
    influencer_report: Optional[InfluencerRiskReport],
    wallet_reports: List[WalletAuditReport]
) -> float:
    """Score rug/honeypot risk (0-100, inverted: high = low risk).

    Low exit risk scores high. This is a critical disqualifier.

    Spec Section 8.1: rug_honeypot weight = 0.10
    """
    score = 100.0

    if issuer_report:
        if issuer_report.prior_rug_pulls > 0:
            score -= min(issuer_report.prior_rug_pulls * 25, 60)

        if issuer_report.risk_classification == RiskClassification.BLACKLISTED:
            return 0.0
        elif issuer_report.risk_classification == RiskClassification.FLAGGED:
            score -= 30

    if influencer_report:
        if influencer_report.influencers_with_prior_rugs > 0:
            score -= min(influencer_report.influencers_with_prior_rugs * 15, 40)

        if influencer_report.coordinated_buy_timing_detected:
            score -= 20

    if wallet_reports:
        scammer_wallets = [
            w for w in wallet_reports
            if w.entity_classification == WalletClassification.SCAMMER
        ]
        if scammer_wallets:
            scammer_holding = sum(w.holding_percent for w in scammer_wallets)
            score -= min(scammer_holding * 2, 50)

    return _clamp(score)


# ---------------------------------------------------------------------------
# Evidence Confidence Calculation
# ---------------------------------------------------------------------------


def calculate_evidence_confidence(
    issuer_report: Optional[EntityHistoryReport],
    wallet_reports: List[WalletAuditReport],
    social_report: Optional[SocialPresenceReport],
    influencer_report: Optional[InfluencerRiskReport],
    candidate: LaunchpadTokenCandidate
) -> float:
    """Calculate overall evidence confidence (0.0-1.0).

    Based on completeness and confidence of input reports.
    """
    components = []

    if issuer_report is not None:
        components.append(issuer_report.confidence)
    else:
        components.append(0.0)

    if wallet_reports:
        components.append(min(len(wallet_reports) / 20, 1.0))
    else:
        components.append(0.0)

    if social_report is not None:
        components.append(social_report.evidence_completeness)
    else:
        components.append(0.0)

    if influencer_report is not None:
        components.append(influencer_report.evidence_completeness)
    else:
        components.append(0.0)

    components.append(1.0 if candidate.passed_initial_filter else 0.5)

    if not components:
        return 0.0

    return sum(components) / len(components)


# ---------------------------------------------------------------------------
# Main Scoring Engine
# ---------------------------------------------------------------------------


@dataclass
class DueDiligenceScoringEngine:
    """Deterministic due-diligence scoring engine.

    Pure computation - no network, no wallet, no trading.
    """

    def score(
        self,
        candidate: LaunchpadTokenCandidate,
        *,
        evaluation_time: datetime,
        issuer_report: Optional[EntityHistoryReport] = None,
        wallet_reports: Optional[List[WalletAuditReport]] = None,
        social_report: Optional[SocialPresenceReport] = None,
        influencer_report: Optional[InfluencerRiskReport] = None,
    ) -> TradeDueDiligenceScore:
        """Score a token candidate and produce TradeDueDiligenceScore.

        Args:
            candidate: Token candidate from launchpad discovery
            evaluation_time: Timezone-aware datetime for evaluation.
                Must have tzinfo set. Non-UTC timezones are normalized to UTC.
            issuer_report: Optional issuer/creator history
            wallet_reports: Optional list of wallet audit reports
            social_report: Optional social presence analysis
            influencer_report: Optional influencer risk analysis

        Returns:
            TradeDueDiligenceScore with all components filled

        Raises:
            ValueError: If evaluation_time is naive (no tzinfo)
        """
        if evaluation_time.tzinfo is None:
            raise ValueError(
                "evaluation_time must be timezone-aware (use datetime with tzinfo). "
                "Naive datetimes are rejected to ensure deterministic scoring."
            )

        evaluation_time = evaluation_time.astimezone(timezone.utc)

        wallet_reports = wallet_reports or []

        launch_timing = score_launch_timing(candidate, evaluation_time)
        issuer_history = score_issuer_history(issuer_report)
        social_authenticity = score_social_authenticity(social_report)
        telegram_quality = score_telegram_quality(social_report)
        influencer_risk = score_influencer_risk(influencer_report)
        holder_distribution = score_holder_distribution(wallet_reports)
        whale_risk = score_whale_risk(wallet_reports)
        prior_token_history = score_prior_token_history(issuer_report, candidate)
        bonding_curve = score_bonding_curve(candidate)
        rug_honeypot = score_rug_honeypot(issuer_report, influencer_report, wallet_reports)

        evidence_confidence = calculate_evidence_confidence(
            issuer_report, wallet_reports, social_report, influencer_report, candidate
        )

        result = TradeDueDiligenceScore(
            token_address=candidate.token_address,
            timestamp=candidate.timestamp,
            launch_timing=launch_timing,
            issuer_history=issuer_history,
            social_authenticity=social_authenticity,
            telegram_quality=telegram_quality,
            influencer_risk=influencer_risk,
            holder_distribution=holder_distribution,
            whale_risk=whale_risk,
            prior_token_history=prior_token_history,
            bonding_curve=bonding_curve,
            rug_honeypot=rug_honeypot,
            evidence_confidence=evidence_confidence,
        )

        result.total_score = result.calculate_total_score()
        result.risk_score = 100.0 - result.total_score
        result.decision_band = result.determine_decision_band()
        result.band_rationale = _generate_rationale(result)

        return result


def _generate_rationale(score: TradeDueDiligenceScore) -> str:
    """Generate human-readable rationale for decision band."""
    band = score.decision_band

    if score.rug_honeypot < 20:
        return f"REJECT: Critical rug/honeypot risk (score={score.rug_honeypot:.1f})"

    if score.issuer_history < 20:
        return f"REJECT: Critical issuer history risk (score={score.issuer_history:.1f})"

    if score.evidence_confidence < 0.5:
        return f"OBSERVE: Insufficient evidence (confidence={score.evidence_confidence:.2f})"

    if band == DecisionBand.REJECT:
        return f"REJECT: Total score {score.total_score:.1f} below threshold (30)"
    elif band == DecisionBand.OBSERVE:
        return f"OBSERVE: Total score {score.total_score:.1f} in observation range (30-50)"
    elif band == DecisionBand.SIMULATE_ONLY:
        return f"SIMULATE_ONLY: Total score {score.total_score:.1f} qualifies for simulation (50-70)"
    else:
        return f"CANDIDATE: Total score {score.total_score:.1f} qualifies for future review (>70)"


def create_scoring_engine() -> DueDiligenceScoringEngine:
    """Factory function to create a scoring engine instance."""
    return DueDiligenceScoringEngine()


DEFAULT_SCORING_ENGINE = DueDiligenceScoringEngine()
