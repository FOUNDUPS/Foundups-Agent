"""
LinkedInActions connection policy tests.

Validates pre-click role gating for live Connect actions.
"""

import asyncio
import os
import sys
import unittest
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from modules.infrastructure.browser_actions.src.linkedin_actions import LinkedInActions  # noqa: E402


@dataclass
class _FakeRoutingResult:
    success: bool
    driver_used: str = "vision"
    action: str = ""
    duration_ms: int = 1
    fallback_used: bool = False
    error: Optional[str] = None
    result_data: Dict[str, Any] = field(default_factory=dict)


class _FakeRouter:
    def __init__(
        self,
        profile_extract: Optional[Dict[str, Any]] = None,
        profile_extract_success: bool = True,
        connect_success: bool = True,
        add_note_success: bool = True,
        send_success: bool = True,
        type_success: bool = True,
    ) -> None:
        self.profile_extract = profile_extract or {}
        self.profile_extract_success = profile_extract_success
        self.connect_success = connect_success
        self.add_note_success = add_note_success
        self.send_success = send_success
        self.type_success = type_success
        self.calls: List[Dict[str, Any]] = []

    async def execute(self, action: str, payload: Dict[str, Any], driver: Any = None):
        self.calls.append({"action": action, "payload": payload, "driver": driver})

        if action == "navigate":
            return _FakeRoutingResult(success=True, action=action, result_data={})

        if action == "find_by_description":
            return _FakeRoutingResult(
                success=self.profile_extract_success,
                action=action,
                result_data=self.profile_extract if self.profile_extract_success else {},
                error=None if self.profile_extract_success else "extract_failed",
            )

        if action == "click_by_description":
            desc = str(payload.get("description", "")).lower()
            if "connect button" in desc:
                return _FakeRoutingResult(success=self.connect_success, action=action)
            if "add a note" in desc:
                return _FakeRoutingResult(success=self.add_note_success, action=action)
            if "invitation note text input field" in desc:
                return _FakeRoutingResult(success=self.type_success, action=action)
            if "send invitation button" in desc:
                return _FakeRoutingResult(success=self.send_success, action=action)
            return _FakeRoutingResult(success=True, action=action)

        return _FakeRoutingResult(success=True, action=action)

    def close(self) -> None:
        return None


class TestLinkedInActionsConnectionPolicy(unittest.TestCase):
    def _run(self, coro):
        return asyncio.run(coro)

    def test_blocks_disallowed_role_before_connect_click(self):
        router = _FakeRouter(
            profile_extract={
                "name": "Jane Doe",
                "headline": "Business Development Director",
                "company": "Acme",
                "industry": "Technology",
            }
        )
        actions = LinkedInActions(router=router)

        result = self._run(
            actions.send_connection_request(
                "https://www.linkedin.com/in/jane-doe/"
            )
        )
        self.assertFalse(result.success)
        self.assertIn("policy_blocked", result.error or "")
        connect_clicks = [
            c
            for c in router.calls
            if c["action"] == "click_by_description"
            and "connect button" in str(c["payload"].get("description", "")).lower()
        ]
        self.assertEqual(len(connect_clicks), 0)

    def test_allows_founder_and_clicks_connect(self):
        router = _FakeRouter()
        actions = LinkedInActions(router=router)

        result = self._run(
            actions.send_connection_request(
                "https://www.linkedin.com/in/gary-phillips/",
                profile_name="Gary Phillips",
                headline="Founder | Architect | Blockchain",
                company="ELOSIA",
                industry="Blockchain",
            )
        )
        self.assertTrue(result.success)
        self.assertEqual(actions.get_session_stats()["connections_sent"], 1)
        connect_clicks = [
            c
            for c in router.calls
            if c["action"] == "click_by_description"
            and "connect button" in str(c["payload"].get("description", "")).lower()
        ]
        self.assertGreaterEqual(len(connect_clicks), 1)

    def test_dry_run_allows_without_clicking_connect(self):
        router = _FakeRouter()
        actions = LinkedInActions(router=router)

        result = self._run(
            actions.send_connection_request(
                "https://www.linkedin.com/in/gary-phillips/",
                profile_name="Gary Phillips",
                headline="Chief Technology Officer",
                dry_run=True,
            )
        )
        self.assertTrue(result.success)
        self.assertTrue(result.details.get("dry_run"))
        connect_clicks = [
            c
            for c in router.calls
            if c["action"] == "click_by_description"
            and "connect button" in str(c["payload"].get("description", "")).lower()
        ]
        self.assertEqual(len(connect_clicks), 0)

    def test_blocks_when_metadata_missing(self):
        router = _FakeRouter(profile_extract_success=False)
        actions = LinkedInActions(router=router)

        result = self._run(
            actions.send_connection_request(
                "https://www.linkedin.com/in/unknown-profile/"
            )
        )
        self.assertFalse(result.success)
        self.assertIn("missing_profile_metadata", result.error or "")


