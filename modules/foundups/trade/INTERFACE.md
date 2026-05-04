# Trade FoundUp - Interface Contract

**Version**: 0.1.0  
**Status**: Incubating (Phase 0)  
**WSP References**: WSP 11 (Interface), WSP 97 (Truth), WSP 104 (Namespace)

---

## 1. Adapter Contract Boundaries

### 1.1 MarketAdapterSpec

Market adapters abstract blockchain or exchange-specific details.

```python
@dataclass
class MarketAdapterSpec:
    adapter_id: str           # Unique adapter identifier
    chain_or_exchange: str    # e.g., "solana", "ethereum", "binance"
    display_name: str         # Human-readable name
    status: AdapterStatus     # PLANNED | INTERFACE_ONLY | SIMULATION | PAPER_TRADING
    
    # Capabilities
    supports_token_events: bool
    supports_wallet_events: bool
    supports_ohlcv: bool
    supports_order_book: bool
    supports_social_signals: bool
    
    # Truth boundary
    live_execution_enabled: bool = False  # MUST be False in Phase 0
```

**Planned Adapters:**

| Adapter ID | Chain/Exchange | Priority |
|------------|----------------|----------|
| `solana` | Solana | P1 |
| `ethereum` | Ethereum | P2 |
| `base` | Base | P2 |
| `bnb` | BNB Chain | P2 |
| `tron` | Tron | P3 |
| `cardano` | Cardano | P3 |

### 1.2 LaunchpadAdapterSpec

Launchpad adapters abstract token launch platform mechanics.

```python
@dataclass
class LaunchpadAdapterSpec:
    adapter_id: str           # Unique adapter identifier
    platform_name: str        # e.g., "pump.fun", "sunpump"
    chain: str                # Underlying chain
    display_name: str         # Human-readable name
    status: AdapterStatus     # PLANNED | INTERFACE_ONLY | SIMULATION
    
    # Capabilities
    supports_launch_detection: bool
    supports_bonding_curve: bool
    supports_migration_tracking: bool
    supports_top_traders: bool
    supports_holder_distribution: bool
    
    # Truth boundary
    live_execution_enabled: bool = False  # MUST be False in Phase 0
```

**Planned Adapters:**

| Adapter ID | Platform | Chain | Data Source |
|------------|----------|-------|-------------|
| `pumpfun` | Pump.fun | Solana | Bitquery |
| `pumpswap` | PumpSwap | Solana | Bitquery |
| `raydium_launchlab` | Raydium LaunchLab | Solana | Direct RPC |
| `moonshot` | Moonshot | Solana | TBD |
| `letsbonk` | LetsBONK | Solana | TBD |
| `four_meme` | Four.Meme | BNB | TBD |
| `sunpump` | SunPump | Tron | TBD |
| `zora` | Zora | Base/ETH | TBD |
| `snekfun` | Snek.fun | Cardano | TBD |

---

## 2. Universal Event Schema

All events normalize to these schemas:

### 2.1 MarketEvent

```python
@dataclass
class MarketEvent:
    event_id: str
    event_type: str           # price_update, volume_spike, liquidity_change
    adapter_id: str
    chain: str
    timestamp: datetime
    symbol: Optional[str]
    price_usd: Optional[float]
    volume_24h: Optional[float]
    market_cap: Optional[float]
    liquidity_usd: Optional[float]
    raw_data: Dict[str, Any]
```

### 2.2 TokenEvent

```python
@dataclass
class TokenEvent:
    event_id: str
    event_type: str           # token_created, migrated_to_dex, metadata_update
    adapter_id: str
    chain: str
    timestamp: datetime
    token_address: Optional[str]
    token_symbol: Optional[str]
    token_name: Optional[str]
    creator_address: Optional[str]
    launchpad: Optional[str]
    bonding_curve_progress: Optional[float]  # 0.0 - 1.0
    raw_data: Dict[str, Any]
```

### 2.3 WalletEvent

```python
@dataclass
class WalletEvent:
    event_id: str
    event_type: str           # buy, sell, transfer, holder_change
    adapter_id: str
    chain: str
    timestamp: datetime
    wallet_cluster_id: Optional[str]  # Hashed, not raw PII
    is_known_entity: bool
    entity_label: Optional[str]       # whale, insider, bot
    token_address: Optional[str]
    action: Optional[str]
    amount_tokens: Optional[float]
    amount_usd: Optional[float]
    raw_data: Dict[str, Any]
```

### 2.4 SocialEvent

