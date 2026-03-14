"""OpenClaw conversation provider chain helpers."""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger("openclaw_dae")


def try_ironclaw_conversation(
    dae: Any,
    user_msg: str,
    system_prompt: str,
) -> Optional[str]:
    """Try IronClaw OpenAI-compatible gateway for conversational reply."""
    try:
        from .ironclaw_gateway_client import IronClawGatewayClient

        client = IronClawGatewayClient()
        content = client.chat_completion(
            user_message=user_msg,
            system_prompt=system_prompt,
            max_tokens=80,
            temperature=0.7,
        )
        if not content:
            return None
        content = dae._trim_self_dialogue(content)
        if not content or len(content) <= 3:
            return None
        logger.info(
            "[OPENCLAW-DAE] Conversation via IronClaw (%s): %d chars",
            client.config.model,
            len(content),
        )
        return dae._ensure_conversation_identity(content)
    except Exception as exc:
        logger.debug("[OPENCLAW-DAE] IronClaw unavailable: %s", exc)
        return None


def try_preferred_external_conversation(
    dae: Any,
    user_msg: str,
    system_prompt: str,
) -> Optional[str]:
    """Try operator-selected external provider/model for conversation."""
    provider_name = (dae._preferred_external_provider or "").strip().lower()
    model_name = (dae._preferred_external_model or "").strip().lower()
    if not provider_name or not model_name:
        dae._mark_preferred_external_status("not_selected", "provider_or_model_empty")
        return None
    if not dae._allow_external_llm:
        dae._mark_preferred_external_status(
            "blocked",
            "external_llm_disabled_by_key_isolation",
        )
        return None

    try:
        from modules.ai_intelligence.ai_gateway.src.ai_gateway import AIGateway

        gateway = AIGateway()
        provider = gateway.providers.get(provider_name)
        if provider is None:
            dae._mark_preferred_external_status("blocked", "provider_not_registered")
            return None
        if not provider.api_key:
            dae._mark_preferred_external_status("blocked", "provider_key_missing")
            return None

        provider.models["quick"] = model_name
        prompt = f"{system_prompt}\n\nUser: {user_msg}"
        content = gateway._call_provider(provider, prompt, "quick")
        content = dae._trim_self_dialogue(content)
        if not content or len(content) <= 3:
            dae._mark_preferred_external_status("failed", "empty_or_short_response")
            return None
        dae._mark_preferred_external_status("success", "response_returned")
        logger.info(
            "[OPENCLAW-DAE] Conversation via preferred external model (%s/%s): %d chars",
            provider_name,
            model_name,
            len(content),
        )
        return dae._ensure_conversation_identity(content)
    except Exception as exc:
        detail = f"{type(exc).__name__}:{str(exc)[:120]}"
        dae._mark_preferred_external_status("failed", detail)
        logger.warning("[OPENCLAW-DAE] Preferred external model unavailable: %s", detail)
        return None
