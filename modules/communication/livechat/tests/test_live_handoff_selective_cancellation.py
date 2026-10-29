"""Offline source-bound PR841 handoff tests; no application imports or live effects.

The real owner method bodies are compiled from their AST. Browser, auth, model,
telemetry and provider boundaries are replaced explicitly. This is bounded local
lifecycle evidence, not full-package or native/operational YouTube qualification.
"""
import ast
import asyncio
import logging
import importlib.util
import os
from pathlib import Path
import socket
import sys
import time
import threading
from types import ModuleType, SimpleNamespace

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"


def source_class(filename, classname, namespace, methods=None):
    """Compile unchanged production methods, retaining their original locations."""
    path = SRC / filename
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == classname)
    if methods is not None:
        node.body = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in methods]
    node.bases = []
    module = ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), node], type_ignores=[]))
    namespace.update(__file__=str(path), __name__=__name__)
    exec(compile(module, str(path), "exec"), namespace)
    return namespace[classname]


def source_function(filename, name, namespace):
    path = SRC / filename
    node = next(n for n in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(path), "exec"), namespace)
    return namespace[name]


@pytest.fixture
def process_cases(monkeypatch):
    """Reuse the companion's effect-free loaders; no application package import."""
    path = Path(__file__).with_name("test_engagement_runner_lifecycle.py")
    spec = importlib.util.spec_from_file_location("pr841_process_cases", path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def runner_source(process_cases, monkeypatch):
    return process_cases._load_runner_source(monkeypatch)


def _offline_subprocess_runner(module, tmp_path, *, finish=False):
    script = tmp_path / "owned_child.py"
    script.write_text("import time\nprint('READY', flush=True)\n" + ("" if finish else "time.sleep(30)\n"), encoding="utf-8")
    runner = module.SubprocessRunner(tmp_path)
    runner.engagement_script = script
    return runner


async def _reap_test_process(process):
    if process.returncode is None:
        process.kill()
    await process.wait()


@pytest.fixture
def owners(monkeypatch, process_cases):
    def denied(*args, **kwargs):
        raise AssertionError("Network/provider effects forbidden in handoff tests")
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    signal = ModuleType("modules.platform_integration.stream_resolver.src.live_stream_signal")
    signal.get_live_channel = lambda: None
    monkeypatch.setitem(sys.modules, signal.__name__, signal)
    namespace = {"asyncio": asyncio, "os": os, "time": time, "logger": logging.getLogger(__name__)}
    helper = process_cases.load_lifecycle(monkeypatch)
    namespace.update({name: value for name,value in vars(helper).items() if callable(value)})
    cls = source_class("multi_channel_coordinator.py", "MultiChannelCoordinator", namespace)
    live = {"channel": None}
    coordinator = cls(
        log_studio_context=lambda *a: None,
        verify_studio_inbox_clear=lambda *a: None,
        reconnect_chrome_driver=lambda *a: None,
        reconnect_edge_driver=lambda *a: None,
        detect_current_channel_id=lambda *a: None,
        update_engagement_status=lambda *a: None,
        set_active_channel=lambda *a: None,
        is_live_stream_pending=lambda: False,
        get_confirmed_live_channel=lambda: live["channel"],
    )
    return coordinator, live, signal, namespace


async def tick_until(predicate):
    async def wait():
        while not predicate():
            await asyncio.sleep(0)
    await asyncio.wait_for(wait(), 3)


@pytest.mark.asyncio
@pytest.mark.parametrize("port", [9222, 9223])
async def test_confirmed_session_blocks_real_dispatch_without_file_signal(owners, port):
    coordinator, live, signal, _ = owners
    calls = []
    async def run(**kwargs):
        calls.append(kwargs)
        return {"stats": {"comments_processed": 1}}
    runner = SimpleNamespace(run_engagement=run)
    live["channel"] = "live"
    result = await coordinator._run_owned_engagement(runner, channel_id="live", video_id=None, max_comments=1, browser_port=port)
    assert result["deferred"] == "live_channel"
    assert calls == []
    await coordinator._run_owned_engagement(runner, channel_id="other", video_id=None, max_comments=1, browser_port=port)
    assert [c["channel_id"] for c in calls] == ["other"]


@pytest.mark.asyncio
@pytest.mark.parametrize("live_port", [9222, 9223])
async def test_matching_operation_settles_and_other_browser_continues(owners, live_port):
    coordinator, live, _, _ = owners
    started, finished = set(), set()
    release = asyncio.Event()
    async def run(**kwargs):
        channel = kwargs["channel_id"]
        started.add(channel)
        try:
            await release.wait()
        finally:
            await asyncio.sleep(0)
            finished.add(channel)
        return {"stats": {"comments_processed": 1}}
    runner = SimpleNamespace(run_engagement=run, supports_settled_cancellation=True)
    first = asyncio.create_task(coordinator._run_owned_engagement(runner, channel_id="live", video_id=None, max_comments=1, browser_port=live_port))
    other = asyncio.create_task(coordinator._run_owned_engagement(runner, channel_id="other", video_id=None, max_comments=1, browser_port=9223 if live_port == 9222 else 9222))
    try:
        await tick_until(lambda: len(started) == 2)
        live["channel"] = "live"
        await coordinator.settle_channel("live")
        assert (await first)["deferred"] == "live_channel"
        assert finished == {"live"}
        assert not other.done()
        assert not asyncio.current_task().cancelling()
    finally:
        release.set()
        await asyncio.gather(first, other, return_exceptions=True)
    assert not coordinator._active_engagements


@pytest.mark.asyncio
async def test_unknown_mode_waits_actual_completion_without_cancellation(owners):
    coordinator, live, _, _ = owners
    release = asyncio.Event()
    started = asyncio.Event()
    async def run(**kwargs):
        started.set()
        await release.wait()
        return {"stats": {"comments_processed": 0}}
    runner = SimpleNamespace(run_engagement=run)
    operation = asyncio.create_task(coordinator._run_owned_engagement(runner, channel_id="live", video_id=None, max_comments=1))
    await asyncio.wait_for(started.wait(), 3)
    live["channel"] = "live"
    settlement = asyncio.create_task(coordinator.settle_channel("live"))
    try:
        await asyncio.sleep(0)
        assert not settlement.done()
        assert all(not t.cancelling() for t in coordinator._active_engagements)
    finally:
        release.set()
        await operation
        await settlement


@pytest.mark.asyncio
async def test_identity_change_between_create_and_start_prevents_dispatch(owners):
    coordinator, live, _, _ = owners
    async def forbidden(**kwargs):
        pytest.fail("late confirmed channel dispatched")
    runner = SimpleNamespace(run_engagement=forbidden)
    task = asyncio.create_task(coordinator._run_owned_engagement(runner, channel_id="live", video_id=None, max_comments=1))
    await asyncio.sleep(0)  # owner task registered; runner task has not run yet
    live["channel"] = "live"
    assert (await task)["deferred"] == "live_channel"

@pytest.fixture
def dae_owner(owners):
    coordinator, live, signal, namespace = owners
    import threading
    namespace.update(threading=threading, group_channels_by_browser=lambda **k: {"chrome": [], "edge": []})
    cls = source_class("auto_moderator_dae.py", "AutoModeratorDAE", namespace, {
        "_get_confirmed_live_channel", "_run_confirmed_live_chat", "terminate_comment_engagement",
        "_comment_engagement_loop", "_ensure_multi_channel_coordinator", "_browser_engagement_loop", "_run_comment_engagement",
    })
    source_function("auto_moderator_dae.py", "_env_truthy", namespace)
    dae = cls()
    dae._confirmed_live_channel_id = None
    dae._live_chat_active = False
    dae._live_stream_pending = True
    dae.multi_channel_coordinator = coordinator
    coordinator.get_confirmed_live_channel = dae._get_confirmed_live_channel
    dae._comment_engagement_task = None
    dae.telemetry = None
    dae.current_stream_id = None
    dae._rotation_supervisors = {}
    return dae, coordinator, namespace


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["normal", "poll_error", "cancel", "settle_error"])
async def test_confirmed_handoff_reserves_before_settlement_and_always_clears(dae_owner, outcome):
    dae, coordinator, _ = dae_owner
    order = []
    async def initialize():
        order.append("initialize")
        return True
    async def settle(channel):
        assert channel == "actual-channel"
        assert dae._get_confirmed_live_channel() == channel
        assert not dae._live_chat_active
        order.append("settle")
        await asyncio.sleep(0)
        if outcome == "settle_error":
            raise RuntimeError("cleanup failed")
    coordinator.settle_channel = settle
    async def poll():
        assert dae._get_confirmed_live_channel() == "actual-channel"
        assert dae._live_chat_active
        order.append("poll")
        if outcome == "cancel":
            raise asyncio.CancelledError
        if outcome == "poll_error":
            raise ValueError("offline poll failure")
    dae.livechat = SimpleNamespace(initialize=initialize, channel_id="actual-channel", live_chat_id="confirmed-chat",
                                   youtube=object(), run_polling_loop=poll, stop_listening=lambda: order.append("stop"))
    if outcome == "cancel":
        with pytest.raises(asyncio.CancelledError):
            await dae._run_confirmed_live_chat()
    else:
        await dae._run_confirmed_live_chat()
    assert order == (["initialize", "settle", "stop"] if outcome == "settle_error" else ["initialize", "settle", "poll", "stop"])
    assert dae._get_confirmed_live_channel() is None
    assert not dae._live_chat_active


