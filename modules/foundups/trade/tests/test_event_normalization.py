"""Trade FoundUp - Event Normalization Tests

Tests for event normalization layer in src/events.py.

WSP References:
- WSP 97: Truth Boundaries (events are observation, not execution)
- WSP 11: Interface Protocol (event contracts)
"""
import pytest
from datetime import datetime, timezone

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from events import (
    # ID generation
    generate_event_id,
    generate_deterministic_event_id,
    # Market events
    create_market_event,
    create_price_update_event,
    create_volume_spike_event,
    create_liquidity_change_event,
    # Token events
    create_token_event,
    create_token_created_event,
    create_migration_event,
    # Wallet events
    create_wallet_event,
    create_buy_event,
    create_sell_event,
    hash_wallet_address,
    # Social events
    create_social_event,
    create_mention_event,
    create_sentiment_shift_event,
    # Risk events
    create_risk_event,
    create_honeypot_detection_event,
    create_rug_risk_event,
    # Validation
    ValidationResult,
    validate_market_event,
    validate_token_event,
    validate_wallet_event,
    validate_social_event,
    validate_risk_event,
    validate_event,
)
from contracts import (
    MarketEvent,
    TokenEvent,
    WalletEvent,
    SocialEvent,
    RiskEvent,
)


class TestEventIdGeneration:
    """Event ID generation tests."""

    def test_generate_event_id_has_prefix(self):
        """Generated ID has correct prefix."""
        id1 = generate_event_id("mkt")
        assert id1.startswith("mkt_")

    def test_generate_event_id_unique(self):
        """Generated IDs are unique."""
        ids = [generate_event_id("evt") for _ in range(100)]
        assert len(set(ids)) == 100

    def test_generate_deterministic_event_id(self):
        """Deterministic ID is reproducible."""
        ts = datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)
        id1 = generate_deterministic_event_id(
            event_type="price_update",
            adapter_id="solana",
            payload_hash="abc123",
            timestamp=ts,
        )
        id2 = generate_deterministic_event_id(
            event_type="price_update",
            adapter_id="solana",
            payload_hash="abc123",
            timestamp=ts,
        )
        assert id1 == id2

    def test_generate_deterministic_event_id_different_inputs(self):
        """Different inputs produce different deterministic IDs."""
        ts = datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)
        id1 = generate_deterministic_event_id("price_update", "solana", "abc", ts)
        id2 = generate_deterministic_event_id("price_update", "solana", "xyz", ts)
        assert id1 != id2


class TestMarketEventHelpers:
    """Market event helper tests."""

    def test_create_market_event_basic(self):
        """Create basic market event."""
        event = create_market_event(
            event_type="price_update",
            adapter_id="solana",
            chain="solana",
        )
        assert event.event_type == "price_update"
        assert event.adapter_id == "solana"
        assert event.chain == "solana"
        assert event.event_id.startswith("mkt_")

    def test_create_market_event_with_data(self):
        """Create market event with all fields."""
        event = create_market_event(
            event_type="price_update",
            adapter_id="solana",
            chain="solana",
            symbol="SOL/USD",
            price_usd=150.0,
            volume_24h=1000000.0,
            market_cap=50000000000.0,
            liquidity_usd=100000000.0,
            raw_data={"source": "test"},
        )
        assert event.symbol == "SOL/USD"
        assert event.price_usd == 150.0
        assert event.volume_24h == 1000000.0
        assert event.raw_data == {"source": "test"}

    def test_create_price_update_event(self):
        """Create price update event shortcut."""
        event = create_price_update_event(
            adapter_id="solana",
            chain="solana",
            symbol="MEME",
            price_usd=0.001,
        )
        assert event.event_type == "price_update"
        assert event.symbol == "MEME"
        assert event.price_usd == 0.001

    def test_create_volume_spike_event(self):
        """Create volume spike event shortcut."""
        event = create_volume_spike_event(
            adapter_id="solana",
            chain="solana",
            symbol="MEME",
            volume_24h=5000000.0,
        )
        assert event.event_type == "volume_spike"
        assert event.volume_24h == 5000000.0

    def test_create_liquidity_change_event(self):
        """Create liquidity change event shortcut."""
        event = create_liquidity_change_event(
            adapter_id="solana",
            chain="solana",
            symbol="MEME",
            liquidity_usd=250000.0,
        )
        assert event.event_type == "liquidity_change"
        assert event.liquidity_usd == 250000.0


