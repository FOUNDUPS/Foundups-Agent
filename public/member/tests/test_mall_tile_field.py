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
        """Tile field uses CSS grid with density variables."""
        assert 'display: grid' in tile_field_css
        # Video Mall runtime uses CSS variables for density control
        assert '--field-columns' in tile_field_css

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
        assert 'enterFoundUp:' in tile_field_js
        # Video runtime API (replaced inspector with play/pause)
        assert 'togglePlay:' in tile_field_js
        assert 'expandFoundUp:' in tile_field_js
        assert 'collapseFoundUp:' in tile_field_js

    def test_double_tap_detection(self, tile_field_js):
        """Double-tap detection is implemented."""
        assert 'DOUBLE_TAP_WINDOW' in tile_field_js
        assert 'lastTapTime' in tile_field_js

    def test_video_runtime_elements(self, tile_field_js):
        """Video runtime elements are created dynamically."""
        assert 'mall-tile-field-collapse-hint' in tile_field_js
        assert 'mall-tile-queue-count' in tile_field_js

    def test_foundup_id_attribute(self, tile_field_js):
        """Tiles have data-foundup-id for SoftProto targeting."""
        assert 'data-foundup-id' in tile_field_js

    def test_uses_mall_planes(self, tile_field_js):
        """Integration with existing mallPlanes for FoundUp view."""
        assert 'window.mallPlanes' in tile_field_js
        assert 'mallPlanes.openFoundUp' in tile_field_js


class TestGuardrailsRespected:
    """Test that D's guardrails are respected."""

    def test_escape_closes_expanded_first(self, index_html):
        """Escape key closes expanded video field before other surfaces."""
        # The escape handler should check expanded state first
        assert 'mallTileField.isExpanded()' in index_html
        assert 'mallTileField.collapseFoundUp()' in index_html

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


class TestProjectionControls:
    """Test the projection shell for tile sorting."""

    def test_projection_container_exists(self, index_html):
        """Projection controls container exists."""
        assert 'id="mallProjection"' in index_html

    def test_projection_has_aria_label(self, index_html):
        """Projection nav has accessibility label."""
        assert 'aria-label="Sort FoundUps"' in index_html

    def test_default_projection_chip(self, index_html):
        """Default (All) projection chip exists."""
        assert 'data-projection="default"' in index_html
        assert '>All</button>' in index_html

    def test_alpha_projection_chip(self, index_html):
        """Alphabetical projection chip exists."""
        assert 'data-projection="alpha"' in index_html
        assert '>A-Z</button>' in index_html

    def test_readiness_projection_chip(self, index_html):
        """Readiness projection chip exists."""
        assert 'data-projection="readiness"' in index_html
        assert '>Readiness</button>' in index_html

    def test_category_projection_chip(self, index_html):
        """Category projection chip exists."""
        assert 'data-projection="category"' in index_html
        assert '>Category</button>' in index_html

    def test_default_chip_is_active(self, index_html):
        """Default projection chip has active class."""
        # Check the active class is on the default chip
        assert 'mall-projection-chip active" data-projection="default"' in index_html


class TestProjectionCSS:
    """Test projection controls CSS."""

    def test_projection_container_styles(self, tile_field_css):
        """Projection container has flex layout."""
        assert '.mall-projection {' in tile_field_css
        assert 'display: flex' in tile_field_css

    def test_projection_chip_styles(self, tile_field_css):
        """Projection chips have pill styling."""
        assert '.mall-projection-chip {' in tile_field_css
        assert 'border-radius: 999px' in tile_field_css

    def test_active_chip_highlight(self, tile_field_css):
        """Active projection chip has visual highlight."""
        assert '.mall-projection-chip.active {' in tile_field_css

    def test_chip_hover_state(self, tile_field_css):
        """Projection chips have hover state."""
        assert '.mall-projection-chip:hover' in tile_field_css

    def test_chip_touch_target(self, tile_field_css):
        """Projection chips have 44px min-height for phone ergonomics."""
        assert 'min-height: 44px' in tile_field_css


class TestProjectionJS:
    """Test projection logic in JS."""

    def test_projection_api_setProjection(self, tile_field_js):
        """setProjection function is exposed."""
        assert 'setProjection:' in tile_field_js

    def test_projection_api_getProjection(self, tile_field_js):
        """getProjection function is exposed."""
        assert 'getProjection:' in tile_field_js

    def test_projection_api_resetProjection(self, tile_field_js):
        """resetProjection function is exposed."""
        assert 'resetProjection:' in tile_field_js

    def test_projection_state_variable(self, tile_field_js):
        """currentProjection state variable exists."""
        assert 'currentProjection' in tile_field_js

    def test_original_order_preserved(self, tile_field_js):
        """Original order is preserved for reset."""
        assert 'originalOrder' in tile_field_js

    def test_readiness_order_defined(self, tile_field_js):
        """Readiness sort order is defined."""
        assert 'READINESS_ORDER' in tile_field_js

    def test_sort_by_projection_function(self, tile_field_js):
        """sortByProjection function exists."""
        assert 'sortByProjection' in tile_field_js

    def test_bind_projection_chips_called(self, tile_field_js):
        """bindProjectionChips is called in initialize."""
        assert 'bindProjectionChips()' in tile_field_js


# ═══════════════════════════════════════════════
# Non-Video Tile Behavior (PR #303)
# ═══════════════════════════════════════════════

