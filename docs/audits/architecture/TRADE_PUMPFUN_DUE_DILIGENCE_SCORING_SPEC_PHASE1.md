# TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1

**Worker**: W9
**Date**: 2026-05-23
**Status**: SPEC_ONLY
**Base commit**: origin/main
**Mode**: Read-only architecture/spec

---

## WSP 97 Truth Boundary Checklist

| Label | Status |
|-------|--------|
| DOCS_ONLY | YES |
| SPEC_ONLY | YES |
| NO_CODE_CHANGE | YES |
| NO_LIVE_FEEDS | YES |
| NO_EXTERNAL_API_CALLS | YES |
| NO_WALLET | YES |
| NO_ORDER_PLACEMENT | YES |
| NO_NETWORK_CALLS | YES |
| NO_REAL_TRADING | YES |
| NO_EXCHANGE_SDK_IMPORT | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_CATALOG_MUTATION | YES |
| NO_MANIFEST_MUTATION | YES |
| NO_PROJECTION_MUTATION | YES |
| NO_PORTFOLIO_PROMOTION | YES |
| NO_PUBLIC_SURFACE_CLAIM | YES |
| NO_CI_GATE_ACTIVATION | YES |
| NO_DEPENDENCY_INSTALL | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. HoloIndex Assessment

### Queries Executed

| Query | Quality | Notes |
|-------|---------|-------|
| "Trade pump.fun memecoin issuer X telegram influencer rug pull" | POOR | Did NOT surface Trade docs despite terms present |
| "Trade FoundUp game theory memecoin launchpad social due diligence" | GOOD | Trade README, ROADMAP surfaced |
| "TRADE_POC_SIMULATION_HARNESS_PHASE1" | GOOD | Trade INTERFACE, README surfaced |
| "TRADE_ADAPTER_INTEGRATION_PHASE1" | GOOD | adapters.py, contracts.py surfaced |

### Retrieval Quality Report

| Check | Result |
|-------|--------|
| Trade README surfaced | YES (queries 2-4) |
| Trade INTERFACE surfaced | YES (queries 3-4) |
| Trade ROADMAP surfaced | YES (query 2) |
| Recent simulation/evidence audits surfaced | NO (required direct file listing) |
| Fallback rg/direct read required | YES (for audit file inventory) |

### HoloIndex Improvement Feedback

**Query 1 failed due to multiple retrieval-quality factors:**

| Factor | Issue |
|--------|-------|
| Term mismatch | Query: `issuer`, `X account`, `rug pull`. Docs: `creator`, `twitter`, `soft-rug`, `rug_pull_score` |
| Punctuation tokenization | `pump.fun` may split as `pump` + `fun`, diluting match |
| Long mixed query dilution | Combining launchpad, social, rug, influencer, WSP_15 lets unrelated files win on generic terms |
| No module/path boost | HoloIndex does not know intent is `modules/foundups/trade/**` |
| Design gap | Some due-diligence terms are implied but not explicitly documented |

**Better queries for future:**
```
"Trade FoundUp Pump.fun Bitquery top traders holder distribution"
"Trade RiskEvent rug_pull_score honeypot_score insider_concentration_score"
"Trade SocialEvent twitter telegram discord sentiment engagement"
```

**Future HoloIndex improvement candidates:**
- Punctuation normalization: `pump.fun` <-> `pumpfun` <-> `pump fun`
- Alias expansion: `X` <-> `twitter`, `issuer` <-> `creator`
- Module/path boost when query includes known FoundUp name
- Stronger exact-file scoring for module paths

---

## 2. Existing Trade Docs Inventory

### 2.1 Documented Components

| Component | Location | Status |
|-----------|----------|--------|
| Universal event schemas | `contracts.py`, `INTERFACE.md` | DOCUMENTED |
| MarketEvent, TokenEvent, WalletEvent | `contracts.py` | DOCUMENTED |
| SocialEvent, RiskEvent | `contracts.py` | DOCUMENTED |
| Adapter layer (Market, Launchpad) | `contracts.py`, `adapters.py` | DOCUMENTED |
| Pump.fun/PumpSwap adapter specs | `INTERFACE.md` | DOCUMENTED |
| ExecutionGuard/SimulationGuard | `guards.py` | DOCUMENTED |
| Truth fields (WSP 97) | `contracts.py` | DOCUMENTED |
| Risk score fields | `RiskEvent` dataclass | DOCUMENTED |
| Social bot/coordination detection | `SocialEvent` dataclass | DOCUMENTED |
| Holder distribution | `LaunchpadAdapterSpec` | DOCUMENTED |
| Top traders | `LaunchpadAdapterSpec` | DOCUMENTED |
| Bonding curve tracking | `LaunchpadAdapterSpec` | DOCUMENTED |
| Migration tracking | `LaunchpadAdapterSpec` | DOCUMENTED |

