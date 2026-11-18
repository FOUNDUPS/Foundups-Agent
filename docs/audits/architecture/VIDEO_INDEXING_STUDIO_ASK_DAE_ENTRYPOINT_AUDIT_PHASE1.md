# Video Indexing / Studio Ask / DAE Entrypoint Audit (Phase 1)

- Lane: W9 / AUDIT (read-only)
- Status: DECISION-ONLY (no code/SKILLz/scheduler/menu/WSP/registry/manifest/CI/dependency change)
- Base: origin/main 5461fb4f7
- Date: 2026-06-16
- WSP refs: WSP_00, WSP_50/WSP_87 (HoloIndex pre-action), WSP_97 (Truth Boundary), WSP_22 (ModLog)
- Method: 4 parallel read-only discovery lanes (menu / DAE+heartbeat / indexer+SKILLz / shorts-scheduler) over a clean origin/main worktree + 1 adversarial sentinel. Every claim is file:line-backed; HoloIndex was discovery-only.

---

## 1. Executive Summary

The YouTube indexing menu MISREPRESENTS its providers, and the cleanest indexing execution seam (the DAE Phase 2 path) is correct and reusable - but the Shorts Scheduler is NOT a safe place to run an indexing "test" because it mutates live YouTube metadata as an inseparable part of indexing.

Load-bearing findings (all sentinel-verified):
1. Menu option 1 is labeled `[GEMINI] Gemini AI Indexing` but runs **Studio Ask** browser automation (`run_video_indexing_cycle`). Option 4 `[TEST] Test Video Indexing (single video)` is the **Gemini API** (`GeminiVideoAnalyzer`), NOT Studio Ask. Two label/provider mismatches (sentinel UPHELD).
2. There is **NO bounded single-video Studio Ask test entrypoint** in the menu today. The single-video method `StudioAskIndexer.ask_about_video` exists (studio_ask_indexer.py:453) but is unwired; every Studio Ask menu path runs the FULL cycle (option 1 hardcodes max_videos_per_channel=9999) (sentinel UPHELD).
3. The main YouTube DAE ALREADY has the correct Phase 2 indexing execution seam (auto_moderator_dae.py:1563-1582, gated chrome + YT_VIDEO_INDEXING_ENABLED, emits ActivityType.VIDEO_INDEXING). Do NOT duplicate it (sentinel UPHELD).
4. The DAE heartbeat OBSERVES only; it never executes `run_video_indexing_cycle` (sentinel UPHELD).
5. `studio_ask_indexer.py` is already on the #817 "Ask Studio" header-primary selector model; the stale watch-page selectors are demoted to labelled fallback (USE_WATCH_PAGE=False). The `transcript_ask` SKILLz BODY is still stale (documents the old watch-page selectors) and correctly remains `prototype`.
6. CRITICAL / NEEDS_012: the Shorts Scheduler ALREADY consumes the video-index artifact (good - no duplicate store), but it OWNS Studio Ask/Gemini indexing AND **mutates live YouTube title/description (and save_video) during the index step**, including its "INDEXING-ONLY MODE" (sentinel REFUTED the "read-only consumer" assumption).

Recommended next slice: `VIDEO_INDEXING_STUDIO_ASK_MENU_AND_SKILL_ENTRYPOINT_PHASE1` (relabel menu, add a bounded single-video Studio-Ask test wired to `ask_about_video`, explicit provider naming, SKILLz body update). The scheduler metadata-coupling is a SEPARATE NEEDS_012 decision (`SHORTS_SCHEDULER_INDEX_METADATA_DECOUPLING`).

---

## 2. Phase 0 HoloIndex Retrieval Report

