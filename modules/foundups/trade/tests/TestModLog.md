# Trade FoundUp - Test ModLog

## Test Change Log

### [2026-05-04] - TRADE_FOUNDUP_INTERNAL_SEED_PHASE1 (v0.1.0)

**WSP Protocol References**: WSP 97 (Truth), WSP 104 (Namespace)

#### Tests Added

**test_manifest_contract.py** — Manifest validation (15 tests):
- TestTradeManifestExists: file exists, valid JSON
- TestTradeManifestFields: foundup_id, routing_prefix, data_namespace, lifecycle_stage, tier, launch_readiness, is_invite_only, entry_url, subscription_tier, cabr_contract
- TestTradeManifestCapabilities: capabilities present, no execution capabilities
- TestTradeManifestAgentRoutes: query-only routes

**test_trade_contracts.py** — Contract serialization (40+ tests):
- TestTruthFields: all defaults False/True, assert_no_execution, to_dict
- TestExecutionGuardPolicy: all 9 blocked operations, unknown passes, to_dict
- TestAdapterSpecs: MarketAdapterSpec, LaunchpadAdapterSpec, live_execution_enabled
- TestEventSchemas: MarketEvent, TokenEvent, WalletEvent, SocialEvent, RiskEvent
- TestSignalSchemas: TradeSignal, ExitSignal simulation defaults
- TestProofSchemas: ProofMetric, SimulationResult no real capital
- TestJsonSerialization: all contracts serialize to valid JSON
- TestDefaultInstances: DEFAULT_TRUTH_FIELDS, DEFAULT_EXECUTION_GUARD

#### Verification

```bash
python -m pytest modules/foundups/trade/tests -q
# Expected: 55+ passed

python -m pytest modules/foundups/tests/test_namespace_guardrail.py -q
# Verifies trade namespace integration
```

---

### [2026-05-04] - TRADE_FOUNDUP_ADAPTER_CONTRACTS_PHASE2 (v0.2.0)

**WSP Protocol References**: WSP 97 (Truth), WSP 11 (Interface)

#### Tests Added

**test_adapter_contracts.py** — Adapter abstraction (35+ tests):
- TestAdapterCapability: market, launchpad, risk capabilities
- TestAdapterHealth: default healthy, failures, rate limited, to_dict
- TestAdapterRateLimit: defaults, is_rate_limited, increase_backoff, reset
- TestAdapterError: error codes, retryable, to_dict
- TestAdapterResult: success/failure, is_simulation default, to_dict
- TestAdapterRegistry: register, lookup, capability search, health, rate limits
- TestSingletonRegistry: get_adapter_registry, reset

**test_event_normalization.py** — Event helpers (50+ tests):
- TestEventIdGeneration: prefix, uniqueness, deterministic
- TestMarketEventHelpers: create_market_event, price_update, volume_spike, liquidity_change
- TestTokenEventHelpers: create_token_event, token_created, migration
- TestWalletEventHelpers: buy, sell, hash_wallet_address
- TestSocialEventHelpers: mention, sentiment_shift
- TestRiskEventHelpers: honeypot_detection, rug_risk
- TestMarketEventValidation: valid, missing required, negative values, warnings
- TestTokenEventValidation: valid, invalid bonding_curve
- TestWalletEventValidation: valid, negative amount, raw address warning
- TestSocialEventValidation: valid, invalid sentiment
- TestRiskEventValidation: valid, invalid scores, consistency warnings
- TestGenericValidation: validate_event for all types

**test_execution_guards.py** — Simulation guards (30+ tests):
- TestGuardExceptions: all custom exception types
- TestAssertNoMoneyMode: default passes, false raises
- TestAssertNoWalletSigning: default passes, false raises
- TestAssertNoOrderPlacement: default passes, false raises
- TestAssertNoRealTrades, TestAssertNoCapitalDeployment, TestAssertNoPrivateKeyAccess
- TestValidateExecutionGuardPolicy: all violations, ethical blocks
- TestValidateTruthFields: all truth field violations
- TestSimulationGuard: context manager, assertions, blocked operations
- TestPhase0GuardIntegration: full workflow

