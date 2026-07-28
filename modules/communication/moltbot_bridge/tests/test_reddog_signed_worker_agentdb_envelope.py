"""Security regressions for persisted signed-worker AgentDB envelopes."""

from __future__ import annotations

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.scripts.run_task import execute_task
from modules.communication.moltbot_bridge.src import (
    openclaw_supervisor as supervisor_module,
    reddog_openclaw_hermes_0102_worker_dispatch_runtime as runtime,
    reddog_signed_worker_execution_claim as execution_claim_module,
    reddog_signed_worker_run_task_runtime as run_task_runtime,
    reddog_signed_worker_supervisor_admission as supervisor_admission_module,
)
from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
    SIGNED_WORKER_OPENCLAW_CLAIM_REJECT,
    SignedWorkerOpenClawClaimReason,
    claim_reddog_signed_worker_dispatch_task_once,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_agentdb_envelope import (
    verify_reddog_signed_worker_agentdb_envelope,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_execution_claim import (
    EXECUTION_LEASE_SECONDS,
    admit_signed_worker_execution_once,
    bind_execution_admission,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_execution_recovery import (
    recover_expired_signed_worker_executions,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_result_receipt import (
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
from modules.infrastructure.database.src import (
    signed_worker_execution_store as execution_store_module,
)


@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    monkeypatch.setenv("OPENCLAW_SIGNED_QUEUE_STAGE_TASKS_ENABLED", "1")
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


def _rewrite_context(task_id: str, mutate) -> dict[str, object]:
    db = AgentDB()
    task = db.get_autonomous_task_by_id(task_id)
    assert task is not None
    context = json.loads(json.dumps(task["context"]))
    mutate(context)
    assert db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET context = ? WHERE task_id = ?",
        (json.dumps(context, sort_keys=True), task_id),
    ) == 1
    return context


def _set_nested(
    mapping: dict[str, object],
    path: tuple[object, ...],
    value: object,
) -> None:
    cursor: object = mapping
    for key in path[:-1]:
        cursor = cursor[key]  # type: ignore[index]
    cursor[path[-1]] = value  # type: ignore[index]


def _test_digest(value: object) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, default=str,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _rechain_context_history(context: dict[str, object]) -> None:
    history = context["signed_worker_task_result_receipts"]
    assert isinstance(history, list)
    normalized: list[dict[str, object]] = []
    for raw in history:
        assert isinstance(raw, dict)
        sequence = int(raw.get("attempt_sequence") or 0)
        entry = {
            "attempt_sequence": sequence,
            "claim_status": str(raw.get("claim_status") or ""),
            "receipt_id": str(raw.get("receipt_id") or ""),
            "receipt_digest": str(raw.get("receipt_digest") or ""),
            "previous_history_digest": (
                str(normalized[-1]["history_entry_digest"])
                if normalized
                else (
                    _test_digest([])
                    if sequence == 1
                    else str(raw.get("previous_history_digest") or "")
                )
            ),
        }
        entry["history_entry_digest"] = _test_digest(entry)
        normalized.append(entry)
    context["signed_worker_task_result_receipts"] = normalized


def test_run_task_rebuilds_canonical_context_before_runner_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    _rewrite_context(
        task_id,
        lambda context: context.update(
            {
                "worker_runtime": "hermes",
                "worker_role": "attacker",
                "capability": "unbounded_repo_write",
                "worker_dispatch_intent": {
                    **dict(context["worker_dispatch_intent"]),
                    "worker_runtime": "hermes",
                    "role": "attacker",
                    "capability": "unbounded_repo_write",
                },
            }
        ),
    )
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    runner = _FakeRunner()

    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=runner,
    )

    assert result["ok"] is True
    assert len(runner.calls) == 1
    canonical = runner.calls[0]["task_context"]
    assert canonical["worker_runtime"] == "openclaw"
    assert canonical["worker_role"] == "openclaw_candidate"
    assert canonical["capability"] == "candidate_queue_review"
    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "completed"
    assert stored["context"]["worker_runtime"] == "openclaw"
    assert stored["context"]["worker_role"] == "openclaw_candidate"
    assert stored["context"]["capability"] == "candidate_queue_review"


def test_run_task_signed_success_uses_exact_finalization_cas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    monkeypatch.setattr(
        AgentDB,
        "complete_autonomous_task",
        lambda *_args, **_kwargs: pytest.fail("generic finalizer used"),
    )
    runner = _FakeRunner()

    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=runner,
    )

    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert result["ok"] is True
    assert result["finalization_owned"] is True
    assert stored is not None and stored["status"] == "completed"


def test_generic_completion_rejects_reserved_signed_worker_namespace() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()

    assert db.complete_autonomous_task(task_id) is False

    stored = db.get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "pending"
    assert "signed_worker_execution_claim" not in stored["context"]


def test_direct_run_preserves_requeue_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)

    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(requeue_required=True),
    )

    stored = db.get_autonomous_task_by_id(task_id)
    assert result["ok"] is True
    assert stored is not None and stored["status"] == "pending"
    assert stored["assigned_to"] is None
    receipt = stored["context"]["signed_worker_task_last_result"]
    assert receipt["claim_status"] == "DIRECT_REQUEUED"
    assert receipt["runner_result_summary"]["queue_chain_requeue_required"] is True
    assert db.db.execute_query(
        "SELECT attempt_sequence FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    ) == [{"attempt_sequence": 1}]


def test_run_task_post_claim_exception_fails_through_exact_cas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    monkeypatch.setattr(
        run_task_runtime,
        "_runner",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("binding-failed")),
    )

    result = execute_task(task_id, repo_root=tmp_path)

    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert result["ok"] is False
    assert result["finalization_owned"] is True
    assert "dispatch_error:RuntimeError" in result["detail"]
    assert stored is not None and stored["status"] == "failed"