if __name__ == "__main__":
    unittest.main(verbosity=2)


# Policy-only dry-run acceptance plus explicit live compatibility controls.
# The reviewed runner supplies inert import boundaries; the four legacy tests
# above remain unchanged and are excluded because they call the real constructor.
from copy import deepcopy
from datetime import datetime as _Datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


_CONNECTION_URL = "https://www.linkedin.com/in/synthetic-person/"
_CONNECTION_META = {
    "name": "Synthetic Principal", "headline": "Founder",
    "company": "Example", "industry": "Technology",
}


class _ConnectionClock(_Datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 22, 12, tzinfo=tz)


def _connection_trace(events, label, callback):
    def traced(*args, **kwargs):
        events.append(label)
        return callback(*args, **kwargs)
    return traced


@pytest.fixture
def connection_current(monkeypatch):
    import time
    from modules.platform_integration.linkedin_agent.src.engagement import connection_manager as policy

    owner = sys.modules[LinkedInActions.__module__]
    monkeypatch.setattr(owner, "datetime", _ConnectionClock)
    monkeypatch.setattr(policy, "datetime", _ConnectionClock)
    constructor = Mock(side_effect=AssertionError("real browser constructor forbidden"))
    monkeypatch.setattr(LinkedInActions, "__init__", constructor)
    manager = policy.LinkedInConnectionManager()
    events, simulations = [], []
    router = _FakeRouter()
    execute = router.execute

    async def route(action, payload, driver=None):
        events.append("router:" + action)
        return await execute(action, payload, driver)

    def sleep(seconds):
        events.append("simulation")
        simulations.append((seconds, len(manager.connection_history), tuple(manager.pending_requests)))

    monkeypatch.setattr(router, "execute", route)
    monkeypatch.setattr(time, "sleep", sleep)
    for name, label in (("evaluate_connection_policy", "policy"), ("send_connection_request", "manager")):
        monkeypatch.setattr(manager, name, _connection_trace(events, label, getattr(manager, name)))
    actions = LinkedInActions.__new__(LinkedInActions)
    actions.router = router
    actions._connection_manager = manager
    actions._connection_profile_cls = policy.LinkedInProfile
    actions._connection_status_cls = policy.ConnectionStatus
    actions._session_stats = {"connections_sent": 0}
    yield SimpleNamespace(actions=actions, manager=manager, policy=policy, router=router,
                          events=events, simulations=simulations)
    constructor.assert_not_called()


def _connection_request(state, **overrides):
    params = {"profile_name": _CONNECTION_META["name"], "dry_run": True,
              **{key: value for key, value in _CONNECTION_META.items() if key != "name"}}
    params.update(overrides)
    return asyncio.run(state.actions.send_connection_request(_CONNECTION_URL, **params))


def _connection_result(success=True, error=None, details=None):
    return {"success": success, "action": "send_connection_request", "post_id": "synthetic-person",
            "posts_read": 0, "engagements": 0, "error": error, "duration_ms": 0,
            "details": details or {}}


