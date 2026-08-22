"""
Local LLM Backend Resolver

Simple resolver for selecting between local LLM backends.
Phase 1: Lightweight local selection, not full ai_gateway integration.

Policy:
1. If LM Studio is available and has the requested model → use LMStudioBackend
2. Else → use LlamaCppBackend (direct file loading)

Dependency boundary (LM_STUDIO_DEPENDENCY_BOUNDARY_DOC_AND_GATE_PHASE1):
LM Studio is an OPTIONAL local dependency. This resolver only PROBES for it
(``is_lm_studio_available`` → a short HTTP GET). It never launches LM Studio.
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

logger = logging.getLogger(__name__)

# Model ID mapping for LM Studio
LM_STUDIO_MODEL_IDS = {
    "qwen": "qwen-coder-7b",
    "gemma": "gemma-270m",
}


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


def resolve_qwen_backend(
    model_path: Optional[Path] = None,
    n_ctx: int = 2048,
    n_threads: int = 4,
) -> Optional[LocalLLMBackend]:
    """
    Resolve and initialize the best available Qwen backend.

    Priority:
    1. LM Studio API (if available and has qwen-coder-7b loaded) - no model_path needed
    2. Direct llama_cpp (file loading) - requires model_path

    Args:
        model_path: Path to GGUF model file. Only required for llama_cpp fallback.
        n_ctx: Context window size
        n_threads: Thread count for inference

    Returns:
        Initialized LocalLLMBackend, or None if unavailable
    """
    # Try LM Studio first (avoids file locks, doesn't need model_path).
    # Probe-only: this never launches LM Studio.
    lm_studio_reachable = is_lm_studio_available()
    if lm_studio_reachable:
        model_id = LM_STUDIO_MODEL_IDS["qwen"]
        backend = LMStudioBackend(model_id=model_id)
        if backend.initialize():
            logger.info(f"[RESOLVER] Qwen using LMStudioBackend ({model_id})")
            return backend
        logger.debug("[RESOLVER] LM Studio reachable but Qwen model not loaded; trying local GGUF fallback")

    # Fall back to llama_cpp (requires model_path)
    if model_path is None:
        logger.warning(
            "[RESOLVER] No Qwen backend. %s",
            operator_action_for(LocalLLMAvailability.UNAVAILABLE),
        )
        return None

    if not lm_studio_reachable:
        logger.info(
            "[RESOLVER] %s",
            operator_action_for(LocalLLMAvailability.FALLBACK_LLAMA_CPP),
        )

    backend = LlamaCppBackend(
        model_path=model_path,
        n_ctx=n_ctx,
        n_threads=n_threads,
    )
    if backend.initialize():
        logger.info(f"[RESOLVER] Qwen using LlamaCppBackend ({model_path.name})")
        return backend

    logger.warning("[RESOLVER] No Qwen backend available (llama.cpp fallback load failed)")
    return None


def resolve_gemma_backend(
    model_path: Optional[Path] = None,
    n_ctx: int = 1024,
    n_threads: int = 4,
) -> Optional[LocalLLMBackend]:
    """
    Resolve and initialize the best available Gemma backend.

    Priority:
    1. LM Studio API (if available and has gemma-270m loaded) - no model_path needed
    2. Direct llama_cpp (file loading) - requires model_path

    Args:
        model_path: Path to GGUF model file. Only required for llama_cpp fallback.
        n_ctx: Context window size
        n_threads: Thread count for inference

    Returns:
        Initialized LocalLLMBackend, or None if unavailable
    """
    # Try LM Studio first (avoids file locks, doesn't need model_path).
    # Probe-only: this never launches LM Studio.
    lm_studio_reachable = is_lm_studio_available()
    if lm_studio_reachable:
        model_id = LM_STUDIO_MODEL_IDS["gemma"]
        backend = LMStudioBackend(model_id=model_id)
        if backend.initialize():
            logger.info(f"[RESOLVER] Gemma using LMStudioBackend ({model_id})")
            return backend
        logger.debug("[RESOLVER] LM Studio reachable but Gemma model not loaded; trying local GGUF fallback")

    # Fall back to llama_cpp (requires model_path)
    if model_path is None:
        logger.warning(
            "[RESOLVER] No Gemma backend. %s",
            operator_action_for(LocalLLMAvailability.UNAVAILABLE),
        )
        return None

    if not lm_studio_reachable:
        logger.info(
            "[RESOLVER] %s",
            operator_action_for(LocalLLMAvailability.FALLBACK_LLAMA_CPP),
        )

    backend = LlamaCppBackend(
        model_path=model_path,
        n_ctx=n_ctx,
        n_threads=n_threads,
        n_gpu_layers=0,  # CPU-only for fast triage
    )
    if backend.initialize():
        logger.info(f"[RESOLVER] Gemma using LlamaCppBackend ({model_path.name})")
        return backend

    logger.warning("[RESOLVER] No Gemma backend available (llama.cpp fallback load failed)")
    return None