def test_run_task_finalization_conflict_never_overwrites_concurrent_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    original = run_task_runtime.finalize_signed_worker_execution

    def conflict(
        db, selected_task_id, *, context, accepted, result_context, **kwargs
    ):
        assert db.db.execute_write(
            "UPDATE agents_autonomous_tasks SET status = 'cancelled' "
            "WHERE task_id = ? AND status = 'executing'",
            (selected_task_id,),
        ) == 1
        return original(
            db,
            selected_task_id,
            context=context,
            accepted=accepted,
            result_context=result_context,
            **kwargs,
        )

    monkeypatch.setattr(
        run_task_runtime, "finalize_signed_worker_execution", conflict
    )
    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
    )

    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert result["ok"] is False
    assert result["finalization_owned"] is True
    assert result["detail"] == "reddog_signed_worker_finalization_conflict"
    assert stored is not None and stored["status"] == "cancelled"
    rows = db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    )
    assert rows == []


def test_execution_claim_consumes_token_without_persisting_raw_value() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")

    admission = admit_signed_worker_execution_once(
        db=db,
        task_id=task_id,
        token_factory=lambda: "raw-use-token-must-not-persist",
    )

    assert admission is not None
    task = db.get_autonomous_task_by_id(task_id)
    assert task is not None and task["status"] == "executing"
    serialized = json.dumps(task["context"], sort_keys=True)
    assert "raw-use-token-must-not-persist" not in serialized
    assert admission.claim_receipt["status"] == "CLAIMED"
    assert admission.use_receipt["status"] == "CONSUMED"
    assert admission.claim_receipt["token_digest"].startswith("sha256:")
    assert admission.use_receipt["token_digest"] == (
        admission.claim_receipt["token_digest"]
    )
    assert admit_signed_worker_execution_once(db=db, task_id=task_id) is None


