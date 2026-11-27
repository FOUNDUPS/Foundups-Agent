"""Offline watcher acceptance and real-process checkpoint/crash controls."""

import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src.reddog_relay_google_docs import GoogleDocsRelayReader
from modules.communication.moltbot_bridge.src.reddog_relay_poll_store import RelayPollStore
from modules.communication.moltbot_bridge.src.reddog_relay_watcher import (
    EffectProof, RelayBindings, RelayMessage, RelaySnapshot, RelaySource,
    RelayUnavailable, RelayWatcher,
)
from modules.infrastructure.database.src.db_manager import DatabaseManager


ROOT = Path(__file__).resolve().parents[4]
SOURCE = RelaySource("google_docs", "fixture-account", "fixture-document", "little-dog", "codex-target")


def message(mid="message-1", payload="private-payload-never-persisted", **kw):
    return RelayMessage(mid, kw.get("sender", "work"), kw.get("recipient", "little-dog"), kw.get("kind", "request"), payload)


class FakeProvider:
    def __init__(self):
        self.messages, self.calls, self.reads = (), [], []
        self.complete, self.allowed, self.revision = True, True, "revision-1"
        self.read_error = None
        self.outcomes, self.recovered = {}, {}

    def read(self, source, watermark, *, timeout_seconds):
        assert 0 < timeout_seconds <= 60
        self.reads.append(watermark)
        if self.read_error:
            raise self.read_error
        return RelaySnapshot(source.key, self.revision, self.messages, self.complete)

    def admit(self, source, msg):
        return self.allowed

    def perform(self, source, msg, phase, op, attempt, *, timeout_seconds):
        self.calls.append((msg.message_id, phase, op, attempt))
        outcome = self.outcomes.get(phase, "APPLIED")
        if isinstance(outcome, Exception):
            raise outcome
        return EffectProof(op, attempt, outcome, f"proof-{attempt}-{op}")

    def reconcile(self, source, msg, phase, op, attempt, *, timeout_seconds):
        outcome = self.recovered.get(phase, "UNKNOWN")
        return EffectProof(op, attempt, outcome, f"recovered-{attempt}-{op}")

    def bindings(self):
        return RelayBindings(self.read, self.admit, self.perform, self.reconcile, 5)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDUPS_DB_ENGINE", "sqlite")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "relay.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    DatabaseManager.reset_for_tests()
    db = DatabaseManager()
    store = RelayPollStore(db, repo_root=ROOT, allowed_root=tmp_path)
    provider, now = FakeProvider(), [0.0]
    worker = RelayWatcher(store, SOURCE, provider.bindings(), clock=lambda: now[0])
    yield SimpleNamespace(db=db, store=store, provider=provider, now=now, worker=worker, root=tmp_path)
    DatabaseManager.reset_for_tests()


def poll(s):
    s.now[0] = s.store.checkpoint(SOURCE.key)["next_due"]
    return s.worker.tick()


def begin(s, messages=()):
    s.provider.messages = messages
    assert s.worker.tick()["status"] == "WAITING"
    assert s.provider.reads == []
    return poll(s)


def test_durable_initial_wait_exact_backoff_and_cap(setup):
    s = setup
    result = begin(s)
    observed = [60, result["delay_seconds"]]
    for _ in range(6):
        observed.append(poll(s)["delay_seconds"])
    assert observed == [60, 120, 240, 480, 960, 1920, 3600, 3600]
    assert s.store.checkpoint(SOURCE.key)["observed_at"] == s.now[0]


def test_duplicate_reorder_and_own_ack_do_not_wake_or_repeat_effects(setup):
    s = setup
    assert begin(s, (message("b"), message("a")))["new_activity"] is True
    assert len(s.provider.calls) == 4
    s.provider.messages = (message("a"), message("b"), message("a"), message("ack", sender="little-dog", kind="ack"))
    result = poll(s)
    assert result["new_activity"] is False and result["delay_seconds"] == 120
    assert len(s.provider.calls) == 4
    s.provider.messages += (message("c"),)
    assert poll(s)["delay_seconds"] == 60
    assert len(s.provider.calls) == 6


@pytest.mark.parametrize("failure", [RelayUnavailable("AUTH_REQUIRED", 300), RuntimeError("private-error-text")])
def test_read_failure_preserves_cursor_interval_and_observation_time(setup, failure):
    s = setup
    begin(s)
    before = s.store.checkpoint(SOURCE.key)
    s.provider.read_error = failure
    result = poll(s)
    after = s.store.checkpoint(SOURCE.key)
    assert result["status"].startswith("BLOCKED")
    assert (after["watermark"], after["delay"], after["observed_at"]) == (before["watermark"], before["delay"], before["observed_at"])
    assert after["last_attempt_at"] > before["last_attempt_at"]
    assert after["last_error"] != "private-error-text"


