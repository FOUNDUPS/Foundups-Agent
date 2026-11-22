# Member Area Interface

## 2026-11-22 — Floating controls and camera candidate

The shared floating player has a persistent external grip and side edges.
Drag within the available viewport; keyboard arrows move the focused grip.
Enter/click opens `+` → Video, which provides Play, Expand, Hide, Return and
Close alternatives. The app floating title/expand row and app Play strip are
removed. Provider controls remain exposed, and recovery remains available in
Video. App gestures never intercept the cross-origin iframe interior.

Outward pinch defaults to WikiTube; direct app Full Video is configurable.
Separate optional inward-pinch and video-swipe-up return choices are stored in
`pfmall_video_options_v1` without coupling the old frame/collapse fields. Until
chosen, return gestures retain their current behavior. Full Video entry requests
playback through the existing provider guard. Hidden/tucked YouTube pauses;
its full-height rail restores the same paused player. Selection reveal remains
an existing independent preference. No native-fullscreen pass is implied.

The dock camera opens canonical public AutoPost in the same tab after saving
Mall state. `cameraDestination()` includes only an allowlisted `return_to` URL,
matching AutoPost's own parser. Red Dog on this dock stays in-page and calls the
canonical conversation owner. Missing backend admission produces a closable
availability message, not a Mall redirect or search dictation. Existing account
avatar, product and legacy mode-sheet owners retain their separate behavior.
No new AI model, voice capture, backend deployment or permission is introduced.
See [the incident](../../modules/foundups/pfmall/MEDIA_PLAYBACK_INCIDENT_HPC.md).

## 2026-11-21 — v26 phone candidate (unreleased)

Build v25 remains the frozen comparison at its existing preview. Build v26 uses a
separate source receipt and preview channel; no production redirect or release is
part of this change. Phone-layout browser fixtures are separate from physical
Safari and installed-PWA evidence. The principal has opened v25 on an iPhone 11;
v26 physical playback, audio and uninterrupted three-clip transitions are NOT_RUN.

The shared pre-Fractal shell keeps one provider and one actionable bottom Search
Dock while entering/leaving WikiTube or app Full Video. A fully hidden parked
player pauses. Native YouTube controls and native fullscreen are not intercepted.
The leading + retains discovery controls, AutoPost and Video Options; the trailing
+ is Add FoundUp on Play and Add Video in the HPC pilot. Video preferences affect
app controls and qualified visible playback, never promise provider autoplay.

Play public browsing and static FoundUp details correspond to the currently
available public discovery surfaces. The requested future levels 1–2 public /
level 3+ member policy is not a deployed graph ACL. The separate Fractal runtime
`22374b161570b2cd0e265e1c2b8c1009fb599394` is not imported. Contributions remain
unavailable until an authoritative service verifies current identity, membership
and per-FoundUp editor permission (012 initially for HPC). A successful existing
invite check only restores a manual review; it does not publish or grant editor
permission. No six-month checkout is activated. Cross-origin HPC-to-Play
contribution return is not connected and fails closed.

The existing same-origin Play `/?signin=required` gate and `/sso-callback/` are
preserved. Valid legacy `enter` links resolve public metadata rather than being
silently intercepted as a Mall view. Auth/callback, deep links and existing invite
flows are excluded from public landing normalization. Apex-to-Play routing is a
pure tested plan only; no live apex redirect is installed.

The full HPC banner opens <https://hasan4speaker.com/>. The distinct Mall return
opens Play; Voice Your Opinion / Contact Congress retains
<https://vote.mtrout.com/contact>. Vote/Contact whole-banner return links to HPC
remain a different navigation contract.

Browse AI is a separate compatibility pilot: no model is preloaded, no automatic
cloud fallback, and no model capability is claimed. The explicit, checksum-bound
41-byte WASM addition fixture is not an AI model. Actual model selection/download
and WebGPU qualification remain later work, including same-runtime Safari/PWA
checks. This dependency does not block the phone UI candidate.


**Module**: `public/member/`
**Version**: 2.4.0

## Shared dock and player preferences — 2026-11-21