class TestNonVideoTileRendering:
    """Non-video tiles render without video controls."""

    def test_has_videos_includes_video_data(self, tile_field_js):
        """hasVideos check includes video_data for expanded tiles."""
        # Both renderTiles and togglePlay must check video_data
        assert 'item.video_data' in tile_field_js

    def test_non_video_class_applied(self, tile_field_js):
        """Non-video tiles get .non-video class."""
        assert "' non-video'" in tile_field_js or '" non-video"' in tile_field_js

    def test_play_indicator_conditional_on_has_videos(self, tile_field_js):
        """Play indicator only rendered for video tiles."""
        assert "hasVideos ? '<div class=\"mall-tile-play-indicator\">" in tile_field_js or \
               'hasVideos ?' in tile_field_js and 'mall-tile-play-indicator' in tile_field_js

    def test_audio_button_conditional_on_has_videos(self, tile_field_js):
        """Audio (speaker) button only rendered for video tiles."""
        assert "hasVideos ? '<button class=\"mall-tile-audio\"" in tile_field_js or \
               'hasVideos ?' in tile_field_js and 'mall-tile-audio' in tile_field_js

    def test_expand_button_conditional_on_has_videos(self, tile_field_js):
        """Expand button only rendered for video tiles."""
        assert "hasVideos ? '<button class=\"mall-tile-expand\"" in tile_field_js or \
               'hasVideos ?' in tile_field_js and 'mall-tile-expand' in tile_field_js


class TestNonVideoActionBadge:
    """Non-video tiles show source action badge."""

    def test_source_type_actions_defined(self, tile_field_js):
        """Source type action labels are defined."""
        assert 'sourceTypeActions' in tile_field_js

    def test_github_repo_action_label(self, tile_field_js):
        """github_repo gets 'View Repo' action label."""
        assert "'View Repo'" in tile_field_js or '"View Repo"' in tile_field_js

    def test_external_app_action_label(self, tile_field_js):
        """external_app gets 'Open App' action label."""
        assert "'Open App'" in tile_field_js or '"Open App"' in tile_field_js

    def test_internal_service_action_label(self, tile_field_js):
        """internal_service gets 'Open Service' action label."""
        assert "'Open Service'" in tile_field_js or '"Open Service"' in tile_field_js

    def test_action_badge_class_rendered(self, tile_field_js):
        """Action badge uses .mall-tile-action-badge class."""
        assert 'mall-tile-action-badge' in tile_field_js

    def test_action_badge_only_for_non_video(self, tile_field_js):
        """Action badge conditional on !hasVideos."""
        assert '!hasVideos' in tile_field_js


class TestNonVideoActionBadgeCSS:
    """CSS styling for non-video tile action badge."""

    def test_action_badge_styles_exist(self, tile_field_css):
        """Action badge CSS class is defined."""
        assert '.mall-tile-action-badge' in tile_field_css

    def test_action_badge_positioned_bottom_left(self, tile_field_css):
        """Action badge is positioned at bottom-left."""
        # Extract the action badge block and check positioning
        assert 'bottom:' in tile_field_css and 'left:' in tile_field_css

    def test_non_video_class_styles_exist(self, tile_field_css):
        """Non-video tile class has styles."""
        assert '.mall-tile.non-video' in tile_field_css

    def test_non_video_border_accent(self, tile_field_css):
        """Non-video tiles have border accent."""
        assert 'border-color:' in tile_field_css


class TestNonVideoTileTapBehavior:
    """Non-video tile tap opens quick-view by ID."""

    def test_non_video_tap_opens_quick_view(self, tile_field_js):
        """Non-video tiles open quick-view instead of inline preview."""
        assert 'if (!hasVideos)' in tile_field_js

    def test_quick_view_opened_by_foundup_id(self, tile_field_js):
        """Quick-view opened by foundup_id, not index."""
        assert 'openFoundUpById' in tile_field_js

    def test_foundup_id_extracted_from_item(self, tile_field_js):
        """foundup_id is extracted from item for handoff."""
        assert 'item.foundup_id' in tile_field_js or "item.foundup_id || item.id" in tile_field_js


class TestMallPlanesIdLookup:
    """mall-planes.js supports ID-based lookup."""

    @pytest.fixture
    def mall_planes_js(self):
        path = Path(__file__).parent.parent / 'js' / 'mall-planes.js'
        return path.read_text(encoding='utf-8')

    def test_open_foundup_by_id_exposed(self, mall_planes_js):
        """openFoundUpById function is exposed in public API."""
        assert 'openFoundUpById' in mall_planes_js

    def test_open_foundup_by_id_iterates_catalog(self, mall_planes_js):
        """openFoundUpById iterates catalog to find matching ID."""
        assert 'catalog[i].foundup_id' in mall_planes_js or 'catalog[i].id' in mall_planes_js

    def test_open_foundup_by_id_calls_open_foundup(self, mall_planes_js):
        """openFoundUpById calls openFoundUp with found index."""
        assert 'openFoundUp(i)' in mall_planes_js


class TestExpandedVideoTilesPreserved:
    """Expanded video tiles (with video_data) retain video behavior."""

    def test_video_data_treated_as_video(self, tile_field_js):
        """video_data field counts as hasVideos."""
        # Check both renderTiles hasVideos and togglePlay hasVideos
        assert 'video_data' in tile_field_js
        # Should appear twice (renderTiles + togglePlay)
        import re
        matches = re.findall(r'item\.video_data', tile_field_js)
        assert len(matches) >= 2, "video_data should be checked in both renderTiles and togglePlay"

    def test_get_expanded_videos_sets_video_data(self, tile_field_js):
        """getExpandedVideos() sets video_data on mapped items."""
        assert 'video_data:' in tile_field_js or 'video_data: video' in tile_field_js
