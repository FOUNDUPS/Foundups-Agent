"""Runtime launch broker tests."""

import threading
import time
from types import SimpleNamespace

import pytest

from modules.infrastructure.dae_daemon.src.dae_daemon import (
    get_central_daemon,
    reset_central_daemon,
)
from modules.infrastructure.dae_daemon.src.dae_launch_broker import (
    DAELaunchBroker,
    DAELaunchSpec,
    get_dae_launch_broker,
    reset_dae_launch_broker,
)
from modules.infrastructure.dae_daemon.src.schemas import DAEEventType, DAEState


class TestDAELaunchBroker:
    def setup_method(self):
        reset_dae_launch_broker()
        reset_central_daemon()

    def teardown_method(self):
        reset_dae_launch_broker()
        reset_central_daemon()

    def test_start_one_shot_dae(self, tmp_path):
        daemon = get_central_daemon(data_dir=tmp_path / "dae_daemon")
        daemon.start()
        broker = get_dae_launch_broker(daemon=daemon)

        calls = []

        def one_shot(result_text="ok"):
            calls.append(result_text)
            return {"status": "completed", "message": result_text}

        broker.register_launch_spec(
            DAELaunchSpec(
                dae_id="unit_test_dae",
                dae_name="Unit Test DAE",
                domain="tests",
                start_callable=one_shot,
            )
        )

        result = broker.start_dae(
            "unit_test_dae",
            actor_id="012",
            launch_kwargs={"result_text": "launched"},
        )
        assert result["status"] == "starting"

        deadline = time.time() + 2.0
        status = {}
        while time.time() < deadline:
            status = broker.get_status("unit_test_dae")
            if status["state"] == "stopped":
                break
            time.sleep(0.05)

        assert status["state"] == "stopped"
        assert status["running"] is False
        assert status["run_count"] == 1
        assert status["last_result_summary"] == "completed"
        assert calls == ["launched"]

    def test_launch_failure_sets_crashed_state(self, tmp_path):
        daemon = get_central_daemon(data_dir=tmp_path / "dae_daemon")
        daemon.start()
        broker = get_dae_launch_broker(daemon=daemon)

        def boom():
            raise RuntimeError("launch failure")

        broker.register_launch_spec(
            DAELaunchSpec(
                dae_id="crashy_dae",
                dae_name="Crashy DAE",
                domain="tests",
                start_callable=boom,
            )
        )

        broker.start_dae("crashy_dae", actor_id="012")

        deadline = time.time() + 2.0
        status = {}
        while time.time() < deadline:
            status = broker.get_status("crashy_dae")
            if status["state"] == "crashed":
                break
            time.sleep(0.05)

        assert status["state"] == "crashed"
        assert "launch failure" in status["last_error"]

    def test_list_and_stop_supported_dae(self, tmp_path):
        daemon = get_central_daemon(data_dir=tmp_path / "dae_daemon")
        daemon.start()
        broker = get_dae_launch_broker(daemon=daemon)

        stop_event = threading.Event()

        def long_running():
            while not stop_event.is_set():
                time.sleep(0.05)
            return {"status": "stopped"}

        def stop_callable():
            stop_event.set()

        broker.register_launch_spec(
            DAELaunchSpec(
                dae_id="loop_dae",
                dae_name="Loop DAE",
                domain="tests",
                start_callable=long_running,
                stop_callable=stop_callable,
            )
        )

        launchable = broker.list_launchable()
        assert "loop_dae" in launchable
        assert launchable["loop_dae"]["enabled"] is True

        broker.start_dae("loop_dae", actor_id="012")

        deadline = time.time() + 2.0
        while time.time() < deadline:
            if broker.get_status("loop_dae")["running"]:
                break
            time.sleep(0.05)

        second = broker.start_dae("loop_dae", actor_id="012")
        assert second["status"] == "already_running"

        stop_result = broker.stop_dae("loop_dae", actor_id="012")
        assert stop_result["status"] == "stopped"


