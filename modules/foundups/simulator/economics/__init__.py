"""Token Economics module for FoundUps simulator.

Implements WSP 26 + TOKENOMICS.md complete economic model:

BTC RESERVE (Hotel California):
- BTC flows IN, never OUT
- Sources: Subscriptions, demurrage, exit fees, trading fees
- BTC → UPS capacity (more BTC = stronger currency)

TWO TOKEN TYPES:
- UPS = Universal fuel (demurrage, lottery, cross-FoundUp)
- F_i = FoundUp-specific (21M cap, Bitcoin-like, earned by agents)

TWO F_i SOURCES (different exit fees):
- MINED F_i (agent work) → 11% exit fee (discourages extraction)
- STAKED F_i (UPS investment) → 5% exit fee (value preservation)

BIO-DECAY (ICE/LIQUID/VAPOR):
- LIQUID (wallet): Decays 0.5%-5%/month (Michaelis-Menten kinetics)
- ICE (staked): No decay, earns yield
- VAPOR (exit): 15% fee, BTC locked forever

F_i ORDER BOOK:
- Buy/sell F_i when supply scarce
- Trading fees → BTC Reserve

Pool Structure (WSP 26 Section 6.3-6.4):
- Stakeholders 80%: Un(60%) + Dao(16%) + Du(4%)
- Network 20%: Network(16% drip) + Fund(4% held)

Subscription Tiers (WSP 26 Section 4.9):
- Free: 1x base, 1 cycle/month
- Spark ($2.95): 2x base, 2 cycles = 4x effective
- Explorer ($9.95): 3x base, 3 cycles = 9x effective
- Builder ($19.95): 5x base, 5 cycles = 25x effective
- Founder ($49.95): 10x base, 30 cycles = ~300x effective

Key Classes:
- BTCReserve: The "hole in the bucket" for Bitcoin
- DemurrageEngine: Bio-decay for LIQUID UPS
- FiOrderBook: Buy/sell F_i tokens
- TokenEconomicsEngine: Human vs Agent boundary enforcement
- PoolDistributor: Epoch rewards per Un/Dao/Du structure
"""

from .token_economics import (
    TokenType,
    FeeConfig,
    OperationalProfitPolicy,
    OperationalProfitResult,
    SubscriptionTier,
    SubscriptionConfig,
    SUBSCRIPTION_TIERS,
    AgentExecutionWallet,
    HumanUPSAccount,
    StakedPosition,
    FoundUpTokenPool,
    TokenEconomicsEngine,
    # Adoption curve mathematics (diffusion of innovation)
    sigmoid,
    adoption_curve,
)

from .pool_distribution import (
    ParticipantType,
    ActivityLevel,
    ComputeMetrics,
    StakerPosition,
    Participant,
    EpochDistribution,
    PoolDistributor,
    FoundUpTokenDistributor,
    POOL_PERCENTAGES,
    ACTIVITY_SHARES,
    POOL_ACCESS,
    COMPUTE_TIER_WEIGHTS,
    STAKER_TIER_THRESHOLDS,
    STAKER_CAP_GENESIS,
    STAKER_CAP_EARLY,
    STAKER_MIN_BTC,
    STAKER_RECOMMENDED_BTC,
    # Weighted stake allocation (BTCStakerPool mechanics)
    STAKE_WEIGHT_EXPONENT,
    btc_stake_weight,
    calculate_weighted_share,
    calculate_total_weighted_stake,
    distribute_weighted_staker_pool,
)

from .dilution_scenario import (
    AdoptionModel,
    AdoptionConfig,
    DilutionSnapshot,
    DilutionScenario,
    run_dilution_scenario,
    compare_adoption_models,
    analyze_minimum_viable_pool,  # CABR/PoB: uses target_ratio not target_roi
)

from .staker_viability import (
    StakerTierConfig,
    StakerAnalysis,
    calculate_staker_distributions,
    find_optimal_staker_count,
    run_staker_matrix,
)