@pytest.mark.asyncio
@pytest.mark.parametrize("initialized,channel,chat,service", [
    (False,"actual","chat",True), (True,None,"chat",True), (True," ","chat",True),
    (True,"actual",None,True), (True,"actual"," ",True), (True,"actual","chat",False),
])
async def test_unconfirmed_identity_keeps_comments_without_polling(dae_owner, initialized, channel, chat, service):
    dae, coordinator, _ = dae_owner
    async def initialize():
        return initialized
    async def forbidden(*args):
        pytest.fail("unconfirmed session entered handoff/polling")
    coordinator.settle_channel = forbidden
    dae.livechat = SimpleNamespace(initialize=initialize, channel_id=channel, live_chat_id=chat, youtube=service, run_polling_loop=forbidden)
    await dae._run_confirmed_live_chat()
    assert dae._get_confirmed_live_channel() is None
    assert not dae._live_chat_active


@pytest.mark.asyncio
async def test_default_termination_awaits_real_supervisor_children(dae_owner):
    dae, coordinator, _ = dae_owner
    started, cleaned = set(), set()
    async def browser(**kwargs):
        name = kwargs["browser_name"]
        started.add(name)
        try:
            await asyncio.Event().wait()
        finally:
            await asyncio.sleep(0)
            cleaned.add(name)
    dae._browser_engagement_loop = browser
    dae._comment_engagement_task = asyncio.create_task(dae._comment_engagement_loop(None, 1, "subprocess"))
    await tick_until(lambda: len(started) == 2)
    await dae.terminate_comment_engagement()
    assert cleaned == {"chrome", "edge"}
    assert dae._comment_engagement_task is None
    await dae.terminate_comment_engagement()  # absent/default repeat is harmless


