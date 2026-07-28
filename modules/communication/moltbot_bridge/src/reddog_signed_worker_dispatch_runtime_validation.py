"""Validation and authenticated lineage binding for worker dispatch."""

from __future__ import annotations

from dataclasses import dataclass
import hmac
from typing import Any, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_architect_fix_publication_effect_binding import (
    signed_publication_effect_binding_reasons,
)
from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT,
    WORKER_DISPATCH_INTENT_FIELDS,
    WORKER_DISPATCH_RECEIPT_FIELDS,
    derive_worker_dispatch_roles,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_dispatch_runtime_types import (
    WorkerDispatchRuntimeReason,
    canonical_digest,
    dedupe,
    mapping,
    sequence,
)
from modules.communication.moltbot_bridge.src.reddog_worker_dispatch_authority_binding import (
    WorkerDispatchAuthorityVerificationContext,
    authenticated_recorded_authority_binding,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    build_work_order_materialization_binding,
    canonical_full_work_order_digest,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_consumer_dryrun import (
    plan_reddog_wre_queue_consumer_dry_run,
)


_ALLOWED_WORKER_RUNTIMES = frozenset({"0102", "openclaw", "hermes"})


@dataclass(frozen=True)
class ValidatedDispatchRequest:
    receipt: Mapping[str, Any]
    intents: tuple[Mapping[str, Any], ...]
    queue_item: Mapping[str, Any]


@dataclass(frozen=True)
class AuthenticatedDispatchBinding:
    work_authority: Mapping[str, Any]
    queue_consumer_receipt: Mapping[str, Any]
    work_order_materialization_binding: Mapping[str, Any]


def validate_dispatch_request(
    *,
    worker_dispatch_dryrun_result: Mapping[str, Any],
    work_state_snapshot: Mapping[str, Any],
    queue_item_id: str,
    writer_present: bool,
    seen_intent_ids: Optional[set[str]],
) -> tuple[ValidatedDispatchRequest, tuple[str, ...]]:
    request = _request(worker_dispatch_dryrun_result, work_state_snapshot, queue_item_id)
    reasons = list(_basic_reasons(worker_dispatch_dryrun_result, request))
    if not writer_present:
        reasons.append(WorkerDispatchRuntimeReason.WRITER_MISSING)
    reasons.extend(_queue_binding_reasons(request))
    reasons.extend(_publication_reasons(work_state_snapshot, queue_item_id, request))
    reasons.extend(_replay_and_intent_reasons(request, seen_intent_ids))
    return request, dedupe(reasons)


def authenticate_dispatch_request(
    *,
    request: ValidatedDispatchRequest,
    authority_verification_context: WorkerDispatchAuthorityVerificationContext,
    queue_authority_runtime_result: Mapping[str, Any],
    queue_authority_verification_result: Mapping[str, Any],
    work_state_snapshot: Mapping[str, Any],
    queue_item_id: str,
    created_at: str,
) -> tuple[Optional[AuthenticatedDispatchBinding], Optional[str]]:
    authority = authenticated_recorded_authority_binding(
        context=authority_verification_context,
        authority_runtime_result=queue_authority_runtime_result,
        authority_verification_result=queue_authority_verification_result,
        dryrun_receipt=request.receipt,
    )
    if not authority:
        return None, WorkerDispatchRuntimeReason.AUTHORITY_VERIFICATION_BINDING_MISMATCH
    work_authority = _work_authority(queue_authority_runtime_result)
    queue_receipt = _queue_consumer_receipt(
        work_state_snapshot, queue_item_id, created_at
    )
    work_order_binding = build_work_order_materialization_binding(
        work_order_id=str(work_authority.get("work_order_id") or ""),
        base_ref=str(work_authority.get("base_ref") or ""),
        queue_consumer_receipt=queue_receipt,
    )
    if not _work_order_matches(work_authority, queue_receipt, work_order_binding):
        return None, WorkerDispatchRuntimeReason.WORK_ORDER_BINDING_MISMATCH
    return AuthenticatedDispatchBinding(
        work_authority=work_authority,
        queue_consumer_receipt=queue_receipt,
        work_order_materialization_binding=work_order_binding,
    ), None


def _request(
    dryrun_result: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    queue_item_id: str,
) -> ValidatedDispatchRequest:
    dryrun = mapping(dryrun_result)
    receipt = mapping(dryrun.get("receipt"))
    intents = tuple(mapping(intent) for intent in sequence(receipt.get("dispatch_intents")))
    return ValidatedDispatchRequest(
        receipt=receipt,
        intents=intents,
        queue_item=_queue_item(snapshot, queue_item_id),
    )


def _basic_reasons(
    dryrun_result: Mapping[str, Any],
    request: ValidatedDispatchRequest,
) -> tuple[str, ...]:
    reasons: list[str] = []
    dryrun = mapping(dryrun_result)
    if (
        dryrun.get("accepted") is not True
        or dryrun.get("decision") != SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT
    ):
        reasons.append(WorkerDispatchRuntimeReason.DRYRUN_NOT_ACCEPTED)
    if not request.receipt:
        reasons.append(WorkerDispatchRuntimeReason.RECEIPT_MISSING)
    if not request.intents:
        reasons.append(WorkerDispatchRuntimeReason.INTENTS_MISSING)
    if not _exact_dispatch_schema(request.receipt, request.intents):
        reasons.append(WorkerDispatchRuntimeReason.DISPATCH_SCHEMA_MISMATCH)
    if not request.queue_item:
        reasons.append(WorkerDispatchRuntimeReason.QUEUE_ITEM_MISSING)
    return tuple(reasons)


def _queue_binding_reasons(request: ValidatedDispatchRequest) -> tuple[str, ...]:
    reasons: list[str] = []
    if not _wsp15_matches(request.receipt, request.queue_item):
        reasons.append(WorkerDispatchRuntimeReason.WSP15_BINDING_MISMATCH)
    if not _model_binding_matches(request.receipt, request.queue_item):
        reasons.append(WorkerDispatchRuntimeReason.MODEL_RUNTIME_BINDING_MISMATCH)
    if not _worker_plan_matches(request.receipt, request.queue_item):
        reasons.append(WorkerDispatchRuntimeReason.WORKER_PLAN_BINDING_MISMATCH)
    return tuple(reasons)


def _publication_reasons(
    snapshot: Mapping[str, Any],
    queue_item_id: str,
    request: ValidatedDispatchRequest,
) -> tuple[str, ...]:
    reasons = signed_publication_effect_binding_reasons(
        snapshot,
        request.receipt,
        queue_item_id=queue_item_id,
        claim_id=str(request.queue_item.get("claim_id") or ""),
    )
    return (
        (WorkerDispatchRuntimeReason.ARCHITECT_FIX_PUBLICATION_BINDING_MISMATCH,)
        if reasons
        else ()
    )


def _replay_and_intent_reasons(
    request: ValidatedDispatchRequest,
    seen_intent_ids: Optional[set[str]],
) -> tuple[str, ...]:
    reasons: list[str] = []
    if seen_intent_ids is not None and any(
        str(intent.get("intent_id") or "") in seen_intent_ids
        for intent in request.intents
    ):
        reasons.append(WorkerDispatchRuntimeReason.IDEMPOTENCY_REPLAY)
    if any(not _intent_safe(intent, request.receipt) for intent in request.intents):
        reasons.append(WorkerDispatchRuntimeReason.INTENT_UNSAFE)
    return tuple(reasons)


def _intent_safe(intent: Mapping[str, Any], receipt: Mapping[str, Any]) -> bool:
    if not intent or str(intent.get("worker_runtime") or "") not in _ALLOWED_WORKER_RUNTIMES:
        return False
    if not str(intent.get("role") or "") or not str(intent.get("capability") or ""):
        return False
    flags = (
        "dry_run_only",
        "no_worker_spawn_performed",
        "no_openclaw_enqueue_performed",
        "no_hermes_dispatch_performed",
    )
    if any(intent.get(flag) is not True for flag in flags):
        return False
    binding_fields = (
        "work_order_id",
        "foundup_id",
        "requested_operation",
        "wsp15_allocation_receipt_id",
        "wsp15_allocation_digest",
        "model_runtime_binding_receipt_id",
        "model_runtime_binding_digest",
        "architect_fix_publication_receipt_id",
        "architect_fix_publication_binding_digest",
        "verified_work_authority_digest",
        "authority_verification_receipt_id",
        "authority_verification_receipt_digest",
    )
    return all(str(intent.get(key) or "") == str(receipt.get(key) or "") for key in binding_fields)


def _exact_dispatch_schema(
    receipt: Mapping[str, Any],
    intents: Sequence[Mapping[str, Any]],
) -> bool:
    return (
        set(receipt) == WORKER_DISPATCH_RECEIPT_FIELDS
        and all(set(intent) == WORKER_DISPATCH_INTENT_FIELDS for intent in intents)
    )


def _worker_plan_matches(
    receipt: Mapping[str, Any],
    queue_item: Mapping[str, Any],
) -> bool:
    expected = derive_worker_dispatch_roles(mapping(queue_item.get("wsp15_allocation_receipt")))
    intents = tuple(mapping(value) for value in sequence(receipt.get("dispatch_intents")))
    actual = tuple(
        (
            str(intent.get("role") or ""),
            str(intent.get("worker_runtime") or ""),
            str(intent.get("capability") or ""),
        )
        for intent in intents
    )
    return int(receipt.get("dispatch_intent_count") or -1) == len(intents) and actual == expected


def _wsp15_matches(receipt: Mapping[str, Any], queue_item: Mapping[str, Any]) -> bool:
    allocation = mapping(queue_item.get("wsp15_allocation_receipt"))
    return bool(receipt and queue_item and allocation) and (
        str(receipt.get("wsp15_allocation_receipt_id") or "")
        == str(allocation.get("receipt_id") or "")
        and str(receipt.get("wsp15_allocation_digest") or "")
        == canonical_digest(allocation)
    )


def _model_binding_matches(
    receipt: Mapping[str, Any],
    queue_item: Mapping[str, Any],
) -> bool:
    receipt_id = str(receipt.get("model_runtime_binding_receipt_id") or "")
    receipt_digest = str(receipt.get("model_runtime_binding_digest") or "")
    queue_id = str(queue_item.get("model_runtime_binding_receipt_id") or "")
    queue_digest = str(queue_item.get("model_runtime_binding_digest") or "")
    if bool(receipt_id) != bool(receipt_digest) or bool(queue_id) != bool(queue_digest):
        return False
    if not receipt_id and not queue_id:
        return True
    return (
        receipt_id == queue_id
        and receipt_digest == queue_digest
        and receipt_id.startswith("reddog_model_runtime_binding:")
        and receipt_digest.startswith("sha256:")
    )


def _queue_item(snapshot: Mapping[str, Any], queue_item_id: str) -> Mapping[str, Any]:
    for item in sequence(snapshot.get("wre_queue_items")):
        candidate = mapping(item)
        if str(candidate.get("queue_item_id") or "") == str(queue_item_id or ""):
            return candidate
    return {}


def _work_authority(runtime_result: Mapping[str, Any]) -> Mapping[str, Any]:
    return mapping(mapping(mapping(runtime_result).get("authority_result")).get("work_authority"))


def _queue_consumer_receipt(
    snapshot: Mapping[str, Any],
    queue_item_id: str,
    created_at: str,
) -> Mapping[str, Any]:
    result = plan_reddog_wre_queue_consumer_dry_run(
        snapshot,
        now_iso=created_at,
        requested_queue_item_id=queue_item_id,
        require_governed_lineage=True,
    )
    if result.accepted is not True or result.receipt is None:
        return {}
    return result.receipt.to_dict()


def _work_order_matches(
    work_authority: Mapping[str, Any],
    queue_receipt: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> bool:
    queue_digest = canonical_full_work_order_digest(queue_receipt)
    return bool(queue_receipt) and hmac.compare_digest(
        queue_digest,
        str(work_authority.get("queue_consumer_receipt_digest") or ""),
    ) and hmac.compare_digest(
        queue_digest,
        str(binding.get("queue_consumer_receipt_digest") or ""),
    )
