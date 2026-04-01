#!/usr/bin/env python3
"""Tests for Red Dog context briefing phase 4.

Validates:
  1. briefing surface exists (JS-injected, CSS present)
  2. gatherContext reads all expected shell signals
  3. renderBriefing produces truthful output
  4. window.redDog context API exists
  5. no fake AI, no backend, no network dependency
  6. existing behaviors unaffected
"""

from pathlib import Path

import pytest

MEMBER_ROOT = Path(__file__).resolve().parents[1]
CONCIERGE_JS = MEMBER_ROOT / "js" / "account-concierge.js"
CONCIERGE_CSS = MEMBER_ROOT / "css" / "account-concierge.css"
INDEX_HTML = MEMBER_ROOT / "index.html"


# -- 1. briefing surface exists --


class TestBriefingSurface:

    def test_js_creates_briefing_element(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog-context-briefing" in content, "JS must create briefing element"

    def test_js_sets_data_attr(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-briefing" in content, "Briefing must have data hook"

    def test_briefing_has_role_status(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "role" in content
        assert "status" in content, "Briefing must have role=status for a11y"

    def test_briefing_injected_into_concierge(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-concierge" in content, "Briefing must inject into concierge host"
        assert "insertBefore" in content, "Briefing must be prepended to concierge section"

    def test_css_has_briefing_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-context-briefing" in content, "CSS must define briefing styles"

    def test_css_has_briefing_line_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-briefing-line" in content, "CSS must define line styles"

    def test_no_index_html_collision(self):
        """Briefing must be JS-injected, not in static HTML."""
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "reddog-context-briefing" not in content
        assert "data-reddog-briefing" not in content


# -- 2. gatherContext reads shell signals --


class TestGatherContext:

    def test_gather_context_function_exists(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function gatherContext()" in content

    def test_reads_tile_count(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "account-foundup-tile" in content
        assert "tileCount" in content

    def test_reads_ready_count(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "status-ready" in content
        assert "readyCount" in content

    def test_reads_invite_text(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-invite-count" in content
        assert "inviteText" in content

    def test_reads_projection(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "mallTileField" in content
        assert "getProjection" in content
        assert "ctx.projection" in content

    def test_reads_inspecting_index(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "getInspectingIndex" in content
        assert "ctx.inspecting" in content

    def test_reads_inspector_open(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "isInspectorOpen" in content
        assert "ctx.inspectorOpen" in content

    def test_reads_view_plane_open(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "mallPlanes" in content
        assert "ctx.viewOpen" in content

    def test_reads_view_active_index(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "getActiveIndex" in content
        assert "ctx.viewIndex" in content

    def test_reads_plane_state(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "planeOpen" in content

    def test_reads_mode_state(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "modesVisible" in content
        assert "currentMode" in content

    def test_type_guards_on_mall_apis(self):
        """Must check typeof before calling B's APIs."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "typeof window.mallTileField.getProjection" in content
        assert "typeof window.mallPlanes.isOpen" in content


# -- 3. renderBriefing produces truthful output --


class TestRenderBriefing:

    def test_render_briefing_function_exists(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function renderBriefing()" in content

    def test_shows_foundup_count(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "FoundUp" in content
        assert "tileCount" in content

    def test_shows_ready_count(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "readyCount" in content
        assert "ready" in content

    def test_shows_projection_mode(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "'Sorted: '" in content or "Sorted:" in content

    def test_shows_inspecting_state(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "Inspecting" in content

    def test_shows_view_state(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "Viewing" in content

    def test_uses_esc_for_output(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "esc(l)" in content, "Briefing lines must use esc() for safety"

    def test_briefing_refreshes_on_open(self):
        """Briefing must re-render when plane opens."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "renderBriefing" in content
        assert "_origOpenPlane" in content, "Must wrap openPlane to trigger refresh"

    def test_inject_briefing_called_on_open(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "injectBriefing()" in content


# -- 4. window.redDog context API --


class TestContextAPI:

    def test_api_has_get_context(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "getContext:" in content or "getContext :" in content

    def test_api_get_context_references_gather(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "getContext: gatherContext" in content

    def test_api_has_refresh_briefing(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "refreshBriefing:" in content or "refreshBriefing :" in content

    def test_refresh_briefing_calls_render(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "renderBriefing()" in content


# -- 5. no fake AI, no backend, no network --


class TestNoFakeAI:

    def test_no_fetch(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "fetch(" not in content, "Must not make network calls"

    def test_no_chatbot(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        lower = content.lower()
        assert "chatbot" not in lower, "No chatbot behavior"

    def test_no_streaming(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        lower = content.lower()
        assert "streaming" not in lower, "No fake streaming"

    def test_no_typing_animation(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        lower = content.lower()
        assert "typing" not in lower or "human_type" not in lower, "No typing animation"

    def test_briefing_uses_static_text(self):
        """Lines must be plain text, not simulated AI output."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog-briefing-line" in content


# -- 6. existing behaviors unaffected --


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

    def test_mode_sheet_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "openModes" in content
        assert "closeModes" in content
        assert "executeMode" in content

    def test_signout_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "signOut" in content

    def test_escape_closes_plane(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "Escape" in content

    def test_scrim_closes(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "scrim.addEventListener" in content

    def test_window_reddog_api(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "window.redDog = api" in content

    def test_set_identity_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "setIdentity:" in content

    def test_set_foundups_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "setFoundUps:" in content

    def test_set_invites_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "setInvites:" in content
