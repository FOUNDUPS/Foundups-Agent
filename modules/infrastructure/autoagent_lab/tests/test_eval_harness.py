"""Tests for eval harness — deterministic skill config scoring.

Covers:
- Valid skill config scoring
- Malformed/missing skill metadata
- Missing/malformed WSP chain handling
- Context-driven historical fidelity/quality
- Score range clamped to 0.0-1.0
- Deterministic output on same input
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from modules.infrastructure.autoagent_lab.src.eval_harness import (
    EvalResult,
    WEIGHTS,
    _clamp,
    _eval_config_validity,
    _eval_wsp_compliance,
    _extract_frontmatter,
    eval_skill_config,
    quick_score,
    validate_weights,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_skill_content():
    """Minimal valid SKILL.md content."""
    return """---
name: test_skill
description: A test skill for evaluation
version: 1.0
agents: [qwen]
domain: testing
category: workflow
---
# Test Skill

This skill does testing things.

## WSP Compliance
References WSP 49 for structure and WSP 97 for boundaries.
"""


@pytest.fixture
def minimal_skill_content():
    """Skill with only required fields."""
    return """---
name: minimal_skill
description: Minimal required fields only
---
# Minimal Skill
"""


@pytest.fixture
def malformed_skill_content():
    """SKILL.md with invalid YAML."""
    return """---