def test_incomplete_snapshot_never_advances_or_dispatches(setup):
    s = setup
    s.provider.complete = False
    assert begin(s, (message(),))["status"] == "BLOCKED_OBSERVATION"
    assert s.store.checkpoint(SOURCE.key)["watermark"] == ""
    assert s.store.checkpoint(SOURCE.key)["observed_at"] is None
    assert not s.provider.calls


def test_changed_identity_rolls_back_entire_batch(setup):
    s = setup
    begin(s, (message(),))
    s.provider.messages = (message("new"), message(payload="altered"))
    s.provider.revision = "new-revision"
    assert poll(s)["status"] == "BLOCKED_OBSERVATION"
    assert s.store.checkpoint(SOURCE.key)["watermark"] == "revision-1"
    assert s.db.execute_query("SELECT COUNT(*) n FROM modules_reddog_relay_messages")[0]["n"] == 1
    assert len(s.provider.calls) == 2


def test_atomic_ingestion_rolls_back_cursor_message_and_operations(setup):
    s = setup
    s.db.execute_write("""CREATE TRIGGER abort_forward BEFORE INSERT ON modules_reddog_relay_operations
        WHEN NEW.phase='forward' BEGIN SELECT RAISE(ABORT, 'fixture rollback'); END""")
    assert begin(s, (message(),))["status"] == "BLOCKED_OBSERVATION"
    for table in ("messages", "operations"):
        assert s.db.execute_query(f"SELECT COUNT(*) n FROM modules_reddog_relay_{table}")[0]["n"] == 0
    assert s.store.checkpoint(SOURCE.key)["watermark"] == ""
    assert not s.provider.calls


def test_unknown_effect_is_not_replayed_and_new_activity_still_resets(setup):
    s = setup
    s.provider.outcomes["forward"] = RuntimeError("uncertain")
    assert begin(s, (message(),))["status"] == "BLOCKED_EFFECT"
    assert poll(s)["delay_seconds"] == 120
    assert len(s.provider.calls) == 2
    s.provider.messages += (message("new"),)
    result = poll(s)
    assert result["delay_seconds"] == 60 and result["new_activity"] is True
    assert sum(c[0] == "message-1" and c[1] == "forward" for c in s.provider.calls) == 1


def test_missing_pending_source_blocks_without_dropping_operations(setup):
    s = setup
    s.provider.outcomes["forward"] = "UNKNOWN"
    begin(s, (message(),))
    s.provider.messages = ()
    assert "SOURCE_MISSING_OR_CHANGED" in poll(s)["blockers"]
    assert len(s.store.pending(SOURCE.key)) == 1
    assert len(s.provider.calls) == 2


def test_authoritative_applied_recovery_does_not_call_effect_again(setup):
    s = setup
    s.provider.outcomes["forward"] = "UNKNOWN"
    begin(s, (message(),))
    s.provider.recovered["forward"] = "APPLIED"
    assert poll(s)["status"] == "OBSERVED"
    assert not s.store.pending(SOURCE.key)
    assert len(s.provider.calls) == 2


def test_terminal_negative_proof_permits_one_new_fenced_attempt(setup):
    s = setup
    s.provider.outcomes["forward"] = "UNKNOWN"
    begin(s, (message(),))
    s.provider.outcomes["forward"] = "APPLIED"
    s.provider.recovered["forward"] = "TERMINAL_NOT_APPLIED"
    assert poll(s)["status"] == "OBSERVED"
    calls = [c for c in s.provider.calls if c[1] == "forward"]
    assert len(calls) == 2 and calls[0][2] == calls[1][2]
    assert [c[3] for c in calls] == [1, 2]


def test_wrong_attempt_or_operation_proof_cannot_authorize_replay(setup):
    s = setup
    s.provider.outcomes["forward"] = "UNKNOWN"
    begin(s, (message(),))
    bad = lambda source, msg, phase, op, attempt, **kw: EffectProof(op, 0, "TERMINAL_NOT_APPLIED", "stale")
    s.worker.bindings = RelayBindings(s.provider.read, s.provider.admit, s.provider.perform, bad, 5)
    assert poll(s)["status"] == "BLOCKED_EFFECT"
    assert len(s.provider.calls) == 2


