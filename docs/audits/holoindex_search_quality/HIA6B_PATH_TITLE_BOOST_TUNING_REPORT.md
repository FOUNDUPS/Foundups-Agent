# HIA6B: Path/Title Boost Tuning Report

**Date**: 2026-05-01
**Status**: COMPLETE
**Branch**: feat/hia6b-path-title-boost-tuning

## Summary

Implemented normalized underscore matching to fix the remaining HIA6A top-1 failure.
Pass rates improved from 90.9% to 100% (both top-1 and top-5).

## Before/After Metrics

| Metric | Before (HIA6A) | After (HIA6B) | Improvement |
|--------|----------------|---------------|-------------|
| Top-1 Pass Rate | 90.9% (10/11) | 100.0% (11/11) | +9.1% |
| Top-5 Pass Rate | 100.0% (11/11) | 100.0% (11/11) | No change |

## Remaining Failure Analysis

### Query: "HoloIndex semantic code navigation"

**Evidence rule**: `path_contains: "holo"`
**Before**: FAIL top-1, PASS top-5
**After**: PASS top-1, PASS top-5

### Score Breakdown (Before Fix)

| File | Similarity | Keyword Score | Tokens Matched |
|------|------------|---------------|----------------|
| openclaw_codebase_agent.py | 59.4% | +1.0 | "code" (exact) |
| holoindex_plugin.py | 54.3% | +1.0 | "holoindex" (exact) |
| holo_index.py | 62.7% | +0.0 | none (underscore mismatch) |

**Problem**: Query token "holoindex" (no underscore) didn't match path "holo_index"
(with underscore). Despite `holo_index.py` having higher semantic similarity (62.7%),
it received no keyword boost, allowing `openclaw_codebase_agent.py` to win.

## Solution

Added `_normalize_for_match()` helper that removes underscores for fuzzy matching:

```python
def _normalize_for_match(text: str) -> str:
    """Normalize text for fuzzy matching: lowercase, remove underscores."""
    return text.lower().replace("_", "")
```

Applied as secondary path matching with equal boost (+1.0):

```python
if token in path:
    keyword_score += 1.0
elif _normalize_for_match(token) in path_normalized:
    keyword_score += 1.0  # HIA6B: Fuzzy path match
```

### Score Breakdown (After Fix)

| File | Similarity | Keyword Score | Tokens Matched |
|------|------------|---------------|----------------|
| holo_index.py | 62.7% | +1.0 | "holoindex" (fuzzy) |
| openclaw_codebase_agent.py | 59.4% | +1.0 | "code" (exact) |
| holoindex_plugin.py | 54.3% | +1.0 | "holoindex" (exact) |

Now `holo_index.py` wins due to higher semantic similarity with equal keyword boost.

## Regression Analysis

Tested all 11 sentinel queries for regression impact:

| Query | Token Matches Changed | Regression Risk |
|-------|----------------------|-----------------|
| YouTube channel registry | None | Safe |
| demurrage economics simulator | None | Safe |
| browser automation selenium | None | Safe |
| WSP 97 system execution prompting | None | Safe |
| WSP 00 zen state attainment | None | Safe |
| module organization domains | None | Safe |
| search engine query execution | +1 (holoindex fuzzy) | Beneficial |
| **HoloIndex semantic code navigation** | **+1 (holoindex fuzzy)** | **Fix target** |
| route_foundup_job router | None | Safe |
| commit git workflow skill | None | Safe |
| review pull request skill | None | Safe |

**No regressions detected.** The normalized matching only affects queries containing
terms with underscore variations (like "holoindex" vs "holo_index").

## Files Changed

1. `holo_index/core/search_engine.py`:
   - Added `_normalize_for_match()` helper function
   - Applied fuzzy matching in vector search path (line ~385)
   - Applied fuzzy matching in lexical search path (line ~490)

2. `docs/audits/holoindex_search_quality/hia3_baseline_metrics.json`:
   - Regenerated with 100% pass rates

3. `docs/audits/holoindex_search_quality/HIA6B_PATH_TITLE_BOOST_TUNING_REPORT.md`:
   - This report

4. `holo_index/ModLog.md`:
   - Added HIA6B entry

## Test Results

```
holo_index/tests/test_search_quality_baseline.py: 10 passed
holo_index/tests/test_confidence_scoring.py: 17 passed
holo_index/tests/test_backend_routing.py: 19 passed
Total: 46 passed
```

## WSP 97 Compliance

All changes are deterministic:
- Simple string normalization (remove underscores)
- No LLM/BM25/TurboQuant changes
- No new dependencies
- Preserves HIA4B WSP number boost behavior

## HIA Series Summary

| Audit | Top-1 | Top-5 | Key Fix |
|-------|-------|-------|---------|
| HIA3 (baseline) | 54.5% | 54.5% | Category-aware routing |
| HIA4B | 81.8% | 90.9% | WSP number exact match |
| HIA6A | 90.9% | 100.0% | Indexing priority order |
| **HIA6B** | **100.0%** | **100.0%** | **Underscore normalization** |

**Search quality baseline target achieved: 100% top-1, 100% top-5.**
