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
    assert holodae_specs[0].metadata["resident_owner"] == "dae_launch_broker"
    assert holodae_specs[0].metadata["runtime_autostart"] is False
    assert holodae_specs[0].metadata["runtime_reindex_allowed"] is False
    broker.start_dae.assert_not_called()


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


def test_main_resident_red_dog_chain_passes_profile_to_downstream_preflights(monkeypatch):
    """The resident RedDog main path must be one contiguous startup chain.

    This test proves the product-level seam: after an accepted resident FIX
    cycle, the same process must carry the safe handoff/profile values into the
    promotion, queue, serial-loop, and OpenClaw claim preflights before the
    interactive menu starts. All runtime work is mocked.
    """

    order: list[str] = []
    expected_profile = "signed_0102_bounded_code_fusion_worktree_draft_pr"

    monkeypatch.setenv("OPENCLAW_SECURITY_PREFLIGHT", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_PREFLIGHT", "0")
    monkeypatch.setenv("WRE_DASHBOARD_PREFLIGHT", "0")
    monkeypatch.setenv("WSP_FRAMEWORK_PREFLIGHT", "0")
    monkeypatch.setenv("OPENCLAW_SUPERVISOR_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ENABLED", "0")
    monkeypatch.delenv("REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF", raising=False)
    monkeypatch.delenv("REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", raising=False)

    def pass_step(name: str):
        def _step(*_args, **_kwargs):
            order.append(name)
            return True

        return _step

    def resident_cycle(*_args, **_kwargs):
        order.append("resident_cycle")
        os.environ["REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF"] = "1"
        os.environ["REDDOG_RESIDENT_QUEUE_BINDING_PROFILE"] = expected_profile
        return True

    def profile_bound_step(name: str):
        def _step(*_args, **_kwargs):
            assert os.environ["REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF"] == "1"
            assert os.environ["REDDOG_RESIDENT_QUEUE_BINDING_PROFILE"] == expected_profile
            order.append(name)
            return True

        return _step

    with patch.object(main, "run_env_hygiene_preflight", pass_step("env_hygiene")), patch.object(
        main, "run_brain_artifact_preflight", pass_step("brain")
    ), patch.object(
        main, "run_ironclaw_runtime_preflight", pass_step("ironclaw")
    ), patch.object(
        main, "run_openclaw_security_preflight", pass_step("security")
    ), patch.object(
        main, "run_dependency_security_preflight", pass_step("dep_security")
    ), patch.object(
        main, "run_wre_dashboard_preflight", pass_step("dashboard")
    ), patch.object(
        main, "run_wsp_framework_preflight", pass_step("wsp")
    ), patch.object(
        main, "run_git_main_merge_sentinel_preflight", pass_step("merge_sentinel")
    ), patch.object(
        main, "run_reddog_authoritative_work_state_refresh_preflight", pass_step("work_state")
    ), patch.object(
        main, "run_reddog_resident_architect_durable_cycle_preflight", resident_cycle
    ), patch.object(
        main, "run_reddog_architect_fix_promotion_preflight", profile_bound_step("fix_promotion")
    ), patch.object(
        main, "run_reddog_wre_queue_consumer_preflight", profile_bound_step("queue_consumer")
    ), patch.object(
        main,
        "run_reddog_resident_queue_orchestration_plan_preflight",
        profile_bound_step("queue_orchestration"),
    ), patch.object(
        main,
        "run_reddog_resident_queue_next_stage_dispatch_preflight",
        profile_bound_step("next_stage_dispatch"),
    ), patch.object(
        main,
        "run_reddog_resident_queue_control_loop_preflight",
        profile_bound_step("queue_control_loop"),
    ), patch.object(
        main, "run_reddog_readonly_operational_bootstrap_preflight", pass_step("readonly_bootstrap")
    ), patch.object(
        main, "bootstrap_runtime_dae_launches", pass_step("dae_bootstrap")
    ), patch(
        "modules.infrastructure.cli.src.main_menu.run_main_menu",
        side_effect=lambda **_kwargs: order.append("menu"),
    ):
        main.main()

    assert order == [
        "env_hygiene",
        "brain",
        "ironclaw",
        "security",
        "dep_security",
        "dashboard",
        "wsp",
        "merge_sentinel",
        "work_state",
        "resident_cycle",
        "fix_promotion",
        "queue_consumer",
        "queue_orchestration",
        "next_stage_dispatch",
        "queue_control_loop",
        "readonly_bootstrap",
        "dae_bootstrap",
        "menu",
    ]


def test_reddog_queue_control_loop_profile_repeats_serial_and_claim(monkeypatch):
    calls: list[str] = []

    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE",
        "signed_0102_bounded_code_fusion_worktree_draft_pr",
    )
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_MAX_ROUNDS", "3")

    with patch.object(
        main,
        "run_reddog_resident_queue_serial_loop_preflight",
        side_effect=lambda _repo_root: calls.append("serial") or True,
    ), patch.object(
        main,
        "run_reddog_openclaw_signed_worker_claim_loop_preflight",
        side_effect=lambda _repo_root: calls.append("claim") or True,
    ):
        assert main.run_reddog_resident_queue_control_loop_preflight(Path("O:/Foundups-Agent")) is True

    assert calls == ["serial", "claim", "serial", "claim", "serial", "claim"]


