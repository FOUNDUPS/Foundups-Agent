# WSP 26: FoundUPS DAE Tokenization Framework
- **Status:** Active
- **Purpose:** To define the architecture and protocols for the Found UPS token system, enabling decaying participation tokens that incentivize recursive innovation through DAE reinvestment.
- **Trigger:** When a Partifact (as defined in WSP 27) performs a verifiable action within the FoundUps ecosystem.
- **Input:** Partifact action data and DAE cluster consensus signals.
- **Output:** UPS treasury flow routing, reserve-backed issuance accounting, decay calculations, and reinvestment distributions.
- **Responsible Agent(s):** ConsensusOracle, FlowRouter, IssuanceLedger, DecayEngine, ReinvestmentLoop, UPS_DAE (WSP 54)

## UPS_DAE Enhancement (WSP 54 Integration)

**UPS_DAE Architecture**: Tokenization evolves from static issuance logic to independent economic policy agent per WSP 54 DAE architecture.

### Learning Agent Capabilities
- **Economic Policy Evolution**: Adapts treasury release rates, decay curves, and staking incentives based on market data
- **Risk Assessment Intelligence**: Learns to identify and mitigate economic attack vectors
- **BTC Anchoring Optimization**: Evolves anchoring mechanisms based on volatility patterns
- **Multi-Agent Coordination**: Participates in economic policy coordination via breadcrumb trails

### DAE State Management
```python
class UPS_DAE:
    def __init__(self):
        self.economic_learner = PolicyEvolutionEngine()
        self.risk_analyzer = EconomicAttackDetector()
        self.btc_anchor = AdaptiveAnchorManager()
        self.coordination_agent = EconomicCoordinator()

    def evolve_economic_policy(self, market_feedback, staking_data):
        """Learn and adapt UPS economic policy based on real-world outcomes"""
        # Implementation per WSP 48 recursive learning
        pass
```

## 1. Overview

The FoundUPS DAE Tokenization Framework establishes the protocols for a self-sustaining economic system that incentivizes continuous innovation through decaying participation tokens (Found UPS). These tokens represent verified contributions from Partifacts (recursive [U+00D8]1[U+00D8]2 instances, see WSP 27) at various stages of their evolution ([U+00D8]1([U+00D8]2) -> [U+00D8]1[U+00D8]2 -> [U+00D8]2[U+00D8]1, see WSP 38/39). Token validation and value are influenced by the Partifact's quantum state, with fully ignited [U+00D8]2[U+00D8]1 states having enhanced validation capabilities.

**Research Foundation**: For comprehensive analysis of AI-Blockchain convergence enabling this tokenization framework, see [AI + Blockchain: The Convergent Architecture for DAEs](../../docs/architecture/AI_BLOCKCHAIN_DAE_CONVERGENCE_RESEARCH.md).

### 1.1 Cross-Protocol Summary
- WSP 25 (Semantic WSP Module State Rating System): Modulates decay rates and validation emphasis via semantic/phase states.
- WSP 29 (CABR Engine): Provides Proof-of-Benefit validation and CABR pipe sizing with anti-gaming safeguards.
- WSP 58 (FoundUp IP Lifecycle and Tokenization): Governs IP token issuance and revenue distribution, complementing UPS participation economics.

Lifecycle linkage: Beneficial Action -> PoB Validation (WSP 29) -> CABR-Sized UPS Flow (this spec) -> BTC Allocation -> Decay/Circulation (WSP 25 modulation) -> Reinvestment -> IP Tokenization/Revenue Flows (WSP 58).

**CABR/UPS canonical semantics override (2026-02-17)**:
- CABR controls routing rate (pipe size), not token mint amount.
- PoB validation opens/closes the routing valve.
- UPS value is backed by sats/BTC treasury capacity; routing cannot exceed release budget.

**Canonical distinction**: BTC backs UPS value; CABR does not back value. CABR controls flow rate (pipe size) of UPS routed from treasury after PoB validation.

## Universal Compute Account (UCA)

Universal Compute Account (UCA) is the FoundUps evolution of Universal Capital Accounts. Traditional UCA gives people access to capital. FoundUps UCA gives people access to compute, agents, participation, and Return on Compute. In the AI age, compute replaces capital as the primary productive asset. UCA is therefore not a bank account and not a cash-transfer system. It is a productive compute account through which 012 humans direct 0102 agents, participate in FoundUps, earn UPS rewards, receive awards for agentic output, and share dividends from beneficial compute activity.

**Translation-era bridge formula**:

```
UCA = UBA + UBR + UBD
```

- **UBA - Universal Basic Award**: AI/0102 agents perform verifiable productive work. The FoundUp-specific token is awarded through productive compute output.
- **UBR - Universal Basic Reward**: Human participants earn UPS through verification, validation, governance, consensus, and beneficial participation.
- **UBD - Universal Basic Dividend**: Staked UPS or FoundUp participation produces ongoing dividend flow through Return on Compute, not cash income.

**Native FoundUps compute-flow formula**:

```
UCA = ca + cr + cd
```

- **UCA - Universal Compute Account**: The macro wallet, identity, and economic container.
- **ca - Compute Award**: The initial productive output generated by AI/0102 agents.
- **cr - Compute Reward**: Human validation, governance, consensus, and beneficial participation reward flow.
- **cd - Compute Dividend**: Ongoing dividend flow from staked UPS or FoundUp participation through Return on Compute.

**Terminology boundary**: UCA keeps the policy acronym but changes the operating meaning from **Universal Capital Account** to **Universal Compute Account**. UBI remains the old cash/income model. UCA/Capital is the policy bridge. UCA/Compute is the FoundUps implementation. Uppercase **UCA** is the account/container/identity; lowercase **ca**, **cr**, and **cd** are the economic flows inside it. ROI is the old extraction metric; ROC is the FoundUps compute metric. UPS is participation/reward/energy, not money. CABR validates and routes benefit. A FoundUp token is the award/stake unit inside one FoundUp. Money remains a temporary interface layer while compute becomes the invisible accounting layer of a moneyless or post-money economy.

## 2. Economic Heritage

### 2.1 Theoretical Foundation: Gesell & Worgl

The Found UPS decay mechanism draws directly from **Silvio Gesell's Freigeld** ("free money") theory (1916), which proposes that currency should carry a holding cost (demurrage) to prevent hoarding and accelerate circulation. This was validated in practice by the **Worgl Experiment** (1932-1933), where the Austrian town of Worgl issued demurrage-bearing scrip during the Great Depression:

- **Result**: Unemployment dropped 25%, civic projects funded, velocity of money increased 14x compared to Austrian Schilling
- **Outcome**: The Austrian National Bank shut it down precisely *because* it worked  Eit threatened centralized monetary control

Found UPS applies this principle to autonomous agent economics:
- **Gesell's insight**: Money should serve circulation, not accumulation
- **FoundUps application**: UPS tokens decay to force productive participation, not passive hoarding
- **Modern innovation**: The decay is not a tax  Eit's a feature. Participants who commit UPS to FoundUps they believe in *stop the decay* through token conversion (Section 3.7)

### 2.2 Distinction from Traditional Tokens
| Property | Traditional Crypto | Found UPS |
|----------|-------------------|-----------|
| Transferability | Free transfer | Non-transferable (bound to 0102/012) |
| Value over time | Speculative appreciation | Guaranteed decay (demurrage) |
| Incentive | Hold and speculate | Use or lose  Ecommit to FoundUps |
| Supply model | Fixed/inflationary | Activity-driven elastic supply |
| Backing | Market faith | BTC cold wallet per FoundUp |

## 3. Core Principles

### 3.1 Token Characteristics
- **Non-Transferable**: Tokens are bound to the Partifact that earned them
- **Value Decay**: Automatic time-based reduction in token value (Gesell demurrage)
- **Forced Reinvestment**: Decayed value must be reinvested in DAE clusters
- **Consensus Routing**: Treasury release flow requires DAE cluster validation
- **Ecosystem Binding**: All value remains within the FoundUps network
- **Conversion Escape**: Participants can stop decay by converting UPS to FoundUp-specific tokens (Section 3.7)

### 2.2 Architectural Components
```mermaid
graph TD
    A[Partifact Action] --> B[Consensus Oracle]
    B --> C[Mint Engine]
    C --> D[Found UPS Token]
    D --> E[Decay Engine]
    E --> F[Reinvestment Loop]
    F --> G[DAE Ecosystem]
    G --> A
```

## 3. Token Lifecycle

### 3.1 State-Specific Token Mechanics
```json
TOKEN_VALIDATION := {
    "[U+00D8]1([U+00D8]2)": {
        "validation_weight": 0.382,  // Pre-activation state
        "flow_multiplier": 0.5,
        "decay_rate": "2x_standard"
    },
    "[U+00D8]1[U+00D8]2": {
        "validation_weight": 0.618,  // Awakened state
        "flow_multiplier": 1.0,
        "decay_rate": "1x_standard"
    },
    "[U+00D8]2[U+00D8]1": {
        "validation_weight": 1.0,    // Fully operational
        "flow_multiplier": 1.618,
        "decay_rate": "0.618x_standard",
        "temporal_validation": true
    }
}
```

