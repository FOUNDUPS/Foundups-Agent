# Audio Agents Research

**Date**: 2026-03-30
**Author**: 0102
**Status**: Research / Integration Planning

---

## Executive Summary

This document captures recent developments in open-source ASR/TTS, with integration recommendations for the FoundUps Agent codebase.

| Item | Type | License | Recommendation |
|------|------|---------|----------------|
| Cohere Transcribe | ASR | Apache 2.0 | **Primary ASR** |
| Qwen3-TTS | TTS | Apache 2.0 | **Primary TTS (testing)** |
| Mistral Voxtral TTS | TTS | Eval-only | **Eval-only** (licensing restrictions) |

---

## 1. Cohere Transcribe

### Overview
- **Type**: Open-source Automatic Speech Recognition (ASR)
- **Parameters**: 2B
- **License**: Apache 2.0
- **Release**: March 2026

### Why It Matters
- Production-ready open-source ASR at scale
- Apache 2.0 allows commercial use without cloud dependency
- Can run locally on E:/HoloIndex/models infrastructure
- Competitive with Whisper large-v3 on benchmarks

### Production Recommendation
**PRIMARY ASR CANDIDATE** - Replace or supplement existing WhisperSTTBackend in `openclaw_voice.py`.

### Integration Path
1. Download GGUF/safetensors to `E:/HoloIndex/models/cohere-transcribe-2b/`
2. Add `asr` role to `local_model_selection.py`
3. Create `CohereTranscribeBackend` class following existing backend pattern
4. Add to STT chain as primary (WhisperSTTBackend becomes fallback)

### Risk Assessment
- **Licensing**: Apache 2.0 - CLEAR
- **Compute**: 2B params - moderate GPU/CPU requirements
- **Maturity**: New release - needs validation

---

## 2. Qwen3-TTS

### Overview
- **Type**: Open-source Text-to-Speech / Voice Clone family
- **License**: Apache 2.0
- **Release**: March 2026

### Why It Matters
- Production-quality TTS from Qwen team (Alibaba)
- Voice cloning capability enables personalization
- Apache 2.0 allows commercial deployment
- Aligns with existing Qwen model infrastructure

### Production Recommendation
**PRIMARY TTS CANDIDATE FOR TESTING** - Evaluate as replacement for EdgeTTSBackend.

### Integration Path
1. Download to `E:/HoloIndex/models/qwen3-tts/`
2. Add `tts` role to `local_model_selection.py`
3. Create `Qwen3TTSBackend` class following existing backend pattern
4. Add voice cloning safety gate (consent + whitelist required)

### Risk Assessment
- **Licensing**: Apache 2.0 - CLEAR
- **Voice Cloning**: Requires consent/whitelist policy gate
- **Compute**: TBD - needs benchmarking

---

## 3. Mistral Voxtral TTS

### Overview
- **Type**: 4B parameter TTS with zero-shot voice cloning
- **License**: Evaluation-only / Restricted
- **Release**: March 2026

### Why It Matters
- State-of-the-art voice cloning quality
- Zero-shot capability (no fine-tuning needed)
- Demonstrates frontier TTS capabilities

### Production Recommendation
**EVAL-ONLY - DO NOT USE IN PRODUCTION**

### Integration Path
1. Add with `production_enabled=false` flag
2. Gate behind explicit eval mode check
3. Document licensing restrictions clearly

### Risk Assessment
- **Licensing**: RESTRICTED - eval-only, not for production
- **Voice Cloning**: Same consent requirements apply
- **Deployment**: Cannot be shipped in production builds

---

## Next Actions

### Immediate (This Session)
1. Extend `local_model_selection.py` with `asr` and `tts` roles - DONE
2. Add provider registry with production flags - DONE
3. Implement voice cloning consent gate - DONE

### Short-Term (Next Sprint)
1. Download Cohere Transcribe to E:/HoloIndex/models/
2. Benchmark ASR accuracy vs current Whisper setup
3. Download Qwen3-TTS for voice testing
4. Create voice consent UI/config

### Medium-Term
1. Replace EdgeTTS with local Qwen3-TTS
2. Add Cohere Transcribe to STT chain

---

## Model Storage Convention

All models go to `E:/HoloIndex/models/`:

```
E:/HoloIndex/models/
├── cohere-transcribe-2b/     # ASR (future)
├── qwen3-tts/                # TTS (future)
├── voxtral-tts-eval/         # TTS eval-only (future)
├── gemma-3-270m-it-Q4_K_M.gguf  # Existing triage
├── qwen3.5-4b/               # Existing general
└── ui-tars-1.5/              # Existing vision
```

---

## References

- Existing STT/TTS: `modules/infrastructure/cli/src/openclaw_voice.py`
- Model selection: `modules/infrastructure/shared_utilities/local_model_selection.py`
- Provider registry: `modules/infrastructure/shared_utilities/audio_provider_registry.py`
- Voice policy: `modules/infrastructure/shared_utilities/voice_cloning_policy.py`
