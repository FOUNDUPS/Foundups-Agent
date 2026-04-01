#!/usr/bin/env python3
"""Tests for concierge channel attachment phase 1 (WSP 97).

Validates:
  1. channels mode action in mode sheet
  2. channel list rendering from catalog data
  3. attach/detach toggle hooks
  4. Mall projection quick-switch hooks
  5. window.redDog API extensions for channels
  6. CSS for channel section
  7. truthful hooks (no fake backend)
  8. no regression to existing concierge
"""

from pathlib import Path

import pytest

MEMBER_ROOT = Path(__file__).resolve().parents[1]
CONCIERGE_JS = MEMBER_ROOT / "js" / "account-concierge.js"
CONCIERGE_CSS = MEMBER_ROOT / "css" / "account-concierge.css"


# -- 1. Channels mode action --


class TestChannelsModeAction:

    def test_channels_in_mode_actions(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "id: 'channels'" in content
        assert "label: 'Channels'" in content

    def test_channels_mode_has_icon(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        lines = [l for l in content.splitlines() if "'channels'" in l and "icon:" in l]
        assert len(lines) >= 1

    def test_execute_mode_handles_channels(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "case 'channels':" in content

    def test_channels_opens_plane(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        ch_block = content[content.find("case 'channels':"):]
        ch_block = ch_block[:ch_block.find("break;")]
        assert "openPlane()" in ch_block

    def test_channels_injects_section(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        ch_block = content[content.find("case 'channels':"):]
        ch_block = ch_block[:ch_block.find("break;")]
        assert "injectChannels()" in ch_block

    def test_channels_scrolls_to_section(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        ch_block = content[content.find("case 'channels':"):]
        ch_block = ch_block[:ch_block.find("break;")]
        assert "data-reddog-channels" in ch_block
        assert "scrollIntoView" in ch_block


# -- 2. Channel list rendering --


class TestChannelListRendering:

    def test_channel_platforms_defined(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "CHANNEL_PLATFORMS" in content

    def test_youtube_platform(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "youtube_channel" in content

    def test_linkedin_platform(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "linkedin_profile" in content

    def test_x_platform(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "x_account" in content

    def test_autopost_platform(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "autopost" in content

    def test_get_channels_from_catalog(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function getChannelsFromCatalog()" in content

    def test_reads_stored_catalog(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "storedCatalog" in content

    def test_channel_row_markup(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-channel" in content
        assert "reddog-channel-row" in content

    def test_channel_shows_video_count(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "videoCount" in content
        assert "videos" in content

    def test_channel_shows_source_handle(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "sourceHandle" in content

    def test_inject_channels_function(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function injectChannels()" in content

    def test_set_foundups_stores_catalog(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        set_block = content[content.find("setFoundUps:"):]
        set_block = set_block[:set_block.find("},")]
        assert "storedCatalog" in set_block

    def test_channels_injected_on_plane_open(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        open_block = content[content.find("_origOpenPlane"):]
        assert "injectChannels()" in open_block

    def test_channel_list_container(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-channel-list" in content


# -- 3. Attach/detach toggle --


class TestAttachDetachToggle:

    def test_toggle_function(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function toggleChannelAttach(" in content

    def test_toggle_emits_attach_command(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "attach_channel" in content

    def test_toggle_emits_detach_command(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "detach_channel" in content

    def test_toggle_button_in_markup(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-channel-toggle" in content

    def test_toggle_uses_attached_class(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "attached" in content

    def test_attached_channels_state(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "attachedChannels" in content


# -- 4. Mall projection quick-switch --


class TestMallProjectionHooks:

    def test_populate_my_mall_button(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-populate-mall" in content
        assert "Populate My Mall" in content

    def test_personal_mall_button(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-personal-mall" in content
        assert "Personal Mall" in content

    def test_search_mall_button(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-search-mall" in content
        assert "Search Mall" in content

    def test_populate_emits_command(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "populate_my_mall" in content

    def test_personal_mall_emits_command(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "open_personal_mall" in content

    def test_search_mall_emits_command(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "open_search_mall" in content

    def test_personal_mall_uses_real_b_api(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Should call projectPersonalMall() — not setProjection('personal')
        assert "projectPersonalMall()" in content
        assert "setProjection('personal')" not in content

    def test_search_mall_emits_only(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Search Mall scope not yet landed by B — emit command only
        assert "setProjection('search')" not in content

    def test_projection_typeof_guard(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Personal Mall calls should be guarded with typeof checks
        populate_block = content[content.find("populate_my_mall"):]
        assert "typeof" in populate_block[:200]
        assert "projectPersonalMall" in populate_block[:200]


# -- 5. window.redDog API extensions --


class TestRedDogAPIChannels:

    def test_api_open_channels(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_def = content[content.find("var api = {"):]
        assert "openChannels:" in api_def

    def test_api_get_channels(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_def = content[content.find("var api = {"):]
        assert "getChannels:" in api_def

    def test_api_toggle_channel(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_def = content[content.find("var api = {"):]
        assert "toggleChannel:" in api_def

    def test_api_populate_my_mall(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_def = content[content.find("var api = {"):]
        assert "populateMyMall:" in api_def

    def test_api_open_personal_mall(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_def = content[content.find("var api = {"):]
        assert "openPersonalMall:" in api_def

    def test_api_open_search_mall(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        api_def = content[content.find("var api = {"):]
        assert "openSearchMall:" in api_def


# -- 6. CSS for channel section --


class TestChannelCSS:

    def test_channels_section_class(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-channels-section" in content

    def test_channel_row_class(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-channel-row" in content

    def test_channel_icon_class(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-channel-icon" in content

    def test_channel_info_flex(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-channel-info" in content

    def test_channel_name_class(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-channel-name" in content

    def test_channel_meta_class(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-channel-meta" in content

    def test_channel_toggle_class(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-channel-toggle" in content

    def test_channel_toggle_attached_state(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-channel-toggle.attached" in content

    def test_channel_actions_class(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-channel-actions" in content

    def test_phone_channel_row_44px(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        mobile_block = content[content.find("max-width: 480px"):]
        assert "reddog-channel-row" in mobile_block
        assert "min-height: 44px" in mobile_block


# -- 7. Truthful hooks --


class TestTruthfulHooks:

    def test_no_fake_ai_in_channels(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        ch_block = content[content.find("channel attachment"):]
        ch_block = ch_block[:ch_block.find("context briefing")]
        assert "AI says" not in ch_block
        assert "I think" not in ch_block

    def test_no_fetch_in_channels(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        ch_block = content[content.find("channel attachment"):]
        ch_block = ch_block[:ch_block.find("context briefing")]
        assert "fetch(" not in ch_block
        assert "XMLHttpRequest" not in ch_block

    def test_all_commands_use_emit(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # attach/detach use variable action: emitRedDogCommand(action, ...)
        assert "'attach_channel'" in content
        assert "'detach_channel'" in content
        assert "emitRedDogCommand(action" in content
        assert "emitRedDogCommand('populate_my_mall'" in content
        assert "emitRedDogCommand('open_personal_mall'" in content
        assert "emitRedDogCommand('open_search_mall'" in content


# -- 8. No regression --


class TestNoRegression:

    def test_window_reddog_api(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "window.redDog = api" in content

    def test_ai_tools_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-tools" in content
        assert "CATEGORIES" in content
        assert "DENSITY_PRESETS" in content

    def test_briefing_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "renderBriefing" in content

    def test_recommendations_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "RECOMMENDATION_RULES" in content

    def test_mode_sheet_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "injectModeSheet" in content

    def test_original_modes_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "id: 'summary'" in content
        assert "id: 'listen'" in content
        assert "id: 'tools'" in content
        assert "id: 'foundups'" in content
        assert "id: 'invites'" in content
        assert "id: 'options'" in content

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

    def test_css_ai_tools_preserved(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-ai-tools" in content

    def test_css_mode_sheet_preserved(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert ".reddog-mode-sheet" in content

    def test_css_desktop_query_preserved(self):
        content = CONCIERGE_CSS.read_text(encoding="utf-8")
        assert "min-width: 640px" in content
