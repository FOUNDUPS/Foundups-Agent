# Trade Due-Diligence Post-Tuning Regime Observation — Phase 1

**Slice**: `TRADE_DUE_DILIGENCE_POST_TUNING_REGIME_OBSERVATION_PHASE1`
**Worker**: W9
**Agent**: 0102
**Date**: 2026-05-24
**Mode**: Observation (docs-only, no tuning)
**Branch**: `docs/trade-due-diligence-post-tuning-regime-observation-phase1`
**Base commit**: `9ae77d4b9` (origin/main, post-PR #698)
**WSP Lock**: WSP_00 → WSP_15 → WSP_50 → WSP_64 → WSP_83 → WSP_87 → WSP_97 → WSP_104 → WSP_22

---

## WSP_97 Truth Boundary Checklist

| Truth Boundary Checklist Item | Status |
|-------------------------------|--------|
| TRADE_POST_TUNING_REGIME_OBSERVATION_ONLY | YES |
| DOCS_ONLY | YES |
| OBSERVATION_ONLY | YES |
| NO_ENGINE_MUTATION | YES |
| NO_CONTRACT_MUTATION | YES |
| NO_FIXTURE_MUTATION | YES |
| NO_TEST_MUTATION | YES |
| NO_WEIGHT_CHANGE | YES |
| NO_BAND_CHANGE | YES |
| NO_HARD_DISQUALIFIER_CHANGE | YES |
| NO_SOFT_DISQUALIFIER_CHANGE | YES |
| DETERMINISTIC_BYTE_IDENTICAL_VERIFIED | YES |
| NO_TUNING_IN_THIS_SLICE | YES |
| NO_GENERATED_OBSERVATION_ARTIFACTS_COMMITTED | YES |
| NO_LIVE_FEEDS | YES |
| NO_NETWORK_CALLS | YES |
| NO_WALLET | YES |
| NO_WALLET_SIGNING | YES |
| NO_KEY_MATERIAL | YES |
| NO_ORDER_PLACEMENT | YES |
| NO_REAL_TRADING | YES |
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

**Verdict**: PASS (33/33)

---

## 1. Mission

Run the synthetic regime pack against post-#698 main and produce a canonical
observation record of expected-vs-actual decision bands for all 7 regimes.
Determine whether any further tuning is required.

**NO TUNING in this slice.** If observation surfaces a defect, this audit
names a FUTURE slice — this PR does NOT fix it.

---

## 2. Chain-of-Thought / Chain-of-Action / Chain-of-Evidence (CoT/CoA/CoE)

### 2.1 Chain-of-Thought (Assumptions / Canonical Sources)

| Source | PR | Merge Commit | Content |
|--------|-----|--------------|---------|
| Scoring Engine | #687 | — | Initial due-diligence scoring implementation |
| Deterministic Clock | #691 | — | Explicit `evaluation_time` parameter |
| Synthetic Regime Pack | #693 | `d7331d5b4` | R1–R7 fixtures, decision-shape evidence |
| Decision-Shape Review | #696 | `51750c7af` | Regime classifications, soft disqualifier identification |
| Soft Disqualifier Tuning | #698 | `9ae77d4b9` | R2/R5/R6 soft caps + R3/R7 fixture corrections |

### 2.2 Chain-of-Action

| Step | Action | Mutates Code? |
|------|--------|---------------|
| 1 | Verify PRs #693, #696, #698 merged in main | NO |
| 2 | Run HoloIndex retrieval queries | NO |
| 3 | Run regime test suite (42 tests) | NO |
| 4 | Generate per-regime observation table | NO |
| 5 | Verify determinism (2 re-runs, byte-identical hashes) | NO |
| 6 | Run full Trade test suite (405 tests) | NO |
| 7 | Write audit document | NO |

### 2.3 Chain-of-Evidence

| Evidence | Source | Value |
|----------|--------|-------|
| PRs merged | git log | #693 at d7331d5b4, #696 at 51750c7af, #698 at 9ae77d4b9 |
| Regime tests | pytest | 42 passed, 0 skipped |
| Full Trade tests | pytest | 405 passed, 0 skipped |
| Determinism | 2-run hash comparison | 7/7 byte-identical |
| Band matches | Observation table | 7/7 MATCH |

---

## 3. HoloIndex Retrieval Assessment

### 3.1 Queries Executed

| Query | DOCS Hits | Quality |
|-------|-----------|---------|
| `TRADE_DUE_DILIGENCE_SYNTHETIC_REGIME_PACK_PHASE1` | Position #1 | STRONG |
| `TRADE_DUE_DILIGENCE_SOFT_DISQUALIFIER_PHASE1` | Not in top 3 | WEAK |

### 3.2 Assessment

The soft disqualifier audit doc (PR #698) was recently added and may not be
indexed yet. Direct file reads used as fallback per WSP_50 protocol.

---

## 4. Canonical Expected Band Table

Per #696 decision-shape review + #698 soft disqualifier tuning:

| Regime | ID | Expected Band | Source |
|--------|----|---------------|--------|
| R1 | organic_launch_clean_socials | CANDIDATE_FOR_FUTURE_REVIEW | Original fixture |
| R2 | influencer_pump_high_concentration | SIMULATE_ONLY | #698 soft disqualifier |
| R3 | dead_x_no_telegram | SIMULATE_ONLY | #698 Path A fixture |
| R4 | issuer_prior_rug_history | REJECT | Hard disqualifier |
| R5 | whale_accumulation_then_dump | SIMULATE_ONLY | #698 soft disqualifier |
| R6 | telegram_active_low_authenticity | SIMULATE_ONLY | #698 soft disqualifier |
| R7 | bonding_curve_migration_risk | CANDIDATE_FOR_FUTURE_REVIEW | #698 Path A fixture |

---

## 5. Per-Regime Observed Table

### R1: organic_launch_clean_socials

| Component | Score |
|-----------|-------|
| launch_timing | 100.00 |
| issuer_history | 97.50 |
| social_authenticity | 88.00 |
| telegram_quality | 76.00 |
| influencer_risk | 90.00 |
| holder_distribution | 100.00 |
| whale_risk | 90.00 |
| prior_token_history | 100.00 |
| bonding_curve | 92.50 |
| rug_honeypot | 100.00 |
| **total_score** | **94.85** |
| **risk_score** | **5.15** |
| **evidence_confidence** | **0.94** |

| Field | Value |
|-------|-------|
| Expected band | candidate_for_future_review |
| Actual band | candidate_for_future_review |
| **Result** | **MATCH** |
| Hard disqualifiers | None |
| Soft disqualifier triggers | None |
| deterministic_hash | `17e69c130f71a852...` |

---

### R2: influencer_pump_high_concentration

| Component | Score |
|-----------|-------|
| launch_timing | 88.00 |
| issuer_history | 85.00 |
| social_authenticity | 18.00 |
| telegram_quality | 19.00 |
| influencer_risk | 10.00 |
| holder_distribution | 40.00 |
| whale_risk | 13.00 |
| prior_token_history | 100.00 |
| bonding_curve | 82.50 |
| rug_honeypot | 50.00 |
| **total_score** | **51.73** |
| **risk_score** | **48.27** |
| **evidence_confidence** | **0.82** |

| Field | Value |
|-------|-------|
| Expected band | simulate_only |
| Actual band | simulate_only |
| **Result** | **MATCH** |
| Hard disqualifiers | None |
| Soft disqualifier triggers | influencer_risk < 20, whale_risk < 20, social < 40 AND tg < 50 |
| deterministic_hash | `13c46c56c036376b...` |

---

### R3: dead_x_no_telegram

| Component | Score |
|-----------|-------|
| launch_timing | 82.00 |
| issuer_history | 75.00 |
| social_authenticity | 5.00 |
| telegram_quality | 20.00 |
| influencer_risk | 85.00 |
| holder_distribution | 50.00 |
| whale_risk | 90.00 |
| prior_token_history | 60.00 |
| bonding_curve | 99.00 |
| rug_honeypot | 100.00 |
| **total_score** | **66.90** |
| **risk_score** | **33.10** |
| **evidence_confidence** | **0.64** |

| Field | Value |
|-------|-------|
| Expected band | simulate_only |
| Actual band | simulate_only |
| **Result** | **MATCH** |
| Hard disqualifiers | None |
| Soft disqualifier triggers | social < 40 AND tg < 50 |
| deterministic_hash | `836524ecef9a9311...` |

---

### R4: issuer_prior_rug_history

| Component | Score |
|-----------|-------|
| launch_timing | 100.00 |
| issuer_history | 0.00 |
| social_authenticity | 65.00 |
| telegram_quality | 64.50 |
| influencer_risk | 75.00 |
| holder_distribution | 50.00 |
| whale_risk | 90.00 |
| prior_token_history | 28.00 |
| bonding_curve | 95.00 |
| rug_honeypot | 10.00 |
| **total_score** | **52.27** |
| **risk_score** | **47.73** |
| **evidence_confidence** | **0.79** |

| Field | Value |
|-------|-------|
| Expected band | reject |
| Actual band | reject |
| **Result** | **MATCH** |
| Hard disqualifiers | issuer_history_below_20, rug_honeypot_below_20 |
| Soft disqualifier triggers | None |
| deterministic_hash | `39af85138f214979...` |

---

### R5: whale_accumulation_then_dump

| Component | Score |
|-----------|-------|
| launch_timing | 96.40 |
| issuer_history | 85.00 |
| social_authenticity | 62.00 |
| telegram_quality | 66.60 |
| influencer_risk | 85.00 |
| holder_distribution | 55.00 |
| whale_risk | 14.50 |
| prior_token_history | 75.00 |
| bonding_curve | 90.00 |
| rug_honeypot | 100.00 |
| **total_score** | **72.12** |
| **risk_score** | **27.88** |
| **evidence_confidence** | **0.71** |

| Field | Value |
|-------|-------|
| Expected band | simulate_only |
| Actual band | simulate_only |
| **Result** | **MATCH** |
| Hard disqualifiers | None |
| Soft disqualifier triggers | whale_risk < 20 |
| deterministic_hash | `07be31618678382d...` |

---

### R6: telegram_active_low_authenticity

| Component | Score |
|-----------|-------|
| launch_timing | 100.00 |
| issuer_history | 90.00 |
| social_authenticity | 35.00 |
| telegram_quality | 45.50 |
| influencer_risk | 70.00 |
| holder_distribution | 100.00 |
| whale_risk | 90.00 |
| prior_token_history | 100.00 |
| bonding_curve | 90.00 |
| rug_honeypot | 100.00 |
| **total_score** | **84.78** |
| **risk_score** | **15.22** |
| **evidence_confidence** | **0.85** |

| Field | Value |
|-------|-------|
| Expected band | simulate_only |
| Actual band | simulate_only |
| **Result** | **MATCH** |
| Hard disqualifiers | None |
| Soft disqualifier triggers | social < 40 AND tg < 50 |
| deterministic_hash | `e6488412ca8fe3be...` |

---

### R7: bonding_curve_migration_risk

| Component | Score |
|-----------|-------|
| launch_timing | 100.00 |
| issuer_history | 92.50 |
| social_authenticity | 78.00 |
| telegram_quality | 73.90 |
| influencer_risk | 82.00 |
| holder_distribution | 100.00 |
| whale_risk | 90.00 |
| prior_token_history | 100.00 |
| bonding_curve | 42.50 |
| rug_honeypot | 100.00 |
| **total_score** | **89.70** |
| **risk_score** | **10.30** |
| **evidence_confidence** | **0.86** |

| Field | Value |
|-------|-------|
| Expected band | candidate_for_future_review |
| Actual band | candidate_for_future_review |
| **Result** | **MATCH** |
| Hard disqualifiers | None |
| Soft disqualifier triggers | None |
| deterministic_hash | `b34d78803c7b44db...` |

---

## 6. Determinism Proof

Two independent scoring runs with identical inputs and `FIXTURE_REFERENCE_TIME`:

| Regime | Run 1 Hash | Run 2 Hash | Byte-Identical |
|--------|------------|------------|----------------|
| R1_organic_launch_clean_socials | 17e69c130f71a852... | 17e69c130f71a852... | YES |
| R2_influencer_pump_high_concentration | 13c46c56c036376b... | 13c46c56c036376b... | YES |
| R3_dead_x_no_telegram | 836524ecef9a9311... | 836524ecef9a9311... | YES |
| R4_issuer_prior_rug_history | 39af85138f214979... | 39af85138f214979... | YES |
| R5_whale_accumulation_then_dump | 07be31618678382d... | 07be31618678382d... | YES |
| R6_telegram_active_low_authenticity | e6488412ca8fe3be... | e6488412ca8fe3be... | YES |
| R7_bonding_curve_migration_risk | b34d78803c7b44db... | b34d78803c7b44db... | YES |

**Result**: 7/7 byte-identical across both runs. Determinism VERIFIED.

---

## 7. Soft Disqualifier Trigger Map

| Regime | influencer_risk < 20 | whale_risk < 20 | social < 40 AND tg < 50 | Band Cap Applied |
|--------|---------------------|-----------------|-------------------------|------------------|
| R1 | NO | NO | NO | NO |
| R2 | YES (10.00) | YES (13.00) | YES (18.00, 19.00) | YES → SIMULATE_ONLY |
| R3 | NO | NO | YES (5.00, 20.00) | YES → SIMULATE_ONLY |
| R4 | NO | NO | NO | NO (hard disqualifier takes precedence) |
| R5 | NO | YES (14.50) | NO | YES → SIMULATE_ONLY |
| R6 | NO | NO | YES (35.00, 45.50) | YES → SIMULATE_ONLY |
| R7 | NO | NO | NO | NO |

---

## 8. Hard Disqualifier Preservation Proof

R4 (issuer_prior_rug_history) triggers two hard disqualifiers:
- `issuer_history_below_20`: issuer_history = 0.00 < 20
- `rug_honeypot_below_20`: rug_honeypot = 10.00 < 20

Both force immediate REJECT regardless of total_score (52.27). Hard disqualifier logic preserved.

---

## 9. Summary

### 9.1 Match/Mismatch Table

| Regime | Expected | Actual | Result |
|--------|----------|--------|--------|
| R1 | CANDIDATE_FOR_FUTURE_REVIEW | CANDIDATE_FOR_FUTURE_REVIEW | MATCH |
| R2 | SIMULATE_ONLY | SIMULATE_ONLY | MATCH |
| R3 | SIMULATE_ONLY | SIMULATE_ONLY | MATCH |
| R4 | REJECT | REJECT | MATCH |
| R5 | SIMULATE_ONLY | SIMULATE_ONLY | MATCH |
| R6 | SIMULATE_ONLY | SIMULATE_ONLY | MATCH |
| R7 | CANDIDATE_FOR_FUTURE_REVIEW | CANDIDATE_FOR_FUTURE_REVIEW | MATCH |

**Result**: 7/7 MATCH. No divergences.

### 9.2 Test Results

| Test Suite | Count | Skipped |
|------------|-------|---------|
| test_due_diligence_regimes.py | 42 passed | 0 |
| Full Trade tests | 405 passed | 0 |

---

## 10. Recommendation

**NO FURTHER TUNING REQUIRED.**

The Trade due-diligence chain is observation-stable at post-#698 main:
- All 7 regimes match their canonical expected bands
- Determinism verified (byte-identical hashes across runs)
- Hard disqualifiers preserved (R4 → REJECT)
- Soft disqualifiers correctly cap R2/R5/R6 at SIMULATE_ONLY
- 405 tests pass with 0 skipped

**Recommended next direction** (architect's choice):

| Option | Slice | Description |
|--------|-------|-------------|
| A | TRADE_DUE_DILIGENCE_REGIME_COVERAGE_EXPANSION_PHASE1 | Add more regimes (broaden coverage) |
| B | TRADE_HARNESS_INTEGRATION_WITH_SCORING_PHASE1 | Wire harness + engine (still simulation-only) |
| C | TRADE_OBSERVATION_STABLE_SNAPSHOT_PHASE1 | Document stable state and pause active Trade work |

---

## 11. Completion Summary

| Item | Value |
|------|-------|
| Branch | `docs/trade-due-diligence-post-tuning-regime-observation-phase1` |
| Base commit | `9ae77d4b9` |
| Files changed | 1 (this audit doc) |
| Worker-Lane | W9 |
| Slice | TRADE_DUE_DILIGENCE_POST_TUNING_REGIME_OBSERVATION_PHASE1 |
| Per-regime MATCH | 7/7 |
| Determinism | VERIFIED (byte-identical) |
| Trade tests | 405 passed, 0 skipped |
| Regime tests | 42 passed, 0 skipped |
| Recommendation | NO TUNING |
| WSP_97 | PASS (33/33) |

---

**Worker**: W9
**Slice**: TRADE_DUE_DILIGENCE_POST_TUNING_REGIME_OBSERVATION_PHASE1
**WSP Lock**: WSP_00 → WSP_15 → WSP_50 → WSP_64 → WSP_83 → WSP_87 → WSP_97 → WSP_104 → WSP_22