| # | Query | Top relevant hit | Quality | Found edit target? |
|---|-------|------------------|---------|--------------------|
| 1 | Studio Ask indexer run_video_indexing_cycle menu Gemini Test | studio_ask_indexer.py + indexing_menu.py | HIGH | YES (indexer + menu) |
| 2 | DAE Phase 2 YT_VIDEO_INDEXING_ENABLED ActivityType VIDEO_INDEXING | studio_ask_indexer.py, video_indexer.py | MEDIUM | partial (indexer core; NOT auto_moderator_dae) |
| 3 | transcript_ask SKILLz Studio Ask header selector | transcript_ask/executor.py, validator.py | HIGH | YES (SKILLz files) |
| 4 | shorts scheduler description generation video_index memory | video_index_store.py, video_indexer.py | LOW | NO (missed scheduler index_weave.py) |
| 5 | VideoIndexStore memory video_index scheduler hashtags | video_index_store.py, cli.py | LOW | NO (missed scheduler) |

Retrieval verdict: the `video_indexer` module is well-indexed (q1/q3 HIGH). HoloIndex MISSED the Shorts Scheduler consumption seam (`youtube_shorts_scheduler/src/index_weave.py`) on q4/q5 - recorded as `HOLOINDEX_LOW_SIGNAL` for the scheduler->index link; the scheduler lane found it by direct read. No HoloIndex hit was used as proof.

---

## 3. Current Menu Reality Matrix

`modules/infrastructure/cli/src/indexing_menu.py` (reached via main -> 1 YouTube DAEs -> 8 YouTube Indexing):

| Option | Label (operator sees) | Actual provider | Browser? | Writes | Risk |
|--------|-----------------------|-----------------|----------|--------|------|
| 1 | `[GEMINI] Gemini AI Indexing` | **STUDIO_ASK** (run_video_indexing_cycle; studio_ask_indexer.py:876) | yes (9222/9223) | memory/video_index/{channel} | HIGH - MISLABEL; max_videos_per_channel=9999 (ALL) |
| 2 | `[DAEMON] Continuous Indexing` | **STUDIO_ASK** (run_video_indexing_cycle) | yes | memory/video_index/{channel}; STOP file memory/STOP_VIDEO_INDEXER | HIGH - 24/7; bounded-able via per-cycle limits |
| 3 | `[LOCAL] Whisper Indexing` | OTHER (faster-whisper) + Selenium video LISTING | partial | ChromaDB | MEDIUM |
| 4 | `[TEST] Test Video Indexing (single video)` | **Gemini API** (GeminiVideoAnalyzer.analyze_video; gemini_video_analyzer.py:336) | no | memory/video_index/test | MEDIUM - MISLABEL (it is Gemini API, the only single-video path, NOT Studio Ask) |
| 5 | `[BATCH] Batch Index Channel` | **Gemini API** (subprocess batch_index_videos.py) | no | memory/video_index/{channel} | MEDIUM - bulk API cost |
| 6 | `[ENHANCE] Batch Enhance Videos` | OTHER (Grok -> OpenAI -> Gemini rotation) | no | enhances existing JSON in place | MEDIUM |
| 7 | `[TRAIN] Extract Training Data` | OTHER (local Gemma filter) | no | memory/training_data/{channel} | LOW |

- Q1 (Studio Ask entrypoints): options **1, 2** (indexing_menu.py:69,79,141,167,179).
- Q2 (Gemini API entrypoints): options **4, 5** (indexing_menu.py:235,239; :285,293; gemini_video_analyzer.py:297,365). PLUS an optional in-cycle Gemini enrichment pass inside run_video_indexing_cycle gated on `GEMINI_API_KEY` (studio_ask_indexer.py:991-1029).
- Q3 (single-video Studio Ask test): **GAP CONFIRMED**. `StudioAskIndexer.ask_about_video` (studio_ask_indexer.py:453) is the single-video method but is unwired to any menu option; option 4 (the only single-video "Test") routes to the Gemini API instead.

---

## 4. DAE Phase 2 / Heartbeat Boundary

