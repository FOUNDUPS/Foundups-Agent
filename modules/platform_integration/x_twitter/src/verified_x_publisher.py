"""API-only X publishing with explicit account binding and durable readback.

The injected client uses the synchronous Tweepy Client API. No credentials,
browser transport, simulator, automatic write retry, or reply generation live
in this leaf. Provider exception text is never returned or logged.
"""

import asyncio
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import hashlib
import re
from urllib.parse import urlsplit

from modules.platform_integration.social_media_orchestrator.src.core.publication_store import (
    PublicationStore,
)

_API_TIMEOUT_SECONDS = 30


async def _call(method, **kwargs):
    """Bound the await; the injected client must also bound its socket I/O.

    A timeout cannot revoke an accepted provider write. The caller retains its
    claim, and a cancelled/hung request never blocks the event loop on a join.
    """
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="verified-x")
    try:
        return await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(executor, partial(method, **kwargs)),
            timeout=_API_TIMEOUT_SECONDS,
        )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def decimal_id(value):
    """Accept canonical provider IDs, never booleans or simulated identifiers."""
    if type(value) is int:
        value = str(value)
    if isinstance(value, str) and re.fullmatch(r"[1-9][0-9]{0,19}", value):
        return value
    return None


def _field(value, name, default=None):
    return value.get(name, default) if isinstance(value, Mapping) else getattr(value, name, default)


def _data(response):
    if _field(response, "errors"):
        raise ValueError("Provider reported errors")
    data = _field(response, "data")
    if data is None:
        raise ValueError("Provider data missing")
    return data


def _expanded_text(data):
    """Expand only provider t.co entities, then compare the complete text."""
    text = _field(data, "text")
    if not isinstance(text, str):
        raise ValueError("Readback text missing")
    entities = _field(data, "entities", {})
    if not isinstance(entities, Mapping):
        raise ValueError("Malformed readback entities")
    urls = entities.get("urls", [])
    if not isinstance(urls, list):
        raise ValueError("Malformed readback URLs")
    replacements = {}
    for entity in urls:
        short = _field(entity, "url")
        expanded = _field(entity, "expanded_url")
        if not isinstance(short, str) or not isinstance(expanded, str):
            raise ValueError("Malformed readback URL")
        if urlsplit(short).hostname != "t.co":
            continue
        if urlsplit(expanded).scheme not in {"http", "https"}:
            raise ValueError("Malformed expanded URL")
        if short in replacements and replacements[short] != expanded:
            raise ValueError("Conflicting readback URL")
        replacements[short] = expanded
    return re.sub(r"https?://t\.co/[A-Za-z0-9]+", lambda m: replacements.get(m[0], m[0]), text)


def _result(account, status, *, provider_user_id=None, post_id=None, error=None):
    return dict(success=status in {"verified", "already_verified"}, status=status,
                dry_run=False, account=account, provider_user_id=provider_user_id,
                post_id=post_id,
                post_url=f"https://x.com/i/web/status/{post_id}" if post_id else None,
                error=error)


async def _identify(client, expected_user_id):
    try:
        response = await _call(client.get_me, user_auth=True)
        actual = decimal_id(_field(_data(response), "id"))
    except Exception:
        return None, "authentication_failed"
    if actual is None:
        return None, "malformed_identity"
    return actual, None if actual == expected_user_id else "account_mismatch"


async def _create(client, store, claim, content):
    try:
        response = await _call(client.create_tweet, text=content, user_auth=True)
        post_id = decimal_id(_field(_data(response), "id"))
        if post_id is None:
            raise ValueError("Malformed provider ID")
    except Exception:
        try:
            store.record_unknown(claim)
        except Exception:
            return None, "storage_error", "create_outcome_unknown"
        return None, "outcome_unknown", "create_outcome_unknown"
    try:
        store.record_post_id(claim, post_id)
    except Exception:
        return post_id, "storage_error", "receipt_not_durable"
    return post_id, None, None


async def _readback(client, store, claim, content, post_id):
    status, error = "verified", None
    try:
        response = await _call(
            client.get_tweet, id=post_id, tweet_fields=["author_id", "entities"],
            user_auth=True,
        )
    except Exception:
        status, error = "readback_pending", "readback_unavailable"
    else:
        try:
            data = _data(response)
            matches = (
                decimal_id(_field(data, "id")) == post_id
                and decimal_id(_field(data, "author_id")) == claim["provider_user_id"]
                and _expanded_text(data) == content
            )
            if not matches:
                raise ValueError("Readback mismatch")
        except Exception:
            status, error = "verification_failed", "readback_mismatch"
    try:
        store.record_readback(claim, post_id, verified=status == "verified", error=error)
    except Exception:
        status, error = "storage_error", "verification_not_durable"
    return _result(claim["account"], status, provider_user_id=claim["provider_user_id"],
                   post_id=post_id, error=error)


async def publish_verified_x(content, account, campaign_id, job_id, *, client,
                             expected_user_id, db_path):
    """Execute a validated request admitted by UnifiedXInterface only."""
    actual, error = await _identify(client, expected_user_id)
    if error:
        return _result(account, "rejected", provider_user_id=actual, error=error)
    try:
        store = PublicationStore(db_path)
        claim = store.claim(account, actual, campaign_id, job_id,
                            hashlib.sha256(content.encode("utf-8")).hexdigest())
    except Exception:
        return _result(account, "storage_error", provider_user_id=actual,
                       error="claim_not_durable")
    decision = claim["decision"]
    if decision in {"account_conflict", "content_conflict", "rate_limited", "outcome_unknown"}:
        status = "rejected" if decision.endswith("conflict") else decision
        return _result(account, status, provider_user_id=actual, error=decision)
    post_id = decimal_id(claim.get("post_id"))
    if decision == "already_verified" and post_id:
        return _result(account, "already_verified", provider_user_id=actual, post_id=post_id)
    if decision == "claimed":
        post_id, status, error = await _create(client, store, claim, content)
        if status:
            return _result(account, status, provider_user_id=actual, post_id=post_id, error=error)
    if not post_id:
        return _result(account, "rejected", provider_user_id=actual, error="invalid_receipt")
    return await _readback(client, store, claim, content, post_id)
