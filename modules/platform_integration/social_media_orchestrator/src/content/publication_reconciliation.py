"""Effect-free publication receipt reconciliation, never execution admission.

Caller-supplied receipts remain unverified. This compiler can expose a missing
handoff; it cannot authenticate an approval, a provider result or a memory write.
"""

from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import PurePosixPath
import re
from urllib.parse import urldefrag

from .campaign_brief import CampaignBriefError, _identifier, _object, _text, _url


def _enum(value, choices):
    if not isinstance(value, str) or value not in choices:
        raise CampaignBriefError("publication_state_invalid")


def _hash(value, size=64, optional=True):
    if value is None and optional:
        return
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{%d}" % size, value):
        raise CampaignBriefError("publication_digest_invalid")


def _receipt_url(value, optional=True):
    if value is None and optional:
        return
    _text(value, 2048)
    base, fragment = urldefrag(value)
    _url(base)  # Preserve the existing strict source URL policy unchanged.
    if fragment and not re.fullmatch(r"[A-Za-z0-9_.~:/=-]{1,256}", fragment):
        raise CampaignBriefError("publication_fragment_invalid")


def _time(value, optional=True):
    if value is None and optional:
        return None
    _text(value, 64)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.utcoffset() is None:
            raise ValueError
        return parsed
    except ValueError as exc:
        raise CampaignBriefError("publication_time_invalid") from exc


def _approval(value, channel=False):
    fields = ("state", "content_hash", "receipt_ref")
    _object(value, fields + (("destination", "locale", "platform", "source_revision", "source_hash") if channel else ()))
    _enum(value["state"], ("unknown", "unapproved", "approved", "revoked"))
    _hash(value["content_hash"])
    _receipt_url(value["receipt_ref"])
    if channel:
        _receipt_url(value["destination"])
        if value["locale"] is not None:
            _text(value["locale"], 16)
        if value["platform"] is not None:
            _enum(value["platform"], ("linkedin", "substack", "reddit"))
        if value["source_revision"] is not None:
            _text(value["source_revision"], 128)
        _hash(value["source_hash"])


def _website(value):
    _object(value, ("url", "source_hash", "deployment", "observation"))
    _receipt_url(value["url"], optional=False)
    _hash(value["source_hash"])
    deploy, obs = value["deployment"], value["observation"]
    _object(deploy, ("state", "source_revision", "receipt_ref"))
    _enum(deploy["state"], ("unknown", "saved", "blocked", "succeeded"))
    if deploy["source_revision"] is not None:
        _text(deploy["source_revision"], 128)
    _receipt_url(deploy["receipt_ref"])
    _object(obs, ("state", "url", "publication_id", "source_revision", "content_hash",
                  "observed_at", "evidence_ref"))
    _enum(obs["state"], ("unknown", "absent", "present"))
    _receipt_url(obs["url"])
    if obs["publication_id"] is not None:
        _identifier(obs["publication_id"])
    if obs["source_revision"] is not None:
        _text(obs["source_revision"], 128)
    _hash(obs["content_hash"])
    _time(obs["observed_at"])
    _receipt_url(obs["evidence_ref"])


def _channels(values):
    if not isinstance(values, list) or not 1 <= len(values) <= 12:
        raise CampaignBriefError("publication_channels_invalid")
    seen = set()
    for channel in values:
        _object(channel, ("platform", "locale", "destination", "artifact_hash",
                          "source_revision", "source_hash", "approval", "delivery"))
        _enum(channel["platform"], ("linkedin", "substack", "reddit"))
        _text(channel["locale"], 16)
        if not re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z]{2,8})?", channel["locale"]):
            raise CampaignBriefError("publication_locale_invalid")
        _receipt_url(channel["destination"])
        key = (channel["platform"], channel["locale"], channel["destination"])
        if key in seen:
            raise CampaignBriefError("publication_channel_duplicate")
        seen.add(key)
        _hash(channel["artifact_hash"])
        _hash(channel["source_hash"])
        if channel["source_revision"] is not None:
            _text(channel["source_revision"], 128)
        _approval(channel["approval"], channel=True)
        delivery = channel["delivery"]
        _object(delivery, ("state", "permalink", "artifact_hash", "observed_at",
                           "evidence_ref", "private_queue_checked", "destination", "publication_id", "source_revision"))
        _enum(delivery["state"], ("unknown", "not_placed", "draft", "scheduled", "live",
                                  "submitted_unknown"))
        _receipt_url(delivery["permalink"])
        _receipt_url(delivery["destination"])
        if delivery["publication_id"] is not None:
            _identifier(delivery["publication_id"])
        if delivery["source_revision"] is not None:
            _text(delivery["source_revision"], 128)
        _hash(delivery["artifact_hash"])
        _time(delivery["observed_at"])
        _receipt_url(delivery["evidence_ref"])
        if type(delivery["private_queue_checked"]) is not bool:
            raise CampaignBriefError("publication_queue_coverage_invalid")