- Q4 (Phase 2 seam): **EXISTS and correct.** `auto_moderator_dae.py:1563-1582` (inside `_browser_engagement_loop`), placed AFTER Phase 1 comment engagement (:1551-1559) and before Phase 3 shorts (:1584+). Gated `browser_name == "chrome" AND YT_VIDEO_INDEXING_ENABLED` (:1566), imports + `await run_video_indexing_cycle(browser=browser_name)` (:1568-1570), signals `ActivityType.VIDEO_INDEXING` (:1571-1578). Non-fatal try/except. **REUSE this seam; do not duplicate.**
- Q5 (heartbeat): **OBSERVES, does not execute.** `_heartbeat_loop` (:2133-2582) has zero `run_video_indexing_cycle` / `VIDEO_INDEXING` references. It writes telemetry (SQLite :2197-2207, JSONL :2246-2274), and its OODA branch only emits breadcrumbs (:2425) + PatternMemory outcomes (:2454); the only activity it actively launches is comment engagement (:2569). Matches the ruling: heartbeat observes status / stale / last-success, does not execute indexing.
- Q9 (safe one-cycle/one-video gates): (1) `YT_VIDEO_INDEXING_ENABLED` truthy - checked at the DAE seam (auto_moderator_dae.py:1566, default `false`) and re-checked in the indexer (studio_ask_indexer.py:896, default `true`); the seam default OFF is the effective master switch. (2) `browser == chrome` at the seam (Edge never reaches Phase 2). (3) STOP-file kill switch `memory/STOP_VIDEO_INDEXER` (studio_ask_indexer.py:38,899-901, re-checked per video). (4) `max_videos_per_channel` (default 3; set to 1 for one video). (5) Channel scope auto-filtered by browser via `youtube_channel_registry.group_channels_by_browser(role="indexing")` (studio_ask_indexer.py:907-928), preventing wrong-account collisions. `GEMINI_API_KEY` gates only the optional enrichment, safe to omit.

---

## 5. transcript_ask SKILLz Staleness Assessment

Classification: **PROTOTYPE with STALE body selectors.**
- Frontmatter is correct: `promotion_state: prototype`, `evals: []` (SKILLz.md:11-12).
- The Phase 1 notice header (SKILLz.md:26-47) correctly marks the watch-page `button[aria-label="Ask"]` path STALE and points to the #817 "Ask Studio" header model.
- BUT the instructional BODY is still stale: the Architecture diagram (:65-77, `youtube.com/watch?v=...`, `Click Ask button (aria-label=Ask)`) and Step 2 (:115-131, `button[aria-label="Ask"]` + `#flexible-item-buttons`) document the demoted watch-page selectors as operative.
- Ruling: update the SKILLz body to the #817 header-primary model, but it MUST remain `prototype` until live-DOM validation exists (see Appendix A). `SKILLZ_STALE_VS_817` flagged.
- Note: `studio_ask_indexer.py` itself (the executable path) is ALREADY on the #817 header-primary selectors (ASK_STUDIO_SELECTORS :111-137; USE_WATCH_PAGE=False :164) with the watch-page path as fail-closed fallback (:537,661-672). The staleness is in the SKILLz doc body, not the runtime.

---

## 6. Shorts Scheduler Context Consumption Assessment (CRITICAL)

