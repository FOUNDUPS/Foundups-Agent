"""
Local LLM Backend Adapters

Provides unified interface for local model inference backends:
- LlamaCppBackend: Direct GGUF file loading via llama_cpp
- LMStudioBackend: OpenAI-compatible API via LM Studio

WSP 77: Agent Coordination
WSP 91: DAEMON Observability
"""

import json
import logging
import os
import urllib.parse
import urllib.request
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
    ALLOWED_CHAT_CONTROLS = frozenset({"response_format", "seed", "stop", "top_p"})

    def __init__(self, model_id: str, base_url: str = None, request_timeout: float = 30.0):
        self.model_id = model_id
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.request_timeout = max(1.0, min(float(request_timeout), 600.0))
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
                timeout=self.request_timeout,
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

    def create_chat_completion(
        self,
        messages: List[Dict],
        max_tokens: int = 512,
        temperature: float = 0.2,
        **kwargs,
    ) -> Dict:
        if not self._initialized or self._client is None:
            return {"choices": [{"message": {"content": ""}}]}
        try:
            controls = {
                name: kwargs[name]
                for name in self.ALLOWED_CHAT_CONTROLS
                if name in kwargs
            }
            if "enable_thinking" in kwargs:
                if type(kwargs["enable_thinking"]) is not bool:
                    raise ValueError("invalid_enable_thinking")
                controls["extra_body"] = {
                    "chat_template_kwargs": {
                        "enable_thinking": kwargs["enable_thinking"],
                    }
                }
            response = self._client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **controls,
            )
            content = response.choices[0].message.content if response.choices else ""
            return {"choices": [{"message": {"content": content}}]}
        except Exception as e:
            logger.error(f"[LM-STUDIO] Chat completion failed: {e}")
            return {"choices": [{"message": {"content": ""}}]}

    def create_native_chat(
        self,
        *,
        input_text: str,
        system_prompt: str,
        max_output_tokens: int,
        reasoning: str = "off",
        temperature: float = 1.0,
        top_p: float = 0.95,
        max_response_bytes: int = 262_144,
    ) -> Dict:
        """Call LM Studio's native chat route with explicit reasoning control."""
        if not self._initialized:
            return {"output": []}
        if reasoning not in {"off", "low", "medium", "high", "on"}:
            raise ValueError("invalid_lm_studio_reasoning_control")
        if not 1 <= int(max_output_tokens) <= 1_000_000:
            raise ValueError("invalid_lm_studio_max_output_tokens")
        if not 1 <= int(max_response_bytes) <= 1_048_576:
            raise ValueError("invalid_lm_studio_max_response_bytes")
        request = urllib.request.Request(
            _lm_studio_native_chat_endpoint(self.base_url),
            data=_lm_studio_native_chat_payload(
                model_id=self.model_id,
                input_text=input_text,
                system_prompt=system_prompt,
                reasoning=reasoning,
                temperature=temperature,
                top_p=top_p,
                max_output_tokens=max_output_tokens,
            ),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            return _read_lm_studio_native_chat(
                request,
                timeout=self.request_timeout,
                max_response_bytes=int(max_response_bytes),
            )
        except Exception as exc:
            logger.error(f"[LM-STUDIO] Native chat failed: {exc}")
            return {"output": []}


def _lm_studio_native_chat_endpoint(base_url: str) -> str:
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("invalid_lm_studio_base_url")
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, "/api/v1/chat", "", "")
    )


def _lm_studio_native_chat_payload(
    *,
    model_id: str,
    input_text: str,
    system_prompt: str,
    reasoning: str,
    temperature: float,
    top_p: float,
    max_output_tokens: int,
) -> bytes:
    return json.dumps(
        {
            "model": model_id,
            "input": str(input_text),
            "system_prompt": str(system_prompt),
            "reasoning": reasoning,
            "temperature": float(temperature),
            "top_p": float(top_p),
            "max_output_tokens": int(max_output_tokens),
            "store": False,
            "stream": False,
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _read_lm_studio_native_chat(
    request: urllib.request.Request,
    *,
    timeout: float,
    max_response_bytes: int,
) -> Dict:
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(max_response_bytes + 1)
    if len(raw) > max_response_bytes:
        raise ValueError("lm_studio_native_response_too_large")
    decoded = json.loads(raw)
    if not isinstance(decoded, dict):
        raise ValueError("lm_studio_native_response_invalid")
    return decoded


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
