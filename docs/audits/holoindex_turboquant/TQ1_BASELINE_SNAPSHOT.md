# TQ1 Baseline Snapshot

**Slice**: `TQ2_FP32_INT8_REAL_CORPUS_AUDIT_PHASE1` (baseline-policy artifact)
**Snapshot date**: 2026-04-23
**Author**: Worker CV
**WSP**: 97 (truth distinction), 50 (pre-action verification), 22 (ModLog)

---

## Why This Document Exists

The TQ2 decision artifact cites "TQ1 synthetic-corpus benchmarks" as prior evidence
that motivated real-corpus gating. The TQ1 benchmark scripts and report landed on
`origin/main` via branch-hygiene cleanup commit `6dff05b49` (PR #427) at:

- `holo_index/scripts/benchmarks/tq1_baseline_bench.py`
- `holo_index/scripts/benchmarks/tq1_onnx_int8_bench.py`
- `holo_index/scripts/benchmarks/tq1_queries.py`
- `holo_index/scripts/benchmarks/tq1_retrieval_agreement.py`
- `holo_index/docs/TQ1_BENCHMARK_REPORT.md`

Per the TQ2 baseline policy, any claim cited as "TQ1 prior evidence" must have a
reachable snapshot on `origin/main` before it is load-bearing for a gate decision.
`#427` made the scripts reachable, but they are still **archival**: they remain
synthetic-corpus measurements and do not gate TQ2. This file freezes the TQ1
claims that TQ2 references so the decision artifact is self-contained and does
not drift if TQ1 scripts are later modified.

---

## TQ1 Provenance

| Field | Value |
|---|---|
| Source branches | `research/tq1-turboquant-benchmark` (local), `bf7c18069` (pre-#427) |
| Merge commit on `main` | `6dff05b49` (PR #427, 2026-04-23) |
| Benchmark script | `holo_index/scripts/benchmarks/tq1_onnx_int8_bench.py` |
| Agreement harness | `holo_index/scripts/benchmarks/tq1_retrieval_agreement.py` |
| Query set | `holo_index/scripts/benchmarks/tq1_queries.py` (30 queries) |
| Original report | `holo_index/docs/TQ1_BENCHMARK_REPORT.md` (reachable on main) |
| Model artifact | `E:/HoloIndex/models/tq1_onnx_int8/model_int8.onnx` (local only) |
| fp32 reference | `sentence-transformers/all-MiniLM-L6-v2` (HF cache, 384-dim) |

The scripts and report are reachable from `origin/main` as of `6dff05b49`.
Model binary stays off-repo by design (see `.gitignore` `holo_index/models/`).
Treat the TQ1 numbers themselves as **archival** — synthetic evidence,
superseded by TQ2 real-corpus measurements for gate purposes.

---

## TQ1 Claims (Frozen, Not Re-Verified Here)

The following numbers are cited verbatim from the TQ1 research artifacts.
They are recorded here to make the TQ2 decision artifact self-contained;
this document does **not** re-run TQ1.

### Performance (synthetic, small-N)

| Metric | fp32 (SentenceTransformer) | int8 (TurboQuant ONNX) | Ratio |
|---|---|---|---|
| Cold start load | baseline | ~5.6x faster | 5.6x |
| Model load wall | baseline | ~6.6x faster | 6.6x |
| Single-query encode (median) | baseline | ~8.8x faster | 8.8x |
| Model artifact size | baseline | ~4.0x smaller | 4.0x |

### Quality (synthetic, small-N)

| Metric | Value | Threshold | Verdict |
|---|---|---|---|
| Mean cosine drift vs fp32 | 3.65% | 2% same-model threshold | **FAIL** |
| Synthetic top-1 retrieval agreement | 76.7% | N/A (no explicit gate) | flagged |
| Implied top-1 flip rate | ~23% | N/A | flagged |

### Derived Status (HIA3)

Based on the TQ1 quality numbers, HIA3 wired the int8 backend with:

```python
BACKEND_QUALITY = "experimental"
QUALITY_GATE    = "not_default_ready"
```

and kept `HOLO_USE_TURBOQUANT=0` as the production default. No callsite
outside the backend seam depends on TQ1 numbers being exact.

---

## What TQ1 Could Not Prove

TQ1 was a **synthetic, embedding-only** benchmark. It measured:

1. Embedder-vs-embedder cosine similarity on arbitrary text.
2. Top-k agreement of one embedder against itself via a synthetic document
   pool assembled at benchmark time.

It did **not** touch the live ChromaDB collections (`navigation_code`,
`navigation_wsp`, `navigation_tests`, `navigation_skills`,
`navigation_symbols`, `navigation_vocabulary`). It therefore did not measure
what HoloIndex production users actually experience, which is:

> Query encoded by embedder E, matched against a corpus indexed by the
> fp32 reference embedder, through ChromaDB's approximate-nearest-neighbor
> layer.

That is the measurement TQ2 performs. TQ1's role is strictly prior:
"there is drift, investigate before flipping the default."

---

## Relationship to TQ2

| Question | TQ1 answer | TQ2 answer |
|---|---|---|
| Is int8 faster? | Yes (synthetic) | Yes (real corpus, see TQ2 latency table) |
| Does int8 drift from fp32 on arbitrary text? | Yes, 3.65% | Out of scope (not re-measured) |
| Does int8 retrieve the same docs from real collections? | Unknown | **Measured, see TQ2 report** |
| Is int8 safe as the default backend? | No | **Gated, see TQ2 decision** |

---

## References

- `holo_index/core/turboquant_backend.py` — HIA3 backend (merged)
- `docs/audits/holoindex_turboquant/TQ2_FP32_INT8_REAL_CORPUS_AUDIT.md` — TQ2 decision
- `docs/audits/holoindex_turboquant/tq2_metrics.json` — TQ2 raw metrics
- `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md`
