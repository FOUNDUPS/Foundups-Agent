"""Validated entrypoints for signed-worker terminal persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .signed_worker_execution_binding import finalization_binding
from .signed_worker_execution_commit import commit_signed_worker_final_state
from .signed_worker_finalization_status import finalization_status_matches


_TARGET_STATUSES = {"completed", "failed", "pending"}
SIGNED_WORKER_TASK_PREFIX = "reddog-worker-dispatch-"


def is_signed_worker_task_id(task_id: str) -> bool:
    """Return whether generic task finalizers must reject this namespace."""

    return str(task_id or "").startswith(SIGNED_WORKER_TASK_PREFIX)


def finalize_signed_worker_execution(
    db: Any,
    task_id: str,
    *,
    context: Mapping[str, Any],
    accepted: bool,
    result_context: Mapping[str, Any],
    target_status: str | None = None,
    retry_not_before: str | None = None,
    assurance_completion: Mapping[str, Any] | None = None,
) -> bool:
    """Persist a normal result only while the exact execution lease is active."""

    binding = _validated_binding(
        task_id=task_id,
        context=context,
        accepted=accepted,
        result_context=result_context,
        target_status=target_status,
        assurance_completion=assurance_completion,
        reject_expired_recovery=True,
    )
    if binding is None:
        return False
    assigned_to, claim, use, status = binding
    return commit_signed_worker_final_state(
        db.db,
        task_id=task_id,
        assigned_to=assigned_to,
        claim=claim,
        use=use,
        result_context=result_context,
        target_status=status,
        retry_not_before=retry_not_before,
        assurance_completion=assurance_completion,
        lease_now=datetime.now(timezone.utc),
        allow_expired_recovery=False,
    )


def finalize_expired_signed_worker_execution_recovery(
    db: Any,
    task_id: str,
    *,
    context: Mapping[str, Any],
    result_context: Mapping[str, Any],
    recovery_now: datetime,
    assurance_completion: Mapping[str, Any] | None = None,
) -> bool:
    """Persist only the canonical negative result for an expired execution."""

    binding = _validated_binding(
        task_id=task_id,
        context=context,
        accepted=False,
        result_context=result_context,
        target_status="failed",
        assurance_completion=assurance_completion,
        reject_expired_recovery=False,
    )
    if binding is None or not _is_expired_recovery(result_context):
        return False
    assigned_to, claim, use, _ = binding
    return commit_signed_worker_final_state(
        db.db,
        task_id=task_id,
        assigned_to=assigned_to,
        claim=claim,
        use=use,
        result_context=result_context,
        target_status="failed",
        retry_not_before=None,
        assurance_completion=assurance_completion,
        lease_now=recovery_now,
        allow_expired_recovery=True,
    )


def _validated_binding(
    *,
    task_id: str,
    context: Mapping[str, Any],
    accepted: bool,
    result_context: Mapping[str, Any],
    target_status: str | None,
    assurance_completion: Mapping[str, Any] | None,
    reject_expired_recovery: bool,
) -> tuple[str, Mapping[str, Any], Mapping[str, Any], str] | None:
    binding = finalization_binding(
        task_id,
        context.get("signed_worker_execution_claim"),
        context.get("signed_worker_execution_use"),
    )
    status = target_status or ("completed" if accepted is True else "failed")
    if (
        binding is None
        or status not in _TARGET_STATUSES
        or not finalization_status_matches(
            accepted, status, assurance_completion, result_context
        )
        or (reject_expired_recovery and _is_expired_recovery(result_context))
    ):
        return None
    return (*binding, status)


def _is_expired_recovery(context: Mapping[str, Any]) -> bool:
    receipt = context.get("signed_worker_task_last_result")
    if not isinstance(receipt, Mapping):
        return False
    reasons = receipt.get("rejection_reasons")
    return bool(
        receipt.get("accepted") is False
        and receipt.get("decision") == "EXECUTION_LEASE_RECOVERED"
        and receipt.get("effect_commit_state") == "INDETERMINATE"
        and isinstance(reasons, list)
        and "signed_worker_execution_lease_expired" in reasons
    )


__all__ = [
    "SIGNED_WORKER_TASK_PREFIX",
    "finalize_expired_signed_worker_execution_recovery",
    "finalize_signed_worker_execution",
    "is_signed_worker_task_id",
]
