"""
Local LLM Backend Resolver

Simple resolver for selecting between local LLM backends.
Phase 1: Lightweight local selection, not full ai_gateway integration.

Policy:
1. If LM Studio is available and has the requested model → use LMStudioBackend
2. Else → use LlamaCppBackend (direct file loading)

WSP 77: Agent Coordination
"""

import logging
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
    # Try LM Studio first (avoids file locks, doesn't need model_path)
    if is_lm_studio_available():
        model_id = LM_STUDIO_MODEL_IDS["qwen"]
        backend = LMStudioBackend(model_id=model_id)
        if backend.initialize():
            logger.info(f"[RESOLVER] Qwen using LMStudioBackend ({model_id})")
            return backend
        logger.debug("[RESOLVER] LM Studio available but Qwen model not loaded")

    # Fall back to llama_cpp (requires model_path)
    if model_path is None:
        logger.warning("[RESOLVER] No Qwen backend: LM Studio unavailable and no model_path for fallback")
        return None

    backend = LlamaCppBackend(
        model_path=model_path,
        n_ctx=n_ctx,
        n_threads=n_threads,
    )
    if backend.initialize():
        logger.info(f"[RESOLVER] Qwen using LlamaCppBackend ({model_path.name})")
        return backend

    logger.warning("[RESOLVER] No Qwen backend available")
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
    # Try LM Studio first (avoids file locks, doesn't need model_path)
    if is_lm_studio_available():
        model_id = LM_STUDIO_MODEL_IDS["gemma"]
        backend = LMStudioBackend(model_id=model_id)
        if backend.initialize():
            logger.info(f"[RESOLVER] Gemma using LMStudioBackend ({model_id})")
            return backend
        logger.debug("[RESOLVER] LM Studio available but Gemma model not loaded")

    # Fall back to llama_cpp (requires model_path)
    if model_path is None:
        logger.warning("[RESOLVER] No Gemma backend: LM Studio unavailable and no model_path for fallback")
        return None

    backend = LlamaCppBackend(
        model_path=model_path,
        n_ctx=n_ctx,
        n_threads=n_threads,
        n_gpu_layers=0,  # CPU-only for fast triage
    )
    if backend.initialize():
        logger.info(f"[RESOLVER] Gemma using LlamaCppBackend ({model_path.name})")
        return backend

    logger.warning("[RESOLVER] No Gemma backend available")
    return None
