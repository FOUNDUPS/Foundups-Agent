#!/usr/bin/env python3
"""
WRE Skills Metrics Ingestion v2
FIXED: Separate tables for fidelity/outcome/performance to prevent field overwrites
WSP Compliance: WSP 77 (Agent Coordination), WSP 91 (DAEMON Observability)
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import argparse

logger = logging.getLogger(__name__)


class MetricsIngestorV2:
    """
    Batch ingestion engine for WRE skills metrics (v2 - FIXED)

    CRITICAL FIX: Uses separate tables for each metric type to prevent
    INSERT OR REPLACE from overwriting fields.

    Reads newline-delimited JSON files and ingests into SQLite for analytics.
    Tracks ingestion watermarks to avoid duplicate processing.
    """

    def __init__(self, sqlite_path: Optional[Path] = None, json_dir: Optional[Path] = None):
        """
        Initialize metrics ingestor

        Args:
            sqlite_path: Path to SQLite database (defaults to skills/skills_metrics.db)
            json_dir: Directory containing JSON metrics files (defaults to recursive_improvement/metrics/)
        """
        if sqlite_path is None:
            self.sqlite_path = Path(__file__).parent / "skills_metrics.db"
        else:
            self.sqlite_path = Path(sqlite_path)

        if json_dir is None:
            self.json_dir = Path(__file__).parent.parent / "recursive_improvement" / "metrics"
        else:
            self.json_dir = Path(json_dir)

        self.conn = None
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create SQLite schema if it doesn't exist"""
        self.conn = sqlite3.connect(str(self.sqlite_path))
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Skills registry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                skill_id TEXT PRIMARY KEY,
                skill_name TEXT NOT NULL,
                promotion_state TEXT NOT NULL,
                primary_agent TEXT NOT NULL,
                intent_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_promoted_at TIMESTAMP,
                version TEXT DEFAULT '1.0'
            )
        """)

        # FIXED: Separate tables for each metric type
        # Pattern fidelity metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fidelity_metrics (
                execution_id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                pattern_fidelity REAL NOT NULL,
                patterns_followed INTEGER NOT NULL,
                patterns_missed INTEGER NOT NULL,
                agent TEXT NOT NULL,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
            )
        """)

        # Outcome quality metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outcome_metrics (
                execution_id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                decision TEXT NOT NULL,
                expected_decision TEXT,
                correct BOOLEAN NOT NULL,
                confidence REAL,
                reasoning TEXT,
                agent TEXT NOT NULL,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
            )
        """)

        # Performance metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                execution_id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                execution_time_ms INTEGER NOT NULL,
                exception BOOLEAN NOT NULL,
                exception_type TEXT,
                memory_usage_mb REAL,
                agent TEXT NOT NULL,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
            )
        """)

        # Promotion events
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS promotion_events (
                event_id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                from_state TEXT NOT NULL,
                to_state TEXT NOT NULL,
                approver TEXT,
                approval_ticket TEXT,
                timestamp TIMESTAMP NOT NULL,
                reason TEXT,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
            )
        """)

        # Rollback events
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rollback_events (
                event_id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                from_state TEXT NOT NULL,
                to_state TEXT NOT NULL,
                trigger_reason TEXT NOT NULL,
                trigger_metric TEXT,
                timestamp TIMESTAMP NOT NULL,
                automated BOOLEAN,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
            )
        """)

        # 0102 (AI supervisor) approvals (NEW - WSP 50 tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_0102_approvals (
                approval_id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                promotion_path TEXT NOT NULL,
                approver TEXT NOT NULL,  -- "0102" (AI supervisor)
                approval_ticket TEXT NOT NULL,

                -- WSP 50 Pre-Action Verification
                wsp_50_no_duplication BOOLEAN NOT NULL,
                wsp_50_evidence TEXT,

                -- Test coverage
                test_coverage_complete BOOLEAN NOT NULL,
                test_evidence TEXT,

                -- Instruction clarity
                instruction_clarity_approved BOOLEAN NOT NULL,

                -- Dependencies validated
                dependencies_validated BOOLEAN NOT NULL,
                dependency_evidence TEXT,

                -- Security review
                security_reviewed BOOLEAN NOT NULL,
                security_notes TEXT,

                -- Production-specific (nullable for prototype->staged)
                production_readiness BOOLEAN,
                integration_approved BOOLEAN,
                monitoring_configured BOOLEAN,
                rollback_tested BOOLEAN,
                documentation_updated BOOLEAN,

                approval_timestamp TIMESTAMP NOT NULL,
                notes TEXT,

                FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
            )
        """)

        # Ingestion watermarks (track what's been ingested)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_watermarks (
                file_name TEXT PRIMARY KEY,
                last_ingested_line INTEGER DEFAULT 0,
                last_ingested_timestamp REAL,
                last_ingestion_run TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indexes for query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fidelity_skill ON fidelity_metrics(skill_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fidelity_timestamp ON fidelity_metrics(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcome_skill ON outcome_metrics(skill_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcome_timestamp ON outcome_metrics(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_skill ON performance_metrics(skill_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_metrics(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_promotion_skill ON promotion_events(skill_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rollback_skill ON rollback_events(skill_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_approval_skill ON ai_0102_approvals(skill_id)")

        self.conn.commit()
        logger.info(f"[METRICS-DB-V2] Schema ensured: {self.sqlite_path}")

    def ingest_all(self, batch_size: int = 1000) -> Dict[str, int]:
        """
        Ingest all new metrics from JSON files

        Args:
            batch_size: Number of records to ingest per transaction

        Returns:
            Dict with ingestion counts per metric type
        """
        stats = {
            "fidelity": 0,
            "outcomes": 0,
            "performance": 0,
            "promotions": 0,
            "rollbacks": 0
        }

        # Ingest fidelity metrics
        for filepath in self.json_dir.glob("*_fidelity.json"):
            count = self._ingest_file(filepath, "fidelity", batch_size)
            stats["fidelity"] += count

        # Ingest outcome metrics
        for filepath in self.json_dir.glob("*_outcomes.json"):
            count = self._ingest_file(filepath, "outcomes", batch_size)
            stats["outcomes"] += count

        # Ingest performance metrics
        for filepath in self.json_dir.glob("*_performance.json"):
            count = self._ingest_file(filepath, "performance", batch_size)
            stats["performance"] += count

        # Ingest promotion/rollback events
        for filepath in self.json_dir.glob("*_promotion_log.json"):
            count = self._ingest_file(filepath, "promotion_log", batch_size)
            stats["promotions"] += count  # Both in same file, approximation
            stats["rollbacks"] += 0

        logger.info(f"[METRICS-INGEST-V2] Ingestion complete: {stats}")
        return stats

    def _ingest_file(self, filepath: Path, metric_type: str, batch_size: int) -> int:
        """
        Ingest metrics from a single JSON file

        Args:
            filepath: Path to JSON metrics file
            metric_type: Type of metrics (fidelity, outcomes, performance, promotion_log)
            batch_size: Batch size for transactions

        Returns:
            Number of records ingested
        """
        if not filepath.exists():
            return 0

        filename = filepath.name

        # Get watermark (last ingested line)
        cursor = self.conn.cursor()
        cursor.execute("SELECT last_ingested_line FROM ingestion_watermarks WHERE file_name = ?", (filename,))
        row = cursor.fetchone()
        watermark = row[0] if row else 0

        # Read new lines only
        new_metrics = []
        current_line = 0

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    current_line += 1
                    if current_line <= watermark:
                        continue  # Skip already ingested

                    if line.strip():
                        try:
                            metric = json.loads(line)
                            new_metrics.append((current_line, metric))
                        except json.JSONDecodeError as e:
                            logger.warning(f"[METRICS-INGEST-V2] Malformed JSON in {filename} line {current_line}: {e}")
        except Exception as e:
            logger.error(f"[METRICS-INGEST-V2] Failed to read {filename}: {e}")
            return 0

        if not new_metrics:
            return 0

        # Batch ingest
        ingested_count = 0
        for i in range(0, len(new_metrics), batch_size):
            batch = new_metrics[i:i + batch_size]
            self._ingest_batch(batch, metric_type)
            ingested_count += len(batch)

        # Update watermark
        last_line = new_metrics[-1][0]
        cursor.execute("""
            INSERT OR REPLACE INTO ingestion_watermarks (file_name, last_ingested_line, last_ingested_timestamp, last_ingestion_run)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (filename, last_line, time.time()))
        self.conn.commit()

        logger.info(f"[METRICS-INGEST-V2] Ingested {ingested_count} records from {filename}")
        return ingested_count

    def _ingest_batch(self, batch: List[tuple], metric_type: str) -> None:
        """
        Ingest a batch of metrics into SQLite

        Args:
            batch: List of (line_number, metric_dict) tuples
            metric_type: Type of metrics
        """
        cursor = self.conn.cursor()

        for _, metric in batch:
            try:
                if metric_type == "fidelity":
                    self._ingest_fidelity_metric(cursor, metric)
                elif metric_type == "outcomes":
                    self._ingest_outcome_metric(cursor, metric)
                elif metric_type == "performance":
                    self._ingest_performance_metric(cursor, metric)
                elif metric_type == "promotion_log":
                    if metric.get("event_type") == "promotion":
                        self._ingest_promotion_event(cursor, metric)
                    elif metric.get("event_type") == "rollback":
                        self._ingest_rollback_event(cursor, metric)
            except Exception as e:
                logger.warning(f"[METRICS-INGEST-V2] Failed to ingest metric: {e}")
                # Continue with next metric

        self.conn.commit()

    def _ingest_fidelity_metric(self, cursor, metric: Dict) -> None:
        """Ingest fidelity metric into dedicated table"""
        cursor.execute("""
            INSERT OR REPLACE INTO fidelity_metrics (
                execution_id, skill_id, timestamp, pattern_fidelity,
                patterns_followed, patterns_missed, agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            metric["execution_id"],
            metric["skill_name"],
            metric["timestamp"],
            metric["pattern_fidelity"],
            metric["patterns_followed"],
            metric["patterns_missed"],
            metric["agent"]
        ))

    def _ingest_outcome_metric(self, cursor, metric: Dict) -> None:
        """Ingest outcome metric into dedicated table"""
        cursor.execute("""
            INSERT OR REPLACE INTO outcome_metrics (
                execution_id, skill_id, timestamp, decision, expected_decision,
                correct, confidence, reasoning, agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metric["execution_id"],
            metric["skill_name"],
            metric["timestamp"],
            metric["decision"],
            metric.get("expected_decision"),
            metric["correct"],
            metric["confidence"],
            metric["reasoning"],
            metric["agent"]
        ))

    def _ingest_performance_metric(self, cursor, metric: Dict) -> None:
        """Ingest performance metric into dedicated table"""
        cursor.execute("""
            INSERT OR REPLACE INTO performance_metrics (
                execution_id, skill_id, timestamp, execution_time_ms,
                exception, exception_type, memory_usage_mb, agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metric["execution_id"],
            metric["skill_name"],
            metric["timestamp"],
            metric["execution_time_ms"],
            metric["exception_occurred"],
            metric.get("exception_type"),
            metric.get("memory_usage_mb"),
            metric["agent"]
        ))

    def _ingest_promotion_event(self, cursor, event: Dict) -> None:
        """Ingest promotion event"""
        cursor.execute("""
            INSERT OR REPLACE INTO promotion_events (
                event_id, skill_id, from_state, to_state, approver,
                approval_ticket, timestamp, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event["event_id"],
            event["skill_name"],
            event["from_state"],
            event["to_state"],
            event["approver"],
            event["approval_ticket"],
            event["timestamp"],
            event["reason"]
        ))

    def _ingest_rollback_event(self, cursor, event: Dict) -> None:
        """Ingest rollback event"""
        cursor.execute("""
            INSERT OR REPLACE INTO rollback_events (
                event_id, skill_id, from_state, to_state, trigger_reason,
                trigger_metric, timestamp, automated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event["event_id"],
            event["skill_name"],
            event["from_state"],
            event["to_state"],
            event["trigger_reason"],
            event["trigger_metric"],
            event["timestamp"],
            event["automated"]
        ))

    def close(self) -> None:
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """CLI entry point for metrics ingestion"""
    parser = argparse.ArgumentParser(description="Ingest WRE skills metrics from JSON to SQLite (v2 - FIXED)")
    parser.add_argument("--json-path", type=str, help="Path to JSON metrics directory")
    parser.add_argument("--sqlite-db", type=str, help="Path to SQLite database")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for ingestion")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

    # Initialize ingestor
    ingestor = MetricsIngestorV2(
        sqlite_path=Path(args.sqlite_db) if args.sqlite_db else None,
        json_dir=Path(args.json_path) if args.json_path else None
    )

    # Run ingestion
    start_time = time.time()
    stats = ingestor.ingest_all(batch_size=args.batch_size)
    elapsed = time.time() - start_time

    print(f"\n[OK] Ingestion complete in {elapsed:.2f}s")
    print(f"  Fidelity metrics: {stats['fidelity']}")
    print(f"  Outcome metrics: {stats['outcomes']}")
    print(f"  Performance metrics: {stats['performance']}")
    print(f"  Promotion events: {stats['promotions']}")
    print(f"  Rollback events: {stats['rollbacks']}")
    print(f"  Total: {sum(stats.values())}")

    ingestor.close()


if __name__ == "__main__":
    main()