from .channel_partner_pool import (
    CHANNEL_PARTNER_CAP,
    CHANNEL_PARTNER_PASSIVE_SHARE,
    RegistryState,
    ChannelPartner,
    GenesisClosureEvent,
    ChannelPartnerDistribution,
    ChannelPartnerPool,
    get_channel_partner_pool,
    reset_channel_partner_pool,
)

from .fee_simulation import (
    FeeScenario,
    SimulationResult,
    run_scenario,
    compare_scenarios,
    print_comparison,
)

from .btc_reserve import (
    BTCSourceType,
    PaymentCrypto,
    CryptoRates,
    BTCInflow,
    BTCReserve,
    get_btc_reserve,
    reset_btc_reserve,
)

from .fi_orderbook import (
    OrderSide,
    OrderStatus,
    EntryProtectionConfig,
    Order,
    Trade,
    FiOrderBook,
    OrderBookManager,
)

from .demurrage import (
    TokenState,
    ActivityTier,
    ACTIVITY_TIER_MULTIPLIERS,
    ACTIVITY_TIER_THRESHOLDS,
    FoundUpType,
    FOUNDUP_TYPE_RATIOS,
    NotificationType,
    DecayNotification,
    DecayConfig,
    WalletState,
    DemurrageEngine,
    DECAY_RELIEF_ACTIVITIES,
    get_relief_for_activity,
)

from .circuit_breaker import (
    BreakerState,
    BreakerTrigger,
    BreakerConfig,
    QueuedExit,
    CircuitBreaker,
    get_circuit_breaker,
    reset_circuit_breaker,
)

from .bonding_curve import (
    BondingCurveConfig,
    FiBondingCurve,
    BondingCurveManager,
)

from .rage_quit import (
    FailureReason,
    FoundUpHealth,
    RageQuitConfig,
    RageQuitResult,
    RageQuitAdapter,
    get_rage_quit_adapter,
    reset_rage_quit_adapter,
)

from .emergency_reserve import (
    ReserveSourceType,
    DeploymentReason,
    ReserveDeposit,
    ReserveDeployment,
    EmergencyReserveConfig,
    EmergencyReserve,
    get_emergency_reserve,
    reset_emergency_reserve,
)

from .investor_staking import (
    # Bonding curve mathematics (Bitclout-inspired)
    bonding_price,
    bonding_cost,
    bonding_tokens_for_btc,
    calculate_investor_return,
    # Investor types
    InvestorTier,
    InvestorPosition,
    InvestorPool,
    get_investor_pool,
    reset_investor_pool,
    # Demo function
    demonstrate_10x_100x_returns,
)

from .investor_liability import (
    InvestorCohort,
    BuyoutPolicy,
    EscrowSchedule,
    LiabilitySnapshot,
    FundingSources,
    CoverageCovenants,
    CoverageResult,
    InvestorLiabilityEngine,
    BuyoutCoverageEngine,
)
from .underwriting_scenarios import (
    ContractTerms,
    FoundupLane,
    PoolMember,
    ScenarioConfig,
    YearProjection,
    UnderwritingOutcome,
    stake_weight,
    simulate_underwriting,
    default_scenarios,
    run_underwriting_matrix,
)

from .fi_rating import (
    ColorTemperature,
    COLOR_GRADIENT,
    interpolate_color,
    FounderTrackRecord,
    FiRating,
    AgentProfile,
    FiRatingEngine,
    get_rating_engine,
    reset_rating_engine,
)

from .dynamic_exit_friction import (
    FoundUpTier,
    MATURITY_EXIT_FEES,
    MIN_EXIT_FEE,
    ActivityMetrics,
    ExitFeeResult,
    calculate_stake_discount,
    calculate_vesting_bonus,
    calculate_activity_modifier,
    calculate_dynamic_exit_fee,
    DynamicExitEngine,
    get_dynamic_exit_engine,
    reset_dynamic_exit_engine,
)

from .epoch_ledger import (
    EpochEntry,
    MerkleProof,
    EpochLedger,
    get_epoch_ledger,
    reset_epoch_ledgers,
)

