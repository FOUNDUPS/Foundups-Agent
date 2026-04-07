"""Experiment configuration — load and validate experiment specs.

An ExperimentSpec defines what to optimize, how to evaluate, and
what safety budget to enforce. Loaded from YAML files.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger("autoagent_lab.config")

VALID_MUTABLE_FIELDS = frozenset({"agents", "wsp_chain", "domains", "tokens_budget", "prompt"})

DEFAULT_EVAL_WEIGHTS = {
    "config_validity": 0.2,
    "wsp_compliance": 0.2,
    "historical_fidelity": 0.3,
    "historical_quality": 0.3,
}


@dataclass
class TargetSpec:
    """What the experiment optimizes."""

    skill_path: str
    mutable_fields: list[str] = field(default_factory=lambda: ["agents", "tokens_budget"])

    def validate(self) -> list[str]:
        """Return list of validation errors (empty = valid)."""
        errors = []
        if not self.skill_path:
            errors.append("target.skill_path is required")
        if not self.mutable_fields:
            errors.append("target.mutable_fields must have at least one entry")
        for f in self.mutable_fields:
            if f not in VALID_MUTABLE_FIELDS:
                errors.append(f"target.mutable_fields: '{f}' is not valid. Choose from: {sorted(VALID_MUTABLE_FIELDS)}")
        return errors


@dataclass
class EvalSpec:
    """How changes are scored."""

    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_EVAL_WEIGHTS))

    def validate(self) -> list[str]:
        errors = []
        expected_keys = set(DEFAULT_EVAL_WEIGHTS.keys())
        actual_keys = set(self.weights.keys())
        if actual_keys != expected_keys:
            errors.append(f"eval.weights must have keys {sorted(expected_keys)}, got {sorted(actual_keys)}")
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            errors.append(f"eval.weights must sum to 1.0, got {total:.3f}")
        for k, v in self.weights.items():
            if not isinstance(v, (int, float)) or v < 0:
                errors.append(f"eval.weights.{k} must be a non-negative number, got {v!r}")
        return errors


@dataclass
class BudgetSpec:
    """Safety budget for the experiment."""

    max_iterations: int = 10
    min_improvement: float = 0.0

    def validate(self) -> list[str]:
        errors = []
        if self.max_iterations < 1:
            errors.append(f"budget.max_iterations must be >= 1, got {self.max_iterations}")
        if self.min_improvement < 0.0:
            errors.append(f"budget.min_improvement must be >= 0.0, got {self.min_improvement}")
        return errors


@dataclass
class ExperimentSpec:
    """Complete experiment specification."""

    name: str
    target: TargetSpec
    eval: EvalSpec
    budget: BudgetSpec
    log_level: str = "INFO"

    def validate(self) -> list[str]:
        """Return all validation errors across all sub-specs."""
        errors = []
        if not self.name or not self.name.strip():
            errors.append("name is required")
        errors.extend(self.target.validate())
        errors.extend(self.eval.validate())
        errors.extend(self.budget.validate())
        return errors


def load_experiment_spec(path: str | Path) -> ExperimentSpec:
    """Load an ExperimentSpec from a YAML file.

    Args:
        path: Path to the YAML spec file.

    Returns:
        Validated ExperimentSpec.

    Raises:
        FileNotFoundError: If the spec file doesn't exist.
        ValueError: If the spec is invalid.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Experiment spec not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"Experiment spec must be a YAML mapping, got {type(raw).__name__}")

    target_raw = raw.get("target", {})
    eval_raw = raw.get("eval", {})
    budget_raw = raw.get("budget", {})

    spec = ExperimentSpec(
        name=raw.get("name", ""),
        target=TargetSpec(
            skill_path=target_raw.get("skill_path", ""),
            mutable_fields=target_raw.get("mutable_fields", ["agents", "tokens_budget"]),
        ),
        eval=EvalSpec(
            weights=eval_raw.get("weights", dict(DEFAULT_EVAL_WEIGHTS)),
        ),
        budget=BudgetSpec(
            max_iterations=budget_raw.get("max_iterations", _env_max_iterations()),
            min_improvement=budget_raw.get("min_improvement", 0.0),
        ),
        log_level=raw.get("log_level", "INFO"),
    )

    errors = spec.validate()
    if errors:
        raise ValueError(f"Invalid experiment spec ({path}):\n" + "\n".join(f"  - {e}" for e in errors))

    return spec


def _env_max_iterations() -> int:
    """Read max iterations from env, defaulting to 10."""
    try:
        return int(os.environ.get("AUTOAGENT_MAX_ITERATIONS", "10"))
    except ValueError:
        return 10


def is_lab_enabled() -> bool:
    """Check the AUTOAGENT_LAB_ENABLED master switch."""
    return os.environ.get("AUTOAGENT_LAB_ENABLED", "false").strip().lower() in ("true", "1", "yes", "on")
