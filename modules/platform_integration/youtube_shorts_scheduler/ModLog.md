# YouTube Shorts Scheduler - ModLog

## 2026-06-16 - Pin video-index context consumption on the scheduling path (Phase 1)

**By:** 0102 (Worker-Lane SSVCC-AUTHOR)
**Slice:** SHORTS_SCHEDULER_VIDEO_INDEX_CONTEXT_CONSUMPTION_COVERAGE_PHASE1
**WSP References:** WSP 22 (ModLog), WSP 50 (Pre-Action), WSP 84 (Code Reuse), WSP 97 (Truth Signaling)
**Basis:** #820 ALREADY built the artifact-consumption path; this slice PINS it with tests (no rebuild).

### Tests (deliverable)

Added scheduling-path consumption coverage to `tests/test_index_metadata_decoupling.py` (reusing the
existing harness): TEST A (MISSING artifact -> base content, no enhancement, no scheduler-owned
indexing) and TEST B (PRESENT artifact -> index context + woven hashtags + `0102 DIGITAL TWIN INDEX`
block applied; `schedule_video` only on the explicit scheduling path), plus an env-gate complement and
an observability-marker test. See `tests/TestModLog.md` for details and non-vacuity notes.

### Production (observability only - the single permitted touch)

`_update_video_metadata` now emits ONE behaviour-neutral log line
`index_context=present|missing|disabled` (present = `ctx` not None; missing = artifact absent/`ctx`
None; disabled = `YT_SCHEDULER_INDEX_WEAVE_ENABLED` false). This unifies/replaces the prior
"No index artifact ... skipping enhancement" debug line. No response body, no transcript, no secrets.
Control flow (consumption logic) is UNCHANGED - the `present`/`missing` branches still set the same
`new_title`/`new_description` as before; only the log output differs.

## 2026-06-16 - Decouple Index Read-for-Context from Live Metadata Write (Phase 1)

**By:** 0102 (Worker-Lane SSIMD-AUTHOR)
**Slice:** SHORTS_SCHEDULER_INDEX_METADATA_DECOUPLING_PHASE1
**WSP References:** WSP 22 (ModLog), WSP 50 (Pre-Action), WSP 84 (Code Reuse), WSP 97 (Truth Signaling)
**Decision basis:** merged audit #818; producer precondition #819.

### Problem

The scheduler entangled "READ the video index for context" with "WRITE live YouTube
metadata". The indexing path (`run_indexing_cycle`, INDEXING-ONLY MODE) called
`_update_video_metadata` (live `edit_title`/`edit_description`) and `self.dom.save_video()`,
and the read path called scheduler-owned `ensure_index_json` (stub/Gemini). A bounded index
pass or artifact refresh could silently overwrite production metadata.

### Resolution (read/write split)

- Added a PURE, read-only context builder `build_index_metadata_context(...) -> Optional[MetadataContext]`
  in `index_weave.py`. It only `load_index_json` + the existing pure builders
  (`build_human_description_context`, `inject_context_into_description`, `build_topic_hashtags`,
  `build_digital_twin_index_block`, `weave_description`, optional `generate_clickbait_title_from_index`).
  It takes NO dom/driver, NEVER calls `ensure_index_json`/`save_index_json`/`create_stub_index_json`,
  and NEVER imports/instantiates `GeminiVideoAnalyzer`. Returns None on a MISSING artifact ->
  caller "skip enhancement", NOT "index now".
- `_update_video_metadata` (scheduling read path) now consumes the pure builder. The
  scheduler-owned `ensure_index_json` create/Gemini calls were removed from this read path.
  Live `edit_title`/`edit_description` order and the env gates
  (`YT_SCHEDULER_INDEX_WEAVE_ENABLED`/`_INDEX_MODE`/`_INDEX_INFORM_TITLE`/`_INDEX_ENHANCE_DESCRIPTION`)
  are preserved; artifact-present bytes are unchanged.
- The content-channel gate's delete+Gemini-reindex branch is now READ-ONLY: it reads an
  EXISTING artifact for transcript-refined classification (no unlink, no `ensure_index_json`,
  no Gemini coupling).
- `run_indexing_cycle` is now a READ-ONLY artifact/context VALIDATION path (marked
  deprecated/read-only in its docstring). It no longer calls `_update_video_metadata`,
  `edit_title`/`edit_description`/`schedule_video`, or `save_video`. It records artifact
  presence/absence per video.

### save_video resolution

`self.dom.save_video()` was a LATENT AttributeError: `dom_automation.py` defines no
`def save_video`; `YouTubeStudioDOM` (class at `dom_automation.py:336`) has no base class and no
`__getattr__`/`__getattribute__`. The only reference was `scheduler.py` (indexing path). The real
page-level save is `click_save` (`dom_automation.py:2703`), reached on the scheduling path via
`schedule_video`. The call was removed from the indexing path (no save implementation added).
Recorded: SAVE_VIDEO_LATENT_BUG_REMOVED_FROM_INDEXING_PATH.

### Behavior preservation

INDEXING is now read-only; SCHEDULING still writes (unchanged). The explicit scheduling/publish
path (`run_scheduling_cycle` -> `_update_video_metadata` -> `schedule_video`), per-video order,
visibility guards, dry_run short-circuit, post-schedule artifact bookkeeping, and
`record_schedule_outcome` are untouched. External callers use `run_scheduler_dae` only
(`multi_channel_coordinator.py`); `run_indexing_cycle`/`run_indexer_dae` are not exported and have
no external runtime callers.

### Tests

- `tests/test_index_metadata_decoupling.py` (7 controls + 1 Control-4 discrimination test + 2
  pure-builder cases). Negative controls 1/2/4/5 demonstrably FAIL on the old coupled code; control
  3 is honestly paired with control 7 (positive scheduling-write regression anchor). Strict
  `spec_set` DOM double of `YouTubeStudioDOM` (no invented `save_video`).

- Control 4 hardened (non-vacuous): the per-video loop in `run_indexing_cycle` swallows each video
  body exception into `results["errors"]` (inner `except`), and only the OUTER except sets
  `results["fatal_error"]`. A swallowed `save_video` `AttributeError` therefore lands in
  `results["errors"]` (mentioning `save_video`) and NEVER in `fatal_error`. Control 4 now asserts
  REACHABILITY (`navigate_to_video` called with the video id) and NON-VACUOUS DETECTION
  (`results["errors"] == []` AND no error references `save_video`), keeping `not hasattr(dom,
  "save_video")` as documentation only. Asserting `"fatal_error" not in results` alone would be
  VACUOUS because the inner except hides the access.

- Discrimination test `test_control4_detection_channel_surfaces_save_video` PROVES the channel has
  teeth: it monkeypatches the bound `scheduler.build_index_metadata_context` (the loop's call at
  `scheduler.py:1107`, imported `scheduler.py:29`) with a stand-in that calls
  `scheduler.dom.save_video()`, then asserts the swallowed `AttributeError` SURFACES via
  `any("save_video" in e["error"] for e in results["errors"])` (still no `fatal_error`). No product
  code is edited. Verified: under this injection the hardened Control 4 raises `AssertionError`.

---

## 2026-06-15 - UNLISTED Filter Enforcement (Scheduled vs Unlisted)

**By:** 0102
**WSP References:** WSP 22, WSP 97 (Truth Signaling)

### Problem

