"""Trade Harness Scoring Integration

Integration layer between SimulationHarness and DueDiligenceScoringEngine.
Provides opt-in scoring gate for filtering strategy intents based on
decision bands.

WSP References:
- WSP 97: Truth Boundaries (simulation-only, no real trading)
- WSP 104: FoundUp Route Namespace

Slice: TRADE_HARNESS_INTEGRATION_WITH_SCORING_PHASE1

This integration is OPT-IN ONLY. Default behavior is disabled (no scoring gate).
When enabled, intents are filtered per decision band:
- REJECT: synthetic strategy intent is blocked for this bar
- OBSERVE: synthetic strategy intent is blocked; observation/audit note only
- SIMULATE_ONLY: synthetic strategy intent may continue inside simulation only
- CANDIDATE_FOR_FUTURE_REVIEW: synthetic strategy intent may continue inside simulation

No band authorizes external order placement, wallet signing, live feeds,
real trading, or public readiness.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from .contracts import (
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
    from .simulation_harness import (
        IntentType,
        StrategyIntent,
        SyntheticBar,
        SimulationState,
    )
    from .due_diligence_scoring import DueDiligenceScoringEngine
except ImportError:
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
    from simulation_harness import (
        IntentType,
        StrategyIntent,
        SyntheticBar,
        SimulationState,
    )
    from due_diligence_scoring import DueDiligenceScoringEngine


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Bands that ALLOW synthetic strategy intents to proceed in simulation
ALLOWED_BANDS = frozenset({
    DecisionBand.SIMULATE_ONLY,
    DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW,
})

# Bands that BLOCK synthetic strategy intents
BLOCKED_BANDS = frozenset({
    DecisionBand.REJECT,
    DecisionBand.OBSERVE,
})


# ---------------------------------------------------------------------------
# Gate Action
# ---------------------------------------------------------------------------


class GateAction(str, Enum):
    """Result of scoring gate evaluation."""

    ALLOW = "allow"  # Intent may proceed in simulation
    BLOCK = "block"  # Intent is blocked
    OBSERVE = "observe"  # Intent is blocked, observation/audit note only


# ---------------------------------------------------------------------------
# Gate Result
# ---------------------------------------------------------------------------


@dataclass
class ScoringGateResult:
    """Result of scoring gate evaluation."""

    action: GateAction
    original_intent: StrategyIntent
    filtered_intent: StrategyIntent
    decision_band: DecisionBand
    total_score: float
    risk_score: float
    evidence_confidence: float
    gate_rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "original_intent": self.original_intent.to_dict(),
            "filtered_intent": self.filtered_intent.to_dict(),
            "decision_band": self.decision_band.value,
            "total_score": round(self.total_score, 2),
            "risk_score": round(self.risk_score, 2),
            "evidence_confidence": round(self.evidence_confidence, 2),
            "gate_rationale": self.gate_rationale,
        }


# ---------------------------------------------------------------------------
# Synthetic Candidate Derivation
# ---------------------------------------------------------------------------


def derive_synthetic_candidate(
    bar: SyntheticBar,
    seed: int,
    evaluation_time: datetime,
) -> LaunchpadTokenCandidate:
    """Derive a synthetic LaunchpadTokenCandidate from bar state.

    This is a DETERMINISTIC transformation from (bar, seed) to candidate.
    NO live data. All fields are synthetic and deterministic.

    The derivation uses bar properties to create plausible-looking
    candidate fields while maintaining determinism:
    - token_address/symbol/name derived from seed + bar_index hash
    - bonding_curve_progress derived from bar_index / 100 (capped)
    - initial_market_cap_usd derived from bar close_price * volume
    - transaction_count derived from volume / 100

    Args:
        bar: Synthetic bar from harness
        seed: Simulation seed for determinism
        evaluation_time: Evaluation timestamp (must be timezone-aware)

    Returns:
        Synthetic LaunchpadTokenCandidate
    """
    # Deterministic hash for synthetic identifiers
    id_hash = hashlib.sha256(f"{seed}-{bar.bar_index}".encode()).hexdigest()

    # Synthetic token address (looks like Solana base58)
    token_address = f"SYN{id_hash[:40].upper()}"

    # Synthetic symbol from hash
    symbol = f"SYN{id_hash[:4].upper()}"

    # Synthetic name
    name = f"Synthetic Token {bar.bar_index}"

    # Synthetic creator address
    creator = f"CREATOR{id_hash[40:60].upper()}"

    # Bonding curve progress: increases with bar_index, capped at 0.95
    bonding_progress = min(bar.bar_index / 100.0, 0.95)

    # Market cap from price * volume (scaled down)
    market_cap = bar.close_price * bar.volume / 1000.0

    # Transaction count from volume
    tx_count = max(bar.volume // 100, 1)

    # Timestamp: evaluation_time minus some minutes based on bar_index
    # This simulates "age" of the token at evaluation
    from datetime import timedelta
    token_timestamp = evaluation_time - timedelta(minutes=bar.bar_index * 0.5)

    return LaunchpadTokenCandidate(
        token_address=token_address,
        token_symbol=symbol,
        token_name=name,
        chain="solana",
        launchpad="pumpfun",
        timestamp=token_timestamp,
        creator_address=creator,
        bonding_curve_progress=bonding_progress,
        initial_market_cap_usd=market_cap,
        transaction_count=tx_count,
        passed_initial_filter=True,
        discovery_source="simulation",
    )


def derive_synthetic_reports(
    bar: SyntheticBar,
    seed: int,
) -> tuple[
    Optional[EntityHistoryReport],
    List[WalletAuditReport],
    Optional[SocialPresenceReport],
    Optional[InfluencerRiskReport],
]:
    """Derive synthetic reports from bar state.

    Creates deterministic synthetic reports for scoring. All values are
    derived from bar properties and seed to ensure reproducibility.

    Args:
        bar: Synthetic bar from harness
        seed: Simulation seed for determinism

    Returns:
        Tuple of (issuer_report, wallet_reports, social_report, influencer_report)
    """
    # Deterministic hash for variation
    var_hash = hashlib.sha256(f"{seed}-{bar.bar_index}-reports".encode()).hexdigest()
    var_int = int(var_hash[:8], 16)

    # Synthetic issuer report
    # Clean history for most, occasional rug history based on hash
    rug_pulls = 1 if var_int % 20 == 0 else 0  # 5% chance of rug history
    issuer_report = EntityHistoryReport(
        entity_id=f"ISSUER{var_hash[:20].upper()}",
        entity_type=EntityType.ISSUER,
        prior_token_launches=max(1, var_int % 10),
        prior_rug_pulls=rug_pulls,
        prior_successful_launches=max(0, (var_int % 10) - rug_pulls),
        average_token_lifespan_hours=float((var_int % 500) + 100),
        average_holder_loss_percent=float((var_int % 30)),
        risk_classification=(
            RiskClassification.FLAGGED if rug_pulls > 0
            else RiskClassification.CLEAN
        ),
        confidence=0.7 + (var_int % 30) / 100.0,
    )

    # Synthetic wallet reports (5-15 wallets)
    wallet_count = 5 + (var_int % 11)
    wallet_reports: List[WalletAuditReport] = []
    for i in range(wallet_count):
        wallet_hash = hashlib.sha256(f"{seed}-{bar.bar_index}-w{i}".encode()).hexdigest()
        wallet_int = int(wallet_hash[:8], 16)

        # Distribution: most are retail, some are whales
        is_whale = wallet_int % 10 == 0  # 10% chance
        holding = float(wallet_int % 15 + 1) if not is_whale else float(wallet_int % 20 + 10)

        wallet_reports.append(WalletAuditReport(
            wallet_hash=f"WALLET{wallet_hash[:20].upper()}",
            token_address=f"SYN{var_hash[:40].upper()}",
            holding_percent=holding,
            entity_classification=(
                WalletClassification.WHALE if is_whale
                else WalletClassification.RETAIL
            ),
            risk_contribution=0.8 if is_whale else 0.1,
            prior_tokens_held=wallet_int % 50 + 1,
        ))

    # Synthetic social report
    social_report = SocialPresenceReport(
        token_address=f"SYN{var_hash[:40].upper()}",
        x_account_exists=var_int % 4 != 0,  # 75% have X
        x_account_age_days=(var_int % 365) + 1,
        x_follower_count=(var_int % 10000) + 100,
        x_follower_bot_percent=float(var_int % 40),
        x_engagement_authenticity=0.3 + (var_int % 60) / 100.0,
        x_prior_token_mentions=var_int % 5,
        telegram_exists=var_int % 3 != 0,  # 66% have Telegram
        telegram_member_count=(var_int % 5000) + 50,
        telegram_bot_percent=float(var_int % 50),
        telegram_admin_active=var_int % 2 == 0,
        telegram_spam_ratio=(var_int % 30) / 100.0,
        social_authenticity_score=30.0 + float(var_int % 60),
        evidence_completeness=0.5 + (var_int % 40) / 100.0,
    )

    # Synthetic influencer report
    influencer_report = InfluencerRiskReport(
        token_address=f"SYN{var_hash[:40].upper()}",
        known_pumper_wallets_detected=var_int % 3,
        coordinated_buy_timing_detected=var_int % 10 == 0,
        influencers_with_prior_rugs=var_int % 2,
        total_influencers_detected=var_int % 5,
        influencer_risk_score=float(var_int % 80),
        coordination_risk_score=float(var_int % 50),
        evidence_completeness=0.6 + (var_int % 30) / 100.0,
    )

    return issuer_report, wallet_reports, social_report, influencer_report


# ---------------------------------------------------------------------------
# Scoring Gate
# ---------------------------------------------------------------------------


class ScoringGate:
    """Scoring gate for filtering strategy intents.

    OPT-IN ONLY: disabled by default. When enabled, evaluates intents
    against the due-diligence scoring engine and blocks/allows based
    on decision band.

    Integration hook point: per-bar, before intent execution.
    """

    def __init__(
        self,
        enabled: bool = False,
        seed: int = 42,
        base_evaluation_time: Optional[datetime] = None,
    ) -> None:
        """Initialize scoring gate.

        Args:
            enabled: Whether scoring gate is active (default: False)
            seed: Simulation seed for deterministic candidate derivation
            base_evaluation_time: Base timestamp for evaluation. If None,
                uses a fixed deterministic time. Must be timezone-aware.
        """
        self.enabled = enabled
        self.seed = seed

        # Default to fixed deterministic time for reproducibility
        self._base_time = base_evaluation_time or datetime(
            2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc
        )

        self._engine: Optional[DueDiligenceScoringEngine] = None
        self._gate_results: List[ScoringGateResult] = []

    def _get_engine(self) -> DueDiligenceScoringEngine:
        """Lazy-initialize scoring engine."""
        if self._engine is None:
            self._engine = DueDiligenceScoringEngine()
        return self._engine

    def _get_evaluation_time(self, bar: SyntheticBar) -> datetime:
        """Get evaluation time for a bar.

        Uses base time plus bar_index minutes to simulate progression.
        """
        from datetime import timedelta
        return self._base_time + timedelta(minutes=bar.bar_index)

    def apply(
        self,
        bar: SyntheticBar,
        intent: StrategyIntent,
        state: SimulationState,
    ) -> StrategyIntent:
        """Apply scoring gate to an intent.

        If gate is disabled, returns intent unchanged (passthrough).
        If gate is enabled, evaluates intent against scoring engine
        and may block or allow based on decision band.

        Args:
            bar: Current synthetic bar
            intent: Strategy's intended action
            state: Current simulation state

        Returns:
            Filtered intent (may be HOLD if blocked)
        """
        # Passthrough if disabled
        if not self.enabled:
            return intent

        # Only gate BUY intents (SELL/HOLD pass through)
        if intent.intent_type != IntentType.BUY:
            return intent

        # Derive synthetic candidate and reports
        evaluation_time = self._get_evaluation_time(bar)
        candidate = derive_synthetic_candidate(bar, self.seed, evaluation_time)
        issuer, wallets, social, influencer = derive_synthetic_reports(bar, self.seed)

        # Score the candidate
        engine = self._get_engine()
        score = engine.score(
            candidate=candidate,
            issuer_report=issuer,
            wallet_reports=wallets,
            social_report=social,
            influencer_report=influencer,
            evaluation_time=evaluation_time,
        )

        # Determine gate action
        if score.decision_band in BLOCKED_BANDS:
            action = (
                GateAction.OBSERVE if score.decision_band == DecisionBand.OBSERVE
                else GateAction.BLOCK
            )
            filtered_intent = StrategyIntent(IntentType.HOLD)
            rationale = f"Intent blocked: {score.decision_band.value}"
        else:
            action = GateAction.ALLOW
            filtered_intent = intent
            rationale = f"Intent allowed: {score.decision_band.value}"

        # Record result
        result = ScoringGateResult(
            action=action,
            original_intent=intent,
            filtered_intent=filtered_intent,
            decision_band=score.decision_band,
            total_score=score.total_score,
            risk_score=score.risk_score,
            evidence_confidence=score.evidence_confidence,
            gate_rationale=rationale,
        )
        self._gate_results.append(result)

        return filtered_intent

    def get_results(self) -> List[ScoringGateResult]:
        """Get all gate evaluation results."""
        return self._gate_results.copy()

    def get_summary(self) -> Dict[str, Any]:
        """Get gate summary statistics."""
        if not self._gate_results:
            return {
                "enabled": self.enabled,
                "total_evaluations": 0,
                "allowed": 0,
                "blocked": 0,
                "observed": 0,
            }

        allowed = sum(1 for r in self._gate_results if r.action == GateAction.ALLOW)
        blocked = sum(1 for r in self._gate_results if r.action == GateAction.BLOCK)
        observed = sum(1 for r in self._gate_results if r.action == GateAction.OBSERVE)

        return {
            "enabled": self.enabled,
            "total_evaluations": len(self._gate_results),
            "allowed": allowed,
            "blocked": blocked,
            "observed": observed,
            "band_distribution": {
                band.value: sum(
                    1 for r in self._gate_results if r.decision_band == band
                )
                for band in DecisionBand
            },
        }

    def reset(self) -> None:
        """Reset gate state (clear results)."""
        self._gate_results.clear()


# ---------------------------------------------------------------------------
# Integration Helper
# ---------------------------------------------------------------------------


def apply_scoring_gate(
    bar: SyntheticBar,
    intent: StrategyIntent,
    state: SimulationState,
    gate: Optional[ScoringGate] = None,
) -> StrategyIntent:
    """Apply scoring gate to an intent (convenience function).

    If no gate provided, returns intent unchanged (passthrough).

    Args:
        bar: Current synthetic bar
        intent: Strategy's intended action
        state: Current simulation state
        gate: Optional scoring gate instance

    Returns:
        Filtered intent
    """
    if gate is None:
        return intent
    return gate.apply(bar, intent, state)
