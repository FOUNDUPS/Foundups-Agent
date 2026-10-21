"""Tests for compute access wiring in persistent service layer."""

from __future__ import annotations

import tempfile
from contextlib import nullcontext
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier

import pytest
from sqlalchemy import delete, event, insert, select, update
from sqlalchemy.exc import IntegrityError, InvalidRequestError, OperationalError

from modules.foundups.agent_market.src.exceptions import (
    AgentMarketError, InvalidStateTransitionError, PermissionDeniedError, ValidationError,
)
from modules.foundups.agent_market.src.models import (
    EventRecord, Foundup, Payout, PayoutStatus, Proof, Task, TaskStatus, Verification,
)
from modules.foundups.agent_market.src.persistence.sqlite_adapter import Base, SQLiteAdapter
from modules.foundups.agent_market.src.registry import PersistentFoundupRegistry
from modules.foundups.agent_market.src.task_pipeline import PersistentTaskPipeline


@pytest.fixture
def adapter():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "persistent_compute.db"
        adapter = SQLiteAdapter(db_path)
        yield adapter
        adapter.close()


def _foundup(foundup_id: str = "f_1", owner_id: str = "owner_1") -> Foundup:
    return Foundup(
        foundup_id=foundup_id,
        name="persistent compute foundup",
        owner_id=owner_id,
        token_symbol="FUP",
        immutable_metadata={"launch_model": "tokenized"},
        mutable_metadata={},
    )


def test_registry_enforces_compute_access(adapter):
    adapter.compute_access_enforced = True
    registry = PersistentFoundupRegistry(adapter)
    with pytest.raises(PermissionDeniedError):
        registry.create_foundup(_foundup())


def test_registry_debits_launch_when_plan_active(adapter):
    adapter.compute_access_enforced = True
    adapter.activate_compute_plan("owner_1", tier="builder", monthly_credit_allocation=20)
    registry = PersistentFoundupRegistry(adapter)

    registry.create_foundup(_foundup())
    wallet = adapter.get_wallet("owner_1")
    assert wallet["credit_balance"] == 10

    ledger = adapter.list_compute_ledger("owner_1")
    assert any(entry["entry_type"] == "debit" and entry["reason"] == "create_foundup" for entry in ledger)


def test_task_pipeline_enforces_and_debits_each_step(adapter):
    adapter.compute_access_enforced = True
    for actor in ("owner_1", "agent_1", "verifier_1", "treasury_1"):
        adapter.activate_compute_plan(actor, tier="builder", monthly_credit_allocation=20)

    registry = PersistentFoundupRegistry(adapter)
    pipeline = PersistentTaskPipeline(adapter)
    registry.create_foundup(_foundup())

    task = Task(
        task_id="task_1",
        foundup_id="f_1",
        title="build compute gate",
        description="wire compute gating",
        acceptance_criteria=["gate", "tests"],
        reward_amount=100,
        creator_id="owner_1",
    )
    pipeline.create_task(task)
    pipeline.claim_task(task.task_id, "agent_1")
    pipeline.submit_proof(
        Proof(
            proof_id="proof_1",
            task_id=task.task_id,
            submitter_id="agent_1",
            artifact_uri="ipfs://proof",
            artifact_hash="sha256:abc",
        )
    )
    pipeline.verify_proof(
        task.task_id,
        Verification(
            verification_id="ver_1",
            task_id=task.task_id,
            verifier_id="verifier_1",
            approved=True,
            reason="looks good",
        ),
    )
    pipeline.trigger_payout(task.task_id, actor_id="treasury_1")

    owner_wallet = adapter.get_wallet("owner_1")
    agent_wallet = adapter.get_wallet("agent_1")
    verifier_wallet = adapter.get_wallet("verifier_1")
    treasury_wallet = adapter.get_wallet("treasury_1")

    assert owner_wallet["credit_balance"] == 8  # 20 - launch(10) - task.create(2)
    assert agent_wallet["credit_balance"] == 17  # 20 - claim(1) - submit(2)
    assert verifier_wallet["credit_balance"] == 18  # 20 - verify(2)
    assert treasury_wallet["credit_balance"] == 19  # 20 - payout(1)


