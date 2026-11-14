"""RedDog WRE worktree side-effect runner.

Approved helper for REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_WORKTREE_CREATE_PHASE1.
It performs only argv-list git worktree create/remove operations. Authorization
and policy checks live in reddog_wre_worktree_create.py before this runner is
constructed or called.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, Protocol, runtime_checkable

from modules.communication.moltbot_bridge.src.reddog_wre_cwd_guard import (
    validate_wre_worker_operation_cwd,
)


@runtime_checkable
class RedDogWorktreeRunner(Protocol):
    """Side-effect interface used by the worktree-create orchestration."""

    def create_worktree(
        self,
        *,
        worktree_path: Path,
        branch_name: str,
        base_ref: str,
    ) -> Dict[str, Any]: ...

    def cleanup_worktree(self, *, worktree_path: Path) -> Dict[str, Any]: ...


class RealRedDogWorktreeRunner:
    """Runs real git worktree commands after upstream authorization.

    This class deliberately does no policy work. Callers must validate RedDog
    work-order receipts, the OpenClaw policy gate, the execution valve, path
    confinement, and branch safety before invoking it.
    """

    def __init__(self, repo_root: Path, *, timeout_s: int = 120) -> None:
        self.repo_root = Path(repo_root)
        self.timeout_s = int(timeout_s)

    def _guard_worktree(self, worktree_path: Path) -> Dict[str, Any] | None:
        guard = validate_wre_worker_operation_cwd(
            repo_root=self.repo_root,
            worktree_path=worktree_path,
            operation_cwd=worktree_path,
        )
        if guard.ok:
            return None
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"{guard.code}: {guard.reason}",
        }

    def _run(self, argv: list[str]) -> Dict[str, Any]:
        proc = subprocess.run(
            argv,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            timeout=self.timeout_s,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }

    def create_worktree(
        self,
        *,
        worktree_path: Path,
        branch_name: str,
        base_ref: str,
    ) -> Dict[str, Any]:
        if not Path(worktree_path).is_absolute():
            return {
                "ok": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "worktree_path must be absolute",
            }
        guard = self._guard_worktree(Path(worktree_path))
        if guard is not None:
            return guard
        return self._run(
            [
                "git",
                "worktree",
                "add",
                "-b",
                branch_name,
                str(worktree_path),
                base_ref,
            ]
        )

    def cleanup_worktree(self, *, worktree_path: Path) -> Dict[str, Any]:
        guard = self._guard_worktree(Path(worktree_path))
        if guard is not None:
            return guard
        return self._run(["git", "worktree", "remove", str(worktree_path), "--force"])


__all__ = ["RealRedDogWorktreeRunner", "RedDogWorktreeRunner"]
