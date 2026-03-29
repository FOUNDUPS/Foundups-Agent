#!/usr/bin/env python3
"""
Test G3: Per-Channel Operation Tracking (Phase 2)

Tests the youtube_channel_operations table and its associated methods
in YouTubeTelemetryStore. These track raw facts (timestamps, failures)
for AI Overseer sentinel queries - no derived classifications.

WSP 91: Observability
WSP 72: Module Independence (isolated tests)

Author: 0102
Created: 2026-03-30
"""

import gc
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from modules.communication.livechat.src.youtube_telemetry_store import YouTubeTelemetryStore


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    store = YouTubeTelemetryStore(db_path=db_path)
    yield store

    # Cleanup
    del store
    gc.collect()  # Release SQLite file handles
    try:
        db_path.unlink()
    except Exception:
        pass


class TestChannelOperationsTable:
    """Test youtube_channel_operations table creation."""

    def test_table_created(self, temp_db):
        """Verify table is created on init."""
        with temp_db._get_connection() as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='youtube_channel_operations'
            """)
            assert cursor.fetchone() is not None

    def test_index_created(self, temp_db):
        """Verify index is created for stale channel queries."""
        with temp_db._get_connection() as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='index' AND name='idx_youtube_channel_ops_last_comment'
            """)
            assert cursor.fetchone() is not None


class TestRecordChannelOperation:
    """Test record_channel_operation() method."""

    def test_insert_new_channel(self, temp_db):
        """Test inserting a new channel operation."""
        temp_db.record_channel_operation(
            channel_id="UC123",
            channel_name="TestChannel",
            operation="comment_scan",
            success=True,
        )

        result = temp_db.get_channel_operation_stats("UC123")
        assert result is not None
        assert result["channel_id"] == "UC123"
        assert result["channel_name"] == "TestChannel"
        assert result["last_comment_scan"] is not None
        assert result["consecutive_failures"] == 0

    def test_update_existing_channel(self, temp_db):
        """Test updating an existing channel."""
        temp_db.record_channel_operation(
            channel_id="UC123",
            channel_name="TestChannel",
            operation="comment_scan",
            success=True,
        )

        # Update with shorts scan
        temp_db.record_channel_operation(
            channel_id="UC123",
            channel_name="TestChannel",
            operation="shorts",
            success=True,
        )

        result = temp_db.get_channel_operation_stats("UC123")
        assert result["last_comment_scan"] is not None
        assert result["last_scheduling_scan"] is not None

    def test_operation_type_mapping(self, temp_db):
        """Test all operation types map to correct columns."""
        operations = [
            ("comment_scan", "last_comment_scan"),
            ("comments", "last_comment_scan"),
            ("scheduling_scan", "last_scheduling_scan"),
            ("shorts", "last_scheduling_scan"),
            ("indexing_scan", "last_indexing_scan"),
            ("indexing", "last_indexing_scan"),
            ("rotation", "last_rotation_success"),
        ]

        for idx, (operation, expected_column) in enumerate(operations):
            channel_id = f"UC{idx}"
            temp_db.record_channel_operation(
                channel_id=channel_id,
                channel_name=f"Channel{idx}",
                operation=operation,
                success=True,
            )
            result = temp_db.get_channel_operation_stats(channel_id)
            assert result[expected_column] is not None, f"Failed for {operation}"

    def test_unknown_operation_logged(self, temp_db, caplog):
        """Test unknown operation types are logged as warnings."""
        import logging
        with caplog.at_level(logging.WARNING):
            temp_db.record_channel_operation(
                channel_id="UC123",
                channel_name="TestChannel",
                operation="unknown_op",
                success=True,
            )
        assert "Unknown operation type" in caplog.text

    def test_consecutive_failures_increment(self, temp_db):
        """Test consecutive_failures increments on failure."""
        # First failure
        temp_db.record_channel_operation(
            channel_id="UC123",
            channel_name="TestChannel",
            operation="comment_scan",
            success=False,
        )
        result = temp_db.get_channel_operation_stats("UC123")
        assert result["consecutive_failures"] == 1

        # Second failure
        temp_db.record_channel_operation(
            channel_id="UC123",
            channel_name="TestChannel",
            operation="comment_scan",
            success=False,
        )
        result = temp_db.get_channel_operation_stats("UC123")
        assert result["consecutive_failures"] == 2

    def test_consecutive_failures_reset(self, temp_db):
        """Test consecutive_failures resets to 0 on success."""
        # Two failures
        for _ in range(2):
            temp_db.record_channel_operation(
                channel_id="UC123",
                channel_name="TestChannel",
                operation="comment_scan",
                success=False,
            )

        # Success resets
        temp_db.record_channel_operation(
            channel_id="UC123",
            channel_name="TestChannel",
            operation="comment_scan",
            success=True,
        )
        result = temp_db.get_channel_operation_stats("UC123")
        assert result["consecutive_failures"] == 0


