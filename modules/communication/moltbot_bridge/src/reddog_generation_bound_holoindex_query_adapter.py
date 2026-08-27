"""Generation-bound HoloIndex adapter for resident RedDog audit workers.

The adapter reuses the extension's governed one-shot owner query.  That path
selects the repository authority, resolves the immutable query-replica route,
starts or reuses the authenticated owner, verifies the response, and cleans up
process-owned state.  This module only normalizes and scopes returned hits.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from threading import Lock
import time
from typing import Any, Callable, Mapping, Sequence

from holo_index.query_receipt import build_query_receipt
from modules.communication.moltbot_bridge.src.reddog_holoindex_query_adapter import (
    holoindex_hits,
    path_is_allowed,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service_supervisor import (
    _owner_python_runtime,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_sealed_holo_runtime import (
    scrub_holo_child_environment,
)


QueryOnceRunner = Callable[..., Mapping[str, Any]]
_OWNER_QUERY_ONCE_LOCK = Lock()
_OWNER_CLEANUP_RESERVE_SECONDS = 3.0
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_REASON = re.compile(r"^[A-Za-z0-9_.:-]{0,160}$")
_DIGEST_FIELDS = (
    "freshness_generation_id",
    "freshness_receipt_digest",
    "repo_root_digest",
    "authority_repo_root_digest",
    "query_replica_descriptor_digest",
    "query_replica_generation_id",
    "query_replica_id",
    "query_replica_path_identity_digest",
    "retrieval_runtime_ranker_digest",
)
_HEAD_FIELDS = (
    "repo_head_sha",
    "workspace_repo_head_sha",
    "authority_repo_head_sha",
)
_BOOLEAN_FIELDS = (
    "workspace_overlay_present",
    "no_authority_worktree_mutation_performed",
    "index_gap_detected",
    "no_holoindex_reindex_performed",
    "no_reindex",
    "owner_retry_performed",
)
_MAX_PROCESS_STDOUT_BYTES = 8 * 1024 * 1024
_MAX_PROCESS_STDERR_BYTES = 1024 * 1024
_OWNER_QUERY_CONFIGURATION_KEYS = (
    "HOLOINDEX_QUERY_SERVICE_URL", "HOLOINDEX_QUERY_SERVICE_TOKEN",
    "REDDOG_HOLOINDEX_OWNER_AUTO_START", "HOLOINDEX_SSD_PATH",
    "REDDOG_HOLOINDEX_QUERY_ROUTE_FILE", "REDDOG_HOLOINDEX_QUERY_REPLICA_ROOT",
    "REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT",
)


def _owner_query_environment(pythonpath_entries: Sequence[str]) -> dict[str, str]:
    environment = scrub_holo_child_environment(os.environ)
    for name in _OWNER_QUERY_CONFIGURATION_KEYS:
        value = os.environ.get(name)
        if value:
            environment[name] = value
    if pythonpath_entries:
        environment["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    return environment


def _capture_owner_process(
    command: Sequence[str], *, root: Path, payload: Mapping[str, Any],
    timeout_seconds: float, options: Mapping[str, Any],
    environment: Mapping[str, str],
) -> tuple[bytes | None, str]:
    try:
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process = subprocess.run(
                list(command), cwd=str(root), env=dict(environment),
                input=json.dumps(payload, ensure_ascii=True).encode("utf-8"),
                stdout=stdout, stderr=stderr, timeout=timeout_seconds,
                check=False, shell=False, close_fds=True, **dict(options),
            )
            stdout_size, stderr_size = stdout.tell(), stderr.tell()
            if (
                process.returncode != 0
                or stdout_size > _MAX_PROCESS_STDOUT_BYTES
                or stderr_size > _MAX_PROCESS_STDERR_BYTES
            ):
                return None, "HOLOINDEX_OWNER_QUERY_PROCESS_FAILED"
            stdout.seek(0)
            return stdout.read(_MAX_PROCESS_STDOUT_BYTES + 1), ""
    except subprocess.TimeoutExpired:
        return None, "HOLOINDEX_OWNER_QUERY_PROCESS_TIMEOUT"
    except (OSError, TypeError, ValueError):
        return None, "HOLOINDEX_OWNER_QUERY_PROCESS_FAILED"


def _run_owner_query_once(
    payload: Mapping[str, Any], *, repo_root: Path,
    operation_timeout_seconds: float,
    process_timeout_seconds: float,
) -> Mapping[str, Any]:
    root = Path(repo_root).resolve(strict=False)
    script = (root / "scripts" / "reddog_holoindex_owner_query_once.py").resolve(
        strict=False
    )
    if script.parent != (root / "scripts").resolve(strict=False) or not script.is_file():
        return _failure(str(payload.get("query") or ""), "HOLOINDEX_OWNER_QUERY_SCRIPT_INVALID")
    try:
        python_executable, pythonpath_entries = _owner_python_runtime(sys.executable)
    except (OSError, TypeError, ValueError):
        return _failure(
            str(payload.get("query") or ""),
            "HOLOINDEX_OWNER_QUERY_PROCESS_FAILED",
        )
    command = [
        python_executable, "-S", "-B", str(script),
        "--operation-timeout-seconds", str(operation_timeout_seconds),
    ]
    options: dict[str, Any] = {}
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
        options.update(startupinfo=startup, creationflags=subprocess.CREATE_NO_WINDOW)
    stdout, process_error = _capture_owner_process(
        command, root=root, payload=payload,
        timeout_seconds=process_timeout_seconds, options=options,
        environment=_owner_query_environment(pythonpath_entries),
    )
    if process_error or stdout is None:
        return _failure(str(payload.get("query") or ""), process_error)
    try:
        result = json.loads(stdout.decode("utf-8-sig", errors="strict"))
    except (UnicodeError, ValueError, json.JSONDecodeError):
        return _failure(str(payload.get("query") or ""), "HOLOINDEX_OWNER_QUERY_RESPONSE_INVALID")
    return result if isinstance(result, Mapping) else _failure(
        str(payload.get("query") or ""), "HOLOINDEX_OWNER_QUERY_RESPONSE_INVALID"
    )


def _failure(query: str, error: str) -> Mapping[str, Any]:
    return {
        "ok": False,
        "source": "holoindex_owner_service",
        "query": query,
        "freshness": "UNKNOWN",
        "hits": [],
        "error": error,
        "index_gap_detected": True,
        "stale_reasons": ["holoindex_owner_query_failed"],
        "no_holoindex_reindex_performed": True,
        "no_reindex": True,
        "owner_attempts": 0,
        "owner_retry_performed": False,
        "owner_retry_reason": "",
    }


def _scoped_hits(
    raw_result: Any, allowed_paths: Sequence[str], limit: int,
) -> list[Mapping[str, Any]]:
    hits = [
        hit for hit in holoindex_hits(raw_result)
        if path_is_allowed(str(hit.get("path") or ""), allowed_paths)
    ]
    return hits[:limit]


def _safe_reason(value: Any) -> str:
    text = value if isinstance(value, str) else ""
    return text if _REASON.fullmatch(text) else ""


def _safe_projection(result: Mapping[str, Any], query: str) -> dict[str, Any]:
    projected: dict[str, Any] = {
        "ok": result.get("ok") is True,
        "source": "holoindex_owner_service",
        "query": query,
        "freshness": str(result.get("freshness") or "UNKNOWN").upper(),
        "error": _safe_reason(result.get("error")),
        "stale_reasons": [
            reason for reason in (
                _safe_reason(value) for value in result.get("stale_reasons", ())
            ) if reason
        ] if isinstance(result.get("stale_reasons"), (list, tuple)) else [],
    }
    for field in _DIGEST_FIELDS:
        value = result.get(field)
        if isinstance(value, str) and _DIGEST.fullmatch(value):
            projected[field] = value
    for field in _HEAD_FIELDS:
        value = result.get(field)
        if isinstance(value, str) and _GIT_SHA.fullmatch(value):
            projected[field] = value
    for field in _BOOLEAN_FIELDS:
        if isinstance(result.get(field), bool):
            projected[field] = result[field]
    attempts = result.get("owner_attempts")
    if isinstance(attempts, int) and not isinstance(attempts, bool) and 0 <= attempts <= 2:
        projected["owner_attempts"] = attempts
    retry_reason = _safe_reason(result.get("owner_retry_reason"))
    if retry_reason:
        projected["owner_retry_reason"] = retry_reason
    authority = result.get("semantic_evidence_authority")
    if authority in {"clean_workspace_head", "committed_head_only"}:
        projected["semantic_evidence_authority"] = authority
    if result.get("retrieval_mode") == "semantic":
        projected["retrieval_mode"] = "semantic"
    return projected


def _owner_receipt_matches(result: Mapping[str, Any], query: str) -> bool:
    supplied = result.get("query_receipt")
    if not isinstance(supplied, Mapping):
        return False
    recomputed = build_query_receipt(
        source="holoindex_owner_service",
        source_class="holoindex",
        query=query,
        result=result,
        require_generation=True,
    )
    return dict(supplied) == dict(recomputed)


def _semantic_authority_is_bound(result: Mapping[str, Any]) -> bool:
    authority = result.get("semantic_evidence_authority")
    overlay = result.get("workspace_overlay_present")
    return bool(
        isinstance(overlay, bool)
        and (
            authority == "committed_head_only"
            or (authority == "clean_workspace_head" and overlay is False)
        )
    )


def _successful_result_is_bound(result: Mapping[str, Any], query: Any) -> bool:
    if result.get("ok") is not True:
        return True
    return bool(
        isinstance(query, str)
        and result.get("query") == query
        and result.get("source") == "holoindex_owner_service"
        and str(result.get("freshness") or "").upper() == "CURRENT"
        and all(_DIGEST.fullmatch(str(result.get(field) or "")) for field in _DIGEST_FIELDS)
        and all(_GIT_SHA.fullmatch(str(result.get(field) or "")) for field in _HEAD_FIELDS)
        and result.get("repo_root_digest") == result.get("authority_repo_root_digest")
        and result.get("repo_head_sha") == result.get("workspace_repo_head_sha")
        and result.get("repo_head_sha") == result.get("authority_repo_head_sha")
        and result.get("freshness_generation_id") == result.get("query_replica_generation_id")
        and result.get("retrieval_mode") == "semantic"
        and result.get("index_gap_detected") is False
        and not result.get("stale_reasons")
        and result.get("no_holoindex_reindex_performed") is True
        and result.get("no_reindex") is True
        and result.get("no_authority_worktree_mutation_performed") is True
        and _semantic_authority_is_bound(result)
        and isinstance(result.get("raw_result"), Mapping)
        and _owner_receipt_matches(result, query)
    )


def _normalize_result(
    result: Any, *, query: Any, allowed_paths: Sequence[str], limit: Any,
) -> Mapping[str, Any]:
    query_text = query if isinstance(query, str) else ""
    if not isinstance(result, Mapping) or not _successful_result_is_bound(result, query):
        return _failure(query_text, "HOLOINDEX_OWNER_QUERY_RESPONSE_INVALID")
    normalized = _safe_projection(result, query_text)
    valid_limit = (
        limit if isinstance(limit, int) and not isinstance(limit, bool) and 1 <= limit <= 20
        else 0
    )
    normalized["hits"] = _scoped_hits(
        result.get("raw_result"), allowed_paths, valid_limit,
    ) if valid_limit else []
    return normalized


@dataclass(frozen=True)
class GenerationBoundHoloIndexQueryAdapter:
    """Read-only resident adapter over the governed one-shot owner lifecycle."""

    repo_root: Path
    query_once_runner: QueryOnceRunner | None = None
    operation_timeout_seconds: float = 60.0

    def query(
        self, *, query: str, allowed_paths: Sequence[str], limit: int,
    ) -> Mapping[str, Any]:
        payload = {
            "query": query,
            "limit": limit,
            "retrieval_mode": "semantic",
            "include_bundle": False,
        }
        runner = self.query_once_runner or _run_owner_query_once
        if isinstance(self.operation_timeout_seconds, bool):
            query_text = query if isinstance(query, str) else ""
            return _failure(query_text, "HOLOINDEX_OWNER_QUERY_TIMEOUT_INVALID")
        try:
            timeout = float(self.operation_timeout_seconds)
        except (TypeError, ValueError):
            query_text = query if isinstance(query, str) else ""
            return _failure(query_text, "HOLOINDEX_OWNER_QUERY_TIMEOUT_INVALID")
        if not math.isfinite(timeout) or timeout <= 0 or timeout > 60:
            query_text = query if isinstance(query, str) else ""
            return _failure(query_text, "HOLOINDEX_OWNER_QUERY_TIMEOUT_INVALID")
        deadline = time.monotonic() + timeout
        if not _OWNER_QUERY_ONCE_LOCK.acquire(timeout=timeout):
            query_text = query if isinstance(query, str) else ""
            return _failure(query_text, "HOLOINDEX_OWNER_QUERY_BUSY_TIMEOUT")
        try:
            remaining = deadline - time.monotonic()
            if remaining <= _OWNER_CLEANUP_RESERVE_SECONDS:
                query_text = query if isinstance(query, str) else ""
                return _failure(query_text, "HOLOINDEX_OWNER_QUERY_DEADLINE_EXHAUSTED")
            try:
                result = runner(
                    payload, repo_root=self.repo_root,
                    operation_timeout_seconds=(
                        remaining - _OWNER_CLEANUP_RESERVE_SECONDS
                    ),
                    process_timeout_seconds=remaining,
                )
                return _normalize_result(
                    result, query=query, allowed_paths=allowed_paths, limit=limit,
                )
            except Exception:
                query_text = query if isinstance(query, str) else ""
                return _failure(query_text, "HOLOINDEX_OWNER_QUERY_ONCE_FAILED")
        finally:
            _OWNER_QUERY_ONCE_LOCK.release()


__all__ = ["GenerationBoundHoloIndexQueryAdapter"]
