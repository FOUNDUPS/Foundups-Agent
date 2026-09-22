"""
Tests for LinkedIn social adapter command parsing and routing.
"""

import unittest
from unittest.mock import AsyncMock, patch

from modules.communication.moltbot_bridge.src.linkedin_social_adapter import (
    execute_linkedin_action,
    _parse_action_command,
    _parse_natural_linkedin_command,
    handle_linkedin_social_intent,
)


class TestLinkedInSocialAdapter(unittest.IsolatedAsyncioTestCase):
    def test_parse_valid_command(self):
        parsed = _parse_action_command(
            'linkedin action read_feed max_posts=5 profile="linkedin_foundups"'
        )
        self.assertIsNotNone(parsed)
        action, params = parsed  # type: ignore[misc]
        self.assertEqual(action, "read_feed")
        self.assertEqual(params.get("max_posts"), "5")
        self.assertEqual(params.get("profile"), "linkedin_foundups")

    def test_parse_alias_command(self):
        parsed = _parse_action_command(
            "ln action send_connection_request profile_url=https://www.linkedin.com/in/jane/"
        )
        self.assertIsNotNone(parsed)
        action, params = parsed  # type: ignore[misc]
        self.assertEqual(action, "connect")
        self.assertIn("profile_url", params)

    def test_parse_group_post_command(self):
        parsed = _parse_action_command(
            'linkedin action group_post title="Research update" url=https://foundups.com/litepaper dry_run=true'
        )
        self.assertIsNotNone(parsed)
        action, params = parsed  # type: ignore[misc]
        self.assertEqual(action, "group_post")
        self.assertEqual(params.get("title"), "Research update")
        self.assertEqual(params.get("url"), "https://foundups.com/litepaper")

    def test_parse_scam_reply_command(self):
        parsed = _parse_action_command(
            'linkedin action scam_reply post_index=2 risk_reason="shortened link"'
        )
        self.assertIsNotNone(parsed)
        action, params = parsed  # type: ignore[misc]
        self.assertEqual(action, "scam_reply")
        self.assertEqual(params.get("post_index"), "2")
        self.assertEqual(params.get("risk_reason"), "shortened link")

    def test_parse_non_command(self):
        parsed = _parse_action_command("hello there")
        self.assertIsNone(parsed)

    def test_parse_natural_agentic_reply_command(self):
        parsed = _parse_natural_linkedin_command(
            "0102 go agentic on this LinkedIn post and reply as 0102"
        )
        self.assertIsNotNone(parsed)
        action, params = parsed  # type: ignore[misc]
        self.assertEqual(action, "reply_post")
        self.assertEqual(params.get("agentic"), "true")
        self.assertEqual(params.get("dry_run"), "true")
        self.assertEqual(params.get("post_index"), "0")

    def test_parse_natural_live_like_reply_command(self):
        parsed = _parse_natural_linkedin_command(
            "LinkedIn like and reply to this post now"
        )
        self.assertIsNotNone(parsed)
        action, params = parsed  # type: ignore[misc]
        self.assertEqual(action, "like_reply")
        self.assertEqual(params.get("dry_run"), "false")

    def test_parse_natural_selected_post_and_read_first(self):
        parsed = _parse_natural_linkedin_command(
            "LinkedIn use visible selected post and read post first then comment as 0102"
        )
        self.assertIsNotNone(parsed)
        action, params = parsed  # type: ignore[misc]
        self.assertEqual(action, "reply_post")
        self.assertEqual(params.get("use_selected_post"), "true")
        self.assertEqual(params.get("read_first"), "true")

    def test_parse_natural_short_operator_phrase(self):
        parsed = _parse_natural_linkedin_command(
            "use post 2 and read first then comment as 0102"
        )
        self.assertIsNotNone(parsed)
        action, params = parsed  # type: ignore[misc]
        self.assertEqual(action, "reply_post")
        self.assertEqual(params.get("post_index"), "1")
        self.assertEqual(params.get("read_first"), "true")

    def test_parse_natural_post_two_is_second_visible_post(self):
        parsed = _parse_natural_linkedin_command(
            "LinkedIn go agentic on post 2 and reply as 0102"
        )
        self.assertIsNotNone(parsed)
        action, params = parsed  # type: ignore[misc]
        self.assertEqual(action, "reply_post")
        self.assertEqual(params.get("post_index"), "1")

    async def test_handle_command_success(self):
        mock_result = {"success": True, "action": "read_feed", "posts_count": 1}
        with patch(
            "modules.communication.moltbot_bridge.src.linkedin_social_adapter.execute_linkedin_action",
            new=AsyncMock(return_value=mock_result),
        ):
            response = await handle_linkedin_social_intent(
                "linkedin action read_feed max_posts=1",
                sender="@UnDaoDu",
            )
        self.assertIsNotNone(response)
        self.assertIn("LinkedIn action executed", response or "")
        self.assertIn('"success": true', (response or "").lower())

    async def test_handle_unsupported_action(self):
        response = await handle_linkedin_social_intent(
            "linkedin action unknown_action",
            sender="@UnDaoDu",
        )
        self.assertIsNotNone(response)
        self.assertIn("not recognized", response or "")

    async def test_handle_natural_linkedin_request(self):
        mock_result = {
            "success": True,
            "action": "reply_post",
            "dry_run": True,
            "skill": "linkedin_agentic_reply",
        }
        with patch(
            "modules.communication.moltbot_bridge.src.linkedin_social_adapter.execute_linkedin_action",
            new=AsyncMock(return_value=mock_result),
        ) as exec_mock:
            response = await handle_linkedin_social_intent(
                "0102 go agentic on this LinkedIn post and reply as 0102",
                sender="@UnDaoDu",
            )
        self.assertIsNotNone(response)
        exec_mock.assert_awaited()
        called_action = exec_mock.await_args.args[0]
        called_params = exec_mock.await_args.args[1]
        self.assertEqual(called_action, "reply_post")
        self.assertEqual(called_params.get("agentic"), "true")
        self.assertIn("Skill executed: linkedin_agentic_reply", response or "")

    async def test_execute_scam_reply_dry_run_builds_template(self):
        class _DummyLinkedIn:
            def __init__(self, *args, **kwargs):
                pass

            def close(self):
                return None

        with patch(
            "modules.infrastructure.browser_actions.src.linkedin_actions.LinkedInActions",
            new=_DummyLinkedIn,
        ):
            result = await execute_linkedin_action(
                "scam_reply",
                {"post_index": "1", "dry_run": "true", "risk_reason": "hidden shortlink"},
            )

        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("dry_run"))
        self.assertEqual(result.get("post_index"), 1)
        self.assertIn("Potentially risky pattern", result.get("reply_text", ""))

    async def test_execute_reply_post_agentic_dry_run_uses_drafter(self):
        class _DummyLinkedIn:
            def __init__(self, *args, **kwargs):
                pass

            async def draft_agentic_reply(
                self,
                post_index=0,
                post_context="",
                author="",
                engagement_reason="",
                agent_identity="0102",
                use_selected_post=False,
                read_first=False,
            ):
                return {
                    "success": True,
                    "reply_text": "That is the real shift. Once the loop is embodied, fleet memory compounds instead of resetting.",
                    "post_index": post_index,
                    "agent_identity": agent_identity,
                    "method": "digital_twin",
                    "use_selected_post": use_selected_post,
                    "read_first": read_first,
                }

            def close(self):
                return None

        with patch(
            "modules.infrastructure.browser_actions.src.linkedin_actions.LinkedInActions",
            new=_DummyLinkedIn,
        ):
            result = await execute_linkedin_action(
                "reply_post",
                {"post_index": "0", "agentic": "true", "dry_run": "true"},
            )

        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("dry_run"))
        self.assertTrue(result.get("agentic_requested"))
        self.assertIn("fleet memory compounds", result.get("reply_text", ""))
        self.assertEqual(result.get("draft", {}).get("method"), "digital_twin")
        self.assertEqual(result.get("skill"), "linkedin_agentic_reply")

    async def test_execute_reply_post_agentic_routes_via_skill_wrapper(self):
        with patch(
            "modules.platform_integration.linkedin_agent.skillz.linkedin_agentic_reply.execute_skill",
            new=AsyncMock(
                return_value={
                    "success": True,
                    "action": "reply_post",
                    "skill": "linkedin_agentic_reply",
                    "reply_text": "skill-routed reply",
                }
            ),
        ) as mock_skill:
            result = await execute_linkedin_action(
                "reply_post",
                {"post_index": "0", "agentic": "true", "dry_run": "true"},
            )

        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("skill"), "linkedin_agentic_reply")
        mock_skill.assert_awaited_once()

    async def test_execute_reply_post_agentic_selected_post_flags_propagate(self):
        class _DummyLinkedIn:
            def __init__(self, *args, **kwargs):
                pass

            async def draft_agentic_reply(
                self,
                post_index=0,
                post_context="",
                author="",
                engagement_reason="",
                agent_identity="0102",
                use_selected_post=False,
                read_first=False,
            ):
                return {
                    "success": True,
                    "reply_text": "Selected post was read before reply drafting.",
                    "post_index": post_index,
                    "agent_identity": agent_identity,
                    "method": "digital_twin",
                    "use_selected_post": use_selected_post,
                    "read_first": read_first,
                }

            def close(self):
                return None

        with patch(
            "modules.infrastructure.browser_actions.src.linkedin_actions.LinkedInActions",
            new=_DummyLinkedIn,
        ):
            result = await execute_linkedin_action(
                "reply_post",
                {
                    "post_index": "1",
                    "agentic": "true",
                    "dry_run": "true",
                    "use_selected_post": "true",
                    "read_first": "true",
                },
            )

        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("draft", {}).get("use_selected_post"), True)
        self.assertEqual(result.get("draft", {}).get("read_first"), True)

    async def test_execute_scam_scan_reply_dry_run_returns_plans(self):
        class _DummyLinkedIn:
            def __init__(self, *args, **kwargs):
                pass

            async def scan_feed_for_scam(self, max_posts=10, min_score=4):
                return [
                    {
                        "post_id": "index_0",
                        "post_index": 0,
                        "author": "Suspicious Seller",
                        "risk_score": 6,
                        "risk_signals": ["third_party_setup_offer", "external_link"],
                        "suggested_reply": "Please verify official channels first.",
                    }
                ]

            def close(self):
                return None

        with patch(
            "modules.infrastructure.browser_actions.src.linkedin_actions.LinkedInActions",
            new=_DummyLinkedIn,
        ):
            result = await execute_linkedin_action(
                "scam_scan_reply",
                {"dry_run": "true", "agentic": "true", "max_replies": "1"},
            )

        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("dry_run"))
        self.assertEqual(len(result.get("planned_replies", [])), 1)
        self.assertTrue(result["planned_replies"][0]["agentic_requested"])


