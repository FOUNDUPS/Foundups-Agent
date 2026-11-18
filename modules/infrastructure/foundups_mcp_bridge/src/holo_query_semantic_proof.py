"""Generation-pinned semantic proof orchestration for the HoloIndex owner."""

from __future__ import annotations

import time
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any, Callable, Mapping

from .holo_query_freshness_gate import (
    FreshnessSnapshot,
    snapshot_error,
)
from .holo_query_embedding_space_proof import (
    backend_generation_failure,
    embedding_space_evidence,
    pin_backend_generation,
)
from .holo_query_service_response import (
    semantic_success_response as _success_response,
)


PRODUCER_FAILURE_CODES = frozenset({
    "HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE",
    "HOLOINDEX_TIER0_INCOMPLETE",
    "HOLOINDEX_TIER0_LOOKUP_FAILED",
})


def _producer_failure_code(raw: Mapping[str, Any]) -> str:
    """Allow only stable producer codes across the owner trust boundary."""
    value = raw.get("metadata")
    metadata = value if isinstance(value, Mapping) else {}
    error = str(metadata.get("error") or "")
    return (
        error if error in PRODUCER_FAILURE_CODES
        else "SEMANTIC_BACKEND_UNAVAILABLE"
    )


def _semantic_evidence(
    owner: Any,
    result: Any,
) -> tuple[Mapping[str, Any], str, bool]:
    raw = result if isinstance(result, Mapping) else {}
    value = raw.get("metadata")
    metadata = value if isinstance(value, Mapping) else {}
    raw_mode = str(metadata.get("retrieval_mode") or "unknown").lower()
    backend_mode = str(getattr(owner._backend, "retrieval_mode", "unknown")).lower()
    embedding_backend = str(metadata.get("embedding_backend") or "").strip().lower()
    invalid_backends = {"", "none", "unknown", "lexical", "failed"}
    valid = bool(
        isinstance(result, Mapping)
        and not metadata.get("error")
        and raw_mode == "semantic"
        and backend_mode == "semantic"
        and embedding_backend not in invalid_backends
    )
    return raw, raw_mode, valid


def _timed_proof_call(
    owner: Any,
    function: Callable[..., Any],
    *args: Any,
    deadline: float,
) -> tuple[Any, bool]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return None, False
    try:
        return owner._run(function, *args, timeout_seconds=remaining), False
    except FutureTimeoutError:
        return None, True


def _deadline_failure(
    owner: Any,
    *,
    query: str,
    started: float,
    snapshot: FreshnessSnapshot | None = None,
    poisoned: bool,
    backend: bool = False,
) -> Mapping[str, Any]:
    reason = (
        "backend_timeout_owner_poisoned"
        if backend and poisoned
        else "proof_timeout_owner_poisoned"
        if poisoned
        else "query_deadline_exceeded"
    )
    return owner._failure(
        "QUERY_TIMEOUT",
        query=query,
        snapshot=snapshot,
        reasons=(reason,),
        started=started,
    )


def repository_proof(
    owner: Any,
    expected_sha: str,
    *,
    query: str,
    started: float,
    snapshot: FreshnessSnapshot | None = None,
    raw: Mapping[str, Any] | None = None,
    mode: str = "unknown",
    deadline: float,
) -> tuple[str, Mapping[str, Any] | None]:
    value, poisoned = _timed_proof_call(
        owner,
        owner._freshness.repository_error,
        owner._repository_state_reader,
        owner.repo_root,
        expected_sha,
        deadline=deadline,
    )
    if value is None:
        return "", _deadline_failure(
            owner,
            query=query,
            started=started,
            snapshot=snapshot,
            poisoned=poisoned,
        )
    error, actual_sha = value
    if not error:
        return actual_sha, None
    return "", owner._failure(
        error,
        query=query,
        snapshot=snapshot,
        raw=raw,
        mode=mode,
        started=started,
    )


