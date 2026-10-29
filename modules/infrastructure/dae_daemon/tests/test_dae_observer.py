"""DAE observer read-surface tests."""

import json
import sqlite3
import threading
from types import SimpleNamespace

from modules.infrastructure.dae_daemon.src.dae_daemon import (
    CentralDAEmon,
    get_central_daemon,
    reset_central_daemon,
)
from modules.infrastructure.dae_daemon.src.dae_launch_broker import (
    get_dae_launch_broker,
    reset_dae_launch_broker,
)
from modules.infrastructure.dae_daemon.src.dae_observer import (
    get_dae_observer,
    reset_dae_observer,
)
from modules.infrastructure.dae_daemon.src.dae_registry import DAERegistry
from modules.infrastructure.dae_daemon.src.event_store import DAEEventStore
from modules.infrastructure.dae_daemon.src.schemas import DAERegistration, DAEEventType, DAEEvent


class TestDAEObserver:
    def setup_method(self):
        reset_dae_observer()
        reset_dae_launch_broker()
        reset_central_daemon()

    def teardown_method(self):
        reset_dae_observer()
        reset_dae_launch_broker()
        reset_central_daemon()

    def test_tail_events_returns_recent_activity(self, tmp_path):
        daemon = get_central_daemon(data_dir=tmp_path / "dae_daemon")
        daemon.start()
        daemon.register_dae(
            DAERegistration(
                dae_id="openclaw",
                dae_name="OpenClaw DAE",
                domain="communication",
            )
        )
        daemon.registry.report_event(
            "openclaw",
            DAEEventType.ACTION_PERFORMED,
            {"action_type": "pqn_simulation", "target": "pqn_theory_archive", "result": "started"},
        )

        observer = get_dae_observer(daemon=daemon)
        events = observer.tail_events(dae_id="openclaw", limit=5)

        assert events
        assert events[-1]["event_type"] == "action_performed"
        assert events[-1]["payload"]["action_type"] == "pqn_simulation"

    def test_live_status_combines_registry_and_recent_events(self, tmp_path):
        daemon = get_central_daemon(data_dir=tmp_path / "dae_daemon")
        daemon.start()
        daemon.register_dae(
            DAERegistration(
                dae_id="openclaw",
                dae_name="OpenClaw DAE",
                domain="communication",
            )
        )
        daemon.registry.report_heartbeat("openclaw", {"healthy": True})
        daemon.registry.report_event(
            "openclaw",
            DAEEventType.MESSAGE_IN,
            {"source": "012", "summary": "tail openclaw"},
        )

        observer = get_dae_observer(daemon=daemon)
        snapshot = observer.get_live_status("openclaw", limit=5)

        assert snapshot["registered"] is True
        assert snapshot["dae_id"] == "openclaw"
        assert snapshot["state"] in {"registered", "running"}
        assert snapshot["recent_events"]
        assert snapshot["last_event"]["event_type"] == "message_in"

    def test_follow_events_respects_cursor_and_returns_next_cursor(self, tmp_path):
        daemon = get_central_daemon(data_dir=tmp_path / "dae_daemon")
        daemon.start()
        daemon.register_dae(
            DAERegistration(
                dae_id="openclaw",
                dae_name="OpenClaw DAE",
                domain="communication",
            )
        )
        daemon.registry.report_event(
            "openclaw",
            DAEEventType.MESSAGE_IN,
            {"source": "012", "summary": "first"},
        )
        daemon.registry.report_event(
            "openclaw",
            DAEEventType.ACTION_PERFORMED,
            {"action_type": "launch_requested", "target": "openclaw", "result": "ok"},
        )

        observer = get_dae_observer(daemon=daemon)
        follow = observer.follow_events(dae_id="openclaw", since_sequence=1, limit=5)

        assert follow["since_sequence"] == 1
        assert follow["next_cursor"] >= 2
        assert follow["events"]
        assert all(event["sequence_id"] > 1 for event in follow["events"])
        assert follow["events"][-1]["event_type"] == "action_performed"


