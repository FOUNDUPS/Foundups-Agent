# HIA_AGENTIC_RAG_RANKING_QUALITY_PHASE6

**Date**: 2026-05-06
**Slice**: HIA_AGENTIC_RAG_RANKING_QUALITY_PHASE6
**Status**: COMPLETE - AUDIT ONLY
**Author**: 0102 W1
**Base**: main @ `961a17c7b` (PR #507 merged)

---

## Purpose

Measure remaining HoloIndex ranking quality after Phases 1-5 (baseline gate,
collection health, sentinel sufficiency, docs/knowledge recall, WSP_97 alias
recall). Identify whether deterministic fixes remain or Gemma reranking is
needed.

---

## Aggregate Metrics

### Before Index Refresh (Phase 6 Audit)

| Metric | Value |
|--------|-------|
| Total sentinels tested | 27 |
| Found (any position) | 25/27 (93%) |
| Top-1 | 23/27 (85%) |
| Top-5 | 25/27 (93%) |
| Failures | 2 (7%) |
| Test-over-source inversions | 0 |

### After Index Refresh (Phase 7)

| Metric | Value |
|--------|-------|
| Total sentinels tested | 27 |
| Found (any position) | **27/27 (100%)** |
| Top-1 | **25/27 (93%)** |
| Top-5 | **27/27 (100%)** |
| Failures | **0 (0%)** |
| Test-over-source inversions | 0 |

**Reindex command**: `python holo_index.py --index-symbols --ssd E:/HoloIndex`

**Root cause**: `--index-code` only indexes NAVIGATION.py entries into `navigation_code`.
The two files (`agentic_rag_verdict.py`, `collection_health.py`) live in `holo_index/core/`
which is indexed via the **symbol index** (`navigation_symbols`), not the code collection.
The symbol index was stale (20K entries, all from `modules/`). Re-running `--index-symbols`
reprioritized `holo_index/core` as P1, indexing 186 symbols including both target files.

---

## Position Distribution

### Before Index Refresh

```
pos-1:  23  #######################
pos-2:   2  ##
NOT FOUND: 2  XX
```

### After Index Refresh

```
pos-1:  25  #########################
pos-2:   2  ##
NOT FOUND: 0
```

93% of sentinels land at TOP-1. No results beyond position 2. Zero failures.

---

## Test Suite Results (All Green)

| Suite | Passed |
|-------|--------|
| test_agentic_rag_sentinel_sufficiency.py | 11 |
| test_agentic_rag_docs_knowledge_recall.py | 8 |
| test_agentic_rag_wsp97_alias_recall.py | 14 |
| test_search_quality_baseline.py | 10 |
| test_collection_health.py | 18 |
| test_backend_routing.py | 19 |
| **Total** | **80** |

---

## Sentinel Results (Full Table)

### Phase 4: Docs/Knowledge Recall (6/6 PASS)

| Query | Expected | Bucket | Position | Verdict |
|-------|----------|--------|----------|---------|
| WSP 97 System Execution Prompting Protocol | WSP_97 | wsps | 1 | PASS |
| rESP quantum entanglement theoretical foundation WSP 61 | WSP_61 | wsps | 1 | PASS |
| FOUNDUPS BTC reserve token architecture | BTC_RESERVE_TOKEN | docs | 1 | PASS |
| HIA Agentic RAG live collection health audit | HIA_AGENTIC_RAG_LIVE_COLLECTION_HEALTH | docs | 1 | PASS |
| HoloIndex degraded mode WSP doc retrieval audit | DEGRADED_MODE_WSP_DOC_RETRIEVAL | docs | 1 | PASS |
| rESP quantum entanglement cross linguistic signatures | rESP_Cross_Linguistic_Quantum | knowledge | 1 | PASS |

### Phase 5: WSP_97 Alias Recall (4/4 PASS)

| Query | Expected | Bucket | Position | Verdict |
|-------|----------|--------|----------|---------|
| retrieve evidence before stating facts | WSP_97 | wsps | 1 | PASS |
| function agentically apply CoT CoR | WSP_97 | wsps | 1 | PASS |
| hard think dialectic sweep first principles | WSP_97 | wsps | 1 | PASS |
| agentic activation protocol execution | WSP_97 | wsps | 1 | PASS |

### Phase 6: Cross-Domain Probes (13/13 PASS)

| Query | Expected | Bucket | Position | Verdict |
|-------|----------|--------|----------|---------|
| CABR validation engine | cabr_hooks | code | 2 | PASS |
| CABR validation engine | WSP_29 | wsps | 1 | PASS |
| hermes foundup job executor | hermes | code | 1 | PASS |
| backend routing turboquant | backend_routing | code | 1 | PASS |
| backend routing turboquant | turboquant_backend | code | 2 | PASS |
| WSP 50 pre action verification | WSP_50 | wsps | 1 | PASS |
| agent permission manager | agent_permission_manager | code | 1 | PASS |
| WRE master orchestrator | wre_master_orchestrator | code | 1 | PASS |
| pattern memory sqlite storage | pattern_memory | code | 1 | PASS |
| libido monitor gemma | libido_monitor | code | 1 | PASS |
| foundup genesis validator | foundup_genesis | code | 1 | PASS |
| WSP 22 modlog updates | WSP_22 | wsps | 1 | PASS |
| WSP 77 agent coordination | WSP_77 | wsps | 1 | PASS |
| build plan swarm orchestration | build_plan | code | 1 | PASS |

### Phase 6: Source-vs-Test Probes (3/3 PASS after Phase 7 refresh)

| Query | Expected | Bucket | Before Refresh | After Refresh | Verdict |
|-------|----------|--------|----------------|---------------|---------|
| search engine keyword scoring | search_engine.py | code | 1 | 1 | PASS |
| agentic rag verdict classification | agentic_rag_verdict | code | NOT FOUND | **1** | **PASS (repaired)** |
| collection health inspection | collection_health | code | NOT FOUND | **1** | **PASS (repaired)** |

---

## Failure Classification (Pre-Refresh)

### Failure 1: `agentic_rag_verdict.py` (REPAIRED in Phase 7)

| Field | Before Refresh | After Refresh |
|-------|----------------|---------------|
| Query | "agentic rag verdict classification" | same |
| Expected | `agentic_rag_verdict` in code bucket | same |
| Got top-1 | `modules/foundups/kosei/src/contracts.py` | **`holo_index/core/agentic_rag_verdict.py`** |
| In symbol index | NO | **YES (7 symbols)** |
| Classification | INDEXING GAP | **REPAIRED** |

### Failure 2: `collection_health.py` (REPAIRED in Phase 7)

| Field | Before Refresh | After Refresh |
|-------|----------------|---------------|
| Query | "collection health inspection" | same |
| Expected | `collection_health` in code bucket | same |
| Got top-1 | `health_reporter.py` | **`holo_index/core/collection_health.py`** |
| In symbol index | NO | **YES (9 symbols)** |
| Classification | INDEXING GAP | **REPAIRED** |

### Root Cause

Both files live in `holo_index/core/` which is indexed via the **symbol index**
(`navigation_symbols`), not the code collection (`navigation_code`). The code
collection only indexes NAVIGATION.py entries (296 entries). The symbol index
was stale — all 20,000 slots consumed by `modules/` before `holo_index/core`
(P1 priority root) was reached.

### Fix Applied (Phase 7)

```bash
python holo_index.py --index-symbols --ssd E:/HoloIndex
```

Re-running `--index-symbols` rebuilt the symbol index with correct P1 priority
ordering. `holo_index/core` (186 symbols) was indexed first, then `modules/`
filled the remaining ~19,814 slots.

Note: `--index-code` alone does NOT fix this — it only refreshes NAVIGATION.py
entries. The symbol index requires `--index-symbols` explicitly.

---

## Failure Classification Summary (Post-Refresh)

| Classification | Count | Examples |
|---------------|-------|---------|
| Indexing gap | 0 | (both repaired) |
| Invalid sentinel | 0 | - |
| Source-over-test | 0 | - |
| Semantic drift | 0 | - |
| Alias gap | 0 | (fixed in Phase 5) |
| Missing file | 0 | - |
| Requires Gemma reranking | 0 | - |

---

## Source-vs-Test Ranking Quality

All 7 source-vs-test probes correctly rank source files above tests:

| Query | Top-1 File | Type |
|-------|-----------|------|
| search engine keyword scoring | search_engine.py | SRC |
| backend routing turboquant | backend_routing.py | SRC |
| agent permission manager | agent_permission_manager.py | SRC |
| WRE master orchestrator | wre_master_orchestrator.py | SRC |
| pattern memory sqlite storage | pattern_memory.py | SRC |
| cabr hooks validation | cabr_hooks.py | SRC |
| hermes foundup job executor | hermes_job_executor.py | SRC |

No test-over-source inversions detected.

---

## Deterministic Fixes Still Available

### 1. Code Index Refresh (Fixes Both Failures)

```bash
python holo_index.py --index-code --ssd E:/HoloIndex
```

Expected outcome: Both `agentic_rag_verdict.py` and `collection_health.py`
become discoverable. Projected pass rate: 27/27 (100%).

### 2. WSP Alias Registry Expansion (Future)

The alias registry currently covers only WSP 97. High-value expansion targets:

| WSP | Candidate Aliases |
|-----|------------------|
| WSP 50 | "verify before edit", "search before read" |
| WSP 87 | "keep files under size limit", "block independence" |
| WSP 22 | "update modlog", "document changes" |
| WSP 77 | "coordinate agents", "qwen gemma coordination" |

These are NOT failures — all explicit WSP queries (e.g., "WSP 50 pre action
verification") already return the correct WSP at TOP-1. Alias expansion would
add natural-language recall for operational phrases, as was done for WSP 97.

### 3. Priority Root Expansion

Not needed. Current priority roots produce correct source-over-test ranking
for all tested queries.

### 4. Sentinel Correction

No invalid sentinels found. All 27 sentinels target real files with
well-scoped queries.

---

## Gemma Reranking Assessment

### Is Gemma Reranking Justified?

**NO.** There are zero failures that require LLM reranking.

| Criterion | Finding |
|-----------|---------|
| Failures requiring semantic understanding | 0 |
| Ranking inversions (wrong doc outranks right doc) | 0 |
| Source-vs-test inversions | 0 |
| Natural-language recall gaps | 0 (fixed by alias registry) |
| Remaining failures | 0 (both repaired by symbol index refresh) |

### When Would Gemma Reranking Be Justified?

Gemma reranking would be justified if:

1. **Semantic drift failures** emerge — queries where the right doc exists
   in the candidate pool but ranks below an irrelevant doc due to embedding
   similarity misjudgment. (Not observed.)

2. **Cross-bucket confusion** — a query retrieves the right content but in
   the wrong bucket (e.g., WSP content in docs bucket). (Not observed.)

3. **Alias registry saturation** — so many WSPs need natural-language
   aliases that maintaining the registry becomes impractical. (Currently
   only 1 WSP has aliases; registry approach scales to 20+ before
   maintenance cost becomes material.)

### Recommendation

Defer Gemma reranking. After the Phase 7 symbol index refresh, ranking quality
is 100% recall (27/27) and 93% top-1 (25/27). All failures were indexing gaps,
now repaired. No semantic ranking problem exists that would benefit from LLM
reranking.

---

## WSP 97 Truth Boundaries

| Statement | Status |
|-----------|--------|
| Audit measured ranking quality, not just pass/fail | TRUE |
| Both failures are classified with root cause | TRUE |
| No ranking improvements were guessed without evidence | TRUE |
| Gemma reranking recommendation is evidence-based | TRUE |
| No code changes in this slice | TRUE |
| No TurboQuant changes | TRUE |
| No ChromaDB artifacts committed | TRUE |

---

## Files Added

| File | Purpose |
|------|---------|
| `docs/audits/holoindex_search_quality/HIA_AGENTIC_RAG_RANKING_QUALITY_PHASE6.md` | This audit |

---

## Phase 7: Index Refresh Results (2026-05-06)

### Command

```bash
python holo_index.py --index-symbols --ssd E:/HoloIndex
```

Note: `--index-code` only refreshes NAVIGATION.py entries (navigation_code).
The two target files are in `holo_index/core/` which is served by the
**symbol index** (navigation_symbols). `--index-symbols` was required.

### Before/After

| File | Before Refresh | After Refresh |
|------|----------------|---------------|
| agentic_rag_verdict.py | NOT in symbol index | **7 symbols indexed, TOP-1** |
| collection_health.py | NOT in symbol index | **9 symbols indexed, TOP-1** |
| Symbol collection total | 20,000 (all modules/) | 20,000 (186 holo_index/core + modules/) |

### Final Pass Rate

| Metric | Phase 6 (pre) | Phase 7 (post) |
|--------|---------------|----------------|
| Recall | 25/27 (93%) | **27/27 (100%)** |
| Top-1 | 23/27 (85%) | **25/27 (93%)** |
| Failures | 2 | **0** |

---

## HIA Agentic RAG Pipeline Status

| Phase | Status |
|-------|--------|
| Phase 1: Baseline gate | DONE (PR #503) |
| Phase 2: Collection health | DONE (PR #504) |
| Phase 3: Sentinel sufficiency | DONE (PR #505) |
| Phase 4/4B: Docs/knowledge recall | DONE (PR #506) |
| Phase 5: WSP_97 alias recall | DONE (PR #507) |
| Phase 6: Ranking quality audit | DONE (this slice) |
| Phase 7: Index refresh | DONE (this slice) |

**Pipeline verdict: COMPLETE.** 27/27 sentinels pass, 93% TOP-1, zero
failures, Gemma reranking not justified.

### Long-term: WSP Alias Registry Expansion

Expand `_WSP_ALIAS_REGISTRY` to cover operational phrases for
WSP 50, WSP 87, WSP 22, WSP 77 as usage patterns emerge.
Not blocking — all explicit WSP queries already work.
