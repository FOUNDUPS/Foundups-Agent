"""
Lane Autoplay & Fullscreen Entry Tests

Tests for:
  - Tap starts lane autoplay (video-backed tiles in Mall mode)
  - Lane autoplay stays inside the lane's videos[] queue
  - Autoplay policy: loop to start when queue ends
  - Pinch-out expanded behavior remains intact
  - Fullscreen exposes "Enter FoundUp" button
  - FoundUp entry uses stable identity (foundup_id)
  - Non-video tiles remain truthful (no fake autoplay)
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(relpath):
    with open(os.path.join(ROOT, relpath), encoding="utf-8") as f:
        return f.read()


class TestLaneAutoplayState:
    """Test lane autoplay state management."""

    def test_autoplay_lane_index_var_exists(self):
        """autoplayLaneIndex variable tracks current lane."""
        js = _read("js/mall-tile-field.js")
        assert "autoplayLaneIndex" in js

    def test_autoplay_video_index_var_exists(self):
        """autoplayVideoIndex tracks position in lane queue."""
        js = _read("js/mall-tile-field.js")
        assert "autoplayVideoIndex" in js

    def test_autoplay_loop_policy_defined(self):
        """AUTOPLAY_LOOP_POLICY defines queue-end behavior."""
        js = _read("js/mall-tile-field.js")
        assert "AUTOPLAY_LOOP_POLICY" in js
        assert "'loop'" in js  # Loop policy chosen


class TestLaneAutoplayBehavior:
    """Test lane autoplay advancement logic."""

    def test_advance_lane_autoplay_function_exists(self):
        """advanceLaneAutoplay function handles video ended event."""
        js = _read("js/mall-tile-field.js")
        assert "function advanceLaneAutoplay()" in js

    def test_start_lane_video_at_index_exists(self):
        """startLaneVideoAtIndex plays specific video in lane."""
        js = _read("js/mall-tile-field.js")
        assert "function startLaneVideoAtIndex(" in js

    def test_html5_video_ended_calls_advance(self):
        """HTML5 video ended event triggers advanceLaneAutoplay."""
        js = _read("js/mall-tile-field.js")
        # Both inline preview and lane preview should have ended handler
        assert "video.onended" in js or "vid.onended" in js
        assert "advanceLaneAutoplay()" in js

    def test_youtube_ended_calls_advance(self):
        """YouTube player ended state triggers advanceLaneAutoplay."""
        js = _read("js/mall-tile-field.js")
        # YT.PlayerState.ENDED = 0
        assert "event.data === 0" in js
        assert "advanceLaneAutoplay()" in js

    def test_loop_policy_resets_to_zero(self):
        """Loop policy resets autoplayVideoIndex to 0 at queue end."""
        js = _read("js/mall-tile-field.js")
        assert "nextVideoIdx = 0" in js


class TestLaneAutoplayQueueConstraint:
    """Test that autoplay stays within the lane queue."""

    def test_only_advances_in_mall_mode(self):
        """Autoplay only advances when expandedFoundUp is null."""
        js = _read("js/mall-tile-field.js")
        assert "if (expandedFoundUp !== null) return" in js

    def test_checks_lane_videos_array(self):
        """Autoplay checks lane.videos exists before advancing."""
        js = _read("js/mall-tile-field.js")
        assert "!lane.videos" in js

    def test_stops_if_no_videos(self):
        """Stops preview if lane has no videos."""
        js = _read("js/mall-tile-field.js")
        # Should call stopInlinePreview when no videos
        assert "stopInlinePreview()" in js


class TestTogglePlayLaneInit:
    """Test togglePlay initializes lane autoplay correctly."""

    def test_toggle_play_sets_autoplay_lane_index(self):
        """togglePlay sets autoplayLaneIndex for video-backed tiles."""
        js = _read("js/mall-tile-field.js")
        assert "autoplayLaneIndex = index" in js

    def test_toggle_play_sets_video_index_zero(self):
        """togglePlay starts at video index 0."""
        js = _read("js/mall-tile-field.js")
        assert "autoplayVideoIndex = 0" in js

    def test_toggle_play_calls_start_lane_video(self):
        """togglePlay calls startLaneVideoAtIndex for lane autoplay."""
        js = _read("js/mall-tile-field.js")
        assert "startLaneVideoAtIndex(index, 0)" in js


class TestStopInlinePreviewClearsLane:
    """Test stopInlinePreview clears lane state."""

    def test_stop_clears_autoplay_lane_index(self):
        """stopInlinePreview resets autoplayLaneIndex to null."""
        js = _read("js/mall-tile-field.js")
        assert "autoplayLaneIndex = null" in js

    def test_stop_clears_autoplay_video_index(self):
        """stopInlinePreview resets autoplayVideoIndex to 0."""
        js = _read("js/mall-tile-field.js")
        # Should reset to 0 in stopInlinePreview
        assert "autoplayVideoIndex = 0" in js


class TestFullscreenEnterFoundUp:
    """Test fullscreen player Enter FoundUp button."""

    def test_enter_button_in_top_bar(self):
        """Enter FoundUp button exists in fullscreen top bar."""
        js = _read("js/mall-video-player.js")
        assert 'data-action="enter"' in js
        assert "Enter FoundUp" in js

    def test_enter_action_handler_exists(self):
        """handleTopBarClick handles 'enter' action."""
        js = _read("js/mall-video-player.js")
        assert "case 'enter':" in js
        assert "enterFoundUp()" in js

    def test_enter_foundup_function_exists(self):
        """enterFoundUp function navigates to FoundUp page."""
        js = _read("js/mall-video-player.js")
        assert "function enterFoundUp()" in js

    def test_uses_stable_foundup_id(self):
        """Entry URL uses currentFoundUpId (stable identity)."""
        js = _read("js/mall-video-player.js")
        assert "currentFoundUpId" in js
        assert "encodeURIComponent(currentFoundUpId)" in js

    def test_navigates_to_foundup_html(self):
        """Navigates to /member/foundup.html with id param."""
        js = _read("js/mall-video-player.js")
        assert "/member/foundup.html?id=" in js


class TestFullscreenEnterFoundUpCSS:
    """Test Enter FoundUp button styling."""

    def test_entry_button_class_exists(self):
        """Entry button has dedicated CSS class."""
        css = _read("css/mall-video-player.css")
        assert ".video-player-btn-entry" in css

    def test_entry_button_has_label(self):
        """Entry button has visible label."""
        css = _read("css/mall-video-player.css")
        assert ".video-player-btn-label" in css


class TestFullscreenVideoEnded:
    """Test fullscreen player video ended handler."""

    def test_handle_video_ended_exists(self):
        """handleVideoEnded function is defined."""
        js = _read("js/mall-video-player.js")
        assert "function handleVideoEnded()" in js

    def test_handle_video_ended_advances_queue(self):
        """handleVideoEnded calls goToVideo to advance."""
        js = _read("js/mall-video-player.js")
        # Check it advances to next video
        assert "goToVideo(currentIndex + 1)" in js

    def test_handle_video_ended_loops_at_end(self):
        """handleVideoEnded loops to start at queue end."""
        js = _read("js/mall-video-player.js")
        assert "goToVideo(0)" in js


class TestNonVideoTruth:
    """Test non-video tiles retain truthful behavior."""

    def test_non_video_opens_quickview(self):
        """Non-video tiles open quick-view, not fake autoplay."""
        js = _read("js/mall-tile-field.js")
        # Non-video tiles should use openFoundUpById
        assert "openFoundUpById(foundupId)" in js

    def test_non_video_check_before_autoplay(self):
        """hasVideos check prevents non-video autoplay."""
        js = _read("js/mall-tile-field.js")
        assert "if (!hasVideos)" in js


class TestExpandedModeUnaffected:
    """Test pinch-out expanded mode remains intact."""

    def test_expanded_mode_class_toggle(self):
        """Expanded mode class still toggles correctly."""
        js = _read("js/mall-tile-field.js")
        assert "expandedFoundUp !== null" in js
        assert "expanded-mode" in js

    def test_pinch_out_expand_still_works(self):
        """Pinch-out gesture still expands to video field."""
        js = _read("js/mall-tile-field.js")
        assert "onPinchOut:" in js
        assert "expandFoundUp(index)" in js

    def test_pinch_in_collapse_still_works(self):
        """Pinch-in gesture still collapses back to Mall."""
        js = _read("js/mall-tile-field.js")
        assert "onPinchIn:" in js
        assert "collapseFoundUp()" in js
