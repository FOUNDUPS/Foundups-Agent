"""
Video Mall Field Runtime Tests

Tests for the video-backed Mall field with:
  - Snapped field motion (default)
  - Glide mode override
  - Poster + queue count tiles
  - tap = lane autoplay (Shorts-style queue traversal)
  - pinch-out = expand into video field
  - pinch-in = collapse back
  - AI-controlled density presets
  - Enter FoundUp button for WSP 104 canonical routing
  - Lane autoplay with video end detection
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(relpath):
    with open(os.path.join(ROOT, relpath), encoding="utf-8") as f:
        return f.read()


class TestSnappedFieldMotion:
    """Test snapped field motion as default."""

    def test_scroll_snap_type_in_css(self):
        """Wrapper has scroll-snap-type for snapped motion."""
        css = _read("css/mall-tile-field.css")
        assert "scroll-snap-type: both mandatory" in css

    def test_tiles_have_snap_align(self):
        """Tiles have scroll-snap-align for snap targets."""
        css = _read("css/mall-tile-field.css")
        assert "scroll-snap-align: start" in css

    def test_wrapper_class_exists(self):
        """Wrapper class exists for scroll container."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-field-wrapper" in css


class TestGlideMode:
    """Test glide mode override."""

    def test_glide_class_removes_snap(self):
        """Glide mode class removes scroll-snap-type."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-field-wrapper.motion-glide" in css
        assert "scroll-snap-type: none" in css

    def test_set_motion_mode_api(self):
        """setMotionMode function exists in JS."""
        js = _read("js/mall-tile-field.js")
        assert "setMotionMode:" in js

    def test_get_motion_mode_api(self):
        """getMotionMode function exists in JS."""
        js = _read("js/mall-tile-field.js")
        assert "getMotionMode:" in js


class TestVideoBackedTiles:
    """Test poster and queue count on tiles."""

    def test_poster_url_as_background(self):
        """Tiles use poster_url as background-image."""
        js = _read("js/mall-tile-field.js")
        assert "poster_url" in js
        assert "background-image" in js

    def test_queue_count_badge(self):
        """Tiles show video queue count badge."""
        js = _read("js/mall-tile-field.js")
        assert "video_count" in js
        assert "mall-tile-queue-count" in js

    def test_queue_count_css_exists(self):
        """Queue count badge CSS exists."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-queue-count" in css

    def test_background_size_cover(self):
        """Tiles have background-size: cover for posters."""
        css = _read("css/mall-tile-field.css")
        assert "background-size: cover" in css


class TestEnterFoundUpButton:
    """Test Enter FoundUp button for WSP 104 canonical routing."""

    def test_enter_button_in_tile_html(self):
        """Enter FoundUp button included in tile HTML."""
        js = _read("js/mall-tile-field.js")
        assert "mall-tile-enter" in js
        assert "Enter FoundUp" in js

    def test_navigate_to_foundup_function(self):
        """navigateToFoundUp function exists for WSP 104 routing."""
        js = _read("js/mall-tile-field.js")
        assert "function navigateToFoundUp" in js

    def test_navigate_uses_stable_id(self):
        """Navigation uses foundup_id from data attribute, not index."""
        js = _read("js/mall-tile-field.js")
        assert "tile.dataset.foundupId" in js

    def test_navigate_to_canonical_route(self):
        """Navigation goes to /f/{foundup_id} canonical route."""
        js = _read("js/mall-tile-field.js")
        assert "'/f/' + encodeURIComponent(foundupId)" in js

    def test_enter_button_click_handler(self):
        """Enter button has click handler."""
        js = _read("js/mall-tile-field.js")
        assert ".mall-tile-enter" in js
        assert "navigateToFoundUp(foundupId)" in js

    def test_enter_button_css_exists(self):
        """Enter button has CSS styling."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-enter" in css

    def test_enter_button_visible_on_preview(self):
        """Enter button visible during preview."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile.is-previewing .mall-tile-enter" in css

    def test_fullscreen_has_enter_foundup_button(self):
        """Fullscreen video player has Enter FoundUp button."""
        js = _read("js/mall-video-player.js")
        assert 'data-action="enter"' in js
        assert "Enter FoundUp" in js

    def test_fullscreen_enter_action_handler(self):
        """Fullscreen Enter action navigates to /f/{foundup_id}."""
        js = _read("js/mall-video-player.js")
        assert "case 'enter':" in js
        assert "'/f/' + encodeURIComponent(currentFoundUpId)" in js

    def test_fullscreen_enter_button_css(self):
        """Fullscreen Enter button has distinct styling."""
        css = _read("css/mall-video-player.css")
        assert ".video-player-enter-btn" in css

    def test_expanded_mode_routes_to_parent(self):
        """In expanded mode, Enter FoundUp routes to parent FoundUp ID."""
        js = _read("js/mall-tile-field.js")
        # Check that expanded mode uses mallCatalog[expandedFoundUp] for ID
        idx = js.index("// In expanded mode, route to PARENT")
        section = js[idx:idx+300]
        assert "mallCatalog[expandedFoundUp]" in section
        assert "parentItem.foundup_id" in section


