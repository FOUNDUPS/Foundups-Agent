"""Post-merge composition of canonical Holo freshness and replica activation."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .reddog_holoindex_maintenance_handshake import (
    OPERATIONAL_FAILED,
    RedDogHoloIndexOperationalResult,
    ensure_reddog_holoindex_operational,
)
from .reddog_holoindex_owner_acquisition import build_owner_query_environment
from .reddog_holoindex_owner_replica_route import (
    QUERY_REPLICA_REQUIRED_ERROR,
    QUERY_REPLICA_ROOT_ENV,
    QUERY_REPLICA_ROUTE_FILE_ENV,
)
from .reddog_holoindex_query_replica_activation import activate_query_replica
from .reddog_holoindex_query_replica_activation_contract import (
    QueryReplicaActivationConfig,
)


POSTMERGE_ROUTE_CONFIG_ERROR = "HOLOINDEX_POSTMERGE_ROUTE_CONFIG_INVALID"
POSTMERGE_OPERATIONAL_BINDING_MISMATCH = (
    "HOLOINDEX_POSTMERGE_OPERATIONAL_BINDING_MISMATCH"
)
POSTMERGE_TARGETS_EXHAUSTED = "HOLOINDEX_POSTMERGE_REPLICA_TARGETS_EXHAUSTED"
_GENERATION_RE = re.compile(r"sha256:([0-9a-f]{64})\Z")
_HEAD_RE = re.compile(r"[0-9a-f]{40}\Z")
_MAX_TARGET_ATTEMPTS = 999


@dataclass(frozen=True)
class _PostmergeReplicaDependencies:
    """Injected effect boundaries for deterministic falsification."""

    ensure_operational: Callable[..., Any] = ensure_reddog_holoindex_operational
    activate: Callable[..., Any] = activate_query_replica
    build_environment: Callable[..., dict[str, str]] = build_owner_query_environment


def _failure(current: Any, error: str) -> RedDogHoloIndexOperationalResult:
    return RedDogHoloIndexOperationalResult(
        False,
        OPERATIONAL_FAILED,
        bool(getattr(current, "refreshed", False)),
        error,
        str(getattr(current, "repo_head_sha", "") or ""),
        str(getattr(current, "generation_id", "") or ""),
        str(getattr(current, "freshness_receipt_digest", "") or ""),
        tuple(getattr(current, "freshness_reasons", ()) or ()),
    )


def _ready_with_refresh(current: Any, operational: Any) -> Any:
    if not getattr(operational, "ready", False):
        return operational
    return RedDogHoloIndexOperationalResult(
        True,
        str(getattr(operational, "status", "") or ""),
        bool(
            getattr(current, "refreshed", False)
            or getattr(operational, "refreshed", False)
        ),
        "",
        str(getattr(operational, "repo_head_sha", "") or ""),
        str(getattr(operational, "generation_id", "") or ""),
        str(getattr(operational, "freshness_receipt_digest", "") or ""),
        tuple(getattr(operational, "freshness_reasons", ()) or ()),
    )


def _binding_matches(current: Any, operational: Any) -> bool:
    """Require owner admission to prove the canonical refresh identity exactly."""

    expected = (
        str(getattr(current, "repo_head_sha", "") or ""),
        str(getattr(current, "generation_id", "") or ""),
        str(getattr(current, "freshness_receipt_digest", "") or ""),
    )
    observed = (
        str(getattr(operational, "repo_head_sha", "") or ""),
        str(getattr(operational, "generation_id", "") or ""),
        str(getattr(operational, "freshness_receipt_digest", "") or ""),
    )
    return bool(getattr(operational, "ready", False) and all(expected) and observed == expected)


def _route_path(environ: Mapping[str, str]) -> Path | None:
    route_value = environ.get(QUERY_REPLICA_ROUTE_FILE_ENV)
    legacy_value = environ.get(QUERY_REPLICA_ROOT_ENV)
    if (
        type(route_value) is not str
        or not route_value
        or route_value != route_value.strip()
        or not Path(route_value).is_absolute()
        or (type(legacy_value) is str and bool(legacy_value.strip()))
        or (legacy_value is not None and type(legacy_value) is not str)
    ):
        return None
    route_path = Path(route_value)
    if route_path.parent == route_path or route_path.parent.parent == route_path.parent:
        return None
    return route_path


def _path_absent(path: Path) -> bool:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return False


def _next_targets(
    *, route_path: Path, generation_id: str, repo_head_sha: str,
) -> tuple[Path, Path] | None:
    generation = _GENERATION_RE.fullmatch(generation_id)
    if generation is None or _HEAD_RE.fullmatch(repo_head_sha) is None:
        return None
    replica_parent = route_path.parent.parent
    generation_prefix = generation.group(1)[:8]
    for attempt in range(1, _MAX_TARGET_ATTEMPTS + 1):
        replica = replica_parent / f"{generation_prefix}-r{attempt}"
        receipt = route_path.parent / (
            f"activation_{repo_head_sha[:8]}_r{attempt}.json"
        )
        if _path_absent(replica) and _path_absent(receipt):
            return replica, receipt
    return None


def _operational(
    dependencies: _PostmergeReplicaDependencies,
    *, repo_root: Path, owner_runtime_root: Path, environ: Mapping[str, str],
) -> Any:
    return dependencies.ensure_operational(
        repo_root=repo_root,
        owner_runtime_root=owner_runtime_root,
        requested=True,
        auto_maintenance=False,
        environ=environ,
    )


def _current_proof_valid(current: Any, expected_repo_head_sha: str) -> bool:
    return bool(
        getattr(current, "ready", False) is True
        and getattr(current, "repo_head_sha", "") == expected_repo_head_sha
        and getattr(current, "generation_id", "")
        and getattr(current, "freshness_receipt_digest", "")
    )


def _route_environment(
    dependencies: _PostmergeReplicaDependencies,
    environ: Mapping[str, str],
) -> Mapping[str, str] | None:
    try:
        return dependencies.build_environment(process_environment=environ)
    except (OSError, TypeError, ValueError):
        return None


def _existing_route_result(
    current: Any,
    operational: Any,
) -> RedDogHoloIndexOperationalResult | None:
    if getattr(operational, "ready", False) is True:
        if not _binding_matches(current, operational):
            return _failure(current, POSTMERGE_OPERATIONAL_BINDING_MISMATCH)
        return _ready_with_refresh(current, operational)
    if getattr(operational, "error", "") != QUERY_REPLICA_REQUIRED_ERROR:
        error = str(getattr(operational, "error", "") or OPERATIONAL_FAILED)
        return _failure(current, error)
    return None


def _activate_missing_replica(
    dependencies: _PostmergeReplicaDependencies,
    *,
    repo_root: Path,
    owner_runtime_root: Path,
    canonical_store: Path,
    expected_repo_head_sha: str,
    current: Any,
    environ: Mapping[str, str],
    timeout_seconds: float,
) -> str:
    """Activate one absent-only replica target and return a stable error."""

    route_path = _route_path(environ)
    if route_path is None:
        return POSTMERGE_ROUTE_CONFIG_ERROR
    targets = _next_targets(
        route_path=route_path,
        generation_id=str(getattr(current, "generation_id", "") or ""),
        repo_head_sha=expected_repo_head_sha,
    )
    if targets is None:
        return POSTMERGE_TARGETS_EXHAUSTED
    replica_root, receipt_path = targets
    activation = dependencies.activate(
        QueryReplicaActivationConfig(
            repo_root=repo_root,
            owner_runtime_root=owner_runtime_root,
            canonical_store=canonical_store,
            replica_root=replica_root,
            route_path=route_path,
            route_runtime_root=route_path.parent,
            receipt_path=receipt_path,
            expected_repo_head_sha=expected_repo_head_sha,
            timeout_seconds=timeout_seconds,
            real=True,
        )
    )
    if (
        getattr(activation, "ok", False) is True
        and getattr(activation, "route_committed", False) is True
        and getattr(activation, "post_query_replica_unchanged", False) is True
    ):
        return ""
    return str(
        getattr(activation, "error", "") or "QUERY_REPLICA_ACTIVATION_FAILED"
    )


def _ensure_postmerge_query_replica_operational_for_test(
    *,
    repo_root: Path | str, owner_runtime_root: Path | str,
    canonical_store: Path | str, expected_repo_head_sha: str,
    current: Any, environ: Mapping[str, str],
    timeout_seconds: float = 1800.0,
    dependencies: _PostmergeReplicaDependencies | None = None,
) -> RedDogHoloIndexOperationalResult:
    """Activate one new replica when exact-current owner admission needs it."""
    deps = dependencies or _PostmergeReplicaDependencies()
    root = Path(repo_root).resolve(strict=False)
    runtime_root = Path(owner_runtime_root).resolve(strict=False)
    store = Path(canonical_store).resolve(strict=False)
    if not _current_proof_valid(current, expected_repo_head_sha):
        return _failure(current, "HOLOINDEX_POSTMERGE_CURRENT_PROOF_INVALID")
    route_environment = _route_environment(deps, environ)
    if route_environment is None:
        return _failure(current, POSTMERGE_ROUTE_CONFIG_ERROR)
    initial = _operational(
        deps,
        repo_root=root,
        owner_runtime_root=runtime_root,
        environ=route_environment,
    )
    existing = _existing_route_result(current, initial)
    if existing is not None:
        return existing
    activation_error = _activate_missing_replica(
        deps,
        repo_root=root,
        owner_runtime_root=runtime_root,
        canonical_store=store,
        expected_repo_head_sha=expected_repo_head_sha,
        current=current,
        environ=route_environment,
        timeout_seconds=timeout_seconds,
    )
    if activation_error:
        return _failure(current, activation_error)
    final = _operational(
        deps,
        repo_root=root,
        owner_runtime_root=runtime_root,
        environ=route_environment,
    )
    if getattr(final, "ready", False) is not True:
        return _failure(current, str(getattr(final, "error", "") or OPERATIONAL_FAILED))
    if not _binding_matches(current, final):
        return _failure(current, POSTMERGE_OPERATIONAL_BINDING_MISMATCH)
    return _ready_with_refresh(current, final)


def ensure_postmerge_query_replica_operational(
    *,
    repo_root: Path | str, owner_runtime_root: Path | str,
    canonical_store: Path | str, expected_repo_head_sha: str,
    current: Any, environ: Mapping[str, str],
    timeout_seconds: float = 1800.0,
) -> RedDogHoloIndexOperationalResult:
    """Compose post-merge activation using sealed production dependencies."""

    return _ensure_postmerge_query_replica_operational_for_test(
        repo_root=repo_root,
        owner_runtime_root=owner_runtime_root,
        canonical_store=canonical_store,
        expected_repo_head_sha=expected_repo_head_sha,
        current=current,
        environ=environ,
        timeout_seconds=timeout_seconds,
    )


__all__ = [
    "POSTMERGE_OPERATIONAL_BINDING_MISMATCH",
    "POSTMERGE_ROUTE_CONFIG_ERROR",
    "POSTMERGE_TARGETS_EXHAUSTED",
    "ensure_postmerge_query_replica_operational",
]
