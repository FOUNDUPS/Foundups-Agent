import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

_MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"
_MAIN_SPEC = importlib.util.spec_from_file_location("foundups_test_main", _MAIN_PATH)
assert _MAIN_SPEC and _MAIN_SPEC.loader
main = importlib.util.module_from_spec(_MAIN_SPEC)
_MAIN_SPEC.loader.exec_module(main)


def test_bootstrap_runtime_dae_launches_registers_openclaw(monkeypatch):
    daemon = MagicMock()
    daemon.running = True
    broker = MagicMock()
    broker.list_launchable_daes.return_value = {"openclaw": {}}
    broker.get_runtime_status.return_value = {"running": False}

    monkeypatch.setenv("OPENCLAW_RESIDENT_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_RESIDENT_AUTOSTART", "1")
    monkeypatch.setenv("OPENCLAW_SUPERVISOR_ENABLED", "0")

    with patch.object(main, "get_central_daemon", return_value=daemon), patch.object(
        main, "get_dae_launch_broker", return_value=broker
    ):
        main.bootstrap_runtime_dae_launches()

    specs = [call.args[0] for call in broker.register_launch_spec.call_args_list]
    openclaw_specs = [spec for spec in specs if spec.dae_id == "openclaw"]
    assert len(openclaw_specs) == 1
    assert openclaw_specs[0].stop_callable is not None
    broker.start_dae.assert_called_once_with("openclaw", actor_id="0102")


def test_bootstrap_runtime_dae_launches_registers_pqn_simulation(monkeypatch):
    daemon = MagicMock()
    daemon.running = True
    broker = MagicMock()
    broker.list_launchable_daes.return_value = {"openclaw": {}, "pqn_simulation": {}}
    broker.get_runtime_status.return_value = {"running": True}

    monkeypatch.setenv("OPENCLAW_RESIDENT_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_RESIDENT_AUTOSTART", "1")

    with patch.object(main, "get_central_daemon", return_value=daemon), patch.object(
        main, "get_dae_launch_broker", return_value=broker
    ):
        main.bootstrap_runtime_dae_launches()

    specs = [call.args[0] for call in broker.register_launch_spec.call_args_list]
    simulation_specs = [spec for spec in specs if spec.dae_id == "pqn_simulation"]
    assert len(simulation_specs) == 1
    assert simulation_specs[0].start_callable is main.run_pqn_simulation_once


def test_bootstrap_runtime_dae_launches_registers_holodae_stop_hook(monkeypatch):
    daemon = MagicMock()
    daemon.running = True
    broker = MagicMock()
    broker.list_launchable_daes.return_value = {"holodae": {}}
    broker.get_runtime_status.return_value = {"running": True}

    monkeypatch.setenv("OPENCLAW_RESIDENT_ENABLED", "0")
    monkeypatch.setenv("OPENCLAW_SUPERVISOR_ENABLED", "0")

    with patch.object(main, "get_central_daemon", return_value=daemon), patch.object(
        main, "get_dae_launch_broker", return_value=broker
    ):
        main.bootstrap_runtime_dae_launches()

    specs = [call.args[0] for call in broker.register_launch_spec.call_args_list]
    holodae_specs = [spec for spec in specs if spec.dae_id == "holodae"]
    assert len(holodae_specs) == 1
    assert holodae_specs[0].stop_callable is main.stop_holodae


def test_bootstrap_runtime_dae_launches_registers_git_push_and_social_stop_hooks(monkeypatch):
    daemon = MagicMock()
    daemon.running = True
    broker = MagicMock()
    broker.list_launchable_daes.return_value = {"git_push_dae": {}, "social_media": {}}
    broker.get_runtime_status.return_value = {"running": True}

    monkeypatch.setenv("OPENCLAW_RESIDENT_ENABLED", "0")
    monkeypatch.setenv("OPENCLAW_SUPERVISOR_ENABLED", "0")

    with patch.object(main, "get_central_daemon", return_value=daemon), patch.object(
        main, "get_dae_launch_broker", return_value=broker
    ):
        main.bootstrap_runtime_dae_launches()

    specs = [call.args[0] for call in broker.register_launch_spec.call_args_list]
    git_specs = [spec for spec in specs if spec.dae_id == "git_push_dae"]
    social_specs = [spec for spec in specs if spec.dae_id == "social_media"]
    assert len(git_specs) == 1
    assert len(social_specs) == 1
    assert git_specs[0].stop_callable is not None
    assert social_specs[0].stop_callable is not None
    assert git_specs[0].stop_callable.__name__ == "stop_git_push_dae"
    assert social_specs[0].stop_callable.__name__ == "stop_social_media_dae"


def test_bootstrap_runtime_dae_launches_registers_and_autostarts_openclaw_supervisor(monkeypatch):
    daemon = MagicMock()
    daemon.running = True
    broker = MagicMock()
    broker.list_launchable_daes.return_value = {
        "openclaw": {},
        "openclaw_supervisor": {},
    }

    def runtime_status(dae_id):
        if dae_id == "openclaw":
            return {"running": True}
        if dae_id == "openclaw_supervisor":
            return {"running": False}
        return {"running": False}

    broker.get_runtime_status.side_effect = runtime_status

    monkeypatch.setenv("OPENCLAW_RESIDENT_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_RESIDENT_AUTOSTART", "1")
    monkeypatch.setenv("OPENCLAW_SUPERVISOR_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_SUPERVISOR_AUTOSTART", "1")

    with patch.object(main, "get_central_daemon", return_value=daemon), patch.object(
        main, "get_dae_launch_broker", return_value=broker
    ):
        main.bootstrap_runtime_dae_launches()

    specs = [call.args[0] for call in broker.register_launch_spec.call_args_list]
    supervisor_specs = [spec for spec in specs if spec.dae_id == "openclaw_supervisor"]
    assert len(supervisor_specs) == 1
    assert supervisor_specs[0].stop_callable is main.stop_openclaw_supervisor_service
    broker.start_dae.assert_called_once_with("openclaw_supervisor", actor_id="0102")
