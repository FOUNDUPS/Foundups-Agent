# HIA7: Sentinel Query Expansion Report

**Date**: 2026-05-01
**Status**: COMPLETE
**Branch**: feat/hia7-sentinel-expansion-gate

## Summary

Expanded sentinel query set from 11 to 38 queries across 10 categories to validate
search quality before adding LLM reranking. Results show indexing and ranking gaps
that must be addressed before proceeding.

## Expanded Baseline Metrics

| Metric | HIA6B (11 queries) | HIA7 (38 queries) | Delta |
|--------|-------------------|-------------------|-------|
| Top-1 Pass Rate | 100.0% (11/11) | 86.8% (33/38) | -13.2% |
| Top-5 Pass Rate | 100.0% (11/11) | 92.1% (35/38) | -7.9% |
| Confidence Min | 0.68 | 0.655 | -0.025 |
| Confidence Avg | 0.852 | 0.885 | +0.033 |
| Latency p50 | 90ms | 102ms | +12ms |
| Latency p95 | 382ms | 155ms | -227ms |

## Query Categories (38 total)

| Category | Count | Top-1 Pass | Top-5 Pass |
|----------|-------|------------|------------|
| HoloIndex Core | 5 | 4/5 (80%) | 5/5 (100%) |
| WSP Protocols | 6 | 6/6 (100%) | 6/6 (100%) |
| OpenClaw/FoundUpJob | 5 | 5/5 (100%) | 5/5 (100%) |
| WRE Queue/Worker | 4 | 3/4 (75%) | 3/4 (75%) |
| BuildPlan/Swarm | 3 | 2/3 (67%) | 2/3 (67%) |
| pfMALL | 3 | 2/3 (67%) | 3/3 (100%) |
| YouTube/Video | 3 | 3/3 (100%) | 3/3 (100%) |
| Skills/Scanner | 3 | 2/3 (67%) | 2/3 (67%) |
| Code/Symbol | 4 | 4/4 (100%) | 4/4 (100%) |
| Docs/Knowledge | 2 | 2/2 (100%) | 2/2 (100%) |

## Failure Analysis

### Top-1 Failures (5 queries)

| Query | Expected | Got | Root Cause |
|-------|----------|-----|------------|
| backend routing turboquant embedding | `backend_routing` | `turboquant_backend.py` | Semantic drift - "turboquant" in query matches file better |
| WRE bridge integration cursor | `wre_bridge` | `integrate_with_wre.py` | Indexing gap - wre_bridge.py in development/ not indexed |
| build plan generator hermes | `build_plan` | `hermes_adapter.py` | Semantic drift - "hermes" keyword boosts wrong file |
| pfmall catalog verification | `pfmall_catalog` | test file | Ranking - test file ranked above src file |
| orphan capability scanner detection | `orphan` | `security_scanner.py` | Indexing gap - orphan*.py files not in priority roots |

### Top-5 Failures (3 queries)

| Query | Evidence Rule | Files Exist? | Root Cause |
|-------|--------------|--------------|------------|
| WRE bridge integration cursor | `wre_bridge` | Yes | `modules/development/` not in indexed roots |
| build plan generator hermes | `build_plan` | Yes | `modules/foundups/agent/src/` not in priority roots |
| orphan capability scanner detection | `orphan` | Yes | `holo_index/qwen_advisor/` not in priority roots |

### Root Cause Distribution

| Root Cause | Count | % of Failures |
|------------|-------|---------------|
| Indexing gap (file not indexed) | 3 | 60% |
| Semantic drift (wrong file ranked higher) | 2 | 40% |
| Ranking issue (test > src) | 1 | 20% |

Note: Some queries have multiple root causes.

## Target File Verification

All failing queries have target files that exist:

```
holo_index/core/backend_routing.py                           EXISTS
modules/development/ide_foundups/src/wre_bridge.py           EXISTS
modules/foundups/agent/src/build_plan.py                     EXISTS
modules/foundups/agent/src/build_plan_generator.py           EXISTS
modules/communication/moltbot_bridge/src/pfmall_catalog.py   EXISTS
holo_index/qwen_advisor/orphan_batch_analyzer.py             EXISTS
modules/infrastructure/code_quality/tools/orphan_analyzer.py EXISTS
```

## Gate Evaluation

**Gate Criteria**: Top-5 >= 95% AND Top-1 >= 85%

| Metric | Required | Actual | Status |
|--------|----------|--------|--------|
| Top-1 Pass Rate | >= 85% | 86.8% | PASS |
| Top-5 Pass Rate | >= 95% | 92.1% | **FAIL** |

**Gate Result**: NOT PASSED

## Recommendations

### Option A: Fix Indexing Gaps (Recommended)

Add missing directories to priority roots in `indexing_engine.py`:

```python
roots = [
    holo.project_root / "holo_index" / "core",           # P1: search infrastructure
    holo.project_root / "holo_index" / "qwen_advisor",   # P1: add for orphan analyzers
    holo.project_root / "modules" / "infrastructure" / "wre_core" / "src",
    holo.project_root / "modules" / "development" / "ide_foundups" / "src",  # P1: add for wre_bridge
    holo.project_root / "modules" / "foundups" / "agent" / "src",            # P1: add for build_plan
    holo.project_root / "modules",
    # ... rest
]
```

Expected impact: Fixes 3/5 top-1 failures, likely achieves 95%+ top-5.

### Option B: Relax Evidence Rules

For semantic drift failures, use broader evidence:
- `backend_routing` -> also accept `turboquant_backend` (related)
- `build_plan` -> also accept `hermes` (same domain)

Not recommended: Loosens quality bar rather than fixing root cause.

### Option C: Proceed to HIA8

Accept 92.1% top-5 as acceptable baseline, proceed with LLM reranking.

Not recommended until indexing gaps are closed.

## Next Steps

1. **HIA7B**: Fix indexing priority roots for failing categories
2. Re-run baseline after indexing fix
3. If gate passes (top-5 >= 95%), proceed to HIA8 (LLM reranking evaluation)

## Files Changed

1. `holo_index/tests/test_search_quality_baseline.py`:
   - Expanded SENTINEL_QUERIES from 11 to 38 queries
   - Added 10 category coverage

2. `docs/audits/holoindex_search_quality/hia3_baseline_metrics.json`:
   - Regenerated with 38-query baseline

3. `docs/audits/holoindex_search_quality/HIA7_SENTINEL_EXPANSION_REPORT.md`:
   - This report

## WSP 97 Compliance

Results reported truthfully:
- Pass rates reflect actual search performance
- Failures documented with root cause analysis
- No overclaiming - gate not passed, documented why
- Evidence rules validated against existing files