class _RejectNestedLock:
    """Use a real Lock, but fail recursive acquisition without hanging a test."""

    def __init__(self):
        self.lock = threading.Lock()

    def __enter__(self):
        if not self.lock.acquire(blocking=False):
            raise RuntimeError("nested event-store lock acquisition")
        return self

    def __exit__(self, *exc):
        self.lock.release()


def _event_store_event(name, sequence_id=0):
    return DAEEvent(
        event_type=DAEEventType.MESSAGE_IN,
        dae_id="collision-test",
        payload={"summary": name},
        actor_id="test-actor",
        timestamp=1234.0,
        event_id=f"event-{name}",
        dedupe_key=f"dedupe-{name}",
        sequence_id=sequence_id,
    )


def _event_store_with_seed(tmp_path):
    store = DAEEventStore(data_dir=tmp_path / "events")
    store._lock = _RejectNestedLock()
    seed = _event_store_event("seed")
    assert store.write(seed) == (True, "ok")
    assert seed.sequence_id == 1
    return store, seed


def _event_store_write_trace(store):
    trace = []
    write_jsonl, write_sqlite = store._write_jsonl, store._write_sqlite

    def jsonl(event):
        trace.append(("jsonl", event.sequence_id))
        return write_jsonl(event)

    def sqlite(event):
        trace.append(("sqlite", event.sequence_id))
        return write_sqlite(event)

    store._write_jsonl, store._write_sqlite = jsonl, sqlite
    return trace


def _event_store_jsonl(store):
    return [json.loads(line) for line in store._jsonl_path.read_text().splitlines()]


def test_event_store_first_collision_recovers_without_nested_lock(tmp_path):
    store, seed = _event_store_with_seed(tmp_path)
    event = _event_store_event("recover", sequence_id=1)
    original = event.to_dict()
    trace = _event_store_write_trace(store)

    assert store.write(event) == (True, "ok")

    expected = dict(original, sequence_id=2)
    assert event.to_dict() == expected
    assert trace == [("jsonl", 1), ("sqlite", 1), ("jsonl", 2), ("sqlite", 2)]
    assert [row.to_dict() for row in store.query()] == [seed.to_dict(), expected]
    # JSONL precedes SQLite: the failed attempt remains, not an atomic dual write.
    assert _event_store_jsonl(store) == [seed.to_dict(), original, expected]
    assert store.verify_parity() == (False, "parity mismatch: jsonl=3 sqlite=2")
    assert not store._lock.lock.locked()


def _assert_event_store_collision_budget(tmp_path, retry, attempts):
    store, seed = _event_store_with_seed(tmp_path)
    event = _event_store_event("exhausted")
    trace = _event_store_write_trace(store)
    next_sequence = store._next_sequence_id
    store._next_sequence_id = lambda: 1
    try:
        result = store.write(event, _retry=retry)
    finally:
        store._next_sequence_id = next_sequence

    assert result == (False, "error: UNIQUE constraint failed: dae_events.sequence_id")
    assert trace == [("jsonl", 1), ("sqlite", 1)] * attempts
    assert [row.to_dict() for row in store.query()] == [seed.to_dict()]
    assert _event_store_jsonl(store) == [seed.to_dict()] + [event.to_dict()] * attempts
    assert store.verify_parity() == (
        False, f"parity mismatch: jsonl={attempts + 1} sqlite=1"
    )
    assert not store._lock.lock.locked()
    following = _event_store_event("after-exhaustion")
    assert store.write(following) == (True, "ok")
    assert following.sequence_id == 2
    assert [row.event_id for row in store.query()] == [seed.event_id, following.event_id]
    assert not store._lock.lock.locked()


def test_event_store_retry_budget_zero_allows_four_attempts(tmp_path):
    _assert_event_store_collision_budget(tmp_path, retry=0, attempts=4)


