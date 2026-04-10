"""
Tile Keyboard Accessibility Tests — pfMALL A11y Phase 1

Tests keyboard navigation and focus management for Mall tiles.
Validates WCAG 2.1 Level AA compliance for:
  - Focus visibility: Clear visual indicator for keyboard focus
  - Keyboard activation: Enter/Space parity with pointer
  - Control accessibility: Audio/expand buttons focusable with labels
  - Focus return: Surface exit returns focus to originating tile
"""
import pytest
from pathlib import Path


@pytest.fixture
def tile_field_css():
    """Load the tile field CSS file."""
    path = Path(__file__).parent.parent / 'css' / 'mall-tile-field.css'
    return path.read_text(encoding='utf-8')


@pytest.fixture
def tile_field_js():
    """Load the tile field JS file."""
    path = Path(__file__).parent.parent / 'js' / 'mall-tile-field.js'
    return path.read_text(encoding='utf-8')


@pytest.fixture
def mall_planes_css():
    """Load the mall-planes CSS file."""
    path = Path(__file__).parent.parent / 'css' / 'mall-planes.css'
    return path.read_text(encoding='utf-8')


@pytest.fixture
def mall_planes_js():
    """Load the mall-planes JS file."""
    path = Path(__file__).parent.parent / 'js' / 'mall-planes.js'
    return path.read_text(encoding='utf-8')


# ========== Focus Visibility ==========

class TestTileFocusVisibility:
    """Test visible focus indicators on tiles."""

    def test_tile_has_tabindex(self, tile_field_js):
        """Tiles are keyboard focusable via tabindex."""
        assert 'tabindex="0"' in tile_field_js

    def test_tile_has_aria_label(self, tile_field_js):
        """Tiles have aria-label for screen readers."""
        assert 'aria-label="' in tile_field_js

    def test_tile_focus_visible_separate_from_hover(self, tile_field_css):
        """Focus-visible is separate from hover (distinct styling)."""
        # Must NOT be combined: .mall-tile:hover, .mall-tile:focus-visible
        # Should have separate rule for :focus-visible
        lines = tile_field_css.split('\n')
        focus_visible_lines = [l for l in lines if ':focus-visible' in l and '.mall-tile' in l]
        # At least one line should have ONLY :focus-visible (not combined with :hover)
        standalone_focus = any(
            ':focus-visible' in l and ':hover' not in l
            for l in focus_visible_lines
        )
        assert standalone_focus, "Tile :focus-visible should be a standalone rule"

    def test_tile_focus_has_visible_ring(self, tile_field_css):
        """Focus-visible has a clear visible ring (box-shadow or outline)."""
        # Look for focus indicator styles after :focus-visible
        assert '141, 113, 255' in tile_field_css  # Purple focus ring color
        # Check for either outline or box-shadow with focus ring
        assert 'box-shadow: 0 0 0 3px' in tile_field_css or 'outline: 2px solid' in tile_field_css

    def test_tile_hover_no_outline_none(self, tile_field_css):
        """Hover state should not have outline: none that breaks focus."""
        # Split into rules and check hover doesn't have outline: none
        # Focus-visible CAN have outline: none if using box-shadow instead
        css_text = tile_field_css
        # Find the hover rule
        hover_match = '.mall-tile:hover {'
        if hover_match in css_text:
            hover_start = css_text.index(hover_match)
            hover_end = css_text.index('}', hover_start)
            hover_rule = css_text[hover_start:hover_end]
            assert 'outline: none' not in hover_rule


# ========== Keyboard Activation ==========

class TestKeyboardActivation:
    """Test keyboard activation parity with pointer."""

    def test_tile_keydown_handler_exists(self, tile_field_js):
        """Tiles have keydown event handler."""
        assert "addEventListener('keydown'" in tile_field_js

    def test_space_triggers_toggle_play(self, tile_field_js):
        """Spacebar triggers togglePlay (same as tap)."""
        # Space key check exists
        assert "e.key === ' '" in tile_field_js
        # And calls togglePlay
        assert 'togglePlay(index)' in tile_field_js

    def test_enter_triggers_enter_foundup(self, tile_field_js):
        """Enter key triggers enterFoundUp."""
        assert "e.key === 'Enter'" in tile_field_js
        assert 'enterFoundUp(index)' in tile_field_js

    def test_escape_closes_expanded_or_preview(self, tile_field_js):
        """Escape key closes expanded view or stops preview."""
        assert "e.key === 'Escape'" in tile_field_js
        assert 'collapseFoundUp()' in tile_field_js or 'stopInlinePreview()' in tile_field_js


