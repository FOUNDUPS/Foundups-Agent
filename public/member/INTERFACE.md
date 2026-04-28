# Member Area Interface

**Module**: `public/member/`
**Version**: 2.1.0

## Public Interface

### Entry URL
```text
/member/
```

### Auth Requirements
- Clerk session required
- invite validation required
- username claim required before admitted users enter the Mall
- redirects to `/?signin=required` if not authenticated

### Runtime Surface

`/member/` is now the admitted-user p.fMALL shell hosted from Firebase static assets.

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
| `togglePlay(index)` | Start lane autoplay on tile (entry point for tap gesture) |
| `getPlayingIndex()` | Get currently playing tile index |
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
| `clearFieldScope()` | Clear scope, show all |
| `getFieldScope()` | Get current scope object |

**Field Scope Types**:
| Type | Match Logic |
|------|-------------|
| `personal` | `creator === '012'` |
| `creator` | Substring match on creator/entity |
| `category` | Exact match (case-insensitive) |
| `tag` | Exact match in tags array |

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

### Shell-Local vs OpenClaw Capabilities

| Hook | Shell-Local (Current) | OpenClaw (Future) |
|------|----------------------|-------------------|
| `searchByCreator()` | String match on catalog | AI semantic search |
| `projectPersonalMall()` | Filter by creator | Personalized ranking |
| `setProjection()` | Client-side sort | AI-ranked projections |
| `getRecommendations()` | Static recommendations | AI-generated suggestions |

> **Dev/Testing Shim**: The Search Mall text input is a temporary shell-local shim for testing field scope APIs. It will be replaced by OpenClaw-powered search UI.

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
- tap tile: start lane autoplay through FoundUp's video queue (Shorts-style)
- Enter FoundUp button: navigate to `/f/{foundup_id}` (WSP 104 canonical)
- pinch-out on tile: expand into FoundUp's video field
- swipe: navigate snapped field (default) or glide (override)
- desktop mouse drag: maps to touch swipe (drag-scroll parity)

**FoundUp View (expanded)**:
- pinch-in: collapse back to Mall
- swipe up: close FoundUp view
- swipe left/right: navigate between FoundUps
- double-tap: toggle shell-local save (localStorage)
- "Full details" link: navigate to `/member/foundup.html?id={foundup_id}` (deep-linkable)

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
| No playability claim without API confirmation | `play_tile` reports `applied`, not `playing`; only the `videoPlayerOpen` event (emitted by `mallVideoPlayer`) is proof playback began. |
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
