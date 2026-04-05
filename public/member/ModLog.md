# Member Area Module Change Log

## [2026-04-05] Saved/History Surface Doc Sync (Worker F, WSP_97)

**Who**: 0102 (Claude Opus 4.6) — Worker F
**Type**: Documentation
**Slice**: `pfMALL_SAVED_HISTORY_SURFACE_DOC_SYNC_PHASE1`
**Spec**: WSP_97

**Files Modified**:
- `public/member/INTERFACE.md` — Added Saved Videos and Watch History methods to `window.redDog` API table
- `modules/foundups/docs/PFMALL_FULLSCREEN_PLAYER_CONTRACT.md` — Added concierge browse surfaces note to Phase 2

**Documented**:
- `openSaved()`, `refreshSaved()` — Saved Videos concierge surface
- `openHistory()`, `refreshHistory()`, `clearHistory()` — Watch History concierge surface
- Concierge Plane Surfaces table (data source + re-entry action)

**No runtime changes** — docs-only slice.

---

## [2026-04-05] Watch History Surface Phase 1 (Worker C, WSP_97)

**Who**: 0102 (Claude Opus 4.6) — Worker C
**Type**: Feature (Watch History UI)
**Slice**: `pfMALL_WATCH_HISTORY_SURFACE_PHASE1`
**Spec**: WSP_97

**Files Modified**:
- `public/member/js/account-concierge.js` — Watch History section + re-entry + clear
- `public/member/css/account-concierge.css` — History card/list/clear styling
- `public/member/tests/test_account_concierge.py` — 28 new tests (21 surface + 7 CSS)

