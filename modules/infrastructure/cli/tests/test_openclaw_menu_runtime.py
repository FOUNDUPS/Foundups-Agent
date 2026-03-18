from unittest.mock import MagicMock, patch

from modules.infrastructure.cli.src import openclaw_menu


def test_webhook_server_uses_runtime_broker_when_registered():
    broker = MagicMock()
    broker.get_runtime_status.return_value = {
        "registered": True,
        "running": False,
        "state": "stopped",
        "run_count": 0,
    }
    broker.start_dae.return_value = {"status": "starting"}

    with patch.object(openclaw_menu, "_get_openclaw_runtime_broker", return_value=broker), patch(
        "builtins.input", return_value=""
    ):
        openclaw_menu._webhook_server()

    broker.start_dae.assert_called_once_with("openclaw", actor_id="012")
