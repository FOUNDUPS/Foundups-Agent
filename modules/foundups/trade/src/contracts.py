"""Trade FoundUp Contracts

Typed contracts for autonomous trading intelligence.
All contracts are market-adapter driven and chain-agnostic.

WSP References:
- WSP 97: Truth Boundaries (no false execution claims)
- WSP 103: FoundUp Federation Protocol
- WSP 104: FoundUp Route Namespace

Phase 0 Constraints:
- no_money_mode: True (always)
- dry_run_mode: True (always)
- real_execution_performed: False (always)
- No wallet signing
- No private keys
- No order placement
- No autonomous capital deployment
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional


# ---------------------------------------------------------------------------
# WSP 97 Truth Fields
# ---------------------------------------------------------------------------


@dataclass
class TruthFields:
    """WSP 97 truth boundary fields.

    Phase 0: All execution fields are False.
    These fields MUST NOT be set to True without actual execution.
    """

    dry_run_mode: bool = True
    no_money_mode: bool = True
    real_execution_performed: bool = False
    verification_complete: bool = False
    cabr_ready: bool = False
    payout_ready: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dry_run_mode": self.dry_run_mode,
            "no_money_mode": self.no_money_mode,
            "real_execution_performed": self.real_execution_performed,
            "verification_complete": self.verification_complete,
            "cabr_ready": self.cabr_ready,
            "payout_ready": self.payout_ready,
        }

    def assert_no_execution(self) -> None:
        """Verify no execution claims are made."""
        assert self.dry_run_mode is True, "dry_run_mode must be True in Phase 0"
        assert self.no_money_mode is True, "no_money_mode must be True in Phase 0"
        assert self.real_execution_performed is False, "real_execution_performed must be False"
        assert self.verification_complete is False, "verification_complete must be False"
        assert self.cabr_ready is False, "cabr_ready must be False"
        assert self.payout_ready is False, "payout_ready must be False"


# ---------------------------------------------------------------------------
# Adapter Specifications
# ---------------------------------------------------------------------------


class AdapterStatus(str, Enum):
    """Adapter implementation status."""

    PLANNED = "planned"
    INTERFACE_ONLY = "interface_only"
    SIMULATION = "simulation"
    PAPER_TRADING = "paper_trading"
    LIVE = "live"  # Not allowed in Phase 0


@dataclass
class MarketAdapterSpec:
    """Market adapter specification (chain/exchange abstraction).

    Market adapters abstract blockchain or exchange-specific details.
    Examples: solana, ethereum, base, bnb, tron, cardano, cex

    Phase 0: Interface specification only.
    """

    adapter_id: str
    chain_or_exchange: str
    display_name: str
    status: AdapterStatus = AdapterStatus.PLANNED

    # Capabilities (what this adapter can provide)
    supports_token_events: bool = False
    supports_wallet_events: bool = False
    supports_ohlcv: bool = False
    supports_order_book: bool = False
    supports_social_signals: bool = False

    # Truth boundary
    live_execution_enabled: bool = False  # MUST be False in Phase 0

    # Metadata
    documentation_url: Optional[str] = None
    data_sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "chain_or_exchange": self.chain_or_exchange,
            "display_name": self.display_name,
            "status": self.status.value,
            "supports_token_events": self.supports_token_events,
            "supports_wallet_events": self.supports_wallet_events,
            "supports_ohlcv": self.supports_ohlcv,
            "supports_order_book": self.supports_order_book,
            "supports_social_signals": self.supports_social_signals,
            "live_execution_enabled": self.live_execution_enabled,
            "documentation_url": self.documentation_url,
            "data_sources": self.data_sources,
        }


@dataclass
class LaunchpadAdapterSpec:
    """Launchpad adapter specification (token launch platform abstraction).

    Launchpad adapters abstract platform-specific launch mechanics.
    Examples: pumpfun, pumpswap, letsbonk, raydium_launchlab, sunpump, zora

    Phase 0: Interface specification only.
    """

    adapter_id: str
    platform_name: str
    chain: str
    display_name: str
    status: AdapterStatus = AdapterStatus.PLANNED

    # Capabilities
    supports_launch_detection: bool = False
    supports_bonding_curve: bool = False
    supports_migration_tracking: bool = False
    supports_top_traders: bool = False
    supports_holder_distribution: bool = False

    # Truth boundary
    live_execution_enabled: bool = False  # MUST be False in Phase 0

    # Metadata
    documentation_url: Optional[str] = None
    api_type: Optional[str] = None  # e.g., "bitquery", "direct_rpc", "websocket"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "platform_name": self.platform_name,
            "chain": self.chain,
            "display_name": self.display_name,
            "status": self.status.value,
            "supports_launch_detection": self.supports_launch_detection,
            "supports_bonding_curve": self.supports_bonding_curve,
            "supports_migration_tracking": self.supports_migration_tracking,
            "supports_top_traders": self.supports_top_traders,
            "supports_holder_distribution": self.supports_holder_distribution,
            "live_execution_enabled": self.live_execution_enabled,
            "documentation_url": self.documentation_url,
            "api_type": self.api_type,
        }


# ---------------------------------------------------------------------------
# Universal Event Schemas
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class MarketEvent:
    """Universal market event schema.

    Normalized market data event from any adapter.
    """

    event_id: str
    event_type: str  # e.g., "price_update", "volume_spike", "liquidity_change"
    adapter_id: str
    chain: str
    timestamp: datetime = field(default_factory=_utc_now)

    # Market data
    symbol: Optional[str] = None
    price_usd: Optional[float] = None
    volume_24h: Optional[float] = None
    market_cap: Optional[float] = None
    liquidity_usd: Optional[float] = None

    # Raw data passthrough
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "adapter_id": self.adapter_id,
            "chain": self.chain,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "price_usd": self.price_usd,
            "volume_24h": self.volume_24h,
            "market_cap": self.market_cap,
            "liquidity_usd": self.liquidity_usd,
            "raw_data": self.raw_data,
        }


@dataclass
class TokenEvent:
    """Token lifecycle event schema.

    Token creation, migration, or metadata change events.
    """

    event_id: str
    event_type: str  # e.g., "token_created", "migrated_to_dex", "metadata_update"
    adapter_id: str
    chain: str
    timestamp: datetime = field(default_factory=_utc_now)

    # Token identity
    token_address: Optional[str] = None
    token_symbol: Optional[str] = None
    token_name: Optional[str] = None

    # Launch metadata
    creator_address: Optional[str] = None
    launchpad: Optional[str] = None
    bonding_curve_progress: Optional[float] = None  # 0.0 - 1.0

    # Raw data
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "adapter_id": self.adapter_id,
            "chain": self.chain,
            "timestamp": self.timestamp.isoformat(),
            "token_address": self.token_address,
            "token_symbol": self.token_symbol,
            "token_name": self.token_name,
            "creator_address": self.creator_address,
            "launchpad": self.launchpad,
            "bonding_curve_progress": self.bonding_curve_progress,
            "raw_data": self.raw_data,
        }


@dataclass
class WalletEvent:
    """Wallet activity event schema.

    Wallet-level transaction and holding events.
    """

    event_id: str
    event_type: str  # e.g., "buy", "sell", "transfer", "holder_change"
    adapter_id: str
    chain: str
    timestamp: datetime = field(default_factory=_utc_now)

    # Wallet identity (hashed or clustered, not raw PII)
    wallet_cluster_id: Optional[str] = None
    is_known_entity: bool = False
    entity_label: Optional[str] = None  # e.g., "whale", "insider", "bot"

    # Transaction data
    token_address: Optional[str] = None
    action: Optional[str] = None
    amount_tokens: Optional[float] = None
    amount_usd: Optional[float] = None

    # Raw data
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "adapter_id": self.adapter_id,
            "chain": self.chain,
            "timestamp": self.timestamp.isoformat(),
            "wallet_cluster_id": self.wallet_cluster_id,
            "is_known_entity": self.is_known_entity,
            "entity_label": self.entity_label,
            "token_address": self.token_address,
            "action": self.action,
            "amount_tokens": self.amount_tokens,
            "amount_usd": self.amount_usd,
            "raw_data": self.raw_data,
        }


@dataclass
class SocialEvent:
    """Social signal event schema.

    Social media, sentiment, and community activity events.
    """

    event_id: str
    event_type: str  # e.g., "mention", "sentiment_shift", "influencer_post"
    source: str  # e.g., "twitter", "telegram", "discord"
    timestamp: datetime = field(default_factory=_utc_now)

    # Signal data
    token_address: Optional[str] = None
    token_symbol: Optional[str] = None
    sentiment_score: Optional[float] = None  # -1.0 to 1.0
    mention_count: Optional[int] = None
    engagement_score: Optional[float] = None

    # Manipulation indicators
    bot_activity_detected: bool = False
    coordinated_activity_detected: bool = False

    # Raw data
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "token_address": self.token_address,
            "token_symbol": self.token_symbol,
            "sentiment_score": self.sentiment_score,
            "mention_count": self.mention_count,
            "engagement_score": self.engagement_score,
            "bot_activity_detected": self.bot_activity_detected,
            "coordinated_activity_detected": self.coordinated_activity_detected,
            "raw_data": self.raw_data,
        }


@dataclass
class RiskEvent:
    """Risk assessment event schema.

    Risk engine output for a token or market condition.
    """

    event_id: str
    event_type: str  # e.g., "honeypot_detected", "rug_risk", "exit_blocked"
    timestamp: datetime = field(default_factory=_utc_now)

    # Target
    token_address: Optional[str] = None
    chain: Optional[str] = None

    # Risk scores (0.0 = safe, 1.0 = maximum risk)
    overall_risk_score: float = 0.0
    honeypot_score: float = 0.0
    rug_pull_score: float = 0.0
    no_exit_score: float = 0.0
    insider_concentration_score: float = 0.0

    # Flags
    is_honeypot: bool = False
    is_exit_blocked: bool = False
    has_suspicious_holders: bool = False

    # Reasoning
    risk_factors: List[str] = field(default_factory=list)
    confidence: float = 0.0  # 0.0 - 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "token_address": self.token_address,
            "chain": self.chain,
            "overall_risk_score": self.overall_risk_score,
            "honeypot_score": self.honeypot_score,
            "rug_pull_score": self.rug_pull_score,
            "no_exit_score": self.no_exit_score,
            "insider_concentration_score": self.insider_concentration_score,
            "is_honeypot": self.is_honeypot,
            "is_exit_blocked": self.is_exit_blocked,
            "has_suspicious_holders": self.has_suspicious_holders,
            "risk_factors": self.risk_factors,
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# Signal Schemas
# ---------------------------------------------------------------------------


@dataclass
class TradeSignal:
    """Trade signal schema.

    Entry signal from intelligence layer. Does NOT execute trades.
    """

    signal_id: str
    signal_type: Literal["entry", "scale_in", "hold"]
    timestamp: datetime = field(default_factory=_utc_now)

    # Target
    token_address: Optional[str] = None
    chain: Optional[str] = None

    # Signal strength
    confidence: float = 0.0  # 0.0 - 1.0
    expected_upside: Optional[float] = None  # Percentage
    expected_timeframe_seconds: Optional[int] = None

    # Risk-adjusted
    risk_score: float = 0.0
    risk_reward_ratio: Optional[float] = None

    # Reasoning
    signal_factors: List[str] = field(default_factory=list)
    model_id: Optional[str] = None

    # Truth boundary
    is_simulation: bool = True  # MUST be True in Phase 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "timestamp": self.timestamp.isoformat(),
            "token_address": self.token_address,
            "chain": self.chain,
            "confidence": self.confidence,
            "expected_upside": self.expected_upside,
            "expected_timeframe_seconds": self.expected_timeframe_seconds,
            "risk_score": self.risk_score,
            "risk_reward_ratio": self.risk_reward_ratio,
            "signal_factors": self.signal_factors,
            "model_id": self.model_id,
            "is_simulation": self.is_simulation,
        }


@dataclass
class ExitSignal:
    """Exit signal schema.

    Exit signal from intelligence layer. Does NOT execute trades.
    """

    signal_id: str
    signal_type: Literal["exit", "scale_out", "stop_loss", "take_profit"]
    timestamp: datetime = field(default_factory=_utc_now)

    # Target
    token_address: Optional[str] = None
    chain: Optional[str] = None

    # Signal data
    urgency: Literal["low", "medium", "high", "critical"] = "medium"
    confidence: float = 0.0

    # Exit reasoning
    exit_factors: List[str] = field(default_factory=list)

    # Performance context (if from simulation)
    simulated_pnl_percent: Optional[float] = None
    hold_duration_seconds: Optional[int] = None

    # Truth boundary
    is_simulation: bool = True  # MUST be True in Phase 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "timestamp": self.timestamp.isoformat(),
            "token_address": self.token_address,
            "chain": self.chain,
            "urgency": self.urgency,
            "confidence": self.confidence,
            "exit_factors": self.exit_factors,
            "simulated_pnl_percent": self.simulated_pnl_percent,
            "hold_duration_seconds": self.hold_duration_seconds,
            "is_simulation": self.is_simulation,
        }


# ---------------------------------------------------------------------------
# Proof and Simulation Schemas
# ---------------------------------------------------------------------------


@dataclass
class ProofMetric:
    """Proof metric for simulation performance tracking.

    Measures system performance without real capital.
    """

    metric_id: str
    metric_type: str
    timestamp: datetime = field(default_factory=_utc_now)

    # Metric value
    value: float = 0.0
    unit: str = ""

    # Context
    adapter_id: Optional[str] = None
    model_id: Optional[str] = None
    timeframe_seconds: Optional[int] = None
    sample_size: Optional[int] = None

    # Classification
    category: Literal[
        "latency", "accuracy", "performance", "reliability", "cost"
    ] = "performance"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "metric_type": self.metric_type,
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "unit": self.unit,
            "adapter_id": self.adapter_id,
            "model_id": self.model_id,
            "timeframe_seconds": self.timeframe_seconds,
            "sample_size": self.sample_size,
            "category": self.category,
        }


@dataclass
class SimulationResult:
    """Simulation/paper trading result.

    Tracks hypothetical performance without real capital.
    """

    simulation_id: str
    timestamp: datetime = field(default_factory=_utc_now)

    # Simulation period
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Performance
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    # Returns (simulated)
    simulated_pnl_percent: float = 0.0
    simulated_max_drawdown_percent: float = 0.0
    simulated_sharpe_ratio: Optional[float] = None

    # Risk metrics
    average_risk_score: float = 0.0
    honeypot_avoidance_rate: float = 0.0
    false_positive_rate: float = 0.0

    # Model performance
    model_id: Optional[str] = None
    model_latency_ms: Optional[float] = None
    valid_json_rate: float = 1.0

    # Truth boundary
    is_simulation: bool = True  # MUST be True
    real_capital_used: bool = False  # MUST be False in Phase 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "timestamp": self.timestamp.isoformat(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "simulated_pnl_percent": self.simulated_pnl_percent,
            "simulated_max_drawdown_percent": self.simulated_max_drawdown_percent,
            "simulated_sharpe_ratio": self.simulated_sharpe_ratio,
            "average_risk_score": self.average_risk_score,
            "honeypot_avoidance_rate": self.honeypot_avoidance_rate,
            "false_positive_rate": self.false_positive_rate,
            "model_id": self.model_id,
            "model_latency_ms": self.model_latency_ms,
            "valid_json_rate": self.valid_json_rate,
            "is_simulation": self.is_simulation,
            "real_capital_used": self.real_capital_used,
        }


# ---------------------------------------------------------------------------
# Execution Guard
# ---------------------------------------------------------------------------


class UnsupportedOperationError(Exception):
    """Raised when an unsupported operation is attempted."""
    pass


@dataclass
class ExecutionGuardPolicy:
    """Execution guard policy for Phase 0.

    Defines what operations are blocked in no-money mode.
    """

    policy_id: str = "phase0_no_money"

    # Global flags
    no_money_mode: bool = True  # MUST be True
    dry_run_mode: bool = True  # MUST be True

    # Blocked operations (all True = blocked)
    block_real_trades: bool = True
    block_wallet_signing: bool = True
    block_private_keys: bool = True
    block_order_placement: bool = True
    block_capital_deployment: bool = True
    block_wash_trading: bool = True
    block_market_manipulation: bool = True
    block_bot_concealment: bool = True
    block_fake_volume: bool = True

    def assert_operation_allowed(self, operation: str) -> None:
        """Raise UnsupportedOperationError if operation is blocked."""
        blocked_operations = {
            "real_trade": self.block_real_trades,
            "wallet_sign": self.block_wallet_signing,
            "private_key_access": self.block_private_keys,
            "order_place": self.block_order_placement,
            "capital_deploy": self.block_capital_deployment,
            "wash_trade": self.block_wash_trading,
            "market_manipulate": self.block_market_manipulation,
            "conceal_bot": self.block_bot_concealment,
            "fake_volume": self.block_fake_volume,
        }

        if operation in blocked_operations and blocked_operations[operation]:
            raise UnsupportedOperationError(
                f"Operation '{operation}' is blocked in {self.policy_id} mode. "
                "Trade FoundUp Phase 0 does not support execution operations."
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "no_money_mode": self.no_money_mode,
            "dry_run_mode": self.dry_run_mode,
            "block_real_trades": self.block_real_trades,
            "block_wallet_signing": self.block_wallet_signing,
            "block_private_keys": self.block_private_keys,
            "block_order_placement": self.block_order_placement,
            "block_capital_deployment": self.block_capital_deployment,
            "block_wash_trading": self.block_wash_trading,
            "block_market_manipulation": self.block_market_manipulation,
            "block_bot_concealment": self.block_bot_concealment,
            "block_fake_volume": self.block_fake_volume,
        }


# ---------------------------------------------------------------------------
# Default Instances
# ---------------------------------------------------------------------------

# Default execution guard for Phase 0
DEFAULT_EXECUTION_GUARD = ExecutionGuardPolicy()

# Default truth fields for Phase 0
DEFAULT_TRUTH_FIELDS = TruthFields()


# ---------------------------------------------------------------------------
# Due Diligence Schema (TRADE_DUE_DILIGENCE_SCHEMA_PHASE1)
#
# Spec: TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1 (PR #683)
#
# Pure data structures for pump.fun due-diligence scoring.
# No network calls, no wallet access, no order placement.
# ---------------------------------------------------------------------------


class DecisionBand(str, Enum):
    """Decision band from due-diligence scoring.

    No band authorizes real trading. All bands are simulation/observation only.

    Spec Section 8.3:
    - reject: Do not proceed (score < 30 or critical risk)
    - observe: Monitor only (score 30-50 or low evidence)
    - simulate_only: Paper trade simulation (score 50-70)
    - candidate_for_future_review: Flag for advanced analysis (score > 70)
    """

    REJECT = "reject"
    OBSERVE = "observe"
    SIMULATE_ONLY = "simulate_only"
    CANDIDATE_FOR_FUTURE_REVIEW = "candidate_for_future_review"


class RiskClassification(str, Enum):
    """Entity risk classification."""

    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    FLAGGED = "flagged"
    BLACKLISTED = "blacklisted"


class EntityType(str, Enum):
    """Entity type for history tracking."""

    ISSUER = "issuer"
    INFLUENCER = "influencer"
    WHALE = "whale"
    BOT = "bot"
    RETAIL = "retail"


class WalletClassification(str, Enum):
    """Wallet entity classification."""

    RETAIL = "retail"
    WHALE = "whale"
    INSIDER = "insider"
    BOT = "bot"
    SCAMMER = "scammer"
    UNKNOWN = "unknown"


@dataclass
class EntityHistoryReport:
    """Issuer/influencer history report.

    Spec Section 5.5: EntityHistoryReport schema.
    Tracks prior token launches, rug pulls, and risk signals.
    """

    entity_id: str  # Hashed wallet or social handle (privacy-preserving)
    entity_type: EntityType
    timestamp: datetime = field(default_factory=_utc_now)

    # Prior activity
    prior_token_launches: int = 0
    prior_rug_pulls: int = 0
    prior_successful_launches: int = 0
    average_token_lifespan_hours: float = 0.0
    average_holder_loss_percent: float = 0.0

    # Associations
    known_associations: List[str] = field(default_factory=list)  # Other flagged entities
    first_seen_timestamp: Optional[datetime] = None

    # Classification
    risk_classification: RiskClassification = RiskClassification.CLEAN
    confidence: float = 0.0  # 0.0 - 1.0

    def __post_init__(self):
        """Validate fields."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")
        if self.prior_rug_pulls < 0:
            raise ValueError(f"prior_rug_pulls cannot be negative: {self.prior_rug_pulls}")
        if self.prior_token_launches < 0:
            raise ValueError(f"prior_token_launches cannot be negative: {self.prior_token_launches}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "timestamp": self.timestamp.isoformat(),
            "prior_token_launches": self.prior_token_launches,
            "prior_rug_pulls": self.prior_rug_pulls,
            "prior_successful_launches": self.prior_successful_launches,
            "average_token_lifespan_hours": self.average_token_lifespan_hours,
            "average_holder_loss_percent": self.average_holder_loss_percent,
            "known_associations": self.known_associations,
            "first_seen_timestamp": self.first_seen_timestamp.isoformat() if self.first_seen_timestamp else None,
            "risk_classification": self.risk_classification.value,
            "confidence": self.confidence,
        }


