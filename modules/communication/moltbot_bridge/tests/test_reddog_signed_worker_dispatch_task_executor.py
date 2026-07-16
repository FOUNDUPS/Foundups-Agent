"""Tests for REDDOG_SIGNED_WORKER_TASK_OPENCLAW_CLAIM_RUNTIME_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import json
import sqlite3
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
from modules.communication.moltbot_bridge.tests.test_reddog_main_resident_queue_serial_loop_bootstrap import (
    NOW as BOOTSTRAP_NOW,
    PILOT_ARTIFACT,
    PILOT_OPERATION,
    REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    _draft_pr_publish_request,
    _ed25519_signing_material,
    _FakeWorkerDispatchTaskWriter,
    _FakeWorktreeRunner,
    _held_out_gate_request,
    _outcome_ratchet_request,
    _pattern_memory_admission_request,
    _pilot_allowed_paths,
    _pilot_path_overrides,
    _pilot_payloads,
    _pilot_worktree_path,
    _principals,
    _profile as _bootstrap_profile,
    _repo,
    _slice_verifier_request,
    _snapshot as _bootstrap_snapshot,
    _snapshots,
    _run_bootstrap_to_held_out_regression_gate,
    _run_bootstrap_to_verified_outcome_ratchet,
    _valve_environment,
    _work_order,
    _write_runtime_json,
    run_reddog_main_resident_queue_serial_loop_bootstrap,
)
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
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


class _FakeEnvDraftPrRunner:
    instances: list["_FakeEnvDraftPrRunner"] = []

    def __init__(self, *, repo_root: Path, timeout_s: int) -> None:
        self.repo_root = Path(repo_root)
        self.timeout_s = timeout_s
        self.calls: list[tuple[str, ...]] = []
        self.__class__.instances.append(self)

    def push_branch(self, *, worktree_path: Path, branch_name: str):
        self.calls.append(("push_branch", str(worktree_path), branch_name))
        return {"ok": True, "branch_name": branch_name}

    def create_draft_pr(self, *, branch_name: str, base_branch: str, title: str, body: str):
        self.calls.append(("create_draft_pr", branch_name, base_branch, title, body))
        return "https://github.com/FOUNDUPS/Foundups-Agent/pull/4242"


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


def test_openclaw_claim_env_bound_queue_loop_runner_materializes_bounded_artifact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _bootstrap_snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _bootstrap_profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(**pilot_overrides)
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {str(work_order["work_order_id"]): work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    worktree_runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)

    seed = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=worktree_runner,
        now_iso=BOOTSTRAP_NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=9,
    )
    assert seed.accepted is True
    assert seed.dispatched_stages[-1] == "worktree_create"
    assert worktree.exists()
    assert not (worktree / PILOT_ARTIFACT).exists()

    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        pilot_payloads["artifact_contents"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )

    task_id = _publish_agentdb_task()
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
    monkeypatch.setenv("REDDOG_GENERIC_WRITER_DRYRUN_RESULT_PATH", str(generic_writer))
    monkeypatch.setenv("REDDOG_GOVERNED_SHELL_DRYRUN_RESULT_PATH", str(governed_shell))
    monkeypatch.setenv("REDDOG_ARTIFACT_CONTENTS_PATH", str(artifacts))
    monkeypatch.setenv("REDDOG_HOLOINDEX_EVIDENCE_PATH", str(holoindex))
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=repo)

    assert result["accepted"] is True, json.dumps(result, sort_keys=True)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == task_id
    assert result["worker_runtime"] == "openclaw"
    assert result["capability"] == "candidate_queue_review"
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "completed"

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["bounded_worker_pilot"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT"
    assert stage["bounded_task_execution_performed"] is True
    assert stage["bounded_file_edit_performed"] is True
    assert stage["shell_command_executed"] is False
    assert stage["openclaw_enqueue_performed"] is False
    assert stage["hermes_dispatch_performed"] is False
    assert stage["holoindex_reindex_performed"] is False
    assert (worktree / PILOT_ARTIFACT).read_text(encoding="utf-8").startswith(
        "# Resident Queue Pilot"
    )
    assert not (repo / PILOT_ARTIFACT).exists()


def test_openclaw_claim_env_bound_queue_loop_runner_reaches_slice_verifier(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _bootstrap_snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _bootstrap_profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(**pilot_overrides)
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {str(work_order["work_order_id"]): work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    worktree_runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)
    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        pilot_payloads["artifact_contents"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )
    verifier = _write_runtime_json(
        tmp_path,
        "verifier_request.json",
        _slice_verifier_request(),
    )

    seed = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=worktree_runner,
        now_iso=BOOTSTRAP_NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=10,
    )
    assert seed.accepted is True
    assert seed.dispatched_stages[-1] == "bounded_worker_pilot"
    assert (worktree / PILOT_ARTIFACT).exists()

    task_id = _publish_agentdb_task()
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
    monkeypatch.setenv("REDDOG_SLICE_VERIFIER_REQUEST_PATH", str(verifier))
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=repo)

    assert result["accepted"] is True, json.dumps(result, sort_keys=True)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == task_id
    assert result["worker_runtime"] == "openclaw"
    assert result["capability"] == "candidate_queue_review"
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "completed"

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["slice_verifier"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT"
    assert stage["verifier_result"]["decision"] == AUTONOMOUS_SLICE_VERIFIER_ACCEPT
    assert stage["verifier_result"]["receipt"]["changed_paths"] == [PILOT_ARTIFACT]
    assert stage["no_command_execution_performed"] is True
    assert stage["no_github_call_performed"] is True
    assert stage["no_pr_publish_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_pattern_memory_write_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True
    assert (worktree / PILOT_ARTIFACT).exists()
    assert not (repo / PILOT_ARTIFACT).exists()


def test_openclaw_claim_env_bound_queue_loop_runner_reaches_verified_draft_pr_publish(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from modules.foundups.agent.src import worktree_pr_runner

    _FakeEnvDraftPrRunner.instances.clear()
    monkeypatch.setattr(worktree_pr_runner, "RealWorktreeRunner", _FakeEnvDraftPrRunner)
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _bootstrap_snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _bootstrap_profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(**pilot_overrides)
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {str(work_order["work_order_id"]): work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    worktree_runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)
    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        pilot_payloads["artifact_contents"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )
    verifier = _write_runtime_json(
        tmp_path,
        "verifier_request.json",
        _slice_verifier_request(),
    )
    publish_request = _write_runtime_json(
        tmp_path,
        "publish_request.json",
        _draft_pr_publish_request(worktree),
    )

    seed = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        verifier_request_path=verifier,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=worktree_runner,
        now_iso=BOOTSTRAP_NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=11,
    )
    assert seed.accepted is True
    assert seed.dispatched_stages[-1] == "slice_verifier"

    task_id = _publish_agentdb_task()
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
    monkeypatch.setenv("REDDOG_DRAFT_PR_PUBLISH_REQUEST_PATH", str(publish_request))
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_MODE", "real")
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S", "88")
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=repo)

    assert result["accepted"] is True, json.dumps(result, sort_keys=True)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == task_id
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "completed"
    assert len(_FakeEnvDraftPrRunner.instances) == 1
    draft_runner = _FakeEnvDraftPrRunner.instances[0]
    assert draft_runner.repo_root == repo.resolve()
    assert draft_runner.timeout_s == 88
    assert [call[0] for call in draft_runner.calls] == ["push_branch", "create_draft_pr"]

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["verified_draft_pr_publish"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT"
    assert stage["publish_result"]["decision"] == "VERIFIED_DRAFT_PR_PUBLISH_ACCEPT"
    assert stage["no_ready_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_pattern_memory_write_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True


def test_openclaw_claim_env_bound_queue_loop_runner_reaches_verified_outcome_ratchet(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _bootstrap_snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _bootstrap_profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(**pilot_overrides)
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {str(work_order["work_order_id"]): work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    worktree_runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)
    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        pilot_payloads["artifact_contents"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )
    verifier = _write_runtime_json(
        tmp_path,
        "verifier_request.json",
        _slice_verifier_request(),
    )
    publish_request = _write_runtime_json(
        tmp_path,
        "publish_request.json",
        _draft_pr_publish_request(worktree),
    )
    draft_runner = _FakeEnvDraftPrRunner(repo_root=repo, timeout_s=88)

    seed = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        verifier_request_path=verifier,
        publish_request_path=publish_request,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=worktree_runner,
        draft_pr_runner=draft_runner,
        now_iso=BOOTSTRAP_NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=12,
    )
    assert seed.accepted is True
    assert seed.dispatched_stages[-1] == "verified_draft_pr_publish"
    seeded = json.loads(chain.read_text(encoding="utf-8"))
    verifier_stage = seeded["stage_results"]["slice_verifier"]
    publish_stage = seeded["stage_results"]["verified_draft_pr_publish"]
    assert publish_stage["publish_result"]["decision"] == "VERIFIED_DRAFT_PR_PUBLISH_ACCEPT"

    ratchet_request = _write_runtime_json(
        tmp_path,
        "ratchet_request.json",
        _outcome_ratchet_request(verifier_stage["verifier_result"]),
    )
    outcome_store = tmp_path / "runtime" / "outcomes" / "signed-worker-ratchet.jsonl"
    task_id = _publish_agentdb_task()
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
    monkeypatch.setenv("REDDOG_OUTCOME_RATCHET_REQUEST_PATH", str(ratchet_request))
    monkeypatch.setenv("REDDOG_OUTCOME_RATCHET_STORE_PATH", str(outcome_store))
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=repo)

    assert result["accepted"] is True, json.dumps(result, sort_keys=True)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == task_id
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "completed"

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["verified_outcome_ratchet"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT"
    assert stage["ratchet_result"]["decision"] == "OUTCOME_RATCHET_RECORDED"
    assert stage["ratchet_result"]["receipt"]["pattern_memory_write_performed"] is False
    assert stage["no_command_execution_performed"] is True
    assert stage["no_pr_publish_performed"] is True
    assert stage["no_ready_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True
    assert "held_out_regression_gate" not in stored["stage_results"]

    records = [
        json.loads(line)
        for line in outcome_store.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 1
    assert records[0]["ratchet_receipt"]["work_order_id"] == work_order["work_order_id"]
    assert records[0]["publish_result"]["decision"] == "VERIFIED_DRAFT_PR_PUBLISH_ACCEPT"
    assert not (repo / "runtime" / "outcomes" / "signed-worker-ratchet.jsonl").exists()


def test_openclaw_claim_env_bound_queue_loop_runner_reaches_held_out_regression_gate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    ctx = _run_bootstrap_to_verified_outcome_ratchet(tmp_path)
    verifier_stage = ctx["verifier_stage"]
    held_out_request = _write_runtime_json(
        tmp_path,
        "held_out_gate_request.json",
        _held_out_gate_request(verifier_stage["verifier_result"]),
    )
    task_id = _publish_agentdb_task()
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(ctx["state"]))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(ctx["chain"]))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(ctx["profile"]))
    monkeypatch.setenv("REDDOG_HELD_OUT_GATE_REQUEST_PATH", str(held_out_request))
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=ctx["repo"])

    assert result["accepted"] is True, json.dumps(result, sort_keys=True)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == task_id
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "completed"

    stored = json.loads(Path(ctx["chain"]).read_text(encoding="utf-8"))
    stage = stored["stage_results"]["held_out_regression_gate"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT"
    assert (
        stage["gate_result"]["decision"]
        == "HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT"
    )
    assert stage["gate_result"]["receipt"]["no_pattern_memory_write_performed"] is True
    assert stage["no_command_execution_performed"] is True
    assert stage["no_test_execution_performed"] is True
    assert stage["no_pattern_memory_write_performed"] is True
    assert stage["no_pr_publish_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True
    assert "pattern_memory_admission" not in stored["stage_results"]


def test_openclaw_claim_env_bound_queue_loop_runner_reaches_pattern_memory_admission(
    tmp_path: Path,
    monkeypatch,
) -> None:
    ctx = _run_bootstrap_to_held_out_regression_gate(tmp_path)
    admission_request = _write_runtime_json(
        tmp_path,
        "pattern_memory_admission_request.json",
        _pattern_memory_admission_request(),
    )
    pattern_memory_db = tmp_path / "runtime" / "pattern_memory.db"
    task_id = _publish_agentdb_task()
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(ctx["state"]))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(ctx["chain"]))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(ctx["profile"]))
    monkeypatch.setenv("REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_PATH", str(admission_request))
    monkeypatch.setenv("REDDOG_PATTERN_MEMORY_ADMISSION_DB_PATH", str(pattern_memory_db))
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=ctx["repo"])

    assert result["accepted"] is True, json.dumps(result, sort_keys=True)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == task_id
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "completed"

    stored = json.loads(Path(ctx["chain"]).read_text(encoding="utf-8"))
    stage = stored["stage_results"]["pattern_memory_admission"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT"
    assert stage["pattern_memory_write_performed"] is True
    assert stage["receipt"]["pattern_memory_record_id"].startswith("reddog_verified_outcome_")
    assert stage["no_command_execution_performed"] is True
    assert stage["no_pr_publish_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True

    with sqlite3.connect(pattern_memory_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM skill_outcomes").fetchone()[0]
        execution_id = conn.execute(
            "SELECT execution_id FROM skill_outcomes LIMIT 1"
        ).fetchone()[0]
    assert count == 1
    assert execution_id == stage["receipt"]["pattern_memory_record_id"]
    assert not (ctx["repo"] / "runtime" / "pattern_memory.db").exists()


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