def _ready_payout(adapter, suffix="1", *, fund=True):
    adapter.compute_access_enforced = True
    adapter.compute_default_credits = 0
    foundup = _foundup(f"f_{suffix}")
    foundup.token_symbol = f"FUP{suffix}"
    adapter.create_foundup(foundup)
    task = Task(
        task_id=f"task_{suffix}", foundup_id=f"f_{suffix}", title="bounded task",
        description="disposable initiation", acceptance_criteria=["audited"],
        reward_amount=100, creator_id="owner_1", status=TaskStatus.VERIFIED,
        assignee_id="agent_1", proof_id=f"proof_{suffix}", verification_id=f"ver_{suffix}",
    )
    adapter.create_task(task)
    adapter.create_proof(Proof(
        proof_id=task.proof_id, task_id=task.task_id, submitter_id="agent_1",
        artifact_uri="memory://synthetic-proof", artifact_hash="sha256:synthetic",
    ))
    adapter.create_verification(Verification(
        verification_id=task.verification_id, task_id=task.task_id,
        verifier_id="verifier_1", approved=True, reason="fixture approval only",
    ))
    if fund:
        adapter.activate_compute_plan("treasury_1", tier="builder", monthly_credit_allocation=20)
    return PersistentTaskPipeline(adapter), task


def _rows(adapter, name):
    table = Base.metadata.tables[name]
    with adapter.engine.connect() as conn:
        return [dict(row) for row in conn.execute(
            select(table).order_by(*table.primary_key.columns)
        ).mappings()]


def _database_snapshot(adapter):
    return {name: _rows(adapter, name) for name in sorted(Base.metadata.tables)}


def _change_row(adapter, table_name, key, value, **changes):
    table = Base.metadata.tables[table_name]
    with adapter.engine.begin() as conn:
        conn.execute(update(table).where(table.c[key] == value).values(**changes))


def _assert_initiation(adapter, task, payout, *, cost=1):
    current = adapter.get_task(task.task_id)
    assert current.status is TaskStatus.VERIFIED
    assert current.payout_id == payout.payout_id
    assert payout.status is PayoutStatus.INITIATED
    assert payout.reference is None and payout.paid_at is None
    assert (payout.task_id, payout.recipient_id, payout.amount) == (
        task.task_id, task.assignee_id, task.reward_amount,
    )
    events = adapter.query_events(task_id=task.task_id, event_type="payout.initiated")
    assert len(events) == 1
    recorded = events[0]
    assert (recorded.actor_id, recorded.foundup_id, recorded.proof_id, recorded.payout_id) == (
        "treasury_1", task.foundup_id, task.proof_id, payout.payout_id,
    )
    expected = {"payout_id": payout.payout_id, "amount": task.reward_amount,
                "task_id": task.task_id, "foundup_id": task.foundup_id,
                "proof_id": task.proof_id, "verification_id": task.verification_id,
                "recipient_id": task.assignee_id, "required_credits": cost}
    assert all(recorded.payload.get(key) == value for key, value in expected.items())
    linked = [row for row in _rows(adapter, "compute_ledger_entries")
              if row["event_id"] == recorded.event_id]
    assert len(linked) == (1 if cost else 0)
    if cost:
        assert (linked[0]["actor_id"], linked[0]["foundup_id"], linked[0]["entry_type"],
                linked[0]["reason"], linked[0]["amount"]) == (
                    "treasury_1", task.foundup_id, "debit", "trigger_payout", cost)
    assert not adapter.query_events(task_id=task.task_id, event_type="payout.completed")


@pytest.mark.parametrize("enforced", [True, False])
def test_initiation_is_pending_and_disabled_enforcement_still_charges(adapter, enforced):
    pipeline, task = _ready_payout(adapter)
    adapter.compute_access_enforced = enforced
    payout = pipeline.trigger_payout(task.task_id, "treasury_1")
    _assert_initiation(adapter, task, payout)
    assert adapter.get_wallet("treasury_1")["credit_balance"] == 19


