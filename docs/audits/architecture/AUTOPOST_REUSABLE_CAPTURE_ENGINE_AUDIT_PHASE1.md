# AUTOPOST_REUSABLE_CAPTURE_ENGINE_AUDIT_PHASE1

**Slice**: AUTOPOST_REUSABLE_CAPTURE_ENGINE_AUDIT_PHASE1
**Worker-Lane**: G (parallel to the Mall discovery audit on Lane A)
**Type**: READ-ONLY discovery audit. DECISION-ONLY. No code/runtime change in any repo.
**Base SHA**: 486eb69d7 (origin/main at dispatch; rebased onto current origin/main, which now carries the merged Mall discovery audit)
**Cross-repo**: AutoPost code read at O:/repos/AutoPost (separate repo, read-only, never modified). Audit doc + ModLog written only in o:/Foundups-Agent.
**Discipline**: WSP_00 zen state. WSP_97 Truth Boundary. Evidence-backed; no private chain-of-thought.

---

## 1. Mission + Scope

Determine whether AutoPost's CAPTURE engine can become a REUSABLE, FoundUp-agnostic component -- the creation/input half (camera capture, content recognition, automatic listing creation, data-entry automation) that complements the PlayFoundups Mall's discovery/display half. Goal: a shared "capture -> auto-listing" template usable by GotJunk (reuse listings), GetK (vehicle listings), Move2Japan (property listings), and other FoundUps.

Output is a MAP plus smallest-build-steps, not features. The Mall (discovery half) is treated as the downstream consumer of this engine's listings; the Mall discovery audit (docs/audits/architecture/PLAYFOUNDUPS_MALL_PUBLIC_DISCOVERY_AUDIT_PHASE1.md) is now merged to origin/main and is cross-linked here as the discovery counterpart, but its findings are not a dependency of this capture-half map.

**In scope**: AutoPost capture/recognition/listing/post code; reconciliation with prior merged AutoPost audits; the reusable-template architecture; the Mall handoff metadata contract; a WRE automation roadmap; ordered smallest implementation steps.
**Out of scope (hard)**: any implementation; any modification of the AutoPost repo; any real posting/egress; authoring the adapter or executing code.

---

## 2. Predecessors / Current Context (Phase 0 Discovery + Reconcile)

### 2.1 HoloIndex discovery ratings

| Lane | HoloIndex rating | Note |
|------|------------------|------|
| CAPTURE | DIRECT_READ_REQUIRED | HoloIndex indexes o:/Foundups-Agent, not the AutoPost repo; all CAPTURE evidence is direct read of O:/repos/AutoPost. |
| RECOGNITION | DIRECT_READ_REQUIRED | Same -- AutoPost is outside the HoloIndex corpus. |
| LISTING | DIRECT_READ_REQUIRED | Same; targeted greps confirmed absence of sqlite imports, publish() call sites, listing vocabulary. |
| REUSABILITY | MEDIUM | Found the right monorepo modules (pfmall_catalog.py, gotjunk, move2japan, trade) but semantic ranking did not distinguish "catalog of apps" from "catalog of items"; "GetK vehicle listing" surfaced trade/adapters.py (crypto-token trading) = FALSE_LEAD. Direct reads required to classify. |
| RECONCILE | MEDIUM | Surfaced both merged AutoPost audits + Kosei boundary docs; noisy WSP/patent hits. No index reference to a generic "capture->listing engine" -- that is new ground. |

### 2.2 Reconciliation with existing merged audits (BUILD ON; do NOT re-derive)

