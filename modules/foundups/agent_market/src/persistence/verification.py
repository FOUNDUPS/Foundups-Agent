"""Atomic SQLite verification within the existing FAM persistence boundary.

This records a supplied decision; it does not confer verifier authority or judge
the artifact. Legacy ambiguous history requires separate reconciliation.
"""

from datetime import datetime, timezone

from sqlalchemy import text

from ..exceptions import InvalidStateTransitionError, NotFoundError, PermissionDeniedError, ValidationError
from ..models import TaskStatus, Verification
from .orm_models import ComputeLedgerEntryRow, EventRecordRow, FoundupRow, ProofRow, TaskRow, VerificationRow
from .sqlite_adapter import (
    _compute_decision, _debit_in_session,
    _payout_event_scopes as _event_scopes,
    _payout_reference_scopes as _reference_scopes,
    _payout_scope_requires_check as _scope_requires_check,
)


def _require(condition, message):
    if not condition:
        raise ValidationError(f"Verification history requires reconciliation: {message}")


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _utc(value):
    _require(isinstance(value, datetime), "invalid decision timestamp")
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _identity(sess, task, decision):
    _require(task is not None and sess.get(FoundupRow, task.foundup_id) is not None,
             "missing task or FoundUp")
    proof = sess.get(ProofRow, task.proof_id) if _text(task.proof_id) else None
    _require(proof is not None and proof.task_id == task.task_id
             and proof.submitter_id == task.assignee_id, "missing or unbound proof")
    _require(decision.task_id == task.task_id and type(decision.approved) is bool,
             "decision task or boolean mismatch")
    _require(all(_text(value) for value in (
        task.task_id, task.foundup_id, task.assignee_id, proof.proof_id,
        proof.artifact_uri, proof.artifact_hash, decision.verification_id,
        decision.verifier_id, decision.reason,
    )), "incomplete identity")
    return {
        "verification_version": 1, "verification_id": decision.verification_id,
        "foundup_id": task.foundup_id, "task_id": task.task_id, "proof_id": proof.proof_id,
        "verifier_id": decision.verifier_id, "approved": decision.approved,
        "reason": decision.reason, "verified_at": _utc(decision.verified_at).isoformat(),
        "proof_snapshot": {
            "submitter_id": proof.submitter_id, "artifact_uri": proof.artifact_uri,
            "artifact_hash": proof.artifact_hash, "notes": proof.notes,
            "submitted_at": proof.submitted_at.isoformat(),
        },
    }


def _verification_events(events, ledger):
    referenced = {row.event_id for row in ledger if row.reason == "verify_proof"}
    return [row for row in events.values() if row.event_id in referenced
            or row.event_type in ("proof.verified", "proof.rejected")
            or isinstance(row.payload, dict) and "verification_version" in row.payload]


def _validate_event(sess, event_row, ledger):
    payload = event_row.payload
    _require(isinstance(payload, dict), "invalid event payload")
    identity = payload.get("verification_id")
    decision = sess.get(VerificationRow, identity) if _text(identity) else None
    _require(decision is not None, "event missing decision")
    task = sess.get(TaskRow, decision.task_id)
    expected = _identity(sess, task, decision)
    cost = payload.get("required_credits")
    _require(type(cost) is int and cost >= 0 and type(payload.get("verification_version")) is int
             and type(payload.get("approved")) is bool, "invalid version, decision or cost")
    _require(payload == dict(expected, required_credits=cost), "changed or incomplete identity")
    _require(event_row.event_type == ("proof.verified" if decision.approved else "proof.rejected")
             and event_row.actor_id == decision.verifier_id and _text(event_row.event_id)
             and event_row.foundup_id == task.foundup_id and event_row.task_id == task.task_id
             and event_row.proof_id == task.proof_id and event_row.payout_id is None,
             "event scope or outcome mismatch")
    if decision.approved:
        _require(task.status == TaskStatus.VERIFIED and task.verification_id == identity,
                 "accepted task linkage mismatch")
    else:
        _require(task.verification_id != identity, "rejected decision approved task")
    debits = [row for row in ledger if row.event_id == event_row.event_id]
    _require(len(debits) == (1 if cost else 0), "debit cardinality mismatch")
    for debit in debits:
        _require(debit.actor_id == decision.verifier_id and debit.foundup_id == task.foundup_id
                 and debit.entry_type == "debit" and debit.reason == "verify_proof"
                 and debit.rail == "metered_execution" and debit.payment_ref is None
                 and type(debit.amount) is int and debit.amount == cost, "debit identity mismatch")
    return identity


