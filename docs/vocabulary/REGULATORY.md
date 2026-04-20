# Regulatory Vocabulary

Terminology for compliance and legal framing.

## CRITICAL: We are NOT building CAGR/ROI

**We are building CABR/PoB** - protocol participation, not investment.

## Terminology Migration

| OLD (Investment/Securities) | NEW (Protocol Participation) |
|-----------------------------|------------------------------|
| ROI | Distribution ratio |
| Returns | Allocations |
| Investment | Protocol participation |
| Investor | Staker / Participant |
| Earnings | Distributions |
| Passive income | Epoch distributions |
| Yield | Protocol rewards |
| 10x returns | 10x allocation ratio |
| Capital | Liquidity provision |
| Profit | Protocol output |

## BTC Staker Model (Correct Framing)

```
Staker provides: LIQUIDITY (energy for UPS capacity)
BTC → Reserve → Backs UPS → Protocol runs
Staker receives: F_i distributions (protocol mechanics)

This is NOT investment. This is protocol participation.
Like: Uniswap LP, ETH staking, Curve gauges
```

## Regulatory-Safe Framing

| Principle | Implementation |
|-----------|----------------|
| Describe mechanics, not outcomes | Functions, not promises |
| Algorithmic distribution | `share = f(pool, tier, count)` |
| No promised returns | Market-determined value |
| Transparent rules | Anyone can verify |

## Canonical Staker Model

| Concept | Terminology | Model |
|---------|-------------|-------|
| Du Pool Stakers | CABR/PoB (distribution ratio) | Protocol participation |

**Canonical source**: `modules/foundups/simulator/economics/pool_distribution.py`

**FROZEN/EXPLORATORY**: `investor_staking.py` contains an exploratory I_i bonding curve model that is NOT the canonical staker architecture. Do not implement.

## Governance Model

| Term | Definition |
|------|------------|
| **SmartDAO** | 0102-native governance (NO human voting) |
| **0102 agents** | Run SmartDAO autonomously |
| **Digital Twin** | 012 represented by 0102 agent |

## 0102 Enforcement

When writing docs/code:
1. Use NEW column terminology
2. If about to write OLD term → STOP → substitute NEW term
3. "Distribution ratio" not "ROI"
4. "Protocol participation" not "investment"

---
*Category: Regulatory | HoloIndex indexed*
