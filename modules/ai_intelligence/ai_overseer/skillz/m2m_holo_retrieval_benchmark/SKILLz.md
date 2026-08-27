---
name: m2m_holo_retrieval_benchmark
description: Measure one pinned HoloIndex generation with receipt-bound public regression evidence
version: 2.0.0
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

Measure HoloIndex retrieval quality without mutating the index. The skill runs
against the authenticated generation-bound query owner and emits a benchmark
run plus a deterministically recomputed verification receipt.

## Inputs

- fixed public regression corpus: checked-in `retrieval_corpus_v1.json`
  (not caller-overridable and not independent promotion evidence)
- `limit`: per-query result count (default `8`)
- `reindex`: must be absent or `false`; `true` fails closed

## Guardrails

1. Every query must have at least one graded relevant path.
2. Every result must bind the exact repository root, SHA, generation, and freshness receipt.
3. The owner must prove that no re-index occurred during the query.
4. Metrics are Recall@K, MRR, nDCG@K, mean latency, and p95 latency.
5. Verification recomputes ranking metrics from the bound query receipts.
6. Recall@K, MRR, and nDCG@K must each meet the fixed `0.95` quality policy.
7. The skill never promotes a generation or writes repository artifacts.

## Execution Steps

### Step 1: Bind the Candidate

Load the current freshness generation and bind the benchmark limit plus the
ranker source digest. Missing bindings fail closed.

### Step 2: Run Held-Out Queries

For each query, use the authenticated loopback owner and build a
`holoindex_query_receipt.v1`. Console output is never parsed.

### Step 3: Evaluate Gates

The deterministic verifier checks the corpus, split, candidate binding, query
receipts, ranked paths, and aggregate metrics. A valid run is evaluation
evidence only; it is not promotion authority.

### Step 4: Return Receipts

Return the benchmark and verification receipts to the governed WRE caller.
Negative-outcome persistence is `SPECIFIED_NOT_IMPLEMENTED` in this slice; a
governed caller must retain it later, never through a query-time repository
write.

## Output Contract

```json
{
  "success": true,
  "benchmark_run": {
    "schema_version": "holoindex_retrieval_benchmark_run.v1",
    "metrics": {"recall_at_k": 1.0, "mrr": 1.0, "ndcg_at_k": 1.0},
    "no_holoindex_reindex_performed": true,
    "no_generation_promotion_performed": true
  },
  "verification": {
    "schema_version": "holoindex_retrieval_benchmark_verification.v1",
    "accepted": true
  }
}
```

## Truth Boundary

The deterministic receipt IDs prove integrity after serialization. They are
not signatures and do not authorize promotion. A future promotion transaction
must use a separate sealed evaluation corpus, rehydrate the receipts, and
require independently administered signed authority. The legacy `heldout_cases` field means
only that those cases are excluded from `train_cases`.

The benchmark runtime's `evaluate_m2m_holo_retrieval_a_grade(...)` facade
is content-bound to the separate `m2m_holo_retrieval_grade_gate` module and can admit
A-grade evidence only after it re-runs this fixed public corpus and a distinct
evaluator supplies a valid
signature-verifier-approved envelope over a sealed, public-corpus-disjoint
evaluation. The current verifier is an injected seam, not deployed signing
trust. That admission is
still not promotion authority.
The thresholds cannot be weakened. This facade is not currently registered as
an AI Overseer/VSIX Skillz operation; independent evaluator trust and a
non-test caller remain future governed composition work.

The Skillz calls the existing authenticated loopback owner client directly.
Its public API does not accept an arbitrary query callback.
Each result must bind the clean authority candidate to the ranker digest the
owner computed from its actually loaded retrieval modules.

## WSP Chain

- WSP 95: SKILLz wardrobe integration
- WSP 99: M2M evaluation loop
- WSP 87: retrieval-first memory contract
- WSP 50: verify before rollout
- WSP 22: benchmark traceability
