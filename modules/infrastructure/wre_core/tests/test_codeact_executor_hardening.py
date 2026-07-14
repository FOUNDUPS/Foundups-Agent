#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hardening tests for CodeAct executor safety policy."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from modules.infrastructure.wre_core.src.codeact_executor import (
    CodeActExecutor,
    SafetyGates,
)


def test_require_allowlist_blocks_when_empty():
    gates = SafetyGates(
        allowed_commands=[],
        blocked_patterns=[],
        require_allowlist=True,
    )
    assert gates.is_command_allowed("git status") is False


def test_shell_execution_uses_shell_false():
    executor = CodeActExecutor(repo_root=Path("."))
    skill = {
        "format": "codeact",
        "code_section": {
            "main_action": {"type": "shell", "command": "python --version", "capture": "out"}
        },
        "safety_gates": {
            "allowed_commands": ["python *"],
            "require_allowlist": True,
            "forbid_shell_metacharacters": True,
        },
    }

    with patch("modules.infrastructure.wre_core.src.codeact_executor.subprocess.run") as mock_run:
        class _Result:
            returncode = 0
            stdout = "Python 3.x"
            stderr = ""

        mock_run.return_value = _Result()
        result = executor.execute(skill, {})

    assert result.success is True
    assert mock_run.call_count == 1
    _, kwargs = mock_run.call_args
    assert kwargs.get("shell") is False


def test_readonly_git_command_still_runs_from_repo_root(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    executor = CodeActExecutor(repo_root=repo)
    skill = {
        "format": "codeact",
        "code_section": {
            "main_action": {"type": "shell", "command": "git status --short", "capture": "out"}
        },
        "safety_gates": {
            "allowed_commands": ["git status *"],
            "require_allowlist": True,
            "forbid_shell_metacharacters": True,
        },
    }

    with patch("modules.infrastructure.wre_core.src.codeact_executor.subprocess.run") as mock_run:
        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        mock_run.return_value = _Result()
        result = executor.execute(skill, {})

    assert result.success is True
    assert mock_run.call_count == 1
    _, kwargs = mock_run.call_args
    assert kwargs.get("cwd") == str(repo.resolve())


def test_mutating_git_command_from_shared_root_is_blocked_before_subprocess(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    executor = CodeActExecutor(repo_root=repo)
    skill = {
        "format": "codeact",
        "code_section": {
            "main_action": {"type": "shell", "command": "git add README.md", "capture": "out"}
        },
        "safety_gates": {
            "allowed_commands": ["git *"],
            "require_allowlist": True,
            "forbid_shell_metacharacters": True,
        },
    }

    with patch("modules.infrastructure.wre_core.src.codeact_executor.subprocess.run") as mock_run:
        result = executor.execute(skill, {})

    assert result.success is False
    assert "worker git cwd guard" in (result.error or "")
    assert "FAIL_CLAIMED_WORKTREE_MISSING" in (result.error or "")
    assert mock_run.call_count == 0


def test_mutating_git_command_runs_only_from_claimed_worktree(tmp_path: Path):
    repo = tmp_path / "repo"
    worktree = tmp_path / "worker-worktree"
    repo.mkdir()
    worktree.mkdir()
    executor = CodeActExecutor(repo_root=repo, worker_worktree_path=worktree)
    skill = {
        "format": "codeact",
        "code_section": {
            "main_action": {"type": "shell", "command": "git add README.md", "capture": "out"}
        },
        "safety_gates": {
            "allowed_commands": ["git *"],
            "require_allowlist": True,
            "forbid_shell_metacharacters": True,
        },
    }

    with patch("modules.infrastructure.wre_core.src.codeact_executor.subprocess.run") as mock_run:
        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        mock_run.return_value = _Result()
        result = executor.execute(skill, {})

    assert result.success is True
    assert mock_run.call_count == 1
    _, kwargs = mock_run.call_args
    assert kwargs.get("cwd") == str(worktree.resolve())


def test_metacharacter_policy_blocks_command():
    executor = CodeActExecutor(repo_root=Path("."))
    skill = {
        "format": "codeact",
        "code_section": {
            "main_action": {"type": "shell", "command": "python --version && whoami", "capture": "out"}
        },
        "safety_gates": {
            "allowed_commands": ["python *"],
            "require_allowlist": True,
            "forbid_shell_metacharacters": True,
        },
    }

    result = executor.execute(skill, {})
    assert result.success is False
    assert "metacharacter policy" in (result.error or "").lower()