#### Verification

```bash
python -m pytest modules/foundups/trade/tests -q
# Expected: 170+ passed
```

---

### [2026-05-23] - TRADE_POC_SIMULATION_HARNESS_PHASE1 (v0.3.0)

**WSP Protocol References**: WSP 97 (Truth), WSP 104 (Namespace)

#### Tests Added

**test_simulation_harness.py** — Deterministic PoC simulation (35+ tests):
- TestForbiddenImports: no forbidden network/exchange imports in source
- TestDeterminism: same seed identical JSON, no wall-clock timestamps, no UUIDs
- TestSyntheticBar: serialization, OHLC bounds
- TestSimulationState: equity calculation, unrealized PnL
- TestTradeLedger: fill accumulation, realized PnL
- TestSimpleSMAStrategy: hold behavior, buy signals
- TestSimulationHarness: run returns summary, seed 42 no violations, truth boundary
- TestInvariants: cash non-negative, no NaN/Infinity, ledger reconciliation, equity reconciliation
- TestCLI: --simulate exits 0, JSON parseable, deterministic rerun, error handling
- TestNoNetworkNoOrderPlacement: SimulationGuard active, truth boundary enforced

#### CLI Verification

```bash
python -m modules.foundups.trade --simulate --seed 42 --json
# Expected: exit 0, invariant_violations=0

python -m modules.foundups.trade --simulate --seed 42 --json > /tmp/run1.json
python -m modules.foundups.trade --simulate --seed 42 --json > /tmp/run2.json
diff /tmp/run1.json /tmp/run2.json
# Expected: no diff (byte-identical)
```

#### Test Verification

```bash
python -m pytest modules/foundups/trade/tests/test_simulation_harness.py -q
# Expected: 35+ passed
```

---

### [2026-05-23] - TRADE_ADAPTER_INTEGRATION_PHASE1 (v0.4.0)

**WSP Protocol References**: WSP 97 (Truth), WSP 104 (Namespace)

#### Tests Added

**test_simulation_data_adapter.py** — Simulation-only data adapter (21 tests):
- TestForbiddenImports: no forbidden network/exchange imports in source AST
- TestForbiddenFields: no forbidden fields (api_key, wallet, etc.) with allowed exceptions (network_capable, live_capable, wallet_capable when hardcoded False)
- TestSimulatedDataAdapter: default/custom initialization, iter_bars count, get_bars, bar type, sequential indices
- TestDeterministicEquivalence: adapter bars match harness bars exactly, determinism across 5 seeds, same seed produces identical bars
- TestDescribe: returns dict, contains required fields, capability flags all False, source reflects fixture_path
- TestReset: reset regenerates same bars
- TestFactoryFunctions: create_simulated_adapter, create_default_adapter
- TestProtocolCompliance: DataAdapterProtocol methods present

#### Determinism Proof

```bash
# Baseline SHA256 (before adapter):
python -m modules.foundups.trade --simulate --seed 42 --json | sha256sum
# d800eb45bd1bb49048ff1b9cabcc4da237f21b735ba4cb571e9e40c682527a89

# After adapter integration:
python -m modules.foundups.trade --simulate --seed 42 --json | sha256sum
# d800eb45bd1bb49048ff1b9cabcc4da237f21b735ba4cb571e9e40c682527a89

# Result: byte-identical (adapter adds capability without changing simulation output)
```

#### Test Verification

```bash
python -m pytest modules/foundups/trade/tests/test_simulation_data_adapter.py -q
# Expected: 21 passed

python -m pytest modules/foundups/trade/tests/ -q
# Expected: 249 passed (228 existing + 21 new)
```

---

## Future Entries

Next slice: `TRADE_ADAPTER_FIXTURE_LOADER_PHASE1` (optional)
