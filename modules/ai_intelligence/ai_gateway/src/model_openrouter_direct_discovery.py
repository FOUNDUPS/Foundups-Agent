"""Bounded, explicit OpenRouter model-list discovery with durable receipts."""
from __future__ import annotations
import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)
from .model_provider_catalog_artifact_store import AtomicArtifactOps, ProviderCatalogArtifactStore
from .model_provider_catalog_snapshot import (
    MAX_RECORDS,
    MAX_RESPONSE_BYTES,
    DiscoveryInvocation,
    DiscoveryReceipt,
    ProviderCatalogCandidateSnapshot,
    admit_discovery_invocation,
    build_candidate_snapshot,
    build_discovery_receipt,
    candidate_snapshot_id,
    parse_and_sanitize_openrouter_catalog,
    rehydrate_discovery_invocation,
    sha256_bytes,
)
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
TOTAL_TIMEOUT_SECONDS = 15.0
REQUEST_ENVELOPE: Mapping[str, Any] = {
    "method": "GET",
    "url": OPENROUTER_MODELS_URL,
    "headers": {"Accept": "application/json"},
    "allow_redirects": False,
    "timeout_seconds": TOTAL_TIMEOUT_SECONDS,
    "max_response_bytes": MAX_RESPONSE_BYTES,
    "max_records": MAX_RECORDS,
    "body": None,
}
@dataclass(frozen=True)
class HTTPRequest:
    method: str
    url: str
    headers: Mapping[str, str]
    allow_redirects: bool
    timeout_seconds: float
    max_response_bytes: int
    max_records: int
    body: None = None
@dataclass(frozen=True)
class HTTPResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes
    redirected: bool = False
class AsyncHTTPProtocol(Protocol):
    async def fetch(self, request: HTTPRequest) -> HTTPResponse:
        """Fetch one bounded response without adding credentials."""
@dataclass(frozen=True)
class DiscoveryRunResult:
    receipt: DiscoveryReceipt
    candidate: ProviderCatalogCandidateSnapshot | None
    attempt_path: Path | None
    candidate_path: Path | None
class ResponseBodyTooLarge(ValueError):
    """Raised by transports before retaining an oversized response."""
class AioHTTPTransport:
    """Default transport with a total deadline and bounded streaming read."""
    async def fetch(self, request: HTTPRequest) -> HTTPResponse:
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=request.timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                request.url,
                headers=dict(request.headers),
                allow_redirects=request.allow_redirects,
                max_redirects=0,
            ) as response:
                body = bytearray()
                async for chunk in response.content.iter_chunked(64 * 1024):
                    if len(body) + len(chunk) > request.max_response_bytes:
                        raise ResponseBodyTooLarge("body_too_large")
                    body.extend(chunk)
                return HTTPResponse(
                    status=response.status,
                    headers=dict(response.headers),
                    body=bytes(body),
                    redirected=bool(response.history),
                )
