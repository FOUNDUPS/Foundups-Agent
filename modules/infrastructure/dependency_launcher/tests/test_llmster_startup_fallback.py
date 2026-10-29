"""Offline startup/caller controls; no real process, network or model actions."""

from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from modules.infrastructure.dependency_launcher.src import dae_dependencies as deps
from modules.infrastructure.dependency_launcher.src import lm_studio_startup as startup
from modules.infrastructure.shared_utilities import lm_studio_model_lifecycle as lifecycle
from modules.infrastructure.shared_utilities import lm_studio_native_transport as native

KEY = "gemma4-e2b"
_REAL_OBSERVE = startup.observe_processes
_ROOT = Path(__file__).resolve().parents[4]


def state(kind=native.LMStudioResidencyState.RESIDENT, *, key=KEY, instances=1):
    loaded = tuple(native.LMStudioLoadedInstance(f"instance-{i}", {}) for i in range(instances))
    return native.LMStudioModelState(key, kind, loaded if kind is native.LMStudioResidencyState.RESIDENT else ())


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    def denied(*_args, **_kwargs):
        raise AssertionError("unexpected offline effect")

    locks = []

    @contextmanager
    def lock(identity, **kwargs):
        locks.append((identity, kwargs))
        yield

    monkeypatch.setattr(startup, "runtime_operation_lock", lock)
    monkeypatch.setattr(startup, "inspect_lm_studio_model", denied)
    monkeypatch.setattr(startup, "observe_processes", denied)
    monkeypatch.setattr(startup.subprocess, "run", Mock(side_effect=denied))
    monkeypatch.setattr(startup.subprocess, "Popen", Mock(side_effect=denied))
    monkeypatch.setattr(startup.time, "sleep", lambda *_: None)
    monkeypatch.setattr(deps, "is_port_open", Mock(return_value=False))
    for name in ("load_all_models", "_load_ui_tars_model", "_load_gemma_model", "_load_qwen_model"):
        monkeypatch.setattr(deps, name, denied)
    return locks


def launch(**changes):
    args = dict(port=1234, model_key=KEY, lms_cli="lms.exe", gui_path="LM Studio.exe")
    args.update(changes)
    return startup.launch_model_server(**args)


def cold(monkeypatch, *, processes=((False, False), (False, False), (False, True)), after=None):
    probe = Mock(side_effect=[state(native.LMStudioResidencyState.SERVER_UNREACHABLE), after or state()])
    monkeypatch.setattr(startup, "inspect_lm_studio_model", probe)
    monkeypatch.setattr(startup, "observe_processes", Mock(side_effect=processes))
    commands = Mock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.setattr(startup.subprocess, "run", commands)
    return probe, commands


def test_warm_exact_model_works_without_cli_or_process_observer(monkeypatch, isolated):
    probe = Mock(return_value=state())
    monkeypatch.setattr(startup, "inspect_lm_studio_model", probe)
    assert launch(lms_cli=None, gui_path=None)[0] is True
    probe.assert_called_once_with(KEY, base_url="http://127.0.0.1:1234", timeout=1.0)
    assert isolated == [(lifecycle.lm_studio_node_lock_identity("http://127.0.0.1:1234"), {"timeout_seconds": 2.0})]
    assert startup.subprocess.run.call_count == 0
    assert startup.subprocess.Popen.call_count == 0


def test_empty_native_inventory_is_server_ready_only_when_no_model_requested(monkeypatch):
    monkeypatch.setattr(startup, "inspect_lm_studio_model", Mock(return_value=state(native.LMStudioResidencyState.NOT_INSTALLED)))
    assert launch(model_key=None)[0] is True


@pytest.mark.parametrize("kind", [native.LMStudioResidencyState.NOT_INSTALLED, native.LMStudioResidencyState.INSTALLED_NOT_RESIDENT])
def test_missing_or_unloaded_model_is_not_ready_and_never_loaded(monkeypatch, kind):
    monkeypatch.setattr(startup, "inspect_lm_studio_model", Mock(return_value=state(kind)))
    ok, message = launch()
    assert not ok and "not resident" in message
    assert startup.subprocess.run.call_count == 0


@pytest.mark.parametrize("observed", [state(instances=2), state(key="qwen-coder-7b")])
def test_ambiguous_or_wrong_selected_model_is_not_ready(monkeypatch, observed):
    monkeypatch.setattr(startup, "inspect_lm_studio_model", Mock(return_value=observed))
    assert launch()[0] is False
    assert startup.subprocess.run.call_count == 0


@pytest.mark.parametrize("error", [native.LMStudioAuthenticationError("private detail"), ValueError("private detail"), RuntimeError("private detail")])
def test_invalid_native_http_is_failure_without_spawn_or_private_error(monkeypatch, error):
    monkeypatch.setattr(startup, "inspect_lm_studio_model", Mock(side_effect=error))
    ok, message = launch()
    assert not ok and "private detail" not in message
    assert startup.subprocess.run.call_count == 0


def test_tcp_occupant_without_native_http_prevents_launch(monkeypatch):
    monkeypatch.setattr(startup, "inspect_lm_studio_model", Mock(return_value=state(native.LMStudioResidencyState.SERVER_UNREACHABLE)))
    monkeypatch.setattr(deps, "is_port_open", Mock(return_value=True))
    assert "port occupied" in launch()[1]
    assert startup.subprocess.run.call_count == 0


@pytest.mark.parametrize("snapshot", [(None, None), (True, None), (None, False), (True, True)])
def test_unknown_or_conflicting_process_observation_never_launches(monkeypatch, snapshot):
    _, commands = cold(monkeypatch, processes=[snapshot])
    assert launch()[0] is False
    assert commands.call_count == 0
    assert startup.subprocess.Popen.call_count == 0


def test_cold_state_change_prevents_daemon_or_gui_start(monkeypatch):
    _, commands = cold(monkeypatch, processes=[(False, False), (True, False)])
    assert "state changed" in launch()[1]
    assert commands.call_count == 0


def test_missing_cli_does_not_start_unbound_gui(monkeypatch):
    _, commands = cold(monkeypatch, processes=[(False, False)])
    assert "explicit loopback" in launch(lms_cli=None)[1]
    assert commands.call_count == 0
    assert startup.subprocess.Popen.call_count == 0


def test_headless_cold_start_checks_commands_and_explicit_bind(monkeypatch):
    _, commands = cold(monkeypatch)
    assert launch()[0] is True
    assert [call.args[0] for call in commands.call_args_list] == [
        ["lms.exe", "daemon", "up"],
        ["lms.exe", "server", "start", "--bind", "127.0.0.1", "--port", "1234"],
    ]
    assert all(call.kwargs["timeout"] == 30 and call.kwargs["shell"] is False for call in commands.call_args_list)
    assert startup.subprocess.Popen.call_count == 0


@pytest.mark.parametrize("snapshot", [(True, False), (False, True)])
def test_existing_gui_or_daemon_starts_http_without_starting_another_runtime(monkeypatch, snapshot):
    _, commands = cold(monkeypatch, processes=[snapshot, snapshot])
    assert launch()[0] is True
    assert len(commands.call_args_list) == 1
    assert commands.call_args.args[0][1:3] == ["server", "start"]
    assert startup.subprocess.Popen.call_count == 0


@pytest.mark.parametrize("failure_position", [0, 1])
def test_nonzero_command_never_reports_ready_or_falls_back(monkeypatch, failure_position):
    _, commands = cold(monkeypatch)
    commands.side_effect = [SimpleNamespace(returncode=1)] if failure_position == 0 else [SimpleNamespace(returncode=0), SimpleNamespace(returncode=2)]
    assert launch()[0] is False
    assert commands.call_count == failure_position + 1
    assert startup.subprocess.Popen.call_count == 0


@pytest.mark.parametrize("failure_position", [0, 1])
def test_command_timeout_does_not_retry_or_launch_gui(monkeypatch, failure_position):
    _, commands = cold(monkeypatch)
    error = startup.subprocess.TimeoutExpired("private diagnostic", 30)
    commands.side_effect = [error] if failure_position == 0 else [SimpleNamespace(returncode=0), error]
    ok, message = launch()
    assert not ok and "private diagnostic" not in message
    assert commands.call_count == failure_position + 1
    assert startup.subprocess.Popen.call_count == 0


@pytest.mark.parametrize("late", [(True, False), (None, None), (True, True)])
def test_changed_state_after_daemon_up_prevents_server_command(monkeypatch, late):
    _, commands = cold(monkeypatch, processes=[(False, False), (False, False), late])
    assert launch()[0] is False
    assert commands.call_count == 1


def test_successful_command_without_http_readiness_is_not_success(monkeypatch):
    probe, commands = cold(monkeypatch, processes=[(False, True), (False, True)])
    probe.side_effect = None
    probe.return_value = state(native.LMStudioResidencyState.SERVER_UNREACHABLE)
    monkeypatch.setattr(startup, "_WAIT_SECONDS", 2)
    assert "native API not ready" in launch()[1]
    assert probe.call_count == 3 and commands.call_count == 1


