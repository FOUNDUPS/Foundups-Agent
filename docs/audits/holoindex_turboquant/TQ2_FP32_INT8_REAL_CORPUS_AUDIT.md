# TQ2 — fp32 vs int8 Real-Corpus Retrieval Audit (Phase 1)

**Slice**: `TQ2_FP32_INT8_REAL_CORPUS_AUDIT_PHASE1`
**Branch**: `research/tq2-fp32-int8-real-corpus-audit`
**Tracking**: `origin/main @ f08a416ec`
**Audit date**: 2026-04-23
**Author**: Worker CV
**WSP Lock**: WSP 15 (prioritization) → WSP 97 (truth distinction / execution)

---

## Decision

**`HOLD_INT8`**

The HIA3 int8 TurboQuant ONNX backend **remains experimental and gated off**
(`HOLO_USE_TURBOQUANT=0` stays the production default;
`backend_quality="experimental"` and `quality_gate="not_default_ready"` stay
in place). Performance gains are confirmed on the real corpus, but a single
low-count collection (`navigation_vocabulary`, 30 docs) pushes overall
top-5 set-agreement below the 95% promotion gate.

| Gate | Threshold | Measured | Pass? |
|---|---|---|---|
| Overall top-1 agreement | ≥ 90.0% | **97.3%** | ✅ |
| Overall top-5 set agreement | ≥ 95.0% | **88.7%** | ❌ |
| All sentinel queries top-1 agree | all | 30/30 | ✅ |

**Blocker**: overall top-5 set-agreement 88.7% < 95.0%.

---

## Baseline Policy

This audit treats the live `sentence-transformers/all-MiniLM-L6-v2`
SentenceTransformer path as the **authoritative baseline** because it is the
embedder that built every row currently stored in the live ChromaDB
collections at `E:/HoloIndex/vectors/`. No corpus reindex was performed.
The int8 backend is evaluated query-side only — the exact behavior a
production flip of `HOLO_USE_TURBOQUANT=1` would produce.

TQ1 synthetic-benchmark artifacts are **not** used as load-bearing evidence;
they are archived in `TQ1_BASELINE_SNAPSHOT.md` in this directory for
provenance but do not gate this decision.

---

## Method

### Corpus

Live ChromaDB PersistentClient at `E:/HoloIndex/vectors/` (the path
`HoloIndex.__init__` resolves to via `ssd_path / "vectors"`). Collection
counts at audit time:

| Collection | Documents | Included? |
|---|---:|---|
| `navigation_code` | 296 | ✅ |
| `navigation_wsp` | 3,446 | ✅ |
| `navigation_tests` | 0 | skipped (empty) |
| `navigation_skills` | 59 | ✅ |
| `navigation_symbols` | 20,000 | ✅ |
| `navigation_vocabulary` | 30 | ✅ |
| **Total audited** | **23,831** | 5 collections |

### Query Set

30 real-corpus queries derived from the TQ1 set plus production usage
patterns (WSP IDs, module paths, symbol names, env vars, natural language).
See `holo_index/scripts/benchmarks/tq2_real_corpus_audit.py::TQ2_QUERIES`.

### Sentinel Set

Six queries where the fp32 top-1 is unambiguous and the production system
must not regress:

1. `WSP 97 truth distinction protocol`
2. `WSP 87 size limits for modules`
3. `AgentPermissionManager.request_permission`
4. `modules/ai_intelligence/agent_permissions`
5. `modules/platform_integration/youtube_auth`
6. `HOLO_USE_TURBOQUANT environment switch`

Run across all five audited collections → 30 sentinel observations.

### Backends Under Test

| Role | Backend | Source |
|---|---|---|
| Authoritative baseline (A) | `SentenceTransformer("all-MiniLM-L6-v2")` | `E:/HoloIndex/models/...` (HF cache) |
| Candidate (B) | `TurboQuantEmbedder` (HIA3) | `E:/HoloIndex/models/tq2_int8_staging/` |