@dataclass
class WalletAuditReport:
    """Wallet audit report for holder analysis.

    Spec Section 6.4: WalletAuditReport schema.
    Privacy-preserving wallet analysis for holder distribution and risk.
    """

    wallet_hash: str  # Privacy-preserving hash, not raw address
    token_address: str
    timestamp: datetime = field(default_factory=_utc_now)

    # Holding data
    holding_percent: float = 0.0  # 0.0 - 100.0
    acquisition_timestamp: Optional[datetime] = None
    acquisition_price_usd: float = 0.0
    current_value_usd: float = 0.0
    unrealized_pnl_percent: float = 0.0

    # Historical behavior
    prior_tokens_held: int = 0
    prior_rugs_held: int = 0
    prior_dumps_executed: int = 0

    # Classification
    entity_classification: WalletClassification = WalletClassification.UNKNOWN
    risk_contribution: float = 0.0  # 0.0 - 1.0, contribution to token risk

    def __post_init__(self):
        """Validate fields."""
        if not 0.0 <= self.holding_percent <= 100.0:
            raise ValueError(f"holding_percent must be 0.0-100.0, got {self.holding_percent}")
        if not 0.0 <= self.risk_contribution <= 1.0:
            raise ValueError(f"risk_contribution must be 0.0-1.0, got {self.risk_contribution}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wallet_hash": self.wallet_hash,
            "token_address": self.token_address,
            "timestamp": self.timestamp.isoformat(),
            "holding_percent": self.holding_percent,
            "acquisition_timestamp": self.acquisition_timestamp.isoformat() if self.acquisition_timestamp else None,
            "acquisition_price_usd": self.acquisition_price_usd,
            "current_value_usd": self.current_value_usd,
            "unrealized_pnl_percent": self.unrealized_pnl_percent,
            "prior_tokens_held": self.prior_tokens_held,
            "prior_rugs_held": self.prior_rugs_held,
            "prior_dumps_executed": self.prior_dumps_executed,
            "entity_classification": self.entity_classification.value,
            "risk_contribution": self.risk_contribution,
        }