async def discover_openrouter_model_catalog(
    invocation: DiscoveryInvocation | Mapping[str, Any],
    *,
    repo_root: Path | str,
    runtime_root: Path | str,
    attempt_path: Path | str,
    candidate_path: Path | str,
    transport: AsyncHTTPProtocol | None = None,
    clock_ms: Callable[[], int] | None = None,
    artifact_ops: AtomicArtifactOps | None = None,
) -> DiscoveryRunResult:
    """Perform one admitted refresh; no caller or scheduler invokes this implicitly."""
    clock = clock_ms or _clock_ms
    started = clock()
    item = _invocation(invocation)
    request_digest = _request_digest()
    call_id = _call_id(item.invocation_id, started)
    try:
        root, attempt_target, candidate_target = _validated_paths(repo_root, runtime_root, attempt_path, candidate_path)
        store = ProviderCatalogArtifactStore.create(repo_root=repo_root, runtime_root=root, ops=artifact_ops)
    except (OSError, ValueError):
        receipt = _receipt(item, call_id, request_digest, False, "BLOCKED_PRECALL",
                           "output_path_invalid", started, clock())
        return DiscoveryRunResult(receipt, None, None, None)
    try:
        admit_discovery_invocation(item, now_ms=started)
    except ValueError as error:
        receipt = _receipt(item, call_id, request_digest, False, "BLOCKED_PRECALL",
                           _admission_failure_reason(error), started, clock())
        _try_write(attempt_target, receipt.to_dict(), store)
        return DiscoveryRunResult(receipt, None, attempt_target, candidate_target)
    intent = _receipt(item, call_id, request_digest, False, "BLOCKED_PRECALL",
                      "precall_intent", started, started)
    try:
        _write(attempt_target, intent.to_dict(), store)
    except (OSError, ValueError):
        failed = _receipt(item, call_id, request_digest, False, "BLOCKED_PRECALL",
                          "precall_write_failed", started, clock())
        return DiscoveryRunResult(failed, None, attempt_target, candidate_target)
    armed = _receipt(item, call_id, request_digest, True, "INDETERMINATE",
                     "transport_pending", started, clock())
    try:
        _write(attempt_target, armed.to_dict(), store)
    except (OSError, ValueError):
        return DiscoveryRunResult(intent, None, attempt_target, candidate_target)
    return await _execute(
        item, call_id, request_digest, started, store,
        attempt_target, candidate_target, transport or AioHTTPTransport(), clock,
    )
async def _execute(
    invocation: DiscoveryInvocation,
    call_id: str,
    request_digest: str,
    started: int,
    store: ProviderCatalogArtifactStore,
    attempt_path: Path,
    candidate_path: Path,
    transport: AsyncHTTPProtocol,
    clock: Callable[[], int],
) -> DiscoveryRunResult:
    try:
        response = await transport.fetch(_request())
    except (asyncio.TimeoutError, TimeoutError):
        return _failed(
            invocation, call_id, request_digest, started, "transport_timeout",
            store, attempt_path, candidate_path, clock,
        )
    except ResponseBodyTooLarge:
        return _failed(
            invocation, call_id, request_digest, started, "body_too_large",
            store, attempt_path, candidate_path, clock,
        )
    except Exception:
        return _failed(
            invocation, call_id, request_digest, started, "transport_failed",
            store, attempt_path, candidate_path, clock,
        )
    try:
        response = _validated_response(response)
        rejected = _response_rejection(response)
    except Exception:
        return _failed(
            invocation, call_id, request_digest, started, "transport_failed",
            store, attempt_path, candidate_path, clock,
        )
    if rejected is not None:
        reason, body_digest, body_size = rejected
        return _failed(
            invocation, call_id, request_digest, started, reason,
            store, attempt_path, candidate_path, clock,
            http_status=response.status, response_body_digest=body_digest,
            response_byte_count=body_size,
        )
    return _normalize_and_persist(
        invocation, call_id, request_digest, started, response,
        store, attempt_path, candidate_path, clock,
    )
def _normalize_and_persist(
    invocation: DiscoveryInvocation,
    call_id: str,
    request_digest: str,
    started: int,
    response: HTTPResponse,
    store: ProviderCatalogArtifactStore,
    attempt_path: Path,
    candidate_path: Path,
    clock: Callable[[], int],
) -> DiscoveryRunResult:
    body_digest, body_size = sha256_bytes(response.body), len(response.body)
    try:
        payload, rejected_count, counts = parse_and_sanitize_openrouter_catalog(response.body)
    except ValueError as error:
        reason = str(error)
        if reason not in {
            "body_too_large", "json_invalid", "top_level_invalid",
            "record_limit_exceeded", "no_acceptable_records",
        }:
            reason = "json_invalid"
        return _failed(
            invocation, call_id, request_digest, started, reason,
            store, attempt_path, candidate_path, clock,
            http_status=response.status, response_body_digest=body_digest,
            response_byte_count=body_size,
        )
    return _persist_candidate(
        invocation, call_id, request_digest, started, response, payload,
        rejected_count, counts, store, attempt_path, candidate_path, clock,
    )
