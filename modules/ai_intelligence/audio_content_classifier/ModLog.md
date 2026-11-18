# ModLog - audio_content_classifier

## 2026-06-19 - PoC creation (Slice: RND_MUSIC_VS_TALK_DETECTION_POC)

**Worker-Lane**: RND-MUSIC-TALK
**Branch**: rnd/music-vs-talk-detection-poc (off origin/main)
**WSP**: WSP 00 (zen), WSP 22 (this log), WSP 49 (module structure),
WSP 84 (reuse-first), WSP 97 (truth boundary / isolation), WSP 11 (interface).

### What was built

An ISOLATED R&D PoC: `audio_content_classifier`, an acoustic music-vs-talk
discriminator (Approach B). It decides on the **waveform** (librosa) and
optionally **fuses** openai-whisper segment `no_speech_prob` /
`compression_ratio`, so sung lyrics that transcribe as words still classify as
`music` (the lyrics-as-text confound text-only methods fail).

Files:
- `src/audio_content_classifier.py` - `classify_content`, `extract_acoustic_features`,
  `aggregate_stt_signals`, `_decide`, `ClassificationResult`. All heavy ops behind
  lazy imports + guards; fail-safe `method='unavailable'` on missing file/deps.
- `src/feature_thresholds.py` - externalized `THRESHOLDS` + `WEIGHTS` with per-feature
  provenance, so the live eval calibrates boundaries without touching logic.
- `tests/test_decision_logic.py` - hermetic decision tests incl. the confound test.
- `tests/test_classify_contract.py` - hermetic API/contract + fail-safe tests.
- `scripts/live_classify.py` - the ONLY place real models/audio run (NOT pytest).
- `README.md`, `INTERFACE.md`, `requirements.txt`, `tests/README.md`,
  `tests/TestModLog.md`.

### Why Approach B (and not A or C)

- **A (reuse the existing LLM `content_category` label)**: usually ABSENT for
  unlisted scheduler shorts (stub artifacts have empty `transcript_summary`;
  scheduler decoupled per #819/#820) and is an unvalidated emergent prompt
  property, not a calibrated detector. Reused only as a live **oracle** for
  agreement, not as a build dependency.
- **C (Gemma on transcript text)**: by construction sees lyrics-as-text and is
  fooled by sung words / spoken-word; kept as an OPTIONAL secondary tie-breaker
  behind a flag in the live entrypoint, never primary.
- **B**: only candidate runnable offline today with zero new deps (librosa 0.11.0
  + openai-whisper verified installed; faster-whisper intentionally avoided) and
  robust to the confound at the signal level. Occam layer discipline: one
  validated signal-level layer first; fuse A/C only if the eval demands it.

### WSP 84 reuse map (cited file:line)

- librosa MFCC/feature pattern: `acoustic_lab/src/acoustic_processor.py:160`.
- 16kHz mono audio fetch (unlisted-cookie support):
  `youtube_live_audio/src/youtube_live_audio.py:405` (cookies `:451`).
- whisper segment dicts (`no_speech_prob`/`compression_ratio`): openai-whisper
  `transcribe` standard, consumed as injectable fusion signals.
- Gemma transcript tie-breaker (optional): `video_indexer/src/gemma_segment_classifier.py:63`
  (bracket keywords `:99-101`).

### Isolation contract (#819/#820, WSP 49/97)

MUST NOT import from / be imported by `youtube_shorts_scheduler`. No edit to the
scheduler gate, no change to `executor.py` `classify_content` taxonomy, no new
content_type branch in the live gate. Read-only: never writes/re-indexes/deletes
the index artifact. Promotion to scheduling is OUT OF SCOPE - only after the live
eval passes would a SEPARATE, separately-reviewed slice precompute a music/talk
label into the artifact the read-only gate already consumes.

### Tests

Scoped unit tests pass (mocked features + injected whisper segment dicts; no
model, no audio, no network). See `tests/TestModLog.md` for the run summary.

### Deferred to live validation (012, via scripts/live_classify.py)

Real-audio accuracy on a labeled set (~30-50 shorts oversampling the confound
classes: instrumental FFCPLN, sung-lyrics Suno, rap/spoken-over-beat, plain
talking-head), threshold calibration in `feature_thresholds.py`, oracle agreement
%, and the sung-lyrics acceptance gate. Target: >=90% overall AND sung-lyrics
correctly called `music` on the majority of that subset. No scheduling change
ships regardless of eval outcome.
