"""Tests for REDDOG_RESIDENT_QUEUE_BOUNDED_WORKER_PILOT_HANDLER_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_queue_bounded_worker_pilot_handler import (
    BOUNDED_WORKER_PILOT_STAGE_KEY,
    FAIL_ARTIFACT_CONTENTS_MISSING,
    FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
    FAIL_DISPATCH_STAGE_MISMATCH,
    FAIL_WORK_ORDER_MISSING,
    FAIL_WORKTREE_CREATE_STAGE_MISSING,
    WORKTREE_CREATE_STAGE_KEY,
    build_reddog_resident_queue_bounded_worker_pilot_stage_handler,
)
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
    NEXT_QUEUE_BOUNDED_WORKER_PILOT_INVOKE,
    NEXT_QUEUE_SLICE_VERIFIER_INVOKE,
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
    QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT,
    QueueAuthorizedBoundedWorkerPilotInvokeReason,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_execution_valve_invoke import (
    QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_executor_plan_dryrun import (
    QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_verified_authority_work_order_invoke import (
    QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_bounded_worker_pilot_invoke import (
    ARTIFACT,
    WORK_ORDER_ID,
    _valid_bundle,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    WORKER_DISPATCH_DRYRUN_STAGE_RESULT,
    with_queue_wsp15_allocation,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_bounded_worker_pilot_handler.py"
)
NOW_ISO = "2026-07-14T00:00:00+00:00"
EXPIRES = "2026-07-14T01:00:00+00:00"


class _Resolver:
    def __init__(self, work_order: dict[str, object] | None) -> None:
        self.work_order = work_order
        self.calls: list[dict[str, object | None]] = []

    def resolve(self, *, work_order_id: str, queue_item_id: str | None, selected_slice: str | None):
        self.calls.append(
            {
                "work_order_id": work_order_id,
                "queue_item_id": queue_item_id,
                "selected_slice": selected_slice,
            }
        )
        return self.work_order or {}


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
        prompt_text="RedDog resident queue bounded worker pilot worktree authority",
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


def _seeded_store(bundle: dict, **stage_overrides: object) -> InMemoryResidentQueueChainResultsStore:
    stage_results: dict[str, object] = {
        "authority_request": {"status": QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT},
        "authority_runtime": {"decision": QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT},
        "authority_verification": {"decision": QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT},
        "worker_dispatch_dryrun": WORKER_DISPATCH_DRYRUN_STAGE_RESULT,
        "work_order_invocation": {"decision": QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT},
        "executor_plan": {"decision": QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT},
        "execution_valve": {"decision": QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT},
        WORKTREE_CREATE_STAGE_KEY: bundle["queue_worktree_create_result"],
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


def _handler(*, chain_store: InMemoryResidentQueueChainResultsStore, bundle: dict, resolver: _Resolver | None = None):
    return build_reddog_resident_queue_bounded_worker_pilot_stage_handler(
        chain_results_store=chain_store,
        work_order_resolver=resolver or _Resolver(bundle["work_order"]),
        generic_writer_dryrun_result=bundle["generic_writer_dryrun_result"],
        governed_shell_dryrun_result=bundle["governed_shell_dryrun_result"],
        artifact_contents=bundle["artifact_contents"],
        repo_root=bundle["repo_root"],
    )


def test_dispatcher_records_bounded_worker_pilot_and_advances_to_slice_verifier(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    chain_store = _seeded_store(bundle)
    resolver = _Resolver(bundle["work_order"])

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={
            BOUNDED_WORKER_PILOT_STAGE_KEY: _handler(
                chain_store=chain_store,
                bundle=bundle,
                resolver=resolver,
            )
        },
        now_iso=NOW_ISO,
    )

    assert result.accepted is True
    assert result.decision == RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT
    assert result.dispatched_stage == BOUNDED_WORKER_PILOT_STAGE_KEY
    assert result.next_action == NEXT_QUEUE_SLICE_VERIFIER_INVOKE
    assert resolver.calls == [
        {
            "work_order_id": WORK_ORDER_ID,
            "queue_item_id": "queue-1",
            "selected_slice": "REDDOG_TEST_SLICE_PHASE1",
        }
    ]
    stage = chain_store.load()["stage_results"][BOUNDED_WORKER_PILOT_STAGE_KEY]
    assert stage["decision"] == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT
    assert stage["bounded_task_execution_performed"] is True
    assert stage["bounded_file_edit_performed"] is True
    assert stage["shell_command_executed"] is False
    assert stage["openclaw_enqueue_performed"] is False
    assert stage["hermes_dispatch_performed"] is False
    assert (bundle["worktree"] / ARTIFACT).exists()
    assert not (bundle["repo_root"] / ARTIFACT).exists()


def test_missing_worktree_create_stage_rejects_direct_handler_call(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    handler = _handler(
        chain_store=_seeded_store(bundle, **{WORKTREE_CREATE_STAGE_KEY: {}}),
        bundle=bundle,
    )
    request = ResidentQueueStageDispatchRequest(
        stage_key=BOUNDED_WORKER_PILOT_STAGE_KEY,
        next_action=NEXT_QUEUE_BOUNDED_WORKER_PILOT_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
    assert FAIL_WORKTREE_CREATE_STAGE_MISSING in result["rejection_reasons"]


def test_missing_work_order_rejects_direct_handler_call(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    handler = _handler(chain_store=_seeded_store(bundle), bundle=bundle, resolver=_Resolver(None))
    request = ResidentQueueStageDispatchRequest(
        stage_key=BOUNDED_WORKER_PILOT_STAGE_KEY,
        next_action=NEXT_QUEUE_BOUNDED_WORKER_PILOT_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
    assert FAIL_WORK_ORDER_MISSING in result["rejection_reasons"]


def test_missing_artifacts_rejects_direct_handler_call(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    handler = build_reddog_resident_queue_bounded_worker_pilot_stage_handler(
        chain_results_store=_seeded_store(bundle),
        work_order_resolver=_Resolver(bundle["work_order"]),
        generic_writer_dryrun_result=bundle["generic_writer_dryrun_result"],
        governed_shell_dryrun_result=bundle["governed_shell_dryrun_result"],
        artifact_contents={},
        repo_root=bundle["repo_root"],
    )
    request = ResidentQueueStageDispatchRequest(
        stage_key=BOUNDED_WORKER_PILOT_STAGE_KEY,
        next_action=NEXT_QUEUE_BOUNDED_WORKER_PILOT_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
    assert FAIL_ARTIFACT_CONTENTS_MISSING in result["rejection_reasons"]


def test_wrong_stage_rejects_direct_handler_call(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    handler = _handler(chain_store=_seeded_store(bundle), bundle=bundle)
    request = ResidentQueueStageDispatchRequest(
        stage_key=WORKTREE_CREATE_STAGE_KEY,
        next_action=NEXT_QUEUE_BOUNDED_WORKER_PILOT_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
    assert FAIL_DISPATCH_STAGE_MISMATCH in result["rejection_reasons"]


def test_wrong_next_action_rejects_direct_handler_call(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    handler = _handler(chain_store=_seeded_store(bundle), bundle=bundle)
    request = ResidentQueueStageDispatchRequest(
        stage_key=BOUNDED_WORKER_PILOT_STAGE_KEY,
        next_action="RUN_QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE",
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_REJECT
    assert FAIL_DISPATCH_NEXT_ACTION_MISMATCH in result["rejection_reasons"]


def test_holoindex_gap_rejection_is_not_recorded_by_dispatcher(tmp_path: Path) -> None:
    bundle = _valid_bundle(tmp_path)
    bundle["work_order"]["holoindex_evidence"] = {
        "index_gap_detected": True,
        "retrieval_quality": "INDEX_GAP",
    }
    chain_store = _seeded_store(bundle)

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={BOUNDED_WORKER_PILOT_STAGE_KEY: _handler(chain_store=chain_store, bundle=bundle)},
        now_iso=NOW_ISO,
    )

    assert result.accepted is False
    assert FAIL_RECORD_REJECTED in result.rejection_reasons
    assert QueueAuthorizedBoundedWorkerPilotInvokeReason.PILOT_NOT_ACCEPTED in result.rejection_reasons
    assert "FAIL_HOLOINDEX_INDEX_GAP" in result.rejection_reasons
    assert BOUNDED_WORKER_PILOT_STAGE_KEY not in chain_store.load()["stage_results"]


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
        "reddog_wre_queue_authorized_slice_verifier_invoke",
        "reddog_wre_queue_authorized_verified_draft_pr_publish_invoke",
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
        "create_reddog_wre_worktree(",
        "RealRedDogWorktreeRunner",
        "subprocess",
        "git ",
        "\ngh ",
        "openclaw_supervisor",
        "hermes_job_executor",
        "create_pull_request",
        "settle_reward",
        "holo_index.py --index",
    )
    for token in forbidden_tokens:
        assert token not in source