def test_exact_retry_and_reopen_return_same_initiation_without_writes(adapter):
    pipeline, task = _ready_payout(adapter)
    first = pipeline.trigger_payout(task.task_id, "treasury_1")
    before = _database_snapshot(adapter)
    assert pipeline.trigger_payout(task.task_id, "treasury_1") == first
    assert _database_snapshot(adapter) == before
    reopened = SQLiteAdapter(adapter.db_path)
    try:
        assert PersistentTaskPipeline(reopened).trigger_payout(task.task_id, "treasury_1") == first
        _assert_initiation(reopened, task, first)
        assert _database_snapshot(reopened) == before
    finally:
        reopened.close()


@pytest.mark.parametrize("cost", [0, 1])
def test_committed_retry_uses_cost_snapshot_not_current_policy(adapter, cost):
    pipeline, task = _ready_payout(adapter)
    adapter.compute_meter_costs["payout.trigger"] = cost
    first = pipeline.trigger_payout(task.task_id, "treasury_1")
    _assert_initiation(adapter, task, first, cost=cost)
    adapter.compute_meter_costs["payout.trigger"] = 99
    _change_row(adapter, "compute_plans", "actor_id", "treasury_1", status="inactive")
    _change_row(adapter, "compute_wallets", "actor_id", "treasury_1", credit_balance=0)
    before = _database_snapshot(adapter)
    assert pipeline.trigger_payout(task.task_id, "treasury_1") == first
    assert _database_snapshot(adapter) == before


def test_changed_retry_actor_rejects_without_charge(adapter):
    pipeline, task = _ready_payout(adapter)
    pipeline.trigger_payout(task.task_id, "treasury_1")
    adapter.activate_compute_plan("other_actor", tier="builder", monthly_credit_allocation=20)
    before = _database_snapshot(adapter)
    with pytest.raises(AgentMarketError):
        pipeline.trigger_payout(task.task_id, "other_actor")
    assert _database_snapshot(adapter) == before


@pytest.mark.parametrize("table,key,field,value", [
    ("tasks", "task_id", "reward_amount", 101),
    ("tasks", "task_id", "assignee_id", "other_agent"),
    ("tasks", "task_id", "foundup_id", "other_foundup"),
    ("proofs", "proof_id", "artifact_hash", "sha256:substituted"),
    ("proofs", "proof_id", "submitter_id", "other_agent"),
    ("verifications", "verification_id", "approved", False),
    ("verifications", "verification_id", "verifier_id", "other_verifier"),
])
def test_retry_rejects_mutated_persisted_lineage(adapter, table, key, field, value):
    pipeline, task = _ready_payout(adapter)
    pipeline.trigger_payout(task.task_id, "treasury_1")
    _change_row(adapter, table, key, getattr(task, key), **{field: value})
    before = _database_snapshot(adapter)
    with pytest.raises(AgentMarketError):
        pipeline.trigger_payout(task.task_id, "treasury_1")
    assert _database_snapshot(adapter) == before


@pytest.mark.parametrize("table,key,field,value", [
    ("tasks", "task_id", "assignee_id", None),
    ("tasks", "task_id", "status", TaskStatus.SUBMITTED),
    ("tasks", "task_id", "proof_id", "missing"),
    ("tasks", "task_id", "verification_id", "missing"),
    ("proofs", "proof_id", "task_id", "other_task"),
    ("proofs", "proof_id", "submitter_id", "other_agent"),
    ("verifications", "verification_id", "task_id", "other_task"),
    ("verifications", "verification_id", "approved", False),
])
def test_invalid_initial_lineage_rejects_before_writes(adapter, table, key, field, value):
    pipeline, task = _ready_payout(adapter)
    _change_row(adapter, table, key, getattr(task, key), **{field: value})
    before = _database_snapshot(adapter)
    with pytest.raises(AgentMarketError):
        pipeline.trigger_payout(task.task_id, "treasury_1")
    assert _database_snapshot(adapter) == before


