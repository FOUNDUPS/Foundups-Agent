"""Bounded Git identity and changed-path inputs for registry planning."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import subprocess
from typing import Any, Sequence

from .wre_git_bounded_io import (
    resolve_exact_commit, run_bounded_stdout, validate_commit_sha,
)

MAX_CHANGED_PATH_BYTES = 4 * 1024 * 1024
MAX_CHANGED_PATHS = 4096


def canonical_changed_paths(value: Any) -> tuple[str, ...] | None:
    """Return sorted, unique, confined POSIX paths or reject."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return None
    if any(type(item) is not str for item in value):
        return None
    paths = tuple(item for item in value if item != "")
    valid = all(
        item and "\\" not in item and not PurePosixPath(item).is_absolute()
        and all(part not in {"", ".", ".."} for part in PurePosixPath(item).parts)
        for item in paths
    )
    return tuple(sorted(set(paths))) if valid and paths == tuple(sorted(set(paths))) else None


def verified_git_plan_inputs(
    worktree: Path, repo_root: Path, base_sha: str, head_sha: str,
) -> tuple[tuple[str, ...], dict[str, str]]:
    """Bind one Git repository and return its bounded no-rename path set."""
    worktree_r, repo_r = worktree.resolve(strict=True), repo_root.resolve(strict=True)
    validate_commit_sha(base_sha)
    validate_commit_sha(head_sha)
    base = resolve_exact_commit(worktree_r, base_sha)
    head = resolve_exact_commit(worktree_r, head_sha)
    worktree_common = _git_common_dir(worktree_r)
    if worktree_common != _git_common_dir(repo_r):
        raise ValueError("git_repository_mismatch")
    changed = _git_changed_paths(worktree_r, base, head)
    binding = {
        "worktree_path": worktree_r.as_posix(),
        "repository_common_dir": worktree_common.as_posix(),
    }
    return changed, binding


def _git_changed_paths(repo: Path, base_sha: str, head_sha: str) -> tuple[str, ...]:
    lineage = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", base_sha, head_sha],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=30, shell=False, check=False,
    )
    if lineage.returncode != 0:
        raise ValueError("git_lineage_invalid")
    output = run_bounded_stdout(
        ("git", "-C", str(repo), "diff", "--no-renames", "--name-only", "-z",
         base_sha, head_sha),
        cwd=repo, max_bytes=MAX_CHANGED_PATH_BYTES, timeout_s=60,
    )
    paths = canonical_changed_paths(
        output.decode("utf-8", errors="strict").split("\0")
    )
    if not paths or len(paths) > MAX_CHANGED_PATHS:
        raise ValueError("git_changed_paths_invalid")
    return paths


def _git_common_dir(root: Path) -> Path:
    output = run_bounded_stdout(
        ("git", "-C", str(root), "rev-parse", "--path-format=absolute",
         "--git-common-dir"),
        cwd=root, max_bytes=4096, timeout_s=30,
    )
    return Path(output.decode("utf-8", errors="strict").strip()).resolve(strict=True)


__all__ = ["canonical_changed_paths", "verified_git_plan_inputs"]
