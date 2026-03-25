#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pattern Memory - SQLite Outcome Storage for Recursive Learning

Per WSP 60 (Module Memory Architecture), WSP 48 (Recursive Self-Improvement)

Stores skill execution outcomes for recursive evolution:
- Skill executed with what parameters?
- What was the outcome (success/failure)?
- What was the pattern fidelity?
- What did we learn?

This enables skills to evolve via A/B testing and converge to >90% fidelity

WSP Compliance:
- WSP 60: Module Memory Architecture (pattern recall)
- WSP 48: Recursive Self-Improvement (learning loop)
- WSP 91: DAEMON Observability (breadcrumb tracking)
- WSP 96: WRE Skills Wardrobe (trainable weights)
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class SkillOutcome:
    """
    Record of skill execution outcome for learning

    Per WSP 96: Skills are trainable weights that evolve
    """
    execution_id: str
    skill_name: str
    agent: str  # qwen, gemma, grok, ui-tars
    timestamp: str  # ISO format
    input_context: str  # JSON string
    output_result: str  # JSON string
    success: bool
    pattern_fidelity: float  # 0.0-1.0 from Gemma validation
    outcome_quality: float  # 0.0-1.0 correctness score
    execution_time_ms: int
    step_count: int  # Number of steps in micro chain-of-thought
    failed_at_step: Optional[int] = None  # Which step failed (if any)
    notes: Optional[str] = None


