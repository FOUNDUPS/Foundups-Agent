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


# Current-behavior qualification, not a future no-mutation acceptance contract.
# The reviewed runner supplies inert import boundaries; the four legacy tests
# above remain unchanged and are excluded because they call the real constructor.
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


def _connection_preview(status="pending"):
    return {"dry_run": True, "policy_reason": "allow role category matched",
            "matched_allow": ["founder"], "request_status": status, "profile": _CONNECTION_META}


def _connection_pending(state):
    assert len(state.manager.connection_history) == 1
    request = state.manager.connection_history[0]
    assert state.manager.pending_requests == {"synthetic-person": request}
    assert request.status is state.policy.ConnectionStatus.PENDING
    assert request.from_profile_id == "current_user" and request.to_profile_id == "synthetic-person"
    assert request.timestamp == _ConnectionClock.now()
    assert state.simulations == [(1, 1, ("synthetic-person",))]


@pytest.mark.parametrize("extract", [False, True])
def test_connection_current_allowed_dry_mutates_before_preview(connection_current, extract):
    state = connection_current
    state.router.profile_extract = dict(_CONNECTION_META)
    overrides = dict(profile_name=None, headline=None, company=None, industry=None) if extract else {}
    result = _connection_request(state, **overrides)
    assert result.to_dict() == _connection_result(details=_connection_preview())
    expected = ["router:navigate"] + (["router:find_by_description"] if extract else [])
    assert state.events == expected + ["policy", "manager", "policy", "simulation"]
    _connection_pending(state)
    assert state.router.calls[0]["payload"] == {"url": _CONNECTION_URL}
    assert not any(call["action"] == "click_by_description" for call in state.router.calls)
    assert state.actions._session_stats == {"connections_sent": 0}


def test_connection_current_blocked_dry_records_history(connection_current):
    state = connection_current
    headline = "Founder and Marketing Advisor"
    result = _connection_request(state, headline=headline)
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


def test_connection_current_pending_retry_reuses_request(connection_current):
    state = connection_current
    _connection_request(state)
    original = state.manager.pending_requests["synthetic-person"]
    state.events.clear()
    state.simulations.clear()
    state.router.calls.clear()
    result = _connection_request(state)
    assert result.to_dict() == _connection_result(details=_connection_preview())
    assert state.manager.pending_requests["synthetic-person"] is original
    assert len(state.manager.connection_history) == 1 and state.manager.connection_history[0] is original
    assert state.events == ["router:navigate", "policy", "manager"]
    assert not state.simulations and state.actions._session_stats == {"connections_sent": 0}


def test_connection_current_blocked_history_exhausts_quota(connection_current):
    state = connection_current
    state.manager.max_daily_requests = 1
    prior = state.policy.ConnectionRequest("synthetic-prior", "current_user", "other",
                                           status=state.policy.ConnectionStatus.BLOCKED)
    state.manager.connection_history.append(prior)
    result = _connection_request(state)
    assert result.to_dict() == _connection_result(details=_connection_preview("withdrawn"))
    assert state.manager.connection_history == [prior] and not state.manager.pending_requests
    assert state.events == ["router:navigate", "policy", "manager"]
    assert not state.simulations and state.actions._session_stats == {"connections_sent": 0}


def test_connection_current_connected_returns_dry_success(connection_current):
    state = connection_current
    profile = state.policy.LinkedInProfile("synthetic-person", "Synthetic", "Principal", "Founder")
    prior = state.policy.Connection("synthetic-connection", "current_user", profile, _ConnectionClock.now())
    state.manager.connections["synthetic-person"] = prior
    result = _connection_request(state)
    assert result.to_dict() == _connection_result(details=_connection_preview("connected"))
    assert state.manager.connections == {"synthetic-person": prior}
    assert not state.manager.pending_requests and not state.manager.connection_history
    assert state.events == ["router:navigate", "policy", "manager"]
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
