# TQ3 — Per-Collection Backend Routing (Phase 1)

**Slice**: `TQ3_PER_COLLECTION_BACKEND_ROUTING_PHASE1`
**Date**: 2026-04-23
**Worker**: CX
**Decision**: `HOLD_ROUTING` (infrastructure shipped; policy-promotion deferred pending stable-corpus re-audit)

---

## Context

TQ2 (`TQ2_FP32_INT8_REAL_CORPUS_AUDIT.md`, decision `HOLD_INT8`) measured that
the HIA3 TurboQuant ONNX int8 backend was retrieval-equivalent to fp32 on
every production navigation collection **except** `navigation_vocabulary`
(30 docs; top-5 set-agreement 43.3%). Rather than promote int8 globally
(vocabulary would regress) or hold it off entirely (code / WSP / skills /
symbols had measured 100% top-1 and 100% top-5 over 23,801 docs), TQ3
introduces **per-collection routing**: int8 where TQ2 proved equivalence,
fp32 where it did not.

TQ3 ships the routing surface:

* `holo_index/core/backend_routing.py` — policy module with the canonical
  collection → backend map.
* `holo_index/core/holo_index.py` — loads both backends when
  `HOLO_USE_TURBOQUANT=1`, exposes `routing_active`, `embedders`, and
  `collection_backend_map`.
* `holo_index/core/search_engine.py` — resolves the routed embedder per
  collection on every search and emits `routing_active` +
  `collection_backend_map` on the response metadata.
* `holo_index/scripts/benchmarks/tq3_routed_corpus_audit.py` — a TQ2
  overlay that audits the routed policy vs the pure-fp32 baseline.

## Policy Map (TQ3 Target)

| Collection             | Routed backend             | Evidence source        |
| ---------------------- | -------------------------- | ---------------------- |
| `navigation_code`      | `turboquant_onnx_int8`     | TQ2 (evidence drifted) |
| `navigation_wsp`       | `turboquant_onnx_int8`     | TQ2 (evidence drifted) |
| `navigation_skills`    | `turboquant_onnx_int8`     | TQ2 + TQ3 both 100%    |
| `navigation_symbols`   | `turboquant_onnx_int8`     | TQ2 + TQ3 both 100%    |
| `navigation_vocabulary`| `sentence_transformers`    | TQ2 blocker; TQ3 trivial 100% |
| `navigation_tests`     | *(unlisted → fp32 default)*| TQ2 could not audit (empty) |
| *any other*            | *(default → fp32)*         | Safe baseline          |

The map is **declared now** so the routing surface is testable and stable,
but `HOLD_ROUTING` means no default flips from this slice. Production
default remains `HOLO_USE_TURBOQUANT=0` (pure fp32). Promotion requires a
clean re-audit pass (see Blockers).

## Gate Result (TQ3 run, 2026-04-23)

Thresholds (identical to TQ2 for direct comparability):

* overall top-1 agreement ≥ 90%
* overall top-5 set-agreement ≥ 95%
* all sentinel queries: top-1 agrees with fp32

Routed-mode result:

| Metric                          | Value  | Gate   | Status |
| ------------------------------- | ------ | ------ | ------ |
| overall top-1 agreement         | 95.3%  | ≥ 90%  | PASS   |
| overall top-5 set-agreement     | 72.7%  | ≥ 95%  | **FAIL** |
| sentinels passing               | 5 / 6  | 6 / 6  | **FAIL** |

**Decision**: `HOLD_ROUTING`.

### Per-Collection (Routed vs Pure fp32)

| Collection             | Docs (now) | Routed backend | top-1  | top-5  | Notes |
| ---------------------- | ---------- | -------------- | ------ | ------ | ----- |
| `navigation_code`      | 296        | int8           | 86.7%  | 46.7%  | Regressed vs TQ2 (was 100% / 100%) |
| `navigation_wsp`       | 1,916      | int8           | 90.0%  | 16.7%  | Regressed vs TQ2 (was 100% / 100%) |
| `navigation_skills`    | 59         | int8           | 100.0% | 100.0% | Stable vs TQ2 |
| `navigation_symbols`   | 20,000     | int8           | 100.0% | 100.0% | Stable vs TQ2 |
| `navigation_vocabulary`| 30         | fp32           | 100.0% | 100.0% | Trivial (same backend) |

### Failing Sentinel

* `navigation_wsp` / `WSP 97 truth distinction protocol` → fp32 top-1
  `wsp_201`, routed (int8) top-1 `wsp_108`.

### Divergences (7 total)

| Collection         | Backend | Query                                       |
| ------------------ | ------- | ------------------------------------------- |
| `navigation_code`  | int8    | `pfMALL data isolation model`               |
| `navigation_code`  | int8    | `ai overseer role detection`                |
| `navigation_code`  | int8    | `embedding_backend search metadata`         |
| `navigation_code`  | int8    | `token budget for DAE pattern memory`       |
| `navigation_wsp`   | int8    | `WSP 97 truth distinction protocol`         |
| `navigation_wsp`   | int8    | `how does 0102 recall patterns from 0201`   |
| `navigation_wsp`   | int8    | `token budget for DAE pattern memory`       |