@pytest.mark.parametrize("statement_start", [
    "insert into compute_ledger_entries", "insert into payouts",
    "insert into event_records", "update tasks",
])
def test_every_initiation_write_rolls_back_together(adapter, statement_start):
    pipeline, task = _ready_payout(adapter)
    before, observed = _database_snapshot(adapter), []

    def interrupt(conn, cursor, statement, parameters, context, executemany):
        if statement.lower().replace('"', '').lstrip().startswith(statement_start):
            observed.append(statement_start)
            raise RuntimeError("injected after actual SQL write")

    event.listen(adapter.engine, "after_cursor_execute", interrupt)
    try:
        with pytest.raises(RuntimeError, match="injected after actual SQL write"):
            pipeline.trigger_payout(task.task_id, "treasury_1")
    finally:
        event.remove(adapter.engine, "after_cursor_execute", interrupt)
    assert observed == [statement_start]
    assert _database_snapshot(adapter) == before
    reopened = SQLiteAdapter(adapter.db_path)
    try:
        assert _database_snapshot(reopened) == before
        payout = PersistentTaskPipeline(reopened).trigger_payout(task.task_id, "treasury_1")
        _assert_initiation(reopened, task, payout)
    finally:
        reopened.close()


@pytest.mark.parametrize("same_task", [True, False])
def test_two_adapters_serialize_task_and_shared_wallet(adapter, same_task):
    pipeline, first = _ready_payout(adapter)
    second = first if same_task else _ready_payout(adapter, "2", fund=False)[1]
    _change_row(adapter, "compute_wallets", "actor_id", "treasury_1", credit_balance=1)
    other = SQLiteAdapter(adapter.db_path)
    other.compute_access_enforced = True
    barrier = Barrier(2)

    def run(pipeline, task_id):
        barrier.wait(timeout=5)
        try:
            return pipeline.trigger_payout(task_id, "treasury_1")
        except PermissionDeniedError as exc:
            return exc

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, pipeline, first.task_id),
                       pool.submit(run, PersistentTaskPipeline(other), second.task_id)]
            results = [future.result(timeout=10) for future in futures]
        successes = [result for result in results if isinstance(result, Payout)]
        assert len(successes) == (2 if same_task else 1)
        assert len({result.payout_id for result in successes}) == 1
        assert len(_rows(adapter, "payouts")) == 1
        assert adapter.get_wallet("treasury_1")["credit_balance"] == 0
        selected = first if successes[0].task_id == first.task_id else second
        _assert_initiation(adapter, selected, successes[0])
    finally:
        other.close()


@pytest.mark.parametrize("kind", ["orphan", "duplicate", "paid_initiated", "missing_payout"])
def test_legacy_payout_states_reject_without_reconciliation(adapter, kind):
    pipeline, task = _ready_payout(adapter)
    if kind != "missing_payout":
        adapter.create_payout(Payout("legacy", task.task_id, "agent_1", 100))
    if kind == "duplicate":
        adapter.create_payout(Payout("duplicate", task.task_id, "agent_1", 100))
    if kind in {"paid_initiated", "missing_payout"}:
        task.payout_id = "legacy"
        task.status = TaskStatus.PAID if kind == "paid_initiated" else TaskStatus.VERIFIED
        adapter.update_task(task)
    before = _database_snapshot(adapter)
    with pytest.raises(AgentMarketError):
        pipeline.trigger_payout(task.task_id, "treasury_1")
    assert _database_snapshot(adapter) == before


