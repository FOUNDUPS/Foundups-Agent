"""Tests for PQN runtime broker routing through the research adapter."""

from unittest.mock import MagicMock, patch

from modules.communication.moltbot_bridge.src.pqn_research_adapter import (
    handle_pqn_research_intent,
)


class TestPQNResearchAdapterRuntimeControl:
    def test_launch_pqn_research_uses_broker(self):
        broker = MagicMock()
        broker.start_dae.return_value = {"status": "starting", "started_at": 123.0}

        with patch(
            "modules.communication.moltbot_bridge.src.pqn_research_adapter._get_launch_broker",
            return_value=broker,
        ):
            result = handle_pqn_research_intent("launch pqn research", "012")

        broker.start_dae.assert_called_once_with("pqn_research", actor_id="012")
        assert "pqn_research" in result
        assert "starting" in result

    def test_status_pqn_architect_uses_broker(self):
        broker = MagicMock()
        broker.get_runtime_status.return_value = {
            "registered": True,
            "state": "running",
            "running": True,
            "enabled": True,
            "run_count": 2,
            "last_error": "",
        }

        with patch(
            "modules.communication.moltbot_bridge.src.pqn_research_adapter._get_launch_broker",
            return_value=broker,
        ):
            result = handle_pqn_research_intent("status pqn architect", "012")

        broker.get_runtime_status.assert_called_once_with("pqn_architect")
        assert "state=running" in result
        assert "run_count=2" in result

    def test_stop_pqn_research_uses_broker(self):
        broker = MagicMock()
        broker.stop_dae.return_value = {"status": "stopped"}

        with patch(
            "modules.communication.moltbot_bridge.src.pqn_research_adapter._get_launch_broker",
            return_value=broker,
        ):
            result = handle_pqn_research_intent("stop pqn research", "012")

        broker.stop_dae.assert_called_once_with("pqn_research", actor_id="012")
        assert "stopped" in result

    def test_runtime_control_handles_missing_broker(self):
        with patch(
            "modules.communication.moltbot_bridge.src.pqn_research_adapter._get_launch_broker",
            return_value=None,
        ):
            result = handle_pqn_research_intent("launch pqn research", "012")

        assert "runtime broker is not available" in result.lower()

    def test_show_pqn_simulation_plan_returns_plan(self):
        reporter = MagicMock()
        fake_plan = {
            "run_count": 6,
            "matched_null_required": True,
            "out_root": "modules/ai_intelligence/pqn_alignment/artifact_results/theory_archive_simulation",
            "spec": {
                "target_resonance_hz": 7.05,
                "observables": ["spectral_gap_ratio", "detection_signal_eta"],
            },
        }

        with patch(
            "modules.ai_intelligence.pqn_alignment.PQNAlignmentDAE",
        ) as dae_cls:
            dae_cls.return_value.get_theory_archive_simulation_plan.return_value = fake_plan
            result = handle_pqn_research_intent(
                "show pqn simulation plan",
                "012",
                report_action=reporter,
            )

        assert "PQN Theory-Archive Simulation Plan" in result
        assert "run_count=6" in result
        reporter.assert_called_once()
        assert reporter.call_args.args[0] == "pqn_simulation_plan"

    def test_run_pqn_simulation_uses_broker_runtime(self):
        reporter = MagicMock()
        broker = MagicMock()
        broker.start_dae.return_value = {
            "status": "starting",
            "started_at": 456.0,
        }

        with patch(
            "modules.communication.moltbot_bridge.src.pqn_research_adapter._get_launch_broker",
            return_value=broker,
        ):
            result = handle_pqn_research_intent(
                "run pqn simulation",
                "012",
                report_action=reporter,
            )

        broker.start_dae.assert_called_once_with("pqn_simulation", actor_id="012")
        assert "PQN simulation launch `pqn_simulation` -> starting." in result
        reporter.assert_called_once()
        assert reporter.call_args.args[0] == "pqn_simulation_runtime"
        assert reporter.call_args.args[2] == "starting"