class TestPinchExpandCollapse:
    """Test pinch expand/collapse behavior."""

    def test_expand_foundup_function(self):
        """expandFoundUp function exists."""
        js = _read("js/mall-tile-field.js")
        assert "function expandFoundUp" in js

    def test_collapse_foundup_function(self):
        """collapseFoundUp function exists."""
        js = _read("js/mall-tile-field.js")
        assert "function collapseFoundUp" in js

    def test_expanded_foundup_state(self):
        """expandedFoundUp state variable exists."""
        js = _read("js/mall-tile-field.js")
        assert "expandedFoundUp" in js

    def test_expanded_mode_class(self):
        """expanded-mode class is applied to field."""
        js = _read("js/mall-tile-field.js")
        assert "expanded-mode" in js

    def test_collapse_hint_exists(self):
        """Collapse hint element is created."""
        js = _read("js/mall-tile-field.js")
        assert "mall-tile-field-collapse-hint" in js

    def test_pinch_handlers_wired(self):
        """Pinch handlers are wired via gestureZone."""
        js = _read("js/mall-tile-field.js")
        assert "onPinchOut" in js
        assert "onPinchIn" in js

    def test_get_expanded_videos(self):
        """getExpandedVideos function maps videos to tiles."""
        js = _read("js/mall-tile-field.js")
        assert "function getExpandedVideos" in js


class TestDensityPresets:
    """Test AI-controlled density presets."""

    def test_set_density_api(self):
        """setDensity function exists."""
        js = _read("js/mall-tile-field.js")
        assert "setDensity:" in js

    def test_get_density_api(self):
        """getDensity function exists."""
        js = _read("js/mall-tile-field.js")
        assert "getDensity:" in js

    def test_density_css_variables(self):
        """CSS variables for field columns exist."""
        css = _read("css/mall-tile-field.css")
        assert "--field-columns" in css

    def test_density_preset_classes(self):
        """Density preset data attributes exist in CSS."""
        css = _read("css/mall-tile-field.css")
        assert 'data-density="3x4"' in css
        assert 'data-density="3x5"' in css
        assert 'data-density="4x6"' in css
        assert 'data-density="5x8"' in css
        assert 'data-density="6x3"' in css


class TestAdaptiveDesktopLayout:
    """Test adaptive desktop 6x3 layout for wide viewports."""

    def test_6x3_preset_in_css(self):
        """6x3 desktop preset exists in CSS."""
        css = _read("css/mall-tile-field.css")
        assert 'data-density="6x3"' in css
        assert "--field-columns: 6" in css
        assert "--field-rows: 3" in css

    def test_6x3_in_valid_densities(self):
        """6x3 is in the validDensities array."""
        js = _read("js/mall-tile-field.js")
        assert "'6x3'" in js
        assert "validDensities" in js

    def test_detect_optimal_density_function(self):
        """detectOptimalDensity function exists for viewport detection."""
        js = _read("js/mall-tile-field.js")
        assert "function detectOptimalDensity" in js

    def test_auto_select_density_function(self):
        """autoSelectDensity function exists for automatic density selection."""
        js = _read("js/mall-tile-field.js")
        assert "function autoSelectDensity" in js

    def test_density_manually_set_tracking(self):
        """densityManuallySet variable tracks manual override."""
        js = _read("js/mall-tile-field.js")
        assert "densityManuallySet" in js

    def test_manual_override_preserved(self):
        """Manual override prevents auto-selection."""
        js = _read("js/mall-tile-field.js")
        assert "if (densityManuallySet) return" in js

    def test_resize_handler_bound(self):
        """Resize event listener bound for viewport changes."""
        js = _read("js/mall-tile-field.js")
        assert "addEventListener('resize'" in js or 'addEventListener("resize"' in js

    def test_handle_resize_function(self):
        """handleResize function exists."""
        js = _read("js/mall-tile-field.js")
        assert "function handleResize" in js

    def test_reset_density_override_api(self):
        """resetDensityOverride function exposed in API."""
        js = _read("js/mall-tile-field.js")
        assert "resetDensityOverride:" in js

    def test_auto_select_density_api(self):
        """autoSelectDensity function exposed in API."""
        js = _read("js/mall-tile-field.js")
        assert "autoSelectDensity:" in js

    def test_desktop_detection_uses_fine_pointer(self):
        """Desktop detection uses pointer: coarse media query."""
        js = _read("js/mall-tile-field.js")
        assert "pointer: coarse" in js

    def test_desktop_detection_uses_width_threshold(self):
        """Desktop detection uses width >= 1024px threshold."""
        js = _read("js/mall-tile-field.js")
        assert "1024" in js

    def test_desktop_detection_uses_landscape(self):
        """Desktop detection checks for landscape orientation."""
        js = _read("js/mall-tile-field.js")
        assert "isLandscape" in js

    def test_auto_select_called_on_init(self):
        """autoSelectDensity called during initialize."""
        js = _read("js/mall-tile-field.js")
        # Should call autoSelectDensity in initialize function
        assert "autoSelectDensity()" in js

    def test_mobile_default_preserved(self):
        """Mobile default is 3x5 when no viewport adaptation applies."""
        js = _read("js/mall-tile-field.js")
        # detectOptimalDensity returns '3x5' as default
        assert "return '3x5'" in js


class TestPortraitTileGeometry:
    """Test portrait-first 9:16 tile geometry."""

    def test_tiles_are_portrait_aspect(self):
        """Tiles use portrait 9:16 aspect ratio."""
        css = _read("css/mall-tile-field.css")
        assert "aspect-ratio: 9 / 16" in css

    def test_default_columns_is_three(self):
        """Default field layout is 3 columns for mobile-first dense wall."""
        css = _read("css/mall-tile-field.css")
        assert "--field-columns: 3" in css

    def test_tile_radius_is_minimal(self):
        """Default tile radius is small for low-chrome look."""
        css = _read("css/mall-tile-field.css")
        # Default value in .mall-tile should be 0.4rem or similar
        assert "border-radius: var(--tile-radius, 0.4rem)" in css

    def test_gap_is_tight(self):
        """Default gap is tight for dense wall feel."""
        css = _read("css/mall-tile-field.css")
        # Default gap should be 0.2rem or similar
        assert "gap: var(--tile-gap, 0.2rem)" in css

    def test_js_default_density_is_3x5(self):
        """JS default density is 3x5 for mobile-first."""
        js = _read("js/mall-tile-field.js")
        assert "currentDensity = '3x5'" in js


