"""Bounded, effect-free editorial iterations under the existing content owner.

Review assertions are supplied evidence, not authenticated authority or proof
of factual accuracy. This module never invokes models, publishes or learns.
"""

from copy import deepcopy
import re

from .campaign_brief import CampaignBriefError, _identifier, _object, _text
from .campaign_planner import _digest


LENSES = {
    "grounding": "Check each factual claim against sources; separate inference, unknowns and allegations.",
    "audience": "Can the intended reader understand the purpose, context and next step?",
    "writing": "Check structure, voice, repetition, precise attribution and native rendered formatting.",
    "imagery": "Inspect actual images and rendered crops; check relevance, provenance, captions and alt text.",
}
MAX_ROUNDS = 3
CONTRACT_VERSION = "social_editorial_cycle.v1"


def _contract_digest():
    return _digest({"lenses": LENSES, "max_rounds": MAX_ROUNDS, "schema": CONTRACT_VERSION})


def _body(value):
    if (not isinstance(value, str) or not value.strip() or len(value) > 30000
            or any((ord(c) < 32 and c not in "\n\t") or ord(c) == 127
                   or 0xD800 <= ord(c) <= 0xDFFF for c in value)):
        raise CampaignBriefError("editorial_body_invalid")


def _assets(values, source_ids):
    if not isinstance(values, list) or len(values) > 12:
        raise CampaignBriefError("editorial_assets_invalid")
    seen = set()
    for asset in values:
        _object(asset, ("asset_id", "sha256", "caption", "alt_text", "source_ids", "kind"))
        key = _identifier(asset["asset_id"])
        if key in seen:
            raise CampaignBriefError("editorial_duplicate_asset")
        seen.add(key)
        if not isinstance(asset["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", asset["sha256"]):
            raise CampaignBriefError("editorial_asset_digest_invalid")
        _text(asset["caption"], 1000)
        _text(asset["alt_text"], 1000)
        if asset["kind"] not in ("original", "reused", "illustration"):
            raise CampaignBriefError("editorial_asset_kind_invalid")
        ids = asset["source_ids"]
        if (not isinstance(ids, list) or len(ids) > 20
                or any(not isinstance(key, str) or key not in source_ids for key in ids)
                or len(set(ids)) != len(ids)):
            raise CampaignBriefError("editorial_asset_sources_invalid")


def _reviews(values, revision, author_id):
    if not isinstance(values, list) or len(values) > len(LENSES):
        raise CampaignBriefError("editorial_reviews_invalid")
    by_lens = {}
    for review in values:
        _object(review, ("lens", "revision", "reviewer_id", "decision", "notes",
                         "evidence_refs", "provider", "model"))
        lens = review["lens"]
        if not isinstance(lens, str) or lens not in LENSES or lens in by_lens:
            raise CampaignBriefError("editorial_lens_invalid")
        _identifier(review["reviewer_id"])
        if review["reviewer_id"] == author_id:
            raise CampaignBriefError("editorial_self_review")
        if review["revision"] != revision:
            raise CampaignBriefError("editorial_stale_review")
        if review["decision"] not in ("pass", "revise", "unknown"):
            raise CampaignBriefError("editorial_decision_invalid")
        _text(review["notes"], 2000)
        _text(review["provider"], 100)
        _text(review["model"], 160)
        refs = review["evidence_refs"]
        if not isinstance(refs, list) or not 1 <= len(refs) <= 20:
            raise CampaignBriefError("editorial_review_evidence_missing")
        for ref in refs:
            _text(ref, 500)
        by_lens[lens] = review
    return by_lens


def evaluate_editorial_cycle(brief, topic_id, rounds):
    """Evaluate up to three supplied draft/review rounds; perform no effects.

    Submit an empty reviews list first to obtain the exact revision for review.
    Resubmit that round with bound review assertions, then append a revised
    round if changes are requested. No callback/provider execution is hidden here.
    """
    from .content_orchestrator import prepare_campaign

    package = prepare_campaign(brief)
    _identifier(topic_id)
    topic = next((item for item in package["items"] if item["topic_id"] == topic_id), None)
    if topic is None:
        raise CampaignBriefError("editorial_topic_not_in_package")
    if not isinstance(rounds, list) or not 1 <= len(rounds) <= MAX_ROUNDS:
        raise CampaignBriefError("editorial_round_limit")
    history, previous_revision, prior_status = [], None, None
    for index, supplied in enumerate(rounds, 1):
        if prior_status != "revision_requested" and index > 1:
            raise CampaignBriefError("editorial_previous_review_required")
        _object(supplied, ("author_id", "content", "assets", "reviews"))
        _identifier(supplied["author_id"])
        _body(supplied["content"])
        _assets(supplied["assets"], set(topic["source_ids"]))
        artifact = {"package_revision": package["package_revision"], "topic_id": topic_id,
                    "review_contract_digest": _contract_digest(),
                    "iteration": index, "previous_revision": previous_revision,
                    "author_id": supplied["author_id"], "content": supplied["content"],
                    "assets": deepcopy(supplied["assets"])}
        if _digest([artifact["content"], artifact["assets"]]) in {item["content_digest"] for item in history}:
            raise CampaignBriefError("editorial_no_change")
        revision = _digest(artifact)
        reviews = _reviews(supplied["reviews"], revision, supplied["author_id"])
        missing = [lens for lens in LENSES if lens not in reviews]
        needs_revision = any(item["decision"] == "revise" for item in reviews.values())
        unknown = any(item["decision"] == "unknown" for item in reviews.values())
        if missing or unknown:
            status = "awaiting_review"
        elif needs_revision:
            status = "iteration_limit" if index == MAX_ROUNDS else "revision_requested"
        else:
            status = "awaiting_principal_review"
        history.append({"iteration": index, "revision": revision,
                        "content_digest": _digest([artifact["content"], artifact["assets"]]),
                        "status": status, "reviews": deepcopy(supplied["reviews"])})
        previous_revision, prior_status = revision, status
    return {"schema_version": CONTRACT_VERSION, "campaign_id": package["campaign_id"],
            "foundup_id": package["brand"]["foundup_id"], "topic_id": topic_id,
            "package_revision": package["package_revision"], "revision": revision,
            "artifact": artifact, "audience": package["audience"],
            "brand": deepcopy(package["brand"]), "objective": package["objective"],
            "cta": deepcopy(package["cta"]), "title": topic["title"],
            "sources": [deepcopy(s) for s in package["sources"] if s["source_id"] in topic["source_ids"]],
            "status": status, "history": history, "max_rounds": MAX_ROUNDS,
            "review_requests": [{"lens": lens, "revision": revision, "instruction": instruction}
                                for lens, instruction in LENSES.items()],
            "review_evidence_status": "supplied_unverified_identity_and_assertions",
            "publication_ready": False, "scheduled": False, "model_called": False,
            "storage_written": False, "rsi_transfer_demonstrated": False,
            "measurement": deepcopy(package["measurement"])}


def editorial_benchmark_task(brief, topic_id, rounds, *, golden):
    """Project a reviewed-input fixture into the existing AI Gateway harness.

    This constructs a task only, never benchmark evidence or a promotion receipt.
    Freeze independently reviewed held-out expectations before calling a runner.
    """
    from modules.ai_intelligence.ai_gateway.src.model_combination_benchmark_harness import ModelBenchmarkTask

    _object(golden, ("expected_output_digest", "fixture_ref"))
    if (not isinstance(golden["expected_output_digest"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", golden["expected_output_digest"])):
        raise CampaignBriefError("editorial_golden_digest_invalid")
    _text(golden["fixture_ref"], 500)
    result = evaluate_editorial_cycle(brief, topic_id, rounds)
    return ModelBenchmarkTask(
        task_id=result["foundup_id"] + ":" + result["campaign_id"] + ":" + topic_id,
        task_family="editorial_review", prompt_digest=result["revision"],
        expected_output_digest=golden["expected_output_digest"],
        verifier_contract_digest=_contract_digest(),
        metadata={"campaign_id": result["campaign_id"], "foundup_id": result["foundup_id"],
                  "golden_fixture_ref": golden["fixture_ref"],
                  "evidence_status": "supplied_fixture_not_benchmark_execution"},
    )