The int8 staging directory is assembled at audit time by copying
`model_int8.onnx` from `E:/HoloIndex/models/tq1_onnx_int8/` alongside the
MiniLM tokenizer files pulled from the fp32 HuggingFace snapshot. This is a
read-only staging operation; no model was retrained or re-quantized.

### Measurement

For each `(collection, query)` pair:

1. Encode the query with fp32 → `v_A`.
2. Encode the query with int8 → `v_B`.
3. Query the same Chroma collection with `v_A` → `top_k_A` (k=10).
4. Query the same Chroma collection with `v_B` → `top_k_B` (k=10).
5. Compare:
   - top-1 agreement (id match),
   - top-5 set agreement (set-equality of first five ids),
   - Jaccard@{1,3,5,10},
   - Kendall tau over the intersection of top-10 ids,
   - per-encoder latency (p50 / p95).

All measurements are deterministic given the live Chroma state; the script
records the Chroma collection count alongside the metrics.

### Promotion Gate

| Criterion | Threshold |
|---|---|
| Overall top-1 agreement | ≥ 90.0% |
| Overall top-5 set agreement | ≥ 95.0% |
| All sentinel queries top-1 agree | all |

All three must pass → `PROMOTE_INT8`. Any fail → `HOLD_INT8`.

---

## Results

### Per-Collection Agreement

| Collection | Docs | Top-1 | Top-5 set | Jaccard@5 (mean / min) | Tau (mean / min) |
|---|---:|---:|---:|---:|---:|
| `navigation_code` | 296 | 100.0% | 100.0% | 1.000 / 1.000 | 1.000 / 1.000 |
| `navigation_wsp` | 3,446 | 100.0% | 100.0% | 1.000 / 1.000 | 1.000 / 1.000 |
| `navigation_skills` | 59 | 100.0% | 100.0% | 1.000 / 1.000 | 1.000 / 1.000 |
| `navigation_symbols` | 20,000 | 100.0% | 100.0% | 1.000 / 1.000 | 1.000 / 1.000 |
| `navigation_vocabulary` | 30 | **86.7%** | **43.3%** | 0.787 / 0.429 | 0.744 / 0.278 |
| **Overall (unweighted mean over collections)** | — | **97.3%** | **88.7%** | — | — |

All sentinels pass (30/30 agree).

### Divergences

All four divergent queries are in `navigation_vocabulary`:

| Query | fp32 top-1 | int8 top-1 |
|---|---|---|
| `sentence transformer model load timeout` | `vocab_1_28` | `vocab_1_10` |
| `embedding_backend search metadata` | `vocab_1_24` | `vocab_1_23` |
| `antifaFM broadcaster 24/7 headless launch` | `vocab_1_13` | `vocab_1_7` |
| `YouTube stream resolver livestream detection` | `vocab_1_13` | `vocab_1_4` |

Raw detail: `tq2_divergent_queries.json`.

### Latency (p50 / p95, ms)

| Stage | fp32 | int8 | int8 speedup |
|---|---:|---:|---:|
| Encode | 20.06 / 50.64 | 3.04 / 4.79 | **6.6x / 10.6x** |
| Chroma query | 1.94 / 2.56 | 1.63 / 1.97 | 1.2x / 1.3x |

Cold load:

| Backend | Seconds |
|---|---:|
| fp32 `SentenceTransformer` | 15.32 |
| int8 `TurboQuantEmbedder` | 1.15 |

→ ~13.3x faster cold start on this box.

---

## Interpretation

### What TQ2 confirms

- Int8 is **retrieval-equivalent** to fp32 on every production navigation
  collection: `code`, `wsp`, `skills`, `symbols`. Perfect top-1, top-5,
  Jaccard@k, and Kendall tau across 20k-document and 3.4k-document
  collections — this is a far stronger result than TQ1's synthetic
  76.7% top-1 agreement suggested.
- The large speedup stays — int8 encode is ~6.6x faster at p50 and cold
  load is ~13x faster. These are the numbers a production flip would
  deliver.
- All sentinels hold — "unambiguous" queries behave identically.

### What blocks promotion

