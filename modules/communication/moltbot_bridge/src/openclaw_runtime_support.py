"""OpenClaw runtime/model probe helpers."""

from __future__ import annotations

import logging
import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("openclaw_dae")


def _env_truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


def resolve_local_code_model_snapshot() -> Dict[str, str]:
    """Resolve local code-model path/status from centralized LOCAL_MODEL_* routing."""
    snapshot = {
        "path": "unavailable",
        "state": "ERROR",
        "source": "unavailable",
    }
    try:
        from modules.infrastructure.shared_utilities.local_model_selection import (
            resolve_model_selection,
        )

        selection = resolve_model_selection("code")
        snapshot["path"] = str(selection.path)
        snapshot["state"] = "OK" if selection.exists else "MISSING"
        snapshot["source"] = selection.source
    except Exception as exc:
        snapshot["source"] = f"error:{type(exc).__name__}"
    return snapshot


def probe_ironclaw_runtime() -> Dict[str, str]:
    """Probe IronClaw runtime for identity/status reporting."""
    runtime = {
        "healthy": "UNKNOWN",
        "detail": "not-probed",
        "model": os.getenv("IRONCLAW_MODEL", "local/qwen-coder-7b").strip() or "local/qwen-coder-7b",
        "models": "none",
        "base_url": os.getenv("IRONCLAW_BASE_URL", "http://127.0.0.1:3000").strip() or "http://127.0.0.1:3000",
    }
    try:
        from .ironclaw_gateway_client import IronClawGatewayClient

        client = IronClawGatewayClient()
        healthy, detail = client.health()
        models = client.list_models()
        runtime["healthy"] = "PASS" if healthy else "FAIL"
        runtime["detail"] = detail
        runtime["model"] = client.config.model
        runtime["models"] = ", ".join(models[:5]) if models else "none"
        runtime["base_url"] = client.config.base_url
    except Exception as exc:
        runtime["healthy"] = "FAIL"
        runtime["detail"] = f"probe_error:{type(exc).__name__}"
    return runtime


