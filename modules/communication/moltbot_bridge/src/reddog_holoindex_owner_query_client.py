"""Bounded loopback client for the host-owned HoloIndex query service.

This module isolates transport from the RedDog read-only audit worker. It has
no indexing or repository mutation authority and accepts only a loopback HTTP
endpoint with bearer authentication.
"""

from __future__ import annotations

import ipaddress
import inspect
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from holo_index.repository_state import read_repository_state, repository_root_digest
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service import (
    MIN_BEARER_TOKEN_CHARS,
    TOKEN_TOO_SHORT_ERROR,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_replica_binding import (
    parse_replica_binding,
)


HOLOINDEX_QUERY_SERVICE_URL_ENV = "HOLOINDEX_QUERY_SERVICE_URL"
HOLOINDEX_QUERY_SERVICE_TOKEN_ENV = "HOLOINDEX_QUERY_SERVICE_TOKEN"
MAX_HOLOINDEX_SERVICE_RESPONSE_BYTES = 2_000_000
_REPLICA_PUBLIC_FIELDS = (
    "query_replica_descriptor_digest",
    "query_replica_generation_id",
    "query_replica_id",
    "query_replica_path_identity_digest",
)
_EMPTY_REPLICA_BINDING = ("", "", "", "")


@dataclass
class _OwnerResponseState:
    ok: bool
    error: str
    freshness: str
    stale_reasons: list[str]
    raw_result: Mapping[str, Any]
    repo_head_sha: str
    repo_root_digest: str
    generation_id: str
    receipt_digest: str
    retrieval_mode: str
    replica_binding: tuple[str, str, str, str]


@dataclass(frozen=True)
class _OwnerQueryContext:
    repo_root: Path
    query: str
    endpoint: str
    token: str
    expected_head: str
    expected_root_digest: str
    started: float
    deadline: float


class _NoRedirectHandler(HTTPRedirectHandler):
    """Fail closed instead of forwarding the bearer token to a redirect."""

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        del req, fp, code, msg, headers, newurl
        return None


_NO_REDIRECT_OPENER = build_opener(ProxyHandler({}), _NoRedirectHandler())
# Keep this module-level call seam so focused tests can replace transport without
# weakening the production default's redirect policy.
urlopen = _NO_REDIRECT_OPENER.open


def _endpoint(value: str) -> str:
    endpoint = str(value or "").strip().rstrip("/")
    if not endpoint:
        return ""
    parsed = urlparse(endpoint)
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("HOLOINDEX_QUERY_SERVICE_URL_NOT_LOOPBACK") from exc
    try:
        address = ipaddress.ip_address(parsed.hostname or "")
    except ValueError as exc:
        raise ValueError("HOLOINDEX_QUERY_SERVICE_URL_NOT_LOOPBACK") from exc
    if (
        parsed.scheme != "http"
        or str(address) != "127.0.0.1"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("HOLOINDEX_QUERY_SERVICE_URL_NOT_LOOPBACK")
    path = parsed.path.rstrip("/")
    if path not in {"", "/holoindex/v1/query"}:
        raise ValueError("HOLOINDEX_QUERY_SERVICE_PATH_INVALID")
    if not path:
        endpoint += "/holoindex/v1/query"
    return endpoint


def _error_code(payload: Mapping[str, Any], default: str) -> str:
    error = payload.get("error")
    if isinstance(error, Mapping):
        return str(error.get("code") or default)
    detail = payload.get("detail")
    if isinstance(detail, Mapping):
        detail_error = detail.get("error")
        if isinstance(detail_error, Mapping):
            return str(detail_error.get("code") or default)
        if detail_error:
            return str(detail_error)
    return str(error or default)


def _failure(
    *,
    query: str,
    started: float,
    error: str,
    stale_reasons: tuple[str, ...] = (),
) -> Mapping[str, Any]:
    return {
        "ok": False,
        "source": "holoindex_owner_service",
        "query": query,
        "freshness": "UNKNOWN",
        "raw_result": {},
        "error": error,
        "latency_ms": int((time.monotonic() - started) * 1000),
        "index_gap_detected": True,
        "stale_reasons": list(stale_reasons),
        "no_holoindex_reindex_performed": True,
    }


def _service_token(value: str | None) -> tuple[str, str]:
    token = str(
        value
        if value is not None
        else os.getenv(HOLOINDEX_QUERY_SERVICE_TOKEN_ENV, "")
    ).strip()
    if not token:
        return "", "HOLOINDEX_QUERY_SERVICE_TOKEN_MISSING"
    if len(token) < MIN_BEARER_TOKEN_CHARS:
        return "", TOKEN_TOO_SHORT_ERROR
    return token, ""


def _request_payload(
    *,
    query: str,
    limit: int,
    expected_head: str,
    expected_root_digest: str,
) -> bytes:
    return json.dumps(
        {
            "query": query,
            "limit": max(1, min(int(limit or 8), 20)),
            "expected_repo_head_sha": expected_head,
            "expected_repo_root_digest": expected_root_digest,
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _set_response_socket_timeout(response: Any, timeout_seconds: float) -> None:
    """Shorten the live socket timeout as the absolute deadline approaches."""

    frontier = [response]
    seen: set[int] = set()
    for _depth in range(5):
        next_frontier: list[Any] = []
        for candidate in frontier:
            identity = id(candidate)
            if identity in seen:
                continue
            seen.add(identity)
            setter = getattr(candidate, "settimeout", None)
            if callable(setter):
                setter(max(0.001, float(timeout_seconds)))
                return
            for attribute in ("fp", "raw", "_sock", "sock"):
                try:
                    nested = getattr(candidate, attribute, None)
                except Exception:
                    nested = None
                if nested is not None:
                    next_frontier.append(nested)
        frontier = next_frontier


def _read_response_body(response: Any, *, deadline: float) -> bytes:
    chunks: list[bytes] = []
    total = 0
    read_one = getattr(response, "read1", None)
    reader = read_one if callable(read_one) else getattr(response, "read", None)
    if not callable(reader):
        raise ValueError("HOLOINDEX_QUERY_SERVICE_INVALID_RESPONSE")
    chunk_size = 64 * 1024 if callable(read_one) else 1
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("HOLOINDEX_QUERY_DEADLINE_EXCEEDED")
        _set_response_socket_timeout(response, remaining)
        chunk = reader(
            min(
                chunk_size,
                MAX_HOLOINDEX_SERVICE_RESPONSE_BYTES + 1 - total,
            )
        )
        if time.monotonic() >= deadline:
            raise TimeoutError("HOLOINDEX_QUERY_DEADLINE_EXCEEDED")
        if not chunk:
            break
        if not isinstance(chunk, bytes):
            raise ValueError("HOLOINDEX_QUERY_SERVICE_INVALID_RESPONSE")
        chunks.append(chunk)
        total += len(chunk)
        if total > MAX_HOLOINDEX_SERVICE_RESPONSE_BYTES:
            raise ValueError("HOLOINDEX_QUERY_SERVICE_RESPONSE_TOO_LARGE")
    return b"".join(chunks)


def _read_payload(request: Request, *, deadline: float) -> Mapping[str, Any]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("HOLOINDEX_QUERY_DEADLINE_EXCEEDED")
    with urlopen(
        request,
        timeout=max(0.001, min(remaining, 60.0)),
    ) as response:
        raw_body = _read_response_body(response, deadline=deadline)
    payload = json.loads(raw_body.decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("HOLOINDEX_QUERY_SERVICE_INVALID_RESPONSE")
    return payload


def _http_error_payload(
    exc: HTTPError,
    *,
    deadline: float,
) -> Mapping[str, Any] | None:
    try:
        body = _read_response_body(exc, deadline=deadline)
        error_payload = json.loads(body.decode("utf-8"))
    except TimeoutError:
        raise
    except Exception:
        return None
    return error_payload if isinstance(error_payload, Mapping) else None


def _repository_state_with_budget(repo_root: Path, remaining: float) -> Any | None:
    reader = read_repository_state
    parameters = inspect.signature(reader).parameters.values()
    supports_timeout = any(
        item.name == "timeout_seconds"
        or item.kind is inspect.Parameter.VAR_KEYWORD
        for item in parameters
    )
    timeout = max(0.01, min(remaining, 15.0))
    executor = ThreadPoolExecutor(
        max_workers=1,
        thread_name_prefix="holoindex-client-repository-proof",
    )
    try:
        if supports_timeout:
            future = executor.submit(
                reader,
                repo_root,
                timeout_seconds=timeout,
            )
        else:
            future = executor.submit(reader, repo_root)
        return future.result(timeout=timeout)
    except FutureTimeoutError:
        return None
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _post_query_repository_error(
    repo_root: Path,
    expected_head: str,
    deadline: float,
) -> str:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return "HOLOINDEX_QUERY_DEADLINE_EXCEEDED"
    repository_state = _repository_state_with_budget(repo_root, remaining)
    if repository_state is None:
        return "HOLOINDEX_QUERY_DEADLINE_EXCEEDED"
    if time.monotonic() >= deadline:
        return "HOLOINDEX_QUERY_DEADLINE_EXCEEDED"
    if not repository_state.proven_clean:
        return "REPOSITORY_STATE_CHANGED_DURING_QUERY"
    if repository_state.head_sha != expected_head:
        return "REPOSITORY_STATE_CHANGED_DURING_QUERY"
    return ""


def _response_state(payload: Mapping[str, Any]) -> _OwnerResponseState:
    raw_value = payload.get("raw_result")
    raw_result = raw_value if isinstance(raw_value, Mapping) else {}
    ok = payload.get("ok") is True
    raw_reasons = payload.get("stale_reasons")
    stale_reasons = (
        [str(value) for value in raw_reasons if str(value).strip()]
        if isinstance(raw_reasons, list)
        else []
    )
    replica = parse_replica_binding(
        tuple(payload.get(key) for key in _REPLICA_PUBLIC_FIELDS)
    )
    return _OwnerResponseState(
        ok=ok,
        error=_error_code(
            payload,
            "HOLOINDEX_QUERY_SERVICE_FAILED",
        )
        if not ok
        else "",
        freshness=str(payload.get("freshness") or "UNKNOWN").upper(),
        stale_reasons=stale_reasons,
        raw_result=raw_result,
        repo_head_sha=str(payload.get("repo_head_sha") or ""),
        repo_root_digest=str(payload.get("repo_root_digest") or ""),
        generation_id=str(payload.get("freshness_generation_id") or ""),
        receipt_digest=str(payload.get("freshness_receipt_digest") or ""),
        retrieval_mode=str(payload.get("retrieval_mode") or "").lower(),
        replica_binding=replica or _EMPTY_REPLICA_BINDING,
    )


def _response_contract_checks(
    state: _OwnerResponseState, *, success_contract_valid: bool,
    expected_head: str, repo_root: Path,
) -> tuple[tuple[bool, str, str], ...]:
    return (
        (not success_contract_valid, "HOLOINDEX_QUERY_SERVICE_CONTRACT_INVALID",
         "owner_response_contract_invalid"),
        (state.repo_head_sha != expected_head, "REPO_HEAD_MISMATCH",
         "stale_repo_head_sha"),
        (state.repo_root_digest != repository_root_digest(repo_root),
         "REPO_ROOT_MISMATCH", "repository_root_mismatch"),
        (not state.generation_id or not state.receipt_digest,
         "MISSING_GENERATION_BINDING", ""),
        (state.retrieval_mode != "semantic", "SEMANTIC_BACKEND_UNAVAILABLE", ""),
        (state.replica_binding == _EMPTY_REPLICA_BINDING,
         "HOLOINDEX_QUERY_SERVICE_BINDING_MISMATCH",
         "query_replica_binding_mismatch"),
    )


def _apply_response_contract(
    state: _OwnerResponseState, payload: Mapping[str, Any],
    expected_head: str, repo_root: Path,
) -> None:
    contract_valid = bool(
        payload.get("schema_version") == "holoindex_query_service.v1"
        and payload.get("source") == "holoindex"
        and payload.get("no_holoindex_reindex_performed") is True
    )
    success_contract_valid = bool(
        contract_valid
        and state.freshness == "CURRENT"
        and payload.get("index_gap_detected") is False
        and not state.stale_reasons
        and not payload.get("error")
        and isinstance(payload.get("raw_result"), Mapping)
    )
    if not contract_valid:
        state.ok = False
        state.error = "HOLOINDEX_QUERY_SERVICE_CONTRACT_INVALID"
        state.stale_reasons.append("owner_response_contract_invalid")
    checks = _response_contract_checks(
        state, success_contract_valid=success_contract_valid,
        expected_head=expected_head, repo_root=repo_root,
    )
    for failed, failure_code, reason in checks:
        if state.ok and failed:
            state.ok = False
            state.error = failure_code
            if reason:
                state.stale_reasons.append(reason)


def _normalized_response(
    *,
    payload: Mapping[str, Any],
    repo_root: Path,
    expected_head: str,
    query: str,
    started: float,
    deadline: float,
) -> Mapping[str, Any]:
    state = _response_state(payload)
    _apply_response_contract(state, payload, expected_head, repo_root)
    raw_hits = payload.get("hits")
    hits = (
        [dict(item) for item in raw_hits if isinstance(item, Mapping)]
        if isinstance(raw_hits, list)
        else []
    )
    if state.ok:
        repository_error = _post_query_repository_error(
            repo_root, expected_head, deadline
        )
        if repository_error:
            state.ok = False
            state.error = repository_error
            state.stale_reasons.append("repository_state_changed_during_query")
    if not state.ok and state.freshness == "CURRENT":
        state.freshness = "STALE"
    if not state.ok and not state.stale_reasons:
        state.stale_reasons.append("holoindex_owner_query_failed")
    replica_binding = dict(zip(_REPLICA_PUBLIC_FIELDS, state.replica_binding))
    return {
        "ok": state.ok,
        "source": "holoindex_owner_service",
        "query": query,
        "freshness": state.freshness,
        "hits": hits,
        "raw_result": state.raw_result,
        "error": state.error,
        "latency_ms": int((time.monotonic() - started) * 1000),
        "index_gap_detected": bool(state.stale_reasons or not state.ok),
        "stale_reasons": list(dict.fromkeys(state.stale_reasons)),
        "freshness_generation_id": state.generation_id,
        "freshness_receipt_digest": state.receipt_digest,
        "freshness_receipt_path": "",
        "repo_head_sha": state.repo_head_sha,
        "repo_root_digest": state.repo_root_digest,
        "retrieval_mode": state.retrieval_mode,
        "no_holoindex_reindex_performed": True,
        **replica_binding,
    }


def _transport_configuration(
    *,
    service_url: str | None,
    service_token: str | None,
    query: str,
    started: float,
) -> tuple[str, str, Mapping[str, Any] | None]:
    configured_url = (
        service_url
        if service_url is not None
        else os.getenv(HOLOINDEX_QUERY_SERVICE_URL_ENV, "")
    )
    try:
        endpoint = _endpoint(configured_url)
    except ValueError as exc:
        return "", "", _failure(query=query, started=started, error=str(exc))
    if not endpoint:
        return "", "", _failure(
            query=query,
            started=started,
            error="HOLOINDEX_QUERY_SERVICE_URL_MISSING",
        )
    token, token_error = _service_token(service_token)
    if token_error:
        return "", "", _failure(
            query=query,
            started=started,
            error=token_error,
        )
    return endpoint, token, None


def _query_context(
    *,
    repo_root: Path,
    query: str,
    service_url: str | None,
    service_token: str | None,
    timeout_seconds: float,
    started: float,
) -> tuple[_OwnerQueryContext | None, Mapping[str, Any] | None]:
    try:
        requested_budget = float(timeout_seconds)
        if not math.isfinite(requested_budget) or requested_budget <= 0:
            raise ValueError
        budget = min(requested_budget, 60.0)
    except (TypeError, ValueError):
        return None, _failure(
            query=query,
            started=started,
            error="HOLOINDEX_QUERY_TIMEOUT_INVALID",
        )
    endpoint, token, failure = _transport_configuration(
        service_url=service_url,
        service_token=service_token,
        query=query,
        started=started,
    )
    if failure:
        return None, failure
    deadline = started + budget
    repository_state = _repository_state_with_budget(
        repo_root,
        deadline - time.monotonic(),
    )
    if repository_state is None or time.monotonic() >= deadline:
        return None, _failure(
            query=query,
            started=started,
            error="HOLOINDEX_QUERY_DEADLINE_EXCEEDED",
        )
    if not repository_state.proven_clean:
        return None, _failure(
            query=query,
            started=started,
            error=repository_state.error
            or "HOLOINDEX_REPOSITORY_STATE_UNAVAILABLE",
        )
    return _OwnerQueryContext(
        repo_root=repo_root,
        query=query,
        endpoint=endpoint,
        token=token,
        expected_head=repository_state.head_sha,
        expected_root_digest=repository_root_digest(repo_root),
        started=started,
        deadline=deadline,
    ), None


def _execute_owner_request(
    context: _OwnerQueryContext,
    *,
    limit: int,
) -> tuple[Mapping[str, Any] | None, Mapping[str, Any] | None]:
    request = Request(
        context.endpoint,
        data=_request_payload(
            query=context.query,
            limit=limit,
            expected_head=context.expected_head,
            expected_root_digest=context.expected_root_digest,
        ),
        headers={
            "Authorization": f"Bearer {context.token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        return _read_payload(
            request,
            deadline=context.deadline,
        ), None
    except HTTPError as exc:
        try:
            error_payload = _http_error_payload(
                exc,
                deadline=context.deadline,
            )
        except TimeoutError as timeout_exc:
            return None, _failure(
                query=context.query,
                started=context.started,
                error=str(timeout_exc),
            )
        if error_payload is not None:
            return error_payload, None
        return None, _failure(
            query=context.query,
            started=context.started,
            error=f"HOLOINDEX_QUERY_SERVICE_HTTP_{exc.code}",
        )
    except (OSError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return None, _failure(
            query=context.query,
            started=context.started,
            error=str(exc) or type(exc).__name__,
        )


def query_holoindex_owner(
    *,
    repo_root: Path,
    query: str,
    limit: int,
    service_url: str | None = None,
    service_token: str | None = None,
    timeout_seconds: float = 15.0,
) -> Mapping[str, Any]:
    """Execute one bounded, generation-bound loopback query."""

    started = time.monotonic()
    query_text = str(query or "")
    context, failure = _query_context(
        repo_root=repo_root,
        query=query_text,
        service_url=service_url,
        service_token=service_token,
        timeout_seconds=timeout_seconds,
        started=started,
    )
    if failure or context is None:
        return failure or _failure(
            query=query_text,
            started=started,
            error="HOLOINDEX_QUERY_PREFLIGHT_FAILED",
        )
    payload, failure = _execute_owner_request(context, limit=limit)
    if failure or payload is None:
        return failure or _failure(
            query=query_text,
            started=started,
            error="HOLOINDEX_QUERY_SERVICE_INVALID_RESPONSE",
        )
    return _normalized_response(
        payload=payload,
        repo_root=repo_root,
        expected_head=context.expected_head,
        query=query_text,
        started=started,
        deadline=context.deadline,
    )


__all__ = [
    "HOLOINDEX_QUERY_SERVICE_TOKEN_ENV",
    "HOLOINDEX_QUERY_SERVICE_URL_ENV",
    "MAX_HOLOINDEX_SERVICE_RESPONSE_BYTES",
    "query_holoindex_owner",
]
