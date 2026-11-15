"""Offline, source-bound tests for ownership of the operator watcher.

Compile the actual run/_run_dae AST without importing the DAE's heavyweight
module graph or calling its constructor. The public run method and the real
startup/stop branches execute below; auth, browser, model, and manifest IO do
not. This proves bounded lifecycle behavior, not full-module/runtime readiness.
"""

import ast
import asyncio
from contextlib import contextmanager
from datetime import datetime
import logging
import os
from pathlib import Path
import sys
import threading
from types import MethodType, ModuleType

import pytest


_SOURCE = Path(__file__).resolve().parents[1] / "src" / "auto_moderator_dae.py"
_QUEUE_MODULE = "modules.communication.livechat.src.operator_command_queue"


async def wait_event(event):
    """Bound regression failures instead of leaving a test waiting forever."""
    await asyncio.wait_for(event.wait(), timeout=5)


@pytest.fixture
def runtime_gates(monkeypatch):
    from modules.communication.livechat.src import automation_gates

    @contextmanager
    def native_lock(identity, *, timeout_seconds):
        assert identity == 'foundups-youtube-runtime-owner'
        assert timeout_seconds == 0.01
        yield

    monkeypatch.setattr(automation_gates, 'runtime_operation_lock', native_lock)
    return automation_gates


@pytest.fixture
def lifecycle(monkeypatch, runtime_gates):
    from modules.communication.livechat.src.engagement_lifecycle import _await_owned_completion

    tree = ast.parse(_SOURCE.read_text(encoding="utf-8"), filename=str(_SOURCE))
    dae_node = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                    and node.name == "AutoModeratorDAE")
    methods = [node for node in dae_node.body if isinstance(node, ast.AsyncFunctionDef)
               and node.name in {"run", "_run_dae"}]
    env_helper = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                      and node.name == "_env_truthy")
    isolated_class = ast.ClassDef(name="AutoModeratorDAE", bases=[], keywords=[],
                                  body=methods, decorator_list=[])
    isolated = ast.fix_missing_locations(ast.Module(
        body=[env_helper, isolated_class], type_ignores=[]))
    namespace = {
        "__package__": "modules.communication.livechat.src",
        "__file__": str(_SOURCE), "asyncio": asyncio, "os": os,
        "datetime": datetime, "logger": logging.getLogger(__name__),
        "_await_owned_completion": _await_owned_completion,
    }
    exec(compile(isolated, str(_SOURCE), "exec"), namespace)

    queues = []

    class FakeQueue:
        def __init__(self, dae):
            self.dae = dae
            self.started = asyncio.Event()
            self.finished = asyncio.Event()
            self.cleanup_started = asyncio.Event()
            self.cleanup_release = None
            self.task = None
            self.failure = None
            queues.append(self)

        async def watch_forever(self):
            self.task = asyncio.current_task()
            self.started.set()
            try:
                if self.failure:
                    raise self.failure
                await asyncio.Event().wait()
            finally:
                # Cleanup needs a scheduling turn: cancellation alone is insufficient.
                self.cleanup_started.set()
                if self.cleanup_release is not None:
                    await self.cleanup_release.wait()
                await asyncio.sleep(0)
                self.finished.set()

    queue_module = ModuleType(_QUEUE_MODULE)
    queue_module.OperatorCommandQueue = FakeQueue
    monkeypatch.setitem(sys.modules, _QUEUE_MODULE, queue_module)
    # Disable every optional startup effect before exercising the real body.
    for key, value in {
        "YT_DEPS_AUTO_LAUNCH": "false", "COMMUNITY_STARTUP_ENGAGE": "false",
        "YT_COMMENT_ONLY_MODE": "false", "YT_AUTOMATION_RUN_ID": "offline-lifecycle",
    }.items():
        monkeypatch.setenv(key, value)
    dae = namespace["AutoModeratorDAE"]()
    dae.operator_manifest_task = None
    dae.enable_ai_monitoring = False
    dae._shorts_scheduler_available = False
    dae._comment_engagement_task = None
    dae.connect = lambda: False
    return dae, queues, queue_module


def assert_reaped(dae, queue, *, started=True):
    assert dae.operator_manifest_task is None
    assert not dae._operator_manifest_run_active
    if started:
        assert queue.finished.is_set()
        assert queue.task.done()


