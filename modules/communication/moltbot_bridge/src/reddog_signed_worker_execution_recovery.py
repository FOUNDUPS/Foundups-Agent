"""Fail-closed recovery for expired signed-worker execution leases."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_signed_worker_result_receipt import (
    DIRECT_REJECT,
    append_signed_worker_result_history,
    build_signed_worker_task_result_receipt,
)
from modules.infrastructure.database.src.signed_worker_assurance_staging import (
    rehydrate_staged_assurance_completion,
)
from modules.infrastructure.database.src.signed_worker_execution_binding import (
    finalization_binding,
)
from modules.infrastructure.database.src.signed_worker_execution_store import (
    SIGNED_WORKER_TASK_PREFIX,
    finalize_signed_worker_execution,
)
from modules.infrastructure.database.src.signed_worker_assurance_request import (
    parse_utc,
)


_POSITIVE_ASSURANCE = frozenset({"ACCEPT", "VERIFIED"})


def recover_expired_signed_worker_executions(
    db: Any,
    *,
    now_factory: Callable[[], datetime] | None = None,
    limit: int = 50,
) -> Mapping[str, Any]:
    """Terminalize expired claims without replaying an unknown worker effect."""

    now = (now_factory or (lambda: datetime.now(timezone.utc)))()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    rows = _executing_rows(db, limit=max(1, min(int(limit), 50)))
    if rows is None:
        return {
            "accepted": False,
            "recovered_task_ids": [],
            "rejected_task_ids": ["database_scan_failed"],
            "no_worker_effect_replayed": True,
        }
    recovered: list[str] = []
    rejected: list[str] = []
    for row in rows:
        task_id = str(row.get("task_id") or "")
        outcome = _recover_one(
            db,
            task_id=task_id,
            raw_context=row.get("context"),
            now=now.astimezone(timezone.utc),
        )
        if outcome is True:
            recovered.append(task_id)
        elif outcome is False:
            rejected.append(task_id)
    return {
        "accepted": not rejected,
        "recovered_task_ids": recovered,
        "rejected_task_ids": rejected,
        "no_worker_effect_replayed": True,
    }


def _executing_rows(
    db: Any,
    *,
    limit: int,
) -> list[dict[str, Any]] | None:
    try:
        with db.db.get_connection() as connection:
            rows = connection.execute(
                "SELECT task_id, context FROM agents_autonomous_tasks "
                "WHERE status = 'executing' AND task_id LIKE ? "
                "ORDER BY assigned_at ASC LIMIT ?",
                (f"{SIGNED_WORKER_TASK_PREFIX}%", limit),
            ).fetchall()
    except Exception:
        return None
    return [dict(row) for row in rows]


def _recover_one(
    db: Any,
    *,
    task_id: str,
    raw_context: Any,
    now: datetime,
) -> bool | None:
    context = _context(raw_context)
    lease_state, assigned_to = _lease_state(
        context,
        task_id=task_id,
        now=now,
    )
    if lease_state == "ACTIVE":
        return None
    if lease_state != "EXPIRED":
        return False
    completion, completion_state = _recovery_completion(
        db,
        task_id=task_id,
        assigned_to=assigned_to,
    )
    if completion_state != "RECOVERABLE":
        return False
    receipt = _lease_expiry_receipt(context, completion=completion)
    final_context = append_signed_worker_result_history(context, receipt)
    if finalize_signed_worker_execution(
        db,
        task_id,
        context=context,
        accepted=False,
        result_context=final_context,
        assurance_completion=completion,
    ):
        return True
    if _already_recovered(db, task_id):
        return True
    return _revoke_unfinished_verifier(db, task_id=task_id, now=now)


def _lease_state(
    context: Mapping[str, Any],
    *,
    task_id: str,
    now: datetime,
) -> tuple[str, str]:
    binding = finalization_binding(
        task_id,
        context.get("signed_worker_execution_claim"),
        context.get("signed_worker_execution_use"),
    )
    if binding is None:
        return "INVALID", ""
    assigned_to, claim, use = binding
    claimed_at = parse_utc(str(claim.get("claimed_at") or ""))
    lease_expires_at = parse_utc(str(claim.get("lease_expires_at") or ""))
    consumed_at = parse_utc(str(use.get("consumed_at") or ""))
    if (
        claimed_at is None
        or lease_expires_at is None
        or consumed_at is None
        or not (claimed_at <= consumed_at < lease_expires_at)
    ):
        return "INVALID", ""
    if now < lease_expires_at:
        return "ACTIVE", assigned_to
    return "EXPIRED", assigned_to


def _recovery_completion(
    db: Any,
    *,
    task_id: str,
    assigned_to: str,
) -> tuple[dict[str, str] | None, str]:
    durable = _durable_verifier_reservation(db, task_id)
    staged_present = bool(
        durable
        and (
            durable.get("staged_completion_json")
            or durable.get("staged_completion_digest")
        )
    )
    completion = rehydrate_staged_assurance_completion(
        db.db,
        task_id=task_id,
        assigned_to=assigned_to,
    )
    if staged_present and completion is None:
        return None, "INVALID"
    if completion and completion.get("terminal_status") in _POSITIVE_ASSURANCE:
        return None, "POSITIVE_UNVERIFIED"
    return completion, "RECOVERABLE"


def _lease_expiry_receipt(
    context: Mapping[str, Any],
    *,
    completion: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    return build_signed_worker_task_result_receipt(
        base_context=context,
        claim_status=DIRECT_REJECT,
        result={
            "accepted": False,
            "decision": "EXECUTION_LEASE_RECOVERED",
            "receipt_id": "",
            "effect_commit_state": "INDETERMINATE",
            "rejection_reasons": ["signed_worker_execution_lease_expired"],
        },
        assurance_completion=completion,
    )


def _revoke_unfinished_verifier(
    db: Any,
    *,
    task_id: str,
    now: datetime,
) -> bool:
    durable = db.get_independent_assurance_reservation_for_task(
        task_id,
        task_kind="verifier",
    )
    reservation = (
        durable.get("reservation")
        if isinstance(durable, Mapping)
        else None
    )
    if (
        not isinstance(reservation, Mapping)
        or str(reservation.get("status") or "") != "RESERVED"
    ):
        return False
    result = db.revoke_independent_assurance(
        str(reservation.get("reservation_id") or ""),
        reason="signed_worker_execution_lease_expired",
        now_iso=now.isoformat(),
    )
    return result.get("accepted") is True


def _durable_verifier_reservation(
    db: Any,
    task_id: str,
) -> Mapping[str, Any] | None:
    durable = db.get_independent_assurance_reservation_for_task(
        task_id,
        task_kind="verifier",
    )
    reservation = (
        durable.get("reservation")
        if isinstance(durable, Mapping)
        else None
    )
    return reservation if isinstance(reservation, Mapping) else None


def _already_recovered(db: Any, task_id: str) -> bool:
    try:
        task = db.get_autonomous_task_by_id(task_id)
    except Exception:
        return False
    if not isinstance(task, Mapping):
        return False
    context = task.get("context")
    context = dict(context) if isinstance(context, Mapping) else {}
    receipt = context.get("signed_worker_task_last_result")
    receipt = dict(receipt) if isinstance(receipt, Mapping) else {}
    return (
        task.get("status") == "failed"
        and receipt.get("decision") == "EXECUTION_LEASE_RECOVERED"
    )


def _context(raw: Any) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return dict(raw)
    try:
        parsed = json.loads(str(raw or ""))
    except (TypeError, ValueError):
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


__all__ = ["recover_expired_signed_worker_executions"]
