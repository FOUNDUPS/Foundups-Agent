"""Writer-contention expiry falsifiers for HoloIndex post-merge claims."""

from __future__ import annotations

import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pytest

from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager
from modules.infrastructure.database.src.holoindex_postmerge_claim_contract import (
    begin_holoindex_postmerge_write_fence,
)


HEAD = "a" * 40
TASK_ID = "holoindex_postmerge_refresh:" + HEAD
REQUEST_ID = "holoindex_postmerge_requested:" + HEAD
COMPLETION_ID = "holoindex_postmerge_completed:" + HEAD
AGENT_ID = "openclaw_supervisor"
AUTHORITY_DIGEST = "sha256:" + ("b" * 64)
REQUEST_DIGEST = "sha256:" + ("c" * 64)


@pytest.fixture()
def agent_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AgentDB:
    monkeypatch.setenv("FOUNDUPS_DB_ENGINE", "sqlite")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "claim-atomicity.db"))
    DatabaseManager.reset_for_tests()
    database = AgentDB()
    yield database
    DatabaseManager.reset_for_tests()


def _seed(agent_db: AgentDB) -> dict[str, Any]:
    context = {
        "schema_version": "holoindex_postmerge_coordination_v1",
        "source": "holoindex_postmerge_coordinator",
        "target_repo_head_sha": HEAD,
        "authority_root_digest": AUTHORITY_DIGEST,
        "request_event_id": REQUEST_ID,
    }
    assert agent_db.create_coordination_event(
        REQUEST_ID, "holoindex_postmerge_maintenance", "wre", [AGENT_ID],
        {"payload_digest": REQUEST_DIGEST},
    )
    assert agent_db.create_holoindex_postmerge_task_if_absent(
        task_id=TASK_ID, description="exact SHA maintenance",
        required_skills=["holo-search"], estimated_complexity=3.0,
        priority_score=19.0, context=context,
    )
    return context


def _seed_and_claim(agent_db: AgentDB) -> tuple[str, str]:
    context = _seed(agent_db)
    claim_id = agent_db.claim_holoindex_postmerge_task(
        TASK_ID, AGENT_ID, expected_source=context["source"],
        expected_schema_version=context["schema_version"],
        expected_target_repo_head_sha=HEAD,
        expected_authority_root_digest=AUTHORITY_DIGEST, lease_seconds=1,
    )
    task = agent_db.get_autonomous_task_by_id(TASK_ID)
    assert task is not None and claim_id
    return claim_id, str(task["context"]["claim_binding_digest"])


def _cross_expiry_behind_writer(
    agent_db: AgentDB, operation: Callable[[], Any],
) -> Any:
    path = str(agent_db.db.backend_info()["db_path"])
    blocker = sqlite3.connect(path, isolation_level=None, timeout=5.0)
    blocker.execute("BEGIN IMMEDIATE")
    result: list[Any] = []
    worker = threading.Thread(target=lambda: result.append(operation()))
    worker.start()
    time.sleep(1.1)
    blocker.rollback()
    blocker.close()
    worker.join(timeout=5.0)
    assert not worker.is_alive() and len(result) == 1
    return result[0]


def test_claim_issues_lease_after_sqlite_writer_wait(agent_db: AgentDB) -> None:
    context = _seed(agent_db)
    released_at: list[datetime] = []

    def claim() -> str:
        return agent_db.claim_holoindex_postmerge_task(
            TASK_ID, AGENT_ID, expected_source=context["source"],
            expected_schema_version=context["schema_version"],
            expected_target_repo_head_sha=HEAD,
            expected_authority_root_digest=AUTHORITY_DIGEST, lease_seconds=1,
        )

    path = str(agent_db.db.backend_info()["db_path"])
    blocker = sqlite3.connect(path, isolation_level=None, timeout=5.0)
    blocker.execute("BEGIN IMMEDIATE")
    result: list[str] = []
    worker = threading.Thread(target=lambda: result.append(claim()))
    worker.start()
    time.sleep(1.1)
    released_at.append(datetime.now(timezone.utc))
    blocker.rollback()
    blocker.close()
    worker.join(timeout=5.0)
    assert not worker.is_alive() and result and result[0]
    task = agent_db.get_autonomous_task_by_id(TASK_ID)
    assert datetime.fromisoformat(task["context"]["claim_issued_at"]) >= released_at[0]


def test_start_rechecks_expiry_after_sqlite_writer_wait(agent_db: AgentDB) -> None:
    claim_id, digest = _seed_and_claim(agent_db)
    accepted = _cross_expiry_behind_writer(
        agent_db,
        lambda: agent_db.start_holoindex_postmerge_execution(
            TASK_ID, AGENT_ID, claim_id=claim_id, claim_binding_digest=digest,
        ),
    )
    assert not accepted
    assert agent_db.get_autonomous_task_by_id(TASK_ID)["status"] == "assigned"


def test_completion_rechecks_expiry_after_sqlite_writer_wait(
    agent_db: AgentDB,
) -> None:
    claim_id, digest = _seed_and_claim(agent_db)
    assert agent_db.start_holoindex_postmerge_execution(
        TASK_ID, AGENT_ID, claim_id=claim_id, claim_binding_digest=digest,
    )
    payload: dict[str, Any] = {
        "schema_version": "holoindex_postmerge_coordination_v1",
        "payload_digest": "sha256:" + ("d" * 64),
    }
    accepted = _cross_expiry_behind_writer(
        agent_db,
        lambda: agent_db.commit_holoindex_postmerge_completion(
            task_id=TASK_ID, agent_id=AGENT_ID, request_event_id=REQUEST_ID,
            request_payload_digest=REQUEST_DIGEST,
            completion_event_id=COMPLETION_ID, completion_payload=payload,
            claim_id=claim_id, claim_binding_digest=digest,
        ),
    )
    assert not accepted
    assert agent_db.get_autonomous_task_by_id(TASK_ID)["status"] == "executing"
    assert agent_db.get_coordination_event_by_id(COMPLETION_ID) is None


def test_postgres_fence_emits_row_lock_without_eager_statement() -> None:
    """Keep the backend seam exact while a live PostgreSQL lane is unavailable."""

    class PostgresDatabase:
        @staticmethod
        def backend_info() -> dict[str, str]:
            return {"engine": "postgres"}

    class RecordingConnection:
        def __init__(self) -> None:
            self.statements: list[str] = []

        def execute(self, statement: str) -> None:
            self.statements.append(statement)

    connection = RecordingConnection()
    suffix = begin_holoindex_postmerge_write_fence(
        PostgresDatabase(), connection,
    )

    assert suffix == " FOR UPDATE"
    assert connection.statements == []
