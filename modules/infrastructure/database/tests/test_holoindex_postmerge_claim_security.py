"""Integrity and use-time fencing for HoloIndex post-merge claims."""

from __future__ import annotations

import json
import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager
from modules.infrastructure.database.src.holoindex_postmerge_claim_contract import (
    MAX_POSTMERGE_CLAIM_LEASE_SECONDS,
    build_holoindex_postmerge_claim_context,
    holoindex_postmerge_claim_binding_digest,
    holoindex_postmerge_claim_binding_valid,
    holoindex_postmerge_claim_completed_in_lease,
)


HEAD = "a" * 40
TASK_ID = "holoindex_postmerge_refresh:" + HEAD
REQUEST_ID = "holoindex_postmerge_requested:" + HEAD
COMPLETION_ID = "holoindex_postmerge_completed:" + HEAD
AGENT_ID = "openclaw_supervisor"
AUTHORITY_DIGEST = "sha256:" + ("b" * 64)
REQUEST_DIGEST = "sha256:" + ("c" * 64)
COMPLETION_PAYLOAD = {
    "schema_version": "holoindex_postmerge_coordination_v1",
    "payload_digest": "sha256:" + ("d" * 64),
}


@pytest.fixture()
def agent_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AgentDB:
    monkeypatch.setenv("FOUNDUPS_DB_ENGINE", "sqlite")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "claim.db"))
    DatabaseManager.reset_for_tests()
    database = AgentDB()
    yield database
    DatabaseManager.reset_for_tests()


def _base_context() -> dict[str, Any]:
    return {
        "schema_version": "holoindex_postmerge_coordination_v1",
        "source": "holoindex_postmerge_coordinator",
        "target_repo_head_sha": HEAD,
        "authority_root_digest": AUTHORITY_DIGEST,
        "request_event_id": REQUEST_ID,
    }


def _seed(agent_db: AgentDB) -> None:
    assert agent_db.create_coordination_event(
        REQUEST_ID,
        "holoindex_postmerge_maintenance",
        "wre",
        [AGENT_ID],
        {"payload_digest": REQUEST_DIGEST},
    )
    assert agent_db.create_holoindex_postmerge_task_if_absent(
        task_id=TASK_ID,
        description="exact SHA maintenance",
        required_skills=["holo-search"],
        estimated_complexity=3.0,
        priority_score=19.0,
        context=_base_context(),
    )


def _claim(agent_db: AgentDB, *, lease_seconds: int = 7500) -> dict[str, Any]:
    claim_id = agent_db.claim_holoindex_postmerge_task(
        TASK_ID,
        AGENT_ID,
        expected_source="holoindex_postmerge_coordinator",
        expected_schema_version="holoindex_postmerge_coordination_v1",
        expected_target_repo_head_sha=HEAD,
        expected_authority_root_digest=AUTHORITY_DIGEST,
        lease_seconds=lease_seconds,
    )
    assert claim_id
    task = agent_db.get_autonomous_task_by_id(TASK_ID)
    assert task is not None
    return task


@pytest.mark.parametrize(
    "lease_seconds",
    [True, False, 0, -1, 1.0, "1", MAX_POSTMERGE_CLAIM_LEASE_SECONDS + 1],
)
def test_claim_rejects_noncanonical_or_overlong_lease(
    agent_db: AgentDB, lease_seconds: Any,
) -> None:
    _seed(agent_db)
    assert not agent_db.claim_holoindex_postmerge_task(
        TASK_ID,
        AGENT_ID,
        expected_source="holoindex_postmerge_coordinator",
        expected_schema_version="holoindex_postmerge_coordination_v1",
        expected_target_repo_head_sha=HEAD,
        expected_authority_root_digest=AUTHORITY_DIGEST,
        lease_seconds=lease_seconds,
    )
    assert agent_db.get_autonomous_task_by_id(TASK_ID)["status"] == "pending"


def test_agentdb_and_idle_port_share_the_canonical_lease_default() -> None:
    from modules.infrastructure.idle_automation.src.holoindex_postmerge_contract import (
        ASSIGNMENT_LEASE_SECONDS,
        AgentDbPort,
    )

    concrete = inspect.signature(
        AgentDB.claim_holoindex_postmerge_task
    ).parameters["lease_seconds"].default
    protocol = inspect.signature(
        AgentDbPort.claim_holoindex_postmerge_task
    ).parameters["lease_seconds"].default
    assert concrete == protocol == ASSIGNMENT_LEASE_SECONDS
    assert ASSIGNMENT_LEASE_SECONDS == MAX_POSTMERGE_CLAIM_LEASE_SECONDS


