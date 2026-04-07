"""Tests for experiment config loading and validation."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from modules.infrastructure.autoagent_lab.src.experiment_config import (
    BudgetSpec,
    EvalSpec,
    ExperimentSpec,
    TargetSpec,
    is_lab_enabled,
    load_experiment_spec,
)


# ---------------------------------------------------------------------------
# TargetSpec validation
# ---------------------------------------------------------------------------


class TestTargetSpec:

    def test_valid_target(self):
        t = TargetSpec(skill_path="modules/foo/SKILL.md", mutable_fields=["agents"])
        assert t.validate() == []

    def test_missing_skill_path(self):
        t = TargetSpec(skill_path="", mutable_fields=["agents"])
        errors = t.validate()
        assert any("skill_path" in e for e in errors)

    def test_empty_mutable_fields(self):
        t = TargetSpec(skill_path="foo.md", mutable_fields=[])
        errors = t.validate()
        assert any("mutable_fields" in e for e in errors)

    def test_invalid_mutable_field(self):
        t = TargetSpec(skill_path="foo.md", mutable_fields=["agents", "INVALID"])
        errors = t.validate()
        assert any("INVALID" in e for e in errors)

    def test_all_valid_fields(self):
        t = TargetSpec(
            skill_path="foo.md",
            mutable_fields=["agents", "wsp_chain", "domains", "tokens_budget", "prompt"],
        )
        assert t.validate() == []


# ---------------------------------------------------------------------------
# EvalSpec validation
# ---------------------------------------------------------------------------


class TestEvalSpec:

    def test_default_weights_valid(self):
        e = EvalSpec()
        assert e.validate() == []

    def test_weights_must_sum_to_one(self):
        e = EvalSpec(weights={
            "config_validity": 0.5,
            "wsp_compliance": 0.5,
            "historical_fidelity": 0.5,
            "historical_quality": 0.5,
        })
        errors = e.validate()
        assert any("sum to 1.0" in e for e in errors)

    def test_missing_weight_key(self):
        e = EvalSpec(weights={"config_validity": 1.0})
        errors = e.validate()
        assert any("must have keys" in e for e in errors)

    def test_negative_weight(self):
        e = EvalSpec(weights={
            "config_validity": -0.1,
            "wsp_compliance": 0.4,
            "historical_fidelity": 0.3,
            "historical_quality": 0.4,
        })
        errors = e.validate()
        assert any("non-negative" in e for e in errors)


# ---------------------------------------------------------------------------
# BudgetSpec validation
# ---------------------------------------------------------------------------


class TestBudgetSpec:

    def test_default_valid(self):
        b = BudgetSpec()
        assert b.validate() == []

    def test_zero_iterations_invalid(self):
        b = BudgetSpec(max_iterations=0)
        errors = b.validate()
        assert any("max_iterations" in e for e in errors)

    def test_negative_improvement_invalid(self):
        b = BudgetSpec(min_improvement=-0.1)
        errors = b.validate()
        assert any("min_improvement" in e for e in errors)


# ---------------------------------------------------------------------------
# ExperimentSpec validation
# ---------------------------------------------------------------------------


class TestExperimentSpec:

    def test_valid_spec(self):
        spec = ExperimentSpec(
            name="test",
            target=TargetSpec(skill_path="foo.md", mutable_fields=["agents"]),
            eval=EvalSpec(),
            budget=BudgetSpec(),
        )
        assert spec.validate() == []

    def test_empty_name_invalid(self):
        spec = ExperimentSpec(
            name="",
            target=TargetSpec(skill_path="foo.md", mutable_fields=["agents"]),
            eval=EvalSpec(),
            budget=BudgetSpec(),
        )
        errors = spec.validate()
        assert any("name" in e for e in errors)


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


class TestLoadExperimentSpec:

    def _write_yaml(self, data: dict) -> Path:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8")
        yaml.dump(data, tmp)
        tmp.close()
        return Path(tmp.name)

    def test_loads_valid_spec(self):
        path = self._write_yaml({
            "name": "test-experiment",
            "target": {
                "skill_path": "modules/foo/SKILL.md",
                "mutable_fields": ["agents", "tokens_budget"],
            },
            "eval": {
                "weights": {
                    "config_validity": 0.2,
                    "wsp_compliance": 0.2,
                    "historical_fidelity": 0.3,
                    "historical_quality": 0.3,
                },
            },
            "budget": {"max_iterations": 5, "min_improvement": 0.01},
        })
        try:
            spec = load_experiment_spec(path)
            assert spec.name == "test-experiment"
            assert spec.target.skill_path == "modules/foo/SKILL.md"
            assert spec.budget.max_iterations == 5
            assert spec.budget.min_improvement == 0.01
        finally:
            os.unlink(path)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_experiment_spec("/nonexistent/spec.yaml")

    def test_invalid_spec_raises_value_error(self):
        path = self._write_yaml({"name": "", "target": {"skill_path": ""}})
        try:
            with pytest.raises(ValueError, match="Invalid experiment spec"):
                load_experiment_spec(path)
        finally:
            os.unlink(path)

    def test_non_mapping_raises_value_error(self):
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8")
        tmp.write("- just a list\n")
        tmp.close()
        try:
            with pytest.raises(ValueError, match="YAML mapping"):
                load_experiment_spec(tmp.name)
        finally:
            os.unlink(tmp.name)

    def test_defaults_applied(self):
        path = self._write_yaml({
            "name": "defaults-test",
            "target": {"skill_path": "foo.md"},
        })
        try:
            spec = load_experiment_spec(path)
            assert spec.budget.max_iterations == 10
            assert spec.budget.min_improvement == 0.0
            assert spec.log_level == "INFO"
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Master switch
# ---------------------------------------------------------------------------


class TestLabEnabled:

    def test_default_disabled(self, monkeypatch):
        monkeypatch.delenv("AUTOAGENT_LAB_ENABLED", raising=False)
        assert is_lab_enabled() is False

    def test_enabled_true(self, monkeypatch):
        monkeypatch.setenv("AUTOAGENT_LAB_ENABLED", "true")
        assert is_lab_enabled() is True

    def test_enabled_one(self, monkeypatch):
        monkeypatch.setenv("AUTOAGENT_LAB_ENABLED", "1")
        assert is_lab_enabled() is True

    def test_enabled_false(self, monkeypatch):
        monkeypatch.setenv("AUTOAGENT_LAB_ENABLED", "false")
        assert is_lab_enabled() is False
