"""Chain-Agnostic Token Factory Adapter for FoundUps Agent Market.

Provides a unified interface for token deployment across multiple chains
without vendor lock-in. Implements the TokenFactoryAdapter contract.

WSP References:
- WSP 11: Implements TokenFactoryAdapter interface contract
- WSP 30: Chain-agnostic design pattern
- WSP 72: Module independence (no direct chain dependencies)

The bundled backend is in-memory simulation. Other chain types require an
explicitly registered, connected backend; enum membership is not implementation.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .exceptions import ValidationError
from .interfaces import TokenFactoryAdapter
from .models import Foundup, TokenTerms

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_address(prefix: str, seed: str) -> str:
    """Generate a deterministic mock address from seed."""
    hash_val = hashlib.sha256(seed.encode()).hexdigest()[:40]
    return f"{prefix}_{hash_val}"


class ChainType(str, Enum):
    """Supported blockchain types."""

    MOCK = "mock"
    HEDERA = "hedera"
    EVM = "evm"
    SOLANA = "solana"  # Future


@dataclass
class TokenDeploymentResult:
    """Result of a token deployment operation."""

    success: bool
    token_address: Optional[str] = None
    chain_type: ChainType = ChainType.MOCK
    transaction_id: Optional[str] = None
    explorer_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VestingConfig:
    """Vesting configuration for token distribution."""

    start_time: datetime
    cliff_duration_days: int = 0
    vesting_duration_days: int = 365
    initial_unlock_percent: float = 0.0
    beneficiaries: Dict[str, float] = field(default_factory=dict)


class ChainBackend(ABC):
    """Abstract interface for chain-specific token operations."""

    @property
    @abstractmethod
    def chain_type(self) -> ChainType:
        """Return the chain type this backend handles."""
        pass

    @abstractmethod
    def deploy_token(
        self,
        name: str,
        symbol: str,
        max_supply: int,
        treasury_account: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TokenDeploymentResult:
        """Deploy a new token on this chain."""
        pass

    @abstractmethod
    def configure_vesting(
        self,
        token_address: str,
        config: VestingConfig,
    ) -> bool:
        """Configure vesting for a deployed token."""
        pass

    @abstractmethod
    def get_treasury_balance(self, token_address: str) -> int:
        """Get treasury balance for a token."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if backend is connected and operational."""
        pass


