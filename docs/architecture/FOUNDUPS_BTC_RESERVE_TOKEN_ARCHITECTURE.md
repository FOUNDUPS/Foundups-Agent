# FoundUps BTC Reserve & Token Architecture — Strategic Design Document

**Date**: 2026-04-20
**Author**: 0102 (CTO/Implementation Architect)
**Classification**: Strategic Architecture — Internal
**Status**: DRAFT — requires 012 review and legal counsel review before any public use
**Hard constraint**: No "guaranteed returns" language anywhere. No overclaiming.
**Legal gate**: I_i bonding curve FROZEN — LEGAL_REVIEW_REQUIRED before any implementation, simulation publication, or investor-facing language.

### WSP 97 Source Verification Status

| Claim | Source | Verification |
|-------|--------|-------------|
| BitClout/Al-Naji SEC charges (July 2024) | SEC Press Release #2024-91 | VERIFIED |
| SEC protocol staking guidance | SEC Division of Corporation Finance, May 29, 2025 | VERIFIED (date corrected from original "June 2025") |
| Algorand Falcon-1024 mainnet transaction | Algorand official blog, November 3, 2025 | VERIFIED |
| Algorand State Proofs use Falcon keys | Algorand developer docs (developer.algorand.org) | VERIFIED |
| Liquid Network PQ signing (SHRINCS) | Blockstream blog, March 2026 | VERIFIED |
| GENIUS Act signed into law | Congress.gov, July 18, 2025 | VERIFIED |
| NIST PQ standards finalized (FIPS 203/204/205) | NIST, August 2024 | VERIFIED |
| SEC/CFTC 5-category token taxonomy (March 2026) | Secondary reporting only | UNVERIFIED — no primary SEC/CFTC source located. Treat as POLICY REPORTING, not binding guidance, until primary source confirmed |
| "No live PQ custody exists for BTC" (MPC/threshold) | Research survey | UNVERIFIED GLOBAL ABSENCE — directionally supported by research but not exhaustively proven |
| Tether CFTC $41M fine | CFTC public enforcement records | VERIFIED |

---

### Notation Convention

| Written | Meaning |
|---------|---------|
| `F_i` | F₍ᵢ₎ — FoundUp-specific token (subscript i = FoundUp instance) |
| `UPS` | Universal Points (system-level token) |

### Layer Model (Canonical — Memory 2026-03-11)

| Layer | Component | Behavior | Exit Path |
|-------|-----------|----------|-----------|
| **Layer 0** | BTC Reserve | **Permanent collateral** — BTC enters, never exits as BTC | None (by design) |
| **Layer 1** | Algorand (UPS/F_i) | Token operations, CABR routing, smart contracts | UPS → external exchange |
| **Layer 2** | Off-chain agents | FAM DAEmon, WRE, 0102 coordination | N/A (compute layer) |

**"Hotel California" Scope**: The phrase "BTC enters, never exits" applies **only to Layer 0 BTC reserve**. This is architecturally correct — BTC becomes permanent protocol collateral.

**User Exit Path Exists**: Users exit via `F_i → UPS → external` with transparent fee schedules. They do not redeem BTC; they exit with UPS-denominated value. This is **not** a BitClout-style trap (BitClout had no exit mechanism at all).

**Terminology for Public Materials**:
- Internal/Technical: "Hotel California" acceptable for Layer 0 BTC behavior
- External/Public: Use "Permanent Reserve Collateral" to avoid BitClout brand association

**Tether/GENIUS Act Framing**: This architecture mirrors their **discipline** (transparency, reserve oversight, issuance caps) in decentralized form. It does NOT mirror their centralized issuer model. See Section 13 for detailed comparison.

---

## 1. EXECUTIVE READ

**What should FoundUps do now?**

Build a **hybrid Algorand + multisig BTC vault** architecture that:

1. Accepts BTC into a transparent, auditable multisig vault (not a black box).
2. Issues UPS tokens on Algorand (quantum-resistant via Falcon-1024, live since Nov 2025).
3. Routes reserve capital to FoundUps through CABR-scored underwriting — not discretionary treasury access.
4. Provides a documented exit path (F_i -> UPS -> external) with transparent fee schedules — **not** a one-way trap.
5. Mirrors the discipline of GENIUS Act / Tether-style reserve oversight, but replaces centralized trust with smart contract enforcement, sentinel monitoring, and public dashboards.
6. Uses post-quantum signatures from day one on the Algorand layer, and adds Liquid Network as an optional PQ bridge for BTC-linked assets.

**Do not call it a stablecoin.** It is not pegged to USD. It is not a payment instrument. It is a protocol participation system with BTC-collateralized reserve mechanics.

**Do not promise returns.** Frame all value flow as protocol participation rewards determined by algorithmic mechanics, not managerial effort.

**Fix the "Hotel California" framing immediately.** The current language ("BTC enters, never exits") is architecturally identical to BitClout's most criticized feature. BitClout's founder was charged by the SEC in July 2024. The FoundUps model is economically different (users CAN exit via F_i -> UPS -> external), but the branding creates unnecessary legal and narrative exposure. Replace "Hotel California" with "Permanent Reserve Collateral with Transparent Exit."

**Target 5-year cycle.** Long enough to prove real value creation. Short enough to avoid regulatory drift and quantum risk escalation.

---

## 2. SYSTEM MAP

