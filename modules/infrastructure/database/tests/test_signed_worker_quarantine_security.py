"""Cross-object quarantine regressions for signed-worker recovery."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_signed_worker_execution_recovery import (
    recover_expired_signed_worker_executions,
)
from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager
from modules.infrastructure.database.src.signed_worker_execution_quarantine import (
    quarantine_signed_worker_execution,
)
from modules.infrastructure.database.tests.signed_worker_assurance_test_support import (
    _prepare_signed_verifier_recovery,
)


@pytest.fixture()
def agent_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AgentDB:
    monkeypatch.setenv("FOUNDUPS_DB_ENGINE", "sqlite")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "assurance.db"))
    DatabaseManager.reset_for_tests()
    database = AgentDB()
    yield database
    DatabaseManager.reset_for_tests()


def test_first_quarantine_atomically_releases_reserved_verifier(
    agent_db: AgentDB,
) -> None:
    task_id, claimed_at = _prepare_signed_verifier_recovery(
        agent_db,
        terminal_status="VERIFIED",
    )
    task = agent_db.get_autonomous_task_by_id(task_id)
    assert task is not None

    outcome = quarantine_signed_worker_execution(
        agent_db,
        task_id=task_id,
        raw_context=json.dumps(task["context"], sort_keys=True),
        expected_status="executing",
        reason="canonical_authority_rejected",
        now_iso=claimed_at.isoformat(),
    )

    assert outcome == "QUARANTINED"
    assert agent_db.get_autonomous_task_by_id(task_id)["status"] == "quarantined"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation["reservation"]["status"] == "QUARANTINED"


def test_quarantine_rejects_generic_namespace_without_mutation(
    agent_db: AgentDB,
) -> None:
    task_id = "generic-forged-quarantine"
    assert agent_db.create_autonomous_task(
        task_id=task_id,
        description="ordinary generic task",
        required_skills=[],
        estimated_complexity=0.1,
        priority_score=1.0,
        context={"signed_worker_agentdb_envelope": {"attacker_selected": True}},
    )
    assert agent_db.assign_autonomous_task(task_id, "generic-worker")
    before = agent_db.db.execute_query(
        "SELECT status, context, assigned_to, assigned_at, completed_at "
        "FROM agents_autonomous_tasks WHERE task_id = ?",
        (task_id,),
    )[0]

    outcome = quarantine_signed_worker_execution(
        agent_db,
        task_id=task_id,
        raw_context=before["context"],
        expected_status="assigned",
        reason="forged_signed_metadata",
        now_iso=datetime.now(timezone.utc).isoformat(),
    )

    after = agent_db.db.execute_query(
        "SELECT status, context, assigned_to, assigned_at, completed_at "
        "FROM agents_autonomous_tasks WHERE task_id = ?",
        (task_id,),
    )[0]
    assert outcome == "REJECTED"
    assert after == before


def test_invalid_stale_assignment_quarantines_before_reservation_skip(
    agent_db: AgentDB,
) -> None:
    task_id, _ = _prepare_signed_verifier_recovery(
        agent_db,
        terminal_status="VERIFIED",
    )
    task = agent_db.get_autonomous_task_by_id(task_id)
    assert task is not None
    context = dict(task["context"])
    context.pop("signed_worker_agentdb_envelope", None)
    context.pop("signed_worker_execution_claim", None)
    context.pop("signed_worker_execution_use", None)
    stale = datetime.now(timezone.utc) - timedelta(seconds=301)
    assert agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'assigned', context = ?, "
        "assigned_at = ? WHERE task_id = ? AND status = 'executing'",
        (json.dumps(context, sort_keys=True), stale.isoformat(), task_id),
    ) == 1

    recovered = recover_expired_signed_worker_executions(agent_db)

    assert recovered["accepted"] is True
    assert recovered["quarantined_task_ids"] == [task_id]
    assert agent_db.get_autonomous_task_by_id(task_id)["status"] == "quarantined"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation["reservation"]["status"] == "QUARANTINED"