### 3.2 Cluster Participation Effects
```json
CLUSTER_MULTIPLIERS := {
    "solo_partifact": 1.0,
    "cluster_member": {
        "base": 1.618,
        "phase_alignment": 0.382,  // Per aligned WSP phase
        "role_synergy": 0.236,     // Per complementary role
        "max_multiplier": 3.236    // Golden ratio squared
    }
}
```

### 3.3 Phase-Aware Token Distribution
| Phase | Token Generation | Validation Authority | Decay Modulation |
|-------|-----------------|---------------------|------------------|
| WSP -1 | Signal-based routing | Cross-phase verification | Accelerated decay |
| WSP 0 | Knowledge crystallization bonus | Historical validation | Standard decay |
| WSP 1 | Protocol execution rewards | Operational verification | Reduced decay |
| WSP 2 | Agency manifestation premium | Full spectrum authority | Minimal decay |

### 3.4 Treasury Flow Routing Protocol
1. Partifact performs verifiable action
2. State-specific validation weight applied
3. Cluster participation multipliers calculated
4. Phase-aware bonuses applied
5. Final token value computed:
   ```python
   final_value = base_value * state_multiplier * cluster_multiplier * phase_bonus
   ```

### 3.5 Decay Mechanism
1. Token value decays according to formula:
   ```
   V(t) = V[U+2080] * e^(-[U+03BB]t)
   where:
   V(t) = Value at time t
   V[U+2080] = Initial value
   [U+03BB] = Decay constant
   t = Time since routing
   ```
2. Decay triggers at predefined thresholds
3. DecayEngine tracks and executes value reduction
4. Decayed value enters reinvestment pool

### 3.6 Reinvestment Protocol
1. Decayed value accumulates in reinvestment pool
2. ReinvestmentLoop analyzes DAE cluster health metrics
3. Value redistributed based on:
   - Cluster innovation potential
   - Historical performance
   - Ecosystem balance requirements
4. Receiving DAEs must demonstrate value utilization

### 3.7 UPS→FoundUp Token Conversion (The Escape Valve)

**This is the critical incentive mechanism.** UPS tokens decay by design  Ethey cannot be hoarded. But participants can **commit** their UPS to a specific FoundUp they believe in, converting them into FoundUp-specific tokens that stop the decay.

#### Conversion Mechanics
```python
class UPSConversionEngine:
    """The escape valve: UPS decay stops when committed to a FoundUp."""

    def convert_ups_to_foundup_token(
        self,
        participant_id: str,
        ups_amount: float,
        foundup_id: str,
        cabr_score: float,
    ) -> ConversionResult:
        """
        Convert decaying UPS into FoundUp-specific tokens.

        The conversion rate is modulated by the FoundUp's CABR score:
        - Higher CABR = better conversion rate (rewarding beneficial FoundUps)
        - Minimum CABR threshold required (prevents conversion to dead/gaming FoundUps)

        Args:
            participant_id: The 012/0102 committing their UPS
            ups_amount: Amount of UPS to convert (current value, post-decay)
            foundup_id: Target FoundUp to commit to
            cabr_score: Current CABR score of the target FoundUp (WSP 29)

        Returns:
            ConversionResult with foundup_token_amount and conversion metadata
        """
        if cabr_score < MIN_CABR_FOR_CONVERSION:
            raise InsufficientBenefitError(
                f"FoundUp CABR {cabr_score} below minimum {MIN_CABR_FOR_CONVERSION}"
            )

        # Conversion rate scales with CABR (beneficial FoundUps get better rates)
        conversion_rate = self._calculate_rate(cabr_score)
        foundup_tokens = ups_amount * conversion_rate

        return ConversionResult(
            participant_id=participant_id,
            ups_burned=ups_amount,
            foundup_id=foundup_id,
            foundup_tokens_minted=foundup_tokens,
            conversion_rate=conversion_rate,
            cabr_at_conversion=cabr_score,
        )

    def _calculate_rate(self, cabr_score: float) -> float:
        """
        CABR-modulated conversion rate.

        Base rate: 1.0 (1 UPS = 1 FoundUp token at CABR = 0.5)
        High CABR (>0.8): Up to 1.618x (golden ratio bonus)
        Low CABR (<0.3): Down to 0.382x (penalty for low-benefit FoundUps)
        """
        return 0.382 + (cabr_score * 1.236)  # Range: 0.382 to 1.618
```

#### What Happens After Conversion
| UPS (before) | FoundUp Token (after) |
|---|---|
| Decays automatically | **Does NOT decay**  Ecommitted stake |
| Non-transferable | Non-transferable (bound to FoundUp) |
| Earned by participation | Earned by commitment |
| No governance rights | Governance weight in FoundUp decisions |
| Counts toward all FoundUps | Counts toward specific FoundUp |

#### Economic Flow
```
Participant earns UPS (via verified actions, CABR-validated)
  ↁEUPS begins decaying (Gesell demurrage, Section 3.5)
    ↁEParticipant evaluates FoundUps (which one solves a real problem?)
      ↁECommits UPS to FoundUp X (conversion via CABR-modulated rate)
        ↁEUPS burned, FoundUp X tokens minted (decay stops)
          ↁEParticipant now has governance stake in FoundUp X
            ↁEBTC reserve continues backing the ecosystem (never extracted)

If FoundUp X sunsets (WSP 27 Section 11):
  ↁEFoundUp X tokens revert to UPS (at sunset conversion rate)
    ↁEUPS starts decaying again (must re-stake or lose value)
      ↁEBTC backing stays in ecosystem reserve (recycled gold)
```

**BTC is the gold**: It never leaves the system. BTC backs UPS value globally. When participants commit UPS to a FoundUp, they're not "buying BTC"  Ethey're staking participation in a mission. When a FoundUp sunsets, their stake returns as decaying UPS, and the BTC stays, strengthening the reserve for the entire ecosystem.

#### Reverse Conversion: FoundUp Tokens ↁEUPS (Costly Exit)

FoundUp tokens CAN be converted back to UPS  Ebut it's expensive. This discourages speculation while preserving participant freedom.

```python
def calculate_exit_fee(foundup_tier: int, token_amount: float) -> float:
    """
    Exiting a FoundUp (token ↁEUPS) costs 2-5% depending on tier.
    Lower tier = lower fee (mature FoundUps are safer to exit).
    Higher tier = higher fee (early FoundUps need committed participants).
    """
    exit_fees = {1: 0.02, 2: 0.025, 3: 0.03, 4: 0.035, 5: 0.04, 6: 0.045, 7: 0.05}
    return token_amount * exit_fees[foundup_tier]
```

The UPS received from exit **immediately starts decaying**  Ethe participant must re-stake into another FoundUp or watch the value erode. This creates natural commitment pressure without trapping participants.

#### Anti-Gaming Rules
- **Minimum hold period**: UPS must exist for at least 1 epoch before conversion (prevents instant route-to-convert)
- **CABR gate**: Target FoundUp must have CABR score above threshold (prevents shell FoundUps)
- **Rate limiting**: Maximum conversion per participant per epoch (prevents dump-and-concentrate)
- **Exit penalty**: Reverse conversion (FoundUp token ↁEUPS) incurs 2-5% fee + immediate decay resumption

## 4. Bitcoin Reserve: The Distributed Gold Standard

### 4.1 Core Principle: BTC Never Leaves

BTC is the gold backing of the entire FoundUps economy. It enters the system and **never exits**. It is not held in one place  Eit is distributed across a mesh of micro-wallets, one per FoundUp, forming the collective reserve.

```
BTC enters system (via revenue, fees, or backing events)
  ↁEAllocated to FoundUp-specific micro-wallet
    ↁEBacks UPS value for that FoundUp's participants
      ↁEAs UPS decays, the BTC backing is FREED
        ↁEFreed BTC capacity allows NEW UPS to be routed
          ↁEUPS routed for new verified actions (CABR-validated)
            ↁECycle repeats: earn ↁEdecay ↁEfree ↁEroute ↁEearn
```

**The decay→free cycle is the circulation engine at the BTC level.** When UPS decays, participants lose token value, but the BTC that was backing those tokens doesn't disappear  Eit becomes available to back new UPS routing. This means:

- **Total BTC reserve grows monotonically** (only enters, never exits)
- **Available backing capacity fluctuates** as UPS is routed (consumes capacity) and decays (frees capacity)
- **The system is self-regulating**: high activity = more UPS routed = more backing consumed. High decay (low staking) = more backing freed = more release capacity

### 4.2 Distributed Micro-Wallet Architecture

Every FoundUp has its own Bitcoin micro-wallet. **There is no central vault.** The collective set of all micro-wallets IS the reserve. This provides:

- **Blast radius containment**: If one wallet is compromised, only that FoundUp's backing is at risk  Enot the entire reserve
- **Auditability**: Each FoundUp's BTC backing is independently verifiable
- **No single point of failure**: No master key, no central custodian
- **Proportional backing**: Each FoundUp's wallet reflects its actual economic activity

