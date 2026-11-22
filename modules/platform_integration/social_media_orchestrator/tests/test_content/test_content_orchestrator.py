"""Offline editorial package contracts; the separate legacy scaffold is retained."""

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


def publication_packet():
    """Synthetic stage receipts, not provider or publication authority."""
    import hashlib

    digest = hashlib.sha256(b"approved public manuscript").hexdigest()
    artifact = hashlib.sha256(b"Japanese LinkedIn adaptation").hexdigest()
    receipt = "https://example.org/receipts/approved"
    return {
        "schema_version": "publication_reconciliation_input.v1",
        "foundup_id": "esingularity_001", "publication_id": "jhr-003",
        "audit_at": "2026-11-16T13:00:00Z",
        "source": {"revision": "manuscript-v8", "content_hash": digest,
                   "approval": {"state": "approved", "content_hash": digest,
                                "receipt_ref": receipt}},
        "archive": {"path": "modules/foundups/esingularity/jhr/reports/issue.md",
                    "commit_sha": "ab" * 20, "content_hash": digest},
        "website": {
            "url": "https://example.org/reports/jhr#jhr-003",
            "source_hash": digest,
            "deployment": {"state": "succeeded", "source_revision": "ab" * 20,
                           "receipt_ref": "https://example.org/receipts/deployed"},
            "observation": {"state": "present", "url": "https://example.org/reports/jhr#jhr-003",
                            "publication_id": "jhr-003", "source_revision": "manuscript-v8",
                            "content_hash": digest, "observed_at": "2026-11-16T12:55:00Z",
                            "evidence_ref": "https://example.org/receipts/readback"}},
        "channels": [{
            "platform": "linkedin", "locale": "ja",
            "destination": "https://example.org/newsletters/jhr",
            "artifact_hash": artifact, "source_revision": "manuscript-v8", "source_hash": digest,
            "approval": {"state": "approved", "content_hash": artifact, "receipt_ref": receipt,
                         "destination": "https://example.org/newsletters/jhr", "locale": "ja",
                         "platform": "linkedin", "source_revision": "manuscript-v8", "source_hash": digest},
            "delivery": {"state": "not_placed", "permalink": None, "artifact_hash": None,
                         "observed_at": "2026-11-16T12:55:00Z",
                         "evidence_ref": "https://example.org/receipts/queue",
                         "private_queue_checked": True,
                         "destination": "https://example.org/newsletters/jhr",
                         "publication_id": "jhr-003", "source_revision": "manuscript-v8"}}],
        "open_work": [],
    }


