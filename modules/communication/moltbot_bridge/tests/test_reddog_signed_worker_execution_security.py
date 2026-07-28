"""Security regressions for signed-worker admission and lease ownership."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.scripts.run_task import execute_task
from modules.communication.moltbot_bridge.src.reddog_signed_worker_agentdb_envelope import (
    VerifiedSignedWorkerAgentDbEnvelope,
    verify_reddog_signed_worker_agentdb_envelope,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_execution_claim import (
    admit_signed_worker_execution_once,
    bind_execution_admission,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_execution_recovery import (
    _resolve_raced_finalization,
    recover_expired_signed_worker_executions,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_result_receipt import (
    DIRECT_ACCEPT,
    append_signed_worker_result_history,
    build_signed_worker_task_result_receipt,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    worker_dispatch_authority_verification_context,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_worker_dispatch_task_executor import (
    _FakeRunner,
    _publish_agentdb_task,
)
from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager
from modules.infrastructure.database.src.signed_worker_execution_store import (
    finalize_signed_worker_execution,
)


@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    DatabaseManager.reset_for_tests()
    from modules.communication.moltbot_bridge.src import (
        reddog_signed_worker_agentdb_envelope as envelope_module,
    )

    monkeypatch.setattr(
        envelope_module,
        "build_worker_dispatch_authority_context_from_env",
        lambda **_: worker_dispatch_authority_verification_context(),
    )
    yield
    DatabaseManager.reset_for_tests()


def _verified_admission(db: AgentDB, task_id: str):
    task = db.get_autonomous_task_by_id(task_id)
    assert task is not None
    verified = verify_reddog_signed_worker_agentdb_envelope(
        envelope=task["context"]["signed_worker_agentdb_envelope"],
        task_id=task_id,
        authority_context=worker_dispatch_authority_verification_context(),
    )
    admission = admit_signed_worker_execution_once(
        db=db,
        task_id=task_id,
        verified_envelope=verified,
    )
    assert admission is not None
    return admission


def _ledger_count(db: AgentDB, task_id: str) -> int:
    with db.db.get_connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM agents_signed_worker_result_history "
            "WHERE task_id = ?",
            (task_id,),
        ).fetchone()
    return int(dict(row).get("count") or 0)


def test_forged_process_local_verification_proof_cannot_admit() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    task = db.get_autonomous_task_by_id(task_id)
    assert task is not None
    forged = VerifiedSignedWorkerAgentDbEnvelope(
        task_id=task_id,
        canonical_context=task["context"],
        dispatch_receipt={},
        dispatch_intent={},
        authority_verification_result={},
        _verification_seal=object(),
    )

    admitted = admit_signed_worker_execution_once(
        db=db,
        task_id=task_id,
        verified_envelope=forged,
    )

    assert admitted is None
    assert db.get_autonomous_task_by_id(task_id)["status"] == "quarantined"
    assert _ledger_count(db, task_id) == 0


def test_expired_execution_lease_cannot_finalize_success() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    admission = _verified_admission(db, task_id)
    context = bind_execution_admission(admission.claimed_context, admission)
    receipt = build_signed_worker_task_result_receipt(
        base_context=context,
        claim_status=DIRECT_ACCEPT,
        result={"accepted": True, "decision": "ACCEPT", "receipt_id": "result-1"},
    )
    result_context = append_signed_worker_result_history(context, receipt)
    expired = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert db.db.execute_write(
        "UPDATE agents_signed_worker_execution_leases SET lease_expires_at = ? "
        "WHERE task_id = ?",
        (expired.isoformat(), task_id),
    ) == 1

    finalized = finalize_signed_worker_execution(
        db,
        task_id,
        context=context,
        accepted=True,
        result_context=result_context,
    )

    assert finalized is False
    assert db.get_autonomous_task_by_id(task_id)["status"] == "executing"
    assert _ledger_count(db, task_id) == 0


def test_direct_run_rejects_stale_assignment_without_runner_effect(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    stale = datetime.now(timezone.utc) - timedelta(seconds=301)
    assert db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET assigned_at = ? WHERE task_id = ?",
        (stale.isoformat(), task_id),
    ) == 1
    runner = _FakeRunner()

    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=runner,
    )

    assert result["ok"] is False
    assert runner.calls == []
    assert db.get_autonomous_task_by_id(task_id)["status"] == "assigned"
    recovered = recover_expired_signed_worker_executions(db)
    assert recovered["requeued_assigned_task_ids"] == [task_id]


def test_empty_decision_terminal_result_survives_recovery_race() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    admission = _verified_admission(db, task_id)
    context = bind_execution_admission(admission.claimed_context, admission)
    receipt = build_signed_worker_task_result_receipt(
        base_context=context,
        claim_status=DIRECT_ACCEPT,
        result={"accepted": True, "decision": "", "receipt_id": "result-1"},
    )
    result_context = append_signed_worker_result_history(context, receipt)
    assert finalize_signed_worker_execution(
        db,
        task_id,
        context=context,
        accepted=True,
        result_context=result_context,
    )

    outcome = _resolve_raced_finalization(
        db,
        task_id=task_id,
        now=datetime.now(timezone.utc),
    )

    assert outcome == "SKIPPED"
    assert db.get_autonomous_task_by_id(task_id)["status"] == "completed"
    assert _ledger_count(db, task_id) == 1