class TestGestureEnginePinch:
    """Test pinch detection in gesture engine."""

    def test_pinch_threshold(self):
        """PINCH_THRESHOLD constant exists."""
        js = _read("js/gesture-engine.js")
        assert "PINCH_THRESHOLD" in js

    def test_pinch_out_handler(self):
        """onPinchOut handler is supported."""
        js = _read("js/gesture-engine.js")
        assert "onPinchOut" in js

    def test_pinch_in_handler(self):
        """onPinchIn handler is supported."""
        js = _read("js/gesture-engine.js")
        assert "onPinchIn" in js

    def test_two_finger_touch_detection(self):
        """Two-finger touch is detected for pinch."""
        js = _read("js/gesture-engine.js")
        assert "e.touches.length === 2" in js

    def test_ctrl_wheel_pinch(self):
        """Ctrl+wheel triggers pinch on desktop."""
        js = _read("js/gesture-engine.js")
        assert "e.ctrlKey" in js
        assert "deltaY" in js


class TestPublicAPI:
    """Test public API surface."""

    def test_api_has_video_runtime_methods(self):
        """API exposes video runtime methods."""
        js = _read("js/mall-tile-field.js")
        assert "togglePlay:" in js
        assert "getPlayingIndex:" in js
        assert "expandFoundUp:" in js
        assert "collapseFoundUp:" in js
        assert "isExpanded:" in js
        assert "getExpandedIndex:" in js

    def test_api_has_motion_methods(self):
        """API exposes motion mode methods."""
        js = _read("js/mall-tile-field.js")
        assert "setMotionMode:" in js
        assert "getMotionMode:" in js

    def test_api_has_density_methods(self):
        """API exposes density methods."""
        js = _read("js/mall-tile-field.js")
        assert "setDensity:" in js
        assert "getDensity:" in js


class TestNoRegression:
    """Test no regression in existing functionality."""

    def test_projection_still_works(self):
        """Projection system still exists."""
        js = _read("js/mall-tile-field.js")
        assert "setProjection:" in js
        assert "getProjection:" in js
        assert "resetProjection:" in js

    def test_enter_foundup_still_works(self):
        """enterFoundUp function still exists."""
        js = _read("js/mall-tile-field.js")
        assert "enterFoundUp:" in js

    def test_mall_planes_integration(self):
        """mallPlanes.openFoundUp is still called."""
        js = _read("js/mall-tile-field.js")
        assert "window.mallPlanes.openFoundUp" in js


class TestFeelPolish:
    """Test phase 2 feel polish improvements."""

    def test_tap_pulse_animation(self):
        """Tap pulse class exists for immediate feedback."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile.tap-pulse" in css
        assert "tile-tap-pulse" in css

    def test_tap_pulse_applied_on_toggle(self):
        """togglePlay adds tap-pulse class for visual feedback."""
        js = _read("js/mall-tile-field.js")
        assert "tap-pulse" in js
        assert "classList.add('tap-pulse')" in js

    def test_scroll_behavior_smooth(self):
        """Wrapper has scroll-behavior: smooth for phone feel."""
        css = _read("css/mall-tile-field.css")
        assert "scroll-behavior: smooth" in css

    def test_density_adaptive_radius(self):
        """Tile radius scales with density."""
        css = _read("css/mall-tile-field.css")
        assert "--tile-radius" in css
        assert "border-radius: var(--tile-radius" in css

    def test_density_adaptive_gap(self):
        """Gap scales with density."""
        css = _read("css/mall-tile-field.css")
        assert "--tile-gap" in css
        assert "gap: var(--tile-gap" in css

    def test_transition_class_on_expand(self):
        """Transitioning class used for smooth expand."""
        js = _read("js/mall-tile-field.js")
        assert "transitioning" in js
        assert "classList.add('transitioning')" in js

    def test_collapse_hint_animation(self):
        """Collapse hint uses CSS class for animation."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-field-collapse-hint.visible" in css

    def test_play_indicator_snappy(self):
        """Play indicator has fast transition timing."""
        css = _read("css/mall-tile-field.css")
        # Should be 80ms or faster for snappy feel
        assert "80ms" in css or "transition: transform 80ms" in css

    def test_minimum_tile_size(self):
        """Tiles have minimum size for tap targets."""
        css = _read("css/mall-tile-field.css")
        assert "min-width: 3rem" in css
        assert "min-height: 3rem" in css


