"""Storage helpers for durable RedDog FIX promotion claims."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping


def ensure_claim_table(db: Any) -> None:
    with db.db.get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reddog_fix_promotion_claims (
                claim_id TEXT PRIMARY KEY, intent_id TEXT NOT NULL UNIQUE,
                cycle_id TEXT NOT NULL UNIQUE, determination_id TEXT NOT NULL UNIQUE,
                queue_candidate_id TEXT NOT NULL, wsp15_receipt_id TEXT NOT NULL,
                status TEXT NOT NULL, lease_id TEXT, lease_owner TEXT,
                lease_expires_at TEXT, revision INTEGER NOT NULL,
                promotion_receipt_id TEXT, committed_revision TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        _ensure_claim_columns(conn)


def _ensure_claim_columns(conn: Any) -> None:
    columns = {
        str(row["name"])
        for row in conn.execute(
            "PRAGMA table_info(reddog_fix_promotion_claims)"
        ).fetchall()
    }
    for name in ("promotion_receipt_id", "committed_revision"):
        if name not in columns:
            conn.execute(
                f"ALTER TABLE reddog_fix_promotion_claims ADD COLUMN {name} TEXT"
            )


def insert_pending_claim(
    conn: Any,
    claim_id: str,
    binding: Mapping[str, str],
    now: datetime,
) -> None:
    conn.execute(
        """
        INSERT INTO reddog_fix_promotion_claims
        (claim_id, intent_id, cycle_id, determination_id, queue_candidate_id,
         wsp15_receipt_id, status, revision, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'PENDING', 0, ?)
        ON CONFLICT(determination_id) DO NOTHING
        """,
        (
            claim_id,
            binding["intent_id"],
            binding["cycle_id"],
            binding["determination_id"],
            binding["queue_candidate_id"],
            binding["wsp15_allocation_receipt_id"],
            iso_utc(now),
        ),
    )


def lease_claim_row(
    conn: Any,
    claim_id: str,
    binding: Mapping[str, str],
    *,
    lease_id: str,
    worker_id: str,
    expires: str,
    now: datetime,
) -> int | None:
    cursor = conn.execute(
        """
        UPDATE reddog_fix_promotion_claims
        SET status = 'CLAIMED', lease_id = ?, lease_owner = ?,
            lease_expires_at = ?, revision = revision + 1, updated_at = ?
        WHERE claim_id = ? AND intent_id = ? AND cycle_id = ?
          AND determination_id = ? AND queue_candidate_id = ?
          AND wsp15_receipt_id = ? AND (
            status = 'PENDING' OR
            (status = 'CLAIMED' AND lease_expires_at <= ?)
        )
        """,
        (
            lease_id, worker_id, expires, iso_utc(now), claim_id,
            binding["intent_id"], binding["cycle_id"], binding["determination_id"],
            binding["queue_candidate_id"], binding["wsp15_allocation_receipt_id"],
            iso_utc(now),
        ),
    )
    if cursor.rowcount != 1:
        return None
    row = conn.execute(
        "SELECT revision FROM reddog_fix_promotion_claims WHERE claim_id = ?",
        (claim_id,),
    ).fetchone()
    return int(row["revision"])


def claim_id_for_binding(binding: Mapping[str, str]) -> str:
    value = json.dumps(
        {"binding": dict(binding), "schema": "reddog_fix_promotion_claim.v1"},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return "sha256:" + hashlib.sha256(value.encode("ascii")).hexdigest()


def utc(value: datetime | None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("now_must_be_timezone_aware")
    return result.astimezone(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


__all__ = [
    "claim_id_for_binding",
    "ensure_claim_table",
    "insert_pending_claim",
    "lease_claim_row",
    "iso_utc",
    "utc",
]
