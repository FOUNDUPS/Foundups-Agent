"""Trade FoundUp - Adapter Contract Tests

Tests for adapter abstraction layer in src/adapters.py.

WSP References:
- WSP 97: Truth Boundaries (all adapters simulation-only)
- WSP 11: Interface Protocol (adapter contracts)
"""
import pytest
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from adapters import (
    AdapterCapability,
    AdapterHealth,
    AdapterRateLimit,
    AdapterErrorCode,
    AdapterError,
    AdapterResult,
    MarketAdapter,
    LaunchpadAdapter,
    AdapterRegistry,
    get_adapter_registry,
    reset_adapter_registry,
)
from contracts import (
    AdapterStatus,
    MarketAdapterSpec,
    LaunchpadAdapterSpec,
)


class TestAdapterCapability:
    """AdapterCapability enum tests."""

    def test_market_capabilities_exist(self):
        """Market data capabilities are defined."""
        assert AdapterCapability.TOKEN_EVENTS == "token_events"
        assert AdapterCapability.WALLET_EVENTS == "wallet_events"
        assert AdapterCapability.OHLCV_DATA == "ohlcv_data"
        assert AdapterCapability.ORDER_BOOK == "order_book"
        assert AdapterCapability.SOCIAL_SIGNALS == "social_signals"

    def test_launchpad_capabilities_exist(self):
        """Launchpad capabilities are defined."""
        assert AdapterCapability.LAUNCH_DETECTION == "launch_detection"
        assert AdapterCapability.BONDING_CURVE == "bonding_curve"
        assert AdapterCapability.MIGRATION_TRACKING == "migration_tracking"
        assert AdapterCapability.TOP_TRADERS == "top_traders"
        assert AdapterCapability.HOLDER_DISTRIBUTION == "holder_distribution"

    def test_risk_capabilities_exist(self):
        """Risk detection capabilities are defined."""
        assert AdapterCapability.HONEYPOT_DETECTION == "honeypot_detection"
        assert AdapterCapability.RUG_DETECTION == "rug_detection"
        assert AdapterCapability.LIQUIDITY_ANALYSIS == "liquidity_analysis"


class TestAdapterHealth:
    """AdapterHealth dataclass tests."""

    def test_default_health_is_healthy(self):
        """Default health status is healthy."""
        health = AdapterHealth(adapter_id="test")
        assert health.is_healthy is True
        assert health.success_rate == 1.0
        assert health.consecutive_failures == 0

    def test_health_with_failures(self):
        """Health with failures records correctly."""
        health = AdapterHealth(
            adapter_id="test",
            is_healthy=False,
            requests_total=100,
            requests_failed=25,
            success_rate=0.75,
            consecutive_failures=3,
            last_error_message="Connection timeout",
        )
        assert health.is_healthy is False
        assert health.success_rate == 0.75
        assert health.requests_failed == 25
        assert health.consecutive_failures == 3

    def test_health_rate_limited(self):
        """Health records rate limit status."""
        health = AdapterHealth(
            adapter_id="test",
            rate_limited=True,
            rate_limit_remaining=0,
            rate_limit_reset=datetime.now(timezone.utc),
        )
        assert health.rate_limited is True
        assert health.rate_limit_remaining == 0

    def test_health_to_dict(self):
        """Health serializes to dict."""
        health = AdapterHealth(adapter_id="test")
        d = health.to_dict()
        assert d["adapter_id"] == "test"
        assert d["is_healthy"] is True
        assert "last_check" in d