def test_restart_recovers_expired_execution_without_replaying_worker() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    claimed_at = datetime(2026, 7, 28, tzinfo=timezone.utc)
    admission = admit_signed_worker_execution_once(
        db=db,
        task_id=task_id,
        now_factory=lambda: claimed_at,
    )
    assert admission is not None
    assert admission.claim_receipt["lease_expires_at"] == (
        claimed_at + timedelta(seconds=EXECUTION_LEASE_SECONDS)
    ).isoformat()

    DatabaseManager.reset_for_tests()
    restarted = AgentDB()
    recovered = recover_expired_signed_worker_executions(
        restarted,
        now_factory=lambda: (
            claimed_at
            + timedelta(seconds=EXECUTION_LEASE_SECONDS + 1)
        ),
    )

    assert recovered["accepted"] is True
    assert recovered["recovered_task_ids"] == [task_id]
    assert recovered["no_worker_effect_replayed"] is True
    stored = restarted.get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "failed"
    receipt = stored["context"]["signed_worker_task_last_result"]
    assert receipt["decision"] == "EXECUTION_LEASE_RECOVERED"
    assert receipt["accepted"] is False
    assert receipt["effect_commit_state"] == "INDETERMINATE"
    assert receipt["no_source_repo_mutation_performed"] is False
    rows = restarted.db.execute_query(
        "SELECT attempt_sequence FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    )
    assert rows == [{"attempt_sequence": 1}]

    repeated = recover_expired_signed_worker_executions(
        restarted,
        now_factory=lambda: (
            claimed_at
            + timedelta(seconds=EXECUTION_LEASE_SECONDS + 2)
        ),
    )
    assert repeated["accepted"] is True
    assert repeated["recovered_task_ids"] == []


def test_unexpired_execution_is_not_recovered() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    claimed_at = datetime(2026, 7, 28, tzinfo=timezone.utc)
    assert admit_signed_worker_execution_once(
        db=db,
        task_id=task_id,
        now_factory=lambda: claimed_at,
    ) is not None

    result = recover_expired_signed_worker_executions(
        db,
        now_factory=lambda: claimed_at + timedelta(seconds=30),
    )

    assert result["accepted"] is True
    assert result["recovered_task_ids"] == []
    stored = db.get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "executing"


def test_execution_recovery_database_scan_failure_rejects() -> None:
    class _BrokenDatabase:
        def get_connection(self):
            raise RuntimeError("database unavailable")

    result = recover_expired_signed_worker_executions(
        SimpleNamespace(db=_BrokenDatabase()),
    )

    assert result["accepted"] is False
    assert result["rejected_task_ids"] == ["database_scan_failed"]
    assert result["no_worker_effect_replayed"] is True


def test_concurrent_expired_execution_recovery_commits_one_result() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    claimed_at = datetime(2026, 7, 28, tzinfo=timezone.utc)
    assert admit_signed_worker_execution_once(
        db=db,
        task_id=task_id,
        now_factory=lambda: claimed_at,
    ) is not None
    recovered_at = claimed_at + timedelta(
        seconds=EXECUTION_LEASE_SECONDS + 1
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: recover_expired_signed_worker_executions(
                    AgentDB(),
                    now_factory=lambda: recovered_at,
                ),
                range(2),
            )
        )

    assert all(result["accepted"] is True for result in results)
    stored = db.get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "failed"
    rows = db.db.execute_query(
        "SELECT attempt_sequence FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    )
    assert rows == [{"attempt_sequence": 1}]


def test_concurrent_direct_run_task_executes_signed_worker_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    barrier = threading.Barrier(2)
    original_get = AgentDB.get_autonomous_tasks

    def synchronized_get(self, status="pending", limit=50):
        tasks = original_get(self, status=status, limit=limit)
        if status == "assigned":
            barrier.wait(timeout=5)
        return tasks

    monkeypatch.setattr(AgentDB, "get_autonomous_tasks", synchronized_get)
    runner = _FakeRunner()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: execute_task(
                    task_id,
                    repo_root=tmp_path,
                    signed_worker_runner=runner,
                ),
                range(2),
            )
        )

    assert sum(result["ok"] is True for result in results) == 1
    assert len(runner.calls) == 1
    loser = next(result for result in results if result["ok"] is False)
    assert loser["finalization_owned"] is True
    assert "execution_already_claimed" in loser["detail"]
    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "completed"
    assert stored["context"]["signed_worker_execution_use"]["status"] == "CONSUMED"
    rows = db.db.execute_query(
        "SELECT attempt_sequence FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    )
    assert rows == [{"attempt_sequence": 1}]


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("signed_worker_agentdb_envelope",), {}),
        (
            ("signed_worker_agentdb_envelope", "schema_version"),
            "reddog_signed_worker_agentdb_envelope.v999",
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "worker_dispatch_intent",
                "capability",
            ),
            "unbounded_repo_write",
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "worker_dispatch_intent",
                "intent_id",
            ),
            "worker_dispatch_intent_attacker",
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "signed_authority_worker_dispatch_receipt",
                "receipt_id",
            ),
            "signed_authority_worker_dispatch_attacker",
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "signed_authority_worker_dispatch_receipt",
                "architect_fix_publication_binding_digest",
            ),
            "sha256:attacker-publication",
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "wsp15_allocation_receipt",
                "mps_total",
            ),
            1,
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "queue_consumer_receipt",
                "operational_snapshot_id",
            ),
            "sha256:" + ("f" * 64),
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "agentdb_task_binding",
                "task_id",
            ),
            "reddog-worker-dispatch-attacker",
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "queue_authority_runtime_result",
                "authority_result",
                "identity",
                "principal_public_key",
            ),
            "pub:attacker",
        ),
        (
            (
                "signed_worker_agentdb_envelope",
                "queue_authority_runtime_result",
                "authority_result",
                "work_authority",
                "requested_operation",
            ),
            "unbounded_repo_write",
        ),
    ),
)
def test_claim_rejects_tampered_envelope_before_runner_selection(
    tmp_path: Path,
    path: tuple[object, ...],
    value: object,
) -> None:
    task_id = _publish_agentdb_task()
    _rewrite_context(
        task_id,
        lambda context: _set_nested(context, path, value),
    )
    runner = _FakeRunner()

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REJECT
    assert (
        SignedWorkerOpenClawClaimReason.AGENTDB_ENVELOPE_REJECTED
        in result["rejection_reasons"]
    )
    assert runner.calls == []
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "failed"