from .btc_anchor_connector import (
    AnchorMode,
    AnchorStatus,
    AnchorRecord,
    BTCAnchorConnector,
    get_anchor_connector,
    reset_anchor_connector,
    LAYER_D_ENABLED,
)

from .participation_sentinel import (
    AlertType,
    RecommendedAction,
    SentinelAlert,
    ParticipantProfile,
    ParticipationSentinel,
    get_participation_sentinel,
    reset_participation_sentinel,
)

from .allocation_engine import (
    AllocationStrategy,
    AllocationPath,
    AllocationTarget,
    AllocationResult,
    AllocationBatch,
    AllocationEngine,
    get_allocation_engine,
    reset_allocation_engine,
)
from .cabr_flow_router import (
    CABRFlowInputs,
    CABRFlowResult,
    DEFAULT_RELEASE_RATE,
    route_cabr_ups_flow,
)

from .pavs_audit import (
    PAVSAuditor,
    PAVSAuditReport,
    AuditCheck,
    AuditSection,
    AuditStatus,
    run_audit,
)

from .ai_parameter_optimizer import (
    OptimizationObjective,
    OptimizationResult,
    ParameterBounds,
    TUNABLE_PARAMETERS,
    OptimizerConfig,
    AIParameterOptimizer,
)

# Subscription Tiers (Stake-to-Spend Model - 2026-02-17)
from .subscription_tiers import (
    SubscriptionTier as SubTier,  # Alias to avoid collision with token_economics.SubscriptionTier
    TIERS as SUBSCRIPTION_TIER_CONFIGS,
    AGENT_COSTS as SUBSCRIPTION_AGENT_COSTS,
    TOPUP_OPTIONS,
    calculate_monthly_capacity,
    model_usage_pattern,
    recommend_tier,
    project_subscription_revenue,
)

# Agent Compute Costs (Real Infrastructure Pricing - 2026-02-17)
from .agent_compute_costs import (
    TaskComplexity,
    InfrastructureCost,
    AGENT_INFRASTRUCTURE_COSTS,
    UPsPricing,
    calculate_ups_pricing,
    FoundUpStake,
    UserAccount,
    simulate_user_journey,
    analyze_openclaw_infrastructure,
)

# Ten Year Projection (Combined Revenue Model - 2026-02-17)
from .ten_year_projection import (
    GROWTH_SCENARIOS,
    SUBSCRIBER_GROWTH_SCENARIOS,
    YearSnapshot,
    TenYearProjection,
    interpolate_growth,
    interpolate_subscribers,
    calculate_subscription_revenue,
    generate_projection,
    generate_all_projections,
    export_for_animation,
)

