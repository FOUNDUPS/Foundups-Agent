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

### [2026-05-23] - TRADE_DUE_DILIGENCE_SCHEMA_PHASE1 (v0.5.0)

**WSP Protocol References**: WSP 97 (Truth), WSP 104 (Namespace)
**Spec**: TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1 (PR #683)

#### Tests Added

**test_due_diligence_contracts.py** — Due diligence contracts (43 tests):
- TestForbiddenImports: no forbidden network/exchange imports
- TestForbiddenFields: no api_key, secret, signer, wallet_private_key, order_id, endpoint, exchange_client
- TestDecisionBand: all 4 bands defined, no band authorizes real trading
- TestEntityHistoryReport: valid construction, confidence bounds, negative values rejected, serialization
- TestWalletAuditReport: valid construction, holding_percent bounds, risk_contribution bounds
- TestSocialPresenceReport: valid construction, score/evidence bounds
- TestInfluencerRiskReport: valid construction, risk_score bounds
- TestLaunchpadTokenCandidate: valid construction, bonding_curve bounds, defaults
- TestTradeDueDiligenceScore: valid construction, all 10 component bounds, calculate_total_score
- TestDecisionBandDetermination: each band reachable, high rug/issuer risk forces reject, low confidence forces observe
- TestNoRealTradingAuthorization: all 4 bands verified
- TestSerialization: all contracts JSON serializable, deterministic output
- TestMissingEvidenceConfidence: zero/partial confidence impact

#### Spec-to-Contract Mapping

| Spec Section | Contract |
|--------------|----------|
| 5.5 EntityHistoryReport | EntityHistoryReport |
| 6.4 WalletAuditReport | WalletAuditReport |
| 5.2/5.3 X/Telegram | SocialPresenceReport |
| 5.4 Influencer/KOL | InfluencerRiskReport |
| 4.3 LaunchDiscoveryEvent | LaunchpadTokenCandidate |
| 8.1/8.2 Score components | TradeDueDiligenceScore |
| 8.3 Decision bands | DecisionBand enum |

#### Test Verification

```bash
python -m pytest modules/foundups/trade/tests/test_due_diligence_contracts.py -q
# Expected: 43 passed

python -m pytest modules/foundups/trade/tests/ -q
# Expected: 292 passed (249 existing + 43 new)
```

---

### [2026-05-24] - TRADE_DUE_DILIGENCE_SCORING_ENGINE_PHASE1 (v0.6.0)

**WSP Protocol References**: WSP 97 (Truth), WSP 104 (Namespace)
**Spec**: TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1 (PR #683)

#### Tests Added

**test_due_diligence_scoring.py** — Deterministic scoring engine (50 tests):
- TestForbiddenImports: no forbidden network/exchange imports in source
- TestForbiddenFields: no api_key/secret/signer fields
- TestScoreLaunchTiming: fresh vs old launch, bounds checking
- TestScoreIssuerHistory: clean, risky, blacklisted, none cases
- TestScoreSocialAuthenticity: good vs none social reports
- TestScoreTelegramQuality: active vs absent Telegram
- TestScoreInfluencerRisk: low vs high influencer risk
- TestScoreHolderDistribution: distributed vs concentrated holdings
- TestScoreWhaleRisk: no whales vs whale-dominated
- TestScoreBondingCurve: optimal, early, late curve positions
- TestScoreRugHoneypot: clean, risky, blacklisted, scammer cases
- TestEvidenceConfidence: full vs no evidence
- TestScoringEngine: engine creation, scoring, all components populated
- TestDeterminism: same inputs same output, JSON deterministic
- TestDecisionBandDetermination: all 4 bands reachable, hard disqualifiers
- TestNoRealTradingAuthorization: all bands verified

#### Component Scorer Coverage

| Scorer | Test Cases |
|--------|------------|
| score_launch_timing | fresh, old, 30min, bounds |
| score_issuer_history | clean, risky, blacklisted, none |
| score_social_authenticity | good, none |
| score_telegram_quality | good, none |
| score_influencer_risk | low, high |
| score_holder_distribution | distributed, concentrated, none |
| score_whale_risk | no whales, whale-dominated |
| score_bonding_curve | optimal, early, late |
| score_rug_honeypot | clean, risky, blacklisted, scammer |
| calculate_evidence_confidence | full, none |

#### Test Verification

```bash
python -m pytest modules/foundups/trade/tests/test_due_diligence_scoring.py -q
# Expected: 50 passed

python -m pytest modules/foundups/trade/tests/ -q
# Expected: 342 passed (292 existing + 50 new)
```

---

### [2026-05-24] - TRADE_DUE_DILIGENCE_SCORING_ENGINE_DETERMINISTIC_CLOCK_FIX_PHASE1 (v0.6.1)

**WSP Protocol References**: WSP 97 (Truth), WSP 104 (Namespace)
**Spec**: TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1 (PR #683)

#### Tests Added/Modified

**test_due_diligence_scoring.py** — Deterministic clock fix (8 new tests, 50 modified):
- TestTimezoneValidation::test_naive_datetime_raises_valueerror: naive evaluation_time raises ValueError
- TestTimezoneValidation::test_non_utc_timezone_normalizes_to_utc: JST and UTC same instant produces byte-identical output
- TestStaticClockScan::test_no_forbidden_clock_patterns_in_source: zero hits for datetime.now, date.today, time.time, time.monotonic, _utc_now
- TestScoringInvariants::test_component_weights_sum_to_one: weights unchanged (sum to 1.0)
- TestScoringInvariants::test_decision_bands_unchanged: all 4 bands present
- TestScoringInvariants::test_hard_disqualifier_thresholds_unchanged: <20 threshold unchanged
- TestScoringInvariants::test_low_evidence_threshold_unchanged: <0.5 threshold unchanged
- TestDeterminism::test_byte_identical_determinism: explicit byte-identical JSON test

#### Changes to Existing Tests

All 50 existing tests updated to pass explicit `evaluation_time=FIXED_EVAL_TIME` parameter:
- FIXED_EVAL_TIME = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)
- fresh_candidate fixture: timestamp = FIXED_EVAL_TIME - 2 minutes
- old_candidate fixture: timestamp = FIXED_EVAL_TIME - 8 hours

#### Test Verification

```bash
python -m pytest modules/foundups/trade/tests/test_due_diligence_scoring.py -q
# Expected: 58 passed (50 existing + 8 new)

python -m pytest modules/foundups/trade/tests/ -q
# Expected: 350 passed (342 existing + 8 new)
```

---

### [2026-05-24] - TRADE_DUE_DILIGENCE_SYNTHETIC_REGIME_PACK_PHASE1

**Worker**: W6
**Branch**: `feat/trade-due-diligence-synthetic-regime-pack-phase1`
**Scope**: test/fixture only — no engine, no contracts, no `src/` mutation.

#### Cases added (42 new tests)

| Test | Coverage |
|------|----------|
| `test_regime_fixture_has_no_forbidden_imports` | Fixture file does not import any networking / exchange SDK from the slice forbidden list. |
| `test_regime_fixture_has_no_forbidden_fields` | Fixture file does not reference any wallet/order/key field name. |
| `test_regime_test_file_has_no_forbidden_imports` | This test file itself does not import any forbidden module. |
| `test_registry_has_all_seven_mandatory_regimes` | All 7 mandatory regime IDs (R1..R7) are present. |
| `test_registry_regime_ids_are_unique` | No duplicate `regime_id` across the registry. |
| `test_regime_score_is_well_formed[R*]` ×7 | Engine output is structurally valid (10 components in [0,100], aggregates consistent). |
| `test_regime_band_is_valid[R*]` ×7 | `decision_band` is a valid `DecisionBand` enum value. |
| `test_regime_no_band_authorizes_real_trading[R*]` ×7 | `assert_no_real_trading_authorized(band)` passes silently — Phase 0 boundary intact. |
| `test_regime_scoring_is_deterministic[R*]` ×7 | Same regime scored twice in one test → bit-equal components + identical deterministic hash. |
| `test_regime_hard_disqualifiers_consistent_with_band[R*]` ×7 | If any documented hard disqualifier triggers, band must be REJECT or OBSERVE. |
| `test_expected_vs_actual_table_is_complete_for_all_regimes` | Full evidence schema complete for every regime; pack-level determinism across two back-to-back full passes. |
| `test_fixture_file_does_not_touch_engine_internals` | Fixture file does not reference `_WEIGHTS` / `__setattr__` / `_missing_` engine-mutation surfaces. |

#### Constraints honored

- NO modification of `modules/foundups/trade/src/**` (engine, contracts, harness).
- NO modification of existing trade tests.
- NO new external dependencies (stdlib + pytest only).
- NO forbidden imports (requests/urllib/httpx/ccxt/web3/exchange SDKs/etc.).
- NO forbidden fields (`api_key`/`secret`/`wallet_private_key`/`order_id`/etc.).
- NO registry/catalog/projection/manifest/CI/dependency edits.
- NO `@pytest.mark.skip` used anywhere in the new files.
- All fixtures synthetic deterministic Python literals.
- Trade status unchanged (still Phase 0 / not_portfolio / poc_status=idea / entity_type=skeleton_candidate).

#### Test policy (per operator's patched W6 prompt)

Per-regime tests fail on: nondeterministic output, invalid `DecisionBand`, malformed score, missing component, forbidden import/field, boundary violation, real-trading authorization claim.

Per-regime tests do **NOT** fail on `expected_band != actual_band`. Divergence is recorded in the per-regime result row (`band_match=False`) and routed to a future targeted engine-tuning slice via the audit doc.

#### Decision-shape findings (recorded, NOT slice failures)

5 of 7 regimes show `expected_band != actual_band`. Pattern: only hard disqualifiers (`rug_honeypot<20`, `issuer_history<20`, `evidence_confidence<0.5`) reliably move the band below `CANDIDATE_FOR_FUTURE_REVIEW` once other components are reasonable. Full per-regime breakdown in:

`docs/audits/architecture/TRADE_DUE_DILIGENCE_SYNTHETIC_REGIME_PACK_PHASE1.md`

#### Test results

```bash
python -m pytest modules/foundups/trade/tests/test_due_diligence_regimes.py
# 42 passed in 0.16s

python -m pytest modules/foundups/trade/tests/
# 384 passed in 1.91s   (342 existing + 42 new, 0 skipped)
```

#### WSP refs

WSP_00, WSP_15, WSP_50, WSP_64, WSP_83, WSP_87, WSP_97, WSP_104, WSP_22

---

### [2026-05-22] - TRADE_DUE_DILIGENCE_SOFT_DISQUALIFIER_PHASE1 (v0.6.2)

**Worker**: W8 (Repair: W6)
**Branch**: `feat/trade-due-diligence-soft-disqualifier-phase1`
**Scope**: Soft disqualifier tuning for R2, R5, R6 per PR #693 decision-shape review.

#### Soft Disqualifier Rules Implemented

| Regime | Trigger Condition | Cap Band | Reason |
|--------|-------------------|----------|--------|
| R2 | influencer_risk < 20 | SIMULATE_ONLY | Coordinated pump risk |
| R5 | whale_risk < 20 | SIMULATE_ONLY | Whale accumulation dump risk |
| R6 | social_authenticity < 40 AND telegram_quality < 50 | SIMULATE_ONLY | Low-authenticity social signals |

#### NOT TUNED (per PR #693 decision-shape review)

- R3 (dead_x_no_telegram): No soft disqualifier - EXPECTATION_TOO_STRICT (fixture expected_band updated to match engine)
- R7 (bonding_curve_migration_risk): No soft disqualifier - ACCEPTABLE_BEHAVIOR (fixture expected_band updated to match engine)

#### Tests Added (13 new tests)

**test_due_diligence_scoring.py** — Soft disqualifier tests:
| Test | Coverage |
|------|----------|
| `test_whale_risk_soft_disqualifier_caps_at_simulate_only` | whale_risk < 20 caps CANDIDATE at SIMULATE_ONLY |
| `test_influencer_risk_soft_disqualifier_caps_at_simulate_only` | influencer_risk < 20 caps CANDIDATE at SIMULATE_ONLY |
| `test_social_telegram_soft_disqualifier_caps_at_simulate_only` | social+telegram combo caps at SIMULATE_ONLY |
| `test_social_only_does_not_trigger_soft_disqualifier` | social alone does NOT trigger |
| `test_telegram_only_does_not_trigger_soft_disqualifier` | telegram alone does NOT trigger |
| `test_soft_disqualifiers_do_not_affect_simulate_only_band` | Lower bands unchanged |
| `test_soft_disqualifiers_do_not_affect_observe_band` | OBSERVE unchanged |
| `test_soft_disqualifiers_do_not_affect_reject_band` | REJECT unchanged |
| `test_hard_disqualifier_takes_priority_over_soft` | Hard > soft priority |
| `test_all_components_high_allows_candidate` | Clean path to CANDIDATE |
| `test_bonding_curve_low_does_not_trigger_soft_disqualifier` | R7 unchanged proof |
| `test_social_authenticity_very_low_alone_does_not_trigger` | R3 unchanged proof |
| `test_weights_unchanged_for_r3_r7_components` | Weights unchanged proof |

**test_due_diligence_contracts.py** — Updated 2 existing tests:
- `test_score_over_70_is_candidate`: Added component values to clear soft disqualifiers
- `test_partial_confidence_allows_higher_bands`: Added component values to clear soft disqualifiers

#### Constraints honored

- NO weight change (all 10 weights unchanged)
- NO hard disqualifier threshold change (<20 unchanged)
- NO schema/contract mutation (only `determine_decision_band()` logic)
- NO fixture input mutation (only expected-band assertions in 2 existing tests)
- NO R3 tuning
- NO R7 tuning
- NO registry/catalog/manifest/projection/CI/dependency edits
- Deterministic scoring preserved
- Trade status unchanged (not_portfolio / poc_status=idea / entity_type=skeleton_candidate)

#### Test results

```bash
python -m pytest modules/foundups/trade/tests/test_due_diligence_scoring.py
# 71 passed (58 existing + 13 new)

python -m pytest modules/foundups/trade/tests/
# 405 passed (392 existing + 13 new, 0 skipped)
```

#### Repair (2026-05-22 W6)

- Rebased onto origin/main post-#697 (1b7f6f2e3)
- Updated fixture expected_band values for R2, R3, R5, R7 per PR #693 reconciliation
- Updated audit doc citation from #696 (incorrect) to #693 (correct decision-shape review)
- Band-match rate: 7/7 (all MATCH post-repair)
- Path A chosen: R3/R7 expected_band updated to match engine output
- Zero skipped tests in full trade suite

#### WSP refs

WSP_00, WSP_15, WSP_50, WSP_64, WSP_83, WSP_87, WSP_97, WSP_104, WSP_22

---

---

### [2026-05-24] - TRADE_HARNESS_INTEGRATION_WITH_SCORING_PHASE1

**WSP Protocol References**: WSP 97 (Truth), WSP 104 (Namespace), WSP 22 (ModLog)

#### Tests Added

**test_scoring_integration.py** — Harness/scoring integration (26 tests):

- TestDeterminism: baseline hash unchanged (5 tests)
  - test_baseline_hash_unchanged_with_gate_disabled
  - test_baseline_length_unchanged
  - test_synthetic_candidate_is_deterministic
  - test_synthetic_reports_are_deterministic
  - test_gate_results_are_deterministic

- TestGateBehavior: gate passthrough and evaluation (5 tests)
  - test_disabled_gate_is_passthrough
  - test_sell_intent_passes_through
  - test_hold_intent_passes_through
  - test_buy_intent_is_evaluated
  - test_convenience_function_with_none_gate

- TestBandActionMapping: band → action verification (4 tests)
  - test_allowed_bands_set
  - test_blocked_bands_set
  - test_all_bands_covered
  - test_no_overlap

- TestGateResults: result recording and summary (4 tests)
  - test_gate_records_results
  - test_gate_summary_empty
  - test_gate_reset
  - test_result_to_dict

- TestSyntheticCandidate: candidate derivation (3 tests)
  - test_candidate_has_required_fields
  - test_different_seeds_produce_different_candidates
  - test_different_bars_produce_different_candidates

- TestForbiddenImports: static scan (2 tests)
  - test_scoring_integration_has_no_forbidden_imports
  - test_all_src_files_have_no_forbidden_imports

- TestForbiddenFields: static scan (2 tests)
  - test_scoring_integration_has_no_forbidden_fields
  - test_all_src_files_have_no_forbidden_fields

- TestIntegration: end-to-end (1 test)
  - test_gate_can_filter_buys_across_simulation

#### Files Added

- `src/scoring_integration.py` — Integration layer (Option A)
- `tests/test_scoring_integration.py` — 26 tests

#### Key Design Decisions

- **Option A chosen**: Separate `scoring_integration.py` module
  - Rationale: Isolates scoring-gate behavior from core harness, reduces regression risk
- **Default-off**: Gate disabled by default, opt-in via `ScoringGate(enabled=True)`
- **Per-bar hook**: Gate evaluates at each bar before intent execution
- **Synthetic derivation**: Deterministic (bar, seed) → LaunchpadTokenCandidate mapping
- **BUY-only gating**: SELL/HOLD intents pass through ungated

#### Band → Action Mapping

| Band | Action | Intent Outcome |
|------|--------|----------------|
| REJECT | BLOCK | BUY → HOLD |
| OBSERVE | OBSERVE | BUY → HOLD (with audit note) |
| SIMULATE_ONLY | ALLOW | BUY proceeds |
| CANDIDATE_FOR_FUTURE_REVIEW | ALLOW | BUY proceeds |

#### Constraints Honored

- NO scoring engine mutation (due_diligence_scoring.py unchanged)
- NO contracts mutation (contracts.py unchanged)
- NO fixture mutation (due_diligence_regimes.py unchanged)
- NO weight/band/disqualifier change (does not trigger #700 R1-R5)
- Default behavior byte-identical (baseline hash unchanged)
- Forbidden imports: 0 hits
- Forbidden fields: 0 hits
- Trade status unchanged (not_portfolio / poc_status=idea / skeleton_candidate)

#### Test Results

```bash
python -m pytest modules/foundups/trade/tests/test_scoring_integration.py -v
# 26 passed

python -m pytest modules/foundups/trade/tests/ -q
# 431 passed (405 existing + 26 new, 0 skipped)
```

#### WSP refs

WSP_00, WSP_15, WSP_50, WSP_64, WSP_83, WSP_87, WSP_97, WSP_104, WSP_22

---

## Future Entries

Next slice: TRADE_HARNESS_INTEGRATION_REGIME_REPLAY_PHASE1 or TRADE_HARNESS_INTEGRATION_OBSERVATION_SNAPSHOT_PHASE1
