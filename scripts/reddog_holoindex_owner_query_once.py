#!/usr/bin/env python3
"""One-shot generation-bound HoloIndex query bridge for the RedDog extension.

The extension sends one bounded semantic query on stdin. This adapter starts or
reuses the existing authenticated loopback owner, executes the query through
``query_holoindex_owner``, and returns only the owner's secret-free response.
It never indexes, mutates repository state, or exposes the owner bearer token.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from holo_index.query_receipt import build_query_receipt  # noqa: E402
from modules.communication.moltbot_bridge.src.reddog_holoindex_owner_query_client import (  # noqa: E402
    query_holoindex_owner,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_bootstrap import (  # noqa: E402
    OWNER_CONFIGURED,
    OWNER_REUSED,
    OWNER_STARTED,
    cleanup_reddog_holoindex_owner,
    ensure_reddog_holoindex_owner,
    resolve_reddog_holoindex_owner_handoff,
)


MAX_QUERY_CHARS = 16_000
MAX_LIMIT = 20


def _failure(error: str, *, query: str = "") -> dict[str, Any]:
    return {
        "ok": False,
        "source": "holoindex_owner_service",
        "query": query,
        "freshness": "UNKNOWN",
        "raw_result": {},
        "error": error,
        "index_gap_detected": True,
        "stale_reasons": ["holoindex_owner_query_failed"],
        "no_holoindex_reindex_performed": True,
    }


def _read_payload() -> Mapping[str, Any]:
    raw = sys.stdin.buffer.read()
    value = json.loads(raw.decode("utf-8", errors="strict"))
    if not isinstance(value, Mapping):
        raise ValueError("payload_not_object")
    return value


def _bounded_request(payload: Mapping[str, Any]) -> tuple[str, int, str]:
    query = payload.get("query")
    if not isinstance(query, str) or not query.strip():
        return "", 0, "query_required"
    query = query.strip()
    if len(query) > MAX_QUERY_CHARS:
        return "", 0, "query_too_large"
    raw_limit = payload.get("limit", 5)
    if isinstance(raw_limit, bool):
        return "", 0, "limit_invalid"
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return "", 0, "limit_invalid"
    if limit < 1 or limit > MAX_LIMIT:
        return "", 0, "limit_invalid"
    return query, limit, ""


def query_once(
    payload: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    ensure_owner: Callable[..., Any] = ensure_reddog_holoindex_owner,
    resolve_handoff: Callable[[], tuple[str, str] | None] = (
        resolve_reddog_holoindex_owner_handoff
    ),
    query_owner: Callable[..., Mapping[str, Any]] = query_holoindex_owner,
    cleanup_owner: Callable[..., None] = cleanup_reddog_holoindex_owner,
) -> Mapping[str, Any]:
    """Execute one owner-bound query and always clean up process-owned state."""

    query, limit, request_error = _bounded_request(payload)
    if request_error:
        return _failure(request_error)

    started_here = False
    try:
        bootstrap = ensure_owner(repo_root=repo_root, requested=True)
        status = str(getattr(bootstrap, "status", ""))
        if getattr(bootstrap, "ready", False) is not True:
            return _failure(
                str(getattr(bootstrap, "error", "") or "owner_bootstrap_failed"),
                query=query,
            )
        started_here = status == OWNER_STARTED
        service_url: str | None = None
        service_token: str | None = None
        if status in {OWNER_STARTED, OWNER_REUSED}:
            handoff = resolve_handoff()
            if handoff is None:
                return _failure("owner_handoff_missing", query=query)
            service_url, service_token = handoff
        elif status != OWNER_CONFIGURED:
            return _failure("owner_bootstrap_status_invalid", query=query)

        result = query_owner(
            repo_root=repo_root,
            query=query,
            limit=limit,
            service_url=service_url,
            service_token=service_token,
            timeout_seconds=60.0,
        )
        if not isinstance(result, Mapping):
            return _failure("owner_response_invalid", query=query)
        receipt = build_query_receipt(
            source="holoindex_owner_service",
            source_class="holoindex",
            query=query,
            result=result,
            require_generation=True,
        )
        return {**dict(result), "query_receipt": dict(receipt)}
    except Exception as exc:
        return _failure(type(exc).__name__, query=query)
    finally:
        if started_here:
            cleanup_owner()


def main() -> int:
    try:
        payload = _read_payload()
    except (UnicodeError, ValueError, json.JSONDecodeError):
        result: Mapping[str, Any] = _failure("invalid_json")
    else:
        result = query_once(payload)
    sys.stdout.write(json.dumps(result, ensure_ascii=True, sort_keys=True))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