class MockChainBackend(ChainBackend):
    """In-memory mock chain backend for testing."""

    def __init__(self) -> None:
        self._tokens: Dict[str, Dict[str, Any]] = {}
        self._vesting: Dict[str, VestingConfig] = {}
        self._balances: Dict[str, int] = {}

    @property
    def chain_type(self) -> ChainType:
        return ChainType.MOCK

    def deploy_token(
        self,
        name: str,
        symbol: str,
        max_supply: int,
        treasury_account: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TokenDeploymentResult:
        token_address = _generate_address("mock_token", f"{symbol}_{treasury_account}")
        tx_id = f"mock_tx_{uuid.uuid4().hex[:12]}"

        self._tokens[token_address] = {
            "name": name,
            "symbol": symbol,
            "max_supply": max_supply,
            "treasury_account": treasury_account,
            "metadata": metadata or {},
            "deployed_at": _utc_now().isoformat(),
        }
        self._balances[token_address] = max_supply

        logger.info(
            "[MOCK-CHAIN] Token deployed: %s (%s) -> %s",
            name,
            symbol,
            token_address,
        )

        return TokenDeploymentResult(
            success=True,
            token_address=token_address,
            chain_type=ChainType.MOCK,
            transaction_id=tx_id,
            explorer_url=None,
            metadata={"mock": True},
        )

    def configure_vesting(
        self,
        token_address: str,
        config: VestingConfig,
    ) -> bool:
        if token_address not in self._tokens:
            logger.warning("[MOCK-CHAIN] Token not found: %s", token_address)
            return False
        self._vesting[token_address] = config
        logger.info("[MOCK-CHAIN] Vesting configured for: %s", token_address)
        return True

    def get_treasury_balance(self, token_address: str) -> int:
        return self._balances.get(token_address, 0)

    def is_connected(self) -> bool:
        return True


class ChainAgnosticTokenFactory(TokenFactoryAdapter):
    """Chain-agnostic token factory implementation.

    Delegates to chain-specific backends while maintaining
    a unified interface. Supports multiple chains simultaneously.

    Example:
        factory = ChainAgnosticTokenFactory()
        factory.register_backend(HederaBackend())
        factory.register_backend(EVMBackend())

        # Deploy on default (mock) chain
        address = factory.deploy_token(foundup, terms)

        # Deploy on specific chain
        terms.chain_hint = "hedera"
        address = factory.deploy_token(foundup, terms)
    """

    def __init__(self, default_chain: ChainType = ChainType.MOCK) -> None:
        """Initialize token factory.

        Args:
            default_chain: Used only when chain_hint is None. MOCK preserves
                the local PoC simulation; unavailable defaults never fall back.
        """
        self._backends: Dict[ChainType, ChainBackend] = {}
        self._default_chain = default_chain
        self._deployments: Dict[str, TokenDeploymentResult] = {}

        # Always register mock backend
        self.register_backend(MockChainBackend())
        logger.info(
            "[TOKEN-FACTORY] Initialized | default_chain=%s",
            default_chain.value,
        )

    def register_backend(self, backend: ChainBackend) -> None:
        """Register a chain backend.

        Args:
            backend: ChainBackend implementation to register.
        """
        chain_type = backend.chain_type
        if not isinstance(chain_type, ChainType):
            raise ValidationError("Token backend chain type must be a ChainType")
        self._backends[chain_type] = backend
        logger.info(
            "[TOKEN-FACTORY] Backend registered: %s",
            chain_type.value,
        )

    def _get_backend(
        self, chain_hint: Optional[str] = None
    ) -> tuple[ChainType, ChainBackend]:
        """Resolve exactly one chain; reject invalid or unavailable selections."""
        chain_type = self._default_chain
        if chain_hint is not None:
            if not isinstance(chain_hint, str):
                raise ValidationError("Token chain hint must be a chain name or None")
            try:
                chain_type = ChainType(chain_hint.strip().lower())
            except ValueError as exc:
                raise ValidationError("Unsupported token chain hint") from exc

        backend = self._backends.get(chain_type)
        if backend is None:
            raise ValidationError(f"No token backend registered for chain: {chain_type.value}")
        if backend.chain_type is not chain_type:
            raise ValidationError("Token backend chain identity mismatch")
        try:
            connected = backend.is_connected()
        except Exception as exc:
            raise ValidationError(
                f"Could not check token backend connectivity: {chain_type.value}"
            ) from exc
        if not connected:
            raise ValidationError(f"Token backend is disconnected: {chain_type.value}")
        if backend.chain_type is not chain_type:
            raise ValidationError("Token backend chain identity mismatch")
        return chain_type, backend

    def deploy_token(self, foundup: Foundup, terms: TokenTerms) -> str:
        """Deploy a token for a FoundUp.

        Implements TokenFactoryAdapter.deploy_token interface.
        Chain selection is determined by terms.chain_hint.

        Args:
            foundup: FoundUp to deploy token for.
            terms: Token terms including chain hint.

        Returns:
            Token address string.

        Raises:
            ValidationError: If the selected backend is invalid, unavailable,
                or reports a different chain. No fallback is attempted.
            RuntimeError: If deployment fails.
        """
        selected_chain, backend = self._get_backend(terms.chain_hint)

        result = backend.deploy_token(
            name=terms.token_name,
            symbol=terms.token_symbol,
            max_supply=terms.max_supply,
            treasury_account=terms.treasury_account,
            metadata={
                "foundup_id": foundup.foundup_id,
                "owner_id": foundup.owner_id,
            },
        )

        if not result.success:
            raise RuntimeError(f"Token deployment failed: {result.error}")
        if result.chain_type is not selected_chain:
            raise ValidationError("Token deployment result chain mismatch")

        # Track deployment
        self._deployments[foundup.foundup_id] = result

        logger.info(
            "[TOKEN-FACTORY] Token deployed | foundup=%s chain=%s address=%s",
            foundup.foundup_id,
            result.chain_type.value,
            result.token_address,
        )

        return result.token_address or ""

    def configure_vesting(self, token_address: str, terms: TokenTerms) -> None:
        """Configure vesting for a deployed token.

        Implements TokenFactoryAdapter.configure_vesting interface.

        Args:
            token_address: Address of deployed token.
            terms: Token terms with vesting policy.

        Raises:
            ValidationError: If the selected backend is invalid or unavailable.
        """
        _selected_chain, backend = self._get_backend(terms.chain_hint)

        vesting_policy = terms.vesting_policy or {}
        config = VestingConfig(
            start_time=_utc_now(),
            cliff_duration_days=int(vesting_policy.get("cliff_days", 0)),
            vesting_duration_days=int(vesting_policy.get("vesting_days", 365)),
            initial_unlock_percent=float(vesting_policy.get("initial_unlock", 0)),
        )

        success = backend.configure_vesting(token_address, config)
        if not success:
            logger.warning(
                "[TOKEN-FACTORY] Vesting configuration failed for: %s",
                token_address,
            )

    def get_treasury_account(self, foundup_id: str) -> str:
        """Get treasury account for a FoundUp.

        Implements TokenFactoryAdapter.get_treasury_account interface.

        Args:
            foundup_id: FoundUp ID to get treasury for.

        Returns:
            Treasury account address.
        """
        deployment = self._deployments.get(foundup_id)
        if deployment and deployment.token_address:
            return f"treasury_{deployment.token_address[:16]}"
        return f"treasury_{foundup_id}"

    def get_deployment_status(self, foundup_id: str) -> Optional[TokenDeploymentResult]:
        """Get deployment status for a FoundUp.

        Args:
            foundup_id: FoundUp ID to check.

        Returns:
            TokenDeploymentResult if deployed, None otherwise.
        """
        return self._deployments.get(foundup_id)

    def list_supported_chains(self) -> List[str]:
        """List supported chain types.

        Returns:
            List of chain type strings with connection status.
        """
        return [
            f"{chain.value}:{'connected' if backend.is_connected() else 'disconnected'}"
            for chain, backend in self._backends.items()
        ]


# Keep stub for backwards compatibility
class TokenFactoryStub(TokenFactoryAdapter):
    """Stub implementation for testing (deprecated, use ChainAgnosticTokenFactory)."""

    pass


# Default factory instance
_default_factory: Optional[ChainAgnosticTokenFactory] = None


def get_token_factory() -> ChainAgnosticTokenFactory:
    """Get or create the default token factory instance."""
    global _default_factory
    if _default_factory is None:
        _default_factory = ChainAgnosticTokenFactory()
    return _default_factory
