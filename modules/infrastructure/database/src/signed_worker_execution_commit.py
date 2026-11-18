"""Transactional commit for a validated signed-worker terminal state."""

from __future__ import annotations
from datetime import datetime
from typing import Any, Mapping
from .signed_worker_assurance_completion import complete_assurance_reservation
from .signed_worker_execution_binding import assurance_request_matches, validated_result_context
from .signed_worker_execution_lease_fence import (
    execution_lease_allows_finalization,
)
from .signed_worker_result_ledger import persist_result_history_ledger
from .signed_worker_execution_row import (
    matching_execution_context,
    supplied_execution_receipts_match,
    update_signed_worker_final_row,
)

def commit_signed_worker_final_state(
    database: Any,
    *,
    task_id: str,
    assigned_to: str,
    claim: Mapping[str, Any],
    use: Mapping[str, Any],
    result_context: Mapping[str, Any],
    target_status: str,
    retry_not_before: str | None,
    assurance_completion: Mapping[str, Any] | None,
    lease_now: datetime,
    allow_expired_recovery: bool,
) -> bool:
    """Commit task, assurance, and result ledger in one transaction."""

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
                lease_now=lease_now,
                allow_expired_recovery=allow_expired_recovery,
            )
    except Exception:
        return False

def _apply_final_state(
    connection: Any,
    *,
    task_id: str,
    assigned_to: str,
    claim: Mapping[str, Any],
    use: Mapping[str, Any],
    result_context: Mapping[str, Any],
    target_status: str,
    retry_not_before: str | None,
    assurance_completion: Mapping[str, Any] | None,
    lease_now: datetime,
    allow_expired_recovery: bool,
) -> bool:
    validated = _validated_finalization_state(
        connection,
        task_id=task_id,
        assigned_to=assigned_to,
        claim=claim,
        use=use,
        result_context=result_context,
        assurance_completion=assurance_completion,
        lease_now=lease_now,
        allow_expired_recovery=allow_expired_recovery,
    )
    if validated is None:
        return False
    row, raw_context, final_context = validated
    if not update_signed_worker_final_row(
        connection,
        row=row,
        task_id=task_id,
        assigned_to=assigned_to,
        raw_context=raw_context,
        final_context=final_context,
        persisted_status=target_status,
        retry_not_before=retry_not_before,
    ):
        return False
    _persist_linked_effects(
        connection,
        task_id=task_id,
        assigned_to=assigned_to,
        claim=claim,
        use=use,
        final_context=final_context,
        assurance_completion=assurance_completion,
    )
    return True

def _validated_finalization_state(
    connection: Any,
    *,
    task_id: str,
    assigned_to: str,
    claim: Mapping[str, Any],
    use: Mapping[str, Any],
    result_context: Mapping[str, Any],
    assurance_completion: Mapping[str, Any] | None,
    lease_now: datetime,
    allow_expired_recovery: bool,
) -> tuple[dict[str, Any], str, Mapping[str, Any]] | None:
    row = connection.execute(
        "SELECT status, assigned_to, assigned_at, completed_at, context "
        "FROM agents_autonomous_tasks WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    authenticated = matching_execution_context(row, assigned_to, claim, use)
    supplied = dict(result_context)
    if authenticated is None or not supplied_execution_receipts_match(
        supplied, claim, use
    ):
        return None
    raw_context, authenticated_context = authenticated
    final_context = validated_result_context(authenticated_context, supplied)
    if not _finalization_inputs_match(
        connection,
        task_id=task_id,
        assigned_to=assigned_to,
        claim=claim,
        use=use,
        authenticated_context=authenticated_context,
        supplied_context=supplied,
        final_context=final_context,
        assurance_completion=assurance_completion,
        lease_now=lease_now,
        allow_expired_recovery=allow_expired_recovery,
    ):
        return None
    return dict(row), raw_context, final_context

def _finalization_inputs_match(
    connection: Any,
    *,
    task_id: str,
    assigned_to: str,
    claim: Mapping[str, Any],
    use: Mapping[str, Any],
    authenticated_context: Mapping[str, Any],
    supplied_context: Mapping[str, Any],
    final_context: Mapping[str, Any] | None,
    assurance_completion: Mapping[str, Any] | None,
    lease_now: datetime,
    allow_expired_recovery: bool,
) -> bool:
    return bool(
        final_context is not None
        and assurance_request_matches(
            authenticated_context, supplied_context, assurance_completion
        )
        and execution_lease_allows_finalization(
            connection,
            task_id=task_id,
            assigned_to=assigned_to,
            claim=claim,
            use=use,
            now=lease_now,
            allow_expired_recovery=allow_expired_recovery,
        )
    )

def _persist_linked_effects(
    connection: Any,
    *,
    task_id: str,
    assigned_to: str,
    claim: Mapping[str, Any],
    use: Mapping[str, Any],
    final_context: Mapping[str, Any],
    assurance_completion: Mapping[str, Any] | None,
) -> None:
    if assurance_completion is not None and not complete_assurance_reservation(
        connection,
        task_id=task_id,
        assigned_to=assigned_to,
        request=assurance_completion,
    ):
        raise RuntimeError("assurance_completion_rejected")
    if not persist_result_history_ledger(
        connection,
        task_id,
        final_context,
        claim_receipt_id=str(claim.get("receipt_id") or ""),
        use_receipt_id=str(use.get("receipt_id") or ""),
    ):
        raise RuntimeError("signed_worker_result_ledger_rejected")

__all__ = ["commit_signed_worker_final_state"]
