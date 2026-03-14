"""OpenClaw control-plane bootstrap helpers."""

from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger("openclaw_dae")


def _env_truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


def initialize_control_plane_state(
    dae,
    *,
    backend: str,
    allow_external_requested: bool,
) -> None:
    """Initialize OpenClaw identity/runtime/model/context control-plane state."""
    dae._ollama_model = os.getenv("OPENCLAW_OLLAMA_MODEL", "qwen2.5-coder:7b").strip()
    strict_default = "1" if backend == "ironclaw" else "0"
    dae._ironclaw_strict = _env_truthy("OPENCLAW_IRONCLAW_STRICT", strict_default)
    dae._ironclaw_allow_local_fallback = _env_truthy(
        "OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK",
        "0",
    )
    dae._ironclaw_autostart_enabled = _env_truthy("OPENCLAW_IRONCLAW_AUTOSTART", "1")
    dae._ironclaw_autostart_start_cmd = os.getenv("IRONCLAW_START_CMD", "").strip()
    dae._ironclaw_autostart_default_cmd = (
        os.getenv("OPENCLAW_IRONCLAW_DEFAULT_START_CMD", "ironclaw gateway").strip()
        or "ironclaw gateway"
    )
    dae._ironclaw_autostart_last_attempt = 0.0
    try:
        dae._ironclaw_autostart_cooldown_sec = max(
            3.0,
            float(os.getenv("OPENCLAW_IRONCLAW_AUTOSTART_COOLDOWN_SEC", "20")),
        )
    except ValueError:
        dae._ironclaw_autostart_cooldown_sec = 20.0
    try:
        dae._ironclaw_autostart_wait_sec = max(
            1.0,
            float(os.getenv("OPENCLAW_IRONCLAW_AUTOSTART_WAIT_SEC", "8")),
        )
    except ValueError:
        dae._ironclaw_autostart_wait_sec = 8.0
    try:
        dae._ironclaw_autostart_missing_backoff_sec = max(
            30.0,
            float(
                os.getenv(
                    "OPENCLAW_IRONCLAW_AUTOSTART_MISSING_BACKOFF_SEC",
                    "300",
                )
            ),
        )
    except ValueError:
        dae._ironclaw_autostart_missing_backoff_sec = 300.0
    dae._ironclaw_autostart_missing_backoff_until = 0.0
    dae._ironclaw_autostart_allow_shell = _env_truthy(
        "OPENCLAW_IRONCLAW_AUTOSTART_ALLOW_SHELL",
        "0",
    )

    dae._identity_genus = dae._normalize_genus_label(
        os.getenv("OPENCLAW_IDENTITY_GENUS", "Ex.machina"),
        "Ex.machina",
    )
    legacy_species = os.getenv("OPENCLAW_IDENTITY_SPECIES", "").strip()
    family_env = os.getenv("OPENCLAW_IDENTITY_MODEL_FAMILY", "").strip()
    model_name_env = os.getenv("OPENCLAW_IDENTITY_MODEL_NAME", "").strip()
    if not family_env and legacy_species and "+" in legacy_species:
        family_env = legacy_species.split("+", 1)[0].strip()
    if not model_name_env and legacy_species and "+" in legacy_species:
        model_name_env = legacy_species.split("+", 1)[1].strip()

    dae._identity_model_family = dae._normalize_lower_label(family_env, "davinci")
    dae._identity_model_name_template = dae._normalize_lower_label(
        model_name_env,
        "{model}",
    )
    dae._identity_model_catalog = dae._normalize_lower_label(
        os.getenv("OPENCLAW_IDENTITY_MODEL_CATALOG", "").strip()
        or os.getenv("OPENCLAW_IDENTITY_MODEL_LINEAGE", "").strip()
        or "qwen2.5,qwen3,qwen3.5,ui_tars1.5,grok4,codex5.3,opus4.6,sonnet4.6,gemini3pro",
        "qwen2.5,qwen3,qwen3.5,ui_tars1.5,grok4,codex5.3,opus4.6,sonnet4.6,gemini3pro",
    )
    dae._identity_protocol_anchor = dae._normalize_lower_label(
        os.getenv("OPENCLAW_IDENTITY_PROTOCOL", "wsp_00"),
        "wsp_00",
    )
    dae._wsp00_boot_enabled = _env_truthy("OPENCLAW_WSP00_BOOT", "1")
    dae._wsp00_boot_mode = (
        os.getenv("OPENCLAW_WSP00_BOOT_MODE", "compact").strip().lower() or "compact"
    )
    dae._wsp00_prompt_file = os.getenv("OPENCLAW_WSP00_PROMPT_FILE", "").strip()
    dae._platform_context_enabled = _env_truthy("OPENCLAW_PLATFORM_CONTEXT_ENABLED", "1")
    dae._platform_context_files = os.getenv("OPENCLAW_PLATFORM_CONTEXT_FILES", "").strip()
    try:
        dae._platform_context_max_chars = max(
            400,
            int(os.getenv("OPENCLAW_PLATFORM_CONTEXT_MAX_CHARS", "2200")),
        )
    except ValueError:
        dae._platform_context_max_chars = 2200
    try:
        dae._platform_context_refresh_sec = max(
            5.0,
            float(os.getenv("OPENCLAW_PLATFORM_CONTEXT_REFRESH_SEC", "120")),
        )
    except ValueError:
        dae._platform_context_refresh_sec = 120.0
    try:
        dae._platform_context_quick_response_chars = max(
            200,
            int(os.getenv("OPENCLAW_PLATFORM_CONTEXT_QUICK_RESPONSE_CHARS", "1000")),
        )
    except ValueError:
        dae._platform_context_quick_response_chars = 1000
    dae._platform_context_pack_cache = ""
    dae._platform_context_pack_loaded_at = 0.0
    dae._platform_context_pack_sources = []
    dae._agentic_model_selection_enabled = _env_truthy(
        "OPENCLAW_AGENTIC_MODEL_SELECTION",
        "1",
    )
    dae._conversation_model_target_locked = _env_truthy(
        "OPENCLAW_CONVERSATION_MODEL_LOCK",
        "0",
    )
    configured_conversation_target = (
        os.getenv("OPENCLAW_CONVERSATION_MODEL_TARGET", "").strip().lower()
    )
    default_conversation_target = (
        dae._resolve_local_target_for_role("general") or "local/qwen3.5-4b"
    )
    dae._conversation_model_target_id = (
        configured_conversation_target or default_conversation_target
    )
    dae._preferred_external_provider = (
        os.getenv("OPENCLAW_CONVERSATION_PREFERRED_PROVIDER", "").strip().lower()
    )
    dae._preferred_external_model = (
        os.getenv("OPENCLAW_CONVERSATION_PREFERRED_MODEL", "").strip().lower()
    )
    dae._model_switch_live_probe = _env_truthy(
        "OPENCLAW_MODEL_SWITCH_LIVE_PROBE",
        "1",
    )
    try:
        dae._model_switch_probe_timeout_sec = max(
            0.8,
            float(os.getenv("OPENCLAW_MODEL_SWITCH_PROBE_TIMEOUT_SEC", "2.0")),
        )
    except ValueError:
        dae._model_switch_probe_timeout_sec = 2.0

    dae._last_conversation_engine = "uninitialized"
    dae._last_conversation_detail = "none"
    dae._previous_conversation_engine = "none"
    dae._previous_conversation_detail = "none"
    dae._preferred_external_last_status = "not_selected"
    dae._preferred_external_last_status_detail = "none"
    dae._preferred_external_last_status_at = 0.0
    dae._token_usage_last_prompt_tokens = 0
    dae._token_usage_last_completion_tokens = 0
    dae._token_usage_last_total_tokens = 0
    dae._token_usage_last_engine = "none"
    dae._token_usage_last_provider = "none"
    dae._token_usage_last_model = "none"
    dae._token_usage_last_source = "none"
    dae._token_usage_last_cost_estimate_usd = 0.0
    dae._token_usage_last_at = 0.0
    dae._last_social_response_source = "none"
    dae._last_social_response_action = "none"
    dae._last_social_response_skill = "none"
    dae._last_social_response_success = "unknown"
    dae._last_social_response_preview = "none"
    dae._last_social_response_at = 0.0
    dae._last_auto_model_role = "boot"
    dae._last_auto_model_target = dae._conversation_model_target_id or "unassigned"
    dae._last_auto_model_reason = (
        "explicit_env_target" if configured_conversation_target else "boot_default"
    )
    dae._token_usage_session_turns = 0
    dae._token_usage_session_prompt_tokens = 0
    dae._token_usage_session_completion_tokens = 0
    dae._token_usage_session_total_tokens = 0
    dae._token_usage_session_cost_estimate_usd = 0.0
    dae._turn_cancel_event = threading.Event()
    dae._turn_cancel_reason = "none"

    if dae._no_api_keys:
        os.environ["OPENCLAW_NO_API_KEYS"] = "1"
        if backend == "ironclaw":
            os.environ["IRONCLAW_NO_API_KEYS"] = "1"
        if allow_external_requested:
            logger.warning(
                "[OPENCLAW-DAE] OPENCLAW_ALLOW_EXTERNAL_LLM ignored because no_api_keys mode is ON"
            )
