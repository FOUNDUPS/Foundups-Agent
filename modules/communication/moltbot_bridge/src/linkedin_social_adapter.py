"""
LinkedIn social adapter for OpenClaw/IronClaw SOCIAL intent routing.

Command format (strict):
  linkedin action <action> key=value key2="value 2"
  ln action <action> key=value

Examples:
  linkedin action read_feed max_posts=5
  linkedin action connect profile_url=https://www.linkedin.com/in/jane/ dry_run=true
  linkedin action reply_post post_index=0 reply_text="great work"
  linkedin action scam_reply post_index=0 risk_reason="shortened external link"
  linkedin action group_post dry_run=true
"""

from __future__ import annotations

import asyncio
import json
import re
import shlex
from dataclasses import asdict, is_dataclass
from typing import Any, Callable, Dict, Optional, Tuple


SUPPORTED_ACTIONS = {
    "navigate_feed",
    "navigate_profile",
    "read_feed",
    "like_post",
    "reply_post",
    "like_reply",
    "scam_reply",
    "scam_scan",
    "scam_scan_reply",
    "engagement_session",
    "connect",
    "digital_twin",
    "group_post",
}

ACTION_ALIASES = {
    "reply_to_post": "reply_post",
    "like_and_reply": "like_reply",
    "reply_scam": "scam_reply",
    "scam_callout": "scam_reply",
    "scan_scam": "scam_scan",
    "scan_and_reply_scam": "scam_scan_reply",
    "run_engagement_session": "engagement_session",
    "send_connection_request": "connect",
    "run_digital_twin_flow": "digital_twin",
    "post_group": "group_post",
    "post_group_news": "group_post",
    "openclaw_group_post": "group_post",
}