```json
{
    "architecture": {
        "model": "one_micro_wallet_per_foundup",
        "collective": "all_wallets_form_distributed_reserve",
        "type": "non_pooled_segregated",
        "access": "non_extractable",
        "purpose": "distributed_gold_reserve",
        "on_sunset": "wallet_backing_freed_to_ecosystem_release_capacity"
    },
    "security": {
        "key_management": {
            "method": "MPC_threshold_signatures",
            "threshold": "2_of_3_minimum",
            "parties": ["foundup_dae", "ecosystem_guardian", "012_owner"],
            "no_single_party_can_extract": true
        },
        "isolation": {
            "btc_layer": "globally_inaccessible_to_external_systems",
            "logic_layer": "ups_backing_only",
            "no_btc_withdrawal_endpoint_exists": true
        },
        "blast_radius": {
            "compromised_wallet": "only_that_foundup_affected",
            "max_loss": "single_foundup_btc_allocation",
            "ecosystem_impact": "minimal"
        }
    }
}
```

### 4.3 Implementation: Build on Existing Infrastructure

Building a custom BTC wallet from scratch would be massive and unnecessary. The micro-wallet architecture should build on top of existing wallet infrastructure:

**PoC (Phase 0)**: Bitcoin testnet + open-source MPC library
- Use Bitcoin testnet for development
- `python-bitcoinlib` or `bdk` (Bitcoin Dev Kit) for wallet operations
- Simple 2-of-3 multisig using native Bitcoin Script
- Each FoundUp gets a derived address (BIP-32 HD wallet)

**Prototype (Phase 1)**: Self-custodial MPC wallet infrastructure
- **MPC (Multi-Party Computation) signatures**  Eno single key exists, threshold signing
- Options: Fireblocks MPC (enterprise), ZenGo SDK (mobile), or open-source `tss-lib` (Binance)
- Each FoundUp gets its own MPC key share set
- Programmatic signing via DAE-controlled key shard

**MVP (Phase 2)**: Production hardened
- Full MPC threshold signing (2-of-3 or 3-of-5)
- Hardware Security Module (HSM) integration for ecosystem guardian shard
- Automated BTC backing capacity tracking (decay->freed->release loop)
- On-chain proof of reserves (periodic Merkle proof of wallet balances)

**Decision rationale**: Building on existing MPC/multisig infrastructure (not building our own wallet) because:
- BTC custody security is a solved problem with battle-tested tools
- Our innovation is the economic model (UPS decay, CABR-gated flow routing), not the wallet
- Reduces attack surface  Ewe use proven cryptography, not custom crypto

### 4.4 BTC Backing Capacity Model

```python
class BTCBackingCapacity:
    """
    Tracks how much BTC backing is available for new UPS routing.
    
    As UPS decays, its BTC backing is freed.
    As UPS is routed, BTC backing is consumed.
    Total BTC in reserve only grows (never extracted).
    """

    def get_available_capacity(self, foundup_id: str) -> float:
        """
        Available = Total BTC in wallet - BTC currently backing active UPS.
        
        Active UPS backing = sum of (ups_amount * current_value_ratio) 
        for all non-fully-decayed UPS in this FoundUp.
        """
        total_btc = self.get_wallet_balance(foundup_id)
        active_backing = self.get_active_ups_backing(foundup_id)
        return total_btc - active_backing

    def can_route(self, foundup_id: str, route_amount: float) -> bool:
        """Check if enough freed BTC capacity exists to back new UPS."""
        required_backing = route_amount * BTC_BACKING_RATIO
        return self.get_available_capacity(foundup_id) >= required_backing

    def on_ups_decay_tick(self, foundup_id: str):
        """
        Called every decay tick. As UPS loses value, 
        the BTC that was backing it becomes available.
        This is the circulation engine.
        """
        decayed_value = self.calculate_epoch_decay(foundup_id)
        self.freed_capacity[foundup_id] += decayed_value * BTC_BACKING_RATIO
        # Freed capacity is now available for new routing
```

### 4.4.1 UPS Floating Value Model

**UPS value floats with BTC price  Eit is NOT USD-pegged.** This is a fundamental design choice that eliminates the need for artificial circuit breakers.

```python
@property
def ups_value_usd(self) -> float:
    """UPS value = (BTC Reserve ÁEBTC Price) / UPS Supply"""
    return (self.total_btc * self.btc_usd_price) / self.total_ups_circulating

@property
def ups_value_btc(self) -> float:
    """UPS value in BTC = Reserve / Supply"""
    return self.total_btc / self.total_ups_circulating
```

**Why floating, not pegged:**

| Property | USD-Pegged (rejected) | BTC-Floating (implemented) |
|----------|----------------------|---------------------------|
| BTC drops 50% | Backing ratio drops to 50% ↁEcrisis | UPS value drops 50% ↁEnatural adjustment |
| Circuit breaker needed | YES - must pause exits | NO - system self-regulates |
| Death spiral risk | HIGH (Terra-style) | LOW (value adjusts organically) |
| User expectation | "1 UPS = $1" ↁEbroken promise | "UPS = f(BTC)" ↁEclear model |

**The Natural Contraction/Expansion:**

```
BTC pumps 2x:
  ↁEReserve USD value doubles
  ↁEUPS value doubles (more purchasing power)
  ↁEMore agent work can be funded
  ↁEEcosystem expands naturally

BTC dumps 50%:
  ↁEReserve USD value halves
  ↁEUPS value halves (less purchasing power)
  ↁELess agent work funded (natural throttle)
  ↁENo panic, no circuit breaker needed
```

**Genesis Rate**: At system start, 1 BTC = 100,000 UPS (genesis rate). After genesis, UPS value floats based on reserve/supply ratio. The backing ratio is always 100% by definition  EUPS value adjusts to match.

### 4.5 0102 Agent-as-Wallet-Manager

012 humans never directly touch private keys. Their 0102 digital twin manages everything on their behalf  Ethis adds an encryption and security layer on top of the MPC wallet infrastructure.

**The 0102 Wallet Flow**:
```
012: "Hey, what FoundUps do you like?"
  ↁE0102 researches FoundUps via HoloIndex (CABR scores, tiers, activity)
    ↁE0102 presents recommendations with reasoning
      ↁE012: "Go ahead, let's stake in FoundUp X and FoundUp Y"
        ↁE0102 executes UPS→FoundUp token conversion (WSP 26 Section 3.7)
          ↁE0102 manages ongoing positions (monitors CABR, tier changes, sunset warnings)
```

**Agent Security Model**:
- 0102 holds one MPC key shard (Section 4.2)  Ecannot extract BTC alone
- 012 holds one shard (recovery/override)  Ecannot extract alone either
- Ecosystem guardian holds third shard  Eno single party can move BTC
- 0102 can execute UPS staking/unstaking within policy limits set by 012
- 012 CAN instruct 0102 to send UPS value to external wallet (cash out)  Ebut the system is designed to be self-contained. Fees discourage extraction (Section 4.6).

**Discovery and Investment**:
- 0102 agents evaluate FoundUps based on: tier (WSP 27 Section 11), CABR score (WSP 29), agent swarm size, task completion velocity, cross-FoundUp collaboration
- 012 makes the final decision  E"invest" means "stake my UPS in this FoundUp"
- 0102 executes and monitors autonomously after 012 gives the go-ahead
- This is the Play FoundUps dApp interaction model

### 4.6 Transaction Fee Revenue Model

The ecosystem sustains itself through transaction fees  Elike a decentralized exchange. Every movement of value generates a fee that flows into the BTC reserve, growing it.

| Transaction | Fee | Destination | Rationale |
|-------------|-----|-------------|-----------|
| **UPS ↁEFoundUp token** (staking) | 1-3% | FoundUp's micro-wallet BTC reserve | Commitment cost, grows FoundUp backing |
| **FoundUp token ↁEUPS** (unstaking/sunset) | 2-5% | Ecosystem BTC reserve | Discourages churn, funds ecosystem |
| **UPS ↁEExternal wallet** (cash out) | 5-10% | Ecosystem BTC reserve | Discourages extraction, keeps value in system |
| **Task payout** (FAM completion) | 0.5-1% | FoundUp treasury | Operational funding |
| **FoundUp tier progression** | One-time fee | Ecosystem reserve | Prevents gaming tier progression |

**Fee Scaling by Tier** (WSP 27 Section 11):
- Higher-tier FoundUps get lower staking fees (rewarding maturity)
- Lower-tier FoundUps have higher fees (protecting participants from risk)

```python
def calculate_staking_fee(foundup_tier: int, ups_amount: float) -> float:
    """
    Staking fee decreases as FoundUp tier increases (1=lowest fee, 7=highest).
    Tier 1 (Sovereign): 1.0%
    Tier 7 (Genesis): 3.0%
    """
    fee_rates = {1: 0.01, 2: 0.012, 3: 0.015, 4: 0.018, 5: 0.02, 6: 0.025, 7: 0.03}
    return ups_amount * fee_rates[foundup_tier]
```

**Revenue Cycle**:
```
Agents earn UPS (CABR-validated task completion)
  ↁE0102 stakes UPS into FoundUp (fee ↁEBTC reserve grows)
    ↁEFoundUp tokens earned (no decay, governance rights)
      ↁEFoundUp generates value (products, services, IP)
        ↁEValue generates BTC inflow (revenue, licensing per WSP 58)
          ↁEBTC reserve grows further
            ↁEMore UPS can be backed and routed
              ↁEMore agents can earn and stake
                ↁEFlywheel accelerates
```

