"""Tests for RedDog extension-to-WRE operational spine explicit invoke guard."""

from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_extension_wre_operational_spine_invoke import (
    EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_ACCEPT,
    EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_REJECT,
    ExtensionWREOperationalSpineInvokeReason,
    invoke_reddog_extension_wre_operational_spine_explicit_valve,
)
from modules.communication.moltbot_bridge.src.reddog_operator_loop_wardrobe_selection import (
    AUTHORITY_SIGNED_VALVE_REQUIRED,
    WARDROBE_ARCHITECT_AUDIT,
    select_reddog_operator_loop_wardrobe_dryrun,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    ExecutionValveEnvironment,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_extension_wre_operational_spine_invoke.py"
)
EXTENSION_JS = REPO_ROOT / "extensions" / "foundups_advisory_workers" / "extension.js"
_TOKEN = "SOVEREIGN-WRE-SPINE-INVOKE-TEST"


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


def _holo():
    return {
        "holoindex_query": "RedDog extension WRE operational spine explicit invoke",
        "holoindex_status": "bundle_json_ok",
        "index_gap_detected": False,
        "skill_hits": [{"skill_name": "openclaw_executor"}],
    }


def _selection_receipt(**overrides):
    result = select_reddog_operator_loop_wardrobe_dryrun(
        "Invoke RedDog WRE operational spine through the explicit worktree valve.",
        authority_request="worktree_write",
        holoindex_evidence=_holo(),
    )
    payload = result.receipt.to_dict()
    payload.update(overrides)
    return payload


