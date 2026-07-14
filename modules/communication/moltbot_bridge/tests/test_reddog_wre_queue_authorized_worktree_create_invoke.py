"""Tests for REDDOG_WRE_QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_PHASE1."""

from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_execution_valve_invoke import (
    QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_executor_plan_dryrun import (
    QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
    QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_worktree_create_invoke import (
    QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT,
    QueueAuthorizedWorktreeCreateInvokeReason,
    invoke_reddog_wre_queue_authorized_worktree_create,
)
from modules.communication.moltbot_bridge.src.reddog_wre_worktree_create import (
    WORKTREE_CREATE_ACCEPT,
    WORKTREE_CREATE_REJECT,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_wre_queue_authorized_worktree_create_invoke.py"
)
NOW = datetime(2026, 7, 14, 13, 30, 0, tzinfo=timezone.utc)
WORK_ORDER_ID = "wre-queue-authorized-worktree-001"
FID = "paccess_001"
INVOCATION_DIGEST = "sha256:" + ("e" * 64)
PLAN_DIGEST = "sha256:" + ("1" * 64)
VALVE_DIGEST = "sha256:" + ("2" * 64)


class FakeRunner:
    def __init__(self, *, ok: bool = True, raises: bool = False) -> None:
        self.ok = ok
        self.raises = raises
        self.calls: list[tuple[str, str, str | None, str | None]] = []

    def create_worktree(self, *, worktree_path, branch_name, base_ref):
        self.calls.append(("create_worktree", str(worktree_path), branch_name, base_ref))
        if self.raises:
            raise RuntimeError("simulated create failure")
        if self.ok:
            Path(worktree_path).mkdir(parents=True, exist_ok=True)
        return {"ok": self.ok, "returncode": 0 if self.ok else 1}

    def cleanup_worktree(self, *, worktree_path):
        self.calls.append(("cleanup_worktree", str(worktree_path), None, None))
        return {"ok": True}


def _future_expiry(minutes: int = 30) -> str:
    return (NOW + timedelta(minutes=minutes)).replace(microsecond=0).isoformat()


def _fresh_captured() -> str:
    return (NOW - timedelta(seconds=30)).replace(microsecond=0).isoformat()


def _worktree_path(repo_root: Path) -> str:
    return str(repo_root.parent / ".reddog" / "worktrees" / repo_root.name / WORK_ORDER_ID / "nonce")


def _work_order(**overrides):
    payload = {
        "work_order_id": WORK_ORDER_ID,
        "created_at": _fresh_captured(),
        "red_dog_instance_id": "reddog-main-bootstrap",
        "authenticated_principal": "github:mjtrout",
        "principal_provider": "github",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "repo_permission_snapshot": {
            "permission_level": "write",
            "captured_at": _fresh_captured(),
            "source": "mock",
            "digest": "sha256:snap-1",
        },
        "requested_operation": "feature_slice",
        "authority_tier": "source",
        "allowed_paths": [f"modules/foundups/{FID}/**"],
        "denied_paths": [".env", ".git/**"],
        "branch_name": "feat/paccess-001-worktree",
        "base_ref": "main",
        "task_summary": "Create isolated worktree from queue-authorized valve.",
        "wsp_applicability": ["WSP_34", "WSP_50", "WSP_97"],
        "holoindex_evidence_refs": [
            "modules/communication/moltbot_bridge/src/reddog_wre_worktree_create.py"
        ],
        "skillz_candidates": [],
        "required_tests": ["pytest modules/communication/moltbot_bridge/tests"],
        "required_policy_gates": ["openclaw_policy_gate", "signed_work_order_authority"],
        "required_reviewers": [],
        "sentinel_checks": [],
        "rollback_plan": "Remove worktree and delete branch on abort.",
        "expiry": _future_expiry(),
        "nonce": "work-order-nonce-worktree",
        "evidence_digest": "sha256:" + ("a" * 64),
        "advisory_only_source_packet": {
            "work_focus_digest": "sha256:" + ("b" * 64),
            "wsp_prompt_digest": "sha256:" + ("c" * 64),
            "copy_md_run_trace_digest": "sha256:" + ("d" * 64),
        },
        "holoindex_evidence": {
            "holoindex_query": "RedDog queue authorized worktree create",
            "holoindex_status": "bundle_json_ok",
            "code_hits": ["modules/communication/moltbot_bridge/src/reddog_wre_worktree_create.py"],
            "wsp_hits": ["WSP_framework/src/WSP_34_Git_Operations_Protocol.md"],
            "skillz_hits": [],
            "direct_read_fallback_used": True,
            "index_gap_detected": False,
            "applicable_wsps": ["WSP_34", "WSP_97"],
            "evidence_refs": [
                "modules/communication/moltbot_bridge/src/reddog_wre_worktree_create.py"
            ],
            "retrieval_quality": "HIGH",
            "skillz_gap_detected": False,
        },
    }
    payload.update(overrides)
    return payload


def _executor_payload(repo_root: Path, **overrides):
    payload = {
        "decision": "EXECUTOR_PLAN_ACCEPT",
        "work_order_id": WORK_ORDER_ID,
        "plan": {
            "plan_id": "plan-001",
            "work_order_id": WORK_ORDER_ID,
            "proposed_branch_name": "feat/paccess-001-worktree",
            "proposed_worktree_path": _worktree_path(repo_root),
            "lock_key": WORK_ORDER_ID,
            "allowed_paths": [f"modules/foundups/{FID}/**"],
            "denied_paths": [".env", ".git/**"],
            "required_tests": ["pytest modules/communication/moltbot_bridge/tests"],
            "cleanup_plan": {"on_failure": "remove_worktree_delete_branch"},
            "phase_receipts": [],
            "no_mutation_performed": True,
            "invocation_receipt_digest": INVOCATION_DIGEST,
            "plan_digest": PLAN_DIGEST,
        },
        "rejection_reasons": [],
        "rejection_receipt_digest": "",
        "no_mutation_performed": True,
        "phase_receipts": [],
    }
    payload.update(overrides)
    return payload


def _queue_executor_result(repo_root: Path, **overrides):
    payload = {
        "decision": QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
        "rejection_reasons": [],
        "executor_plan_result": _executor_payload(repo_root),
        "explicit_queue_authorized_executor_plan_requested": True,
    }
    payload.update(overrides)
    return payload


def _queue_valve_result(**overrides):
    payload = {
        "decision": QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT,
        "rejection_reasons": [],
        "valve_decision": {
            "valve_state": "VALVE_OPEN_WORKTREE_CREATE",
            "work_order_id": WORK_ORDER_ID,
            "rejection_reasons": [],
            "gates_checked": ["execution_valve_evaluator"],
            "no_execution_performed": True,
            "decision_digest": VALVE_DIGEST,
            "intake_target": "foundup_job",
        },
        "explicit_queue_authorized_execution_valve_requested": True,
    }
    payload.update(overrides)
    return payload


def _repo_root(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    return repo_root


def test_queue_authorized_chain_creates_isolated_worktree_only(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    runner = FakeRunner()
    result = invoke_reddog_wre_queue_authorized_worktree_create(
        explicit_queue_authorized_worktree_create_requested=True,
        queue_executor_plan_result=_queue_executor_result(repo_root),
        queue_execution_valve_result=_queue_valve_result(),
        work_order=_work_order(),
        runner=runner,
        repo_root=repo_root,
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT
    assert result.rejection_reasons == []
    assert result.worktree_create_result is not None
    assert result.worktree_create_result.decision == WORKTREE_CREATE_ACCEPT
    assert result.no_task_execution_performed is True
    assert result.no_file_edit_performed is True
    assert result.no_shell_command_executed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_pr_created is True
    assert result.no_reward_settlement_performed is True
    assert result.no_holoindex_reindex_performed is True
    assert [call[0] for call in runner.calls] == ["create_worktree"]
    assert Path(result.worktree_create_result.worktree_path).exists()


def test_explicit_invoke_missing_rejects() -> None:
    repo_root = Path.cwd()
    result = invoke_reddog_wre_queue_authorized_worktree_create(
        explicit_queue_authorized_worktree_create_requested=False,
        queue_executor_plan_result=_queue_executor_result(repo_root),
        queue_execution_valve_result=_queue_valve_result(),
        work_order=_work_order(),
        runner=FakeRunner(),
        repo_root=repo_root,
    )

    assert result.decision == QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT
    assert QueueAuthorizedWorktreeCreateInvokeReason.EXPLICIT_INVOKE_MISSING in result.rejection_reasons
    assert result.worktree_create_result is None


def test_runner_required_rejects_before_side_effect() -> None:
    repo_root = Path.cwd()
    result = invoke_reddog_wre_queue_authorized_worktree_create(
        explicit_queue_authorized_worktree_create_requested=True,
        queue_executor_plan_result=_queue_executor_result(repo_root),
        queue_execution_valve_result=_queue_valve_result(),
        work_order=_work_order(),
        runner=None,
        repo_root=repo_root,
    )

    assert result.decision == QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT
    assert QueueAuthorizedWorktreeCreateInvokeReason.RUNNER_REQUIRED in result.rejection_reasons
    assert result.worktree_create_result is None


def test_rejected_executor_plan_blocks_before_worktree_create() -> None:
    repo_root = Path.cwd()
    runner = FakeRunner()
    result = invoke_reddog_wre_queue_authorized_worktree_create(
        explicit_queue_authorized_worktree_create_requested=True,
        queue_executor_plan_result=_queue_executor_result(
            repo_root, decision=QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT
        ),
        queue_execution_valve_result=_queue_valve_result(),
        work_order=_work_order(),
        runner=runner,
        repo_root=repo_root,
    )

    assert result.decision == QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT
    assert QueueAuthorizedWorktreeCreateInvokeReason.EXECUTOR_PLAN_NOT_ACCEPTED in result.rejection_reasons
    assert runner.calls == []


def test_rejected_valve_blocks_before_worktree_create() -> None:
    repo_root = Path.cwd()
    runner = FakeRunner()
    result = invoke_reddog_wre_queue_authorized_worktree_create(
        explicit_queue_authorized_worktree_create_requested=True,
        queue_executor_plan_result=_queue_executor_result(repo_root),
        queue_execution_valve_result=_queue_valve_result(
            decision=QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
        ),
        work_order=_work_order(),
        runner=runner,
        repo_root=repo_root,
    )

    assert result.decision == QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT
    assert QueueAuthorizedWorktreeCreateInvokeReason.VALVE_NOT_ACCEPTED in result.rejection_reasons
    assert runner.calls == []


def test_inside_repo_path_rejects_before_runner(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    executor = _executor_payload(repo_root)
    executor["plan"] = dict(executor["plan"])
    executor["plan"]["proposed_worktree_path"] = str(repo_root / ".reddog" / WORK_ORDER_ID)
    runner = FakeRunner()
    result = invoke_reddog_wre_queue_authorized_worktree_create(
        explicit_queue_authorized_worktree_create_requested=True,
        queue_executor_plan_result=_queue_executor_result(repo_root, executor_plan_result=executor),
        queue_execution_valve_result=_queue_valve_result(),
        work_order=_work_order(),
        runner=runner,
        repo_root=repo_root,
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT
    assert QueueAuthorizedWorktreeCreateInvokeReason.WORKTREE_CREATE_NOT_ACCEPTED in result.rejection_reasons
    assert "worktree_path_inside_repo_root" in result.rejection_reasons
    assert runner.calls == []
    assert result.worktree_create_result is not None
    assert result.worktree_create_result.decision == WORKTREE_CREATE_REJECT


def test_lock_collision_rejects_before_runner(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    runner = FakeRunner()
    result = invoke_reddog_wre_queue_authorized_worktree_create(
        explicit_queue_authorized_worktree_create_requested=True,
        queue_executor_plan_result=_queue_executor_result(repo_root),
        queue_execution_valve_result=_queue_valve_result(),
        work_order=_work_order(),
        runner=runner,
        repo_root=repo_root,
        locks={WORK_ORDER_ID},
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT
    assert "lock_collision" in result.rejection_reasons
    assert runner.calls == []


def test_create_failure_preserves_cleanup_result(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    runner = FakeRunner(ok=False)
    result = invoke_reddog_wre_queue_authorized_worktree_create(
        explicit_queue_authorized_worktree_create_requested=True,
        queue_executor_plan_result=_queue_executor_result(repo_root),
        queue_execution_valve_result=_queue_valve_result(),
        work_order=_work_order(),
        runner=runner,
        repo_root=repo_root,
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT
    assert QueueAuthorizedWorktreeCreateInvokeReason.WORKTREE_CREATE_NOT_ACCEPTED in result.rejection_reasons
    assert "worktree_create_failed" in result.rejection_reasons
    assert [call[0] for call in runner.calls] == ["create_worktree", "cleanup_worktree"]


def test_result_is_json_serializable(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    result = invoke_reddog_wre_queue_authorized_worktree_create(
        explicit_queue_authorized_worktree_create_requested=True,
        queue_executor_plan_result=_queue_executor_result(repo_root),
        queue_execution_valve_result=_queue_valve_result(),
        work_order=_work_order(),
        runner=FakeRunner(),
        repo_root=repo_root,
        now=NOW,
    )

    payload = result.to_dict()
    assert payload["decision"] == QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT
    assert payload["worktree_create_result"]["decision"] == WORKTREE_CREATE_ACCEPT
    json.dumps(payload)


def test_module_has_no_shell_openclaw_hermes_pr_reward_or_holoindex_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "holo_index",
        "git",
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls

    source = MODULE_PATH.read_text(encoding="utf-8")
    forbidden_tokens = (
        "RealRedDogWorktreeRunner",
        "git ",
        "gh ",
        "openclaw_supervisor",
        "hermes_job_executor",
        "create_pull_request",
        "settle_reward",
        "holo_index.py --index",
    )
    for token in forbidden_tokens:
        assert token not in source