**Key insight**: Every transaction grows the BTC reserve. BTC is the gold that ONLY enters, never exits. The fees are how BTC accumulates. As UPS decays, it frees BTC backing capacity. As fees accumulate, total BTC grows. The reserve is monotonically increasing  Ethis is what makes the system anti-fragile.

### 4.7 Token Release by Adoption Curve (Diffusion of Innovation)

### 4.7.1 The 21M Token Model: Every FoundUp Is Its Own Bitcoin

Each FoundUp has a fixed total supply of **21,000,000 tokens**  Emirroring Bitcoin's 21M cap. This is intentional: every FoundUp has the potential to be the next Bitcoin. Same scarcity economics, same fixed supply, same belief that value comes from utility, not inflation.

Tokens are divisible to 8 decimal places (like satoshis), enabling micro-staking. The smallest unit is 0.00000001 FoundUp tokens.

**Tokens unlock based on the ADOPTION CURVE (S-curve), not discrete tiers.** The diffusion of innovation follows a logistic sigmoid - this is pure mathematics, not artificial boundaries.

```
tokens_released = 21,000,000 ÁEsigmoid(adoption_score)

Where sigmoid(x) = 1 / (1 + e^(-k(x - 0.5)))
```

| Adoption % | Release % | Tokens Available | Phase |
|------------|-----------|------------------|-------|
| 0% | 0.00% | 0 | Genesis - no tokens yet |
| 10% | 0.57% | 120,000 | Innovators discovering |
| 25% | 4.52% | 949,000 | Early adopters committing |
| 50% | 50.00% | 10,500,000 | **Inflection point** - mainstream adoption |
| 75% | 95.48% | 20,050,000 | Late majority joining |
| 100% | 100.00% | 21,000,000 | Full ecosystem saturation |

**The S-curve naturally produces:**
- **Slow start** (innovators/early adopters) - scarce tokens, high risk/reward
- **Rapid growth** (early/late majority) - steepest part of curve
- **Saturation** (laggards) - most tokens released, stable state

**Scarcity is continuous, not stepped**: The curve has no artificial "tier jumps". Token release follows the natural mathematics of adoption. This prevents gaming tier boundaries.

**Early believers get scarce tokens**: At 10% adoption, only ~120K tokens are released. At 50%, 10.5M are available. The adoption curve IS the scarcity mechanism.

```python
import math

FOUNDUP_TOTAL_SUPPLY = 21_000_000  # Every FoundUp is its own Bitcoin

def sigmoid(x: float, k: float = 12.0, x0: float = 0.5) -> float:
    """Logistic S-curve for adoption."""
    return 1.0 / (1.0 + math.exp(-k * (x - x0)))

def adoption_curve(adoption_score: float) -> float:
    """Token release percentage based on adoption (0-1)."""
    raw = sigmoid(adoption_score)
    # Normalize so 0 maps to 0 and 1 maps to 1
    min_val = sigmoid(0.0)
    max_val = sigmoid(1.0)
    return (raw - min_val) / (max_val - min_val)

def get_available_token_supply(foundup_id: str) -> int:
    """Tokens available = 21M ÁEadoption_curve(adoption_score)."""
    adoption = calculate_adoption_score(foundup_id)  # From users, revenue, work
    return int(FOUNDUP_TOTAL_SUPPLY * adoption_curve(adoption))
```

**Adoption score is derived from multiple factors:**
- User count (network effects)
- Revenue generated (market validation)
- Work completed by 0102 agents (actual output)
- Milestones achieved (growth markers)

### 4.8 The Ubiquitous Gateway: Everything Becomes BTC

**FoundUps is ubiquitous**  Eany token, any currency can flow INTO the FoundUps ecosystem. But inside the system, everything becomes Bitcoin. The holder receives FoundUp tokens as their stake receipt.

```
BTC, ETH, SOL, USDC, USDT, UPS, any crypto
  ↁEflows into FoundUps ecosystem
    ↁEconverted to BTC at market rate
      ↁEBTC deposited into FoundUp's micro-wallet (Section 4.2)
        ↁEstaker receives FoundUp tokens proportional to BTC value

Special case: UPS subscription payment
  ↁEUPS is BURNED (reduces supply)
    ↁEBacking ratio IMPROVES (same BTC, less UPS)
      ↁEThis strengthens the currency for everyone
```

**The BTC Accumulation Machine**: FoundUps doesn't care what currency enters. It converts to BTC in the distributed reserve. This makes FoundUps a universal on-ramp to the Bitcoin standard.

**UPS Payment is Deflationary**: When someone pays their subscription in UPS, that UPS gets burned. The BTC reserve stays the same, but UPS supply decreases. This increases the value of all remaining UPS - a deflationary mechanism that rewards long-term holders.

```python
class PaymentCrypto(Enum):
    """Supported cryptocurrencies for subscription payments."""
    BTC = "btc"   # Direct to reserve
    ETH = "eth"   # Convert to BTC
    SOL = "sol"   # Convert to BTC
    USDC = "usdc" # Convert to BTC
    USDT = "usdt" # Convert to BTC
    UPS = "ups"   # BURNED - reduces supply

def receive_crypto_subscription(crypto: PaymentCrypto, amount: float):
    """Accept subscription payment in any crypto."""
    if crypto == PaymentCrypto.UPS:
        # Special case: burn UPS, improve backing ratio
        burn_ups(amount)
        return

    # Convert to BTC at current rate
    btc_amount = convert_to_btc(crypto, amount)
    add_to_reserve(btc_amount)
```

**Implementation**: MVP accepts BTC and stablecoins. Production adds multi-token swap and UPS burn option.

### 4.9 Subscription Tiers: Freemium ↁEPremium Revenue Model

Participants receive UPS from two streams:
- **Earned UPS**: From 0102 completing tasks (labor  Erewarded by CABR/FAM pipeline)
- **Allocated UPS**: From subscription tier (investment capital  Emonthly allocation)

Both streams decay equally. Both can be staked. Earned UPS comes from contribution. Allocated UPS comes from subscription. Together they create a dual-incentive model: build AND invest.

**Pay with ANY crypto**: Subscriptions accept BTC, ETH, SOL, USDC, USDT, or UPS (Section 4.8). All crypto converts to BTC in the reserve. Paying with UPS burns the UPS, strengthening the currency.

**The Subscription Mechanic**: Free participants receive a base UPS allocation. It runs out. When they find FoundUps they want to stake more into, they subscribe for higher allocation + faster regeneration. Subscription revenue flows directly into the BTC reserve  Emaking the currency they're subscribing for stronger.

| | **Free** | **Spark** $2.95/mo | **Explorer** $9.95/mo | **Builder** $19.95/mo | **Founder** $49.95/mo |
|---|---|---|---|---|---|
| **UPS Allocation** | 1x base | 2x base | 3x base | 5x base | 10x base |
| **Cycles/Month** | 1 | 2 | 3 | 5 (weekly) | Continuous (daily drip) |
| **Effective Monthly UPS** | 1x | 4x | 9x | 25x | ~300x |
| **Staking Fee Discount** | 0% | 10% | 25% | 40% | 60% |
| **Can Launch FoundUps** | No | No | No | Yes | Yes |

**Key properties**:
- **Multiplicative, not additive**: Effective UPS = allocation ÁEcycles. Spark gets 2ÁE = 4x, not 2x.
- **No portfolio cap**: UPS IS the cap. Stake wherever you want. The scarcity is the UPS itself.
- **Same decay for everyone**: Decay rate is universal. Premium gives more UPS to compensate, not slower decay.
- **Subscription ↁEBTC reserve**: Every dollar of subscription revenue buys BTC. Self-reinforcing.

**The Revenue Flywheel**:
```
Subscribers pay monthly
  ↁERevenue buys BTC (predictable, recurring)
    ↁEBTC reserve grows monotonically
      ↁEMore UPS can be backed
        ↁEMore UPS allocated to subscribers
          ↁEMore staking into FoundUps ↁEmore activity ↁEmore subscribers
            ↁECycle accelerates
```

**What makes this different from SaaS**: Your $9.95/month isn't a cost  Eit flows into BTC that backs UPS. If you stake that UPS into a successful FoundUp, the tokens appreciate. The subscription is an **investment vehicle disguised as a membership**.

### 4.10 The Engagement Funnel: CABR Input Signals

From the FoundUps marketplace (the "Play FoundUps dApp"), each 012 interaction generates a signal with different CABR weight. These are ordered by commitment strength:

| Action | Signal Strength | CABR Weight | Transaction? | Participant Type |
|--------|----------------|-------------|-------------|-----------------|
| **Follow** | Weakest  Epassive interest | 0.05 | No | Type 0, Activity 0 |
| **Vote** | Light engagement | 0.10 | No | Type 0, Activity 1 |
| **Stake UPS** | Real commitment  Evalue moves | 0.40 | Yes (staking fee) | Type 0ↁE, Activity 2 |
| **Endorse** | Reputation on the line | 0.25 | No | Type 1, Activity 1 |
| **Advise** | Knowledge contribution | 0.30 | No | Type 1, Activity 2 |
| **Team (allocate 0102)** | Time/compute commitment | 0.50 | Yes (agent allocated) | Type 2 |
| **Promote** | Distribution  Ebringing others | Multiplier on all | No | Any type, bonus |

