"""DAE observer read-surface tests."""

import json
import sqlite3
import threading

from modules.infrastructure.dae_daemon.src.dae_daemon import (
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