```python
@dataclass
class SocialEvent:
    event_id: str
    event_type: str           # mention, sentiment_shift, influencer_post
    source: str               # twitter, telegram, discord
    timestamp: datetime
    token_address: Optional[str]
    token_symbol: Optional[str]
    sentiment_score: Optional[float]  # -1.0 to 1.0
    mention_count: Optional[int]
    engagement_score: Optional[float]
    bot_activity_detected: bool
    coordinated_activity_detected: bool
    raw_data: Dict[str, Any]
```

### 2.5 RiskEvent

```python
@dataclass
class RiskEvent:
    event_id: str
    event_type: str           # honeypot_detected, rug_risk, exit_blocked
    timestamp: datetime
    token_address: Optional[str]
    chain: Optional[str]
    overall_risk_score: float       # 0.0 = safe, 1.0 = max risk
    honeypot_score: float
    rug_pull_score: float
    no_exit_score: float
    insider_concentration_score: float
    is_honeypot: bool
    is_exit_blocked: bool
    has_suspicious_holders: bool
    risk_factors: List[str]
    confidence: float               # 0.0 - 1.0
```

---

## 3. WRE Task Adapter Plan

Future WRE integration:

| Task Type | WRE Action | Trade Handler |
|-----------|------------|---------------|
| `trade_analyze` | Analysis job | Risk engine |
| `trade_simulate` | Simulation job | Paper trade engine |
| `trade_score` | Scoring job | Proof metrics |
| `trade_report` | Reporting job | Audit logger |

**FoundUpJob Fields:**

```python
{
    "foundup_id": "trade",
    "tenant_id": "...",
    "requested_action": "trade_analyze",
    "payload": {
        "token_address": "...",
        "chain": "solana",
        "analysis_type": "risk_score"
    }
}
```

---

## 4. FAM Event Plan

FAM event emission patterns:

| Event Type | Trigger | Data |
|------------|---------|------|
| `trade.risk_scored` | Risk analysis complete | Risk event summary |
| `trade.simulation_complete` | Paper trade finished | Simulation result |
| `trade.signal_generated` | Trade/exit signal | Signal data |
| `trade.adapter_status_change` | Adapter health change | Adapter status |

---

## 5. pAVS Registration Plan

pAVS verification seam integration:

| Capability | pAVS Role |
|------------|-----------|
| `market_intelligence` | Provide market analysis |
| `risk_scoring` | Provide risk assessments |
| `simulation` | Provide paper trading |
| `proof_metrics` | Provide performance metrics |

**Registration (future):**

```python
pavs_register(
    foundup_id="trade",
    capabilities=["market_intelligence", "risk_scoring", "simulation"],
    proof_receipt_types=["risk_score", "simulation_result"]
)
```

---

## 6. Proof Metric Plan

Performance tracking without real capital:

| Metric Category | Metrics |
|-----------------|---------|
| **Latency** | Detection latency, adapter latency, model latency |
| **Accuracy** | Honeypot detection, no-exit detection, soft-rug prediction, false positives, false negatives |
| **Performance** | Simulated expectancy, simulated max drawdown, win rate, Sharpe ratio |
| **Reliability** | Valid JSON rate, rate-limit reliability, adapter uptime |
| **Cost** | Model cost per analysis, API cost per request |

---

## 7. Explicit Unsupported Operations

**Phase 0 blocks all execution operations:**

| Operation | Status | Reason |
|-----------|--------|--------|
| Real trades | BLOCKED | No-money mode |
| Wallet signing | BLOCKED | No private key access |
| Private key access | BLOCKED | Security boundary |
| Order placement | BLOCKED | No exchange integration |
| Wash trading | BLOCKED | Illegal activity |
| Market manipulation | BLOCKED | Illegal activity |
| Bot concealment | BLOCKED | Ethical violation |
| Fake volume | BLOCKED | Market manipulation |
| Autonomous capital deployment | BLOCKED | No-money mode |

**Enforcement:**

```python
from contracts import ExecutionGuardPolicy, UnsupportedOperationError

guard = ExecutionGuardPolicy()
guard.assert_operation_allowed("real_trade")  # Raises UnsupportedOperationError
```

---

## 8. Truth Fields Contract

All Trade operations must respect WSP 97 truth fields:

```python
@dataclass
class TruthFields:
    dry_run_mode: bool = True           # MUST be True in Phase 0
    no_money_mode: bool = True          # MUST be True in Phase 0
    real_execution_performed: bool = False
    verification_complete: bool = False
    cabr_ready: bool = False
    payout_ready: bool = False
```

---

## 9. Public API (Phase 0)

**Contracts module:**