def _legacy_debit(adapter, task, kind):
    actor = "treasury_1" if kind == "same_actor" else "old_actor"
    if actor != "treasury_1":
        adapter.activate_compute_plan(actor, tier="builder", monthly_credit_allocation=20)
    scope = None if kind == "missing_scope" else task.foundup_id
    adapter.debit_credits(actor, 1, "trigger_payout", foundup_id=scope)
    row = next(row for row in _rows(adapter, "compute_ledger_entries")
               if row["reason"] == "trigger_payout")
    if kind == "conflicting_event_scope":
        adapter.create_event(EventRecord(
            event_id="legacy_event", event_type="payout.initiated", actor_id=actor,
            payload={}, foundup_id="other_foundup", task_id="other_task",
        ))
        _change_row(adapter, "compute_ledger_entries", "entry_id", row["entry_id"],
                    event_id="legacy_event")
    if kind == "past_100":
        table = Base.metadata.tables["compute_ledger_entries"]
        filler = [{**row, "entry_id": f"unrelated_{i:03}", "reason": "unrelated",
                   "created_at": row["created_at"] + timedelta(seconds=i + 1)}
                  for i in range(105)]
        with adapter.engine.begin() as conn:
            conn.execute(insert(table), filler)


@pytest.mark.parametrize("kind", [
    "same_actor", "different_actor", "missing_scope", "past_100", "conflicting_event_scope",
])
def test_legacy_debit_residue_blocks_before_another_charge(adapter, kind):
    pipeline, task = _ready_payout(adapter)
    _legacy_debit(adapter, task, kind)
    before = _database_snapshot(adapter)
    with pytest.raises(AgentMarketError):
        pipeline.trigger_payout(task.task_id, "treasury_1")
    assert _database_snapshot(adapter) == before


def test_consistent_other_foundup_initiation_does_not_block(adapter):
    pipeline, first = _ready_payout(adapter)
    _, second = _ready_payout(adapter, "2", fund=False)
    payout1 = pipeline.trigger_payout(first.task_id, "treasury_1")
    payout2 = pipeline.trigger_payout(second.task_id, "treasury_1")
    _assert_initiation(adapter, first, payout1)
    _assert_initiation(adapter, second, payout2)
    assert payout1.payout_id != payout2.payout_id
    assert adapter.get_wallet("treasury_1")["credit_balance"] == 18


@pytest.mark.parametrize("corruption", [
    "event_actor", "event_scope", "event_missing", "event_duplicate", "cost_snapshot",
    "debit_missing", "extra_actor", "extra_reason", "extra_type",
])
def test_retry_validates_complete_event_and_ledger_cardinality(adapter, corruption):
    pipeline, task = _ready_payout(adapter)
    payout = pipeline.trigger_payout(task.task_id, "treasury_1")
    _assert_initiation(adapter, task, payout)
    recorded = adapter.query_events(task_id=task.task_id, event_type="payout.initiated")[0]
    events = Base.metadata.tables["event_records"]
    ledger = Base.metadata.tables["compute_ledger_entries"]
    with adapter.engine.begin() as conn:
        if corruption == "event_missing":
            conn.execute(delete(events).where(events.c.event_id == recorded.event_id))
        elif corruption == "event_duplicate":
            row = dict(conn.execute(select(events).where(events.c.event_id == recorded.event_id)).mappings().one())
            row["event_id"] = "duplicate_event"
            conn.execute(insert(events), row)
        elif corruption.startswith("event_"):
            field = "actor_id" if corruption == "event_actor" else "foundup_id"
            conn.execute(update(events).where(events.c.event_id == recorded.event_id).values(**{field: "other"}))
        elif corruption == "cost_snapshot":
            payload = {**recorded.payload, "required_credits": 0}
            conn.execute(update(events).where(events.c.event_id == recorded.event_id).values(payload=payload))
        elif corruption == "debit_missing":
            conn.execute(delete(ledger).where(ledger.c.event_id == recorded.event_id))
        else:
            row = dict(conn.execute(select(ledger).where(ledger.c.event_id == recorded.event_id)).mappings().one())
            field = {"extra_actor": "actor_id", "extra_reason": "reason", "extra_type": "entry_type"}[corruption]
            row.update(entry_id="extra_linked", **{field: "wrong"})
            conn.execute(insert(ledger), row)
    before = _database_snapshot(adapter)
    with pytest.raises(AgentMarketError):
        pipeline.trigger_payout(task.task_id, "treasury_1")
    assert _database_snapshot(adapter) == before


