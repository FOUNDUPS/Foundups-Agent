"""Cross-process exact-SHA authority worktree maintenance transaction."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from holo_index.freshness_receipt import BASELINE_QUERY_COLLECTIONS
from holo_index.maintenance_lock import (
    AUTHORITY_BLOCK_MARKER_CONTENT,
    AUTHORITY_BLOCK_MARKER_FILENAME,
    MaintenanceLeaseBusy,
    MaintenanceLockError,
    acquire_authority_update_lease,
    authority_block_marker_path,
    authority_block_marker_valid,
)
from holo_index.maintenance_session import MaintenanceSession, MaintenanceSessionError
from holo_index.repository_state import read_repository_state, repository_root_digest
from holo_index.storage_contract import resolve_holoindex_ssd_path

from .reddog_holoindex_maintenance_handshake import (
    RedDogHoloIndexOperationalResult,
    ensure_reddog_holoindex_operational,
)
from .reddog_holoindex_owner_bootstrap import cleanup_reddog_holoindex_owner


_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_PROCESS_LOCK = threading.Lock()

GitRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class RedDogHoloIndexAuthorityTransactionResult:
    """Secret-free exact-SHA authority transaction result."""

    ready: bool
    status: str
    target_repo_head_sha: str = ""
    observed_origin_main_sha: str = ""
    generation_id: str = ""
    freshness_receipt_digest: str = ""
    refreshed: bool = False
    error: str = ""


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


def _block_marker_path(root: Path) -> Path:
    return authority_block_marker_path(root)


def _valid_block_marker(root: Path) -> bool:
    return authority_block_marker_valid(root)


def _publish_block_marker(root: Path) -> bool:
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f"{AUTHORITY_BLOCK_MARKER_FILENAME}.",
            suffix=".tmp",
            dir=root,
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(AUTHORITY_BLOCK_MARKER_CONTENT)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, _block_marker_path(root))
        return _valid_block_marker(root)
    except OSError:
        return False
    finally:
        if temporary_name:
            try:
                Path(temporary_name).unlink(missing_ok=True)
            except OSError:
                pass


def _clear_block_marker(root: Path) -> bool:
    marker = _block_marker_path(root)
    if not marker.exists():
        return True
    if not _valid_block_marker(root):
        return False
    try:
        marker.unlink()
    except OSError:
        return False
    return not marker.exists()


def _marker_is_only_dirty_path(runner: GitRunner, root: Path) -> bool:
    status_result = _run_git(
        runner,
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    if status_result is None or status_result.returncode != 0:
        return False
    entries = [
        line.strip()
        for line in str(status_result.stdout or "").splitlines()
        if line.strip()
    ]
    return entries == [f"?? {AUTHORITY_BLOCK_MARKER_FILENAME}"]


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


def advance_reddog_holoindex_authority(
    *,
    workspace_root: Path | str,
    repo_root: Path | str,
    target_repo_head_sha: str,
    expected_authority_root_digest: str,
    environ: Mapping[str, str] | None = None,
    git_runner: GitRunner = _default_git_runner,
    ensure_operational: Callable[..., Any] = ensure_reddog_holoindex_operational,
    cleanup_owner: Callable[[], None] = cleanup_reddog_holoindex_owner,
    lease_factory: Callable[[Path | str], Any] = acquire_authority_update_lease,
) -> RedDogHoloIndexAuthorityTransactionResult:
    """Advance one clean authority checkout and prove its exact-HEAD index."""
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
    ssd_path = resolve_holoindex_ssd_path(environ=env)

    try:
        with _PROCESS_LOCK, lease_factory(ssd_path):
            if not _authority_binding_valid(
                runner=git_runner,
                workspace_root=workspace,
                authority_root=root,
                expected_digest=expected_authority_root_digest,
            ):
                return RedDogHoloIndexAuthorityTransactionResult(
                    False,
                    "REJECTED",
                    target_repo_head_sha=target_sha,
                    error="authority_root_binding_invalid",
                )
            initial_state = read_repository_state(root)
            recovering_block = _valid_block_marker(root)
            if not initial_state.proven_clean and not (
                recovering_block and _marker_is_only_dirty_path(git_runner, root)
            ):
                return RedDogHoloIndexAuthorityTransactionResult(
                    False,
                    "REJECTED",
                    target_repo_head_sha=target_sha,
                    error="authority_root_dirty",
                )
            observed_sha, fetch_error = _fetch_origin_main(git_runner, root)
            if fetch_error or observed_sha != target_sha:
                return RedDogHoloIndexAuthorityTransactionResult(
                    False,
                    "SUPERSEDED" if observed_sha else "REJECTED",
                    target_repo_head_sha=target_sha,
                    observed_origin_main_sha=observed_sha,
                    error=fetch_error or "target_superseded",
                )
            if not _is_ancestor(
                git_runner,
                root,
                initial_state.head_sha,
                target_sha,
            ):
                return RedDogHoloIndexAuthorityTransactionResult(
                    False,
                    "REJECTED",
                    target_repo_head_sha=target_sha,
                    observed_origin_main_sha=observed_sha,
                    error="authority_non_forward_update_rejected",
                )

            cleanup_owner()
            if not _switch_exact_sha(git_runner, root, target_sha):
                return RedDogHoloIndexAuthorityTransactionResult(
                    False,
                    "REJECTED",
                    target_repo_head_sha=target_sha,
                    observed_origin_main_sha=observed_sha,
                    error="authority_worktree_update_failed",
                )
            if recovering_block and not _clear_block_marker(root):
                return RedDogHoloIndexAuthorityTransactionResult(
                    False,
                    "REJECTED",
                    target_repo_head_sha=target_sha,
                    observed_origin_main_sha=observed_sha,
                    error="authority_block_marker_clear_failed",
                )
            switched_state = read_repository_state(root)
            if (
                not switched_state.proven_clean
                or switched_state.head_sha != target_sha
            ):
                return RedDogHoloIndexAuthorityTransactionResult(
                    False,
                    "REJECTED",
                    target_repo_head_sha=target_sha,
                    observed_origin_main_sha=observed_sha,
                    error="authority_worktree_post_switch_invalid",
                )
            operational: RedDogHoloIndexOperationalResult = ensure_operational(
                repo_root=root,
                owner_runtime_root=workspace,
                requested=True,
                auto_maintenance=True,
                environ=env,
            )
            if (
                not operational.ready
                or operational.repo_head_sha != target_sha
                or not operational.generation_id
                or not operational.freshness_receipt_digest
            ):
                return RedDogHoloIndexAuthorityTransactionResult(
                    False,
                    "REJECTED",
                    target_repo_head_sha=target_sha,
                    observed_origin_main_sha=observed_sha,
                    error=operational.error
                    or "holoindex_operational_proof_invalid",
                )

            latest_sha, latest_error = _fetch_origin_main(git_runner, root)
            if latest_error or latest_sha != target_sha:
                cleanup_owner()
                safe_invalidation = False
                if (
                    not latest_error
                    and _SHA_RE.fullmatch(latest_sha)
                    and _is_ancestor(git_runner, root, target_sha, latest_sha)
                    and _switch_exact_sha(git_runner, root, latest_sha)
                ):
                    safe_invalidation = True
                if not safe_invalidation:
                    safe_invalidation = _invalidate_generation(
                        repo_root=root,
                        ssd_path=ssd_path,
                        source="postmerge_target_superseded",
                    )
                durable_blocked = (
                    safe_invalidation or _publish_block_marker(root)
                )
                return RedDogHoloIndexAuthorityTransactionResult(
                    False,
                    "SUPERSEDED" if safe_invalidation else "REJECTED",
                    target_repo_head_sha=target_sha,
                    observed_origin_main_sha=latest_sha,
                    error=(
                        latest_error
                        or (
                            "target_superseded"
                            if safe_invalidation
                            else (
                                "target_superseded_invalidation_failed"
                                if durable_blocked
                                else "target_superseded_fail_closed_marker_failed"
                            )
                        )
                    ),
                )

            return RedDogHoloIndexAuthorityTransactionResult(
                True,
                "REFRESHED" if operational.refreshed else "READY",
                target_repo_head_sha=target_sha,
                observed_origin_main_sha=latest_sha,
                generation_id=operational.generation_id,
                freshness_receipt_digest=operational.freshness_receipt_digest,
                refreshed=bool(operational.refreshed),
            )
    except MaintenanceLeaseBusy:
        return RedDogHoloIndexAuthorityTransactionResult(
            False,
            "BUSY",
            target_repo_head_sha=target_sha,
            error="authority_update_lease_busy",
        )
    except (MaintenanceLockError, OSError, ValueError):
        return RedDogHoloIndexAuthorityTransactionResult(
            False,
            "REJECTED",
            target_repo_head_sha=target_sha,
            error="authority_update_lease_failed",
        )


__all__ = [
    "RedDogHoloIndexAuthorityTransactionResult",
    "advance_reddog_holoindex_authority",
]