def _connection_preview(allowed, profile):
    return {"dry_run": True,
            "policy_reason": "allow role category matched" if allowed else "hard-deny role category matched",
            "matched_allow": ["founder"] if allowed else [],
            "matched_deny": [] if allowed else ["marketing"], "profile": profile}


def _connection_state(state):
    return deepcopy((state.manager.pending_requests, state.manager.connection_history,
                     state.manager.connections, state.actions._session_stats))


def _connection_preview_guard(state, monkeypatch):
    send = Mock(side_effect=AssertionError("preview must not create a request"))
    simulate = Mock(side_effect=AssertionError("preview must not simulate a request"))
    monkeypatch.setattr(state.manager, "send_connection_request", send)
    monkeypatch.setattr(state.manager, "_simulate_connection_request", simulate)
    return _connection_state(state), send, simulate


def _connection_preview_unchanged(state, guarded):
    before, send, simulate = guarded
    assert _connection_state(state) == before
    send.assert_not_called()
    simulate.assert_not_called()
    assert not state.simulations
    assert not any(call["action"] == "click_by_description" for call in state.router.calls)


def _connection_seed(state, kind):
    state.actions._session_stats["connections_sent"] = 7
    if kind == "pending":
        prior = state.policy.ConnectionRequest("synthetic-prior", "current_user", "synthetic-person")
        state.manager.pending_requests["synthetic-person"] = prior
        state.manager.connection_history.append(prior)
    elif kind == "connected":
        profile = state.policy.LinkedInProfile("synthetic-person", "Synthetic", "Principal", "Founder")
        prior = state.policy.Connection("synthetic-connection", "current_user", profile, _ConnectionClock.now())
        state.manager.connections["synthetic-person"] = prior
    elif kind == "quota":
        state.manager.max_daily_requests = 1
        state.manager.connection_history.append(state.policy.ConnectionRequest(
            "synthetic-prior", "current_user", "other", status=state.policy.ConnectionStatus.BLOCKED))


def _connection_pending(state):
    assert len(state.manager.connection_history) == 1
    request = state.manager.connection_history[0]
    assert state.manager.pending_requests == {"synthetic-person": request}
    assert request.status is state.policy.ConnectionStatus.PENDING
    assert request.from_profile_id == "current_user" and request.to_profile_id == "synthetic-person"
    assert request.timestamp == _ConnectionClock.now()
    assert state.simulations == [(1, 1, ("synthetic-person",))]


@pytest.mark.parametrize("allowed", [True, False])
@pytest.mark.parametrize("extract", [False, True])
def test_connection_preview_uses_policy_without_request(connection_current, monkeypatch, allowed, extract):
    state = connection_current
    profile = {**_CONNECTION_META, "headline": "Founder" if allowed else "Founder and Marketing Advisor"}
    state.router.profile_extract = dict(profile)
    overrides = dict(profile_name=None, headline=None, company=None, industry=None) if extract else {
        "headline": profile["headline"]}
    guarded = _connection_preview_guard(state, monkeypatch)
    result = _connection_request(state, **overrides)
    error = None if allowed else "policy_blocked: hard-deny role category matched"
    assert result.to_dict() == _connection_result(allowed, error, _connection_preview(allowed, profile))
    expected = ["router:navigate"] + (["router:find_by_description"] if extract else [])
    assert state.events == expected + ["policy"]
    assert state.router.calls[0]["payload"] == {"url": _CONNECTION_URL}
    _connection_preview_unchanged(state, guarded)


