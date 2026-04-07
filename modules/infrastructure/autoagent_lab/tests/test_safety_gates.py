"""Tests for safety gates — score regression, allowlist, budget, workspace isolation."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from modules.infrastructure.autoagent_lab.src.safety_gates import (
    FileAllowlist,
    IterationBudget,
    SafetyViolation,
    ScoreDecision,
    check_score_regression,
    validate_workspace_path,
)


# ---------------------------------------------------------------------------
# Gate 1: Score Regression
# ---------------------------------------------------------------------------


class TestScoreRegression:

    def test_improvement_keeps(self):
        d = check_score_regression(baseline=0.70, candidate=0.75)
        assert d.keep is True
        assert d.delta == pytest.approx(0.05)

    def test_regression_discards(self):
        d = check_score_regression(baseline=0.80, candidate=0.75)
        assert d.keep is False
        assert "regression" in d.reason

    def test_no_change_keeps(self):
        d = check_score_regression(baseline=0.70, candidate=0.70)
        assert d.keep is True
        assert d.delta == pytest.approx(0.0)

    def test_min_improvement_threshold(self):
        d = check_score_regression(baseline=0.70, candidate=0.71, min_improvement=0.05)
        assert d.keep is False
        assert "below threshold" in d.reason

    def test_min_improvement_met(self):
        d = check_score_regression(baseline=0.70, candidate=0.76, min_improvement=0.05)
        assert d.keep is True

    def test_decision_fields(self):
        d = check_score_regression(baseline=0.50, candidate=0.60)
        assert isinstance(d, ScoreDecision)
        assert d.baseline == 0.50
        assert d.candidate == 0.60
        assert d.delta == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# Gate 2: File Allowlist
# ---------------------------------------------------------------------------


class TestFileAllowlist:

    def test_allowed_workspace_path(self):
        a = FileAllowlist(repo_root=Path("."))
        assert a.check_write("modules/infrastructure/autoagent_lab/workspace/exp_001/SKILL.md") is True

    def test_allowed_logs_path(self):
        a = FileAllowlist(repo_root=Path("."))
        assert a.check_write("modules/infrastructure/autoagent_lab/logs/exp_001.jsonl") is True

    def test_blocked_wre_path(self):
        a = FileAllowlist(repo_root=Path("."))
        assert a.check_write("modules/infrastructure/wre_core/src/pattern_memory.py") is False

    def test_blocked_env_file(self):
        a = FileAllowlist(repo_root=Path("."))
        assert a.check_write(".env") is False

    def test_blocked_openclaw(self):
        a = FileAllowlist(repo_root=Path("."))
        assert a.check_write("modules/communication/moltbot_bridge/src/openclaw_dae.py") is False

    def test_enforce_raises_on_blocked(self):
        a = FileAllowlist(repo_root=Path("."))
        with pytest.raises(SafetyViolation, match="Write blocked"):
            a.enforce_write("modules/infrastructure/wre_core/bad_write.py")

    def test_enforce_passes_on_allowed(self):
        a = FileAllowlist(repo_root=Path("."))
        # Should not raise
        a.enforce_write("modules/infrastructure/autoagent_lab/workspace/test.yaml")

    def test_custom_patterns(self):
        a = FileAllowlist(patterns=["custom/**"], repo_root=Path("."))
        assert a.check_write("custom/foo.txt") is True
        assert a.check_write("other/foo.txt") is False


# ---------------------------------------------------------------------------
# Gate 3: Iteration Budget
# ---------------------------------------------------------------------------


class TestIterationBudget:

    def test_has_budget_initially(self):
        b = IterationBudget(max_iterations=5)
        assert b.has_budget() is True
        assert b.remaining == 5

    def test_consume_decrements(self):
        b = IterationBudget(max_iterations=3)
        b.consume()
        assert b.current == 1
        assert b.remaining == 2

    def test_budget_exhaustion(self):
        b = IterationBudget(max_iterations=2)
        b.consume()
        b.consume()
        assert b.has_budget() is False
        with pytest.raises(SafetyViolation, match="budget exhausted"):
            b.consume()

    def test_single_iteration(self):
        b = IterationBudget(max_iterations=1)
        b.consume()
        assert b.remaining == 0
        assert b.has_budget() is False


# ---------------------------------------------------------------------------
# Gate 4: Workspace Isolation
# ---------------------------------------------------------------------------


class TestWorkspaceIsolation:

    def test_valid_path_inside_workspace(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        target = workspace / "exp_001" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.touch()
        # Should not raise
        validate_workspace_path(workspace, target)

    def test_escape_raises(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        outside = tmp_path / "production" / "SKILL.md"
        outside.parent.mkdir(parents=True)
        outside.touch()
        with pytest.raises(SafetyViolation, match="Workspace escape"):
            validate_workspace_path(workspace, outside)

    def test_parent_traversal_blocked(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        # Path that uses .. to escape
        escape = workspace / ".." / "production" / "SKILL.md"
        with pytest.raises(SafetyViolation, match="Workspace escape"):
            validate_workspace_path(workspace, escape)
