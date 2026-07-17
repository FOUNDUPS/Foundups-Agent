"""Tests for REDDOG_OPENCLAW_HERMES_0102_WORKER_DISPATCH_RUNTIME_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_openclaw_hermes_0102_worker_dispatch_runtime as runtime,
)
from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT,
)
from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_openclaw_hermes_0102_worker_dispatch_runtime.py"
)


@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    DatabaseManager.reset_for_tests()
    yield
    DatabaseManager.reset_for_tests()


class _FakeWriter:
    def __init__(self, *, ok=True, created_override=None) -> None:
        self.ok = ok
        self.created_override = created_override
        self.calls = []

    def enqueue_signed_worker_dispatch_tasks(self, tasks, receipt):
        self.calls.append((list(tasks), receipt))
        if not self.ok:
            return {"ok": False, "reason": "writer_rejected", "created_task_ids": []}
        created = self.created_override
        if created is None:
            created = [task.task_id for task in tasks]
        return {"ok": True, "created_task_ids": created}


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _allocation(**overrides):
    payload = {
        "schema_version": "reddog_wsp15_allocation_receipt.v1",
        "receipt_id": "sha256:wsp15-allocation",
        "mps_total": 20,
        "priority": "P0",
        "reasoning_tier": "ULTRA",
        "worker_plan": {
            "schema_version": "reddog_wsp15_worker_plan.v1",
            "fusion_required": True,
            "reasoning_tier": "ULTRA",
            "critic_count": 1,
            "coding_worker_count": 1,
            "independent_verifier_required": True,
            "openclaw_candidate": True,
            "hermes_execution_allowed": False,
            "queue_mutation_allowed": False,
            "mode_selection_source": "reddog_wsp15_allocation_receipt.v1",
        },
    }
    payload.update(overrides)
    return payload


def _intent(role: str, runtime_name: str, capability: str, allocation=None, **overrides):
    allocation = allocation or _allocation()
    payload = {
        "intent_id": f"worker_dispatch_intent_{role}",
        "role": role,
        "worker_runtime": runtime_name,
        "capability": capability,
        "work_order_id": "wo-1",
        "foundup_id": "paccess_001",
        "requested_operation": "create_foundup",
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "wsp15_allocation_digest": _digest(allocation),
        "dry_run_only": True,
        "no_worker_spawn_performed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
    }
    payload.update(overrides)
    return payload


def _dryrun_result(allocation=None, intents=None, **overrides):
    allocation = allocation or _allocation()
    intents = intents or (
        _intent("fusion_lead", "0102", "architect_review", allocation),
        _intent("coding_worker_1", "0102", "bounded_code_change", allocation),
        _intent("queue_stage_worker", "openclaw", "queue_stage_progress", allocation),
    )
    receipt = {
        "receipt_id": "signed_authority_worker_dispatch_abc",
        "work_order_id": "wo-1",
        "foundup_id": "paccess_001",
        "requested_operation": "create_foundup",
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "wsp15_allocation_digest": _digest(allocation),
        "wsp15_priority": allocation["priority"],
        "wsp15_mps_total": allocation["mps_total"],
        "wsp15_reasoning_tier": allocation["reasoning_tier"],
        "dispatch_intent_count": len(intents),
        "dispatch_intents": list(intents),
        "no_worker_spawn_performed": True,
        "no_queue_mutation_performed": True,
        "no_worktree_created": True,
        "no_shell_command_executed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
    }
    payload = {
        "accepted": True,
        "decision": SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT,
        "rejection_reasons": [],
        "receipt": receipt,
    }
    payload.update(overrides)
    return payload


def _snapshot(allocation=None):
    allocation = allocation or _allocation()
    return {
        "schema_version": "reddog_authoritative_work_state.v1",
        "wre_queue_items": [
            {
                "queue_item_id": "queue-1",
                "slice_id": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
                "status": "QUEUED",
                "wsp15_allocation_receipt": allocation,
            }
        ],
    }


def test_publishes_signed_worker_dispatch_intents_as_pending_tasks() -> None:
    writer = _FakeWriter()

    result = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(),
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=writer,
        now=datetime(2026, 7, 16, tzinfo=timezone.utc),
    )

    assert result.accepted is True
    assert result.decision == runtime.SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT
    assert result.receipt is not None
    assert result.receipt.agentdb_tasks_enqueued is True
    assert result.receipt.no_worker_process_started is True
    assert result.receipt.no_hermes_execution_performed is True
    assert len(result.tasks) == 3
    assert writer.calls and len(writer.calls[0][0]) == 3
    assert {task.context["worker_runtime"] for task in result.tasks} == {"0102", "openclaw"}
    assert all(task.context["execution_allowed_by_dispatch_runtime"] is False for task in result.tasks)
    assert all(runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL in task.required_skills for task in result.tasks)


def test_agentdb_writer_publishes_tasks_atomically() -> None:
    result = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(),
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=runtime.AgentDbSignedWorkerDispatchTaskWriter(),
    )

    assert result.accepted is True
    pending = AgentDB().get_autonomous_tasks(status="pending", limit=10)
    assert len(pending) == 3
    assert {task["task_id"] for task in pending} == set(result.receipt.task_ids)
    for task in pending:
        assert task["context"]["source"] == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
        assert task["context"]["requires_downstream_stages"]
        assert task["context"]["report_contract"]["requires_signed_authority"] is True


def test_agentdb_writer_rejects_duplicate_without_second_batch() -> None:
    writer = runtime.AgentDbSignedWorkerDispatchTaskWriter()
    first = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(),
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=writer,
    )
    second = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(),
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert first.accepted is True
    assert second.accepted is False
    assert second.rejection_reasons == (runtime.WorkerDispatchRuntimeReason.WRITER_REJECTED,)
    assert len(AgentDB().get_autonomous_tasks(status="pending", limit=10)) == 3


def test_rejects_missing_writer_and_unaccepted_dryrun() -> None:
    missing_writer = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(),
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=None,
    )
    rejected_dryrun = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result={"accepted": False, "decision": "NO"},
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=_FakeWriter(),
    )

    assert missing_writer.accepted is False
    assert runtime.WorkerDispatchRuntimeReason.WRITER_MISSING in missing_writer.rejection_reasons
    assert rejected_dryrun.accepted is False
    assert runtime.WorkerDispatchRuntimeReason.DRYRUN_NOT_ACCEPTED in rejected_dryrun.rejection_reasons


def test_rejects_unsafe_intent_before_writer_call() -> None:
    allocation = _allocation()
    bad_intent = _intent(
        "coding_worker_1",
        "0102",
        "bounded_code_change",
        allocation,
        no_worker_spawn_performed=False,
    )
    writer = _FakeWriter()

    result = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(allocation, intents=(bad_intent,)),
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert result.accepted is False
    assert runtime.WorkerDispatchRuntimeReason.INTENT_UNSAFE in result.rejection_reasons
    assert writer.calls == []


def test_rejects_wsp15_queue_binding_mismatch_and_seen_replay() -> None:
    allocation = _allocation()
    other = _allocation(receipt_id="sha256:other-allocation")
    mismatch = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(allocation),
        work_state_snapshot=_snapshot(other),
        queue_item_id="queue-1",
        writer=_FakeWriter(),
    )
    replay = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(allocation),
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=_FakeWriter(),
        seen_intent_ids={"worker_dispatch_intent_fusion_lead"},
    )

    assert mismatch.accepted is False
    assert runtime.WorkerDispatchRuntimeReason.WSP15_BINDING_MISMATCH in mismatch.rejection_reasons
    assert replay.accepted is False
    assert runtime.WorkerDispatchRuntimeReason.IDEMPOTENCY_REPLAY in replay.rejection_reasons


def test_result_is_deterministic_and_json_serializable() -> None:
    first = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(),
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=_FakeWriter(),
        now=datetime(2026, 7, 16, tzinfo=timezone.utc),
    )
    second = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(),
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=_FakeWriter(),
        now=datetime(2026, 7, 16, tzinfo=timezone.utc),
    )

    assert first.receipt is not None and second.receipt is not None
    assert first.receipt.receipt_digest == second.receipt.receipt_digest
    json.dumps(first.to_dict(), sort_keys=True)


def test_module_ast_boundaries() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_text = (
        "subprocess",
        "requests",
        "hermes_job_executor",
        "worktree_pr_runner",
        "git push",
        "gh pr",
        "holo_index.py --index",
        "run_task.py",
        "pattern_memory_sink",
    )
    for token in forbidden_text:
        assert token not in source

    imported = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    assert not (imported & {"subprocess", "requests", "socket", "urllib", "shutil"})
    assert not (calls & {"eval", "exec", "compile", "system", "popen", "run", "Popen"})