| Prior merged audit | What it already established about AutoPost (EXISTS -- do not re-derive) |
|--------------------|--------------------------------------------------------------------------|
| docs/audits/architecture/AUTOPOST_EXTERNAL_FOUNDUP_COMPLETION_AUDIT_PHASE1.md | External CANDIDATE_FOUNDUP at PoC, "Overall PoC Completion: 35%" (:293); platform connectors all MOCK stubs (:127-134); TOKEN_DEFERRED; no external foundup_registry.json. |
| docs/audits/autopost_external_foundup/AUTOPOST_EXTERNAL_OPERATIONAL_READINESS_AUDIT.md | AutoPost is a Google AI Studio Cloud Run SPA, not self-hosted (:228); autopost.foundups.com DNS-configured but dead (:248); catalog external_url realigned to the AI Studio URL (:435); 6/7 readiness gates pass, poster asset missing. |
| docs/audits/kosei_ai_systems/AUTOPOST_VS_KOSEI_BOUNDARY_REPORT.md | AutoPost is the camera-to-post TOOL/engine; Kosei is the FoundUp/business that decides what gets posted where (:96-97). AutoPost stays external; zero Kosei refs in AutoPost and vice versa. Closest prior framing to "engine", but it does NOT spec a reusable capture->listing capability for other FoundUps. |
| docs/audits/architecture/FOUNDUP_PUBLIC_SURFACE_STATUS_AUDIT_PHASE1.md | AutoPost classified EXTERNAL PUBLIC (AI Studio URL), outside the monorepo manifest system (:100-114). |
| docs/audits/architecture/FOUNDUPS_PORTFOLIO_DATA_PROJECTION_SPEC_PHASE1.md | AutoPost not in the portfolio projection (only gotjunk_001, kosei, holoindex) (:81-84). |
| docs/audits/architecture/FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1.md | AutoPost registry row: portfolio_status=not_portfolio, poc_landing_status=placeholder, portfolio_ready=false (:104). |

**These facts are fenced as EXISTS and are NOT re-derived below.** The NEW GROUND this audit adds: (a) whether the capture->listing pipeline is a generalizable, extractable engine; (b) the capture-half -> Mall metadata contract; (c) a trace proving the end-to-end path is a mock chain.

### 2.3 Contradictions found vs prior audits (decision-only observations -- NOT edits to prior files)

