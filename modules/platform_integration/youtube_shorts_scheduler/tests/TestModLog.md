# YouTube Shorts Scheduler - TestModLog

## 2026-06-16 - Index<->Metadata Decoupling tests (Phase 1)

**By:** 0102 (Worker-Lane SSIMD-AUTHOR)
**Slice:** SHORTS_SCHEDULER_INDEX_METADATA_DECOUPLING_PHASE1
**WSP References:** WSP 6 (Test Audit), WSP 22 (ModLog), WSP 97 (Truth Signaling)

### Added

`tests/test_index_metadata_decoupling.py` - proves the Phase 1 read/write split:

- CONTROL 1 - INDEXING does NOT call `edit_title` (FAILS on old code: old `edit_title.call_count==1`).
- CONTROL 2 - INDEXING does NOT call `edit_description` (FAILS on old code: old `edit_description.call_count==1`).
- CONTROL 3 - INDEXING does NOT call `schedule_video`. HONESTY FLAG: old `run_indexing_cycle`
  already skipped scheduling, so this passes on both old and new; it is discriminating only when
  PAIRED with CONTROL 7 (positive `schedule_video` call on the same strict-double type).
- CONTROL 4 - INDEXING does NOT access/resolve `save_video`. Strict `spec_set` double of
  `YouTubeStudioDOM` has no `save_video`; old code accessed it (latent AttributeError surfaced).
  `save_video` is NOT invented (no `create=True`, no loose Mock).
  Records: SAVE_VIDEO_LATENT_BUG_REMOVED_FROM_INDEXING_PATH.
- CONTROL 5 - scheduler READ path does NOT call `ensure_index_json` (FAILS on old code:
  old `_update_video_metadata` called `ensure_index_json` once with a present artifact).
- CONTROL 6 - scheduler READ path does NOT import/instantiate `GeminiVideoAnalyzer`
  (`sys.modules` import guard that raises on construction).
- CONTROL 7 - EXPLICIT scheduling path STILL writes `edit_title`/`edit_description`/`schedule_video`
  (positive regression anchor; MUST pass on both old and refactored code).
- PURE BUILDER (present artifact) - `build_index_metadata_context` returns a populated
  `MetadataContext`, takes no dom/driver, and never calls `ensure_index_json`/`save_index_json`/
  `create_stub_index_json` or imports `GeminiVideoAnalyzer`.
- PURE BUILDER (missing artifact) - returns None ("skip enhancement", NOT index now), with
  `ensure_index_json`/`save_index_json` uncalled.

### Anti-vacuity

Strict `spec_set` MagicMock against the REAL `YouTubeStudioDOM` interface; no invented methods.
Each negative control asserts the loop body executed (`navigate_to_video('vid1')`) before asserting
a sink (non-)call, so `dry_run` short-circuits cannot make "not called" vacuous. No browser, no live
YouTube, no credentials. ASCII-only.

### Results

- New file: 9 passed.
- Module suite (`test_scheduler.py` + new file): 36 passed, 2 skipped, 3 FAILED.
  The 3 failures are PRE-EXISTING and unrelated to this slice: `TestChannelConfig::
  test_get_channel_config_move2japan` and two `TestScheduleTracker` slot tests assert stale
  time-slot expectations against `channel_config.py`/`schedule_tracker.py`, both byte-identical to
  base (this slice touches only `scheduler.py` and `index_weave.py`).

---