def _base_order(now: datetime, **overrides):
    captured = (now - timedelta(seconds=60)).replace(microsecond=0).isoformat()
    payload = {
        "work_order_id": "wo-extension-wre-spine-001",
        "created_at": captured,
        "red_dog_instance_id": "reddog-ext-0.3.48",
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
        "branch_name": "feat/reddog-extension-wre-spine-test",
        "base_ref": "main",
        "task_summary": "Create a guarded RedDog WRE worktree through extension explicit invoke.",
        "wsp_applicability": ["WSP_34", "WSP_50", "WSP_97"],
        "holoindex_evidence_refs": [
            "docs/audits/architecture/REDDOG_WRE_EXECUTION_VALVE_CONTRACT_PHASE1.md"
        ],
        "skillz_candidates": [],
        "required_tests": [
            "modules/communication/moltbot_bridge/tests/"
            "test_reddog_extension_wre_operational_spine_invoke.py"
        ],
        "required_policy_gates": ["openclaw_policy_gate"],
        "required_reviewers": [],
        "sentinel_checks": [],
        "rollback_plan": "Remove worktree and delete branch on abort.",
        "expiry": _future_expiry(now),
        "nonce": "nonce-extension-wre-spine-001",
        "evidence_digest": "sha256:" + ("b" * 64),
        "advisory_only_source_packet": {
            "work_focus_digest": "sha256:" + ("c" * 64),
            "wsp_prompt_digest": "sha256:" + ("d" * 64),
            "copy_md_run_trace_digest": "sha256:" + ("e" * 64),
        },
        "holoindex_evidence": {
            "holoindex_query": "RedDog extension WRE operational spine",
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


def _accepted_signature(order):
    return {
        "accepted": True,
        "reason_codes": [],
        "work_order_id": order["work_order_id"],
    }


def _open_worktree_env():
    return ExecutionValveEnvironment(
        valve_worktree_create_enabled=True,
        sovereign_worktree_token=_TOKEN,
    )


def test_accepts_only_explicit_sovereign_worktree_selection_and_calls_runner(tmp_path: Path) -> None:
    fixed = datetime(2026, 7, 12, 12, 0, 0, tzinfo=timezone.utc)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    order = _base_order(fixed)
    runner = FakeRunner()

    result = invoke_reddog_extension_wre_operational_spine_explicit_valve(
        order,
        explicit_wre_operational_spine_requested=True,
        selection_receipt=_selection_receipt(),
        seen_nonces=set(),
        valve_environment=_open_worktree_env(),
        signature_verification_result=_accepted_signature(order),
        runner=runner,
        repo_root=repo_root,
        now=fixed,
        locks=set(),
    )

    assert result.decision == EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_ACCEPT
    assert result.worktree_spine_result is not None
    assert result.worktree_spine_result.decision == "WORKTREE_SPINE_ACCEPT"
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


def test_rejects_missing_explicit_request_before_runner_call(tmp_path: Path) -> None:
    fixed = datetime(2026, 7, 12, 12, 5, 0, tzinfo=timezone.utc)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    order = _base_order(fixed)
    runner = FakeRunner()

    result = invoke_reddog_extension_wre_operational_spine_explicit_valve(
        order,
        explicit_wre_operational_spine_requested=False,
        selection_receipt=_selection_receipt(),
        valve_environment=_open_worktree_env(),
        signature_verification_result=_accepted_signature(order),
        runner=runner,
        repo_root=repo_root,
        now=fixed,
    )

    assert result.decision == EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_REJECT
    assert result.rejection_reasons == [
        ExtensionWREOperationalSpineInvokeReason.EXPLICIT_INVOKE_MISSING
    ]
    assert runner.calls == []


def test_rejects_missing_selection_before_runner_call(tmp_path: Path) -> None:
    fixed = datetime(2026, 7, 12, 12, 10, 0, tzinfo=timezone.utc)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    order = _base_order(fixed)
    runner = FakeRunner()

    result = invoke_reddog_extension_wre_operational_spine_explicit_valve(
        order,
        explicit_wre_operational_spine_requested=True,
        selection_receipt=None,
        valve_environment=_open_worktree_env(),
        signature_verification_result=_accepted_signature(order),
        runner=runner,
        repo_root=repo_root,
        now=fixed,
    )

    assert result.decision == EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_REJECT
    assert result.rejection_reasons == [
        ExtensionWREOperationalSpineInvokeReason.SELECTION_RECEIPT_MISSING
    ]
    assert runner.calls == []


def test_rejects_non_sovereign_selection_before_runner_call(tmp_path: Path) -> None:
    fixed = datetime(2026, 7, 12, 12, 15, 0, tzinfo=timezone.utc)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    order = _base_order(fixed)
    runner = FakeRunner()
    selection = _selection_receipt(
        selected_wardrobe=WARDROBE_ARCHITECT_AUDIT,
        execution_plane="audit_only",
        authority_boundary="no_authority",
    )

    result = invoke_reddog_extension_wre_operational_spine_explicit_valve(
        order,
        explicit_wre_operational_spine_requested=True,
        selection_receipt=selection,
        valve_environment=_open_worktree_env(),
        signature_verification_result=_accepted_signature(order),
        runner=runner,
        repo_root=repo_root,
        now=fixed,
    )

    assert result.decision == EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_REJECT
    assert ExtensionWREOperationalSpineInvokeReason.SELECTION_NOT_SOVEREIGN in result.rejection_reasons
    assert ExtensionWREOperationalSpineInvokeReason.SELECTION_PLANE_NOT_GOVERNED in result.rejection_reasons
    assert runner.calls == []


def test_rejects_signed_valve_only_boundary_for_worktree_create(tmp_path: Path) -> None:
    fixed = datetime(2026, 7, 12, 12, 20, 0, tzinfo=timezone.utc)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    order = _base_order(fixed)
    runner = FakeRunner()

    result = invoke_reddog_extension_wre_operational_spine_explicit_valve(
        order,
        explicit_wre_operational_spine_requested=True,
        selection_receipt=_selection_receipt(authority_boundary=AUTHORITY_SIGNED_VALVE_REQUIRED),
        valve_environment=_open_worktree_env(),
        signature_verification_result=_accepted_signature(order),
        runner=runner,
        repo_root=repo_root,
        now=fixed,
    )

    assert result.decision == EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_REJECT
    assert (
        ExtensionWREOperationalSpineInvokeReason.SELECTION_AUTHORITY_BOUNDARY_INVALID
        in result.rejection_reasons
    )
    assert runner.calls == []


def test_rejects_selection_rejections_before_runner_call(tmp_path: Path) -> None:
    fixed = datetime(2026, 7, 12, 12, 25, 0, tzinfo=timezone.utc)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    order = _base_order(fixed)
    runner = FakeRunner()

    result = invoke_reddog_extension_wre_operational_spine_explicit_valve(
        order,
        explicit_wre_operational_spine_requested=True,
        selection_receipt=_selection_receipt(rejection_reasons=["write_sensitive_index_gap"]),
        valve_environment=_open_worktree_env(),
        signature_verification_result=_accepted_signature(order),
        runner=runner,
        repo_root=repo_root,
        now=fixed,
    )

    assert result.decision == EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_REJECT
    assert ExtensionWREOperationalSpineInvokeReason.SELECTION_HAS_REJECTIONS in result.rejection_reasons
    assert runner.calls == []


def test_lower_spine_rejection_is_preserved(tmp_path: Path) -> None:
    fixed = datetime(2026, 7, 12, 12, 30, 0, tzinfo=timezone.utc)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    order = _base_order(fixed)
    runner = FakeRunner()

    result = invoke_reddog_extension_wre_operational_spine_explicit_valve(
        order,
        explicit_wre_operational_spine_requested=True,
        selection_receipt=_selection_receipt(),
        seen_nonces=set(),
        signature_verification_result=_accepted_signature(order),
        runner=runner,
        repo_root=repo_root,
        now=fixed,
    )

    assert result.decision == EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_REJECT
    assert ExtensionWREOperationalSpineInvokeReason.WORKTREE_SPINE_REJECTED in result.rejection_reasons
    assert "execution_valve_not_open_for_worktree_create" in result.rejection_reasons
    assert "explicit_valve_flag_missing" in result.rejection_reasons
    assert runner.calls == []


def test_sovereign_token_is_not_emitted(tmp_path: Path) -> None:
    fixed = datetime(2026, 7, 12, 12, 35, 0, tzinfo=timezone.utc)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    order = _base_order(fixed, nonce="nonce-extension-wre-spine-token")

    result = invoke_reddog_extension_wre_operational_spine_explicit_valve(
        order,
        explicit_wre_operational_spine_requested=True,
        selection_receipt=_selection_receipt(),
        seen_nonces=set(),
        valve_environment=_open_worktree_env(),
        signature_verification_result=_accepted_signature(order),
        runner=FakeRunner(),
        repo_root=repo_root,
        now=fixed,
        locks=set(),
    )

    assert result.decision == EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_ACCEPT
    assert _TOKEN not in json.dumps(result.to_dict(), sort_keys=True)


def test_ast_boundary_no_extension_runtime_openclaw_hermes_or_command_execution() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imports = set()
    calls = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    forbidden_import_fragments = (
        "subprocess",
        "reddog_wre_worktree_runner",
        "openclaw",
        "agent_db",
        "hermes",
        "wre_core",
        "skillz",
    )
    forbidden_calls = {
        "open",
        "eval",
        "exec",
        "system",
        "popen",
        "run",
        "check_call",
        "check_output",
    }
    assert not any(fragment in imported for imported in imports for fragment in forbidden_import_fragments)
    assert not (calls & forbidden_calls)


def test_extension_runtime_not_modified_by_this_slice() -> None:
    text = EXTENSION_JS.read_text(encoding="utf-8")
    assert "invoke_reddog_extension_wre_operational_spine_explicit_valve" not in text
    assert "reddog_extension_wre_operational_spine_invoke.py" not in text
