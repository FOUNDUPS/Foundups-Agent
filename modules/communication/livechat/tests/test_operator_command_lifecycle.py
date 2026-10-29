"""Offline, source-bound tests for ownership of the operator watcher.

Compile the actual run/_run_dae AST without importing the DAE's heavyweight
module graph or calling its constructor. The public run method and the real
startup/stop branches execute below; auth, browser, model, and manifest IO do
not. This proves bounded lifecycle behavior, not full-module/runtime readiness.
"""

import ast
import asyncio
from datetime import datetime
import logging
import os
from pathlib import Path
import sys
from types import MethodType, ModuleType

import pytest


_SOURCE = Path(__file__).resolve().parents[1] / "src" / "auto_moderator_dae.py"
_QUEUE_MODULE = "modules.communication.livechat.src.operator_command_queue"


async def wait_event(event):
    """Bound regression failures instead of leaving a test waiting forever."""
    await asyncio.wait_for(event.wait(), timeout=5)


@pytest.fixture
def lifecycle(monkeypatch):
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
    }
    exec(compile(isolated, str(_SOURCE), "exec"), namespace)

    queues = []

    class FakeQueue:
        def __init__(self, dae):
            self.dae = dae
            self.started = asyncio.Event()
            self.finished = asyncio.Event()
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