class TestPersonalMallProjection:
    """Test Personal Mall (My Mall) field scope projection."""

    def test_project_personal_mall_api(self):
        """projectPersonalMall function is exposed."""
        js = _read("js/mall-tile-field.js")
        assert "projectPersonalMall:" in js

    def test_clear_field_scope_api(self):
        """clearFieldScope function is exposed."""
        js = _read("js/mall-tile-field.js")
        assert "clearFieldScope:" in js

    def test_get_field_scope_api(self):
        """getFieldScope function is exposed."""
        js = _read("js/mall-tile-field.js")
        assert "getFieldScope:" in js

    def test_field_scope_state_variable(self):
        """currentFieldScope state variable exists."""
        js = _read("js/mall-tile-field.js")
        assert "currentFieldScope" in js

    def test_full_catalog_preserved(self):
        """fullCatalog preserves unscoped reference."""
        js = _read("js/mall-tile-field.js")
        assert "fullCatalog" in js

    def test_filter_by_scope_function(self):
        """filterByScope function exists."""
        js = _read("js/mall-tile-field.js")
        assert "function filterByScope" in js

    def test_personal_scope_filters_creator(self):
        """Personal scope filters by creator === '012'."""
        js = _read("js/mall-tile-field.js")
        assert "creator === '012'" in js

    def test_personal_scope_video_count_sort(self):
        """Personal scope sorts video_count > 0 first."""
        js = _read("js/mall-tile-field.js")
        assert "video_count" in js
        assert "aHasVideos" in js or "video_count || 0" in js

    def test_personal_scope_display_order_sort(self):
        """Personal scope sorts by display_order within groups."""
        js = _read("js/mall-tile-field.js")
        assert "display_order" in js

    def test_clear_scope_resets_to_full(self):
        """clearFieldScope resets to full catalog."""
        js = _read("js/mall-tile-field.js")
        assert "mallCatalog = fullCatalog.slice()" in js


class TestExpandCollapseAnimation:
    """Test FLIP animation for expand/collapse transitions."""

    def test_flip_layer_class_exists(self):
        """FLIP transition layer class exists in CSS."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-flip-layer" in css

    def test_flip_animating_transition_class(self):
        """Expanding uses flip-animating class with CSS transitions."""
        css = _read("css/mall-tile-field.css")
        assert ".flip-animating" in css
        js = _read("js/mall-tile-field.js")
        assert "flip-animating" in js

    def test_flip_collapsing_transition_class(self):
        """Collapsing uses flip-collapsing class with CSS transitions."""
        css = _read("css/mall-tile-field.css")
        assert ".flip-collapsing" in css
        js = _read("js/mall-tile-field.js")
        assert "flip-collapsing" in js

    def test_geometry_transition_properties(self):
        """FLIP layer transitions left, top, width, height."""
        css = _read("css/mall-tile-field.css")
        # Check that all geometry properties are transitioned
        assert "left 280ms" in css or "left 250ms" in css
        assert "top 280ms" in css or "top 250ms" in css
        assert "width 280ms" in css or "width 250ms" in css
        assert "height 280ms" in css or "height 250ms" in css

    def test_reduced_motion_bypass(self):
        """Reduced-motion media query bypasses animation."""
        css = _read("css/mall-tile-field.css")
        assert "prefers-reduced-motion: reduce" in css

    def test_prefers_reduced_motion_function(self):
        """prefersReducedMotion function exists in JS."""
        js = _read("js/mall-tile-field.js")
        assert "function prefersReducedMotion" in js

    def test_create_flip_layer_function(self):
        """createFlipLayer function exists in JS."""
        js = _read("js/mall-tile-field.js")
        assert "function createFlipLayer" in js

    def test_cleanup_flip_layer_function(self):
        """cleanupFlipLayer function exists in JS."""
        js = _read("js/mall-tile-field.js")
        assert "function cleanupFlipLayer" in js

    def test_expand_source_index_tracked(self):
        """Source index is tracked for collapse animation."""
        js = _read("js/mall-tile-field.js")
        assert "expandSourceIndex" in js

    def test_expand_source_visual_stored(self):
        """Source visual (bgImage, bgColor) stored for collapse continuity."""
        js = _read("js/mall-tile-field.js")
        assert "expandSourceVisual" in js
        assert "expandSourceVisual.bgImage" in js or "bgImage: bgImage" in js

    def test_flip_layer_positioned_fixed(self):
        """FLIP layer uses fixed positioning."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-flip-layer" in css
        # Position fixed for viewport-relative animation
        assert "position: fixed" in css

    def test_animation_cleanup_happens(self):
        """cleanupFlipLayer is called after animation."""
        js = _read("js/mall-tile-field.js")
        assert "cleanupFlipLayer(flipLayer)" in js

    def test_will_change_optimization(self):
        """FLIP layer has will-change for GPU acceleration."""
        css = _read("css/mall-tile-field.css")
        assert "will-change:" in css


class TestSearchMallProjection:
    """Test Search Mall field scope projections."""

    def test_set_field_scope_api(self):
        """setFieldScope function is exposed."""
        js = _read("js/mall-tile-field.js")
        assert "setFieldScope:" in js

    def test_search_by_creator_api(self):
        """searchByCreator function is exposed."""
        js = _read("js/mall-tile-field.js")
        assert "searchByCreator:" in js

    def test_filter_by_category_api(self):
        """filterByCategory function is exposed."""
        js = _read("js/mall-tile-field.js")
        assert "filterByCategory:" in js

    def test_filter_by_tag_api(self):
        """filterByTag function is exposed."""
        js = _read("js/mall-tile-field.js")
        assert "filterByTag:" in js

    def test_creator_scope_type(self):
        """Creator scope type exists in filterByScope."""
        js = _read("js/mall-tile-field.js")
        assert "scope.type === 'creator'" in js

    def test_category_scope_type(self):
        """Category scope type exists in filterByScope."""
        js = _read("js/mall-tile-field.js")
        assert "scope.type === 'category'" in js

    def test_tag_scope_type(self):
        """Tag scope type exists in filterByScope."""
        js = _read("js/mall-tile-field.js")
        assert "scope.type === 'tag'" in js

    def test_creator_search_case_insensitive(self):
        """Creator search is case-insensitive."""
        js = _read("js/mall-tile-field.js")
        assert "toLowerCase()" in js
        assert "indexOf(query)" in js

    def test_category_filter_exact_match(self):
        """Category filter uses exact match."""
        js = _read("js/mall-tile-field.js")
        assert "=== catQuery" in js

    def test_tag_filter_array_search(self):
        """Tag filter searches tags array."""
        js = _read("js/mall-tile-field.js")
        assert "item.tags" in js
        assert ".some(" in js

    def test_sort_scoped_results_function(self):
        """sortScopedResults function exists."""
        js = _read("js/mall-tile-field.js")
        assert "function sortScopedResults" in js

    def test_scope_options_object(self):
        """setFieldScope accepts options object with type and query."""
        js = _read("js/mall-tile-field.js")
        assert "options.type" in js
        assert "scope.query" in js


