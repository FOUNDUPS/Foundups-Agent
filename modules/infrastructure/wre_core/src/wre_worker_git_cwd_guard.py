"""Worker git cwd guard for isolated WRE lanes.

This module prevents a recurring operational failure mode: a worker believes it
is operating in an isolated worktree, but a mutating git command is run from the
shared main checkout. The guard is pure evaluation. It does not execute git,
create worktrees, inspect repository state, or mutate files.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence


WRE_WORKER_GIT_CWD_GUARD_PASS = "WRE_WORKER_GIT_CWD_GUARD_PASS"
WRE_WORKER_GIT_CWD_GUARD_NOT_GIT = "WRE_WORKER_GIT_CWD_GUARD_NOT_GIT"
WRE_WORKER_GIT_CWD_GUARD_READONLY = "WRE_WORKER_GIT_CWD_GUARD_READONLY"

FAIL_ARGV_EMPTY = "FAIL_ARGV_EMPTY"
FAIL_OPERATION_CWD_NOT_ABSOLUTE = "FAIL_OPERATION_CWD_NOT_ABSOLUTE"
FAIL_OPERATION_CWD_DEVICE_PREFIX = "FAIL_OPERATION_CWD_DEVICE_PREFIX"
FAIL_REPO_ROOT_NOT_ABSOLUTE = "FAIL_REPO_ROOT_NOT_ABSOLUTE"
FAIL_WORKTREE_NOT_ABSOLUTE = "FAIL_WORKTREE_NOT_ABSOLUTE"
FAIL_WORKTREE_DEVICE_PREFIX = "FAIL_WORKTREE_DEVICE_PREFIX"
FAIL_WORKTREE_INSIDE_REPO_ROOT = "FAIL_WORKTREE_INSIDE_REPO_ROOT"
FAIL_WORKTREE_EQUALS_FILESYSTEM_ROOT = "FAIL_WORKTREE_EQUALS_FILESYSTEM_ROOT"
FAIL_OPERATION_CWD_INSIDE_REPO_ROOT = "FAIL_OPERATION_CWD_INSIDE_REPO_ROOT"
FAIL_OPERATION_CWD_OUTSIDE_WORKTREE = "FAIL_OPERATION_CWD_OUTSIDE_WORKTREE"
FAIL_CLAIMED_WORKTREE_MISSING = "FAIL_CLAIMED_WORKTREE_MISSING"
FAIL_GIT_C_OPTION_FOR_MUTATION = "FAIL_GIT_C_OPTION_FOR_MUTATION"
FAIL_GIT_WORK_TREE_OPTION_FOR_MUTATION = "FAIL_GIT_WORK_TREE_OPTION_FOR_MUTATION"


_DEVICE_PREFIXES = ("\\\\?\\", "\\\\.\\", "//?/", "//./")
_READONLY_SUBCOMMANDS = {
    "blame",
    "cat-file",
    "describe",
    "diff",
    "for-each-ref",
    "grep",
    "log",
    "ls-files",
    "merge-base",
    "rev-list",
    "rev-parse",
    "shortlog",
    "show",
    "status",
}
_READONLY_WORKTREE_SUBCOMMANDS = {"list"}
_CWD_OPTIONS = {"-C"}
_WORK_TREE_OPTIONS = {"--git-dir", "--work-tree", "--namespace"}


@dataclass(frozen=True)
class WorkerGitCwdGuardResult:
    """Pure decision result for a proposed worker git command."""

    ok: bool
    code: str
    reason: str
    command_kind: str
    git_subcommand: Optional[str]
    repo_root: str
    operation_cwd: str
    claimed_worktree_path: Optional[str]
    no_git_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _as_path(value: Path | str) -> Path:
    return value if isinstance(value, Path) else Path(str(value))


def _has_device_prefix(path: Path) -> bool:
    raw = str(path)
    try:
        resolved = str(path.resolve())
    except OSError:
        resolved = raw
    return any(raw.startswith(prefix) or resolved.startswith(prefix) for prefix in _DEVICE_PREFIXES)


def _safe_resolve(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = _safe_resolve(child)
    parent_r = _safe_resolve(parent)
    return child_r == parent_r or parent_r in child_r.parents


def _result(
    *,
    ok: bool,
    code: str,
    reason: str,
    command_kind: str,
    git_subcommand: Optional[str],
    repo_root: Path,
    operation_cwd: Path,
    claimed_worktree_path: Optional[Path],
) -> WorkerGitCwdGuardResult:
    return WorkerGitCwdGuardResult(
        ok=ok,
        code=code,
        reason=reason,
        command_kind=command_kind,
        git_subcommand=git_subcommand,
        repo_root=str(repo_root),
        operation_cwd=str(operation_cwd),
        claimed_worktree_path=str(claimed_worktree_path) if claimed_worktree_path is not None else None,
    )


def _looks_like_git(executable: str) -> bool:
    name = executable.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return name in {"git", "git.exe"}


def _git_subcommand(argv: Sequence[str]) -> Optional[str]:
    idx = 1
    while idx < len(argv):
        token = str(argv[idx])
        if token == "-C":
            idx += 2
            continue
        if token.startswith("-c"):
            idx += 1
            continue
        if token.startswith("--"):
            idx += 1
            if token in _WORK_TREE_OPTIONS and idx < len(argv):
                idx += 1
            continue
        return token.lower()
    return None


def _has_mutation_cwd_bypass_option(argv: Sequence[str]) -> Optional[str]:
    for token in (str(item) for item in argv[1:]):
        if token in _CWD_OPTIONS:
            return FAIL_GIT_C_OPTION_FOR_MUTATION
        if token in _WORK_TREE_OPTIONS or token.startswith("--git-dir=") or token.startswith("--work-tree="):
            return FAIL_GIT_WORK_TREE_OPTION_FOR_MUTATION
    return None


def _is_readonly_git(argv: Sequence[str], subcommand: Optional[str]) -> bool:
    if subcommand is None:
        return False
    if subcommand in _READONLY_SUBCOMMANDS:
        return True
    if subcommand == "worktree":
        return len(argv) >= 3 and str(argv[2]).lower() in _READONLY_WORKTREE_SUBCOMMANDS
    return False


def validate_worker_git_operation_cwd(
    *,
    repo_root: Path | str,
    operation_cwd: Path | str,
    argv: Sequence[str],
    claimed_worktree_path: Optional[Path | str] = None,
) -> WorkerGitCwdGuardResult:
    """Validate a worker git command before it can run.

    Read-only git inspection commands are allowed from any absolute cwd.
    Mutating or unknown git commands require a claimed isolated worktree, and
    the operation cwd must be inside that worktree and outside the shared repo.
    """

    repo = _as_path(repo_root)
    cwd = _as_path(operation_cwd)
    worktree = _as_path(claimed_worktree_path) if claimed_worktree_path is not None else None

    if not argv:
        return _result(
            ok=False,
            code=FAIL_ARGV_EMPTY,
            reason="argv must contain an executable",
            command_kind="unknown",
            git_subcommand=None,
            repo_root=repo,
            operation_cwd=cwd,
            claimed_worktree_path=worktree,
        )

    if not repo.is_absolute():
        return _result(
            ok=False,
            code=FAIL_REPO_ROOT_NOT_ABSOLUTE,
            reason="repo_root must be absolute",
            command_kind="unknown",
            git_subcommand=None,
            repo_root=repo,
            operation_cwd=cwd,
            claimed_worktree_path=worktree,
        )
    if not cwd.is_absolute():
        return _result(
            ok=False,
            code=FAIL_OPERATION_CWD_NOT_ABSOLUTE,
            reason="operation_cwd must be absolute",
            command_kind="unknown",
            git_subcommand=None,
            repo_root=repo,
            operation_cwd=cwd,
            claimed_worktree_path=worktree,
        )
    if _has_device_prefix(cwd):
        return _result(
            ok=False,
            code=FAIL_OPERATION_CWD_DEVICE_PREFIX,
            reason="operation_cwd must not use a device or extended-length prefix",
            command_kind="unknown",
            git_subcommand=None,
            repo_root=repo,
            operation_cwd=cwd,
            claimed_worktree_path=worktree,
        )

    if not _looks_like_git(str(argv[0])):
        return _result(
            ok=True,
            code=WRE_WORKER_GIT_CWD_GUARD_NOT_GIT,
            reason="command is not a git command",
            command_kind="not_git",
            git_subcommand=None,
            repo_root=_safe_resolve(repo),
            operation_cwd=_safe_resolve(cwd),
            claimed_worktree_path=_safe_resolve(worktree) if worktree is not None else None,
        )

    subcommand = _git_subcommand(argv)
    if _is_readonly_git(argv, subcommand):
        return _result(
            ok=True,
            code=WRE_WORKER_GIT_CWD_GUARD_READONLY,
            reason="read-only git command",
            command_kind="git_readonly",
            git_subcommand=subcommand,
            repo_root=_safe_resolve(repo),
            operation_cwd=_safe_resolve(cwd),
            claimed_worktree_path=_safe_resolve(worktree) if worktree is not None else None,
        )

    bypass_reason = _has_mutation_cwd_bypass_option(argv)
    if bypass_reason is not None:
        return _result(
            ok=False,
            code=bypass_reason,
            reason="mutating git command must not override cwd with git options",
            command_kind="git_mutation",
            git_subcommand=subcommand,
            repo_root=_safe_resolve(repo),
            operation_cwd=_safe_resolve(cwd),
            claimed_worktree_path=_safe_resolve(worktree) if worktree is not None else None,
        )
    if worktree is None:
        return _result(
            ok=False,
            code=FAIL_CLAIMED_WORKTREE_MISSING,
            reason="mutating git command requires a claimed isolated worktree",
            command_kind="git_mutation",
            git_subcommand=subcommand,
            repo_root=_safe_resolve(repo),
            operation_cwd=_safe_resolve(cwd),
            claimed_worktree_path=None,
        )
    if not worktree.is_absolute():
        return _result(
            ok=False,
            code=FAIL_WORKTREE_NOT_ABSOLUTE,
            reason="claimed_worktree_path must be absolute",
            command_kind="git_mutation",
            git_subcommand=subcommand,
            repo_root=repo,
            operation_cwd=cwd,
            claimed_worktree_path=worktree,
        )
    if _has_device_prefix(worktree):
        return _result(
            ok=False,
            code=FAIL_WORKTREE_DEVICE_PREFIX,
            reason="claimed_worktree_path must not use a device or extended-length prefix",
            command_kind="git_mutation",
            git_subcommand=subcommand,
            repo_root=repo,
            operation_cwd=cwd,
            claimed_worktree_path=worktree,
        )

    repo_r = _safe_resolve(repo)
    worktree_r = _safe_resolve(worktree)
    cwd_r = _safe_resolve(cwd)
    if worktree_r == Path(worktree_r.anchor):
        return _result(
            ok=False,
            code=FAIL_WORKTREE_EQUALS_FILESYSTEM_ROOT,
            reason="claimed_worktree_path must not be a filesystem root",
            command_kind="git_mutation",
            git_subcommand=subcommand,
            repo_root=repo_r,
            operation_cwd=cwd_r,
            claimed_worktree_path=worktree_r,
        )
    if _is_inside(worktree_r, repo_r) or _is_inside(repo_r, worktree_r):
        return _result(
            ok=False,
            code=FAIL_WORKTREE_INSIDE_REPO_ROOT,
            reason="claimed_worktree_path must be outside the shared repo root",
            command_kind="git_mutation",
            git_subcommand=subcommand,
            repo_root=repo_r,
            operation_cwd=cwd_r,
            claimed_worktree_path=worktree_r,
        )
    if _is_inside(cwd_r, repo_r):
        return _result(
            ok=False,
            code=FAIL_OPERATION_CWD_INSIDE_REPO_ROOT,
            reason="operation_cwd must not be inside the shared repo root for mutating git",
            command_kind="git_mutation",
            git_subcommand=subcommand,
            repo_root=repo_r,
            operation_cwd=cwd_r,
            claimed_worktree_path=worktree_r,
        )
    if not _is_inside(cwd_r, worktree_r):
        return _result(
            ok=False,
            code=FAIL_OPERATION_CWD_OUTSIDE_WORKTREE,
            reason="operation_cwd must be inside the claimed isolated worktree",
            command_kind="git_mutation",
            git_subcommand=subcommand,
            repo_root=repo_r,
            operation_cwd=cwd_r,
            claimed_worktree_path=worktree_r,
        )

    return _result(
        ok=True,
        code=WRE_WORKER_GIT_CWD_GUARD_PASS,
        reason="mutating git command is scoped to the isolated worktree cwd",
        command_kind="git_mutation",
        git_subcommand=subcommand,
        repo_root=repo_r,
        operation_cwd=cwd_r,
        claimed_worktree_path=worktree_r,
    )


__all__ = [
    "FAIL_ARGV_EMPTY",
    "FAIL_CLAIMED_WORKTREE_MISSING",
    "FAIL_GIT_C_OPTION_FOR_MUTATION",
    "FAIL_GIT_WORK_TREE_OPTION_FOR_MUTATION",
    "FAIL_OPERATION_CWD_DEVICE_PREFIX",
    "FAIL_OPERATION_CWD_INSIDE_REPO_ROOT",
    "FAIL_OPERATION_CWD_NOT_ABSOLUTE",
    "FAIL_OPERATION_CWD_OUTSIDE_WORKTREE",
    "FAIL_REPO_ROOT_NOT_ABSOLUTE",
    "FAIL_WORKTREE_DEVICE_PREFIX",
    "FAIL_WORKTREE_EQUALS_FILESYSTEM_ROOT",
    "FAIL_WORKTREE_INSIDE_REPO_ROOT",
    "FAIL_WORKTREE_NOT_ABSOLUTE",
    "WRE_WORKER_GIT_CWD_GUARD_NOT_GIT",
    "WRE_WORKER_GIT_CWD_GUARD_PASS",
    "WRE_WORKER_GIT_CWD_GUARD_READONLY",
    "WorkerGitCwdGuardResult",
    "validate_worker_git_operation_cwd",
]
