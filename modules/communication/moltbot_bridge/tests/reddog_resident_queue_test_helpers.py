"""Shared resident queue test fixtures."""

from __future__ import annotations

from typing import Any

from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)


WORKER_DISPATCH_DRYRUN_STAGE_RESULT = {
    "decision": "SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT",
}

WORKER_DISPATCH_RUNTIME_STAGE_RESULT = {
    "decision": "SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT",
}

ASSURANCE_RESERVATION = {
    "reservation_id": "assurance-reservation-" + "1" * 20,
    "reservation_digest": "sha256:" + "0" * 64,
    "status": "reserved",
    "work_order_id": "wo-resident-queue-1",
    "author_task_id": "reddog-worker-dispatch-" + "1" * 16,
    "author_principal_id": "worker:author",
    "verifier_task_id": "reddog-worker-dispatch-" + "2" * 16,
    "verifier_principal_id": "worker:verifier",
}

ASSURANCE_CAPACITY_ADMISSION_STAGE_RESULT = {
    "decision": "ASSURANCE_CAPACITY_ADMISSION_ACCEPT",
    "reservation": ASSURANCE_RESERVATION,
}


class FakeAssuranceReservationStore:
    def __init__(self) -> None:
        self.reservation = dict(ASSURANCE_RESERVATION)
        self.reservations = {
            str(self.reservation["reservation_id"]): dict(self.reservation)
        }

    def reserve_independent_assurance(self, request):
        self.reservation = {**dict(request), "status": "reserved"}
        self.reservations[str(self.reservation["reservation_id"])] = dict(
            self.reservation
        )
        return {
            "accepted": True,
            "status": "ASSURANCE_CAPACITY_RESERVED",
            "reservation": dict(self.reservation),
        }

    def get_independent_assurance_reservation(self, reservation_id: str):
        value = self.reservations.get(reservation_id)
        return dict(value) if value is not None else None

    def complete_independent_assurance(self, reservation_id: str, **kwargs):
        if (
            reservation_id not in self.reservations
            or not kwargs.get("terminal_receipt_id")
        ):
            return {"accepted": False, "status": "rejected"}
        return {"accepted": True, "status": "completed"}


def queue_wsp15_allocation_receipt(*, prompt_text: str = "RedDog resident queue worktree authority") -> dict[str, Any]:
    return allocate_reddog_wsp15_receipt(
        requested_operation="create_foundup",
        prompt_text=prompt_text,
        changed_paths=("modules/communication/moltbot_bridge/src/reddog_resident_queue_orchestration_plan.py",),
        allowed_read_targets=("modules/communication/moltbot_bridge/src/reddog_resident_queue_orchestration_plan.py",),
    ).to_dict()


def with_queue_wsp15_allocation(queue_item: dict[str, Any], *, prompt_text: str = "RedDog resident queue worktree authority") -> dict[str, Any]:
    allocation = queue_wsp15_allocation_receipt(prompt_text=prompt_text)
    item = dict(queue_item)
    refs = [str(ref) for ref in item.get("evidence_refs") or ()]
    refs.extend(
        [
            f"wsp15_allocation:{allocation['receipt_id']}",
        ]
    )
    item["evidence_refs"] = list(dict.fromkeys(refs))
    item["wsp15_allocation_receipt"] = allocation
    return item
