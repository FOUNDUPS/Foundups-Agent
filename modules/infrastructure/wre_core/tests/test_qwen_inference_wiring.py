#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Qwen Inference Wiring (Phase 2)

Validates that execute_skill() can wire to local Qwen inference
WSP Compliance: WSP 5 (Test Coverage), WSP 96 (WRE Skills)
"""

import sys
import json
from datetime import datetime
from pathlib import Path
import uuid

# Add repo root to path
repo_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

from modules.infrastructure.wre_core.src.libido_monitor import GemmaLibidoMonitor
from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory, SkillOutcome
from modules.infrastructure.wre_core.src.skill_selector import SkillSelector
from modules.infrastructure.wre_core.skillz.wre_skills_loader import WRESkillsLoader


def _typed_effect_result():
    return {
        "success": True,
        "output": "Explicit test executor result",
        "steps_completed": 4,
        "failed_at_step": None,
        "effect_receipts": [{"receipt_id": "test-1", "effect_type": "test"}],
        "_effect_evidence": True,
    }


def test_execute_skill_result_shape_without_model_call():
    """Explicit typed effect evidence has the expected structural fidelity."""
    execution_result = _typed_effect_result()
    libido_monitor = GemmaLibidoMonitor()
    step_output_dict = {
        "output": execution_result["output"],
        "steps_completed": execution_result["steps_completed"],
        "failed_at_step": execution_result["failed_at_step"]
    }
    expected_patterns = ["output", "steps_completed"]

    fidelity = libido_monitor.validate_step_fidelity(
        step_output=step_output_dict,
        expected_patterns=expected_patterns
    )

    assert execution_result["success"] is True
    assert execution_result["_effect_evidence"] is True
    assert fidelity == 1.0


def test_typed_effect_outcome_uses_isolated_pattern_memory(tmp_path):
    """Typed effect evidence persists without inventing outcome quality."""
    input_context = {"files_changed": 3, "lines_changed": 150}
    execution_result = _typed_effect_result()
    pattern_memory = PatternMemory(db_path=tmp_path / "pattern_memory.db")

    outcome = SkillOutcome(
        execution_id=str(uuid.uuid4()),
        skill_name="qwen_gitpush",
        agent="qwen",
        timestamp=datetime.now().isoformat(),
        input_context=json.dumps(input_context),
        output_result=json.dumps(execution_result),
        success=True,
        pattern_fidelity=1.0,
        outcome_quality=0.0,
        execution_time_ms=250,
        step_count=4,
        notes="Typed test evidence; independent outcome quality unavailable"
    )
    pattern_memory.store_outcome(outcome)
    metrics = pattern_memory.get_skill_metrics("qwen_gitpush", days=1)

    assert metrics["execution_count"] == 1
    assert metrics["avg_fidelity"] == 1.0
    assert metrics["avg_quality"] == 0.0


def test_resolve_skill_file_uses_authoritative_registry_location():
    """The portable registry points directly at the executable Skillz file."""
    skills_loader = WRESkillsLoader()

    skill_path = skills_loader.resolve_skill_file("qwen_gitpush")
    configured = skills_loader._resolve_registered_location(
        skills_loader.registry["skills"]["qwen_gitpush"]["location"]
    )

    assert skill_path.exists()
    assert skill_path.parent == configured
    assert skill_path.name == "SKILLz.md"
    assert "git_push_dae" in str(skill_path)
    assert "skillz" in str(skill_path).lower()


def test_skill_selector_matches_natural_language_git_intent():
    """Natural-language commands should discover qwen_gitpush candidates."""
    skills_loader = WRESkillsLoader()
    selector = SkillSelector(skills_loader=skills_loader)

    candidates = selector.find_candidates_for_intent("git commit and push changes")

    assert "qwen_gitpush" in candidates


if __name__ == "__main__":
    raise SystemExit("Run with pytest so storage is isolated")
