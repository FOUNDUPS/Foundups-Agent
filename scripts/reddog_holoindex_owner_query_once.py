#!/usr/bin/env python3
"""One-shot generation-bound HoloIndex query bridge for the RedDog extension.

The extension sends one bounded semantic query on stdin. This adapter starts or
reuses the existing authenticated loopback owner, executes the query through
``query_holoindex_owner``, and returns only the owner's secret-free response.
It never indexes, mutates repository state, or exposes the owner bearer token.
"""

from __future__ import annotations

import json
import math
import sys
from threading import Lock
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from holo_index.query_receipt import (  # noqa: E402
    build_query_receipt,
    canonical_semantic_evidence,
)
from holo_index.query_admission import (  # noqa: E402
    ReadonlyQueryAdmission,
    rehydrate_canonical_freshness_proof,
)
from holo_index.storage_contract import resolve_holoindex_ssd_path  # noqa: E402
from holo_index.repository_state import repository_root_digest  # noqa: E402
from holo_index.cli.commands.bundle_json import build_wsp_memory_bundle  # noqa: E402
from holo_index.authority_worktree import (  # noqa: E402
    HoloIndexAuthoritySelection,
    resolve_holoindex_authority_root,
    resolve_holoindex_runtime_root,
)
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
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_replica_route import (  # noqa: E402
    QUERY_REPLICA_REQUIRED_ERROR,
    resolve_query_replica_owner_route,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_acquisition import (  # noqa: E402
    MAX_OWNER_ATTEMPTS,
    OWNER_OPERATION_TIMEOUT_SECONDS,
    OWNER_PORT_SHARD_COUNT,
    TRANSIENT_OWNER_ERRORS,
    build_owner_query_environment,
    owner_port_for_attempt as _owner_port_for_attempt,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_replica_binding import (  # noqa: E402
    parse_replica_binding,
)


MAX_QUERY_CHARS = 16_000
MAX_LIMIT = 20
MAX_MODULE_HINT_CHARS = 512
MAX_MUST_INCLUDE = 40
MAX_MUST_INCLUDE_CHARS = 1024
DEFAULT_OPERATION_TIMEOUT_SECONDS = OWNER_OPERATION_TIMEOUT_SECONDS
MAX_OPERATION_TIMEOUT_SECONDS = OWNER_OPERATION_TIMEOUT_SECONDS
_REQUEST_KEYS = frozenset({
    "query", "limit", "retrieval_mode", "include_bundle", "module_hint",
    "must_include", "bundle_only",
})
PROCESS_OWNED_STATUSES = frozenset({OWNER_STARTED, OWNER_REUSED})
_OWNER_LIFECYCLE_LOCK = Lock()
_REPLICA_PUBLIC_FIELDS = (
    "query_replica_descriptor_digest",
    "query_replica_generation_id",
    "query_replica_id",
    "query_replica_path_identity_digest",
)
OwnerHandoffResolver = Callable[[], tuple[str, str] | None]
AuthoritySelector = Callable[[Path], HoloIndexAuthoritySelection]
Preflight = Callable[..., ReadonlyQueryAdmission]


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


def _with_retry_telemetry(
    result: Mapping[str, Any],
    *,
    attempts: int,
    retry_reason: str,
) -> dict[str, Any]:
    return {
        **dict(result),
        "owner_attempts": attempts,
        "owner_retry_performed": attempts > 1,
        "owner_retry_reason": retry_reason,
    }


def _read_payload() -> Mapping[str, Any]:
    raw = sys.stdin.buffer.read()
    value = json.loads(raw.decode("utf-8-sig", errors="strict"))
    if not isinstance(value, Mapping):
        raise ValueError("payload_not_object")
    return value


@dataclass(frozen=True)
class _QueryRequest:
    query: str
    limit: int
    retrieval_mode: str
    include_bundle: bool
    module_hint: str
    must_include: tuple[str, ...]
    bundle_only: bool


@dataclass(frozen=True)
class _PreparedQuery:
    query: str
    limit: int
    selection: HoloIndexAuthoritySelection
    route_environment: Mapping[str, str]
    select_authority: AuthoritySelector
    ssd_path: Path
    bundle_fields: Mapping[str, Any] | None


def _bounded_request(payload: Mapping[str, Any]) -> tuple[_QueryRequest | None, str]:
    if any(not isinstance(key, str) or key not in _REQUEST_KEYS for key in payload):
        return None, "request_field_invalid"
    query = payload.get("query")
    if not isinstance(query, str) or not query.strip():
        return None, "query_required"
    query = query.strip()
    if len(query) > MAX_QUERY_CHARS:
        return None, "query_too_large"
    raw_limit = payload.get("limit", 5)
    if isinstance(raw_limit, bool):
        return None, "limit_invalid"
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return None, "limit_invalid"
    if limit < 1 or limit > MAX_LIMIT:
        return None, "limit_invalid"
    mode = payload.get("retrieval_mode", "semantic")
    if mode not in {"semantic", "lexical"}:
        return None, "retrieval_mode_invalid"
    include_bundle = payload.get("include_bundle", False)
    bundle_only = payload.get("bundle_only", False)
    if not isinstance(include_bundle, bool) or not isinstance(bundle_only, bool):
        return None, "bundle_flag_invalid"
    hint = payload.get("module_hint", "")
    if not isinstance(hint, str) or len(hint) > MAX_MODULE_HINT_CHARS:
        return None, "module_hint_invalid"
    raw_paths = payload.get("must_include", [])
    if not isinstance(raw_paths, list) or len(raw_paths) > MAX_MUST_INCLUDE:
        return None, "must_include_invalid"
    if any(not isinstance(item, str) or not item or len(item) > MAX_MUST_INCLUDE_CHARS for item in raw_paths):
        return None, "must_include_invalid"
    return _QueryRequest(
        query, limit, mode, include_bundle or bundle_only, hint.strip(),
        tuple(raw_paths), bundle_only,
    ), ""


def _authority_metadata(
    selection: HoloIndexAuthoritySelection,
) -> dict[str, Any]:
    return {
        "workspace_repo_head_sha": selection.workspace_head_sha,
        "authority_repo_head_sha": selection.authority_head_sha,
        "authority_repo_root_digest": selection.authority_root_digest,
        "workspace_overlay_present": selection.workspace_overlay_present,
        "semantic_evidence_authority": (
            "clean_workspace_head"
            if selection.source == "workspace"
            else "committed_head_only"
        ),
        "no_authority_worktree_mutation_performed": True,
    }


def _bind_authority(
    result: Mapping[str, Any],
    selection: HoloIndexAuthoritySelection,
    query: str,
) -> Mapping[str, Any]:
    metadata = _authority_metadata(selection)
    if (
        result.get("ok") is True
        and result.get("repo_root_digest") != selection.authority_root_digest
    ):
        return {
            **_failure("HOLOINDEX_AUTHORITY_ROOT_MISMATCH", query=query),
            **metadata,
        }
    return {**dict(result), **metadata}


def _same_authority(
    before: HoloIndexAuthoritySelection,
    after: HoloIndexAuthoritySelection,
) -> bool:
    return bool(
        after.accepted
        and after.selected_root == before.selected_root
        and after.workspace_head_sha == before.workspace_head_sha
        and after.authority_head_sha == before.authority_head_sha
        and after.authority_root_digest == before.authority_root_digest
        and after.workspace_overlay_present == before.workspace_overlay_present
    )


def _preflight_authority(
    selection: HoloIndexAuthoritySelection,
    query: str,
    *,
    preflight: Callable[..., ReadonlyQueryAdmission],
    ssd_path: Path,
) -> Mapping[str, Any] | None:
    try:
        admission = preflight(
            repo_root=selection.selected_root,
            ssd_path=ssd_path,
            expected_repo_head_sha=selection.authority_head_sha,
        )
    except Exception as exc:
        return {
            **_failure(type(exc).__name__, query=query),
            **_authority_metadata(selection),
        }
    if admission.allowed is True:
        return None
    binding = (
        dict(admission.binding)
        if isinstance(admission.binding, Mapping)
        else {}
    )
    return {
        **_failure(admission.error or "STALE_INDEX", query=query),
        **admission.to_dict(),
        **binding,
        **_authority_metadata(selection),
        "query": query,
        "raw_result": {},
    }


@dataclass
class _OwnerQueryState:
    attempts: int = 0
    retry_reason: str = ""
    cleanup_required: bool = False


def _response_matches_replica_route(
    result: Mapping[str, Any], route: Any,
) -> bool:
    expected = parse_replica_binding(
        getattr(route, "expected_replica_binding", None)
    )
    actual = parse_replica_binding(
        tuple(result.get(key) for key in _REPLICA_PUBLIC_FIELDS)
    )
    return expected is not None and actual == expected


def _owner_service_credentials(
    bootstrap: Any, resolve_handoff: Callable[..., Any],
    state: _OwnerQueryState, query: str,
) -> tuple[str | None, str | None, bool, Mapping[str, Any] | None]:
    status = str(getattr(bootstrap, "status", ""))
    if getattr(bootstrap, "ready", False) is not True:
        error = str(getattr(bootstrap, "error", "") or "owner_bootstrap_failed")
        return None, None, error in TRANSIENT_OWNER_ERRORS, _failure(error, query=query)
    process_owned = status in PROCESS_OWNED_STATUSES
    state.cleanup_required = process_owned
    if process_owned:
        handoff = resolve_handoff()
        if handoff is None:
            return None, None, False, _failure("owner_handoff_missing", query=query)
        return handoff[0], handoff[1], True, None
    if status == OWNER_CONFIGURED:
        return None, None, False, None
    return None, None, False, _failure("owner_bootstrap_status_invalid", query=query)


def _owner_attempt(
    *, query: str, limit: int, authority_root: Path, runtime_root: Path,
    ssd_path: Path,
    ensure_owner: Callable[..., Any], resolve_handoff: Callable[..., Any],
    query_owner: Callable[..., Mapping[str, Any]], state: _OwnerQueryState,
    resolve_replica_route: Callable[..., Any], operation_deadline: float | None,
    route_environment: Mapping[str, str],
) -> tuple[Mapping[str, Any], bool, bool]:
    remaining = _remaining_timeout(operation_deadline)
    if remaining == 0:
        return _failure("QUERY_TIMEOUT", query=query), False, False
    try:
        route = resolve_replica_route(
            canonical_repo_root=authority_root,
            canonical_ssd_path=ssd_path,
            environment=route_environment,
        )
    except Exception:
        return _failure(QUERY_REPLICA_REQUIRED_ERROR, query=query), False, False
    ensure_kwargs = {"startup_timeout_seconds": remaining} if remaining is not None else {}
    bootstrap = ensure_owner(
        repo_root=authority_root, runtime_root=runtime_root, requested=True,
        query_replica_route=route,
        owner_port=_owner_port_for_attempt(state.attempts),
        **ensure_kwargs,
    )
    service_url, service_token, process_owned, failure = _owner_service_credentials(
        bootstrap, resolve_handoff, state, query,
    )
    if failure is not None:
        return failure, process_owned, False
    remaining = _remaining_timeout(operation_deadline)
    if remaining == 0:
        return _failure("QUERY_TIMEOUT", query=query), False, False
    result = query_owner(
        repo_root=authority_root, query=query, limit=limit,
        service_url=service_url, service_token=service_token,
        timeout_seconds=remaining if remaining is not None else 60.0,
    )
    if not isinstance(result, Mapping):
        return _failure("owner_response_invalid", query=query), False, False
    if result.get("ok") is True and not _response_matches_replica_route(result, route):
        return _failure(
            "HOLOINDEX_QUERY_SERVICE_BINDING_MISMATCH", query=query
        ), False, False
    retryable = process_owned and str(result.get("error") or "") in TRANSIENT_OWNER_ERRORS
    return result, retryable, True


def _query_with_retry(
    *, query: str, limit: int, authority_root: Path, runtime_root: Path,
    ssd_path: Path,
    ensure_owner: Callable[..., Any], resolve_handoff: Callable[..., Any],
    query_owner: Callable[..., Mapping[str, Any]], cleanup_owner: Callable[[], None],
    state: _OwnerQueryState, resolve_replica_route: Callable[..., Any],
    operation_deadline: float | None,
    route_environment: Mapping[str, str],
) -> tuple[Mapping[str, Any], bool]:
    while state.attempts < MAX_OWNER_ATTEMPTS:
        if _remaining_timeout(operation_deadline) == 0:
            return _failure("QUERY_TIMEOUT", query=query), False
        state.attempts += 1
        result, retryable, bindable = _owner_attempt(
            query=query, limit=limit, authority_root=authority_root,
            runtime_root=runtime_root, ssd_path=ssd_path,
            ensure_owner=ensure_owner,
            resolve_handoff=resolve_handoff, query_owner=query_owner, state=state,
            resolve_replica_route=resolve_replica_route,
            operation_deadline=operation_deadline,
            route_environment=route_environment,
        )
        if state.attempts != 1 or not retryable:
            return result, bindable or retryable
        state.retry_reason = str(result.get("error") or "")
        cleanup_owner()
        state.cleanup_required = False
    return result, bindable


def _bind_query_receipt(
    result: Mapping[str, Any], *, query: str, repo_root: Path,
    selection: HoloIndexAuthoritySelection, select_authority: Callable[..., Any],
) -> Mapping[str, Any]:
    final_selection = select_authority(repo_root)
    if not _same_authority(selection, final_selection):
        return {
            **_failure("REPOSITORY_STATE_CHANGED_DURING_QUERY", query=query),
            **_authority_metadata(selection),
        }
    bound = _bind_authority(result, final_selection, query)
    try:
        semantic_json, _, _ = canonical_semantic_evidence(bound.get("raw_result"))
    except ValueError as exc:
        return {
            **_failure(str(exc), query=query),
            **_authority_metadata(final_selection),
        }
    bound = {**dict(bound), "semantic_evidence_json": semantic_json}
    receipt = build_query_receipt(
        source="holoindex_owner_service", source_class="holoindex",
        query=query, result=bound, require_generation=True,
    )
    return {**dict(bound), "query_receipt": dict(receipt)}


def _admit_query(
    request: _QueryRequest, repo_root: Path,
    *, select_authority: Callable[..., HoloIndexAuthoritySelection],
    preflight: Callable[..., ReadonlyQueryAdmission],
    ssd_path: Path,
) -> tuple[str, int, HoloIndexAuthoritySelection | None, Mapping[str, Any] | None]:
    query, limit = request.query, request.limit
    selection = select_authority(repo_root)
    if not selection.accepted:
        failure = {
            **_failure(selection.error or "authority_selection_failed", query=query),
            **_authority_metadata(selection),
        }
    else:
        failure = _preflight_authority(
            selection, query, preflight=preflight,
            ssd_path=ssd_path,
        )
    if failure is not None:
        failure = _with_retry_telemetry(failure, attempts=0, retry_reason="")
    return query, limit, selection, failure


def _bundle_authority(repo_root: Path, selection: HoloIndexAuthoritySelection):
    return {
        "repo_head_sha": selection.workspace_head_sha,
        "repo_root_digest": repository_root_digest(repo_root),
        "workspace_overlay_present": selection.workspace_overlay_present,
        "evidence_authority": (
            "workspace_overlay" if selection.workspace_overlay_present
            else "workspace_head"
        ),
    }


def _build_requested_bundle(request, repo_root, selection, bundle_builder):
    if not request.include_bundle:
        return None
    try:
        bundle = bundle_builder(
            repo_root, request.query, limit=request.limit,
            retrieval_mode="lexical", module_hint=request.module_hint,
            must_include=list(request.must_include), bundle_only=True,
        )
    except Exception as exc:
        bundle = {"schema_version": "wsp_memory_bundle_v1", "ok": False,
                  "error": type(exc).__name__}
    return {
        "bundle": bundle, "bundle_ok": bundle.get("ok") is True,
        "bundle_error": str(bundle.get("error") or ""),
        "bundle_authority": _bundle_authority(repo_root, selection),
    }


def _lexical_result(request, selection, bundle_fields):
    bundle = (bundle_fields or {}).get("bundle") or {}
    result = {
        "ok": bundle.get("ok") is True, "source": "holoindex_bundle",
        "query": request.query, "freshness": "UNKNOWN", "raw_result": {},
        "error": str(bundle.get("error") or ""), "index_gap_detected": True,
        "stale_reasons": ["semantic_query_not_requested"],
        "no_holoindex_reindex_performed": True, "owner_attempts": 0,
        "owner_retry_performed": False, "owner_retry_reason": "",
        **_authority_metadata(selection),
    }
    return {**result, **(bundle_fields or {}), "no_reindex": True}


def _execute_admitted_query(
    *, query: str, limit: int, repo_root: Path,
    selection: HoloIndexAuthoritySelection, ensure_owner: Callable[..., Any],
    resolve_handoff: Callable[..., Any], query_owner: Callable[..., Any],
    cleanup_owner: Callable[[], None], select_authority: Callable[..., Any],
    select_runtime_root: Callable[[Path], Path], ssd_path: Path,
    resolve_replica_route: Callable[..., Any], operation_deadline: float | None,
    route_environment: Mapping[str, str], preflight: Preflight,
) -> Mapping[str, Any]:
    state = _OwnerQueryState()
    try:
        selection, changed = _revalidate_serialized_authority(
            repo_root=repo_root, selection=selection, query=query,
            select_authority=select_authority, preflight=preflight,
            ssd_path=ssd_path,
        )
        if changed is not None:
            return _with_retry_telemetry(changed, attempts=0, retry_reason="")
        result, bindable = _query_with_retry(
            query=query, limit=limit, authority_root=selection.selected_root,
            runtime_root=select_runtime_root(repo_root), ssd_path=ssd_path,
            ensure_owner=ensure_owner,
            resolve_handoff=resolve_handoff, query_owner=query_owner,
            cleanup_owner=cleanup_owner, state=state,
            resolve_replica_route=resolve_replica_route,
            operation_deadline=operation_deadline,
            route_environment=route_environment,
        )
        result = _with_retry_telemetry(
            result, attempts=state.attempts, retry_reason=state.retry_reason,
        )
        if bindable:
            result = _bind_query_receipt(
                result, query=query, repo_root=repo_root, selection=selection,
                select_authority=select_authority,
            )
        return result
    except Exception as exc:
        return _with_retry_telemetry(
            _failure(type(exc).__name__, query=query),
            attempts=max(1, state.attempts), retry_reason=state.retry_reason,
        )
    finally:
        if state.cleanup_required:
            cleanup_owner()


def _revalidate_serialized_authority(
    *, repo_root: Path, selection: HoloIndexAuthoritySelection, query: str,
    select_authority: AuthoritySelector, preflight: Preflight, ssd_path: Path,
) -> tuple[HoloIndexAuthoritySelection, Mapping[str, Any] | None]:
    current = select_authority(repo_root)
    if not _same_authority(selection, current):
        return current, {
            **_failure("REPOSITORY_STATE_CHANGED_DURING_QUERY", query=query),
            **_authority_metadata(selection),
        }
    return current, _preflight_authority(
        current, query, preflight=preflight, ssd_path=ssd_path,
    )


def _resolve_query_ssd_path(
    resolver: Callable[[], Path], query: str,
) -> tuple[Path | None, Mapping[str, Any] | None]:
    try:
        return resolver(), None
    except Exception as exc:
        return None, _with_retry_telemetry(
            _failure(type(exc).__name__, query=query),
            attempts=0, retry_reason="",
        )


def _operation_deadline(value: float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("operation_timeout_invalid")
    timeout = float(value)
    if (
        not math.isfinite(timeout) or timeout <= 0
        or timeout > MAX_OPERATION_TIMEOUT_SECONDS
    ):
        raise ValueError("operation_timeout_invalid")
    return time.monotonic() + timeout


def _remaining_timeout(deadline: float | None) -> float | None:
    if deadline is None:
        return None
    return max(0.0, deadline - time.monotonic())


def _request_and_deadline(
    payload: Mapping[str, Any], operation_timeout_seconds: float | None,
) -> tuple[_QueryRequest | None, float | None, Mapping[str, Any] | None]:
    try:
        deadline = _operation_deadline(operation_timeout_seconds)
    except (TypeError, ValueError):
        failure = _with_retry_telemetry(
            _failure("operation_timeout_invalid"), attempts=0, retry_reason="",
        )
        return None, None, failure
    request, request_error = _bounded_request(payload)
    if request_error or request is None:
        failure = _with_retry_telemetry(
            _failure(request_error), attempts=0, retry_reason="",
        )
        return None, deadline, failure
    return request, deadline, None


def _query_runtime_environment(
    explicit: Mapping[str, str] | None,
) -> dict[str, str]:
    return build_owner_query_environment(
        process_environment=explicit,
        user_environment={} if explicit is not None else None,
    )


def _environment_bound_authority_selector(
    selector: AuthoritySelector, environment: Mapping[str, str],
) -> AuthoritySelector:
    if selector is resolve_holoindex_authority_root:
        return lambda root: selector(root, environment=environment)
    return selector


def _execute_serialized_owner_query(
    *, operation_deadline: float | None, query: str,
    execute: Callable[[], Mapping[str, Any]],
) -> Mapping[str, Any]:
    remaining = _remaining_timeout(operation_deadline)
    if remaining == 0:
        return _with_retry_telemetry(
            _failure("QUERY_TIMEOUT", query=query), attempts=0, retry_reason="",
        )
    acquired = (
        _OWNER_LIFECYCLE_LOCK.acquire(timeout=remaining)
        if remaining is not None
        else _OWNER_LIFECYCLE_LOCK.acquire()
    )
    if not acquired:
        return _with_retry_telemetry(
            _failure("QUERY_TIMEOUT", query=query), attempts=0, retry_reason="",
        )
    try:
        return execute()
    finally:
        _OWNER_LIFECYCLE_LOCK.release()


def _route_query_context(
    *, request: _QueryRequest, repo_root: Path,
    select_authority: AuthoritySelector,
    query_environment: Mapping[str, str] | None,
) -> tuple[
    dict[str, str], AuthoritySelector, HoloIndexAuthoritySelection | None,
    Mapping[str, Any] | None,
]:
    try:
        environment = _query_runtime_environment(query_environment)
    except (TypeError, ValueError):
        return {}, select_authority, None, _with_retry_telemetry(
            _failure(QUERY_REPLICA_REQUIRED_ERROR, query=request.query),
            attempts=0, retry_reason="",
        )
    selector = _environment_bound_authority_selector(select_authority, environment)
    return environment, selector, selector(repo_root), None


def _prepare_owner_query(
    *, request: _QueryRequest, repo_root: Path,
    select_authority: AuthoritySelector,
    query_environment: Mapping[str, str] | None,
    bundle_builder: Callable[..., Mapping[str, Any]],
    resolve_ssd_path: Callable[[], Path], preflight: Preflight,
) -> tuple[_PreparedQuery | None, Mapping[str, Any] | None]:
    environment, selector, selection, failure = _route_query_context(
        request=request, repo_root=repo_root, select_authority=select_authority,
        query_environment=query_environment,
    )
    if failure is not None or selection is None:
        return None, failure or _failure(QUERY_REPLICA_REQUIRED_ERROR, query=request.query)
    bundle = _build_requested_bundle(request, repo_root, selection, bundle_builder)
    if request.bundle_only or request.retrieval_mode == "lexical":
        return None, _lexical_result(request, selection, bundle)
    ssd_path, failure = _resolve_query_ssd_path(resolve_ssd_path, request.query)
    if failure is not None or ssd_path is None:
        return None, {**(failure or {}), **(bundle or {}), "no_reindex": True}
    query, limit, selection, failure = _admit_query(
        request, repo_root, select_authority=lambda _root: selection,
        preflight=preflight, ssd_path=ssd_path,
    )
    if failure is not None or selection is None:
        return None, {**(failure or {}), **(bundle or {}), "no_reindex": True}
    return _PreparedQuery(
        query, limit, selection, environment, selector, ssd_path, bundle,
    ), None


def query_once(
    payload: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT, ensure_owner: Callable[..., Any] = ensure_reddog_holoindex_owner,
    resolve_handoff: OwnerHandoffResolver = resolve_reddog_holoindex_owner_handoff,
    query_owner: Callable[..., Mapping[str, Any]] = query_holoindex_owner,
    cleanup_owner: Callable[..., None] = cleanup_reddog_holoindex_owner,
    select_authority: AuthoritySelector = resolve_holoindex_authority_root,
    select_runtime_root: Callable[[Path], Path] = resolve_holoindex_runtime_root,
    preflight: Preflight = rehydrate_canonical_freshness_proof,
    resolve_ssd_path: Callable[[], Path] = resolve_holoindex_ssd_path,
    resolve_replica_route: Callable[..., Any] = resolve_query_replica_owner_route,
    bundle_builder: Callable[..., Mapping[str, Any]] = build_wsp_memory_bundle,
    operation_timeout_seconds: float | None = DEFAULT_OPERATION_TIMEOUT_SECONDS,
    query_environment: Mapping[str, str] | None = None,
) -> Mapping[str, Any]:
    """Execute one owner-bound query and always clean up process-owned state."""

    request, deadline, request_failure = _request_and_deadline(payload, operation_timeout_seconds)
    if request_failure is not None or request is None:
        return request_failure or _failure("request_invalid")
    prepared, terminal = _prepare_owner_query(
        request=request, repo_root=repo_root, select_authority=select_authority,
        query_environment=query_environment, bundle_builder=bundle_builder,
        resolve_ssd_path=resolve_ssd_path, preflight=preflight,
    )
    if terminal is not None or prepared is None:
        return terminal or _failure(QUERY_REPLICA_REQUIRED_ERROR, query=request.query)
    result = _execute_serialized_owner_query(
        operation_deadline=deadline, query=prepared.query,
        execute=lambda: _execute_admitted_query(
            query=prepared.query, limit=prepared.limit, repo_root=repo_root,
            selection=prepared.selection,
            ensure_owner=ensure_owner, resolve_handoff=resolve_handoff,
            query_owner=query_owner, cleanup_owner=cleanup_owner,
            select_authority=prepared.select_authority,
            select_runtime_root=select_runtime_root, ssd_path=prepared.ssd_path,
            resolve_replica_route=resolve_replica_route,
            operation_deadline=deadline,
            route_environment=prepared.route_environment, preflight=preflight,
        ),
    )
    return {**result, **(prepared.bundle_fields or {}), "no_reindex": True}


def _cli_operation_timeout(argv: list[str]) -> float | None:
    if not argv:
        return DEFAULT_OPERATION_TIMEOUT_SECONDS
    if len(argv) != 2 or argv[0] != "--operation-timeout-seconds":
        raise ValueError("invalid_arguments")
    timeout = float(argv[1])
    _operation_deadline(timeout)
    return timeout


def _main_result(arguments: list[str]) -> Mapping[str, Any]:
    try:
        operation_timeout = _cli_operation_timeout(arguments)
    except (TypeError, ValueError):
        return _failure("invalid_arguments")
    try:
        payload = _read_payload()
    except (UnicodeError, ValueError, json.JSONDecodeError):
        return _failure("invalid_json")
    return query_once(payload, operation_timeout_seconds=operation_timeout)


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    result = _main_result(arguments)
    sys.stdout.write(json.dumps(result, ensure_ascii=True, sort_keys=True))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
