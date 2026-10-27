"""Offline editorial package contracts; replaces the invalid empty scaffold."""

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from modules.platform_integration.social_media_orchestrator.src.content.content_orchestrator import prepare_campaign
from modules.platform_integration.social_media_orchestrator.src.content.campaign_brief import CampaignBriefError
from modules.platform_integration.social_media_orchestrator.src.content.campaign_planner import execute_content_campaign


def sample_brief():
    return {
        "schema_version": "social_content_brief.v1", "campaign_id": "alpha_launch",
        "brand": {"foundup_id": "alpha", "canonical_brand": "Alpha", "default_locale": "en",
                  "rules": ["Use plain language."], "authority_boundary": "BRANDING_ONLY_NO_EXECUTION_AUTHORITY"},
        "audience": "Developers", "objective": "Read the release notes",
        "cta": {"label": "Read more", "url": "https://example.org/alpha"},
        "platforms": ["x", "linkedin"], "start_at": "2026-10-28T09:00:00+09:00",
        "interval_hours": 24, "max_items": 7,
        "sources": [
            {"source_id": "release", "foundup_id": "alpha", "url": "https://example.org/alpha",
             "excerpt": "Alpha now exports plain text."},
            {"source_id": "guide", "foundup_id": "alpha", "url": "https://example.org/guide",
             "excerpt": "The guide explains the export settings."}],
        "topics": [
            {"topic_id": "guide", "title": "Export guide", "source_ids": ["guide"], "priority": 2},
            {"topic_id": "release", "title": "Export release", "source_ids": ["release"], "priority": 5}],
    }


class TestContentOrchestrator(unittest.TestCase):
    def test_source_preserving_drafts_ordered_slots_and_no_input_mutation(self):
        brief = sample_brief()
        original = deepcopy(brief)
        package = prepare_campaign(brief)
        self.assertEqual([i["topic_id"] for i in package["items"]], ["release", "guide"])
        self.assertEqual([i["proposed_at"] for i in package["items"]],
                         ["2026-10-28T00:00:00+00:00", "2026-10-29T00:00:00+00:00"])
        for item in package["items"]:
            for draft in item["drafts"].values():
                self.assertIn(brief["cta"]["url"], draft["content"])
                self.assertFalse(draft["truncated"])
                for key in item["source_ids"]:
                    source = next(s for s in brief["sources"] if s["source_id"] == key)
                    self.assertIn(source["excerpt"], draft["content"])
                    self.assertIn(source["url"], draft["content"])
        package["brand"]["rules"].append("Changed")
        package["sources"][0]["excerpt"] = "Changed"
        self.assertEqual(brief, original)

    def test_revision_binding_and_truth_boundaries(self):
        brief = sample_brief()
        package = prepare_campaign(brief)
        self.assertEqual(package, prepare_campaign(deepcopy(brief)))
        for field, value in (("objective", "Read guide"), ("start_at", "2026-11-01T09:00:00+09:00")):
            changed = deepcopy(brief)
            changed[field] = value
            self.assertNotEqual(package["package_revision"], prepare_campaign(changed)["package_revision"])
        self.assertFalse(package["publication_ready"])
        self.assertIsNone(package["publication_grant"])
        self.assertFalse(package["brand_rules_applied"])
        self.assertEqual(package["evidence_status"], "supplied_unverified")
        self.assertEqual(package["measurement"]["status"], "provider_collection_not_connected")

    def test_overlength_copy_is_withheld_without_cutting_qualifiers_or_urls(self):
        brief = sample_brief()
        brief["sources"][0]["excerpt"] = "Evidence is preliminary. " * 30
        drafts = prepare_campaign(brief)["items"][0]["drafts"]
        self.assertEqual(drafts["x"]["status"], "shorter_copy_required")
        self.assertIsNone(drafts["x"]["content"])
        self.assertIn(brief["sources"][0]["excerpt"], drafts["linkedin"]["content"])
        brief["sources"] = [{"source_id": f"s{i}", "foundup_id": "alpha", "url": "https://example.org/a",
                             "excerpt": "Evidence " * 130} for i in range(3)]
        brief["topics"] = [{"topic_id": "long", "title": "Evidence", "source_ids": ["s0", "s1", "s2"], "priority": 1}]
        for draft in prepare_campaign(brief)["items"][0]["drafts"].values():
            self.assertEqual(draft["status"], "shorter_copy_required")

    def test_evidence_deduplication_item_cap_and_absolute_offset_slots(self):
        brief = sample_brief()
        brief["topics"].append({"topic_id": "duplicate", "title": "New title", "source_ids": ["release"], "priority": 1})
        self.assertEqual(len(prepare_campaign(brief)["items"]), 2)
        brief["max_items"] = 1
        self.assertEqual(len(prepare_campaign(brief)["items"]), 1)
        brief["topics"][0]["priority"] = 5
        brief["start_at"] = "2026-11-01T01:30:00-04:00"
        first = prepare_campaign(brief)["items"][0]
        self.assertEqual(first["topic_id"], "guide")
        self.assertEqual(first["proposed_at"], "2026-11-01T05:30:00+00:00")

    def test_invalid_field_shapes_and_bounds(self):
        for path, value in (
            (("schema_version",), "unknown"), (("campaign_id",), "../x"),
            (("audience",), ""), (("objective",), "bad\ntext"),
            (("audience",), "\ud800"), (("objective",), "bad\x7ftext"),
            (("platforms",), []), (("platforms",), ["x", "x"]), (("platforms",), ["facebook"]),
            (("platforms",), [{}]), (("interval_hours",), True), (("interval_hours",), 0),
            (("max_items",), 15), (("start_at",), "2026-10-28T09:00:00"), (("start_at",), "tomorrow"),
            (("sources",), []), (("topics",), []), (("brand", "authority_boundary"), "commander"),
            (("brand", "rules"), []), (("brand", "canonical_brand"), 3),
            (("brand", "default_locale"), "e"), (("brand", "foundup_id"), "alpha-beta"),
        ):
            brief = sample_brief()
            target = brief
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path, value=value), self.assertRaises(CampaignBriefError):
                prepare_campaign(brief)

    def test_scope_duplicate_sources_and_unrecognized_authority_reject(self):
        for change in (
            lambda b: b["sources"][0].update(foundup_id="beta"),
            lambda b: b["sources"].append(deepcopy(b["sources"][0])),
            lambda b: b["topics"][0].update(source_ids=["missing"]),
            lambda b: b["topics"][0].update(source_ids=["release", "release"]),
            lambda b: b["topics"][0].update(source_ids=[{}]),
            lambda b: b["topics"][0].update(priority=True),
            lambda b: b["topics"].append(deepcopy(b["topics"][0])),
            lambda b: b["sources"][0].update(verified=True), lambda b: b.update(approved=True),
        ):
            brief = sample_brief()
            change(brief)
            with self.subTest(brief=brief), self.assertRaises(CampaignBriefError):
                prepare_campaign(brief)

    def test_url_and_calendar_failures(self):
        for url in ("http://example.org", "https://user@example.org/a", "https://example.org:443/a",
                    "https://127.0.0.1/a", "https://example.local/a", "https://example.org/a?secret=x",
                    "https://127.1/a", "https://foo..com/a", "https://www.-bad.com/a",
                    "https://example.org/a#x", "https://example.org/a\\b", "https://[::1]/a", "https://example.org/a b"):
            brief = sample_brief()
            brief["sources"][0]["url"] = url
            with self.subTest(url=url), self.assertRaises(CampaignBriefError):
                prepare_campaign(brief)
        brief = sample_brief()
        brief["start_at"] = "9999-12-31T23:00:00Z"
        with self.assertRaisesRegex(CampaignBriefError, "content_calendar_overflow"):
            prepare_campaign(brief)