# Safety acceptance replaces the prior eleven current-behavior characterizations.
# Real package bootstrap remains excluded by the reviewed synchronous runner.
import asyncio
import builtins
import sys
from copy import deepcopy
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def linkedin_inert(monkeypatch):
    adapter = sys.modules[execute_linkedin_action.__module__]
    module_name = "modules.infrastructure.browser_actions.src.linkedin_actions"
    outcome = SimpleNamespace(success=True, to_dict=lambda: {"success": True})
    client = SimpleNamespace(
        like_post=AsyncMock(return_value=outcome),
        like_and_reply=AsyncMock(return_value=outcome),
        reply_to_post=AsyncMock(return_value=outcome),
        read_feed=AsyncMock(return_value=[{"post_id": "synthetic_post"}]), close=Mock(),
    )
    factory = Mock(return_value=client)
    fake = ModuleType(module_name)
    fake.LinkedInActions = factory
    monkeypatch.setitem(sys.modules, module_name, fake)
    agentic = AsyncMock(return_value={"success": True, "route": "inert_agentic"})
    draft = AsyncMock(side_effect=AssertionError("unexpected provider drafting"))
    monkeypatch.setattr(adapter, "_execute_agentic_linkedin_skill", agentic)
    monkeypatch.setattr(adapter, "_draft_agentic_linkedin_reply", draft)
    state = SimpleNamespace(adapter=adapter, client=client, factory=factory,
                            agentic=agentic, draft=draft, deny_import=False, imports=[])
    original_import = builtins.__import__

    def tracked_import(name, *args, **kwargs):
        if name == module_name:
            state.imports.append(name)
            if state.deny_import:
                raise AssertionError("browser import forbidden before preview")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", tracked_import)
    return state