def _freshness_snapshot(
    owner: Any,
    expected_sha: str,
    *,
    query: str,
    started: float,
    deadline: float,
) -> tuple[FreshnessSnapshot | None, Mapping[str, Any] | None]:
    snapshot, poisoned = _timed_proof_call(
        owner,
        owner._freshness.snapshot,
        expected_sha,
        deadline=deadline,
    )
    if snapshot is None:
        return None, _deadline_failure(
            owner,
            query=query,
            started=started,
            poisoned=poisoned,
        )
    return snapshot, None


def _generation_change_reasons(
    before: FreshnessSnapshot,
    after: FreshnessSnapshot,
) -> tuple[str, ...]:
    fields = (
        ("freshness_generation_id", "freshness_generation_changed_during_query"),
        ("freshness_receipt_digest", "freshness_receipt_digest_changed_during_query"),
        ("repo_head_sha", "repo_head_sha_changed_during_query"),
    )
    return tuple(
        reason
        for field, reason in fields
        if before.binding.get(field) != after.binding.get(field)
    )


def _pre_query_proof(
    owner: Any,
    *,
    expected_sha: str,
    query: str,
    started: float,
    deadline: float,
) -> tuple[FreshnessSnapshot | None, Mapping[str, Any] | None]:
    try:
        owner._verify_replica_binding()
    except Exception:
        return None, owner._failure(
            "QUERY_REPLICA_INVALID", query=query, started=started
        )
    _actual_sha, failure = repository_proof(
        owner,
        expected_sha,
        query=query,
        started=started,
        deadline=deadline,
    )
    if failure:
        return None, failure
    before, failure = _freshness_snapshot(
        owner,
        expected_sha,
        query=query,
        started=started,
        deadline=deadline,
    )
    if failure or before is None:
        return None, failure or owner._failure("STALE_INDEX", query=query)
    if not before.valid:
        return None, owner._failure(
            snapshot_error(before),
            query=query,
            snapshot=before,
            started=started,
        )
    pin_failure = backend_generation_failure(
        owner, before, query=query, started=started
    )
    if pin_failure:
        return None, pin_failure
    return before, None


def _execute_backend_search(
    owner: Any,
    *,
    query: str,
    limit: int,
    doc_type: str,
    before: FreshnessSnapshot,
    started: float,
    deadline: float,
) -> tuple[Any, Mapping[str, Any] | None]:
    try:
        result, poisoned = _timed_proof_call(
            owner, owner._search, query, limit, doc_type, deadline=deadline
        )
    except Exception:
        return None, owner._failure(
            "SEMANTIC_BACKEND_UNAVAILABLE",
            query=query,
            snapshot=before,
            started=started,
        )
    if result is None:
        return None, _deadline_failure(
            owner,
            query=query,
            snapshot=before,
            started=started,
            poisoned=poisoned,
            backend=True,
        )
    return result, None


def _semantic_deadline_failure(
    owner: Any,
    *,
    query: str,
    before: FreshnessSnapshot,
    raw: Mapping[str, Any],
    mode: str,
    started: float,
    deadline: float,
) -> Mapping[str, Any] | None:
    if time.monotonic() < deadline:
        return None
    return owner._failure(
        "QUERY_TIMEOUT",
        query=query,
        snapshot=before,
        raw=raw,
        mode=mode,
        started=started,
    )


def _semantic_search(
    owner: Any,
    *,
    query: str,
    limit: int,
    doc_type: str,
    before: FreshnessSnapshot,
    started: float,
    deadline: float,
) -> tuple[Mapping[str, Any] | None, str, Mapping[str, Any] | None]:
    result, search_failure = _execute_backend_search(
        owner,
        query=query,
        limit=limit,
        doc_type=doc_type,
        before=before,
        started=started,
        deadline=deadline,
    )
    if search_failure:
        return None, "unknown", search_failure
    raw, mode, semantic = _semantic_evidence(owner, result)
    pin_backend_generation(owner, before)
    if not semantic:
        return raw, mode, owner._failure(
            _producer_failure_code(raw),
            query=query,
            snapshot=before,
            raw=raw,
            mode=mode,
            started=started,
        )
    space_error, space_reasons = embedding_space_evidence(owner, raw, before)
    if space_error:
        return raw, mode, owner._failure(
            space_error,
            query=query,
            snapshot=before,
            reasons=space_reasons,
            raw=raw,
            mode=mode,
            started=started,
        )
    deadline_failure = _semantic_deadline_failure(
        owner, query=query, before=before, raw=raw, mode=mode,
        started=started, deadline=deadline,
    )
    return raw, mode, deadline_failure


