# FoundUps Investor Economics

**Version**: 1.0.0
**Date**: 2026-02-10
**Status**: FROZEN/EXPLORATORY - NOT CANONICAL

> **WARNING**: This document describes an exploratory I_i bonding curve model
> that is NOT the canonical staker architecture. Do NOT implement.
>
> **Canonical staker model**: `pool_distribution.py` (Du pool stakers)
> **Decision**: 012 directive 2026-04-20 (AW4 DUPOOL-TRUTH1)

## Executive Summary (EXPLORATORY - NOT FOR IMPLEMENTATION)

This exploratory model described an early capital provider mechanism:
- **Guaranteed Floor**: 10x buyout option at Year 3
- **Unlimited Ceiling**: 100x-1000x+ if network succeeds
- **Pool Participation**: 12.16% pre-hurdle, 0.64% after repayment target is met
- **Perpetual Tail**: 0.64% continues permanently once post-hurdle mode is locked
- **Transferable Rights**: vested investor rights can be transferred
- **BTC Backing**: Investment becomes permanent network collateral

## Underwriting Guardrails (Simulator-Enforced)

The simulator now enforces conservative underwriting outputs in addition to
upside projections:

- **Conservative target (3Y)**: `2.5x` total value multiple
- **Conservative target (10Y)**: `10x` total value multiple
- **Coverage covenants**:
  - `P50 coverage >= 1.25`
  - `P90 coverage >= 1.00`
- **Coverage definition**:
  - `(escrow releasable + protocol fees + refinancing + reserve buffer) / buyout liability`

Implementation note:
- Simulator contract is dynamic in
  `modules/foundups/simulator/economics/investor_staking.py`:
  - `12.16%` while cumulative distributions are below the repayment target
  - `0.64%` after cumulative distributions meet/exceed the repayment target
- Once the post-hurdle mode is reached, it is locked and does not revert back to
  `12.16%` even if new principal enters later.
- Repayment target default is `10x` of invested BTC
  (`repayment_target_multiple = 10.0`).

**Comparable**: BitClout/DeSo raised [$200M from a16z, Sequoia, Coinbase Ventures](https://www.theblock.co/post/118133/bitclout-creator-decentralized-social-blockchain-200-million-funding-a16z-others) in 2021.

---

## Investment Rounds

### Bonding Curve Pricing

Investment tokens (I_i) are priced on a quadratic bonding curve:

```
Price(supply) = k × supply²

Where:
  k = 0.0001 BTC (price constant)
  n = 2 (quadratic - Bitclout model)
```

This creates **early investor advantage**: Supply 10x → Price 100x.

### Round Structure

| Round | BTC Range | Target Raise | I_i Price Range | Investor Profile |
|-------|-----------|--------------|-----------------|------------------|
| **Pre-Seed** | 0.1 - 1 BTC | 5 BTC | 0.0001 - 0.01 BTC | Founders, Friends |
| **Seed** | 1 - 10 BTC | 50 BTC | 0.01 - 1.0 BTC | Angels, Early Believers |
| **Series A** | 10 - 50 BTC | 200 BTC | 1.0 - 25 BTC | VCs, Institutions |
| **Series B** | 50 - 100 BTC | 500 BTC | 25 - 100 BTC | Growth Funds |
| **TOTAL** | | **755 BTC** (~$75.5M @ $100K BTC) | | |

### Example Investment Scenarios

```
PRE-SEED (0.5 BTC):
  Entry supply: 0
  Tokens received: 22.4 I_i
  Entry price: 0.0001 BTC/I_i
  Pool share: ~15% of investor pool

SEED (10 BTC):
  Entry supply: ~50 I_i
  Tokens received: 66.9 I_i
  Entry price: 0.025 BTC/I_i
  Pool share: ~46% of investor pool

SERIES A (50 BTC):
  Entry supply: ~150 I_i
  Tokens received: 47.2 I_i
  Entry price: 2.25 BTC/I_i
  Pool share: ~20% of investor pool
```

---

## BTC Escrow & Sequester Model

### The "Dry Wallet" Architecture

Investor BTC is **escrowed**, not spent. It becomes permanent network collateral.

```
INVESTMENT FLOW:
Investor BTC → Dry Wallet (Escrow)
                    ↓
              Sequestered for 3 years
                    ↓
              [CHOICE POINT at Year 3]
                    ↓
    ┌───────────────┼───────────────┐
    ↓               ↓               ↓
 BUYOUT         PARTIAL          HOLD
 (10x)          (50/50)        (100x+)
    ↓               ↓               ↓
 BTC returns    Half returns    BTC stays
 to investor    to investor     in system
    ↓               ↓               ↓
 Investor       Investor        ALL BTC
 exits          de-risks        becomes
                                reserve
```

### Escrow Release Schedule

The escrow is **time-locked** with milestone releases:

| Year | Network Milestone | BTC Release to Reserve | Cumulative |
|------|-------------------|------------------------|------------|
| 0 | Investment closes | 0% (fully escrowed) | 0% |
| 1 | 25 FoundUps active | 20% to reserve | 20% |
| 2 | 50 FoundUps active | 20% to reserve | 40% |
| 3 | **CHOICE POINT** | See below | Variable |
| 4+ | Continued growth | Remaining to reserve | 100% |

### Year 3 Choice Point

At Year 3, investors choose:

**Option A: BUYOUT (10x)**
- Network buys back I_i at 10x entry price
- BTC from escrow funds the buyout
- Investor exits with guaranteed return

**Option B: HOLD (100x+)**
- Investor declines buyout
- Their proportional escrow BTC moves to reserve permanently
- Continue earning pool shares (12.16% pre-hurdle, 0.64% post-hurdle)

**Option C: PARTIAL (50/50)**
- Sell 50% of I_i for 5x return
- Hold 50% for long-term upside
- Half of escrow funds buyout, half to reserve

### Buyout Funding Mechanism

```python
# Year 3 Buyout Funding Sources
buyout_sources = {
    "escrow_release": "40% of investor BTC (Years 1-2 releases)",
    "accumulated_fees": "3 years of network fees (subscriptions, trading, etc.)",
    "new_investor_round": "Series B raises at higher valuation",
    "reserve_appreciation": "BTC price growth over 3 years",
}

# Example: 100 BTC seed round needs 1000 BTC for 10x buyout
funding_available = {
    "escrow (40%)": 40,           # 40 BTC
    "fees (3 years)": 150,        # ~50 BTC/year
    "series_b": 300,              # New investment
    "btc_appreciation": 200,      # If BTC 2x in 3 years
    "TOTAL": 690,                 # BTC available
}

# Not all investors will exercise (many will hold for upside)
# Typical exercise rate: 30-50% → Actual need: 300-500 BTC
# STATUS: FULLY FUNDABLE
```

---

## Stakeholder Pool Participation

### Dynamic Network Share (12.16% -> 0.64%)

Investors participate in the **Stakeholder Pools** at DAO activity level:

```
TOKEN POOL MATRIX (WSP 26 Section 6.3-6.4):

                 Un(60%)  Dao(16%)  Du(4%)  Total
-----------------------------------------------
dao level:       9.60%    2.56%     0.64%   12.80%

INVESTOR POOL RECEIVES (pre-hurdle):
- Un Pool:  9.60% of EVERY FoundUp's distributions
- Dao Pool: 2.56% of EVERY FoundUp's distributions
- TOTAL:    12.16% of ALL FoundUp token flows

After repayment target is met, investor pool rate compresses to 0.64%.
```

### F_i Accumulation Projections

```
BASE CASE: 100 FoundUps, 720M F_i/year distributed

Investor Pool Annual Earnings:
  Un Pool (9.60%):   69,120,000 F_i
  Dao Pool (2.56%):  18,432,000 F_i
  TOTAL:             87,552,000 F_i/year

5-Year Accumulation:
  Total to pool:     437,760,000 F_i
  Seed investor (46% of pool): 203,190,193 F_i
```

---

## Return Projections

### By Investment Round

| Round | BTC In | Pool % | 5Y F_i | Curve (10x supply) | Total | Return |
|-------|--------|--------|--------|-------------------|-------|--------|
| Pre-Seed | 0.5 | 15% | 65M | 3,000 BTC | 3,007 BTC | **6,000x** |
| Seed | 10 | 46% | 203M | 14,000 BTC | 16,000 BTC | **1,600x** |
| Series A | 50 | 20% | 88M | 5,000 BTC | 5,900 BTC | **118x** |
| Series B | 100 | 10% | 44M | 2,000 BTC | 2,440 BTC | **24x** |

### By Network Growth Scenario

**Seed Investor (10 BTC)**:

| Scenario | FoundUps | 5Y F_i | Total BTC | Return |
|----------|----------|--------|-----------|--------|
| Conservative | 50 | 70M | 4,200 | **420x** |
| Base Case | 100 | 203M | 16,000 | **1,600x** |
| Bull Case | 250 | 700M | 63,000 | **6,300x** |
| Moon Shot | 500 | 2.1B | 370,000 | **37,000x** |

---

## Exit Strategy: The Hybrid Model

### The Investor Pitch

> "Invest in FoundUps seed round. At Year 3, you have a CHOICE:
>
> **A) TAKE 10x GUARANTEED**: We buy back your I_i for 10x your entry price.
> Your BTC comes from escrow. Risk eliminated.
>
> **B) HOLD FOR 100x+**: Keep your I_i and continue earning pool shares
> (12.16% pre-hurdle, 0.64% post-hurdle). Ride the AI adoption S-curve.
>
> **C) SPLIT 50/50**: De-risk with a 5x partial exit while keeping upside.
>
> The floor is 10x. The ceiling is 1000x. You choose."

