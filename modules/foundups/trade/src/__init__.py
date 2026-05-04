"""Trade FoundUp - Autonomous Trading Intelligence

Autonomous trading intelligence and execution FoundUp.
Market-adapter driven, chain-agnostic.

WSP References:
- WSP 97: Truth Boundaries (no false execution claims)
- WSP 103: FoundUp Federation Protocol
- WSP 104: FoundUp Route Namespace

Phase 0 Status:
- no_money_mode: True
- dry_run_mode: True
- real_execution_performed: False
"""

# Contracts (core data types)
from .contracts import (
    AdapterStatus,
    MarketAdapterSpec,
    LaunchpadAdapterSpec,
    MarketEvent,
    TokenEvent,
    WalletEvent,
    SocialEvent,
    RiskEvent,
    TradeSignal,
    ExitSignal,
    ProofMetric,
    SimulationResult,
    ExecutionGuardPolicy,
    TruthFields,
    UnsupportedOperationError,
    DEFAULT_EXECUTION_GUARD,
    DEFAULT_TRUTH_FIELDS,
)

# Adapters (abstraction layer)
from .adapters import (
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

# Events (normalization layer)
from .events import (
    generate_event_id,
    generate_deterministic_event_id,
    create_market_event,
    create_price_update_event,
    create_volume_spike_event,
    create_liquidity_change_event,
    create_token_event,
    create_token_created_event,
    create_migration_event,
    create_wallet_event,
    create_buy_event,
    create_sell_event,
    hash_wallet_address,
    create_social_event,
    create_mention_event,
    create_sentiment_shift_event,
    create_risk_event,
    create_honeypot_detection_event,
    create_rug_risk_event,
    ValidationResult,
    validate_market_event,
    validate_token_event,
    validate_wallet_event,
    validate_social_event,
    validate_risk_event,
    validate_event,
)

# Guards (simulation enforcement)
from .guards import (
    NoMoneyModeViolation,
    WalletSigningViolation,
    OrderPlacementViolation,
    TruthBoundaryViolation,
    ExecutionGuardViolation,
    assert_no_money_mode,
    assert_no_wallet_signing,
    assert_no_order_placement,
    assert_no_real_trades,
    assert_no_capital_deployment,
    assert_no_private_key_access,
    PolicyValidationResult,
    validate_execution_guard_policy,
    validate_truth_fields,
    SimulationGuard,
    create_phase0_guard,
    is_phase0_compliant,
    get_phase0_violations,
)

__all__ = [
    # Contracts - Enums
    "AdapterStatus",
    # Contracts - Adapter specs
    "MarketAdapterSpec",
    "LaunchpadAdapterSpec",
    # Contracts - Event schemas
    "MarketEvent",
    "TokenEvent",
    "WalletEvent",
    "SocialEvent",
    "RiskEvent",
    # Contracts - Signal schemas
    "TradeSignal",
    "ExitSignal",
    # Contracts - Proof schemas
    "ProofMetric",
    "SimulationResult",
    # Contracts - Guard
    "ExecutionGuardPolicy",
    "TruthFields",
    "UnsupportedOperationError",
    "DEFAULT_EXECUTION_GUARD",
    "DEFAULT_TRUTH_FIELDS",
    # Adapters - Types
    "AdapterCapability",
    "AdapterHealth",
    "AdapterRateLimit",
    "AdapterErrorCode",
    "AdapterError",
    "AdapterResult",
    # Adapters - Protocols
    "MarketAdapter",
    "LaunchpadAdapter",
    # Adapters - Registry
    "AdapterRegistry",
    "get_adapter_registry",
    "reset_adapter_registry",
    # Events - ID generation
    "generate_event_id",
    "generate_deterministic_event_id",
    # Events - Market helpers
    "create_market_event",
    "create_price_update_event",
    "create_volume_spike_event",
    "create_liquidity_change_event",
    # Events - Token helpers
    "create_token_event",
    "create_token_created_event",
    "create_migration_event",
    # Events - Wallet helpers
    "create_wallet_event",
    "create_buy_event",
    "create_sell_event",
    "hash_wallet_address",
    # Events - Social helpers
    "create_social_event",
    "create_mention_event",
    "create_sentiment_shift_event",
    # Events - Risk helpers
    "create_risk_event",
    "create_honeypot_detection_event",
    "create_rug_risk_event",
    # Events - Validation
    "ValidationResult",
    "validate_market_event",
    "validate_token_event",
    "validate_wallet_event",
    "validate_social_event",
    "validate_risk_event",
    "validate_event",
    # Guards - Exceptions
    "NoMoneyModeViolation",
    "WalletSigningViolation",
    "OrderPlacementViolation",
    "TruthBoundaryViolation",
    "ExecutionGuardViolation",
    # Guards - Assertions
    "assert_no_money_mode",
    "assert_no_wallet_signing",
    "assert_no_order_placement",
    "assert_no_real_trades",
    "assert_no_capital_deployment",
    "assert_no_private_key_access",
    # Guards - Policy validation
    "PolicyValidationResult",
    "validate_execution_guard_policy",
    "validate_truth_fields",
    # Guards - Context manager
    "SimulationGuard",
    "create_phase0_guard",
    "is_phase0_compliant",
    "get_phase0_violations",
]

__version__ = "0.2.0"
