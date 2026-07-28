"""Fail-closed recovery for expired signed-worker execution leases."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
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
    finalize_expired_signed_worker_execution_recovery,
)
from modules.infrastructure.database.src.signed_worker_execution_lease import (
    execution_lease_state,
)
from modules.infrastructure.database.src.signed_worker_execution_quarantine import (
    quarantine_signed_worker_execution,
)
from modules.infrastructure.database.src.signed_worker_finalization_status import (
    durable_terminal_state_matches,
)
from modules.infrastructure.database.src.signed_worker_assignment import (
    SIGNED_WORKER_ASSIGNMENT_LEASE_SECONDS,
    signed_worker_assignment_matches,
)


_POSITIVE_ASSURANCE = frozenset({"ACCEPT", "VERIFIED"})
ASSIGNMENT_LEASE_SECONDS = SIGNED_WORKER_ASSIGNMENT_LEASE_SECONDS


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
        return _recovery_payload(rejected=["database_scan_failed"])
    recovered: list[str] = []
    rejected: list[str] = []
    quarantined: list[str] = []
    assignment_recovery = _recover_stale_assignments(
        db, now=now.astimezone(timezone.utc)
    )
    if assignment_recovery is None:
        return _recovery_payload(rejected=["assigned_task_scan_failed"])
    requeued, assigned_quarantined, assigned_rejected = assignment_recovery
    quarantined.extend(assigned_quarantined)
    rejected.extend(assigned_rejected)
    for row in rows:
        task_id = str(row.get("task_id") or "")
        outcome = _recover_one(
            db,
            task_id=task_id,
            raw_context=row.get("context"),
            now=now.astimezone(timezone.utc),
        )
        if outcome == "RECOVERED":
            recovered.append(task_id)
        elif outcome == "QUARANTINED":
            quarantined.append(task_id)
        elif outcome == "REJECTED":
            rejected.append(task_id)
    return _recovery_payload(
        recovered=recovered,
        rejected=rejected,
        quarantined=quarantined,
        requeued=requeued,
    )


def _recovery_payload(
    *,
    recovered: list[str] | None = None,
    rejected: list[str] | None = None,
    quarantined: list[str] | None = None,
    requeued: list[str] | None = None,
) -> Mapping[str, Any]:
    rejected = rejected or []
    return {
        "accepted": not rejected,
        "recovered_task_ids": recovered or [],
        "rejected_task_ids": rejected,
        "quarantined_task_ids": quarantined or [],
        "requeued_assigned_task_ids": requeued or [],
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
) -> str:
    context = _context(raw_context)
    lease_state, assigned_to = _lease_state(
        db,
        context,
        task_id=task_id,
        now=now,
    )
    if lease_state == "ACTIVE":
        return "SKIPPED"
    if lease_state != "EXPIRED":
        return _quarantine_task(
            db,
            task_id=task_id,
            raw_context=raw_context,
            now=now,
            reason="invalid_execution_lease",
        )
    completion, completion_state = _recovery_completion(
        db,
        task_id=task_id,
        assigned_to=assigned_to,
    )
    if completion_state != "RECOVERABLE":
        return _quarantine_task(
            db,
            task_id=task_id,
            raw_context=raw_context,
            now=now,
            reason=f"assurance_{completion_state.lower()}",
        )
    receipt = _lease_expiry_receipt(context, completion=completion)
    final_context = append_signed_worker_result_history(context, receipt)
    if finalize_expired_signed_worker_execution_recovery(
        db,
        task_id,
        context=context,
        result_context=final_context,
        recovery_now=now,
        assurance_completion=completion,
    ):
        return "RECOVERED"
    return _resolve_raced_finalization(
        db,
        task_id=task_id,
        now=now,
    )


def _recover_stale_assignments(
    db: Any,
    *,
    now: datetime,
) -> tuple[list[str], list[str], list[str]] | None:
    try:
        with db.db.get_connection() as connection:
            rows = connection.execute(
                "SELECT task_id, assigned_to, assigned_at, context "
                "FROM agents_autonomous_tasks WHERE status = 'assigned' "
                "AND task_id LIKE ? ORDER BY assigned_at ASC LIMIT 50",
                (f"{SIGNED_WORKER_TASK_PREFIX}%",),
            ).fetchall()
    except Exception:
        return None
    requeued: list[str] = []
    quarantined: list[str] = []
    rejected: list[str] = []
    for row in rows:
        payload = dict(row)
        if _assigned_not_expired(payload, now=now):
            continue
        task_id = str(payload.get("task_id") or "")
        context = _context(payload.get("context"))
        assigned_to = str(payload.get("assigned_to") or "")
        if not signed_worker_assignment_matches(task_id, assigned_to, context):
            outcome = _quarantine_task(
                db,
                task_id=task_id,
                raw_context=payload.get("context"),
                now=now,
                reason="invalid_signed_assignment",
                expected_status="assigned",
            )
            if outcome == "QUARANTINED":
                quarantined.append(task_id)
            elif outcome == "REJECTED":
                rejected.append(task_id)
            continue
        if _active_verifier_reservation(db, task_id):
            continue
        if _requeue_assignment(
            db,
            task_id=task_id,
            assigned_to=assigned_to,
            raw_context=str(payload.get("context") or ""),
        ):
            requeued.append(task_id)
    return requeued, quarantined, rejected


def _assigned_not_expired(
    row: Mapping[str, Any],
    *,
    now: datetime,
) -> bool:
    assigned_at = _parse_utc(row.get("assigned_at"))
    return (
        assigned_at is not None
        and now < assigned_at + timedelta(seconds=ASSIGNMENT_LEASE_SECONDS)
    )


def _active_verifier_reservation(db: Any, task_id: str) -> bool:
    try:
        durable = db.get_independent_assurance_reservation_for_task(
            task_id,
            task_kind="verifier",
        )
    except Exception:
        return True
    reservation = (
        durable.get("reservation")
        if isinstance(durable, Mapping)
        else None
    )
    return (
        isinstance(reservation, Mapping)
        and str(reservation.get("status") or "") == "RESERVED"
    )


def _requeue_assignment(
    db: Any,
    *,
    task_id: str,
    assigned_to: str,
    raw_context: str,
) -> bool:
    try:
        changed = db.db.execute_write(
            "UPDATE agents_autonomous_tasks SET status = 'pending', "
            "assigned_to = NULL, assigned_at = NULL "
            "WHERE task_id = ? AND status = 'assigned' "
            "AND assigned_to = ? AND context = ?",
            (task_id, assigned_to, raw_context),
        )
    except Exception:
        return False
    return changed == 1


def _quarantine_task(
    db: Any,
    *,
    task_id: str,
    raw_context: Any,
    now: datetime,
    reason: str,
    expected_status: str = "executing",
) -> str:
    return quarantine_signed_worker_execution(
        db,
        task_id=task_id,
        raw_context=raw_context,
        expected_status=expected_status,
        reason=reason,
        now_iso=now.isoformat(),
    )


def _lease_state(
    db: Any,
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
    assigned_to, _, _ = binding
    return (
        execution_lease_state(
            db,
            task_id=task_id,
            context=context,
            now=now,
        ),
        assigned_to,
    )


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
    if durable and not staged_present:
        return None, "MISSING"
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


def _resolve_raced_finalization(
    db: Any,
    *,
    task_id: str,
    now: datetime,
) -> str:
    """Accept only durable terminal state; quarantine an exact forged race."""

    row = _current_task_row(db, task_id)
    if row is None:
        return "REJECTED"
    context = _context(row.get("context"))
    status = str(row.get("status") or "")
    receipt = context.get("signed_worker_task_last_result")
    decision = (
        str(receipt.get("decision") or "")
        if isinstance(receipt, Mapping)
        else ""
    )
    if _durable_terminal_row_matches(
        db,
        task_id=task_id,
        row=row,
        context=context,
        status=status,
        decision=decision,
    ):
        if status == "failed" and decision == "EXECUTION_LEASE_RECOVERED":
            return "RECOVERED"
        return "SKIPPED"
    if status == "assigned" and signed_worker_assignment_matches(
        task_id,
        str(row.get("assigned_to") or ""),
        context,
    ):
        return "SKIPPED"
    return _quarantine_task(
        db,
        task_id=task_id,
        raw_context=row.get("context"),
        now=now,
        reason="terminal_result_not_persisted",
        expected_status=status,
    )


def _current_task_row(db: Any, task_id: str) -> dict[str, Any] | None:
    try:
        with db.db.get_connection() as connection:
            row = connection.execute(
                "SELECT status, assigned_to, context "
                "FROM agents_autonomous_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
    except Exception:
        return None
    return dict(row) if row is not None else None


def _durable_terminal_row_matches(
    db: Any,
    *,
    task_id: str,
    row: Mapping[str, Any],
    context: Mapping[str, Any],
    status: str,
    decision: str,
) -> bool:
    try:
        with db.db.get_connection() as connection:
            return durable_terminal_state_matches(
                connection,
                task_id=task_id,
                task={**dict(row), "context": dict(context)},
                target_status=status,
                decision=decision,
            )
    except Exception:
        return False


def _context(raw: Any) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return dict(raw)
    try:
        parsed = json.loads(str(raw or ""))
    except (TypeError, ValueError):
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


def _parse_utc(value: Any) -> datetime | None:
    text = str(value or "").replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


__all__ = ["recover_expired_signed_worker_executions"]
