"""OpenClaw execution-route helpers after plan resolution."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger("openclaw_dae")


async def execute_plan(dae: Any, plan: Any) -> str:
    """Execute a resolved plan by dispatching to the appropriate route."""
    intent = plan.intent
    route = plan.route

    if route == "holo_index":
        return await execute_query(dae, intent)
    if route == "wre_orchestrator":
        return await execute_command(dae, intent)
    if route == "ai_overseer":
        return execute_monitor(dae, intent)
    if route == "youtube_shorts_scheduler":
        return await execute_schedule(dae, intent)
    if route == "communication":
        return await dae._execute_social(intent)
    if route == "infrastructure":
        return execute_system(dae, intent)
    if route == "auto_moderator_bridge":
        return await execute_automation(dae, intent)
    if route == "fam_adapter":
        return execute_foundup(dae, intent)
    if route == "pqn_research_adapter":
        return execute_research(dae, intent)

    social_control = await dae._try_conversation_social_control(intent)
    if social_control:
        return social_control
    return dae._execute_conversation(intent)


async def execute_query(dae: Any, intent: Any) -> str:
    """Route QUERY to HoloIndex semantic search."""
    if dae._is_token_usage_query(intent.raw_message):
        dae._mark_conversation_engine("token_usage", "deterministic_query_route")
        return dae._build_token_usage_report()

    if dae._is_identity_query(intent.raw_message):
        if dae._wants_full_identity_card(intent.raw_message):
            dae._mark_conversation_engine("identity_card", "deterministic_query_route")
            return dae._build_identity_card()
        dae._mark_conversation_engine("identity_compact", "deterministic_query_route")
        if dae._is_compact_identity_query(intent.raw_message):
            return dae._build_identity_compact_runtime()
        return dae._build_identity_compact()

    try:
        from holo_index.core import HoloIndex

        holo = HoloIndex()
        results = holo.search(intent.extracted_task or intent.raw_message, limit=3)

        code_hits = results.get("code", [])
        wsp_hits = results.get("wsps", [])

        if not code_hits and not wsp_hits:
            return (
                f"No results found for: {intent.extracted_task}\n\n"
                "Try rephrasing or use more specific terms."
            )

        parts = []
        if code_hits:
            parts.append("**Code matches:**")
            for hit in code_hits[:3]:
                path = hit.get("file", "unknown")
                snippet = hit.get("content", "")[:200]
                parts.append(f"  - `{path}`: {snippet}")

        if wsp_hits:
            parts.append("\n**WSP guidance:**")
            for hit in wsp_hits[:2]:
                title = hit.get("title", "WSP")
                content = hit.get("content", "")[:200]
                parts.append(f"  - **{title}**: {content}")

        return "\n".join(parts)
    except ImportError:
        logger.warning("[OPENCLAW-DAE] HoloIndex not available for query")
        return (
            f"Received your query: {intent.raw_message[:100]}\n"
            "HoloIndex is currently offline. Try again shortly."
        )
    except Exception as exc:
        logger.error("[OPENCLAW-DAE] Query execution error: %s", exc)
        return f"Error processing query: {exc}"


async def execute_command(dae: Any, intent: Any) -> str:
    """Route COMMAND to WRE orchestrator with file-specific permission gate."""
    if dae._is_source_modification(intent):
        file_paths = dae._extract_file_paths(intent.raw_message)
        if file_paths and dae.permissions:
            for fpath in file_paths:
                result = dae.permissions.check_permission(
                    agent_id="openclaw",
                    operation="write",
                    file_path=fpath,
                )
                if not result.allowed:
                    logger.warning(
                        "[OPENCLAW-DAE] [COMMAND] Execution blocked: %s denied for %s",
                        result.reason,
                        fpath,
                    )
                    return (
                        f"**Permission Denied** (SOURCE tier gate)\n\n"
                        f"Cannot modify `{fpath}`: {result.reason}\n\n"
                        "File is protected by the allowlist/forbidlist policy. "
                        "Contact @012 to update permissions."
                    )

    follow_wsp_response = await try_execute_follow_wsp(dae, intent)
    if follow_wsp_response:
        return follow_wsp_response

    if dae.wre is None:
        logger.warning(
            "[DAEMON][OPENCLAW-FALLBACK] event=command_fallback sender=%s reason=wre_unavailable",
            intent.sender,
        )
        dae._emit_to_overseer(
            event_type="command_fallback",
            sender=intent.sender,
            channel=intent.channel,
            details={"reason": "wre_unavailable", "task": intent.extracted_task},
        )
        return command_advisory_fallback(dae, intent)

    try:
        result = dae.wre.execute(
            {
                "type": "orchestration",
                "task": intent.extracted_task,
                "source": "openclaw_dae",
                "sender": intent.sender,
                "channel": intent.channel,
                "target_files": dae._extract_file_paths(intent.raw_message),
            }
        )
        return f"Command executed via WRE:\n{result}"
    except Exception as exc:
        logger.error("[OPENCLAW-DAE] Command execution error: %s", exc)
        logger.warning(
            "[DAEMON][OPENCLAW-FALLBACK] event=command_fallback sender=%s reason=wre_error",
            intent.sender,
        )
        dae._emit_to_overseer(
            event_type="command_fallback",
            sender=intent.sender,
            channel=intent.channel,
            details={"reason": "wre_error", "error": str(exc)[:200]},
        )
        return command_advisory_fallback(dae, intent, error=str(exc))


async def try_execute_follow_wsp(dae: Any, intent: Any) -> Optional[str]:
    """Deterministic WSP 97 path for the canonical operator: 'follow wsp'."""
    raw_message = (intent.raw_message or "").strip()
    normalized = re.sub(r"\s+", " ", raw_message.lower())
    if "follow wsp" not in normalized:
        return None

    task_text = re.sub(
        r"^\s*(please\s+)?follow\s+wsp\b[:\-\s]*",
        "",
        raw_message,
        flags=re.IGNORECASE,
    ).strip()
    if not task_text:
        task_text = intent.extracted_task or "general_wsp_execution"

    try:
        from modules.infrastructure.wsp_orchestrator.src.wsp_orchestrator import (
            WSPOrchestrator,
        )

        orchestrator = WSPOrchestrator(dae.repo_root)
        try:
            result = await orchestrator.follow_wsp(task_text)
        finally:
            shutdown = getattr(orchestrator, "shutdown", None)
            if shutdown is not None:
                await shutdown()

        summary = {
            "task": task_text,
            "tasks_completed": result.get("tasks_completed", 0),
            "tasks_failed": result.get("tasks_failed", 0),
            "success": bool(result.get("success", False)),
        }
        gate = result.get("wsp00_gate")
        if isinstance(gate, dict):
            summary["wsp00_gate"] = {
                "gate_passed": bool(gate.get("gate_passed", False)),
                "auto_awaken": bool(gate.get("auto_awaken", False)),
                "attempted_awakening": bool(gate.get("attempted_awakening", False)),
            }

        return (
            "Follow WSP executed via WSP Orchestrator:\n"
            f"{json.dumps(summary, indent=2, ensure_ascii=False)}"
        )
    except Exception as exc:
        logger.error("[OPENCLAW-DAE] Follow WSP execution error: %s", exc)
        return f"Follow WSP execution failed:\n{exc}"


def command_advisory_fallback(
    dae: Any,
    intent: Any,
    error: Optional[str] = None,
) -> str:
    """Deterministic advisory fallback when WRE is unavailable."""
    task = intent.extracted_task or intent.raw_message
    parts = [
        "**Advisory Mode** (WRE unavailable)",
        "",
        f"Command recognized: `{task[:100]}`",
        "",
        "I cannot execute this command automatically right now.",
        "Here are your options:",
        "",
        "1. **CLI execution**: Run manually via the main menu (`python main.py`)",
        "2. **Retry later**: WRE may become available after system restart",
        "3. **Query mode**: Ask me to explain what this command does instead",
    ]
    if error:
        parts.append("")
        parts.append(f"**Error detail**: {error[:200]}")

    logger.info(
        "[OPENCLAW-DAE] [COMMAND] Advisory fallback returned for: %s",
        task[:50],
    )
    return "\n".join(parts)


def execute_monitor(dae: Any, intent: Any) -> str:
    """Route MONITOR to AI Overseer status."""
    parts = ["**System Status:**"]

    if dae.wre:
        parts.append(f"  - WRE: ONLINE (state={dae.wre.state})")
        if dae.wre.skills_loader:
            parts.append("  - Skills Loader: ACTIVE")
        if dae.wre.libido_monitor:
            parts.append("  - Libido Monitor: ACTIVE")
    else:
        parts.append("  - WRE: OFFLINE")

    if dae.overseer:
        parts.append("  - AI Overseer: LOADED")
    else:
        parts.append("  - AI Overseer: NOT LOADED")

    identity = dae.get_identity_snapshot(include_runtime_probe=True)
    parts.append(f"  - OpenClaw Conversation Backend: {identity['backend']}")
    parts.append(
        "  - Runtime Profile: "
        f"{identity.get('runtime_profile', 'openclaw')}"
    )
    parts.append(
        "  - OpenClaw Key Isolation: "
        f"{identity['key_isolation']} "
        f"(external_llm={'ON' if dae._allow_external_llm else 'OFF'})"
    )
    parts.append(
        "  - IronClaw Strict Mode: "
        f"{identity['ironclaw_strict']} "
        f"(allow_local_fallback={identity['ironclaw_allow_local_fallback']})"
    )
    parts.append(
        "  - 0102 Taxonomy: "
        f"genus={identity['genus']} "
        f"lineage={identity['lineage']} "
        f"model_family={identity['model_family']} "
        f"model_name={identity['model_name']}"
    )
    parts.append(
        "  - Conversation Model Target: "
        f"{identity.get('conversation_model_target', 'local/qwen-coder-7b')} "
        f"(preferred_external="
        f"{identity.get('preferred_external_provider', 'none')}/"
        f"{identity.get('preferred_external_model', 'none')})"
    )
    parts.append(
        "  - Preferred External Status: "
        f"{identity.get('preferred_external_status', 'not_selected')} "
        f"({identity.get('preferred_external_status_detail', 'none')}, "
        f"age={identity.get('preferred_external_status_age', 'never')})"
    )
    parts.append(f"  - Protocol Anchor: {identity['protocol_anchor']}")
    parts.append(
        "  - WSP_00 Boot Prompt: "
        f"{identity['wsp00_boot']} "
        f"(mode={identity['wsp00_boot_mode']}, file_override={identity['wsp00_file_override']})"
    )
    parts.append(
        "  - Platform Context Pack: "
        f"{identity.get('platform_context', 'OFF')} "
        f"(sources={identity.get('platform_context_sources', '0')}, "
        f"loaded={identity.get('platform_context_loaded_ago', 'never')})"
    )
    parts.append(
        f"  - Last Conversation Engine: {identity['last_engine']} ({identity['last_engine_detail']})"
    )
    parts.append(
        "  - Previous Conversation Engine: "
        f"{identity.get('previous_engine', 'none')} "
        f"({identity.get('previous_engine_detail', 'none')})"
    )
    parts.append(
        "  - Token Usage (Last Turn): "
        f"prompt={identity.get('token_last_prompt_tokens', '0')} "
        f"completion={identity.get('token_last_completion_tokens', '0')} "
        f"total={identity.get('token_last_total_tokens', '0')} "
        f"engine={identity.get('token_last_engine', 'none')} "
        f"provider={identity.get('token_last_provider', 'none')} "
        f"source={identity.get('token_last_source', 'none')} "
        f"cost_estimate_usd={identity.get('token_last_cost_estimate_usd', '0.000000')} "
        f"age={identity.get('token_last_age', 'never')}"
    )
    parts.append(
        "  - Token Usage (Session): "
        f"turns={identity.get('token_session_turns', '0')} "
        f"prompt={identity.get('token_session_prompt_tokens', '0')} "
        f"completion={identity.get('token_session_completion_tokens', '0')} "
        f"total={identity.get('token_session_total_tokens', '0')} "
        f"cost_estimate_usd={identity.get('token_session_cost_estimate_usd', '0.000000')}"
    )
    parts.append(
        "  - Local Code Model: "
        f"{identity['local_code_model_path']} "
        f"({identity['local_code_model_state']}, source={identity['local_code_model_source']})"
    )
    if dae._conversation_backend == "ironclaw" or _env_truthy(
        "OPENCLAW_ALLOW_IRONCLAW_FALLBACK",
        "0",
    ):
        parts.append(
            "  - IronClaw Runtime: "
            f"{identity['ironclaw_runtime_healthy']} ({identity['ironclaw_runtime_detail']}) "
            f"configured_model={identity['ironclaw_runtime_model']} "
            f"visible_models={identity['ironclaw_runtime_models']}"
        )

    import time as _time

    parts.append("")
    parts.append("**Security Status:**")
    status = "PASS" if dae._skill_scan_ok else "FAIL"
    required = "required" if dae._skill_scan_required else "optional"
    enforced = "enforced" if dae._skill_scan_enforced else "warn-only"
    checked_ago = (
        f"{int(_time.time() - dae._skill_scan_checked_at)}s ago"
        if dae._skill_scan_checked_at > 0
        else "never"
    )
    parts.append(f"  - Skill Safety Gate: {status} ({required}, {enforced})")
    parts.append(f"  - Last Check: {checked_ago}")
    parts.append(f"  - Message: {dae._skill_scan_message}")

    if dae.permissions:
        parts.append("  - Permission Manager: ACTIVE")
    else:
        parts.append("  - Permission Manager: NOT LOADED")

    parts.append(f"  - OpenClaw DAE: state={dae.state} coherence={dae.coherence}")
    return "\n".join(parts)


async def execute_schedule(dae: Any, intent: Any) -> str:
    """Route SCHEDULE intent to explicit YouTube action adapter or fallback."""
    try:
        from .youtube_automation_adapter import handle_youtube_automation_intent

        yt_response = await handle_youtube_automation_intent(
            intent.raw_message,
            intent.sender,
        )
        if yt_response:
            return yt_response
    except Exception as exc:
        logger.warning("[OPENCLAW-DAE] YouTube automation adapter unavailable: %s", exc)

    return (
        f"Schedule request received: {intent.extracted_task}\n"
        "Routing to YouTube Shorts Scheduler... "
        "(use explicit command for execution: "
        "`youtube action scheduling channel=move2japan max_videos=3 dry_run=true`)"
    )


def execute_system(dae: Any, intent: Any) -> str:
    """Route SYSTEM intent (requires commander authority)."""
    if not intent.is_authorized_commander:
        return "System commands require @012 authorization. Your request has been logged."
    return (
        f"System command received: {intent.extracted_task}\n"
        "Infrastructure routing in progress..."
    )


async def execute_automation(dae: Any, intent: Any) -> str:
    """Route AUTOMATION intent to explicit YouTube adapter or AutoModeratorBridge."""
    try:
        from .youtube_automation_adapter import handle_youtube_automation_intent

        yt_response = await handle_youtube_automation_intent(
            intent.raw_message,
            intent.sender,
        )
        if yt_response:
            return yt_response
    except Exception as exc:
        logger.warning("[OPENCLAW-DAE] YouTube automation adapter unavailable: %s", exc)

    try:
        from .auto_moderator_bridge import handle_automation_intent

        return handle_automation_intent(intent.raw_message, intent.sender)
    except ImportError as exc:
        logger.warning("[OPENCLAW-DAE] AutoModeratorBridge not available: %s", exc)
        return (
            "Automation bridge not available. "
            "Check that auto_moderator_bridge.py exists."
        )
    except Exception as exc:
        logger.error("[OPENCLAW-DAE] Automation execution error: %s", exc)
        return f"Automation error: {exc}"


def execute_foundup(dae: Any, intent: Any) -> str:
    """Route FOUNDUP intent to FAM Adapter."""
    try:
        from .fam_adapter import handle_fam_intent

        return handle_fam_intent(intent.raw_message, intent.sender)
    except ImportError as exc:
        logger.warning("[OPENCLAW-DAE] FAM Adapter not available: %s", exc)
        return (
            "FoundUps Agent Market not available. "
            "Check that fam_adapter.py exists."
        )
    except Exception as exc:
        logger.error("[OPENCLAW-DAE] FAM execution error: %s", exc)
        return f"FAM error: {exc}"


def execute_research(dae: Any, intent: Any) -> str:
    """Route RESEARCH intent to PQN Research Adapter."""
    try:
        from .pqn_research_adapter import handle_pqn_research_intent

        return handle_pqn_research_intent(intent.raw_message, intent.sender)
    except ImportError as exc:
        logger.warning(
            "[OPENCLAW-DAE] PQN Research Adapter not available: %s",
            exc,
        )
        return (
            "PQN Research module not available. "
            "Check that pqn_research_adapter.py exists."
        )
    except Exception as exc:
        logger.error("[OPENCLAW-DAE] Research execution error: %s", exc)
        return f"Research error: {exc}"


def _env_truthy(name: str, default: str = "0") -> bool:
    """Return True when environment variable is set to a truthy value."""
    import os

    return os.getenv(name, default).strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }
