"""Tests for REDDOG_RESIDENT_QUEUE_PATTERN_MEMORY_ADMISSION_HANDLER_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    CHAIN_RESULTS_SCHEMA_VERSION,
    InMemoryResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    FAIL_RECORD_REJECTED,
    RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT,
    ResidentQueueStageDispatchRequest,
    invoke_reddog_resident_queue_next_stage_dispatch,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_CHAIN_COMPLETE,
    NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_pattern_memory_admission_handler import (
    FAIL_ADMISSION_REQUEST_MISSING,
    FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
    FAIL_DISPATCH_STAGE_MISMATCH,
    FAIL_HELD_OUT_REGRESSION_GATE_STAGE_MISSING,
    FAIL_PATTERN_MEMORY_SINK_MISSING,
    HELD_OUT_REGRESSION_GATE_STAGE_KEY,
    PATTERN_MEMORY_ADMISSION_STAGE_KEY,
    build_reddog_resident_queue_pattern_memory_admission_stage_handler,
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
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_pattern_memory_admission_invoke import (
    QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT,
    QueueAuthorizedPatternMemoryAdmissionInvokeReason,
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
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_held_out_regression_gate_invoke import (
    _queue_ratchet_result,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_pattern_memory_admission_invoke import (
    FakePatternMemorySink,
    _admission_request,
    _queue_gate_result,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_slice_verifier_invoke import (
    _queue_pilot_result,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_verified_draft_pr_publish_invoke import (
    _queue_verifier_result,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_verified_outcome_ratchet_invoke import (
    _queue_publish_result,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    WORKER_DISPATCH_DRYRUN_STAGE_RESULT,
    WORKER_DISPATCH_RUNTIME_STAGE_RESULT,
    with_queue_wsp15_allocation,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_pattern_memory_admission_handler.py"
)
NOW_ISO = "2026-07-14T00:00:00+00:00"
EXPIRES = "2026-07-14T01:00:00+00:00"


def _snapshot() -> dict[str, object]:
    queue_item = with_queue_wsp15_allocation(
        {
            "queue_item_id": "queue-1",
            "slice_id": "REDDOG_TEST_SLICE_PHASE1",
            "claim_id": "claim-1",
            "worker_id": "reddog-0102",
            "status": "QUEUED",
            "evidence_refs": ["claim:claim-1", "freshness:fresh-1"],
            "no_execution_performed": True,
        },
        prompt_text="RedDog resident queue pattern memory admission worktree authority",
    )
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
        "wre_queue_items": [queue_item],
    }


def _seeded_store(**stage_overrides: object) -> InMemoryResidentQueueChainResultsStore:
    stage_results: dict[str, object] = {
        "authority_request": {"status": QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT},
        "authority_runtime": {"decision": QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT},
        "authority_verification": {"decision": QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT},
        "worker_dispatch_dryrun": WORKER_DISPATCH_DRYRUN_STAGE_RESULT,
        "worker_dispatch_runtime": WORKER_DISPATCH_RUNTIME_STAGE_RESULT,
        "work_order_invocation": {"decision": QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT},
        "executor_plan": {"decision": QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT},
        "execution_valve": {"decision": QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT},
        "worktree_create": {"decision": QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT},
        "bounded_worker_pilot": _queue_pilot_result(),
        "slice_verifier": _queue_verifier_result(),
        "verified_draft_pr_publish": _queue_publish_result(),
        "verified_outcome_ratchet": _queue_ratchet_result(),
        HELD_OUT_REGRESSION_GATE_STAGE_KEY: _queue_gate_result(),
    }
    stage_results.update(stage_overrides)
    return InMemoryResidentQueueChainResultsStore(
        {
            "schema_version": CHAIN_RESULTS_SCHEMA_VERSION,
            "queue_item_id": "queue-1",
            "selected_slice": "REDDOG_TEST_SLICE_PHASE1",
            "stage_results": stage_results,
            "receipts": [],
        }
    )


def _handler(
    *,
    chain_store: InMemoryResidentQueueChainResultsStore,
    admission_request: dict[str, object] | None = None,
    sink: FakePatternMemorySink | None = None,
):
    return build_reddog_resident_queue_pattern_memory_admission_stage_handler(
        chain_results_store=chain_store,
        admission_request=admission_request if admission_request is not None else _admission_request(),
        sink=sink if sink is not None else FakePatternMemorySink(),
    )


def test_dispatcher_records_pattern_memory_admission_and_completes_chain() -> None:
    chain_store = _seeded_store()
    sink = FakePatternMemorySink()

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={
            PATTERN_MEMORY_ADMISSION_STAGE_KEY: _handler(
                chain_store=chain_store,
                sink=sink,
            )
        },
        now_iso=NOW_ISO,
    )

    assert result.accepted is True
    assert result.decision == RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT
    assert result.dispatched_stage == PATTERN_MEMORY_ADMISSION_STAGE_KEY
    assert result.next_action == NEXT_QUEUE_CHAIN_COMPLETE
    stage = chain_store.load()["stage_results"][PATTERN_MEMORY_ADMISSION_STAGE_KEY]
    assert stage["decision"] == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT
    assert stage["pattern_memory_write_performed"] is True
    assert stage["receipt"]["pattern_memory_record_id"] == "pattern-memory-record-1"
    assert stage["no_command_execution_performed"] is True
    assert stage["no_pr_publish_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True
    assert len(sink.records) == 1


def test_missing_held_out_stage_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store(**{HELD_OUT_REGRESSION_GATE_STAGE_KEY: {}}))
    request = ResidentQueueStageDispatchRequest(
        stage_key=PATTERN_MEMORY_ADMISSION_STAGE_KEY,
        next_action=NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
    assert FAIL_HELD_OUT_REGRESSION_GATE_STAGE_MISSING in result["rejection_reasons"]


def test_missing_admission_request_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store(), admission_request={})
    request = ResidentQueueStageDispatchRequest(
        stage_key=PATTERN_MEMORY_ADMISSION_STAGE_KEY,
        next_action=NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
    assert FAIL_ADMISSION_REQUEST_MISSING in result["rejection_reasons"]


def test_missing_sink_rejects_direct_handler_call() -> None:
    handler = build_reddog_resident_queue_pattern_memory_admission_stage_handler(
        chain_results_store=_seeded_store(),
        admission_request=_admission_request(),
        sink=None,
    )
    request = ResidentQueueStageDispatchRequest(
        stage_key=PATTERN_MEMORY_ADMISSION_STAGE_KEY,
        next_action=NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
    assert FAIL_PATTERN_MEMORY_SINK_MISSING in result["rejection_reasons"]


def test_wrong_stage_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store())
    request = ResidentQueueStageDispatchRequest(
        stage_key=HELD_OUT_REGRESSION_GATE_STAGE_KEY,
        next_action=NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
    assert FAIL_DISPATCH_STAGE_MISMATCH in result["rejection_reasons"]


def test_wrong_next_action_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store())
    request = ResidentQueueStageDispatchRequest(
        stage_key=PATTERN_MEMORY_ADMISSION_STAGE_KEY,
        next_action="RUN_QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE",
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
    assert FAIL_DISPATCH_NEXT_ACTION_MISMATCH in result["rejection_reasons"]


def test_admission_rejection_is_not_recorded_by_dispatcher() -> None:
    request = _admission_request()
    request["admission_metadata"]["note"] = "api_key = leak"
    chain_store = _seeded_store()

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={
            PATTERN_MEMORY_ADMISSION_STAGE_KEY: _handler(
                chain_store=chain_store,
                admission_request=request,
                sink=FakePatternMemorySink(),
            )
        },
        now_iso=NOW_ISO,
    )

    assert result.accepted is False
    assert FAIL_RECORD_REJECTED in result.rejection_reasons
    assert QueueAuthorizedPatternMemoryAdmissionInvokeReason.SECRET_IN_RECORD in result.rejection_reasons
    assert PATTERN_MEMORY_ADMISSION_STAGE_KEY not in chain_store.load()["stage_results"]


def test_module_has_no_shell_git_openclaw_hermes_pr_reward_or_holoindex_authority() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_import_roots = {
        "subprocess",
        "os",
        "shutil",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "holo_index",
        "git",
        "pattern_memory",
    }
    banned_calls = {"eval", "exec", "compile", "__import__", "open"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls

    forbidden_tokens = (
        "subprocess",
        "git ",
        "\ngh ",
        "openclaw_supervisor",
        "hermes_job_executor",
        "create_draft_pr",
        "push_branch",
        "mark_ready",
        "merge_pr",
        "settle_reward",
        "holo_index.py --index",
        "PatternMemory(",
    )
    for token in forbidden_tokens:
        assert token not in source
