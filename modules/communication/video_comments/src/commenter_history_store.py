"""
Commenter History Store - WSP 60 Module Memory for Studio Engagement
====================================================================

Stores per-commenter interaction history for YouTube Studio comment engagement.
This provides contextual memory for intelligent replies (Grok/LM Studio) and
supports later Gemma/Qwen routing (WSP 77 / WSP 96).

Data stored here is *local* and scoped to the `communication/video_comments` module.
It is not intended for cross-service use without explicit integration.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


MEMORY_DIR = Path(__file__).resolve().parents[1] / "memory"
DB_PATH = MEMORY_DIR / "commenter_history.db"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_handle(handle: Optional[str]) -> str:
    if not handle:
        return ""
    handle = handle.strip()
    if handle.startswith("@"):
        handle = handle[1:]
    return " ".join(handle.split())


def make_commenter_key(*, channel_id: Optional[str], handle: Optional[str]) -> str:
    """
    Stable commenter key for lookups.

    Preference order:
    1) YouTube channel id (best stability)
    2) normalized handle (lowercased)
    3) "unknown"
    """
    if channel_id:
        return channel_id.strip()
    normalized = _normalize_handle(handle)
    if normalized:
        return normalized.lower()
    return "unknown"


@dataclass(frozen=True)
class CommenterInteraction:
    commenter_key: str
    commenter_handle: str
    commenter_channel_id: Optional[str]
    comment_text: str
    reply_text: Optional[str]
    liked: bool
    hearted: bool
    replied: bool
    commenter_type: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commenter_key": self.commenter_key,
            "commenter_handle": self.commenter_handle,
            "commenter_channel_id": self.commenter_channel_id,
            "comment_text": self.comment_text,
            "reply_text": self.reply_text,
            "liked": self.liked,
            "hearted": self.hearted,
            "replied": self.replied,
            "commenter_type": self.commenter_type,
            "created_at": self.created_at,
        }


class CommenterHistoryStore:
    """
    SQLite store for per-commenter history (WSP 60).

    Design goals (PoC):
    - Small schema
    - Append-only interactions
    - Fast retrieval of last N interactions per commenter
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path or os.getenv("YT_COMMENT_HISTORY_DB", str(DB_PATH))).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, isolation_level=None, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS commenter_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    commenter_key TEXT NOT NULL,
                    commenter_handle TEXT,
                    commenter_channel_id TEXT,
                    comment_text TEXT,
                    reply_text TEXT,
                    liked INTEGER NOT NULL,
                    hearted INTEGER NOT NULL,
                    replied INTEGER NOT NULL,
                    commenter_type TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_commenter_interactions_key_time
                ON commenter_interactions(commenter_key, created_at DESC)
                """
            )
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reply_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    target_key TEXT NOT NULL,
                    original_context TEXT NOT NULL,
                    reply_text TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('unknown', 'verified', 'not_submitted')),
                    evidence TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_reply_attempt_active_target
                ON reply_attempts(target_key) WHERE status IN ('unknown', 'verified')
            """)

    @staticmethod
    def reply_target_key(original_context: Dict[str, Any]) -> str:
        """Identify a real thread independently of the generated draft or its row position."""
        required = ("_target_channel_id", "video_id", "comment_id", "text")
        if not isinstance(original_context, dict) or any(
            not isinstance(original_context.get(key), str) or not original_context[key].strip()
            for key in required
        ):
            raise ValueError("stable_comment_identity_required")
        author = original_context.get("author_handle") or original_context.get("author_name")
        if not isinstance(author, str) or author.strip().lower() in ("", "unknown", "@unknown"):
            raise ValueError("stable_comment_author_required")
        identity = [original_context[key] for key in required[:3]]
        return hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode("utf-8")).hexdigest()

    def begin_reply_attempt(self, original_context: Dict[str, Any], reply_text: str) -> Optional[str]:
        """Durably reserve before browser work; unknown survives crashes and new drafts."""
        target_key = self.reply_target_key(original_context)
        if not isinstance(reply_text, str) or not reply_text.strip():
            raise ValueError("nonempty_reply_required")
        attempt_id, now = uuid4().hex, _utc_now_iso()
        with self._get_connection() as conn:
            conn.execute("PRAGMA synchronous=FULL")
            cursor = conn.execute("""
                INSERT OR IGNORE INTO reply_attempts
                (attempt_id, target_key, original_context, reply_text, status, evidence, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'unknown', '{}', ?, ?)
            """, (attempt_id, target_key, json.dumps(original_context, ensure_ascii=False), reply_text, now, now))
        return attempt_id if cursor.rowcount == 1 else None

    def finish_reply_attempt(self, attempt_id: str, status: str, evidence: Dict[str, Any]) -> None:
        """Only explicit no-click evidence releases a reservation; unknown never expires."""
        if status not in ("unknown", "verified", "not_submitted"):
            raise ValueError("invalid_reply_attempt_status")
        with self._get_connection() as conn:
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute("""
                UPDATE reply_attempts SET status = ?, evidence = ?, updated_at = ?
                WHERE attempt_id = ? AND status = 'unknown'
            """, (status, json.dumps(evidence, ensure_ascii=False), _utc_now_iso(), attempt_id))
            if cursor.rowcount != 1:
                raise ValueError("reply_attempt_not_pending")
            if status == 'verified':
                original_json, reply = conn.execute(
                    "SELECT original_context, reply_text FROM reply_attempts WHERE attempt_id = ?", (attempt_id,)).fetchone()
                original = json.loads(original_json)
                handle = original.get('author_handle') or original['author_name']
                channel = original.get('channel_id')
                conn.execute("""
                    INSERT INTO commenter_interactions
                    (commenter_key, commenter_handle, commenter_channel_id, comment_text, reply_text,
                     liked, hearted, replied, commenter_type, created_at)
                    VALUES (?, ?, ?, ?, ?, 0, 0, 1, 'unknown', ?)
                """, (make_commenter_key(channel_id=channel, handle=handle), _normalize_handle(handle),
                      channel, original['text'], reply, _utc_now_iso()))
            conn.commit()

    def get_reply_attempts(self, original_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT attempt_id, status, original_context, reply_text, evidence, created_at, updated_at
                FROM reply_attempts WHERE target_key = ? ORDER BY created_at
            """, (self.reply_target_key(original_context),)).fetchall()
        return [dict(attempt_id=row[0], status=row[1], original_context=json.loads(row[2]),
                     reply_text=row[3], evidence=json.loads(row[4]), created_at=row[5], updated_at=row[6])
                for row in rows]

    def append_reply_evidence(self, attempt_id: str, inspection: Dict[str, Any]) -> None:
        """Attach bounded private post inspection without changing reservation status."""
        if not isinstance(inspection, dict):
            raise ValueError("inspection_must_be_an_object")
        encoded = json.dumps(inspection, ensure_ascii=False, allow_nan=False)
        if len(encoded.encode('utf-8')) > 16384:
            raise ValueError("inspection_evidence_too_large")
        with self._get_connection() as conn:
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT evidence FROM reply_attempts WHERE attempt_id = ?", (attempt_id,)).fetchone()
            if row is None:
                raise ValueError("reply_attempt_not_found")
            evidence = json.loads(row[0])
            evidence['post_inspection'] = json.loads(encoded)
            conn.execute("UPDATE reply_attempts SET evidence = ?, updated_at = ? WHERE attempt_id = ?",
                         (json.dumps(evidence, ensure_ascii=False), _utc_now_iso(), attempt_id))
            conn.commit()

    def record_interaction(
        self,
        *,
        commenter_handle: Optional[str],
        commenter_channel_id: Optional[str],
        comment_text: str,
        reply_text: Optional[str],
        liked: bool,
        hearted: bool,
        replied: bool,
        commenter_type: Optional[str],
        created_at: Optional[str] = None,
    ) -> None:
        commenter_key = make_commenter_key(channel_id=commenter_channel_id, handle=commenter_handle)
        created_at = created_at or _utc_now_iso()
        handle_normalized = _normalize_handle(commenter_handle)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO commenter_interactions (
                    commenter_key,
                    commenter_handle,
                    commenter_channel_id,
                    comment_text,
                    reply_text,
                    liked,
                    hearted,
                    replied,
                    commenter_type,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    commenter_key,
                    handle_normalized,
                    commenter_channel_id,
                    (comment_text or "")[:1000],
                    (reply_text or "")[:1000] if reply_text else None,
                    1 if liked else 0,
                    1 if hearted else 0,
                    1 if replied else 0,
                    commenter_type or "unknown",
                    created_at,
                ),
            )

    def get_recent_interactions(self, *, commenter_key: str, limit: int = 5) -> List[CommenterInteraction]:
        if not commenter_key:
            return []

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    commenter_key,
                    commenter_handle,
                    commenter_channel_id,
                    comment_text,
                    reply_text,
                    liked,
                    hearted,
                    replied,
                    commenter_type,
                    created_at
                FROM commenter_interactions
                WHERE commenter_key = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (commenter_key, limit),
            )
            rows = cursor.fetchall()

        # Oldest-to-newest for prompt readability
        rows.reverse()
        return [
            CommenterInteraction(
                commenter_key=row[0],
                commenter_handle=row[1] or "",
                commenter_channel_id=row[2],
                comment_text=row[3] or "",
                reply_text=row[4],
                liked=bool(row[5]),
                hearted=bool(row[6]),
                replied=bool(row[7]),
                commenter_type=row[8] or "unknown",
                created_at=row[9],
            )
            for row in rows
        ]

    def get_profile_summary(self, *, commenter_key: str) -> Dict[str, Any]:
        if not commenter_key:
            return {"commenter_key": commenter_key, "total": 0}

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(replied) AS replies,
                    SUM(liked) AS likes,
                    SUM(hearted) AS hearts,
                    MAX(created_at) AS last_seen
                FROM commenter_interactions
                WHERE commenter_key = ?
                """,
                (commenter_key,),
            )
            row = cursor.fetchone()

        return {
            "commenter_key": commenter_key,
            "total": int(row[0] or 0),
            "replies": int(row[1] or 0),
            "likes": int(row[2] or 0),
            "hearts": int(row[3] or 0),
            "last_seen": row[4],
        }


_store: Optional[CommenterHistoryStore] = None


def get_commenter_history_store() -> CommenterHistoryStore:
    global _store
    if _store is None:
        _store = CommenterHistoryStore()
    return _store

