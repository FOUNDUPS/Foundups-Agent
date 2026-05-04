# Trade FoundUp

**Autonomous trading intelligence and execution FoundUp.**

**Version**: 0.1.0  
**Status**: Incubating (Phase 0)  
**Type**: F0_DAE  
**Owner**: 012  

---

## One-Line Thesis

Trade is the autonomous FoundUp that turns compute into market intelligence, proves edge in hostile meme-launch markets, then expands into ubiquitous autonomous trading.

---

## Core Principle

**Trade is ubiquitous.**

- Must NOT be chain-specific
- Must NOT be launchpad-specific
- Must NOT be meme-specific
- Must BE market-adapter driven

The meme-coin launchpad PoC is just the fastest hostile environment to test the system.

---

## WSP 97 Truth Boundary

**Phase 0 constraints (NO EXCEPTIONS):**

| Field | Value | Meaning |
|-------|-------|---------|
| `no_money_mode` | `True` | No real capital deployment |
| `dry_run_mode` | `True` | All operations are simulated |
| `real_execution_performed` | `False` | No actual trades executed |
| `verification_complete` | `False` | No CABR verification |
| `cabr_ready` | `False` | No V3 scoring |
| `payout_ready` | `False` | No blockchain payouts |

**Unsupported Operations (Phase 0):**

- No real trades
- No wallet signing
- No private keys
- No order placement
- No wash trading
- No market manipulation
- No bot concealment
- No fake volume
- No autonomous capital deployment

---

## Route Namespace

Canonical contract: `modules/foundups/docs/FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md`  
Routing follows **WSP 104** (`/f/{foundup_id}`).

| Field | Value |
|-------|-------|
| `foundup_id` | `trade` |
| `routing_prefix` | `/f/trade` |
| Landing route | `/f/trade` |
| App mount | `/f/trade/app` |

---

## App Mount

Shell contract: **`/f/trade/app`**

**Current status**: Not deployed. Internal prototype only.

---

## AI Capability Hooks

Contract surface (implementation staged):

| Hook | Status | Intent |
|------|--------|--------|
| `get_status` | Planned | Short operational snapshot |
| `get_context` | Planned | Bounded context for trading decision |
| `navigate` | Planned | Change surface within tenant bounds |
| `launch_capability` | Planned | Invoke intelligence/simulation capability |
| Shell handoff/return | Planned | Delegate to shell or return from tool |

---

## DAEmon Outputs

Per **WSP 91** (when DAEMON workers attach):

| Output | Status | Notes |
|--------|--------|-------|
| Health status | Planned | healthy / degraded / critical |
| Last action | Planned | Last simulation or analysis |
| Error state | Planned | Active error or "none" |
| Recommended next action | Planned | Operator/agent hint |
| Queue / work state | Planned | Simulation queue state |
| Telemetry namespace | Defined | `idb_trade` |

---

## Data / Telemetry Namespace

| Field | Value |
|-------|-------|
| `foundup_id` | `trade` |
| `data_namespace` | `idb_trade` |
| Tenant bounds | Cache, storage, telemetry stay tenant-scoped per WSP 104 |

---

## Architecture

Trade is adapter-driven:

```
Trade/
├── market_adapters/       # Chain/exchange abstraction (solana, ethereum, cex, etc.)
├── launchpad_adapters/    # Launch platform abstraction (pumpfun, sunpump, zora, etc.)
├── intelligence/          # Risk engine, honeypot detector, entity graph, game theory
├── orchestration/         # WRE task adapter, model router, swarm dispatcher
├── simulation/            # Paper trade, backtest, shadow execution, proof metrics
├── execution/             # No-money mode, micro-wallet mode (future), execution guard
└── audit/                 # Decision log, violations, proof of performance
```

---

## Universal Event Schema

All market data normalized to universal schemas:

