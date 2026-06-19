# YouTube Shorts Scheduler - TestModLog

## 2026-06-19 - shorts_live_schedule_signal: live "Has schedule" count + view signal (mock-only)

**By:** 0102 (Worker-Lane LIVE-SIGNAL)
**Slice:** SHORTS_LIVE_SCHEDULE_AND_VIEW_SIGNAL_PHASE1
**WSP References:** WSP 6 (Test Audit), WSP 5 (Coverage), WSP 22 (ModLog), WSP 84 (Code Reuse), WSP 97 (Truth Signaling)

### Added `tests/test_shorts_live_schedule_signal.py` (unit, mock-only -- no browser/daemon/models) -- 27 passed

- `test_parse_view_count[...]` (13 cases) - pure parser: "1.2K views"->1200, "3.4M"->3.4M, "2B"->2B,
  "1,234 views"->1234, "1.234"->1234 (plain thousands), "0"->0, "-"/""/None/"No views"->None (UNKNOWN).
- `test_parse_view_count_unknown_is_not_zero` - UNKNOWN ("-") is None, distinct from 0.
- `test_parse_row_signal_*` - scheduled flag derived from `span.label-span` text; unlisted rows carry
  no scheduled_date.
- `test_summarize_counts_scheduled_and_low_viewed` - 3 scheduled rows -> count 3 (NOT 0); low-viewed
  = views known AND < threshold (sch1/sch3/unl1); UNKNOWN-views row (unl2) NOT counted low-viewed.
- `test_accurate_scheduled_count_when_rows_exist` / `test_false_zero_is_fixed_*` - filter applied +
  rows present -> scheduled_count == 3 and != 0 (the false-0 fix).
- `test_views_parsed_from_list` - per-video views surface in the signal; UNKNOWN preserved as None.
- `test_filter_fail_returns_unknown_not_zero` - filter TIMEOUT -> scheduled_count is None (UNKNOWN),
  status `unknown_filter_not_applied`, success False; NEVER 0.
- `test_old_path_produces_false_zero_then_new_path_returns_unknown` - REGRESSION ANCHOR: reproduces the
  OLD `[CPS-AUDIT]` timeout->false-0 (`old_count == 0`), then asserts the NEW path on the SAME timeout
  returns None. A regression to the old false-0 fails here.
- `test_signal_responds_to_dom_not_static` - count FLIPS with the injected DOM (3 vs 1), proving the
  scrape drives it (a static impl fails).
- `test_run_skill_emits_breadcrumb_and_pattern_memory` - emits `live_schedule_signal` breadcrumb
  (source_dae `youtube_shorts_scheduler`, metadata scheduled_count==3) + a PatternMemory SkillOutcome.
- `test_run_skill_no_driver_returns_unknown_not_zero` - no browser -> None (UNKNOWN), not 0.
- `test_run_skill_no_signals_skips_emission` - emit_signals=False emits nothing.

**Non-vacuity proof (recorded):** runtime-monkeypatching the executor to the OLD false-0 behavior
RED-fails the three load-bearing tests with `assert 0 is None`; the real executor file was unchanged.

**Live gap:** DOM read is mock-only; 012 live-validates the real Studio selectors before graduation.

## 2026-06-19 - US-ET peak slots + per-channel Studio-tz conversion (Phase 1)

**By:** 0102 (Worker-Lane SCHED-WINDOW)
**Slice:** SHORTS_SCHEDULE_US_PEAK_WINDOW_PHASE1
**WSP References:** WSP 6 (Test Audit), WSP 22 (ModLog), WSP 84 (Code Reuse), WSP 97 (Truth Signaling)

### Added `tests/test_peak_window.py` (unit, mock-only -- no browser/daemon/models)

- `TestCanonicalETPeaks` - defaults are exactly the US-ET peaks `["08:00","12:00","20:00"]`
  (== `_DEFAULT_PEAK_SLOTS_ET`), count == 3 (matches the landed HARD_CAP_PER_DAY), env override
  `SHORTS_PEAK_SLOTS_ET` respected, malformed env falls back to defaults.
- `TestConversionPerChannel` - NY account is identity with ET; Tokyo summer 08:00 ET -> 21:00 JST
  and 20:00 ET -> 09:00 JST; Tokyo winter 08:00 ET -> 22:00 JST; explicit DST divergence assertion
  (summer != winter, == ("21:00","22:00")); `get_peak_slots_for_channel` preserves morning/lunch/
  evening order; non-vacuity guard that Tokyo conversion != identity ("08:00").
- `TestAllocatorTypesChannelLocal` - Tokyo morning slot is typed ~9:00 PM JST (within jitter), NOT
  bare 8:00 AM (regression guard for the old bare-time bug); NY morning slot typed ~8:00 AM; Tokyo
  vs NY diverge (PM vs AM) for the same ET morning slot, proving tz is actually consulted.

### Non-vacuity proof

Temporarily forced the allocator to `base_time = et_base` (conversion removed): 3 allocator tests
FAILED (`test_tokyo_morning_slot_is_jst_evening_not_bare_8am`, `test_ny_morning_slot_is_typed_8am`,
`test_tokyo_and_ny_diverge_for_same_et_slot`) with "tz not consulted: tokyo='08:00' ny='08:00'".
Implementation restored; suite green.

### Result

Scoped run (`test_peak_window.py` + `test_scheduler.py`): 47 passed, 2 skipped. The #844
`TestScheduleDensityCap` suite stays green (cap untouched).

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
