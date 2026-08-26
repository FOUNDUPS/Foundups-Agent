"""Non-production A/B evidence storage for WRE PatternMemory."""

from __future__ import annotations

from datetime import datetime
import logging
import sqlite3
from typing import Any, Optional
import uuid

logger = logging.getLogger(__name__)


def initialize_ab_schema(conn: Any) -> None:
    """Create or migrate the non-production A/B evidence table."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS ab_test_assignments (
               test_id TEXT PRIMARY KEY,
               skill_name TEXT NOT NULL,
               control_version TEXT NOT NULL,
               treatment_version TEXT NOT NULL,
               start_time TEXT NOT NULL,
               end_time TEXT,
               status TEXT DEFAULT 'running',
               winner TEXT,
               sample_size_target INTEGER DEFAULT 20,
               control_successes INTEGER DEFAULT 0,
               control_trials INTEGER DEFAULT 0,
               treatment_successes INTEGER DEFAULT 0,
               treatment_trials INTEGER DEFAULT 0
           )"""
    )
    try:
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(ab_test_assignments)").fetchall()
        }
        if "winner" not in columns:
            conn.execute("ALTER TABLE ab_test_assignments ADD COLUMN winner TEXT")
    except sqlite3.OperationalError as exc:
        logger.warning(
            "[PATTERN-MEMORY] A/B schema upgrade failed; error_type=%s",
            type(exc).__name__,
        )


class PatternABEvidenceMixin:
    """SQLite-backed A/B statistics with no production-promotion authority."""

    conn: Any

    def schedule_ab_test(
        self,
        skill_name: str,
        control_version: str,
        treatment_version: str,
        sample_size_target: int = 20,
    ) -> str:
        """Schedule two distinct variants with a per-variant sample target."""
        self._validate_ab_schedule(
            skill_name, control_version, treatment_version, sample_size_target
        )
        test_id = f"ab_{skill_name}_{uuid.uuid4().hex[:8]}"
        self.conn.execute(
            """INSERT INTO ab_test_assignments (
                   test_id, skill_name, control_version, treatment_version,
                   start_time, sample_size_target
               ) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                test_id,
                skill_name,
                control_version,
                treatment_version,
                datetime.now().isoformat(),
                sample_size_target,
            ),
        )
        self.conn.commit()
        logger.info("[PATTERN-MEMORY] Scheduled A/B test %s", test_id)
        return test_id

    def get_active_ab_test(self, skill_name: str) -> Optional[dict[str, Any]]:
        """Return the newest running statistical test for one skill."""
        row = self.conn.execute(
            """SELECT * FROM ab_test_assignments
               WHERE skill_name = ? AND status = 'running'
               ORDER BY start_time DESC LIMIT 1""",
            (skill_name,),
        ).fetchone()
        return dict(row) if row else None

    def record_ab_outcome(self, test_id: str, variant: str, success: bool) -> None:
        """Record one exact-Boolean sample against a running, named variant."""
        if variant not in {"control", "treatment"}:
            raise ValueError("variant must be control or treatment")
        if type(success) is not bool:
            raise TypeError("A/B success must be a boolean")
        prefix = "control" if variant == "control" else "treatment"
        cursor = self.conn.execute(
            f"""UPDATE ab_test_assignments
                SET {prefix}_trials = {prefix}_trials + 1,
                    {prefix}_successes = {prefix}_successes + ?
                WHERE test_id = ? AND status = 'running'""",
            (1 if success else 0, test_id),
        )
        if cursor.rowcount != 1:
            self.conn.rollback()
            raise ValueError("A/B test is missing or inactive")
        self.conn.commit()

    def check_ab_promotion(
        self, test_id: str, min_margin: float = 0.10
    ) -> Optional[str]:
        """Return a statistical winner; never grant production authority."""
        if type(min_margin) not in {int, float} or not 0 <= min_margin <= 1:
            raise ValueError("min_margin must be between zero and one")
        row = self.conn.execute(
            "SELECT * FROM ab_test_assignments WHERE test_id = ?", (test_id,)
        ).fetchone()
        if not row:
            return None
        test = dict(row)
        target = test["sample_size_target"]
        if test["control_trials"] < target or test["treatment_trials"] < target:
            return None
        control_rate = test["control_successes"] / test["control_trials"]
        treatment_rate = test["treatment_successes"] / test["treatment_trials"]
        margin = treatment_rate - control_rate
        if margin >= min_margin:
            return "treatment"
        if margin <= -min_margin:
            return "control"
        return None

    def promote_variation(self, variation_id: str) -> None:
        """Reject legacy unauthenticated production mutation."""
        raise PermissionError(
            "Production variation promotion requires the unimplemented "
            "independent signed promoter authority"
        )

    def stage_variation_candidate(self, variation_id: str) -> None:
        """Record an A/B winner without granting production authority."""
        self._update_variation_state(variation_id, "candidate_ready", promoted=0)

    def archive_variation(self, variation_id: str) -> None:
        """Archive a losing variation without deleting its evidence."""
        self._update_variation_state(variation_id, "archived", promoted=0)

    def close_ab_test(self, test_id: str, winner: str) -> None:
        """Close a running statistical test and durably record its label."""
        allowed = {"control", "treatment", "treatment_candidate", "inconclusive"}
        if winner not in allowed:
            raise ValueError("A/B winner label is invalid")
        cursor = self.conn.execute(
            """UPDATE ab_test_assignments
               SET status = 'completed', end_time = ?, winner = ?
               WHERE test_id = ? AND status = 'running'""",
            (datetime.now().isoformat(), winner, test_id),
        )
        if cursor.rowcount != 1:
            self.conn.rollback()
            raise ValueError("A/B test is missing or inactive")
        self.conn.commit()
        logger.info("[PATTERN-MEMORY] Closed A/B test %s", test_id)

    @staticmethod
    def _validate_ab_schedule(
        skill_name: str,
        control_version: str,
        treatment_version: str,
        sample_size_target: int,
    ) -> None:
        if not isinstance(skill_name, str) or not skill_name.strip():
            raise ValueError("skill_name must be non-empty")
        if not isinstance(control_version, str) or not control_version.strip():
            raise ValueError("control_version must be non-empty")
        if not isinstance(treatment_version, str) or not treatment_version.strip():
            raise ValueError("treatment_version must be non-empty")
        if control_version == treatment_version:
            raise ValueError("control and treatment versions must differ")
        if type(sample_size_target) is not int or sample_size_target < 1:
            raise ValueError("sample_size_target must be a positive integer")

    def _update_variation_state(
        self, variation_id: str, status: str, *, promoted: int
    ) -> None:
        cursor = self.conn.execute(
            """UPDATE skill_variations SET promoted = ?, test_status = ?
               WHERE variation_id = ?""",
            (promoted, status, variation_id),
        )
        if cursor.rowcount != 1:
            self.conn.rollback()
            raise ValueError("variation is missing")
        self.conn.commit()
        logger.info("[PATTERN-MEMORY] Variation %s is %s", variation_id, status)
