#!/usr/bin/env python3
"""Read-only, generation-bound HoloIndex query owner service.

WSP 97 truth boundary: success proves all seven baseline collections at the
caller-supplied repository HEAD both before and after semantic retrieval.
Lexical fallback is never represented as semantic evidence.
"""

from __future__ import annotations

import math
import os
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from holo_index.freshness_receipt import (
    evaluate_freshness_for_paths,
    freshness_receipt_path,
    load_freshness_receipt,
)
from holo_index.repository_state import read_repository_state, repository_root_digest
from holo_index.retrieval_runtime_binding import (
    loaded_retrieval_ranker_digest,
    loaded_retrieval_runtime_root,
)
from holo_index.query_receipt import digest_json
from holo_index.storage_contract import resolve_holoindex_ssd_path
from .reddog_holoindex_acceptance_guards import StoreProof
from .reddog_holoindex_query_replica_descriptor import ActiveQueryReplicaBinding
from .holo_query_service_replica import (
    build_query_replica_runtime,
    prepare_query_backend,
)
from .reddog_holoindex_runtime_environment_binding import (
    OWNER_STARTUP_FORCED_ENVIRONMENT,
    QUERY_RUNTIME_FORCED_ENVIRONMENT,
    RuntimeEnvironmentBindingError,
    exact_runtime_closure_verified,
    runtime_environment_manifest,
)
from .holo_query_service_request import (
    ALLOWED_DOC_TYPE_FILTERS,
    EXPECTED_ROOT_DIGEST_PATTERN,
    EXPECTED_SHA_PATTERN,
    validate_payload as _validate_payload,
)
from .holo_query_freshness_gate import (
    BASELINE_COLLECTIONS,
    BASELINE_FRESHNESS_PATHS,
    FreshnessSnapshot as _FreshnessSnapshot,
    HoloQueryFreshnessGate as _FreshnessGate,
    maintenance_reason_for_error,
)
from .holo_query_service_response import (
    build_response as _response,
    failure_reason as _failure_reason,
    flatten_hits as _flatten_hits,  # noqa: F401 - legacy test/import surface
    semantic_canary_empty_response as _empty_canary_response,
)
from .holo_query_transport import MIN_BEARER_TOKEN_CHARS


SCHEMA_VERSION = "holoindex_query_service.v1"
QUERY_PATH, HEALTH_PATH = "/holoindex/v1/query", "/holoindex/v1/health"
TOKEN_ENV = "HOLOINDEX_QUERY_SERVICE_TOKEN"
TOKEN_TOO_SHORT_ERROR = "HOLOINDEX_QUERY_SERVICE_TOKEN_TOO_SHORT"
DEFAULT_BIND_HOST, DEFAULT_PORT = "127.0.0.1", 8127
DEFAULT_LIMIT, MAX_LIMIT = 8, 50
MAX_QUERY_CHARS, MAX_REQUEST_BYTES = 4_096, 16_384
DEFAULT_QUERY_TIMEOUT_SECONDS, MAX_QUERY_TIMEOUT_SECONDS = 15.0, 30.0
DEFAULT_STARTUP_WARMUP_TIMEOUT_SECONDS = 270.0
MAX_STARTUP_WARMUP_TIMEOUT_SECONDS = 300.0

def _default_backend_factory(ssd_path: Path) -> Any:
    from holo_index.core.holo_index import HoloIndex
    return HoloIndex(ssd_path=ssd_path, quiet=True)


def validate_bind_host(host: str) -> str:
    """Accept only the Phase-1 literal IPv4 loopback binding."""
    normalized = str(host or "").strip().lower()
    if normalized != DEFAULT_BIND_HOST:
        raise ValueError("HOLOINDEX_QUERY_SERVICE_LOOPBACK_REQUIRED")
    return normalized


