from types import SimpleNamespace

from modules.communication.moltbot_bridge.scripts import launch as openclaw_launch


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