@pytest.mark.asyncio
async def test_live_handoff_preserves_real_supervisor_and_both_browser_tasks(dae_owner):
    dae, coordinator, _ = dae_owner
    tasks = {}
    async def browser(**kwargs):
        tasks[kwargs["browser_name"]] = asyncio.current_task()
        await asyncio.Event().wait()
    dae._browser_engagement_loop = browser
    supervisor = asyncio.create_task(dae._comment_engagement_loop(None, 1, "subprocess"))
    dae._comment_engagement_task = supervisor
    try:
        await tick_until(lambda: len(tasks) == 2)
        dae._confirmed_live_channel_id = "actual"
        await dae.terminate_comment_engagement(for_live_handoff=True)
        assert not supervisor.done()
        assert all(not task.done() and not task.cancelling() for task in tasks.values())
    finally:
        await dae.terminate_comment_engagement()


def test_monitor_routes_to_confirmed_owner_and_preserves_default_restart():
    tree = ast.parse((SRC / "auto_moderator_dae.py").read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "AutoModeratorDAE")
    monitor = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "monitor_chat")
    calls = [n for n in ast.walk(monitor) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    assert sum(c.func.attr == "_run_confirmed_live_chat" for c in calls) == 1
    restart = [c for c in calls if c.func.attr == "terminate_comment_engagement"]
    assert len(restart) == 1 and not restart[0].args and not restart[0].keywords


def _fake_browser_state():
    state = {"navigations": [], "swaps": [], "oops": False, "hook": lambda: None, "comments": 0}
    class Driver:
        current_url = "https://studio.youtube.com/"
        def get(self, url):
            state["navigations"].append(url)
            state["hook"]()
        def refresh(self):
            state["hook"]()
        def execute_script(self, script):
            return state["comments"] if "ytcp-comment-thread" in script else True
    driver = Driver()
    class Swapper:
        def __init__(self, driver):
            self.driver = driver
        async def swap_to(self, account):
            state["swaps"].append(account)
            return True
        async def swap_from_oops_page(self, account, **kwargs):
            state["swaps"].append(account)
            return False
    return state, driver, Swapper


@pytest.fixture
def browser_boundaries(owners, monkeypatch):
    coordinator, live, signal, namespace = owners
    source_function("multi_channel_coordinator.py", "_env_truthy", namespace)
    source_function("multi_channel_coordinator.py", "_is_session_error", namespace)
    state, driver, Swapper = _fake_browser_state()
    def stub(name, **attrs):
        module = ModuleType(name)
        module.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, module)
    stub("modules.infrastructure.dependency_launcher.src.dae_dependencies",
         connect_chrome_with_retry=lambda **kw: driver, connect_edge_with_retry=lambda **kw: driver,
         STUDIO_FILTER="offline", EDGE_DEBUG_PORT=9223, CHROME_DEBUG_PORT=9222)
    stub("modules.communication.video_comments.skillz.tars_account_swapper.account_swapper_skill", TarsAccountSwapper=Swapper)
    stub("modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker",
         ScheduleTracker=lambda channel: SimpleNamespace(has_sufficient_coverage=lambda days: (True, days)))
    namespace.update(CHANNEL_FALLBACKS={"Other": "Live"}, CHANNEL_IDS={"Live": "live"}, ACCOUNT_SECTIONS={},
                     _is_oops_page=lambda driver: state["oops"], _detect_wrong_account_scenario=lambda *a, **k: None)
    async def no_delay(*args):
        await asyncio.sleep(0)
    namespace["asyncio"] = SimpleNamespace(**{**asyncio.__dict__, "sleep": no_delay})
    async def detect(*args):
        return None
    async def verify(*args):
        return True
    coordinator.detect_current_channel_id = detect
    coordinator.verify_studio_inbox_clear = verify
    for key, value in {
        "YT_SHORTS_PER_CHANNEL_ENABLED": "false", "YT_SHORTS_SCHEDULING_ENABLED": "false",
        "YT_VIDEO_INDEXING_ENABLED": "false", "LN_GROUP_ROTATION_ENABLED": "false",
        "YT_AGENTIC_AUDIT_ENABLED": "true", "YT_STAY_UNTIL_COMMENTS_CLEAR": "false",
        "YT_INBOX_VERIFY_RETRIES": "1", "YT_STOP_ROTATION_ON_LIVE": "false",
    }.items():
        monkeypatch.setenv(key, value)
    return coordinator, live, state