def test_event_store_retry_budget_one_allows_three_attempts(tmp_path):
    _assert_event_store_collision_budget(tmp_path, retry=1, attempts=3)


def test_event_store_retry_budget_two_allows_two_attempts(tmp_path):
    _assert_event_store_collision_budget(tmp_path, retry=2, attempts=2)


def test_event_store_retry_budget_three_allows_one_attempt(tmp_path):
    _assert_event_store_collision_budget(tmp_path, retry=3, attempts=1)


def test_event_store_retry_budget_above_three_attempts_once(tmp_path):
    _assert_event_store_collision_budget(tmp_path, retry=4, attempts=1)


def test_event_store_generic_sqlite_failure_does_not_retry(tmp_path):
    store, seed = _event_store_with_seed(tmp_path)
    event = _event_store_event("sqlite-failure")
    attempts = []
    write_sqlite = store._write_sqlite

    def fail_write(current):
        attempts.append(current.sequence_id)
        raise sqlite3.OperationalError("injected database failure")

    store._write_sqlite = fail_write
    try:
        result = store.write(event)
    finally:
        store._write_sqlite = write_sqlite

    assert result == (False, "error: injected database failure")
    assert attempts == [2]
    assert [row.to_dict() for row in store.query()] == [seed.to_dict()]
    assert _event_store_jsonl(store) == [seed.to_dict(), event.to_dict()]
    assert store.verify_parity() == (False, "parity mismatch: jsonl=2 sqlite=1")
    assert not store._lock.lock.locked()
    assert store.write(_event_store_event("after-generic-failure")) == (True, "ok")


def test_event_store_other_unique_constraint_does_not_retry(tmp_path):
    store, seed = _event_store_with_seed(tmp_path)
    event = _event_store_event("different-dedupe")
    event.event_id = seed.event_id
    trace = _event_store_write_trace(store)

    assert store.write(event) == (False, "error: UNIQUE constraint failed: dae_events.event_id")

    assert trace == [("jsonl", 2), ("sqlite", 2)]
    assert [row.to_dict() for row in store.query()] == [seed.to_dict()]
    assert _event_store_jsonl(store) == [seed.to_dict(), event.to_dict()]
    assert not store._lock.lock.locked()


def test_event_store_exact_duplicate_preserves_both_stores(tmp_path):
    store, event = _event_store_with_seed(tmp_path)
    original = event.to_dict()
    jsonl_before = store._jsonl_path.read_bytes()
    sqlite_before = [row.to_dict() for row in store.query()]
    trace = _event_store_write_trace(store)

    assert store.write(event) == (False, f"duplicate: {event.dedupe_key}")

    assert event.to_dict() == original
    assert trace == []
    assert store._jsonl_path.read_bytes() == jsonl_before
    assert [row.to_dict() for row in store.query()] == sqlite_before
    assert store.verify_parity() == (True, "parity ok: 1 events")
    assert not store._lock.lock.locked()


# Existing-gap characterization, not acceptance of a repaired persistence contract.
# Future repairs must revise these explicit observations with new source evidence.
def test_event_store_characterizes_jsonl_failure_before_sqlite(tmp_path):
    """A failed append stops SQLite, but consumes a local sequence number."""
    store, seed = _event_store_with_seed(tmp_path)
    event = _event_store_event("append-failure")
    before = store._jsonl_path.read_bytes()
    write_jsonl = store._write_jsonl

    def fail_append(current):
        raise OSError("injected JSONL append failure")

    store._write_jsonl = fail_append
    trace = _event_store_write_trace(store)
    try:
        result = store.write(event)
    finally:
        store._write_jsonl = write_jsonl

    assert result == (False, "error: injected JSONL append failure")
    assert trace == [("jsonl", 2)]
    assert store._jsonl_path.read_bytes() == before
    assert [row.to_dict() for row in store.query()] == [seed.to_dict()]
    assert not store._lock.lock.locked()
    following = _event_store_event("after-append-failure")
    assert store.write(following) == (True, "ok")
    assert [row.sequence_id for row in store.query()] == [1, 3]


