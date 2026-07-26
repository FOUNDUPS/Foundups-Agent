"""Tests for REDDOG_RESIDENT_QUEUE_VERIFIED_OUTCOME_RATCHET_HANDLER_PHASE1."""

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
    NEXT_QUEUE_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE,
    NEXT_QUEUE_VERIFIED_OUTCOME_RATCHET_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_verified_outcome_ratchet_handler import (
    FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
    FAIL_DISPATCH_STAGE_MISMATCH,
    FAIL_RATCHET_REQUEST_MISSING,
    FAIL_RATCHET_STORE_MISSING,
    FAIL_VERIFIED_DRAFT_PR_PUBLISH_STAGE_MISSING,
    VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY,
    VERIFIED_OUTCOME_RATCHET_STAGE_KEY,
    build_reddog_resident_queue_verified_outcome_ratchet_stage_handler,
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
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_execution_valve_invoke import (
    QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_executor_plan_dryrun import (
    QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_outcome_ratchet_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT,
    QueueAuthorizedVerifiedOutcomeRatchetInvokeReason,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_worktree_create_invoke import (
    QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_verified_authority_work_order_invoke import (
    QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_slice_verifier_invoke import (
    _queue_pilot_result,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_verified_draft_pr_publish_invoke import (
    _queue_verifier_result,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_verified_outcome_ratchet_invoke import (
    _queue_publish_result,
    _ratchet_request,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    ASSURANCE_CAPACITY_ADMISSION_STAGE_RESULT,
    WORKER_DISPATCH_DRYRUN_STAGE_RESULT,
    WORKER_DISPATCH_RUNTIME_STAGE_RESULT,
    with_queue_wsp15_allocation,
)
from modules.infrastructure.wre_core.src import reddog_verified_outcome_ratchet as ratchet


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_verified_outcome_ratchet_handler.py"
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
        prompt_text="RedDog resident queue verified outcome ratchet worktree authority",
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
        "assurance_capacity_admission": ASSURANCE_CAPACITY_ADMISSION_STAGE_RESULT,
        "bounded_worker_pilot": _queue_pilot_result(),
        "slice_verifier": _queue_verifier_result(),
        VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY: _queue_publish_result(),
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
    ratchet_request: dict[str, object] | None = None,
    store: ratchet.InMemoryOutcomeRatchetStore | None = None,
):
    return build_reddog_resident_queue_verified_outcome_ratchet_stage_handler(
        chain_results_store=chain_store,
        ratchet_request=ratchet_request if ratchet_request is not None else _ratchet_request(),
        store=store if store is not None else ratchet.InMemoryOutcomeRatchetStore(),
    )


def test_dispatcher_records_outcome_ratchet_and_advances_to_model_feedback_admission() -> None:
    chain_store = _seeded_store()
    outcome_store = ratchet.InMemoryOutcomeRatchetStore()

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={
            VERIFIED_OUTCOME_RATCHET_STAGE_KEY: _handler(
                chain_store=chain_store,
                store=outcome_store,
            )
        },
        now_iso=NOW_ISO,
    )

    assert result.accepted is True
    assert result.decision == RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT
    assert result.dispatched_stage == VERIFIED_OUTCOME_RATCHET_STAGE_KEY
    assert result.next_action == NEXT_QUEUE_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE
    stage = chain_store.load()["stage_results"][VERIFIED_OUTCOME_RATCHET_STAGE_KEY]
    assert stage["decision"] == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT
    assert stage["ratchet_result"]["decision"] == ratchet.OUTCOME_RATCHET_RECORDED
    assert stage["ratchet_result"]["receipt"]["pattern_memory_write_performed"] is False
    assert stage["no_command_execution_performed"] is True
    assert stage["no_pr_publish_performed"] is True
    assert stage["no_ready_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True
    assert len(outcome_store.records) == 1


def test_missing_publish_stage_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store(**{VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY: {}}))
    request = ResidentQueueStageDispatchRequest(
        stage_key=VERIFIED_OUTCOME_RATCHET_STAGE_KEY,
        next_action=NEXT_QUEUE_VERIFIED_OUTCOME_RATCHET_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT
    assert FAIL_VERIFIED_DRAFT_PR_PUBLISH_STAGE_MISSING in result["rejection_reasons"]


def test_missing_ratchet_request_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store(), ratchet_request={})
    request = ResidentQueueStageDispatchRequest(
        stage_key=VERIFIED_OUTCOME_RATCHET_STAGE_KEY,
        next_action=NEXT_QUEUE_VERIFIED_OUTCOME_RATCHET_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT
    assert FAIL_RATCHET_REQUEST_MISSING in result["rejection_reasons"]


def test_missing_store_rejects_direct_handler_call() -> None:
    handler = build_reddog_resident_queue_verified_outcome_ratchet_stage_handler(
        chain_results_store=_seeded_store(),
        ratchet_request=_ratchet_request(),
        store=None,
    )
    request = ResidentQueueStageDispatchRequest(
        stage_key=VERIFIED_OUTCOME_RATCHET_STAGE_KEY,
        next_action=NEXT_QUEUE_VERIFIED_OUTCOME_RATCHET_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT
    assert FAIL_RATCHET_STORE_MISSING in result["rejection_reasons"]


def test_wrong_stage_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store())
    request = ResidentQueueStageDispatchRequest(
        stage_key=VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY,
        next_action=NEXT_QUEUE_VERIFIED_OUTCOME_RATCHET_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT
    assert FAIL_DISPATCH_STAGE_MISMATCH in result["rejection_reasons"]


def test_wrong_next_action_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store())
    request = ResidentQueueStageDispatchRequest(
        stage_key=VERIFIED_OUTCOME_RATCHET_STAGE_KEY,
        next_action="RUN_QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE",
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT
    assert FAIL_DISPATCH_NEXT_ACTION_MISMATCH in result["rejection_reasons"]


def test_ratchet_rejection_is_not_recorded_by_dispatcher() -> None:
    request = _ratchet_request()
    request["holoindex_evidence"]["index_gap_detected"] = True
    chain_store = _seeded_store()
    outcome_store = ratchet.InMemoryOutcomeRatchetStore()

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={
            VERIFIED_OUTCOME_RATCHET_STAGE_KEY: _handler(
                chain_store=chain_store,
                ratchet_request=request,
                store=outcome_store,
            )
        },
        now_iso=NOW_ISO,
    )

    assert result.accepted is False
    assert FAIL_RECORD_REJECTED in result.rejection_reasons
    assert QueueAuthorizedVerifiedOutcomeRatchetInvokeReason.RATCHET_NOT_ACCEPTED in result.rejection_reasons
    assert ratchet.FAIL_HOLOINDEX_EVIDENCE in result.rejection_reasons
    assert VERIFIED_OUTCOME_RATCHET_STAGE_KEY not in chain_store.load()["stage_results"]


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
    }
    banned_import_fragments = {
        "reddog_wre_queue_authorized_held_out_regression_gate_invoke",
        "reddog_wre_queue_authorized_pattern_memory_admission_invoke",
    }
    banned_calls = {"eval", "exec", "compile", "__import__", "open"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
                assert all(fragment not in alias.name for fragment in banned_import_fragments)
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
            assert all(fragment not in node.module for fragment in banned_import_fragments)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls

    forbidden_tokens = (
        "subprocess",
        "git ",
        "\ngh ",
        "openclaw_supervisor",
        "hermes_job_executor",
        "publish_verified_draft_pr(",
        "create_draft_pr",
        "push_branch",
        "settle_reward",
        "holo_index.py --index",
    )
    for token in forbidden_tokens:
        assert token not in source