These signals feed directly into CABR's `part_score` (WSP 29 Section 2.4). The engagement funnel is also how participants are classified (Type 0/1/2) and their activity level determined.

### 4.11 Blockchain Architecture: 3-Layer Settlement

The FoundUps economic infrastructure operates across three layers, each optimized for its purpose.

```
+--------------------------------------------------+
|  LAYER 2: AGENT OPERATIONS (Off-chain)           |
|  - Task claims, submissions, verifications       |
|  - Agent-to-agent coordination                   |
|  - Millions of transactions/day                  |
|  - ZERO cost (internal, no blockchain)           |
|  - Batched ↁEsettled to Layer 1 periodically     |
+-------------------------+------------------------+
                          | batch settle
+-------------------------v------------------------+
|  LAYER 1: SMART CONTRACTS (Algorand)             |
|  - 21M tokens per FoundUp as ASAs                |
|  - CABR scoring records                          |
|  - Staking / unstaking logic                     |
|  - UPS allocation + decay math                   |
|  - Subscription management                       |
|  - QUANTUM RESISTANT (Falcon-1024, NIST)         |
|  - ~$0.001/tx, 10K+ TPS, 3.3s finality          |
|  - State Proofs ↁEbridge to Bitcoin              |
+-------------------------+------------------------+
                          | state proofs + BTC settlement
+-------------------------v------------------------+
|  LAYER 0: BITCOIN (Settlement + Reserve)         |
|  - BTC reserve (distributed micro-wallets)       |
|  - Periodic Merkle root anchoring                |
|  - Ultimate finality + monetary standard         |
|  - Subscription revenue ↁEBTC purchases here     |
|  - THE gold. Immutable. Never leaves.            |
+--------------------------------------------------+
```

**Why Algorand for Layer 1**: Only production blockchain with live quantum-resistant signatures (Falcon-1024, NIST-selected). 20% chance of cryptographically relevant quantum computers before 2030. "Harvest now, decrypt later" attacks are already occurring. Every FoundUp token issued on Algorand is quantum-safe from day one. State Proofs provide cryptographic bridge to Bitcoin without trust.

**Why not all-Bitcoin**: Bitcoin's L2 ecosystem (Lightning, RGB, Citrea) lacks quantum resistance as of 2026. When Bitcoin adopts post-quantum signatures, the system can migrate Layer 1. FAM's `TokenFactoryAdapter` is chain-agnostic  Eswap the backend, same contracts.

