"""Centralized DAEmon Event Store — Layer 1.

Dual-write persistence: JSONL (append-only DR) + SQLite (indexed queries).
Adapted from FAMEventStore (fam_daemon.py:233-512) — same gold standard pattern.

WSP Compliance:
    WSP 72: Only imports Layer 0 schemas (no cross-module deps)
    WSP 84: Reuses FAMEventStore architecture
"""

import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from modules.infrastructure.dae_daemon.src.schemas import DAEEvent, DAEEventType

logger = logging.getLogger(__name__)


class DAEEventStore:
    """Dual-write event store for the cardiovascular system.

    - Append-only JSONL for disaster recovery
    - SQLite for fast querying and deduplication
    - Replay-safe with dedupe_key enforcement
    - Atomic sequence ID generation (thread-safe)
    """

    SQLITE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS dae_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT UNIQUE NOT NULL,
        sequence_id INTEGER UNIQUE NOT NULL,
        dedupe_key TEXT UNIQUE NOT NULL,
        event_type TEXT NOT NULL,
        dae_id TEXT NOT NULL,
        actor_id TEXT,
        payload_json TEXT,
        timestamp REAL NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_dae_events_type ON dae_events(event_type);
    CREATE INDEX IF NOT EXISTS idx_dae_events_dae ON dae_events(dae_id);
    CREATE INDEX IF NOT EXISTS idx_dae_events_timestamp ON dae_events(timestamp);
    """

    def __init__(
        self,
        data_dir: Path,
        jsonl_filename: str = "dae_events.jsonl",
        sqlite_filename: str = "dae_audit.db",
    ) -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._jsonl_path = self._data_dir / jsonl_filename
        self._sqlite_path = self._data_dir / sqlite_filename

        self._lock = threading.Lock()
        self._sequence_counter = 0

        self._init_sqlite()
        self._load_sequence_counter()

        logger.info(
            "[DAE-STORE] Initialized | jsonl=%s sqlite=%s sequence=%d",
            self._jsonl_path, self._sqlite_path, self._sequence_counter,
        )

    # ------------------------------------------------------------------
    # Init helpers
    # ------------------------------------------------------------------

    def _init_sqlite(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.executescript(self.SQLITE_SCHEMA)
            conn.commit()

    def _load_sequence_counter(self) -> None:
        with self._connect() as conn:
            cursor = conn.execute("SELECT MAX(sequence_id) FROM dae_events")
            row = cursor.fetchone()
            if row and row[0] is not None:
                self._sequence_counter = row[0]

    def _connect(self) -> sqlite3.Connection:
        """Return a configured SQLite connection for event-store operations."""
        conn = sqlite3.connect(str(self._sqlite_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _next_sequence_id(self) -> int:
        """Get next sequence_id, refreshing from DB to avoid race conditions."""
        # Refresh from DB to handle multi-process scenarios
        with self._connect() as conn:
            cursor = conn.execute("SELECT MAX(sequence_id) FROM dae_events")
            row = cursor.fetchone()
            if row and row[0] is not None:
                self._sequence_counter = max(self._sequence_counter, row[0])
        self._sequence_counter += 1
        return self._sequence_counter

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def write(self, event: DAEEvent, _retry: int = 0) -> Tuple[bool, str]:
        """Write event to both JSONL and SQLite.

        Returns (success, message).
        Retries up to 3 times on sequence_id collision (multi-process race).
        """
        with self._lock:
            try:
                if self._is_duplicate(event.dedupe_key):
                    return (False, f"duplicate: {event.dedupe_key}")

                if event.sequence_id == 0:
                    event.sequence_id = self._next_sequence_id()

                self._write_jsonl(event)
                self._write_sqlite(event)

                logger.debug(
                    "[DAE-STORE] Written | seq=%d type=%s dae=%s",
                    event.sequence_id, event.event_type.value, event.dae_id,
                )
                return (True, "ok")

            except Exception as e:
                # Retry on sequence_id collision (multi-process race condition)
                if "UNIQUE constraint failed: dae_events.sequence_id" in str(e) and _retry < 3:
                    logger.warning("[DAE-STORE] Sequence collision, retrying (%d/3)...", _retry + 1)
                    event.sequence_id = 0  # Reset to get fresh sequence_id
                    return self.write(event, _retry=_retry + 1)
                logger.error("[DAE-STORE] Write failed: %s", e)
                return (False, f"error: {e}")

    def _is_duplicate(self, dedupe_key: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM dae_events WHERE dedupe_key = ? LIMIT 1",
                (dedupe_key,),
            )
            return cursor.fetchone() is not None

    def _write_jsonl(self, event: DAEEvent) -> None:
        with open(self._jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), default=str) + "\n")

    def _write_sqlite(self, event: DAEEvent) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dae_events (
                    event_id, sequence_id, dedupe_key, event_type,
                    dae_id, actor_id, payload_json, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.sequence_id,
                    event.dedupe_key,
                    event.event_type.value,
                    event.dae_id,
                    event.actor_id,
                    json.dumps(event.payload, default=str),
                    event.timestamp,
                ),
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(
        self,
        event_type: Optional[str] = None,
        dae_id: Optional[str] = None,
        since_sequence: int = 0,
        limit: int = 100,
    ) -> List[DAEEvent]:
        """Query events from SQLite."""
        conditions = ["sequence_id > ?"]
        params: List[Any] = [since_sequence]

        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if dae_id:
            conditions.append("dae_id = ?")
            params.append(dae_id)

        where_clause = " AND ".join(conditions)
        params.append(limit)

        with self._connect() as conn:
            cursor = conn.execute(
                f"""
                SELECT * FROM dae_events
                WHERE {where_clause}
                ORDER BY sequence_id ASC
                LIMIT ?
                """,
                tuple(params),
            )
            rows = cursor.fetchall()

        events = []
        for row in rows:
            events.append(
                DAEEvent(
                    event_id=row["event_id"],
                    sequence_id=row["sequence_id"],
                    dedupe_key=row["dedupe_key"],
                    event_type=DAEEventType(row["event_type"]),
                    dae_id=row["dae_id"],
                    actor_id=row["actor_id"] or "system",
                    payload=json.loads(row["payload_json"] or "{}"),
                    timestamp=row["timestamp"],
                )
            )
        return events

    def query_recent(
        self,
        event_type: Optional[str] = None,
        dae_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[DAEEvent]:
        """Return the most recent events, ordered oldest->newest within the window."""
        conditions = ["1=1"]
        params: List[Any] = []

        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if dae_id:
            conditions.append("dae_id = ?")
            params.append(dae_id)

        where_clause = " AND ".join(conditions)
        params.append(limit)

        with self._connect() as conn:
            cursor = conn.execute(
                f"""
                SELECT * FROM dae_events
                WHERE {where_clause}
                ORDER BY sequence_id DESC
                LIMIT ?
                """,
                tuple(params),
            )
            rows = list(reversed(cursor.fetchall()))

        events = []
        for row in rows:
            events.append(
                DAEEvent(
                    event_id=row["event_id"],
                    sequence_id=row["sequence_id"],
                    dedupe_key=row["dedupe_key"],
                    event_type=DAEEventType(row["event_type"]),
                    dae_id=row["dae_id"],
                    actor_id=row["actor_id"] or "system",
                    payload=json.loads(row["payload_json"] or "{}"),
                    timestamp=row["timestamp"],
                )
            )
        return events

    # ------------------------------------------------------------------
    # Stats / Parity
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get event store statistics."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM dae_events")
            total = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT event_type, COUNT(*) FROM dae_events GROUP BY event_type"
            )
            by_type = {row[0]: row[1] for row in cursor.fetchall()}

            cursor = conn.execute("SELECT MAX(sequence_id) FROM dae_events")
            max_seq = cursor.fetchone()[0] or 0

        return {
            "total_events": total,
            "max_sequence_id": max_seq,
            "events_by_type": by_type,
            "jsonl_path": str(self._jsonl_path),
            "sqlite_path": str(self._sqlite_path),
        }

    def verify_parity(self) -> Tuple[bool, str]:
        """Verify JSONL line count == SQLite row count."""
        try:
            jsonl_count = 0
            if self._jsonl_path.exists():
                with open(self._jsonl_path, "r", encoding="utf-8") as f:
                    jsonl_count = sum(1 for _ in f)

            with self._connect() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM dae_events")
                sqlite_count = cursor.fetchone()[0]

            if jsonl_count == sqlite_count:
                return (True, f"parity ok: {jsonl_count} events")
            else:
                return (False, f"parity mismatch: jsonl={jsonl_count} sqlite={sqlite_count}")

        except Exception as e:
            return (False, f"parity check failed: {e}")
