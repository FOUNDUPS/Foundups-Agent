# Headless Video Orchestrator - Interface

## Public API

### `HeadlessVideoOrchestrator` (`src/orchestrator.py`)

`MusicVideoRequest` adds optional `render_profile` (`"legacy"` default or `"staging_720p"`), `max_duration_sec` (default `178.5`, strictly `<180.0` for Shorts staging), and `audio_fade_out_sec`. Profile, orientation, 4K refusal, and `<180.0s` bounds are validated upfront **before** any FFmpeg subprocess runs. `_overlay_audio` explicitly maps `0:v:0` and `1:a:0` with finite timeouts and Windows `CREATE_NO_WINDOW`.

### Antifa FM Staging & Benchmark Utilities (`src/media_signal_audit.py`, `src/antifafm_staging.py`)

- `probe_media_artifact(path) -> dict`: SHA256, container/stream durations, geometry/fps, and explicit `subtitle_streams` / `has_embedded_subtitles`.
- `parse_embedded_srt(srt_text, *, max_audio_duration_sec=None) -> dict`: Separates positive-duration `lyric_cues` from zero-duration or bracketed `[...]` `stage_directions`; `audio_alignment_verified` remains `False`.
- `compare_audio_sources(path_a, path_b) -> dict`: Compares decoded 16kHz mono RMS envelope correlation and duration delta across containers (e.g. `.m4a` vs `.mp3`).
- `analyze_audio_16k_mono(path, *, quantile=0.85, preferred_max_sec=178.5, hard_limit_sec=180.0) -> dict`: Computes 16kHz mono normalized RMS and `normalized_rms_positive_first_difference` quantiles (`selection_threshold_validated=False`, `musical_ending_verified=False`).
- `audit_satire_claims(claims) -> dict`: Fails closed on unverified factual assertions (`numeric_stat`, `benefit_claim`, `constitutional_legal`, `phone_number`, `allegation`) and official Onion/Spy affiliation claims.
- `render_benchmark_excerpt(...) -> dict`: Validates every source frame's dimensions, renders deterministic `720x1280` or `1280x720` `24fps` `H.264/yuv420p` `AAC 192k` excerpts (reusing `VideoEditor` with isolated temp dir for multi-segment stitches), and writes `antifafm_cut_manifest.v1` JSON. Still pan/zoom is labeled `camera_only`; multi-hash sequences are labeled `multi_image_sequence_unreviewed` (`true_character_animation=False` until independent human/peer visual evaluation). Native crop ratios `<1.0` set `upscale_interpolation_warning=True`. `rsi_promotion_status` stays `"candidate_unpromoted"`.
- `verify_rendered_output(video_path, ...) -> dict`: Runs full `ffmpeg -f null -` decode with `blackdetect`/`freezedetect`, H264/yuv420p/AAC/frame-count/`<180s` and per-channel PCM sample-peak checks (`stereo_true_peak_certified=False`, `visual_and_listening_review_verified=False`). Black or frozen (`>=2.5s`) cuts fail closed (`FAILED_TECHNICAL_VERIFICATION`); passing technical checks return `TECHNICAL_DECODE_PASSED_REVIEW_REQUIRED`.
- `plan_daily_publish_slots(...)` & `stage_antifafm_daily_candidate(...)`: Reuses `ScheduleTracker(..., persist=False).preview_copy()` with `max_per_day=1` (`calendar_inventory_qualified=False` unless Studio inventory is complete), enforces canonical Antifa FM channel `UCVSmg5aOhP4tnQ9KFUg97qA`, blocks duplicate SHA256s, and refuses `dry_run is not True` before any uploader/service construction.
