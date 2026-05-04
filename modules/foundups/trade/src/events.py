"""Trade FoundUp - Event Normalization Layer

Helper constructors and validators for universal event schemas.
All events are normalized to chain-agnostic format.

WSP References:
- WSP 97: Truth Boundaries (events are observation, not execution)
- WSP 11: Interface Protocol (event contracts)
- WSP 104: FoundUp Route Namespace

Phase 0 Constraints:
- All events represent observed data, not executed actions
- No wallet signing or execution events
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from .contracts import (
        MarketEvent,
        TokenEvent,
        WalletEvent,
        SocialEvent,
        RiskEvent,
    )
except ImportError:
    from contracts import (
        MarketEvent,
        TokenEvent,
        WalletEvent,
        SocialEvent,
        RiskEvent,
    )


# ---------------------------------------------------------------------------
# Event ID Generation
# ---------------------------------------------------------------------------


def generate_event_id(prefix: str = "evt") -> str:
    """Generate a unique event ID.

    Format: {prefix}_{uuid4_short}
    Example: evt_a1b2c3d4
    """
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def generate_deterministic_event_id(
    event_type: str,
    adapter_id: str,
    payload_hash: str,
    timestamp: Optional[datetime] = None,
) -> str:
    """Generate a deterministic event ID for deduplication.

    Format: {event_type}_{sha256_short}
    Uses: sha256(event_type:adapter_id:payload_hash:timestamp)[:16]
    """
    ts = timestamp or datetime.now(timezone.utc)
    ts_str = ts.strftime("%Y%m%d%H%M%S")
    data = f"{event_type}:{adapter_id}:{payload_hash}:{ts_str}"
    hash_hex = hashlib.sha256(data.encode()).hexdigest()[:16]
    return f"{event_type[:3]}_{hash_hex}"


# ---------------------------------------------------------------------------
# Market Event Helpers
# ---------------------------------------------------------------------------


def create_market_event(
    event_type: str,
    adapter_id: str,
    chain: str,
    *,
    event_id: Optional[str] = None,
    symbol: Optional[str] = None,
    price_usd: Optional[float] = None,
    volume_24h: Optional[float] = None,
    market_cap: Optional[float] = None,
    liquidity_usd: Optional[float] = None,
    raw_data: Optional[Dict[str, Any]] = None,
) -> MarketEvent:
    """Create a normalized market event.

    Args:
        event_type: Type of event (price_update, volume_spike, liquidity_change)
        adapter_id: Source adapter ID
        chain: Blockchain or exchange
        event_id: Optional custom event ID (auto-generated if not provided)
        symbol: Trading symbol
        price_usd: Price in USD
        volume_24h: 24-hour volume
        market_cap: Market capitalization
        liquidity_usd: Liquidity in USD
        raw_data: Raw adapter response data

    Returns:
        Normalized MarketEvent
    """
    return MarketEvent(
        event_id=event_id or generate_event_id("mkt"),
        event_type=event_type,
        adapter_id=adapter_id,
        chain=chain,
        symbol=symbol,
        price_usd=price_usd,
        volume_24h=volume_24h,
        market_cap=market_cap,
        liquidity_usd=liquidity_usd,
        raw_data=raw_data or {},
    )


def create_price_update_event(
    adapter_id: str,
    chain: str,
    symbol: str,
    price_usd: float,
    **kwargs: Any,
) -> MarketEvent:
    """Create a price update event."""
    return create_market_event(
        event_type="price_update",
        adapter_id=adapter_id,
        chain=chain,
        symbol=symbol,
        price_usd=price_usd,
        **kwargs,
    )


def create_volume_spike_event(
    adapter_id: str,
    chain: str,
    symbol: str,
    volume_24h: float,
    **kwargs: Any,
) -> MarketEvent:
    """Create a volume spike event."""
    return create_market_event(
        event_type="volume_spike",
        adapter_id=adapter_id,
        chain=chain,
        symbol=symbol,
        volume_24h=volume_24h,
        **kwargs,
    )


def create_liquidity_change_event(
    adapter_id: str,
    chain: str,
    symbol: str,
    liquidity_usd: float,
    **kwargs: Any,
) -> MarketEvent:
    """Create a liquidity change event."""
    return create_market_event(
        event_type="liquidity_change",
        adapter_id=adapter_id,
        chain=chain,
        symbol=symbol,
        liquidity_usd=liquidity_usd,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Token Event Helpers
# ---------------------------------------------------------------------------


def create_token_event(
    event_type: str,
    adapter_id: str,
    chain: str,
    *,
    event_id: Optional[str] = None,
    token_address: Optional[str] = None,
    token_symbol: Optional[str] = None,
    token_name: Optional[str] = None,
    creator_address: Optional[str] = None,
    launchpad: Optional[str] = None,
    bonding_curve_progress: Optional[float] = None,
    raw_data: Optional[Dict[str, Any]] = None,
) -> TokenEvent:
    """Create a normalized token event.

    Args:
        event_type: Type of event (token_created, migrated_to_dex, metadata_update)
        adapter_id: Source adapter ID
        chain: Blockchain
        event_id: Optional custom event ID
        token_address: Token contract address
        token_symbol: Token symbol
        token_name: Token name
        creator_address: Creator wallet address
        launchpad: Launchpad platform (e.g., pumpfun, sunpump)
        bonding_curve_progress: Progress through bonding curve (0.0 - 1.0)
        raw_data: Raw adapter response data

    Returns:
        Normalized TokenEvent
    """
    return TokenEvent(
        event_id=event_id or generate_event_id("tok"),
        event_type=event_type,
        adapter_id=adapter_id,
        chain=chain,
        token_address=token_address,
        token_symbol=token_symbol,
        token_name=token_name,
        creator_address=creator_address,
        launchpad=launchpad,
        bonding_curve_progress=bonding_curve_progress,
        raw_data=raw_data or {},
    )


def create_token_created_event(
    adapter_id: str,
    chain: str,
    token_address: str,
    token_symbol: str,
    token_name: str,
    *,
    launchpad: Optional[str] = None,
    creator_address: Optional[str] = None,
    **kwargs: Any,
) -> TokenEvent:
    """Create a token creation event."""
    return create_token_event(
        event_type="token_created",
        adapter_id=adapter_id,
        chain=chain,
        token_address=token_address,
        token_symbol=token_symbol,
        token_name=token_name,
        launchpad=launchpad,
        creator_address=creator_address,
        **kwargs,
    )


def create_migration_event(
    adapter_id: str,
    chain: str,
    token_address: str,
    token_symbol: str,
    *,
    launchpad: Optional[str] = None,
    bonding_curve_progress: float = 1.0,
    **kwargs: Any,
) -> TokenEvent:
    """Create a token migration event (graduated from bonding curve)."""
    return create_token_event(
        event_type="migrated_to_dex",
        adapter_id=adapter_id,
        chain=chain,
        token_address=token_address,
        token_symbol=token_symbol,
        launchpad=launchpad,
        bonding_curve_progress=bonding_curve_progress,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Wallet Event Helpers
# ---------------------------------------------------------------------------


def create_wallet_event(
    event_type: str,
    adapter_id: str,
    chain: str,
    *,
    event_id: Optional[str] = None,
    wallet_cluster_id: Optional[str] = None,
    is_known_entity: bool = False,
    entity_label: Optional[str] = None,
    token_address: Optional[str] = None,
    action: Optional[str] = None,
    amount_tokens: Optional[float] = None,
    amount_usd: Optional[float] = None,
    raw_data: Optional[Dict[str, Any]] = None,
) -> WalletEvent:
    """Create a normalized wallet event.

    Args:
        event_type: Type of event (buy, sell, transfer, holder_change)
        adapter_id: Source adapter ID
        chain: Blockchain
        event_id: Optional custom event ID
        wallet_cluster_id: Hashed wallet cluster identifier (not raw address)
        is_known_entity: Whether wallet is a known entity (whale, insider, etc.)
        entity_label: Entity classification label
        token_address: Token being transacted
        action: Transaction action
        amount_tokens: Token amount
        amount_usd: USD value
        raw_data: Raw adapter response data

    Returns:
        Normalized WalletEvent
    """
    return WalletEvent(
        event_id=event_id or generate_event_id("wal"),
        event_type=event_type,
        adapter_id=adapter_id,
        chain=chain,
        wallet_cluster_id=wallet_cluster_id,
        is_known_entity=is_known_entity,
        entity_label=entity_label,
        token_address=token_address,
        action=action,
        amount_tokens=amount_tokens,
        amount_usd=amount_usd,
        raw_data=raw_data or {},
    )


def create_buy_event(
    adapter_id: str,
    chain: str,
    wallet_cluster_id: str,
    token_address: str,
    amount_tokens: float,
    *,
    amount_usd: Optional[float] = None,
    entity_label: Optional[str] = None,
    **kwargs: Any,
) -> WalletEvent:
    """Create a token buy event."""
    return create_wallet_event(
        event_type="buy",
        adapter_id=adapter_id,
        chain=chain,
        wallet_cluster_id=wallet_cluster_id,
        token_address=token_address,
        action="buy",
        amount_tokens=amount_tokens,
        amount_usd=amount_usd,
        is_known_entity=entity_label is not None,
        entity_label=entity_label,
        **kwargs,
    )


def create_sell_event(
    adapter_id: str,
    chain: str,
    wallet_cluster_id: str,
    token_address: str,
    amount_tokens: float,
    *,
    amount_usd: Optional[float] = None,
    entity_label: Optional[str] = None,
    **kwargs: Any,
) -> WalletEvent:
    """Create a token sell event."""
    return create_wallet_event(
        event_type="sell",
        adapter_id=adapter_id,
        chain=chain,
        wallet_cluster_id=wallet_cluster_id,
        token_address=token_address,
        action="sell",
        amount_tokens=amount_tokens,
        amount_usd=amount_usd,
        is_known_entity=entity_label is not None,
        entity_label=entity_label,
        **kwargs,
    )


def hash_wallet_address(
    address: str,
    salt: str = "trade_foundup_v1",
) -> str:
    """Hash a wallet address for privacy-preserving storage.

    Returns a cluster ID, not the raw address.
    """
    data = f"{salt}:{address.lower()}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Social Event Helpers
# ---------------------------------------------------------------------------


def create_social_event(
    event_type: str,
    source: str,
    *,
    event_id: Optional[str] = None,
    token_address: Optional[str] = None,
    token_symbol: Optional[str] = None,
    sentiment_score: Optional[float] = None,
    mention_count: Optional[int] = None,
    engagement_score: Optional[float] = None,
    bot_activity_detected: bool = False,
    coordinated_activity_detected: bool = False,
    raw_data: Optional[Dict[str, Any]] = None,
) -> SocialEvent:
    """Create a normalized social event.

    Args:
        event_type: Type of event (mention, sentiment_shift, influencer_post)
        source: Social platform (twitter, telegram, discord)
        event_id: Optional custom event ID
        token_address: Token being discussed
        token_symbol: Token symbol
        sentiment_score: Sentiment score (-1.0 to 1.0)
        mention_count: Number of mentions
        engagement_score: Engagement score
        bot_activity_detected: Whether bot activity was detected
        coordinated_activity_detected: Whether coordinated activity was detected
        raw_data: Raw data

    Returns:
        Normalized SocialEvent
    """
    return SocialEvent(
        event_id=event_id or generate_event_id("soc"),
        event_type=event_type,
        source=source,
        token_address=token_address,
        token_symbol=token_symbol,
        sentiment_score=sentiment_score,
        mention_count=mention_count,
        engagement_score=engagement_score,
        bot_activity_detected=bot_activity_detected,
        coordinated_activity_detected=coordinated_activity_detected,
        raw_data=raw_data or {},
    )


def create_mention_event(
    source: str,
    token_symbol: str,
    mention_count: int,
    *,
    sentiment_score: Optional[float] = None,
    **kwargs: Any,
) -> SocialEvent:
    """Create a token mention event."""
    return create_social_event(
        event_type="mention",
        source=source,
        token_symbol=token_symbol,
        mention_count=mention_count,
        sentiment_score=sentiment_score,
        **kwargs,
    )


def create_sentiment_shift_event(
    source: str,
    token_symbol: str,
    sentiment_score: float,
    **kwargs: Any,
) -> SocialEvent:
    """Create a sentiment shift event."""
    return create_social_event(
        event_type="sentiment_shift",
        source=source,
        token_symbol=token_symbol,
        sentiment_score=sentiment_score,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Risk Event Helpers
# ---------------------------------------------------------------------------


def create_risk_event(
    event_type: str,
    *,
    event_id: Optional[str] = None,
    token_address: Optional[str] = None,
    chain: Optional[str] = None,
    overall_risk_score: float = 0.0,
    honeypot_score: float = 0.0,
    rug_pull_score: float = 0.0,
    no_exit_score: float = 0.0,
    insider_concentration_score: float = 0.0,
    is_honeypot: bool = False,
    is_exit_blocked: bool = False,
    has_suspicious_holders: bool = False,
    risk_factors: Optional[List[str]] = None,
    confidence: float = 0.0,
) -> RiskEvent:
    """Create a normalized risk event.

    Args:
        event_type: Type of event (honeypot_detected, rug_risk, exit_blocked)
        event_id: Optional custom event ID
        token_address: Token being analyzed
        chain: Blockchain
        overall_risk_score: Overall risk score (0.0 = safe, 1.0 = max risk)
        honeypot_score: Honeypot risk score
        rug_pull_score: Rug pull risk score
        no_exit_score: No-exit risk score
        insider_concentration_score: Insider concentration score
        is_honeypot: Whether token is a honeypot
        is_exit_blocked: Whether exit is blocked
        has_suspicious_holders: Whether suspicious holder patterns detected
        risk_factors: List of identified risk factors
        confidence: Confidence in assessment (0.0 - 1.0)

    Returns:
        Normalized RiskEvent
    """
    return RiskEvent(
        event_id=event_id or generate_event_id("rsk"),
        event_type=event_type,
        token_address=token_address,
        chain=chain,
        overall_risk_score=overall_risk_score,
        honeypot_score=honeypot_score,
        rug_pull_score=rug_pull_score,
        no_exit_score=no_exit_score,
        insider_concentration_score=insider_concentration_score,
        is_honeypot=is_honeypot,
        is_exit_blocked=is_exit_blocked,
        has_suspicious_holders=has_suspicious_holders,
        risk_factors=risk_factors or [],
        confidence=confidence,
    )


def create_honeypot_detection_event(
    token_address: str,
    chain: str,
    honeypot_score: float,
    *,
    confidence: float = 0.0,
    risk_factors: Optional[List[str]] = None,
    **kwargs: Any,
) -> RiskEvent:
    """Create a honeypot detection event."""
    is_honeypot = honeypot_score >= 0.8
    return create_risk_event(
        event_type="honeypot_detected",
        token_address=token_address,
        chain=chain,
        honeypot_score=honeypot_score,
        overall_risk_score=honeypot_score,
        is_honeypot=is_honeypot,
        confidence=confidence,
        risk_factors=risk_factors or (["honeypot_detected"] if is_honeypot else []),
        **kwargs,
    )


def create_rug_risk_event(
    token_address: str,
    chain: str,
    rug_pull_score: float,
    *,
    insider_concentration_score: float = 0.0,
    confidence: float = 0.0,
    risk_factors: Optional[List[str]] = None,
    **kwargs: Any,
) -> RiskEvent:
    """Create a rug pull risk event."""
    overall_score = max(rug_pull_score, insider_concentration_score)
    factors = risk_factors or []
    if rug_pull_score >= 0.7:
        factors.append("high_rug_risk")
    if insider_concentration_score >= 0.7:
        factors.append("insider_concentration")

    return create_risk_event(
        event_type="rug_risk",
        token_address=token_address,
        chain=chain,
        rug_pull_score=rug_pull_score,
        insider_concentration_score=insider_concentration_score,
        overall_risk_score=overall_score,
        has_suspicious_holders=insider_concentration_score >= 0.5,
        confidence=confidence,
        risk_factors=factors,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Event Validation
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Result of event validation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_market_event(event: MarketEvent) -> ValidationResult:
    """Validate a market event."""
    errors = []
    warnings = []

    # Required fields
    if not event.event_id:
        errors.append("event_id is required")
    if not event.event_type:
        errors.append("event_type is required")
    if not event.adapter_id:
        errors.append("adapter_id is required")
    if not event.chain:
        errors.append("chain is required")

    # Value validation
    if event.price_usd is not None and event.price_usd < 0:
        errors.append("price_usd cannot be negative")
    if event.volume_24h is not None and event.volume_24h < 0:
        errors.append("volume_24h cannot be negative")
    if event.market_cap is not None and event.market_cap < 0:
        errors.append("market_cap cannot be negative")
    if event.liquidity_usd is not None and event.liquidity_usd < 0:
        errors.append("liquidity_usd cannot be negative")

    # Warnings for missing optional fields
    if event.symbol is None:
        warnings.append("symbol not provided")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_token_event(event: TokenEvent) -> ValidationResult:
    """Validate a token event."""
    errors = []
    warnings = []

    # Required fields
    if not event.event_id:
        errors.append("event_id is required")
    if not event.event_type:
        errors.append("event_type is required")
    if not event.adapter_id:
        errors.append("adapter_id is required")
    if not event.chain:
        errors.append("chain is required")

    # Value validation
    if event.bonding_curve_progress is not None:
        if event.bonding_curve_progress < 0 or event.bonding_curve_progress > 1:
            errors.append("bonding_curve_progress must be between 0.0 and 1.0")

    # Warnings for missing optional fields
    if event.token_address is None:
        warnings.append("token_address not provided")
    if event.token_symbol is None:
        warnings.append("token_symbol not provided")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_wallet_event(event: WalletEvent) -> ValidationResult:
    """Validate a wallet event."""
    errors = []
    warnings = []

    # Required fields
    if not event.event_id:
        errors.append("event_id is required")
    if not event.event_type:
        errors.append("event_type is required")
    if not event.adapter_id:
        errors.append("adapter_id is required")
    if not event.chain:
        errors.append("chain is required")

    # Value validation
    if event.amount_tokens is not None and event.amount_tokens < 0:
        errors.append("amount_tokens cannot be negative")
    if event.amount_usd is not None and event.amount_usd < 0:
        errors.append("amount_usd cannot be negative")

    # Privacy check - wallet_cluster_id should be hashed, not raw address
    if event.wallet_cluster_id and len(event.wallet_cluster_id) > 44:
        warnings.append("wallet_cluster_id may be a raw address - should be hashed")

    # Warnings
    if event.wallet_cluster_id is None:
        warnings.append("wallet_cluster_id not provided")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_social_event(event: SocialEvent) -> ValidationResult:
    """Validate a social event."""
    errors = []
    warnings = []

    # Required fields
    if not event.event_id:
        errors.append("event_id is required")
    if not event.event_type:
        errors.append("event_type is required")
    if not event.source:
        errors.append("source is required")

    # Value validation
    if event.sentiment_score is not None:
        if event.sentiment_score < -1 or event.sentiment_score > 1:
            errors.append("sentiment_score must be between -1.0 and 1.0")
    if event.mention_count is not None and event.mention_count < 0:
        errors.append("mention_count cannot be negative")
    if event.engagement_score is not None and event.engagement_score < 0:
        errors.append("engagement_score cannot be negative")

    # Warnings
    if event.token_symbol is None:
        warnings.append("token_symbol not provided")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_risk_event(event: RiskEvent) -> ValidationResult:
    """Validate a risk event."""
    errors = []
    warnings = []

    # Required fields
    if not event.event_id:
        errors.append("event_id is required")
    if not event.event_type:
        errors.append("event_type is required")

    # Score validation (all must be 0.0 - 1.0)
    score_fields = [
        ("overall_risk_score", event.overall_risk_score),
        ("honeypot_score", event.honeypot_score),
        ("rug_pull_score", event.rug_pull_score),
        ("no_exit_score", event.no_exit_score),
        ("insider_concentration_score", event.insider_concentration_score),
        ("confidence", event.confidence),
    ]
    for field_name, value in score_fields:
        if value < 0 or value > 1:
            errors.append(f"{field_name} must be between 0.0 and 1.0")

    # Consistency checks
    if event.is_honeypot and event.honeypot_score < 0.5:
        warnings.append("is_honeypot=True but honeypot_score < 0.5")
    if event.is_exit_blocked and event.no_exit_score < 0.5:
        warnings.append("is_exit_blocked=True but no_exit_score < 0.5")

    # Warnings
    if event.token_address is None:
        warnings.append("token_address not provided")
    if len(event.risk_factors) == 0:
        warnings.append("no risk_factors provided")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Event Type Union
# ---------------------------------------------------------------------------

AnyEvent = Union[MarketEvent, TokenEvent, WalletEvent, SocialEvent, RiskEvent]


def validate_event(event: AnyEvent) -> ValidationResult:
    """Validate any event type."""
    if isinstance(event, MarketEvent):
        return validate_market_event(event)
    elif isinstance(event, TokenEvent):
        return validate_token_event(event)
    elif isinstance(event, WalletEvent):
        return validate_wallet_event(event)
    elif isinstance(event, SocialEvent):
        return validate_social_event(event)
    elif isinstance(event, RiskEvent):
        return validate_risk_event(event)
    else:
        return ValidationResult(
            is_valid=False,
            errors=[f"Unknown event type: {type(event).__name__}"],
            warnings=[],
        )
