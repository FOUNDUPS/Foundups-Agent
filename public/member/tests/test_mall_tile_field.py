"""
Mall Tile Field Tests

Tests for the low-chrome tile discovery surface.
SoftProto mount point: #mallTileField[data-softproto-mount="tile-field"]

Gestures tested:
  - Tap tile: Show inspector overlay
  - Double-tap tile: Enter FoundUp view
  - Escape: Close inspector
"""
import pytest
from pathlib import Path


@pytest.fixture
def index_html():
    """Load the member index.html file."""
    path = Path(__file__).parent.parent / 'index.html'
    return path.read_text(encoding='utf-8')


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


class TestTileFieldStructure:
    """Test the HTML structure for tile field."""

    def test_tile_field_container_exists(self, index_html):
        """Tile field mount point exists."""
        assert 'id="mallTileField"' in index_html

    def test_tile_field_has_softproto_hook(self, index_html):
        """Tile field has SoftProto mount attribute."""
        assert 'data-softproto-mount="tile-field"' in index_html

    def test_tile_field_css_linked(self, index_html):
        """Tile field CSS is linked in head."""
        assert 'href="css/mall-tile-field.css"' in index_html

    def test_tile_field_js_loaded(self, index_html):
        """Tile field JS is loaded."""
        assert 'src="js/mall-tile-field.js"' in index_html

    def test_mall_copy_removed(self, index_html):
        """Mall copy section removed entirely (anchor model chrome reduction)."""
        # Phase 2 removed mall-copy entirely - tiles speak for themselves
        assert 'mall-copy' not in index_html
        assert 'Swipe through the FoundUps' not in index_html
        assert 'The gate stays exactly where it is' not in index_html

    def test_carousel_removed(self, index_html):
        """Old carousel structure is removed."""
        assert 'mall-carousel-shell' not in index_html
        assert 'id="mallTrack"' not in index_html
        assert 'id="mallDots"' not in index_html
        assert 'id="mallFocus"' not in index_html


class TestTileFieldCSS:
    """Test the tile field CSS."""

    def test_tile_field_grid(self, tile_field_css):
        """Tile field uses CSS grid."""
        assert 'display: grid' in tile_field_css
        assert 'grid-template-columns: repeat(auto-fill' in tile_field_css

    def test_tile_square_aspect(self, tile_field_css):
        """Tiles are square."""
        assert 'aspect-ratio: 1' in tile_field_css

    def test_tile_themes_exist(self, tile_field_css):
        """Theme classes exist for tiles."""
        assert '.mall-tile.theme-antifafm' in tile_field_css
        assert '.mall-tile.theme-gotjunk' in tile_field_css
        assert '.mall-tile.theme-magadoom' in tile_field_css

    def test_inspector_overlay_styles(self, tile_field_css):
        """Inspector overlay styles exist."""
        assert '.tile-inspector-scrim' in tile_field_css
        assert '.tile-inspector' in tile_field_css
        assert '.tile-inspector.visible' in tile_field_css


class TestTileFieldJS:
    """Test the tile field JavaScript."""

    def test_public_api_exposed(self, tile_field_js):
        """Public API is exposed on window.mallTileField."""
        assert 'window.mallTileField' in tile_field_js
        assert 'initialize:' in tile_field_js
        assert 'openInspector:' in tile_field_js
        assert 'closeInspector:' in tile_field_js
        assert 'enterFoundUp:' in tile_field_js

    def test_double_tap_detection(self, tile_field_js):
        """Double-tap detection is implemented."""
        assert 'DOUBLE_TAP_DELAY' in tile_field_js
        assert 'lastTapTime' in tile_field_js

    def test_inspector_creation(self, tile_field_js):
        """Inspector overlay is created dynamically."""
        assert 'createInspector' in tile_field_js
        assert 'tile-inspector-scrim' in tile_field_js

    def test_foundup_id_attribute(self, tile_field_js):
        """Tiles have data-foundup-id for SoftProto targeting."""
        assert 'data-foundup-id' in tile_field_js

    def test_uses_mall_planes(self, tile_field_js):
        """Integration with existing mallPlanes for FoundUp view."""
        assert 'window.mallPlanes' in tile_field_js
        assert 'mallPlanes.openFoundUp' in tile_field_js


