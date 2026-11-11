"""Offline source-bound subprocess, thread and rotation lifecycle cases."""

import ast
import asyncio
import logging
import importlib.util
import os
from pathlib import Path
import sys
import threading
from types import ModuleType, SimpleNamespace

import pytest


SRC = Path(__file__).resolve().parents[1] / "src"


def load_lifecycle(monkeypatch):
    """Load the complete pure helper with its own imports/global namespace."""
    spec = importlib.util.spec_from_file_location("pr841_lifecycle_source", SRC / "engagement_lifecycle.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def runner_source(monkeypatch):
    return _load_runner_source(monkeypatch)


def _load_runner_source(monkeypatch):
    source = SRC / "engagement_runner.py"
    monkeypatch.setattr(os, "environ", {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP") if key in os.environ})
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.ImportFrom) and (node.module or "").startswith("modules.")
    )]
    module = ModuleType("pr841_runner_source")
    module.__file__ = str(source)
    module._lifecycle = load_lifecycle(monkeypatch)
    for name in ("_await_owned_completion", "_finish_subprocess", "await_thread_worker"):
        module.__dict__[name] = getattr(module._lifecycle, name)
    from modules.communication.livechat.src.automation_gates import stop_active, stop_file_path
    import tempfile
    from uuid import uuid4
    monkeypatch.setenv('YT_AUTOMATION_STOP_FILE', str(Path(tempfile.gettempdir()) / ('lifecycle-STOP-' + uuid4().hex)))
    module.stop_active = stop_active
    module.stop_file_path = stop_file_path
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(compile(tree, str(source), "exec"), module.__dict__)
    for key, value in {
        "YT_AUTOMATION_RUN_ID": "offline-runner-test",
        "YT_AUTOMATION_ENABLED": "true",
        "YT_COMMENT_ENGAGEMENT_ENABLED": "true",
        "COMMUNITY_DOM_ONLY": "true",
        "COMMUNITY_DEBUG_SUBPROCESS": "false",
        "COMMUNITY_UNLIMITED_TIMEOUT": "30",
    }.items():
        monkeypatch.setenv(key, value)
    return module


def _offline_subprocess_runner(module, tmp_path, *, finish=False):
    script = tmp_path / "owned_child.py"
    script.write_text(
        "import json, time\n"
        "print(json.dumps({'stats': {'comments_processed': 7}}), flush=True)\n"
        + ("" if finish else "time.sleep(30)\n"), encoding="utf-8"
    )
    runner = module.SubprocessRunner(tmp_path)
    runner.engagement_script = script
    return runner


async def _reap_test_process(process):
    if process.returncode is None:
        process.kill()
    await process.wait()


def test_runner_subprocess_success_reaps_and_parses(runner_source, tmp_path, monkeypatch):
    async def scenario():
        runner = _offline_subprocess_runner(runner_source, tmp_path, finish=True)
        original = asyncio.create_subprocess_exec
        processes = []

        async def spawn(*args, **kwargs):
            process = await original(*args, **kwargs)
            processes.append(process)
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        result = await runner.run_engagement("offline-channel")
        assert result["stats"]["comments_processed"] == 7
        assert processes[0].returncode == 0
        assert processes[0].stdout.at_eof() and processes[0].stderr.at_eof()
    asyncio.run(scenario())


@pytest.mark.parametrize("during_spawn", [False, True])
def test_runner_subprocess_cancellation_reaps_owned_child(
    runner_source, tmp_path, monkeypatch, during_spawn
):
    async def scenario():
        runner = _offline_subprocess_runner(runner_source, tmp_path)
        original = asyncio.create_subprocess_exec
        spawned, release_spawn, waiting = asyncio.Event(), asyncio.Event(), asyncio.Event()
        processes = []

        async def spawn(*args, **kwargs):
            process = await original(*args, **kwargs)
            original_wait = process.wait

            async def wait():
                waiting.set()
                return await original_wait()

            process.wait = wait
            processes.append(process)
            spawned.set()
            if during_spawn:
                await release_spawn.wait()
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        task = asyncio.create_task(runner.run_engagement("offline-channel"))
        try:
            await asyncio.wait_for(spawned.wait(), 5)
            if not during_spawn:
                await asyncio.wait_for(waiting.wait(), 5)
            task.cancel()
            await asyncio.sleep(0)
            if during_spawn:
                assert not task.done(), "cancellation must retain a racing spawn"
                task.cancel()  # A second request must not detach cleanup.
                release_spawn.set()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(asyncio.shield(task), 5)
            assert processes[0].returncode is not None, "runner returned before child exit"
            assert processes[0].stdout.at_eof() and processes[0].stderr.at_eof()
        finally:
            release_spawn.set()
            for process in processes:
                await _reap_test_process(process)
            await asyncio.gather(task, return_exceptions=True)
    asyncio.run(scenario())


