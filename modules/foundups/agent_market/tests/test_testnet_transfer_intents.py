"""Probe admission with synthetic public fixtures; no transport or settlement."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from threading import Barrier

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError

from modules.foundups.agent_market.src.authorization import CallerAuthorization
from modules.foundups.agent_market.src.models import Proof, Verification
from modules.foundups.agent_market.src.exceptions import (
    AgentMarketError, NotFoundError, PermissionDeniedError, ValidationError,
)
from modules.foundups.agent_market.src.persistence.sqlite_adapter import SQLiteAdapter
from modules.foundups.agent_market.src.persistence.migrations import MigrationManager
from modules.foundups.agent_market.src.persistence.testnet_transfer_intents import (
    HostTestnetPolicy, PreparedTestnetIntent, SubmittedTestnetBinding,
    TestnetTransferIntentService as IntentService,
)
from modules.foundups.agent_market.tests.test_persistent_compute_wiring import (
    _OTHER_TREASURY_AUTH, _TREASURY_AUTH, _change_row, _ready_payout, _rows,
)
from modules.foundups.agent_market.tests.test_sqlite_adapter import _ORM_TABLES

NOW, LIMIT = 2_000_000_000, 2**63 - 1
IDENTITY = dict(network="algorand-testnet", genesis_id="testnet-v1.0",
                genesis_hash_hex="ab" * 32, asset_id=12345, asset_decimals=6,
                sender_address="TEST_SENDER", expected_auth_address="TEST_AUTH")


def _old(adapter):
    assert len(_ORM_TABLES) == 13
    return {name: _rows(adapter, name) for name in _ORM_TABLES.values()}


def _intents(adapter):
    with adapter.engine.connect() as conn:
        exists = conn.execute(text("SELECT name FROM sqlite_master WHERE name='testnet_transfer_intents'")).first()
        return list(conn.execute(text("SELECT * FROM testnet_transfer_intents ORDER BY intent_id")).mappings()) if exists else []


def _snapshot(adapter):
    with adapter.engine.connect() as conn:
        present = conn.execute(text("SELECT name FROM sqlite_master WHERE name='schema_migrations'")).first()
        versions = conn.execute(text("SELECT * FROM schema_migrations ORDER BY version")).all() if present else None
    return _old(adapter), _intents(adapter), versions


@pytest.fixture
def ready(tmp_path, monkeypatch, request):
    monkeypatch.setattr(SQLiteAdapter, "_now_utc", lambda self: datetime.fromtimestamp(NOW, timezone.utc))
    adapter = SQLiteAdapter(tmp_path / "intents.sqlite", **getattr(request, "param", {}))
    pipeline, task = _ready_payout(adapter)
    payout = pipeline.trigger_payout(task.task_id, "treasury_1", authorization=_TREASURY_AUTH)
    policy = HostTestnetPolicy("probe_policy", 1, "treasury_1", "f_1", "agent_1", **IDENTITY,
                               recipient_allowlist=frozenset({"TEST_RECEIVER", "TEST_SECOND"}),
                               max_amount_atoms=1000, max_fee_microalgos=2000, expires_at_epoch_s=NOW + 60)
    binding = SubmittedTestnetBinding(1, "TEST_TRANSPORT_PROBE", "probe_policy", 1, **IDENTITY,
                                     recipient_address="TEST_RECEIVER", amount_atoms=7,
                                     fee_cap_microalgos=1000, expires_at_epoch_s=NOW + 60)
    yield adapter, pipeline, task, payout, policy, binding
    adapter.close()


def _prepare(ready, *, policy=None, binding=None, actor="treasury_1", authorization=_TREASURY_AUTH, payout_id=...):
    adapter, _, _, payout, configured, submitted = ready
    return IntentService(adapter, configured if policy is None else policy).prepare(
        payout.payout_id if payout_id is ... else payout_id, actor,
        submitted if binding is None else binding, authorization=authorization)


def _reject(ready, error=ValidationError, **changes):
    before = _snapshot(ready[0])
    with pytest.raises(error):
        _prepare(ready, **changes)
    assert _snapshot(ready[0]) == before


def test_explicit_atoms_prepare_without_old_state_effects(ready):
    before, result = _old(ready[0]), _prepare(ready)
    assert type(result) is PreparedTestnetIntent and result.state == "PREPARED"
    assert result.payout_id == ready[3].payout_id and result.purpose == "TEST_TRANSPORT_PROBE"
    assert result.created_at_epoch_s == NOW and result.expires_at_epoch_s == NOW + 60
    identity = json.loads(result.identity_json)
    assert result.identity_json == json.dumps(identity, sort_keys=True, separators=(",", ":"), allow_nan=False)
    assert identity["binding"]["amount_atoms"] == 7 != ready[3].amount
    assert identity["policy"]["asset_id"] == 12345
    assert len(identity["initiation_payload_sha256"]) == 64 and identity["initiation_event_id"]
    assert result.identity_sha256 == hashlib.sha256(result.identity_json.encode()).hexdigest()
    assert len(_intents(ready[0])) == 1 and _old(ready[0]) == before


def test_exact_retry_reopen_and_original_pending_call(ready, monkeypatch):
    first, before = _prepare(ready), _snapshot(ready[0])
    monkeypatch.setattr(SQLiteAdapter, "_now_utc", lambda self: datetime.fromtimestamp(NOW + 1, timezone.utc))
    assert _prepare(ready) == first and _snapshot(ready[0]) == before
    ready[0].close()
    reopened = SQLiteAdapter(ready[0].db_path)
    try:
        assert _prepare((reopened, *ready[1:])) == first
        assert ready[1].trigger_payout(ready[2].task_id, "treasury_1", authorization=_TREASURY_AUTH) == ready[3]
        assert _snapshot(reopened) == before
    finally:
        reopened.close()


@pytest.mark.parametrize("same_foundup", [False, True], ids=["other-foundup", "same-foundup"])
def test_later_legitimate_task_still_initiates(ready, same_foundup):
    first = _prepare(ready)
    if same_foundup:
        task = replace(ready[2], task_id="later_task", proof_id="later_proof",
                       verification_id="later_verification", payout_id=None)
        ready[0].create_task(task)
        ready[0].create_proof(Proof(proof_id=task.proof_id, task_id=task.task_id,
                                  submitter_id="agent_1", artifact_uri="memory://later-proof",
                                  artifact_hash="sha256:later-proof"))
        ready[0].create_verification(Verification(verification_id=task.verification_id,
                                                task_id=task.task_id, verifier_id="verifier_1",
                                                approved=True, reason="fixed trusted fixture"))
        pipeline = ready[1]
    else:
        pipeline, task = _ready_payout(ready[0], "2", fund=False)
    assert task.foundup_id == ("f_1" if same_foundup else "f_2")
    payout = pipeline.trigger_payout(task.task_id, "treasury_1", authorization=_TREASURY_AUTH)
    assert payout.task_id == task.task_id and len(_intents(ready[0])) == 1
    before = _snapshot(ready[0])
    assert _prepare(ready) == first
    assert ready[1].trigger_payout(ready[2].task_id, "treasury_1", authorization=_TREASURY_AUTH) == ready[3]
    assert _snapshot(ready[0]) == before


@pytest.mark.parametrize("context", [None, {}, CallerAuthorization("treasury_1", frozenset()),
    CallerAuthorization("treasury_1", frozenset({("f_2", "treasury")})),
    CallerAuthorization("treasury_1", frozenset({("f_1", "admin")})), _OTHER_TREASURY_AUTH],
    ids=["absent", "payload", "no-grant", "wrong-foundup", "admin", "wrong-principal"])
def test_current_authority_is_required_on_every_call(ready, context):
    _reject(ready, PermissionDeniedError, authorization=context)


def test_other_legitimate_treasury_cannot_take_over(ready):
    _reject(ready, PermissionDeniedError, actor="other_actor", authorization=_OTHER_TREASURY_AUTH,
            policy=replace(ready[4], principal_id="other_actor"))


@pytest.mark.parametrize("field,value", [("network", "algorand-mainnet"), ("genesis_id", "mainnet-v1.0"),
    ("genesis_hash_hex", "cd" * 32), ("asset_id", 54321), ("asset_decimals", 5),
    ("sender_address", "OTHER_SENDER"), ("expected_auth_address", "OTHER_AUTH"),
    ("purpose", "REWARD_SETTLEMENT"), ("format_version", 2), ("policy_id", "other"),
    ("policy_version", 2), ("expires_at_epoch_s", NOW + 61)])
def test_each_submitted_identity_field_is_bound(ready, field, value):
    _reject(ready, binding=replace(ready[5], **{field: value}))
    _prepare(ready)
    policy = replace(ready[4], **{field: value}) if hasattr(ready[4], field) else ready[4]
    _reject(ready, policy=policy, binding=replace(ready[5], **{field: value}))


@pytest.mark.parametrize("field,value", [("foundup_id", "f_2"), ("payout_recipient_id", "other_agent"),
    ("recipient_allowlist", frozenset({"OTHER_RECIPIENT"})), ("recipient_allowlist", {"TEST_RECEIVER"})])
def test_host_scope_and_recipient_binding(ready, field, value):
    _reject(ready, policy=replace(ready[4], **{field: value}))


@pytest.mark.parametrize("value", [True, "7", float("nan"), float("inf"), 0, -1, LIMIT + 1])
def test_invalid_amount_types_and_range_have_no_effect(ready, value):
    _reject(ready, binding=replace(ready[5], amount_atoms=value))


@pytest.mark.parametrize("field,value", [("fee_cap_microalgos", True), ("fee_cap_microalgos", 0),
    ("fee_cap_microalgos", LIMIT + 1), ("asset_decimals", True), ("asset_decimals", -1),
    ("asset_decimals", 20), ("expires_at_epoch_s", "soon")])
def test_invalid_fee_decimals_and_expiry(ready, field, value):
    _reject(ready, binding=replace(ready[5], **{field: value}))


@pytest.mark.parametrize("field,value", [("max_amount_atoms", True), ("max_amount_atoms", LIMIT + 1),
    ("max_fee_microalgos", float("inf")), ("asset_id", 0), ("policy_version", False),
    ("genesis_hash_hex", "not-hex"), ("sender_address", ""), ("policy_id", "x" * 65)])
def test_invalid_host_policy_has_no_effect(ready, field, value):
    _reject(ready, policy=replace(ready[4], **{field: value}))


@pytest.mark.parametrize("field,value", [("amount_atoms", 1001), ("fee_cap_microalgos", 2001),
                                       ("recipient_address", "OTHER_RECIPIENT")])
def test_submitted_quantity_fee_and_recipient_limits(ready, field, value):
    _reject(ready, binding=replace(ready[5], **{field: value}))


def test_exact_numeric_caps_and_zero_decimals_remain_valid(ready):
    policy = replace(ready[4], max_amount_atoms=LIMIT, max_fee_microalgos=LIMIT, asset_decimals=0)
    binding = replace(ready[5], amount_atoms=LIMIT, fee_cap_microalgos=LIMIT, asset_decimals=0)
    result = _prepare(ready, policy=policy, binding=binding)
    assert json.loads(result.identity_json)["binding"]["amount_atoms"] == LIMIT


@pytest.mark.parametrize("kind,value", [("binding", None), ("policy", None),
    ("payout_id", {}), ("payout_id", True), ("payout_id", None), ("actor", [])])
def test_payload_and_identity_types_fail_closed(ready, kind, value):
    if kind in ("binding", "policy"):
        value = asdict(ready[5] if kind == "binding" else ready[4])
    _reject(ready, **{kind: value})


def test_records_are_immutable_without_nested_mutation(ready):
    for record in (ready[4], ready[5]):
        with pytest.raises(FrozenInstanceError):
            record.policy_id = "changed"
    with pytest.raises(AttributeError):
        ready[4].recipient_allowlist.add("OTHER_RECIPIENT")
    result = _prepare(ready)
    with pytest.raises(FrozenInstanceError):
        result.state = "CONFIRMED"


@pytest.mark.parametrize("change", ["policy-version", "quantity", "authority", "expiry", "host-cap"])
def test_retry_revalidates_current_inputs_without_overwriting(ready, monkeypatch, change):
    _prepare(ready)
    changes, error = {}, ValidationError
    if change == "policy-version":
        changes = dict(policy=replace(ready[4], policy_version=2), binding=replace(ready[5], policy_version=2))
    elif change == "quantity":
        changes = dict(binding=replace(ready[5], amount_atoms=8))
    elif change == "authority":
        changes, error = dict(authorization=None), PermissionDeniedError
    elif change == "host-cap":
        changes = dict(policy=replace(ready[4], max_amount_atoms=1001))
    else:
        monkeypatch.setattr(SQLiteAdapter, "_now_utc", lambda self: datetime.fromtimestamp(NOW + 60, timezone.utc))
    _reject(ready, error, **changes)


@pytest.mark.parametrize("column,value", [("identity_json", "{}"), ("identity_sha256", "0" * 64),
                                         ("actor_id", "other_actor"), ("state", "CONFIRMED")])
def test_corrupted_intent_is_never_overwritten(ready, column, value):
    _prepare(ready)
    with ready[0].engine.begin() as conn:
        conn.execute(text("PRAGMA ignore_check_constraints=ON"))
        conn.execute(text(f"UPDATE testnet_transfer_intents SET {column}=:value"), {"value": value})
        conn.execute(text("PRAGMA ignore_check_constraints=OFF"))
    _reject(ready)


@pytest.mark.parametrize("kind", ["proof", "self-verification", "duplicate-event", "missing-payout"])
def test_ambiguous_existing_history_is_not_repaired(ready, kind):
    if kind == "proof":
        _change_row(ready[0], "proofs", "proof_id", ready[2].proof_id, artifact_hash="changed")
    elif kind == "self-verification":
        _change_row(ready[0], "verifications", "verification_id", ready[2].verification_id, verifier_id="agent_1")
    elif kind == "duplicate-event":
        row = dict(next(row for row in _rows(ready[0], "event_records") if row["event_type"] == "payout.initiated"), event_id="extra_event")
        with ready[0].session() as sess:
            from modules.foundups.agent_market.src.persistence.orm_models import EventRecordRow
            sess.add(EventRecordRow(**row))
    else:
        _reject(ready, NotFoundError, payout_id="missing")
        return
    _reject(ready, AgentMarketError)


@pytest.mark.parametrize("kind", ["version2", "unrecorded", "future", "missing-column", "missing-unique", "partial-unique", "wrong-unique", "generated-column", "generated-required"])
def test_unqualified_schema_never_gains_admission(ready, kind, monkeypatch):
    with ready[0].engine.begin() as conn:
        if kind in ("version2", "unrecorded", "future"):
            conn.execute(text("DELETE FROM schema_migrations" + ("" if kind == "unrecorded" else " WHERE version>=3")))
            if kind == "future":
                conn.execute(text("INSERT INTO schema_migrations(version,description) VALUES(4,'unqualified')"))
        elif kind == "generated-column":
            conn.execute(text("ALTER TABLE testnet_transfer_intents ADD COLUMN hidden_shadow INTEGER GENERATED ALWAYS AS(format_version) VIRTUAL"))
        elif kind == "generated-required":
            conn.execute(text("ALTER TABLE testnet_transfer_intents DROP COLUMN actor_id"))
            conn.execute(text("ALTER TABLE testnet_transfer_intents ADD COLUMN actor_id TEXT GENERATED ALWAYS AS('treasury_1') VIRTUAL NOT NULL"))
        else:
            conn.execute(text("DROP TABLE IF EXISTS testnet_transfer_intents"))
            declaration = "intent_id TEXT PRIMARY KEY" if kind == "missing-column" else (
                "intent_id TEXT NOT NULL PRIMARY KEY,payout_id TEXT NOT NULL,purpose TEXT NOT NULL,"
                "format_version INTEGER NOT NULL,state TEXT NOT NULL,foundup_id TEXT NOT NULL,"
                "task_id TEXT NOT NULL,actor_id TEXT NOT NULL,identity_json TEXT NOT NULL,"
                "identity_sha256 TEXT NOT NULL,created_at_epoch_s INTEGER NOT NULL,expires_at_epoch_s INTEGER NOT NULL,"
                "CHECK(format_version=1),CHECK(purpose='TEST_TRANSPORT_PROBE'),CHECK(state='PREPARED')")
            conn.execute(text("CREATE TABLE testnet_transfer_intents(" + declaration + ")"))
            if kind in ("partial-unique", "wrong-unique"):
                key = "payout_id,purpose) WHERE state='PREPARED'" if kind == "partial-unique" else "payout_id,actor_id)"
                conn.execute(text("CREATE UNIQUE INDEX unsupported_key ON testnet_transfer_intents(" + key))
    monkeypatch.setattr(ready[0], "_next_id", lambda prefix: pytest.fail("Unqualified schema reached intent ID allocation"))
    _reject(ready)


def test_non_sqlite_rejects_before_session(ready, monkeypatch):
    monkeypatch.setattr(ready[0].engine.dialect, "name", "postgresql")
    monkeypatch.setattr(ready[0], "session", lambda: pytest.fail("unsupported backend opened session"))
    with pytest.raises(ValidationError):
        _prepare(ready)


def test_insert_failure_rolls_back_and_reopen_sees_no_intent(ready):
    before, observed = _snapshot(ready[0]), []
    def interrupt(conn, cursor, statement, parameters, context, executemany):
        if statement.lower().replace('"', '').lstrip().startswith("insert into testnet_transfer_intents"):
            observed.append(True)
            raise RuntimeError("after actual intent insert")
    event.listen(ready[0].engine, "after_cursor_execute", interrupt)
    try:
        with pytest.raises(RuntimeError, match="after actual intent insert"):
            _prepare(ready)
    finally:
        event.remove(ready[0].engine, "after_cursor_execute", interrupt)
    assert observed == [True] and _snapshot(ready[0]) == before
    reopened = SQLiteAdapter(ready[0].db_path)
    try:
        assert _snapshot(reopened) == before
    finally:
        reopened.close()


@pytest.mark.parametrize("expired", [False, True])
def test_lost_response_keeps_one_record_without_renewal(ready, monkeypatch, expired):
    original = ready[0].session
    @contextmanager
    def lost_response():
        with original() as sess:
            yield sess
        raise RuntimeError("lost response after commit")
    monkeypatch.setattr(ready[0], "session", lost_response)
    with pytest.raises(RuntimeError, match="lost response after commit"):
        _prepare(ready)
    monkeypatch.setattr(ready[0], "session", original)
    committed = _snapshot(ready[0])
    assert len(committed[1]) == 1
    if expired:
        monkeypatch.setattr(SQLiteAdapter, "_now_utc", lambda self: datetime.fromtimestamp(NOW + 60, timezone.utc))
        _reject(ready)
    else:
        assert _prepare(ready).intent_id == committed[1][0]["intent_id"]
        assert _snapshot(ready[0]) == committed


@pytest.mark.parametrize("conflict", [False, True])
def test_two_adapters_serialize_identical_and_conflicting_content(ready, conflict):
    other, barrier = SQLiteAdapter(ready[0].db_path), Barrier(2)
    before = _old(ready[0])
    def run(adapter, binding):
        barrier.wait(timeout=5)
        try:
            return _prepare((adapter, *ready[1:]), binding=binding)
        except ValidationError as exc:
            return exc
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, ready[0], ready[5]), pool.submit(
                run, other, replace(ready[5], amount_atoms=8) if conflict else ready[5])]
            results = [future.result(timeout=10) for future in futures]
        successes = [result for result in results if type(result) is PreparedTestnetIntent]
        assert len(successes) == (1 if conflict else 2)
        assert len({result.intent_id for result in successes}) == 1
        assert sum(isinstance(result, ValidationError) for result in results) == int(conflict)
        assert all(result == successes[0] for result in successes)
        assert len(_intents(other)) == 1 and _old(other) == before
        winner, row = successes[0], _intents(other)[0]
        assert {key: row[key] for key in asdict(winner)} == asdict(winner)
        winner_binding = replace(ready[5], amount_atoms=json.loads(winner.identity_json)["binding"]["amount_atoms"])
        reopened = SQLiteAdapter(ready[0].db_path)
        try:
            assert _prepare((reopened, *ready[1:]), binding=winner_binding) == winner
        finally:
            reopened.close()
    finally:
        other.close()


def test_first_admission_rejects_at_exact_expiry(ready):
    _reject(ready, policy=replace(ready[4], expires_at_epoch_s=NOW),
            binding=replace(ready[5], expires_at_epoch_s=NOW))


def test_one_admission_clock_sample(ready, monkeypatch):
    samples = []
    def clock(self):
        samples.append(NOW if not samples else NOW + 60)
        return datetime.fromtimestamp(samples[-1], timezone.utc)
    monkeypatch.setattr(SQLiteAdapter, "_now_utc", clock)
    assert _prepare(ready).created_at_epoch_s == NOW
    assert samples == [NOW]


@pytest.mark.parametrize("ready", [{"schema_version": 2}, {"auto_migrate": False}],
                         indirect=True, ids=["pinned-v2-constructor", "disabled-migration-constructor"])
def test_v2_upgrade_is_additive_and_repeatable(ready):
    _reject(ready)
    with ready[0].engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS testnet_transfer_intents"))
    before = _old(ready[0])
    manager = MigrationManager(ready[0].engine)
    assert manager.migrate() == 3 and _old(ready[0]) == before
    _prepare(ready)
    committed = _snapshot(ready[0])
    assert manager.migrate() == 3 and _snapshot(ready[0]) == committed


def test_busy_writer_has_no_fallback_and_can_retry_after_release(ready):
    other, before, observed = SQLiteAdapter(ready[0].db_path), _snapshot(ready[0]), []
    def no_wait(dbapi_connection, connection_record, connection_proxy):
        dbapi_connection.execute("PRAGMA busy_timeout=0")
        observed.append(True)
    event.listen(ready[0].engine, "checkout", no_wait)
    try:
        with other.engine.connect() as lock:
            lock.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                with pytest.raises(OperationalError, match="locked"):
                    _prepare(ready)
            finally:
                lock.rollback()
    finally:
        event.remove(ready[0].engine, "checkout", no_wait)
        other.close()
    assert observed and _snapshot(ready[0]) == before
    assert _prepare(ready).state == "PREPARED"


def _revalidate(ready, expected, *, policy=None, binding=None, actor="treasury_1", authorization=_TREASURY_AUTH):
    adapter, _, _, _, configured, submitted = ready
    return IntentService(adapter, configured if policy is None else policy).revalidate_existing(
        expected, actor, submitted if binding is None else binding, authorization=authorization)


@contextmanager
def _revalidation_readonly(adapter, monkeypatch):
    before = _snapshot(adapter)
    monkeypatch.setattr(adapter, "_next_id", lambda prefix: pytest.fail("revalidation allocated an ID"))
    def refuse_write(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "DROP", "ALTER")):
            pytest.fail("revalidation attempted a database write")
    event.listen(adapter.engine, "before_cursor_execute", refuse_write)
    try:
        yield
    finally:
        event.remove(adapter.engine, "before_cursor_execute", refuse_write)
        assert _snapshot(adapter) == before


@pytest.mark.parametrize("elapsed", [0, 1, 59], ids=["same-time", "later", "before-expiry"])
def test_revalidation_exact_reopen_without_allocation_or_writes(ready, monkeypatch, elapsed):
    expected, before = _prepare(ready), _snapshot(ready[0])
    monkeypatch.setattr(SQLiteAdapter, "_now_utc", lambda self: datetime.fromtimestamp(NOW + elapsed, timezone.utc))
    with _revalidation_readonly(ready[0], monkeypatch):
        assert _revalidate(ready, expected) == expected
    ready[0].close()
    reopened = SQLiteAdapter(ready[0].db_path)
    try:
        with _revalidation_readonly(reopened, monkeypatch):
            assert _revalidate((reopened, *ready[1:]), expected) == expected
        assert _snapshot(reopened) == before
        assert ready[1].trigger_payout(ready[2].task_id, "treasury_1", authorization=_TREASURY_AUTH) == ready[3]
        assert _snapshot(reopened) == before
    finally:
        reopened.close()


def test_revalidation_deleted_intent_is_not_recreated(ready, monkeypatch):
    expected = _prepare(ready)
    with ready[0].engine.begin() as conn:
        conn.execute(text("DELETE FROM testnet_transfer_intents WHERE intent_id=:value"), {"value": expected.intent_id})
    with _revalidation_readonly(ready[0], monkeypatch), pytest.raises(ValidationError):
        _revalidate(ready, expected)
    assert _intents(ready[0]) == []


def test_prepare_retains_get_or_create_behavior_after_intent_loss(ready):
    first, old = _prepare(ready), _old(ready[0])
    with ready[0].engine.begin() as conn:
        conn.execute(text("DELETE FROM testnet_transfer_intents WHERE intent_id=:value"), {"value": first.intent_id})
    second = _prepare(ready)
    assert second.intent_id != first.intent_id and second.identity_json == first.identity_json
    assert second.identity_sha256 == first.identity_sha256 and len(_intents(ready[0])) == 1
    assert _old(ready[0]) == old


@pytest.mark.parametrize("field,value", [("intent_id", "different_intent"), ("payout_id", "missing"),
    ("purpose", "OTHER_PURPOSE"), ("state", "CONFIRMED"), ("identity_json", "{}"),
    ("identity_sha256", "0" * 64), ("created_at_epoch_s", NOW + 1), ("expires_at_epoch_s", NOW + 61)],
    ids=["intent-id", "payout-id", "purpose", "state", "identity-json", "identity-hash", "created", "expiry"])
def test_revalidation_binds_every_original_dto_field(ready, monkeypatch, field, value):
    expected = replace(_prepare(ready), **{field: value})
    with _revalidation_readonly(ready[0], monkeypatch), pytest.raises(AgentMarketError):
        _revalidate(ready, expected)


@pytest.mark.parametrize("kind", ["replaced-id", "replaced-created", "replaced-expiry", "json-and-hash"])
def test_revalidation_rejects_replaced_or_rehashed_stored_intent(ready, monkeypatch, kind):
    expected = _prepare(ready)
    changes = {"intent_id": "replacement"} if kind == "replaced-id" else (
        {"created_at_epoch_s": NOW - 1} if kind == "replaced-created" else {"expires_at_epoch_s": NOW + 61})
    if kind == "json-and-hash":
        changed = json.loads(expected.identity_json)
        changed["binding"]["amount_atoms"] += 1
        encoded = json.dumps(changed, sort_keys=True, separators=(",", ":"), allow_nan=False)
        changes = dict(identity_json=encoded, identity_sha256=hashlib.sha256(encoded.encode()).hexdigest())
    _change_row(ready[0], "testnet_transfer_intents", "intent_id", expected.intent_id, **changes)
    with _revalidation_readonly(ready[0], monkeypatch), pytest.raises(ValidationError):
        _revalidate(ready, expected)


@pytest.mark.parametrize("context", [None, {}, CallerAuthorization("treasury_1", frozenset()),
    CallerAuthorization("treasury_1", frozenset({("f_2", "treasury")})),
    CallerAuthorization("treasury_1", frozenset({("f_1", "admin")})), _OTHER_TREASURY_AUTH],
    ids=["absent", "payload", "no-grant", "wrong-foundup", "admin", "wrong-principal"])
def test_revalidation_requires_current_scoped_authority(ready, monkeypatch, context):
    expected = _prepare(ready)
    with _revalidation_readonly(ready[0], monkeypatch), pytest.raises(PermissionDeniedError):
        _revalidate(ready, expected, authorization=context)


@pytest.mark.parametrize("change", ["policy-version", "quantity", "host-cap", "exact-expiry", "initiating-actor"])
def test_revalidation_rechecks_policy_binding_clock_and_initiator(ready, monkeypatch, change):
    expected, changes = _prepare(ready), {}
    if change == "policy-version":
        changes = dict(policy=replace(ready[4], policy_version=2), binding=replace(ready[5], policy_version=2))
    elif change == "quantity":
        changes = dict(binding=replace(ready[5], amount_atoms=8))
    elif change == "host-cap":
        changes = dict(policy=replace(ready[4], max_amount_atoms=1001))
    elif change == "initiating-actor":
        changes = dict(actor="other_actor", authorization=_OTHER_TREASURY_AUTH,
                       policy=replace(ready[4], principal_id="other_actor"))
    else:
        monkeypatch.setattr(SQLiteAdapter, "_now_utc", lambda self: datetime.fromtimestamp(NOW + 60, timezone.utc))
    with _revalidation_readonly(ready[0], monkeypatch), pytest.raises(AgentMarketError):
        _revalidate(ready, expected, **changes)


class _SnapshotComparisonTrap:
    def __eq__(self, other):
        raise AssertionError("snapshot rich comparison was invoked")


class _SnapshotSubclass(PreparedTestnetIntent):
    def __eq__(self, other):
        raise AssertionError("snapshot subclass comparison was invoked")


@pytest.mark.parametrize("kind", ["absent", "mapping", "subclass"])
def test_revalidation_rejects_nonexact_snapshot_type(ready, monkeypatch, kind):
    first = _prepare(ready)
    expected = None if kind == "absent" else (asdict(first) if kind == "mapping" else _SnapshotSubclass(**asdict(first)))
    with _revalidation_readonly(ready[0], monkeypatch), pytest.raises(ValidationError):
        _revalidate(ready, expected)


@pytest.mark.parametrize("field", ["intent_id", "payout_id", "purpose", "state", "identity_json",
                                   "identity_sha256", "created_at_epoch_s", "expires_at_epoch_s"])
def test_revalidation_checks_field_types_before_rich_equality(ready, monkeypatch, field):
    expected = replace(_prepare(ready), **{field: _SnapshotComparisonTrap()})
    with _revalidation_readonly(ready[0], monkeypatch), pytest.raises(ValidationError):
        _revalidate(ready, expected)


@pytest.mark.parametrize("field,value,created", [("created_at_epoch_s", True, 1),
    ("created_at_epoch_s", 1.0, 1), ("expires_at_epoch_s", float(NOW + 60), NOW)],
    ids=["created-bool-equals-one", "created-float-equals-one", "expiry-float-equals-int"])
def test_revalidation_rejects_equal_nonbuiltin_integer_fields(ready, monkeypatch, field, value, created):
    monkeypatch.setattr(SQLiteAdapter, "_now_utc", lambda self: datetime.fromtimestamp(created, timezone.utc))
    expected = replace(_prepare(ready), **{field: value})
    with _revalidation_readonly(ready[0], monkeypatch), pytest.raises(ValidationError):
        _revalidate(ready, expected)


@pytest.mark.parametrize("field", ["intent_id", "payout_id", "purpose", "state", "identity_json", "identity_sha256"])
def test_revalidation_rejects_string_subclasses_in_snapshot(ready, monkeypatch, field):
    class TextSubclass(str):
        pass
    first = _prepare(ready)
    expected = replace(first, **{field: TextSubclass(getattr(first, field))})
    with _revalidation_readonly(ready[0], monkeypatch), pytest.raises(ValidationError):
        _revalidate(ready, expected)


def test_revalidation_non_sqlite_refuses_before_session(ready, monkeypatch):
    expected = _prepare(ready)
    monkeypatch.setattr(ready[0].engine.dialect, "name", "postgresql")
    monkeypatch.setattr(ready[0], "session", lambda: pytest.fail("unsupported revalidation opened a session"))
    with _revalidation_readonly(ready[0], monkeypatch), pytest.raises(ValidationError):
        _revalidate(ready, expected)


@pytest.mark.parametrize("kind", ["unrecorded", "future-gap", "generated-column"])
def test_revalidation_requires_current_qualified_schema(ready, monkeypatch, kind):
    expected = _prepare(ready)
    with ready[0].engine.begin() as conn:
        if kind == "generated-column":
            conn.execute(text("ALTER TABLE testnet_transfer_intents ADD COLUMN shadow INTEGER GENERATED ALWAYS AS(format_version) VIRTUAL"))
        else:
            conn.execute(text("DELETE FROM schema_migrations" + (" WHERE version>=3" if kind == "future-gap" else "")))
            if kind == "future-gap":
                conn.execute(text("INSERT INTO schema_migrations(version,description) VALUES(4,'unqualified')"))
    with _revalidation_readonly(ready[0], monkeypatch), pytest.raises(ValidationError):
        _revalidate(ready, expected)


@pytest.mark.parametrize("kind", ["proof", "payout", "original-debit"])
def test_revalidation_rechecks_actual_pending_lineage(ready, monkeypatch, kind):
    expected = _prepare(ready)
    if kind == "proof":
        _change_row(ready[0], "proofs", "proof_id", ready[2].proof_id, artifact_hash="changed")
    elif kind == "payout":
        _change_row(ready[0], "payouts", "payout_id", ready[3].payout_id, amount=101)
    else:
        debit = next(row for row in _rows(ready[0], "compute_ledger_entries") if row["reason"] == "trigger_payout")
        _change_row(ready[0], "compute_ledger_entries", "entry_id", debit["entry_id"], amount=2)
    with _revalidation_readonly(ready[0], monkeypatch), pytest.raises(AgentMarketError):
        _revalidate(ready, expected)
