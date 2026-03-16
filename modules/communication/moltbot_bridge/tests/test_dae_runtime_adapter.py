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
    assert classify_dae_runtime_category("tail openclaw") == "monitor"


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


def test_parse_tail_openclaw_request():
    request = parse_dae_runtime_request("tail openclaw")

    assert request is not None
    assert request["action"] == "tail"
    assert request["dae_id"] == "openclaw"


def test_live_status_openclaw_uses_observer():
    observer = MagicMock()
    observer.get_live_status.return_value = {
        "registered": True,
        "dae_id": "openclaw",
        "state": "running",
        "enabled": True,
        "domain": "communication",
        "pid": 123,
        "last_heartbeat_age_sec": 2.0,
        "runtime": {"running": True, "run_count": 1, "last_error": ""},
        "recent_events": [
            {
                "sequence_id": 44,
                "event_type": "action_performed",
                "payload": {
                    "action_type": "pqn_simulation",
                    "target": "pqn_theory_archive",
                    "result": "started",
                },
            }
        ],
    }

    with patch(
        "modules.communication.moltbot_bridge.src.dae_runtime_adapter._get_dae_observer",
        return_value=observer,
    ):
        result = handle_dae_runtime_intent(
            "status openclaw live",
            "012",
            allow_mutation=False,
        )

    observer.get_live_status.assert_called_once_with("openclaw", limit=8)
    assert "DAE live status `openclaw`" in result
    assert "recent_events:" in result


def test_tail_openclaw_uses_observer():
    observer = MagicMock()
    observer.tail_events.return_value = [
        {
            "sequence_id": 41,
            "event_type": "message_in",
            "payload": {"source": "012", "summary": "tail openclaw"},
        },
        {
            "sequence_id": 42,
            "event_type": "action_performed",
            "payload": {
                "action_type": "pqn_simulation",
                "target": "pqn_theory_archive",
                "result": "started",
            },
        },
    ]

    with patch(
        "modules.communication.moltbot_bridge.src.dae_runtime_adapter._get_dae_observer",
        return_value=observer,
    ):
        result = handle_dae_runtime_intent(
            "tail openclaw",
            "012",
            allow_mutation=False,
        )

    observer.tail_events.assert_called_once_with(dae_id="openclaw", limit=8)
    assert "DAE event tail `openclaw`" in result
    assert "pqn_simulation" in result