@pytest.mark.parametrize("allowed", [True, False])
@pytest.mark.parametrize("kind", ["empty", "pending", "connected", "quota"])
def test_connection_preview_repeated_with_seeded_state(connection_current, monkeypatch, allowed, kind):
    state = connection_current
    _connection_seed(state, kind)
    guarded = _connection_preview_guard(state, monkeypatch)
    profile = {**_CONNECTION_META, "headline": "Founder" if allowed else "Founder and Marketing Advisor"}
    error = None if allowed else "policy_blocked: hard-deny role category matched"
    for _ in range(2):
        result = _connection_request(state, headline=profile["headline"])
        assert result.to_dict() == _connection_result(allowed, error, _connection_preview(allowed, profile))
        _connection_preview_unchanged(state, guarded)
    assert state.events == ["router:navigate", "policy"] * 2


def test_connection_live_denial_preserves_bookkeeping(connection_current):
    state = connection_current
    headline = "Founder and Marketing Advisor"
    result = _connection_request(state, headline=headline, dry_run=False)
    details = {"policy_reason": "hard-deny role category matched", "matched_allow": [],
               "matched_deny": ["marketing"], "request_status": "blocked",
               "profile": {**_CONNECTION_META, "headline": headline}}
    assert result.to_dict() == _connection_result(False, "policy_blocked: hard-deny role category matched", details)
    assert state.events == ["router:navigate", "policy", "manager", "policy"]
    assert [r.status for r in state.manager.connection_history] == [state.policy.ConnectionStatus.BLOCKED]
    assert not state.manager.pending_requests and not state.simulations
    assert [call["action"] for call in state.router.calls] == ["navigate"]
    assert state.actions._session_stats == {"connections_sent": 0}


def test_connection_current_missing_metadata_skips_manager(connection_current):
    state = connection_current
    state.router.profile_extract_success = False
    result = _connection_request(state, profile_name=None, headline=None, company=None, industry=None)
    details = {"profile": {key: "" for key in _CONNECTION_META}}
    assert result.to_dict() == _connection_result(False, "policy_blocked: missing_profile_metadata", details)
    assert state.events == ["router:navigate", "router:find_by_description"]
    assert not state.manager.pending_requests and not state.manager.connection_history
    assert not state.simulations and state.actions._session_stats == {"connections_sent": 0}


@pytest.mark.parametrize("connect_success", [True, False])
def test_connection_current_fake_live_clicks_follow_bookkeeping(connection_current, connect_success):
    state = connection_current
    state.router.connect_success = connect_success
    result = _connection_request(state, dry_run=False)
    details = {"policy_reason": "allow role category matched", "request_status": "pending"}
    if connect_success:
        details.update(matched_allow=["founder"], profile=_CONNECTION_META,
                       connect_click_success=True, send_click_success=True,
                       add_note_success=None, note_typed_success=None)
    error = None if connect_success else "connect_click_failed: None"
    assert result.to_dict() == _connection_result(connect_success, error, details)
    expected_clicks = ["Connect button on LinkedIn profile"]
    if connect_success:
        expected_clicks.append("Send invitation button in Connect dialog")
    assert [call["payload"]["description"] for call in state.router.calls[1:]] == expected_clicks
    assert state.events == ["router:navigate", "policy", "manager", "policy", "simulation"] + [
        "router:click_by_description" for _ in expected_clicks]
    _connection_pending(state)
    assert state.actions._session_stats == {"connections_sent": int(connect_success)}


def test_connection_current_unavailable_manager_has_no_routes(connection_current):
    state = connection_current
    state.actions._connection_manager = None
    result = _connection_request(state)
    assert result.to_dict() == _connection_result(False, "connection_policy_manager_unavailable")
    assert not state.events and not state.router.calls and not state.simulations
    assert not state.manager.connection_history and not state.manager.pending_requests


# Requested-note ordering acceptance; local acknowledgment is not delivery proof.
# Spare scripted replies keep baseline failures about behavior, not mock exhaustion.
_ACK_NOTE = "Synthetic invitation note."
_ACK_DIRECT_STEPS = ("connect", "send")
_ACK_ADD_FAILED_STEPS = ("connect", "add")
_ACK_TYPE_FAILED_STEPS = ("connect", "add", "type")
_ACK_NOTE_STEPS = ("connect", "add", "type", "send")