def _linkedin_direct(action, params, observer=None):
    before = deepcopy(params)
    with pytest.raises(RuntimeError, match="no running event loop"):
        asyncio.get_running_loop()
    try:
        return asyncio.run(execute_linkedin_action(action, params, observer))
    finally:
        assert params == before


def _linkedin_wrapper(task):
    from modules.platform_integration.linkedin_agent.skillz.linkedin_engagement.executor import execute

    before = deepcopy(task)
    with pytest.raises(RuntimeError, match="no running event loop"):
        asyncio.get_running_loop()
    try:
        return execute(task)
    finally:
        assert task == before


def _linkedin_no_effects(state):
    assert state.imports == []
    state.factory.assert_not_called()
    state.client.close.assert_not_called()
    state.agentic.assert_not_awaited()
    state.draft.assert_not_awaited()
    for name in ("like_post", "like_and_reply", "reply_to_post", "read_feed"):
        getattr(state.client, name).assert_not_awaited()


def _linkedin_preview(action, index=2, post_id="index_2"):
    result = {"success": True, "action": action, "dry_run": True,
              "post_id": post_id, "post_index": index}
    if action == "like_reply":
        result.update(reply_text="Synthetic reply", agentic_requested=False, draft=None)
    return result


@pytest.mark.parametrize("outer,nested", [
    ("omitted", "false"), (True, "false"), ("omitted", False),
    (True, False), (True, "missing"), (False, "true"),
])
def test_linkedin_dry_run_wrapper_precedence(linkedin_inert, monkeypatch, outer, nested):
    task = {"action": "reply_post", "params": {"reply_text": "Synthetic reply"}}
    if outer != "omitted":
        task["dry_run"] = outer
    if nested != "missing":
        task["params"]["dry_run"] = nested
    recorder = AsyncMock(return_value={"success": True})
    monkeypatch.setattr(linkedin_inert.adapter, "execute_linkedin_action", recorder)
    result = _linkedin_wrapper(task)
    expected = {"reply_text": "Synthetic reply", "dry_run": "false" if outer is False else "true"}
    recorder.assert_awaited_once_with("reply_post", expected)
    assert recorder.await_args.args[1] is not task["params"]
    assert result["params"] == expected and result["success"] is True
    _linkedin_no_effects(linkedin_inert)