def test_runner_subprocess_timeout_reaps_owned_child(runner_source, tmp_path, monkeypatch):
    async def scenario():
        runner = _offline_subprocess_runner(runner_source, tmp_path)
        monkeypatch.setenv("COMMUNITY_UNLIMITED_TIMEOUT", "0")
        original = asyncio.create_subprocess_exec
        processes = []

        async def spawn(*args, **kwargs):
            process = await original(*args, **kwargs)
            processes.append(process)
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        try:
            result = await asyncio.wait_for(runner.run_engagement("offline-channel"), 5)
            assert result["error"] == "timeout" and result["timeout_seconds"] == 0
            assert processes[0].returncode is not None
            assert processes[0].stdout.at_eof() and processes[0].stderr.at_eof()
        finally:
            for process in processes:
                await _reap_test_process(process)
    asyncio.run(scenario())


@pytest.mark.parametrize("error_type", [OSError, asyncio.TimeoutError])
def test_runner_subprocess_spawn_failure_preserved(runner_source, tmp_path, monkeypatch, error_type):
    async def scenario():
        runner = _offline_subprocess_runner(runner_source, tmp_path)

        async def fail(*args, **kwargs):
            raise error_type("offline spawn failure")

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fail)
        with pytest.raises(error_type, match="offline spawn failure"):
            await runner.run_engagement("offline-channel")
    asyncio.run(scenario())


def _stubborn_process():
    started, terminated, exited = asyncio.Event(), asyncio.Event(), asyncio.Event()
    drained = []

    class Pipe:
        async def read(self, size):
            assert size == 65536
            return await self.readline()

        async def readline(self):
            await exited.wait()
            drained.append(self)
            return b""

    class Process:
        pid = 123
        returncode = None
        kills = 0
        stdout, stderr = Pipe(), Pipe()

        async def wait(self):
            started.set()
            await exited.wait()
            return self.returncode

        def terminate(self):
            terminated.set()

        def kill(self):
            self.kills += 1
            self.returncode = -9
            exited.set()

    process = Process()

    return process, started, terminated, exited, drained


@pytest.mark.parametrize("kill_required", [False, True])
def test_runner_subprocess_cleanup_resists_repeated_cancel(
    runner_source, tmp_path, monkeypatch, kill_required
):
    async def scenario():
        runner = _offline_subprocess_runner(runner_source, tmp_path)
        process, started, terminated, exited, drained = _stubborn_process()

        async def spawn(*args, **kwargs):
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        task = asyncio.create_task(runner.run_engagement("offline-channel"))
        try:
            await asyncio.wait_for(started.wait(), 5)
            task.cancel()
            await asyncio.wait_for(terminated.wait(), 5)
            task.cancel()
            await asyncio.sleep(0)
            assert not task.done()
            if not kill_required:
                process.returncode = -15
                exited.set()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(asyncio.shield(task), 5)
            assert process.kills == int(kill_required)
            assert len(drained) == 2
        finally:
            exited.set()
            await asyncio.gather(task, return_exceptions=True)
    asyncio.run(scenario())


def _prepare_thread_worker(runner_source, tmp_path, monkeypatch, outcome):
    runner = runner_source.ThreadRunner(tmp_path)
    loop = asyncio.get_running_loop()
    started = asyncio.Event()
    release, finished = threading.Event(), threading.Event()
    if outcome == "timeout":
        monkeypatch.setenv("COMMUNITY_UNLIMITED_TIMEOUT", "0")

        class TimedAsyncio:
            def __getattr__(self, name):
                return getattr(asyncio, name)

            async def wait_for(self, awaitable, timeout):
                return await asyncio.wait_for(awaitable, 0.02 if timeout == 0 else timeout)

        monkeypatch.setattr(runner_source, "asyncio", TimedAsyncio())
        monkeypatch.setattr(runner_source._lifecycle, "asyncio", TimedAsyncio())

    def execute(*args):
        loop.call_soon_threadsafe(started.set)
        try:
            assert release.wait(5), "test failed to release its disposable worker"
            if outcome == "cancel_worker_error":
                raise RuntimeError("offline worker failure")
            return {"stats": {"comments_processed": 7}}
        finally:
            finished.set()

    monkeypatch.setattr(runner, "_execute_sync", execute)
    return runner, started, release, finished


@pytest.mark.parametrize("outcome", ["cancel", "repeat_cancel", "timeout", "cancel_worker_error"])
def test_runner_thread_settles_before_return(runner_source, tmp_path, monkeypatch, outcome):
    async def scenario():
        runner, started, release, finished = _prepare_thread_worker(runner_source, tmp_path, monkeypatch, outcome)
        task = asyncio.create_task(runner.run_engagement("offline-channel"))
        try:
            await asyncio.wait_for(started.wait(), 5)
            if outcome != "timeout":
                task.cancel()
            await asyncio.sleep(0.05 if outcome == "timeout" else 0)
            if outcome == "repeat_cancel":
                task.cancel()
                await asyncio.sleep(0)
            assert not task.done(), "runner released ownership while thread still ran"
            assert not finished.is_set()
            release.set()
            if outcome == "timeout":
                result = await asyncio.wait_for(asyncio.shield(task), 5)
                assert result["error"] == "timeout" and result["timeout_seconds"] == 0
            else:
                with pytest.raises(asyncio.CancelledError):
                    await asyncio.wait_for(asyncio.shield(task), 5)
            assert finished.is_set()
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)
    asyncio.run(scenario())


