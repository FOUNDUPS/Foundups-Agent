"""Trade FoundUp - Adapter Abstraction Layer

Protocols and registry for market/launchpad adapters.
All adapters are simulation-only in Phase 0.

WSP References:
- WSP 97: Truth Boundaries (no real execution)
- WSP 11: Interface Protocol (adapter contracts)
- WSP 104: FoundUp Route Namespace

Phase 0 Constraints:
- live_execution_enabled: False (always)
- All adapters return simulation data only
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, TypeVar, runtime_checkable

try:
    from .contracts import (
        AdapterStatus,
        MarketAdapterSpec,
        LaunchpadAdapterSpec,
        MarketEvent,
        TokenEvent,
        WalletEvent,
        RiskEvent,
    )
except ImportError:
    from contracts import (
        AdapterStatus,
        MarketAdapterSpec,
        LaunchpadAdapterSpec,
        MarketEvent,
        TokenEvent,
        WalletEvent,
        RiskEvent,
    )


# ---------------------------------------------------------------------------
# Adapter Capability Enum
# ---------------------------------------------------------------------------


class AdapterCapability(str, Enum):
    """Capabilities an adapter can provide."""

    # Market data capabilities
    TOKEN_EVENTS = "token_events"
    WALLET_EVENTS = "wallet_events"
    OHLCV_DATA = "ohlcv_data"
    ORDER_BOOK = "order_book"
    SOCIAL_SIGNALS = "social_signals"

    # Launchpad capabilities
    LAUNCH_DETECTION = "launch_detection"
    BONDING_CURVE = "bonding_curve"
    MIGRATION_TRACKING = "migration_tracking"
    TOP_TRADERS = "top_traders"
    HOLDER_DISTRIBUTION = "holder_distribution"

    # Risk capabilities
    HONEYPOT_DETECTION = "honeypot_detection"
    RUG_DETECTION = "rug_detection"
    LIQUIDITY_ANALYSIS = "liquidity_analysis"


# ---------------------------------------------------------------------------
# Adapter Health
# ---------------------------------------------------------------------------


@dataclass
class AdapterHealth:
    """Health status of an adapter.

    Used for monitoring adapter availability and performance.
    """

    adapter_id: str
    is_healthy: bool = True
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_success: Optional[datetime] = None
    last_error: Optional[datetime] = None

    # Performance metrics
    latency_ms: Optional[float] = None
    success_rate: float = 1.0  # 0.0 - 1.0
    requests_total: int = 0
    requests_failed: int = 0

    # Rate limit status
    rate_limited: bool = False
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[datetime] = None

    # Error context
    last_error_message: Optional[str] = None
    consecutive_failures: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "is_healthy": self.is_healthy,
            "last_check": self.last_check.isoformat(),
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_error": self.last_error.isoformat() if self.last_error else None,
            "latency_ms": self.latency_ms,
            "success_rate": self.success_rate,
            "requests_total": self.requests_total,
            "requests_failed": self.requests_failed,
            "rate_limited": self.rate_limited,
            "rate_limit_remaining": self.rate_limit_remaining,
            "rate_limit_reset": self.rate_limit_reset.isoformat() if self.rate_limit_reset else None,
            "last_error_message": self.last_error_message,
            "consecutive_failures": self.consecutive_failures,
        }


# ---------------------------------------------------------------------------
# Adapter Rate Limit
# ---------------------------------------------------------------------------


@dataclass
class AdapterRateLimit:
    """Rate limit configuration for an adapter.

    Used to prevent API abuse and handle rate limiting gracefully.
    """

    adapter_id: str

    # Limits
    requests_per_second: float = 1.0
    requests_per_minute: int = 60
    requests_per_hour: int = 1000

    # Burst handling
    burst_limit: int = 10
    burst_window_seconds: int = 1

    # Current state
    current_count: int = 0
    window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Backoff configuration
    backoff_base_seconds: float = 1.0
    backoff_max_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    current_backoff_seconds: float = 0.0

    def is_rate_limited(self) -> bool:
        """Check if currently rate limited."""
        return self.current_backoff_seconds > 0

    def reset_backoff(self) -> None:
        """Reset backoff after successful request."""
        self.current_backoff_seconds = 0.0

    def increase_backoff(self) -> float:
        """Increase backoff after rate limit hit. Returns new backoff."""
        if self.current_backoff_seconds == 0:
            self.current_backoff_seconds = self.backoff_base_seconds
        else:
            self.current_backoff_seconds = min(
                self.current_backoff_seconds * self.backoff_multiplier,
                self.backoff_max_seconds,
            )
        return self.current_backoff_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "requests_per_second": self.requests_per_second,
            "requests_per_minute": self.requests_per_minute,
            "requests_per_hour": self.requests_per_hour,
            "burst_limit": self.burst_limit,
            "burst_window_seconds": self.burst_window_seconds,
            "current_count": self.current_count,
            "window_start": self.window_start.isoformat(),
            "backoff_base_seconds": self.backoff_base_seconds,
            "backoff_max_seconds": self.backoff_max_seconds,
            "backoff_multiplier": self.backoff_multiplier,
            "current_backoff_seconds": self.current_backoff_seconds,
            "is_rate_limited": self.is_rate_limited(),
        }


# ---------------------------------------------------------------------------
# Adapter Error
# ---------------------------------------------------------------------------


class AdapterErrorCode(str, Enum):
    """Error codes for adapter operations."""

    RATE_LIMITED = "rate_limited"
    AUTHENTICATION_FAILED = "authentication_failed"
    NETWORK_ERROR = "network_error"
    PARSE_ERROR = "parse_error"
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    INTERNAL_ERROR = "internal_error"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    EXECUTION_BLOCKED = "execution_blocked"  # WSP 97: Execution attempted in Phase 0


@dataclass
class AdapterError:
    """Error from adapter operation.

    Structured error response for adapter failures.
    """

    adapter_id: str
    error_code: AdapterErrorCode
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Context
    operation: Optional[str] = None
    request_id: Optional[str] = None
    raw_error: Optional[str] = None

    # Retry guidance
    is_retryable: bool = True
    retry_after_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "error_code": self.error_code.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation,
            "request_id": self.request_id,
            "raw_error": self.raw_error,
            "is_retryable": self.is_retryable,
            "retry_after_seconds": self.retry_after_seconds,
        }


# ---------------------------------------------------------------------------
# Adapter Result
# ---------------------------------------------------------------------------

T = TypeVar("T")


@dataclass
class AdapterResult:
    """Result wrapper for adapter operations.

    Provides consistent success/error handling across all adapters.
    """

    adapter_id: str
    operation: str
    success: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Result data (on success)
    data: Optional[Any] = None
    events: List[Any] = field(default_factory=list)  # Normalized events

    # Error info (on failure)
    error: Optional[AdapterError] = None

    # Metadata
    latency_ms: Optional[float] = None
    request_id: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None

    # Truth boundary (Phase 0)
    is_simulation: bool = True  # MUST be True in Phase 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "operation": self.operation,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "events": [e.to_dict() if hasattr(e, "to_dict") else e for e in self.events],
            "error": self.error.to_dict() if self.error else None,
            "latency_ms": self.latency_ms,
            "request_id": self.request_id,
            "is_simulation": self.is_simulation,
        }


# ---------------------------------------------------------------------------
# Adapter Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class MarketAdapter(Protocol):
    """Protocol for market data adapters.

    Adapters must implement this protocol to provide market data.
    All methods return simulation data only in Phase 0.
    """

    @property
    def adapter_id(self) -> str:
        """Unique adapter identifier."""
        ...

    @property
    def spec(self) -> MarketAdapterSpec:
        """Adapter specification."""
        ...

    def get_capabilities(self) -> List[AdapterCapability]:
        """Return supported capabilities."""
        ...

    def get_health(self) -> AdapterHealth:
        """Return current health status."""
        ...

    async def fetch_market_data(
        self,
        symbol: str,
        **kwargs: Any,
    ) -> AdapterResult:
        """Fetch market data for a symbol."""
        ...

    async def fetch_token_events(
        self,
        token_address: str,
        **kwargs: Any,
    ) -> AdapterResult:
        """Fetch token lifecycle events."""
        ...

    async def fetch_wallet_events(
        self,
        wallet_address: str,
        **kwargs: Any,
    ) -> AdapterResult:
        """Fetch wallet activity events."""
        ...


@runtime_checkable
class LaunchpadAdapter(Protocol):
    """Protocol for launchpad adapters.

    Adapters must implement this protocol to provide launchpad data.
    All methods return simulation data only in Phase 0.
    """

    @property
    def adapter_id(self) -> str:
        """Unique adapter identifier."""
        ...

    @property
    def spec(self) -> LaunchpadAdapterSpec:
        """Adapter specification."""
        ...

    def get_capabilities(self) -> List[AdapterCapability]:
        """Return supported capabilities."""
        ...

    def get_health(self) -> AdapterHealth:
        """Return current health status."""
        ...

    async def fetch_recent_launches(
        self,
        limit: int = 100,
        **kwargs: Any,
    ) -> AdapterResult:
        """Fetch recent token launches."""
        ...

    async def fetch_bonding_curve(
        self,
        token_address: str,
        **kwargs: Any,
    ) -> AdapterResult:
        """Fetch bonding curve data for a token."""
        ...

    async def fetch_top_traders(
        self,
        token_address: str,
        **kwargs: Any,
    ) -> AdapterResult:
        """Fetch top traders for a token."""
        ...

    async def fetch_holder_distribution(
        self,
        token_address: str,
        **kwargs: Any,
    ) -> AdapterResult:
        """Fetch holder distribution for a token."""
        ...


# ---------------------------------------------------------------------------
# Adapter Registry
# ---------------------------------------------------------------------------


class AdapterRegistry:
    """Registry for market and launchpad adapters.

    Provides central management of all adapters with health monitoring.
    """

    def __init__(self) -> None:
        self._market_adapters: Dict[str, MarketAdapter] = {}
        self._launchpad_adapters: Dict[str, LaunchpadAdapter] = {}
        self._health_cache: Dict[str, AdapterHealth] = {}
        self._rate_limits: Dict[str, AdapterRateLimit] = {}

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def register_market_adapter(self, adapter: MarketAdapter) -> None:
        """Register a market adapter."""
        adapter_id = adapter.adapter_id
        if adapter_id in self._market_adapters:
            raise ValueError(f"Market adapter '{adapter_id}' already registered")
        self._market_adapters[adapter_id] = adapter
        self._health_cache[adapter_id] = AdapterHealth(adapter_id=adapter_id)

    def register_launchpad_adapter(self, adapter: LaunchpadAdapter) -> None:
        """Register a launchpad adapter."""
        adapter_id = adapter.adapter_id
        if adapter_id in self._launchpad_adapters:
            raise ValueError(f"Launchpad adapter '{adapter_id}' already registered")
        self._launchpad_adapters[adapter_id] = adapter
        self._health_cache[adapter_id] = AdapterHealth(adapter_id=adapter_id)

    def unregister_adapter(self, adapter_id: str) -> bool:
        """Unregister an adapter. Returns True if found and removed."""
        removed = False
        if adapter_id in self._market_adapters:
            del self._market_adapters[adapter_id]
            removed = True
        if adapter_id in self._launchpad_adapters:
            del self._launchpad_adapters[adapter_id]
            removed = True
        if adapter_id in self._health_cache:
            del self._health_cache[adapter_id]
        if adapter_id in self._rate_limits:
            del self._rate_limits[adapter_id]
        return removed

    # -------------------------------------------------------------------------
    # Lookup
    # -------------------------------------------------------------------------

    def get_market_adapter(self, adapter_id: str) -> Optional[MarketAdapter]:
        """Get a market adapter by ID."""
        return self._market_adapters.get(adapter_id)

    def get_launchpad_adapter(self, adapter_id: str) -> Optional[LaunchpadAdapter]:
        """Get a launchpad adapter by ID."""
        return self._launchpad_adapters.get(adapter_id)

    def list_market_adapters(self) -> List[str]:
        """List all registered market adapter IDs."""
        return list(self._market_adapters.keys())

    def list_launchpad_adapters(self) -> List[str]:
        """List all registered launchpad adapter IDs."""
        return list(self._launchpad_adapters.keys())

    def list_all_adapters(self) -> Dict[str, List[str]]:
        """List all registered adapters by type."""
        return {
            "market": self.list_market_adapters(),
            "launchpad": self.list_launchpad_adapters(),
        }

    # -------------------------------------------------------------------------
    # Capability Lookup
    # -------------------------------------------------------------------------

    def find_adapters_with_capability(
        self,
        capability: AdapterCapability,
    ) -> List[str]:
        """Find all adapters supporting a capability."""
        result = []
        for adapter_id, adapter in self._market_adapters.items():
            if capability in adapter.get_capabilities():
                result.append(adapter_id)
        for adapter_id, adapter in self._launchpad_adapters.items():
            if capability in adapter.get_capabilities():
                result.append(adapter_id)
        return result

    # -------------------------------------------------------------------------
    # Health Management
    # -------------------------------------------------------------------------

    def get_adapter_health(self, adapter_id: str) -> Optional[AdapterHealth]:
        """Get health status for an adapter."""
        return self._health_cache.get(adapter_id)

    def update_adapter_health(self, health: AdapterHealth) -> None:
        """Update health status for an adapter."""
        self._health_cache[health.adapter_id] = health

    def get_healthy_adapters(self) -> List[str]:
        """Get list of healthy adapter IDs."""
        return [
            adapter_id
            for adapter_id, health in self._health_cache.items()
            if health.is_healthy
        ]

    def get_unhealthy_adapters(self) -> List[str]:
        """Get list of unhealthy adapter IDs."""
        return [
            adapter_id
            for adapter_id, health in self._health_cache.items()
            if not health.is_healthy
        ]

    # -------------------------------------------------------------------------
    # Rate Limit Management
    # -------------------------------------------------------------------------

    def set_rate_limit(self, rate_limit: AdapterRateLimit) -> None:
        """Set rate limit configuration for an adapter."""
        self._rate_limits[rate_limit.adapter_id] = rate_limit

    def get_rate_limit(self, adapter_id: str) -> Optional[AdapterRateLimit]:
        """Get rate limit configuration for an adapter."""
        return self._rate_limits.get(adapter_id)

    def is_rate_limited(self, adapter_id: str) -> bool:
        """Check if an adapter is currently rate limited."""
        rate_limit = self._rate_limits.get(adapter_id)
        if rate_limit is None:
            return False
        return rate_limit.is_rate_limited()

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------

    def get_registry_summary(self) -> Dict[str, Any]:
        """Get summary of all registered adapters."""
        return {
            "total_adapters": len(self._market_adapters) + len(self._launchpad_adapters),
            "market_adapters": len(self._market_adapters),
            "launchpad_adapters": len(self._launchpad_adapters),
            "healthy_adapters": len(self.get_healthy_adapters()),
            "unhealthy_adapters": len(self.get_unhealthy_adapters()),
            "rate_limited_adapters": sum(
                1 for adapter_id in self._rate_limits if self.is_rate_limited(adapter_id)
            ),
            "adapters": self.list_all_adapters(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry state."""
        return {
            "summary": self.get_registry_summary(),
            "health": {
                adapter_id: health.to_dict()
                for adapter_id, health in self._health_cache.items()
            },
            "rate_limits": {
                adapter_id: limit.to_dict()
                for adapter_id, limit in self._rate_limits.items()
            },
        }


# ---------------------------------------------------------------------------
# Default Registry Instance
# ---------------------------------------------------------------------------

# Singleton registry for Trade FoundUp
_default_registry: Optional[AdapterRegistry] = None


def get_adapter_registry() -> AdapterRegistry:
    """Get the default adapter registry (singleton)."""
    global _default_registry
    if _default_registry is None:
        _default_registry = AdapterRegistry()
    return _default_registry


def reset_adapter_registry() -> None:
    """Reset the default adapter registry (for testing)."""
    global _default_registry
    _default_registry = None
