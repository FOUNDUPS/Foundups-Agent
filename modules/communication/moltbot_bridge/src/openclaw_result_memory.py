"""OpenClaw execution validation and memory-storage helpers."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, List

logger = logging.getLogger("openclaw_dae")


def validate_and_remember(
    dae: Any,
    plan: Any,
    response_text: str,
    execution_time_ms: int,
) -> Any:
    """Validate execution output and persist learning outcome."""
    wsp_violations: List[str] = []

    if not response_text or len(response_text.strip()) == 0:
        wsp_violations.append("WSP-50: Empty response generated")
        response_text = "I was unable to generate a response. Please try again."

    secret_patterns = ["AIza", "sk-", "oauth_token", "Bearer ey"]
    for pattern in secret_patterns:
        if pattern in response_text:
            wsp_violations.append(
                f"WSP-SECURITY: Response contains '{pattern}' pattern"
            )
            response_text = "[REDACTED - security filter triggered]"
            break

    fidelity = 1.0 if not wsp_violations else 0.5

    learning_stored = False
    if dae.wre and dae.wre.sqlite_memory:
        try:
            from modules.infrastructure.wre_core.src.pattern_memory import SkillOutcome

            outcome = SkillOutcome(
                execution_id=f"openclaw-{uuid.uuid4().hex[:12]}",
                skill_name=f"openclaw_{plan.intent.category.value}",
                agent="openclaw_dae",
                timestamp=datetime.now().isoformat(),
                input_context=json.dumps(
                    {
                        "message": plan.intent.raw_message[:200],
                        "channel": plan.intent.channel,
                        "category": plan.intent.category.value,
                    }
                ),
                output_result=json.dumps(
                    {
                        "response_length": len(response_text),
                        "response_preview": " ".join(response_text.split())[:160],
                        "route": plan.route,
                        "tier": plan.permission_level.value,
                        "social_source": getattr(
                            dae, "_last_social_response_source", "unknown"
                        ),
                        "social_action": getattr(
                            dae, "_last_social_response_action", "unknown"
                        ),
                        "social_skill": getattr(
                            dae, "_last_social_response_skill", "unknown"
                        ),
                    }
                ),
                success=len(wsp_violations) == 0,
                pattern_fidelity=fidelity,
                outcome_quality=0.9 if not wsp_violations else 0.5,
                execution_time_ms=execution_time_ms,
                step_count=len(plan.steps),
                notes=(
                    f"OpenClaw DAE | {plan.intent.channel} | "
                    f"{plan.intent.category.value}"
                ),
            )
            dae.wre.sqlite_memory.store_outcome(outcome)
            learning_stored = True
        except Exception as exc:
            logger.warning("[OPENCLAW-DAE] Failed to store outcome: %s", exc)

    result = dae.ExecutionResult(
        plan=plan,
        success=len(wsp_violations) == 0,
        response_text=response_text,
        execution_time_ms=execution_time_ms,
        pattern_fidelity=fidelity,
        wsp_violations=wsp_violations,
        learning_stored=learning_stored,
    )

    logger.info(
        "[OPENCLAW-DAE] Result: success=%s fidelity=%.2f time=%dms violations=%d "
        "learned=%s",
        result.success,
        fidelity,
        execution_time_ms,
        len(wsp_violations),
        learning_stored,
    )
    return result