def _persist_candidate(
    invocation: DiscoveryInvocation, call_id: str, request_digest: str, started: int,
    response: HTTPResponse, payload: Mapping[str, Any], rejected_count: int,
    counts: Mapping[str, int], store: ProviderCatalogArtifactStore,
    attempt_path: Path, candidate_path: Path, clock: Callable[[], int],
) -> DiscoveryRunResult:
    body_digest, body_size = sha256_bytes(response.body), len(response.body)
    completed = max(started, clock())
    snapshot_id = candidate_snapshot_id(payload)
    receipt = _receipt(
        invocation, call_id, request_digest, True, "COMPLETED", "completed",
        started, completed, http_status=response.status,
        response_body_digest=body_digest, response_byte_count=body_size,
        candidate_snapshot_id=snapshot_id, accepted_record_count=len(payload["data"]),
        rejected_record_count=rejected_count, rejection_counts=counts,
    )
    candidate = build_candidate_snapshot(
        catalog_payload=payload, rejected_record_count=rejected_count,
        rejection_counts=counts, observed_at_ms=completed,
        observation_receipt=receipt,
    )
    try:
        _write(candidate_path, candidate.to_dict(), store)
    except (OSError, ValueError):
        return _failed(
            invocation, call_id, request_digest, started, "candidate_write_failed",
            store, attempt_path, candidate_path, clock,
            http_status=response.status, response_body_digest=body_digest,
            response_byte_count=body_size,
        )
    try:
        _write(attempt_path, receipt.to_dict(), store)
    except (OSError, ValueError):
        indeterminate = _receipt(
            invocation, call_id, request_digest, True, "INDETERMINATE",
            "terminal_receipt_write_failed", started, clock(),
            http_status=response.status, response_body_digest=body_digest,
            response_byte_count=body_size,
        )
        return DiscoveryRunResult(indeterminate, candidate, attempt_path, candidate_path)
    return DiscoveryRunResult(receipt, candidate, attempt_path, candidate_path)
def _failed(
    invocation: DiscoveryInvocation,
    call_id: str,
    request_digest: str,
    started: int,
    reason: str,
    store: ProviderCatalogArtifactStore,
    attempt_path: Path,
    candidate_path: Path,
    clock: Callable[[], int],
    **details: Any,
) -> DiscoveryRunResult:
    receipt = _receipt(
        invocation, call_id, request_digest, True, "FAILED", reason,
        started, clock(), **details,
    )
    if not _try_write(attempt_path, receipt.to_dict(), store):
        receipt = _receipt(
            invocation, call_id, request_digest, True, "INDETERMINATE",
            "terminal_receipt_write_failed", started, clock(), **details,
        )
    return DiscoveryRunResult(receipt, None, attempt_path, candidate_path)
def _response_rejection(response: HTTPResponse) -> tuple[str, str | None, int | None] | None:
    size = len(response.body)
    if size > MAX_RESPONSE_BYTES:
        return "body_too_large", None, None
    digest = sha256_bytes(response.body)
    if response.redirected and not 300 <= response.status < 400:
        return "redirect_history_rejected", digest, min(size, MAX_RESPONSE_BYTES)
    if 300 <= response.status < 400:
        return "redirect_rejected", digest, min(size, MAX_RESPONSE_BYTES)
    if response.status != 200:
        return "http_status_rejected", digest, min(size, MAX_RESPONSE_BYTES)
    content_type = _header(response.headers, "content-type").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        return "content_type_rejected", digest, min(size, MAX_RESPONSE_BYTES)
    return None