def test_runner_thread_success_contract(runner_source, tmp_path, monkeypatch):
    runner = runner_source.ThreadRunner(tmp_path)
    seen = []

    def execute(channel, maximum, switches, port):
        seen.append((channel, maximum, port))
        return {"stats": {"comments_processed": 7}}

    monkeypatch.setattr(runner, "_execute_sync", execute)
    result = asyncio.run(runner.run_engagement("offline-channel", 3, browser_port=9223))
    assert result == {"stats": {"comments_processed": 7}}
    assert seen == [("offline-channel", 3, 9223)]


def test_runner_owned_cancellation_does_not_cancel_owner(runner_source):
    async def scenario():
        child = asyncio.create_task(asyncio.Event().wait())
        owner = asyncio.create_task(runner_source._await_owned_completion(child))
        await asyncio.sleep(0)
        child.cancel()
        assert await owner is False
        assert child.cancelled()
    asyncio.run(scenario())


def test_runner_owner_cancellation_is_reported_after_settlement(runner_source):
    async def scenario():
        release = asyncio.Event()
        child = asyncio.create_task(release.wait())
        owner = asyncio.create_task(runner_source._await_owned_completion(child))
        await asyncio.sleep(0)
        owner.cancel()
        await asyncio.sleep(0)
        assert not owner.done() and not child.done()
        release.set()
        assert await owner is True
        assert child.done() and not child.cancelled()
    asyncio.run(scenario())


def test_runner_settled_cancellation_capabilities(runner_source):
    assert runner_source.EngagementRunner.supports_settled_cancellation is False
    assert runner_source.InProcessRunner.supports_settled_cancellation is False
    assert runner_source.SubprocessRunner.supports_settled_cancellation is True
    assert runner_source.ThreadRunner.supports_settled_cancellation is True


@pytest.fixture
def rotation_source(runner_source, monkeypatch, tmp_path):
    source = SRC / "rotation_supervisor.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.ImportFrom) and (node.module or "").startswith("modules.")
    )]
    module = ModuleType("pr841_rotation_source")
    module.__file__ = str(source)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(compile(tree, str(source), "exec"), module.__dict__)
    module._await_owned_completion = runner_source._await_owned_completion
    module._finish_subprocess = runner_source._finish_subprocess
    module.get_channels = lambda **kw: [
        {"name": "Live", "key": "live", "id": "UC-live"},
        {"name": "Other", "key": "other", "id": "UC-other"},
    ]
    module.group_channels_by_browser = lambda **kw: {}
    module._saves, module._clears = [], []
    module.load_checkpoint = lambda: None
    module.get_remaining_channels = lambda channels, checkpoint: [
        channel for channel in channels if channel not in checkpoint["processed_channels"]
    ]
    module.save_checkpoint = lambda **kw: module._saves.append(kw)
    module.clear_checkpoint = lambda: module._clears.append(True)
    monkeypatch.setenv("TEMP", str(tmp_path))
    monkeypatch.setattr(module.RotationSupervisor, "_record_channel_op", lambda *args, **kw: None)
    monkeypatch.setattr(module.RotationSupervisor, "_check_escalation", lambda *args, **kw: None)
    signal = ModuleType("modules.platform_integration.stream_resolver.src.live_stream_signal")
    signal.get_live_channel = lambda: None
    monkeypatch.setitem(sys.modules, signal.__name__, signal)
    module._signal = signal
    telemetry = ModuleType("modules.communication.livechat.src.breadcrumb_telemetry")
    telemetry.store_breadcrumb = lambda **kw: None
    telemetry.get_breadcrumb_telemetry = lambda: telemetry
    monkeypatch.setitem(sys.modules, telemetry.__name__, telemetry)
    return module


def _fake_rotation_work(module, supervisor, *, block_channel=None):
    spawned, started, released, finished = [], asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def spawn(channel, operation, maximum):
        spawned.append(channel)
        return module.TaskHeartbeat(channel, channel, operation, state=module.TaskState.RUNNING)

    async def monitor(heartbeat):
        if heartbeat.channel == block_channel:
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                await released.wait()
                finished.set()
        return module.TaskState.COMPLETED

    supervisor._spawn_task, supervisor._monitor_task = spawn, monitor
    return spawned, started, released, finished


