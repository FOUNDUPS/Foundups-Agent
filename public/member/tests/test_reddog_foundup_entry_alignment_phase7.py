#!/usr/bin/env python3
"""Tests for Red Dog FoundUp entry alignment phase 7.

Validates:
  1. digital-twin identity replaces "Shell concierge"
  2. context briefing renders truthful FoundUp data
  3. recommended actions are local-only, no fake backend
  4. FAB state ring and visual alignment with Mall Red Dog
  5. window.entryRedDog API exposed
  6. red-dog-concierge.js entry topics updated
  7. no regression to existing entry shell or Mall Red Dog
"""

from pathlib import Path
import re

import pytest

MEMBER_ROOT = Path(__file__).resolve().parents[1]
FOUNDUP_HTML = MEMBER_ROOT / "foundup.html"
CONCIERGE_JS = MEMBER_ROOT / "js" / "red-dog-concierge.js"
ACCOUNT_CONCIERGE_JS = MEMBER_ROOT / "js" / "account-concierge.js"
ACCOUNT_CONCIERGE_CSS = MEMBER_ROOT / "css" / "account-concierge.css"


# -- 1. digital-twin identity --


class TestDigitalTwinIdentity:

    def test_subtitle_is_digital_twin(self):
        """Entry page must say 'Your digital twin', not 'Shell concierge'."""
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "Your digital twin" in content
        assert "Shell concierge" not in content

    def test_concierge_header_preserved(self):
        """Red Dog name must still appear in concierge header."""
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "concierge-name" in content
        assert "Red Dog" in content

    def test_logo_preserved(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "/logo-dog.png" in content

    def test_aria_label_present(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert 'aria-label="Red Dog concierge"' in content


# -- 2. context briefing --


class TestEntryBriefing:

    def test_briefing_container_exists(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "data-reddog-briefing" in content

    def test_briefing_body_element(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert 'id="entryBriefingBody"' in content

    def test_briefing_section_label(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "Briefing" in content

    def test_render_briefing_function(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "renderBriefing" in content

    def test_briefing_shows_name(self):
        """Briefing must reference FoundUp name from item data."""
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "item.name" in content

    def test_briefing_shows_readiness(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        # renderBriefing must include readiness
        briefing_block = content[content.find("renderBriefing"):]
        assert "readinessLabel" in briefing_block or "launch_readiness" in briefing_block

    def test_briefing_shows_token(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        briefing_block = content[content.find("renderBriefing"):]
        assert "token_symbol" in briefing_block

    def test_briefing_shows_lifecycle(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        briefing_block = content[content.find("renderBriefing"):]
        assert "lifecycle_stage" in briefing_block

    def test_briefing_shows_tier(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        briefing_block = content[content.find("renderBriefing"):]
        assert "item.tier" in briefing_block

    def test_briefing_shows_route(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        briefing_block = content[content.find("renderBriefing"):]
        assert "routing_prefix" in briefing_block

    def test_briefing_line_css(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "entry-briefing-line" in content

    def test_briefing_called_from_populate(self):
        """renderBriefing must be called when concierge context is populated."""
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        populate_block = content[content.find("populateConciergeContext"):]
        assert "renderBriefing" in populate_block


# -- 3. recommended actions --


class TestEntryRecommendations:

    def test_recommendations_container_exists(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "data-reddog-recommendations" in content

    def test_recommendations_body_element(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert 'id="entryRecsBody"' in content

    def test_section_label(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "Suggested actions" in content

    def test_return_to_mall_rec(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "return_to_mall" in content
        assert "Return to Mall" in content

    def test_scroll_readiness_rec(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "scroll_readiness" in content
        assert "Review readiness" in content

    def test_scroll_about_rec(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "scroll_about" in content
        assert "View about" in content

    def test_copy_link_rec(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "copy_link" in content
        assert "Copy link" in content

    def test_rec_pills_css(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "entry-rec-action" in content
        assert "border-radius: 999px" in content

    def test_rec_row_flex_wrap(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "entry-recs-row" in content
        assert "flex-wrap" in content

    def test_render_recommendations_function(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "renderRecommendations" in content

    def test_recommendations_called_from_populate(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        populate_block = content[content.find("populateConciergeContext"):]
        assert "renderRecommendations" in populate_block

    def test_scroll_uses_smooth_behavior(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "behavior: 'smooth'" in content

    def test_copy_uses_clipboard_api(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "navigator.clipboard" in content

    def test_no_backend_calls_in_recs(self):
        """Recommendations must not fetch or call any backend."""
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        rec_block = content[content.find("ENTRY_RECOMMENDATIONS"):]
        rec_block = rec_block[:rec_block.find("renderRecommendations")]
        assert "fetch(" not in rec_block
        assert "XMLHttpRequest" not in rec_block

    def test_rec_phone_min_height(self):
        """Rec pills must get 44px min-height on phone."""
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        mobile_block = content[content.find("max-width: 480px"):]
        assert "entry-rec-action" in mobile_block
        assert "min-height: 44px" in mobile_block

    def test_closeConcierge_on_scroll_actions(self):
        """Scroll actions should close concierge before scrolling."""
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "closeConcierge();" in content
        assert "scrollIntoView" in content


# -- 4. FAB state ring and visual alignment --


class TestFABAlignment:

    def test_fab_state_ring_css(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert ".entry-red-dog.active" in content
        assert "box-shadow" in content[content.find(".entry-red-dog.active"):]

    def test_fab_toggle_adds_active_class(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "'active'" in content
        toggle_block = content[content.find("toggleConcierge"):]
        assert "active" in toggle_block

    def test_close_removes_active_class(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        close_block = content[content.find("closeConcierge"):]
        assert "remove('active')" in close_block

    def test_fab_meets_wcag_minimum(self):
        """FAB must be at least 44px."""
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        match = re.search(r'\.entry-red-dog\s*\{[^}]*width:\s*(\d+)px', content)
        assert match, "FAB must have explicit width"
        assert int(match.group(1)) >= 44

    def test_fab_safe_area(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "safe-bottom" in content
        assert "safe-area-inset-right" in content

    def test_fab_gradient_preserved(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "linear-gradient" in content
        fab_block = content[content.find(".entry-red-dog {"):]
        assert "#7c5cfc" in fab_block


# -- 5. window.entryRedDog API --


class TestEntryRedDogAPI:

    def test_api_exposed(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "window.entryRedDog" in content

    def test_api_open(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        api_block = content[content.find("window.entryRedDog"):]
        assert "open:" in api_block

    def test_api_close(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        api_block = content[content.find("window.entryRedDog"):]
        assert "close:" in api_block

    def test_api_toggle(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        api_block = content[content.find("window.entryRedDog"):]
        assert "toggle:" in api_block

    def test_api_is_open(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        api_block = content[content.find("window.entryRedDog"):]
        assert "isOpen:" in api_block

    def test_api_get_context(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        api_block = content[content.find("window.entryRedDog"):]
        assert "getContext:" in api_block

    def test_get_context_returns_page_entry(self):
        """getEntryContext must set page to 'entry'."""
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        ctx_block = content[content.find("getEntryContext"):]
        assert "page: 'entry'" in ctx_block

    def test_get_context_includes_foundup_id(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        ctx_block = content[content.find("getEntryContext"):]
        assert "foundupId" in ctx_block


# -- 6. red-dog-concierge.js entry topics --


class TestConciergeTopicsUpdated:

    def test_who_is_red_dog_topic_on_entry(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        entry_block = content[content.find("isEntryPage"):]
        assert "Who is Red Dog?" in entry_block

    def test_digital_twin_language_in_topic(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "digital twin" in content

    def test_suggested_actions_reference(self):
        """How do I go back topic should reference suggested actions."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "suggested actions" in content

    def test_entry_topics_count(self):
        """Entry page should have 4 topics."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Find the entry topics array between "isEntryPage ? [" and "] : []"
        marker = "isEntryPage ? ["
        start = content.find(marker)
        assert start != -1, "Entry topics block not found"
        entry_block = content[start:]
        entry_block = entry_block[:entry_block.find("] : []")]
        q_count = entry_block.count("q: '")
        assert q_count == 4, f"Expected 4 entry topics, got {q_count}"


# -- 7. no regression --


class TestNoRegression:

    def test_entry_shell_structure_preserved(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "entry-shell" in content
        assert "entryContent" in content
        assert "conciergeSheet" in content

    def test_entry_back_link_preserved(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "Back to Mall" in content

    def test_return_to_mall_link_preserved(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "Return to Mall" in content

    def test_catalog_fetch_preserved(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "mall-video-catalog.json" in content

    def test_render_entry_preserved(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "renderEntry" in content

    def test_escape_closes_preserved(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "Escape" in content

    def test_scrim_closes_preserved(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "conciergeScrim" in content

    def test_readiness_labels_preserved(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "READINESS_LABELS" in content

    def test_concierge_js_still_loaded(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "red-dog-concierge.js" in content

    def test_viewport_fit_cover(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "viewport-fit=cover" in content

    def test_mall_red_dog_api_untouched(self):
        """Mall account-concierge.js must still expose window.redDog."""
        content = ACCOUNT_CONCIERGE_JS.read_text(encoding="utf-8")
        assert "window.redDog = api" in content

    def test_mall_briefing_untouched(self):
        content = ACCOUNT_CONCIERGE_JS.read_text(encoding="utf-8")
        assert "renderBriefing" in content
        assert "data-reddog-briefing" in content

    def test_mall_recommendations_untouched(self):
        content = ACCOUNT_CONCIERGE_JS.read_text(encoding="utf-8")
        assert "RECOMMENDATION_RULES" in content
        assert "data-reddog-recommendations" in content

    def test_concierge_js_mall_topics_untouched(self):
        """Mall topics in red-dog-concierge.js must be preserved."""
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "What is the Mall?" in content
        assert "How do I browse?" in content

    def test_concierge_js_page_detection_preserved(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "isMallPage" in content
        assert "isEntryPage" in content
