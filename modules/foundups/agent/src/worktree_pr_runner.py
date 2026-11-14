#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Worktree / draft-PR runner -- the APPROVED side-effect helper for the live scaffold
writer (FOUNDUP_SCAFFOLD_WRITER_LIVE_PHASE1).

This is the ONLY module in the FoundUp live-write path permitted to call git/gh via
subprocess. It performs NO authorization -- the orchestration
(foundup_scaffold_writer_live.run_foundup_scaffold_writer_live) gates EVERYTHING
(preauth packet, sovereign token, valve, paths, digests) BEFORE any method here is
called, and injects this runner explicitly. Tests inject a FakeRunner instead, so no
real git/gh executes in CI.

Hard constraints:
    - argv lists only (never shell=True); no secrets are ever passed as arguments.
    - Draft PR ONLY: `gh pr create --draft`. NEVER `gh pr ready` / `gh pr merge`.
    - Worktrees are created at a caller-supplied ISOLATED path (validated outside the
      main repo by the orchestration before this runner is called).

The WorktreeRunner protocol below documents the interface the orchestration expects.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, Protocol, runtime_checkable

from modules.communication.moltbot_bridge.src.reddog_wre_cwd_guard import (
    validate_wre_worker_operation_cwd,
)


@runtime_checkable
class WorktreeRunner(Protocol):
    """Side-effect interface the live writer delegates to (duck-typed)."""

    def create_worktree(self, *, worktree_path: Path, branch_name: str, base_branch: str) -> Dict[str, Any]: ...
    def commit_all(self, *, worktree_path: Path, add_paths, message: str) -> Dict[str, Any]: ...
    def push_branch(self, *, worktree_path: Path, branch_name: str) -> Dict[str, Any]: ...
    def create_draft_pr(self, *, branch_name: str, base_branch: str, title: str, body: str) -> str: ...
    def cleanup_worktree(self, *, worktree_path: Path) -> Dict[str, Any]: ...


class RealWorktreeRunner:
    """Executes real git worktree + draft-PR operations. Production only.

    Constructed with the main repo root. Every method uses argv lists (no shell) and
    a timeout. This runner must ONLY be reached after full authorization -- it does no
    checking itself.
    """

    def __init__(self, repo_root: Path, *, timeout_s: int = 120) -> None:
        self.repo_root = Path(repo_root)
        self.timeout_s = timeout_s

    def _guard_worktree_cwd(self, worktree_path: Path) -> Dict[str, Any] | None:
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

    def _run(self, argv, cwd=None) -> Dict[str, Any]:
        proc = subprocess.run(  # noqa: S603 -- argv list, no shell, approved helper
            argv, cwd=str(cwd or self.repo_root),
            capture_output=True, text=True, timeout=self.timeout_s,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }

    def create_worktree(self, *, worktree_path: Path, branch_name: str, base_branch: str) -> Dict[str, Any]:
        # Refuse a relative path even if the orchestration is bypassed: a relative path
        # would be resolved against this runner's cwd (repo_root), risking an in-repo worktree.
        if not Path(worktree_path).is_absolute():
            return {"ok": False, "returncode": -1, "stdout": "", "stderr": "worktree_path must be absolute"}
        guard = self._guard_worktree_cwd(Path(worktree_path))
        if guard is not None:
            return guard
        return self._run(
            ["git", "worktree", "add", "-b", branch_name, str(worktree_path), base_branch],
        )

    def commit_all(self, *, worktree_path: Path, add_paths, message: str) -> Dict[str, Any]:
        guard = self._guard_worktree_cwd(Path(worktree_path))
        if guard is not None:
            return guard
        # Stage ONLY the explicit module path(s) -- never `git add -A` -- so nothing
        # outside the scaffolded module can be committed even if the worktree is dirty.
        add = self._run(
            ["git", "add", "--"] + [str(p) for p in add_paths],
            cwd=worktree_path,
        )
        if not add["ok"]:
            return add
        return self._run(["git", "commit", "-m", message], cwd=worktree_path)

    def push_branch(self, *, worktree_path: Path, branch_name: str) -> Dict[str, Any]:
        guard = self._guard_worktree_cwd(Path(worktree_path))
        if guard is not None:
            return guard
        return self._run(
            ["git", "push", "-u", "origin", branch_name],
            cwd=worktree_path,
        )

    def create_draft_pr(self, *, branch_name: str, base_branch: str, title: str, body: str) -> str:
        # DRAFT only. This runner never marks ready and never merges.
        res = self._run([
            "gh", "pr", "create", "--draft",
            "--base", base_branch, "--head", branch_name,
            "--title", title, "--body", body,
        ])
        if not res["ok"]:
            raise RuntimeError("gh pr create --draft failed")
        return res["stdout"]

    def cleanup_worktree(self, *, worktree_path: Path) -> Dict[str, Any]:
        guard = self._guard_worktree_cwd(Path(worktree_path))
        if guard is not None:
            return guard
        return self._run(["git", "worktree", "remove", str(worktree_path), "--force"])