def _validated_service_bounds(
    query_timeout_seconds: float,
    startup_warmup_timeout_seconds: float,
    max_query_chars: int,
    max_request_bytes: int,
    max_limit: int,
) -> tuple[float, float, int, int, int]:
    """Normalize and validate the owner's public resource bounds."""
    timeout = float(query_timeout_seconds)
    warmup_timeout = float(startup_warmup_timeout_seconds)
    if not math.isfinite(timeout) or not 0 < timeout <= MAX_QUERY_TIMEOUT_SECONDS:
        raise ValueError("query_timeout_seconds must be > 0 and <= 30")
    if (
        not math.isfinite(warmup_timeout)
        or not 0 < warmup_timeout <= MAX_STARTUP_WARMUP_TIMEOUT_SECONDS
    ):
        raise ValueError(
            "startup_warmup_timeout_seconds must be > 0 and <= 300"
        )
    query_chars, request_bytes, result_limit = (
        int(max_query_chars), int(max_request_bytes), int(max_limit)
    )
    if min(query_chars, request_bytes, result_limit) <= 0:
        raise ValueError("request bounds must be positive")
    if result_limit > MAX_LIMIT:
        raise ValueError("max_limit must be <= 50")
    return timeout, warmup_timeout, query_chars, request_bytes, result_limit


def _captured_bearer_token(explicit_token: str | None) -> str:
    environment_token = os.environ.pop(TOKEN_ENV, "")
    selected = environment_token if explicit_token is None else explicit_token
    return str(selected).strip()


def _new_owner_executor() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(
        max_workers=1, thread_name_prefix="holoindex-query-owner"
    )


def _freshness_gate(
    repo_root: Path, ssd_path: Path, receipt_path: Path,
    receipt_loader: Callable[[Path], Any] | None,
    freshness_evaluator: Callable[..., Any] | None,
    maintenance_probe: Callable[[Path], Any] | None,
) -> _FreshnessGate:
    return _FreshnessGate(
        repo_root, ssd_path, receipt_path,
        receipt_loader or load_freshness_receipt,
        freshness_evaluator or evaluate_freshness_for_paths,
        maintenance_probe,
    )


def _service_storage_paths(
    repo_root: Path | str, canonical_input: Path | str | None,
) -> tuple[Path, Path, Path]:
    root = Path(repo_root).resolve(strict=False)
    canonical = resolve_holoindex_ssd_path(canonical_input)
    return root, canonical, freshness_receipt_path(canonical)


def _owner_runtime_environment(
    replica: Any, backend_factory: Callable[[Path], Any] | None,
) -> tuple[str, str, bool]:
    ranker_digest = loaded_retrieval_ranker_digest()
    manifest = runtime_environment_manifest(
        source_root=loaded_retrieval_runtime_root(),
        ranker_digest=ranker_digest,
        replica_binding=replica.public_binding,
        replica_artifacts=(replica.binding.artifacts if replica.binding else ()),
        require_complete_replica_binding=backend_factory is None,
        required_environment=(
            {**OWNER_STARTUP_FORCED_ENVIRONMENT, **QUERY_RUNTIME_FORCED_ENVIRONMENT}
            if backend_factory is None else None
        ),
    )
    return ranker_digest, digest_json(manifest), exact_runtime_closure_verified(manifest)


def _service_replica_runtime(
    *, repo_root: Path, canonical_ssd_path: Path,
    proof: StoreProof | None,
    injected: Callable[[], ActiveQueryReplicaBinding] | None,
    backend_factory: Callable[[Path], Any] | None,
) -> Any:
    return build_query_replica_runtime(
        repo_root=repo_root, canonical_ssd_path=canonical_ssd_path,
        proof=proof, injected=injected, require_replica=backend_factory is None,
    )


def _required_owner_runtime_environment(
    replica: Any, backend_factory: Callable[[Path], Any] | None,
) -> tuple[str, str, bool]:
    try:
        return _owner_runtime_environment(replica, backend_factory)
    except RuntimeEnvironmentBindingError:
        raise ValueError("HOLOINDEX_RUNTIME_ENVIRONMENT_UNAVAILABLE") from None