# ========== Control Accessibility ==========

class TestControlAccessibility:
    """Test audio and expand button accessibility."""

    def test_audio_button_has_aria_label(self, tile_field_js):
        """Audio button has aria-label."""
        assert 'aria-label=' in tile_field_js
        assert 'Unmute preview' in tile_field_js or 'Mute preview' in tile_field_js

    def test_audio_button_has_title(self, tile_field_js):
        """Audio button has title for tooltip."""
        assert '.title =' in tile_field_js

    def test_expand_button_has_aria_label(self, tile_field_js):
        """Expand button has aria-label."""
        assert 'aria-label="Open fullscreen"' in tile_field_js

    def test_expand_button_has_title(self, tile_field_js):
        """Expand button has title attribute."""
        assert 'title="Fullscreen"' in tile_field_js

    def test_audio_button_focus_visible_css(self, tile_field_css):
        """Audio button has focus-visible styling."""
        assert '.mall-tile-audio:focus-visible' in tile_field_css

    def test_expand_button_focus_visible_css(self, tile_field_css):
        """Expand button has focus-visible styling."""
        assert '.mall-tile-expand:focus-visible' in tile_field_css

    def test_control_buttons_focusable_in_tile(self, tile_field_css):
        """Control buttons become visible when tile has focus-within."""
        assert ':focus-within .mall-tile-expand' in tile_field_css
        assert ':focus-within .mall-tile-audio' in tile_field_css


# ========== Focus Return ==========

class TestFocusReturn:
    """Test focus management when closing surfaces."""

    def test_return_focus_id_tracked(self, mall_planes_js):
        """Return focus ID is tracked on open (stable identity)."""
        assert 'returnFocusId' in mall_planes_js

    def test_focus_returned_by_foundup_id(self, mall_planes_js):
        """Focus is returned by querying data-foundup-id (stable across projections)."""
        assert 'data-foundup-id="' in mall_planes_js
        assert 'tile.focus()' in mall_planes_js

    def test_close_button_focused_on_open(self, mall_planes_js):
        """Close button receives focus when plane opens."""
        assert 'closeBtn.focus()' in mall_planes_js

    def test_navigate_updates_return_id(self, mall_planes_js):
        """Arrow navigation updates return focus ID to navigated item."""
        # Check that navigateFoundUp updates returnFocusId from item identity
        assert 'navItem.foundup_id || navItem.id' in mall_planes_js or 'item.foundup_id || item.id' in mall_planes_js

    def test_focus_return_uses_stable_identity(self, mall_planes_js):
        """Focus return uses foundup_id, not data-index (survives projection changes)."""
        # Must NOT query by data-index for focus return
        # The closeView function should query by data-foundup-id
        close_view_section = mall_planes_js[mall_planes_js.find('function closeView'):]
        close_view_section = close_view_section[:close_view_section.find('function ', 10)]
        assert 'data-foundup-id' in close_view_section
        assert 'data-index' not in close_view_section


# ========== Mall Planes Focus Styles ==========

class TestMallPlanesFocusStyles:
    """Test focus styles for mall planes UI elements."""

    def test_close_button_focus_visible(self, mall_planes_css):
        """Close button has focus-visible styling."""
        assert '.fv-close-btn:focus-visible' in mall_planes_css

    def test_primary_cta_focus_visible(self, mall_planes_css):
        """Primary CTA has focus-visible styling."""
        assert '.fv-primary-cta:focus-visible' in mall_planes_css

    def test_secondary_link_focus_visible(self, mall_planes_css):
        """Secondary link has focus-visible styling."""
        assert '.fv-secondary-link:focus-visible' in mall_planes_css

    def test_focus_uses_outline_not_just_color(self, mall_planes_css):
        """Focus styles use outline for visibility."""
        # Must have outline property in focus-visible rules
        assert 'outline: 2px solid' in mall_planes_css


# ========== ARIA Semantics ==========

class TestARIASemantics:
    """Test ARIA roles and semantics."""

    def test_tile_rendered_as_article(self, tile_field_js):
        """Tiles are rendered as article elements."""
        assert '<article class="' in tile_field_js

    def test_mall_planes_keyboard_handler(self, mall_planes_js):
        """Mall planes has keyboard handler for navigation."""
        assert "addEventListener('keydown'" in mall_planes_js
        assert "e.key === 'Escape'" in mall_planes_js
        assert "e.key === 'ArrowLeft'" in mall_planes_js
        assert "e.key === 'ArrowRight'" in mall_planes_js
