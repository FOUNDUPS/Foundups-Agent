"""OpenClaw main autonomy loop orchestration."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("openclaw_dae")


async def process_message(
    dae: Any,
    message: str,
    sender: str,
    channel: str,
    session_key: str = "default",
    metadata: Optional[Dict] = None,
) -> str:
    """Run the full OpenClaw autonomy loop for one inbound message."""
    start_time = time.time()
    dae.clear_turn_cancel()

    honeypot = dae.HoneypotDefense

    if honeypot.is_secret_seeking(message):
        response = honeypot.handle_secret_request(message, sender, channel)
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "[OPENCLAW-DAE] [HONEYPOT] Canary response sent | sender=%s time=%dms",
            sender,
            elapsed_ms,
        )
        return response

    containment = dae._check_containment(sender, channel)
    if containment:
        logger.warning(
            "[DAEMON][OPENCLAW-CONTAINMENT] event=containment_active sender=%s "
            "channel=%s action=%s expires_at=%.0f",
            sender,
            channel,
            containment.get("action"),
            containment.get("expires_at", 0),
        )
        if containment.get("action") in ("mute_sender", "mute_channel"):
            return (
                "Your access is temporarily restricted due to security policy. "
                f"Reason: {containment.get('reason', 'security incident')}. "
                "Please try again later."
            )

    if channel == "discord" and honeypot.is_code_modify_attempt(message):
        response = honeypot.generate_code_modify_deflection(message, sender, channel)
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "[OPENCLAW-DAE] [LAW-3] Code modify deflected | sender=%s time=%dms",
            sender,
            elapsed_ms,
        )
        return response

    if dae._is_turn_cancelled("pre_classify"):
        return dae._turn_cancelled_response()

    intent = dae.classify_intent(
        message=message,
        sender=sender,
        channel=channel,
        session_key=session_key,
        metadata=metadata,
    )
    dae._apply_runtime_profile_policy(intent)

    if dae._central_adapter:
        try:
            dae._central_adapter.report_message_in(
                source=f"{sender}@{channel}",
                summary=f"intent={intent.category.value} conf={intent.confidence:.2f}",
            )
        except Exception:
            pass

    dae._report_daemon_action(
        "intent_classified",
        target=intent.category.value,
        result=f"domain={intent.target_domain or 'none'} conf={intent.confidence:.2f}",
        sender=sender,
        channel=channel,
        commander=intent.is_authorized_commander,
        extracted_task=intent.extracted_task or "",
    )

    if intent.category in (
        dae.IntentCategory.COMMAND,
        dae.IntentCategory.SYSTEM,
        dae.IntentCategory.SCHEDULE,
        dae.IntentCategory.SOCIAL,
        dae.IntentCategory.AUTOMATION,
        dae.IntentCategory.FOUNDUP,
        dae.IntentCategory.RESEARCH,
    ):
        if dae._is_turn_cancelled("pre_skill_safety"):
            return dae._turn_cancelled_response()
        if not dae._ensure_skill_safety():
            logger.warning(
                "[OPENCLAW-DAE] Skill safety gate blocked %s route: %s",
                intent.category.value,
                dae._skill_scan_message,
            )
            dae._report_daemon_action(
                "skill_safety_gate",
                target=intent.category.value,
                result="blocked",
                reason=dae._skill_scan_message,
            )
            intent.category = dae.IntentCategory.CONVERSATION
            intent.target_domain = "digital_twin"
            intent.metadata["skill_safety_gate"] = dae._skill_scan_message
        else:
            dae._report_daemon_action(
                "skill_safety_gate",
                target=intent.category.value,
                result="passed",
                policy=dae._skill_scan_message,
            )

    if dae._is_turn_cancelled("pre_preflight"):
        return dae._turn_cancelled_response()

    preflight_ok = dae._wsp_preflight(intent)
    dae._report_daemon_action(
        "wsp_preflight",
        target=intent.category.value,
        result="passed" if preflight_ok else "downgraded",
        target_domain=intent.target_domain or "none",
    )
    if not preflight_ok:
        intent.category = dae.IntentCategory.CONVERSATION
        intent.target_domain = "digital_twin"

    if dae._is_turn_cancelled("pre_permission_gate"):
        return dae._turn_cancelled_response()

    tier = dae._resolve_autonomy_tier(intent)
    gate_ok = dae._check_permission_gate(intent, tier)
    dae._report_daemon_action(
        "permission_gate",
        target=tier.value,
        result="granted" if gate_ok else "downgraded",
        category=intent.category.value,
        sender=sender,
    )
    if not gate_ok:
        tier = dae.AutonomyTier.ADVISORY
        intent.category = dae.IntentCategory.CONVERSATION
        intent.target_domain = "digital_twin"

    if dae._is_turn_cancelled("pre_plan"):
        return dae._turn_cancelled_response()

    plan = dae._plan_execution(intent, tier)
    dae._report_daemon_action(
        "plan_built",
        target=plan.route,
        result=f"tier={plan.permission_level.value} steps={len(plan.steps)}",
        wsp_preflight=plan.wsp_preflight_passed,
        estimated_tokens=plan.estimated_tokens,
    )

    try:
        response_text = await dae._execute_plan(plan)
        dae._report_daemon_action(
            "plan_executed",
            target=plan.route,
            result="completed",
            category=plan.intent.category.value,
        )
        if dae._is_turn_cancelled("post_execute_plan"):
            response_text = dae._turn_cancelled_response()
    except Exception as exc:
        logger.error("[OPENCLAW-DAE] Execution error: %s", exc)
        dae._report_daemon_action(
            "plan_executed",
            target=plan.route,
            result="error",
            error=str(exc),
            category=plan.intent.category.value,
        )
        if dae._is_turn_cancelled("execute_exception"):
            response_text = dae._turn_cancelled_response()
        else:
            response_text = f"An error occurred during processing: {exc}"

    elapsed_ms = int((time.time() - start_time) * 1000)
    if dae._is_turn_cancelled("pre_validate"):
        return dae._turn_cancelled_response()

    result = dae._validate_and_remember(plan, response_text, elapsed_ms)
    dae._report_daemon_action(
        "result_validated",
        target=plan.route,
        result="success" if result.success else "failure",
        execution_time_ms=elapsed_ms,
        pattern_fidelity=result.pattern_fidelity,
        learning_stored=result.learning_stored,
        wsp_violations=len(result.wsp_violations),
    )

    if dae._central_adapter:
        try:
            dae._central_adapter.report_message_out(
                dest=f"{sender}@{channel}",
                summary=f"route={plan.route} time={elapsed_ms}ms",
            )
        except Exception:
            pass

    return result.response_text