def test_claim_time_preflight_is_restart_safe_and_non_consuming() -> None:
    task_id = _publish_agentdb_task()
    task = AgentDB().get_autonomous_task_by_id(task_id)
    assert task is not None
    envelope = task["context"]["signed_worker_agentdb_envelope"]
    authority = worker_dispatch_authority_verification_context()

    first = verify_reddog_signed_worker_agentdb_envelope(
        envelope=envelope,
        task_id=task_id,
        authority_context=authority,
    )
    second = verify_reddog_signed_worker_agentdb_envelope(
        envelope=envelope,
        task_id=task_id,
        authority_context=authority,
    )

    assert first.task_id == task_id
    assert second.canonical_context == first.canonical_context


def test_supervisor_verifies_exact_claimed_database_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    original_admit = execution_claim_module.admit_signed_worker_execution_once

    def replace_then_admit(*, db, task_id):
        assert db.db.execute_write(
            "UPDATE agents_autonomous_tasks "
            "SET context = ?, required_skills = ?, discovered_by = ? "
            "WHERE task_id = ? AND status = 'assigned'",
            (json.dumps({}), json.dumps(["attacker_skill"]), "attacker", task_id),
        ) == 1
        return original_admit(db=db, task_id=task_id)

    monkeypatch.setattr(
        supervisor_admission_module,
        "admit_signed_worker_execution_once",
        replace_then_admit,
    )
    runner = _FakeRunner()
    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REJECT
    assert runner.calls == []
    assert stored is not None and stored["status"] == "failed"


def test_supervisor_finalization_conflict_never_overwrites_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    original_persist = (
        supervisor_module._persist_reddog_signed_worker_dispatch_task_result
    )

    def replace_owner_then_persist(db, selected_task_id, **kwargs):
        assert db.db.execute_write(
            "UPDATE agents_autonomous_tasks "
            "SET assigned_to = ?, context = ? "
            "WHERE task_id = ? AND status = 'executing'",
            ("other-worker", json.dumps({"owner": "other-worker"}), selected_task_id),
        ) == 1
        return original_persist(db, selected_task_id, **kwargs)

    monkeypatch.setattr(
        supervisor_module,
        "_persist_reddog_signed_worker_dispatch_task_result",
        replace_owner_then_persist,
    )
    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert result["accepted"] is False
    assert (
        SignedWorkerOpenClawClaimReason.RESULT_PERSISTENCE_REJECTED
        in result["rejection_reasons"]
    )
    assert stored is not None and stored["status"] == "executing"
    assert stored["assigned_to"] == "other-worker"
    assert stored["context"] == {"owner": "other-worker"}