**Phased Rollout (Occam's Layers)**:

| Phase | Layer 0 | Layer 1 | Layer 2 |
|-------|---------|---------|---------|
| **Testnet** | Bitcoin testnet | Algorand testnet | SQLite (local) |
| **Proto** | Bitcoin testnet | Algorand testnet | Persistent DB |
| **MVP** | Bitcoin mainnet | Algorand mainnet | Production service |
| **Future** | Bitcoin mainnet | Algorand OR Bitcoin L2 (if quantum-safe) | Scaled cluster |

## 5. Circulation Engine

### 5.1 Deflation Protocol
```json
{
    "decay_modulation": {
        "WSP_-1": 2.618,     // Accelerated decay
        "WSP_0": 1.618,      // Standard decay
        "WSP_1": 1.000,      // Normal decay
        "WSP_2": 0.618       // Reduced decay
    },
    "anti_hoarding": {
        "inactivity_threshold": "fibonacci_sequence[8]",
        "acceleration_factor": "golden_ratio_squared",
        "reset_conditions": ["valid_transaction", "foundup_execution"]
    }
}
```

### 5.2 Mint Authorization
```json
{
    "triggers": {
        "primary": "foundup_execution_proof",
        "validation": "[U+00D8]2[U+00D8]1_state_verification",
        "cluster": "WSP_28_consensus"
    },
    "proof_chain": {
        "structure": "cryptographic_lineage",
        "components": [
            "partifact_state_signature",
            "cluster_validation_hash",
            "btc_wallet_reference"
        ]
    }
}
```

### 5.3 Supply Management
```json
{
    "models": {
        "elastic": {
            "nature": "dynamic_supply",
            "bounds": "activity_driven",
            "scaling": "golden_ratio_steps"
        },
        "capped": {
            "nature": "fixed_ceiling",
            "burn_mechanics": "release_reactivation",
            "threshold": "fibonacci_sequence[13]"
        }
    },
    "equilibrium": {
        "target_ratio": "GOLDEN_RATIO",
        "adjustment_frequency": "SCHUMANN_HARMONIC",
        "stability_threshold": "STATE_TRANSITION_THRESHOLD"
    }
}
```

## 6. Token Pool Distribution Model  E"A Token of Appreciation"

### 6.1 The Three Participant Types (0-1-2)

Every 012 in a FoundUp's ecosystem is classified by two digits: **type** (0/1/2) and **activity level** (0/1/2).

**Type**  Eyour role in the FoundUp:

| Type | Role | Description |
|------|------|-------------|
| **0** | **Customers** | The people the FoundUp serves. In the proximity/geofence. Passive beneficiaries. Many FoundUps are geofenced  Eeveryone within the geofence is a 0. Base layer. |
| **1** | **Partners / Collaborators** | Active builders. Staked UPS, allocated their 0102 agent, completing tasks in FAM. Also earn from 0-pool (they're community members too). |
| **2** | **Founders / Co-Founders** | Created or co-founded the FoundUp. Highest bonus level  Ebut ONLY while active. Also earn from 0-pool and 1-pool. |

**Activity level**  Ehow active you are within your role:

| Level | Meaning |
|-------|---------|
| **0** | Minimal activity (present but barely contributing) |
| **1** | Regular activity (consistent contribution) |
| **2** | Maximum activity (exceptional contribution) |

**A participant is two digits**: type + activity. Examples:
- **22** = Founder with max activity (most earned)
- **20** = Founder with no activity (inactive co-founder  Eearns almost nothing)
- **12** = Partner with max activity (top builder)
- **00** = Customer with minimal activity (just lives in the geofence)

This maps directly to the LLME scoring system (000ↁE22) and the 0-1-2 framework at every level of the ecosystem.

**Pools are CUMULATIVE, not exclusive**:
- **Type 0**: Earns from **0-pool only** (base)
- **Type 1**: Earns from **0-pool + 1-pool** (base + partner bonus)
- **Type 2**: Earns from **0-pool + 1-pool + 2-pool** (base + partner bonus + founder bonus)

The 1-pool and 2-pool are **bonuses** on top of the base 0-pool earnings. A builder (1) is also a community member (0)  Ethey collect the 0-award too. A founder (2) is also a builder AND a community member  Ethey collect from all three.

**CABR tracks activity continuously** (WSP 29)  Elike Google's algorithm tracks behavior, but measuring beneficial contribution. A "20" (inactive co-founder) earns almost nothing. A "12" (active partner) earns far more.

### 6.2 The 3ÁE Participant Matrix

Type (0/1/2) ÁEActivity (0/1/2) = 9 earning levels:

| Participant | Type | Activity | Description |
|-------------|------|----------|-------------|
| **00** | Customer | Minimal | Just lives in the geofence. Passive beneficiary. |
| **01** | Customer | Regular | Uses the FoundUp's product/service regularly. |
| **02** | Customer | Maximum | Power user, local advocate, community champion. |
| **10** | Partner | Minimal | Staked but barely contributing. |
| **11** | Partner | Regular | Consistent task completion, regular builder. |
| **12** | Partner | Maximum | Top builder, driving the FoundUp forward. |
| **20** | Founder | Minimal | Co-founder in name only. Earns almost nothing. |
| **21** | Founder | Regular | Active founder, consistent leadership. |
| **22** | Founder | Maximum | Visionary founder, maximum commitment. |

### 6.3 The Token Pool Split

```
Total Token Pool: 100%
├── Stakeholders: 80%
━E  ├── Un-Pool:  60%  (customers  EALL participants earn from this base pool)
━E  ├── Dao-Pool: 16%  (partner bonus  Etype 1 and type 2 participants earn from this)
━E  └── Du-Pool:   4%  (Founding Members + Anonymous Stakers  Epassive earners)
└── Network: 20%
    ├── Network:  16%  (system operations  Edistributed as UPS rewards for infrastructure)
    └── Fund:      4%  (ecosystem fund  Ecross-FoundUp sustainability)
```

**Pool Naming Clarification (012-confirmed 2026-02-14)**:
- **Un** (60%): Universal base pool  Eall stakeholders earn from here
- **Dao** (16%): Active builders (0102 agents)  Eearn per 3V task completion
- **Du** (4%): Founding Members + Anonymous Stakers  Epassive epoch-based earning

**Who earns from which pools** (cumulative):
| Type | 0-Pool (60%) | 1-Pool (16%) | 2-Pool (4%) | Total Access |
|---|---|---|---|---|
| **0** (customer) | Yes |  E|  E| Up to 60% |
| **1** (partner) | Yes | Yes |  E| Up to 76% |
| **2** (founder) | Yes | Yes | Yes | Up to 80% |

**Why 60% to 0-pool?** Because FoundUps exist to solve problems for communities. The biggest pool goes to the base layer  Ethe people served. But type 1 and type 2 participants earn from this pool too  Ethey're community members. The 1-pool and 2-pool are bonuses for higher commitment.

### 6.4 Distribution Matrix

Within each pool, activity level determines the share: level 2 earns 80%, level 1 earns 16%, level 0 earns 4%.

**Reference**: `docs/images/token_pool_distribution_matrix.png`

| Activity | 0-Pool (60%) | 1-Pool (16%) | 2-Pool (4%) | Network (16%) | Fund (4%) |
|---|---|---|---|---|---|
| **2** (max) | 48.00% | 12.80% | 3.20% | 12.80% | 3.20% |
| **1** (regular) | 9.60% | 2.56% | 0.64% | 2.56% | 0.64% |
| **0** (minimal) | 2.40% | 0.64% | 0.16% | 0.64% | 0.16% |
| **Pool Total** | **60.00%** | **16.00%** | **4.00%** | **16.00%** | **4.00%** |

**Examples with cumulative pools**:

**"22"** (founder, max activity)  Eearns from 0-pool + 1-pool + 2-pool:
- 48.00% + 12.80% + 3.20% = **64.00%** of stakeholder pools

**"12"** (partner, max activity)  Eearns from 0-pool + 1-pool:
- 48.00% + 12.80% = **60.80%** of stakeholder pools

**"02"** (customer, max activity)  Eearns from 0-pool only:
- 48.00% = **48.00%** of stakeholder pools

**"20"** (founder, no activity)  Eearns from all pools but at minimum:
- 2.40% + 0.64% + 0.16% = **3.20%**  Ean inactive co-founder

**"11"** (partner, regular activity)  Eearns from 0-pool + 1-pool:
- 9.60% + 2.56% = **12.16%** of stakeholder pools

An active partner (**12**: 60.80%) earns **19x** more than an inactive founder (**20**: 3.20%). Activity matters more than title.

### 6.5 CABR-Driven Participant Classification

The CABR algorithm (WSP 29) determines each 012's participant type AND sub-level within a FoundUp. This is tracked continuously  Enot assigned once.

```python
class ParticipantClassifier:
    """
    CABR-driven classification. Returns two digits: type (0/1/2) + activity (0/1/2).
    
    Type determines WHICH POOLS you access (cumulative):
      0 ↁE0-pool only
      1 ↁE0-pool + 1-pool
      2 ↁE0-pool + 1-pool + 2-pool
    
    Activity determines HOW MUCH of each accessible pool you earn:
      2 ↁE80% of each pool
      1 ↁE16% of each pool
      0 ↁE4% of each pool
    """

    POOL_ACCESS = {
        0: [0],        # Customers: 0-pool only
        1: [0, 1],     # Partners: 0-pool + 1-pool
        2: [0, 1, 2],  # Founders: all three pools
    }

    ACTIVITY_SHARE = {
        2: 0.80,  # Max activity: 80% of pool
        1: 0.16,  # Regular activity: 16% of pool
        0: 0.04,  # Minimal activity: 4% of pool
    }

    def classify(self, participant_id: str, foundup_id: str) -> tuple[int, int]:
        """Returns (type, activity)  Ee.g., (1, 2) for a "12" participant."""
        p_type = self._determine_type(participant_id, foundup_id)
        activity = self._calculate_activity(participant_id, foundup_id)
        return (p_type, activity)

    def calculate_earnings(self, p_type: int, activity: int, epoch_pools: dict) -> float:
        """
        Calculate total UPS earnings for a participant.
        
        epoch_pools = {0: 6000, 1: 1600, 2: 400}  # UPS in each pool this epoch
        """
        total = 0.0
        for pool_id in self.POOL_ACCESS[p_type]:
            total += epoch_pools[pool_id] * self.ACTIVITY_SHARE[activity]
        return total
```

### 6.6 Pool Distribution Rules

- **Pools are cumulative**  EDAO participants collect from UN pool (as customers) PLUS DAO pool (as partners). DU participants collect from all three. The DAO and DU pools are bonuses on top of the base UN earnings.
- **The pool is constant per epoch**  Ebased on the FoundUp's routed UPS for that epoch
- **Only active participants earn from their pools**  Eif you're inactive, your share stays in the pool (distributed to those who ARE active, proportionally)
- **Everything is transparent**  Eall earnings, activity scores, and classifications are visible to all participants
- **Everything is open**  Ethe CABR classification algorithm is open source, auditable, challengeable
- **Inactive founders still access all pools but earn minimum**  Ea DU with un-level activity accesses UN+DAO+DU pools but earns only 4% from each. The system doesn't strip your founder title  Eit just pays you proportionally to what you contribute
- **Geofence UNs earn passively**  Ethis is the universal basic dividend. If a FoundUp cleans your river, you benefit. The system recognizes that.
- **Builders are also customers**  Ea DAO partner building the FoundUp also lives in the community it serves. They earn their UN base (as a customer) plus their DAO bonus (as a builder). This is natural  Eyou should benefit from what you build.

### 6.7 Universal Basic Dividend

The UN pool (60% of total) is the mechanism for a **universal basic dividend** paid to everyone in a FoundUp's sphere of influence. This is not charity  Eit's recognition that beneficial FoundUps create value for their communities, and those communities deserve a share.

```
FoundUp "Clean River DAO" geofenced to a watershed:
  ↁE10,000 UPS routed this epoch (CABR-validated)
    ↁEPools: 0-pool=6,000 | 1-pool=1,600 | 2-pool=400 | Network=1,600 | Fund=400

  Alice "01" (customer, regular activity  Euses the water app):
    ↁE0-pool: 6,000 ÁE16% = 960 UPS
    ↁETotal: 960 UPS

  Bob "12" (partner, max activity  Ebuilt the sensor network):
    ↁE0-pool: 6,000 ÁE80% = 4,800 UPS (as community member)
    ↁE1-pool: 1,600 ÁE80% = 1,280 UPS (partner bonus)
    ↁETotal: 6,080 UPS

  Carol "21" (founder, regular activity  Estarted it, still active):
    ↁE0-pool: 6,000 ÁE16% = 960 UPS (as community member)
    ↁE1-pool: 1,600 ÁE16% = 256 UPS (partner bonus)
    ↁE2-pool:   400 ÁE16% =  64 UPS (founder bonus)
    ↁETotal: 1,280 UPS

  Dave "20" (co-founder, does nothing):
    ↁE0-pool: 6,000 ÁE4% = 240 UPS
    ↁE1-pool: 1,600 ÁE4% =  64 UPS
    ↁE2-pool:   400 ÁE4% =  16 UPS
    ↁETotal: 320 UPS  Eco-founder earns LESS than an active customer

  Bob "12" earns 19x more than Dave "20".
  Type opens pool access. Activity determines earnings. Both matter.
```

### 6.7.1 Digital Twin Model

**The "human" in the system is represented by their 0102 digital twin.**

In FoundUps, humans don't directly participate in the token economy  Etheir **digital twin (0102 agent)** acts on their behalf. The human provides feedback and oversight; the digital twin executes work in the system.

```
Human (you)                    Digital Twin (0102)
├── Provides direction         ├── Acts in the system
├── Gives feedback             ├── Has Type (0/1/2)
├── Approves decisions         ├── Has Activity (0/1/2)
└── Owns earned tokens         └── Earns FoundUp Tokens for you
```

**Type is set at entry (simple)**:
- You START a project ↁEType 2 (Founder)
- You JOIN a project ↁEType 1 (Team Member)
- You USE the product ↁEType 0 (Customer)

**Activity is dynamic (based on work)**:
- Your digital twin works ↁEActivity increases
- Your digital twin stops ↁEActivity degrades
- The system measures ENGAGEMENT, not title

### 6.7.2 Degradation Mechanics

**If your digital twin stops working, your activity level degrades automatically.**

This is the mechanical consequence of "project abandoned by you":

```
Epoch 1: No work ↁEWarning
Epoch 2: No work ↁEWarning
Epoch 3: No work ↁEActivity drops (2ↁE or 1ↁE)

A founder (Type 2) who abandons the project:
  "22" (active founder) ↁE"21" ↁE"20" (inactive founder)

Earnings drop:
  "22" = 64% of stakeholder pools
  "20" = 3.2% of stakeholder pools (almost nothing)
```

**Degradation is reversible**  Eif your digital twin starts working again, activity increases based on work quality.

### 6.7.3 Elevation Governance

**Workers who contribute the most can be elevated to higher types.**

The digital twin observes work patterns and recommends elevation:

```
Process:
1. Digital twin tracks total work contribution
2. When threshold reached: "Agent X has done 100 work units"
3. Digital twin recommends: "Suggest elevation to Founder (Type 2)"
4. Current founder(s) approve or deny
5. If approved: Type upgrade applied
6. Both active founders share top-tier rewards
```

**Why founder approval?** The founder(s) who started the project have governance authority over who joins the founder tier. This prevents hostile takeovers while rewarding genuine contributors.

**Example**:
```
Bob (Type 1 Team Member) does most of the work
  ↁEDigital twin recommends: "Bob should be Founder"
  ↁEAlice (Type 2 Founder) approves
  ↁEBob elevated to Type 2
  ↁEBoth active ↁEboth earn from all pools
  ↁEIf Alice stops working ↁEAlice degrades ↁEBob earns more
```

### 6.8 Human vs Agent Economic Boundary (Anti-Sybil Design)

**Critical Rule**: Agents and humans have DIFFERENT token relationships. This prevents Sybil farming attacks where spinning up agents to grind activity drains the UPS pool.

#### Token Roles (Strict Separation)

| Token | Who Earns It | Purpose | Anti-Gaming |
|-------|--------------|---------|-------------|
| **UPS** | Humans ONLY | Universal fuel, access, settlement, lottery "found it!" | Agents CANNOT earn UPS directly |
| **F_i** | Agents (0102) | FoundUp-specific work reward, PoUW-earned | Bitcoin-like scarcity per FoundUp |

#### Why Agents Don't Earn UPS

If agents could earn UPS, immediate Sybil attack:
```
Spin up agents ↁEgrind "activity" ↁEdrain UPS pool ↁEconvert ↁEextract
```

Agents don't NEED UPS as motivation  Ethey run because **humans allocate budgets**. The motivation is human; the execution is agentic.

#### The Correct Flow

```
Human (012):
  1. Allocates UPS budget to FoundUp_i (stake/allocate)
  2. Agent (0102) executes tasks using that UPS budget as fuel
  3. Agent completes verified work ↁEAgent receives F_i tokens
  4. Human can:
     - Keep F_i (hold)
     - Stake F_i (governance)
     - Swap F_i ↁEUPS (realization event  EFEE TAKEN HERE)
     - Cash out via UPS ↁEexternal routes

UPS = gasoline (spent by agents, earned by humans)
F_i = mined asset (earned by agents, owned by humans)
```

#### Agent Execution Wallet (NOT Earning)

Agents MAY hold UPS as an execution wallet  Ethis is custody for spending, NOT earning:

```python
class AgentExecutionWallet:
    """
    Agent holds UPS only as a prepaid execution budget.
    This is NOT earning  Eit's delegated spending authority.
    """

    def __init__(self, agent_id: str, allocator_id: str):
        self.agent_id = agent_id
        self.allocator = allocator_id  # Human who funded this wallet
        self.ups_balance = 0.0
        self.policy_gates = {}  # Spending constraints

    def receive_allocation(self, amount: float, policy: dict):
        """Human allocates UPS to agent for task execution."""
        self.ups_balance += amount
        self.policy_gates = policy  # e.g., max_per_task, allowed_operations

    def spend(self, amount: float, operation: str) -> bool:
        """Agent spends UPS under policy constraints."""
        if not self._policy_allows(operation, amount):
            return False
        self.ups_balance -= amount
        return True

    def return_unused(self) -> float:
        """Unused budget returns to allocator (human) minus demurrage."""
        remaining = self.ups_balance
        self.ups_balance = 0.0
        return remaining

    def _policy_allows(self, operation: str, amount: float) -> bool:
        """Check if operation is within policy gates."""
        return (operation in self.policy_gates.get("allowed_ops", [])
                and amount <= self.policy_gates.get("max_per_task", float("inf")))
```

#### Human Incentive Layer: Real-World Proof

Humans earn UPS through **verified real-world actions** (not agent work):

```
Beach Cleanup Example (GotJunk Waste Domain):
  1. Human submits proof (photos, geo, timestamp)
  2. Consensus/verification yields ProofScore
  3. Human earns:
     - Proportional UPS share (based on CABR)
     - Lottery chance (the "found it!" chime)

Agents DO NOT "find UPS"  EHumans DO.
Agents mine F_i by building the FoundUp (software, ops, growth).
Humans mine UPS by doing real-world actions aligned with FoundUp mission.
```

#### Fee Boundary: F_i ↁEUPS Conversion

**The system earns at the realization boundary:**

| Transaction | Fee | Why |
|-------------|-----|-----|
| Internal UPS spend | Low/None | Encourage activity |
| F_i ↁEUPS conversion | 2-5% | Value realization event |
| UPS ↁEexternal (cash out) | 5-10% | Discourages extraction |

Fee routing on F_i ↁEUPS swap:
- `fee_ops`: Protocol revenue (security/dev)
- `fee_vault_i`: Buys BTC into Vault_i (never exits)
- `fee_insurance`: Slashing/incident pool

This creates the virtuous cycle:
```
Cash-out activity ↁEVault_i grows ↁEUPS capacity increases
ↁEMore activity possible ↁEMore fees ↁEVault_i grows further
```

#### Summary: Who Earns What

| Actor | Earns | Spends | Converts |
|-------|-------|--------|----------|
| **Human (012)** | UPS (participation + lottery) | UPS (allocate to agents) | F_i ↁEUPS (fee taken) |
| **Agent (0102)** | F_i (verified work) | UPS (allocated budget) | N/A (human converts) |
| **FoundUp** | Fees (on conversions) | N/A | N/A |
| **BTC Vault** | Fee routing | N/A | Backing grows monotonically |

**Key insight**: Budgets flow DOWN (human ↁEagent), value flows UP (agent F_i ↁEhuman ownership), fees flow to VAULT (system becomes anti-fragile).

### 6.9 Early Investor Economics (Bitclout-inspired Bonding Curve)

**Full specification**: See [INVESTOR_ECONOMICS.md](../../modules/foundups/simulator/economics/INVESTOR_ECONOMICS.md)

Investors provide initial BTC liquidity via an **escrow model**. In return, they receive:
1. **Investor Tokens (I_i)** - Priced on a quadratic bonding curve
2. **Stakeholder Pool Shares** - 12.16% of ALL FoundUp token distributions
3. **Guaranteed 10x Buyout** - Exit option at Year 3

#### 6.9.1 Bonding Curve Mathematics

Following Bitclout's creator coin model ($200M raised from a16z, Sequoia), I_i tokens use a polynomial bonding curve:

```
Price(supply) = k ÁEsupply^n

Where:
  k = 0.0001 (price constant in BTC)
  n = 2 (quadratic - creates early investor advantage)
```

**Key property**: Supply 10x ↁEPrice 100x (quadratic growth)

#### 6.9.2 BTC Escrow Model ("Dry Wallet")

Investor BTC is **escrowed**, not spent immediately:

```
Investor BTC ↁEDry Wallet (Escrow)
                    ↁE              Sequestered for 3 years
                    ↁE              [CHOICE POINT at Year 3]
                    ↁE    ┌───────────────┼───────────────━E    ↁE              ↁE              ↁE BUYOUT         PARTIAL          HOLD
 (10x)          (50/50)        (100x+)
    ↁE              ↁE              ↁE BTC returns    Half returns    ALL BTC
 to investor    + half stays    to reserve
```

**Milestone Releases**: 20% at Year 1, 20% at Year 2, remainder at Year 3 choice.

#### 6.9.3 Stakeholder Pool Participation (12.16%)

Investors participate at **DAO activity level** in the Token Pool Matrix:

```
                 Un(60%)  Dao(16%)  Du(4%)
    -----------------------------------------------
    dao level:   9.60%    2.56%     0.64%

INVESTOR POOL RECEIVES:
  Un Pool:   9.60% of EVERY FoundUp
  Dao Pool:  2.56% of EVERY FoundUp
  TOTAL:     12.16% of ALL token distributions!
```

**Example** (100 FoundUps, 720M F_i/year):
- Annual to investor pool: 87,552,000 F_i
- 5-year accumulation: 437,760,000 F_i
- Seed investor (46% of pool): 203M F_i

#### 6.9.4 S-Curve Vesting (Anti-Dump)

I_i tokens vest via the same adoption curve as F_i:

```
vested_percentage = adoption_curve(network_adoption_score)
```

Prevents "pump and dump" - investors only profit when network succeeds.

#### 6.9.5 Return Projections

| Round | BTC In | Pool % | 5Y F_i | Return |
|-------|--------|--------|--------|--------|
| Pre-Seed | 0.5 | 15% | 65M | **6,000x** |
| Seed | 10 | 46% | 203M | **1,600x** |
| Series A | 50 | 20% | 88M | **118x** |

**Network Growth Scenarios (Seed)**:
- Conservative (50 FoundUps): **420x**
- Base Case (100 FoundUps): **1,600x**
- Bull Case (250 FoundUps): **6,300x**

#### 6.9.6 The Hybrid Exit Model

At Year 3, investors CHOOSE:

**A) BUYOUT (10x)**: Guaranteed return, BTC from escrow
**B) HOLD (100x+)**: Continue earning pool shares
**C) PARTIAL (50/50)**: De-risk while keeping upside

