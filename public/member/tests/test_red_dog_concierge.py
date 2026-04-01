#!/usr/bin/env python3
"""Tests for Red Dog concierge module (unified phase 1).

Validates:
  1. concierge module presence
  2. Red Dog hook usage
  3. concierge surface markup/logic presence
  4. readiness/help copy presence
  5. no regression to member entry flow
"""

from pathlib import Path

import pytest

MEMBER_ROOT = Path(__file__).resolve().parents[1]
CONCIERGE_JS = MEMBER_ROOT / "js" / "red-dog-concierge.js"
INDEX_HTML = MEMBER_ROOT / "index.html"
FOUNDUP_HTML = MEMBER_ROOT / "foundup.html"


# -- 1. concierge module presence --


class TestConciergeModulePresence:

    def test_js_file_exists(self):
        assert CONCIERGE_JS.exists(), "red-dog-concierge.js not found"

    def test_js_file_not_empty(self):
        assert CONCIERGE_JS.stat().st_size > 100, "red-dog-concierge.js is suspiciously small"

    def test_js_is_iife(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "(function" in content, "Expected IIFE pattern"
        assert "})();" in content, "Expected IIFE closing"


# -- 2. Red Dog hook usage --


class TestRedDogHookUsage:

    def test_references_unified_plane(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "accountPlane" in content, "Must reference unified Red Dog plane"

    def test_references_concierge_hook(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-reddog-concierge" in content, "Must reference concierge section hook"

    def test_references_entry_sheet_hook(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "conciergeSheet" in content, "Must reference entry page concierge sheet"

    def test_detects_mall_page(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "mallTileField" in content, "Must detect Mall page"

    def test_detects_entry_page(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "entryContent" in content, "Must detect entry page via entryContent"

    def test_script_tag_in_index_html(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "js/red-dog-concierge.js" in content, "index.html must load concierge module"

    def test_script_tag_in_foundup_html(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "js/red-dog-concierge.js" in content, "foundup.html must load concierge module"


# -- 3. concierge surface markup/logic presence --


class TestConciergeSurface:

    def test_builds_guide_section(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "data-concierge" in content, "Must use data-concierge attribute for guide section"

    def test_uses_details_elements(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "<details" in content, "Must use <details> for collapsible topics"
        assert "<summary" in content, "Must use <summary> for topic headers"

    def test_injects_styles(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "concierge-topic" in content, "Must define .concierge-topic styles"

    def test_has_escape_helper(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "function esc" in content, "Must have XSS escape helper"


# -- 4. readiness/help copy presence --


class TestHelpCopy:

    def test_mall_topic_what_is_mall(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "What is the Mall" in content

    def test_mall_topic_how_to_browse(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "How do I browse" in content

    def test_mall_topic_who_is_red_dog(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "Red Dog" in content

    def test_entry_topic_readiness_states(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        lower = content.lower()
        assert "ready" in lower
        assert "conditional" in lower
        assert "discoverable" in lower

    def test_no_network_dependency(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "fetch(" not in content, "Concierge must not make network calls"
        assert "XMLHttpRequest" not in content, "Concierge must not make network calls"

    def test_no_fake_ai(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "typing indicator" not in content.lower(), "No fake AI streaming"


# -- 5. no regression to member entry flow --


class TestNoRegression:

    def test_index_has_loading_state(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "loadingState" in content

    def test_index_has_invite_gate(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "inviteGate" in content

    def test_index_has_username_modal(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "usernameModal" in content

    def test_index_has_member_area(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "memberArea" in content

    def test_index_has_clerk_auth(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "initClerkAuth" in content

    def test_index_has_red_dog_button(self):
        content = INDEX_HTML.read_text(encoding="utf-8")
        assert "redDogBtn" in content

    def test_foundup_has_back_to_mall(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "Back to Mall" in content

    def test_foundup_has_entry_red_dog(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "entryRedDog" in content

    def test_foundup_has_concierge_sheet(self):
        content = FOUNDUP_HTML.read_text(encoding="utf-8")
        assert "conciergeSheet" in content