@pytest.mark.parametrize("browser", ["chrome", "edge"])
@pytest.mark.parametrize("file_signal", ["missing", "stale", "fresh"])
def test_rotation_confirmed_identity_skips_only_live_channel(rotation_source, browser, file_signal):
    async def scenario():
        module = rotation_source
        supervisor = module.RotationSupervisor(
            browser=browser, get_confirmed_live_channel=lambda: "UC-live"
        )
        if file_signal == "fresh":
            module._signal.get_live_channel = lambda: "UC-live"
        spawned, *_ = _fake_rotation_work(module, supervisor)
        result = await supervisor.run_rotation(channels=["Live", "Other"])
        assert spawned == ["Other"]
        assert result.channels_processed == ["Other"] and result.failed_channels == []
        assert module._clears == []
        assert module._saves[-1]["processed_channels"] == {"Other"}
    asyncio.run(scenario())


def test_rotation_offline_processes_all_and_clears_complete_checkpoint(rotation_source):
    async def scenario():
        module = rotation_source
        supervisor = module.RotationSupervisor(get_confirmed_live_channel=lambda: None)
        spawned, *_ = _fake_rotation_work(module, supervisor)
        result = await supervisor.run_rotation(channels=["Live", "Other"])
        assert spawned == result.channels_processed == ["Live", "Other"]
        assert module._clears == [True]
    asyncio.run(scenario())


@pytest.mark.parametrize("parent_cancel", [False, True])
def test_rotation_targeted_handoff_or_shutdown_waits_cleanup(rotation_source, parent_cancel):
    async def scenario():
        module = rotation_source
        supervisor = module.RotationSupervisor()
        spawned, started, release, finished = _fake_rotation_work(module, supervisor, block_channel="Live")
        task = asyncio.create_task(supervisor.run_rotation(channels=["Live", "Other"]))
        handoff = None
        try:
            await asyncio.wait_for(started.wait(), 5)
            assert "UC-live" in supervisor._owned_tasks
            if parent_cancel:
                task.cancel()
            else:
                handoff = asyncio.create_task(supervisor.settle_channel("UC-live"))
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            if parent_cancel:
                task.cancel()
                await asyncio.sleep(0)
            assert not task.done() and not finished.is_set()
            if handoff:
                assert not handoff.done()
            release.set()
            if parent_cancel:
                with pytest.raises(asyncio.CancelledError):
                    await task
                assert spawned == ["Live"]
            else:
                await handoff
                result = await task
                assert result.channels_processed == ["Other"] and result.failed_channels == []
                assert module._saves[-1]["processed_channels"] == {"Other"}
                assert module._clears == []
            assert finished.is_set() and not supervisor._owned_tasks
        finally:
            release.set()
            await asyncio.gather(task, *([handoff] if handoff else []), return_exceptions=True)
    asyncio.run(scenario())


def test_rotation_eager_admission_registers_before_child_runs(rotation_source):
    async def scenario():
        module = rotation_source
        supervisor = module.RotationSupervisor()
        spawned, *_ = _fake_rotation_work(module, supervisor)
        original_spawn = supervisor._spawn_task

        async def spawn(channel, operation, maximum):
            assert supervisor._owned_tasks["UC-live"] is asyncio.current_task()
            return await original_spawn(channel, operation, maximum)

        supervisor._spawn_task = spawn
        loop = asyncio.get_running_loop()
        old_factory = loop.get_task_factory()
        loop.set_task_factory(asyncio.eager_task_factory)
        try:
            result = await supervisor.run_rotation(channels=["Live"])
            assert result.channels_processed == spawned == ["Live"]
        finally:
            loop.set_task_factory(old_factory)
    asyncio.run(scenario())


def test_rotation_preserves_completed_checkpoint_when_live_work_deferred(rotation_source):
    async def scenario():
        module = rotation_source
        module.load_checkpoint = lambda: {
            "browser": "chrome", "operation": "comments", "processed_channels": ["Other"],
        }
        supervisor = module.RotationSupervisor(get_confirmed_live_channel=lambda: "UC-live")
        spawned, *_ = _fake_rotation_work(module, supervisor)
        result = await supervisor.run_rotation(channels=["Live", "Other"])
        assert spawned == result.channels_processed == []
        assert module._saves[-1]["processed_channels"] == {"Other"}
        assert not module._clears
    asyncio.run(scenario())


def test_rotation_does_not_clear_other_browser_checkpoint(rotation_source):
    async def scenario():
        module = rotation_source
        module.load_checkpoint = lambda: {
            "browser": "edge", "operation": "comments", "processed_channels": ["Other"],
        }
        supervisor = module.RotationSupervisor(browser="chrome")
        await supervisor.run_rotation(channels=[])
        assert not module._clears and not module._saves
    asyncio.run(scenario())


