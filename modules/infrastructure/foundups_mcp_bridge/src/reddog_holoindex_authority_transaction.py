"""Cross-process exact-SHA authority worktree maintenance transaction."""

from __future__ import annotations

import os
import re
import subprocess
import threading
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from holo_index.freshness_receipt import BASELINE_QUERY_COLLECTIONS
from holo_index.maintenance_lock import (
    MaintenanceLeaseBusy,
    MaintenanceLockError,
    acquire_authority_update_lease,
)
from holo_index.maintenance_session import MaintenanceSession, MaintenanceSessionError
from holo_index.repository_state import read_repository_state, repository_root_digest
from holo_index.storage_contract import resolve_holoindex_ssd_path

from .reddog_holoindex_authority_marker import (
    clear_authority_block_marker as _clear_block_marker,
    marker_is_only_dirty_path as _marker_is_only_dirty_path,
    publish_authority_block_marker as _publish_block_marker,
    valid_authority_block_marker as _valid_block_marker,
)
from .reddog_holoindex_authority_types import (
    AuthorityContext as _AuthorityContext,
    AuthorityDependencies as _AuthorityDependencies,
    GitRunner,
    PreparedAuthority as _PreparedAuthority,
    RedDogHoloIndexAuthorityTransactionResult,
)
from .reddog_holoindex_maintenance_handshake import (
    OPERATIONAL_FAILED,
    RedDogHoloIndexOperationalResult,
    ensure_reddog_holoindex_current,
)
from .reddog_holoindex_owner_bootstrap import cleanup_reddog_holoindex_owner
from .reddog_holoindex_postmerge_replica import (
    POSTMERGE_OPERATIONAL_BINDING_MISMATCH,
    ensure_postmerge_query_replica_operational,
)


_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_PROCESS_LOCK = threading.Lock()


def _default_git_runner(
    argv: Sequence[str], cwd: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
        shell=False,
    )


def _run_git(
    runner: GitRunner,
    root: Path,
    *args: str,
) -> subprocess.CompletedProcess[str] | None:
    try:
        return runner(("git", *args), root)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _fetch_origin_main(runner: GitRunner, root: Path) -> tuple[str, str]:
    fetched = _run_git(runner, root, "fetch", "--quiet", "origin", "main")
    if fetched is None or fetched.returncode != 0:
        return "", "origin_main_fetch_failed"
    resolved = _run_git(runner, root, "rev-parse", "FETCH_HEAD")
    sha = str(resolved.stdout or "").strip().lower() if resolved else ""
    if (
        resolved is None
        or resolved.returncode != 0
        or _SHA_RE.fullmatch(sha) is None
    ):
        return "", "origin_main_sha_unproven"
    return sha, ""


def _is_ancestor(
    runner: GitRunner,
    root: Path,
    ancestor_sha: str,
    descendant_sha: str,
) -> bool:
    if ancestor_sha == descendant_sha:
        return True
    result = _run_git(
        runner,
        root,
        "merge-base",
        "--is-ancestor",
        ancestor_sha,
        descendant_sha,
    )
    return result is not None and result.returncode == 0


def _common_git_dir(
    runner: GitRunner,
    root: Path,
) -> Path | None:
    result = _run_git(
        runner,
        root,
        "rev-parse",
        "--path-format=absolute",
        "--git-common-dir",
    )
    value = str(result.stdout or "").strip() if result else ""
    if result is None or result.returncode != 0 or not value:
        return None
    path = Path(value)
    return (path if path.is_absolute() else root / path).resolve(strict=False)


def _authority_binding_valid(
    *,
    runner: GitRunner,
    workspace_root: Path,
    authority_root: Path,
    expected_digest: str,
) -> bool:
    if (
        not expected_digest
        or authority_root == workspace_root
        or not authority_root.is_dir()
        or not (authority_root / ".git").exists()
    ):
        return False
    workspace_common = _common_git_dir(runner, workspace_root)
    authority_common = _common_git_dir(runner, authority_root)
    if workspace_common is None or authority_common is None:
        return False
    return bool(
        os.path.normcase(str(workspace_common))
        == os.path.normcase(str(authority_common))
        and repository_root_digest(authority_root) == expected_digest
    )


def _switch_exact_sha(runner: GitRunner, root: Path, target_sha: str) -> bool:
    switched = _run_git(
        runner,
        root,
        "switch",
        "--detach",
        "--quiet",
        target_sha,
    )
    if switched is None or switched.returncode != 0:
        return False
    state = read_repository_state(root)
    return bool(state.head_sha == target_sha)