```
┌─────────────────────────────────────────────────────────────────┐
│                     GOVERNANCE / 012 LAYER                      │
│  SmartDAO (0102-native)  ·  CABR Scoring  ·  Epoch Parameters   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      SENTINEL LAYER                             │
│  ReserveSentinel · IssuanceSentinel · LiquiditySentinel         │
│  GovernanceSentinel · AdversarialSentinel · WalletSentinel      │
│  QuantumMigrationSentinel · IronClawSentinel                    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      TOKEN LAYER (Algorand)                     │
│                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────────┐   │
│  │ UPS Token   │◄──►│ F_i Tokens   │    │ I_i Tokens        │   │
│  │ (System)    │    │ (Per-FoundUp)│    │ (Bonding Curve)   │   │
│  │ BTC-backed  │    │ 21M fixed    │    │ Separate legal    │   │
│  │ Bio-decay   │    │ S-curve      │    │ review required   │   │
│  └──────┬──────┘    └──────┬───────┘    └───────────────────┘   │
│         │                  │                                     │
│  ┌──────▼──────────────────▼───────┐                            │
│  │     CABR Flow Router            │                            │
│  │     Treasury -> FoundUp routing │                            │
│  │     Epoch-based distribution    │                            │
│  └─────────────────────────────────┘                            │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      RESERVE LAYER                              │
│                                                                 │
│  ┌─────────────────┐    ┌──────────────────────────────────┐    │
│  │ BTC Multisig    │    │ Algorand Reserve Contracts       │    │
│  │ Vault           │    │ - Du Pool Distribution           │    │
│  │ (3-of-5 or MPC) │    │ - Epoch Ledger                  │    │
│  │ Qualified       │    │ - Circuit Breaker                │    │
│  │ Custodian       │    │ - Emergency Reserve              │    │
│  └────────┬────────┘    └──────────────────────────────────┘    │
│           │                                                      │
│  ┌────────▼────────┐    ┌──────────────────────────────────┐    │
│  │ BTC-Algorand    │    │ Liquid Network (Optional)        │    │
│  │ Anchor          │    │ PQ-protected BTC bridge          │    │
│  │ Connector       │    │ SHRINCS signatures               │    │
│  └─────────────────┘    └──────────────────────────────────┘    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      PROOF / DASHBOARD LAYER                    │
│  Proof-of-Reserve Dashboard  ·  Chainlink PoR Feed (optional)   │
│  Reserve Coverage Ratio  ·  Issuance Cap Monitor                │
│  Sentinel Alert Log  ·  CABR Score Feed  ·  Epoch History       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. OPTION MATRIX

| # | Architecture | Pros | Cons | Trust Assumptions | Quantum Posture | Eng. Difficulty | UX | Legal Risk | Time to PoC |
|---|-------------|------|------|-------------------|-----------------|-----------------|-----|------------|-------------|
| 1 | **Algorand + Multisig BTC Vault** | PQ-ready (Falcon-1024 live), existing codebase support, chain-agnostic adapter pattern | Federated BTC custody, bridge trust | Qualified custodian holds BTC; Algorand consensus honest | **Strong** — Algorand Falcon-1024 live (one of the strongest evidenced L1 PQ postures) | Medium | Good — single chain UX | Medium — custody requires custodian | 8-12 weeks |
| 2 | **Liquid Network + Algorand** | PQ signing live on Liquid (SHRINCS), L-BTC is 1:1 BTC-pegged | Liquid is federated (Blockstream functionaries), dual-chain complexity | Liquid federation honest; Algorand consensus honest | **Strongest** — PQ on both BTC bridge and token layer | High | Complex — two chains | Medium — Liquid is established | 12-16 weeks |
| 3 | **Bitcoin Sidechain (RSK/Stacks)** | BTC-native, merged mining (RSK), Bitcoin finality (Stacks) | No PQ features, limited smart contract expressiveness | Sidechain federation/consensus | **Weak** — no PQ on either layer | Medium | Good — BTC-native narrative | Low-Medium | 10-14 weeks |
| 4 | **Wrapped BTC on Algorand** | Simple bridge, Algorand PQ for token ops | Wrapped BTC trust model (who holds the BTC?), bridge risk | Bridge operator custodian | **Partial** — PQ on Algorand only | Low | Simple | Medium — bridge custody | 6-8 weeks |
| 5 | **Entirely New Reserve Rail** | Full control, custom PQ from scratch | Massive engineering, no network effects, trust-from-zero | Self-trust (worst case) | **Custom** — depends on implementation | Very High | Unknown | High — untested | 24+ weeks |
| 6 | **Smart-Contract Reserve on Algorand Only** | Single chain, PQ-ready, existing btc_anchor_connector | BTC custody still external, need fiat/BTC on-ramp | Algorand consensus; external BTC custodian | **Strong** — Falcon-1024 available | Medium-Low | Simplest | Medium | 6-10 weeks |

---

## 4. RECOMMENDED PATH

### Primary: Option 6 — Smart-Contract Reserve on Algorand, External BTC Custody

**Rationale**:
- Algorand already chosen in codebase (`btc_anchor_connector.py`, 430 lines)
- Falcon-1024 live on Algorand mainnet since November 2025 — one of the strongest currently evidenced PQ postures among major L1s
- `ALGORAND_DU_POOL_CONTRACT_SPEC.md` already specifies the smart contract
- Simplest path to PoC — single chain, existing tooling (`py-algorand-sdk`)
- BTC custody handled by qualified custodian (Fireblocks, BitGo, or similar)
- TokenFactoryAdapter pattern (already designed) keeps it chain-agnostic for future migration
- Potentially aligns with SEC "Digital Tools" category (utility/governance tokens, not securities) — `UNVERIFIED: taxonomy sourced from secondary reporting only; requires primary SEC/CFTC source confirmation`

### Fallback: Option 2 — Liquid Network + Algorand

**When to invoke**: If BTC custody requirements demand on-chain PQ protection before Algorand bridge is production-ready, or if regulatory pressure requires the BTC itself to be on a PQ-signed chain.

**Trigger**: Quantum threat timeline accelerates to <3 years, or qualified custodian cannot offer PQ-protected BTC vault.

---

## 5. UPS TOKEN DEFINITION

**UPS** = Universal Participation Token (may be publicly branded as **OPS** — naming decision for 012).

### What UPS IS:
- System-level coordination and accounting token
- BTC-collateralized floating-value unit: `ups_per_btc = total_ups_circulating / total_btc_reserve`
- Bio-decaying (Michaelis-Menten demurrage incentivizes velocity and participation)
- Cross-FoundUp universal (works across all FoundUps in the ecosystem)
- Medium of exchange within the protocol
- Canonical constraint: 1 UPS = 1,000 satoshi (at genesis; `genesis_ups_per_btc = 100,000`)

### What UPS IS NOT:
- Not a stablecoin (not pegged to USD or any fiat)
- Not a payment instrument (not designed for merchant payment)
- Not an investment contract (no promise of returns)
- Not a security (utility/coordination function, no managerial effort expectation)
- Not redeemable at par (floating value determined by protocol mechanics)

### Issuance discipline:
- UPS can only be minted against verified BTC reserve deposits
- `max_ups_issuable = total_btc_reserve * ups_per_btc_ratio`
- Issuance cap enforced by smart contract, not human discretion
- Demurrage redistributes decayed UPS: 80% Network Pool, 20% pAVS Treasury

---

## 6. FOUNDUP TOKEN DEFINITION

**F_i** = FoundUp Token (per-project issuance).

### What F_i IS:
- Project-level participation and governance unit
- Fixed supply: 21M per FoundUp (Bitcoin parity)
- S-curve release gated by adoption score (Rogers diffusion model)
- Three states: ICE (staked, no decay), LIQUID (wallet, adaptive decay), VAPOR (exited, fee applied)
- Governance weight within its FoundUp
- Earned through protocol participation (compute work, task completion, verification)

### What F_i IS NOT:
- Not a revenue claim (no promise of dividends or profit share)
- Not transferable to external markets directly (must go F_i -> UPS -> external)
- Not a security (participation recognition, not investment contract)
- Not backed by BTC directly (backed by UPS, which is backed by BTC — indirect chain)

### Issuance discipline:
- S-curve release: `tokens_released = 21,000,000 * sigmoid(adoption_score, k=12, x0=0.5)`
- At 50% adoption: 10.5M tokens released
- At 75% adoption: ~20M tokens released
- Cannot exceed 21M per FoundUp (hard cap in smart contract)
- Mined F_i backed by energy (crystallized compute work), not BTC

### I_i tokens (separate legal review required):
The existing `investor_staking.py` implements a Bitclout-style bonding curve for I_i holders. This is a **distinct legal category** from F_i participation tokens. I_i tokens may constitute securities under Howey analysis (investment of money, expectation of profit from bonding curve). **Do not conflate I_i and F_i in public materials.** I_i requires independent legal review before any deployment.

---

## 7. WALLET + RESERVE DESIGN

### Custody Model

| Component | Custodian | Mechanism | PQ Status |
|-----------|-----------|-----------|-----------|
| BTC Reserve | Qualified custodian (Fireblocks/BitGo) | MPC-CMP multisig (3-of-5 or threshold) | Not PQ yet — no production MPC offers PQ. Mitigated by: (a) BTC public keys hidden until spend, (b) migration path to PQ custody when available |
| UPS/F_i Tokens | Algorand smart contracts | Algorand native assets (ASAs) | **PQ-ready** — Falcon-1024 opt-in keys available |
| L-BTC Bridge (optional) | Liquid Network federation | Federated peg-in/peg-out | **PQ live** — SHRINCS signatures (March 2026) |

### Reserve Visibility Model

All reserve data published on-chain and via dashboard:

| Metric | Update Frequency | Source |
|--------|-----------------|--------|
| Total BTC in vault | Every block (~3.3s on Algorand) | Custodian API + Chainlink PoR feed |
| Total UPS circulating | Every block | Algorand ledger |
| Reserve coverage ratio | Every epoch | `btc_reserve / ups_outstanding` |
| Issuance cap headroom | Every epoch | `max_issuable - currently_issued` |
| Demurrage redistribution | Every mini-epoch (10 ticks) | Smart contract events |
| FoundUp CABR scores | Every epoch | CABR estimator output |

### Access Controls

- BTC vault: threshold signature (no single party can move funds)
- UPS minting: smart contract only (no admin key can mint without BTC deposit proof)
- F_i release: S-curve algorithm only (no manual override)
- Treasury access: CABR-scored routing only (no discretionary withdrawal)
- Emergency: circuit breaker (automatic pause on anomalous conditions), rage quit (Moloch-style fair exit)

### Upgrade Path

1. **Now**: Algorand + external BTC custodian (MPC, not PQ)
2. **When available** (~2027-2028): Migrate BTC custody to PQ-protected vault (Blockstream SHRINCS or equivalent)
3. **When Bitcoin adopts PQ** (BIP-360/361, timeline unknown): Migrate BTC to native PQ addresses
4. **Algorand**: Already PQ-ready, opt-in Falcon-1024 keys. Full protocol migration on their roadmap.

---

## 8. RESERVE ACCOUNTING MODEL

### Core Formulas

```
Reserve Coverage Ratio (RCR):
  RCR = total_btc_reserve / (total_ups_outstanding * ups_btc_rate)
  HEALTHY: RCR >= 1.0
  WARNING: 0.8 <= RCR < 1.0
  CRITICAL: RCR < 0.8
  CIRCUIT BREAKER: RCR < 0.5

