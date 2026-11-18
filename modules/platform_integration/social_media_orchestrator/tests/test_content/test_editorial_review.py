"""Offline editorial contracts; review fixtures do not establish model quality."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from modules.platform_integration.social_media_orchestrator.src.content.editorial_review import (
    LENSES, editorial_benchmark_task, evaluate_editorial_cycle,
)
from modules.platform_integration.social_media_orchestrator.src.content.campaign_brief import CampaignBriefError
from modules.platform_integration.social_media_orchestrator.tests.test_content.test_content_orchestrator import sample_brief


def draft(text="A source-backed explanation.\n\nRead the guide."):
    return {"author_id": "writer", "content": text, "assets": [], "reviews": []}


def reviewed(brief, rounds, decision="pass"):
    result = evaluate_editorial_cycle(brief, "release", rounds)
    rounds[-1]["reviews"] = [
        {"lens": lens, "revision": result["revision"], "reviewer_id": "auditor",
         "decision": decision, "notes": "Synthetic review for contract testing only.",
         "evidence_refs": ["fixture:source-and-render"], "provider": "test", "model": "fixture"}
        for lens in LENSES]
    return rounds


class EditorialReviewTests(unittest.TestCase):
    def setUp(self):
        self.brief = sample_brief()

    def test_requests_bind_all_lenses_without_effects(self):
        rounds = [draft()]
        original = deepcopy(rounds)
        result = evaluate_editorial_cycle(self.brief, "release", rounds)
        self.assertEqual(result["status"], "awaiting_review")
        self.assertEqual({r["lens"] for r in result["review_requests"]}, set(LENSES))
        self.assertEqual({r["revision"] for r in result["review_requests"]}, {result["revision"]})
        for field in ("publication_ready", "scheduled", "model_called", "storage_written", "rsi_transfer_demonstrated"):
            self.assertIs(result[field], False)
        self.assertEqual(rounds, original)
        result["artifact"]["assets"].append({})
        self.assertEqual(rounds, original)

    def test_all_pass_never_authorizes_publication(self):
        result = evaluate_editorial_cycle(self.brief, "release", reviewed(self.brief, [draft()]))
        self.assertEqual(result["status"], "awaiting_principal_review")
        self.assertFalse(result["publication_ready"])

    def test_stale_content_and_brief_rejected(self):
        rounds = reviewed(self.brief, [draft()])
        for change in ("content", "audience", "source"):
            with self.subTest(change=change):
                altered, brief = deepcopy(rounds), deepcopy(self.brief)
                if change == "content":
                    altered[0]["content"] += " Changed."
                elif change == "audience":
                    brief["audience"] = "Another audience"
                else:
                    brief["sources"][0]["excerpt"] = "Changed source evidence"
                with self.assertRaisesRegex(CampaignBriefError, "stale_review"):
                    evaluate_editorial_cycle(brief, "release", altered)

    def test_independent_reviewer_and_complete_lenses(self):
        for mutation, error in (("self", "self_review"), ("duplicate", "lens_invalid"),
                                ("evidence", "evidence_missing"), ("authority", "object_invalid")):
            with self.subTest(mutation=mutation):
                rounds = reviewed(self.brief, [draft()])
                item = rounds[0]["reviews"][0]
                if mutation == "self":
                    item["reviewer_id"] = "writer"
                elif mutation == "duplicate":
                    rounds[0]["reviews"][1] = deepcopy(item)
                elif mutation == "evidence":
                    item["evidence_refs"] = []
                else:
                    item["approved"] = True
                with self.assertRaisesRegex(CampaignBriefError, error):
                    evaluate_editorial_cycle(self.brief, "release", rounds)

    def test_missing_or_unknown_review_blocks_next_round(self):
        for decision in ("unknown", "missing"):
            with self.subTest(decision=decision):
                rounds = reviewed(self.brief, [draft()])
                if decision == "missing":
                    rounds[0]["reviews"].pop()
                else:
                    rounds[0]["reviews"][0]["decision"] = "unknown"
                self.assertEqual(evaluate_editorial_cycle(self.brief, "release", rounds)["status"], "awaiting_review")
                with self.assertRaisesRegex(CampaignBriefError, "previous_review_required"):
                    evaluate_editorial_cycle(self.brief, "release", rounds + [draft("Revised text")])

    def test_revision_loop_and_limit(self):
        rounds = reviewed(self.brief, [draft()], "revise")
        for text in ("Second version", "Third version"):
            rounds.append(draft(text))
            reviewed(self.brief, rounds, "revise")
        result = evaluate_editorial_cycle(self.brief, "release", rounds)
        self.assertEqual(result["status"], "iteration_limit")
        self.assertEqual(len({r["revision"] for r in result["history"]}), 3)
        with self.assertRaisesRegex(CampaignBriefError, "round_limit"):
            evaluate_editorial_cycle(self.brief, "release", rounds + [draft("Fourth")])

    def test_unchanged_revision_rejected(self):
        rounds = reviewed(self.brief, [draft()], "revise")
        with self.assertRaisesRegex(CampaignBriefError, "no_change"):
            evaluate_editorial_cycle(self.brief, "release", rounds + [draft()])

    def test_oscillation_rejected(self):
        rounds = reviewed(self.brief, [draft()], "revise")
        rounds.append(draft("Second version"))
        reviewed(self.brief, rounds, "revise")
        with self.assertRaisesRegex(CampaignBriefError, "no_change"):
            evaluate_editorial_cycle(self.brief, "release", rounds + [draft()])

    def test_no_host_effects(self):
        with patch("builtins.open", side_effect=AssertionError("file effect")), \
                patch("socket.socket", side_effect=AssertionError("network effect")), \
                patch("subprocess.Popen", side_effect=AssertionError("process effect")), \
                patch("os.getenv", side_effect=AssertionError("environment read")):
            result = evaluate_editorial_cycle(self.brief, "release", [draft()])
        self.assertEqual(result["status"], "awaiting_review")

    def test_assets_and_caption_bound_to_revision(self):
        rounds = [draft()]
        rounds[0]["assets"] = [{"asset_id": "cover", "sha256": "a" * 64,
            "caption": "Illustration, not documentary evidence", "alt_text": "Two figures",
            "source_ids": ["release"], "kind": "illustration"}]
        reviewed(self.brief, rounds)
        rounds[0]["assets"][0]["caption"] = "Changed meaning"
        with self.assertRaisesRegex(CampaignBriefError, "stale_review"):
            evaluate_editorial_cycle(self.brief, "release", rounds)
        rounds[0]["reviews"] = []
        rounds[0]["assets"][0]["source_ids"] = ["guide"]
        with self.assertRaisesRegex(CampaignBriefError, "asset_sources_invalid"):
            evaluate_editorial_cycle(self.brief, "release", rounds)

    def test_strict_inputs(self):
        for value in (None, [], [draft()] * 4):
            with self.subTest(value=repr(value)[:20]), self.assertRaises(CampaignBriefError):
                evaluate_editorial_cycle(self.brief, "release", value)
        for content in (True, "", "x" * 30001, "bad\x00", "bad\ud800"):
            with self.subTest(content=repr(content)[:20]), self.assertRaises(CampaignBriefError):
                evaluate_editorial_cycle(self.brief, "release", [draft(content)])
        with self.assertRaisesRegex(CampaignBriefError, "topic_not_in_package"):
            evaluate_editorial_cycle(self.brief, "absent", [draft()])

    def test_existing_benchmark_projection_is_not_execution(self):
        golden = {"expected_output_digest": "b" * 64, "fixture_ref": "fixture:independent-golden"}
        task = editorial_benchmark_task(self.brief, "release", reviewed(self.brief, [draft()]), golden=golden)
        self.assertEqual(task.task_family, "editorial_review")
        self.assertEqual(task.metadata["evidence_status"], "supplied_fixture_not_benchmark_execution")
        self.assertEqual(len(task.to_dict()["prompt_digest"]), 64)
        pending = editorial_benchmark_task(self.brief, "release", [draft()], golden=golden)
        self.assertEqual(task.expected_output_digest, pending.expected_output_digest)
        other = deepcopy(self.brief)
        other["campaign_id"] = "another_campaign"
        alternate = editorial_benchmark_task(other, "release", [draft()], golden=golden)
        self.assertNotEqual(task.task_id, alternate.task_id)
        for invalid in ({}, {"expected_output_digest": "invalid", "fixture_ref": "ref"}, None):
            with self.subTest(invalid=invalid), self.assertRaises(CampaignBriefError):
                editorial_benchmark_task(self.brief, "release", [draft()], golden=invalid)

    def test_rubric_change_invalidates_prior_reviews(self):
        rounds = reviewed(self.brief, [draft()])
        with patch.dict(LENSES, {"writing": "A revised acceptance rubric"}):
            with self.assertRaisesRegex(CampaignBriefError, "stale_review"):
                evaluate_editorial_cycle(self.brief, "release", rounds)


if __name__ == "__main__":
    unittest.main()
