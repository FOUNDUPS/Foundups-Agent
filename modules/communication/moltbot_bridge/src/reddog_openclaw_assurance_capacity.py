"""Independent assurance-capacity request and receipt helpers.

WRE decides whether assurance is mandatory. OpenClaw uses this module to bind
one author task to one distinct verifier task before any bounded code edit.
AgentDB remains the atomic reservation authority.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Protocol


ASSURANCE_CAPACITY_RESERVED = "ASSURANCE_CAPACITY_RESERVED"
ASSURANCE_CAPACITY_BLOCKED = "BLOCKED_ASSURANCE_CAPACITY"
ASSURANCE_CAPACITY_LEASE_SECONDS = 14_400


class IndependentAssuranceReservationStore(Protocol):
    """Durable store that atomically claims an independent verifier task."""

    def reserve_independent_assurance(
        self, request: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...

    def get_independent_assurance_reservation(
        self, reservation_id: str
    ) -> Mapping[str, Any] | None: ...

    def renew_independent_assurance(
        self, request: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...

    def stage_independent_assurance_completion(
        self, request: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...

def canonical_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_assurance_reservation_request(
    *,
    work_order_id: str,
    queue_item_id: str,
    author_task: Mapping[str, Any],
    verifier_task: Mapping[str, Any],
    operational_snapshot_id: str,
    wsp15_allocation_receipt_id: str,
    now: datetime,
    lease_seconds: int = ASSURANCE_CAPACITY_LEASE_SECONDS,
) -> dict[str, Any]:
    """Build the exact request AgentDB must atomically admit or reject."""

    author_context = _mapping(author_task.get("context"))
    verifier_context = _mapping(verifier_task.get("context"))
    reserved_at = _utc(now)
    expires_at = reserved_at + timedelta(seconds=lease_seconds)
    core = {
        "schema_version": "reddog_assurance_capacity_request.v1",
        "work_order_id": str(work_order_id),
        "queue_item_id": str(queue_item_id),
        "author_task_id": str(author_task.get("task_id") or ""),
        "author_principal_id": str(
            author_context.get("worker_principal_id") or ""
        ),
        "verifier_task_id": str(verifier_task.get("task_id") or ""),
        "verifier_principal_id": str(
            verifier_context.get("worker_principal_id") or ""
        ),
        "capability": str(verifier_context.get("capability") or ""),
        "worker_runtime": str(verifier_context.get("worker_runtime") or ""),
        "operational_snapshot_id": str(operational_snapshot_id),
        "wsp15_allocation_receipt_id": str(wsp15_allocation_receipt_id),
        "reserved_at": _iso(reserved_at),
        "expires_at": _iso(expires_at),
    }
    stable_seed = {
        key: value
        for key, value in core.items()
        if key not in {"reserved_at", "expires_at"}
    }
    reservation_id = (
        "assurance-reservation-"
        + canonical_digest(stable_seed).removeprefix("sha256:")[:20]
    )
    lease_id = (
        "assurance-lease-"
        + canonical_digest({**stable_seed, "reserved_at": core["reserved_at"]})
        .removeprefix("sha256:")[:20]
    )
    request = {
        **core,
        "reservation_id": reservation_id,
        "lease_id": lease_id,
    }
    request["reservation_digest"] = canonical_digest(request)
    return request


def build_assurance_renewal_request(
    reservation: Mapping[str, Any],
    *,
    now: datetime,
    lease_seconds: int = ASSURANCE_CAPACITY_LEASE_SECONDS,
) -> dict[str, Any]:
    """Build a bounded renewal request without changing admission bindings."""

    reserved_at = _utc(now)
    expires_at = reserved_at + timedelta(seconds=lease_seconds)
    core = {
        "schema_version": str(
            reservation.get("request_schema_version")
            or reservation.get("schema_version")
            or "reddog_assurance_capacity_request.v1"
        ),
        "work_order_id": str(reservation.get("work_order_id") or ""),
        "queue_item_id": str(reservation.get("queue_item_id") or ""),
        "author_task_id": str(reservation.get("author_task_id") or ""),
        "author_principal_id": str(
            reservation.get("author_principal_id") or ""
        ),
        "verifier_task_id": str(reservation.get("verifier_task_id") or ""),
        "verifier_principal_id": str(
            reservation.get("verifier_principal_id") or ""
        ),
        "capability": str(reservation.get("capability") or ""),
        "worker_runtime": str(reservation.get("worker_runtime") or ""),
        "operational_snapshot_id": str(
            reservation.get("operational_snapshot_id") or ""
        ),
        "wsp15_allocation_receipt_id": str(
            reservation.get("wsp15_allocation_receipt_id") or ""
        ),
        "reserved_at": _iso(reserved_at),
        "expires_at": _iso(expires_at),
        "reservation_id": str(reservation.get("reservation_id") or ""),
    }
    renewal_count = int(reservation.get("renewal_count") or 0) + 1
    core["lease_id"] = (
        "assurance-lease-"
        + canonical_digest(
            {
                "reservation_id": core["reservation_id"],
                "reserved_at": core["reserved_at"],
                "renewal_count": renewal_count,
            }
        ).removeprefix("sha256:")[:20]
    )
    request = {**core, "renewal_count": renewal_count}
    request["reservation_digest"] = canonical_digest(request)
    return request


def find_assurance_tasks(
    worker_dispatch_runtime: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Return the single author and verifier task from a dispatch result."""

    bounded_authors: list[Mapping[str, Any]] = []
    verifiers: list[Mapping[str, Any]] = []
    for raw in _list(worker_dispatch_runtime.get("tasks")):
        task = _mapping(raw)
        context = _mapping(task.get("context"))
        capability = str(context.get("capability") or "")
        if capability == "bounded_code_change":
            bounded_authors.append(task)
        elif capability == "independent_slice_verification":
            verifiers.append(task)
    # The reservation author is the worker that can mutate the bounded
    # worktree, never the queue-stage driver that advances orchestration.
    authors = bounded_authors
    if len(authors) != 1 or len(verifiers) != 1:
        return {}, {}
    return authors[0], verifiers[0]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> tuple[Any, ...]:
    return tuple(value) if isinstance(value, (list, tuple)) else ()


def _utc(value: datetime) -> datetime:
    current = value
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).replace(microsecond=0)


def _iso(value: datetime) -> str:
    return _utc(value).isoformat()


__all__ = [
    "ASSURANCE_CAPACITY_BLOCKED",
    "ASSURANCE_CAPACITY_LEASE_SECONDS",
    "ASSURANCE_CAPACITY_RESERVED",
    "IndependentAssuranceReservationStore",
    "build_assurance_renewal_request",
    "build_assurance_reservation_request",
    "canonical_digest",
    "find_assurance_tasks",
]