@pytest.mark.parametrize("action", [
    "like_post", "reply_post", "like_reply", "scam_reply", "scam_scan_reply",
    "engagement_session", "connect", "digital_twin", "group_post",
])
def test_linkedin_dry_run_all_write_flags(linkedin_inert, monkeypatch, action):
    recorder = AsyncMock(return_value={"success": True})
    monkeypatch.setattr(linkedin_inert.adapter, "execute_linkedin_action", recorder)
    result = _linkedin_wrapper({"action": action, "params": {"dry_run": "false"}})
    recorder.assert_awaited_once_with(action, {"dry_run": "true"})
    assert result["success"] is True
    _linkedin_no_effects(linkedin_inert)


def test_linkedin_dry_run_read_control(linkedin_inert):
    result = _linkedin_wrapper({"action": "read_feed", "params": {"max_posts": "2"}})
    assert result["params"] == {"max_posts": "2"}
    assert result["result"]["posts"] == [{"post_id": "synthetic_post"}]
    linkedin_inert.client.read_feed.assert_awaited_once_with(max_posts=2)
    linkedin_inert.factory.assert_called_once()
    linkedin_inert.client.close.assert_called_once_with()
    for name in ("like_post", "like_and_reply", "reply_to_post"):
        getattr(linkedin_inert.client, name).assert_not_awaited()


@pytest.mark.parametrize("route", ["direct", "wrapper", "wrapper_conflict"])
def test_linkedin_dry_run_reply_guard_after_construction(linkedin_inert, route):
    params = {"reply_text": "Synthetic reply", "dry_run": "true"}
    if route == "direct":
        result = _linkedin_direct("reply_post", params)
    else:
        if route == "wrapper_conflict":
            params["dry_run"] = "false"
        result = _linkedin_wrapper({"action": "reply_post", "params": params})["result"]
    assert result == _linkedin_preview("like_reply", index=0, post_id="index_0") | {"action": "reply_post"}
    linkedin_inert.factory.assert_called_once()
    linkedin_inert.client.close.assert_called_once_with()
    linkedin_inert.client.reply_to_post.assert_not_awaited()


@pytest.mark.parametrize("action", ["like_post", "like_reply"])
@pytest.mark.parametrize("index,post_id,expected_index,expected_id", [
    ("2", " explicit-id ", 2, "explicit-id"), ("invalid", " ", 0, "index_0"),
])
def test_linkedin_dry_run_early_preview(linkedin_inert, action, index, post_id, expected_index, expected_id):
    linkedin_inert.deny_import = True
    params = {"dry_run": "true", "post_index": index, "post_id": post_id,
              "reply_text": " Synthetic reply "}
    result = _linkedin_direct(action, params)
    assert result == _linkedin_preview(action, expected_index, expected_id)
    _linkedin_no_effects(linkedin_inert)