@pytest.mark.asyncio
@pytest.mark.parametrize("browser,port", [("chrome",9222),("edge",9223)])
async def test_actual_browser_audit_and_dispatch_exclude_confirmed_channel(browser_boundaries, browser, port):
    coordinator, live, state = browser_boundaries
    live["channel"] = "live"
    calls = []
    async def run(**kwargs):
        calls.append(kwargs)
        return {"stats": {"comments_processed": 1, "all_processed": True}}
    runner = SimpleNamespace(run_engagement=run)
    result = await getattr(coordinator, f"_run_{browser}_engagement")(runner, [("Live","live"),("Other","other")], 1, False)
    assert result == 1
    assert [(c["channel_id"], c["browser_port"]) for c in calls] == [("other",port)]
    assert all("/live/" not in url for url in state["navigations"])
    assert "Live" not in state["swaps"]


@pytest.mark.asyncio
@pytest.mark.parametrize("browser", ["chrome","edge"])
async def test_actual_browser_fallback_cannot_navigate_into_confirmed_channel(browser_boundaries, monkeypatch, browser):
    coordinator, live, state = browser_boundaries
    monkeypatch.setenv("YT_AGENTIC_AUDIT_ENABLED", "false")
    live["channel"] = "live"
    state["oops"] = True
    async def forbidden(**kwargs):
        pytest.fail("fallback entered protected channel")
    result = await getattr(coordinator, f"_run_{browser}_engagement")(
        SimpleNamespace(run_engagement=forbidden), [("Other","other")], 1, False)
    assert result == 0
    assert "Live" not in state["swaps"]
    assert all("/live/" not in url for url in state["navigations"])


