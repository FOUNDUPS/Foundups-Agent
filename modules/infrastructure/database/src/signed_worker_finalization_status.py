"""Cross-object terminal-state rules for signed-worker finalization."""

from __future__ import annotations

from typing import Any, Mapping


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


__all__ = ["finalization_status_matches"]
