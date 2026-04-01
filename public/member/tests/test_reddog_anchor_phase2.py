#!/usr/bin/env python3
"""Tests for Red Dog agent anchor phase 2.

Validates:
  1. Red Dog anchor wrapper is present
  2. tap opens unified plane (existing behavior preserved)
  3. double-tap quick summary exists
  4. press-and-hold placeholder state exists
  5. anchor state ring and visual states
  6. protected close/recovery controls still work
  7. no regression to unified user plane
"""

from pathlib import Path

import pytest

MEMBER_ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = MEMBER_ROOT / "index.html"
CONCIERGE_JS = MEMBER_ROOT / "js" / "account-concierge.js"
CONCIERGE_CSS = MEMBER_ROOT / "css" / "account-concierge.css"
MEMBER_CSS = MEMBER_ROOT / "css" / "member.css"


# -- 1. Red Dog anchor wrapper --


class TestAnchorPresence:

    def test_anchor_wrapper_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="redDogAnchor"' in content, "Anchor wrapper must exist"

    def test_anchor_has_data_attr(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-anchor" in content, "Anchor must have data hook"

    def test_red_dog_btn_inside_anchor(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        anchor_pos = content.find('id="redDogAnchor"')
        btn_pos = content.find('id="redDogBtn"')
        assert anchor_pos < btn_pos, "Button must be inside anchor wrapper"

    def test_anchor_css_exists(self):
        content = MEMBER_CSS.read_text(encoding="utf-8")
        assert ".red-dog-anchor" in content, "Anchor CSS must exist"


# -- 2. tap opens unified plane --


class TestTapBehavior:

    def test_trigger_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="redDogBtn"' in content

    def test_trigger_has_reddog_trigger_attr(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-trigger" in content

    def test_js_wires_pointer_events(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "pointerdown" in content, "Must use pointerdown for tap detection"
        assert "pointerup" in content, "Must use pointerup for tap detection"

    def test_js_has_toggle_plane(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "togglePlane" in content, "Must have togglePlane function"

    def test_js_has_double_tap_window(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "DOUBLE_TAP_WINDOW" in content, "Must define double-tap timing window"


# -- 3. double-tap quick summary --


class TestQuickSummary:

    def test_summary_element_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="redDogSummary"' in content, "Summary element must exist"

    def test_summary_has_data_attr(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-summary" in content

    def test_summary_content_slot(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-summary-content" in content, "Summary content slot must exist"

    def test_summary_hidden_by_default(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        import re
        match = re.search(r'id="redDogSummary"[^>]*', content)
        assert match, "Summary element must exist"
        assert "hidden" in match.group(), "Summary must be hidden by default"

    def test_js_has_show_summary(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "showSummary" in content, "Must have showSummary function"

    def test_js_has_dismiss_summary(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "dismissSummary" in content, "Must have dismissSummary function"

    def test_summary_css_exists(self):
        content = MEMBER_CSS.read_text(encoding="utf-8")
        assert ".red-dog-summary" in content, "Summary CSS must exist"

    def test_summary_no_network(self):
        """Summary must be shell-owned with no backend calls."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "fetch(" not in content, "Concierge must not make network calls"

    def test_api_exposes_summary(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "showSummary:" in content or "showSummary :" in content, \
            "window.redDog must expose showSummary"


# -- 4. press-and-hold placeholder --


class TestPushToTalk:

    def test_listening_element_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="redDogListening"' in content, "Listening element must exist"

    def test_listening_has_data_attr(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-listening" in content

    def test_listening_hidden_by_default(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        import re
        match = re.search(r'id="redDogListening"[^>]*', content)
        assert match, "Listening element must exist"
        assert "hidden" in match.group(), "Listening indicator must be hidden by default"

    def test_listening_label_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "Listening" in content, "Listening label must exist"

    def test_listening_waves_exist(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "red-dog-listening-waves" in content, "Wave animation elements must exist"

    def test_js_has_hold_threshold(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "HOLD_THRESHOLD" in content, "Must define hold timing threshold"

    def test_js_has_start_listening(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "startListening" in content

    def test_js_has_stop_listening(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "stopListening" in content

    def test_listening_css_exists(self):
        content = MEMBER_CSS.read_text(encoding="utf-8")
        assert ".red-dog-listening" in content, "Listening CSS must exist"

    def test_no_transcription_backend(self):
        """Push-to-talk is visual placeholder only."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        lower = content.lower()
        assert "websocket" not in lower, "No WebSocket for voice"
        assert "mediarecorder" not in lower, "No audio recording"
        assert "speechrecognition" not in lower, "No speech API"

    def test_api_exposes_listening(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "startListening:" in content or "startListening :" in content, \
            "window.redDog must expose startListening"


# -- 5. anchor state ring --


class TestStateRing:

    def test_state_ring_in_html(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "red-dog-state-ring" in content, "State ring element must exist"

    def test_state_ring_data_attr(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-reddog-anchor-state" in content

    def test_default_state_is_idle(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'data-reddog-anchor-state="idle"' in content, "Default state must be idle"

    def test_css_has_idle_state(self):
        content = MEMBER_CSS.read_text(encoding="utf-8")
        assert 'anchor-state="idle"' in content

    def test_css_has_active_state(self):
        content = MEMBER_CSS.read_text(encoding="utf-8")
        assert 'anchor-state="active"' in content

    def test_css_has_listening_state(self):
        content = MEMBER_CSS.read_text(encoding="utf-8")
        assert 'anchor-state="listening"' in content

    def test_js_sets_anchor_state(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "setAnchorState" in content, "Must have setAnchorState function"

    def test_api_exposes_anchor_state(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "anchorState:" in content or "anchorState :" in content, \
            "window.redDog must expose anchorState"


# -- 6. protected close/recovery controls --


class TestProtectedControls:

    def test_escape_closes_plane(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "Escape" in content

    def test_scrim_closes_plane(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "scrim" in content.lower()

    def test_signout_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "data-account-signout" in content

    def test_signout_label(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "Sign out" in content

    def test_signout_wired(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "signOut" in content

    def test_pointer_cancel_stops_listening(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "pointercancel" in content, "Must handle pointercancel to stop listening"

    def test_pointer_leave_stops_listening(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "pointerleave" in content, "Must handle pointerleave to stop listening"

    def test_context_menu_prevented(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "contextmenu" in content, "Must prevent context menu on long press"


# -- 7. no regression to unified user plane --


class TestNoRegression:

    def test_plane_exists(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'id="accountPlane"' in content

    def test_plane_has_reddog_label(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert 'aria-label="Red Dog"' in content

    def test_window_reddog_api(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "window.redDog" in content

    def test_index_has_loading_state(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "loadingState" in content

    def test_index_has_invite_gate(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "inviteGate" in content

    def test_index_has_member_area(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "memberArea" in content

    def test_index_has_clerk_auth(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "initClerkAuth" in content

    def test_reddog_concierge_loaded(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "js/red-dog-concierge.js" in content

    def test_account_concierge_loaded(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "js/account-concierge.js" in content

    def test_mall_tile_field_present(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "mallTileField" in content

    def test_data_reddog_hooks_intact(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        for hook in ["data-reddog-plane", "data-reddog-identity", "data-reddog-foundups",
                      "data-reddog-invites", "data-reddog-options", "data-reddog-concierge",
                      "data-reddog-state", "data-reddog-trigger", "data-reddog-greeting"]:
            assert hook in content, f"Hook {hook} must still be present"