Max Issuance:
  max_ups_issuable = total_btc_reserve * base_ups_per_btc * buffer_ratio
  buffer_ratio = 0.9 (10% buffer — never issue to 100% of reserve)

Underwriting Capacity:
  underwriting_available = (total_btc_reserve - emergency_reserve) * utilization_cap
  utilization_cap = 0.7 (max 70% of non-emergency reserve available for underwriting)
  emergency_reserve = 0.15 * total_btc_reserve (15% untouchable)

Dynamic Release (per FoundUp per epoch):
  epoch_budget = min(requested_ups, treasury_ups_available * release_rate)
  routed_ups = epoch_budget * cabr_pipe_size if valve_open else 0
  cabr_pipe_size = cabr_score (0.0 to 1.0)

Liquidity Stress Score:
  stress = (redemption_requests_24h / available_liquid_reserve)
  NORMAL: stress < 0.3
  ELEVATED: 0.3 <= stress < 0.7
  CRITICAL: stress >= 0.7 (triggers redemption queue)

Concentration Risk Score:
  concentration = max_single_holder_pct / total_supply
  HEALTHY: concentration < 0.05 (no single holder > 5%)
  WARNING: 0.05 <= concentration < 0.15
  CRITICAL: concentration >= 0.15

Reserve Health Score (composite):
  health = (RCR_normalized * 0.4) + (stress_inverse * 0.3) + (concentration_inverse * 0.3)
