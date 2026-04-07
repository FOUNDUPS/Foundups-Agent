"""Safety gates for AutoAgent Lab experiments.

All gates are fail-closed: if a gate cannot be evaluated, the experiment halts.

Gates:
1. Score regression rejection — discard if new_score < baseline
2. File allowlist — block writes outside allowed paths
3. Iteration budget — stop when max_iterations reached
4. Workspace isolation — all mutations happen in workspace/ only
"""

from __future__ import annotations

import fnmatch
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("autoagent_lab.safety")


class SafetyViolation(Exception):
    """Raised when an experiment violates a safety gate."""


# ---------------------------------------------------------------------------
# Gate 1: Score Regression
# ---------------------------------------------------------------------------


@dataclass
class ScoreDecision:
    """Result of a score-gate check."""

    keep: bool
    baseline: float
    candidate: float
    delta: float
    reason: str


def check_score_regression(baseline: float, candidate: float, min_improvement: float = 0.0) -> ScoreDecision:
    """Check whether a candidate score improves on the baseline.

    Args:
        baseline: Score before mutation.
        candidate: Score after mutation.
        min_improvement: Minimum delta required to keep (default: 0.0 = any improvement).

    Returns:
        ScoreDecision with keep=True if candidate is sufficiently better.
    """
    delta = candidate - baseline

    if delta < 0:
        return ScoreDecision(
            keep=False,
            baseline=baseline,
            candidate=candidate,
            delta=delta,
            reason=f"regression: {delta:+.4f}",
        )

    if delta < min_improvement:
        return ScoreDecision(
            keep=False,
            baseline=baseline,
            candidate=candidate,
            delta=delta,
            reason=f"improvement {delta:+.4f} below threshold {min_improvement}",
        )

    return ScoreDecision(
        keep=True,
        baseline=baseline,
        candidate=candidate,
        delta=delta,
        reason=f"improvement: {delta:+.4f}",
    )


# ---------------------------------------------------------------------------
# Gate 2: File Allowlist
# ---------------------------------------------------------------------------

DEFAULT_WRITE_ALLOWLIST = [
    "modules/infrastructure/autoagent_lab/workspace/**",
    "modules/infrastructure/autoagent_lab/logs/**",
]


@dataclass
class FileAllowlist:
    """Enforces which paths the experiment can write to."""

    patterns: list[str] = field(default_factory=lambda: list(DEFAULT_WRITE_ALLOWLIST))
    repo_root: Path = field(default_factory=lambda: Path(os.environ.get("FOUNDUPS_REPO_ROOT", ".")))

    def check_write(self, path: str | Path) -> bool:
        """Check if a path is allowed for writing.

        Args:
            path: Absolute or repo-relative path.

        Returns:
            True if the path matches at least one allowlist pattern.
        """
        rel = self._to_relative(path)
        # Normalize to forward slashes for glob matching
        rel_str = rel.as_posix()
        return any(fnmatch.fnmatch(rel_str, pattern) for pattern in self.patterns)

    def enforce_write(self, path: str | Path) -> None:
        """Raise SafetyViolation if the path is not in the allowlist.

        Args:
            path: Path to check.

        Raises:
            SafetyViolation: If the path is not allowed.
        """
        if not self.check_write(path):
            rel = self._to_relative(path)
            raise SafetyViolation(
                f"Write blocked: '{rel.as_posix()}' is not in the allowlist. "
                f"Allowed patterns: {self.patterns}"
            )

    def _to_relative(self, path: str | Path) -> Path:
        """Convert to a repo-relative path."""
        p = Path(path)
        try:
            return p.relative_to(self.repo_root)
        except ValueError:
            return p


# ---------------------------------------------------------------------------
# Gate 3: Iteration Budget
# ---------------------------------------------------------------------------


@dataclass
class IterationBudget:
    """Tracks iteration count against a maximum."""

    max_iterations: int
    current: int = 0

    def has_budget(self) -> bool:
        """Check if more iterations are allowed."""
        return self.current < self.max_iterations

    def consume(self) -> None:
        """Consume one iteration. Raises SafetyViolation if budget exhausted."""
        if not self.has_budget():
            raise SafetyViolation(
                f"Iteration budget exhausted: {self.current}/{self.max_iterations}"
            )
        self.current += 1

    @property
    def remaining(self) -> int:
        return max(0, self.max_iterations - self.current)


# ---------------------------------------------------------------------------
# Gate 4: Workspace Isolation
# ---------------------------------------------------------------------------


def validate_workspace_path(workspace_dir: Path, target_path: Path) -> None:
    """Ensure a target path is inside the workspace directory.

    Args:
        workspace_dir: The experiment workspace root.
        target_path: The path being written to.

    Raises:
        SafetyViolation: If target_path escapes the workspace.
    """
    try:
        target_path.resolve().relative_to(workspace_dir.resolve())
    except ValueError:
        raise SafetyViolation(
            f"Workspace escape: '{target_path}' is not inside workspace '{workspace_dir}'"
        )
