#!/usr/bin/env python3
"""Tests for Red Dog mobile ergonomics phase 6.

Validates:
  1. avatar/account trigger meets phone-safe sizing
  2. Red Dog surface accounts for mobile spacing constraints
  3. mode sheet / plane remain usable on small screens
  4. current Red Dog interaction grammar still works
  5. no regression to briefing / recommendations / invites / options
"""

from pathlib import Path
import re

import pytest

MEMBER_ROOT = Path(__file__).resolve().parents[1]
CONCIERGE_JS = MEMBER_ROOT / "js" / "account-concierge.js"
CONCIERGE_CSS = MEMBER_ROOT / "css" / "account-concierge.css"
MEMBER_CSS = MEMBER_ROOT / "css" / "member.css"
INDEX_HTML = MEMBER_ROOT / "index.html"


# -- 1. avatar/account trigger meets phone-safe sizing --


class TestAvatarTouchTarget:

    def test_concierge_css_avatar_44px(self):
        """Account-concierge.css avatar trigger must be at least 44px."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        # Find the mall-avatar-trigger width in concierge CSS
        match = re.search(r'\.mall-avatar-trigger\s*\{[^}]*width:\s*(\d+)px', content)
        assert match, "Avatar trigger must have width defined"
        size = int(match.group(1))
        assert size >= 44, f"Avatar trigger {size}px is below 44px WCAG minimum"

    def test_concierge_css_avatar_img_44px(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        match = re.search(r'\.mall-avatar-trigger img\s*\{[^}]*width:\s*(\d+)px', content)
        assert match, "Avatar img must have width defined"
        size = int(match.group(1))
        assert size >= 44, f"Avatar img {size}px is below 44px minimum"

    def test_member_css_avatar_44px(self):
        """Member.css avatar trigger must be at least 44px."""
        content = MEMBER_CSS.read_text(encoding="utf-8")
        match = re.search(r'\.mall-avatar-trigger\s*\{[^}]*width:\s*(\d+)px', content)
        assert match, "Avatar trigger must have width defined in member.css"
        size = int(match.group(1))
        assert size >= 44, f"Member.css avatar trigger {size}px is below 44px minimum"

    def test_concierge_css_placeholder_44px(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        match = re.search(
            r'\.mall-avatar-trigger\s+\.account-avatar-placeholder\s*\{[^}]*width:\s*(\d+)px',
            content
        )
        assert match, "Placeholder must have width defined"
        size = int(match.group(1))
        assert size >= 44, f"Placeholder {size}px is below 44px minimum"


# -- 2. Red Dog surface accounts for mobile spacing --


class TestMobileSpacing:

    def test_small_screen_media_query_exists(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert "max-width: 480px" in content, "Must have small-screen media query"

    def test_plane_safe_area_padding(self):
        """Account plane must use safe-area insets."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert "safe-area-inset-left" in content, "Plane must handle left safe area"
        assert "safe-area-inset-right" in content, "Plane must handle right safe area"

    def test_landscape_media_query_exists(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert "max-height: 500px" in content, "Must have landscape media query"

    def test_small_screen_reduces_plane_padding(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        # Inside max-width: 480px, plane padding should be tighter
        assert "0.75rem" in content, "Small screen should use tighter padding"

    def test_small_screen_plane_max_height(self):
        """Plane should use more viewport on small screens."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert "90dvh" in content or "90vh" in content, "Small screen plane needs taller max-height"

    def test_option_buttons_min_height(self):
        """Option buttons must meet 44px tap target on phone."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert "account-option-btn" in content
        assert "min-height: 44px" in content, "Option buttons need 44px min-height"

    def test_invites_toggle_min_height(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert "account-invites-toggle" in content
        # Should appear in the 480px media query with min-height
        assert "min-height" in content

    def test_viewport_fit_cover(self):
        """Viewport meta must include viewport-fit=cover."""
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "viewport-fit=cover" in content

    def test_safe_area_variables_defined(self):
        """Root must define safe area CSS variables."""
        content = MEMBER_CSS.read_text(encoding="utf-8")
        assert "--safe-bottom" in content
        assert "--safe-top" in content

    def test_fab_uses_safe_area(self):
        """Red Dog FAB must account for safe area."""
        content = MEMBER_CSS.read_text(encoding="utf-8")
        assert "var(--safe-bottom)" in content


# -- 3. mode sheet / plane remain usable on small screens --


class TestModeSheetPhone:

    def test_mode_action_min_height(self):
        """Mode actions must meet 44px tap target on phone."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert "reddog-mode-action" in content
        # Check the 480px media query has min-height: 44px for mode actions
        mobile_block = content[content.find("max-width: 480px"):]
        assert "min-height: 44px" in mobile_block, "Mode actions need 44px min-height on phone"

    def test_mode_sheet_wider_on_phone(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert "min-width: 180px" in content, "Mode sheet should be wider on phone"

    def test_briefing_readable_on_phone(self):
        """Briefing text should be slightly larger on phone."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        mobile_block = content[content.find("max-width: 480px"):]
        assert "reddog-briefing-line" in mobile_block, "Briefing lines must have phone styles"

    def test_recommendation_pills_phone_sized(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        mobile_block = content[content.find("max-width: 480px"):]
        assert "reddog-rec-action" in mobile_block, "Rec pills must have phone styles"

    def test_landscape_plane_taller(self):
        """In landscape, plane should use more vertical space."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        landscape_block = content[content.find("max-height: 500px"):]
        assert "95dvh" in landscape_block or "95vh" in landscape_block


# -- 4. current Red Dog interaction grammar still works --


class TestInteractionGrammar:

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
        assert "stopListening" in content

    def test_pointer_cancel_guard(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "pointercancel" in content

    def test_pointer_leave_guard(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "pointerleave" in content

    def test_context_menu_prevented(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "contextmenu" in content

    def test_mode_sheet_swipe(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "anchorTouchStartY" in content
        assert "ANCHOR_SWIPE_THRESHOLD" in content

    def test_escape_closes(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "Escape" in content

    def test_scrim_closes(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "scrim.addEventListener" in content

    def test_signout_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "signOut" in content


# -- 5. no regression to briefing / recommendations / invites / options --


class TestNoRegression:

    def test_briefing_surface(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "renderBriefing" in content
        assert "data-reddog-briefing" in content

    def test_recommendations_surface(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "RECOMMENDATION_RULES" in content
        assert "data-reddog-recommendations" in content

    def test_get_context_api(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "getContext:" in content

    def test_get_recommendations_api(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "getRecommendations:" in content

    def test_run_recommendation_api(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "runRecommendation:" in content

    def test_mode_sheet_api(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "openModes:" in content
        assert "closeModes:" in content
        assert "isModeSheetOpen:" in content

    def test_set_identity_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "setIdentity:" in content

    def test_set_foundups_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "setFoundUps:" in content

    def test_set_invites_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "setInvites:" in content

    def test_window_reddog_api(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "window.redDog = api" in content

    def test_css_mode_sheet_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-mode-sheet" in content
        assert ".reddog-mode-action" in content

    def test_css_briefing_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-context-briefing" in content
        assert ".reddog-briefing-line" in content

    def test_css_recommendations_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-recommendations" in content
        assert ".reddog-rec-action" in content

    def test_css_desktop_query_preserved(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert "min-width: 640px" in content, "Desktop centering query must remain"
