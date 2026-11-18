"""Publish signed RedDog worker-dispatch intents to AgentDB.

This stable facade validates signed dispatch inputs, binds them to the
authoritative queue-consumer lineage, stages held tasks, commits publication
authority, and activates the exact batch. It does not execute workers or
mutate repository content.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_signed_worker_agentdb_envelope import (
    SIGNED_WORKER_DISPATCH_TASK_SKILL,
    SIGNED_WORKER_DISPATCH_TASK_SOURCE,
    WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_dispatch_agentdb_writer import (
    AgentDbSignedWorkerDispatchTaskWriter,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_dispatch_runtime_types import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT,
    SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_REJECT,
    SignedWorkerDispatchRuntimeReceipt,
    SignedWorkerDispatchRuntimeResult,
    SignedWorkerDispatchTaskSpec,
    SignedWorkerDispatchTaskWriter,
    WorkerDispatchRuntimeReason,
    iso8601,
    reject_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_dispatch_runtime_validation import (
    AuthenticatedDispatchBinding,
    ValidatedDispatchRequest,
    authenticate_dispatch_request,
    validate_dispatch_request,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_dispatch_task_builder import (
    build_signed_worker_dispatch_runtime_receipt,
    build_signed_worker_dispatch_task,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_publication_admission import (
    complete_signed_worker_publication,
    prepare_signed_worker_publication,
)
from modules.communication.moltbot_bridge.src.reddog_worker_dispatch_authority_binding import (
    WorkerDispatchAuthorityVerificationContext,
)


def publish_reddog_signed_worker_dispatch_runtime(
    *,
    worker_dispatch_dryrun_result: Mapping[str, Any],
    queue_authority_runtime_result: Mapping[str, Any],
    queue_authority_verification_result: Mapping[str, Any],
    authority_verification_context: WorkerDispatchAuthorityVerificationContext,
    work_state_snapshot: Mapping[str, Any],
    queue_item_id: str,
    writer: Optional[SignedWorkerDispatchTaskWriter],
    seen_intent_ids: Optional[set[str]] = None,
    now: Optional[datetime] = None,
) -> SignedWorkerDispatchRuntimeResult:
    """Stage accepted signed worker intents, commit authority, then activate."""

    created_at = iso8601(now)
    request, reasons = validate_dispatch_request(
        worker_dispatch_dryrun_result=worker_dispatch_dryrun_result,
        work_state_snapshot=work_state_snapshot,
        queue_item_id=queue_item_id,
        writer_present=writer is not None,
        seen_intent_ids=seen_intent_ids,
    )
    if reasons:
        return reject_runtime(reasons)
    binding, reason = authenticate_dispatch_request(
        request=request,
        authority_verification_context=authority_verification_context,
        queue_authority_runtime_result=queue_authority_runtime_result,
        queue_authority_verification_result=queue_authority_verification_result,
        work_state_snapshot=work_state_snapshot,
        queue_item_id=queue_item_id,
        created_at=created_at,
    )
    if binding is None:
        return reject_runtime([str(reason or "")])
    return _publish_authenticated(
        request=request,
        binding=binding,
        authority_runtime_result=queue_authority_runtime_result,
        authority_verification_context=authority_verification_context,
        writer=writer,
        seen_intent_ids=seen_intent_ids,
        created_at=created_at,
    )


def _publish_authenticated(
    *,
    request: ValidatedDispatchRequest,
    binding: AuthenticatedDispatchBinding,
    authority_runtime_result: Mapping[str, Any],
    authority_verification_context: WorkerDispatchAuthorityVerificationContext,
    writer: Optional[SignedWorkerDispatchTaskWriter],
    seen_intent_ids: Optional[set[str]],
    created_at: str,
) -> SignedWorkerDispatchRuntimeResult:
    tasks = _build_tasks(request, binding, authority_runtime_result)
    receipt = build_signed_worker_dispatch_runtime_receipt(
        receipt=request.receipt,
        queue_item=request.queue_item,
        tasks=tasks,
        created_at=created_at,
    )
    admission = prepare_signed_worker_publication(
        nonce_store=authority_verification_context.nonce_store,
        work_authority=binding.work_authority,
        tasks=tasks,
        receipt=receipt,
    )
    if admission is None:
        return reject_runtime(
            [WorkerDispatchRuntimeReason.AUTHORITY_VERIFICATION_BINDING_MISMATCH]
        )
    assert writer is not None
    if not _writer_accepts(
        writer,
        tasks,
        receipt,
        recovery_status=admission.status if admission.recovering else "",
    ):
        return reject_runtime([WorkerDispatchRuntimeReason.WRITER_REJECTED])
    if not complete_signed_worker_publication(
        authority_verification_context.nonce_store,
        admission,
    ):
        return reject_runtime([WorkerDispatchRuntimeReason.WRITER_REJECTED])
    if not _writer_activates(writer, tasks, receipt):
        return reject_runtime([WorkerDispatchRuntimeReason.WRITER_REJECTED])
    return _accepted_result(request, tasks, receipt, seen_intent_ids)


def _accepted_result(
    request: ValidatedDispatchRequest,
    tasks: tuple[SignedWorkerDispatchTaskSpec, ...],
    receipt: SignedWorkerDispatchRuntimeReceipt,
    seen_intent_ids: Optional[set[str]],
) -> SignedWorkerDispatchRuntimeResult:
    if seen_intent_ids is not None:
        seen_intent_ids.update(
            str(intent.get("intent_id") or "") for intent in request.intents
        )
    return SignedWorkerDispatchRuntimeResult(
        accepted=True,
        decision=SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT,
        receipt=receipt,
        tasks=tasks,
        rejection_reasons=(),
    )


def _build_tasks(
    request: ValidatedDispatchRequest,
    binding: AuthenticatedDispatchBinding,
    authority_runtime_result: Mapping[str, Any],
) -> tuple[SignedWorkerDispatchTaskSpec, ...]:
    return tuple(
        build_signed_worker_dispatch_task(
            queue_item=request.queue_item,
            dryrun_receipt=request.receipt,
            intent=intent,
            work_authority=binding.work_authority,
            queue_authority_runtime_result=authority_runtime_result,
            queue_consumer_receipt=binding.queue_consumer_receipt,
            work_order_materialization_binding=(
                binding.work_order_materialization_binding
            ),
        )
        for intent in request.intents
    )


def _writer_accepts(
    writer: SignedWorkerDispatchTaskWriter,
    tasks: Sequence[SignedWorkerDispatchTaskSpec],
    receipt: SignedWorkerDispatchRuntimeReceipt,
    *,
    recovery_status: str = "",
) -> bool:
    try:
        operation = writer.enqueue_signed_worker_dispatch_tasks
        if recovery_status:
            method_name = "recover_signed_worker_dispatch_tasks"
            if recovery_status == "APPLIED":
                method_name = "recover_applied_signed_worker_dispatch_tasks"
            operation = getattr(
                writer,
                method_name,
                None,
            )
            if not callable(operation):
                return False
        result = operation(tasks, receipt)
    except Exception:
        return False
    if not isinstance(result, Mapping) or result.get("ok") is not True:
        return False
    created = tuple(str(value) for value in result.get("created_task_ids", ()))
    return created == tuple(task.task_id for task in tasks)


def _writer_activates(
    writer: SignedWorkerDispatchTaskWriter,
    tasks: Sequence[SignedWorkerDispatchTaskSpec],
    receipt: SignedWorkerDispatchRuntimeReceipt,
) -> bool:
    operation = getattr(writer, "activate_signed_worker_dispatch_tasks", None)
    if not callable(operation):
        return False
    try:
        result = operation(tasks, receipt)
    except Exception:
        return False
    if not isinstance(result, Mapping) or result.get("ok") is not True:
        return False
    activated = tuple(str(value) for value in result.get("created_task_ids", ()))
    return activated == tuple(task.task_id for task in tasks)


__all__ = [
    "AgentDbSignedWorkerDispatchTaskWriter",
    "SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT",
    "SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_REJECT",
    "SIGNED_WORKER_DISPATCH_TASK_SKILL",
    "SIGNED_WORKER_DISPATCH_TASK_SOURCE",
    "SignedWorkerDispatchRuntimeReceipt",
    "SignedWorkerDispatchRuntimeResult",
    "SignedWorkerDispatchTaskSpec",
    "SignedWorkerDispatchTaskWriter",
    "WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION",
    "WorkerDispatchRuntimeReason",
    "publish_reddog_signed_worker_dispatch_runtime",
]