def test_event_store_characterizes_jsonl_only_reopen_retry(tmp_path):
    """Reopening does not replay the JSONL-only attempt; retry appends again."""
    store, seed = _event_store_with_seed(tmp_path)
    event = _event_store_event("jsonl-only")
    write_sqlite = store._write_sqlite

    def fail_sqlite(current):
        raise sqlite3.OperationalError("injected pre-commit failure")

    store._write_sqlite = fail_sqlite
    try:
        assert store.write(event) == (False, "error: injected pre-commit failure")
    finally:
        store._write_sqlite = write_sqlite

    attempt_bytes = store._jsonl_path.read_bytes()
    assert _event_store_jsonl(store) == [seed.to_dict(), event.to_dict()]
    reopened = DAEEventStore(data_dir=store._data_dir)
    assert reopened._jsonl_path.read_bytes() == attempt_bytes
    assert [row.to_dict() for row in reopened.query()] == [seed.to_dict()]
    assert reopened.get_latest_sequence_id() == 1
    assert reopened.write(event) == (True, "ok")
    assert [row.to_dict() for row in reopened.query()] == [seed.to_dict(), event.to_dict()]
    assert _event_store_jsonl(reopened) == [seed.to_dict(), event.to_dict(), event.to_dict()]
    assert reopened.verify_parity() == (False, "parity mismatch: jsonl=3 sqlite=2")


def test_event_store_characterizes_post_commit_error_and_replay(tmp_path):
    """False is not proof of rollback when the response fails after commit."""
    store, seed = _event_store_with_seed(tmp_path)
    event = _event_store_event("committed-error")
    write_sqlite = store._write_sqlite

    def commit_then_fail(current):
        write_sqlite(current)
        raise RuntimeError("injected response failure after SQLite commit")

    store._write_sqlite = commit_then_fail
    try:
        assert store.write(event) == (
            False, "error: injected response failure after SQLite commit"
        )
    finally:
        store._write_sqlite = write_sqlite

    expected = [seed.to_dict(), event.to_dict()]
    assert [row.to_dict() for row in store.query()] == expected
    assert _event_store_jsonl(store) == expected
    before = store._jsonl_path.read_bytes()
    reopened = DAEEventStore(data_dir=store._data_dir)
    assert reopened.write(event) == (False, f"duplicate: {event.dedupe_key}")
    assert [row.to_dict() for row in reopened.query()] == expected
    assert reopened._jsonl_path.read_bytes() == before
    assert reopened.verify_parity() == (True, "parity ok: 2 events")


def test_event_store_characterizes_conflicting_dedupe_unclassified(tmp_path):
    """Exact and conflicting repeats currently receive the same duplicate result."""
    store, seed = _event_store_with_seed(tmp_path)
    exact = DAEEvent.from_dict(seed.to_dict())
    conflict = _event_store_event("conflicting-identity")
    conflict.dedupe_key = seed.dedupe_key
    conflict.actor_id = "different-actor"
    before = store._jsonl_path.read_bytes()
    trace = _event_store_write_trace(store)

    outcomes = [store.write(exact), store.write(conflict)]

    assert outcomes == [(False, f"duplicate: {seed.dedupe_key}")] * 2
    assert conflict.sequence_id == 0
    assert trace == []
    assert [row.to_dict() for row in store.query()] == [seed.to_dict()]
    assert store._jsonl_path.read_bytes() == before


def test_event_store_characterizes_count_only_parity_false_positive(tmp_path):
    """Count parity currently accepts malformed or unrelated one-line content."""
    store, seed = _event_store_with_seed(tmp_path)
    unrelated = _event_store_event("unrelated", sequence_id=99).to_dict()
    for content in ("not-json\n", json.dumps(unrelated) + "\n"):
        store._jsonl_path.write_text(content, encoding="utf-8")
        assert store.verify_parity() == (True, "parity ok: 1 events")
        assert [row.to_dict() for row in store.query()] == [seed.to_dict()]

    store._jsonl_path.write_text("not-json\nsecond-line\n", encoding="utf-8")
    assert store.verify_parity() == (False, "parity mismatch: jsonl=2 sqlite=1")


