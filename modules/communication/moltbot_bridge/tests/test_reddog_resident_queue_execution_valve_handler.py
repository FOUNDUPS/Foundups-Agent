"""Tests for REDDOG_RESIDENT_QUEUE_EXECUTION_VALVE_HANDLER_PHASE1."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    CHAIN_RESULTS_SCHEMA_VERSION,
    InMemoryResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_execution_valve_handler import (
    EXECUTION_VALVE_STAGE_KEY,
    EXECUTOR_PLAN_STAGE_KEY,
    FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
    FAIL_DISPATCH_STAGE_MISMATCH,
    FAIL_EXECUTOR_PLAN_STAGE_MISSING,
    FAIL_WORK_ORDER_INVOCATION_STAGE_MISSING,
    FAIL_WORK_ORDER_MISSING,
    WORK_ORDER_INVOCATION_STAGE_KEY,
    build_reddog_resident_queue_execution_valve_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    FAIL_RECORD_REJECTED,
    RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT,
    ResidentQueueStageDispatchRequest,
    invoke_reddog_resident_queue_next_stage_dispatch,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_EXECUTION_VALVE_INVOKE,
    NEXT_QUEUE_WORKTREE_CREATE_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_CLOSED,
    VALVE_OPEN_WORKTREE_CREATE,
    ExecutionValveEnvironment,
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
    QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT,
    QueueAuthorizedExecutionValveInvokeReason,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_executor_plan_dryrun import (
    QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_verified_authority_work_order_invoke import (
    QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
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
    / "reddog_resident_queue_execution_valve_handler.py"
)
NOW_ISO = "2026-07-14T00:00:00+00:00"
NOW = datetime(2026, 7, 14, 13, 0, 0, tzinfo=timezone.utc)
EXPIRES = "2026-07-14T01:00:00+00:00"
WORK_ORDER_ID = "wre-queue-resident-execution-valve-001"
REPO = "FOUNDUPS/Foundups-Agent"
FID = "paccess_001"
INVOCATION_DIGEST = "sha256:" + ("e" * 64)
POLICY_DIGEST = "sha256:" + ("f" * 64)


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


def _future_expiry(minutes: int = 30) -> str:
    return (NOW + timedelta(minutes=minutes)).replace(microsecond=0).isoformat()


def _fresh_captured() -> str:
    return (NOW - timedelta(seconds=30)).replace(microsecond=0).isoformat()


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
        prompt_text="RedDog resident queue execution valve worktree authority",
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


def _work_order(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
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
        "requested_operation": "feature_slice",
        "authority_tier": "source",
        "allowed_paths": [f"modules/foundups/{FID}/**"],
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
            "holoindex_query": "RedDog resident queue execution valve handler",
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


def _invocation_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
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


def _work_order_invocation_result(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "decision": QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
        "rejection_reasons": [],
        "invocation_result": _invocation_payload(),
        "explicit_queue_work_order_invocation_requested": True,
    }
    payload.update(overrides)
    return payload


def _executor_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "decision": "EXECUTOR_PLAN_ACCEPT",
        "work_order_id": WORK_ORDER_ID,
        "plan": {
            "plan_id": "plan-001",
            "work_order_id": WORK_ORDER_ID,
            "proposed_branch_name": "feat/paccess-001-valve",
            "proposed_worktree_path": "/tmp/.reddog/worktrees/repo/work/nonce/",
            "lock_key": WORK_ORDER_ID,
            "allowed_paths": [f"modules/foundups/{FID}/**"],
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


def _executor_plan_result(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "decision": QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
        "rejection_reasons": [],
        "executor_plan_result": _executor_payload(),
        "explicit_queue_authorized_executor_plan_requested": True,
    }
    payload.update(overrides)
    return payload


def _seeded_store(**stage_overrides: object) -> InMemoryResidentQueueChainResultsStore:
    stage_results: dict[str, object] = {
        "authority_request": {"status": QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT},
        "authority_runtime": {"decision": QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT},
        "authority_verification": {"decision": QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT},
        "worker_dispatch_dryrun": WORKER_DISPATCH_DRYRUN_STAGE_RESULT,
        WORK_ORDER_INVOCATION_STAGE_KEY: _work_order_invocation_result(),
        EXECUTOR_PLAN_STAGE_KEY: _executor_plan_result(),
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


def _open_env() -> ExecutionValveEnvironment:
    return ExecutionValveEnvironment(
        valve_worktree_create_enabled=True,
        sovereign_worktree_token="012-sovereign-worktree-token",
    )


def _handler(
    *,
    chain_store: InMemoryResidentQueueChainResultsStore,
    resolver: _Resolver | None = None,
    valve_environment: ExecutionValveEnvironment | None = None,
):
    return build_reddog_resident_queue_execution_valve_stage_handler(
        chain_results_store=chain_store,
        work_order_resolver=resolver or _Resolver(_work_order()),
        valve_environment=valve_environment or _open_env(),
        now=NOW,
    )


def test_dispatcher_records_execution_valve_and_advances_to_worktree_create() -> None:
    chain_store = _seeded_store()
    resolver = _Resolver(_work_order())

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={EXECUTION_VALVE_STAGE_KEY: _handler(chain_store=chain_store, resolver=resolver)},
        now_iso=NOW_ISO,
    )

    assert result.accepted is True
    assert result.decision == RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT
    assert result.dispatched_stage == EXECUTION_VALVE_STAGE_KEY
    assert result.next_action == NEXT_QUEUE_WORKTREE_CREATE_INVOKE
    assert resolver.calls == [
        {
            "work_order_id": WORK_ORDER_ID,
            "queue_item_id": "queue-1",
            "selected_slice": "REDDOG_TEST_SLICE_PHASE1",
        }
    ]
    stage = chain_store.load()["stage_results"][EXECUTION_VALVE_STAGE_KEY]
    assert stage["decision"] == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT
    assert stage["valve_decision"]["valve_state"] == VALVE_OPEN_WORKTREE_CREATE
    assert stage["valve_decision"]["no_execution_performed"] is True
    assert stage["no_worktree_created"] is True
    assert stage["no_shell_command_executed"] is True
    assert stage["no_repo_mutation_performed"] is True


def test_missing_work_order_invocation_stage_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store(**{WORK_ORDER_INVOCATION_STAGE_KEY: {}}))
    request = ResidentQueueStageDispatchRequest(
        stage_key=EXECUTION_VALVE_STAGE_KEY,
        next_action=NEXT_QUEUE_EXECUTION_VALVE_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
    assert FAIL_WORK_ORDER_INVOCATION_STAGE_MISSING in result["rejection_reasons"]


def test_missing_executor_plan_stage_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store(**{EXECUTOR_PLAN_STAGE_KEY: {}}))
    request = ResidentQueueStageDispatchRequest(
        stage_key=EXECUTION_VALVE_STAGE_KEY,
        next_action=NEXT_QUEUE_EXECUTION_VALVE_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
    assert FAIL_EXECUTOR_PLAN_STAGE_MISSING in result["rejection_reasons"]


def test_missing_work_order_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store(), resolver=_Resolver(None))
    request = ResidentQueueStageDispatchRequest(
        stage_key=EXECUTION_VALVE_STAGE_KEY,
        next_action=NEXT_QUEUE_EXECUTION_VALVE_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
    assert FAIL_WORK_ORDER_MISSING in result["rejection_reasons"]
    assert f"work_order_id:{WORK_ORDER_ID}" in result["rejection_reasons"]


def test_wrong_stage_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store())
    request = ResidentQueueStageDispatchRequest(
        stage_key=EXECUTOR_PLAN_STAGE_KEY,
        next_action=NEXT_QUEUE_EXECUTION_VALVE_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
    assert FAIL_DISPATCH_STAGE_MISMATCH in result["rejection_reasons"]


def test_wrong_next_action_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store())
    request = ResidentQueueStageDispatchRequest(
        stage_key=EXECUTION_VALVE_STAGE_KEY,
        next_action="RUN_QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN",
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
    assert FAIL_DISPATCH_NEXT_ACTION_MISMATCH in result["rejection_reasons"]


def test_closed_valve_rejection_is_not_recorded_by_dispatcher() -> None:
    chain_store = _seeded_store()

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={
            EXECUTION_VALVE_STAGE_KEY: _handler(
                chain_store=chain_store,
                valve_environment=ExecutionValveEnvironment(),
            )
        },
        now_iso=NOW_ISO,
    )

    assert result.accepted is False
    assert FAIL_RECORD_REJECTED in result.rejection_reasons
    assert QueueAuthorizedExecutionValveInvokeReason.VALVE_STATE_NOT_EXPECTED in result.rejection_reasons
    assert "explicit_valve_flag_missing" in result.rejection_reasons
    assert EXECUTION_VALVE_STAGE_KEY not in chain_store.load()["stage_results"]


def test_receipt_chain_mismatch_rejection_is_not_recorded_by_dispatcher() -> None:
    bad_executor = _executor_payload()
    bad_executor["plan"] = dict(bad_executor["plan"])
    bad_executor["plan"]["invocation_receipt_digest"] = "sha256:" + ("9" * 64)
    chain_store = _seeded_store(**{EXECUTOR_PLAN_STAGE_KEY: _executor_plan_result(executor_plan_result=bad_executor)})

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={EXECUTION_VALVE_STAGE_KEY: _handler(chain_store=chain_store)},
        now_iso=NOW_ISO,
    )

    assert result.accepted is False
    assert FAIL_RECORD_REJECTED in result.rejection_reasons
    assert "executor_plan_invocation_digest_mismatch" in result.rejection_reasons
    assert EXECUTION_VALVE_STAGE_KEY not in chain_store.load()["stage_results"]


def test_module_has_no_shell_network_worktree_openclaw_hermes_holoindex_or_later_stage_imports() -> None:
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
        "hmac",
        "secrets",
    }
    banned_import_fragments = {
        "reddog_wre_queue_authorized_worktree_create_invoke",
        "reddog_wre_queue_authorized_bounded_worker_pilot_invoke",
        "reddog_wre_queue_authorized_slice_verifier_invoke",
        "reddog_wre_queue_authorized_verified_draft_pr_publish_invoke",
        "reddog_wre_queue_authorized_verified_outcome_ratchet_invoke",
        "reddog_wre_queue_authorized_held_out_regression_gate_invoke",
        "reddog_wre_queue_authorized_pattern_memory_admission_invoke",
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
