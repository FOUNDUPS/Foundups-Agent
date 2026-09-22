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


# Current-behavior characterization, not dry-run safety acceptance. These cases
# deliberately record fake writes that the separately declared future contract
# must prevent. No real browser module or action client is used.
def _linkedin_dry_run_characterization(task, *, direct=False, forwarding=False):
    import asyncio
    import sys
    from contextlib import nullcontext
    from copy import deepcopy
    from types import ModuleType, SimpleNamespace
    from unittest.mock import Mock

    before = deepcopy(task)
    fake_result = SimpleNamespace(success=True, to_dict=lambda: {"success": True})
    client = SimpleNamespace(
        like_post=AsyncMock(return_value=fake_result),
        like_and_reply=AsyncMock(return_value=fake_result),
        reply_to_post=AsyncMock(return_value=fake_result),
        read_feed=AsyncMock(return_value=[{"post_id": "synthetic_post"}]),
        close=Mock(),
    )
    factory = Mock(return_value=client)
    module_name = "modules.infrastructure.browser_actions.src.linkedin_actions"
    browser = ModuleType(module_name)
    browser.LinkedInActions = factory
    adapter = sys.modules[execute_linkedin_action.__module__]
    recorder = AsyncMock(return_value={"success": True}) if forwarding else None
    replacement = (
        patch.object(adapter, "execute_linkedin_action", new=recorder)
        if forwarding else nullcontext()
    )
    with patch.dict(sys.modules, {module_name: browser}), replacement:
        if direct:
            result = asyncio.run(execute_linkedin_action(task["action"], task["params"]))
        else:
            from modules.platform_integration.linkedin_agent.skillz.linkedin_engagement.executor import execute

            result = execute(task)
    assert task == before
    assert result["success"] is True
    return result, factory, client, recorder


def _assert_linkedin_characterized_callbacks(factory, client, *, constructed, writes):
    assert factory.call_count == constructed
    assert client.close.call_count == constructed
    assert sum(action.await_count for action in (
        client.like_post, client.like_and_reply, client.reply_to_post,
    )) == writes


def _assert_linkedin_characterized_forwarding(task, expected):
    result, factory, client, recorder = _linkedin_dry_run_characterization(
        task, forwarding=True,
    )
    recorder.assert_awaited_once_with(task["action"], expected)
    assert recorder.await_args.args[1] is not task["params"]
    assert result["params"] == expected
    _assert_linkedin_characterized_callbacks(factory, client, constructed=0, writes=0)
    client.read_feed.assert_not_awaited()


def test_linkedin_dry_run_characterizes_default_nested_false_forwarding():
    task = {"action": "reply_post", "params": {"dry_run": "false", "reply_text": "Synthetic reply"}}
    _assert_linkedin_characterized_forwarding(task, dict(task["params"]))


def test_linkedin_dry_run_characterizes_true_nested_false_forwarding():
    task = {
        "action": "reply_post", "dry_run": True,
        "params": {"dry_run": "false", "reply_text": "Synthetic reply"},
    }
    _assert_linkedin_characterized_forwarding(task, dict(task["params"]))


def test_linkedin_dry_run_characterizes_true_adds_missing_nested_flag():
    task = {"action": "reply_post", "dry_run": True, "params": {"reply_text": "Synthetic reply"}}
    _assert_linkedin_characterized_forwarding(
        task, {"reply_text": "Synthetic reply", "dry_run": "true"},
    )


def test_linkedin_dry_run_characterizes_false_overrides_nested_true():
    task = {
        "action": "reply_post", "dry_run": False,
        "params": {"dry_run": "true", "reply_text": "Synthetic reply"},
    }
    _assert_linkedin_characterized_forwarding(
        task, {"reply_text": "Synthetic reply", "dry_run": "false"},
    )