### 2.2 Existing Risk Fields in RiskEvent

From `contracts.py` / `INTERFACE.md`:

```python
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

### 2.3 Existing Social Fields in SocialEvent

```python
sentiment_score: Optional[float]  # -1.0 to 1.0
mention_count: Optional[int]
engagement_score: Optional[float]
bot_activity_detected: bool
coordinated_activity_detected: bool
```

### 2.4 Existing Wallet Fields in WalletEvent

```python
wallet_cluster_id: Optional[str]  # Hashed, not raw PII
is_known_entity: bool
entity_label: Optional[str]       # whale, insider, bot
```

---

## 3. Missing Design Gap

**The 012-intended workflow is NOT explicitly canonicalized:**

```text
discover pump.fun launches
  -> research issuer
  -> check X account activity
  -> check Telegram activity
  -> identify who is pumping it
  -> track influencers/KOLs
  -> check what tokens issuer/influencers launched before
  -> audit large trades
  -> audit whale/wallet history across tokens
  -> rate token via WSP_15-style scoring
  -> verify not rug pull
  -> decide whether it is worth simulated capture in pump.fun stage
```

### 3.1 Missing Components

| Component | Status | Gap |
|-----------|--------|-----|
| Due-diligence workflow sequence | MISSING | No explicit pipeline defined |
| Issuer identity/history research | PARTIAL | `creator_address` exists, no history lookup |
| X (Twitter) account analysis | PARTIAL | `SocialEvent` exists, no X-specific workflow |
| Telegram community analysis | PARTIAL | `SocialEvent` exists, no Telegram-specific workflow |
| Influencer/KOL identification | MISSING | No KOL tracking schema |
| Prior token launch history | MISSING | No cross-token issuer history |
| Large trade audit | PARTIAL | `WalletEvent` exists, no audit workflow |
| Cross-token wallet history | MISSING | No wallet history across tokens |
| WSP_15-style prioritization score | MISSING | No decision band scoring |
| Simulated capture decision | MISSING | No explicit decision model |
| Game-theory rationale | PARTIAL | Mentioned in README, not formalized |

---

## 4. Pump.fun Discovery Flow

### 4.1 Launch Detection Pipeline

```text
[Bitquery/RPC Feed] 
    -> [Launch Detection]
    -> [Initial Filter (market cap, age, bonding progress)]
    -> [Due Diligence Queue]
```

### 4.2 Initial Filter Criteria

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Token age | < 24 hours | Focus on fresh launches |
| Bonding curve progress | < 80% | Not yet migrated |
| Initial market cap | $1K - $500K | Avoid micro/mega caps |
| Minimum transactions | > 10 | Filter dead launches |
| Creator verified | Not anonymous | Basic identity check |

### 4.3 Discovery Event Schema

```python
@dataclass
class LaunchDiscoveryEvent:
    event_id: str
    timestamp: datetime
    token_address: str
    token_symbol: str
    token_name: str
    chain: str = "solana"
    launchpad: str = "pumpfun"
    creator_address: str
    bonding_curve_progress: float
    initial_market_cap_usd: float
    transaction_count: int
    discovery_source: str  # "bitquery", "rpc", "websocket"
    passed_initial_filter: bool
    filter_rejection_reasons: List[str] = field(default_factory=list)
