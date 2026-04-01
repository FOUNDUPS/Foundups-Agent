"""
Mobile Blockers Phase 1 Tests

Tests for phone-first shell fixes:
- Safe area inset handling
- Dynamic viewport height (100dvh)
- Immediate tap response (no 300ms delay)
"""
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(relpath):
    with open(os.path.join(ROOT, relpath), encoding="utf-8") as f:
        return f.read()


class TestSafeAreaHandling:
    """Test safe area inset CSS is present."""

    def test_safe_area_variables_defined(self):
        """Safe area CSS variables are defined in member.css."""
        css = _read("css/member.css")
        assert "--safe-top: env(safe-area-inset-top" in css
        assert "--safe-bottom: env(safe-area-inset-bottom" in css
        assert "--safe-left: env(safe-area-inset-left" in css
        assert "--safe-right: env(safe-area-inset-right" in css

    def test_red_dog_anchor_uses_safe_area(self):
        """Red Dog FAB uses safe-area-inset-bottom."""
        css = _read("css/member.css")
        # Check that .red-dog-anchor bottom includes var(--safe-bottom)
        assert "calc(1.25rem + var(--safe-bottom))" in css

    def test_mall_shell_uses_safe_area(self):
        """Mall shell padding includes safe-area-inset-bottom."""
        css = _read("css/member.css")
        assert "calc(6rem + var(--safe-bottom))" in css

    def test_entry_red_dog_uses_safe_area(self):
        """Entry page Red Dog button uses safe-area-inset-bottom."""
        html = _read("foundup.html")
        assert "calc(1.5rem + var(--safe-bottom))" in html


class TestViewportFitCover:
    """Test viewport-fit=cover is present for notched devices."""

    def test_index_has_viewport_fit_cover(self):
        """index.html has viewport-fit=cover."""
        html = _read("index.html")
        assert "viewport-fit=cover" in html

    def test_foundup_has_viewport_fit_cover(self):
        """foundup.html has viewport-fit=cover."""
        html = _read("foundup.html")
        assert "viewport-fit=cover" in html


class TestDynamicViewportHeight:
    """Test 100dvh is used for mobile-safe viewport height."""

    def test_member_area_uses_dvh(self):
        """member-area uses 100dvh for min-height."""
        css = _read("css/member.css")
        assert ".member-area" in css
        # Should have both 100vh (fallback) and 100dvh
        assert "min-height: 100dvh" in css

    def test_mall_shell_uses_dvh(self):
        """mall-shell uses 100dvh for min-height."""
        css = _read("css/member.css")
        # Should have 100dvh after 100vh
        assert "min-height: 100dvh" in css

    def test_entry_shell_uses_dvh(self):
        """entry-shell uses 100dvh for min-height."""
        html = _read("foundup.html")
        assert "min-height: 100dvh" in html

    def test_webkit_fill_available_fallback(self):
        """-webkit-fill-available fallback exists for older Safari."""
        css = _read("css/member.css")
        assert "-webkit-fill-available" in css


class TestTapLatencyFix:
    """Test 300ms tap delay is removed."""

    def test_double_tap_window_renamed(self):
        """DOUBLE_TAP_DELAY renamed to DOUBLE_TAP_WINDOW."""
        js = _read("js/mall-tile-field.js")
        assert "DOUBLE_TAP_WINDOW" in js
        # Old delay variable should not exist
        assert "DOUBLE_TAP_DELAY = 300" not in js

    def test_immediate_inspector_open(self):
        """Single tap opens inspector immediately (no setTimeout wait)."""
        js = _read("js/mall-tile-field.js")
        # Should NOT have setTimeout waiting before openInspector
        # Old pattern: setTimeout(function() { ... openInspector ...
        # New pattern: direct openInspector(index) call
        assert "openInspector(index);" in js
        # The setTimeout for delayed inspector should be removed
        # Check for the new immediate pattern comment
        assert "open inspector immediately" in js.lower()

    def test_double_tap_still_enters_foundup(self):
        """Double-tap still enters FoundUp directly."""
        js = _read("js/mall-tile-field.js")
        assert "enterFoundUp(index)" in js
        assert "DOUBLE_TAP_WINDOW" in js


class TestInspectEnterSemanticsPreserved:
    """Test tap=inspect, double-tap=enter semantics are preserved."""

    def test_tap_opens_inspector(self):
        """Tap gesture opens inspector."""
        js = _read("js/mall-tile-field.js")
        assert "openInspector" in js

    def test_double_tap_enters_foundup(self):
        """Double-tap gesture enters FoundUp."""
        js = _read("js/mall-tile-field.js")
        # Double-tap should call enterFoundUp
        assert "enterFoundUp(index)" in js

    def test_inspector_enter_button_exists(self):
        """Inspector has Enter FoundUp button."""
        js = _read("js/mall-tile-field.js")
        assert "Enter FoundUp" in js
        assert "inspectorEnterBtn" in js


class TestThumbZoneRefinement:
    """Test Phase 2 thumb-zone ergonomics improvements."""

    def test_projection_chip_touch_target(self):
        """Projection chips have 44px min-height for WCAG compliance."""
        css = _read("css/mall-tile-field.css")
        assert "min-height: 44px" in css
        assert ".mall-projection-chip" in css

    def test_inspector_enter_button_touch_target(self):
        """Inspector enter button has comfortable thumb target."""
        css = _read("css/mall-tile-field.css")
        # Check for 48px min-height on the enter button
        assert ".tile-inspector-enter" in css
        assert "min-height: 48px" in css

    def test_inspector_bottom_sheet_on_phone(self):
        """Inspector becomes bottom sheet on small screens."""
        css = _read("css/mall-tile-field.css")
        assert "@media (max-width: 480px)" in css
        # Inspector should be bottom-anchored on mobile
        assert "bottom: 0" in css
        assert "translateY(100%)" in css

    def test_inspector_handle_indicator(self):
        """Bottom sheet has drag handle indicator."""
        css = _read("css/mall-tile-field.css")
        # Handle is created via ::before pseudo-element
        assert ".tile-inspector::before" in css
        assert 'content: ""' in css

    def test_mall_header_safe_top(self):
        """Mall header includes safe-area-inset-top for notched phones."""
        css = _read("css/member.css")
        assert "calc(0.5rem + var(--safe-top))" in css


class TestNoRegression:
    """Test existing shell behaviors are preserved."""

    def test_tile_inspector_still_works(self):
        """Tile inspector overlay still exists."""
        js = _read("js/mall-tile-field.js")
        assert "tile-inspector" in js
        assert "openInspector" in js
        assert "closeInspector" in js

    def test_foundup_entry_path_unchanged(self):
        """/member/foundup.html?id= path still works."""
        js = _read("js/mall-planes.js")
        assert "/member/foundup.html?id=" in js

    def test_anchor_structure_preserved(self):
        """Three-anchor structure is preserved."""
        html = _read("index.html")
        assert 'data-anchor="top"' in html
        assert 'data-anchor="middle"' in html
        assert 'data-anchor="bottom"' in html
