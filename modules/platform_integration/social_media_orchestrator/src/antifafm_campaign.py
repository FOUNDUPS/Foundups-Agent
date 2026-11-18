"""Bounded AntifaFM campaign operations behind the existing SOCIAL router.

One invocation previews, reviews listener requests, or publishes one own-account
station update. OpenClaw owns invocation and cadence; this module starts no loop.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from functools import partial
from pathlib import Path
from typing import Any

from .core.x_conversation_reader import (
    ConversationReadError, provider_id, read_conversation, recent_mention_ids, verify_account,
)


class CampaignInputError(ValueError):
    """A fixed validation identifier, never an SDK or credential error string."""


STATION_URL = "https://antifafm.com/"
STATION_POST = (
    "Listen to Antifa FM at https://antifafm.com/\n\n"
    "Some songs contain strong language.\n"
    "Shared by 0102, AI assistant for UnDaoDu."
)
MODULE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = MODULE_ROOT / "config" / "antifafm_campaign.local.json"
DEFAULT_DB = MODULE_ROOT / "memory" / "orchestrator_posted_streams.db"
ACCOUNTS = {"move2japan", "foundups", "antifafm"}
ACTIONS = {"preview", "check_account", "draft_reply", "review_mentions", "publish"}
PARAMETERS = {"action", "account", "dry_run", "post_id", "limit", "job_id", "content"}


def _dry_run(value: str) -> bool:
    if value not in {"true", "false"}:
        raise CampaignInputError("dry_run_must_be_true_or_false")
    return value == "true"


def _load_settings() -> dict[str, Any]:
    path = Path(os.environ.get("ANTIFAFM_CAMPAIGN_CONFIG", str(DEFAULT_CONFIG)))
    if path.stat().st_size > 32_768:
        raise CampaignInputError("campaign_config_too_large")
    settings = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(settings, dict) or settings.get("schema") != "antifafm_campaign.v1":
        raise CampaignInputError("campaign_config_invalid")
    return settings


def _account_settings(settings: dict[str, Any], account: str) -> dict[str, Any]:
    accounts = settings.get("accounts")
    if not isinstance(accounts, dict) or not isinstance(accounts.get(account), dict):
        raise CampaignInputError("account_not_configured")
    selected = accounts[account]
    provider_id(selected.get("user_id"))
    return selected


def _build_client(selected: dict[str, Any]) -> Any:
    """Resolve names of existing host secrets; never print or save their values."""
    import tweepy

    names = selected.get("credential_env")
    fields = {"consumer_key", "consumer_secret", "access_token", "access_token_secret"}
    if not isinstance(names, dict) or set(names) != fields:
        raise CampaignInputError("credential_references_invalid")
    credentials = {}
    for field in fields:
        name = names[field]
        if not isinstance(name, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,95}", name):
            raise CampaignInputError("credential_reference_invalid")
        value = os.environ.get(name)
        if not value:
            raise CampaignInputError("account_api_credentials_missing")
        credentials[field] = value
    client = tweepy.Client(**credentials, wait_on_rate_limit=False)
    client.session.request = partial(client.session.request, timeout=20)
    return client


def _draft_one(client: Any, drafter: Any, post_id: str, account_id: str) -> dict[str, Any]:
    context = read_conversation(client, post_id, account_id)
    if not context["context_complete"]:
        return {
            "action": "review_required", "reason": "conversation_context_incomplete",
            "reply": "", "source_url": context["source_url"],
            "reply_to_id": context["post_id"], "no_publication_performed": True,
        }
    return drafter.draft_station_reply(
        context["thread_context"], context_url=context["source_url"],
        reply_to_id=context["post_id"],
        initiated_by_listener=context["initiated_by_listener"],
    )


async def execute_antifafm_campaign(
    params: dict[str, str], *, settings: dict[str, Any] | None = None,
    client: Any = None, drafter: Any = None, db_path: Path | None = None,
) -> dict[str, Any]:
    """Execute one explicit operation; dry-run defaults true and has no effects.

    Injected settings/client/drafter are host composition and offline test seams,
    never command-string parameters. Publishing replies is not supported.
    """
    base: dict[str, Any] = {"campaign": "antifafm", "no_publication_performed": True}
    try:
        if not isinstance(params, dict) or set(params) - PARAMETERS:
            raise CampaignInputError("campaign_parameter_unsupported")
        if not all(isinstance(value, str) for value in params.values()):
            raise CampaignInputError("campaign_parameter_invalid")
        action = params.get("action", "preview").lower()
        account = params.get("account", "move2japan").lower()
        dry_run = _dry_run(params.get("dry_run", "true"))
        if action not in ACTIONS or account not in ACCOUNTS:
            raise CampaignInputError("campaign_action_or_account_invalid")
        if "post_id" in params and action != "draft_reply":
            raise CampaignInputError("post_id_only_valid_for_reply_draft")
        if action == "draft_reply":
            provider_id(params.get("post_id"))
        job_id = params.get("job_id", "")
        if action == "publish" and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}", job_id):
            raise CampaignInputError("explicit_job_id_required")
        limit_text = params.get("limit", "3")
        if not re.fullmatch(r"[1-5]", limit_text):
            raise CampaignInputError("mention_limit_invalid")
        content = params.get("content", STATION_POST)
        if (not content.strip() or len(content) > 280 or "@" in content
                or STATION_URL not in content):
            raise CampaignInputError("own_post_requires_station_url_no_mentions_max_280_chars")
        base.update(action=action, account=account, dry_run=dry_run)
        if action == "publish":
            base["job_id"] = job_id
        if dry_run or action == "preview":
            return {
                **base, "success": True, "status": "preview", "content": content,
                "model_called": False, "api_called": False,
                "reply_publication_supported": False,
            }
        settings = settings if settings is not None else _load_settings()
        if action == "publish" and settings.get("enabled") is not True:
            raise CampaignInputError("campaign_publication_disabled")
        selected = _account_settings(settings, account)
        client = client if client is not None else _build_client(selected)
        account_id = provider_id(selected["user_id"])
        if action == "publish":
            from .unified_x_interface import XAccount, post_verified_x

            # Once the publishing owner is entered, absence of a receipt cannot
            # prove that the provider did not accept a write.
            base["no_publication_performed"] = None
            try:
                result = await post_verified_x(
                    content, XAccount(account), "antifafm", job_id, client=client,
                    expected_user_id=account_id, db_path=db_path or DEFAULT_DB, dry_run=False,
                )
            except Exception:
                return {**base, "success": False, "status": "outcome_unknown",
                        "error": "publication_owner_failed", "publication_verified": False}
            if result.get("status") in {"rejected", "rate_limited", "dry_run", "already_verified"}:
                base["no_publication_performed"] = True
            return {**base, **result, "publication_verified": result.get("status") in {
                "verified", "already_verified",
            }}
        identity = await asyncio.to_thread(verify_account, client, account_id)
        if action == "check_account":
            return {**base, "success": True, "status": "account_verified", **identity}
        ids = [params["post_id"]] if action == "draft_reply" else await asyncio.to_thread(
            recent_mention_ids, client, account_id, int(limit_text),
        )
        if not ids:
            return {**base, "success": True, "status": "no_mentions", "decisions": []}
        if drafter is None:
            from modules.ai_intelligence.digital_twin.src.comment_drafter import CommentDrafter

            drafter = await asyncio.to_thread(CommentDrafter.for_station)
        decisions = []
        for post_id in ids:
            try:
                decisions.append(await asyncio.to_thread(_draft_one, client, drafter, post_id, account_id))
            except Exception:
                decisions.append({
                    "action": "review_required", "reason": "context_or_model_unavailable",
                    "reply": "", "reply_to_id": post_id,
                    "source_url": f"https://x.com/i/status/{post_id}",
                    "no_publication_performed": True,
                })
        return {
            **base, "success": True, "status": "review_complete", "decisions": decisions,
            "reviewed_count": len(decisions), "reply_publication_supported": False,
        }
    except (CampaignInputError, ConversationReadError) as exc:
        # Only our typed, fixed validation identifiers cross this boundary.
        error = str(exc) if re.fullmatch(r"[a-z0-9_]+", str(exc)) else "campaign_validation_failed"
        return {**base, "success": False, "status": "blocked", "error": error}
    except FileNotFoundError:
        return {**base, "success": False, "status": "blocked", "error": "campaign_config_unavailable"}
    except Exception:
        return {**base, "success": False, "status": "blocked", "error": "campaign_dependency_unavailable"}