class TestTokenEventHelpers:
    """Token event helper tests."""

    def test_create_token_event_basic(self):
        """Create basic token event."""
        event = create_token_event(
            event_type="token_created",
            adapter_id="pumpfun",
            chain="solana",
        )
        assert event.event_type == "token_created"
        assert event.adapter_id == "pumpfun"
        assert event.event_id.startswith("tok_")

    def test_create_token_event_with_data(self):
        """Create token event with all fields."""
        event = create_token_event(
            event_type="token_created",
            adapter_id="pumpfun",
            chain="solana",
            token_address="ABC123...",
            token_symbol="MEME",
            token_name="Meme Coin",
            creator_address="XYZ789...",
            launchpad="pumpfun",
            bonding_curve_progress=0.25,
        )
        assert event.token_symbol == "MEME"
        assert event.launchpad == "pumpfun"
        assert event.bonding_curve_progress == 0.25

    def test_create_token_created_event(self):
        """Create token creation event shortcut."""
        event = create_token_created_event(
            adapter_id="pumpfun",
            chain="solana",
            token_address="ABC123",
            token_symbol="MEME",
            token_name="Meme Coin",
            launchpad="pumpfun",
        )
        assert event.event_type == "token_created"
        assert event.token_address == "ABC123"
        assert event.launchpad == "pumpfun"

    def test_create_migration_event(self):
        """Create migration event shortcut."""
        event = create_migration_event(
            adapter_id="pumpfun",
            chain="solana",
            token_address="ABC123",
            token_symbol="MEME",
            launchpad="pumpfun",
        )
        assert event.event_type == "migrated_to_dex"
        assert event.bonding_curve_progress == 1.0


class TestWalletEventHelpers:
    """Wallet event helper tests."""

    def test_create_wallet_event_basic(self):
        """Create basic wallet event."""
        event = create_wallet_event(
            event_type="buy",
            adapter_id="solana",
            chain="solana",
        )
        assert event.event_type == "buy"
        assert event.event_id.startswith("wal_")

    def test_create_wallet_event_with_data(self):
        """Create wallet event with all fields."""
        event = create_wallet_event(
            event_type="buy",
            adapter_id="solana",
            chain="solana",
            wallet_cluster_id="cluster_abc",
            is_known_entity=True,
            entity_label="whale",
            token_address="TOKEN123",
            action="buy",
            amount_tokens=1000000.0,
            amount_usd=5000.0,
        )
        assert event.wallet_cluster_id == "cluster_abc"
        assert event.is_known_entity is True
        assert event.entity_label == "whale"
        assert event.amount_usd == 5000.0

    def test_create_buy_event(self):
        """Create buy event shortcut."""
        event = create_buy_event(
            adapter_id="solana",
            chain="solana",
            wallet_cluster_id="cluster_123",
            token_address="TOKEN123",
            amount_tokens=50000.0,
            amount_usd=250.0,
        )
        assert event.event_type == "buy"
        assert event.action == "buy"
        assert event.amount_tokens == 50000.0

    def test_create_sell_event(self):
        """Create sell event shortcut."""
        event = create_sell_event(
            adapter_id="solana",
            chain="solana",
            wallet_cluster_id="cluster_123",
            token_address="TOKEN123",
            amount_tokens=50000.0,
            entity_label="insider",
        )
        assert event.event_type == "sell"
        assert event.action == "sell"
        assert event.is_known_entity is True
        assert event.entity_label == "insider"

    def test_hash_wallet_address(self):
        """Hash wallet address for privacy."""
        address = "0x1234567890abcdef1234567890abcdef12345678"
        hashed = hash_wallet_address(address)

        # Should be consistent
        assert hash_wallet_address(address) == hashed

        # Should be shorter than original
        assert len(hashed) == 16

        # Different addresses produce different hashes
        other_address = "0xabcdef1234567890abcdef1234567890abcdef12"
        assert hash_wallet_address(other_address) != hashed

    def test_hash_wallet_address_case_insensitive(self):
        """Hash is case-insensitive."""
        lower = hash_wallet_address("0xabcdef")
        upper = hash_wallet_address("0xABCDEF")
        assert lower == upper


class TestSocialEventHelpers:
    """Social event helper tests."""

    def test_create_social_event_basic(self):
        """Create basic social event."""
        event = create_social_event(
            event_type="mention",
            source="twitter",
        )
        assert event.event_type == "mention"
        assert event.source == "twitter"
        assert event.event_id.startswith("soc_")

    def test_create_social_event_with_data(self):
        """Create social event with all fields."""
        event = create_social_event(
            event_type="sentiment_shift",
            source="telegram",
            token_symbol="MEME",
            sentiment_score=0.85,
            mention_count=1000,
            engagement_score=0.75,
            bot_activity_detected=True,
            coordinated_activity_detected=False,
        )
        assert event.sentiment_score == 0.85
        assert event.mention_count == 1000
        assert event.bot_activity_detected is True

    def test_create_mention_event(self):
        """Create mention event shortcut."""
        event = create_mention_event(
            source="twitter",
            token_symbol="MEME",
            mention_count=500,
            sentiment_score=0.6,
        )
        assert event.event_type == "mention"
        assert event.mention_count == 500

    def test_create_sentiment_shift_event(self):
        """Create sentiment shift event shortcut."""
        event = create_sentiment_shift_event(
            source="discord",
            token_symbol="MEME",
            sentiment_score=-0.3,
        )
        assert event.event_type == "sentiment_shift"
        assert event.sentiment_score == -0.3


