"""Fail-closed repository-state proof for HoloIndex freshness consumers.

An exact commit SHA binds content only when the worktree has no tracked or
untracked changes. This helper uses argv-only Git status and returns a compact
digest; callers never receive or log changed path names.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from holo_index.freshness_receipt import read_git_head_sha


REPOSITORY_DIRTY_CODE = "HOLOINDEX_REPOSITORY_DIRTY"
REPOSITORY_STATE_UNAVAILABLE_CODE = "HOLOINDEX_REPOSITORY_STATE_UNAVAILABLE"
SEALED_TARGET_REPO_ROOT_ENV = "REDDOG_SEALED_RUNTIME_TARGET_REPO_ROOT"
SEALED_RUNTIME_REQUIRED_ENV = "REDDOG_SEALED_RUNTIME_REQUIRED"


@dataclass(frozen=True)
class RepositoryState:
    """Bounded repository state suitable for freshness decisions."""

    head_sha: str
    clean: bool
    state_digest: str
    error: str = ""

    @property
    def proven_clean(self) -> bool:
        return self.clean is True and not self.error and self.head_sha != "unknown"


def _digest(head_sha: str, status: str) -> str:
    payload = (head_sha + chr(10) + status).encode("utf-8", errors="replace")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def repository_root_digest(repo_root: Path | str) -> str:
    """Return a public path identity without exposing the repository path."""

    root = os.path.normcase(str(Path(repo_root).resolve(strict=False)))
    return "sha256:" + hashlib.sha256(root.encode("utf-8")).hexdigest()


def runtime_repository_root(
    default_root: Path | str,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolve the authorized checkout while code executes from a sealed copy."""

    environment = os.environ if environ is None else environ
    fallback = Path(default_root).resolve(strict=False)
    if not sealed_runtime_required(environment):
        return fallback
    raw = str(environment.get(SEALED_TARGET_REPO_ROOT_ENV, "")).strip()
    candidate = Path(raw)
    if not raw or not candidate.is_absolute():
        raise RuntimeError("HOLOINDEX_SEALED_TARGET_REPO_ROOT_INVALID")
    resolved = candidate.resolve(strict=False)
    if not resolved.is_dir() or not (resolved / ".git").exists():
        raise RuntimeError("HOLOINDEX_SEALED_TARGET_REPO_ROOT_INVALID")
    return resolved


def sealed_runtime_required(
    environ: Mapping[str, str] | None = None,
) -> bool:
    environment = os.environ if environ is None else environ
    return str(environment.get(SEALED_RUNTIME_REQUIRED_ENV, "")).strip() == "1"


def _unavailable_state(head_sha: str) -> RepositoryState:
    return RepositoryState(
        head_sha=head_sha,
        clean=False,
        state_digest=_digest(head_sha, "unavailable"),
        error=REPOSITORY_STATE_UNAVAILABLE_CODE,
    )


def read_repository_state(
    repo_root: Path | str,
    *,
    timeout_seconds: float = 5.0,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> RepositoryState:
    """Return exact-HEAD plus clean-worktree proof without shell execution."""

    root = Path(repo_root).resolve(strict=False)
    head_sha = read_git_head_sha(root)
    if head_sha == "unknown" or not (root / ".git").exists():
        return _unavailable_state(head_sha)
    argv: Sequence[str] = (
        "git",
        "-C",
        str(root),
        "status",
        "--porcelain=v1",
        "--untracked-files=normal",
    )
    try:
        completed = runner(
            list(argv),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(0.1, min(float(timeout_seconds), 15.0)),
            check=False,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return _unavailable_state(head_sha)
    if completed.returncode != 0:
        return _unavailable_state(head_sha)
    status = str(completed.stdout or "")
    clean = not status.strip()
    return RepositoryState(
        head_sha=head_sha,
        clean=clean,
        state_digest=_digest(head_sha, status),
        error="" if clean else REPOSITORY_DIRTY_CODE,
    )


__all__ = [
    "REPOSITORY_DIRTY_CODE",
    "REPOSITORY_STATE_UNAVAILABLE_CODE",
    "RepositoryState",
    "read_repository_state",
    "repository_root_digest",
    "runtime_repository_root",
    "sealed_runtime_required",
]
