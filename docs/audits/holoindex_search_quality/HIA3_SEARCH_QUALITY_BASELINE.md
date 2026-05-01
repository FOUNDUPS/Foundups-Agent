# HIA3: HoloIndex Search Quality Baseline

**Date**: 2026-05-01
**Status**: BASELINE CAPTURED (HIA3B diagnostic applied)
**Corpus**: 20,413 documents (frozen at 4bf59321a7cf)

## Executive Summary

Search quality baseline established with **54.5% pass rate** across 11 sentinel queries.
This truthful measurement identifies gaps before BM25, Gemma reranking, or corrective RAG changes.

**HIA3B Diagnostic**: Initial baseline showed 9.1% due to a harness bug that prioritized code
results over category-specific results. After fixing category-aware hit selection, true pass
rate is 54.5%.

## Methodology

### Sentinel Query Design
- 11 queries covering code/wsp/symbol/skill categories
- Each has an **evidence rule** (path_contains, type_equals)
- Pass = expected item appears in top-1 or top-5 results
- **Category-aware evaluation**: WSP queries check WSP results, skill queries check skill results

### Test Configuration
```
HOLO_USE_TURBOQUANT=0  (pure fp32 embeddings)
HOLO_EMIT_CONFIDENCE=1 (capture confidence scores)
```

## Results

| Metric | Value |
|--------|-------|
| Top-1 Pass Rate | 54.5% (6/11) |
| Top-5 Pass Rate | 54.5% (6/11) |
| Latency p50 | 91ms |
| Latency p95 | 419ms |
| Confidence avg | 0.76 |

### Query-by-Query Analysis

| Query | Category | Pass? | Finding |
|-------|----------|-------|---------|
| YouTube channel registry | code | PASS | Found youtube_channel_registry.py |
| demurrage economics simulator | code | PASS | Found demurrage.py |
| browser automation selenium | code | FAIL | Found linkedin_actions.py (no selenium in path) |
| WSP 97 truth distinction protocol | wsp | FAIL | Found WSP 94 instead of WSP 97 |
| WSP 00 zen state attainment | wsp | PASS | Found WSP_00_Zen_State_Attainment_Protocol.md |
| module organization domains | wsp | PASS | Found WSP_3_Enterprise_Domain_Organization.md |
| execute_search function | symbol | FAIL | Found demurrage.py (no search in path) |
| HoloIndex class initialization | symbol | FAIL | Found demurrage.py (no holo_index in path) |
| route_foundup_job router | symbol | FAIL | Found demurrage.py (no foundup_job in path) |
| commit git workflow skill | skill | PASS | Found skillz type document |
| review pull request skill | skill | PASS | Found skillz type document |

## Root Cause Analysis

### Issue 1: Symbol Collection Noise (3 failures)
`demurrage.py` appears as top-1 for unrelated symbol queries (execute_search, HoloIndex, foundup_job).
The symbol collection may have over-indexed this file or the embedding vectors are too similar.

### Issue 2: Semantic Mismatch (1 failure)
"WSP 97 truth distinction protocol" finds WSP 94 (Agent Coordination) instead of WSP 97.
Embedding similarity doesn't distinguish between different WSP numbers.

### Issue 3: Missing Index Coverage (1 failure)
"browser automation selenium" finds linkedin_actions.py. The selenium modules may not be
in the indexed corpus, or the query doesn't match selenium-related embeddings.

## HIA3B Diagnostic Summary

**Original bug**: `all_hits = code + wsps + skills` always checked code first, causing WSP
and skill queries to fail when any code result existed.

**Fix**: Category-aware hit selection routes queries to their primary category before
falling back to combined results.

## WSP 97 Compliance

This baseline is recorded truthfully:
- **No overclaiming**: 54.5% is the actual pass rate
- **Failures documented**: 5/11 queries fail for specific reasons
- **No LLM in hot path**: Pure embedding search, Gemma/Qwen not invoked
- **Harness bug fixed**: HIA3B diagnostic corrected false negative rate

## Recommendations for HIA4+

1. **Symbol collection deduplication** - Investigate demurrage.py over-representation
2. **BM25 hybrid for WSP numbers** - "WSP 97" should keyword-match WSP_97*.md
3. **Verify selenium indexing** - Check if foundups_selenium module is in corpus
4. **Query expansion** - Map "selenium" to related file paths

## Files

- Test suite: `holo_index/tests/test_search_quality_baseline.py`
- Baseline JSON: `docs/audits/holoindex_search_quality/hia3_baseline_metrics.json`
- Corpus manifest: `docs/audits/holoindex_turboquant/corpus_freeze_manifest.json`