def test_cold_gui_preference_is_refused_without_spawn_or_server_command(monkeypatch):
    _, commands = cold(monkeypatch, processes=[(False, False), (False, False)])
    ok, message = launch(prefer_headless=False)
    assert startup.subprocess.Popen.call_count == 0
    assert commands.call_count == 0
    assert not ok and "not qualified" in message


def test_existing_gui_can_start_explicitly_bound_http_with_gui_preference(monkeypatch):
    _, commands = cold(monkeypatch, processes=[(True, False), (True, False)])
    assert launch(prefer_headless=False)[0] is True
    assert startup.subprocess.Popen.call_count == 0
    assert [call.args[0] for call in commands.call_args_list] == [
        ["lms.exe", "server", "start", "--bind", "127.0.0.1", "--port", "1234"],
    ]


def test_lock_timeout_prevents_even_observation(monkeypatch):
    monkeypatch.setattr(startup, "runtime_operation_lock", Mock(side_effect=TimeoutError))
    assert "busy" in launch()[1]
    assert startup.subprocess.run.call_count == 0


def test_busy_competing_startup_does_not_probe_or_spawn(monkeypatch):
    gate = threading.Lock()
    entered, release = threading.Event(), threading.Event()

    @contextmanager
    def lock(*_args, **_kwargs):
        if not gate.acquire(blocking=False):
            raise TimeoutError
        try:
            yield
        finally:
            gate.release()

    def observe(*_args, **_kwargs):
        entered.set()
        assert release.wait(2)
        return state()

    monkeypatch.setattr(startup, "runtime_operation_lock", lock)
    probe = Mock(side_effect=observe)
    monkeypatch.setattr(startup, "inspect_lm_studio_model", probe)
    with ThreadPoolExecutor(max_workers=1) as executor:
        first = executor.submit(launch)
        try:
            assert entered.wait(2)
            assert "busy" in launch()[1]
            assert probe.call_count == 1
        finally:
            release.set()
        assert first.result(timeout=2)[0] is True
    assert startup.subprocess.run.call_count == 0


@pytest.mark.parametrize("port", [True, 0, 65536, "1234"])
def test_invalid_port_is_rejected_before_lock(monkeypatch, isolated, port):
    assert launch(port=port)[0] is False
    assert isolated == []


@pytest.mark.parametrize("mode", ["missing", "denied", "incomplete"])
def test_process_observer_reports_unknown_instead_of_absent(monkeypatch, mode):
    if mode == "missing":
        monkeypatch.setitem(sys.modules, "psutil", None)
    elif mode == "denied":
        monkeypatch.setitem(sys.modules, "psutil", SimpleNamespace(process_iter=Mock(side_effect=PermissionError)))
    else:
        monkeypatch.setitem(sys.modules, "psutil", SimpleNamespace(process_iter=lambda *_: [SimpleNamespace(info={"name": None})]))
    assert _REAL_OBSERVE() == (None, None)


def test_process_observer_recognizes_known_runtime_names(monkeypatch):
    processes = [SimpleNamespace(info={"name": "LM Studio.exe"}), SimpleNamespace(info={"name": "other.exe"})]
    monkeypatch.setitem(sys.modules, "psutil", SimpleNamespace(process_iter=lambda *_: processes))
    assert _REAL_OBSERVE() == (True, False)


def test_native_health_requires_models_schema_not_openai_listing(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, *_args):
            return json.dumps({"data": [{"id": KEY}]}).encode()

    monkeypatch.setattr(startup, "inspect_lm_studio_model", native.inspect_lm_studio_model)
    request = Mock(return_value=Response())
    monkeypatch.setattr(native, "_open_no_redirect", request)
    assert startup.is_server_reachable(1234) is False
    assert request.call_args.args[0].full_url == "http://127.0.0.1:1234/api/v1/models"
    assert request.call_args.kwargs["timeout"] == 1.0


def test_valid_empty_native_inventory_proves_server_reachability(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, *_args):
            return b'{"models": []}'

    monkeypatch.setattr(startup, "inspect_lm_studio_model", native.inspect_lm_studio_model)
    monkeypatch.setattr(native, "_open_no_redirect", Mock(return_value=Response()))
    assert startup.is_server_reachable(1234) is True


def test_facade_keeps_vision_default_and_forwards_explicit_general_key(monkeypatch):
    dispatch = Mock(return_value=(True, "ready"))
    monkeypatch.setattr(startup, "launch_model_server", dispatch)
    monkeypatch.setattr(startup, "resolve_lms_cli_path", lambda: None)
    monkeypatch.setattr(deps, "resolve_lm_studio_path", lambda: None)
    assert deps.launch_lm_studio()[0]
    assert dispatch.call_args.kwargs["model_key"] == deps.UI_TARS_MODEL_ID
    assert deps.launch_lm_studio(model_key=KEY)[0]
    assert dispatch.call_args.kwargs["model_key"] == KEY
    assert deps.launch_lm_studio(load_model=False)[0]
    assert dispatch.call_args.kwargs["model_key"] is None


def test_general_default_is_not_replaced_by_coder_alias(monkeypatch):
    monkeypatch.delenv("QWEN_MODEL_ID", raising=False)
    monkeypatch.setenv("LOCAL_QWEN_MODEL_ID", "qwen-coder-7b")
    source = ast.parse(Path(deps.__file__).read_text(encoding="utf-8"))
    assignment = next(node for node in source.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "QWEN_MODEL_ID" for t in node.targets))
    scope = {"os": __import__("os")}
    exec(compile(ast.Module(body=[assignment], type_ignores=[]), deps.__file__, "exec"), scope)
    assert scope["QWEN_MODEL_ID"] == "qwen3.5-4b"


def test_ensure_dependencies_forwards_selected_key_without_real_browser(monkeypatch):
    monkeypatch.setenv("YT_EDGE_AUTO_LAUNCH", "true")
    monkeypatch.setattr(deps, "launch_chrome", lambda: (True, "mock"))
    monkeypatch.setattr(deps, "launch_edge", lambda: (True, "mock"))
    selected = Mock(return_value=(True, "mock"))
    monkeypatch.setattr(deps, "launch_lm_studio", selected)
    assert asyncio.run(deps.ensure_dependencies(model_key=KEY))["lm_studio"]
    selected.assert_called_once_with(model_key=KEY)


@pytest.mark.parametrize("configured", [KEY, None])
def test_actual_youtube_startup_slice_selects_general_without_vision_requirement(monkeypatch, configured):
    # Execute the actual Phase -2 AST node only; importing the full DAE is not qualified.
    if configured is None:
        monkeypatch.delenv("LM_STUDIO_NATIVE_MODEL_KEY", raising=False)
    else:
        monkeypatch.setenv("LM_STUDIO_NATIVE_MODEL_KEY", configured)
    source = _ROOT / "modules/communication/livechat/src/auto_moderator_dae.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    phase = next(node for node in ast.walk(tree) if isinstance(node, ast.If) and isinstance(node.test, ast.Call) and any(isinstance(arg, ast.Constant) and arg.value == "YT_DEPS_AUTO_LAUNCH" for arg in node.test.args))
    wrapper = ast.AsyncFunctionDef(name="phase", args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]), body=[phase], decorator_list=[])
    module = ast.fix_missing_locations(ast.Module(body=[wrapper], type_ignores=[]))
    selected = AsyncMock(return_value={"chrome": True, "lm_studio": True})
    monkeypatch.setattr(deps, "ensure_dependencies", selected)
    scope = {"os": __import__("os"), "logger": Mock(), "_env_truthy": lambda *_: True}
    exec(compile(module, str(source), "exec"), scope)
    asyncio.run(scope["phase"]())
    selected.assert_awaited_once_with(require_lm_studio=True, model_key=configured or deps.QWEN_MODEL_ID)
    assert selected.await_args.kwargs["model_key"] != deps.UI_TARS_MODEL_ID


@pytest.mark.parametrize("root", ["http://localhost:1234", "http://127.0.0.1:1234/v1", "http://[::1]:1234"])
def test_public_lock_identity_matches_existing_protocol_and_transaction(monkeypatch, root):
    old_digest = hashlib.sha256(json.dumps("loopback:1234", separators=(",", ":")).encode()).hexdigest()
    expected = f"lm-studio-node:{old_digest}"
    assert lifecycle.lm_studio_node_lock_identity(root) == expected
    observed = []

    @contextmanager
    def lock(identity, **_kwargs):
        observed.append(identity)
        yield

    monkeypatch.setattr(lifecycle, "runtime_operation_lock", lock)
    monkeypatch.setattr(lifecycle, "inspect_lm_studio_model", Mock(return_value=state()))
    result = lifecycle.execute_lm_studio_model_transaction(model_key=KEY, base_url=root, mode=lifecycle.LMStudioLeaseMode.BORROW_ONLY, operation=lambda lease: lease.instance_id)
    assert result.value == "instance-0" and observed == [expected]
    assert result.lifecycle_receipt.lock_scope_digest == old_digest
    assert result.lifecycle_receipt.residency_origin == "preexisting"
    assert not result.lifecycle_receipt.load_confirmed and not result.lifecycle_receipt.unload_confirmed