@dataclass
class SocialPresenceReport:
    """Social presence analysis report.

    Spec Section 5.2/5.3: X and Telegram analysis.
    Tracks social authenticity signals without storing PII.
    """

    token_address: str
    timestamp: datetime = field(default_factory=_utc_now)

    # X (Twitter) signals
    x_account_exists: bool = False
    x_account_age_days: int = 0
    x_follower_count: int = 0
    x_follower_bot_percent: float = 0.0  # 0.0 - 100.0
    x_engagement_authenticity: float = 0.0  # 0.0 - 1.0
    x_prior_token_mentions: int = 0

    # Telegram signals
    telegram_exists: bool = False
    telegram_member_count: int = 0
    telegram_bot_percent: float = 0.0  # 0.0 - 100.0
    telegram_admin_active: bool = False
    telegram_spam_ratio: float = 0.0  # 0.0 - 1.0

    # Aggregate scores
    social_authenticity_score: float = 0.0  # 0.0 - 100.0
    evidence_completeness: float = 0.0  # 0.0 - 1.0

    def __post_init__(self):
        """Validate fields."""
        if not 0.0 <= self.social_authenticity_score <= 100.0:
            raise ValueError(f"social_authenticity_score must be 0.0-100.0, got {self.social_authenticity_score}")
        if not 0.0 <= self.evidence_completeness <= 1.0:
            raise ValueError(f"evidence_completeness must be 0.0-1.0, got {self.evidence_completeness}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_address": self.token_address,
            "timestamp": self.timestamp.isoformat(),
            "x_account_exists": self.x_account_exists,
            "x_account_age_days": self.x_account_age_days,
            "x_follower_count": self.x_follower_count,
            "x_follower_bot_percent": self.x_follower_bot_percent,
            "x_engagement_authenticity": self.x_engagement_authenticity,
            "x_prior_token_mentions": self.x_prior_token_mentions,
            "telegram_exists": self.telegram_exists,
            "telegram_member_count": self.telegram_member_count,
            "telegram_bot_percent": self.telegram_bot_percent,
            "telegram_admin_active": self.telegram_admin_active,
            "telegram_spam_ratio": self.telegram_spam_ratio,
            "social_authenticity_score": self.social_authenticity_score,
            "evidence_completeness": self.evidence_completeness,
        }


