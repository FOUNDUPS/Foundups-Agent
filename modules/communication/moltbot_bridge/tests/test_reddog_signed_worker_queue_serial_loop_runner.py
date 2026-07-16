"""Tests for REDDOG_SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
    SIGNED_WORKER_DISPATCH_TASK_SOURCE,
    WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_dispatch_task_executor import (
    SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_ACCEPT,
    SignedWorkerDispatchTaskExecutorReason,
    execute_reddog_signed_worker_dispatch_task,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_openclaw_queue_loop_runtime_binding import (
    SIGNED_WORKER_QUEUE_LOOP_BINDING_READY,
    SignedWorkerOpenClawQueueLoopBindingReason,
    build_reddog_signed_worker_queue_loop_runner_from_env,
    is_openclaw_candidate_signed_worker_context,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_queue_serial_loop_runner import (
    RedDogSignedWorkerQueueSerialLoopRunner,
    SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_ACCEPT,
    SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_REJECT,
    SignedWorkerQueueSerialLoopRunnerConfig,
    SignedWorkerQueueSerialLoopRunnerReason,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_signed_worker_queue_serial_loop_runner.py"
)
BINDING_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_signed_worker_openclaw_queue_loop_runtime_binding.py"
)


class _FakeBootstrapResult:
    def __init__(self, payload):
        self._payload = dict(payload)

    def to_dict(self):
        return dict(self._payload)


class _FakeBootstrap:
    def __init__(self, payload=None, *, raises: bool = False):
        self.payload = payload or _bootstrap_payload()
        self.raises = raises
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(dict(kwargs))
        if self.raises:
            raise RuntimeError("bootstrap_failed")
        return _FakeBootstrapResult(self.payload)


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _allocation():
    return {
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


def _context(**intent_overrides):
    allocation = _allocation()
    intent = _intent(allocation, **intent_overrides)
    receipt = {
        "receipt_id": "signed_authority_worker_dispatch_abc",
        "work_order_id": "wo-1",
        "foundup_id": "paccess_001",
        "requested_operation": "create_foundup",
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "wsp15_allocation_digest": _digest(allocation),
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
        "source": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        "schema_version": WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION,
        "queue_item_id": "queue-1",
        "selected_slice": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
        "worker_runtime": intent["worker_runtime"],
        "worker_role": intent["role"],
        "capability": intent["capability"],
        "signed_authority_worker_dispatch_receipt": receipt,
        "worker_dispatch_intent": intent,
        "wsp15_allocation_receipt": allocation,
        "execution_allowed_by_dispatch_runtime": False,
        "requires_downstream_stages": ["work_order_invocation"],
        "report_contract": {
            "worker_process_started": False,
            "repo_mutation_performed": False,
            "hermes_execution_performed": False,
            "requires_signed_authority": True,
        },
    }


def _config(tmp_path: Path) -> SignedWorkerQueueSerialLoopRunnerConfig:
    return SignedWorkerQueueSerialLoopRunnerConfig(
        repo_root=tmp_path / "repo",
        work_state_path=tmp_path / "work_state.json",
        chain_results_path=tmp_path / "chain_results.json",
        authority_profile_path=tmp_path / "authority_profile.json",
        now_iso="2026-07-16T00:00:00+00:00",
        now_epoch=1000,
        max_steps=1,
        bootstrap_kwargs={"work_order_materializer_mode": "authority_profile"},
    )


def _bootstrap_payload(**overrides):
    payload = {
        "accepted": True,
        "status": "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED",
        "queue_item_id": "queue-1",
        "selected_slice": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
        "steps_run": 1,
        "dispatched_stages": ("work_order_invocation",),
        "next_action": "RUN_QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN",
        "chain_results_path": "O:/runtime/chain_results.json",
        "store_revision": "sha256:chain-revision",
        "rejection_reasons": (),
        "no_repo_mutation_performed": True,
        "no_shell_command_executed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_pr_created": True,
        "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
    }
    payload.update(overrides)
    return payload


def test_openclaw_candidate_context_filter_accepts_only_target_capability() -> None:
    assert is_openclaw_candidate_signed_worker_context(_context()) is True
    assert (
        is_openclaw_candidate_signed_worker_context(
            _context(worker_runtime="hermes", capability="candidate_queue_review")
        )
        is False
    )
    assert (
        is_openclaw_candidate_signed_worker_context(
            _context(worker_runtime="openclaw", capability="coding_worker")
        )
        is False
    )


def test_runtime_binding_builds_runner_from_explicit_env(tmp_path: Path) -> None:
    bootstrap = _FakeBootstrap()
    env = {
        "REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER": "1",
        "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(tmp_path / "state.json"),
        "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH": str(tmp_path / "chain.json"),
        "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH": str(tmp_path / "profile.json"),
        "REDDOG_WORK_ORDER_MATERIALIZER_MODE": "authority_profile",
        "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_MAX_STEPS": "1",
        "REDDOG_RESIDENT_QUEUE_NOW_EPOCH": "1000",
    }

    binding = build_reddog_signed_worker_queue_loop_runner_from_env(
        repo_root=tmp_path,
        env=env,
        bootstrap=bootstrap,
    )
    assert binding.accepted is True
    assert binding.status == SIGNED_WORKER_QUEUE_LOOP_BINDING_READY
    assert binding.runner is not None

    result = binding.runner.run_signed_worker_dispatch_task(
        task_id="task-1",
        task_context=_context(),
        worker_dispatch_intent=_context()["worker_dispatch_intent"],
        signed_authority_receipt=_context()["signed_authority_worker_dispatch_receipt"],
        repo_root=tmp_path,
    )

    assert result["accepted"] is True
    assert result["decision"] == SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_ACCEPT
    assert bootstrap.calls[0]["requested_queue_item_id"] == "queue-1"
    assert bootstrap.calls[0]["work_order_materializer_mode"] == "authority_profile"


def test_runtime_binding_rejects_missing_required_paths(tmp_path: Path) -> None:
    binding = build_reddog_signed_worker_queue_loop_runner_from_env(
        repo_root=tmp_path,
        env={"REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER": "1"},
        bootstrap=_FakeBootstrap(),
    )

    assert binding.accepted is False
    assert binding.requested is True
    assert SignedWorkerOpenClawQueueLoopBindingReason.WORK_STATE_PATH_MISSING in binding.rejection_reasons
    assert SignedWorkerOpenClawQueueLoopBindingReason.CHAIN_RESULTS_PATH_MISSING in binding.rejection_reasons
    assert SignedWorkerOpenClawQueueLoopBindingReason.AUTHORITY_PROFILE_PATH_MISSING in binding.rejection_reasons


def test_queue_serial_loop_runner_accepts_openclaw_candidate(tmp_path: Path) -> None:
    bootstrap = _FakeBootstrap()
    runner = RedDogSignedWorkerQueueSerialLoopRunner(_config(tmp_path), bootstrap=bootstrap)

    result = runner.run_signed_worker_dispatch_task(
        task_id="task-1",
        task_context=_context(),
        worker_dispatch_intent=_context()["worker_dispatch_intent"],
        signed_authority_receipt=_context()["signed_authority_worker_dispatch_receipt"],
        repo_root=tmp_path / "repo",
    )

    assert result["accepted"] is True
    assert result["decision"] == SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_ACCEPT
    assert result["queue_item_id"] == "queue-1"
    assert result["receipt_id"]
    assert result["no_source_repo_mutation_performed"] is True
    assert result["no_shell_command_executed"] is True
    assert bootstrap.calls[0]["requested_queue_item_id"] == "queue-1"
    assert bootstrap.calls[0]["max_steps"] == 1
    assert bootstrap.calls[0]["work_order_materializer_mode"] == "authority_profile"


def test_queue_serial_loop_runner_rejects_non_openclaw_worker(tmp_path: Path) -> None:
    context = _context(worker_runtime="0102", role="coding_worker_1", capability="bounded_code_change")
    runner = RedDogSignedWorkerQueueSerialLoopRunner(_config(tmp_path), bootstrap=_FakeBootstrap())

    result = runner.run_signed_worker_dispatch_task(
        task_id="task-1",
        task_context=context,
        worker_dispatch_intent=context["worker_dispatch_intent"],
        signed_authority_receipt=context["signed_authority_worker_dispatch_receipt"],
        repo_root=tmp_path / "repo",
    )

    assert result["accepted"] is False
    assert result["decision"] == SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_REJECT
    assert SignedWorkerQueueSerialLoopRunnerReason.UNSUPPORTED_WORKER_RUNTIME in result["rejection_reasons"]
    assert SignedWorkerQueueSerialLoopRunnerReason.UNSUPPORTED_CAPABILITY in result["rejection_reasons"]


def test_queue_serial_loop_runner_rejects_bootstrap_kwarg_override(tmp_path: Path) -> None:
    config = SignedWorkerQueueSerialLoopRunnerConfig(
        repo_root=tmp_path / "repo",
        work_state_path=tmp_path / "work_state.json",
        chain_results_path=tmp_path / "chain_results.json",
        authority_profile_path=tmp_path / "authority_profile.json",
        bootstrap_kwargs={"requested_queue_item_id": "attacker-queue"},
    )
    runner = RedDogSignedWorkerQueueSerialLoopRunner(config, bootstrap=_FakeBootstrap())
    context = _context()

    result = runner.run_signed_worker_dispatch_task(
        task_id="task-1",
        task_context=context,
        worker_dispatch_intent=context["worker_dispatch_intent"],
        signed_authority_receipt=context["signed_authority_worker_dispatch_receipt"],
        repo_root=tmp_path / "repo",
    )

    assert result["accepted"] is False
    assert SignedWorkerQueueSerialLoopRunnerReason.BOOTSTRAP_KWARG_CONFLICT in result["rejection_reasons"]


def test_queue_serial_loop_runner_rejects_failed_or_unsafe_bootstrap(tmp_path: Path) -> None:
    rejected_runner = RedDogSignedWorkerQueueSerialLoopRunner(
        _config(tmp_path),
        bootstrap=_FakeBootstrap(
            _bootstrap_payload(accepted=False, rejection_reasons=("missing_work_order",))
        ),
    )
    unsafe_runner = RedDogSignedWorkerQueueSerialLoopRunner(
        _config(tmp_path),
        bootstrap=_FakeBootstrap(_bootstrap_payload(no_shell_command_executed=False)),
    )
    context = _context()

    rejected = rejected_runner.run_signed_worker_dispatch_task(
        task_id="task-1",
        task_context=context,
        worker_dispatch_intent=context["worker_dispatch_intent"],
        signed_authority_receipt=context["signed_authority_worker_dispatch_receipt"],
        repo_root=tmp_path / "repo",
    )
    unsafe = unsafe_runner.run_signed_worker_dispatch_task(
        task_id="task-1",
        task_context=context,
        worker_dispatch_intent=context["worker_dispatch_intent"],
        signed_authority_receipt=context["signed_authority_worker_dispatch_receipt"],
        repo_root=tmp_path / "repo",
    )

    assert rejected["accepted"] is False
    assert SignedWorkerQueueSerialLoopRunnerReason.BOOTSTRAP_REJECTED in rejected["rejection_reasons"]
    assert "missing_work_order" in rejected["rejection_reasons"]
    assert unsafe["accepted"] is False
    assert SignedWorkerQueueSerialLoopRunnerReason.BOOTSTRAP_UNSAFE in unsafe["rejection_reasons"]


def test_queue_serial_loop_runner_allows_bounded_isolated_worktree_progress(
    tmp_path: Path,
) -> None:
    runner = RedDogSignedWorkerQueueSerialLoopRunner(
        _config(tmp_path),
        bootstrap=_FakeBootstrap(
            _bootstrap_payload(
                no_repo_mutation_performed=False,
                no_worktree_created=False,
                no_bounded_task_execution_performed=False,
                no_bounded_file_edit_performed=False,
            )
        ),
    )
    context = _context()

    result = runner.run_signed_worker_dispatch_task(
        task_id="task-1",
        task_context=context,
        worker_dispatch_intent=context["worker_dispatch_intent"],
        signed_authority_receipt=context["signed_authority_worker_dispatch_receipt"],
        repo_root=tmp_path / "repo",
    )

    assert result["accepted"] is True
    assert result["decision"] == SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_ACCEPT
    assert result["no_source_repo_mutation_performed"] is True
    assert result["no_shell_command_executed"] is True


def test_signed_worker_executor_accepts_queue_serial_loop_runner(tmp_path: Path) -> None:
    context = _context()
    runner = RedDogSignedWorkerQueueSerialLoopRunner(_config(tmp_path), bootstrap=_FakeBootstrap())

    result = execute_reddog_signed_worker_dispatch_task(
        task_context=context,
        task_id="task-1",
        repo_root=tmp_path / "repo",
        runner=runner,
    )

    assert result.accepted is True
    assert result.decision == SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_ACCEPT
    assert result.runner_result is not None
    assert result.runner_result["decision"] == SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_ACCEPT


def test_signed_worker_executor_rejects_unsupported_queue_runner_target(tmp_path: Path) -> None:
    context = _context(worker_runtime="0102", role="coding_worker_1", capability="bounded_code_change")
    runner = RedDogSignedWorkerQueueSerialLoopRunner(_config(tmp_path), bootstrap=_FakeBootstrap())

    result = execute_reddog_signed_worker_dispatch_task(
        task_context=context,
        task_id="task-1",
        repo_root=tmp_path / "repo",
        runner=runner,
    )

    assert result.accepted is False
    assert SignedWorkerDispatchTaskExecutorReason.RUNNER_REJECTED in result.rejection_reasons
    assert SignedWorkerQueueSerialLoopRunnerReason.UNSUPPORTED_WORKER_RUNTIME in result.rejection_reasons


def test_queue_serial_loop_runner_ast_has_no_shell_network_or_mutation_calls() -> None:
    forbidden_text = (
        "subprocess",
        "requests",
        "holo_index.py --index",
        "create_autonomous_task",
        "complete_autonomous_task",
        "git push",
        "gh pr",
    )
    for path in (MODULE_PATH, BINDING_PATH):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
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
        assert "socket" not in imported
        assert "eval" not in calls
        assert "exec" not in calls
        assert "system" not in attrs
        assert "popen" not in attrs
