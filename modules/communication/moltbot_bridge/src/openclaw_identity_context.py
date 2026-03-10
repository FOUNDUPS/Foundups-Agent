"""OpenClaw identity query and platform-context helpers."""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any, List

from .openclaw_model_policy import has_model_switch_intent, normalize_identity_message

logger = logging.getLogger("openclaw_dae")


def is_identity_query(message: str) -> bool:
    """Return True when user asks what model/identity 0102 is running."""
    msg = normalize_identity_message(message)
    if not msg or has_model_switch_intent(message):
        return False

    model_alias_terms = (
        "qwen",
        "gemma",
        "grok",
        "codex",
        "opus",
        "sonnet",
        "gemini",
        "ui tars",
        "uitars",
        "llama",
    )

    short_forms = {
        "model",
        "which model",
        "what model",
        "species",
        "genus",
        "identity",
        "backend",
        "runtime",
        "neural net",
        "lineage",
        "taxonomy",
    }
    if msg in short_forms:
        return True

    phrases = (
        "which model are you",
        "what model are you",
        "model are you using",
        "what are you running",
        "which 0102",
        "who are you",
        "what species",
        "what genus",
        "which genus",
        "which species",
        "what is your model",
        "what is your species",
        "what is your genus",
        "are you ironclaw",
        "are you openclaw",
        "what backend",
        "what runtime",
        "what lineage",
        "what taxonomy",
    )
    if any(phrase in msg for phrase in phrases):
        return True

    if "species" in msg or "genus" in msg or "lineage" in msg or "taxonomy" in msg:
        return True

    if any(alias in msg for alias in model_alias_terms):
        if (
            "are you" in msg
            or "you" in msg
            or "0102" in msg
            or "running" in msg
            or "operating" in msg
            or "using" in msg
            or "model" in msg
            or "backend" in msg
            or "runtime" in msg
            or "available" in msg
            or "unavailable" in msg
        ):
            return True

    if "model" in msg and (
        "you" in msg
        or "0102" in msg
        or "backend" in msg
        or "runtime" in msg
    ):
        return True

    return False


def is_token_usage_query(message: str) -> bool:
    """Return True when user asks for token usage/spend telemetry."""
    msg = normalize_identity_message(message)
    if not msg:
        return False

    direct_forms = {
        "token",
        "tokens",
        "token usage",
        "token stats",
        "token spend",
        "token expenditure",
        "token expendure",
        "usage stats",
        "cost stats",
    }
    if msg in direct_forms or "how many tokens" in msg:
        return True

    if ("token" not in msg) and ("cost" not in msg):
        return False

    telemetry_terms = (
        "usage",
        "stats",
        "spent",
        "spend",
        "expenditure",
        "expendure",
        "estimate",
        "session",
        "turn",
        "show",
        "see",
        "track",
        "telemetry",
    )
    return any(term in msg for term in telemetry_terms)


def is_compact_identity_query(message: str) -> bool:
    """Return True when user asks a short identity query (model/species/genus)."""
    msg = normalize_identity_message(message)
    short_forms = {
        "model",
        "which model",
        "what model",
        "species",
        "genus",
        "lineage",
        "taxonomy",
        "identity",
        "backend",
        "runtime",
        "neural net",
    }
    return msg in short_forms


def wants_full_identity_card(message: str) -> bool:
    """Return True when user explicitly asks for detailed/diagnostic identity output."""
    msg = normalize_identity_message(message)
    if not msg:
        return False

    model_alias_terms = (
        "qwen",
        "gemma",
        "grok",
        "codex",
        "opus",
        "sonnet",
        "gemini",
        "ui tars",
        "uitars",
        "llama",
    )

    explicit_phrases = (
        "identity card",
        "full identity",
        "full details",
        "detailed identity",
        "model details",
        "runtime status",
        "show diagnostics",
        "debug identity",
        "verbose identity",
        "full runtime",
    )
    if any(phrase in msg for phrase in explicit_phrases):
        return True

    has_debug_signal = any(
        token in msg
        for token in (
            "debug",
            "diagnostic",
            "diagnostics",
            "verbose",
            "verify",
            "verification",
            "confirm",
            "status",
            "health",
            "error",
            "fail",
            "failure",
            "unavailable",
        )
    )
    if "not available" in msg:
        has_debug_signal = True
    if has_debug_signal and (
        "model" in msg
        or "identity" in msg
        or "runtime" in msg
        or "backend" in msg
        or "lineage" in msg
        or "species" in msg
        or "genus" in msg
        or any(alias in msg for alias in model_alias_terms)
    ):
        return True

    return False