@pytest.mark.parametrize("flag", [True, " TRUE ", "yes", "on"])
def test_linkedin_dry_run_truthy_preview(linkedin_inert, flag):
    linkedin_inert.deny_import = True
    result = _linkedin_direct("like_post", {"dry_run": flag, "post_index": "2", "agentic": "true"})
    assert result == _linkedin_preview("like_post")
    _linkedin_no_effects(linkedin_inert)


def test_linkedin_dry_run_missing_reply(linkedin_inert):
    linkedin_inert.deny_import = True
    result = _linkedin_direct("like_reply", {"dry_run": "true", "reply_text": " "})
    assert result == {"success": False, "action": "like_reply", "error": "missing reply_text",
                      "agentic_requested": False, "draft": None}
    _linkedin_no_effects(linkedin_inert)


def test_linkedin_dry_run_agentic_route(linkedin_inert):
    linkedin_inert.deny_import = True
    params = {"dry_run": "true", "agentic": "true", "browser_port": "invalid"}
    observer = object()
    result = _linkedin_direct("like_reply", params, observer)
    assert result == {"success": True, "route": "inert_agentic"}
    linkedin_inert.agentic.assert_awaited_once_with("like_reply", params, observer)
    assert linkedin_inert.agentic.await_args.args[1] is params
    assert linkedin_inert.imports == []
    linkedin_inert.factory.assert_not_called()
    linkedin_inert.draft.assert_not_awaited()


@pytest.mark.parametrize("action", ["like_post", "like_reply"])
def test_linkedin_dry_run_invalid_port(linkedin_inert, action):
    linkedin_inert.deny_import = True
    with pytest.raises(ValueError):
        _linkedin_direct(action, {"dry_run": "true", "browser_port": "invalid", "reply_text": "reply"})
    _linkedin_no_effects(linkedin_inert)


@pytest.mark.parametrize("action,field", [("like_post", "post_id"), ("like_reply", "reply_text")])
def test_linkedin_dry_run_invalid_field(linkedin_inert, action, field):
    linkedin_inert.deny_import = True
    with pytest.raises(AttributeError):
        _linkedin_direct(action, {"dry_run": "true", field: None})
    _linkedin_no_effects(linkedin_inert)


@pytest.mark.parametrize("action", ["like_post", "like_reply"])
def test_linkedin_dry_run_wrapper_preview(linkedin_inert, action):
    linkedin_inert.deny_import = True
    task = {"action": action, "dry_run": True,
            "params": {"dry_run": "false", "post_index": "2", "reply_text": " Synthetic reply "}}
    result = _linkedin_wrapper(task)
    assert result["success"] is True and result["params"]["dry_run"] == "true"
    assert result["result"] == _linkedin_preview(action)
    _linkedin_no_effects(linkedin_inert)


@pytest.mark.parametrize("action,method", [("like_post", "like_post"), ("like_reply", "like_and_reply")])
@pytest.mark.parametrize("flag", ["omitted", "false"])
def test_linkedin_dry_run_live_compatibility(linkedin_inert, action, method, flag):
    params = {"post_index": "2", "post_id": " explicit-id ", "reply_text": " Synthetic reply ",
              "profile": "synthetic", "browser_port": "9223"}
    if flag != "omitted":
        params["dry_run"] = flag
    observer = object()
    result = _linkedin_direct(action, params, observer)
    expected = {"success": True, "action": action, "result": {"success": True}}
    args = {"post_id": "explicit-id", "post_index": 2}
    if action == "like_reply":
        args["reply_text"] = "Synthetic reply"
        expected.update(reply_text="Synthetic reply", agentic_requested=False, draft=None)
    assert result == expected
    getattr(linkedin_inert.client, method).assert_awaited_once_with(**args)
    linkedin_inert.factory.assert_called_once_with(profile="synthetic", browser_port=9223, dom_action_observer=observer)
    linkedin_inert.client.close.assert_called_once_with()
    linkedin_inert.agentic.assert_not_awaited()
    linkedin_inert.draft.assert_not_awaited()


@pytest.mark.parametrize("action,method", [("like_post", "like_post"), ("like_reply", "like_and_reply")])
@pytest.mark.parametrize("phase", ["constructor", "action", "close"])
def test_linkedin_dry_run_live_errors(linkedin_inert, action, method, phase):
    exc = RuntimeError("synthetic " + phase)
    target = {"constructor": linkedin_inert.factory, "action": getattr(linkedin_inert.client, method),
              "close": linkedin_inert.client.close}[phase]
    target.side_effect = exc
    with pytest.raises(RuntimeError) as caught:
        _linkedin_direct(action, {"reply_text": "reply", "dry_run": "false"})
    assert caught.value is exc
    assert linkedin_inert.client.close.call_count == (0 if phase == "constructor" else 1)
    assert getattr(linkedin_inert.client, method).await_count == (0 if phase == "constructor" else 1)