class TestAdapterRateLimit:
    """AdapterRateLimit dataclass tests."""

    def test_default_rate_limit(self):
        """Default rate limit has sensible defaults."""
        limit = AdapterRateLimit(adapter_id="test")
        assert limit.requests_per_second == 1.0
        assert limit.requests_per_minute == 60
        assert limit.requests_per_hour == 1000
        assert limit.burst_limit == 10

    def test_is_rate_limited_false_by_default(self):
        """Not rate limited by default."""
        limit = AdapterRateLimit(adapter_id="test")
        assert limit.is_rate_limited() is False

    def test_increase_backoff(self):
        """Backoff increases exponentially."""
        limit = AdapterRateLimit(
            adapter_id="test",
            backoff_base_seconds=1.0,
            backoff_multiplier=2.0,
        )

        # First backoff
        backoff1 = limit.increase_backoff()
        assert backoff1 == 1.0
        assert limit.is_rate_limited() is True

        # Second backoff
        backoff2 = limit.increase_backoff()
        assert backoff2 == 2.0

        # Third backoff
        backoff3 = limit.increase_backoff()
        assert backoff3 == 4.0

    def test_backoff_max_limit(self):
        """Backoff respects max limit."""
        limit = AdapterRateLimit(
            adapter_id="test",
            backoff_base_seconds=30.0,
            backoff_max_seconds=60.0,
            backoff_multiplier=2.0,
        )
        limit.increase_backoff()  # 30
        limit.increase_backoff()  # Would be 60, clamped to max
        backoff = limit.increase_backoff()  # Still 60, not 120
        assert backoff == 60.0

    def test_reset_backoff(self):
        """Backoff resets correctly."""
        limit = AdapterRateLimit(adapter_id="test")
        limit.increase_backoff()
        assert limit.is_rate_limited() is True
        limit.reset_backoff()
        assert limit.is_rate_limited() is False

    def test_rate_limit_to_dict(self):
        """Rate limit serializes to dict."""
        limit = AdapterRateLimit(adapter_id="test")
        d = limit.to_dict()
        assert d["adapter_id"] == "test"
        assert d["requests_per_second"] == 1.0
        assert d["is_rate_limited"] is False


class TestAdapterError:
    """AdapterError dataclass tests."""

    def test_error_code_values(self):
        """Error codes have expected values."""
        assert AdapterErrorCode.RATE_LIMITED == "rate_limited"
        assert AdapterErrorCode.NETWORK_ERROR == "network_error"
        assert AdapterErrorCode.EXECUTION_BLOCKED == "execution_blocked"

    def test_error_creation(self):
        """Error creates with required fields."""
        error = AdapterError(
            adapter_id="pumpfun",
            error_code=AdapterErrorCode.RATE_LIMITED,
            message="Rate limit exceeded",
        )
        assert error.adapter_id == "pumpfun"
        assert error.error_code == AdapterErrorCode.RATE_LIMITED
        assert error.is_retryable is True  # Default

    def test_non_retryable_error(self):
        """Non-retryable errors flagged correctly."""
        error = AdapterError(
            adapter_id="test",
            error_code=AdapterErrorCode.UNSUPPORTED_OPERATION,
            message="Operation not supported",
            is_retryable=False,
        )
        assert error.is_retryable is False

    def test_error_to_dict(self):
        """Error serializes to dict."""
        error = AdapterError(
            adapter_id="test",
            error_code=AdapterErrorCode.TIMEOUT,
            message="Request timed out",
            operation="fetch_token_events",
        )
        d = error.to_dict()
        assert d["adapter_id"] == "test"
        assert d["error_code"] == "timeout"
        assert d["operation"] == "fetch_token_events"


class TestAdapterResult:
    """AdapterResult dataclass tests."""

    def test_success_result(self):
        """Success result creates correctly."""
        result = AdapterResult(
            adapter_id="pumpfun",
            operation="fetch_recent_launches",
            success=True,
            data={"tokens": []},
        )
        assert result.success is True
        assert result.error is None
        assert result.is_simulation is True  # Phase 0 default

    def test_failure_result(self):
        """Failure result includes error."""
        error = AdapterError(
            adapter_id="pumpfun",
            error_code=AdapterErrorCode.NETWORK_ERROR,
            message="Connection failed",
        )
        result = AdapterResult(
            adapter_id="pumpfun",
            operation="fetch_recent_launches",
            success=False,
            error=error,
        )
        assert result.success is False
        assert result.error is not None
        assert result.error.error_code == AdapterErrorCode.NETWORK_ERROR

    def test_result_is_simulation_default_true(self):
        """is_simulation defaults to True (Phase 0)."""
        result = AdapterResult(
            adapter_id="test",
            operation="test",
            success=True,
        )
        assert result.is_simulation is True

    def test_result_to_dict(self):
        """Result serializes to dict."""
        result = AdapterResult(
            adapter_id="test",
            operation="fetch_data",
            success=True,
            latency_ms=150.0,
        )
        d = result.to_dict()
        assert d["adapter_id"] == "test"
        assert d["success"] is True
        assert d["latency_ms"] == 150.0
        assert d["is_simulation"] is True


