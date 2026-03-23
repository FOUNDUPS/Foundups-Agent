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
from pathlib import Path
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

    Uses QwenInferenceEngine from holo_index with lazy loading.
    Logs load time for WSP 91 observability.

    Args:
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        context_length: Context window size
        force_reinit: Force re-initialization (use with caution)

    Returns:
        QwenInferenceEngine instance, or None if unavailable
    """
    global _qwen_engine, _qwen_initialized

    # Return existing if already loaded
    if _qwen_initialized and _qwen_engine is not None and not force_reinit:
        logger.debug("[AI-SINGLETON] Qwen engine already loaded, returning existing")
        return _qwen_engine

    try:
        from holo_index.qwen_advisor.llm_engine import QwenInferenceEngine
        from holo_index.qwen_advisor.config import QwenAdvisorConfig

        start_time = time.time()
        logger.info("[AI-SINGLETON] Loading Qwen engine (singleton)...")

        config = QwenAdvisorConfig.from_env()
        engine = QwenInferenceEngine(
            model_path=config.model_path,
            max_tokens=max_tokens,
            temperature=temperature,
            context_length=context_length,
        )

        # Initialize the model
        if engine.initialize():
            load_time = (time.time() - start_time) * 1000
            logger.info(f"[AI-SINGLETON] Qwen engine loaded in {load_time:.0f}ms")
            _qwen_engine = engine
            _qwen_initialized = True
            return _qwen_engine
        else:
            logger.warning("[AI-SINGLETON] Qwen engine initialization failed")
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

    Uses llama_cpp directly with the triage model path.
    Logs load time for WSP 91 observability.

    Args:
        n_ctx: Context window size
        n_threads: Number of threads for inference
        force_reinit: Force re-initialization (use with caution)

    Returns:
        Llama instance for Gemma, or None if unavailable
    """
    global _gemma_engine, _gemma_initialized

    # Return existing if already loaded
    if _gemma_initialized and _gemma_engine is not None and not force_reinit:
        logger.debug("[AI-SINGLETON] Gemma engine already loaded, returning existing")
        return _gemma_engine

    try:
        from llama_cpp import Llama
        from modules.infrastructure.shared_utilities.local_model_selection import (
            resolve_triage_model_path,
        )
        import os

        model_path = resolve_triage_model_path()
        if not model_path.exists():
            logger.warning(f"[AI-SINGLETON] Gemma model not found: {model_path}")
            return None

        start_time = time.time()
        logger.info(f"[AI-SINGLETON] Loading Gemma engine from {model_path} (singleton)...")

        # Suppress llama.cpp loading noise
        old_stdout = os.dup(1)
        old_stderr = os.dup(2)
        devnull = os.open(os.devnull, os.O_WRONLY)

        try:
            os.dup2(devnull, 1)
            os.dup2(devnull, 2)

            engine = Llama(
                model_path=str(model_path),
                n_ctx=n_ctx,
                n_threads=n_threads,
                n_gpu_layers=0,  # CPU-only for fast pattern matching
                verbose=False,
            )
        finally:
            os.dup2(old_stdout, 1)
            os.dup2(old_stderr, 2)
            os.close(devnull)
            os.close(old_stdout)
            os.close(old_stderr)

        load_time = (time.time() - start_time) * 1000
        logger.info(f"[AI-SINGLETON] Gemma engine loaded in {load_time:.0f}ms")

        _gemma_engine = engine
        _gemma_initialized = True
        return _gemma_engine

    except ImportError as e:
        logger.warning(f"[AI-SINGLETON] Gemma engine unavailable (llama_cpp not installed): {e}")
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
