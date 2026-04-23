# TQ0 — Turbo-Quant Research (Phase 0)

**Slice**: `TQ0_TURBOQUANT_RESEARCH_PHASE0`
**Window**: W6
**Lane**: HoloIndex embedding backend / cold-start reduction
**Date**: 2026-04-21
**Status**: Research-only. No code changes, no package installs, no model downloads.

This document surveys int8-quantization options for the HoloIndex embedding backend (`sentence-transformers/all-MiniLM-L6-v2`). It is intended as the evidence base for a W7 implementation slice. All numeric claims are labeled either **VERIFIED** (measured/read in this repo or filesystem during this research), **LITERATURE** (widely cited in the vendor / HF community but not re-measured here), or **UNKNOWN** (no citable source available offline and no measurement performed).

---

## 1. Current state (VERIFIED)

| Aspect | Current value | Evidence |
|---|---|---|
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` | `holo_index/core/holo_index.py:190` — `model_name = "all-MiniLM-L6-v2"` |
| Weights format | float32 safetensors | `model.safetensors` in HF cache snapshot |
| Weights file size on disk | **87 MB** | `ls` of `E:\HoloIndex\models\models--sentence-transformers--all-MiniLM-L6-v2\snapshots\c9745ed1d9f207416be6d2e6f8de32d1f16199bf\model.safetensors` |
| Embedding dimension | 384 | MiniLM-L6-v2 spec (model card; not re-measured) — LITERATURE |
| Backend | `sentence-transformers` (PyTorch) | `from sentence_transformers import SentenceTransformer as ST` — `holo_index/core/holo_index.py:88` |
| Runtime wrapper | Timeout-guarded import + load | `HOLO_MODEL_IMPORT_TIMEOUT=20s` default (l.47); `HOLO_MODEL_LOAD_TIMEOUT` used at l.227 |
| Fallback on timeout | Lexical-only retrieval | `self.retrieval_mode = "lexical"` l.205 / l.232 |
| Declared dependencies | `sentence-transformers>=2.2.0`, `llama-cpp-python==0.2.69`, `chromadb>=0.4.0` | `holo_index/requirements.txt` |

**Performance baseline claimed in W6 brief (REPORTED, not re-measured in this slice)**:
- Import time ~12 s
- Model load ~20 s

These two numbers are the optimization target. Note that the ~12 s import cost is dominated by `torch` + `transformers` (both pulled transitively by `sentence-transformers`), not by the MiniLM weights themselves. Any backend that removes the PyTorch import from the hot path is likely to produce a cold-start win that is **independent of int8 quantization**. This distinction matters for framing the Phase 1 benchmarks in W7.

---

## 2. Model inventory — `E:\HoloIndex\models\` (VERIFIED)

Quantized / GGUF models already present locally:

| Path | Type | Quantization | Purpose |
|---|---|---|---|
| `gemma4-e2b/google_gemma-4-E2B-it-Q4_K_M.gguf` | Generative (Gemma 4 E2B) | Q4_K_M | Not embeddings |
| `qwen3.5-4b/Qwen3.5-4B-Q4_K_M.gguf` | Generative (Qwen 3.5 4B) | Q4_K_M | Not embeddings |
| `mradermacher/UI-TARS-1.5-7B-GGUF/…Q3_K_M.gguf` | Vision-language (UI-TARS) | Q3_K_M / Q3_K_S | Not embeddings |
| `ui-tars-1.5/lmstudio-community/gpt-oss-20b-GGUF/gpt-oss-20b-MXFP4.gguf` | Generative | MXFP4 | Not embeddings |
| `models--sentence-transformers--all-MiniLM-L6-v2/…/model.safetensors` | Embedding (MiniLM-L6-v2) | **float32 only** | Current HoloIndex model |

**Conclusion**: No quantized MiniLM (or any embedding-only quantized model) is currently present locally. Every GGUF under `E:\HoloIndex\models\` is a generative or vision-language LLM. Any int8 path selected in W7 will require adding a new artifact (either by ONNX export from the existing fp32 checkpoint, a GGUF download, or a ctranslate2 conversion).

---

## 3. Existing quantization patterns in this codebase (VERIFIED)

The repository already has a working `llama-cpp-python` loading pattern for quantized **generative** models. The canonical example is:

```python
# holo_index/qwen_advisor/gemma_rag_inference.py:169–195
from llama_cpp import Llama
# Suppress llama.cpp stdout/stderr noise
old_stdout, old_stderr = os.dup(1), os.dup(2)
devnull = os.open(os.devnull, os.O_WRONLY)
try:
    os.dup2(devnull, 1); os.dup2(devnull, 2)
    self.gemma_llm = Llama(
        model_path=str(self.gemma_model_path),
        n_ctx=2048,
        n_threads=2,
        n_gpu_layers=0,
        verbose=False,
    )