def test_source_binding_cannot_silently_change_destination(setup):
    s = setup
    begin(s)
    altered = RelaySource("google_docs", "fixture-account", "fixture-document", "little-dog", "other-target")
    worker = RelayWatcher(s.store, altered, s.provider.bindings(), clock=lambda: s.now[0])
    with pytest.raises(ValueError, match="source_binding_changed"):
        worker.tick()


def test_no_default_connector_or_raw_body_persistence(setup):
    s = setup
    missing = RelayWatcher(s.store, SOURCE, None)
    assert missing.tick()["status"] == "BLOCKED_CONNECTOR_BINDINGS"
    begin(s, (message(),))
    rows = s.db.execute_query("SELECT * FROM modules_reddog_relay_messages")
    assert "payload" not in rows[0]
    assert "private-payload-never-persisted" not in str(rows)


def test_clock_rollback_is_blocked_without_new_observation(setup):
    s = setup
    begin(s)
    s.now[0] = 10
    assert s.worker.tick()["status"] == "BLOCKED_CLOCK_ROLLBACK"
    assert s.store.checkpoint(SOURCE.key)["observed_at"] == 60


@pytest.mark.parametrize("failure", [None, RelayUnavailable("RETRY"), RuntimeError("private")])
def test_clock_rollback_during_read_preserves_checkpoint_and_blocks_effects(setup, failure):
    s = setup
    begin(s)
    before = s.store.checkpoint(SOURCE.key)
    s.provider.messages = (message(),)
    read = s.provider.read
    def backwards(*args, **kwargs):
        s.now[0] -= 1
        if failure:
            raise failure
        return read(*args, **kwargs)
    s.provider.read = backwards
    s.worker.bindings = s.provider.bindings()
    result = poll(s)
    assert result["status"] == "BLOCKED_CLOCK_ROLLBACK" and result["poll_performed"]
    after = s.store.checkpoint(SOURCE.key)
    for field in ("watermark", "delay", "next_due", "observed_at", "last_attempt_at"):
        assert after[field] == before[field]
    assert not s.provider.calls and not s.store.pending(SOURCE.key)


def test_bounded_run_waits_and_stops_in_existing_calling_thread(setup):
    s = setup
    class Stop:
        def is_set(self):
            return False
        def wait(self, seconds):
            s.now[0] += seconds
            return False
    result = s.worker.run(Stop(), max_checks=3)
    assert result["status"] == "CHECK_LIMIT"
    assert [x["delay_seconds"] for x in result["checks"]] == [120, 240, 480]
    assert s.now[0] == 420


def test_native_docs_reader_binds_exact_source_revision_and_all_tab_content():
    calls = []
    document = {"documentId": SOURCE.container, "revisionId": "opaque-revision",
                "tabs": [{"tabId": "t.0", "body": {"content": []}}]}
    def read(**kw):
        calls.append(kw)
        return {"structuredContent": document, "isError": False}
    decoded = []
    def decode(value):
        decoded.append(value)
        return (message(),)
    reader = GoogleDocsRelayReader(read, decode)
    result = reader(SOURCE, "opaque-revision", timeout_seconds=5)
    assert result.complete is True and result.source_key == SOURCE.key
    assert result.messages == (message(),) and decoded == [document]
    assert calls == [{"document_id": SOURCE.container, "timeout_seconds": 5}]


@pytest.mark.parametrize("response", [
    {"isError": True}, {},
    {"documentId": "wrong", "revisionId": "r", "tabs": []},
    {"documentId": SOURCE.container, "revisionId": "r", "tabs": []},
    {"documentId": SOURCE.container, "revisionId": "r", "tabs": [{"tabId": "t.0"}]},
])
def test_native_docs_reader_refuses_partial_or_unbound_responses(response):
    def decode(document):
        pytest.fail("must not decode invalid document read")
    with pytest.raises(RelayUnavailable):
        GoogleDocsRelayReader(lambda **kw: response, decode)(SOURCE, "", timeout_seconds=5)


@pytest.mark.parametrize("info", [{"engine": "postgres"}, {"engine": "sqlite", "db_path": ":memory:"}, {"engine": "sqlite", "db_path": "relative.db"}])
def test_unqualified_store_backend_is_refused(info, tmp_path):
    with pytest.raises(ValueError, match="explicit_local_sqlite"):
        RelayPollStore(SimpleNamespace(backend_info=lambda: info), repo_root=ROOT, allowed_root=tmp_path)


def test_hard_link_alias_is_refused_before_provider_read(setup):
    s = setup
    os.link(s.root / "relay.db", s.root / "alias.db")
    try:
        with pytest.raises(ValueError, match="identity_changed_or_linked"):
            s.worker.tick()
        assert not s.provider.reads
        with pytest.raises(ValueError, match="identity_changed_or_linked"):
            RelayPollStore(s.db, repo_root=ROOT, allowed_root=s.root)
    finally:
        (s.root / "alias.db").unlink()


