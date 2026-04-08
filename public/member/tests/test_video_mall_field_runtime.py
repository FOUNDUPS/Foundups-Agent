"""
Video Mall Field Runtime Tests

Tests for the video-backed Mall field with:
  - Snapped field motion (default)
  - Glide mode override
  - Poster + queue count tiles
  - tap = inline preview play/pause
  - speaker toggle = mute/unmute inline preview
  - expand button = fullscreen player
  - double-tap = enter FoundUp
  - pinch-out = expand into video field
  - pinch-in = collapse back
  - AI-controlled density presets
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


class TestTapInlinePreview:
    """Test tap = inline preview behavior."""

    def test_toggle_play_function(self):
        """togglePlay function exists."""
        js = _read("js/mall-tile-field.js")
        assert "function togglePlay" in js

    def test_playing_index_tracked(self):
        """Playing index is tracked for the active preview tile."""
        js = _read("js/mall-tile-field.js")
        assert "playingIndex" in js

    def test_toggle_play_starts_inline_preview(self):
        """togglePlay starts inline preview for a new tile."""
        js = _read("js/mall-tile-field.js")
        assert "startInlinePreview(index, false)" in js

    def test_toggle_play_pauses_active_preview(self):
        """togglePlay pauses an active inline preview."""
        js = _read("js/mall-tile-field.js")
        assert "pauseInlinePreview()" in js
        assert "previewPaused" in js

    def test_toggle_play_resumes_paused_preview(self):
        """togglePlay resumes a paused inline preview."""
        js = _read("js/mall-tile-field.js")
        assert "resumeInlinePreview()" in js

    def test_play_indicator_css(self):
        """Play indicator CSS exists."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-play-indicator" in css

    def test_only_one_preview_active_at_a_time(self):
        """Starting a new preview stops the previous active preview."""
        js = _read("js/mall-tile-field.js")
        assert "playingIndex !== null && playingIndex !== index" in js
        assert "stopInlinePreview()" in js


class TestPreviewControls:
    """Test explicit tile controls for preview/fullscreen."""

    def test_audio_button_markup_exists(self):
        """Tiles render a speaker/mute control."""
        js = _read("js/mall-tile-field.js")
        assert "mall-tile-audio" in js
        assert "Start muted preview" in js

    def test_audio_button_css_exists(self):
        """Speaker button CSS exists."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-audio" in css

    def test_audio_button_toggle_handler_exists(self):
        """Audio button toggles preview mute state."""
        js = _read("js/mall-tile-field.js")
        assert "togglePreviewMute(index)" in js
        assert "setPreviewMutedState(!previewMuted)" in js

    def test_expand_button_keeps_fullscreen_path(self):
        """Expand button still opens the fullscreen player explicitly."""
        js = _read("js/mall-tile-field.js")
        assert "mall-tile-expand" in js
        assert "openFullscreenFromTile(index)" in js

    def test_open_fullscreen_stops_inline_preview(self):
        """Fullscreen handoff stops any active inline preview first."""
        js = _read("js/mall-tile-field.js")
        assert "function openFullscreenFromTile" in js
        assert "stopInlinePreview();" in js


class TestDoubleTapEnter:
    """Test double-tap = enter FoundUp."""

    def test_double_tap_window(self):
        """Double-tap detection window exists."""
        js = _read("js/mall-tile-field.js")
        assert "DOUBLE_TAP_WINDOW" in js

    def test_enter_foundup_on_double_tap(self):
        """Double-tap calls enterFoundUp."""
        js = _read("js/mall-tile-field.js")
        assert "enterFoundUp(index)" in js


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
        assert 'data-density="2x3"' in css
        assert 'data-density="3x4"' in css
        assert 'data-density="3x5"' in css
        assert 'data-density="5x8"' in css


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

    def test_inline_preview_layer_exists(self):
        """Inline preview layer CSS exists for in-grid playback."""
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-preview" in css
        assert ".mall-tile.is-previewing .mall-tile-preview" in css


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
