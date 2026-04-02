# Voxtral TTS Evaluation Contract for antifaFM

**Date**: 2026-03-31
**Owner**: 0102
**Status**: EVAL-ONLY (not production)

---

## Executive Summary

This contract defines the evaluation boundary for Mistral Voxtral TTS within the antifaFM broadcaster. Voxtral is a 4B parameter TTS model with zero-shot voice cloning capability. It is registered in `audio_provider_registry.py` as `voxtral_tts_eval` with `production_enabled=false`.

**Key constraint**: Voxtral evaluation must flow through the shared audio substrate and voice cloning policy. No broadcaster-local duplicate registry.

---

## Current State Audit

### antifaFM Voice Output Surfaces (as of 2026-03-31)

| Surface | Type | Current Implementation | TTS Candidate |
|---------|------|------------------------|---------------|
| Icecast stream | Audio relay | `ffmpeg_streamer.py` passthrough | NO - pure relay |
| Karaoke overlay | STT-only | `karaoke_overlay.py` (Whisper) | NO - STT, not TTS |
| News ticker | Text display | `news_ticker.py` (OBS text source) | YES - narration |
| DJ interstitials | None | Not implemented | YES - primary candidate |
| Emergency alerts | None | Not implemented | YES - safety-critical |
| Branded intros/outros | None | Not implemented | YES - consistency |

### Shared Audio Substrate

**Provider registry**: `modules/infrastructure/shared_utilities/audio_provider_registry.py`

| Provider | Type | Production | Voice Cloning | Notes |
|----------|------|------------|---------------|-------|
| `cohere_transcribe` | ASR | YES | NO | Preferred ASR |
| `whisper_local` | ASR | YES | NO | Fallback ASR |
| `qwen3_tts` | TTS | YES | YES | Preferred TTS |
| `edge_tts` | TTS | YES | NO | Cloud fallback |
| `voxtral_tts_eval` | TTS | **NO** | YES | EVAL ONLY |

### Voice Cloning Policy

**Policy gate**: `modules/infrastructure/shared_utilities/voice_cloning_policy.py`

Any voice cloning request must satisfy:
1. Voice ID on `allowed_voices` whitelist
2. Explicit consent recorded for voice ID
3. Kill switch not engaged
4. Audit logging for all requests

---

## Candidate Use Cases

### 1. DJ Interstitials (PRIMARY CANDIDATE)

**Description**: Short TTS announcements between songs or segments.

**Examples**:
- "This is antifaFM, broadcasting 24/7 antifascist music"
- "Now playing: [track name] by [artist]"
- "Thanks for tuning in to antifaFM"

**Voice mode**:
- Generic synthetic: OK without consent
- Cloned DJ persona: REQUIRES consent + whitelist

**Evaluation criteria**:
- Latency: < 500ms to first audio
- Quality: Natural prosody, correct pronunciation
- Integration: Fits FFmpeg audio mixing pipeline

### 2. Emergency Announcements (SAFETY-CRITICAL)

**Description**: Urgent alerts requiring immediate audience attention.

**Examples**:
- "Emergency broadcast test"
- "Stream experiencing technical difficulties"
- "We'll be back shortly"

**Voice mode**: Generic synthetic ONLY (no cloning)

**Evaluation criteria**:
- Reliability: Must work when other systems fail
- Clarity: High intelligibility even at low quality
- Speed: Immediate generation, no queuing delay

### 3. News Ticker Narration (OPTIONAL)

**Description**: Text-to-speech reading of scrolling headlines.

**Current state**: `news_ticker.py` displays text only.

**Voice mode**: Generic synthetic ONLY

**Evaluation criteria**:
- Pacing: Match ticker scroll speed
- Pronunciation: Handle proper nouns, foreign names
- Volume: Balance with music stream

### 4. Branded Intros/Outros (FUTURE)

**Description**: Consistent station identification.

**Voice mode**:
- Pre-recorded: No TTS needed
- Live-generated: Cloned or generic

**Evaluation criteria**: Deferred until DJ persona requirements clarified.

---

## Evaluation Protocol

### Phase 1: Latency Benchmark

Test Voxtral first-audio latency with:
```python
from modules.infrastructure.shared_utilities.audio_provider_registry import (
    get_audio_registry,
    is_voxtral_allowed,
)

# Only in eval environment
if is_voxtral_allowed():
    # Benchmark latency
    pass
```

**Target**: < 500ms to first audio for 10-word utterance

### Phase 2: Quality Assessment

Evaluate:
- Prosody (naturalness of intonation)
- Pronunciation (proper nouns, foreign words)
- Consistency (same voice across generations)

**Method**: Generate 10 sample DJ interstitials, rate 1-5.

### Phase 3: Integration Fit

Test FFmpeg audio mixing:
```bash
ffmpeg -i stream.mp3 -i tts_output.wav \
  -filter_complex "[0:a][1:a]amix=inputs=2:duration=longest" \
  -f flv rtmp://...
```

### Phase 4: Policy Compliance

Verify voice cloning policy is enforced:
```python
from modules.infrastructure.shared_utilities.voice_cloning_policy import (
    get_voice_policy,
    VoiceCloneRequest,
)

policy = get_voice_policy()
result = policy.check(VoiceCloneRequest(
    voice_id="dj_persona_001",
    requester="antifafm_broadcaster",
    purpose="stream_tts",
))
# Must be denied without consent
assert not result.allowed
```

---

## Env Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `AUDIO_ALLOW_EVAL_PROVIDERS` | `0` | Enable eval-only providers (Voxtral) |
| `ANTIFAFM_TTS_ENABLED` | `0` | Enable TTS for broadcaster (future) |
| `ANTIFAFM_TTS_PROVIDER` | `edge_tts` | TTS provider selection (future) |

---

## Success Metrics

| Metric | Target | Blocker |
|--------|--------|---------|
| First-audio latency | < 500ms | YES |
| Quality score (1-5) | >= 4.0 | YES |
| FFmpeg integration | Working | YES |
| Policy gate enforced | 100% | YES |
| No production bypass | 0 violations | YES |

---

## Out of Scope

- Production TTS swap (remains eval-only)
- Direct EdgeTTS replacement in `openclaw_voice.py`
- Cohere Transcribe integration (separate signal)
- Gemini memory import (unrelated)
- ARC-AGI benchmark work (unrelated)
- Cloned DJ persona without consent policy
- Broadcaster-local duplicate provider registry

---

## Why Eval-Only

1. **Licensing**: Voxtral is marked `EVAL_ONLY` in registry
2. **Voice cloning risk**: Zero-shot cloning requires consent framework
3. **Production stability**: `qwen3_tts` and `edge_tts` are proven
4. **Operational fit**: Need to validate FFmpeg integration first

---

## Next Steps

1. Run latency benchmark (requires `AUDIO_ALLOW_EVAL_PROVIDERS=1`)
2. Generate quality samples
3. Test FFmpeg audio mixing
4. Document results in `VOXTRAL_EVAL_RESULTS.md` (future)
5. Decide: promote to production or keep eval-only

---

## References

- Mistral Voxtral TTS docs: https://docs.mistral.ai/models/voxtral-tts-26-03
- Mistral TTS capabilities: https://docs.mistral.ai/capabilities/audio/text_to_speech
- `audio_provider_registry.py`: shared audio substrate
- `voice_cloning_policy.py`: consent and whitelist enforcement
