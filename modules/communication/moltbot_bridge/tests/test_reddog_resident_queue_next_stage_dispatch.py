"""Tests for REDDOG_RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    InMemoryResidentQueueChainResultsStore,
    record_resident_queue_stage_result,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    FAIL_EXPLICIT_DISPATCH_MISSING,
    FAIL_HANDLER_EXCEPTION,
    FAIL_HANDLER_MISSING,
    FAIL_HANDLER_RESULT_INVALID,
    FAIL_RECORD_REJECTED,
    RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT,
    RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_REJECT,
    ResidentQueueStageDispatchRequest,
    invoke_reddog_resident_queue_next_stage_dispatch,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_next_stage_dispatch.py"
)
NOW = "2026-07-14T00:00:00+00:00"
EXPIRES = "2026-07-14T01:00:00+00:00"


def _snapshot() -> dict[str, object]:
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
                "evidence_refs": ["claim:claim-1", "freshness:fresh-1"],
                "no_execution_performed": True,
            }
        ],
    }


def _authority_request_accept() -> dict[str, object]:
    return {"status": "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT"}


def _authority_runtime_accept() -> dict[str, object]:
    return {"decision": "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT"}


class _RecordingHandler:
    def __init__(self, result: dict[str, object]) -> None:
        self.result = result
        self.requests: list[ResidentQueueStageDispatchRequest] = []

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> dict[str, object]:
        self.requests.append(request)
        return dict(self.result)


def test_explicit_flag_required_before_handler_invocation() -> None:
    handler = _RecordingHandler(_authority_request_accept())
    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=False,
        work_state_snapshot=_snapshot(),
        store=InMemoryResidentQueueChainResultsStore(),
        handlers={"authority_request": handler},
        now_iso=NOW,
    )

    assert result.accepted is False
    assert result.decision == RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_REJECT
    assert FAIL_EXPLICIT_DISPATCH_MISSING in result.rejection_reasons
    assert handler.requests == []


def test_missing_handler_rejects_without_store_write() -> None:
    store = InMemoryResidentQueueChainResultsStore()

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=store,
        handlers={},
        now_iso=NOW,
    )

    assert result.accepted is False
    assert FAIL_HANDLER_MISSING in result.rejection_reasons
    assert result.dispatched_stage == "authority_request"
    assert store.load() == {}


def test_dispatches_current_stage_handler_and_records_result() -> None:
    store = InMemoryResidentQueueChainResultsStore()
    handler = _RecordingHandler(_authority_request_accept())

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=store,
        handlers={"authority_request": handler},
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.decision == RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT
    assert result.dispatched_stage == "authority_request"
    assert result.stage_handler_invoked is True
    assert result.next_action == NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE
    assert handler.requests[0].stage_key == "authority_request"
    assert handler.requests[0].next_action == "RUN_QUEUE_AUTHORITY_REQUEST_DRYRUN"
    state = store.load()
    assert state["stage_results"]["authority_request"]["status"] == "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT"
    assert state["no_bridge_invoked"] is True


def test_dispatch_uses_existing_chain_state_to_pick_next_stage() -> None:
    store = InMemoryResidentQueueChainResultsStore()
    seed = record_resident_queue_stage_result(
        work_state_snapshot=_snapshot(),
        store=store,
        stage_key="authority_request",
        stage_result=_authority_request_accept(),
        now_iso=NOW,
    )
    assert seed.accepted is True
    handler = _RecordingHandler(_authority_runtime_accept())

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=store,
        handlers={"authority_runtime": handler},
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.dispatched_stage == "authority_runtime"
    assert handler.requests[0].stage_key == "authority_runtime"
    assert store.load()["stage_results"]["authority_runtime"]["decision"] == "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT"


def test_handler_exception_fails_closed_without_store_write() -> None:
    def bad_handler(_: ResidentQueueStageDispatchRequest) -> dict[str, object]:
        raise RuntimeError("boom")

    store = InMemoryResidentQueueChainResultsStore()
    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=store,
        handlers={"authority_request": bad_handler},
        now_iso=NOW,
    )

    assert result.accepted is False
    assert FAIL_HANDLER_EXCEPTION in result.rejection_reasons
    assert result.stage_handler_invoked is True
    assert store.load() == {}


def test_handler_non_mapping_result_fails_closed_without_store_write() -> None:
    def bad_handler(_: ResidentQueueStageDispatchRequest):  # type: ignore[no-untyped-def]
        return "bad"

    store = InMemoryResidentQueueChainResultsStore()
    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=store,
        handlers={"authority_request": bad_handler},
        now_iso=NOW,
    )

    assert result.accepted is False
    assert FAIL_HANDLER_RESULT_INVALID in result.rejection_reasons
    assert store.load() == {}


def test_rejected_handler_result_is_not_persisted() -> None:
    store = InMemoryResidentQueueChainResultsStore()
    handler = _RecordingHandler(
        {
            "status": "QUEUE_AUTHORITY_REQUEST_DRYRUN_REJECT",
            "rejection_reasons": ["FAIL_PROFILE_MISSING"],
        }
    )

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=store,
        handlers={"authority_request": handler},
        now_iso=NOW,
    )

    assert result.accepted is False
    assert FAIL_RECORD_REJECTED in result.rejection_reasons
    assert "FAIL_PROFILE_MISSING" in result.rejection_reasons
    assert store.load() == {}


def test_result_is_json_serializable() -> None:
    store = InMemoryResidentQueueChainResultsStore()
    handler = _RecordingHandler(_authority_request_accept())

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=store,
        handlers={"authority_request": handler},
        now_iso=NOW,
    )

    payload = result.to_dict()
    assert payload["record_result"]["accepted"] is True
    assert payload["plan"]["current_stage"] == "authority_request"


def test_module_has_no_concrete_bridge_or_execution_imports() -> None:
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
    banned_import_fragments = {
        "reddog_wre_queue_authority_request_dryrun",
        "reddog_wre_queue_authority_runtime_invoke",
        "reddog_wre_queue_authority_verification_invoke",
        "reddog_wre_queue_authorized",
        "reddog_wre_queue_verified_authority_work_order_invoke",
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
