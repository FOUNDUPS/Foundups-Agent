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

## Future Entries

Next slice: `TRADE_FOUNDUP_BITQUERY_ADAPTER_PHASE1`