@pytest.mark.asyncio
@pytest.mark.parametrize("browser", ["chrome","edge"])
async def test_actual_browser_identity_change_during_preparation_blocks_runner(browser_boundaries, monkeypatch, browser):
    coordinator, live, state = browser_boundaries
    monkeypatch.setenv("YT_AGENTIC_AUDIT_ENABLED", "false")
    state["hook"] = lambda: live.update(channel="other")
    async def forbidden(**kwargs):
        pytest.fail("newly confirmed channel dispatched after preparation await")
    result = await getattr(coordinator, f"_run_{browser}_engagement")(
        SimpleNamespace(run_engagement=forbidden), [("Other","other")], 1, False)
    assert result == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("port", [9222,9223])
async def test_actual_retry_rechecks_identity_after_verification_await(owners, port):
    coordinator, live, _, _ = owners
    async def verify(*args):
        await asyncio.sleep(0)
        live["channel"] = "live"
        return False
    coordinator.verify_studio_inbox_clear = verify
    async def forbidden(**kwargs):
        pytest.fail("retry dispatched after live confirmation")
    assert await coordinator._verify_and_retry_engagement(
        None, SimpleNamespace(run_engagement=forbidden), "live", "Live", 1, port, 2, False, None, False) == 2


@pytest.mark.asyncio
async def test_concurrent_session_cannot_overwrite_or_clear_older_owner(dae_owner):
    dae, coordinator, _ = dae_owner
    initializing, release = asyncio.Event(), asyncio.Event()
    async def initialize():
        initializing.set()
        await release.wait()
        return True
    async def poll():
        assert dae._get_confirmed_live_channel() == "actual"
    dae.livechat = SimpleNamespace(initialize=initialize, channel_id="actual", live_chat_id="chat", youtube=True,
                                   run_polling_loop=poll, stop_listening=lambda: None)
    first = asyncio.create_task(dae._run_confirmed_live_chat())
    try:
        await asyncio.wait_for(initializing.wait(), 3)
        with pytest.raises(RuntimeError, match="already owned"):
            await dae._run_confirmed_live_chat()
        assert dae._live_handoff_running
    finally:
        release.set()
        await first
    assert not dae._live_handoff_running
    assert dae._get_confirmed_live_channel() is None