def _invalidate_generation(
    *,
    repo_root: Path,
    ssd_path: Path,
    source: str,
) -> bool:
    try:
        session = MaintenanceSession.begin(
            ssd_path=ssd_path,
            repo_root=repo_root,
            planned_collections=BASELINE_QUERY_COLLECTIONS,
            source=source,
        )
    except (MaintenanceLockError, MaintenanceSessionError, OSError, ValueError):
        return False
    session.close()
    return True


def _operational_valid(
    operational: Any, target_sha: str,
) -> bool:
    return bool(
        getattr(operational, "ready", False)
        and getattr(operational, "repo_head_sha", "") == target_sha
        and getattr(operational, "generation_id", "")
        and getattr(operational, "freshness_receipt_digest", "")
    )


def _operational_failure(
    *, target_sha: str, observed_sha: str, operational: Any,
) -> RedDogHoloIndexAuthorityTransactionResult:
    return RedDogHoloIndexAuthorityTransactionResult(
        False,
        "REJECTED",
        target_repo_head_sha=target_sha,
        observed_origin_main_sha=observed_sha,
        error=str(
            getattr(operational, "error", "")
            or "holoindex_operational_proof_invalid"
        ),
    )


def _enforce_canonical_operational_binding(
    *, current: Any, operational: Any, target_sha: str,
) -> Any:
    """Reject an activation seam that substitutes another canonical identity."""

    expected_generation = str(getattr(current, "generation_id", "") or "")
    expected_receipt = str(
        getattr(current, "freshness_receipt_digest", "") or ""
    )
    if not getattr(operational, "ready", False):
        return operational
    if (
        getattr(operational, "repo_head_sha", "") == target_sha
        and str(getattr(operational, "generation_id", "") or "")
        == expected_generation
        and str(getattr(operational, "freshness_receipt_digest", "") or "")
        == expected_receipt
        and expected_generation
        and expected_receipt
    ):
        return operational
    return RedDogHoloIndexOperationalResult(
        False,
        OPERATIONAL_FAILED,
        bool(getattr(current, "refreshed", False)),
        POSTMERGE_OPERATIONAL_BINDING_MISMATCH,
        target_sha,
        expected_generation,
        expected_receipt,
        tuple(getattr(current, "freshness_reasons", ()) or ()),
    )


def _reject(
    context: _AuthorityContext,
    error: str,
    *,
    observed_sha: str = "",
    status: str = "REJECTED",
) -> RedDogHoloIndexAuthorityTransactionResult:
    return RedDogHoloIndexAuthorityTransactionResult(
        False,
        status,
        target_repo_head_sha=context.target_sha,
        observed_origin_main_sha=observed_sha,
        error=error,
    )


def _validate_initial_authority(
    context: _AuthorityContext,
    dependencies: _AuthorityDependencies,
) -> tuple[str, bool, RedDogHoloIndexAuthorityTransactionResult | None]:
    if not _authority_binding_valid(
        runner=dependencies.git_runner,
        workspace_root=context.workspace,
        authority_root=context.root,
        expected_digest=context.expected_digest,
    ):
        return "", False, _reject(context, "authority_root_binding_invalid")
    initial_state = read_repository_state(context.root)
    recovering_block = _valid_block_marker(context.root)
    if not initial_state.proven_clean and not (
        recovering_block
        and _marker_is_only_dirty_path(context.root, dependencies.git_runner)
    ):
        return "", recovering_block, _reject(context, "authority_root_dirty")
    observed_sha, fetch_error = _fetch_origin_main(
        dependencies.git_runner, context.root
    )
    if fetch_error or observed_sha != context.target_sha:
        return observed_sha, recovering_block, _reject(
            context,
            fetch_error or "target_superseded",
            observed_sha=observed_sha,
            status="SUPERSEDED" if observed_sha else "REJECTED",
        )
    if not _is_ancestor(
        dependencies.git_runner,
        context.root,
        initial_state.head_sha,
        context.target_sha,
    ):
        return observed_sha, recovering_block, _reject(
            context,
            "authority_non_forward_update_rejected",
            observed_sha=observed_sha,
        )
    return observed_sha, recovering_block, None