```

---

## 5. Issuer / Social / Influencer Due Diligence

### 5.1 Issuer Identity Research

| Signal | Source | Weight |
|--------|--------|--------|
| Creator wallet age | On-chain | Medium |
| Creator prior tokens | On-chain | High |
| Creator prior token outcomes | On-chain | High |
| Creator social links | Token metadata | Medium |
| Creator X account | Linked metadata | Medium |
| Creator Telegram | Linked metadata | Medium |
| Creator anonymity | Absence of links | High (negative) |

### 5.2 X (Twitter) Account Analysis

| Signal | Source | Weight |
|--------|--------|--------|
| Account age | X API | Medium |
| Follower count | X API | Low |
| Follower quality (bot %) | X API analysis | High |
| Recent token mentions | X API search | Medium |
| Prior token shilling history | Historical search | High |
| Engagement authenticity | X API metrics | High |
| Account verified | X API | Low |

### 5.3 Telegram Community Analysis

| Signal | Source | Weight |
|--------|--------|--------|
| Group exists | Telegram API | Medium |
| Member count | Telegram API | Low |
| Member growth rate | Telegram API | Medium |
| Bot % in group | Telegram API analysis | High |
| Admin activity | Telegram API | Medium |
| Spam/shill ratio | Message analysis | High |
| Prior group history | Historical lookup | High |

### 5.4 Influencer/KOL Detection

| Signal | Detection Method | Risk Level |
|--------|------------------|------------|
| Known pumper wallet | Entity database | HIGH |
| Coordinated buy timing | Transaction clustering | HIGH |
| Influencer X mention | X API monitoring | MEDIUM |
| Paid promotion disclosure | Content analysis | LOW |
| Multiple influencers same token | Coordination pattern | HIGH |
| Influencer prior rug history | Historical lookup | CRITICAL |

### 5.5 Issuer/Influencer History Schema

```python
@dataclass
class EntityHistoryReport:
    entity_id: str  # Hashed wallet or social handle
    entity_type: str  # "issuer", "influencer", "whale"
    prior_token_launches: int
    prior_rug_pulls: int
    prior_successful_launches: int
    average_token_lifespan_hours: float
    average_holder_loss_percent: float
    known_associations: List[str]  # Other flagged entities
    first_seen_timestamp: datetime
    risk_classification: str  # "clean", "suspicious", "flagged", "blacklisted"
    confidence: float
```

---

## 6. Wallet / Large Trade / Holder Audit

### 6.1 Holder Distribution Analysis

| Signal | Threshold | Risk Level |
|--------|-----------|------------|
| Top 10 holder % | > 50% | HIGH |
| Creator holding % | > 20% | HIGH |
| Single wallet % | > 15% | MEDIUM |
| Wallet cluster concentration | > 30% in cluster | HIGH |
| New wallet % (< 1 day old) | > 40% | HIGH |

### 6.2 Large Trade Audit

| Signal | Detection | Risk Level |
|--------|-----------|------------|
| Whale buy > 5% supply | Transaction monitoring | MEDIUM |
| Coordinated buys (timing) | Clustering | HIGH |
| Dev wallet activity | Creator wallet monitoring | CRITICAL |
| Insider pre-buy | Early transaction analysis | CRITICAL |
| Wash trading patterns | Self-transfer detection | HIGH |

### 6.3 Cross-Token Wallet History

| Signal | Source | Implication |
|--------|--------|-------------|
| Wallet held prior rugs | Historical lookup | HIGH RISK |
| Wallet is serial dumper | Exit pattern analysis | HIGH RISK |
| Wallet associated with scams | Entity database | CRITICAL |
| Wallet is known bot | Bot database | MEDIUM |
| Wallet is known whale | Whale database | INFORMATIONAL |

### 6.4 Wallet Audit Schema

```python
@dataclass
class WalletAuditReport:
    wallet_hash: str  # Privacy-preserving hash
    token_address: str
    holding_percent: float
    acquisition_timestamp: datetime
    acquisition_price_usd: float
    current_value_usd: float
    unrealized_pnl_percent: float
    prior_tokens_held: int
    prior_rugs_held: int
    prior_dumps_executed: int
    entity_classification: str  # "retail", "whale", "insider", "bot", "scammer"
    risk_contribution: float  # 0.0 - 1.0
```

---

## 7. Rug Pull / Honeypot / No-Exit Risk Model

### 7.1 Rug Pull Risk Signals

| Signal | Detection | Weight |
|--------|-----------|--------|
| Creator large holding | Holder analysis | 0.25 |
| Creator prior rugs | History lookup | 0.30 |
| Liquidity < 24h old | LP analysis | 0.10 |
| No locked liquidity | LP analysis | 0.20 |
| Social suddenly silent | Social monitoring | 0.15 |

### 7.2 Honeypot Risk Signals

| Signal | Detection | Weight |
|--------|-----------|--------|
| Sell tax > buy tax | Contract analysis | 0.30 |
| Transfer restrictions | Contract analysis | 0.30 |
| Hidden mint function | Contract analysis | 0.20 |
| Blacklist function | Contract analysis | 0.10 |
| Pause function | Contract analysis | 0.10 |

### 7.3 No-Exit Risk Signals

| Signal | Detection | Weight |
|--------|-----------|--------|
| Zero liquidity | LP analysis | 0.40 |
| Frozen liquidity | LP analysis | 0.30 |
| Only creator can sell | Transaction analysis | 0.30 |

### 7.4 Composite Risk Score

```python
@dataclass
class CompositeRiskScore:
    token_address: str
    timestamp: datetime
    
    # Component scores (0.0 - 1.0, higher = more risk)
    rug_pull_risk: float
    honeypot_risk: float
    no_exit_risk: float
    holder_concentration_risk: float
    social_authenticity_risk: float
    issuer_history_risk: float
    whale_manipulation_risk: float
    
    # Aggregate
    total_risk_score: float  # Weighted average
    confidence: float
    
    # Classification
    risk_band: str  # "low", "medium", "high", "critical"
    is_disqualified: bool
    disqualification_reasons: List[str]