def _capture_handoff_children(monkeypatch, during_spawn):
    original_spawn = asyncio.create_subprocess_exec
    processes, waited = {}, set()
    spawned, release_spawn = asyncio.Event(), asyncio.Event()
    async def spawn(*args, **kwargs):
        channel = args[args.index("--channel") + 1]
        process = await original_spawn(args[0], "-I", "-S", "-B", *args[1:], **kwargs)
        processes[channel] = process
        original_wait = process.wait
        async def wait():
            code = await original_wait()
            waited.add(channel)
            return code
        process.wait = wait
        if len(processes) == 2:
            spawned.set()
        if channel == "actual" and during_spawn:
            await release_spawn.wait()
        return process
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    return processes, waited, spawned, release_spawn


@pytest.mark.asyncio
@pytest.mark.parametrize("port,during_spawn", [(9222,False),(9223,False),(9222,True),(9223,True)])
async def test_real_matching_child_is_reaped_before_polling_other_child_survives(
    dae_owner, runner_source, tmp_path, monkeypatch, port, during_spawn
):
    dae, coordinator, _ = dae_owner
    runner = _offline_subprocess_runner(runner_source, tmp_path)
    processes, waited, spawned, release_spawn = _capture_handoff_children(monkeypatch, during_spawn)
    matching = asyncio.create_task(coordinator._run_owned_engagement(runner, channel_id="actual", video_id=None, max_comments=1, browser_port=port))
    other = asyncio.create_task(coordinator._run_owned_engagement(runner, channel_id="other", video_id=None, max_comments=1, browser_port=9223 if port == 9222 else 9222))
    polled = []
    async def initialize():
        return True
    async def poll():
        assert processes["actual"].returncode is not None
        assert "actual" in waited
        assert processes["other"].returncode is None
        assert not other.done()
        polled.append(True)
    dae.livechat = SimpleNamespace(initialize=initialize, channel_id="actual", live_chat_id="chat", youtube=True,
                                   run_polling_loop=poll, stop_listening=lambda: None)
    handoff = None
    try:
        await asyncio.wait_for(spawned.wait(), 5)
        handoff = asyncio.create_task(dae._run_confirmed_live_chat())
        await tick_until(lambda: dae._get_confirmed_live_channel() == "actual")
        if during_spawn:
            await asyncio.sleep(0)
            assert not handoff.done() and not polled
        release_spawn.set()
        await asyncio.wait_for(handoff, 5)
        assert polled == [True]
        assert (await matching)["deferred"] == "live_channel"
        assert not other.done()
    finally:
        release_spawn.set()
        if handoff and not handoff.done():
            handoff.cancel()
        for task in (matching, other):
            if not task.done():
                task.cancel()
        await asyncio.gather(*(t for t in (matching, other, handoff) if t), return_exceptions=True)
        for process in processes.values():
            await _reap_test_process(process)


@pytest.mark.parametrize("file_state", ["missing", "stale", "fresh"])
def test_actual_signal_ttl_does_not_expire_confirmed_session(owners, tmp_path, file_state):
    import json
    from typing import Dict, Optional
    coordinator, live, signal, _ = owners
    path = SRC.parents[2] / "platform_integration" / "stream_resolver" / "src" / "live_stream_signal.py"
    namespace = {"json": json, "time": time, "Dict": Dict, "Optional": Optional,
                 "logger": logging.getLogger(__name__), "_get_signal_path": lambda: tmp_path / "signal.json"}
    tree = ast.parse(path.read_text(encoding="utf-8"))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {"read_live_signal", "get_live_channel"}]
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), namespace)
    if file_state != "missing":
        (tmp_path / "signal.json").write_text(json.dumps({"live": True, "channel_id": "live", "written_at": time.time() - (301 if file_state == "stale" else 0)}), encoding="utf-8")
    signal.get_live_channel = namespace["get_live_channel"]
    assert signal.get_live_channel() == ("live" if file_state == "fresh" else None)
    live["channel"] = "live"
    assert coordinator._is_live_channel("live")
    assert not coordinator._is_live_channel("other")
    live["channel"] = None
    assert coordinator._is_live_channel("live") is (file_state == "fresh")