@pytest.mark.parametrize("denial", ["no_plan", "inactive", "scout", "empty", "no_wallet"])
def test_compute_denial_leaves_every_table_unchanged(adapter, denial):
    pipeline, task = _ready_payout(adapter)
    plans, wallets = (Base.metadata.tables[name] for name in ("compute_plans", "compute_wallets"))
    with adapter.engine.begin() as conn:
        if denial == "no_plan":
            conn.execute(delete(plans).where(plans.c.actor_id == "treasury_1"))
        elif denial == "no_wallet":
            conn.execute(delete(wallets).where(wallets.c.actor_id == "treasury_1"))
        elif denial == "empty":
            conn.execute(update(wallets).where(wallets.c.actor_id == "treasury_1").values(credit_balance=0))
        else:
            field = "tier" if denial == "scout" else "status"
            conn.execute(update(plans).where(plans.c.actor_id == "treasury_1").values(**{field: denial}))
    before = _database_snapshot(adapter)
    with pytest.raises(PermissionDeniedError):
        pipeline.trigger_payout(task.task_id, "treasury_1")
    assert _database_snapshot(adapter) == before


def test_non_sqlite_rejects_before_session_or_compute_attribute_access(adapter, monkeypatch):
    pipeline, task = _ready_payout(adapter)
    before, calls = _database_snapshot(adapter), []

    def forbidden(*args, **kwargs):
        calls.append("forbidden dependency access")
        raise AssertionError("non-SQLite path accessed transaction or compute")

    with monkeypatch.context() as patch:
        patch.setattr(adapter.engine.dialect, "name", "postgresql")
        patch.setattr(adapter, "session", forbidden)
        patch.setattr(adapter, "_SessionFactory", forbidden)
        for name in ("compute_access_enforced", "compute_meter_costs", "compute_default_credits"):
            patch.setattr(SQLiteAdapter, name, property(forbidden), raising=False)
        with pytest.raises(AgentMarketError):
            pipeline.trigger_payout(task.task_id, "treasury_1")
    assert calls == []
    assert _database_snapshot(adapter) == before


def test_other_foundup_event_cannot_hide_target_scoped_wrong_reason_debit(adapter):
    pipeline, target = _ready_payout(adapter)
    _, other = _ready_payout(adapter, "2", fund=False)
    payout = pipeline.trigger_payout(other.task_id, "treasury_1")
    _assert_initiation(adapter, other, payout)
    recorded = adapter.query_events(task_id=other.task_id, event_type="payout.initiated")[0]
    linked = [row for row in _rows(adapter, "compute_ledger_entries")
              if row["event_id"] == recorded.event_id]
    assert len(linked) == 1
    _change_row(adapter, "compute_ledger_entries", "entry_id", linked[0]["entry_id"],
                foundup_id=target.foundup_id, reason="wrong")
    before = _database_snapshot(adapter)
    with pytest.raises(AgentMarketError):
        pipeline.trigger_payout(target.task_id, "treasury_1")
    assert _database_snapshot(adapter) == before