def test_linkedin_dry_run_characterizes_read_control_without_added_flag():
    task = {"action": "read_feed", "params": {"max_posts": "2"}}
    result, factory, client, _ = _linkedin_dry_run_characterization(task)
    assert result["params"] == {"max_posts": "2"}
    assert result["params"] is not task["params"]
    assert result["result"]["posts"] == [{"post_id": "synthetic_post"}]
    client.read_feed.assert_awaited_once_with(max_posts=2)
    _assert_linkedin_characterized_callbacks(factory, client, constructed=1, writes=0)


def test_linkedin_dry_run_characterizes_direct_like_post_fake_write():
    task = {"action": "like_post", "params": {"post_index": "2", "dry_run": "true"}}
    result, factory, client, _ = _linkedin_dry_run_characterization(task, direct=True)
    assert result["action"] == "like_post"
    client.like_post.assert_awaited_once_with(post_id="index_2", post_index=2)
    client.read_feed.assert_not_awaited()
    _assert_linkedin_characterized_callbacks(factory, client, constructed=1, writes=1)


def test_linkedin_dry_run_characterizes_direct_like_reply_fake_write():
    task = {
        "action": "like_reply",
        "params": {"post_index": "2", "dry_run": "true", "reply_text": "Synthetic reply"},
    }
    result, factory, client, _ = _linkedin_dry_run_characterization(task, direct=True)
    assert result["action"] == "like_reply"
    client.like_and_reply.assert_awaited_once_with(
        post_id="index_2", post_index=2, reply_text="Synthetic reply",
    )
    client.read_feed.assert_not_awaited()
    _assert_linkedin_characterized_callbacks(factory, client, constructed=1, writes=1)


def test_linkedin_dry_run_characterizes_reply_guard_after_construction():
    task = {
        "action": "reply_post",
        "params": {"post_index": "2", "dry_run": "true", "reply_text": "Synthetic reply"},
    }
    result, factory, client, _ = _linkedin_dry_run_characterization(task, direct=True)
    assert result["dry_run"] is True
    assert result["agentic_requested"] is False
    assert result["reply_text"] == "Synthetic reply"
    client.read_feed.assert_not_awaited()
    _assert_linkedin_characterized_callbacks(factory, client, constructed=1, writes=0)


def test_linkedin_dry_run_characterizes_wrapper_conflict_reaching_fake_reply():
    task = {
        "action": "reply_post",
        "params": {"post_index": "2", "dry_run": "false", "reply_text": "Synthetic reply"},
    }
    result, factory, client, _ = _linkedin_dry_run_characterization(task)
    assert result["params"]["dry_run"] == "false"
    client.reply_to_post.assert_awaited_once_with(
        post_id="index_2", post_index=2, reply_text="Synthetic reply",
    )
    client.read_feed.assert_not_awaited()
    _assert_linkedin_characterized_callbacks(factory, client, constructed=1, writes=1)


def test_linkedin_dry_run_characterizes_wrapper_reply_preview_control():
    task = {
        "action": "reply_post", "dry_run": True,
        "params": {"post_index": "2", "reply_text": "Synthetic reply"},
    }
    result, factory, client, _ = _linkedin_dry_run_characterization(task)
    assert result["params"]["dry_run"] == "true"
    assert result["result"]["dry_run"] is True
    assert result["result"]["agentic_requested"] is False
    client.read_feed.assert_not_awaited()
    _assert_linkedin_characterized_callbacks(factory, client, constructed=1, writes=0)


def test_linkedin_dry_run_characterizes_wrapper_true_reaching_fake_like():
    task = {"action": "like_post", "dry_run": True, "params": {"post_index": "2"}}
    result, factory, client, _ = _linkedin_dry_run_characterization(task)
    assert result["params"]["dry_run"] == "true"
    client.like_post.assert_awaited_once_with(post_id="index_2", post_index=2)
    client.read_feed.assert_not_awaited()
    _assert_linkedin_characterized_callbacks(factory, client, constructed=1, writes=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