Full list: `docs/audits/holoindex_turboquant/tq3_divergent_queries.json`.

## Root-Cause Finding (WSP 97)

**Corpus drift between TQ2 and TQ3 runs.** TQ2 audited `navigation_wsp` at
3,446 docs; TQ3 saw 1,916 docs in the same Chroma at `E:/HoloIndex/vectors`.
`navigation_code` was stable at 296 but its 5-NN neighborhoods still
diverged under int8 more than before, consistent with an underlying
re-index that also affected code chunk boundaries or payload text.

This does not invalidate the routing **infrastructure** — the routed-mode
audit correctly used int8 for code/wsp/skills/symbols and fp32 for
vocabulary. It invalidates the claim that TQ2's equivalence result still
holds for code/wsp on the present corpus state. Skills and symbols remain
stable; vocabulary is trivially correct under routing.

## Latency (TQ3 Run)

Routed-mode encode is dominated by int8 (4 of 5 collections) and shows
the expected improvement over pure fp32:

| Metric              | Routed  | Pure fp32 |
| ------------------- | ------- | --------- |
| encode p50 (ms)     | 2.73    | 10.94     |
| encode p95 (ms)     | 11.40   | 19.91     |
| query p50 (ms)      | 1.69    | 2.05      |
| query p95 (ms)      | 2.29    | 2.64      |
| cold load fp32 (s)  | —       | 11.64     |
| cold load int8 (s)  | 0.76    | —         |

Latency is not a blocker; the blocker is retrieval equivalence on the
current corpus.

## Blockers (Must Clear Before Default-Promotion)

1. Re-establish a stable corpus (freeze `E:/HoloIndex/vectors` or rebuild
   from deterministic source) before any further TQ re-run. Corpus drift
   between slices makes A/B evidence non-reproducible.
2. On the frozen corpus, re-run TQ2 (pure-int8 vs fp32) and confirm the
   code/wsp collections still meet 100% / 100%. If they regress, the
   int8 lane must shrink to only the collections that pass.
3. Re-run TQ3 (routed vs fp32) and confirm overall ≥ 90% top-1, ≥ 95%
   top-5, all sentinels pass.

## What TQ3 Ships Today

* Routing policy module (`backend_routing.py`) — testable, WSP-50 clean.
* HoloIndex boot loads **both** backends when `HOLO_USE_TURBOQUANT=1`;
  `routing_active` is `True` only when both load cleanly (no silent
  degradation).
* `search_engine.execute_search()` metadata now surfaces:
  - `routing_active: bool`
  - `collection_backend_map: {collection: backend}`
  - `embedding_backend = "routed"` when routing is active (WSP 97 — no
    single-backend overclaim when behavior is mixed).
* `backend_quality` / `quality_gate` extended with `"routed" → "mixed"`
  entries.
* 14 new focused unit tests (`test_backend_routing.py`) covering the
  policy map, the resolver, and degraded-load fallbacks.
* TQ3 audit harness reusing TQ2's frozen query set + sentinels so runs
  are directly comparable.

## What TQ3 Does NOT Change

* Production default remains `HOLO_USE_TURBOQUANT=0` → pure fp32.
* No reindex. Chroma still stores fp32-built vectors. Routing only
  changes the **query** embedder, not the stored vectors.
* `backend_quality="experimental"` and `quality_gate="not_default_ready"`
  claims for `turboquant_onnx_int8` stand. The new `"routed"` entry
  claims `"mixed"` / `"mixed"` — deliberately not `default_ready`.

## Files

* `holo_index/core/backend_routing.py` (new)
* `holo_index/core/holo_index.py` (modified)
* `holo_index/core/search_engine.py` (modified)
* `holo_index/tests/test_backend_routing.py` (new)
* `holo_index/scripts/benchmarks/tq3_routed_corpus_audit.py` (new)
* `docs/audits/holoindex_turboquant/tq3_metrics.json`
* `docs/audits/holoindex_turboquant/tq3_divergent_queries.json`
* `docs/audits/holoindex_turboquant/TQ3_PER_COLLECTION_ROUTING.md` (this file)

## WSP Compliance

* **WSP 15** (priority): Routing is P1-supporting — unblocks safe
  per-collection int8 use once corpus stability returns.
* **WSP 97** (truth distinction): Metadata surfaces the mixed nature of
  routed retrieval (`embedding_backend="routed"`, per-collection map).
  The decision `HOLD_ROUTING` reflects measurement, not intent.
* **WSP 50** (pre-action verification): HoloIndex searched before file
  creation; all 7 read-first files consulted before design.