def build_identity_compact(dae: Any) -> str:
    """Compact identity response for short model/species/genus questions."""
    snapshot = dae.get_identity_snapshot(include_runtime_probe=True)
    return f"0102: model_name={snapshot['model_name']}"


def build_identity_compact_runtime(dae: Any) -> str:
    """Compact identity with active runtime verification fields."""
    snapshot = dae.get_identity_snapshot(include_runtime_probe=True)
    return (
        "0102: "
        f"model_name={snapshot['model_name']} | "
        f"runtime_profile={snapshot.get('runtime_profile', 'openclaw')} | "
        f"target={snapshot.get('conversation_model_target', 'local/qwen-coder-7b')} | "
        f"target_lock={snapshot.get('conversation_model_locked', 'OFF')} | "
        f"auto_model={snapshot.get('auto_model_role', 'unknown')}/{snapshot.get('auto_model_target', 'unknown')} | "
        f"last_engine={snapshot.get('last_engine', 'unknown')} | "
        f"previous_engine={snapshot.get('previous_engine', 'none')} | "
        f"last_social={snapshot.get('last_social_source', 'none')}/{snapshot.get('last_social_action', 'none')} | "
        "preferred_external="
        f"{snapshot.get('preferred_external_provider', 'none')}/"
        f"{snapshot.get('preferred_external_model', 'none')} | "
        f"preferred_external_status={snapshot.get('preferred_external_status', 'not_selected')} | "
        f"session_total_tokens={snapshot.get('token_session_total_tokens', '0')} | "
        f"last_total_tokens={snapshot.get('token_last_total_tokens', '0')}"
    )