```

---

## 8. WSP_15-Style Trade Score

### 8.1 Score Components

This is a **Trade-specific prioritization score**, not a mutation of WSP 15.

| Component | Weight | Range | Meaning |
|-----------|--------|-------|---------|
| `launch_timing_score` | 0.10 | 0-100 | Fresh launch advantage |
| `issuer_history_score` | 0.15 | 0-100 | Clean issuer history |
| `social_authenticity_score` | 0.10 | 0-100 | Real community signals |
| `telegram_quality_score` | 0.05 | 0-100 | Active, non-bot TG |
| `influencer_risk_score` | 0.10 | 0-100 | Low pump-and-dump risk |
| `holder_distribution_score` | 0.15 | 0-100 | Distributed holdings |
| `whale_risk_score` | 0.10 | 0-100 | Low whale manipulation |
| `prior_token_history_score` | 0.10 | 0-100 | Issuer track record |
| `bonding_curve_score` | 0.05 | 0-100 | Healthy curve progression |
| `rug_honeypot_score` | 0.10 | 0-100 | Low exit risk |

### 8.2 Aggregate Scores

```python
@dataclass
class TradeDueDiligenceScore:
    token_address: str
    timestamp: datetime
    
    # Component scores (0-100, higher = better)
    launch_timing_score: float
    issuer_history_score: float
    social_authenticity_score: float
    telegram_quality_score: float
    influencer_risk_score: float
    holder_distribution_score: float
    whale_risk_score: float
    prior_token_history_score: float
    bonding_curve_score: float
    rug_honeypot_score: float
    
    # Aggregates
    total_score: float          # Weighted sum (0-100)
    risk_score: float           # Inverted (0-100, higher = more risk)
    evidence_confidence: float  # Data completeness (0.0-1.0)
    
    # Decision
    decision_band: str
    band_rationale: str
```

### 8.3 Decision Bands

| Band | Total Score | Risk Score | Action |
|------|-------------|------------|--------|
| `reject` | < 30 | > 70 | Do not proceed |
| `observe` | 30-50 | 50-70 | Monitor only |
| `simulate_only` | 50-70 | 30-50 | Paper trade simulation |
| `candidate_for_future_review` | > 70 | < 30 | Flag for advanced analysis |

**No band authorizes real trading.**

### 8.4 Decision Rules

```python
def determine_decision_band(score: TradeDueDiligenceScore) -> str:
    # Hard disqualifiers
    if score.rug_honeypot_score < 20:
        return "reject"
    if score.issuer_history_score < 20:
        return "reject"
    if score.evidence_confidence < 0.5:
        return "observe"
    
    # Band determination
    if score.total_score < 30:
        return "reject"
    elif score.total_score < 50:
        return "observe"
    elif score.total_score < 70:
        return "simulate_only"
    else:
        return "candidate_for_future_review"
