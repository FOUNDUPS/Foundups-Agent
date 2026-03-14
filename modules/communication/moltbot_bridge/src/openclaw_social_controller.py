"""OpenClaw social-control routing helpers.

WSP 73/97 boundary:
- OpenClaw owns natural-language mission control and execution-plane routing.
- Social/LinkedIn/X adapters remain child execution domains.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .openclaw_dae import OpenClawIntent


logger = logging.getLogger("openclaw_dae")


async def execute_social(dae: Any, intent: "OpenClawIntent") -> str:
    """Route SOCIAL intent to deterministic social adapters."""
    try:
        from .linkedin_loop_adapter import handle_linkedin_loop_intent

        linkedin_loop_response = await handle_linkedin_loop_intent(
            intent.raw_message,
            intent.sender,
        )
        if linkedin_loop_response:
            dae._record_social_response("linkedin_loop", linkedin_loop_response)
            return linkedin_loop_response
    except Exception as exc:
        logger.warning("[OPENCLAW-DAE] LinkedIn loop adapter unavailable: %s", exc)

    try:
        from .social_campaign_adapter import handle_social_campaign_intent

        campaign_response = await handle_social_campaign_intent(
            intent.raw_message,
            intent.sender,
        )
        if campaign_response:
            dae._record_social_response("social_campaign", campaign_response)
            return campaign_response
    except Exception as exc:
        logger.warning("[OPENCLAW-DAE] Social campaign adapter unavailable: %s", exc)

    try:
        from .linkedin_social_adapter import handle_linkedin_social_intent

        linkedin_response = await handle_linkedin_social_intent(
            intent.raw_message,
            intent.sender,
        )
        if linkedin_response:
            dae._record_social_response("linkedin", linkedin_response)
            return linkedin_response
    except Exception as exc:
        logger.warning("[OPENCLAW-DAE] LinkedIn social adapter unavailable: %s", exc)

    try:
        from .x_social_adapter import handle_x_social_intent

        x_response = await handle_x_social_intent(
            intent.raw_message,
            intent.sender,
        )
        if x_response:
            dae._record_social_response("x", x_response)
            return x_response
    except Exception as exc:
        logger.warning("[OPENCLAW-DAE] X social adapter unavailable: %s", exc)

    return (
        f"Social engagement request on {intent.channel}: "
        f"{intent.extracted_task}\n"
        "Routing to communication layer... "
        "(Digital Twin engagement via livechat/video_comments)\n"
        "Tips: "
        "`linkedin action <action> key=value`, "
        "`x action <action> key=value`, or "
        "`social campaign <campaign_name> key=value`."
    )


async def try_conversation_social_control(
    dae: Any, intent: "OpenClawIntent"
) -> Optional[str]:
    """
    Allow natural-language social controls from direct conversation channels.

    This keeps operator phrasing ergonomic while still routing through the same
    deterministic social adapters.
    """
    try:
        from .linkedin_loop_adapter import handle_linkedin_loop_intent

        linkedin_loop_response = await handle_linkedin_loop_intent(
            intent.raw_message,
            intent.sender,
        )
        if linkedin_loop_response:
            dae._record_social_response("linkedin_loop", linkedin_loop_response)
            dae._mark_conversation_engine(
                "linkedin_loop_control",
                "deterministic_conversation_route",
            )
            return linkedin_loop_response
    except Exception as exc:
        logger.warning("[OPENCLAW-DAE] LinkedIn loop control unavailable: %s", exc)

    try:
        from .linkedin_social_adapter import handle_linkedin_social_intent

        linkedin_response = await handle_linkedin_social_intent(
            intent.raw_message,
            intent.sender,
        )
        if linkedin_response:
            dae._record_social_response("linkedin", linkedin_response)
            dae._mark_conversation_engine(
                "linkedin_social_control",
                "deterministic_conversation_route",
            )
            return linkedin_response
    except Exception as exc:
        logger.warning("[OPENCLAW-DAE] LinkedIn conversation control unavailable: %s", exc)
    return None