def test_event_store_characterizes_returned_false_still_notifies_emergency(tmp_path):
    """A returned False preserves volatile callbacks, not a durable ack."""
    attempted, failed_listener, emergency, detach = [], [], [], []

    def failed_write(event):
        attempted.append(event)
        return False, "error: injected unavailable store"

    def listener_error(event):
        failed_listener.append(event)
        raise RuntimeError("injected listener failure")

    report = object()

    def evaluate(event):
        emergency.append(event)
        return report

    registry = DAERegistry(SimpleNamespace(write=failed_write))
    assert registry.register(DAERegistration("security-test", "Test", "infrastructure"))
    target = SimpleNamespace(
        killswitch=SimpleNamespace(evaluate_security_event=evaluate),
        _execute_detach=detach.append,
    )
    registry.add_listener(listener_error)
    registry.add_listener(lambda event: CentralDAEmon._on_event(target, event))
    payload = {"reason": "synthetic test", "severity": "critical"}

    assert registry.report_event("security-test", DAEEventType.SECURITY_VIOLATION, payload)

    assert len(attempted) == 2  # Registration and security report both failed persistence.
    assert failed_listener == emergency == [attempted[-1]]
    assert emergency[0].payload == payload
    assert emergency[0].sequence_id == 0
    assert detach == [report]  # Inert spy only: no real killswitch or daemon instance.
    assert list(tmp_path.iterdir()) == []


def test_event_store_characterizes_raised_failure_skips_registry_listeners(tmp_path):
    """An exception from the store escapes before volatile listeners run."""
    store = SimpleNamespace(write=lambda event: (True, "ok"))
    registry = DAERegistry(store)
    assert registry.register(DAERegistration("raised-test", "Test", "infrastructure"))
    attempted, notified = [], []
    failure = OSError("injected raised store failure")

    def raise_write(event):
        attempted.append(event)
        raise failure

    store.write = raise_write
    registry.add_listener(notified.append)
    try:
        registry.report_event("raised-test", DAEEventType.SECURITY_VIOLATION, {})
    except OSError as observed:
        assert observed is failure
    else:
        raise AssertionError("Expected the exact store exception to escape")

    assert len(attempted) == 1
    assert attempted[0].event_type == DAEEventType.SECURITY_VIOLATION
    assert notified == []
    assert list(tmp_path.iterdir()) == []


# Focused noncreating runtime-lookup acceptance; no daemon lifecycle execution.
from unittest.mock import Mock


class _ObserverLookupLock(_RejectNestedLock):
    def __init__(self):
        super().__init__()
        self.entries = self.exits = 0

    def __enter__(self):
        super().__enter__()
        self.entries += 1
        return self

    def __exit__(self, *exc):
        super().__exit__(*exc)
        self.exits += 1


def _observer_runtime_daemon():
    record = {"sequence_id": 7, "event_id": "synthetic-event", "event_type": "action_performed",
              "dae_id": "observer-test", "actor_id": "fixture", "timestamp": 123.0,
              "payload": {"summary": "synthetic action"}}
    event = SimpleNamespace(**record)
    event.event_type = DAEEventType.ACTION_PERFORMED
    registration = SimpleNamespace(dae_name="Synthetic DAE", domain="infrastructure",
        state=SimpleNamespace(value="registered"), enabled=True, pid=None,
        heartbeat_interval_sec=30.0, last_heartbeat=0)
    daemon = SimpleNamespace(registry=SimpleNamespace(get=Mock(return_value=registration)),
        event_store=SimpleNamespace(query_recent=Mock(return_value=[event]),
                                    get_latest_sequence_id=Mock(return_value=9)))
    return daemon, record


