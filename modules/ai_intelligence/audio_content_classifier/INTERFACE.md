# INTERFACE - audio_content_classifier (WSP 11)

> R&D PoC. NOT wired into scheduling. Read-only w.r.t. the system.

## Public surface

```python
from modules.ai_intelligence.audio_content_classifier.src.audio_content_classifier import (
    classify_content,
    ClassificationResult,
    extract_acoustic_features,   # exposed for the live entrypoint / tuning
    aggregate_stt_signals,       # exposed for fusion + testing
)
```

## `classify_content`

```python
classify_content(
    audio_or_video_path: str,
    *,
    transcript: Optional[str] = None,
    segments: Optional[list[dict]] = None,
    sample_rate: int = 16000,
) -> ClassificationResult
```

- **audio_or_video_path**: path to a local `.wav`/`.mp3`. (A YouTube `video_id`
  fetch path is exercised only by `scripts/live_classify.py`, not by this
  function, to keep the module hermetic.)
- **transcript** *(optional)*: transcript text. Reserved for the OPTIONAL Gemma
  tie-breaker in the live entrypoint; accepted so the contract is stable and
  testable. Does not affect the acoustic decision.
- **segments** *(optional)*: list of whisper segment dicts. Recognized keys:
  `no_speech_prob`, `compression_ratio` (openai-whisper standard). When supplied,
  enables `acoustic+stt_fusion` AND makes the decision deterministically
  unit-testable without running a model.
- **sample_rate** *(optional)*: assumed sample rate of the loaded waveform.

### Returns: `ClassificationResult`

| field | type | meaning |
|---|---|---|
| `label` | `'music' \| 'talk'` | predicted dominant content (`'talk'` is the fail-safe default) |
| `confidence` | `float` 0.0-1.0 | `0.0` means **unavailable** (no decision made); success is in `[0.5, 1.0)` |
| `method` | `'acoustic' \| 'acoustic+stt_fusion' \| 'unavailable'` | which signal path produced the result |
| `signals` | `dict` | feature values that drove the decision |

### `signals` keys

Always present on a successful (non-`unavailable`) result:

`spectral_flatness`, `harmonic_percussive_ratio`, `zero_crossing_rate`,
`tempo_bpm`, `beat_strength`, `rms_dynamic_range`, `mfcc_var`, `_score`.

Present only when whisper segments are supplied/available:

`avg_no_speech_prob`, `avg_compression_ratio`.

## Fail-safe contract

`classify_content` **never raises into the caller and never hangs**. On a missing
file, missing dependency (e.g. `librosa`/`numpy` absent), or an audio
load/extraction failure, it returns:

```python
ClassificationResult(label="talk", confidence=0.0, method="unavailable", signals={...partial...})
```

## Helper functions

```python
extract_acoustic_features(wav_float32_mono_16k, sample_rate=16000) -> dict
# librosa-based; raises ImportError if librosa/numpy absent (caller guards it).

aggregate_stt_signals(segments: Optional[list[dict]]) -> dict
# mean no_speech_prob / compression_ratio over segments; {} when none usable.
```

## Isolation guarantees (WSP 49 / #819-#820)

- No import of, and no import by, `youtube_shorts_scheduler`.
- No write/re-index/delete of any index artifact.
- All heavy/optional integrations (`librosa`, `whisper`, `VideoArchiveExtractor`,
  Gemma, the LLM `content_category` oracle) are **lazy-imported** behind guards;
  the module imports cleanly with zero heavy deps installed.

## Tunability

Decision thresholds + weights are externalized in `src/feature_thresholds.py`.
Overriding a constant changes the decision boundary without editing logic.