class TestPublicationReconciliation(unittest.IsolatedAsyncioTestCase):
    async def reconcile(self, input_packet, **overrides):
        from modules.communication.moltbot_bridge.src.social_campaign_adapter import execute_social_campaign

        return await execute_social_campaign("content", {
            "action": "reconcile", "dry_run": "true", "packet": json.dumps(input_packet), **overrides})

    async def test_stage_complete_inputs_only_prepare_review_and_memory_proposals(self):
        packet = publication_packet()
        original = deepcopy(packet)
        result = await self.reconcile(packet)
        self.assertEqual(result["status"], "reconciled")
        report = result["reconciliation"]
        self.assertEqual(report["channels"][0]["next_action"], "REVIEW_DESTINATION_HANDOFF")
        self.assertFalse(report["execution_admitted"])
        self.assertFalse(report["publication_ready"])
        self.assertEqual(report["evidence_status"], "SUPPLIED_UNVERIFIED")
        self.assertEqual(report["memory_projection"]["status"], "PROPOSED_NOT_WRITTEN")
        self.assertFalse(report["storage_written"])
        self.assertNotIn("verified_outcomes", report["memory_projection"])
        self.assertEqual(packet, original)

    async def test_merged_code_and_saved_site_cannot_replace_exact_live_release(self):
        for state in ("unknown", "saved", "blocked"):
            packet = publication_packet()
            packet["website"]["deployment"]["state"] = state
            packet["website"]["observation"]["state"] = "absent"
            report = (await self.reconcile(packet))["reconciliation"]
            with self.subTest(state=state):
                self.assertFalse(report["website"]["evidence_complete"])
                self.assertEqual(report["channels"][0]["next_action"], "RECONCILE_WEBSITE_RELEASE")
                self.assertEqual(report["amplification"]["next_action"], "BLOCKED_WEBSITE_RELEASE")

    async def test_wrong_exact_issue_host_anchor_revision_and_stale_observation_block(self):
        for field, value in (("url", "https://other.example.org/reports/jhr#jhr-003"),
                             ("url", "https://example.org/reports/jhr#jhr-002"),
                             ("publication_id", "jhr-002"), ("source_revision", "manuscript-v7"),
                             ("content_hash", "cd" * 32),
                             ("observed_at", "2026-10-16T12:55:00Z"),
                             ("observed_at", "2026-11-17T12:55:00Z")):
            packet = publication_packet()
            packet["website"]["observation"][field] = value
            report = (await self.reconcile(packet))["reconciliation"]
            with self.subTest(field=field, value=value):
                self.assertFalse(report["website"]["evidence_complete"])
                self.assertFalse(report["amplification"]["evidence_complete"])

    async def test_source_archive_and_destination_approval_bind_to_exact_artifacts(self):
        for field in ("source_approval", "archive", "channel_approval", "channel_source", "deployment_commit",
                      "approval_destination", "approval_locale"):
            packet = publication_packet()
            if field == "source_approval":
                packet["source"]["approval"]["content_hash"] = "ef" * 32
            elif field == "archive":
                packet["archive"]["content_hash"] = "ef" * 32
            elif field == "channel_approval":
                packet["channels"][0]["approval"]["content_hash"] = "ef" * 32
            elif field == "deployment_commit":
                packet["website"]["deployment"]["source_revision"] = "cd" * 20
            elif field == "approval_destination":
                packet["channels"][0]["approval"]["destination"] = "https://example.org/other"
            elif field == "approval_locale":
                packet["channels"][0]["approval"]["locale"] = "en"
            else:
                packet["channels"][0]["source_revision"] = "manuscript-v7"
            report = (await self.reconcile(packet))["reconciliation"]
            with self.subTest(field=field):
                self.assertNotEqual(report["channels"][0]["next_action"], "REVIEW_DESTINATION_HANDOFF")

    async def test_existing_edition_prevents_repost_despite_upstream_release_gap(self):
        packet = publication_packet()
        packet["website"]["observation"]["state"] = "absent"
        packet["channels"][0]["delivery"].update(
            state="live", permalink="https://example.org/articles/existing",
            artifact_hash=packet["channels"][0]["artifact_hash"])
        report = (await self.reconcile(packet))["reconciliation"]
        self.assertEqual(report["channels"][0]["next_action"], "READBACK_EXISTING_NO_REPOST")
        self.assertFalse(report["amplification"]["evidence_complete"])

    async def test_uncertain_submission_is_readback_only_and_unchecked_queue_is_unknown(self):
        packet = publication_packet()
        packet["channels"][0]["delivery"]["state"] = "submitted_unknown"
        report = (await self.reconcile(packet))["reconciliation"]
        self.assertEqual(report["channels"][0]["next_action"], "READBACK_ONLY")
        packet["channels"][0]["delivery"].update(state="not_placed", private_queue_checked=False)
        report = (await self.reconcile(packet))["reconciliation"]
        self.assertEqual(report["channels"][0]["delivery_status"], "unknown")
        self.assertEqual(report["channels"][0]["next_action"], "CHECK_DRAFTS_AND_SCHEDULE")

    async def test_old_open_release_obligation_survives_other_successes(self):
        packet = publication_packet()
        packet["open_work"] = [{"code": "sites_release_blocked", "owner": "website_owner",
                                "next_action": "Reconcile and release the approved issue",
                                "evidence_ref": "https://example.org/issues/2126#receipt",
                                "recorded_at": "2026-10-16T09:00:00+09:00"}]
        report = (await self.reconcile(packet))["reconciliation"]
        self.assertEqual(report["status"], "BLOCKED_OPEN_WORK")
        self.assertEqual(report["memory_projection"]["open_work"], packet["open_work"])
        self.assertFalse(report["amplification"]["evidence_complete"])

    async def test_duplicate_keys_are_review_identifiers_not_effect_grants(self):
        first = (await self.reconcile(publication_packet()))["reconciliation"]
        packet = publication_packet()
        packet["channels"][0]["locale"] = "en"
        second = (await self.reconcile(packet))["reconciliation"]
        self.assertNotEqual(first["channels"][0]["suggested_duplicate_key"],
                            second["channels"][0]["suggested_duplicate_key"])
        self.assertIsNone(first["publication_grant"])

    async def test_delivery_identity_hash_queue_and_approval_scope_are_bound(self):
        for state in ("live", "scheduled", "draft"):
            packet = publication_packet()
            delivery = packet["channels"][0]["delivery"]
            delivery.update(state=state, permalink="https://example.org/articles/existing",
                            artifact_hash=packet["channels"][0]["artifact_hash"])
            report = (await self.reconcile(packet))["reconciliation"]
            self.assertEqual(report["channels"][0]["delivery_status"], state)
            self.assertFalse(report["channels"][0]["delivery_status_is_verified"])
            for key, value in (("artifact_hash", "ef" * 32), ("destination", "https://example.org/other"),
                               ("publication_id", "jhr-002"), ("source_revision", "manuscript-v7")):
                changed = deepcopy(packet)
                changed["channels"][0]["delivery"][key] = value
                with self.subTest(state=state, key=key):
                    item = (await self.reconcile(changed))["reconciliation"]["channels"][0]
                    self.assertEqual(item["delivery_status"], "unknown")
                    self.assertEqual(item["next_action"], "READBACK_EXISTING_NO_REPOST")
            if state == "live":
                delivery["permalink"] = None
            else:
                delivery["private_queue_checked"] = False
            self.assertEqual((await self.reconcile(packet))["reconciliation"]["channels"][0]["delivery_status"], "unknown")
        for key, value in (("platform", "reddit"), ("source_revision", "manuscript-v7"), ("source_hash", "ef" * 32)):
            packet = publication_packet()
            packet["channels"][0]["approval"][key] = value
            with self.subTest(approval=key):
                item = (await self.reconcile(packet))["reconciliation"]["channels"][0]
                self.assertFalse(item["artifact_approval_matches"])
                self.assertEqual(item["next_action"], "REVIEW_ARTIFACT_AND_DESTINATION_APPROVAL")

    async def test_amplification_waits_for_requested_editions_and_stale_unknown_send_never_retries(self):
        packet = publication_packet()
        for platform, locale in (("substack", "en"), ("reddit", "ja")):
            channel = deepcopy(packet["channels"][0])
            channel.update(platform=platform, locale=locale)
            channel["approval"].update(platform=platform, locale=locale)
            packet["channels"].append(channel)
        report = (await self.reconcile(packet))["reconciliation"]
        self.assertTrue(report["amplification"]["website_prerequisites_complete"])
        self.assertFalse(report["amplification"]["evidence_complete"])
        for channel in packet["channels"]:
            channel["delivery"].update(state="live", permalink="https://example.org/articles/existing",
                                       artifact_hash=channel["artifact_hash"])
        report = (await self.reconcile(packet))["reconciliation"]
        self.assertTrue(report["amplification"]["evidence_complete"])
        self.assertFalse(report["execution_admitted"])
        packet["channels"][0]["delivery"].update(state="submitted_unknown", permalink=None,
                                                  observed_at="2026-10-01T00:00:00Z")
        self.assertEqual((await self.reconcile(packet))["reconciliation"]["channels"][0]["next_action"], "READBACK_ONLY")

    async def test_reconcile_real_route_has_no_environment_file_network_or_process_effects(self):
        packet = publication_packet()
        def denied(*args, **kwargs):
            raise AssertionError("unexpected reconciliation effect")
        with patch("os.getenv", denied), patch("builtins.open", denied), \
                patch("pathlib.Path.read_text", denied), patch("socket.create_connection", denied), \
                patch("subprocess.Popen", denied):
            report = (await self.reconcile(packet))["reconciliation"]
        self.assertFalse(report["api_called"])
        self.assertFalse(report["model_called"])
        self.assertFalse(report["storage_written"])

    async def test_detached_memory_retains_receipt_age_ownership_and_changes_review_revision(self):
        packet = publication_packet()
        packet["channels"][0]["delivery"].update(private_queue_checked=False,
                                                  observed_at="2026-10-01T00:00:00Z")
        first = (await self.reconcile(packet))["reconciliation"]
        memory = first["memory_projection"]
        self.assertEqual(memory["audit_at"], packet["audit_at"])
        item = memory["channel_work"][0]
        self.assertEqual(item["owner"], "UNASSIGNED")
        self.assertIn("receipt_freshness", item["missing"])
        self.assertIn("private_queue_coverage", item["missing"])
        self.assertEqual(item["receipt_envelope"]["delivery"], packet["channels"][0]["delivery"])
        self.assertEqual(item["receipt_envelope"]["approval"], packet["channels"][0]["approval"])
        packet["channels"][0]["delivery"]["evidence_ref"] = "https://example.org/receipts/different"
        second = (await self.reconcile(packet))["reconciliation"]
        self.assertNotEqual(first["review_revision"], second["review_revision"])

    async def test_strict_reconcile_route_rejects_authority_bad_json_and_wrong_shapes(self):
        for params in ({"dry_run": "false"}, {"approved": "true"}, {"packet": "{"},
                       {"packet": '{"x":1,"x":2}'}, {"packet": "null"},
                       {"packet": "x" * 65537}, {"brief": "private"},
                       {"action": "publish"}, {"action": "schedule"}):
            with self.subTest(params=params):
                result = await self.reconcile(publication_packet(), **params)
                self.assertEqual(result["status"], "rejected")
                self.assertFalse(result["publication_ready"])
        for change in (lambda p: p.update(approved=True),
                       lambda p: p["channels"].append(deepcopy(p["channels"][0])),
                       lambda p: p["channels"][0].update(platform="x"),
                       lambda p: p["website"].update(url="https://user@example.org/private"),
                       lambda p: p["website"]["observation"].update(observed_at="today"),
                       lambda p: p["archive"].update(path="../private")):
            packet = publication_packet()
            change(packet)
            with self.subTest(packet=packet):
                self.assertEqual((await self.reconcile(packet))["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