@pytest.mark.asyncio
@pytest.mark.parametrize("port", [9222,9223])
async def test_restart_and_inbox_clear_dispatch_share_actual_owner(dae_owner, port):
    dae, coordinator, namespace = dae_owner
    namespace["group_channels_by_browser"] = lambda **kw: {"edge": [{"id":"actual"}] if port == 9223 else []}
    dae._log_studio_context = lambda *a, **kw: None
    dae._comment_engagement_status = {}
    entered, release = asyncio.Event(), asyncio.Event()
    async def run(**kwargs):
        assert kwargs["browser_port"] == port
        entered.set()
        await release.wait()
        return {"stats": {"comments_processed": 1}}
    runner = SimpleNamespace(run_engagement=run, supports_settled_cancellation=True)
    operation = asyncio.create_task(dae._run_comment_engagement(runner, "actual", None, 1, "subprocess"))
    try:
        await asyncio.wait_for(entered.wait(), 3)
        assert any(cid == "actual" and browser == port for cid,browser,r in coordinator._active_engagements.values())
        dae._confirmed_live_channel_id = "actual"
        await dae.terminate_comment_engagement(for_live_handoff=True)
        await operation
        assert "actual" not in dae._comment_engagement_status
    finally:
        release.set()
        await asyncio.gather(operation, return_exceptions=True)

@pytest.mark.asyncio
@pytest.mark.parametrize("browser,enabled", [("chrome",True),("edge",True),("chrome",False),("edge",False)])
async def test_existing_browser_loop_preserves_phase2_indexing_gate(dae_owner, monkeypatch, browser, enabled):
    dae, _, namespace = dae_owner
    calls, phases = [], []
    async def index(**kwargs):
        calls.append(kwargs["browser"])
    module = ModuleType("modules.ai_intelligence.video_indexer.src.studio_ask_indexer")
    module.run_video_indexing_cycle = index
    monkeypatch.setitem(sys.modules, module.__name__, module)
    telemetry = ModuleType("modules.communication.livechat.src.breadcrumb_telemetry")
    telemetry.get_breadcrumb_telemetry = lambda: SimpleNamespace(store_breadcrumb=lambda **k: None)
    monkeypatch.setitem(sys.modules, telemetry.__name__, telemetry)
    discord = ModuleType("modules.communication.livechat.src.discord_status_pusher")
    discord.push_idle = lambda *a: None
    monkeypatch.setitem(sys.modules, discord.__name__, discord)
    namespace["__package__"] = "modules.communication.livechat.src"
    namespace["get_activity_router"] = lambda: SimpleNamespace(signal_activity_complete=lambda *a, **k: phases.append(a[0]))
    namespace["ActivityType"] = SimpleNamespace(COMMENT_ENGAGEMENT="comments", VIDEO_INDEXING="index", SHORTS_SCHEDULING="shorts")
    async def stop(*args):
        raise asyncio.CancelledError
    namespace["asyncio"] = SimpleNamespace(**{**asyncio.__dict__, "sleep": stop})
    dae._shorts_scheduler_available = False
    dae._skill_trigger = None
    dae._shorts_total_cycles = 0
    dae._shorts_total_scheduled = 0
    dae._shorts_last_cycle_result = None
    for key,value in {"YT_COMMENTS_ENABLED":"false", "YT_SHORTS_SCHEDULING_ENABLED":"false",
                      "LN_FEED_ENGAGEMENT_ENABLED":"false", "YT_USE_ROTATION_SUPERVISOR":"false",
                      "YT_VIDEO_INDEXING_ENABLED":"true" if enabled else "false"}.items():
        monkeypatch.setenv(key,value)
    with pytest.raises(asyncio.CancelledError):
        await dae._browser_engagement_loop(browser, None, 1, "subprocess")
    assert calls == ([browser] if enabled else [])
    assert phases.count("comments") >= 2  # Reached the actual end-of-cycle idle branch.