```

---

## 9. Game-Theory Rationale

### 9.1 Why Meme Launchpads?

Meme-coin launchpads are adversarial proving grounds:

| Property | Advantage |
|----------|-----------|
| High signal density | Many signals per hour |
| High adversarial activity | Rug pulls, honeypots, manipulation |
| Fast feedback loops | Know outcome in hours, not months |
| Low capital requirement | Can observe without large positions |
| Public data | All transactions on-chain |

### 9.2 Game-Theory Actors

| Actor | Goal | Detection |
|-------|------|-----------|
| Legitimate issuer | Build community, long-term value | Clean history, active TG, no prior rugs |
| Rug puller | Extract maximum value, exit | High creator %, prior rugs, sudden silence |
| Pump-and-dump operator | Coordinate pump, dump on retail | Influencer coordination, timed buys/sells |
| Bot operator | Front-run, sandwich, arbitrage | Transaction patterns, timing |
| Retail trader | Buy low, sell high | Random timing, small positions |

### 9.3 Simulated Capture Decision

**When to simulate capture (all must be true):**

1. `decision_band` is `simulate_only` or `candidate_for_future_review`
2. `evidence_confidence` >= 0.7
3. No critical risk flags
4. Bonding curve < 70% (not yet migrated)
5. Token age < 6 hours (fresh launch)

**Simulation parameters:**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Simulated entry size | $100 equivalent | Small position |
| Simulated exit trigger | +100% or -50% | Realistic targets |
| Simulated hold time max | 2 hours | Fast meme cycle |
| Position limit | 1 at a time | No portfolio complexity |

---

## 10. What This Does NOT Authorize

This spec explicitly does NOT authorize:

| Action | Status | Reason |
|--------|--------|--------|
| Real trades | BLOCKED | Phase 0 no-money mode |
| Wallet signing | BLOCKED | No private key access |
| Order placement | BLOCKED | No exchange integration |
| Capital deployment | BLOCKED | No funds |
| Public promotion of tokens | BLOCKED | Not investment advice |
| Influencer identification (real names) | BLOCKED | Privacy boundary |
| Wallet deanonymization | BLOCKED | Privacy boundary |
| Insider trading | BLOCKED | Illegal |
| Market manipulation | BLOCKED | Illegal |
| Front-running | BLOCKED | Unethical |
| Wash trading | BLOCKED | Illegal |

---

## 11. Recommended Implementation Slices

### 11.1 Immediate (Phase 1)

| Slice | Scope | Priority |
|-------|-------|----------|
| `TRADE_DUE_DILIGENCE_SCHEMA_PHASE1` | Add `TradeDueDiligenceScore`, `EntityHistoryReport`, `WalletAuditReport` to contracts.py | P1 |
| `TRADE_LAUNCH_DISCOVERY_PIPELINE_PHASE1` | Implement `LaunchDiscoveryEvent` and initial filter | P1 |
| `TRADE_ISSUER_HISTORY_LOOKUP_PHASE1` | Implement issuer history lookup (simulation fixture) | P1 |

### 11.2 Near-Term (Phase 2)

| Slice | Scope | Priority |
|-------|-------|----------|
| `TRADE_SOCIAL_ANALYSIS_SPEC_PHASE1` | Spec X and Telegram analysis workflow | P2 |
| `TRADE_HOLDER_AUDIT_SPEC_PHASE1` | Spec holder distribution and whale audit | P2 |
| `TRADE_DECISION_BAND_ENGINE_PHASE1` | Implement scoring and band determination | P2 |

### 11.3 Harness Regime Expansion (Post-Spec)

Replace generic "bull/bear/ranging" with due-diligence regimes:

| Regime | Description |
|--------|-------------|
| `organic_launch_clean_socials` | Legitimate launch with real community |
| `influencer_pump_high_concentration` | Coordinated pump, concentrated holders |
| `dead_x_no_telegram` | Abandoned social presence |
| `issuer_prior_rug_history` | Known bad actor |
| `whale_accumulation_then_dump` | Whale manipulation pattern |
| `telegram_active_low_authenticity` | Bot-filled community |
| `bonding_curve_migration_risk` | Near migration, exit risk |

---

## 12. Files Changed

| File | Change |
|------|--------|
| `docs/audits/architecture/TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md` | NEW (this file) |

No code changes. No runtime changes. Spec only.

---

## 13. Evidence Packet

```yaml
branch: docs/trade-pumpfun-due-diligence-scoring-spec-phase1
base: origin/main

files_changed:
  - docs/audits/architecture/TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md

holoindex_assessment:
  query_1_quality: POOR (Trade docs not surfaced)
  query_2_quality: GOOD
  query_3_quality: GOOD
  query_4_quality: GOOD
  improvement_feedback: Query 1 should surface Trade README for "pump.fun", "rug pull" terms

existing_docs_summary:
  - Event schemas: DOCUMENTED
  - Adapter layer: DOCUMENTED
  - Risk fields: DOCUMENTED (partial)
  - Social fields: DOCUMENTED (partial)
  - Guards: DOCUMENTED

missing_design_summary:
  - Due-diligence workflow: NOW SPECIFIED
  - Issuer history research: NOW SPECIFIED
  - Influencer/KOL tracking: NOW SPECIFIED
  - Cross-token wallet history: NOW SPECIFIED
  - WSP_15-style scoring: NOW SPECIFIED
  - Decision bands: NOW SPECIFIED

scoring_model_summary:
  components: 10 (launch_timing, issuer_history, social_authenticity, etc.)
  decision_bands: 4 (reject, observe, simulate_only, candidate_for_future_review)
  no_band_authorizes_real_trading: TRUE

next_implementation_slice: TRADE_DUE_DILIGENCE_SCHEMA_PHASE1

wsp_97_verdict: PASS (all 21 labels verified YES)

w10_readiness: READY
```

---

*Spec authored under WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22.*
*Slice: TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1*
