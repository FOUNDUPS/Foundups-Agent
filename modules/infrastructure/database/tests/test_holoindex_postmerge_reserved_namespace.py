"""Security regressions for the HoloIndex post-merge task namespace."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager
from modules.infrastructure.database.src.holoindex_postmerge_task_namespace import (
    HOLOINDEX_POSTMERGE_TASK_PREFIX,
)


SHA = "a" * 40
TASK_ID = HOLOINDEX_POSTMERGE_TASK_PREFIX + SHA


@pytest.fixture()
def agent_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AgentDB:
    monkeypatch.setenv("FOUNDUPS_DB_ENGINE", "sqlite")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "namespace.db"))
    DatabaseManager.reset_for_tests()
    database = AgentDB()
    yield database
    DatabaseManager.reset_for_tests()


def _context() -> dict[str, Any]:
    return {
        "schema_version": "holoindex_postmerge_coordination_v1",
        "source": "holoindex_postmerge_coordinator",
        "target_repo_head_sha": SHA,
        "authority_root_digest": "sha256:" + "b" * 64,
        "request_event_id": "holoindex_postmerge_requested:" + SHA,
        "retry_count": 0,
    }


def _create_protected(database: AgentDB) -> None:
    assert database.create_holoindex_postmerge_task_if_absent(
        task_id=TASK_ID,
        description="Refresh canonical HoloIndex",
        required_skills=["holo-search"],
        estimated_complexity=3.0,
        priority_score=19.0,
        context=_context(),
    )


def _raw_task(database: AgentDB) -> dict[str, Any] | None:
    rows = database.db.execute_query(
        "SELECT * FROM agents_autonomous_tasks WHERE task_id = ?",
        (TASK_ID,),
    )
    return dict(rows[0]) if rows else None


def test_generic_create_cannot_preseed_or_replace_postmerge_task(
    agent_db: AgentDB,
) -> None:
    for create in (
        agent_db.create_autonomous_task,
        agent_db.create_autonomous_task_if_absent,
    ):
        assert not create(
            task_id=TASK_ID,
            description="attacker task",
            required_skills=["attacker"],
            estimated_complexity=1.0,
            priority_score=99.0,
            context={"attacker": True},
        )
    assert _raw_task(agent_db) is None

    _create_protected(agent_db)
    before = _raw_task(agent_db)
    assert not agent_db.create_autonomous_task(
        task_id=TASK_ID,
        description="attacker replacement",
        required_skills=["attacker"],
        estimated_complexity=1.0,
        priority_score=99.0,
        context={"attacker": True},
    )
    assert _raw_task(agent_db) == before


def test_generic_assignment_and_completion_cannot_steal_postmerge_task(
    agent_db: AgentDB,
) -> None:
    _create_protected(agent_db)
    before = _raw_task(agent_db)

    assert not agent_db.assign_autonomous_task(TASK_ID, "attacker-agent")
    assert not agent_db.complete_autonomous_task(TASK_ID)

    assert _raw_task(agent_db) == before


def test_generic_retry_and_requeue_cannot_mutate_postmerge_task(
    agent_db: AgentDB,
) -> None:
    _create_protected(agent_db)
    agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'failed' WHERE task_id = ?",
        (TASK_ID,),
    )
    before = _raw_task(agent_db)

    assert not agent_db.schedule_autonomous_task_retry(
        TASK_ID,
        context={"attacker": True},
        retry_not_before="2026-08-01T00:00:00+00:00",
    )
    assert not agent_db.requeue_autonomous_task(
        TASK_ID,
        expected_status="failed",
    )

    assert _raw_task(agent_db) == before


def test_protected_retry_lane_preserves_coordinator_operation(
    agent_db: AgentDB,
) -> None:
    _create_protected(agent_db)
    agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'failed' WHERE task_id = ?",
        (TASK_ID,),
    )
    retry_context = {**_context(), "retry_count": 1}
    retry_at = "2026-08-01T00:00:00+00:00"

    assert agent_db.schedule_holoindex_postmerge_task_retry(
        TASK_ID,
        context=retry_context,
        retry_not_before=retry_at,
    )
    assert agent_db.get_autonomous_task_by_id(TASK_ID)["status"] == "retry_wait"
    assert agent_db.requeue_holoindex_postmerge_task(TASK_ID)
    assert agent_db.get_autonomous_task_by_id(TASK_ID)["status"] == "pending"


def test_protected_retry_rejects_tampered_stored_binding(
    agent_db: AgentDB,
) -> None:
    _create_protected(agent_db)
    agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'failed', context = ? "
        "WHERE task_id = ?",
        ('{"source":"attacker"}', TASK_ID),
    )

    assert not agent_db.schedule_holoindex_postmerge_task_retry(
        TASK_ID,
        context={**_context(), "retry_count": 1},
        retry_not_before="2026-08-01T00:00:00+00:00",
    )
    assert not agent_db.requeue_holoindex_postmerge_task(
        TASK_ID,
        expected_status="failed",
    )
    assert agent_db.get_autonomous_task_by_id(TASK_ID)["status"] == "failed"


def test_postmerge_reclaim_rejects_noncanonical_task_id(
    agent_db: AgentDB,
) -> None:
    assert agent_db.create_autonomous_task(
        task_id="ordinary-task",
        description="ordinary",
        required_skills=[],
        estimated_complexity=1.0,
        priority_score=1.0,
    )
    assigned_at = "2026-08-01T00:00:00+00:00"
    agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'assigned', "
        "assigned_to = 'openclaw_supervisor', assigned_at = ? WHERE task_id = ?",
        (assigned_at, "ordinary-task"),
    )

    assert not agent_db.reclaim_expired_holoindex_postmerge_task(
        "ordinary-task",
        "openclaw_supervisor",
        expected_assigned_at=assigned_at,
    )
    assert agent_db.get_autonomous_task_by_id("ordinary-task")["status"] == "assigned"


def test_postmerge_reclaim_rejects_tampered_stored_binding(
    agent_db: AgentDB,
) -> None:
    _create_protected(agent_db)
    assigned_at = "2026-08-01T00:00:00+00:00"
    agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'assigned', context = ?, "
        "assigned_to = 'openclaw_supervisor', assigned_at = ? WHERE task_id = ?",
        ('{"source":"attacker"}', assigned_at, TASK_ID),
    )

    assert not agent_db.reclaim_expired_holoindex_postmerge_task(
        TASK_ID,
        "openclaw_supervisor",
        expected_assigned_at=assigned_at,
    )
    assert agent_db.get_autonomous_task_by_id(TASK_ID)["status"] == "assigned"


@pytest.mark.parametrize(
    "task_id,context",
    [
        (HOLOINDEX_POSTMERGE_TASK_PREFIX + "A" * 40, _context()),
        (TASK_ID, {**_context(), "source": "attacker"}),
        (TASK_ID, {**_context(), "authority_root_digest": "sha256:bad"}),
        (TASK_ID, {**_context(), "request_event_id": "attacker"}),
    ],
)
def test_protected_create_rejects_malformed_bindings(
    agent_db: AgentDB,
    task_id: str,
    context: dict[str, Any],
) -> None:
    assert not agent_db.create_holoindex_postmerge_task_if_absent(
        task_id=task_id,
        description="Refresh canonical HoloIndex",
        required_skills=["holo-search"],
        estimated_complexity=3.0,
        priority_score=19.0,
        context=context,
    )
    assert _raw_task(agent_db) is None
