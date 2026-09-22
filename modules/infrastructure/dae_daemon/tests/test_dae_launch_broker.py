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
        assert stop_result["success"] is True
        assert stop_result["status"] in {"stopping", "stopped"}


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


class _StopAckLock:
    """Finite lock-depth spy; no thread or blocking primitive."""

    def __init__(self):
        self.depth = 0

    def __enter__(self):
        self.depth += 1

    def __exit__(self, *args):
        self.depth -= 1


class _StopAckHandle:
    def __init__(self, spec):
        self.spec = spec
        self.alive = True
        self.on_alive_read = lambda: None

    @property
    def is_alive(self):
        self.on_alive_read()
        return self.alive


@pytest.fixture
def inert_stop_case(inert_import_broker):
    broker, registry = inert_import_broker
    spec = _import_streak_spec(broker, registry)
    handle = _StopAckHandle(spec)
    broker._handles["first"] = handle
    broker._lock = _StopAckLock()
    registry.get("first").state = DAEState.RUNNING
    case = SimpleNamespace(broker=broker, registry=registry, spec=spec,
                           handle=handle, callbacks={}, trace=[], after_change=None)
    original_state, original_event = registry.set_state, registry.report_event

    def stage(name):
        assert broker._lock.depth == 0, "callbacks must run outside broker lock"
        case.trace.append(name)
        callback = case.callbacks.get(name)
        if callback is not None:
            callback()

    def set_state(dae_id, state, reason):
        assert broker._lock.depth == 0
        original_state(dae_id, state, reason)
        name = {DAEState.STOPPING: "request_state", DAEState.STOPPED: "completion_state"}
        stage(name.get(state, "failed_state"))

    def report_event(dae_id, event_type, payload):
        assert broker._lock.depth == 0
        original_event(dae_id, event_type, payload)
        stage(payload["action_type"])

    registry.set_state, registry.report_event = set_state, report_event
    spec.stop_callable = lambda: stage("hook")
    return case


def _stop_ack_result(case):
    return DAELaunchBroker.stop_dae(case.broker, "first", actor_id="stop_actor")


def _replace_stop_owner(case, removal):
    case.handle.alive = False
    if removal:
        case.broker._handles.pop("first")
    else:
        case.broker._handles["first"] = _StopAckHandle(case.spec)
    case.registry.get("first").state = DAEState.RUNNING
    case.after_change = list(case.trace)


@pytest.mark.parametrize("exited", [False, True])
def test_stop_ack_pending_or_observed_exit(inert_stop_case, exited):
    case = inert_stop_case
    case.callbacks["hook"] = lambda: setattr(case.handle, "alive", not exited)
    result = _stop_ack_result(case)
    status = "stopped" if exited else "stopping"
    assert result == {"success": True, "dae_id": "first", "status": status}
    expected = ["request_state", "stop_requested", "hook"]
    if exited:
        expected += ["completion_state", "stop_completed"]
    assert case.trace == expected
    assert case.registry.get("first").state == (DAEState.STOPPED if exited else DAEState.STOPPING)
    assert [event[2] for event in case.registry.events] == [
        {"action_type": action, "actor_id": "stop_actor"}
        for action in (["stop_requested", "stop_completed"] if exited else ["stop_requested"])
    ]
    assert case.broker._lock.depth == 0


@pytest.mark.parametrize("missing", ["spec", "handle", "live_worker"])
def test_stop_ack_not_running_has_no_effects(inert_stop_case, missing):
    case = inert_stop_case
    if missing == "spec":
        case.broker._specs.clear()
    elif missing == "handle":
        case.broker._handles.clear()
    else:
        case.handle.alive = False
    assert _stop_ack_result(case) == {"success": False, "dae_id": "first", "error": "not_running"}
    assert case.trace == []
    assert case.registry.events == case.registry.states == []


def test_stop_ack_unsupported_has_no_effects(inert_stop_case):
    case = inert_stop_case
    case.spec.stop_callable = None
    assert _stop_ack_result(case) == {"success": False, "dae_id": "first", "error": "stop_unsupported"}
    assert case.trace == []
    assert case.registry.events == case.registry.states == []


def test_stop_ack_hook_exception_preserves_current_owner_failure(inert_stop_case):
    case = inert_stop_case

    def fail():
        raise RuntimeError("hook failed")

    case.callbacks["hook"] = fail
    assert _stop_ack_result(case) == {"success": False, "dae_id": "first", "error": "hook failed"}
    assert case.trace == ["request_state", "stop_requested", "hook", "failed_state"]
    assert case.registry.states[-1] == ("first", DAEState.CRASHED, "stop_failed:hook failed")


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit])
def test_stop_ack_hook_base_exception_propagates(inert_stop_case, error_type):
    case = inert_stop_case
    error = error_type("interrupted")

    def fail():
        raise error

    case.callbacks["hook"] = fail
    with pytest.raises(error_type) as caught:
        _stop_ack_result(case)
    assert caught.value is error
    assert case.trace == ["request_state", "stop_requested", "hook"]
    assert case.registry.get("first").state == DAEState.STOPPING


@pytest.mark.parametrize("stage", ["request_state", "stop_requested"])
def test_stop_ack_request_reporting_exception_stays_outside_catch(inert_stop_case, stage):
    case = inert_stop_case
    error = RuntimeError("request reporting failed")

    def fail():
        raise error

    case.callbacks[stage] = fail
    with pytest.raises(RuntimeError) as caught:
        _stop_ack_result(case)
    assert caught.value is error
    assert "hook" not in case.trace
    assert "failed_state" not in case.trace


