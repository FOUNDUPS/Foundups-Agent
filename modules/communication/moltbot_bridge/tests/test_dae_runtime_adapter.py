from unittest.mock import MagicMock, patch

from modules.communication.moltbot_bridge.src.dae_runtime_adapter import (
    classify_dae_runtime_category,
    handle_dae_runtime_intent,
    parse_dae_runtime_request,
)


def test_parse_launch_social_media_dae():
    request = parse_dae_runtime_request("launch social media dae")

    assert request is not None
    assert request["action"] == "launch"
    assert request["dae_id"] == "social_media"


def test_classify_status_as_monitor():
    assert classify_dae_runtime_category("status holodae") == "monitor"
    assert classify_dae_runtime_category("list launchable daes") == "monitor"


def test_handle_list_launchable_daes():
    broker = MagicMock()
    broker.list_launchable_daes.return_value = {
        "holodae": {
            "running": False,
            "enabled": True,
            "domain": "ai_intelligence",
            "dae_name": "HoloDAE",
        }
    }

    with patch(
        "modules.communication.moltbot_bridge.src.dae_runtime_adapter._get_launch_broker",
        return_value=broker,
    ):
        result = handle_dae_runtime_intent(
            "list launchable daes",
            "012",
            allow_mutation=False,
        )

    assert "Launchable DAEs" in result
    assert "holodae" in result


def test_launch_requires_mutation_authority():
    broker = MagicMock()

    with patch(
        "modules.communication.moltbot_bridge.src.dae_runtime_adapter._get_launch_broker",
        return_value=broker,
    ):
        result = handle_dae_runtime_intent(
            "launch social media dae",
            "user123",
            allow_mutation=False,
        )

    broker.start_dae.assert_not_called()
    assert "require 012 authorization" in result


def test_status_holodae_uses_broker():
    broker = MagicMock()
    broker.get_runtime_status.return_value = {
        "registered": True,
        "state": "running",
        "running": True,
        "enabled": True,
        "run_count": 3,
        "last_error": "",
    }

    with patch(
        "modules.communication.moltbot_bridge.src.dae_runtime_adapter._get_launch_broker",
        return_value=broker,
    ):
        result = handle_dae_runtime_intent(
            "status holodae",
            "012",
            allow_mutation=False,
        )

    broker.get_runtime_status.assert_called_once_with("holodae")
    assert "state=running" in result
    assert "run_count=3" in result