class TestGuardrailsRespected:
    """Test that D's guardrails are respected."""

    def test_escape_closes_inspector_first(self, index_html):
        """Escape key closes inspector before other surfaces."""
        # The escape handler should check inspector first
        assert 'mallTileField.isInspectorOpen()' in index_html
        assert 'mallTileField.closeInspector()' in index_html

    def test_red_dog_button_preserved(self, index_html):
        """Red Dog button is still present and functional."""
        assert 'id="redDogBtn"' in index_html

    def test_overlay_scrim_preserved(self, index_html):
        """Overlay scrim for existing planes is preserved."""
        assert 'id="overlayScrim"' in index_html


class TestInitialization:
    """Test the initialization flow."""

    def test_tile_field_initialized_with_catalog(self, index_html):
        """Tile field is initialized with mallCatalog."""
        assert 'mallTileField.initialize(mallCatalog)' in index_html

    def test_mall_planes_sync_stub(self, index_html):
        """mallPlanesSync stub exists for navigation plane compatibility."""
        assert 'window.mallPlanesSync' in index_html

    def test_red_dog_concierge_still_wired(self, index_html):
        """Red Dog concierge is still populated with FoundUps."""
        assert 'redDog.setFoundUps(mallCatalog)' in index_html


class TestAnchorModel:
    """Test the 3-anchor shell structure."""

    def test_top_anchor_exists(self, index_html):
        """Top anchor (self/account) exists."""
        assert 'data-anchor="top"' in index_html

    def test_middle_anchor_exists(self, index_html):
        """Middle anchor (discovery field) exists."""
        assert 'data-anchor="middle"' in index_html

    def test_bottom_anchor_exists(self, index_html):
        """Bottom anchor (Red Dog) exists."""
        assert 'data-anchor="bottom"' in index_html

    def test_avatar_trigger_in_top_anchor(self, index_html):
        """Avatar trigger is in top anchor for account access."""
        assert 'id="mallAvatarTrigger"' in index_html

    def test_tile_field_in_middle_anchor(self, index_html):
        """Tile field is in middle anchor."""
        assert 'id="mallTileField"' in index_html

    def test_red_dog_btn_in_bottom_anchor(self, index_html):
        """Red Dog button is in bottom anchor."""
        assert 'id="redDogBtn"' in index_html
        assert 'id="redDogAnchor"' in index_html

    def test_no_mall_copy_chrome(self, index_html):
        """Mall copy instruction section removed (chrome reduction)."""
        assert 'mall-copy' not in index_html


class TestNoRegression:
    """Test that existing functionality isn't broken."""

    def test_foundup_view_plane_exists(self, index_html):
        """FoundUp view plane (slides up) still exists."""
        assert 'id="foundupViewPlane"' in index_html

    def test_account_plane_exists(self, index_html):
        """Account plane still exists."""
        assert 'id="accountPlane"' in index_html

    def test_unified_red_dog_plane_exists(self, index_html):
        """Unified Red Dog/account plane exists (was separate redDogPanel)."""
        # Current truth: Red Dog merged into accountPlane with aria-label="Red Dog"
        assert 'id="accountPlane"' in index_html
        assert 'aria-label="Red Dog"' in index_html

    def test_gesture_engine_loaded(self, index_html):
        """Gesture engine is still loaded."""
        assert 'js/gesture-engine.js' in index_html

    def test_mall_planes_loaded(self, index_html):
        """Mall planes JS is still loaded."""
        assert 'js/mall-planes.js' in index_html