### Why This Works

1. **Removes Fear**: Guaranteed 10x floor eliminates downside worry
2. **Preserves FOMO**: Upside option keeps investors dreaming big
3. **Provides Flexibility**: Partial exit satisfies liquidity needs
4. **Aligns Incentives**: Investors stay engaged with network success
5. **Credibly Fundable**: Escrow + fees + new rounds cover buyouts

---

## Legal Structure

### Investment Instrument

I_i tokens are structured as:
- **Utility tokens** with governance rights
- **Non-transferable** during vesting period (S-curve release)
- **Convertible** to pool shares upon vesting
- **Buyback rights** at Year 3 choice point

### Escrow Terms

```
ESCROW AGREEMENT:
1. Investor deposits BTC to multi-sig Dry Wallet
2. BTC is sequestered for minimum 3 years
3. Milestone releases (20% at Year 1, 20% at Year 2)
4. Year 3 choice point determines final disposition
5. Non-exercised buyout rights = BTC to reserve permanently
```

### Regulatory Considerations

- Investment via BTC (not fiat) simplifies compliance
- Utility token structure (not security)
- Buyout funded by protocol, not third parties
- No equity issued (BitClout/DeSo model)

---

## Comparison: FoundUps vs BitClout/DeSo

| Factor | BitClout/DeSo | FoundUps |
|--------|---------------|----------|
| Total Raised | $200M | Target: $75M (755 BTC) |
| Investors | a16z, Sequoia, Coinbase | TBD |
| Bonding Curve | Quadratic (P = 0.003 × S²) | Quadratic (P = k × S²) |
| Token Utility | Creator coins | Pool shares (12.16% pre-hurdle, 0.64% post-hurdle) |
| Exit Mechanism | Secondary trading | **Guaranteed 10x buyout** |
| BTC Backing | No (pure speculation) | **Yes (Hotel California)** |
| Vesting | None (immediate dump risk) | **S-curve (anti-dump)** |
| Network Effect | Single platform | **100+ FoundUps** |

### Key Advantages Over BitClout

1. **Guaranteed Exit**: 10x buyout option (BitClout had none)
2. **Real Asset Backing**: BTC in reserve forever
3. **Network Diversification**: Pool shares across ALL FoundUps
4. **Anti-Dump Vesting**: S-curve prevents early exits
5. **Sustainable Model**: Escrow funds buyouts

---

## Implementation Checklist

### Smart Contracts Required

- [ ] `InvestorEscrow.sol` - BTC escrow with milestone releases
- [ ] `BondingCurve.sol` - I_i token minting/pricing
- [ ] `PoolDistributor.sol` - dynamic share distribution (12.16% -> 0.64%)
- [ ] `BuybackEngine.sol` - Year 3 choice point execution
- [ ] `VestingSchedule.sol` - S-curve token release

### Documentation Updates

- [x] `investor_staking.py` - Python simulation
- [x] `WSP_26` Section 6.9 - Protocol specification
- [x] `TOKENOMICS.md` - Economics overview
- [x] `INVESTOR_ECONOMICS.md` - This document

### Simulator Scenarios

- [x] Bonding curve pricing
- [x] Pool share accumulation
- [x] Network growth scenarios
- [x] Exit strategy analysis
- [ ] Full Monte Carlo simulation

---

## References

- [BitClout/DeSo $200M Funding](https://www.theblock.co/post/118133/bitclout-creator-decentralized-social-blockchain-200-million-funding-a16z-others)
- [DeSo Tokenomics](https://docs.deso.org/deso-tokenomics/no-equity-just-coins-and-code)
- [Bonding Curves Explained](https://yos.io/2018/11/10/bonding-curves/)
- [WSP 26: FoundUPS DAE Tokenization](../../WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md)

---

*"The floor is 10x. The ceiling is 1000x. You choose."*
