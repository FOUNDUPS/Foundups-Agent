"""Tests for REDDOG_SIGNED_WORKER_TASK_OPENCLAW_CLAIM_RUNTIME_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.scripts.run_task import execute_task
from modules.communication.moltbot_bridge.src import (
    reddog_openclaw_hermes_0102_worker_dispatch_runtime as runtime,
)
from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
    OpenClawSupervisor,
    SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT,
    SIGNED_WORKER_OPENCLAW_CLAIM_IDLE,
    SIGNED_WORKER_OPENCLAW_CLAIM_REJECT,
    SignedWorkerOpenClawClaimReason,
    claim_reddog_signed_worker_dispatch_task_once,
)
from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_dispatch_task_executor import (
    SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_ACCEPT,
    SignedWorkerDispatchTaskExecutorReason,
    execute_reddog_signed_worker_dispatch_task,
)
from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager


REPO_ROOT = Path(__file__).resolve().parents[4]
EXECUTOR_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_signed_worker_dispatch_task_executor.py"
)


@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    DatabaseManager.reset_for_tests()
    yield
    DatabaseManager.reset_for_tests()


class _FakeRunner:
    def __init__(self, *, accepted: bool = True, unsafe: bool = False) -> None:
        self.accepted = accepted
        self.unsafe = unsafe
        self.calls = []

    def run_signed_worker_dispatch_task(
        self,
        *,
        task_id,
        task_context,
        worker_dispatch_intent,
        signed_authority_receipt,
        repo_root,
    ):
        self.calls.append(
            {
                "task_id": task_id,
                "task_context": dict(task_context),
                "worker_dispatch_intent": dict(worker_dispatch_intent),
                "signed_authority_receipt": dict(signed_authority_receipt),
                "repo_root": Path(repo_root),
            }
        )
        return {
            "accepted": self.accepted,
            "receipt_id": "fake-signed-worker-runner-receipt",
            "rejection_reasons": [] if self.accepted else ["runner_declined"],
            "no_source_repo_mutation_performed": not self.unsafe,
            "no_shell_command_executed": not self.unsafe,
        }


class _FakeBinding:
    def __init__(self, runner) -> None:
        self.accepted = True
        self.requested = True
        self.runner = runner
        self.rejection_reasons = ()

    def to_dict(self):
        return {
            "accepted": self.accepted,
            "requested": self.requested,
            "runner": "FakeRunner",
            "rejection_reasons": list(self.rejection_reasons),
        }


class _CollectingWriter:
    def enqueue_signed_worker_dispatch_tasks(self, tasks, receipt):
        return {
            "ok": True,
            "created_task_ids": [task.task_id for task in tasks],
        }


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


def _intent(allocation=None, **overrides):
    allocation = allocation or _allocation()
    payload = {
        "intent_id": "worker_dispatch_intent_openclaw_candidate",
        "role": "openclaw_candidate",
        "worker_runtime": "openclaw",
        "capability": "candidate_queue_review",
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


def _dryrun_result(allocation=None, intent=None):
    allocation = allocation or _allocation()
    intent = intent or _intent(allocation)
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
        "dispatch_intent_count": 1,
        "dispatch_intents": [intent],
        "no_worker_spawn_performed": True,
        "no_queue_mutation_performed": True,
        "no_worktree_created": True,
        "no_shell_command_executed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
    }
    return {
        "accepted": True,
        "decision": SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT,
        "rejection_reasons": [],
        "receipt": receipt,
    }


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


def _task_context():
    result = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(),
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=_CollectingWriter(),
    )
    assert result.accepted is True
    task = result.tasks[0]
    return dict(task.context)


def _publish_agentdb_task(**intent_overrides) -> str:
    allocation = _allocation()
    intent = _intent(allocation, **intent_overrides)
    result = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(allocation=allocation, intent=intent),
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=runtime.AgentDbSignedWorkerDispatchTaskWriter(),
    )
    assert result.accepted is True
    assert result.receipt is not None
    return result.receipt.task_ids[0]


def test_signed_worker_executor_accepts_valid_task_with_injected_runner(tmp_path: Path) -> None:
    runner = _FakeRunner()

    result = execute_reddog_signed_worker_dispatch_task(
        task_context=_task_context(),
        task_id="task-1",
        repo_root=tmp_path,
        runner=runner,
    )

    assert result.accepted is True
    assert result.decision == SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_ACCEPT
    assert result.worker_runtime == "openclaw"
    assert result.capability == "candidate_queue_review"
    assert result.no_shell_command_executed is True
    assert result.no_source_repo_mutation_performed is True
    assert runner.calls[0]["worker_dispatch_intent"]["intent_id"] == "worker_dispatch_intent_openclaw_candidate"


def test_signed_worker_executor_rejects_without_runner(tmp_path: Path) -> None:
    result = execute_reddog_signed_worker_dispatch_task(
        task_context=_task_context(),
        task_id="task-1",
        repo_root=tmp_path,
        runner=None,
    )

    assert result.accepted is False
    assert SignedWorkerDispatchTaskExecutorReason.RUNNER_MISSING in result.rejection_reasons


def test_signed_worker_executor_rejects_tampered_receipt_and_wsp15(tmp_path: Path) -> None:
    context = _task_context()
    context["signed_authority_worker_dispatch_receipt"] = dict(
        context["signed_authority_worker_dispatch_receipt"]
    )
    context["signed_authority_worker_dispatch_receipt"]["dispatch_intents"] = []
    context["worker_dispatch_intent"] = dict(context["worker_dispatch_intent"])
    context["worker_dispatch_intent"]["wsp15_allocation_digest"] = "sha256:tampered"

    result = execute_reddog_signed_worker_dispatch_task(
        task_context=context,
        task_id="task-1",
        repo_root=tmp_path,
        runner=_FakeRunner(),
    )

    assert result.accepted is False
    assert SignedWorkerDispatchTaskExecutorReason.INTENT_NOT_IN_RECEIPT in result.rejection_reasons
    assert SignedWorkerDispatchTaskExecutorReason.WSP15_MISMATCH in result.rejection_reasons


def test_signed_worker_executor_rejects_unsafe_runner(tmp_path: Path) -> None:
    result = execute_reddog_signed_worker_dispatch_task(
        task_context=_task_context(),
        task_id="task-1",
        repo_root=tmp_path,
        runner=_FakeRunner(unsafe=True),
    )

    assert result.accepted is False
    assert SignedWorkerDispatchTaskExecutorReason.RUNNER_UNSAFE in result.rejection_reasons


def test_run_task_routes_signed_worker_before_wre_fallback(tmp_path: Path, monkeypatch) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)

    result = execute_task(task_id, repo_root=tmp_path, signed_worker_runner=_FakeRunner())

    assert result["ok"] is True
    assert result["executor"] == "reddog:signed_worker_dispatch"
    assert result["structured_result"]["accepted"] is True
    assert db.get_autonomous_task_by_id(task_id)["status"] == "completed"


def test_run_task_rejects_signed_worker_without_runner_instead_of_wre_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)

    result = execute_task(task_id, repo_root=tmp_path)

    assert result["ok"] is False
    assert result["executor"] == "reddog:signed_worker_dispatch"
    assert SignedWorkerDispatchTaskExecutorReason.RUNNER_MISSING in result["detail"]
    assert db.get_autonomous_task_by_id(task_id)["status"] == "failed"


def test_run_task_uses_env_bound_queue_loop_runner_when_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")

    from modules.communication.moltbot_bridge.src import (
        reddog_signed_worker_openclaw_queue_loop_runtime_binding as binding_module,
    )

    runner = _FakeRunner()
    monkeypatch.setattr(
        binding_module,
        "build_reddog_signed_worker_queue_loop_runner_from_env",
        lambda *, repo_root, env: _FakeBinding(runner),
    )

    result = execute_task(task_id, repo_root=tmp_path)

    assert result["ok"] is True
    assert result["executor"] == "reddog:signed_worker_dispatch"
    assert result["structured_result"]["accepted"] is True
    assert runner.calls[0]["task_id"] == task_id
    assert db.get_autonomous_task_by_id(task_id)["status"] == "completed"


def test_openclaw_claims_signed_worker_task_once_and_completes_it(tmp_path: Path) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
    )

    assert result["accepted"] is True
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == task_id
    assert result["worker_runtime"] == "openclaw"
    assert result["receipt_id"]
    assert db.get_autonomous_task_by_id(task_id)["status"] == "completed"


def test_openclaw_claim_ignores_non_openclaw_signed_worker_task(tmp_path: Path) -> None:
    task_id = _publish_agentdb_task(
        intent_id="worker_dispatch_intent_hermes_candidate",
        role="hermes_candidate",
        worker_runtime="hermes",
        capability="bounded_code_change",
    )
    db = AgentDB()

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
    )

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_IDLE
    assert SignedWorkerOpenClawClaimReason.NO_PENDING_TASK in result["rejection_reasons"]
    assert db.get_autonomous_task_by_id(task_id)["status"] == "pending"


def test_openclaw_supervisor_instance_claims_signed_worker_task(tmp_path: Path) -> None:
    task_id = _publish_agentdb_task()
    supervisor = OpenClawSupervisor(repo_root=tmp_path)

    result = supervisor.claim_reddog_signed_worker_dispatch_task_once(
        signed_worker_runner=_FakeRunner(),
    )

    assert result["accepted"] is True
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == task_id
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "completed"


def test_openclaw_claim_rejects_without_runner_and_idle_when_empty(tmp_path: Path) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()

    rejected = claim_reddog_signed_worker_dispatch_task_once(repo_root=tmp_path)
    idle = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
    )

    assert rejected["accepted"] is False
    assert rejected["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REJECT
    assert SignedWorkerOpenClawClaimReason.TASK_EXECUTION_REJECTED in rejected["rejection_reasons"]
    assert SignedWorkerDispatchTaskExecutorReason.RUNNER_MISSING in rejected["rejection_reasons"]
    assert db.get_autonomous_task_by_id(task_id)["status"] == "failed"
    assert idle["accepted"] is False
    assert idle["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_IDLE


def test_signed_worker_executor_ast_has_no_shell_network_or_runtime_mutation() -> None:
    source = EXECUTOR_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_text = (
        "subprocess",
        "requests",
        "socket",
        "holo_index.py --index",
        "create_autonomous_task",
        "complete_autonomous_task",
        "git push",
        "gh pr",
    )
    for token in forbidden_text:
        assert token not in source

    imported = set()
    calls = set()
    attrs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                calls.add(func.id)
            elif isinstance(func, ast.Attribute):
                attrs.add(func.attr)

    assert "subprocess" not in imported
    assert "requests" not in imported
    assert "eval" not in calls
    assert "exec" not in calls
    assert "system" not in attrs
    assert "popen" not in attrs
