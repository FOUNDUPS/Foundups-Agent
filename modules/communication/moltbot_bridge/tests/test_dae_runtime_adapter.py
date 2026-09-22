from unittest.mock import MagicMock, call, patch

import pytest

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


def test_parse_launch_pqn_simulation_runtime():
    request = parse_dae_runtime_request("run pqn simulation")

    assert request is not None
    assert request["action"] == "launch"
    assert request["dae_id"] == "pqn_simulation"


def test_parse_show_pqn_simulation_plan_stays_out_of_runtime_adapter():
    request = parse_dae_runtime_request("show pqn simulation plan")

    assert request is None


def test_parse_status_openclaw_supervisor_runtime():
    request = parse_dae_runtime_request("status openclaw supervisor live")

    assert request is not None
    assert request["action"] == "live_status"
    assert request["dae_id"] == "openclaw_supervisor"


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


def test_parse_watch_openclaw_since_request():
    request = parse_dae_runtime_request("watch openclaw since 41")

    assert request is not None
    assert request["action"] == "follow"
    assert request["dae_id"] == "openclaw"
    assert request["since_sequence"] == 41


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


def test_follow_openclaw_uses_cursor_observer():
    observer = MagicMock()
    observer.follow_events.return_value = {
        "dae_id": "openclaw",
        "since_sequence": 41,
        "next_cursor": 43,
        "events": [
            {
                "sequence_id": 42,
                "event_type": "action_performed",
                "payload": {
                    "action_type": "launch_requested",
                    "target": "openclaw",
                    "result": "ok",
                },
            }
        ],
    }

    with patch(
        "modules.communication.moltbot_bridge.src.dae_runtime_adapter._get_dae_observer",
        return_value=observer,
    ):
        result = handle_dae_runtime_intent(
            "watch openclaw since 41",
            "012",
            allow_mutation=False,
        )

    observer.follow_events.assert_called_once_with(
        dae_id="openclaw",
        since_sequence=41,
        limit=8,
    )
    assert "DAE follow `openclaw`" in result
    assert "next_cursor=43" in result


# Current-behavior qualification: eager acquisition is a recorded gap, not a
# future safety requirement. The selected runner supplies an inert src package.
_ACQUISITION_GETTERS = [call.observer(), call.broker()]
_ACQUISITION_STATUS = {
    "registered": True,
    "state": "running",
    "running": True,
    "enabled": True,
    "run_count": 3,
    "last_error": "",
}
_ACQUISITION_STATUS_TEXT = (
    "DAE runtime status `holodae`\nstate=running\nrunning=True\n"
    "enabled=True\nrun_count=3\nlast_error=none"
)
_ACQUISITION_EVENTS = [{
    "sequence_id": 7,
    "event_type": "message_in",
    "payload": {"source": "fixture", "summary": "synthetic"},
}]
_ACQUISITION_TAIL_TEXT = (
    "DAE event tail `holodae`\n- #7 message_in | from=fixture | synthetic"
)
_ACQUISITION_BROKER_UNAVAILABLE = (
    "DAE runtime broker is not available. Start the system through `python main.py` "
    "so 0102 can bootstrap runtime launches."
)


def _probe_dae_acquisition(message, *, allow=False, absent=(), method=None, payload=None):
    """Replace both getters and record only inert acquisition/callback effects."""
    trace = MagicMock()
    methods = {
        "observer": ("tail_events", "follow_events", "get_live_status"),
        "broker": ("list_launchable_daes", "get_runtime_status", "start_dae", "stop_dae"),
    }
    collaborators = {owner: MagicMock(spec=names) for owner, names in methods.items()}
    for owner, names in methods.items():
        for name in names:
            callback = getattr(collaborators[owner], name)
            callback.side_effect = AssertionError("Unexpected inert callback")
            trace.attach_mock(callback, f"{owner}_{name}")
    if method:
        owner, name = method.split(".")
        callback = getattr(collaborators[owner], name)
        callback.side_effect = None
        callback.return_value = payload
    getters = {}
    for owner, collaborator in collaborators.items():
        getters[owner] = MagicMock(return_value=None if owner in absent else collaborator)
        trace.attach_mock(getters[owner], owner)
    target = "modules.communication.moltbot_bridge.src.dae_runtime_adapter."
    with patch(target + "_get_dae_observer", getters["observer"]), patch(
        target + "_get_launch_broker", getters["broker"]
    ):
        response = handle_dae_runtime_intent(message, "fixture_actor", allow_mutation=allow)
    return response, trace.mock_calls