def test_lost_response_after_commit_reopens_without_second_initiation(adapter):
    pipeline, task = _ready_payout(adapter)
    staged, committed = [], []
    lost_response = RuntimeError("injected lost response after payout commit")

    def mark_payout(conn, cursor, statement, parameters, context, executemany):
        if statement.lower().replace('"', '').lstrip().startswith("insert into payouts"):
            staged.append(True)

    def interrupt_response(session):
        if staged and not committed:
            committed.append(True)
            raise lost_response

    event.listen(adapter.engine, "after_cursor_execute", mark_payout)
    event.listen(adapter._SessionFactory, "after_commit", interrupt_response)
    try:
        with pytest.raises((RuntimeError, InvalidRequestError)) as raised:
            pipeline.trigger_payout(task.task_id, "treasury_1")
    finally:
        event.remove(adapter._SessionFactory, "after_commit", interrupt_response)
        event.remove(adapter.engine, "after_cursor_execute", mark_payout)
    assert staged == committed == [True]
    assert any(error is lost_response for error in (
        raised.value, raised.value.__cause__, raised.value.__context__,
    ))
    assert len(_rows(adapter, "payouts")) == 1
    payout = adapter.get_payout(_rows(adapter, "payouts")[0]["payout_id"])
    _assert_initiation(adapter, task, payout)
    before = _database_snapshot(adapter)
    adapter.close()
    reopened = SQLiteAdapter(adapter.db_path)
    try:
        assert PersistentTaskPipeline(reopened).trigger_payout(task.task_id, "treasury_1") == payout
        _assert_initiation(reopened, task, payout)
        assert _database_snapshot(reopened) == before
    finally:
        reopened.close()


def test_task_cannot_substitute_another_valid_initiation_pointer(adapter):
    pipeline, target = _ready_payout(adapter)
    _, other = _ready_payout(adapter, "2", fund=False)
    target_payout = pipeline.trigger_payout(target.task_id, "treasury_1")
    other_payout = pipeline.trigger_payout(other.task_id, "treasury_1")
    _assert_initiation(adapter, target, target_payout)
    _assert_initiation(adapter, other, other_payout)
    assert target_payout.payout_id != other_payout.payout_id
    _change_row(adapter, "tasks", "task_id", target.task_id, payout_id=other_payout.payout_id)
    before = _database_snapshot(adapter)
    with pytest.raises(AgentMarketError):
        pipeline.trigger_payout(target.task_id, "treasury_1")
    assert _database_snapshot(adapter) == before


def test_busy_writer_rejects_without_fallback_then_retries_after_release(adapter):
    pipeline, task = _ready_payout(adapter)
    blocker = SQLiteAdapter(adapter.db_path)
    before, observed = _database_snapshot(adapter), []

    def no_wait(dbapi_connection, connection_record, connection_proxy):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA busy_timeout=0")
            observed.append(cursor.execute("PRAGMA busy_timeout").fetchone()[0])
        finally:
            cursor.close()

    event.listen(adapter.engine, "checkout", no_wait)
    try:
        with blocker.engine.connect() as lock:
            lock.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                with pytest.raises(OperationalError, match="locked"):
                    pipeline.trigger_payout(task.task_id, "treasury_1")
                assert observed and set(observed) == {0}
                assert _database_snapshot(adapter) == before
            finally:
                lock.rollback()
    finally:
        event.remove(adapter.engine, "checkout", no_wait)
        blocker.close()
    assert _database_snapshot(adapter) == before
    payout = pipeline.trigger_payout(task.task_id, "treasury_1")
    _assert_initiation(adapter, task, payout)
    assert adapter.get_wallet("treasury_1")["credit_balance"] == 19


def _submitted_verification(adapter, approved):
    adapter.compute_access_enforced = True
    adapter.compute_default_credits = 0
    adapter.compute_meter_costs["proof.verify"] = 2
    adapter.create_foundup(_foundup())
    task = Task(
        task_id="verify_task", foundup_id="f_1", title="verification witness",
        description="disposable persistence only", acceptance_criteria=["fixed"],
        reward_amount=100, creator_id="owner_1", status=TaskStatus.SUBMITTED,
        assignee_id="agent_1", proof_id="verify_proof",
    )
    adapter.create_task(task)
    adapter.create_proof(Proof(
        proof_id=task.proof_id, task_id=task.task_id, submitter_id="agent_1",
        artifact_uri="memory://synthetic-proof", artifact_hash="sha256:synthetic",
    ))
    adapter.activate_compute_plan("verifier_1", tier="builder", monthly_credit_allocation=20)
    decision = Verification(
        verification_id="verify_decision", task_id=task.task_id,
        verifier_id="verifier_1", approved=approved, reason="fixed synthetic decision",
    )
    return task, decision