def _final_generation_failure(
    owner: Any,
    before: FreshnessSnapshot,
    after: FreshnessSnapshot,
    context: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    proof_kwargs = {
        key: context[key]
        for key in ("query", "started", "raw", "mode", "deadline")
    }
    proof_kwargs["snapshot"] = after
    _actual_sha, failure = repository_proof(
        owner, str(context["expected_sha"]), **proof_kwargs
    )
    if failure:
        return failure
    changed = _generation_change_reasons(before, after)
    if changed:
        stale = FreshnessSnapshot(
            after.binding, "STALE", changed, False, after.embedding_spaces
        )
        return owner._failure(
            "GENERATION_CHANGED_DURING_QUERY",
            query=str(context["query"]),
            snapshot=stale,
            raw=context["raw"],
            mode=str(context["mode"]),
            started=float(context["started"]),
        )
    if time.monotonic() >= float(context["deadline"]):
        return _deadline_failure(
            owner,
            query=str(context["query"]),
            snapshot=after,
            started=float(context["started"]),
            poisoned=False,
        )
    return None


def _post_query_proof(
    owner: Any, *, expected_sha: str,
    query: str,
    before: FreshnessSnapshot,
    raw: Mapping[str, Any],
    mode: str,
    started: float,
    deadline: float,
) -> tuple[FreshnessSnapshot | None, Mapping[str, Any] | None]:
    context = {
        "expected_sha": expected_sha,
        "query": query,
        "started": started,
        "raw": raw,
        "mode": mode,
        "deadline": deadline,
    }
    _actual_sha, failure = repository_proof(
        owner, expected_sha, snapshot=before, **{k: v for k, v in context.items() if k != "expected_sha"}
    )
    if failure:
        return None, failure
    after, failure = _freshness_snapshot(
        owner,
        expected_sha,
        query=query,
        started=started,
        deadline=deadline,
    )
    if failure or after is None:
        return None, failure or owner._failure("STALE_INDEX", query=query)
    try:
        owner._verify_replica_binding()
    except Exception:
        return None, owner._failure(
            "QUERY_REPLICA_CHANGED", query=query, snapshot=after,
            raw=raw, mode=mode, started=started,
        )
    if not after.valid:
        return None, owner._failure(
            snapshot_error(after),
            query=query,
            snapshot=after,
            raw=raw,
            mode=mode,
            started=started,
        )
    failure = _final_generation_failure(owner, before, after, context)
    return (None, failure) if failure else (after, None)


def run_semantic_proof(
    owner: Any,
    *,
    query: str,
    limit: int,
    doc_type: str,
    expected_sha: str,
    started: float,
    deadline: float,
) -> Mapping[str, Any]:
    """Return success only after pre/post exact-generation semantic proof."""
    before, failure = _pre_query_proof(
        owner,
        expected_sha=expected_sha,
        query=query,
        started=started,
        deadline=deadline,
    )
    if failure or before is None:
        return failure or owner._failure("STALE_INDEX", query=query)
    raw, mode, failure = _semantic_search(
        owner,
        query=query,
        limit=limit,
        doc_type=doc_type,
        before=before,
        started=started,
        deadline=deadline,
    )
    if failure or raw is None:
        return failure or owner._failure("SEMANTIC_BACKEND_UNAVAILABLE", query=query)
    after, failure = _post_query_proof(
        owner,
        expected_sha=expected_sha,
        query=query,
        before=before,
        raw=raw,
        mode=mode,
        started=started,
        deadline=deadline,
    )
    if failure or after is None:
        return failure or owner._failure("STALE_INDEX", query=query)
    return _success_response(
        owner=owner,
        query=query, limit=limit, raw=raw, after=after, started=started
    )


__all__ = ["repository_proof", "run_semantic_proof"]