def _connection_ack_send_script(state, monkeypatch, outcomes):
    send = Mock(side_effect=outcomes)
    execute = state.router.execute

    async def route(action, payload, driver=None):
        result = await execute(action, payload, driver)
        if action == "click_by_description" and payload.get("description") == (
            "Send invitation button in Connect dialog"
        ):
            result.success = send()
        return result

    monkeypatch.setattr(state.router, "execute", route)
    return send


def _connection_ack_calls(steps, message):
    payloads = {
        "connect": {"description": "Connect button on LinkedIn profile"},
        "send": {"description": "Send invitation button in Connect dialog"},
        "add": {"description": "Add a note button in Connect dialog"},
        "type": {"description": "Invitation note text input field", "text": message, "slow_type": True},
    }
    return [{"action": "navigate", "payload": {"url": _CONNECTION_URL}, "driver": "selenium"}] + [
        {"action": "click_by_description", "payload": payloads[step], "driver": "vision"}
        for step in steps
    ]


@pytest.mark.parametrize(
    "message,sends,add_note,typed,send_success,send_calls,success,steps",
    [
        pytest.param(None, (False,), None, None, False, 1, True, _ACK_DIRECT_STEPS,
                     id="no_note_missing_send"),
        pytest.param("", (False,), None, None, False, 1, True, _ACK_DIRECT_STEPS,
                     id="empty_note_missing_send"),
        pytest.param(_ACK_NOTE, (True,), False, None, None, 0, False, _ACK_ADD_FAILED_STEPS,
                     id="add_failure_prevents_send"),
        pytest.param(_ACK_NOTE, (True, True), True, False, None, 0, False, _ACK_TYPE_FAILED_STEPS,
                     id="type_failure_prevents_send"),
        pytest.param(_ACK_NOTE, (True, True), True, True, True, 1, True, _ACK_NOTE_STEPS,
                     id="note_single_send_succeeds"),
        pytest.param(_ACK_NOTE, (False, False), True, True, False, 1, False, _ACK_NOTE_STEPS,
                     id="note_single_send_fails"),
    ],
)
def test_connection_ack_note_sequence(
    connection_current, monkeypatch, message, sends, add_note, typed, send_success, send_calls, success, steps,
):
    state = connection_current
    _connection_seed(state, "empty")
    state.router.add_note_success = add_note
    state.router.type_success = typed
    send = _connection_ack_send_script(state, monkeypatch, sends)
    result = _connection_request(state, message=message, dry_run=False)
    details = {
        "policy_reason": "allow role category matched", "matched_allow": ["founder"],
        "request_status": "pending", "profile": _CONNECTION_META,
        "connect_click_success": True, "send_click_success": send_success,
        "add_note_success": add_note, "note_typed_success": typed,
    }
    error = None if success else "send_invitation_failed"
    assert result.to_dict() == _connection_result(success, error, details)
    assert state.router.calls == _connection_ack_calls(steps, message)
    assert state.events == ["router:navigate", "policy", "manager", "policy", "simulation"] + [
        "router:click_by_description" for _ in steps]
    assert send.call_args_list == [unittest.mock.call() for _ in range(send_calls)]
    _connection_pending(state)
    request = state.manager.connection_history[0]
    generated = "Hi John, I noticed your work at Tech Company and would love to connect!"
    assert request.message == (message or generated)
    assert request.response_timestamp is None and not state.manager.connections
    assert state.actions._session_stats == {"connections_sent": 7 + int(success)}


