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