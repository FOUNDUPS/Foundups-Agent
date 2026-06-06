import importlib.util
import os
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


# ---------------------------------------------------------------------------
# Headless bootstrap seam (WRE_OPENCLAW_HERMES_AUTONOMOUS_BUILD_DRYRUN_PHASE1)
#
# These prove the BOUNDED ONE-CYCLE dry-run autonomous build/test seam only.
# Every heavy runtime (WRE readiness, bootstrap, broker, supervisor, sleep) is
# MOCKED: no live process, network, model, Hermes delegate_task, Docker, OAuth,
# or GitHub write occurs. This is NOT a claim of continuous autonomous coding.
# ---------------------------------------------------------------------------

_SUPERVISOR_CLS = (
    "modules.communication.moltbot_bridge.src.openclaw_supervisor.OpenClawSupervisor"
)
_OBSERVER_CLS = "modules.infrastructure.dae_daemon.src.dae_observer.DAEObserver"
_READY_WRE = {"readiness": "READY", "alert_counts": {"critical": 0}}


def test_run_headless_bootstraps_dae_specs_before_supervisor_cycle(monkeypatch):
    """--headless one-cycle path reuses bootstrap_runtime_dae_launches to register
    DAE launch specs BEFORE the supervisor cycle, and hands the supervisor the
    shared (bootstrap-populated) broker rather than a fresh empty one. Mocked."""
    monkeypatch.setenv("OPENCLAW_HEADLESS_MAX_CYCLES", "1")
    monkeypatch.setenv("OPENCLAW_HEADLESS_INTERVAL", "0")

    order = []
    bootstrap_mock = MagicMock(side_effect=lambda: order.append("bootstrap"))
    shared_broker = MagicMock(name="shared_broker")

    supervisor_instance = MagicMock(name="supervisor")

    def _run_cycle():
        order.append("run_cycle")
        return {"plan": {"action": "idle"}, "verify": {"ok": True}}

    supervisor_instance.run_cycle.side_effect = _run_cycle
    supervisor_cls = MagicMock(return_value=supervisor_instance)

    with patch.object(main, "run_connect_wre", return_value=_READY_WRE), patch.object(
        main, "bootstrap_runtime_dae_launches", bootstrap_mock
    ), patch.object(
        main, "get_dae_launch_broker", MagicMock(return_value=shared_broker)
    ), patch.object(main.time, "sleep", MagicMock()), patch(
        _SUPERVISOR_CLS, supervisor_cls
    ), patch(
        _OBSERVER_CLS, MagicMock()
    ):
        rc = main.run_headless()

    assert rc == 0
    bootstrap_mock.assert_called_once()
    # Spec registration happens BEFORE the supervisor cycle:
    assert order == ["bootstrap", "run_cycle"]
    # Supervisor receives the shared, bootstrap-populated broker:
    assert supervisor_cls.call_args.kwargs["broker"] is shared_broker
    supervisor_instance.run_cycle.assert_called_once()


def test_run_headless_fail_closed_when_wre_not_ready():
    """Headless exits 1 (fail-closed) and never bootstraps or constructs the
    supervisor when WRE readiness is not acceptable."""
    supervisor_cls = MagicMock()
    bootstrap_mock = MagicMock()

    with patch.object(
        main,
        "run_connect_wre",
        return_value={"readiness": "DEGRADED", "alert_counts": {"critical": 3}},
    ), patch.object(
        main, "bootstrap_runtime_dae_launches", bootstrap_mock
    ), patch(
        _SUPERVISOR_CLS, supervisor_cls
    ):
        rc = main.run_headless()

    assert rc == 1
    bootstrap_mock.assert_not_called()
    supervisor_cls.assert_not_called()


def test_run_headless_one_cycle_no_live_execution(monkeypatch):
    """One mocked cycle performs no live Hermes delegation, Docker, OAuth, network,
    or GitHub write. The fix defaults resident/supervisor DAE autostart OFF so the
    headless path would not spawn live services even with a real bootstrap."""
    monkeypatch.setenv("OPENCLAW_HEADLESS_MAX_CYCLES", "1")
    monkeypatch.setenv("OPENCLAW_HEADLESS_INTERVAL", "0")
    monkeypatch.delenv("OPENCLAW_RESIDENT_AUTOSTART", raising=False)
    monkeypatch.delenv("OPENCLAW_SUPERVISOR_AUTOSTART", raising=False)
    monkeypatch.delenv("OPENCLAW_SUPERVISOR_ALLOW_RESTART", raising=False)

    supervisor_instance = MagicMock(name="supervisor")
    supervisor_instance.run_cycle.return_value = {
        "plan": {"action": "idle"},
        "verify": {"ok": True},
    }

    with patch.object(main, "run_connect_wre", return_value=_READY_WRE), patch.object(
        main, "bootstrap_runtime_dae_launches", MagicMock()
    ), patch.object(main, "get_dae_launch_broker", MagicMock()), patch.object(
        main.time, "sleep", MagicMock()
    ), patch(
        _SUPERVISOR_CLS, MagicMock(return_value=supervisor_instance)
    ), patch(
        _OBSERVER_CLS, MagicMock()
    ):
        rc = main.run_headless()

    assert rc == 0
    # The fix sets dry-run-safe defaults: headless owns the single supervisor loop,
    # does not autostart live resident/supervisor services, and disables the
    # supervisor's service-restart path so no live webhook service is launched.
    assert os.environ.get("OPENCLAW_RESIDENT_AUTOSTART") == "0"
    assert os.environ.get("OPENCLAW_SUPERVISOR_AUTOSTART") == "0"
    assert os.environ.get("OPENCLAW_SUPERVISOR_ALLOW_RESTART") == "0"
    supervisor_instance.run_cycle.assert_called_once()


def test_supervisor_triage_escalates_not_live_starts_when_restart_disabled(monkeypatch):
    """Guard for the headless dry-run posture: with restart disabled (the default
    run_headless sets), the supervisor triage ESCALATES instead of emitting the
    live 'start_openclaw' action, so no real DAE service is launched. Mocked
    broker/observer; no live process."""
    monkeypatch.setenv("OPENCLAW_SUPERVISOR_ALLOW_RESTART", "0")
    from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
        OpenClawSupervisor,
    )

    sup = OpenClawSupervisor(
        repo_root=Path(__file__).resolve().parents[1],
        broker=MagicMock(),
        observer=MagicMock(),
    )
    # Resident is registered (fix applied) but not running -> with restart disabled
    # the only live-launch branch must NOT be taken.
    result = sup._triage({"openclaw_runtime": {"registered": True, "running": False}})

    assert result["kind"] == "escalate"
    assert result["reason"] == "resident_openclaw_down_restart_disabled"
    assert result.get("action") != "start_openclaw"