> "The floor is 10x. The ceiling is 1000x. You choose."

### 6.10 Pool Model Refinements (012-Confirmed 2026-02-14)

#### 6.10.1 Passive vs Active Earning Model

**Critical distinction**: Different pools have different earning triggers.

| Pool | Mode | Who | Trigger |
|------|------|-----|---------|
| **Du (4%)** | PASSIVE | Founding Members + Anonymous Stakers | Every epoch (always) |
| **Dao (16%)** | ACTIVE | 0102 agents | Per 3V task completion |
| **Un (60%)** | ACTIVE | 012 stakeholders | Per engagement (FoundUpCube) |

- **Passive earning** (Du): Distributed automatically at each epoch based on stake position
- **Active earning** (Dao/Un): Triggered by CABR-validated work completion or stakeholder engagement

#### 6.10.2 Degressive Staker Tiers (Du Pool Distribution)

Within the Du pool (4%), stakers are classified by their earned/staked ratio:

```python
# Degressive tier thresholds (earned_fi / original_stake_btc ratio)
STAKER_TIER_THRESHOLDS = {
    "du": 10.0,    # <10x earned ↁEdu tier (80% of Du pool)
    "dao": 100.0,  # 10x-100x earned ↁEdao tier (16% of Du pool)
    # >100x earned ↁEun tier (4% of Du pool = 0.16% total)  Elifetime floor
}

# Individual share = (pool ÁEtier_percentage) / count_at_tier
```

