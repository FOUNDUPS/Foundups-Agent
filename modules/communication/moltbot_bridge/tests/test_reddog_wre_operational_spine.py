"""Tests for RedDog WRE worktree-create operational spine."""

from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    ExecutionValveEnvironment,
)
from modules.communication.moltbot_bridge.src.reddog_wre_operational_spine import (
    WORKTREE_SPINE_ACCEPT,
    WORKTREE_SPINE_REJECT,
    run_reddog_wre_worktree_create_spine,
)

_TOKEN = "SOVEREIGN-WORKTREE-SPINE-TEST"


class FakeRunner:
    def __init__(self, *, ok: bool = True) -> None:
        self.ok = ok
        self.calls: list[tuple] = []

    def create_worktree(self, *, worktree_path, branch_name, base_ref):
        self.calls.append(("create_worktree", str(worktree_path), branch_name, base_ref))
        if self.ok:
            Path(worktree_path).mkdir(parents=True, exist_ok=True)
        return {"ok": self.ok, "returncode": 0 if self.ok else 1}

    def cleanup_worktree(self, *, worktree_path):
        self.calls.append(("cleanup_worktree", str(worktree_path)))
        return {"ok": True}


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _future_expiry(now: datetime, hours: int = 2) -> str:
    return (now + timedelta(hours=hours)).replace(microsecond=0).isoformat()


