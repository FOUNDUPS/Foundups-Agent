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

from .contracts import (
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
)

__all__ = [
    "MarketAdapterSpec",
    "LaunchpadAdapterSpec",
    "MarketEvent",
    "TokenEvent",
    "WalletEvent",
    "SocialEvent",
    "RiskEvent",
    "TradeSignal",
    "ExitSignal",
    "ProofMetric",
    "SimulationResult",
    "ExecutionGuardPolicy",
    "TruthFields",
]

__version__ = "0.1.0"
