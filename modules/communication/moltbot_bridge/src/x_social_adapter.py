"""
X/Twitter social adapter for OpenClaw/IronClaw SOCIAL intent routing.

Command format (strict):
  x action <action> key=value key2="value 2"
  twitter action <action> key=value

Examples:
  x action post content="foundups: roi -> roc"
  x action read_timeline max_tweets=5
  x action engagement_session duration_minutes=10 max_engagements=3
  x action like_tweet tweet_id=1234567890
  x action retweet tweet_id=1234567890
  x action reply_to_tweet tweet_id=1234567890 reply_text="agreed"
  x action like_and_reply tweet_id=1234567890 reply_text="agreed"
"""

from __future__ import annotations

import json
import shlex
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional, Tuple


SUPPORTED_ACTIONS = {
    "post",
    "read_timeline",
    "engagement_session",
    "like_tweet",
    "retweet",
    "reply_to_tweet",
    "like_and_reply",
}

ACTION_ALIASES = {
    "post_tweet": "post",
    "tweet": "post",
    "publish": "post",
    "read": "read_timeline",
    "timeline": "read_timeline",
    "engage": "engagement_session",
    "session": "engagement_session",
    "like": "like_tweet",
    "heart": "like_tweet",
    "rt": "retweet",
    "repost": "retweet",
    "reply": "reply_to_tweet",
    "respond": "reply_to_tweet",
    "like_reply": "like_and_reply",
}


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_param(params: Dict[str, str], key: str, default: int) -> int:
    raw = params.get(key)
    if raw is None:
        return default
    try:
        return int(str(raw).strip())
    except Exception:
        return default


def _parse_action_command(message: str) -> Optional[Tuple[str, Dict[str, str]]]:
    text = (message or "").strip()
    if not text:
        return None

    lowered = text.lower()
    prefix = None
    if lowered.startswith("x action "):
        prefix = "x action "
    elif lowered.startswith("twitter action "):
        prefix = "twitter action "
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


async def execute_x_action(action: str, params: Dict[str, str]) -> Dict[str, Any]:
    profile = params.get("profile", "x_foundups")
    ai_provider = params.get("ai_provider", "qwen")
    dry_run = _truthy(params.get("dry_run", "false"))
    if action == "post":
        content = params.get("content", params.get("text", "")).strip()
        if not content:
            return {"success": False, "action": action, "error": "missing content"}
        if dry_run:
            return {
                "success": True,
                "action": action,
                "dry_run": True,
                "profile": profile,
                "content_preview": content[:280],
            }

        from modules.infrastructure.browser_actions.src.x_actions import XActions

        x = XActions(profile=profile, ai_provider=ai_provider)
        try:
            image_path = params.get("image_path", "").strip() or None
            result = await x.post_tweet(content=content, image_path=image_path)
            return {"success": bool(result.success), "action": action, "result": _to_jsonable(result)}
        finally:
            x.close()

    if action == "read_timeline":
        max_tweets = _int_param(params, "max_tweets", 10)
        if dry_run:
            return {
                "success": True,
                "action": action,
                "dry_run": True,
                "profile": profile,
                "max_tweets": max_tweets,
            }

        from modules.infrastructure.browser_actions.src.x_actions import XActions

        x = XActions(profile=profile, ai_provider=ai_provider)
        try:
            tweets = await x.read_timeline(max_tweets=max_tweets)
            return {
                "success": True,
                "action": action,
                "tweets_count": len(tweets),
                "tweets": _to_jsonable(tweets),
            }
        finally:
            x.close()

    if action == "engagement_session":
        duration_minutes = _int_param(params, "duration_minutes", 10)
        max_engagements = _int_param(params, "max_engagements", 5)
        if dry_run:
            return {
                "success": True,
                "action": action,
                "dry_run": True,
                "profile": profile,
                "duration_minutes": duration_minutes,
                "max_engagements": max_engagements,
            }

        from modules.infrastructure.browser_actions.src.x_actions import XActions

        x = XActions(profile=profile, ai_provider=ai_provider)
        try:
            result = await x.run_engagement_session(
                duration_minutes=duration_minutes,
                max_engagements=max_engagements,
            )
            return {"success": bool(result.success), "action": action, "result": _to_jsonable(result)}
        finally:
            x.close()

    if action in {"like_tweet", "retweet", "reply_to_tweet", "like_and_reply"}:
        tweet_id = params.get("tweet_id", params.get("id", "")).strip()
        if not tweet_id:
            return {"success": False, "action": action, "error": "missing tweet_id"}

        needs_reply = action in {"reply_to_tweet", "like_and_reply"}
        reply_text = params.get("reply_text", params.get("text", params.get("content", ""))).strip()
        if needs_reply and not reply_text:
            return {"success": False, "action": action, "error": "missing reply_text"}

        if dry_run:
            preview: Dict[str, Any] = {
                "success": True,
                "action": action,
                "dry_run": True,
                "profile": profile,
                "tweet_id": tweet_id,
            }
            if needs_reply:
                preview["reply_preview"] = reply_text[:280]
            return preview

        from modules.infrastructure.browser_actions.src.x_actions import XActions

        x = XActions(profile=profile, ai_provider=ai_provider)
        try:
            if action == "like_tweet":
                result = await x.like_tweet(tweet_id=tweet_id)
            elif action == "retweet":
                result = await x.retweet(tweet_id=tweet_id)
            elif action == "reply_to_tweet":
                result = await x.reply_to_tweet(tweet_id=tweet_id, reply_text=reply_text)
            else:  # like_and_reply
                result = await x.like_and_reply(tweet_id=tweet_id, reply_text=reply_text)
            return {"success": bool(result.success), "action": action, "result": _to_jsonable(result)}
        finally:
            x.close()

    return {"success": False, "action": action, "error": "unsupported action"}


async def handle_x_social_intent(message: str, sender: str = "") -> Optional[str]:
    """
    Handle SOCIAL intent if message is explicit X action command.
    Returns formatted response text or None if not an X action command.
    """
    parsed = _parse_action_command(message)
    if parsed is None:
        return None

    action, params = parsed
    if action not in SUPPORTED_ACTIONS:
        return (
            "X action not recognized.\n"
            f"Requested: {action}\n"
            f"Supported: {', '.join(sorted(SUPPORTED_ACTIONS))}\n"
            "Format: x action <action> key=value"
        )

    try:
        result = await execute_x_action(action, params)
        return (
            f"X action executed for {sender or 'unknown_sender'}:\n"
            f"{json.dumps(result, indent=2, ensure_ascii=False)}"
        )
    except Exception as exc:
        return f"X action execution error: {exc}"
