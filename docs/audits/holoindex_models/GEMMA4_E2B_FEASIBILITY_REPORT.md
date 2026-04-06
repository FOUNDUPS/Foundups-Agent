# Gemma 4 E2B — Local HoloIndex Feasibility Report

**Worker H** · `HOLOINDEX_GEMMA4_FEASIBILITY_AND_BOOTSTRAP_PHASE1` · 2026-04-03

---

## Verdict: VIABLE — CONFIRMED

Gemma 4 E2B fits the RTX 2060 6GB VRAM budget and is fully operational. LM Studio 0.4.9+1 supports `gemma4` architecture. Model loaded in 10s, smoke test passed (inference confirmed).

---

## 1. Model Specifications

| Property | Value |
|----------|-------|
| Name | Gemma 4 E2B (google/gemma-4-E2B) |
| Parameters | 2.3B effective (5.1B with embeddings) |
| Modalities | Text + Image + Audio (multimodal) |
| Context | 128K tokens |
| Layers | 35 |
| Architecture | `gemma4` (new, requires llama.cpp b8648+) |
| Target | On-device deployment |

## 2. Quantization — Q4_K_M (recommended)

| Quant | Size | VRAM (est.) | Quality | Source |
|-------|------|-------------|---------|--------|
| Q4_K_M | 3.46 GB | ~4.0 GB | Recommended balance | bartowski/google_gemma-4-E2B-it-GGUF |
| Q4_K_S | 3.34 GB | ~3.8 GB | Slightly lower quality | bartowski |
| Q3_K_M | 2.94 GB | ~3.4 GB | Noticeable quality loss | bartowski |
| Q8_0 | 5.88 GB | ~6.2 GB | Near-lossless | bartowski (too large for 6GB) |

**Decision**: Q4_K_M at 3.46GB leaves ~2GB headroom on RTX 2060 6GB. Q8_0 exceeds VRAM.

## 3. Local Hardware Compatibility

| Resource | Available | Required | Status |
|----------|-----------|----------|--------|
| GPU VRAM | 6 GB (RTX 2060) | ~4.0 GB (Q4_K_M) | PASS |
| Disk (E:) | 863 GB free | 3.46 GB | PASS |
| LM Studio | 0.4.9+1 (updated from 0.4.8) | gemma4 arch CONFIRMED | PASS |
| llama_cpp Python | 0.2.69 | needs gemma4 arch | CONDITIONAL |

## 4. Runtime Compatibility

### LM Studio (primary path)

- **Version**: 0.4.9+1 (updated from 0.4.8), CLI commit 8d3f370
- **Known archs**: gemma3, Qwen2, qwen3, qwen35, qwen2vl, Nomic BERT
- **Risk**: Bug reports (GitHub issues #1742, #1728) showed "unknown model architecture 'gemma4'" on older versions
- **Status**: CONFIRMED on 0.4.9+1 — model loaded in 10s, smoke test passed

### llama_cpp Python (fallback path)

- **Version**: 0.2.69
- **Risk**: May not include gemma4 architecture support
- **Mitigation**: `pip install --upgrade llama-cpp-python` should pull in b8648+ bindings

### GGUF Sources (two repos)

1. `bartowski/google_gemma-4-E2B-it-GGUF` — 23 quantization variants, bartowski quality
2. `lmstudio-community/gemma-4-E2B-it-GGUF` — LM Studio-optimized packaging

## 5. Integration Architecture

Per architect call: **E2B only, additive, do not repoint consumers**.

```
E:/HoloIndex/models/gemma4-e2b/          ← GGUF download target
E:/LM_studio/models/local/gemma4-e2b/    ← hardlink mirror for LM Studio

Bootstrap script: holo_index/scripts/bootstrap_gemma4_e2b_lmstudio.py
```

**NOT touched** (per architect):
- `local_model_selection.py` — no new role added, no `resolve_*` repointing
- Existing triage/general/code consumers — unchanged
- No env var additions to `wre_defaults.env`

**Future promotion path** (not this slice):
1. Add `multimodal` role to `local_model_selection.py`
2. Set `LOCAL_MODEL_MULTIMODAL_DIR=E:/LM_studio/models/local/gemma4-e2b`
3. Consumers opt-in via `resolve_model_path("multimodal")`

## 6. What Gemma 4 E2B Enables (future slices)

- **Multimodal triage**: Image+text classification for pfMALL tile content
- **Audio transcription assist**: Complement Cohere Transcribe 2B with Gemma audio understanding
- **Visual validation**: Screenshot-based UI testing (complement UI-TARS)
- **Upgraded triage**: Replace gemma-270m for higher-quality fast classification

## 7. Bootstrap Script Usage

```bash
# Download only (safe, no LM Studio interaction)
python holo_index/scripts/bootstrap_gemma4_e2b_lmstudio.py --download-only

# Full bootstrap (download + mirror + LM Studio load)
python holo_index/scripts/bootstrap_gemma4_e2b_lmstudio.py --smoke

# Use lmstudio-community repo instead
python holo_index/scripts/bootstrap_gemma4_e2b_lmstudio.py --use-lmstudio-community --smoke

# Verify via llama_cpp Python fallback
python holo_index/scripts/bootstrap_gemma4_e2b_lmstudio.py --download-only --verify-llama-cpp
```

## 8. Remaining Risk

| Risk | Severity | Mitigation |
|------|----------|------------|
| LM Studio arch incompatibility | RESOLVED | Updated to 0.4.9+1; gemma4 arch confirmed working |
| llama_cpp 0.2.69 incompatibility | LOW | pip upgrade |
| Q4_K_M quality insufficient | LOW | Can switch to Q5_K_M (4.09 GB, still fits) |
| GPU memory contention with other loaded models | MEDIUM | Unload one model before loading gemma4-e2b |

---

**Worker H** · Bootstrap script committed. Feasibility: **VIABLE — CONFIRMED**. Model loaded and inference verified on LM Studio 0.4.9+1 with RTX 2060 6GB. Load time: 10s. No existing consumers repointed.
