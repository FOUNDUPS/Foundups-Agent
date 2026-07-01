"""Tests for RedDog OpenClaw FoundUpJob adapter dry-run planner."""

from __future__ import annotations

import ast
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_openclaw_adapter_dryrun import (
    ADAPTER_DRYRUN_ACCEPT,
    ADAPTER_DRYRUN_REJECT,
    plan_reddog_openclaw_adapter_dryrun,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    INTAKE_ASSIGNMENT_DISPATCHER,
    INTAKE_AUTONOMOUS_TASK,
    INTAKE_FOUNDUP_JOB,
    VALVE_CLOSED,
    VALVE_OPEN_DRYRUN_ONLY,
    VALVE_OPEN_WORKTREE_CREATE,
    ExecutionValveEnvironment,
    ExecutionValveRequest,
    evaluate_reddog_execution_valve,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_receipt import (
    RedDogWorkOrderReceiptStore,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_runtime_invocation import (
    invoke_reddog_work_order_dryrun,
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
        "work_order_id": "wo-adapter-dryrun-001",
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
        "branch_name": "feat/reddog-adapter-dryrun-test",
        "base_ref": "main",
        "task_summary": "Adapter dry-run validation slice",
        "wsp_applicability": ["WSP_34", "WSP_50", "WSP_97"],
        "holoindex_evidence_refs": [
            "docs/audits/architecture/REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_CONTRACT_PHASE1.md",
        ],
        "skillz_candidates": [],
        "required_tests": [
            "modules/communication/moltbot_bridge/tests/test_reddog_openclaw_adapter_dryrun.py"
        ],
        "required_policy_gates": ["openclaw_policy_gate"],
        "required_reviewers": [],
        "sentinel_checks": [],
        "rollback_plan": "Remove worktree and delete branch on abort.",
        "expiry": _future_expiry(),
        "nonce": "nonce-adapter-dryrun-001",
        "evidence_digest": "sha256:" + ("b" * 64),
        "advisory_only_source_packet": {
            "work_focus_digest": "sha256:" + ("c" * 64),
            "wsp_prompt_digest": "sha256:" + ("d" * 64),
            "copy_md_run_trace_digest": "sha256:" + ("e" * 64),
        },
        "holoindex_evidence": {
            "holoindex_query": "RedDog OpenClaw adapter dryrun",
            "holoindex_status": "bundle_json_ok",
            "code_hits": [],
            "wsp_hits": ["WSP_framework/src/WSP_34_Git_Operations_Protocol.md"],
            "skillz_hits": [],
            "direct_read_fallback_used": False,
            "index_gap_detected": False,
            "applicable_wsps": ["WSP_34"],
            "evidence_refs": [
                "docs/audits/architecture/REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_CONTRACT_PHASE1.md"
            ],
            "retrieval_quality": "HIGH",
            "skillz_gap_detected": False,
        },
    }
    payload.update(overrides)
    return payload


def _full_spine_with_open_valve(*, order=None, intake_target=INTAKE_FOUNDUP_JOB):
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
    valve_request = ExecutionValveRequest(
        work_order=order,
        policy_gate_receipt=policy_receipt,
        reddog_work_order_receipt=work_order_receipt,
        invocation_result=invocation.to_dict(),
        executor_plan_result=executor.to_dict(),
        intake_target=intake_target,
        permission_snapshot=order["repo_permission_snapshot"],
    )
    valve = evaluate_reddog_execution_valve(
        valve_request, ExecutionValveEnvironment(valve_dryrun_enabled=True)
    )
    assert valve.valve_state == VALVE_OPEN_DRYRUN_ONLY
    return order, policy_receipt, work_order_receipt, invocation, executor, valve


class TestAdapterDryRunAccept:
    def test_foundup_job_proposed_with_open_dryrun_valve(self):
        order, policy, receipt, invocation, executor, valve = _full_spine_with_open_valve()
        result = plan_reddog_openclaw_adapter_dryrun(
            order,
            policy,
            receipt,
            invocation.to_dict(),
            executor.to_dict(),
            valve.to_dict(),
            target_type=INTAKE_FOUNDUP_JOB,
        )
        assert result.decision == ADAPTER_DRYRUN_ACCEPT
        assert result.proposed_intake is not None
        assert result.proposed_intake.target_type == "foundup_job"
        assert result.proposed_intake.proposed_job_id.startswith("reddog-fj-")
        assert result.proposed_intake.requested_action == "build_foundup"
        assert result.proposed_intake.no_enqueue_performed is True
        assert result.proposed_intake.no_execution_performed is True
        assert result.no_enqueue_performed is True
        assert result.no_execution_performed is True
        assert result.adapter_receipt.decision == ADAPTER_DRYRUN_ACCEPT

    def test_autonomous_task_proposed_with_open_dryrun_valve(self):
        order, policy, receipt, invocation, executor, valve = _full_spine_with_open_valve(
            intake_target=INTAKE_AUTONOMOUS_TASK
        )
        result = plan_reddog_openclaw_adapter_dryrun(
            order,
            policy,
            receipt,
            invocation.to_dict(),
            executor.to_dict(),
            valve.to_dict(),
            target_type=INTAKE_AUTONOMOUS_TASK,
        )
        assert result.decision == ADAPTER_DRYRUN_ACCEPT
        assert result.proposed_intake is not None
        assert result.proposed_intake.target_type == "autonomous_task"
        assert result.proposed_intake.proposed_task_id == "reddog-wo-wo-adapter-dryrun-001"
        assert result.proposed_intake.proposed_job_id is None


class TestAdapterDryRunReject:
    def test_closed_valve_rejects(self):
        order, policy, receipt, invocation, executor, valve = _full_spine_with_open_valve()
        closed_valve = valve.to_dict()
        closed_valve["valve_state"] = VALVE_CLOSED
        result = plan_reddog_openclaw_adapter_dryrun(
            order,
            policy,
            receipt,
            invocation.to_dict(),
            executor.to_dict(),
            closed_valve,
        )
        assert result.decision == ADAPTER_DRYRUN_REJECT
        assert "execution_valve_closed" in result.rejection_reasons

    def test_worktree_create_valve_rejects(self):
        order, policy, receipt, invocation, executor, valve = _full_spine_with_open_valve()
        worktree_valve = valve.to_dict()
        worktree_valve["valve_state"] = VALVE_OPEN_WORKTREE_CREATE
        result = plan_reddog_openclaw_adapter_dryrun(
            order,
            policy,
            receipt,
            invocation.to_dict(),
            executor.to_dict(),
            worktree_valve,
        )
        assert result.decision == ADAPTER_DRYRUN_REJECT
        assert "worktree_valve_not_allowed_for_adapter_dryrun" in result.rejection_reasons

    def test_assignment_dispatcher_target_rejects(self):
        order, policy, receipt, invocation, executor, valve = _full_spine_with_open_valve()
        result = plan_reddog_openclaw_adapter_dryrun(
            order,
            policy,
            receipt,
            invocation.to_dict(),
            executor.to_dict(),
            valve.to_dict(),
            target_type=INTAKE_ASSIGNMENT_DISPATCHER,
        )
        assert result.decision == ADAPTER_DRYRUN_REJECT
        assert "assignment_dispatcher_forbidden_target" in result.rejection_reasons

    def test_missing_receipt_chain_rejects(self):
        order, policy, receipt, invocation, executor, valve = _full_spine_with_open_valve()
        receipt = dict(receipt)
        receipt["receipt_digest"] = ""
        result = plan_reddog_openclaw_adapter_dryrun(
            order,
            policy,
            receipt,
            invocation.to_dict(),
            executor.to_dict(),
            valve.to_dict(),
        )
        assert result.decision == ADAPTER_DRYRUN_REJECT
        assert "missing_reddog_work_order_receipt" in result.rejection_reasons

    def test_missing_executor_plan_rejects(self):
        order, policy, receipt, invocation, executor, valve = _full_spine_with_open_valve()
        executor_payload = executor.to_dict()
        executor_payload["plan"] = None
        executor_payload["decision"] = "EXECUTOR_PLAN_REJECT"
        result = plan_reddog_openclaw_adapter_dryrun(
            order,
            policy,
            receipt,
            invocation.to_dict(),
            executor_payload,
            valve.to_dict(),
        )
        assert result.decision == ADAPTER_DRYRUN_REJECT
        assert "executor_plan_not_accepted" in result.rejection_reasons
        assert "missing_executor_plan" in result.rejection_reasons

    def test_path_scope_violation_rejects(self):
        order, policy, receipt, invocation, executor, valve = _full_spine_with_open_valve()
        order = dict(order)
        order["allowed_paths"] = ["docs/**"]
        executor_payload = executor.to_dict()
        result = plan_reddog_openclaw_adapter_dryrun(
            order,
            policy,
            receipt,
            invocation.to_dict(),
            executor_payload,
            valve.to_dict(),
        )
        assert result.decision == ADAPTER_DRYRUN_REJECT
        assert "path_outside_allowed_scope" in result.rejection_reasons


class TestAdapterDryRunStability:
    def test_deterministic_digest_and_json_serializable(self):
        fixed = datetime(2026, 6, 28, 20, 0, 0, tzinfo=timezone.utc)
        captured = (fixed - timedelta(seconds=60)).replace(microsecond=0).isoformat()
        order = _base_order(
            nonce="nonce-stable-adapter",
            repo_permission_snapshot={
                "permission_level": "write",
                "captured_at": captured,
                "source": "mock",
                "digest": "sha256:" + ("f" * 64),
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            with RedDogWorkOrderReceiptStore(Path(tmp) / "receipts.db") as store:
                invocation = invoke_reddog_work_order_dryrun(
                    order,
                    permission_snapshot={
                        "permission_level": "write",
                        "captured_at": captured,
                        "source": "mock",
                        "digest": order["repo_permission_snapshot"]["digest"],
                    },
                    seen_nonces=set(),
                    receipt_store=store,
                    now=fixed,
                )
        executor = plan_wre_isolated_worktree_execution_dryrun(invocation, order, now=fixed)
        policy = {
            "decision": "POLICY_ACCEPT",
            "receipt_digest": invocation.policy_gate_receipt_digest,
            "no_execution_performed": True,
        }
        receipt = {
            "receipt_id": invocation.receipt_id,
            "receipt_digest": invocation.receipt_digest,
            "policy_gate_receipt_digest": invocation.policy_gate_receipt_digest,
            "no_execution_performed": True,
        }
        valve = evaluate_reddog_execution_valve(
            ExecutionValveRequest(
                work_order=order,
                policy_gate_receipt=policy,
                reddog_work_order_receipt=receipt,
                invocation_result=invocation.to_dict(),
                executor_plan_result=executor.to_dict(),
                intake_target=INTAKE_FOUNDUP_JOB,
                permission_snapshot=order["repo_permission_snapshot"],
            ),
            ExecutionValveEnvironment(valve_dryrun_enabled=True),
            now=fixed,
        )
        first = plan_reddog_openclaw_adapter_dryrun(
            order,
            policy,
            receipt,
            invocation.to_dict(),
            executor.to_dict(),
            valve.to_dict(),
            now=fixed,
        )
        second = plan_reddog_openclaw_adapter_dryrun(
            order,
            policy,
            receipt,
            invocation.to_dict(),
            executor.to_dict(),
            valve.to_dict(),
            now=fixed,
        )
        assert first.proposed_intake is not None
        assert first.proposed_intake.proposed_job_id == second.proposed_intake.proposed_job_id
        assert first.adapter_receipt.adapter_receipt_id == second.adapter_receipt.adapter_receipt_id
        assert first.adapter_receipt.adapter_receipt_digest == second.adapter_receipt.adapter_receipt_digest
        json.dumps(first.to_dict())


class TestNoEnqueueBoundary:
    def test_no_enqueue_no_execution_always(self):
        order, policy, receipt, invocation, executor, valve = _full_spine_with_open_valve()
        result = plan_reddog_openclaw_adapter_dryrun(
            order,
            policy,
            receipt,
            invocation.to_dict(),
            executor.to_dict(),
            valve.to_dict(),
        )
        assert result.no_enqueue_performed is True
        assert result.no_execution_performed is True

    def test_ast_denylist(self):
        module_path = (
            Path(__file__).resolve().parents[1] / "src" / "reddog_openclaw_adapter_dryrun.py"
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
                for token in (
                    "subprocess",
                    "github_integration",
                    "wre_core",
                    "skillz",
                    "agent_db",
                    "hermes_job_executor",
                    "openclaw_supervisor",
                )
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
            "create_autonomous_task(",
            "get_autonomous_tasks(",
            "queue.append(",
            "supervisor.enqueue",
        ):
            assert token not in source