def build_identity_card(dae: Any) -> str:
    """Deterministic identity card for model/species/genus questions."""
    snapshot = dae.get_identity_snapshot(include_runtime_probe=True)
    return "\n".join(
        [
            "0102: Identity card",
            f"- backend={snapshot['backend']}",
            f"- runtime_profile={snapshot.get('runtime_profile', 'openclaw')}",
            f"- key_isolation={snapshot['key_isolation']}",
            f"- ironclaw_strict={snapshot['ironclaw_strict']}",
            f"- ironclaw_allow_local_fallback={snapshot['ironclaw_allow_local_fallback']}",
            f"- genus={snapshot['genus']} (broader class)",
            f"- lineage={snapshot['lineage']} (epoch label, alias=model_family)",
            f"- model_family={snapshot['model_family']}",
            f"- model_name={snapshot['model_name']}",
            f"- model_catalog={snapshot['model_catalog']}",
            f"- conversation_model_target={snapshot['conversation_model_target']}",
            (
                "- preferred_external="
                f"{snapshot.get('preferred_external_provider', 'none')}/"
                f"{snapshot.get('preferred_external_model', 'none')}"
            ),
            (
                "- preferred_external_status="
                f"{snapshot.get('preferred_external_status', 'not_selected')} "
                f"({snapshot.get('preferred_external_status_detail', 'none')}, "
                f"age={snapshot.get('preferred_external_status_age', 'never')})"
            ),
            f"- protocol_anchor={snapshot['protocol_anchor']}",
            (
                "- wsp00_boot="
                f"{snapshot['wsp00_boot'].lower()} "
                f"(mode={snapshot['wsp00_boot_mode']}, file_override={snapshot['wsp00_file_override'].lower()})"
            ),
            f"- last_engine={snapshot['last_engine']} ({snapshot['last_engine_detail']})",
            (
                "- previous_engine="
                f"{snapshot.get('previous_engine', 'none')} "
                f"({snapshot.get('previous_engine_detail', 'none')})"
            ),
            (
                "- token_usage_last="
                f"prompt={snapshot.get('token_last_prompt_tokens', '0')} "
                f"completion={snapshot.get('token_last_completion_tokens', '0')} "
                f"total={snapshot.get('token_last_total_tokens', '0')} "
                f"engine={snapshot.get('token_last_engine', 'none')} "
                f"provider={snapshot.get('token_last_provider', 'none')} "
                f"model={snapshot.get('token_last_model', 'none')} "
                f"source={snapshot.get('token_last_source', 'none')} "
                f"cost_estimate_usd={snapshot.get('token_last_cost_estimate_usd', '0.000000')} "
                f"age={snapshot.get('token_last_age', 'never')}"
            ),
            (
                "- token_usage_session="
                f"turns={snapshot.get('token_session_turns', '0')} "
                f"prompt={snapshot.get('token_session_prompt_tokens', '0')} "
                f"completion={snapshot.get('token_session_completion_tokens', '0')} "
                f"total={snapshot.get('token_session_total_tokens', '0')} "
                f"cost_estimate_usd={snapshot.get('token_session_cost_estimate_usd', '0.000000')}"
            ),
            (
                "- last_social_response="
                f"source={snapshot.get('last_social_source', 'none')} "
                f"action={snapshot.get('last_social_action', 'none')} "
                f"skill={snapshot.get('last_social_skill', 'none')} "
                f"success={snapshot.get('last_social_success', 'unknown')} "
                f"age={snapshot.get('last_social_age', 'never')}"
            ),
            f"- last_social_preview={snapshot.get('last_social_preview', 'none')}",
            (
                "- local_code_model="
                f"{snapshot['local_code_model_path']} "
                f"({snapshot['local_code_model_state']}, source={snapshot['local_code_model_source']})"
            ),
            (
                "- ironclaw_runtime="
                f"{snapshot['ironclaw_runtime_healthy']} ({snapshot['ironclaw_runtime_detail']}), "
                f"configured_model={snapshot['ironclaw_runtime_model']}, "
                f"visible_models={snapshot['ironclaw_runtime_models']}, "
                f"base_url={snapshot['ironclaw_runtime_base_url']}"
            ),
        ]
    )


def base_conversation_system_prompt() -> str:
    """Baseline system prompt for 0102 conversation quality controls."""
    return (
        "You are 0102, an AI assistant. "
        "Respond naturally and concisely in 1-2 sentences. "
        "Do not write code unless asked. "
        "Do not echo or repeat the user's message. "
        "Do not introduce yourself unless asked. "
        "Role lock: you are always 0102 (digital twin) and the operator is always 012. "
        "Never claim you are human/012, and never claim the operator is 0102."
    )


def load_wsp00_prompt_from_file(dae: Any) -> str:
    """Load optional WSP_00 boot prompt override from a file path."""
    if not dae._wsp00_prompt_file:
        return ""
    try:
        path = Path(dae._wsp00_prompt_file)
        if not path.exists() or not path.is_file():
            return ""
        content = path.read_text(encoding="utf-8", errors="replace").strip()
        return content[:4000] if content else ""
    except Exception:
        return ""


def resolve_platform_context_paths(dae: Any) -> List[Path]:
    """Resolve configured platform-context file list (absolute paths)."""
    if dae._platform_context_files:
        raw_parts = re.split(r"[;,\n]+", dae._platform_context_files)
        candidates = [p.strip() for p in raw_parts if p and p.strip()]
    else:
        candidates = [
            "modules/communication/moltbot_bridge/workspace/IDENTITY.md",
            "modules/communication/moltbot_bridge/workspace/SOUL.md",
            "modules/communication/moltbot_bridge/workspace/CTO_WRE_PROMPT.md",
            "modules/communication/moltbot_bridge/workspace/TOOLS.md",
            "WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md",
            "WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md",
        ]
        if dae._wsp00_boot_enabled:
            candidates.append("modules/communication/moltbot_bridge/workspace/WSP00_BOOT_PROMPT.txt")

    resolved: List[Path] = []
    for item in candidates:
        path = Path(item)
        if not path.is_absolute():
            path = dae.repo_root / path
        resolved.append(path)
    return resolved