@dataclass
class InfluencerRiskReport:
    """Influencer/KOL risk analysis report.

    Spec Section 5.4: Influencer/KOL detection.
    Tracks pump coordination and prior rug associations.
    """

    token_address: str
    timestamp: datetime = field(default_factory=_utc_now)

    # Detection signals
    known_pumper_wallets_detected: int = 0
    coordinated_buy_timing_detected: bool = False
    influencer_mentions_count: int = 0
    multiple_influencers_same_token: bool = False

    # Historical risk
    influencers_with_prior_rugs: int = 0
    total_influencers_detected: int = 0

    # Risk scores
    influencer_risk_score: float = 0.0  # 0.0 - 100.0, higher = more risk
    coordination_risk_score: float = 0.0  # 0.0 - 100.0
    evidence_completeness: float = 0.0  # 0.0 - 1.0

    def __post_init__(self):
        """Validate fields."""
        if not 0.0 <= self.influencer_risk_score <= 100.0:
            raise ValueError(f"influencer_risk_score must be 0.0-100.0, got {self.influencer_risk_score}")
        if not 0.0 <= self.coordination_risk_score <= 100.0:
            raise ValueError(f"coordination_risk_score must be 0.0-100.0, got {self.coordination_risk_score}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_address": self.token_address,
            "timestamp": self.timestamp.isoformat(),
            "known_pumper_wallets_detected": self.known_pumper_wallets_detected,
            "coordinated_buy_timing_detected": self.coordinated_buy_timing_detected,
            "influencer_mentions_count": self.influencer_mentions_count,
            "multiple_influencers_same_token": self.multiple_influencers_same_token,
            "influencers_with_prior_rugs": self.influencers_with_prior_rugs,
            "total_influencers_detected": self.total_influencers_detected,
            "influencer_risk_score": self.influencer_risk_score,
            "coordination_risk_score": self.coordination_risk_score,
            "evidence_completeness": self.evidence_completeness,
        }


