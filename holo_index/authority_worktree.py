"""Read-only selection of a clean same-HEAD HoloIndex authority worktree."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from holo_index.repository_state import (
    RepositoryState,
    read_repository_state,
    repository_root_digest,
)


AUTHORITY_REPO_ROOT_ENV = "REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT"
AUTHORITY_ROOT_INVALID = "HOLOINDEX_AUTHORITY_ROOT_INVALID"
AUTHORITY_ROOT_UNRELATED = "HOLOINDEX_AUTHORITY_ROOT_UNRELATED"
AUTHORITY_ROOT_DIRTY = "HOLOINDEX_AUTHORITY_ROOT_DIRTY"
AUTHORITY_ROOT_HEAD_MISMATCH = "HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH"
WORKSPACE_STATE_UNAVAILABLE = "HOLOINDEX_WORKSPACE_STATE_UNAVAILABLE"


@dataclass(frozen=True)
class HoloIndexAuthoritySelection:
    """Internal root selection plus secret-free receipt fields."""

    accepted: bool
    selected_root: Path
    workspace_head_sha: str
    authority_head_sha: str
    authority_root_digest: str
    workspace_overlay_present: bool
    source: str
    rejection_reasons: tuple[str, ...] = ()

    @property
    def error(self) -> str:
        return self.rejection_reasons[0] if self.rejection_reasons else ""


def _git_common_dir(repo_root: Path) -> Path | None:
    argv = [
        "git",
        "-C",
        str(repo_root),
        "rev-parse",
        "--path-format=absolute",
        "--git-common-dir",
    ]
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    value = str(result.stdout or "").strip()
    if result.returncode != 0 or not value:
        return None
    path = Path(value)
    return (path if path.is_absolute() else repo_root / path).resolve(strict=False)


def _failure(
    workspace: Path,
    state: RepositoryState,
    reason: str,
    source: str,
) -> HoloIndexAuthoritySelection:
    return HoloIndexAuthoritySelection(
        accepted=False,
        selected_root=workspace,
        workspace_head_sha=state.head_sha,
        authority_head_sha="",
        authority_root_digest="",
        workspace_overlay_present=not state.proven_clean,
        source=source,
        rejection_reasons=(reason,),
    )


def _candidate(
    workspace: Path,
    environment: Mapping[str, str],
) -> tuple[Path | None, str, str]:
    configured = str(environment.get(AUTHORITY_REPO_ROOT_ENV, "") or "").strip()
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            return None, "configured", AUTHORITY_ROOT_INVALID
        return path.resolve(strict=False), "configured", ""
    sibling = workspace.parent / f"{workspace.name}-holo-authority"
    if sibling.exists():
        return sibling.resolve(strict=False), "deterministic_sibling", ""
    return None, "workspace", ""


def _same_common_dir(
    workspace: Path,
    authority: Path,
    reader: Callable[[Path], Path | None],
) -> bool:
    workspace_common = reader(workspace)
    authority_common = reader(authority)
    return bool(
        workspace_common
        and authority_common
        and os.path.normcase(str(workspace_common))
        == os.path.normcase(str(authority_common))
    )


def _workspace_selection(
    workspace: Path,
    state: RepositoryState,
) -> HoloIndexAuthoritySelection:
    return HoloIndexAuthoritySelection(
        accepted=True,
        selected_root=workspace,
        workspace_head_sha=state.head_sha,
        authority_head_sha=state.head_sha,
        authority_root_digest=repository_root_digest(workspace),
        workspace_overlay_present=not state.proven_clean,
        source="workspace",
    )


def resolve_holoindex_runtime_root(
    workspace_root: Path | str,
    *,
    common_dir_reader: Callable[[Path], Path | None] = _git_common_dir,
) -> Path:
    """Return the same-repository primary worktree for vetted dependencies."""

    workspace = Path(workspace_root).resolve(strict=False)
    common_dir = common_dir_reader(workspace)
    if common_dir is None:
        return workspace
    candidate = common_dir.parent.resolve(strict=False)
    if (
        not candidate.is_dir()
        or not (candidate / ".git").exists()
        or not _same_common_dir(workspace, candidate, common_dir_reader)
    ):
        return workspace
    return candidate


def _validate_authority_candidate(
    workspace: Path,
    workspace_state: RepositoryState,
    authority: Path,
    source: str,
    state_reader: Callable[[Path], RepositoryState],
    common_dir_reader: Callable[[Path], Path | None],
) -> HoloIndexAuthoritySelection:
    if authority == workspace or not authority.is_dir() or not (authority / ".git").exists():
        return _failure(workspace, workspace_state, AUTHORITY_ROOT_INVALID, source)
    if not _same_common_dir(workspace, authority, common_dir_reader):
        return _failure(workspace, workspace_state, AUTHORITY_ROOT_UNRELATED, source)
    authority_state = state_reader(authority)
    if not authority_state.proven_clean:
        return _failure(workspace, workspace_state, AUTHORITY_ROOT_DIRTY, source)
    if authority_state.head_sha != workspace_state.head_sha:
        return _failure(
            workspace, workspace_state, AUTHORITY_ROOT_HEAD_MISMATCH, source
        )
    return HoloIndexAuthoritySelection(
        accepted=True,
        selected_root=authority,
        workspace_head_sha=workspace_state.head_sha,
        authority_head_sha=authority_state.head_sha,
        authority_root_digest=repository_root_digest(authority),
        workspace_overlay_present=not workspace_state.proven_clean,
        source=source,
    )


def resolve_holoindex_authority_root(
    workspace_root: Path | str,
    *,
    environment: Mapping[str, str] | None = None,
    state_reader: Callable[[Path], RepositoryState] = read_repository_state,
    common_dir_reader: Callable[[Path], Path | None] = _git_common_dir,
) -> HoloIndexAuthoritySelection:
    """Select a clean same-HEAD authority root without creating or updating it."""

    workspace = Path(workspace_root).resolve(strict=False)
    workspace_state = state_reader(workspace)
    if workspace_state.head_sha == "unknown":
        return _failure(
            workspace, workspace_state, WORKSPACE_STATE_UNAVAILABLE, "workspace"
        )
    authority, source, candidate_error = _candidate(
        workspace, os.environ if environment is None else environment
    )
    if candidate_error:
        return _failure(workspace, workspace_state, candidate_error, source)
    if authority is None:
        if not workspace_state.proven_clean:
            return _failure(
                workspace, workspace_state, AUTHORITY_ROOT_DIRTY, source
            )
        return _workspace_selection(workspace, workspace_state)
    return _validate_authority_candidate(
        workspace,
        workspace_state,
        authority,
        source,
        state_reader,
        common_dir_reader,
    )


__all__ = [
    "AUTHORITY_REPO_ROOT_ENV",
    "AUTHORITY_ROOT_DIRTY",
    "AUTHORITY_ROOT_HEAD_MISMATCH",
    "AUTHORITY_ROOT_INVALID",
    "AUTHORITY_ROOT_UNRELATED",
    "HoloIndexAuthoritySelection",
    "WORKSPACE_STATE_UNAVAILABLE",
    "resolve_holoindex_authority_root",
    "resolve_holoindex_runtime_root",
]