def test_supervisor_rejects_malformed_requeue_result_history(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    first = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(requeue_required=True),
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )
    assert first["accepted"] is True
    second = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(requeue_required=True),
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )
    assert second["accepted"] is True
    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert len(stored["context"]["signed_worker_task_result_receipts"]) == 2
    _rewrite_context(
        task_id,
        lambda context: context["signed_worker_task_last_result"].update(
            receipt_digest="sha256:" + ("0" * 64)
        ),
    )
    runner = _FakeRunner()
    rejected = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    assert rejected["accepted"] is False
    assert runner.calls == []
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "failed"


def test_supervisor_rejects_tampered_earlier_requeue_result_history(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    for _ in range(2):
        result = claim_reddog_signed_worker_dispatch_task_once(
            repo_root=tmp_path,
            signed_worker_runner=_FakeRunner(requeue_required=True),
            authority_verification_context=(
                worker_dispatch_authority_verification_context()
            ),
        )
        assert result["accepted"] is True
    _rewrite_context(
        task_id,
        lambda context: context["signed_worker_task_result_receipts"][0].update(
            receipt_digest="sha256:not-a-digest"
        ),
    )
    runner = _FakeRunner()
    rejected = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    assert rejected["accepted"] is False
    assert runner.calls == []
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "failed"


def test_supervisor_rejects_gapped_durable_result_ledger(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    for _ in range(2):
        assert claim_reddog_signed_worker_dispatch_task_once(
            repo_root=tmp_path,
            signed_worker_runner=_FakeRunner(requeue_required=True),
            authority_verification_context=(
                worker_dispatch_authority_verification_context()
            ),
        )["accepted"] is True
    db = AgentDB()
    assert db.db.execute_write(
        "UPDATE agents_signed_worker_result_history "
        "SET attempt_sequence = 3 WHERE task_id = ? AND attempt_sequence = 2",
        (task_id,),
    ) == 1
    runner = _FakeRunner()

    rejected = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    assert rejected["accepted"] is False
    assert runner.calls == []
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "failed"


def test_supervisor_retains_ten_entry_tail_but_all_durable_attempts(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    for _ in range(11):
        assert claim_reddog_signed_worker_dispatch_task_once(
            repo_root=tmp_path,
            signed_worker_runner=_FakeRunner(requeue_required=True),
            authority_verification_context=(
                worker_dispatch_authority_verification_context()
            ),
        )["accepted"] is True
    db = AgentDB()
    stored = db.get_autonomous_task_by_id(task_id)
    assert stored is not None
    history = stored["context"]["signed_worker_task_result_receipts"]
    assert len(history) == 10
    assert history[0]["attempt_sequence"] == 2
    assert history[-1]["attempt_sequence"] == 11
    rows = db.db.execute_query(
        "SELECT attempt_sequence FROM agents_signed_worker_result_history "
        "WHERE task_id = ? ORDER BY attempt_sequence",
        (task_id,),
    )
    assert rows == [{"attempt_sequence": value} for value in range(1, 12)]


def test_preledger_context_history_is_quarantined_before_execution(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    task = db.get_autonomous_task_by_id(task_id)
    assert task is not None
    receipt = build_signed_worker_task_result_receipt(
        base_context=task["context"],
        claim_status="LEGACY_CONTEXT",
        result={"accepted": False, "decision": "legacy"},
    )
    forged = append_signed_worker_result_history(task["context"], receipt)
    assert db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET context = ? WHERE task_id = ?",
        (json.dumps(forged, sort_keys=True), task_id),
    ) == 1
    runner = _FakeRunner()

    rejected = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    assert rejected["accepted"] is False
    assert runner.calls == []
    assert db.get_autonomous_task_by_id(task_id)["status"] == "failed"
    assert db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    ) == []


def test_supervisor_rejects_fully_rehashed_result_history(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    for _ in range(2):
        assert claim_reddog_signed_worker_dispatch_task_once(
            repo_root=tmp_path,
            signed_worker_runner=_FakeRunner(requeue_required=True),
            authority_verification_context=(
                worker_dispatch_authority_verification_context()
            ),
        )["accepted"] is True

    def forge(context: dict[str, object]) -> None:
        history = context["signed_worker_task_result_receipts"]
        assert isinstance(history, list) and isinstance(history[0], dict)
        history[0]["receipt_digest"] = "sha256:" + ("f" * 64)
        _rechain_context_history(context)

    _rewrite_context(task_id, forge)
    runner = _FakeRunner()
    rejected = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    assert rejected["accepted"] is False
    assert runner.calls == []
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "failed"


def test_direct_run_rejects_rehashed_truncated_result_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    for _ in range(2):
        assert claim_reddog_signed_worker_dispatch_task_once(
            repo_root=tmp_path,
            signed_worker_runner=_FakeRunner(requeue_required=True),
            authority_verification_context=(
                worker_dispatch_authority_verification_context()
            ),
        )["accepted"] is True

    def truncate(context: dict[str, object]) -> None:
        history = context["signed_worker_task_result_receipts"]
        assert isinstance(history, list)
        context["signed_worker_task_result_receipts"] = [history[-1]]
        _rechain_context_history(context)

    _rewrite_context(task_id, truncate)
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    runner = _FakeRunner()
    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=runner,
    )

    assert result["ok"] is False
    assert runner.calls == []
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "failed"


def test_direct_run_preserves_agentdb_anchored_result_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    assert claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(requeue_required=True),
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )["accepted"] is True
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)

    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
    )

    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert result["ok"] is True
    assert stored is not None and stored["status"] == "completed"
    assert len(stored["context"]["signed_worker_task_result_receipts"]) == 2
    rows = db.db.execute_query(
        "SELECT attempt_sequence FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    )
    assert rows == [{"attempt_sequence": 1}, {"attempt_sequence": 2}]


def test_direct_result_ledger_failure_rolls_back_terminal_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setattr(
        execution_store_module,
        "persist_result_history_ledger",
        lambda *_args, **_kwargs: False,
    )

    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
    )

    stored = db.get_autonomous_task_by_id(task_id)
    assert result["ok"] is False
    assert result["detail"] == "reddog_signed_worker_finalization_conflict"
    assert stored is not None and stored["status"] == "executing"
    assert db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    ) == []