class _ImportStreakRegistry:
    """In-memory launch observations; no daemon, store, listener or heartbeat."""

    def __init__(self):
        self.records = {}
        self.events = []
        self.states = []
        self.disabled = []
        self.fail_at = None

    def get(self, dae_id):
        return self.records.get(dae_id)

    def is_enabled(self, dae_id):
        return self.records[dae_id].enabled

    def enable(self, dae_id):
        self.records[dae_id].enabled = True

    def disable(self, dae_id):
        self.records[dae_id].enabled = False
        self.disabled.append(dae_id)

    def set_state(self, dae_id, state, reason):
        if self.fail_at == "stopped_state" and state == DAEState.STOPPED:
            self.fail_at = None
            raise ImportError("state callback import")
        self.records[dae_id].state = state
        self.states.append((dae_id, state, reason))

    def report_event(self, dae_id, event_type, payload):
        if (self.fail_at == "completed_event"
                and payload.get("action_type") == "launch_completed"):
            self.fail_at = None
            raise ImportError("event callback import")
        self.events.append((dae_id, event_type, dict(payload)))


@pytest.fixture
def inert_import_broker(monkeypatch):
    from modules.infrastructure.dae_daemon.src import dae_launch_broker as module

    registry = _ImportStreakRegistry()
    broker = SimpleNamespace(
        _daemon=SimpleNamespace(registry=registry),
        _handles={}, _specs={}, _import_failures={},
    )
    monkeypatch.setattr(module.time, "time", lambda: 123.0)
    monkeypatch.setattr(module, "logger", SimpleNamespace(
        exception=lambda *args: None, debug=lambda *args: None,
        error=lambda *args: None,
    ))
    return broker, registry


def _import_streak_spec(broker, registry, dae_id="first"):
    spec = DAELaunchSpec(dae_id, "Inert fixture", "tests", lambda: None)
    broker._specs[dae_id] = spec
    broker._handles[dae_id] = SimpleNamespace(
        last_error="", last_result_summary="", completed_at=0.0,
    )
    registry.records[dae_id] = SimpleNamespace(
        pid=None, state=DAEState.REGISTERED, enabled=True,
    )
    return spec


def _run_import_streak(broker, spec, error=None, result=None):
    def start():
        if error is not None:
            raise error
        return result

    spec.start_callable = start
    DAELaunchBroker._run_launch(broker, spec, "012", {})


def _import_streak_failures(registry, dae_id="first"):
    return [payload for owner, _, payload in registry.events
            if owner == dae_id and payload.get("action_type") == "launch_failed"]


class _NestedImportError(ImportError):
    pass


@pytest.mark.parametrize("error_type", [ImportError, ModuleNotFoundError, _NestedImportError])
def test_import_streak_reaches_detachment(inert_import_broker, error_type):
    broker, registry = inert_import_broker
    spec = _import_streak_spec(broker, registry)
    for attempt in range(1, 4):
        _run_import_streak(broker, spec, error_type("missing dependency"))
        assert broker._import_failures == {"first": attempt}
        expected = DAEState.DETACHED if attempt == 3 else DAEState.CRASHED
        assert registry.get("first").state == expected
        assert registry.disabled == (["first"] if attempt == 3 else [])
        assert broker._handles["first"].completed_at == 123.0
        assert registry.events[-1] == ("first", DAEEventType.DAE_STOPPED, {"actor_id": "012"})
    assert [item["import_failure_count"] for item in _import_streak_failures(registry)] == [1, 2, 3]
    assert sum(kind == DAEEventType.DAE_STARTED for _, kind, _ in registry.events) == 3
    assert registry.is_enabled("first") is False


def test_import_streak_success_resets_only_completed_dae(inert_import_broker):
    broker, registry = inert_import_broker
    first = _import_streak_spec(broker, registry)
    second = _import_streak_spec(broker, registry, "second")
    for spec in (first, first, second):
        _run_import_streak(broker, spec, ImportError("missing"))
    received = []

    def complete(**kwargs):
        received.append(kwargs)
        return {"status": "completed"}

    first.start_callable = complete
    DAELaunchBroker._run_launch(broker, first, "012", {"bounded": True})
    assert received == [{"bounded": True}]
    assert broker._import_failures == {"second": 1}
    assert broker._handles["first"].last_result_summary == "completed"
    assert registry.get("first").state == DAEState.STOPPED
    assert registry.events[-2][2] == {
        "action_type": "launch_completed", "actor_id": "012", "result": "completed",
    }
    _run_import_streak(broker, first, ImportError("new streak"))
    assert broker._import_failures == {"first": 1, "second": 1}
    assert registry.disabled == []