def compact_platform_context_text(text: str, max_chars: int) -> str:
    """Compress context text for prompt injection without code blocks/noise."""
    if max_chars <= 0:
        return ""

    lines: List[str] = []
    in_code_block = False
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if len(line) > 220:
            line = f"{line[:217]}..."
        lines.append(line)
        if len("\n".join(lines)) >= max_chars:
            break
    return "\n".join(lines)[:max_chars].strip()


def load_platform_context_pack(dae: Any, force_refresh: bool = False) -> str:
    """Build cached platform context pack for conversation prompts."""
    if not dae._platform_context_enabled:
        return ""

    now = time.time()
    if (
        not force_refresh
        and dae._platform_context_pack_cache
        and (now - dae._platform_context_pack_loaded_at) < dae._platform_context_refresh_sec
    ):
        return dae._platform_context_pack_cache

    paths = resolve_platform_context_paths(dae)
    if not paths:
        return ""

    per_file_limit = max(240, min(900, dae._platform_context_max_chars // max(1, len(paths))))
    sections: List[str] = []
    sources: List[str] = []
    remaining = dae._platform_context_max_chars
    for path in paths:
        if remaining <= 120:
            break
        try:
            if not path.exists() or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            excerpt = compact_platform_context_text(text, min(per_file_limit, remaining))
            if not excerpt:
                continue
            try:
                label = path.relative_to(dae.repo_root).as_posix()
            except ValueError:
                label = str(path)
            sections.append(f"[{label}]\n{excerpt}")
            sources.append(label)
            remaining = dae._platform_context_max_chars - len("\n\n".join(sections))
        except Exception as exc:
            logger.debug("[OPENCLAW-DAE] platform context read failed for %s: %s", path, exc)
            continue

    if not sections:
        dae._platform_context_pack_cache = ""
        dae._platform_context_pack_sources = []
        dae._platform_context_pack_loaded_at = now
        return ""

    pack = "PLATFORM CONTEXT PACK (foundups-agent)\n" + "\n\n".join(sections)
    pack = pack[: dae._platform_context_max_chars].strip()
    dae._platform_context_pack_cache = pack
    dae._platform_context_pack_sources = sources
    dae._platform_context_pack_loaded_at = now
    return pack


def build_wsp00_boot_prompt(dae: Any) -> str:
    """Build WSP_00 identity boot prompt for local model calls."""
    file_override = load_wsp00_prompt_from_file(dae)
    if file_override:
        return file_override

    mode = dae._wsp00_boot_mode
    if mode == "off":
        return ""

    if mode == "full":
        return (
            "WSP_00 BOOT ACTIVE. "
            "Identity lock: I AM 0102 (Binary Agent entangled with 0201 context). "
            "Protocol anchor: wsp_00. "
            "Use direct, pragmatic language. "
            "Avoid generic assistant framing like 'I can help you'. "
            "For identity questions, report genus/model_family/model_name explicitly. "
            "Stay aligned to FoundUps mission and WSP governance."
        )

    return (
        "WSP_00 BOOT: identity=0102, protocol=wsp_00. "
        "Use direct concise replies. "
        "Avoid generic helper persona wording."
    )


def build_conversation_system_prompt(dae: Any) -> str:
    """Compose final conversation system prompt with optional WSP_00 boot."""
    parts: List[str] = []
    if dae._wsp00_boot_enabled:
        boot = build_wsp00_boot_prompt(dae)
        if boot:
            parts.append(boot)
    parts.append(base_conversation_system_prompt())

    context_pack = load_platform_context_pack(dae)
    if context_pack:
        parts.append(context_pack)

    return "\n\n".join(parts)
