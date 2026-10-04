#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hardening tests for CodeAct executor safety policy."""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

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


def _exit_truth_skill(code_section):
    return {
        "format": "codeact",
        "code_section": code_section,
        "safety_gates": {
            "allowed_commands": ["python *"],
            "require_allowlist": True,
            "forbid_shell_metacharacters": True,
        },
    }


@pytest.mark.parametrize("returncode", [17, -9], ids=["positive", "negative"])
@pytest.mark.parametrize("stderr", ["", "failure detail " * 900], ids=["empty", "long"])
@pytest.mark.parametrize("capture", [False, True], ids=["no_capture", "capture"])
def test_nonzero_shell_exit_is_failure(returncode, stderr, capture, tmp_path):
    executor = CodeActExecutor(repo_root=tmp_path)
    action = {"type": "shell", "command": "python --version"}
    if capture:
        action["capture"] = "failed_capture"
    skill = _exit_truth_skill({"main_action": action})
    context = {"seed": "preserved"}
    with patch("modules.infrastructure.wre_core.src.codeact_executor.subprocess.run") as run:
        run.return_value = CompletedProcess([], returncode, "failed stdout", stderr)
        result = executor.execute(skill, context)
    assert run.call_count == 1
    assert result.success is False
    assert isinstance(result.error, str) and str(returncode) in result.error
    assert 0 < len(result.error) <= 1024
    assert result.actions_executed == 0
    assert result.outputs == context == {"seed": "preserved"}


@pytest.mark.parametrize("stderr", ["", "warning only"], ids=["empty", "warning"])
@pytest.mark.parametrize("capture", [False, True], ids=["no_capture", "capture"])
def test_zero_shell_exit_preserves_success(stderr, capture, tmp_path):
    executor = CodeActExecutor(repo_root=tmp_path)
    action = {"type": "shell", "command": "python --version"}
    if capture:
        action["capture"] = "captured"
    skill = _exit_truth_skill({"main_action": action})
    with patch("modules.infrastructure.wre_core.src.codeact_executor.subprocess.run") as run:
        run.return_value = CompletedProcess([], 0, "  useful stdout\n", stderr)
        result = executor.execute(skill, {"seed": "preserved"})
    assert run.call_count == 1
    assert result.success is True and result.error is None
    assert result.actions_executed == 1
    assert result.outputs == ({"seed": "preserved", "captured": "useful stdout"}
                              if capture else {"seed": "preserved"})


@pytest.mark.parametrize("failure_index", [1, 2, 3], ids=["pre", "main", "post"])
def test_nonzero_shell_exit_stops_stage_and_retains_prefix(failure_index, tmp_path):
    later_effects = []
    executor = CodeActExecutor(repo_root=tmp_path, llm_callback=later_effects.append)
    names = ["pre_first", "pre_second", "main", "post_first", "post_last"]
    actions = [{"type": "shell", "command": "python --version " + name,
                "capture": name} for name in names]
    skill = _exit_truth_skill({
        "pre_actions": actions[:2],
        "conditionals": [{"if": "True", "then": {"type": "continue"}}],
        "main_action": actions[2],
        "post_actions": actions[3:] + [{"type": "llm_generate", "prompt_template": "later"}],
    })
    results = [CompletedProcess([], 17 if index == failure_index else 0,
                                "value_" + name, "") for index, name in enumerate(names)]
    with patch("modules.infrastructure.wre_core.src.codeact_executor.subprocess.run") as run:
        run.side_effect = results
        with patch.object(executor, "_evaluate_conditional",
                          wraps=executor._evaluate_conditional) as conditional:
            result = executor.execute(skill, {"seed": "preserved"})
    assert result.success is False and "17" in (result.error or "")
    assert 0 < len(result.error) <= 1024
    assert result.actions_executed == failure_index
    assert result.outputs == dict({"seed": "preserved"},
                                  **{name: "value_" + name for name in names[:failure_index]})
    assert run.call_count == failure_index + 1
    assert [call.args[0][-1] for call in run.call_args_list] == names[:failure_index + 1]
    assert conditional.call_count == (0 if failure_index < 2 else 1)
    assert later_effects == []