def _switch_and_refresh(
    context: _AuthorityContext,
    dependencies: _AuthorityDependencies,
    *,
    observed_sha: str,
    recovering_block: bool,
) -> _PreparedAuthority | RedDogHoloIndexAuthorityTransactionResult:
    dependencies.cleanup_owner()
    if not _switch_exact_sha(
        dependencies.git_runner, context.root, context.target_sha
    ):
        return _reject(
            context, "authority_worktree_update_failed", observed_sha=observed_sha
        )
    if recovering_block and not _clear_block_marker(context.root):
        return _reject(
            context,
            "authority_block_marker_clear_failed",
            observed_sha=observed_sha,
        )
    switched_state = read_repository_state(context.root)
    if not switched_state.proven_clean or switched_state.head_sha != context.target_sha:
        return _reject(
            context,
            "authority_worktree_post_switch_invalid",
            observed_sha=observed_sha,
        )
    operational = dependencies.ensure_current(
        repo_root=context.root,
        owner_runtime_root=context.workspace,
        requested=True,
        auto_maintenance=True,
        environ=context.environ,
    )
    if not _operational_valid(operational, context.target_sha):
        return _operational_failure(
            target_sha=context.target_sha,
            observed_sha=observed_sha,
            operational=operational,
        )
    return _PreparedAuthority(observed_sha, operational)


def _prepare_authority_locked(
    context: _AuthorityContext,
    dependencies: _AuthorityDependencies,
) -> _PreparedAuthority | RedDogHoloIndexAuthorityTransactionResult:
    observed_sha, recovering_block, rejected = _validate_initial_authority(
        context, dependencies
    )
    if rejected is not None:
        return rejected
    return _switch_and_refresh(
        context,
        dependencies,
        observed_sha=observed_sha,
        recovering_block=recovering_block,
    )


def _post_activation_authority_error(
    context: _AuthorityContext,
    dependencies: _AuthorityDependencies,
) -> str:
    if not _authority_binding_valid(
        runner=dependencies.git_runner,
        workspace_root=context.workspace,
        authority_root=context.root,
        expected_digest=context.expected_digest,
    ):
        return "authority_root_binding_invalid"
    state = read_repository_state(context.root)
    if not state.proven_clean or state.head_sha != context.target_sha:
        return "authority_worktree_post_activation_invalid"
    return ""


def _superseded_result(
    context: _AuthorityContext,
    dependencies: _AuthorityDependencies,
    *,
    latest_sha: str,
    latest_error: str,
) -> RedDogHoloIndexAuthorityTransactionResult:
    safe_invalidation = bool(
        not latest_error
        and _SHA_RE.fullmatch(latest_sha)
        and _is_ancestor(
            dependencies.git_runner,
            context.root,
            context.target_sha,
            latest_sha,
        )
        and _switch_exact_sha(dependencies.git_runner, context.root, latest_sha)
    )
    if not safe_invalidation:
        safe_invalidation = _invalidate_generation(
            repo_root=context.root,
            ssd_path=context.ssd_path,
            source="postmerge_target_superseded",
        )
    durable_blocked = safe_invalidation or _publish_block_marker(context.root)
    error = latest_error or (
        "target_superseded"
        if safe_invalidation
        else (
            "target_superseded_invalidation_failed"
            if durable_blocked
            else "target_superseded_fail_closed_marker_failed"
        )
    )
    return _reject(
        context,
        error,
        observed_sha=latest_sha,
        status="SUPERSEDED" if safe_invalidation else "REJECTED",
    )


def _success_result(
    context: _AuthorityContext,
    *,
    latest_sha: str,
    operational: Any,
) -> RedDogHoloIndexAuthorityTransactionResult:
    refreshed = bool(getattr(operational, "refreshed", False))
    return RedDogHoloIndexAuthorityTransactionResult(
        True,
        "REFRESHED" if refreshed else "READY",
        target_repo_head_sha=context.target_sha,
        observed_origin_main_sha=latest_sha,
        generation_id=str(getattr(operational, "generation_id", "") or ""),
        freshness_receipt_digest=str(
            getattr(operational, "freshness_receipt_digest", "") or ""
        ),
        refreshed=refreshed,
    )


def _finalize_locked(
    context: _AuthorityContext,
    dependencies: _AuthorityDependencies,
    operational: Any,
) -> RedDogHoloIndexAuthorityTransactionResult:
    authority_error = _post_activation_authority_error(context, dependencies)
    if authority_error:
        dependencies.cleanup_owner()
        return _reject(context, authority_error)
    latest_sha, latest_error = _fetch_origin_main(
        dependencies.git_runner, context.root
    )
    if latest_error or latest_sha != context.target_sha:
        dependencies.cleanup_owner()
        return _superseded_result(
            context,
            dependencies,
            latest_sha=latest_sha,
            latest_error=latest_error,
        )
    if not _operational_valid(operational, context.target_sha):
        dependencies.cleanup_owner()
        return _operational_failure(
            target_sha=context.target_sha,
            observed_sha=latest_sha,
            operational=operational,
        )
    return _success_result(context, latest_sha=latest_sha, operational=operational)