class TestTapInlinePreviewAR:
    """Test tap = inline preview play/pause behavior (AR slice)."""

    def test_start_inline_preview_function(self):
        """startInlinePreview function exists for inline playback."""
        js = _read("js/mall-tile-field.js")
        assert "function startInlinePreview" in js

    def test_pause_inline_preview_function(self):
        """pauseInlinePreview function exists."""
        js = _read("js/mall-tile-field.js")
        assert "function pauseInlinePreview" in js

    def test_resume_inline_preview_function(self):
        """resumeInlinePreview function exists."""
        js = _read("js/mall-tile-field.js")
        assert "function resumeInlinePreview" in js

    def test_stop_inline_preview_function(self):
        """stopInlinePreview function exists."""
        js = _read("js/mall-tile-field.js")
        assert "function stopInlinePreview" in js

    def test_one_active_preview_rule(self):
        """Starting a new preview stops the previous one (defensive cleanup)."""
        js = _read("js/mall-tile-field.js")
        # Defensive cleanup: always stop previous preview first
        assert "// Defensive cleanup: always stop previous preview first" in js
        assert "stopInlinePreview()" in js

    def test_toggle_play_starts_inline(self):
        """togglePlay calls startInlinePreview for new tile."""
        js = _read("js/mall-tile-field.js")
        assert "startInlinePreview(index, false)" in js

    def test_toggle_play_pauses_active(self):
        """togglePlay pauses active inline preview."""
        js = _read("js/mall-tile-field.js")
        assert "pauseInlinePreview()" in js
        assert "previewPaused" in js

    def test_toggle_play_resumes_paused(self):
        """togglePlay resumes a paused inline preview."""
        js = _read("js/mall-tile-field.js")
        assert "resumeInlinePreview()" in js

    def test_preview_generation_guard(self):
        """previewGeneration prevents stale async callbacks."""
        js = _read("js/mall-tile-field.js")
        assert "previewGeneration" in js
        assert "gen !== previewGeneration" in js

    def test_youtube_api_loader(self):
        """ensureYouTubeAPI function lazy-loads IFrame API."""
        js = _read("js/mall-tile-field.js")
        assert "function ensureYouTubeAPI" in js
        assert "iframe_api" in js

    def test_youtube_video_id_extractor(self):
        """extractYouTubeVideoId parses YouTube URLs."""
        js = _read("js/mall-tile-field.js")
        assert "function extractYouTubeVideoId" in js

    def test_html5_video_fallback(self):
        """HTML5 video element created for non-YouTube sources."""
        js = _read("js/mall-tile-field.js")
        assert "mall-tile-preview-media" in js
        assert "video.playsInline" in js


class TestPreviewControlsAR:
    """Test audio button and expand button for inline preview."""

    def test_audio_button_markup(self):
        """Audio button rendered with mall-tile-audio class."""
        js = _read("js/mall-tile-field.js")
        assert "mall-tile-audio" in js
        assert "Start muted preview" in js

    def test_audio_button_css(self):
        """Audio button CSS exists."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-audio" in css

    def test_toggle_preview_mute_function(self):
        """togglePreviewMute function handles audio toggle."""
        js = _read("js/mall-tile-field.js")
        assert "function togglePreviewMute" in js

    def test_expand_button_fullscreen_path(self):
        """Expand button calls openFullscreenFromTile."""
        js = _read("js/mall-tile-field.js")
        assert "openFullscreenFromTile(index)" in js

    def test_fullscreen_stops_preview(self):
        """openFullscreenFromTile stops inline preview first."""
        js = _read("js/mall-tile-field.js")
        assert "function openFullscreenFromTile" in js
        assert "stopInlinePreview();" in js

    def test_preview_container_markup(self):
        """Preview container and stage rendered for video tiles."""
        js = _read("js/mall-tile-field.js")
        assert "mall-tile-preview" in js
        assert "mall-tile-preview-stage" in js

    def test_public_api_exposes_preview(self):
        """Public API exposes inline preview methods."""
        js = _read("js/mall-tile-field.js")
        assert "startInlinePreview:" in js
        assert "stopInlinePreview:" in js
        assert "pauseInlinePreview:" in js
        assert "resumeInlinePreview:" in js
        assert "togglePreviewMute:" in js


class TestInlinePreviewAudioStatesAR:
    """Test audio button visual state clarity (AR slice)."""

    def test_audio_active_css(self):
        """Audio button has is-active state CSS."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-audio.is-active" in css

    def test_audio_unmuted_css(self):
        """Active unmuted state has distinct background."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-audio.is-active:not(.is-muted)" in css

    def test_audio_muted_css(self):
        """Active muted state has distinct background."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-audio.is-active.is-muted" in css

    def test_audio_paused_css(self):
        """Paused preview audio state has dimmed background."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile.is-paused .mall-tile-audio.is-active" in css

    def test_svg_muted_icon(self):
        """Muted SVG uses speaker body + X lines."""
        js = _read("js/mall-tile-field.js")
        assert 'x1="23" y1="9" x2="17" y2="15"' in js

    def test_svg_waves_icon(self):
        """Unmuted SVG uses speaker+waves path."""
        js = _read("js/mall-tile-field.js")
        assert "M15.54 8.46a5 5 0 010 7.07" in js

    def test_svg_body_path(self):
        """Speaker body path exists in SVG markup."""
        js = _read("js/mall-tile-field.js")
        assert "M11 5L6 9H2v6h4l5 4V5z" in js

    def test_audio_btn_innerHTML_updated(self):
        """Audio button innerHTML is updated on state change."""
        js = _read("js/mall-tile-field.js")
        assert "audioBtn.innerHTML" in js


class TestPausedPreviewIndicatorAR:
    """Test paused preview shows visible play indicator (AR slice)."""

    def test_paused_preview_visible_css(self):
        """Paused preview shows play indicator."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile.is-previewing.is-paused .mall-tile-play-indicator" in css

    def test_inline_preview_layer_css(self):
        """Inline preview layer CSS exists for in-grid playback."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-preview" in css
        assert ".mall-tile.is-previewing .mall-tile-preview" in css

    def test_preview_stage_css(self):
        """Preview stage CSS exists."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-preview-stage" in css

    def test_touch_devices_show_controls(self):
        """Touch devices always show audio and expand buttons."""
        css = _read("css/mall-tile-field.css")
        assert "hover: none" in css


