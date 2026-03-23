"""OpenClaw execution-route helpers after plan resolution."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

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

    # Memory queries: decision recall, unresolved work, recent sessions
    memory_response = _try_memory_query(dae, intent.raw_message)
    if memory_response:
        return memory_response

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

    command_context = _build_wre_command_context(dae, intent)
    try:
        execute_skill = getattr(dae.wre, "execute_skill", None)
        if callable(execute_skill):
            skill_name, skill_agent, selection_metadata = _resolve_wre_skill_execution(
                dae, intent, command_context
            )
            if skill_name:
                skill_context = dict(command_context)
                if selection_metadata:
                    skill_context["skill_selection"] = selection_metadata
                result = execute_skill(
                    skill_name=skill_name,
                    agent=skill_agent,
                    input_context=skill_context,
                )
                return _format_wre_command_result(result, skill_name=skill_name)

        result = dae.wre.execute(command_context)
        return _format_wre_command_result(result)
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


def _build_wre_command_context(dae: Any, intent: Any) -> Dict[str, Any]:
    """Normalize OpenClaw COMMAND context for WRE entry points."""
    return {
        "type": "orchestration",
        "task": intent.extracted_task or intent.raw_message,
        "command": intent.raw_message,
        "source": "openclaw_dae",
        "sender": intent.sender,
        "channel": intent.channel,
        "target_files": dae._extract_file_paths(intent.raw_message),
    }


def _resolve_wre_skill_execution(
    dae: Any,
    intent: Any,
    command_context: Dict[str, Any],
) -> tuple[Optional[str], str, Dict[str, Any]]:
    """
    Pick the best existing WRE skill for an OpenClaw COMMAND.

    Prefer natural-language candidate discovery, bias git requests toward the
    existing `qwen_gitpush` skill, and fall back to `openclaw_executor` as the
    generic command bridge when no domain-specific match exists.
    """
    wre = dae.wre
    loader = getattr(wre, "skills_loader", None)
    task_text = command_context.get("task", "") or ""

    candidates = []
    find_candidates = getattr(wre, "find_skill_candidates", None)
    if callable(find_candidates):
        try:
            candidates = list(find_candidates(task_text) or [])
        except Exception as exc:
            logger.warning("[OPENCLAW-DAE] Skill discovery failed for '%s': %s", task_text, exc)

    if _looks_like_git_command(task_text) and _loader_has_skill(loader, "qwen_gitpush"):
        candidates.insert(0, "qwen_gitpush")

    if not candidates and _loader_has_skill(loader, "openclaw_executor"):
        candidates.append("openclaw_executor")

    candidates = _dedupe_skills(candidates)
    if not candidates:
        return None, "qwen", {}

    selected_skill = candidates[0]
    selection_metadata: Dict[str, Any] = {}
    select_skill_tot = getattr(wre, "select_skill_tot", None)
    if callable(select_skill_tot) and len(candidates) > 1:
        try:
            selected_skill, selection_metadata = select_skill_tot(candidates, command_context)
        except Exception as exc:
            logger.warning("[OPENCLAW-DAE] ToT skill selection failed: %s", exc)

    return selected_skill, _resolve_skill_agent(loader, selected_skill), selection_metadata


def _loader_has_skill(loader: Any, skill_name: str) -> bool:
    """Duck-typed skill existence check for real loaders and test doubles."""
    if loader is None:
        return False

    has_skill = getattr(loader, "has_skill", None)
    if callable(has_skill):
        try:
            result = has_skill(skill_name)
            if isinstance(result, bool):
                return result
        except Exception:
            pass

    registry = getattr(loader, "registry", {}) or {}
    skills = registry.get("skills", {}) if isinstance(registry, dict) else {}
    return isinstance(skills, dict) and skill_name in skills


def _resolve_skill_agent(loader: Any, skill_name: str) -> str:
    """Choose the preferred execution agent for a registered skill."""
    if loader is None:
        return "qwen"

    registry = getattr(loader, "registry", {}) or {}
    skills = registry.get("skills", {}) if isinstance(registry, dict) else {}
    skill_info = skills.get(skill_name, {}) if isinstance(skills, dict) else {}

    agents = skill_info.get("agents") or []
    primary_agent = skill_info.get("primary_agent")
    fallback_agent = skill_info.get("fallback_agent")

    for candidate in ("qwen", "gemma", "grok", "ui-tars"):
        if candidate == primary_agent or candidate in agents:
            return candidate

    if primary_agent:
        return str(primary_agent)
    if fallback_agent:
        return str(fallback_agent)
    if agents:
        return str(agents[0])
    return "qwen"


def _looks_like_git_command(task_text: str) -> bool:
    """Detect git-oriented autonomous development requests."""
    lowered = (task_text or "").lower()
    return bool(
        re.search(
            r"\b(git|commit|push|branch|merge|rebase|stash|diff|pull request)\b",
            lowered,
        )
    )


def _dedupe_skills(skill_names: list[str]) -> list[str]:
    """Preserve candidate order while removing duplicates and blanks."""
    seen = set()
    ordered = []
    for skill_name in skill_names:
        if not skill_name or skill_name in seen:
            continue
        seen.add(skill_name)
        ordered.append(skill_name)
    return ordered


def _format_wre_command_result(result: Any, skill_name: Optional[str] = None) -> str:
    """Render WRE execution results for OpenClaw channel responses."""
    prefix = "Command executed via WRE"
    if skill_name:
        prefix = f"Command executed via WRE skill `{skill_name}`"

    if isinstance(result, dict):
        output = result.get("output")
        if output in (None, ""):
            output = result.get("reason") or result.get("error")
        if output in (None, ""):
            output = json.dumps(result, indent=2, ensure_ascii=False, default=str)
        elif not isinstance(output, str):
            output = json.dumps(output, indent=2, ensure_ascii=False, default=str)
        return f"{prefix}:\n{output}"

    return f"{prefix}:\n{result}"


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
    try:
        from .dae_runtime_adapter import is_dae_runtime_request, handle_dae_runtime_intent

        if is_dae_runtime_request(intent.raw_message):
            response = handle_dae_runtime_intent(
                intent.raw_message,
                intent.sender,
                allow_mutation=False,
            )
            if response:
                return response
    except Exception as exc:
        logger.warning("[OPENCLAW-DAE] DAE runtime monitor adapter unavailable: %s", exc)

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
    try:
        from .dae_runtime_adapter import is_dae_runtime_request, handle_dae_runtime_intent

        if is_dae_runtime_request(intent.raw_message):
            response = handle_dae_runtime_intent(
                intent.raw_message,
                intent.sender,
                allow_mutation=True,
            )
            if response:
                return response
    except Exception as exc:
        logger.warning("[OPENCLAW-DAE] DAE runtime system adapter unavailable: %s", exc)
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

        return handle_pqn_research_intent(
            intent.raw_message,
            intent.sender,
            report_action=dae._report_daemon_action,
        )
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


# --------------------------------------------------------------------------- #
#  Memory Query Helpers (P0: openclaw_memory_queries)                          #
# --------------------------------------------------------------------------- #


# Time qualifiers that should be normalized to None (not treated as topics)
_TIME_ONLY_QUALIFIERS = {
    "yesterday",
    "today",
    "last night",
    "this morning",
    "this week",
    "last week",
    "recently",
    "lately",
}


def _normalize_time_qualifier(topic: Optional[str]) -> Optional[str]:
    """
    Normalize time-only qualifiers to None.

    "what was I working on yesterday" should query recent activity,
    not search for the literal topic "yesterday".
    """
    if topic is None:
        return None
    topic_lower = topic.lower().strip()
    if topic_lower in _TIME_ONLY_QUALIFIERS:
        return None
    return topic


def _try_memory_query(dae: Any, raw_message: str) -> Optional[str]:
    """
    Detect and handle deterministic memory queries.

    Supported patterns:
    - "what did we decide about X" -> decision recall
    - "show unresolved work" / "show pending work" -> unresolved work
    - "show recent sessions" / "show high-value sessions" -> recent sessions
    - "show past work on X" / "what was I working on" -> past work recall

    IMPORTANT: Patterns must be narrow to avoid hijacking normal QUERY traffic.
    Use word boundaries and require memory-specific nouns.
    """
    normalized = raw_message.lower().strip()

    # Decision query: "what did we decide about X"
    # Narrow: requires exact phrase "what did we decide"
    decision_match = re.search(
        r"what\s+did\s+we\s+decide\s+(?:about|on|for|regarding)\s+(.+)",
        normalized,
    )
    if decision_match:
        topic = decision_match.group(1).strip().rstrip("?")
        return _query_decisions(dae, topic)

    # Past work query: "show past work on X" / "what was I working on X"
    # Narrow: requires "past work" or "working on" phrases with topic
    past_work_match = re.search(
        r"(?:show|list|find)\s+(?:past|prior|previous)\s+work\s+(?:on|about|for)\s+(.+)",
        normalized,
    )
    if past_work_match:
        topic = past_work_match.group(1).strip().rstrip("?")
        return _query_past_work(dae, topic)

    # "what was I working on X" variant
    working_on_match = re.search(
        r"what\s+(?:was|were)\s+(?:i|we|you)\s+working\s+on\s*(.*)$",
        normalized,
    )
    if working_on_match:
        topic = working_on_match.group(1).strip().rstrip("?") or None
        # Normalize time-only qualifiers to None (not a topic)
        topic = _normalize_time_qualifier(topic)
        return _query_past_work(dae, topic)

    # Unresolved work query
    # Narrow: requires memory noun (work|tasks|items) AND status word with word boundaries
    # Avoids: "what openclaw..." matching via "open" substring
    if re.search(
        r"\b(unresolved|pending|remaining)\b.{0,20}\b(work|tasks?|items?)\b",
        normalized,
    ) or re.search(
        r"\b(work|tasks?|items?)\b.{0,20}\b(unresolved|pending|remaining|left)\b",
        normalized,
    ):
        return _query_unresolved_work(dae)

    # Recent sessions query
    # Narrow: requires "sessions" noun explicitly
    # Avoids: "show latest WSP docs" matching via "latest" alone
    if re.search(
        r"\b(recent|high.?value|latest)\b.{0,15}\bsessions?\b",
        normalized,
    ) or re.search(
        r"\bsessions?\b.{0,15}\b(recent|high.?value|latest)\b",
        normalized,
    ):
        return _query_recent_sessions(dae)

    return None


def _query_decisions(dae: Any, topic: str) -> str:
    """
    Search workspace memory and breadcrumbs for decisions related to a topic.

    Sources with explicit provenance:
    - workspace_memory: Memory notes containing topic
    - breadcrumbs: AgentDB activity related to topic
    """
    memory_matches = _scan_workspace_memory(dae, topic)
    breadcrumb_matches = _search_breadcrumbs(topic, limit=10)

    # Filter breadcrumbs to decision-related actions
    decision_keywords = {"decide", "decision", "agreed", "chose", "approved", "rejected"}
    decision_breadcrumbs = []
    for crumb in breadcrumb_matches:
        action = str(crumb.get("action", "")).lower()
        query = str(crumb.get("query", "")).lower()
        if any(kw in action or kw in query for kw in decision_keywords):
            decision_breadcrumbs.append(crumb)

    if not memory_matches and not decision_breadcrumbs:
        return (
            f"**No decisions found for:** `{topic}`\n\n"
            "I searched workspace memory notes and AgentDB breadcrumbs but found no matching records.\n"
            "This may mean:\n"
            "- The decision was made before memory notes were captured\n"
            "- The topic uses different terminology\n"
            "- No formal decision was recorded\n\n"
            "Try rephrasing or ask 012 directly."
        )

    parts = [f"**Decisions related to:** `{topic}`\n"]
    sources = []

    # Memory matches
    if memory_matches:
        sources.append("workspace_memory")
        for match in memory_matches[:5]:
            parts.append(f"### {match['title']}")
            parts.append(f"**Source:** `workspace_memory:{match['path']}`")
            parts.append(f"**Date:** {match.get('date', 'unknown')}")
            if match.get("snippet"):
                parts.append(f"\n{match['snippet'][:500]}")
            parts.append("")

    # Breadcrumb evidence
    if decision_breadcrumbs:
        sources.append("breadcrumbs")
        parts.append("### Related Activity (breadcrumbs)")
        for crumb in decision_breadcrumbs[:3]:
            date = crumb.get("timestamp", "unknown")[:10] if crumb.get("timestamp") else "unknown"
            action = crumb.get("action", "unknown")
            query = crumb.get("query", "")[:80] if crumb.get("query") else ""
            parts.append(f"- **{date}**: {action}")
            if query:
                parts.append(f"  > {query}")
        parts.append("")

    scanned = memory_matches[0].get("total_scanned", "?") if memory_matches else "0"
    parts.append(f"_Sources: {', '.join(sources)} | Scanned {scanned} memory artifacts._")
    return "\n".join(parts)


def _query_past_work(dae: Any, topic: Optional[str]) -> str:
    """
    Query past work from workspace memory and AgentDB breadcrumbs.

    Combines:
    - workspace_memory: Memory notes matching topic (or recent notes if no topic)
    - breadcrumbs: Recent AgentDB activity matching topic

    Returns results with explicit provenance.
    """
    results = []

    # Source 1: Workspace memory
    if topic:
        # Topic-filtered search
        memory_matches = _scan_workspace_memory(dae, topic)
        for match in memory_matches[:5]:
            results.append({
                "source": "workspace_memory",
                "title": match.get("title", "unknown"),
                "date": match.get("date", "unknown"),
                "path": match.get("path", ""),
                "snippet": match.get("snippet", "")[:300],
            })
    else:
        # No topic: include recent workspace memory notes
        recent_notes = _get_recent_memory_notes(dae, limit=5)
        for note in recent_notes:
            results.append({
                "source": "workspace_memory",
                "title": note.get("title", "unknown"),
                "date": note.get("date", "unknown"),
                "path": note.get("path", ""),
                "snippet": "",
            })

    # Source 2: AgentDB breadcrumbs
    breadcrumb_matches = _search_breadcrumbs(topic, limit=20)
    for crumb in breadcrumb_matches[:10]:
        results.append({
            "source": "breadcrumbs",
            "title": crumb.get("action", "unknown"),
            "date": crumb.get("timestamp", "unknown")[:10] if crumb.get("timestamp") else "unknown",
            "agent": crumb.get("agent_id", ""),
            "query": crumb.get("query", "")[:100] if crumb.get("query") else "",
        })

    if not results:
        topic_str = f" for `{topic}`" if topic else ""
        return (
            f"**No past work found{topic_str}.**\n\n"
            "Searched: workspace memory notes, AgentDB breadcrumbs.\n"
            "Try a broader topic or check recent sessions."
        )

    # Build response with provenance
    parts = []
    if topic:
        parts.append(f"**Past work on:** `{topic}`\n")
    else:
        parts.append("**Recent work activity:**\n")

    # Group by source for clarity
    memory_items = [r for r in results if r["source"] == "workspace_memory"]
    breadcrumb_items = [r for r in results if r["source"] == "breadcrumbs"]

    if memory_items:
        parts.append("### Workspace Memory")
        for item in memory_items:
            parts.append(f"- **{item['date']}**: {item['title']} (`{item['path']}`)")
            if item.get("snippet"):
                parts.append(f"  > {item['snippet'][:150]}...")
        parts.append("")

    if breadcrumb_items:
        parts.append("### Activity Breadcrumbs")
        for item in breadcrumb_items:
            agent_str = f" [{item['agent']}]" if item.get("agent") else ""
            query_str = f": {item['query']}" if item.get("query") else ""
            parts.append(f"- **{item['date']}**: {item['title']}{agent_str}{query_str}")
        parts.append("")

    source_str = ", ".join(sorted(set(r["source"] for r in results)))
    parts.append(f"_Sources: {source_str}_")
    return "\n".join(parts)


def _search_breadcrumbs(topic: Optional[str], limit: int = 20) -> list[Dict[str, Any]]:
    """
    Search AgentDB breadcrumbs, optionally filtered by topic.

    Returns breadcrumbs matching the topic in action, query, or data fields.
    """
    try:
        from modules.infrastructure.database.src.agent_db import AgentDB

        db = AgentDB()
        all_breadcrumbs = db.get_breadcrumbs(limit=limit * 2)

        if not topic:
            # Return recent breadcrumbs without filtering
            return all_breadcrumbs[:limit]

        # Filter by topic presence in action, query, or data
        topic_lower = topic.lower()
        topic_words = set(topic_lower.split())
        matches = []

        for crumb in all_breadcrumbs:
            searchable = " ".join([
                str(crumb.get("action", "")),
                str(crumb.get("query", "")),
                str(crumb.get("data", "")),
            ]).lower()

            # Match if topic or any topic word (>3 chars) found
            if topic_lower in searchable:
                matches.append(crumb)
            elif any(word in searchable for word in topic_words if len(word) > 3):
                matches.append(crumb)

        return matches[:limit]

    except ImportError:
        logger.debug("AgentDB not available for breadcrumb search")
        return []
    except Exception as exc:
        logger.debug("Failed to search breadcrumbs: %s", exc)
        return []


def _query_unresolved_work(dae: Any) -> str:
    """Query queue status and memory for unresolved/pending work."""
    unresolved = []
    sources = []

    # Check native execution queue
    queue_path = _get_workspace_path(dae) / "reports/openclaw_native_execution_queue_status.json"
    if queue_path.exists():
        try:
            with open(queue_path, "r", encoding="utf-8") as f:
                queue_data = json.load(f)
            sources.append(str(queue_path.name))

            # Next ready items
            for item in queue_data.get("next_ready", []):
                unresolved.append({
                    "title": item.get("title", "unknown"),
                    "priority": item.get("priority", "?"),
                    "source": "native_queue (ready)",
                })

            # Audit-required items
            for item in queue_data.get("next_audit", [])[:3]:
                unresolved.append({
                    "title": item.get("title", "unknown"),
                    "priority": item.get("priority", "?"),
                    "source": "native_queue (audit_required)",
                })
        except Exception as exc:
            logger.debug("Failed to read queue status: %s", exc)

    # Check self-research status for update candidates
    research_path = _get_workspace_path(dae) / "reports/openclaw_self_research_status.json"
    if research_path.exists():
        try:
            with open(research_path, "r", encoding="utf-8") as f:
                research_data = json.load(f)
            sources.append(str(research_path.name))

            for candidate in research_data.get("update_candidates", [])[:3]:
                unresolved.append({
                    "title": candidate.get("title", "unknown"),
                    "priority": candidate.get("mps", {}).get("priority", "?"),
                    "source": "self_research",
                })
        except Exception as exc:
            logger.debug("Failed to read self-research status: %s", exc)

    if not unresolved:
        return (
            "**No unresolved work found.**\n\n"
            "Checked: native execution queue, self-research status.\n"
            "Either all work is complete or no pending items were recorded."
        )

    parts = ["**Unresolved Work:**\n"]
    for item in unresolved:
        parts.append(
            f"- [{item['priority']}] {item['title']} _(from {item['source']})_"
        )

    parts.append("")
    parts.append(f"_Sources: {', '.join(sources)}_")
    return "\n".join(parts)


def _query_recent_sessions(dae: Any) -> str:
    """List recent high-value session notes from workspace memory."""
    memory_dir = _get_workspace_path(dae) / "memory"
    if not memory_dir.exists():
        return (
            "**No session memory found.**\n\n"
            "Workspace memory directory does not exist."
        )

    # Get recent memory notes sorted by date
    notes = []
    try:
        for note_path in sorted(memory_dir.glob("*.md"), reverse=True)[:10]:
            try:
                content = note_path.read_text(encoding="utf-8")
                first_line = content.split("\n")[0].strip()
                title = first_line.lstrip("#").strip() if first_line.startswith("#") else note_path.stem

                # Extract date from filename (2026-03-22-topic.md)
                date_match = re.match(r"(\d{4}-\d{2}-\d{2})", note_path.stem)
                date = date_match.group(1) if date_match else "unknown"

                notes.append({
                    "title": title,
                    "date": date,
                    "path": note_path.name,
                    "size": len(content),
                })
            except Exception:
                continue
    except Exception as exc:
        logger.debug("Failed to scan memory directory: %s", exc)

    if not notes:
        return (
            "**No recent sessions found.**\n\n"
            "Workspace memory exists but contains no readable notes."
        )

    parts = ["**Recent Sessions:**\n"]
    for note in notes:
        parts.append(f"- **{note['date']}**: {note['title']} (`{note['path']}`)")

    parts.append("")
    parts.append(f"_Found {len(notes)} session note(s) in workspace memory._")
    return "\n".join(parts)


def _get_recent_memory_notes(dae: Any, limit: int = 5) -> list[Dict[str, Any]]:
    """
    Get recent workspace memory notes without topic filtering.

    Returns list of notes with title, date, path.
    """
    memory_dir = _get_workspace_path(dae) / "memory"
    if not memory_dir.exists():
        return []

    notes = []
    try:
        for note_path in sorted(memory_dir.glob("*.md"), reverse=True)[:limit]:
            try:
                content = note_path.read_text(encoding="utf-8")
                first_line = content.split("\n")[0].strip()
                title = first_line.lstrip("#").strip() if first_line.startswith("#") else note_path.stem

                date_match = re.match(r"(\d{4}-\d{2}-\d{2})", note_path.stem)
                date = date_match.group(1) if date_match else "unknown"

                notes.append({
                    "title": title,
                    "date": date,
                    "path": note_path.name,
                })
            except Exception:
                continue
    except Exception as exc:
        logger.debug("Failed to get recent memory notes: %s", exc)

    return notes


def _scan_workspace_memory(dae: Any, topic: str) -> list[Dict[str, Any]]:
    """
    Scan workspace memory notes for content matching a topic.

    Returns list of matches with provenance.
    """
    from pathlib import Path

    memory_dir = _get_workspace_path(dae) / "memory"
    if not memory_dir.exists():
        return []

    topic_lower = topic.lower()
    topic_words = set(topic_lower.split())
    matches = []
    total_scanned = 0

    try:
        for note_path in memory_dir.glob("*.md"):
            total_scanned += 1
            try:
                content = note_path.read_text(encoding="utf-8")
                content_lower = content.lower()

                # Check if topic appears in content
                if topic_lower not in content_lower:
                    # Fallback: check if any topic word appears
                    if not any(word in content_lower for word in topic_words if len(word) > 3):
                        continue

                # Extract title and date
                first_line = content.split("\n")[0].strip()
                title = first_line.lstrip("#").strip() if first_line.startswith("#") else note_path.stem

                date_match = re.match(r"(\d{4}-\d{2}-\d{2})", note_path.stem)
                date = date_match.group(1) if date_match else "unknown"

                # Extract snippet around topic
                snippet = _extract_snippet(content, topic_lower)

                matches.append({
                    "title": title,
                    "date": date,
                    "path": str(note_path.relative_to(_get_workspace_path(dae))),
                    "snippet": snippet,
                    "total_scanned": total_scanned,
                })
            except Exception:
                continue
    except Exception as exc:
        logger.debug("Failed to scan workspace memory: %s", exc)

    # Sort by date descending
    matches.sort(key=lambda m: m.get("date", ""), reverse=True)

    # Propagate total_scanned to all matches
    for match in matches:
        match["total_scanned"] = total_scanned

    return matches


def _extract_snippet(content: str, topic: str) -> str:
    """Extract a text snippet around the topic mention."""
    content_lower = content.lower()
    pos = content_lower.find(topic)
    if pos == -1:
        # Return first meaningful paragraph
        lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#")]
        return lines[0] if lines else ""

    # Extract context around match
    start = max(0, pos - 100)
    end = min(len(content), pos + len(topic) + 200)

    snippet = content[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet = snippet + "..."

    return snippet


def _get_workspace_path(dae: Any) -> "Path":
    """Get the workspace path for memory and reports."""
    from pathlib import Path

    repo_root = getattr(dae, "repo_root", None)
    if repo_root:
        return Path(repo_root) / "modules/communication/moltbot_bridge/workspace"
    return Path("modules/communication/moltbot_bridge/workspace")


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