class HoloIndexQueryOwnerService:
    """Singleton, serialized owner for generation-pinned semantic queries."""

    def __init__(
        self, *, repo_root: Path | str,
        ssd_path: Path | str | None = None,
        canonical_ssd_path: Path | str | None = None,
        query_replica_root_proof: StoreProof | None = None,
        backend_factory: Callable[[Path], Any] | None = None,
        _replica_verifier_for_test: Callable[[], ActiveQueryReplicaBinding] | None = None,
        receipt_loader: Callable[[Path], Any] | None = None,
        freshness_evaluator: Callable[..., Any] | None = None,
        repository_state_reader: Callable[[Path], Any] | None = None,
        maintenance_probe: Callable[[Path], Any] | None = None,
        bearer_token: str | None = None, query_timeout_seconds: float = DEFAULT_QUERY_TIMEOUT_SECONDS,
        startup_warmup_timeout_seconds: float = DEFAULT_STARTUP_WARMUP_TIMEOUT_SECONDS,
        max_query_chars: int = MAX_QUERY_CHARS, max_request_bytes: int = MAX_REQUEST_BYTES,
        max_limit: int = MAX_LIMIT,
    ) -> None:
        timeout, warmup_timeout, query_chars, request_bytes, result_limit = (
            _validated_service_bounds(
                query_timeout_seconds, startup_warmup_timeout_seconds,
                max_query_chars, max_request_bytes, max_limit,
            )
        )
        canonical_input = canonical_ssd_path if canonical_ssd_path is not None else ssd_path
        self.repo_root, self.canonical_ssd_path, self.receipt_path = _service_storage_paths(
            repo_root, canonical_input
        )
        self.ssd_path = self.canonical_ssd_path  # compatibility: freshness authority
        self.query_timeout_seconds, self.startup_warmup_timeout_seconds = timeout, warmup_timeout
        self.max_query_chars, self.max_request_bytes = query_chars, request_bytes
        self.max_limit = result_limit
        self._bearer_token = _captured_bearer_token(bearer_token)
        self._factory = backend_factory or _default_backend_factory
        self._replica = _service_replica_runtime(
            repo_root=self.repo_root, canonical_ssd_path=self.canonical_ssd_path,
            proof=query_replica_root_proof, injected=_replica_verifier_for_test,
            backend_factory=backend_factory,
        )
        self.query_ssd_path = self._replica.query_ssd_path
        (self.retrieval_runtime_ranker_digest, self.runtime_environment_digest,
         self.runtime_environment_exact_closure_verified) = _required_owner_runtime_environment(
            self._replica, backend_factory)
        self._repository_state_reader = repository_state_reader or read_repository_state
        self._freshness = _freshness_gate(
            self.repo_root, self.canonical_ssd_path, self.receipt_path,
            receipt_loader, freshness_evaluator, maintenance_probe,
        )
        self._backend: Any | None = None
        self._backend_lock, self._request_lock = threading.Lock(), threading.Lock()
        self._poisoned, self._warmed = threading.Event(), threading.Event()
        self._executor = _new_owner_executor()

    def _verify_replica_binding(self) -> ActiveQueryReplicaBinding | None:
        return self._replica.verify()

    @property
    def replica_public_binding(self) -> Mapping[str, str]:
        return self._replica.public_binding

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
        if not self._request_lock.acquire(blocking=False):
            return
        try:
            backend, self._backend = self._backend, None
            close = getattr(backend, "close", None)
            if callable(close):
                close()
        finally:
            self._request_lock.release()

    def authorization_error(self, authorization: str | None) -> str:
        expected = self._bearer_token
        if not expected:
            return "AUTH_NOT_CONFIGURED"
        if len(expected) < MIN_BEARER_TOKEN_CHARS:
            return TOKEN_TOO_SHORT_ERROR
        scheme, separator, supplied = str(authorization or "").strip().partition(" ")
        if not separator or scheme.lower() != "bearer" or not supplied.strip():
            return "UNAUTHORIZED"
        return "" if secrets.compare_digest(supplied.strip(), expected) else "UNAUTHORIZED"

    def _get_backend(self) -> Any:
        if self._backend is not None:
            return self._backend
        with self._backend_lock:
            if self._backend is None:
                self._backend = prepare_query_backend(self._replica, self._factory)
        return self._backend

    def _search(self, query: str, limit: int, doc_type: str) -> Any:
        return self._get_backend().search(query, limit=limit, doc_type_filter=doc_type)

    def _run(
        self,
        function: Callable[..., Any],
        *args: Any,
        timeout_seconds: float | None = None,
    ) -> Any:
        timeout = (
            self.query_timeout_seconds
            if timeout_seconds is None
            else float(timeout_seconds)
        )
        if timeout <= 0:
            raise FutureTimeoutError
        future = self._executor.submit(function, *args)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            # Python threads cannot be safely cancelled. The timed-out call may
            # still own backend state, so this process must never reuse it.
            self._poisoned.set()
            raise

    def _poison_failure(
        self,
        *,
        query: str = "",
        started: float | None = None,
    ) -> dict[str, Any]:
        return self._failure(
            "QUERY_OWNER_POISONED",
            query=query,
            reasons=("backend_timeout_owner_poisoned",),
            started=started,
        )

    def _failure(
        self,
        error: str,
        *,
        query: str = "",
        snapshot: _FreshnessSnapshot | None = None,
        reasons: Sequence[str] = (),
        raw: Mapping[str, Any] | None = None,
        mode: str = "unknown",
        started: float | None = None,
    ) -> dict[str, Any]:
        maintenance_reason = maintenance_reason_for_error(error)
        failure_reasons = list(reasons)
        if maintenance_reason:
            failure_reasons.append(maintenance_reason)
        if snapshot is not None:
            failure_reasons.extend(snapshot.stale_reasons)
        if not failure_reasons:
            failure_reasons.append(_failure_reason(error))
        response_binding = dict(snapshot.binding if snapshot else {})
        response_binding.update(self.replica_public_binding)
        return _response(
            ok=False, query=query,
            freshness=snapshot.freshness if snapshot else "UNKNOWN",
            error=error,
            reasons=failure_reasons,
            binding=response_binding,
            retrieval_runtime_ranker_digest=(
                self.retrieval_runtime_ranker_digest
            ),
            runtime_environment_digest=self.runtime_environment_digest,
            runtime_environment_exact_closure_verified=(
                self.runtime_environment_exact_closure_verified
            ),
            raw=raw, mode=mode,
            latency_ms=int((time.monotonic() - started) * 1000) if started else 0,
        )

    def _auth_failure(self, error: str, *, query: str = "") -> dict[str, Any]:
        return self._failure(error, query=query)

    def handle_query(
        self,
        payload: Any,
        *,
        authorization: str | None,
        request_size: int | None = None,
    ) -> Mapping[str, Any]:
        return _handle_query(self, payload, authorization, request_size)

    def handle_health(self, *, authorization: str | None) -> Mapping[str, Any]:
        return _handle_health(self, authorization)


def _handle_query(
    owner: HoloIndexQueryOwnerService,
    payload: Any,
    authorization: str | None,
    request_size: int | None,
) -> Mapping[str, Any]:
    started = time.monotonic()
    deadline = started + owner.query_timeout_seconds
    auth_error = owner.authorization_error(authorization)
    if auth_error:
        return owner._failure(auth_error, started=started)
    if owner._poisoned.is_set():
        return owner._poison_failure(started=started)
    request, error = _validate_payload(
        payload, request_size=request_size,
        max_request_bytes=owner.max_request_bytes,
        max_query_chars=owner.max_query_chars, max_limit=owner.max_limit,
    )
    query = str(payload.get("query") or "") if isinstance(payload, Mapping) else ""
    if error or request is None:
        return owner._failure(
            error or "INVALID_REQUEST", query=query, started=started
        )
    if request["expected_repo_root_digest"] and request[
        "expected_repo_root_digest"
    ] != repository_root_digest(owner.repo_root):
        return owner._failure(
            "REPO_ROOT_MISMATCH", query=query, started=started
        )
    remaining = max(0.0, deadline - time.monotonic())
    if not owner._request_lock.acquire(timeout=remaining):
        return owner._failure(
            "QUERY_QUEUE_TIMEOUT", query=query, started=started
        )
    try:
        if owner._poisoned.is_set():
            return owner._poison_failure(query=query, started=started)
        from .holo_query_semantic_proof import run_semantic_proof

        return run_semantic_proof(
            owner, query=request["query"], limit=request["limit"],
            doc_type=request["doc_type_filter"],
            expected_sha=request["expected_repo_head_sha"], started=started,
            deadline=deadline,
        )
    finally:
        owner._request_lock.release()