@pytest.mark.parametrize("stage", ["completion_state", "stop_completed"])
def test_stop_ack_completion_reporting_exception_stays_caught(inert_stop_case, stage):
    case = inert_stop_case
    case.callbacks["hook"] = lambda: setattr(case.handle, "alive", False)

    def fail():
        raise RuntimeError("completion reporting failed")

    case.callbacks[stage] = fail
    result = _stop_ack_result(case)
    assert result == {"success": False, "dae_id": "first", "error": "completion reporting failed"}
    assert case.registry.get("first").state == DAEState.CRASHED
    assert case.trace[-1] == "failed_state"


@pytest.mark.parametrize("removal", [False, True])
@pytest.mark.parametrize("stage", ["request_state", "stop_requested", "hook", "completion_state", "stop_completed"])
def test_stop_ack_owner_change_stops_old_owner_publication(inert_stop_case, stage, removal):
    case = inert_stop_case
    case.callbacks["hook"] = lambda: setattr(case.handle, "alive", False)
    case.callbacks[stage] = lambda: _replace_stop_owner(case, removal)
    assert _stop_ack_result(case) == {"success": False, "dae_id": "first", "error": "runtime_changed"}
    assert case.after_change is not None
    assert case.trace == case.after_change
    assert case.registry.get("first").state == DAEState.RUNNING
    if stage in {"request_state", "stop_requested"}:
        assert "hook" not in case.trace


@pytest.mark.parametrize("removal", [False, True])
@pytest.mark.parametrize("stage", ["hook", "completion_state", "stop_completed"])
def test_stop_ack_superseded_exception_does_not_crash_new_owner(inert_stop_case, stage, removal):
    case = inert_stop_case
    case.callbacks["hook"] = lambda: setattr(case.handle, "alive", False)

    def replace_then_raise():
        _replace_stop_owner(case, removal)
        raise RuntimeError("old owner failed")

    case.callbacks[stage] = replace_then_raise
    assert _stop_ack_result(case) == {"success": False, "dae_id": "first", "error": "runtime_changed"}
    assert case.trace == case.after_change
    assert case.registry.get("first").state == DAEState.RUNNING


@pytest.mark.parametrize("removal", [False, True])
def test_stop_ack_liveness_observation_cannot_ack_replacement(inert_stop_case, removal):
    case = inert_stop_case
    reads = []

    def change_on_second_read():
        reads.append(None)
        if len(reads) == 2:
            _replace_stop_owner(case, removal)

    case.handle.on_alive_read = change_on_second_read
    result = _stop_ack_result(case)
    assert result == {"success": False, "dae_id": "first", "error": "runtime_changed"}
    assert len(reads) == 2
    assert case.after_change == ["request_state", "stop_requested", "hook"]
    assert case.trace == case.after_change
    assert case.registry.get("first").state == DAEState.RUNNING


@pytest.mark.parametrize("refresh", ["registration", "request_callback"])
def test_stop_ack_binds_launched_spec_and_captured_hook(inert_stop_case, refresh):
    case = inert_stop_case

    def wrong_hook():
        raise AssertionError("a refreshed hook must not control the captured worker")

    if refresh == "registration":
        case.broker._specs["first"] = DAELaunchSpec(
            "first", "Future launch", "tests", lambda: None, stop_callable=wrong_hook,
        )
    else:
        case.callbacks["stop_requested"] = lambda: setattr(case.spec, "stop_callable", wrong_hook)
    assert _stop_ack_result(case) == {"success": True, "dae_id": "first", "status": "stopping"}
    assert case.trace == ["request_state", "stop_requested", "hook"]


@pytest.mark.parametrize("removal", [False, True])
def test_stop_ack_initial_liveness_change_prevents_request(inert_stop_case, removal):
    case = inert_stop_case
    case.handle.on_alive_read = lambda: _replace_stop_owner(case, removal)
    assert _stop_ack_result(case) == {"success": False, "dae_id": "first", "error": "runtime_changed"}
    assert case.after_change == case.trace == []
    assert case.registry.events == case.registry.states == []
    assert case.registry.get("first").state == DAEState.RUNNING


@pytest.mark.parametrize("removal", [False, True])
def test_stop_ack_failure_reporting_change_prevents_old_ack(inert_stop_case, removal):
    case = inert_stop_case

    def fail():
        raise RuntimeError("old hook failed")

    case.callbacks["hook"] = fail
    case.callbacks["failed_state"] = lambda: _replace_stop_owner(case, removal)
    assert _stop_ack_result(case) == {"success": False, "dae_id": "first", "error": "runtime_changed"}
    assert case.after_change == ["request_state", "stop_requested", "hook", "failed_state"]
    assert case.trace == case.after_change
    assert case.registry.get("first").state == DAEState.RUNNING


def test_stop_ack_failure_reporting_exception_propagates(inert_stop_case):
    case = inert_stop_case
    reporting_error = ValueError("failure reporting failed")

    def hook_failed():
        raise RuntimeError("hook failed")

    def reporting_failed():
        raise reporting_error

    case.callbacks.update(hook=hook_failed, failed_state=reporting_failed)
    with pytest.raises(ValueError) as caught:
        _stop_ack_result(case)
    assert caught.value is reporting_error
    assert case.trace == ["request_state", "stop_requested", "hook", "failed_state"]

