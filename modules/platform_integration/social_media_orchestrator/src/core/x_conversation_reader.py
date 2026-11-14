"""Read bounded X conversation context for listener-initiated station drafts.

Provider text is untrusted data. This reader has no search, write, or reply API.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any


class ConversationReadError(ValueError):
    """Only fixed reader validation identifiers may cross the campaign boundary."""


TWEET_FIELDS = [
    "author_id", "conversation_id", "created_at", "entities",
    "in_reply_to_user_id", "referenced_tweets",
]
_ID = re.compile(r"[1-9][0-9]{0,19}\Z")


def provider_id(value: Any) -> str:
    """Reject synthetic IDs, booleans, and lossy numeric coercions."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ConversationReadError("provider_id_invalid")
    result = str(value)
    if not _ID.fullmatch(result):
        raise ConversationReadError("provider_id_invalid")
    return result


def record(value: Any) -> dict[str, Any]:
    """Accept Tweepy Response/Tweet/User objects or their dictionary form."""
    for _ in range(3):
        errors = value.get("errors") if isinstance(value, Mapping) else getattr(value, "errors", None)
        if errors:
            raise ConversationReadError("provider_reported_errors")
        if isinstance(value, Mapping):
            if "data" in value and "id" not in value:
                value = value["data"]
                continue
            return dict(value)
        value = getattr(value, "data", None)
    raise ConversationReadError("provider_record_invalid")


def verify_account(client: Any, expected_user_id: str) -> dict[str, str]:
    expected = provider_id(expected_user_id)
    me = record(client.get_me(user_auth=True))
    if provider_id(me.get("id")) != expected:
        raise ConversationReadError("account_identity_mismatch")
    return {"user_id": expected, "username": str(me.get("username", ""))[:15]}


def read_conversation(client: Any, post_id: str, account_id: str) -> dict[str, Any]:
    """Read the target and up to four connected parents/quoted posts.

    Missing, oversized, or deeper context is reported as incomplete. A mention
    establishes contact only; the drafter must still judge the actual request.
    """
    target_id, account_id = provider_id(post_id), provider_id(account_id)
    pending, seen, posts = [target_id], set(), []
    complete, initiated = True, False
    while pending and len(posts) < 5:
        current = pending.pop(0)
        if current in seen:
            continue
        seen.add(current)
        item = record(client.get_tweet(current, tweet_fields=TWEET_FIELDS, user_auth=True))
        if provider_id(item.get("id")) != current:
            raise ConversationReadError("source_identity_mismatch")
        author_id = provider_id(item.get("author_id"))
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ConversationReadError("source_text_missing")
        if len(text) > 1800:
            complete = False
        if current == target_id and author_id != account_id:
            entities = item.get("entities", {})
            if not isinstance(entities, Mapping):
                raise ConversationReadError("source_entities_invalid")
            mentions = entities.get("mentions", [])
            if not isinstance(mentions, list):
                raise ConversationReadError("source_mentions_invalid")
            initiated = str(item.get("in_reply_to_user_id", "")) == account_id or any(
                isinstance(mention, Mapping) and str(mention.get("id", "")) == account_id
                for mention in mentions
            )
        references = item.get("referenced_tweets", [])
        if not isinstance(references, list):
            raise ConversationReadError("source_references_invalid")
        if item.get("in_reply_to_user_id") and not any(
            isinstance(reference, Mapping) and reference.get("type") == "replied_to"
            for reference in references
        ):
            complete = False
        edges = []
        for reference in references:
            if not isinstance(reference, Mapping):
                raise ConversationReadError("source_reference_invalid")
            kind = reference.get("type")
            if kind in {"replied_to", "quoted"}:
                linked = provider_id(reference.get("id"))
                edges.append({"type": kind, "id": linked})
                if linked not in seen and linked not in pending:
                    pending.append(linked)
        posts.append({"id": current, "author_id": author_id, "text": text[:1800],
                      "references": edges})
    complete = complete and not pending
    context = json.dumps({"target_post_id": target_id, "posts": posts}, ensure_ascii=False)
    if len(context) > 2400:
        complete = False
    return {
        "post_id": target_id,
        "source_url": f"https://x.com/i/status/{target_id}",
        "thread_context": context,
        "context_complete": complete,
        "initiated_by_listener": initiated,
        "posts_read": len(posts),
    }


def recent_mention_ids(client: Any, account_id: str, limit: int) -> list[str]:
    """Return at most five recent explicit mentions; no keyword targeting."""
    if type(limit) is not int or not 1 <= limit <= 5:
        raise ConversationReadError("mention_limit_invalid")
    response = client.get_users_mentions(
        provider_id(account_id), max_results=5, user_auth=True,
    )
    errors = response.get("errors") if isinstance(response, Mapping) else getattr(response, "errors", None)
    if errors:
        raise ConversationReadError("provider_reported_errors")
    values = response.get("data") if isinstance(response, Mapping) else getattr(response, "data", None)
    if values is None:
        meta = response.get("meta") if isinstance(response, Mapping) else getattr(response, "meta", None)
        if isinstance(meta, Mapping) and type(meta.get("result_count")) is int and meta["result_count"] == 0:
            return []
        raise ConversationReadError("mentions_response_invalid")
    if not isinstance(values, list):
        raise ConversationReadError("mentions_response_invalid")
    ids = []
    for value in values:
        candidate = provider_id(record(value).get("id"))
        if candidate not in ids:
            ids.append(candidate)
        if len(ids) == limit:
            break
    return ids