@pytest.mark.asyncio
async def test_stop_failure_still_reaps_heartbeat_and_clears_identity(dae_owner):
    dae, _, _ = dae_owner
    started, finished = asyncio.Event(), asyncio.Event()
    async def heartbeat():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            await asyncio.sleep(0)
            finished.set()
    dae._heartbeat_loop = heartbeat
    dae.telemetry = object()
    async def initialize():
        return True
    async def poll():
        await asyncio.wait_for(started.wait(), 3)
    def stop():
        raise RuntimeError("offline end-session save failed")
    dae.livechat = SimpleNamespace(initialize=initialize, channel_id="actual", live_chat_id="chat", youtube=True,
                                   run_polling_loop=poll, stop_listening=stop)
    with pytest.raises(RuntimeError, match="end-session save"):
        await dae._run_confirmed_live_chat()
    assert finished.is_set()
    assert dae._get_confirmed_live_channel() is None
    assert not dae._live_chat_active and not dae._live_handoff_running


@pytest.mark.asyncio
async def test_failed_cleanup_retains_owner_and_blocks_second_handoff(dae_owner):
    dae, coordinator, _ = dae_owner
    started = asyncio.Event()
    async def run(**kwargs):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            raise PermissionError("offline child termination denied")
    runner = SimpleNamespace(run_engagement=run, supports_settled_cancellation=True)
    operation = asyncio.create_task(coordinator._run_owned_engagement(runner, channel_id="actual", video_id=None, max_comments=1))
    await asyncio.wait_for(started.wait(), 3)
    polled = []
    async def initialize():
        return True
    async def poll():
        polled.append(True)
    dae.livechat = SimpleNamespace(initialize=initialize, channel_id="actual", live_chat_id="chat", youtube=True,
                                   run_polling_loop=poll, stop_listening=lambda: None)
    await dae._run_confirmed_live_chat()
    with pytest.raises(PermissionError, match="termination denied"):
        await operation
    assert len(coordinator._active_engagements) == 1
    await dae._run_confirmed_live_chat()
    assert not polled
    assert len(coordinator._active_engagements) == 1
    with pytest.raises(RuntimeError, match="unresolved cleanup"):
        await coordinator._run_owned_engagement(runner, channel_id="actual", video_id=None, max_comments=1)
    assert dae._get_confirmed_live_channel() is None

@pytest.mark.asyncio
async def test_failed_rotation_instance_cannot_be_replaced_or_forgotten(dae_owner):
    dae, _, namespace = dae_owner
    retained = SimpleNamespace(_owned_tasks={"actual": object()})
    async def fail(**kwargs):
        raise PermissionError("offline rotation cleanup denied")
    retained.run_rotation = fail
    with pytest.raises(PermissionError, match="cleanup denied"):
        await namespace["run_owned_rotation"](dae, retained, "chrome", 1, "comments")
    assert dae._rotation_supervisors["chrome"] is retained
    replacement = SimpleNamespace(_owned_tasks={}, run_rotation=fail)
    with pytest.raises(RuntimeError, match="unresolved child state"):
        await namespace["run_owned_rotation"](dae, replacement, "chrome", 1, "comments")
    assert dae._rotation_supervisors["chrome"] is retained
    polled = []
    async def initialize():
        return True
    async def settle(channel):
        raise PermissionError("offline rotation cleanup denied")
    async def poll():
        polled.append(True)
    retained.settle_channel = settle
    dae.livechat = SimpleNamespace(initialize=initialize, channel_id="actual", live_chat_id="chat", youtube=True,
                                   run_polling_loop=poll, stop_listening=lambda: None)
    await dae._run_confirmed_live_chat()
    assert not polled
