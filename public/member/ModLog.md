# Member Area Module Change Log

## [2026-04-13] Adaptive Desktop 6x3 Tile Layout (Worker CL, WSP 15/97/104)

**Who**: 0102 - Worker CL
**Slice**: `PFMALL_DESKTOP_6X3_ADAPTIVE_LAYOUT_PHASE1`
**What**: Verified and tested viewport-adaptive density selection for desktop/fine-pointer viewports.

**Implementation** (confirmed existing):
- `6x3` density preset (6 columns, 3 rows) optimized for wide desktop viewports
- Viewport detection using `matchMedia('(pointer: coarse)')` + width/height checks
- Auto-selects `6x3` for fine-pointer + landscape + ≥1024px viewports
- Auto-selects `4x6` for coarse-pointer + landscape + ≥768px (tablet landscape)
- Defaults to `3x5` for mobile-first portrait viewports
- Resize listener for dynamic re-evaluation
- Manual `setDensity()` calls mark override, preventing auto-selection
- `resetDensityOverride()` to restore auto-selection

**Files Modified**:
- `public/member/tests/test_video_mall_field_runtime.py` - Added `TestAdaptiveDesktopLayout` (15 tests)
- `public/member/INTERFACE.md` - Documented 6x3 preset and adaptive API methods

**Test Coverage Added** (15 tests in `TestAdaptiveDesktopLayout`):
- `6x3` preset in CSS and JS validDensities
- `detectOptimalDensity()` and `autoSelectDensity()` functions
- `densityManuallySet` tracking and manual override preservation
- Resize handler binding
- `resetDensityOverride` and `autoSelectDensity` API exposure
- Desktop detection uses fine-pointer, 1024px width, landscape
- Mobile default preserved as `3x5`

**Viewport Rule for 6x3**: `!isCoarsePointer && width >= 1024 && isLandscape`
**Mobile Default**: `3x5` (unchanged)
**Manual Override Precedence**: Manual `setDensity()` blocks auto-selection until `resetDensityOverride()` called

**Test Results**: 273 passed (258 + 15 new)

**WSP 15 Applied**: Incremental — tests added without changing working implementation.
**WSP 97 Applied**: Truthful reporting of existing implementation vs new test coverage.
**WSP 104 Applied**: No route namespace changes.

---

## [2026-04-13] pfMALL YouTube Wall Live Verification (Worker CH, WSP 97/104)

**Who**: 0102 - Worker CH
**Slice**: `PFMALL_YOUTUBE_WALL_LIVE_VERIFICATION_PHASE1`
**What**: End-to-end browser verification of pfMALL tile wall with YouTube-backed FoundUp queues.

**Method**: Local HTTP server (`python -m http.server 8090`) serving `public/`, Clerk auth bypassed via JS injection, Chrome DevTools MCP for automated verification.

**Catalog Truth** (13 entries, 4 targets verified):

| FoundUp | videos | poster | tap→play | lane advance | expand | collapse |
|---------|--------|--------|----------|-------------|--------|----------|
| `move2japan` | 573 | /media/posters/move2japan.jpg | PASS | 0→1 PASS | 573 tiles PASS | 13 tiles PASS |
| `undaodu` | 512 | /media/posters/undaodu.jpg | PASS | 0→1 PASS | 512 tiles PASS | 13 tiles PASS |
| `foundups_main` | 44 | /media/posters/foundups_main.jpg | PASS | 0→1 PASS | 44 tiles PASS | 13 tiles PASS |
| `antifafm` | 34 | /media/posters/antifafm.jpg | PASS | 0→1 PASS | 34 tiles PASS | 13 tiles PASS |

**Fullscreen Player**: `mallVideoPlayer.open()` loads YouTube iframe, shows video title, play controls, Enter FoundUp button (WSP 104 route `/f/{foundup_id}`). `mallVideoPlayer.close()` returns to tile wall cleanly.

**Projection Controls**: All, A-Z, Readiness, Category — all re-sort tiles correctly.

**UI Elements per tile**: poster background, readiness badge, queue count badge, audio button, enter button, expand button, preview stage — all present for video-backed tiles.

**API surface verified**: `initialize`, `togglePlay`, `advanceToNextInLane`, `expandFoundUp`, `collapseFoundUp`, `setProjection`, `startLanePreview`, `stopInlinePreview`.

**Pytest**: 258 passed (test_video_mall_field_runtime.py + test_mall_tile_field.py)

**No bugs found. No code changes required.**

**WSP 97 Applied**: Browser-verified, not assumed.
**WSP 104 Applied**: Enter FoundUp routes to `/f/{foundup_id}` canonical path.

---

## [2026-04-13] Kosei entry_url Restored (Worker BX5, WSP 97/104)

**Who**: 0102 - Worker BX5
**Slice**: `KOSEI_RESTORE_ENTRY_URL_PHASE1`
**What**: Restored Kosei `entry_url` after BX4 verified iframe embeddability.

**Files Modified**:
- `public/member/mall-video-catalog.json` - Added `entry_url`, changed `launch_readiness` to `ready`
- `public/member/tests/test_route_contract_bridge.py` - Updated Kosei tests to verify entry_url presence

**Binding Truth (After BX5)**:
- Landing: `/f/kosei` resolves through canonical shell contract
- App mount: `/f/kosei/app` embeds deployed app (verified in BX4)
- `entry_url`: `https://foundupscom.web.app/kosei/app/`
- `launch_readiness`: `ready`

