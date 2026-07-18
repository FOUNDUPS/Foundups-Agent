"""Tests for RedDog WRE isolated worktree create orchestration."""

from __future__ import annotations

import ast
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_effect_commit_outcome import (
    EFFECT_COMMITTED,
    EFFECT_INDETERMINATE,
    EFFECT_NOT_COMMITTED,
)

from modules.communication.moltbot_bridge.src.reddog_work_order_receipt import (
    RedDogWorkOrderReceiptStore,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_runtime_invocation import (
    invoke_reddog_work_order_dryrun,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    INTAKE_FOUNDUP_JOB,
    VALVE_CLOSED,
    VALVE_OPEN_WORKTREE_CREATE,
    ExecutionValveEnvironment,
    ExecutionValveRequest,
    evaluate_reddog_execution_valve,
)
from modules.communication.moltbot_bridge.src.reddog_wre_executor_dryrun import (
    plan_wre_isolated_worktree_execution_dryrun,
)
from modules.communication.moltbot_bridge.src.reddog_wre_worktree_create import (
    PHASE_WORKTREE_CLEANUP_PLANNED,
    PHASE_WORKTREE_CREATED,
    PHASE_WORKTREE_PREFLIGHT,
    WORKTREE_CREATE_ACCEPT,
    WORKTREE_CREATE_REJECT,
    create_reddog_wre_worktree,
)

_TOKEN = "SOVEREIGN-WORKTREE-CREATE-TEST"


class FakeRunner:
    def __init__(
        self,
        *,
        ok: bool = True,
        raises: bool = False,
        commit_then_raise: bool = False,
    ) -> None:
        self.ok = ok
        self.raises = raises
        self.commit_then_raise = commit_then_raise
        self.calls: list[tuple] = []

    def create_worktree(self, *, worktree_path, branch_name, base_ref):
        self.calls.append(("create_worktree", str(worktree_path), branch_name, base_ref))
        if self.commit_then_raise:
            Path(worktree_path).mkdir(parents=True, exist_ok=True)
            raise RuntimeError("simulated post-commit transport failure")
        if self.raises:
            raise RuntimeError("simulated create failure")
        Path(worktree_path).mkdir(parents=True, exist_ok=True)
        return {"ok": self.ok, "returncode": 0 if self.ok else 1}

    def cleanup_worktree(self, *, worktree_path):
        self.calls.append(("cleanup_worktree", str(worktree_path)))
        return {"ok": True}


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _future_expiry(hours: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


def _fresh_captured() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _base_order(**overrides):
    payload = {
        "work_order_id": "wo-worktree-create-001",
        "created_at": _fresh_captured(),
        "red_dog_instance_id": "reddog-ext-0.3.45",
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
        "branch_name": "feat/reddog-worktree-create-test",
        "base_ref": "main",
        "task_summary": "Create an isolated worktree for a RedDog worker slice",
        "wsp_applicability": ["WSP_34", "WSP_50", "WSP_97"],
        "holoindex_evidence_refs": [
            "docs/audits/architecture/REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1.md"
        ],
        "skillz_candidates": [],
        "required_tests": [
            "modules/communication/moltbot_bridge/tests/test_reddog_wre_worktree_create.py"
        ],
        "required_policy_gates": ["openclaw_policy_gate"],
        "required_reviewers": [],
        "sentinel_checks": [],
        "rollback_plan": "Remove worktree and delete branch on abort.",
        "expiry": _future_expiry(),
        "nonce": "nonce-worktree-create-001",
        "evidence_digest": "sha256:" + ("b" * 64),
        "advisory_only_source_packet": {
            "work_focus_digest": "sha256:" + ("c" * 64),
            "wsp_prompt_digest": "sha256:" + ("d" * 64),
            "copy_md_run_trace_digest": "sha256:" + ("e" * 64),
        },
        "holoindex_evidence": {
            "holoindex_query": "RedDog WRE worktree create",
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


def _accepted_spine(tmp_path: Path, *, now: datetime | None = None):
    fixed = now or datetime.now(timezone.utc).replace(microsecond=0)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    captured = (fixed - timedelta(seconds=60)).replace(microsecond=0).isoformat()
    order = _base_order(
        repo_permission_snapshot={
            "permission_level": "write",
            "captured_at": captured,
            "source": "mock",
            "digest": "sha256:" + ("f" * 64),
        }
    )
    with tempfile.TemporaryDirectory() as tmp:
        with RedDogWorkOrderReceiptStore(Path(tmp) / "receipts.db") as store:
            invocation = invoke_reddog_work_order_dryrun(
                order,
                permission_snapshot=order["repo_permission_snapshot"],
                seen_nonces=set(),
                receipt_store=store,
                now=fixed,
            )
    executor = plan_wre_isolated_worktree_execution_dryrun(
        invocation,
        order,
        now=fixed,
        repo_root=str(repo_root),
    )
    policy = {
        "decision": "POLICY_ACCEPT",
        "receipt_digest": invocation.policy_gate_receipt_digest,
        "no_execution_performed": True,
        "work_order_id": order["work_order_id"],
    }
    receipt = {
        "receipt_id": invocation.receipt_id,
        "receipt_digest": invocation.receipt_digest,
        "policy_gate_receipt_digest": invocation.policy_gate_receipt_digest,
        "no_execution_performed": True,
        "work_order_id": order["work_order_id"],
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
        ExecutionValveEnvironment(
            valve_worktree_create_enabled=True,
            sovereign_worktree_token=_TOKEN,
        ),
        now=fixed,
    )
    assert valve.valve_state == VALVE_OPEN_WORKTREE_CREATE
    return order, executor, valve, repo_root, fixed


class TestWorktreeCreateAccept:
    def test_accept_creates_only_worktree(self, tmp_path: Path):
        order, executor, valve, repo_root, fixed = _accepted_spine(tmp_path)
        runner = FakeRunner()
        result = create_reddog_wre_worktree(
            order,
            executor.to_dict(),
            valve.to_dict(),
            runner=runner,
            repo_root=repo_root,
            now=fixed,
            admission_consumer=lambda: True,
        )
        assert result.decision == WORKTREE_CREATE_ACCEPT
        assert result.effect_commit_state == EFFECT_COMMITTED
        assert result.effect_attempt_key.startswith("worktree-attempt-")
        assert result.reconciliation_required is False
        assert result.no_task_execution_performed is True
        assert result.no_file_edit_performed is True
        assert result.no_pr_created is True
        assert result.merge_performed is False
        assert result.main_checkout_untouched is True
        assert len(runner.calls) == 1
        assert runner.calls[0][0] == "create_worktree"
        assert Path(runner.calls[0][1]).resolve() == Path(result.worktree_path).resolve()
        assert runner.calls[0][2:] == ("feat/reddog-worktree-create-test", "main")
        assert not _is_inside(Path(result.worktree_path), repo_root)
        assert _is_inside(Path(result.worktree_path), repo_root.parent / ".reddog" / "worktrees" / "repo")
        phases = [receipt.phase for receipt in result.phase_receipts]
        assert phases == [
            PHASE_WORKTREE_PREFLIGHT,
            PHASE_WORKTREE_CREATED,
            PHASE_WORKTREE_CLEANUP_PLANNED,
        ]
        assert Path(result.worktree_path).exists()

    def test_digest_stable_and_no_token_leak(self, tmp_path: Path):
        fixed = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)
        order, executor, valve, repo_root, _ = _accepted_spine(tmp_path, now=fixed)
        first = create_reddog_wre_worktree(
            order,
            executor.to_dict(),
            valve.to_dict(),
            runner=FakeRunner(),
            repo_root=repo_root,
            now=fixed,
            admission_consumer=lambda: True,
        )
        second = create_reddog_wre_worktree(
            order,
            executor.to_dict(),
            valve.to_dict(),
            runner=FakeRunner(),
            repo_root=repo_root,
            now=fixed,
            admission_consumer=lambda: True,
        )
        assert first.result_digest == second.result_digest
        blob = json.dumps(first.to_dict())
        assert _TOKEN not in blob


class TestWorktreeCreateReject:
    def test_closed_valve_rejects_before_runner(self, tmp_path: Path):
        order, executor, valve, repo_root, fixed = _accepted_spine(tmp_path)
        closed = valve.to_dict()
        closed["valve_state"] = VALVE_CLOSED
        runner = FakeRunner()
        result = create_reddog_wre_worktree(
            order,
            executor.to_dict(),
            closed,
            runner=runner,
            repo_root=repo_root,
            now=fixed,
            admission_consumer=lambda: True,
        )
        assert result.decision == WORKTREE_CREATE_REJECT
        assert "execution_valve_not_open_for_worktree_create" in result.rejection_reasons
        assert runner.calls == []

    def test_relative_plan_path_rejects_before_runner(self, tmp_path: Path):
        order, executor, valve, repo_root, fixed = _accepted_spine(tmp_path)
        payload = executor.to_dict()
        payload["plan"]["proposed_worktree_path"] = ".reddog/worktrees/wo/nonce/"
        runner = FakeRunner()
        result = create_reddog_wre_worktree(
            order,
            payload,
            valve.to_dict(),
            runner=runner,
            repo_root=repo_root,
            now=fixed,
            admission_consumer=lambda: True,
        )
        assert result.decision == WORKTREE_CREATE_REJECT
        assert "worktree_path_not_absolute" in result.rejection_reasons
        assert runner.calls == []

    def test_outside_reddog_root_rejects_before_runner(self, tmp_path: Path):
        order, executor, valve, repo_root, fixed = _accepted_spine(tmp_path)
        payload = executor.to_dict()
        payload["plan"]["proposed_worktree_path"] = str(tmp_path / "outside")
        runner = FakeRunner()
        result = create_reddog_wre_worktree(
            order,
            payload,
            valve.to_dict(),
            runner=runner,
            repo_root=repo_root,
            now=fixed,
        )
        assert result.decision == WORKTREE_CREATE_REJECT
        assert "worktree_path_not_under_reddog_root" in result.rejection_reasons
        assert runner.calls == []

    def test_legacy_in_repo_reddog_worktree_rejects_before_runner(self, tmp_path: Path):
        order, executor, valve, repo_root, fixed = _accepted_spine(tmp_path)
        payload = executor.to_dict()
        payload["plan"]["proposed_worktree_path"] = str(
            repo_root / ".reddog" / "worktrees" / order["work_order_id"] / "nonce"
        )
        runner = FakeRunner()
        result = create_reddog_wre_worktree(
            order,
            payload,
            valve.to_dict(),
            runner=runner,
            repo_root=repo_root,
            now=fixed,
        )
        assert result.decision == WORKTREE_CREATE_REJECT
        assert "worktree_path_inside_repo_root" in result.rejection_reasons
        assert any(reason.startswith("cwd_guard_failed:") for reason in result.rejection_reasons)
        assert runner.calls == []

    def test_create_failure_attempts_cleanup(self, tmp_path: Path):
        order, executor, valve, repo_root, fixed = _accepted_spine(tmp_path)
        runner = FakeRunner(ok=False)
        result = create_reddog_wre_worktree(
            order,
            executor.to_dict(),
            valve.to_dict(),
            runner=runner,
            repo_root=repo_root,
            now=fixed,
            admission_consumer=lambda: True,
        )
        assert result.decision == WORKTREE_CREATE_REJECT
        assert "worktree_create_failed" in result.rejection_reasons
        assert result.effect_commit_state == EFFECT_NOT_COMMITTED
        assert [call[0] for call in runner.calls] == ["create_worktree", "cleanup_worktree"]

    def test_commit_then_throw_is_indeterminate(self, tmp_path: Path):
        order, executor, valve, repo_root, fixed = _accepted_spine(tmp_path)
        runner = FakeRunner(commit_then_raise=True)
        result = create_reddog_wre_worktree(
            order,
            executor.to_dict(),
            valve.to_dict(),
            runner=runner,
            repo_root=repo_root,
            now=fixed,
            admission_consumer=lambda: True,
        )

        assert result.decision == WORKTREE_CREATE_REJECT
        assert result.effect_commit_state == EFFECT_INDETERMINATE
        assert result.reconciliation_required is True
        assert result.reconciliation_data["next_action"] == (
            "inspect_worktree_registry_path_and_branch"
        )
        assert result.effect_attempt_key.startswith("worktree-attempt-")


class TestWorktreeCreateBoundaries:
    def test_orchestration_module_delegates_side_effects(self):
        module_path = (
            Path(__file__).resolve().parents[1] / "src" / "reddog_wre_worktree_create.py"
        )
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        assert "subprocess" not in imported
        for token in (
            "git worktree",
            "worktree add",
            "gh pr",
            "git commit",
            "push_branch",
            "create_draft_pr",
            "shell=True",
        ):
            assert token not in source

    def test_runner_uses_argv_only_and_no_gh(self):
        module_path = (
            Path(__file__).resolve().parents[1] / "src" / "reddog_wre_worktree_runner.py"
        )
        source = module_path.read_text(encoding="utf-8")
        assert "validate_wre_worker_operation_cwd" in source
        assert "shell=True" not in source
        assert '"gh"' not in source and "'gh'" not in source
        assert '"commit"' not in source and "'commit'" not in source
        assert '"push"' not in source and "'push'" not in source
        assert '"worktree"' in source and '"add"' in source

    def test_real_runner_rejects_in_repo_worktree_before_subprocess(self, tmp_path: Path, monkeypatch):
        import modules.communication.moltbot_bridge.src.reddog_wre_worktree_runner as runner_module

        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        blocked_path = repo_root / ".reddog" / "worktrees" / "wo" / "nonce"
        called = {"subprocess": False}

        def fake_run(*args, **kwargs):
            called["subprocess"] = True
            raise AssertionError("subprocess must not run for in-repo worktree path")

        monkeypatch.setattr(runner_module.subprocess, "run", fake_run)
        runner = runner_module.RealRedDogWorktreeRunner(repo_root)
        result = runner.create_worktree(
            worktree_path=blocked_path,
            branch_name="feat/blocked",
            base_ref="main",
        )

        assert result["ok"] is False
        assert "FAIL_WORKTREE_INSIDE_REPO_ROOT" in result["stderr"]
        assert called["subprocess"] is False
