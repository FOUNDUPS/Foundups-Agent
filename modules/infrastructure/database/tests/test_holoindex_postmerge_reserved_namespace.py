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
from modules.infrastructure.database.src.signed_worker_execution_quarantine import (
    quarantine_signed_worker_execution,
)
from modules.infrastructure.database.tests.signed_worker_assurance_test_support import (
    _request as _assurance_request,
    _seed_tasks as _seed_assurance_tasks,
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
    retry_context["retry_not_before"] = retry_at

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


@pytest.mark.parametrize(
    "retry_context",
    [
        {
            **_context(),
            "authority_root_digest": "sha256:" + "c" * 64,
            "retry_count": 1,
            "retry_not_before": "2026-08-01T00:00:00+00:00",
        },
        {
            **_context(),
            "retry_count": 999,
            "retry_not_before": "2026-08-01T00:00:00+00:00",
        },
    ],
)
def test_protected_retry_rejects_supplied_authority_or_sequence_rewrite(
    agent_db: AgentDB,
    retry_context: dict[str, Any],
) -> None:
    _create_protected(agent_db)
    agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'failed' WHERE task_id = ?",
        (TASK_ID,),
    )
    before = _raw_task(agent_db)

    assert not agent_db.schedule_holoindex_postmerge_task_retry(
        TASK_ID,
        context=retry_context,
        retry_not_before="2026-08-01T00:00:00+00:00",
    )
    assert _raw_task(agent_db) == before


@pytest.mark.parametrize("protected_field", ["author_task_id", "verifier_task_id"])
def test_assurance_reservation_rejects_protected_task_binding(
    agent_db: AgentDB,
    protected_field: str,
) -> None:
    _seed_assurance_tasks(agent_db)
    _create_protected(agent_db)
    before = _raw_task(agent_db)

    result = agent_db.reserve_independent_assurance(
        _assurance_request(**{protected_field: TASK_ID})
    )

    assert result["accepted"] is False
    assert any(
        "task_namespace_protected" in reason
        for reason in result["rejection_reasons"]
    )
    assert _raw_task(agent_db) == before


def test_forged_legacy_assurance_binding_cannot_mutate_protected_task(
    agent_db: AgentDB,
) -> None:
    _seed_assurance_tasks(agent_db)
    _create_protected(agent_db)
    assert agent_db.reserve_independent_assurance(_assurance_request())["accepted"]
    agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations "
        "SET verifier_task_id = ? WHERE reservation_id = ?",
        (TASK_ID, "assurance-1"),
    )
    before = _raw_task(agent_db)

    rehydrated = agent_db.get_independent_assurance_reservation("assurance-1")
    revoked = agent_db.revoke_independent_assurance(
        "assurance-1",
        reason="security-test",
        now_iso="2026-08-01T00:00:00+00:00",
    )
    staged = agent_db.stage_independent_assurance_completion(
        {"verifier_task_id": TASK_ID}
    )
    agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations SET status = 'EXPIRED' "
        "WHERE reservation_id = ?",
        ("assurance-1",),
    )
    renewed = agent_db.renew_independent_assurance(
        _assurance_request(
            verifier_task_id=TASK_ID,
            lease_id="lease-2",
            renewal_count=1,
        )
    )
    agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations "
        "SET status = 'RESERVED', expires_at = ? WHERE reservation_id = ?",
        ("2000-01-01T00:00:00Z", "assurance-1"),
    )
    expired = agent_db.expire_independent_assurance_reservations(
        now_iso="2030-08-01T00:00:00+00:00"
    )

    for result in (rehydrated, renewed, revoked, expired, staged):
        assert result is not None
        assert result["accepted"] is False
    assert _raw_task(agent_db) == before


def test_forged_legacy_assurance_binding_cannot_quarantine_protected_task(
    agent_db: AgentDB,
) -> None:
    signed_task_id = "reddog-worker-dispatch-quarantine-attacker"
    signed_context = '{"signed_worker":true}'
    _seed_assurance_tasks(agent_db)
    _create_protected(agent_db)
    assert agent_db.reserve_independent_assurance(_assurance_request())["accepted"]
    assert agent_db.db.execute_write(
        "INSERT INTO agents_autonomous_tasks "
        "(task_id, description, required_skills, estimated_complexity, "
        "priority_score, context, status, assigned_to) "
        "VALUES (?, 'signed author', '[]', 1.0, 1.0, ?, 'assigned', 'author-0102')",
        (signed_task_id, signed_context),
    ) == 1
    agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'assigned', "
        "assigned_to = 'verifier-0201' WHERE task_id = ?",
        (TASK_ID,),
    )
    agent_db.db.execute_write(
        "UPDATE agents_independent_assurance_reservations "
        "SET author_task_id = ?, verifier_task_id = ? WHERE reservation_id = ?",
        (signed_task_id, TASK_ID, "assurance-1"),
    )
    before_holo = _raw_task(agent_db)
    before_author = agent_db.get_autonomous_task_by_id(signed_task_id)
    before_reservation = agent_db.db.execute_query(
        "SELECT * FROM agents_independent_assurance_reservations "
        "WHERE reservation_id = ?",
        ("assurance-1",),
    )[0]

    result = quarantine_signed_worker_execution(
        agent_db,
        task_id=signed_task_id,
        raw_context=signed_context,
        expected_status="assigned",
        reason="security-replay",
        now_iso="2026-08-01T00:00:00+00:00",
    )

    assert result == "REJECTED"
    assert _raw_task(agent_db) == before_holo
    assert agent_db.get_autonomous_task_by_id(signed_task_id) == before_author
    assert agent_db.db.execute_query(
        "SELECT * FROM agents_independent_assurance_reservations "
        "WHERE reservation_id = ?",
        ("assurance-1",),
    )[0] == before_reservation


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