- Q7 (already consumes the artifact?): **YES.** `index_weave.load_index_json` reads `memory/video_index/{channel}/{video_id}.json` (env `VIDEO_INDEXER_ARTIFACT_PATH`, default `memory/video_index`; index_weave.py:114-132); called at scheduler.py:387,495,928,1150. There is NO `VideoIndexStore` class in the scheduler module (it reads raw JSON). **No duplicate storage should be recommended** (same path/store as the indexer).
- Q6 (how it SHOULD consume): read-only via the existing pure formatters - `load_index_json -> build_human_description_context (index_weave.py:50-88) -> build_topic_hashtags (:406-422) -> build_digital_twin_index_block (:425-481) -> generate_clickbait_title_from_index`. Today these read-only formatters are entangled with a write path.
- ANTI-PATTERN (the scheduler OWNS indexing): `index_weave.ensure_index_json` (index_weave.py:323-403) CREATES the artifact when missing (stub mode :348-358, or Gemini mode `GeminiVideoAnalyzer().analyze_video` :360-391); scheduler.py:375-383 deletes the existing index and re-indexes mode=`gemini`; scheduler.py:901-922 ensures/creates it. The consumer is also the indexer/writer.
- CRITICAL RETURN CONDITION (sentinel REFUTED the read-only assumption): **the scheduler MUTATES live YouTube metadata during indexing.** `_update_video_metadata` (scheduler.py:769) ensures/loads/weaves the index (:896-960) then writes `self.dom.edit_title` (:963) and `self.dom.edit_description` (:966) - real DOM writes (dom_automation.py:2652-2691). The dedicated "INDEXING-ONLY MODE" `run_indexing_cycle` (scheduler.py:1017), even when it SKIPS scheduling (:1142), still calls `_update_video_metadata` (:1135) and `self.dom.save_video` (:1144), committing a rewritten description to live YouTube. The schedule path additionally sets publish via `self.dom.schedule_video` (:488).
- Consequence: **any "bounded single-video indexing test" routed through the scheduler would silently overwrite production video metadata on studio.youtube.com.** This is `NEEDS_012`. Flags: `SCHEDULER_MUTATES_METADATA_DURING_INDEX`, `SCHEDULER_ALREADY_CONSUMES_INDEX`, `SCHEDULER_OWNS_STUDIO_ASK`.

---

## 7. Recommended Architecture

```
Studio Ask Indexing (provider, browser-authenticated)
  -> StudioAskIndexer.ask_about_video / run_video_indexing_cycle
  -> writes/updates memory/video_index/{channel}/{video_id}.json   (artifact = single source)
DAE Phase 2 (auto_moderator_dae.py:1563-1582)  OWNS the execution cycle (gated, chrome-only)
Heartbeat  OBSERVES status/stale/last-success; does NOT execute indexing
Shorts Scheduler  CONSUMES the artifact READ-ONLY for description/hashtags/title/Digital-Twin
                  -> must NOT own Studio Ask indexing; must NOT rewrite metadata as a side effect of indexing
Gemini API (GeminiVideoAnalyzer)  = explicit, separate optional cloud analyzer/enrichment provider
                  -> never a hidden fallback for a failed Studio Ask (Studio Ask fails CLOSED)
```

Rulings:
- DAE owns the execution cycle; heartbeat observes. (Confirmed already true.)
- Studio Ask is the PRIMARY browser-authenticated provider; Gemini API is a SEPARATE optional provider, not a hidden fallback. (Refined: a Studio-Ask cycle MAY run an additive Gemini enrichment pass when `GEMINI_API_KEY` is set - that is explicit/gated, still not a fallback.)
- The Shorts Scheduler consumes the artifact; it should not be the OWNER of indexing, and indexing must not be a vehicle for metadata mutation.
- The video-index artifact (`memory/video_index/{channel}/{video_id}.json`) is the single contract between indexing and scheduling.

### 7.1 Governed Browser Session (the autonomous surface)

0102 runs browser indexing WITHOUT handling credentials, by attaching to an already-authenticated browser session over its remote-debug port. This is implemented today:
- `studio_ask_indexer.py:904-905`: Chrome (9222) = Move2Japan, UnDaoDu (Set 1); Edge (9223) = FoundUps, antifaFM (Set 10). Per-channel port registry at `video_indexer.py:91-106`.
- The DAE attaches via `opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{chrome_port}")` (auto_moderator_dae.py:412) - it connects to an existing session; 012 owns/authenticates the profile, 0102 never receives passwords, cookies, or OAuth secrets.
- Menu 13 "Automation Dependencies" confirms/starts Chrome 9222 (`dependency_launcher/src/dae_dependencies.py::is_chrome_running`, NAVIGATION.py:246).
- Boundary rule (the repo guards against wrong-account/browser collisions): do NOT mix - Chrome 9222 only for Move2Japan/UnDaoDu, Edge 9223 only for FoundUps/antifaFM. The indexer enforces this via `group_channels_by_browser`.
- Operator safe bounded-run flow: main -> 13 Automation Dependencies (confirm Chrome 9222) -> 1 YouTube DAEs -> 8 YouTube Indexing -> 2 Continuous Indexing, videos per channel = 1, max cycles = 1. PRECONDITION: the local runtime must be on origin/main WITH #817 (a pre-#817 runtime uses stale selectors).

