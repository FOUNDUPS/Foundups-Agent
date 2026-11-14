"""Tests for independent assurance admission before bounded code edits."""

from __future__ import annotations

from datetime import datetime, timezone

from modules.communication.moltbot_bridge.src.reddog_resident_queue_assurance_capacity_admission_handler import (
    ASSURANCE_CAPACITY_ADMISSION_ACCEPT,
    ASSURANCE_CAPACITY_ADMISSION_STAGE_KEY,
    FAIL_ASSURANCE_STORE_MISSING,
    FAIL_WORKER_DISPATCH_RUNTIME_STAGE_REJECTED,
    FAIL_WORKTREE_CREATE_STAGE_REJECTED,
    build_reddog_resident_queue_assurance_capacity_admission_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    InMemoryResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_ASSURANCE_CAPACITY_ADMISSION,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)


NOW = datetime(2026, 7, 25, 0, 0, tzinfo=timezone.utc)
WORK_ORDER_ID = "work-order-assurance-1"


def _allocation() -> dict[str, object]:
    return allocate_reddog_wsp15_receipt(
        requested_operation="implement",
        prompt_text="critical autonomous coding security runtime",
        changed_paths=(
            "modules/communication/moltbot_bridge/src/example.py",
        ),
        allowed_read_targets=(
            "modules/communication/moltbot_bridge/src/example.py",
        ),
    ).to_dict()


def _snapshot() -> dict[str, object]:
    allocation = _allocation()
    return {
        "schema_version": "reddog_authoritative_work_state.v1",
        "snapshot_id": "snapshot-assurance-1",
        "wre_queue_items": [
            {
                "queue_item_id": "queue-1",
                "slice_id": "ASSURANCE_TEST_PHASE1",
                "wsp15_allocation_receipt": allocation,
            }
        ],
    }


def _task(
    task_id: str, *, role: str, runtime: str, capability: str
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "context": {
            "worker_role": role,
            "worker_runtime": runtime,
            "worker_principal_id": f"agentdb-task:{task_id}",
            "capability": capability,
            "signed_authority_worker_dispatch_receipt": {
                "work_order_id": WORK_ORDER_ID,
            },
        },
    }


def _chain_store() -> InMemoryResidentQueueChainResultsStore:
    return InMemoryResidentQueueChainResultsStore(
        {
            "schema_version": "reddog_resident_queue_chain_results.v1",
            "stage_results": {
                "worker_dispatch_runtime": {
                    "decision": "SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT",
                    "receipt": {"work_order_id": WORK_ORDER_ID},
                    "tasks": [
                        _task(
                            "reddog-worker-dispatch-" + "1" * 16,
                            role="coding_worker_1",
                            runtime="0102",
                            capability="bounded_code_change",
                        ),
                        _task(
                            "reddog-worker-dispatch-" + "2" * 16,
                            role="independent_slice_verifier",
                            runtime="openclaw",
                            capability="independent_slice_verification",
                        ),
                    ],
                },
                "worktree_create": {
                    "decision": "QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT"
                },
            },
        }
    )


class _Store:
    def __init__(self, *, accept: bool = True) -> None:
        self.accept = accept
        self.requests: list[dict[str, object]] = []

    def reserve_independent_assurance(self, request):
        self.requests.append(dict(request))
        if not self.accept:
            return {
                "accepted": False,
                "status": "BLOCKED_ASSURANCE_CAPACITY",
                "rejection_reasons": ["no_independent_verifier_available"],
                "retry_at": request["expires_at"],
            }
        return {
            "accepted": True,
            "status": "ASSURANCE_CAPACITY_RESERVED",
            "reservation": {**dict(request), "status": "reserved"},
        }


