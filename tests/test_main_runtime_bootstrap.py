import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
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
    ), patch.object(
        main,
        "run_runtime_compatibility_advisory_preflight",
        pass_step("runtime_compatibility"),
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
        "runtime_compatibility",
        "menu",
    ]


def test_runtime_compatibility_adapter_failure_never_blocks_menu(tmp_path, monkeypatch, capsys):
    from modules.infrastructure.dependency_launcher.src import runtime_compatibility_preflight

    def fail(_repo_root):
        raise RuntimeError("must_not_escape")

    monkeypatch.setattr(runtime_compatibility_preflight, "run_runtime_compatibility_advisory", fail)
    assert main.run_runtime_compatibility_advisory_preflight(tmp_path) is True
    assert "preflight=NOT_READY" in capsys.readouterr().out


def test_main_missing_resident_bindings_warns_and_still_loads_menu(monkeypatch):
    monkeypatch.setenv("OPENCLAW_SECURITY_PREFLIGHT", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_PREFLIGHT", "0")
    monkeypatch.setenv("WRE_DASHBOARD_PREFLIGHT", "0")
    monkeypatch.setenv("WSP_FRAMEWORK_PREFLIGHT", "0")
    monkeypatch.setenv("OPENCLAW_SUPERVISOR_ENABLED", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE_ENFORCED", "0")

    passing_preflights = {
        name: MagicMock(return_value=True)
        for name in (
            "run_env_hygiene_preflight",
            "run_brain_artifact_preflight",
            "run_ironclaw_runtime_preflight",
            "run_openclaw_security_preflight",
            "run_dependency_security_preflight",
            "run_wre_dashboard_preflight",
            "run_wsp_framework_preflight",
            "run_git_main_merge_sentinel_preflight",
            "run_reddog_authoritative_work_state_refresh_preflight",
            "run_reddog_architect_fix_promotion_preflight",
            "run_reddog_wre_queue_consumer_preflight",
            "run_reddog_resident_queue_orchestration_plan_preflight",
            "run_reddog_resident_queue_next_stage_dispatch_preflight",
            "run_reddog_resident_queue_control_loop_preflight",
            "run_reddog_readonly_operational_bootstrap_preflight",
            "bootstrap_runtime_dae_launches",
        )
    }

    with patch.multiple(main, **passing_preflights), patch.object(
        main,
        "_reddog_resident_model_runtime_bindings_from_env",
        return_value=(None, None, "missing_model_runtime_binding_root"),
    ), patch.object(main, "_run_reddog_main_resident_client") as resident_client, patch(
        "modules.infrastructure.cli.src.main_menu.run_main_menu"
    ) as run_main_menu:
        main.main()

    resident_client.assert_not_called()
    run_main_menu.assert_called_once()


def test_main_missing_resident_bindings_enforced_stops_before_later_stages(
    monkeypatch,
):
    monkeypatch.setenv("OPENCLAW_SECURITY_PREFLIGHT", "0")
    monkeypatch.setenv("OPENCLAW_DEP_SECURITY_PREFLIGHT", "0")
    monkeypatch.setenv("WRE_DASHBOARD_PREFLIGHT", "0")
    monkeypatch.setenv("WSP_FRAMEWORK_PREFLIGHT", "0")
    monkeypatch.setenv("OPENCLAW_SUPERVISOR_ENABLED", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE_ENFORCED", "1")

    pre_resident_preflights = {
        name: MagicMock(return_value=True)
        for name in (
            "run_env_hygiene_preflight",
            "run_brain_artifact_preflight",
            "run_ironclaw_runtime_preflight",
            "run_openclaw_security_preflight",
            "run_dependency_security_preflight",
            "run_wre_dashboard_preflight",
            "run_wsp_framework_preflight",
            "run_git_main_merge_sentinel_preflight",
            "run_reddog_authoritative_work_state_refresh_preflight",
        )
    }
    later_stage = MagicMock(return_value=True)

    with patch.multiple(main, **pre_resident_preflights), patch.object(
        main,
        "_reddog_resident_model_runtime_bindings_from_env",
        return_value=(None, None, "missing_model_runtime_binding_root"),
    ), patch.object(main, "_run_reddog_main_resident_client") as resident_client, patch.object(
        main,
        "run_reddog_architect_fix_promotion_preflight",
        later_stage,
    ), patch(
        "modules.infrastructure.cli.src.main_menu.run_main_menu"
    ) as run_main_menu:
        main.main()

    resident_client.assert_not_called()
    later_stage.assert_not_called()
    run_main_menu.assert_not_called()


def test_reddog_queue_control_loop_profile_repeats_serial_and_claim(monkeypatch):
    calls: list[str] = []

    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE",
        "signed_0102_bounded_code_fusion_worktree_draft_pr",
    )
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_MAX_ROUNDS", "3")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPT_PERSISTENCE", "0")

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


def test_reddog_queue_control_propagates_startup_verifier_config(monkeypatch):
    verifier_config = object()
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPT_PERSISTENCE", "0")

    with patch.object(
        main, "run_reddog_resident_queue_serial_loop_preflight"
    ) as serial, patch.object(
        main, "run_reddog_openclaw_signed_worker_claim_loop_preflight"
    ) as claim:

        def serial_side_effect(_repo_root):
            serial.authority_verification_config = verifier_config
            serial.last_result = {"progress_count": 0, "status": "COMPLETE"}
            return True

        def claim_side_effect(
            _repo_root, *, authority_verification_config=None
        ):
            assert authority_verification_config is verifier_config
            claim.last_result = {"progress_count": 0, "status": "IDLE"}
            return True

        serial.side_effect = serial_side_effect
        claim.side_effect = claim_side_effect
        assert main.run_reddog_resident_queue_control_loop_preflight(
            Path("O:/Foundups-Agent")
        ) is True

    assert claim.call_count == 1


def test_reddog_queue_control_receipt_reports_observed_authority_and_worker_effects(
    monkeypatch, tmp_path
):
    from modules.communication.moltbot_bridge.tests.reddog_resident_live_canary_test_support import (
        _SIGNING_CONTEXT,
    )

    repo = tmp_path / "repo"
    repo.mkdir()
    runtime_root = tmp_path / "runtime"
    receipt_path = runtime_root / "control-receipts.jsonl"
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_MAX_ROUNDS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPT_PERSISTENCE", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPTS_PATH", str(receipt_path)
    )

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_control_loop_signing_context."
        "build_control_loop_receipt_signing_context",
        return_value=_SIGNING_CONTEXT,
    ), patch.object(
        main, "run_reddog_resident_queue_serial_loop_preflight"
    ) as serial, patch.object(
        main, "run_reddog_openclaw_signed_worker_claim_loop_preflight"
    ) as claim:

        def serial_side_effect(_repo_root):
            serial.last_result = {
                "accepted": True,
                "progress_count": 2,
                "dispatched_stages": ("authority_runtime", "bounded_worker_pilot"),
                "rejection_reasons": (),
            }
            return True

        def claim_side_effect(_repo_root):
            from modules.communication.moltbot_bridge.src import openclaw_supervisor

            evidence = openclaw_supervisor._signed_worker_claim_result(
                accepted=True,
                status=openclaw_supervisor.SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT,
                task_id="task-1",
                receipt_id="signed-worker-receipt-1",
            )
            claim.last_result = {
                "accepted": True,
                "progress_count": 1,
                "completed_count": 1,
                "requeued_count": 0,
                "failed_count": 0,
                "receipt_ids": ("signed-worker-receipt-1",),
                    "worker_execution_count": 0,
                    "worker_process_spawn_count": 0,
                    "shell_command_count": 0,
                    "child_execution_evidence_digests": (
                        evidence["execution_result_digest"],
                    ),
                    "child_execution_outcomes": (
                        {
                            "task_id": "task-1",
                            "status": "completed",
                            "receipt_id": "signed-worker-receipt-1",
                            "evidence_digest": evidence[
                                "execution_result_digest"
                            ],
                            "worker_execution_performed": False,
                            "effect_evidence_complete": True,
                            "worker_process_spawn_count": 0,
                            "shell_command_count": 0,
                        },
                    ),
                    "child_execution_evidence": (evidence,),
                "rejection_reasons": (),
            }
            return True

        serial.side_effect = serial_side_effect
        claim.side_effect = claim_side_effect
        assert main.run_reddog_resident_queue_control_loop_preflight(repo) is True

    receipt = json.loads(receipt_path.read_text(encoding="utf-8").splitlines()[-1])
    assert receipt["authority_issued"] is True
    assert receipt["worker_claim_performed"] is True
    assert receipt["worker_execution_performed"] is True
    assert receipt["bounded_file_edit_observed"] is True
    assert receipt["bounded_file_edit_count"] == 1
    assert receipt["shell_command_execution_observed"] is False
    assert receipt["shell_command_count"] == 0
    assert receipt["worker_process_spawn_observed"] is False
    assert receipt["worker_process_spawn_count"] == 0


