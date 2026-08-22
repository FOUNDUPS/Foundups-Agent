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
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
    LMStudioAuthenticationError,
    LMStudioResidencyState,
    inspect_lm_studio_model,
    normalize_lm_studio_base_url,
)

logger = logging.getLogger(__name__)


class _RejectLMStudioRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        return None


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
    MAX_NATIVE_REQUEST_BYTES = 262_144

    def __init__(
        self,
        model_id: str,
        base_url: str = None,
        request_timeout: float = 30.0,
        expected_instance_id: str | None = None,
        api_token: str | None = None,
    ):
        self.model_id = model_id
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.request_timeout = max(1.0, min(float(request_timeout), 600.0))
        self.expected_instance_id = expected_instance_id
        self.api_token = api_token
        self._client = None
        self._initialized = False

    @property
    def backend_name(self) -> str:
        return "lm_studio"

    @property
    def inference_model_id(self) -> str:
        """Prefer the exact verified instance identity when one was leased."""
        return self.expected_instance_id or self.model_id

    def initialize(self) -> bool:
        """Verify LM Studio API is available and model is loaded."""
        if self._initialized:
            return True

        try:
            state = inspect_lm_studio_model(
                self.model_id,
                base_url=self.base_url,
                api_token=self.api_token,
                timeout=min(self.request_timeout, 10.0),
            )
            if state.state is not LMStudioResidencyState.RESIDENT:
                logger.warning(
                    "[LM-STUDIO] Exact model '%s' is not resident (%s)",
                    self.model_id,
                    state.state.value,
                )
                return False
            instance_ids = tuple(item.instance_id for item in state.loaded_instances)
            expected = self.expected_instance_id
            if len(instance_ids) != 1 or (expected is not None and instance_ids[0] != expected):
                logger.warning("[LM-STUDIO] Exact model residency is ambiguous or changed")
                return False
            self.expected_instance_id = instance_ids[0]

            from openai import OpenAI

            root = normalize_lm_studio_base_url(self.base_url)
            self._client = OpenAI(
                base_url=f"{root}/v1",
                api_key=self.api_token or "not-needed",
                timeout=self.request_timeout,
            )
            logger.info("[LM-STUDIO] Exact model '%s' resident and verified", self.model_id)
            self._initialized = True
            return True

        except ImportError:
            logger.warning("[LM-STUDIO] openai package not installed")
            return False
        except LMStudioAuthenticationError:
            raise
        except Exception as e:
            logger.debug(f"[LM-STUDIO] Not available: {e}")
            return False

    def create_completion(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2, **kwargs) -> Dict:
        if not self._initialized or self._client is None:
            return {"choices": [{"text": ""}]}
        try:
            self._require_exact_instance_unchanged()
            response = self._client.completions.create(
                model=self.inference_model_id,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            self._require_exact_instance_unchanged()
            return {"choices": [{"text": response.choices[0].text if response.choices else ""}]}
        except LMStudioAuthenticationError:
            raise
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
            self._require_exact_instance_unchanged()
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
                model=self.inference_model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **controls,
            )
            self._require_exact_instance_unchanged()
            content = response.choices[0].message.content if response.choices else ""
            return {"choices": [{"message": {"content": content}}]}
        except LMStudioAuthenticationError:
            raise
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
        request = _build_lm_studio_native_chat_request(
            base_url=self.base_url,
            model_id=self.inference_model_id,
            api_token=self.api_token,
            input_text=input_text,
            system_prompt=system_prompt,
            reasoning=reasoning,
            temperature=temperature,
            top_p=top_p,
            max_output_tokens=max_output_tokens,
            max_request_bytes=self.MAX_NATIVE_REQUEST_BYTES,
        )
        try:
            self._require_exact_instance_unchanged()
            response = _read_lm_studio_native_chat(
                request,
                timeout=self.request_timeout,
                max_response_bytes=int(max_response_bytes),
            )
            _verify_native_instance_response(response, self.expected_instance_id)
            self._require_exact_instance_unchanged()
            return response
        except LMStudioAuthenticationError:
            raise
        except Exception as exc:
            logger.error(f"[LM-STUDIO] Native chat failed: {exc}")
            return {"output": []}

    def _require_exact_instance_unchanged(self) -> None:
        """Fail before/after use unless the initialized instance still owns the key."""

        _require_exact_lm_studio_instance_unchanged(self)


def _build_lm_studio_native_chat_request(
    *,
    base_url: str,
    model_id: str,
    api_token: str | None,
    max_request_bytes: int,
    **controls: Any,
) -> urllib.request.Request:
    headers = {"Content-Type": "application/json"}
    if api_token is not None:
        headers["Authorization"] = f"Bearer {api_token}"
    payload = _lm_studio_native_chat_payload(model_id=model_id, **controls)
    if len(payload) > max_request_bytes:
        raise ValueError("lm_studio_native_request_too_large")
    return urllib.request.Request(
        _lm_studio_native_chat_endpoint(base_url),
        data=payload,
        headers=headers,
        method="POST",
    )


def _require_exact_lm_studio_instance_unchanged(backend: LMStudioBackend) -> None:
    state = inspect_lm_studio_model(
        backend.model_id,
        base_url=backend.base_url,
        api_token=backend.api_token,
        timeout=min(backend.request_timeout, 10.0),
    )
    instance_ids = tuple(item.instance_id for item in state.loaded_instances)
    if (
        state.state is not LMStudioResidencyState.RESIDENT
        or len(instance_ids) != 1
        or instance_ids[0] != backend.expected_instance_id
    ):
        backend._initialized = False
        raise RuntimeError("lm_studio_exact_instance_changed")


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
    try:
        with _open_lm_studio_request(request, timeout=timeout) as response:
            if hasattr(response, "geturl") and response.geturl() != request.full_url:
                raise ValueError("lm_studio_native_redirect_rejected")
            raw = response.read(max_response_bytes + 1)
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise LMStudioAuthenticationError(
                "lm_studio_authentication_failed"
            ) from None
        raise
    if len(raw) > max_response_bytes:
        raise ValueError("lm_studio_native_response_too_large")
    decoded = json.loads(raw)
    if not isinstance(decoded, dict):
        raise ValueError("lm_studio_native_response_invalid")
    return decoded


def _verify_native_instance_response(
    response: Mapping[str, Any], expected_instance_id: str | None
) -> None:
    if expected_instance_id is None:
        return
    if response.get("model_instance_id") != expected_instance_id:
        raise ValueError("lm_studio_native_instance_mismatch")
    stats = response.get("stats")
    if not isinstance(stats, Mapping):
        raise ValueError("lm_studio_native_stats_invalid")
    if "model_load_time_seconds" in stats:
        raise ValueError("lm_studio_native_implicit_load_rejected")


def _open_lm_studio_request(
    request: urllib.request.Request, *, timeout: float
) -> Any:
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _RejectLMStudioRedirect()
    )
    return opener.open(request, timeout=timeout)


def is_lm_studio_available(
    base_url: str = LMStudioBackend.DEFAULT_BASE_URL,
    api_token: str | None = None,
) -> bool:
    """Check native LM Studio server reachability without asserting residency."""
    try:
        state = inspect_lm_studio_model(
            "__reddog_reachability_probe__",
            base_url=base_url,
            api_token=api_token,
            timeout=2.0,
        )
        return state.state is not LMStudioResidencyState.SERVER_UNREACHABLE
    except LMStudioAuthenticationError:
        raise
    except Exception:
        return False
