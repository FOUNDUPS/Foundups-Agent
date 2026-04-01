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