def attempt_ironclaw_autostart(dae: Any) -> tuple[bool, str]:
    """Try to auto-start IronClaw gateway and wait briefly for health."""
    if not dae._ironclaw_autostart_enabled:
        return False, "autostart_disabled"

    now = time.time()
    if now < dae._ironclaw_autostart_missing_backoff_until:
        return False, "autostart_missing_executable_backoff"
    if (now - dae._ironclaw_autostart_last_attempt) < dae._ironclaw_autostart_cooldown_sec:
        return False, "autostart_cooldown"
    dae._ironclaw_autostart_last_attempt = now

    cmd_candidates: list[str] = []
    if dae._ironclaw_autostart_start_cmd:
        cmd_candidates.append(dae._ironclaw_autostart_start_cmd)
    discovered = shutil.which("ironclaw")
    if discovered:
        discovered_cmd = f"\"{discovered}\" gateway"
        if discovered_cmd not in cmd_candidates:
            cmd_candidates.append(discovered_cmd)
    binary_name = "ironclaw.exe" if os.name == "nt" else "ironclaw"
    local_binary_candidates = [
        dae.repo_root / "target" / "release" / binary_name,
        dae.repo_root / "ironclaw" / "target" / "release" / binary_name,
        dae.repo_root / "modules" / "ironclaw" / "target" / "release" / binary_name,
    ]
    for bin_path in local_binary_candidates:
        if bin_path.exists():
            local_cmd = f"\"{str(bin_path)}\" gateway"
            if local_cmd not in cmd_candidates:
                cmd_candidates.append(local_cmd)
    if dae._ironclaw_autostart_default_cmd and dae._ironclaw_autostart_default_cmd not in cmd_candidates:
        cmd_candidates.append(dae._ironclaw_autostart_default_cmd)
    if not cmd_candidates:
        return False, "missing_ironclaw_start_cmd"

    try:
        env = os.environ.copy()
        try:
            from .ironclaw_gateway_client import scrub_sensitive_env, env_truthy

            if env_truthy("IRONCLAW_NO_API_KEYS", "1"):
                env = scrub_sensitive_env(env)
        except Exception:
            pass

        cwd_candidates = [
            dae.repo_root / "temp" / "_vendor" / "ironclaw",
            dae.repo_root / "ironclaw",
            dae.repo_root,
        ]
        cwd = next((p for p in cwd_candidates if p.exists()), dae.repo_root)

        started_cmd = ""
        missing_execs: list[str] = []
        spawn_errors: list[str] = []
        for cmd in cmd_candidates:
            try:
                if dae._ironclaw_autostart_allow_shell:
                    subprocess.Popen(
                        cmd,
                        cwd=str(cwd),
                        env=env,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    args = shlex.split(cmd, posix=False)
                    if not args:
                        continue
                    executable = args[0].strip('"')
                    if not Path(executable).is_absolute() and shutil.which(executable) is None:
                        missing_execs.append(executable)
                        continue
                    subprocess.Popen(
                        args,
                        cwd=str(cwd),
                        env=env,
                        shell=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                started_cmd = cmd
                logger.info(
                    "[OPENCLAW-DAE] IronClaw autostart launched | cmd=%s cwd=%s shell=%s",
                    cmd,
                    cwd,
                    dae._ironclaw_autostart_allow_shell,
                )
                break
            except FileNotFoundError as exc:
                missing_execs.append(str(exc.filename or exc))
            except Exception as exc:
                spawn_errors.append(type(exc).__name__)

        if not started_cmd:
            if missing_execs:
                uniq = sorted({m for m in missing_execs if m})
                dae._ironclaw_autostart_missing_backoff_until = (
                    now + dae._ironclaw_autostart_missing_backoff_sec
                )
                preview = ",".join(uniq[:3]) if uniq else "unknown"
                return False, f"autostart_executable_missing:{preview}"
            if spawn_errors:
                return False, f"autostart_spawn_failed:{spawn_errors[0]}"
            return False, "autostart_spawn_failed"

        deadline = time.time() + dae._ironclaw_autostart_wait_sec
        while time.time() < deadline:
            healthy, detail = False, "not_probed"
            try:
                from .ironclaw_gateway_client import IronClawGatewayClient

                healthy, detail = IronClawGatewayClient().health()
            except Exception as exc:
                detail = f"probe_error:{type(exc).__name__}"

            if healthy:
                logger.info(
                    "[OPENCLAW-DAE] IronClaw autostart recovered runtime | cmd=%s",
                    started_cmd,
                )
                return True, "autostart_recovered"

            time.sleep(0.5)

        return False, "autostart_started_but_unhealthy"

    except Exception as exc:
        logger.warning("[OPENCLAW-DAE] IronClaw autostart failed: %s", exc)
        return False, f"autostart_error:{type(exc).__name__}"


def resolve_identity_model_name(
    dae: Any,
    local_code: Dict[str, str],
    ironclaw_runtime: Dict[str, str],
) -> str:
    """Resolve model_name label from template using current runtime model hint."""
    template = dae._identity_model_name_template or "{model}"

    model_hint = "model"
    preferred_provider = (dae._preferred_external_provider or "").strip().lower()
    preferred_model = (dae._preferred_external_model or "").strip().lower()
    if (
        dae._conversation_backend != "ironclaw"
        and preferred_provider
        and preferred_model
        and dae._allow_external_llm
        and dae._provider_has_key(preferred_provider)
    ):
        model_hint = f"{preferred_provider}/{preferred_model}"
    elif dae._conversation_backend == "ironclaw":
        model_hint = (ironclaw_runtime.get("model") or "model").strip() or "model"
    else:
        code_path = (local_code.get("path") or "").strip()
        if code_path and code_path.lower() != "unavailable":
            try:
                model_hint = Path(code_path).name or "model"
            except Exception:
                model_hint = code_path
    model_hint = model_hint.lower()

    if "{model}" in template:
        return template.replace("{model}", model_hint).lower()

    if "model" in template:
        return template.replace("model", model_hint).lower()

    return template.lower()


def probe_provider_endpoint(
    dae: Any,
    provider: str,
    timeout_sec: float = 2.0,
) -> tuple[bool, str]:
    """Best-effort live provider probe for model availability reporting."""
    provider_name = (provider or "").strip().lower()
    if not provider_name:
        return False, "invalid_provider"
    if not dae._provider_has_key(provider_name):
        return False, "no_key"

    try:
        import requests as _req
    except Exception:
        return False, "requests_unavailable"

    api_keys = {
        "openai": os.getenv("OPENAI_API_KEY", "").strip(),
        "anthropic": os.getenv("ANTHROPIC_API_KEY", "").strip(),
        "grok": (
            os.getenv("GROK_API_KEY", "").strip()
            or os.getenv("XAI_API_KEY", "").strip()
        ),
        "gemini": os.getenv("GEMINI_API_KEY", "").strip(),
    }
    key = api_keys.get(provider_name, "")
    if not key:
        return False, "no_key"

    endpoint = ""
    headers: Dict[str, str] = {}
    params: Dict[str, str] = {}

    if provider_name in {"openai", "grok"}:
        base = "https://api.openai.com/v1" if provider_name == "openai" else "https://api.x.ai/v1"
        endpoint = f"{base}/models"
        headers = {"Authorization": f"Bearer {key}"}
    elif provider_name == "anthropic":
        endpoint = "https://api.anthropic.com/v1/models"
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        }
    elif provider_name == "gemini":
        endpoint = "https://generativelanguage.googleapis.com/v1/models"
        params = {"key": key}
    else:
        return False, "unsupported_provider"

    try:
        response = _req.get(
            endpoint,
            headers=headers or None,
            params=params or None,
            timeout=max(0.5, timeout_sec),
        )
        code = int(response.status_code)
        if 200 <= code < 300:
            return True, "api_ok"
        if code in {401, 403}:
            return False, "auth_error"
        return True, f"http_{code}"
    except Exception as exc:
        return False, f"network_{type(exc).__name__.lower()}"


def get_model_availability_snapshot(
    dae: Any,
    live_probe: bool = False,
    timeout_sec: float = 2.0,
) -> Dict[str, Any]:
    """Return startup model/provider availability for voice/chat diagnostics."""
    local_root = Path(
        os.getenv("LOCAL_MODEL_ROOT", "E:/LM_studio/models/local")
    ).expanduser()

    local_targets = {
        "local/qwen-coder-7b": "qwen-coder-7b",
        "local/qwen3-4b": "qwen3-4b",
        "local/qwen3.5-4b": "qwen3.5-4b",
        "local/gemma-270m": "gemma-270m",
    }
    local_status: Dict[str, str] = {}
    for target_id, folder in local_targets.items():
        model_dir = local_root / folder
        if not model_dir.exists() or not model_dir.is_dir():
            local_status[target_id] = "missing"
            continue
        try:
            has_gguf = any(model_dir.glob("*.gguf"))
        except Exception:
            has_gguf = False
        local_status[target_id] = "ready" if has_gguf else "dir_only"

    providers = ("openai", "anthropic", "grok", "gemini")
    provider_status: Dict[str, str] = {}
    for provider in providers:
        if not dae._provider_has_key(provider):
            provider_status[provider] = "no_key"
            continue
        if not live_probe:
            provider_status[provider] = "key_present"
            continue
        _, detail = probe_provider_endpoint(dae, provider, timeout_sec=timeout_sec)
        provider_status[provider] = detail

    target = dae._conversation_model_target_id or "local/qwen-coder-7b"
    target_status = "unknown"
    if target in local_status:
        target_status = local_status[target]
    else:
        external = dae._resolve_external_target(target)
        if external:
            provider_name, _ = external
            target_status = provider_status.get(provider_name, "no_key")

    local_code = resolve_local_code_model_snapshot()
    ironclaw_runtime = {
        "healthy": "N/A",
        "detail": "not_probed",
        "model": os.getenv("IRONCLAW_MODEL", "local/qwen-coder-7b").strip() or "local/qwen-coder-7b",
        "models": "none",
    }
    effective_model_name = resolve_identity_model_name(dae, local_code, ironclaw_runtime)

    return {
        "probe_mode": "live" if live_probe else "keys_only",
        "local_root": str(local_root),
        "local": local_status,
        "providers": provider_status,
        "target": target,
        "target_status": target_status,
        "effective_model_name": effective_model_name,
    }


def get_identity_snapshot(dae: Any, include_runtime_probe: bool = True) -> Dict[str, str]:
    """Return canonical 0102 identity snapshot used by daemon/CLI/status surfaces."""
    local_code = resolve_local_code_model_snapshot()
    ironclaw_runtime = {
        "healthy": "N/A",
        "detail": "backend_not_ironclaw",
        "model": os.getenv("IRONCLAW_MODEL", "local/qwen-coder-7b").strip() or "local/qwen-coder-7b",
        "models": "none",
        "base_url": os.getenv("IRONCLAW_BASE_URL", "http://127.0.0.1:3000").strip() or "http://127.0.0.1:3000",
    }
    if include_runtime_probe and (
        dae._conversation_backend == "ironclaw"
        or _env_truthy("OPENCLAW_ALLOW_IRONCLAW_FALLBACK", "0")
    ):
        ironclaw_runtime = probe_ironclaw_runtime()

    model_name = resolve_identity_model_name(dae, local_code, ironclaw_runtime)
    token_snapshot = dae._get_token_usage_snapshot()
    return {
        "backend": dae._conversation_backend,
        "runtime_profile": dae._runtime_profile,
        "key_isolation": "ON" if dae._no_api_keys else "OFF",
        "ironclaw_strict": "ON" if dae._ironclaw_strict else "OFF",
        "ironclaw_allow_local_fallback": "ON" if dae._ironclaw_allow_local_fallback else "OFF",
        "genus": dae._identity_genus,
        "lineage": dae._identity_model_family,
        "model_family": dae._identity_model_family,
        "model_name": model_name,
        "model_catalog": dae._identity_model_catalog or "unspecified",
        "conversation_model_target": dae._conversation_model_target_id or "local/qwen-coder-7b",
        "conversation_model_locked": "ON" if dae._conversation_model_target_locked else "OFF",
        "auto_model_role": dae._last_auto_model_role or "unknown",
        "auto_model_target": dae._last_auto_model_target or "unknown",
        "auto_model_reason": dae._last_auto_model_reason or "unknown",
        "preferred_external_provider": dae._preferred_external_provider or "none",
        "preferred_external_model": dae._preferred_external_model or "none",
        "preferred_external_status": dae._preferred_external_last_status,
        "preferred_external_status_detail": dae._preferred_external_last_status_detail,
        "preferred_external_status_age": (
            f"{int(max(0.0, time.time() - dae._preferred_external_last_status_at))}s"
            if dae._preferred_external_last_status_at > 0
            else "never"
        ),
        "protocol_anchor": dae._identity_protocol_anchor,
        "wsp00_boot": "ON" if dae._wsp00_boot_enabled else "OFF",
        "wsp00_boot_mode": dae._wsp00_boot_mode,
        "wsp00_file_override": "YES" if bool(dae._wsp00_prompt_file) else "NO",
        "platform_context": "ON" if dae._platform_context_enabled else "OFF",
        "platform_context_sources": str(len(dae._platform_context_pack_sources)),
        "platform_context_loaded_ago": (
            f"{int(max(0.0, time.time() - dae._platform_context_pack_loaded_at))}s"
            if dae._platform_context_pack_loaded_at > 0
            else "never"
        ),
        "last_engine": dae._last_conversation_engine,
        "last_engine_detail": dae._last_conversation_detail,
        "previous_engine": dae._previous_conversation_engine,
        "previous_engine_detail": dae._previous_conversation_detail,
        "token_last_prompt_tokens": str(token_snapshot["last_prompt_tokens"]),
        "token_last_completion_tokens": str(token_snapshot["last_completion_tokens"]),
        "token_last_total_tokens": str(token_snapshot["last_total_tokens"]),
        "token_last_engine": token_snapshot["last_engine"],
        "token_last_provider": token_snapshot["last_provider"],
        "token_last_model": token_snapshot["last_model"],
        "token_last_source": token_snapshot["last_source"],
        "token_last_cost_estimate_usd": f"{token_snapshot['last_cost_estimate_usd']:.6f}",
        "token_last_age": token_snapshot["last_age"],
        "token_session_turns": str(token_snapshot["session_turns"]),
        "token_session_prompt_tokens": str(token_snapshot["session_prompt_tokens"]),
        "token_session_completion_tokens": str(token_snapshot["session_completion_tokens"]),
        "token_session_total_tokens": str(token_snapshot["session_total_tokens"]),
        "token_session_cost_estimate_usd": f"{token_snapshot['session_cost_estimate_usd']:.6f}",
        "last_social_source": dae._last_social_response_source,
        "last_social_action": dae._last_social_response_action,
        "last_social_skill": dae._last_social_response_skill,
        "last_social_success": dae._last_social_response_success,
        "last_social_preview": dae._last_social_response_preview,
        "last_social_age": (
            f"{int(max(0.0, time.time() - dae._last_social_response_at))}s"
            if dae._last_social_response_at > 0
            else "never"
        ),
        "local_code_model_path": local_code.get("path", "unavailable"),
        "local_code_model_state": local_code.get("state", "ERROR"),
        "local_code_model_source": local_code.get("source", "unavailable"),
        "ironclaw_runtime_healthy": ironclaw_runtime.get("healthy", "UNKNOWN"),
        "ironclaw_runtime_detail": ironclaw_runtime.get("detail", "not-probed"),
        "ironclaw_runtime_model": ironclaw_runtime.get("model", "unknown"),
        "ironclaw_runtime_models": ironclaw_runtime.get("models", "none"),
        "ironclaw_runtime_base_url": ironclaw_runtime.get("base_url", "unknown"),
    }
