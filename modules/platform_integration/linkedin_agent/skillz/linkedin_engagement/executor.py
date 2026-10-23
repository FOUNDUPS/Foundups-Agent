#!/usr/bin/env python3
"""
LinkedIn Engagement Executor — WRE Skill Bridge

Bridges WRE execute_skill() calls to the existing linkedin_social_adapter,
allowing LinkedIn actions to flow through the ReAct reasoning loop and
feed outcomes into PatternMemory for self-improvement.

WSP Compliance: WSP 42, WSP 50, WSP 77, WSP 96
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Supported actions (mirrors linkedin_social_adapter.SUPPORTED_ACTIONS)
SUPPORTED_ACTIONS = {
    "navigate_feed",
    "navigate_profile",
    "read_feed",
    "like_post",
    "reply_post",
    "like_reply",
    "scam_reply",
    "scam_scan",
    "scam_scan_reply",
    "engagement_session",
    "connect",
    "digital_twin",
    "group_post",
}

# Actions that are read-only (no mutation risk)
READ_ONLY_ACTIONS = {"navigate_feed", "navigate_profile", "read_feed", "scam_scan"}


def execute(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    WRE skill executor entry point.

    Called by WREMasterOrchestrator.execute_skill() when routing to this skill.

    Args:
        task: WRE task dict with at minimum:
            - action: str — LinkedIn action name
            - params: dict — Action parameters (optional, default empty)
            - dry_run: bool — Safety gate (optional, default True)
            - sender: str — Who initiated (optional, default "@012")

    Returns:
        Structured result dict for PatternMemory storage.
    """
    action = task.get("action", "").strip().lower()
    params = dict(task.get("params", {}))
    sender = task.get("sender", "@012")
    dry_run = task.get("dry_run", True)

    # --- Validate action ---
    error = _action_validation_error(action)
    if error is not None:
        return error

    # --- Safety gate: enforce dry_run for write actions ---
    if action not in READ_ONLY_ACTIONS and dry_run:
        params["dry_run"] = "true"
    elif not dry_run:
        params["dry_run"] = "false"

    return _execute_adapter(action, params, sender)


def _action_validation_error(action: str) -> Optional[Dict[str, Any]]:
    """Preserve the existing unsupported-action response contract."""
    if not action:
        return {
            "success": False,
            "skill": "linkedin_engagement",
            "error": "no_action_specified",
            "supported": sorted(SUPPORTED_ACTIONS),
        }

    if action not in SUPPORTED_ACTIONS:
        return {
            "success": False,
            "skill": "linkedin_engagement",
            "action": action,
            "error": "unsupported_action",
            "supported": sorted(SUPPORTED_ACTIONS),
        }
    return None


def _execute_adapter(action: str, params: Dict[str, Any], sender: str) -> Dict[str, Any]:
    """Keep timing, result projection and exception envelopes around dispatch."""
    t0 = time.monotonic()
    try:
        from modules.communication.moltbot_bridge.src.linkedin_social_adapter import (
            execute_linkedin_action,
        )

        # execute_linkedin_action is async
        result = _run_async(execute_linkedin_action(action, params))

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return _adapter_result(action, params, sender, result, elapsed_ms)

    except ImportError as exc:
        logger.error("[WRE-SKILL] linkedin_engagement adapter import failed: %s", exc)
        return {
            "success": False,
            "skill": "linkedin_engagement",
            "action": action,
            "error": "adapter_import_failed",
            "detail": str(exc),
        }
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        logger.error("[WRE-SKILL] linkedin_engagement execution error: %s", exc)
        return {
            "success": False,
            "skill": "linkedin_engagement",
            "action": action,
            "error": "execution_failed",
            "detail": str(exc)[:500],
            "execution_time_ms": elapsed_ms,
        }


def _adapter_result(action, params, sender, result, elapsed_ms) -> Dict[str, Any]:
    """Project the adapter result without treating a preview as a posted receipt."""
    success = bool(result.get("success", False)) if isinstance(result, dict) else False
    logger.info(
        "[WRE-SKILL] linkedin_engagement | action=%s success=%s elapsed=%dms sender=%s",
        action,
        success,
        elapsed_ms,
        sender,
    )
    return {
        "success": success,
        "skill": "linkedin_engagement",
        "action": action,
        "params": params,
        "result": result,
        "execution_time_ms": elapsed_ms,
        "sender": sender,
    }


def _run_async(coro):
    """Run an async coroutine from synchronous context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already in an async context — use nest_asyncio or Thread fallback
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=120)
    else:
        return asyncio.run(coro)


def get_skill_info() -> Dict[str, Any]:
    """Return skill metadata for WRE discovery integration."""
    return {
        "name": "linkedin_engagement",
        "version": "1.0.0",
        "domain": "social",
        "actions": sorted(SUPPORTED_ACTIONS),
        "read_only_actions": sorted(READ_ONLY_ACTIONS),
        "default_dry_run": True,
        "agents": ["qwen"],
        "intent_type": "DECISION",
    }