def _validate_task_links(sess, foundup_id, checked):
    for task in sess.query(TaskRow).all():
        if task.verification_id is None and task.status not in (TaskStatus.VERIFIED, TaskStatus.PAID):
            continue
        scopes = [task.foundup_id] + _reference_scopes(sess, [(VerificationRow, task.verification_id)])
        if _scope_requires_check(sess, foundup_id, scopes):
            event_row = checked.get(task.verification_id)
            _require(event_row is not None and event_row.task_id == task.task_id
                     and event_row.payload["approved"] is True and task.status == TaskStatus.VERIFIED,
                     "task has unbound accepted decision")


def _history(sess, foundup_id):
    """Read complete relevant history; absence of scope is never unrelated."""
    all_events = {row.event_id: row for row in sess.query(EventRecordRow).all()}
    ledger = sess.query(ComputeLedgerEntryRow).all()
    events, checked = _verification_events(all_events, ledger), {}
    for event_row in events:
        scopes = _event_scopes(sess, event_row)
        scopes += [row.foundup_id for row in ledger if row.event_id == event_row.event_id]
        if _scope_requires_check(sess, foundup_id, scopes):
            identity = _validate_event(sess, event_row, ledger)
            _require(identity not in checked, "duplicate decision events")
            checked[identity] = event_row
    event_ids = {row.event_id for row in events}
    checked_ids = {row.event_id for row in checked.values()}
    for debit in ledger:
        if debit.reason != "verify_proof" and debit.event_id not in event_ids:
            continue
        event_row = all_events.get(debit.event_id)
        scopes = [debit.foundup_id]
        if debit.event_id is not None:
            scopes += _event_scopes(sess, event_row) if event_row is not None else [None]
        if _scope_requires_check(sess, foundup_id, scopes):
            _require(debit.event_id in checked_ids, "ambiguous legacy verification debit")
    for decision in sess.query(VerificationRow).all():
        scopes = _reference_scopes(sess, [(TaskRow, decision.task_id)])
        if _scope_requires_check(sess, foundup_id, scopes):
            _require(decision.verification_id in checked, "orphaned or legacy decision")
    _validate_task_links(sess, foundup_id, checked)
    return checked


def _stage(adapter, sess, task, decision, identity):
    access = _compute_decision(adapter, sess, decision.verifier_id, "proof.verify", task.foundup_id)
    if not access["allowed"]:
        raise PermissionDeniedError(str(access["reason"]))
    cost, event_id = access["required_credits"], adapter._next_id("evt")
    if cost:
        _debit_in_session(adapter, sess, decision.verifier_id, cost, "verify_proof", task.foundup_id, event_id)
    sess.add(VerificationRow(
        verification_id=decision.verification_id, task_id=task.task_id,
        verifier_id=decision.verifier_id, approved=decision.approved, reason=decision.reason,
        verified_at=_utc(decision.verified_at),
    ))
    if decision.approved:
        task.status, task.verification_id = TaskStatus.VERIFIED, decision.verification_id
    sess.add(EventRecordRow(
        event_id=event_id, event_type="proof.verified" if decision.approved else "proof.rejected",
        actor_id=decision.verifier_id, payload=dict(identity, required_credits=cost),
        foundup_id=task.foundup_id, task_id=task.task_id, proof_id=task.proof_id,
        timestamp=adapter._now_utc(),
    ))


def verify_proof_atomic(adapter, task_id, decision):
    """Record or replay one supplied decision; no external or domain authority."""
    if adapter.engine.dialect.name != "sqlite":
        raise ValidationError("Atomic proof verification supports SQLite only")
    _require(_text(task_id) and isinstance(decision, Verification), "invalid request")
    with adapter.session() as sess:
        sess.execute(text("BEGIN IMMEDIATE"))
        task = sess.get(TaskRow, task_id)
        if task is None:
            raise NotFoundError(f"Task not found: {task_id}")
        identity = _identity(sess, task, decision)
        checked = _history(sess, task.foundup_id)
        prior = checked.get(decision.verification_id)
        if prior is not None:
            _require(prior.payload == dict(identity, required_credits=prior.payload["required_credits"]),
                     "retry request identity changed")
        else:
            _require(sess.get(VerificationRow, decision.verification_id) is None,
                     "decision ID already belongs to another operation")
            if task.status != TaskStatus.SUBMITTED:
                raise InvalidStateTransitionError("Proof verification requires a submitted task")
            _require(task.verification_id is None and task.payout_id is None, "submitted task has later linkage")
            _stage(adapter, sess, task, decision, identity)
        result = adapter._row_to_task(task)
    if not decision.approved:
        raise ValidationError(f"Proof rejected: {decision.reason}")
    return result
