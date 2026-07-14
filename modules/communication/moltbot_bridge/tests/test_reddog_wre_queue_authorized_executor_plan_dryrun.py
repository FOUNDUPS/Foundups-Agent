"""Tests for REDDOG_WRE_QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_PHASE1."""

from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_work_order_runtime_invocation import (
    INVOCATION_ACCEPT,
    INVOCATION_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_executor_dryrun import (
    EXECUTOR_PLAN_ACCEPT,
    EXECUTOR_PLAN_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_executor_plan_dryrun import (
    QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
    QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT,
    QueueAuthorizedExecutorPlanDryRunReason,
    plan_reddog_wre_queue_authorized_executor_dryrun,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_verified_authority_work_order_invoke import (
    QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
    QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_wre_queue_authorized_executor_plan_dryrun.py"
)
NOW = datetime(2026, 7, 14, 12, 30, 0, tzinfo=timezone.utc)
WORK_ORDER_ID = "wre-queue-authorized-executor-plan-001"
REPO = "FOUNDUPS/Foundups-Agent"
FID = "paccess_001"
ALLOWED = [f"modules/foundups/{FID}/**"]
DENIED = [".env", ".git/**"]


def _future_expiry(minutes: int = 30) -> str:
    return (NOW + timedelta(minutes=minutes)).replace(microsecond=0).isoformat()


def _fresh_captured() -> str:
    return (NOW - timedelta(seconds=30)).replace(microsecond=0).isoformat()


def _work_order(**overrides):
    payload = {
        "work_order_id": WORK_ORDER_ID,
        "created_at": _fresh_captured(),
        "red_dog_instance_id": "reddog-main-bootstrap",
        "authenticated_principal": "github:mjtrout",
        "principal_provider": "github",
        "repo_full_name": REPO,
        "repo_permission_snapshot": {
            "permission_level": "write",
            "captured_at": _fresh_captured(),
            "source": "mock",
            "digest": "sha256:snap-1",
        },
        "requested_operation": "feature_slice",
        "authority_tier": "source",
        "allowed_paths": ALLOWED,
        "denied_paths": DENIED,
        "branch_name": "feat/paccess-001-executor-plan",
        "base_ref": "main",
        "task_summary": "Plan executor worktree proposal from queue-authorized invocation.",
        "wsp_applicability": ["WSP_34", "WSP_50", "WSP_97"],
        "holoindex_evidence_refs": [
            "modules/communication/moltbot_bridge/src/reddog_wre_executor_dryrun.py"
        ],
        "skillz_candidates": [],
        "required_tests": ["pytest modules/communication/moltbot_bridge/tests"],
        "required_policy_gates": ["openclaw_policy_gate", "signed_work_order_authority"],
        "required_reviewers": [],
        "sentinel_checks": [],
        "rollback_plan": "Remove worktree and delete branch on abort.",
        "expiry": _future_expiry(),
        "nonce": "work-order-nonce-executor-plan",
        "evidence_digest": "sha256:" + ("a" * 64),
        "advisory_only_source_packet": {
            "work_focus_digest": "sha256:" + ("b" * 64),
            "wsp_prompt_digest": "sha256:" + ("c" * 64),
            "copy_md_run_trace_digest": "sha256:" + ("d" * 64),
        },
        "holoindex_evidence": {
            "holoindex_query": "RedDog queue authorized executor plan dryrun",
            "holoindex_status": "bundle_json_ok",
            "code_hits": ["modules/communication/moltbot_bridge/src/reddog_wre_executor_dryrun.py"],
            "wsp_hits": ["WSP_framework/src/WSP_34_Git_Operations_Protocol.md"],
            "skillz_hits": [],
            "direct_read_fallback_used": True,
            "index_gap_detected": False,
            "applicable_wsps": ["WSP_34", "WSP_97"],
            "evidence_refs": ["modules/communication/moltbot_bridge/src/reddog_wre_executor_dryrun.py"],
            "retrieval_quality": "HIGH",
            "skillz_gap_detected": False,
        },
    }
    payload.update(overrides)
    return payload


def _invocation_result(**overrides):
    payload = {
        "decision": INVOCATION_ACCEPT,
        "work_order_id": WORK_ORDER_ID,
        "policy_gate_decision": "POLICY_ACCEPT",
        "receipt_id": "reddog-work-order-receipt-001",
        "receipt_digest": "sha256:" + ("e" * 64),
        "no_execution_performed": True,
        "rejection_reasons": [],
        "gates_checked": ["signed_work_order_authority"],
        "idempotent_replay": False,
        "policy_gate_receipt_digest": "sha256:" + ("f" * 64),
    }
    payload.update(overrides)
    return payload


def _queue_work_order_result(**overrides):
    payload = {
        "decision": QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
        "rejection_reasons": [],
        "invocation_result": _invocation_result(),
        "explicit_queue_work_order_invocation_requested": True,
        "no_worker_spawn_performed": True,
        "no_worktree_created": True,
        "no_shell_command_executed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_pr_created": True,
        "no_reward_settlement_performed": True,
    }
    payload.update(overrides)
    return payload


def test_accepted_queue_work_order_invocation_builds_executor_plan() -> None:
    result = plan_reddog_wre_queue_authorized_executor_dryrun(
        explicit_queue_authorized_executor_plan_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(),
        work_order=_work_order(),
        now=NOW,
        repo_root="/repo/Foundups-Agent",
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT
    assert result.rejection_reasons == []
    assert result.executor_plan_result is not None
    assert result.executor_plan_result.decision == EXECUTOR_PLAN_ACCEPT
    assert result.executor_plan_result.plan is not None
    assert result.executor_plan_result.plan.work_order_id == WORK_ORDER_ID
    assert result.executor_plan_result.plan.invocation_receipt_digest == "sha256:" + ("e" * 64)
    assert result.executor_plan_result.plan.no_mutation_performed is True
    assert "/.reddog/worktrees/" in result.executor_plan_result.plan.proposed_worktree_path
    assert result.no_execution_valve_opened is True
    assert result.no_worktree_created is True
    assert result.no_shell_command_executed is True
    assert result.no_repo_mutation_performed is True
    assert result.no_holoindex_reindex_performed is True


def test_explicit_dryrun_missing_rejects() -> None:
    result = plan_reddog_wre_queue_authorized_executor_dryrun(
        explicit_queue_authorized_executor_plan_requested=False,
        queue_work_order_invocation_result=_queue_work_order_result(),
        work_order=_work_order(),
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT
    assert QueueAuthorizedExecutorPlanDryRunReason.EXPLICIT_DRYRUN_MISSING in result.rejection_reasons
    assert result.executor_plan_result is None


def test_queue_work_order_invocation_not_accepted_rejects() -> None:
    result = plan_reddog_wre_queue_authorized_executor_dryrun(
        explicit_queue_authorized_executor_plan_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(
            decision=QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT,
            rejection_reasons=["authority_missing"],
        ),
        work_order=_work_order(),
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT
    assert (
        QueueAuthorizedExecutorPlanDryRunReason.WORK_ORDER_INVOCATION_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert result.executor_plan_result is None


def test_missing_invocation_payload_rejects() -> None:
    result = plan_reddog_wre_queue_authorized_executor_dryrun(
        explicit_queue_authorized_executor_plan_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(invocation_result=None),
        work_order=_work_order(),
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT
    assert QueueAuthorizedExecutorPlanDryRunReason.INVOCATION_PAYLOAD_MISSING in result.rejection_reasons
    assert result.executor_plan_result is None


def test_rejected_invocation_payload_is_preserved_as_executor_reject() -> None:
    result = plan_reddog_wre_queue_authorized_executor_dryrun(
        explicit_queue_authorized_executor_plan_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(
            invocation_result=_invocation_result(
                decision=INVOCATION_REJECT,
                rejection_reasons=["policy_rejected"],
            )
        ),
        work_order=_work_order(),
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT
    assert QueueAuthorizedExecutorPlanDryRunReason.EXECUTOR_PLAN_NOT_ACCEPTED in result.rejection_reasons
    assert "invocation_rejected" in result.rejection_reasons
    assert result.executor_plan_result is not None
    assert result.executor_plan_result.decision == EXECUTOR_PLAN_REJECT


def test_protected_branch_rejection_is_preserved() -> None:
    result = plan_reddog_wre_queue_authorized_executor_dryrun(
        explicit_queue_authorized_executor_plan_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(),
        work_order=_work_order(branch_name="main"),
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT
    assert QueueAuthorizedExecutorPlanDryRunReason.EXECUTOR_PLAN_NOT_ACCEPTED in result.rejection_reasons
    assert "protected_branch_forbidden" in result.rejection_reasons


def test_lock_collision_rejection_is_preserved() -> None:
    result = plan_reddog_wre_queue_authorized_executor_dryrun(
        explicit_queue_authorized_executor_plan_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(),
        work_order=_work_order(),
        now=NOW,
        locks={WORK_ORDER_ID},
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT
    assert QueueAuthorizedExecutorPlanDryRunReason.EXECUTOR_PLAN_NOT_ACCEPTED in result.rejection_reasons
    assert "lock_collision" in result.rejection_reasons


def test_result_is_json_serializable() -> None:
    result = plan_reddog_wre_queue_authorized_executor_dryrun(
        explicit_queue_authorized_executor_plan_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(),
        work_order=_work_order(),
        now=NOW,
    )

    payload = result.to_dict()
    assert payload["decision"] == QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT
    assert payload["executor_plan_result"]["decision"] == EXECUTOR_PLAN_ACCEPT
    json.dumps(payload)


def test_module_has_no_execution_valve_worktree_shell_or_holoindex_imports() -> None:
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
        "evaluate_reddog_execution_valve(",
        "create_reddog_wre_worktree(",
        "git ",
        "gh ",
        "worktree add",
        "openclaw_supervisor",
        "hermes_job_executor",
        "holo_index.py --index",
    )
    for token in forbidden_tokens:
        assert token not in source
