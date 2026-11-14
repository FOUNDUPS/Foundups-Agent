"""Cross-object quarantine regressions for signed-worker recovery."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier

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
    _request,
    _seed_tasks,
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


def test_author_quarantine_atomically_cancels_reserved_verifier(
    agent_db: AgentDB,
) -> None:
    task_id = "reddog-worker-dispatch-author-quarantine"
    _seed_tasks(agent_db)
    assert agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET task_id = ? WHERE task_id = ?",
        (task_id, "author-task"),
    ) == 1
    reserved = agent_db.reserve_independent_assurance(
        _request(author_task_id=task_id)
    )
    assert reserved["accepted"] is True
    assert agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'executing', assigned_to = ? "
        "WHERE task_id = ? AND status = 'pending'",
        ("agentdb-task:" + task_id, task_id),
    ) == 1
    task = agent_db.get_autonomous_task_by_id(task_id)
    assert task is not None
    raw_context = agent_db.db.execute_query(
        "SELECT context FROM agents_autonomous_tasks WHERE task_id = ?",
        (task_id,),
    )[0]["context"]
    now_iso = datetime.now(timezone.utc).isoformat()

    first = quarantine_signed_worker_execution(
        agent_db,
        task_id=task_id,
        raw_context=raw_context,
        expected_status="executing",
        reason="author_effect_indeterminate",
        now_iso=now_iso,
    )
    after_first = agent_db.get_autonomous_task_by_id(task_id)
    second = quarantine_signed_worker_execution(
        agent_db,
        task_id=task_id,
        raw_context=raw_context,
        expected_status="executing",
        reason="author_effect_indeterminate",
        now_iso=now_iso,
    )

    assert first == second == "QUARANTINED"
    assert agent_db.get_autonomous_task_by_id(task_id) == after_first
    assert after_first["status"] == "quarantined"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation["reservation"]["status"] == "QUARANTINED"
    assert agent_db.get_autonomous_task_by_id("verifier-task")["status"] == "cancelled"


def test_author_quarantine_accepts_prior_verifier_quarantine(
    agent_db: AgentDB,
) -> None:
    author_id = "reddog-worker-dispatch-author-concurrent"
    verifier_id = "reddog-worker-dispatch-verifier-concurrent"
    _seed_tasks(agent_db)
    assert agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET task_id = ? WHERE task_id = ?",
        (author_id, "author-task"),
    ) == 1
    assert agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET task_id = ? WHERE task_id = ?",
        (verifier_id, "verifier-task"),
    ) == 1
    reserved = agent_db.reserve_independent_assurance(
        _request(author_task_id=author_id, verifier_task_id=verifier_id)
    )
    assert reserved["accepted"] is True
    assert agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'executing' "
        "WHERE task_id IN (?, ?)",
        (author_id, verifier_id),
    ) == 2
    raw = {
        row["task_id"]: row["context"]
        for row in agent_db.db.execute_query(
            "SELECT task_id, context FROM agents_autonomous_tasks "
            "WHERE task_id IN (?, ?)",
            (author_id, verifier_id),
        )
    }
    now_iso = datetime.now(timezone.utc).isoformat()

    assert quarantine_signed_worker_execution(
        agent_db,
        task_id=verifier_id,
        raw_context=raw[verifier_id],
        expected_status="executing",
        reason="verifier_effect_indeterminate",
        now_iso=now_iso,
    ) == "QUARANTINED"
    assert quarantine_signed_worker_execution(
        agent_db,
        task_id=author_id,
        raw_context=raw[author_id],
        expected_status="executing",
        reason="author_effect_indeterminate",
        now_iso=now_iso,
    ) == "QUARANTINED"
    assert agent_db.get_autonomous_task_by_id(author_id)["status"] == "quarantined"
    assert agent_db.get_autonomous_task_by_id(verifier_id)["status"] == "quarantined"
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation["reservation"]["status"] == "QUARANTINED"


def test_author_and_verifier_quarantine_race_stays_coherent(
    agent_db: AgentDB,
) -> None:
    author_id = "reddog-worker-dispatch-author-race"
    verifier_id = "reddog-worker-dispatch-verifier-race"
    _seed_tasks(agent_db)
    for original, replacement in (
        ("author-task", author_id),
        ("verifier-task", verifier_id),
    ):
        assert agent_db.db.execute_write(
            "UPDATE agents_autonomous_tasks SET task_id = ? WHERE task_id = ?",
            (replacement, original),
        ) == 1
    reserved = agent_db.reserve_independent_assurance(
        _request(author_task_id=author_id, verifier_task_id=verifier_id)
    )
    assert reserved["accepted"] is True
    assert agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'executing' "
        "WHERE task_id IN (?, ?)",
        (author_id, verifier_id),
    ) == 2
    raw = {
        row["task_id"]: row["context"]
        for row in agent_db.db.execute_query(
            "SELECT task_id, context FROM agents_autonomous_tasks "
            "WHERE task_id IN (?, ?)",
            (author_id, verifier_id),
        )
    }
    barrier = Barrier(2)
    now_iso = datetime.now(timezone.utc).isoformat()

    def quarantine(task_id: str) -> str:
        barrier.wait(timeout=5)
        return quarantine_signed_worker_execution(
            AgentDB(),
            task_id=task_id,
            raw_context=raw[task_id],
            expected_status="executing",
            reason="concurrent_effect_indeterminate",
            now_iso=now_iso,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = dict(zip(
            (author_id, verifier_id),
            pool.map(quarantine, (author_id, verifier_id)),
            strict=True,
        ))

    assert outcomes[author_id] == "QUARANTINED"
    assert outcomes[verifier_id] in {"QUARANTINED", "REJECTED"}
    assert agent_db.get_autonomous_task_by_id(author_id)["status"] == "quarantined"
    assert agent_db.get_autonomous_task_by_id(verifier_id)["status"] in {
        "cancelled",
        "quarantined",
    }
    reservation = agent_db.get_independent_assurance_reservation("assurance-1")
    assert reservation["reservation"]["status"] == "QUARANTINED"
    assert agent_db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id IN (?, ?)",
        (author_id, verifier_id),
    ) == []


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


def test_quarantine_without_reservation_replays_idempotently(
    agent_db: AgentDB,
) -> None:
    task_id = "reddog-worker-dispatch-no-reservation"
    raw_context = json.dumps({"source": "signed-worker"}, sort_keys=True)
    assert agent_db.db.execute_write(
        "INSERT INTO agents_autonomous_tasks "
        "(task_id, description, required_skills, estimated_complexity, "
        "priority_score, discovered_by, context, status, assigned_to) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'executing', ?)",
        (
            task_id,
            "signed task without independent assurance",
            json.dumps(["reddog_signed_worker_dispatch"]),
            0.1,
            1.0,
            "reddog_signed_worker_dispatch_runtime",
            raw_context,
            "worker-1",
        ),
    ) == 1
    now_iso = datetime.now(timezone.utc).isoformat()

    first = quarantine_signed_worker_execution(
        agent_db,
        task_id=task_id,
        raw_context=raw_context,
        expected_status="executing",
        reason="canonical_authority_rejected",
        now_iso=now_iso,
    )
    after_first = agent_db.get_autonomous_task_by_id(task_id)
    second = quarantine_signed_worker_execution(
        agent_db,
        task_id=task_id,
        raw_context=raw_context,
        expected_status="executing",
        reason="canonical_authority_rejected",
        now_iso=now_iso,
    )

    assert first == "QUARANTINED"
    assert second == "QUARANTINED"
    assert agent_db.get_autonomous_task_by_id(task_id) == after_first


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
