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
        valid_types = {"youtube_channel", "linkedin_profile", "x_profile", "tiktok_profile", "instagram_profile"}
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
