"""Test-only worktree runner for progressive resident-chain coverage."""

from __future__ import annotations

from pathlib import Path


class FakeProfileWorktreeRunner:
    """Record bounded worktree and draft-PR effects without touching Git."""

    instances: list["FakeProfileWorktreeRunner"] = []

    def __init__(self, *, repo_root: Path, timeout_s: int) -> None:
        self.repo_root = Path(repo_root)
        self.timeout_s = timeout_s
        self.calls: list[tuple[str, str, str | None, str | None]] = []
        self.__class__.instances.append(self)

    def create_worktree(self, *, worktree_path: Path, branch_name: str, base_ref: str):
        self.calls.append(("create_worktree", str(worktree_path), branch_name, base_ref))
        Path(worktree_path).mkdir(parents=True, exist_ok=True)
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}

    def cleanup_worktree(self, *, worktree_path: Path):
        self.calls.append(("cleanup_worktree", str(worktree_path), None, None))
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}

    def push_branch(self, *, worktree_path: Path, branch_name: str):
        self.calls.append(("push_branch", str(worktree_path), branch_name, None))
        return {"ok": True, "branch_name": branch_name}

    def create_draft_pr(self, *, branch_name: str, base_branch: str, title: str, body: str):
        self.calls.append(("create_draft_pr", branch_name, base_branch, title))
        _ = body
        return "https://github.com/FOUNDUPS/Foundups-Agent/pull/4242"