class PatternMemory:
    """
    Pattern Memory - SQLite storage for skill outcomes and recursive learning

    Per WSP 60: Enable recall instead of computation
    Per WSP 48: Store outcomes for self-improvement

    Database Schema:
    - skill_outcomes: Execution records
    - skill_variations: A/B test variations
    - learning_events: Pattern improvement events
    - false_positives: Learned skip patterns to avoid rework

    This enables:
    1. Recall successful patterns (50-200 tokens)
    2. A/B test variations (Qwen generates, Gemma validates)
    3. Converge to >90% fidelity over 4 weeks
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize pattern memory database

        Args:
            db_path: Path to SQLite database file
        """
        # Reuse shared singleton only for default production path.
        # Tests and explicit db paths must get isolated storage.
        self._uses_shared_singleton = db_path is None
        if self._uses_shared_singleton and getattr(PatternMemory, "_initialized", False):
            self.__dict__.update(getattr(PatternMemory, "_shared_state", {}))
            logger.debug("[PATTERN-MEMORY] Reusing existing singleton instance")
            return

        if db_path is None:
            self.db_path = Path(__file__).parent.parent / "data" / "pattern_memory.db"
        else:
            self.db_path = Path(db_path)

        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self.false_positive_columns: set = set()

        self._initialize_schema()
        self._seed_false_positive_memory()

        # Log init once per process to reduce telemetry spam for shared instance.
        if self._uses_shared_singleton:
            if not getattr(PatternMemory, "_initialized", False):
                logger.info(f"[PATTERN-MEMORY] Initialized - db={self.db_path}")
            PatternMemory._shared_state = dict(self.__dict__)
            PatternMemory._initialized = True
        else:
            logger.info(f"[PATTERN-MEMORY] Initialized (isolated) - db={self.db_path}")

    def _initialize_schema(self) -> None:
        """
        Create database schema if not exists

        Per WSP 60: Structured memory for pattern recall
        """
        cursor = self.conn.cursor()

        # Skill outcomes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_outcomes (
                execution_id TEXT PRIMARY KEY,
                skill_name TEXT NOT NULL,
                agent TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                input_context TEXT NOT NULL,
                output_result TEXT NOT NULL,
                success INTEGER NOT NULL,
                pattern_fidelity REAL NOT NULL,
                outcome_quality REAL NOT NULL,
                execution_time_ms INTEGER NOT NULL,
                step_count INTEGER NOT NULL,
                failed_at_step INTEGER,
                notes TEXT
            )
        """)

        # Index for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_skill_outcomes_skill_name
            ON skill_outcomes(skill_name)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_skill_outcomes_timestamp
            ON skill_outcomes(timestamp DESC)
        """)

        # Skill variations table (for A/B testing)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_variations (
                variation_id TEXT PRIMARY KEY,
                skill_name TEXT NOT NULL,
                parent_version TEXT,
                variation_content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                test_status TEXT DEFAULT 'testing',
                avg_fidelity REAL,
                execution_count INTEGER DEFAULT 0,
                promoted BOOLEAN DEFAULT 0
            )
        """)

        # Learning events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_events (
                event_id TEXT PRIMARY KEY,
                skill_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                description TEXT,
                before_fidelity REAL,
                after_fidelity REAL,
                variation_id TEXT,
                continuity_id TEXT,
                parent_continuity_id TEXT,
                execution_id TEXT
            )
        """)

        # Backfill continuity columns if table existed before schema upgrade
        try:
            cursor.execute("PRAGMA table_info(learning_events)")
            columns = {row["name"] for row in cursor.fetchall()}
            if "continuity_id" not in columns:
                cursor.execute("ALTER TABLE learning_events ADD COLUMN continuity_id TEXT")
            if "parent_continuity_id" not in columns:
                cursor.execute("ALTER TABLE learning_events ADD COLUMN parent_continuity_id TEXT")
            if "execution_id" not in columns:
                cursor.execute("ALTER TABLE learning_events ADD COLUMN execution_id TEXT")
        except sqlite3.OperationalError as exc:
            logger.warning("[PATTERN-MEMORY] Learning events schema upgrade failed: %s", exc)

        # A/B test assignments table (Sprint 1 - TT-SI closure)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ab_test_assignments (
                test_id TEXT PRIMARY KEY,
                skill_name TEXT NOT NULL,
                control_version TEXT NOT NULL,
                treatment_version TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT DEFAULT 'running',
                sample_size_target INTEGER DEFAULT 20,
                control_successes INTEGER DEFAULT 0,
                control_trials INTEGER DEFAULT 0,
                treatment_successes INTEGER DEFAULT 0,
                treatment_trials INTEGER DEFAULT 0
            )
        """)

        # Telemetry counters table (Sprint 1 - observability)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_counters (
                counter_name TEXT PRIMARY KEY,
                counter_value INTEGER DEFAULT 0,
                last_updated TEXT
            )
        """)

        # Retrieval quality tracking (Sprint 2 - Agentic RAG)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS retrieval_quality (
                retrieval_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                query TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                results_count INTEGER,
                relevance_score REAL,
                used_in_execution INTEGER DEFAULT 0,
                retrieval_time_ms INTEGER
            )
        """)

        # Skill relationship edges (Sprint 2 - Graph-of-Thought)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_edges (
                edge_id TEXT PRIMARY KEY,
                source_skill TEXT NOT NULL,
                target_skill TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                evidence TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_skill_edges_source
            ON skill_edges(source_skill)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_skill_edges_target
            ON skill_edges(target_skill)
        """)

        # False positives table (WSP 48 - learn from mistakes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS false_positives (
                entity_type TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                reason TEXT NOT NULL,
                actual_location TEXT,
                created_at TEXT NOT NULL,
                PRIMARY KEY (entity_type, entity_name)
            )
        """)

        # Backfill columns if table existed before schema upgrade
        try:
            cursor.execute("PRAGMA table_info(false_positives)")
            columns = {row["name"] for row in cursor.fetchall()}
            if "actual_location" not in columns:
                cursor.execute("ALTER TABLE false_positives ADD COLUMN actual_location TEXT")
            if "created_at" not in columns:
                cursor.execute("ALTER TABLE false_positives ADD COLUMN created_at TEXT")
        except sqlite3.OperationalError as exc:
            logger.warning("[PATTERN-MEMORY] False-positive schema verification failed: %s", exc)

        try:
            cursor.execute("PRAGMA table_info(false_positives)")
            self.false_positive_columns = {row["name"] for row in cursor.fetchall()}
        except sqlite3.OperationalError:
            self.false_positive_columns = set()

        self.conn.commit()
        logger.debug("[PATTERN-MEMORY] Schema initialized")

    def _seed_false_positive_memory(self) -> None:
        """
        Seed known false positives so automation skips learned mistakes.

        This prevents repeated scaffolding of entities we know are valid.
        """
        seeds = [
            {
                "entity_type": "module",
                "entity_name": "holo_dae",
                "reason": (
                    "HoloDAE is a coordinator class in holo_index/qwen_advisor/, "
                    "not a standalone module"
                ),
                "actual_location": "holo_index/qwen_advisor/holodae_coordinator.py",
            }
        ]

        for seed in seeds:
            try:
                existing = self.get_false_positive_reason(seed["entity_type"], seed["entity_name"])
                if not existing or not existing.get("created_at") or not existing.get("actual_location"):
                    self.record_false_positive(
                        entity_type=seed["entity_type"],
                        entity_name=seed["entity_name"],
                        reason=seed["reason"],
                        actual_location=seed.get("actual_location"),
                    )
            except Exception as exc:
                logger.warning(
                    "[PATTERN-MEMORY] Failed to seed false positive %s/%s: %s",
                    seed.get("entity_type"),
                    seed.get("entity_name"),
                    exc,
                )

    def store_outcome(self, outcome: SkillOutcome) -> None:
        """
        Store skill execution outcome

        Per WSP 48: Record outcomes for learning

        Args:
            outcome: Skill execution outcome
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO skill_outcomes (
                execution_id, skill_name, agent, timestamp,
                input_context, output_result, success,
                pattern_fidelity, outcome_quality, execution_time_ms,
                step_count, failed_at_step, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            outcome.execution_id,
            outcome.skill_name,
            outcome.agent,
            outcome.timestamp,
            outcome.input_context,
            outcome.output_result,
            1 if outcome.success else 0,
            outcome.pattern_fidelity,
            outcome.outcome_quality,
            outcome.execution_time_ms,
            outcome.step_count,
            outcome.failed_at_step,
            outcome.notes
        ))

        self.conn.commit()

        logger.info(f"[PATTERN-MEMORY] Stored outcome - skill={outcome.skill_name}, "
                   f"exec_id={outcome.execution_id}, fidelity={outcome.pattern_fidelity:.2f}")

    def record_false_positive(
        self,
        entity_type: str,
        entity_name: str,
        reason: str,
        actual_location: Optional[str] = None
    ) -> None:
        """
        Persist a false positive so automation will skip it next time.

        Args:
            entity_type: Domain of entity (e.g., 'module', 'file', 'test')
            entity_name: Identifier or name of the entity
            reason: Human-readable explanation for skipping
            actual_location: Where the entity truly lives (if applicable)
        """
        cursor = self.conn.cursor()

        # Remove existing records when table lacks uniqueness constraints
        try:
            cursor.execute(
                "DELETE FROM false_positives WHERE entity_type = ? AND entity_name = ?",
                (entity_type, entity_name)
            )
        except sqlite3.OperationalError:
            pass

        insert_columns = ["entity_type", "entity_name", "reason"]
        values = [entity_type, entity_name, reason]

        if "recorded_by" in self.false_positive_columns:
            insert_columns.append("recorded_by")
            values.append("wsp_automation")

        if "actual_location" in self.false_positive_columns:
            insert_columns.append("actual_location")
            values.append(actual_location)

        timestamp_value = datetime.now().isoformat()
        if "created_at" in self.false_positive_columns:
            insert_columns.append("created_at")
            values.append(timestamp_value)
        if "timestamp" in self.false_positive_columns:
            insert_columns.append("timestamp")
            values.append(timestamp_value)

        placeholders = ", ".join(["?"] * len(values))
        cursor.execute(
            f"INSERT OR REPLACE INTO false_positives ({', '.join(insert_columns)}) "
            f"VALUES ({placeholders})",
            values
        )
        self.conn.commit()
        logger.info(
            "[PATTERN-MEMORY] Recorded false positive - %s/%s",
            entity_type,
            entity_name,
        )

    def is_false_positive(self, entity_type: str, entity_name: str) -> bool:
        """Return True if the entity is a known false positive."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 1 FROM false_positives
            WHERE entity_type = ? AND entity_name = ?
            LIMIT 1
        """, (entity_type, entity_name))
        return cursor.fetchone() is not None

    def get_false_positive_reason(
        self,
        entity_type: str,
        entity_name: str
    ) -> Optional[Dict[str, Optional[str]]]:
        """
        Retrieve reason and metadata for a known false positive.

        Returns:
            Dict with reason and actual_location if found, otherwise None.
        """
        cursor = self.conn.cursor()

        select_columns = ["reason"]
        created_key = None

        if "actual_location" in self.false_positive_columns:
            select_columns.append("actual_location")

        if "created_at" in self.false_positive_columns:
            select_columns.append("created_at")
            created_key = "created_at"
        elif "timestamp" in self.false_positive_columns:
            select_columns.append("timestamp")
            created_key = "timestamp"

        columns_sql = ", ".join(select_columns)

        cursor.execute(f"""
            SELECT {columns_sql}
            FROM false_positives
            WHERE entity_type = ? AND entity_name = ?
            LIMIT 1
        """, (entity_type, entity_name))
        row = cursor.fetchone()
        if not row:
            return None

        result = {"reason": row["reason"]}
        if "actual_location" in self.false_positive_columns:
            result["actual_location"] = row["actual_location"]
        if created_key:
            result["created_at"] = row[created_key]

        return result

    def recall_successful_patterns(
        self,
        skill_name: str,
        min_fidelity: float = 0.90,
        limit: int = 10
    ) -> List[Dict]:
        """
        Recall successful execution patterns for a skill

        Per WSP 60: Recall instead of compute (50-200 tokens vs 5000+)

        This enables Qwen to learn from past successful executions:
        - What input context led to high fidelity?
        - What output patterns worked well?
        - What step sequences succeeded?

        Args:
            skill_name: Skill to recall patterns for
            min_fidelity: Minimum pattern fidelity threshold
            limit: Max number of patterns to recall

        Returns:
            List of successful execution records
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM skill_outcomes
            WHERE skill_name = ?
              AND success = 1
              AND pattern_fidelity >= ?
            ORDER BY pattern_fidelity DESC, timestamp DESC
            LIMIT ?
        """, (skill_name, min_fidelity, limit))

        rows = cursor.fetchall()

        patterns = [dict(row) for row in rows]

        logger.info(f"[PATTERN-MEMORY] Recalled {len(patterns)} successful patterns - "
                   f"skill={skill_name}, min_fidelity={min_fidelity}")

        return patterns

    def recall_failure_patterns(
        self,
        skill_name: str,
        max_fidelity: float = 0.70,
        limit: int = 10
    ) -> List[Dict]:
        """
        Recall failed execution patterns for learning

        Per WSP 48: Learn from failures to improve

        This enables Qwen to generate better variations:
        - Which steps failed most often?
        - What input contexts cause failures?
        - What validation patterns need strengthening?

        Args:
            skill_name: Skill to recall failures for
            max_fidelity: Maximum pattern fidelity (failures)
            limit: Max number of patterns to recall

        Returns:
            List of failed execution records
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM skill_outcomes
            WHERE skill_name = ?
              AND pattern_fidelity <= ?
            ORDER BY pattern_fidelity ASC, timestamp DESC
            LIMIT ?
        """, (skill_name, max_fidelity, limit))

        rows = cursor.fetchall()

        patterns = [dict(row) for row in rows]

        logger.info(f"[PATTERN-MEMORY] Recalled {len(patterns)} failure patterns - "
                   f"skill={skill_name}, max_fidelity={max_fidelity}")

        return patterns

    def get_skill_metrics(self, skill_name: str, days: int = 7) -> Dict:
        """
        Get aggregated metrics for a skill over time period

        Per WSP 91: Observability for monitoring

        Returns:
            Dict with avg fidelity, success rate, execution count
        """
        cursor = self.conn.cursor()

        # Calculate metrics from last N days
        cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT
                COUNT(*) as execution_count,
                AVG(pattern_fidelity) as avg_fidelity,
                AVG(outcome_quality) as avg_quality,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as success_rate,
                AVG(execution_time_ms) as avg_time_ms,
                AVG(step_count) as avg_steps
            FROM skill_outcomes
            WHERE skill_name = ? AND timestamp >= ?
        """, (skill_name, cutoff_time))

        row = cursor.fetchone()

        if row["execution_count"] == 0:
            return {
                "skill_name": skill_name,
                "execution_count": 0,
                "avg_fidelity": 0.0,
                "avg_quality": 0.0,
                "success_rate": 0.0,
                "avg_time_ms": 0,
                "avg_steps": 0,
                "period_days": days
            }

        return {
            "skill_name": skill_name,
            "execution_count": row["execution_count"],
            "avg_fidelity": round(row["avg_fidelity"], 3),
            "avg_quality": round(row["avg_quality"], 3),
            "success_rate": round(row["success_rate"], 3),
            "avg_time_ms": int(row["avg_time_ms"]),
            "avg_steps": round(row["avg_steps"], 1),
            "period_days": days
        }

    def store_variation(
        self,
        variation_id: str,
        skill_name: str,
        variation_content: str,
        parent_version: Optional[str] = None,
        created_by: str = "qwen"
    ) -> None:
        """
        Store skill variation for A/B testing

        Per WSP 48: Recursive self-improvement through variation testing

        Args:
            variation_id: Unique variation identifier
            skill_name: Base skill name
            variation_content: Full SKILL.md content of variation
            parent_version: Version this was derived from
            created_by: Agent that created variation (qwen, 0102)
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO skill_variations (
                variation_id, skill_name, parent_version,
                variation_content, created_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            variation_id,
            skill_name,
            parent_version,
            variation_content,
            datetime.now().isoformat(),
            created_by
        ))

        self.conn.commit()

        logger.info(f"[PATTERN-MEMORY] Stored variation - skill={skill_name}, "
                   f"var_id={variation_id}, created_by={created_by}")

    def record_learning_event(
        self,
        event_id: str,
        skill_name: str,
        event_type: str,
        description: str,
        before_fidelity: Optional[float] = None,
        after_fidelity: Optional[float] = None,
        variation_id: Optional[str] = None,
        continuity_id: Optional[str] = None,
        parent_continuity_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> None:
        """
        Record learning event for skill evolution tracking with continuity lineage.

        Per WSP 48: Track self-improvement progress
        Per WSP 91: Observability with continuity metadata

        Event types: variation_created, variation_promoted, threshold_tuned, rollback

        Args:
            event_id: Unique event identifier
            skill_name: Skill that evolved
            event_type: Type of learning event
            description: Human-readable description
            before_fidelity: Fidelity before change
            after_fidelity: Fidelity after change
            variation_id: Related variation (if applicable)
            continuity_id: Continuity ID linking to work chain
            parent_continuity_id: Parent continuity for lineage tracking
            execution_id: Execution ID that triggered this event
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO learning_events (
                event_id, skill_name, event_type, timestamp,
                description, before_fidelity, after_fidelity, variation_id,
                continuity_id, parent_continuity_id, execution_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            skill_name,
            event_type,
            datetime.now().isoformat(),
            description,
            before_fidelity,
            after_fidelity,
            variation_id,
            continuity_id,
            parent_continuity_id,
            execution_id
        ))

        self.conn.commit()

        continuity_suffix = f", continuity={continuity_id}" if continuity_id else ""
        logger.info(f"[PATTERN-MEMORY] Learning event - skill={skill_name}, "
                   f"type={event_type}, event_id={event_id}{continuity_suffix}")

    def get_evolution_history(self, skill_name: str) -> List[Dict]:
        """
        Get evolution history for a skill

        Per WSP 48: Track recursive improvement over time

        Returns:
            List of learning events in chronological order
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM learning_events
            WHERE skill_name = ?
            ORDER BY timestamp ASC
        """, (skill_name,))

        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def get_evolution_by_continuity(
        self,
        continuity_id: str,
        include_children: bool = False
    ) -> List[Dict]:
        """
        Get evolution events linked to a continuity chain.

        Per WSP 91: Observability - query evolution lineage
        Per WSP 97: Answer "what work led to this evolved skill?"

        Args:
            continuity_id: Continuity ID to query
            include_children: If True, also return events where this is the parent

        Returns:
            List of learning events linked to this continuity chain
        """
        cursor = self.conn.cursor()

        if include_children:
            cursor.execute("""
                SELECT * FROM learning_events
                WHERE continuity_id = ? OR parent_continuity_id = ?
                ORDER BY timestamp ASC
            """, (continuity_id, continuity_id))
        else:
            cursor.execute("""
                SELECT * FROM learning_events
                WHERE continuity_id = ?
                ORDER BY timestamp ASC
            """, (continuity_id,))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_evolution_by_execution(self, execution_id: str) -> List[Dict]:
        """
        Get evolution events triggered by a specific execution.

        Per WSP 91: Answer "which execution triggered this skill evolution?"

        Args:
            execution_id: Execution ID to query

        Returns:
            List of learning events triggered by this execution
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM learning_events
            WHERE execution_id = ?
            ORDER BY timestamp ASC
        """, (execution_id,))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------ #
    #  A/B Testing & Variation Promotion (Sprint 1 - TT-SI Closure)      #
    # ------------------------------------------------------------------ #

    def schedule_ab_test(
        self,
        skill_name: str,
        control_version: str,
        treatment_version: str,
        sample_size_target: int = 20
    ) -> str:
        """
        Schedule A/B test between control and treatment variation.

        Per WRE_COT_DEEP_ANALYSIS.md Gap D: Close TT-SI loop

        Args:
            skill_name: Skill being tested
            control_version: Current production version ID
            treatment_version: New variation ID to test
            sample_size_target: Min samples before promotion decision

        Returns:
            test_id for tracking
        """
        import uuid
        test_id = f"ab_{skill_name}_{uuid.uuid4().hex[:8]}"
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO ab_test_assignments (
                test_id, skill_name, control_version, treatment_version,
                start_time, sample_size_target
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            test_id, skill_name, control_version, treatment_version,
            datetime.now().isoformat(), sample_size_target
        ))
        self.conn.commit()
        logger.info(f"[PATTERN-MEMORY] Scheduled A/B test {test_id}")
        return test_id

    def get_active_ab_test(self, skill_name: str) -> Optional[Dict]:
        """Get active A/B test for skill if exists."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM ab_test_assignments
            WHERE skill_name = ? AND status = 'running'
            ORDER BY start_time DESC LIMIT 1
        """, (skill_name,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def record_ab_outcome(
        self,
        test_id: str,
        variant: str,
        success: bool
    ) -> None:
        """
        Record outcome for A/B test variant.

        Args:
            test_id: A/B test identifier
            variant: 'control' or 'treatment'
            success: Whether execution met fidelity threshold
        """
        cursor = self.conn.cursor()
        if variant == 'control':
            cursor.execute("""
                UPDATE ab_test_assignments
                SET control_trials = control_trials + 1,
                    control_successes = control_successes + ?
                WHERE test_id = ?
            """, (1 if success else 0, test_id))
        else:
            cursor.execute("""
                UPDATE ab_test_assignments
                SET treatment_trials = treatment_trials + 1,
                    treatment_successes = treatment_successes + ?
                WHERE test_id = ?
            """, (1 if success else 0, test_id))
        self.conn.commit()

    def check_ab_promotion(self, test_id: str, min_margin: float = 0.10) -> Optional[str]:
        """
        Check if treatment should be promoted.

        Args:
            test_id: A/B test identifier
            min_margin: Minimum win margin (default 10%)

        Returns:
            'treatment' if should promote, 'control' if treatment lost, None if inconclusive
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ab_test_assignments WHERE test_id = ?", (test_id,))
        row = cursor.fetchone()
        if not row:
            return None

        test = dict(row)
        total_trials = test['control_trials'] + test['treatment_trials']

        if total_trials < test['sample_size_target']:
            return None

        control_rate = test['control_successes'] / max(test['control_trials'], 1)
        treatment_rate = test['treatment_successes'] / max(test['treatment_trials'], 1)

        margin = treatment_rate - control_rate

        if margin >= min_margin:
            return 'treatment'
        elif margin <= -min_margin:
            return 'control'
        return None

    def promote_variation(self, variation_id: str) -> None:
        """Promote variation to production."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE skill_variations
            SET promoted = 1, test_status = 'promoted'
            WHERE variation_id = ?
        """, (variation_id,))
        self.conn.commit()
        logger.info(f"[PATTERN-MEMORY] Promoted variation {variation_id}")

    def archive_variation(self, variation_id: str) -> None:
        """Archive losing variation."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE skill_variations
            SET test_status = 'archived'
            WHERE variation_id = ?
        """, (variation_id,))
        self.conn.commit()
        logger.info(f"[PATTERN-MEMORY] Archived variation {variation_id}")

    def close_ab_test(self, test_id: str, winner: str) -> None:
        """Close A/B test with winner."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE ab_test_assignments
            SET status = 'completed', end_time = ?
            WHERE test_id = ?
        """, (datetime.now().isoformat(), test_id))
        self.conn.commit()
        logger.info(f"[PATTERN-MEMORY] Closed A/B test {test_id}, winner={winner}")

    # ------------------------------------------------------------------ #
    #  Telemetry Counters (Sprint 1 - Observability)                     #
    # ------------------------------------------------------------------ #

    def increment_counter(self, counter_name: str, delta: int = 1) -> int:
        """
        Increment telemetry counter and return new value.

        Per WRE_COT_DEEP_ANALYSIS.md: Track retry_count, variation_win_rate
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO telemetry_counters (counter_name, counter_value, last_updated)
            VALUES (?, ?, ?)
            ON CONFLICT(counter_name) DO UPDATE SET
                counter_value = counter_value + ?,
                last_updated = ?
        """, (
            counter_name, delta, datetime.now().isoformat(),
            delta, datetime.now().isoformat()
        ))
        self.conn.commit()

        cursor.execute(
            "SELECT counter_value FROM telemetry_counters WHERE counter_name = ?",
            (counter_name,)
        )
        row = cursor.fetchone()
        return row['counter_value'] if row else delta

    def get_counter(self, counter_name: str) -> int:
        """Get current counter value."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT counter_value FROM telemetry_counters WHERE counter_name = ?",
            (counter_name,)
        )
        row = cursor.fetchone()
        return row['counter_value'] if row else 0

    def get_telemetry_dashboard(self) -> Dict:
        """
        Get telemetry dashboard for Sprint 1 metrics.

        Returns:
            Dict with retry_count, variation_win_rate, avg_fidelity_delta
        """
        cursor = self.conn.cursor()

        cursor.execute("SELECT * FROM telemetry_counters")
        counters = {row['counter_name']: row['counter_value'] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN promoted = 1 THEN 1 ELSE 0 END) as promoted
            FROM skill_variations
            WHERE test_status IN ('promoted', 'archived')
        """)
        row = cursor.fetchone()
        total_tested = row['total'] or 0
        promoted = row['promoted'] or 0
        win_rate = promoted / max(total_tested, 1)

        cursor.execute("""
            SELECT AVG(after_fidelity - before_fidelity) as avg_delta
            FROM learning_events
            WHERE event_type = 'variation_promoted'
              AND before_fidelity IS NOT NULL
              AND after_fidelity IS NOT NULL
        """)
        row = cursor.fetchone()
        avg_delta = row['avg_delta'] or 0

        # Sprint 2: Retrieval metrics
        cursor.execute("""
            SELECT
                COUNT(*) as total_retrievals,
                AVG(relevance_score) as avg_relevance,
                SUM(CASE WHEN relevance_score >= 0.5 THEN 1 ELSE 0 END) as high_relevance_count
            FROM retrieval_quality
        """)
        ret_row = cursor.fetchone()
        retrieval_total = ret_row['total_retrievals'] or 0
        high_relevance = ret_row['high_relevance_count'] or 0
        retrieval_coverage = high_relevance / max(retrieval_total, 1)

        # Sprint 2: Graph metrics
        cursor.execute("SELECT COUNT(*) as edge_count FROM skill_edges")
        edge_count = cursor.fetchone()['edge_count'] or 0

        cursor.execute("""
            SELECT COUNT(DISTINCT source_skill) as connected_skills
            FROM skill_edges
        """)
        connected_skills = cursor.fetchone()['connected_skills'] or 0

        # Sprint 3: ToT and CodeAct metrics
        tot_selections = counters.get("tot_selections", 0)
        tot_high_confidence = counters.get("tot_high_confidence", 0)
        tot_branch_count = counters.get("tot_branch_count", 0)
        tot_confidence_rate = tot_high_confidence / max(tot_selections, 1)
        tot_avg_branches = tot_branch_count / max(tot_selections, 1)

        codeact_success = counters.get("codeact_exec_success", 0)
        codeact_fail = counters.get("codeact_exec_fail", 0)
        codeact_total = codeact_success + codeact_fail
        codeact_success_rate = codeact_success / max(codeact_total, 1)
        codeact_gate_triggers = counters.get("codeact_gate_triggers", 0)

        return {
            # Sprint 1
            "retry_count": counters.get("react_retry_count", 0),
            "total_executions": counters.get("total_executions", 0),
            "variation_win_rate": round(win_rate, 3),
            "avg_fidelity_delta": round(avg_delta, 3),
            "variations_tested": total_tested,
            "variations_promoted": promoted,
            # Sprint 2
            "retrieval_coverage": round(retrieval_coverage, 3),
            "avg_retrieval_relevance": round(ret_row['avg_relevance'] or 0, 3),
            "total_retrievals": retrieval_total,
            "skill_edges": edge_count,
            "connected_skills": connected_skills,
            # Sprint 3
            "tot_selections": tot_selections,
            "tot_confidence_rate": round(tot_confidence_rate, 3),
            "tot_avg_branches": round(tot_avg_branches, 1),
            "codeact_executions": codeact_total,
            "codeact_success_rate": round(codeact_success_rate, 3),
            "codeact_gate_triggers": codeact_gate_triggers
        }

    # ------------------------------------------------------------------ #
    #  Retrieval Quality Tracking (Sprint 2 - Agentic RAG)               #
    # ------------------------------------------------------------------ #

    def record_retrieval(
        self,
        retrieval_id: str,
        execution_id: str,
        skill_name: str,
        query: str,
        results_count: int,
        relevance_score: float,
        retrieval_time_ms: int
    ) -> None:
        """Record retrieval event for quality tracking."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO retrieval_quality (
                retrieval_id, execution_id, skill_name, query,
                timestamp, results_count, relevance_score, retrieval_time_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            retrieval_id, execution_id, skill_name, query,
            datetime.now().isoformat(), results_count, relevance_score, retrieval_time_ms
        ))
        self.conn.commit()
        logger.debug(f"[PATTERN-MEMORY] Recorded retrieval {retrieval_id}")

    def get_retrieval_stats(self, skill_name: str, days: int = 7) -> Dict:
        """Get retrieval quality stats for a skill."""
        cursor = self.conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT
                COUNT(*) as total_retrievals,
                AVG(relevance_score) as avg_relevance,
                AVG(results_count) as avg_results,
                AVG(retrieval_time_ms) as avg_time_ms
            FROM retrieval_quality
            WHERE skill_name = ? AND timestamp >= ?
        """, (skill_name, cutoff))
        row = cursor.fetchone()
        return dict(row) if row else {}

    # ------------------------------------------------------------------ #
    #  Graph-of-Thought Edges (Sprint 2 - Cross-Skill Transfer)          #
    # ------------------------------------------------------------------ #

    def add_skill_edge(
        self,
        source_skill: str,
        target_skill: str,
        edge_type: str,
        weight: float = 1.0,
        evidence: Optional[str] = None
    ) -> str:
        """
        Add edge between skills for knowledge transfer.

        Edge types:
        - caused_by: source caused target to fail/succeed
        - improved_by: source improvement helped target
        - similar_to: skills share patterns
        - depends_on: source depends on target
        """
        import uuid
        edge_id = f"edge_{uuid.uuid4().hex[:8]}"
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO skill_edges (
                edge_id, source_skill, target_skill, edge_type,
                weight, created_at, evidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            edge_id, source_skill, target_skill, edge_type,
            weight, datetime.now().isoformat(), evidence
        ))
        self.conn.commit()
        logger.info(
            f"[PATTERN-MEMORY] Added edge {source_skill} --{edge_type}--> {target_skill}"
        )
        return edge_id

    def get_related_skills(
        self,
        skill_name: str,
        edge_types: Optional[List[str]] = None,
        min_weight: float = 0.5
    ) -> List[Dict]:
        """Get skills related to source skill via edges."""
        cursor = self.conn.cursor()

        if edge_types:
            placeholders = ",".join(["?"] * len(edge_types))
            cursor.execute(f"""
                SELECT * FROM skill_edges
                WHERE source_skill = ?
                  AND edge_type IN ({placeholders})
                  AND weight >= ?
                ORDER BY weight DESC
            """, (skill_name, *edge_types, min_weight))
        else:
            cursor.execute("""
                SELECT * FROM skill_edges
                WHERE source_skill = ?
                  AND weight >= ?
                ORDER BY weight DESC
            """, (skill_name, min_weight))

        return [dict(row) for row in cursor.fetchall()]

    def get_skill_graph(self, skill_name: str, depth: int = 2) -> Dict:
        """
        Get skill subgraph centered on skill_name.

        Returns nodes and edges for visualization/analysis.
        """
        visited = set()
        nodes = []
        edges = []

        def traverse(skill: str, current_depth: int):
            if skill in visited or current_depth > depth:
                return
            visited.add(skill)
            nodes.append({"id": skill, "depth": current_depth})

            related = self.get_related_skills(skill)
            for rel in related:
                edges.append({
                    "source": rel["source_skill"],
                    "target": rel["target_skill"],
                    "type": rel["edge_type"],
                    "weight": rel["weight"]
                })
                traverse(rel["target_skill"], current_depth + 1)

        traverse(skill_name, 0)
        return {"nodes": nodes, "edges": edges}

    def transfer_learning(
        self,
        source_skill: str,
        target_skill: str
    ) -> Optional[Dict]:
        """
        Transfer successful patterns from source to target skill.

        Returns transferred pattern info or None if no transferable patterns.
        """
        source_successes = self.recall_successful_patterns(source_skill, min_fidelity=0.90, limit=3)

        if not source_successes:
            return None

        edges = self.get_related_skills(source_skill, edge_types=["similar_to", "improved_by"])
        target_related = any(e["target_skill"] == target_skill for e in edges)

        if not target_related:
            self.add_skill_edge(
                source_skill=source_skill,
                target_skill=target_skill,
                edge_type="similar_to",
                weight=0.5,
                evidence="Auto-detected during transfer_learning"
            )

        return {
            "source_skill": source_skill,
            "target_skill": target_skill,
            "patterns_transferred": len(source_successes),
            "best_source_fidelity": source_successes[0]["pattern_fidelity"]
        }

    # ------------------------------------------------------------------ #
    #  Tree-of-Thought Skill Scoring (Sprint 3 - Gap B)                   #
    # ------------------------------------------------------------------ #

    def get_skill_fidelity_stats(self, skill_name: str, days: int = 30) -> Dict:
        """
        Get historical fidelity statistics for a skill.

        Per WRE_COT_DEEP_ANALYSIS.md Gap B: ToT skill selection

        Returns:
            {
                "skill_name": str,
                "total_executions": int,
                "avg_fidelity": float,
                "success_rate": float,  # fidelity >= 0.7
                "recent_trend": float   # last 7 days vs previous
            }
        """
        cursor = self.conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        recent_cutoff = (datetime.now() - timedelta(days=7)).isoformat()

        # Overall stats
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                AVG(pattern_fidelity) as avg_fidelity,
                SUM(CASE WHEN pattern_fidelity >= 0.7 THEN 1 ELSE 0 END) as successes
            FROM skill_outcomes
            WHERE skill_name = ? AND timestamp >= ?
        """, (skill_name, cutoff))
        row = cursor.fetchone()

        total = row['total'] or 0
        avg_fidelity = row['avg_fidelity'] or 0.5
        success_rate = (row['successes'] or 0) / max(total, 1)

        # Recent trend (last 7 days vs previous)
        cursor.execute("""
            SELECT AVG(pattern_fidelity) as recent_avg
            FROM skill_outcomes
            WHERE skill_name = ? AND timestamp >= ?
        """, (skill_name, recent_cutoff))
        recent_avg = cursor.fetchone()['recent_avg'] or avg_fidelity

        cursor.execute("""
            SELECT AVG(pattern_fidelity) as older_avg
            FROM skill_outcomes
            WHERE skill_name = ? AND timestamp >= ? AND timestamp < ?
        """, (skill_name, cutoff, recent_cutoff))
        older_avg = cursor.fetchone()['older_avg'] or avg_fidelity

        recent_trend = recent_avg - older_avg

        return {
            "skill_name": skill_name,
            "total_executions": total,
            "avg_fidelity": round(avg_fidelity, 3),
            "success_rate": round(success_rate, 3),
            "recent_trend": round(recent_trend, 3)
        }

    def rank_skills_for_context(
        self,
        candidate_skills: List[str],
        context_keywords: List[str]
    ) -> List[Dict]:
        """
        Rank candidate skills by historical fidelity and context match.

        Per WRE_COT_DEEP_ANALYSIS.md Gap B: ToT skill selection

        ToT scoring formula:
            score = (0.6 * avg_fidelity) + (0.2 * success_rate) + (0.1 * trend_bonus) + (0.1 * context_match)

        Returns sorted list of {skill_name, score, components, total_executions}
        """
        scored = []

        for skill in candidate_skills:
            stats = self.get_skill_fidelity_stats(skill)

            # Context match: check if skill name contains context keywords
            context_match = sum(
                1 for kw in context_keywords
                if kw.lower() in skill.lower()
            ) / max(len(context_keywords), 1)

            # Trend bonus: positive trend = bonus, negative = penalty
            trend_bonus = max(0, min(1, 0.5 + stats['recent_trend']))

            # ToT score
            score = (
                0.6 * stats['avg_fidelity'] +
                0.2 * stats['success_rate'] +
                0.1 * trend_bonus +
                0.1 * context_match
            )

            scored.append({
                "skill_name": skill,
                "score": round(score, 3),
                "components": {
                    "fidelity": stats['avg_fidelity'],
                    "success_rate": stats['success_rate'],
                    "trend_bonus": round(trend_bonus, 3),
                    "context_match": round(context_match, 3)
                },
                "total_executions": stats['total_executions']
            })

        # Sort by score descending
        scored.sort(key=lambda x: x['score'], reverse=True)
        logger.debug(f"[PATTERN-MEMORY] Ranked {len(scored)} skills for ToT selection")
        return scored

    def close(self) -> None:
        """Close database connection"""
        self.conn.close()
        if getattr(self, "_uses_shared_singleton", False):
            PatternMemory._initialized = False
            PatternMemory._shared_state = {}
        logger.debug("[PATTERN-MEMORY] Connection closed")


# Example usage
if __name__ == "__main__":
    from datetime import timedelta
    import uuid

    logging.basicConfig(level=logging.INFO)

    # Initialize pattern memory
    memory = PatternMemory()

    print("[EXAMPLE 1] Store skill execution outcome:")
    outcome = SkillOutcome(
        execution_id=str(uuid.uuid4()),
        skill_name="qwen_gitpush",
        agent="qwen",
        timestamp=datetime.now().isoformat(),
        input_context=json.dumps({"files_changed": 14, "lines_added": 250}),
        output_result=json.dumps({"action": "push_now", "mps_score": 14}),
        success=True,
        pattern_fidelity=0.92,
        outcome_quality=0.95,
        execution_time_ms=1200,
        step_count=4,
        notes="Successful git push with P1 priority"
    )
    memory.store_outcome(outcome)
    print(f"  Stored: exec_id={outcome.execution_id[:8]}...")

    print("\n[EXAMPLE 2] Recall successful patterns:")
    patterns = memory.recall_successful_patterns("qwen_gitpush", min_fidelity=0.90, limit=5)
    print(f"  Recalled {len(patterns)} successful patterns")
    if patterns:
        print(f"  Best fidelity: {patterns[0]['pattern_fidelity']:.2f}")

    print("\n[EXAMPLE 3] Get skill metrics:")
    metrics = memory.get_skill_metrics("qwen_gitpush", days=7)
    print(f"  Executions: {metrics['execution_count']}")
    print(f"  Avg fidelity: {metrics['avg_fidelity']:.2f}")
    print(f"  Success rate: {metrics['success_rate']:.1%}")

    print("\n[EXAMPLE 4] Store variation for A/B testing:")
    memory.store_variation(
        variation_id="qwen_gitpush_v1.1_improved",
        skill_name="qwen_gitpush",
        variation_content="# Improved version with better MPS calculation",
        parent_version="v1.0_baseline",
        created_by="qwen"
    )
    print("  Variation stored for A/B testing")

    print("\n[EXAMPLE 5] Record learning event:")
    memory.record_learning_event(
        event_id=str(uuid.uuid4()),
        skill_name="qwen_gitpush",
        event_type="variation_promoted",
        description="Promoted v1.1 after 65% → 78% fidelity improvement",
        before_fidelity=0.65,
        after_fidelity=0.78,
        variation_id="qwen_gitpush_v1.1_improved"
    )
    print("  Learning event recorded")

    memory.close()

    print("\n[OK] Pattern Memory ready - recursive learning enabled")