@pytest.mark.parametrize("message", [
    pytest.param("hello there", id="unmatched"),
    pytest.param("show pqn simulation plan", id="simulation_plan"),
])
def test_dae_acquisition_characterizes_no_request(message):
    response, trace = _probe_dae_acquisition(message)
    assert response == ""
    assert trace == []


def test_dae_acquisition_characterizes_unresolved():
    response, trace = _probe_dae_acquisition("status unknown dae")
    assert response == (
        "I could not resolve that DAE name. Use `list launchable daes` first, then "
        "launch/status/stop by the known runtime name."
    )
    assert trace == _ACQUISITION_GETTERS


@pytest.mark.parametrize("message,absent", [
    pytest.param("launch holodae", (), id="launch"),
    pytest.param("stop holodae", (), id="stop"),
    pytest.param("launch holodae", ("observer", "broker"), id="both_unavailable"),
])
def test_dae_acquisition_characterizes_denied_control(message, absent):
    response, trace = _probe_dae_acquisition(message, absent=absent)
    assert response == (
        "Runtime launch and stop commands require 012 authorization. "
        "Use `status <dae>` or `list launchable daes` for read-only inspection."
    )
    assert trace == _ACQUISITION_GETTERS


@pytest.mark.parametrize("message,method,payload,expected,callback", [
    pytest.param("list daes", "broker.list_launchable_daes", {
        "vision_dae": {"running": False, "enabled": True, "domain": "infrastructure", "dae_name": "Vision"},
        "holodae": {"running": True, "enabled": True, "domain": "ai_intelligence", "dae_name": "HoloDAE"},
    }, "Launchable DAEs:\n"
       "- holodae: running=True enabled=True domain=ai_intelligence name=HoloDAE\n"
       "- vision_dae: running=False enabled=True domain=infrastructure name=Vision",
       call.broker_list_launchable_daes(), id="list_sorted"),
    pytest.param("list daes", "broker.list_launchable_daes", {},
                 "No launchable DAEs are currently registered.",
                 call.broker_list_launchable_daes(), id="list_empty"),
    pytest.param("status holodae", "broker.get_runtime_status", _ACQUISITION_STATUS,
                 _ACQUISITION_STATUS_TEXT, call.broker_get_runtime_status("holodae"),
                 id="status_registered"),
    pytest.param("status holodae", "broker.get_runtime_status", {"registered": False},
                 "DAE runtime `holodae` is not registered.",
                 call.broker_get_runtime_status("holodae"), id="status_unregistered"),
])
def test_dae_acquisition_characterizes_broker_read(message, method, payload, expected, callback):
    response, trace = _probe_dae_acquisition(message, method=method, payload=payload)
    assert response == expected
    assert trace == _ACQUISITION_GETTERS + [callback]


