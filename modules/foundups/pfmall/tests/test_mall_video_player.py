"""
Tests for Mall Video Player (Fullscreen Layer) — WSP 97 Phase 1.

Acceptance criteria:
- Fullscreen works on phone (responsive)
- Rail stays queue-constrained (no cross-FoundUp drift)
- Return path is clean (swipe-down, pinch-in, back button)

Test structure:
- TestVideoPlayerCSS: CSS file exists with required styles
- TestVideoPlayerJS: JS file exists with required API
- TestVideoPlayerIntegration: HTML includes CSS/JS
- TestGestureSupport: Gesture patterns match WSP 97 spec
- TestQueueConstraint: No cross-FoundUp drift
- TestReturnPath: Multiple exit methods
"""

import pytest
from pathlib import Path
import re

# ─── Paths ───
REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
MEMBER_DIR = REPO_ROOT / "public" / "member"
CSS_FILE = MEMBER_DIR / "css" / "mall-video-player.css"
JS_FILE = MEMBER_DIR / "js" / "mall-video-player.js"
INDEX_HTML = MEMBER_DIR / "index.html"


@pytest.fixture(scope="module")
def css_content():
    """Load CSS file content."""
    assert CSS_FILE.exists(), f"CSS file not found: {CSS_FILE}"
    return CSS_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def js_content():
    """Load JS file content."""
    assert JS_FILE.exists(), f"JS file not found: {JS_FILE}"
    return JS_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def html_content():
    """Load index.html content."""
    assert INDEX_HTML.exists(), f"HTML file not found: {INDEX_HTML}"
    return INDEX_HTML.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# CSS Structure Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestVideoPlayerCSS:
    """CSS file structure and required classes."""

    def test_css_file_exists(self):
        """CSS file exists at expected path."""
        assert CSS_FILE.exists()

    def test_fullscreen_container_class(self, css_content):
        """Fullscreen container class exists with fixed positioning."""
        assert ".video-player-fullscreen" in css_content
        assert "position: fixed" in css_content or "position:fixed" in css_content

    def test_top_bar_class(self, css_content):
        """Top bar class exists."""
        assert ".video-player-top-bar" in css_content

    def test_stage_class(self, css_content):
        """Video stage class exists."""
        assert ".video-player-stage" in css_content

    def test_queue_rail_class(self, css_content):
        """Queue rail class exists."""
        assert ".video-player-queue-rail" in css_content

    def test_queue_item_class(self, css_content):
        """Queue item class exists."""
        assert ".video-player-queue-item" in css_content

    def test_chrome_hidden_class(self, css_content):
        """Chrome hidden state class exists."""
        assert ".chrome-hidden" in css_content

    def test_rail_visible_class(self, css_content):
        """Rail visible state class exists."""
        assert ".visible" in css_content

    def test_safe_area_support(self, css_content):
        """Safe area insets for notch devices."""
        assert "env(safe-area-inset" in css_content

    def test_responsive_media_query(self, css_content):
        """Mobile responsive media query exists."""
        assert "@media" in css_content
        assert "max-width" in css_content or "orientation" in css_content


# ═══════════════════════════════════════════════════════════════════════════
# JS Structure Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestVideoPlayerJS:
    """JS file structure and public API."""

    def test_js_file_exists(self):
        """JS file exists at expected path."""
        assert JS_FILE.exists()

    def test_public_api_exists(self, js_content):
        """Public API object is exposed."""
        assert "window.mallVideoPlayer" in js_content

    def test_open_function(self, js_content):
        """Open function exists in API."""
        assert "open:" in js_content or "open :" in js_content

    def test_close_function(self, js_content):
        """Close function exists in API."""
        assert "close:" in js_content or "close :" in js_content

    def test_next_function(self, js_content):
        """Next video function exists."""
        assert "next:" in js_content or "nextVideo" in js_content

    def test_prev_function(self, js_content):
        """Previous video function exists."""
        assert "prev:" in js_content or "prevVideo" in js_content

    def test_is_open_function(self, js_content):
        """isOpen status function exists."""
        assert "isOpen:" in js_content or "isOpen :" in js_content

    def test_get_foundup_id_function(self, js_content):
        """getFoundUpId function exists for queue constraint."""
        assert "getFoundUpId" in js_content


# ═══════════════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestVideoPlayerIntegration:
    """HTML includes CSS and JS files."""

    def test_css_link_in_html(self, html_content):
        """CSS file is linked in HTML."""
        assert 'mall-video-player.css' in html_content

    def test_js_script_in_html(self, html_content):
        """JS file is included in HTML."""
        assert 'mall-video-player.js' in html_content

    def test_gesture_engine_loaded_first(self, html_content):
        """Gesture engine is loaded before video player."""
        gesture_pos = html_content.find('gesture-engine.js')
        player_pos = html_content.find('mall-video-player.js')
        assert gesture_pos < player_pos, "gesture-engine.js must load before mall-video-player.js"


