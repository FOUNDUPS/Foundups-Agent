"""Tests for RedDog WRE execution valve evaluator."""

from __future__ import annotations

import ast
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_work_order_receipt import (
    RedDogWorkOrderReceiptStore,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_runtime_invocation import (
    invoke_reddog_work_order_dryrun,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    INTAKE_ASSIGNMENT_DISPATCHER,
    INTAKE_AUTONOMOUS_TASK,
    INTAKE_FOUNDUP_JOB,
    VALVE_CLOSED,
    VALVE_OPEN_DRYRUN_ONLY,
    VALVE_OPEN_LIVE_ENQUEUE,
    VALVE_OPEN_WORKTREE_CREATE,
    ExecutionValveEnvironment,
    ExecutionValveRequest,
    evaluate_reddog_execution_valve,
)
from modules.communication.moltbot_bridge.src.reddog_wre_executor_dryrun import (
    plan_wre_isolated_worktree_execution_dryrun,
)


def _future_expiry(hours: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


def _fresh_captured() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _base_order(**overrides):
    payload = {
        "work_order_id": "wo-valve-001",
        "created_at": _fresh_captured(),
        "red_dog_instance_id": "reddog-ext-0.3.28",
        "authenticated_principal": "principal-012",
        "principal_provider": "github",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "repo_permission_snapshot": {
            "permission_level": "write",
            "captured_at": _fresh_captured(),
            "source": "mock",
            "digest": "sha256:" + ("a" * 64),
        },
        "requested_operation": "feature_slice",
        "authority_tier": "source",
        "allowed_paths": ["modules/communication/moltbot_bridge/**"],
        "denied_paths": [".env"],
        "branch_name": "feat/reddog-valve-test",
        "base_ref": "main",
        "task_summary": "Execution valve validation",
        "wsp_applicability": ["WSP_34", "WSP_50", "WSP_97"],
        "holoindex_evidence_refs": [
            "docs/audits/architecture/REDDOG_WRE_EXECUTION_VALVE_CONTRACT_PHASE1.md",
        ],
        "skillz_candidates": [],
        "required_tests": [
            "modules/communication/moltbot_bridge/tests/test_reddog_wre_execution_valve.py"
        ],
        "required_policy_gates": ["openclaw_policy_gate"],
        "required_reviewers": [],
        "sentinel_checks": [],
        "rollback_plan": "Remove worktree and delete branch on abort.",
        "expiry": _future_expiry(),
        "nonce": "nonce-valve-001",
        "evidence_digest": "sha256:" + ("b" * 64),
        "advisory_only_source_packet": {
            "work_focus_digest": "sha256:" + ("c" * 64),
            "wsp_prompt_digest": "sha256:" + ("d" * 64),
            "copy_md_run_trace_digest": "sha256:" + ("e" * 64),
        },
        "holoindex_evidence": {
            "holoindex_query": "RedDog execution valve",
            "holoindex_status": "bundle_json_ok",
            "code_hits": [],
            "wsp_hits": ["WSP_framework/src/WSP_34_Git_Operations_Protocol.md"],
            "skillz_hits": [],
            "direct_read_fallback_used": False,
            "index_gap_detected": False,
            "applicable_wsps": ["WSP_34"],
            "evidence_refs": [
                "docs/audits/architecture/REDDOG_WRE_EXECUTION_VALVE_CONTRACT_PHASE1.md"
            ],
            "retrieval_quality": "HIGH",
            "skillz_gap_detected": False,
        },
    }
    payload.update(overrides)
    return payload


def _full_spine_bundle(*, order=None):
    order = order or _base_order()
    with tempfile.TemporaryDirectory() as tmp:
        with RedDogWorkOrderReceiptStore(Path(tmp) / "receipts.db") as store:
            invocation = invoke_reddog_work_order_dryrun(
                order,
                permission_snapshot={
                    "permission_level": "write",
                    "captured_at": _fresh_captured(),
                    "source": "mock",
                    "digest": order["repo_permission_snapshot"]["digest"],
                },
                seen_nonces=set(),
                receipt_store=store,
            )
    executor = plan_wre_isolated_worktree_execution_dryrun(invocation, order)
    policy_receipt = {
        "decision": "POLICY_ACCEPT",
        "receipt_digest": invocation.policy_gate_receipt_digest,
        "no_execution_performed": True,
        "work_order_id": order["work_order_id"],
    }
    work_order_receipt = {
        "receipt_id": invocation.receipt_id,
        "receipt_digest": invocation.receipt_digest,
        "policy_gate_receipt_digest": invocation.policy_gate_receipt_digest,
        "no_execution_performed": True,
        "work_order_id": order["work_order_id"],
    }
    return order, policy_receipt, work_order_receipt, invocation, executor


def _request_from_spine(
    order,
    policy_receipt,
    work_order_receipt,
    invocation,
    executor,
    *,
    intake_target=INTAKE_FOUNDUP_JOB,
    **flags,
):
    return ExecutionValveRequest(
        work_order=order,
        policy_gate_receipt=policy_receipt,
        reddog_work_order_receipt=work_order_receipt,
        invocation_result=invocation.to_dict(),
        executor_plan_result=executor.to_dict(),
        intake_target=intake_target,
        permission_snapshot=order["repo_permission_snapshot"],
        **flags,
    )


class TestValveDefaultClosed:
    def test_default_closed_without_explicit_flag(self):
        order, policy, receipt, invocation, executor = _full_spine_bundle()
        req = _request_from_spine(order, policy, receipt, invocation, executor)
        decision = evaluate_reddog_execution_valve(req, ExecutionValveEnvironment())
        assert decision.valve_state == VALVE_CLOSED
        assert "explicit_valve_flag_missing" in decision.rejection_reasons
        assert decision.no_execution_performed is True
        assert len(decision.decision_digest) == 64


class TestValveOpenPaths:
    def test_explicit_dryrun_only_opens_dryrun_state(self):
        order, policy, receipt, invocation, executor = _full_spine_bundle()
        req = _request_from_spine(order, policy, receipt, invocation, executor)
        env = ExecutionValveEnvironment(valve_dryrun_enabled=True)
        decision = evaluate_reddog_execution_valve(req, env)
        assert decision.valve_state == VALVE_OPEN_DRYRUN_ONLY
        assert decision.rejection_reasons == []

    def test_worktree_create_requires_stronger_valve_and_token(self):
        order, policy, receipt, invocation, executor = _full_spine_bundle()
        req = _request_from_spine(order, policy, receipt, invocation, executor)
        env = ExecutionValveEnvironment(valve_worktree_create_enabled=True)
        decision = evaluate_reddog_execution_valve(req, env)
        assert decision.valve_state == VALVE_CLOSED
        assert "worktree_valve_missing_sovereign_token" in decision.rejection_reasons

    def test_live_enqueue_requires_live_enqueue_token(self):
        order, policy, receipt, invocation, executor = _full_spine_bundle()
        req = _request_from_spine(order, policy, receipt, invocation, executor)
        env = ExecutionValveEnvironment(valve_live_enqueue_enabled=True)
        decision = evaluate_reddog_execution_valve(req, env)
        assert decision.valve_state == VALVE_CLOSED
        assert "live_enqueue_valve_missing_sovereign_token" in decision.rejection_reasons

    def test_live_enqueue_with_token_opens_live_enqueue_state(self):
        order, policy, receipt, invocation, executor = _full_spine_bundle()
        req = _request_from_spine(order, policy, receipt, invocation, executor)
        env = ExecutionValveEnvironment(
            valve_live_enqueue_enabled=True,
            sovereign_live_enqueue_token="012-sovereign-live-enqueue-token",
        )
        decision = evaluate_reddog_execution_valve(req, env)
        assert decision.valve_state == VALVE_OPEN_LIVE_ENQUEUE
        assert decision.rejection_reasons == []

    def test_worktree_create_with_token_opens(self):
        order, policy, receipt, invocation, executor = _full_spine_bundle()
        req = _request_from_spine(order, policy, receipt, invocation, executor)
        env = ExecutionValveEnvironment(
            valve_worktree_create_enabled=True,
            sovereign_worktree_token="012-sovereign-valve-token",
        )
        decision = evaluate_reddog_execution_valve(req, env)
        assert decision.valve_state == VALVE_OPEN_WORKTREE_CREATE
        assert decision.rejection_reasons == []


class TestValveRejections:
    def test_missing_receipt_chain_rejects(self):
        order, policy, receipt, invocation, executor = _full_spine_bundle()
        policy = dict(policy)
        policy["receipt_digest"] = ""
        req = _request_from_spine(order, policy, receipt, invocation, executor)
        env = ExecutionValveEnvironment(valve_dryrun_enabled=True)
        decision = evaluate_reddog_execution_valve(req, env)
        assert decision.valve_state == VALVE_CLOSED
        assert "missing_policy_gate_receipt_digest" in decision.rejection_reasons

    def test_stale_permission_rejects(self):
        order, policy, receipt, invocation, executor = _full_spine_bundle()
        stale = (datetime.now(timezone.utc) - timedelta(hours=2)).replace(microsecond=0).isoformat()
        order = dict(order)
        order["repo_permission_snapshot"] = {
            "permission_level": "write",
            "captured_at": stale,
            "source": "mock",
            "digest": "sha256:" + ("a" * 64),
        }
        req = _request_from_spine(order, policy, receipt, invocation, executor)
        req = ExecutionValveRequest(
            work_order=order,
            policy_gate_receipt=policy,
            reddog_work_order_receipt=receipt,
            invocation_result=invocation.to_dict(),
            executor_plan_result=executor.to_dict(),
            intake_target=INTAKE_FOUNDUP_JOB,
            permission_snapshot=order["repo_permission_snapshot"],
        )
        env = ExecutionValveEnvironment(valve_dryrun_enabled=True, permission_ttl_seconds=300)
        decision = evaluate_reddog_execution_valve(req, env)
        assert decision.valve_state == VALVE_CLOSED
        assert "stale_permission_snapshot" in decision.rejection_reasons

    def test_assignment_dispatcher_target_rejects(self):
        order, policy, receipt, invocation, executor = _full_spine_bundle()
        req = _request_from_spine(
            order, policy, receipt, invocation, executor, intake_target=INTAKE_ASSIGNMENT_DISPATCHER
        )
        env = ExecutionValveEnvironment(valve_dryrun_enabled=True)
        decision = evaluate_reddog_execution_valve(req, env)
        assert decision.valve_state == VALVE_CLOSED
        assert "assignment_dispatcher_forbidden_target" in decision.rejection_reasons

    def test_direct_worker_and_model_launch_reject(self):
        order, policy, receipt, invocation, executor = _full_spine_bundle()
        req = _request_from_spine(
            order,
            policy,
            receipt,
            invocation,
            executor,
            direct_worker_launch=True,
            direct_model_launch=True,
        )
        env = ExecutionValveEnvironment(valve_dryrun_enabled=True)
        decision = evaluate_reddog_execution_valve(req, env)
        assert decision.valve_state == VALVE_CLOSED
        assert "direct_worker_launch_forbidden" in decision.rejection_reasons
        assert "direct_model_launch_forbidden" in decision.rejection_reasons

    def test_autonomous_task_target_passes_with_valve(self):
        order, policy, receipt, invocation, executor = _full_spine_bundle()
        req = _request_from_spine(
            order, policy, receipt, invocation, executor, intake_target=INTAKE_AUTONOMOUS_TASK
        )
        env = ExecutionValveEnvironment(valve_dryrun_enabled=True)
        decision = evaluate_reddog_execution_valve(req, env)
        assert decision.valve_state == VALVE_OPEN_DRYRUN_ONLY
        assert decision.intake_target == INTAKE_AUTONOMOUS_TASK


class TestNoExecutionBoundary:
    def test_no_execution_performed_always(self):
        order, policy, receipt, invocation, executor = _full_spine_bundle()
        req = _request_from_spine(order, policy, receipt, invocation, executor)
        for env in (
            ExecutionValveEnvironment(),
            ExecutionValveEnvironment(valve_dryrun_enabled=True),
            ExecutionValveEnvironment(
                valve_worktree_create_enabled=True,
                sovereign_worktree_token="token",
            ),
        ):
            decision = evaluate_reddog_execution_valve(req, env)
            assert decision.no_execution_performed is True

    def test_decision_json_serializable(self):
        order, policy, receipt, invocation, executor = _full_spine_bundle()
        req = _request_from_spine(order, policy, receipt, invocation, executor)
        decision = evaluate_reddog_execution_valve(
            req, ExecutionValveEnvironment(valve_dryrun_enabled=True)
        )
        json.dumps(decision.to_dict())

    def test_ast_denylist(self):
        module_path = (
            Path(__file__).resolve().parents[1] / "src" / "reddog_wre_execution_valve.py"
        )
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        forbidden = [
            name
            for name in imported
            if any(
                token in name
                for token in ("subprocess", "github_integration", "wre_core", "skillz")
            )
        ]
        assert forbidden == []
        for token in (
            "import subprocess",
            "git worktree",
            "worktree add",
            "create_branch",
            "merge_pull_request",
            "git ",
            "gh ",
            "os.mkdir",
            "Path.mkdir",
            "execute_skill",
            "hermes_job_executor",
            "openclaw_supervisor",
        ):
            assert token not in source
