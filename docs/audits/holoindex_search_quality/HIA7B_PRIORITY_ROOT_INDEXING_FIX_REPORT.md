# HIA7B: Priority Root Indexing Gap Fix Report

**Date**: 2026-05-02
**Status**: COMPLETE
**Branch**: feat/hia7-sentinel-expansion-gate

## Summary

Added priority indexing roots to ensure target files are indexed. Files are now
indexed and discoverable, but semantic drift causes ranking issues that require
separate tuning (HIA8).

## Changes Made

Added 3 priority roots to `indexing_engine.py`:

```python
roots = roots or [
    holo.project_root / "holo_index" / "core",                      # P1: existing
    holo.project_root / "modules" / "infrastructure" / "wre_core" / "src",  # P1: existing
    holo.project_root / "holo_index" / "qwen_advisor",              # P1: HIA7B NEW
    holo.project_root / "modules" / "development" / "ide_foundups" / "src",  # P1: HIA7B NEW
    holo.project_root / "modules" / "foundups" / "agent" / "src",   # P1: HIA7B NEW
    holo.project_root / "modules",                                  # P2: bulk
    # ...
]
```

## Indexing Verification

All target files are now indexed and discoverable:

| Target File | Direct Query | Top-1 Result | Similarity |
|-------------|--------------|--------------|------------|
| wre_bridge.py | "wre_bridge" | wre_bridge.py | 57.2% |
| build_plan.py | "build_plan" | build_plan.py | 55.9% |
| orphan_batch_analyzer.py | "orphan batch analyzer" | orphan_batch_analyzer.py | 66.4% |

**Indexing gap: FIXED**

## Baseline Results

| Metric | HIA7 (Before) | HIA7B (After) | Delta |
|--------|---------------|---------------|-------|
| Top-1 Pass Rate | 86.8% (33/38) | 84.2% (32/38) | -2.6% |
| Top-5 Pass Rate | 92.1% (35/38) | 92.1% (35/38) | 0.0% |

Note: Top-1 decreased by 1 query due to index rebalancing affecting "WRE master orchestrator"
query (performance_orchestrator.py now ranked higher than wre_master_orchestrator.py).

## Failure Analysis (Post-Fix)

### Top-1 Failures (6 queries)

| Query | Got | Expected | Root Cause |
|-------|-----|----------|------------|
| backend routing turboquant embedding | turboquant_backend.py | backend_routing | Semantic drift |
| WRE master orchestrator coordination | performance_orchestrator.py | wre_master_orchestrator | Semantic drift (new) |
| WRE bridge integration cursor | integrate_with_wre.py | wre_bridge | Semantic drift: "integration" boosts wrong file |
| build plan generator hermes | hermes_adapter.py | build_plan | Semantic drift: "hermes" boosts wrong file |
| pfmall catalog verification | test file | pfmall_catalog | Test file ranked higher |
| orphan capability scanner detection | security_scanner.py | orphan | Semantic drift: "scanner" boosts wrong file |

### Top-5 Failures (3 queries)

| Query | Root Cause |
|-------|------------|
| WRE master orchestrator coordination | File exists but semantic drift |
| WRE bridge integration cursor | File exists but semantic drift |
| build plan generator hermes | File exists but semantic drift |

### Root Cause Distribution

| Root Cause | HIA7 Count | HIA7B Count | Status |
|------------|------------|-------------|--------|
| Indexing gap | 3 | 0 | **FIXED** |
| Semantic drift | 2 | 6 | **Increased** (more visible now) |

## Key Insight

The indexing fix was successful: target files are now indexed and appear in top-5
results for direct queries. However, the sentinel queries use natural language
that causes semantic drift:

- Query "WRE bridge integration cursor" → "integration" matches integrate_with_wre.py better
- Query "build plan generator hermes" → "hermes" matches hermes_adapter.py better
- Query "orphan capability scanner detection" → "scanner" matches security_scanner.py better

This is **not an indexing problem** but a **semantic ranking problem** that requires:
1. Query-specific keyword boosting, or
2. LLM-based reranking (HIA8), or
3. Adjusting evidence rules to accept semantic equivalents

## Gate Evaluation

**Gate Criteria**: Top-5 >= 95% AND Top-1 >= 85%

| Metric | Required | Actual | Status |
|--------|----------|--------|--------|
| Top-1 Pass Rate | >= 85% | 84.2% | **FAIL** |
| Top-5 Pass Rate | >= 95% | 92.1% | **FAIL** |

**Gate Result**: NOT PASSED

## Files Changed

1. `holo_index/core/indexing_engine.py`:
   - Added 3 priority roots for HIA7B sentinel coverage

2. `docs/audits/holoindex_search_quality/hia3_baseline_metrics.json`:
   - Regenerated with 38-query baseline after re-indexing

3. `docs/audits/holoindex_search_quality/HIA7B_PRIORITY_ROOT_INDEXING_FIX_REPORT.md`:
   - This report

## Recommendations

### Option A: Proceed to HIA8 (LLM Reranking)

Accept that deterministic ranking has limits. Use Gemma/LLM to rerank top-10
results based on intent matching. This is the recommended path per the HIA series.

### Option B: Keyword Boosting Tuning

Add query-specific keyword detection to boost exact file name matches:
- Query contains "wre_bridge" → boost files with "wre_bridge" in path
- Query contains "build_plan" → boost files with "build_plan" in path

This is deterministic but requires maintaining keyword mappings.

### Option C: Evidence Rule Relaxation

Accept semantic equivalents in evidence rules:
- "wre_bridge" OR "integrate_with_wre" (same module)
- "build_plan" OR "hermes" (same domain)

Not recommended: weakens quality signal.

## Next Steps

1. **HIA8**: Evaluate LLM reranking for semantic drift correction
2. Consider whether 84.2%/92.1% is acceptable baseline before LLM layer
3. If LLM reranking is deferred, tune keyword boosting for high-value queries

## WSP 97 Compliance

Results reported truthfully:
- Indexing gap fixed (verified with direct queries)
- Semantic drift identified as separate root cause
- Gate not passed, documented why
- No overclaiming - improvements are incremental
