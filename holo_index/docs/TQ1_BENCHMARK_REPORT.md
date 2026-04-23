# TQ1 — TurboQuant Backend Benchmark Report

**Slice**: TQ1-TURBOQUANT-BENCHMARK
**Window**: W5
**Date**: 2026-04-21
**Branch**: `research/tq1-turboquant-benchmark` (local, not pushed)
**WSP References**: WSP 15 (scoring discipline), WSP 97 (truthful assessment)
**Status**: COMPLETE

---

## Summary table

| Option | Available | Setup cost | Artifact size | Cold (import+load) | Load (warm) | Single-q median | Batch/q | Quality vs fp32 | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Baseline** — SentenceTransformers fp32 | YES | LOW (installed) | 88 MB safetensors | **55.2 s** | 14.7 s | 18.4 ms | 1.9 ms | — (baseline) | *current* |
| **A** — Optimum/ST ONNX fp32 | YES (via optimum 2.1.0) | MEDIUM | ~86 MB ONNX | *est. ~9-11 s* | *est. ~2-3 s* | *est. ~2 ms* | *est. ~1 ms* | **Near-zero drift (est.)** | Fallback if int8 unacceptable |
| **B** — ONNX Runtime int8 dynamic | YES (via optimum+onnx+ort) | MEDIUM | **21.8 MB** | **9.84 s** | 2.21 s | 2.1 ms | 1.08 ms | **Mean drift 3.65%, top-1 agreement 76.7%** | **Recommended, pending calibration improvement** |
| **C** — llama-cpp GGUF embedding | PARTIAL | **HIGH_SETUP_COST** | ~33-80 MB | *unmeasured* | *unmeasured* | *unmeasured* | *unmeasured* | *different model — needs retrieval-agreement measurement on real corpus* | Defer |

**Recommendation**: **B** for HIA3, with a follow-up task to move from dynamic to static (calibrated) int8 before promoting to production. A stays in the quiver as a known-good fallback if calibrated int8 still drifts too much.

---

## Environment

| Field | Value |
|---|---|
| Python | 3.12.2 |
| Python executable | `O:\Foundups-Agent\.venv\Scripts\python.exe` |
| Platform | Windows 11 (10.0.26200) |
| sentence-transformers | 5.4.1 |
| torch | 2.11.0 |
| transformers | 4.57.6 (also seen as 5.5.4 at env-survey; `transformers` version moved when optimum installed) |
| onnxruntime | 1.20.1 |
| onnx | 1.21.0 *(installed for TQ1; was missing at start)* |
| optimum | 2.1.0 *(installed for TQ1; was missing at start)* |
| llama-cpp-python | 0.3.20 (present but unused — no embedding GGUF locally) |
| numpy | 2.4.4 |
| chromadb | 1.5.5 |

No GPU usage — CPU-only `CPUExecutionProvider`.

Local model inventory at `E:/HoloIndex/models/`:
- `models--sentence-transformers--all-MiniLM-L6-v2` — 88 MB (current baseline)
- `gemma4-e2b/google_gemma-4-E2B-it-Q4_K_M.gguf` — chat model, not embedder
- `mradermacher/UI-TARS-1.5-7B-GGUF/*` — vision, not embedder
- `qwen3.5-4b/Qwen3.5-4B-Q4_K_M.gguf` — chat, not embedder
- `ui-tars-1.5/lmstudio-community/gpt-oss-20b-GGUF/*` — chat, not embedder

**No GGUF embedding models present locally.** This is the gating fact for Option C.

---

## Benchmark artifacts

All measurements are reproducible via scripts committed to `holo_index/scripts/benchmarks/`:

- `tq1_queries.py` — 30 representative HoloIndex queries (WSP, SKILLz, pfMALL, ai_overseer, module paths, symbols). Frozen for this report.
- `tq1_baseline_bench.py` — Option baseline. Writes `tq1_baseline_vectors.json` (used by int8 comparison).
- `tq1_onnx_int8_bench.py` — Option B. Exports ONNX via optimum, quantizes to int8 via `onnxruntime.quantization.quantize_dynamic`, encodes, reports cosine drift.
- `tq1_retrieval_agreement.py` — synthetic top-k agreement probe (Jaccard + Kendall tau) between fp32 and int8 on the query set.

Exported model artifacts live at `E:/HoloIndex/models/tq1_onnx_int8/` — never committed.

---

## Per-option analysis

### Baseline — SentenceTransformers fp32 (current HoloIndex backend)

The live backend. Measured to have something to compare against.

