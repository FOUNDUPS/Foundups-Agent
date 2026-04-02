#!/usr/bin/env python3
"""Tests for Red Dog unified user plane (phase 1 unification).

Validates:
  1. unified plane structure (Red Dog owns the surface)
  2. duplicate concierge/account concepts are removed
  3. Red Dog primary affordance is present
  4. protected controls remain visible/recoverable
  5. no regression to account-plane entry/exit flow
  6. no regression to member entry flow
  7. command-surface hooks for future SoftProto
"""

from pathlib import Path

import pytest

MEMBER_ROOT = Path(__file__).resolve().parents[1]
CONCIERGE_JS = MEMBER_ROOT / "js" / "account-concierge.js"
REDDOG_JS = MEMBER_ROOT / "js" / "red-dog-concierge.js"
CONCIERGE_CSS = MEMBER_ROOT / "css" / "account-concierge.css"
INDEX_HTML = MEMBER_ROOT / "index.html"
FOUNDUP_HTML = MEMBER_ROOT / "foundup.html"


# -- 1. unified plane structure --


class TestUnifiedPlaneStructure:

    def test_plane_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="accountPlane"' in content

    def test_plane_has_reddog_label(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'aria-label="Red Dog"' in content, "Plane must identify as Red Dog"

    def test_plane_has_reddog_plane_hook(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-plane" in content

    def test_reddog_header_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "reddog-header" in content, "Red Dog header must exist in plane"

    def test_reddog_header_has_name(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "Red Dog" in content

    def test_reddog_header_has_greeting_slot(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-greeting" in content

    def test_reddog_state_hook(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-state" in content, "State display slot must exist"


# -- 2. duplicate concepts removed --


class TestDuplicatesRemoved:

    def test_no_separate_reddog_panel(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="redDogPanel"' not in content, "Old Red Dog panel must be removed"

    def test_no_agent_handle_element(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="agentHandle"' not in content, "Old agent handle must be removed"

    def test_no_agent_email_element(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="agentEmail"' not in content, "Old agent email must be removed"

    def test_no_agent_invite_codes_element(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="agentInviteCodes"' not in content, "Old invite codes display must be removed"

    def test_no_agent_message_element(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="agentMessage"' not in content, "Old agent message must be removed"

    def test_no_old_logout_btn(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="logoutBtn"' not in content, "Old logout button must be removed"

    def test_no_old_concierge_label(self):
        """The old generic 'Concierge' section label should be replaced."""
        content = INDEX_HTML.read_text(encoding="utf-8")
        import re
        plane_match = re.search(
            r'id="accountPlane".*?</aside>',
            content,
            re.DOTALL,
        )
        assert plane_match
        plane_html = plane_match.group()
        assert ">Concierge<" not in plane_html, "Old 'Concierge' label must be replaced with 'Red Dog'"


# -- 3. Red Dog primary affordance --


class TestRedDogPrimary:

    def test_reddog_trigger_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="redDogBtn"' in content

    def test_reddog_trigger_has_hook(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-trigger" in content

    def test_reddog_trigger_opens_plane(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "redDogBtn" in content, "JS must wire Red Dog trigger"
        assert "redDogTrigger" in content, "JS must reference Red Dog trigger"

    def test_js_exposes_reddog_api(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "window.redDog" in content, "Must expose window.redDog API"

    def test_reddog_concierge_section(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-concierge" in content, "Red Dog concierge section must exist"

    def test_reddog_guidance_items(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "reddog-guidance-item" in content, "Guidance items must use Red Dog framing"

    def test_concierge_js_digital_twin_framing(self):
        content = REDDOG_JS.read_text(encoding="utf-8")
        assert "personal agent" in content.lower() or "red dog" in content.lower(), \
            "Concierge JS must use digital twin framing"


# -- 4. protected controls remain visible/recoverable --


class TestProtectedControls:

    def test_signout_exists_in_plane(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-account-signout" in content, "Sign out must remain in plane"

    def test_signout_label(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "Sign out" in content

    def test_signout_after_options(self):
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
        assert options_pos < signout_pos, "Sign out must appear after Options"

    def test_signout_wired_in_js(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "signOut" in content

    def test_escape_closes_plane(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "Escape" in content, "Escape key must close the plane"

    def test_scrim_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="accountPlaneScrim"' in content

    def test_scrim_closes_plane(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "scrim" in content.lower()

    def test_avatar_trigger_still_in_header(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="mallAvatarTrigger"' in content

    def test_avatar_trigger_opens_plane(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "avatarTrigger" in content


# -- 5. no regression to account-plane entry/exit --


class TestAccountPlaneFlow:

    def test_swipe_down_opens(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "touchstart" in content
        assert "touchend" in content

    def test_swipe_up_closes(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "SWIPE_THRESHOLD" in content

    def test_plane_has_open_class_pattern(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".account-plane.open" in content

    def test_identity_block_present(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-identity" in content

    def test_foundups_section_present(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-foundups" in content

    def test_invites_section_present(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-invites" in content

    def test_invites_hidden_by_default(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert "account-invites-drawer" in content
        assert "display: none" in content or "display:none" in content


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

    def test_red_dog_btn_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "redDogBtn" in content

    def test_red_dog_concierge_loaded(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "js/red-dog-concierge.js" in content

    def test_account_concierge_loaded(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "js/account-concierge.js" in content

    def test_foundup_page_still_works(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "entryRedDog" in content
        assert "conciergeSheet" in content
        assert "Back to Mall" in content


# -- 7. command-surface hooks --


class TestCommandSurfaceHooks:

    def test_plane_hook(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-plane" in content

    def test_identity_hook(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-identity" in content

    def test_foundups_hook(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-foundups" in content

    def test_invites_hook(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-invites" in content

    def test_options_hook(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-options" in content

    def test_concierge_hook(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-concierge" in content

    def test_state_hook(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-state" in content

    def test_trigger_hook(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-trigger" in content

    def test_greeting_hook(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-greeting" in content