def test_public_finalizer_requires_exactly_one_new_result_entry() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    admission = admit_signed_worker_execution_once(db=db, task_id=task_id)
    assert admission is not None
    context = bind_execution_admission(admission.claimed_context, admission)

    with pytest.raises(TypeError):
        execution_store_module.finalize_signed_worker_execution(
            db,
            task_id,
            context=context,
            accepted=False,
        )
    assert execution_store_module.finalize_signed_worker_execution(
        db,
        task_id,
        context=context,
        accepted=False,
        result_context=context,
    ) is False

    stored = db.get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "executing"
    assert db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    ) == []


def test_public_finalizer_rejects_accepted_caller_selected_identity() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    admission = admit_signed_worker_execution_once(db=db, task_id=task_id)
    assert admission is not None
    authenticated = bind_execution_admission(
        admission.claimed_context,
        admission,
    )
    attacker_context = {
        **authenticated,
        "worker_role": "attacker_role",
        "worker_runtime": "hermes",
        "capability": "unbounded_repo_write",
    }
    receipt = build_signed_worker_task_result_receipt(
        base_context=attacker_context,
        claim_status="DIRECT_ACCEPT",
        result={
            "accepted": True,
            "decision": "ATTACKER_ACCEPT",
            "worker_role": "attacker_role",
            "worker_runtime": "hermes",
            "capability": "unbounded_repo_write",
        },
    )
    result_context = append_signed_worker_result_history(
        attacker_context,
        receipt,
    )

    assert execution_store_module.finalize_signed_worker_execution(
        db,
        task_id,
        context=authenticated,
        accepted=True,
        result_context=result_context,
    ) is False
    stored = db.get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "executing"
    assert stored["context"]["worker_role"] == authenticated["worker_role"]
    assert stored["context"]["worker_runtime"] == authenticated["worker_runtime"]
    assert stored["context"]["capability"] == authenticated["capability"]


