"""Editorial package compiler inside the existing content owner; no effects."""

from copy import deepcopy
from datetime import timedelta, timezone
import hashlib
import json

from .campaign_brief import CampaignBriefError, validate_brief


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=True, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _draft(topic, sources, cta, maximum):
    selected = [sources[key] for key in topic["source_ids"]]
    links = list(dict.fromkeys([source["url"] for source in selected]))
    body = topic["title"] + "\n\n" + "\n\n".join(source["excerpt"] for source in selected)
    citations = "\n".join(url for url in links if url != cta["url"])
    body += "\n\n" + cta["label"] + ": " + cta["url"]
    if citations:
        body += "\n\nSources:\n" + citations
    fits = len(body) <= maximum
    return {"status": "draft_requires_review" if fits else "shorter_copy_required",
            "content": body if fits else None, "candidate_length": len(body),
            "max_length": maximum, "length_basis": "raw_unicode_characters",
            "provider_length_validation": "pending", "truncated": False}


def _calendar_items(brief, sources, start, limits):
    items, seen = [], set()
    # Priority is supplied editorial preference, never fabricated search volume.
    topics = sorted(brief["topics"], key=lambda topic: (-topic["priority"], topic["topic_id"]))
    for topic in topics:
        fingerprint = _digest(sorted({(sources[key]["url"], sources[key]["excerpt"])
                                      for key in topic["source_ids"]}))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        slot = start.astimezone(timezone.utc) + timedelta(hours=len(items) * brief["interval_hours"])
        drafts = {platform: _draft(topic, sources, brief["cta"],
                                  limits["twitter" if platform == "x" else platform]["max_length"])
                  for platform in brief["platforms"]}
        items.append({"topic_id": topic["topic_id"], "title": topic["title"],
                      "priority": topic["priority"], "source_ids": list(topic["source_ids"]),
                      "proposed_at": slot.isoformat(), "scheduled": False, "drafts": drafts})
        if len(items) == brief["max_items"]:
            break
    return items


def prepare_content_campaign(brief, limits):
    """Compile source-preserving drafts and proposed slots from an explicit brief.

    All evidence and branding remain caller-supplied and unverified. No model,
    host configuration, registry lookup, scheduler or publisher is invoked.
    """
    sources, start = validate_brief(brief)
    try:
        items = _calendar_items(brief, sources, start, limits)
    except OverflowError as exc:
        raise CampaignBriefError("content_calendar_overflow") from exc
    package = {"schema_version": "social_content_package.v1", "campaign_id": brief["campaign_id"],
               "brand": deepcopy(brief["brand"]), "audience": brief["audience"],
               "objective": brief["objective"], "cta": deepcopy(brief["cta"]),
               "sources": deepcopy(brief["sources"]), "items": items,
               "ranking_basis": "supplied_editorial_priority_then_topic_id",
               "evidence_status": "supplied_unverified", "brand_rules_applied": False,
               "review_required": ["source_accuracy_and_rights", "brand_voice_and_locale",
                                   "platform_policy", "account_and_execution_authority"],
               "measurement": {"metrics": ["impressions", "clicks", "conversions"],
                               "join_keys": ["foundup_id", "campaign_id", "package_revision",
                                             "topic_id", "platform", "provider_account_id", "provider_post_id"],
                               "status": "provider_collection_not_connected"},
               "publication_ready": False, "publication_grant": None,
               "no_publication_performed": True, "storage_written": False,
               "api_called": False, "model_called": False}
    package["package_revision"] = _digest(package)
    return package


async def execute_content_campaign(params):
    """Existing SOCIAL command entry: a bounded inline JSON brief, no file path."""
    base = {"campaign": "content", "no_publication_performed": True,
            "publication_ready": False, "scope": "editorial_package_only"}
    try:
        if (not isinstance(params, dict) or set(params) - {"action", "dry_run", "brief"}
                or not all(isinstance(v, str) for v in params.values())):
            raise CampaignBriefError("content_parameter_invalid")
        if params.get("action", "prepare") != "prepare" or params.get("dry_run", "true") != "true":
            raise CampaignBriefError("content_execution_not_supported")
        raw = params.get("brief", "")
        if not raw or len(raw) > 65536 or len(raw.encode("utf-8")) > 65536:
            raise CampaignBriefError("content_brief_size_invalid")
        brief = json.loads(raw, object_pairs_hook=_unique_object)
        from .content_orchestrator import prepare_campaign

        package = prepare_campaign(brief)
        return {**base, "success": True, "status": "prepared", "package": package}
    except (CampaignBriefError, ValueError, RecursionError, UnicodeError) as exc:
        error = str(exc) if isinstance(exc, CampaignBriefError) else "content_json_invalid"
        return {**base, "success": False, "status": "rejected", "error": error}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CampaignBriefError("content_duplicate_json_key")
        result[key] = value
    return result
