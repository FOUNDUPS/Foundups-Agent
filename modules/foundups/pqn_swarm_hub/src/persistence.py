"""
PQN Swarm Hub - SQLite Persistence Layer

Phase 1: SQLite store for all contracts.
Pattern: FAMEventStore (dual-write optional, SQLite primary)

WSP 72: Module independence
WSP 91: Observability (persistence audit-safe)

Tables:
- work_units (PQNWorkUnit)
- submissions (rESPSubmission)
- verification_decisions (VerificationDecision)
- contributions (ContributionRecord)
- participants (ParticipantIdentity)
- gate_decisions (GateDecision)
"""

import json
import logging
import sqlite3
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar

from .contracts import (
    ContributionRecord,
    PQNWorkUnit,
    SubmissionStatus,
    VerificationDecision,
    WorkUnitStatus,
    rESPSubmission,
    utc_now,
)
from .gate import GateDecision, ParticipantIdentity, ParticipantStatus, ParticipantTier

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_DB_DIR = Path("data/pqn_swarm_hub")
DEFAULT_DB_FILENAME = "swarm.db"


class SQLiteStore:
    """
    SQLite persistence for PQN Swarm Hub contracts.

    Thread-safe with connection-per-operation pattern.
    Phase 1: No migrations, schema created on init.
    """

    SCHEMA = """
    -- Work Units
    CREATE TABLE IF NOT EXISTS work_units (
        work_unit_id TEXT PRIMARY KEY,
        description TEXT NOT NULL,
        config_json TEXT NOT NULL,
        creator_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        source TEXT NOT NULL DEFAULT 'internal',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_work_units_status ON work_units(status);
    CREATE INDEX IF NOT EXISTS idx_work_units_creator ON work_units(creator_id);
    CREATE INDEX IF NOT EXISTS idx_work_units_source ON work_units(source);

    -- Submissions
    CREATE TABLE IF NOT EXISTS submissions (
        submission_id TEXT PRIMARY KEY,
        work_unit_id TEXT NOT NULL,
        submitter_id TEXT NOT NULL,
        metrics_json TEXT NOT NULL,
        artifacts_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending_verification',
        source TEXT NOT NULL DEFAULT 'internal',
        submitted_at TEXT NOT NULL,
        FOREIGN KEY (work_unit_id) REFERENCES work_units(work_unit_id)
    );
    CREATE INDEX IF NOT EXISTS idx_submissions_work_unit ON submissions(work_unit_id);
    CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
    CREATE INDEX IF NOT EXISTS idx_submissions_source ON submissions(source);

    -- Verification Decisions
    CREATE TABLE IF NOT EXISTS verification_decisions (
        decision_id TEXT PRIMARY KEY,
        submission_id TEXT NOT NULL,
        decision TEXT NOT NULL,
        verifier_id TEXT NOT NULL,
        rationale TEXT,
        confidence REAL,
        decided_at TEXT NOT NULL,
        FOREIGN KEY (submission_id) REFERENCES submissions(submission_id)
    );
    CREATE INDEX IF NOT EXISTS idx_decisions_submission ON verification_decisions(submission_id);

    -- Contributions
    CREATE TABLE IF NOT EXISTS contributions (
        contribution_id TEXT PRIMARY KEY,
        work_unit_id TEXT NOT NULL,
        submission_id TEXT NOT NULL,
        decision_id TEXT NOT NULL,
        contributor_id TEXT NOT NULL,
        score REAL NOT NULL,
        recorded_at TEXT NOT NULL,
        FOREIGN KEY (work_unit_id) REFERENCES work_units(work_unit_id),
        FOREIGN KEY (submission_id) REFERENCES submissions(submission_id),
        FOREIGN KEY (decision_id) REFERENCES verification_decisions(decision_id)
    );
    CREATE INDEX IF NOT EXISTS idx_contributions_contributor ON contributions(contributor_id);

    -- Participants
    CREATE TABLE IF NOT EXISTS participants (
        participant_id TEXT PRIMARY KEY,
        display_name TEXT,
        model_type TEXT,
        compute_capacity TEXT,
        capability_tags_json TEXT,
        metadata_json TEXT,
        registered_at TEXT NOT NULL
    );

    -- Gate Decisions
    CREATE TABLE IF NOT EXISTS gate_decisions (
        decision_id TEXT PRIMARY KEY,
        participant_id TEXT NOT NULL,
        decision TEXT NOT NULL,
        tier TEXT NOT NULL,
        reason TEXT,
        decider_id TEXT NOT NULL,
        decided_at TEXT NOT NULL,
        FOREIGN KEY (participant_id) REFERENCES participants(participant_id)
    );
    CREATE INDEX IF NOT EXISTS idx_gate_decisions_participant ON gate_decisions(participant_id);
    """

    def __init__(
        self,
        db_dir: Optional[Path] = None,
        db_filename: str = DEFAULT_DB_FILENAME,
    ) -> None:
        """
        Initialize SQLite store.

        Args:
            db_dir: Directory for database file (default: data/pqn_swarm_hub/)
            db_filename: Database filename (default: swarm.db)
        """
        self._db_dir = Path(db_dir) if db_dir else DEFAULT_DB_DIR
        self._db_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._db_dir / db_filename
        self._lock = threading.Lock()

        self._init_schema()
        logger.info("[SWARM-STORE] Initialized | path=%s", self._db_path)

    def _init_schema(self) -> None:
        """Create schema if not exists."""
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.executescript(self.SCHEMA)
            # Migration: Add source columns for existing databases (Phase 2)
            self._migrate_source_columns(conn)
            conn.commit()

    def _migrate_source_columns(self, conn: sqlite3.Connection) -> None:
        """Add source columns to existing tables if missing."""
        # Check work_units table
        cursor = conn.execute("PRAGMA table_info(work_units)")
        columns = {row[1] for row in cursor.fetchall()}
        if "source" not in columns:
            conn.execute("ALTER TABLE work_units ADD COLUMN source TEXT NOT NULL DEFAULT 'internal'")
            logger.info("[SWARM-STORE] Migrated work_units: added source column")

        # Check submissions table
        cursor = conn.execute("PRAGMA table_info(submissions)")
        columns = {row[1] for row in cursor.fetchall()}
        if "source" not in columns:
            conn.execute("ALTER TABLE submissions ADD COLUMN source TEXT NOT NULL DEFAULT 'internal'")
            logger.info("[SWARM-STORE] Migrated submissions: added source column")

    def _connect(self) -> sqlite3.Connection:
        """Return a configured SQLite connection."""
        conn = sqlite3.connect(str(self._db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    # =========================================================================
    # Work Units
    # =========================================================================

    def save_work_unit(self, unit: PQNWorkUnit) -> None:
        """Insert or update a work unit."""
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO work_units
                    (work_unit_id, description, config_json, creator_id, status, source, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        unit.work_unit_id,
                        unit.description,
                        json.dumps(unit.config),
                        unit.creator_id,
                        unit.status.value,
                        unit.source,
                        unit.created_at.isoformat(),
                        unit.updated_at.isoformat(),
                    ),
                )
                conn.commit()

    def get_work_unit(self, work_unit_id: str) -> Optional[PQNWorkUnit]:
        """Retrieve a work unit by ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM work_units WHERE work_unit_id = ?",
                (work_unit_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_work_unit(row)

    def list_work_units(
        self,
        status_filter: Optional[WorkUnitStatus] = None,
        limit: int = 100,
    ) -> List[PQNWorkUnit]:
        """List work units with optional status filter."""
        with self._connect() as conn:
            if status_filter:
                cursor = conn.execute(
                    "SELECT * FROM work_units WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status_filter.value, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM work_units ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )
            return [self._row_to_work_unit(row) for row in cursor.fetchall()]

    def _row_to_work_unit(self, row: sqlite3.Row) -> PQNWorkUnit:
        unit = PQNWorkUnit(
            description=row["description"],
            config=json.loads(row["config_json"]),
            creator_id=row["creator_id"],
            work_unit_id=row["work_unit_id"],
            status=WorkUnitStatus(row["status"]),
            source=row["source"] if "source" in row.keys() else "internal",
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
        return unit

    # =========================================================================
    # Submissions
    # =========================================================================

    def save_submission(self, sub: rESPSubmission) -> None:
        """Insert or update a submission."""
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO submissions
                    (submission_id, work_unit_id, submitter_id, metrics_json, artifacts_json, status, source, submitted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sub.submission_id,
                        sub.work_unit_id,
                        sub.submitter_id,
                        json.dumps(sub.metrics),
                        json.dumps(sub.artifacts),
                        sub.status.value,
                        sub.source,
                        sub.submitted_at.isoformat(),
                    ),
                )
                conn.commit()

    def get_submission(self, submission_id: str) -> Optional[rESPSubmission]:
        """Retrieve a submission by ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM submissions WHERE submission_id = ?",
                (submission_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_submission(row)

    def list_submissions(
        self,
        work_unit_id: Optional[str] = None,
        status_filter: Optional[SubmissionStatus] = None,
        limit: int = 100,
    ) -> List[rESPSubmission]:
        """List submissions with optional filters."""
        with self._connect() as conn:
            query = "SELECT * FROM submissions WHERE 1=1"
            params: List[Any] = []
            if work_unit_id:
                query += " AND work_unit_id = ?"
                params.append(work_unit_id)
            if status_filter:
                query += " AND status = ?"
                params.append(status_filter.value)
            query += " ORDER BY submitted_at DESC LIMIT ?"
            params.append(limit)
            cursor = conn.execute(query, params)
            return [self._row_to_submission(row) for row in cursor.fetchall()]

    def _row_to_submission(self, row: sqlite3.Row) -> rESPSubmission:
        sub = rESPSubmission(
            work_unit_id=row["work_unit_id"],
            submitter_id=row["submitter_id"],
            metrics=json.loads(row["metrics_json"]),
            artifacts=json.loads(row["artifacts_json"]),
            submission_id=row["submission_id"],
            status=SubmissionStatus(row["status"]),
            source=row["source"] if "source" in row.keys() else "internal",
            submitted_at=datetime.fromisoformat(row["submitted_at"]),
        )
        return sub

    # =========================================================================
    # Verification Decisions
    # =========================================================================

    def save_decision(self, dec: VerificationDecision) -> None:
        """Insert or update a verification decision."""
        with self._lock:
            with self._connect() as conn:
                confidence = getattr(dec, "confidence", None)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO verification_decisions
                    (decision_id, submission_id, decision, verifier_id, rationale, confidence, decided_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dec.decision_id,
                        dec.submission_id,
                        dec.decision,
                        dec.verifier_id,
                        dec.rationale,
                        confidence,
                        dec.decided_at.isoformat(),
                    ),
                )
                conn.commit()

    def get_decision(self, decision_id: str) -> Optional[VerificationDecision]:
        """Retrieve a decision by ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM verification_decisions WHERE decision_id = ?",
                (decision_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_decision(row)

    def list_decisions(
        self,
        submission_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[VerificationDecision]:
        """List decisions with optional submission filter."""
        with self._connect() as conn:
            if submission_id:
                cursor = conn.execute(
                    "SELECT * FROM verification_decisions WHERE submission_id = ? ORDER BY decided_at DESC LIMIT ?",
                    (submission_id, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM verification_decisions ORDER BY decided_at DESC LIMIT ?",
                    (limit,),
                )
            return [self._row_to_decision(row) for row in cursor.fetchall()]

    def _row_to_decision(self, row: sqlite3.Row) -> VerificationDecision:
        dec = VerificationDecision(
            submission_id=row["submission_id"],
            decision=row["decision"],
            verifier_id=row["verifier_id"],
            rationale=row["rationale"] or "",
            decision_id=row["decision_id"],
            decided_at=datetime.fromisoformat(row["decided_at"]),
        )
        dec.confidence = row["confidence"]
        return dec

    # =========================================================================
    # Contributions
    # =========================================================================

    def save_contribution(self, cr: ContributionRecord) -> None:
        """Insert or update a contribution record."""
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO contributions
                    (contribution_id, work_unit_id, submission_id, decision_id, contributor_id, score, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cr.contribution_id,
                        cr.work_unit_id,
                        cr.submission_id,
                        cr.decision_id,
                        cr.contributor_id,
                        cr.score,
                        cr.recorded_at.isoformat(),
                    ),
                )
                conn.commit()

    def get_contribution(self, contribution_id: str) -> Optional[ContributionRecord]:
        """Retrieve a contribution by ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM contributions WHERE contribution_id = ?",
                (contribution_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_contribution(row)

    def list_contributions(
        self,
        contributor_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ContributionRecord]:
        """List contributions with optional contributor filter."""
        with self._connect() as conn:
            if contributor_id:
                cursor = conn.execute(
                    "SELECT * FROM contributions WHERE contributor_id = ? ORDER BY recorded_at DESC LIMIT ?",
                    (contributor_id, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM contributions ORDER BY recorded_at DESC LIMIT ?",
                    (limit,),
                )
            return [self._row_to_contribution(row) for row in cursor.fetchall()]

    def _row_to_contribution(self, row: sqlite3.Row) -> ContributionRecord:
        cr = ContributionRecord(
            work_unit_id=row["work_unit_id"],
            submission_id=row["submission_id"],
            decision_id=row["decision_id"],
            contributor_id=row["contributor_id"],
            score=row["score"],
            contribution_id=row["contribution_id"],
            recorded_at=datetime.fromisoformat(row["recorded_at"]),
        )
        return cr

    # =========================================================================
    # Participants
    # =========================================================================

    def save_participant(self, p: ParticipantIdentity) -> None:
        """Insert or update a participant."""
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO participants
                    (participant_id, display_name, model_type, compute_capacity, capability_tags_json, metadata_json, registered_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        p.participant_id,
                        p.display_name,
                        p.model_type,
                        p.compute_capacity,
                        json.dumps(p.capability_tags),
                        json.dumps(p.metadata),
                        p.registered_at.isoformat(),
                    ),
                )
                conn.commit()

    def get_participant(self, participant_id: str) -> Optional[ParticipantIdentity]:
        """Retrieve a participant by ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM participants WHERE participant_id = ?",
                (participant_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_participant(row)

    def list_participants(self, limit: int = 100) -> List[ParticipantIdentity]:
        """List all participants."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM participants ORDER BY registered_at DESC LIMIT ?",
                (limit,),
            )
            return [self._row_to_participant(row) for row in cursor.fetchall()]

    def _row_to_participant(self, row: sqlite3.Row) -> ParticipantIdentity:
        p = ParticipantIdentity(
            participant_id=row["participant_id"],
            display_name=row["display_name"] or "",
            model_type=row["model_type"] or "",
            compute_capacity=row["compute_capacity"] or "",
            capability_tags=json.loads(row["capability_tags_json"] or "[]"),
            metadata=json.loads(row["metadata_json"] or "{}"),
            registered_at=datetime.fromisoformat(row["registered_at"]),
        )
        return p

    # =========================================================================
    # Gate Decisions
    # =========================================================================

    def save_gate_decision(self, gd: GateDecision) -> None:
        """Insert or update a gate decision."""
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO gate_decisions
                    (decision_id, participant_id, decision, tier, reason, decider_id, decided_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        gd.decision_id,
                        gd.participant_id,
                        gd.decision,
                        gd.tier.value,
                        gd.reason,
                        gd.decider_id,
                        gd.decided_at.isoformat(),
                    ),
                )
                conn.commit()

    def get_gate_decision(self, decision_id: str) -> Optional[GateDecision]:
        """Retrieve a gate decision by ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM gate_decisions WHERE decision_id = ?",
                (decision_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_gate_decision(row)

    def list_gate_decisions(
        self,
        participant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[GateDecision]:
        """List gate decisions with optional participant filter."""
        with self._connect() as conn:
            if participant_id:
                cursor = conn.execute(
                    "SELECT * FROM gate_decisions WHERE participant_id = ? ORDER BY decided_at DESC LIMIT ?",
                    (participant_id, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM gate_decisions ORDER BY decided_at DESC LIMIT ?",
                    (limit,),
                )
            return [self._row_to_gate_decision(row) for row in cursor.fetchall()]

    def _row_to_gate_decision(self, row: sqlite3.Row) -> GateDecision:
        gd = GateDecision(
            participant_id=row["participant_id"],
            decision=row["decision"],
            tier=ParticipantTier(row["tier"]),
            reason=row["reason"] or "",
            decider_id=row["decider_id"],
            decision_id=row["decision_id"],
            decided_at=datetime.fromisoformat(row["decided_at"]),
        )
        return gd

    # =========================================================================
    # Utility
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Return counts for all tables."""
        with self._connect() as conn:
            stats = {}
            for table in ["work_units", "submissions", "verification_decisions", "contributions", "participants", "gate_decisions"]:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            return stats

    @property
    def db_path(self) -> Path:
        return self._db_path


# Singleton instance
_store_instance: Optional[SQLiteStore] = None


def get_sqlite_store(
    db_dir: Optional[Path] = None,
    db_filename: str = DEFAULT_DB_FILENAME,
) -> SQLiteStore:
    """
    Get singleton SQLiteStore instance.

    Args:
        db_dir: Directory for database file
        db_filename: Database filename

    Returns:
        SQLiteStore singleton
    """
    global _store_instance
    if _store_instance is None:
        _store_instance = SQLiteStore(db_dir=db_dir, db_filename=db_filename)
    return _store_instance


def reset_sqlite_store() -> None:
    """Reset singleton (for testing)."""
    global _store_instance
    _store_instance = None