**Surface Added**:
- Recently Watched section in Red Dog plane (after Saved Videos)
- History count badge (purple theme to distinguish from saved's orange)
- Video cards with thumbnail, title, foundupId, watched date
- Clear History button wired to `mallVideoPlayer.clearHistory()`
- Empty state: "No watch history yet. Videos you play will appear here."

**Re-entry Behavior**:
- Primary: reconstruct queue from storedCatalog → find video by videoId → player.open()
- Fallback: navigate to `/member/foundup.html?id={foundupId}`

**Public API Added**:
- `window.redDog.openHistory()` — inject + scroll to history section
- `window.redDog.refreshHistory()` — re-render history cards
- `window.redDog.clearHistory()` — clear all watch history

**Mode Sheet**: Added `History` entry to MODE_ACTIONS

**Test Count**: 987 → 1015 (+28 new, 0 regressions)

---

## [2026-04-03] Saved Videos Surface Phase 1 (Worker C, WSP_97)

**Who**: 0102 (Claude Opus 4.6) — Worker C
**Type**: Feature (Saved Videos UI)
**Slice**: `pfMALL_SAVED_VIDEOS_SURFACE_PHASE1`
**Spec**: WSP_97

**Files Modified**:
- `public/member/js/account-concierge.js` — Saved Videos section + re-entry logic
- `public/member/css/account-concierge.css` — Saved card/list styling
- `public/member/tests/test_account_concierge.py` — 23 new tests

**Surface Added**:
- Saved Videos section in Red Dog plane (after Channels)
- Saved count badge
- Video cards with thumbnail, title, foundupId, savedAt
- Empty state: "No saved videos yet. Swipe left or use Save in the player to save a video."

**Re-entry Behavior**:
1. If catalog has the FoundUp with videos → open fullscreen player at saved video index
2. Fallback → navigate to `/member/foundup.html?id={foundupId}`

**Public API**:
| Method | Description |
|--------|-------------|
| `redDog.openSaved()` | Open plane scrolled to Saved Videos |
| `redDog.refreshSaved()` | Re-render saved list |

**Command Emitted**: `reenter_saved_video` `{ foundupId, videoId }`

**Tests**: 987 passed (23 new Saved Videos tests)

---

## [2026-04-03] Shell Bridge Interceptor Phase 1 (Worker F)

**Who**: 0102 (Claude Opus 4.5) — Worker F
**Type**: Feature (External FoundUp Integration)
**Slice**: `PFMALL_SHELL_BRIDGE_INTERCEPTOR_PHASE1`
**Protocol**: WSP 15, WSP 97

**Purpose**: Shell-side postMessage listener for external FoundUp iframes. Intercepts `agent_request` events and dispatches to backend, then posts `agent_response` back to origin iframe.

**Contract**: `holo_index/docs/EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md`

**Files Created**:
- `public/member/js/shell-bridge-interceptor.js` — Main interceptor module

**Files Modified**:
- `public/member/index.html` — Added script include (line 1038)
- `public/member/foundup.html` — Added script include (line 786)

**Message Structure** (per bridge contract):
```
Inbound:  { type: "agent_request", route: "openclaw_search", payload: { action: "..." } }
Outbound: { type: "agent_response", status: "success|error", data: {...} }
```

**Supported Routes**:
| Route | Actions |
|-------|---------|
| `openclaw_search` | `semantic_search`, `wsp_lookup` |

**Features**:
- Origin validation (allowlist + same-origin)
- Stub responses for Phase 1 (backend not wired)
- `window.shellBridgeInterceptor` API for runtime config
- Debug mode via `?debug=1`

**Phase 2 Integration Points**:
- `window.shellBridgeBackend.search()` — Real semantic search
- `window.shellBridgeBackend.wspLookup()` — Real WSP lookup
- `CONFIG.backendUrl` — Backend API endpoint

**Tests**: 37 tests in `test_shell_bridge_interceptor.py`

| Test Class | Count | Coverage |
|------------|-------|----------|
| TestInterceptorExists | 4 | File structure, IIFE, init |
| TestMessageTypeHandling | 3 | Type validation |
| TestRouteHandling | 4 | Route dispatch |
| TestActionHandlers | 6 | semantic_search, wsp_lookup |
| TestResponseFormat | 5 | Contract Section 3.1 |
| TestOriginValidation | 4 | Security |
| TestStubMode | 4 | Phase 1 stubs |
| TestPublicAPI | 4 | window.shellBridgeInterceptor |
| TestHTMLIntegration | 3 | HTML includes |

---

## [2026-04-03] Fullscreen Player Save Share History Phase 2 (Worker F)

**Who**: 0102 (Claude Opus 4.5) — Worker F
**Type**: Feature (Shell-Local Persistence)
**Slice**: `pfMALL_FULLSCREEN_PLAYER_SAVE_SHARE_HISTORY_PHASE2`
**Protocol**: WSP 97

**Files Modified**:
- `public/member/js/mall-video-player.js` — Save, share, history implementation
- `public/member/css/mall-video-player.css` — Saved button state styling
- `modules/foundups/pfmall/tests/test_mall_video_player.py` — 27 new tests

**localStorage Keys**:
| Key | Purpose |
|-----|---------|
| `pfmall_saved_videos` | Map of `{foundupId}::{videoId}` → saved entry |
| `pfmall_watch_history` | Array of watch entries (max 50, newest first) |

**Save Behavior**:
- Toggle save per video within FoundUp queue
- Button state reflects saved vs unsaved (`.saved` class)
- Swipe-left gesture also toggles save
- Event emission preserved: `videoPlayerSave`

**Share Behavior**:
- `navigator.share` when available (mobile native share)
- Clipboard fallback (`navigator.clipboard.writeText` or `execCommand`)
- URL priority: `embed_url` > `source_url`
- Event emission preserved: `videoPlayerShare`

**Watch History**:
- Records on open and navigate
- Entry: `{ foundupId, videoId, videoIndex, title, thumbnail, timestamp }`
- Deduplicates by foundupId + videoId
- Max 50 entries (oldest trimmed)

**New API Methods**:
```javascript
mallVideoPlayer.isCurrentSaved()   // boolean
mallVideoPlayer.getSavedVideos()   // Map
mallVideoPlayer.getSavedCount()    // number
mallVideoPlayer.getHistory()       // Array
mallVideoPlayer.clearHistory()     // void
```

**Tests**: 69 player tests passed, 927 member tests passed

---

## [2026-04-03] Concierge Video Schema Sync Phase 1 (Worker C)

**Who**: 0102 (Claude Opus 4.5) — Worker C
**Type**: Fix (Schema Drift)
**Slice**: `CONCIERGE_VIDEO_SCHEMA_SYNC_PHASE1`
**Protocol**: WSP 97

**Files Modified**:
- `public/member/js/account-concierge.js` — FoundUps grid renders video catalog fields
- `public/member/css/account-concierge.css` — Category-based icon colors, video status classes

**Stale Fields Removed**:

| Old Field | New Field | Fallback |
|-----------|-----------|----------|
| `item.theme` | `item.category` | `'default'` |
| `item.token_symbol` | `item.creator_display` or `item.creator` | Sliced to 4 chars |
| `item.name` | `item.title` or `item.entity` | `item.name` (legacy) |
| `item.launch_readiness` | `item.status` | `item.launch_readiness` (legacy) |

**CSS Changes**:

| Old Class | New Class |
|-----------|-----------|
| `.theme-antifafm` | `.cat-media` |
| `.theme-gotjunk` | `.cat-startup` |
| `.theme-magadoom` | `.cat-games` |
| — | `.cat-travel`, `.cat-music`, `.cat-ai-education`, `.cat-ai-research`, `.cat-thought-leadership`, `.cat-default` |
| `.status-ready` | `.status-active` (+ legacy compat kept) |
| — | `.status-placeholder`, `.status-archived`, `.status-pending` |

**Backward Compatible**: Legacy `item.name` and `item.launch_readiness` remain as fallbacks.

**Tests**: 916 passed (full member suite)

---

## [2026-04-03] Search Mall Filter UI Phase 2 (Worker C)

**Who**: 0102 (Claude Opus 4.5) — Worker C
**Type**: Feature (Filter UI)
**Slice**: `SEARCH_MALL_FILTER_UI_PHASE2`
**Protocol**: WSP 97

**Files Modified**:
- `public/member/js/account-concierge.js` — Category pills + tag dropdown
- `public/member/css/account-concierge.css` — Filter row styling
- `public/member/tests/test_account_concierge.py` — 14 new filter tests
- `public/member/tests/test_search_mall_concierge_wiring_phase1.py` — Fixed block sizes

**UI Added**:
```html
<!-- Category filter pills -->
<div class="reddog-filter-row" data-reddog-category-filters>
  <span class="reddog-filter-label">Category:</span>
  <button class="reddog-filter-pill" data-reddog-category="travel">travel</button>
  <!-- ... music, media, startup, ai-education, ai-research, thought-leadership -->
</div>

<!-- Tag filter dropdown -->
<div class="reddog-filter-row">
  <span class="reddog-filter-label">Tag:</span>
  <select class="reddog-tag-select" data-reddog-tag-select>
    <option value="">All tags</option>
    <option value="012-lane">012-lane</option>
    <!-- ... ffcpln, consciousness, meditation, founders, ai, music, resistance, japan, expat -->
  </select>
</div>
```

**Wiring**:
| Filter | API | Command |
|--------|-----|---------|
| Category pill click | `mallTileField.filterByCategory(cat)` | `filter_category` |
| Tag select change | `mallTileField.filterByTag(tag)` | `filter_tag` |
| Clear (×) | `mallTileField.clearFieldScope()` | — |

**Mutual Exclusivity**:
- Selecting category clears tag and search input
- Selecting tag clears category and search input
- Typing in search clears category and tag

**CSS Added**:
- `.reddog-filter-row` — flex row with wrap
- `.reddog-filter-pill` — small rounded pill button
- `.reddog-filter-pill.active` — orange highlight
- `.reddog-tag-select` — styled dropdown

**Tests**: 916 passed (14 new filter tests)

---

## [2026-04-03] Member Doc Residual Sync Phase 2 (Worker C)

**Who**: 0102 (Claude Opus 4.5) — Worker C
**Type**: Documentation Fix
**Slice**: `MEMBER_DOC_RESIDUAL_SYNC_PHASE2`
**Protocol**: WSP 97

**Files Modified**:
- `public/member/README.md` — Fixed catalog references, added Video Mall as primary
- `public/member/INTERFACE.md` — Fixed UI Contract gestures, updated catalog sources

**Drift Fixed**:

| Issue | Fix |
|-------|-----|
| `mall-catalog.json` as primary | → `mall-video-catalog.json` is primary |
| "tap-to-enter" | → "double-tap tile: enter FoundUp view" |
| "quick view" | → "FoundUp view" |
| "card taps open" | → Updated to current gesture grammar |

**Catalog Truth**:
- `mall-video-catalog.json` — Video Mall data source (primary)
- `mall-catalog.json` — Legacy FoundUp catalog (non-video)

**UI Contract Updated**:
- Mall Context: tap=play/pause, double-tap=enter, pinch=expand/collapse
- FoundUp View: pinch-in=collapse, swipe up=close, double-tap=save
- Red Dog Plane: swipe down or tap avatar

**Tests**: 902 passed (no runtime changes)

---

## [2026-04-03] Member Surface Doc Sync Phase 1 (Worker C)

**Who**: 0102 (Claude Opus 4.5) — Worker C
**Type**: Documentation
**Slice**: `PFMALL_MEMBER_SURFACE_DOC_SYNC_PHASE1`
**Protocol**: WSP 97

**Files Modified**:
- `public/member/README.md` — Updated runtime shape, UX section, shell-local vs OpenClaw table
- `public/member/INTERFACE.md` — Full `window.redDog` and `window.mallTileField` API documentation
- `public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md` — Updated implementation status, success criteria

**Truth Locked**:
1. **Unified plane**: `account-concierge.js` is the unified Red Dog plane
2. **Public API**: `window.redDog` is the active API (`window.accountConcierge` is compat alias)
3. **Search Mall shim**: Text input is dev/testing shim, not final UI
4. **Shell-local vs OpenClaw**: Clear separation table in both README and INTERFACE

**API Documentation Added** (INTERFACE.md):
- `window.redDog` — 20+ methods
- `window.mallTileField` — 18+ methods
- `window.mallPlanes` — 5 methods
- `window.gestureZone` — 2 methods

**Version Bump**: INTERFACE.md 2.0.0 → 2.1.0

**Tests**: 902 passed (no changes to runtime)

---

## [2026-04-02] Search Mall Concierge Wiring Phase 1 (Worker B)

**Who**: 0102 (Claude Opus 4.5) — Worker B
**Type**: Feature (UI Wiring)
**Slice**: `search_mall_concierge_wiring_phase1`
**Protocol**: WSP 97

**Files Modified**:
- `public/member/js/account-concierge.js` — Search input UI, wiring to field scope APIs
- `public/member/css/account-concierge.css` — Search input styling
- `public/member/tests/test_account_concierge.py` — 13 new Search Mall wiring tests

**UI Added**:
```html
<!-- Search input (hidden by default, shown on Search Mall click) -->
<div class="reddog-search-container" data-reddog-search-container>
  <input type="text" class="reddog-search-input" data-reddog-search-input placeholder="Search by creator...">
  <button class="reddog-search-clear" data-reddog-search-clear>&times;</button>
</div>
```

**Functions Added**:
- `toggleSearchInput(show)` — Show/hide search input
- `clearSearch()` — Clear input and reset field scope

**Wiring**:
| Button/Input | Wires To |
|--------------|----------|
| Search Mall button | `toggleSearchInput(true)` → shows input |
| Search input (typing) | `mallTileField.searchByCreator(query)` |
| Clear button | `clearSearch()` → `mallTileField.clearFieldScope()` |
| Escape key | `clearSearch()` |
| `redDog.openSearchMall()` | `toggleSearchInput(true)` |

**CSS Added**:
- `.reddog-search-container` — flex container with rounded border
- `.reddog-search-input` — 44px min-height, transparent background
- `.reddog-search-clear` — 44px circular button

**Gaps Closed**:
- G-01: Search Mall button now wired to searchByCreator() ✓
- G-02: Creator search pill now wired ✓

**Tests**: 857 passed (13 new Search Mall wiring tests)

---

## [2026-04-02] Search Mall Projection Phase 1 (Worker B)

**Who**: 0102 (Claude Opus 4.5) — Worker B
**Type**: Feature (Field Scope Search)
**Slice**: `search_mall_projection_phase1`
**Protocol**: WSP 97

**Files Modified**:
- `public/member/js/mall-tile-field.js` — Extended field scope with search/filter APIs
- `public/member/tests/test_video_mall_field_runtime.py` — 12 new Search Mall tests

**New Hooks**:
```javascript
// Generic scope setter (replaces direct string scope)
window.mallTileField.setFieldScope({ type: 'creator', query: 'Move2Japan' });
window.mallTileField.setFieldScope({ type: 'category', query: 'travel' });
window.mallTileField.setFieldScope({ type: 'tag', query: '012-lane' });

// Convenience wrappers
window.mallTileField.searchByCreator('012');     // case-insensitive substring
window.mallTileField.filterByCategory('music');  // exact match
window.mallTileField.filterByTag('ffcpln');      // exact tag match
```

**Scope Types**:
| Type | Match Logic | Fields Searched |
|------|-------------|-----------------|
| `personal` | exact `creator === '012'` | creator |
| `creator` | case-insensitive substring | creator, entity |
| `category` | exact match (case-insensitive) | category |
| `tag` | exact match in tags array | tags[] |

**Sort Order** (all scopes):
1. `video_count > 0` first
2. `display_order` ascending
3. Zero-video lanes at end

**Grammar Preserved**:
- tap = play/pause
- double-tap = enter FoundUp
- pinch expand/collapse
- density/motion unchanged
- projection sorts work within scope

**No Backend**:
- String match only, no API calls
- Filters against `fullCatalog` in memory

**Tests**: 843 passed (12 new Search Mall tests)

---

## [2026-04-02] Personal Mall Projection Phase 1 (Worker B)

**Who**: 0102 (Claude Opus 4.5) — Worker B
**Type**: Feature (Field Scope)
**Slice**: `personal_mall_projection_phase1`
**Protocol**: WSP 97

**Files Modified**:
- `public/member/js/mall-tile-field.js` — Added field scope system
- `public/member/tests/test_video_mall_field_runtime.py` — 10 new Personal Mall tests

**New Hooks**:
```javascript
// Project Personal Mall (012 lanes only)
window.mallTileField.projectPersonalMall();

// Clear scope (show all lanes)
window.mallTileField.clearFieldScope();

// Get current scope ('personal' or null)
window.mallTileField.getFieldScope();
```

**Scope Logic**:
- Filter: `creator === '012'`
- Sort order within scope:
  1. `video_count > 0` first
  2. Then `display_order` ascending
  3. Zero-video lanes at end

**State Variables Added**:
- `currentFieldScope` — null (all) or 'personal' (012 lanes)
- `fullCatalog` — Unscoped catalog reference for reset

**Grammar Preserved**:
- tap = play/pause
- double-tap = enter FoundUp
- pinch expand/collapse
- density/motion unchanged
- projection sorts still work within scope

**Not Touched**:
- Red Dog controls
- Concierge
- Search
- Backend AI

**Tests**: 765 passed (10 new Personal Mall tests)

---

## [2026-04-02] Video Mall Feel Polish Phase 2 (Worker B)

**Who**: 0102 (Claude Opus 4.5) — Worker B
**Type**: Polish (Phone Feel)
**Slice**: `video_mall_feel_polish_phase2`
**Protocol**: WSP 97

**Files Modified**:
- `public/member/css/mall-tile-field.css` — Feel polish (tap pulse, snap smoothness, density-adaptive styling)
- `public/member/js/mall-tile-field.js` — Tap pulse feedback, transition effects
- `public/member/tests/test_video_mall_field_runtime.py` — 9 new feel polish tests

**What Was Tuned**:

1. **Tap feel** — Added immediate tap-pulse animation (180ms) for visual confirmation before play state resolves

2. **Snap feel** — Added `scroll-behavior: smooth` to wrapper for phone-native scroll deceleration

3. **Expand/collapse feel** — Added fade transition (120ms) with `.transitioning` class for smooth content swap

4. **Density-adaptive styling**:
   - Border-radius scales with density: 1.25rem (2x3) → 0.6rem (5x8)
   - Gap scales with density: 0.65rem (2x3) → 0.3rem (5x8)
   - Minimum tile size: 3rem x 3rem for tap targets

5. **Play indicator** — Tightened from 150ms to 80ms for snappier response

6. **Collapse hint** — Uses CSS class with transform+opacity transition (150ms)

**Hooks Preserved**:
- `expandFoundUp(index)` — unchanged signature
- `collapseFoundUp()` — unchanged signature
- `setDensity(density)` — unchanged signature
- `setMotionMode(mode)` — unchanged signature
- `togglePlay(index)` — unchanged signature
- `enterFoundUp(index)` — unchanged signature

**Grammar Preserved**:
- tap = play/pause
- double-tap = enter FoundUp
- pinch-out = expand FoundUp into video field
- pinch-in = collapse back
- snap/glide motion modes

**Tests**: 755 passed (9 new feel polish tests)

**Manual Feel Checklist**:
- [ ] Tap pulse visible on tile tap
- [ ] No lag between tap and play indicator
- [ ] Snap settling feels deliberate, not jittery
- [ ] Expand fade is smooth, not jarring
- [ ] Collapse hint slides up with content
- [ ] 5x8 density tiles still tappable
- [ ] Border radius looks proportional at all densities

---

## [2026-04-02] Video Mall Field Runtime Phase 1 (Worker B)

**Who**: 0102 (Claude Opus 4.5) — Worker B
**Type**: Feature (Video Runtime)
**Slice**: `video_mall_runtime_foundation_phase1`
**Protocol**: WSP 97

**Files Modified**:
- `public/member/js/mall-tile-field.js` — Video runtime (tap=play/pause, pinch expand/collapse)
- `public/member/js/gesture-engine.js` — Pinch detection (two-finger + ctrl+wheel)
- `public/member/css/mall-tile-field.css` — Video runtime styles (snap, density, play indicator)
- `public/member/index.html` — Escape handler uses isExpanded/collapseFoundUp
- `public/member/tests/test_mall_tile_field.py` — Updated for video runtime API
- `public/member/tests/test_mobile_blockers.py` — Updated for video runtime API

**Files Created**:
- `public/member/tests/test_video_mall_field_runtime.py` — 38 video runtime tests

**Video Runtime Features**:

Motion modes:
```javascript
window.mallTileField.setMotionMode('snap'); // Default - discrete paging
window.mallTileField.setMotionMode('glide'); // Fluid scroll override
```

Density presets (AI-controlled):
```javascript
window.mallTileField.setDensity('2x3'); // Default
window.mallTileField.setDensity('3x4');
window.mallTileField.setDensity('3x5');
window.mallTileField.setDensity('5x8');
```

Gesture behaviors:
- Tap tile = play/pause in Mall context
- Double-tap tile = enter FoundUp view
- Pinch-out = expand into FoundUp's video field
- Pinch-in = collapse back to Mall
- Escape = collapse expanded view

**Pinch Detection** (gesture-engine.js):
```javascript
gestureZone(el, {
  onPinchOut: function() { /* expand */ },
  onPinchIn: function() { /* collapse */ }
});
// Touch: two-finger distance change > 30px
// Desktop: ctrl+wheel
```

**Tests**: 746 passed (38 new video runtime tests)

---

## [2026-04-02] Localhost Mall Dev Harness Phase 3 (Worker B)

**Who**: 0102 (Claude Opus 4.5) — Worker B
**Type**: Developer Tooling
**Slice**: `pfmall_localhost_dev_harness_phase3`

**Files Modified**:
- `public/member/index.html` — localhost dev harness (bypasses Clerk/Firestore)
- `public/member/js/gesture-engine.js` — added `onTap` callback for desktop parity
- `public/f/index.html` — preserve devMall param on redirect

**Files Created**:
- `public/member/tests/test_localhost_dev_harness.py` — 28 harness tests

**Localhost Dev Harness**:

Activation requires BOTH:
```javascript
const isLocalhost = host === 'localhost' || host === '127.0.0.1';
const hasDevFlag = params.get('devMall') === '1';
return isLocalhost && hasDevFlag;
```

Mock data seeded:
```javascript
const mockUserData = {
  id: 'dev_member_001',
  username: 'devmember',
  email: 'dev@localhost',
  inviteValidated: true,
  inviteCodes: ['DEV-0001-0001', ...],
  upsBalance: 1000
};
```

Usage:
```
# Serve with firebase emulator or any local server
firebase serve --only hosting

# Test Mall
http://localhost:5000/member/?devMall=1

# Test Entry
http://localhost:5000/member/foundup.html?id=antifafm_001&devMall=1

# Test Route Bridge
http://localhost:5000/f/antifafm_001?devMall=1
```

**Gesture Engine Desktop Parity**:

Added `onTap` callback:
```javascript
gestureZone(el, {
  onTap: function() { /* single tap/click */ },
  onDoubleTap: function() { /* double tap/click */ },
  onSwipe: function(dir) { /* swipe direction */ }
});
```

Desktop parity:
- click = tap (fires after TAP_CONFIRM_DELAY if not double)
- double-click = double-tap (cancels pending tap)
- click-drag = swipe (unchanged)

**Protected Behaviors (unchanged)**:
- Production Clerk/Firestore auth flow
- Production invite gate
- Production route handling

**Test Results**: 627 passed (full member suite)

---

## [2026-04-02] Route Bridge Hosting Activation Phase 2 (Worker B)

**Who**: 0102 (Claude Opus 4.5) — Worker B
**Type**: Operational Deployment
**Slice**: `route_bridge_hosting_activation_phase2`

**Action**: Firebase Hosting deployment to activate route bridge rewrites

**Hosting Configuration** (firebase.json - gitignored):
```json
"rewrites": [
  { "source": "/f/**", "destination": "/f/index.html" },
  { "source": "**", "destination": "/index.html" }
]
```

**Deployment Target**: `foundupscom` site (https://foundupscom.web.app)

**Verified Route Contract**:
| Route | Behavior |
|-------|----------|
| `/f/{id}` | Serves bridge, JS redirects to `/member/foundup.html?id={id}` |
| `/f/` (no id) | Bridge shows error: "No FoundUp specified" |
| `/f/{invalid}` | Bridge shows error: "Invalid FoundUp ID" |
| `/**` (other) | Catch-all to gateway `/index.html` |

**Runtime Verification**:
- `curl -I /f/antifafm` → HTTP 200, text/html (bridge served)
- WebFetch confirms redirect logic executes
- Destination `/member/foundup.html?id=` loads correctly

**Note**: firebase.json is gitignored; this deployment is operational, not code-tracked.

---

## [2026-04-02] Mobile Thumb-Zone Refinement Phase 2 (Worker B)

**Who**: 0102 (Claude Opus 4.5) — Worker B
**Type**: UX Improvement
**Slice**: `pfmall_mobile_thumbzone_refinement_phase2`

**Files Modified**:
- `public/member/css/mall-tile-field.css` — projection chip touch targets, inspector bottom sheet
- `public/member/css/member.css` — mall header safe-top padding
- `public/member/tests/test_mobile_blockers.py` — added 5 thumb-zone tests
- `public/member/tests/test_mall_tile_field.py` — added chip touch target test

**Phone Ergonomics Refinements**:

1. **Projection Chips** (44px WCAG touch targets)
```css
.mall-projection-chip {
  min-height: 44px;
  padding: 0.6rem 1rem;
  font-size: 0.8rem;
}
```

2. **Inspector as Bottom Sheet on Phone** (<=480px)
```css
@media (max-width: 480px) {
  .tile-inspector {
    top: auto;
    bottom: 0;
    transform: translateY(100%);
    border-radius: 1.5rem 1.5rem 0 0;
  }
}
```

3. **Inspector Enter Button** (48-52px thumb target)
```css
.tile-inspector-enter {
  min-height: 48px;  /* desktop */
}
@media (max-width: 480px) {
  .tile-inspector-enter {
    min-height: 52px; /* phone */
  }
}
```

4. **Mall Header Safe-Top** (notched phones)
```css
.mall-header {
  padding: calc(0.5rem + var(--safe-top)) 0 0.5rem;
}
```

5. **Bottom Sheet Handle Indicator**
```css
.tile-inspector::before {
  content: "";
  width: 2rem;
  height: 0.25rem;
  background: rgba(255, 255, 255, 0.25);
}
```

**Protected Behaviors (unchanged)**:
- Tap = inspect (immediate)
- Double-tap = enter FoundUp directly
- Three-anchor model
- Red Dog positioning

**Test Results**: 77 passed (mobile + tile field tests)

---

## [2026-04-02] Mobile Blockers Phase 1 (Worker B)

**Who**: 0102 (Claude Opus 4.5) — Worker B
**Type**: Bug Fix / UX Improvement
**Slice**: `pfmall_mobile_blockers_phase1`

**Files Modified**:
- `public/member/css/member.css` — safe area variables, dynamic viewport height
- `public/member/js/mall-tile-field.js` — immediate tap response (no 300ms delay)
- `public/member/index.html` — viewport-fit=cover meta
- `public/member/foundup.html` — viewport-fit=cover, safe area, dynamic height
- `public/member/tests/test_mall_tile_field.py` — updated for renamed variable

**Files Created**:
- `public/member/tests/test_mobile_blockers.py` — 19 mobile blocker tests

**P0 Fixes Applied**:

1. **Safe Area Insets** (iPhone home indicator)
```css
:root {
  --safe-bottom: env(safe-area-inset-bottom, 0px);
}
.red-dog-anchor {
  bottom: calc(1.25rem + var(--safe-bottom));
}
```

2. **Dynamic Viewport Height** (iOS Safari 100vh bug)
```css
.member-area, .mall-shell {
  min-height: 100vh;
  min-height: 100dvh;
}
@supports not (min-height: 100dvh) {
  min-height: -webkit-fill-available;
}
```

3. **Tap Latency Fix** (300ms delay removed)
```javascript
// OLD: setTimeout wait before openInspector
// NEW: openInspector(index) called immediately
// Double-tap still works to bypass inspector and enter directly
```

**Behavioral Change**:
- Tap → opens inspector **immediately** (was: 300ms delay)
- Double-tap → enters FoundUp directly (unchanged semantics)

**Protected Behaviors (unchanged)**:
- Tile inspector overlay
- Tile enter flow (via inspector button or double-tap)
- Three-anchor structure
- /member/foundup.html?id= fallback path

**Test Results**: 485 passed, 2 warnings

---

## [2026-04-02] Route Contract Bridge Phase 1 (Worker B)

**Who**: 0102 (Claude Opus 4.5) — Worker B
**Type**: Feature Addition
**Slice**: `pfmall_route_contract_bridge_phase1`

**Files Created**:
- `public/f/index.html` — route bridge for `/f/{foundup_id}`
- `public/member/tests/test_route_contract_bridge.py` — 15 route bridge tests

**Files Modified**:
- `firebase.json` — added `/f/**` rewrite rule before catch-all

**Bridge Behavior**:
```
/f/{foundup_id}  →  parse id  →  /member/foundup.html?id={foundup_id}
/f/{id}/{subpath} →  redirect with subpath param preserved
/f/ (no id)       →  error: "No FoundUp specified" + Mall link
/f/{invalid}      →  error: "Invalid FoundUp ID" + Mall link
```

**Firebase Hosting**:
```json
"rewrites": [
  { "source": "/f/**", "destination": "/f/index.html" },
  { "source": "**", "destination": "/index.html" }
]
```

**Route Contract Truth**:
- `/f/{id}` is the canonical route family per contract
- Current bridge redirects to transitional entry (shell-owned)
- No fake tenant runtime — explicit redirect to `/member/foundup.html`
- Subpath preserved for future routing expansion

**Test Results**: 403 passed, 2 warnings

---

## [2026-04-02] FoundUp Entry Shell Alignment Phase 3 (Worker B)

**Who**: 0102 (Claude Opus 4.5) — Worker B
**Type**: Refinement
**Slice**: `pfmall_foundup_entry_shell_alignment_phase3`

**Files Modified**:
- `public/member/foundup.html` — aligned branding and route-contract language

**Files Created**:
- `public/member/tests/test_foundup_entry_shell.py` — 19 focused entry shell tests

**Stale Branding Removed**:
- `p.fMALL` → `FoundUps Mall` (title, meta, dynamic title)
- "carousel" → removed from navigation copy

**Route Contract Wording**:
- "Route" → "Target Route" (clarifies not yet live)
- `routing_prefix` displayed as target, not active link

**Transitional Path Preserved**:
- `/member/foundup.html?id={foundup_id}` — unchanged, still the shell-owned entry

**Protected Behaviors (unchanged)**:
- Back to Mall navigation
- Red Dog concierge sheet
- Deep-linkable entry pages
- Readiness guide content

**Test Results**: 388 passed, 2 warnings

---

## [2026-04-01] FoundUp Handoff Plane Phase 2 (Worker B)

**Who**: 0102 (Claude Opus 4.5) — Worker B
**Type**: Refinement
**Slice**: `pfmall_foundup_handoff_plane_phase2`

**Files Modified**:
- `public/member/js/mall-planes.js` — refined handoff plane, removed stale semantics
- `public/member/tests/test_navigation_planes.py` — updated TestDoubleTapSave → TestFoundUpHandoff

**Stale Behaviors Removed**:
- Save/favorite localStorage logic (`toggleSave`, `isSaved`, `pfmall_saved_` prefix)
- `fvSaveIndicator` element in view plane
- "Double-tap to save" hint text
- `onDoubleTap: toggleSave` gesture binding

**Handoff Language Updated**:
- "Full details" → "Open FoundUp"
- `fv-detail-link` class → `fv-open-link` class
- Routing prefix surfaced in CTA: "Open FoundUp → /f/antifafm"
- Hint simplified to: "Swipe up to close · Swipe sideways for next"

**Fallback Path (truthful today)**:
- `/member/foundup.html?id={foundup_id}` — transitional shell-owned entry
- Future: `/f/{foundup_id}` when in-scope routes are live

**Protected Behaviors (unchanged)**:
- Tile tap → inspect
- Tile double-tap → enter view plane
- Swipe-up → close view plane
- Swipe left/right → navigate between FoundUps
- Escape → close view plane
- Account plane / Red Dog access

**Test Results**: 321 passed, 2 warnings

---

## [2026-04-01] Mall Projection Shell Phase 1 (Worker B)

**Who**: 0102 (Claude Opus 4.5) — Worker B
**Type**: Feature Addition
**Slice**: `pfmall_mall_projection_shell_phase1`

**Files Modified**:
- `public/member/index.html` — added projection controls nav in middle anchor
- `public/member/css/mall-tile-field.css` — projection chip styles (already present from phase 1)
- `public/member/js/mall-tile-field.js` — projection sorting logic and API
- `public/member/tests/test_mall_tile_field.py` — added 19 projection tests

**Projection Controls**:
```html
<nav id="mallProjection" class="mall-projection" aria-label="Sort FoundUps">
  <button data-projection="default">All</button>
  <button data-projection="alpha">A-Z</button>
  <button data-projection="readiness">Readiness</button>
  <button data-projection="category">Category</button>
</nav>
```

**Sort Modes (using catalog fields only)**:
- `default` — original catalog order preserved
- `alpha` — sort by `name` A-Z
- `readiness` — sort by `launch_readiness` (ready > conditional > discoverable_only)
- `category` — sort by `category`, then alpha

**Public API Extended**:
```javascript
window.mallTileField.setProjection(name)   // Set projection mode
window.mallTileField.getProjection()       // Get current projection
window.mallTileField.resetProjection()     // Reset to default
```

**Chrome Minimal**: Chips are compact pills (0.72rem), low-contrast until active

**Ownership Boundaries**:
- B owns: projection UI, sorting logic, chip wiring
- C owns: account-plane content, Red Dog panel content/logic (untouched)

**Test Results**: 52 passed, 2 warnings

---

## [2026-04-01] Mall Anchor Shell Phase 2 (Worker B)

**Who**: 0102 (Claude Opus 4.5) — Worker B
**Type**: Shell Refinement
**Slice**: `pfmall_mall_anchor_shell_phase2`

**Files Modified**:
- `public/member/index.html` — aligned shell to 3-anchor model
- `public/member/css/member.css` — anchor layout, minimal header, self-anchor styles
- `public/member/css/mall-tile-field.css` — tile field takes full middle space
- `public/member/tests/test_mall_tile_field.py` — added 7 anchor model tests

**Anchor Model Alignment**:
```
+---------------------------+
|       TOP ANCHOR          |  data-anchor="top"
|  (minimal brand + avatar) |  Self / Account access
+---------------------------+
|                           |
|      MIDDLE FIELD         |  data-anchor="middle"
|   (#mallTileField)        |  Discovery / Navigation
|                           |
+---------------------------+
|      BOTTOM ANCHOR        |  data-anchor="bottom"
|   (#redDogAnchor)         |  Red Dog / Digital Twin
+---------------------------+
```

**Chrome Reduction**:
- REMOVED: `.mall-copy` instruction section ("Tap to inspect...")
- REMOVED: `.mall-brand-kicker` ("Invite access granted")
- REMOVED: `.mall-status-chip` ("invite admitted")
- MINIMIZED: Brand to small logo only (self-anchor dominates)

**Ownership Boundaries**:
- B owns: shell structure, anchor positioning, chrome
- C owns: account-plane content, Red Dog panel content/logic

**Test Results**: 259 passed, 2 warnings

---

## [2026-04-01] Tile Field Phase 1 (Worker B)

**Who**: 0102 (Claude Opus 4.5) — Worker B
**Type**: Feature Replacement
**Slice**: `pfmall_tile_field_phase1`

**Files Created**:
- `public/member/css/mall-tile-field.css` — tile grid layout, inspector overlay styles
- `public/member/js/mall-tile-field.js` — tile rendering, tap/double-tap detection, inspector
- `public/member/tests/test_mall_tile_field.py` — 26 tests for tile field structure and behavior

**Files Modified**:
- `public/member/index.html` — replaced carousel with tile field, reduced chrome, added SoftProto mount point
- `public/member/tests/test_account_concierge.py` — updated for tile field model
- `public/member/tests/test_navigation_planes.py` — updated for tile field model

**Structure Change**:
- REMOVED: `.mall-carousel-shell`, `.mall-track`, `.mall-dots`, `.mall-focus`
- ADDED: `#mallTileField[data-softproto-mount="tile-field"]`
- Chrome reduction: verbose marketing copy replaced with "Tap to inspect. Double-tap to enter."

**Gesture Map (Tile Field)**:
- Tap tile → opens inspector overlay (preview)
- Double-tap tile → enter FoundUp view directly
- Tap inspector scrim → close inspector
- Tap "Enter FoundUp" button → enter FoundUp view
- Escape → closes inspector first, then other planes

**SoftProto Integration**:
- Mount point: `#mallTileField[data-softproto-mount="tile-field"]`
- Each tile has `data-foundup-id` for addressable targeting
- Inspector z-index: 180-181 (below gesture hints 300)

**Guardrails Respected (D)**:
- Escape key handling preserved (inspector → planes → close)
- Red Dog button unchanged
- Account plane unchanged
- Invite gate / username claim blocking unchanged

**Test Results**: 145/145 passing

---

## [2026-04-01] Navigation Planes Phase 2 (Worker B)

**Who**: 0102 (Claude Opus 4.6) — Worker B
**Type**: Feature Addition
**Slice**: `pfmall_member_navigation_planes_phase2`

**Files Created**:
- `public/member/js/gesture-engine.js` — unified touch + mouse gesture detection (gestureZone, dragScroll)
- `public/member/js/mall-planes.js` — FoundUp view plane state machine + drag-scroll wiring
- `public/member/js/gesture-hints.js` — one-time dismissible gesture discovery hints
- `public/member/css/mall-planes.css` — view plane transitions, hint overlay styles
- `public/member/tests/test_navigation_planes.py` — 42 tests across 8 categories

**Files Modified**:
- `public/member/index.html` — added view plane HTML, CSS link, script tags, wired card click to in-page view, added closeSurfaces integration, added carousel sync callback, added gesture hints HTML

**Plane Model**:
1. Mall (default) — horizontal scroll-snap card carousel
2. Account plane (swipe-down from top) — unchanged, managed by account-concierge.js
3. FoundUp view (slides up from bottom) — new lightweight in-page overlay

**Gesture Map**:
- Tap card → opens FoundUp view (was: navigate to foundup.html)
- Swipe up in view → closes, returns to Mall
- Swipe left/right in view → navigate to next/previous FoundUp
- Double-tap / double-click in view → toggle save (localStorage)
- Mouse drag on Mall track → scroll carousel (desktop parity)
- Escape → closes view; ArrowLeft/ArrowRight → navigate in view

**Behavior Change**:
1. Card taps now open an in-page FoundUp quick view instead of navigating away.
2. Full entry page (foundup.html) remains accessible via "Full details" link inside the view.
3. Desktop users can drag the carousel track (mouse drag maps to touch swipe).
4. First-time visitors see a gesture discovery hint overlay (dismissible, persisted in localStorage).
5. Double-tap/click saves a FoundUp locally (heart indicator, localStorage).
6. FoundUp view supports swipe-left/right to browse without returning to Mall.
7. All existing surfaces (account plane, Red Dog panel, overlay scrim) remain untouched.

**Why**: Mall navigation lacked gesture-driven PWA feel. Card taps broke flow by navigating away. This slice adds physical, predictable plane transitions with desktop-touch parity.

---

## [2026-04-01] Red Dog Concierge Phase 1

**Who**: 0102 (Claude Opus 4.6)
**Type**: Feature Addition
**Slice**: `pfmall_member_red_dog_concierge_phase1`

**What**: Red Dog becomes a real shell-owned concierge surface on both Mall and FoundUp entry pages.

**Files Modified**:
- `public/member/foundup.html` — added concierge sheet with scrim, toggle, context-aware guidance, readiness key, navigation tips, Escape/scrim dismiss
- `public/member/index.html` — added readiness guide and navigation guidance sections to existing Red Dog panel
- `public/member/css/member.css` — added readiness dot/key styles for Mall panel

**Files Created**:
- `modules/foundups/pfmall/tests/test_member_red_dog_concierge.py` — 26 tests

**Behavior Change**:
1. FoundUp entry page: Red Dog opens a concierge sheet (not navigation).
2. Concierge sheet is context-aware — shows current FoundUp name, readiness, and entry copy.
3. Both pages now explain all three readiness levels (Ready, Conditional, Discoverable Only) with colored dots.
4. Both pages now include navigation guidance.
5. Sheet dismisses via scrim click or Escape key.
6. No backend dependency — all content is static or from mall-catalog.json.

**Why**: Red Dog was a return-to-Mall affordance on entry pages and lacked guidance on the Mall page. Phase 1 concierge gives it real utility without fake AI theater.

### [2026-04-01] Red Dog Concierge JS Module (Worker C)

**Who**: 0102 (Claude Opus 4.6) — Worker C
**Slice**: `pfmall_member_red_dog_concierge_phase1` (continued)

**Files Created**:
- `public/member/js/red-dog-concierge.js` — standalone concierge module (IIFE, no deps)
- `public/member/tests/test_red_dog_concierge.py` — 30 focused tests

**Files Modified**:
- `public/member/index.html` — added `<script src="js/red-dog-concierge.js">` tag
- `public/member/foundup.html` — added `<script src="js/red-dog-concierge.js">` tag

**What the module does**:
1. Detects page context (Mall vs FoundUp entry) via `#mallTrack` / `#entryContent`
2. Finds concierge host (`#redDogPanel` or `#conciergeSheet`)
3. Injects collapsible "Mall guide" help topics using `<details>` elements
4. Mall page topics: what the Mall is, how to browse, entering FoundUps, account info
5. Entry page topics: what this page shows, readiness states explained, navigation back
6. Injects minimal CSS for topic styling
7. No network calls, no fake AI, no backend dependency

**Hook mismatch noted**: Handoff specified `#redDogButton`, `#conciergeHost`, `#accountPlane`, `#accountPlaneHandle` — none exist. Built against actual hooks: `#redDogBtn`, `#redDogPanel`, `#entryRedDog`, `#conciergeSheet`.

---

## [2026-03-31] FoundUp Entry Page (Phase 1)

**Who**: 0102 (Claude Opus 4.6)
**Type**: Feature Addition
**Slice**: `pfmall_member_foundup_entry_phase1`

**What**: Card taps now navigate to a dedicated entry page instead of an in-page overlay.

**Files Created**:
- `public/member/foundup.html` — dedicated FoundUp entry view

**Files Modified**:
- `public/member/index.html` — card click navigates to `foundup.html?id={id}` instead of `openFoundupOverlay()`
- `public/member/README.md` — added `foundup.html` to runtime shape
- `public/member/INTERFACE.md` — updated hosted assets and UI contract
- `public/member/ModLog.md` — this entry

**Behavior Change**:
1. Tapping a FoundUp card navigates to `/member/foundup.html?id={foundup_id}`.
2. Entry page is deep-linkable (share URL, bookmark, back button works).
3. Shows readiness posture, detail rows, what-happens-next copy, and description.
4. Not-found state for unknown IDs. Back-to-Mall navigation.
5. Red Dog button present (currently returns to Mall).

**Why**: In-page overlays are not deep-linkable and break browser history. Dedicated page enables sharing, bookmarks, and proper back-button behavior.

---

## [2026-03-31] Invite-Gated Mall Cutover

**Who**: 0102 (Codex)
**Type**: Experience Cutover

**What**: Replaced the admitted `/member/` shell with a Firebase-hosted p.fMALL experience while preserving the existing invite/auth gateway.

**Files Modified**:
- `public/member/index.html`
- `public/member/css/member.css`
- `public/member/README.md`
- `public/member/INTERFACE.md`
- `public/member/ModLog.md`

**Files Created**:
- `public/member/mall-catalog.json`

**Behavior Change**:
1. Invite validation and username claim remain unchanged.
2. Authenticated admitted users now land in a swipe-first Mall shell instead of the legacy member shell.
3. Invite codes moved into the Red Dog concierge sheet.
4. No gateway rewrite or landing-page redirect surgery was required.

**Why**:
- `foundups.com` gateway behavior was already working and had to stay stable.
- The operational bug was the admitted `/member/` destination, not the invite gate itself.

---

## [2026-02-18] Layer 1: Shell Implementation

**Who**: 0102 (Claude Opus 4.5)
**Type**: New Module Creation
**WSP**: WSP 49 (Structure), WSP 72 (Independence)

**What**: Created member area shell with authentication and navigation.

**Files Created**:
- `public/member/index.html` - Main member area with auth state, navigation, placeholders
- `public/member/css/member.css` - Shared styles (dark theme, glassmorphism)
- `public/member/README.md` - Module documentation
- `public/member/INTERFACE.md` - Public API definition
- `public/member/ROADMAP.md` - Layer progression plan
- `public/member/ModLog.md` - This file

**Files Modified**:
- `public/index.html` - Added redirect to `/member/` after successful signup

**Architecture Decisions**:
1. **Occam's Layered** - Build one layer at a time, test, then next
2. **No God Modules** - Each section (wallet, foundups, agents) is independent
3. **Same Design Language** - Matches landing page (CSS variables, glassmorphism)
4. **Firebase Auth** - Uses same Firebase project as landing page
5. **Hash-based Routing** - Simple, no additional dependencies

**Layer 1 Features**:
- Firebase auth state listener
- Redirect to landing if not authenticated
- Sidebar navigation with section routing
- Mobile responsive (collapsible sidebar)
- User info display (name, avatar)
- Invite codes display with copy functionality
- Placeholder sections for all future modules
- Sign out functionality

**Next Layer**: Dashboard (Layer 2) - Real data integration

**WSP References**:
- WSP 49: Module structure compliance
- WSP 72: Module independence (no cross-dependencies)
- WSP 22: Change logging (this file)
- WSP 50: Searched HoloIndex before creating

---

*Created: 2026-02-18*
