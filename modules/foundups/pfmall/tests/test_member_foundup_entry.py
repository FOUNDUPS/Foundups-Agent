#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the member Mall FoundUp entry page (Phase 1).

Verifies that:
- foundup.html exists and contains the expected structure
- index.html navigates to foundup.html on card tap (not overlay)
- Entry page references the correct catalog fields
- Deep-linking via ?id= parameter is wired
"""

import re
from pathlib import Path

import pytest


MEMBER_DIR = Path(__file__).resolve().parents[4] / "public" / "member"
ENTRY_PAGE = MEMBER_DIR / "foundup.html"
INDEX_PAGE = MEMBER_DIR / "index.html"


# ---------------------------------------------------------------------------
# foundup.html — existence and structure
# ---------------------------------------------------------------------------

class TestFoundupEntryPage:
    """Tests for the dedicated FoundUp entry page."""

    def test_entry_page_exists(self):
        assert ENTRY_PAGE.is_file(), "public/member/foundup.html must exist"

    def test_entry_page_is_valid_html(self):
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_entry_page_reads_id_param(self):
        """Page extracts foundup_id from ?id= query parameter."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "URLSearchParams" in html
        assert "params.get('id')" in html or "params.get(\"id\")" in html

    def test_entry_page_fetches_catalog(self):
        """Page fetches mall-catalog.json to find the FoundUp."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "mall-catalog.json" in html

    def test_entry_page_matches_by_foundup_id(self):
        """Page finds the catalog entry by foundup_id field."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "foundup_id" in html

    def test_entry_page_renders_hero_fields(self):
        """Page renders name, tagline, and token_symbol in hero section."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        for field in ("item.name", "item.tagline", "item.token_symbol"):
            assert field in html, f"Entry page should reference {field}"

    def test_entry_page_renders_readiness(self):
        """Page shows launch_readiness state."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "launch_readiness" in html

    def test_entry_page_renders_detail_rows(self):
        """Page shows detail fields: category, tier, lifecycle, routing."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        for field in ("category", "tier", "lifecycle_stage", "routing_prefix"):
            assert field in html, f"Entry page should reference {field}"

    def test_entry_page_has_back_link(self):
        """Page has a link back to the Mall."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "/member/" in html
        assert "Back to Mall" in html or "Return to Mall" in html

    def test_entry_page_has_not_found_state(self):
        """Page handles unknown foundup_id gracefully."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "Not Found" in html or "not found" in html.lower()

    def test_entry_page_escapes_output(self):
        """Page uses an escape function to prevent XSS."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "esc(" in html or "escapeHtml(" in html

    def test_entry_page_has_readiness_classes(self):
        """Page applies readiness-specific CSS classes."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "readiness-ready" in html
        assert "readiness-conditional" in html
        assert "readiness-discoverable_only" in html

    def test_entry_page_uses_member_css(self):
        """Page links to the shared member.css stylesheet."""
        html = ENTRY_PAGE.read_text(encoding="utf-8")
        assert "member.css" in html


# ---------------------------------------------------------------------------
# index.html — card tap navigates (not overlay)
# ---------------------------------------------------------------------------

class TestIndexCardNavigation:
    """Verify index.html card click navigates to foundup.html."""

    def test_index_page_exists(self):
        assert INDEX_PAGE.is_file()

    def test_card_click_navigates_to_entry(self):
        """Card click handler sets window.location to foundup.html."""
        html = INDEX_PAGE.read_text(encoding="utf-8")
        assert "foundup.html" in html, (
            "index.html should reference foundup.html for card navigation"
        )

    def test_card_click_passes_foundup_id(self):
        """Navigation URL includes the foundup_id as ?id= parameter."""
        html = INDEX_PAGE.read_text(encoding="utf-8")
        assert "foundup_id" in html
        # Should encode the ID for safe URL usage
        assert "encodeURIComponent" in html

    def test_card_click_does_not_open_overlay(self):
        """Card click no longer calls openFoundupOverlay directly."""
        html = INDEX_PAGE.read_text(encoding="utf-8")
        # Find click event handlers in card binding section
        # The click handler should NOT call openFoundupOverlay
        click_pattern = re.search(
            r"card\.addEventListener\('click'.*?}\);",
            html,
            re.DOTALL,
        )
        assert click_pattern, "Should have a card click handler"
        handler_body = click_pattern.group(0)
        assert "openFoundupOverlay" not in handler_body, (
            "Card click handler should navigate, not open overlay"
        )


# ---------------------------------------------------------------------------
# Catalog shape compatibility
# ---------------------------------------------------------------------------

class TestCatalogShapeForEntry:
    """Entry page expects specific fields from mall-catalog.json."""

    def test_entry_page_field_expectations(self):
        """All fields used by foundup.html are in the catalog export shape."""
        from modules.foundups.pfmall.api import reset_default_shell
        from modules.foundups.pfmall.member_catalog_export import build_mall_catalog

        reset_default_shell()
        catalog = build_mall_catalog()
        assert len(catalog) >= 1

        # Fields referenced by foundup.html
        entry_fields = {
            "foundup_id", "name", "tagline", "description", "category",
            "tier", "lifecycle_stage", "launch_readiness", "token_symbol",
            "routing_prefix", "entry_copy",
        }
        for item in catalog:
            missing = entry_fields - item.keys()
            assert not missing, (
                f"{item['foundup_id']} missing fields needed by foundup.html: {missing}"
            )
        reset_default_shell()
