# HoloIndex FoundUp Query Alias and Targeted Verdict — Phase 1

**Slice**: `HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1`
**Agent**: 0102
**Date**: 2026-05-23
**Mode**: HoloIndex retrieval quality fix
**Branch**: `feat/holoindex-foundup-query-alias-phase1`
**WSP Lock**: WSP_00 -> WSP_15 -> WSP_50 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22

---

## WSP_97 Truth Boundary Checklist

| Label | Status |
|-------|--------|
| HOLOINDEX_RETRIEVAL_QUALITY_FIX_ONLY | YES |
| QUERY_ALIAS_EXPANSION_ONLY | YES |
| TARGET_VERDICT_CHECK_ONLY | YES |
| HOLOINDEX_CORE_MUTATION_AUTHORIZED_FOR_RETRIEVAL_QUALITY | YES |
| NO_LIVE_REINDEX | YES |
| NO_GENERATED_INDEX_ARTIFACTS | YES |
| NO_TRADE_STATUS_CHANGE | YES |
| NO_TRADE_RUNTIME_CHANGE | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_CATALOG_MUTATION | YES |
| NO_PROJECTION_MUTATION | YES |
| NO_DEPENDENCY_INSTALL | YES |
| NO_CI_CHANGE | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Problem Statement

Natural analyst language queries for Trade module failed to surface Trade documentation:

| Query | Before Fix | After Fix |
|-------|------------|-----------|
| "Trade pump.fun memecoin issuer X telegram influencer rug pull large trades" | whack_a_magat, ritual, unrelated | Trade ModLog, pumpfun_comparison |
| "Trade FoundUp pump.fun memecoin launchpad simulation" | partial | Trade README, ROADMAP, ModLog, test_adapter_contracts.py |

**Root cause**: HoloIndex did not expand analyst language aliases (pump.fun, memecoin, issuer, rug pull) to Trade module terminology (pumpfun, meme-coin, creator_address, rug_pull_score).

---

## 2. Implementation

### 2.1 Search-Time Alias Expansion (search_engine.py)

Added `_TRADE_ALIAS_GROUPS` mapping analyst language to Trade terminology:

```python
_TRADE_ALIAS_GROUPS = {
    "pump.fun": ["pumpfun", "pump fun", "pump_fun"],
    "memecoin": ["meme-coin", "meme coin", "meme_coin"],
    "issuer": ["creator", "creator_address", "token_creator"],
    "rug pull": ["rug_pull_score", "soft-rug", "honeypot"],
    "twitter": ["x account", "socialevent", "social_event"],
    "large trades": ["top traders", "walletevent", "holder distribution"],
    # ... additional aliases
}
```

### 2.2 Trade Intent Detection

Added `_is_trade_intent_query()` detecting Trade keywords:
- Platform: pump.fun, pumpfun, launchpad
- Token: memecoin, meme-coin
- Risk: rug pull, honeypot, soft-rug
- Social: twitter, telegram, influencer
- Activity: whale, top traders, holder distribution

### 2.3 Path Boost for Trade Module

Added `_trade_path_boost()`:
- 8.0 boost for Trade target docs (README, INTERFACE, ROADMAP, contracts.py)
- 5.0 boost for any Trade module path

### 2.4 Target-Aware Verdict (agentic_rag_verdict.py)

Added `QueryIntent.TRADE` with target-aware rules:
- **SUFFICIENT**: Trade module evidence found in results
- **DEGRADED**: Hits exist but no Trade module evidence
- **UNSAFE_TO_ACT**: No hits at all

---

## 3. Before/After Retrieval Comparison

### Query 1: "Trade pump.fun memecoin issuer X telegram influencer rug pull large trades WSP 15 rating"

**BEFORE**:
```
[CODE] modules/infrastructure/wre_core/src/improvement_job_contract.py
[CODE] modules/gamification/whack_a_magat/src/whack.py
[DOCS] docs/SPRINT_1_2_WSP_COMPLIANCE_AUDIT.md
[DOCS] modules/communication/video_comments/skillz/tars_account_swapper/README.md
```
Trade docs: **0 in top results**

**AFTER**:
```
[CODE] modules/foundups/simulator/economics/pumpfun_comparison.py
[DOCS] modules/foundups/trade/ModLog.md
```
Trade docs: **1+ in top results**

### Query 2: "Trade FoundUp pump.fun memecoin launchpad simulation"

**BEFORE**: Partial Trade hits

**AFTER**:
```
[CODE] modules/foundups/trade/tests/test_adapter_contracts.py
[DOCS] modules/foundups/trade/README.md
[DOCS] modules/foundups/trade/ROADMAP.md
[DOCS] modules/foundups/trade/ModLog.md
```
Trade docs: **3 in top docs results**

---

## 4. Test Results

### 4.1 New Tests

```
python -m pytest holo_index/tests/test_trade_query_alias_retrieval.py -v
36 passed in 2.52s
```

| Test Class | Tests | Purpose |
|------------|-------|---------|
| TestTradeIntentDetection | 8 | Trade keyword detection |
| TestTradeAliasExpansion | 5 | Alias expansion logic |
| TestTradePathBoost | 6 | Path boost scoring |
| TestTradeAliasKeywordBoost | 2 | Content alias matching |
| TestTradeQueryIntentClassification | 5 | Intent classification |
| TestTradeModuleEvidenceDetection | 5 | Evidence detection |
| TestTradeVerdictClassification | 3 | Verdict logic |
| TestRegressionPreviousBehavior | 2 | WSP/general intent preserved |

### 4.2 Regression Suites

```
python -m pytest holo_index/tests/test_audit_spec_slice_id_indexing.py \
                 holo_index/tests/test_hxa_retrieval_fix.py \
                 holo_index/tests/test_work_ledger_indexing.py \
                 holo_index/tests/test_search_quality_baseline.py -q
135 passed in 13.91s
```

---

## 5. Files Changed

| File | Change |
|------|--------|
| `holo_index/core/search_engine.py` | Added Trade alias registry, path boost, keyword boost |
| `holo_index/core/agentic_rag_verdict.py` | Added TRADE intent, target-aware verdict |
| `holo_index/tests/test_trade_query_alias_retrieval.py` | NEW (36 tests) |
| `docs/audits/holoindex_search_quality/HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1.md` | NEW (this file) |
| `holo_index/ModLog.md` | UPDATED |

---

## 6. WSP_97 Verdict

| Check | Result |
|-------|--------|
| HoloIndex retrieval quality fix only | PASS |
| Query alias expansion only | PASS |
| Target verdict check only | PASS |
| HoloIndex core mutation authorized | PASS |
| No live reindex | PASS |
| No generated index artifacts | PASS |
| No Trade status change | PASS |
| No Trade runtime change | PASS |
| No registry mutation | PASS |
| No catalog mutation | PASS |
| No projection mutation | PASS |
| No dependency install | PASS |
| No CI change | PASS |
| No CABR ready | PASS |
| No payout ready | PASS |
| No DAO activation | PASS |

**Verdict**: PASS

---

## 7. W10 Readiness

This slice improves HoloIndex retrieval quality for Trade module queries. W10 can now rely on HoloIndex to surface Trade documentation when analyst language queries are used.

---

*Slice authored under WSP_00 -> WSP_15 -> WSP_50 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22.*
*Slice: HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1*
