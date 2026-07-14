"""Tests for REDDOG_RESIDENT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_HANDLER_PHASE1."""

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
    NEXT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_INVOKE,
    NEXT_QUEUE_VERIFIED_OUTCOME_RATCHET_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_verified_draft_pr_publish_handler import (
    FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
    FAIL_DISPATCH_STAGE_MISMATCH,
    FAIL_DRAFT_PR_RUNNER_MISSING,
    FAIL_PUBLISH_REQUEST_MISSING,
    FAIL_SLICE_VERIFIER_STAGE_MISSING,
    SLICE_VERIFIER_STAGE_KEY,
    VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY,
    build_reddog_resident_queue_verified_draft_pr_publish_stage_handler,
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
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_slice_verifier_invoke import (
    QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_draft_pr_publish_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT,
    QueueAuthorizedVerifiedDraftPrPublishInvokeReason,
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
    FakeDraftPrRunner,
    _publish_request,
    _queue_verifier_result,
)
from modules.infrastructure.wre_core.src.reddog_verified_draft_pr_publish import (
    VERIFIED_DRAFT_PR_PUBLISH_ACCEPT,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_verified_draft_pr_publish_handler.py"
)
NOW_ISO = "2026-07-14T00:00:00+00:00"
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


def _seeded_store(**stage_overrides: object) -> InMemoryResidentQueueChainResultsStore:
    stage_results: dict[str, object] = {
        "authority_request": {"status": QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT},
        "authority_runtime": {"decision": QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT},
        "authority_verification": {"decision": QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT},
        "work_order_invocation": {"decision": QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT},
        "executor_plan": {"decision": QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT},
        "execution_valve": {"decision": QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT},
        "worktree_create": {"decision": QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT},
        "bounded_worker_pilot": _queue_pilot_result(),
        SLICE_VERIFIER_STAGE_KEY: _queue_verifier_result(),
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
    publish_request: dict[str, object] | None = None,
    runner: FakeDraftPrRunner | None = None,
):
    return build_reddog_resident_queue_verified_draft_pr_publish_stage_handler(
        chain_results_store=chain_store,
        publish_request=publish_request if publish_request is not None else _publish_request(),
        runner=runner if runner is not None else FakeDraftPrRunner(),
    )


def test_dispatcher_records_draft_pr_publish_and_advances_to_outcome_ratchet() -> None:
    chain_store = _seeded_store()
    runner = FakeDraftPrRunner()

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={
            VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY: _handler(
                chain_store=chain_store,
                runner=runner,
            )
        },
        now_iso=NOW_ISO,
    )

    assert result.accepted is True
    assert result.decision == RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT
    assert result.dispatched_stage == VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY
    assert result.next_action == NEXT_QUEUE_VERIFIED_OUTCOME_RATCHET_INVOKE
    stage = chain_store.load()["stage_results"][VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY]
    assert stage["decision"] == QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT
    assert stage["publish_result"]["decision"] == VERIFIED_DRAFT_PR_PUBLISH_ACCEPT
    assert stage["publish_result"]["receipt"]["draft_pr_url"].endswith("/pull/2000")
    assert stage["no_ready_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_pattern_memory_write_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True
    assert [call[0] for call in runner.calls] == ["push_branch", "create_draft_pr"]


def test_missing_slice_verifier_stage_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store(**{SLICE_VERIFIER_STAGE_KEY: {}}))
    request = ResidentQueueStageDispatchRequest(
        stage_key=VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY,
        next_action=NEXT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT
    assert FAIL_SLICE_VERIFIER_STAGE_MISSING in result["rejection_reasons"]


def test_missing_publish_request_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store(), publish_request={})
    request = ResidentQueueStageDispatchRequest(
        stage_key=VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY,
        next_action=NEXT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT
    assert FAIL_PUBLISH_REQUEST_MISSING in result["rejection_reasons"]


def test_missing_runner_rejects_direct_handler_call() -> None:
    handler = build_reddog_resident_queue_verified_draft_pr_publish_stage_handler(
        chain_results_store=_seeded_store(),
        publish_request=_publish_request(),
        runner=None,
    )
    request = ResidentQueueStageDispatchRequest(
        stage_key=VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY,
        next_action=NEXT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT
    assert FAIL_DRAFT_PR_RUNNER_MISSING in result["rejection_reasons"]


def test_wrong_stage_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store())
    request = ResidentQueueStageDispatchRequest(
        stage_key=SLICE_VERIFIER_STAGE_KEY,
        next_action=NEXT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT
    assert FAIL_DISPATCH_STAGE_MISMATCH in result["rejection_reasons"]


def test_wrong_next_action_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store())
    request = ResidentQueueStageDispatchRequest(
        stage_key=VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY,
        next_action="RUN_QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE",
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_REJECT
    assert FAIL_DISPATCH_NEXT_ACTION_MISMATCH in result["rejection_reasons"]


def test_publish_rejection_is_not_recorded_by_dispatcher() -> None:
    request = _publish_request()
    request["pre_publish_branch_head_sha"] = "b" * 40
    chain_store = _seeded_store()

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={
            VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY: _handler(
                chain_store=chain_store,
                publish_request=request,
                runner=FakeDraftPrRunner(),
            )
        },
        now_iso=NOW_ISO,
    )

    assert result.accepted is False
    assert FAIL_RECORD_REJECTED in result.rejection_reasons
    assert QueueAuthorizedVerifiedDraftPrPublishInvokeReason.PUBLISH_NOT_ACCEPTED in result.rejection_reasons
    assert "FAIL_HEAD_MISMATCH" in result.rejection_reasons
    assert VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY not in chain_store.load()["stage_results"]


def test_module_has_no_direct_shell_git_openclaw_hermes_merge_memory_reward_or_holoindex_authority() -> None:
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
        "reddog_wre_queue_authorized_verified_outcome_ratchet_invoke",
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
        "mark_ready",
        "merge_pr",
        "PatternMemory(",
        "store_outcome",
        "settle_reward",
        "holo_index.py --index",
    )
    for token in forbidden_tokens:
        assert token not in source
