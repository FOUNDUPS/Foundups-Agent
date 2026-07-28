"""Exact-CAS persistence for admitted RedDog signed-worker executions."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Mapping

from modules.infrastructure.database.src.signed_worker_assurance_completion import (
    complete_assurance_reservation,
)
from modules.infrastructure.database.src.signed_worker_execution_binding import (
    assurance_request_matches,
    canonical_digest,
    finalization_binding,
)
from modules.infrastructure.database.src.signed_worker_result_ledger import (
    persist_result_history_ledger,
)


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
    """Persist a result only for the exact admitted owner and context."""

    binding = finalization_binding(
        task_id,
        context.get("signed_worker_execution_claim"),
        context.get("signed_worker_execution_use"),
    )
    status = target_status or ("completed" if accepted is True else "failed")
    if binding is None or status not in _TARGET_STATUSES:
        return False
    assigned_to, claim, use = binding
    return _commit_final_state(
        db.db,
        task_id=task_id,
        assigned_to=assigned_to,
        claim=claim,
        use=use,
        result_context=result_context,
        target_status=status,
        retry_not_before=retry_not_before,
        assurance_completion=assurance_completion,
    )


def _commit_final_state(
    database: Any, *, task_id: str, assigned_to: str,
    claim: Mapping[str, Any], use: Mapping[str, Any],
    result_context: Mapping[str, Any],
    target_status: str, retry_not_before: str | None,
    assurance_completion: Mapping[str, Any] | None,
) -> bool:
    try:
        with database.get_connection() as connection:
            return _apply_final_state(
                connection,
                task_id=task_id,
                assigned_to=assigned_to,
                claim=claim,
                use=use,
                result_context=result_context,
                target_status=target_status,
                retry_not_before=retry_not_before,
                assurance_completion=assurance_completion,
            )
    except Exception:
        return False


def _apply_final_state(
    connection: Any, *, task_id: str, assigned_to: str,
    claim: Mapping[str, Any], use: Mapping[str, Any],
    result_context: Mapping[str, Any], target_status: str,
    retry_not_before: str | None,
    assurance_completion: Mapping[str, Any] | None,
) -> bool:
    row = connection.execute(
        "SELECT status, assigned_to, assigned_at, completed_at, context "
        "FROM agents_autonomous_tasks WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    raw_context = _matching_context(
        row, assigned_to, claim, use, expected_status="executing"
    )
    final_context = dict(result_context)
    if (
        raw_context is None
        or final_context.get("signed_worker_execution_claim") != claim
        or final_context.get("signed_worker_execution_use") != use
        or not assurance_request_matches(final_context, assurance_completion)
    ):
        return False
    if not _update_final_row(
        connection, row=dict(row), task_id=task_id,
        assigned_to=assigned_to, raw_context=raw_context,
        final_context=final_context, expected_status="executing",
        persisted_status=target_status, retry_not_before=retry_not_before,
    ):
        return False
    if assurance_completion is not None and not complete_assurance_reservation(
        connection, task_id=task_id, assigned_to=assigned_to,
        request=assurance_completion,
    ):
        raise RuntimeError("assurance_completion_rejected")
    if not persist_result_history_ledger(
        connection, task_id, final_context,
        claim_receipt_id=str(claim.get("receipt_id") or ""),
        use_receipt_id=str(use.get("receipt_id") or ""),
    ):
        raise RuntimeError("signed_worker_result_ledger_rejected")
    return True


def _matching_context(
    row: Any, assigned_to: str, claim: Mapping[str, Any],
    use: Mapping[str, Any], *, expected_status: str,
) -> str | None:
    if row is None:
        return None
    payload, raw_context = dict(row), str(dict(row).get("context") or "")
    try:
        stored = json.loads(raw_context)
    except (TypeError, ValueError):
        return None
    if (
        payload.get("status") != expected_status
        or str(payload.get("assigned_to") or "") != assigned_to
        or not isinstance(stored, dict)
        or stored.get("signed_worker_execution_claim") != claim
        or stored.get("signed_worker_execution_use") != use
    ):
        return None
    stored.pop("signed_worker_execution_claim", None)
    stored.pop("signed_worker_execution_use", None)
    return (
        raw_context
        if claim.get("context_digest") == canonical_digest(stored)
        else None
    )


def _update_final_row(
    connection: Any, *, row: Mapping[str, Any], task_id: str,
    assigned_to: str, raw_context: str, final_context: Mapping[str, Any],
    expected_status: str, persisted_status: str,
    retry_not_before: str | None,
) -> bool:
    requeue = persisted_status == "pending"
    changed = connection.execute(
        "UPDATE agents_autonomous_tasks SET context = ?, status = ?, "
        "completed_at = ?, retry_not_before = ?, assigned_to = ?, assigned_at = ? "
        "WHERE task_id = ? AND status = ? AND assigned_to = ? AND context = ?",
        (
            json.dumps(dict(final_context), sort_keys=True),
            persisted_status,
            None if requeue else row.get("completed_at") or datetime.now().isoformat(),
            retry_not_before if requeue else None,
            None if requeue else assigned_to,
            None if requeue else row.get("assigned_at"),
            task_id, expected_status, assigned_to, raw_context,
        ),
    ).rowcount
    return changed == 1
__all__ = [
    "SIGNED_WORKER_TASK_PREFIX",
    "finalize_signed_worker_execution",
    "is_signed_worker_task_id",
]
