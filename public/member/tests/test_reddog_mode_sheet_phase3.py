#!/usr/bin/env python3
"""Tests for Red Dog mode sheet phase 3.

Validates:
  1. mode sheet surface exists (JS-injected, CSS present)
  2. local Red Dog gesture opens mode sheet
  3. mode actions are present
  4. window.redDog mode-sheet API exists
  5. existing tap/double-tap/hold behaviors still work
  6. Mall/global gestures remain unaffected
"""

from pathlib import Path

import pytest

MEMBER_ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = MEMBER_ROOT / "index.html"
CONCIERGE_JS = MEMBER_ROOT / "js" / "account-concierge.js"
CONCIERGE_CSS = MEMBER_ROOT / "css" / "account-concierge.css"


# -- 1. mode sheet surface exists --


class TestModeSheetSurface:

    def test_js_creates_mode_sheet_element(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog-mode-sheet" in content, "JS must create mode sheet element"

    def test_js_sets_data_attr(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-mode-sheet" in content, "Mode sheet must have data hook"

    def test_js_injects_into_anchor(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "anchor.insertBefore" in content, "Mode sheet must be injected into anchor"

    def test_css_has_mode_sheet_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-mode-sheet" in content, "CSS must define mode sheet styles"

    def test_css_has_animation(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert "reddog-mode-in" in content, "Mode sheet must have entry animation"

    def test_mode_sheet_hidden_by_default(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "modeSheetEl.hidden = true" in content, "Mode sheet must be hidden on creation"

    def test_no_index_html_collision(self):
        """Mode sheet must be JS-injected, not in index.html markup."""
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "reddog-mode-sheet" not in content, "Mode sheet must not be in static HTML"


# -- 2. local Red Dog gesture opens mode sheet --


class TestLocalGesture:

    def test_anchor_touchstart_handler(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "anchorTouchStartY" in content, "Must track anchor touch start"

    def test_anchor_swipe_threshold(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "ANCHOR_SWIPE_THRESHOLD" in content, "Must define anchor swipe threshold"

    def test_swipe_up_opens_modes(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "openModes" in content, "Swipe up must call openModes"

    def test_swipe_down_closes_modes(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "closeModes" in content, "Swipe down must call closeModes"

    def test_gesture_is_local_to_anchor(self):
        """Swipe detection must be on anchor element, not Mall body."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # The anchor touchstart must reference the anchor var, not mallShell
        assert "anchor.addEventListener('touchstart'" in content

    def test_escape_closes_mode_sheet(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Must have escape handler that checks modesVisible
        assert "modesVisible" in content
        assert "Escape" in content


# -- 3. mode actions are present --


class TestModeActions:

    def test_summary_action(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "'summary'" in content

    def test_listen_action(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "'listen'" in content

    def test_foundups_action(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "'foundups'" in content

    def test_invites_action(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "'invites'" in content

    def test_options_action(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "'options'" in content

    def test_actions_use_data_attr(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-mode=" in content, "Actions must use data-reddog-mode attribute"

    def test_execute_mode_function(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "executeMode" in content, "Must have executeMode dispatcher"

    def test_css_has_action_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-mode-action" in content, "CSS must define action button styles"

    def test_css_has_hover_state(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-mode-action:hover" in content, "Actions must have hover state"

    def test_no_network_dependency(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "fetch(" not in content, "Mode actions must not make network calls"

    def test_no_fake_ai(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        lower = content.lower()
        assert "chatbot" not in lower, "No chatbot behavior"
        assert "streaming" not in lower, "No fake streaming"


# -- 4. window.redDog mode-sheet API --


class TestModeSheetAPI:

    def test_api_has_open_modes(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "openModes:" in content or "openModes :" in content

    def test_api_has_close_modes(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "closeModes:" in content or "closeModes :" in content

    def test_api_has_toggle_modes(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "toggleModes:" in content or "toggleModes :" in content

    def test_api_has_set_mode(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "setMode:" in content or "setMode :" in content

    def test_api_has_current_mode(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "currentMode:" in content or "currentMode :" in content

    def test_api_has_is_mode_sheet_open(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "isModeSheetOpen:" in content or "isModeSheetOpen :" in content


# -- 5. existing behaviors still work --


class TestExistingBehaviors:

    def test_tap_toggle_plane(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "togglePlane" in content

    def test_double_tap_summary(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "DOUBLE_TAP_WINDOW" in content
        assert "showSummary" in content

    def test_hold_listening(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "HOLD_THRESHOLD" in content
        assert "startListening" in content

    def test_pointer_events_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "pointerdown" in content
        assert "pointerup" in content

    def test_scrim_closes(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "scrim.addEventListener" in content

    def test_escape_closes_plane(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "Escape" in content

    def test_signout_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "signOut" in content

    def test_window_reddog_api(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "window.redDog = api" in content


# -- 6. Mall/global gestures unaffected --


class TestNoGlobalConflict:

    def test_mall_swipe_down_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "mallShell" in content, "Mall swipe-down handler must remain"

    def test_swipe_up_on_plane_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "plane.addEventListener('touchstart'" in content, "Plane swipe-up must remain"

    def test_anchor_gesture_uses_separate_vars(self):
        """Anchor swipe must use its own tracking vars, not Mall's."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "anchorTouchStartY" in content
        assert "anchorTouchCurrentY" in content
        assert "anchorSwiping" in content

    def test_no_global_touchstart_hijack(self):
        """Must not add touchstart on document or body."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "document.addEventListener('touchstart'" not in content
        assert "document.body.addEventListener('touchstart'" not in content
