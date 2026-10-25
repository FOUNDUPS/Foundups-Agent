Warning: truncated output (original token count: 36517)
Total output lines: 2841

# YouTube Shorts Scheduler - ModLog

## 2026-10-25 — Dual-surface scheduling training procedure

WSP 22/50/84/97. Reuses ContentPageScheduler and detail-page DOM automation;
no executable behavior, default selection or scheduling configuration changed.
REMOTE_SCHEDULING now distinguishes popup save from detail Done + page Save,
requires exact-ID/date/time/timezone readback, preserves metadata for schedule-only
requests, and records 012's Google push/number-match waiting boundary. Records
aggregate detail-page and Content-table observations reported by the coordinating
Work browser, without private video IDs or individual release slots. This is
separate from local transport qualification, model training and backlog completion.

Retrieval: source-bound lexical bundle at 7384448; workspace_head context,
freshness UNKNOWN, index_gap_detected=true. Relevant existing owner found first;
removed noisy general WSP hit by direct module reads. No semantic freshness or
training promotion claimed. V2 bootstrap attempted but torch unavailable; tracker
check returned compliant from its existing state. Documentation validation only:
relative links and git diff whitespace check; no live scheduler executed here.

## 2026-10-22 — PR1860 current-main scheduling reconciliation

WSP 00/6/10/11/15/22/50/84/97. C4/I4/D4/Impact4=16/P0.
Main `be7ce629b5f36382466432987eaf279b0e5bbc5c`; original PR
`d0c3c16f93d3956083a7ab8341de531e43cc7abd`. Isolated source maintenance,
not native worker execution or live publishing. Holo retrieval rejected the
checkout/head binding (UNKNOWN freshness/index gap); exact Git, module docs,
NAVIGATION and prior all-file audit supply the bounded fallback.

Preserves selected-clip CLI/adapter, nonpersistent preview, transcript language
and offsets, and dated source audits. Adds strict selected edit-page/visibility
checks, a 100-page discovery bound, attempt limits shared across visibility
passes, suppression of channel-wide sync for selected/preview requests, restored
preview tracker state, disabled preview diagnostic screenshots, and explicit success receipts. DOM imports no longer create a diagnostics directory. Preserve-metadata leaves
prior description-sync evidence unchanged; changed metadata requires independent
readback before claiming sync. Failed selected metadata updates do not schedule.
An obsolete rotation-test double now accepts the actual driver keyword without
weakening its budget assertions. Omitted `.en` model language remains English;
explicit incompatible language still fails through the existing factory.

The original hosted failure was a backend manifest digest-pin mismatch.
Regenerate current registry/manifest and both digest pins, retaining current
main's runtime members. Dedicated offline CI covers the connected path.
Validation evidence and remaining acceptance are recorded in tests/TestModLog.md;
merge/CI/main readback receipts belong to PR1860. No deployment/account effect.

## 2026-10-18 - Defer browser-only peak helper to scheduler execution

**By:** 0102
**WSP References:** WSP 22 (ModLog), WSP 84 (reuse), WSP 97 (evidence)

- Moved the existing `get_peak_slots_et` import from `scripts/launch.py` module
  scope into `run_multi_channel_scheduler`'s initial local imports, before any
  browser connection. Its sole call remains unchanged in that function.
- Importing general launcher entry points no longer loads `src.__init__`, the
  browser scheduler, or Selenium for this helper. This fixes an inherited
  dependency coupling exposed when social imports stopped eagerly reaching an
  incidental Selenium installer. Package exports, scheduling behavior and guards
  are unchanged.
- Added an isolated real-launcher import regression with browser imports and
  external actions denied. Old source failed; repaired source passed. One
  formerly failing resident-chain main-import test also passed without Selenium.
  See `tests/TestModLog.md`; no browser or scheduler execution was tested.
## 2026-09-21 - Repair existing remote adapter contract and preview isolation

WSP 00/11/22/50/84/95/97. Reused the scheduler and existing Red Dog adapter;
no replacement publisher. Corrected stale CLI constructor/method calls,
added transport-only preflight and metadata preservation, normalized JSON
planned/actual receipts, and respected payload failures. A shared attached
browser is detached rather than closed. Missing imports return JSON failures.

Preview trackers no longer create/write storage; slot preview deep-copies
the current tracker, dry-run cannot trigger postcycle autoheal, and preview
stops after the first visible batch. One limit covers all visibility passes.
The later Work audit located the existing `publish_daily_clips` prototype;
the proposed parallel remote skill registration was excluded from this branch.
The diagnostic skill points to that owner and its source-export boundary.

Actual adapter preflight returned `browser_unavailable` for Move2Japan/9222.
No YouTube mutation occurred. Metadata-plan binding, unattended
ingress and live saved-result proof remain outstanding; see
[remote runbook](docs/REMOTE_SCHEDULING.md). Offline regression evidence and
the existing channel-density configuration mismatch are in tests/TestModLog.

Retrieval evaluation: owner query failed `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`
(freshness UNKNOWN, index gap true). Direct source/Git checks were used.
Noise: broad YouTube hits include old live-content skills. Ordering: actual
callers/definitions before historical docs. Missing artifacts: video_indexer
memory README/requirements and actual clip transcripts. Staleness: branch
differs from inspected main. Duplication: existing adapter/scheduler reused.
Japanese STT primitives already present on inspected origin/main were reused
and extended through batch evidence rather than introducing another backend.
Manual interface repair was necessary to reproduce stale API calls and verify
their replacement against the actual scheduler and regression tests.

012 clarified that every recorded clip belongs in the request. Removed the
adapter's default five and CLI's default ten caps; both now default to all.
Added exact `video_ids` selection with existing Studio pagination, per-visibility
order, exclusion of unrelated uploads and explicit incomplete-batch receipts.
Tests exercise 3/8/13-clip execution with mocked DOM and 61-clip paginated preview.
No hard cap on total batch size is imposed; existing daily spacing is separate.

September 22 reconciliation: moved only this lane's changes to an isolated
main-based worktree. Unqualified remote CLI requests now stop with
`clip_selection_required` before connecting, preventing old backlog selection
while the existing Work prototype's source is retrieved. The requested recent
window and unresolved source/readback integration are recorded in
[the Work audit](docs/PRIOR_WORK_AUDIT_2026-09-22.md).

## 2026-06-20 - Unified Shorts+Videos live priority signal (flag-gated, fallback-safe)

**By:** 0102 (Worker-Lane: UNIFIED-PRIORITY)
**Slice:** YOUTUBE_ROTATION_UNIFIED_SHORTS_VIDEOS_SIGNAL_PHASE1
**WSP References:** WSP 22 (ModLog), WSP 49 (Structure), WSP 50 (Pre-Action),
WSP 84 (Code Reuse: content_type threads through to existing read_live_schedule_signal),
WSP 91 (unified breadcrumb per channel), WSP 97 (truth signaling)

### Why (the gap)

The live HAS_SCHEDULE signal from the previous slice
(YOUTUBE_SHORTS_ROTATION_LIVE_SCHEDULE_SIGNAL_PRIORITY_PHASE1) only handled Shorts.
Channels with a FULL Shorts schedule but an EMPTY Videos schedule had no mechanism
to be prioritized for Videos. The `YT_VIDEO_PROCESSING_ENABLED` gate already processes
Videos in the channel loop, but the order was the raw rotation order with no live signal.

### What changed

**`skillz/shorts_live_schedule_signal/executor.py`**
- Added `VALID_CONTENT_TYPES = frozenset({"short", "upload"})` constant.
- Added `_validate_content_type(content_type)` at module level.
- `read_live_schedule_signal()` gains `content_type: str = "short"` parameter.
  Validated at entry (Addendum I: CONTENT_TYPE_VALIDATED_SHORT_OR_UPLOAD): invalid
  content_type fails closed (scheduled_count=None, no URL built, no DOM access).
  DOM scan logic (HAS_SCHEDULE filter + row scrape) is REUSED unchanged for both
  content types (WSP 84). Result shape gains `content_type` and `content_type_valid` fields.

**`skillz/what_should_i_schedule/executor.py`**
- `build_live_count_fn(driver, *, content_type="short", ...)` gains `content_type`
  parameter. Threads through to `read_live_schedule_signal` call without duplicating
  DOM logic (WSP 84). Cache is per channel_id (one call per channel per pass,
  Addendum D: LIVE_SIGNAL_ONE_CALL_PER_CHANNEL_CONTENT_TYPE).

**`scripts/launch.py`**
- `_pass_video_ranking: dict` module-level store for pass-local videos ranking.
  Cleared at start of each `_prioritize_channels` call (no cross-pass contamination).
- `_prioritize_channels`: when `YT_VIDEO_PROCESSING_ENABLED=1` AND driver AND
  live signal enabled, also computes a Videos ranking via
  `build_live_count_fn(driver, content_type="upload")`. Stores in `_pass_video_ranking`.
  Shorts ranking is unaffected by Videos ranking failure (Addendum E systemic contract).
- `_emit_priority_breadcrumb` gains `channel_breadcrumbs` kwarg (Addendum G):
  per-channel low-cardinality signal summary (shorts/videos counts, sources, decision).
  No DOM text, no auth material.
- Videos loop: reads `_pass_video_ranking` per channel. If `total_deficit == 0` (live
  confirms sufficient), skips the video pass for that channel this cycle (priority-only;
  does NOT change scheduling behavior, Addendum F: VIDEO_PASS_PRIORITY_ONLY_NO_VIDEO_BEHAVIOR_CHANGE).

### Decision model
```
Shorts=0 (live) -> highest Shorts priority (unchanged from prior slice)
Videos=0 (live) AND YT_VIDEO_PROCESSING_ENABLED=1 -> highest Videos priority
Both empty -> Shorts first (deterministic)
Live check fails per-channel -> fallback that channel/dimension only (Addendum E)
Live check fails systemically -> all channels fallback for that dimension (Addendum E)
YT_VIDEO_PROCESSING_ENABLED=0 -> Videos live check NOT run (Addendum H)
```

### Tests added
`tests/test_unified_shorts_videos_priority.py` - 10 mock-only, non-vacuous tests.
`tests/test_live_schedule_signal_priority.py` - updated mocks to accept content_type.

All 69 tests pass (0 regressions).

---

## 2026-06-20 - Wire live HAS_SCHEDULE signal into rotation priority (flag-gated, fallback-safe)

**By:** 0102 (Worker-Lane: LIVE-PRIORITY)
**Slice:** YOUTUBE_SHORTS_ROTATION_LIVE_SCHEDULE_SIGNAL_PRIORITY_PHASE1
**WSP References:** WSP 22 (ModLog), WSP 49 (Structure), WSP 50 (Pre-Action),
WSP 84 (Code Reuse: calls existing read_live_schedule_signal, never duplicates DOM scan),
WSP 91 (breadcrumb now records which signal drove priority), WSP 97 (truth signaling)

### Why (the gap)
`_prioritize_channels` in `scripts/launch.py` drove the rotation order using only the
offline tracker JSON (`memory/schedule_<channel_id>.json`). If the tracker was stale or
out-of-sync with YouTube Studio, channels with 0 LIVE scheduled items were not
necessarily ranked first. The existing `shorts_live_schedule_signal` SKILLz already has
the correct DOM-scraping logic for the accurate "Has schedule" count, but it was not
wired into the priority ranking.

### What changed

**`skillz/what_should_i_schedule/executor.py`**
- Added `build_live_count_fn(driver, *, live_signal_fn=None)` (new factory function).
  Wraps `shorts_live_schedule_signal.read_live_schedule_signal` into a drop-in
  `count_fn` for `rank_channels_by_need()`. Per-channel result is cached (live DOM
  called once per channel per ranking call, not once per (channel, date) pair).
  - `scheduled_count == 0` (filter confirmed applied) -> return 0 for all date queries
    for that channel (maximum deficit override; channel ranks FIRST).
  - `scheduled_count is None` (filter failed / UNKNOWN) or any exception -> delegate
    to `_default_count_fn` (offline tracker) for that channel (fallback contract).
  - No hardcoded channel IDs; channel_id always comes from the ranking loop / registry.
  - DOM scan logic NOT duplicated (WSP 84): reuses `read_live_schedule_signal` as-is.
- Updated docstring (DATA SOURCE seam now describes the live wiring).

