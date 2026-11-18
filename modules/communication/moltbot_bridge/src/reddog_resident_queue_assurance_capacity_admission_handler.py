"""Resident queue assurance-capacity admission stage.

This stage runs after worktree creation and before the bounded coding pilot. It
reserves a distinct verifier task in AgentDB. Capacity exhaustion is a durable
defer condition, not a failed or accepted chain stage.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_openclaw_assurance_capacity import (
    ASSURANCE_CAPACITY_BLOCKED,
    ASSURANCE_CAPACITY_RESERVED,
    IndependentAssuranceReservationStore,
    build_assurance_reservation_request,
    canonical_digest,
    find_assurance_tasks,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_ASSURANCE_CAPACITY_ADMISSION,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_worktree_create_invoke import (
    QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT,
)


ASSURANCE_CAPACITY_ADMISSION_STAGE_KEY = "assurance_capacity_admission"
WORKER_DISPATCH_RUNTIME_STAGE_KEY = "worker_dispatch_runtime"
WORKTREE_CREATE_STAGE_KEY = "worktree_create"
ASSURANCE_CAPACITY_ADMISSION_ACCEPT = "ASSURANCE_CAPACITY_ADMISSION_ACCEPT"
ASSURANCE_CAPACITY_ADMISSION_REJECT = "ASSURANCE_CAPACITY_ADMISSION_REJECT"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_WORKTREE_CREATE_STAGE_MISSING = "FAIL_WORKTREE_CREATE_STAGE_MISSING"
FAIL_WORKTREE_CREATE_STAGE_REJECTED = "FAIL_WORKTREE_CREATE_STAGE_REJECTED"
FAIL_WORKER_DISPATCH_RUNTIME_STAGE_MISSING = (
    "FAIL_WORKER_DISPATCH_RUNTIME_STAGE_MISSING"
)
FAIL_WORKER_DISPATCH_RUNTIME_STAGE_REJECTED = (
    "FAIL_WORKER_DISPATCH_RUNTIME_STAGE_REJECTED"
)
FAIL_ASSURANCE_TASKS_INVALID = "FAIL_ASSURANCE_TASKS_INVALID"
FAIL_WORK_ORDER_ID_MISSING = "FAIL_WORK_ORDER_ID_MISSING"
FAIL_WSP15_ALLOCATION_MISSING = "FAIL_WSP15_ALLOCATION_MISSING"
FAIL_ASSURANCE_STORE_MISSING = "FAIL_ASSURANCE_STORE_MISSING"
FAIL_ASSURANCE_RESERVATION_INVALID = "FAIL_ASSURANCE_RESERVATION_INVALID"


@dataclass(frozen=True)
class ResidentQueueAssuranceCapacityAdmissionStageHandler:
    work_state_snapshot: Mapping[str, Any]
    chain_results_store: ResidentQueueChainResultsStore
    reservation_store: IndependentAssuranceReservationStore | None
    now: datetime | None = None

    def __call__(
        self, request: ResidentQueueStageDispatchRequest
    ) -> Mapping[str, Any]:
        if request.stage_key != ASSURANCE_CAPACITY_ADMISSION_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{ASSURANCE_CAPACITY_ADMISSION_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_ASSURANCE_CAPACITY_ADMISSION:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_ASSURANCE_CAPACITY_ADMISSION}",
                f"actual:{request.next_action}",
            )

        stages = _stage_results(_mapping(self.chain_results_store.load()))
        worktree_create = _mapping(stages.get(WORKTREE_CREATE_STAGE_KEY))
        if not worktree_create:
            return _reject(FAIL_WORKTREE_CREATE_STAGE_MISSING)
        if (
            worktree_create.get("decision")
            != QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT
        ):
            return _reject(FAIL_WORKTREE_CREATE_STAGE_REJECTED)
        runtime = _mapping(stages.get(WORKER_DISPATCH_RUNTIME_STAGE_KEY))
        if not runtime:
            return _reject(FAIL_WORKER_DISPATCH_RUNTIME_STAGE_MISSING)
        if (
            runtime.get("decision")
            != SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT
        ):
            return _reject(FAIL_WORKER_DISPATCH_RUNTIME_STAGE_REJECTED)
        author_task, verifier_task = find_assurance_tasks(runtime)
        if not author_task or not verifier_task:
            return _reject(FAIL_ASSURANCE_TASKS_INVALID)
        if self.reservation_store is None:
            return _reject(FAIL_ASSURANCE_STORE_MISSING)

        queue_item = _queue_item(self.work_state_snapshot, request.queue_item_id)
        allocation = _mapping(queue_item.get("wsp15_allocation_receipt"))
        allocation_id = str(allocation.get("receipt_id") or "")
        if not allocation_id:
            return _reject(FAIL_WSP15_ALLOCATION_MISSING)
        work_order_id = str(
            _mapping(_mapping(runtime.get("receipt"))).get("work_order_id")
            or _mapping(_mapping(author_task.get("context")).get(
                "signed_authority_worker_dispatch_receipt"
            )).get("work_order_id")
            or ""
        )
        if not work_order_id:
            return _reject(FAIL_WORK_ORDER_ID_MISSING)

        snapshot_id = str(
            self.work_state_snapshot.get("snapshot_id")
            or self.work_state_snapshot.get("operational_snapshot_id")
            or canonical_digest(self.work_state_snapshot)
        )
        reservation_request = build_assurance_reservation_request(
            work_order_id=work_order_id,
            queue_item_id=str(request.queue_item_id or ""),
            author_task=author_task,
            verifier_task=verifier_task,
            operational_snapshot_id=snapshot_id,
            wsp15_allocation_receipt_id=allocation_id,
            now=self.now or datetime.now(timezone.utc),
        )
        reserved = _mapping(
            self.reservation_store.reserve_independent_assurance(
                reservation_request
            )
        )
        if reserved.get("accepted") is not True:
            retry_at = str(
                reserved.get("retry_at")
                or reservation_request.get("expires_at")
                or ""
            )
            return {
                "accepted": True,
                "decision": ASSURANCE_CAPACITY_BLOCKED,
                "status": ASSURANCE_CAPACITY_BLOCKED,
                "rejection_reasons": list(
                    dict.fromkeys(
                        str(reason)
                        for reason in reserved.get("rejection_reasons", ())
                        if str(reason)
                    )
                ),
                "queue_chain_requeue_required": True,
                "retry_at": retry_at,
                "reservation_id": reservation_request["reservation_id"],
                "reservation_digest": "",
                "no_bounded_worker_pilot_performed": True,
                "no_repo_mutation_performed": True,
            }
        reservation = _mapping(reserved.get("reservation"))
        if (
            str(reservation.get("reservation_id") or "")
            != reservation_request["reservation_id"]
            or str(reservation.get("reservation_digest") or "")
            != reservation_request["reservation_digest"]
            or str(reservation.get("author_task_id") or "")
            != reservation_request["author_task_id"]
            or str(reservation.get("verifier_task_id") or "")
            != reservation_request["verifier_task_id"]
        ):
            return _reject(FAIL_ASSURANCE_RESERVATION_INVALID)

        return {
            "accepted": True,
            "decision": ASSURANCE_CAPACITY_ADMISSION_ACCEPT,
            "status": ASSURANCE_CAPACITY_RESERVED,
            "rejection_reasons": [],
            "queue_chain_requeue_required": False,
            # Yield only after the dispatcher persists this stage result. The
            # bounded code stage must be entered by the reserved author task.
            "queue_chain_yield_required": True,
            "reservation": dict(reservation),
            "reservation_id": reservation["reservation_id"],
            "reservation_digest": reservation["reservation_digest"],
            "no_bounded_worker_pilot_performed": True,
            "no_repo_mutation_performed": True,
        }


def build_reddog_resident_queue_assurance_capacity_admission_stage_handler(
    *,
    work_state_snapshot: Mapping[str, Any],
    chain_results_store: ResidentQueueChainResultsStore,
    reservation_store: IndependentAssuranceReservationStore | None,
    now: datetime | None = None,
) -> ResidentQueueAssuranceCapacityAdmissionStageHandler:
    return ResidentQueueAssuranceCapacityAdmissionStageHandler(
        work_state_snapshot=work_state_snapshot,
        chain_results_store=chain_results_store,
        reservation_store=reservation_store,
        now=now,
    )


def _reject(*reasons: str) -> dict[str, Any]:
    return {
        "accepted": False,
        "decision": ASSURANCE_CAPACITY_ADMISSION_REJECT,
        "status": ASSURANCE_CAPACITY_ADMISSION_REJECT,
        "rejection_reasons": list(
            dict.fromkeys(reason for reason in reasons if reason)
        ),
        "queue_chain_requeue_required": False,
        "no_bounded_worker_pilot_performed": True,
        "no_repo_mutation_performed": True,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _stage_results(state: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    raw = (
        state.get("stage_results")
        if state.get("schema_version")
        == "reddog_resident_queue_chain_results.v1"
        else state
    )
    if not isinstance(raw, Mapping):
        return {}
    return {
        str(key): value
        for key, value in raw.items()
        if isinstance(value, Mapping)
    }


def _queue_item(
    snapshot: Mapping[str, Any], queue_item_id: str | None
) -> Mapping[str, Any]:
    values = snapshot.get("wre_queue_items")
    if not isinstance(values, list):
        return {}
    for value in values:
        item = _mapping(value)
        if str(item.get("queue_item_id") or "") == str(queue_item_id or ""):
            return item
    return {}


__all__ = [
    "ASSURANCE_CAPACITY_ADMISSION_ACCEPT",
    "ASSURANCE_CAPACITY_ADMISSION_REJECT",
    "ASSURANCE_CAPACITY_ADMISSION_STAGE_KEY",
    "FAIL_ASSURANCE_RESERVATION_INVALID",
    "FAIL_ASSURANCE_STORE_MISSING",
    "FAIL_ASSURANCE_TASKS_INVALID",
    "FAIL_WORKER_DISPATCH_RUNTIME_STAGE_REJECTED",
    "FAIL_WORKTREE_CREATE_STAGE_REJECTED",
    "ResidentQueueAssuranceCapacityAdmissionStageHandler",
    "build_reddog_resident_queue_assurance_capacity_admission_stage_handler",
]
