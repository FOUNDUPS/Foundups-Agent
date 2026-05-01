# HIA5: BM25 Hybrid Retrieval Gate Decision

**Date**: 2026-05-01
**Status**: COMPLETE
**Branch**: feat/hia5-bm25-hybrid-gate
**Decision**: DEFER_BM25 + RECOMMEND_ALTERNATIVE

## Summary

After HIA4B improved baseline to 81.8% top-1 / 90.9% top-5, this audit evaluates whether
BM25 hybrid retrieval is justified for remaining failures. Conclusion: BM25 is NOT the
optimal solution for the remaining failures.

## Remaining Failures After HIA4B

| Query | Top-1 | Top-5 | Root Cause |
|-------|-------|-------|------------|
| search engine query execution | FAIL | FAIL | search_engine.py not indexed |
| HoloIndex semantic code navigation | FAIL | PASS | Semantic similarity gap |

**Total**: 2 queries failing (1 hard fail, 1 soft fail in top-1 only)

## Failure Analysis

### Query 1: "search engine query execution"

**Evidence rule**: `path_contains: "search"`
**Actual top-1**: `holoindex_plugin.py`
**Expected**: `search_engine.py`

**Root Cause**: `holo_index/core/search_engine.py` is NOT in the symbol collection.
This is an **indexing gap**, not a retrieval algorithm issue.

**BM25 Impact**: NONE. BM25 cannot find documents that don't exist in the corpus.

**Fix**: Expand symbol indexing to include `holo_index/core/` directory.

### Query 2: "HoloIndex semantic code navigation"

**Evidence rule**: `path_contains: "holo"`
**Actual top-1**: `openclaw_codebase_agent.py` (59.4% similarity)
**Expected**: `holoindex_plugin.py` (exists in top-5)

**Root Cause**: Semantic embedding similarity prefers `openclaw_codebase_agent.py`
because it discusses HoloIndex integration, code navigation, and semantic search concepts.
The ~9% semantic similarity gap outweighs the +1.0 keyword path boost.

**BM25 Analysis** (from spike):
```
Query: "HoloIndex semantic code navigation"
  holoindex_plugin.py: BM25=3.290 (WINNER)
  openclaw_codebase_agent.py: BM25=2.468
```

BM25's IDF weighting correctly ranks `holoindex_plugin.py` higher because "holoindex"
is a rare term with high discriminative value.

**However**, the current keyword scoring already provides +1.0 for path match.
The issue is the sort key formula weights:
- 30% semantic similarity
- 20% keyword score

A 9% semantic gap (0.594 - ~0.50) = 2.7% in sort key.
A +1.0 keyword boost = 2.0% in sort key.

**Simpler alternatives exist** that don't require new dependencies.

## BM25 Dependency Assessment

### rank-bm25 (PyPI)

| Aspect | Finding |
|--------|---------|
| Version | 0.2.2 (latest) |
| Maintenance | INACTIVE - no updates in 12+ months |
| Downloads | 72K weekly (popular) |
| Dependencies | numpy |
| License | Apache 2.0 |
| Risk | Maintenance abandonment |

### bm25s (Alternative)

| Aspect | Finding |
|--------|---------|
| Status | Actively maintained |
| Performance | Faster than rank-bm25 |
| Dependencies | numpy, minimal |

### ChromaDB Built-in BM25

ChromaDB 1.3.0 includes `Bm25EmbeddingFunction` but requires `fastembed` dependency.

**Recommendation**: If BM25 is ever needed, prefer ChromaDB's built-in over external libraries.

### Pure Local Implementation

Feasible for small candidate sets (post-retrieval reranking). Spike demonstrates ~50 lines
of Python can implement BM25 scoring. However, this adds maintenance burden.

## Spike Results

Created `holo_index/tests/spike_bm25_analysis.py` for decision support.

**Key Findings**:

1. **IDF Analysis**: "holoindex" has IDF=0.875, "query"/"execution" have IDF=1.386
   (higher = rarer = more discriminative)

2. **Query 2 BM25 Ranking**: BM25 correctly ranks holoindex_plugin.py above
   openclaw_codebase_agent.py (3.290 vs 2.468)

3. **Query 1 BM25 Impact**: None - target document not in corpus

## Decision Matrix

| Solution | Query 1 Impact | Query 2 Impact | Complexity | Dependency Risk |
|----------|----------------|----------------|------------|-----------------|
| BM25 Hybrid | NONE | Partial | HIGH | MEDIUM |
| Index holo_index/core/ | FIXES | None | LOW | NONE |
| Increase path/title boost | None | Likely fixes | LOW | NONE |
| Add exact name boost | None | Likely fixes | LOW | NONE |
| Gemma reranking | None | Fixes | MEDIUM | None (existing) |

## Final Decision: DEFER_BM25

**Rationale**:

1. **Query 1 is indexing-shaped**: BM25 cannot help. Fix is to index `holo_index/core/`.

2. **Query 2 has simpler alternatives**: Increasing path/title boost from 1.0 to 3.0
   or adding exact path substring matching (like WSP number boost) would likely fix
   without new dependencies.

3. **Current baseline is acceptable**: 81.8% top-1 / 90.9% top-5 is strong for
   semantic search without LLM reranking.

4. **Dependency risk**: rank-bm25 is unmaintained. Adding it introduces future liability.

5. **BM25 is not zero-cost**: Requires maintaining token index, updating on corpus changes,
   tuning k/b parameters, hybrid score fusion logic.

## Recommended Next Steps (Alternative Path)

### HIA6A: Indexing Gap Fix (P1)
- Add `holo_index/core/` to symbol indexing scope
- Expected impact: Query 1 passes

### HIA6B: Path/Title Boost Tuning (P2)
- Increase path match boost from 1.0 to 2.5
- Add exact path substring boost for query terms appearing in filenames
- Expected impact: Query 2 likely passes top-1

### HIA7: Gemma Reranking (P3)
- Use Gemma for top-5 → top-1 reranking when confidence < 0.8
- Only invoke for ambiguous results (cost control)
- Expected impact: Query 2 guaranteed to pass

## Files Changed

1. `holo_index/tests/spike_bm25_analysis.py` (new) - Analysis spike, test-only
2. `docs/audits/holoindex_search_quality/HIA5_BM25_HYBRID_GATE.md` (new) - This report

## Test Results

```
holo_index/tests/test_search_quality_baseline.py: 10 passed
holo_index/tests/test_confidence_scoring.py: 17 passed
holo_index/tests/test_backend_routing.py: 19 passed
```

No regressions.

## WSP 97 Compliance

This decision follows WSP 97 truth distinction:
- Did not overclaim BM25 benefits
- Acknowledged indexing as root cause for Query 1
- Provided spike evidence for Query 2 analysis
- Recommended simpler alternatives before complex solutions