def _health_result(
    owner: HoloIndexQueryOwnerService,
    authorization: str | None,
) -> Mapping[str, Any]:
    auth_error = owner.authorization_error(authorization)
    if auth_error:
        return owner._failure(auth_error)
    if owner._poisoned.is_set():
        return owner._poison_failure()
    if not owner._request_lock.acquire(blocking=False):
        return owner._failure("OWNER_BUSY")
    try:
        if owner._poisoned.is_set():
            return owner._poison_failure()
        from .holo_query_semantic_proof import repository_proof, run_semantic_proof

        started = time.monotonic()
        canary_budget = (
            owner.query_timeout_seconds
            if owner._warmed.is_set()
            else owner.startup_warmup_timeout_seconds
        )
        deadline = started + canary_budget
        expected_sha, failure = repository_proof(
            owner, "", query="", started=started, deadline=deadline
        )
        if failure:
            return failure
        if not EXPECTED_SHA_PATTERN.fullmatch(expected_sha):
            return owner._failure("HEALTH_UNAVAILABLE")
        result = run_semantic_proof(
            owner, query="HoloIndex semantic readiness canary", limit=1,
            doc_type="all", expected_sha=expected_sha, started=started,
            deadline=deadline,
        )
    finally:
        owner._request_lock.release()
    if result.get("ok") is not True:
        return result
    if not result.get("hits"):
        return _empty_canary_response(result)
    owner._warmed.set()
    return {**result, "query": "", "hits": [], "raw_result": {}}


def _handle_health(
    owner: HoloIndexQueryOwnerService,
    authorization: str | None,
) -> Mapping[str, Any]:
    result = _health_result(owner, authorization)
    return {
        **result,
        "status": "ready" if result["ok"] else "unavailable",
        "loopback_only": True,
    }


def create_holo_query_app(service: HoloIndexQueryOwnerService | None = None) -> Any:
    from .holo_query_service_http import create_holo_query_app as create_app
    return create_app(service)


def create_stdlib_server(
    service: HoloIndexQueryOwnerService,
    *,
    host: str = DEFAULT_BIND_HOST,
    port: int = DEFAULT_PORT,
) -> Any:
    from .holo_query_service_http import create_stdlib_server as create_server
    return create_server(service, host=host, port=port)


def main(argv: Sequence[str] | None = None) -> int:
    from .holo_query_service_http import main as http_main
    return http_main(argv)


def __getattr__(name: str) -> Any:
    if name in {"FastAPI", "app"}:
        from . import holo_query_service_http
        return getattr(holo_query_service_http, name)
    raise AttributeError(name)


__all__ = [
    "ALLOWED_DOC_TYPE_FILTERS", "BASELINE_COLLECTIONS",
    "BASELINE_FRESHNESS_PATHS", "DEFAULT_BIND_HOST",
    "DEFAULT_STARTUP_WARMUP_TIMEOUT_SECONDS", "HEALTH_PATH",
    "HoloIndexQueryOwnerService", "MAX_LIMIT", "MAX_QUERY_CHARS",
    "MAX_REQUEST_BYTES", "MAX_STARTUP_WARMUP_TIMEOUT_SECONDS",
    "MIN_BEARER_TOKEN_CHARS", "QUERY_PATH",
    "TOKEN_ENV", "TOKEN_TOO_SHORT_ERROR", "app",  # noqa: F822
    "create_holo_query_app", "create_stdlib_server", "main",
    "validate_bind_host",
]

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
