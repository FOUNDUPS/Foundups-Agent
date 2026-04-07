"""Tests for mall-video-catalog.json manifest shape.

Worker E acceptance criteria:
- real demo content exists in stable manifest form
- shape is test-covered
- no flattening of all 012 presence into one creator tile
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

CATALOG_PATH = Path(__file__).parent.parent.parent.parent.parent / "public" / "member" / "mall-video-catalog.json"


@pytest.fixture
def catalog() -> list[dict]:
    """Load the video catalog."""
    assert CATALOG_PATH.exists(), f"Catalog not found at {CATALOG_PATH}"
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


class TestCatalogStructure:
    """Test overall catalog structure."""

    def test_catalog_is_list(self, catalog: list[dict]):
        assert isinstance(catalog, list)
        assert len(catalog) > 0

    def test_catalog_has_multiple_foundups(self, catalog: list[dict]):
        """012 presence must NOT be flattened into one creator tile."""
        assert len(catalog) >= 4, "Expected at least 4 distinct FoundUp lanes"

    def test_each_entry_has_distinct_foundup_id(self, catalog: list[dict]):
        ids = [entry["foundup_id"] for entry in catalog]
        assert len(ids) == len(set(ids)), "Duplicate foundup_id found"


class TestFoundUpEntryShape:
    """Test individual FoundUp entry shape per spec."""

    REQUIRED_FIELDS = [
        "foundup_id",
        "title",
        "creator",
        "entity",
        "source_type",
        "category",
        "tags",
        "status",
        "video_count",
        "videos",
    ]

    OPTIONAL_FIELDS = [
        "source_id",
        "source_handle",
        "geo",
        "poster_url",
    ]

    def test_all_entries_have_required_fields(self, catalog: list[dict]):
        for entry in catalog:
            for field in self.REQUIRED_FIELDS:
                assert field in entry, f"Missing required field '{field}' in {entry.get('foundup_id', 'unknown')}"

    def test_foundup_id_format(self, catalog: list[dict]):
        for entry in catalog:
            fid = entry["foundup_id"]
            assert isinstance(fid, str)
            assert len(fid) > 0
            assert fid == fid.lower().replace(" ", "_"), f"foundup_id should be lowercase snake_case: {fid}"

    def test_source_type_values(self, catalog: list[dict]):
        valid_types = {
            "youtube_channel", "linkedin_profile", "x_profile",
            "tiktok_profile", "instagram_profile", "derived",
            "github_repo", "external_app", "internal_service",
        }
        for entry in catalog:
            assert entry["source_type"] in valid_types, f"Invalid source_type: {entry['source_type']}"

    def test_status_values(self, catalog: list[dict]):
        valid_statuses = {"active", "placeholder", "archived", "pending"}
        for entry in catalog:
            assert entry["status"] in valid_statuses, f"Invalid status: {entry['status']}"

    def test_tags_is_list(self, catalog: list[dict]):
        for entry in catalog:
            assert isinstance(entry["tags"], list)
            assert all(isinstance(tag, str) for tag in entry["tags"])

    def test_video_count_matches_videos_array(self, catalog: list[dict]):
        for entry in catalog:
            assert entry["video_count"] == len(entry["videos"]), (
                f"video_count mismatch in {entry['foundup_id']}: "
                f"count={entry['video_count']}, actual={len(entry['videos'])}"
            )


class TestVideoEntryShape:
    """Test individual video entry shape per spec."""

    REQUIRED_VIDEO_FIELDS = [
        "video_id",
        "title",
        "timestamp",
        "duration_seconds",
    ]

    OPTIONAL_VIDEO_FIELDS = [
        "thumbnail_url",
        "embed_url",
        "source_url",
        "poster_url",
        "is_live",
    ]

    def test_all_videos_have_required_fields(self, catalog: list[dict]):
        for entry in catalog:
            for video in entry["videos"]:
                for field in self.REQUIRED_VIDEO_FIELDS:
                    assert field in video, (
                        f"Missing required field '{field}' in video {video.get('video_id', 'unknown')} "
                        f"of {entry['foundup_id']}"
                    )

    def test_video_id_unique_within_foundup(self, catalog: list[dict]):
        for entry in catalog:
            ids = [v["video_id"] for v in entry["videos"]]
            assert len(ids) == len(set(ids)), f"Duplicate video_id in {entry['foundup_id']}"

    def test_timestamp_is_iso_format(self, catalog: list[dict]):
        import re
        iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        for entry in catalog:
            for video in entry["videos"]:
                ts = video["timestamp"]
                assert iso_pattern.match(ts), f"Invalid timestamp format: {ts}"

    def test_duration_is_non_negative(self, catalog: list[dict]):
        for entry in catalog:
            for video in entry["videos"]:
                assert video["duration_seconds"] >= 0


class TestExpectedFoundUps:
    """Test that expected 012 lanes are present."""

    EXPECTED_LANES = [
        "move2japan",
        "antifafm",
        "foundups_main",
        "undaodu",
    ]

    def test_core_youtube_lanes_present(self, catalog: list[dict]):
        ids = {entry["foundup_id"] for entry in catalog}
        for lane in self.EXPECTED_LANES:
            assert lane in ids, f"Expected lane '{lane}' not found in catalog"

    def test_lanes_are_distinct_entities(self, catalog: list[dict]):
        """Each lane should have its own entity, not all collapsed to '012'."""
        entities = {entry["entity"] for entry in catalog}
        assert len(entities) > 1, "All lanes collapsed to same entity"

    def test_youtube_lanes_have_source_ids(self, catalog: list[dict]):
        youtube_entries = [e for e in catalog if e["source_type"] == "youtube_channel"]
        for entry in youtube_entries:
            assert entry.get("source_id"), f"YouTube lane {entry['foundup_id']} missing source_id"
            assert entry["source_id"].startswith("UC"), f"Invalid YouTube channel ID: {entry['source_id']}"


class TestCategoryDiversity:
    """Test that catalog has category diversity."""

    def test_multiple_categories(self, catalog: list[dict]):
        categories = {entry["category"] for entry in catalog}
        assert len(categories) >= 3, f"Expected at least 3 categories, got: {categories}"

    def test_expected_categories_present(self, catalog: list[dict]):
        categories = {entry["category"] for entry in catalog}
        expected = {"travel", "media", "music"}
        for cat in expected:
            assert cat in categories, f"Expected category '{cat}' not found"


class TestProjectionMetadata:
    """Test projection-ready enrichment fields (Phase 2)."""

    PROJECTION_FIELDS = [
        "creator_id",
        "creator_display",
        "topic_family",
        "related_lanes",
        "display_order",
    ]

    def test_all_entries_have_projection_fields(self, catalog: list[dict]):
        """All lanes must have projection metadata for Red Dog filtering."""
        for entry in catalog:
            for field in self.PROJECTION_FIELDS:
                assert field in entry, (
                    f"Missing projection field '{field}' in {entry['foundup_id']}"
                )

    def test_creator_id_is_consistent(self, catalog: list[dict]):
        """All 012 lanes should share same creator_id."""
        creator_ids = {entry["creator_id"] for entry in catalog}
        assert "012" in creator_ids, "Expected creator_id '012' in catalog"

    def test_topic_family_values(self, catalog: list[dict]):
        """topic_family must be one of defined values."""
        valid_families = {
            "life", "consciousness", "startup", "resistance",
            "ai-education", "science", "media",
        }
        for entry in catalog:
            assert entry["topic_family"] in valid_families, (
                f"Invalid topic_family '{entry['topic_family']}' in {entry['foundup_id']}"
            )

    def test_related_lanes_are_valid_refs(self, catalog: list[dict]):
        """related_lanes must reference existing foundup_ids."""
        all_ids = {entry["foundup_id"] for entry in catalog}
        for entry in catalog:
            for ref in entry["related_lanes"]:
                assert ref in all_ids, (
                    f"Invalid related_lane '{ref}' in {entry['foundup_id']} - not in catalog"
                )

    def test_display_order_is_unique(self, catalog: list[dict]):
        """display_order must be unique across all lanes."""
        orders = [entry["display_order"] for entry in catalog]
        assert len(orders) == len(set(orders)), "Duplicate display_order found"

    def test_geo_is_filled(self, catalog: list[dict]):
        """All lanes must have non-null geo for location projection."""
        for entry in catalog:
            assert entry.get("geo") is not None, (
                f"Missing geo in {entry['foundup_id']}"
            )

    def test_all_tags_include_012_lane(self, catalog: list[dict]):
        """All 012 lanes should have '012-lane' tag for filtering."""
        for entry in catalog:
            assert "012-lane" in entry["tags"], (
                f"Missing '012-lane' tag in {entry['foundup_id']}"
            )


class TestNonVideoFoundUps:
    """Test non-video FoundUp types (github_repo, external_app, internal_service)."""

    NON_VIDEO_SOURCE_TYPES = {"github_repo", "external_app", "internal_service"}

    def test_external_url_present_for_non_video_types(self, catalog: list[dict]):
        """Non-video source types must have external_url."""
        for entry in catalog:
            if entry["source_type"] in self.NON_VIDEO_SOURCE_TYPES:
                assert "external_url" in entry and entry["external_url"], (
                    f"Missing external_url in {entry['foundup_id']} "
                    f"(source_type={entry['source_type']})"
                )

    def test_external_url_is_https(self, catalog: list[dict]):
        """external_url must be a valid https URL."""
        for entry in catalog:
            url = entry.get("external_url")
            if url:
                assert url.startswith("https://"), (
                    f"external_url must be https in {entry['foundup_id']}: {url}"
                )


class TestDerivedLanes:
    """Test derived lane conditional fields."""

    def test_derived_lanes_have_parent_channels(self, catalog: list[dict]):
        """Derived lanes must declare parent_channels."""
        for entry in catalog:
            if entry["source_type"] == "derived":
                assert "parent_channels" in entry, (
                    f"Missing parent_channels in derived lane {entry['foundup_id']}"
                )
                assert isinstance(entry["parent_channels"], list), (
                    f"parent_channels must be a list in {entry['foundup_id']}"
                )
                assert len(entry["parent_channels"]) > 0, (
                    f"parent_channels must not be empty in {entry['foundup_id']}"
                )

    def test_derived_lanes_have_derivation_method(self, catalog: list[dict]):
        """Derived lanes must declare derivation_method."""
        valid_methods = {"manual_curation", "topic_tag", "ai_classification"}
        for entry in catalog:
            if entry["source_type"] == "derived":
                assert "derivation_method" in entry, (
                    f"Missing derivation_method in derived lane {entry['foundup_id']}"
                )
                assert entry["derivation_method"] in valid_methods, (
                    f"Invalid derivation_method '{entry['derivation_method']}' "
                    f"in {entry['foundup_id']}"
                )

    def test_parent_channels_reference_valid_lanes(self, catalog: list[dict]):
        """parent_channels must reference existing foundup_ids."""
        all_ids = {entry["foundup_id"] for entry in catalog}
        for entry in catalog:
            if entry["source_type"] == "derived" and "parent_channels" in entry:
                for ref in entry["parent_channels"]:
                    assert ref in all_ids, (
                        f"Invalid parent_channel '{ref}' in {entry['foundup_id']}"
                    )
