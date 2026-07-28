"""Regressions for the signed-worker task namespace boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager
from modules.infrastructure.database.src.signed_worker_execution_store import (
    SIGNED_WORKER_TASK_PREFIX,
)


@pytest.fixture()
def agent_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AgentDB:
    monkeypatch.setenv("FOUNDUPS_DB_ENGINE", "sqlite")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "namespace.db"))
    DatabaseManager.reset_for_tests()
    database = AgentDB()
    yield database
    DatabaseManager.reset_for_tests()


def _signed_task_id(suffix: str) -> str:
    return f"{SIGNED_WORKER_TASK_PREFIX}{suffix}"


def _seed_signed_task(
    database: AgentDB,
    *,
    task_id: str,
    status: str = "failed",
) -> None:
    context = json.dumps(
        {
            "schema_version": "reddog_signed_worker_agentdb_envelope.v1",
            "worker_principal_id": "worker-0102",
            "work_order_id": "work-1",
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    database.db.execute_write(
        """
        INSERT INTO agents_autonomous_tasks (
            task_id, description, required_skills, estimated_complexity,
            priority_score, discovered_by, discovered_at, context,
            assigned_to, assigned_at, retry_not_before, status, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            "legitimate signed worker task",
            '["reddog_signed_worker_dispatch"]',
            0.5,
            19.0,
            "signed_worker_publication",
            "2026-07-28T00:00:00+00:00",
            context,
            "openclaw",
            "2026-07-28T00:01:00+00:00",
            None,
            status,
            None,
        ),
    )


def _raw_task(database: AgentDB, task_id: str) -> dict[str, Any] | None:
    rows = database.db.execute_query(
        "SELECT * FROM agents_autonomous_tasks WHERE task_id = ?",
        (task_id,),
    )
    return dict(rows[0]) if rows else None


def test_generic_create_apis_cannot_enter_or_replace_signed_namespace(
    agent_db: AgentDB,
) -> None:
    existing_id = _signed_task_id("existing")
    absent_id = _signed_task_id("absent")
    _seed_signed_task(agent_db, task_id=existing_id)
    before = _raw_task(agent_db, existing_id)

    assert not agent_db.create_autonomous_task(
        task_id=existing_id,
        description="attacker replacement",
        required_skills=["attacker"],
        estimated_complexity=1.0,
        priority_score=99.0,
        context={"attacker": True},
    )
    assert not agent_db.create_autonomous_task_if_absent(
        task_id=existing_id,
        description="attacker replacement",
        required_skills=["attacker"],
        estimated_complexity=1.0,
        priority_score=99.0,
        context={"attacker": True},
    )
    assert _raw_task(agent_db, existing_id) == before

    assert not agent_db.create_autonomous_task(
        task_id=absent_id,
        description="attacker task",
        required_skills=["attacker"],
        estimated_complexity=1.0,
        priority_score=99.0,
        context={"attacker": True},
    )
    assert not agent_db.create_autonomous_task_if_absent(
        task_id=absent_id,
        description="attacker task",
        required_skills=["attacker"],
        estimated_complexity=1.0,
        priority_score=99.0,
        context={"attacker": True},
    )
    assert _raw_task(agent_db, absent_id) is None


def test_generic_retry_and_requeue_leave_signed_task_byte_identical(
    agent_db: AgentDB,
) -> None:
    task_id = _signed_task_id("immutable")
    _seed_signed_task(agent_db, task_id=task_id)
    before = _raw_task(agent_db, task_id)

    assert not agent_db.schedule_autonomous_task_retry(
        task_id,
        context={"attacker": True},
        retry_not_before="2026-07-29T00:00:00+00:00",
    )
    assert not agent_db.requeue_autonomous_task(
        task_id,
        expected_status="failed",
    )

    assert _raw_task(agent_db, task_id) == before


def test_signed_worker_assignment_path_remains_available(agent_db: AgentDB) -> None:
    task_id = _signed_task_id("assignment")
    _seed_signed_task(agent_db, task_id=task_id, status="pending")

    assert agent_db.assign_autonomous_task(task_id, "openclaw")
    assigned = _raw_task(agent_db, task_id)
    assert assigned is not None
    assert assigned["status"] == "assigned"
    assert assigned["assigned_to"] == "openclaw"