def test_reddog_queue_control_loop_stops_after_idle_round(monkeypatch):
    calls: list[str] = []

    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE",
        "signed_0102_bounded_code_fusion_worktree_draft_pr",
    )
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_MAX_ROUNDS", "5")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPT_PERSISTENCE", "0")

    with patch.object(main, "run_reddog_resident_queue_serial_loop_preflight") as serial, patch.object(
        main,
        "run_reddog_openclaw_signed_worker_claim_loop_preflight",
    ) as claim:

        def serial_side_effect(_repo_root):
            calls.append("serial")
            serial.last_result = {"progress_count": 0, "status": "COMPLETE"}
            return True

        def claim_side_effect(_repo_root):
            calls.append("claim")
            claim.last_result = {"progress_count": 0, "status": "IDLE"}
            return True

        serial.side_effect = serial_side_effect
        claim.side_effect = claim_side_effect

        assert main.run_reddog_resident_queue_control_loop_preflight(Path("O:/Foundups-Agent")) is True

    assert calls == ["serial", "claim"]


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


def test_control_receipt_persistence_failure_blocks_even_when_not_enforced(
    monkeypatch, tmp_path
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_MAX_ROUNDS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_ENFORCED", "0")
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPT_PERSISTENCE", "1"
    )
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPTS_PATH",
        str(tmp_path / "runtime" / "control.jsonl"),
    )

    with patch.object(
        main, "run_reddog_resident_queue_serial_loop_preflight"
    ) as serial, patch.object(
        main, "_reddog_persist_queue_control_receipt", side_effect=OSError("disk")
    ):
        serial.return_value = False
        serial.last_result = {
            "accepted": False,
            "progress_count": 1,
            "dispatched_stages": ("authority_runtime",),
            "rejection_reasons": ("serial_reject",),
        }
        assert main.run_reddog_resident_queue_control_loop_preflight(repo) is False

    result = main.run_reddog_resident_queue_control_loop_preflight.last_result
    assert result["status"] == "CONTROL_LOOP_RECEIPT_PERSISTENCE_REJECT"
    assert result["accepted"] is False


def test_reddog_serial_loop_profile_passes_agentdb_worker_dispatch_writer(monkeypatch):
    observed: dict[str, object] = {}

    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE",
        "signed_0102_bounded_code",
    )
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", "O:/runtime/reddog")

    def fake_bootstrap(**kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            accepted=True,
            status="REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED",
            queue_item_id="queue-1",
            selected_slice="REDDOG_TEST_SLICE_PHASE1",
            steps_run=1,
            dispatched_stages=("worker_dispatch_runtime",),
            next_action="COMPLETE",
            chain_results_path="O:/runtime/reddog/resident_queue_chain_results.json",
            store_revision="rev-1",
            rejection_reasons=(),
        )

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap.run_reddog_main_resident_queue_serial_loop_bootstrap",
        side_effect=fake_bootstrap,
    ):
        assert main.run_reddog_resident_queue_serial_loop_preflight(Path("O:/Foundups-Agent")) is True

    writer = observed.get("worker_dispatch_writer")
    assert writer is not None
    assert writer.__class__.__name__ == "AgentDbSignedWorkerDispatchTaskWriter"


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
