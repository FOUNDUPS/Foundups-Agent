#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Red Dog concierge phase 1.

Verifies that the concierge surface exists on both Mall and FoundUp
entry pages, contains readiness explanations, and is context-aware.
"""

import re
from pathlib import Path

import pytest

MEMBER_DIR = Path(__file__).resolve().parents[4] / "public" / "member"
INDEX_PAGE = MEMBER_DIR / "index.html"
ENTRY_PAGE = MEMBER_DIR / "foundup.html"
MEMBER_CSS = MEMBER_DIR / "css" / "member.css"


# ---------------------------------------------------------------------------
# Mall page — Red Dog concierge
# ---------------------------------------------------------------------------

class TestMallRedDogConcierge:
    """Red Dog concierge on the Mall page (index.html) — account-concierge unified plane."""

    def test_red_dog_button_exists(self):
        html = INDEX_PAGE.read_text(encoding="utf-8")
        assert "redDogBtn" in html
        assert 'aria-label' in html.split("redDogBtn")[1][:200]

    def test_red_dog_plane_exists(self):
        """Account plane (unified Red Dog surface) exists."""
        html = INDEX_PAGE.read_text(encoding="utf-8")
        assert "accountPlane" in html
        assert "data-reddog-plane" in html

    def test_red_dog_header_present(self):
        """Red Dog header with name and greeting exists."""
        html = INDEX_PAGE.read_text(encoding="utf-8")
        assert "reddog-header-name" in html
        assert "Red Dog" in html
        assert "data-reddog-greeting" in html

    def test_navigation_guidance_present(self):
        """Red Dog concierge contains gesture guidance matching runtime truth."""
        html = INDEX_PAGE.read_text(encoding="utf-8")
        assert "reddog-concierge-guidance" in html
        assert "Tap a tile to play" in html
        assert "Double-tap to enter" in html

    def test_identity_section_present(self):
        """Account identity section exists in the plane."""
        html = INDEX_PAGE.read_text(encoding="utf-8")
        assert "data-reddog-identity" in html

    def test_foundups_section_present(self):
        """FoundUps section exists in the plane."""
        html = INDEX_PAGE.read_text(encoding="utf-8")
        assert "data-reddog-foundups" in html

    def test_options_section_present(self):
        """Options section (sign out, etc.) exists in the plane."""
        html = INDEX_PAGE.read_text(encoding="utf-8")
        assert "data-reddog-options" in html


# ---------------------------------------------------------------------------
# FoundUp entry page — Red Dog concierge
# ---------------------------------------------------------------------------

class TestEntryRedDogConcierge:
    """Red Dog concierge on the FoundUp entry page (foundup.html)."""

    def test_red_dog_button_exists(self):
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "entryRedDog" in html
        assert "entry-red-dog" in html

    def test_concierge_sheet_exists(self):
        """A concierge sheet/panel exists in the markup."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "conciergeSheet" in html
        assert "concierge-sheet" in html

    def test_concierge_scrim_exists(self):
        """Overlay scrim exists for dismissal."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "conciergeScrim" in html
        assert "concierge-scrim" in html

    def test_concierge_has_red_dog_header(self):
        """Concierge sheet shows Red Dog identity."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "Red Dog" in html
        assert "concierge-name" in html

    def test_concierge_has_context_section(self):
        """Concierge has a context-aware FoundUp section."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "conciergeContext" in html
        assert "This FoundUp" in html

    def test_concierge_is_context_aware(self):
        """Script populates concierge with FoundUp-specific data."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "populateConciergeContext" in html
        # Must be called after renderEntry
        render_pos = html.index("renderEntry(item)")
        populate_pos = html.index("populateConciergeContext(item)")
        assert populate_pos > render_pos, (
            "populateConciergeContext must be called after renderEntry"
        )

    def test_concierge_has_readiness_guide(self):
        """Concierge sheet explains all three readiness levels."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "Readiness guide" in html
        assert "dot-ready" in html
        assert "dot-conditional" in html
        assert "dot-discoverable" in html

    def test_concierge_has_navigation_tips(self):
        """Concierge sheet has navigation guidance."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "deep-linkable" in html
        assert "Back to Mall" in html or "Return to Mall" in html

    def test_concierge_toggle_wired(self):
        """Red Dog button wires to toggleConcierge, not navigation."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "toggleConcierge" in html
        # Should NOT navigate away on click
        click_section = html[html.index("entryRedDog"):]
        click_line_end = click_section.index(";")
        click_binding = click_section[:click_line_end]
        assert "window.location" not in click_binding

    def test_concierge_escape_closes(self):
        """Pressing Escape closes the concierge."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "Escape" in html
        assert "closeConcierge" in html

    def test_scrim_click_closes(self):
        """Clicking scrim closes the concierge."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "conciergeScrim" in html
        assert "closeConcierge" in html


# ---------------------------------------------------------------------------
# CSS — concierge styling
# ---------------------------------------------------------------------------

class TestConciergeCSS:
    """CSS for concierge components exists."""

    def test_member_css_has_readiness_dots(self):
        css = MEMBER_CSS.read_text(encoding="utf-8")
        assert "rd-dot-ready" in css
        assert "rd-dot-conditional" in css
        assert "rd-dot-discoverable" in css

    def test_member_css_has_readiness_key(self):
        css = MEMBER_CSS.read_text(encoding="utf-8")
        assert "red-dog-readiness-key" in css

    def test_entry_page_has_concierge_styles(self):
        """foundup.html has inline styles for the concierge sheet."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "concierge-sheet" in html
        assert "concierge-scrim" in html


# ---------------------------------------------------------------------------
# No regression — existing entry flow
# ---------------------------------------------------------------------------

class TestEntryFlowRegression:
    """Verify existing entry page behavior is preserved."""

    def test_entry_page_still_fetches_catalog(self):
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "mall-video-catalog.json" in html

    def test_entry_page_still_has_readiness_blocks(self):
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "readiness-ready" in html
        assert "readiness-conditional" in html
        assert "readiness-discoverable_only" in html

    def test_entry_page_still_has_back_link(self):
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "Back to Mall" in html

    def test_entry_page_still_escapes_output(self):
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "esc(" in html

    def test_index_navigates_to_entry_via_concierge(self):
        """Entry navigation lives in account-concierge.js (dynamic tile rendering)."""
        js_path = MEMBER_DIR / "js" / "account-concierge.js"
        js = js_path.read_text(encoding="utf-8")
        assert "foundup.html" in js
        assert "encodeURIComponent" in js
