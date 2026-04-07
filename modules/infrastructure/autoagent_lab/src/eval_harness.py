"""Evaluation harness for AutoAgent Lab experiments.

Deterministic scoring for WRE skill configs. Uses weighted components:
- config_validity (0.2): YAML parse + required fields
- wsp_compliance (0.2): WSP references are structurally valid
- historical_fidelity (0.3): From injected context (PatternMemory adapter future)
- historical_quality (0.3): From injected context (PatternMemory adapter future)

Phase 2 design: Pure function, no direct DB dependency. Historical scores
are passed via context dict. Production PatternMemory adapter is future work.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger("autoagent_lab.eval")

# Score component weights (from spec)
WEIGHTS = {
    "config_validity": 0.2,
    "wsp_compliance": 0.2,
    "historical_fidelity": 0.3,
    "historical_quality": 0.3,
}

# Required fields in skill frontmatter
REQUIRED_FIELDS = {"name", "description"}

# Optional but scored fields
SCORED_FIELDS = {"version", "agents", "domain", "category"}

# WSP reference pattern: WSP followed by digits (e.g., WSP 49, WSP 97)
WSP_PATTERN = re.compile(r"WSP\s*(\d+)", re.IGNORECASE)


@dataclass
class EvalResult:
    """Result of skill config evaluation.

    All scores are in range [0.0, 1.0].
    """

    total_score: float
    config_validity: float
    wsp_compliance: float
    historical_fidelity: float
    historical_quality: float
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "total_score": self.total_score,
            "config_validity": self.config_validity,
            "wsp_compliance": self.wsp_compliance,
            "historical_fidelity": self.historical_fidelity,
            "historical_quality": self.historical_quality,
            "reasons": self.reasons,
        }


def eval_skill_config(
    skill_path: Path | str,
    context: Optional[dict] = None,
    weights: Optional[dict[str, float]] = None,
) -> EvalResult:
    """Evaluate a skill config and return a structured score.

    Args:
        skill_path: Path to the SKILL.md file.
        context: Optional dict with historical data:
            - historical_fidelity: float (0.0-1.0) from PatternMemory
            - historical_quality: float (0.0-1.0) from PatternMemory
            If not provided, defaults to 0.5 (neutral baseline).
        weights: Optional custom weights (must sum to 1.0).
            Defaults to spec weights if not provided.

    Returns:
        EvalResult with total_score and component scores.

    The score is deterministic: same input = same output.
    """
    skill_path = Path(skill_path)
    context = context or {}
    w = weights or WEIGHTS

    reasons: list[str] = []

    # --- Component 1: Config Validity ---
    config_validity, validity_reasons = _eval_config_validity(skill_path)
    reasons.extend(validity_reasons)

    # --- Component 2: WSP Compliance ---
    wsp_compliance, wsp_reasons = _eval_wsp_compliance(skill_path)
    reasons.extend(wsp_reasons)

    # --- Component 3: Historical Fidelity (from context) ---
    historical_fidelity = _clamp(context.get("historical_fidelity", 0.5))
    if "historical_fidelity" not in context:
        reasons.append("historical_fidelity: using default 0.5 (no context)")

    # --- Component 4: Historical Quality (from context) ---
    historical_quality = _clamp(context.get("historical_quality", 0.5))
    if "historical_quality" not in context:
        reasons.append("historical_quality: using default 0.5 (no context)")

    # --- Weighted Total ---
    total_score = _clamp(
        config_validity * w["config_validity"]
        + wsp_compliance * w["wsp_compliance"]
        + historical_fidelity * w["historical_fidelity"]
        + historical_quality * w["historical_quality"]
    )

    return EvalResult(
        total_score=total_score,
        config_validity=config_validity,
        wsp_compliance=wsp_compliance,
        historical_fidelity=historical_fidelity,
        historical_quality=historical_quality,
        reasons=reasons,
    )


def _eval_config_validity(skill_path: Path) -> tuple[float, list[str]]:
    """Evaluate config validity by parsing YAML frontmatter.

    Returns:
        (score, list of reasons)
    """
    reasons = []

    # File must exist
    if not skill_path.exists():
        return 0.0, ["config_validity: file not found"]

    try:
        content = skill_path.read_text(encoding="utf-8")
    except Exception as e:
        return 0.0, [f"config_validity: read error: {e}"]

    # Parse YAML frontmatter (between --- delimiters)
    frontmatter = _extract_frontmatter(content)
    if frontmatter is None:
        return 0.0, ["config_validity: no YAML frontmatter found"]

    try:
        data = yaml.safe_load(frontmatter)
    except yaml.YAMLError as e:
        return 0.0, [f"config_validity: YAML parse error: {e}"]

    if not isinstance(data, dict):
        return 0.0, ["config_validity: frontmatter is not a mapping"]

    # Check required fields
    score = 1.0
    missing_required = REQUIRED_FIELDS - set(data.keys())
    if missing_required:
        penalty = len(missing_required) * 0.25
        score -= penalty
        reasons.append(f"config_validity: missing required fields: {sorted(missing_required)}")

    # Bonus for optional scored fields
    present_scored = SCORED_FIELDS & set(data.keys())
    bonus = len(present_scored) * 0.05
    score = min(1.0, score + bonus)
    if present_scored:
        reasons.append(f"config_validity: has scored fields: {sorted(present_scored)}")

    # Check for empty required values
    for req in REQUIRED_FIELDS:
        if req in data and not data[req]:
            score -= 0.1
            reasons.append(f"config_validity: '{req}' is empty")

    return _clamp(score), reasons


def _eval_wsp_compliance(skill_path: Path) -> tuple[float, list[str]]:
    """Evaluate WSP compliance by checking WSP references.

    Returns:
        (score, list of reasons)
    """
    reasons = []

    if not skill_path.exists():
        return 0.0, ["wsp_compliance: file not found"]

    try:
        content = skill_path.read_text(encoding="utf-8")
    except Exception as e:
        return 0.0, [f"wsp_compliance: read error: {e}"]

    # Find all WSP references
    wsp_refs = WSP_PATTERN.findall(content)
    wsp_numbers = [int(n) for n in wsp_refs]

    if not wsp_numbers:
        # No WSP references - neutral score (not necessarily bad)
        return 0.5, ["wsp_compliance: no WSP references found (neutral)"]

    # Validate WSP numbers are in plausible range (1-200)
    valid_refs = [n for n in wsp_numbers if 1 <= n <= 200]
    invalid_refs = [n for n in wsp_numbers if n < 1 or n > 200]

    if invalid_refs:
        reasons.append(f"wsp_compliance: invalid WSP numbers: {invalid_refs}")

    # Score based on ratio of valid refs
    if wsp_numbers:
        ratio = len(valid_refs) / len(wsp_numbers)
    else:
        ratio = 0.5

    # Bonus for having multiple valid refs (shows thoughtful compliance)
    if len(valid_refs) >= 3:
        ratio = min(1.0, ratio + 0.1)
        reasons.append(f"wsp_compliance: {len(valid_refs)} valid WSP refs (bonus)")
    elif len(valid_refs) >= 1:
        reasons.append(f"wsp_compliance: {len(valid_refs)} valid WSP ref(s)")

    return _clamp(ratio), reasons


def _extract_frontmatter(content: str) -> Optional[str]:
    """Extract YAML frontmatter from markdown content.

    Frontmatter is delimited by --- at start and end.
    """
    lines = content.strip().split("\n")
    if not lines or not lines[0].strip() == "---":
        return None

    # Find closing ---
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:i])

    return None


def _clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp a value to a range."""
    return max(min_val, min(max_val, value))


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def quick_score(skill_path: Path | str, context: Optional[dict] = None) -> float:
    """Convenience function returning just the total score.

    Args:
        skill_path: Path to SKILL.md
        context: Optional historical context

    Returns:
        Total score as float in [0.0, 1.0]
    """
    return eval_skill_config(skill_path, context).total_score


def validate_weights(weights: dict[str, float]) -> list[str]:
    """Validate custom weights.

    Args:
        weights: Dict of component name -> weight.

    Returns:
        List of validation errors (empty = valid).
    """
    errors = []
    expected_keys = set(WEIGHTS.keys())
    actual_keys = set(weights.keys())

    if actual_keys != expected_keys:
        errors.append(f"weights must have keys {sorted(expected_keys)}, got {sorted(actual_keys)}")

    total = sum(weights.values())
    if abs(total - 1.0) > 0.01:
        errors.append(f"weights must sum to 1.0, got {total:.3f}")

    for k, v in weights.items():
        if not isinstance(v, (int, float)) or v < 0:
            errors.append(f"weights['{k}'] must be non-negative number, got {v!r}")

    return errors