def _observer_runtime_fixture(monkeypatch):
    from modules.infrastructure.dae_daemon.src import dae_launch_broker as broker
    from modules.infrastructure.dae_daemon.src import dae_observer as owner

    lock = _ObserverLookupLock()
    effects = []
    for target, name in ((CentralDAEmon, "__init__"), (DAEEventStore, "__init__"),
                         (DAERegistry, "__init__"), (broker.DAELaunchBroker, "__init__"),
                         (owner.DAEObserver, "__init__"), (threading.Thread, "__init__"),
                         (threading.Thread, "start")):
        spy = Mock(name=target.__name__ + "." + name,
                   side_effect=AssertionError("real runtime effect forbidden"))
        monkeypatch.setattr(target, name, spy)
        effects.append(spy)
    creator = Mock(wraps=broker.get_dae_launch_broker)
    monkeypatch.setattr(broker, "get_dae_launch_broker", creator)
    monkeypatch.setattr(broker, "_broker_lock", lock)
    monkeypatch.setattr(broker, "_launch_broker", None)
    observer = object.__new__(owner.DAEObserver)
    observer._daemon, record = _observer_runtime_daemon()
    return SimpleNamespace(broker=broker, observer=observer, lock=lock, effects=effects,
                           creator=creator, record=record)


def _observer_runtime_projection(state, snapshot, runtime):
    assert snapshot == {"registered": True, "dae_id": "observer-test",
        "dae_name": "Synthetic DAE", "domain": "infrastructure", "state": "registered",
        "enabled": True, "pid": None, "heartbeat_interval_sec": 30.0,
        "last_heartbeat_age_sec": None, "runtime": runtime, "latest_sequence_id": 9,
        "next_cursor": 7, "recent_events": [state.record], "last_event": state.record,
        "last_action": state.record}
    state.observer._daemon.registry.get.assert_called_once_with("observer-test")
    state.observer._daemon.event_store.query_recent.assert_called_once_with(
        dae_id="observer-test", event_type=None, limit=3)
    state.observer._daemon.event_store.get_latest_sequence_id.assert_called_once_with()


def _observer_runtime_no_effects(state):
    assert [spy.call_count for spy in state.effects] == [0] * len(state.effects)
    assert state.lock.entries == state.lock.exits
    assert not state.lock.lock.locked()


def test_observer_runtime_absent_never_creates_broker(monkeypatch):
    state = _observer_runtime_fixture(monkeypatch)
    snapshot = state.observer.get_live_status("observer-test", limit=3)
    _observer_runtime_projection(state, snapshot, {})
    assert state.broker._launch_broker is None
    assert (state.creator.call_count, [spy.call_count for spy in state.effects]) == (
        0, [0] * len(state.effects))
    _observer_runtime_no_effects(state)


def test_observer_runtime_present_preserves_status_outside_singleton_lock(monkeypatch):
    state = _observer_runtime_fixture(monkeypatch)
    runtime = {"registered": True, "thread_alive": True, "marker": "preserved"}

    def status(dae_id):
        assert dae_id == "observer-test" and not state.lock.lock.locked()
        with state.lock:
            return runtime

    status_spy = Mock(side_effect=status)
    current = SimpleNamespace(get_runtime_status=status_spy)
    state.broker._launch_broker = current
    snapshot = state.observer.get_live_status("observer-test", limit=3)
    _observer_runtime_projection(state, snapshot, runtime)
    status_spy.assert_called_once_with("observer-test")
    assert state.broker._launch_broker is current and state.lock.entries == 2
    _observer_runtime_no_effects(state)


def test_observer_runtime_status_error_does_not_retry_or_create(monkeypatch):
    state = _observer_runtime_fixture(monkeypatch)
    status = Mock(side_effect=RuntimeError("synthetic status failure"))
    current = SimpleNamespace(get_runtime_status=status)
    state.broker._launch_broker = current
    assert state.observer._get_runtime_status("observer-test") == {}
    status.assert_called_once_with("observer-test")
    assert state.broker._launch_broker is current and state.lock.entries == 1
    _observer_runtime_no_effects(state)


