"""Bounded, read-only HoloIndex query adapter for RedDog audit workers.

This module owns HoloIndex storage resolution, generation freshness proof,
owner-service delegation, and result normalization. It has no indexing or
repository mutation authority.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from holo_index.freshness_receipt import (
    BASELINE_QUERY_FRESHNESS_PATHS,
    freshness_receipt_path,
)
from holo_index.maintenance_lock import maintenance_lock_path, probe_maintenance_lock
from holo_index.query_admission import evaluate_readonly_query_admission
from holo_index.storage_contract import (
    HoloIndexStorageError,
    resolve_holoindex_ssd_path,
)
from modules.communication.moltbot_bridge.src.reddog_holoindex_owner_query_client import (
    HOLOINDEX_QUERY_SERVICE_TOKEN_ENV,
    HOLOINDEX_QUERY_SERVICE_URL_ENV,
    query_holoindex_owner,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_bootstrap import (
    restart_reddog_holoindex_owner,
    resolve_reddog_holoindex_owner_handoff,
)


# The default HoloIndex search queries these seven evidence collections. Feed
# one deterministic representative path per collection into the existing
# path-based freshness gate so CURRENT means the whole baseline query surface
# is proven at the exact repository HEAD.
HOLOINDEX_BASELINE_FRESHNESS_PATHS = BASELINE_QUERY_FRESHNESS_PATHS
MAINTENANCE_ACTIVE_ERROR = "HOLOINDEX_MAINTENANCE_ACTIVE"
MAINTENANCE_ACTIVE_REASON = "holoindex_maintenance_active"
MAINTENANCE_UNPROVEN_ERROR = "HOLOINDEX_MAINTENANCE_LOCK_UNPROVEN"
MAINTENANCE_UNPROVEN_REASON = "holoindex_maintenance_lock_unproven"
DIRECT_QUERY_DIAGNOSTIC_ERROR = "HOLOINDEX_DIRECT_QUERY_DIAGNOSTIC_ONLY"
DIRECT_QUERY_DIAGNOSTIC_REASON = "direct_query_has_no_freshness_authority"


def path_is_allowed(path: str, allowed_paths: Sequence[str]) -> bool:
    """Return true only when a repository-relative path matches signed scope."""
    candidate = str(path or "").replace("\\", "/").strip()
    while candidate.startswith("./"):
        candidate = candidate[2:]
    candidate_parts = candidate.split("/")
    if (
        not candidate
        or candidate.startswith("/")
        or ":" in candidate
        or "\0" in candidate
        or any(part in {"", ".", ".."} for part in candidate_parts)
    ):
        return False
    for value in allowed_paths:
        pattern = str(value or "").replace("\\", "/").strip()
        while pattern.startswith("./"):
            pattern = pattern[2:]
        pattern_parts = pattern.replace("/**", "").split("/")
        if (
            not pattern
            or pattern.startswith("/")
            or ":" in pattern
            or "\0" in pattern
            or any(part in {"", ".", ".."} for part in pattern_parts)
        ):
            continue
        if pattern.endswith("/**"):
            root = pattern[:-3].rstrip("/")
            if candidate == root or candidate.startswith(root + "/"):
                return True
        elif candidate == pattern:
            return True
    return False


def _scope_result_hits(
    result: Mapping[str, Any],
    allowed_paths: Sequence[str],
) -> Mapping[str, Any]:
    scoped = dict(result)
    raw_hits = result.get("hits")
    hits = raw_hits if isinstance(raw_hits, list) else []
    scoped["hits"] = [
        hit for hit in hits
        if isinstance(hit, Mapping)
        and path_is_allowed(str(hit.get("path") or ""), allowed_paths)
    ]
    return scoped


def _owner_configuration(
    service_url: str | None,
    service_token: str | None,
) -> tuple[str, str, bool] | None:
    """Prefer operator configuration, then the process-private auto owner."""
    env_url = os.getenv(HOLOINDEX_QUERY_SERVICE_URL_ENV, "")
    env_token = os.getenv(HOLOINDEX_QUERY_SERVICE_TOKEN_ENV, "")
    configured = (
        service_url is not None
        or service_token is not None
        or bool(env_url.strip())
        or bool(env_token.strip())
    )
    if configured:
        return (
            str(service_url if service_url is not None else env_url),
            str(service_token if service_token is not None else env_token),
            False,
        )
    try:
        handoff = resolve_reddog_holoindex_owner_handoff()
        return (*handoff, True) if handoff is not None else None
    except Exception:
        return None


def _maintenance_block(lock_path: Path) -> tuple[str, str]:
    try:
        probe = probe_maintenance_lock(lock_path)
    except Exception:
        return MAINTENANCE_UNPROVEN_ERROR, MAINTENANCE_UNPROVEN_REASON
    if getattr(probe, "clear", False) is True:
        return "", ""
    if getattr(probe, "held", False) is True or getattr(probe, "status", "") == "held":
        return MAINTENANCE_ACTIVE_ERROR, MAINTENANCE_ACTIVE_REASON
    return MAINTENANCE_UNPROVEN_ERROR, MAINTENANCE_UNPROVEN_REASON


def holoindex_hits(result: Any) -> list[Mapping[str, Any]]:
    """Normalize canonical and compatibility HoloIndex result buckets."""

    if not isinstance(result, Mapping):
        return []
    hits: list[Mapping[str, Any]] = []
    for key in (
        "code_hits",
        "wsp_hits",
        "docs_hits",
        "knowledge_hits",
        "test_hits",
        "skill_hits",
        "work_ledger_hits",
        "symbol_hits",
        "code",
        "wsps",
        "docs",
        "knowledge",
        "tests",
        "skills",
        "work_ledger",
    ):
        value = result.get(key)
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            continue
        for item in value:
            if not isinstance(item, Mapping):
                continue
            path = str(
                item.get("path") or item.get("file") or item.get("location") or ""
            ).replace("\\", "/")
            if ":" in path:
                maybe_path = path.split(":", 1)[0]
                if "/" in maybe_path or "." in maybe_path:
                    path = maybe_path
            if not path:
                continue
            hits.append(
                {
                    "path": path,
                    "title": str(item.get("title") or item.get("name") or key),
                    "score": item.get("score")
                    or item.get("final_score")
                    or item.get("distance"),
                    "digest": str(item.get("digest") or item.get("content_digest") or ""),
                    "evidence_ref": str(item.get("evidence_ref") or ""),
                }
            )
    seen: set[str] = set()
    deduped: list[Mapping[str, Any]] = []
    for hit in hits:
        path = str(hit.get("path") or "").replace("\\", "/").strip()
        if not path or path in seen:
            continue
        seen.add(path)
        deduped.append(hit)
    return deduped


def paths_from_query_receipt(receipt: Mapping[str, Any]) -> tuple[str, ...]:
    """Return normalized, ordered, unique paths from a query receipt."""

    paths: list[str] = []
    for item in receipt.get("hits") or ():
        if not isinstance(item, Mapping):
            continue
        path = str(item.get("path") or "").replace("\\", "/").strip()
        if path:
            paths.append(path)
    return tuple(dict.fromkeys(paths))


def _direct_failure(
    *,
    query: str,
    started: float,
    error: str,
    hits: Sequence[Mapping[str, Any]] = (),
    stale_reasons: Sequence[str] = (),
    retrieval_mode: str = "",
    storage_error: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "source": "holoindex_direct_diagnostic",
        "query": query,
        "freshness": "UNKNOWN",
        "hits": list(hits),
        "error": error,
        "latency_ms": int((time.monotonic() - started) * 1000),
        "index_gap_detected": True,
        "stale_reasons": list(dict.fromkeys(stale_reasons)),
        "no_holoindex_reindex_performed": True,
    }
    if retrieval_mode:
        result["retrieval_mode"] = retrieval_mode
    if storage_error is not None:
        result["storage_error"] = dict(storage_error)
    return result


def _direct_backend_query(
    *,
    ssd_path: Path,
    query: str,
    limit: int,
) -> tuple[Any, str]:
    previous_readonly = os.environ.get("HOLOINDEX_QUERY_READONLY")
    os.environ["HOLOINDEX_QUERY_READONLY"] = "1"
    try:
        from holo_index.core.holo_index import HoloIndex

        index = HoloIndex(ssd_path=str(ssd_path), quiet=True)
        result = index.search(query, limit=limit)
        retrieval_mode = str(getattr(index, "retrieval_mode", "unknown")).lower()
        return result, retrieval_mode
    finally:
        if previous_readonly is None:
            os.environ.pop("HOLOINDEX_QUERY_READONLY", None)
        else:
            os.environ["HOLOINDEX_QUERY_READONLY"] = previous_readonly


def _direct_diagnostic_result(
    *,
    result: Any,
    fallback_mode: str,
    query: str,
    limit: int,
    started: float,
) -> Mapping[str, Any]:
    """Downgrade direct access to an explicit non-operational diagnostic."""
    metadata_value = result.get("metadata") if isinstance(result, Mapping) else None
    metadata = metadata_value if isinstance(metadata_value, Mapping) else {}
    retrieval_mode = str(metadata.get("retrieval_mode") or fallback_mode).lower()
    reasons = [DIRECT_QUERY_DIAGNOSTIC_REASON]
    if retrieval_mode != "semantic":
        reasons.append("nonsemantic_retrieval")
    return _direct_failure(
        query=query,
        started=started,
        error=DIRECT_QUERY_DIAGNOSTIC_ERROR,
        hits=holoindex_hits(result)[:limit],
        stale_reasons=reasons,
        retrieval_mode=retrieval_mode,
    )


def _direct_admission_failure(
    *,
    repo_root: Path,
    ssd_path: Path,
    receipt_path: Path | str | None,
    query: str,
    started: float,
) -> Mapping[str, Any] | None:
    admission = evaluate_readonly_query_admission(
        repo_root=repo_root,
        ssd_path=ssd_path,
        receipt_path=receipt_path,
    )
    if admission.allowed:
        return None
    return _direct_failure(
        query=query,
        started=started,
        error=admission.error,
        stale_reasons=admission.reasons,
    )


def _direct_paths(
    ssd_path_value: Path | str | None,
) -> tuple[Path, Path]:
    ssd_path = resolve_holoindex_ssd_path(ssd_path_value)
    return ssd_path, freshness_receipt_path(ssd_path)


def _direct_preflight(
    repo_root: Path,
    ssd_path_value: Path | str | None,
    receipt_path_value: Path | str | None,
    query: str,
    started: float,
) -> tuple[Path, Path, Mapping[str, Any] | None]:
    ssd_path, receipt_path = _direct_paths(ssd_path_value)
    failure = _direct_admission_failure(
        repo_root=repo_root,
        ssd_path=ssd_path,
        receipt_path=receipt_path_value,
        query=query,
        started=started,
    )
    if failure is None:
        error, reason = _maintenance_block(
            maintenance_lock_path(ssd_path)
        )
        if error:
            failure = _direct_failure(
                query=query,
                started=started,
                error=error,
                stale_reasons=[reason],
            )
    return ssd_path, receipt_path, failure


def _query_direct_diagnostic(
    *,
    repo_root: Path,
    ssd_path_value: Path | str | None,
    receipt_path_value: Path | str | None,
    query: str,
    limit: int,
) -> Mapping[str, Any]:
    started = time.monotonic()
    bounded_limit = max(1, min(int(limit or 8), 20))
    try:
        ssd_path, receipt_path, preflight_failure = _direct_preflight(
            repo_root, ssd_path_value, receipt_path_value, query, started
        )
        if preflight_failure is not None:
            return preflight_failure
        lock_path = maintenance_lock_path(ssd_path)
        result, fallback_mode = _direct_backend_query(
            ssd_path=ssd_path,
            query=query,
            limit=bounded_limit,
        )
    except HoloIndexStorageError as exc:
        return _direct_failure(
            query=query,
            started=started,
            error=exc.code,
            storage_error=exc.to_dict(),
        )
    except Exception as exc:
        return _direct_failure(
            query=query,
            started=started,
            error=f"holoindex_query_failed:{type(exc).__name__}",
        )
    maintenance_error, maintenance_reason = _maintenance_block(lock_path)
    if maintenance_error:
        return _direct_failure(
            query=query,
            started=started,
            error=maintenance_error,
            stale_reasons=[maintenance_reason],
        )
    return _direct_diagnostic_result(
        result=result,
        fallback_mode=fallback_mode,
        query=query,
        limit=bounded_limit,
        started=started,
    )


@dataclass(frozen=True)
class HoloIndexReadOnlyQueryAdapter:
    """Read-only HoloIndex discovery adapter for repo audit workers."""

    repo_root: Path
    ssd_path: Path | str | None = None
    freshness_receipt_path: Path | str | None = None
    service_url: str | None = None
    service_token: str | None = None
    service_timeout_seconds: float = 15.0

    def _query_owner_service(
        self,
        *,
        query: str,
        limit: int,
        owner: tuple[str, str, bool],
    ) -> Mapping[str, Any]:
        service_url, service_token, private = owner

        def invoke(url: str, token: str) -> dict[str, Any]:
            return dict(query_holoindex_owner(
                repo_root=self.repo_root,
                query=query,
                limit=limit,
                service_url=url,
                service_token=token,
                timeout_seconds=self.service_timeout_seconds,
            ))

        result = invoke(service_url, service_token)
        poisoned_timeout = (
            result.get("error") == "QUERY_TIMEOUT"
            and "backend_timeout_owner_poisoned"
            in result.get("stale_reasons", ())
        )
        if private and (
            result.get("error") == "QUERY_OWNER_POISONED" or poisoned_timeout
        ):
            restarted = restart_reddog_holoindex_owner(
                failed_handoff=(service_url, service_token),
            )
            if restarted is not None:
                result = invoke(*restarted)
        raw_result = result.pop("raw_result", {})
        result["hits"] = holoindex_hits(raw_result)[
            : max(1, min(int(limit or 8), 20))
        ]
        return result

    def query(self, *, query: str, allowed_paths: Sequence[str], limit: int) -> Mapping[str, Any]:
        owner = _owner_configuration(self.service_url, self.service_token)
        if owner is not None:
            return _scope_result_hits(
                self._query_owner_service(query=query, limit=limit, owner=owner),
                allowed_paths,
            )
        if self.ssd_path is None and self.freshness_receipt_path is None:
            return {
                "ok": False,
                "source": "holoindex",
                "query": str(query or ""),
                "freshness": "UNKNOWN",
                "hits": [],
                "error": "HOLOINDEX_QUERY_SERVICE_NOT_CONFIGURED",
                "index_gap_detected": True,
                "stale_reasons": ["holoindex_owner_service_required"],
                "no_holoindex_reindex_performed": True,
            }
        return _scope_result_hits(
            _query_direct_diagnostic(
                repo_root=self.repo_root,
                ssd_path_value=self.ssd_path,
                receipt_path_value=self.freshness_receipt_path,
                query=str(query or ""),
                limit=limit,
            ),
            allowed_paths,
        )


__all__ = [
    "DIRECT_QUERY_DIAGNOSTIC_ERROR",
    "DIRECT_QUERY_DIAGNOSTIC_REASON",
    "HOLOINDEX_BASELINE_FRESHNESS_PATHS",
    "HoloIndexReadOnlyQueryAdapter",
    "holoindex_hits",
    "path_is_allowed",
    "paths_from_query_receipt",
]