name: broken
description: [unclosed bracket
---
# Broken
"""


@pytest.fixture
def missing_frontmatter_content():
    """SKILL.md without YAML frontmatter."""
    return """# No Frontmatter

This skill has no YAML frontmatter at all.
"""


@pytest.fixture
def empty_required_fields_content():
    """SKILL.md with empty required fields."""
    return """---
name: ""
description: ""
version: 1.0
---
# Empty Required
"""


@pytest.fixture
def many_wsp_refs_content():
    """SKILL.md with many WSP references."""
    return """---
name: wsp_heavy
description: Lots of WSP refs
---
# WSP Heavy Skill

## Compliance
- WSP 3: Domains
- WSP 49: Structure
- WSP 50: Pre-Action
- WSP 72: Independence
- WSP 91: Observability
- WSP 97: Boundaries
"""


@pytest.fixture
def invalid_wsp_refs_content():
    """SKILL.md with invalid WSP numbers."""
    return """---
name: bad_wsp
description: Invalid WSP refs
---
# Bad WSP

References WSP 999, WSP 0, and WSP -5.
"""


def _write_temp_skill(content: str) -> Path:
    """Write content to a temp SKILL.md and return path."""
    fd, path = tempfile.mkstemp(suffix=".md", prefix="SKILL_")
    os.close(fd)
    Path(path).write_text(content, encoding="utf-8")
    return Path(path)


# ---------------------------------------------------------------------------
# EvalResult
# ---------------------------------------------------------------------------


class TestEvalResult:

    def test_to_dict(self):
        result = EvalResult(
            total_score=0.75,
            config_validity=0.9,
            wsp_compliance=0.8,
            historical_fidelity=0.7,
            historical_quality=0.6,
            reasons=["test reason"],
        )
        d = result.to_dict()
        assert d["total_score"] == 0.75
        assert d["config_validity"] == 0.9
        assert d["reasons"] == ["test reason"]

    def test_default_reasons_empty(self):
        result = EvalResult(
            total_score=0.5,
            config_validity=0.5,
            wsp_compliance=0.5,
            historical_fidelity=0.5,
            historical_quality=0.5,
        )
        assert result.reasons == []


# ---------------------------------------------------------------------------
# Config Validity
# ---------------------------------------------------------------------------


class TestConfigValidity:

    def test_valid_config_high_score(self, valid_skill_content):
        path = _write_temp_skill(valid_skill_content)
        try:
            score, reasons = _eval_config_validity(path)
            assert score >= 0.8  # Has all fields
        finally:
            path.unlink()

    def test_minimal_config_valid(self, minimal_skill_content):
        path = _write_temp_skill(minimal_skill_content)
        try:
            score, reasons = _eval_config_validity(path)
            assert score >= 0.5  # Has required fields
        finally:
            path.unlink()

    def test_malformed_yaml_zero_score(self, malformed_skill_content):
        path = _write_temp_skill(malformed_skill_content)
        try:
            score, reasons = _eval_config_validity(path)
            assert score == 0.0
            assert any("YAML parse error" in r for r in reasons)
        finally:
            path.unlink()

    def test_missing_frontmatter_zero_score(self, missing_frontmatter_content):
        path = _write_temp_skill(missing_frontmatter_content)
        try:
            score, reasons = _eval_config_validity(path)
            assert score == 0.0
            assert any("no YAML frontmatter" in r for r in reasons)
        finally:
            path.unlink()

    def test_empty_required_fields_penalized(self, empty_required_fields_content):
        path = _write_temp_skill(empty_required_fields_content)
        try:
            score, reasons = _eval_config_validity(path)
            assert score < 1.0
            assert any("is empty" in r for r in reasons)
        finally:
            path.unlink()

    def test_file_not_found_zero_score(self):
        score, reasons = _eval_config_validity(Path("/nonexistent/SKILL.md"))
        assert score == 0.0
        assert any("not found" in r for r in reasons)


# ---------------------------------------------------------------------------
# WSP Compliance
# ---------------------------------------------------------------------------


class TestWSPCompliance:

    def test_many_wsp_refs_bonus(self, many_wsp_refs_content):
        path = _write_temp_skill(many_wsp_refs_content)
        try:
            score, reasons = _eval_wsp_compliance(path)
            assert score >= 0.9  # Bonus for 3+ refs
            assert any("bonus" in r for r in reasons)
        finally:
            path.unlink()

    def test_no_wsp_refs_neutral(self, minimal_skill_content):
        path = _write_temp_skill(minimal_skill_content)
        try:
            score, reasons = _eval_wsp_compliance(path)
            assert score == 0.5  # Neutral
            assert any("neutral" in r for r in reasons)
        finally:
            path.unlink()

    def test_invalid_wsp_numbers_penalized(self, invalid_wsp_refs_content):
        path = _write_temp_skill(invalid_wsp_refs_content)
        try:
            score, reasons = _eval_wsp_compliance(path)
            assert score < 0.8  # Some invalid refs
            assert any("invalid WSP numbers" in r for r in reasons)
        finally:
            path.unlink()

    def test_file_not_found_zero_score(self):
        score, reasons = _eval_wsp_compliance(Path("/nonexistent/SKILL.md"))
        assert score == 0.0


# ---------------------------------------------------------------------------
# Historical Context
# ---------------------------------------------------------------------------


class TestHistoricalContext:

    def test_context_fidelity_used(self, valid_skill_content):
        path = _write_temp_skill(valid_skill_content)
        try:
            result = eval_skill_config(path, context={"historical_fidelity": 0.95})
            assert result.historical_fidelity == 0.95
        finally:
            path.unlink()

    def test_context_quality_used(self, valid_skill_content):
        path = _write_temp_skill(valid_skill_content)
        try:
            result = eval_skill_config(path, context={"historical_quality": 0.85})
            assert result.historical_quality == 0.85
        finally:
            path.unlink()

    def test_default_fidelity_05(self, valid_skill_content):
        path = _write_temp_skill(valid_skill_content)
        try:
            result = eval_skill_config(path, context={})
            assert result.historical_fidelity == 0.5
            assert any("using default 0.5" in r for r in result.reasons)
        finally:
            path.unlink()

    def test_default_quality_05(self, valid_skill_content):
        path = _write_temp_skill(valid_skill_content)
        try:
            result = eval_skill_config(path, context={})
            assert result.historical_quality == 0.5
        finally:
            path.unlink()

    def test_context_clamped_to_range(self, valid_skill_content):
        path = _write_temp_skill(valid_skill_content)
        try:
            result = eval_skill_config(
                path,
                context={"historical_fidelity": 1.5, "historical_quality": -0.5},
            )
            assert result.historical_fidelity == 1.0  # Clamped
            assert result.historical_quality == 0.0  # Clamped
        finally:
            path.unlink()

    def test_full_context_high_score(self, valid_skill_content):
        path = _write_temp_skill(valid_skill_content)
        try:
            result = eval_skill_config(
                path,
                context={"historical_fidelity": 0.95, "historical_quality": 0.90},
            )
            # Good config + good WSP + high historical = high total
            assert result.total_score > 0.7
        finally:
            path.unlink()


# ---------------------------------------------------------------------------
# Score Range and Determinism
# ---------------------------------------------------------------------------


class TestScoreRange:

    def test_total_score_in_range(self, valid_skill_content):
        path = _write_temp_skill(valid_skill_content)
        try:
            result = eval_skill_config(path)
            assert 0.0 <= result.total_score <= 1.0
            assert 0.0 <= result.config_validity <= 1.0
            assert 0.0 <= result.wsp_compliance <= 1.0
            assert 0.0 <= result.historical_fidelity <= 1.0
            assert 0.0 <= result.historical_quality <= 1.0
        finally:
            path.unlink()

    def test_broken_config_low_score(self, malformed_skill_content):
        path = _write_temp_skill(malformed_skill_content)
        try:
            result = eval_skill_config(path)
            assert result.total_score < 0.5  # Low due to broken config
        finally:
            path.unlink()

    def test_clamp_function(self):
        assert _clamp(1.5) == 1.0
        assert _clamp(-0.5) == 0.0
        assert _clamp(0.5) == 0.5
        assert _clamp(0.0) == 0.0
        assert _clamp(1.0) == 1.0


class TestDeterminism:

    def test_same_input_same_output(self, valid_skill_content):
        path = _write_temp_skill(valid_skill_content)
        try:
            context = {"historical_fidelity": 0.8, "historical_quality": 0.75}
            result1 = eval_skill_config(path, context=context)
            result2 = eval_skill_config(path, context=context)
            assert result1.total_score == result2.total_score
            assert result1.config_validity == result2.config_validity
            assert result1.wsp_compliance == result2.wsp_compliance
        finally:
            path.unlink()

    def test_different_context_different_score(self, valid_skill_content):
        path = _write_temp_skill(valid_skill_content)
        try:
            result_low = eval_skill_config(
                path,
                context={"historical_fidelity": 0.2, "historical_quality": 0.2},
            )
            result_high = eval_skill_config(
                path,
                context={"historical_fidelity": 0.95, "historical_quality": 0.95},
            )
            assert result_high.total_score > result_low.total_score
        finally:
            path.unlink()


# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------


class TestWeights:

    def test_default_weights_sum_to_one(self):
        assert abs(sum(WEIGHTS.values()) - 1.0) < 0.001

    def test_custom_weights_used(self, valid_skill_content):
        path = _write_temp_skill(valid_skill_content)
        try:
            # Heavily weight historical_fidelity
            custom_weights = {
                "config_validity": 0.1,
                "wsp_compliance": 0.1,
                "historical_fidelity": 0.7,
                "historical_quality": 0.1,
            }
            result = eval_skill_config(
                path,
                context={"historical_fidelity": 1.0, "historical_quality": 0.0},
                weights=custom_weights,
            )
            # With fidelity=1.0 and weight=0.7, should be high
            assert result.total_score > 0.7
        finally:
            path.unlink()

    def test_validate_weights_valid(self):
        errors = validate_weights(WEIGHTS)
        assert errors == []

    def test_validate_weights_wrong_keys(self):
        bad = {"foo": 0.5, "bar": 0.5}
        errors = validate_weights(bad)
        assert len(errors) > 0
        assert any("keys" in e for e in errors)

    def test_validate_weights_wrong_sum(self):
        bad = {
            "config_validity": 0.5,
            "wsp_compliance": 0.5,
            "historical_fidelity": 0.5,
            "historical_quality": 0.5,
        }
        errors = validate_weights(bad)
        assert any("sum to 1.0" in e for e in errors)

    def test_validate_weights_negative(self):
        bad = {
            "config_validity": -0.1,
            "wsp_compliance": 0.4,
            "historical_fidelity": 0.4,
            "historical_quality": 0.3,
        }
        errors = validate_weights(bad)
        assert any("non-negative" in e for e in errors)


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------


class TestConvenience:

    def test_quick_score_returns_float(self, valid_skill_content):
        path = _write_temp_skill(valid_skill_content)
        try:
            score = quick_score(path)
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0
        finally:
            path.unlink()


# ---------------------------------------------------------------------------
# Frontmatter Extraction
# ---------------------------------------------------------------------------


class TestFrontmatterExtraction:

    def test_extract_valid_frontmatter(self):
        content = "---\nname: test\n---\n# Body"
        fm = _extract_frontmatter(content)
        assert fm == "name: test"

    def test_no_frontmatter_returns_none(self):
        content = "# Just markdown"
        fm = _extract_frontmatter(content)
        assert fm is None

    def test_unclosed_frontmatter_returns_none(self):
        content = "---\nname: test\n# No closing"
        fm = _extract_frontmatter(content)
        assert fm is None