def test_runtime_owner_is_nonreentrant_across_threads(runtime_gates):
    observed = []

    def contender():
        try:
            with runtime_gates.youtube_runtime_owner():
                observed.append('entered')
        except TimeoutError:
            observed.append('busy')

    with runtime_gates.youtube_runtime_owner():
        with pytest.raises(TimeoutError, match='youtube_runtime_owner_busy'):
            with runtime_gates.youtube_runtime_owner():
                pytest.fail('nested owner entered')
        worker = threading.Thread(target=contender)
        worker.start()
        worker.join(timeout=5)
        assert not worker.is_alive()
        assert observed == ['busy']
    with runtime_gates.youtube_runtime_owner():
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize('native_busy', [False, True])
async def test_runtime_owner_refusal_precedes_watcher_and_resets_run(lifecycle, runtime_gates, monkeypatch, native_busy):
    dae, queues, _ = lifecycle

    @contextmanager
    def refused(*_args, **_kwargs):
        raise TimeoutError('native_busy')
        yield

    if native_busy:
        with monkeypatch.context() as patch:
            patch.setattr(runtime_gates, 'runtime_operation_lock', refused)
            with pytest.raises(TimeoutError, match='native_busy'):
                await dae.run()
    else:
        with runtime_gates.youtube_runtime_owner():
            with pytest.raises(TimeoutError, match='youtube_runtime_owner_busy'):
                await dae.run()
    assert queues == [] and dae.operator_manifest_task is None
    assert not dae._operator_manifest_run_active
    await dae.run()
    assert len(queues) == 1
    assert_reaped(dae, queues[0], started=False)


@pytest.mark.asyncio
async def test_runtime_owner_waits_through_repeated_cancellation(lifecycle, runtime_gates):
    dae, queues, _ = lifecycle
    started, comments_started, comments_cleanup = asyncio.Event(), asyncio.Event(), asyncio.Event()
    release_comments, release_watcher = asyncio.Event(), asyncio.Event()

    async def comments():
        comments_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            comments_cleanup.set()
            await release_comments.wait()

    async def body(self):
        queues[-1].cleanup_release = release_watcher
        await wait_event(queues[-1].started)
        self._comment_engagement_task = asyncio.create_task(comments())
        await wait_event(comments_started)
        started.set()
        await asyncio.Event().wait()

    dae._run_dae = MethodType(body, dae)
    running = asyncio.create_task(dae.run())
    try:
        await wait_event(started)
        running.cancel()
        await wait_event(queues[0].cleanup_started)
        await wait_event(comments_cleanup)
        running.cancel()
        release_watcher.set()
        await wait_event(queues[0].finished)
        assert not running.done()
        with pytest.raises(TimeoutError, match='youtube_runtime_owner_busy'):
            with runtime_gates.youtube_runtime_owner():
                pytest.fail('foreground owner entered before comment cleanup')
    finally:
        release_watcher.set()
        release_comments.set()
        with pytest.raises(asyncio.CancelledError):
            await running
    assert_reaped(dae, queues[0])
    assert dae._comment_engagement_task.cancelled()
    with runtime_gates.youtube_runtime_owner():
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['timeout', 'cancel'])
async def test_ordinary_phase3_waits_for_owned_scheduler_worker(monkeypatch, mode):
    from modules.communication.livechat.src.engagement_lifecycle import _await_owned_completion

    tree = ast.parse(_SOURCE.read_text(encoding='utf-8'))
    method = next(node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)
                  and node.name == '_browser_engagement_loop')
    target = next(node for node in ast.walk(method) if isinstance(node, ast.Try) and any(
        isinstance(part, ast.If) and isinstance(part.test, ast.Name) and part.test.id == 'stream_requests'
        for part in node.body))
    exercise = ast.parse('async def exercise():\n    request_worker = None\n').body[0]
    exercise.body.append(target)
    started, release = asyncio.Event(), asyncio.Event()
    stop = threading.Event()

    async def worker(_fn, **kwargs):
        assert kwargs['stop_event'] is stop and 'stream_schedule_requests' not in kwargs
        started.set()
        await release.wait()
        return {}

    monkeypatch.setattr(asyncio, 'to_thread', worker)
    namespace = {'asyncio': asyncio, '_await_owned_completion': _await_owned_completion,
                 'stream_requests': [], 'run_multi_channel_scheduler': object(), 'browser_name': 'chrome',
                 'max_shorts': 1, 'scheduler_stop_event': stop, 'phase3_timeout': .01 if mode == 'timeout' else 10,
                 'logger': logging.getLogger(__name__), 'tag': 'OFFLINE'}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[exercise], type_ignores=[])), str(_SOURCE), 'exec'), namespace)
    running = asyncio.create_task(namespace['exercise']())
    try:
        await wait_event(started)
        if mode == 'cancel':
            running.cancel()
        async def wait_stop():
            while not stop.is_set():
                await asyncio.sleep(.001)
        await asyncio.wait_for(wait_stop(), timeout=5)
        assert not running.done()
    finally:
        release.set()
        if mode == 'cancel':
            with pytest.raises(asyncio.CancelledError):
                await running
        else:
            await running


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["return", "error", "cancel"])
async def test_wrapper_awaits_watcher_cleanup_and_preserves_body_exit(lifecycle, outcome):
    dae, queues, _ = lifecycle

    async def body(self):
        await wait_event(queues[-1].started)
        if outcome == "error":
            raise ValueError("startup failed")
        if outcome == "cancel":
            raise asyncio.CancelledError()
        return "body-result"

    dae._run_dae = MethodType(body, dae)
    if outcome == "error":
        with pytest.raises(ValueError, match="startup failed"):
            await dae.run()
    elif outcome == "cancel":
        with pytest.raises(asyncio.CancelledError):
            await dae.run()
    else:
        assert await dae.run() == "body-result"
    assert len(queues) == 1
    assert queues[0].task.cancelled()
    assert_reaped(dae, queues[0])


