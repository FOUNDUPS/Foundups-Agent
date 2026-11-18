"""One-use admission from current queue truth into signer authority issuance."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Any, Mapping
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_progressive_execution_stage_policy import (
    validate_queue_progressive_stage_binding,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    canonical_reddog_wsp15_allocation_digest,
)


class VerifiedQueueAuthorityAdmission:
    """Opaque, process-local proof that current queue truth admitted a request."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "VerifiedQueueAuthorityAdmission":
        raise TypeError("queue_authority_admission_direct_construction_forbidden")

    def __copy__(self) -> Any:
        raise TypeError("queue_authority_admission_copy_forbidden")

    def __deepcopy__(self, _memo: Any) -> Any:
        raise TypeError("queue_authority_admission_copy_forbidden")

    def __reduce__(self) -> Any:
        raise TypeError("queue_authority_admission_pickle_forbidden")


@dataclass(frozen=True)
class _AdmissionSeal:
    request_digest: str
    queue_item_digest: str


_LOCK = threading.Lock()
_ADMISSIONS: WeakKeyDictionary[VerifiedQueueAuthorityAdmission, _AdmissionSeal] = (
    WeakKeyDictionary()
)


def _digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _request_mapping(request: Any) -> Mapping[str, Any]:
    try:
        payload = request.to_dict()
    except Exception:
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _queue_item_matches_request(
    queue_item: Mapping[str, Any], request: Mapping[str, Any]
) -> bool:
    receipt = request.get("queue_consumer_receipt")
    allocation = queue_item.get("wsp15_allocation_receipt")
    stage = request.get("progressive_policy_stage_receipt")
    if not all(
        isinstance(value, Mapping)
        for value in (receipt, allocation, stage)
    ):
        return False
    exact_fields = (
        "queue_item_id",
        "slice_id",
        "claim_id",
        "worker_id",
        "progressive_policy_stage_receipt_id",
        "progressive_policy_stage_digest",
    )
    optional_fields = (
        "model_selection_receipt_id",
        "model_selection_digest",
        "model_runtime_binding_receipt_id",
        "model_runtime_binding_digest",
        "model_runtime_binding_verification_receipt_id",
        "model_runtime_binding_verification_digest",
        "memex_supply_receipt_id",
        "memex_supply_digest",
    )
    return bool(
        queue_item.get("status") == "QUEUED"
        and queue_item.get("no_execution_performed") is True
        and validate_queue_progressive_stage_binding(queue_item, allocation)
        and all(queue_item.get(field) == receipt.get(field) for field in exact_fields)
        and all(
            str(queue_item.get(field) or "") == str(receipt.get(field) or "")
            for field in optional_fields
        )
        and _digest(allocation)
        == _digest(receipt.get("wsp15_allocation_receipt") or {})
        and _digest(queue_item.get("progressive_policy_stage_receipt") or {})
        == _digest(receipt.get("progressive_policy_stage_receipt") or {})
        and allocation.get("receipt_id")
        == receipt.get("wsp15_allocation_receipt_id")
        and canonical_reddog_wsp15_allocation_digest(allocation)
        == receipt.get("wsp15_allocation_digest")
        and canonical_full_work_order_digest(receipt)
        == request.get("queue_consumer_receipt_digest")
        and receipt.get("slice_id") == stage.get("selected_slice")
    )


def _admit_current_queue_authority(
    *, request: Any, authoritative_queue_item: Mapping[str, Any]
) -> VerifiedQueueAuthorityAdmission | None:
    """Mint one opaque proof only from a matching current authoritative item."""

    payload = _request_mapping(request)
    if not payload or not isinstance(authoritative_queue_item, Mapping):
        return None
    try:
        if not _queue_item_matches_request(authoritative_queue_item, payload):
            return None
        seal = _AdmissionSeal(_digest(payload), _digest(authoritative_queue_item))
    except (TypeError, ValueError):
        return None
    capability = object.__new__(VerifiedQueueAuthorityAdmission)
    with _LOCK:
        _ADMISSIONS[capability] = seal
    return capability


def consume_current_queue_authority(
    capability: Any, *, request: Any
) -> bool:
    """Consume one admission and bind it to the unchanged signer request."""

    if type(capability) is not VerifiedQueueAuthorityAdmission:
        return False
    with _LOCK:
        seal = _ADMISSIONS.pop(capability, None)
    if seal is None:
        return False
    payload = _request_mapping(request)
    try:
        return hmac.compare_digest(seal.request_digest, _digest(payload))
    except (TypeError, ValueError):
        return False


__all__ = [
    "VerifiedQueueAuthorityAdmission",
    "consume_current_queue_authority",
]
