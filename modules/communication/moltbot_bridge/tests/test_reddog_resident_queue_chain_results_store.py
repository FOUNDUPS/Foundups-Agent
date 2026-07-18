"""Tests for REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_STORE_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_orchestration_plan_bootstrap import (
    run_reddog_main_resident_queue_orchestration_plan_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    CHAIN_RESULT_RECORDED,
    FAIL_ATOMIC_COMMIT_FAILED,
    FAIL_PROPOSED_PLAN_REJECTED,
    FAIL_STAGE_ALREADY_RECORDED,
    FAIL_STAGE_NOT_CURRENT,
    AtomicJsonResidentQueueChainResultsStore,
    InMemoryResidentQueueChainResultsStore,
    record_resident_queue_stage_result,
    resident_queue_chain_snapshot_is_canonical,
    resident_queue_chain_snapshot_revision,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE,
    NEXT_QUEUE_WORKTREE_CREATE_INVOKE,
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
    / "reddog_resident_queue_chain_results_store.py"
)
NOW = "2026-07-14T00:00:00+00:00"
EXPIRES = "2026-07-14T01:00:00+00:00"


def _queue_wsp15_allocation_receipt() -> dict[str, object]:
    return allocate_reddog_wsp15_receipt(
        requested_operation="create_foundup",
        prompt_text="RedDog resident queue chain result store worktree authority",
        changed_paths=("modules/communication/moltbot_bridge/src/reddog_resident_queue_chain_results_store.py",),
        allowed_read_targets=("modules/communication/moltbot_bridge/src/reddog_resident_queue_chain_results_store.py",),
    ).to_dict()


def _snapshot() -> dict[str, object]:
    allocation = _queue_wsp15_allocation_receipt()
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


def _accepted(stage: str) -> dict[str, object]:
    values = {
        "authority_request": {"status": "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT"},
        "authority_runtime": {"decision": "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT"},
        "authority_verification": {"decision": "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT"},
        "worker_dispatch_dryrun": {"decision": "SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT"},
        "worker_dispatch_runtime": {"decision": "SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT"},
        "work_order_invocation": {"decision": "QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT"},
        "executor_plan": {"decision": "QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT"},
        "execution_valve": {"decision": "QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT"},
    }
    return values[stage]


def _seed_store_through(stage: str) -> InMemoryResidentQueueChainResultsStore:
    order = (
        "authority_request",
        "authority_runtime",
        "authority_verification",
        "worker_dispatch_dryrun",
        "worker_dispatch_runtime",
        "work_order_invocation",
        "executor_plan",
        "execution_valve",
    )
    store = InMemoryResidentQueueChainResultsStore()
    for key in order:
        result = record_resident_queue_stage_result(
            work_state_snapshot=_snapshot(),
            store=store,
            stage_key=key,
            stage_result=_accepted(key),
            now_iso=NOW,
        )
        assert result.accepted is True
        if key == stage:
            break
    return store


def test_record_current_stage_advances_plan_and_persists_result() -> None:
    store = InMemoryResidentQueueChainResultsStore()

    result = record_resident_queue_stage_result(
        work_state_snapshot=_snapshot(),
        store=store,
        stage_key="authority_request",
        stage_result=_accepted("authority_request"),
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.status == CHAIN_RESULT_RECORDED
    assert result.receipt is not None
    assert result.receipt.recorded_stage == "authority_request"
    assert result.next_plan is not None
    assert result.next_plan.next_action == NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE
    state = store.load()
    assert state["schema_version"] == "reddog_resident_queue_chain_results.v1"
    assert state["stage_results"]["authority_request"]["status"] == "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT"
    assert state["no_bridge_invoked"] is True
    assert state["no_holoindex_reindex_performed"] is True


def test_rejects_out_of_order_stage_without_commit() -> None:
    store = InMemoryResidentQueueChainResultsStore()

    result = record_resident_queue_stage_result(
        work_state_snapshot=_snapshot(),
        store=store,
        stage_key="authority_runtime",
        stage_result=_accepted("authority_runtime"),
        now_iso=NOW,
    )

    assert result.accepted is False
    assert FAIL_STAGE_NOT_CURRENT in result.rejection_reasons
    assert store.load() == {}


def test_rejects_duplicate_stage_without_overwrite() -> None:
    store = _seed_store_through("authority_request")

    result = record_resident_queue_stage_result(
        work_state_snapshot=_snapshot(),
        store=store,
        stage_key="authority_request",
        stage_result=_accepted("authority_request"),
        now_iso=NOW,
    )

    assert result.accepted is False
    assert FAIL_STAGE_ALREADY_RECORDED in result.rejection_reasons
    assert store.load()["stage_results"]["authority_request"]["status"] == "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT"


def test_rejected_stage_result_does_not_commit() -> None:
    store = InMemoryResidentQueueChainResultsStore()

    result = record_resident_queue_stage_result(
        work_state_snapshot=_snapshot(),
        store=store,
        stage_key="authority_request",
        stage_result={
            "status": "QUEUE_AUTHORITY_REQUEST_DRYRUN_REJECT",
            "rejection_reasons": ["FAIL_PROFILE_MISSING"],
        },
        now_iso=NOW,
    )

    assert result.accepted is False
    assert FAIL_PROPOSED_PLAN_REJECTED in result.rejection_reasons
    assert "FAIL_PROFILE_MISSING" in result.rejection_reasons
    assert store.load() == {}


def test_commit_failure_fails_closed() -> None:
    store = InMemoryResidentQueueChainResultsStore(fail_commit=True)

    result = record_resident_queue_stage_result(
        work_state_snapshot=_snapshot(),
        store=store,
        stage_key="authority_request",
        stage_result=_accepted("authority_request"),
        now_iso=NOW,
    )

    assert result.accepted is False
    assert FAIL_ATOMIC_COMMIT_FAILED in result.rejection_reasons
    assert store.load() == {}


def test_atomic_json_store_writes_schema_for_bootstrap(tmp_path: Path) -> None:
    path = tmp_path / "runtime" / "chain_results.json"
    store = AtomicJsonResidentQueueChainResultsStore(path)

    result = record_resident_queue_stage_result(
        work_state_snapshot=_snapshot(),
        store=store,
        stage_key="authority_request",
        stage_result=_accepted("authority_request"),
        now_iso=NOW,
    )

    assert result.accepted is True
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["revision"] == result.receipt.store_revision
    assert data["receipts"][-1]["store_revision"] == data["revision"]
    assert resident_queue_chain_snapshot_revision(data) == data["revision"]
    assert resident_queue_chain_snapshot_is_canonical(data) is True
    assert store.load() == data
    assert data["stage_results"]["authority_request"]["status"] == "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT"
    assert not list(path.parent.glob("*.tmp"))


def test_bootstrap_reads_chain_results_store_schema(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    state_path = tmp_path / "runtime" / "work_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(_snapshot(), sort_keys=True), encoding="utf-8")
    chain_path = tmp_path / "runtime" / "chain_results.json"
    store = AtomicJsonResidentQueueChainResultsStore(chain_path)
    record_resident_queue_stage_result(
        work_state_snapshot=_snapshot(),
        store=store,
        stage_key="authority_request",
        stage_result=_accepted("authority_request"),
        now_iso=NOW,
    )

    result = run_reddog_main_resident_queue_orchestration_plan_bootstrap(
        repo_root=repo,
        work_state_path=state_path,
        chain_results_path=chain_path,
        now_iso=NOW,
    )

    assert result.ready is True
    assert result.current_stage == "authority_runtime"
    assert result.next_action == NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE
    assert result.accepted_stage_count == 2


def test_multi_stage_recording_keeps_serial_order() -> None:
    store = _seed_store_through("executor_plan")

    result = record_resident_queue_stage_result(
        work_state_snapshot=_snapshot(),
        store=store,
        stage_key="execution_valve",
        stage_result=_accepted("execution_valve"),
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.previous_plan is not None
    assert result.previous_plan.current_stage == "execution_valve"
    assert result.next_plan is not None
    assert result.next_plan.next_action == NEXT_QUEUE_WORKTREE_CREATE_INVOKE
    assert result.next_plan.current_stage == "worktree_create"


def test_module_has_no_bridge_invocation_or_reindex_imports() -> None:
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
    banned_attrs = {
        "system",
        "popen",
        "spawn",
        "run",
        "Popen",
        "check_call",
        "check_output",
        "remove",
        "rmdir",
        "rename",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs
