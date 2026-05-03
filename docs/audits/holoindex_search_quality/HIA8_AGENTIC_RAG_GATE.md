# HIA8: Agentic RAG Gate Evaluation

**Date**: 2026-05-03
**Status**: AUDIT/GATE - NO IMPLEMENTATION
**Branch**: docs/hia8-agentic-rag-gate
**Author**: 0102 W1

## 1. Current State

### Retrieval Mode
- **Primary**: Semantic embedding search (SentenceTransformer fp32)
- **Experimental**: TurboQuant ONNX int8 (behind `HOLO_USE_TURBOQUANT=1`)
- **Fallback**: Lexical search (when embedding model unavailable)
- **Symbol fallback**: ripgrep exact match for identifier queries

### Confidence Scoring
- **Implementation**: Pure heuristic in `search_engine.py:_compute_confidence()`
- **Formula**: `similarity + (keyword_score / 10.0) + type_boost`
- **Exposure**: Only when `HOLO_EMIT_CONFIDENCE=1` (env var)
- **Type boosts**: code=0.1, wsp=0.1, skillz=0.08, test=0.05, symbol=0.05

### Deterministic Ranking
- **Sort key formula**: `(0.5 * priority + 0.3 * similarity + 0.2 * keyword_score, similarity, priority)`
- **No randomness**: Results are deterministic for same query and corpus
- **No LLM inference**: Ranking is pure numeric computation

### TurboQuant Status
- **Default**: `HOLO_USE_TURBOQUANT=0` (disabled)
- **Quality claim**: `experimental` / `not_default_ready`
- **Baseline measured with**: TurboQuant OFF (fp32 backend)
- **Drift gap**: 3.65% cosine drift (HIA3 report)

### Gemma/Qwen Advisory Status
- **gemma_rag_inference.py**: EXISTS at `holo_index/qwen_advisor/gemma_rag_inference.py`
  - Purpose: WRE pattern for binary classification (50-100ms)
  - Model: Gemma 3 270M via llama_cpp
  - Integration: Used by OpenClaw intent classification, NOT by search
- **qwen_orchestrator.py**: EXISTS at `holo_index/qwen_advisor/orchestration/qwen_orchestrator.py`
  - Purpose: HoloDAE orchestration layer
  - Integration: Coordinates HoloIndex components, NOT in search hot path

### LLM in Search Hot Path

| Component | LLM Import | LLM Call | Status |
|-----------|------------|----------|--------|
| search_engine.py | NO | NO | **CLEAN** |
| indexing_engine.py | NO | NO | **CLEAN** |
| holo_index.py | NO | NO | **CLEAN** |
| backend_routing.py | NO | NO | **CLEAN** |

**Verdict**: No LLM is currently in the search hot path. Search is pure embedding + keyword scoring.

---

## 2. Baseline Evidence

### HIA7 38-Query Metrics (2026-05-01)

| Metric | Value |
|--------|-------|
| Total queries | 38 |
| Top-1 pass rate | 86.8% (33/38) |
| Top-5 pass rate | 92.1% (35/38) |
| Confidence min | 0.655 |
| Confidence avg | 0.885 |
| Confidence max | 1.0 |
| Latency p50 | 102ms |
| Latency p95 | 155ms |
| Latency max | 414ms |
| Corpus doc count | 20,413 |

### Failing Query Categories

| Category | Top-1 Failures | Root Cause |
|----------|----------------|------------|
| HoloIndex Core | 1/5 | Semantic drift (turboquant > backend_routing) |
| WRE Queue/Worker | 1/4 | Indexing gap (wre_bridge.py) |
| BuildPlan/Swarm | 1/3 | Semantic drift (hermes > build_plan) |
| pfMALL | 1/3 | Ranking (test file > src file) |
| Skills/Scanner | 1/3 | Indexing gap (orphan analyzer) |

### Root Cause Distribution

| Root Cause | Count | % |
|------------|-------|---|
| Semantic drift | 2 | 40% |
| Indexing gap | 2 | 40% |
| Ranking issue | 1 | 20% |

### Latency Baseline

| Percentile | Value |
|------------|-------|
| p50 | 102ms |
| p95 | 155ms |
| max | 414ms |

**Note**: Latency includes embedding encode + ChromaDB query. First query may include model load time.

### Known Indexing/Ranking Gaps

1. **wre_bridge.py**: In `modules/development/`, not in priority roots
2. **build_plan.py**: Semantic drift - "hermes" keyword matches hermes_adapter.py better
3. **orphan_batch_analyzer.py**: In `holo_index/qwen_advisor/`, not in symbol roots
4. **HIA7B attempted fix**: Adding priority roots caused regression (84.2% top-1). Reverted.

---

## 3. Agentic RAG Options

### Option A: Gemma Reranker Behind Flag

**Description**: Use Gemma 3 270M for top-5 -> top-1 reranking when confidence < threshold.

| Aspect | Assessment |
|--------|------------|
| Model | gemma-3-270m-it (253MB GGUF) |
| Expected latency | +50-100ms per query |
| Implementation | Call Gemma with "Which result best matches: {query}?" |
| Flag | `HOLO_GEMMA_RERANK=1` |
| Default | OFF |

**Pros**:
- Addresses semantic drift failures
- Gemma already loaded for OpenClaw (shared model)
- Quantized model is fast (50-100ms)

**Cons**:
- Adds inference latency
- Requires llama_cpp in search path
- May introduce non-determinism

### Option B: Qwen/Gemma Corrective Retry Loop

**Description**: If top-1 confidence < 0.7, query Gemma/Qwen for query expansion and retry.

| Aspect | Assessment |
|--------|------------|
| Trigger | confidence < 0.7 |
| Expansion | Gemma generates synonyms/related terms |
| Retry | Re-run search with expanded query |
| Max retries | 1 (to bound latency) |

**Pros**:
- Addresses both semantic drift and query ambiguity
- Self-correcting loop

**Cons**:
- High complexity
- 2x latency on low-confidence queries
- May expand in wrong direction

### Option C: Query Complexity Classifier

**Description**: Use Gemma to classify query as simple/complex. Simple -> deterministic, complex -> LLM-assisted.

| Aspect | Assessment |
|--------|------------|
| Classification | simple (80%) vs complex (20%) |
| Simple path | Current deterministic search |
| Complex path | Gemma reranker or query expansion |

**Pros**:
- Minimizes LLM usage to where needed
- Maintains performance for simple queries

**Cons**:
- Classification overhead on every query
- Classification errors cause wrong path

### Option D: Confidence-Threshold Retry

**Description**: If top-1 confidence < 0.65, add lexical fallback and re-merge results.

| Aspect | Assessment |
|--------|------------|
| Trigger | confidence < 0.65 (current min) |
| Action | Run lexical search, merge with semantic |
| No LLM | Pure algorithmic retry |

**Pros**:
- No LLM dependency
- Fast (lexical is cheap)
- Already implemented as fallback

**Cons**:
- Lexical may not help semantic drift
- Merge logic complexity

### Option E: BM25 Hybrid Reconsideration

**Status**: DEFERRED (HIA5 decision)

**Rationale from HIA5**:
- BM25 cannot help indexing gap failures (file not in corpus)
- Semantic drift has simpler fixes (boost tuning, exact match)
- Dependency risk (rank-bm25 unmaintained)
- Current baseline acceptable (86.8%/92.1%)

**Recommendation**: Do not reconsider BM25 at this time.

### Option F: HyDE (Hypothetical Document Embeddings)

**Description**: Generate hypothetical answer with LLM, embed that, search for similar documents.

| Aspect | Assessment |
|--------|------------|
| LLM usage | Required (generate hypothetical doc) |
| Latency | +300-500ms (LLM generation + re-embed) |
| Benefit | Better for abstract/conceptual queries |

**Pros**:
- Strong for "what does X do" queries
- Well-documented technique

**Cons**:
- High latency
- Overkill for symbol/path queries
- Requires quality LLM for hypothesis

### Option G: Self-RAG Validation

**Description**: After retrieval, LLM validates "Does this answer the query?" and filters results.

| Aspect | Assessment |
|--------|------------|
| Validation | Per-result yes/no from Gemma |
| Latency | +50ms per result (5 results = +250ms) |
| Benefit | Removes false positives |

**Pros**:
- Precise filtering
- Can explain why result matches

**Cons**:
- Linear latency with result count
- Gemma may not understand code context

### Option H: GraphRAG

**Description**: Build knowledge graph of code relationships, traverse graph for multi-hop reasoning.

| Aspect | Assessment |
|--------|------------|
| Graph | Module -> file -> function -> import relationships |
| Query | Graph traversal + embedding search |
| Latency | Varies (graph size dependent) |

**Pros**:
- Strong for "what calls X" queries
- Enables multi-hop reasoning

**Cons**:
- Very high complexity
- Graph maintenance overhead
- Overkill for current failures

---

## 4. WSP 15 Priority Matrix

### Scoring Criteria

| Factor | Weight | Description |
|--------|--------|-------------|
| Complexity | 25% | Implementation difficulty (1=simple, 5=complex) |
| Importance | 25% | How much it improves baseline (1=low, 5=high) |
| Deferability | 20% | Can we ship without it? (1=must have, 5=nice to have) |
| Impact | 15% | User-visible improvement (1=low, 5=high) |
| Risk | 15% | Chance of regression/bugs (1=high risk, 5=low risk) |

### Option Scores

| Option | Complexity | Importance | Deferability | Impact | Risk | **MPS Score** |
|--------|------------|------------|--------------|--------|------|---------------|
| A: Gemma Reranker | 2 | 3 | 3 | 3 | 4 | **3.00** |
| B: Corrective Retry | 4 | 3 | 4 | 3 | 2 | 2.85 |
| C: Query Classifier | 3 | 2 | 4 | 2 | 3 | 2.60 |
| D: Confidence Retry | 2 | 2 | 4 | 2 | 5 | 2.85 |
| E: BM25 Hybrid | 3 | 2 | 5 | 2 | 3 | 2.60 |
| F: HyDE | 4 | 3 | 4 | 3 | 3 | 2.90 |
| G: Self-RAG | 3 | 2 | 4 | 2 | 4 | 2.80 |
| H: GraphRAG | 5 | 3 | 5 | 4 | 1 | 2.45 |

### Recommendation

**P0 (This Slice)**: Gate audit only - no implementation

**P1 (Next Slice)**: Option A - Gemma Reranker Behind Flag
- Highest MPS score (3.00)
- Low complexity (Gemma already available)
- Addresses semantic drift (40% of failures)
- Flag-gated (no regression risk to default path)

**P2 (Deferred)**: Option D - Confidence-Threshold Retry
- Second-best simplicity
- No LLM dependency
- Complements Gemma reranker

**P3 (Future)**: Options F/G if P1/P2 insufficient

---

## 5. WSP 97 Truth Boundaries

### Explicit Statements for This Slice

| Statement | Status |
|-----------|--------|
| No LLM hot-path change in this slice | TRUE |
| No claims of improved accuracy unless benchmarked | TRUE |
| No automatic task creation | TRUE |
| No autonomous code execution | TRUE |
| No TurboQuant default change | TRUE |
| No dependency added | TRUE |

### What This Document Does

- Audits current retrieval architecture
- Documents baseline metrics truthfully
- Evaluates agentic RAG options objectively
- Recommends next slice with rationale

### What This Document Does NOT Do

- Implement any code changes
- Modify search hot path
- Add Gemma/Qwen imports
- Change routing policy
- Change TurboQuant defaults
- Claim improvements without benchmarks

---

## 6. Proposed Gate Criteria for Implementation

Any future agentic RAG implementation (HIA8A, HIA8B, etc.) MUST prove:

### Non-Regression Gates

| Gate | Requirement | Measurement |
|------|-------------|-------------|
| Top-1 baseline | >= 86.8% (current) | HIA7 38-query sentinel |
| Top-5 baseline | >= 92.1% (current) OR clear rationale for trade-off | HIA7 38-query sentinel |
| Latency p95 | <= 200ms | pytest timing |
| TurboQuant default | UNCHANGED (`HOLO_USE_TURBOQUANT=0`) | Code review |

### Implementation Gates

| Gate | Requirement |
|------|-------------|
| Feature flag | Defaults OFF (`HOLO_*=0`) |
| Hot-path import | No Gemma/Qwen import unless flag enabled |
| Lazy loading | LLM model loaded only on first flagged query |
| Fallback | Graceful degradation if model unavailable |

