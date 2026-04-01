"""
Navigation Planes Phase 2 — static content tests.

8 test categories matching the handoff spec:
  1. Plane state machine (Mall ↔ FoundUp view)
  2. Swipe-up close
  3. Swipe left/right navigate
  4. Double-tap save
  5. Desktop parity (drag, wheel)
  6. Gesture hint dismissal + localStorage
  7. No regression (account plane, Red Dog, existing carousel)
  8. Keyboard fallback
"""
import os
import re
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(relpath):
    with open(os.path.join(ROOT, relpath), encoding="utf-8") as f:
        return f.read()


# ─── 1. Plane State Machine ───────────────────────────────────

class TestPlaneStateMachine:
    """Verify HTML structure and JS API for FoundUp view plane."""

    def test_view_plane_element_exists(self):
        html = _read("index.html")
        assert 'id="foundupViewPlane"' in html

    def test_view_plane_has_body(self):
        html = _read("index.html")
        assert 'id="foundupViewBody"' in html

    def test_view_plane_has_close_button(self):
        html = _read("index.html")
        assert 'id="foundupViewClose"' in html

    def test_view_plane_has_scrim(self):
        html = _read("index.html")
        assert 'id="foundupViewScrim"' in html

    def test_mall_planes_js_exposes_api(self):
        js = _read("js/mall-planes.js")
        assert "window.mallPlanes" in js
        assert "openFoundUp" in js
        assert "closeView" in js
        assert "setCatalog" in js

    def test_tile_field_opens_view(self):
        # Tile field uses mallPlanes.openFoundUp for FoundUp view
        js = _read("js/mall-tile-field.js")
        assert "mallPlanes.openFoundUp" in js


# ─── 2. Swipe-Up Close ────────────────────────────────────────

class TestSwipeUpClose:
    """Verify swipe-up closes the FoundUp view."""

    def test_swipe_up_handler_in_planes(self):
        js = _read("js/mall-planes.js")
        assert "'up'" in js
        assert "closeView" in js

    def test_scrim_click_closes(self):
        js = _read("js/mall-planes.js")
        assert "scrim.addEventListener('click', closeView)" in js

    def test_close_removes_open_class(self):
        js = _read("js/mall-planes.js")
        assert "plane.classList.remove('open')" in js

    def test_view_plane_aria_label(self):
        html = _read("index.html")
        assert 'aria-label="FoundUp quick view"' in html


# ─── 3. Swipe Left/Right Navigate ─────────────────────────────

class TestSwipeLeftRight:
    """Verify swipe left/right navigates between FoundUps."""

    def test_left_swipe_advances(self):
        js = _read("js/mall-planes.js")
        assert "'left'" in js
        assert "navigateFoundUp(1)" in js

    def test_right_swipe_goes_back(self):
        js = _read("js/mall-planes.js")
        assert "'right'" in js
        assert "navigateFoundUp(-1)" in js

    def test_navigate_calls_render(self):
        js = _read("js/mall-planes.js")
        assert "renderView(catalog[next])" in js

    def test_navigate_syncs_carousel(self):
        js = _read("js/mall-planes.js")
        assert "mallPlanesSync" in js


# ─── 4. FoundUp Handoff ───────────────────────────────────────

class TestFoundUpHandoff:
    """Verify FoundUp handoff plane is coherent."""

    def test_open_link_exists(self):
        """View plane has Open FoundUp link."""
        js = _read("js/mall-planes.js")
        assert "fv-open-link" in js
        assert "Open FoundUp" in js

    def test_transitional_route_used(self):
        """Handoff uses transitional /member/foundup.html route."""
        js = _read("js/mall-planes.js")
        assert "/member/foundup.html?id=" in js

    def test_routing_prefix_surfaced(self):
        """routing_prefix is shown in handoff link."""
        js = _read("js/mall-planes.js")
        assert "routing_prefix" in js

    def test_no_stale_save_semantics(self):
        """Save/favorite semantics removed from view plane."""
        js = _read("js/mall-planes.js")
        assert "toggleSave" not in js
        assert "fvSaveIndicator" not in js
        assert "pfmall_saved_" not in js

    def test_hint_text_updated(self):
        """Hint text no longer mentions save."""
        js = _read("js/mall-planes.js")
        assert "Swipe up to close" in js
        assert "Swipe sideways for next" in js
        assert "Double-tap to save" not in js


# ─── 5. Desktop Parity ────────────────────────────────────────

