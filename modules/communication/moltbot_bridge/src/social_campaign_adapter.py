"""
Social campaign adapter for OpenClaw/IronClaw SOCIAL intent routing.

Command format (strict):
  social campaign <campaign_name> key=value key2="value 2"

Supported campaigns:
  research_x_to_ln_group
  antifafm

Example:
  social campaign research_x_to_ln_group \
    content="new research summary" \
    ln_title="foundups research update" \
    dry_run=true
"""

from __future__ import annotations

import json
import shlex
from typing import Any, Dict, Optional, Tuple


SUPPORTED_CAMPAIGNS = {
    "research_x_to_ln_group",
    "antifafm",
}

CAMPAIGN_ALIASES = {
    "research_to_ln_group": "research_x_to_ln_group",
    "research_to_ln": "research_x_to_ln_group",
}


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_campaign_command(message: str) -> Optional[Tuple[str, Dict[str, str]]]:
    text = (message or "").strip()
    if not text:
        return None

    lowered = text.lower()
    prefix = "social campaign "
    if not lowered.startswith(prefix):
        return None

    remainder = text[len(prefix) :].strip()
    if not remainder:
        return None

    try:
        parts = shlex.split(remainder)
    except ValueError:
        if remainder.split(None, 1)[0].lower() == "antifafm":
            return "antifafm", {"_invalid_command": "true"}
        raise
    if not parts:
        return None

    raw_campaign = parts[0].strip().lower()
    campaign = CAMPAIGN_ALIASES.get(raw_campaign, raw_campaign)
    if campaign not in SUPPORTED_CAMPAIGNS:
        return campaign, {}

    params: Dict[str, str] = {}
    for token in parts[1:]:
        if "=" not in token:
            if campaign == "antifafm":
                return campaign, {"_invalid_command": "true"}
            continue
        key, value = token.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if campaign == "antifafm" and (not key or key in params):
            return campaign, {"_invalid_command": "true"}
        if key:
            params[key] = value
    return campaign, params


async def execute_social_campaign(campaign: str, params: Dict[str, str]) -> Dict[str, Any]:
    if campaign == "antifafm":
        from modules.platform_integration.social_media_orchestrator.src.antifafm_campaign import (
            execute_antifafm_campaign,
        )

        return await execute_antifafm_campaign(params)

    if campaign != "research_x_to_ln_group":
        return {"success": False, "campaign": campaign, "error": "unsupported campaign"}

    from .linkedin_social_adapter import execute_linkedin_action
    from .x_social_adapter import execute_x_action

    research_content = params.get("content", params.get("text", params.get("research", ""))).strip()
    if not research_content:
        return {
            "success": False,
            "campaign": campaign,
            "error": "missing content/text/research parameter",
        }

    global_dry_run = params.get("dry_run", "true")
    x_dry_run = _truthy(params.get("x_dry_run", global_dry_run))
    ln_dry_run = _truthy(params.get("ln_dry_run", global_dry_run))

    x_params = {
        "content": research_content,
        "profile": params.get("x_profile", "x_foundups"),
        "dry_run": "true" if x_dry_run else "false",
    }
    image_path = params.get("x_image_path", "").strip()
    if image_path:
        x_params["image_path"] = image_path

    ln_params = {
        "title": params.get("ln_title", "foundups research update"),
        "url": params.get("ln_url", "https://foundups.com/litepaper"),
        "summary": params.get("ln_summary", research_content[:450]),
        "source": params.get("ln_source", "foundups"),
        "dry_run": "true" if ln_dry_run else "false",
    }

    x_result = await execute_x_action("post", x_params)
    ln_result = await execute_linkedin_action("group_post", ln_params)

    success = bool(x_result.get("success", False)) and bool(ln_result.get("success", False))
    return {
        "success": success,
        "campaign": campaign,
        "dry_run": {"x": x_dry_run, "linkedin": ln_dry_run},
        "steps": {
            "x_post": x_result,
            "linkedin_group_post": ln_result,
        },
    }


async def handle_social_campaign_intent(message: str, sender: str = "") -> Optional[str]:
    """
    Handle SOCIAL intent if message is explicit social campaign command.
    Returns formatted response text or None when message is not a campaign command.
    """
    parsed = _parse_campaign_command(message)
    if parsed is None:
        return None

    campaign, params = parsed
    if campaign not in SUPPORTED_CAMPAIGNS:
        return (
            "Social campaign not recognized.\n"
            f"Requested: {campaign}\n"
            f"Supported: {', '.join(sorted(SUPPORTED_CAMPAIGNS))}\n"
            "Format: social campaign <campaign_name> key=value"
        )

    try:
        result = await execute_social_campaign(campaign, params)
        label = "result" if campaign == "antifafm" else "executed"
        return (
            f"Social campaign {label} for {sender or 'unknown_sender'}:\n"
            f"{json.dumps(result, indent=2, ensure_ascii=False)}"
        )
    except Exception as exc:
        return f"Social campaign execution error: {exc}"
