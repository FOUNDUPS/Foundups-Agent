"""Effect-free petition intake and campaign planning; never a publication grant."""

from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import unquote, urlsplit, urlunsplit


PARAMETERS = {"action", "dry_run", "petition_url", "campaign_id", "title", "platforms"}
PLATFORMS = {"x", "linkedin", "facebook", "youtube"}
HOSTS = {"change.org", "www.change.org", "chng.it", "actionnetwork.org", "www.actionnetwork.org"}
STEPS = (
    ("verify_petition", "Read the public petition; verify its organizer, title and destination."),
    ("verify_evidence", "Reconcile campaign claims, sources, corrections and institutional targets."),
    ("bind_accounts", "Resolve existing authorized provider account IDs and applicable policy."),
    ("draft_package", "Prepare broad public posts and optional assets from verified campaign evidence."),
    ("admit_work", "Bind exact copy, revision, account, budget and stable effect identity through existing owners."),
    ("publish_verify", "Use qualified transports and reconcile provider readback before any retry."),
    ("review_outcomes", "Record verified responses and aggregate outcomes; respect supporter preferences."),
)


class PetitionInputError(ValueError):
    """Fixed input diagnostic without echoing private or untrusted values."""


def _petition_destination(value: str) -> tuple[str, str, bool]:
    if len(value) > 2048 or any(c.isspace() or ord(c) < 32 for c in value) or "\\" in value:
        raise PetitionInputError("petition_url_invalid")
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or parsed.hostname not in HOSTS
                or parsed.username is not None or parsed.password is not None
                or parsed.port is not None):
            raise PetitionInputError("petition_url_not_supported")
    except ValueError as exc:
        raise PetitionInputError("petition_url_not_supported") from exc
    decoded = unquote(parsed.path)
    if ("%" in decoded or "\\" in decoded or "?" in decoded or "#" in decoded
            or any(c.isspace() or ord(c) < 32 for c in decoded)
            or any(part in {".", ".."} for part in decoded.split("/"))):
        raise PetitionInputError("petition_url_path_invalid")
    host = parsed.hostname
    platform = "change_org" if host in {"change.org", "www.change.org", "chng.it"} else "action_network"
    short_link = host == "chng.it"
    prefix = "/" if short_link else "/p/" if platform == "change_org" else "/petitions/"
    slug = decoded[len(prefix):].rstrip("/") if decoded.startswith(prefix) else ""
    if not slug or "/" in slug or len(slug) > 600:
        raise PetitionInputError("petition_public_link_required")
    host = "chng.it" if short_link else "www.change.org" if platform == "change_org" else "actionnetwork.org"
    # Tracking/query fragments are deliberately excluded from plans and IDs.
    return urlunsplit(("https", host, parsed.path.rstrip("/"), "", "")), platform, short_link


def _platform_plan(names: list[str]) -> list[dict]:
    return [{
        "platform": name, "account_id": None, "enabled": False,
        "status": "account_and_transport_qualification_required",
        "publication_grant": None,
    } for name in names]


def _validated_input(params: dict[str, str]) -> tuple:
    if not isinstance(params, dict) or set(params) - PARAMETERS:
        raise PetitionInputError("petition_parameter_unsupported")
    if not all(isinstance(v, str) for v in params.values()):
        raise PetitionInputError("petition_parameter_invalid")
    if params.get("action", "preview") not in {"preview", "plan"}:
        raise PetitionInputError("petition_execution_not_implemented")
    if params.get("dry_run", "true") != "true":
        raise PetitionInputError("petition_execution_not_implemented")
    campaign_id = params.get("campaign_id", "")
    if campaign_id and not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", campaign_id):
        raise PetitionInputError("petition_campaign_id_invalid")
    title = params.get("title", "").strip()
    if len(title) > 180 or any(ord(c) < 32 for c in title):
        raise PetitionInputError("petition_title_invalid")
    names = params.get("platforms", "x,linkedin").split(",")
    if not names or len(names) != len(set(names)) or set(names) - PLATFORMS:
        raise PetitionInputError("petition_platform_invalid")
    raw_url = params.get("petition_url", "")
    url, platform, short_link = _petition_destination(raw_url) if raw_url else (None, "change_org", False)
    return campaign_id, title, names, url, platform, short_link


async def execute_petition_campaign(params: dict[str, str]) -> dict:
    """Return a deterministic plan without storage, network, browser or model use."""
    base = {
        "campaign": "petition", "scope": "plan_only",
        "no_publication_performed": True, "api_called": False,
        "model_called": False, "storage_written": False,
        "publication_ready": False, "execution_supported": False,
        "authority": "not_evaluated_plan_only",
    }
    try:
        campaign_id, title, names, url, platform, short_link = _validated_input(params)
        brief = {"title": title or None, "cta": {"primary": "sign_petition", "destination": url},
                 "platform_matrix": _platform_plan(names)}
        digest = hashlib.sha256(json.dumps(brief, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return {
            **base, "success": True, "schema_version": "petition_campaign_plan.v1",
            "status": "intake_ready" if url else "awaiting_petition_url",
            "campaign_id": campaign_id or ("petition_" + hashlib.sha256(url.encode()).hexdigest()[:12] if url else None),
            "plan_revision": digest[:12], "petition_platform": platform,
            "petition_verified": False, "short_link_resolution_required": short_link,
            "account_setup": "external_petition_adoption" if url else "principal_creates_petition",
            "brief": brief,
            "steps": [{"step": name, "status": "pending", "instruction": text} for name, text in STEPS],
            "blockers": ["public_petition_and_sources_not_verified", "provider_accounts_not_bound",
                         "publication_authority_not_bound", "petition_publication_transport_not_qualified"]
                        if url else ["petition_url_missing"],
        }
    except PetitionInputError as exc:
        return {**base, "success": False, "status": "rejected", "error": str(exc)}