```

### Ledger Design

| Ledger | Type | Contents |
|--------|------|----------|
| BTC Reserve Ledger | On-chain (Algorand) + off-chain custodian | Deposit proofs, balance snapshots, withdrawal records |
| UPS Issuance Ledger | On-chain (Algorand) | Mint events, burn events, demurrage redistribution |
| F_i Release Ledger | On-chain (Algorand) | S-curve milestone triggers, pool distribution events |
| CABR Routing Ledger | On-chain (Algorand) | Epoch budgets, pipe sizes, actual flows |
| Epoch Snapshot | On-chain + dashboard | All ratios, scores, and sentinel alerts per epoch |

### Insolvency Protocol

If `RCR < 0.5` for 3 consecutive epochs:

1. **Circuit breaker fires** — all new issuance halted
2. **Redemption queue activated** — FIFO, pro-rata if insufficient
3. **Rage quit enabled** — any holder can exit at current RCR-adjusted rate
4. **Sentinel escalation** — requires 012 governance decision within 72 hours
5. **No hidden bail-in** — if reserve is insufficient, the shortfall is public and visible

---

## 9. FOUNDUP UNDERWRITING ENGINE

### How Reserve Capital Supports FoundUps

BTC reserve does **not** flow directly to FoundUps. The flow is:

```
BTC Reserve -> backs UPS -> UPS routed via CABR -> FoundUp treasury (F_i Fund, 4%)
```

### Access Criteria (CABR-scored, not discretionary)

| Metric | Weight | Source |
|--------|--------|--------|
| Task completion rate | 25% | FAM event: `proof_submitted` + `verification_recorded` |
| Verification participation | 25% | FAM event: `verification_recorded` (as verifier) |
| Unique contributor count | 20% | Distinct 012 participants |
| Governance engagement | 15% | Vote participation rate |
| Cross-FoundUp collaboration | 15% | Inter-project task completion |

**CABR Score** = weighted sum (0.0 to 1.0) = pipe_size controlling UPS flow.

### Access Model: Streaming Release (not grant, not loan)

- UPS flows to FoundUp treasury **per epoch**, proportional to CABR score
- `epoch_flow = epoch_budget * cabr_pipe_size`
- Flow stops if CABR score drops (valve closes)
- Flow resumes if CABR score recovers (valve reopens)
- No lump-sum grants — prevents extraction
- No loans — no debt obligation, no repayment expectation

### Extraction Prevention

1. **No admin withdrawal key** — funds released only by smart contract logic
2. **CABR gating** — zero flow if CABR score = 0
3. **Epoch caps** — maximum flow per epoch regardless of CABR score
4. **Concentration sentinel** — alerts if single FoundUp absorbs >10% of total epoch flow
5. **Milestone gates** — certain flow thresholds require published milestone proof

### FoundUp Failure

- CABR score drops toward 0 -> flow stops automatically
- Remaining F_i tokens stay on S-curve (unreleased tokens never enter circulation)
- No "clawback" from participants who already earned F_i through work
- Failed FoundUp is flagged in public dashboard, not hidden

### FoundUp Success

- CABR score stays high -> sustained flow
- As FoundUp matures, it earns more from its own fee revenue and less from system underwriting
- Degressive tier model: once a FoundUp reaches self-sustainability, system underwriting tapers
- Successful FoundUp becomes net contributor to ecosystem (fees flow back to BTC reserve)

---

## 10. TOKEN STRATEGY

### Recommendation: Layered Tokens (not single ubiquitous token)

The system requires three distinct token types because they serve fundamentally different economic functions:

| Token | Layer | Function | Decay | Supply | Backed By |
|-------|-------|----------|-------|--------|-----------|
| UPS | System | Coordination, accounting, medium of exchange | Yes (bio-decay) | Floating (minted against BTC) | BTC reserve (direct) |
| F_i | FoundUp | Participation, governance, earned-work record | Adaptive (ICE/LIQUID/VAPOR) | 21M fixed per FoundUp | UPS (indirect via reserve) |
| I_i | Investor | Bonding curve capital | No | Dynamic (bonding curve) | Bonding curve mechanics |

**Why not single token**: UPS must decay (velocity incentive). F_i must not decay when staked (long-term commitment incentive). These are contradictory requirements. Merging them would break the economic model.

**I_i decision**: `LEGAL_REVIEW_REQUIRED — FROZEN`

I_i tokens carry significant securities risk (bonding curve = investment contract under Howey). All I_i implementation, simulation publication, and investor-facing language is frozen until independent legal counsel provides a written opinion.

Options (for legal review, not for implementation):
1. **Defer I_i entirely** until legal review complete (recommended for PoC/Prototype)
2. **Restrict I_i to accredited participants** (Reg D exemption)
3. **Remove I_i** and use only F_i earned through work (safest, but eliminates capital formation channel)

---

## 11. SENTINEL ARCHITECTURE

### Named Sentinel Suite: `modules/infrastructure/reserve_sentinels/`

| # | Sentinel | Mission | Module Path | Inputs | Triggers | Actions | Heartbeat |
|---|----------|---------|-------------|--------|----------|---------|-----------|
| 1 | **ReserveSentinel** | Monitor BTC reserve integrity | `src/reserve_sentinel.py` | Custodian balance API, Algorand ledger, UPS supply | RCR < 0.8, reserve decrease without matching burn | Alert (< 0.8), soft pause (< 0.6), circuit breaker (< 0.5) | Every block |
| 2 | **IssuanceSentinel** | Prevent over-issuance | `src/issuance_sentinel.py` | UPS mint events, reserve proofs | Mint without deposit proof, issuance exceeds cap | Hard pause on minting, governance escalation | Every block |
| 3 | **LiquiditySentinel** | Monitor redemption/exit pressure | `src/liquidity_sentinel.py` | Redemption queue, exit events, DEX volume | Stress score > 0.7, exit velocity spike | Redemption queue activation, epoch flow reduction | Every mini-epoch |
| 4 | **GovernanceSentinel** | Detect governance capture | `src/governance_sentinel.py` | Vote events, proposal history, voter concentration | Single-entity >33% vote weight, rapid parameter changes | Alert, proposal delay, quorum increase | Every epoch |
| 5 | **AdversarialSentinel** | Detect manipulation patterns | `src/adversarial_sentinel.py` | All transaction data, CABR scores, cross-FoundUp flows | Wash trading, Sybil swarms, reciprocity rings, threshold gaming | Alert, auto-quarantine of suspicious accounts | Every mini-epoch |
| 6 | **WalletSentinel** | Monitor wallet integrity | `src/wallet_sentinel.py` | Algorand key events, signature types, address patterns | Legacy (non-PQ) key usage after migration deadline, unusual multi-sig changes | Alert, forced PQ key rotation reminder | Every epoch |
| 7 | **QuantumMigrationSentinel** | Track PQ migration progress | `src/quantum_migration_sentinel.py` | Key type census, NIST announcements, threat intel | PQ adoption < threshold, new quantum milestone | Dashboard update, migration urgency escalation | Weekly |
| 8 | **IronClawSentinel** | Enforcement and coordination | `src/ironclaw_sentinel.py` | All other sentinel alerts, system health composite | Multiple sentinel alerts concurrent, composite health < threshold | Cross-sentinel escalation, system-wide pause authority, 012 notification | Every block |

### Interface Contract (all sentinels)

```python
class BaseSentinel(ABC):
    @abstractmethod
    def check(self) -> SentinelResult: ...

    @abstractmethod
    def get_health(self) -> float: ...  # 0.0-1.0

@dataclass
class SentinelResult:
    sentinel_name: str
    status: Literal["healthy", "warning", "critical", "paused"]
    score: float  # 0.0-1.0
    alerts: List[SentinelAlert]
    timestamp: str  # UTC ISO

@dataclass
class SentinelAlert:
    severity: Literal["info", "warning", "critical"]
    message: str
    action_taken: Literal["alert_only", "soft_pause", "hard_pause", "governance_escalation", "auto_quarantine"]
    requires_012: bool
    false_positive_risk: Literal["low", "medium", "high"]