def _request() -> ResidentQueueStageDispatchRequest:
    return ResidentQueueStageDispatchRequest(
        stage_key=ASSURANCE_CAPACITY_ADMISSION_STAGE_KEY,
        next_action=NEXT_QUEUE_ASSURANCE_CAPACITY_ADMISSION,
        queue_item_id="queue-1",
        selected_slice="ASSURANCE_TEST_PHASE1",
        plan_id="plan-1",
        accepted_stages=("queue_consumer", "worktree_create"),
    )


def test_reserves_distinct_verifier_before_bounded_worker() -> None:
    store = _Store()
    result = build_reddog_resident_queue_assurance_capacity_admission_stage_handler(
        work_state_snapshot=_snapshot(),
        chain_results_store=_chain_store(),
        reservation_store=store,
        now=NOW,
    )(_request())

    assert result["decision"] == ASSURANCE_CAPACITY_ADMISSION_ACCEPT
    assert result["queue_chain_requeue_required"] is False
    assert result["queue_chain_yield_required"] is True
    assert result["reservation"]["author_task_id"] != result["reservation"][
        "verifier_task_id"
    ]
    assert result["reservation"]["author_principal_id"] != result[
        "reservation"
    ]["verifier_principal_id"]
    assert result["reservation"]["operational_snapshot_id"] == (
        "snapshot-assurance-1"
    )
    assert result["reservation"]["wsp15_allocation_receipt_id"] == (
        _allocation()["receipt_id"]
    )
    assert result["no_bounded_worker_pilot_performed"] is True


def test_capacity_exhaustion_defers_without_accepting_stage() -> None:
    store = _Store(accept=False)
    result = build_reddog_resident_queue_assurance_capacity_admission_stage_handler(
        work_state_snapshot=_snapshot(),
        chain_results_store=_chain_store(),
        reservation_store=store,
        now=NOW,
    )(_request())

    assert result["status"] == "BLOCKED_ASSURANCE_CAPACITY"
    assert result["queue_chain_requeue_required"] is True
    assert result["retry_at"]
    assert result["reservation_digest"] == ""
    assert result["no_bounded_worker_pilot_performed"] is True


def test_missing_reservation_store_rejects_without_exception() -> None:
    result = build_reddog_resident_queue_assurance_capacity_admission_stage_handler(
        work_state_snapshot=_snapshot(),
        chain_results_store=_chain_store(),
        reservation_store=None,
        now=NOW,
    )(_request())

    assert result["accepted"] is False
    assert result["rejection_reasons"] == [FAIL_ASSURANCE_STORE_MISSING]
    assert result["no_bounded_worker_pilot_performed"] is True


def test_rejected_worktree_stage_cannot_reserve_assurance() -> None:
    chain_store = _chain_store()
    state = chain_store.load()
    state["stage_results"]["worktree_create"]["decision"] = (
        "QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT"
    )
    chain_store = InMemoryResidentQueueChainResultsStore(state)
    store = _Store()

    result = build_reddog_resident_queue_assurance_capacity_admission_stage_handler(
        work_state_snapshot=_snapshot(),
        chain_results_store=chain_store,
        reservation_store=store,
        now=NOW,
    )(_request())

    assert result["rejection_reasons"] == [FAIL_WORKTREE_CREATE_STAGE_REJECTED]
    assert store.requests == []


def test_rejected_worker_dispatch_stage_cannot_reserve_assurance() -> None:
    chain_store = _chain_store()
    state = chain_store.load()
    state["stage_results"]["worker_dispatch_runtime"]["decision"] = (
        "SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_REJECT"
    )
    chain_store = InMemoryResidentQueueChainResultsStore(state)
    store = _Store()

    result = build_reddog_resident_queue_assurance_capacity_admission_stage_handler(
        work_state_snapshot=_snapshot(),
        chain_results_store=chain_store,
        reservation_store=store,
        now=NOW,
    )(_request())

    assert result["rejection_reasons"] == [
        FAIL_WORKER_DISPATCH_RUNTIME_STAGE_REJECTED
    ]
    assert store.requests == []
