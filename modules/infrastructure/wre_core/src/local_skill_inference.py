"""Fail-closed local inference adapter for generic WRE Skillz execution."""

from __future__ import annotations

import json
from typing import Any, Mapping


def execute_local_skill_inference(
    *,
    skill_content: str,
    input_context: Mapping[str, Any],
    agent: str,
) -> dict[str, Any]:
    """Generate a local proposal; model text alone is never effect success."""
    if agent.lower() != "qwen":
        return _failure("unsupported_local_agent")
    try:
        from holo_index.qwen_advisor.llm_engine import QwenInferenceEngine
        from modules.infrastructure.shared_utilities.local_model_selection import (
            resolve_code_model_path,
        )
        engine = QwenInferenceEngine(
            model_path=resolve_code_model_path(),
            max_tokens=512,
            temperature=0.2,
            context_length=2048,
        )
        if not engine.initialize():
            return _failure("local_model_unavailable")
        response = engine.generate_response(
            prompt=_build_prompt(skill_content, input_context),
            system_prompt="You are drafting a WRE proposal. Do not claim effects.",
        )
    except Exception:
        return _failure("local_model_unavailable")

    if not _is_safe_proposal(response):
        return _failure("local_model_unavailable")
    return {
        "success": False,
        "output": "",
        "proposal": response.strip(),
        "steps_completed": 0,
        "failed_at_step": 1,
        "error": "Local model output is an unverified proposal, not effect evidence",
        "error_code": "unverified_model_proposal",
        "_effect_evidence": False,
    }


def _is_safe_proposal(response: Any) -> bool:
    """Reject engine sentinel/error strings that can contain raw exceptions."""
    if not isinstance(response, str) or not response.strip():
        return False
    normalized = response.lstrip().lower()
    return not normalized.startswith(("error:", "[error", "exception:"))


def _build_prompt(skill_content: str, input_context: Mapping[str, Any]) -> str:
    return (
        "Execute this skill step-by-step:\n\n"
        f"{skill_content}\n\n"
        "Input Context:\n"
        f"{json.dumps(dict(input_context), indent=2)}\n\n"
        "Draft a structured proposal. Do not claim that repository, shell, Git, "
        "network, or external effects occurred."
    )


def _failure(error_code: str) -> dict[str, Any]:
    return {
        "success": False,
        "output": "",
        "proposal": "",
        "steps_completed": 0,
        "failed_at_step": 1,
        "error": "Local skill inference is unavailable or unsupported",
        "error_code": error_code,
        "_effect_evidence": False,
    }
