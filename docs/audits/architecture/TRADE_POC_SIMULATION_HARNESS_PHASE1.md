# Trade PoC Simulation Harness — Phase 1

**Slice**: `TRADE_POC_SIMULATION_HARNESS_PHASE1`
**Worker**: W6
**Date**: 2026-05-23
**Mode**: Implementation (PoC harness + tests)
**Base commit**: PR #678 merged
**Branch**: `feat/trade-poc-simulation-harness-phase1`
**WSP Lock**: WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22

---

## WSP_97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| TRADE_POC_SIMULATION_HARNESS_ONLY | YES |
| SYNTHETIC_DATA_ONLY | YES |
| DETERMINISTIC_EVIDENCE_ONLY | YES |
| NO_REAL_TRADING | YES |
| NO_WALLET_SIGNING | YES |
| NO_KEY_MATERIAL | YES |
| NO_ORDER_PLACEMENT | YES |
| NO_NETWORK_CALL | YES |
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

## 1. Goal

Produce a fully simulated, deterministic PoC harness for the Trade FoundUp module that generates measurable engineering evidence for a future review.

**This slice does NOT prove**:
- Market edge
- Production readiness
- Real trading readiness
- Portfolio eligibility
- Public-surface readiness
- CABR/payout/DAO readiness

**This slice DOES prove**:
- Deterministic synthetic market simulation works
- Simulated book/ledger invariants hold
- No real trading surfaces are imported or called
- Output is reproducible and audit-ready

---

## 2. Current Trade Phase 0 Truth Boundary

Per `modules/foundups/trade/README.md`:

| Field | Value |
|-------|-------|
| `no_money_mode` | `True` |
| `dry_run_mode` | `True` |
| `real_execution_performed` | `False` |
| `verification_complete` | `False` |
| `cabr_ready` | `False` |
| `payout_ready` | `False` |

**Unsupported operations**: No real trades, no wallet signing, no private keys, no order placement.

---

## 3. Harness Architecture

```
SimulationHarness
├── _generate_synthetic_bars()    # Deterministic OHLCV from seed
├── run()                         # Execute strategy + track state
├── to_json()                     # Canonical deterministic output
└── _check_invariants()           # Per-bar + final invariant checks

SimpleSMAStrategy (Reference)
├── receive_bar(bar, state)       # Process bar, return intent
└── Intent: BUY(qty) | SELL(qty) | HOLD

SimulationState
├── cash, position, mark_price
├── equity (computed)
└── unrealized_pnl (computed)

TradeLedger
└── fills: List[SimulatedFill]    # All simulated trades
```

---

## 4. Synthetic Data Model

```python
SyntheticBar:
    bar_index: int
    open_price, high_price, low_price, close_price: float
    volume: int

# Generation: deterministic Gaussian walk from seed
# price[i+1] = price[i] * (1 + gauss(0, 0.02))
# Volume: gauss(10000, 2000), clamped to >= 100
```

**No live exchange data. No real prices. No network calls.**

---

## 5. Strategy Contract

```python
class ReferenceStrategy(Protocol):
    def receive_bar(self, bar: SyntheticBar, state: SimulationState) -> StrategyIntent:
        ...

class StrategyIntent:
    intent_type: IntentType  # HOLD | BUY | SELL
    quantity: int
```

- Strategy receives synthetic bars and returns intent objects
- Harness applies intents to in-process simulated book
- Strategy does NOT call adapters, network, exchange SDKs, wallet code, or filesystem

---

## 6. Invariants

| Invariant | Description |
|-----------|-------------|
| `cash_non_negative` | Cash >= 0 (long-only strategy) |
| `position_non_negative` | Position >= 0 (no shorts) |
| `no_nan_infinity` | No NaN/Infinity in equity or cash |
| `equity_reconciliation` | final_equity == cash + position * mark_price |
| `ledger_reconciliation` | position == sum(buys) - sum(sells) |
| `min_order_size` | No order below MIN_ORDER_SIZE (1) |

---

## 7. Determinism Guarantee

- Same seed + same bars = byte-identical JSON output
- No wall-clock timestamps in output
- No hostnames, absolute paths, or environment-derived values
- No random UUIDs (fill_id derived from seed + bar_index)
- run_id = `run-{seed}-{bars}`

**Proof**: Two CLI runs with `--seed 42 --json` produce identical output.

---

## 8. Sample seed=42 Output

```
Trade PoC Simulation Complete
  run_id: run-42-100
  seed: 42
  bars: 100
  initial_capital: 10000.00
  final_equity: 9203.68
  total_trades: 16
  gross_pnl: -796.32
  max_drawdown: 0.1785
  sharpe_like_ratio: -0.0542
  invariant_violations: 0
```

**Note**: Negative PnL is expected — the reference SMA strategy is not optimized. This proves the harness tracks losses correctly, not that the strategy has market edge.

---

## 9. Forbidden Imports Verification

**Test**: `TestForbiddenImports.test_no_forbidden_imports_in_source`

