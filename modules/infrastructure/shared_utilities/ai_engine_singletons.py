"""
AI Engine Singletons - Centralized LLM Instance Management

WSP 77: Agent Coordination (Qwen + Gemma engines)
WSP 91: DAEMON Observability (load time logging)

This module provides singleton access to AI engines (Qwen, Gemma) to prevent
redundant model loading. Loading llama_cpp models takes 2-10 seconds each,
so multiple components loading the same model wastes significant startup time.

Usage:
    from modules.infrastructure.shared_utilities.ai_engine_singletons import (
        get_qwen_engine,
        get_gemma_engine,
        is_qwen_loaded,
        is_gemma_loaded,
    )

    # Get or create singleton (lazy loading)
    qwen = get_qwen_engine()
    gemma = get_gemma_engine()

    # Check if already loaded (no side effects)
    if is_qwen_loaded():
        print("Qwen ready")
"""

import logging
import time
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Module-level singletons (lazy initialization)
_qwen_engine: Optional[Any] = None
_gemma_engine: Optional[Any] = None

# Track initialization state
_qwen_initialized: bool = False
_gemma_initialized: bool = False


def is_qwen_loaded() -> bool:
    """Check if Qwen engine is already loaded (no side effects)."""
    return _qwen_initialized and _qwen_engine is not None


def is_gemma_loaded() -> bool:
    """Check if Gemma engine is already loaded (no side effects)."""
    return _gemma_initialized and _gemma_engine is not None


def get_qwen_engine(
    max_tokens: int = 512,
    temperature: float = 0.2,
    context_length: int = 2048,
    force_reinit: bool = False,
) -> Optional[Any]:
    """
    Get or create singleton Qwen inference engine.

    Uses local_llm_resolver to select best available backend:
    1. LM Studio API (if available) - avoids file lock conflicts, no config needed
    2. Direct llama_cpp loading (fallback) - requires QwenAdvisorConfig

    Args:
        max_tokens: Maximum tokens to generate (unused by backend, kept for API compat)
        temperature: Sampling temperature (unused by backend, kept for API compat)
        context_length: Context window size
        force_reinit: Force re-initialization (use with caution)

    Returns:
        LocalLLMBackend instance with .generate_response() compatibility, or None
    """
    global _qwen_engine, _qwen_initialized

    # Return existing if already loaded
    if _qwen_initialized and _qwen_engine is not None and not force_reinit:
        logger.debug("[AI-SINGLETON] Qwen engine already loaded, returning existing")
        return _qwen_engine

    try:
        from modules.infrastructure.shared_utilities.local_llm_resolver import resolve_qwen_backend

        start_time = time.time()
        logger.info("[AI-SINGLETON] Resolving Qwen backend...")

        # First try without model_path (LM Studio path - no config needed)
        engine = resolve_qwen_backend(n_ctx=context_length)

        # If LM Studio unavailable, try with config for llama_cpp fallback
        if engine is None:
            try:
                from holo_index.qwen_advisor.config import QwenAdvisorConfig
                config = QwenAdvisorConfig.from_env()
                engine = resolve_qwen_backend(
                    model_path=config.model_path,
                    n_ctx=context_length,
                )
            except Exception as config_err:
                logger.debug(f"[AI-SINGLETON] Config load failed, LM Studio was only option: {config_err}")

        if engine is not None:
            load_time = (time.time() - start_time) * 1000
            logger.info(f"[AI-SINGLETON] Qwen engine ready ({engine.backend_name}) in {load_time:.0f}ms")
            _qwen_engine = engine
            _qwen_initialized = True
            return _qwen_engine
        else:
            logger.warning("[AI-SINGLETON] Qwen engine: no backend available")
            return None

    except ImportError as e:
        logger.warning(f"[AI-SINGLETON] Qwen engine unavailable: {e}")
        return None
    except Exception as e:
        logger.error(f"[AI-SINGLETON] Qwen engine load failed: {e}")
        return None


def get_gemma_engine(
    n_ctx: int = 1024,
    n_threads: int = 4,
    force_reinit: bool = False,
) -> Optional[Any]:
    """
    Get or create singleton Gemma inference engine.

    Uses local_llm_resolver to select best available backend:
    1. LM Studio API (if available) - avoids file lock conflicts, no config needed
    2. Direct llama_cpp loading (fallback) - requires model path resolution

    Args:
        n_ctx: Context window size
        n_threads: Number of threads for inference
        force_reinit: Force re-initialization (use with caution)

    Returns:
        LocalLLMBackend instance (callable), or None if unavailable
    """
    global _gemma_engine, _gemma_initialized

    # Return existing if already loaded
    if _gemma_initialized and _gemma_engine is not None and not force_reinit:
        logger.debug("[AI-SINGLETON] Gemma engine already loaded, returning existing")
        return _gemma_engine

    try:
        from modules.infrastructure.shared_utilities.local_llm_resolver import resolve_gemma_backend

        start_time = time.time()
        logger.info("[AI-SINGLETON] Resolving Gemma backend...")

        # First try without model_path (LM Studio path - no config needed)
        engine = resolve_gemma_backend(n_ctx=n_ctx, n_threads=n_threads)

        # If LM Studio unavailable, try with model path for llama_cpp fallback
        if engine is None:
            try:
                from modules.infrastructure.shared_utilities.local_model_selection import (
                    resolve_triage_model_path,
                )
                model_path = resolve_triage_model_path()
                engine = resolve_gemma_backend(
                    model_path=model_path,
                    n_ctx=n_ctx,
                    n_threads=n_threads,
                )
            except Exception as path_err:
                logger.debug(f"[AI-SINGLETON] Model path resolution failed, LM Studio was only option: {path_err}")

        if engine is not None:
            load_time = (time.time() - start_time) * 1000
            logger.info(f"[AI-SINGLETON] Gemma engine ready ({engine.backend_name}) in {load_time:.0f}ms")
            _gemma_engine = engine
            _gemma_initialized = True
            return _gemma_engine
        else:
            logger.warning("[AI-SINGLETON] Gemma engine: no backend available")
            return None

    except ImportError as e:
        logger.warning(f"[AI-SINGLETON] Gemma engine unavailable: {e}")
        return None
    except Exception as e:
        logger.error(f"[AI-SINGLETON] Gemma engine load failed: {e}")
        return None


def get_engine_status() -> dict:
    """
    Get status of all AI engine singletons.

    Returns:
        Dict with load status for each engine
    """
    return {
        "qwen": {
            "loaded": is_qwen_loaded(),
            "instance": _qwen_engine is not None,
        },
        "gemma": {
            "loaded": is_gemma_loaded(),
            "instance": _gemma_engine is not None,
        },
    }


def unload_engines():
    """
    Unload all engines (for testing or memory cleanup).

    Note: In practice, engines should stay loaded for the lifetime
    of the process to avoid repeated slow initialization.
    """
    global _qwen_engine, _gemma_engine, _qwen_initialized, _gemma_initialized

    _qwen_engine = None
    _gemma_engine = None
    _qwen_initialized = False
    _gemma_initialized = False

    logger.info("[AI-SINGLETON] All engines unloaded")
