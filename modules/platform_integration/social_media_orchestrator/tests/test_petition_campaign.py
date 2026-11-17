"""Petition intake boundaries: no provider effects or inferred launch authority."""

import unittest
from unittest.mock import patch

from modules.platform_integration.social_media_orchestrator.src.petition_campaign import execute_petition_campaign


class TestPetitionCampaign(unittest.IsolatedAsyncioTestCase):
    async def test_preview_requires_link_without_claiming_progress(self):
        result = await execute_petition_campaign({})
        self.assertEqual(result["status"], "awaiting_petition_url")
        self.assertIsNone(result["campaign_id"])
        self.assertFalse(result["publication_ready"])
        self.assertTrue(result["no_publication_performed"])

    async def test_tracking_variants_share_identity_and_never_verify_petition(self):
        results = [await execute_petition_campaign({"petition_url": url}) for url in (
            "https://change.org/p/example?recruiter=private-tracker#section",
            "https://www.change.org/p/example",
        )]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]["status"], "intake_ready")
        self.assertEqual(results[0]["account_setup"], "external_petition_adoption")
        self.assertFalse(results[0]["petition_verified"])
        self.assertNotIn("private-tracker", str(results[0]))

    async def test_other_platform_and_short_link_stay_unverified(self):
        for url, platform, short in (
            ("https://actionnetwork.org/petitions/example", "action_network", False),
            ("https://chng.it/example", "change_org", True),
        ):
            with self.subTest(url=url):
                result = await execute_petition_campaign({"petition_url": url})
                self.assertTrue(result["success"])
                self.assertEqual(result["petition_platform"], platform)
                self.assertEqual(result["short_link_resolution_required"], short)
                self.assertFalse(result["petition_verified"])

    async def test_provider_and_authority_flags_cannot_enable_effects(self):
        for params in (
            {"action": "publish"}, {"dry_run": "false"}, {"approved": "true"},
            {"authority": "commander"}, {"action": "sign_up"}, {"dry_run": "TRUE"},
            {"petition_url": 7}, {"platforms": "x,x"}, {"platforms": "email"},
            {"campaign_id": "../outside"}, {"title": "bad\nvalue"}, {"action": True},
        ):
            with self.subTest(params=params):
                result = await execute_petition_campaign(params)
                self.assertFalse(result["success"])
                self.assertTrue(result["no_publication_performed"])
                self.assertFalse(result["execution_supported"])

    async def test_nonpublic_or_confusable_urls_reject_without_echoing_values(self):
        for url in (
            "http://change.org/p/example", "https://127.0.0.1/p/example",
            "https://change.org.evil.invalid/p/example", "https://change.org:443/p/example",
            "https://organizer@change.org/p/example", "https://change.org/login_or_join",
            "https://change.org/p/../login", "https://change.org/p/%2e%2e",
            "https://change.org/p/a%2fb", "https://change.org/p/%252e%252e",
            "https://change.org/p/example\\other", "https://change.org/p/",
            "https://actionnetwork.org/users/sign_in", "https://chng.it/",
            "https://change.org/p//", "https://chng.it///",
        ):
            with self.subTest(url=url):
                result = await execute_petition_campaign({"petition_url": url})
                self.assertFalse(result["success"])
                self.assertNotIn(url, str(result))

    async def test_plan_reads_no_environment_files_or_providers(self):
        def denied(*args, **kwargs):
            raise AssertionError("unexpected effect")
        with patch("os.getenv", denied), patch("pathlib.Path.read_text", denied), \
                patch("pathlib.Path.read_bytes", denied), patch("socket.create_connection", denied), \
                patch("subprocess.Popen", denied), patch("builtins.open", denied):
            result = await execute_petition_campaign({
                "action": "plan", "petition_url": "https://www.change.org/p/example",
                "platforms": "x,linkedin,facebook,youtube",
            })
        self.assertTrue(result["success"])
        self.assertFalse(result["api_called"])
        self.assertFalse(result["model_called"])
        self.assertFalse(result["storage_written"])
        self.assertTrue(all(not item["enabled"] and item["account_id"] is None
                            for item in result["brief"]["platform_matrix"]))


if __name__ == "__main__":
    unittest.main()