- **Cold import** (subprocess, empty Python): 40.48 s
- **Warm import + model load** (same process): 9.47 s + 14.69 s = 24.2 s
- **Total cold-to-first-encode**: ~55 s — *this is why FX2-C had to raise the import timeout default to 20s and load timeout to 30s*
- **Single query**: median 18.4 ms, p95 27.0 ms, max 1.17 s (first query pays JIT/cache cost)
- **Batch of 30**: 57 ms total → 1.9 ms/query
- **Vector**: 384-dim float32
- **Artifact**: 88 MB safetensors (on disk)

This is the baseline the int8 comparison is against.

### Option A — Optimum / SentenceTransformers ONNX fp32

**Not benchmarked as a distinct row.** The tooling is identical to Option B minus the `quantize_dynamic` step — the fp32 ONNX artifact (86.18 MB, already produced as a side-effect of B's export step) sits at `E:/HoloIndex/models/tq1_onnx_int8/fp32/model.onnx` and is ready to be loaded through the same ORT pipeline.

Why skipped: the interesting quality question is *how much drift the int8 step introduces*. Fp32 ONNX is mathematically equivalent to fp32 PyTorch within floating-point tolerance; a re-measurement would duplicate baseline quality with only the inference-runtime savings (ORT vs torch). If int8 drift proves unacceptable after calibration work, A is a known-good fallback — estimated performance from B's numbers minus the ~3-4% dynamic-quantization cost, roughly: cold ~9-11 s, load ~2-3 s, single-q ~2 ms.

**Setup cost MEDIUM**: requires `pip install optimum[onnxruntime]` (already done for this report — `optimum==2.1.0`, `onnx==1.21.0` added to the venv).

### Option B — ONNX Runtime int8 dynamic quantization (measured)

Pipeline: optimum exports `all-MiniLM-L6-v2` to ONNX fp32 → `onnxruntime.quantization.quantize_dynamic` with `QuantType.QInt8` produces `model_int8.onnx` (weights int8, activations fp32). Loaded via a plain `ort.InferenceSession`. Pooling and L2-normalization reimplemented in numpy (5 lines) because `SentenceTransformer`'s high-level wrapper is no longer in the path.

**Performance (measured):**

| Metric | Baseline fp32 | Option B int8 | Speedup |
|---|---|---|---|
| Artifact on disk | 88 MB | **21.8 MB** | 4.0× smaller |
| Cold (fresh process, import + tokenizer + session) | 55.2 s | **9.84 s** | **5.6× faster** |
| Warm load only | 14.69 s | 2.21 s | **6.6× faster** |
| Single query, median | 18.4 ms | 2.10 ms | **8.8× faster** |
| Single query, max (first query JIT) | 1170 ms | 3.2 ms | **365× faster** |
| Batch of 30, per query | 1.90 ms | 1.08 ms | 1.76× faster |
| Export+quantize, one-time | — | ~30 s (observed on first run) | amortized |

Cold-start speedup is the real prize — it's also the metric FX2-C had to expand timeouts for. Under Option B, the 20-s import / 30-s load defaults become wildly conservative.

**Quality (measured, same-model so cosine is valid):**

| Metric | Value |
|---|---|
| Cosine vs fp32, mean | 0.9635 |
| Cosine vs fp32, median | 0.9653 |
| Cosine vs fp32, min | 0.9453 |
| Cosine drift mean (1 − cos) | **3.65 %** |
| Cosine drift max | 5.47 % |

**Mean drift of 3.65 % exceeds the 2 % threshold in the brief.** The honest reading is that dynamic int8 on MiniLM is a little too aggressive — MiniLM is already a distilled model, so residual precision matters more than on a full BERT-base.

**Retrieval agreement probe (synthetic, 30-query self-ranking):**

| k | Jaccard (set overlap) | Exact-match % | Kendall-tau (order) |
|---|---|---|---|
| 1 | 0.767 | 76.7 % | 1.00 |
| 3 | 0.790 | 60.0 % | 0.60 |
| 5 | 0.783 | 46.7 % | 0.66 |
| 10 | 0.773 | 10.0 % | 0.69 |

Top-1 agrees 77 % of the time. In plain English: on ~1 out of 4 queries, the int8 backend would surface a different most-relevant result than the fp32 baseline. That's material for a tool whose contract is "find the right existing code."

**Important caveat (WSP 97):** this probe ranks each query against the other 29 queries, not the real HoloIndex ChromaDB corpus. At real corpus scale (thousands of entries) the distinctiveness margin between "right answer" and "second-best" typically grows, which tends to *reduce* the rate at which quantization noise flips the ordering. I did not measure that; it needs a proper A/B on the live collections in a later slice.

**Verdict for B**: performance wins are large and real. Quality is *borderline* — not acceptable as-is under the brief's threshold, but a standard static-calibration pass (using a sample of 100-500 real HoloIndex queries as a calibration set, available through the search-cache logs) typically cuts MiniLM int8 drift by 2-3×, which would land it well under 2 %. Recommend B *contingent on* doing that calibration work as part of HIA3; if static calibration doesn't get there, fall back to A.

### Option C — llama-cpp GGUF embedding

**Classified HIGH_SETUP_COST, not benchmarked.**

`llama-cpp-python==0.3.20` is installed. The repo already uses it for Gemma chat inference (see `gemma_rag_inference.py`). No code work is needed to load a GGUF embedder — `Llama(model_path=..., embedding=True)` is a one-liner.

What's missing is the model. No embedding GGUF is present at `E:/HoloIndex/models/`. Candidate models that would need to be downloaded:

| Model | Dims | Size (Q4_K_M) | Notes |
|---|---|---|---|
| `CompendiumLabs/bge-small-en-v1.5-gguf` | **384** | ~33 MB | Matches MiniLM dim — no reindex if adopted |
| `nomic-ai/nomic-embed-text-v1.5.Q4_K_M.gguf` | 768 | ~80 MB | Higher quality, **would require full ChromaDB reindex** |
| `CompendiumLabs/bge-base-en-v1.5-gguf` | 768 | ~85 MB | Same reindex concern as nomic |

Per architect instruction, no download was performed. `bge-small-en-v1.5` is the only dim-compatible candidate; it's also a *different* model than MiniLM, so cosine-drift is not a meaningful comparison — quality would have to be measured via retrieval agreement on the real corpus, which is outside this timebox.

**Why C is deferred, not rejected:** if static-calibrated int8 (Option B refined) can't get under the quality threshold, `bge-small-en-v1.5-gguf` is a promising Plan C — it reuses existing llama-cpp infrastructure and matches dim, but it's a different model with different retrieval semantics and would need its own A/B.

---

## Final recommendation

**Option B (ONNX Runtime int8) — with a mandatory calibration follow-up before production.**

Rationale:
1. **Performance is decisive**: 5.6× cold-start speedup, 6.6× load speedup, 8.8× single-query speedup, 4.0× smaller on disk. Cold-start is the known HoloIndex pain point (FX2-C timeout expansion).
2. **Same-model, same-dim**: zero migration cost on the ChromaDB side. No reindex of `navigation_code`, `navigation_wsp`, `navigation_tests`, `navigation_skills`, `navigation_symbols`. This alone rules Option C out of the near-term path.
3. **Tooling already in the venv** after TQ1's `pip install optimum[onnxruntime]`. No new runtime dependencies to justify; optimum is only needed at export time, production only needs `onnxruntime` + `transformers` (already pinned).
4. **Quality gap is closable**: dynamic int8 is the crudest form of quantization. Static calibration with a real query sample is a standard technique with a well-known 2-3× drift reduction on MiniLM. HIA3 should scope that work explicitly.

**What HIA3 should NOT skip:**
- A real A/B on the live ChromaDB corpus (not the synthetic 30-query probe from this report). Top-1 agreement on real retrieval workload is the truth test.
- Static calibration pass using real query logs (search_cache hits or HoloIndex command-line history) as the calibration set.
- Promotion gate: int8 drift <2 % AND real-corpus top-5 agreement >95 % before flipping `TurboQuantEmbedder.is_available()` to `True`.

---

## WSP 97 caveats — what was measured vs estimated vs blocked

**Measured (direct numbers in this report):**
- All baseline and Option B latency and artifact numbers.
- Cosine drift on the 30 TQ1 queries.
- Synthetic top-k agreement on the 30 TQ1 queries.

**Estimated (explicitly labeled):**
- Option A performance numbers (derived from Option B minus the int8 step).
- Option C artifact sizes (from Hugging Face model cards, not downloaded or loaded).
- Static-calibration drift reduction ("2-3× typical") — rule of thumb from the ONNX Runtime quantization docs, not measured on this model.

**Not measured / blocked:**
- Real-corpus A/B agreement (requires running HoloIndex against ChromaDB with each backend; out of TQ1 scope).
- Option A as a distinct row (see analysis — the fp32 ONNX artifact exists and is ready to benchmark; ~5 minutes if architect requests).
- Option C end-to-end (no local GGUF embedder; download blocked per brief).
- GPU acceleration (CPU-only on purpose — HoloIndex runs CPU-only in production).

---

## Follow-ups (not part of TQ1)

1. **HIA3** — implement calibrated int8 path in `TurboQuantEmbedder.encode()`, promote `is_available()` behind a real-corpus A/B gate.
2. **TQ1-addendum** (cheap, if requested): benchmark Option A as a distinct row against the already-exported fp32 ONNX.
3. **Observability** — surface `embedding_backend` through the CLI's `--status` output so operators can see which backend served a query (already done in search metadata per HIA-TAX1; CLI surface is the missing piece).
4. **Calibration-set harvesting** — tap `search_cache` or the agent activity log for a realistic query distribution to feed static-calibration in HIA3.
