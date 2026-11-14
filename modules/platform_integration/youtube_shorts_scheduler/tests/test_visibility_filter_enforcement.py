"""Tests for UNLISTED vs Scheduled visibility filter detection and enforcement."""

from modules.platform_integration.youtube_shorts_scheduler.src.dom_automation import (
    classify_visibility_filter,
    VISIBILITY_CHECKBOX_LABELS,
)


class TestClassifyVisibilityFilter:
    def test_unlisted_chip(self):
        assert classify_visibility_filter("Visibility: Unlisted") == "UNLISTED"

    def test_scheduled_chip_has_schedule(self):
        assert classify_visibility_filter("Visibility: Has schedule") == "SCHEDULED"

    def test_scheduled_chip_text(self):
        assert classify_visibility_filter("Visibility: Scheduled") == "SCHEDULED"

    def test_unlisted_url_param(self):
        url = (
            "https://studio.youtube.com/channel/UCxxx/videos/short?"
            "filter=%5B%7B%22name%22%3A%22VISIBILITY%22%2C%22value%22%3A%5B%22UNLISTED%22%5D%7D%5D"
        )
        assert classify_visibility_filter("", url) == "UNLISTED"

    def test_scheduled_url_param(self):
        url = (
            "https://studio.youtube.com/channel/UCxxx/videos/short?"
            "filter=%5B%7B%22name%22%3A%22VISIBILITY%22%2C%22value%22%3A%5B%22SCHEDULED%22%5D%7D%5D"
        )
        assert classify_visibility_filter("", url) == "SCHEDULED"

    def test_chip_beats_empty_url(self):
        assert (
            classify_visibility_filter("Visibility: Has schedule", "https://studio.youtube.com/...")
            == "SCHEDULED"
        )

    def test_no_filter(self):
        assert classify_visibility_filter("", "") is None


class TestVisibilityCheckboxLabels:
    def test_scheduled_uses_has_schedule(self):
        assert VISIBILITY_CHECKBOX_LABELS["SCHEDULED"] == "Has schedule"

    def test_unlisted_label(self):
        assert VISIBILITY_CHECKBOX_LABELS["UNLISTED"] == "Unlisted"
