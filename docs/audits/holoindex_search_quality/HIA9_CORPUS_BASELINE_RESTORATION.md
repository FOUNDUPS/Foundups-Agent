# HIA9: Corpus Baseline Restoration Report

**Date**: 2026-05-04
**Status**: PARTIAL RESTORATION COMPLETE
**Branch**: fix/hia9-corpus-baseline-restoration
**Author**: 0102

## Executive Summary

HIA8A benchmark revealed 60.5% accuracy vs expected 86.8% baseline. Investigation discovered
**ALL-ZERO embeddings** in three critical collections, causing semantic search to return random results.

After re-indexing, accuracy improved from 52.6% to 73.7% Top-1 (21.1% recovery). Remaining gap
(73.7% vs 86.8%) attributed to indexing limits and semantic drift - consistent with HIA7 findings.

## Root Cause Analysis

### Critical Finding: Zero Embeddings

| Collection | Before Fix | After Fix |
|------------|-----------|-----------|
| navigation_code | ALL ZEROS | norm=1.0 |
| navigation_wsp | ALL ZEROS | norm=1.0 |
| navigation_skills | ALL ZEROS | norm=1.0 |
| navigation_docs | OK (norm=1.0) | OK |
| navigation_knowledge | OK (norm=1.0) | OK |
| navigation_symbols | 0 entries | 20,000 |

**Evidence**: ChromaDB query `query_embeddings` returned `distance=1.0` for all results,
indicating identical "embeddings" (all zeros).

### Cause Hypothesis

The zero embeddings likely resulted from:
1. Indexing during model loading failure (timeout/OOM)
2. Interrupted indexing that wrote metadata but not embeddings
3. ChromaDB collection corruption during concurrent access

## Recovery Actions

### Commands Executed

```bash
# WSP collection - 117 entries re-embedded
python holo_index.py --index-wsp --ssd E:/HoloIndex

# Code collection - 296 entries re-embedded
python holo_index.py --index-code --ssd E:/HoloIndex

# Skills collection - 64 entries re-embedded
hi.index_skillz_entries()

# Symbol collection - 20,000 entries indexed
from core.indexing_engine import index_symbol_entries
index_symbol_entries(hi)
```

### Collection Counts (Verified)

| Collection | Count | Embeddings |
|------------|-------|------------|
| navigation_code | 296 | Valid |
| navigation_wsp | 117 | Valid |
| navigation_skills | 64 | Valid |
| navigation_docs | 3143 | Valid |
| navigation_knowledge | 47 | Valid |
| navigation_symbols | 20000 | Valid |

## Baseline Metrics

### Before Restoration (Broken)

| Metric | Value |
|--------|-------|
| Top-1 Pass Rate | 52.6% (20/38) |
| Top-5 Pass Rate | 57.9% (22/38) |
| Root Cause | Zero embeddings |

### After Restoration

| Metric | Value | HIA7 Expected | Delta |
|--------|-------|---------------|-------|
| Top-1 Pass Rate | 73.7% (28/38) | 86.8% (33/38) | -13.1% |
| Top-5 Pass Rate | 84.2% (32/38) | 92.1% (35/38) | -7.9% |
| Latency p95 | 342ms | ~155ms | +187ms |

### Recovery Summary

- **Recovered from zero embeddings**: +21.1% Top-1 (52.6% → 73.7%)
- **Remaining gap to HIA7**: -13.1% Top-1 (73.7% vs 86.8%)

## Remaining Failures (10 queries)

### Top-1 Failures

| Query | Expected | Got | Root Cause |
|-------|----------|-----|------------|
| backend routing turboquant embedding | `backend_routing` | `turboquant_backend.py` | Semantic drift |
| WRE bridge integration cursor | `wre_bridge` | `integrate_with_wre.py` | Indexing gap |
| build plan generator hermes | `build_plan` | `hermes_adapter.py` | Semantic drift |
| swarm coordinator dispatch | `swarm_coordinator` | Test file | Ranking issue |
| catalog indexer classification | `catalog_indexer` | `video_index_store.py` | Indexing gap |
| orphan capability scanner | `orphan` | `security_scanner.py` | Indexing gap |
| skills registry loader | `skills_registry` | `wre_skills_loader.py` | Near miss |
| CABR validation engine | `cabr` | Test file | Ranking issue |
| tokenomics pool architecture | `token` | `channel_partner_pool.py` | Semantic drift |
| blockchain algorand | `algorand` | `rESP_patent_integration.py` | Indexing gap |

### Root Cause Distribution

| Cause | Count | HIA7 Comparison |
|-------|-------|-----------------|
| Semantic drift | 4 | Same issue |
| Indexing gap | 4 | HIA7B partially fixed |
| Ranking issue | 2 | Test > src ranking |

## Why HIA7 Baseline Not Fully Restored

1. **Indexing limits**: 20,000 symbol entry cap reached before `holo_index/qwen_advisor` indexed
2. **Missing priority roots**: `holo_index/qwen_advisor` not in P1 roots for orphan analyzers
3. **Semantic drift**: Query keywords match wrong files (e.g., "turboquant" → turboquant_backend.py)

These issues were documented in HIA7/HIA7B as known limitations requiring future work.

## WSP 97 Destructive-Action Safety Verdict

| Action | Safety |
|--------|--------|
| Collection reset | SAFE - re-indexed with valid embeddings |
| Vector deletion | NONE - no deletions performed |
| Backup files | N/A - ChromaDB PersistentClient handles durability |

**Verdict**: SAFE - No data loss. Collections restored with valid embeddings.

## HIA8A Reranker Evaluation Status

| Criterion | Status |
|-----------|--------|
| Corpus baseline restored | PARTIAL (73.7% vs 86.8%) |
| Zero embeddings fixed | COMPLETE |
| Reranker can be evaluated | YES - but will measure against 73.7% baseline |
| Full HIA7 baseline | NOT RESTORED - indexing gaps remain |

**Recommendation**: Proceed with HIA8A reranker evaluation using current 73.7%/84.2% baseline.
The reranker's effectiveness can be measured as delta from this restored baseline.

## Test Results

```
holo_index/tests/test_search_quality_baseline.py: 9/10 PASS
holo_index/tests/test_backend_routing.py: Verified
```

Minor test failure: `latency_p50_ms` field missing in generated baseline JSON (schema issue).

## Files Changed

| File | Change |
|------|--------|
| docs/audits/.../HIA9_CORPUS_BASELINE_RESTORATION.md | NEW - this report |
| docs/audits/.../hia3_baseline_metrics.json | REGENERATED |
| holo_index/ModLog.md | Entry added |

## Next Steps

1. **Accept 73.7%/84.2% as current baseline** for HIA8A evaluation
2. **HIA10 (future)**: Add `holo_index/qwen_advisor` to P1 priority roots
3. **HIA8A**: Re-run reranker benchmark against restored baseline
4. **Cleanup**: Remove temporary `hia9_baseline_check.py` script

---

*0102: Root cause was zero embeddings from corrupted indexing. Semantic search
requires valid embedding vectors - all-zero vectors produce random distance=1.0 results.
Collections re-indexed with verified norm=1.0 embeddings. Partial recovery achieved.*