def _validate(packet):
    _object(packet, ("schema_version", "foundup_id", "publication_id", "audit_at",
                     "source", "archive", "website", "channels", "open_work"))
    if packet["schema_version"] != "publication_reconciliation_input.v1":
        raise CampaignBriefError("publication_schema_invalid")
    _identifier(packet["foundup_id"])
    _identifier(packet["publication_id"])
    now = _time(packet["audit_at"], optional=False)
    source, archive = packet["source"], packet["archive"]
    _object(source, ("revision", "content_hash", "approval"))
    _text(source["revision"], 128)
    _hash(source["content_hash"], optional=False)
    _approval(source["approval"])
    _object(archive, ("path", "commit_sha", "content_hash"))
    path = _text(archive["path"], 500)
    if (PurePosixPath(path).is_absolute() or "\\" in path or ":" in path
            or any(p in ("", ".", "..") for p in path.split("/"))):
        raise CampaignBriefError("publication_archive_path_invalid")
    _hash(archive["commit_sha"], size=40)
    _hash(archive["content_hash"])
    _website(packet["website"])
    _channels(packet["channels"])
    if not isinstance(packet["open_work"], list) or len(packet["open_work"]) > 30:
        raise CampaignBriefError("publication_open_work_invalid")
    for item in packet["open_work"]:
        _object(item, ("code", "owner", "next_action", "evidence_ref", "recorded_at"))
        _identifier(item["code"])
        _text(item["owner"], 128)
        _text(item["next_action"], 300)
        _receipt_url(item["evidence_ref"], optional=False)
        _time(item["recorded_at"], optional=False)
    return now


def _approved(approval, digest):
    return (digest is not None and approval["state"] == "approved"
            and approval["content_hash"] == digest and bool(approval["receipt_ref"]))


def _fresh(timestamp, now):
    observed = _time(timestamp)
    return observed is not None and timedelta(0) <= now - observed <= timedelta(hours=24)


def _website_report(packet, now):
    source, archive, website = packet["source"], packet["archive"], packet["website"]
    obs, deploy = website["observation"], website["deployment"]
    checks = {
        "source_approval": _approved(source["approval"], source["content_hash"]),
        "repository_archive": bool(archive["commit_sha"]) and archive["content_hash"] == source["content_hash"],
        "website_source": website["source_hash"] == source["content_hash"],
        "deployment": deploy["state"] == "succeeded" and bool(deploy["receipt_ref"])
                      and bool(archive["commit_sha"])
                      and deploy["source_revision"] == archive["commit_sha"],
        "exact_issue_readback": obs["state"] == "present" and obs["url"] == website["url"]
                               and obs["publication_id"] == packet["publication_id"]
                               and obs["source_revision"] == source["revision"]
                               and obs["content_hash"] == source["content_hash"]
                               and bool(obs["evidence_ref"]) and _fresh(obs["observed_at"], now),
    }
    return {"evidence_complete": all(checks.values()), "checks": checks,
            "owner": "UNASSIGNED", "receipt_envelope": deepcopy(website),
            "missing": [key for key, passed in checks.items() if not passed],
            "next_action": "REVIEW_DERIVED_EDITIONS" if all(checks.values()) else "RECONCILE_WEBSITE_RELEASE"}


def _channel_report(packet, channel, website_complete, now):
    source, delivery = packet["source"], channel["delivery"]
    identity = [packet["foundup_id"], packet["publication_id"], source["revision"],
                channel["platform"], channel["locale"], channel["destination"]]
    duplicate_key = hashlib.sha256(json.dumps(identity, ensure_ascii=True).encode()).hexdigest()
    bound = (channel["source_revision"] == source["revision"]
             and channel["source_hash"] == source["content_hash"])
    approval = (_approved(channel["approval"], channel["artifact_hash"])
                and channel["approval"]["destination"] == channel["destination"]
                and channel["approval"]["locale"] == channel["locale"]
                and channel["approval"]["platform"] == channel["platform"]
                and channel["approval"]["source_revision"] == source["revision"]
                and channel["approval"]["source_hash"] == source["content_hash"])
    observed = bool(delivery["evidence_ref"]) and _fresh(delivery["observed_at"], now)
    artifact_matches = bool(channel["artifact_hash"]) and delivery["artifact_hash"] == channel["artifact_hash"]
    destination_matches = bool(channel["destination"]) and delivery["destination"] == channel["destination"]
    identity_matches = (delivery["publication_id"] == packet["publication_id"]
                        and delivery["source_revision"] == source["revision"])
    status = delivery["state"] if observed and destination_matches and identity_matches else "unknown"
    if status in ("not_placed", "draft", "scheduled") and not delivery["private_queue_checked"]:
        status = "unknown"
    if status in ("live", "scheduled", "draft") and not artifact_matches:
        status = "unknown"
    if status == "live" and not delivery["permalink"]:
        status = "unknown"
    # A known provider reference always wins over any proposed new write.
    if delivery["permalink"]:
        action = "READBACK_EXISTING_NO_REPOST"
    elif delivery["state"] == "submitted_unknown":
        action = "READBACK_ONLY"
    elif delivery["state"] in ("live", "scheduled", "draft"):
        action = "READBACK_EXISTING_STATE"
    elif not website_complete:
        action = "RECONCILE_WEBSITE_RELEASE"
    elif status != "not_placed" or not delivery["private_queue_checked"]:
        action = "CHECK_DRAFTS_AND_SCHEDULE"
    elif not channel["destination"] or not bound or not approval:
        action = "REVIEW_ARTIFACT_AND_DESTINATION_APPROVAL"
    else:
        action = "REVIEW_DESTINATION_HANDOFF"
    checks = {"website_prerequisites": website_complete, "source_revision": bound,
              "artifact_approval": approval, "receipt_freshness": observed,
              "delivery_destination": destination_matches, "delivery_identity": identity_matches}
    if delivery["state"] in ("live", "scheduled", "draft"):
        checks["delivery_artifact"] = artifact_matches
    if delivery["state"] in ("not_placed", "scheduled", "draft"):
        checks["private_queue_coverage"] = delivery["private_queue_checked"]
    if delivery["state"] == "live":
        checks["live_permalink"] = bool(delivery["permalink"])
    return {"platform": channel["platform"], "locale": channel["locale"],
            "owner": "UNASSIGNED", "checks": checks,
            "missing": [key for key, passed in checks.items() if not passed],
            "destination": channel["destination"], "delivery_status": status,
            "receipt_envelope": {"artifact_hash": channel["artifact_hash"],
                                 "source_hash": channel["source_hash"],
                                 "source_revision": channel["source_revision"],
                                 "approval": deepcopy(channel["approval"]),
                                 "delivery": deepcopy(delivery)},
            "source_revision_matches": bound, "artifact_approval_matches": approval,
            "delivery_artifact_matches": artifact_matches,
            "delivery_destination_matches": destination_matches,
            "delivery_identity_matches": identity_matches,
            "supplied_delivery_state": delivery["state"], "delivery_status_is_verified": False,
            "next_action": action, "existing_permalink": delivery["permalink"],
            "suggested_duplicate_key": duplicate_key, "duplicate_key_is_effect_job": False,
            "execution_admitted": False}