---

## 8. Smallest Safe Implementation Slice

Classification: `VIDEO_INDEXING_STUDIO_ASK_MENU_AND_SKILL_ENTRYPOINT_PHASE1` (do NOT implement in this read-only audit).
1. Relabel menu option 1 from `[GEMINI] Gemini AI Indexing` to `Studio Ask (browser) Indexing`; relabel option 4 to `[TEST] Gemini API single-video analyze` (explicit provider naming; no hidden cross-provider behaviour).
2. Add a BOUNDED single-video Studio Ask test entrypoint wired to `StudioAskIndexer.ask_about_video` (studio_ask_indexer.py:453) - which only navigates + scrapes + writes a local JSON artifact, never `edit_title`/`edit_description`/`save_video`/`schedule_video`. This is the SAFE single-video test seam (NOT the scheduler).
3. Update the `transcript_ask` SKILLz body to the #817 Ask Studio header model; keep `promotion_state: prototype` (graduation blocked pending Appendix A live-DOM proof).
4. Scheduler: read-only consumption only - keep `load_index_json`/`build_*` formatters; do NOT call `ensure_index_json` (no scheduler-owned indexing); treat a missing artifact as "skip enhancement", not "index now". (This touches the metadata-mutation coupling -> see section 9 NEEDS_012.)

Explicitly NOT in scope: Skillz registry promotion, WRE activity-router wiring, any publish/schedule/metadata mutation, live YouTube runs.

---

## 9. Return Conditions / Blockers

- `SCHEDULER_MUTATES_METADATA_DURING_INDEX` -> **NEEDS_012 (HIT).** The scheduler rewrites live YouTube title/description (and `save_video`) inside its index path, including the "INDEXING-ONLY MODE". A bounded indexing test MUST NOT route through the scheduler. Decoupling the scheduler's write-side from its index-read-side is a separate slice `SHORTS_SCHEDULER_INDEX_METADATA_DECOUPLING` requiring 012 sign-off (it changes when/whether live metadata is written).
- DAE Phase 2 is PRESENT (not absent) - no invention needed.
- Scheduler ALREADY consumes the `memory/video_index` artifact (same store) - do NOT add a duplicate storage layer.
- Adding the single-video Studio Ask test does NOT require live browser credentials in code - it attaches via the 9222/9223 debug port (no secrets). It does require an operator-provided authenticated session (governed browser surface).
- LIVE_DOM_VALIDATION_REQUIRED_BEFORE_SKILL_PROMOTION: `transcript_ask` must not graduate past prototype until the Appendix A operator probe passes against a live #817 Studio page.

---

## Appendix A - Operator-Assisted Live DOM Proof (LIVE_DOM_VALIDATION_REQUIRED_BEFORE_SKILL_PROMOTION)

The worker (0102) did NOT run this. It is an OPTIONAL manual proof for 012 to run on a SAFE unlisted/private video's YouTube Studio `/video/{id}/edit` page, in the browser console. It is a pure DOM selector probe: NO submit, NO metadata mutation.

