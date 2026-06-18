"""
Tests for YouTube Shorts Scheduler.

Unit tests for channel config, schedule tracker, and content generator.
Integration tests require live browser session.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import json

from modules.platform_integration.youtube_shorts_scheduler.src.channel_config import (
    get_channel_config,
    build_studio_url,
    get_studio_urls,
    CHANNELS,
)
from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import (
    ScheduleTracker,
    HARD_CAP_PER_DAY,
    MAX_JITTER_STEPS,
)


def _within_jitter(actual_time: str, base_time: str, max_steps: int = MAX_JITTER_STEPS) -> bool:
    """
    Return True if actual_time is within +/- (max_steps * 15 min) of base_time.

    The allocator applies randomized 15-min-step jitter to each base slot, so
    exact-time assertions are flaky. This verifies the slot is the expected base
    slot (i.e. correct ordering) while tolerating the bounded jitter window.
    """
    parsed_actual = datetime.strptime(actual_time.strip(), "%I:%M %p")
    parsed_base = datetime.strptime(base_time.strip(), "%I:%M %p")
    delta_min = abs((parsed_actual - parsed_base).total_seconds()) / 60.0
    return delta_min <= max_steps * 15
from modules.platform_integration.youtube_shorts_scheduler.src.content_generator import (
    generate_clickbait_title,
    extract_title_hint_from_index,
    generate_clickbait_title_from_index,
    get_standard_description,
    generate_description_with_context,
    get_hashtags,
)
from modules.platform_integration.youtube_shorts_scheduler.src.schedule_dba import (
    record_schedule_outcome,
)
from modules.platform_integration.youtube_shorts_scheduler.src.index_weave import (
    build_digital_twin_index_block,
    build_topic_hashtags,
    build_human_description_context,
    create_stub_index_json,
    inject_context_into_description,
    remove_existing_index_block,
    weave_description,
    update_index_after_schedule,
)


class TestChannelConfig:
    """Tests for channel configuration."""

    def test_get_channel_config_move2japan(self):
        """Test Move2Japan channel config."""
        config = get_channel_config("move2japan")
        assert config is not None
        assert config["id"] == "UC-LSSlOZwpGIRIYihaz8zCw"
        assert config["chrome_port"] == 9222
        # Density cap is 3/day (was 8). NOTE: the time-slot grid itself is
        # intentionally NOT reduced in this slice (1-6am window deferred:
        # Studio timezone is unverified) so slot count is not asserted here.
        # The HARD_CAP_PER_DAY clamp guarantees <= 3/day regardless of grid size.
        assert config["max_per_day"] == 3

    def test_get_channel_config_undaodu(self):
        """Test UnDaoDu channel config."""
        config = get_channel_config("undaodu")
        assert config is not None
        assert config["id"] == "UCfHM9Fw9HD-NwiS0seD_oIA"
        assert config["chrome_port"] == 9222  # Shared with Move2Japan

    def test_get_channel_config_foundups(self):
        """Test FoundUps channel config."""
        config = get_channel_config("foundups")
        assert config is not None
        assert config["id"] == "UCSNTUXjAgpd4sgWYP0xoJgw"
        assert config["chrome_port"] == 9223  # Edge browser

    def test_get_channel_config_case_insensitive(self):
        """Test case insensitive lookup."""
        config1 = get_channel_config("MOVE2JAPAN")
        config2 = get_channel_config("Move2Japan")
        config3 = get_channel_config("move2japan")
        assert config1 == config2 == config3

    def test_get_channel_config_unknown(self):
        """Test unknown channel returns None."""
        config = get_channel_config("unknown_channel")
        assert config is None

    def test_build_studio_url_basic(self):
        """Test basic Studio URL building."""
        url = build_studio_url("UC123", "short")
        assert "studio.youtube.com/channel/UC123/videos/short" in url

    def test_build_studio_url_with_visibility(self):
        """Test URL with visibility filter."""
        url = build_studio_url("UC123", "short", "UNLISTED")
        assert "UNLISTED" in url
        assert "filter=" in url

    def test_get_studio_urls(self):
        """Test pre-built URL generation."""
        urls = get_studio_urls("move2japan")
        assert "unlisted_shorts" in urls
        assert "scheduled_shorts" in urls
        assert "public_shorts" in urls
        assert "all_shorts" in urls
        assert "base" in urls


class TestScheduleTracker:
    """Tests for schedule tracking."""

    def test_tracker_initialization(self):
        """Test tracker creates storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ScheduleTracker("test_channel", Path(tmpdir))
            assert tracker.channel_id == "test_channel"
            assert tracker.tracker_file.parent.exists()

    def test_tracker_increment(self):
        """Test incrementing video count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ScheduleTracker("test_channel", Path(tmpdir))
            tracker.increment("Jan 5, 2026", "video123")
            assert tracker.get_count("Jan 5, 2026") == 1
            tracker.increment("Jan 5, 2026", "video456")
            assert tracker.get_count("Jan 5, 2026") == 2

    def test_tracker_persistence(self):
        """Test schedule persists to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and populate tracker
            tracker1 = ScheduleTracker("test_channel", Path(tmpdir))
            tracker1.increment("Jan 5, 2026", "video123")
            tracker1.increment("Jan 6, 2026", "video456")

            # Load fresh tracker
            tracker2 = ScheduleTracker("test_channel", Path(tmpdir))
            assert tracker2.get_count("Jan 5, 2026") == 1
            assert tracker2.get_count("Jan 6, 2026") == 1

    def test_get_next_available_slot_empty(self):
        """Test finding slot with empty schedule (base slot 0, allowing jitter)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ScheduleTracker("test_channel", Path(tmpdir))
            time_slots = ["5:00 AM", "11:00 AM", "5:00 PM"]

            slot = tracker.get_next_available_slot(time_slots, max_per_day=3)
            assert slot is not None
            date_str, time_str = slot
            # First slot on empty day = base "5:00 AM" +/- jitter (max +/-30 min).
            # Jitter is randomized, so assert the result is within the slot-0 window.
            assert _within_jitter(time_str, "5:00 AM")

    def test_get_next_available_slot_partial(self):
        """Test finding slot with partially filled day (rolls to base slot 1)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ScheduleTracker("test_channel", Path(tmpdir))
            time_slots = ["5:00 AM", "11:00 AM", "5:00 PM"]

            # Fill first slot of tomorrow
            tomorrow = datetime.now() + timedelta(days=1)
            date_str = tomorrow.strftime("%b %d, %Y").replace(" 0", " ")
            tracker.increment(date_str, "video1")

            slot = tracker.get_next_available_slot(time_slots, max_per_day=3)
            assert slot is not None
            returned_date, time_str = slot
            # Should get second slot (base "11:00 AM") on same day, +/- jitter.
            assert _within_jitter(time_str, "11:00 AM")

    def test_get_summary(self):
        """Test schedule summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ScheduleTracker("test_channel", Path(tmpdir))
            tracker.increment("Jan 5, 2026", "v1")
            tracker.increment("Jan 5, 2026", "v2")
            tracker.increment("Jan 6, 2026", "v3")

            summary = tracker.get_summary()
            assert summary["total_scheduled"] == 3
            assert summary["dates_with_videos"] == 2


class TestContentGenerator:
    """Tests for content generation."""

    def test_generate_clickbait_title(self):
        """Test title generation."""
        title = generate_clickbait_title()
        assert len(title) <= 100
        assert "#FFCPLN" in title or "#MAGA" in title

    def test_generate_clickbait_title_with_hint(self):
        """Test title with song hint."""
        title = generate_clickbait_title(song_hint="Test Song")
        assert len(title) <= 100

    def test_extract_title_hint_from_index_prefers_summary(self):
        idx = {"metadata": {"summary": "FFCPLN music short: My Song Title"}}
        hint = extract_title_hint_from_index(idx, fallback_title="Fallback")
        assert "My Song Title" in hint

    def test_generate_clickbait_title_from_index_under_100(self):
        idx = {"metadata": {"summary": "FFCPLN music short: My Song Title"}}
        title = generate_clickbait_title_from_index(original_title="Orig", index_json=idx)
        assert len(title) <= 100

    def test_get_standard_description_ffcpln(self):
        """Test FFCPLN description."""
        desc = get_standard_description("ffcpln")
        assert "FFCPLN" in desc
        assert "https://antifaFM.com" in desc

    def test_get_standard_description_alt(self):
        """Test alternative description."""
        desc = get_standard_description("alt")
        assert "FFCPLN" in desc

    def test_generate_description_with_context(self):
        """Test contextual description."""
        desc = generate_description_with_context(
            song_name="Test Song",
            artist="Test Artist",
        )
        assert "Test Song" in desc
        assert "Test Artist" in desc

    def test_get_hashtags(self):
        """Test hashtag generation."""
        hashtags = get_hashtags()
        assert "#FFCPLN" in hashtags


class TestSchedulerIntegration:
    """Integration tests (require browser connection)."""

    @pytest.mark.skip(reason="Requires live browser session")
    def test_scheduler_connect(self):
        """Test browser connection."""
        from modules.platform_integration.youtube_shorts_scheduler.src.scheduler import (
            YouTubeShortsScheduler,
        )

        scheduler = YouTubeShortsScheduler("move2japan", dry_run=True)
        connected = scheduler.connect_browser()
        assert connected
        scheduler.disconnect()

    @pytest.mark.skip(reason="Requires live browser session")
    def test_scheduler_dry_run(self):
        """Test dry run scheduling."""
        from modules.platform_integration.youtube_shorts_scheduler.src.scheduler import (
            run_scheduler_dae,
        )
        import asyncio

        results = asyncio.run(run_scheduler_dae(
            "move2japan",
            max_videos=1,
            dry_run=True,
        ))
        assert "channel" in results


class TestScheduleDBA:
    """Tests for schedule DBA (PatternMemory integration)."""

    def test_record_schedule_outcome_no_crash(self, tmp_path):
        """Record should not crash; it should return bool."""
        db_path = tmp_path / "pattern_memory.db"
        ok = record_schedule_outcome(
            channel_id="UC_TEST",
            video_id="vid123",
            date_str="Jan 19, 2026",
            time_str="5:30 PM",
            mode="test",
            success=True,
            agent="pytest",
            details={"note": "unit test"},
            db_path=db_path,
        )
        assert ok in (True, False)


class TestIndexWeave:
    """Unit tests for schedule→index weave helpers (no browser)."""

    def test_build_topic_hashtags(self):
        idx = {"metadata": {"topics": ["Education Singularity", "0102", "EDUIT.org"]}}
        tags = build_topic_hashtags(idx, max_tags=5)
        assert tags
        assert all(t.startswith("#") for t in tags)

    def test_build_digital_twin_index_block_contains_header_and_id(self):
        idx = {
            "indexed_at": "2026-01-17T00:00:00Z",
            "metadata": {"topics": ["Education"], "key_points": ["The key insight is X."]},
            "audio": {"segments": [{"start": 0, "end": 10, "text": "hi"}]},
        }
        block = build_digital_twin_index_block(channel_key="undaodu", video_id="abc123", index_json=idx)
        assert "0102 DIGITAL TWIN INDEX v1" in block
        assert "abc123" in block

    def test_weave_description_removes_existing_block(self):
        idx = {
            "indexed_at": "2026-01-17T00:00:00Z",
            "metadata": {"topics": ["Education"], "key_points": ["The key insight is X."]},
            "audio": {"segments": [{"start": 0, "end": 10, "text": "hi"}]},
        }
        block = build_digital_twin_index_block(channel_key="undaodu", video_id="abc123", index_json=idx)
        base = f"hello\n\n{block}\n"
        cleaned = remove_existing_index_block(base)
        assert "0102 DIGITAL TWIN INDEX v1" not in cleaned

        rewoven = weave_description(base_description=base, index_block=block, extra_hashtags=["#Education"])
        # should only contain one header instance
        assert rewoven.count("0102 DIGITAL TWIN INDEX v1") == 1

    def test_update_index_after_schedule_adds_fields(self):
        idx = {"metadata": {}, "audio": {"segments": []}}
        updated = update_index_after_schedule(
            index_json=idx,
            channel_key="move2japan",
            video_id="vid999",
            date_str="Jan 19, 2026",
            time_str="5:30 PM",
            scheduled_by="0102",
            description_index_block="INDEX",
        )
        assert updated["scheduling"]["is_scheduled"] is True
        assert updated["description_sync"]["condensed_index"] == "INDEX"

    def test_build_human_description_context_nonempty(self):
        idx = {
            "metadata": {
                "summary": "This video discusses the education singularity.",
                "topics": ["Education", "Technology"],
                "key_points": ["Education must be democratized."],
            }
        }
        ctx = build_human_description_context(idx)
        assert "Summary" in ctx
        assert "education singularity" in ctx.lower()

    def test_inject_context_into_description_inserts_before_hashtags(self):
        base = "Line1\n\n#TAG1 #TAG2"
        out = inject_context_into_description(base_description=base, context_block="Summary:\nX")
        assert "Summary:\nX" in out
        # context should appear before the hashtag line
        assert out.index("Summary:\nX") < out.index("#TAG1")

    def test_create_stub_index_json_has_expected_fields(self):
        stub = create_stub_index_json(
            channel_key="move2japan",
            video_id="vid123",
            title="My Song",
            base_description="Base",
        )
        assert stub["video_id"] == "vid123"
        assert stub["indexer"] == "scheduler_stub"
        assert stub["metadata"]["summary"]


def _allocate_n(tracker, time_slots, n, max_per_day):
    """
    Allocate n videos one at a time, recording each into the tracker.

    Mirrors the scheduler loop: get_next_available_slot -> increment.
    Returns the list of (date_str, time_str) slots actually allocated
    (None entries mean the window was exhausted).
    """
    allocated = []
    for i in range(n):
        slot = tracker.get_next_available_slot(time_slots, max_per_day=max_per_day)
        if slot is None:
            allocated.append(None)
            continue
        date_str, time_str = slot
        tracker.increment(date_str, f"vid{i}")
        allocated.append((date_str, time_str))
    return allocated


class TestScheduleDensityCap:
    """
    Density-cap tests for SHORTS_SCHEDULE_DENSITY_AND_WINDOW_PHASE1.

    These prove the authoritative HARD_CAP_PER_DAY clamp at the allocator:
    no single day may receive more than HARD_CAP_PER_DAY (=3) videos, even
    when a caller passes a larger max_per_day. NON-VACUOUS: removing the
    clamp (effective_cap = min(max_per_day, HARD_CAP_PER_DAY)) makes the
    8/day case below exceed 3 and the assertions fail.
    """

    def test_hard_cap_constant_is_three(self):
        assert HARD_CAP_PER_DAY == 3

    def test_allocator_caps_at_three_per_day(self):
        """Allocating 4 videos with max_per_day=3 must roll the 4th to the next day."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ScheduleTracker("test_channel", Path(tmpdir))
            time_slots = ["1:30 AM", "3:30 AM", "5:30 AM"]

            allocated = _allocate_n(tracker, time_slots, n=4, max_per_day=3)
            assert all(s is not None for s in allocated)

            # No day exceeds 3
            for date_str, count in tracker.schedule.items():
                assert count <= 3, f"{date_str} got {count} (>3)"

            # The 4th video rolled to a second, distinct day
            distinct_days = {s[0] for s in allocated}
            assert len(distinct_days) == 2
            # First day holds exactly 3, second day holds exactly 1
            counts = sorted(tracker.schedule.values(), reverse=True)
            assert counts == [3, 1]

    def test_clamp_authority_overrides_caller_max_per_day_eight(self):
        """
        Even when called with max_per_day=8 (stale registry value), the
        authoritative clamp must keep every day at <= HARD_CAP_PER_DAY (3).
        This is the load-bearing belt-and-suspenders guarantee.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ScheduleTracker("test_channel", Path(tmpdir))
            time_slots = ["1:30 AM", "3:30 AM", "5:30 AM"]

            # Try to cram 9 videos with the OLD cap of 8 per day.
            allocated = _allocate_n(tracker, time_slots, n=9, max_per_day=8)
            assert all(s is not None for s in allocated)

            # Despite max_per_day=8, no day exceeds the hard cap of 3.
            for date_str, count in tracker.schedule.items():
                assert count <= HARD_CAP_PER_DAY, f"{date_str} got {count} (>{HARD_CAP_PER_DAY})"

            # 9 videos at 3/day => exactly 3 distinct days, each full.
            assert len(tracker.schedule) == 3
            assert sorted(tracker.schedule.values()) == [3, 3, 3]

    def test_report_threshold_matches_effective_cap(self):
        """
        get_summary's full/partial day counts must use HARD_CAP_PER_DAY,
        not a lying hard-coded value. A day with exactly the cap is 'full';
        one below it is 'partial'.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ScheduleTracker("test_channel", Path(tmpdir))
            # One full day (== cap) and one partial day (cap - 1).
            for i in range(HARD_CAP_PER_DAY):
                tracker.increment("Jan 5, 2026", f"full{i}")
            for i in range(HARD_CAP_PER_DAY - 1):
                tracker.increment("Jan 6, 2026", f"part{i}")

            summary = tracker.get_summary()
            assert summary["full_days"] == 1
            assert summary["partial_days"] == 1
            assert summary["total_scheduled"] == (2 * HARD_CAP_PER_DAY - 1)
