#!/usr/bin/env python3
"""
YouTube DAE Telemetry Storage Module

Lightweight SQLite-based telemetry ingestion for YouTube live stream monitoring.
Stores stream sessions, heartbeats, moderation actions, and channel operations.

Phase 2 (G3): Added youtube_channel_operations table for per-channel tracking.
This provides a sentinel-queryable data surface for AI Overseer without
persisting derived classifications (raw facts only).

WSP References:
- WSP 72: Module Independence (standalone SQLite storage)
- WSP 78: Database Integration (agent coordination)
- WSP 91: DAEMON Observability (cardiovascular telemetry)
- WSP 22: Documentation (ModLog integration)
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Default database path (shared with Vision DAE)
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "foundups.db"


class YouTubeTelemetryStore:
    """
    SQLite-based storage for YouTube DAE cardiovascular telemetry.

    Thread-safe implementation with automatic table creation and
    concurrent write support via isolation_level=None (autocommit).

    Tables:
        - youtube_streams: Stream session metadata
        - youtube_heartbeats: Periodic health pulses
        - youtube_moderation_actions: Spam/toxic blocks
        - youtube_channel_operations: Per-channel operation timestamps (G3)
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize YouTube telemetry store.

        Args:
            db_path: Path to SQLite database file (creates if missing)
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_tables()

    @contextmanager
    def _get_connection(self):
        """
        Context manager for thread-safe SQLite connections.

        Uses isolation_level=None for autocommit mode to handle
        concurrent writes safely.

        Yields:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(
            self.db_path,
            isolation_level=None,  # Autocommit for concurrent writes
            timeout=10.0  # Wait up to 10s for lock
        )
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_tables(self):
        """
        Create YouTube DAE telemetry tables if they don't exist.

        Schema:
            youtube_streams: Stream session metadata
            youtube_heartbeats: Periodic health pulses
            youtube_moderation_actions: Spam/toxic blocks
        """
        with self._get_connection() as conn:
            # Table 1: Stream Sessions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS youtube_streams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT NOT NULL,
                    channel_name TEXT NOT NULL,
                    channel_id TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_minutes INTEGER,
                    chat_messages INTEGER DEFAULT 0,
                    moderation_actions INTEGER DEFAULT 0,
                    banter_responses INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active'
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_youtube_streams_start_time
                ON youtube_streams(start_time DESC)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_youtube_streams_video_id
                ON youtube_streams(video_id)
            """)

            # Table 2: Heartbeats
            conn.execute("""
                CREATE TABLE IF NOT EXISTS youtube_heartbeats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    stream_active BOOLEAN DEFAULT 0,
                    chat_messages_per_min REAL DEFAULT 0.0,
                    moderation_actions INTEGER DEFAULT 0,
                    banter_responses INTEGER DEFAULT 0,
                    uptime_seconds REAL DEFAULT 0.0,
                    memory_mb REAL,
                    cpu_percent REAL
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_youtube_heartbeats_timestamp
                ON youtube_heartbeats(timestamp DESC)
            """)

            # Table 3: Moderation Actions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS youtube_moderation_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    stream_id INTEGER,
                    author_id TEXT,
                    message_text TEXT,
                    violation_type TEXT,
                    action_taken TEXT,
                    confidence REAL DEFAULT 0.0,
                    FOREIGN KEY (stream_id) REFERENCES youtube_streams(id)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_youtube_moderation_timestamp
                ON youtube_moderation_actions(timestamp DESC)
            """)

            # Table 4: Channel Operations (G3 - Phase 2)
            # Raw facts only - no sentinel classifications
            conn.execute("""
                CREATE TABLE IF NOT EXISTS youtube_channel_operations (
                    channel_id TEXT PRIMARY KEY,
                    channel_name TEXT,
                    last_comment_scan TEXT,
                    last_scheduling_scan TEXT,
                    last_indexing_scan TEXT,
                    last_rotation_success TEXT,
                    consecutive_failures INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_youtube_channel_ops_last_comment
                ON youtube_channel_operations(last_comment_scan DESC)
            """)

            logger.info("YouTube DAE telemetry tables ensured")

    def record_stream_start(
        self,
        video_id: str,
        channel_name: str,
        channel_id: Optional[str] = None
    ) -> int:
        """
        Record new stream session start.

        Args:
            video_id: YouTube video ID
            channel_name: Channel display name
            channel_id: YouTube channel ID (optional)

        Returns:
            Stream session ID
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO youtube_streams (video_id, channel_name, channel_id, start_time, status)
                VALUES (?, ?, ?, ?, 'active')
            """, (video_id, channel_name, channel_id, timestamp))

            stream_id = cursor.lastrowid
            logger.info(f"Recorded stream start: {video_id} (session {stream_id})")
            return stream_id

    def record_stream_end(self, stream_id: int):
        """
        Record stream session end.

        Args:
            stream_id: Stream session ID from record_stream_start()
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            # Calculate duration
            cursor = conn.execute("""
                SELECT start_time FROM youtube_streams WHERE id = ?
            """, (stream_id,))
            row = cursor.fetchone()

            if row:
                start_time = datetime.fromisoformat(row[0])
                end_time = datetime.fromisoformat(timestamp)
                duration_minutes = int((end_time - start_time).total_seconds() / 60)

                conn.execute("""
                    UPDATE youtube_streams
                    SET end_time = ?, duration_minutes = ?, status = 'ended'
                    WHERE id = ?
                """, (timestamp, duration_minutes, stream_id))

                logger.info(f"Recorded stream end: session {stream_id} ({duration_minutes} min)")

    def record_heartbeat(
        self,
        status: str,
        stream_active: bool = False,
        chat_messages_per_min: float = 0.0,
        moderation_actions: int = 0,
        banter_responses: int = 0,
        uptime_seconds: float = 0.0,
        memory_mb: Optional[float] = None,
        cpu_percent: Optional[float] = None
    ):
        """
        Record periodic heartbeat pulse.

        Args:
            status: Health status (healthy, warning, critical, offline)
            stream_active: Whether actively monitoring a stream
            chat_messages_per_min: Recent chat message rate
            moderation_actions: Moderation actions taken
            banter_responses: Banter responses sent
            uptime_seconds: DAE uptime
            memory_mb: Memory usage in MB
            cpu_percent: CPU usage percentage
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO youtube_heartbeats (
                    timestamp, status, stream_active, chat_messages_per_min,
                    moderation_actions, banter_responses, uptime_seconds,
                    memory_mb, cpu_percent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, status, stream_active, chat_messages_per_min,
                moderation_actions, banter_responses, uptime_seconds,
                memory_mb, cpu_percent
            ))

    def record_moderation_action(
        self,
        stream_id: Optional[int],
        author_id: str,
        message_text: str,
        violation_type: str,
        action_taken: str,
        confidence: float = 0.0
    ):
        """
        Record moderation action (spam block, toxic flag, etc.).

        Args:
            stream_id: Active stream session ID (None if no stream)
            author_id: Message author ID
            message_text: Original message text
            violation_type: Type of violation (spam, toxic, caps, repetitive)
            action_taken: Action taken (block, warn, delete)
            confidence: Confidence score (0.0-1.0)
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO youtube_moderation_actions (
                    timestamp, stream_id, author_id, message_text,
                    violation_type, action_taken, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, stream_id, author_id, message_text,
                violation_type, action_taken, confidence
            ))

    def get_recent_streams(self, limit: int = 10) -> List[Dict]:
        """
        Get recent stream sessions.

        Args:
            limit: Maximum number of streams to return

        Returns:
            List of stream session dicts
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, video_id, channel_name, channel_id, start_time, end_time,
                       duration_minutes, chat_messages, moderation_actions,
                       banter_responses, status
                FROM youtube_streams
                ORDER BY start_time DESC
                LIMIT ?
            """, (limit,))

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_recent_heartbeats(self, limit: int = 50) -> List[Dict]:
        """
        Get recent heartbeat pulses.

        Args:
            limit: Maximum number of heartbeats to return

        Returns:
            List of heartbeat dicts
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT timestamp, status, stream_active, chat_messages_per_min,
                       moderation_actions, banter_responses, uptime_seconds,
                       memory_mb, cpu_percent
                FROM youtube_heartbeats
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    # =========================================================================
    # G3: Per-Channel Operation Tracking (Phase 2)
    # =========================================================================

    def record_channel_operation(
        self,
        channel_id: str,
        channel_name: str,
        operation: str,
        success: bool = True,
    ) -> None:
        """
        Record operation timestamp for a channel.

        This provides a sentinel-queryable data surface for AI Overseer.
        Only raw facts are persisted - no derived classifications.

        Args:
            channel_id: YouTube channel ID
            channel_name: Channel display name
            operation: Operation type (comment_scan, scheduling_scan, indexing_scan, rotation)
            success: Whether operation succeeded
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Map operation to column name
        column_map = {
            "comment_scan": "last_comment_scan",
            "comments": "last_comment_scan",
            "scheduling_scan": "last_scheduling_scan",
            "shorts": "last_scheduling_scan",
            "indexing_scan": "last_indexing_scan",
            "indexing": "last_indexing_scan",
            "rotation": "last_rotation_success",
        }

        column = column_map.get(operation)
        if not column:
            logger.warning(f"Unknown operation type: {operation}")
            return

        with self._get_connection() as conn:
            # Check if channel exists
            cursor = conn.execute(
                "SELECT consecutive_failures FROM youtube_channel_operations WHERE channel_id = ?",
                (channel_id,)
            )
            row = cursor.fetchone()

            if row is None:
                # Insert new channel
                conn.execute(f"""
                    INSERT INTO youtube_channel_operations (channel_id, channel_name, {column}, consecutive_failures)
                    VALUES (?, ?, ?, ?)
                """, (channel_id, channel_name, timestamp, 0 if success else 1))
            else:
                # Update existing channel
                current_failures = row[0] or 0
                new_failures = 0 if success else current_failures + 1

                conn.execute(f"""
                    UPDATE youtube_channel_operations
                    SET channel_name = ?, {column} = ?, consecutive_failures = ?
                    WHERE channel_id = ?
                """, (channel_name, timestamp, new_failures, channel_id))

            logger.debug(f"Recorded {operation} for {channel_name}: success={success}")

    def get_stale_channels(
        self,
        operation: str,
        max_age_hours: int = 24,
    ) -> List[Dict]:
        """
        Find channels not processed within max_age_hours.

        This is a sentinel-queryable surface - AI Overseer can use this
        to detect channels needing attention without storing classifications.

        Args:
            operation: Operation type to check (comment_scan, scheduling_scan, indexing_scan)
            max_age_hours: Maximum age in hours before channel is considered stale

        Returns:
            List of stale channel dicts with channel_id, channel_name, last_scan, hours_stale
        """
        column_map = {
            "comment_scan": "last_comment_scan",
            "comments": "last_comment_scan",
            "scheduling_scan": "last_scheduling_scan",
            "shorts": "last_scheduling_scan",
            "indexing_scan": "last_indexing_scan",
            "indexing": "last_indexing_scan",
        }

        column = column_map.get(operation)
        if not column:
            logger.warning(f"Unknown operation type: {operation}")
            return []

        cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()

        with self._get_connection() as conn:
            # Find channels where last scan is older than cutoff OR is NULL
            cursor = conn.execute(f"""
                SELECT channel_id, channel_name, {column} as last_scan, consecutive_failures
                FROM youtube_channel_operations
                WHERE {column} IS NULL OR {column} < ?
                ORDER BY {column} ASC NULLS FIRST
            """, (cutoff,))

            results = []
            now = datetime.now(timezone.utc)
            for row in cursor.fetchall():
                channel_id, channel_name, last_scan, failures = row
                if last_scan:
                    last_dt = datetime.fromisoformat(last_scan.replace('Z', '+00:00'))
                    hours_stale = (now - last_dt).total_seconds() / 3600
                else:
                    hours_stale = float('inf')

                results.append({
                    "channel_id": channel_id,
                    "channel_name": channel_name,
                    "last_scan": last_scan,
                    "hours_stale": round(hours_stale, 1),
                    "consecutive_failures": failures or 0,
                })

            return results

    def get_channel_operation_stats(self, channel_id: str) -> Optional[Dict]:
        """
        Get operation stats for a specific channel.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Dict with all operation timestamps and failure count, or None
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT channel_id, channel_name, last_comment_scan, last_scheduling_scan,
                       last_indexing_scan, last_rotation_success, consecutive_failures
                FROM youtube_channel_operations
                WHERE channel_id = ?
            """, (channel_id,))

            row = cursor.fetchone()
            if not row:
                return None

            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))


if __name__ == "__main__":
    # Test schema creation
    print("Testing YouTube Telemetry Store...")
    store = YouTubeTelemetryStore()

    # Test stream recording
    stream_id = store.record_stream_start("test_video_123", "Test Channel")
    print(f"Created stream session: {stream_id}")

    # Test heartbeat recording
    store.record_heartbeat(
        status="healthy",
        stream_active=True,
        chat_messages_per_min=15.5,
        uptime_seconds=120.0
    )
    print("Recorded heartbeat")

    # Test moderation recording
    store.record_moderation_action(
        stream_id=stream_id,
        author_id="user123",
        message_text="SPAM MESSAGE!!!",
        violation_type="spam",
        action_taken="block",
        confidence=0.95
    )
    print("Recorded moderation action")

    # Test stream end
    store.record_stream_end(stream_id)
    print("Ended stream session")

    # Query recent data
    streams = store.get_recent_streams(limit=5)
    print(f"\nRecent streams: {len(streams)}")

    heartbeats = store.get_recent_heartbeats(limit=5)
    print(f"Recent heartbeats: {len(heartbeats)}")

    print("\nSchema test complete!")
