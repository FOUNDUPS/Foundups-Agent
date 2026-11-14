"""Bounded input contract for source-backed editorial packages, not authority."""

from datetime import datetime
import ipaddress
import re
from urllib.parse import urlsplit


class CampaignBriefError(ValueError):
    """Fixed diagnostics never echo untrusted campaign content."""


def _object(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise CampaignBriefError("content_object_invalid")
    return value


def _text(value, maximum):
    if (not isinstance(value, str) or not value.strip() or len(value) > maximum
            or any(ord(c) < 32 or ord(c) == 127 or 0xD800 <= ord(c) <= 0xDFFF for c in value)):
        raise CampaignBriefError("content_text_invalid")
    return value


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value):
        raise CampaignBriefError("content_identity_invalid")
    return value


def _items(value, maximum):
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        raise CampaignBriefError("content_list_invalid")
    return value


def _url(value):
    _text(value, 2048)
    try:
        parts = urlsplit(value)
        host = parts.hostname or ""
        if (parts.scheme != "https" or not host.isascii() or "." not in host
                or parts.username is not None or parts.password is not None
                or parts.port is not None or parts.query or parts.fragment
                or "\\" in value or any(c.isspace() for c in value)
                or len(host) > 253 or not re.fullmatch(
                    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
                    r"(?:[a-z]{2,63}|xn--[a-z0-9-]{1,59})", host)
                or host.endswith((".localhost", ".local", ".internal"))):
            raise ValueError
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError
    except ValueError as exc:
        raise CampaignBriefError("content_url_invalid") from exc
    return value


def _brand(value):
    # Projection of modules/foundups/brand_context.schema.json. Full registry
    # verification remains with the registered FoundUp target verifier.
    _object(value, ("foundup_id", "canonical_brand", "default_locale", "rules", "authority_boundary"))
    _identifier(value["foundup_id"])
    if not re.fullmatch(r"[a-z0-9_]+", value["foundup_id"]):
        raise CampaignBriefError("content_foundup_identity_invalid")
    _text(value["canonical_brand"], 128)
    _text(value["default_locale"], 16)
    if len(value["default_locale"]) < 2:
        raise CampaignBriefError("content_locale_invalid")
    for rule in _items(value["rules"], 20):
        _text(rule, 300)
    if value["authority_boundary"] != "BRANDING_ONLY_NO_EXECUTION_AUTHORITY":
        raise CampaignBriefError("content_brand_authority_invalid")


def _sources(values, foundup_id):
    sources = {}
    for source in _items(values, 20):
        _object(source, ("source_id", "foundup_id", "url", "excerpt"))
        key = _identifier(source["source_id"])
        if key in sources or source["foundup_id"] != foundup_id:
            raise CampaignBriefError("content_source_scope_invalid")
        _url(source["url"])
        _text(source["excerpt"], 1200)
        sources[key] = source
    return sources


def _topics(values, sources):
    seen = set()
    for topic in _items(values, 30):
        _object(topic, ("topic_id", "title", "source_ids", "priority"))
        key = _identifier(topic["topic_id"])
        _text(topic["title"], 120)
        ids = _items(topic["source_ids"], 5)
        for source_id in ids:
            _identifier(source_id)
        if key in seen or len(ids) != len(set(ids)) or set(ids) - set(sources):
            raise CampaignBriefError("content_topic_sources_invalid")
        if type(topic["priority"]) is not int or not 1 <= topic["priority"] <= 5:
            raise CampaignBriefError("content_priority_invalid")
        seen.add(key)


def validate_brief(brief):
    """Validate supplied public evidence; do not authenticate it or fetch URLs."""
    _object(brief, ("schema_version", "campaign_id", "brand", "audience", "objective",
                    "cta", "platforms", "start_at", "interval_hours", "max_items", "sources", "topics"))
    if brief["schema_version"] != "social_content_brief.v1":
        raise CampaignBriefError("content_schema_invalid")
    _identifier(brief["campaign_id"])
    _brand(brief["brand"])
    _text(brief["audience"], 300)
    _text(brief["objective"], 300)
    _object(brief["cta"], ("label", "url"))
    _text(brief["cta"]["label"], 80)
    _url(brief["cta"]["url"])
    platforms = _items(brief["platforms"], 2)
    if any(not isinstance(p, str) or p not in {"x", "linkedin"} for p in platforms) or len(set(platforms)) != len(platforms):
        raise CampaignBriefError("content_platform_invalid")
    _text(brief["start_at"], 40)
    try:
        start = datetime.fromisoformat(brief["start_at"].replace("Z", "+00:00"))
        if start.utcoffset() is None:
            raise ValueError
    except ValueError as exc:
        raise CampaignBriefError("content_start_timezone_required") from exc
    for field, minimum, maximum in (("interval_hours", 1, 168), ("max_items", 1, 14)):
        if type(brief[field]) is not int or not minimum <= brief[field] <= maximum:
            raise CampaignBriefError("content_calendar_bound_invalid")
    sources = _sources(brief["sources"], brief["brand"]["foundup_id"])
    _topics(brief["topics"], sources)
    return sources, start
