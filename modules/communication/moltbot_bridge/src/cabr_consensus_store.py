#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CABR Consensus Store Phase 2 -- SQLite Audit Trail for CABRConsensusRecord

Provides local SQLite persistence for CABRConsensusRecord audit trails.
This is EVIDENCE STORAGE ONLY -- persistence does NOT mean:
  - verification_complete=True
  - cabr_ready=True
  - payout_ready=True
  - Payout approval
  - DAO activation
  - Token issuance
  - External settlement

WSP 97 TRUTH BOUNDARIES:
  * DOES:
    - Store CABRConsensusRecord as immutable append-only rows
    - Key records by deterministic record_id/record_hash
    - Reject duplicate record_id (idempotent insert)
    - Preserve truth fields exactly as input (all False in Phase 1)
    - Store decision, reason codes, score/quorum summaries, timestamps
    - Support query by record_id, decision filter, time range
    - Fail closed on schema/write errors
    - Use caller-provided DB path (tests use tmp_path)

  X DOES NOT:
    - Issue tokens or UPS
    - Allocate rewards
    - Write to wallet
    - Trigger payouts
    - Activate DAO transitions
    - Make network calls
    - Claim consensus is final
    - Cause automatic state progression
    - Store secrets or credentials

Architecture:
  Phase 1 -> CABRConsensusRecord (in-memory decision)
  Phase 2 -> CABRConsensusStore (this) -> SQLite persistence

WSP Compliance:
  WSP 11  : Interface contract (explicit, typed)
  WSP 91  : Observability (timestamps, audit fields)
  WSP 97  : System Execution Prompting (truth boundaries)

Slice: CABR_CONSENSUS_FINALIZATION_PHASE2_SQLITE_AUDIT_TRAIL
Worker: W1
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("cabr_consensus_store")


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string or None."""
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Store Result Enum
# ---------------------------------------------------------------------------


class CABRConsensusStoreResultStatus(str, Enum):
    """Status of store operations."""

    SUCCESS = "success"
    """Operation completed successfully."""

    ALREADY_EXISTS = "already_exists"
    """Record with this record_id already exists (idempotent)."""

    NOT_FOUND = "not_found"
    """Record not found."""

    SCHEMA_ERROR = "schema_error"
    """Database schema initialization failed."""

    WRITE_ERROR = "write_error"
    """Write operation failed."""

    READ_ERROR = "read_error"
    """Read operation failed."""

    VALIDATION_ERROR = "validation_error"
    """Input validation failed."""


# ---------------------------------------------------------------------------
# Store Exceptions
# ---------------------------------------------------------------------------


class CABRConsensusStoreError(Exception):
    """Base exception for CABRConsensusStore errors."""

    def __init__(
        self,
        message: str,
        status: CABRConsensusStoreResultStatus,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.status = status
        self.details = details or {}


# ---------------------------------------------------------------------------
# Store Result Dataclass
# ---------------------------------------------------------------------------


@dataclass
class CABRConsensusStoreResult:
    """Result from CABRConsensusStore operations."""

    status: CABRConsensusStoreResultStatus
    """Operation status."""

    message: str
    """Human-readable message."""

    record_id: Optional[str] = None
    """Record ID if applicable."""

    record_count: int = 0
    """Number of records affected/returned."""

    records: Optional[List[Dict[str, Any]]] = None
    """Retrieved records if applicable."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "status": self.status.value,
            "message": self.message,
            "record_id": self.record_id,
            "record_count": self.record_count,
            "records": self.records,
        }


