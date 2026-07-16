"""Tests for REDDOG_RESIDENT_QUEUE_WORKER_DISPATCH_DRYRUN_STAGE_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    InMemoryResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    FAIL_RECORD_REJECTED,
    RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT,
    ResidentQueueStageDispatchRequest,
    invoke_reddog_resident_queue_next_stage_dispatch,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_WORKER_DISPATCH_DRYRUN,
    NEXT_QUEUE_WORKER_DISPATCH_RUNTIME,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_worker_dispatch_dryrun_handler import (
    AUTHORITY_RUNTIME_STAGE_KEY,
    AUTHORITY_VERIFICATION_STAGE_KEY,
    FAIL_AUTHORITY_RUNTIME_STAGE_MISSING,
    FAIL_AUTHORITY_VERIFICATION_STAGE_MISSING,
    FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
    FAIL_DISPATCH_STAGE_MISMATCH,
    FAIL_QUEUE_ITEM_MISSING,
    FAIL_WSP15_ALLOCATION_MISSING,
    WORKER_DISPATCH_DRYRUN_STAGE_KEY,
    build_reddog_resident_queue_worker_dispatch_dryrun_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT,
    SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_REJECT,
    SignedAuthorityWorkerDispatchDryRunReason,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    AUTHORITY_ISSUED,
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


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_worker_dispatch_dryrun_handler.py"
)
NOW_ISO = "2026-07-14T00:00:00+00:00"
EXPIRES = "2026-07-14T01:00:00+00:00"


def _digest(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _allocation(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "reddog_wsp15_allocation_receipt.v1",
        "receipt_id": "sha256:wsp15-allocation",
        "mps_total": 20,
        "priority": "P0",
        "reasoning_tier": "ULTRA",
        "worker_plan": {
            "schema_version": "reddog_wsp15_worker_plan.v1",
            "fusion_required": True,
            "reasoning_tier": "ULTRA",
            "critic_count": 2,
            "coding_worker_count": 2,
            "independent_verifier_required": True,
            "openclaw_candidate": True,
            "hermes_execution_allowed": False,
            "queue_mutation_allowed": False,
            "mode_selection_source": "reddog_wsp15_allocation_receipt.v1",
        },
    }
    payload.update(overrides)
    return payload


def _work_authority(allocation: dict[str, object] | None = None, **overrides: object) -> dict[str, object]:
    allocation = allocation or _allocation()
    payload: dict[str, object] = {
        "work_order_id": "wo-1",
        "principal_id": "github:mjtrout",
        "reddog_id": "reddog:abc123",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "foundup_id": "paccess_001",
        "allowed_paths": ["modules/foundups/paccess_001/src/app.py"],
        "denied_paths": [],
        "requested_operation": "create_foundup",
        "permission_snapshot_digest": "sha256:permission-snapshot",
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "wsp15_allocation_digest": _digest(allocation),
        "wsp15_priority": allocation["priority"],
        "wsp15_mps_total": allocation["mps_total"],
        "wsp15_reasoning_tier": allocation["reasoning_tier"],
        "nonce": "nonce-1",
        "issued_at": 1000,
        "expires_at": 1100,
        "valve_state_required": "VALVE_OPEN_WORKTREE_CREATE",
        "key_epoch": "epoch-1",
        "signature": "sig-work",
    }
    payload.update(overrides)
    return payload


def _runtime_result(allocation: dict[str, object] | None = None) -> dict[str, object]:
    allocation = allocation or _allocation()
    return {
        "decision": QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
        "authority_result": {
            "accepted": True,
            "receipt": {"status": AUTHORITY_ISSUED, "receipt_id": "auth-1"},
            "work_authority": _work_authority(allocation),
        },
    }


def _verification_result() -> dict[str, object]:
    return {
        "decision": QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
        "verification_result": {
            "accepted": True,
            "reason_codes": [],
            "work_order_id": "wo-1",
        },
    }


def _snapshot(allocation: dict[str, object] | None = None, *, queue_item_id: str = "queue-1") -> dict[str, object]:
    allocation = allocation or _allocation()
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
                "queue_item_id": queue_item_id,
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


def _store(allocation: dict[str, object] | None = None) -> InMemoryResidentQueueChainResultsStore:
    allocation = allocation or _allocation()
    return InMemoryResidentQueueChainResultsStore(
        {
            "schema_version": "reddog_resident_queue_chain_results.v1",
            "queue_item_id": "queue-1",
            "selected_slice": "REDDOG_TEST_SLICE_PHASE1",
            "stage_results": {
                "authority_request": {"status": QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT},
                AUTHORITY_RUNTIME_STAGE_KEY: _runtime_result(allocation),
                AUTHORITY_VERIFICATION_STAGE_KEY: _verification_result(),
            },
        }
    )


def _handler(
    *,
    snapshot: dict[str, object] | None = None,
    store: InMemoryResidentQueueChainResultsStore | None = None,
):
    return build_reddog_resident_queue_worker_dispatch_dryrun_stage_handler(
        work_state_snapshot=snapshot or _snapshot(),
        chain_results_store=store or _store(),
    )


def test_dispatcher_records_worker_dispatch_dryrun_and_advances_to_work_order_invocation() -> None:
    allocation = _allocation()
    store = _store(allocation)
    snapshot = _snapshot(allocation)

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=snapshot,
        store=store,
        handlers={WORKER_DISPATCH_DRYRUN_STAGE_KEY: _handler(snapshot=snapshot, store=store)},
        now_iso=NOW_ISO,
        requested_queue_item_id="queue-1",
    )

    assert result.accepted is True
    assert result.decision == RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT
    assert result.dispatched_stage == WORKER_DISPATCH_DRYRUN_STAGE_KEY
    assert result.next_action == NEXT_QUEUE_WORKER_DISPATCH_RUNTIME
    stage = store.load()["stage_results"][WORKER_DISPATCH_DRYRUN_STAGE_KEY]
    assert stage["accepted"] is True
    assert stage["decision"] == SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT
    assert stage["receipt"]["dispatch_intent_count"] == 7
    assert stage["receipt"]["no_worker_spawn_performed"] is True
    assert stage["receipt"]["no_openclaw_enqueue_performed"] is True
    assert stage["receipt"]["no_hermes_dispatch_performed"] is True


def test_missing_authority_runtime_stage_rejects_direct_handler_call() -> None:
    store = InMemoryResidentQueueChainResultsStore(
        {
            "schema_version": "reddog_resident_queue_chain_results.v1",
            "stage_results": {AUTHORITY_VERIFICATION_STAGE_KEY: _verification_result()},
        }
    )
    request = ResidentQueueStageDispatchRequest(
        stage_key=WORKER_DISPATCH_DRYRUN_STAGE_KEY,
        next_action=NEXT_QUEUE_WORKER_DISPATCH_DRYRUN,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=("authority_request", AUTHORITY_RUNTIME_STAGE_KEY, AUTHORITY_VERIFICATION_STAGE_KEY),
    )

    result = dict(_handler(store=store)(request))

    assert result["decision"] == SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_REJECT
    assert FAIL_AUTHORITY_RUNTIME_STAGE_MISSING in result["rejection_reasons"]


def test_missing_authority_verification_stage_rejects_direct_handler_call() -> None:
    store = InMemoryResidentQueueChainResultsStore(
        {
            "schema_version": "reddog_resident_queue_chain_results.v1",
            "stage_results": {AUTHORITY_RUNTIME_STAGE_KEY: _runtime_result()},
        }
    )
    request = ResidentQueueStageDispatchRequest(
        stage_key=WORKER_DISPATCH_DRYRUN_STAGE_KEY,
        next_action=NEXT_QUEUE_WORKER_DISPATCH_DRYRUN,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=("authority_request", AUTHORITY_RUNTIME_STAGE_KEY),
    )

    result = dict(_handler(store=store)(request))

    assert result["decision"] == SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_REJECT
    assert FAIL_AUTHORITY_VERIFICATION_STAGE_MISSING in result["rejection_reasons"]


def test_missing_queue_item_rejects_before_planner_call() -> None:
    request = ResidentQueueStageDispatchRequest(
        stage_key=WORKER_DISPATCH_DRYRUN_STAGE_KEY,
        next_action=NEXT_QUEUE_WORKER_DISPATCH_DRYRUN,
        queue_item_id="queue-missing",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=("authority_request", AUTHORITY_RUNTIME_STAGE_KEY, AUTHORITY_VERIFICATION_STAGE_KEY),
    )

    result = dict(_handler()(request))

    assert result["decision"] == SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_REJECT
    assert FAIL_QUEUE_ITEM_MISSING in result["rejection_reasons"]
    assert "queue_item_id:queue-missing" in result["rejection_reasons"]


def test_missing_queue_allocation_rejects_before_planner_call() -> None:
    snapshot = _snapshot()
    snapshot["wre_queue_items"][0].pop("wsp15_allocation_receipt")  # type: ignore[index]
    request = ResidentQueueStageDispatchRequest(
        stage_key=WORKER_DISPATCH_DRYRUN_STAGE_KEY,
        next_action=NEXT_QUEUE_WORKER_DISPATCH_DRYRUN,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=("authority_request", AUTHORITY_RUNTIME_STAGE_KEY, AUTHORITY_VERIFICATION_STAGE_KEY),
    )

    result = dict(_handler(snapshot=snapshot)(request))

    assert result["decision"] == SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_REJECT
    assert FAIL_WSP15_ALLOCATION_MISSING in result["rejection_reasons"]


def test_allocation_tamper_is_not_recorded_by_dispatcher() -> None:
    signed_allocation = _allocation()
    tampered_allocation = _allocation(mps_total=19)
    store = _store(signed_allocation)
    snapshot = _snapshot(tampered_allocation)

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=snapshot,
        store=store,
        handlers={WORKER_DISPATCH_DRYRUN_STAGE_KEY: _handler(snapshot=snapshot, store=store)},
        now_iso=NOW_ISO,
        requested_queue_item_id="queue-1",
    )

    assert result.accepted is False
    assert FAIL_RECORD_REJECTED in result.rejection_reasons
    assert SignedAuthorityWorkerDispatchDryRunReason.WSP15_DIGEST_MISMATCH in result.rejection_reasons
    assert WORKER_DISPATCH_DRYRUN_STAGE_KEY not in store.load()["stage_results"]


def test_wrong_stage_rejects_direct_handler_call() -> None:
    request = ResidentQueueStageDispatchRequest(
        stage_key="authority_verification",
        next_action=NEXT_QUEUE_WORKER_DISPATCH_DRYRUN,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=("authority_request", AUTHORITY_RUNTIME_STAGE_KEY),
    )

    result = dict(_handler()(request))

    assert result["decision"] == SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_REJECT
    assert FAIL_DISPATCH_STAGE_MISMATCH in result["rejection_reasons"]


def test_wrong_next_action_rejects_direct_handler_call() -> None:
    request = ResidentQueueStageDispatchRequest(
        stage_key=WORKER_DISPATCH_DRYRUN_STAGE_KEY,
        next_action="RUN_QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE",
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=("authority_request", AUTHORITY_RUNTIME_STAGE_KEY),
    )

    result = dict(_handler()(request))

    assert result["decision"] == SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_REJECT
    assert FAIL_DISPATCH_NEXT_ACTION_MISMATCH in result["rejection_reasons"]


def test_module_has_no_worker_spawn_openclaw_hermes_shell_or_holoindex_imports() -> None:
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
        "openclaw_supervisor",
        "hermes_job_executor",
        "worker_assignment_protocol",
        "swarm_dispatch_integration",
        "worktree_pr_runner",
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
        "replace",
        "unlink",
        "remove",
        "rmdir",
        "rename",
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