**`scripts/launch.py`**
- `_prioritize_channels(channels, driver=None)` gains an optional `driver` parameter.
  When `YT_SCHEDULE_PRIORITY_ENABLED=1` AND `YT_LIVE_SCHEDULE_SIGNAL_ENABLED=1` AND
  `driver` is not None: calls `build_live_count_fn(driver)` and injects the resulting
  `count_fn` into `rank_channels_by_need(**rank_kwargs)`. On any import/build error,
  `live_count_fn` stays None and the offline tracker is used (zero regression risk).
- Call site moved from BEFORE driver connect to AFTER driver connect + tab cleanup (so
  `driver` is available when the live flag is on).
- `_emit_priority_breadcrumb` gains `live_signal_active: bool = False` kwarg; the
  breadcrumb metadata now includes `ranking_signal` ("live_schedule_signal" vs
  "offline_tracker") so WRE/operator can audit which signal drove the decision.

### Flag summary
| Flag | Default | Effect |
|---|---|---|
| `YT_SCHEDULE_PRIORITY_ENABLED` | `0` (off) | Master gate: off -> original channel order unchanged |
| `YT_LIVE_SCHEDULE_SIGNAL_ENABLED` | `0` (off) | Secondary gate: off -> offline tracker only (no live DOM call) |
| both `1` + driver available | n/a | Live DOM check drives ranking; fallback per-channel if check fails |

### Fallback contract (never breaks)
- Per-channel: live check fails or returns UNKNOWN -> offline tracker used for that channel.
- Any exception in `build_live_count_fn` or `rank_channels_by_need` -> original `channels`
  list returned unchanged (existing `_prioritize_channels` safety net).
- `driver=None` -> offline tracker path (pre-slice behavior, identical).

### Tests added
`tests/test_live_schedule_signal_priority.py` - 9 mock-only, non-vacuous tests:
- Non-vacuity proof: OLD code (no count_fn injection) does not rank X first when live=0.
- Live=0 -> X ranked highest regardless of tracker count.
- Live=0 dominates over non-zero tracker.
- Live failure -> tracker fallback (no exception, channel not dropped).
- Filter UNKNOWN (None) -> tracker fallback (not treated as false-0).
- Flag off -> `build_live_count_fn` never called.
- Priority flag off -> original order returned.
- Cache: live signal called exactly once per channel per ranking call.
- End-to-end: `_prioritize_channels` with live=0 reorders rotation, breadcrumb shows live_signal_active=True.

All 50 existing tests in the three related test files pass unchanged (zero regression).

---

## 2026-06-19 - Optionally schedule PRIVATE Shorts too (flag-gated, default-off, private->public)

**By:** 0102 (Worker-Lane SCHED-PRIVATE)
**Slice:** SHORTS_SCHEDULE_INCLUDE_PRIVATE_PHASE1
**WSP References:** WSP 22 (ModLog), WSP 49 (Structure), WSP 50 (Pre-Action), WSP 84 (Code Reuse: the DOM/URL layer already accepts PRIVATE), WSP 97 (truth signaling / outward-action breadcrumb)

### Why (the UNLISTED-only gap)
The scheduling cycle only processed UNLISTED Shorts: `run_scheduling_cycle` navigated with
`navigate_to_shorts_with_fallback(channel_id, "UNLISTED")` (was `scheduler.py:317`), the batch
loop scraped via `get_unlisted_videos()` (was `scheduler.py:350/370`), and the edit-page guard
rejected anything not `unlisted`/`unknown` (was `scheduler.py:502`). 012 also wants PRIVATE
videos processed. Scheduling a PRIVATE video uses the YouTube Studio `PUBLISH_FROM_PRIVATE`
schedule radio (`dom_automation.py:144-145,240,246`) -> the video PUBLISHES PUBLIC at its slot.
That is OUTWARD-FACING, so the PRIVATE pass is **default-OFF** and opt-in only.

### Phase 0 (verified on origin/main `47a6aa437`)
- UNLISTED-only nav: `scheduler.py:317` (and re-navs `:366`, `:666`).
- Scrape under UNLISTED filter: `get_unlisted_videos()` is UNLISTED-hardcoded -- guard
  `ensure_visibility_filter("UNLISTED")` (`dom_automation.py:2522`) AND a JS row scan that
  requires `\bunlisted\b` (`dom_automation.py:2537-2540`). It returns `[]` under a PRIVATE
  filter, so it is NOT a drop-in private scraper.
- Edit-page guard: `scheduler.py:502` `if edit_vis not in ("unlisted","unknown")` rejects
  `private` (which `read_edit_page_visibility` returns at `dom_automation.py:1316-1317`).
- DOM layer ALREADY supports PRIVATE for nav + filter + schedule:
  `navigate_to_shorts_with_fallback(..., "PRIVATE")` (`dom_automation.py:1411-1437`, generic),
  `ensure_visibility_filter("PRIVATE")` (`:1324`), PRIVATE chip/url markers (`:294,306`),
  and the schedule radio IS `PUBLISH_FROM_PRIVATE` (private -> public). Confirmed.

### What changed (minimal; scheduler.py ONLY)
- **`_resolve_visibility_targets()`**: default `["UNLISTED"]`; when
  `YT_SCHEDULE_INCLUDE_PRIVATE == "1"` returns `["UNLISTED","PRIVATE"]` (strict `=="1"`;
  emits a warning that private->public is enabled). UNLISTED is always first.
- **`_run_visibility_pass(target, ...)`**: extracted the existing navigate + continuous batch
  loop verbatim, with the `"UNLISTED"` literal replaced by `target`. `run_scheduling_cycle`
  now runs this loop ONCE PER TARGET. The single `self.tracker` is shared across passes, so the
  per-day cap (3), peak window/tz, and rotation budget are SHARED (UNLISTED fills slots first,
  PRIVATE continues into the remainder -- no per-channel budget doubling).
- **`_scrape_videos_for_visibility(target)`**: UNLISTED delegates to the unchanged
  `self.dom.get_unlisted_videos()`; PRIVATE scrapes rows scheduler-side via
  `self.driver.execute_script` (mirrors the strict scan, keyed on `private`, excludes
  scheduled rows) -- WITHOUT modifying the DOM/URL layer. Precedent: `_get_all_videos`
  already scrapes scheduler-side.
- **Edit-page guard relaxed**: accepts `private` ONLY when the active pass is PRIVATE; the
  UNLISTED pass still rejects `private`.
- **Outward breadcrumb**: per private video scheduled, logs
  `[PRIVATE->PUBLIC] {video_id} scheduled to publish {date} {time}` (live + dry-run) so 012 can
  review each private->public action. Default-off => zero private scheduling unless flagged.

