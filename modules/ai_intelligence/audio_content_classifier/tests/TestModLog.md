# TestModLog - audio_content_classifier

## 2026-06-19 - Initial hermetic unit suite (Slice: RND_MUSIC_VS_TALK_DETECTION_POC)

**Command**:
```
python -m pytest modules/ai_intelligence/audio_content_classifier/tests/ -q
```

**Result**: `14 passed in 0.32s`

**Coverage of decision logic (non-vacuous, no model / no audio / no network)**:

| test | asserts |
|---|---|
| test_decide_pure_music_features | instrumental features -> `music`, conf > 0.7, method `acoustic` |
| test_decide_pure_speech_features | speech features -> `talk`, conf > 0.7, method `acoustic` |
| test_lyrics_confound_sung_words | acoustically-music + transcribed words + high `avg_no_speech_prob` -> STILL `music` (confound defense) |
| test_rap_spoken_over_beat | strong-beat tie-break -> `music`, method `acoustic+stt_fusion` |
| test_thresholds_externalized | overriding a `feature_thresholds` constant moves the boundary |
| test_aggregate_stt_signals_empty | no/malformed segments -> `{}` (acoustic-only), never raises |
| test_module_imports_without_heavy_deps | module reload imports cleanly (guarded lazy deps) |
| test_classify_content_mocks_extractor | extractor + load mocked -> features flow to `_decide` |
| test_classify_content_fusion_via_segments | injected segments -> method `acoustic+stt_fusion` |
| test_failsafe_missing_file | missing path -> `talk`/0.0/`unavailable`, no exception |
| test_failsafe_missing_deps | simulated `ImportError` on librosa -> `unavailable`, no hang/raise |
| test_failsafe_audio_load_failure | `librosa.load` raising -> `unavailable` |
| test_signals_dict_keys_present | every documented acoustic signal key present |
| test_classification_result_shape | result fields match the WSP 11 contract |

**AST check**: `py_compile` OK on all `src/`, `scripts/`, `tests/` files.
**ASCII check**: all source + doc files 0 non-ASCII bytes (`.pyc` caches gitignored).

## Deferred to LIVE validation (012, NOT pytest)

Run via `scripts/live_classify.py` on a 012-labeled set (~30-50 real shorts,
oversampling confound classes: instrumental FFCPLN, sung-lyrics Suno,
rap/spoken-over-beat, plain talking-head). Score a confusion matrix vs
`true_label`, overall accuracy, and **per-confound-class** accuracy. The
sung-lyrics row is the acceptance gate. Target: >=90% overall AND sung-lyrics
correctly called `music` on the majority of that subset. Calibrate via
`feature_thresholds.py` constants and re-run; logic untouched. Cross-check the
existing Gemini/Studio `content_category` oracle for agreement where present.
Record live results here when run.
