"""Exact-CAS persistence for admitted RedDog signed-worker executions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Mapping

from modules.infrastructure.database.src.signed_worker_result_ledger import (
    persist_result_history_ledger,
)


_TARGET_STATUSES = {"completed", "failed", "pending", "completed_reserved"}


def finalize_signed_worker_execution(
    db: Any,
    task_id: str,
    *,
    context: Mapping[str, Any],
    accepted: bool,
    result_context: Mapping[str, Any] | None = None,
    target_status: str | None = None,
    retry_not_before: str | None = None,
) -> bool:
    """Persist a result only for the exact admitted owner and context."""

    binding = _finalization_binding(
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
    )


def _finalization_binding(
    task_id: str, claim: Any, use: Any
) -> tuple[str, Mapping[str, Any], Mapping[str, Any]] | None:
    if not isinstance(claim, Mapping) or not isinstance(use, Mapping):
        return None
    expected_claim, expected_use = dict(claim), dict(use)
    assigned_to = str(expected_claim.get("assigned_to") or "")
    if (
        str(expected_claim.get("task_id") or "") != task_id
        or str(expected_use.get("task_id") or "") != task_id
        or str(expected_claim.get("status") or "") != "CLAIMED"
        or str(expected_use.get("status") or "") != "CONSUMED"
        or expected_use.get("claim_receipt_id") != expected_claim.get("receipt_id")
        or expected_use.get("token_digest") != expected_claim.get("token_digest")
        or not assigned_to
        or not _valid_receipt(expected_claim)
        or not _valid_receipt(expected_use)
    ):
        return None
    return assigned_to, expected_claim, expected_use


def _commit_final_state(
    database: Any, *, task_id: str, assigned_to: str,
    claim: Mapping[str, Any], use: Mapping[str, Any],
    result_context: Mapping[str, Any] | None,
    target_status: str, retry_not_before: str | None,
) -> bool:
    expected_status = "completed" if target_status == "completed_reserved" else "executing"
    persisted_status = "completed" if target_status == "completed_reserved" else target_status
    try:
        with database.get_connection() as connection:
            row = connection.execute(
                "SELECT status, assigned_to, assigned_at, completed_at, context "
                "FROM agents_autonomous_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            raw_context = _matching_context(
                row, assigned_to, claim, use, expected_status=expected_status
            )
            if raw_context is None:
                return False
            final_context = dict(result_context) if result_context is not None else json.loads(raw_context)
            if (
                final_context.get("signed_worker_execution_claim") != claim
                or final_context.get("signed_worker_execution_use") != use
            ):
                return False
            updated = _update_final_row(
                connection, row=dict(row), task_id=task_id,
                assigned_to=assigned_to, raw_context=raw_context,
                final_context=final_context, expected_status=expected_status,
                persisted_status=persisted_status,
                retry_not_before=retry_not_before,
            )
            if not updated:
                return False
            if not persist_result_history_ledger(
                connection,
                task_id,
                final_context,
                claim_receipt_id=str(claim.get("receipt_id") or ""),
                use_receipt_id=str(use.get("receipt_id") or ""),
            ):
                raise RuntimeError("signed_worker_result_ledger_rejected")
            return True
    except Exception:
        return False


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
    return raw_context if claim.get("context_digest") == _digest(stored) else None


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


def _valid_receipt(receipt: Mapping[str, Any]) -> bool:
    body = dict(receipt)
    receipt_id = str(body.pop("receipt_id", "") or "")
    return _is_digest(receipt_id) and receipt_id == _digest(body)


def _digest(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_digest(value: Any) -> bool:
    text = str(value or "").removeprefix("sha256:")
    return len(text) == 64 and all(char in "0123456789abcdef" for char in text)


__all__ = ["finalize_signed_worker_execution"]
