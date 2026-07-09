"""WRE worktree current-directory guard.

This guard is for commands that mutate files or git state after an isolated
worktree has been created. It deliberately does not authorize the work. It only
answers whether the operation cwd is inside the isolated worktree and outside
the shared repository checkout.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Optional

WRE_CWD_GUARD_PASS = "WRE_CWD_GUARD_PASS"
FAIL_REPO_ROOT_NOT_ABSOLUTE = "FAIL_REPO_ROOT_NOT_ABSOLUTE"
FAIL_WORKTREE_NOT_ABSOLUTE = "FAIL_WORKTREE_NOT_ABSOLUTE"
FAIL_WORKTREE_DEVICE_PREFIX = "FAIL_WORKTREE_DEVICE_PREFIX"
FAIL_WORKTREE_INSIDE_REPO_ROOT = "FAIL_WORKTREE_INSIDE_REPO_ROOT"
FAIL_WORKTREE_EQUALS_FILESYSTEM_ROOT = "FAIL_WORKTREE_EQUALS_FILESYSTEM_ROOT"
FAIL_OPERATION_CWD_NOT_ABSOLUTE = "FAIL_OPERATION_CWD_NOT_ABSOLUTE"
FAIL_OPERATION_CWD_DEVICE_PREFIX = "FAIL_OPERATION_CWD_DEVICE_PREFIX"
FAIL_OPERATION_CWD_OUTSIDE_WORKTREE = "FAIL_OPERATION_CWD_OUTSIDE_WORKTREE"
FAIL_OPERATION_CWD_INSIDE_REPO_ROOT = "FAIL_OPERATION_CWD_INSIDE_REPO_ROOT"

_DEVICE_PREFIXES = ("\\\\?\\", "\\\\.\\", "//?/", "//./")


@dataclass(frozen=True)
class WreCwdGuardResult:
    ok: bool
    code: str
    reason: str
    repo_root: str
    worktree_path: str
    operation_cwd: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _as_path(value: Path | str) -> Path:
    return value if isinstance(value, Path) else Path(str(value))


def _has_device_prefix(path: Path) -> bool:
    raw = str(path)
    resolved = str(path.resolve())
    return any(raw.startswith(prefix) or resolved.startswith(prefix) for prefix in _DEVICE_PREFIXES)


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _result(
    *,
    ok: bool,
    code: str,
    reason: str,
    repo_root: Path,
    worktree_path: Path,
    operation_cwd: Path,
) -> WreCwdGuardResult:
    return WreCwdGuardResult(
        ok=ok,
        code=code,
        reason=reason,
        repo_root=str(repo_root),
        worktree_path=str(worktree_path),
        operation_cwd=str(operation_cwd),
    )


def validate_wre_worker_operation_cwd(
    *,
    repo_root: Path | str,
    worktree_path: Path | str,
    operation_cwd: Optional[Path | str] = None,
) -> WreCwdGuardResult:
    """Fail closed unless a mutating worker operation runs inside the worktree.

    `repo_root` is the shared checkout. `worktree_path` is the isolated checkout.
    `operation_cwd` defaults to `worktree_path`, which is the expected cwd for
    git add/commit/test/edit commands inside a worker lane.
    """

    repo = _as_path(repo_root)
    worktree = _as_path(worktree_path)
    cwd = _as_path(operation_cwd) if operation_cwd is not None else worktree

    if not repo.is_absolute():
        return _result(
            ok=False,
            code=FAIL_REPO_ROOT_NOT_ABSOLUTE,
            reason="repo_root must be absolute",
            repo_root=repo,
            worktree_path=worktree,
            operation_cwd=cwd,
        )
    if not worktree.is_absolute():
        return _result(
            ok=False,
            code=FAIL_WORKTREE_NOT_ABSOLUTE,
            reason="worktree_path must be absolute",
            repo_root=repo,
            worktree_path=worktree,
            operation_cwd=cwd,
        )
    if _has_device_prefix(worktree):
        return _result(
            ok=False,
            code=FAIL_WORKTREE_DEVICE_PREFIX,
            reason="worktree_path must not use a device or extended-length prefix",
            repo_root=repo,
            worktree_path=worktree,
            operation_cwd=cwd,
        )
    if not cwd.is_absolute():
        return _result(
            ok=False,
            code=FAIL_OPERATION_CWD_NOT_ABSOLUTE,
            reason="operation_cwd must be absolute",
            repo_root=repo,
            worktree_path=worktree,
            operation_cwd=cwd,
        )
    if _has_device_prefix(cwd):
        return _result(
            ok=False,
            code=FAIL_OPERATION_CWD_DEVICE_PREFIX,
            reason="operation_cwd must not use a device or extended-length prefix",
            repo_root=repo,
            worktree_path=worktree,
            operation_cwd=cwd,
        )

    repo_r = repo.resolve()
    worktree_r = worktree.resolve()
    cwd_r = cwd.resolve()

    if worktree_r == Path(worktree_r.anchor):
        return _result(
            ok=False,
            code=FAIL_WORKTREE_EQUALS_FILESYSTEM_ROOT,
            reason="worktree_path must not be a filesystem root",
            repo_root=repo_r,
            worktree_path=worktree_r,
            operation_cwd=cwd_r,
        )
    if _is_inside(worktree_r, repo_r) or _is_inside(repo_r, worktree_r):
        return _result(
            ok=False,
            code=FAIL_WORKTREE_INSIDE_REPO_ROOT,
            reason="worktree_path must be outside the shared repo root",
            repo_root=repo_r,
            worktree_path=worktree_r,
            operation_cwd=cwd_r,
        )
    if _is_inside(cwd_r, repo_r):
        return _result(
            ok=False,
            code=FAIL_OPERATION_CWD_INSIDE_REPO_ROOT,
            reason="operation_cwd must not be inside the shared repo root",
            repo_root=repo_r,
            worktree_path=worktree_r,
            operation_cwd=cwd_r,
        )
    if not _is_inside(cwd_r, worktree_r):
        return _result(
            ok=False,
            code=FAIL_OPERATION_CWD_OUTSIDE_WORKTREE,
            reason="operation_cwd must be inside the isolated worktree",
            repo_root=repo_r,
            worktree_path=worktree_r,
            operation_cwd=cwd_r,
        )

    return _result(
        ok=True,
        code=WRE_CWD_GUARD_PASS,
        reason="operation_cwd is isolated inside worktree",
        repo_root=repo_r,
        worktree_path=worktree_r,
        operation_cwd=cwd_r,
    )


__all__ = [
    "FAIL_OPERATION_CWD_DEVICE_PREFIX",
    "FAIL_OPERATION_CWD_INSIDE_REPO_ROOT",
    "FAIL_OPERATION_CWD_NOT_ABSOLUTE",
    "FAIL_OPERATION_CWD_OUTSIDE_WORKTREE",
    "FAIL_REPO_ROOT_NOT_ABSOLUTE",
    "FAIL_WORKTREE_DEVICE_PREFIX",
    "FAIL_WORKTREE_EQUALS_FILESYSTEM_ROOT",
    "FAIL_WORKTREE_INSIDE_REPO_ROOT",
    "FAIL_WORKTREE_NOT_ABSOLUTE",
    "WRE_CWD_GUARD_PASS",
    "WreCwdGuardResult",
    "validate_wre_worker_operation_cwd",
]