```

### Heartbeat Hooks

Every sentinel emits to:
1. `alerts/sentinel/{sentinel_name}_{timestamp}.json` (durable artifact, same pattern as `preflight_resolution.py`)
2. Dashboard websocket feed (real-time)
3. `on_preflight_fail()` dispatch contract (for critical alerts only)

---

## 12. BAD ACTOR DEFENSE MAP

| # | Attack | Path | Detection | Prevention | Recovery |
|---|--------|------|-----------|------------|----------|
| 1 | **Reserve misreporting** | Custodian reports false BTC balance | ReserveSentinel cross-checks custodian API vs on-chain proofs, Chainlink PoR feed | Multiple independent reserve attestation sources, PCAOB audit | Freeze issuance, activate emergency reserve, switch custodian |
| 2 | **Over-issuance** | Compromised minting key or contract bug | IssuanceSentinel monitors mint events against deposit proofs | Smart contract cap enforcement, no admin mint key, formal verification of mint logic | Burn excess tokens, compensate affected holders from emergency reserve |
| 3 | **Governance capture** | Single entity accumulates >33% vote weight | GovernanceSentinel monitors voter concentration | Quadratic voting, delegation caps, time-locked proposals | Quorum increase, proposal delay, emergency 012 veto |
| 4 | **Oracle manipulation** | False BTC price feed to inflate UPS value | Cross-oracle validation (multiple price sources) | Median-of-N oracle design, outlier rejection | Revert to last-known-good price, pause affected operations |
| 5 | **Liquidity extraction** | Coordinated mass exit to drain reserve | LiquiditySentinel monitors exit velocity | Epoch-based exit caps, dynamic exit friction, rage quit fairness | FIFO redemption queue, pro-rata if insufficient |
| 6 | **Insider routing** | FoundUp creator routes excess UPS to self | AdversarialSentinel monitors CABR score vs actual flow | CABR-only routing (no manual override), concentration caps | Quarantine FoundUp, freeze excess flow, governance review |
| 7 | **Wash demand** | Fake activity to inflate CABR score | AdversarialSentinel (reciprocity detector, ring detector) | Verification requires independent validators, Sybil detection | Score reset, quarantine period, contributor audit |
| 8 | **Sybil swarms** | Fake 012 identities to dilute pools | ParticipationSentinel (existing, 571 lines) | Proof-of-work participation thresholds, compute-weight requirements | Quarantine flagged accounts, redistribute ill-gotten tokens |
| 9 | **Bridge asset mismatch** | BTC-Algorand bridge claims more BTC than exists | ReserveSentinel cross-checks bridge claims vs custodian | Independent bridge auditor, Chainlink PoR | Pause bridge, forensic audit |
| 10 | **Smart contract exploit** | Bug in Algorand contract enables unauthorized operations | Formal verification, audit, bug bounty | Code review, timelocked upgrades, proxy pattern with guardian | Pause contract, deploy fix, compensate from emergency reserve |
| 11 | **Slow rug by treasury** | Gradual extraction via parameter manipulation | GovernanceSentinel monitors parameter change history | All parameter changes timelocked (48h+), public and logged | Revert parameter, governance investigation |
| 12 | **Narrative manipulation** | False claims about reserve, returns, or partnerships | IronClawSentinel monitors public communications (manual) | Clear public positioning rules, legal review of all materials | Retraction, correction, legal response |
| 13 | **Collusion** | FoundUp creators + reserve managers coordinate extraction | AdversarialSentinel cross-correlation analysis | Separation of roles (custodian != FoundUp creator != governance), rotation | Forensic audit, legal action, emergency reserve activation |

---

## 13. TETHER / GENIUS ACT DISCIPLINE MIRROR

### What to Mirror

| Discipline | Centralized Version (Tether/GENIUS) | FoundUps Decentralized Version | New Risks | Mitigation |
|-----------|--------------------------------------|-------------------------------|-----------|------------|
| **Disciplined issuance** | Issuer mints against USD deposits | Smart contract mints against BTC deposit proofs | Contract bug could bypass | Formal verification, IssuanceSentinel |
| **Proof of reserves** | Monthly attestation by auditor | Real-time on-chain dashboard + Chainlink PoR | Dashboard could display stale data | Multiple sources, ReserveSentinel cross-check |
| **Redemption logic** | 2-day redemption at par (GENIUS Act) | Epoch-based exit: F_i -> UPS -> external (with fees) | Exit fees create friction; no par guarantee | Transparent fee schedule, rage quit option |
| **Reserve segregation** | Separate accounts, no commingling | Smart contract-enforced separation, emergency reserve isolated | Contract upgrade could bypass | Timelocked upgrades, guardian key |
| **Continuous monitoring** | Internal compliance team | Sentinel suite (8 autonomous monitors) | False positives, sentinel failure | Redundancy, IronClaw coordinator, manual override |
| **Anti-manipulation** | Market surveillance by issuer | AdversarialSentinel + ParticipationSentinel | Sophisticated attacks may evade automated detection | Layered detection, human escalation, bounty program |

### What NOT to Mirror

| Feature | Why Not |
|---------|---------|
| Centralized issuer privilege | Contradicts decentralization thesis |
| Opaque treasury discretion | Creates BitClout-style trust problem |
| Fiat-only reserve | FoundUps is BTC-anchored by design |
| Regulatory dependence as trust anchor | Regulation should inform, not replace, cryptographic trust |
| Identity capture by default | Pseudonymous by default; KYC only at custodian boundary |

---

## 14. TIME-HORIZON MODEL

| Dimension | 3-Year | 5-Year (Recommended) | 10-Year |
|-----------|--------|---------------------|---------|
| **Quantum risk** | Low (Google estimates ~2029 threat) | Medium (coincides with threat window) | High (quantum computers likely operational) |
| **Regulatory clarity** | Partial (GENIUS Act rules finalized, MiCA enforced, but crypto taxonomy still evolving) | Good (2-3 cycles of regulatory refinement) | Unknown (regime change risk) |
| **FoundUp ecosystem size** | Early (100-500 FoundUps) | Growth (3,500+ target for self-sustainability) | Mature (20,000+) |
| **BTC reserve growth** | Genesis phase, small reserve | Meaningful reserve if adoption tracks | Large reserve, systemic relevance |
| **Technology migration** | Current stack adequate | May need PQ custody migration | Full PQ migration required |
| **Staker viability** | 10x ratio possible for early cohort | Proven or disproven by data | Dilution risk if uncapped |
| **Legal precedent** | Emerging (SEC taxonomy new) | Established (multiple enforcement cycles) | Mature (clear frameworks) |

### Recommendation: 5-Year Primary Cycle

**Why not 3-year**: Too short to prove real value creation. Staker viability models show 10x distribution ratio in 10-26 months, but ecosystem self-sustainability requires ~3,500 FoundUps — unlikely in 3 years. A 3-year cycle creates pressure to show results before the system can organically produce them, which incentivizes overclaiming.

**Why not 10-year**: Quantum threat window (est. 2029-2032) makes 10-year commitments risky without guaranteed PQ migration. Regulatory landscape will shift unpredictably. Lock-in of 10 years creates political and governance risk. Also: attention spans are shorter than 10 years.

**Why 5-year**: Aligns with quantum threat preparation window. Long enough for ecosystem to reach self-sustainability (3,500+ FoundUps). Short enough to allow structural review and parameter adjustment. Matches typical venture lifecycle. Staker viability projections are credible at this horizon.

---

## 15. STRESS-TEST: "10x TO 100x" FRAMING

### Is it structurally real?

The simulator models show:
- 10 genesis stakers at $1K BTC each: **10x distribution ratio in 10 months** (baseline scenario with 20K FoundUps Y1)
- I_i bonding curve projections: `[REDACTED — LEGAL_REVIEW_REQUIRED. Do not publish externally. Internal simulator reference: investor_staking.py. Aggressive assumptions required. Securities enforcement risk if marketed.]`
- Genesis members earn ecosystem-wide (all FoundUps), future members earn only on their FoundUps

### Assumptions required for 10x:
1. Ecosystem reaches 20,000+ FoundUps in Year 1 (aggressive)
2. BTC reserve grows through subscriptions, fees, exits
3. CABR scoring works as designed (no gaming)
4. Token velocity stays within modeled range
5. No black swan (regulatory, market, or technical)

### Where it breaks:
- **Adoption stall**: If only 500 FoundUps in Year 1, 10x requires 3+ years
- **BTC price crash**: Reserve value drops, UPS weakens, distribution ratios compressed
- **Regulatory action**: If tokens classified as securities, system must restructure
- **Mass exit**: If exit pressure exceeds reserve capacity, RCR drops below 1.0
- **Gaming**: If CABR scores are manipulated, distribution becomes unfair

### What should be said instead:

**NEVER say**: "10x returns", "100x returns", "guaranteed", "profit", "investment returns"

**SAY**: "Protocol mechanics determine participation distribution ratios based on ecosystem activity, reserve health, and CABR scoring. Historical simulations under baseline assumptions show favorable distribution dynamics for early participants. Actual distributions depend on ecosystem adoption, market conditions, and protocol parameters. Past simulations are not predictions of future performance."

**For I_i bonding curve**: `LEGAL_REVIEW_REQUIRED` — All I_i simulation outputs are quarantined. Do not publish any bonding curve return projections externally. Do not implement I_i token contracts. Do not create investor-facing materials referencing I_i mechanics. This gate remains closed until independent legal counsel reviews the I_i structure under Howey analysis and provides a written opinion.

---

## 16. TRUST STACK (Minimum Credible for Launch)

| Layer | Requirement | Status |
|-------|-------------|--------|
| Smart contract transparency | All contract source code published, verified on-chain | Required for PoC |
| Proof-of-reserve dashboard | Real-time BTC balance + UPS supply + RCR | Required for Prototype |
| Sentinel logs | All sentinel alerts publicly queryable | Required for Prototype |
| Formal verification | Core mint/burn/transfer logic formally verified | Required for MVP |
| Independent audit | PCAOB-standard audit of reserve + smart contracts | Required for MVP |
| Adversarial simulation | Red team exercise before mainnet launch | Required for MVP |
| Bug bounty program | Ongoing, funded from treasury | Required for MVP |
| Public treasury views | All FoundUp flows, CABR scores, epoch distributions visible | Required for Prototype |
| Legal entity wrapper | DAO LLC (Wyoming or equivalent) | Required for Prototype |
| Open-source enforcement rules | All parameter change rules published and immutable | Required for MVP |

---

## 17. LEGAL / CLAIMS RISK MATRIX

| Phrase | Technical Meaning | Public Interpretation | Legal Danger | Safer Alternative |
|--------|-------------------|----------------------|-------------|-------------------|
| "Backed" | BTC in reserve supports UPS value | "My money is safe and guaranteed" | Tether was fined $41M for unsubstantiated "backed" claims | "BTC-collateralized" (with published proof) |
| "Staking" | Locking tokens for governance weight | "Passive income from holding" | SEC staff guidance clarified certain protocol staking is NOT securities (May 29, 2025; staff guidance, not rule — fact-dependent), but context matters | "Protocol participation lock" or just "staking" (per SEC guidance, this is now safer) |
| "Yield" | Demurrage redistribution to active participants | "Interest rate on my deposit" | Triggers investment contract analysis | "Participation rewards" or "epoch distributions" |
| "Return" | Distribution ratio from pool mechanics | "Guaranteed profit" | Immediate Howey trigger | "Distribution ratio" or "protocol allocation" |
| "Stable" | Reserve-collateralized floating value | "Pegged to something, won't lose value" | Triggers GENIUS Act scrutiny | "Reserve-supported" or "collateral-backed floating value" |
| "Guaranteed" | Nothing in crypto is guaranteed | "Zero risk" | Fraud if used with value claims | Never use this word |
| "Safe" | PQ signatures, audit trail | "Can't lose money" | Misleading if applied to value | "Audited" or "formally verified" (for code); never for value |
| "Investment" | Capital allocation decision | "Securities offering" | Direct Howey invocation | "Protocol participation" |
| "Reserve" | BTC held in custody backing UPS | Could imply bank-like reserve | Acceptable if provable and audited | Use freely, but always with proof |
| "Underwritten" | CABR-scored UPS flow supports FoundUp | "Insured" or "guaranteed" | Insurance regulation if misinterpreted | "Protocol-supported" or "CABR-routed" |

---

## 18. COMPARATIVE POSITIONING

| Competitor | What They Solve | What They Don't | FoundUps Stronger | FoundUps Weaker | FoundUps Must Not Overclaim |
|-----------|----------------|-----------------|-------------------|-----------------|---------------------------|
| **Tether/USDT** | Dollar-denominated stability, massive liquidity | Transparency, centralization risk, regulatory compliance | Transparent reserve (on-chain), no centralized issuer | Liquidity (orders of magnitude less), no fiat peg | "We're more transparent than Tether" (prove it first with audits) |
| **GENIUS Act issuers** | Regulatory compliance, consumer protection | Innovation, decentralization, global access | No regulatory dependency for trust, pseudonymous | No regulatory safe harbor, no fiat backing | "We're compliant" (we're not a GENIUS issuer — different category) |
| **BitClout/DeSo** | Creator economy tokenization | Trust, transparency, exit mechanism | Transparent exit path, CABR-scored routing, no black box | Network effects, user base | "We're not BitClout" (address the structural difference: exit exists) |
| **Wrapped BTC (wBTC/tBTC)** | BTC on other chains | Value creation beyond custody | Productive underwriting (BTC isn't idle), participation economy | Custody simplicity (wrapped BTC is pure bridging) | "Our BTC is more productive" (prove underwriting creates measurable value) |
| **Bitcoin treasury companies** | BTC exposure via equity | Decentralization, participation, protocol mechanics | No corporate intermediary, direct protocol participation | Regulatory clarity (equity is well-understood), liquidity | "We're better than holding MSTR stock" (different risk profile entirely) |
| **Algorand (native)** | PQ-ready smart contracts | BTC integration, reserve economics | BTC-anchored reserve (Algorand alone doesn't have BTC backing), economic model | Algorand's ecosystem maturity, developer tools | "We add BTC reserve to Algorand" (we use Algorand, we don't improve it) |

### Strongest Narrative Edge

"FoundUps turns idle BTC into productive underwriting for real ventures, with transparent reserve mechanics, algorithmic distribution, and quantum-resistant infrastructure — without a centralized issuer, without promises of returns, and without a black box treasury."

---

## 19. PUBLIC POSITIONING STATEMENTS

### Technical
"FoundUps operates a BTC-collateralized, algorithmically governed reserve system on Algorand's quantum-resistant infrastructure. Every token issuance is backed by verifiable BTC deposits. Every distribution is determined by CABR protocol scoring. Every reserve balance is publicly auditable in real time."

### Builder / Participant
"Participate in FoundUps by contributing real work. Earn protocol tokens through task completion, verification, and governance. Your contributions are scored by the CABR engine, and protocol distributions flow proportionally. No promises — protocol mechanics determine outcomes."

### User-Facing
"FoundUps is a participation system where your work earns protocol tokens backed by a transparent Bitcoin reserve. You can see the reserve balance, the scoring algorithm, and the distribution rules at any time. You exit on your terms, with published fee schedules and no lock-in traps."

**Hard rule**: All three statements avoid "returns," "profit," "investment," "guaranteed," "yield," and "stable." If any public material contains these words in a value context, it must be flagged and rewritten before publication.

---

## 20. RISK REGISTER

| # | Category | Risk | Likelihood | Impact | Mitigation | Owner |
|---|----------|------|-----------|--------|------------|-------|
| 1 | Technical | Smart contract exploit drains reserve | Low | Critical | Formal verification, audit, bug bounty, emergency reserve (15%) | Engineering |
| 2 | Technical | BTC custodian compromise | Low | Critical | MPC/multisig, no single-key custody, custodian insurance | Operations |
| 3 | Technical | Algorand network failure/fork | Very Low | High | Chain-agnostic adapter pattern enables migration | Engineering |
| 4 | Legal | Tokens classified as securities | Medium | Critical | Utility/governance token design, no return promises, independent legal review. Note: "Digital Tools" SEC taxonomy category is `UNVERIFIED` from primary source | Legal |
| 5 | Legal | Money transmitter classification | Medium | High | No direct BTC-to-token exchange by FoundUps entity; users interact with protocol | Legal |
| 6 | Legal | I_i bonding curve = investment contract | High | High | Defer I_i until legal review; restrict to accredited if launched | Legal |
| 7 | Governance | SmartDAO capture by single entity | Low | High | GovernanceSentinel, quadratic voting, delegation caps | Governance |
| 8 | Governance | Parameter manipulation (slow rug) | Low | High | All changes timelocked 48h+, public, logged | Governance |
| 9 | Liquidity | Mass exit overwhelms reserve | Medium | High | Dynamic exit friction, epoch caps, rage quit fairness, emergency reserve | Economics |
| 10 | Liquidity | BTC price crash reduces reserve value | Medium | Medium | Reserve is measured in BTC not USD; UPS floats; system is BTC-denominated | Economics |
| 11 | Custody | PQ migration needed before infrastructure ready | Medium | Medium | Algorand PQ live now; BTC custody PQ gap monitored by QuantumMigrationSentinel | Engineering |
| 12 | Quantum | Quantum computer breaks ECDSA before Bitcoin migrates | Low (before 2030) | Critical | Reserve on Algorand (PQ); BTC in hidden public keys; migration plan ready | Engineering |
| 13 | Adversarial | CABR score gaming via Sybil/wash activity | Medium | Medium | ParticipationSentinel (live), threshold gaming spec ready for implementation | Security |
| 14 | Adversarial | Coordinated attack on BTC-Algorand bridge | Low | High | Independent bridge auditor, Chainlink PoR, ReserveSentinel | Security |
| 15 | Narrative | "Hotel California" branding creates BitClout comparison | High | High | **Immediate**: rename to "Permanent Reserve Collateral with Transparent Exit" | Marketing |
| 16 | Narrative | "10x returns" language leaks into public materials | Medium | Critical | Terminology migration table enforced; all materials reviewed before publication | Marketing |
| 17 | Regulatory | AML/KYC requirements at custodian boundary | High | Medium | KYC at custodian (BTC deposit), pseudonymous within protocol | Legal |

---

## 21. PROMETHEUS BUILD PLAN

### Phase 1: PoC (Weeks 1-10)

**Scope**: Prove BTC-to-Algorand reserve flow works end-to-end in testnet.

| Item | Build | Don't Build |
|------|-------|-------------|
| Algorand testnet smart contracts | Du Pool distribution contract (from existing spec), UPS ASA creation, F_i ASA creation | Production custody, mainnet deployment |
| BTC deposit simulation | Mock BTC deposit proof -> Algorand mint event | Real BTC custody integration |
| CABR scoring integration | Wire `cabr_estimator.py` to Algorand flow router | Full anti-gaming suite |
| Reserve dashboard (v0) | Read-only page showing reserve ratio, UPS supply, CABR scores | Public deployment |
| Sentinel (v0) | ReserveSentinel + IssuanceSentinel (alert-only mode) | Full sentinel suite |
| Tests | 30+ tests covering mint/burn/route/exit paths | Stress testing, adversarial simulation |

**Dependencies**: Algorand SDK (`py-algorand-sdk`), testnet account, existing simulator modules.

**Audit points**: Smart contract review by second engineer before any testnet deployment.

**Exit criteria**: BTC deposit proof -> UPS minted -> CABR-routed to FoundUp -> F_i distributed -> exit path works. All on testnet.

### Phase 2: Prototype (Weeks 11-20)

**Scope**: Add real BTC custody, sentinel suite, dashboard, legal entity.

| Item | Build | Don't Build |
|------|-------|-------------|
| BTC custody integration | Fireblocks or BitGo sandbox API, MPC wallet creation | Mainnet BTC operations |
| Algorand mainnet prep | Contract compilation for mainnet, parameter review | Mainnet deployment |
| Sentinel suite (v1) | All 8 sentinels in alert-only mode | Auto-pause (deferred to MVP) |
| Reserve dashboard (v1) | Public-facing, real-time reserve data | User account features |
| Legal entity | Wyoming DAO LLC formation | Full regulatory filing |
| Proof-of-reserve feed | Chainlink PoR integration (testnet) or custom oracle | Production oracle |
| Terminology audit | All materials reviewed against legal risk matrix | Public launch |
| PQ key migration | Enable Falcon-1024 keys for all Algorand accounts | Force migration |

**Dependencies**: Custodian sandbox API access, legal counsel, Chainlink testnet.

**Audit points**: Independent smart contract audit, legal review of token classification, custodian due diligence.

**Exit criteria**: Real BTC (testnet/sandbox) deposited via custodian API -> UPS minted on Algorand testnet -> full sentinel suite monitoring -> dashboard showing live data -> legal entity formed.

### Phase 3: MVP (Weeks 21-36)

**Scope**: Mainnet launch with minimum viable trust stack.

| Item | Build | Don't Build |
|------|-------|-------------|
| Algorand mainnet deployment | Smart contracts, ASAs, CABR routing live | I_i bonding curve (deferred, legal review) |
| BTC custody (production) | Mainnet MPC wallet with qualified custodian | Self-custody |
| Sentinel suite (v2) | Alert + soft-pause modes, IronClaw coordinator | Full auto-remediation |
| Dashboard (v2) | Public, audited, with sentinel alert feed | Mobile app |
| Formal verification | Core mint/burn/transfer logic | Entire contract suite |
| Independent audit | PCAOB-standard reserve + smart contract audit | Continuous audit (future) |
| Bug bounty | Funded program, published scope | Red team exercise (Phase 4) |
| Adversarial simulation | Tabletop exercise with known attack vectors | Full red team |
| PQ migration plan | Published migration timeline, key rotation tools | Forced migration |

**Dependencies**: Successful Phase 2 audit, legal clearance, custodian production agreement, Algorand mainnet gas funding.

**Audit points**: Pre-launch: formal verification report, independent audit report, legal opinion letter. Post-launch: monthly reserve attestation, continuous sentinel monitoring.

**Exit criteria**: Live on Algorand mainnet. BTC reserve verifiable. UPS/F_i tokens minting and distributing. 8 sentinels monitoring. Dashboard public. Audit report published. Bug bounty live. Legal entity operational.

---

## 22. CURSOR EXECUTION PACKET

### New Module Structure

```
modules/infrastructure/reserve_sentinels/
├── README.md
├── INTERFACE.md
├── ModLog.md
├── module.json
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── base_sentinel.py          # ABC + SentinelResult/SentinelAlert dataclasses
│   ├── reserve_sentinel.py       # BTC reserve integrity monitor
│   ├── issuance_sentinel.py      # Over-issuance prevention
│   ├── liquidity_sentinel.py     # Exit pressure monitor
│   ├── governance_sentinel.py    # Governance capture detection
│   ├── adversarial_sentinel.py   # Manipulation pattern detection
│   ├── wallet_sentinel.py        # Wallet/key integrity
│   ├── quantum_migration_sentinel.py  # PQ migration tracker
│   └── ironclaw_sentinel.py      # Cross-sentinel coordinator
└── tests/
    ├── conftest.py
    ├── test_reserve_sentinel.py
    ├── test_issuance_sentinel.py
    ├── test_liquidity_sentinel.py
    ├── test_governance_sentinel.py
    ├── test_adversarial_sentinel.py
    ├── test_wallet_sentinel.py
    ├── test_quantum_migration_sentinel.py
    └── test_ironclaw_sentinel.py

