# TestModLog — public/member/tests/

Test evolution log for the p.fMALL member shell test suite.

---

## 2026-04-10 | Route Contract Bridge Tests (WSP 104/97)

**File**: `test_route_contract_bridge.py` (rewritten)
**Tests**: 22 | **Classes**: 7 | **Result**: 22 passed
**Worker**: BM

Validates WSP 104 canonical landing route cutover from redirect bridge to direct render:

| Class | Count | What it covers |
|-------|-------|----------------|
| TestCanonicalRouteExists | 3 | Landing HTML exists, parses foundup_id, fetches catalog |
| TestFirebaseRouting | 3 | firebase.json has /f/** rewrite before catchall |
| TestCanonicalRouteBehavior | 4 | Missing ID error, invalid ID, mall fallback, subpath capture |
| TestCanonicalRouteRendering | 3 | No redirect, renders entry content directly, marks canonical |
| TestWsp104Compliance | 3 | Canonical route displayed, no transitional redirect, path-based identity |
| TestSubpathForwardCompatibility | 3 | Subpath captured, info displayed, /app mount comment |
| TestTransitionalFallbackPreserved | 3 | foundup.html still exists and accepts id param |

**Key changes**:
- Tests verify `/f/{foundup_id}` renders content directly (no `location.replace`)
- Tests verify identity from `window.location.pathname`, not query params
- Tests verify subpath capture for future `/f/{id}/app` mount
- Transitional fallback (`/member/foundup.html?id=`) preserved for backward compat

---

## 2026-04-10 | Portrait Tile Geometry Tests (WSP 15/97)

**File**: `test_video_mall_field_runtime.py` (extended)
**Tests**: 5 new | **Class**: `TestPortraitTileGeometry` | **Result**: 159 passed total
**Worker**: BJ

Validates portrait-first 9:16 tile geometry for Shorts-style video wall:

| Test | What it covers |
|------|----------------|
| test_tiles_are_portrait_aspect | `aspect-ratio: 9 / 16` in CSS |
| test_default_columns_is_three | `--field-columns: 3` default for mobile-first |
| test_tile_radius_is_minimal | `border-radius: var(--tile-radius, 0.4rem)` for low chrome |
| test_gap_is_tight | `gap: var(--tile-gap, 0.2rem)` for dense wall |
| test_js_default_density_is_3x5 | `currentDensity = '3x5'` in JS |

**Updated tests**:
- `test_density_preset_classes`: Updated from `2x3/3x4/3x5/5x8` to `3x4/3x5/4x6/5x8`
- `test_touch_padding_value`: Updated from `2.4rem` to `1.5rem` for low-chrome layout

---

## 2026-04-10 | Preview Resource Hardening Tests (WSP 15/97)

**File**: `test_video_mall_field_runtime.py` (extended)
**Tests**: 13 new | **Class**: `TestPreviewResourceHardening` | **Result**: 154 passed total
**Worker**: BD

Validates inline preview resource discipline for mobile/PWA:

| Test | What it covers |
|------|----------------|
| test_stale_callback_guard_increment_first | `previewGeneration++` happens FIRST in teardown |
| test_html5_video_load_called | `video.load()` releases media buffers |
| test_html5_video_removed_from_dom | Video element removed from parent on teardown |
| test_html5_video_onerror_cleared | `onerror` handler cleared to prevent stale callback |
| test_visibility_handler_bound | `bindVisibilityHandler()` exists and called |
| test_visibility_change_pauses_preview | `visibilitychange` pauses preview when hidden |
| test_invalid_url_failsafe | URL validated before preview attempt |
| test_youtube_error_callback_guarded | YT `onError` checks generation guard |
| test_html5_video_error_handler | `video.onerror` fails quietly |
| test_fullscreen_handoff_cleanup | `openFullscreenFromTile` stops preview first |
| test_expand_cleanup | `expandFoundUp` stops preview first |
| test_collapse_cleanup | `collapseFoundUp` stops preview first |
| test_visibility_bound_guard | Handler has double-bind guard |

**Updated test**:
- `test_one_active_preview_rule`: Updated to check for defensive cleanup comment

---

## 2026-04-09 | Tile Keyboard Accessibility Tests (WSP 15/97)

**File**: `test_tile_keyboard_a11y.py` (new)
**Tests**: 27 | **Classes**: 6 | **Result**: 27 passed
**Worker**: BC

Validates WCAG 2.1 Level AA keyboard accessibility for Mall tiles:

| Class | Count | What it covers |
|-------|-------|----------------|
| TestTileFocusVisibility | 5 | tabindex, aria-label, focus-visible ring, hover/focus separation |
| TestKeyboardActivation | 4 | keydown handler, Space/Enter/Escape key behavior |
| TestControlAccessibility | 7 | Audio/expand button aria-labels, titles, focus-visible CSS |
| TestFocusReturn | 5 | returnFocusId tracking, focus restore by stable identity |
| TestMallPlanesFocusStyles | 4 | Close button, CTA, secondary link focus styles |
| TestARIASemantics | 2 | Article element, mall-planes keyboard handler |

**Key A11y improvements verified**:
- Tiles have visible purple focus ring (`box-shadow: 0 0 0 3px rgba(141, 113, 255, 0.35)`)
- Keyboard Enter/Space parity with pointer interactions
- Focus returns to originating tile by `foundup_id` (stable across projection/filter changes)
- Control buttons (audio/expand) focusable with proper labels
- `test_focus_return_uses_stable_identity` validates closeView queries by `data-foundup-id`, not `data-index`

---

## 2026-04-09 | Non-Video Action Surface Phase 2 Tests (WSP 15/97)

**File**: `test_non_video_quickview_actions.py` (extended)
**Tests**: 17 new/updated | **Classes**: `TestQuickViewActionSurface`, `TestOverlayActionSurface`, `TestQuickViewActionCSS`, `TestOverlayActionCSS` | **Result**: 42 passed total
**Worker**: BB

Validates dominant primary CTA and demoted secondary path:

| Test | What it covers |
|------|----------------|
| test_renders_primary_cta_class | `.fv-primary-cta` used for source action |
| test_renders_secondary_link_class | `.fv-secondary-link` for demoted entry path |
| test_renders_source_context | `.fv-source-context` shows type + domain |
| test_extract_domain_helper | `extractDomain()` for destination context |
| test_secondary_link_says_more_about | "More about {name}" text |
| test_overlay_renders_primary_cta_class | Overlay uses `.foundup-overlay-primary-cta` |
| test_overlay_renders_secondary_link_class | Overlay uses `.foundup-overlay-secondary-link` |
| test_overlay_renders_source_context | Overlay context with domain |
| test_overlay_has_actions_container | `.foundup-overlay-actions` container |
| test_overlay_extract_domain_helper | Overlay `extractDomain()` helper |
| test_video_primary_cta_is_open_foundup | Video entries retain Open FoundUp |
| test_overlay_video_primary_cta_is_open_foundup | Overlay video entries unchanged |
| test_primary_cta_styles (CSS) | `.fv-primary-cta` styled dominant |
| test_secondary_link_styles (CSS) | `.fv-secondary-link` styled demoted |
| test_source_context_styles (CSS) | `.fv-source-context` styled subtle |
| test_overlay_primary_cta_styles (CSS) | Overlay primary CTA styled |
| test_overlay_actions_container (CSS) | Overlay actions container styled |

---

## 2026-04-09 | Mall Locomotion and Gesture Polish Tests (WSP 97)

**File**: `test_video_mall_field_runtime.py` (extended)
**Tests**: 18 new | **Class**: `TestMallLocomotionAndGestures` | **Result**: 141 passed total
**Worker**: AP

Validates desktop drag-to-scroll, tap guard, and scroll edge shadows:

| Test | What it covers |
|------|----------------|
| test_drag_scroll_instance_variable | `dragScrollInstance` handler tracking |
| test_tap_guard_active_variable | `tapGuardActive` prevents drag→tap race |
| test_bind_drag_scroll_function | `bindDragScroll()` exists |
| test_bind_scroll_state_function | `bindScrollState()` for edge shadows |
| test_tap_guard_in_click_handler | Guard check in click handler |
| test_is_dragging_class_applied | `.is-dragging` added during drag |
| test_is_dragging_class_removed | `.is-dragging` removed after drag |
| test_tap_guard_cleared_with_delay | 100ms delay before clearing guard |
| test_wrapper_cursor_grab_css | `cursor: grab` affordance |
| test_is_dragging_cursor_grabbing_css | `cursor: grabbing` during drag |
| test_touch_action_pan_css | `touch-action: pan-x pan-y` clarity |
| test_scroll_edge_shadow_elements | `::before`/`::after` shadow elements |
| test_can_scroll_up_class | `.can-scroll-up` shadow visibility |
| test_can_scroll_down_class | `.can-scroll-down` shadow visibility |
| test_scroll_state_updated_on_scroll | Scroll event updates classes |
| test_drag_moved_threshold | 5px threshold before guard activates |
| test_interactive_elements_excluded_from_drag | Buttons excluded from drag |
| test_two_dimensional_scroll | X and Y scroll support |

---

## 2026-04-09 | Inline Preview AR Tests (WSP 97)

**File**: `test_video_mall_field_runtime.py` (extended)
**Tests**: +40 new, -4 removed | **Result**: 123 passed total
**Worker**: AR

Removed `TestTapPlayPause` (4 tests — asserted stale fullscreen-on-tap behavior).
Added 6 AR test classes:

| Class | Tests | Covers |
|-------|-------|--------|
| TestTapInlinePreviewAR | 12 | Preview lifecycle, generation guard, YouTube/HTML5 paths |
| TestPreviewControlsAR | 7 | Audio/expand buttons, public API exposure |
| TestInlinePreviewAudioStatesAR | 8 | 4 CSS states, SVG paths, innerHTML swap |
| TestPausedPreviewIndicatorAR | 4 | Paused state visibility, touch override |
| TestMediaFieldMappingAR | 5 | `embed_url`/`source_url` canonical fields, priority order |
| TestAudioButtonAccessibilityAR | 4 | `aria-label`/`title` update per mute state |

---

## 2026-04-08 | Expanded Video Field Animation Tests (WSP 97)

**File**: `test_video_mall_field_runtime.py` (extended)
**Tests**: 13 new | **Class**: `TestExpandCollapseAnimation` | **Result**: 82 passed total
**Worker**: AK

Validates FLIP animation for expand/collapse transitions:

| Test | What it covers |
|------|----------------|
| test_flip_layer_class_exists | `.mall-flip-layer` in CSS |
| test_flip_animating_transition_class | `.flip-animating` class in CSS and JS |
| test_flip_collapsing_transition_class | `.flip-collapsing` class in CSS and JS |
| test_geometry_transition_properties | left/top/width/height 280ms/250ms transitions |
| test_reduced_motion_bypass | `prefers-reduced-motion: reduce` media query |
| test_prefers_reduced_motion_function | `prefersReducedMotion()` helper |
| test_create_flip_layer_function | `createFlipLayer()` helper |
| test_cleanup_flip_layer_function | `cleanupFlipLayer()` helper |
| test_expand_source_index_tracked | `expandSourceIndex` state |
| test_expand_source_visual_stored | `expandSourceVisual` for collapse continuity |
| test_flip_layer_positioned_fixed | `position: fixed` on layer |
| test_animation_cleanup_happens | `cleanupFlipLayer(flipLayer)` called |
| test_will_change_optimization | `will-change:` GPU hint |

---

## 2026-04-03 | Shell Bridge Interceptor Tests (WSP 97)

**File**: `test_shell_bridge_interceptor.py`
**Tests**: 37 | **Classes**: 9 | **Result**: 37 passed
**Worker**: F

Validates postMessage interceptor per `EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md`:

| Class | Count | What it covers |
|-------|-------|----------------|
| TestInterceptorExists | 4 | File exists, IIFE wrapper, init function, message listener |
| TestMessageTypeHandling | 3 | agent_request type check, non-object rejection, handleMessage |
| TestRouteHandling | 4 | openclaw_search route, handlers object, dispatchRequest, unknown_route error |
| TestActionHandlers | 6 | semantic_search, wsp_lookup, unknown_action error, query/limit/protocol_number extraction |
| TestResponseFormat | 5 | agent_response type, status field, data field, results array, quantum_coherence |
| TestOriginValidation | 4 | Origin check, allowedOrigins list, same-origin allowed, disallowed rejected |
| TestStubMode | 4 | Stub indicator, setTimeout delay, shellBridgeBackend hookpoint |
| TestPublicAPI | 4 | window.shellBridgeInterceptor, addAllowedOrigin, setBackend, getConfig |
| TestHTMLIntegration | 3 | Included in index.html, foundup.html, loaded before concierge |

**Contract compliance**: Section 2.1 (semantic_search), 2.2 (wsp_lookup), 3.1 (response format)

---

## 2026-04-02 | Search Mall Concierge Wiring Phase 1 (WSP 97)

**File**: `test_search_mall_concierge_wiring_phase1.py`
**Tests**: 45 | **Classes**: 8 | **Result**: 45 passed
**Worker**: C

Validates concierge search surface wired to B's real field-scope API:

| Class | Count | What it covers |
|-------|-------|----------------|
| TestCreatorSearchPill | 4 | Pill exists, emits command, injects channels, opens search input |
| TestSearchMallButton | 3 | Button exists, emits command, opens search input |
| TestSearchInputWiring | 10 | Input calls searchByCreator, clears on empty, Escape, clear button |
| TestTypeofGuards | 2 | typeof guards on searchByCreator and clearFieldScope |
| TestPublicAPISearch | 8 | openSearchMall/searchByCreator/clearSearch on window.redDog |
| TestBSearchAPIExists | 5 | B's real APIs exist: searchByCreator/filterByCategory/Tag/clear/get |
| TestSearchCSS | 6 | Container, input 44px, clear 44px, placeholder styling |
| TestNoRegression | 7 | Personal Mall, channel attachment, AI tools, briefing, modes |

**Key design decisions**:
- Creator search pill and Search Mall button both open the same search input
- Search input calls `mallTileField.searchByCreator(query)` on every keystroke
- Clear resets input, hides container, and calls `mallTileField.clearFieldScope()`
- `setProjection('search')` is NOT used — confirmed not a valid projection value

---

## 2026-04-02 | Concierge Channel Attachment Phase 1 (WSP 97)

**File**: `test_concierge_channel_attachment_phase1.py`
**Tests**: 66 | **Classes**: 8 | **Result**: 66 passed
**Worker**: C

Validates channel/account attachment surface and Mall projection hooks:

| Class | Count | What it covers |
|-------|-------|----------------|
| TestChannelsModeAction | 6 | 'channels' mode in mode sheet, opens plane, injects section, scrolls |
| TestChannelListRendering | 13 | CHANNEL_PLATFORMS (4 types), catalog reader, row markup, video count |
| TestAttachDetachToggle | 6 | toggleChannelAttach, attach/detach commands, attached class, state |
| TestMallProjectionHooks | 9 | Populate/Personal/Search Mall buttons, commands, setProjection, typeof |
| TestRedDogAPIChannels | 6 | openChannels/getChannels/toggleChannel/populateMyMall/openPersonalMall/openSearchMall |
| TestChannelCSS | 10 | Section/row/icon/info/name/meta/toggle/actions classes, phone 44px |
| TestTruthfulHooks | 3 | No fake AI, no fetch, all commands use emitRedDogCommand |
| TestNoRegression | 13 | window.redDog, AI tools, briefing, recs, modes, CSS preserved |

**Key design decisions**:
- Channel data sourced from `window._mallVideoCatalog` (B's catalog)
- Attach/detach uses local state + `reddog:command` events (no backend)
- Mall projection hooks emit commands + call `setProjection()` with typeof guards
- All interactive elements 44px minimum on phone (WCAG)

---

## 2026-04-02 | Red Dog Mall Controls Phase 1 (WSP 97)

**File**: `test_reddog_mall_controls_phase1.py`
**Tests**: 81 | **Classes**: 9 | **Result**: 81 passed
**Worker**: C

Validates Red Dog AI tools controls for Mall projection:

| Class | Count | What it covers |
|-------|-------|----------------|
| TestAIToolsModeAction | 6 | 'tools' mode in mode sheet, opens plane, injects section |
| TestCategoryProjection | 13 | 6 categories, setCategory, typeof guards, default 'all' |
| TestCreatorEntityHook | 2 | Creator search button, command emission |
| TestDensityPresets | 10 | 4 presets (2x3/3x4/3x5/5x8), setDensity, API guard |
| TestMotionMode | 7 | Snap/Glide toggle, default snap, API guard, command event |
| TestTruthfulHooks | 9 | No fake AI, no fetch, CustomEvent dispatch, briefing state |
| TestRedDogAPIExtensions | 7 | openTools/set/getCategory/Density/MotionMode on window.redDog |
| TestAIToolsCSS | 10 | Pills, active state, mono font, 44px phone targets |
| TestNoRegression | 17 | All prior Red Dog behaviors preserved |

**Key design decisions**:
- All controls emit `reddog:command` CustomEvent for B to wire
- typeof guards on all `mallTileField` API calls
- No backend calls, no fake AI responses
- Briefing reflects current category/density/motion when non-default

---

## 2026-04-02 | Red Dog FoundUp Entry Alignment Phase 7

**File**: `test_reddog_foundup_entry_alignment_phase7.py`
**Tests**: 65 | **Classes**: 7 | **Result**: 65 passed
**Worker**: C

Validates entry-page Red Dog alignment with Mall Red Dog:

| Class | Count | What it covers |
|-------|-------|----------------|
| TestDigitalTwinIdentity | 4 | "Your digital twin" subtitle, logo, aria-label |
| TestEntryBriefing | 12 | Briefing container, 6 data fields, CSS, populate hook |
| TestEntryRecommendations | 16 | 4 local actions, pills, smooth scroll, clipboard, no backend |
| TestFABAlignment | 6 | State ring, active class, WCAG 44px, safe area, gradient |
| TestEntryRedDogAPI | 8 | window.entryRedDog: open/close/toggle/isOpen/getContext |
| TestConciergeTopicsUpdated | 4 | "Who is Red Dog?" digital-twin topic, 4 entry topics |
| TestNoRegression | 15 | Entry shell, Mall Red Dog, concierge.js all preserved |

---

## 2026-04-02 | Red Dog Mobile Ergonomics Phase 6

**File**: `test_reddog_mobile_ergonomics_phase6.py`
**Tests**: 43 | **Classes**: 5 | **Result**: 43 passed
**Worker**: C

| Class | Count | What it covers |
|-------|-------|----------------|
| TestAvatarTouchTarget | 4 | 44px WCAG minimum on avatar/trigger/img/placeholder |
| TestMobileSpacing | 10 | 480px query, safe-area, dvh, option/invite 44px targets |
| TestModeSheetPhone | 5 | Mode action 44px, sheet wider, briefing/rec phone styles |
| TestInteractionGrammar | 10 | Tap/double-tap/hold, pointer guards, swipe, escape, scrim |
| TestNoRegression | 14 | Briefing/recs/invites/options/mode sheet/desktop query |

---

## 2026-04-02 | Red Dog Recommended Actions Phase 5

**File**: `test_reddog_recommended_actions_phase5.py`
**Tests**: 63 | **Classes**: 6 | **Result**: 63 passed
**Worker**: C

---

## 2026-04-02 | Red Dog Context Briefing Phase 4

**File**: `test_reddog_context_briefing_phase4.py`
**Tests**: 48 | **Classes**: 6 | **Result**: 48 passed
**Worker**: C

---

## Suite Summary

| File | Tests | Worker | Phase |
|------|-------|--------|-------|
| test_video_mall_field_runtime.py | 100 | AK/AP | Animation + Locomotion |
| test_concierge_channel_attachment_phase1.py | 66 | C | Channel attachment |
| test_reddog_mall_controls_phase1.py | 81 | C | WSP 97 controls |
| test_reddog_foundup_entry_alignment_phase7.py | 65 | C | Entry alignment |
| test_reddog_mobile_ergonomics_phase6.py | 43 | C | Phone ergonomics |
| test_reddog_recommended_actions_phase5.py | 63 | C | Recommended actions |
| test_reddog_context_briefing_phase4.py | 48 | C | Context briefing |
| (other member tests) | ~446 | B/mixed | Mall shell, tiles, etc. |
| **Total** | **912** | | |
