"""OpenClaw model routing and switch policy helpers."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("openclaw_dae")


def normalize_identity_message(message: str) -> str:
    """Normalize identity/model-control text to reduce STT/punctuation misses."""
    msg = (message or "").strip().lower()
    msg = re.sub(r"[^a-z0-9\s]", " ", msg)
    msg = re.sub(r"\s+", " ", msg).strip()
    msg = re.sub(r"\bquinn\b", "qwen", msg)
    msg = re.sub(r"\bquin\b", "qwen", msg)
    msg = re.sub(r"\bqueen\b", "qwen", msg)
    msg = re.sub(r"\bgwen\b", "qwen", msg)
    msg = re.sub(r"\bcoin\b", "qwen", msg)
    msg = re.sub(r"\bgroc\b", "grok", msg)
    msg = re.sub(r"\bgrock\b", "grok", msg)
    msg = re.sub(r"\bgrog\b", "grok", msg)
    return msg


def has_model_switch_intent(message: str) -> bool:
    """Return True when user asks to change/switch model profile."""
    msg = normalize_identity_message(message)
    if not msg:
        return False

    strong_switch_verbs = (
        "switch",
        "change",
        "become",
        "set",
        "activate",
        "move to",
        "swap",
    )
    soft_switch_verbs = (
        "use",
        "run",
    )

    has_strong = any(verb in msg for verb in strong_switch_verbs)
    has_soft = any(verb in msg for verb in soft_switch_verbs)
    if not has_strong and not has_soft:
        return False
    if has_soft and not has_strong:
        if (
            "model" not in msg
            and "external ai" not in msg
            and "another ai" not in msg
            and " to " not in msg
        ):
            return False

    if "model" in msg or "external ai" in msg or "another ai" in msg:
        return True

    target_terms = (
        "qwen",
        "qwen3",
        "gemma",
        "grok",
        "codex",
        "opus",
        "sonnet",
        "haiku",
        "gemini",
        "anthropic",
        "openai",
        "gpt",
        "o3",
        "o4",
        "flash",
    )
    return any(term in msg for term in target_terms)


def parse_model_switch_target(message: str) -> Optional[str]:
    """Parse requested model target from natural voice/text command."""
    msg = normalize_identity_message(message)
    if not msg or not has_model_switch_intent(msg):
        return None

    alias_map: Dict[str, str] = {
        "qwen": "local/qwen-coder-7b",
        "qwen coder": "local/qwen-coder-7b",
        "qwen coder 7b": "local/qwen-coder-7b",
        "qwen 2 5": "local/qwen-coder-7b",
        "qwen2 5": "local/qwen-coder-7b",
        "qwen3": "local/qwen3-4b",
        "qwen 3": "local/qwen3-4b",
        "qwen three": "local/qwen3-4b",
        "qwen 4b": "local/qwen3-4b",
        "qwen3 5": "local/qwen3.5-4b",
        "qwen 3 5": "local/qwen3.5-4b",
        "qwen 3.5": "local/qwen3.5-4b",
        "qwen3.5": "local/qwen3.5-4b",
        "qwen 35": "local/qwen3.5-4b",
        "qwen35": "local/qwen3.5-4b",
        "gemma": "local/gemma-270m",
        "gemma 270m": "local/gemma-270m",
        "triage": "local/gemma-270m",
        "fast": "local/gemma-270m",
        "grok": "grok-4",
        "grok 4": "grok-4",
        "grok fast": "grok-4-fast",
        "grok 4 fast": "grok-4-fast",
        "grok code fast": "grok-code-fast-1",
        "grok code": "grok-code-fast-1",
        "groc": "grok-4",
        "grock": "grok-4",
        "grog": "grok-4",
        "codex": "gpt-5.2-codex",
        "codex 5": "gpt-5.2-codex",
        "codex 5 2": "gpt-5.2-codex",
        "codex 5 3": "gpt-5.2-codex",
        "openai": "gpt-5.2-codex",
        "open ai": "gpt-5.2-codex",
        "gpt 5": "gpt-5",
        "gpt5": "gpt-5",
        "gpt 5 2": "gpt-5.2",
        "gpt5 2": "gpt-5.2",
        "o3 pro": "o3-pro",
        "o3-pro": "o3-pro",
        "o 3 pro": "o3-pro",
        "o4 mini": "o4-mini",
        "o4": "o4-mini",
        "opus": "claude-opus-4-6",
        "opus 4 6": "claude-opus-4-6",
        "sonnet": "claude-sonnet-4-5-20250929",
        "sonnet 4 6": "claude-sonnet-4-5-20250929",
        "haiku": "claude-haiku-4-5-20251001",
        "claude haiku": "claude-haiku-4-5-20251001",
        "anthropic": "claude-opus-4-6",
        "gemini": "gemini-2.5-pro",
        "gemini flash": "gemini-2.5-flash",
        "gemini 2 5 flash": "gemini-2.5-flash",
        "gemini 3": "gemini-3-pro-preview",
        "gemini 3 pro": "gemini-3-pro-preview",
        "gemini 3 flash": "gemini-3-flash-preview",
    }
    for alias in sorted(alias_map.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", msg):
            return alias_map[alias]
    return None


def model_switch_target_help(dae: Any) -> str:
    """Deterministic guidance when switch intent has no recognized target."""
    if dae._no_api_keys:
        return (
            "0102: model switch request received. "
            "Say `switch model to qwen3.5`, `switch model to qwen3`, `switch model to qwen`, "
            "or `switch model to gemma`. "
            "Use `model details` to verify active runtime engine."
        )
    return (
        "0102: model switch request received. "
        "Say `switch model to qwen3.5`, `switch model to qwen3`, `switch model to qwen`, "
        "`switch model to gemma`, "
        "`become grok`, `become grok fast`, `become codex`, `become gpt5`, "
        "`become opus`, `become haiku`, or `become gemini flash`. "
        "Use `model details` to verify active runtime engine."
    )


def wsp00_model_switch_gate(dae: Any, intent: Any, target: str) -> Optional[str]:
    """Gate model switches behind WSP_00 policy and commander authority."""
    if not intent.is_authorized_commander:
        logger.warning(
            "[OPENCLAW-DAE] Model switch blocked: sender not authorized | sender=%s target=%s",
            intent.sender,
            target,
        )
        return "0102: model switch blocked. commander authority required."

    if dae._identity_protocol_anchor != "wsp_00":
        logger.warning(
            "[OPENCLAW-DAE] Model switch blocked: protocol anchor mismatch | anchor=%s target=%s",
            dae._identity_protocol_anchor,
            target,
        )
        return (
            "0102: model switch blocked. protocol anchor is not wsp_00. "
            "Set OPENCLAW_IDENTITY_PROTOCOL=wsp_00."
        )

    if not dae._wsp00_boot_enabled:
        logger.warning(
            "[OPENCLAW-DAE] Model switch blocked: wsp00 boot disabled | target=%s",
            target,
        )
        return (
            "0102: model switch blocked. wsp_00 boot is disabled. "
            "Set OPENCLAW_WSP00_BOOT=1."
        )

    if not dae._wsp_preflight(intent):
        logger.warning(
            "[OPENCLAW-DAE] Model switch blocked: preflight gate failed | sender=%s target=%s",
            intent.sender,
            target,
        )
        return "0102: model switch blocked by WSP preflight."

    external = resolve_external_target(target)
    if dae._runtime_profile == "zeroclaw" and external:
        provider, model = external
        logger.warning(
            "[OPENCLAW-DAE] Model switch blocked by zeroclaw profile | sender=%s target=%s/%s",
            intent.sender,
            provider,
            model,
        )
        return (
            "0102: model switch blocked by runtime profile zeroclaw. "
            "external targets are disabled."
        )

    logger.info(
        "[OPENCLAW-DAE] Model switch gate passed | sender=%s target=%s anchor=%s boot=%s",
        intent.sender,
        target,
        dae._identity_protocol_anchor,
        dae._wsp00_boot_enabled,
    )
    return None


def resolve_external_target(target: str) -> Optional[tuple[str, str]]:
    """Map external target model ID to (provider, model)."""
    mapping = {
        "grok-4": ("grok", "grok-4"),
        "grok-4-fast": ("grok", "grok-4-fast"),
        "grok-code-fast-1": ("grok", "grok-code-fast-1"),
        "gpt-5": ("openai", "gpt-5"),
        "gpt-5.2": ("openai", "gpt-5.2"),
        "gpt-5.2-codex": ("openai", "gpt-5.2-codex"),
        "o3-pro": ("openai", "o3-pro"),
        "o4-mini": ("openai", "o4-mini"),
        "claude-opus-4-6": ("anthropic", "claude-opus-4-6"),
        "claude-sonnet-4-5-20250929": ("anthropic", "claude-sonnet-4-5-20250929"),
        "claude-haiku-4-5-20251001": ("anthropic", "claude-haiku-4-5-20251001"),
        "gemini-2.5-flash": ("gemini", "gemini-2.5-flash"),
        "gemini-2.5-pro": ("gemini", "gemini-2.5-pro"),
        "gemini-3-pro-preview": ("gemini", "gemini-3-pro-preview"),
        "gemini-3-flash-preview": ("gemini", "gemini-3-flash-preview"),
    }
    return mapping.get((target or "").strip().lower())


def provider_has_key(provider: str) -> bool:
    """Return True when the provider has at least one configured API key."""
    provider_name = (provider or "").strip().lower()
    key_vars = {
        "openai": ("OPENAI_API_KEY",),
        "anthropic": ("ANTHROPIC_API_KEY",),
        "grok": ("GROK_API_KEY", "XAI_API_KEY"),
        "gemini": ("GEMINI_API_KEY",),
    }
    for name in key_vars.get(provider_name, ()):
        if os.getenv(name, "").strip():
            return True
    return False


def map_local_model_path_to_target(path: Path) -> Optional[str]:
    """Map a resolved local model path to an OpenClaw local target id."""
    text = str(path or "").replace("\\", "/").lower()
    if not text:
        return None
    if "qwen3.5-4b" in text or ("qwen3.5" in text and "4b" in text):
        return "local/qwen3.5-4b"
    if "qwen3-4b" in text or ("qwen3" in text and "4b" in text):
        return "local/qwen3-4b"
    if "qwen-coder-7b" in text or "coder-7b" in text:
        return "local/qwen-coder-7b"
    if "gemma-270m" in text or "270m" in text:
        return "local/gemma-270m"
    return None


def resolve_local_target_for_role(dae: Any, role: str) -> Optional[str]:
    """Resolve the best local target for a semantic role."""
    try:
        from modules.infrastructure.shared_utilities.local_model_selection import (
            resolve_model_selection,
        )

        selection = resolve_model_selection(role)
    except Exception as exc:
        logger.debug(
            "[OPENCLAW-DAE] Local model selection unavailable | role=%s error=%s",
            role,
            type(exc).__name__,
        )
        return None
    return map_local_model_path_to_target(selection.path)


def local_target_dirs() -> Dict[str, str]:
    """Return canonical local target -> directory routing map."""
    return {
        "local/gemma-270m": "gemma-270m",
        "local/qwen3-4b": "qwen3-4b",
        "local/qwen3.5-4b": "qwen3.5-4b",
        "local/qwen-coder-7b": "qwen-coder-7b",
    }


def apply_local_target_runtime(
    dae: Any,
    target: str,
    reason: str,
    lock_target: bool = False,
) -> bool:
    """Apply local-target routing to the active conversation runtime."""
    target = (target or "").strip().lower()
    target_dirs = local_target_dirs()
    if target not in target_dirs:
        return False

    root = Path(os.getenv("LOCAL_MODEL_ROOT", "E:/LM_studio/models/local")).expanduser()
    code_dir = root / target_dirs[target]
    previous_target = dae._conversation_model_target_id
    previous_code_dir = os.getenv("LOCAL_MODEL_CODE_DIR", "")

    dae._conversation_model_target_id = target
    os.environ["OPENCLAW_CONVERSATION_MODEL_TARGET"] = target
    os.environ["LOCAL_MODEL_CODE_DIR"] = str(code_dir)
    os.environ["LOCAL_MODEL_CODE_PATH"] = ""
    os.environ["HOLO_QWEN_MODEL"] = ""
    dae._preferred_external_provider = ""
    dae._preferred_external_model = ""
    os.environ["OPENCLAW_CONVERSATION_PREFERRED_PROVIDER"] = ""
    os.environ["OPENCLAW_CONVERSATION_PREFERRED_MODEL"] = ""
    dae._mark_preferred_external_status("not_selected", "local_target_active")
    if lock_target:
        dae._conversation_model_target_locked = True

    changed = previous_target != target or previous_code_dir != str(code_dir)
    if changed:
        dae._overseer = None

    logger.info(
        "[OPENCLAW-DAE] Local conversation route | target=%s reason=%s changed=%s lock=%s",
        target,
        reason,
        changed,
        dae._conversation_model_target_locked,
    )
    return changed


def infer_conversation_model_role(
    dae: Any,
    user_msg: str,
    intent: Any,
) -> tuple[str, str]:
    """Infer the best local model role for this conversational turn."""
    msg = (user_msg or "").strip().lower()

    triage_terms = (
        "status",
        "health",
        "check",
        "diagnose",
        "diagnostic",
        "preflight",
        "runtime",
        "available",
        "availability",
        "error",
        "failing",
        "failed",
        "monitor",
        "watch",
        "dashboard",
        "connect wre",
    )
    code_terms = (
        "fix",
        "patch",
        "refactor",
        "rewrite",
        "implement",
        "test",
        "pytest",
        "traceback",
        "exception",
        "stack trace",
        "module",
        "codebase",
        "repo",
        "repository",
        "git",
        "branch",
        "commit",
        "merge",
        "cleanup",
        "clean up",
        "security",
        "hardening",
        "cve",
        "dependency",
        "dependencies",
        "wsp",
        "wre",
        "main.py",
        "obs",
        "openclaw",
        "ironclaw",
    )

    code_hit = any(term in msg for term in code_terms)
    triage_hit = getattr(intent.category, "value", "") == "monitor" or any(
        term in msg for term in triage_terms
    )

    if code_hit:
        return "code", "code_or_system_change_request"
    if triage_hit:
        return "triage", "diagnostic_or_health_request"
    return "general", "default_general_reasoning"


def maybe_apply_agentic_conversation_model(
    dae: Any,
    intent: Any,
    user_msg: str,
) -> None:
    """Auto-select the best local model for this turn unless an operator pinned one."""
    if not dae._agentic_model_selection_enabled:
        return
    if dae._conversation_model_target_locked:
        return
    if dae._conversation_backend == "ironclaw":
        return
    if dae._preferred_external_provider and dae._preferred_external_model:
        return

    role, reason = infer_conversation_model_role(dae, user_msg, intent)
    target = resolve_local_target_for_role(dae, role)
    dae._last_auto_model_role = role
    dae._last_auto_model_target = target or "unresolved"
    dae._last_auto_model_reason = reason
    if not target:
        logger.info(
            "[OPENCLAW-DAE] Agentic model route unresolved | role=%s reason=%s",
            role,
            reason,
        )
        return

    apply_local_target_runtime(
        dae,
        target,
        f"agentic:{role}:{reason}",
        lock_target=False,
    )


def apply_model_switch_target(dae: Any, target: str) -> str:
    """Apply model switch request and return deterministic operator confirmation."""
    target = (target or "").strip().lower()
    if not target:
        return "0102: No model target recognized."

    target_dirs = local_target_dirs()
    if target in target_dirs:
        root = Path(os.getenv("LOCAL_MODEL_ROOT", "E:/LM_studio/models/local")).expanduser()
        code_dir = root / target_dirs[target]
        apply_local_target_runtime(
            dae,
            target,
            "manual_model_switch",
            lock_target=True,
        )
        return (
            "0102: Model switched to "
            f"{target} (local). "
            f"Routing LOCAL_MODEL_CODE_DIR -> {code_dir} and reloading conversation engine."
        )

    external = resolve_external_target(target)
    if external:
        provider, model = external
        if dae._runtime_profile == "zeroclaw":
            dae._mark_preferred_external_status(
                "blocked",
                "runtime_profile_zeroclaw",
            )
            return (
                "0102: model switch blocked by runtime profile zeroclaw. "
                "external targets are disabled."
            )
        dae._preferred_external_provider = provider
        dae._preferred_external_model = model
        os.environ["OPENCLAW_CONVERSATION_PREFERRED_PROVIDER"] = provider
        os.environ["OPENCLAW_CONVERSATION_PREFERRED_MODEL"] = model
        if not dae._allow_external_llm:
            dae._mark_preferred_external_status(
                "blocked",
                "external_llm_disabled_by_key_isolation",
            )
            return (
                "0102: cannot switch to "
                f"{provider}/{model} while key isolation is ON. "
                "Use a local target: qwen3, qwen, or gemma."
            )
        if not provider_has_key(provider):
            dae._mark_preferred_external_status(
                "blocked",
                "provider_key_missing",
            )
            return (
                "0102: cannot switch to "
                f"{provider}/{model}. provider api key is not configured."
            )
        if dae._model_switch_live_probe:
            ok, detail = dae._probe_provider_endpoint(
                provider,
                timeout_sec=dae._model_switch_probe_timeout_sec,
            )
            if not ok:
                dae._mark_preferred_external_status(
                    "blocked",
                    f"live_probe_failed:{detail}",
                )
                return (
                    "0102: cannot switch to "
                    f"{provider}/{model}. live provider probe failed ({detail}). "
                    "Check key validity/network, or disable strict probe with "
                    "OPENCLAW_MODEL_SWITCH_LIVE_PROBE=0."
                )
            dae._mark_preferred_external_status("selected", f"live_probe:{detail}")
        else:
            dae._mark_preferred_external_status("selected", "probe_disabled")
        dae._conversation_model_target_locked = True
        return (
            "0102: Model switched to "
            f"{provider}/{model}. "
            "Target is configured; use `model details` to verify active engine per turn."
        )

    return f"0102: Unsupported model target: {target}"