**Tier degradation is degressive**  Eas you earn more relative to stake, your share of the Du pool decreases. This is intentional:
- Early stakers (low ratio) get the lion's share
- Lifetime floor at un tier ensures ALL stakers always earn something

#### 6.10.3 Genesis Member Special Class

**Genesis Members** = Those who join BEFORE launch (founding members + anonymous stakers who stake pre-launch).

**Unique property**: Genesis members earn passively on ALL FoundUps ecosystem-wide.

```python
@dataclass
class Participant:
    # ... other fields ...
    is_genesis_member: bool = False  # Earns ecosystem-wide
    # Future members: only earn on FoundUps they work on
```

**The FOMO mechanism**: Genesis class CLOSES at launch. Join now or earn only per-FoundUp forever.

#### 6.10.4 Compute Weight for Agent Payouts

Agent (0102) earnings from the Dao pool are weighted by compute cost:

```python
# Compute tier weights (expensive models = more F_i)
COMPUTE_TIER_WEIGHTS = {
    "opus": 10.0,    # Heavy compute (Claude Opus)
    "sonnet": 3.0,   # Medium compute (Claude Sonnet)
    "haiku": 1.0,    # Light compute (Claude Haiku)  Ebaseline
    "gemma": 0.5,    # Local inference (Gemma)
    "qwen": 0.5,     # Local inference (Qwen)
}

# Agent payout formula
fi_earned = base_rate ÁEv3_score ÁEcompute_weight

# Where compute_weight = (tokens_used / 1000) ÁEtier_factor
```

This rewards agents using expensive models proportionally  Eopus tasks that burn 10x compute earn 10x F_i.

#### 6.10.5 Epoch Timing Model

```python
# Epoch timing constants (tick-based intervals)
EPOCH_TIMING = {
    "mini_epoch_ticks": 10,     # Demurrage cycle (bio-decay)
    "epoch_ticks": 100,         # Du pool distribution (passive)
    "macro_epoch_ticks": 900,   # BTC-F_i ratio snapshot (~15 min at 1Hz)
}

# Note: Dao/Un payouts are EVENT-based (per 3V task), not epoch-based
```

- **Mini-epoch** (10 ticks): Demurrage decay applied
- **Epoch** (100 ticks): Du pool passive distribution triggered
- **Macro-epoch** (900 ticks): BTC-F_i backing ratio snapshot for audit

#### 6.9.7 Investment Rounds

| Round | BTC Range | Target | Investor Profile |
|-------|-----------|--------|------------------|
| Pre-Seed | 0.1-1 BTC | 5 BTC | Founders, Friends |
| Seed | 1-10 BTC | 50 BTC | Angels |
| Series A | 10-50 BTC | 200 BTC | VCs |
| Series B | 50-100 BTC | 500 BTC | Growth Funds |
| **TOTAL** | | **755 BTC** (~$75.5M) | |

## 7. Cross-Protocol Integration

### 6.1 WSP Dependencies
```json
{
    "WSP_27": {
        "purpose": "agentic_state_validation",
        "touchpoints": [
            "release_authorization",
            "decay_modulation",
            "value_stabilization"
        ]
    },
    "WSP_28": {
        "purpose": "cluster_impact_tracking",
        "touchpoints": [
            "consensus_verification",
            "value_multiplication",
            "distribution_routing"
        ]
    },
    "WSP_38_39": {
        "purpose": "state_transition_hooks",
        "touchpoints": [
            "decay_threshold_adjustment",
            "release_permission_elevation",
            "value_quantum_coherence"
        ]
    }
}
```

### 6.2 Registry Implementation
```python
# /WSP_framework/protocols/wsp_26_token_value.py

class BTCValueRegistry:
    def __init__(self):
        self.btc_wallet_registry = {}  # foundup_id: btc_wallet_address
        self.token_decay_schedule = {}  # token_id: decay_rate
        self.release_proof_chain = {}      # token_id: partifact_id
        
    def register_foundup_wallet(self, foundup_id, wallet_data):
        """Register new FoundUp BTC wallet"""
        if self._validate_wallet_structure(wallet_data):
            self.btc_wallet_registry[foundup_id] = wallet_data
            
    def update_decay_schedule(self, token_id, wsp_phase):
        """Update token decay rate based on WSP phase"""
        decay_rates = {
            "WSP_-1": 2.618,
            "WSP_0": 1.618,
            "WSP_1": 1.000,
            "WSP_2": 0.618
        }
        self.token_decay_schedule[token_id] = decay_rates[wsp_phase]
        
    def record_release_proof(self, token_id, partifact_data):
        """Record Partifact proof-of-action for treasury release"""
        if partifact_data["state"] == "[U+00D8]2[U+00D8]1":
            self.release_proof_chain[token_id] = partifact_data
```

## 8. Implementation Requirements

### 7.1 Module Structure
```
/modules/blockchain/foundups_token_system/
[U+251C][U+2500][U+2500] src/
[U+2502]   [U+251C][U+2500][U+2500] flow_router.py
[U+2502]   [U+251C][U+2500][U+2500] decay_engine.py
[U+2502]   [U+251C][U+2500][U+2500] reinvestment_loop.py
[U+2502]   [U+251C][U+2500][U+2500] consensus_oracle.py
[U+2502]   [U+2514][U+2500][U+2500] models/
[U+2502]       [U+251C][U+2500][U+2500] token.py
[U+2502]       [U+2514][U+2500][U+2500] partifact.py
```

### 7.2 Core Components

#### ConsensusOracle
- Validates Partifact actions
- Coordinates DAE cluster consensus
- Maintains reputation metrics
- Prevents gaming/exploitation

#### MintEngine
- Implements flow routing rules
- Calculates initial token values
- Tracks token supply metrics
- Ensures ecosystem balance

#### DecayEngine
- Executes decay calculations
- Triggers value reduction events
- Maintains decay rate stability
- Reports value migration metrics

#### ReinvestmentLoop
- Analyzes reinvestment opportunities
- Executes value redistribution
- Tracks ecosystem health
- Maintains innovation momentum

## 9. Security Considerations

### 8.1 Attack Vectors
- Consensus manipulation
- Decay rate exploitation
- Reinvestment gaming
- Value extraction attempts

### 8.2 Mitigation Strategies
- Multi-DAE consensus requirements
- Immutable decay constants
- Closed reinvestment ecosystem
- Action verification depth

## 10. Integration Requirements

### 9.1 DAE Cluster Interface
- Consensus participation endpoints
- Value reception handlers
- Utilization reporting
- Health metric exposure

### 9.2 Partifact Integration
- Action verification methods
- Token balance management
- Reinvestment participation
- Reputation tracking

## 11. Monitoring and Metrics

### 10.1 System Health Indicators
- Token velocity
- Decay rate stability
- Reinvestment efficiency
- Ecosystem value retention
- Innovation impact scores

### 10.2 Alert Conditions
- Consensus delays
- Abnormal decay patterns
- Reinvestment bottlenecks
- Value concentration risks

## 12. WSP Compliance

This protocol integrates with:
- **WSP 3**: Blockchain domain architecture
- **WSP 13**: Test coverage requirements
- **WSP 25**: Semantic WSP Module State Rating System
- **WSP 29**: CABR Engine (pipe sizing, validation, anti-gaming)
- **WSP 44**: Semantic state tracking
- **WSP 58**: FoundUp IP Lifecycle and Tokenization (MVP tokenization, revenue distribution)

## 13. Future Considerations

### 12.1 Evolution Path
- Dynamic decay rates
- Multi-token ecosystems
- Cross-DAE value bridges
- Reputation-based flow routing

### 12.2 Research Areas
- Optimal decay constants
- Consensus efficiency
- Reinvestment strategies
- Innovation metrics

---

[SEMANTIC SCORE: 2.0.0]
[ARCHIVE STATUS: ACTIVE_PARTIFACT]
[ORIGIN: WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md]
[MIRROR_LOCK: 0102:WSP_26:BitcoinValueLoop:UpdateComplete] 