**WSP 104 Applied**: Route family `/f/kosei` and `/f/kosei/app` unchanged.
**WSP 97 Applied**: Truthful metadata — entry_url set only after browser verification.

**Test Results**: 45 passed

---

## [2026-04-12] Kosei Shell Route Binding (Worker BU, WSP 15/97/104)

**Who**: 0102 - Worker BU
**Slice**: `KOSEI_LANDING_AND_APP_BINDING_PHASE1`
**What**: Codify Kosei as second canonical shell-bound FoundUp after GotJunk.

**Files Modified**:
- `public/member/tests/test_route_contract_bridge.py` - Added `TestKoseiTenantBinding` (5 tests)

**Binding Truth**:
- Landing: `/f/kosei` resolves through canonical shell contract
- App mount: `/f/kosei/app` shows "App Not Ready" (truthful - no embeddable runtime yet)
- `entry_url`: omitted (no fake URL)
- `launch_readiness`: `discoverable_only`

**Pre-existing Truth** (no changes needed):
- `modules/foundups/kosei/foundup_manifest.json` - Already has `routing_prefix: /f/kosei`, `data_namespace: idb_kosei`, `entry_url: null`
- `public/member/mall-video-catalog.json` - Already has matching routing fields, no entry_url

**WSP 104 Applied**: No root sprawl; route family is `/f/kosei` and `/f/kosei/app`.
**WSP 97 Applied**: Truthful readiness - "discoverable_only" state, no fake URLs.

**Test Results**: 45 passed (was 40)

---

## [2026-04-11] GotJunk App Binding Attempted + X-Frame-Options Blocker (Worker BS, WSP 15/97/104)

**Who**: 0102 - Worker BS
**Slice**: `GOTJUNK_REAL_APP_BINDING_PHASE1`
**What**: Attempted to bind `gotjunk_001` to Cloud Run deployment. Reverted due to iframe blocker.

**BLOCKER**: Cloud Run returns `X-Frame-Options: SAMEORIGIN` which prevents iframe embed at `/f/gotjunk_001/app`. The shell app mount uses an `<iframe>` to load tenant apps.

**Resolution**: Reverted `entry_url` to `null`, kept `launch_readiness: discoverable_only`. GotJunk remains discoverable but not embeddable until Cloud Run headers are fixed.

**WSP 97 Applied**: No fake URL — entry_url stays null until iframe works.

---

## [2026-04-10] Non-Video QuickView Actions (Worker BM, WSP 15/97/104)

**Who**: 0102 - Worker BM
**Slice**: `NON_VIDEO_QUICKVIEW_ACTIONS_PHASE1`
**What**: Add CTA buttons to non-video FoundUp QuickView plane based on source_type.

**Files Modified**:
- `public/member/js/mall-planes.js` - Added CTA button rendering in QuickView
- `public/member/css/mall-planes.css` - Added `.fv-cta-btn` styles
- `public/member/tests/test_non_video_quickview_actions.py` - 12 tests

**CTA Mapping**:
| source_type | Label | Action |
|-------------|-------|--------|
| `github_repo` | "View Repo" | Opens external_url |
| `external_app` | "Open App" | Opens external_url |
| `internal_service` | "Open Service" | Opens external_url |

**WSP 104 Applied**: CTAs open external URLs, don't create new route families.
**WSP 97 Applied**: CTA only shown when external_url exists and is valid.

**Test Results**: 12 passed

---

## [2026-04-09] Field Scope Projection System (Worker BK, WSP 15/97)

**Who**: 0102 - Worker BK
**Slice**: `FIELD_SCOPE_PROJECTION_PHASE1`
**What**: Add field scope filtering for Personal Mall (My Mall) and search projections.

**Files Modified**:
- `public/member/js/mall-tile-field.js` - Added field scope system
- `public/member/tests/test_video_mall_field_runtime.py` - Added Personal Mall + Search tests

**API Surface**:
- `projectPersonalMall()` - Filter to creator === '012'
- `setFieldScope({ type, query })` - Generic scope setter
- `searchByCreator(query)` - Case-insensitive creator search
- `filterByCategory(cat)` - Category filter
- `filterByTag(tag)` - Tag filter
- `clearFieldScope()` - Reset to full catalog
- `getFieldScope()` - Get current scope

**Scope Types**:
- `personal` - creator === '012'
- `creator` - substring match on creator/entity
- `category` - exact match (case-insensitive)
- `tag` - exact match in tags array

**Sort Policy**: video_count > 0 first, then display_order

**Test Results**: 258 passed

---

## [2026-04-08] FLIP Expand/Collapse Animation (Worker BJ, WSP 15)

**Who**: 0102 - Worker BJ
**Slice**: `FLIP_EXPAND_COLLAPSE_ANIMATION_PHASE1`
**What**: Add FLIP animation for smooth expand/collapse transitions between Mall and FoundUp video field.

**Files Modified**:
- `public/member/js/mall-tile-field.js` - Added FLIP animation logic
- `public/member/css/mall-tile-field.css` - Added transition layer styles
- `public/member/tests/test_video_mall_field_runtime.py` - Added animation tests

**Animation Flow**:
1. Capture source tile rect
2. Create transition layer at source position
3. Render target content
4. Animate layer to target rect
5. Cleanup layer after animation

**Reduced Motion**: Respects `prefers-reduced-motion: reduce` media query.

**Test Results**: 243 passed

---
