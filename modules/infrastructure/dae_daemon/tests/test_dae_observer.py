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
