"""Trusted-host HoloIndex maintenance handshake for autonomous RedDog work.

RedDog query workers remain read-only.  This module is the host/WRE boundary
that may stop an auto-owned query service, run the canonical full baseline
index transaction, prove its exact-HEAD receipt, and restart the owner.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from holo_index.freshness_receipt import (
    BASELINE_QUERY_COLLECTIONS,
    BASELINE_QUERY_FRESHNESS_PATHS,
    HoloIndexFreshnessReceipt,
    evaluate_freshness_for_paths,
    freshness_receipt_path,
    load_freshness_receipt,
)
from holo_index.repository_state import RepositoryState, read_repository_state
from holo_index.query_receipt import generation_binding_from_receipt
from holo_index.storage_contract import (
    HOLOINDEX_SSD_PATH_ENV,
    READONLY_QUERY_ENV,
    resolve_holoindex_ssd_path,
    storage_path_identity,
)

from . import reddog_holoindex_owner_bootstrap as owner_bootstrap
from .holo_query_service_supervisor import SERVICE_TOKEN_ENV, SERVICE_URL_ENV


AUTO_MAINTENANCE_ENV = "REDDOG_HOLOINDEX_AUTO_MAINTENANCE"
MAINTENANCE_TIMEOUT_ENV = "REDDOG_HOLOINDEX_MAINTENANCE_TIMEOUT_SECONDS"

OPERATIONAL_NOT_REQUESTED = "NOT_REQUESTED"
OPERATIONAL_READY = "READY"
OPERATIONAL_REFRESHED = "REFRESHED"
OPERATIONAL_FAILED = "FAILED"

DIRTY_ERROR = "HOLOINDEX_MAINTENANCE_REPOSITORY_DIRTY"
EXTERNAL_OWNER_ERROR = "HOLOINDEX_MAINTENANCE_EXTERNAL_OWNER_UNSUPPORTED"
MAINTENANCE_REQUIRED_ERROR = "HOLOINDEX_MAINTENANCE_REQUIRED"
REFRESH_FAILED_ERROR = "HOLOINDEX_MAINTENANCE_REFRESH_FAILED"
REFRESH_TIMEOUT_ERROR = "HOLOINDEX_MAINTENANCE_REFRESH_TIMEOUT"
RECEIPT_INVALID_ERROR = "HOLOINDEX_MAINTENANCE_RECEIPT_INVALID"
REPOSITORY_CHANGED_ERROR = "HOLOINDEX_MAINTENANCE_REPOSITORY_CHANGED"
TIMEOUT_INVALID_ERROR = "HOLOINDEX_MAINTENANCE_TIMEOUT_INVALID"

_HANDSHAKE_LOCK = threading.Lock()

_REFRESH_ENV_EXACT_DENY = frozenset(
    {
        "HOLO_FAST_SEARCH",
        "HOLO_INDEX_SYMBOLS",
        "HOLO_INDEX_WEB",
        "HOLO_SKIP_MODEL",
        READONLY_QUERY_ENV,
        SERVICE_TOKEN_ENV,
        SERVICE_URL_ENV,
        "WSP_PATH",
        "WSP_PATHS",
    }
)
_REFRESH_ENV_PREFIX_DENY = (
    "HOLO_SYMBOL_",
    "HOLO_WEB_",
    "HOLO_WSP_",
    "HOLOINDEX_WSP_",
)


@dataclass(frozen=True)
class RedDogHoloIndexOperationalResult:
    """Secret-free operational proof returned to the trusted host."""

    ready: bool
    status: str
    refreshed: bool = False
    error: str = ""
    repo_head_sha: str = ""
    generation_id: str = ""
    freshness_reasons: tuple[str, ...] = ()


def _path_identity(path: Path | str) -> str:
    return os.path.normcase(str(Path(path).resolve(strict=False)))


def _receipt_validation(
    *, repo_root: Path, ssd_path: Path, state: RepositoryState
) -> tuple[HoloIndexFreshnessReceipt | None, tuple[str, ...]]:
    receipt_path = freshness_receipt_path(ssd_path)
    try:
        receipt = load_freshness_receipt(receipt_path)
    except FileNotFoundError:
        return None, ("missing_freshness_receipt",)
    except (OSError, TypeError, ValueError):
        return None, ("malformed_freshness_receipt",)

    reasons: list[str] = []
    if _path_identity(receipt.repo_root) != _path_identity(repo_root):
        reasons.append("freshness_repo_root_mismatch")
    if storage_path_identity(receipt.ssd_path) != storage_path_identity(ssd_path):
        reasons.append("freshness_ssd_path_mismatch")
    check = evaluate_freshness_for_paths(
        receipt,
        BASELINE_QUERY_FRESHNESS_PATHS,
        expected_repo_head_sha=state.head_sha,
    )
    if set(check.required_collections) != set(BASELINE_QUERY_COLLECTIONS):
        reasons.append("freshness_baseline_mapping_incomplete")
    by_name = {entry.name: entry for entry in receipt.collections}
    for name in sorted(BASELINE_QUERY_COLLECTIONS):
        entry = by_name.get(name)
        fingerprint = (
            str(entry.embedding_space_fingerprint or "") if entry else ""
        )
        if (
            len(fingerprint) != 71
            or not fingerprint.startswith("sha256:")
            or any(character not in "0123456789abcdef" for character in fingerprint[7:])
        ):
            reasons.append(f"collection_embedding_space_unproven:{name}")
    reasons.extend(check.reasons)
    return receipt, tuple(dict.fromkeys(reasons))


def _timeout_seconds(
    environ: Mapping[str, str], explicit: float | None
) -> tuple[float, str]:
    raw: object = explicit
    if raw is None:
        raw = environ.get(MAINTENANCE_TIMEOUT_ENV, "1800")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0, TIMEOUT_INVALID_ERROR
    if not 1.0 <= value <= 7200.0:
        return 0.0, TIMEOUT_INVALID_ERROR
    return value, ""


def _refresh_environment(
    *, environ: Mapping[str, str], ssd_path: Path
) -> dict[str, str]:
    """Return a canonical maintenance environment without scope overrides."""
    child_environment = dict(environ)
    for name in tuple(child_environment):
        normalized = name.upper()
        if normalized in _REFRESH_ENV_EXACT_DENY or normalized.startswith(
            _REFRESH_ENV_PREFIX_DENY
        ):
            child_environment.pop(name, None)
    child_environment[HOLOINDEX_SSD_PATH_ENV] = str(ssd_path)
    child_environment["HOLO_USE_TURBOQUANT"] = "0"
    child_environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return child_environment


def _run_full_refresh(
    *, repo_root: Path, ssd_path: Path, environ: Mapping[str, str], timeout: float, runner
) -> str:
    child_environment = _refresh_environment(environ=environ, ssd_path=ssd_path)
    command = [
        sys.executable,
        "-B",
        str(repo_root / "holo_index.py"),
        "--index-all",
        "--ssd",
        str(ssd_path),
    ]
    try:
        completed = runner(
            command,
            cwd=str(repo_root),
            env=child_environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return REFRESH_TIMEOUT_ERROR
    except (OSError, subprocess.SubprocessError, ValueError):
        return REFRESH_FAILED_ERROR
    return "" if completed.returncode == 0 else REFRESH_FAILED_ERROR


def _ready_result(
    *, refreshed: bool, state: RepositoryState, receipt: HoloIndexFreshnessReceipt
) -> RedDogHoloIndexOperationalResult:
    return RedDogHoloIndexOperationalResult(
        ready=True,
        status=OPERATIONAL_REFRESHED if refreshed else OPERATIONAL_READY,
        refreshed=refreshed,
        repo_head_sha=state.head_sha,
        generation_id=receipt.generation_id,
    )


def _failure(
    error: str,
    *,
    state: RepositoryState | None = None,
    reasons: tuple[str, ...] = (),
) -> RedDogHoloIndexOperationalResult:
    return RedDogHoloIndexOperationalResult(
        ready=False,
        status=OPERATIONAL_FAILED,
        error=error,
        repo_head_sha=state.head_sha if state is not None else "",
        freshness_reasons=reasons,
    )


def _start_owner(
    *,
    repo_root: Path,
    ssd_path: Path,
    refreshed: bool,
    state: RepositoryState,
    receipt: HoloIndexFreshnessReceipt,
) -> RedDogHoloIndexOperationalResult:
    binding = generation_binding_from_receipt(
        receipt,
        receipt_path=freshness_receipt_path(ssd_path),
    )
    owner = owner_bootstrap.ensure_reddog_holoindex_owner(
        repo_root=repo_root,
        requested=True,
        expected_repo_head_sha=state.head_sha,
        expected_generation_id=receipt.generation_id,
        expected_receipt_digest=str(binding["freshness_receipt_digest"]),
    )
    if not owner.ready:
        return _failure(owner.error or owner_bootstrap.BOOTSTRAP_FAILED_ERROR, state=state)
    return _ready_result(refreshed=refreshed, state=state, receipt=receipt)


def _refresh_and_start_owner(
    *,
    repo_root: Path,
    ssd_path: Path,
    environ: Mapping[str, str],
    timeout: float,
    runner,
    initial_state: RepositoryState,
    initial_reasons: tuple[str, ...],
) -> RedDogHoloIndexOperationalResult:
    owner_bootstrap.cleanup_reddog_holoindex_owner()
    refresh_error = _run_full_refresh(
        repo_root=repo_root,
        ssd_path=ssd_path,
        environ=environ,
        timeout=timeout,
        runner=runner,
    )
    if refresh_error:
        return _failure(refresh_error, state=initial_state, reasons=initial_reasons)
    final_state = read_repository_state(repo_root)
    if not final_state.proven_clean or final_state.head_sha != initial_state.head_sha:
        return _failure(REPOSITORY_CHANGED_ERROR, state=final_state)
    receipt, final_reasons = _receipt_validation(
        repo_root=repo_root,
        ssd_path=ssd_path,
        state=final_state,
    )
    if receipt is None or final_reasons:
        return _failure(
            RECEIPT_INVALID_ERROR,
            state=final_state,
            reasons=final_reasons,
        )
    return _start_owner(
        repo_root=repo_root,
        ssd_path=ssd_path,
        refreshed=True,
        state=final_state,
        receipt=receipt,
    )


def _ensure_locked(
    *,
    repo_root: Path,
    environ: Mapping[str, str],
    auto_maintenance: bool,
    timeout_seconds: float | None,
    runner,
) -> RedDogHoloIndexOperationalResult:
    state = read_repository_state(repo_root)
    if not state.proven_clean:
        return _failure(DIRTY_ERROR, state=state)
    ssd_path = resolve_holoindex_ssd_path(environ=environ)
    receipt, reasons = _receipt_validation(
        repo_root=repo_root,
        ssd_path=ssd_path,
        state=state,
    )
    if receipt is not None and not reasons:
        return _start_owner(
            repo_root=repo_root,
            ssd_path=ssd_path,
            refreshed=False,
            state=state,
            receipt=receipt,
        )
    if not auto_maintenance:
        return _failure(MAINTENANCE_REQUIRED_ERROR, state=state, reasons=reasons)
    if environ.get(SERVICE_URL_ENV) or environ.get(SERVICE_TOKEN_ENV):
        return _failure(EXTERNAL_OWNER_ERROR, state=state, reasons=reasons)
    timeout, timeout_error = _timeout_seconds(environ, timeout_seconds)
    if timeout_error:
        return _failure(timeout_error, state=state, reasons=reasons)
    return _refresh_and_start_owner(
        repo_root=repo_root,
        ssd_path=ssd_path,
        environ=environ,
        timeout=timeout,
        runner=runner,
        initial_state=state,
        initial_reasons=reasons,
    )


def ensure_reddog_holoindex_operational(
    *,
    repo_root: Path | str,
    requested: bool,
    auto_maintenance: bool | None = None,
    timeout_seconds: float | None = None,
    environ: Mapping[str, str] | None = None,
    runner=subprocess.run,
) -> RedDogHoloIndexOperationalResult:
    """Ensure a clean exact-HEAD index and authenticated semantic owner."""
    if not requested:
        return RedDogHoloIndexOperationalResult(False, OPERATIONAL_NOT_REQUESTED)
    env = os.environ if environ is None else environ
    maintenance_enabled = (
        str(env.get(AUTO_MAINTENANCE_ENV, "1")).strip() != "0"
        if auto_maintenance is None
        else bool(auto_maintenance)
    )
    root = Path(repo_root).resolve(strict=False)
    with _HANDSHAKE_LOCK:
        return _ensure_locked(
            repo_root=root,
            environ=env,
            auto_maintenance=maintenance_enabled,
            timeout_seconds=timeout_seconds,
            runner=runner,
        )


__all__ = [
    "AUTO_MAINTENANCE_ENV",
    "DIRTY_ERROR",
    "EXTERNAL_OWNER_ERROR",
    "MAINTENANCE_REQUIRED_ERROR",
    "OPERATIONAL_FAILED",
    "OPERATIONAL_NOT_REQUESTED",
    "OPERATIONAL_READY",
    "OPERATIONAL_REFRESHED",
    "RECEIPT_INVALID_ERROR",
    "REFRESH_FAILED_ERROR",
    "REFRESH_TIMEOUT_ERROR",
    "REPOSITORY_CHANGED_ERROR",
    "RedDogHoloIndexOperationalResult",
    "ensure_reddog_holoindex_operational",
]
