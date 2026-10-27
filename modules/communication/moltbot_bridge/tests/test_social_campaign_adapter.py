"""
Tests for social campaign adapter command parsing and routing.
"""

import unittest
from unittest.mock import AsyncMock, patch

from modules.communication.moltbot_bridge.src.social_campaign_adapter import (
    _parse_campaign_command,
    execute_social_campaign,
    handle_social_campaign_intent,
    handle_petition_campaign_intent,
)


class TestSocialCampaignAdapter(unittest.IsolatedAsyncioTestCase):
    def test_parse_valid_campaign_command(self):
        parsed = _parse_campaign_command(
            'social campaign research_x_to_ln_group content="new research summary"'
        )
        self.assertIsNotNone(parsed)
        campaign, params = parsed  # type: ignore[misc]
        self.assertEqual(campaign, "research_x_to_ln_group")
        self.assertEqual(params.get("content"), "new research summary")

    def test_parse_alias_campaign_command(self):
        parsed = _parse_campaign_command(
            'social campaign research_to_ln content="new research summary"'
        )
        self.assertIsNotNone(parsed)
        campaign, params = parsed  # type: ignore[misc]
        self.assertEqual(campaign, "research_x_to_ln_group")
        self.assertEqual(params.get("content"), "new research summary")

    def test_parse_non_campaign(self):
        parsed = _parse_campaign_command("social action post now")
        self.assertIsNone(parsed)

    async def test_antifafm_real_route_defaults_to_preview(self):
        result = await execute_social_campaign("antifafm", {})
        self.assertEqual(result["status"], "preview")
        self.assertTrue(result["no_publication_performed"])
        self.assertFalse(result["api_called"])

    async def test_antifafm_targeting_parameter_is_rejected(self):
        result = await execute_social_campaign("antifafm", {"keywords": "MAGA"})
        self.assertEqual(result["error"], "campaign_parameter_unsupported")

    async def test_antifafm_malformed_tokens_never_default_to_execution(self):
        for command in (
            'social campaign antifafm action=publish dry_run=true dry_run=false',
            'social campaign antifafm action=publish stray-token',
            'social campaign antifafm content="unterminated',
        ):
            with self.subTest(command=command):
                campaign, params = _parse_campaign_command(command)
                result = await execute_social_campaign(campaign, params)
                self.assertFalse(result["success"])
                self.assertTrue(result["no_publication_performed"])

    async def test_handle_campaign_success(self):
        mock_result = {
            "success": True,
            "campaign": "research_x_to_ln_group",
            "steps": {
                "x_post": {"success": True},
                "linkedin_group_post": {"success": True},
            },
        }
        with patch(
            "modules.communication.moltbot_bridge.src.social_campaign_adapter.execute_social_campaign",
            new=AsyncMock(return_value=mock_result),
        ):
            response = await handle_social_campaign_intent(
                'social campaign research_x_to_ln_group content="new research summary"',
                sender="@UnDaoDu",
            )
        self.assertIsNotNone(response)
        self.assertIn("Social campaign executed", response or "")
        self.assertIn('"success": true', (response or "").lower())

    async def test_handle_unsupported_campaign(self):
        response = await handle_social_campaign_intent(
            "social campaign unknown_campaign content=test",
            sender="@UnDaoDu",
        )
        self.assertIsNotNone(response)
        self.assertIn("not recognized", response or "")

    async def test_petition_natural_request_returns_plan_not_execution(self):
        for message in (
            "RedDog, let's launch a petition on this",
            "Red Dog please start a petition https://www.change.org/p/example",
            "0102, launch the petition https://www.change.org/p/example",
            "social campaign petition action=plan petition_url=https://www.change.org/p/example",
        ):
            with self.subTest(message=message):
                response = await handle_petition_campaign_intent(message, "012")
                self.assertIn('"scope": "plan_only"', response)
                self.assertNotIn("Social campaign executed", response)

    async def test_petition_shortcut_cannot_dispatch_other_publishers(self):
        for message in (
            "social campaign antifafm action=publish dry_run=false",
            'social campaign research_x_to_ln_group content="test" dry_run=false',
            "do not launch a petition", "what if we launch a petition?",
            "explain a petition", "someone wrote: launch a petition",
        ):
            with self.subTest(message=message), patch(
                "modules.communication.moltbot_bridge.src.social_campaign_adapter.execute_social_campaign",
                new=AsyncMock(),
            ) as execute:
                self.assertIsNone(await handle_petition_campaign_intent(message, "012"))
                execute.assert_not_awaited()

    async def test_petition_malformed_command_is_rejected(self):
        for message in (
            "social campaign petition action=plan action=publish",
            "social campaign petition stray-token",
            'social campaign petition title="unterminated',
            "launch a petition https://www.change.org/p/one https://www.change.org/p/two",
        ):
            with self.subTest(message=message):
                response = await handle_petition_campaign_intent(message, "012")
                self.assertIn('"status": "rejected"', response)
                self.assertIn('"no_publication_performed": true', response)

    async def test_conversation_controller_returns_petition_plan_before_provider_routes(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from modules.communication.moltbot_bridge.src.openclaw_social_controller import try_conversation_social_control

        dae = SimpleNamespace(_record_social_response=Mock(), _mark_conversation_engine=Mock())
        intent = SimpleNamespace(raw_message="RedDog, let's launch a petition on this", sender="012")
        result = await try_conversation_social_control(dae, intent)
        self.assertIn('"status": "awaiting_petition_url"', result)
        dae._mark_conversation_engine.assert_called_once_with(
            "social_campaign_control", "deterministic_conversation_route")

    async def test_existing_research_provider_mapping_is_preserved(self):
        import sys
        from types import SimpleNamespace

        x = AsyncMock(return_value={"success": True})
        linkedin = AsyncMock(return_value={"success": True})
        with patch.dict(sys.modules, {
            "modules.communication.moltbot_bridge.src.x_social_adapter": SimpleNamespace(execute_x_action=x),
            "modules.communication.moltbot_bridge.src.linkedin_social_adapter": SimpleNamespace(execute_linkedin_action=linkedin),
        }):
            result = await execute_social_campaign("research_x_to_ln_group", {
                "content": "research draft", "dry_run": "false", "x_dry_run": "true",
            })
        self.assertTrue(result["success"])
        self.assertEqual(result["dry_run"], {"x": True, "linkedin": False})
        self.assertEqual(x.await_args.args[0], "post")
        self.assertEqual(x.await_args.args[1]["content"], "research draft")
        self.assertEqual(x.await_args.args[1]["dry_run"], "true")
        self.assertEqual(linkedin.await_args.args[0], "group_post")
        self.assertEqual(linkedin.await_args.args[1]["summary"], "research draft")


if __name__ == "__main__":
    unittest.main(verbosity=2)
