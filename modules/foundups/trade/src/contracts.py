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