def test_public_finalizer_rejects_non_genesis_first_history_link() -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    admission = admit_signed_worker_execution_once(db=db, task_id=task_id)
    assert admission is not None
    context = bind_execution_admission(admission.claimed_context, admission)
    receipt = build_signed_worker_task_result_receipt(
        base_context=context,
        claim_status="FORGED_GENESIS",
        result={"accepted": False, "decision": "reject"},
    )
    result_context = append_signed_worker_result_history(context, receipt)
    entry = result_context["signed_worker_task_result_receipts"][0]
    entry["previous_history_digest"] = "sha256:" + ("f" * 64)
    entry_body = {
        key: value for key, value in entry.items()
        if key != "history_entry_digest"
    }
    entry["history_entry_digest"] = _test_digest(entry_body)

    assert execution_store_module.finalize_signed_worker_execution(
        db,
        task_id,
        context=context,
        accepted=False,
        result_context=result_context,
    ) is False

    stored = db.get_autonomous_task_by_id(task_id)
    assert stored is not None and stored["status"] == "executing"
    assert db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    ) == []


def test_supervisor_result_ledger_failure_rolls_back_terminal_state(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    with db.db.get_connection() as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_signed_worker_result_insert
            BEFORE INSERT ON agents_signed_worker_result_history
            BEGIN
                SELECT RAISE(ABORT, 'injected ledger failure');
            END
            """
        )
    runner = _FakeRunner()

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
    )

    stored = db.get_autonomous_task_by_id(task_id)
    assert result["accepted"] is False
    assert (
        SignedWorkerOpenClawClaimReason.RESULT_PERSISTENCE_REJECTED
        in result["rejection_reasons"]
    )
    assert len(runner.calls) == 1
    assert stored is not None and stored["status"] == "executing"
    assert db.db.execute_query(
        "SELECT task_id FROM agents_signed_worker_result_history "
        "WHERE task_id = ?",
        (task_id,),
    ) == []


@pytest.mark.parametrize("authority_failure", ("expired", "revoked"))
def test_claim_rejects_invalid_use_time_authority_before_runner_selection(
    tmp_path: Path,
    authority_failure: str,
) -> None:
    _publish_agentdb_task()
    authority = worker_dispatch_authority_verification_context()
    if authority_failure == "expired":
        authority = replace(authority, trusted_now_epoch=lambda: 2000)
    else:
        authority = replace(
            authority,
            revocation_oracle=SimpleNamespace(is_revoked=lambda **_: True),
        )
    runner = _FakeRunner()

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
        authority_verification_context=authority,
    )

    assert result["accepted"] is False
    assert (
        SignedWorkerOpenClawClaimReason.AGENTDB_ENVELOPE_REJECTED
        in result["rejection_reasons"]
    )
    assert runner.calls == []


@pytest.mark.parametrize(
    "tamper",
    ("source", "required_skills", "all_mutable_markers"),
)
def test_run_task_signed_markers_never_fall_through_to_wre(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    if tamper == "source":
        _rewrite_context(task_id, lambda context: context.update(source="attacker"))
    elif tamper == "required_skills":
        assert db.db.execute_write(
            "UPDATE agents_autonomous_tasks SET required_skills = ? WHERE task_id = ?",
            (json.dumps(["attacker_skill"]), task_id),
        ) == 1
    else:
        _rewrite_context(task_id, lambda context: context.clear())
        assert db.db.execute_write(
            "UPDATE agents_autonomous_tasks "
            "SET required_skills = ?, discovered_by = ? WHERE task_id = ?",
            (json.dumps(["attacker_skill"]), "attacker", task_id),
        ) == 1
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    monkeypatch.setenv(
        "WRE_MOCK_SKILLS",
        f"{runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL},attacker_skill",
    )
    runner = _FakeRunner()

    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=runner,
    )

    assert result["ok"] is False
    assert result["executor"] == "reddog:signed_worker_dispatch"
    assert "routing_binding_mismatch" in result["detail"]
    assert runner.calls == []


def test_competing_preverification_claim_is_never_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    _rewrite_context(task_id, lambda context: context.update(source="attacker"))
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")

    def competing_claim(*, db, task_id):
        assert db.db.execute_write(
            "UPDATE agents_autonomous_tasks SET status = 'executing' "
            "WHERE task_id = ? AND status = 'assigned'",
            (task_id,),
        ) == 1
        return None

    monkeypatch.setattr(
        run_task_runtime,
        "admit_signed_worker_execution_once",
        competing_claim,
    )
    result = execute_task(task_id, repo_root=tmp_path)

    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert result["ok"] is False
    assert result["finalization_owned"] is True
    assert result["executor"] == "reddog:signed_worker_dispatch"
    assert stored is not None and stored["status"] == "executing"


def test_successful_admission_verifies_exact_claimed_database_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    original_admit = run_task_runtime.admit_signed_worker_execution_once

    def replace_then_admit(*, db, task_id):
        assert db.db.execute_write(
            "UPDATE agents_autonomous_tasks "
            "SET context = ?, required_skills = ?, discovered_by = ? "
            "WHERE task_id = ? AND status = 'assigned'",
            (json.dumps({}), json.dumps(["attacker_skill"]), "attacker", task_id),
        ) == 1
        return original_admit(db=db, task_id=task_id)

    monkeypatch.setattr(
        run_task_runtime,
        "admit_signed_worker_execution_once",
        replace_then_admit,
    )
    runner = _FakeRunner()
    result = execute_task(
        task_id,
        repo_root=tmp_path,
        signed_worker_runner=runner,
    )

    stored = AgentDB().get_autonomous_task_by_id(task_id)
    assert result["ok"] is False
    assert result["finalization_owned"] is True
    assert "routing_binding_mismatch" in result["detail"]
    assert runner.calls == []
    assert stored is not None and stored["status"] == "failed"


def test_tampered_expired_verifier_never_renews_assurance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = _publish_agentdb_task(
        intent_id="worker_dispatch_intent_independent_slice_verifier",
        role="independent_slice_verifier",
        worker_runtime="openclaw",
        capability="independent_slice_verification",
    )
    _rewrite_context(
        task_id,
        lambda context: _set_nested(
            context,
            (
                "signed_worker_agentdb_envelope",
                "worker_dispatch_intent",
                "capability",
            ),
            "attacker_capability",
        ),
    )
    db = AgentDB()
    assert db.db.execute_write(
        "UPDATE agents_autonomous_tasks SET status = 'expired' WHERE task_id = ?",
        (task_id,),
    ) == 1
    effects: list[str] = []
    monkeypatch.setattr(
        db,
        "get_independent_assurance_reservation_for_task",
        lambda *_args, **_kwargs: effects.append("reservation-read"),
    )
    monkeypatch.setattr(
        db,
        "renew_independent_assurance",
        lambda *_args, **_kwargs: effects.append("renewal"),
    )
    monkeypatch.setattr(
        supervisor_module,
        "_openclaw_independent_verifier_ready_from_env",
        lambda *_args, **_kwargs: True,
    )

    from modules.communication.moltbot_bridge.src.reddog_signed_worker_claim_admission import (
        rehydrate_signed_worker_agentdb_context,
        renew_expired_verified_assurance,
    )
    from modules.communication.moltbot_bridge.src.reddog_signed_worker_openclaw_queue_loop_runtime_binding import (
        is_openclaw_independent_verifier_signed_worker_context,
    )

    env = {"REDDOG_RESIDENT_QUEUE_NOW_ISO": "2026-07-16T00:00:00+00:00"}
    renew_expired_verified_assurance(
        db=db,
        source=runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        env=env,
        repo_root=tmp_path,
        authority_verification_context=(
            worker_dispatch_authority_verification_context()
        ),
        rehydrate=lambda **kwargs: rehydrate_signed_worker_agentdb_context(
            **kwargs,
            env=env,
        ),
        is_verifier_context=(
            is_openclaw_independent_verifier_signed_worker_context
        ),
        is_stage_ready=(
            supervisor_module._openclaw_independent_verifier_ready_from_env
        ),
    )

    assert effects == []
    assert db.get_autonomous_task_by_id(task_id)["status"] == "expired"
