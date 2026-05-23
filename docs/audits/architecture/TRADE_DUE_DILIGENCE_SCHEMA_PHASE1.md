# Trade Due Diligence Schema — Phase 1

**Slice**: `TRADE_DUE_DILIGENCE_SCHEMA_PHASE1`
**Agent**: 0102
**Date**: 2026-05-23
**Mode**: Implementation (contracts only)
**Spec**: TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1 (PR #683)
**Branch**: `feat/trade-due-diligence-schema-phase1`
**WSP Lock**: WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22

---

## WSP_97 Truth Boundary Checklist

| Label | Status |
|-------|--------|
| TRADE_DUE_DILIGENCE_SCHEMA_ONLY | YES |
| CONTRACTS_ONLY | YES |
| PURE_DATA_STRUCTURES_ONLY | YES |
| NO_LIVE_FEEDS | YES |
| NO_EXCHANGE_API_CALLS | YES |
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

---

## 1. Mission

Implement typed schema layer for Trade pump.fun due-diligence scoring model. Pure data contracts only — no network calls, wallet access, or trading execution.

---

## 2. Spec-to-Contract Mapping

| Spec Section | Spec Schema | Implementation |
|--------------|-------------|----------------|
| 5.5 | EntityHistoryReport | `EntityHistoryReport` dataclass |
| 6.4 | WalletAuditReport | `WalletAuditReport` dataclass |
| 5.2/5.3 | X/Telegram analysis | `SocialPresenceReport` dataclass |
| 5.4 | Influencer/KOL detection | `InfluencerRiskReport` dataclass |
| 4.3 | LaunchDiscoveryEvent | `LaunchpadTokenCandidate` dataclass |
| 8.1/8.2 | TradeDueDiligenceScore | `TradeDueDiligenceScore` dataclass |
| 8.3 | Decision bands | `DecisionBand` enum |
| 8.4 | Decision rules | `determine_decision_band()` method |

---

## 3. Contracts Implemented

### 3.1 Enums

| Enum | Values | Purpose |
|------|--------|---------|
| `DecisionBand` | reject, observe, simulate_only, candidate_for_future_review | Due-diligence decision output |
| `RiskClassification` | clean, suspicious, flagged, blacklisted | Entity risk level |
| `EntityType` | issuer, influencer, whale, bot, retail | Entity category |
| `WalletClassification` | retail, whale, insider, bot, scammer, unknown | Wallet entity type |

### 3.2 Data Contracts

| Contract | Fields | Validation |
|----------|--------|------------|
| `EntityHistoryReport` | entity_id, prior_token_launches, prior_rug_pulls, confidence | confidence: 0.0-1.0, no negative counts |
| `WalletAuditReport` | wallet_hash, holding_percent, risk_contribution | holding_percent: 0.0-100.0, risk_contribution: 0.0-1.0 |
| `SocialPresenceReport` | x_account_exists, telegram_exists, social_authenticity_score | score: 0.0-100.0, evidence: 0.0-1.0 |
| `InfluencerRiskReport` | known_pumper_wallets_detected, influencer_risk_score | score: 0.0-100.0 |
| `LaunchpadTokenCandidate` | token_address, bonding_curve_progress, passed_initial_filter | bonding_curve: 0.0-1.0 |
| `TradeDueDiligenceScore` | 10 component scores, total_score, decision_band | all scores: 0.0-100.0 |

### 3.3 TradeDueDiligenceScore Components

| Component | Weight | Range | Meaning |
|-----------|--------|-------|---------|
| `launch_timing` | 0.10 | 0-100 | Fresh launch advantage |
| `issuer_history` | 0.15 | 0-100 | Clean issuer history |
| `social_authenticity` | 0.10 | 0-100 | Real community signals |
| `telegram_quality` | 0.05 | 0-100 | Active, non-bot TG |
| `influencer_risk` | 0.10 | 0-100 | Low pump-and-dump risk |
| `holder_distribution` | 0.15 | 0-100 | Distributed holdings |
| `whale_risk` | 0.10 | 0-100 | Low whale manipulation |
| `prior_token_history` | 0.10 | 0-100 | Issuer track record |
| `bonding_curve` | 0.05 | 0-100 | Healthy curve progression |
| `rug_honeypot` | 0.10 | 0-100 | Low exit risk |

---

## 4. Decision Band Semantics

| Band | Total Score | Risk Score | Action |
|------|-------------|------------|--------|
| `reject` | < 30 | > 70 | Do not proceed |
| `observe` | 30-50 | 50-70 | Monitor only |
| `simulate_only` | 50-70 | 30-50 | Paper trade simulation |
| `candidate_for_future_review` | > 70 | < 30 | Flag for advanced analysis |

**No band authorizes real trading.**

### Hard Disqualifiers

- `rug_honeypot` < 20 → REJECT
- `issuer_history` < 20 → REJECT
- `evidence_confidence` < 0.5 → OBSERVE

---

## 5. Forbidden Import/Field Scan

### 5.1 Forbidden Imports (0 violations)

Scanned `contracts.py` for: requests, urllib, httpx, aiohttp, websocket, ccxt, web3, socket, alpaca, binance, coinbase, kraken, ib_insync, etc.

**Result**: PASS

### 5.2 Forbidden Fields (0 violations)

Scanned for: api_key, secret, signer, wallet_private_key, private_key, order_id, endpoint, exchange_client, api_url, api_secret

**Result**: PASS

---

## 6. HoloIndex Assessment

### Pre-Implementation Queries

| Query | Result |
|-------|--------|
| "TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1" | pumpfun_comparison.py surfaced, spec doc not in top results |
| "Trade pump.fun due diligence scoring issuer wallet social rug pull" | Trade test files surfaced |
| "TradeDueDiligenceScore EntityHistoryReport WalletAuditReport" | contracts.py surfaced (no prior due-diligence contracts) |

### Assessment

HoloIndex correctly identified contracts.py as the target file. PR #684 (alias expansion) improved retrieval for Trade queries.

---

## 7. Test Results

### 7.1 New Tests

```
python -m pytest modules/foundups/trade/tests/test_due_diligence_contracts.py -v
43 passed in 0.27s
```

| Test Class | Tests | Purpose |
|------------|-------|---------|
| TestForbiddenImports | 1 | No network/exchange imports |
| TestForbiddenFields | 1 | No api_key/secret/signer fields |
| TestDecisionBand | 2 | All bands defined, none authorize trading |
| TestEntityHistoryReport | 5 | Construction, bounds, serialization |
| TestWalletAuditReport | 4 | Construction, bounds |
| TestSocialPresenceReport | 3 | Construction, bounds |
| TestInfluencerRiskReport | 2 | Construction, bounds |
| TestLaunchpadTokenCandidate | 3 | Construction, bounds, defaults |
| TestTradeDueDiligenceScore | 6 | Construction, component bounds, weighted scoring |
| TestDecisionBandDetermination | 7 | Each band reachable, hard disqualifiers |
| TestNoRealTradingAuthorization | 4 | All bands verified |
| TestSerialization | 3 | JSON serializable, deterministic |
| TestMissingEvidenceConfidence | 2 | Confidence impact on bands |

### 7.2 Full Test Suite

```
python -m pytest modules/foundups/trade/tests/ -q
292 passed in 1.45s
```

**Breakdown**: 249 existing + 43 new = 292 total

---

## 8. Files Changed

| File | Change |
|------|--------|
| `modules/foundups/trade/src/contracts.py` | Added 6 dataclasses, 4 enums, validation |
| `modules/foundups/trade/tests/test_due_diligence_contracts.py` | NEW (43 tests) |
| `modules/foundups/trade/tests/TestModLog.md` | UPDATED |
| `docs/audits/architecture/TRADE_DUE_DILIGENCE_SCHEMA_PHASE1.md` | NEW (this file) |

---

## 9. WSP_97 Verdict

| Check | Result |
|-------|--------|
| Trade due diligence schema only | PASS |
| Contracts only | PASS |
| Pure data structures only | PASS |
| No live feeds | PASS |
| No exchange API calls | PASS |
| No network calls | PASS |
| No wallet | PASS |
| No wallet signing | PASS |
| No key material | PASS |
| No order placement | PASS |
| No real trading | PASS |
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

## 10. W10 Readiness

This slice implements typed contracts for due-diligence scoring. W10 can review:
- Contract validation logic
- Decision band semantics
- Spec-to-implementation mapping
- No real trading authorization claim

---

## 11. Next Slice (Do Not Start)

| Slice | Purpose |
|-------|---------|
| `TRADE_DUE_DILIGENCE_SCORING_ENGINE_PHASE1` | Implement scoring engine using these contracts |

---

*Slice authored under WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22.*
*Slice: TRADE_DUE_DILIGENCE_SCHEMA_PHASE1*
