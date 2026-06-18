# audio_content_classifier (R&D PoC)

> [!WARNING]
> **R&D PoC ONLY - NOT WIRED INTO SCHEDULING.**
> Slice: `RND_MUSIC_VS_TALK_DETECTION_POC` | Worker-Lane: `RND-MUSIC-TALK`
> This module is an isolated proof-of-concept. It MUST NOT be imported by, or
> import from, `modules/platform_integration/youtube_shorts_scheduler`. It does
> NOT change the scheduler gate, does NOT change the `executor.py` taxonomy, and
> does NOT add a content_type branch to the live gate. It is read-only with
> respect to the system: it reads audio/artifacts and never writes, re-indexes,
> or deletes the index artifact (honoring the #819/#820 decoupling contract).

## Purpose

Answer one question about a short, at the **signal level**: is the dominant
content **music** or **talk** (a person speaking)?

This is **Approach B**: a `librosa`-based acoustic music/speech discriminator,
optionally **fused** with `openai-whisper` segment `no_speech_prob` /
`compression_ratio`.

## Why acoustic (the lyrics-as-text confound)

Text-only methods (transcript keyword gates, Gemma-on-transcript) are fooled by
**sung lyrics**: a Suno song with words transcribes to words and looks like
"talk". At the signal level, sung lyrics stay **acoustically music** (sustained
harmonics, steady beat, low zero-crossing-rate). Deciding on the waveform means
text presence does not flip the label. This is the only candidate approach
immune to the lyrics confound, which is why it was selected for the PoC over:

- **A. Reuse the existing LLM `content_category` label** (Gemini analyzer /
  Studio Ask twin) - usually **absent** for unlisted scheduler shorts (stub
  artifacts with empty `transcript_summary`), and an unvalidated emergent prompt
  property. Reused here only as a live **oracle** for agreement, not a build dep.
- **C. Gemma on transcript text** - by construction can only see lyrics-as-text;
  kept as an OPTIONAL secondary tie-breaker behind a flag, never primary.

## Install note

- `librosa` (>= 0.11) and `openai-whisper` are **already present** in this repo's
  environment (verified: librosa 0.11.0, numpy 2.4.4, openai-whisper importable).
- `faster-whisper` is **intentionally NOT** a dependency (it is not installed).
- The LIVE video-id path additionally needs `yt-dlp` + `ffmpeg` (+ `soundfile`)
  for `VideoArchiveExtractor.extract_audio` - required only by the live
  entrypoint, **never** by the unit tests.

## How to run (live, NOT pytest)

```bash
# Local clip:
python -m modules.ai_intelligence.audio_content_classifier.scripts.live_classify --path clip.wav --whisper

# YouTube video id (reuses VideoArchiveExtractor; close live Chrome/Edge first):
YT_DLP_COOKIES_BROWSER=chrome \
  python -m modules.ai_intelligence.audio_content_classifier.scripts.live_classify --video-id VIDEOID --whisper --json
```

The live script prints predicted label, confidence, full signals dict, method,
and - when an index artifact exists - the existing Gemini/Studio
`content_category` as an independent **oracle** for agreement.

## Public API

```python
from modules.ai_intelligence.audio_content_classifier.src.audio_content_classifier \
    import classify_content, ClassificationResult

result = classify_content("clip.wav", segments=whisper_segments)  # segments optional
# ClassificationResult(label='music'|'talk', confidence=0.0-1.0, method=..., signals={...})
```

See `INTERFACE.md` for the full WSP 11 contract.

## WSP 84 reuse map (cited)

| Reused capability | Source (file:line) |
|---|---|
| librosa MFCC/feature pattern | `modules/platform_integration/acoustic_lab/src/acoustic_processor.py:160` |
| 16kHz mono audio fetch (unlisted cookies) | `modules/platform_integration/youtube_live_audio/src/youtube_live_audio.py:405` (cookies at `:451`) |
| whisper segment dicts (no_speech_prob/compression_ratio) | openai-whisper `transcribe` standard |
| Gemma transcript tie-breaker (optional) | `modules/ai_intelligence/video_indexer/src/gemma_segment_classifier.py:63` (bracket keywords `:99-101`) |
| LLM content_category oracle (live cross-check only) | Gemini analyzer / `studio_ask_indexer` `content_category` |

## Tunability

All decision thresholds + weights live in `src/feature_thresholds.py` so the
live eval and 012 can calibrate boundaries **without touching decision logic**.
The unit test `test_thresholds_externalized` proves overriding a constant moves
the boundary.

## What is deferred to live validation

Unit tests are hermetic (mocked features + injected whisper segment dicts; no
model, no audio, no network). Real-audio accuracy, threshold calibration, and
the confound-subset acceptance gate are validated by 012 via the live entrypoint
on a labeled set - see `tests/TestModLog.md` and `ModLog.md`.
