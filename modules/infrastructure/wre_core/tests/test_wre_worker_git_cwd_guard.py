"""Tests for WRE worker git cwd guard."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.infrastructure.wre_core.src.wre_worker_git_cwd_guard import (
    FAIL_CLAIMED_WORKTREE_MISSING,
    FAIL_GIT_C_OPTION_FOR_MUTATION,
    FAIL_OPERATION_CWD_INSIDE_REPO_ROOT,
    FAIL_OPERATION_CWD_NOT_ABSOLUTE,
    FAIL_OPERATION_CWD_OUTSIDE_WORKTREE,
    FAIL_WORKTREE_INSIDE_REPO_ROOT,
    WRE_WORKER_GIT_CWD_GUARD_NOT_GIT,
    WRE_WORKER_GIT_CWD_GUARD_PASS,
    WRE_WORKER_GIT_CWD_GUARD_READONLY,
    validate_worker_git_operation_cwd,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = REPO_ROOT / "modules" / "infrastructure" / "wre_core" / "src" / "wre_worker_git_cwd_guard.py"


def test_readonly_git_status_is_allowed_from_shared_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    result = validate_worker_git_operation_cwd(
        repo_root=repo,
        operation_cwd=repo,
        argv=["git", "status", "--short"],
    )

    assert result.ok is True
    assert result.code == WRE_WORKER_GIT_CWD_GUARD_READONLY
    assert result.command_kind == "git_readonly"
    assert result.no_git_executed is True


def test_non_git_command_is_not_guarded_by_git_cwd_guard(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    result = validate_worker_git_operation_cwd(
        repo_root=repo,
        operation_cwd=repo,
        argv=["python", "-m", "pytest"],
    )

    assert result.ok is True
    assert result.code == WRE_WORKER_GIT_CWD_GUARD_NOT_GIT
    assert result.command_kind == "not_git"


def test_mutating_git_requires_claimed_worktree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    result = validate_worker_git_operation_cwd(
        repo_root=repo,
        operation_cwd=repo,
        argv=["git", "add", "modules/example.py"],
    )

    assert result.ok is False
    assert result.code == FAIL_CLAIMED_WORKTREE_MISSING
    assert result.command_kind == "git_mutation"
    assert result.git_subcommand == "add"


def test_mutating_git_from_shared_root_is_rejected_even_with_claim(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    worktree = tmp_path / "worktree"
    repo.mkdir()
    worktree.mkdir()

    result = validate_worker_git_operation_cwd(
        repo_root=repo,
        operation_cwd=repo,
        claimed_worktree_path=worktree,
        argv=["git", "commit", "-m", "demo"],
    )

    assert result.ok is False
    assert result.code == FAIL_OPERATION_CWD_INSIDE_REPO_ROOT


def test_mutating_git_inside_external_worktree_is_allowed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    worktree = tmp_path / "worktree"
    cwd = worktree / "modules" / "foundups" / "demo"
    repo.mkdir()
    cwd.mkdir(parents=True)

    result = validate_worker_git_operation_cwd(
        repo_root=repo,
        operation_cwd=cwd,
        claimed_worktree_path=worktree,
        argv=["git", "add", "--", "modules/foundups/demo/README.md"],
    )

    assert result.ok is True
    assert result.code == WRE_WORKER_GIT_CWD_GUARD_PASS
    assert result.command_kind == "git_mutation"
    assert result.git_subcommand == "add"


def test_mutating_git_outside_claimed_worktree_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    worktree = tmp_path / "worktree"
    other = tmp_path / "other"
    repo.mkdir()
    worktree.mkdir()
    other.mkdir()

    result = validate_worker_git_operation_cwd(
        repo_root=repo,
        operation_cwd=other,
        claimed_worktree_path=worktree,
        argv=["git", "push", "-u", "origin", "branch"],
    )

    assert result.ok is False
    assert result.code == FAIL_OPERATION_CWD_OUTSIDE_WORKTREE


def test_mutating_git_rejects_c_option_bypass(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    worktree = tmp_path / "worktree"
    cwd = worktree / "src"
    repo.mkdir()
    cwd.mkdir(parents=True)

    result = validate_worker_git_operation_cwd(
        repo_root=repo,
        operation_cwd=cwd,
        claimed_worktree_path=worktree,
        argv=["git", "-C", str(repo), "add", "README.md"],
    )

    assert result.ok is False
    assert result.code == FAIL_GIT_C_OPTION_FOR_MUTATION


def test_rejects_in_repo_worktree_and_relative_cwd(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    in_repo_worktree = repo / ".worktrees" / "bad"
    in_repo_worktree.mkdir(parents=True)

    in_repo = validate_worker_git_operation_cwd(
        repo_root=repo,
        operation_cwd=in_repo_worktree,
        claimed_worktree_path=in_repo_worktree,
        argv=["git", "add", "README.md"],
    )
    assert in_repo.ok is False
    assert in_repo.code == FAIL_WORKTREE_INSIDE_REPO_ROOT

    relative_cwd = validate_worker_git_operation_cwd(
        repo_root=repo,
        operation_cwd=Path("relative"),
        claimed_worktree_path=tmp_path / "worktree",
        argv=["git", "add", "README.md"],
    )
    assert relative_cwd.ok is False
    assert relative_cwd.code == FAIL_OPERATION_CWD_NOT_ABSOLUTE


def test_unknown_git_subcommand_fails_closed_unless_inside_claimed_worktree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    worktree = tmp_path / "worktree"
    repo.mkdir()
    worktree.mkdir()

    missing_claim = validate_worker_git_operation_cwd(
        repo_root=repo,
        operation_cwd=repo,
        argv=["git", "future-mutating-command"],
    )
    assert missing_claim.ok is False
    assert missing_claim.code == FAIL_CLAIMED_WORKTREE_MISSING

    accepted = validate_worker_git_operation_cwd(
        repo_root=repo,
        operation_cwd=worktree,
        claimed_worktree_path=worktree,
        argv=["git", "future-mutating-command"],
    )
    assert accepted.ok is True
    assert accepted.code == WRE_WORKER_GIT_CWD_GUARD_PASS


def test_module_has_no_shell_git_execution_or_filesystem_mutation_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {"subprocess", "os", "shutil", "socket", "requests", "urllib", "holo_index"}
    banned_calls = {"eval", "exec", "compile", "__import__", "open"}
    banned_module_attrs = {"run", "Popen", "system", "popen", "remove", "unlink", "rmdir", "replace", "rename"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                if node.func.value.id in {"subprocess", "os", "shutil", "Path"}:
                    assert node.func.attr not in banned_module_attrs
