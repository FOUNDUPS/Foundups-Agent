#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for AgentDB schema compatibility migrations."""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path

from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager


def _reset_database(db_path: Path) -> None:
    DatabaseManager.reset_for_tests()
    DatabaseManager._db_path = str(db_path)


def test_agent_db_migrates_legacy_autonomous_task_schema() -> None:
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "legacy_foundups.db"
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE agents_autonomous_tasks (
                task_id TEXT PRIMARY KEY,
                description TEXT,
                required_skills JSON,
                estimated_complexity REAL,
                priority_score REAL,
                discovered_by TEXT DEFAULT 'autonomous_discovery',
                discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                context JSON,
                assigned_to TEXT,
                assigned_at DATETIME
            )
            """
        )
        conn.execute(
            """
            INSERT INTO agents_autonomous_tasks (
                task_id, description, required_skills, estimated_complexity, priority_score
            ) VALUES ('legacy-task', 'legacy description', '[]', 0.1, 0.5)
            """
        )
        conn.commit()
        conn.close()

        _reset_database(db_path)
        agent_db = AgentDB()

        columns = {row["name"] for row in agent_db.db.get_table_info("agents_autonomous_tasks")}
        assert "status" in columns
        assert "completed_at" in columns

        tasks = agent_db.get_autonomous_tasks()
        assert len(tasks) == 1
        assert tasks[0]["task_id"] == "legacy-task"
        assert tasks[0]["status"] == "pending"

        assert agent_db.assign_autonomous_task("legacy-task", "0102")
        assigned_rows = agent_db.db.execute_query(
            "SELECT status, assigned_to FROM agents_autonomous_tasks WHERE task_id = ?",
            ("legacy-task",),
        )
        assert assigned_rows[0]["status"] == "assigned"
        assert assigned_rows[0]["assigned_to"] == "0102"

        assert agent_db.complete_autonomous_task("legacy-task")
        completed_rows = agent_db.db.execute_query(
            "SELECT status, completed_at FROM agents_autonomous_tasks WHERE task_id = ?",
            ("legacy-task",),
        )
        assert completed_rows[0]["status"] == "completed"
        assert completed_rows[0]["completed_at"] is not None
    finally:
        DatabaseManager.reset_for_tests()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_agent_db_returns_recent_breadcrumb_agents() -> None:
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "breadcrumbs_foundups.db"
    try:
        _reset_database(db_path)
        agent_db = AgentDB()
        agent_db.add_breadcrumb(session_id="session-a", action="search", agent_id="0102")
        agent_db.add_breadcrumb(session_id="session-b", action="search", agent_id="0201")

        recent_agents = agent_db.get_recent_breadcrumb_agents(minutes=60, limit=10)

        assert "0102" in recent_agents
        assert "0201" in recent_agents
    finally:
        DatabaseManager.reset_for_tests()
        shutil.rmtree(temp_dir, ignore_errors=True)