**Forbidden modules** (none found in `simulation_harness.py`):
- requests, urllib, httpx, aiohttp
- websocket, websockets
- ccxt, web3
- socket
- alpaca, binance, coinbase, kraken, ib_insync

**Result**: PASS

---

## 10. What This Does NOT Prove

| Claim | Status |
|-------|--------|
| Market edge | NOT CLAIMED |
| Production readiness | NOT CLAIMED |
| Real trading readiness | NOT CLAIMED |
| Portfolio eligibility | NOT CLAIMED |
| Public-surface readiness | NOT CLAIMED |
| CABR/payout/DAO readiness | NOT CLAIMED |
| Positive expectancy | NOT CLAIMED |

---

## 11. Future Evidence Review Criteria

Define criteria around safety and reproducibility, not profitability claims:

| Criterion | Threshold |
|-----------|-----------|
| Multiple seeds complete with invariant_violations=0 | 5+ seeds |
| Multiple synthetic regimes complete deterministically | Yes |
| No forbidden imports or network behavior | Zero violations |
| Outputs are stable and reviewable | Byte-identical reruns |
| Strategy behavior is explainable from ledger/state transitions | Yes |

---

## 12. HoloIndex Assessment

| Query | Top Results |
|-------|-------------|
| `trade module simulation harness guards contracts adapters` | guards.py, test_execution_guards.py, contracts.py, INTERFACE.md |
| `Trade FoundUp no real trading dry run simulation WSP 97` | guards.py, README.md, contracts.py |

**Assessment**: HoloIndex correctly surfaces Trade module files. Simulation harness will be indexed after merge.

---

## 13. Test Results

```
python -m pytest modules/foundups/trade/tests/ -q
228 passed in 2.18s
```

**New tests** (36):
- `TestForbiddenImports`: 2 tests
- `TestDeterminism`: 5 tests
- `TestSyntheticBar`: 2 tests
- `TestSimulationState`: 4 tests
- `TestTradeLedger`: 3 tests
- `TestSimpleSMAStrategy`: 2 tests
- `TestSimulationHarness`: 6 tests
- `TestInvariants`: 4 tests
- `TestCLI`: 5 tests
- `TestNoNetworkNoOrderPlacement`: 3 tests

---

## 14. Deterministic Rerun Proof

```bash
python -m modules.foundups.trade --simulate --seed 42 --json > /tmp/run1.json
python -m modules.foundups.trade --simulate --seed 42 --json > /tmp/run2.json
diff /tmp/run1.json /tmp/run2.json
# Result: no diff (byte-identical)
```

**Result**: PASS

---

## 15. Files Changed

| File | Change |
|------|--------|
| `modules/foundups/trade/src/simulation_harness.py` | NEW (550+ lines) |
| `modules/foundups/trade/__main__.py` | NEW (CLI entry point) |
| `modules/foundups/trade/tests/test_simulation_harness.py` | NEW (36 tests) |
| `modules/foundups/trade/tests/TestModLog.md` | UPDATED |
| `docs/audits/architecture/TRADE_POC_SIMULATION_HARNESS_PHASE1.md` | NEW (this file) |

---

## 16. WSP_97 Verdict

| Check | Result |
|-------|--------|
| Trade PoC simulation harness only | PASS |
| Synthetic data only | PASS |
| Deterministic evidence only | PASS |
| No real trading | PASS |
| No wallet signing | PASS |
| No key material | PASS |
| No order placement | PASS |
| No network call | PASS |
| No exchange SDK import | PASS |
| No registry mutation | PASS |
| No catalog mutation | PASS |
| No manifest mutation | PASS |
| No projection mutation | PASS |
| No portfolio promotion | PASS |
| No public surface claim | PASS |
| No CI gate activation | PASS |
| No dependency install | PASS |
| No CABR ready | PASS |
| No payout ready | PASS |
| No DAO activation | PASS |

**Verdict**: PASS

---

## 17. Internal Subworker Summaries

| Subworker | Role | Result |
|-----------|------|--------|
| DISCOVERY_SUBWORKER | Read existing Trade module | Found contracts.py, guards.py, adapters.py, 5 test files |
| HARNESS_DESIGN_SUBWORKER | Propose deterministic engine shape | SimulationHarness + SimulationState + TradeLedger design |
| TEST_SECURITY_SUBWORKER | Design forbidden imports/network checks | FORBIDDEN_IMPORTS set, AST scanning |
| IMPLEMENTATION_WORKER | Single writer for all files | Created 3 new files, updated TestModLog |
| VERIFICATION_SUBWORKER | Run tests, determinism proof | 228 passed, determinism PASS |

---

## 18. Next Slice (Do Not Start)

| Slice | Purpose |
|-------|---------|
| `TRADE_POC_SIMULATION_EVIDENCE_REVIEW_PHASE1` | Review evidence, decide W10 readiness |

---

*Slice authored under WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22.*
*Slice: TRADE_POC_SIMULATION_HARNESS_PHASE1*