class TestRiskEventHelpers:
    """Risk event helper tests."""

    def test_create_risk_event_basic(self):
        """Create basic risk event."""
        event = create_risk_event(
            event_type="honeypot_detected",
        )
        assert event.event_type == "honeypot_detected"
        assert event.event_id.startswith("rsk_")

    def test_create_risk_event_with_scores(self):
        """Create risk event with all scores."""
        event = create_risk_event(
            event_type="rug_risk",
            token_address="TOKEN123",
            chain="solana",
            overall_risk_score=0.8,
            honeypot_score=0.2,
            rug_pull_score=0.9,
            no_exit_score=0.1,
            insider_concentration_score=0.7,
            is_honeypot=False,
            has_suspicious_holders=True,
            risk_factors=["high_concentration", "new_token"],
            confidence=0.85,
        )
        assert event.overall_risk_score == 0.8
        assert event.rug_pull_score == 0.9
        assert event.has_suspicious_holders is True
        assert len(event.risk_factors) == 2

    def test_create_honeypot_detection_event(self):
        """Create honeypot detection event shortcut."""
        event = create_honeypot_detection_event(
            token_address="TOKEN123",
            chain="solana",
            honeypot_score=0.95,
            confidence=0.9,
        )
        assert event.event_type == "honeypot_detected"
        assert event.is_honeypot is True  # Score >= 0.8
        assert "honeypot_detected" in event.risk_factors

    def test_create_honeypot_detection_low_score(self):
        """Honeypot detection with low score not flagged."""
        event = create_honeypot_detection_event(
            token_address="TOKEN123",
            chain="solana",
            honeypot_score=0.3,
        )
        assert event.is_honeypot is False
        assert "honeypot_detected" not in event.risk_factors

    def test_create_rug_risk_event(self):
        """Create rug risk event shortcut."""
        event = create_rug_risk_event(
            token_address="TOKEN123",
            chain="solana",
            rug_pull_score=0.85,
            insider_concentration_score=0.75,
        )
        assert event.event_type == "rug_risk"
        assert event.overall_risk_score == 0.85  # Max of scores
        assert "high_rug_risk" in event.risk_factors
        assert "insider_concentration" in event.risk_factors
        assert event.has_suspicious_holders is True


class TestMarketEventValidation:
    """Market event validation tests."""

    def test_valid_market_event(self):
        """Valid market event passes validation."""
        event = create_market_event(
            event_type="price_update",
            adapter_id="solana",
            chain="solana",
            symbol="MEME",
            price_usd=0.001,
        )
        result = validate_market_event(event)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_market_event_missing_required(self):
        """Market event with missing required fields fails."""
        event = MarketEvent(
            event_id="",  # Empty
            event_type="",  # Empty
            adapter_id="",  # Empty
            chain="",  # Empty
        )
        result = validate_market_event(event)
        assert result.is_valid is False
        assert "event_id is required" in result.errors

    def test_market_event_negative_values(self):
        """Market event with negative values fails."""
        event = create_market_event(
            event_type="price_update",
            adapter_id="solana",
            chain="solana",
            price_usd=-10.0,
            volume_24h=-1000.0,
        )
        result = validate_market_event(event)
        assert result.is_valid is False
        assert "price_usd cannot be negative" in result.errors
        assert "volume_24h cannot be negative" in result.errors

    def test_market_event_warnings(self):
        """Market event with missing optional fields gets warnings."""
        event = create_market_event(
            event_type="price_update",
            adapter_id="solana",
            chain="solana",
        )
        result = validate_market_event(event)
        assert result.is_valid is True
        assert "symbol not provided" in result.warnings


class TestTokenEventValidation:
    """Token event validation tests."""

    def test_valid_token_event(self):
        """Valid token event passes validation."""
        event = create_token_event(
            event_type="token_created",
            adapter_id="pumpfun",
            chain="solana",
            token_address="ABC123",
            token_symbol="MEME",
        )
        result = validate_token_event(event)
        assert result.is_valid is True

    def test_token_event_invalid_bonding_curve(self):
        """Token event with invalid bonding curve fails."""
        event = create_token_event(
            event_type="token_created",
            adapter_id="pumpfun",
            chain="solana",
            bonding_curve_progress=1.5,  # Invalid: > 1.0
        )
        result = validate_token_event(event)
        assert result.is_valid is False
        assert "bonding_curve_progress must be between 0.0 and 1.0" in result.errors


