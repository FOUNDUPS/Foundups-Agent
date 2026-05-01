"""OpenClaw execution-route helpers after plan resolution."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional

# ImprovementJob contract imports (OC_IMP3)
from modules.infrastructure.wre_core.src.improvement_job_contract import (
    ImprovementJob,
    ImprovementRiskLevel,
    ImprovementScope,
    ImprovementType,
    WSP15Priority,
    create_improvement_job,
)

from .openclaw_memory_queries import (
    normalize_time_qualifier,
    query_continuity_status,
    query_cross_surface_activity,
    query_current_continuity,
    query_decisions,
    query_past_work,
    query_recent_sessions,
    query_unresolved_work,
)
from .openclaw_execution_bundle import build_execution_bundle

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
    if route == "training_controller":
        return execute_training(dae, intent)
    if route == "improvement_router":
        return execute_improvement(dae, intent)

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

    # Schedule management commands
    schedule_response = _try_schedule_command(dae, intent.raw_message)
    if schedule_response:
        return schedule_response

    # Build execution bundle with HoloIndex retrieval (single search, WSP 87/97)
    query_text = intent.extracted_task or intent.raw_message
    bundle = build_execution_bundle(query_text, route="holo_index", limit=5)
    logger.debug(
        "[OPENCLAW-DAE] [BUNDLE] query=%s conf=%.2f candidates=%d code=%d wsp=%d",
        query_text[:50],
        bundle.confidence,
        len(bundle.candidate_paths),
        len(bundle.code_hits),
        len(bundle.wsp_hits),
    )

    # Use bundle's pre-fetched HoloIndex hits (no duplicate search)
    code_hits = bundle.code_hits
    wsp_hits = bundle.wsp_hits

    if not code_hits and not wsp_hits:
        # Bundle has no HoloIndex results - provide fallback with bundle context
        if bundle.candidate_paths:
            # Bundle found candidate paths via other means (breadcrumbs, etc.)
            parts = [f"No direct matches for: {intent.extracted_task}"]
            parts.append("\n**Related paths from prior work:**")
            for path in bundle.candidate_paths[:3]:
                parts.append(f"  - `{path}`")
            return "\n".join(parts)
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

    # Include verification hints if present
    if bundle.verification_hints:
        parts.append("\n**Verification:**")
        for hint in bundle.verification_hints[:2]:
            parts.append(f"  - {hint}")

    return "\n".join(parts)


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
    """Normalize OpenClaw COMMAND context for WRE entry points.

    Includes parent continuity context for cross-surface tracking (OpenClaw → WRE).
    """
    ctx: Dict[str, Any] = {
        "type": "orchestration",
        "task": intent.extracted_task or intent.raw_message,
        "command": intent.raw_message,
        "source": "openclaw_dae",
        "sender": intent.sender,
        "channel": intent.channel,
        "target_files": dae._extract_file_paths(intent.raw_message),
    }
    # Gateway Continuity Layer: Propagate continuity for cross-surface tracking
    continuity_ctx = getattr(dae, "_continuity_context", None)
    if continuity_ctx is not None:
        ctx["parent_continuity_context"] = continuity_ctx
    return ctx


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
    """Route FOUNDUP intent through orchestrator entrypoint.

    Phase 1 (OC1): Orchestrator dispatches to FAM with safe fallback.
    Phase 2+: Will add genesis validation gate before FAM handoff.
    """
    try:
        from .openclaw_foundup_orchestrator import dispatch_foundup

        return dispatch_foundup(dae, intent)
    except ImportError as exc:
        # Fallback: orchestrator unavailable, try direct FAM
        logger.warning(
            "[OPENCLAW-DAE] Orchestrator unavailable, trying direct FAM: %s", exc
        )
        try:
            from .fam_adapter import handle_fam_intent

            return handle_fam_intent(intent.raw_message, intent.sender)
        except ImportError as fam_exc:
            logger.warning("[OPENCLAW-DAE] FAM Adapter not available: %s", fam_exc)
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


def execute_training(dae: Any, intent: Any) -> str:
    """Route TRAINING intent to corpus training controller (012 only).

    Commands:
    - "training status" -> show checkpoint, due status, progress
    - "start training" / "run training batch" -> trigger batch
    - "is training due" -> boolean check
    """
    if not intent.is_authorized_commander:
        return "Training commands require @012 authorization. Your request has been logged."

    msg_lower = intent.raw_message.lower().strip()

    # Dispatch by sub-command
    if _is_training_status_query(msg_lower):
        return _get_training_status()
    if _is_training_start_command(msg_lower):
        return _start_training_batch()
    if _is_training_due_query(msg_lower):
        status = _get_training_status_data()
        due = status.get("training_due", False)
        progress = status.get("progress_pct", 0.0)
        return f"Training due: **{'YES' if due else 'NO'}** (progress: {progress:.1f}%, threshold: 95%)"

    # Default: show status
    return _get_training_status()


def _is_training_status_query(msg: str) -> bool:
    """Detect training status queries."""
    return any(
        kw in msg
        for kw in ("training status", "training progress", "checkpoint status", "show training")
    )


def _is_training_start_command(msg: str) -> bool:
    """Detect training start commands."""
    return any(
        kw in msg
        for kw in ("start training", "run training", "training batch", "begin training")
    )


def _is_training_due_query(msg: str) -> bool:
    """Detect training due queries."""
    return any(
        kw in msg
        for kw in ("is training due", "training due", "need training", "should train")
    )


def _get_training_status_data() -> dict:
    """Fetch training status data from startup_maintenance_gate."""
    try:
        from pathlib import Path
        from modules.infrastructure.idle_automation.src.startup_maintenance_gate import (
            StartupMaintenanceGate,
        )

        gate = StartupMaintenanceGate(Path("O:/Foundups-Agent"))
        return gate.check_training_readiness()
    except Exception as exc:
        logger.warning("[OPENCLAW-DAE] Training status fetch failed: %s", exc)
        return {"error": str(exc)}


def _get_training_status() -> str:
    """Build human-readable training status report.

    Uses startup_maintenance_gate as single source of truth for:
    - checkpoint_line
    - corpus_lines
    - progress_pct
    - training_due
    """
    status = _get_training_status_data()

    if "error" in status:
        return f"**Training Status: ERROR**\n\nCould not fetch status: {status['error']}"

    checkpoint = status.get("checkpoint_line")
    corpus_lines = status.get("corpus_lines")
    progress = status.get("progress_pct", 0.0)
    training_due = status.get("training_due", False)
    exists = status.get("exists", False)
    age_hours = status.get("age_hours")

    parts = ["**Training Status**", ""]
    parts.append(f"- **Checkpoint**: {checkpoint or 'none'} / {corpus_lines or 'unknown'} lines")
    parts.append(f"- **Progress**: {progress:.1f}%")
    parts.append(f"- **Due**: {'YES' if training_due else 'NO'} (threshold: 95%)")
    parts.append(f"- **Status artifact exists**: {'yes' if exists else 'no'}")
    if age_hours is not None:
        parts.append(f"- **Last updated**: {age_hours:.1f} hours ago")

    if training_due:
        parts.append("")
        parts.append("_Training is due. Use `start training` to begin batch._")

    return "\n".join(parts)


def _start_training_batch() -> str:
    """Trigger training batch execution via startup_maintenance_gate."""
    try:
        from pathlib import Path
        from modules.communication.moltbot_bridge.scripts.run_task import (
            _try_startup_maintenance_dispatch,
        )

        result = _try_startup_maintenance_dispatch(
            repo_root=Path("O:/Foundups-Agent"),
            task_id="startup_training_batch",
            context={"source": "openclaw_training_command"},
        )

        if result is None:
            return "**Training Batch: NOT STARTED**\n\nDispatcher returned None (task may not be configured)."

        # Contract: dispatcher returns {ok, detail, executor, structured_result}
        ok = result.get("ok", False)
        detail = result.get("detail", "No detail")
        executor = result.get("executor", "unknown")

        # Detect "already complete" case: not a failure, just no-op
        if not ok and "Already processed" in detail:
            return f"**Training Batch: COMPLETE**\n\nNo new data to process.\n\nExecutor: `{executor}`\n\n{detail[:500]}"

        if ok:
            return f"**Training Batch: STARTED**\n\nExecutor: `{executor}`\n\n{detail[:500]}"
        else:
            return f"**Training Batch: FAILED**\n\nExecutor: `{executor}`\n\n{detail[:500]}"

    except Exception as exc:
        logger.error("[OPENCLAW-DAE] Training batch start failed: %s", exc)
        return f"**Training Batch: ERROR**\n\nCould not start: {exc}"


# ---------------------------------------------------------------------------
# ImprovementJob Inspection Hook (OC_IMP3)
# ---------------------------------------------------------------------------
# Module-level storage for test inspection ONLY.
# Not a production queue - just allows tests to verify job creation.
_LAST_IMPROVEMENT_JOB: Optional[ImprovementJob] = None


def get_last_improvement_job() -> Optional[ImprovementJob]:
    """Return the last created ImprovementJob for test inspection.

    WSP 97: This is a test hook only. Not a production queue.
    """
    return _LAST_IMPROVEMENT_JOB


def clear_improvement_job_hook() -> None:
    """Clear the inspection hook. For test cleanup."""
    global _LAST_IMPROVEMENT_JOB
    _LAST_IMPROVEMENT_JOB = None


# ---------------------------------------------------------------------------
# Improvement Type Classification
# ---------------------------------------------------------------------------

# Map string improvement types to ImprovementType enum
_IMPROVEMENT_TYPE_MAP: Dict[str, ImprovementType] = {
    "fmas_scan": ImprovementType.FMAS_SCAN,
    "drift_correction": ImprovementType.DRIFT_CORRECTION,
    "wsp_violation": ImprovementType.WSP_VIOLATION,
    "test_hygiene": ImprovementType.TEST_HYGIENE,
    "module_repair": ImprovementType.MODULE_REPAIR,
    "orphan_connection": ImprovementType.ORPHAN_CONNECTION,
    "doc_ledger_hygiene": ImprovementType.DOC_LEDGER_HYGIENE,
    "general": ImprovementType.FMAS_SCAN,  # Default fallback
}


def _classify_improvement_type(msg_lower: str) -> str:
    """Classify improvement sub-type from message text.

    Returns string key for _IMPROVEMENT_TYPE_MAP.

    Order matters: check specific keywords before generic ones.
    Priority: fmas > drift > wsp > doc artifacts > test > orphan > module > doc.
    Doc artifacts (modlog/readme/roadmap) must come before "test" and "module".
    """
    if "fmas" in msg_lower:
        return "fmas_scan"
    elif "drift" in msg_lower:
        return "drift_correction"
    elif "wsp" in msg_lower or "violation" in msg_lower:
        return "wsp_violation"
    # Doc artifacts (modlog/readme/roadmap) must come BEFORE "test" and "module"
    # "update modlog for test module" is doc_ledger_hygiene, not test_hygiene
    elif "modlog" in msg_lower or "readme" in msg_lower or "roadmap" in msg_lower:
        return "doc_ledger_hygiene"
    elif "test" in msg_lower or "stale" in msg_lower:
        return "test_hygiene"
    elif "orphan" in msg_lower:
        return "orphan_connection"
    elif "repair" in msg_lower or "module" in msg_lower or "cleanup" in msg_lower:
        return "module_repair"
    elif "doc" in msg_lower:
        return "doc_ledger_hygiene"
    return "general"


def _extract_module_path(message: str) -> str:
    """Extract module path from improvement message if present.

    Looks for patterns like:
      - modules/domain/module_name
      - in holo_index
      - in wre_core
    """
    # Try to find explicit module path
    module_match = re.search(
        r"(?:modules/[a-z_]+/[a-z_]+|in\s+([a-z_]+))",
        message.lower(),
    )
    if module_match:
        if module_match.group(0).startswith("modules/"):
            return module_match.group(0)
        elif module_match.group(1):
            # "in module_name" -> try to construct path
            module_name = module_match.group(1)
            # Common module locations
            for domain in ["infrastructure", "communication", "ai_intelligence", "foundups"]:
                return f"modules/{domain}/{module_name}"
    return ""


def _extract_wsp_refs(message: str) -> List[str]:
    """Extract WSP references from improvement message."""
    wsp_refs = []
    # Match patterns like "WSP 49", "wsp49", "WSP-49"
    wsp_matches = re.findall(r"wsp[-_\s]?(\d+)", message.lower())
    for num in wsp_matches:
        wsp_refs.append(f"WSP {num}")
    return wsp_refs


def _derive_risk_level(improvement_type_str: str, msg_lower: str) -> ImprovementRiskLevel:
    """Derive risk level from improvement type and message content."""
    # Security-related keywords -> HIGH
    if any(kw in msg_lower for kw in ["security", "secret", "credential", "vulnerability"]):
        return ImprovementRiskLevel.HIGH

    # Documentation-only changes -> LOW
    if improvement_type_str in ("doc_ledger_hygiene",):
        return ImprovementRiskLevel.LOW

    # Test hygiene with "stale" -> LOW (just updating tests)
    if improvement_type_str == "test_hygiene" and "stale" in msg_lower:
        return ImprovementRiskLevel.LOW

    # Default to MEDIUM for most repairs
    return ImprovementRiskLevel.MEDIUM


def _generate_finding_id(message: str, sender: str) -> str:
    """Generate deterministic finding ID from message content."""
    hash_input = f"improvement:{sender}:{message}"
    return f"imp_intent_{hashlib.sha256(hash_input.encode()).hexdigest()[:12]}"


def execute_improvement(dae: Any, intent: Any) -> str:
    """Route IMPROVEMENT intent (codebase self-improvement requests).

    Creates an ImprovementJob with dry_run=True and returns advisory.

    WSP 97 Truth Boundary:
      - Classifies the improvement request
      - Creates ImprovementJob (dry_run=True, not executed)
      - Returns advisory with job_id
      - Does NOT execute autonomous repairs
      - Does NOT queue for worker dispatch
      - Does NOT claim repair capability exists

    Supported improvement types:
      - WSP violations (fix violation, fix wsp, wsp violation)
      - Module repairs (repair module, duplicate module, module cleanup)
      - Test hygiene (stale test)
      - Code drift (fix drift, codebase improvement)
      - FMAS scans (run fmas repair, fmas scan)
      - Orphan connections (orphan capability)
      - Documentation hygiene (modlog, readme)
    """
    global _LAST_IMPROVEMENT_JOB

    msg = intent.raw_message or ""
    msg_lower = msg.lower().strip()
    sender = getattr(intent, "sender", "unknown")

    # Classify improvement sub-type
    improvement_type_str = _classify_improvement_type(msg_lower)
    improvement_type_enum = _IMPROVEMENT_TYPE_MAP.get(
        improvement_type_str, ImprovementType.FMAS_SCAN
    )

    # Extract scope information from message
    module_path = _extract_module_path(msg)
    wsp_refs = _extract_wsp_refs(msg)

    # Build scope
    scope = ImprovementScope(
        module_path=module_path,
        wsp_refs=wsp_refs,
    )

    # Derive risk level
    risk_level = _derive_risk_level(improvement_type_str, msg_lower)

    # Generate finding ID
    finding_id = _generate_finding_id(msg, sender)

    # Create ImprovementJob (always dry_run=True)
    job = create_improvement_job(
        finding_id=finding_id,
        improvement_type=improvement_type_enum,
        scope=scope,
        risk_level=risk_level,
        requested_by=sender,
        payload={
            "raw_message": msg,
            "extracted_task": getattr(intent, "extracted_task", ""),
            "source": "openclaw_improvement_intent",
        },
    )

    # Store for test inspection (NOT a production queue)
    _LAST_IMPROVEMENT_JOB = job

    logger.info(
        "[OPENCLAW-DAE] [IMPROVEMENT] ImprovementJob created: "
        "job_id=%s type=%s risk=%s dry_run=%s sender=%s",
        job.job_id,
        improvement_type_enum.value,
        risk_level.value,
        job.dry_run,
        sender,
    )

    # WSP 97: Truthful advisory response - no repair execution claims
    return (
        f"**Improvement Intent Recognized**\n\n"
        f"- **Type**: `{improvement_type_str}`\n"
        f"- **Request**: {intent.extracted_task or intent.raw_message}\n\n"
        f"**ImprovementJob Created**\n\n"
        f"- **Job ID**: `{job.job_id}`\n"
        f"- **Improvement Type**: `{improvement_type_enum.value}`\n"
        f"- **Risk Level**: `{risk_level.value}`\n"
        f"- **Dry Run**: `True`\n"
        f"- **Status**: `{job.status.value}` (created, not executed)\n\n"
        f"**WSP 97 Truth Boundary**\n\n"
        f"This job was created but NOT executed. Autonomous codebase repair "
        f"and worker dispatch are not implemented in this slice. "
        f"The job exists for future FMAS integration.\n\n"
        f"_WSP 97: AI surfaces improvement needs. Humans decide execution._"
    )



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
        return query_decisions(dae, topic)

    # Past work query: "show past work on X" / "what was I working on X"
    # Narrow: requires "past work" or "working on" phrases with topic
    past_work_match = re.search(
        r"(?:show|list|find)\s+(?:past|prior|previous)\s+work\s+(?:on|about|for)\s+(.+)",
        normalized,
    )
    if past_work_match:
        topic = past_work_match.group(1).strip().rstrip("?")
        return query_past_work(dae, topic)

    # "what was I working on X" variant
    working_on_match = re.search(
        r"what\s+(?:was|were)\s+(?:i|we|you)\s+working\s+on\s*(.*)$",
        normalized,
    )
    if working_on_match:
        topic = working_on_match.group(1).strip().rstrip("?") or None
        # Normalize time-only qualifiers to None (not a topic)
        topic = normalize_time_qualifier(topic)
        return query_past_work(dae, topic)

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
        return query_unresolved_work(dae)

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
        return query_recent_sessions(dae)

    # Gateway Continuity Layer queries
    # "show continuity <id>" / "continuity status <id>"
    continuity_id_match = re.search(
        r"(?:show|get|lookup)\s+continuity\s+([a-f0-9]{8,16})",
        normalized,
    )
    if continuity_id_match:
        return query_continuity_status(dae, continuity_id_match.group(1))

    # "show cross-surface activity" / "cross-surface work"
    if re.search(r"cross[- ]?surface\s+(?:activity|work|handoff)", normalized):
        return query_cross_surface_activity(dae)

    # "what is my continuity id" / "show my continuity"
    if re.search(r"(?:my|current)\s+continuity(?:\s+id)?", normalized):
        return query_current_continuity(dae)

    return None


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


# -----------------------------------------------------------------------------
# Schedule Command Handlers
# -----------------------------------------------------------------------------


def _try_schedule_command(dae: Any, raw_message: str) -> Optional[str]:
    """
    Detect and handle schedule management commands.

    Supported patterns:
    - "schedule self research daily" / "run self research daily" -> add schedule
    - "list schedules" / "show schedules" -> list all schedules
    - "show due schedules" -> show currently due schedules
    - "remove schedule <id>" -> remove a schedule
    - "disable schedule <id>" -> disable a schedule
    - "enable schedule <id>" -> enable a schedule

    IMPORTANT: Only matches explicit schedule-related commands.
    """
    normalized = raw_message.lower().strip()

    # List schedules: "list schedules" / "show schedules" / "show my schedules"
    if re.search(r"\b(list|show)\s+(my\s+)?schedules?\b", normalized):
        return _list_schedules()

    # Due schedules: "show due schedules" / "what schedules are due"
    if re.search(r"\b(due|pending)\s+schedules?\b", normalized) or re.search(
        r"\bschedules?\s+(that\s+are\s+)?due\b", normalized
    ):
        return _show_due_schedules()

    # Remove schedule: "remove schedule <id>" / "delete schedule <id>"
    remove_match = re.search(
        r"\b(remove|delete)\s+schedule\s+([a-f0-9]{12})\b", normalized
    )
    if remove_match:
        return _remove_schedule(remove_match.group(2))

    # Disable schedule: "disable schedule <id>"
    disable_match = re.search(r"\bdisable\s+schedule\s+([a-f0-9]{12})\b", normalized)
    if disable_match:
        return _toggle_schedule(disable_match.group(1), enabled=False)

    # Enable schedule: "enable schedule <id>"
    enable_match = re.search(r"\benable\s+schedule\s+([a-f0-9]{12})\b", normalized)
    if enable_match:
        return _toggle_schedule(enable_match.group(1), enabled=True)

    # Add schedule: "schedule X daily" / "run X daily" (must include cadence)
    # Must match schedule patterns from ScheduleParser
    add_match = re.search(
        r"\b(schedule|run)\s+(.+?\s+(daily|nightly|morning|evening))\b",
        normalized,
    )
    if add_match:
        phrase = add_match.group(2).strip()
        return _add_schedule(phrase)

    return None


def _list_schedules() -> str:
    """List all configured schedules."""
    try:
        from modules.infrastructure.idle_automation.src.schedule_evaluator import (
            ScheduleEvaluator,
        )

        evaluator = ScheduleEvaluator()
        schedules = evaluator.list_schedules()

        if not schedules:
            return (
                "**No schedules configured.**\n\n"
                "Add a schedule with: `schedule self research daily`\n"
                "Supported: self research, queue audit, grant watchlist\n"
                "Cadences: daily, nightly, morning, evening"
            )

        parts = [f"**{len(schedules)} schedule(s) configured:**\n"]
        for spec in schedules:
            status = "enabled" if spec.enabled else "DISABLED"
            last_run = spec.last_run[:10] if spec.last_run else "never"
            parts.append(f"- `{spec.id}` [{status}]")
            parts.append(f"  - Phrase: {spec.phrase}")
            parts.append(f"  - Routine: {spec.routine} | Cadence: {spec.cadence}")
            parts.append(f"  - Last run: {last_run}")

        return "\n".join(parts)
    except Exception as exc:
        return f"**Error listing schedules:** {exc}"


def _show_due_schedules() -> str:
    """Show schedules that are currently due."""
    try:
        from modules.infrastructure.idle_automation.src.schedule_evaluator import (
            ScheduleEvaluator,
        )

        evaluator = ScheduleEvaluator()
        due = evaluator.get_due_schedules()

        if not due:
            return "**No schedules currently due.**\n\nSchedules run during idle automation cycles."

        parts = [f"**{len(due)} schedule(s) due:**\n"]
        for spec in due:
            parts.append(f"- `{spec.id}`: {spec.routine} ({spec.cadence})")
            parts.append(f"  - Phrase: {spec.phrase}")

        return "\n".join(parts)
    except Exception as exc:
        return f"**Error checking due schedules:** {exc}"


def _add_schedule(phrase: str) -> str:
    """Add a new schedule from a natural-language phrase."""
    try:
        from modules.infrastructure.idle_automation.src.schedule_evaluator import (
            ScheduleEvaluator,
            ScheduleParser,
            get_supported_phrases,
        )

        # Validate first
        parsed = ScheduleParser.parse(phrase)
        if parsed is None:
            examples = get_supported_phrases()[:4]
            return (
                f"**Could not parse schedule phrase:** `{phrase}`\n\n"
                "**Supported formats:**\n"
                + "\n".join(f"- `{ex}`" for ex in examples)
            )

        evaluator = ScheduleEvaluator()
        spec = evaluator.add_schedule(phrase)

        if spec:
            return (
                f"**Schedule added:** `{spec.id}`\n"
                f"- Phrase: {spec.phrase}\n"
                f"- Routine: {spec.routine}\n"
                f"- Cadence: {spec.cadence}\n\n"
                "Schedule will run during next idle automation cycle when due."
            )
        return "**Failed to add schedule.**"
    except Exception as exc:
        return f"**Error adding schedule:** {exc}"


def _remove_schedule(schedule_id: str) -> str:
    """Remove a schedule by ID."""
    try:
        from modules.infrastructure.idle_automation.src.schedule_evaluator import (
            ScheduleEvaluator,
        )

        evaluator = ScheduleEvaluator()
        if evaluator.remove_schedule(schedule_id):
            return f"**Schedule removed:** `{schedule_id}`"
        return f"**Schedule not found:** `{schedule_id}`"
    except Exception as exc:
        return f"**Error removing schedule:** {exc}"


def _toggle_schedule(schedule_id: str, enabled: bool) -> str:
    """Enable or disable a schedule."""
    try:
        from modules.infrastructure.idle_automation.src.schedule_evaluator import (
            ScheduleEvaluator,
        )

        evaluator = ScheduleEvaluator()
        if evaluator.set_enabled(schedule_id, enabled):
            status = "enabled" if enabled else "disabled"
            return f"**Schedule {status}:** `{schedule_id}`"
        return f"**Schedule not found:** `{schedule_id}`"
    except Exception as exc:
        return f"**Error updating schedule:** {exc}"