def _prepare_rotation_child(module, tmp_path, monkeypatch, kind):
    supervisor = module.RotationSupervisor(
        heartbeat_interval=0.01, task_timeout=0 if kind == "timeout" else 30,
    )
    script = tmp_path / "rotation_child.py"
    script.write_text(
        "import sys, time\n"
        + ("sys.stdout.write('x' * 300000); sys.stdout.flush()\n"
           "sys.stderr.write('y' * 300000); sys.stderr.flush()\n" if kind == "noisy_success"
           else "time.sleep(30)\n"), encoding="utf-8"
    )
    supervisor._build_task_command = lambda channel, operation, maximum: (
        [sys.executable, "-u", str(script)], "offline-child", tmp_path / "heartbeat.json"
    )
    original = asyncio.create_subprocess_exec
    processes = []
    spawned, release_spawn, monitoring = asyncio.Event(), asyncio.Event(), asyncio.Event()
    original_monitor = supervisor._monitor_task

    async def monitor(heartbeat):
        monitoring.set()
        return await original_monitor(heartbeat)

    supervisor._monitor_task = monitor

    async def spawn(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        spawned.set()
        if kind == "spawn_handoff":
            await release_spawn.wait()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    return supervisor, processes, spawned, release_spawn, monitoring


@pytest.mark.parametrize("kind", ["noisy_success", "timeout", "spawn_handoff", "running_handoff"])
def test_rotation_owned_subprocess_lifetime(rotation_source, tmp_path, monkeypatch, kind):
    async def scenario():
        module = rotation_source
        supervisor, processes, spawned, release_spawn, monitoring = _prepare_rotation_child(module, tmp_path, monkeypatch, kind)
        task = asyncio.create_task(supervisor.run_rotation(channels=["Live"]))
        handoff = None
        try:
            await asyncio.wait_for(spawned.wait(), 5)
            if kind in {"spawn_handoff", "running_handoff"}:
                if kind == "running_handoff":
                    await asyncio.wait_for(monitoring.wait(), 5)
                handoff = asyncio.create_task(supervisor.settle_channel("UC-live"))
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                if kind == "spawn_handoff":
                    assert not handoff.done() and not task.done()
                    release_spawn.set()
                await asyncio.wait_for(asyncio.shield(handoff), 5)
            result = await asyncio.wait_for(asyncio.shield(task), 5)
            assert processes[0].returncode is not None
            assert processes[0].stdout.at_eof() and processes[0].stderr.at_eof()
            assert not supervisor._active_tasks and not supervisor._owned_tasks
            if kind == "noisy_success":
                assert result.channels_processed == ["Live"] and module._clears == [True]
            elif kind == "timeout":
                assert result.failed_channels == ["Live"] and not module._clears
            else:
                assert result.channels_processed == result.failed_channels == []
                assert not module._clears
        finally:
            release_spawn.set()
            for process in processes:
                await _reap_test_process(process)
            await asyncio.gather(task, *([handoff] if handoff else []), return_exceptions=True)
    asyncio.run(scenario())


def _make_failed_cleanup_process(failure):
    state = SimpleNamespace(
        stopped=asyncio.Event(), waiting=asyncio.Event(), cleanup_started=False,
    )

    class Process:
        pid, returncode = 12345, None
        stdout, stderr = asyncio.StreamReader(), asyncio.StreamReader()

        def terminate(self):
            if failure == "terminate":
                raise OSError("offline terminate failure")
            if failure == "cancel":
                raise asyncio.CancelledError()

        def kill(self):
            raise OSError("offline kill failure")

        async def wait(self):
            if state.cleanup_started:
                if failure == "kill":
                    raise asyncio.TimeoutError()
                if failure == "wait":
                    raise OSError("offline wait failure")
            state.waiting.set()
            await state.stopped.wait()
            return self.returncode

        async def communicate(self):
            return await asyncio.gather(self.stdout.read(), self.stderr.read())

    state.process = Process()
    return state


def _install_failed_cleanup(module, supervisor, monkeypatch, failure, during_spawn):
    state = _make_failed_cleanup_process(failure)
    state.spawned, state.release_spawn, state.monitoring = (
        asyncio.Event(), asyncio.Event(), asyncio.Event()
    )
    state.spawn_calls = []

    async def spawn(*args, **kwargs):
        state.spawn_calls.append(True)
        state.spawned.set()
        if during_spawn:
            await state.release_spawn.wait()
        return state.process

    async def monitor(heartbeat):
        state.monitoring.set()
        await asyncio.Event().wait()

    original_finish = module._finish_subprocess

    async def fail_cleanup(*args):
        state.cleanup_started = True
        await original_finish(*args)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(module, "_finish_subprocess", fail_cleanup)
    monkeypatch.setattr(supervisor, "_monitor_task", monitor)
    return state


async def _assert_failed_cleanup_retained(supervisor, state, heartbeat, owned, failure):
    assert state.process.returncode is None
    assert supervisor._active_tasks[heartbeat.task_id] is heartbeat
    assert supervisor._owned_tasks["UC-live"] is owned
    assert heartbeat._spawn_task.result() is state.process
    error = RuntimeError if failure == "cancel" else OSError
    message = "did not settle" if failure == "cancel" else f"offline {failure} failure"
    with pytest.raises(error, match=message):
        await supervisor.settle_channel("UC-live")
    with pytest.raises(RuntimeError, match="unresolved cleanup"):
        await supervisor.run_rotation(channels=["Live"])
    assert len(state.spawn_calls) == 1
    assert supervisor._active_tasks[heartbeat.task_id] is heartbeat
    assert supervisor._owned_tasks["UC-live"] is owned


async def _release_failed_cleanup_test(state, heartbeat, rotation, handoff):
    state.release_spawn.set()
    state.process.returncode = -9
    state.stopped.set()
    state.process.stdout.feed_eof()
    state.process.stderr.feed_eof()
    await asyncio.gather(rotation, *([handoff] if handoff else []), return_exceptions=True)
    if heartbeat is not None:
        pending = list(heartbeat._drain_tasks)
        if heartbeat._wait_task is not None:
            pending.append(heartbeat._wait_task)
        await asyncio.gather(*pending, return_exceptions=True)


@pytest.mark.parametrize("failure,during_spawn", [
    ("terminate", False), ("kill", False), ("wait", False), ("terminate", True), ("cancel", False),
])
def test_rotation_cleanup_failure_retains_owner_and_rejects_redispatch(
    rotation_source, monkeypatch, failure, during_spawn
):
    async def scenario():
        supervisor = rotation_source.RotationSupervisor()
        state = _install_failed_cleanup(rotation_source, supervisor, monkeypatch, failure, during_spawn)
        rotation = asyncio.create_task(supervisor.run_rotation(channels=["Live"]))
        handoff, heartbeat = None, None
        try:
            await asyncio.wait_for(state.spawned.wait(), 5)
            if not during_spawn:
                await asyncio.wait_for(state.monitoring.wait(), 5)
                await asyncio.wait_for(state.waiting.wait(), 5)
            owned = supervisor._owned_tasks["UC-live"]
            heartbeat = next(iter(supervisor._active_tasks.values()))
            handoff = asyncio.create_task(supervisor.settle_channel("UC-live"))
            await asyncio.sleep(0)
            state.release_spawn.set()
            error = RuntimeError if failure == "cancel" else OSError
            message = "did not settle" if failure == "cancel" else f"offline {failure} failure"
            with pytest.raises(error, match=message):
                await asyncio.wait_for(asyncio.shield(handoff), 5)
            if failure == "cancel":
                result = await asyncio.wait_for(asyncio.shield(rotation), 5)
                assert result.channels_processed == result.failed_channels == []
            else:
                with pytest.raises(error, match=message):
                    await asyncio.wait_for(asyncio.shield(rotation), 5)
            await _assert_failed_cleanup_retained(supervisor, state, heartbeat, owned, failure)
        finally:
            await _release_failed_cleanup_test(state, heartbeat, rotation, handoff)
    asyncio.run(scenario())


# Bounded framing controls exercise the actual runner and stdlib StreamReader.
def _framing_payload(case):
    import json
    good = json.dumps({'stats': {'comments_processed': 7}, 'label': '日本語'}, ensure_ascii=False).encode()
    def padded(size, count):
        prefix = json.dumps({'stats': {'comments_processed': count}, 'padding': ''}).encode()
        return prefix[:-2] + b'x' * (size - len(prefix)) + prefix[-2:]
    split = good.index('日本語'.encode()) + 1
    cases = {
        'normal_eof': [good], 'crlf_multiline': [b'noise\r\n' + good + b'\r\n'],
        'split_utf8': [good[:split], good[split:split+1], good[split+1:] + b'\n'],
        'boundary_65536': [padded(65536, 7) + b'\n'],
        'oversized_then_same_chunk': [padded(65537, 999) + b'\n' + good + b'\n'],
        'oversized_forged_suffix': [b'x' * 65537 + b'{"stats":{"comments_processed":999}}\n' + good + b'\n'],
        'oversized_then_later_chunk': [b'x' * 131072 + b'\n', good + b'\n'],
        'oversized_eof': [padded(65537, 999)],
        'empty_lines': [b'\n\r\n' + good + b'\n'],
        'multiple_json': [good + b'\n{"stats":{"comments_processed":999}}\n'],
    }
    return cases[case]


async def _run_memory_streams(module, tmp_path, monkeypatch, chunks):
    stdout, stderr = asyncio.StreamReader(), asyncio.StreamReader()
    stderr.feed_eof()
    async def feed():
        for chunk in chunks:
            stdout.feed_data(chunk)
            await asyncio.sleep(0)
        stdout.feed_eof()
    producer = asyncio.create_task(feed())
    class Process:
        pid = 123
        returncode = 0
        async def wait(self):
            await producer
            return self.returncode
    process = Process(); process.stdout, process.stderr = stdout, stderr
    async def spawn(*args, **kwargs):
        return process
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
    runner = _offline_subprocess_runner(module, tmp_path, finish=True)
    return await runner.run_engagement('offline-channel')


@pytest.mark.parametrize('case', [
    'normal_eof', 'crlf_multiline', 'split_utf8', 'boundary_65536',
    'oversized_then_same_chunk', 'oversized_forged_suffix',
    'oversized_then_later_chunk', 'oversized_eof', 'empty_lines', 'multiple_json',
])
def test_runner_frames_bounded_physical_lines(runner_source, tmp_path, monkeypatch, case):
    result = asyncio.run(_run_memory_streams(runner_source, tmp_path, monkeypatch, _framing_payload(case)))
    expected = 0 if case == 'oversized_eof' else 7
    assert result['stats']['comments_processed'] == expected
    if case == 'split_utf8':
        assert result['label'] == '日本語'


def test_immediate_chunk_stream_keeps_event_loop_responsive(runner_source, tmp_path, monkeypatch):
    async def scenario():
        ticks = [0]; observed = []; stop = asyncio.Event()
        class Stream:
            def __init__(self, chunks): self.chunks = list(chunks)
            async def read(self, size):
                assert size == 65536
                observed.append(ticks[0])
                return self.chunks.pop(0) if self.chunks else b''
            async def readline(self):
                observed.append(ticks[0])
                return self.chunks.pop(0) if self.chunks else b''
        class Process:
            pid = 123; returncode = 0
            stdout = Stream([b'noise\n'] * 256 + [b'{"stats":{"comments_processed":7}}\n'])
            stderr = Stream([])
            async def wait(self): return 0
        async def spawn(*args, **kwargs): return Process()
        async def pulse():
            while not stop.is_set():
                ticks[0] += 1
                await asyncio.sleep(0)
        monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
        heartbeat = asyncio.create_task(pulse())
        try:
            runner = _offline_subprocess_runner(runner_source, tmp_path, finish=True)
            result = await runner.run_engagement('offline-channel')
            assert result['stats']['comments_processed'] == 7
            assert max(observed) > min(observed)
        finally:
            stop.set(); await heartbeat
    asyncio.run(scenario())


@pytest.mark.parametrize('failure', ['oserror', 'cancelled'])
def test_finished_reader_failure_is_not_reported_as_settlement(runner_source, caplog, failure):
    async def scenario():
        class Process:
            returncode = 0
            async def wait(self): return 0
        spawn = asyncio.get_running_loop().create_future(); spawn.set_result(Process())
        async def reader():
            if failure == 'cancelled': raise asyncio.CancelledError()
            raise OSError('private-reader-diagnostic-marker')
        drain = asyncio.create_task(reader())
        await asyncio.sleep(0)
        with pytest.raises(RuntimeError, match='subprocess_cleanup_reader_or_wait_failed'):
            await runner_source._finish_subprocess(spawn, [drain], None)
        assert 'private-reader-diagnostic-marker' not in caplog.text
    asyncio.run(scenario())


_PIPE_FIXTURE_PROGRAM = """import json, pathlib, subprocess, sys, time
root = pathlib.Path(__file__).parent
mode = sys.argv[sys.argv.index('--channel') + 1]
(root / 'started').write_text('ready')
if mode == 'inherited':
    subprocess.Popen([sys.executable, '-I', '-S', '-B', str(root / 'pipe_descendant.py')], stdin=subprocess.DEVNULL, stdout=sys.stdout, stderr=sys.stderr)
elif mode in ('actual', 'complete', 'flood'):
    sys.stdout.buffer.write(b'x' * (2 * 1024 * 1024) + b'\\n')
    sys.stdout.buffer.flush()
    print(json.dumps({'stats': {'comments_processed': 7}}), flush=True)
    (root / 'emitted').write_text('done')
else:
    print('READY', flush=True)
deadline = time.monotonic() + 8
while mode != 'complete' and not (root / 'release').exists() and time.monotonic() < deadline:
    time.sleep(.02)
"""
_PIPE_DESCENDANT_PROGRAM = """import pathlib, time
root = pathlib.Path(__file__).parent
(root / 'inherited_ready').write_text('ready')
deadline = time.monotonic() + 8
while not (root / 'release').exists() and time.monotonic() < deadline:
    time.sleep(.02)
"""


def _pipe_fixture_runner(module, tmp_path):
    script = tmp_path / 'pipe_child.py'
    script.write_text(_PIPE_FIXTURE_PROGRAM, encoding='utf-8')
    (tmp_path / 'pipe_descendant.py').write_text(_PIPE_DESCENDANT_PROGRAM, encoding='utf-8')
    runner = module.SubprocessRunner(tmp_path); runner.engagement_script = script
    return runner


def _capture_pipe_fixture(monkeypatch):
    original_spawn, original_task = asyncio.create_subprocess_exec, asyncio.create_task
    state = SimpleNamespace(processes={}, readers={}, tasks=[])
    def task(coro, *args, **kwargs):
        value = original_task(coro, *args, **kwargs); state.tasks.append(value)
        if getattr(coro, '__qualname__', '').endswith('._drain_stream'):
            state.readers[value] = coro.cr_frame.f_locals['stream']
        return value
    async def spawn(*args, **kwargs):
        channel = args[args.index('--channel') + 1]
        kwargs['env'] = {key: os.environ[key] for key in ('SYSTEMROOT','WINDIR','TEMP','TMP') if key in os.environ}
        kwargs['env'].update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', PYTHON_DOTENV_DISABLED='1')
        process = await original_spawn(args[0], '-I', '-S', '-B', *args[1:], **kwargs)
        state.processes[channel] = process
        return process
    monkeypatch.setattr(asyncio, 'create_task', task)
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
    return state


async def _fixture_ready(condition, timeout=3):
    deadline = asyncio.get_running_loop().time() + timeout
    while not condition() and asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(.02)
    return bool(condition())


def _fixture_reader_failed(state):
    return any(task.done() and not task.cancelled() and isinstance(task.exception(), ValueError)
               for task in state.readers)


async def _settle_pipe_fixture(state, tmp_path, operations):
    # This recovery is restricted to synthetic children/readers created above.
    (tmp_path / 'release').write_text('release', encoding='utf-8')
    for operation in operations:
        if not operation.done(): operation.cancel()
    for process in state.processes.values():
        if process.returncode is None: process.kill()
    await asyncio.sleep(.05)
    for task, stream in state.readers.items():
        if task.done() and not task.cancelled() and isinstance(task.exception(), ValueError):
            while await asyncio.wait_for(stream.read(65536), 3): pass
    await asyncio.wait_for(asyncio.gather(*operations, return_exceptions=True), 5)
    for process in state.processes.values():
        await asyncio.wait_for(process.wait(), 3)


@pytest.mark.parametrize('finish', [True, False])
def test_real_oversized_child_output_settles(runner_source, tmp_path, monkeypatch, finish):
    async def scenario():
        runner = _pipe_fixture_runner(runner_source, tmp_path)
        state = _capture_pipe_fixture(monkeypatch)
        mode = 'complete' if finish else 'flood'
        operation = asyncio.create_task(runner.run_engagement(mode))
        try:
            assert await _fixture_ready(lambda: mode in state.processes and (tmp_path/'started').exists())
            assert await _fixture_ready(lambda: (tmp_path/'emitted').exists() or _fixture_reader_failed(state))
            if not finish: operation.cancel()
            done, _ = await asyncio.wait({operation}, timeout=3)
            assert done, 'oversized output retained a blocked reader/wait cleanup'
            if finish:
                assert operation.result()['stats']['comments_processed'] == 7
            else:
                assert operation.cancelled()
            process = state.processes[mode]
            assert process.returncode is not None
            assert process.stdout.at_eof() and process.stderr.at_eof()
        finally:
            await _settle_pipe_fixture(state, tmp_path, [operation])
    asyncio.run(scenario())


def test_inherited_pipe_keeps_ownership_until_controlled_descendant_exit(runner_source, tmp_path, monkeypatch):
    async def scenario():
        runner = _pipe_fixture_runner(runner_source, tmp_path)
        state = _capture_pipe_fixture(monkeypatch)
        operation = asyncio.create_task(runner.run_engagement('inherited'))
        try:
            assert await _fixture_ready(lambda: 'inherited' in state.processes and (tmp_path/'inherited_ready').exists())
            operation.cancel(); process = state.processes['inherited']
            assert await _fixture_ready(lambda: process.returncode is not None)
            await asyncio.sleep(.15)
            assert not operation.done()
            assert await asyncio.wait_for(process.wait(), .2) == process.returncode
            assert any(not task.done() for task in state.readers)
            (tmp_path/'release').write_text('release', encoding='utf-8')
            done, _ = await asyncio.wait({operation}, timeout=5)
            assert done and operation.cancelled()
            assert process.stdout.at_eof() and process.stderr.at_eof()
        finally:
            await _settle_pipe_fixture(state, tmp_path, [operation])
    asyncio.run(scenario())


@pytest.mark.asyncio
async def test_cleanup_diagnostics_separate_process_exit_from_reader_settlement(runner_source, caplog):
    release = asyncio.Event()
    async def reader(): await release.wait()
    async def wait(): return 0
    process = SimpleNamespace(returncode=0, wait=wait)
    spawn = asyncio.get_running_loop().create_future(); spawn.set_result(process)
    drain = asyncio.create_task(reader())
    with caplog.at_level(logging.INFO):
        cleanup = asyncio.create_task(runner_source._finish_subprocess(spawn, [drain], None))
        try:
            assert await _fixture_ready(lambda: 'phase=process_exit_observed' in caplog.text)
            assert not cleanup.done()
            assert 'phase=readers_settled' not in caplog.text
            release.set(); await cleanup
            assert 'phase=readers_settled' in caplog.text
        finally:
            release.set(); await cleanup
