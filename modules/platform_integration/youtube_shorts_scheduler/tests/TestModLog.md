# YouTube Shorts Scheduler - TestModLog

## 2026-06-16 - Pin video-index context consumption on the scheduling path (Phase 1)

**By:** 0102 (Worker-Lane SSVCC-AUTHOR)
**Slice:** SHORTS_SCHEDULER_VIDEO_INDEX_CONTEXT_CONSUMPTION_COVERAGE_PHASE1
**WSP References:** WSP 6 (Test Audit), WSP 22 (ModLog), WSP 84 (Code Reuse), WSP 97 (Truth Signaling)
**Basis:** #820 ALREADY built the artifact-consumption path; this PINS it (no rebuild).

### Added (extend `tests/test_index_metadata_decoupling.py`, reuse the existing harness)

- TEST A `test_scheduling_path_missing_artifact_writes_base_content` - `run_scheduling_cycle`
  with NO artifact: reachability (`navigate_to_video('vid1')`) FIRST; `edit_title`/`edit_description`/
  `schedule_video` STILL fire (`schedule_video.call_count == 1`); the `edit_description` argument
  equals the pinned BASE sentinel (no twin marker `0102 DIGITAL TWIN INDEX`, none of the index
  hashtags `#Mindfulness`/`#Zen`); no scheduler-owned indexing (bound `save_index_json` spy never
  fires, `GeminiVideoAnalyzer` never constructed, no artifact file on disk); structural proof that
  `ensure_index_json`/`create_stub_index_json` are NOT bound in the scheduler namespace.
- TEST B `test_scheduling_path_present_artifact_weaves_index_context` - `run_scheduling_cycle` with a
  PRESENT artifact (topics `[Mindfulness, Zen]`, key_points populated): reachability FIRST;
  `edit_description` includes the index context (`Breathe and be present.`), >=1 woven index hashtag,
  AND the twin block; `schedule_video.call_count == 1`. Cross-check: `run_indexing_cycle` over the
  same harness yields `schedule_video.call_count == 0` (scheduling write is invoked ONLY from the
  explicit scheduling path; pairs with Control 3/7).
- TEST B (env-gate complement) `test_scheduling_path_present_artifact_disabled_skips_enhancement` -
  PRESENT artifact + `YT_SCHEDULER_INDEX_WEAVE_ENABLED=false` -> twin block ABSENT (proves the TEST B
  twin assertion is env-gated, not unconditional).
- Observability `test_update_metadata_logs_index_context_marker` - asserts the
  `index_context=present|missing|disabled` token only (via caplog), never content/transcript.

### Non-vacuity

TEST A FAILS if the missing-artifact path were (re-)coupled to indexing (bound `save_index_json`
side-effect raises, or an artifact appears on disk) or if base content were enhanced (twin/hashtag
assertion fires). TEST B FAILS if consumption became a no-op/None (the PRESENT twin/context/hashtag
markers would be absent) or if scheduling fired from a read path. `get_standard_description` is
randomized, so TEST A pins the BASE via a deterministic stub of the BOUND scheduler name. Strict
`spec_set` DOM double, `dry_run=False`, `read_edit_page_visibility -> "unlisted"`. No browser, no
live YouTube, ASCII-only. No skip/xfail.

### Pre-existing unrelated failures (NOT mine)

`test_scheduler.py` 3 failures (`test_get_channel_config_move2japan` time-slots 8 vs 3;
`test_get_next_available_slot_empty`/`_partial` time-of-day-dependent slot values) are byte-identical
to base (`test_scheduler.py` unchanged in this diff). Classified by reading tracebacks; never stashed.

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
