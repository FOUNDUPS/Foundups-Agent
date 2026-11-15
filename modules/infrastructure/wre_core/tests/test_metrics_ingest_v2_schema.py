"""Regression tests for MetricsIngestorV2 schema and rollback triggers."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.infrastructure.wre_core.skillz.metrics_ingest_v2 import MetricsIngestorV2
from modules.infrastructure.wre_core.skillz.skills_registry_v2 import WRESkillsRegistryV2


def test_metrics_ingest_v2_initializes_ai_0102_approvals_index(tmp_path: Path) -> None:
    db_path = tmp_path / "wre_metrics.db"
    json_dir = tmp_path / "metrics_json"
    json_dir.mkdir()

    ingestor = MetricsIngestorV2(sqlite_path=db_path, json_dir=json_dir)
    try:
        assert ingestor.conn is not None
        row = ingestor.conn.execute(
            "SELECT name, tbl_name FROM sqlite_master "
            "WHERE type='index' AND name='idx_approval_skill'"
        ).fetchone()
        assert row is not None
        assert row["name"] == "idx_approval_skill"
        assert row["tbl_name"] == "ai_0102_approvals"
    finally:
        ingestor.close()


def test_check_rollback_triggers_healthy_fidelity_drop_and_exceptions(tmp_path: Path) -> None:
    db_path = tmp_path / "wre_rollback.db"
    json_dir = tmp_path / "metrics_json"
    json_dir.mkdir()

    ingestor = MetricsIngestorV2(sqlite_path=db_path, json_dir=json_dir)
    conn = ingestor.conn
    assert conn is not None
    try:
        conn.execute(
            "INSERT INTO skills (skill_id, skill_name, promotion_state, primary_agent, intent_type) "
            "VALUES (?, ?, 'production', 'qwen', 'CLASSIFICATION')",
            ("canary_healthy", "canary_healthy"),
        )
        conn.execute(
            "INSERT INTO skills (skill_id, skill_name, promotion_state, primary_agent, intent_type) "
            "VALUES (?, ?, 'production', 'qwen', 'CLASSIFICATION')",
            ("canary_exc", "canary_exc"),
        )
        t0 = datetime(2026, 11, 15, 0, 0, 0, tzinfo=timezone.utc)
        for i in range(10):
            ts = (t0 + timedelta(seconds=i)).isoformat()
            conn.execute(
                "INSERT INTO fidelity_metrics "
                "(execution_id, skill_id, timestamp, pattern_fidelity, patterns_followed, patterns_missed, agent) "
                "VALUES (?, 'canary_healthy', ?, 0.94, 9, 1, 'qwen')",
                (f"healthy_fid_{i}", ts),
            )
            conn.execute(
                "INSERT INTO fidelity_metrics "
                "(execution_id, skill_id, timestamp, pattern_fidelity, patterns_followed, patterns_missed, agent) "
                "VALUES (?, 'canary_exc', ?, 0.95, 9, 1, 'qwen')",
                (f"exc_fid_{i}", ts),
            )
        for i in range(20):
            ts = (t0 + timedelta(seconds=i)).isoformat()
            conn.execute(
                "INSERT INTO performance_metrics "
                "(execution_id, skill_id, timestamp, execution_time_ms, exception, exception_type, memory_usage_mb, agent) "
                "VALUES (?, 'canary_healthy', ?, 100, 0, NULL, 12.0, 'qwen')",
                (f"healthy_perf_{i}", ts),
            )
            is_exc = 1 if i < 2 else 0
            conn.execute(
                "INSERT INTO performance_metrics "
                "(execution_id, skill_id, timestamp, execution_time_ms, exception, exception_type, memory_usage_mb, agent) "
                "VALUES (?, 'canary_exc', ?, 110, ?, ?, 12.0, 'qwen')",
                (f"exc_perf_{i}", ts, is_exc, "RuntimeError" if is_exc else None),
            )
        conn.commit()
    finally:
        ingestor.close()

    registry = WRESkillsRegistryV2(sqlite_path=db_path)
    try:
        healthy = registry.check_rollback_triggers("canary_healthy")
        assert healthy["should_rollback"] is False

        with sqlite3.connect(db_path) as upd:
            for i in range(10):
                ts = (t0 + timedelta(seconds=100 + i)).isoformat()
                upd.execute(
                    "INSERT INTO fidelity_metrics "
                    "(execution_id, skill_id, timestamp, pattern_fidelity, patterns_followed, patterns_missed, agent) "
                    "VALUES (?, 'canary_healthy', ?, 0.72, 7, 3, 'qwen')",
                    (f"degraded_fid_{i}", ts),
                )
            upd.commit()

        degraded = registry.check_rollback_triggers("canary_healthy")
        assert degraded["should_rollback"] is True
        assert degraded["trigger"] == "pattern_fidelity_drop"

        exc_result = registry.check_rollback_triggers("canary_exc")
        assert exc_result["should_rollback"] is True
        assert exc_result["trigger"] == "high_exception_rate"
    finally:
        if registry.conn:
            registry.conn.close()