class TestAdapterRegistry:
    """AdapterRegistry tests."""

    @pytest.fixture
    def registry(self):
        """Create fresh registry for each test."""
        reset_adapter_registry()
        return AdapterRegistry()

    @pytest.fixture
    def mock_market_adapter(self):
        """Create a mock market adapter."""
        @dataclass
        class MockMarketAdapter:
            adapter_id: str = "solana"

            @property
            def spec(self) -> MarketAdapterSpec:
                return MarketAdapterSpec(
                    adapter_id=self.adapter_id,
                    chain_or_exchange="solana",
                    display_name="Solana",
                    status=AdapterStatus.SIMULATION,
                )

            def get_capabilities(self) -> List[AdapterCapability]:
                return [
                    AdapterCapability.TOKEN_EVENTS,
                    AdapterCapability.WALLET_EVENTS,
                ]

            def get_health(self) -> AdapterHealth:
                return AdapterHealth(adapter_id=self.adapter_id)

            async def fetch_market_data(self, symbol: str, **kwargs) -> AdapterResult:
                return AdapterResult(
                    adapter_id=self.adapter_id,
                    operation="fetch_market_data",
                    success=True,
                )

            async def fetch_token_events(self, token_address: str, **kwargs) -> AdapterResult:
                return AdapterResult(
                    adapter_id=self.adapter_id,
                    operation="fetch_token_events",
                    success=True,
                )

            async def fetch_wallet_events(self, wallet_address: str, **kwargs) -> AdapterResult:
                return AdapterResult(
                    adapter_id=self.adapter_id,
                    operation="fetch_wallet_events",
                    success=True,
                )

        return MockMarketAdapter()

    @pytest.fixture
    def mock_launchpad_adapter(self):
        """Create a mock launchpad adapter."""
        @dataclass
        class MockLaunchpadAdapter:
            adapter_id: str = "pumpfun"

            @property
            def spec(self) -> LaunchpadAdapterSpec:
                return LaunchpadAdapterSpec(
                    adapter_id=self.adapter_id,
                    platform_name="pump.fun",
                    chain="solana",
                    display_name="Pump.fun",
                    status=AdapterStatus.SIMULATION,
                )

            def get_capabilities(self) -> List[AdapterCapability]:
                return [
                    AdapterCapability.LAUNCH_DETECTION,
                    AdapterCapability.BONDING_CURVE,
                ]

            def get_health(self) -> AdapterHealth:
                return AdapterHealth(adapter_id=self.adapter_id)

            async def fetch_recent_launches(self, limit: int = 100, **kwargs) -> AdapterResult:
                return AdapterResult(
                    adapter_id=self.adapter_id,
                    operation="fetch_recent_launches",
                    success=True,
                )

            async def fetch_bonding_curve(self, token_address: str, **kwargs) -> AdapterResult:
                return AdapterResult(
                    adapter_id=self.adapter_id,
                    operation="fetch_bonding_curve",
                    success=True,
                )

            async def fetch_top_traders(self, token_address: str, **kwargs) -> AdapterResult:
                return AdapterResult(
                    adapter_id=self.adapter_id,
                    operation="fetch_top_traders",
                    success=True,
                )

            async def fetch_holder_distribution(self, token_address: str, **kwargs) -> AdapterResult:
                return AdapterResult(
                    adapter_id=self.adapter_id,
                    operation="fetch_holder_distribution",
                    success=True,
                )

        return MockLaunchpadAdapter()

    def test_register_market_adapter(self, registry, mock_market_adapter):
        """Can register a market adapter."""
        registry.register_market_adapter(mock_market_adapter)
        assert "solana" in registry.list_market_adapters()

    def test_register_launchpad_adapter(self, registry, mock_launchpad_adapter):
        """Can register a launchpad adapter."""
        registry.register_launchpad_adapter(mock_launchpad_adapter)
        assert "pumpfun" in registry.list_launchpad_adapters()

    def test_register_duplicate_raises(self, registry, mock_market_adapter):
        """Duplicate registration raises ValueError."""
        registry.register_market_adapter(mock_market_adapter)
        with pytest.raises(ValueError):
            registry.register_market_adapter(mock_market_adapter)

    def test_get_market_adapter(self, registry, mock_market_adapter):
        """Can retrieve market adapter by ID."""
        registry.register_market_adapter(mock_market_adapter)
        adapter = registry.get_market_adapter("solana")
        assert adapter is not None
        assert adapter.adapter_id == "solana"

    def test_get_launchpad_adapter(self, registry, mock_launchpad_adapter):
        """Can retrieve launchpad adapter by ID."""
        registry.register_launchpad_adapter(mock_launchpad_adapter)
        adapter = registry.get_launchpad_adapter("pumpfun")
        assert adapter is not None
        assert adapter.adapter_id == "pumpfun"

    def test_get_nonexistent_adapter(self, registry):
        """Getting nonexistent adapter returns None."""
        assert registry.get_market_adapter("nonexistent") is None
        assert registry.get_launchpad_adapter("nonexistent") is None

    def test_unregister_adapter(self, registry, mock_market_adapter):
        """Can unregister an adapter."""
        registry.register_market_adapter(mock_market_adapter)
        assert registry.unregister_adapter("solana") is True
        assert "solana" not in registry.list_market_adapters()

    def test_unregister_nonexistent(self, registry):
        """Unregistering nonexistent adapter returns False."""
        assert registry.unregister_adapter("nonexistent") is False

    def test_find_adapters_with_capability(
        self, registry, mock_market_adapter, mock_launchpad_adapter
    ):
        """Can find adapters by capability."""
        registry.register_market_adapter(mock_market_adapter)
        registry.register_launchpad_adapter(mock_launchpad_adapter)

        # Find adapters with TOKEN_EVENTS
        adapters = registry.find_adapters_with_capability(AdapterCapability.TOKEN_EVENTS)
        assert "solana" in adapters
        assert "pumpfun" not in adapters

        # Find adapters with LAUNCH_DETECTION
        adapters = registry.find_adapters_with_capability(AdapterCapability.LAUNCH_DETECTION)
        assert "pumpfun" in adapters
        assert "solana" not in adapters

    def test_adapter_health_management(self, registry, mock_market_adapter):
        """Can update and retrieve adapter health."""
        registry.register_market_adapter(mock_market_adapter)

        # Check initial health
        health = registry.get_adapter_health("solana")
        assert health is not None
        assert health.is_healthy is True

        # Update health
        new_health = AdapterHealth(adapter_id="solana", is_healthy=False)
        registry.update_adapter_health(new_health)

        # Verify update
        health = registry.get_adapter_health("solana")
        assert health.is_healthy is False

    def test_get_healthy_unhealthy_adapters(self, registry, mock_market_adapter):
        """Can filter healthy/unhealthy adapters."""
        registry.register_market_adapter(mock_market_adapter)

        # Initially healthy
        assert "solana" in registry.get_healthy_adapters()
        assert "solana" not in registry.get_unhealthy_adapters()

        # Mark unhealthy
        registry.update_adapter_health(AdapterHealth(adapter_id="solana", is_healthy=False))

        assert "solana" not in registry.get_healthy_adapters()
        assert "solana" in registry.get_unhealthy_adapters()

    def test_rate_limit_management(self, registry, mock_market_adapter):
        """Can manage adapter rate limits."""
        registry.register_market_adapter(mock_market_adapter)

        # Set rate limit
        limit = AdapterRateLimit(adapter_id="solana", requests_per_second=0.5)
        registry.set_rate_limit(limit)

        # Retrieve
        retrieved = registry.get_rate_limit("solana")
        assert retrieved is not None
        assert retrieved.requests_per_second == 0.5

    def test_is_rate_limited(self, registry, mock_market_adapter):
        """Can check if adapter is rate limited."""
        registry.register_market_adapter(mock_market_adapter)

        # Not rate limited initially
        assert registry.is_rate_limited("solana") is False

        # Set and trigger rate limit
        limit = AdapterRateLimit(adapter_id="solana")
        limit.increase_backoff()  # Now rate limited
        registry.set_rate_limit(limit)

        assert registry.is_rate_limited("solana") is True

    def test_registry_summary(self, registry, mock_market_adapter, mock_launchpad_adapter):
        """Can get registry summary."""
        registry.register_market_adapter(mock_market_adapter)
        registry.register_launchpad_adapter(mock_launchpad_adapter)

        summary = registry.get_registry_summary()
        assert summary["total_adapters"] == 2
        assert summary["market_adapters"] == 1
        assert summary["launchpad_adapters"] == 1
        assert summary["healthy_adapters"] == 2

    def test_registry_to_dict(self, registry, mock_market_adapter):
        """Registry serializes to dict."""
        registry.register_market_adapter(mock_market_adapter)
        d = registry.to_dict()
        assert "summary" in d
        assert "health" in d
        assert "rate_limits" in d


class TestSingletonRegistry:
    """Test singleton registry behavior."""

    def test_get_adapter_registry_singleton(self):
        """get_adapter_registry returns same instance."""
        reset_adapter_registry()
        reg1 = get_adapter_registry()
        reg2 = get_adapter_registry()
        assert reg1 is reg2

    def test_reset_adapter_registry(self):
        """reset_adapter_registry creates new instance."""
        reset_adapter_registry()
        reg1 = get_adapter_registry()
        reset_adapter_registry()
        reg2 = get_adapter_registry()
        assert reg1 is not reg2