class TestGetStaleChannels:
    """Test get_stale_channels() method."""

    def test_no_stale_channels(self, temp_db):
        """Test returns empty list when all channels are fresh."""
        temp_db.record_channel_operation(
            channel_id="UC123",
            channel_name="FreshChannel",
            operation="comment_scan",
            success=True,
        )

        stale = temp_db.get_stale_channels("comment_scan", max_age_hours=24)
        assert len(stale) == 0

    def test_stale_channel_detected(self, temp_db):
        """Test stale channel is detected based on max_age_hours."""
        # Insert channel and manually backdate
        temp_db.record_channel_operation(
            channel_id="UC123",
            channel_name="StaleChannel",
            operation="comment_scan",
            success=True,
        )

        # Manually backdate the timestamp
        old_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        with temp_db._get_connection() as conn:
            conn.execute("""
                UPDATE youtube_channel_operations
                SET last_comment_scan = ?
                WHERE channel_id = ?
            """, (old_time, "UC123"))

        stale = temp_db.get_stale_channels("comment_scan", max_age_hours=24)
        assert len(stale) == 1
        assert stale[0]["channel_id"] == "UC123"
        assert stale[0]["hours_stale"] > 24

    def test_null_timestamp_is_stale(self, temp_db):
        """Test channel with NULL timestamp is considered stale."""
        # Insert channel with only indexing scan (comment_scan will be NULL)
        temp_db.record_channel_operation(
            channel_id="UC123",
            channel_name="PartialChannel",
            operation="indexing",
            success=True,
        )

        stale = temp_db.get_stale_channels("comment_scan", max_age_hours=24)
        assert len(stale) == 1
        assert stale[0]["channel_id"] == "UC123"
        assert stale[0]["hours_stale"] == float('inf')

    def test_stale_channels_ordered(self, temp_db):
        """Test stale channels are ordered by staleness (oldest first)."""
        # Channel A: 72 hours stale
        temp_db.record_channel_operation(
            channel_id="UCA",
            channel_name="OldestChannel",
            operation="comment_scan",
            success=True,
        )
        old_time_a = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        with temp_db._get_connection() as conn:
            conn.execute(
                "UPDATE youtube_channel_operations SET last_comment_scan = ? WHERE channel_id = ?",
                (old_time_a, "UCA")
            )

        # Channel B: 48 hours stale
        temp_db.record_channel_operation(
            channel_id="UCB",
            channel_name="OlderChannel",
            operation="comment_scan",
            success=True,
        )
        old_time_b = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        with temp_db._get_connection() as conn:
            conn.execute(
                "UPDATE youtube_channel_operations SET last_comment_scan = ? WHERE channel_id = ?",
                (old_time_b, "UCB")
            )

        stale = temp_db.get_stale_channels("comment_scan", max_age_hours=24)
        assert len(stale) == 2
        assert stale[0]["channel_id"] == "UCA"  # Oldest first
        assert stale[1]["channel_id"] == "UCB"

    def test_includes_consecutive_failures(self, temp_db):
        """Test stale channel results include consecutive_failures."""
        temp_db.record_channel_operation(
            channel_id="UC123",
            channel_name="FailingChannel",
            operation="comment_scan",
            success=False,
        )
        temp_db.record_channel_operation(
            channel_id="UC123",
            channel_name="FailingChannel",
            operation="comment_scan",
            success=False,
        )

        # Backdate to make it stale
        old_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        with temp_db._get_connection() as conn:
            conn.execute(
                "UPDATE youtube_channel_operations SET last_comment_scan = ? WHERE channel_id = ?",
                (old_time, "UC123")
            )

        stale = temp_db.get_stale_channels("comment_scan", max_age_hours=24)
        assert len(stale) == 1
        assert stale[0]["consecutive_failures"] == 2


class TestGetChannelOperationStats:
    """Test get_channel_operation_stats() method."""

    def test_returns_none_for_unknown_channel(self, temp_db):
        """Test returns None for unknown channel."""
        result = temp_db.get_channel_operation_stats("UNKNOWN")
        assert result is None

    def test_returns_all_columns(self, temp_db):
        """Test returns all expected columns."""
        temp_db.record_channel_operation(
            channel_id="UC123",
            channel_name="TestChannel",
            operation="comment_scan",
            success=True,
        )

        result = temp_db.get_channel_operation_stats("UC123")

        expected_keys = [
            "channel_id",
            "channel_name",
            "last_comment_scan",
            "last_scheduling_scan",
            "last_indexing_scan",
            "last_rotation_success",
            "consecutive_failures",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"


class TestRawFactsOnly:
    """
    Verify this layer stores raw facts only - no derived classifications.

    Per STT/TTS boundary: sentinel classifications (DEAD/ALIVE/WEAK) are
    computed at query time by AI Overseer, NOT stored here.
    """

    def test_no_sentinel_signal_column(self, temp_db):
        """Verify no sentinel_signal or classification column exists."""
        with temp_db._get_connection() as conn:
            cursor = conn.execute("""
                PRAGMA table_info(youtube_channel_operations)
            """)
            columns = [row[1] for row in cursor.fetchall()]

        forbidden_columns = ["sentinel_signal", "classification", "status", "health"]
        for col in forbidden_columns:
            assert col not in columns, f"Found forbidden column: {col}"

    def test_stores_timestamps_not_judgments(self, temp_db):
        """Verify only timestamps and counts are stored."""
        temp_db.record_channel_operation(
            channel_id="UC123",
            channel_name="TestChannel",
            operation="comment_scan",
            success=True,
        )

        result = temp_db.get_channel_operation_stats("UC123")

        # These are raw facts
        assert isinstance(result["last_comment_scan"], str)  # ISO timestamp
        assert isinstance(result["consecutive_failures"], int)  # Count

        # These should NOT exist (AI derives them)
        assert "health_status" not in result
        assert "priority" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