@pytest.mark.parametrize("error_type", [RuntimeError, ValueError])
def test_import_streak_non_import_exception_breaks_streak(inert_import_broker, error_type):
    broker, registry = inert_import_broker
    first = _import_streak_spec(broker, registry)
    second = _import_streak_spec(broker, registry, "second")
    for spec in (first, first, second):
        _run_import_streak(broker, spec, ImportError("missing"))
    _run_import_streak(broker, first, error_type("ordinary failure"))
    assert broker._import_failures == {"second": 1}
    assert _import_streak_failures(registry)[-1]["import_failure_count"] == 0
    assert registry.get("first").state == DAEState.CRASHED
    _run_import_streak(broker, first, ImportError("new streak"))
    assert broker._import_failures == {"first": 1, "second": 1}
    assert registry.disabled == []


@pytest.mark.parametrize("stage", ["summary", "completed_event", "stopped_state"])
def test_import_streak_preserves_guarded_downstream_boundary(inert_import_broker, stage):
    broker, registry = inert_import_broker
    spec = _import_streak_spec(broker, registry)
    for _ in range(2):
        _run_import_streak(broker, spec, ImportError("missing"))

    class BrokenSummary:
        def __str__(self):
            raise ImportError("summary import")

    registry.fail_at = stage
    result = BrokenSummary() if stage == "summary" else "completed"
    _run_import_streak(broker, spec, result=result)
    assert broker._import_failures == {"first": 3}
    assert _import_streak_failures(registry)[-1]["import_failure_count"] == 3
    assert registry.get("first").state == DAEState.DETACHED
    assert registry.disabled == ["first"]
    assert broker._handles["first"].completed_at == 123.0
    assert registry.events[-1][1] == DAEEventType.DAE_STOPPED


def test_import_streak_reenable_preserves_until_recovery(inert_import_broker):
    broker, registry = inert_import_broker
    spec = _import_streak_spec(broker, registry)
    for _ in range(3):
        _run_import_streak(broker, spec, ImportError("missing"))
    assert registry.disabled == ["first"]
    registry.enable("first")
    _run_import_streak(broker, spec, ImportError("still missing"))
    assert broker._import_failures == {"first": 4}
    assert registry.disabled == ["first", "first"]
    assert registry.get("first").state == DAEState.DETACHED
    registry.enable("first")
    _run_import_streak(broker, spec, result="recovered")
    assert broker._import_failures == {}
    assert registry.is_enabled("first") is True
    _run_import_streak(broker, spec, ImportError("new streak"))
    assert broker._import_failures == {"first": 1}
    assert registry.get("first").state == DAEState.CRASHED
    assert registry.disabled == ["first", "first"]


def test_import_streak_disabled_admission_does_not_launch(inert_import_broker, monkeypatch):
    broker, registry = inert_import_broker
    _import_streak_spec(broker, registry)
    broker._import_failures["first"] = 3
    registry.disable("first")

    def forbidden_thread(*args, **kwargs):
        raise AssertionError("disabled admission must not construct a thread")

    monkeypatch.setattr(threading, "Thread", forbidden_thread)
    result = DAELaunchBroker.start_dae(broker, "first", actor_id="012")
    assert result == {"success": False, "dae_id": "first", "error": "disabled"}
    assert broker._import_failures == {"first": 3}
    assert registry.events == []
    assert registry.states == []


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit])
def test_import_streak_base_exception_preserves_streak_and_finally(inert_import_broker, error_type):
    broker, registry = inert_import_broker
    spec = _import_streak_spec(broker, registry)
    broker._import_failures["first"] = 2
    error = error_type("interrupted")
    with pytest.raises(error_type) as caught:
        _run_import_streak(broker, spec, error)
    assert caught.value is error
    assert broker._import_failures == {"first": 2}
    assert broker._handles["first"].completed_at == 123.0
    assert _import_streak_failures(registry) == []
    assert registry.get("first").state == DAEState.RUNNING
    assert registry.events[-1] == ("first", DAEEventType.DAE_STOPPED, {"actor_id": "012"})
    assert registry.disabled == []