def test_claim_expiry_boundary_is_closed() -> None:
    issued = datetime.now(timezone.utc)
    context = build_holoindex_postmerge_claim_context(
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        base_context=_base_context(),
        claim_id="hpmc_" + ("f" * 32),
        issued_at=issued,
        lease_seconds=1,
    )
    assert context is not None
    expires = datetime.fromisoformat(str(context["claim_expires_at"]))
    assert not holoindex_postmerge_claim_binding_valid(
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        assigned_at=context["claim_issued_at"],
        context=context,
        now=expires,
        require_active=True,
    )
    assert holoindex_postmerge_claim_binding_valid(
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        assigned_at=context["claim_issued_at"],
        context=context,
        now=expires,
        require_expired=True,
    )
    assert not holoindex_postmerge_claim_completed_in_lease(
        context, context["claim_expires_at"]
    )


@pytest.mark.parametrize("field", ["claim_id", "claim_expires_at"])
def test_rehashed_stored_claim_tamper_cannot_replace_issued_capability(
    agent_db: AgentDB, field: str,
) -> None:
    _seed(agent_db)
    task = _claim(agent_db)
    original = dict(task["context"])
    tampered = dict(original)
    tampered[field] = (
        "hpmc_" + ("e" * 32)
        if field == "claim_id"
        else (
            datetime.fromisoformat(tampered["claim_issued_at"])
            + timedelta(seconds=60)
        ).isoformat()
    )
    tampered["claim_binding_digest"] = holoindex_postmerge_claim_binding_digest(
        task_id=TASK_ID, agent_id=AGENT_ID, context=tampered,
    )
    agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET context = ? WHERE task_id = ?",
        (json.dumps(tampered), TASK_ID),
    )

    assert not agent_db.start_holoindex_postmerge_execution(
        TASK_ID,
        AGENT_ID,
        claim_id=str(original["claim_id"]),
        claim_binding_digest=str(original["claim_binding_digest"]),
    )
    assert agent_db.get_autonomous_task_by_id(TASK_ID)["status"] == "assigned"


def test_first_completion_after_expiry_is_atomically_rejected(
    agent_db: AgentDB,
) -> None:
    _seed(agent_db)
    task = _claim(agent_db)
    original = dict(task["context"])
    issued = datetime.now(timezone.utc) - timedelta(seconds=2)
    expired = build_holoindex_postmerge_claim_context(
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        base_context=_base_context(),
        claim_id=str(original["claim_id"]),
        issued_at=issued,
        lease_seconds=1,
    )
    assert expired is not None
    agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'executing', "
        "assigned_at = ?, context = ? WHERE task_id = ?",
        (expired["claim_issued_at"], json.dumps(expired), TASK_ID),
    )

    assert not agent_db.commit_holoindex_postmerge_completion(
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        request_event_id=REQUEST_ID,
        request_payload_digest=REQUEST_DIGEST,
        completion_event_id=COMPLETION_ID,
        completion_payload=COMPLETION_PAYLOAD,
        claim_id=str(expired["claim_id"]),
        claim_binding_digest=str(expired["claim_binding_digest"]),
    )
    assert agent_db.get_autonomous_task_by_id(TASK_ID)["status"] == "executing"
    assert agent_db.get_coordination_event_by_id(REQUEST_ID)[
        "resolution_status"
    ] == "pending"
    assert agent_db.get_coordination_event_by_id(COMPLETION_ID) is None


def test_exact_completed_replay_remains_idempotent_after_lease_expiry(
    agent_db: AgentDB,
) -> None:
    _seed(agent_db)
    task = _claim(agent_db)
    original = dict(task["context"])
    issued = datetime.now(timezone.utc) - timedelta(seconds=10)
    completed_at = issued + timedelta(seconds=2)
    expired = build_holoindex_postmerge_claim_context(
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        base_context=_base_context(),
        claim_id=str(original["claim_id"]),
        issued_at=issued,
        lease_seconds=5,
    )
    assert expired is not None
    agent_db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'completed', "
        "assigned_at = ?, completed_at = ?, context = ? WHERE task_id = ?",
        (
            expired["claim_issued_at"], completed_at.isoformat(),
            json.dumps(expired), TASK_ID,
        ),
    )
    agent_db.db.execute_write(
        "UPDATE agents_coordination_events SET resolution_status = 'completed' "
        "WHERE event_id = ?",
        (REQUEST_ID,),
    )
    assert agent_db.create_coordination_event(
        COMPLETION_ID,
        "holoindex_postmerge_maintenance_completed",
        AGENT_ID,
        ["wre"],
        COMPLETION_PAYLOAD,
    )

    assert agent_db.commit_holoindex_postmerge_completion(
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        request_event_id=REQUEST_ID,
        request_payload_digest=REQUEST_DIGEST,
        completion_event_id=COMPLETION_ID,
        completion_payload=COMPLETION_PAYLOAD,
        claim_id=str(expired["claim_id"]),
        claim_binding_digest=str(expired["claim_binding_digest"]),
    )
