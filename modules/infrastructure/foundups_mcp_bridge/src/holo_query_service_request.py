"""Bounded request validation for the private Holo query owner."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping


DEFAULT_LIMIT = 8
ALLOWED_DOC_TYPE_FILTERS = frozenset(
    {"all", "code", "wsp", "test", "skill", "docs", "knowledge"}
)
EXPECTED_SHA_PATTERN = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
EXPECTED_ROOT_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


def _serialized_size(payload: Mapping[str, Any]) -> tuple[int, str]:
    try:
        return len(json.dumps(
            payload, separators=(",", ":"), ensure_ascii=False
        ).encode()), ""
    except (TypeError, ValueError):
        return 0, "INVALID_REQUEST"


def validate_payload(
    payload: Any, *, request_size: int | None, max_request_bytes: int,
    max_query_chars: int, max_limit: int,
) -> tuple[dict[str, Any] | None, str]:
    if request_size is not None and request_size > max_request_bytes:
        return None, "REQUEST_TOO_LARGE"
    if not isinstance(payload, Mapping):
        return None, "INVALID_REQUEST"
    size, error = _serialized_size(payload)
    if error or size > max_request_bytes:
        return None, error or "REQUEST_TOO_LARGE"
    allowed = {
        "query", "limit", "doc_type_filter", "expected_repo_head_sha",
        "expected_repo_root_digest",
    }
    if set(payload) - allowed:
        return None, "UNSUPPORTED_REQUEST_FIELDS"
    query_value = payload.get("query")
    if not isinstance(query_value, str) or not query_value.strip():
        return None, "EMPTY_QUERY"
    query = query_value.strip()
    if len(query) > max_query_chars:
        return None, "QUERY_TOO_LARGE"
    limit = payload.get("limit", DEFAULT_LIMIT)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= max_limit:
        return None, "INVALID_LIMIT"
    doc_type = payload.get("doc_type_filter", "all")
    if not isinstance(doc_type, str) or doc_type not in ALLOWED_DOC_TYPE_FILTERS:
        return None, "INVALID_DOC_TYPE_FILTER"
    expected_sha = payload.get("expected_repo_head_sha")
    if not isinstance(expected_sha, str) or not EXPECTED_SHA_PATTERN.fullmatch(expected_sha):
        return None, "EXPECTED_REPO_HEAD_SHA_REQUIRED"
    expected_root = payload.get("expected_repo_root_digest")
    if expected_root is not None and (
        not isinstance(expected_root, str)
        or not EXPECTED_ROOT_DIGEST_PATTERN.fullmatch(expected_root)
    ):
        return None, "EXPECTED_REPO_ROOT_DIGEST_REQUIRED"
    return {
        "query": query, "limit": limit, "doc_type_filter": doc_type,
        "expected_repo_head_sha": expected_sha,
        "expected_repo_root_digest": str(expected_root or ""),
    }, ""


__all__ = [
    "ALLOWED_DOC_TYPE_FILTERS", "EXPECTED_ROOT_DIGEST_PATTERN",
    "EXPECTED_SHA_PATTERN", "validate_payload",
]
