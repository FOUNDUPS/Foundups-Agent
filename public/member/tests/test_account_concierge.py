#!/usr/bin/env python3
"""Tests for Red Dog unified plane (migrated from account concierge phase 1).

Validates:
  1. account concierge host structure
  2. identity/avatar affordance presence
  3. FoundUps section naming and grid/tile structure
  4. invite codes hidden by default
  5. options section contains sign out
  6. no regression to member entry flow
"""

from pathlib import Path

import pytest

MEMBER_ROOT = Path(__file__).resolve().parents[1]
CONCIERGE_JS = MEMBER_ROOT / "js" / "account-concierge.js"
CONCIERGE_CSS = MEMBER_ROOT / "css" / "account-concierge.css"
MALL_VIDEO_PLAYER_JS = MEMBER_ROOT / "js" / "mall-video-player.js"
INDEX_HTML = MEMBER_ROOT / "index.html"
FOUNDUP_HTML = MEMBER_ROOT / "foundup.html"


# -- 1. account concierge host structure --


class TestAccountConciergeHost:

    def test_js_file_exists(self):
        assert CONCIERGE_JS.exists(), "account-concierge.js not found"

    def test_css_file_exists(self):
        assert CONCIERGE_CSS.exists(), "account-concierge.css not found"

    def test_js_is_iife(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "(function" in content, "Expected IIFE pattern"
        assert "})();" in content, "Expected IIFE closing"

    def test_js_loaded_in_index(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "js/account-concierge.js" in content, "index.html must load account-concierge.js"

    def test_css_loaded_in_index(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "css/account-concierge.css" in content, "index.html must load account-concierge.css"

    def test_account_plane_exists_in_html(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="accountPlane"' in content, "Account plane element must exist"

    def test_account_plane_scrim_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="accountPlaneScrim"' in content, "Account plane scrim must exist"

    def test_plane_has_aria_label(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'aria-label="Red Dog"' in content

    def test_plane_has_drag_handle(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "account-plane-handle" in content


# -- 2. identity/avatar affordance presence --


class TestIdentityAvatar:

    def test_avatar_area_in_plane(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "account-avatar" in content, "Avatar area must exist in account plane"

    def test_avatar_img_data_attr(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-account-avatar-img" in content, "Avatar image hook must exist"

    def test_avatar_placeholder_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "account-avatar-placeholder" in content, "Avatar placeholder must exist"

    def test_name_data_attr(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-account-name" in content, "Name hook must exist"

    def test_handle_data_attr(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-account-handle" in content, "Handle hook must exist"

    def test_avatar_link_for_profile_action(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-account-avatar-link" in content, "Avatar must be tappable for profile action"

    def test_avatar_trigger_in_header(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="mallAvatarTrigger"' in content, "Header must have avatar trigger button"

    def test_js_uses_clerk_image_url(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "imageUrl" in content, "JS must reference Clerk user imageUrl for avatar"

    def test_js_opens_clerk_profile(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "openUserProfile" in content, "Avatar tap must open Clerk user profile"

    def test_no_fake_upload_backend(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "upload" not in content.lower(), "Must not implement fake upload behavior"


# -- 3. FoundUps section naming and grid/tile structure --


class TestFoundUpsSection:

    def test_section_labeled_your_foundups(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert ">Your FoundUps<" in content, "Section must be labeled 'Your FoundUps'"

    def test_grid_container_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "account-foundups-grid" in content, "FoundUps grid container must exist"

    def test_css_defines_tile_grid(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert "account-foundups-grid" in content, "CSS must define grid layout"
        assert "grid-template-columns" in content, "Must use CSS grid for tile layout"

    def test_js_renders_tiles(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "account-foundup-tile" in content, "JS must render tile elements"
        assert "account-foundup-icon" in content, "JS must render icon elements"

    def test_tiles_are_links_to_entry(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "foundup.html?id=" in content, "Tiles must link to entry page"

    def test_tiles_show_readiness_status(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "account-foundup-status" in content, "Tiles must show readiness indicator"


# -- 4. invite codes hidden by default --


class TestInvitesHidden:

    def test_invites_toggle_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "account-invites-toggle" in content, "Invites toggle button must exist"

    def test_invites_drawer_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "account-invites-drawer" in content, "Invites drawer must exist"

    def test_drawer_hidden_by_default_in_css(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert "account-invites-drawer" in content
        assert "display: none" in content or "display:none" in content, "Drawer must be hidden by default"

    def test_drawer_open_class(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".account-invites-drawer.open" in content, "Must have .open class to reveal drawer"

    def test_js_toggles_drawer(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "invitesToggle" in content, "JS must reference invites toggle"
        assert "invitesDrawer" in content, "JS must reference invites drawer"

    def test_invite_codes_not_shown_in_plane_by_default(self):
        """The plane HTML should not contain any raw invite code text."""
        content = INDEX_HTML.read_text(encoding="utf-8")
        import re
        plane_match = re.search(
            r'id="accountPlane".*?</aside>',
            content,
            re.DOTALL,
        )
        assert plane_match, "Account plane aside must exist"
        plane_html = plane_match.group()
        assert "FUP-" not in plane_html, "No invite codes should be hardcoded in the plane"


# -- 5. options section contains sign out --


class TestOptionsSection:

    def test_options_section_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert ">Options<" in content, "Options section must exist"

    def test_signout_in_options(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-account-signout" in content, "Sign out button must exist in plane"

    def test_signout_label(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "Sign out" in content, "Sign out must be labeled"

    def test_signout_not_primary_action(self):
        """Sign out should be inside Options, not at top level of the plane."""
        content = INDEX_HTML.read_text(encoding="utf-8")
        import re
        plane_match = re.search(
            r'id="accountPlane".*?</aside>',
            content,
            re.DOTALL,
        )
        assert plane_match
        plane_html = plane_match.group()
        options_pos = plane_html.find(">Options<")
        signout_pos = plane_html.find("data-account-signout")
        assert options_pos < signout_pos, "Sign out must appear after Options section label"

    def test_js_handles_signout(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "signOut" in content, "JS must handle sign out action"


# -- 6. no regression to member entry flow --


class TestNoRegression:

    def test_index_has_loading_state(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "loadingState" in content

    def test_index_has_invite_gate(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "inviteGate" in content

    def test_index_has_username_modal(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "usernameModal" in content

    def test_index_has_member_area(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "memberArea" in content

    def test_index_has_clerk_auth(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "initClerkAuth" in content

    def test_index_has_red_dog_button(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "redDogBtn" in content

    def test_red_dog_concierge_still_loaded(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "js/red-dog-concierge.js" in content, "Red Dog concierge must still be loaded"

    def test_swipe_instructions_present(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "Swipe" in content, "Swipe instructions must be present"


# -- 7. Search Mall Concierge Wiring --


class TestSearchMallWiring:
    """Test Search Mall button wiring to field scope APIs."""

    def test_search_mall_button_exists(self):
        """Search Mall button exists in concierge."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert 'data-reddog-search-mall' in content

    def test_search_input_container_created(self):
        """Search input container is created."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert 'data-reddog-search-container' in content

    def test_search_input_created(self):
        """Search input field is created."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert 'data-reddog-search-input' in content

    def test_search_clear_button_created(self):
        """Search clear button is created."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert 'data-reddog-search-clear' in content

    def test_toggle_search_input_function(self):
        """toggleSearchInput function exists."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert 'function toggleSearchInput' in content

    def test_clear_search_function(self):
        """clearSearch function exists."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert 'function clearSearch' in content

    def test_search_wires_to_searchByCreator(self):
        """Search input wires to mallTileField.searchByCreator."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert 'searchByCreator' in content

    def test_clear_wires_to_clearFieldScope(self):
        """Clear search wires to mallTileField.clearFieldScope."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert 'clearFieldScope' in content

    def test_open_search_mall_api_wired(self):
        """openSearchMall API calls toggleSearchInput."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Find the openSearchMall function block
        import re
        # Match the function with its body (may span multiple lines)
        match = re.search(r'openSearchMall:\s*function\s*\(\s*\)\s*\{[\s\S]*?toggleSearchInput', content)
        assert match, "openSearchMall must call toggleSearchInput"


class TestSearchMallCSS:
    """Test Search Mall CSS styling."""

    def test_search_container_styles(self):
        """Search container has flex layout."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert '.reddog-search-container' in content

    def test_search_input_styles(self):
        """Search input has styling."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert '.reddog-search-input' in content

    def test_search_clear_styles(self):
        """Search clear button has styling."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert '.reddog-search-clear' in content

    def test_search_input_touch_target(self):
        """Search input has 44px min-height for WCAG touch target."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        # Check for min-height: 44px in search input
        assert 'min-height: 44px' in content


# -- 8. Category/Tag Filter UI --


class TestCategoryTagFilters:
    """Test Category and Tag filter UI."""

    def test_category_filter_html_created(self):
        """Category filter row is created."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert 'data-reddog-category-filters' in content

    def test_category_filter_pills(self):
        """Category filter pills are created."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert 'data-reddog-category=' in content

    def test_category_travel_exists(self):
        """Travel category filter exists."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "travel" in content and "data-reddog-category" in content

    def test_tag_select_created(self):
        """Tag select dropdown is created."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert 'data-reddog-tag-select' in content

    def test_tag_012_lane_option(self):
        """012-lane tag option exists."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert '012-lane' in content

    def test_category_filter_wires_to_api(self):
        """Category filter wires to mallTileField.filterByCategory."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert 'filterByCategory' in content

    def test_tag_filter_wires_to_api(self):
        """Tag filter wires to mallTileField.filterByTag."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert 'filterByTag' in content

    def test_category_emits_command(self):
        """Category filter emits reddog command."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "filter_category" in content

    def test_tag_emits_command(self):
        """Tag filter emits reddog command."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "filter_tag" in content

    def test_clear_search_clears_filters(self):
        """clearSearch clears category and tag filters."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Should clear category active states
        assert "data-reddog-category" in content
        # Should clear tag select
        assert "data-reddog-tag-select" in content


class TestCategoryTagCSS:
    """Test Category/Tag filter CSS."""

    def test_filter_row_styles(self):
        """Filter row has styling."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert '.reddog-filter-row' in content

    def test_filter_pill_styles(self):
        """Filter pill has styling."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert '.reddog-filter-pill' in content

    def test_filter_pill_active_state(self):
        """Filter pill has active state."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert '.reddog-filter-pill.active' in content

    def test_tag_select_styles(self):
        """Tag select has styling."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert '.reddog-tag-select' in content


# -- 9. Video Schema Status Sync --


class TestVideoSchemaStatusSync:
    """Test concierge counts .status-active (video catalog) not just .status-ready."""

    def test_summary_counts_active(self):
        """Summary builder counts .status-active."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert ".status-active" in content

    def test_summary_uses_active_label(self):
        """Summary displays 'active' not 'ready'."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # The summary line should say "N active"
        assert "active'" in content or 'active"' in content

    def test_context_has_activeCount(self):
        """gatherContext sets ctx.activeCount."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "ctx.activeCount" in content

    def test_no_stale_readyCount(self):
        """No remaining ctx.readyCount references."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "ctx.readyCount" not in content
        assert "readyCount:" not in content

    def test_selector_includes_legacy_fallback(self):
        """Status selector includes .status-ready as backward compat."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert ".status-active, .status-ready" in content

    def test_recommendation_uses_activeCount(self):
        """Recommendation test uses ctx.activeCount."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "ctx.activeCount > 0" in content

    def test_recommendation_label_updated(self):
        """Recommendation label says 'active' not 'ready'."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "View active FoundUps" in content

    def test_grid_renders_category_class(self):
        """Grid icon uses cat- prefix not theme- prefix."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "cat-'" in content or "cat-\"" in content

    def test_grid_renders_video_title(self):
        """Grid uses item.title as primary display name."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "item.title" in content

    def test_css_has_status_active(self):
        """CSS has .status-active class."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".status-active" in content

    def test_css_has_category_classes(self):
        """CSS has category-based icon classes."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".cat-travel" in content
        assert ".cat-music" in content
        assert ".cat-media" in content


# -- 10. Saved Videos Surface --


class TestSavedVideosSurface:
    """Test Saved Videos section in concierge."""

    def test_inject_saved_videos_function(self):
        """injectSavedVideos function exists."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function injectSavedVideos" in content

    def test_render_saved_videos_function(self):
        """renderSavedVideos function exists."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function renderSavedVideos" in content

    def test_reenter_saved_video_function(self):
        """reenterSavedVideo function exists."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function reenterSavedVideo" in content

    def test_saved_section_data_attr(self):
        """Saved section uses data-reddog-saved attribute."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-saved" in content

    def test_reads_getSavedVideos(self):
        """Reads from mallVideoPlayer.getSavedVideos."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "getSavedVideos" in content

    def test_saved_count_displayed(self):
        """Saved count badge is rendered."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog-saved-count" in content

    def test_empty_state_message(self):
        """Empty state message is present."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "No saved videos yet. Swipe left or use Save in the player to save a video." in content

    def test_saved_card_rendered(self):
        """Saved video cards are rendered."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog-saved-card" in content

    def test_saved_card_has_thumbnail(self):
        """Saved card includes thumbnail."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog-saved-thumb" in content

    def test_saved_card_has_title(self):
        """Saved card includes title."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog-saved-title" in content

    def test_reentry_uses_player_open(self):
        """Re-entry opens fullscreen player if queue available."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "player.open(" in content

    def test_reentry_fallback_to_entry_page(self):
        """Re-entry falls back to FoundUp entry page."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "foundup.html?id=" in content

    def test_reentry_emits_command(self):
        """Re-entry emits reddog command."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reenter_saved_video" in content

    def test_saved_mode_in_execute(self):
        """executeMode handles 'saved' case."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "case 'saved':" in content

    def test_open_saved_api(self):
        """openSaved function exposed in public API."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "openSaved:" in content

    def test_refresh_saved_api(self):
        """refreshSaved function exposed in public API."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "refreshSaved:" in content

    def test_injected_on_plane_open(self):
        """Saved videos injected when plane opens."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "injectSavedVideos()" in content


class TestSavedVideosCSS:
    """Test Saved Videos CSS."""

    def test_saved_section_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-saved-section" in content

    def test_saved_card_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-saved-card" in content

    def test_saved_thumb_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-saved-thumb" in content

    def test_saved_title_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-saved-title" in content

    def test_saved_empty_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-saved-empty" in content

    def test_saved_count_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-saved-count" in content


# -- Watch History Surface --


class TestWatchHistorySurface:
    """Test Watch History section in concierge."""

    def test_inject_watch_history_function(self):
        """injectWatchHistory function exists."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function injectWatchHistory" in content

    def test_render_watch_history_function(self):
        """renderWatchHistory function exists."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function renderWatchHistory" in content

    def test_reenter_history_video_function(self):
        """reenterHistoryVideo function exists."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function reenterHistoryVideo" in content

    def test_clear_watch_history_function(self):
        """clearWatchHistory function exists."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function clearWatchHistory" in content

    def test_history_section_data_attr(self):
        """History section uses data-reddog-history attribute."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-history" in content

    def test_reads_getHistory(self):
        """Reads from mallVideoPlayer.getHistory."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "getHistory" in content

    def test_history_count_displayed(self):
        """History count badge is rendered."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog-history-count" in content

    def test_empty_state_message(self):
        """Empty state message is present."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "No watch history yet. Videos you play will appear here." in content

    def test_history_card_rendered(self):
        """History video cards are rendered."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog-history-card" in content

    def test_history_card_has_thumbnail(self):
        """History card includes thumbnail."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog-history-thumb" in content

    def test_history_card_has_title(self):
        """History card includes title."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog-history-title" in content

    def test_reentry_uses_player_open(self):
        """Re-entry opens fullscreen player if queue available."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "player.open(" in content

    def test_reentry_fallback_to_entry_page(self):
        """Re-entry falls back to FoundUp entry page."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "foundup.html?id=" in content

    def test_reentry_emits_command(self):
        """Re-entry emits reddog command."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reenter_history_video" in content

    def test_history_mode_in_execute(self):
        """executeMode handles 'history' case."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "case 'history':" in content

    def test_open_history_api(self):
        """openHistory function exposed in public API."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "openHistory:" in content

    def test_refresh_history_api(self):
        """refreshHistory function exposed in public API."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "refreshHistory:" in content

    def test_clear_history_api(self):
        """clearHistory exposed in public API."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "clearHistory:" in content

    def test_clear_calls_player_api(self):
        """clearWatchHistory calls player.clearHistory."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "player.clearHistory()" in content

    def test_clear_button_rendered(self):
        """Clear button rendered when history exists."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-history-clear" in content

    def test_injected_on_plane_open(self):
        """Watch history injected when plane opens."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "injectWatchHistory()" in content


class TestWatchHistoryCSS:
    """Test Watch History CSS."""

    def test_history_section_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-history-section" in content

    def test_history_card_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-history-card" in content

    def test_history_thumb_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-history-thumb" in content

    def test_history_title_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-history-title" in content

    def test_history_empty_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-history-empty" in content

    def test_history_count_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-history-count" in content

    def test_history_clear_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-history-clear" in content

    def test_continue_badge_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-history-continue-badge" in content


class TestWatchHistoryResumePosition:
    """pfMALL_RESUME_POSITION_PHASE1 — shell-local continue-watching."""

    def test_format_continue_at_in_js(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function formatContinueAt" in content
        assert "Continue at" in content

    def test_history_card_continue_badge_markup(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog-history-continue-badge" in content
        assert "entry.playbackPosition" in content

    def test_video_player_close_refreshes_history(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "videoPlayerClose" in content
        assert "renderWatchHistory()" in content

    def test_reenter_passes_resume_to_open(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "resumeOpt" in content
        assert "player.open(foundupId, foundup.videos, startIdx, resumeOpt)" in content


class TestMallVideoPlayerResume:
    """Static checks on mall-video-player resume behavior."""

    def test_player_js_exists(self):
        assert MALL_VIDEO_PLAYER_JS.is_file()

    def test_resume_helpers_present(self):
        content = MALL_VIDEO_PLAYER_JS.read_text(encoding="utf-8")
        assert "MIN_RESUME_SECONDS" in content
        assert "COMPLETE_RATIO" in content
        assert "normalizeResumeSeconds" in content
        assert "mergeHistoryResume" in content
        assert "flushCurrentPlaybackPosition" in content
        assert "playbackPosition" in content

    def test_open_accepts_resume_opts(self):
        content = MALL_VIDEO_PLAYER_JS.read_text(encoding="utf-8")
        assert "resumeOpts" in content
        assert "pendingResumeSeconds" in content

    def test_embed_clears_resume(self):
        content = MALL_VIDEO_PLAYER_JS.read_text(encoding="utf-8")
        assert "cannot read playback time" in content or "resume N/A" in content