__all__ = [
    # Token economics (Human vs Agent)
    "TokenType",
    "FeeConfig",
    "OperationalProfitPolicy",
    "OperationalProfitResult",
    "AgentExecutionWallet",
    "HumanUPSAccount",
    "StakedPosition",
    "FoundUpTokenPool",
    "TokenEconomicsEngine",
    # Adoption curve (diffusion of innovation - S-curve)
    "sigmoid",
    "adoption_curve",
    # Subscription tiers (WSP 26 Section 4.9)
    "SubscriptionTier",
    "SubscriptionConfig",
    "SUBSCRIPTION_TIERS",
    # Pool distribution (Un/Dao/Du)
    "ParticipantType",
    "ActivityLevel",
    "ComputeMetrics",
    "StakerPosition",
    "Participant",
    "EpochDistribution",
    "PoolDistributor",
    "FoundUpTokenDistributor",
    "POOL_PERCENTAGES",
    "ACTIVITY_SHARES",
    "POOL_ACCESS",
    "COMPUTE_TIER_WEIGHTS",
    "STAKER_TIER_THRESHOLDS",
    "STAKER_CAP_GENESIS",
    "STAKER_CAP_EARLY",
    "STAKER_MIN_BTC",
    "STAKER_RECOMMENDED_BTC",
    # Weighted stake allocation (BTCStakerPool mechanics)
    "STAKE_WEIGHT_EXPONENT",
    "btc_stake_weight",
    "calculate_weighted_share",
    "calculate_total_weighted_stake",
    "distribute_weighted_staker_pool",
    # Dilution analysis (012-confirmed 2026-02-14)
    "AdoptionModel",
    "AdoptionConfig",
    "DilutionSnapshot",
    "DilutionScenario",
    "run_dilution_scenario",
    "compare_adoption_models",
    "analyze_minimum_viable_pool",
    # Staker viability (Du pool = BTC stakers only)
    "StakerTierConfig",
    "StakerAnalysis",
    "calculate_staker_distributions",
    "find_optimal_staker_count",
    "run_staker_matrix",
    # Channel Partner Pool (genesis founding partners)
    "CHANNEL_PARTNER_CAP",
    "CHANNEL_PARTNER_PASSIVE_SHARE",
    "RegistryState",
    "ChannelPartner",
    "GenesisClosureEvent",
    "ChannelPartnerDistribution",
    "ChannelPartnerPool",
    "get_channel_partner_pool",
    "reset_channel_partner_pool",
    # Fee simulation (test different economic parameters)
    "FeeScenario",
    "SimulationResult",
    "run_scenario",
    "compare_scenarios",
    "print_comparison",
    # BTC Reserve (Hotel California - BTC flows in, never out)
    "BTCSourceType",
    "PaymentCrypto",
    "CryptoRates",
    "BTCInflow",
    "BTCReserve",
    "get_btc_reserve",
    "reset_btc_reserve",
    # F_i Order Book (buy/sell FoundUp tokens)
    "OrderSide",
    "OrderStatus",
    "EntryProtectionConfig",
    "Order",
    "Trade",
    "FiOrderBook",
    "OrderBookManager",
    # Demurrage (bio-decay for LIQUID UPS - WSP 26 Section 16)
    "TokenState",
    "ActivityTier",
    "ACTIVITY_TIER_MULTIPLIERS",
    "ACTIVITY_TIER_THRESHOLDS",
    "FoundUpType",  # Type-based redistribution ratios
    "FOUNDUP_TYPE_RATIOS",  # Default ratios by FoundUp type
    "NotificationType",
    "DecayNotification",
    "DecayConfig",
    "WalletState",
    "DemurrageEngine",
    "DECAY_RELIEF_ACTIVITIES",
    "get_relief_for_activity",
    # Circuit Breaker (death spiral prevention)
    "BreakerState",
    "BreakerTrigger",
    "BreakerConfig",
    "QueuedExit",
    "CircuitBreaker",
    "get_circuit_breaker",
    "reset_circuit_breaker",
    # Bonding Curve (guaranteed liquidity AMM)
    "BondingCurveConfig",
    "FiBondingCurve",
    "BondingCurveManager",
    # Rage Quit (Moloch-style fair exit)
    "FailureReason",
    "FoundUpHealth",
    "RageQuitConfig",
    "RageQuitResult",
    "RageQuitAdapter",
    "get_rage_quit_adapter",
    "reset_rage_quit_adapter",
    # Emergency Reserve (Ethena-style stability fund)
    "ReserveSourceType",
    "DeploymentReason",
    "ReserveDeposit",
    "ReserveDeployment",
    "EmergencyReserveConfig",
    "EmergencyReserve",
    "get_emergency_reserve",
    "reset_emergency_reserve",
    # Investor Staking (Bitclout-inspired bonding curve)
    "bonding_price",
    "bonding_cost",
    "bonding_tokens_for_btc",
    "calculate_investor_return",
    "InvestorTier",
    "InvestorPosition",
    "InvestorPool",
    "get_investor_pool",
    "reset_investor_pool",
    "demonstrate_10x_100x_returns",
    # Investor liability and coverage underwriting
    "InvestorCohort",
    "BuyoutPolicy",
    "EscrowSchedule",
    "LiabilitySnapshot",
    "FundingSources",
    "CoverageCovenants",
    "CoverageResult",
    "InvestorLiabilityEngine",
    "BuyoutCoverageEngine",
    # Underwriting scenarios
    "ContractTerms",
    "FoundupLane",
    "PoolMember",
    "ScenarioConfig",
    "YearProjection",
    "UnderwritingOutcome",
    "stake_weight",
    "simulate_underwriting",
    "default_scenarios",
    "run_underwriting_matrix",
    # F_i Rating Engine (color temperature gradient)
    "ColorTemperature",
    "COLOR_GRADIENT",
    "interpolate_color",
    "FounderTrackRecord",
    "FiRating",
    "AgentProfile",
    "FiRatingEngine",
    "get_rating_engine",
    "reset_rating_engine",
    # Dynamic Exit Friction (WSP 26 Section 14)
    "FoundUpTier",
    "MATURITY_EXIT_FEES",
    "MIN_EXIT_FEE",
    "ActivityMetrics",
    "ExitFeeResult",
    "calculate_stake_discount",
    "calculate_vesting_bonus",
    "calculate_activity_modifier",
    "calculate_dynamic_exit_fee",
    "DynamicExitEngine",
    "get_dynamic_exit_engine",
    "reset_dynamic_exit_engine",
    # Epoch Ledger (WSP 26 Section 15 - auditable distributions)
    "EpochEntry",
    "MerkleProof",
    "EpochLedger",
    "get_epoch_ledger",
    "reset_epoch_ledgers",
    # Layer-D BTC Anchor Connector (WSP 78 - blockchain settlement)
    "AnchorMode",
    "AnchorStatus",
    "AnchorRecord",
    "BTCAnchorConnector",
    "get_anchor_connector",
    "reset_anchor_connector",
    "LAYER_D_ENABLED",
    # Participation Sentinel (WSP 26 Section 15 - AI pattern detection)
    "AlertType",
    "RecommendedAction",
    "SentinelAlert",
    "ParticipantProfile",
    "ParticipationSentinel",
    "get_participation_sentinel",
    "reset_participation_sentinel",
    # Allocation Engine (0102 digital twin UPS→F_i routing)
    "AllocationStrategy",
    "AllocationPath",
    "AllocationTarget",
    "AllocationResult",
    "AllocationBatch",
    "AllocationEngine",
    "get_allocation_engine",
    "reset_allocation_engine",
    # CABR flow router (pipe-size treasury routing)
    "CABRFlowInputs",
    "CABRFlowResult",
    "DEFAULT_RELEASE_RATE",
    "route_cabr_ups_flow",
    # pAVS Audit (OpenClaw verification)
    "PAVSAuditor",
    "PAVSAuditReport",
    "AuditCheck",
    "AuditSection",
    "AuditStatus",
    "run_audit",
    # AI Parameter Optimizer (OpenClaw + GPT)
    "OptimizationObjective",
    "OptimizationResult",
    "ParameterBounds",
    "TUNABLE_PARAMETERS",
    "OptimizerConfig",
    "AIParameterOptimizer",
    # Subscription Tiers (Stake-to-Spend Model)
    "SubTier",
    "SUBSCRIPTION_TIER_CONFIGS",
    "SUBSCRIPTION_AGENT_COSTS",
    "TOPUP_OPTIONS",
    "calculate_monthly_capacity",
    "model_usage_pattern",
    "recommend_tier",
    "project_subscription_revenue",
    # Agent Compute Costs (Real Infrastructure)
    "TaskComplexity",
    "InfrastructureCost",
    "AGENT_INFRASTRUCTURE_COSTS",
    "UPsPricing",
    "calculate_ups_pricing",
    "FoundUpStake",
    "UserAccount",
    "simulate_user_journey",
    "analyze_openclaw_infrastructure",
    # Ten Year Projection (Combined Revenue)
    "GROWTH_SCENARIOS",
    "SUBSCRIBER_GROWTH_SCENARIOS",
    "YearSnapshot",
    "TenYearProjection",
    "interpolate_growth",
    "interpolate_subscribers",
    "calculate_subscription_revenue",
    "generate_projection",
    "generate_all_projections",
    "export_for_animation",
]
