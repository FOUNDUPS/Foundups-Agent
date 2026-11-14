#!/usr/bin/env python3
"""Pre-commit guard against worker CWD pollution of the shared main checkout.

This hook is intentionally narrow. It does not authorize work; it only blocks
accidental direct commits from the shared repo checkout and detached integration
worktrees unless an explicit override is present.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

PASS = "PASS"
FAIL_SHARED_MAIN_CHECKOUT = "FAIL_SHARED_MAIN_CHECKOUT"
FAIL_DETACHED_UNSAFE_CHECKOUT = "FAIL_DETACHED_UNSAFE_CHECKOUT"
FAIL_GIT_CONTEXT = "FAIL_GIT_CONTEXT"

ALLOW_ENV = "FOUNDUPS_ALLOW_SHARED_MAIN_COMMIT"
SHARED_ROOT_ENV = "FOUNDUPS_SHARED_REPO_ROOT"

WORKTREE_MARKERS = (
    "/.worktrees/",
    "/.claude/worktrees/",
    "/Foundups-Agent-worktrees/",
    "/tmp/",
)


@dataclass(frozen=True)
class WorktreeCwdGuardDecision:
    ok: bool
    code: str
    reason: str
    repo_root: str
    shared_repo_root: str
    branch: str


def _normalize(path: Path | str) -> str:
    return str(Path(path).resolve()).replace("\\", "/")


def _run_git(args: Iterable[str], cwd: Optional[Path] = None) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "git command failed").strip())
    return proc.stdout.strip()


def _is_marked_worker_tree(repo_root: str) -> bool:
    root = repo_root.replace("\\", "/")
    return any(marker in root for marker in WORKTREE_MARKERS)


def evaluate_pre_commit_cwd(
    *,
    repo_root: Path | str,
    shared_repo_root: Path | str,
    branch: str,
    allow_override: bool = False,
) -> WorktreeCwdGuardDecision:
    repo = _normalize(repo_root)
    shared = _normalize(shared_repo_root)
    current_branch = str(branch or "").strip()

    if allow_override:
        return WorktreeCwdGuardDecision(
            ok=True,
            code=PASS,
            reason="explicit shared-main override present",
            repo_root=repo,
            shared_repo_root=shared,
            branch=current_branch or "(detached)",
        )

    if repo == shared and current_branch == "main":
        return WorktreeCwdGuardDecision(
            ok=False,
            code=FAIL_SHARED_MAIN_CHECKOUT,
            reason=(
                "direct commit from the shared main checkout is blocked; use an "
                "isolated worktree or set FOUNDUPS_ALLOW_SHARED_MAIN_COMMIT=1"
            ),
            repo_root=repo,
            shared_repo_root=shared,
            branch=current_branch,
        )

    if not current_branch and not _is_marked_worker_tree(repo):
        return WorktreeCwdGuardDecision(
            ok=False,
            code=FAIL_DETACHED_UNSAFE_CHECKOUT,
            reason=(
                "detached checkout is not a marked worker/build worktree; use an "
                "isolated branch worktree or set FOUNDUPS_ALLOW_SHARED_MAIN_COMMIT=1"
            ),
            repo_root=repo,
            shared_repo_root=shared,
            branch="(detached)",
        )

    return WorktreeCwdGuardDecision(
        ok=True,
        code=PASS,
        reason="commit cwd is not the shared main checkout",
        repo_root=repo,
        shared_repo_root=shared,
        branch=current_branch or "(detached)",
    )


def current_git_decision(cwd: Optional[Path] = None) -> WorktreeCwdGuardDecision:
    try:
        repo_root = Path(_run_git(["rev-parse", "--show-toplevel"], cwd=cwd))
        branch = _run_git(["branch", "--show-current"], cwd=cwd)
    except Exception as exc:  # pragma: no cover - exercised through CLI behavior.
        return WorktreeCwdGuardDecision(
            ok=False,
            code=FAIL_GIT_CONTEXT,
            reason=f"could not resolve git context: {type(exc).__name__}",
            repo_root="",
            shared_repo_root="",
            branch="",
        )

    shared_root = Path(os.environ.get(SHARED_ROOT_ENV, "O:/Foundups-Agent"))
    return evaluate_pre_commit_cwd(
        repo_root=repo_root,
        shared_repo_root=shared_root,
        branch=branch,
        allow_override=os.environ.get(ALLOW_ENV) == "1",
    )


def main() -> int:
    decision = current_git_decision()
    if decision.ok:
        return 0
    sys.stderr.write(
        "\n".join(
            [
                f"[WRE-CWD-GUARD] {decision.code}: {decision.reason}",
                f"[WRE-CWD-GUARD] repo_root={decision.repo_root or 'unknown'}",
                f"[WRE-CWD-GUARD] shared_repo_root={decision.shared_repo_root or 'unknown'}",
                f"[WRE-CWD-GUARD] branch={decision.branch or 'unknown'}",
            ]
        )
        + "\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