def _validated_response(value: Any) -> HTTPResponse:
    if type(value) is not HTTPResponse:
        raise ValueError("transport_failed")
    status, headers, body, redirected = value.status, value.headers, value.body, value.redirected
    if type(status) is not int or not 100 <= status <= 599:
        raise ValueError("transport_failed")
    if type(headers) is not dict or len(headers) > 64:
        raise ValueError("transport_failed")
    clean: dict[str, str] = {}
    for key, item in headers.items():
        if type(key) is not str or type(item) is not str:
            raise ValueError("transport_failed")
        if not 0 < len(key) <= 128 or len(item) > 4096 or _control_text(key + item):
            raise ValueError("transport_failed")
        clean[key] = item
    if type(body) is not bytes or type(redirected) is not bool:
        raise ValueError("transport_failed")
    return HTTPResponse(status, clean, body, redirected)
def _control_text(value: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in value)
def _receipt(
    invocation: DiscoveryInvocation,
    call_id: str,
    request_digest: str,
    attempted: bool,
    outcome: str,
    reason: str,
    started: int,
    completed: int,
    **details: Any,
) -> DiscoveryReceipt:
    return build_discovery_receipt(
        invocation=invocation, call_id=call_id,
        request_envelope_digest=request_digest, attempted=attempted,
        outcome=outcome, reason=reason, started_at_ms=started,
        completed_at_ms=max(started, completed), **details,
    )
def _validated_paths(
    repo_root: Path | str,
    runtime_root: Path | str,
    attempt_path: Path | str,
    candidate_path: Path | str,
) -> tuple[Path, Path, Path]:
    root = validate_runtime_root_path(runtime_root, repo_root=repo_root)
    attempt = validate_runtime_artifact_path(
        attempt_path, repo_root=repo_root, allowed_root=root
    )
    candidate = validate_runtime_artifact_path(
        candidate_path, repo_root=repo_root, allowed_root=root
    )
    if attempt == candidate:
        raise ValueError("runtime_artifact_paths_not_distinct")
    return root, attempt, candidate
def _write(path: Path, payload: Mapping[str, Any], store: ProviderCatalogArtifactStore) -> None:
    store.replace_text(path, json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
def _try_write(path: Path, payload: Mapping[str, Any], store: ProviderCatalogArtifactStore) -> bool:
    try:
        _write(path, payload, store)
        return True
    except (OSError, ValueError):
        return False
def _invocation(value: DiscoveryInvocation | Mapping[str, Any]) -> DiscoveryInvocation:
    if isinstance(value, DiscoveryInvocation):
        return rehydrate_discovery_invocation(value.to_dict())
    return rehydrate_discovery_invocation(value)
def _request() -> HTTPRequest:
    return HTTPRequest(
        method="GET", url=OPENROUTER_MODELS_URL,
        headers={"Accept": "application/json"}, allow_redirects=False,
        timeout_seconds=TOTAL_TIMEOUT_SECONDS,
        max_response_bytes=MAX_RESPONSE_BYTES,
        max_records=MAX_RECORDS,
    )
def _request_digest() -> str:
    encoded = json.dumps(
        REQUEST_ENVELOPE, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256_bytes(encoded)
def _admission_failure_reason(error: ValueError) -> str:
    reason = str(error)
    if reason in {"scheduled_invocation_not_due", "scheduled_invocation_expired"}:
        return reason
    return "invocation_invalid"
def _call_id(invocation_id: str, started: int) -> str:
    value = f"{invocation_id}\0{started}".encode("utf-8")
    return f"model_provider_catalog_discovery_call:{hashlib.sha256(value).hexdigest()}"
def _header(headers: Mapping[str, str], name: str) -> str:
    return next((str(value) for key, value in headers.items() if str(key).lower() == name), "")
def _clock_ms() -> int:
    return time.time_ns() // 1_000_000
__all__ = [
    "AioHTTPTransport", "AsyncHTTPProtocol", "DiscoveryRunResult", "HTTPRequest",
    "HTTPResponse", "OPENROUTER_MODELS_URL", "REQUEST_ENVELOPE",
    "ResponseBodyTooLarge", "discover_openrouter_model_catalog",
]
