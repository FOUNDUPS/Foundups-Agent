# Trade Due Diligence Scoring Engine — Phase 1

**Slice**: `TRADE_DUE_DILIGENCE_SCORING_ENGINE_PHASE1`
**Agent**: 0102
**Date**: 2026-05-24
**Mode**: Implementation (scoring engine)
**Spec**: TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1 (PR #683)
**Branch**: `feat/trade-due-diligence-scoring-engine-phase1`
**WSP Lock**: WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22

---

## WSP_97 Truth Boundary Checklist

| Label | Status |
|-------|--------|
| TRADE_DUE_DILIGENCE_SCORING_ENGINE_ONLY | YES |
| PURE_COMPUTATION_ONLY | YES |
| DETERMINISTIC_SCORING | YES |
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

Implement deterministic scoring engine for Trade pump.fun due-diligence model. Consumes input reports from previous schema slice, produces `TradeDueDiligenceScore` with all 10 components filled. Pure computation — no network calls, wallet access, or trading execution.

---

## 2. Input → Output Contract

### Inputs (from TRADE_DUE_DILIGENCE_SCHEMA_PHASE1)

| Contract | Purpose |
|----------|---------|
| `LaunchpadTokenCandidate` | Token metadata, bonding curve, creator |
| `EntityHistoryReport` | Issuer/creator history, rug pulls |
| `WalletAuditReport[]` | Holder distribution, whale detection |
| `SocialPresenceReport` | X/Telegram authenticity signals |
| `InfluencerRiskReport` | Pump coordination risk |

### Output

| Contract | Purpose |
|----------|---------|
| `TradeDueDiligenceScore` | All 10 component scores + decision band |

---

## 3. Component Scorers Implemented

| Scorer | Weight | Logic Summary |
|--------|--------|---------------|
| `score_launch_timing` | 0.10 | Fresh (<5 min) = 100, decays with age |
| `score_issuer_history` | 0.15 | Clean = high, rug pulls penalize, blacklist = 0 |
| `score_social_authenticity` | 0.10 | Passthrough from SocialPresenceReport |
| `score_telegram_quality` | 0.05 | Member count, bot %, spam ratio |
| `score_influencer_risk` | 0.10 | Inverted from influencer_risk_score |
| `score_holder_distribution` | 0.15 | Top holder concentration penalty |
| `score_whale_risk` | 0.10 | Whale holding % + risk contribution |
| `score_prior_token_history` | 0.10 | Success ratio, lifespan, holder loss |
| `score_bonding_curve` | 0.05 | Optimal 10-50%, penalize early/late |
| `score_rug_honeypot` | 0.10 | Rug pulls, blacklist, scammer wallets |

---

## 4. Decision Band Semantics

| Band | Total Score | Trigger |
|------|-------------|---------|
| `REJECT` | < 30 | Critical risk or hard disqualifier |
| `OBSERVE` | 30-50 | Low evidence or moderate scores |
| `SIMULATE_ONLY` | 50-70 | Qualifies for paper trading |
| `CANDIDATE_FOR_FUTURE_REVIEW` | > 70 | Flag for advanced analysis |

### Hard Disqualifiers (force REJECT)

- `rug_honeypot` < 20
- `issuer_history` < 20

### Low Evidence Override (force OBSERVE)

- `evidence_confidence` < 0.5

**No band authorizes real trading.**

---

## 5. Forbidden Import/Field Scan

### 5.1 Forbidden Imports (0 violations)

Scanned `due_diligence_scoring.py` for: requests, urllib, httpx, aiohttp, websocket, ccxt, web3, socket, alpaca, binance, coinbase, kraken, ib_insync, etc.

**Result**: PASS

### 5.2 Forbidden Fields (0 violations)

Scanned for: api_key, secret, signer, wallet_private_key, private_key, order_id, endpoint, exchange_client, api_url, api_secret

**Result**: PASS

---

## 6. Determinism Verification

### Test: Same Inputs → Same Output

```python
result1 = engine.score(candidate, issuer_report=clean_issuer)
result2 = engine.score(candidate, issuer_report=clean_issuer)
assert result1.total_score == result2.total_score
assert result1.decision_band == result2.decision_band
```

**Result**: PASS

### Test: JSON Serialization Deterministic

```python
json1 = json.dumps(result1.to_dict(), sort_keys=True)
json2 = json.dumps(result2.to_dict(), sort_keys=True)
assert json1 == json2
```

**Result**: PASS

---

## 7. Test Results

### 7.1 New Tests

```
python -m pytest modules/foundups/trade/tests/test_due_diligence_scoring.py -v
50 passed in 0.46s
```

| Test Class | Tests | Purpose |
|------------|-------|---------|
| TestForbiddenImports | 1 | No network/exchange imports |
| TestForbiddenFields | 1 | No api_key/secret/signer fields |
| TestScoreLaunchTiming | 4 | Launch timing scorer |
| TestScoreIssuerHistory | 4 | Issuer history scorer |
| TestScoreSocialAuthenticity | 2 | Social authenticity scorer |
| TestScoreTelegramQuality | 2 | Telegram quality scorer |
| TestScoreInfluencerRisk | 2 | Influencer risk scorer |
| TestScoreHolderDistribution | 3 | Holder distribution scorer |
| TestScoreWhaleRisk | 2 | Whale risk scorer |
| TestScoreBondingCurve | 3 | Bonding curve scorer |
| TestScoreRugHoneypot | 4 | Rug/honeypot scorer |
| TestEvidenceConfidence | 2 | Evidence confidence calculation |
| TestScoringEngine | 8 | Engine instantiation and scoring |
| TestDeterminism | 2 | Deterministic output |
| TestDecisionBandDetermination | 6 | All bands reachable, disqualifiers |
| TestNoRealTradingAuthorization | 4 | No band authorizes trading |

### 7.2 Full Test Suite

```
python -m pytest modules/foundups/trade/tests/ -q
342 passed in 1.97s
```

**Breakdown**: 292 existing + 50 new = 342 total

---

## 8. Files Changed

| File | Change |
|------|--------|
| `modules/foundups/trade/src/due_diligence_scoring.py` | NEW (scoring engine, ~400 lines) |
| `modules/foundups/trade/tests/test_due_diligence_scoring.py` | NEW (50 tests) |
| `modules/foundups/trade/tests/TestModLog.md` | UPDATED |
| `docs/audits/architecture/TRADE_DUE_DILIGENCE_SCORING_ENGINE_PHASE1.md` | NEW (this file) |

---

## 9. WSP_97 Verdict

| Check | Result |
|-------|--------|
| Trade due diligence scoring engine only | PASS |
| Pure computation only | PASS |
| Deterministic scoring | PASS |
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

This slice implements the deterministic scoring engine. W10 can review:
- Component scorer logic
- Decision band determination
- Hard disqualifier behavior
- Evidence confidence calculation
- No real trading authorization claim

---

## 11. Next Slice (Do Not Start)

| Slice | Purpose |
|-------|---------|
| `TRADE_DUE_DILIGENCE_SYNTHETIC_REGIME_PACK_PHASE1` | Synthetic test data for scoring validation |

---

*Slice authored under WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22.*
*Slice: TRADE_DUE_DILIGENCE_SCORING_ENGINE_PHASE1*