### Scope / follow-ups
- OUT OF SCOPE: long-form private (note as follow-up), indexing, the detector, the long-form
  path. The DOM/URL layer was NOT modified.

## 2026-06-19 - Long-form uses US-ET peak + per-channel Studio-tz conversion (match shorts)

**By:** 0102 (Worker-Lane LONGFORM-TZ)
**Slice:** LONG_FORM_TZ_PEAK_WINDOW_PHASE1  (#847 follow-up; closes the #859 TZ gap)
**WSP References:** WSP 22 (ModLog), WSP 49 (Structure), WSP 50 (Pre-Action), WSP 84 (Code Reuse: reuse `get_peak_slots_et` + `get_next_available_slot(channel_tz=...)` from #847, mirror the shorts path), WSP 97 (truth signaling)

### Why (the long-form TZ gap, closed)
The shorts path publishes at the US-ET peak for EVERY channel: `scheduler.py:90` uses
`get_peak_slots_et()` and `scheduler.py:457-461` passes `channel_tz=self.channel_tz` into
`tracker.get_next_available_slot(...)`, which DST-converts ET -> Studio-account tz
(`schedule_tracker.py:251-252` via `peak_window.convert_et_to_channel_tz`, #847).
The long-form path did NOT: `ContentPageScheduler.schedule_all_visible` called
`tracker.get_next_available_slot(time_slots, max_per_day)` WITHOUT `channel_tz`
(`content_page_scheduler.py:896` on origin/main `c1b475a06`), using the bare
`_DEFAULT_TIME_SLOTS_FALLBACK` typed AS-IS in the account's own tz. For the Asia/Tokyo
channels (`move2japan`/`undaodu`) that meant 08:00 ET was typed as 8:00 AM JST -- the WRONG
US wall-clock (off the US peak). The #859 ModLog named exactly this follow-up.

### What changed (minimal; mirror the shorts path)
- **`content_page_scheduler.py` `schedule_all_visible`**: added `channel_tz: Optional[str] = None`
  and forward it into `get_next_available_slot(time_slots, max_per_day, channel_tz=channel_tz)`.
  When set, each ET base slot is DST-converted to the account-local wall-clock before the bare
  time is typed (identity for ET accounts, shifted for Tokyo). Backwards compatible (None = old).
- **`scripts/launch.py` long-form block**: now uses `get_peak_slots_et()` as the ET base slots
  (was the bare per-account `time_slots`/`_DEFAULT_TIME_SLOTS_FALLBACK`) AND forwards
  `channel_tz=<registry timezone>` into `schedule_all_visible`. The old `[VIDEO][TZ-WARN]`
  "would publish off-peak" condition is REMOVED (the times are now correct); the
  `[VIDEO][LONG-FORM] pass START` breadcrumb now reads `ET-peak->tz=<tz>` (info, not warning).
  `_DEFAULT_TIME_SLOTS_FALLBACK` is retained for reference only with a do-not-reintroduce note.
- **Master gate `YT_VIDEO_PROCESSING_ENABLED` unchanged & DEFAULT OFF** — enabling long-form
  is still 012's call; this slice only makes the TIMES correct when enabled.

### Tests (mock-only, non-vacuous, NO browser)
`tests/test_long_form_tz_peak_window.py` (7 tests) drives the REAL `schedule_all_visible` with a
REAL `ScheduleTracker`, stubbing only the DOM row-read + per-row Studio click flow to capture the
time string that WOULD be typed:
- Tokyo 08:00 ET -> ~21:00 JST (summer/EDT) and ~22:00 JST (winter/EST) -> DST proven (summer !=
  winter); full-day peaks (08/12/20 ET) -> 21:00/01:00/09:00 JST in order;
- NY 08:00 ET -> ~8:00 AM (identity); Tokyo vs NY diverge (PM vs AM) for the same ET slot;
- MUST-FAIL probe: the no-`channel_tz` path types bare ET while the with-tz path types JST evening.
**MUST-FAIL on origin/main:** verified -- all 7 fail there with
`TypeError: schedule_all_visible() got an unexpected keyword argument 'channel_tz'` (the param
does not exist pre-slice). The #859 `test_long_form_scheduling_enable.py` mock was updated to
accept the new kwarg; it + `test_peak_window.py` + `test_scheduler.py` stay green (no regression).

### Scope
Touched: `content_page_scheduler.py` (`schedule_all_visible` channel_tz), `scripts/launch.py`
(ET peaks + thread channel_tz, drop TZ-WARN), the new test, the #859 test mock, this ModLog.
Did NOT touch: the enable flag, private path, indexing, shorts path, the rotation budget, the
other `get_next_available_slot` call sites (`resolve_conflicts`/`thin_schedule` — calendar helpers,
not the long-form launch path).

## 2026-06-19 - Enable long-form video scheduling for all 4 channels (flag-gated, default OFF)

**By:** 0102 (Worker-Lane LONGFORM-SCHED)
**Slice:** LONG_FORM_SCHEDULING_ENABLE_PHASE1
**WSP References:** WSP 22 (ModLog), WSP 49 (Structure), WSP 50 (Pre-Action), WSP 84 (Code Reuse: ContentPageScheduler/ScheduleTracker already complete; mirror #858 rotation), WSP 97 (truth signaling)

### Why (the dormant long-form path)
The long-form (Videos-tab) scheduling pass already exists inside
`run_multi_channel_scheduler` (`scripts/launch.py`, the `YT_VIDEO_PROCESSING_ENABLED`
block; ~`:1028-1085` on origin/main `36b0d2892`). It is DORMANT for two reasons:
1. Master gate `YT_VIDEO_PROCESSING_ENABLED` (default `"false"`, `launch.py:1031`) is set
   nowhere in daemon operation (the DAE PHASE 3, `auto_moderator_dae.py:1592-1640`, never
   sets it) -> long-form never runs.
2. Even with the flag on, the block requires the registry `content_types` to include
   `"upload"` (`launch.py:1034-1035`). On origin/main only `move2japan` + `undaodu` had
   `"upload"`; `foundups` + `antifafm` were `["short"]` -> 2/4 channels skipped.

OUTWARD-FACING: scheduling a long-form upload publishes it PUBLIC at its slot, so the
master gate stays DEFAULT OFF — 012 enables it deliberately.

### What changed (minimal; registry defaults + launch.py long-form block only)
- **Registry DEFAULTS** (`youtube_channel_registry.py:_default_channels`): added `"upload"`
  to `foundups` (`:85`) and `antifafm` (`:102`) `content_types`, so all 4 channels are
  long-form-eligible when the flag is enabled.
  - **RUNTIME SHADOW (deployment note):** the persisted `memory/youtube_channels.json` is
    gitignored and holds `foundups`/`antifafm` at `["short"]`. `_merge_defaults…24517 tokens truncated…lane enables high-impact work sequencing without destabilizing Shorts PoC
- WSP 22: ModLog captures control-plane memory for 0102 recall

## V0.2.0 - Layer Cake Testing (2026-01-01)

### Layer 1: Navigation + Filter - COMPLETE
- **URL-based filter (RECOMMENDED)**: `filter=[{"name":"VISIBILITY","value":["UNLISTED"]}]`
- **UI-based filter**: Click `input[placeholder='Filter']` → Click "Visibility" (index 9) → Click "Unlisted" SPAN → ESC
- Test: `python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer1_filter`
- Test with UI: `python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer1_filter --ui`

### Layer 2: Video Edit Page - COMPLETE
- Navigate to: `https://studio.youtube.com/video/{VIDEO_ID}/edit`
- Visibility section: `ytcp-video-metadata-visibility`
- Select button: `#select-button` with `aria-label='Edit video visibility status'`
- Test: `python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer2_edit`

### Layer 3: Visibility Change - DISCOVERED
- **Key Finding**: The visibility button TOGGLES/CYCLES visibility states rather than opening a dialog
- Clicking `#select-button` changes visibility (observed: Unlisted → Scheduled)
- "Made for kids" section is part of main page, not a separate dialog
- No modal dialog for visibility selection
- Test: `python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer3_schedule`

### Architecture Decision
- **ADR-003**: Visibility toggle button behavior
  - YouTube Studio uses a toggle button for visibility changes
  - Clicking cycles through: Public → Unlisted → Private → Scheduled
  - Need to detect current state and click appropriate number of times
  - Alternative: May need to explore different UI path for explicit scheduling with date/time

### DOM Element Reference
```
ytcp-video-metadata-visibility
  └── #container
      └── #content
          └── #icon-and-type
              └── #visibility-text (shows: "Unlisted", "Scheduled", etc.)
      └── #select-button (YTCP-ICON-BUTTON, aria='Edit video visibility status')
```

## V0.2.1 - UI-TARS Visual Verification Integration (2026-01-01)

### Added
- `--uitars` flag for test_layer1_filter.py
- UI-TARS vision model integration for complex dialog navigation
- Fallback from UI-TARS to DOM selectors if vision model can't find elements

### UI-TARS Integration
- Uses `modules/infrastructure/foundups_vision/src/ui_tars_bridge.py`
- Connects to LM Studio API at port 1234
- Model: UI-TARS 1.5 7B (vision-language model)
- Verified working: Found Filter input at coordinates (174, 115) in 1000x1000 space

### Test Modes
```bash
# URL-based filter (most reliable, no UI interaction)
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer1_filter

# UI-based filter (DOM selectors)
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer1_filter --ui

# UI-TARS vision-based filter (requires LM Studio with ui-tars-1.5-7b)
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer1_filter --uitars
```

### Architecture Decision
- **ADR-004**: UI-TARS for Shadow DOM workaround
  - YouTube Studio uses heavy Shadow DOM which blocks standard selectors
  - UI-TARS screenshots the entire page and uses vision to find elements
  - Provides natural language descriptions: "Filter input in the toolbar"
  - Falls back to DOM selectors if vision fails
  - Trade-off: Slower (20-30s inference) but more robust for complex dialogs

### Technical Details
- Screenshot resizing: 2560x1202 → 1280x601 (for faster inference)
- Coordinate mapping: 1000x1000 box → viewport CSS pixels
- Model output format: `click(start_box='<|box_start|>(x,y)<|box_end|>')`
- Timeout: 120s (allows for CPU-based inference)

## V0.2.2 - Visibility Filter Dialog Deep Dive (2026-01-01)

### Key Findings

**ADR-005**: Visibility Filter Dialog Structure
- The `<ytcp-filter-dialog>` contains a `<tp-yt-paper-dialog id="dialog">` that is **hidden by default**
- Inner dialog has `display: none` and `aria-hidden="true"` until properly triggered
- Dialog contains 6 checkboxes: Public, Private, Unlisted, Members, Has schedule, Draft
- Apply/Cancel buttons at the bottom

**ADR-006**: JavaScript .click() vs ActionChains
- YouTube Studio's `ytcp-checkbox-lit` elements do NOT respond to JavaScript `.click()`
- Must use Selenium ActionChains with coordinate-based clicks for checkbox interaction
- Verified: `aria-checked` changes from `false` to `true` with ActionChains click

**ADR-007**: Force-Opening Dialog Bypasses Event System
- Force-opening the dialog via JS (`display: block`, `opened=true`) shows the checkboxes
- However, clicking Apply doesn't apply the filter because YouTube's event handlers weren't initialized
- The dialog must be opened through YouTube's native click handlers for the filter to work

### Visibility Dialog DOM Structure
```
ytcp-filter-dialog
  └── tp-yt-paper-dialog#dialog (display: none by default)
      └── .header (title: "Visibility", close button)
      └── form#contentsForm
          └── ytcp-checkbox-group.selection-list
              └── ul
                  └── li.row (x6)
                      └── label.ytcp-checkbox-label
                          └── ytcp-checkbox-lit
                              └── #checkbox (role="checkbox", aria-checked)
                          └── span.checkbox-label (text: "Public"/"Unlisted"/etc.)
      └── .buttons-row
          └── ytcp-button (text: "Apply")
          └── ytcp-button (text: "Cancel")
```

### Checkbox Click Pattern
```python
# Working pattern for ytcp-checkbox-lit clicks:
from selenium.webdriver.common.action_chains import ActionChains

# Get checkbox center coordinates via JS
coords = driver.execute_script('''
    const checkbox = ...;  // Find the checkbox
    const rect = checkbox.getBoundingClientRect();
    return {x: rect.left + rect.width/2, y: rect.top + rect.height/2};
''')

# Click using ActionChains (moves to viewport coords)
actions = ActionChains(driver)
actions.move_by_offset(coords['x'], coords['y']).click().perform()
actions.move_by_offset(-coords['x'], -coords['y']).perform()  # Reset
```

### Recommendation
**Use URL-based filtering for reliability:**
```python
filter_param = '[{"name":"VISIBILITY","value":["UNLISTED"]}]'
url = f"https://studio.youtube.com/channel/{channel_id}/videos/short?filter={quote(filter_param)}"
```

UI-based filtering is complex due to:
1. Shadow DOM blocking standard selectors
2. Dialog requiring proper event initialization
3. Checkbox clicks requiring ActionChains (not JS .click())

### Test Files Created
- `test_visibility_filter_complete.py` - Full 6-step filter flow (force-open approach)
- `test_visibility_natural_click.py` - Attempted natural click approach
- `debug_visibility_dialog*.py` - Diagnostic scripts
- `debug_checkbox_click.py` - Checkbox click testing
- `debug_filter_dialog.py` - Dialog structure exploration

## V0.3.0 - URL-First with DOM Fallback (2026-01-01)

### Added
- `navigate_to_shorts_with_fallback()` method in `dom_automation.py`
- `_apply_filter_via_dom()` private method for fallback logic
- New DOM selectors for filter UI interaction
- `--fallback` test mode in `test_layer1_filter.py`

### Architecture Decision
- **ADR-008**: URL-First with DOM Fallback Strategy
  - Primary: Use pre-filtered URL with encoded `filter` parameter (instant, reliable)
  - Fallback: Click through Filter UI via DOM/ActionChains if URL filter chip not detected
  - Rationale: URL approach is faster and bypasses Shadow DOM issues; DOM fallback provides resilience

### Implementation Details
```python
# URL-first approach (preferred)
url = build_studio_url(channel_id, "short", "UNLISTED")
# Generates: https://studio.youtube.com/channel/{ID}/videos/short?filter=%5B%7B%22name%22%3A%22VISIBILITY%22%2C%22value%22%3A%5B%22UNLISTED%22%5D%7D%5D

# DOM fallback (if URL filter chip not detected)
1. Click filter area at (170, 104) using ActionChains
2. Click "Visibility" menu item
3. Select "Unlisted" checkbox
4. Click "Apply" button
5. Verify filter chip appeared
```

### Test Command
```bash
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer1_filter --fallback
```

## V0.4.0 - Layer 2: Video Edit + Content Enhancement (2026-01-01)

### Added
- Layer 2 DOM selectors for video edit page (title/description textboxes)
- `click_first_video_edit_button()` method in `dom_automation.py`
- `get_current_title()` and `get_current_description()` extraction methods
- `set_title()` and `set_description()` modification methods
- `enhance_title()` and `enhance_description()` functions in `content_generator.py`
- `--enhance` test mode in `test_layer2_edit.py`

### Architecture Decision
- **ADR-009**: Layer 2 Edit Workflow
  - Navigate to filtered shorts → Click edit button → Extract content → Enhance → Preview
  - Enhancement preserves original content hooks while adding FFCPLN branding
  - Title limited to 100 chars, description includes SEO hashtags

### Test Commands
```bash
# Basic Layer 2 navigation test
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer2_edit

# Full enhancement workflow (preview only, no save)
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer2_edit --enhance
```

## V0.4.1 - Selector Fixes for Layer 1/2 (2026-01-01)

### Fixed
- **ADR-009**: VIDEO_TABLE selector fixed
  - Old: `table[aria-label='Video list']` (doesn't exist on page)
  - New: `ytcp-video-row` (actual video row elements)
- **ADR-010**: Filter chip selector fixed
  - Old: `button[aria-label*='Visibility: Unlisted']`
  - New: JavaScript-based detection of `ytcp-chip` with text content matching
- **ADR-011**: Filter input wait added
  - Added WebDriverWait for Filter input in DOM fallback
  - Increased timeout to 10 seconds

### Test Results (2026-01-01)
| Test | Mode | Status | Notes |
|------|------|--------|-------|
| Layer 1 | `--fallback` | PASS | URL-first with DOM fallback, 30 videos found |
| Layer 2 | basic | PASS | Direct URL navigation to edit page |
| Layer 2 | `--enhance` | FAIL | `click_first_video_edit_button` needs selector fix |

### Key Finding: URL Filter is Reliable
- URL-based filtering: `?filter=[{"name":"VISIBILITY","value":["UNLISTED"]}]`
- Chip detection: `ytcp-chip` element with text "Visibility: Unlisted"
- Filter input disappears when filter is applied (replaced by chip)

### Diagnostic Script Added
- `tests/diagnose_page.py` - Quick page state inspection tool

## V0.5.0 - Complete WRE Stack + CLI Integration (2026-01-01)

### Added
- **ROADMAP.md**: 3-phase development plan (layer tests → linking → DAE)
- **scripts/launch.py**: WSP 62 extraction for main.py integration
- **main.py option 6**: YouTube Shorts Scheduler submenu
- **Layer 3 selectors**: Full scheduling DOM elements (visibility, date, time, done)
- **WSP 95 SKILLz.md**: FFCPLN title enhancement skill

### WRE Layer Stack Validated

| Layer | Action | Status |
|-------|--------|--------|
| L0 | Entry (select video) | ✅ |
| L1 | Open visibility dialog | ✅ |
| L1.1 | Expand schedule | ✅ |
| L2 | Set DATE | ✅ |
| L3 | Set TIME | ✅ |
| L4 | Click Done | ✅ |
| L5.1 | Related Video modal | ⚠️ Selector needs fix |
| L5.2 | Select top-left video | ⚠️ Coordinate issue |
| L5.3 | SAVE | ✅ |
| L5.4 | Return to list | ✅ |
| L5.5 | REFRESH (F5) | ✅ CRITICAL |

### Videos Scheduled (Demo)
1. `gdTtl3c3rtA` → Feb 17, 2026 at 5:00 PM
2. `7ww5-6me4zg` → Feb 18, 2026 at 6:00 PM

### Architecture Decision
- **ADR-012**: Visual-First, Selenium-Later
  - Phase 1: Validate DOM selectors via browser subagent (visual)
  - Phase 2: Convert to pure Selenium once selectors verified
  - Phase 3: DAE loop with self-monitoring

### Known Issues
- **L5.1-5.2**: Related video selector clicks arbitrary position, not top-left
- **TODO**: Add search feature support for related video selection

### CLI Integration
```bash
python main.py
# Select 1 (YouTube) → 6 (Shorts Scheduler)
# Options: 1=Enhance, 2=Dry Run, 3=Schedule
```

### Test Commands
```bash
# Layer 1 with fallback
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer1_filter --fallback

# Layer 2 with enhancement
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer2_edit --enhance
```

## V0.6.0 - Full Chain Test + Menu Restructure (2026-01-01)

### Added
- **test_full_chain.py**: Concatenated L1 → L2 → L3 → L4 test
- **ADR-013**: main.py YouTube menu restructure (Occam's Razor)

### Full Chain Test
```bash
# Dry run (preview only)
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_full_chain --dry-run

# Live run (saves changes)
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_full_chain
```

**Chain Flow:**
1. L1: Navigate to unlisted shorts (URL filter)
2. L2: Click first video → edit page
3. L3: Open visibility → Schedule → Set date/time → Done → Save
4. L4: Return to list → Refresh (F5)

### Architecture Decision
- **ADR-013**: YouTube Menu Restructure (Occam's Razor)
  - main.py → 1 (YouTube DAEs) → Independent DAEs at 1.x level
  - Option 1 = Live Chat Monitor (direct launch with 012 profile)
  - Option 2 = Comment Engagement DAE
  - Option 3 = Shorts Scheduler (submenu)
  - Option 4 = Shorts Generator (Veo3/Sora2 submenu)
  - Option 5 = YouTube Stats
  - Option 6 = Full Production Mode
  - Option 7 = AI Overseer Mode

### CLI Integration Updated
```bash
python main.py
# Select 1 (YouTube) → 3 (Shorts Scheduler)
# Options: 1=Enhance, 2=Dry Run, 3=Schedule
```

## V0.7.0 - Human Behavior + Selenium Fixes (2026-01-01)

### Added
- **human_behavior module integration** in `test_layer3_schedule.py`
- **Ctrl+A before typing** for date/time inputs (replaces, not appends)
- **set_schedule_date_time()** function with validation logging
- **Aligned test menu** - Options 4-8 now match actual layer tests

### Architecture Decisions

- **ADR-014**: Human Behavior for Popup Stability
  - Standard JS `.click()` can close popups prematurely
  - `human_behavior` uses Bezier curve mouse movements
  - Triggers proper hover states before clicking
  - Slower but more reliable for reactive YouTube UI

- **ADR-015**: Ctrl+A Before Input
  - YouTube date/time inputs have existing values
  - Must select all (Ctrl+A) before typing to replace
  - Prevents "Jan 01, 2026Jan 08, 2026" errors

### Test Menu (main.py → 1 → 3)
```
== SELENIUM TESTS ==
4. [TEST] Full Chain (navigate → enhance → schedule → save)
5. [TEST] L0: Entry (navigate to unlisted, select video)
6. [TEST] L1: Filter (apply unlisted filter)
7. [TEST] L2: Edit (open edit page, find visibility)
8. [TEST] L3: Schedule (visibility → schedule → date/time → done)
```

### Test File Mapping
| Option | Test File | Description |
|--------|-----------|-------------|
| 4 | `test_full_chain.py` | Full L0→L3 |
| 5 | `test_layer0_entry.py` | Entry/navigation |
| 6 | `test_layer1_filter.py` | URL filter |
| 7 | `test_layer2_edit.py` | Edit page |
| 8 | `test_layer3_schedule.py` | Schedule dialog |

### Key Code Pattern
```python
# Import human behavior
from modules.infrastructure.foundups_selenium.src.human_behavior import get_human_behavior
human = get_human_behavior(driver)

# Click with human-like movement
human.human_click(date_input)

# Ctrl+A before typing to replace existing value
ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
date_input.send_keys("Jan 08, 2026")
```

### Coverage Status
| Layer | Status |
|-------|--------|
| L0 Entry | ✅ Selenium |
| L1 Filter | ✅ Selenium |
| L2 Edit | ✅ Selenium |
| L2.5 SKILLz | ✅ FFCPLN |
| L3 Schedule | ✅ Selenium + human_behavior |
| L4 Done | ✅ Selenium |
| L5 Save/Return | ⚠️ In progress |

## V0.8.0 - WRE-TARS Visual Verification (2026-01-01)

### Added
- **WREVisualTestRunner** (`foundups_selenium/src/wre_visual_runner.py`)
  - Visual-first test execution with UI-TARS verification gates
  - Each step: action → screenshot → verify → record → proceed/retry
  - Integrates with pattern_memory for recursive learning (WSP 48/60)
- **`--wre-tars` flag** for test_layer3_schedule.py
- **`run_with_visual_verification()`** function

### Architecture Decisions
- **ADR-016**: Pure UI-TARS Verification (Option 1)
  - Speed is not a factor for testing - correctness matters
  - Visual verification = DOM-agnostic robustness
  - Natural language prompts: "Is the date picker visible?"
  - Each step becomes training data for pattern_memory

### WREVisualTestRunner API
```python
runner = create_wre_runner(driver, skill_name="youtube_schedule_l3")

runner.step(
    "L3.2 Expand Schedule",
    action=lambda: click_schedule_expand(driver),
    verify_prompt="Is the Schedule section showing date and time inputs?"
)

runner.print_summary()  # Shows ✅/❌ for each step
```

### Test Command
```bash
# Standard DOM-based test
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer3_schedule

# WRE-TARS visual verification mode
python -m modules.platform_integration.youtube_shorts_scheduler.tests.test_layer3_schedule --wre-tars
```

### Pattern Memory Integration
- Outcomes stored in `wre_core/data/pattern_memory.db`
- Skill name: `youtube_schedule_l3`
- Fields: step name, verify prompt, success, screenshot path, execution_ms

## V0.9.0 - Edge Browser + Multi-Channel Rotation (2026-01-18)

### Added
- **RavingANTIFA channel support** in `channel_config.py`
  - Channel ID: `UCVSmg5aOhP4tnQ9KFUg97qA`
  - Uses Edge browser (port 9223) like FoundUps
  - Same timezone/slots as FoundUps (America/New_York)

- **Edge browser support** in `scripts/launch.py`
  - Auto-detects browser from channel config (port 9223 = Edge)
  - Uses EdgeOptions for Edge connections
  - Provides correct startup instructions for each browser

- **Multi-channel rotation** function `run_multi_channel_scheduler()`
  - Chrome (9222): Move2Japan -> UnDaoDu rotation
  - Edge (9223): FoundUps -> RavingANTIFA rotation
  - Uses TarsAccountSwapper for account switching between channels
  - Reuses single browser connection for full rotation

### Changed
- **Menu restructure** for multi-channel rotation:
  - Option C: Chrome Rotation (Move2Japan -> UnDaoDu)
  - Option E: Edge Rotation (FoundUps -> RavingANTIFA)
- **Docstrings updated** in scheduler.py for RavingANTIFA support
- **CLI updated** with `--browser` flag for multi-channel mode

### Browser Port Routing
```
Chrome (9222): Move2Japan, UnDaoDu
Edge (9223): FoundUps, RavingANTIFA
```

### Architecture Decision
- **ADR-017**: Multi-Channel Rotation with Account Swapper
  - Single browser session for entire rotation (efficiency)
  - TarsAccountSwapper handles channel switching via YouTube's account picker
  - Each channel gets `max_per_channel` videos scheduled before rotation
  - Account switch uses DOM-based avatar -> Switch account -> Select channel flow

### CLI Usage
```bash
# Multi-channel rotation
python -m modules.platform_integration.youtube_shorts_scheduler.scripts.launch --browser edge --mode schedule

# Single channel (legacy)
python -m modules.platform_integration.youtube_shorts_scheduler.scripts.launch --channel UCfHM9Fw9HD-NwiS0seD_oIA

# From main.py menu: 1 (YouTube DAEs) -> 3 (Scheduler) -> 5 (Edge rotation)
```

### WSP Compliance
- WSP 3: Platform Integration domain
- WSP 49: Standard module structure maintained
- WSP 22: This ModLog entry

## V0.9.1 - Menu Simplified for 0102 Clarity (2026-01-19)

### Changed
- **Menu restructure** in `scripts/launch.py` → `show_shorts_scheduler_menu()`:
  - Removed letter-coded choices (no `C`/`E`) for 012 clarity
  - Production actions only:
    - `1` NEXT short (full cake)
    - `2` ALL shorts (safety: bounded by `max_videos` in orchestrator)
    - `3` DRY RUN preview (no save)
    - `4-5` browser-grouped multi-channel rotation
    - `6` indexing handoff (use YouTube DAEs → `8` [INDEX])
    - `7` full-videos placeholder (future layer)
  - Tests remain in `tests/` and are run directly via `python -m ...` (WSP 34)

- **Handler updated** in `main.py` (L1755-1817):
  - Options `1-3` now use the production orchestrator `src/scheduler.run_scheduler_dae`
  - Options `4-5` run browser-grouped rotation via `run_multi_channel_scheduler`
  - Option `6` prints indexing handoff (keeps domains functionally distributed)
  - Option `7` remains a placeholder until videos DOM selectors exist

### Added
- **Orchestration SKILLz template** at `.agent/skills/orchestration_template/SKILL.md`
  - Documents LEGO layered test pattern
  - Provides reusable template for building automation systems

### Architecture Decision
- **ADR-018**: Simplified 0102 Menu
  - Dev tests hidden behind D submenu (not cluttering main menu)
  - Auto-detect replaces manual channel key setting
  - Numeric options only (no C/E letter confusion)
  - Placeholders signal future work without blocking current use

## V0.9.2 - Hardened Rotation with Oops Detection (2026-01-19)

### Added
- **Oops page detection** in `run_multi_channel_scheduler()`:
  - Imports `_is_oops_page()` and `CHANNEL_FALLBACKS` from `multi_channel_coordinator.py` (no vibecoding - reuses existing LEGO block)
  - When permission error detected, tries bidirectional fallback channel
  - Only skips if both target and fallback fail

### Changed
- **max_per_channel default**: Changed from 5 to 9999 (run until complete)
- **No prompts**: Automation runs without user input

### Architecture Decision
- **ADR-019**: Reuse LEGO Blocks
  - `_is_oops_page()` already battle-tested in comment engagement
  - `CHANNEL_FALLBACKS` provides bidirectional recovery
  - No duplicate code - import and reuse

## V0.9.3 - Occam's Razor Menu Simplification (2026-01-19)

### Changed
- **`show_shorts_scheduler_menu()`** simplified from 7 options to 2:
  - **Before**: Schedule Next, Schedule All, Dry Run, Chrome rotation, Edge rotation, Indexing handoff, Videos placeholder
  - **After**: 1. Schedule ALL Shorts (continuous), 0. Back
  - Dev options accessible via CLI: `--browser chrome|edge`, `--dry-run`

- **main.py handler** simplified:
  - Option 1 now schedules ALL shorts (max_videos=9999)
  - Removed handlers for options 2-7
  - CLI reference preserved in comments for developers

### Architecture Decision
- **ADR-020**: Occam's Razor for 012-Facing Menus
  - User said: "too many options... apply occums"
  - Primary action should be ONE button that "just works"
  - Dev/debug options remain accessible via CLI, not cluttering menu
  - Pattern: Indexing and Scheduling now both have single primary action

### WSP Compliance
- WSP 50: Pre-action verification (menu shows current channel)
- WSP 22: This ModLog documents the change

## 2026-09-21 - Read-only remote audit

WSP 00/50/84/97: retained Holo authority mismatch and used source/Git evidence.
Added [diagnostic skill](skillz/youtube-remote-audit/SKILL.md) and
[evidence report](docs/REMOTE_AUDIT_2026-09-21.md). Observed 13 unlisted clips.
Recorded legacy CLI drift and preview tracker writes; neither repaired.
Source/AST and live read-only inventory verified; no runtime code changed,
no scheduling tests or public actions performed. Existing dirty files preserved.

## 2026-09-21 - YUMORI source context and factual-scope correction

WSP 50/84/97: added [source context](docs/YUMORI_SOURCE_CONTEXT_2026-09-21.md)
from current Drive masters, the live site, FIN inspection and municipal records.
Recorded coverage limits, conflicting request wording, modeled/verified boundaries,
and the existing ASR path's forced-English behavior. Linked it from the audit
skill and corrected the initial overbroad factual-content restriction.
Documentation only; no new publisher, runtime repair, outreach or YouTube write.