def test_linkedin_dry_run_close_error_wins(linkedin_inert):
    linkedin_inert.client.like_post.side_effect = ValueError("action")
    exc = RuntimeError("close")
    linkedin_inert.client.close.side_effect = exc
    with pytest.raises(RuntimeError) as caught:
        _linkedin_direct("like_post", {})
    assert caught.value is exc and isinstance(caught.value.__context__, ValueError)
    linkedin_inert.client.close.assert_called_once_with()


@pytest.mark.parametrize("action,error", [("", "no_action_specified"), ("NOT_SUPPORTED", "unsupported_action")])
def test_linkedin_dry_run_wrapper_validation(linkedin_inert, monkeypatch, action, error):
    recorder = AsyncMock(side_effect=AssertionError("unexpected delegation"))
    monkeypatch.setattr(linkedin_inert.adapter, "execute_linkedin_action", recorder)
    result = _linkedin_wrapper({"action": action})
    assert result["success"] is False and result["error"] == error
    assert result["skill"] == "linkedin_engagement" and len(result["supported"]) == 13
    if action:
        assert result["action"] == "not_supported"
    else:
        assert "action" not in result
    recorder.assert_not_awaited()
    _linkedin_no_effects(linkedin_inert)


@pytest.mark.parametrize("exc,error", [(ImportError("synthetic import"), "adapter_import_failed"),
                                      (ValueError("x" * 600), "execution_failed")])
def test_linkedin_dry_run_wrapper_error_envelope(linkedin_inert, monkeypatch, exc, error):
    from modules.platform_integration.linkedin_agent.skillz.linkedin_engagement import executor

    monkeypatch.setattr(executor, "time", SimpleNamespace(monotonic=Mock(side_effect=[1.0, 1.125])))
    recorder = AsyncMock(side_effect=exc)
    monkeypatch.setattr(linkedin_inert.adapter, "execute_linkedin_action", recorder)
    result = _linkedin_wrapper({"action": "like_post"})
    expected = {"success": False, "skill": "linkedin_engagement", "action": "like_post",
                "error": error, "detail": str(exc) if error == "adapter_import_failed" else str(exc)[:500]}
    if error == "execution_failed":
        expected["execution_time_ms"] = 125
    assert result == expected
    recorder.assert_awaited_once_with("like_post", {"dry_run": "true"})
    _linkedin_no_effects(linkedin_inert)


@pytest.mark.parametrize("payload,success", [({"success": True}, True), ({"success": False}, False), ([], False)])
def test_linkedin_dry_run_wrapper_result_envelope(linkedin_inert, monkeypatch, payload, success):
    from modules.platform_integration.linkedin_agent.skillz.linkedin_engagement import executor

    monkeypatch.setattr(executor, "time", SimpleNamespace(monotonic=Mock(side_effect=[1.0, 1.125])))
    recorder = AsyncMock(return_value=payload)
    monkeypatch.setattr(linkedin_inert.adapter, "execute_linkedin_action", recorder)
    result = _linkedin_wrapper({"action": " LIKE_POST ", "sender": "synthetic", "params": {}})
    assert result == {"success": success, "skill": "linkedin_engagement", "action": "like_post",
                      "sender": "synthetic", "params": {"dry_run": "true"}, "result": payload,
                      "execution_time_ms": 125}
    recorder.assert_awaited_once_with("like_post", {"dry_run": "true"})
    _linkedin_no_effects(linkedin_inert)


def test_linkedin_dry_run_wrapper_import_error(linkedin_inert, monkeypatch):
    original_import = builtins.__import__

    def failed_adapter_import(name, *args, **kwargs):
        if name == execute_linkedin_action.__module__:
            raise ImportError("synthetic missing adapter")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", failed_adapter_import)
    result = _linkedin_wrapper({"action": "like_post"})
    assert result == {"success": False, "skill": "linkedin_engagement", "action": "like_post",
                      "error": "adapter_import_failed", "detail": "synthetic missing adapter"}
    _linkedin_no_effects(linkedin_inert)


if __name__ == "__main__":
    unittest.main(verbosity=2)
