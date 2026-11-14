"""Cross-object terminal-state rules for signed-worker finalization."""

from __future__ import annotations

from typing import Any, Mapping

from .signed_worker_assurance_request import (
    canonical_request_digest,
    canonical_request_json,
    validated_assurance_completion_request,
)
from .signed_worker_result_ledger import validate_result_history_ledger


_POSITIVE_ASSURANCE_STATUSES = frozenset({"ACCEPT", "VERIFIED"})
_NEGATIVE_ASSURANCE_STATUSES = frozenset({"REJECT", "FAILED", "CANCELLED"})
_ACCEPT_CLAIM_STATUSES = frozenset(
    {"ACCEPT", "DIRECT_ACCEPT", "SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT"}
)
_REQUEUE_CLAIM_STATUSES = frozenset(
    {"DIRECT_REQUEUED", "SIGNED_WORKER_OPENCLAW_CLAIM_REQUEUED"}
)
_REJECT_CLAIM_STATUSES = frozenset(
    {"REJECT", "DIRECT_REJECT", "SIGNED_WORKER_OPENCLAW_CLAIM_REJECT"}
)


def finalization_status_matches(
    accepted: bool,
    target_status: str,
    assurance_completion: Mapping[str, Any] | None,
    result_context: Mapping[str, Any],
) -> bool:
    """Reject contradictory task, receipt, and assurance terminal states."""

    receipt = result_context.get("signed_worker_task_last_result")
    if not isinstance(receipt, Mapping) or receipt.get("accepted") is not accepted:
        return False
    claim_status = str(receipt.get("claim_status") or "")
    if target_status == "pending":
        return (
            accepted is True
            and assurance_completion is None
            and claim_status in _REQUEUE_CLAIM_STATUSES
        )
    if target_status == "completed":
        if accepted is not True or claim_status not in _ACCEPT_CLAIM_STATUSES:
            return False
        allowed_assurance = _POSITIVE_ASSURANCE_STATUSES
    elif target_status == "failed":
        if accepted is not False or claim_status not in _REJECT_CLAIM_STATUSES:
            return False
        allowed_assurance = _NEGATIVE_ASSURANCE_STATUSES
    else:
        return False
    if assurance_completion is None:
        return True
    terminal = str(assurance_completion.get("terminal_status") or "").upper()
    return terminal in allowed_assurance


def durable_terminal_state_matches(
    connection: Any,
    *,
    task_id: str,
    task: Mapping[str, Any],
    target_status: str,
    decision: str,
) -> bool:
    """Require independently durable proof before accepting a raced finalization."""

    context = task.get("context")
    context = dict(context) if isinstance(context, Mapping) else {}
    receipt = context.get("signed_worker_task_last_result")
    receipt = dict(receipt) if isinstance(receipt, Mapping) else {}
    if (
        task.get("status") != target_status
        or receipt.get("decision") != decision
        or not validate_result_history_ledger(connection, task_id, context)
    ):
        return False
    request = receipt.get("assurance_completion_request")
    row = _assurance_row(connection, task_id)
    if request is None:
        return row is None
    return _terminal_assurance_matches(
        row,
        request=request,
        task_id=task_id,
        assigned_to=str(task.get("assigned_to") or ""),
    )


def _assurance_row(connection: Any, task_id: str) -> Mapping[str, Any] | None:
    rows = connection.execute(
        "SELECT * FROM agents_independent_assurance_reservations "
        "WHERE verifier_task_id = ? ORDER BY created_at DESC LIMIT 2",
        (task_id,),
    ).fetchall()
    return dict(rows[0]) if len(rows) == 1 else None


def _terminal_assurance_matches(
    row: Mapping[str, Any] | None,
    *,
    request: Any,
    task_id: str,
    assigned_to: str,
) -> bool:
    normalized = validated_assurance_completion_request(
        request if isinstance(request, Mapping) else {},
        task_id=task_id,
        assigned_to=assigned_to,
    )
    if row is None or normalized is None:
        return False
    return all(
        (
            row.get("status") == normalized["terminal_status"],
            row.get("terminal_status") == normalized["terminal_status"],
            row.get("terminal_receipt_id") == normalized["terminal_receipt_id"],
            row.get("terminal_receipt_digest")
            == normalized["terminal_receipt_digest"],
            row.get("admission_reservation_digest")
            == normalized["admission_reservation_digest"],
            row.get("verifier_principal_id")
            == normalized["verifier_principal_id"],
            row.get("staged_completion_json")
            == canonical_request_json(normalized),
            row.get("staged_completion_digest")
            == canonical_request_digest(normalized),
        )
    )


__all__ = ["durable_terminal_state_matches", "finalization_status_matches"]