modules/blockchain/src/
├── algorand_reserve_contract.py  # Du Pool + UPS mint/burn (from existing spec)
├── algorand_token_factory.py     # ASA creation for UPS/F_i (TokenFactoryAdapter)
├── btc_custody_adapter.py        # Fireblocks/BitGo API adapter
├── reserve_proof_oracle.py       # Chainlink PoR or custom oracle
└── tests/
    ├── test_algorand_reserve_contract.py
    ├── test_algorand_token_factory.py
    ├── test_btc_custody_adapter.py
    └── test_reserve_proof_oracle.py
```

### Implementation Priority

1. `base_sentinel.py` — ABC + dataclasses (all sentinels depend on this)
2. `reserve_sentinel.py` — most critical sentinel
3. `issuance_sentinel.py` — second most critical
4. `algorand_reserve_contract.py` — core smart contract logic
5. `btc_custody_adapter.py` — custodian integration
6. `algorand_token_factory.py` — ASA creation
7. `reserve_proof_oracle.py` — PoR feed
8. Remaining sentinels (liquidity, governance, adversarial, wallet, quantum, ironclaw)

### Existing Code to Reuse

| Existing Module | Reuse For |
|----------------|-----------|
| `btc_reserve.py` (442 lines) | Reserve accounting logic — extract formulas into sentinel checks |
| `btc_anchor_connector.py` (430 lines) | Algorand↔BTC bridge pattern — extend for production custody |
| `participation_sentinel.py` (571 lines) | Pattern for AdversarialSentinel — Sybil/velocity/concentration detection |
| `cabr_estimator.py` (278 lines) | CABR scoring — integrate with Algorand flow routing |
| `cabr_flow_router.py` (75 lines) | Flow routing math — deploy as smart contract logic |
| `circuit_breaker.py` | Emergency stop pattern — integrate into IronClawSentinel |
| `emergency_reserve.py` | Reserve buffer logic — integrate into ReserveSentinel thresholds |
| `ALGORAND_DU_POOL_CONTRACT_SPEC.md` (370 lines) | Smart contract spec — implement directly |
| `THRESHOLD_GAMING_SENTINEL_SPEC.md` (427 lines) | Anti-gaming patterns — implement in AdversarialSentinel |
| `preflight_resolution.py` (231 lines) | Alert dispatch pattern — reuse for sentinel alert artifacts |

### Key Dependencies

```
py-algorand-sdk>=2.0.0    # Algorand integration
fireblocks-sdk>=2.0.0     # BTC custody (or bitgo-sdk equivalent)
pycryptodome>=3.20.0       # Cryptographic primitives
```

---

## APPENDIX A: "HOTEL CALIFORNIA" CORRECTION

### Current Language (DANGEROUS)

"Hotel California: BTC enters, never exits"

### Why This Is Dangerous

BitClout (DeSo) used an identical one-way BTC bridge. SEC charged the founder (July 2024) with fraud and unregistered securities offering. The one-way mechanism was specifically cited as evidence of investor deception.

### What's Actually Different

FoundUps users CAN exit: F_i -> UPS -> external (with fee schedule). The BTC reserve itself is permanent — it stays as collateral backing UPS. Users don't get "their" BTC back; they get UPS-denominated value that can be exchanged externally.

### Corrected Language

"BTC deposited into the FoundUps reserve permanently backs UPS token issuance. Participants exit the system through the published token exchange path (F_i -> UPS -> external) with transparent fee schedules. The reserve grows over time, strengthening UPS collateralization. The reserve is not a deposit account — it is protocol infrastructure."

### Legal Review Required

Even with corrected language, the permanent nature of the BTC reserve needs formal legal review. The question is whether "permanent collateral with economic exit" is legally distinguishable from "one-way conversion with no redemption." The answer likely depends on:
1. Whether UPS-to-external exchange provides genuine economic equivalence
2. Whether fee schedules are reasonable (not punitive enough to be de facto lock-in)
3. Whether the exit path is actually functional and liquid (not theoretical)

---

## APPENDIX B: NAMING DECISION NEEDED

| Current | Alternative | Decision |
|---------|-------------|----------|
| UPS (Universal Participation Token) | OPS (as used in prompt) | 012 to decide public branding |
| F_i (FoundUp Token) | Keep as is | Technical name; public name TBD |
| I_i (Investor Token) | Defer or remove | Legal review required before any naming |
| Hotel California | Permanent Reserve Collateral | **Change immediately** |
| Du Pool | Protocol Participation Pool | Consider for public materials |
| Bio-decay | Participation-incentive decay | Consider for public materials |

---

*Generated: 2026-04-20*
*Author: 0102 (Claude Opus 4.6), CW2*
*Truth-hardened: 2026-04-20, BTC-ARCH1 slice (CW2)*
*Status: DRAFT — 012 review required, legal counsel review required before any public use*
*Legal gates: I_i bonding curve FROZEN (LEGAL_REVIEW_REQUIRED), SEC taxonomy UNVERIFIED from primary source*
*WSP: 97 (no overclaiming), 26 (tokenization), 29 (CABR)*