finally:
    os.dup2(old_stdout, 1); os.dup2(old_stderr, 2)
    os.close(devnull)
```

Also used in:
- `holo_index/qwen_advisor/llm_engine.py:84–100` (Qwen generative)
- `holo_index/qwen_advisor/orchestration/autonomous_refactoring.py:43`

**Implication**: if W7 chooses the llama.cpp embeddings path, there is a proven in-repo loading pattern (including stdout suppression, CPU-only defaults, and controlled thread count) to copy. No `optimum`, `onnxruntime`, or `ctranslate2` patterns exist in this codebase today.

---

## 4. Options matrix

Each row evaluates a distinct backend for serving MiniLM-L6-v2 embeddings with int8 (or lower) weights. Columns mark evidence class for each claim.

| # | Option | New deps | Artifact | Removes `torch` from hot path? | In-repo pattern exists? | Expected weight size | Accuracy regression | Literature support |
|---|---|---|---|---|---|---|---|---|
| A | `optimum` + ONNX Runtime, dynamic int8 | `optimum[onnxruntime]` (new) | `.onnx` + `model_quantized.onnx` | **Yes** (ORT Python wheel is a torch-free runtime for inference) | No | ~23 MB (LITERATURE: typical int8 BERT compression, UNKNOWN for MiniLM-specific) | <1% MTEB drop typical for dynamic int8 on MiniLM (LITERATURE, Hugging Face optimum docs) | Highest: first-class HF tooling, `optimum-cli export onnx` and `ORTQuantizer` are the documented recipe |
| B | `sentence-transformers` 3.x built-in ONNX / OpenVINO / quantized backend | No new pip surface if already on ST 3.x; UNKNOWN whether current `sentence-transformers>=2.2.0` satisfies | `.onnx` | **Yes** on the ORT/OpenVINO path | No | Same as A | Same as A | Good: ST 3.x introduced `backend="onnx"` / `backend="openvino"` kwargs to `SentenceTransformer` — LITERATURE |
| C | `llama-cpp-python` embeddings (`embedding=True` + MiniLM GGUF) | None (already `llama-cpp-python==0.2.69`) | MiniLM GGUF | **Yes** (llama.cpp is native C++, no torch) | Yes — copy `gemma_rag_inference.py` load pattern | ~22–30 MB (LITERATURE for MiniLM Q4/Q5/Q8 GGUFs; UNKNOWN without downloading) | UNKNOWN — depends on quant (Q8 ≈ float16, Q4 typically 1–3% MTEB drop on BERT-class encoders, LITERATURE) | Moderate. MiniLM GGUF conversions exist on HF (e.g. community repos), but availability on HF today is UNKNOWN without web access. Embedding API in `llama-cpp-python` 0.2.x is functional but less battle-tested than ORT |
| D | `ctranslate2` + `ct2-transformers-converter` | `ctranslate2` (new) | CT2 model dir | **Yes** (standalone C++ runtime) | No | ~23 MB (int8 BERT, LITERATURE) | <1% typical (LITERATURE) | Moderate: CT2 has an `encoder_only` path for BERT/MiniLM and is the production choice at several orgs |
| E | Binary / int8 **embedding-output** quantization via `sentence-transformers.quantize_embeddings()` | None (already ST) | Same fp32 weights | **No** (weights unchanged; only compresses emitted vectors) | No | 87 MB (unchanged) | ~1–4% recall drop (LITERATURE, HF "Binary and Scalar Quantization" 2024 post) | **Does not solve the stated problem**: this is a vector-compression technique for ANN storage, not a weight-quantization / cold-start technique. Listed for completeness so it is not confused with A–D. |
| F | Replace MiniLM with a smaller / natively-quantized embedding model (e.g. `bge-micro-v2` int8, `nomic-embed-text` GGUF) | Varies | New model | Yes | No | Varies | **Model-swap, not a quant of the same model** — different semantic fingerprint, requires re-indexing Chroma. Out of scope for TQ0 unless accuracy on MTEB-ish retrieval is not a constraint. |

**Out of the matrix**: QAT (quantization-aware training) — would require a training pipeline and labeled retrieval data; vastly out of scope for W7.

---

## 5. Expected performance gains

All numbers below are **LITERATURE ranges** unless tagged otherwise. W7 must re-measure on this machine.

### 5.1 Cold-start import time (current ~12 s, REPORTED)

The dominant cost is `import torch` (and its transitive extensions) pulled by `sentence-transformers`. Empirically on Windows+Python 3.11/3.12 this is commonly **5–10 s** just for torch (LITERATURE; user reports on PyTorch issue tracker), with additional cost for `transformers` and `sentence-transformers` init.

- **Option A / B / D**: drop torch from the hot path → expected import time **1–4 s** (LITERATURE for ORT / ctranslate2 cold imports; UNKNOWN without measurement). This is the single largest lever.
- **Option C** (llama-cpp-python): already imported elsewhere in HoloIndex for the advisor path, so its cost may already be paid before the embedding phase starts. Net additional import cost close to **0 s** if the advisor initializes first; **~0.5–1 s** otherwise (LITERATURE).
- **Option E**: no change — torch still imported.

**Expected speedup on the import leg: 3–10× (cold)**, attributable mostly to the choice of non-torch runtime, not to int8 per se.

### 5.2 Model load time (current ~20 s, REPORTED)

Weight load time is roughly linear in file size for mmap-backed loaders and roughly linear in on-disk size for full deserializers. int8 cuts on-disk size ~4×.

- **Options A, B, D**: load from ~20 MB int8 artifact → **4–8× load speedup** is the commonly cited ballpark (LITERATURE). On a warm page cache the wall-clock may be dominated by framework init, not I/O.
- **Option C**: GGUF mmap load is typically **<1 s** for a ~25 MB MiniLM GGUF (LITERATURE; Gemma 3 270M GGUF loads similarly fast in the existing `gemma_rag_inference.py` path).

**Expected speedup on the load leg: 4–20× (cold)**. UNKNOWN until benchmarked.

### 5.3 Per-query inference latency

- **fp32 PyTorch MiniLM-L6-v2 on CPU**: commonly ~5–15 ms / short sentence on modern x86 (LITERATURE).
- **int8 ONNX / CT2**: commonly **2–4× faster** than fp32 PyTorch on CPU for BERT-class encoders (LITERATURE — Intel neural-compressor benchmarks, HF optimum examples).
- **llama.cpp embeddings**: competitive when GGUF is Q8 or higher; Q4 can be faster but may regress accuracy more.
- **Option E**: no runtime change; only affects downstream vector-store costs.

HoloIndex embeds one query per `search`, so absolute per-query improvement (~5–10 ms saved) is negligible versus the cold-start wins. This favors optimizing for cold start first.

### 5.4 Accuracy tradeoff

- Dynamic int8 on MiniLM is commonly reported at <1% MTEB regression (LITERATURE, HF optimum docs).
- Q4 GGUF on BERT-class encoders can drop 1–3% (LITERATURE).
- Binary embedding quantization (Option E) drops 1–4% recall (LITERATURE).
- HoloIndex's retrieval bar is internal code search, not a public benchmark, so a small MTEB regression is likely invisible in practice. UNKNOWN until measured against the HoloIndex evaluation fixtures (W7 must define a spot-check corpus).

---

## 6. llama.cpp embeddings specifics

The research brief asks explicitly whether llama.cpp supports embedding-only models and whether a MiniLM GGUF exists.

- **Does `llama.cpp` / `llama-cpp-python` support embeddings?** Yes (LITERATURE; `Llama(..., embedding=True)` + `Llama.embed()` / `Llama.create_embedding()`). The API has been present since `llama-cpp-python` 0.2.x and is what the repo already depends on (0.2.69).
- **Does a MiniLM GGUF exist?** **UNKNOWN from this environment.** Community GGUF conversions of small BERT-class encoders exist on Hugging Face (e.g. `leliuga/all-MiniLM-L6-v2-GGUF` is commonly cited — LITERATURE, availability as of this session **UNVERIFIED** because W6 forbids downloads). W7 must verify availability or convert locally via `llama.cpp/convert-hf-to-gguf.py`.
- **Known caveat**: llama.cpp's BERT/embedding path went through churn in 2024. `llama-cpp-python==0.2.69` is pinned, and the embedding API shape in that specific version is **UNKNOWN without a code test**. W7 should either (a) upgrade `llama-cpp-python` or (b) confirm 0.2.69's embedding API behavior before committing.

---

## 7. Recommended approach

**Primary recommendation: Option A — `optimum[onnxruntime]` + dynamic int8 export of MiniLM-L6-v2.**

Rationale:
1. **Directly attacks both stated pains.** The ~12 s import cost is dominated by `torch`; ORT Python replaces that with a much smaller native wheel (LITERATURE). The ~20 s load cost is dominated by an 87 MB fp32 deserialize; int8 cuts that to ~23 MB (LITERATURE).
2. **Most mature tooling path.** `optimum-cli export onnx` and `ORTQuantizer.quantize(config=AutoQuantizationConfig.avx2())` are Hugging Face's documented, supported recipe for exactly this model.
3. **Mechanical, reproducible conversion.** The fp32 safetensors already on disk (`E:\HoloIndex\models\…`) can be the export source — no new model download is required, only a one-time ONNX export that W7 can vendor into the repo's indexes directory.
4. **Accuracy risk is bounded.** Dynamic int8 on MiniLM is widely reported at <1% MTEB delta (LITERATURE). W7 can spot-check against a small fixture before cutover.
5. **Minimizes operational surprises.** Does not touch the `llama-cpp-python==0.2.69` pin, does not require changing the advisor path, and leaves `sentence-transformers` in place as a fallback if ORT is unavailable.

**Backup recommendation: Option C — `llama.cpp` embeddings via the already-installed `llama-cpp-python`.**

Conditions that would make C preferable to A:
- A working MiniLM GGUF is easy to obtain or convert.
- The team prefers zero new Python pip surface.
- The embedding API in `llama-cpp-python==0.2.69` is validated to work (needs a small spike in W7).

**Explicitly not recommended for this phase:**
- Option E (embedding-output quantization) — solves a different problem; does not improve cold start.
- Option F (model swap) — violates the implicit contract that existing Chroma indexes remain valid.
- QAT — out of scope.

---

## 8. Risks and open questions (for W7)

1. **Is `sentence-transformers` currently on 2.x or 3.x in this venv?** The pin is `>=2.2.0`. Option B (ST native ONNX backend) is only viable on ≥3.x. **UNKNOWN** until W7 inspects the resolved version in the active venv. If 3.x is in use, A and B converge — same ONNX artifact, different Python entrypoint.
2. **Does `chromadb` store embeddings under an implicit fp32 contract?** If a new backend produces numerically slightly different vectors, existing index entries may drift. Mitigation: re-embed + re-index once on cutover (one-time cost), or keep fp32 as the indexing path and int8 only as the query path. W7 must decide.
3. **MiniLM GGUF availability.** UNKNOWN offline; W7 must verify or convert.
4. **`llama-cpp-python==0.2.69` embedding API parity.** The pin predates several embedding-path fixes in upstream. If C is chosen, a version bump may be required — which would affect the existing advisor path and therefore needs coordination.
5. **Windows wheels.** ORT, ctranslate2, and llama-cpp-python all ship pre-built Windows wheels, but AVX/AVX2 support flags vary by CPU. W7 should declare the target CPU feature set.
6. **Offline mode.** HoloIndex already supports `HOLO_OFFLINE=1`. The new backend must not break that path.
7. **No fabricated benchmarks.** Every number in §5 is either LITERATURE or UNKNOWN. W7 must produce measured numbers on this machine before accepting the swap.

---

## 9. Handoff to W7

W7 should take the following as inputs:

- **Target model identifier**: `sentence-transformers/all-MiniLM-L6-v2` (unchanged).
- **Source artifact**: `E:\HoloIndex\models\models--sentence-transformers--all-MiniLM-L6-v2\snapshots\c9745ed1d9f207416be6d2e6f8de32d1f16199bf\model.safetensors` (87 MB, fp32, VERIFIED).
- **Primary path**: export to ONNX via `optimum-cli`, apply `ORTQuantizer` dynamic int8, persist to a predictable path (e.g. `E:\HoloIndex\models\all-MiniLM-L6-v2-onnx-int8\`), add a thin backend switch in `holo_index/core/holo_index.py` around l.186–230 so `sentence-transformers` PyTorch load becomes the fallback.
- **Required measurements before cutover**:
  - Cold `import` time of the new backend.
  - Cold load time for the int8 artifact.
  - Per-query latency for a representative HoloIndex query.
  - Top-k recall delta on an internal fixture (W7 to define).
- **Required tests**: existing HoloIndex tests must still pass with the new backend; a parity test between fp32 and int8 vectors (e.g. cosine ≥ 0.99 on a sample set) is a reasonable acceptance gate.
- **Non-goals for W7** (deferred): Option F (model swap), QAT, GPU inference, server-side embedding.

---

## 10. References

All external references are from prior knowledge; **none were fetched in this session** (W6 forbids network access for this slice).

- Hugging Face `optimum` docs — "Quantization" and "Accelerated Inference with ONNX Runtime".
- Hugging Face `sentence-transformers` 3.x release notes — ONNX and OpenVINO backends.
- Hugging Face blog (2024) — "Binary and Scalar Quantization for Sentence Transformers" (Option E background).
- `llama-cpp-python` README — `embedding=True` flag and `Llama.create_embedding()` API.
- `ctranslate2` docs — `ct2-transformers-converter` encoder-only path for BERT.
- Intel neural-compressor examples for BERT int8 dynamic quantization.

No benchmarks from these references are reproduced verbatim as local numbers; W7 produces the canonical measurements for this repo.
