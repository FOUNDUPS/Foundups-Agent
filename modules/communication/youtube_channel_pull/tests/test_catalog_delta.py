"""
Tests for YouTube Channel Pull catalog delta generation.

Tests channel identity extraction, duplicate detection, and delta generation
using fixture data (no live API required).
"""

import pytest
from modules.communication.youtube_channel_pull.src.channel_puller import (
    get_channel_id_from_catalog,
    get_channel_ids_from_catalog,
)
from modules.communication.youtube_channel_pull.src.catalog_delta import (
    get_existing_video_ids,
    compute_delta,
    generate_full_delta,
    format_delta_summary,
)


# ==================== Fixtures ====================


@pytest.fixture
def sample_catalog_entry():
    """Single YouTube-backed catalog entry."""
    return {
        "foundup_id": "move2japan",
        "title": "Move to Japan",
        "source_type": "youtube_channel",
        "source_id": "UC-LSSlOZwpGIRIYihaz8zCw",
        "videos": [
            {"video_id": "abc123", "title": "Video 1"},
            {"video_id": "def456", "title": "Video 2"},
            {"video_id": "ghi789", "title": "Video 3"},
        ],
    }


@pytest.fixture
def sample_catalog():
    """Multi-entry catalog."""
    return [
        {
            "foundup_id": "move2japan",
            "source_type": "youtube_channel",
            "source_id": "UC-LSSlOZwpGIRIYihaz8zCw",
            "videos": [
                {"video_id": "abc123", "title": "Video 1"},
                {"video_id": "def456", "title": "Video 2"},
            ],
        },
        {
            "foundup_id": "antifafm",
            "source_type": "youtube_channel",
            "source_id": "UCVSmg5aOhP4tnQ9KFUg97qA",
            "videos": [
                {"video_id": "xyz999", "title": "Existing"},
            ],
        },
        {
            "foundup_id": "gotjunk",
            "source_type": "web_app",
            "source_id": None,
            "videos": [],
        },
    ]


@pytest.fixture
def sample_pulled_videos():
    """Simulated API response."""
    return [
        {"video_id": "abc123", "title": "Video 1 (exists)"},
        {"video_id": "new001", "title": "New Video 1"},
        {"video_id": "new002", "title": "New Video 2"},
    ]


# ==================== Channel Identity Tests ====================


class TestChannelIdentityExtraction:
    """Test channel ID extraction from catalog."""

    def test_extract_channel_id_youtube_type(self, sample_catalog_entry):
        """YouTube channel entry returns source_id."""
        channel_id = get_channel_id_from_catalog(sample_catalog_entry)
        assert channel_id == "UC-LSSlOZwpGIRIYihaz8zCw"

    def test_extract_channel_id_non_youtube_type(self):
        """Non-YouTube entry returns None."""
        entry = {"source_type": "web_app", "source_id": "some-id"}
        assert get_channel_id_from_catalog(entry) is None

    def test_extract_channel_id_missing_source(self):
        """Missing source_id returns None."""
        entry = {"source_type": "youtube_channel"}
        assert get_channel_id_from_catalog(entry) is None

    def test_extract_channel_id_invalid_format(self):
        """Non-UC prefix returns None."""
        entry = {"source_type": "youtube_channel", "source_id": "invalid"}
        assert get_channel_id_from_catalog(entry) is None

    def test_extract_all_channel_ids(self, sample_catalog):
        """Extract all YouTube-backed FoundUps."""
        mapping = get_channel_ids_from_catalog(sample_catalog)
        assert len(mapping) == 2
        assert mapping["move2japan"] == "UC-LSSlOZwpGIRIYihaz8zCw"
        assert mapping["antifafm"] == "UCVSmg5aOhP4tnQ9KFUg97qA"
        assert "gotjunk" not in mapping  # web_app, not youtube


# ==================== Duplicate Detection Tests ====================


class TestDuplicateDetection:
    """Test existing video ID extraction."""

    def test_get_existing_video_ids(self, sample_catalog_entry):
        """Extract video IDs from entry."""
        ids = get_existing_video_ids(sample_catalog_entry)
        assert ids == {"abc123", "def456", "ghi789"}

    def test_get_existing_video_ids_empty(self):
        """Empty videos returns empty set."""
        entry = {"videos": []}
        assert get_existing_video_ids(entry) == set()

    def test_get_existing_video_ids_missing_field(self):
        """Missing video_id field handled."""
        entry = {"videos": [{"title": "No ID"}, {"video_id": "abc"}]}
        assert get_existing_video_ids(entry) == {"abc"}


# ==================== Delta Generation Tests ====================


class TestDeltaGeneration:
    """Test delta computation."""

    def test_compute_delta_with_new_and_existing(self, sample_pulled_videos):
        """Delta correctly identifies new vs existing."""
        existing_ids = {"abc123", "def456"}
        delta = compute_delta("move2japan", existing_ids, sample_pulled_videos)

        assert delta["foundup_id"] == "move2japan"
        assert delta["existing_count"] == 2
        assert delta["pulled_count"] == 3
        assert delta["new_count"] == 2
        assert delta["skipped_count"] == 1

        new_ids = [v["video_id"] for v in delta["new_videos"]]
        assert "new001" in new_ids
        assert "new002" in new_ids
        assert "abc123" not in new_ids

        assert "abc123" in delta["skipped_ids"]

    def test_compute_delta_all_new(self):
        """All videos are new."""
        pulled = [{"video_id": "x"}, {"video_id": "y"}]
        delta = compute_delta("test", set(), pulled)

        assert delta["new_count"] == 2
        assert delta["skipped_count"] == 0

    def test_compute_delta_all_existing(self):
        """All videos already exist."""
        pulled = [{"video_id": "x"}, {"video_id": "y"}]
        delta = compute_delta("test", {"x", "y"}, pulled)

        assert delta["new_count"] == 0
        assert delta["skipped_count"] == 2

    def test_generate_full_delta(self, sample_catalog):
        """Full delta across multiple FoundUps."""
        pulled = {
            "move2japan": [
                {"video_id": "abc123"},  # exists
                {"video_id": "new001"},  # new
            ],
            "antifafm": [
                {"video_id": "xyz999"},  # exists
                {"video_id": "new002"},  # new
                {"video_id": "new003"},  # new
            ],
        }

        delta = generate_full_delta(sample_catalog, pulled)

        assert "generated_at" in delta
        assert delta["summary"]["foundups_checked"] == 2
        assert delta["summary"]["total_new_videos"] == 3
        assert delta["summary"]["total_skipped"] == 2


# ==================== Formatting Tests ====================


class TestDeltaFormatting:
    """Test human-readable delta output."""

    def test_format_delta_summary(self):
        """Format produces readable output."""
        delta = {
            "generated_at": "2026-04-13T12:00:00Z",
            "summary": {
                "foundups_checked": 2,
                "total_new_videos": 5,
                "total_skipped": 10,
            },
            "deltas": [
                {
                    "foundup_id": "move2japan",
                    "existing_count": 573,
                    "pulled_count": 50,
                    "new_count": 3,
                    "skipped_count": 47,
                    "new_videos": [
                        {"video_id": "x", "title": "New Video Title Here"},
                    ],
                    "skipped_ids": [],
                }
            ],
        }

        output = format_delta_summary(delta)
        assert "YOUTUBE CHANNEL PULL DELTA REPORT" in output
        assert "move2japan" in output
        assert "New: 3" in output
        assert "New Video Title Here" in output
