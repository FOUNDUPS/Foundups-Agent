"""Tests for REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import reddog_resident_queue_orchestration_plan as planner
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    governed_worker_dispatch_snapshot,
    with_queue_wsp15_allocation,
)
from modules.communication.moltbot_bridge.tests.reddog_signed_worker_dispatch_test_support import (
    governed_snapshot,
    readonly_allocation,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_orchestration_plan.py"
)
NOW = "2026-07-14T00:00:00+00:00"
EXPIRES = "2026-07-14T01:00:00+00:00"


def test_bounded_queue_fixture_rejects_high_risk_prompt() -> None:
    with pytest.raises(
        AssertionError,
        match="bounded queue test fixture was rejected by progressive policy",
    ):
        with_queue_wsp15_allocation(
            {"slice_id": "REDDOG_TEST_SLICE_PHASE1"},
            prompt_text="Publish signer authority changes",
        )


def _queue_wsp15_allocation_receipt() -> dict[str, object]:
    return allocate_reddog_wsp15_receipt(
        requested_operation="edit_foundup_module",
        prompt_text="Fix one bounded FoundUp module defect",
        changed_paths=("modules/foundups/paccess_001/src/worker.py",),
        allowed_read_targets=("modules/foundups/paccess_001/src/worker.py",),
    ).to_dict()


def _snapshot() -> dict[str, object]:
    allocation = _queue_wsp15_allocation_receipt()
    snapshot = {
        "schema_version": "reddog_authoritative_work_state.v1",
        "freshness_receipts": [
            {
                "receipt_id": "fresh-1",
                "fresh": True,
            }
        ],
        "worker_claims": [
            {
                "claim_id": "claim-1",
                "slice_id": "REDDOG_TEST_SLICE_PHASE1",
                "worker_id": "reddog-0102",
                "status": "ACTIVE",
                "expires_at": EXPIRES,
                "freshness_receipt_id": "fresh-1",
            }
        ],
        "wre_queue_items": [
            {
                "queue_item_id": "queue-1",
                "slice_id": "REDDOG_TEST_SLICE_PHASE1",
                "claim_id": "claim-1",
                "worker_id": "reddog-0102",
                "status": "QUEUED",
                "evidence_refs": [
                    "claim:claim-1",
                    "freshness:fresh-1",
                    f"wsp15_allocation:{allocation['receipt_id']}",
                ],
                "wsp15_allocation_receipt": allocation,
                "no_execution_performed": True,
            }
        ],
    }
    return governed_worker_dispatch_snapshot(
        snapshot,
        task_prompt_text="Fix one bounded FoundUp module defect",
    )


def _accepted_results_through(stage_key: str) -> dict[str, dict[str, object]]:
    values = {
        "authority_request": {
            "status": "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT",
        },
        "authority_runtime": {
            "decision": "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT",
        },
        "authority_verification": {
            "decision": "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT",
        },
        "worker_dispatch_dryrun": {
            "decision": "SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT",
        },
        "worker_dispatch_runtime": {
            "decision": "SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT",
        },
        "work_order_invocation": {
            "decision": "QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT",
        },
        "executor_plan": {
            "decision": "QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT",
        },
        "execution_valve": {
            "decision": "QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT",
        },
        "worktree_create": {
            "decision": "QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT",
        },
        "assurance_capacity_admission": {
            "decision": "ASSURANCE_CAPACITY_ADMISSION_ACCEPT",
        },
        "bounded_worker_pilot": {
            "decision": "QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT",
        },
        "exact_sha_commit": {
            "decision": "RESIDENT_QUEUE_EXACT_SHA_COMMIT_ACCEPT",
        },
        "slice_verifier": {
            "decision": "QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT",
        },
        "verified_draft_pr_publish": {
            "decision": "QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT",
        },
        "verified_outcome_ratchet": {
            "decision": "QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT",
        },
        "model_feedback_admission": {
            "decision": "QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_ACCEPT",
        },
        "held_out_regression_gate": {
            "decision": "QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT",
        },
        "pattern_memory_admission": {
            "decision": "QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT",
        },
    }
    ordered: dict[str, dict[str, object]] = {}
    for key, value in values.items():
        ordered[key] = value
        if key == stage_key:
            break
    return ordered


def test_autovalidates_queue_item_and_names_authority_request_as_next_action() -> None:
    result = planner.plan_reddog_resident_queue_orchestration(_snapshot(), now_iso=NOW)

    assert result.accepted is True
    assert result.status == planner.RESIDENT_QUEUE_ORCHESTRATION_PLAN_READY
    assert result.selected_queue_item_id == "queue-1"
    assert result.selected_slice == "REDDOG_TEST_SLICE_PHASE1"
    assert result.current_stage == "authority_request"
    assert result.missing_stage == "authority_request"
    assert result.next_action == planner.NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN
    assert result.accepted_stages == ("queue_consumer",)
    assert result.queue_consumer_result is not None
    assert result.queue_consumer_result["status"] == "WRE_QUEUE_CONSUMER_DRYRUN_READY"
    assert result.no_worker_spawn_performed is True
    assert result.no_holoindex_reindex_performed is True


def test_accepted_authority_request_advances_to_authority_runtime() -> None:
    result = planner.plan_reddog_resident_queue_orchestration(
        _snapshot(),
        now_iso=NOW,
        chain_results=_accepted_results_through("authority_request"),
    )

    assert result.accepted is True
    assert result.current_stage == "authority_runtime"
    assert result.next_action == planner.NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE
    assert result.accepted_stages == ("queue_consumer", "authority_request")


def test_bounded_worker_advances_to_exact_sha_commit_before_verifier() -> None:
    result = planner.plan_reddog_resident_queue_orchestration(
        _snapshot(),
        now_iso=NOW,
        chain_results=_accepted_results_through("bounded_worker_pilot"),
    )

    assert result.accepted is True
    assert result.current_stage == "exact_sha_commit"
    assert result.next_action == planner.NEXT_QUEUE_EXACT_SHA_COMMIT
    assert "slice_verifier" not in result.accepted_stages


def test_rejected_stage_fails_closed_and_does_not_skip_forward() -> None:
    result = planner.plan_reddog_resident_queue_orchestration(
        _snapshot(),
        now_iso=NOW,
        chain_results={
            "authority_request": {
                "status": "QUEUE_AUTHORITY_REQUEST_DRYRUN_REJECT",
                "rejection_reasons": ["FAIL_PROFILE_MISSING"],
            }
        },
    )

    assert result.accepted is False
    assert result.status == planner.RESIDENT_QUEUE_ORCHESTRATION_PLAN_REJECT
    assert result.next_action == "REJECT"
    assert f"{planner.FAIL_STAGE_REJECTED}:authority_request" in result.rejection_reasons
    assert "FAIL_PROFILE_MISSING" in result.rejection_reasons


def test_future_stage_without_required_current_stage_is_rejected_as_contamination() -> None:
    result = planner.plan_reddog_resident_queue_orchestration(
        _snapshot(),
        now_iso=NOW,
        chain_results={
            "authority_runtime": {
                "decision": "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT",
            }
        },
    )

    assert result.accepted is False
    assert result.current_stage == "authority_request"
    assert result.next_action == planner.NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN
    assert f"{planner.FAIL_OUT_OF_ORDER_STAGE_RESULT}:authority_request" in result.rejection_reasons
    assert "future_stage_present:authority_runtime" in result.rejection_reasons


def test_all_stages_accepted_completes_chain_without_mutation_authority() -> None:
    result = planner.plan_reddog_resident_queue_orchestration(
        _snapshot(),
        now_iso=NOW,
        chain_results=_accepted_results_through("pattern_memory_admission"),
    )

    assert result.accepted is True
    assert result.status == planner.RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE
    assert result.current_stage is None
    assert result.missing_stage is None
    assert result.next_action == planner.NEXT_QUEUE_CHAIN_COMPLETE
    assert result.accepted_stages[-1] == "pattern_memory_admission"
    assert result.no_pr_created is True
    assert result.no_pattern_memory_write_performed is True


def test_signed_readonly_audit_terminates_after_worker_dispatch() -> None:
    snapshot = governed_snapshot(readonly_allocation())
    result = planner.plan_reddog_resident_queue_orchestration(
        snapshot,
        now_iso=NOW,
        chain_results=_accepted_results_through("worker_dispatch_runtime"),
    )

    assert result.accepted is True
    assert result.status == planner.RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE
    assert result.current_stage is None
    assert "work_order_invocation" not in result.accepted_stages


def test_signed_readonly_audit_rejects_effect_stage_contamination() -> None:
    snapshot = governed_snapshot(readonly_allocation())
    contaminated = _accepted_results_through("work_order_invocation")

    result = planner.plan_reddog_resident_queue_orchestration(
        snapshot, now_iso=NOW, chain_results=contaminated
    )

    assert result.accepted is False
    assert any("work_order_invocation" in reason for reason in result.rejection_reasons)
    assert result.no_reward_settlement_performed is True


def test_invalid_snapshot_rejects_before_chain_planning() -> None:
    broken = _snapshot()
    broken["wre_queue_items"] = []

    result = planner.plan_reddog_resident_queue_orchestration(broken, now_iso=NOW)

    assert result.accepted is False
    assert result.current_stage == "queue_consumer"
    assert planner.FAIL_QUEUE_CONSUMER_NOT_READY in result.rejection_reasons
    assert "FAIL_NO_QUEUE_ITEM" in result.rejection_reasons


def test_supplied_queue_consumer_result_can_select_requested_queue_item() -> None:
    supplied = {
        "accepted": True,
        "status": "WRE_QUEUE_CONSUMER_DRYRUN_READY",
        "selected_queue_item_id": "queue-2",
        "selected_slice": "REDDOG_OTHER_SLICE_PHASE1",
        "rejection_reasons": [],
    }

    result = planner.plan_reddog_resident_queue_orchestration(
        _snapshot(),
        queue_consumer_result=supplied,
        chain_results={},
        requested_queue_item_id="queue-2",
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.selected_queue_item_id == "queue-2"
    assert result.selected_slice == "REDDOG_OTHER_SLICE_PHASE1"
    assert result.next_action == planner.NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN


def test_plan_id_is_deterministic_for_same_inputs() -> None:
    first = planner.plan_reddog_resident_queue_orchestration(
        _snapshot(),
        now_iso=NOW,
        chain_results=_accepted_results_through("executor_plan"),
    )
    second = planner.plan_reddog_resident_queue_orchestration(
        _snapshot(),
        now_iso=NOW,
        chain_results=_accepted_results_through("executor_plan"),
    )

    assert first.plan_id == second.plan_id


def test_result_is_json_serializable() -> None:
    result = planner.plan_reddog_resident_queue_orchestration(_snapshot(), now_iso=NOW)

    assert result.to_dict()["queue_consumer_result"]["selected_queue_item_id"] == "queue-1"


def test_chain_results_must_be_mapping() -> None:
    result = planner.plan_reddog_resident_queue_orchestration(
        _snapshot(),
        now_iso=NOW,
        chain_results=[],  # type: ignore[arg-type]
    )

    assert result.accepted is False
    assert planner.FAIL_CHAIN_RESULTS_NOT_MAPPING in result.rejection_reasons


def test_module_has_no_runtime_execution_or_reindex_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "holo_index",
    }
    banned_calls = {
        "eval",
        "exec",
        "compile",
        "__import__",
        "open",
    }
    banned_attrs = {
        "system",
        "popen",
        "spawn",
        "run",
        "Popen",
        "check_call",
        "check_output",
        "replace",
        "unlink",
        "remove",
        "rmdir",
        "rename",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in banned_import_roots
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs
