#!/usr/bin/env python3
"""Tests for Red Dog recommended actions phase 5.

Validates:
  1. recommendation surface exists (JS-injected, CSS present)
  2. recommendations derive from real shell state
  3. recommendation actions trigger truthful shell behaviors
  4. window.redDog recommendation API exists
  5. no fake AI, no backend, no network dependency
  6. briefing/mode-sheet/existing behaviors still work
"""

from pathlib import Path

import pytest

MEMBER_ROOT = Path(__file__).resolve().parents[1]
CONCIERGE_JS = MEMBER_ROOT / "js" / "account-concierge.js"
CONCIERGE_CSS = MEMBER_ROOT / "css" / "account-concierge.css"
INDEX_HTML = MEMBER_ROOT / "index.html"


# -- 1. recommendation surface exists --


class TestRecommendationSurface:

    def test_js_creates_recommendations_element(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog-recommendations" in content

    def test_js_sets_data_attr(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-recommendations" in content

    def test_js_sets_aria_label(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "Recommended actions" in content

    def test_recommendations_injected_into_concierge(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-concierge" in content

    def test_recommendations_after_briefing(self):
        """Recommendations should be inserted after the briefing block."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-briefing" in content
        assert "briefing.nextSibling" in content

    def test_css_has_recommendations_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-recommendations" in content

    def test_css_has_action_button_styles(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-rec-action" in content

    def test_css_has_hover_state(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-rec-action:hover" in content

    def test_css_has_active_state(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-rec-action:active" in content

    def test_css_pill_shape(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert "border-radius: 999px" in content

    def test_no_index_html_collision(self):
        """Recommendations must be JS-injected, not in static HTML."""
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "reddog-recommendations" not in content
        assert "data-reddog-recommendations" not in content

    def test_recommendations_refresh_on_open(self):
        """Must re-render when plane opens."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "renderRecommendations()" in content
        assert "injectRecommendations()" in content


# -- 2. recommendations derive from real shell state --


class TestRecommendationRules:

    def test_recommendation_rules_array(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "RECOMMENDATION_RULES" in content

    def test_max_recommendations_capped(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "MAX_RECOMMENDATIONS" in content

    def test_rule_return_to_mall(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "'return_to_mall'" in content
        assert "Return to Mall" in content

    def test_rule_enter_foundup(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "'enter_foundup'" in content
        assert "Enter FoundUp" in content

    def test_rule_reset_projection(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "'reset_projection'" in content
        assert "Reset to All" in content

    def test_rule_view_ready(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "'view_ready'" in content
        assert "View ready FoundUps" in content

    def test_rule_open_invites(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "'open_invites'" in content
        assert "Check Invites" in content

    def test_rule_view_foundups(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "'view_foundups'" in content
        assert "View My FoundUps" in content

    def test_rule_show_summary(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "'show_summary'" in content
        assert "Show Summary" in content

    def test_rules_use_context(self):
        """Each rule must test against gatherContext output."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function (ctx)" in content or "function(ctx)" in content

    def test_rules_check_view_open(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "ctx.viewOpen" in content

    def test_rules_check_inspector(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "ctx.inspectorOpen" in content

    def test_rules_check_projection(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "ctx.projection" in content

    def test_rules_check_ready_count(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "ctx.readyCount" in content

    def test_rules_check_tile_count(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "ctx.tileCount" in content


# -- 3. recommendation actions trigger truthful shell behaviors --


class TestRecommendationActions:

    def test_return_to_mall_calls_close_view(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "mallPlanes.closeView" in content

    def test_enter_foundup_calls_enter(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "mallTileField.enterFoundUp" in content

    def test_reset_projection_calls_reset(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "mallTileField.resetProjection" in content

    def test_view_ready_sets_projection(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "setProjection" in content
        assert "'readiness'" in content

    def test_open_invites_uses_execute_mode(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "executeMode('invites')" in content

    def test_view_foundups_uses_execute_mode(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "executeMode('foundups')" in content

    def test_show_summary_calls_show(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "showSummary()" in content

    def test_actions_type_guard_mall_apis(self):
        """Must typeof-check before calling B's mutating APIs."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "typeof window.mallPlanes.closeView" in content
        assert "typeof window.mallTileField.resetProjection" in content

    def test_run_recommendation_refreshes(self):
        """After running an action, must refresh both recs and briefing."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # runRecommendation should call renderRecommendations and renderBriefing
        assert "renderRecommendations()" in content
        assert "renderBriefing()" in content

    def test_buttons_use_data_attr(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-rec=" in content

    def test_delegated_click_handler(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "recsEl.addEventListener('click'" in content

    def test_uses_esc_for_labels(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "esc(r.label)" in content or "esc(r.id)" in content


# -- 4. window.redDog recommendation API --


class TestRecommendationAPI:

    def test_api_has_get_recommendations(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "getRecommendations:" in content or "getRecommendations :" in content

    def test_api_has_run_recommendation(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "runRecommendation:" in content or "runRecommendation :" in content

    def test_api_has_refresh_recommendations(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "refreshRecommendations:" in content or "refreshRecommendations :" in content

    def test_get_recommendations_returns_array(self):
        """Must build array from rules."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "var recs = []" in content

    def test_run_recommendation_takes_id(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function runRecommendation(id)" in content


# -- 5. no fake AI, no backend, no network --


class TestNoFakeAI:

    def test_no_fetch(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "fetch(" not in content

    def test_no_chatbot(self):
        lower = CONCIERGE_JS.read_text(encoding="utf-8").lower()
        assert "chatbot" not in lower

    def test_no_streaming(self):
        lower = CONCIERGE_JS.read_text(encoding="utf-8").lower()
        assert "streaming" not in lower

    def test_no_ml_model(self):
        lower = CONCIERGE_JS.read_text(encoding="utf-8").lower()
        assert "tensorflow" not in lower
        assert "model.predict" not in lower

    def test_no_localstorage_persistence(self):
        """Recommendations are ephemeral, no persistence."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "localStorage" not in content


# -- 6. briefing/mode-sheet/existing behaviors still work --


class TestExistingBehaviors:

    def test_briefing_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "renderBriefing" in content
        assert "injectBriefing" in content
        assert "data-reddog-briefing" in content

    def test_mode_sheet_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "openModes" in content
        assert "closeModes" in content
        assert "executeMode" in content
        assert "data-reddog-mode-sheet" in content

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

    def test_get_context_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "getContext:" in content

    def test_refresh_briefing_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "refreshBriefing:" in content