@pytest.mark.parametrize("message,method,payload,expected,callback", [
    pytest.param("tail holodae", "observer.tail_events", _ACQUISITION_EVENTS,
                 _ACQUISITION_TAIL_TEXT,
                 call.observer_tail_events(dae_id="holodae", limit=8), id="tail_events"),
    pytest.param("tail holodae", "observer.tail_events", [],
                 "No recent daemon events for `holodae`.",
                 call.observer_tail_events(dae_id="holodae", limit=8), id="tail_empty"),
    pytest.param("watch holodae since 6", "observer.follow_events", {
        "dae_id": "holodae", "since_sequence": 6, "next_cursor": 8,
        "events": _ACQUISITION_EVENTS,
    }, "DAE follow `holodae`\nsince_sequence=6\nnext_cursor=8\nnew_events=1\n"
       "events:\n- #7 message_in | from=fixture | synthetic",
       call.observer_follow_events(dae_id="holodae", since_sequence=6, limit=8),
       id="follow_cursor"),
    pytest.param("status holodae live", "observer.get_live_status", {
        "dae_id": "holodae", "state": "running", "enabled": True,
        "registered": True, "next_cursor": 8,
    }, "DAE live status `holodae`\nstate=running\nenabled=True\nregistered=True\nnext_cursor=8",
       call.observer_get_live_status("holodae", limit=8), id="live_registered"),
    pytest.param("status holodae live", "observer.get_live_status", {"registered": False},
                 "DAE runtime `holodae` is not registered.",
                 call.observer_get_live_status("holodae", limit=8), id="live_unregistered"),
])
def test_dae_acquisition_characterizes_observer_read(message, method, payload, expected, callback):
    response, trace = _probe_dae_acquisition(message, method=method, payload=payload)
    assert response == expected
    assert trace == _ACQUISITION_GETTERS + [callback]


@pytest.mark.parametrize("verb,method,payload,expected,callback", [
    pytest.param(verb, "broker.start_dae", {"status": "started", "started_at": 123},
                 "DAE runtime launch `holodae` -> started.\nstarted_at=123",
                 call.broker_start_dae("holodae", actor_id="fixture_actor"), id=verb)
    for verb in ("launch", "start", "run")
] + [
    pytest.param("stop", "broker.stop_dae", {"status": "stopping"},
                 "DAE runtime stop `holodae` -> stopping.",
                 call.broker_stop_dae("holodae", actor_id="fixture_actor"), id="stop"),
])
def test_dae_acquisition_characterizes_permitted_control(verb, method, payload, expected, callback):
    response, trace = _probe_dae_acquisition(
        f"{verb} holodae", allow=True, method=method, payload=payload
    )
    assert response == expected
    assert trace == _ACQUISITION_GETTERS + [callback]


@pytest.mark.parametrize("message,absent,allow,expected", [
    pytest.param("list daes", ("broker",), False, _ACQUISITION_BROKER_UNAVAILABLE, id="list"),
    pytest.param("status holodae", ("broker",), False, _ACQUISITION_BROKER_UNAVAILABLE, id="status"),
    pytest.param("launch holodae", ("broker",), True, _ACQUISITION_BROKER_UNAVAILABLE, id="launch"),
    pytest.param("stop holodae", ("broker",), True, _ACQUISITION_BROKER_UNAVAILABLE, id="stop"),
    pytest.param("tail holodae", ("observer",), False, "DAE observer is not available yet.", id="tail"),
    pytest.param("follow holodae", ("observer",), False, "DAE observer is not available yet.", id="follow"),
    pytest.param("status holodae live", ("observer",), False, "DAE observer is not available yet.", id="live"),
])
def test_dae_acquisition_characterizes_required_unavailable(message, absent, allow, expected):
    response, trace = _probe_dae_acquisition(message, absent=absent, allow=allow)
    assert response == expected
    assert trace == _ACQUISITION_GETTERS


@pytest.mark.parametrize("message,absent,method,payload,expected,callback", [
    pytest.param("status holodae", ("observer",), "broker.get_runtime_status",
                 _ACQUISITION_STATUS, _ACQUISITION_STATUS_TEXT,
                 call.broker_get_runtime_status("holodae"), id="observer_not_required"),
    pytest.param("tail holodae", ("broker",), "observer.tail_events", _ACQUISITION_EVENTS,
                 _ACQUISITION_TAIL_TEXT, call.observer_tail_events(dae_id="holodae", limit=8),
                 id="broker_not_required"),
])
def test_dae_acquisition_characterizes_irrelevant_unavailable(
    message, absent, method, payload, expected, callback
):
    response, trace = _probe_dae_acquisition(message, absent=absent, method=method, payload=payload)
    assert response == expected
    assert trace == _ACQUISITION_GETTERS + [callback]
