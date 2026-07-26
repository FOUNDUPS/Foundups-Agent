"""Tests for REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_RUNNER_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    InMemoryResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_CHAIN_COMPLETE,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_serial_loop import (
    FAIL_DISPATCH_REJECTED,
    FAIL_EXPLICIT_LOOP_MISSING,
    FAIL_MAX_STEPS_INVALID,
    MAX_RESIDENT_QUEUE_SERIAL_LOOP_STEPS,
    RESIDENT_QUEUE_SERIAL_LOOP_COMPLETE,
    RESIDENT_QUEUE_SERIAL_LOOP_LIMIT_REACHED,
    RESIDENT_QUEUE_SERIAL_LOOP_REJECT,
    run_reddog_resident_queue_serial_loop,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_request_dryrun import (
    QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_runtime_invoke import (
    QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_verification_invoke import (
    QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_bounded_worker_pilot_invoke import (
    QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_execution_valve_invoke import (
    QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_executor_plan_dryrun import (
    QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_held_out_regression_gate_invoke import (
    QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_model_feedback_ledger_admission_invoke import (
    QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_pattern_memory_admission_invoke import (
    QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_slice_verifier_invoke import (
    QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_draft_pr_publish_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_outcome_ratchet_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_worktree_create_invoke import (
    QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_verified_authority_work_order_invoke import (
    QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_serial_loop.py"
)
NOW = "2026-07-14T00:00:00+00:00"
EXPIRES = "2026-07-14T01:00:00+00:00"
STAGE_ACCEPT_VALUES = {
    "authority_request": ("status", QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT),
    "authority_runtime": ("decision", QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT),
    "authority_verification": ("decision", QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT),
    "worker_dispatch_dryrun": ("decision", SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT),
    "worker_dispatch_runtime": ("decision", SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT),
    "work_order_invocation": ("decision", QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT),
    "executor_plan": ("decision", QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT),
    "execution_valve": ("decision", QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT),
    "worktree_create": ("decision", QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT),
    "assurance_capacity_admission": (
        "decision",
        "ASSURANCE_CAPACITY_ADMISSION_ACCEPT",
    ),
    "bounded_worker_pilot": ("decision", QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT),
    "slice_verifier": ("decision", QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT),
    "verified_draft_pr_publish": ("decision", QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT),
    "verified_outcome_ratchet": ("decision", QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT),
    "model_feedback_admission": ("decision", QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_ACCEPT),
    "held_out_regression_gate": ("decision", QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT),
    "pattern_memory_admission": ("decision", QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT),
}


def _snapshot() -> dict[str, object]:
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation="create_foundup",
        prompt_text="RedDog resident queue serial loop runtime authority worktree execution",
        changed_paths=("modules/communication/moltbot_bridge/src/reddog_resident_queue_serial_loop.py",),
        allowed_read_targets=("modules/communication/moltbot_bridge/src/reddog_resident_queue_serial_loop.py",),
    ).to_dict()
    return {
        "schema_version": "reddog_authoritative_work_state.v1",
        "freshness_receipts": [{"receipt_id": "fresh-1", "fresh": True}],
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


def _handler(stage_key: str):
    field_name, accepted_value = STAGE_ACCEPT_VALUES[stage_key]

    def call(request: ResidentQueueStageDispatchRequest) -> dict[str, object]:
        assert request.stage_key == stage_key
        return {
            field_name: accepted_value,
            "queue_item_id": request.queue_item_id,
            "selected_slice": request.selected_slice,
            "stage_key": stage_key,
        }

    return call


def _handlers(*stage_keys: str):
    keys = stage_keys or tuple(STAGE_ACCEPT_VALUES)
    return {key: _handler(key) for key in keys}


def _complete_store() -> InMemoryResidentQueueChainResultsStore:
    return InMemoryResidentQueueChainResultsStore(
        {
            "schema_version": "reddog_resident_queue_chain_results.v1",
            "stage_results": {
                key: {field: value}
                for key, (field, value) in STAGE_ACCEPT_VALUES.items()
            },
        }
    )


def test_serial_loop_runs_all_injected_stages_to_chain_complete() -> None:
    store = InMemoryResidentQueueChainResultsStore()

    result = run_reddog_resident_queue_serial_loop(
        explicit_resident_queue_serial_loop_requested=True,
        work_state_snapshot=_snapshot(),
        store=store,
        handlers=_handlers(),
        now_iso=NOW,
        requested_queue_item_id="queue-1",
    )

    assert result.accepted is True
    assert result.status == RESIDENT_QUEUE_SERIAL_LOOP_COMPLETE
    assert result.steps_run == len(STAGE_ACCEPT_VALUES)
    assert result.dispatched_stages == tuple(STAGE_ACCEPT_VALUES)
    assert result.next_action == NEXT_QUEUE_CHAIN_COMPLETE
    assert result.final_plan is not None
    assert result.final_plan.status == "RESIDENT_QUEUE_ORCHESTRATION_PLAN_COMPLETE"
    assert result.no_default_handler_used is True
    assert result.no_holoindex_reindex_performed_by_loop is True
    stored = store.load()
    assert set(stored["stage_results"]) == set(STAGE_ACCEPT_VALUES)
    assert len(stored["stage_results"]) == len(STAGE_ACCEPT_VALUES)


def test_serial_loop_is_explicitly_requested() -> None:
    store = InMemoryResidentQueueChainResultsStore()

    result = run_reddog_resident_queue_serial_loop(
        explicit_resident_queue_serial_loop_requested=False,
        work_state_snapshot=_snapshot(),
        store=store,
        handlers=_handlers(),
        now_iso=NOW,
    )

    assert result.accepted is False
    assert result.status == RESIDENT_QUEUE_SERIAL_LOOP_REJECT
    assert result.rejection_reasons == [FAIL_EXPLICIT_LOOP_MISSING]
    assert result.steps_run == 0
    assert store.load() == {}


def test_serial_loop_rejects_invalid_max_steps() -> None:
    result = run_reddog_resident_queue_serial_loop(
        explicit_resident_queue_serial_loop_requested=True,
        work_state_snapshot=_snapshot(),
        store=InMemoryResidentQueueChainResultsStore(),
        handlers=_handlers(),
        now_iso=NOW,
        max_steps=MAX_RESIDENT_QUEUE_SERIAL_LOOP_STEPS + 1,
    )

    assert result.accepted is False
    assert result.rejection_reasons == [FAIL_MAX_STEPS_INVALID]


def test_serial_loop_stops_at_step_limit_with_next_action() -> None:
    store = InMemoryResidentQueueChainResultsStore()

    result = run_reddog_resident_queue_serial_loop(
        explicit_resident_queue_serial_loop_requested=True,
        work_state_snapshot=_snapshot(),
        store=store,
        handlers=_handlers(),
        now_iso=NOW,
        requested_queue_item_id="queue-1",
        max_steps=2,
    )

    assert result.accepted is True
    assert result.status == RESIDENT_QUEUE_SERIAL_LOOP_LIMIT_REACHED
    assert result.steps_run == 2
    assert result.dispatched_stages == ("authority_request", "authority_runtime")
    assert result.next_action == "RUN_QUEUE_AUTHORITY_VERIFICATION_INVOKE"


def test_serial_loop_rejects_when_next_handler_missing_after_progress() -> None:
    store = InMemoryResidentQueueChainResultsStore()

    result = run_reddog_resident_queue_serial_loop(
        explicit_resident_queue_serial_loop_requested=True,
        work_state_snapshot=_snapshot(),
        store=store,
        handlers=_handlers("authority_request"),
        now_iso=NOW,
        requested_queue_item_id="queue-1",
        max_steps=2,
    )

    assert result.accepted is False
    assert result.status == RESIDENT_QUEUE_SERIAL_LOOP_REJECT
    assert result.steps_run == 1
    assert result.dispatched_stages == ("authority_request",)
    assert FAIL_DISPATCH_REJECTED in result.rejection_reasons
    assert "FAIL_HANDLER_MISSING" in result.rejection_reasons
    assert "stage:authority_runtime" in result.rejection_reasons


def test_serial_loop_accepts_already_complete_chain_without_invoking_handler() -> None:
    calls: list[str] = []

    def should_not_run(request: ResidentQueueStageDispatchRequest) -> dict[str, object]:
        calls.append(request.stage_key)
        return {}

    result = run_reddog_resident_queue_serial_loop(
        explicit_resident_queue_serial_loop_requested=True,
        work_state_snapshot=_snapshot(),
        store=_complete_store(),
        handlers={"authority_request": should_not_run},
        now_iso=NOW,
        requested_queue_item_id="queue-1",
    )

    assert result.accepted is True
    assert result.status == RESIDENT_QUEUE_SERIAL_LOOP_COMPLETE
    assert result.steps_run == 0
    assert calls == []


def test_serial_loop_rejects_handler_exception_without_recording_stage() -> None:
    store = InMemoryResidentQueueChainResultsStore()

    def broken(request: ResidentQueueStageDispatchRequest) -> dict[str, object]:
        raise RuntimeError("boom")

    result = run_reddog_resident_queue_serial_loop(
        explicit_resident_queue_serial_loop_requested=True,
        work_state_snapshot=_snapshot(),
        store=store,
        handlers={"authority_request": broken},
        now_iso=NOW,
        requested_queue_item_id="queue-1",
    )

    assert result.accepted is False
    assert result.steps_run == 0
    assert FAIL_DISPATCH_REJECTED in result.rejection_reasons
    assert "FAIL_HANDLER_EXCEPTION" in result.rejection_reasons
    assert store.load() == {}


def test_serial_loop_to_dict_serializes_nested_results() -> None:
    result = run_reddog_resident_queue_serial_loop(
        explicit_resident_queue_serial_loop_requested=True,
        work_state_snapshot=_snapshot(),
        store=InMemoryResidentQueueChainResultsStore(),
        handlers=_handlers(),
        now_iso=NOW,
        requested_queue_item_id="queue-1",
        max_steps=1,
    )

    payload = result.to_dict()

    assert payload["status"] == RESIDENT_QUEUE_SERIAL_LOOP_LIMIT_REACHED
    assert payload["final_plan"]["current_stage"] == "authority_runtime"
    assert payload["dispatch_results"][0]["dispatched_stage"] == "authority_request"


def test_serial_loop_has_no_shell_network_holoindex_or_concrete_stage_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "os",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "holo_index",
        "git",
        "hmac",
        "secrets",
    }
    banned_import_fragments = {
        "reddog_resident_queue_authority_request_handler",
        "reddog_resident_queue_authority_runtime_handler",
        "reddog_resident_queue_authority_verification_handler",
        "reddog_resident_queue_worktree_create_handler",
        "reddog_resident_queue_verified_draft_pr_publish_handler",
        "reddog_resident_queue_pattern_memory_admission_handler",
        "openclaw_supervisor",
        "hermes_job_executor",
        "pattern_memory",
    }
    banned_calls = {"eval", "exec", "compile", "__import__", "open"}
    banned_attrs = {
        "system",
        "popen",
        "spawn",
        "run",
        "Popen",
        "check_call",
        "check_output",
        "unlink",
        "remove",
        "rmdir",
        "rename",
        "replace",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
                assert all(fragment not in alias.name for fragment in banned_import_fragments)
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
            assert all(fragment not in node.module for fragment in banned_import_fragments)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs
