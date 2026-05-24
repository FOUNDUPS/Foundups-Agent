# Trade Harness Integration with Scoring — Phase 1

**Slice**: `TRADE_HARNESS_INTEGRATION_WITH_SCORING_PHASE1`
**Worker**: W6
**Agent**: 0102
**Date**: 2026-05-24
**Mode**: Implementation (integration layer only)
**Branch**: `feat/trade-harness-integration-with-scoring-phase1`
**Base commit**: `d86450997` (origin/main, post-PR #701)
**WSP Lock**: WSP_00 → WSP_15 → WSP_50 → WSP_64 → WSP_83 → WSP_87 → WSP_97 → WSP_104 → WSP_22

---

## WSP_97 Truth Boundary Checklist

| Truth Boundary Checklist Item | Status |
|-------------------------------|--------|
| TRADE_HARNESS_SCORING_INTEGRATION_ONLY | YES |
| SIMULATION_MODE_ONLY | YES |
| DETERMINISTIC_INTEGRATION | YES |
| NO_SCORING_ENGINE_MUTATION | YES |
| NO_CONTRACT_MUTATION | YES |
| NO_FIXTURE_MUTATION | YES |
| NO_REGIME_PACK_MUTATION | YES |
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
| NO_TRADE_STATUS_CHANGE | YES |
| DOES_NOT_TRIGGER_700_R1_THROUGH_R5 | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |
| DEFAULT_BEHAVIOR_BYTE_IDENTICAL | YES |
| SCORING_GATE_OPT_IN_ONLY | YES |
| ROADMAP_ALIGNED | YES |
| DOES_NOT_REOPEN_700_STABLE_SNAPSHOT | YES |
| NO_EXTERNAL_ORDER_SEMANTICS | YES |

**Verdict**: PASS (33/33)

---

## 1. Mission

Wire the simulation harness (PR #679) to consume the deterministic due-diligence
scoring engine (PR #687, clock-fix #691, soft disqualifiers #698). The integration
is **OPT-IN ONLY** — default behavior remains byte-identical to main.

When enabled, the scoring gate filters strategy intents based on decision bands:
- **REJECT**: Synthetic strategy intent is blocked
- **OBSERVE**: Synthetic strategy intent is blocked (observation/audit note only)
- **SIMULATE_ONLY**: Synthetic strategy intent may proceed in simulation
- **CANDIDATE_FOR_FUTURE_REVIEW**: Synthetic strategy intent may proceed in simulation

No band authorizes external order placement, wallet signing, live feeds, real trading,
or public readiness.

---

## 2. Chain-of-Thought / Chain-of-Action / Chain-of-Evidence (CoT/CoA/CoE)

### 2.1 Chain-of-Thought (Assumptions)

- Integration must not trigger #700's re-open criteria R1–R5
- Default behavior must remain byte-identical (baseline hash unchanged)
- Scoring gate is opt-in only via `ScoringGate(enabled=True)`
- Option A (separate module) preferred to isolate integration from core harness
- Trade remains Phase 0 / not_portfolio / poc_status=idea / skeleton_candidate

### 2.2 Chain-of-Action

| Step | Action | Mutates Existing? |
|------|--------|-------------------|
| 1 | Capture baseline hash (seed=42, bars=100) | NO |
| 2 | Create scoring_integration.py (Option A) | NO (new file) |
| 3 | Create test_scoring_integration.py | NO (new file) |
| 4 | Run new tests (26 pass) | NO |
| 5 | Run full Trade suite (431 pass) | NO |
| 6 | Verify baseline hash unchanged | NO |
| 7 | Update TestModLog.md (append-only) | YES (append) |
| 8 | Create audit document | NO (new file) |

### 2.3 Chain-of-Evidence

| Evidence | Source | Value |
|----------|--------|-------|
| Baseline hash | Pre-implementation capture | `c90cd57aedbe9bab094551198d8c07c93fa02edf635653639ebbf3f931b58726` |
| Post-implementation hash | Test verification | Same (byte-identical) |
| New tests | test_scoring_integration.py | 26 passed |
| Full suite | pytest trade/tests | 431 passed (405 + 26) |
| Forbidden imports | Static scan | 0 hits |
| Forbidden fields | Static scan | 0 hits |

---

## 3. HoloIndex Retrieval Assessment

| Query | Quality | Notes |
|-------|---------|-------|
| TRADE_POC_SIMULATION_HARNESS_PHASE1 | WEAK | Doc in top 5 |
| TRADE_DUE_DILIGENCE_SCORING_ENGINE_PHASE1 | STRONG | Doc at #1 |
| TRADE_OBSERVATION_STABLE_SNAPSHOT_PHASE1 | STRONG | Doc at #1 |

---

## 4. Integration Matrix

### 4.1 Hook Point

| Field | Value |
|-------|-------|
| Hook location | Per-bar, before intent execution |
| Trigger | BUY intents only (SELL/HOLD pass through) |
| Gate function | `ScoringGate.apply(bar, intent, state)` |
| Default state | Disabled (passthrough) |

### 4.2 Candidate Derivation

Deterministic transformation: `(bar, seed) → LaunchpadTokenCandidate`

| Bar Field | Candidate Field | Derivation |
|-----------|-----------------|------------|
| bar_index | token_address | SHA-256 hash of `{seed}-{bar_index}` |
| bar_index | bonding_curve_progress | `min(bar_index / 100, 0.95)` |
| close_price * volume | initial_market_cap_usd | Scaled by 1/1000 |
| volume | transaction_count | `max(volume // 100, 1)` |
| evaluation_time - bar_index | timestamp | Token "age" simulation |

### 4.3 Band → Action Mapping

| Decision Band | Gate Action | Intent Outcome | Rationale |
|---------------|-------------|----------------|-----------|
| REJECT | BLOCK | BUY → HOLD | Critical risk, block synthetic intent |
| OBSERVE | OBSERVE | BUY → HOLD | Low evidence, observation only |
| SIMULATE_ONLY | ALLOW | BUY proceeds | Score 50-70, simulate permitted |
| CANDIDATE_FOR_FUTURE_REVIEW | ALLOW | BUY proceeds | Score >70, simulate permitted |

### 4.4 Evaluation Time Source

| Field | Value |
|-------|-------|
| Base time | Fixed: `2026-05-24T12:00:00Z` (deterministic) |
| Per-bar time | `base_time + bar_index minutes` |
| Timezone | UTC (timezone-aware) |

---

## 5. Option Chosen: A (Separate Module)

**Choice**: Option A — Create `scoring_integration.py` as separate module

**Rationale**:
- Isolates scoring-gate behavior from core harness
- Reduces regression risk to existing harness tests
- Cleaner separation of concerns
- Easier to disable/remove if needed
- Core harness remains untouched (no modification)

**Alternative considered**: Option B (extend simulation_harness.py)
- Rejected: Tighter coupling, higher regression risk, harder to maintain

---

## 6. Forbidden Scans

### 6.1 Forbidden Imports

| Module | Hits |
|--------|------|
| requests | 0 |
| urllib | 0 |
| httpx | 0 |
| aiohttp | 0 |
| websocket | 0 |
| websockets | 0 |
| socket | 0 |
| asyncio | 0 |
| ccxt | 0 |
| web3 | 0 |
| alpaca | 0 |
| binance | 0 |
| coinbase | 0 |
| kraken | 0 |
| ib_insync | 0 |
| ftx | 0 |
| bitfinex | 0 |
| polygon | 0 |
| yfinance | 0 |
| eth_account | 0 |
| cryptography | 0 |

**Result**: 0 forbidden imports detected

### 6.2 Forbidden Fields

| Field | Hits |
|-------|------|
| api_key | 0 |
| secret | 0 |
| signer | 0 |
| wallet_private_key | 0 |
| order_id | 0 |
| endpoint | 0 |
| exchange_client | 0 |

**Result**: 0 forbidden fields detected

---

## 7. Determinism Proof

### 7.1 Baseline Hash Verification

| Metric | Expected | Actual |
|--------|----------|--------|
| Hash (seed=42, bars=100) | `c90cd57aed...` | `c90cd57aed...` |
| Length | 3690 bytes | 3690 bytes |
| Match | — | **IDENTICAL** |

### 7.2 Gate Determinism

Two runs with same inputs produce identical:
- Gate results (action, band, score)
- Filtered intents
- Summary statistics

---

## 8. Roadmap Alignment

### 8.1 Current Roadmap State

| Field | Value |
|-------|-------|
| Phase | Phase 0: Internal Seed |
| Status | Incubating |
| Next step | TRADE_FOUNDUP_BITQUERY_ADAPTER_PHASE1 (per roadmap) |

### 8.2 This Slice

This slice wires simulation harness to scoring engine for **simulation-only**
integration. Aligns with Phase 0 scope (simulation infrastructure).

### 8.3 Does NOT Enable

- Live feeds
- Public readiness
- Real trading
- Trade promotion
- Any capability outside Phase 0

---

## 9. #700 Re-Open Criteria Check

| Criterion | Trigger | Status |
|-----------|---------|--------|
| R1: New regime divergence | Future regime expansion shows divergence | NOT TRIGGERED |
| R2: Determinism regression | Scoring engine produces different band | NOT TRIGGERED |
| R3: Soft disqualifier challenge | New evidence challenges thresholds | NOT TRIGGERED |
| R4: Entity type promotion | Registry changes skeleton_candidate | NOT TRIGGERED |
| R5: Real trading authorization | Slice claims real trading | NOT TRIGGERED |

**Result**: This slice does NOT re-open #700's stable snapshot.

---

## 10. Files Changed

| File | Change |
|------|--------|
| `modules/foundups/trade/src/scoring_integration.py` | NEW (350 lines) |
| `modules/foundups/trade/tests/test_scoring_integration.py` | NEW (370 lines) |
| `modules/foundups/trade/tests/TestModLog.md` | APPEND (integration entry) |
| `docs/audits/architecture/TRADE_HARNESS_INTEGRATION_WITH_SCORING_PHASE1.md` | NEW (this file) |

---

## 11. Test Results

| Suite | Count | Skipped |
|-------|-------|---------|
| test_scoring_integration.py | 26 passed | 0 |
| Full Trade tests | 431 passed | 0 |
| Baseline | 405 existing | — |
| New | 26 added | — |

---

## 12. Completion Summary

| Item | Value |
|------|-------|
| Branch | `feat/trade-harness-integration-with-scoring-phase1` |
| Base commit | `d86450997` |
| Files changed | 4 |
| Option chosen | A (separate module) |
| Hook point | Per-bar, BUY intents only |
| Default behavior | Disabled (passthrough, byte-identical) |
| Forbidden imports | 0 hits |
| Forbidden fields | 0 hits |
| Baseline hash | UNCHANGED |
| New tests | 26 |
| Total tests | 431 (405 + 26) |
| #700 criteria | NOT triggered |
| WSP_97 | PASS (33/33) |

---

## 13. Cited Prior PRs

| PR | Merge Commit | Contribution |
|----|--------------|--------------|
| #679 | `7999f54a9` | Simulation harness |
| #687 | `409594844` | Scoring engine |
| #691 | `1bcbcde92` | Deterministic clock fix |
| #698 | `9ae77d4b9` | Soft disqualifier tuning |
| #700 | `10cd0c5e1` | Stable snapshot governance |

---

**Worker**: W6
**Slice**: TRADE_HARNESS_INTEGRATION_WITH_SCORING_PHASE1
**WSP Lock**: WSP_00 → WSP_15 → WSP_50 → WSP_64 → WSP_83 → WSP_87 → WSP_97 → WSP_104 → WSP_22