```js
(async () => {
  const f = s => !!document.querySelector(s);
  const r = { url: location.href };
  r.header_button = f('ytcp-icon-button[aria-label="Ask Studio"]');
  const hb = document.querySelector('ytcp-icon-button[aria-label="Ask Studio"]')
          || document.querySelector('ytcp-icon-button[aria-label*="Ask"]');
  if (hb) hb.click();
  await new Promise(x => setTimeout(x, 2500));
  r.dialog        = f('ytcp-dialog#dialog');
  r.prompt_box    = f('div[contenteditable][aria-label="Ask something"]');
  r.prompt_box_alt= f('div.ytcpCreatorChatEntityAttachmentInlineFlowPromptBox[contenteditable="true"]');
  console.table(r);
  return r;
})();
```

Expected PASS evidence: `header_button === true`; `dialog === true`; at least one of `prompt_box` / `prompt_box_alt` true; URL is a Studio `/video/{id}/edit` page; no submit/send occurs.

Optional response-stream proof (only if 012 intentionally sends a harmless prompt such as "Summarize this video in one sentence."):

```js
const el = document.querySelector('#PAcreator_chat_streaming');
console.log('response_stream:', !!el, el && el.innerText.slice(0,120));
```

Expected PASS: `response_stream: true`; returned text is answer content; the selector reads from `#PAcreator_chat_streaming`, not the prompt box.

Constraints: this manual proof is NOT a substitute for automated tests; it IS required before promoting `transcript_ask` beyond prototype; it is NOT required for this read-only audit PR; it must NOT include private video data, full transcript text, cookies, tokens, account identifiers, or channel credentials.

---

## 10. WSP_97 Truth Boundary Checklist

Declared items: 22 - Rows: 22 - All YES

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | HOLOINDEX_DISCOVERY_RECORDED | YES | Section 2; 5 queries rated, scheduler-miss recorded as HOLOINDEX_LOW_SIGNAL |
| 2 | MENU_LABELS_MATCH_ACTUAL_PROVIDER | YES (FALSIFIED) | Section 3; opt1 Gemini-label=Studio Ask, opt4 Test=Gemini API; 2 mismatches (indexing_menu.py:25,28,69,235) |
| 3 | STUDIO_ASK_ENTRYPOINTS_IDENTIFIED | YES | options 1,2 (indexing_menu.py:69,79,141,167,179 -> studio_ask_indexer.py:876) |
| 4 | GEMINI_API_ENTRYPOINTS_IDENTIFIED | YES | options 4,5 (gemini_video_analyzer.py:297,365) + in-cycle gated pass (studio_ask_indexer.py:991) |
| 5 | SINGLE_VIDEO_STUDIO_ASK_GAP_CONFIRMED_OR_REFUTED | YES (CONFIRMED) | ask_about_video unwired (studio_ask_indexer.py:453; only caller :847) |
| 6 | DAE_PHASE2_REUSED_NOT_DUPLICATED | YES | auto_moderator_dae.py:1563-1582 exists; reuse, do not duplicate |
| 7 | HEARTBEAT_OBSERVES_NOT_EXECUTES | YES | _heartbeat_loop:2133-2582 has zero run_video_indexing_cycle refs |
| 8 | TRANSCRIPT_ASK_SKILLZ_STALENESS_CLASSIFIED | YES | Section 5; PROTOTYPE + STALE body (SKILLz.md:65-77,115-131) |
| 9 | SHORTS_SCHEDULER_CONTEXT_SEAM_IDENTIFIED | YES | index_weave.load_index_json (index_weave.py:124-132; scheduler.py:387,495,928,1150) |
| 10 | GEMINI_API_NOT_HIDDEN_FALLBACK | YES (REFINED) | explicit providers; Studio Ask fails closed (studio_ask_indexer.py:661-672); Gemini pass is gated additive (:991) |
| 11 | NO_LIVE_YOUTUBE_RUN | YES | read-only audit; no browser opened, no app run |
| 12 | NO_PUBLISH_SCHEDULE_METADATA_MUTATION | YES | nothing executed; scheduler-mutation is a documented finding, not performed |
| 13 | NO_CODE_CHANGE | YES | only this doc + root ModLog added |
| 14 | FILE_SCOPE_EXACTLY_TWO | YES | docs/audits/architecture/VIDEO_INDEXING_STUDIO_ASK_DAE_ENTRYPOINT_AUDIT_PHASE1.md + ModLog.md |
| 15 | ASCII_CLEAN | YES | byte-checked: zero bytes > 127 before commit |
| 16 | LIVE_DOM_OPERATOR_PROOF_DEFINED | YES | Appendix A; pure DOM probe, no submit |
| 17 | LIVE_DOM_NOT_RUN_BY_WORKER | YES | worker ran nothing live; probe is for 012 manually |
| 18 | SKILL_PROMOTION_BLOCKED_PENDING_LIVE_DOM_PROOF | YES | Section 5/9; transcript_ask stays prototype until Appendix A passes |
| 19 | NO_PRIVATE_VIDEO_DATA_REQUIRED | YES | Appendix A constraints forbid private/transcript/cookie/token/credential data |
| 20 | GOVERNED_BROWSER_SESSION_VIA_REMOTE_DEBUG_PORT | YES | Section 7.1; debuggerAddress 127.0.0.1:9222/9223 (auto_moderator_dae.py:412; studio_ask_indexer.py:904) |
| 21 | ZERO_CREDENTIAL_HANDLING_BY_0102 | YES | attach-to-existing-session; 0102 never receives passwords/cookies/OAuth secrets (Section 7.1) |
| 22 | BROWSER_PORT_CHANNEL_MAPPING_RESPECTED | YES | Chrome 9222=Move2Japan/UnDaoDu, Edge 9223=FoundUps/antifaFM; group_channels_by_browser (studio_ask_indexer.py:905-928) |