def test_reddog_queue_control_loop_without_profile_preserves_legacy_single_pass(monkeypatch):
    calls: list[str] = []

    monkeypatch.delenv("REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", raising=False)
    monkeypatch.delenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP", raising=False)

    with patch.object(
        main,
        "run_reddog_resident_queue_serial_loop_preflight",
        side_effect=lambda _repo_root: calls.append("serial") or True,
    ), patch.object(
        main,
        "run_reddog_openclaw_signed_worker_claim_loop_preflight",
        side_effect=lambda _repo_root: calls.append("claim") or True,
    ):
        assert main.run_reddog_resident_queue_control_loop_preflight(Path("O:/Foundups-Agent")) is True

    assert calls == ["serial", "claim"]


def test_reddog_queue_control_loop_invalid_rounds_fail_closed_when_enforced(monkeypatch):
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_MAX_ROUNDS", "0")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_ENFORCED", "1")

    with patch.object(main, "run_reddog_resident_queue_serial_loop_preflight") as serial, patch.object(
        main,
        "run_reddog_openclaw_signed_worker_claim_loop_preflight",
    ) as claim:
        assert main.run_reddog_resident_queue_control_loop_preflight(Path("O:/Foundups-Agent")) is False

    serial.assert_not_called()
    claim.assert_not_called()


def test_main_dependency_security_blocker_runs_reddog_diagnostic_before_return(monkeypatch):
    """A pre-RedDog startup blocker must still give RedDog a read-only diagnostic turn."""

    order: list[str] = []

    def pass_step(name: str):
        def _step(*_args, **_kwargs):
            order.append(name)
            return True

        return _step

    def fail_step(name: str):
        def _step(*_args, **_kwargs):
            order.append(name)
            return False

        return _step

    def diagnostic(*_args, **kwargs):
        order.append(f"diagnostic:{kwargs['component']}:{kwargs['stage']}")

    monkeypatch.setenv("OPENCLAW_SECURITY_PREFLIGHT", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_PREFLIGHT", "1")
    monkeypatch.setenv("WRE_DASHBOARD_PREFLIGHT", "0")
    monkeypatch.setenv("WSP_FRAMEWORK_PREFLIGHT", "0")

    with patch.object(main, "run_env_hygiene_preflight", pass_step("env_hygiene")), patch.object(
        main, "run_brain_artifact_preflight", pass_step("brain")
    ), patch.object(
        main, "run_ironclaw_runtime_preflight", pass_step("ironclaw")
    ), patch.object(
        main, "run_openclaw_security_preflight", pass_step("security")
    ), patch.object(
        main, "run_dependency_security_preflight", fail_step("dep_security")
    ), patch.object(
        main, "_handle_startup_blocker", side_effect=diagnostic
    ), patch.object(
        main, "run_wre_dashboard_preflight", pass_step("dashboard")
    ), patch.object(
        main, "bootstrap_runtime_dae_launches", pass_step("dae_bootstrap")
    ):
        main.main()

    assert order == [
        "env_hygiene",
        "brain",
        "ironclaw",
        "security",
        "dep_security",
        "diagnostic:dep_security:run_dependency_security_preflight",
    ]


def test_startup_blocker_diagnostic_is_read_only_and_restores_env(monkeypatch):
    """The startup-blocker diagnostic cannot leak auto handoff/profile into the chain."""

    observed: dict[str, str] = {}

    monkeypatch.setenv("REDDOG_RESIDENT_ARCHITECT_AUTO_FIX_HANDOFF", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_ARCHITECT_AUTO_QUEUE_PROFILE", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", "preexisting_profile")
    monkeypatch.delenv("REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF", raising=False)

    def resident_cycle(_repo_root):
        observed["durable_cycle"] = os.environ["REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE"]
        observed["work_focus"] = os.environ["REDDOG_RESIDENT_ARCHITECT_WORK_FOCUS"]
        observed["auto_fix"] = os.environ["REDDOG_RESIDENT_ARCHITECT_AUTO_FIX_HANDOFF"]
        observed["auto_profile"] = os.environ["REDDOG_RESIDENT_ARCHITECT_AUTO_QUEUE_PROFILE"]
        observed["cycle_bucket"] = os.environ["REDDOG_RESIDENT_ARCHITECT_CYCLE_BUCKET"]
        assert "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF" not in os.environ
        assert "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE" not in os.environ
        os.environ["REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF"] = "1"
        os.environ["REDDOG_RESIDENT_QUEUE_BINDING_PROFILE"] = "leaked_profile"
        return True

    with patch.object(
        main,
        "run_reddog_resident_architect_durable_cycle_preflight",
        side_effect=resident_cycle,
    ):
        main._run_reddog_startup_blocker_diagnostic(
            Path("O:/Foundups-Agent"),
            component="dep security",
            stage="run_dependency_security_preflight",
        )

    assert observed["durable_cycle"] == "1"
    assert observed["auto_fix"] == "0"
    assert observed["auto_profile"] == "0"
    assert observed["cycle_bucket"].startswith("startup_blocker:dep_security:")
    assert "Diagnose startup blocker dep_security" in observed["work_focus"]
    assert os.environ["REDDOG_RESIDENT_ARCHITECT_AUTO_FIX_HANDOFF"] == "1"
    assert os.environ["REDDOG_RESIDENT_ARCHITECT_AUTO_QUEUE_PROFILE"] == "1"
    assert os.environ["REDDOG_RESIDENT_QUEUE_BINDING_PROFILE"] == "preexisting_profile"
    assert "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF" not in os.environ


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
