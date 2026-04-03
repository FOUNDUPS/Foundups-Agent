#!/usr/bin/env python3
"""Tests for search mall concierge wiring phase 1 (WSP 97).

Validates:
  1. Creator search pill wires to real search input
  2. Search Mall button wires to real search input
  3. Search input calls B's searchByCreator API
  4. Clear search calls B's clearFieldScope API
  5. Public API: searchByCreator, clearSearch, openSearchMall
  6. typeof guards on all B API calls
  7. No regression to existing concierge
"""

from pathlib import Path

import pytest

MEMBER_ROOT = Path(__file__).resolve().parents[1]
CONCIERGE_JS = MEMBER_ROOT / "js" / "account-concierge.js"
CONCIERGE_CSS = MEMBER_ROOT / "css" / "account-concierge.css"
TILE_FIELD_JS = MEMBER_ROOT / "js" / "mall-tile-field.js"


# -- 1. Creator search pill wiring --


class TestCreatorSearchPill:

    def test_creator_pill_exists(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-creator-search" in content

    def test_creator_pill_emits_command(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "emitRedDogCommand('search_creator'" in content

    def test_creator_pill_injects_channels(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Creator pill click handler should inject channels
        handler_block = content[content.find("if (creatorBtn)"):]
        handler_block = handler_block[:handler_block.find("return;")]
        assert "injectChannels()" in handler_block

    def test_creator_pill_toggles_search_input(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        handler_block = content[content.find("if (creatorBtn)"):]
        handler_block = handler_block[:handler_block.find("return;")]
        assert "toggleSearchInput(true)" in handler_block


# -- 2. Search Mall button wiring --


class TestSearchMallButton:

    def test_search_mall_button_exists(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-search-mall" in content
        assert "Search Mall" in content

    def test_search_mall_emits_command(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "emitRedDogCommand('open_search_mall'" in content

    def test_search_mall_toggles_search_input(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Find the click handler, not the markup
        search_block = content[content.find("closest('[data-reddog-search-mall]')"):]
        search_block = search_block[:search_block.find("return;")]
        assert "toggleSearchInput(true)" in search_block


# -- 3. Search input calls B's real API --


class TestSearchInputWiring:

    def test_search_input_exists(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-search-input" in content

    def test_search_input_calls_search_by_creator(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "mallTileField.searchByCreator(" in content

    def test_search_input_clears_on_empty(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "mallTileField.clearFieldScope()" in content

    def test_escape_clears_search(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "'Escape'" in content
        assert "clearSearch()" in content

    def test_search_clear_button_exists(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-search-clear" in content

    def test_toggle_search_input_function(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function toggleSearchInput(" in content

    def test_clear_search_function(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function clearSearch()" in content

    def test_clear_search_resets_input(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        clear_block = content[content.find("function clearSearch()"):]
        clear_block = clear_block[:clear_block.find("}")]
        assert "input.value = ''" in clear_block

    def test_clear_search_hides_container(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        clear_block = content[content.find("function clearSearch()"):]
        clear_block = clear_block[:600]
        assert "toggleSearchInput(false)" in clear_block

    def test_clear_search_calls_clear_field_scope(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        clear_block = content[content.find("function clearSearch()"):]
        clear_block = clear_block[:700]
        assert "clearFieldScope" in clear_block


# -- 4. typeof guards --


class TestTypeofGuards:

    def test_search_by_creator_guard(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "typeof window.mallTileField.searchByCreator" in content

    def test_clear_field_scope_guard(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "typeof window.mallTileField.clearFieldScope" in content


# -- 5. Public API extensions --


class TestPublicAPISearch:

    def test_api_open_search_mall(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_def = content[content.find("var api = {"):]
        assert "openSearchMall:" in api_def

    def test_api_open_search_mall_injects_channels(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_block = content[content.find("openSearchMall:"):]
        api_block = api_block[:api_block.find("},")]
        assert "injectChannels()" in api_block

    def test_api_open_search_mall_toggles_input(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_block = content[content.find("openSearchMall:"):]
        api_block = api_block[:api_block.find("},")]
        assert "toggleSearchInput(true)" in api_block

    def test_api_search_by_creator(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_def = content[content.find("var api = {"):]
        assert "searchByCreator:" in api_def

    def test_api_search_by_creator_calls_b(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_block = content[content.find("searchByCreator: function"):]
        api_block = api_block[:api_block.find("},")]
        assert "mallTileField.searchByCreator(" in api_block

    def test_api_search_by_creator_typeof_guard(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_block = content[content.find("searchByCreator: function"):]
        api_block = api_block[:api_block.find("},")]
        assert "typeof" in api_block

    def test_api_clear_search(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_def = content[content.find("var api = {"):]
        assert "clearSearch:" in api_def

    def test_no_set_projection_search(self):
        """Confirm we don't call setProjection('search') — it's not a valid value."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "setProjection('search')" not in content


# -- 6. B's real search API exists --


class TestBSearchAPIExists:

    def test_b_search_by_creator(self):
        content = TILE_FIELD_JS.read_text(encoding="utf-8")
        assert "searchByCreator:" in content

    def test_b_filter_by_category(self):
        content = TILE_FIELD_JS.read_text(encoding="utf-8")
        assert "filterByCategory:" in content

    def test_b_filter_by_tag(self):
        content = TILE_FIELD_JS.read_text(encoding="utf-8")
        assert "filterByTag:" in content

    def test_b_clear_field_scope(self):
        content = TILE_FIELD_JS.read_text(encoding="utf-8")
        assert "clearFieldScope:" in content

    def test_b_get_field_scope(self):
        content = TILE_FIELD_JS.read_text(encoding="utf-8")
        assert "getFieldScope:" in content


# -- 7. CSS for search --


class TestSearchCSS:

    def test_search_container_class(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-search-container" in content

    def test_search_input_class(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-search-input" in content

    def test_search_input_44px(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        input_block = content[content.find(".reddog-search-input {"):]
        input_block = input_block[:input_block.find("}")]
        assert "min-height: 44px" in input_block

    def test_search_clear_button_class(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-search-clear" in content

    def test_search_clear_44px(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        clear_block = content[content.find(".reddog-search-clear {"):]
        clear_block = clear_block[:clear_block.find("}")]
        assert "min-width: 44px" in clear_block
        assert "min-height: 44px" in clear_block

    def test_search_placeholder_styled(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-search-input::placeholder" in content


# -- 8. No regression --


class TestNoRegression:

    def test_window_reddog_api(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "window.redDog = api" in content

    def test_personal_mall_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "projectPersonalMall()" in content

    def test_channel_attachment_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "toggleChannelAttach" in content
        assert "attachedChannels" in content

    def test_ai_tools_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-tools" in content
        assert "CATEGORIES" in content

    def test_briefing_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "renderBriefing" in content

    def test_mode_sheet_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "injectModeSheet" in content

    def test_original_modes_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "id: 'channels'" in content
        assert "id: 'tools'" in content
        assert "id: 'summary'" in content