**PFDOCK-20261121 / SPECIFIED_NOT_IMPLEMENTED.** All FoundUp and fractal views
consume one shell-owned floating bottom Search Dock, including HPC and
`play.foundups.com`. Its `+` menu puts the AI list first and Video settings
second. The [shared navigation contract](../../modules/foundups/docs/PFMALL_MALL_NAVIGATION_CONTRACT.md#14-shared-search-dock-and-video-preferences)
owns the full behavior matrix: Floating is the confirmed video-tile tap
default; WikiTube/Fullscreen are selectable; expansion, pinch-in return and
video-swipe-up return have independent preferences. Rotate Floating to
landscape fullscreen and restore it on portrait subject to later deliberate
navigation. Rotation lock remains an open idea.

Reuse `mall-video-projection.js` for dock/menu composition,
`mall-tile-field.js` for selection, `mall-video-player.js` for transitions and
`mall-state-restore.js` for validated preferences. Native fullscreen may hide
the dock; preserve and restore its state. Keep tile tap, app-frame action,
provider controls, video gestures and grid/type gestures distinct. Shared
preferences are origin-local until an authenticated sync owner is qualified.
This defines no new public API or dispatcher authority. Earlier runtime
observations below must not override this newer acceptance contract.

## Proposed fractal view contract — 2026-11-19

The [navigation contract](../../modules/foundups/docs/PFMALL_MALL_NAVIGATION_CONTRACT.md#13-fractal-work-navigation)
owns the future component graph view. Reuse this shell's search, field, player
and permitted state owners. A component's stable identity can appear in
multiple lenses without duplicating the component. Containment and typed reuse,
dependency or work links follow the [master architecture](../../modules/foundups/docs/FOUNDUPS_MASTER_ARCHITECTURE.md#fractal-views-of-the-same-work).

The future return record retains caller, lens, selection and recoverable view
state. Keep graph snapshot revision separate from exact source revision and
overlay identity; unavailable pinned evidence must not silently open main.
Revalidate access for Back, direct entry, search and conversational context.
Private PC paths and receipts stay in architect scope. A builder association
requires explicit permitted work-to-component evidence; animations and aggregate
telemetry cannot supply it.

Tools → Benchmark and graph selection are planned navigation surfaces. This
specification adds no dispatcher command, endpoint, execution authority or
resident voice transport. Functionality and integration evidence remain
independent. The [documentation audit](../../docs/audits/architecture/PFMALL_FRACTAL_DOCUMENTATION_AUDIT_20261119.md)
records implementation boundaries; existing interfaces below retain their
current contracts.

## Public Interface

### Public video projection & open Mall landing

`play.foundups.com` mounts the open guest **Play FoundUps Mall** (`p.fMALL`)
discovery landing across all catalog FoundUps without Clerk or Firestore
account reads, while the dedicated `hpc.foundups.com` hostname mounts a fixed
single-FoundUp guest video field from `mall-public-video-catalog.json` (its
header brand link returns to `https://play.foundups.com/`). Entering any
FoundUp from `play.foundups.com` (`Enter FoundUp` on tiles, floating/WikiTube
player, quick-view cards, or direct `/member/foundup.html` / `/f/{id}/app`
routes) requires membership and passes through the `foundups.com` Member Portal
(`https://foundups.com/member/?enter={foundup_id}`). FoundUps `/members` and
`/members/` redirect to `/member/`. On `foundups.com`, `?foundup=hpc` and
`?enter={foundup_id}` enforce the existing Clerk sign-in, invitation, and
`@username` checks; the same-tab sign-in handoff (`pfmall_product_return_v1`)
retains the requested member destination for up to 15 minutes and consumes it
once after admission. Touch and narrow views use three portrait columns with six-item vertical
batches. Tap or Enter opens or switches the selected clip in the single
top-anchored floating player (`#videoPlayerFullscreen.video-player-floating`)
above the grid while keeping the selected tile visible (`aria-current="true"`)
and allowing the grid to scroll underneath (`--floating-player-clearance`).
Swiping the floating player right (or activating `Tuck player`) tucks it to
the right viewport edge while audio and queue state continue; tapping or
swiping left on `.video-player-tuck-handle` (`Restore player`) restores it.
The corner control, `Open WikiTube`, or pinch-out on a thumbnail or the
floating player chrome opens sequential WikiTube playback (`WikiTube video player`)
and immediately attempts playback while retaining the live provider iframe.
`Floating player` minimizes WikiTube back to the floating player; Close,
Escape, Back, or pinch-in on floating or WikiTube chrome closes the player
and restores grid anchor and focus. WikiTube advances sequentially on clip
end and bounds consecutive auto-skips (`MAX_CONSECUTIVE_AUTO_SKIPS = 5`) across
unavailable (`100`) or restricted (`101`, `150`) clips (`queueHalted = true`),
halting immediately with `Play video` when autoplay is blocked.

A viewport of at least 900 CSS px with a fine primary pointer and hover opens
the shared theater. It displays the main player, then scoped video search, then
the horizontal queue. Fresh entry requests the first clip muted, with manual
Play recovery when needed. The centered desktop search form is up to
584 CSS px wide and 52 px high. Typing filters the queue during playback.
Submitting with Enter or the search button starts the next matching clip,
or the first match when the current clip is outside the results or last.
An empty query or no matches leaves playback alone. Enter on a focused
thumbnail selects that video. Switching between layouts preserves the
active iframe, media time, selected ID and query.
The YouTube controls provide desktop fullscreen and sound controls.

The player uses YouTube's IFrame API, `playsinline`, origin-level Referer and
distinct ready/state/error/autoplay/timeout outcomes. The local
`mallVideoPlayback` event and `getPlaybackSnapshot()` expose only the provider
state, video ID, code and observable media time. No event is sent externally.
A thumbnail below 120 × 70 opens the player with a separate Play video
action. One provider iframe is active. A source link remains explicit.

`mallStateRestore.selectVideoScope(id)` selects tab-local storage. It restores
legacy offsets, the stable tile ID/offset, and optional theater and phone
queries. The active iframe keeps its media time during in-page resizing.
`setScopedPhoneQuery(query)` applies the existing metadata matcher to the
touch grid on submit and retains source tile indices. On resize, an active
desktop selection outside the phone filter is visible until the player closes.

HPC selects `/member/hpc.webmanifest` and its touch icon in the document head
when the public route resolves. A fresh standalone launch opens the scoped
collection. The header portrait links to the canonical Mall. On the phone
the header action opens Vote's manual contact resource. The bottom anchor
holds the options dialog, query field and dictation button, and the existing
public Red Dog briefing link. Device speech recognition starts by request
only when the browser reports an available local language. The keyboard
mic remains the alternative. The options dialog includes Home, disclosure
and device-model availability. Both off-page actions save scoped state.

The dedicated hostname sets presentation and `/f/{id}/app` preserves member
admission. See the [shared media incident](../../modules/foundups/pfmall/MEDIA_PLAYBACK_INCIDENT_HPC.md)
for verification boundaries and service-worker version evidence.

### Public FX directory — 2026-10-25

The homepage navigation links **FX** to `/f/`, whose existing index renderer
provides **FX — FoundUps Exchange** project/token discovery. Its only catalog
request remains `/f/public_catalog.json`; member runtime fields are excluded.

The existing input performs case-insensitive substring matching over canonical
ID, name, public summary and a nonempty string `token_symbol`. Both a bare ticker
and its `$`-prefixed form match. Null, missing, blank and non-string symbols do
not become ticker text or search terms. Readiness continues to filter
`poc_landing_status`, independently of the query. Empty/cleared queries, no-match
results, catalog errors and Return to Mall retain the existing owners.

Tickers are declarations, not deployment or trading evidence. This slice adds
no catalog records, router, claim verification, chain observation, price feed,
wallet, order placement or participation authority. `/f/{id}` landing routes and
protected app/deep-app handoff remain unchanged. Controlled VM tests exercise
the actual input/change handlers; deployment and browser layout require separate
verification.

### Entry URL
```text
/member/
```

### Ordinary Mall Auth Requirements
- Clerk session required
- invite validation required
- username claim required before admitted users enter the Mall
- redirects to `/?signin=required` if not authenticated

### Registered Public Product Selection

`/member/?foundup=move2japan` and `/member/index.html?foundup=move2japan` select
public houses in this same page. Exactly one case-sensitive supported `foundup`
value is required. Unknown or duplicate selections do not relax ordinary admission.
The legacy `/move2japan/` page is only a fixed redirect; `/f/move2japan` uses the
registry's exact public `poc_url`. `/f/move2japan/app` retains its existing gate.

`Move2JapanSearch.prepareShell(window)` runs before shared controllers bind:
it moves the one existing `#mallTileField` into the property layout and installs
the product form inside the existing `#accountPlane`. It creates no second shell,
account controller or tenant runtime. The actual page's product boot selects
`mallStateRestore.selectProduct('move2japan')` before mounting the public catalog.
Only an already-present Clerk user starts the read-only account initializer.

The shared `window.redDog` gains:

| API | Product contract |
| --- | --- |
| `registerDiscoveryAdapter({element, focusElement})` | Register the native product form in the existing plane |
| `setDiscoveryAdmission(boolean)` | Strict admission state; revocation clears shared identity and member content |
| `isDiscoveryAdmitted()` | Current product account admission, never payment entitlement |

`product-discovery` retains the full controller plus accessible modal handling.
The older reduced `public-discovery` mode remains available for existing callers;
Move2Japan's canonical page uses `product-discovery`. Shared density/motion controls
remain available to admitted accounts. Global video scope, category, query, layout
and channel actions cannot change geographic results; the native property form
owns its filters. Dispatcher `search_catalog` returns `incompatible_projection`
when the shared field refuses the query, without emitting a state-change event.

The property selection has precedence over responsive category rows, including
empty results. `getLayoutMode()` reports `grouped`; ordinary rows/grid behavior
is retained when leaving the product. Property detail identity is
`(foundup_id, listing_id)` and remains separate from video channel identity.

### Independent View State and Account Return

`mallStateRestore` exposes `selectProduct`, `save`, `restore`, `bindAutoSave`,
`rememberProductReturn` and `consumeProductReturn`.

| View | Storage key / schema |
| --- | --- |
| Ordinary video Mall | `pfmall_mall_state_v1`; scope, projection, layout, vertical and category-row offsets, plus optional `activeVideo: { foundupId, videoId, queueQuery }` (`localStorage`, ordinary `/member/` only; HPC's tab-local `pfmall_video_scope_hpc_v1` in `sessionStorage` is isolated and unaffected) |
| Move2Japan | `pfmall_product_move2japan_state_v1`; `pfmall_product_state.v1`, geographic rows and stable listing anchors |
| Account return | Session-only `pfmall_product_return_v1`; one use, 15 minutes, allowlisted filters and fixed member destination |

Product restoration never applies video scope or layout. Deferred video scroll
callbacks recheck the selected product. A loading product cannot overwrite its
previous geographic state with an empty capture. The return is consumed only by
the normal Mall initializer after Clerk/invite/username admission succeeds.
The shared service worker normalizes member query navigations to one
shell entry; public property JSON uses network-first validation and dated cached
fallback. Auth, account, dynamic and cross-origin requests are not cached.

### Runtime Surface

`/member/` on `foundups.com` is the Clerk/invite/username-admitted Member
Portal shell hosted from Firebase static assets, while `play.foundups.com`
opens `/member/` directly as the unauthenticated open p.fMALL discovery
landing for all FoundUps. Entering a FoundUp from `play.foundups.com` passes
through `https://foundups.com/member/?enter={foundup_id}`, redirecting
signed-out visitors to `https://foundups.com/?signin=required` (which opens the
eligibility/sign-in modal) and resuming FoundUp entry after admission.
Storage and service worker registrations are origin-local (`pfmall-member-v22`
/ `Build v22`). Top-left `.mall-brand-cluster` renders `/logo-foundups.svg` +
`.mall-brand-ln` (`FoundUPS on LinkedIn`), while Red Dog (`/logo-dog.png`) owns
the bottom-right concierge/search anchor. Mall FoundUp tiles support hover-hold
(`650ms`), touch press-and-hold (`450ms`), and `.mall-tile-flip-btn` / `i` / `f`
to turn over and reveal WSP 109 `Outcome · Solution · Pain` (`mallTileField.flipTile(foundupId, flipped)`),
and phone viewports (`mallTileField.isPhonePatchViewport()`) progressively
patch-load grid/expanded DOM batches (`PHONE_PATCH_BATCH = 9`) and viewport
poster images via `IntersectionObserver`.

The ordinary Mall dock searches the loaded catalog. Tap or swipe up on its
plus button for an anchored options panel and the public AutoPost link.
The panel displays the build of the loaded interface. The scoped video
header repeats it beside the topic. Update the build and shell cache
generation together. The runtime tests check their agreement.
Search and dictated text wrap into a bounded editable field above the
controls when they outgrow the compact pill. Enter or the search icon
submits. The mic or a hold on Red Dog dictates into the search field using
an installed local recognizer.
On unsupported devices the control focuses the input for keyboard dictation.
Release a hold or press the square Stop in Red Dog's position to finish
dictation. The result stays editable, and hiding the dock or backgrounding
the page cancels capture. Tap Red Dog at rest to open the existing concierge.

The older runtime placed the dock between video and queue. The accepted
target is video, scrolling queue/tiles, then one viewport-bottom floating dock
across shared views (see the contract above); deployed parity is unverified.
A query filters the current lane while
the active clip continues. Selecting a result or submitting an idle queue
starts a matching clip. The media area can scroll independently on short
screens. Escape first dismisses options or leaves the input, then returns
to the originating card. In the ordinary viewer, tapping Red Dog returns
to the card and opens the concierge. In HPC it opens the public briefing.
Device model selection and resident speech follow the shared roadmap.

It owns:
- invite-gated post-auth landing
- Video Mall tile field with gesture-driven navigation
- FoundUp entry page (deep-linkable via `foundup.html?id={id}`)
- Red Dog unified plane with AI tools, channels, and context briefing

It does not yet own:
- direct tenant execution
- `/f/{foundup_id}` transport routing
- wallet or agent operations

### Hosted Assets

```text
/member/index.html
/member/foundup.html
/member/css/member.css
/member/css/account-concierge.css
/member/css/mall-planes.css
/member/css/mall-tile-field.css
/member/js/gesture-engine.js
/member/js/mall-planes.js
/member/js/mall-tile-field.js
/member/js/gesture-hints.js
/member/js/account-concierge.js
/member/js/red-dog-concierge.js
/member/mall-video-catalog.json     <- Video Mall data source
/member/mall-catalog.json           <- Legacy FoundUp catalog
```

### JavaScript Surface

The page bootstraps these internal behaviors:
- `initClerkAuth()`
- `initializeMall(clerkUserId, userData, clerkUser)`
- `loadMallCatalog()`
- `loadInviteContext(clerkUserId, clerkUser)`

---

#### `window.redDog` (Unified Plane API)

**Source**: `js/account-concierge.js`

The primary public API for the unified Red Dog plane. All concierge interactions go through this API.

| Method | Description |
|--------|-------------|
| `open()` | Open the Red Dog plane |
| `close()` | Close the Red Dog plane |
| `toggle()` | Toggle plane open/close |
| `isOpen()` | Returns boolean |
| **AI Tools** | |
| `setCategory(id)` | Set projection category |
| `getCategory()` | Get current category |
| `setDensity(preset)` | Set density preset (3x4, 3x5, 4x6, 5x8) |
| `getDensity()` | Get current density |
| `setMotionMode(mode)` | Set motion mode (snap, glide) |
| `getMotionMode()` | Get current motion mode |
| **Channels** | |
| `populateMyMall()` | Project Personal Mall (012 lanes) |
| `openPersonalMall()` | Alias for populateMyMall |
| `openSearchMall()` | Show search input |
| `searchByCreator(query)` | Filter by creator name |
| `clearSearch()` | Clear search and reset field scope |
| **Context** | |
| `getContext()` | Get current context briefing |
| `refreshBriefing()` | Refresh context briefing |
| `getRecommendations()` | Get AI recommendations |
| `runRecommendation(action)` | Execute a recommendation |
| **Saved Videos** | |
| `openSaved()` | Open Saved Videos section in concierge plane |
| `refreshSaved()` | Re-render saved videos from localStorage |
| **Watch History** | |
| `openHistory()` | Open Recently Watched section in concierge plane |
| `refreshHistory()` | Re-render watch history from localStorage |
| `clearHistory()` | Clear watch history (delegates to `mallVideoPlayer.clearHistory()`) |
| **Identity** | |
| `setIdentity(clerkUser, userData)` | Set identity block |
| `setFoundUps(foundupDocs)` | Set FoundUps grid |
| `setInvites(inviteDocs)` | Set invites drawer |
| **Verification Alerts (PFM9)** | |
| `showVerificationAlert(alert)` | Store and display a VerificationGapGuard alert (in-memory only) |
| `dismissVerificationAlert(alertId)` | Dismiss an alert by ID |
| `getVerificationAlertCount()` | Get count of active alerts |
| `getVerificationAlerts()` | Get all active alerts (shallow copy) |

**Verification Alert Schema** (`RedDogVerificationAlert`):
```typescript
interface RedDogVerificationAlert {
  alert_id: string;              // Unique alert identifier
  event_id: string;              // VerificationGapEvent.event_id
  foundup_id: string;            // Which FoundUp this relates to
  summary: string;               // Human-readable summary
  action_required: "human_review" | "acknowledge" | "info_only";
  panel_to_open?: "verification_wall" | "task_detail" | "evidence";
  created_at: string;            // ISO 8601 timestamp
}
```

**Verification Alert Events**:
| Event | Payload |
|-------|---------|
| `reddog:verification_alert` | `RedDogVerificationAlert` — dispatched by AI agents to surface anomalies |
| `reddog:alert_stored` | `{ alert_id, count }` — emitted after alert stored |
| `reddog:alert_dismissed` | `{ alert_id, count }` — emitted after alert dismissed |

**WSP 97 Truth Boundary**: RedDog may notify, summarize, and open panels for human review. RedDog may NOT judge, deny rewards, publish accusations, or finalize protected decisions.

**Backward Compatibility**: `window.accountConcierge` is an alias for `window.redDog` (will be removed).

**Concierge Plane Surfaces**:
| Surface | Data Source | Re-entry Action |
|---------|-------------|-----------------|
| Saved Videos | `mallVideoPlayer.getSavedVideos()` (localStorage) | Reconstruct queue from catalog, open player |
| Recently Watched | `mallVideoPlayer.getHistory()` (localStorage) | Reconstruct queue from catalog, open player |

Both surfaces render cards with thumbnail, title, and meta. **Recently Watched** cards may show a **Continue at m:ss** badge when `playbackPosition` is valid (local HTML5 progress only). Click-to-reenter opens the player at the matching queue index and seeks to `playbackPosition` when present and valid (file sources only).

---

#### `window.mallTileField` (Video Mall API)

**Source**: `js/mall-tile-field.js`

Video Mall tile grid with field scope projections.

| Method | Description |
|--------|-------------|
| `initialize(config)` | Initialize tile field |
| `navigateToFoundUp(foundupId)` | Navigate to `/f/{foundup_id}` (WSP 104 canonical) |
| **Video Runtime** | |
| `startLanePreview(foundupIndex, videoIndex, muted)` | Start lane autoplay through FoundUp's video queue |
| `advanceToNextInLane()` | Advance to next video in queue (loops at end) |
| `togglePlay(index)` | Start lane autoplay on tile, or route zero-video `hpc` tile to `/member/?foundup=hpc` after saving Mall state |
| `getPlayingIndex()` | Get currently playing tile index |
| `getActiveVideo()` | Return `{ foundupId, videoId, queueQuery }` when inline/fullscreen playback is open (`null` otherwise) |
| `restoreActiveVideo(activeVideo)` | Restore saved inline playback (`autoplay: false`) with preserved `queueQuery` |
| `expandFoundUp(index)` | Expand tile to FoundUp view |
| `collapseFoundUp()` | Collapse back to Mall |
| `isExpanded()` | Returns boolean |
| `getExpandedIndex()` | Get expanded tile index |
| **Motion** | |
| `setMotionMode(mode)` | Set snap or glide |
| `getMotionMode()` | Get current motion mode |
| **Density** | |
| `setDensity(preset)` | Set density preset |
| `getDensity()` | Get current density |
| **Projection** | |
| `setProjection(type)` | Set projection sort |
| `getProjection()` | Get current projection |
| `resetProjection()` | Reset to default |
| **Field Scope** | |
| `setFieldScope(options)` | Set field scope `{ type, query }` |
| `projectPersonalMall()` | Filter to 012 lanes |
| `searchByCreator(query)` | Case-insensitive creator search |
| `filterByCategory(cat)` | Filter by category |
| `filterByTag(tag)` | Filter by tag |
| `filterBySourceGroup(group)` | Filter by source group (`'videos'` \| `'apps'`) |
| `clearFieldScope()` | Clear scope, show all |
| `getFieldScope()` | Get current scope object |

**Field Scope Types**:
| Type | Match Logic |
|------|-------------|
| `personal` | `creator === '012'` |
| `creator` | Substring match on creator/entity |
| `category` | Exact match (case-insensitive) |
| `tag` | Exact match in tags array |
| `source_group` | `'videos'` (`videos.length > 0` / `video_count > 0`) or `'apps'` (`github_repo`, `external_app`, `internal_app`, `internal_service`) |

---

#### `window.mallPlanes` (FoundUp View API)

**Source**: `js/mall-planes.js`

Manages in-page FoundUp view plane (slides up from bottom).

| Method | Description |
|--------|-------------|
| `setCatalog(catalog)` | Set catalog for view |
| `openFoundUp(index)` | Open FoundUp at index |
| `closeView()` | Close FoundUp view |
| `isOpen()` | Returns boolean |
| `getActiveIndex()` | Get current FoundUp index |

---

#### `window.gestureZone` (Gesture Engine)

**Source**: `js/gesture-engine.js`

| Method | Description |
|--------|-------------|
| `gestureZone(el, handlers)` | Attach gesture handlers to element |
| `dragScroll(track)` | Enable drag-to-scroll on element |

**Gesture Handlers**: `onSwipeLeft`, `onSwipeRight`, `onSwipeUp`, `onSwipeDown`, `onDoubleTap`

---

#### `window.mallVideoPlayer` (Fullscreen Player API)

**Source**: `js/mall-video-player.js`
**Contract**: `modules/foundups/docs/PFMALL_FULLSCREEN_PLAYER_CONTRACT.md`

Fullscreen video player with queue rail. Queue-constrained to single FoundUp.

| Method | Description |
|--------|-------------|
| `open(foundupId, queue, startIndex, resumeOpts?)` | Open player with FoundUp queue. Optional `resumeOpts`: `{ resumeSeconds: number }` (HTML5 file sources only; embeds ignore). YouTube embeds use IFrame API for autoplay-advance; other embeds use raw iframe (no ended detection). |
| `close()` | Exit fullscreen |
| `goToVideo(index)` | Navigate to video index |
| `next()` | Next video in queue |
| `prev()` | Previous video in queue |
| `isOpen()` | Returns boolean |
| `getFoundUpId()` | Current queue constraint |
| `getCurrentIndex()` | Current video index |
| `getCurrentVideoId()` | Current video ID string (`video_id`), or `''` when closed |
| `getQueueLength()` | Queue length |
| **Save (Phase 2)** | |
| `isCurrentSaved()` | Returns boolean — is current video saved |
| `getSavedVideos()` | Returns Object map of `{foundupId}::{videoId}` → saved entry |
| `getSavedCount()` | Returns number of saved videos |
| **History (Phase 2)** | |
| `getHistory()` | Returns Array of watch entries (newest first, max 50) |
| `clearHistory()` | Clear watch history |

**localStorage Keys** (Phase 2):
| Key | Structure |
|-----|-----------|
| `pfmall_saved_videos` | `{ "{foundupId}::{videoId}": { foundupId, videoId, title, thumbnail, savedAt } }` |
| `pfmall_watch_history` | `[{ foundupId, videoId, videoIndex, title, thumbnail, timestamp, playbackPosition? }, ...]` — `playbackPosition` is shell-local seconds for **direct file** (`<video>`) items only; omitted or cleared when below resume threshold or near end; **not** set for iframe embeds (cannot read time truthfully). |

**Gesture Semantics**:

The following table records the older runtime. The planned configurable
video-return bindings and Floating default are owned by the shared contract
above; do not treat this table as the next-iteration acceptance matrix.

| Gesture | Action |
|---------|--------|
| swipe-up | Next video |
| swipe-down | Exit fullscreen |
| pinch-in | Exit fullscreen |
| tap | Toggle chrome |
| swipe-left | Toggle save (Phase 2) |
| swipe-right | Dismiss hook |

**Events**:
| Event | Payload |
|-------|---------|
| `videoPlayerOpen` | `{ foundupId, videoIndex }` |
| `videoPlayerClose` | none |
| `videoPlayerNavigate` | `{ foundupId, videoIndex }` |
| `videoPlayerSave` | `{ foundupId, video, saved }` |
| `videoPlayerShare` | `{ foundupId, video }` |
| `videoPlayerDismiss` | `{ foundupId, video }` |
| `videoPlayerSave` | `{ foundupId, video }` |
| `videoPlayerShare` | `{ foundupId, video }` |

---

#### Legacy: `js/red-dog-concierge.js`

Self-contained IIFE for FAQ topics. Will be removed when OpenClaw lands.
- Detects page context (Mall vs FoundUp entry)
- Injects contextual help topics into `#redDogPanel` (Mall), `#conciergeSheet` (entry)
- No network calls, no backend, no fake AI

---

### Shell-Local vs Resident RedDog/OpenClaw Capabilities

| Hook | Shell-Local (Current) | Resident RedDog/OpenClaw (Future) |
|------|----------------------|-------------------|
| `searchByCreator()` | String match on catalog | AI semantic search |
| `projectPersonalMall()` | Filter by creator | Personalized ranking |
| `setProjection()` | Client-side sort | AI-ranked projections |
| `getRecommendations()` | Static recommendations | AI-generated suggestions |

> **Dev/Testing Shim**: The Search Mall text input is a temporary shell-local
> shim for testing field-scope APIs. Future AI search requires an authenticated
> RedDog adapter; the shell does not directly host the model or OpenClaw
> authority.

### Data Expectations

**Video Mall Catalog** (primary)
```json
/member/mall-video-catalog.json
```
Schema: `modules/foundups/docs/PFMALL_VIDEO_MALL_CATALOG_SCHEMA.md`

**Legacy FoundUp Catalog**
```json
/member/mall-catalog.json
```

**User document shape**
```typescript
interface UserDoc {
  email: string;
  username?: string;
  inviteValidated?: boolean;
  usedInviteCode?: string;
  inviteCodes: string[];
  waitlistJoined?: string;
  createdAt: string;
}
```

**Invite document shape**
```typescript
interface InviteDoc {
  code: string;
  status: "active" | "used";
  createdBy: string;
  createdAt: string;
  usedBy: string | null;
  usedAt: string | null;
}
```

### UI Contract

**Mall Context (tile field)**:
- category rows play the selected lane in the tile
- wide desktop video tiles play in context on click, Enter or Space. The
  separate fullscreen action opens the full viewer. Hover reveals the
  button. Back and Escape restore focus and scroll in the expanded lane.
- Enter FoundUp button: navigate to `/f/{foundup_id}` (WSP 104 canonical)
- pinch-out on tile: expand into FoundUp's video field
- swipe: navigate snapped field (default) or glide (override)
- desktop mouse drag: maps to touch swipe (drag-scroll parity)

**FoundUp View (expanded)**:
- pinch-in: collapse back to Mall
- desktop Ctrl+wheel down: collapse back to Mall
- Save in the shared player: toggle the browser-local bookmark
- "Full details" link: navigate to `/member/foundup.html?id={foundup_id}` (deep-linkable)

See the [desktop browse map](../../modules/foundups/docs/PFMALL_MALL_NAVIGATION_CONTRACT.md#46-desktop-poster-browsing)
for current mouse, keyboard, card and full-player behavior.

**Red Dog Plane**:
- swipe down from top or tap avatar: open Red Dog plane
- primary explicit control is the Red Dog icon

**Other**:
- first-time visitors see a gesture discovery hint overlay (dismissible, shown once)
- invite gate and username claim remain blocking surfaces ahead of the Mall

---

## pfMALL Agent Control Contract

**Source**: `js/pfmall-control-dispatcher.js`
**Scope**: Browser-side postMessage bridge for structured agent control of the pfMALL video wall. Phase 1 (PMCTRL1).

This contract defines the **only** sanctioned way for an external agent (0102, Hermes, future native phone agent, future RedDog AI) to drive the `/member/` runtime. The dispatcher is an **API contract**, not a UI driver: every command routes to an existing runtime API on `window.mallTileField` / `window.mallVideoPlayer`. When the underlying API is missing, the dispatcher returns `api_unavailable`; it never fabricates success, and it never uses direct DOM selectors as a fallback.

This browser control contract is not the future RedDog conversation transport.
It carries no resident identity, durable conversation, model credential, work
order, OpenClaw policy, or Hermes execution authority.

### Message Envelopes

All three envelope types carry `source` (identity of sender/dispatcher, e.g. `"0102"`, `"pfmall-dispatcher"`), `target` (routing hint), and `type` (discriminator). The dispatcher listens only for `pfmall_command` frames from an origin allowlist and only replies / emits within the same frame.

**`pfmall_command`** (agent → dispatcher):
```jsonc
{
  "type": "pfmall_command",
  "source": "0102",
  "target": "pfmall",
  "command": "set_layout",        // one of the seven commands below
  "request_id": "req-42",         // correlation id; echoed on response
  "payload": { /* command-specific */ }
}
```

**`pfmall_response`** (dispatcher → agent, always in reply to a command):
```jsonc
{
  "type": "pfmall_response",
  "source": "pfmall-dispatcher",
  "target": "0102",
  "request_id": "req-42",         // echoes request_id
  "status": "ok" | "denied" | "error",
  "result": { /* present on ok */ },
  "error":  { "code": "...", "message": "..." } // present on denied|error
}
```

**`pfmall_event`** (dispatcher → subscribers, unsolicited truth signal):
```jsonc
{
  "type": "pfmall_event",
  "source": "pfmall-dispatcher",
  "event": "layout_applied",       // one of the six event names below
  "payload": { /* event-specific */ },
  "timestamp": 1713600000000
}
```

### Response Statuses (WSP 97 truth taxonomy)

| Status | Meaning |
|--------|---------|
| `ok` | Command was routed, underlying API was invoked, and the outcome is reported truthfully in `result`. A `result.applied` flag may be `false` even on `ok` (e.g. reset_session when no session was active — truthful no-op). |
| `denied` | Command was **structurally valid** but **refused by policy** (e.g. device tier does not permit the requested layout). `error.code` carries the policy reason (e.g. `unsupported_density_for_device`). Never used for malformed input or missing APIs. |
| `error` | Command was malformed, unknown, missing required fields, the runtime API is absent (`api_unavailable`), the API threw, or a session-mode gate was violated (`session_mode_required`). |

The three statuses are disjoint; in particular a **policy denial is `denied`, not `error`**, and a **missing runtime API is `api_unavailable` (error), not fabricated success**.

### Commands (7)

| Command | Purpose | Routed To |
|---------|---------|-----------|
| `inspect_state` | Read-only snapshot of density, device tier, expanded index, playing index, session override flags | `mallTileField` getters |
| `set_layout` | Request density preset; subject to device policy (`DENSITY_TIERS`) | `mallTileField.requestDensity(preset, {source})` |
| `play_tile` | Start lane autoplay for a FoundUp via its canonical id | `mallVideoPlayer.open(foundupId, queue, startIndex)` |
| `expand_tile` | Expand a FoundUp tile to its video field | `mallTileField.expandFoundUp(index)` |
| `collapse_tile` | Collapse back to Mall | `mallTileField.collapseFoundUp()` |
| `load_videos` | Load an agent-provided video list into a **session override** (gated — see below) | `mallTileField.loadSessionVideos(videos, {source})` |
| `reset_session` | Clear any active session override | `mallTileField.resetSession({source})` |

No other commands exist in Phase 1. Phase 1 does not include: floating search, RedDog AI pipe, native-phone agent hooks, backend calls, canonical catalog mutation, or direct DOM selector fallbacks.

### Events (6)

Events are a truth channel independent from the response channel. They fire **only** when the corresponding real state change is observed or the corresponding real refusal occurred.

| Event | Fires When | Payload |
|-------|-----------|---------|
| `layout_applied` | `mallTileField.requestDensity` returned `applied:true` | `{ preset, deviceClass, source }` |
| `layout_denied` | `mallTileField.requestDensity` returned `applied:false` with a policy reason | `{ preset, reason, deviceClass, source }` |
| `video_loaded` | `load_videos` succeeded **and** API confirmed `session_mode:true` | `{ video_count, source }` |
| `video_failed` | `load_videos` failed, including when the API refused to enter session mode | `{ reason, source }` |
| `state_changed` | Dispatcher-local session override flipped (active ↔ inactive) | `{ change, video_count?, source }` |
| `session_reset` | Active session override was cleared (either by reset_session clearing a real active session, or by API acknowledgement) | `{ source, api_acknowledged }` |

A truthful no-op (e.g. `reset_session` when no override was active) emits **no** event.

### Device Policy (`set_layout`)

Density is gated by device class before the command reaches any visual change:

| Device Class | Allowed Presets |
|--------------|-----------------|
| `phone` | `3x4`, `3x5` |
| `tablet` | `3x4`, `3x5`, `4x6` |
| `desktop` | `3x4`, `3x5`, `4x6`, `5x8` |

If the preset is not in the tier's allow-list, the dispatcher returns `status:"denied"` with `error.code:"unsupported_density_for_device"` and emits `layout_denied`. This is a **policy denial**, not an error — the request was well-formed and simply not permitted for this device.

### Session Override Truth Rules

The dispatcher tracks a local `sessionState` ( `overrideActive`, `overrideAppliedAt`, `overrideVideoCount` ) distinct from the canonical mall catalog. Rules:

1. **No silent canonical mutation.** `load_videos` never mutates `mall-video-catalog.json` or the live tile catalog. It exclusively asks the runtime to enter a session-scoped override.
2. **API-confirmed session mode is required.** `load_videos` marks the override active **only** when `mallTileField.loadSessionVideos(...)` returns `{ applied: true, session_mode: true }`. If the API returns `applied:true` but `session_mode` is not explicitly `true`, the dispatcher returns `error` with `code:"session_mode_required"` and emits `video_failed` (reason `session_mode_required`). This is the hard gate against silent catalog mutation.
3. **`reset_session` clears the override** and emits `session_reset`; if no override was active, it returns `status:"ok"` with `result.changed:false` and emits nothing (truthful no-op).
4. **`reset_session` is idempotent** and works even when the runtime lacks `mallTileField.resetSession` — dispatcher state is dispatcher-owned; `result.api_called` / `result.api_acknowledged` expose whether the runtime also acknowledged.
5. **Missing session API ⇒ `api_unavailable`.** When `mallTileField.loadSessionVideos` is not present, `load_videos` returns `error` with `code:"api_unavailable"`; it does **not** fall back to DOM manipulation, catalog rewrite, or any speculative path.

### 0102 / Agent Boundary (Phase 1)

- The dispatcher is the **only** sanctioned agent→mall entry point. No other cross-origin pathway is authorized.
- **Not yet wired in Phase 1** (explicit non-scope):
  - No native-phone agent hook (no Android/iOS bridge, no WebView IPC).
  - No RedDog AI integration (the legacy `red-dog-concierge.js` FAQ IIFE is unaffected).
  - No floating search bar, no agent-driven search UI.
  - No backend calls. No writes to `mall-video-catalog.json`. No tenant execution.
- The dispatcher is an **API contract**, not a UI driver. It does not click buttons, toggle classes, or read DOM state. Every effect is routed through `window.mallTileField` / `window.mallVideoPlayer` APIs.

### WSP 97 Truth Constraints (summary)

| Rule | Enforcement |
|------|-------------|
| No playability claim without API confirmation | `play_tile` reports `applied`, not `playing`; `videoPlayerOpen` confirms the view opened. Provider `playing` plus advancing media time is required to establish playback. |
| Policy denial is `status:"denied"`, not `"error"` | `set_layout` against a tier-disallowed preset returns `denied` with `error.code:"unsupported_density_for_device"`. |
| Missing API is `api_unavailable`, not fabricated success | All seven commands return `error`/`api_unavailable` when their target API is absent; none synthesize DOM-based fallbacks. |
| No silent canonical catalog mutation | `load_videos` requires API-confirmed `session_mode:true`; otherwise `error`/`session_mode_required`. |
| Reserved events fire only on real state changes | Truthful no-ops (e.g. reset with no active session) emit no event. |

### Related Protocols

- WSP 11 (Interface Protocol) — this section is the agent-control interface of record.
- WSP 91 (Observability) — `pfmall_event` frames are the observable truth signal.
- WSP 97 (Canonical Execution Loop) — status/event truth taxonomy.
- WSP 22 (ModLog) — changes to this contract are logged in `public/member/ModLog.md`.

---

*Last Updated: 2026-04-20*


## Responsive browse and local query API — 2026-10-18

- `mallTileField.setLayoutMode('rows'|'grid') -> boolean` chooses an explicit
  layout. On first entry the ordinary field defaults to grid at 1024 CSS px
  or wider with a fine primary pointer and hover, and to rows elsewhere.
  Stored layout takes precedence. Density requests can also select grid.
- `getLayoutMode()`, `getRowOffsets()`, `restoreRowOffsets(offsets)` expose
  presentation state; row keys are category strings, offsets nonnegative finite numbers.
- `searchCatalog(query)` and `redDog.searchCatalog(query)` apply the same
  `{type:'query', query}` field scope. Input is bounded to 300 characters.
  AND-match search terms against lane/video metadata; `video(s)` requires a video
  queue; small house/car/clothing aliases are explicit, not AI inference.
  Leading `I'm/I am looking for`, `show me`, `find` and `browse` requests accept
  bounded greeting/Red Dog/please prefixes. Clothes, clothing and apparel share
  an alias set. Red and dog are retained as item words outside that request prefix.
  Negation, price/budget and size terms are preserved as literal metadata terms;
  no exclusion, numeric comparison or garment-size interpretation is performed.
  Grouped product discovery still refuses this global operation and retains its
  domain filter owner.
- `pfmallControlDispatcher.dispatch('search_catalog', {query})` exposes that same
  local presentation operation, returns `scope: local_catalog` plus observed state,
  and emits `state_changed`. Existing origin checks are unchanged. It is not a
  resident conversation transport or a grant of backend/worker authority.
- State inspection includes `tile_field.layout_mode` where the field API exists.
- Row movement preserves catalog-wide `data-index`; grouping never renumbers queues.
- Scope/projection changes stop inline media and clear expanded index state before
  filtering/reordering. Pinch gestures and canonical `/f/{foundup_id}` entry remain.

Rows continue through the loaded catalog. Server pagination, virtualization,
provider-confirmed live discovery, follow/payment persistence, consented preference
mapping and authenticated speech/conversation are future slices, not implied by
this presentation interface.

Catalog queries discover matching channels. Opening a matching channel retains its full video queue; the query does not filter individual videos within that queue.