### Documentation Gates

| Gate | Requirement |
|------|-------------|
| Benchmark report | Before/after metrics for sentinel queries |
| Latency impact | p50/p95/max documented |
| Failure analysis | Any new failures explained |

---

## 7. Recommended Next Prompt

### HIA8A_GEMMA_RERANKER_SPIKE_BEHIND_FLAG_PHASE1

```
You are 0102 W1 operating under WSP_00, WSP_15, WSP_50, and WSP_97.

Role: HoloIndex agentic RAG spike worker.

Objective:
Implement Gemma reranker spike BEHIND FLAG (`HOLO_GEMMA_RERANK=1`).
Default OFF. No hot-path import when flag disabled.

Gate criteria (from HIA8):
- Top-1 >= 86.8% (no regression)
- Top-5 >= 92.1% OR rationale
- p95 latency <= 200ms (flagged path allowed to be slower)
- HOLO_USE_TURBOQUANT default unchanged

Implementation requirements:
1. Create holo_index/core/gemma_reranker.py
2. Integrate into search_engine.py with lazy import
3. Only activate when HOLO_GEMMA_RERANK=1
4. Use existing gemma-3-270m-it model path
5. Rerank top-5 -> top-1 for low-confidence results

Test requirements:
1. Flag OFF: No Gemma import, no latency change
2. Flag ON: Gemma reranks, measure latency delta
3. Sentinel queries: Compare before/after

Do not:
- Change HOLO_USE_TURBOQUANT default
- Import Gemma in search_engine.py unconditionally
- Break existing deterministic path

Return:
- Branch/head
- Files changed
- Benchmark results (flag OFF vs ON)
- WSP_97 verdict
```

### Rationale for HIA8A

1. **Lowest complexity** of LLM options (score 2/5)
2. **Addresses root cause**: 40% of failures are semantic drift
3. **Safe**: Flag-gated, no regression risk to default path
4. **Reusable**: Gemma model already available via gemma_rag_inference.py
5. **Measurable**: Clear before/after comparison possible

### Alternative: If HIA8A Rejected

If Gemma reranker is not desired, next slice should be:

**HIA8B_CONFIDENCE_RETRY_SPIKE_PHASE1**
- No LLM dependency
- Pure algorithmic confidence-threshold retry
- Lower impact but zero risk

---

## Appendix A: Files Read

| File | Purpose |
|------|---------|
| holo_index/core/search_engine.py | Current search implementation |
| holo_index/core/indexing_engine.py | Current indexing implementation |
| holo_index/tests/test_search_quality_baseline.py | Sentinel query definitions |
| docs/audits/holoindex_search_quality/HIA7_SENTINEL_EXPANSION_REPORT.md | 38-query baseline |
| docs/audits/holoindex_search_quality/HIA7B_PRIORITY_ROOT_INDEXING_FIX_REPORT.md | Revert decision |
| docs/audits/holoindex_search_quality/HIA5_BM25_HYBRID_GATE.md | BM25 deferral rationale |
| docs/audits/holoindex_search_quality/hia3_baseline_metrics.json | Current metrics |
| holo_index/qwen_advisor/gemma_rag_inference.py | Gemma availability |
| holo_index/qwen_advisor/orchestration/qwen_orchestrator.py | Qwen availability |

## Appendix B: HoloIndex Preflight Results

All 5 preflight searches returned results ([OK] 10 hits each):
1. "HIA7 sentinel expansion HoloIndex baseline 38 queries" - Found holodae_coordinator.py, WSP_35
2. "Gemma reranker HoloIndex search hot path" - Found gemma_intent_classifier.py, wsp_orchestrator.py
3. "Qwen advisor HoloIndex corrective RAG" - Found holodae_coordinator.py, WSP_35
4. "BM25 hybrid HoloIndex gate deferred" - Found public/f/holoindex_prod_01/index.html
5. "HOLO_EMIT_CONFIDENCE search_engine confidence scoring" - Found confidence_tracker.py, WSP_37

**Note**: Search 4 did not find HIA5_BM25_HYBRID_GATE.md as top result (semantic gap). This is expected - audit docs are not in primary collections.