@dataclass
class LaunchpadTokenCandidate:
    """Launchpad token candidate for due diligence.

    Spec Section 4.3: LaunchDiscoveryEvent equivalent.
    Represents a token discovered from a launchpad feed.
    """

    token_address: str
    token_symbol: str
    token_name: str
    chain: str = "solana"
    launchpad: str = "pumpfun"
    timestamp: datetime = field(default_factory=_utc_now)

    # Creator
    creator_address: str = ""

    # Launch metrics
    bonding_curve_progress: float = 0.0  # 0.0 - 1.0
    initial_market_cap_usd: float = 0.0
    transaction_count: int = 0

    # Filter status
    passed_initial_filter: bool = False
    filter_rejection_reasons: List[str] = field(default_factory=list)

    # Discovery source
    discovery_source: str = "simulation"  # "bitquery", "rpc", "websocket", "simulation"

    def __post_init__(self):
        """Validate fields."""
        if not 0.0 <= self.bonding_curve_progress <= 1.0:
            raise ValueError(f"bonding_curve_progress must be 0.0-1.0, got {self.bonding_curve_progress}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_address": self.token_address,
            "token_symbol": self.token_symbol,
            "token_name": self.token_name,
            "chain": self.chain,
            "launchpad": self.launchpad,
            "timestamp": self.timestamp.isoformat(),
            "creator_address": self.creator_address,
            "bonding_curve_progress": self.bonding_curve_progress,
            "initial_market_cap_usd": self.initial_market_cap_usd,
            "transaction_count": self.transaction_count,
            "passed_initial_filter": self.passed_initial_filter,
            "filter_rejection_reasons": self.filter_rejection_reasons,
            "discovery_source": self.discovery_source,
        }