```python
from modules.foundups.trade.src.contracts import (
    # Adapter specs
    MarketAdapterSpec,
    LaunchpadAdapterSpec,
    AdapterStatus,
    
    # Event schemas
    MarketEvent,
    TokenEvent,
    WalletEvent,
    SocialEvent,
    RiskEvent,
    
    # Signal schemas
    TradeSignal,
    ExitSignal,
    
    # Proof schemas
    ProofMetric,
    SimulationResult,
    
    # Guard
    ExecutionGuardPolicy,
    UnsupportedOperationError,
    
    # Truth
    TruthFields,
    DEFAULT_TRUTH_FIELDS,
    DEFAULT_EXECUTION_GUARD,
)
```

**Adapters module (v0.2.0):**

```python
from modules.foundups.trade.src.adapters import (
    # Capability enum
    AdapterCapability,
    
    # Health/rate limit tracking
    AdapterHealth,
    AdapterRateLimit,
    AdapterErrorCode,
    AdapterError,
    AdapterResult,
    
    # Protocols
    MarketAdapter,
    LaunchpadAdapter,
    
    # Registry
    AdapterRegistry,
    get_adapter_registry,
    reset_adapter_registry,
)
```

**Events module (v0.2.0):**

```python
from modules.foundups.trade.src.events import (
    # ID generation
    generate_event_id,
    generate_deterministic_event_id,
    
    # Event constructors
    create_market_event,
    create_price_update_event,
    create_token_event,
    create_token_created_event,
    create_wallet_event,
    create_buy_event,
    create_sell_event,
    create_social_event,
    create_risk_event,
    create_honeypot_detection_event,
    create_rug_risk_event,
    
    # Validation
    validate_event,
    ValidationResult,
    
    # Utilities
    hash_wallet_address,
)
```

**Guards module (v0.2.0):**

```python
from modules.foundups.trade.src.guards import (
    # Exceptions
    NoMoneyModeViolation,
    WalletSigningViolation,
    OrderPlacementViolation,
    ExecutionGuardViolation,
    
    # Assertions
    assert_no_money_mode,
    assert_no_wallet_signing,
    assert_no_order_placement,
    assert_no_real_trades,
    
    # Policy validation
    validate_execution_guard_policy,
    validate_truth_fields,
    
    # Context manager
    SimulationGuard,
    create_phase0_guard,
    is_phase0_compliant,
)
```

---

## 10. Adapter Protocol

Adapters must implement these protocols:

### 10.1 MarketAdapter Protocol

```python
@runtime_checkable
class MarketAdapter(Protocol):
    @property
    def adapter_id(self) -> str: ...
    
    @property
    def spec(self) -> MarketAdapterSpec: ...
    
    def get_capabilities(self) -> List[AdapterCapability]: ...
    def get_health(self) -> AdapterHealth: ...
    
    async def fetch_market_data(self, symbol: str, **kwargs) -> AdapterResult: ...
    async def fetch_token_events(self, token_address: str, **kwargs) -> AdapterResult: ...
    async def fetch_wallet_events(self, wallet_address: str, **kwargs) -> AdapterResult: ...
```

### 10.2 LaunchpadAdapter Protocol

```python
@runtime_checkable
class LaunchpadAdapter(Protocol):
    @property
    def adapter_id(self) -> str: ...
    
    @property
    def spec(self) -> LaunchpadAdapterSpec: ...
    
    def get_capabilities(self) -> List[AdapterCapability]: ...
    def get_health(self) -> AdapterHealth: ...
    
    async def fetch_recent_launches(self, limit: int = 100, **kwargs) -> AdapterResult: ...
    async def fetch_bonding_curve(self, token_address: str, **kwargs) -> AdapterResult: ...
    async def fetch_top_traders(self, token_address: str, **kwargs) -> AdapterResult: ...
    async def fetch_holder_distribution(self, token_address: str, **kwargs) -> AdapterResult: ...
```

---

## 11. SimulationGuard Usage

```python
from modules.foundups.trade.src.guards import create_phase0_guard

# Create Phase 0 compliant guard
guard = create_phase0_guard()

# Use as context manager
with guard:
    # All operations verified as simulation-only
    guard.assert_simulation_only("my_operation")
    
    # Check blocked operations
    blocked = guard.get_blocked_operations()
    # ['real_trade', 'wallet_sign', 'private_key_access', ...]
    
    # Attempting blocked operation raises
    guard.assert_operation_allowed("real_trade")  # Raises UnsupportedOperationError
```

---

*All schemas serialize to dict/JSON via `.to_dict()` method.*
