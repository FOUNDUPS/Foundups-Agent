"""
Local LLM Backend Adapters

Provides unified interface for local model inference backends:
- LlamaCppBackend: Direct GGUF file loading via llama_cpp
- LMStudioBackend: OpenAI-compatible API via LM Studio

WSP 77: Agent Coordination
WSP 91: DAEMON Observability
"""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LocalLLMBackend(ABC):
    """Abstract base for local LLM backends."""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the backend. Returns True if successful."""
        pass

    @abstractmethod
    def create_completion(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2, **kwargs) -> Dict:
        """Generate text completion. Returns dict with 'choices' containing 'text'."""
        pass

    @abstractmethod
    def create_chat_completion(self, messages: List[Dict], max_tokens: int = 512, temperature: float = 0.2, **kwargs) -> Dict:
        """Generate chat completion. Returns dict with 'choices' containing 'message'."""
        pass

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return backend identifier for logging."""
        pass

    # Compatibility methods for existing callers

    def generate_response(self, prompt: str, max_tokens: int = 512) -> str:
        """
        Compatibility wrapper for QwenInferenceEngine.generate_response() callers.
        Returns extracted text string (not raw dict).
        """
        result = self.create_completion(prompt, max_tokens=max_tokens)
        if result and "choices" in result and result["choices"]:
            return result["choices"][0].get("text", "")
        return ""

    def __call__(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2, **kwargs) -> Dict:
        """
        Compatibility wrapper for direct Llama() callable callers.
        Returns raw dict with 'choices' (same as create_completion).
        """
        return self.create_completion(prompt, max_tokens=max_tokens, temperature=temperature, **kwargs)


class LlamaCppBackend(LocalLLMBackend):
    """
    Direct GGUF model loading via llama_cpp.

    Requires exclusive file access - will fail if LM Studio holds locks.
    """

    def __init__(self, model_path: Path, n_ctx: int = 2048, n_threads: int = 4, n_gpu_layers: int = 0):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.n_gpu_layers = n_gpu_layers
        self._llm = None

    @property
    def backend_name(self) -> str:
        return "llama_cpp"

    def initialize(self) -> bool:
        """Load model via llama_cpp with stdout suppression."""
        if self._llm is not None:
            return True

        if not self.model_path.exists():
            logger.warning(f"[LLAMA-CPP] Model not found: {self.model_path}")
            return False

        try:
            from llama_cpp import Llama

            logger.info(f"[LLAMA-CPP] Loading {self.model_path.name}...")

            # Suppress llama.cpp loading noise
            old_stdout = os.dup(1)
            old_stderr = os.dup(2)
            devnull = os.open(os.devnull, os.O_WRONLY)

            try:
                os.dup2(devnull, 1)
                os.dup2(devnull, 2)

                self._llm = Llama(
                    model_path=str(self.model_path),
                    n_ctx=self.n_ctx,
                    n_threads=self.n_threads,
                    n_gpu_layers=self.n_gpu_layers,
                    verbose=False,
                )
            finally:
                os.dup2(old_stdout, 1)
                os.dup2(old_stderr, 2)
                os.close(devnull)
                os.close(old_stdout)
                os.close(old_stderr)

            logger.info(f"[LLAMA-CPP] Model loaded: {self.model_path.name}")
            return True

        except Exception as e:
            logger.error(f"[LLAMA-CPP] Load failed: {e}")
            return False

    def create_completion(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2, **kwargs) -> Dict:
        if self._llm is None:
            return {"choices": [{"text": ""}]}
        try:
            return self._llm(prompt, max_tokens=max_tokens, temperature=temperature, **kwargs)
        except Exception as e:
            logger.error(f"[LLAMA-CPP] Completion failed: {e}")
            return {"choices": [{"text": ""}]}

    def create_chat_completion(self, messages: List[Dict], max_tokens: int = 512, temperature: float = 0.2, **kwargs) -> Dict:
        if self._llm is None:
            return {"choices": [{"message": {"content": ""}}]}
        try:
            return self._llm.create_chat_completion(messages=messages, max_tokens=max_tokens, temperature=temperature, **kwargs)
        except Exception as e:
            logger.error(f"[LLAMA-CPP] Chat completion failed: {e}")
            return {"choices": [{"message": {"content": ""}}]}


class LMStudioBackend(LocalLLMBackend):
    """
    LM Studio OpenAI-compatible API backend.

    Connects to LM Studio's local server (default: localhost:1234).
    Avoids file lock conflicts when LM Studio is running.
    """

    DEFAULT_BASE_URL = "http://localhost:1234/v1"

    def __init__(self, model_id: str, base_url: str = None):
        self.model_id = model_id
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self._client = None
        self._initialized = False

    @property
    def backend_name(self) -> str:
        return "lm_studio"

    def initialize(self) -> bool:
        """Verify LM Studio API is available and model is loaded."""
        if self._initialized:
            return True

        try:
            from openai import OpenAI

            self._client = OpenAI(
                base_url=self.base_url,
                api_key="not-needed",
                timeout=30.0,
            )

            # Verify model is available
            models = self._client.models.list()
            available = [m.id for m in models.data]

            if self.model_id not in available:
                logger.warning(f"[LM-STUDIO] Model '{self.model_id}' not loaded. Available: {available}")
                return False

            logger.info(f"[LM-STUDIO] Connected, model '{self.model_id}' ready")
            self._initialized = True
            return True

        except ImportError:
            logger.warning("[LM-STUDIO] openai package not installed")
            return False
        except Exception as e:
            logger.debug(f"[LM-STUDIO] Not available: {e}")
            return False

    def create_completion(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2, **kwargs) -> Dict:
        if not self._initialized or self._client is None:
            return {"choices": [{"text": ""}]}
        try:
            response = self._client.completions.create(
                model=self.model_id,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return {"choices": [{"text": response.choices[0].text if response.choices else ""}]}
        except Exception as e:
            logger.error(f"[LM-STUDIO] Completion failed: {e}")
            return {"choices": [{"text": ""}]}

    def create_chat_completion(self, messages: List[Dict], max_tokens: int = 512, temperature: float = 0.2, **kwargs) -> Dict:
        if not self._initialized or self._client is None:
            return {"choices": [{"message": {"content": ""}}]}
        try:
            response = self._client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return {"choices": [{"message": {"content": response.choices[0].message.content if response.choices else ""}}]}
        except Exception as e:
            logger.error(f"[LM-STUDIO] Chat completion failed: {e}")
            return {"choices": [{"message": {"content": ""}}]}


def is_lm_studio_available(base_url: str = LMStudioBackend.DEFAULT_BASE_URL) -> bool:
    """Check if LM Studio API is responding."""
    try:
        import urllib.request
        import json

        req = urllib.request.Request(f"{base_url}/models", method="GET")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode())
            return "data" in data and len(data["data"]) > 0
    except Exception:
        return False