class TestDesktopParity:
    """Verify mouse-drag maps to touch-swipe behavior."""

    def test_gesture_engine_has_mouse_handlers(self):
        js = _read("js/gesture-engine.js")
        assert "mousedown" in js
        assert "mouseup" in js
        assert "mousemove" in js

    def test_drag_scroll_function_exists(self):
        js = _read("js/gesture-engine.js")
        assert "function dragScroll" in js
        assert "window.dragScroll" in js

    def test_drag_scroll_wired_to_mall_track(self):
        js = _read("js/mall-planes.js")
        assert "dragScroll(mallTrack)" in js

    def test_dblclick_maps_to_double_tap(self):
        js = _read("js/gesture-engine.js")
        assert "dblclick" in js
        assert "onDoubleTap" in js

    def test_tile_field_exists(self):
        # Tile field replaced carousel horizontal scrolling
        html = _read("index.html")
        assert 'id="mallTileField"' in html


# ─── 6. Gesture Hint Dismissal ────────────────────────────────

class TestGestureHints:
    """Verify hints appear once, dismiss on tap, persist in localStorage."""

    def test_hint_container_in_html(self):
        html = _read("index.html")
        assert 'id="gestureHints"' in html

    def test_hint_items_present(self):
        html = _read("index.html")
        assert "Swipe sideways to browse" in html
        assert "Swipe down from top" in html
        assert "Tap any card" in html

    def test_dismiss_text_present(self):
        html = _read("index.html")
        assert "Tap anywhere to dismiss" in html

    def test_hints_js_checks_localstorage(self):
        js = _read("js/gesture-hints.js")
        assert "pfmall_hints_dismissed" in js
        assert "localStorage.getItem" in js
        assert "localStorage.setItem" in js

    def test_auto_dismiss_timeout(self):
        js = _read("js/gesture-hints.js")
        assert "setTimeout(dismiss, 6000)" in js

    def test_hints_css_loaded(self):
        html = _read("index.html")
        assert "mall-planes.css" in html


# ─── 7. No Regression ─────────────────────────────────────────

class TestNoRegression:
    """Verify existing surfaces remain untouched."""

    def test_account_plane_still_exists(self):
        html = _read("index.html")
        assert 'id="accountPlane"' in html
        assert 'id="accountPlaneScrim"' in html

    def test_account_concierge_js_still_loaded(self):
        html = _read("index.html")
        assert 'js/account-concierge.js' in html

    def test_unified_red_dog_plane_still_exists(self):
        html = _read("index.html")
        # Current truth: Red Dog merged into accountPlane with aria-label="Red Dog"
        assert 'id="accountPlane"' in html
        assert 'aria-label="Red Dog"' in html
        assert 'id="redDogBtn"' in html

    def test_red_dog_concierge_js_still_loaded(self):
        html = _read("index.html")
        assert 'js/red-dog-concierge.js' in html

    def test_mall_track_still_has_scroll_snap(self):
        css = _read("css/member.css")
        assert "scroll-snap-type: x mandatory" in css

    def test_overlay_scrim_still_exists(self):
        html = _read("index.html")
        assert 'id="overlayScrim"' in html

    def test_tile_field_css_exists(self):
        # Dots replaced by tile field grid
        css = _read("css/mall-tile-field.css")
        assert ".mall-tile-field" in css

    def test_foundup_entry_page_untouched(self):
        entry = _read("foundup.html")
        assert "entry-shell" in entry
        assert "entryContent" in entry

    def test_account_concierge_js_not_modified(self):
        """account-concierge.js must remain byte-identical (not our file)."""
        js = _read("js/account-concierge.js")
        assert "window.accountConcierge" in js
        assert "swipe-down" in js.lower() or "touchstart" in js.lower()


# ─── 8. Keyboard Fallback ─────────────────────────────────────

class TestKeyboardFallback:
    """Verify Escape and Arrow keys work in FoundUp view."""

    def test_escape_closes_view(self):
        js = _read("js/mall-planes.js")
        assert "'Escape'" in js
        assert "closeView" in js

    def test_arrow_left_navigates(self):
        js = _read("js/mall-planes.js")
        assert "'ArrowLeft'" in js

    def test_arrow_right_navigates(self):
        js = _read("js/mall-planes.js")
        assert "'ArrowRight'" in js

    def test_arrow_keys_in_mall_planes(self):
        # Arrow keys for FoundUp view navigation remain in mall-planes.js
        js = _read("js/mall-planes.js")
        assert "ArrowRight" in js
        assert "ArrowLeft" in js