# Current-behavior qualification, not the prospective admission acceptance gate.
def _connection_admission_capture(state, monkeypatch, kind):
    _connection_seed(state, kind if kind in {"quota", "connected", "pending"} else "empty")
    if kind == "simulation_failure":
        simulate = state.manager._simulate_connection_request

        def failed_simulation(request):
            simulate(request)
            raise RuntimeError("synthetic simulation failure")

        monkeypatch.setattr(state.manager, "_simulate_connection_request", failed_simulation)
    returned = []
    send = state.manager.send_connection_request

    def capture(*args, **kwargs):
        request = send(*args, **kwargs)
        returned.append(request)
        return request

    monkeypatch.setattr(state.manager, "send_connection_request", capture)
    return returned


def _connection_admission_bookkeeping(state, kind, before, prior, request):
    assert state.manager.connections == before[2]
    if kind in {"quota", "connected", "pending"}:
        assert _connection_state(state)[:3] == before[:3]
        if kind == "pending":
            assert request is prior is state.manager.pending_requests["synthetic-person"]
            assert state.manager.connection_history[0] is prior
        else:
            assert not state.manager.pending_requests
            assert all(item is not request for item in state.manager.connection_history)
    else:
        assert len(state.manager.connection_history) == 1
        stored = state.manager.connection_history[0]
        if kind == "blocked":
            assert stored is request and not state.manager.pending_requests
        else:
            assert state.manager.pending_requests == {"synthetic-person": stored}
            assert state.manager.pending_requests["synthetic-person"] is stored
            assert stored.status is state.policy.ConnectionStatus.PENDING
            assert stored.request_id == request.request_id
            assert (stored is request) is (kind == "fresh")
            assert stored.message == _ACK_NOTE and stored.response_timestamp is None


@pytest.mark.parametrize("kind,status", [
    ("fresh", "pending"), ("quota", "withdrawn"), ("connected", "connected"),
    ("pending", "pending"), ("simulation_failure", "withdrawn"), ("blocked", "blocked"),
])
def test_connection_admission_current_manager_outcome(connection_current, monkeypatch, kind, status):
    state = connection_current
    returned = _connection_admission_capture(state, monkeypatch, kind)
    before = _connection_state(state)
    prior = state.manager.pending_requests.get("synthetic-person")
    headline = "Founder and Marketing Advisor" if kind == "blocked" else "Founder"
    result = _connection_request(state, headline=headline, message=_ACK_NOTE, dry_run=False)
    assert len(returned) == 1
    request = returned[0]
    assert request.status is state.policy.ConnectionStatus(status)
    assert (request.from_profile_id, request.to_profile_id) == ("current_user", "synthetic-person")
    expected_id = "synthetic-prior" if kind == "pending" else f"req_synthetic-person_{_ConnectionClock.now().timestamp()}"
    assert request.request_id == expected_id and request.timestamp == _ConnectionClock.now()
    assert request.response_timestamp is None
    assert request.message == (None if kind == "pending" else _ACK_NOTE)
    success = kind != "blocked"
    details = {"policy_reason": "allow role category matched" if success else "hard-deny role category matched",
               "matched_allow": ["founder"] if success else [], "request_status": status,
               "profile": {**_CONNECTION_META, "headline": headline}}
    if success:
        details.update(connect_click_success=True, send_click_success=True,
                       add_note_success=True, note_typed_success=True)
    else:
        details.update(matched_deny=["marketing"])
    error = None if success else "policy_blocked: hard-deny role category matched"
    assert result.to_dict() == _connection_result(success, error, details)
    steps = _ACK_NOTE_STEPS if success else ()
    assert state.router.calls == _connection_ack_calls(steps, _ACK_NOTE)
    events = ["router:navigate", "policy", "manager"]
    if kind in {"fresh", "simulation_failure", "blocked"}:
        events.append("policy")
    simulated = kind in {"fresh", "simulation_failure"}
    assert state.simulations == ([(1, 1, ("synthetic-person",))] if simulated else [])
    assert state.events == events + (["simulation"] if simulated else []) + [
        "router:click_by_description" for _ in steps]
    assert state.actions._session_stats == {"connections_sent": 7 + int(success)}
    _connection_admission_bookkeeping(state, kind, before, prior, request)
