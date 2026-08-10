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

from holo_index.query_receipt import (  # noqa: E402
    build_query_receipt,
    canonical_semantic_evidence,
)
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


MAX_QUERY_CHARS = 16_000
MAX_LIMIT = 20
MAX_OWNER_ATTEMPTS = 3
PROCESS_OWNED_STATUSES = frozenset({OWNER_STARTED, OWNER_REUSED})
TRANSIENT_OWNER_ERRORS = frozenset(
    {
        "HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP",
        "QUERY_OWNER_POISONED",
        "SEMANTIC_BACKEND_UNAVAILABLE",
    }
)


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
    select_authority: Callable[
        [Path], HoloIndexAuthoritySelection
    ] = resolve_holoindex_authority_root,
    select_runtime_root: Callable[[Path], Path] = resolve_holoindex_runtime_root,
) -> Mapping[str, Any]:
    """Execute one owner-bound query and always clean up process-owned state."""

    query, limit, request_error = _bounded_request(payload)
    if request_error:
        return _failure(request_error)
    selection = select_authority(repo_root)
    if not selection.accepted:
        return _with_retry_telemetry(
            {
                **_failure(
                    selection.error or "authority_selection_failed", query=query
                ),
                **_authority_metadata(selection),
            },
            attempts=0,
            retry_reason="",
        )
    authority_root = selection.selected_root

    started_here = False
    attempts = 0
    retry_reason = ""
    try:
        while attempts < MAX_OWNER_ATTEMPTS:
            attempts += 1
            bootstrap = ensure_owner(
                repo_root=authority_root,
                runtime_root=select_runtime_root(repo_root),
                requested=True,
            )
            status = str(getattr(bootstrap, "status", ""))
            if getattr(bootstrap, "ready", False) is not True:
                error = str(
                    getattr(bootstrap, "error", "") or "owner_bootstrap_failed"
                )
                if attempts < MAX_OWNER_ATTEMPTS and error in TRANSIENT_OWNER_ERRORS:
                    retry_reason = error
                    cleanup_owner()
                    continue
                if error in TRANSIENT_OWNER_ERRORS:
                    result = _failure(error, query=query)
                    break
                return _with_retry_telemetry(
                    _failure(error, query=query),
                    attempts=attempts,
                    retry_reason=retry_reason,
                )
            process_owned = status in PROCESS_OWNED_STATUSES
            started_here = status == OWNER_STARTED
            service_url: str | None = None
            service_token: str | None = None
            if process_owned:
                handoff = resolve_handoff()
                if handoff is None:
                    return _with_retry_telemetry(
                        _failure("owner_handoff_missing", query=query),
                        attempts=attempts,
                        retry_reason=retry_reason,
                    )
                service_url, service_token = handoff
            elif status != OWNER_CONFIGURED:
                return _with_retry_telemetry(
                    _failure("owner_bootstrap_status_invalid", query=query),
                    attempts=attempts,
                    retry_reason=retry_reason,
                )

            result = query_owner(
                repo_root=authority_root,
                query=query,
                limit=limit,
                service_url=service_url,
                service_token=service_token,
                timeout_seconds=60.0,
            )
            if not isinstance(result, Mapping):
                return _with_retry_telemetry(
                    _failure("owner_response_invalid", query=query),
                    attempts=attempts,
                    retry_reason=retry_reason,
                )
            error = str(result.get("error") or "")
            if (
                attempts < MAX_OWNER_ATTEMPTS
                and process_owned
                and error in TRANSIENT_OWNER_ERRORS
            ):
                retry_reason = error
                cleanup_owner()
                started_here = False
                continue
            break

        final_selection = select_authority(repo_root)
        if not _same_authority(selection, final_selection):
            return _with_retry_telemetry(
                {
                    **_failure(
                        "REPOSITORY_STATE_CHANGED_DURING_QUERY", query=query
                    ),
                    **_authority_metadata(selection),
                },
                attempts=attempts,
                retry_reason=retry_reason,
            )
        result = _bind_authority(result, final_selection, query)
        try:
            semantic_evidence_json, _, _ = canonical_semantic_evidence(
                result.get("raw_result")
            )
        except ValueError as exc:
            return _with_retry_telemetry(
                {
                    **_failure(str(exc), query=query),
                    **_authority_metadata(final_selection),
                },
                attempts=attempts,
                retry_reason=retry_reason,
            )
        result = {
            **dict(result),
            "semantic_evidence_json": semantic_evidence_json,
        }
        receipt = build_query_receipt(
            source="holoindex_owner_service",
            source_class="holoindex",
            query=query,
            result=result,
            require_generation=True,
        )
        return _with_retry_telemetry(
            {**dict(result), "query_receipt": dict(receipt)},
            attempts=attempts,
            retry_reason=retry_reason,
        )
    except Exception as exc:
        return _with_retry_telemetry(
            _failure(type(exc).__name__, query=query),
            attempts=max(1, attempts),
            retry_reason=retry_reason,
        )
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