@dataclass
class TradeDueDiligenceScore:
    """Trade due-diligence score with 10 components.

    Spec Section 8.1/8.2: TradeDueDiligenceScore schema.
    WSP_15-style scoring for pump.fun tokens.

    Component scores: 0-100 (higher = better/safer)
    No decision band authorizes real trading.
    """

    token_address: str
    timestamp: datetime = field(default_factory=_utc_now)

    # 10 component scores (0-100, higher = better)
    launch_timing: float = 0.0  # Fresh launch advantage
    issuer_history: float = 0.0  # Clean issuer history
    social_authenticity: float = 0.0  # Real community signals
    telegram_quality: float = 0.0  # Active, non-bot TG
    influencer_risk: float = 0.0  # Low pump-and-dump risk (inverted)
    holder_distribution: float = 0.0  # Distributed holdings
    whale_risk: float = 0.0  # Low whale manipulation (inverted)
    prior_token_history: float = 0.0  # Issuer track record
    bonding_curve: float = 0.0  # Healthy curve progression
    rug_honeypot: float = 0.0  # Low exit risk (inverted)

    # Aggregates
    total_score: float = 0.0  # Weighted sum (0-100)
    risk_score: float = 0.0  # Inverted (0-100, higher = more risk)
    evidence_confidence: float = 0.0  # Data completeness (0.0-1.0)

    # Decision
    decision_band: DecisionBand = DecisionBand.REJECT
    band_rationale: str = ""

    # Component weights (spec Section 8.1)
    _WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
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
    }, repr=False)

    def __post_init__(self):
        """Validate all component scores are 0-100."""
        components = [
            ("launch_timing", self.launch_timing),
            ("issuer_history", self.issuer_history),
            ("social_authenticity", self.social_authenticity),
            ("telegram_quality", self.telegram_quality),
            ("influencer_risk", self.influencer_risk),
            ("holder_distribution", self.holder_distribution),
            ("whale_risk", self.whale_risk),
            ("prior_token_history", self.prior_token_history),
            ("bonding_curve", self.bonding_curve),
            ("rug_honeypot", self.rug_honeypot),
            ("total_score", self.total_score),
            ("risk_score", self.risk_score),
        ]
        for name, value in components:
            if not 0.0 <= value <= 100.0:
                raise ValueError(f"{name} must be 0.0-100.0, got {value}")

        if not 0.0 <= self.evidence_confidence <= 1.0:
            raise ValueError(f"evidence_confidence must be 0.0-1.0, got {self.evidence_confidence}")

    def calculate_total_score(self) -> float:
        """Calculate weighted total score from components."""
        return (
            self.launch_timing * self._WEIGHTS["launch_timing"] +
            self.issuer_history * self._WEIGHTS["issuer_history"] +
            self.social_authenticity * self._WEIGHTS["social_authenticity"] +
            self.telegram_quality * self._WEIGHTS["telegram_quality"] +
            self.influencer_risk * self._WEIGHTS["influencer_risk"] +
            self.holder_distribution * self._WEIGHTS["holder_distribution"] +
            self.whale_risk * self._WEIGHTS["whale_risk"] +
            self.prior_token_history * self._WEIGHTS["prior_token_history"] +
            self.bonding_curve * self._WEIGHTS["bonding_curve"] +
            self.rug_honeypot * self._WEIGHTS["rug_honeypot"]
        )

    def determine_decision_band(self) -> DecisionBand:
        """Determine decision band from score and risk flags.

        Spec Section 8.4: Decision rules.
        No band authorizes real trading.

        Soft disqualifiers (PR #696 TRADE_DUE_DILIGENCE_SOFT_DISQUALIFIER_PHASE1):
        - whale_risk < 20: cap at SIMULATE_ONLY (R5 whale accumulation risk)
        - influencer_risk < 20: cap at SIMULATE_ONLY (R2 pump coordination risk)
        - social_authenticity < 40 AND telegram_quality < 50: cap at SIMULATE_ONLY
          (R6 low-authenticity social signals)
        """
        # Hard disqualifiers (unchanged)
        if self.rug_honeypot < 20:
            return DecisionBand.REJECT
        if self.issuer_history < 20:
            return DecisionBand.REJECT
        if self.evidence_confidence < 0.5:
            return DecisionBand.OBSERVE

        # Band determination by total score
        if self.total_score < 30:
            return DecisionBand.REJECT
        elif self.total_score < 50:
            return DecisionBand.OBSERVE
        elif self.total_score < 70:
            return DecisionBand.SIMULATE_ONLY
        else:
            # Soft disqualifiers: cap CANDIDATE_FOR_FUTURE_REVIEW at SIMULATE_ONLY
            # when certain risk signals are present (PR #696 soft-disqualifier tuning)

            # R5: whale_risk < 20 indicates whale accumulation with dump risk
            if self.whale_risk < 20:
                return DecisionBand.SIMULATE_ONLY

            # R2: influencer_risk < 20 indicates coordinated pump risk
            if self.influencer_risk < 20:
                return DecisionBand.SIMULATE_ONLY

            # R6: low social authenticity combined with low telegram quality
            if self.social_authenticity < 40 and self.telegram_quality < 50:
                return DecisionBand.SIMULATE_ONLY

            return DecisionBand.CANDIDATE_FOR_FUTURE_REVIEW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_address": self.token_address,
            "timestamp": self.timestamp.isoformat(),
            "launch_timing": self.launch_timing,
            "issuer_history": self.issuer_history,
            "social_authenticity": self.social_authenticity,
            "telegram_quality": self.telegram_quality,
            "influencer_risk": self.influencer_risk,
            "holder_distribution": self.holder_distribution,
            "whale_risk": self.whale_risk,
            "prior_token_history": self.prior_token_history,
            "bonding_curve": self.bonding_curve,
            "rug_honeypot": self.rug_honeypot,
            "total_score": self.total_score,
            "risk_score": self.risk_score,
            "evidence_confidence": self.evidence_confidence,
            "decision_band": self.decision_band.value,
            "band_rationale": self.band_rationale,
        }


def assert_no_real_trading_authorized(band: DecisionBand) -> None:
    """Assert that no decision band authorizes real trading.

    This is a runtime check to enforce the spec requirement:
    'No band authorizes real trading.'
    """
    # All bands are simulation/observation only
    authorized_for_real_trading = False
    assert not authorized_for_real_trading, (
        f"Decision band '{band.value}' does not authorize real trading. "
        "Trade FoundUp Phase 0 is simulation-only."
    )
