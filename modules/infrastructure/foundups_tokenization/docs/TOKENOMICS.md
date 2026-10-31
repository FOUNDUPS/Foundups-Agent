# FoundUps Tokenomics: Complete Economic Model

**Version**: 2.1.0
**Date**: 2026-02-17
**Status**: Architecture Complete, Simulator Operational
**Canonical Spec**: [WSP 26: FoundUPS DAE Tokenization](../../../../WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md)
**Implementation**: [`modules/foundups/simulator/economics/`](../../../../modules/foundups/simulator/economics/__init__.py)

## Current qualification status — 2026-10-31

The 2026-02-17 header status is historical design status, not economic activation.
Follow the [WSP 26 §1.2 simulator-first change contract](../../../../WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md#12-simulator-first-change-contract).
Only valid behavior with fresh source-bound tests and independent acceptance is
the implementation reference; existing defects and disputed rules are excluded.
Activity/mint wording, stage versus continuous release, units, pool denominators,
fees and decay/burn variants below remain explicit conflicts, not new decisions.
See the [dated conflict inventory](../../../../docs/architecture/FOUNDUPS_BLOCKCHAIN_RECONCILIATION_SECURITY_20261031.md#5-economic-conflicts-and-0102-decisions).
Resolve/version changes in the simulator, independently accept them, update the
affected governing mirrors, then prove chain parity before separate activation.
No source publication or simulator result grants funding, signing or settlement.

### Security-first status — 2026-11-01

[The current roadmap](../../../../docs/architecture/FOUNDUPS_BLOCKCHAIN_RECONCILIATION_SECURITY_20261031.md#current-sprint-and-blockchain-roadmap--2026-11-01)
starts with wallet-policy isolation and complete epoch-effect accounting.
Adoption expands the released ceiling within the intended21M total; work-mint
capacity subtracts already mined supply. The separate staked F_i counter does
not prove a combined cap. Units, fees, denominators, funded backing and exits
remain unresolved; no new asset, schedule, solvency or issuance rule is selected.

## Executive Summary

FoundUps tokenomics implements a **bio-decay economic model** where:
1. **UPS (Universal Participation)** = Inflationary consumption token across ALL FoundUps
2. **FoundUp Tokens** (e.g., JUNK$) = Deflationary 21M-capped asset tokens per FoundUp
3. **CABR + PoB** = Pipe-size + valve routing of treasury UPS flow (prevents gaming)
4. **Bio-Decay States** = ICE/LIQUID/VAPOR (water analogy for intuitive UX)
5. **BTC Reserve** = Hotel California model (BTC flows in, never out)

**Result**: Self-sustaining economy where **active participation = value creation**, and **inactivity = value redistribution**.

---

## Table of Contents

1. [Two-Token Architecture](#two-token-architecture)
2. [Bio-Decay Model (ICE/LIQUID/VAPOR)](#bio-decay-model)
3. [CABR Integration (Flow Routing)](#cabr-integration)
4. [Rogers Diffusion Curve (Stage Release)](#rogers-diffusion-curve)
5. [BTC Reserve (Hotel California Model)](#btc-reserve)
5a. [Architectural Invariants (012-Confirmed)](#architectural-invariants)
6. [Mesh Network Integration](#mesh-network-integration)
7. [Mathematical Formulas](#mathematical-formulas)
8. [Economic Simulations](#economic-simulations)
9. [Early Capital Provider Economics](#early-capital-provider-economics)
10. [Implementation Roadmap](#implementation-roadmap)

---

## Two-Token Architecture

### UPS (Universal Participation Token)

```yaml
Purpose: "Consumption currency across ALL FoundUps"
Supply: "Floating  -reserve-backed circulating UPS (WSP 26/29)"
Value: "ups_per_btc = total_ups_circulating / total_btc_reserve"
Routing: "CABR sizes pipe, PoB opens valve, flow comes from treasury"
Characteristics:
  - Inflationary (grows with ecosystem activity)
  - Bio-decaying (incentivizes activity  -see Demurrage)
  - BTC-backed (floating rate  -more BTC = stronger UPS)
  - Cross-FoundUp (universal currency)
  - F_i can ONLY swap INTO UPS (not directly to external)
```

**Supply Dynamics** (floating value model):
- **More BTC accumulated**  ->ups_per_btc decreases  ->each UPS worth more BTC
- **More UPS routed into circulation**  ->ups_per_btc increases  ->each UPS worth less BTC
- **Bio-decay** removes UPS from circulation  ->deflation  ->UPS strengthens
- **Net effect**: Activity creates UPS (inflation) + decay removes UPS (deflation) + fees add BTC (backing)

**Example**:
```python
from modules.foundups.simulator.economics.btc_reserve import get_btc_reserve

reserve = get_btc_reserve()

# Initial state: genesis rate
# ups_per_btc = 100,000 (genesis default)

# After ecosystem activity and treasury routing:
# - 50,000 UPS circulating via CABR/PoB-routed flow
# - 0.5 BTC accumulated from fees/decay/exits
# ups_per_btc = 50,000 / 0.5 = 100,000 (stable!)

# After heavy activity + decay:
# - 80,000 UPS routed, but 30,000 decayed away -> 50,000 circulating
# - 1.2 BTC accumulated
# ups_per_btc = 50,000 / 1.2 = 41,667 (UPS strengthened!)
```

### FoundUp Tokens (e.g., JUNK$ for GotJunk)

```yaml
Purpose: "Asset-specific staking tokens"
Supply: "21,000,000 fixed (Bitcoin parity)"
Acquisition: "Swap UPS (burns UPS, issues FoundUp token allocation)"
Characteristics:
  - Deflationary (fixed cap)
  - Stage-released (Rogers Diffusion)
  - Slower decay than UPS (incentivizes staking)
  - Governance rights in FoundUp
  - Revenue sharing from fees
```

**Stage Allocation** (Rogers Diffusion):
```yaml
Innovators (2.5%):        525,000 tokens
  IDEA:        175,000  # 1:1 swap ratio
  Proto:       175,000  # 1:1 swap ratio
  Soft_Proto:  175,000  # 1:1 swap ratio

Early_Adopters (13.5%):  2,835,000 tokens
  MVP:       2,835,000  # 10:1 swap ratio

Early_Majority (34%):    7,140,000 tokens
  Launch:    7,140,000  # 100:1 swap ratio

Late_Majority (34%):     7,140,000 tokens
  Crowdfunding: 7,140,000  # 50:1 swap ratio

Laggards (16%):          3,360,000 tokens
  System_Reserve: NEVER RELEASED (stabilization fund)
```

---

## Bio-Decay Model (ICE/LIQUID/VAPOR)

### Water Analogy for Intuitive UX

```
EARN UPS (CABR validated)  ->LIQUID (wallet, decaying)
                                     ->              +----------------------+---------------------|               ->                     ->                     ->          STAKE               LET DECAY               EXIT
               ->                     ->                     ->        ICE (frozen)        RESERVOIR              VAPOR (tax)
        No decay            Returns to              15% fee
        Earn yield          Active users            80%  ->BTC
                                                    20%  ->Reservoir
```

### State Definitions

**ICE (Staked)**:
```yaml
State: "Frozen in FoundUp token (e.g., JUNK$)"
Decay: NONE
Benefits:
  - Governance voting rights
  - Revenue sharing (transaction fees)
  - Priority access to features
  - Network status/reputation
Transition: "Stake UPS  ->Receive FoundUp token position"
```

**LIQUID (Wallet)**:
```yaml
State: "Unstaked in user wallet"
Decay: ADAPTIVE (0.5% - 5% monthly)
Formula: "U(t) = U_0 * e^(-lambda(t)*t)"
Lambda_Calculation:
  base: "lambda_min + enzymatic_acceleration"
  circadian: "+ 30% during 6-7 PM local"
  cap: "Max 3% daily (no shock)"
Triggers:
  - Time elapsed since last activity
  - Inactivity period (D days)
  - Circadian pulse window
```

**VAPOR (Exited)**:
```yaml
State: "Swapped to external cryptocurrency"
Tax: "15% evaporation fee"
Routing:
  BTC_Allocation (80%): "Buy BTC, lock in reserves"
  Reservoir (20%): "Redistribute to active users"
Irreversible: "One-way exit (cannot return)"
Purpose: "Capture value on exit, strengthen ecosystem"
```

### Decay Relief Activities

**Actions that reset decay timer (D=0)**:
```yaml
FoundUp_Actions:
  - list_item:       24h relief, 1.0 UPS reward
  - sell_item:       48h relief, 2.0 UPS reward
  - host_storage:    24h relief, 0.01 UPS per file

Social_Actions:
  - invite_friend:   72h relief, 10.0 UPS reward
  - share_boost:     12h relief, 0.5 UPS reward

Governance:
  - vote_proposal:   24h relief, 0.1 UPS reward
  - create_proposal: 168h relief, 5.0 UPS reward

Cross_FoundUp:
  - use_other_foundup: 24h relief, 0.5 UPS reward
  - complete_cabr_task: 48h relief, 5.0 UPS reward
```

---

## CABR Integration (Flow Routing)

### The Critical Rule: CABR Routes, PoB Opens

**UPS is routed from treasury when PoB is validated.** CABR does not create UPS; it sizes the flow pipe.

**Why This Matters**:
- **Prevents gaming**: Multi-agent consensus required
- **Ensures quality**: Better actions = larger routing pipe
- **Ties to value**: PoB-validated work controls release
- **BTC correlation**: Flow is bounded by treasury capacity

### CABR Validation Flow

```
User Action  ->Submit to CABR Oracle
                     ->        Phase 1: Gemma (50ms classification)
        Phase 2: Qwen (200ms strategic analysis)
        Phase 3: Vision DAE (500ms quality check)
                     ->        Consensus = weighted_avg(gemma, qwen, vision)
                     ->        IF consensus >= 0.618 (golden ratio):
            pipe_size = consensus_score
            flow = treasury_release_budget × pipe_size
            Route flow to stakeholders
            Start decay timer
        ELSE:
            Reject (valve stays closed)
```

**Example (GotJunk Item Listing)**:
```python
# User lists item with photo
action = {
    "type": "list_item",
    "photo": photoBlob,
    "description": "Vintage oak desk, good condition",
    "price": 50,
    "location": {lat: 34.05, lon: -118.25}
}

# CABR validation
gemma_score = 0.85  # Good classification (furniture)
qwen_score = 0.75   # No gaming detected, reasonable price
vision_score = 0.90  # High quality photo, real item

# Weighted consensus
consensus = (gemma * 0.30) + (qwen * 0.50) + (vision * 0.20)
consensus = (0.85 * 0.30) + (0.75 * 0.50) + (0.90 * 0.20)
consensus = 0.255 + 0.375 + 0.180 = 0.81

# Check threshold
if consensus >= 0.618:  # PASS
    base_budget = 1.0  # UPS available for this event
    up_flow = base_budget * consensus
    up_flow = 1.0 * 0.81 = 0.81 UPS

    # Route to user's LIQUID wallet
    route_to_liquid_wallet(user_id, up_flow)
```

### Anti-Gaming Patterns Detected

**Qwen Pattern Analysis**:
```python
gaming_patterns = {
    "excessive_listing": {
        "threshold": "> 20 listings/24h",
        "penalty": "Temporary ban 24h"
    },
    "duplicate_descriptions": {
        "threshold": "> 50% identical text",
        "penalty": "Reduce rewards 50%"
    },
    "self_trading": {
        "threshold": "Buyer == Seller pattern",
        "penalty": "Permanent ban"
    },
    "invite_farming": {
        "threshold": "Same IP invites > 70%",
        "penalty": "Void all invite rewards"
    }
}
```

---

## Rogers Diffusion Curve (Continuous S-Curve Release)

### Adoption-Based Token Release

Based on Everett Rogers' **Diffusion of Innovation** theory, implemented as a **continuous sigmoid S-curve**  -no artificial tier boundaries.

```
         tokens_released = 21,000,000  *sigmoid(adoption_score)

100% +------------------------------------------------ Full saturation
     |                                       /
 95% +-----------------------------------/-- Late Majority
     |                             /
 50% +---------------------------/---------- INFLECTION POINT
     |                     /
  5% +-------------------/------------------ Early Adopters
     |             /
  0% +----------------------------------------- Genesis
     +-------------------------------------------
       Adoption Score (0.0  ->1.0)
```

**Key Insight**: Token release follows pure mathematics, not discrete stages.

| Adoption % | Release % | Tokens Available |
|------------|-----------|------------------|
| 0% | 0.00% | 0 |
| 10% | 0.57% | 120,000 |
| 25% | 4.52% | 949,000 |
| **50%** | **50.00%** | **10,500,000** (inflection) |
| 75% | 95.48% | 20,050,000 |
| 100% | 100.00% | 21,000,000 |

**Implementation** (see `modules/foundups/simulator/economics/token_economics.py`):
```python
def adoption_curve(adoption_score: float, steepness: float = 12.0) -> float:
    """Continuous S-curve - no artificial tier jumps."""
    raw = sigmoid(adoption_score, k=steepness, x0=0.5)
    min_val = sigmoid(0.0, k=steepness, x0=0.5)
    max_val = sigmoid(1.0, k=steepness, x0=0.5)
    return (raw - min_val) / (max_val - min_val)
```

### Conceptual Phases (for UX, not token release)
```

### Stage Mechanics

**IDEA Stage** (Innovators):
```yaml
Cohort: "2.5% - Believers & Visionaries"
Supply: 525,000 tokens total
  IDEA:       175,000 (0.83%)
  Proto:      175,000 (0.83%)
  Soft_Proto: 175,000 (0.84%)
Swap_Ratio: "1:1 (best ratio ever)"
Decay_Rate: "0.382x (slowest decay)"
Invites: "5-20 per user"
Benefits:
  - Founder status
  - Maximum ROI potential
  - Governance power
  - Network effects (early liquidity)
```

**MVP Stage** (Early Adopters):
```yaml
Cohort: "13.5% - Early majority believers"
Supply: 2,835,000 tokens
Swap_Ratio: "10:1 (10 UPS = 1 JUNK$)"
Decay_Rate: "0.5x"
Invites: "50 per user"
Benefits:
  - Early adopter badge
  - Significant ROI
  - Growing network
```

**Launch Stage** (Early Majority):
```yaml
Cohort: "34% - Mainstream users"
Supply: 7,140,000 tokens
Swap_Ratio: "100:1 (100 UPS = 1 JUNK$)"
Decay_Rate: "1.0x (standard)"
Invites: "Public (no invites needed)"
Benefits:
  - Mature network
  - Stable ecosystem
  - Full feature set
```

---

## BTC Reserve (Hotel California Model)

### "You can check in, but you can never leave"

BTC flows INTO the reserve from multiple sources. It **never** flows out. This creates an ever-growing backing for UPS value.

**BTC Inflow Sources**:
```yaml
Subscriptions:
  - Spark ($2.95/mo), Explorer ($9.95), Builder ($19.95), Founder ($49.95)
  - Paid in BTC/ETH/SOL/USDC  -ALL converted to BTC reserve

Demurrage_Decay:
  - LIQUID UPS bio-decay  ->decayed amount converted to BTC at floating rate
  - Implementation: modules/foundups/simulator/economics/demurrage.py

Exit_Fees (VAPOR):
  - Mined F_i exit: 11% fee  ->BTC reserve (discourages extraction)
  - Staked F_i exit: 5% fee  ->BTC reserve (value preservation)
  - UPS exit: 15% evaporation  ->80% to BTC reserve, 20% to reservoir

Trading_Fees:
  - F_i order book trades  ->fees to BTC reserve
  - Implementation: modules/foundups/simulator/economics/fi_orderbook.py
```

**BTC-F_i Ratio (Key Economic Metric)**:
```
btc_per_fi = btc_reserve / fi_released

Early ecosystem:  F_i plentiful, BTC/F_i low   (S-curve left)
Mature ecosystem: F_i scarce, BTC/F_i high      (S-curve right)

This mirrors BTC's own halving dynamic:
  S-curve release matches BTC scarcity curve
  Early miners get more tokens per unit work
  Late entrants face higher cost per token
```

**Implementation**: `modules/foundups/simulator/economics/btc_reserve.py` (BTCReserve class)

**Safety Mechanisms**:
```yaml
Circuit_Breaker: Prevents death spirals (modules/foundups/simulator/economics/circuit_breaker.py)
Emergency_Reserve: Ethena-style stability fund (modules/foundups/simulator/economics/emergency_reserve.py)
Rage_Quit: Moloch-style fair exit (modules/foundups/simulator/economics/rage_quit.py)
Bonding_Curve: Guaranteed liquidity AMM (modules/foundups/simulator/economics/bonding_curve.py)
```

---

## Architectural Invariants (012-Confirmed)

These are non-negotiable design constraints confirmed by 012. Do not deviate.

### Dual Backing Models (012-confirmed 2026-02-17)

```
UPS  ->backed by  ->BTC (Hotel California: BTC enters, never exits)

F_i has TWO backing paths:
+------------------------------------------------------------------||STAKED F_i:  UPS swapped  ->F_i                                 ||             The UPS links to FoundUp and backs its F_i        ||             Chain: F_i  ->UPS  ->BTC                            |+-------------------------------------------------------------------､
|MINED F_i:   Earned from 0102 compute work                     ||             Backed by ENERGY (the work itself)                ||             No direct BTC backing  -value is crystallized work|+------------------------------------------------------------------|
Two distinct circulation systems:
- UPS pool: For 012 stakeholders (demurrage forces velocity, returns to pool)
- F_i pool: For 0102 agents (21M per FoundUp, S-curve release as FoundUp grows)

CABR = Pipe Size (0.0-1.0): Controls how much UPS flows from Treasury to FoundUp
V3 = Valve: Opens when work is validated (Proof of Benefit)
```

**The "it is and it isn't" nuance**: Staked F_i IS backed by BTC (via UPS).
Mined F_i is NOT backed by BTC  -it represents crystallized compute energy.

### Blockchain Agnostic

- F_i tokens are **native pAVS tokens**, not ERC-20 or chain-specific
- `TokenFactoryAdapter` abstracts the blockchain backend
- No Polygon, no Mumbai, no chain-locked smart contracts
- Chain selection is a deployment decision, not an architectural one

### F_i Swap Path

```
F_i --> UPS --> external (BTC/ETH/SOL/USDC)

F_i can ONLY be swapped into UPS (not directly to external).
This forces all exits through the UPS liquidity layer.
```

### V3 Real-Time Consensus

- CABR V3 (Valuation) produces **real-time consensus scores** (0-1)
- NOT quarterly reporting, NOT batch processing
- Every PoB event gets an immediate V3 score
- See WSP 29 Section: "The 3V Engine Pattern"

### Proof of Benefit (PoB)

Six economic FAM events constitute Proof of Benefit:

| FAM Event | PoB Meaning | CABR Input |
|-----------|-------------|------------|
| `proof_submitted` | "I did work" | task_completion_rate |
| `verification_recorded` | "Work was confirmed" | verification_participation |
| `payout_triggered` | "Tokens transferred" | task_completion_rate |
| `milestone_published` | "Achievement recorded" | governance_engagement |
| `fi_trade_executed` | "Market activity" | cross_foundup_collaboration |
| `investor_funding_received` | "Capital committed" | governance_engagement |

These feed CABR `part_score` at trust 1.0. Full spec: [WSP 29: CABR Engine](../../../WSP_framework/src/WSP_29_CABR_Engine.md)

### Layer Architecture

```
Layer 0: BTC (reserve backing  -Hotel California)
Layer 1: Smart contracts (chain-agnostic via TokenFactoryAdapter)
Layer 2: Off-chain agent operations (0102 agents, FAM DAEmon, CABR scoring)
```

---

## Mesh Network Integration

### Storage Rewards (WSP 98 Integration)

**IPFS Hosting Rewards**:
```yaml
Mechanism: "Host item photos on IPFS  ->Earn UPS"
Validation: "Merkle proof of storage"
Reward: "0.01 UPS per file served to peer"
CABR_Check: "Uptime > 95%, no fake serves"

Example:
  User hosts 1000 item photos
  Average 10 serves per photo per month
  Earnings: 1000  *10  *0.01 = 100 UPS per month
```

**Mesh Coordination**:
```javascript
// modules/foundups/gotjunk/frontend/App.tsx
import { MeshDAE } from '@foundups/mesh-core';

const gotjunkMesh = new MeshDAE({
  foundupId: 'gotjunk',
  capabilities: ['storage', 'discovery'],
  rewards: {
    storage: 0.01,  // UPS per file served
    discovery: 0.001  // UPS per peer discovered
  }
});

// Auto-earn UPS for hosting
gotjunkMesh.on('file_served', async (event) => {
  // CABR validates serving
  const validation = await cabr.validate({
    type: 'host_storage',
    proof: event.merkleProof,
    uptime: event.uptimePercent
  });

  if (validation.passed) {
    // Route UPS reward from treasury
    await routeUPSFromTreasury(user.id, validation.upAmount);
  }
});
```

---

## Mathematical Formulas

### Adaptive Decay (Michaelis-Menten)

```
lambda(t) = lambda_min + (lambda_max - lambda_min) * (D / (K + D))

Where:
  lambda(t) = decay rate at time t
  D = days inactive
  K = 7 (half-maximal constant)
  lambda_min = 0.005/day (0.5% monthly)
  lambda_max = 0.05/day (5% monthly)
```

**Circadian Pulse**:
```
if is_pulse_window(local_time):  # 6-7 PM
    lambda(t) *= 1.30  # 30% boost
```

**Exponential Decay**:
```
U(t) = U_0 * e^(-lambda(t)*t)

Where:
  U(t) = value at time t
  U_0 = initial value
  t = time in days
```

### UPS Floating Value Model

```
ups_per_btc = total_ups_circulating / total_btc_reserve

Where:
  total_ups_circulating = cumulative circulating UPS routed from treasury
  total_btc_reserve = BTC accumulated (Hotel California  -never exits)

Value dynamics:
  More BTC accumulated  ->ups_per_btc decreases  ->each UPS worth more BTC
  More UPS routed into circulation  ->ups_per_btc increases  ->each UPS worth less BTC
  Bio-decay removes UPS from circulation  ->ups_per_btc decreases  ->deflation

Implementation: modules/foundups/simulator/economics/btc_reserve.py (BTCReserve.ups_per_btc)
```

### BTC-F_i Ratio (Economic Health Metric)

```
btc_per_fi = btc_reserve / fi_released

This ratio should INCREASE over time:
  - BTC reserve grows (Hotel California  -inflows from fees, decay, exits)
  - F_i release follows S-curve (scarcer over time)
  - Combined effect: each F_i becomes more BTC-backed

Tracked in simulator: mesa_model.py records snapshots every 50 ticks
Implementation: BTCReserve.total_btc / adoption_curve(score) * 21_000_000
```

---

## Founding Members + Anonymous Stakers (Du 4% Pool)

The Du 4% pool is unique: it's **PASSIVE**  -participants earn every epoch without requiring active work.

### Who Qualifies

| Category | Requirements | Access |
|----------|-------------|--------|
| **Founding Member** | Active subscription (any tier) | Du pool |
| **Anonymous Staker** | BTC locked in contract | Du pool |
| **Genesis Member** | Joined before launch | ALL FoundUps ecosystem-wide |
| **Future Participant** | Joined after launch | Only FoundUps they work on |

**FOMO**: Genesis member class CLOSES at launch. Join now or miss forever.

### Degressive Tier Model (Prevents Infinite Extraction)

As stakers earn more, their share naturally decreases:

```
Earned/Staked Ratio    Activity Tier    Pool Share
-------------------------------------------------
< 10x                  du (tier 2)      80% of 4% = 3.2%
10x - 100x             dao (tier 1)     16% of 4% = 0.64%
> 100x                 un (tier 0)       4% of 4% = 0.16%
```

**Lifetime floor**: Even after 100x return, stakers still share in 0.16% of total F_i (never lose access).

**Math**: Each tier share is divided by count at that tier:
```python
individual_share = (pool  *tier_percentage) / count_at_tier

# Example: 10 stakers at du tier, 100 F_i epoch
# du_tier_share = (4  *0.80) / 10 = 0.32 F_i each
```

### Passive vs Active Earning

| Pool | Mode | Trigger | Who |
|------|------|---------|-----|
| **Du (4%)** | PASSIVE | Every epoch | Founding members + stakers |
| **Dao (16%)** | ACTIVE | Per 3V task | 0102 agents |
| **Un (60%)** | ACTIVE | Per engagement | 012 stakeholders |

**Implementation**: `modules/foundups/simulator/economics/pool_distribution.py` (StakerPosition, ComputeMetrics)

### Agent Compute Weight (Dao 16% Pool)

0102 agents earn F_i scaled by compute cost:

```python
fi_earned = base_rate  *v3_score  *compute_weight

# Compute weight = (tokens_used / 1000)  *tier_factor
TIER_WEIGHTS = {
    "opus": 10.0,    # Heavy compute  ->more F_i
    "sonnet": 3.0,   # Medium compute
    "haiku": 1.0,    # Light compute (baseline)
    "gemma": 0.5,    # Local inference
    "qwen": 0.5,     # Local inference
}
```

### Epoch Timing

| Cycle | Interval | Purpose |
|-------|----------|---------|
| Mini-epoch | 10 ticks | Demurrage (bio-decay) |
| Epoch | 100 ticks | Du pool distribution (passive) |
| Macro-epoch | 900 ticks | BTC-F_i ratio snapshot |
| Event | Real-time | Dao/Un payouts (per 3V task) |

**Implementation**: `modules/foundups/simulator/config.py` (epoch timing constants)

---

## Early Capital Provider Economics

> **IMPORTANT DISTINCTION (CABR/PoB Paradigm):**
> This section describes **I_i token holders** via Bitclout-style bonding curve.
> This is DIFFERENT from **Du pool stakers** (protocol participants):
> - Du Pool Stakers = CABR/PoB terminology (distribution ratio, allocations)
> - I_i Holders = Traditional terminology (returns, multiples) - may require separate legal review

**Full specification**: See [INVESTOR_ECONOMICS.md](../../foundups/simulator/economics/INVESTOR_ECONOMICS.md)

### Bitclout-Inspired Bonding Curve

Early investors receive **I_i (Investor Tokens)** priced on a quadratic bonding curve (same model as BitClout/DeSo's $200M raise from a16z, Sequoia):

```yaml
Price_Formula: "P = k  *supply^n"
Parameters:
  k: 0.0001  # Price constant (BTC per token at supply=1)
  n: 2       # Quadratic (Bitclout-style)
```

### BTC Escrow Model ("Dry Wallet")

Investor BTC is **escrowed**, not spent immediately:

```
Investor BTC  ->Dry Wallet (Escrow)
                     ->              Sequestered for 3 years
                     ->              [CHOICE POINT at Year 3]
                     ->    +----------------+---------------|     ->               ->               -> BUYOUT         PARTIAL          HOLD
 (10x)          (50/50)        (100x+)
```

### Stakeholder Pool Participation (12.16%)

Investors participate at **DAO activity level** in the Token Pool Matrix:

```
Pool Structure (WSP 26 Section 6.3-6.4):
  Stakeholders 80%:  Un(60%) + Dao(16%) + Du(4%)
  Network 20%:       Network(16% drip) + Fund(4% held)

Activity tiers (share within each pool, divided by count at tier):
  du(2)  = 80% of pool  (founding members + stakers  -PASSIVE)
  dao(1) = 16% of pool  (investors at DAO level)
  un(0)  =  4% of pool  (degressive floor after 100x return)

Pool earning modes:
  Du (4%):   PASSIVE  -Founding members/stakers earn every epoch
  Dao (16%): ACTIVE  -0102 agents earn per 3V task completion
  Un (60%):  ACTIVE  -012 stakeholders earn per FoundUpCube engagement

Investor DAO-level access:
                 Un(60%)  Dao(16%)  Du(4%)
-----------------------------------------------
dao level:       9.60%    2.56%     0.64%

TOTAL: 12.16% of ALL FoundUp token distributions!
```

**Implementation**: `modules/foundups/simulator/economics/pool_distribution.py` (PoolDistributor class)

**Example** (100 FoundUps, 720M F_i/year):
- Annual to investor pool: 87,552,000 F_i
- 5-year: 437,760,000 F_i
- Seed investor (46% of pool): 203M F_i

### Return Projections

| Round | BTC In | Pool % | 5Y F_i | Return |
|-------|--------|--------|--------|--------|
| Pre-Seed | 0.5 | 15% | 65M | **6,000x** |
| Seed | 10 | 46% | 203M | **1,600x** |
| Series A | 50 | 20% | 88M | **118x** |

### The Hybrid Exit Model

> "The floor is 10x. The ceiling is 1000x. You choose."

### Investment Rounds (Total: 755 BTC / ~$75.5M)

| Round | BTC Range | Target |
|-------|-----------|--------|
| Pre-Seed | 0.1-1 BTC | 5 BTC |
| Seed | 1-10 BTC | 50 BTC |
| Series A | 10-50 BTC | 200 BTC |
| Series B | 50-100 BTC | 500 BTC |

### Simulator Implementation

```python
from modules.foundups.simulator.economics import (
    InvestorPool, bonding_price, bonding_tokens_for_btc
)

pool = InvestorPool(k=0.0001, n=2.0)
tokens, tier = pool.invest_btc("investor_1", btc_amount=10.0)
returns = pool.get_investor_returns("investor_1")
# returns['price_return_multiple']  ->1,600x for seed
```

---

## pump.fun Benchmark Calibration (2026-02-17)

Our fee model is calibrated against **pump.fun** as a market benchmark.
This is a sizing reference, not proof that pAVS will achieve the same volume profile.

### pump.fun Actual Metrics (Jan 2024 - Feb 2026)

| Metric | pump.fun (Actual) | pAVS (Scenario Projection) |
|--------|-------------------|------------------|
| Fee Rate | 1.25% | 2% + exit + creation |
| Daily Revenue | $3.5M (~35 BTC) | $6.5M (~65 BTC) |
| Monthly Revenue | $105M (~1,050 BTC) | $194M (~1,940 BTC) |
| Annual Revenue | $1.28B (~12,775 BTC) | $2.35B (~23,574 BTC) |
| Cumulative (13mo) | $800M | N/A |

**Sources**: CoinMarketCap, Blockworks, TheBlock, DefiLlama
**Conservative interpretation**: F_0 operating sustainability is gated on **captured pAVS treasury share** (not gross ecosystem fees), minimum sample window, and active FoundUp count.

### pAVS Revenue Multiplier

pAVS generates **1.8x more revenue** per unit volume because:
1. Higher trading fee (2% vs 1.25%)
2. Exit fees (2-15% based on vesting)
3. Creation fees (3% staked, 11% mined)

### Implementation

- `fee_revenue_tracker.py`  -Tracks DEX/exit/creation fees
- `tide_economics.py`  -IMF-like ecosystem balancing
- Mesa model integration  -Fee recording on every trade
- FAM events  -`fee_collected`, `tide_in`, `tide_out`, `sustainability_reached`

---

## Full Tide Economics (IMF-like Balancing)

**012 Insight**: "The system lends and returns ebbing like a tide... no competition - blue ocean strategy"

### Tide Mechanics

```
TIDE OUT: OVERFLOW F_i (>100% reserve) drip 1%/epoch  ->Network Pool
TIDE IN: Network Pool supports CRITICAL F_i (<5% reserve)
```

### Self-Sustainability Threshold (Conservative)

For investor-grade gating we use:
- pAVS capture ratio (`pavs_treasury` only) as the primary operating coverage metric.
- Minimum sample window (>= 1 simulated day and >= 25 active FoundUps).
- Dynamic break-even estimate based on observed per-FoundUp capture (fallback to 3,500 when sample is immature).
- Stress scenario gate (downside/base/upside) with confidence bands.
- Claim rule: downside `p10` revenue/cost ratio must be `>= 1.0`.

Scenario table below remains a planning reference:

| FoundUps | Monthly Revenue | Monthly Cost | Status |
|----------|-----------------|--------------|--------|
| 110 (Genesis) | $56K | $144K | DEFICIT |
| 3,500 | $12M | $12.4M | ~Break-even |
| 20,000 | $97M | $72M | **SURPLUS** |
| 105,000 | $645M | $384M | **SURPLUS** |

**Key Insight**: Bootstrap capital is RUNWAY to reach scale. The 3,500 FoundUp break-even number is now treated as a fallback prior; runtime estimates should be read from simulator metrics.

### Scenario Pack (Defendable Claim Control)

Simulator now computes a stress scenario pack each run:
- `downside` (lower demand + thinner depth + higher volatility)
- `base`
- `upside`

Each lane emits confidence bands (`p10/p50/p90`) and revenue/cost ratios.
Self-sustaining claims are gated by **downside `p10` pass**, not base case only.

Projection export now includes:
- `annual_revenue_btc` (gross fee flow),
- `annual_revenue_protocol_capture_btc`,
- `annual_revenue_platform_capture_btc`,
- combined gross/protocol/platform/net lanes,
- a deterministic `compute_graph` payload (tier weights -> human-hours/sats/F_i equivalents).
- sustainability gating ratios are platform-capture adjusted before claim checks.

---

## Implementation Roadmap

### Phase 1: Design (COMPLETE)
- [x] Architecture design
- [x] Mathematical modeling
- [x] WSP integration
- [x] Documentation

### Phase 2: Simulator Economics (COMPLETE)
- [x] `token_economics.py`  -S-curve adoption, dual-token model
- [x] `btc_reserve.py`  -Hotel California BTC reserve
- [x] `demurrage.py`  -Bio-decay (Michaelis-Menten)
- [x] `pool_distribution.py`  -Un/Dao/Du epoch rewards
- [x] `fi_orderbook.py`  -F_i buy/sell order book
- [x] `circuit_breaker.py`  -Death spiral prevention
- [x] `bonding_curve.py`  -Guaranteed liquidity AMM
- [x] `rage_quit.py`  -Moloch-style fair exit
- [x] `emergency_reserve.py`  -Ethena-style stability fund
- [x] `investor_staking.py`  -Bitclout bonding curve
- [x] `investor_liability.py`  -Buyout coverage engine
- [x] `fee_revenue_tracker.py`  -DEX/exit/creation fee tracking (pump.fun validated)
- [x] `tide_economics.py`  -IMF-like ecosystem balancing (Full Tide)
- [x] Mesa model integration with DemurrageEngine + BTCReserve + PoolDistributor + FeeTracker + TideEngine

### Phase 3: Smart Contracts - Blockchain Agnostic (PENDING)
- [ ] TokenFactoryAdapter (chain-agnostic abstraction layer)
- [ ] F_i token contract template (21M cap per FoundUp)
- [ ] CABR Oracle integration (V1/V2/V3 pipeline)
- [ ] Testnet deployment (chain TBD  -NOT locked to any L1/L2)

### Phase 4: Frontend Integration (PENDING)
- [ ] Decay notifications UI
- [ ] Stake/unstake components
- [ ] CABR validation feedback
- [ ] Invite system

### Phase 5: Production (PENDING)
- [ ] Security audit
- [ ] Mainnet deployment
- [ ] GotJunk IDEA stage launch
- [ ] Monitor & iterate

---

## Conclusion

FoundUps tokenomics creates a **self-sustaining, anti-hoarding, quality-driven economy** where:

1. **Value Creation** = CABR-validated beneficial actions
2. **Value Capture** = BTC accumulation on fees
3. **Value Distribution** = Active participants rewarded, inactive decay
4. **Value Stability** = Hotel California BTC reserve (grows forever, never exits)

**Result**: Solo founders can build unicorn-scale FoundUps without VC funding, employees, or centralized infrastructure.

---

**For Implementation Details**:
- CABR Integration: [CABR_INTEGRATION.md](./CABR_INTEGRATION.md)
- Module README: [../README.md](../README.md)
- ModLog: [../ModLog.md](../ModLog.md)
- WSP 26: [WSP_26_FoundUPS_DAE_Tokenization.md](../../../WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md)