class TestMediaFieldMappingAR:
    """Test inline preview reads canonical pfMALL video fields."""

    def test_embed_url_field(self):
        """startInlinePreview reads embed_url (schema-canonical)."""
        js = _read("js/mall-tile-field.js")
        assert "videoData.embed_url" in js

    def test_source_url_field(self):
        """startInlinePreview reads source_url (schema-canonical)."""
        js = _read("js/mall-tile-field.js")
        assert "videoData.source_url" in js

    def test_camelcase_fallbacks(self):
        """Camel-case aliases embedUrl/sourceUrl accepted."""
        js = _read("js/mall-tile-field.js")
        assert "videoData.embedUrl" in js
        assert "videoData.sourceUrl" in js

    def test_no_stale_url_field(self):
        """Old .url / .video_url fields are NOT used."""
        js = _read("js/mall-tile-field.js")
        # The media-field line should not contain videoData.url or videoData.video_url
        for line in js.splitlines():
            if "embed_url" in line and "source_url" in line:
                assert "videoData.url " not in line
                assert "videoData.video_url" not in line

    def test_field_priority_matches_player(self):
        """Field priority: embed_url > source_url (same as mall-video-player.js)."""
        js = _read("js/mall-tile-field.js")
        # embed_url must appear before source_url in the fallback chain
        idx_embed = js.index("videoData.embed_url")
        idx_source = js.index("videoData.source_url")
        assert idx_embed < idx_source


class TestAudioButtonAccessibilityAR:
    """Test audio button aria-label and title update by state."""

    def test_muted_label(self):
        """Muted state sets aria-label to 'Unmute preview'."""
        js = _read("js/mall-tile-field.js")
        assert "Unmute preview" in js

    def test_unmuted_label(self):
        """Unmuted state sets aria-label to 'Mute preview'."""
        js = _read("js/mall-tile-field.js")
        assert "Mute preview" in js

    def test_aria_label_updated(self):
        """aria-label is set via setAttribute in applyTilePreviewState."""
        js = _read("js/mall-tile-field.js")
        assert "setAttribute('aria-label'" in js

    def test_title_updated(self):
        """title property updated alongside aria-label."""
        js = _read("js/mall-tile-field.js")
        assert "audioBtn.title = " in js

    def test_initial_label_matches_inactive_action(self):
        """Inactive audio button says 'Start muted preview', not 'Toggle audio'."""
        js = _read("js/mall-tile-field.js")
        assert 'aria-label="Start muted preview"' in js
        assert 'title="Start muted preview"' in js
        assert 'aria-label="Toggle audio"' not in js

    def test_three_label_states(self):
        """Three distinct label states: initial, muted-active, unmuted-active."""
        js = _read("js/mall-tile-field.js")
        assert "Start muted preview" in js
        assert "Unmute preview" in js
        assert "Mute preview" in js


