"""Tests for RedDog WRE isolated worktree executor dry-run planner."""

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
    INVOCATION_ACCEPT,
    INVOCATION_REJECT,
    invoke_reddog_work_order_dryrun,
)
from modules.communication.moltbot_bridge.src.reddog_wre_executor_dryrun import (
    EXECUTOR_PLAN_ACCEPT,
    EXECUTOR_PLAN_REJECT,
    PHASE_CLEANUP_PLANNED,
    PHASE_LOCK_CHECKED,
    PHASE_PLAN_BUILT,
    plan_wre_isolated_worktree_execution_dryrun,
)


def _future_expiry(hours: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


def _fresh_captured() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _base_order(**overrides):
    payload = {
        "work_order_id": "wo-exec-dryrun-001",
        "created_at": _fresh_captured(),
        "red_dog_instance_id": "reddog-ext-0.3.27",
        "authenticated_principal": "principal-012",
        "principal_provider": "github",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "repo_permission_snapshot": {
            "permission_level": "read",
            "captured_at": _fresh_captured(),
            "source": "mock",
            "digest": "sha256:" + ("a" * 64),
        },
        "requested_operation": "audit_only",
        "authority_tier": "advisory",
        "allowed_paths": ["docs/**"],
        "denied_paths": [".env"],
        "branch_name": "docs/executor-dryrun-test",
        "base_ref": "main",
        "task_summary": "Executor dry-run planner validation",
        "wsp_applicability": ["WSP_34", "WSP_50"],
        "holoindex_evidence_refs": [
            "docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md",
            "docs/audits/architecture/REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1.md",
        ],
        "skillz_candidates": [],
        "required_tests": ["modules/communication/moltbot_bridge/tests/test_reddog_wre_executor_dryrun.py"],
        "required_policy_gates": ["openclaw_policy_gate"],
        "required_reviewers": [],
        "sentinel_checks": [],
        "rollback_plan": "Remove worktree and delete branch on abort; no merge.",
        "expiry": _future_expiry(),
        "nonce": "nonce-exec-dryrun-001",
        "evidence_digest": "sha256:" + ("b" * 64),
        "advisory_only_source_packet": {
            "work_focus_digest": "sha256:" + ("c" * 64),
            "wsp_prompt_digest": "sha256:" + ("d" * 64),
            "copy_md_run_trace_digest": "sha256:" + ("e" * 64),
        },
        "holoindex_evidence": {
            "holoindex_query": "WRE executor plan dryrun",
            "holoindex_status": "bundle_json_ok",
            "code_hits": [],
            "wsp_hits": ["WSP_framework/src/WSP_34_Git_Operations_Protocol.md"],
            "skillz_hits": [],
            "direct_read_fallback_used": False,
            "index_gap_detected": False,
            "applicable_wsps": ["WSP_34"],
            "evidence_refs": [
                "docs/audits/architecture/REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1.md"
            ],
            "retrieval_quality": "HIGH",
            "skillz_gap_detected": False,
        },
    }
    payload.update(overrides)
    return payload


def _accepted_invocation(order=None, *, nonce_suffix: str = "accept"):
    order = order or _base_order(nonce=f"nonce-{nonce_suffix}")
    with tempfile.TemporaryDirectory() as tmp:
        with RedDogWorkOrderReceiptStore(Path(tmp) / "receipts.db") as store:
            result = invoke_reddog_work_order_dryrun(
                order,
                permission_snapshot={
                    "permission_level": "read",
                    "captured_at": _fresh_captured(),
                    "source": "mock",
                },
                seen_nonces=set(),
                receipt_store=store,
            )
    assert result.decision == INVOCATION_ACCEPT
    return result, order


class TestExecutorDryRunAccept:
    def test_accepted_invocation_creates_plan_no_mutation(self):
        invocation, order = _accepted_invocation()
        result = plan_wre_isolated_worktree_execution_dryrun(invocation, order)
        assert result.decision == EXECUTOR_PLAN_ACCEPT
        assert result.plan is not None
        assert result.no_mutation_performed is True
        assert result.plan.no_mutation_performed is True
        assert result.plan.proposed_branch_name == "docs/executor-dryrun-test"
        assert "/.reddog/worktrees/" in result.plan.proposed_worktree_path
        assert "/wo-exec-dryrun-001/" in result.plan.proposed_worktree_path
        assert "/Foundups-Agent/.reddog/worktrees/" not in result.plan.proposed_worktree_path
        assert result.plan.lock_key == "wo-exec-dryrun-001"
        assert len(result.phase_receipts) == 3
        phases = [r.phase for r in result.phase_receipts]
        assert phases == [PHASE_PLAN_BUILT, PHASE_LOCK_CHECKED, PHASE_CLEANUP_PLANNED]

    def test_plan_digest_stable_and_json_serializable(self):
        fixed = datetime(2026, 6, 28, 18, 0, 0, tzinfo=timezone.utc)
        captured = (fixed - timedelta(seconds=60)).replace(microsecond=0).isoformat()
        order = _base_order(
            nonce="nonce-stable-plan",
            repo_permission_snapshot={
                "permission_level": "read",
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
                        "permission_level": "read",
                        "captured_at": captured,
                        "source": "mock",
                    },
                    seen_nonces=set(),
                    receipt_store=store,
                    now=fixed,
                )
        first = plan_wre_isolated_worktree_execution_dryrun(
            invocation, order, now=fixed, repo_root="/repo"
        )
        second = plan_wre_isolated_worktree_execution_dryrun(
            invocation, order, now=fixed, repo_root="/repo"
        )
        assert first.plan is not None
        assert first.plan.plan_id == second.plan.plan_id
        assert first.plan.plan_digest == second.plan.plan_digest
        json.dumps(first.to_dict())


class TestExecutorDryRunReject:
    def test_rejected_invocation_fails_closed(self):
        invocation, order = _accepted_invocation(nonce_suffix="reject-invoke")
        rejected = type(invocation)(
            decision=INVOCATION_REJECT,
            work_order_id=invocation.work_order_id,
            policy_gate_decision=invocation.policy_gate_decision,
            receipt_id=invocation.receipt_id,
            receipt_digest=invocation.receipt_digest,
            no_execution_performed=True,
            rejection_reasons=["policy_reject"],
            gates_checked=invocation.gates_checked,
            policy_gate_receipt_digest=invocation.policy_gate_receipt_digest,
        )
        result = plan_wre_isolated_worktree_execution_dryrun(rejected, order)
        assert result.decision == EXECUTOR_PLAN_REJECT
        assert result.plan is None
        assert "invocation_rejected" in result.rejection_reasons
        assert result.rejection_receipt_digest

    def test_protected_branch_rejected(self):
        invocation, order = _accepted_invocation(nonce_suffix="protected-branch")
        order = dict(order)
        order["branch_name"] = "main"
        result = plan_wre_isolated_worktree_execution_dryrun(invocation, order)
        assert result.decision == EXECUTOR_PLAN_REJECT
        assert "protected_branch_forbidden" in result.rejection_reasons

    def test_denied_path_overlap_rejected(self):
        invocation, order = _accepted_invocation(nonce_suffix="denied-overlap")
        order["allowed_paths"] = ["docs/**", ".env"]
        result = plan_wre_isolated_worktree_execution_dryrun(invocation, order)
        assert result.decision == EXECUTOR_PLAN_REJECT
        assert "forbidden_path_in_allowed_paths" in result.rejection_reasons

    def test_lock_collision_rejected(self):
        invocation, order = _accepted_invocation(nonce_suffix="lock-collision")
        locks = {"wo-exec-dryrun-001"}
        result = plan_wre_isolated_worktree_execution_dryrun(invocation, order, locks=locks)
        assert result.decision == EXECUTOR_PLAN_REJECT
        assert "lock_collision" in result.rejection_reasons

    def test_cleanup_plan_required(self):
        invocation, order = _accepted_invocation(nonce_suffix="no-cleanup")
        order["rollback_plan"] = ""
        result = plan_wre_isolated_worktree_execution_dryrun(invocation, order)
        assert result.decision == EXECUTOR_PLAN_REJECT
        assert "cleanup_plan_missing" in result.rejection_reasons


class TestNoExecutionBoundary:
    def test_ast_denylist(self):
        module_path = (
            Path(__file__).resolve().parents[1] / "src" / "reddog_wre_executor_dryrun.py"
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
        ):
            assert token not in source
