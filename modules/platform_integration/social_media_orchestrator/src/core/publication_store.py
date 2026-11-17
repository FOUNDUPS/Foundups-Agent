"""Durable claims and provider receipts owned by the social orchestrator.

This table shares the stream registry's database, without changing stream rows.
A claimed write never expires into permission to send again. An unresolved write
must be reconciled; a known provider ID permits readback only.
"""

from contextlib import closing, contextmanager
from pathlib import Path
import sqlite3
import time
import uuid


DEFAULT_DB_PATH = (
    Path(__file__).resolve().parents[2] / "memory" / "orchestrator_posted_streams.db"
)
_DAY_SECONDS = 24 * 60 * 60
_KEY = "account = ? AND campaign_id = ? AND job_id = ?"


class PublicationStore:
    """A strict SQLite receipt owner; errors propagate to the publishing gate."""

    def __init__(self, db_path=None):
        self.path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        if str(self.path) == ":memory:" or str(self.path).startswith("file:"):
            raise ValueError("A durable publication database is required")

    @contextmanager
    def _transaction(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=5, isolation_level=None)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA synchronous = FULL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS x_publications (
                    account TEXT NOT NULL, provider_user_id TEXT NOT NULL,
                    campaign_id TEXT NOT NULL, job_id TEXT NOT NULL,
                    content_hash TEXT NOT NULL, claim_token TEXT NOT NULL,
                    status TEXT NOT NULL, created_at REAL NOT NULL,
                    updated_at REAL NOT NULL, post_id TEXT,
                    verified_at REAL, error TEXT,
                    PRIMARY KEY (account, campaign_id, job_id)
                )
            """)
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.commit()
            except BaseException:
                conn.rollback()
                raise

    def claim(self, account, provider_user_id, campaign_id, job_id, content_hash):
        """Reserve one write atomically, or return the existing immutable binding."""
        key = (account, campaign_id, job_id)
        with self._transaction() as conn:
            row = conn.execute(
                f"SELECT * FROM x_publications WHERE {_KEY}", key
            ).fetchone()
            if row is not None:
                return self._existing(dict(row), provider_user_id, content_hash)
            now = time.time()
            blocked = conn.execute("""
                SELECT 1 FROM x_publications
                WHERE provider_user_id = ? AND campaign_id = ?
                  AND (created_at > ? OR status != 'verified') LIMIT 1
            """, (provider_user_id, campaign_id, now - _DAY_SECONDS)).fetchone()
            if blocked:
                return {"decision": "rate_limited"}
            row = dict(account=account, provider_user_id=provider_user_id,
                       campaign_id=campaign_id, job_id=job_id,
                       content_hash=content_hash, claim_token=uuid.uuid4().hex,
                       status="publishing", created_at=now, updated_at=now,
                       post_id=None, verified_at=None, error=None)
            conn.execute("""
                INSERT INTO x_publications
                (account, provider_user_id, campaign_id, job_id, content_hash,
                 claim_token, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tuple(row[k] for k in (
                "account", "provider_user_id", "campaign_id", "job_id",
                "content_hash", "claim_token", "status", "created_at", "updated_at"
            )))
            return {**row, "decision": "claimed"}

    @staticmethod
    def _existing(row, provider_user_id, content_hash):
        if row["provider_user_id"] != provider_user_id:
            decision = "account_conflict"
        elif row["content_hash"] != content_hash:
            decision = "content_conflict"
        elif row["status"] == "verified" and row["post_id"]:
            decision = "already_verified"
        elif row["post_id"]:
            decision = "readback"
        else:
            decision = "outcome_unknown"
        return {**row, "decision": decision}

    @staticmethod
    def _binding(claim):
        return tuple(claim[k] for k in (
            "account", "campaign_id", "job_id", "provider_user_id",
            "content_hash", "claim_token"
        ))

    def record_post_id(self, claim, post_id):
        """Persist the returned ID before any readback or success report."""
        with self._transaction() as conn:
            cursor = conn.execute(f"""
                UPDATE x_publications
                SET post_id = ?, status = 'readback_pending', updated_at = ?
                WHERE {_KEY} AND provider_user_id = ? AND content_hash = ?
                  AND claim_token = ? AND status = 'publishing' AND post_id IS NULL
            """, (post_id, time.time(), *self._binding(claim)))
            if cursor.rowcount != 1:
                raise RuntimeError("Publication claim no longer matches")

    def record_unknown(self, claim):
        """Block retries when create may have reached the provider."""
        with self._transaction() as conn:
            cursor = conn.execute(f"""
                UPDATE x_publications
                SET status = 'outcome_unknown', error = 'create_outcome_unknown',
                    updated_at = ?
                WHERE {_KEY} AND provider_user_id = ? AND content_hash = ?
                  AND claim_token = ? AND post_id IS NULL
            """, (time.time(), *self._binding(claim)))
            if cursor.rowcount != 1:
                raise RuntimeError("Publication claim no longer matches")

    def record_readback(self, claim, post_id, *, verified, error=None):
        """Retain evidence without downgrading a concurrently verified receipt."""
        now = time.time()
        with self._transaction() as conn:
            cursor = conn.execute(f"""
                UPDATE x_publications SET
                    status = CASE WHEN status = 'verified' THEN status ELSE ? END,
                    verified_at = CASE WHEN ? THEN ? ELSE verified_at END,
                    error = CASE WHEN status = 'verified' THEN NULL ELSE ? END,
                    updated_at = ?
                WHERE {_KEY} AND provider_user_id = ? AND content_hash = ?
                  AND claim_token = ? AND post_id = ?
            """, ("verified" if verified else "readback_pending", verified, now,
                  error, now, *self._binding(claim), post_id))
            if cursor.rowcount != 1:
                raise RuntimeError("Publication receipt no longer matches")