class TestTouchModePaddingAR:
    """Test touch-mode video tiles get control padding even when inactive."""

    def test_touch_has_selector_padding(self):
        """Touch media query adds padding for tiles with audio button via :has()."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile:has(.mall-tile-audio) .mall-tile-inner" in css

    def test_touch_padding_inside_hover_none(self):
        """The :has() padding rule is inside the (hover: none) media query."""
        css = _read("css/mall-tile-field.css")
        # Find the hover:none block and confirm it contains the :has rule
        in_hover_none = False
        found = False
        for line in css.splitlines():
            if "hover: none" in line:
                in_hover_none = True
            if in_hover_none and ".mall-tile:has(.mall-tile-audio)" in line:
                found = True
                break
        assert found, ":has(.mall-tile-audio) padding must be inside @media (hover: none)"

    def test_touch_padding_value(self):
        """Touch padding matches the has-video-controls padding (1.5rem for low-chrome)."""
        css = _read("css/mall-tile-field.css")
        # Both rules should use 1.5rem for low-chrome portrait layout
        lines_with_padding = [l for l in css.splitlines() if "padding-top: 1.5rem" in l]
        assert len(lines_with_padding) >= 2, "Expected 1.5rem padding in both .has-video-controls and :has(.mall-tile-audio) rules"


class TestMallLocomotionAndGestures:
    """Test mall locomotion (desktop drag, touch) and gesture conflict prevention."""

    def test_drag_scroll_instance_variable(self):
        """dragScrollInstance tracks the drag-to-scroll handler."""
        js = _read("js/mall-tile-field.js")
        assert "dragScrollInstance" in js

    def test_tap_guard_active_variable(self):
        """tapGuardActive prevents accidental taps during/after drag."""
        js = _read("js/mall-tile-field.js")
        assert "tapGuardActive" in js

    def test_bind_drag_scroll_function(self):
        """bindDragScroll function exists."""
        js = _read("js/mall-tile-field.js")
        assert "function bindDragScroll" in js

    def test_bind_scroll_state_function(self):
        """bindScrollState function exists for edge shadow tracking."""
        js = _read("js/mall-tile-field.js")
        assert "function bindScrollState" in js

    def test_tap_guard_in_click_handler(self):
        """Click handler checks tapGuardActive before processing."""
        js = _read("js/mall-tile-field.js")
        assert "if (tapGuardActive) return" in js

    def test_is_dragging_class_applied(self):
        """is-dragging class added during drag."""
        js = _read("js/mall-tile-field.js")
        assert "classList.add('is-dragging')" in js

    def test_is_dragging_class_removed(self):
        """is-dragging class removed after drag ends."""
        js = _read("js/mall-tile-field.js")
        assert "classList.remove('is-dragging')" in js

    def test_tap_guard_cleared_with_delay(self):
        """Tap guard is cleared after brief delay to prevent race."""
        js = _read("js/mall-tile-field.js")
        assert "setTimeout" in js
        assert "tapGuardActive = false" in js

    def test_wrapper_cursor_grab_css(self):
        """Wrapper has cursor: grab for drag affordance."""
        css = _read("css/mall-tile-field.css")
        assert "cursor: grab" in css

    def test_is_dragging_cursor_grabbing_css(self):
        """is-dragging state has cursor: grabbing."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-field-wrapper.is-dragging" in css
        assert "cursor: grabbing" in css

    def test_touch_action_pan_css(self):
        """touch-action set for clear pan gesture."""
        css = _read("css/mall-tile-field.css")
        assert "touch-action: pan-x pan-y" in css

    def test_scroll_edge_shadow_elements(self):
        """Wrapper has pseudo-elements for scroll edge shadows."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-field-wrapper::before" in css
        assert ".mall-tile-field-wrapper::after" in css

    def test_can_scroll_up_class(self):
        """can-scroll-up class controls top shadow visibility."""
        css = _read("css/mall-tile-field.css")
        assert ".can-scroll-up" in css

    def test_can_scroll_down_class(self):
        """can-scroll-down class controls bottom shadow visibility."""
        css = _read("css/mall-tile-field.css")
        assert ".can-scroll-down" in css

    def test_scroll_state_updated_on_scroll(self):
        """Scroll event listener updates scroll state classes."""
        js = _read("js/mall-tile-field.js")
        assert "updateScrollState" in js
        assert "addEventListener('scroll'" in js

    def test_drag_moved_threshold(self):
        """Drag requires movement threshold before activating guard."""
        js = _read("js/mall-tile-field.js")
        assert "Math.abs(dx) > 5" in js or "Math.abs(dy) > 5" in js

    def test_interactive_elements_excluded_from_drag(self):
        """Drag ignores clicks on buttons and interactive elements."""
        js = _read("js/mall-tile-field.js")
        assert "e.target.closest('button, a, [tabindex]')" in js

    def test_two_dimensional_scroll(self):
        """Drag scroll works in both X and Y directions."""
        js = _read("js/mall-tile-field.js")
        assert "scrollStartX" in js
        assert "scrollStartY" in js
        assert "scrollLeft" in js
        assert "scrollTop" in js


class TestPreviewResourceHardening:
    """Test inline preview resource hardening (BD slice)."""

    def test_stale_callback_guard_increment_first(self):
        """stopInlinePreview increments generation FIRST to invalidate callbacks."""
        js = _read("js/mall-tile-field.js")
        assert "// Increment generation FIRST" in js
        assert "previewGeneration++" in js

    def test_html5_video_load_called(self):
        """HTML5 video.load() called to release media buffers."""
        js = _read("js/mall-tile-field.js")
        assert "inlineHTML5Video.load()" in js

    def test_html5_video_removed_from_dom(self):
        """HTML5 video removed from DOM on teardown."""
        js = _read("js/mall-tile-field.js")
        assert "inlineHTML5Video.parentNode.removeChild(inlineHTML5Video)" in js

    def test_html5_video_onerror_cleared(self):
        """HTML5 video onerror handler cleared on teardown."""
        js = _read("js/mall-tile-field.js")
        assert "inlineHTML5Video.onerror = null" in js

    def test_visibility_handler_bound(self):
        """bindVisibilityHandler exists and is called on init."""
        js = _read("js/mall-tile-field.js")
        assert "function bindVisibilityHandler" in js
        assert "bindVisibilityHandler()" in js

    def test_visibility_change_pauses_preview(self):
        """visibilitychange pauses preview when page is hidden."""
        js = _read("js/mall-tile-field.js")
        assert "document.addEventListener('visibilitychange'" in js
        assert "document.hidden" in js
        assert "pauseInlinePreview()" in js

    def test_invalid_url_failsafe(self):
        """startInlinePreview validates URL before attempting preview."""
        js = _read("js/mall-tile-field.js")
        assert "videoUrl.length < 5" in js

    def test_youtube_error_callback_guarded(self):
        """YouTube player onError callback checks generation."""
        js = _read("js/mall-tile-field.js")
        assert "onError: function(event)" in js

    def test_html5_video_error_handler(self):
        """HTML5 video has onerror handler that fails quietly."""
        js = _read("js/mall-tile-field.js")
        assert "video.onerror = function()" in js

    def test_fullscreen_handoff_cleanup(self):
        """openFullscreenFromTile stops inline preview first."""
        js = _read("js/mall-tile-field.js")
        assert "function openFullscreenFromTile" in js
        idx_func = js.index("function openFullscreenFromTile")
        idx_stop = js.index("stopInlinePreview();", idx_func)
        assert idx_stop - idx_func < 100

    def test_expand_cleanup(self):
        """expandFoundUp stops inline preview first."""
        js = _read("js/mall-tile-field.js")
        idx_func = js.index("function expandFoundUp")
        idx_stop = js.index("stopInlinePreview();", idx_func)
        assert idx_stop - idx_func < 200

    def test_collapse_cleanup(self):
        """collapseFoundUp stops inline preview first."""
        js = _read("js/mall-tile-field.js")
        idx_func = js.index("function collapseFoundUp")
        idx_stop = js.index("stopInlinePreview();", idx_func)
        assert idx_stop - idx_func < 200

    def test_visibility_bound_guard(self):
        """Visibility handler has guard against double-binding."""
        js = _read("js/mall-tile-field.js")
        assert "visibilityBound" in js
        assert "if (visibilityBound) return" in js


class TestLaneAutoplay:
    """Test Shorts-style lane autoplay through videos[] queue."""

    def test_lane_video_index_state(self):
        """Lane video index state variable exists."""
        js = _read("js/mall-tile-field.js")
        assert "laneVideoIndex" in js

    def test_current_lane_foundup_index_state(self):
        """Current lane FoundUp index state variable exists."""
        js = _read("js/mall-tile-field.js")
        assert "currentLaneFoundupIndex" in js

    def test_lane_autoplay_enabled_flag(self):
        """Lane autoplay enabled flag exists."""
        js = _read("js/mall-tile-field.js")
        assert "laneAutoplayEnabled" in js

    def test_start_lane_preview_function(self):
        """startLanePreview function exists for lane autoplay."""
        js = _read("js/mall-tile-field.js")
        assert "function startLanePreview" in js

    def test_advance_to_next_in_lane_function(self):
        """advanceToNextInLane function exists for queue traversal."""
        js = _read("js/mall-tile-field.js")
        assert "function advanceToNextInLane" in js

    def test_loop_policy_on_queue_end(self):
        """Lane autoplay loops to start when queue ends."""
        js = _read("js/mall-tile-field.js")
        # Check for loop policy comment and implementation
        assert "Loop policy" in js or "loop to start" in js
        assert "nextIndex = 0" in js

    def test_youtube_onstate_change_handler(self):
        """YouTube player has onStateChange for end detection."""
        js = _read("js/mall-tile-field.js")
        assert "onStateChange" in js
        assert "event.data === 0" in js  # YT.PlayerState.ENDED

    def test_html5_ended_event_handler(self):
        """HTML5 video has ended event for lane advancement."""
        js = _read("js/mall-tile-field.js")
        assert "'ended'" in js
        assert "advanceToNextInLane()" in js

    def test_toggle_play_uses_lane_preview(self):
        """togglePlay uses startLanePreview in Mall mode."""
        js = _read("js/mall-tile-field.js")
        assert "startLanePreview(index, 0, false)" in js

    def test_stop_preview_resets_lane_state(self):
        """stopInlinePreview resets lane state."""
        js = _read("js/mall-tile-field.js")
        idx = js.index("function stopInlinePreview")
        section = js[idx:idx+1200]
        assert "currentLaneFoundupIndex = null" in section
        assert "laneVideoIndex = 0" in section

    def test_lane_state_survives_preview_startup(self):
        """Lane state is set AFTER stopInlinePreview in startLanePreview."""
        js = _read("js/mall-tile-field.js")
        idx = js.index("function startLanePreview")
        section = js[idx:idx+600]
        # stopInlinePreview must come BEFORE setting lane state
        stop_idx = section.index("stopInlinePreview()")
        lane_idx = section.index("currentLaneFoundupIndex = foundupIndex")
        assert stop_idx < lane_idx, "stopInlinePreview must precede lane state assignment"

    def test_lane_api_exposed(self):
        """Lane autoplay API exposed on window.mallTileField."""
        js = _read("js/mall-tile-field.js")
        assert "startLanePreview:" in js
        assert "advanceToNextInLane:" in js
        assert "getLaneVideoIndex:" in js

    def test_no_double_tap_entry(self):
        """Tap handler does not call enterFoundUp on double-tap."""
        js = _read("js/mall-tile-field.js")
        # The click handler should NOT have double-tap logic calling enterFoundUp
        idx = js.index("tile.addEventListener('click'")
        handler_end = js.index("});", idx)
        click_handler = js[idx:handler_end]
        assert "enterFoundUp(index)" not in click_handler

    def test_keyboard_enter_opens_fullscreen(self):
        """Keyboard Enter opens fullscreen (not enterFoundUp)."""
        js = _read("js/mall-tile-field.js")
        # Find the keydown handler
        idx = js.index("e.key === 'Enter'")
        section = js[idx:idx+200]
        assert "openFullscreenFromTile(index)" in section
