"""Process-local, one-shot admission for RedDog worktree side effects.

Persisted queue stage results are audit records only.  They cannot recreate the
opaque capability held by this registry and therefore cannot authorize a
worktree runner after restart, replay, or chain splicing.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease import (
    AuthoritativeUseLease,
    consume_authoritative_use_lease,
    is_authoritative_use_lease,
)


def _digest(value: Mapping[str, Any]) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class WorktreeAdmissionCapability:
    """Opaque admission that deliberately has no serialization method."""

    queue_item_id: str
    selected_slice: str
    work_order_id: str
    work_order_digest: str
    executor_plan_digest: str
    valve_decision_digest: str
    expires_at_epoch: int
    _authoritative_use_lease: AuthoritativeUseLease
    _seal: object


class InMemoryWorktreeAdmissionRegistry:
    """Issue and consume process-local authoritative admissions exactly once."""

    def __init__(self) -> None:
        self._seal = object()
        self._lock = threading.Lock()
        self._capabilities: dict[tuple[str, str], WorktreeAdmissionCapability] = {}

    def issue(
        self,
        *,
        queue_item_id: Optional[str],
        selected_slice: Optional[str],
        work_order: Mapping[str, Any],
        executor_plan_result: Mapping[str, Any],
        valve_decision: Mapping[str, Any],
        signed_authority_reverified: bool,
        authoritative_use_lease: Optional[AuthoritativeUseLease],
    ) -> bool:
        queue_id = str(queue_item_id or "").strip()
        slice_id = str(selected_slice or "").strip()
        work_order_id = str(work_order.get("work_order_id") or "").strip()
        if not all((queue_id, slice_id, work_order_id)):
            return False
        if signed_authority_reverified is not True or not is_authoritative_use_lease(authoritative_use_lease):
            return False
        capability = WorktreeAdmissionCapability(
            queue_item_id=queue_id,
            selected_slice=slice_id,
            work_order_id=work_order_id,
            work_order_digest=_digest(work_order),
            executor_plan_digest=_digest(executor_plan_result),
            valve_decision_digest=_digest(valve_decision),
            expires_at_epoch=authoritative_use_lease.expires_at_epoch,
            _authoritative_use_lease=authoritative_use_lease,
            _seal=self._seal,
        )
        with self._lock:
            self._capabilities[(queue_id, work_order_id)] = capability
        return True

    def consume(
        self,
        *,
        queue_item_id: Optional[str],
        selected_slice: Optional[str],
        work_order: Mapping[str, Any],
        executor_plan_result: Mapping[str, Any],
        valve_decision: Mapping[str, Any],
    ) -> Optional[WorktreeAdmissionCapability]:
        queue_id = str(queue_item_id or "").strip()
        work_order_id = str(work_order.get("work_order_id") or "").strip()
        with self._lock:
            capability = self._capabilities.pop((queue_id, work_order_id), None)
        if capability is None or capability._seal is not self._seal:
            return None
        expected = (
            capability.selected_slice == str(selected_slice or "").strip()
            and capability.work_order_digest == _digest(work_order)
            and capability.executor_plan_digest == _digest(executor_plan_result)
            and capability.valve_decision_digest == _digest(valve_decision)
        )
        if not expected or not consume_authoritative_use_lease(capability._authoritative_use_lease):
            return None
        return capability


__all__ = [
    "InMemoryWorktreeAdmissionRegistry",
    "WorktreeAdmissionCapability",
]
