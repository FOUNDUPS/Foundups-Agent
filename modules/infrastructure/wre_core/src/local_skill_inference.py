"""Fail-closed local inference adapter for generic WRE Skillz execution."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping


def validate_local_proposal_config(mode: str, profile: Mapping[str, str] | None) -> dict[str, str] | None:
    """Copy trusted optional configuration; this is not runtime admission."""
    if type(mode) is not str or mode not in ("raw", "native_chat"):
        raise ValueError("Invalid local proposal configuration")
    if mode == "raw":
        if profile is not None:
            raise ValueError("Invalid local proposal configuration")
        return None
    if not isinstance(profile, Mapping) or set(profile) != {"runtime_version", "template_sha256"}:
        raise ValueError("Invalid local proposal configuration")
    copied = dict(profile)
    if (type(copied["runtime_version"]) is not str or copied["runtime_version"] != "0.3.20"
            or type(copied["template_sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", copied["template_sha256"]) is None):
        raise ValueError("Invalid local proposal configuration")
    return copied


def execute_local_skill_inference(
    *,
    skill_content: str,
    input_context: Mapping[str, Any],
    agent: str,
    proposal_mode: str = "raw",
    native_chat_profile: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Generate a local proposal; model text alone is never effect success."""
    if agent.lower() != "qwen":
        return _failure("unsupported_local_agent")
    engine = None
    try:
        profile = validate_local_proposal_config(proposal_mode, native_chat_profile)
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
        if profile is not None:
            response = engine.generate_chat_response(
                prompt=_build_prompt(skill_content, input_context),
                system_prompt="You are drafting a WRE proposal. Do not claim effects.",
                **profile,
            )
        else:
            if not engine.initialize():
                return _failure("local_model_unavailable")
            response = engine.generate_response(
                prompt=_build_prompt(skill_content, input_context),
                system_prompt="You are drafting a WRE proposal. Do not claim effects.",
            )
    except Exception:
        return _failure("local_model_unavailable")
    finally:
        if engine is not None:
            try:
                engine.close()
            except Exception:
                # A proposal is unavailable when its owned resource cleanup fails.
                response = None

    if not _is_safe_proposal(response):
        return _failure("local_model_unavailable")
    return _proposal_result(response)


def _proposal_result(response: str) -> dict[str, Any]:
    """Keep generated text quarantined after successful owned cleanup."""
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
        "Prepare the proposal requested by this skill:\n\n"
        f"{skill_content}\n\n"
        "Input Context:\n"
        f"{json.dumps({k: v for k, v in input_context.items() if k != 'parent_continuity_context'}, indent=2)}\n\n"
        "Follow the skill's required output format for the proposal. "
        "Do not claim that repository, shell, Git, "
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
