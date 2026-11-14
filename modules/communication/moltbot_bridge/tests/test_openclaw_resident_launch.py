import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from modules.communication.moltbot_bridge.scripts import launch as openclaw_launch


def test_broker_bootstrap_registers_only_openclaw_specs(monkeypatch):
    broker = MagicMock()
    broker.list_launchable_daes.side_effect = [
        {}, {"openclaw": {}, "openclaw_supervisor": {}}
    ]

    monkeypatch.setattr(openclaw_launch, "_broker_bootstrapped", False)
    monkeypatch.setattr(
        "modules.infrastructure.dae_daemon.src.dae_launch_broker.get_dae_launch_broker",
        lambda: broker,
    )
    monkeypatch.setenv("OPENCLAW_SUPERVISOR_AUTOSTART", "supervisor-original")
    monkeypatch.delenv("OPENCLAW_RESIDENT_AUTOSTART", raising=False)
    monkeypatch.setenv("FOUNDUPS_MCP_AUTOSTART", "mcp-original")

    openclaw_launch._ensure_broker_bootstrap()

    registered = [call.args[0].dae_id for call in broker.register_launch_spec.call_args_list]
    assert registered == ["openclaw", "openclaw_supervisor"]
    broker.start_dae.assert_not_called()
    assert os.environ["OPENCLAW_SUPERVISOR_AUTOSTART"] == "supervisor-original"
    assert "OPENCLAW_RESIDENT_AUTOSTART" not in os.environ
    assert os.environ["FOUNDUPS_MCP_AUTOSTART"] == "mcp-original"


def test_run_openclaw_resident_service_uses_uvicorn(monkeypatch):
    created = {}

    class FakeConfig:
        def __init__(self, app, host, port, log_level, access_log):
            created["config"] = {
                "app": app,
                "host": host,
                "port": port,
                "log_level": log_level,
                "access_log": access_log,
            }

    class FakeServer:
        def __init__(self, config):
            self.config = config
            self.started = False
            self.should_exit = False

        def install_signal_handlers(self):
            raise AssertionError("should be replaced for broker thread usage")

        def run(self):
            self.started = True

    monkeypatch.setitem(
        __import__("sys").modules,
        "uvicorn",
        SimpleNamespace(Config=FakeConfig, Server=FakeServer),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "modules.communication.moltbot_bridge.src.webhook_receiver",
        SimpleNamespace(app=object()),
    )

    result = openclaw_launch.run_openclaw_resident_service(
        host="127.0.0.1",
        port=18801,
    )

    assert created["config"]["host"] == "127.0.0.1"
    assert created["config"]["port"] == 18801
    assert created["config"]["access_log"] is False
    assert result["status"] == "stopped"


def test_stop_openclaw_resident_service_sets_should_exit():
    openclaw_launch._runtime_server = SimpleNamespace(should_exit=False)
    openclaw_launch._runtime_status.clear()
    openclaw_launch._runtime_status.update({"host": "127.0.0.1", "port": 18800})

    result = openclaw_launch.stop_openclaw_resident_service()

    assert result["status"] == "stopping"
    assert openclaw_launch._runtime_server.should_exit is True

    openclaw_launch._runtime_server = None
    openclaw_launch._runtime_status.clear()


def test_run_openclaw_supervisor_service_uses_supervisor_runtime(monkeypatch, tmp_path):
    created = {}
    monkeypatch.setattr(openclaw_launch, "_ensure_broker_bootstrap", lambda: None)

    class FakeSupervisor:
        def __init__(self, repo_root, runtime_mode=None, postmerge_task_id=""):
            created["repo_root"] = repo_root
            created["runtime_mode"] = runtime_mode
            created["postmerge_task_id"] = postmerge_task_id

        def run_forever(self):
            return {"status": "stopped"}

    monkeypatch.setitem(
        __import__("sys").modules,
        "modules.communication.moltbot_bridge.src.openclaw_supervisor",
        SimpleNamespace(OpenClawSupervisor=FakeSupervisor),
    )

    result = openclaw_launch.run_openclaw_supervisor_service(
        repo_root=str(tmp_path), runtime_mode="holoindex_postmerge_only",
        postmerge_task_id="holoindex_postmerge_refresh:" + ("a" * 40),
    )

    assert created["repo_root"] == tmp_path
    assert created["runtime_mode"] == "holoindex_postmerge_only"
    assert created["postmerge_task_id"].endswith("a" * 40)
    assert result["status"] == "stopped"


def test_register_and_release_postmerge_task_require_attested_runtime(tmp_path):
    openclaw_launch._supervisor_runtime = None
    assert openclaw_launch.register_openclaw_supervisor_postmerge_task(
        "task", tmp_path,
    ) == "not_ready"

    runtime = MagicMock()
    runtime.repo_root = tmp_path.resolve()
    runtime._holoindex_postmerge_only = True
    runtime.register_holoindex_postmerge_task.side_effect = [True, False]
    runtime.release_holoindex_postmerge_task.return_value = True
    openclaw_launch._supervisor_runtime = runtime
    try:
        assert openclaw_launch.register_openclaw_supervisor_postmerge_task(
            "task", tmp_path,
        ) == "bound"
        assert openclaw_launch.register_openclaw_supervisor_postmerge_task(
            "other", tmp_path,
        ) == "rejected"
        assert openclaw_launch.release_openclaw_supervisor_postmerge_task(
            "task", tmp_path,
        ) == "released"
    finally:
        openclaw_launch._supervisor_runtime = None


def test_postmerge_binding_rejects_wrong_root_or_general_runtime(tmp_path):
    runtime = MagicMock()
    runtime.repo_root = tmp_path.resolve()
    runtime._holoindex_postmerge_only = False
    openclaw_launch._supervisor_runtime = runtime
    try:
        assert openclaw_launch.register_openclaw_supervisor_postmerge_task(
            "task", tmp_path,
        ) == "rejected"
        runtime._holoindex_postmerge_only = True
        assert openclaw_launch.register_openclaw_supervisor_postmerge_task(
            "task", tmp_path / "other",
        ) == "rejected"
        runtime.register_holoindex_postmerge_task.assert_not_called()
    finally:
        openclaw_launch._supervisor_runtime = None


@pytest.mark.parametrize(
    "module_name",
    [
        "modules.communication.moltbot_bridge.src.webhook_receiver",
        "modules.communication.moltbot_bridge.src.openclaw_supervisor",
        "modules.communication.moltbot_bridge.scripts.run_task",
        "modules.infrastructure.idle_automation.src.holoindex_postmerge_executor",
        "uvicorn",
    ],
)
def test_postmerge_runtime_dependency_preflight_is_fail_closed(
    monkeypatch, module_name,
):
    monkeypatch.setitem(__import__("sys").modules, module_name, None)
    assert openclaw_launch.openclaw_postmerge_runtime_dependencies_ready() is False


def test_stop_openclaw_supervisor_service_calls_stop():
    runtime = MagicMock()
    openclaw_launch._supervisor_runtime = runtime
    openclaw_launch._supervisor_status.clear()
    openclaw_launch._supervisor_status.update({"repo_root": "O:/Foundups-Agent"})

    result = openclaw_launch.stop_openclaw_supervisor_service()

    assert result["status"] == "stopping"
    runtime.stop.assert_called_once()
    openclaw_launch._supervisor_runtime = None
    openclaw_launch._supervisor_status.clear()