| Schema | Purpose |
|--------|---------|
| `MarketEvent` | Price, volume, liquidity changes |
| `TokenEvent` | Token creation, migration, metadata |
| `WalletEvent` | Wallet transactions and holdings |
| `SocialEvent` | Social signals, sentiment, manipulation |
| `RiskEvent` | Risk scores, honeypot detection |
| `TradeSignal` | Entry signals (simulation only) |
| `ExitSignal` | Exit signals (simulation only) |
| `ProofMetric` | Performance measurement |
| `SimulationResult` | Paper trading outcomes |

---

## PoC Market: Meme Launchpads

First proving ground: meme-coin launch markets (high-signal, high-risk, adversarial).

**Target launchpad adapters (priority order):**

| Platform | Chain | Data Source | Status |
|----------|-------|-------------|--------|
| Pump.fun | Solana | Bitquery API | Planned |
| PumpSwap | Solana | Bitquery API | Planned |
| Raydium LaunchLab | Solana | Direct RPC | Planned |
| Moonshot | Solana | TBD | Planned |
| LetsBONK | Solana | TBD | Planned |
| Four.Meme | BNB Chain | TBD | Planned |
| SunPump | Tron | TBD | Planned |
| Zora | Base/Ethereum | TBD | Planned |
| Snek.fun | Cardano | TBD | Planned |

**Data sources (verified):**
- Bitquery: Token launches, live trades, OHLCV, bonding curves, top traders, holder distribution, migration tracking ([docs](https://docs.bitquery.io/docs/blockchain/Solana/Pumpfun/Pump-Fun-API/))

---

## Proof Metrics (Phase 0)

Track without real capital:

| Metric | Category |
|--------|----------|
| Detection latency | Latency |
| Adapter latency | Latency |
| Honeypot detection accuracy | Accuracy |
| No-exit detection accuracy | Accuracy |
| Soft-rug prediction accuracy | Accuracy |
| False positives | Accuracy |
| False negatives | Accuracy |
| Simulated expectancy | Performance |
| Simulated max drawdown | Performance |
| Model latency | Latency |
| Valid JSON rate | Reliability |
| Model cost | Cost |
| Rate-limit reliability | Reliability |
| Cross-market generalization | Performance |

---

## WRE Integration Plan

Future integration with WRE orchestration:

1. **FoundUpJob**: Jobs with `foundup_id="trade"` route to Trade adapters
2. **FAM Events**: Trade emits `fam_emit` events for proof tracking
3. **pAVS Registration**: Trade registers as pAVS-verifiable FoundUp
4. **Hermes Delegation**: WRE can delegate simulation tasks to Trade workers

---

## WSP References

- **WSP 97** — Truthful Agent Contract (truth boundaries)
- **WSP 91** — DAEMON Observability Protocol
- **WSP 103** — FoundUp Federation Protocol
- **WSP 104** — FoundUp Route Namespace and Tenant Isolation Protocol
- **WSP 29** — CABR Engine (V1/V2/V3 validation)

---

## Lifecycle Phases

| Phase | Description | Capital |
|-------|-------------|---------|
| **Phase 0** (current) | Internal seed, contracts, simulation | None |
| Phase 1 | Adapter layer, multi-launchpad | None |
| Phase 2 | Universal market schema normalization | None |
| Phase 3 | Simulation + proof metrics | None |
| Phase 4 | WRE swarm integration | None |
| Phase 5 | Prototype hardening | None |
| Phase 6 | External FoundUp generation | None |
| Phase 7 | Community compute registry | None |
| Phase 8 | Bounded micro-wallet execution | Micro |
| Phase 9 | Universal trading expansion | Scaled |

---

## Files

| File | Purpose |
|------|---------|
| `foundup_manifest.json` | FoundUp identity and shell contract |
| `module.json` | Module metadata |
| `src/contracts.py` | Typed contracts and event schemas |
| `tests/test_manifest_contract.py` | Manifest validation tests |
| `tests/test_trade_contracts.py` | Contract serialization tests |

---

*Trade is the autonomous FoundUp that turns compute into market intelligence.*