def test_observer_runtime_lookup_observes_each_current_singleton(monkeypatch):
    state = _observer_runtime_fixture(monkeypatch)
    first = SimpleNamespace(get_runtime_status=Mock(return_value={"marker": "A"}))
    second = SimpleNamespace(get_runtime_status=Mock(return_value={"marker": "B"}))
    for current, expected in ((None, {}), (first, {"marker": "A"}),
                              (second, {"marker": "B"}), (None, {})):
        state.broker._launch_broker = current
        assert state.observer._get_runtime_status("observer-test") == expected
        assert state.broker._launch_broker is current
    first.get_runtime_status.assert_called_once_with("observer-test")
    second.get_runtime_status.assert_called_once_with("observer-test")
    assert state.creator.call_count == 0 and state.lock.entries == 4
    _observer_runtime_no_effects(state)


def test_observer_runtime_existing_accessor_is_noncreating(monkeypatch):
    state = _observer_runtime_fixture(monkeypatch)
    accessor = getattr(state.broker, "get_existing_dae_launch_broker", None)
    assert callable(accessor), "noncreating accessor is not implemented"
    assert accessor() is None
    current = SimpleNamespace(get_runtime_status=Mock(), stop=Mock())
    state.broker._launch_broker = current
    assert accessor() is current and state.broker._launch_broker is current
    current.get_runtime_status.assert_not_called()
    current.stop.assert_not_called()
    assert state.creator.call_count == 0 and state.lock.entries == 2
    _observer_runtime_no_effects(state)


def test_observer_runtime_creator_getter_preserves_singleton_contract(monkeypatch):
    state = _observer_runtime_fixture(monkeypatch)
    first, second, expected = object(), object(), object()
    received = []

    def factory(daemon):
        assert state.lock.lock.locked()
        received.append(daemon)
        return expected

    monkeypatch.setattr(state.broker, "DAELaunchBroker", factory)
    assert state.broker.get_dae_launch_broker(daemon=first) is expected
    assert state.broker.get_dae_launch_broker(daemon=second) is expected
    assert received == [first] and state.broker._launch_broker is expected
    assert state.lock.entries == 2
    _observer_runtime_no_effects(state)


def test_observer_runtime_creator_failure_releases_lock_without_publication(monkeypatch):
    state = _observer_runtime_fixture(monkeypatch)
    failure, expected = RuntimeError("synthetic creator failure"), object()
    factory = Mock(side_effect=[failure, expected])
    monkeypatch.setattr(state.broker, "DAELaunchBroker", factory)
    try:
        state.broker.get_dae_launch_broker()
    except RuntimeError as observed:
        assert observed is failure
    else:
        raise AssertionError("creator failure must propagate")
    assert state.broker._launch_broker is None and state.lock.entries == 1
    _observer_runtime_no_effects(state)
    assert state.broker.get_dae_launch_broker() is expected
    assert state.broker._launch_broker is expected and factory.call_count == 2
    assert state.lock.entries == 2
    _observer_runtime_no_effects(state)


def test_observer_runtime_lookup_error_does_not_retry_or_create(monkeypatch):
    state = _observer_runtime_fixture(monkeypatch)
    current = SimpleNamespace(get_runtime_status=Mock())
    state.broker._launch_broker = current
    accessor = Mock(side_effect=RuntimeError("synthetic lookup failure"))
    creator = Mock(side_effect=AssertionError("creating getter forbidden"))
    monkeypatch.setattr(state.broker, "get_existing_dae_launch_broker", accessor, raising=False)
    monkeypatch.setattr(state.broker, "get_dae_launch_broker", creator)
    assert state.observer._get_runtime_status("observer-test") == {}
    accessor.assert_called_once_with()
    creator.assert_not_called()
    current.get_runtime_status.assert_not_called()
    assert state.broker._launch_broker is current
    _observer_runtime_no_effects(state)