| # | Prior claim | Actual (verified by source read) | Cite |
|---|-------------|----------------------------------|------|
| C1 | "Gemini AI Integration FUNCTIONAL -- Transcription + caption generation" | Provider is fully mocked. No @google/genai import in src; transcribe() returns one of 3 hardcoded strings via Math.random after setTimeout(2000); generateCaption() is rule-based string templating. | Completion audit:114 vs geminiProvider.ts:9-35; grep @google/genai in src = none |
| C2 | "Storage: better-sqlite3 (client-side)" | Post storage is ephemeral React useState (lost on reload). better-sqlite3 is a Node-native module, unusable in a browser SPA, and is imported nowhere in src. | Op-readiness:291 vs postRepository.ts:4-5; grep better-sqlite3/sqlite in src = none |
| C3 | Connectors listed as wired "Stub only" in the pipeline | Connectors are ORPHANED dead code: orchestrator imports no connector and terminates at status 'scheduled'; publish() is never called from anywhere. | Completion audit:127 vs postOrchestrator.ts:1-3,41; grep youtubeConnector/.publish( in src = only own defs |

---

## 3. Current AutoPost Architecture Map (capture -> recognition -> listing -> post)

```
[live camera: navigator.mediaDevices.getUserMedia]            captureController.ts:58
        |
        v
CaptureController (multi-segment recorder)                    captureController.ts:17,180,206-233
  - per-segment MediaRecorder -> video/webm Blob, concatenated
  - front/back flip incl. mid-recording                       captureController.ts:134-160
        |
        v
mediaGuard.validateVideo (size + MIME, video-only)            mediaGuard.ts:5-26  [PARTIAL]
        |
        v
postOrchestrator.processNewRecording                          postOrchestrator.ts:6-48
  - ai.transcribe(videoBlob)        [MOCK: random strings]    geminiProvider.ts:5-17
  - ai.generateCaption({transcript})[MOCK: rule templates]    geminiProvider.ts:19-35
  - PostRecord { caption, hashtags, status:'preview-ready' }  types/index.ts:71-86
  - mock scheduler (setTimeout) -> status:'scheduled'         postOrchestrator.ts:38-41  [TERMINATES HERE]
        |
        X  (no edge)
        |
  connectors youtube/instagram/tiktok: ORPHANED dead code     *Connector.ts:13-16
    - publish() are console.log mocks, never imported/called
  persistence: postRepository = in-memory useState            postRepository.ts:4-5
    - better-sqlite3 declared in package.json:17, never imported
  listing/catalog ingest: DOES NOT EXIST in AutoPost
```

The working slice is: record -> mock transcribe -> mock caption -> mock schedule. Everything downstream of caption generation (publish, persistence, any listing/catalog ingest) is stub, dead code, or absent.

---

## 4. Existing Components (EXISTS / PARTIAL, file:line + prior-audit coverage)

| Component | Status | Evidence (O:/repos/AutoPost) | Prior audit coverage |
|-----------|--------|------------------------------|----------------------|
| Camera viewport (live preview) | EXISTS | CameraViewport.tsx:20-24 (srcObject=stream; play().catch); captureController.ts:58 getUserMedia | Completion audit:112 "Camera Module FUNCTIONAL" |
| Multi-segment recording | EXISTS | captureController.ts:17,206-214,232-233 (per-segment webm Blob, concat) | Completion audit:112 |
| Camera flip (incl. mid-record) | EXISTS | captureController.ts:134-160; findBestDevice :82-105; AppShell.tsx:88 | Completion audit:112 |
| Gesture classification engine | EXISTS | inputInterpreter.ts:12-37 getGesture(); gestureController.ts:14,48 useGestures | Completion audit:113 "Gesture Handling FUNCTIONAL" |
| Orchestration stage-shell | PARTIAL | postOrchestrator.ts:6-48 (validate -> AI -> finalize -> schedule); every AI stage + scheduler mocked | not isolated previously |
| AIProvider interface shape | PARTIAL | providers/ai/types.ts:9-15 (transcribe + generateCaption {caption,hashtags}) | implied by "Gemini" row (overstated, see C1) |
| Gesture-DRIVEN capture trigger | PARTIAL | gesture engine drives nav+flip (AppShell.tsx:159-179); recording is a separate press-hold (RecordButton.tsx:31-34) bypassing the gesture engine; 200ms (gestureController.ts:24-29) vs 500ms (gestureConfig.ts:2) inconsistency | not previously traced |
| Media validation / guard | PARTIAL | mediaGuard.ts:10-26 validateVideo (size+MIME, video-only); validateDuration (:28-32) never called | Completion audit:118 "Security BASIC" |
| Post data model (PostRecord) | PARTIAL | types/index.ts:71-86 complete SOCIAL-POST model; for a listing it is effectively MISSING (no listing fields) | Completion audit:116 "Type System COMPLETE" |
| Auto field generation | PARTIAL | postOrchestrator.ts:22-29 generates caption+hashtags only; no listing-field derivation | -- |

---

## 5. Missing Components for Reuse (MISSING, file:line)

| Component | Status | Evidence |
|-----------|--------|----------|
| Real content/object recognition | MISSING | geminiProvider.ts:5-35 mocked; grep @google/genai|GoogleGenAI|vision|classify in src = none; GEMINI_API_KEY plumbed (vite.config.ts:11) but read nowhere |
| Structured listing fields (title/category/price/condition/attributes/location) | MISSING | grep over src for those terms hits only UI copy (PlatformPickerSheet.tsx:50, translations.ts:30); no commerce fields in types/index.ts |
| Recognition output schema (listing-relevant) | MISSING | providers/ai/types.ts:9-13 returns {caption, hashtags}; no object identity/attributes/condition/price/category; no confidence/accuracy field |
| Image / still-photo intake | MISSING | finalBlob hardcoded video/webm (captureController.ts:233); mediaGuard ALLOWED_TYPES video-only (mediaGuard.ts:6); no ImageCapture/canvas path |
| File / upload / gallery / drag-drop intake | MISSING | grep input type=file/FileReader/.files/drop/upload across src = none; only live MediaRecorder Blob enters |
| Data-entry automation | MISSING | no code path populates structured fields; orchestrator sets only caption/hashtags/transcript/status |
| Persistence | MISSING | postRepository.ts:4-5 in-memory useState; better-sqlite3 (package.json:17) never imported (see C2) |
| Platform/listing dispatch | MISSING | connectors orphaned (see C3); publish() never called; no listing/catalog ingest stage exists |
| FoundUp-agnostic headless core | MISSING | capture is browser-only (MediaRecorder/navigator.mediaDevices); domain stores are React useState; orchestration invoked from AppShell.tsx:226; Platform union bakes 8 social networks into the type system (types/index.ts:31-39) |

### 5.1 Consumer reality (where a real engine would plug in)

| Consumer | Status | Evidence |
|----------|--------|----------|
| GotJunk reuse listings | EXISTS (the real reference) | modules/foundups/gotjunk/frontend/types.ts:121-187 CapturedItem { blob; url; ipfsCid?; latitude?/longitude?; status; classification?; price?; discountPercent?; bidDurationHours? } + 16-type/4-pillar taxonomy (:47-51). Recognition unbuilt: gotjunk geminiService.ts = 0 bytes; originalPrice marked "Google Vision API (future)" (:137). |
| Move2Japan property listings | MISSING | move2japan/src/m2j_stakeholder_db.py:29-46 stakeholder CRM only; grep Property/Listing/Vehicle in move2japan = none. Aspirational. |
| GetK vehicle listings | MISSING (module absent) | find modules -iname *getk* = none; the HoloIndex hit trade/adapters.py is crypto-token trading (FALSE_LEAD). Conceptual only. |
| pfMALL per-item Listing schema | MISSING | moltbot_bridge/src/pfmall_catalog.py:84-104 CatalogEntry describes FoundUp APPS (foundup_id/name/tagline/category/tier/lifecycle_stage), not per-item listings. No generic per-item Listing schema at the Mall level. |

**Net**: a reusable capture->listing engine has exactly ONE concrete validating consumer today (GotJunk); the other two are aspirational. AutoPost itself has capture (real) but no recognition and no listing output, so it cannot be "extracted" as a capture->listing engine -- that engine would be built, with GotJunk's CapturedItem as the seed schema.

---

## 6. Recommended Reusable Capture-Engine Template Architecture (decision-only spec)

A FoundUp-agnostic headless core with four pluggable seams + a per-FoundUp config. None of these are authored here; this is the target shape.

```
CaptureEngine (headless, framework-free TS core)
  1. CaptureSource adapter        : produces MediaItem { type: video|image|file, blob, meta }
       - video adapter            = generalize AutoPost CaptureController (decouple from React/DOM)
       - image adapter            = NEW (still capture / ImageCapture / canvas grab)
       - file/upload adapter      = NEW (gallery pick / drag-drop)
  2. RecognitionProvider interface: MediaItem[] -> StructuredFields { objectType, attributes{}, conditionHint?, priceHint?, category? , confidence }
       - per-FoundUp model + extraction schema (config-selected, not import-hardcoded)
       - NOTE: neither AutoPost nor GotJunk has a real impl; define the interface both satisfy
  3. ListingModel (generic)       : seed = GotJunk CapturedItem; media refs + geo + classification + commerce fields + status lifecycle + per-FoundUp attribute set
  4. ListTarget / Publish adapter : marketplace/Mall ingest (replaces AutoPost orphaned social connectors)
       - real publish is a gated side-effect (see Section 8), BLOCKED in Phase 1

PerFoundUpConfig { captureModes[], taxonomy/classificationSet, attributeSchema, recognitionModel, listTarget }
  - GotJunk  : reuse-item taxonomy (4 pillars), bid/discount commerce fields, IPFS media
  - GetK     : vehicle attribute schema (make/model/year/mileage/VIN), price
  - Move2Japan: property attribute schema (region/rent/rooms/availability)
```

**Reuse boundary**: the cleanest extractable AutoPost unit is the video CaptureController (a plain TS class depending only on logger), but it is browser-only and video-only; it becomes the `video` CaptureSource adapter, not the whole engine. The recognition layer, generic ListingModel, per-FoundUp config, and gated ListTarget are net-new.

---

## 7. Integration Strategy with the Mall Listing Model (capture half -> discovery half)

The capture engine emits a ListingRecord; the Mall (discovery half, docs/audits/architecture/PLAYFOUNDUPS_MALL_PUBLIC_DISCOVERY_AUDIT_PHASE1.md, merged on origin/main) consumes it. Because today's pfMALL "catalog" is app-level (CatalogEntry, pfmall_catalog.py:84-104), a per-item listing contract is NEW GROUND -- this audit proposes it as a spec only.

**Shared metadata contract (capture-half output == Mall listing input):**

```
ListingRecord {
  listing_id      : string            // engine-assigned
  foundup_id      : string            // routing; aligns with CatalogEntry.foundup_id
  source          : string            // "autopost" | "gotjunk" | ...
  media           : [{ url|ipfsCid, type: image|video, thumbnailUrl? }]
  title           : string            // recognition/data-entry derived
  category        : string            // per-FoundUp taxonomy term
  attributes      : { ...perFoundUpSchema }   // vehicle/property/reuse-specific
  price           : { amount: number, currency: string } | null
  condition       : string | null     // per-FoundUp condition enum
  location        : { lat?, lng?, region? } | null
  status          : "active" | "sold" | "expired" | "draft"
  created_at      : number
}
```

Handoff rule: the capture half MUST produce this record; the Mall half MUST treat it as listing input and is responsible only for discovery/display. The contract is the seam between the two halves and is the single shared artifact that links this capture-half audit to the merged Mall audit (docs/audits/architecture/PLAYFOUNDUPS_MALL_PUBLIC_DISCOVERY_AUDIT_PHASE1.md). GotJunk CapturedItem (types.ts:121-187) is the closest existing shape and should seed the generic fields; CatalogEntry remains the app-directory layer above individual listings.

---

## 8. WRE Automation Roadmap (WRE-driven capture -> auto-listing, dry-run-respecting)

```
operator capture -> CaptureEngine.CaptureSource
   -> WRE job: RecognitionProvider (Qwen/Gemma or vision model) -> StructuredFields   [D1/D2 read/simulate]
   -> WRE job: build ListingRecord draft (data-entry automation)                       [D2 simulate]
   -> 0102 / human review gate (confidence threshold)                                  [decision gate]
   -> WRE job: publish ListingRecord to Mall ingest (ListTarget)                       [D5 external side-effect: BLOCKED Phase 1]
```

All execution routes through the WRE / Hermes gated executor. Recognition and draft generation are read/simulate class (D1/D2) and may run dry. The publish/ingest leg is an external side-effect (D5) and is BLOCKED pending the destructive-action gate and any external-posting audit -- consistent with hermes_job_executor real-delegation being blocked by default. No step in this roadmap is implemented or enabled by this audit; it is dry-run-respecting by construction.

---

## 9. Smallest Implementation Steps (ordered candidate build slices -- the bridge to building)

Each is small, spec/decision-first, and defers real execution/egress behind WRE/Hermes gates. Ordered so the earliest steps unblock the rest.

1. **Define the ListingRecord contract** (Section 7) as a shared spec doc -- the capture-half -> Mall metadata contract. (doc-only)
2. **Define the RecognitionProvider interface** (MediaItem[] -> StructuredFields) that both AutoPost and GotJunk could satisfy. (interface spec, no impl)
3. **Promote GotJunk CapturedItem as the seed generic ListingModel**; generalize ItemClassification into a per-FoundUp taxonomy config. (spec)
4. **Define the PerFoundUpConfig schema** (capture modes, taxonomy, attribute schema, recognition model, list target). (spec)
5. **Spec the headless CaptureSource adapter seam** extracting AutoPost CaptureController as the `video` adapter; identify the React/DOM decoupling boundary. (spec; no extraction performed)
6. **Wire ONE real recognition impl behind the interface, dry-run** -- GotJunk first (it already has the item model), recognition output validated against the contract, no publish. (gated, dry-run)
7. **Spec the Mall ingest adapter** (ListingRecord -> a new pfMALL per-item catalog layer beneath CatalogEntry). (spec)

Smallest first real-build candidate: steps 1-2 (contracts), then step 6 (one dry-run recognition impl on GotJunk) as the minimum that proves the engine without any external posting.

---

## 10. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | HOLOINDEX_DISCOVERY_RECORDED | YES | Section 2.1 records per-lane ratings (DIRECT_READ_REQUIRED x3, MEDIUM x2) + the GetK FALSE_LEAD. |
| 2 | RECONCILED_WITH_EXISTING_AUTOPOST_AUDIT | YES | Section 2.2 summarizes 6 prior merged audits and fences their facts as EXISTS; Section 2.3 records 3 verified contradictions. |
| 3 | CROSS_REPO_READ_ONLY | YES | AutoPost read at O:/repos/AutoPost; zero writes there. Only files written are in o:/Foundups-Agent (this doc + ModLog). |
| 4 | BASE_SHA_PINNED | YES | Base 486eb69d7 (origin/main at dispatch); branch off that base in an isolated worktree. |
| 5 | EXISTS_VS_MISSING_CLASSIFIED_FILE_LINE | YES | Sections 4-5 classify every component EXISTS/PARTIAL/MISSING with file:line. |
| 6 | REUSABLE_TEMPLATE_DEFINED | YES | Section 6 defines the FoundUp-agnostic engine + 4 seams + per-FoundUp config. |
| 7 | MALL_INTEGRATION_CONTRACT_DEFINED | YES | Section 7 defines the ListingRecord capture-half -> Mall metadata contract. |
| 8 | SMALLEST_STEPS_ORDERED | YES | Section 9 lists 7 ordered, spec-first candidate slices. |
| 9 | NO_IMPLEMENTATION | YES | Decision-only; no code authored; smallest steps are spec/dry-run, publish leg blocked. |
| 10 | NO_AUTOPOST_REPO_CHANGE | YES | AutoPost repo opened read-only; no edits/commits in O:/repos/AutoPost. |
| 11 | ASCII_CLEAN | YES | Byte-checked 0 non-ASCII at write time. |
| 12 | FILE_SCOPE_EXACTLY_TWO | YES | Exactly two files changed in Foundups-Agent: this doc + ModLog.md. |

**Declared == Actual: 12/12 YES.**

---

## 11. Internal Review (author + adversarial Sentinel)

Five parallel discovery lanes (CAPTURE, RECOGNITION, LISTING, REUSABILITY, RECONCILE) plus one adversarial SENTINEL (separation of duties). The Sentinel re-read cited files and UPHELD all load-bearing claims: no EXISTS was a misclassified stub, no MISSING was already-covered, no reuse claim overstated decoupling, no smallest step smuggled real execution/egress. Two cited line ranges were re-pinned at write time (AppShell gesture :159-179; handleStop :197-227).

**Internal Review Verdict: MERGE_READY.**

Merge boundary: author + internal Sentinel STOP at MERGE_READY. An independent external 0102 gate merges.

---

## Cross-References

| Document | Location |
|----------|----------|
| AutoPost completion audit (reconciled) | docs/audits/architecture/AUTOPOST_EXTERNAL_FOUNDUP_COMPLETION_AUDIT_PHASE1.md |
| AutoPost operational readiness (reconciled) | docs/audits/autopost_external_foundup/AUTOPOST_EXTERNAL_OPERATIONAL_READINESS_AUDIT.md |
| AutoPost vs Kosei boundary (reconciled) | docs/audits/kosei_ai_systems/AUTOPOST_VS_KOSEI_BOUNDARY_REPORT.md |
| GotJunk capture->list reference | modules/foundups/gotjunk/frontend/types.ts |
| pfMALL app catalog (CatalogEntry) | modules/communication/moltbot_bridge/src/pfmall_catalog.py |
| Mall discovery half (merged on origin/main, cross-linked) | docs/audits/architecture/PLAYFOUNDUPS_MALL_PUBLIC_DISCOVERY_AUDIT_PHASE1.md |

---

*Decision-only discovery audit. No implementation performed. AutoPost repo read-only. Synthesized from 5 discovery lanes + 1 adversarial Sentinel under WSP_97 Truth Boundary discipline.*