_NATURAL_EXECUTE_TOKENS = {
    "post it",
    "send it",
    "do it now",
    "run it now",
    "comment now",
    "reply now",
    "live run",
    "go live",
    "actual run",
    "not dry run",
}


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_int(value: str, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _build_scam_callout_reply(params: Dict[str, str]) -> str:
    """
    Build a cautious anti-scam reply template for suspicious setup offers.
    """
    risk_reason = params.get("risk_reason", "").strip()
    suspicious_link = params.get("suspicious_link", params.get("link", "")).strip()
    opening = params.get("opening", "Potentially risky pattern here").strip()

    parts = [
        f"{opening}: third-party setup offer + external link.",
        "Please verify official OpenClaw/IronClaw channels before granting access.",
        "Avoid shortened links and unverified remote setup services.",
    ]
    if risk_reason:
        parts.append(f"Risk signal: {risk_reason}.")
    if suspicious_link:
        parts.append(f"Link to review: {suspicious_link}")
    return " ".join(parts).strip()


def _parse_action_command(message: str) -> Optional[Tuple[str, Dict[str, str]]]:
    text = (message or "").strip()
    if not text:
        return None

    lowered = text.lower()
    prefix = None
    if lowered.startswith("linkedin action "):
        prefix = "linkedin action "
    elif lowered.startswith("ln action "):
        prefix = "ln action "
    if not prefix:
        return None

    remainder = text[len(prefix) :].strip()
    if not remainder:
        return None

    parts = shlex.split(remainder)
    if not parts:
        return None

    raw_action = parts[0].strip().lower()
    action = ACTION_ALIASES.get(raw_action, raw_action)
    if action not in SUPPORTED_ACTIONS:
        return action, {}

    params: Dict[str, str] = {}
    for token in parts[1:]:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if key:
            params[key] = value
    return action, params


def _extract_quoted_text(message: str) -> str:
    match = re.search(r'["\']([^"\']{4,})["\']', message or "")
    return match.group(1).strip() if match else ""


def _normalize_text(message: str) -> str:
    lowered = (message or "").strip().lower()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def _parse_natural_linkedin_command(message: str) -> Optional[Tuple[str, Dict[str, str]]]:
    """
    Parse natural-language LinkedIn requests into deterministic adapter commands.

    Safety:
    - Defaults to dry_run=true unless the operator explicitly asks for live execution.
    - Focuses on comment/reply workflows for the visible post.
    """
    text = (message or "").strip()
    if not text:
        return None

    lowered = _normalize_text(text)
    post_reference_signal = re.search(r"\b(?:use\s+)?(?:post|index)\s*(\d+)\b", lowered) is not None
    has_linkedin_signal = (
        "linkedin" in lowered
        or re.search(r"\bln\b", lowered) is not None
        or "this post" in lowered
        or "that post" in lowered
        or "visible post" in lowered
        or "selected post" in lowered
        or post_reference_signal
    )
    has_comment_signal = (
        any(
            token in lowered
            for token in (
                "comment on",
                "reply to",
                "reply on",
                "respond to",
                "go agentic",
                "agentic reply",
                "agentic comment",
                "like and reply",
                "comment and like",
                "scan for scam",
                "scam reply",
            )
        )
        or re.search(r"\b(comment|reply|respond)\b", lowered) is not None
    )
    if not has_linkedin_signal or not has_comment_signal:
        return None

    params: Dict[str, str] = {}
    quoted = _extract_quoted_text(text)
    if quoted:
        params["reply_text"] = quoted

    post_index_match = re.search(r"\b(?:use\s+)?(?:post|index)\s*(\d+)\b", lowered)
    if post_index_match:
        params["post_index"] = str(max(0, int(post_index_match.group(1)) - 1))
    else:
        params["post_index"] = "0"

    if any(token in lowered for token in ("selected post", "visible selected post", "focused post")):
        params["use_selected_post"] = "true"

    if (
        "read post first" in lowered
        or "read it first" in lowered
        or "read first then comment" in lowered
        or "read first then reply" in lowered
    ):
        params["read_first"] = "true"

    if " as 0102" in lowered or "0102" in lowered or "agentic" in lowered:
        params["agentic"] = "true"
        params["agent_identity"] = "0102"

    if "dry run" in lowered or "preview" in lowered or "draft only" in lowered:
        params["dry_run"] = "true"
    elif any(token in lowered for token in _NATURAL_EXECUTE_TOKENS) or re.search(r"\b(now|live|execute)\b", lowered):
        params["dry_run"] = "false"
    else:
        params["dry_run"] = "true"

    if "like and reply" in lowered or "comment and like" in lowered:
        action = "like_reply"
    elif "scan for scam" in lowered or "scan linkedin for scam" in lowered:
        action = "scam_scan_reply"
    elif "scam reply" in lowered:
        action = "scam_reply"
    else:
        action = "reply_post"

    if action == "scam_scan_reply":
        params.setdefault("max_posts", "5")
        params.setdefault("max_replies", "1")
    return action, params


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    return value


async def _draft_agentic_linkedin_reply(linkedin: Any, params: Dict[str, str]) -> Dict[str, Any]:
    """Draft a LinkedIn reply from post context when agentic mode is requested."""
    post_index = _safe_int(params.get("post_index", "0"), default=0)
    return await linkedin.draft_agentic_reply(
        post_index=post_index,
        post_context=params.get("post_context", params.get("content", "")).strip(),
        author=params.get("author", "").strip(),
        engagement_reason=params.get("engagement_reason", "").strip(),
        agent_identity=params.get("agent_identity", "0102").strip() or "0102",
        use_selected_post=_truthy(params.get("use_selected_post", "false")),
        read_first=_truthy(params.get("read_first", "false")),
    )


async def _execute_agentic_linkedin_skill(
    action: str,
    params: Dict[str, str],
    dom_action_observer: Optional[Any] = None,
) -> Dict[str, Any]:
    from modules.platform_integration.linkedin_agent.skillz.linkedin_agentic_reply import (
        execute_skill as execute_agentic_skill,
    )

    result = await execute_agentic_skill(
        action=action,
        params=params,
        dom_action_observer=dom_action_observer,
    )
    result.setdefault("agentic_requested", True)
    return result


async def _execute_direct_action(
    action: str, params: Dict[str, str], linkedin: Any = None, *, dry_run: bool = False,
) -> Dict[str, Any]:
    """Run direct likes or sessions, or return their input preview."""
    if action == "engagement_session":
        config = {
            "duration_minutes": int(params.get("duration_minutes", "10")),
            "max_engagements": int(params.get("max_engagements", "5")),
        }
        if dry_run:
            return {"success": True, "action": action, "dry_run": True, **config}
        result = await linkedin.run_engagement_session(**config)
        return {"success": bool(result.success), "action": action, "result": _to_jsonable(result)}
    reply_fields = {}
    if action == "like_reply":
        reply_text = params.get("reply_text", "").strip()
        if not reply_text:
            return {
                "success": False, "action": action, "error": "missing reply_text",
                "agentic_requested": False, "draft": None,
            }
        reply_fields = {"reply_text": reply_text, "agentic_requested": False, "draft": None}
    post_index = _safe_int(params.get("post_index", "0"), default=0)
    post_id = params.get("post_id", "").strip() or f"index_{post_index}"

    if dry_run:
        return {
            "success": True, "action": action, "dry_run": True,
            "post_id": post_id, "post_index": post_index, **reply_fields,
        }
    if action == "like_post":
        result = await linkedin.like_post(post_id=post_id, post_index=post_index)
    else:
        result = await linkedin.like_and_reply(
            post_id=post_id, reply_text=reply_fields["reply_text"], post_index=post_index,
        )
    return {
        "success": bool(result.success), "action": action, **reply_fields,
        "result": _to_jsonable(result),
    }


async def execute_linkedin_action(
    action: str,
    params: Dict[str, str],
    dom_action_observer: Optional[Any] = None,
) -> Dict[str, Any]:
    agentic = _truthy(params.get("agentic", "false"))
    if action in {"reply_post", "like_reply", "scam_reply", "scam_scan_reply"} and agentic:
        return await _execute_agentic_linkedin_skill(action, params, dom_action_observer)

    if action in {"like_post", "like_reply", "engagement_session"} and _truthy(params.get("dry_run", "false")):
        int(params.get("browser_port", "9222"))  # Preserve validation without browser effects.
        return await _execute_direct_action(action, params, dry_run=True)

    from modules.infrastructure.browser_actions.src.linkedin_actions import LinkedInActions

    profile = params.get("profile", "linkedin_foundups")
    # Default to Chrome (9222) - LinkedIn and YouTube can share Chrome session
    browser_port = int(params.get("browser_port", "9222"))
    linkedin = LinkedInActions(
        profile=profile,
        browser_port=browser_port,
        dom_action_observer=dom_action_observer,
    )
    try:
        if action == "navigate_feed":
            result = await linkedin.navigate_to_feed()
            return {"success": bool(result.success), "action": action, "result": _to_jsonable(result)}

        if action == "navigate_profile":
            profile_url = params.get("profile_url", "").strip()
            if not profile_url:
                return {"success": False, "action": action, "error": "missing profile_url"}
            result = await linkedin.navigate_to_profile(profile_url)
            return {"success": bool(result.success), "action": action, "result": _to_jsonable(result)}

        if action == "read_feed":
            max_posts = int(params.get("max_posts", "10"))
            posts = await linkedin.read_feed(max_posts=max_posts)
            return {
                "success": True,
                "action": action,
                "posts_count": len(posts),
                "posts": _to_jsonable(posts),
            }

        if action in {"like_post", "like_reply", "engagement_session"}:
            return await _execute_direct_action(action, params, linkedin)

        if action == "reply_post":
            reply_text = params.get("reply_text", "").strip()
            drafted = None
            if not reply_text and agentic:
                drafted = await _draft_agentic_linkedin_reply(linkedin, params)
                if drafted.get("success"):
                    reply_text = str(drafted.get("reply_text", "")).strip()
            if not reply_text:
                return {
                    "success": False,
                    "action": action,
                    "error": "missing reply_text",
                    "agentic_requested": agentic,
                    "draft": _to_jsonable(drafted),
                }
            post_index = _safe_int(params.get("post_index", "0"), default=0)
            post_id = params.get("post_id", "").strip() or f"index_{post_index}"
            dry_run = _truthy(params.get("dry_run", "false"))
            if dry_run:
                return {
                    "success": True,
                    "action": action,
                    "dry_run": True,
                    "post_id": post_id,
                    "post_index": post_index,
                    "reply_text": reply_text,
                    "agentic_requested": agentic,
                    "draft": _to_jsonable(drafted),
                }
            result = await linkedin.reply_to_post(
                post_id=post_id,
                reply_text=reply_text,
                post_index=post_index,
            )
            return {
                "success": bool(result.success),
                "action": action,
                "reply_text": reply_text,
                "agentic_requested": agentic,
                "draft": _to_jsonable(drafted),
                "result": _to_jsonable(result),
            }

        if action == "scam_reply":
            post_index = _safe_int(params.get("post_index", "0"), default=0)
            post_id = params.get("post_id", "").strip() or f"index_{post_index}"
            drafted = None
            reply_text = params.get("reply_text", "").strip()
            if not reply_text and agentic:
                drafted = await _draft_agentic_linkedin_reply(linkedin, params)
                if drafted.get("success"):
                    reply_text = str(drafted.get("reply_text", "")).strip()
            if not reply_text:
                reply_text = _build_scam_callout_reply(params)
            dry_run = _truthy(params.get("dry_run", "true"))
            if dry_run:
                return {
                    "success": True,
                    "action": action,
                    "dry_run": True,
                    "post_id": post_id,
                    "post_index": post_index,
                    "reply_text": reply_text,
                    "agentic_requested": agentic,
                    "draft": _to_jsonable(drafted),
                }
            result = await linkedin.reply_to_post(
                post_id=post_id,
                reply_text=reply_text,
                post_index=post_index,
            )
            return {
                "success": bool(result.success),
                "action": action,
                "post_id": post_id,
                "post_index": post_index,
                "reply_text": reply_text,
                "agentic_requested": agentic,
                "draft": _to_jsonable(drafted),
                "result": _to_jsonable(result),
            }

        if action == "scam_scan":
            max_posts = _safe_int(params.get("max_posts", "10"), default=10)
            min_score = _safe_int(params.get("min_score", "4"), default=4)
            flagged = await linkedin.scan_feed_for_scam(
                max_posts=max_posts,
                min_score=min_score,
            )
            return {
                "success": True,
                "action": action,
                "flagged_count": len(flagged),
                "flagged_posts": flagged,
            }

        if action == "scam_scan_reply":
            max_posts = _safe_int(params.get("max_posts", "10"), default=10)
            min_score = _safe_int(params.get("min_score", "4"), default=4)
            max_replies = _safe_int(params.get("max_replies", "1"), default=1)
            dry_run = _truthy(params.get("dry_run", "true"))

            flagged = await linkedin.scan_feed_for_scam(
                max_posts=max_posts,
                min_score=min_score,
            )
            selected = flagged[: max(0, max_replies)]
            plans = []

            for item in selected:
                reply_text = params.get("reply_text", "").strip() or item.get("suggested_reply", "")
                drafted = None
                if agentic and not reply_text:
                    drafted = await linkedin.draft_agentic_reply(
                        post_index=int(item.get("post_index", 0)),
                        post_context=str(item.get("content", "")),
                        author=str(item.get("author", "")),
                        engagement_reason="scam_warning",
                        agent_identity=params.get("agent_identity", "0102").strip() or "0102",
                    )
                    if drafted.get("success"):
                        reply_text = str(drafted.get("reply_text", "")).strip()
                plans.append(
                    {
                        "post_id": item.get("post_id"),
                        "post_index": item.get("post_index"),
                        "author": item.get("author"),
                        "risk_score": item.get("risk_score"),
                        "risk_signals": item.get("risk_signals"),
                        "reply_text": reply_text,
                        "agentic_requested": agentic,
                        "draft": _to_jsonable(drafted),
                        "agentic_note": (
                            "Route through OpenClawDAE after switching model to codex or opus "
                            "if you want model-driven drafting/planning."
                            if agentic
                            else ""
                        ),
                    }
                )

            if dry_run:
                return {
                    "success": True,
                    "action": action,
                    "dry_run": True,
                    "flagged_count": len(flagged),
                    "planned_replies": plans,
                }

            results = []
            for plan in plans:
                result = await linkedin.reply_to_post(
                    post_id=str(plan["post_id"]),
                    reply_text=str(plan["reply_text"]),
                    post_index=int(plan["post_index"]),
                )
                results.append(
                    {
                        "post_id": plan["post_id"],
                        "post_index": plan["post_index"],
                        "author": plan["author"],
                        "success": bool(result.success),
                        "result": _to_jsonable(result),
                    }
                )

            return {
                "success": any(item.get("success") for item in results) if results else False,
                "action": action,
                "dry_run": False,
                "flagged_count": len(flagged),
                "reply_results": results,
            }

        if action == "connect":
            profile_url = params.get("profile_url", "").strip()
            if not profile_url:
                return {"success": False, "action": action, "error": "missing profile_url"}
            result = await linkedin.send_connection_request(
                profile_url=profile_url,
                message=params.get("message"),
                profile_name=params.get("profile_name"),
                headline=params.get("headline"),
                company=params.get("company"),
                industry=params.get("industry"),
                dry_run=_truthy(params.get("dry_run", "false")),
            )
            return {"success": bool(result.success), "action": action, "result": _to_jsonable(result)}

        if action == "digital_twin":
            comment_text = params.get("comment_text", "").strip()
            repost_text = params.get("repost_text", "").strip()
            schedule_date = params.get("schedule_date", "").strip()
            schedule_time = params.get("schedule_time", "").strip()
            mentions_raw = params.get("mentions", "@foundups")
            mentions = [m.strip() for m in mentions_raw.split(",") if m.strip()]
            identity_raw = params.get("identity_cycle", "")
            identity_cycle = [i.strip() for i in identity_raw.split(",") if i.strip()]
            if not all([comment_text, repost_text, schedule_date, schedule_time]):
                return {
                    "success": False,
                    "action": action,
                    "error": "missing comment_text, repost_text, schedule_date, or schedule_time",
                }
            result = await linkedin.run_digital_twin_flow(
                comment_text=comment_text,
                repost_text=repost_text,
                schedule_date=schedule_date,
                schedule_time=schedule_time,
                mentions=mentions,
                identity_cycle=identity_cycle or None,
                dry_run=_truthy(params.get("dry_run", "false")),
            )
            return {"success": bool(result.success), "action": action, "result": _to_jsonable(result)}

        if action == "group_post":
            dry_run = _truthy(params.get("dry_run", "true"))
            title = params.get("title", "").strip()
            url = params.get("url", params.get("source_url", "")).strip()
            summary = params.get("summary", "").strip() or None
            source = params.get("source", "manual").strip() or "manual"

            if title and url:
                from modules.platform_integration.linkedin_agent.skillz.openclaw_group_news import (
                    NewsItem,
                    OpenClawGroupPoster,
                )

                poster = OpenClawGroupPoster()
                item = NewsItem(title=title, url=url, source=source, summary=summary)
                success = await asyncio.to_thread(poster.post_to_group, item, dry_run)
                return {
                    "success": bool(success),
                    "action": action,
                    "mode": "manual_item",
                    "dry_run": dry_run,
                    "item": _to_jsonable(item),
                }

            from modules.platform_integration.linkedin_agent.skillz.openclaw_group_news import (
                run_openclaw_news_flow,
            )

            result = await asyncio.to_thread(run_openclaw_news_flow, dry_run)
            return {
                "success": bool((result or {}).get("posted", False)),
                "action": action,
                "mode": "auto_news_search",
                "result": _to_jsonable(result),
            }

        return {"success": False, "action": action, "error": "unsupported action"}

    finally:
        linkedin.close()


async def handle_linkedin_social_intent(message: str, sender: str = "") -> Optional[str]:
    """
    Handle SOCIAL intent if message is explicit LinkedIn action command.
    Returns formatted response text or None if not a LinkedIn action command.
    """
    parsed = _parse_action_command(message)
    if parsed is None:
        parsed = _parse_natural_linkedin_command(message)
    if parsed is None:
        return None

    action, params = parsed
    if action not in SUPPORTED_ACTIONS:
        return (
            "LinkedIn action not recognized.\n"
            f"Requested: {action}\n"
            f"Supported: {', '.join(sorted(SUPPORTED_ACTIONS))}\n"
            "Format: linkedin action <action> key=value"
        )

    try:
        result = await execute_linkedin_action(action, params)
        skill_note = ""
        if result.get("skill"):
            skill_note = f"Skill executed: {result['skill']}\n"
        return (
            f"LinkedIn action executed for {sender or 'unknown_sender'}:\n"
            f"{skill_note}"
            f"{json.dumps(result, indent=2, ensure_ascii=False)}"
        )
    except Exception as exc:
        return f"LinkedIn action execution error: {exc}"