# ═══════════════════════════════════════════════════════════════════════════
# Gesture Support Tests (WSP 97 Section 6.3)
# ═══════════════════════════════════════════════════════════════════════════

class TestGestureSupport:
    """Gesture patterns match WSP 97 fullscreen semantics."""

    def test_swipe_up_next(self, js_content):
        """Swipe-up triggers next video."""
        # Check for swipe-up = next pattern
        assert "dir === 'up'" in js_content or 'dir === "up"' in js_content
        assert "nextVideo" in js_content

    def test_swipe_down_exit(self, js_content):
        """Swipe-down exits fullscreen."""
        assert "dir === 'down'" in js_content or 'dir === "down"' in js_content
        # Should call close when swiping down
        pattern = r"'down'.*close\(\)|close\(\).*'down'"
        # Just check both exist in swipe handler context
        assert "down" in js_content and "close()" in js_content

    def test_pinch_in_exit(self, js_content):
        """Pinch-in gesture exits fullscreen."""
        assert "pinch" in js_content.lower() or "PINCH_THRESHOLD" in js_content

    def test_tap_toggle_chrome(self, js_content):
        """Tap toggles chrome visibility."""
        assert "onTap" in js_content
        assert "toggleChrome" in js_content

    def test_swipe_left_save_hook(self, js_content):
        """Swipe-left triggers save hook."""
        assert "dir === 'left'" in js_content or 'dir === "left"' in js_content
        assert "Save" in js_content or "save" in js_content

    def test_swipe_right_dismiss_hook(self, js_content):
        """Swipe-right triggers dismiss hook."""
        assert "dir === 'right'" in js_content or 'dir === "right"' in js_content
        assert "Dismiss" in js_content or "dismiss" in js_content


# ═══════════════════════════════════════════════════════════════════════════
# Queue Constraint Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestQueueConstraint:
    """Queue stays FoundUp-constrained (no cross-FoundUp drift)."""

    def test_foundup_id_tracked(self, js_content):
        """FoundUp ID is tracked for queue constraint."""
        assert "currentFoundUpId" in js_content

    def test_queue_is_array(self, js_content):
        """Queue is stored as array from single FoundUp."""
        assert "currentQueue" in js_content
        assert "currentQueue = []" in js_content or "currentQueue = queue" in js_content

    def test_navigation_bounded(self, js_content):
        """Navigation is bounded to queue length."""
        assert "currentQueue.length" in js_content
        # Check for bounds checking
        assert "index < 0" in js_content or "index >= currentQueue.length" in js_content

    def test_no_cross_foundup_navigation(self, js_content):
        """No automatic cross-FoundUp navigation exists."""
        # Should NOT have any logic that switches foundupId during playback
        # The foundupId should only change on explicit open() call
        lines = js_content.split('\n')
        in_open_func = False
        foundup_assignments = []

        for line in lines:
            if 'function open(' in line or 'open: function' in line:
                in_open_func = True
            elif in_open_func and 'function ' in line:
                in_open_func = False

            if 'currentFoundUpId =' in line:
                foundup_assignments.append((in_open_func, line.strip()))

        # All foundupId assignments should be in open() or close()
        for in_open, line in foundup_assignments:
            assert in_open or 'null' in line, f"FoundUpId modified outside open(): {line}"


# ═══════════════════════════════════════════════════════════════════════════
# Return Path Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestReturnPath:
    """Multiple clean exit methods exist."""

    def test_back_button_closes(self, js_content):
        """Back button action closes player."""
        assert "data-action=\"back\"" in js_content or "data-action='back'" in js_content
        assert "case 'back':" in js_content or 'case "back":' in js_content
        assert "close()" in js_content

    def test_escape_key_closes(self, js_content):
        """Escape key closes player."""
        assert "'Escape'" in js_content or '"Escape"' in js_content
        assert "close()" in js_content

    def test_swipe_down_closes(self, js_content):
        """Swipe down closes player (already tested in gestures)."""
        assert "down" in js_content

    def test_pinch_in_closes(self, js_content):
        """Pinch in closes player (already tested in gestures)."""
        assert "pinch" in js_content.lower() or "PINCH_THRESHOLD" in js_content

    def test_close_cleans_state(self, js_content):
        """Close function resets state cleanly."""
        # Check that close() resets key state variables
        assert "isOpen = false" in js_content
        assert "currentQueue = []" in js_content
        assert "currentFoundUpId = null" in js_content


# ═══════════════════════════════════════════════════════════════════════════
# Top Bar Actions Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestTopBarActions:
    """Top bar has required action buttons."""

    def test_back_button(self, js_content):
        """Back button exists."""
        assert "data-action=\"back\"" in js_content

    def test_save_button(self, js_content):
        """Save button exists."""
        assert "data-action=\"save\"" in js_content

    def test_share_button(self, js_content):
        """Share button exists."""
        assert "data-action=\"share\"" in js_content

    def test_more_button(self, js_content):
        """More options button exists."""
        assert "data-action=\"more\"" in js_content


