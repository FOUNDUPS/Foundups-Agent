# tests - audio_content_classifier

Hermetic unit tests for the music-vs-talk PoC. **No live models, no real audio,
no network.** Every test injects crafted feature vectors and/or whisper segment
dicts and asserts the real decision logic.

## Run (scoped)

```bash
python -m pytest modules/ai_intelligence/audio_content_classifier/tests/ -q
```

## Files

- `test_decision_logic.py` - core `_decide` behavior:
  - pure-music features -> `music` (confidence > 0.7)
  - pure-speech features -> `talk` (confidence > 0.7)
  - **lyrics confound**: acoustically-music features + transcribed words +
    high `avg_no_speech_prob` -> still `music` (the key proof)
  - rap/spoken-over-beat tie-break -> `music`, method `acoustic+stt_fusion`
  - thresholds externalized: overriding a constant moves the boundary
  - stt aggregation edge cases
- `test_classify_contract.py` - `classify_content` wiring + fail-safe:
  - extractor + audio load mocked -> features flow to `_decide`
  - segments flip method to `acoustic+stt_fusion`
  - fail-safe: missing file / missing deps / audio load failure -> `unavailable`
  - documented signal keys present; result shape matches contract

## Why no `importorskip` on heavy models

Extraction and STT are always mocked or injected, so the tests never need
librosa/whisper at runtime. The module also imports cleanly with zero heavy deps
(guarded lazy imports), which is asserted directly.

## What is NOT tested here (deferred to live)

Real-audio accuracy, threshold calibration, and the confound-subset acceptance
gate run via `scripts/live_classify.py` on a 012-labeled set. See `TestModLog.md`.
