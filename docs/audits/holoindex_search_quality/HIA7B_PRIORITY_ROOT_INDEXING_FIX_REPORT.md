# HIA7B: Priority Root Indexing Gap Fix Report

**Date**: 2026-05-02
**Status**: COMPLETE - NOT PROMOTED
**Branch**: feat/hia7-sentinel-expansion-gate
**Decision**: Path A - Code reverted, audit preserved

## Summary

Investigated adding priority indexing roots to fix indexing gaps identified in HIA7.
The change improved direct file discoverability but caused a regression in sentinel
query pass rates. **Code reverted. Change not promoted.**

## Experiment

### Hypothesis

Adding priority roots for missing files would improve sentinel query pass rates:
- `holo_index/qwen_advisor/` (orphan analyzers)
- `modules/development/ide_foundups/src/` (wre_bridge.py)
- `modules/foundups/agent/src/` (build_plan.py)

### Results

| Metric | HIA7 (Before) | HIA7B (After) | Delta |
|--------|---------------|---------------|-------|
| Top-1 Pass Rate | 86.8% (33/38) | 84.2% (32/38) | **-2.6%** |
| Top-5 Pass Rate | 92.1% (35/38) | 92.1% (35/38) | 0.0% |

**Outcome**: Top-1 REGRESSED. Gate NOT passed in either case.

### Direct Query Verification

Target files became discoverable via direct queries:

| Target File | Direct Query | Rank | Similarity |
|-------------|--------------|------|------------|
| wre_bridge.py | "wre_bridge" | #1 | 57.2% |
| build_plan.py | "build_plan" | #1 | 55.9% |
| orphan_batch_analyzer.py | "orphan batch analyzer" | #1 | 66.4% |

However, sentinel queries use natural language and continue to exhibit semantic drift.

## Decision: Path A - Revert

### Rationale

1. **Regression**: Top-1 pass rate decreased from 86.8% to 84.2%
2. **Gate not passed**: Neither before (86.8%/92.1%) nor after (84.2%/92.1%) met the
   gate criteria (top-1 >= 85%, top-5 >= 95%)
3. **WSP 97 compliance**: Cannot claim improvement when metrics regressed
4. **Direct discoverability not in gate**: The benefit (files findable via direct
   queries) is not part of the sentinel gate criteria

### Action Taken

- `indexing_engine.py`: Reverted to HIA7 state (no priority root additions)
- `hia3_baseline_metrics.json`: Restored to HIA7 state (86.8%/92.1%)
- This report: Updated to document experiment and decision

## Root Cause Analysis

The priority root change caused index rebalancing that affected unrelated queries:
- "WRE master orchestrator coordination" regressed (new failure)
- Adding more P1 roots shifted which files appeared in the 20K symbol limit

The remaining failures are **semantic drift**, not indexing gaps:
- Query "WRE bridge integration cursor" → "integration" matches integrate_with_wre.py better
- Query "build plan generator hermes" → "hermes" matches hermes_adapter.py better
- Query "orphan capability scanner detection" → "scanner" matches security_scanner.py better

## Final State

| Metric | Value | Gate Requirement | Status |
|--------|-------|------------------|--------|
| Top-1 Pass Rate | 86.8% (33/38) | >= 85% | PASS |
| Top-5 Pass Rate | 92.1% (35/38) | >= 95% | FAIL |

**Code**: Unchanged from HIA7 (no priority root additions)
**Baseline**: 86.8% top-1, 92.1% top-5 (38 queries)

## Recommendations

### Optional: HIA8 (LLM Reranking)

If top-5 >= 95% is required, consider LLM reranking for semantic drift correction.
This is not mandatory; current 92.1% may be acceptable baseline.

### Not Recommended

- Do not add priority roots without regression testing
- Do not claim indexing fixes improve quality without sentinel verification

## WSP 97 Compliance

- No "gate passed" claim (gate not passed)
- No "quality improved" claim (top-1 regressed)
- Experiment documented truthfully
- Decision rationale transparent