# ---------------------------------------------------------------------------
# SQLite Schema
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 1

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cabr_consensus_records (
    -- Primary Key
    record_id TEXT PRIMARY KEY NOT NULL,

    -- Deterministic Hash (for integrity verification)
    record_hash TEXT NOT NULL,

    -- Source Identity
    receipt_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,

    -- Score Reference
    score_id TEXT,
    score_decision TEXT,
    score_reason_code TEXT,

    -- Quorum Reference
    quorum_id TEXT,
    quorum_decision TEXT,
    quorum_reason_code TEXT,

    -- Consensus Decision
    decision TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    reason_human TEXT NOT NULL,

    -- Quorum Metrics
    quorum_met INTEGER NOT NULL DEFAULT 0,
    threshold_met INTEGER NOT NULL DEFAULT 0,
    unique_verifiers INTEGER NOT NULL DEFAULT 0,
    consensus_score REAL NOT NULL DEFAULT 0.0,

    -- Evidence Metrics
    evidence_present INTEGER NOT NULL DEFAULT 0,
    evidence_count INTEGER NOT NULL DEFAULT 0,

    -- Execution Mode
    is_dry_run INTEGER NOT NULL DEFAULT 0,
    is_simulated INTEGER NOT NULL DEFAULT 0,

    -- WSP 97 Truth Fields (ALWAYS FALSE -- stored as evidence only)
    verification_complete INTEGER NOT NULL DEFAULT 0,
    cabr_ready INTEGER NOT NULL DEFAULT 0,
    payout_ready INTEGER NOT NULL DEFAULT 0,

    -- Timestamps
    finalized_at TEXT NOT NULL,
    stored_at TEXT NOT NULL,

    -- Audit Fields
    finalizer_version TEXT NOT NULL,
    store_version INTEGER NOT NULL DEFAULT 1
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_consensus_decision ON cabr_consensus_records(decision);
CREATE INDEX IF NOT EXISTS idx_consensus_receipt_id ON cabr_consensus_records(receipt_id);
CREATE INDEX IF NOT EXISTS idx_consensus_finalized_at ON cabr_consensus_records(finalized_at);
CREATE INDEX IF NOT EXISTS idx_consensus_record_hash ON cabr_consensus_records(record_hash);
"""

SCHEMA_VERSION_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
"""


# ---------------------------------------------------------------------------
# CABRConsensusStore Class
# ---------------------------------------------------------------------------


class CABRConsensusStore:
    """
    SQLite persistence store for CABRConsensusRecord audit trails.

    This is evidence storage only. Persistence does NOT mean:
    - verification_complete=True
    - cabr_ready=True
    - payout_ready=True
    - Payout approval
    - DAO activation
    - Token issuance
    - External settlement

    Records are stored as immutable append-only rows keyed by deterministic
    record_id. Duplicate record_id insertions are rejected (idempotent).

    Usage:
        store = CABRConsensusStore(db_path=Path("/tmp/consensus_audit.db"))
        store.initialize_schema()
        result = store.save_record(consensus_record.to_dict())
        record = store.get_record("ccr_test_18a3b2c1_abc123")

    WSP 97 Truth Fields:
        All truth fields (verification_complete, cabr_ready, payout_ready)
        are stored exactly as provided in the input record. Phase 1 consensus
        records always have these fields set to False.
    """

    def __init__(self, db_path: Union[str, Path]):
        """
        Initialize CABRConsensusStore with database path.

        Args:
            db_path: Path to SQLite database file. Parent directory must exist.
                     Use tmp_path for tests.

        Raises:
            CABRConsensusStoreError: If db_path parent directory does not exist.
        """
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None
        self._schema_initialized = False

        # Validate parent directory exists
        if not self.db_path.parent.exists():
            raise CABRConsensusStoreError(
                f"Parent directory does not exist: {self.db_path.parent}",
                CABRConsensusStoreResultStatus.VALIDATION_ERROR,
                {"db_path": str(self.db_path)},
            )

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create SQLite connection."""
        if self._conn is None:
            try:
                self._conn = sqlite3.connect(
                    str(self.db_path),
                    timeout=10.0,
                    isolation_level="DEFERRED",
                )
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA busy_timeout=10000")
                self._conn.execute("PRAGMA journal_mode=WAL")
                self._conn.execute("PRAGMA foreign_keys=ON")
            except sqlite3.Error as e:
                raise CABRConsensusStoreError(
                    f"Failed to connect to database: {e}",
                    CABRConsensusStoreResultStatus.SCHEMA_ERROR,
                    {"db_path": str(self.db_path), "error": str(e)},
                )
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass
            finally:
                self._conn = None
                self._schema_initialized = False

    def __enter__(self) -> "CABRConsensusStore":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    # ---------------------------------------------------------------------------
    # Schema Management
    # ---------------------------------------------------------------------------

    def initialize_schema(self) -> CABRConsensusStoreResult:
        """
        Initialize database schema if not already present.

        Creates the cabr_consensus_records table and required indexes.
        Safe to call multiple times (idempotent).

        Returns:
            CABRConsensusStoreResult with SUCCESS or SCHEMA_ERROR status.

        Raises:
            CABRConsensusStoreError: If schema initialization fails.
        """
        try:
            conn = self._get_connection()

            # Create schema version table
            conn.executescript(SCHEMA_VERSION_SQL)

            # Check if already initialized
            cursor = conn.execute(
                "SELECT version FROM schema_version WHERE version = ?",
                (SCHEMA_VERSION,),
            )
            if cursor.fetchone() is not None:
                self._schema_initialized = True
                return CABRConsensusStoreResult(
                    status=CABRConsensusStoreResultStatus.SUCCESS,
                    message="Schema already initialized",
                )

            # Create main table and indexes
            conn.executescript(CREATE_TABLE_SQL)

            # Record schema version
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, _utc_iso(_utc_now())),
            )
            conn.commit()

            self._schema_initialized = True
            logger.info("[CABR-STORE] Schema initialized (version=%d)", SCHEMA_VERSION)

            return CABRConsensusStoreResult(
                status=CABRConsensusStoreResultStatus.SUCCESS,
                message=f"Schema initialized (version={SCHEMA_VERSION})",
            )

        except sqlite3.Error as e:
            logger.error("[CABR-STORE] Schema initialization failed: %s", e)
            raise CABRConsensusStoreError(
                f"Schema initialization failed: {e}",
                CABRConsensusStoreResultStatus.SCHEMA_ERROR,
                {"error": str(e)},
            )

    def _ensure_schema(self) -> None:
        """Ensure schema is initialized before operations."""
        if not self._schema_initialized:
            # Check if table exists
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='cabr_consensus_records'"
            )
            if cursor.fetchone() is None:
                raise CABRConsensusStoreError(
                    "Schema not initialized. Call initialize_schema() first.",
                    CABRConsensusStoreResultStatus.SCHEMA_ERROR,
                )
            self._schema_initialized = True

    # ---------------------------------------------------------------------------
    # Record Operations
    # ---------------------------------------------------------------------------

    def save_record(self, record: Dict[str, Any]) -> CABRConsensusStoreResult:
        """
        Save CABRConsensusRecord to database.

        Records are stored as immutable append-only rows. Duplicate record_id
        insertions are rejected (returns ALREADY_EXISTS, not error).

        WSP 97: Truth fields are stored exactly as provided. Phase 1 records
        always have verification_complete=False, cabr_ready=False, payout_ready=False.

        Args:
            record: CABRConsensusRecord.to_dict() output.

        Returns:
            CABRConsensusStoreResult with:
            - SUCCESS: Record saved successfully
            - ALREADY_EXISTS: Record with this record_id already exists
            - VALIDATION_ERROR: Invalid record structure
            - WRITE_ERROR: Database write failed

        Raises:
            CABRConsensusStoreError: If schema not initialized or critical error.
        """
        self._ensure_schema()

        # Validate required fields
        required_fields = ["record_id", "record_hash", "receipt_id", "job_id", "tenant_id", "decision", "reason_code"]
        for field in required_fields:
            if field not in record or record[field] is None:
                return CABRConsensusStoreResult(
                    status=CABRConsensusStoreResultStatus.VALIDATION_ERROR,
                    message=f"Missing required field: {field}",
                    record_id=record.get("record_id"),
                )

        record_id = record["record_id"]

        try:
            conn = self._get_connection()

            # Check for existing record
            cursor = conn.execute(
                "SELECT record_id FROM cabr_consensus_records WHERE record_id = ?",
                (record_id,),
            )
            if cursor.fetchone() is not None:
                logger.debug("[CABR-STORE] Record already exists: %s", record_id)
                return CABRConsensusStoreResult(
                    status=CABRConsensusStoreResultStatus.ALREADY_EXISTS,
                    message=f"Record already exists: {record_id}",
                    record_id=record_id,
                )

            # Insert new record
            stored_at = _utc_iso(_utc_now())
            conn.execute(
                """
                INSERT INTO cabr_consensus_records (
                    record_id, record_hash, receipt_id, job_id, tenant_id,
                    score_id, score_decision, score_reason_code,
                    quorum_id, quorum_decision, quorum_reason_code,
                    decision, reason_code, reason_human,
                    quorum_met, threshold_met, unique_verifiers, consensus_score,
                    evidence_present, evidence_count,
                    is_dry_run, is_simulated,
                    verification_complete, cabr_ready, payout_ready,
                    finalized_at, stored_at, finalizer_version, store_version
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?
                )
                """,
                (
                    record_id,
                    record["record_hash"],
                    record["receipt_id"],
                    record["job_id"],
                    record["tenant_id"],
                    record.get("score_id"),
                    record.get("score_decision"),
                    record.get("score_reason_code"),
                    record.get("quorum_id"),
                    record.get("quorum_decision"),
                    record.get("quorum_reason_code"),
                    record["decision"],
                    record["reason_code"],
                    record.get("reason_human", ""),
                    1 if record.get("quorum_met", False) else 0,
                    1 if record.get("threshold_met", False) else 0,
                    record.get("unique_verifiers", 0),
                    record.get("consensus_score", 0.0),
                    1 if record.get("evidence_present", False) else 0,
                    record.get("evidence_count", 0),
                    1 if record.get("is_dry_run", False) else 0,
                    1 if record.get("is_simulated", False) else 0,
                    1 if record.get("verification_complete", False) else 0,
                    1 if record.get("cabr_ready", False) else 0,
                    1 if record.get("payout_ready", False) else 0,
                    record.get("finalized_at", stored_at),
                    stored_at,
                    record.get("finalizer_version", "0.1.0"),
                    SCHEMA_VERSION,
                ),
            )
            conn.commit()

            logger.info("[CABR-STORE] Saved record: %s", record_id)
            return CABRConsensusStoreResult(
                status=CABRConsensusStoreResultStatus.SUCCESS,
                message=f"Record saved: {record_id}",
                record_id=record_id,
                record_count=1,
            )

        except sqlite3.Error as e:
            logger.error("[CABR-STORE] Write error for %s: %s", record_id, e)
            return CABRConsensusStoreResult(
                status=CABRConsensusStoreResultStatus.WRITE_ERROR,
                message=f"Write error: {e}",
                record_id=record_id,
            )

    def get_record(self, record_id: str) -> CABRConsensusStoreResult:
        """
        Retrieve CABRConsensusRecord by record_id.

        Args:
            record_id: The record identifier to retrieve.

        Returns:
            CABRConsensusStoreResult with:
            - SUCCESS: Record found (records contains single dict)
            - NOT_FOUND: No record with this ID
            - READ_ERROR: Database read failed

        Raises:
            CABRConsensusStoreError: If schema not initialized.
        """
        self._ensure_schema()

        try:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT * FROM cabr_consensus_records WHERE record_id = ?",
                (record_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return CABRConsensusStoreResult(
                    status=CABRConsensusStoreResultStatus.NOT_FOUND,
                    message=f"Record not found: {record_id}",
                    record_id=record_id,
                )

            record = self._row_to_dict(row)
            return CABRConsensusStoreResult(
                status=CABRConsensusStoreResultStatus.SUCCESS,
                message=f"Record found: {record_id}",
                record_id=record_id,
                record_count=1,
                records=[record],
            )

        except sqlite3.Error as e:
            logger.error("[CABR-STORE] Read error for %s: %s", record_id, e)
            return CABRConsensusStoreResult(
                status=CABRConsensusStoreResultStatus.READ_ERROR,
                message=f"Read error: {e}",
                record_id=record_id,
            )

    def record_exists(self, record_id: str) -> bool:
        """
        Check if record exists without retrieving full data.

        Args:
            record_id: The record identifier to check.

        Returns:
            True if record exists, False otherwise.

        Raises:
            CABRConsensusStoreError: If schema not initialized or read fails.
        """
        self._ensure_schema()

        try:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT 1 FROM cabr_consensus_records WHERE record_id = ?",
                (record_id,),
            )
            return cursor.fetchone() is not None

        except sqlite3.Error as e:
            raise CABRConsensusStoreError(
                f"Existence check failed: {e}",
                CABRConsensusStoreResultStatus.READ_ERROR,
                {"record_id": record_id, "error": str(e)},
            )

    def list_records(
        self,
        limit: int = 100,
        decision_filter: Optional[str] = None,
        offset: int = 0,
    ) -> CABRConsensusStoreResult:
        """
        List CABRConsensusRecords with optional filtering.

        Args:
            limit: Maximum number of records to return (default: 100).
            decision_filter: Optional decision value to filter by.
            offset: Number of records to skip (for pagination).

        Returns:
            CABRConsensusStoreResult with:
            - SUCCESS: Records retrieved (may be empty)
            - READ_ERROR: Database read failed

        Raises:
            CABRConsensusStoreError: If schema not initialized.
        """
        self._ensure_schema()

        try:
            conn = self._get_connection()

            if decision_filter:
                cursor = conn.execute(
                    """
                    SELECT * FROM cabr_consensus_records
                    WHERE decision = ?
                    ORDER BY finalized_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (decision_filter, limit, offset),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM cabr_consensus_records
                    ORDER BY finalized_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )

            rows = cursor.fetchall()
            records = [self._row_to_dict(row) for row in rows]

            return CABRConsensusStoreResult(
                status=CABRConsensusStoreResultStatus.SUCCESS,
                message=f"Retrieved {len(records)} record(s)",
                record_count=len(records),
                records=records,
            )

        except sqlite3.Error as e:
            logger.error("[CABR-STORE] List error: %s", e)
            return CABRConsensusStoreResult(
                status=CABRConsensusStoreResultStatus.READ_ERROR,
                message=f"Read error: {e}",
            )

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to dict matching CABRConsensusRecord.to_dict() format."""
        return {
            "record_id": row["record_id"],
            "record_hash": row["record_hash"],
            "receipt_id": row["receipt_id"],
            "job_id": row["job_id"],
            "tenant_id": row["tenant_id"],
            "score_id": row["score_id"],
            "score_decision": row["score_decision"],
            "score_reason_code": row["score_reason_code"],
            "quorum_id": row["quorum_id"],
            "quorum_decision": row["quorum_decision"],
            "quorum_reason_code": row["quorum_reason_code"],
            "decision": row["decision"],
            "reason_code": row["reason_code"],
            "reason_human": row["reason_human"],
            "quorum_met": bool(row["quorum_met"]),
            "threshold_met": bool(row["threshold_met"]),
            "unique_verifiers": row["unique_verifiers"],
            "consensus_score": row["consensus_score"],
            "evidence_present": bool(row["evidence_present"]),
            "evidence_count": row["evidence_count"],
            "is_dry_run": bool(row["is_dry_run"]),
            "is_simulated": bool(row["is_simulated"]),
            "verification_complete": bool(row["verification_complete"]),
            "cabr_ready": bool(row["cabr_ready"]),
            "payout_ready": bool(row["payout_ready"]),
            "finalized_at": row["finalized_at"],
            "stored_at": row["stored_at"],
            "finalizer_version": row["finalizer_version"],
        }