@pytest.mark.asyncio
async def test_concurrent_run_cannot_replace_or_duplicate_owned_watcher(lifecycle):
    dae, queues, _ = lifecycle
    body_started = asyncio.Event()

    async def body(self):
        await wait_event(queues[-1].started)
        body_started.set()
        await asyncio.Event().wait()

    dae._run_dae = MethodType(body, dae)
    running = asyncio.create_task(dae.run())
    await wait_event(body_started)
    original_watcher = dae.operator_manifest_task
    try:
        with pytest.raises(RuntimeError, match="already active"):
            await dae.run()
        assert len(queues) == 1
        assert dae.operator_manifest_task is original_watcher
        assert not original_watcher.done()
    finally:
        running.cancel()
        with pytest.raises(asyncio.CancelledError):
            await running
    assert_reaped(dae, queues[0])


@pytest.mark.asyncio
async def test_sequential_runs_have_distinct_reaped_watchers(lifecycle):
    dae, queues, _ = lifecycle

    async def body(self):
        await wait_event(queues[-1].started)

    dae._run_dae = MethodType(body, dae)
    await dae.run()
    assert_reaped(dae, queues[0])
    await dae.run()
    assert_reaped(dae, queues[1])
    assert len(queues) == 2
    assert queues[0].task is not queues[1].task


@pytest.mark.asyncio
async def test_queue_construction_failure_releases_run_guard(lifecycle):
    dae, queues, module = lifecycle
    real_fake = module.OperatorCommandQueue

    def fail(_dae):
        raise OSError("unreadable ledger")

    module.OperatorCommandQueue = fail
    with pytest.raises(OSError, match="unreadable ledger"):
        await dae.run()
    assert dae.operator_manifest_task is None
    assert not dae._operator_manifest_run_active
    module.OperatorCommandQueue = real_fake
    await dae.run()
    assert len(queues) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("body_error", [False, True])
async def test_watcher_failure_is_retrieved_without_masking_body(lifecycle, caplog, body_error):
    dae, queues, _ = lifecycle

    async def body(self):
        queues[-1].failure = RuntimeError("watcher failed")
        await wait_event(queues[-1].finished)
        if body_error:
            raise ValueError("body failed")
        return "body-result"

    dae._run_dae = MethodType(body, dae)
    if body_error:
        with pytest.raises(ValueError, match="body failed"):
            await dae.run()
    else:
        assert await dae.run() == "body-result"
    assert "Operator watcher failed" in caplog.text
    assert_reaped(dae, queues[0])


@pytest.mark.asyncio
@pytest.mark.parametrize("connect_error", [False, True])
async def test_real_run_body_connection_exit_reaps_even_unstarted_watcher(lifecycle, connect_error):
    dae, queues, _ = lifecycle
    observed_tasks = []

    def connect():
        observed_tasks.append(dae.operator_manifest_task)
        if connect_error:
            raise OSError("connect failed")
        return False

    dae.connect = connect
    if connect_error:
        with pytest.raises(OSError, match="connect failed"):
            await dae.run()
    else:
        assert await dae.run() is None
    assert len(observed_tasks) == 1
    assert observed_tasks[0].done()
    assert observed_tasks[0].cancelled()
    assert_reaped(dae, queues[0], started=False)


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel_run", [False, True])
async def test_real_comment_only_exit_preserves_stop_behavior_and_reaps_watcher(
    lifecycle, monkeypatch, cancel_run
):
    dae, queues, _ = lifecycle
    monkeypatch.setenv("YT_COMMENT_ONLY_MODE", "true")
    dae.connect = lambda: True
    comments_started = asyncio.Event()
    finish_comments = asyncio.Event()

    async def comments():
        comments_started.set()
        await finish_comments.wait()

    dae._comment_engagement_task = asyncio.create_task(comments())
    running = asyncio.create_task(dae.run())
    await wait_event(comments_started)
    await wait_event(queues[0].started)
    if cancel_run:
        running.cancel()
    else:
        finish_comments.set()
    # The existing comment-only body intentionally catches CancelledError.
    assert await running is None
    assert dae._comment_engagement_task.done()
    assert dae._comment_engagement_task.cancelled() is cancel_run
    assert_reaped(dae, queues[0])


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel_run", [False, True])
async def test_real_monitoring_stop_reaps_watcher(lifecycle, cancel_run):
    dae, queues, _ = lifecycle
    dae.connect = lambda: True
    monitoring = asyncio.Event()

    async def monitor():
        await wait_event(queues[0].started)
        monitoring.set()
        if not cancel_run:
            raise KeyboardInterrupt()
        await asyncio.Event().wait()

    dae.monitor_chat = monitor
    running = asyncio.create_task(dae.run())
    await wait_event(monitoring)
    if cancel_run:
        running.cancel()
        with pytest.raises(asyncio.CancelledError):
            await running
    else:
        assert await running is None
    assert_reaped(dae, queues[0])