def _base_order(now: datetime, **overrides):
    captured = (now - timedelta(seconds=60)).replace(microsecond=0).isoformat()
    payload = {
        "work_order_id": "wo-operational-spine-001",
        "created_at": captured,
        "red_dog_instance_id": "reddog-ext-0.3.45",
        "authenticated_principal": "principal-012",
        "principal_provider": "github",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "repo_permission_snapshot": {
            "permission_level": "write",
            "captured_at": captured,
            "source": "mock",
            "digest": "sha256:" + ("a" * 64),
        },
        "requested_operation": "feature_slice",
        "authority_tier": "source",
        "allowed_paths": ["modules/communication/moltbot_bridge/**"],
        "denied_paths": [".env"],
        "branch_name": "feat/reddog-operational-spine-test",
        "base_ref": "main",
        "task_summary": "Create the first isolated RedDog WRE worktree.",
        "wsp_applicability": ["WSP_34", "WSP_50", "WSP_97"],
        "holoindex_evidence_refs": [
            "docs/audits/architecture/REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1.md"
        ],
        "skillz_candidates": [],
        "required_tests": [
            "modules/communication/moltbot_bridge/tests/test_reddog_wre_operational_spine.py"
        ],
        "required_policy_gates": ["openclaw_policy_gate"],
        "required_reviewers": [],
        "sentinel_checks": [],
        "rollback_plan": "Remove worktree and delete branch on abort.",
        "expiry": _future_expiry(now),
        "nonce": "nonce-operational-spine-001",
        "evidence_digest": "sha256:" + ("b" * 64),
        "advisory_only_source_packet": {
            "work_focus_digest": "sha256:" + ("c" * 64),
            "wsp_prompt_digest": "sha256:" + ("d" * 64),
            "copy_md_run_trace_digest": "sha256:" + ("e" * 64),
        },
        "holoindex_evidence": {
            "holoindex_query": "RedDog WRE operational spine",
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


def _accepted_signature(order):
    return {
        "accepted": True,
        "reason_codes": [],
        "work_order_id": order["work_order_id"],
    }


class TestOperationalSpineAccept:
    def test_accept_runs_full_spine_to_worktree_create_only(self, tmp_path: Path):
        fixed = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        order = _base_order(fixed)
        runner = FakeRunner()
        locks: set[str] = set()

        result = run_reddog_wre_worktree_create_spine(
            order,
            seen_nonces=set(),
            valve_environment=ExecutionValveEnvironment(
                valve_worktree_create_enabled=True,
                sovereign_worktree_token=_TOKEN,
            ),
            signature_verification_result=_accepted_signature(order),
            runner=runner,
            repo_root=repo_root,
            now=fixed,
            locks=locks,
            admission_consumer=lambda: True,
        )

        assert result.decision == WORKTREE_SPINE_ACCEPT
        assert result.invocation_result["decision"] == "INVOCATION_ACCEPT"
        assert result.executor_plan_result["decision"] == "EXECUTOR_PLAN_ACCEPT"
        assert result.valve_decision["valve_state"] == "VALVE_OPEN_WORKTREE_CREATE"
        assert result.worktree_create_result["decision"] == "WORKTREE_CREATE_ACCEPT"
        assert result.no_task_execution_performed is True
        assert result.no_file_edit_performed is True
        assert result.no_pr_created is True
        assert result.no_live_openclaw_enqueue is True
        assert result.no_hermes_dispatch is True
        assert result.merge_performed is False
        assert result.main_checkout_untouched is True
        assert [call[0] for call in runner.calls] == ["create_worktree"]
        assert not _is_inside(Path(runner.calls[0][1]), repo_root)
        assert _is_inside(Path(runner.calls[0][1]), repo_root.parent / ".reddog" / "worktrees" / "repo")
        assert locks == {order["work_order_id"]}

    def test_digest_stable_and_sovereign_token_not_emitted(self, tmp_path: Path):
        fixed = datetime(2026, 7, 8, 12, 5, 0, tzinfo=timezone.utc)
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        order = _base_order(fixed, nonce="nonce-operational-spine-stable")

        first = run_reddog_wre_worktree_create_spine(
            order,
            seen_nonces=set(),
            valve_environment=ExecutionValveEnvironment(
                valve_worktree_create_enabled=True,
                sovereign_worktree_token=_TOKEN,
            ),
            signature_verification_result=_accepted_signature(order),
            runner=FakeRunner(),
            repo_root=repo_root,
            now=fixed,
            locks=set(),
        )
        second = run_reddog_wre_worktree_create_spine(
            order,
            seen_nonces=set(),
            valve_environment=ExecutionValveEnvironment(
                valve_worktree_create_enabled=True,
                sovereign_worktree_token=_TOKEN,
            ),
            signature_verification_result=_accepted_signature(order),
            runner=FakeRunner(),
            repo_root=repo_root,
            now=fixed,
            locks=set(),
        )

        assert first.result_digest == second.result_digest
        assert _TOKEN not in json.dumps(first.to_dict())


class TestOperationalSpineReject:
    def test_default_closed_valve_rejects_before_runner(self, tmp_path: Path):
        fixed = datetime(2026, 7, 8, 12, 10, 0, tzinfo=timezone.utc)
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        order = _base_order(fixed)
        runner = FakeRunner()

        result = run_reddog_wre_worktree_create_spine(
            order,
            seen_nonces=set(),
            signature_verification_result=_accepted_signature(order),
            runner=runner,
            repo_root=repo_root,
            now=fixed,
        )

        assert result.decision == WORKTREE_SPINE_REJECT
        assert "execution_valve_not_open_for_worktree_create" in result.rejection_reasons
        assert "explicit_valve_flag_missing" in result.rejection_reasons
        assert result.worktree_create_result == {}
        assert runner.calls == []

    def test_index_gap_write_rejects_at_invocation_before_runner(self, tmp_path: Path):
        fixed = datetime(2026, 7, 8, 12, 15, 0, tzinfo=timezone.utc)
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        order = _base_order(
            fixed,
            holoindex_evidence={
                "holoindex_query": "RedDog WRE operational spine",
                "holoindex_status": "bundle_json_ok",
                "code_hits": [],
                "wsp_hits": [],
                "skillz_hits": [],
                "direct_read_fallback_used": False,
                "index_gap_detected": True,
                "applicable_wsps": ["WSP_34"],
                "evidence_refs": [],
                "retrieval_quality": "INDEX_GAP",
                "skillz_gap_detected": True,
            },
        )
        runner = FakeRunner()

        result = run_reddog_wre_worktree_create_spine(
            order,
            seen_nonces=set(),
            valve_environment=ExecutionValveEnvironment(
                valve_worktree_create_enabled=True,
                sovereign_worktree_token=_TOKEN,
            ),
            signature_verification_result=_accepted_signature(order),
            runner=runner,
            repo_root=repo_root,
            now=fixed,
        )

        assert result.decision == WORKTREE_SPINE_REJECT
        assert "invocation_not_accepted" in result.rejection_reasons
        assert "index_gap_blocks_write_operation" in result.rejection_reasons
        assert result.executor_plan_result == {}
        assert runner.calls == []

    def test_lock_collision_rejects_at_plan_before_runner(self, tmp_path: Path):
        fixed = datetime(2026, 7, 8, 12, 20, 0, tzinfo=timezone.utc)
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        order = _base_order(fixed)
        runner = FakeRunner()

        result = run_reddog_wre_worktree_create_spine(
            order,
            seen_nonces=set(),
            valve_environment=ExecutionValveEnvironment(
                valve_worktree_create_enabled=True,
                sovereign_worktree_token=_TOKEN,
            ),
            signature_verification_result=_accepted_signature(order),
            runner=runner,
            repo_root=repo_root,
            now=fixed,
            locks={order["work_order_id"]},
        )

        assert result.decision == WORKTREE_SPINE_REJECT
        assert "executor_plan_not_accepted" in result.rejection_reasons
        assert "lock_collision" in result.rejection_reasons
        assert result.valve_decision == {}
        assert runner.calls == []

    def test_missing_signed_authority_rejects_before_runner(self, tmp_path: Path):
        fixed = datetime(2026, 7, 8, 12, 25, 0, tzinfo=timezone.utc)
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        order = _base_order(fixed)
        runner = FakeRunner()

        result = run_reddog_wre_worktree_create_spine(
            order,
            seen_nonces=set(),
            valve_environment=ExecutionValveEnvironment(
                valve_worktree_create_enabled=True,
                sovereign_worktree_token=_TOKEN,
            ),
            runner=runner,
            repo_root=repo_root,
            now=fixed,
        )

        assert result.decision == WORKTREE_SPINE_REJECT
        assert "invocation_not_accepted" in result.rejection_reasons
        assert "signed_work_authority_required" in result.rejection_reasons
        assert result.executor_plan_result == {}
        assert runner.calls == []


class TestOperationalSpineBoundaries:
    def test_orchestration_module_has_no_live_dispatch_or_shell_imports(self):
        module_path = (
            Path(__file__).resolve().parents[1] / "src" / "reddog_wre_operational_spine.py"
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
            "shell=True",
            "git worktree",
            "worktree add",
            "gh pr",
            '"commit"',
            "'commit'",
            '"push"',
            "'push'",
            "merge_pull_request",
            "openclaw_supervisor",
            "hermes_job_executor",
            "execute_skill",
            "AgentDB",
        ):
            assert token not in source
