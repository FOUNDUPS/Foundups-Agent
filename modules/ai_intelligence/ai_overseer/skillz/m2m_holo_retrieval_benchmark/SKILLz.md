---
name: m2m_holo_retrieval_benchmark
description: Benchmark Holo retrieval quality and latency before and after M2M staging/promotion
version: 1.0.0
author: 0102
agents: [qwen, gemma]
dependencies: [holo_index, ai_overseer, wre_core]
domain: ai_intelligence
intent_type: TELEMETRY
promotion_state: prototype
pattern_fidelity_threshold: 0.95
category: workflow
evals: []
---
# M2M Holo Retrieval Benchmark Skill

## Purpose

Prevent memory degradation by proving that M2M changes preserve retrieval quality while improving or maintaining search performance.

## Inputs

- `queries`: benchmark query set (required)
- `limit`: per-query result count (default `8`)
- `doc_type`: default `all`
- `reindex`: `true|false` (default `true`)

## Guardrails

1. Must run with fixed query set for comparability.
2. Must capture latency and hit quality metrics.
3. Must fail if fidelity drops below threshold.
4. Must produce machine-readable report for overseer trend tracking.

## Execution Steps

### Step 1: Reindex

If `reindex=true`, run:
- `python holo_index.py --index-wsp`
- `python holo_index.py --index-code`

### Step 2: Baseline and Trial Runs

For each query:
- run semantic search with the same `limit` and `doc_type`
- collect top-hit paths, ranks, latency
- compute quality metrics (precision at k, key-path hit rate)

### Step 3: Evaluate Gates

Pass if all conditions hold:
- no critical key-path loss
- mean latency non-regressive beyond threshold
- query-level fidelity score >= configured threshold

### Step 4: Persist Report

Write:
- `modules/ai_intelligence/ai_overseer/memory/m2m_holo_retrieval_benchmark_latest.json`
- append history:
  `modules/ai_intelligence/ai_overseer/memory/m2m_holo_retrieval_benchmark.jsonl`

## Output Contract

```json
{
  "status": "OK|FAIL",
  "query_count": 12,
  "mean_latency_ms": 43.2,
  "p95_latency_ms": 88.7,
  "precision_at_5": 0.83,
  "key_path_hit_rate": 0.92,
  "fidelity_score": 0.91,
  "regressions": []
}
```

## WSP Chain

- WSP 95: SKILLz wardrobe integration
- WSP 99: M2M evaluation loop
- WSP 87: retrieval-first memory contract
- WSP 50: verify before rollout
- WSP 22: benchmark traceability
