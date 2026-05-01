# HIA3: HoloIndex Search Quality Baseline

**Date**: 2026-05-01
**Status**: BASELINE CAPTURED
**Corpus**: 20,413 documents (frozen at 4bf59321a7cf)

## Executive Summary

Search quality baseline established with **9.1% pass rate** across 11 sentinel queries. 
This truthful measurement identifies the gap before BM25, Gemma reranking, or corrective RAG changes.

## Methodology

### Sentinel Query Design
- 11 queries covering code/wsp/symbol/skill categories
- Each has an **evidence rule** (path_contains, title_contains, type_equals)
- Pass = expected item appears in top-1 or top-5 results

### Test Configuration
```
HOLO_USE_TURBOQUANT=0  (pure fp32 embeddings)
HOLO_EMIT_CONFIDENCE=1 (capture confidence scores)
```

## Results

| Metric | Value |
|--------|-------|
| Top-1 Pass Rate | 9.1% (1/11) |
| Top-5 Pass Rate | 9.1% (1/11) |
| Latency p50 | 52ms |
| Latency p95 | 432ms |
| Confidence (only passing) | 0.85 |

### Query-by-Query Analysis

| Query | Category | Pass? | Finding |
|-------|----------|-------|---------|
| YouTube channel registry | code | PASS | Found via symbol collection |
| demurrage economics simulator | code | FAIL | No results |
| browser automation selenium | code | FAIL | No results |
| WSP 97 truth distinction protocol | wsp | FAIL | No results |
| WSP 00 zen state attainment | wsp | FAIL | No results |
| module organization domains | wsp | FAIL | No results |
| execute_search function | symbol | FAIL | No results |
| HoloIndex class initialization | symbol | FAIL | No results |
| route_foundup_job router | symbol | FAIL | No results |
| commit git workflow skill | skill | FAIL | No results |
| review pull request skill | skill | FAIL | No results |

## Root Cause Analysis

### Primary Issue: Low Result Yield
10/11 queries return **zero results**. This indicates:

1. **Similarity threshold too high**: Queries don't reach the minimum similarity cutoff
2. **Embedding vocabulary mismatch**: Natural language queries vs code/technical documents
3. **Collection routing gaps**: Some collections may not be searched for certain query types

### Secondary Issue: Collection Coverage
The single passing query found its match in `navigation_symbols` (20,000 docs).
WSP collection (117 docs) and skills collection (59 docs) produced no matches.

## WSP 97 Compliance

This baseline is recorded truthfully:
- **No overclaiming**: 9.1% is the actual pass rate
- **Failures documented**: 10/11 queries produce no results
- **No LLM in hot path**: Pure embedding search, Gemma/Qwen not invoked

## Recommendations for HIA4+

1. **Lower similarity threshold** - Current threshold may be too aggressive
2. **Add BM25 hybrid** - Keyword matching would help WSP/skill queries
3. **Reranker** - Gemma reranking could boost relevant results
4. **Query expansion** - Map natural language to technical terms

## Files

- Test suite: `holo_index/tests/test_search_quality_baseline.py`
- Baseline JSON: `docs/audits/holoindex_search_quality/hia3_baseline_metrics.json`
- Corpus manifest: `docs/audits/holoindex_turboquant/corpus_freeze_manifest.json`
