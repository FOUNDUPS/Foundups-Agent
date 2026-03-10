"""OpenClaw DAEmon action-ledger helpers."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict

logger = logging.getLogger("openclaw_dae")


def record_social_response(dae: Any, source: str, response_text: str) -> None:
    """Capture the latest social adapter response for daemon diagnostics."""
    response_text = str(response_text or "").strip()
    payload: Dict[str, Any] = {}
    json_start = response_text.find("{")
    if json_start != -1:
        try:
            payload = json.loads(response_text[json_start:])
        except Exception:
            payload = {}

    skill = "none"
    skill_match = re.search(r"Skill executed:\s*([^\r\n]+)", response_text)
    if skill_match:
        skill = skill_match.group(1).strip() or "none"
    elif payload.get("skill"):
        skill = str(payload.get("skill")).strip() or "none"

    action = str(payload.get("action", "")).strip() or "none"
    success = payload.get("success")

    preview = ""
    if isinstance(payload.get("reply_text"), str) and payload.get("reply_text"):
        preview = str(payload.get("reply_text"))
    elif isinstance(payload.get("draft"), dict) and payload["draft"].get("reply_text"):
        preview = str(payload["draft"]["reply_text"])
    elif isinstance(payload.get("planned_replies"), list) and payload["planned_replies"]:
        first_plan = payload["planned_replies"][0] or {}
        preview = str(first_plan.get("reply_text", "") or "")
    if not preview:
        preview = " ".join(response_text.split())
    preview = (" ".join(preview.split())[:160] or "none")

    dae._last_social_response_source = (source or "unknown").strip() or "unknown"
    dae._last_social_response_action = action
    dae._last_social_response_skill = skill
    dae._last_social_response_success = (
        "true" if success is True else "false" if success is False else "unknown"
    )
    dae._last_social_response_preview = preview
    dae._last_social_response_at = time.time()

    logger.info(
        "[OPENCLAW-DAE] Social response captured | source=%s action=%s skill=%s success=%s",
        dae._last_social_response_source,
        dae._last_social_response_action,
        dae._last_social_response_skill,
        dae._last_social_response_success,
    )


def report_daemon_action(
    dae: Any,
    action_type: str,
    target: str = "",
    result: str = "",
    **details: Any,
) -> None:
    """Emit structured OpenClaw actions to the central DAEmon when available."""
    if not getattr(dae, "_central_adapter", None):
        return
    try:
        compact_details = {
            key: value
            for key, value in details.items()
            if value is not None and value != ""
        }
        dae._central_adapter.report_action(
            action_type=action_type,
            target=target,
            result=result,
            details=compact_details or None,
        )
    except Exception:
        pass