def _verification_observation(adapter, task, decision):
    current = adapter.get_task(task.task_id)
    decisions = _rows(adapter, "verifications")
    events = _rows(adapter, "event_records")
    debits = [row for row in adapter.list_compute_ledger("verifier_1")
              if row["entry_type"] == "debit"]
    if decisions:
        saved = adapter.get_verification(decision.verification_id)
        assert saved.task_id == task.task_id and saved.verifier_id == decision.verifier_id
        assert saved.approved == decision.approved and saved.reason == decision.reason
    for event_row in events:
        assert event_row["task_id"] == task.task_id
        assert event_row["actor_id"] == decision.verifier_id
        assert event_row["event_type"] == ("proof.verified" if decision.approved else "proof.rejected")
    assert all(row["reason"] == "verify_proof" for row in debits)
    assert current.proof_id == task.proof_id and current.payout_id is None
    assert current.verification_id in (None, decision.verification_id)
    return (current.status.value, current.verification_id == decision.verification_id,
            len(decisions), len(events), adapter.get_wallet("verifier_1")["credit_balance"],
            len(debits))


@pytest.mark.parametrize("stage,first_error,retry_error,first_state,retry_state", [
    ("accepted", None, None,
     ("verified", True, 1, 1, 18, 1), ("verified", True, 1, 1, 18, 1)),
    ("rejected", ValidationError, ValidationError,
     ("submitted", False, 1, 1, 18, 1), ("submitted", False, 1, 1, 18, 1)),
    ("insert into verifications", RuntimeError, None,
     ("submitted", False, 0, 0, 20, 0), ("verified", True, 1, 1, 18, 1)),
    ("update tasks", RuntimeError, None,
     ("submitted", False, 0, 0, 20, 0), ("verified", True, 1, 1, 18, 1)),
    ("insert into event_records", RuntimeError, None,
     ("submitted", False, 0, 0, 20, 0), ("verified", True, 1, 1, 18, 1)),
], ids=["accepted", "rejected", "after-decision", "after-task", "after-event"])
def test_verification_interruption_reopen_acceptance(tmp_path, stage, first_error,
                                                     retry_error, first_state, retry_state):
    """Fixed atomicity/replay acceptance; real post-write SQL failure seams."""
    db_path = tmp_path / "verification_acceptance.db"
    adapter = SQLiteAdapter(db_path)
    try:
        task, decision = _submitted_verification(adapter, stage != "rejected")
        before = _database_snapshot(adapter)
        observed = []
        def interrupt(conn, cursor, statement, parameters, context, executemany):
            if statement.lower().startswith(stage):
                observed.append(stage)
                raise RuntimeError("fixed verification interruption")
        event.listen(adapter.engine, "after_cursor_execute", interrupt)
        try:
            with pytest.raises(first_error) if first_error else nullcontext():
                PersistentTaskPipeline(adapter).verify_proof(task.task_id, decision)
        finally:
            event.remove(adapter.engine, "after_cursor_execute", interrupt)
        after = _database_snapshot(adapter)
        if first_error is RuntimeError:
            assert observed == [stage] and after == before
        assert _verification_observation(adapter, task, decision) == first_state
        adapter.close()
        adapter = SQLiteAdapter(db_path)
        adapter.compute_access_enforced = True
        adapter.compute_meter_costs["proof.verify"] = 2
        assert _database_snapshot(adapter) == after
        with pytest.raises(retry_error, match="Proof rejected") if retry_error else nullcontext():
            PersistentTaskPipeline(adapter).verify_proof(task.task_id, decision)
        assert _verification_observation(adapter, task, decision) == retry_state
        final = _database_snapshot(adapter)
        changed = {"tasks", "verifications", "event_records", "compute_wallets", "compute_ledger_entries"}
        assert all(before[name] == final[name] for name in before if name not in changed)
    finally:
        adapter.close()
