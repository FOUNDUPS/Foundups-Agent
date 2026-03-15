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