- `navigation_vocabulary` (30 docs) shows top-1 86.7% and top-5 43.3%.
  Four queries reorder the first five hits. Absolute id-level "correctness"
  is ambiguous (no ground truth), but the collection is small enough that
  ANN rounding on int8 vectors is detectable.
- The gate is a **set-level** rule on top-5. The mean is taken
  unweighted across collections, so one 30-doc outlier drags a 23k-doc
  corpus below threshold. That is intentional: the gate protects any
  collection, not a weighted average.

### Root cause (qualitative)

`navigation_vocabulary` holds short vocabulary/glossary-style entries.
With only 30 documents, many entries cluster very tightly in embedding
space, so small int8 quantization perturbations are enough to swap
neighbors. The other collections have richer text and more separated
clusters, which absorbs the quantization noise.

This is consistent with TQ1's 3.65% mean cosine drift: drift is present,
but for most of the production corpus the drift is below the nearest-
neighbor decision boundary.

---

## Follow-Up Options (out of scope for this slice)

1. **Per-collection gate**. Promote int8 only for `navigation_code`,
   `navigation_wsp`, `navigation_skills`, `navigation_symbols`; keep
   vocabulary on fp32. Requires a backend-router, not just an env flag.
2. **Vocabulary reindex with int8**. If the corpus is re-embedded by int8,
   the query/doc encoders match and the comparison collapses. Reindex is
   cheap on 30 docs, but creates a multi-backend operational footprint.
3. **Static calibration / higher-precision quant**. int8 per-tensor →
   int8 per-channel or int16 activations can close most of the drift.
   Pure model-side work; no corpus change needed.
4. **Relax the gate**. Make the top-5 threshold corpus-weighted instead
   of unweighted. This would pass TQ2 today (23,801 / 23,831 docs live
   in collections with 100% agreement), but explicitly accepts that a
   small collection can regress. Needs sign-off from 012.

None of these are implemented in this slice.

---

## Artifacts

| File | Role |
|---|---|
| `tq2_metrics.json` | Full per-collection metrics, per-sentinel detail, latency, decision |
| `tq2_divergent_queries.json` | Queries where fp32 vs int8 disagreed at top-1 or top-5 |
| `TQ1_BASELINE_SNAPSHOT.md` | Provenance snapshot of TQ1 (archival only) |
| `holo_index/scripts/benchmarks/tq2_real_corpus_audit.py` | Reproducer |

---

## Reproduction

From the repository root:

```bash
PYTHONPATH=. PYTHONIOENCODING=utf-8 \
  python holo_index/scripts/benchmarks/tq2_real_corpus_audit.py
```

Prerequisites:
- Live Chroma DB at `E:/HoloIndex/vectors/` (the path `HoloIndex` uses).
- `E:/HoloIndex/models/tq1_onnx_int8/model_int8.onnx` on disk.
- `E:/HoloIndex/models/models--sentence-transformers--all-MiniLM-L6-v2/` HF
  snapshot on disk (used both as fp32 source and for int8 tokenizer staging).
- `sentence-transformers`, `chromadb`, `onnxruntime`, `transformers` in
  the active Python env.

The script is idempotent: it rewrites `tq2_metrics.json` and
`tq2_divergent_queries.json` on each run.

---

## WSP Compliance

- **WSP 97**: Real measurement against the authoritative production
  embedder; no synthetic-only evidence is load-bearing; prior claims that
  could not be re-verified (TQ1 synthetic numbers) are quarantined in
  `TQ1_BASELINE_SNAPSHOT.md` with explicit provenance.
- **WSP 15**: Prioritization — unblocking the HIA3 gate is higher
  priority than further optimization; real-corpus evidence is higher
  priority than synthetic expansion.
- **WSP 50**: Paths, collection names, and env vars verified against
  `holo_index/core/holo_index.py` before measurement.
- **WSP 22**: ModLog entry recorded alongside this artifact.

---

## Verdict Line

`decision: HOLD_INT8` — see `tq2_metrics.json` line `"decision"`.