class TestContentCampaignEntry(unittest.IsolatedAsyncioTestCase):
    async def test_real_route_with_effects_denied(self):
        from modules.communication.moltbot_bridge.src.social_campaign_adapter import execute_social_campaign

        def denied(*args, **kwargs):
            raise AssertionError("unexpected effect")
        with patch("os.getenv", denied), patch("builtins.open", denied), \
                patch("pathlib.Path.read_text", denied), patch("socket.create_connection", denied), \
                patch("subprocess.Popen", denied):
            result = await execute_social_campaign("content", {"brief": json.dumps(sample_brief())})
        self.assertEqual(result["status"], "prepared")
        self.assertTrue(result["no_publication_performed"])
        self.assertFalse(result["package"]["api_called"])

    async def test_bad_commands_do_not_default_to_execution(self):
        from modules.communication.moltbot_bridge.src.social_campaign_adapter import _parse_campaign_command

        for message in ('social campaign content action=publish dry_run=false',
                        'social campaign content action=prepare action=publish',
                        'social campaign content stray-token', 'social campaign content brief="unterminated'):
            campaign, params = _parse_campaign_command(message)
            result = await execute_content_campaign(params)
            self.assertEqual(campaign, "content")
            self.assertEqual(result["status"], "rejected")

    async def test_bad_json_size_and_authority(self):
        for params in (None, {"brief": 1}, {"file": "private.json"}, {"brief": "{"},
                       {"brief": '{"a":1,"a":2}'}, {"brief": "x" * 65537},
                       {"brief": "\ud800"}, {"brief": "[" * 2000},
                       {"dry_run": "false"}, {"action": "publish"}, {"brief": "null"}):
            with self.subTest(params=params):
                result = await execute_content_campaign(params)
                self.assertEqual(result["status"], "rejected")
                self.assertFalse(result["publication_ready"])


if __name__ == "__main__":
    unittest.main()
