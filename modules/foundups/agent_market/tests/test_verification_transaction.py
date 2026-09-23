"""Desired persistence-only verification acceptance; synthetic disposable fixtures."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from threading import Barrier
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, event, insert, select, update
from sqlalchemy.exc import InvalidRequestError

from modules.foundups.agent_market.src.exceptions import AgentMarketError, ValidationError
from modules.foundups.agent_market.src.persistence.sqlite_adapter import Base, SQLiteAdapter
from modules.foundups.agent_market.src.task_pipeline import PersistentTaskPipeline
from modules.foundups.agent_market.tests.test_persistent_compute_wiring import (
    _database_snapshot, _foundup, _rows, _submitted_verification, _verification_observation,
)


@pytest.fixture
def ready(tmp_path):
    adapter = SQLiteAdapter(tmp_path / "verification.db")
    try:
        task, decision = _submitted_verification(adapter, True)
        yield adapter, task, decision
    finally:
        adapter.close()


def _verify(adapter, task, decision):
    return PersistentTaskPipeline(adapter).verify_proof(task.task_id, decision)


def _unchanged_rejection(adapter, task, decision):
    before = _database_snapshot(adapter)
    with pytest.raises(AgentMarketError):
        _verify(adapter, task, decision)
    assert _database_snapshot(adapter) == before


@pytest.mark.parametrize("field,value", [
    ("task_id", "different"), ("verifier_id", "different"), ("approved", False),
    ("reason", "changed"), ("verified_at", datetime(2001, 1, 1, tzinfo=timezone.utc)),
])
def test_existing_id_rejects_changed_identity(ready, field, value):
    adapter, task, decision = ready
    _verify(adapter, task, decision)
    _unchanged_rejection(adapter, task, replace(decision, **{field: value}))


@pytest.mark.parametrize("naive", [False, True])
def test_equivalent_timestamp_survives_reopen(ready, naive):
    adapter, task, decision = ready
    utc = datetime(2026, 9, 23, 1, 2, 3, 456789, tzinfo=timezone.utc)
    decision.verified_at = utc.replace(tzinfo=None) if naive else utc.astimezone(timezone(timedelta(hours=9)))
    original = decision.verified_at
    _verify(adapter, task, decision)
    assert decision.verified_at == original
    stored = adapter.get_verification(decision.verification_id).verified_at
    assert stored.replace(tzinfo=timezone.utc) == utc
    before = _database_snapshot(adapter)
    adapter.close()
    reopened = SQLiteAdapter(adapter.db_path)
    try:
        assert _verify(reopened, task, replace(decision, verified_at=utc)).status.value == "verified"
        assert _database_snapshot(reopened) == before
    finally:
        reopened.close()


def test_accepted_retry_preserves_pending_payout(ready):
    adapter, task, decision = ready
    _verify(adapter, task, decision)
    adapter.activate_compute_plan("treasury_1", tier="builder", monthly_credit_allocation=20)
    payout = PersistentTaskPipeline(adapter).trigger_payout(task.task_id, "treasury_1")
    before = _database_snapshot(adapter)
    assert _verify(adapter, task, decision).payout_id == payout.payout_id
    assert _database_snapshot(adapter) == before


def test_old_rejection_replays_after_distinct_acceptance(ready):
    adapter, task, decision = ready
    rejection = replace(decision, approved=False)
    with pytest.raises(ValidationError, match="Proof rejected"):
        _verify(adapter, task, rejection)
    accepted = replace(decision, verification_id="accepted_second")
    _verify(adapter, task, accepted)
    before = _database_snapshot(adapter)
    with pytest.raises(ValidationError, match="Proof rejected"):
        _verify(adapter, task, rejection)
    assert _verify(adapter, task, accepted).verification_id == accepted.verification_id
    assert _database_snapshot(adapter) == before
    assert adapter.get_wallet("verifier_1")["credit_balance"] == 16


@pytest.mark.parametrize("cost", [0, 2])
def test_replay_uses_original_cost_without_current_plan(ready, cost):
    adapter, task, decision = ready
    adapter.compute_meter_costs["proof.verify"] = cost
    _verify(adapter, task, decision)
    events = adapter.query_events(task_id=task.task_id, event_type="proof.verified")
    assert len(events) == 1 and events[0].payload["required_credits"] == cost
    assert events[0].proof_id == task.proof_id
    ledger = [r for r in adapter.list_compute_ledger("verifier_1") if r["entry_type"] == "debit"]
    assert len(ledger) == (1 if cost else 0)
    assert all(r["event_id"] == events[0].event_id for r in ledger)
    with adapter.engine.begin() as conn:
        conn.execute(delete(Base.metadata.tables["compute_plans"]))
    adapter.compute_meter_costs["proof.verify"] = 99
    before = _database_snapshot(adapter)
    _verify(adapter, task, decision)
    assert _database_snapshot(adapter) == before


@pytest.mark.parametrize("corruption", [
    "event_missing", "event_duplicate", "event_actor", "event_scope", "event_type",
    "cost", "debit_missing", "extra_debit", "debit_scope", "proof_hash", "decision_reason",
])
def test_durable_operation_corruption_fails_without_effects(ready, corruption):
    adapter, task, decision = ready
    _verify(adapter, task, decision)
    event_row = adapter.query_events(task_id=task.task_id, event_type="proof.verified")[0]
    events, ledger = (Base.metadata.tables[n] for n in ("event_records", "compute_ledger_entries"))
    with adapter.engine.begin() as conn:
        if corruption == "event_missing":
            conn.execute(delete(events).where(events.c.event_id == event_row.event_id))
        elif corruption == "event_duplicate":
            row = dict(conn.execute(select(events)).mappings().one())
            conn.execute(insert(events), dict(row, event_id="duplicate"))
        elif corruption in ("event_actor", "event_scope", "event_type"):
            field = {"event_actor": "actor_id", "event_scope": "foundup_id", "event_type": "event_type"}[corruption]
            conn.execute(update(events).values(**{field: "changed"}))
        elif corruption == "cost":
            conn.execute(update(events).values(payload=dict(event_row.payload, required_credits=99)))
        elif corruption == "debit_missing":
            conn.execute(delete(ledger).where(ledger.c.entry_type == "debit"))
        elif corruption == "extra_debit":
            row = dict(conn.execute(select(ledger).where(ledger.c.entry_type == "debit")).mappings().one())
            conn.execute(insert(ledger), dict(row, entry_id="extra"))
        elif corruption == "debit_scope":
            conn.execute(update(ledger).where(ledger.c.entry_type == "debit").values(foundup_id=None))
        elif corruption == "proof_hash":
            conn.execute(update(Base.metadata.tables["proofs"]).values(artifact_hash="changed"))
        else:
            conn.execute(update(Base.metadata.tables["verifications"]).values(reason="changed"))
    _unchanged_rejection(adapter, task, decision)


@pytest.mark.parametrize("scope", ["f_1", None, "missing"])
def test_legacy_debit_without_operation_identity_holds(ready, scope):
    adapter, task, decision = ready
    adapter.activate_compute_plan("different_actor", tier="builder", monthly_credit_allocation=20)
    adapter.debit_credits("different_actor", 2, reason="verify_proof", foundup_id=scope)
    # Put residue beyond the public ledger's 100-row window.
    for index in range(101):
        adapter.rebate_credits("different_actor", 1, reason=f"later_{index}")
    _unchanged_rejection(adapter, task, decision)


def test_explicitly_unrelated_legacy_foundup_does_not_block(ready):
    adapter, task, decision = ready
    other = _foundup("other_foundup"); other.token_symbol = "OTHER"
    adapter.create_foundup(other)
    adapter.debit_credits("verifier_1", 2, reason="verify_proof", foundup_id=other.foundup_id)
    assert _verify(adapter, task, decision).status.value == "verified"


@pytest.mark.parametrize("residue", ["decision", "legacy_event", "proof_missing", "proof_wrong_task", "task_pointer", "no_plan"])
def test_partial_history_or_missing_prerequisite_holds(ready, residue):
    adapter, task, decision = ready
    if residue == "decision":
        adapter.create_verification(decision)
    else:
        with adapter.engine.begin() as conn:
            if residue == "legacy_event":
                conn.execute(insert(Base.metadata.tables["event_records"]), dict(
                    event_id="legacy", event_type="proof.verified", actor_id=decision.verifier_id,
                    payload={"reason": decision.reason, "approved": True}, foundup_id=task.foundup_id,
                    task_id=task.task_id, timestamp=decision.verified_at))
            elif residue == "proof_missing":
                conn.execute(delete(Base.metadata.tables["proofs"]))
            elif residue == "proof_wrong_task":
                conn.execute(update(Base.metadata.tables["proofs"]).values(task_id="missing"))
            elif residue == "task_pointer":
                conn.execute(update(Base.metadata.tables["tasks"]).values(verification_id="missing"))
            else:
                conn.execute(delete(Base.metadata.tables["compute_plans"]))
    _unchanged_rejection(adapter, task, decision)


def test_non_sqlite_rejects_before_session_or_compute():
    class Unsupported:
        engine = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
        def __getattr__(self, name):
            pytest.fail(f"unsupported backend reached {name}")
    with pytest.raises(ValidationError, match="SQLite"):
        PersistentTaskPipeline(Unsupported()).verify_proof("task", None)


@pytest.mark.parametrize("approved", [False, True])
def test_same_id_competing_adapters_have_one_effect(ready, approved):
    adapter, task, decision = ready
    decision.approved = approved
    second = SQLiteAdapter(adapter.db_path)
    second.compute_access_enforced = True
    second.compute_meter_costs["proof.verify"] = 2
    barrier = Barrier(2)
    def invoke(owner):
        barrier.wait(timeout=10)
        with pytest.raises(ValidationError, match="Proof rejected") if not approved else nullcontext():
            _verify(owner, task, decision)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(invoke, (adapter, second)))
        assert len(_rows(adapter, "verifications")) == len(_rows(adapter, "event_records")) == 1
        assert adapter.get_wallet("verifier_1")["credit_balance"] == 18
    finally:
        second.close()


def test_lost_response_after_verification_commit_replays(ready):
    adapter, task, decision = ready
    staged, committed = [], []
    def mark(conn, cursor, statement, parameters, context, executemany):
        if statement.lower().startswith("insert into verifications"):
            staged.append(True)
    def lose_response(session):
        if staged and not committed:
            committed.append(True)
            raise RuntimeError("lost verification response")
    event.listen(adapter.engine, "after_cursor_execute", mark)
    event.listen(adapter._SessionFactory, "after_commit", lose_response)
    try:
        with pytest.raises((RuntimeError, InvalidRequestError)):
            _verify(adapter, task, decision)
    finally:
        event.remove(adapter.engine, "after_cursor_execute", mark)
        event.remove(adapter._SessionFactory, "after_commit", lose_response)
    assert staged == committed == [True]
    assert _verification_observation(adapter, task, decision) == ("verified", True, 1, 1, 18, 1)
    before = _database_snapshot(adapter)
    adapter.close()
    reopened = SQLiteAdapter(adapter.db_path)
    try:
        assert _verify(reopened, task, decision).status.value == "verified"
        assert _database_snapshot(reopened) == before
        assert reopened.get_wallet("verifier_1")["credit_balance"] == 18
    finally:
        reopened.close()