def reconcile_publication(packet):
    """Check a supplied stage chain; return review work and proposed memory only.

    Hashes are over the same approved manuscript/artifact bytes, not raw HTML or
    a different Doc export. Collection/normalization/authenticity are upstream
    obligations. Twenty-four-hour freshness is a review bound, never a grant.
    """
    now = _validate(packet)
    website = _website_report(packet, now)
    blocked = bool(packet["open_work"])
    complete = website["evidence_complete"] and not blocked
    channels = [_channel_report(packet, c, complete, now) for c in packet["channels"]]
    reconciled_channels = all(c["delivery_status"] == "live" and c["source_revision_matches"]
                              and c["artifact_approval_matches"] for c in channels)
    amplification_complete = complete and reconciled_channels
    report = {
        "schema_version": "publication_reconciliation.v1",
        "foundup_id": packet["foundup_id"], "publication_id": packet["publication_id"],
        "source_revision": packet["source"]["revision"], "audit_at": packet["audit_at"],
        "source_receipt": deepcopy(packet["source"]),
        "status": "BLOCKED_OPEN_WORK" if blocked else ("REVIEW_REQUIRED" if complete else "BLOCKED_WEBSITE_RELEASE"),
        "evidence_status": "SUPPLIED_UNVERIFIED", "website": website, "channels": channels,
        "amplification": {"evidence_complete": amplification_complete,
                          "website_prerequisites_complete": complete,
                          "channels_reconciled": reconciled_channels,
                          "next_action": ("PREPARE_AMPLIFICATION_REVIEW" if amplification_complete else
                                          "RECONCILE_DERIVED_EDITIONS" if complete else "BLOCKED_WEBSITE_RELEASE"),
                          "canonical_url": packet["website"]["url"],
                          "requires": ["authentic_provider_readback", "exact_amplification_copy_approval", "social_dae_admission"],
                          "execution_admitted": False},
        "memory_projection": {"status": "PROPOSED_NOT_WRITTEN",
                              "foundup_id": packet["foundup_id"], "publication_id": packet["publication_id"],
                              "source_revision": packet["source"]["revision"],
                              "audit_at": packet["audit_at"],
                              "canonical_url": packet["website"]["url"],
                              "archive": deepcopy(packet["archive"]),
                              "receipt_refs": {"source_approval": packet["source"]["approval"]["receipt_ref"],
                                               "deployment": packet["website"]["deployment"]["receipt_ref"],
                                               "website_readback": packet["website"]["observation"]["evidence_ref"]},
                              "channel_work": deepcopy(channels),
                              "open_work": deepcopy(packet["open_work"]),
                              "stage_gaps": list(website["missing"]),
                              "ingestion_status": "NOT_ATTEMPTED", "authenticity": "NOT_ADMITTED"},
        "publication_ready": False, "execution_admitted": False, "publication_grant": None,
        "no_publication_performed": True, "storage_written": False,
        "api_called": False, "model_called": False,
    }
    report["review_revision"] = hashlib.sha256(json.dumps(report, ensure_ascii=True, sort_keys=True).encode()).hexdigest()
    return report