---

## Internal Review Verdict

READY (decision-only). The audit is accurate and complete: it maps the menu->provider reality (2 mislabels), confirms the single-video Studio-Ask gap, confirms the DAE Phase 2 seam is correct + the heartbeat observes-only, classifies the SKILLz staleness, and identifies the scheduler consumption seam. The adversarial sentinel REFUTED the naive "scheduler indexing is read-only" assumption and surfaced the load-bearing NEEDS_012: the Shorts Scheduler mutates live YouTube metadata during indexing (including its INDEXING-ONLY mode). The audit therefore routes the recommended bounded single-video test to the SAFE `ask_about_video` seam, not the scheduler, and isolates the scheduler metadata-coupling as a separate 012-gated decision. No code changed; nothing run live. Left OPEN for the external 0102 gate.

## ModLog (WSP 22)

- 2026-06-16: W9 read-only audit of YouTube video-indexing entrypoints (menu / DAE Phase 2 / heartbeat / Studio Ask indexer / transcript_ask SKILLz / Shorts Scheduler). 4 discovery lanes + adversarial sentinel. Findings: 2 menu label/provider mismatches (opt1 "Gemini"=Studio Ask, opt4 "Test"=Gemini API); no bounded single-video Studio-Ask test entrypoint (ask_about_video unwired); DAE Phase 2 seam EXISTS+correct (reuse, auto_moderator_dae.py:1563-1582); heartbeat observes-only; studio_ask_indexer on #817 header model but transcript_ask SKILLz body stale (stays prototype); scheduler already consumes memory/video_index via index_weave but OWNS indexing AND mutates live YouTube title/description during the index step incl. INDEXING-ONLY mode (NEEDS_012). Governed browser surface = Chrome 9222 (Move2Japan/UnDaoDu) / Edge 9223 (FoundUps/antifaFM) debug-port attach, zero credential handling. Appendix A defines the operator-assisted live-DOM proof gating transcript_ask promotion. Next slice: VIDEO_INDEXING_STUDIO_ASK_MENU_AND_SKILL_ENTRYPOINT_PHASE1 (+ separate SHORTS_SCHEDULER_INDEX_METADATA_DECOUPLING NEEDS_012). WSP_97 22/22. Decision-only; left OPEN for W10.