def test_database_replacement_is_refused_before_provider_read(setup):
    s = setup
    (s.root / "relay.db").rename(s.root / "preserved.db")
    (s.root / "relay.db").write_bytes(b"")
    with pytest.raises(ValueError, match="identity_changed_or_linked"):
        s.worker.tick()
    assert not s.provider.reads


def _process_probe(mode, root):
    """Fresh Python process, actual SQLite, actual runtime lock; synthetic provider."""
    root = Path(root)
    os.environ["FOUNDUPS_DB_ENGINE"] = "sqlite"
    os.environ["FOUNDUPS_DB_PATH"] = str(root / "relay.db")
    os.environ.pop("DATABASE_URL", None)
    DatabaseManager.reset_for_tests()
    store = RelayPollStore(DatabaseManager(), repo_root=ROOT, allowed_root=root)
    provider = FakeProvider()
    provider.messages = (message(),)
    effect_path = root / "synthetic-provider.db"
    with sqlite3.connect(effect_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS effects (op TEXT PRIMARY KEY, attempt INTEGER)")

    def perform(source, msg, phase, op, attempt, **kw):
        with sqlite3.connect(effect_path) as conn:
            conn.execute("INSERT INTO effects VALUES (?, ?)", (op, attempt))
        if mode == "after_effect" and phase == "forward":
            os._exit(72)
        return EffectProof(op, attempt, "APPLIED", "provider-" + op)

    def reconcile(source, msg, phase, op, attempt, **kw):
        with sqlite3.connect(effect_path) as conn:
            row = conn.execute("SELECT attempt FROM effects WHERE op=?", (op,)).fetchone()
        return EffectProof(op, attempt, "APPLIED" if row else "TERMINAL_NOT_APPLIED", "recovery-" + op)

    if mode == "before_effect":
        start = store.start_operation
        def die_after_claim(op):
            attempt = start(op)
            if store.operation(op)["phase"] == "forward":
                os._exit(71)
            return attempt
        store.start_operation = die_after_claim
    if mode == "hold":
        read = provider.read
        def hold_read(*args, **kw):
            (root / "held").write_text("locked")
            deadline = time.monotonic() + 10
            while not (root / "release").exists():
                if time.monotonic() > deadline:
                    raise TimeoutError("test release missing")
                time.sleep(0.02)
            return read(*args, **kw)
        provider.read = hold_read
    clock = 120 if mode == "resume" else 60
    worker = RelayWatcher(store, SOURCE, RelayBindings(provider.read, provider.admit, perform, reconcile, 5), clock=lambda: clock)
    result = worker.tick()
    assert result["status"] == "OBSERVED", result


def _child(mode, root):
    return [sys.executable, "-B", "-m", "modules.communication.moltbot_bridge.tests.test_reddog_relay_watcher", mode, str(root)]


@pytest.mark.parametrize("mode,exit_code", [("before_effect", 71), ("after_effect", 72)])
def test_fresh_process_recovers_crash_windows_without_duplicate_effect(setup, mode, exit_code):
    s = setup
    assert s.worker.tick()["status"] == "WAITING"
    crashed = subprocess.run(_child(mode, s.root), cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert crashed.returncode == exit_code, crashed.stderr
    state = s.store.checkpoint(SOURCE.key)
    assert state["watermark"] == "revision-1" and state["next_due"] == 120
    pending = s.store.pending(SOURCE.key)
    assert len(pending) == 1 and pending[0]["state"] == "INFLIGHT"
    resumed = subprocess.run(_child("resume", s.root), cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert resumed.returncode == 0, resumed.stderr
    assert not s.store.pending(SOURCE.key)
    with sqlite3.connect(s.root / "synthetic-provider.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM effects").fetchone()[0] == 2


def test_two_processes_cannot_poll_same_binding_concurrently(setup):
    s = setup
    assert s.worker.tick()["status"] == "WAITING"
    child = subprocess.Popen(_child("hold", s.root), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 10
        while not (s.root / "held").exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert (s.root / "held").exists()
        s.now[0] = 60
        assert s.worker.tick()["status"] == "BLOCKED_WORKER_OWNERSHIP"
        assert not s.provider.reads
        (s.root / "release").write_text("release")
        out, err = child.communicate(timeout=15)
        assert child.returncode == 0, out + err
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=10)


if __name__ == "__main__":
    _process_probe(sys.argv[1], sys.argv[2])