Shorts scheduler could run on **Scheduled** / **Has schedule** filter instead of **Unlisted**
(e.g. antifaFM after prior audit/sync). F5 refresh does not switch filters — unlisted rows
stay invisible and processing silently finds zero videos or wrong rows.

### Solution

- Clear **Has schedule** chips before applying Unlisted
- Uncheck other visibility checkboxes in filter dialog when switching to Unlisted
- URL-first UNLISTED navigation (`YT_SCHEDULER_URL_FILTER_FIRST=true` default)
- Abort scheduler cycle if list filter is still SCHEDULED
- Skip videos whose edit page shows Scheduled (not Unlisted)
- Strict row scrape rejects Scheduled-looking rows

### Tests

- `tests/test_visibility_filter_enforcement.py`

---

## 2026-05-04 - OC21: Agentic Content-Channel Verification Gate

**By:** 0102 (Worker AW3)
**WSP References:** WSP 22 (ModLog), WSP 97 (Truth Signaling), WSP 77 (Agent Coordination)

### Problem

Scheduler was not agentic - blindly scheduled videos without verifying content matches channel:
- UnDaoDu (mindfulness) could schedule FFCPLN music content
- No re-indexing when classification conflicts with channel
- Index stale data was trusted without verification

### Solution

**Agentic Content-Channel Gate** in `scheduler.py`:
1. Before scheduling, classify video by title
2. If FFCPLN classification on non-FFCPLN channel (undaodu, foundups):
   - Delete stale index
   - Re-index with Gemini (reads actual video content)
   - Re-classify with fresh transcript
   - If STILL FFCPLN: skip (content truly doesn't belong)
   - If NOT FFCPLN: proceed (title was misleading, content is fine)

### Key Insight

The problem wasn't "wrong channel upload" but **lack of verification**. The indexer wasn't checking if content matches channel - it assumed content type from channel name alone. Now the system:
- READs actual video content via Gemini
- VERIFIES content-channel fit
- RE-INDEXES when mismatch detected

### Files Changed
- `src/scheduler.py`: 
  - Added `classify_content` import
  - Added content-channel gate with re-index logic (~50 lines)

### Dependencies
- `skillz/gemma_content_type_classifier/executor.py` - pure regex classification (no AI model)
- `index_weave.ensure_index_json(mode="gemini")` - Gemini API re-indexing

---

## 2026-03-30 - YouTube Domain Agent Phase 3 (G4 Schedule Reconciliation)

**By:** 0102
**WSP References:** WSP 22 (ModLog), WSP 77 (Agent Coordination), WSP 91 (Observability)

### Problem

Schedule audit in `run_scheduling_cycle()` logs warnings but does not emit breadcrumbs for AI Overseer sentinel detection.

### Solution

**G4: Schedule Reconciliation Breadcrumb**
- Added breadcrumb emission to post-audit block in `scheduler.py`
- Emits `schedule_audit_unhealthy` when `audit_report["healthy"] == False`
- Uses existing gate: `YT_SCHEDULER_POST_AUDIT=true` (default: false)
- Breadcrumb metadata includes:
  - `channel_key`, `channel_id`
  - `false_positives`, `time_collisions`, `missing_from_tracker` (counts)
  - `auto_heal`, `healed` (count)

### Design Decisions

- **Reuses existing audit**: No changes to `schedule_auditor.py`
- **Gate preserved**: Default remains opt-in (false) to avoid noise
- **Raw facts only**: Counts are integers, not full report objects

### Files Changed
- `scheduler.py`: Added breadcrumb emission in post-audit block (~15 lines)

### Tests Added
- `test_schedule_audit_breadcrumb.py`: 5 tests covering breadcrumb emission, metadata, gating

---

## 2026-03-18 - Hardened Tab Close for Chrome 146

**WSP References**: WSP 97 (CoT/CoR), WSP 91 (Observability)

### Problem
Chrome 146 throws "failed to close window in 20 seconds" during session restore tab cleanup:
```
selenium.common.exceptions.WebDriverException: Message: unknown error: failed to close window in 20 seconds
```

### Root Cause
`driver.close()` can timeout when tabs are unresponsive or Chrome is under load.

### Fix
Changed `launch.py:730` from `driver.close()` to `driver.execute_script("window.close()")` with try-except:
```python
try:
    driver.switch_to.window(handle)
    driver.execute_script("window.close();")  # More reliable than driver.close()
except Exception as close_err:
    print(f"[WARN] Tab close failed (non-fatal): {close_err}")
```

### Files Changed
- `scripts/launch.py`: Lines 723-737 - hardened tab cleanup

---

## 2026-02-27 - Browser Rotation Fix: Add close() Method

**WSP References**: WSP 84 (Code Reuse), WSP 27 (DAE Lifecycle)

### Problem
Browsers (Edge/Chrome) not rotating after commenting completes into scheduling/indexing:
- `multi_channel_coordinator.py:674` calls `shorts_scheduler.close()` - **method didn't exist**
- `run_scheduler_dae()` and `run_indexer_dae()` used `disconnect()` which only clears reference
- Browsers stayed locked, preventing next automation cycle

### Root Cause
`disconnect()` only sets `self.driver = None` - it doesn't call `driver.quit()` to actually release the browser for rotation.

### Fix
1. Added `close()` method to `YouTubeShortsScheduler`:
   ```python
   def close(self):
       """Close browser and release for rotation."""
       if self.driver:
           self.driver.quit()  # Actually close browser
           self.driver = None
           self.dom = None
   ```

2. Updated DAE entry points to use `close()`:
   - `run_scheduler_dae()` finally block: `disconnect()` → `close()`
   - `run_indexer_dae()` finally block: `disconnect()` → `close()`

### Files Changed
- `src/scheduler.py`: Added `close()` method (lines 150-166)
- `src/scheduler.py`: `run_scheduler_dae()` finally uses `close()` (line 1148)
- `src/scheduler.py`: `run_indexer_dae()` finally uses `close()` (line 1198)

### Expected Result
After scheduling/indexing completes, browser is properly closed and available for next DAE rotation cycle.

---

## 2026-02-25 - Edge Browser Hover Fix for Filter Dropdown (ADR-009)

**WSP References**: WSP 77 (Agent Coordination), WSP 84 (Code Reuse)

### Problem
FoundUps shorts scheduler failing on Edge browser:
```
[DOM] Dropdown not visible yet (attempt 1)
[DOM] Dropdown not visible yet (attempt 2)
[DOM] Dropdown not visible yet (attempt 3)
[DOM] Visibility menu item not found/clickable
```

Move2Japan (Chrome) succeeds, FoundUps (Edge) fails. Same code, different browsers.

### Root Cause
The filter dropdown is **hover-dependent**. After clicking the filter:
1. Dropdown opens
2. Mouse stays at click point (not in dropdown)
3. On Edge (slow), dropdown closes before JS scan completes
4. On Chrome (fast), scan completes in time

### Fix
Added mouse hover behavior to `_open_filter_ui()` in `dom_automation.py`:
- After clicking filter, move mouse **80px down** into dropdown area
- Keeps dropdown open while waiting for `tp-yt-paper-listbox` to render
- Pattern modeled after edit button hover (line 1723-1727)

### Files Changed
- `src/dom_automation.py`: `_open_filter_ui()` - Added hover fix with ActionChains

### Testing
- FoundUps (Edge): Should now keep dropdown open during retry loop
- Move2Japan (Chrome): No change (already fast enough)

---

## 2026-02-24 - AI-Driven Content Type Classification Skill (gemma_content_type_classifier)

**WSP References**: WSP 95 (SKILLz Wardrobe), WSP 77 (Agent Coordination), WSP 27 (Phase 0 KNOWLEDGE)

### What
Created `gemma_content_type_classifier` skill to replace static `description_template` config with AI-driven classification.

### Why
012's insight: "isnt description_template = skillz?" - YES! Content type should be determined by AI analyzing video content, not hardcoded per-channel config.

**Problem Solved**:
- Static `description_template` in `youtube_channels.json` assigns templates at channel level
- But channels may have mixed content (e.g., Move2Japan has FFCPLN music AND personal vlogs)
- AI should classify EACH VIDEO, not use channel-wide defaults

### Key Files Created

**Skill (WSP 95 structure)**:
- `skillz/gemma_content_type_classifier/SKILLz.md` - Skill definition with micro chain-of-thought
- `skillz/gemma_content_type_classifier/executor.py` - Classification implementation
- `skillz/gemma_content_type_classifier/__init__.py` - Module exports

**Integration**:
- `src/content_generator.py` - Added `get_ai_driven_template()` function

### Classification Taxonomy

| Content Type | Template | Channels | Indicators |
|-------------|----------|----------|------------|
| `ffcpln_music` | ffcpln | move2japan, ravingantifa | FFCPLN markers, Suno lyrics |
| `ffcpln_news` | ffcpln | move2japan, ravingantifa | ICE, protest, raid, breaking |
| `startup_tech` | foundups | foundups | pAVS, startup, AI, entrepreneur |
| `mindfulness` | undaodu | undaodu | meditation, zen, mindfulness |

### Usage

```python
# Before (static config):
template = channel_config.get("description_template", "ffcpln")

# After (skill-driven):
from modules.platform_integration.youtube_shorts_scheduler.src.content_generator import get_ai_driven_template
template = get_ai_driven_template(title=video_title, channel=channel_key, metadata=index_json)
```

### Test Results
All 5 test cases pass with correct classification:
- `#FFCPLN Burns MAGA` → ffcpln_music (marker detected)
- `Building AI Agents with pAVS` → startup_tech (pAVS detected)
- `Morning Meditation Music` → mindfulness (meditation detected)
- `BREAKING: ICE Raids Chicago` → ffcpln_news (news detected)
- `Random video` → channel baseline fallback

---

## 2026-02-04 - CPS Agentic Navigation + Schedule Thinning + Inline Rescheduling

**WSP References**: WSP 22 (ModLog), WSP 50 (Pre-Action), WSP 84 (No Vibecoding)

### What
Major CPS overhaul: agentic sidebar navigation (no URL filter params), schedule thinning algorithm, inline popup rescheduling, and live DOM selector verification for scheduled video popups.

### Why
1. **URL filter params cause blank screen** in YouTube Studio. Must navigate via base URL + sidebar Filter UI.
2. **8+ videos per day on same date** (e.g., Apr 3, 2026 had 8 shorts at same time). YouTube algorithm works best with 1-3 shorts/day, spaced 4+ hours apart.
3. **Edit page rescheduling is slow** (per-video navigation). Inline popup rescheduling stays on content table.

### Key Changes

**Navigation (`navigate_to_content`)**:
- Removed URL filter params (`?filter=...`) that caused blank screen
- Added `_apply_visibility_filter_via_ui()` — clicks Filter icon > Visibility > checkbox > Apply
- Added `_switch_content_tab()` — switches Shorts/Videos/Live tabs without page reload
- Smart detection: if already on Studio content page, just switch tab

**Schedule Thinning (`thin_schedule`)**:
- Detects overcrowded days (>max_per_day, default 3)
- Redistributes excess videos to future dates via `tracker.get_next_available_slot()`
- Uses inline popup rescheduling (fast, stays on content page)
- Falls back to edit page navigation if row not found on page

**Inline Popup Rescheduling (`reschedule_row_inline`)**:
- Opens visibility edit popup on row, changes date/time, clicks Schedule
- No page navigation required — operates directly on content table rows
- For scheduled videos, popup opens with schedule already expanded

**Audit Fixes (`audit_calendar`)**:
- `max_per_day` now configurable (default 3, was hardcoded 8)
- `heavy_days` threshold uses `max_per_day` parameter
- Added `excess` count per heavy day and `date_map` to audit result

**Selector Additions (ContentPageSelectors)**:
- `FILTER_ICON_CSS`, `FILTER_ITEM_TAG`, `FILTER_CHECKBOX_TAG`, `FILTER_APPLY_BUTTON_XPATH`
- `VISIBILITY_FILTER_MAP`: maps "SCHEDULED" -> "Has schedule", etc.
- `SIDEBAR_CONTENT_XPATH`, `CONTENT_TAB_*` selectors for agentic tab navigation

### Live DOM Verification (Scheduled Video Popup)
All selectors verified on live scheduled video (Apr 3, 2026, 6:00 PM):
- `POPUP_DIALOG_CSS` -> FOUND
- `POPUP_DATE_TRIGGER_CSS` -> FOUND ("Apr 3, 2026")
- `POPUP_TIME_INPUT_CSS` -> FOUND ("6:00 PM")
- `POPUP_SAVE_BUTTON_CSS` -> FOUND (text "Schedule")
- `ytcp-datetime-picker` -> FOUND (verification element)
- `#second-container-expand-button` -> hidden (expected: schedule already expanded)

### Files
- **MODIFIED**: `src/content_page_scheduler.py` — All changes above

---

## 2026-02-04 - Live DOM Selector Audit + Fixes (--chrome inspection)

**WSP References**: WSP 22 (ModLog), WSP 50 (Pre-Action Verification)

### What
Audited all scheduling popup DOM selectors against the live YouTube Studio page using Claude Code `--chrome` browser integration. Fixed 5 broken selectors in `dom_automation.py` and `content_page_scheduler.py`.

### Why
Multiple XPath selectors referenced elements that don't exist in the current YouTube Studio DOM (e.g., `name="SCHEDULE"` radio button). The scheduling flow relied on timeout fallbacks to work around broken selectors. Live inspection confirmed the correct element names and structure.

### Key Findings
- **No `name="SCHEDULE"` radio exists** — scheduling is triggered by expanding `#second-container` which contains `name="PUBLISH_FROM_PRIVATE"` and `name="PUBLISH_FROM_SPONSORS_ONLY"` radios
- **`target="_blank"` on OOPS "Switch account"** — confirmed and fixed in previous session
- **Visibility popup structure**: `ytcp-video-visibility-edit-popup > tp-yt-paper-dialog#dialog > ytcp-video-visibility-select`
- **Working selectors confirmed**: `#datepicker-trigger`, `#time-of-day-container input`, `#save-button`, `#cancel-button`

### Files
- **MODIFIED**: `src/dom_automation.py` — Fixed `SCHEDULE_EXPAND_XPATH`, `SCHEDULE_RADIO_XPATH`, `RADIO_SCHEDULE`, `SCHEDULE_EXPAND`, `SCHEDULE_RADIO` (V1+V2 selectors), hardcoded fallback XPaths at line ~2433, and `?next=` redirect loop fix in `handle_oops_page()` + `_click_oops_switch_account()`
- **MODIFIED**: `src/content_page_scheduler.py` — Fixed `SCHEDULE_RADIO_XPATH` from `name='SCHEDULE'` to `name='PUBLISH_FROM_PRIVATE'`

---

## 2026-02-02 - Channel Registry Integration

**WSP References**: WSP 22 (ModLog), WSP 60 (Memory), WSP 84 (No Vibecoding)

### What
Replaced hard-coded channel config and browser rotation lists with registry-driven data.

### Why
New channels should be added once (registry) and automatically show up in shorts scheduling and rotation.

### Files
- **MODIFIED**: `src/channel_config.py` - builds CHANNELS from registry
- **MODIFIED**: `scripts/launch.py` - browser rotation reads registry

---

## 2026-02-03 - OOPS Page Switchboard Telemetry in dom_automation

**WSP References**: WSP 22 (ModLog), WSP 77 (Agent Coordination)

### What
Added orchestration switchboard OOPS breadcrumb emission to `dom_automation.py`'s `handle_oops_page()` method.

### Why
OOPS page recovery events were invisible to the orchestration layer. The switchboard now receives `oops_page_detected` and `oops_page_recovered` signals from the scheduler's DOM automation, enabling pattern tracking and intelligent escalation (e.g., recommend alternate browser after repeated OOPS).

### Files
- **MODIFIED**: `src/dom_automation.py` - Added `_emit_oops_signal()` helper + switchboard import + emission points in `handle_oops_page()`

---

## 2026-02-01 - Content Page Scheduler (Inline Popup + Calendar Audit)

**WSP References**: WSP 22 (ModLog), WSP 49 (Module Structure), WSP 3 (Organization)

### What
New `ContentPageScheduler` class that schedules videos directly from the YouTube Studio Content table (video list view) instead of navigating to individual video edit pages.

### Why
1. **Faster**: No per-video page navigation — stays on content table, clicks inline visibility popup
2. **Reschedule**: Can change dates on already-scheduled videos (calendar slot optimization)
3. **Calendar Audit**: Reads scheduled dates from table, detects conflicts (same time slot) and clustering (>8/day)
4. **Fallback**: When per-video `schedule_video()` fails (click_save timeout), falls back to Content Page approach

### Files
- **NEW**: `src/content_page_scheduler.py` (~580 lines) — ContentPageScheduler class, calendar audit, standalone entry point
- **MODIFIED**: `scripts/launch.py` — CPS fallback on per-channel errors, CLI `--content-page` / `--audit` flags

### CLI
```bash
python -m ...launch --content-page --browser edge --channel-key foundups --mode schedule
python -m ...launch --audit --browser edge --channel-key move2japan
```

---

## 2026-02-01 - Cooperative Stop Signal for Thread Safety

**WSP References**: WSP 22 (ModLog), WSP 50 (Pre-Action)

### Problem
`run_multi_channel_scheduler()` runs inside `asyncio.to_thread()`. When the DAE's `asyncio.wait_for()` timeout fires, the Python thread can't be interrupted — it keeps driving the browser, causing contention with the next cycle's comment engagement.

### Fix
- `scripts/launch.py`: Added `stop_event: threading.Event` parameter to `run_multi_channel_scheduler()`
- Two cooperative check points in the channel loop:
  1. Before each channel starts (aborts before account swap)
  2. After each channel completes (aborts before next channel)
- When `stop_event.is_set()`, scheduler logs `[STOP]` and breaks out of the channel loop
- Origin URL restore still runs (after the loop, not inside it)
- Backward compatible: `stop_event=None` (default) preserves existing behavior

---

## 2026-01-31 - Time Jitter Fix: Snap to :15 Intervals

**WSP References**: WSP 22 (ModLog), WSP 50 (Pre-Action)

### Problem
YouTube Studio only accepts schedule times on 15-minute boundaries (:00, :15, :30, :45). The `_add_time_jitter()` function used `random.randint(-20, +20)` producing arbitrary minutes like `:09`, `:47` which YouTube Studio rejected or rounded unpredictably.

### Fix
- `src/schedule_tracker.py`: Replaced minute-based jitter with **15-minute step jitter**
  - `MAX_JITTER_STEPS = 2` (replaces `MAX_JITTER_MINUTES = 20`)
  - Jitter now picks random steps in `[-2, +2]`, each step = 15 minutes
  - From base "3:00 PM" can produce: 2:30, 2:45, 3:00, 3:15, 3:30 PM
  - All outputs guaranteed on :00/:15/:30/:45 boundaries

---

## 2026-01-31 - Schedule Auditor + Slot Spread + Stale Video Recovery

**WSP References**: WSP 22 (ModLog), WSP 50 (Pre-Action), WSP 80 (DAE Pattern)

### Context
Multiple issues discovered during production scheduling:
- RavingANTIFA stuck at batch 112 (infinite loop on stale videos)
- Tracker recorded false positives (DOM reported success, YouTube didn't schedule)
- 3 slots/day too few for high-volume channels
- No independent verification of scheduled state
- PRIVATE videos not processable after UNLISTED exhausted

### Changes

**`src/schedule_tracker.py`**:
- Added **global dedup guard** in `increment()`: prevents duplicate video IDs across dates
- Added **`remove_video(video_id)`** method: purges false positives from tracker, decrements date count, cleans empty dates safely (dict mutation guard via `list(keys())`)
- Fixed existing duplicate in Move2Japan tracker (`kYneETZCt0Y` on Jan 19)

**`src/scheduler.py`**:
- **Stale-video detection + auto-purge** (lines 445-492): When all videos in a batch are skipped as "already scheduled" but YouTube still shows them as unlisted:
  1. First detection: Purges stale IDs from tracker via `remove_video()`, retries next batch
  2. Second detection (same cycle): Breaks with clear error (prevents infinite loop)
  - Safety: `_stale_purged` flag ensures only one purge per cycle
- **Post-cycle audit integration** (opt-in via `YT_SCHEDULER_POST_AUDIT=true`):
  - Imports `ScheduleAuditor`, runs audit after scheduling
  - Reports false positives, time collisions, auto-healed count
  - Auto-heal via `YT_SCHEDULER_AUDIT_AUTO_HEAL=true`

**`src/schedule_auditor.py`** (NEW):
- **Independent Layer 2 verification** — reads YouTube Studio SCHEDULED filter via DOM
- `run_audit(auto_heal=False)`: Full audit comparing YouTube state vs tracker JSON
  - Detects: false positives, missing from tracker, time collisions
  - Optional auto-heal: purges false positives from tracker
- `check_tracker_integrity()`: Offline check for count mismatches, duplicate IDs, past dates
- `run_schedule_audit()`: Standalone entry point with browser connection
- Scrapes scheduled video rows: video_id, title, date, time from visibility column

**`src/channel_config.py`**:
- **8 slots per day** (every 3 hours) replaces 3 slots/day:
  - All channels: 12AM, 3AM, 6AM, 9AM, 12PM, 3PM, 6PM, 9PM
  - `max_per_day` changed from 3 to 8
- Move2Japan/UnDaoDu: Asia/Tokyo timezone
- FoundUps/RavingANTIFA: America/New_York timezone

**`src/dom_automation.py`**:
- Added `"PRIVATE"` to supported visibility filter options
- Updated docstrings for `navigate_to_shorts_with_fallback()` and `_apply_filter_via_dom()`

### Architecture

```
Layer 1: SCHEDULING (existing)
  scheduler.py -> schedule_tracker.py -> memory/*.json
  Writes: schedules videos, tracks in JSON + DBA

Layer 2: AUDITING (new)
  schedule_auditor.py -> reads YouTube DOM + tracker JSON
  Reads: compares actual vs tracked, detects discrepancies
  Optional: auto-heals tracker (purge false positives)
```

### Production Data (as of 2026-01-31)
- Move2Japan: 192 videos scheduled, Jan 28 -> Apr 2 (8 slots/day going forward)
- UnDaoDu: 33 videos scheduled, Jan 30 -> Feb 9
- RavingANTIFA: 4 videos scheduled, Jan 31 -> Feb 1 (2 false positives purged)

### ADR-021: Stale Video Recovery Pattern
- When tracker says "scheduled" but YouTube says "unlisted", the prior DOM action failed silently
- `schedule_video()` returned True but YouTube didn't actually commit the schedule
- Fix: Purge from tracker and retry ONCE per cycle, break on second failure
- Future: Post-cycle auditor provides independent verification

---

## 2026-01-30 - Edge Filter Click Hardening (6-Step Retry)

**WSP References**: WSP 22 (ModLog), WSP 50 (Pre-Action Verification)

### Problem
Edge browser stuck in filter click loop — clicking filter but NOT clicking Visibility.
Edge shadow-DOM takes 800-1500ms to render dropdowns vs Chrome's ~300ms.

### Fix
`src/dom_automation.py` — All 6 filter steps hardened with retry+verify:

| Step | Action | Retries | Wait | Verification |
|------|--------|---------|------|-------------|
| 2 | Visibility click | 3 | 1.5s/2.5s/4.0s | Dropdown visible |
| 3 | Dialog open | 3 | 2.0s/3.5s/5.0s | Force-open fallback |
| 4 | Checkbox click | 3 | 1.0s/2.0s/3.0s | State changed |
| 5 | Apply button | 3 | 1.0s/2.0s/3.0s | Dialog dismissed |
| 6 | Chip verify | 3 | 1.0s/2.0s/3.0s | Chip text found |

---

## 2026-01-29 - Fluid Dual-Browser Architecture

**WSP References**: WSP 22 (ModLog), WSP 72 (Module Independence)

**Context**
- Both Google accounts are now logged into BOTH browsers (Chrome & Edge)
- This enables any browser to access any channel via account picker
- Previous architecture locked channels to specific browsers unnecessarily

**Changes**
`src/channel_config.py`:
- Added `CHROME_PORT = 9222`, `EDGE_PORT = 9223`, `ALL_PORTS` constants
- Added `preferred_port` (optimization) and `available_ports` (fluid access) to each channel
- Added `account_section` for account picker index mapping
- Added helper functions:
  - `is_port_available(port)`: Check if browser debug port is responding
  - `get_available_browsers()`: Return list of running browser ports
  - `select_browser_for_channel(channel_key, current_port)`: Smart browser selection

**Browser Selection Strategy**:
1. Reuse current browser if it can access the target channel (minimize switches)
2. Use preferred_port if available
3. Fall back to any available port

**Account Picker Structure** (same on both browsers):
```
Section 0 (Google Account A): UnDaoDu, Move2Japan
Section 1 (Google Account B): FoundUps, RavingANTIFA
```

**Result**
- Chrome (9222) can access ALL 4 channels
- Edge (9223) can access ALL 4 channels
- System automatically selects best browser based on availability
- Legacy `chrome_port` field preserved for backward compatibility

---

## 2026-01-29 - Infinite Loop Bug Fix (Slots Exhausted)

**WSP References**: WSP 22 (ModLog), WSP 50 (Pre-Action Verification)

**Problem**
- Scheduler stuck in infinite loop at BATCH 107
- When scheduling slots were exhausted, `break` only exited inner `for` loop
- Outer `while True` loop continued indefinitely, repeating same batch

**Root Cause**
- Line 320: `break` inside `if not slot:` only exits `for video in videos_to_process:`
- The `while True:` loop has no check for "slots exhausted" condition
- Result: Loop keeps navigating back and retrying with no slots available

**Fix**
`src/scheduler.py`:
- Added `slots_exhausted = False` flag before inner for loop (line 282)
- Set `slots_exhausted = True` when no slots available (line 321)
- Added check after for loop (lines 431-435):
  ```python
  if slots_exhausted:
      results["message"] = f"All scheduling slots filled after {batch_num} batches"
      logger.info(f"[SCHEDULER] Slots exhausted - stopping continuous processing")
      break
  ```

**Result**
- Scheduler now exits cleanly when all scheduling slots are filled
- Clear log message: "Slots exhausted - stopping continuous processing"
- Results include meaningful message about batches processed

---

## 2026-01-28 - Sort by Oldest First Feature

**WSP References**: WSP 22 (ModLog), WSP 50 (Pre-Action Verification)

**Problem**
- After filtering for UNLISTED visibility, videos were processed in default order (newest first)
- FIFO principle violated: oldest uploaded videos should be scheduled first

**Solution**
`src/dom_automation.py`:
- Added `DATE_HEADER_SORT_CSS` and `DATE_HEADER_SORT_XPATH` selectors
- Added `sort_by_date_oldest()` method that:
  - Finds the Date column header sort button
  - Checks current sort state (ascending/descending/none)
  - Clicks to sort ascending (oldest first) if not already sorted
- Integrated into `navigate_to_shorts_with_fallback()`:
  - Called after filter is applied
  - Called at all three return points (filter already applied, UI-TARS verified, fallback)

**Flow After Fix**
1. Navigate to shorts page
2. Apply UNLISTED visibility filter
3. **NEW**: Sort by date (oldest first)
4. Get videos → now in oldest-first order
5. Process videos sequentially

**Result**
- Oldest unlisted videos are now scheduled first (FIFO order)
- Videos waiting the longest get priority

---

## 2026-01-28 - Index Weaving Silent Failure Fix + Enhanced Stubs

**WSP References**: WSP 22 (ModLog), WSP 50 (Pre-Action Verification), WSP 73 (Digital Twin)

**Problem**
- Index weaving was failing silently for unlisted videos
- `YT_SCHEDULER_INDEX_MODE=gemini` was configured, but Gemini API CANNOT access unlisted videos
- No fallback to stub mode when Gemini failed
- No logging when indexing skipped
- Stub indexes had empty `key_points` producing minimal description context
- FFCPLN acronym order was incorrect ("F*** Fake" vs "Fake F***")

**Root Cause**
1. **Gemini API limitation**: Cannot analyze UNLISTED YouTube videos (requires public URL)
2. **Silent failure**: When `ensure_index_json()` failed, no logging, no fallback
3. **Minimal stub data**: Stub index had `key_points: []` - no description context

**Fix**
`src/scheduler.py`:
- Added Gemini-to-stub fallback when Gemini fails
- Added warning log when indexing fails: `[SCHEDULER] Gemini indexing failed ({error}), falling back to stub`
- Added warning log when indexing skipped entirely

`src/index_weave.py`:
- Added `_extract_topics_from_title()` - extracts FFCPLN, MAGA, ICE, etc. from title
- Added `_generate_key_point_from_title()` - creates meaningful key point from title
- Enhanced `create_stub_index_json()` to populate `key_points` and `topics` from title
- Stub now produces richer description context even without Gemini

`src/content_generator.py`:
- Fixed all 5 instances of FFCPLN acronym: "Fake F*** Christian Pedo-Lovin' Nazi"

**Recommendation**
For unlisted video scheduling, use `YT_SCHEDULER_INDEX_MODE=stub` (default).
Only use `gemini` mode for PUBLIC videos or post-publish enrichment.

**Result**
- Indexing no longer fails silently - proper fallback and logging
- Stub indexes now produce meaningful description context from title
- FFCPLN acronym is correct throughout

---

## 2026-01-27 - Scheduler Loop Fix + UI-TARS Verification

**WSP References**: WSP 22 (ModLog), WSP 84 (Reusable Patterns), WSP 91 (Observability)

**Problem**
- Scheduler only processing ONE video per run and exiting
- After `_sync_scheduled_videos()`, browser was on SCHEDULED page, not UNLISTED
- Loop continued with stale video list but wrong page context
- No verification to check if shorts were actually listed before applying filter

**Root Cause**
The `_sync_scheduled_videos()` method navigates to SCHEDULED filter to sync existing schedule,
but never navigated back to UNLISTED before the video processing loop started.

**Fix**
`src/scheduler.py`:
- Added Step 3.5: Navigate back to UNLISTED after sync completes
- Log message: "Returning to unlisted Shorts after sync..."
- Scheduler now processes ALL unlisted videos in one run

`src/dom_automation.py`:
- Added `verify_shorts_listed(use_ui_tars=True)` method
  - Quick DOM check for video rows and filter chips
  - Optional UI-TARS visual verification if DOM check uncertain
  - Returns dict with: shorts_visible, count, method, needs_filter, filter_applied
- Integrated verification into `navigate_to_shorts_with_fallback()`
- If shorts already visible with filter applied, skip redundant filter application

**Result**
- Scheduler now processes ALL unlisted videos in one run (not just 1)
- UI-TARS can verify page state when DOM is uncertain
- Faster navigation when filter already applied
- Better observability of page state

---

## 2026-01-27 - Content-Aware Title Generation + Resume Capability

**WSP References**: WSP 22 (ModLog), WSP 84 (Reusable Patterns), WSP 77 (AI Overseer)

**Problem**
- Title generation was purely template-based with no content awareness
- FFCPLN titles incorrectly used "vs #MAGA" (FFCPLN describes MAGA, not versus)
- No resume capability - system would reprocess already-scheduled videos on restart
- No trending hashtag support for ICE resistance content

**Fix**
`src/schedule_tracker.py`:
- Added `is_video_scheduled(video_id)` - checks if video already in tracker
- Added `get_all_scheduled_video_ids()` - returns list of all scheduled IDs
- Enables resume capability: skip videos that were already processed

`src/scheduler.py`:
- Integrated `is_video_scheduled()` check in video processing loop
- Logs skipped videos with reason "Already scheduled"
- System now picks up where it left off on restart

`src/content_generator.py`:
- Fixed FFCPLN title templates: removed "vs" (FFCPLN describes MAGA, not versus MAGA)
- Added `detect_content_type(index_json)` - detects music/speech/news from index
- Enhanced `extract_title_hint_from_index()` to extract from:
  - Audio transcript summary (Priority 1)
  - Key points metadata (Priority 2)
  - Visual description (Priority 3)
- Added content-type specific templates: `MUSIC_TITLE_TEMPLATES`, `NEWS_TITLE_TEMPLATES`, `SPEECH_TITLE_TEMPLATES`
- Added `TRENDING_ICE_HASHTAGS` with #StopICE #ICEout #ResistICE etc.
- Added `get_trending_ice_hashtags()` and `get_combined_hashtags()`
- Updated `generate_clickbait_title_from_index()` to use content-aware templates

**Result**
- Resume capability: restart won't reprocess videos
- Content-aware titles using actual video index data
- Music vs speech vs news detection for appropriate templates
- Trending ICE resistance hashtags available for descriptions
- FFCPLN correctly describes MAGA (not versus)

---

## 2026-01-27 - Page Content Wait + Retry on Empty Page

**WSP References**: WSP 22 (ModLog), WSP 84 (Reusable Patterns)

**Problem**
- Diagnostic screenshot revealed page loading with **empty content area** (no videos, no filter bar)
- ChromeDriver crash during `wait_for_element(VIDEO_TABLE)` prevented page from fully rendering
- DOM fallback filter can't work when page structure isn't loaded

**Root Cause Analysis**
Screenshot `diag_url_filter_failed_20260127_132846.png` showed:
- Shorts tab selected ✓
- Content area completely empty ✗
- No filter bar visible ✗
- No video table visible ✗

**Fix**
`src/dom_automation.py`:
- Added `_wait_for_page_content(timeout)` - waits for video table OR filter bar OR chip bar
- Added retry mechanism (3 attempts with page refresh) in `navigate_to_shorts_with_fallback()`
- Uses JavaScript to check multiple indicators simultaneously (faster than individual element waits)

**Page Ready Indicators**
```javascript
{
  hasVideoTable: !!document.querySelector('ytcp-video-row'),
  hasFilterBar: !!document.querySelector("input[placeholder='Filter']"),
  hasChipBar: !!document.querySelector('ytcp-chip-bar'),
  hasContentHeader: !!document.querySelector('.video-table-content, #video-list')
}
```

**Result**
- Page refresh on empty content (up to 3 retries)
- Better diagnostic: "Page content ready: table=True, filter=True, chips=True"
- Falls back to DOM filter only after confirming page structure loaded

---

## 2026-01-27 - Diagnostic Screenshot & UI-TARS Integration

**WSP References**: WSP 22 (ModLog), WSP 91 (Observability), WSP 77 (AI Overseer)

**Problem**
- When Selenium/WebDriver errors occur, no visual context is captured
- Difficult to diagnose what the browser UI looked like when failures happen
- No way to leverage UI-TARS vision model for visual debugging

**Fix**
`src/dom_automation.py`:
- Added `DIAGNOSTIC_DIR` for storing diagnostic screenshots
- Added `capture_diagnostic_screenshot(context)` - saves screenshots on errors
- Added `get_browser_state()` - captures URL, title, viewport info
- Added `diagnose_failure(context, error)` - full diagnostic capture (screenshot + state)
- Added `diagnose_with_ui_tars(question)` - async UI-TARS visual analysis
- Integrated diagnostics into `navigate_to_shorts_with_fallback()` and `_apply_filter_via_dom()`

**Usage**
```python
# Automatic - diagnostics captured on filter failures
dom.navigate_to_shorts_with_fallback(channel_id, "UNLISTED")

# Manual diagnostic
diagnostic = dom.diagnose_failure("custom_context", error)
print(f"Screenshot: {diagnostic['screenshot']}")

# UI-TARS visual analysis
result = await dom.diagnose_with_ui_tars("Is the visibility filter dropdown open?")
```

**Screenshot Location**
`modules/platform_integration/youtube_shorts_scheduler/memory/diagnostics/`

---

## 2026-01-27 - WebDriver Health Check & Recovery (Symbols not available fix)

**WSP References**: WSP 22 (ModLog), WSP 91 (Observability)

**Problem**
- Shorts Scheduler crashing with "Symbols not available. Dumping unresolved backtrace" errors
- ChromeDriver native crashes during `wait_for_element()` and `execute_script()` operations
- Basic health check (`current_url`) passed but element operations still failed

**Fix**
1. `src/dom_automation.py`:
   - Enhanced `check_driver_health(thorough=True)` to test both URL access AND element finding
   - Added thorough health check to `wait_for_element()` and `wait_for_clickable()`
   - Catches stale WebDriver connections before expensive operations crash

2. `src/scheduler.py`:
   - Added `reconnect_browser(max_retries=3)` with exponential backoff
   - Added `ensure_healthy_connection()` that auto-reconnects on health check failure
   - Added health check at start of `run_scheduling_cycle()` and `run_indexing_cycle()`

**Result**
- Stale WebDriver connections detected early with clear error messages
- Auto-reconnection attempts before failing hard
- "Symbols not available" crashes should be caught and recovered from

---

## 2026-01-27 - Navigation Robustness Fix (WebDriverException Prevention)

**WSP References**: WSP 22 (ModLog), WSP 84 (Reusable Patterns)

**Problem**
- `scheduler.py` used basic `navigate_to_shorts()` which crashes on filter rendering issues.
- `launch.py` already used robust `navigate_to_shorts_with_fallback()` but scheduler did not.

**Fix**
- `src/scheduler.py`:
  - `run_scheduling_cycle()`: Replaced `navigate_to_shorts()` with `navigate_to_shorts_with_fallback()` (line 179)
  - `_sync_scheduled_videos()`: Same fix (line 333)
  - Both now return gracefully on navigation failure instead of crashing

**Result**
- DAE no longer crashes with WebDriverException during navigation cycle
- Consistent with `launch.py` approach (URL-first + DOM fallback)

## 2026-01-21 - Digital Twin Index Utility Routing (Documented)


**WSP References**: WSP 22 (ModLog), WSP 73 (Digital Twin), WSP 60 (Memory)

**Changes Made**
1. Documented index utility routing (012 voice → Digital Twin, music/video → RavingANTIFA/faceless pipeline).

## V0.1.0 - Initial Module Creation (2025-12-31)

### Created
- Module structure following WSP 49
- README.md with architecture overview
- INTERFACE.md with public API documentation
- Channel configuration for Move2Japan, UnDaoDu, FoundUps
- DOM automation layer with comprehensive selectors
- Schedule tracker with JSON persistence
- Core scheduler orchestrator

### Architecture Decisions
- **ADR-001**: Use Selenium over YouTube API for scheduling
  - Reason: YouTube Data API doesn't support scheduling - only visibility changes
  - Trade-off: More fragile (DOM changes) but enables full automation

- **ADR-002**: Time slots based on audience geography
  - Move2Japan/UnDaoDu: Japan timezone, targeting US viewers
  - FoundUps: EST timezone, targeting US viewers

### WSP Compliance
- WSP 3: Platform Integration domain
- WSP 49: Standard module structure
- WSP 80: DAE pattern ready
- WSP 22: This ModLog

### Implementation Complete
- [x] channel_config.py - Multi-channel support (Move2Japan, UnDaoDu, FoundUps)
- [x] dom_automation.py - Comprehensive Selenium selectors for YouTube Studio
- [x] schedule_tracker.py - JSON persistence with smart slot allocation
- [x] content_generator.py - FFCPLN clickbait titles/descriptions
- [x] scheduler.py - Main orchestrator with DAE entry point
- [x] tests/test_scheduler.py - Unit tests (integration tests require browser)

### Next Steps
- [x] Integration with existing Chrome debug sessions (port 9222/9223)
- [ ] UI-TARS visual verification for complex dialogs
- [ ] Queue management for multi-channel scheduling
- [ ] Add memory/ directory for schedule persistence

## V0.8.1 - Filter UI Regression Fix (2026-01-17)

### Problem
- Shorts Scheduler failed at Layer 1 fallback with: `[DOM] Filter input not found after waiting`.
- Root cause: production fallback in `src/dom_automation.py` relied on a **single** selector (`input[placeholder='Filter']`) while Studio UI variants sometimes render a different filter control (or require a coordinate click to open the dropdown).

### Fix
- `src/dom_automation.py`:
  - `navigate_to_shorts_with_fallback()` now waits longer (up to ~8s) for the **Visibility chip** to appear before declaring URL-filter failure.
  - `_apply_filter_via_dom()` now uses a multi-strategy opener (`_open_filter_ui()`):
    - multiple selectors for the filter input
    - coordinate click fallback (`FILTER_ICON_COORDS`)
    - JS `elementFromPoint` fallback
  - Added best-effort chip verification after DOM fallback.
 - `scripts/launch.py`:
   - Hot-reload `src/dom_automation.py` inside `run_shorts_scheduler()` to prevent stale in-memory imports when running from a long-lived `main.py` menu session.

## V0.8.2 - Schedule Inputs Stabilized + Schedule DBA Write (2026-01-18)

### Scheduling Fix (Current Studio DOM)
- Scheduling date/time inputs are not reliably exposed as aria-labeled inputs until clicked.
- Implemented selector-backed flow:
  - Click date trigger (`ytcp-text-dropdown-trigger#datepicker-trigger div.left-container`)
  - Type into date picker popup (`ytcp-date-picker ... input.tp-yt-paper-input`) using Ctrl+A replace
  - Type into time-of-day input (`ytcp-form-input-container#time-of-day-container ... input.tp-yt-paper-input`) using Ctrl+A replace

### DBA Write (PatternMemory)
- Added `src/schedule_dba.py` to record scheduling outcomes to the existing WRE SQLite DBA:
  - DB: `modules/infrastructure/wre_core/data/pattern_memory.db`
  - Skill name: `youtube_shorts_scheduler_schedule`
- Wired into:
  - `src/scheduler.py` (DAE orchestration path)
  - `scripts/launch.py` (main.py submenu path)

### WSP Notes
- Uses SKILLz naming (WSP 95) for fast skill discovery.
- Adds machine-readable recall of schedule events for 0102 (WSP 60 / WSP 48 via PatternMemory).

## V0.8.3 - Schedule → Index Weave (Digital Twin Description Block) (2026-01-18)

### Added
- `src/index_weave.py`:
  - Ensures `memory/video_index/{channel}/{video_id}.json` exists (Gemini Tier 1) when enabled
  - Builds compact `0102 DIGITAL TWIN INDEX v1` JSON block for description-as-cloud-memory
  - Updates index JSON with `scheduling` + `description_sync` after successful schedule

### Changed
- `src/scheduler.py`:
  - When `YT_SCHEDULER_INDEX_WEAVE_ENABLED=true` (default), scheduler weaves index block into the description during metadata update.
  - After successful schedule, updates the local index JSON with scheduling fields.

### Tests
- `tests/test_scheduler.py`:
  - Added unit tests for `index_weave` helpers (no browser required).

### WSP Compliance
- **WSP 60**: Index JSON is a memory artifact (`memory/video_index/...`)
- **WSP 73**: Digital Twin memory block embedded in description (“cloud memory”)
- **WSP 27**: Scheduler triggers indexing as a secondary layer (Occam layering)

## V0.8.4 - Dialog Done/Save Click Scoped (Avoid Timezone Misclick) (2026-01-18)

### Problem
- In some current Studio variants, after setting date/time, the script could click the **timezone selector** instead of the dialog’s **Done/Save** action.
- This blocks completion of the schedule layer (dialog never commits).

### Fix
- `src/dom_automation.py` `click_done()`:
  - Scoped dialog Save selector to `tp-yt-paper-dialog#dialog div.button-area ytcp-button#save-button` (the actual dialog action area)
  - Added a safety guard to skip any element inside `#timezone-select-button`
  - Tightened the JS fallback to only click `#done-button` or dialog `#save-button` (no generic “Save” text search)

### Test
- `tests/test_layer3_schedule.py`:
  - Added `--click-done` flag to click dialog Done/Save **without** performing page-level Save (safe validation of dialog action)

### WSP Notes
- WSP 50: Pre-action verification using DOM-path evidence from live Studio
- WSP 22: This ModLog memory artifact for DOM drift + mitigation

## V0.8.5 - 012 Digital Twin Interaction Wiring (human_behavior) (2026-01-18)

### Problem
- Several UI actions still used raw Selenium `.click()` / direct field `.click()` patterns.
- This produces brittle interaction timing and a detectable automation signature.

### Fix
- `src/dom_automation.py`:
  - `YouTubeStudioDOM` now binds to `modules.infrastructure.foundups_selenium.src.human_behavior` when available.
  - `safe_click()` now prefers `human_behavior.human_click()` (+ human scroll) and falls back to Selenium/JS only when needed.
  - Added a 012-modeled coordinate click path for viewport clicks (Bezier cursor path), used by legacy coordinate fallbacks.
  - Scheduling flow (date/time) and metadata edits now use `safe_click()` for focus/click.

### WSP Notes
- WSP 91: anti-detection + observability alignment via reusable 012 interaction lego block
- WSP 84: reuse infrastructure behavior module rather than re-implementing ad hoc click logic

## V0.8.6 - 012 Scheduler Speed + Date-First Precise Click (2026-01-18)

### Problem
- With 012-modeled movement enabled, the schedule UI is dense (date/time/timezone adjacent).
- Observed behavior: scheduler sometimes clicks **time/timezone before date**, causing the date picker not to open and Ctrl+A/select-all to target the wrong surface.

### Fix
- `src/dom_automation.py`:
  - Added scheduler-scoped tuning:
    - `YT_SCHEDULER_O12_SPEED_MULT` (default `0.75`) to speed up 012 movement pauses without impacting other DAEs.
    - `YT_SCHEDULER_O12_PRECISE_CLICK` (default `true`) to use a position-stable click path.
  - `set_schedule_date()` now uses a **precise date-trigger click** first to avoid drifting onto time/timezone.

## V0.8.7 - Occam 012: Deterministic Clicks (No Mouse Jumping) (2026-01-18)

### Problem
- Bezier/jitter-based mouse paths can “jump” across dense schedule UI (date/time/timezone cluster).
- This can mis-target controls and destabilize the date picker open → type cycle.

### Fix
- `src/dom_automation.py`:
  - Removed scheduler coupling to `human_behavior` for clicks (kept slow/steady 012 cadence).
  - `safe_click()` now uses:
    - `scrollIntoView` → delay → `.click()` → delay
    - ActionChains/JS fallbacks only if needed
  - Added scheduler knobs:
    - `YT_SCHEDULER_PRE_CLICK_DELAY_SEC` (default `0.25`)
    - `YT_SCHEDULER_POST_CLICK_DELAY_SEC` (default `0.25`)

### Result
- Live Layer 3 `--click-done` validated: date/time set, then dialog Done/Save clicked (no timezone misclick).

## V0.8.8 - Page Save Button Hardening + Full-Cake Runner Uses Production Scheduler (2026-01-18)

### Problem
- Full-cake automation could complete indexing + title + description + schedule dialog Done/Save, but fail at the final **page-level Save** due to DOM drift (custom elements, missing stable ids).

### Fix
- `src/dom_automation.py`:
  - Hardened `click_save()`:
    - waits for dialog close
    - multi-selector cascade (`ytcp-button#save-button` wrappers + `button#save-button`)
    - JS fallback: find visible elements with text `Save` and click inner button if present
  - Added `YT_SCHEDULER_PRE_SAVE_DELAY_SEC` to let dialog close animation complete before save attempt.
- `tests/test_full_chain.py`:
  - Now runs the production orchestrator (`run_scheduler_dae`) with feature flags enabled (no duplicated selectors).

### Result
- Live full cake validated: scheduler returned `total_scheduled: 1` (includes save).

## V0.8.9 - Launcher Stability: Close Session-Restore Extra Tabs (2026-01-18)

### Problem
- Chrome/Edge session restore can open multiple tabs, which can confuse Selenium focus and cause DOM actions to target the wrong tab.

### Fix
- `scripts/launch.py`:
  - Close all extra tabs on connect and keep only the primary tab handle before starting automation.

## V0.9.1 - Oops Page Recovery Layer (Account Switching) (2026-01-19)

### Problem
- When navigating to YouTube Studio for a channel, the browser may land on an "oops" error page if the wrong Google account is logged in.
- This blocks all automation until manually fixed.
- Chrome/Edge browser-channel mapping:
  - **Chrome (9222)**: Move2Japan, UnDaoDu
  - **Edge (9223)**: FoundUps, RavingANTIFA

### Fix
- `src/dom_automation.py`:
  - Added **Oops Page selectors** to `DOMSelectors`:
    - `OOPS_SWITCH_ACCOUNT` - Switch account link on oops page
    - `CHANNEL_SWITCHER_AVATAR` - Avatar button
    - `SWITCH_ACCOUNT_MENU_XPATH` - Switch account menu item
    - `ACCOUNT_ITEM_BY_NAME_TEMPLATE` - Account selection by name
  - Added **`CHANNEL_ACCOUNT_MAP`** mapping channel IDs to account names:
    - `UC-LSSlOZwpGIRIYihaz8zCw` → Move2Japan
    - `UCfHM9Fw9HD-NwiS0seD_oIA` → UnDaoDu
    - `UCSNTUXjAgpd4sgWYP0xoJgw` → FoundUps
    - `UCVSmg5aOhP4tnQ9KFUg97qA` → RavingANTIFA
  - Added **`detect_oops_page()`** - Detects oops page via `#selectaccount-link`
  - Added **`handle_oops_page(target_channel_id)`** - Automated recovery flow:
    1. Click "Switch account" on oops page
    2. Click avatar button on YouTube
    3. Click "Switch account" in menu
    4. Select target account from list
    5. Navigate back to target channel
  - Added **`navigate_with_oops_recovery(channel_id, url)`** - Wrapper with auto-recovery

### Flow Diagram
```
Oops Page → Click "Switch account" → YouTube Page
    ↓
Click Avatar → Click "Switch account" Menu → Account List
    ↓
Select Account → Navigate to Target Channel → Verify (no oops)
```

### WSP Notes
- WSP 50: Pre-action detection before proceeding with navigation
- WSP 84: Reusable recovery pattern for all browser automation
- WSP 22: This ModLog documents the recovery layer

### Testing
- Requires Chrome/Edge with debug port (9222/9223) active
- Test via: Navigate to wrong-account channel, verify recovery

## V0.9.0 - Scheduler Control Plane (Content-Type Placeholder + Index Switches) (2026-01-18)

### Problem
- Scheduler switches were scattered (some in module submenu, some in main controls), increasing the odds of misconfigured runs.
- Next layer requires a **content-type selection** surface (Shorts vs Videos) before implementing new DOM selectors.

### Fix
- `main.py`:
  - Added a dedicated `Scheduler Controls` submenu under YouTube Controls.
  - Introduced placeholder control-plane env vars:
    - `YT_SCHEDULER_CONTENT_TYPE=shorts|videos` (videos is placeholder until implemented)
    - `YT_SCHEDULER_VERIFY_MODE=none|wre-tars` (intent flag; production does not hard-require UI‑TARS)
  - Centralized index weave switches: enable/disable, mode, description weave, title hint, and pre-save delay.

### WSP Notes
- WSP 15: Control-plane enables high-impact work sequencing without destabilizing Shorts PoC
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
