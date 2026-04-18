#!/usr/bin/env python3
"""Tests for Red Dog Mall controls phase 1 (WSP 97).

Validates:
  1. AI Tools mode action exists in mode sheet
  2. category projection controls
  3. creator/entity projection hook
  4. density preset controls
  5. Snap / Glide motion mode toggle
  6. truthful command hooks (no fake backend)
  7. window.redDog API extensions
  8. CSS for AI tools section
  9. no regression to existing Red Dog behaviors
"""

from pathlib import Path
import re

import pytest

MEMBER_ROOT = Path(__file__).resolve().parents[1]
CONCIERGE_JS = MEMBER_ROOT / "js" / "account-concierge.js"
CONCIERGE_CSS = MEMBER_ROOT / "css" / "account-concierge.css"


# -- 1. AI Tools mode action --


class TestAIToolsModeAction:

    def test_tools_in_mode_actions(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "id: 'tools'" in content
        assert "label: 'AI Tools'" in content

    def test_tools_mode_has_icon(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # The tools mode action should have an icon field
        tools_line = [l for l in content.splitlines() if "'tools'" in l and "icon:" in l]
        assert len(tools_line) >= 1

    def test_execute_mode_handles_tools(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "case 'tools':" in content

    def test_tools_opens_plane(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        tools_block = content[content.find("case 'tools':"):]
        tools_block = tools_block[:tools_block.find("break;")]
        assert "openPlane()" in tools_block

    def test_tools_injects_ai_tools(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        tools_block = content[content.find("case 'tools':"):]
        tools_block = tools_block[:tools_block.find("break;")]
        assert "injectAITools()" in tools_block

    def test_tools_scrolls_to_section(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        tools_block = content[content.find("case 'tools':"):]
        tools_block = tools_block[:tools_block.find("break;")]
        assert "data-reddog-tools" in tools_block
        assert "scrollIntoView" in tools_block


# -- 2. Category projection controls --


class TestCategoryProjection:

    def test_categories_defined(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "CATEGORIES" in content

    def test_category_all(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "id: 'all'" in content

    def test_category_startups(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "id: 'startups'" in content

    def test_category_travel(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "id: 'travel'" in content

    def test_category_music(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "id: 'music'" in content

    def test_category_food(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "id: 'food'" in content

    def test_category_tech(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "id: 'tech'" in content

    def test_set_category_function(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function setCategory(" in content

    def test_category_all_resets_projection(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        set_cat = content[content.find("function setCategory("):]
        assert "resetProjection" in set_cat

    def test_category_uses_set_projection(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        set_cat = content[content.find("function setCategory("):]
        assert "setProjection" in set_cat

    def test_category_typeof_guard(self):
        """Must guard mallTileField with typeof check."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        set_cat = content[content.find("function setCategory("):]
        set_cat = set_cat[:set_cat.find("\n  function ")]
        assert "window.mallTileField" in set_cat
        assert "typeof" in set_cat

    def test_category_pills_in_tools(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-category" in content

    def test_default_category_is_all(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "currentCategory = 'all'" in content


# -- 3. Creator/entity projection hook --


class TestCreatorEntityHook:

    def test_creator_search_button(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-creator-search" in content

    def test_creator_search_emits_command(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "search_creator" in content


# -- 4. Density preset controls --


class TestDensityPresets:

    def test_density_presets_defined(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "DENSITY_PRESETS" in content

    def test_density_4x6(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "id: '4x6'" in content

    def test_density_3x4(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "id: '3x4'" in content

    def test_density_3x5(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "id: '3x5'" in content

    def test_density_5x8(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "id: '5x8'" in content

    def test_set_density_function(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function setDensity(" in content

    def test_density_calls_mall_api(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        set_den = content[content.find("function setDensity("):]
        assert "mallTileField.setDensity" in set_den

    def test_density_typeof_guard(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        set_den = content[content.find("function setDensity("):]
        set_den = set_den[:set_den.find("\n  function ")]
        assert "typeof" in set_den

    def test_density_pills_in_tools(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-density" in content

    def test_default_density_is_3x5(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "currentDensity = '3x5'" in content


# -- 5. Snap / Glide motion mode --


class TestMotionMode:

    def test_set_motion_mode_function(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function setMotionMode(" in content

    def test_snap_option(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-motion=\"snap\"" in content

    def test_glide_option(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-motion=\"glide\"" in content

    def test_default_motion_is_snap(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "currentMotionMode = 'snap'" in content

    def test_motion_calls_mall_api(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        set_mot = content[content.find("function setMotionMode("):]
        assert "mallTileField.setMotionMode" in set_mot

    def test_motion_typeof_guard(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        set_mot = content[content.find("function setMotionMode("):]
        set_mot = set_mot[:set_mot.find("\n  function ")]
        assert "typeof" in set_mot

    def test_motion_emits_command(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        set_mot = content[content.find("function setMotionMode("):]
        assert "set_motion_mode" in set_mot


# -- 6. Truthful command hooks --


class TestTruthfulHooks:

    def test_reddog_command_event(self):
        """All controls emit reddog:command CustomEvent."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog:command" in content
        assert "CustomEvent" in content

    def test_emit_function_exists(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function emitRedDogCommand(" in content

    def test_no_fake_ai_responses(self):
        """AI tools must not contain fake AI responses or hallucinated data."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        tools_block = content[content.find("injectAITools"):]
        # Should not have fake chat messages, AI responses, or hallucinated content
        assert "AI says" not in tools_block
        assert "I think" not in tools_block
        assert "Based on my analysis" not in tools_block

    def test_no_fetch_in_tools(self):
        """AI tools must not make backend calls."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        tools_block = content[content.find("injectAITools"):]
        tools_block = tools_block[:tools_block.find("// ---- context briefing")]
        assert "fetch(" not in tools_block
        assert "XMLHttpRequest" not in tools_block

    def test_set_projection_emits_command(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "set_projection" in content

    def test_set_density_emits_command(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "set_density" in content

    def test_briefing_shows_category(self):
        """Briefing should reflect current category when not 'all'."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        briefing_block = content[content.find("function renderBriefing("):]
        assert "currentCategory" in briefing_block

    def test_briefing_shows_density(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        briefing_block = content[content.find("function renderBriefing("):]
        assert "currentDensity" in briefing_block

    def test_briefing_shows_motion(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        briefing_block = content[content.find("function renderBriefing("):]
        assert "currentMotionMode" in briefing_block


# -- 7. window.redDog API extensions --


class TestRedDogAPIExtensions:

    def test_api_open_tools(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_block = content[content.find("window.redDog = api"):]
        # Check the api object definition
        api_def = content[content.find("var api = {"):]
        assert "openTools:" in api_def

    def test_api_set_category(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_def = content[content.find("var api = {"):]
        assert "setCategory:" in api_def

    def test_api_get_category(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_def = content[content.find("var api = {"):]
        assert "getCategory:" in api_def

    def test_api_set_density(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_def = content[content.find("var api = {"):]
        assert "setDensity:" in api_def

    def test_api_get_density(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_def = content[content.find("var api = {"):]
        assert "getDensity:" in api_def

    def test_api_set_motion_mode(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_def = content[content.find("var api = {"):]
        assert "setMotionMode:" in api_def

    def test_api_get_motion_mode(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_def = content[content.find("var api = {"):]
        assert "getMotionMode:" in api_def


# -- 8. CSS for AI tools --


class TestAIToolsCSS:

    def test_ai_tools_class(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-ai-tools" in content

    def test_tools_group_class(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-tools-group" in content

    def test_tools_label_class(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-tools-label" in content

    def test_tools_row_flex_wrap(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-tools-row" in content
        # The row should use flex-wrap
        row_idx = content.find(".reddog-tools-row")
        row_block = content[row_idx:content.find("}", row_idx) + 1]
        assert "flex-wrap" in row_block

    def test_tool_pill_class(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-tool-pill" in content

    def test_tool_pill_border_radius(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        pill_idx = content.find(".reddog-tool-pill {")
        if pill_idx == -1:
            pill_idx = content.find(".reddog-tool-pill{")
        pill_block = content[pill_idx:content.find("}", pill_idx) + 1]
        assert "border-radius: 999px" in pill_block

    def test_tool_pill_active_state(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-tool-pill.active" in content

    def test_density_pill_mono_font(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-density-pill" in content
        den_idx = content.find(".reddog-density-pill")
        den_block = content[den_idx:content.find("}", den_idx) + 1]
        assert "mono" in den_block.lower() or "Mono" in den_block

    def test_motion_pill_min_width(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-motion-pill" in content

    def test_phone_tool_pill_44px(self):
        """Tool pills must get 44px min-height on phone."""
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        mobile_block = content[content.find("max-width: 480px"):]
        assert "reddog-tool-pill" in mobile_block
        assert "min-height: 44px" in mobile_block


# -- 9. No regression --


class TestNoRegression:

    def test_window_reddog_api(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "window.redDog = api" in content

    def test_toggle_plane_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "togglePlane" in content

    def test_show_summary_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "showSummary" in content

    def test_start_listening_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "startListening" in content

    def test_mode_sheet_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "injectModeSheet" in content

    def test_original_mode_actions_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "id: 'summary'" in content
        assert "id: 'listen'" in content
        assert "id: 'foundups'" in content
        assert "id: 'invites'" in content
        assert "id: 'options'" in content

    def test_briefing_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "renderBriefing" in content
        assert "data-reddog-briefing" in content

    def test_recommendations_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "RECOMMENDATION_RULES" in content
        assert "data-reddog-recommendations" in content

    def test_set_identity_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "setIdentity:" in content

    def test_set_foundups_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "setFoundUps:" in content

    def test_set_invites_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "setInvites:" in content

    def test_signout_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "signOut" in content

    def test_escape_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "Escape" in content

    def test_scrim_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "scrim.addEventListener" in content

    def test_css_mode_sheet_preserved(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-mode-sheet" in content

    def test_css_briefing_preserved(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-context-briefing" in content

    def test_css_desktop_query_preserved(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert "min-width: 640px" in content


# ═══════════════════════════════════════════════
# RedDog Density Policy Enforcement (Hardening)
# ═══════════════════════════════════════════════

class TestRedDogDensityPolicyEnforcement:
    """RedDog uses requestDensity for device policy enforcement."""

    def test_set_density_uses_request_density(self):
        """setDensity function uses mallTileField.requestDensity."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "mallTileField.requestDensity" in content

    def test_request_density_source_reddog(self):
        """requestDensity is called with source: 'reddog'."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "source: 'reddog'" in content or 'source: "reddog"' in content

    def test_density_rejection_handled(self):
        """Rejected density requests are handled."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "result.applied" in content or "!result.applied" in content

    def test_density_rejection_logged(self):
        """Rejected density requests are logged."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "Density rejected" in content

    def test_density_rejected_command_emitted(self):
        """density_rejected command is emitted on rejection."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "density_rejected" in content

    def test_fallback_to_set_density(self):
        """Falls back to setDensity if requestDensity unavailable."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "mallTileField.setDensity" in content
