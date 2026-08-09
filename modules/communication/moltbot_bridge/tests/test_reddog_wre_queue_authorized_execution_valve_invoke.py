"""Tests for REDDOG_WRE_QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_PHASE1."""

from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    INTAKE_ASSIGNMENT_DISPATCHER,
    INTAKE_FOUNDUP_JOB,
    VALVE_CLOSED,
    VALVE_OPEN_WORKTREE_CREATE,
    ExecutionValveEnvironment,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_execution_valve_invoke import (
    QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT,
    QueueAuthorizedExecutionValveInvokeReason,
    invoke_reddog_wre_queue_authorized_execution_valve,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_executor_plan_dryrun import (
    QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
    QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_verified_authority_work_order_invoke import (
    QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
    QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_work_authority_digest import (
    canonical_work_authority_digest,
)
from modules.communication.moltbot_bridge.src import (
    reddog_progressive_execution_stage_policy as stage_policy,
)
from modules.communication.moltbot_bridge.tests.reddog_signed_worker_dispatch_test_support import (
    bounded_allocation,
    signed_audit_stage_binding,
    signed_stage_binding,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_wre_queue_authorized_execution_valve_invoke.py"
)
NOW = datetime(2026, 7, 14, 13, 0, 0, tzinfo=timezone.utc)
WORK_ORDER_ID = "wre-queue-authorized-valve-001"
REPO = "FOUNDUPS/Foundups-Agent"
FID = "paccess_001"
TARGET = f"modules/foundups/{FID}/README.md"
INVOCATION_DIGEST = "sha256:" + ("e" * 64)
POLICY_DIGEST = "sha256:" + ("f" * 64)


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
        "requested_operation": "edit_foundup_module",
        "authority_tier": "source",
        "allowed_paths": [TARGET],
        "denied_paths": [".env", ".git/**"],
        "branch_name": "feat/paccess-001-valve",
        "base_ref": "main",
        "task_summary": "Evaluate queue-authorized execution valve.",
        "wsp_applicability": ["WSP_34", "WSP_50", "WSP_97"],
        "holoindex_evidence_refs": [
            "modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py"
        ],
        "skillz_candidates": [],
        "required_tests": ["pytest modules/communication/moltbot_bridge/tests"],
        "required_policy_gates": ["openclaw_policy_gate", "signed_work_order_authority"],
        "required_reviewers": [],
        "sentinel_checks": [],
        "rollback_plan": "Remove worktree and delete branch on abort.",
        "expiry": _future_expiry(),
        "nonce": "work-order-nonce-valve",
        "evidence_digest": "sha256:" + ("a" * 64),
        "advisory_only_source_packet": {
            "work_focus_digest": "sha256:" + ("b" * 64),
            "wsp_prompt_digest": "sha256:" + ("c" * 64),
            "copy_md_run_trace_digest": "sha256:" + ("d" * 64),
        },
        "holoindex_evidence": {
            "holoindex_query": "RedDog queue authorized execution valve",
            "holoindex_status": "bundle_json_ok",
            "code_hits": ["modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py"],
            "wsp_hits": ["WSP_framework/src/WSP_34_Git_Operations_Protocol.md"],
            "skillz_hits": [],
            "direct_read_fallback_used": True,
            "index_gap_detected": False,
            "applicable_wsps": ["WSP_34", "WSP_97"],
            "evidence_refs": [
                "modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py"
            ],
            "retrieval_quality": "HIGH",
            "skillz_gap_detected": False,
        },
    }
    payload.update(overrides)
    return payload


def _invocation_payload(**overrides):
    payload = {
        "decision": "INVOCATION_ACCEPT",
        "work_order_id": WORK_ORDER_ID,
        "policy_gate_decision": "POLICY_ACCEPT",
        "receipt_id": "reddog-work-order-receipt-001",
        "receipt_digest": INVOCATION_DIGEST,
        "no_execution_performed": True,
        "rejection_reasons": [],
        "gates_checked": ["signed_work_order_authority"],
        "idempotent_replay": False,
        "policy_gate_receipt_digest": POLICY_DIGEST,
    }
    payload.update(overrides)
    return payload


def _queue_work_order_result(**overrides):
    payload = {
        "decision": QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
        "rejection_reasons": [],
        "invocation_result": _invocation_payload(),
        "explicit_queue_work_order_invocation_requested": True,
    }
    payload.update(overrides)
    return payload


def _executor_payload(**overrides):
    payload = {
        "decision": "EXECUTOR_PLAN_ACCEPT",
        "work_order_id": WORK_ORDER_ID,
        "plan": {
            "plan_id": "plan-001",
            "work_order_id": WORK_ORDER_ID,
            "proposed_branch_name": "feat/paccess-001-valve",
            "proposed_worktree_path": "/tmp/.reddog/worktrees/repo/work/nonce/",
            "lock_key": WORK_ORDER_ID,
            "allowed_paths": [TARGET],
            "denied_paths": [".env", ".git/**"],
            "required_tests": ["pytest modules/communication/moltbot_bridge/tests"],
            "cleanup_plan": {"on_failure": "remove_worktree_delete_branch"},
            "phase_receipts": [],
            "no_mutation_performed": True,
            "invocation_receipt_digest": INVOCATION_DIGEST,
            "plan_digest": "sha256:" + ("1" * 64),
        },
        "rejection_reasons": [],
        "rejection_receipt_digest": "",
        "no_mutation_performed": True,
        "phase_receipts": [],
    }
    payload.update(overrides)
    return payload


def _queue_executor_result(**overrides):
    payload = {
        "decision": QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
        "rejection_reasons": [],
        "executor_plan_result": _executor_payload(),
        "explicit_queue_authorized_executor_plan_requested": True,
    }
    payload.update(overrides)
    return payload


def _open_env() -> ExecutionValveEnvironment:
    return ExecutionValveEnvironment(
        valve_worktree_create_enabled=True,
        sovereign_worktree_token="012-sovereign-worktree-token",
    )


def _signed_authority(**overrides):
    payload = signed_stage_binding(
        requested_operation="edit_foundup_module",
        changed_paths=(TARGET,),
    )
    payload.update(
        requested_operation="edit_foundup_module",
        allowed_paths=(TARGET,),
        denied_paths=(),
    )
    payload.update(overrides)
    return payload


def test_queue_authorized_chain_opens_expected_worktree_valve_only() -> None:
    result = invoke_reddog_wre_queue_authorized_execution_valve(
        explicit_queue_authorized_execution_valve_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(),
        queue_executor_plan_result=_queue_executor_result(),
        work_order=_work_order(),
        signed_work_authority=_signed_authority(),
        verified_work_authority_digest=canonical_work_authority_digest(
            _signed_authority()
        ),
        valve_environment=_open_env(),
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT
    assert result.rejection_reasons == []
    assert result.valve_decision is not None
    assert result.valve_decision.valve_state == VALVE_OPEN_WORKTREE_CREATE
    assert result.valve_decision.no_execution_performed is True
    assert result.no_worktree_created is True
    assert result.no_shell_command_executed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_repo_mutation_performed is True
    assert result.no_holoindex_reindex_performed is True
    assert result.no_pr_created is True


def test_explicit_invoke_missing_rejects() -> None:
    result = invoke_reddog_wre_queue_authorized_execution_valve(
        explicit_queue_authorized_execution_valve_requested=False,
        queue_work_order_invocation_result=_queue_work_order_result(),
        queue_executor_plan_result=_queue_executor_result(),
        work_order=_work_order(),
        signed_work_authority=_signed_authority(),
        verified_work_authority_digest=canonical_work_authority_digest(
            _signed_authority()
        ),
        valve_environment=_open_env(),
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
    assert QueueAuthorizedExecutionValveInvokeReason.EXPLICIT_INVOKE_MISSING in result.rejection_reasons
    assert result.valve_decision is None


def test_default_closed_valve_rejects_with_decision() -> None:
    result = invoke_reddog_wre_queue_authorized_execution_valve(
        explicit_queue_authorized_execution_valve_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(),
        queue_executor_plan_result=_queue_executor_result(),
        work_order=_work_order(),
        signed_work_authority=_signed_authority(),
        verified_work_authority_digest=canonical_work_authority_digest(
            _signed_authority()
        ),
        valve_environment=ExecutionValveEnvironment(),
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
    assert QueueAuthorizedExecutionValveInvokeReason.VALVE_STATE_NOT_EXPECTED in result.rejection_reasons
    assert "explicit_valve_flag_missing" in result.rejection_reasons
    assert result.valve_decision is not None
    assert result.valve_decision.valve_state == VALVE_CLOSED


def test_worktree_valve_without_token_rejects() -> None:
    result = invoke_reddog_wre_queue_authorized_execution_valve(
        explicit_queue_authorized_execution_valve_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(),
        queue_executor_plan_result=_queue_executor_result(),
        work_order=_work_order(),
        signed_work_authority=_signed_authority(),
        verified_work_authority_digest=canonical_work_authority_digest(
            _signed_authority()
        ),
        valve_environment=ExecutionValveEnvironment(valve_worktree_create_enabled=True),
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
    assert "worktree_valve_missing_sovereign_token" in result.rejection_reasons
    assert result.valve_decision is not None
    assert result.valve_decision.valve_state == VALVE_CLOSED


def test_rejected_queue_work_order_invocation_blocks_before_valve() -> None:
    result = invoke_reddog_wre_queue_authorized_execution_valve(
        explicit_queue_authorized_execution_valve_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(
            decision=QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT
        ),
        queue_executor_plan_result=_queue_executor_result(),
        work_order=_work_order(),
        signed_work_authority=_signed_authority(),
        verified_work_authority_digest=canonical_work_authority_digest(
            _signed_authority()
        ),
        valve_environment=_open_env(),
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
    assert (
        QueueAuthorizedExecutionValveInvokeReason.WORK_ORDER_INVOCATION_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert result.valve_decision is None


def test_rejected_queue_executor_plan_blocks_before_valve() -> None:
    result = invoke_reddog_wre_queue_authorized_execution_valve(
        explicit_queue_authorized_execution_valve_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(),
        queue_executor_plan_result=_queue_executor_result(
            decision=QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT
        ),
        work_order=_work_order(),
        signed_work_authority=_signed_authority(),
        verified_work_authority_digest=canonical_work_authority_digest(
            _signed_authority()
        ),
        valve_environment=_open_env(),
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
    assert QueueAuthorizedExecutionValveInvokeReason.EXECUTOR_PLAN_NOT_ACCEPTED in result.rejection_reasons
    assert result.valve_decision is None


def test_receipt_chain_mismatch_rejects_through_valve() -> None:
    bad_executor = _executor_payload()
    bad_executor["plan"] = dict(bad_executor["plan"])
    bad_executor["plan"]["invocation_receipt_digest"] = "sha256:" + ("9" * 64)
    result = invoke_reddog_wre_queue_authorized_execution_valve(
        explicit_queue_authorized_execution_valve_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(),
        queue_executor_plan_result=_queue_executor_result(executor_plan_result=bad_executor),
        work_order=_work_order(),
        signed_work_authority=_signed_authority(),
        verified_work_authority_digest=canonical_work_authority_digest(
            _signed_authority()
        ),
        valve_environment=_open_env(),
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
    assert "executor_plan_invocation_digest_mismatch" in result.rejection_reasons
    assert result.valve_decision is not None
    assert result.valve_decision.valve_state == VALVE_CLOSED


def test_forbidden_assignment_dispatcher_target_rejects() -> None:
    result = invoke_reddog_wre_queue_authorized_execution_valve(
        explicit_queue_authorized_execution_valve_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(),
        queue_executor_plan_result=_queue_executor_result(),
        work_order=_work_order(),
        signed_work_authority=_signed_authority(),
        verified_work_authority_digest=canonical_work_authority_digest(
            _signed_authority()
        ),
        valve_environment=_open_env(),
        intake_target=INTAKE_ASSIGNMENT_DISPATCHER,
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
    assert "assignment_dispatcher_forbidden_target" in result.rejection_reasons


def test_result_is_json_serializable() -> None:
    result = invoke_reddog_wre_queue_authorized_execution_valve(
        explicit_queue_authorized_execution_valve_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(),
        queue_executor_plan_result=_queue_executor_result(),
        work_order=_work_order(),
        signed_work_authority=_signed_authority(),
        verified_work_authority_digest=canonical_work_authority_digest(
            _signed_authority()
        ),
        valve_environment=_open_env(),
        intake_target=INTAKE_FOUNDUP_JOB,
        now=NOW,
    )

    payload = result.to_dict()
    assert payload["decision"] == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT
    assert payload["valve_decision"]["valve_state"] == VALVE_OPEN_WORKTREE_CREATE
    json.dumps(payload)


def test_signed_audit_authority_cannot_open_effect_valve() -> None:
    result = invoke_reddog_wre_queue_authorized_execution_valve(
        explicit_queue_authorized_execution_valve_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(),
        queue_executor_plan_result=_queue_executor_result(),
        work_order=_work_order(),
        signed_work_authority=signed_audit_stage_binding(),
        verified_work_authority_digest=canonical_work_authority_digest(
            signed_audit_stage_binding()
        ),
        valve_environment=_open_env(),
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
    assert result.rejection_reasons == [
        QueueAuthorizedExecutionValveInvokeReason.BOUNDED_EXECUTION_STAGE_REQUIRED
    ]
    assert result.valve_decision is None


def test_attacker_rehashed_protected_foundup_stage_cannot_open_effect_valve() -> None:
    path = "modules/foundups/trade/src/scoring_integration.py"
    allocation = bounded_allocation(changed_paths=(path,))
    authority = signed_stage_binding()
    authority.update(
        requested_operation="edit_foundup_module",
        allowed_paths=(TARGET,),
        denied_paths=(),
    )
    trusted_digest = canonical_work_authority_digest(authority)
    stage = dict(authority["progressive_policy_stage_receipt"])
    stage.update(
        changed_paths=(path,),
        wsp15_allocation_receipt_id=allocation["receipt_id"],
        wsp15_allocation_digest=(
            stage_policy.canonical_reddog_wsp15_allocation_digest(allocation)
        ),
        complexity=allocation["complexity"],
        risk_classes=(),
        would_block_reasons=(),
        rejection_reasons=(),
    )
    stage["receipt_id"] = stage_policy._digest(stage_policy._unsigned(stage))
    authority.update(
        wsp15_allocation_receipt=allocation,
        wsp15_allocation_receipt_id=allocation["receipt_id"],
        wsp15_allocation_digest=stage["wsp15_allocation_digest"],
        wsp15_priority=allocation["priority"],
        wsp15_mps_total=allocation["mps_total"],
        wsp15_reasoning_tier=allocation["reasoning_tier"],
        progressive_policy_stage_receipt_id=stage["receipt_id"],
        progressive_policy_stage_digest=stage_policy._digest(stage),
        progressive_policy_stage_receipt=stage,
        requested_operation=allocation["requested_operation"],
        allowed_paths=(path,),
        denied_paths=(),
    )

    result = invoke_reddog_wre_queue_authorized_execution_valve(
        explicit_queue_authorized_execution_valve_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(),
        queue_executor_plan_result=_queue_executor_result(),
        work_order=_work_order(allowed_paths=[path]),
        signed_work_authority=authority,
        verified_work_authority_digest=trusted_digest,
        valve_environment=_open_env(),
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
    assert result.rejection_reasons == [
        QueueAuthorizedExecutionValveInvokeReason.VERIFIED_AUTHORITY_DIGEST_MISMATCH
    ]
    assert result.valve_decision is None

    rehashed = invoke_reddog_wre_queue_authorized_execution_valve(
        explicit_queue_authorized_execution_valve_requested=True,
        queue_work_order_invocation_result=_queue_work_order_result(),
        queue_executor_plan_result=_queue_executor_result(),
        work_order=_work_order(allowed_paths=[path]),
        signed_work_authority=authority,
        verified_work_authority_digest=canonical_work_authority_digest(authority),
        valve_environment=_open_env(),
        now=NOW,
    )

    assert rehashed.decision == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
    assert rehashed.rejection_reasons == [
        QueueAuthorizedExecutionValveInvokeReason.BOUNDED_EXECUTION_STAGE_REQUIRED
    ]
    assert rehashed.valve_decision is None


def test_module_has_no_worktree_shell_openclaw_hermes_or_holoindex_imports() -> None:
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