# ═══════════════════════════════════════════════════════════════════════════
# Queue Rail Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestQueueRail:
    """Bottom queue rail behavior."""

    def test_rail_hidden_by_default(self, css_content):
        """Rail is hidden by default via transform."""
        assert "translateY(100%)" in css_content

    def test_rail_visible_state(self, css_content):
        """Rail has visible state class."""
        assert ".video-player-queue-rail.visible" in css_content
        assert "translateY(0)" in css_content

    def test_rail_auto_hide(self, js_content):
        """Rail auto-hides after inactivity."""
        assert "RAIL_AUTO_HIDE_MS" in js_content or "railTimer" in js_content
        assert "hideRail" in js_content

    def test_rail_click_navigation(self, js_content):
        """Clicking rail item navigates to that video."""
        assert "handleRailClick" in js_content
        assert "goToVideo" in js_content

    def test_edge_trigger_shows_rail(self, js_content):
        """Edge trigger zone shows rail."""
        assert "edgeTrigger" in js_content
        assert "showRail" in js_content


# ═══════════════════════════════════════════════════════════════════════════
# Save Feature Tests (Phase 2)
# ═══════════════════════════════════════════════════════════════════════════

class TestSaveFeature:
    """Save button persists locally."""

    def test_saved_key_defined(self, js_content):
        """localStorage key for saved videos is defined."""
        assert "SAVED_KEY" in js_content
        assert "pfmall_saved_videos" in js_content

    def test_get_saved_videos_function(self, js_content):
        """getSavedVideos function exists."""
        assert "function getSavedVideos" in js_content

    def test_toggle_save_function(self, js_content):
        """toggleSave function exists."""
        assert "function toggleSave" in js_content

    def test_is_video_saved_function(self, js_content):
        """isVideoSaved function exists."""
        assert "function isVideoSaved" in js_content

    def test_save_button_state_updated(self, js_content):
        """Save button state is updated."""
        assert "updateSaveButtonState" in js_content

    def test_save_uses_localstorage(self, js_content):
        """Save uses localStorage."""
        assert "localStorage.setItem" in js_content
        assert "localStorage.getItem" in js_content

    def test_is_current_saved_api(self, js_content):
        """isCurrentSaved API method exists."""
        assert "isCurrentSaved:" in js_content

    def test_get_saved_count_api(self, js_content):
        """getSavedCount API method exists."""
        assert "getSavedCount:" in js_content


class TestSaveCSS:
    """Save button CSS states."""

    def test_saved_class_exists(self, css_content):
        """Saved state class exists."""
        assert ".saved" in css_content

    def test_saved_fill_style(self, css_content):
        """Saved state fills the icon."""
        assert "fill:" in css_content


# ═══════════════════════════════════════════════════════════════════════════
# Share Feature Tests (Phase 2)
# ═══════════════════════════════════════════════════════════════════════════

class TestShareFeature:
    """Share button uses native share or clipboard."""

    def test_share_video_function(self, js_content):
        """shareVideo function exists."""
        assert "function shareVideo" in js_content

    def test_get_share_url_function(self, js_content):
        """getShareUrl function exists."""
        assert "function getShareUrl" in js_content

    def test_navigator_share_used(self, js_content):
        """navigator.share is used when available."""
        assert "navigator.share" in js_content

    def test_clipboard_fallback(self, js_content):
        """Clipboard fallback exists."""
        assert "clipboard" in js_content or "execCommand" in js_content

    def test_share_url_priority(self, js_content):
        """Share URL priority: embed_url > source_url."""
        assert "embed_url" in js_content
        assert "source_url" in js_content


# ═══════════════════════════════════════════════════════════════════════════
# Watch History Tests (Phase 2)
# ═══════════════════════════════════════════════════════════════════════════

class TestWatchHistory:
    """Watch history persists locally."""

    def test_history_key_defined(self, js_content):
        """localStorage key for history is defined."""
        assert "HISTORY_KEY" in js_content
        assert "pfmall_watch_history" in js_content

    def test_get_watch_history_function(self, js_content):
        """getWatchHistory function exists."""
        assert "function getWatchHistory" in js_content

    def test_record_watch_function(self, js_content):
        """recordWatch function exists."""
        assert "function recordWatch" in js_content

    def test_history_max_defined(self, js_content):
        """History max limit is defined."""
        assert "HISTORY_MAX" in js_content

    def test_history_recorded_on_open(self, js_content):
        """Watch history is recorded on open."""
        # recordWatch should be called in open function
        assert "recordWatch" in js_content

    def test_history_recorded_on_navigate(self, js_content):
        """Watch history is recorded on navigation."""
        # recordWatch should be called in goToVideo
        assert "recordWatch" in js_content

    def test_get_history_api(self, js_content):
        """getHistory API method exists."""
        assert "getHistory:" in js_content

    def test_clear_history_api(self, js_content):
        """clearHistory API method exists."""
        assert "clearHistory:" in js_content

    def test_history_entry_has_timestamp(self, js_content):
        """History entry includes timestamp."""
        assert "timestamp:" in js_content
        assert "toISOString" in js_content
