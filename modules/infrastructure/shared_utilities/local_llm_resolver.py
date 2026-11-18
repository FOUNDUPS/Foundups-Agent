"""
Local LLM Backend Resolver

Simple resolver for selecting between local LLM backends.
Phase 1: Lightweight local selection, not full ai_gateway integration.

Policy:
1. If LM Studio is available and has the requested model → use LMStudioBackend
2. Else → use LlamaCppBackend (direct file loading)

Dependency boundary (LM_STUDIO_DEPENDENCY_BOUNDARY_DOC_AND_GATE_PHASE1):
LM Studio is an OPTIONAL local dependency. This resolver only PROBES for it
(``LMStudioBackend.initialize`` → exact native inspection). It never launches LM Studio.
Launching LM Studio is the sole responsibility of the explicit dependency
launcher (``dependency_launcher.dae_dependencies.launch_lm_studio``) invoked
from explicit DAE/menu startup paths. When LM Studio is absent the resolver
states the chosen fallback (local GGUF via llama.cpp) clearly, and callers that
strictly require LM Studio can use ``require_lm_studio_backend`` to obtain a
named, operator-actionable unavailable state instead of a silent ``None``.

WSP 77: Agent Coordination
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Optional

from modules.infrastructure.shared_utilities.local_llm_backends import (
    LocalLLMBackend,
    LlamaCppBackend,
    LMStudioBackend,
    is_lm_studio_available,
)
from modules.infrastructure.shared_utilities.local_model_selection import (
    MODEL_DIR_DEFAULTS, resolve_role_native_key,
)

logger = logging.getLogger(__name__)

# Compatibility export only; request selection belongs to local_model_selection.
LM_STUDIO_MODEL_IDS = {
    "qwen": MODEL_DIR_DEFAULTS["code"],
    "gemma": MODEL_DIR_DEFAULTS["triage"],
}
_ROLE_NATIVE_KEY_UNSET = object()


class LocalLLMAvailability(str, Enum):
    """Named, probe-only result states for local LLM backend availability.

    Makes LM Studio absence explicit instead of an ambiguous ``None`` return:

    - ``LM_STUDIO_SERVER_REACHABLE``: the native LM Studio API responds; this
      does not assert that a requested model is resident.
    - ``FALLBACK_LLAMA_CPP``: LM Studio absent, but a local GGUF file exists so
      the llama.cpp fallback can serve the request.
    - ``UNAVAILABLE``: LM Studio absent and no local GGUF fallback is available.
    """

    LM_STUDIO_SERVER_REACHABLE = "lm_studio_server_reachable"
    FALLBACK_LLAMA_CPP = "fallback_llama_cpp"
    UNAVAILABLE = "unavailable"


class LMStudioUnavailableError(RuntimeError):
    """Raised when a caller strictly requires LM Studio but it is unreachable.

    Carries operator-actionable guidance. This is the named state returned for
    "required" paths so callers do not silently degrade. The resolver never
    launches LM Studio to satisfy this requirement.
    """

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or operator_action_for(LocalLLMAvailability.UNAVAILABLE))


def operator_action_for(status: LocalLLMAvailability) -> str:
    """Return operator-actionable guidance for a given availability status."""
    if status is LocalLLMAvailability.LM_STUDIO_SERVER_REACHABLE:
        return (
            "LM Studio server reachable on localhost:1234. Exact model "
            "residency must still be verified before inference."
        )
    if status is LocalLLMAvailability.FALLBACK_LLAMA_CPP:
        return (
            "LM Studio not reachable on localhost:1234 - using local GGUF "
            "fallback via llama.cpp. This is expected when LM Studio is not "
            "running. To use LM Studio instead, start it via the dependency "
            "launcher / main menu (the resolver does not auto-launch it)."
        )
    return (
        "LM Studio not reachable on localhost:1234 and no local GGUF fallback "
        "is available. Either start LM Studio via the dependency launcher / "
        "main menu, or provide a model_path to a local GGUF file. The resolver "
        "never auto-launches LM Studio."
    )


def probe_backend_availability(
    model_path: Optional[Path] = None,
) -> LocalLLMAvailability:
    """Probe-only classification of local LLM availability.

    NEVER launches LM Studio and NEVER loads a model - it only performs the
    lightweight ``is_lm_studio_available`` HTTP probe and a filesystem check for
    the optional GGUF fallback. Returns a named :class:`LocalLLMAvailability`.
    """
    if is_lm_studio_available():
        return LocalLLMAvailability.LM_STUDIO_SERVER_REACHABLE
    if model_path is not None and Path(model_path).exists():
        return LocalLLMAvailability.FALLBACK_LLAMA_CPP
    return LocalLLMAvailability.UNAVAILABLE


def require_lm_studio_backend(
    model_id: str,
    base_url: Optional[str] = None,
    request_timeout: float = 30.0,
    api_token: str | None = None,
) -> LocalLLMBackend:
    """Resolve an LM-Studio-backed engine for paths that strictly require it.

    Probes for LM Studio (never launches it). If unavailable, raises
    :class:`LMStudioUnavailableError` with operator-actionable guidance instead
    of returning a silent ``None``. Use this only for operations that genuinely
    cannot fall back to llama.cpp (e.g. UI-TARS vision via LM Studio).
    """
    probe_url = base_url or LMStudioBackend.DEFAULT_BASE_URL
    if not is_lm_studio_available(probe_url, api_token=api_token):
        raise LMStudioUnavailableError()

    backend = (
        LMStudioBackend(
            model_id=model_id,
            base_url=base_url,
            request_timeout=request_timeout,
            api_token=api_token,
        )
        if base_url is not None
        else LMStudioBackend(
            model_id=model_id,
            request_timeout=request_timeout,
            api_token=api_token,
        )
    )
    if not backend.initialize():
        raise LMStudioUnavailableError(
            f"LM Studio reachable but model '{model_id}' is not loaded. "
            "Load that exact model explicitly before retrying."
        )
    return backend


def _resolve_role_backend(role, model_path, n_ctx, n_threads, native_model_key):
    """One exact native initialization, followed only by an explicit file fallback."""
    has_file = model_path is not None and Path(model_path).is_file()
    key = resolve_role_native_key(role) if native_model_key is _ROLE_NATIVE_KEY_UNSET else native_model_key
    if key is not None:
        backend = LMStudioBackend(model_id=key)
        if backend.initialize():
            logger.info("[RESOLVER] %s using LMStudioBackend (%s)", role, key)
            return backend
        status = backend.last_initialization_status
        logger.warning("[RESOLVER] %s native backend unavailable (%s); no automatic model load", role, status)
        if status == "server_unreachable":
            availability = LocalLLMAvailability.FALLBACK_LLAMA_CPP if has_file else LocalLLMAvailability.UNAVAILABLE
            logger.info("[RESOLVER] %s", operator_action_for(availability))
    else:
        logger.info("[RESOLVER] %s exact native key not configured; no native model guessed", role)
    if not has_file:
        logger.warning("[RESOLVER] %s has no existing explicit GGUF fallback", role)
        return None
    backend = LlamaCppBackend(model_path=Path(model_path), n_ctx=n_ctx, n_threads=n_threads,
                              n_gpu_layers=0)
    logger.info("[RESOLVER] %s trying the explicit GGUF fallback via llama.cpp", role)
    if backend.initialize():
        return backend
    logger.warning("[RESOLVER] %s explicit GGUF fallback failed", role)
    return None


def resolve_qwen_backend(
    model_path: Optional[Path] = None,
    n_ctx: int = 2048,
    n_threads: int = 4,
    *, native_model_key=_ROLE_NATIVE_KEY_UNSET,
) -> Optional[LocalLLMBackend]:
    """Resolve the existing code role; a supplied GGUF remains an explicit fallback.

    Omitted native_model_key uses the role owner. Explicit None skips native
    lookup, e.g. a custom file without a separately configured exact native key.
    No server launch, native model load or arbitrary resident substitution occurs.
    """
    return _resolve_role_backend("code", model_path, n_ctx, n_threads, native_model_key)


def resolve_gemma_backend(
    model_path: Optional[Path] = None,
    n_ctx: int = 1024,
    n_threads: int = 4,
    *, native_model_key=_ROLE_NATIVE_KEY_UNSET,
) -> Optional[LocalLLMBackend]:
    """Resolve the existing triage role under the same exact-key/file contract."""
    return _resolve_role_backend("triage", model_path, n_ctx, n_threads, native_model_key)
