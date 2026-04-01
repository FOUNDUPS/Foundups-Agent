# Member Area Module Change Log

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
