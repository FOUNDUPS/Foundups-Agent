"""
Tests for social campaign adapter command parsing and routing.
"""

import unittest
from unittest.mock import AsyncMock, patch

from modules.communication.moltbot_bridge.src.social_campaign_adapter import (
    _parse_campaign_command,
    execute_social_campaign,
    handle_social_campaign_intent,
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
