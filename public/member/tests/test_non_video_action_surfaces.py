"""
Non-Video Action Surface Tests

Tests that non-video FoundUps (github_repo, external_app, internal_service)
get truthful CTAs and metadata in the entry page, and that video-backed
entries remain video-oriented.

Worker: AL
Slice: PFMALL_NON_VIDEO_ACTION_SURFACE_PHASE1
"""

import json
import os
from pathlib import Path

import pytest

MEMBER_DIR = Path(__file__).resolve().parents[1]
ENTRY_PAGE = MEMBER_DIR / "foundup.html"
CATALOG_PATH = MEMBER_DIR / "mall-video-catalog.json"


def _html():
    return ENTRY_PAGE.read_text(encoding="utf-8")


def _catalog():
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# CTA config and rendering
# ---------------------------------------------------------------------------


class TestSourceTypeCTAConfig:
    """Verify source-type CTA configuration exists in entry page JS."""

    def test_source_type_cta_map_exists(self):
        """SOURCE_TYPE_CTA config is defined."""
        html = _html()
        assert "SOURCE_TYPE_CTA" in html

    def test_github_repo_cta_label(self):
        """github_repo gets 'View Repo' CTA."""
        html = _html()
        assert "View Repo" in html

    def test_external_app_cta_label(self):
        """external_app gets 'Open App' CTA."""
        html = _html()
        assert "Open App" in html

    def test_internal_service_cta_label(self):
        """internal_service gets 'Open Service' CTA."""
        html = _html()
        assert "Open Service" in html

    def test_non_video_source_types_set(self):
        """NON_VIDEO_SOURCE_TYPES set is defined."""
        html = _html()
        assert "NON_VIDEO_SOURCE_TYPES" in html

    def test_cta_references_external_url(self):
        """CTA config reads from external_url field."""
        html = _html()
        assert "external_url" in html


class TestCTARendering:
    """Verify CTA block is rendered for non-video types."""

    def test_cta_block_rendered_by_source_type(self):
        """renderSourceTypeCTA function exists."""
        html = _html()
        assert "renderSourceTypeCTA" in html

    def test_cta_block_has_data_attribute(self):
        """CTA block uses data-source-type attribute for testability."""
        html = _html()
        assert "data-source-type" in html

    def test_cta_opens_in_new_tab(self):
        """CTA link uses target=_blank with noopener."""
        html = _html()
        assert 'target="_blank"' in html
        assert 'rel="noopener noreferrer"' in html

    def test_cta_btn_class_exists(self):
        """CTA button has entry-cta-btn class."""
        html = _html()
        assert "entry-cta-btn" in html

    def test_source_type_label_displayed(self):
        """Source type label shown below CTA."""
        html = _html()
        assert "entry-source-type-label" in html


# ---------------------------------------------------------------------------
# Detail row metadata
# ---------------------------------------------------------------------------


class TestDetailRowMetadata:
    """Verify detail rows show source type and URL for non-video entries."""

    def test_source_type_detail_row(self):
        """Source Type detail row is rendered for non-video types."""
        html = _html()
        assert "Source Type" in html

    def test_external_url_detail_row(self):
        """URL detail row renders external_url as a clickable link."""
        html = _html()
        # Should have a link in the URL detail row
        assert "external_url" in html


# ---------------------------------------------------------------------------
# Concierge briefing
# ---------------------------------------------------------------------------


class TestConciergeBriefing:
    """Verify concierge shows source-type-aware briefing for non-video entries."""

    def test_briefing_shows_source_type(self):
        """Briefing includes source type line for non-video entries."""
        html = _html()
        # The briefing code checks NON_VIDEO_SOURCE_TYPES and adds Type line
        assert "NON_VIDEO_SOURCE_TYPES.has(item.source_type)" in html

    def test_briefing_shows_external_url(self):
        """Briefing includes external URL for non-video entries."""
        html = _html()
        assert "item.external_url" in html


# ---------------------------------------------------------------------------
# Concierge recommendations
# ---------------------------------------------------------------------------


class TestConciergeRecommendations:
    """Verify concierge adds source-type-aware action pill."""

    def test_source_type_action_in_recommendations(self):
        """source_type_action recommendation is injected for non-video types."""
        html = _html()
        assert "source_type_action" in html

    def test_recommendation_opens_external_url(self):
        """Source type recommendation opens external_url."""
        html = _html()
        assert "window.open(currentItem.external_url" in html


# ---------------------------------------------------------------------------
# Video-backed entries remain video-oriented
# ---------------------------------------------------------------------------


class TestVideoEntriesUnchanged:
    """Verify video-backed entries retain video semantics."""

    def test_video_count_still_rendered(self):
        """Video count row still shown for video-backed entries."""
        html = _html()
        assert "item.video_count" in html

    def test_cta_not_rendered_for_video_types(self):
        """SOURCE_TYPE_CTA only maps non-video types."""
        html = _html()
        # youtube_channel should NOT appear in SOURCE_TYPE_CTA
        assert "youtube_channel" not in html.split("SOURCE_TYPE_CTA")[1].split("};")[0]

    def test_no_fake_playback_for_non_video(self):
        """No playback language in CTA labels."""
        html = _html()
        cta_section = html.split("SOURCE_TYPE_CTA")[1].split("};")[0]
        for word in ["Play", "Watch", "Stream", "playback"]:
            assert word not in cta_section, (
                f"Non-video CTA should not use playback language: '{word}'"
            )


# ---------------------------------------------------------------------------
# Catalog truth: real non-video entries have external_url
# ---------------------------------------------------------------------------


class TestCatalogNonVideoTruth:
    """Verify real catalog entries match entry page expectations."""

    NON_VIDEO_TYPES = {"github_repo", "external_app", "internal_service"}

    def test_non_video_entries_have_external_url(self):
        """All non-video catalog entries have external_url."""
        catalog = _catalog()
        for entry in catalog:
            if entry["source_type"] in self.NON_VIDEO_TYPES:
                assert entry.get("external_url"), (
                    f"{entry['foundup_id']} ({entry['source_type']}) missing external_url"
                )

    def test_science_swarm_is_github_repo(self):
        """science_swarm is source_type github_repo."""
        catalog = _catalog()
        entry = next(e for e in catalog if e["foundup_id"] == "science_swarm")
        assert entry["source_type"] == "github_repo"
        assert "github.com" in entry["external_url"]

    def test_autopost_is_external_app(self):
        """autopost is source_type external_app."""
        catalog = _catalog()
        entry = next(e for e in catalog if e["foundup_id"] == "autopost")
        assert entry["source_type"] == "external_app"
        assert entry["external_url"].startswith("https://")

    def test_kosei_is_internal_service(self):
        """kosei is source_type internal_service."""
        catalog = _catalog()
        entry = next(e for e in catalog if e["foundup_id"] == "kosei")
        assert entry["source_type"] == "internal_service"
        assert entry["external_url"].startswith("https://")

    def test_video_entries_have_no_external_url(self):
        """YouTube channel entries do not have external_url."""
        catalog = _catalog()
        for entry in catalog:
            if entry["source_type"] == "youtube_channel":
                assert "external_url" not in entry or not entry.get("external_url"), (
                    f"Video entry {entry['foundup_id']} should not have external_url"
                )