class TestWalletEventValidation:
    """Wallet event validation tests."""

    def test_valid_wallet_event(self):
        """Valid wallet event passes validation."""
        event = create_buy_event(
            adapter_id="solana",
            chain="solana",
            wallet_cluster_id="cluster_abc",
            token_address="TOKEN123",
            amount_tokens=1000.0,
        )
        result = validate_wallet_event(event)
        assert result.is_valid is True

    def test_wallet_event_negative_amount(self):
        """Wallet event with negative amount fails."""
        event = create_wallet_event(
            event_type="buy",
            adapter_id="solana",
            chain="solana",
            amount_tokens=-100.0,
        )
        result = validate_wallet_event(event)
        assert result.is_valid is False
        assert "amount_tokens cannot be negative" in result.errors

    def test_wallet_event_raw_address_warning(self):
        """Wallet event with long address gets warning."""
        event = create_wallet_event(
            event_type="buy",
            adapter_id="solana",
            chain="solana",
            wallet_cluster_id="0x1234567890abcdef1234567890abcdef1234567890abcdef",  # Too long
        )
        result = validate_wallet_event(event)
        assert result.is_valid is True
        assert any("raw address" in w for w in result.warnings)


class TestSocialEventValidation:
    """Social event validation tests."""

    def test_valid_social_event(self):
        """Valid social event passes validation."""
        event = create_mention_event(
            source="twitter",
            token_symbol="MEME",
            mention_count=100,
        )
        result = validate_social_event(event)
        assert result.is_valid is True

    def test_social_event_invalid_sentiment(self):
        """Social event with invalid sentiment fails."""
        event = create_social_event(
            event_type="sentiment_shift",
            source="twitter",
            sentiment_score=1.5,  # Invalid: > 1.0
        )
        result = validate_social_event(event)
        assert result.is_valid is False
        assert "sentiment_score must be between -1.0 and 1.0" in result.errors


class TestRiskEventValidation:
    """Risk event validation tests."""

    def test_valid_risk_event(self):
        """Valid risk event passes validation."""
        event = create_honeypot_detection_event(
            token_address="TOKEN123",
            chain="solana",
            honeypot_score=0.9,
            confidence=0.85,
        )
        result = validate_risk_event(event)
        assert result.is_valid is True

    def test_risk_event_invalid_scores(self):
        """Risk event with invalid scores fails."""
        event = create_risk_event(
            event_type="rug_risk",
            overall_risk_score=1.5,  # Invalid: > 1.0
            honeypot_score=-0.1,  # Invalid: < 0.0
        )
        result = validate_risk_event(event)
        assert result.is_valid is False
        assert "overall_risk_score must be between 0.0 and 1.0" in result.errors
        assert "honeypot_score must be between 0.0 and 1.0" in result.errors

    def test_risk_event_consistency_warning(self):
        """Risk event with inconsistent flags gets warning."""
        event = RiskEvent(
            event_id="test",
            event_type="honeypot_detected",
            is_honeypot=True,
            honeypot_score=0.3,  # Low score but flagged
        )
        result = validate_risk_event(event)
        assert result.is_valid is True
        assert any("honeypot_score < 0.5" in w for w in result.warnings)


class TestGenericValidation:
    """Generic validate_event function tests."""

    def test_validate_market_event(self):
        """validate_event works with MarketEvent."""
        event = create_price_update_event("solana", "solana", "MEME", 0.001)
        result = validate_event(event)
        assert result.is_valid is True

    def test_validate_token_event(self):
        """validate_event works with TokenEvent."""
        event = create_token_created_event(
            "pumpfun", "solana", "ABC", "MEME", "Meme Coin"
        )
        result = validate_event(event)
        assert result.is_valid is True

    def test_validate_wallet_event(self):
        """validate_event works with WalletEvent."""
        event = create_buy_event("solana", "solana", "cluster", "TOKEN", 1000)
        result = validate_event(event)
        assert result.is_valid is True

    def test_validate_social_event(self):
        """validate_event works with SocialEvent."""
        event = create_mention_event("twitter", "MEME", 100)
        result = validate_event(event)
        assert result.is_valid is True

    def test_validate_risk_event(self):
        """validate_event works with RiskEvent."""
        event = create_honeypot_detection_event("TOKEN", "solana", 0.5)
        result = validate_event(event)
        assert result.is_valid is True


class TestValidationResult:
    """ValidationResult dataclass tests."""

    def test_validation_result_to_dict(self):
        """ValidationResult serializes to dict."""
        result = ValidationResult(
            is_valid=False,
            errors=["error1", "error2"],
            warnings=["warning1"],
        )
        d = result.to_dict()
        assert d["is_valid"] is False
        assert len(d["errors"]) == 2
        assert len(d["warnings"]) == 1
