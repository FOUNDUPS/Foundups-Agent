"""Local canary prerequisites, not service health or signed model admission.

No provider, HTTP or native runtime invocation occurs here. Declared model
availability is not authority: the existing signed topology, capability, budget
and provider preflight gates must still pass at invocation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Mapping, Optional

from .reddog_artifact_generation_provider_modes import (
    RUNTIME_MODE_FOUNDUPS_FUSION, RUNTIME_MODE_HERMES_API,
)
from .reddog_hermes_api_transport import RuntimeHermesApiKeyProvider
from .reddog_resident_live_canary_environment import live_canary_artifact_generator_mode


def live_canary_provider_requirements(
    *, repo_root: Path, runtime_root: Path, environ: Mapping[str, str],
    command_resolver: Callable[[str], Optional[str]],
) -> tuple[tuple[str, bool, str], ...]:
    mode = live_canary_artifact_generator_mode(environ)
    checks = [("artifact_generator_mode", bool(mode), "unsupported_artifact_generator_mode")]
    if not mode:
        return tuple(checks)
    providers = {
        item.strip().lower() for item in str(
            environ.get("REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS") or ""
        ).split(",") if item.strip()
    }
    checks.append(("model_provider_identity", bool(providers), "model_provider_identity_missing"))
    if mode == RUNTIME_MODE_FOUNDUPS_FUSION:
        checks.extend((
            ("openrouter_key_reference", bool(str(environ.get("OPENROUTER_API_KEY") or "").strip()), "openrouter_api_key_missing"),
            ("fusion_model_provider", "openrouter" in providers, "openrouter_model_provider_missing"),
        ))
    elif mode == RUNTIME_MODE_HERMES_API:
        checks.append(("hermes_api_key_reference", _hermes_key_available(repo_root, runtime_root), "hermes_api_key_missing_or_invalid"))
    else:
        # Gateway service credentials and sandbox identity remain owned by its
        # existing signed-session preflight; no guessed env-key substitute.
        checks.append(("openclaw_available", bool(command_resolver("openclaw")), "openclaw_not_available"))
    return tuple(checks)


def _hermes_key_available(repo_root: Path, runtime_root: Path) -> bool:
    try:
        return bool(RuntimeHermesApiKeyProvider(runtime_root, repo_root).read_key())
    except (OSError, ValueError, UnicodeError):
        return False


__all__ = ["live_canary_provider_requirements"]