def _lease_failure(
    context: _AuthorityContext,
    *,
    busy: bool,
) -> RedDogHoloIndexAuthorityTransactionResult:
    return _reject(
        context,
        "authority_update_lease_busy" if busy else "authority_update_lease_failed",
        status="BUSY" if busy else "REJECTED",
    )


def _run_initial_phase(
    context: _AuthorityContext,
    dependencies: _AuthorityDependencies,
) -> _PreparedAuthority | RedDogHoloIndexAuthorityTransactionResult:
    try:
        with dependencies.lease_factory(context.ssd_path):
            return _prepare_authority_locked(context, dependencies)
    except MaintenanceLeaseBusy:
        return _lease_failure(context, busy=True)
    except (MaintenanceLockError, OSError, ValueError):
        return _lease_failure(context, busy=False)


def _run_activation_phase(
    context: _AuthorityContext,
    dependencies: _AuthorityDependencies,
    prepared: _PreparedAuthority,
) -> RedDogHoloIndexAuthorityTransactionResult:
    try:
        operational = dependencies.activate_replica(
            repo_root=context.root,
            owner_runtime_root=context.workspace,
            canonical_store=context.ssd_path,
            expected_repo_head_sha=context.target_sha,
            current=prepared.operational,
            environ=context.environ,
        )
        operational = _enforce_canonical_operational_binding(
            current=prepared.operational,
            operational=operational,
            target_sha=context.target_sha,
        )
        with dependencies.lease_factory(context.ssd_path):
            return _finalize_locked(context, dependencies, operational)
    except MaintenanceLeaseBusy:
        dependencies.cleanup_owner()
        return _lease_failure(context, busy=True)
    except (MaintenanceLockError, OSError, ValueError):
        dependencies.cleanup_owner()
        return _lease_failure(context, busy=False)


def _advance_reddog_holoindex_authority_for_test(
    *,
    workspace_root: Path | str,
    repo_root: Path | str,
    target_repo_head_sha: str,
    expected_authority_root_digest: str,
    environ: Mapping[str, str] | None = None,
    git_runner: GitRunner = _default_git_runner,
    ensure_current: Callable[..., Any] = ensure_reddog_holoindex_current,
    activate_replica: Callable[..., Any] = (
        ensure_postmerge_query_replica_operational
    ),
    cleanup_owner: Callable[[], None] = cleanup_reddog_holoindex_owner,
    lease_factory: Callable[[Path | str], Any] = acquire_authority_update_lease,
) -> RedDogHoloIndexAuthorityTransactionResult:
    """Internal dependency seam; production callers use sealed defaults."""
    workspace = Path(workspace_root).resolve(strict=False)
    root = Path(repo_root).resolve(strict=False)
    target_sha = str(target_repo_head_sha or "").strip().lower()
    if _SHA_RE.fullmatch(target_sha) is None:
        return RedDogHoloIndexAuthorityTransactionResult(
            False,
            "REJECTED",
            error="target_repo_head_sha_invalid",
        )
    env = os.environ if environ is None else environ
    context = _AuthorityContext(
        workspace,
        root,
        target_sha,
        expected_authority_root_digest,
        resolve_holoindex_ssd_path(environ=env),
        env,
    )
    dependencies = _AuthorityDependencies(
        git_runner,
        ensure_current,
        activate_replica,
        cleanup_owner,
        lease_factory,
    )
    with _PROCESS_LOCK:
        prepared = _run_initial_phase(context, dependencies)
        if isinstance(prepared, RedDogHoloIndexAuthorityTransactionResult):
            return prepared
        return _run_activation_phase(context, dependencies, prepared)


def advance_reddog_holoindex_authority(
    *,
    workspace_root: Path | str,
    repo_root: Path | str,
    target_repo_head_sha: str,
    expected_authority_root_digest: str,
    environ: Mapping[str, str] | None = None,
) -> RedDogHoloIndexAuthorityTransactionResult:
    """Advance one authority checkout through sealed production effects."""

    return _advance_reddog_holoindex_authority_for_test(
        workspace_root=workspace_root,
        repo_root=repo_root,
        target_repo_head_sha=target_repo_head_sha,
        expected_authority_root_digest=expected_authority_root_digest,
        environ=environ,
    )


__all__ = [
    "RedDogHoloIndexAuthorityTransactionResult",
    "advance_reddog_holoindex_authority",
]
